"""LDAP MCP Server entry point.

Run with:
    python -m src.integrations.mcp.servers.ldap

Environment variables:
    LDAP_SERVER: LDAP server hostname (default: localhost)
    LDAP_PORT: LDAP port (default: 389)
    LDAP_USE_SSL: Use SSL (default: false)
    LDAP_USE_TLS: Use STARTTLS (default: false)
    LDAP_BASE_DN: Base DN for searches
    LDAP_BIND_DN: DN for binding
    LDAP_BIND_PASSWORD: Password for binding
    LDAP_ALLOWED_OPS: Comma-separated allowed operations (default: search,bind)
    LDAP_READ_ONLY: Restrict to read-only (default: true)
    LDAP_TIMEOUT: Connection timeout (default: 30)
    LOG_LEVEL: Logging level (default: INFO)
"""

from .server import main

if __name__ == "__main__":
    main()
