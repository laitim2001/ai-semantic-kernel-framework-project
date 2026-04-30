"""MCP type definitions.

Sprint 50: S50-1 - MCP Server 基礎 (10 pts)
Type definitions for MCP server implementation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MCPServerState(Enum):
    """MCP server connection state."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class MCPTransportType(Enum):
    """MCP transport type."""

    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"


@dataclass
class MCPToolDefinition:
    """Definition of an MCP tool.

    Represents a tool exposed by an MCP server with its schema
    and metadata.
    """

    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)
    server_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API use."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "server_name": self.server_name,
        }

    def to_claude_format(self) -> Dict[str, Any]:
        """Convert to Claude API tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


@dataclass
class MCPToolResult:
    """Result from MCP tool execution."""

    success: bool
    content: Any = None
    error: Optional[str] = None
    tool_name: Optional[str] = None
    execution_time_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "success": self.success,
            "content": self.content,
        }
        if self.error:
            result["error"] = self.error
        if self.tool_name:
            result["tool_name"] = self.tool_name
        if self.execution_time_ms is not None:
            result["execution_time_ms"] = self.execution_time_ms
        return result


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server.

    Supports both stdio (local process) and HTTP (remote) transports.
    """

    name: str
    transport: MCPTransportType = MCPTransportType.STDIO

    # Stdio transport config
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    cwd: Optional[str] = None

    # HTTP transport config
    url: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0

    # Common config
    enabled: bool = True
    auto_connect: bool = True
    retry_attempts: int = 3
    retry_delay: float = 1.0

    def validate(self) -> None:
        """Validate configuration.

        Raises:
            ValueError: If configuration is invalid.
        """
        if not self.name:
            raise ValueError("Server name is required")

        if self.transport == MCPTransportType.STDIO:
            if not self.command:
                raise ValueError("Command is required for stdio transport")
        elif self.transport == MCPTransportType.HTTP:
            if not self.url:
                raise ValueError("URL is required for HTTP transport")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "transport": self.transport.value,
            "command": self.command,
            "args": self.args,
            "env": self.env,
            "cwd": self.cwd,
            "url": self.url,
            "headers": self.headers,
            "timeout": self.timeout,
            "enabled": self.enabled,
            "auto_connect": self.auto_connect,
            "retry_attempts": self.retry_attempts,
            "retry_delay": self.retry_delay,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPServerConfig":
        """Create from dictionary."""
        transport = data.get("transport", "stdio")
        if isinstance(transport, str):
            transport = MCPTransportType(transport)

        return cls(
            name=data["name"],
            transport=transport,
            command=data.get("command"),
            args=data.get("args", []),
            env=data.get("env", {}),
            cwd=data.get("cwd"),
            url=data.get("url"),
            headers=data.get("headers", {}),
            timeout=data.get("timeout", 30.0),
            enabled=data.get("enabled", True),
            auto_connect=data.get("auto_connect", True),
            retry_attempts=data.get("retry_attempts", 3),
            retry_delay=data.get("retry_delay", 1.0),
        )


@dataclass
class MCPMessage:
    """JSON-RPC message for MCP protocol."""

    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        msg: Dict[str, Any] = {"jsonrpc": self.jsonrpc}

        if self.id is not None:
            msg["id"] = self.id
        if self.method is not None:
            msg["method"] = self.method
        if self.params is not None:
            msg["params"] = self.params
        if self.result is not None:
            msg["result"] = self.result
        if self.error is not None:
            msg["error"] = self.error

        return msg

    @classmethod
    def request(
        cls,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        id: Optional[int] = None,
    ) -> "MCPMessage":
        """Create a request message."""
        return cls(method=method, params=params, id=id)

    @classmethod
    def response(
        cls,
        result: Any,
        id: int,
    ) -> "MCPMessage":
        """Create a response message."""
        return cls(result=result, id=id)

    @classmethod
    def error_response(
        cls,
        code: int,
        message: str,
        id: Optional[int] = None,
        data: Optional[Any] = None,
    ) -> "MCPMessage":
        """Create an error response message."""
        error = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return cls(error=error, id=id)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPMessage":
        """Create from dictionary."""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            method=data.get("method"),
            params=data.get("params"),
            result=data.get("result"),
            error=data.get("error"),
        )


# Standard JSON-RPC error codes
class MCPErrorCode:
    """Standard MCP/JSON-RPC error codes."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # MCP-specific error codes
    SERVER_NOT_CONNECTED = -32000
    TOOL_NOT_FOUND = -32001
    TOOL_EXECUTION_ERROR = -32002
    TIMEOUT_ERROR = -32003
    CONNECTION_ERROR = -32004
