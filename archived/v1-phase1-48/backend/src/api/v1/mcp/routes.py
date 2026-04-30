"""MCP API Routes.

REST API endpoints for MCP server management, tool discovery,
and execution.

Endpoints:
    GET     /api/v1/mcp/servers                 - List all registered servers
    POST    /api/v1/mcp/servers                 - Register a new server
    GET     /api/v1/mcp/servers/{name}          - Get server details
    DELETE  /api/v1/mcp/servers/{name}          - Unregister a server
    POST    /api/v1/mcp/servers/{name}/connect  - Connect to a server
    POST    /api/v1/mcp/servers/{name}/disconnect - Disconnect from a server
    GET     /api/v1/mcp/servers/{name}/tools    - List tools for a server
    GET     /api/v1/mcp/tools                   - List all available tools
    POST    /api/v1/mcp/tools/execute           - Execute a tool
    GET     /api/v1/mcp/status                  - Get registry status summary
    GET     /api/v1/mcp/audit                   - Query audit logs
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import datetime
import logging
import time

from .schemas import (
    ServerConfigRequest,
    ServerConfigResponse,
    ServerStatusResponse,
    RegistrySummaryResponse,
    ToolSchemaResponse,
    ToolListResponse,
    ToolParameterSchema,
    ToolExecutionRequest,
    ToolExecutionResponse,
    ConnectionRequest,
    ConnectionResponse,
    AuditQueryRequest,
    AuditQueryResponse,
    AuditEventResponse,
    ErrorResponse,
)
from ....integrations.mcp.registry import (
    ServerRegistry,
    RegisteredServer,
    ServerStatus,
    ConfigLoader,
)
from ....integrations.mcp.security import (
    PermissionManager,
    PermissionLevel,
    AuditLogger,
    AuditEventType,
    AuditFilter,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["MCP"])

# Global instances (should be managed by dependency injection in production)
_registry: Optional[ServerRegistry] = None
_permission_manager: Optional[PermissionManager] = None
_audit_logger: Optional[AuditLogger] = None


def get_registry() -> ServerRegistry:
    """Get the global registry instance."""
    global _registry
    if _registry is None:
        _registry = ServerRegistry()
    return _registry


def get_permission_manager() -> PermissionManager:
    """Get the global permission manager instance."""
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


# =============================================================================
# Server Management Endpoints
# =============================================================================


@router.get(
    "/servers",
    response_model=List[ServerStatusResponse],
    summary="List all registered servers",
)
async def list_servers(
    registry: ServerRegistry = Depends(get_registry),
) -> List[ServerStatusResponse]:
    """List all registered MCP servers with their current status."""
    servers = registry.servers

    return [
        ServerStatusResponse(
            name=server.name,
            status=server.status.value,
            enabled=server.enabled,
            tools_count=len(server.tools),
            last_connected=server.last_connected,
            last_error=server.last_error,
            retry_count=server.retry_count,
        )
        for server in servers.values()
    ]


@router.post(
    "/servers",
    response_model=ServerStatusResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new server",
)
async def register_server(
    config: ServerConfigRequest,
    registry: ServerRegistry = Depends(get_registry),
    audit: AuditLogger = Depends(get_audit_logger),
) -> ServerStatusResponse:
    """Register a new MCP server configuration."""
    # Check if already exists
    if config.name in registry.servers:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Server already registered: {config.name}",
        )

    server = RegisteredServer(
        name=config.name,
        command=config.command,
        args=config.args,
        env=config.env,
        transport=config.transport,
        timeout=config.timeout,
        enabled=config.enabled,
        cwd=config.cwd,
    )

    success = await registry.register(server)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register server",
        )

    # Log audit event
    await audit.log_server_event(
        event_type=AuditEventType.CONFIG_CHANGE,
        server=config.name,
        status="success",
        metadata={"action": "register"},
    )

    return ServerStatusResponse(
        name=server.name,
        status=server.status.value,
        enabled=server.enabled,
        tools_count=0,
        last_connected=None,
        last_error=None,
        retry_count=0,
    )


@router.get(
    "/servers/{server_name}",
    response_model=ServerStatusResponse,
    summary="Get server details",
)
async def get_server(
    server_name: str,
    registry: ServerRegistry = Depends(get_registry),
) -> ServerStatusResponse:
    """Get details for a specific registered server."""
    server = registry.get_server(server_name)

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server not found: {server_name}",
        )

    return ServerStatusResponse(
        name=server.name,
        status=server.status.value,
        enabled=server.enabled,
        tools_count=len(server.tools),
        last_connected=server.last_connected,
        last_error=server.last_error,
        retry_count=server.retry_count,
    )


@router.delete(
    "/servers/{server_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unregister a server",
)
async def unregister_server(
    server_name: str,
    registry: ServerRegistry = Depends(get_registry),
    audit: AuditLogger = Depends(get_audit_logger),
) -> None:
    """Unregister an MCP server (disconnects if connected)."""
    if server_name not in registry.servers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server not found: {server_name}",
        )

    success = await registry.unregister(server_name)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unregister server",
        )

    # Log audit event
    await audit.log_server_event(
        event_type=AuditEventType.CONFIG_CHANGE,
        server=server_name,
        status="success",
        metadata={"action": "unregister"},
    )


@router.post(
    "/servers/{server_name}/connect",
    response_model=ConnectionResponse,
    summary="Connect to a server",
)
async def connect_server(
    server_name: str,
    registry: ServerRegistry = Depends(get_registry),
    audit: AuditLogger = Depends(get_audit_logger),
) -> ConnectionResponse:
    """Connect to a registered MCP server."""
    server = registry.get_server(server_name)

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server not found: {server_name}",
        )

    success = await registry.connect(server_name)

    # Log audit event
    await audit.log_server_event(
        event_type=AuditEventType.SERVER_CONNECT,
        server=server_name,
        status="success" if success else "failure",
        error=server.last_error if not success else None,
    )

    return ConnectionResponse(
        server_name=server_name,
        status=server.status.value,
        success=success,
        message=server.last_error if not success else None,
    )


@router.post(
    "/servers/{server_name}/disconnect",
    response_model=ConnectionResponse,
    summary="Disconnect from a server",
)
async def disconnect_server(
    server_name: str,
    registry: ServerRegistry = Depends(get_registry),
    audit: AuditLogger = Depends(get_audit_logger),
) -> ConnectionResponse:
    """Disconnect from a connected MCP server."""
    server = registry.get_server(server_name)

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server not found: {server_name}",
        )

    success = await registry.disconnect(server_name)

    # Log audit event
    await audit.log_server_event(
        event_type=AuditEventType.SERVER_DISCONNECT,
        server=server_name,
        status="success" if success else "failure",
    )

    return ConnectionResponse(
        server_name=server_name,
        status=server.status.value,
        success=success,
    )


# =============================================================================
# Tool Discovery Endpoints
# =============================================================================


@router.get(
    "/servers/{server_name}/tools",
    response_model=ToolListResponse,
    summary="List tools for a server",
)
async def list_server_tools(
    server_name: str,
    registry: ServerRegistry = Depends(get_registry),
) -> ToolListResponse:
    """List all available tools for a specific server."""
    server = registry.get_server(server_name)

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server not found: {server_name}",
        )

    if server.status != ServerStatus.CONNECTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Server not connected: {server_name}",
        )

    tools = []
    for tool in server.tools:
        params = [
            ToolParameterSchema(
                name=p.name,
                type=p.type.value,
                description=p.description,
                required=p.required,
                default=p.default,
                enum=p.enum,
            )
            for p in tool.parameters
        ]

        tools.append(
            ToolSchemaResponse(
                name=tool.name,
                description=tool.description,
                server=server_name,
                parameters=params,
            )
        )

    return ToolListResponse(tools=tools, total=len(tools))


@router.get(
    "/tools",
    response_model=ToolListResponse,
    summary="List all available tools",
)
async def list_all_tools(
    registry: ServerRegistry = Depends(get_registry),
) -> ToolListResponse:
    """List all available tools from all connected servers."""
    all_tools = registry.get_all_tools()

    tools = []
    for server_name, server_tools in all_tools.items():
        for tool in server_tools:
            params = [
                ToolParameterSchema(
                    name=p.name,
                    type=p.type.value,
                    description=p.description,
                    required=p.required,
                    default=p.default,
                    enum=p.enum,
                )
                for p in tool.parameters
            ]

            tools.append(
                ToolSchemaResponse(
                    name=tool.name,
                    description=tool.description,
                    server=server_name,
                    parameters=params,
                )
            )

    return ToolListResponse(tools=tools, total=len(tools))


# =============================================================================
# Tool Execution Endpoint
# =============================================================================


@router.post(
    "/tools/execute",
    response_model=ToolExecutionResponse,
    summary="Execute a tool",
)
async def execute_tool(
    request: ToolExecutionRequest,
    user_id: str = Query(default="anonymous", description="User ID for audit"),
    registry: ServerRegistry = Depends(get_registry),
    permissions: PermissionManager = Depends(get_permission_manager),
    audit: AuditLogger = Depends(get_audit_logger),
) -> ToolExecutionResponse:
    """Execute a tool on a connected MCP server."""
    # Determine target server
    target_server = request.server_name

    if not target_server:
        # Find server with this tool
        schema = registry.find_tool(request.tool_name)
        if schema:
            # Find which server has this tool
            for name, tools in registry.get_all_tools().items():
                if any(t.name == request.tool_name for t in tools):
                    target_server = name
                    break

    if not target_server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool not found: {request.tool_name}",
        )

    # Check permissions
    allowed = permissions.check_permission(
        user_id=user_id,
        server=target_server,
        tool=request.tool_name,
        level=PermissionLevel.EXECUTE,
    )

    if not allowed:
        # Log access denied
        await audit.log_access(
            user_id=user_id,
            server=target_server,
            tool=request.tool_name,
            granted=False,
            reason="Permission denied",
        )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied for tool execution",
        )

    # Execute the tool
    start_time = time.time()

    result = await registry.call_tool(
        tool_name=request.tool_name,
        arguments=request.arguments,
        server_name=target_server,
    )

    duration_ms = (time.time() - start_time) * 1000

    # Log audit event
    await audit.log_tool_execution(
        user_id=user_id,
        server=target_server,
        tool=request.tool_name,
        arguments=request.arguments,
        status="success" if result.success else "failure",
        result=str(result.content)[:200] if result.content else None,
        duration_ms=duration_ms,
    )

    return ToolExecutionResponse(
        success=result.success,
        content=result.content,
        error=result.error,
        server=target_server,
        tool=request.tool_name,
        duration_ms=duration_ms,
        metadata=result.metadata,
    )


# =============================================================================
# Status and Audit Endpoints
# =============================================================================


@router.get(
    "/status",
    response_model=RegistrySummaryResponse,
    summary="Get registry status summary",
)
async def get_status(
    registry: ServerRegistry = Depends(get_registry),
) -> RegistrySummaryResponse:
    """Get a summary of all server statuses and tool counts."""
    summary = registry.get_status_summary()

    servers = [
        ServerStatusResponse(
            name=s["name"],
            status=s["status"],
            enabled=s["enabled"],
            tools_count=s["tools_count"],
            last_connected=(
                datetime.fromisoformat(s["last_connected"])
                if s["last_connected"]
                else None
            ),
            last_error=s["last_error"],
            retry_count=s["retry_count"],
        )
        for s in summary["servers"]
    ]

    return RegistrySummaryResponse(
        total_servers=summary["total_servers"],
        status_counts=summary["status_counts"],
        total_tools=summary["total_tools"],
        servers=servers,
    )


@router.get(
    "/audit",
    response_model=AuditQueryResponse,
    summary="Query audit logs",
)
async def query_audit(
    user_id: Optional[str] = None,
    server: Optional[str] = None,
    tool: Optional[str] = None,
    event_type: Optional[str] = None,
    status: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    audit: AuditLogger = Depends(get_audit_logger),
) -> AuditQueryResponse:
    """Query audit events with filters."""
    event_types = None
    if event_type:
        try:
            event_types = [AuditEventType(event_type)]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event type: {event_type}",
            )

    filter = AuditFilter(
        user_id=user_id,
        server=server,
        tool=tool,
        event_types=event_types,
        status=status,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )

    events = await audit.query(filter)

    event_responses = [
        AuditEventResponse(
            event_id=e.event_id,
            event_type=e.event_type.value,
            timestamp=e.timestamp,
            user_id=e.user_id,
            server=e.server,
            tool=e.tool,
            status=e.status,
            result=e.result,
            duration_ms=e.duration_ms,
        )
        for e in events
    ]

    return AuditQueryResponse(
        events=event_responses,
        total=len(event_responses),
    )


@router.post(
    "/connect-all",
    response_model=Dict[str, bool],
    summary="Connect to all enabled servers",
)
async def connect_all_servers(
    registry: ServerRegistry = Depends(get_registry),
    audit: AuditLogger = Depends(get_audit_logger),
) -> Dict[str, bool]:
    """Connect to all enabled registered servers."""
    results = await registry.connect_all()

    # Log system event
    await audit.log_server_event(
        event_type=AuditEventType.SYSTEM_START,
        server="*",
        status="success",
        metadata={"connected_count": sum(results.values())},
    )

    return results


@router.post(
    "/disconnect-all",
    response_model=Dict[str, bool],
    summary="Disconnect from all servers",
)
async def disconnect_all_servers(
    registry: ServerRegistry = Depends(get_registry),
    audit: AuditLogger = Depends(get_audit_logger),
) -> Dict[str, bool]:
    """Disconnect from all connected servers."""
    results = await registry.disconnect_all()

    # Log system event
    await audit.log_server_event(
        event_type=AuditEventType.SYSTEM_SHUTDOWN,
        server="*",
        status="success",
    )

    return results
