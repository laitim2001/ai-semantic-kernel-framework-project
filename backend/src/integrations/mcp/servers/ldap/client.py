"""LDAP client with connection management.

Provides secure LDAP operations with:
- Connection pooling
- TLS/SSL support
- User/group search
- Directory modifications
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Optional ldap3 import
try:
    from ldap3 import (
        Server,
        Connection,
        ALL,
        SUBTREE,
        LEVEL,
        BASE,
        MODIFY_ADD,
        MODIFY_DELETE,
        MODIFY_REPLACE,
        Tls,
    )
    from ldap3.core.exceptions import LDAPException
    import ssl
    HAS_LDAP3 = True
except ImportError:
    HAS_LDAP3 = False
    Server = None
    Connection = None


@dataclass
class LDAPConfig:
    """LDAP configuration.

    Attributes:
        server: LDAP server hostname
        port: LDAP port (389 for LDAP, 636 for LDAPS)
        use_ssl: Use SSL/TLS
        use_tls: Use STARTTLS
        base_dn: Base DN for searches
        bind_dn: DN for binding (authentication)
        bind_password: Password for binding
        allowed_operations: List of allowed operations
        read_only: Restrict to read-only operations
        timeout: Connection timeout
    """

    server: str = "localhost"
    port: int = 389
    use_ssl: bool = False
    use_tls: bool = False
    base_dn: str = ""
    bind_dn: Optional[str] = None
    bind_password: Optional[str] = None
    allowed_operations: List[str] = field(default_factory=lambda: ["search", "bind"])
    read_only: bool = True
    timeout: int = 30

    @classmethod
    def from_env(cls) -> "LDAPConfig":
        """Create config from environment variables.

        Environment variables:
            LDAP_SERVER: LDAP server hostname
            LDAP_PORT: LDAP port
            LDAP_USE_SSL: Use SSL (true/false)
            LDAP_USE_TLS: Use STARTTLS (true/false)
            LDAP_BASE_DN: Base DN for searches
            LDAP_BIND_DN: DN for binding
            LDAP_BIND_PASSWORD: Password for binding
            LDAP_ALLOWED_OPS: Comma-separated list of allowed operations
            LDAP_READ_ONLY: Restrict to read-only (default: true)
            LDAP_TIMEOUT: Connection timeout
        """
        ops_str = os.environ.get("LDAP_ALLOWED_OPS", "search,bind")
        allowed_ops = [op.strip() for op in ops_str.split(",") if op.strip()]

        return cls(
            server=os.environ.get("LDAP_SERVER", "localhost"),
            port=int(os.environ.get("LDAP_PORT", "389")),
            use_ssl=os.environ.get("LDAP_USE_SSL", "false").lower() == "true",
            use_tls=os.environ.get("LDAP_USE_TLS", "false").lower() == "true",
            base_dn=os.environ.get("LDAP_BASE_DN", ""),
            bind_dn=os.environ.get("LDAP_BIND_DN"),
            bind_password=os.environ.get("LDAP_BIND_PASSWORD"),
            allowed_operations=allowed_ops,
            read_only=os.environ.get("LDAP_READ_ONLY", "true").lower() == "true",
            timeout=int(os.environ.get("LDAP_TIMEOUT", "30")),
        )


@dataclass
class LDAPSearchResult:
    """LDAP search result.

    Attributes:
        entries: List of matching entries
        total_count: Total number of matches
        search_time: Search time in seconds
    """

    entries: List[Dict[str, Any]]
    total_count: int
    search_time: float


class LDAPClient:
    """LDAP client wrapper.

    Provides secure LDAP operations with connection reuse.

    Example:
        >>> client = LDAPClient(config)
        >>> await client.connect()
        >>> results = await client.search("(objectClass=user)")
        >>> for entry in results.entries:
        ...     print(entry["dn"])
    """

    def __init__(self, config: LDAPConfig):
        """Initialize LDAP client.

        Args:
            config: LDAP configuration
        """
        if not HAS_LDAP3:
            raise ImportError(
                "ldap3 is required for LDAP operations. "
                "Install with: pip install ldap3"
            )

        self._config = config
        self._server: Optional[Server] = None
        self._connection: Optional[Connection] = None
        self._connected = False

    async def connect(
        self,
        bind_dn: Optional[str] = None,
        bind_password: Optional[str] = None,
    ) -> bool:
        """Connect and bind to LDAP server.

        Args:
            bind_dn: DN for binding (overrides config)
            bind_password: Password for binding (overrides config)

        Returns:
            True if connected successfully
        """
        if self._connected:
            return True

        effective_bind_dn = bind_dn or self._config.bind_dn
        effective_password = bind_password or self._config.bind_password

        try:
            # Create TLS context if needed
            tls = None
            if self._config.use_ssl or self._config.use_tls:
                tls = Tls(validate=ssl.CERT_OPTIONAL)

            # Create server
            self._server = Server(
                self._config.server,
                port=self._config.port,
                use_ssl=self._config.use_ssl,
                tls=tls,
                get_info=ALL,
                connect_timeout=self._config.timeout,
            )

            # Create connection
            loop = asyncio.get_event_loop()

            def _connect():
                conn = Connection(
                    self._server,
                    user=effective_bind_dn,
                    password=effective_password,
                    auto_bind=True if effective_bind_dn else False,
                    read_only=self._config.read_only,
                    receive_timeout=self._config.timeout,
                )
                if self._config.use_tls and not self._config.use_ssl:
                    conn.start_tls()
                if effective_bind_dn:
                    conn.bind()
                return conn

            self._connection = await loop.run_in_executor(None, _connect)
            self._connected = True

            logger.info(f"Connected to LDAP server: {self._config.server}:{self._config.port}")
            return True

        except Exception as e:
            logger.error(f"LDAP connection failed: {e}")
            self._connected = False
            raise ConnectionError(f"LDAP connection failed: {e}")

    async def disconnect(self) -> None:
        """Disconnect from LDAP server."""
        if self._connection:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._connection.unbind)
            except Exception:
                pass
            self._connection = None

        self._server = None
        self._connected = False
        logger.info(f"Disconnected from LDAP server: {self._config.server}")

    def _check_operation_allowed(self, operation: str) -> None:
        """Check if operation is allowed.

        Args:
            operation: Operation name

        Raises:
            PermissionError: If operation not allowed
        """
        if operation not in self._config.allowed_operations:
            raise PermissionError(
                f"Operation '{operation}' is not allowed. "
                f"Allowed: {self._config.allowed_operations}"
            )

    async def search(
        self,
        search_filter: str,
        search_base: Optional[str] = None,
        attributes: Optional[List[str]] = None,
        scope: str = "subtree",
        size_limit: int = 1000,
    ) -> LDAPSearchResult:
        """Search LDAP directory.

        Args:
            search_filter: LDAP search filter (e.g., "(objectClass=user)")
            search_base: Base DN for search (default: config base_dn)
            attributes: Attributes to return (default: all)
            scope: Search scope ("base", "level", "subtree")
            size_limit: Maximum number of results

        Returns:
            LDAPSearchResult with matching entries
        """
        self._check_operation_allowed("search")

        if not self._connected or not self._connection:
            raise ConnectionError("Not connected to LDAP server")

        effective_base = search_base or self._config.base_dn
        if not effective_base:
            raise ValueError("Search base DN is required")

        # Map scope string to constant
        scope_map = {
            "base": BASE,
            "level": LEVEL,
            "subtree": SUBTREE,
        }
        ldap_scope = scope_map.get(scope.lower(), SUBTREE)

        start_time = asyncio.get_event_loop().time()

        try:
            loop = asyncio.get_event_loop()

            def _search():
                self._connection.search(
                    search_base=effective_base,
                    search_filter=search_filter,
                    search_scope=ldap_scope,
                    attributes=attributes or ["*"],
                    size_limit=size_limit,
                )
                return self._connection.entries

            entries = await loop.run_in_executor(None, _search)

            search_time = asyncio.get_event_loop().time() - start_time

            # Convert entries to dictionaries
            results = []
            for entry in entries:
                entry_dict = {
                    "dn": str(entry.entry_dn),
                    "attributes": {},
                }
                for attr in entry.entry_attributes:
                    values = entry[attr].values
                    if len(values) == 1:
                        entry_dict["attributes"][attr] = values[0]
                    else:
                        entry_dict["attributes"][attr] = list(values)
                results.append(entry_dict)

            logger.info(
                f"LDAP search completed: filter={search_filter}, "
                f"results={len(results)}, time={search_time:.2f}s"
            )

            return LDAPSearchResult(
                entries=results,
                total_count=len(results),
                search_time=search_time,
            )

        except Exception as e:
            logger.error(f"LDAP search failed: {e}")
            raise

    async def get_entry(
        self,
        dn: str,
        attributes: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get a specific LDAP entry by DN.

        Args:
            dn: Distinguished name of entry
            attributes: Attributes to return

        Returns:
            Entry dictionary or None if not found
        """
        result = await self.search(
            search_filter="(objectClass=*)",
            search_base=dn,
            attributes=attributes,
            scope="base",
            size_limit=1,
        )

        if result.entries:
            return result.entries[0]
        return None

    async def search_users(
        self,
        username: Optional[str] = None,
        email: Optional[str] = None,
        attributes: Optional[List[str]] = None,
    ) -> LDAPSearchResult:
        """Search for user entries.

        Args:
            username: Username to search (supports wildcards)
            email: Email to search (supports wildcards)
            attributes: Attributes to return

        Returns:
            LDAPSearchResult with matching users
        """
        # Build search filter
        filters = ["(objectClass=user)"]
        if username:
            filters.append(f"(sAMAccountName={username})")
        if email:
            filters.append(f"(mail={email})")

        if len(filters) > 1:
            search_filter = f"(&{''.join(filters)})"
        else:
            search_filter = filters[0]

        return await self.search(
            search_filter=search_filter,
            attributes=attributes or [
                "sAMAccountName",
                "cn",
                "displayName",
                "mail",
                "memberOf",
            ],
        )

    async def search_groups(
        self,
        group_name: Optional[str] = None,
        attributes: Optional[List[str]] = None,
    ) -> LDAPSearchResult:
        """Search for group entries.

        Args:
            group_name: Group name to search (supports wildcards)
            attributes: Attributes to return

        Returns:
            LDAPSearchResult with matching groups
        """
        if group_name:
            search_filter = f"(&(objectClass=group)(cn={group_name}))"
        else:
            search_filter = "(objectClass=group)"

        return await self.search(
            search_filter=search_filter,
            attributes=attributes or [
                "cn",
                "description",
                "member",
                "managedBy",
            ],
        )

    async def add_entry(
        self,
        dn: str,
        object_class: List[str],
        attributes: Dict[str, Any],
    ) -> bool:
        """Add a new LDAP entry.

        Args:
            dn: Distinguished name for new entry
            object_class: Object classes for entry
            attributes: Entry attributes

        Returns:
            True if added successfully
        """
        self._check_operation_allowed("add")

        if self._config.read_only:
            raise PermissionError("Server is in read-only mode")

        if not self._connected or not self._connection:
            raise ConnectionError("Not connected to LDAP server")

        try:
            loop = asyncio.get_event_loop()

            def _add():
                return self._connection.add(
                    dn=dn,
                    object_class=object_class,
                    attributes=attributes,
                )

            result = await loop.run_in_executor(None, _add)

            if result:
                logger.info(f"LDAP entry added: {dn}")
            else:
                logger.warning(f"LDAP add failed: {self._connection.result}")

            return result

        except Exception as e:
            logger.error(f"LDAP add failed: {e}")
            raise

    async def modify_entry(
        self,
        dn: str,
        changes: Dict[str, Tuple[str, Any]],
    ) -> bool:
        """Modify an LDAP entry.

        Args:
            dn: Distinguished name of entry
            changes: Dictionary of {attribute: (operation, values)}
                     operation can be "add", "delete", "replace"

        Returns:
            True if modified successfully
        """
        self._check_operation_allowed("modify")

        if self._config.read_only:
            raise PermissionError("Server is in read-only mode")

        if not self._connected or not self._connection:
            raise ConnectionError("Not connected to LDAP server")

        # Map operation strings to constants
        op_map = {
            "add": MODIFY_ADD,
            "delete": MODIFY_DELETE,
            "replace": MODIFY_REPLACE,
        }

        ldap_changes = {}
        for attr, (op, values) in changes.items():
            ldap_op = op_map.get(op.lower())
            if ldap_op is None:
                raise ValueError(f"Invalid operation '{op}'. Use: add, delete, replace")
            ldap_changes[attr] = [(ldap_op, values)]

        try:
            loop = asyncio.get_event_loop()

            def _modify():
                return self._connection.modify(dn=dn, changes=ldap_changes)

            result = await loop.run_in_executor(None, _modify)

            if result:
                logger.info(f"LDAP entry modified: {dn}")
            else:
                logger.warning(f"LDAP modify failed: {self._connection.result}")

            return result

        except Exception as e:
            logger.error(f"LDAP modify failed: {e}")
            raise

    async def delete_entry(self, dn: str) -> bool:
        """Delete an LDAP entry.

        Args:
            dn: Distinguished name of entry to delete

        Returns:
            True if deleted successfully
        """
        self._check_operation_allowed("delete")

        if self._config.read_only:
            raise PermissionError("Server is in read-only mode")

        if not self._connected or not self._connection:
            raise ConnectionError("Not connected to LDAP server")

        try:
            loop = asyncio.get_event_loop()

            def _delete():
                return self._connection.delete(dn=dn)

            result = await loop.run_in_executor(None, _delete)

            if result:
                logger.info(f"LDAP entry deleted: {dn}")
            else:
                logger.warning(f"LDAP delete failed: {self._connection.result}")

            return result

        except Exception as e:
            logger.error(f"LDAP delete failed: {e}")
            raise

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    @property
    def server_info(self) -> Optional[Dict[str, Any]]:
        """Get server information."""
        if self._server:
            return {
                "host": self._server.host,
                "port": self._server.port,
                "ssl": self._server.ssl,
                "naming_contexts": list(self._server.info.naming_contexts) if self._server.info else [],
            }
        return None

    async def __aenter__(self) -> "LDAPClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()


class LDAPConnectionManager:
    """LDAP connection pool manager.

    Manages multiple LDAP connections with reuse and cleanup.
    """

    def __init__(self, config: LDAPConfig):
        """Initialize connection manager.

        Args:
            config: LDAP configuration
        """
        self._config = config
        self._connections: Dict[str, LDAPClient] = {}
        self._lock = asyncio.Lock()

    def _get_connection_key(self, server: str, port: int) -> str:
        """Generate connection pool key."""
        return f"{server}:{port}"

    async def get_connection(
        self,
        server: Optional[str] = None,
        port: Optional[int] = None,
        bind_dn: Optional[str] = None,
        bind_password: Optional[str] = None,
    ) -> LDAPClient:
        """Get or create LDAP connection.

        Args:
            server: LDAP server (default: config server)
            port: LDAP port (default: config port)
            bind_dn: DN for binding
            bind_password: Password for binding

        Returns:
            Connected LDAPClient
        """
        effective_server = server or self._config.server
        effective_port = port or self._config.port
        key = self._get_connection_key(effective_server, effective_port)

        async with self._lock:
            if key in self._connections:
                client = self._connections[key]
                if client.is_connected:
                    return client
                else:
                    del self._connections[key]

            # Create new config with overrides
            config = LDAPConfig(
                server=effective_server,
                port=effective_port,
                use_ssl=self._config.use_ssl,
                use_tls=self._config.use_tls,
                base_dn=self._config.base_dn,
                bind_dn=bind_dn or self._config.bind_dn,
                bind_password=bind_password or self._config.bind_password,
                allowed_operations=self._config.allowed_operations,
                read_only=self._config.read_only,
                timeout=self._config.timeout,
            )

            client = LDAPClient(config)
            await client.connect()

            self._connections[key] = client
            return client

    async def close_all(self) -> None:
        """Close all connections."""
        async with self._lock:
            for client in self._connections.values():
                await client.disconnect()
            self._connections.clear()
