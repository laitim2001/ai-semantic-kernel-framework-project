"""Base Hook class for Claude SDK.

Sprint 49: S49-3 - Hooks System (10 pts)
Provides the abstract base class for all hooks with lifecycle methods.
"""

from abc import ABC, abstractmethod
from typing import Optional

from ..types import (
    HookResult,
    QueryContext,
    ToolCallContext,
    ToolResultContext,
)


class Hook(ABC):
    """Abstract base class for all hooks.

    Hooks intercept various stages of Claude SDK execution:
    - Session lifecycle (start/end)
    - Query lifecycle (start/end)
    - Tool execution (before/after)
    - Error handling

    Priority determines execution order (higher = earlier, 0-100).

    Example:
        class MyHook(Hook):
            priority = 60

            async def on_tool_call(self, context: ToolCallContext) -> HookResult:
                if context.tool_name == "Write":
                    return HookResult.reject("Write operations not allowed")
                return HookResult.ALLOW
    """

    # Priority for hook execution order (higher = executes first)
    # Range: 0-100 (default: 50)
    priority: int = 50

    # Hook name for identification
    name: str = "base"

    # Whether hook is enabled
    enabled: bool = True

    async def on_session_start(self, session_id: str) -> None:
        """Called when a session starts.

        Args:
            session_id: Unique session identifier
        """
        pass

    async def on_session_end(self, session_id: str) -> None:
        """Called when a session ends.

        Args:
            session_id: Unique session identifier
        """
        pass

    async def on_query_start(self, context: QueryContext) -> HookResult:
        """Called before a query is processed.

        Args:
            context: Query context with prompt and session info

        Returns:
            HookResult - ALLOW, reject(reason), or modify(args)
        """
        return HookResult.ALLOW

    async def on_query_end(
        self,
        context: QueryContext,
        result: str,
    ) -> None:
        """Called after a query is processed.

        Args:
            context: Query context
            result: The query result
        """
        pass

    async def on_tool_call(self, context: ToolCallContext) -> HookResult:
        """Called before a tool is executed.

        This is the primary interception point for tool calls.

        Args:
            context: Tool call context with name, args, session info

        Returns:
            HookResult - ALLOW, reject(reason), or modify(args)
        """
        return HookResult.ALLOW

    async def on_tool_result(self, context: ToolResultContext) -> None:
        """Called after a tool completes execution.

        Args:
            context: Tool result context with result and success status
        """
        pass

    async def on_error(self, error: Exception) -> None:
        """Called when an error occurs during execution.

        Args:
            error: The exception that occurred
        """
        pass


class HookChain:
    """Manages a chain of hooks with priority-based execution.

    Hooks are executed in priority order (highest first).
    If any hook rejects, execution stops immediately.
    If a hook modifies args, subsequent hooks receive modified args.
    """

    def __init__(self):
        self._hooks: list[Hook] = []

    def add(self, hook: Hook) -> None:
        """Add a hook to the chain.

        Args:
            hook: Hook instance to add
        """
        self._hooks.append(hook)
        # Sort by priority (descending - higher priority first)
        self._hooks.sort(key=lambda h: h.priority, reverse=True)

    def remove(self, hook: Hook) -> None:
        """Remove a hook from the chain.

        Args:
            hook: Hook instance to remove
        """
        if hook in self._hooks:
            self._hooks.remove(hook)

    def clear(self) -> None:
        """Remove all hooks from the chain."""
        self._hooks.clear()

    @property
    def hooks(self) -> list[Hook]:
        """Get all registered hooks in priority order."""
        return list(self._hooks)

    async def run_session_start(self, session_id: str) -> None:
        """Run on_session_start for all hooks."""
        for hook in self._hooks:
            if hook.enabled:
                await hook.on_session_start(session_id)

    async def run_session_end(self, session_id: str) -> None:
        """Run on_session_end for all hooks."""
        for hook in self._hooks:
            if hook.enabled:
                await hook.on_session_end(session_id)

    async def run_query_start(self, context: QueryContext) -> HookResult:
        """Run on_query_start for all hooks.

        Returns first rejection or ALLOW if all pass.
        Modified args are passed to subsequent hooks.
        """
        current_context = context
        for hook in self._hooks:
            if not hook.enabled:
                continue

            result = await hook.on_query_start(current_context)

            if result.is_rejected:
                return result

            if result.is_modified and result.modified_args:
                # Create new context with modified args
                current_context = QueryContext(
                    prompt=result.modified_args.get("prompt", current_context.prompt),
                    session_id=current_context.session_id,
                    tools=result.modified_args.get("tools", current_context.tools),
                )

        return HookResult.ALLOW

    async def run_query_end(self, context: QueryContext, result: str) -> None:
        """Run on_query_end for all hooks."""
        for hook in self._hooks:
            if hook.enabled:
                await hook.on_query_end(context, result)

    async def run_tool_call(self, context: ToolCallContext) -> HookResult:
        """Run on_tool_call for all hooks.

        Returns first rejection or ALLOW if all pass.
        Modified args are passed to subsequent hooks.
        """
        current_context = context
        for hook in self._hooks:
            if not hook.enabled:
                continue

            result = await hook.on_tool_call(current_context)

            if result.is_rejected:
                return result

            if result.is_modified and result.modified_args:
                # Create new context with modified args
                current_context = ToolCallContext(
                    tool_name=current_context.tool_name,
                    args=result.modified_args,
                    session_id=current_context.session_id,
                    tool_source=current_context.tool_source,
                    mcp_server=current_context.mcp_server,
                )

        # Return ALLOW with final modified args if any modifications occurred
        if current_context.args != context.args:
            return HookResult.modify(current_context.args)

        return HookResult.ALLOW

    async def run_tool_result(self, context: ToolResultContext) -> None:
        """Run on_tool_result for all hooks."""
        for hook in self._hooks:
            if hook.enabled:
                await hook.on_tool_result(context)

    async def run_error(self, error: Exception) -> None:
        """Run on_error for all hooks."""
        for hook in self._hooks:
            if hook.enabled:
                await hook.on_error(error)
