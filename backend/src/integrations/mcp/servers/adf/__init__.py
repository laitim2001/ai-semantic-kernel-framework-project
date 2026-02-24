"""Azure Data Factory MCP Server Module.

Provides MCP integration with Azure Data Factory for ETL pipeline management.

Sprint 125: Azure Data Factory MCP Server

Components:
    - AdfMCPServer: MCP protocol handler with 8 tools
    - AdfApiClient: Azure Data Factory REST API wrapper
    - AdfConfig: Connection configuration from environment variables

Example:
    >>> from integrations.mcp.servers.adf import AdfMCPServer, AdfConfig
    >>> config = AdfConfig.from_env()
    >>> server = AdfMCPServer(config)
    >>> tools = server.get_tools()
"""

from .client import AdfApiClient, AdfConfig
from .server import AdfMCPServer

__all__ = [
    "AdfMCPServer",
    "AdfApiClient",
    "AdfConfig",
]
