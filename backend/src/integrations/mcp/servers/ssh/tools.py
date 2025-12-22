"""SSH MCP tools.

Provides tool definitions for SSH operations.

Tools:
    - ssh_connect: Connect to SSH server
    - ssh_execute: Execute command on remote host
    - ssh_upload: Upload file via SFTP
    - ssh_download: Download file via SFTP
    - ssh_list_directory: List remote directory
    - ssh_disconnect: Disconnect from SSH server
"""

import logging
from typing import Any, Dict, List, Optional

from ...core.types import (
    ToolSchema,
    ToolParameter,
    ToolInputType,
    ToolResult,
)
from .client import SSHConnectionManager, SSHConfig

logger = logging.getLogger(__name__)


class SSHTools:
    """SSH tools for MCP Server.

    Provides SSH operations through the MCP protocol.

    Permission Levels:
        - ssh_connect: Level 3 (HIGH) - Requires human approval
        - ssh_execute: Level 3 (HIGH) - Requires human approval
        - ssh_upload: Level 3 (HIGH) - Requires human approval
        - ssh_download: Level 2 (EXECUTE) - Requires approval
        - ssh_list_directory: Level 2 (EXECUTE) - Requires approval
        - ssh_disconnect: Level 1 (READ) - Low risk

    Example:
        >>> manager = SSHConnectionManager(config)
        >>> tools = SSHTools(manager)
        >>> result = await tools.ssh_connect(
        ...     host="server.example.com",
        ...     username="admin",
        ...     password="secret"
        ... )
    """

    PERMISSION_LEVELS = {
        "ssh_connect": 3,        # HIGH - requires human approval
        "ssh_execute": 3,        # HIGH - requires human approval
        "ssh_upload": 3,         # HIGH - requires human approval
        "ssh_download": 2,       # EXECUTE - requires approval
        "ssh_list_directory": 2, # EXECUTE - requires approval
        "ssh_disconnect": 1,     # READ - low risk
    }

    def __init__(self, connection_manager: SSHConnectionManager):
        """Initialize SSH tools.

        Args:
            connection_manager: SSH connection manager
        """
        self._manager = connection_manager

    @staticmethod
    def get_schemas() -> List[ToolSchema]:
        """Get all SSH tool schemas.

        Returns:
            List of ToolSchema definitions for MCP protocol
        """
        return [
            ToolSchema(
                name="ssh_connect",
                description="Connect to an SSH server. Use either password or private key authentication.",
                parameters=[
                    ToolParameter(
                        name="host",
                        type=ToolInputType.STRING,
                        description="Remote hostname or IP address",
                        required=True,
                    ),
                    ToolParameter(
                        name="username",
                        type=ToolInputType.STRING,
                        description="SSH username",
                        required=True,
                    ),
                    ToolParameter(
                        name="port",
                        type=ToolInputType.INTEGER,
                        description="SSH port (default: 22)",
                        required=False,
                    ),
                    ToolParameter(
                        name="password",
                        type=ToolInputType.STRING,
                        description="Password for authentication (either password or private_key_path required)",
                        required=False,
                    ),
                    ToolParameter(
                        name="private_key_path",
                        type=ToolInputType.STRING,
                        description="Path to private key file",
                        required=False,
                    ),
                    ToolParameter(
                        name="private_key_passphrase",
                        type=ToolInputType.STRING,
                        description="Passphrase for private key (if encrypted)",
                        required=False,
                    ),
                ],
            ),
            ToolSchema(
                name="ssh_execute",
                description="Execute a command on a connected SSH server.",
                parameters=[
                    ToolParameter(
                        name="host",
                        type=ToolInputType.STRING,
                        description="Remote hostname (must be connected)",
                        required=True,
                    ),
                    ToolParameter(
                        name="username",
                        type=ToolInputType.STRING,
                        description="SSH username",
                        required=True,
                    ),
                    ToolParameter(
                        name="command",
                        type=ToolInputType.STRING,
                        description="Command to execute",
                        required=True,
                    ),
                    ToolParameter(
                        name="port",
                        type=ToolInputType.INTEGER,
                        description="SSH port (default: 22)",
                        required=False,
                    ),
                    ToolParameter(
                        name="timeout",
                        type=ToolInputType.INTEGER,
                        description="Command timeout in seconds (default: 60)",
                        required=False,
                    ),
                ],
            ),
            ToolSchema(
                name="ssh_upload",
                description="Upload a file to a remote host via SFTP.",
                parameters=[
                    ToolParameter(
                        name="host",
                        type=ToolInputType.STRING,
                        description="Remote hostname (must be connected)",
                        required=True,
                    ),
                    ToolParameter(
                        name="username",
                        type=ToolInputType.STRING,
                        description="SSH username",
                        required=True,
                    ),
                    ToolParameter(
                        name="local_path",
                        type=ToolInputType.STRING,
                        description="Local file path to upload",
                        required=True,
                    ),
                    ToolParameter(
                        name="remote_path",
                        type=ToolInputType.STRING,
                        description="Remote destination path",
                        required=True,
                    ),
                    ToolParameter(
                        name="port",
                        type=ToolInputType.INTEGER,
                        description="SSH port (default: 22)",
                        required=False,
                    ),
                ],
            ),
            ToolSchema(
                name="ssh_download",
                description="Download a file from a remote host via SFTP.",
                parameters=[
                    ToolParameter(
                        name="host",
                        type=ToolInputType.STRING,
                        description="Remote hostname (must be connected)",
                        required=True,
                    ),
                    ToolParameter(
                        name="username",
                        type=ToolInputType.STRING,
                        description="SSH username",
                        required=True,
                    ),
                    ToolParameter(
                        name="remote_path",
                        type=ToolInputType.STRING,
                        description="Remote file path to download",
                        required=True,
                    ),
                    ToolParameter(
                        name="local_path",
                        type=ToolInputType.STRING,
                        description="Local destination path",
                        required=True,
                    ),
                    ToolParameter(
                        name="port",
                        type=ToolInputType.INTEGER,
                        description="SSH port (default: 22)",
                        required=False,
                    ),
                ],
            ),
            ToolSchema(
                name="ssh_list_directory",
                description="List contents of a remote directory via SFTP.",
                parameters=[
                    ToolParameter(
                        name="host",
                        type=ToolInputType.STRING,
                        description="Remote hostname (must be connected)",
                        required=True,
                    ),
                    ToolParameter(
                        name="username",
                        type=ToolInputType.STRING,
                        description="SSH username",
                        required=True,
                    ),
                    ToolParameter(
                        name="remote_path",
                        type=ToolInputType.STRING,
                        description="Remote directory path to list",
                        required=True,
                    ),
                    ToolParameter(
                        name="port",
                        type=ToolInputType.INTEGER,
                        description="SSH port (default: 22)",
                        required=False,
                    ),
                ],
            ),
            ToolSchema(
                name="ssh_disconnect",
                description="Disconnect from an SSH server.",
                parameters=[
                    ToolParameter(
                        name="host",
                        type=ToolInputType.STRING,
                        description="Remote hostname to disconnect from",
                        required=True,
                    ),
                    ToolParameter(
                        name="username",
                        type=ToolInputType.STRING,
                        description="SSH username",
                        required=True,
                    ),
                    ToolParameter(
                        name="port",
                        type=ToolInputType.INTEGER,
                        description="SSH port (default: 22)",
                        required=False,
                    ),
                ],
            ),
        ]

    async def ssh_connect(
        self,
        host: str,
        username: str,
        port: int = 22,
        password: Optional[str] = None,
        private_key_path: Optional[str] = None,
        private_key_passphrase: Optional[str] = None,
    ) -> ToolResult:
        """Connect to SSH server.

        Args:
            host: Remote hostname
            username: SSH username
            port: SSH port
            password: Password for authentication
            private_key_path: Path to private key
            private_key_passphrase: Passphrase for private key

        Returns:
            ToolResult with connection status
        """
        try:
            client = await self._manager.get_connection(
                host=host,
                username=username,
                port=port,
                password=password,
                private_key_path=private_key_path,
                private_key_passphrase=private_key_passphrase,
            )

            return ToolResult(
                success=True,
                content={
                    "host": host,
                    "username": username,
                    "port": port,
                    "connected": client.is_connected,
                    "message": f"Connected to {username}@{host}:{port}",
                },
            )

        except ImportError as e:
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )
        except (ValueError, ConnectionError) as e:
            logger.warning(f"SSH connection failed: {host} - {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )
        except Exception as e:
            logger.error(f"SSH connection error: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Connection error: {e}",
            )

    async def ssh_execute(
        self,
        host: str,
        username: str,
        command: str,
        port: int = 22,
        timeout: Optional[int] = None,
    ) -> ToolResult:
        """Execute command on remote host.

        Args:
            host: Remote hostname
            username: SSH username
            command: Command to execute
            port: SSH port
            timeout: Command timeout

        Returns:
            ToolResult with command output
        """
        try:
            # Get existing connection
            key = f"{username}@{host}:{port}"
            client = self._manager._connections.get(key)

            if not client or not client.is_connected:
                return ToolResult(
                    success=False,
                    content=None,
                    error=f"Not connected to {key}. Use ssh_connect first.",
                )

            result = await client.execute(command, timeout=timeout)

            return ToolResult(
                success=result.exit_code == 0,
                content={
                    "host": host,
                    "command": command,
                    "exit_code": result.exit_code,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "execution_time": round(result.execution_time, 3),
                },
                error=result.stderr if result.exit_code != 0 else None,
            )

        except Exception as e:
            logger.error(f"SSH execute error: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Execute error: {e}",
            )

    async def ssh_upload(
        self,
        host: str,
        username: str,
        local_path: str,
        remote_path: str,
        port: int = 22,
    ) -> ToolResult:
        """Upload file to remote host.

        Args:
            host: Remote hostname
            username: SSH username
            local_path: Local file path
            remote_path: Remote destination path
            port: SSH port

        Returns:
            ToolResult with upload status
        """
        try:
            key = f"{username}@{host}:{port}"
            client = self._manager._connections.get(key)

            if not client or not client.is_connected:
                return ToolResult(
                    success=False,
                    content=None,
                    error=f"Not connected to {key}. Use ssh_connect first.",
                )

            await client.upload_file(local_path, remote_path)

            return ToolResult(
                success=True,
                content={
                    "host": host,
                    "local_path": local_path,
                    "remote_path": remote_path,
                    "message": f"Uploaded {local_path} to {remote_path}",
                },
            )

        except FileNotFoundError as e:
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )
        except Exception as e:
            logger.error(f"SSH upload error: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Upload error: {e}",
            )

    async def ssh_download(
        self,
        host: str,
        username: str,
        remote_path: str,
        local_path: str,
        port: int = 22,
    ) -> ToolResult:
        """Download file from remote host.

        Args:
            host: Remote hostname
            username: SSH username
            remote_path: Remote file path
            local_path: Local destination path
            port: SSH port

        Returns:
            ToolResult with download status
        """
        try:
            key = f"{username}@{host}:{port}"
            client = self._manager._connections.get(key)

            if not client or not client.is_connected:
                return ToolResult(
                    success=False,
                    content=None,
                    error=f"Not connected to {key}. Use ssh_connect first.",
                )

            await client.download_file(remote_path, local_path)

            return ToolResult(
                success=True,
                content={
                    "host": host,
                    "remote_path": remote_path,
                    "local_path": local_path,
                    "message": f"Downloaded {remote_path} to {local_path}",
                },
            )

        except Exception as e:
            logger.error(f"SSH download error: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Download error: {e}",
            )

    async def ssh_list_directory(
        self,
        host: str,
        username: str,
        remote_path: str,
        port: int = 22,
    ) -> ToolResult:
        """List remote directory.

        Args:
            host: Remote hostname
            username: SSH username
            remote_path: Remote directory path
            port: SSH port

        Returns:
            ToolResult with directory listing
        """
        try:
            key = f"{username}@{host}:{port}"
            client = self._manager._connections.get(key)

            if not client or not client.is_connected:
                return ToolResult(
                    success=False,
                    content=None,
                    error=f"Not connected to {key}. Use ssh_connect first.",
                )

            items = await client.list_directory(remote_path)

            return ToolResult(
                success=True,
                content={
                    "host": host,
                    "path": remote_path,
                    "count": len(items),
                    "items": items,
                },
            )

        except Exception as e:
            logger.error(f"SSH list directory error: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"List directory error: {e}",
            )

    async def ssh_disconnect(
        self,
        host: str,
        username: str,
        port: int = 22,
    ) -> ToolResult:
        """Disconnect from SSH server.

        Args:
            host: Remote hostname
            username: SSH username
            port: SSH port

        Returns:
            ToolResult with disconnection status
        """
        try:
            await self._manager.close_connection(host, username, port)

            return ToolResult(
                success=True,
                content={
                    "host": host,
                    "username": username,
                    "port": port,
                    "message": f"Disconnected from {username}@{host}:{port}",
                },
            )

        except Exception as e:
            logger.error(f"SSH disconnect error: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=f"Disconnect error: {e}",
            )
