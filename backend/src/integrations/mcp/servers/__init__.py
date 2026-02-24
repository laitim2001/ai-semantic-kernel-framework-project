"""MCP Servers Module.

This module contains implementations of MCP servers for various integrations.

Available Servers:
    - azure: Azure cloud resource management
    - n8n: n8n workflow automation (Sprint 124)
"""

from .azure import AzureMCPServer, AzureClientManager, AzureConfig
from .n8n import N8nMCPServer, N8nApiClient, N8nConfig

__all__ = [
    "AzureMCPServer",
    "AzureClientManager",
    "AzureConfig",
    "N8nMCPServer",
    "N8nApiClient",
    "N8nConfig",
]
