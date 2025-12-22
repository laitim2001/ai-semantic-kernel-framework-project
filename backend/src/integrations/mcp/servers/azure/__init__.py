"""Azure MCP Server Module.

Provides MCP server implementation for Azure cloud resource management.

This module enables AI agents to:
    - Query VM status and metrics
    - Execute basic resource management operations
    - Collect logs and diagnostic information
    - Monitor resource health status

Example:
    >>> from integrations.mcp.servers.azure import AzureMCPServer, AzureConfig
    >>> config = AzureConfig(subscription_id="xxx")
    >>> server = AzureMCPServer(config)
    >>> await server.run()
"""

from .client import AzureClientManager, AzureConfig
from .server import AzureMCPServer

__all__ = [
    "AzureClientManager",
    "AzureConfig",
    "AzureMCPServer",
]
