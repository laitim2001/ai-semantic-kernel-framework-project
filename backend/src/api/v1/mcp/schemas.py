"""MCP API Schemas.

Pydantic models for MCP API request/response validation.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ServerConfigRequest(BaseModel):
    """Request to register/update an MCP server configuration."""

    name: str = Field(..., min_length=1, max_length=64, description="Unique server identifier")
    command: str = Field(..., min_length=1, description="Command to execute")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    transport: str = Field(default="stdio", description="Transport type")
    timeout: float = Field(default=30.0, ge=1.0, le=300.0, description="Timeout in seconds")
    enabled: bool = Field(default=True, description="Auto-connect on startup")
    cwd: Optional[str] = Field(default=None, description="Working directory")
    description: Optional[str] = Field(default=None, max_length=256, description="Server description")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")

    class Config:
        schema_extra = {
            "example": {
                "name": "azure-mcp",
                "command": "python",
                "args": ["-m", "mcp_servers.azure"],
                "env": {"AZURE_SUBSCRIPTION_ID": "xxx"},
                "enabled": True,
                "timeout": 30.0,
                "description": "Azure MCP Server",
                "tags": ["azure", "cloud"],
            }
        }


class ServerConfigResponse(BaseModel):
    """Response for server configuration."""

    name: str
    command: str
    args: List[str]
    env: Dict[str, str]
    transport: str
    timeout: float
    enabled: bool
    cwd: Optional[str]
    description: Optional[str]
    tags: List[str]


class ServerStatusResponse(BaseModel):
    """Response for server status."""

    name: str
    status: str
    enabled: bool
    tools_count: int
    last_connected: Optional[datetime]
    last_error: Optional[str]
    retry_count: int


class RegistrySummaryResponse(BaseModel):
    """Response for registry summary."""

    total_servers: int
    status_counts: Dict[str, int]
    total_tools: int
    servers: List[ServerStatusResponse]


class ToolParameterSchema(BaseModel):
    """Tool parameter schema."""

    name: str
    type: str
    description: str
    required: bool
    default: Optional[Any] = None
    enum: Optional[List[str]] = None


class ToolSchemaResponse(BaseModel):
    """Response for tool schema."""

    name: str
    description: str
    server: str
    parameters: List[ToolParameterSchema]


class ToolListResponse(BaseModel):
    """Response for tool list."""

    tools: List[ToolSchemaResponse]
    total: int


class ToolExecutionRequest(BaseModel):
    """Request to execute a tool."""

    tool_name: str = Field(..., min_length=1, description="Name of tool to execute")
    server_name: Optional[str] = Field(default=None, description="Specific server (auto-detected if not provided)")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")

    class Config:
        schema_extra = {
            "example": {
                "tool_name": "list_vms",
                "server_name": "azure-mcp",
                "arguments": {"resource_group": "prod-rg"},
            }
        }


class ToolExecutionResponse(BaseModel):
    """Response for tool execution."""

    success: bool
    content: Optional[Any]
    error: Optional[str]
    server: str
    tool: str
    duration_ms: Optional[float]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AuditEventResponse(BaseModel):
    """Response for audit event."""

    event_id: str
    event_type: str
    timestamp: datetime
    user_id: Optional[str]
    server: Optional[str]
    tool: Optional[str]
    status: str
    result: Optional[str]
    duration_ms: Optional[float]


class AuditQueryRequest(BaseModel):
    """Request for querying audit events."""

    user_id: Optional[str] = None
    server: Optional[str] = None
    tool: Optional[str] = None
    event_types: Optional[List[str]] = None
    status: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class AuditQueryResponse(BaseModel):
    """Response for audit query."""

    events: List[AuditEventResponse]
    total: int


class ConnectionRequest(BaseModel):
    """Request to connect/disconnect a server."""

    server_name: str = Field(..., description="Server name to connect/disconnect")


class ConnectionResponse(BaseModel):
    """Response for connection operation."""

    server_name: str
    status: str
    success: bool
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
