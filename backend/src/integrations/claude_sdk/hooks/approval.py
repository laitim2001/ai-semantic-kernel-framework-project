"""Approval Hook for Claude SDK.

Sprint 49: S49-3 - Hooks System (10 pts)
Requires human confirmation for write/destructive operations.
"""

import asyncio
from typing import Callable, Optional, Set, Awaitable

from .base import Hook
from ..types import HookResult, ToolCallContext


# Default tools that require approval
DEFAULT_APPROVAL_TOOLS: Set[str] = {
    "Write",
    "Edit",
    "MultiEdit",
    "Bash",
}

# Tools that modify data (broader set)
WRITE_OPERATIONS: Set[str] = {
    "Write",
    "Edit",
    "MultiEdit",
    "Bash",
    "Task",
}


class ApprovalHook(Hook):
    """Hook that requires human approval for write operations.

    This hook intercepts tool calls that could modify files or execute
    commands, requiring explicit approval before proceeding.

    Args:
        approval_callback: Async function to request approval.
            Should return True if approved, False if rejected.
        approval_tools: Set of tool names requiring approval.
            Defaults to Write, Edit, MultiEdit, Bash.
        auto_approve_reads: If True, auto-approve Read, Glob, Grep.
        timeout: Timeout for approval request in seconds.

    Example:
        async def request_approval(context: ToolCallContext) -> bool:
            response = await ask_user(f"Allow {context.tool_name}?")
            return response == "yes"

        hook = ApprovalHook(approval_callback=request_approval)
    """

    name: str = "approval"
    priority: int = 90  # High priority - run early

    def __init__(
        self,
        approval_callback: Optional[
            Callable[[ToolCallContext], Awaitable[bool]]
        ] = None,
        approval_tools: Optional[Set[str]] = None,
        auto_approve_reads: bool = True,
        timeout: float = 300.0,  # 5 minutes default
    ):
        self.approval_callback = approval_callback
        self.approval_tools = approval_tools or DEFAULT_APPROVAL_TOOLS.copy()
        self.auto_approve_reads = auto_approve_reads
        self.timeout = timeout

        # Track approved operations for session
        self._approved_operations: Set[str] = set()

        # Read-only tools that are auto-approved
        self._read_tools: Set[str] = {"Read", "Glob", "Grep"}

    async def on_tool_call(self, context: ToolCallContext) -> HookResult:
        """Check if tool requires approval.

        Args:
            context: Tool call context

        Returns:
            HookResult - ALLOW if approved, reject if denied
        """
        tool_name = context.tool_name

        # Auto-approve read operations
        if self.auto_approve_reads and tool_name in self._read_tools:
            return HookResult.ALLOW

        # Check if tool requires approval
        if tool_name not in self.approval_tools:
            return HookResult.ALLOW

        # Generate operation key for deduplication
        operation_key = self._get_operation_key(context)

        # Check if already approved in this session
        if operation_key in self._approved_operations:
            return HookResult.ALLOW

        # Request approval
        if self.approval_callback is None:
            # No callback configured - reject by default
            return HookResult.reject(
                f"Tool '{tool_name}' requires approval but no callback configured"
            )

        try:
            # Request approval with timeout
            approved = await asyncio.wait_for(
                self.approval_callback(context),
                timeout=self.timeout,
            )

            if approved:
                # Remember approval for this session
                self._approved_operations.add(operation_key)
                return HookResult.ALLOW
            else:
                return HookResult.reject(
                    f"User rejected {tool_name} operation"
                )

        except asyncio.TimeoutError:
            return HookResult.reject(
                f"Approval timeout for {tool_name} (waited {self.timeout}s)"
            )
        except Exception as e:
            return HookResult.reject(
                f"Approval failed for {tool_name}: {str(e)}"
            )

    async def on_session_start(self, session_id: str) -> None:
        """Clear approved operations at session start."""
        self._approved_operations.clear()

    async def on_session_end(self, session_id: str) -> None:
        """Clear approved operations at session end."""
        self._approved_operations.clear()

    def _get_operation_key(self, context: ToolCallContext) -> str:
        """Generate unique key for an operation.

        Used to track which operations have been approved.
        """
        # Include tool name and key args
        tool_name = context.tool_name
        args = context.args

        # For file operations, include path
        if "file_path" in args:
            return f"{tool_name}:{args['file_path']}"
        elif "path" in args:
            return f"{tool_name}:{args['path']}"
        elif "command" in args:
            # For Bash, use command prefix
            cmd = args["command"][:50] if args["command"] else ""
            return f"{tool_name}:{cmd}"

        return tool_name

    def add_approval_tool(self, tool_name: str) -> None:
        """Add a tool to the approval list."""
        self.approval_tools.add(tool_name)

    def remove_approval_tool(self, tool_name: str) -> None:
        """Remove a tool from the approval list."""
        self.approval_tools.discard(tool_name)

    def clear_approved_operations(self) -> None:
        """Clear all approved operations (require re-approval)."""
        self._approved_operations.clear()
