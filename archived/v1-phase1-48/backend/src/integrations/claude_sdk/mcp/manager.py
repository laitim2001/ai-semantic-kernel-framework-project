"""MCP Manager for managing multiple MCP servers.

Sprint 50: S50-2 - MCP Manager 與工具發現 (8 pts)

This module provides MCPManager for coordinating multiple MCP servers,
tool discovery, and unified tool execution.

Example:
    manager = MCPManager()

    # Add servers
    manager.add_server(MCPStdioServer(
        name="filesystem",
        command="npx",
        args=["-y", "@anthropic/mcp-filesystem"],
    ))

    manager.add_server(MCPHTTPServer(
        name="remote",
        url="https://mcp.example.com",
    ))

    # Use as context manager
    async with manager:
        # Discover all tools
        tools = await manager.discover_tools()

        # Execute tool by reference
        result = await manager.execute_tool(
            "filesystem:read_file",
            {"path": "/tmp/test.txt"}
        )
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import asyncio
import logging
import time

from .base import MCPServer
from .exceptions import (
    MCPDisconnectedError,
    MCPError,
    MCPToolNotFoundError,
)
from .types import MCPToolDefinition, MCPToolResult

logger = logging.getLogger(__name__)


@dataclass
class ServerInfo:
    """Server information for listing."""

    name: str
    connected: bool
    tools_count: int
    state: str
    error: Optional[str] = None


@dataclass
class HealthCheckResult:
    """Health check result for a server."""

    name: str
    healthy: bool
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class MCPManager:
    """Manager for coordinating multiple MCP servers.

    MCPManager handles:
    - Server registration and lifecycle management
    - Parallel connection/disconnection of servers
    - Tool discovery and aggregation across servers
    - Tool execution routing
    - Health monitoring

    Example:
        manager = MCPManager()
        manager.add_server(stdio_server)
        manager.add_server(http_server)

        async with manager:
            tools = await manager.discover_tools()
            result = await manager.execute_tool("server:tool", {"arg": "value"})
    """

    def __init__(
        self,
        auto_discover: bool = True,
        connection_timeout: float = 30.0,
    ):
        """Initialize MCP Manager.

        Args:
            auto_discover: Whether to auto-discover tools on connect.
            connection_timeout: Timeout for server connections in seconds.
        """
        self._servers: Dict[str, MCPServer] = {}
        self._tools: Dict[str, MCPToolDefinition] = {}  # "server:tool_name" -> tool
        self._tool_to_server: Dict[str, str] = {}  # "tool_name" -> "server_name"
        self._auto_discover = auto_discover
        self._connection_timeout = connection_timeout

    @property
    def servers(self) -> Dict[str, MCPServer]:
        """Get all registered servers."""
        return dict(self._servers)

    @property
    def server_count(self) -> int:
        """Get count of registered servers."""
        return len(self._servers)

    @property
    def connected_count(self) -> int:
        """Get count of connected servers."""
        return sum(1 for s in self._servers.values() if s.is_connected)

    @property
    def tools(self) -> Dict[str, MCPToolDefinition]:
        """Get all discovered tools."""
        return dict(self._tools)

    @property
    def tool_count(self) -> int:
        """Get count of discovered tools."""
        return len(self._tools)

    def add_server(self, server: MCPServer) -> None:
        """Add an MCP server to the manager.

        Args:
            server: MCPServer instance to add.

        Raises:
            ValueError: If server with same name already exists.
        """
        if server.name in self._servers:
            raise ValueError(f"Server already exists: {server.name}")

        self._servers[server.name] = server
        logger.info(f"Added MCP server: {server.name}")

    def remove_server(self, name: str) -> bool:
        """Remove an MCP server from the manager.

        Args:
            name: Name of the server to remove.

        Returns:
            True if server was removed, False if not found.

        Note:
            This does not disconnect the server. Call disconnect_server first.
        """
        if name not in self._servers:
            return False

        # Remove server
        del self._servers[name]

        # Remove tools associated with this server
        tools_to_remove = [
            key for key in self._tools if key.startswith(f"{name}:")
        ]
        for key in tools_to_remove:
            tool = self._tools.pop(key)
            if tool.name in self._tool_to_server:
                if self._tool_to_server[tool.name] == name:
                    del self._tool_to_server[tool.name]

        logger.info(f"Removed MCP server: {name}")
        return True

    def get_server(self, name: str) -> Optional[MCPServer]:
        """Get a server by name.

        Args:
            name: Server name.

        Returns:
            MCPServer if found, None otherwise.
        """
        return self._servers.get(name)

    async def connect_server(self, name: str) -> bool:
        """Connect a specific server.

        Args:
            name: Server name.

        Returns:
            True if connected successfully, False otherwise.
        """
        server = self._servers.get(name)
        if not server:
            return False

        try:
            await asyncio.wait_for(
                server.connect(),
                timeout=self._connection_timeout,
            )
            logger.info(f"Connected to MCP server: {name}")
            return True
        except asyncio.TimeoutError:
            logger.error(f"Connection timeout for server: {name}")
            return False
        except Exception as e:
            logger.error(f"Failed to connect server {name}: {e}")
            return False

    async def disconnect_server(self, name: str) -> bool:
        """Disconnect a specific server.

        Args:
            name: Server name.

        Returns:
            True if disconnected, False if not found.
        """
        server = self._servers.get(name)
        if not server:
            return False

        try:
            await server.disconnect()
            logger.info(f"Disconnected from MCP server: {name}")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting server {name}: {e}")
            return False

    async def connect_all(self) -> Dict[str, bool]:
        """Connect to all registered servers in parallel.

        Returns:
            Dictionary mapping server names to connection success status.
        """
        if not self._servers:
            return {}

        async def connect_with_result(name: str, server: MCPServer) -> tuple:
            try:
                await asyncio.wait_for(
                    server.connect(),
                    timeout=self._connection_timeout,
                )
                logger.info(f"Connected to MCP server: {name}")
                return name, True
            except asyncio.TimeoutError:
                logger.error(f"Connection timeout for server: {name}")
                return name, False
            except Exception as e:
                logger.error(f"Failed to connect server {name}: {e}")
                return name, False

        # Connect all servers in parallel
        tasks = [
            connect_with_result(name, server)
            for name, server in self._servers.items()
        ]
        results = await asyncio.gather(*tasks)

        return dict(results)

    async def disconnect_all(self) -> None:
        """Disconnect all servers."""
        if not self._servers:
            return

        async def disconnect_server(name: str, server: MCPServer) -> None:
            try:
                await server.disconnect()
                logger.info(f"Disconnected from MCP server: {name}")
            except Exception as e:
                logger.error(f"Error disconnecting server {name}: {e}")

        await asyncio.gather(*[
            disconnect_server(name, server)
            for name, server in self._servers.items()
        ])

        # Clear tool cache
        self._tools.clear()
        self._tool_to_server.clear()

    async def discover_tools(self) -> List[MCPToolDefinition]:
        """Discover all tools from connected servers.

        Returns:
            List of all available tools across all servers.
        """
        all_tools: List[MCPToolDefinition] = []

        for name, server in self._servers.items():
            if not server.is_connected:
                logger.debug(f"Skipping disconnected server: {name}")
                continue

            try:
                tools = await server.list_tools()
                all_tools.extend(tools)

                # Build tool index
                for tool in tools:
                    key = f"{name}:{tool.name}"
                    self._tools[key] = tool

                    # Map tool name to server (first server wins)
                    if tool.name not in self._tool_to_server:
                        self._tool_to_server[tool.name] = name

                logger.info(
                    f"Discovered {len(tools)} tools from server: {name}"
                )
            except Exception as e:
                logger.error(f"Failed to discover tools from {name}: {e}")

        return all_tools

    def find_tool_server(self, tool_name: str) -> Optional[str]:
        """Find which server provides a tool.

        Args:
            tool_name: Name of the tool.

        Returns:
            Server name if found, None otherwise.
        """
        return self._tool_to_server.get(tool_name)

    def get_tool(self, tool_ref: str) -> Optional[MCPToolDefinition]:
        """Get a tool by reference.

        Args:
            tool_ref: Tool reference in "server:tool" or "tool" format.

        Returns:
            MCPToolDefinition if found, None otherwise.
        """
        if ":" in tool_ref:
            return self._tools.get(tool_ref)
        else:
            # Search by tool name
            server_name = self._tool_to_server.get(tool_ref)
            if server_name:
                return self._tools.get(f"{server_name}:{tool_ref}")
        return None

    async def execute_tool(
        self,
        tool_ref: str,
        arguments: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> MCPToolResult:
        """Execute a tool by reference.

        Args:
            tool_ref: Tool reference in "server:tool" or "tool" format.
            arguments: Tool arguments.
            timeout: Execution timeout in seconds.

        Returns:
            MCPToolResult with execution result.

        Raises:
            MCPToolNotFoundError: If tool is not found.
            MCPDisconnectedError: If server is not connected.
        """
        # Parse tool reference
        if ":" in tool_ref:
            server_name, tool_name = tool_ref.split(":", 1)
        else:
            tool_name = tool_ref
            server_name = self._tool_to_server.get(tool_name)
            if not server_name:
                raise MCPToolNotFoundError(tool_name)

        # Get server
        server = self._servers.get(server_name)
        if not server:
            raise MCPToolNotFoundError(tool_name, server_name)

        if not server.is_connected:
            raise MCPDisconnectedError(
                f"Server not connected: {server_name}"
            )

        # Execute tool
        return await server.execute_tool(tool_name, arguments, timeout)

    def list_servers(self) -> List[ServerInfo]:
        """List all servers with their status.

        Returns:
            List of ServerInfo objects.
        """
        result = []
        for name, server in self._servers.items():
            tools_count = sum(
                1 for key in self._tools if key.startswith(f"{name}:")
            )
            result.append(ServerInfo(
                name=name,
                connected=server.is_connected,
                tools_count=tools_count,
                state=server.state.value,
            ))
        return result

    async def health_check(self) -> Dict[str, HealthCheckResult]:
        """Perform health check on all servers.

        Returns:
            Dictionary mapping server names to health check results.
        """
        results: Dict[str, HealthCheckResult] = {}

        async def check_server(name: str, server: MCPServer) -> None:
            if not server.is_connected:
                results[name] = HealthCheckResult(
                    name=name,
                    healthy=False,
                    error="Not connected",
                )
                return

            try:
                start = time.time()
                await server.list_tools()
                latency = (time.time() - start) * 1000

                results[name] = HealthCheckResult(
                    name=name,
                    healthy=True,
                    latency_ms=latency,
                )
            except Exception as e:
                results[name] = HealthCheckResult(
                    name=name,
                    healthy=False,
                    error=str(e),
                )

        await asyncio.gather(*[
            check_server(name, server)
            for name, server in self._servers.items()
        ])

        return results

    async def reconnect_unhealthy(self) -> Dict[str, bool]:
        """Reconnect to unhealthy servers.

        Returns:
            Dictionary mapping server names to reconnection success.
        """
        health = await self.health_check()
        unhealthy = [
            name for name, result in health.items()
            if not result.healthy
        ]

        if not unhealthy:
            return {}

        results: Dict[str, bool] = {}

        for name in unhealthy:
            server = self._servers.get(name)
            if not server:
                continue

            try:
                await server.disconnect()
            except Exception:
                pass

            results[name] = await self.connect_server(name)

        return results

    async def __aenter__(self) -> "MCPManager":
        """Enter async context manager."""
        await self.connect_all()
        if self._auto_discover:
            await self.discover_tools()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager."""
        await self.disconnect_all()


# Factory function for convenience
def create_manager(
    auto_discover: bool = True,
    connection_timeout: float = 30.0,
) -> MCPManager:
    """Create an MCPManager instance.

    Args:
        auto_discover: Whether to auto-discover tools on connect.
        connection_timeout: Timeout for server connections.

    Returns:
        MCPManager instance.
    """
    return MCPManager(
        auto_discover=auto_discover,
        connection_timeout=connection_timeout,
    )
