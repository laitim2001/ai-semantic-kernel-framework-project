"""Multi-turn conversation session for Claude SDK."""

import uuid
import time
from typing import Optional, List, Dict, Any

from anthropic import AsyncAnthropic

from .config import ClaudeSDKConfig
from .types import (
    Message,
    ToolCall,
    QueryContext,
    ToolCallContext,
    ToolResultContext,
    SessionResponse,
)
from .tools import get_tool_definitions, execute_tool


class Session:
    """
    Multi-turn conversation session.

    Maintains conversation history and context across multiple queries.

    Example:
        session = await client.create_session()
        try:
            await session.query("Read the auth module")
            await session.query("What security issues do you see?")
            recommendations = await session.query("Provide recommendations")
        finally:
            await session.close()
    """

    def __init__(
        self,
        session_id: str,
        client: AsyncAnthropic,
        config: ClaudeSDKConfig,
        tools: List[str],
        hooks: List[Any],
        mcp_servers: List[Any],
        context: Optional[Dict[str, Any]] = None,
        history: Optional[List[Message]] = None,
    ):
        self.session_id = session_id
        self._client = client
        self._config = config
        self._tools = tools
        self._hooks = hooks
        self._mcp_servers = mcp_servers
        self._context: Dict[str, Any] = context or {}
        self._history: List[Message] = history or []
        self._closed = False
        self._total_tokens = 0

    @property
    def is_closed(self) -> bool:
        return self._closed

    def get_history(self) -> List[Message]:
        """Get conversation history."""
        return self._history.copy()

    def get_context(self) -> Dict[str, Any]:
        """Get current context variables."""
        return self._context.copy()

    def add_context(self, key: str, value: Any) -> None:
        """Add a context variable."""
        self._context[key] = value

    async def query(
        self,
        prompt: str,
        tools: Optional[List[str]] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> SessionResponse:
        """
        Send a query within the session.

        Args:
            prompt: Query text
            tools: Override session tools for this query
            max_tokens: Override max tokens
            stream: Enable streaming response (not yet implemented)

        Returns:
            SessionResponse with content and tool calls
        """
        if self._closed:
            raise RuntimeError("Session is closed")

        # Trigger query start hooks
        for hook in self._hooks:
            if hasattr(hook, "on_query_start"):
                result = await hook.on_query_start(
                    QueryContext(prompt=prompt, session_id=self.session_id)
                )
                if result and result.is_rejected:
                    raise RuntimeError(f"Query rejected: {result.reason}")

        active_tools = tools or self._tools
        tool_definitions = get_tool_definitions(active_tools, self._mcp_servers)
        tool_calls: List[ToolCall] = []

        # Build messages from history
        messages = self._build_messages()
        messages.append({"role": "user", "content": prompt})

        # Add user message to history
        self._history.append(
            Message(role="user", content=prompt, timestamp=time.time())
        )

        # Agentic loop
        while True:
            response = await self._client.messages.create(
                model=self._config.model,
                max_tokens=max_tokens or self._config.max_tokens,
                system=self._build_system_prompt(),
                messages=messages,
                tools=tool_definitions if tool_definitions else None,
            )

            self._total_tokens += (
                response.usage.input_tokens + response.usage.output_tokens
            )

            # Check for tool use
            has_tool_use = any(
                block.type == "tool_use" for block in response.content
            )

            if not has_tool_use:
                # Extract final response
                final_content = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_content += block.text

                # Add assistant response to history
                self._history.append(
                    Message(
                        role="assistant",
                        content=final_content,
                        tool_calls=tool_calls,
                        timestamp=time.time(),
                    )
                )

                # Trigger query end hooks
                for hook in self._hooks:
                    if hasattr(hook, "on_query_end"):
                        await hook.on_query_end(
                            QueryContext(prompt=prompt, session_id=self.session_id),
                            final_content,
                        )

                return SessionResponse(
                    content=final_content,
                    tool_calls=tool_calls,
                    tokens_used=self._total_tokens,
                    message_index=len(self._history) - 1,
                )

            # Process tool calls
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_call = ToolCall(
                        id=block.id, name=block.name, args=block.input
                    )
                    tool_calls.append(tool_call)

                    # Check hooks
                    approved = True
                    for hook in self._hooks:
                        if hasattr(hook, "on_tool_call"):
                            hook_result = await hook.on_tool_call(
                                ToolCallContext(
                                    tool_name=block.name,
                                    args=block.input,
                                    session_id=self.session_id,
                                )
                            )
                            if hook_result and hook_result.is_rejected:
                                approved = False
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": f"Rejected: {hook_result.reason}",
                                    "is_error": True,
                                })
                                break

                    if not approved:
                        continue

                    # Execute tool
                    try:
                        result = await execute_tool(
                            tool_name=block.name,
                            args=block.input,
                            mcp_servers=self._mcp_servers,
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                        for hook in self._hooks:
                            if hasattr(hook, "on_tool_result"):
                                await hook.on_tool_result(
                                    ToolResultContext(
                                        tool_name=block.name,
                                        result=result,
                                        success=True,
                                        session_id=self.session_id,
                                    )
                                )

                    except Exception as e:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error: {str(e)}",
                            "is_error": True,
                        })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

    async def fork(self, branch_name: Optional[str] = None) -> "Session":
        """
        Create a branched session for exploration.

        Args:
            branch_name: Optional name for the branch

        Returns:
            New Session with copied history and context
        """
        branch_id = f"{self.session_id}:{branch_name or uuid.uuid4().hex[:8]}"

        return Session(
            session_id=branch_id,
            client=self._client,
            config=self._config,
            tools=self._tools.copy(),
            hooks=self._hooks,
            mcp_servers=self._mcp_servers,
            context=self._context.copy(),
            history=self._history.copy(),
        )

    async def close(self) -> None:
        """Close the session and cleanup resources."""
        if not self._closed:
            for hook in self._hooks:
                if hasattr(hook, "on_session_end"):
                    await hook.on_session_end(self.session_id)
            self._closed = True

    def _build_messages(self) -> List[Dict[str, Any]]:
        """Build API messages from history."""
        messages = []
        for msg in self._history:
            messages.append({"role": msg.role, "content": msg.content})
        return messages

    def _build_system_prompt(self) -> str:
        """Build system prompt with context."""
        base = self._config.system_prompt or ""

        if self._context:
            context_str = "\n".join(
                f"{k}: {v}" for k, v in self._context.items()
            )
            base = f"{base}\n\nContext:\n{context_str}"

        return base
