"""MCP Server base class.

Sprint 50: S50-1 - MCP Server 基礎 (10 pts)
Abstract base class for MCP server implementations.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .exceptions import MCPDisconnectedError, MCPToolNotFoundError
from .types import (
    MCPMessage,
    MCPServerConfig,
    MCPServerState,
    MCPToolDefinition,
    MCPToolResult,
)

logger = logging.getLogger(__name__)


class MCPServer(ABC):
    """Abstract base class for MCP servers.

    Defines the interface for connecting to MCP servers,
    discovering tools, and executing tool calls.

    Supports both stdio (local process) and HTTP (remote) transports.
    """

    def __init__(self, config: MCPServerConfig):
        """Initialize MCP server.

        Args:
            config: Server configuration.
        """
        self.config = config
        self.name = config.name
        self._state = MCPServerState.DISCONNECTED
        self._tools: Dict[str, MCPToolDefinition] = {}
        self._message_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._lock = asyncio.Lock()

    @property
    def state(self) -> MCPServerState:
        """Get current server state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if server is connected."""
        return self._state == MCPServerState.CONNECTED

    @property
    def tools(self) -> List[MCPToolDefinition]:
        """Get list of available tools."""
        return list(self._tools.values())

    def get_tool(self, name: str) -> Optional[MCPToolDefinition]:
        """Get tool by name.

        Args:
            name: Tool name.

        Returns:
            Tool definition or None if not found.
        """
        return self._tools.get(name)

    def has_tool(self, name: str) -> bool:
        """Check if tool exists.

        Args:
            name: Tool name.

        Returns:
            True if tool exists.
        """
        return name in self._tools

    def _next_message_id(self) -> int:
        """Get next message ID."""
        self._message_id += 1
        return self._message_id

    async def connect(self) -> None:
        """Connect to MCP server.

        Establishes connection and discovers available tools.

        Raises:
            MCPConnectionError: If connection fails.
        """
        if self._state == MCPServerState.CONNECTED:
            logger.debug(f"Server {self.name} already connected")
            return

        self._state = MCPServerState.CONNECTING
        logger.info(f"Connecting to MCP server: {self.name}")

        try:
            await self._connect()
            await self._initialize()
            await self._discover_tools()
            self._state = MCPServerState.CONNECTED
            logger.info(
                f"Connected to MCP server: {self.name} "
                f"({len(self._tools)} tools available)"
            )
        except Exception as e:
            self._state = MCPServerState.ERROR
            logger.error(f"Failed to connect to {self.name}: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        if self._state == MCPServerState.DISCONNECTED:
            return

        logger.info(f"Disconnecting from MCP server: {self.name}")

        try:
            await self._disconnect()
        except Exception as e:
            logger.warning(f"Error during disconnect from {self.name}: {e}")
        finally:
            self._state = MCPServerState.DISCONNECTED
            self._tools.clear()
            self._cancel_pending_requests()

    def _cancel_pending_requests(self) -> None:
        """Cancel all pending requests."""
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()

    async def list_tools(self) -> List[MCPToolDefinition]:
        """List available tools.

        Returns:
            List of tool definitions.

        Raises:
            MCPDisconnectedError: If not connected.
        """
        if not self.is_connected:
            raise MCPDisconnectedError(f"Server {self.name} is not connected")

        return self.tools

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> MCPToolResult:
        """Execute a tool.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.
            timeout: Execution timeout in seconds.

        Returns:
            Tool execution result.

        Raises:
            MCPDisconnectedError: If not connected.
            MCPToolNotFoundError: If tool not found.
            MCPToolExecutionError: If execution fails.
            MCPTimeoutError: If execution times out.
        """
        if not self.is_connected:
            raise MCPDisconnectedError(f"Server {self.name} is not connected")

        if not self.has_tool(tool_name):
            raise MCPToolNotFoundError(tool_name, self.name)

        timeout = timeout or self.config.timeout

        import time

        start_time = time.time()

        try:
            result = await asyncio.wait_for(
                self._execute_tool(tool_name, arguments or {}),
                timeout=timeout,
            )
            execution_time = (time.time() - start_time) * 1000

            return MCPToolResult(
                success=True,
                content=result,
                tool_name=tool_name,
                execution_time_ms=execution_time,
            )
        except asyncio.TimeoutError:
            from .exceptions import MCPTimeoutError

            raise MCPTimeoutError(
                f"Tool {tool_name} execution timed out after {timeout}s"
            )
        except Exception as e:
            from .exceptions import MCPToolExecutionError

            raise MCPToolExecutionError(tool_name, str(e), self.name)

    async def send_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """Send a JSON-RPC request.

        Args:
            method: RPC method name.
            params: Method parameters.
            timeout: Request timeout in seconds.

        Returns:
            Response result.

        Raises:
            MCPDisconnectedError: If not connected.
            MCPTimeoutError: If request times out.
            MCPServerError: If server returns an error.
        """
        if not self.is_connected and method not in ("initialize",):
            raise MCPDisconnectedError(f"Server {self.name} is not connected")

        timeout = timeout or self.config.timeout
        message_id = self._next_message_id()

        message = MCPMessage.request(method, params, message_id)
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_requests[message_id] = future

        try:
            await self._send_message(message)

            response = await asyncio.wait_for(future, timeout=timeout)

            if response.error:
                from .exceptions import MCPServerError

                raise MCPServerError.from_response(response.error)

            return response.result

        except asyncio.TimeoutError:
            from .exceptions import MCPTimeoutError

            raise MCPTimeoutError(
                f"Request {method} timed out after {timeout}s"
            )
        finally:
            self._pending_requests.pop(message_id, None)

    def _handle_response(self, message: MCPMessage) -> None:
        """Handle incoming response message.

        Args:
            message: Response message.
        """
        if message.id is None:
            logger.warning(f"Received response without ID: {message}")
            return

        future = self._pending_requests.get(message.id)
        if future and not future.done():
            future.set_result(message)
        else:
            logger.warning(f"No pending request for ID {message.id}")

    # Abstract methods to be implemented by subclasses

    @abstractmethod
    async def _connect(self) -> None:
        """Establish connection to server.

        Subclasses implement transport-specific connection logic.
        """
        pass

    @abstractmethod
    async def _disconnect(self) -> None:
        """Close connection to server.

        Subclasses implement transport-specific disconnection logic.
        """
        pass

    @abstractmethod
    async def _send_message(self, message: MCPMessage) -> None:
        """Send message to server.

        Args:
            message: Message to send.
        """
        pass

    @abstractmethod
    async def _execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Any:
        """Execute tool on server.

        Args:
            tool_name: Tool name.
            arguments: Tool arguments.

        Returns:
            Tool execution result.
        """
        pass

    async def _initialize(self) -> None:
        """Initialize MCP protocol.

        Sends initialize request to server.
        """
        try:
            result = await self.send_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                    },
                    "clientInfo": {
                        "name": "claude-sdk",
                        "version": "1.0.0",
                    },
                },
            )
            logger.debug(f"Server {self.name} initialized: {result}")
        except Exception as e:
            logger.warning(f"Initialize failed for {self.name}: {e}")
            # Some servers may not support initialize, continue anyway

    async def _discover_tools(self) -> None:
        """Discover available tools from server."""
        try:
            result = await self.send_request("tools/list")

            tools = result.get("tools", []) if isinstance(result, dict) else []

            for tool_data in tools:
                tool = MCPToolDefinition(
                    name=tool_data.get("name", ""),
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", {}),
                    server_name=self.name,
                )
                self._tools[tool.name] = tool

            logger.debug(
                f"Discovered {len(self._tools)} tools from {self.name}"
            )

        except Exception as e:
            logger.warning(f"Tool discovery failed for {self.name}: {e}")
            # Continue with empty tools list

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"{self.__class__.__name__}("
            f"name={self.name!r}, "
            f"state={self._state.value}, "
            f"tools={len(self._tools)})"
        )
