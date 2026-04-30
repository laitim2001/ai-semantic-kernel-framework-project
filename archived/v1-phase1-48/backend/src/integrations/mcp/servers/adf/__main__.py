"""Azure Data Factory MCP Server entry point.

Run with:
    python -m src.integrations.mcp.servers.adf
"""

from .server import main

if __name__ == "__main__":
    main()
