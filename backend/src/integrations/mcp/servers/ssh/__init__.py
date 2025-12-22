"""SSH MCP Server.

Provides secure SSH operations for AI agents.

Features:
    - SSH connection management with connection pool
    - Remote command execution
    - SFTP file transfer
    - Key-based and password authentication
    - Host key verification

Usage:
    python -m src.integrations.mcp.servers.ssh

Security:
    All connections require explicit host configuration.
    Private keys and passwords are handled securely.
"""

from .client import SSHClient, SSHConfig, SSHConnectionManager
from .server import SSHMCPServer

__all__ = [
    "SSHClient",
    "SSHConfig",
    "SSHConnectionManager",
    "SSHMCPServer",
]
