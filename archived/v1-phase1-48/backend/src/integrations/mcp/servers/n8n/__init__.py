"""n8n MCP Server Module.

Provides MCP integration with n8n workflow automation platform.

Modes:
    - Mode 1 (IPA → n8n): IPA Agent triggers n8n workflows via MCP tools
    - Mode 2 (n8n → IPA): n8n workflows call IPA API via webhooks

Components:
    - N8nMCPServer: MCP protocol handler with 6 tools
    - N8nApiClient: n8n REST API wrapper with retry logic
    - N8nConfig: Connection configuration from environment variables

Example:
    >>> from integrations.mcp.servers.n8n import N8nMCPServer, N8nConfig
    >>> config = N8nConfig.from_env()
    >>> server = N8nMCPServer(config)
    >>> tools = server.get_tools()
"""

from .client import N8nApiClient, N8nConfig
from .server import N8nMCPServer

__all__ = [
    "N8nMCPServer",
    "N8nApiClient",
    "N8nConfig",
]
