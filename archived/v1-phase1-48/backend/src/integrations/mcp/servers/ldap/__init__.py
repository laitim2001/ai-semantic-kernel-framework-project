"""LDAP MCP Server.

Provides secure LDAP operations for AI agents.

Features:
    - LDAP/Active Directory queries
    - User and group management
    - Directory search operations
    - Secure bind with TLS support

Usage:
    python -m src.integrations.mcp.servers.ldap

Security:
    Credentials are handled securely.
    Read-only operations by default.
"""

from .client import LDAPClient, LDAPConfig, LDAPConnectionManager
from .server import LDAPMCPServer
from .ad_config import ADConfig
from .ad_operations import ADOperations, ADOperationResult

__all__ = [
    "LDAPClient",
    "LDAPConfig",
    "LDAPConnectionManager",
    "LDAPMCPServer",
    # Sprint 114: AD Account Management
    "ADConfig",
    "ADOperations",
    "ADOperationResult",
]
