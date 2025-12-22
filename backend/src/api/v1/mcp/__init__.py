"""MCP API Module.

REST API endpoints for MCP server management.
"""

from .routes import router
from .schemas import (
    ServerConfigRequest,
    ServerConfigResponse,
    ServerStatusResponse,
    ToolExecutionRequest,
    ToolExecutionResponse,
    ToolSchemaResponse,
)

__all__ = [
    "router",
    "ServerConfigRequest",
    "ServerConfigResponse",
    "ServerStatusResponse",
    "ToolExecutionRequest",
    "ToolExecutionResponse",
    "ToolSchemaResponse",
]
