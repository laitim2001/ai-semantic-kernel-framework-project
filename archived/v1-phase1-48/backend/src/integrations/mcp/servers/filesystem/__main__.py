"""Filesystem MCP Server entry point.

Run with:
    python -m src.integrations.mcp.servers.filesystem

Environment variables:
    FS_ALLOWED_PATHS: Comma-separated list of allowed paths
    FS_MAX_FILE_SIZE: Maximum file size in bytes (default: 10MB)
    FS_MAX_LIST_DEPTH: Maximum directory listing depth (default: 10)
    FS_ALLOW_WRITE: Enable write operations (default: true)
    FS_ALLOW_DELETE: Enable delete operations (default: false)
    LOG_LEVEL: Logging level (default: INFO)
"""

from .server import main

if __name__ == "__main__":
    main()
