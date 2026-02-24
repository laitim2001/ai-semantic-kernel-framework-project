"""n8n MCP Server entry point.

Allows running the server as a module:
    python -m src.integrations.mcp.servers.n8n

Environment Variables:
    N8N_BASE_URL: n8n instance URL (default: http://localhost:5678)
    N8N_API_KEY: n8n API key (required)
    N8N_TIMEOUT: Request timeout in seconds (default: 30)
    N8N_MAX_RETRIES: Max retry attempts (default: 3)
    LOG_LEVEL: Logging level (default: INFO)
"""

from .server import main

if __name__ == "__main__":
    main()
