"""MCP (Model Context Protocol) Integration Module.

This module provides the core infrastructure for MCP-based tool execution,
enabling standardized communication between AI agents and external tools.

Architecture:
    - core/: Core protocol implementation (types, protocol, transport, client)
    - registry/: Server registration and discovery
    - security/: Permissions and audit logging

Example:
    >>> from integrations.mcp import MCPClient, ServerConfig, ServerRegistry
    >>> registry = ServerRegistry()
    >>> await registry.register(RegisteredServer(
    ...     name="azure-mcp",
    ...     command="python",
    ...     args=["-m", "mcp_servers.azure"],
    ... ))
    >>> await registry.connect_all()
    >>> tools = registry.get_all_tools()
    >>> result = await registry.call_tool("list_vms", {"resource_group": "prod-rg"})
"""

# Core types and protocol
from .core.types import (
    ToolInputType,
    ToolParameter,
    ToolSchema,
    ToolResult,
    MCPRequest,
    MCPResponse,
)
from .core.protocol import MCPProtocol
from .core.transport import BaseTransport, StdioTransport, InMemoryTransport
from .core.client import MCPClient, ServerConfig

# Registry
from .registry.server_registry import (
    ServerRegistry,
    ServerStatus,
    RegisteredServer,
)
from .registry.config_loader import ConfigLoader, ServerDefinition

# Security
from .security.permissions import (
    Permission,
    PermissionLevel,
    PermissionPolicy,
    PermissionManager,
)
from .security.audit import (
    AuditEvent,
    AuditEventType,
    AuditLogger,
    AuditFilter,
    AuditStorage,
    InMemoryAuditStorage,
    FileAuditStorage,
)

__all__ = [
    # Core Types
    "ToolInputType",
    "ToolParameter",
    "ToolSchema",
    "ToolResult",
    "MCPRequest",
    "MCPResponse",
    # Protocol
    "MCPProtocol",
    # Transport
    "BaseTransport",
    "StdioTransport",
    "InMemoryTransport",
    # Client
    "MCPClient",
    "ServerConfig",
    # Registry
    "ServerRegistry",
    "ServerStatus",
    "RegisteredServer",
    "ConfigLoader",
    "ServerDefinition",
    # Permissions
    "Permission",
    "PermissionLevel",
    "PermissionPolicy",
    "PermissionManager",
    # Audit
    "AuditEvent",
    "AuditEventType",
    "AuditLogger",
    "AuditFilter",
    "AuditStorage",
    "InMemoryAuditStorage",
    "FileAuditStorage",
]
