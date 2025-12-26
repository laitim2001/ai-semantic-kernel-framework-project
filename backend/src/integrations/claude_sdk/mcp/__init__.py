"""MCP (Model Context Protocol) Server integration.

Sprint 50: S50-1 - MCP Server 基礎 (10 pts)
Sprint 50: S50-2 - MCP Manager 與工具發現 (8 pts)

This module provides MCP server implementations for integrating
external tools and services with Claude SDK.

Supported transports:
- Stdio: Local process communication via stdin/stdout
- HTTP: Remote server communication via HTTP POST

Example:
    # Stdio server (local process)
    from src.integrations.claude_sdk.mcp import create_stdio_server

    server = create_stdio_server(
        name="filesystem",
        command="npx",
        args=["-y", "@anthropic/mcp-filesystem"],
    )
    await server.connect()
    tools = await server.list_tools()
    result = await server.execute_tool("read_file", {"path": "/tmp/test.txt"})

    # HTTP server (remote)
    from src.integrations.claude_sdk.mcp import create_http_server

    server = create_http_server(
        name="remote-tools",
        url="https://mcp.example.com/rpc",
        headers={"Authorization": "Bearer token"},
    )
    await server.connect()
    tools = await server.list_tools()

    # MCP Manager (multiple servers)
    from src.integrations.claude_sdk.mcp import MCPManager, create_manager

    manager = create_manager()
    manager.add_server(create_stdio_server("fs", "npx", ["-y", "@mcp/fs"]))
    manager.add_server(create_http_server("remote", "https://mcp.example.com"))

    async with manager:
        tools = await manager.discover_tools()
        result = await manager.execute_tool("fs:read_file", {"path": "/tmp/test"})
"""

from .base import MCPServer
from .discovery import ToolCategory, ToolDiscovery, ToolIndex
from .exceptions import (
    MCPConfigurationError,
    MCPConnectionError,
    MCPDisconnectedError,
    MCPError,
    MCPInvalidParamsError,
    MCPInvalidRequestError,
    MCPMethodNotFoundError,
    MCPParseError,
    MCPServerError,
    MCPTimeoutError,
    MCPToolExecutionError,
    MCPToolNotFoundError,
)
from .http import MCPHTTPServer, create_http_server
from .manager import (
    HealthCheckResult,
    MCPManager,
    ServerInfo,
    create_manager,
)
from .stdio import MCPStdioServer, create_stdio_server
from .types import (
    MCPErrorCode,
    MCPMessage,
    MCPServerConfig,
    MCPServerState,
    MCPToolDefinition,
    MCPToolResult,
    MCPTransportType,
)

__all__ = [
    # Base class
    "MCPServer",
    # Implementations
    "MCPStdioServer",
    "MCPHTTPServer",
    # Manager
    "MCPManager",
    "ServerInfo",
    "HealthCheckResult",
    # Discovery
    "ToolDiscovery",
    "ToolIndex",
    "ToolCategory",
    # Factory functions
    "create_stdio_server",
    "create_http_server",
    "create_manager",
    # Types
    "MCPServerConfig",
    "MCPServerState",
    "MCPTransportType",
    "MCPToolDefinition",
    "MCPToolResult",
    "MCPMessage",
    "MCPErrorCode",
    # Exceptions
    "MCPError",
    "MCPConnectionError",
    "MCPDisconnectedError",
    "MCPTimeoutError",
    "MCPToolNotFoundError",
    "MCPToolExecutionError",
    "MCPParseError",
    "MCPInvalidRequestError",
    "MCPMethodNotFoundError",
    "MCPInvalidParamsError",
    "MCPServerError",
    "MCPConfigurationError",
]
