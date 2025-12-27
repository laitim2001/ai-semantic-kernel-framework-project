"""Claude SDK MCP API routes.

Sprint 51: S51-3 MCP API Routes (7 pts)
Provides REST API endpoints for MCP server management and tool execution.
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.integrations.claude_sdk.mcp.manager import MCPManager, create_manager
from src.integrations.claude_sdk.mcp.types import (
    MCPServerConfig,
    MCPTransportType,
    MCPToolDefinition,
)
from src.integrations.claude_sdk.mcp.exceptions import (
    MCPDisconnectedError,
    MCPToolNotFoundError,
)


# --- Enums ---


class MCPTransport(str, Enum):
    """MCP transport types."""

    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"


class MCPServerStatus(str, Enum):
    """MCP server status."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    ERROR = "error"


# --- Schemas ---


class MCPServerInfo(BaseModel):
    """Schema for MCP server information."""

    id: str = Field(..., description="Server ID (same as name)")
    name: str = Field(..., description="Server name")
    transport: MCPTransport = Field(..., description="Transport type")
    status: MCPServerStatus = Field(..., description="Connection status")
    tools_count: int = Field(0, description="Number of tools available")
    url: Optional[str] = Field(None, description="Server URL (for HTTP)")
    command: Optional[str] = Field(None, description="Command (for stdio)")
    error: Optional[str] = Field(None, description="Last error message")


class MCPServerListResponse(BaseModel):
    """Response schema for listing MCP servers."""

    servers: List[MCPServerInfo]
    total: int
    connected: int


class MCPToolInfo(BaseModel):
    """Schema for MCP tool information."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    server_name: str = Field(..., description="Server providing this tool")
    input_schema: Dict[str, Any] = Field(default_factory=dict, description="Input schema")


class MCPToolListResponse(BaseModel):
    """Response schema for listing MCP tools."""

    tools: List[MCPToolInfo]
    total: int


class MCPConnectRequest(BaseModel):
    """Request schema for connecting to an MCP server."""

    name: str = Field(..., description="Server name", min_length=1)
    transport: MCPTransport = Field(MCPTransport.STDIO, description="Transport type")

    # Stdio config
    command: Optional[str] = Field(None, description="Command to execute")
    args: Optional[List[str]] = Field(default_factory=list, description="Command arguments")
    env: Optional[Dict[str, str]] = Field(default_factory=dict, description="Environment variables")

    # HTTP config
    url: Optional[str] = Field(None, description="Server URL")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="HTTP headers")
    timeout: float = Field(30.0, description="Connection timeout", ge=1.0, le=300.0)


class MCPConnectResponse(BaseModel):
    """Response schema for MCP server connection."""

    name: str
    status: MCPServerStatus
    transport: MCPTransport
    tools_discovered: int
    error: Optional[str] = None


class MCPExecuteRequest(BaseModel):
    """Request schema for MCP tool execution."""

    tool_ref: str = Field(
        ...,
        description="Tool reference (server:tool or tool name)",
        min_length=1,
    )
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    timeout: Optional[float] = Field(None, description="Execution timeout", ge=1.0, le=300.0)


class MCPExecuteResponse(BaseModel):
    """Response schema for MCP tool execution."""

    tool_name: str
    server_name: str
    success: bool
    content: Any = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None


class MCPHealthResponse(BaseModel):
    """Response schema for MCP server health check."""

    name: str
    healthy: bool
    latency_ms: Optional[float] = None
    error: Optional[str] = None


# --- Global MCP Manager ---


_mcp_manager: Optional[MCPManager] = None


def get_mcp_manager() -> MCPManager:
    """Get the global MCP manager instance."""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = create_manager(auto_discover=True)
    return _mcp_manager


# --- Router ---


router = APIRouter(prefix="/mcp", tags=["Claude SDK MCP"])


# --- Endpoints ---


@router.get("/servers", response_model=MCPServerListResponse)
async def list_mcp_servers(
    status: Optional[MCPServerStatus] = None,
    transport: Optional[MCPTransport] = None,
):
    """
    List all MCP servers.

    Returns a list of all registered MCP servers with their status.
    Optionally filter by connection status or transport type.
    """
    manager = get_mcp_manager()
    server_infos = manager.list_servers()
    servers: List[MCPServerInfo] = []

    for info in server_infos:
        # Map internal state to API status
        if info.state == "connected":
            server_status = MCPServerStatus.CONNECTED
        elif info.state == "connecting":
            server_status = MCPServerStatus.CONNECTING
        elif info.state == "error":
            server_status = MCPServerStatus.ERROR
        else:
            server_status = MCPServerStatus.DISCONNECTED

        # Filter by status
        if status and server_status != status:
            continue

        # Get server for transport info
        server = manager.get_server(info.name)
        server_transport = MCPTransport.STDIO  # Default

        if server:
            # Try to determine transport type
            if hasattr(server, "_config") and server._config:
                if server._config.transport == MCPTransportType.HTTP:
                    server_transport = MCPTransport.HTTP
                elif server._config.transport == MCPTransportType.WEBSOCKET:
                    server_transport = MCPTransport.WEBSOCKET

            # Filter by transport
            if transport and server_transport != transport:
                continue

        servers.append(MCPServerInfo(
            id=info.name,
            name=info.name,
            transport=server_transport,
            status=server_status,
            tools_count=info.tools_count,
            error=info.error,
        ))

    connected_count = sum(1 for s in servers if s.status == MCPServerStatus.CONNECTED)

    return MCPServerListResponse(
        servers=servers,
        total=len(servers),
        connected=connected_count,
    )


@router.post("/servers/connect", response_model=MCPConnectResponse)
async def connect_mcp_server(request: MCPConnectRequest):
    """
    Connect to an MCP server.

    Connects to the specified MCP server and discovers available tools.
    """
    manager = get_mcp_manager()

    # Validate request based on transport
    if request.transport == MCPTransport.STDIO:
        if not request.command:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Command is required for stdio transport",
            )
    elif request.transport in (MCPTransport.HTTP, MCPTransport.WEBSOCKET):
        if not request.url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL is required for HTTP/WebSocket transport",
            )

    # Create server config
    config = MCPServerConfig(
        name=request.name,
        transport=MCPTransportType(request.transport.value),
        command=request.command,
        args=request.args or [],
        env=request.env or {},
        url=request.url,
        headers=request.headers or {},
        timeout=request.timeout,
    )

    try:
        # Check if server already exists
        existing = manager.get_server(request.name)
        if existing:
            # Server exists, try to reconnect
            success = await manager.connect_server(request.name)
        else:
            # Create and add server
            if request.transport == MCPTransport.STDIO:
                from src.integrations.claude_sdk.mcp.stdio import MCPStdioServer

                server = MCPStdioServer(
                    name=request.name,
                    command=request.command,
                    args=request.args or [],
                    env=request.env,
                )
            else:
                from src.integrations.claude_sdk.mcp.http import MCPHTTPServer

                server = MCPHTTPServer(
                    name=request.name,
                    url=request.url,
                    headers=request.headers,
                    timeout=request.timeout,
                )

            manager.add_server(server)
            success = await manager.connect_server(request.name)

        if not success:
            return MCPConnectResponse(
                name=request.name,
                status=MCPServerStatus.ERROR,
                transport=request.transport,
                tools_discovered=0,
                error="Failed to connect to server",
            )

        # Discover tools
        await manager.discover_tools()

        # Count tools for this server
        tools_count = sum(
            1 for key in manager.tools.keys()
            if key.startswith(f"{request.name}:")
        )

        return MCPConnectResponse(
            name=request.name,
            status=MCPServerStatus.CONNECTED,
            transport=request.transport,
            tools_discovered=tools_count,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Connection failed: {str(e)}",
        )


@router.post("/servers/{server_id}/disconnect", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_mcp_server(server_id: str):
    """
    Disconnect from an MCP server.

    Disconnects from the specified server and removes it from active connections.
    """
    manager = get_mcp_manager()
    server = manager.get_server(server_id)

    if server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server '{server_id}' not found",
        )

    success = await manager.disconnect_server(server_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect from server '{server_id}'",
        )


@router.get("/servers/{server_id}/health", response_model=MCPHealthResponse)
async def check_mcp_server_health(server_id: str):
    """
    Check health of an MCP server.

    Returns health status including latency measurement.
    """
    manager = get_mcp_manager()
    server = manager.get_server(server_id)

    if server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server '{server_id}' not found",
        )

    health_results = await manager.health_check()
    result = health_results.get(server_id)

    if result is None:
        return MCPHealthResponse(
            name=server_id,
            healthy=False,
            error="Health check failed",
        )

    return MCPHealthResponse(
        name=result.name,
        healthy=result.healthy,
        latency_ms=result.latency_ms,
        error=result.error,
    )


@router.get("/tools", response_model=MCPToolListResponse)
async def list_mcp_tools(
    server_id: Optional[str] = None,
):
    """
    List all MCP tools.

    Returns a list of all available tools from connected MCP servers.
    Optionally filter by server ID.
    """
    manager = get_mcp_manager()
    all_tools = manager.tools
    tools: List[MCPToolInfo] = []

    for key, tool_def in all_tools.items():
        # Parse server:tool format
        parts = key.split(":", 1)
        if len(parts) != 2:
            continue

        server_name, tool_name = parts

        # Filter by server
        if server_id and server_name != server_id:
            continue

        tools.append(MCPToolInfo(
            name=tool_def.name,
            description=tool_def.description,
            server_name=server_name,
            input_schema=tool_def.input_schema,
        ))

    return MCPToolListResponse(tools=tools, total=len(tools))


@router.post("/tools/execute", response_model=MCPExecuteResponse)
async def execute_mcp_tool(request: MCPExecuteRequest):
    """
    Execute an MCP tool.

    Executes a tool on the appropriate MCP server with the provided arguments.
    """
    manager = get_mcp_manager()

    # Parse tool reference
    if ":" in request.tool_ref:
        server_name, tool_name = request.tool_ref.split(":", 1)
    else:
        tool_name = request.tool_ref
        server_name = manager.find_tool_server(tool_name)
        if not server_name:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool '{tool_name}' not found on any server",
            )

    try:
        result = await manager.execute_tool(
            tool_ref=request.tool_ref,
            arguments=request.arguments,
            timeout=request.timeout,
        )

        return MCPExecuteResponse(
            tool_name=tool_name,
            server_name=server_name,
            success=result.success,
            content=result.content,
            error=result.error,
            execution_time_ms=result.execution_time_ms,
        )

    except MCPToolNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except MCPDisconnectedError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except Exception as e:
        return MCPExecuteResponse(
            tool_name=tool_name,
            server_name=server_name,
            success=False,
            error=str(e),
        )
