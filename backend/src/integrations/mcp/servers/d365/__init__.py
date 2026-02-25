"""Dynamics 365 MCP Server Module.

Provides MCP integration with Dynamics 365 for entity CRUD operations,
OData queries, and metadata discovery.

Sprint 129: D365 MCP Server

Components:
    - D365MCPServer: MCP protocol handler with 6 tools
    - D365ApiClient: Dynamics 365 Web API wrapper (OData v4)
    - D365Config: Connection configuration from environment variables

Example:
    >>> from integrations.mcp.servers.d365 import D365MCPServer, D365Config
    >>> config = D365Config.from_env()
    >>> server = D365MCPServer(config)
    >>> tools = server.get_tools()
"""

from .client import D365ApiClient, D365Config
from .server import D365MCPServer

__all__ = [
    "D365MCPServer",
    "D365ApiClient",
    "D365Config",
]
