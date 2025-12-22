"""MCP Transport Layer.

This module provides transport implementations for MCP communication,
supporting different transport mechanisms:
    - StdioTransport: Communication via stdin/stdout with subprocess
    - (Future) SSETransport: Server-Sent Events transport
    - (Future) WebSocketTransport: WebSocket transport

The transport layer handles low-level communication details and provides
a consistent async interface for the MCP client.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import asyncio
import json
import logging
import os

from .types import MCPRequest, MCPResponse

logger = logging.getLogger(__name__)


class TransportError(Exception):
    """Base exception for transport errors."""

    pass


class ConnectionError(TransportError):
    """Error establishing or maintaining connection."""

    pass


class TimeoutError(TransportError):
    """Operation timed out."""

    pass


class BaseTransport(ABC):
    """Abstract base class for MCP transports.

    All transport implementations must inherit from this class
    and implement the abstract methods.
    """

    @abstractmethod
    async def start(self) -> None:
        """Start the transport connection."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the transport connection."""
        pass

    @abstractmethod
    async def send(self, request: MCPRequest) -> MCPResponse:
        """Send a request and receive response.

        Args:
            request: MCP request to send

        Returns:
            MCP response from server
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if transport is connected."""
        pass


class StdioTransport(BaseTransport):
    """Stdio-based transport for MCP communication.

    Communicates with MCP servers via stdin/stdout of a subprocess.
    Messages are JSON-RPC 2.0 format, one per line.

    Attributes:
        command: The command to execute
        args: Command arguments
        env: Environment variables for the subprocess
        timeout: Default timeout for operations in seconds

    Example:
        >>> transport = StdioTransport(
        ...     command="python",
        ...     args=["-m", "mcp_servers.azure"],
        ...     env={"AZURE_SUBSCRIPTION_ID": "..."},
        ... )
        >>> await transport.start()
        >>> response = await transport.send(request)
        >>> await transport.stop()
    """

    def __init__(
        self,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
        cwd: Optional[str] = None,
    ):
        """Initialize stdio transport.

        Args:
            command: Command to execute
            args: Command arguments
            env: Additional environment variables (merged with current env)
            timeout: Default timeout for operations
            cwd: Working directory for subprocess
        """
        self._command = command
        self._args = args or []
        self._env = env or {}
        self._timeout = timeout
        self._cwd = cwd

        self._process: Optional[asyncio.subprocess.Process] = None
        self._read_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()
        self._pending_requests: Dict[Any, asyncio.Future] = {}
        self._reader_task: Optional[asyncio.Task] = None
        self._connected = False

    async def start(self) -> None:
        """Start the subprocess and establish connection.

        Raises:
            ConnectionError: If subprocess fails to start
        """
        if self._connected:
            logger.warning("Transport already started")
            return

        # Merge environment variables
        process_env = os.environ.copy()
        process_env.update(self._env)

        try:
            self._process = await asyncio.create_subprocess_exec(
                self._command,
                *self._args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env,
                cwd=self._cwd,
            )

            self._connected = True

            # Start background reader
            self._reader_task = asyncio.create_task(self._read_loop())

            logger.info(
                f"Started MCP server: {self._command} {' '.join(self._args)}"
            )

        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise ConnectionError(f"Failed to start subprocess: {e}") from e

    async def stop(self) -> None:
        """Stop the subprocess and close connection."""
        if not self._connected:
            return

        self._connected = False

        # Cancel reader task
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

        # Cancel pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()

        # Terminate process
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
            except Exception as e:
                logger.warning(f"Error stopping process: {e}")
            finally:
                self._process = None

        logger.info("MCP server stopped")

    async def send(
        self,
        request: MCPRequest,
        timeout: Optional[float] = None,
    ) -> MCPResponse:
        """Send a request and wait for response.

        Args:
            request: MCP request to send
            timeout: Optional timeout override

        Returns:
            MCP response

        Raises:
            ConnectionError: If not connected
            TimeoutError: If response times out
        """
        if not self._connected or not self._process:
            raise ConnectionError("Transport not connected")

        timeout = timeout or self._timeout

        # Create future for response
        response_future: asyncio.Future = asyncio.Future()
        self._pending_requests[request.id] = response_future

        try:
            # Send request
            async with self._write_lock:
                request_json = json.dumps(request.to_dict()) + "\n"
                self._process.stdin.write(request_json.encode())
                await self._process.stdin.drain()

            logger.debug(f"Sent MCP request: {request.method} (id={request.id})")

            # Wait for response
            response = await asyncio.wait_for(response_future, timeout=timeout)
            return response

        except asyncio.TimeoutError:
            logger.error(f"Request timeout: {request.method}")
            raise TimeoutError(f"Request timeout: {request.method}")

        except Exception as e:
            logger.error(f"Send error: {e}")
            raise TransportError(f"Send error: {e}") from e

        finally:
            self._pending_requests.pop(request.id, None)

    def is_connected(self) -> bool:
        """Check if transport is connected."""
        return self._connected and self._process is not None

    async def _read_loop(self) -> None:
        """Background task to read responses from stdout."""
        if not self._process or not self._process.stdout:
            return

        try:
            while self._connected:
                line = await self._process.stdout.readline()

                if not line:
                    if self._connected:
                        logger.warning("MCP server closed connection")
                        self._connected = False
                    break

                try:
                    data = json.loads(line.decode().strip())
                    response = MCPResponse.from_dict(data)

                    # Match response to pending request
                    if response.id in self._pending_requests:
                        future = self._pending_requests[response.id]
                        if not future.done():
                            future.set_result(response)
                    else:
                        # Notification or unmatched response
                        logger.debug(f"Received notification/unmatched: {data}")

                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON from server: {e}")
                except Exception as e:
                    logger.error(f"Error processing response: {e}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Read loop error: {e}")
            self._connected = False

    async def read_stderr(self) -> str:
        """Read available stderr output.

        Returns:
            Stderr content as string
        """
        if not self._process or not self._process.stderr:
            return ""

        try:
            # Non-blocking read of available stderr
            data = await asyncio.wait_for(
                self._process.stderr.read(4096),
                timeout=0.1,
            )
            return data.decode() if data else ""
        except asyncio.TimeoutError:
            return ""
        except Exception:
            return ""


class InMemoryTransport(BaseTransport):
    """In-memory transport for testing.

    Routes requests directly to a protocol handler without subprocess.
    Useful for unit testing and local development.
    """

    def __init__(self, protocol: Any = None):
        """Initialize in-memory transport.

        Args:
            protocol: MCPProtocol instance to handle requests
        """
        self._protocol = protocol
        self._connected = False

    async def start(self) -> None:
        """Start the transport (no-op for in-memory)."""
        self._connected = True

    async def stop(self) -> None:
        """Stop the transport (no-op for in-memory)."""
        self._connected = False

    async def send(self, request: MCPRequest) -> MCPResponse:
        """Send request directly to protocol handler.

        Args:
            request: MCP request

        Returns:
            MCP response from protocol handler
        """
        if not self._connected:
            raise ConnectionError("Transport not connected")

        if not self._protocol:
            raise ConnectionError("No protocol handler configured")

        return await self._protocol.handle_request(request)

    def is_connected(self) -> bool:
        """Check if transport is connected."""
        return self._connected

    def set_protocol(self, protocol: Any) -> None:
        """Set the protocol handler.

        Args:
            protocol: MCPProtocol instance
        """
        self._protocol = protocol
