"""MCP Servers Module.

This module contains implementations of MCP servers for various integrations.

Available Servers:
    - azure: Azure cloud resource management
    - n8n: n8n workflow automation (Sprint 124)
    - adf: Azure Data Factory pipeline management (Sprint 125)
    - d365: Dynamics 365 entity management (Sprint 129)
"""

from .azure import AzureMCPServer, AzureClientManager, AzureConfig
from .n8n import N8nMCPServer, N8nApiClient, N8nConfig
from .adf import AdfMCPServer, AdfApiClient, AdfConfig
from .d365 import D365MCPServer, D365ApiClient, D365Config

__all__ = [
    "AzureMCPServer",
    "AzureClientManager",
    "AzureConfig",
    "N8nMCPServer",
    "N8nApiClient",
    "N8nConfig",
    "AdfMCPServer",
    "AdfApiClient",
    "AdfConfig",
    "D365MCPServer",
    "D365ApiClient",
    "D365Config",
]
