"""SSH MCP Server entry point.

Run with:
    python -m src.integrations.mcp.servers.ssh

Environment variables:
    SSH_ALLOWED_HOSTS: Comma-separated list of allowed hosts
    SSH_BLOCKED_HOSTS: Comma-separated list of blocked hosts
    SSH_DEFAULT_TIMEOUT: Default connection timeout (default: 30)
    SSH_COMMAND_TIMEOUT: Default command timeout (default: 60)
    SSH_MAX_CONNECTIONS: Maximum connections per host (default: 5)
    SSH_AUTO_ADD_KEYS: Auto-add unknown host keys (default: false)
    SSH_PRIVATE_KEY_PATH: Path to default private key
    SSH_KNOWN_HOSTS_FILE: Path to known_hosts file
    LOG_LEVEL: Logging level (default: INFO)
"""

from .server import main

if __name__ == "__main__":
    main()
