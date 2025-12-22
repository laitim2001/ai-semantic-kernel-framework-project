"""LDAP MCP tools.

Provides tool definitions for LDAP operations.

Tools:
    - ldap_connect: Connect to LDAP server
    - ldap_search: Search LDAP directory
    - ldap_search_users: Search for users
    - ldap_search_groups: Search for groups
    - ldap_get_entry: Get specific entry by DN
    - ldap_disconnect: Disconnect from LDAP server
"""

import logging
from typing import Any, Dict, List, Optional

from ...core.types import (
    ToolSchema,
    ToolParameter,
    ToolInputType,
    ToolResult,
)
from .client import LDAPConnectionManager, LDAPConfig

logger = logging.getLogger(__name__)


class LDAPTools:
    """LDAP tools for MCP Server.

    Provides LDAP operations through the MCP protocol.

    Permission Levels:
        - ldap_connect: Level 2 (EXECUTE) - Requires approval
        - ldap_search: Level 1 (READ) - Low risk
        - ldap_search_users: Level 1 (READ) - Low risk
        - ldap_search_groups: Level 1 (READ) - Low risk
        - ldap_get_entry: Level 1 (READ) - Low risk
        - ldap_disconnect: Level 1 (READ) - Low risk

    Example:
        >>> manager = LDAPConnectionManager(config)
        >>> tools = LDAPTools(manager, config)
        >>> result = await tools.ldap_search(filter="(objectClass=user)")
    """

    PERMISSION_LEVELS = {
        "ldap_connect": 2,       # EXECUTE - requires approval
        "ldap_search": 1,        # READ - low risk
        "ldap_search_users": 1,  # READ - low risk
        "ldap_search_groups": 1, # READ - low risk
        "ldap_get_entry": 1,     # READ - low risk
        "ldap_disconnect": 1,    # READ - low risk
    }

    def __init__(self, connection_manager: LDAPConnectionManager, config: LDAPConfig):
        """Initialize LDAP tools.

        Args:
            connection_manager: LDAP connection manager
            config: LDAP configuration
        """
        self._manager = connection_manager
        self._config = config

    @staticmethod
    def get_schemas() -> List[ToolSchema]:
        """Get all LDAP tool schemas.

        Returns:
            List of ToolSchema definitions for MCP protocol
        """
        return [
            ToolSchema(
                name="ldap_connect",
                description="Connect to an LDAP server. Uses default server from configuration if not specified.",
                parameters=[
                    ToolParameter(
                        name="server",
                        type=ToolInputType.STRING,
                        description="LDAP server hostname (optional, uses config default)",
                        required=False,
                    ),
                    ToolParameter(
                        name="port",
                        type=ToolInputType.INTEGER,
                        description="LDAP port (default: 389 or 636 for SSL)",
                        required=False,
                    ),
                    ToolParameter(
                        name="bind_dn",
                        type=ToolInputType.STRING,
                        description="DN for binding (optional)",
                        required=False,
                    ),
                    ToolParameter(
                        name="bind_password",
                        type=ToolInputType.STRING,
                        description="Password for binding (optional)",
                        required=False,
                    ),
                ],
            ),
            ToolSchema(
                name="ldap_search",
                description="Search the LDAP directory with a filter.",
                parameters=[
                    ToolParameter(
                        name="filter",
                        type=ToolInputType.STRING,
                        description="LDAP search filter (e.g., '(objectClass=user)')",
                        required=True,
                    ),
                    ToolParameter(
                        name="search_base",
                        type=ToolInputType.STRING,
                        description="Base DN for search (optional, uses config default)",
                        required=False,
                    ),
                    ToolParameter(
                        name="attributes",
                        type=ToolInputType.ARRAY,
                        description="Attributes to return (default: all)",
                        required=False,
                    ),
                    ToolParameter(
                        name="scope",
                        type=ToolInputType.STRING,
                        description="Search scope: 'base', 'level', or 'subtree' (default: subtree)",
                        required=False,
                    ),
                    ToolParameter(
                        name="size_limit",
                        type=ToolInputType.INTEGER,
                        description="Maximum number of results (default: 1000)",
                        required=False,
                    ),
                ],
            ),
            ToolSchema(
                name="ldap_search_users",
                description="Search for user entries in the directory.",
                parameters=[
                    ToolParameter(
                        name="username",
                        type=ToolInputType.STRING,
                        description="Username to search (supports wildcards like 'john*')",
                        required=False,
                    ),
                    ToolParameter(
                        name="email",
                        type=ToolInputType.STRING,
                        description="Email to search (supports wildcards)",
                        required=False,
                    ),
                    ToolParameter(
                        name="attributes",
                        type=ToolInputType.ARRAY,
                        description="Attributes to return",
                        required=False,
                    ),
                ],
            ),
            ToolSchema(
                name="ldap_search_groups",
                description="Search for group entries in the directory.",
                parameters=[
                    ToolParameter(
                        name="group_name",
                        type=ToolInputType.STRING,
                        description="Group name to search (supports wildcards)",
                        required=False,
                    ),
                    ToolParameter(
                        name="attributes",
                        type=ToolInputType.ARRAY,
                        description="Attributes to return",
                        required=False,
                    ),
                ],
            ),
            ToolSchema(
                name="ldap_get_entry",
                description="Get a specific LDAP entry by its distinguished name (DN).",
                parameters=[
                    ToolParameter(
                        name="dn",
                        type=ToolInputType.STRING,
                        description="Distinguished name of the entry",
                        required=True,
                    ),
                    ToolParameter(
                        name="attributes",
                        type=ToolInputType.ARRAY,
                        description="Attributes to return (default: all)",
                        required=False,
                    ),
                ],
            ),
            ToolSchema(
                name="ldap_disconnect",
                description="Disconnect from LDAP server.",
                parameters=[],
            ),
        ]

    async def ldap_connect(
        self,
        server: Optional[str] = None,
        port: Optional[int] = None,
        bind_dn: Optional[str] = None,
        bind_password: Optional[str] = None,
    ) -> ToolResult:
        """Connect to LDAP server.

        Args:
            server: LDAP server hostname
            port: LDAP port
            bind_dn: DN for binding
            bind_password: Password for binding

        Returns:
            ToolResult with connection status
        """
        try:
            client = await self._manager.get_connection(
                server=server,
                port=port,
                bind_dn=bind_dn,
                bind_password=bind_password,
            )

            server_info = client.server_info or {}

            return ToolResult(
                success=True,
                content={
                    "server": server_info.get("host", self._config.server),
                    "port": server_info.get("port", self._config.port),
                    "ssl": server_info.get("ssl", self._config.use_ssl),
                    "connected": client.is_connected,
                    "naming_contexts": server_info.get("naming_contexts", []),
                    "message": f"Connected to LDAP server",
                },
            )

        except ImportError as e:
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )
        except ConnectionError as e:
            logger.warning(f"LDAP connection failed: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )
        except Exception as e:
            logger.error(f"LDAP connection error: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Connection error: {e}",
            )

    async def ldap_search(
        self,
        filter: str,
        search_base: Optional[str] = None,
        attributes: Optional[List[str]] = None,
        scope: str = "subtree",
        size_limit: int = 1000,
    ) -> ToolResult:
        """Search LDAP directory.

        Args:
            filter: LDAP search filter
            search_base: Base DN for search
            attributes: Attributes to return
            scope: Search scope
            size_limit: Maximum results

        Returns:
            ToolResult with search results
        """
        try:
            # Get connection (create if needed with default config)
            client = await self._manager.get_connection()

            result = await client.search(
                search_filter=filter,
                search_base=search_base,
                attributes=attributes,
                scope=scope,
                size_limit=size_limit,
            )

            return ToolResult(
                success=True,
                content={
                    "filter": filter,
                    "scope": scope,
                    "count": result.total_count,
                    "search_time": round(result.search_time, 3),
                    "entries": result.entries,
                },
            )

        except (ValueError, ConnectionError) as e:
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )
        except Exception as e:
            logger.error(f"LDAP search error: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Search error: {e}",
            )

    async def ldap_search_users(
        self,
        username: Optional[str] = None,
        email: Optional[str] = None,
        attributes: Optional[List[str]] = None,
    ) -> ToolResult:
        """Search for users.

        Args:
            username: Username to search
            email: Email to search
            attributes: Attributes to return

        Returns:
            ToolResult with user entries
        """
        try:
            client = await self._manager.get_connection()

            result = await client.search_users(
                username=username,
                email=email,
                attributes=attributes,
            )

            return ToolResult(
                success=True,
                content={
                    "username_filter": username,
                    "email_filter": email,
                    "count": result.total_count,
                    "search_time": round(result.search_time, 3),
                    "users": result.entries,
                },
            )

        except (ValueError, ConnectionError) as e:
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )
        except Exception as e:
            logger.error(f"LDAP user search error: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"User search error: {e}",
            )

    async def ldap_search_groups(
        self,
        group_name: Optional[str] = None,
        attributes: Optional[List[str]] = None,
    ) -> ToolResult:
        """Search for groups.

        Args:
            group_name: Group name to search
            attributes: Attributes to return

        Returns:
            ToolResult with group entries
        """
        try:
            client = await self._manager.get_connection()

            result = await client.search_groups(
                group_name=group_name,
                attributes=attributes,
            )

            return ToolResult(
                success=True,
                content={
                    "group_filter": group_name,
                    "count": result.total_count,
                    "search_time": round(result.search_time, 3),
                    "groups": result.entries,
                },
            )

        except (ValueError, ConnectionError) as e:
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )
        except Exception as e:
            logger.error(f"LDAP group search error: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Group search error: {e}",
            )

    async def ldap_get_entry(
        self,
        dn: str,
        attributes: Optional[List[str]] = None,
    ) -> ToolResult:
        """Get specific entry by DN.

        Args:
            dn: Distinguished name
            attributes: Attributes to return

        Returns:
            ToolResult with entry data
        """
        try:
            client = await self._manager.get_connection()

            entry = await client.get_entry(
                dn=dn,
                attributes=attributes,
            )

            if entry:
                return ToolResult(
                    success=True,
                    content={
                        "dn": dn,
                        "entry": entry,
                    },
                )
            else:
                return ToolResult(
                    success=False,
                    content=None,
                    error=f"Entry not found: {dn}",
                )

        except (ValueError, ConnectionError) as e:
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )
        except Exception as e:
            logger.error(f"LDAP get entry error: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Get entry error: {e}",
            )

    async def ldap_disconnect(self) -> ToolResult:
        """Disconnect from LDAP server.

        Returns:
            ToolResult with disconnection status
        """
        try:
            await self._manager.close_all()

            return ToolResult(
                success=True,
                content={
                    "message": "Disconnected from all LDAP servers",
                },
            )

        except Exception as e:
            logger.error(f"LDAP disconnect error: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Disconnect error: {e}",
            )
