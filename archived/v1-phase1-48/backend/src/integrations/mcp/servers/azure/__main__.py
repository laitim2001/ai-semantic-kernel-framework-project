"""Azure MCP Server entry point.

Run with:
    python -m src.integrations.mcp.servers.azure

Environment variables:
    AZURE_SUBSCRIPTION_ID: Azure subscription ID (required)
    AZURE_TENANT_ID: Azure AD tenant ID (optional)
    AZURE_CLIENT_ID: Azure AD application client ID (optional)
    AZURE_CLIENT_SECRET: Azure AD application client secret (optional)
    LOG_LEVEL: Logging level (default: INFO)
"""

from .server import main

if __name__ == "__main__":
    main()
