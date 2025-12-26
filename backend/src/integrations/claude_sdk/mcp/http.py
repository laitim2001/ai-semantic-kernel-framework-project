"""MCP HTTP Server implementation.

Sprint 50: S50-1 - MCP Server 基礎 (10 pts)
Remote HTTP-based MCP server using JSON-RPC over HTTP.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from .base import MCPServer
from .exceptions import MCPConnectionError, MCPServerError
from .types import MCPMessage, MCPServerConfig, MCPTransportType

logger = logging.getLogger(__name__)

# Check for aiohttp availability
try:
    import aiohttp

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = None  # type: ignore


class MCPHTTPServer(MCPServer):
    """MCP server using HTTP transport.

    Communicates with a remote MCP server via HTTP POST requests
    using JSON-RPC protocol.

    Example:
        config = MCPServerConfig(
            name="remote-tools",
            transport=MCPTransportType.HTTP,
            url="https://mcp.example.com/rpc",
            headers={"Authorization": "Bearer token"},
        )
        server = MCPHTTPServer(config)
        await server.connect()
        tools = await server.list_tools()
    """

    def __init__(self, config: MCPServerConfig):
        """Initialize HTTP server.

        Args:
            config: Server configuration with URL and headers.
        """
        super().__init__(config)
        self._session: Optional["aiohttp.ClientSession"] = None

    async def _connect(self) -> None:
        """Establish HTTP session.

        Raises:
            MCPConnectionError: If connection fails or aiohttp not available.
        """
        if not AIOHTTP_AVAILABLE:
            raise MCPConnectionError(
                "aiohttp is required for HTTP transport. "
                "Install with: pip install aiohttp"
            )

        if not self.config.url:
            raise MCPConnectionError(
                f"No URL specified for server {self.name}"
            )

        try:
            # Create session with default headers
            headers = {
                "Content-Type": "application/json",
                **self.config.headers,
            }

            timeout = aiohttp.ClientTimeout(total=self.config.timeout)

            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout,
            )

            # Test connection with a simple request
            await self._test_connection()

            logger.info(f"Connected to HTTP MCP server: {self.name}")

        except aiohttp.ClientError as e:
            raise MCPConnectionError(
                f"Failed to connect to {self.name}: {e}"
            )

    async def _test_connection(self) -> None:
        """Test connection to server.

        Raises:
            MCPConnectionError: If connection test fails.
        """
        if not self._session:
            return

        try:
            # Try to reach the server
            async with self._session.get(
                self.config.url,
                timeout=aiohttp.ClientTimeout(total=5.0),
            ) as response:
                # Accept any response as connection success
                # Server may return error for GET, but that's OK
                logger.debug(
                    f"Connection test for {self.name}: "
                    f"status={response.status}"
                )
        except aiohttp.ClientError as e:
            raise MCPConnectionError(
                f"Connection test failed for {self.name}: {e}"
            )

    async def _disconnect(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.info(f"Disconnected from HTTP MCP server: {self.name}")

    async def _send_message(self, message: MCPMessage) -> None:
        """Send message via HTTP POST.

        For HTTP transport, responses are received in the same request,
        so this method handles the request/response cycle differently.

        Args:
            message: JSON-RPC message to send.

        Note:
            HTTP transport doesn't use async read loop like stdio.
            Responses are handled synchronously in send_request.
        """
        # For HTTP, actual sending is done in send_request
        # This method is not used for HTTP transport
        pass

    async def send_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """Send HTTP JSON-RPC request.

        Overrides base class to handle HTTP request/response.

        Args:
            method: RPC method name.
            params: Method parameters.
            timeout: Request timeout in seconds.

        Returns:
            Response result.

        Raises:
            MCPConnectionError: If not connected.
            MCPTimeoutError: If request times out.
            MCPServerError: If server returns an error.
        """
        if not self._session:
            raise MCPConnectionError(f"Server {self.name} is not connected")

        timeout_value = timeout or self.config.timeout
        message_id = self._next_message_id()

        message = MCPMessage.request(method, params, message_id)
        payload = message.to_dict()

        try:
            request_timeout = aiohttp.ClientTimeout(total=timeout_value)

            async with self._session.post(
                self.config.url,
                json=payload,
                timeout=request_timeout,
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    raise MCPServerError(
                        code=-32000,
                        message=f"HTTP {response.status}: {text[:200]}",
                    )

                data = await response.json()

                if "error" in data:
                    raise MCPServerError.from_response(data["error"])

                return data.get("result")

        except asyncio.TimeoutError:
            from .exceptions import MCPTimeoutError

            raise MCPTimeoutError(
                f"Request {method} timed out after {timeout_value}s"
            )
        except aiohttp.ClientError as e:
            raise MCPConnectionError(f"HTTP request failed: {e}")

    async def _execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Any:
        """Execute tool via HTTP JSON-RPC call.

        Args:
            tool_name: Tool name.
            arguments: Tool arguments.

        Returns:
            Tool result content.
        """
        result = await self.send_request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments,
            },
        )

        # Extract content from result
        if isinstance(result, dict):
            content = result.get("content", [])
            if isinstance(content, list) and len(content) > 0:
                first_item = content[0]
                if isinstance(first_item, dict):
                    return first_item.get("text", first_item)
                return first_item
            return result

        return result

    @property
    def url(self) -> Optional[str]:
        """Get server URL."""
        return self.config.url


def create_http_server(
    name: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
    **kwargs: Any,
) -> MCPHTTPServer:
    """Create an HTTP MCP server.

    Convenience function for creating MCPHTTPServer instances.

    Args:
        name: Server name.
        url: Server URL (JSON-RPC endpoint).
        headers: HTTP headers (e.g., Authorization).
        timeout: Request timeout in seconds.
        **kwargs: Additional config options.

    Returns:
        Configured MCPHTTPServer instance.

    Example:
        server = create_http_server(
            name="remote-tools",
            url="https://mcp.example.com/rpc",
            headers={"Authorization": "Bearer token"},
        )
    """
    config = MCPServerConfig(
        name=name,
        transport=MCPTransportType.HTTP,
        url=url,
        headers=headers or {},
        timeout=timeout,
        **kwargs,
    )
    return MCPHTTPServer(config)
