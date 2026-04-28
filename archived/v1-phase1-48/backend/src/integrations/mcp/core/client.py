"""MCP Client.

This module provides the main client interface for connecting to and
communicating with MCP servers.

The MCPClient manages multiple server connections and provides a unified
interface for tool discovery and execution.

Example:
    >>> client = MCPClient()
    >>> await client.connect(ServerConfig(
    ...     name="azure-mcp",
    ...     command="python",
    ...     args=["-m", "mcp_servers.azure"],
    ... ))
    >>> tools = await client.list_tools("azure-mcp")
    >>> result = await client.call_tool(
    ...     server="azure-mcp",
    ...     tool="list_vms",
    ...     arguments={"resource_group": "prod-rg"},
    ... )
    >>> await client.disconnect("azure-mcp")
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type
import asyncio
import logging

from .protocol import MCPProtocol
from .transport import BaseTransport, StdioTransport, InMemoryTransport
from .types import ToolSchema, ToolResult, ToolParameter, ToolInputType

logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    """MCP Server configuration.

    Attributes:
        name: Unique server identifier
        command: Command to execute for the server
        args: Command arguments
        env: Environment variables for the server process
        transport: Transport type (stdio, sse, websocket)
        timeout: Default timeout for operations in seconds
        cwd: Working directory for the server process
    """

    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    transport: str = "stdio"
    timeout: float = 30.0
    cwd: Optional[str] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.name:
            raise ValueError("Server name is required")
        if not self.command:
            raise ValueError("Server command is required")


class MCPClient:
    """MCP Client for managing server connections.

    The client maintains connections to multiple MCP servers and provides
    methods for tool discovery and execution.

    Attributes:
        connected_servers: List of currently connected server names

    Example:
        >>> client = MCPClient()
        >>>
        >>> # Connect to a server
        >>> await client.connect(ServerConfig(
        ...     name="azure-mcp",
        ...     command="python",
        ...     args=["-m", "mcp_servers.azure"],
        ... ))
        >>>
        >>> # List available tools
        >>> tools = await client.list_tools("azure-mcp")
        >>> for tool in tools["azure-mcp"]:
        ...     print(f"{tool.name}: {tool.description}")
        >>>
        >>> # Call a tool
        >>> result = await client.call_tool(
        ...     server="azure-mcp",
        ...     tool="list_vms",
        ...     arguments={"resource_group": "prod-rg"},
        ... )
        >>> if result.success:
        ...     print(result.content)
        >>>
        >>> # Disconnect
        >>> await client.disconnect("azure-mcp")
    """

    def __init__(self):
        """Initialize MCP Client."""
        self._servers: Dict[str, BaseTransport] = {}
        self._protocols: Dict[str, MCPProtocol] = {}
        self._tools: Dict[str, Dict[str, ToolSchema]] = {}
        self._server_info: Dict[str, Dict[str, Any]] = {}

    async def connect(
        self,
        config: ServerConfig,
        transport: Optional[BaseTransport] = None,
    ) -> bool:
        """Connect to an MCP server.

        Args:
            config: Server configuration
            transport: Optional custom transport (for testing)

        Returns:
            True if connection successful, False otherwise
        """
        if config.name in self._servers:
            logger.warning(f"Server already connected: {config.name}")
            return True

        try:
            # Create transport if not provided
            if transport is None:
                if config.transport == "stdio":
                    transport = StdioTransport(
                        command=config.command,
                        args=config.args,
                        env=config.env,
                        timeout=config.timeout,
                        cwd=config.cwd,
                    )
                else:
                    raise ValueError(f"Unsupported transport: {config.transport}")

            # Start transport
            await transport.start()

            # Create protocol handler
            protocol = MCPProtocol()

            # Send initialize request
            init_request = protocol.create_request(
                "initialize",
                {
                    "protocolVersion": MCPProtocol.MCP_VERSION,
                    "capabilities": {
                        "tools": {},
                        "resources": {},
                    },
                    "clientInfo": {
                        "name": "ipa-platform",
                        "version": "1.0.0",
                    },
                },
            )

            response = await transport.send(init_request)

            if response.error:
                logger.error(
                    f"Initialize failed for {config.name}: {response.error_message}"
                )
                await transport.stop()
                return False

            # Store server info
            self._server_info[config.name] = response.result or {}

            # Send initialized notification
            initialized_request = protocol.create_notification("initialized")
            try:
                await transport.send(initialized_request)
            except Exception:
                # Some servers don't respond to notifications
                pass

            # Get tool list
            tools_request = protocol.create_request("tools/list", {})
            tools_response = await transport.send(tools_request)

            if tools_response.result:
                self._tools[config.name] = {}
                for tool_data in tools_response.result.get("tools", []):
                    schema = ToolSchema.from_mcp_format(tool_data)
                    self._tools[config.name][schema.name] = schema

            # Store connection
            self._servers[config.name] = transport
            self._protocols[config.name] = protocol

            tool_count = len(self._tools.get(config.name, {}))
            logger.info(
                f"Connected to MCP server: {config.name} ({tool_count} tools)"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to connect to {config.name}: {e}")
            return False

    async def disconnect(self, server_name: str) -> bool:
        """Disconnect from an MCP server.

        Args:
            server_name: Name of server to disconnect

        Returns:
            True if disconnected, False if server not found
        """
        if server_name not in self._servers:
            logger.warning(f"Server not connected: {server_name}")
            return True

        try:
            transport = self._servers[server_name]
            await transport.stop()

            del self._servers[server_name]
            del self._protocols[server_name]
            self._tools.pop(server_name, None)
            self._server_info.pop(server_name, None)

            logger.info(f"Disconnected from MCP server: {server_name}")
            return True

        except Exception as e:
            logger.error(f"Error disconnecting from {server_name}: {e}")
            return False

    async def list_tools(
        self,
        server_name: Optional[str] = None,
        refresh: bool = False,
    ) -> Dict[str, List[ToolSchema]]:
        """List available tools.

        Args:
            server_name: Optional server name to filter by
            refresh: If True, refresh tool list from servers

        Returns:
            Dictionary mapping server names to tool schema lists
        """
        if refresh:
            await self._refresh_tools(server_name)

        if server_name:
            if server_name in self._tools:
                return {server_name: list(self._tools[server_name].values())}
            return {}

        return {
            name: list(tools.values()) for name, tools in self._tools.items()
        }

    async def _refresh_tools(self, server_name: Optional[str] = None) -> None:
        """Refresh tool lists from servers.

        Args:
            server_name: Optional specific server to refresh
        """
        servers = [server_name] if server_name else list(self._servers.keys())

        for name in servers:
            if name not in self._servers:
                continue

            try:
                transport = self._servers[name]
                protocol = self._protocols[name]

                request = protocol.create_request("tools/list", {})
                response = await transport.send(request)

                if response.result:
                    self._tools[name] = {}
                    for tool_data in response.result.get("tools", []):
                        schema = ToolSchema.from_mcp_format(tool_data)
                        self._tools[name][schema.name] = schema

            except Exception as e:
                logger.error(f"Failed to refresh tools for {name}: {e}")

    def get_tool_schema(
        self,
        server: str,
        tool: str,
    ) -> Optional[ToolSchema]:
        """Get schema for a specific tool.

        Args:
            server: Server name
            tool: Tool name

        Returns:
            Tool schema or None if not found
        """
        server_tools = self._tools.get(server, {})
        return server_tools.get(tool)

    async def call_tool(
        self,
        server: str,
        tool: str,
        arguments: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> ToolResult:
        """Call a tool on an MCP server.

        Args:
            server: Server name
            tool: Tool name
            arguments: Tool arguments
            timeout: Optional timeout override

        Returns:
            Tool execution result
        """
        if server not in self._servers:
            return ToolResult(
                success=False,
                content=None,
                error=f"Server not connected: {server}",
            )

        if server not in self._tools or tool not in self._tools[server]:
            return ToolResult(
                success=False,
                content=None,
                error=f"Tool not found: {server}/{tool}",
            )

        try:
            transport = self._servers[server]
            protocol = self._protocols[server]

            request = protocol.create_request(
                "tools/call",
                {
                    "name": tool,
                    "arguments": arguments or {},
                },
            )

            response = await transport.send(request)

            if response.error:
                return ToolResult(
                    success=False,
                    content=None,
                    error=response.error_message or "Unknown error",
                    metadata={"server": server, "tool": tool},
                )

            result = response.result or {}

            if result.get("isError"):
                content_list = result.get("content", [])
                error_text = "Unknown error"
                if content_list:
                    first = content_list[0]
                    if isinstance(first, dict):
                        error_text = first.get("text", error_text)

                return ToolResult(
                    success=False,
                    content=None,
                    error=error_text,
                    metadata={"server": server, "tool": tool},
                )

            # Extract content
            content_list = result.get("content", [])
            if content_list:
                first = content_list[0]
                if isinstance(first, dict):
                    content = first.get("text", "")
                else:
                    content = str(first)
            else:
                content = ""

            return ToolResult(
                success=True,
                content=content,
                metadata={"server": server, "tool": tool},
            )

        except Exception as e:
            logger.error(f"Tool call failed: {server}/{tool}: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
                metadata={"server": server, "tool": tool},
            )

    def is_connected(self, server_name: str) -> bool:
        """Check if a server is connected.

        Args:
            server_name: Server name to check

        Returns:
            True if connected
        """
        if server_name not in self._servers:
            return False
        return self._servers[server_name].is_connected()

    @property
    def connected_servers(self) -> List[str]:
        """Get list of connected server names."""
        return list(self._servers.keys())

    def get_server_info(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a connected server.

        Args:
            server_name: Server name

        Returns:
            Server info dict or None if not connected
        """
        return self._server_info.get(server_name)

    async def close(self) -> None:
        """Close all server connections."""
        for server_name in list(self._servers.keys()):
            await self.disconnect(server_name)

    async def __aenter__(self) -> "MCPClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
