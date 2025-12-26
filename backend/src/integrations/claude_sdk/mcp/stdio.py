"""MCP Stdio Server implementation.

Sprint 50: S50-1 - MCP Server 基礎 (10 pts)
Local process-based MCP server using JSON-RPC over stdio.

Security Note: This module uses asyncio.create_subprocess_exec which is
the secure alternative to shell execution. Arguments are passed as a list,
not through a shell, preventing command injection vulnerabilities.
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

from .base import MCPServer
from .exceptions import MCPConnectionError
from .types import MCPMessage, MCPServerConfig, MCPServerState

logger = logging.getLogger(__name__)


class MCPStdioServer(MCPServer):
    """MCP server using stdio transport.

    Launches a local process and communicates via JSON-RPC
    over stdin/stdout.

    Security: Uses create_subprocess_exec (not shell) to prevent
    command injection. Arguments are passed as a list.

    Example:
        config = MCPServerConfig(
            name="filesystem",
            command="npx",
            args=["-y", "@anthropic/mcp-filesystem"],
        )
        server = MCPStdioServer(config)
        await server.connect()
        tools = await server.list_tools()
    """

    def __init__(self, config: MCPServerConfig):
        """Initialize stdio server.

        Args:
            config: Server configuration with command and args.
        """
        super().__init__(config)
        self._process: Optional[asyncio.subprocess.Process] = None
        self._read_task: Optional[asyncio.Task] = None
        self._buffer = ""

    async def _connect(self) -> None:
        """Start the MCP server process.

        Uses create_subprocess_exec for security (no shell).

        Raises:
            MCPConnectionError: If process fails to start.
        """
        if not self.config.command:
            raise MCPConnectionError(
                f"No command specified for server {self.name}"
            )

        # Prepare environment
        env = os.environ.copy()
        env.update(self.config.env)

        # Build command arguments list (secure - no shell interpolation)
        cmd_args: List[str] = list(self.config.args)

        # Start process using create_subprocess_exec (secure, no shell)
        try:
            logger.debug(
                f"Starting process: {self.config.command} "
                f"{' '.join(cmd_args)}"
            )

            # create_subprocess_exec is secure - arguments passed as list
            # This is equivalent to Node.js execFile, not exec
            self._process = await asyncio.create_subprocess_exec(
                self.config.command,
                *cmd_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.config.cwd,
                env=env,
            )

            # Start reading responses
            self._read_task = asyncio.create_task(self._read_loop())

            logger.info(
                f"Started MCP process {self.name} (PID: {self._process.pid})"
            )

        except FileNotFoundError:
            raise MCPConnectionError(
                f"Command not found: {self.config.command}"
            )
        except PermissionError:
            raise MCPConnectionError(
                f"Permission denied: {self.config.command}"
            )
        except OSError as e:
            raise MCPConnectionError(
                f"Failed to start process for {self.name}: {e}"
            )

    async def _disconnect(self) -> None:
        """Stop the MCP server process."""
        # Cancel read task
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
            self._read_task = None

        # Terminate process
        if self._process:
            try:
                # Try graceful shutdown first
                self._process.terminate()
                try:
                    await asyncio.wait_for(
                        self._process.wait(),
                        timeout=5.0,
                    )
                except asyncio.TimeoutError:
                    # Force kill if still running
                    self._process.kill()
                    await self._process.wait()

                logger.info(f"Stopped MCP process {self.name}")
            except ProcessLookupError:
                # Process already terminated
                pass
            except OSError as e:
                logger.warning(f"Error stopping process {self.name}: {e}")
            finally:
                self._process = None

    async def _send_message(self, message: MCPMessage) -> None:
        """Send message to process stdin.

        Args:
            message: JSON-RPC message to send.

        Raises:
            MCPConnectionError: If process is not running.
        """
        if not self._process or not self._process.stdin:
            raise MCPConnectionError(f"Process {self.name} is not running")

        try:
            data = json.dumps(message.to_dict())
            line = data + "\n"

            logger.debug(f"Sending to {self.name}: {data[:200]}...")

            self._process.stdin.write(line.encode("utf-8"))
            await self._process.stdin.drain()

        except OSError as e:
            logger.error(f"Failed to send message to {self.name}: {e}")
            raise MCPConnectionError(f"Failed to send message: {e}")

    async def _read_loop(self) -> None:
        """Read responses from process stdout."""
        if not self._process or not self._process.stdout:
            return

        try:
            while True:
                line = await self._process.stdout.readline()
                if not line:
                    # Process terminated
                    logger.warning(f"Process {self.name} stdout closed")
                    break

                try:
                    text = line.decode("utf-8").strip()
                    if not text:
                        continue

                    logger.debug(f"Received from {self.name}: {text[:200]}...")

                    data = json.loads(text)
                    message = MCPMessage.from_dict(data)
                    self._handle_response(message)

                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON from {self.name}: {e}")
                except ValueError as e:
                    logger.error(f"Error processing message from {self.name}: {e}")

        except asyncio.CancelledError:
            raise
        except OSError as e:
            logger.error(f"Read loop error for {self.name}: {e}")
            self._state = MCPServerState.ERROR

    async def _execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Any:
        """Execute tool via JSON-RPC call.

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
                # Return first content item's text
                first_item = content[0]
                if isinstance(first_item, dict):
                    return first_item.get("text", first_item)
                return first_item
            return result

        return result

    async def get_stderr(self) -> str:
        """Get stderr output from process.

        Returns:
            Stderr content if available.
        """
        if not self._process or not self._process.stderr:
            return ""

        try:
            # Non-blocking read of available stderr
            stderr_data = await asyncio.wait_for(
                self._process.stderr.read(4096),
                timeout=0.1,
            )
            return stderr_data.decode("utf-8")
        except asyncio.TimeoutError:
            return ""
        except OSError:
            return ""

    @property
    def pid(self) -> Optional[int]:
        """Get process ID if running."""
        return self._process.pid if self._process else None


def create_stdio_server(
    name: str,
    command: str,
    args: Optional[List[str]] = None,
    env: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None,
    **kwargs: Any,
) -> MCPStdioServer:
    """Create a stdio MCP server.

    Convenience function for creating MCPStdioServer instances.

    Args:
        name: Server name.
        command: Command to run (path to executable).
        args: Command arguments (passed as list, not shell).
        env: Environment variables.
        cwd: Working directory.
        **kwargs: Additional config options.

    Returns:
        Configured MCPStdioServer instance.

    Example:
        server = create_stdio_server(
            name="filesystem",
            command="npx",
            args=["-y", "@anthropic/mcp-filesystem"],
        )
    """
    config = MCPServerConfig(
        name=name,
        command=command,
        args=args or [],
        env=env or {},
        cwd=cwd,
        **kwargs,
    )
    return MCPStdioServer(config)
