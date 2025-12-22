"""Shell MCP Server.

Provides secure shell command execution capabilities for AI agents.

Features:
    - PowerShell (Windows) and Bash (Linux) support
    - Command whitelist/blacklist mechanism
    - Timeout control
    - Output size limiting
    - Working directory isolation

Usage:
    python -m src.integrations.mcp.servers.shell

Security:
    All commands are validated against blacklist patterns.
    Dangerous operations require human approval.
"""

from .executor import ShellExecutor, ShellConfig, ShellType, CommandResult
from .server import ShellMCPServer

__all__ = [
    "ShellExecutor",
    "ShellConfig",
    "ShellType",
    "CommandResult",
    "ShellMCPServer",
]
