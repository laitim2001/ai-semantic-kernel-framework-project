"""Shell MCP Server entry point.

Run with:
    python -m src.integrations.mcp.servers.shell

Environment variables:
    SHELL_TYPE: powershell, bash, or cmd (default: auto-detect)
    SHELL_TIMEOUT: Timeout in seconds (default: 60)
    SHELL_MAX_OUTPUT: Max output size in bytes (default: 1MB)
    SHELL_WORKING_DIR: Working directory (optional)
    LOG_LEVEL: Logging level (default: INFO)
"""

from .server import main

if __name__ == "__main__":
    main()
