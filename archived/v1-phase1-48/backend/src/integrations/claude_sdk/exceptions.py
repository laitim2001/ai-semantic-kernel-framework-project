"""Claude SDK exception classes."""

from typing import Optional, Dict, Any


class ClaudeSDKError(Exception):
    """Base exception for Claude SDK."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AuthenticationError(ClaudeSDKError):
    """Raised when API authentication fails."""
    pass


class RateLimitError(ClaudeSDKError):
    """Raised when API rate limit is exceeded."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class TimeoutError(ClaudeSDKError):
    """Raised when operation times out."""
    pass


class ToolError(ClaudeSDKError):
    """Raised when a tool execution fails."""

    def __init__(
        self,
        message: str,
        tool_name: str,
        tool_args: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.tool_name = tool_name
        self.tool_args = tool_args or {}


class HookRejectionError(ClaudeSDKError):
    """Raised when a hook rejects an operation."""

    def __init__(self, message: str, hook_name: str):
        super().__init__(message)
        self.hook_name = hook_name


class MCPError(ClaudeSDKError):
    """Base exception for MCP operations."""
    pass


class MCPConnectionError(MCPError):
    """Raised when MCP server connection fails."""

    def __init__(self, message: str, server_name: str, command: Optional[str] = None):
        super().__init__(message)
        self.server_name = server_name
        self.command = command


class MCPToolError(MCPError):
    """Raised when an MCP tool execution fails."""

    def __init__(self, message: str, server_name: str, tool_name: str):
        super().__init__(message)
        self.server_name = server_name
        self.tool_name = tool_name
