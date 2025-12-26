"""MCP exceptions.

Sprint 50: S50-1 - MCP Server 基礎 (10 pts)
Exception classes for MCP server implementation.
"""

from typing import Any, Dict, Optional

from .types import MCPErrorCode


class MCPError(Exception):
    """Base exception for MCP operations."""

    code: int = MCPErrorCode.INTERNAL_ERROR
    message: str = "Internal MCP error"

    def __init__(
        self,
        message: Optional[str] = None,
        code: Optional[int] = None,
        data: Optional[Any] = None,
    ):
        self.message = message or self.__class__.message
        self.code = code or self.__class__.code
        self.data = data
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-RPC error format."""
        error = {
            "code": self.code,
            "message": self.message,
        }
        if self.data is not None:
            error["data"] = self.data
        return error


class MCPConnectionError(MCPError):
    """Error connecting to MCP server."""

    code = MCPErrorCode.CONNECTION_ERROR
    message = "Failed to connect to MCP server"


class MCPDisconnectedError(MCPError):
    """MCP server is not connected."""

    code = MCPErrorCode.SERVER_NOT_CONNECTED
    message = "MCP server is not connected"


class MCPTimeoutError(MCPError):
    """Timeout waiting for MCP server response."""

    code = MCPErrorCode.TIMEOUT_ERROR
    message = "Timeout waiting for MCP server response"


class MCPToolNotFoundError(MCPError):
    """Requested tool not found on MCP server."""

    code = MCPErrorCode.TOOL_NOT_FOUND
    message = "Tool not found"

    def __init__(self, tool_name: str, server_name: Optional[str] = None):
        self.tool_name = tool_name
        self.server_name = server_name
        message = f"Tool '{tool_name}' not found"
        if server_name:
            message += f" on server '{server_name}'"
        super().__init__(message=message, data={"tool_name": tool_name})


class MCPToolExecutionError(MCPError):
    """Error executing MCP tool."""

    code = MCPErrorCode.TOOL_EXECUTION_ERROR
    message = "Tool execution failed"

    def __init__(
        self,
        tool_name: str,
        error_message: str,
        server_name: Optional[str] = None,
    ):
        self.tool_name = tool_name
        self.server_name = server_name
        message = f"Tool '{tool_name}' execution failed: {error_message}"
        super().__init__(
            message=message,
            data={"tool_name": tool_name, "error": error_message},
        )


class MCPParseError(MCPError):
    """Error parsing MCP message."""

    code = MCPErrorCode.PARSE_ERROR
    message = "Failed to parse MCP message"


class MCPInvalidRequestError(MCPError):
    """Invalid MCP request."""

    code = MCPErrorCode.INVALID_REQUEST
    message = "Invalid MCP request"


class MCPMethodNotFoundError(MCPError):
    """MCP method not found."""

    code = MCPErrorCode.METHOD_NOT_FOUND
    message = "Method not found"

    def __init__(self, method: str):
        self.method = method
        super().__init__(
            message=f"Method '{method}' not found",
            data={"method": method},
        )


class MCPInvalidParamsError(MCPError):
    """Invalid MCP method parameters."""

    code = MCPErrorCode.INVALID_PARAMS
    message = "Invalid method parameters"


class MCPServerError(MCPError):
    """MCP server returned an error."""

    def __init__(
        self,
        code: int,
        message: str,
        data: Optional[Any] = None,
    ):
        super().__init__(message=message, code=code, data=data)

    @classmethod
    def from_response(cls, error: Dict[str, Any]) -> "MCPServerError":
        """Create from JSON-RPC error response."""
        return cls(
            code=error.get("code", MCPErrorCode.INTERNAL_ERROR),
            message=error.get("message", "Unknown error"),
            data=error.get("data"),
        )


class MCPConfigurationError(MCPError):
    """Invalid MCP configuration."""

    code = MCPErrorCode.INTERNAL_ERROR
    message = "Invalid MCP configuration"

    def __init__(self, message: str, config_key: Optional[str] = None):
        data = {"config_key": config_key} if config_key else None
        super().__init__(message=message, data=data)
