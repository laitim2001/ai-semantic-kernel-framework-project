"""Filesystem MCP Server.

Provides secure filesystem operations for AI agents.

Features:
    - Sandboxed file access (configurable allowed paths)
    - Read, write, list, search operations
    - Size limits and path validation
    - Permission-based access control

Usage:
    python -m src.integrations.mcp.servers.filesystem

Security:
    All operations are sandboxed to allowed directories.
    Sensitive file patterns are blocked by default.
"""

from .sandbox import FilesystemSandbox, SandboxConfig
from .server import FilesystemMCPServer

__all__ = [
    "FilesystemSandbox",
    "SandboxConfig",
    "FilesystemMCPServer",
]
