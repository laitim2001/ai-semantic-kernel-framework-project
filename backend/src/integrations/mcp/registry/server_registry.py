"""MCP Server Registry.

This module provides a centralized registry for managing MCP server
configurations, connections, and lifecycle.

Features:
    - Server registration and configuration management
    - Connection lifecycle management
    - Auto-reconnection with exponential backoff
    - Server health monitoring
    - Tool catalog aggregation

Example:
    >>> registry = ServerRegistry()
    >>> await registry.register(ServerDefinition(
    ...     name="azure-mcp",
    ...     command="python",
    ...     args=["-m", "mcp_servers.azure"],
    ...     enabled=True,
    ... ))
    >>> await registry.connect_all()
    >>> tools = registry.get_all_tools()
    >>> await registry.shutdown()
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Awaitable
from enum import Enum
from datetime import datetime
import asyncio
import logging

from ..core.client import MCPClient, ServerConfig
from ..core.types import ToolSchema

logger = logging.getLogger(__name__)


class ServerStatus(str, Enum):
    """Server connection status."""

    REGISTERED = "registered"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


@dataclass
class RegisteredServer:
    """Registered MCP server with status tracking.

    Attributes:
        name: Unique server identifier
        command: Command to execute
        args: Command arguments
        env: Environment variables
        transport: Transport type
        timeout: Operation timeout
        enabled: Whether server should auto-connect
        status: Current connection status
        last_connected: Timestamp of last successful connection
        last_error: Last error message if any
        retry_count: Number of reconnection attempts
        tools: Cached tool schemas from this server
    """

    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    transport: str = "stdio"
    timeout: float = 30.0
    enabled: bool = True
    cwd: Optional[str] = None

    # Runtime state
    status: ServerStatus = ServerStatus.REGISTERED
    last_connected: Optional[datetime] = None
    last_error: Optional[str] = None
    retry_count: int = 0
    tools: List[ToolSchema] = field(default_factory=list)

    def to_config(self) -> ServerConfig:
        """Convert to MCPClient ServerConfig.

        Returns:
            ServerConfig for MCPClient connection
        """
        return ServerConfig(
            name=self.name,
            command=self.command,
            args=self.args,
            env=self.env,
            transport=self.transport,
            timeout=self.timeout,
            cwd=self.cwd,
        )


# Type alias for event handlers
EventHandler = Callable[[str, ServerStatus], Awaitable[None]]


class ServerRegistry:
    """Central registry for MCP servers.

    Manages server configurations, connections, and provides a unified
    interface for tool discovery across all connected servers.

    Attributes:
        servers: Dictionary of registered servers
        max_retries: Maximum reconnection attempts
        retry_delay: Initial delay between retries (exponential backoff)

    Example:
        >>> registry = ServerRegistry(max_retries=5, retry_delay=1.0)
        >>> await registry.register(server_def)
        >>> await registry.connect("my-server")
        >>> await registry.connect_all()
        >>> all_tools = registry.get_all_tools()
        >>> await registry.shutdown()
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        auto_reconnect: bool = True,
    ):
        """Initialize the server registry.

        Args:
            max_retries: Maximum reconnection attempts before giving up
            retry_delay: Initial delay between retries (doubles each attempt)
            auto_reconnect: Enable automatic reconnection on disconnect
        """
        self._servers: Dict[str, RegisteredServer] = {}
        self._client = MCPClient()
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._auto_reconnect = auto_reconnect
        self._event_handlers: List[EventHandler] = []
        self._reconnect_tasks: Dict[str, asyncio.Task] = {}
        self._shutdown_event = asyncio.Event()

    @property
    def servers(self) -> Dict[str, RegisteredServer]:
        """Get all registered servers."""
        return self._servers.copy()

    @property
    def connected_servers(self) -> List[str]:
        """Get list of connected server names."""
        return [
            name
            for name, server in self._servers.items()
            if server.status == ServerStatus.CONNECTED
        ]

    async def register(
        self,
        server: RegisteredServer,
        connect: bool = False,
    ) -> bool:
        """Register a new MCP server.

        Args:
            server: Server configuration to register
            connect: If True, immediately attempt connection

        Returns:
            True if registration successful
        """
        if server.name in self._servers:
            logger.warning(f"Server already registered: {server.name}")
            return False

        self._servers[server.name] = server
        logger.info(f"Registered MCP server: {server.name}")

        if connect and server.enabled:
            await self.connect(server.name)

        return True

    async def unregister(self, server_name: str) -> bool:
        """Unregister a server.

        Args:
            server_name: Name of server to unregister

        Returns:
            True if unregistration successful
        """
        if server_name not in self._servers:
            logger.warning(f"Server not registered: {server_name}")
            return False

        # Disconnect if connected
        if self._servers[server_name].status == ServerStatus.CONNECTED:
            await self.disconnect(server_name)

        # Cancel any pending reconnection
        if server_name in self._reconnect_tasks:
            self._reconnect_tasks[server_name].cancel()
            del self._reconnect_tasks[server_name]

        del self._servers[server_name]
        logger.info(f"Unregistered MCP server: {server_name}")
        return True

    async def connect(self, server_name: str) -> bool:
        """Connect to a registered server.

        Args:
            server_name: Name of server to connect

        Returns:
            True if connection successful
        """
        if server_name not in self._servers:
            logger.error(f"Server not registered: {server_name}")
            return False

        server = self._servers[server_name]

        if server.status == ServerStatus.CONNECTED:
            logger.debug(f"Server already connected: {server_name}")
            return True

        server.status = ServerStatus.CONNECTING
        await self._emit_event(server_name, ServerStatus.CONNECTING)

        try:
            config = server.to_config()
            success = await self._client.connect(config)

            if success:
                server.status = ServerStatus.CONNECTED
                server.last_connected = datetime.utcnow()
                server.last_error = None
                server.retry_count = 0

                # Cache tools
                tools = await self._client.list_tools(server_name)
                server.tools = tools.get(server_name, [])

                await self._emit_event(server_name, ServerStatus.CONNECTED)
                logger.info(
                    f"Connected to MCP server: {server_name} "
                    f"({len(server.tools)} tools)"
                )
                return True
            else:
                server.status = ServerStatus.ERROR
                server.last_error = "Connection failed"
                await self._emit_event(server_name, ServerStatus.ERROR)
                return False

        except Exception as e:
            server.status = ServerStatus.ERROR
            server.last_error = str(e)
            await self._emit_event(server_name, ServerStatus.ERROR)
            logger.error(f"Failed to connect to {server_name}: {e}")
            return False

    async def disconnect(self, server_name: str) -> bool:
        """Disconnect from a server.

        Args:
            server_name: Name of server to disconnect

        Returns:
            True if disconnection successful
        """
        if server_name not in self._servers:
            logger.warning(f"Server not registered: {server_name}")
            return False

        server = self._servers[server_name]

        if server.status != ServerStatus.CONNECTED:
            logger.debug(f"Server not connected: {server_name}")
            return True

        server.status = ServerStatus.DISCONNECTING
        await self._emit_event(server_name, ServerStatus.DISCONNECTING)

        try:
            await self._client.disconnect(server_name)
            server.status = ServerStatus.DISCONNECTED
            server.tools = []
            await self._emit_event(server_name, ServerStatus.DISCONNECTED)
            logger.info(f"Disconnected from MCP server: {server_name}")
            return True

        except Exception as e:
            server.status = ServerStatus.ERROR
            server.last_error = str(e)
            await self._emit_event(server_name, ServerStatus.ERROR)
            logger.error(f"Error disconnecting from {server_name}: {e}")
            return False

    async def connect_all(self) -> Dict[str, bool]:
        """Connect to all enabled registered servers.

        Returns:
            Dictionary mapping server names to connection success
        """
        results = {}

        tasks = []
        for name, server in self._servers.items():
            if server.enabled:
                tasks.append(self.connect(name))
            else:
                results[name] = False

        if tasks:
            task_results = await asyncio.gather(*tasks, return_exceptions=True)
            enabled_servers = [
                name for name, s in self._servers.items() if s.enabled
            ]
            for name, result in zip(enabled_servers, task_results):
                if isinstance(result, Exception):
                    results[name] = False
                else:
                    results[name] = result

        return results

    async def disconnect_all(self) -> Dict[str, bool]:
        """Disconnect from all connected servers.

        Returns:
            Dictionary mapping server names to disconnection success
        """
        results = {}

        for name, server in self._servers.items():
            if server.status == ServerStatus.CONNECTED:
                results[name] = await self.disconnect(name)
            else:
                results[name] = True

        return results

    async def reconnect(
        self,
        server_name: str,
        force: bool = False,
    ) -> bool:
        """Reconnect to a server with retry logic.

        Args:
            server_name: Name of server to reconnect
            force: If True, disconnect first even if connected

        Returns:
            True if reconnection successful
        """
        if server_name not in self._servers:
            return False

        server = self._servers[server_name]

        if force and server.status == ServerStatus.CONNECTED:
            await self.disconnect(server_name)

        server.status = ServerStatus.RECONNECTING
        await self._emit_event(server_name, ServerStatus.RECONNECTING)

        delay = self._retry_delay

        for attempt in range(self._max_retries):
            server.retry_count = attempt + 1

            if self._shutdown_event.is_set():
                return False

            success = await self.connect(server_name)
            if success:
                return True

            if attempt < self._max_retries - 1:
                logger.info(
                    f"Retry {attempt + 1}/{self._max_retries} for "
                    f"{server_name} in {delay}s"
                )
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff

        logger.error(
            f"Failed to reconnect to {server_name} after "
            f"{self._max_retries} attempts"
        )
        return False

    def get_server(self, server_name: str) -> Optional[RegisteredServer]:
        """Get a registered server by name.

        Args:
            server_name: Server name to lookup

        Returns:
            RegisteredServer or None if not found
        """
        return self._servers.get(server_name)

    def get_all_tools(self) -> Dict[str, List[ToolSchema]]:
        """Get all tools from all connected servers.

        Returns:
            Dictionary mapping server names to tool lists
        """
        result = {}
        for name, server in self._servers.items():
            if server.status == ServerStatus.CONNECTED:
                result[name] = server.tools
        return result

    def find_tool(
        self,
        tool_name: str,
        server_name: Optional[str] = None,
    ) -> Optional[ToolSchema]:
        """Find a tool by name.

        Args:
            tool_name: Name of tool to find
            server_name: Optional server to search in

        Returns:
            ToolSchema if found, None otherwise
        """
        if server_name:
            server = self._servers.get(server_name)
            if server:
                for tool in server.tools:
                    if tool.name == tool_name:
                        return tool
        else:
            for server in self._servers.values():
                for tool in server.tools:
                    if tool.name == tool_name:
                        return tool
        return None

    async def call_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        server_name: Optional[str] = None,
    ):
        """Call a tool on a connected server.

        Args:
            tool_name: Name of tool to call
            arguments: Tool arguments
            server_name: Specific server to use (auto-detected if not provided)

        Returns:
            ToolResult from the call
        """
        # Find the server with this tool
        target_server = None

        if server_name:
            target_server = server_name
        else:
            for name, server in self._servers.items():
                if server.status == ServerStatus.CONNECTED:
                    for tool in server.tools:
                        if tool.name == tool_name:
                            target_server = name
                            break
                if target_server:
                    break

        if not target_server:
            from ..core.types import ToolResult

            return ToolResult(
                success=False,
                content=None,
                error=f"Tool not found: {tool_name}",
            )

        return await self._client.call_tool(
            server=target_server,
            tool=tool_name,
            arguments=arguments,
        )

    def add_event_handler(self, handler: EventHandler) -> None:
        """Add a status change event handler.

        Args:
            handler: Async callback for status changes
        """
        self._event_handlers.append(handler)

    def remove_event_handler(self, handler: EventHandler) -> None:
        """Remove an event handler.

        Args:
            handler: Handler to remove
        """
        if handler in self._event_handlers:
            self._event_handlers.remove(handler)

    async def _emit_event(
        self,
        server_name: str,
        status: ServerStatus,
    ) -> None:
        """Emit a status change event to all handlers.

        Args:
            server_name: Name of server
            status: New status
        """
        for handler in self._event_handlers:
            try:
                await handler(server_name, status)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    async def shutdown(self) -> None:
        """Shutdown the registry and all connections."""
        self._shutdown_event.set()

        # Cancel all reconnection tasks
        for task in self._reconnect_tasks.values():
            task.cancel()
        self._reconnect_tasks.clear()

        # Disconnect all servers
        await self.disconnect_all()

        # Close the client
        await self._client.close()

        logger.info("Server registry shutdown complete")

    def get_status_summary(self) -> Dict[str, Any]:
        """Get a summary of all server statuses.

        Returns:
            Summary dictionary with status counts and details
        """
        status_counts = {}
        for status in ServerStatus:
            status_counts[status.value] = 0

        server_details = []
        total_tools = 0

        for name, server in self._servers.items():
            status_counts[server.status.value] += 1
            total_tools += len(server.tools)

            server_details.append(
                {
                    "name": name,
                    "status": server.status.value,
                    "enabled": server.enabled,
                    "tools_count": len(server.tools),
                    "last_connected": (
                        server.last_connected.isoformat()
                        if server.last_connected
                        else None
                    ),
                    "last_error": server.last_error,
                    "retry_count": server.retry_count,
                }
            )

        return {
            "total_servers": len(self._servers),
            "status_counts": status_counts,
            "total_tools": total_tools,
            "servers": server_details,
        }

    async def __aenter__(self) -> "ServerRegistry":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.shutdown()
