"""SSH client with connection management.

Provides secure SSH operations with:
- Connection pooling
- Key-based and password authentication
- Remote command execution
- SFTP file transfer
- Timeout controls
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Optional paramiko import
try:
    import paramiko
    from paramiko import SSHClient as ParamikoClient
    from paramiko import AutoAddPolicy, RejectPolicy
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False
    paramiko = None
    ParamikoClient = None


@dataclass
class SSHConfig:
    """SSH configuration.

    Attributes:
        allowed_hosts: List of allowed hostnames/IPs (empty = all allowed)
        blocked_hosts: List of blocked hostnames/IPs
        default_timeout: Default connection timeout
        command_timeout: Default command execution timeout
        max_connections: Maximum connections per host
        auto_add_host_keys: Automatically add unknown host keys
        private_key_path: Path to default private key
        known_hosts_file: Path to known_hosts file
    """

    allowed_hosts: List[str] = field(default_factory=list)
    blocked_hosts: List[str] = field(default_factory=list)
    default_timeout: int = 30
    command_timeout: int = 60
    max_connections: int = 5
    auto_add_host_keys: bool = False
    private_key_path: Optional[str] = None
    known_hosts_file: Optional[str] = None

    @classmethod
    def from_env(cls) -> "SSHConfig":
        """Create config from environment variables.

        Environment variables:
            SSH_ALLOWED_HOSTS: Comma-separated list of allowed hosts
            SSH_BLOCKED_HOSTS: Comma-separated list of blocked hosts
            SSH_DEFAULT_TIMEOUT: Default connection timeout
            SSH_COMMAND_TIMEOUT: Default command timeout
            SSH_MAX_CONNECTIONS: Maximum connections per host
            SSH_AUTO_ADD_KEYS: Auto-add unknown host keys (true/false)
            SSH_PRIVATE_KEY_PATH: Path to default private key
            SSH_KNOWN_HOSTS_FILE: Path to known_hosts file
        """
        allowed_str = os.environ.get("SSH_ALLOWED_HOSTS", "")
        allowed = [h.strip() for h in allowed_str.split(",") if h.strip()]

        blocked_str = os.environ.get("SSH_BLOCKED_HOSTS", "")
        blocked = [h.strip() for h in blocked_str.split(",") if h.strip()]

        return cls(
            allowed_hosts=allowed,
            blocked_hosts=blocked,
            default_timeout=int(os.environ.get("SSH_DEFAULT_TIMEOUT", "30")),
            command_timeout=int(os.environ.get("SSH_COMMAND_TIMEOUT", "60")),
            max_connections=int(os.environ.get("SSH_MAX_CONNECTIONS", "5")),
            auto_add_host_keys=os.environ.get("SSH_AUTO_ADD_KEYS", "false").lower() == "true",
            private_key_path=os.environ.get("SSH_PRIVATE_KEY_PATH"),
            known_hosts_file=os.environ.get("SSH_KNOWN_HOSTS_FILE"),
        )


@dataclass
class SSHResult:
    """SSH command execution result.

    Attributes:
        exit_code: Command exit code
        stdout: Standard output
        stderr: Standard error
        execution_time: Execution time in seconds
    """

    exit_code: int
    stdout: str
    stderr: str
    execution_time: float


class SSHClient:
    """SSH client wrapper.

    Provides secure SSH operations with connection reuse.

    Example:
        >>> client = SSHClient(host="server.example.com", username="admin")
        >>> await client.connect(password="secret")
        >>> result = await client.execute("ls -la")
        >>> print(result.stdout)
    """

    def __init__(
        self,
        host: str,
        username: str,
        port: int = 22,
        config: Optional[SSHConfig] = None,
    ):
        """Initialize SSH client.

        Args:
            host: Remote hostname or IP
            username: SSH username
            port: SSH port (default: 22)
            config: SSH configuration
        """
        if not HAS_PARAMIKO:
            raise ImportError(
                "paramiko is required for SSH operations. "
                "Install with: pip install paramiko"
            )

        self._host = host
        self._username = username
        self._port = port
        self._config = config or SSHConfig()
        self._client: Optional[ParamikoClient] = None
        self._sftp: Optional[Any] = None
        self._connected = False

        # Validate host
        self._validate_host(host)

    def _validate_host(self, host: str) -> None:
        """Validate host against allowed/blocked lists.

        Args:
            host: Hostname to validate

        Raises:
            ValueError: If host is blocked or not allowed
        """
        # Check blocked hosts
        if self._config.blocked_hosts:
            if host in self._config.blocked_hosts:
                raise ValueError(f"Host '{host}' is blocked")

        # Check allowed hosts
        if self._config.allowed_hosts:
            if host not in self._config.allowed_hosts:
                raise ValueError(
                    f"Host '{host}' is not in allowed hosts list"
                )

    async def connect(
        self,
        password: Optional[str] = None,
        private_key_path: Optional[str] = None,
        private_key_passphrase: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> bool:
        """Connect to SSH server.

        Args:
            password: Password for authentication
            private_key_path: Path to private key file
            private_key_passphrase: Passphrase for private key
            timeout: Connection timeout

        Returns:
            True if connected successfully

        Raises:
            ValueError: If authentication method not provided
            ConnectionError: If connection fails
        """
        if self._connected:
            return True

        # Determine key path
        key_path = private_key_path or self._config.private_key_path

        if not password and not key_path:
            raise ValueError(
                "Either password or private_key_path must be provided"
            )

        effective_timeout = timeout or self._config.default_timeout

        try:
            self._client = ParamikoClient()

            # Set host key policy
            if self._config.auto_add_host_keys:
                self._client.set_missing_host_key_policy(AutoAddPolicy())
            else:
                self._client.set_missing_host_key_policy(RejectPolicy())

            # Load known hosts
            if self._config.known_hosts_file:
                self._client.load_host_keys(self._config.known_hosts_file)
            else:
                # Load system known hosts
                known_hosts = Path.home() / ".ssh" / "known_hosts"
                if known_hosts.exists():
                    self._client.load_host_keys(str(known_hosts))

            # Connect with appropriate authentication
            connect_kwargs = {
                "hostname": self._host,
                "port": self._port,
                "username": self._username,
                "timeout": effective_timeout,
            }

            if key_path:
                # Load private key
                key_path_resolved = Path(key_path).expanduser().resolve()
                if not key_path_resolved.exists():
                    raise FileNotFoundError(f"Private key not found: {key_path}")

                # Try different key types
                pkey = None
                for key_class in [
                    paramiko.RSAKey,
                    paramiko.Ed25519Key,
                    paramiko.ECDSAKey,
                    paramiko.DSSKey,
                ]:
                    try:
                        pkey = key_class.from_private_key_file(
                            str(key_path_resolved),
                            password=private_key_passphrase,
                        )
                        break
                    except Exception:
                        continue

                if pkey is None:
                    raise ValueError(f"Could not load private key: {key_path}")

                connect_kwargs["pkey"] = pkey

            if password:
                connect_kwargs["password"] = password

            # Run connect in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.connect(**connect_kwargs),
            )

            self._connected = True
            logger.info(f"Connected to {self._username}@{self._host}:{self._port}")
            return True

        except Exception as e:
            logger.error(f"SSH connection failed: {e}")
            self._connected = False
            raise ConnectionError(f"SSH connection failed: {e}")

    async def disconnect(self) -> None:
        """Disconnect from SSH server."""
        if self._sftp:
            try:
                self._sftp.close()
            except Exception:
                pass
            self._sftp = None

        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

        self._connected = False
        logger.info(f"Disconnected from {self._host}")

    async def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
    ) -> SSHResult:
        """Execute command on remote host.

        Args:
            command: Command to execute
            timeout: Command timeout

        Returns:
            SSHResult with command output

        Raises:
            ConnectionError: If not connected
        """
        if not self._connected or not self._client:
            raise ConnectionError("Not connected to SSH server")

        effective_timeout = timeout or self._config.command_timeout

        start_time = asyncio.get_event_loop().time()

        try:
            loop = asyncio.get_event_loop()

            # Execute command in thread pool
            def _exec():
                stdin, stdout, stderr = self._client.exec_command(
                    command,
                    timeout=effective_timeout,
                )
                return (
                    stdout.channel.recv_exit_status(),
                    stdout.read().decode("utf-8", errors="replace"),
                    stderr.read().decode("utf-8", errors="replace"),
                )

            exit_code, stdout, stderr = await loop.run_in_executor(None, _exec)

            execution_time = asyncio.get_event_loop().time() - start_time

            logger.info(
                f"Command executed on {self._host}: exit_code={exit_code}, "
                f"time={execution_time:.2f}s"
            )

            return SSHResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Command execution failed: {e}")
            return SSHResult(
                exit_code=-1,
                stdout="",
                stderr=str(e),
                execution_time=execution_time,
            )

    async def upload_file(
        self,
        local_path: str,
        remote_path: str,
    ) -> bool:
        """Upload file to remote host via SFTP.

        Args:
            local_path: Local file path
            remote_path: Remote file path

        Returns:
            True if uploaded successfully
        """
        if not self._connected or not self._client:
            raise ConnectionError("Not connected to SSH server")

        local_resolved = Path(local_path).resolve()
        if not local_resolved.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")

        try:
            if not self._sftp:
                loop = asyncio.get_event_loop()
                self._sftp = await loop.run_in_executor(
                    None, self._client.open_sftp
                )

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._sftp.put(str(local_resolved), remote_path),
            )

            logger.info(f"Uploaded {local_path} to {self._host}:{remote_path}")
            return True

        except Exception as e:
            logger.error(f"File upload failed: {e}")
            raise

    async def download_file(
        self,
        remote_path: str,
        local_path: str,
    ) -> bool:
        """Download file from remote host via SFTP.

        Args:
            remote_path: Remote file path
            local_path: Local file path

        Returns:
            True if downloaded successfully
        """
        if not self._connected or not self._client:
            raise ConnectionError("Not connected to SSH server")

        local_resolved = Path(local_path).resolve()
        local_resolved.parent.mkdir(parents=True, exist_ok=True)

        try:
            if not self._sftp:
                loop = asyncio.get_event_loop()
                self._sftp = await loop.run_in_executor(
                    None, self._client.open_sftp
                )

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._sftp.get(remote_path, str(local_resolved)),
            )

            logger.info(f"Downloaded {self._host}:{remote_path} to {local_path}")
            return True

        except Exception as e:
            logger.error(f"File download failed: {e}")
            raise

    async def list_directory(self, remote_path: str) -> List[Dict[str, Any]]:
        """List directory on remote host.

        Args:
            remote_path: Remote directory path

        Returns:
            List of file/directory info dictionaries
        """
        if not self._connected or not self._client:
            raise ConnectionError("Not connected to SSH server")

        try:
            if not self._sftp:
                loop = asyncio.get_event_loop()
                self._sftp = await loop.run_in_executor(
                    None, self._client.open_sftp
                )

            loop = asyncio.get_event_loop()
            attrs = await loop.run_in_executor(
                None,
                lambda: self._sftp.listdir_attr(remote_path),
            )

            results = []
            for attr in attrs:
                import stat
                is_dir = stat.S_ISDIR(attr.st_mode) if attr.st_mode else False
                results.append({
                    "name": attr.filename,
                    "size": attr.st_size,
                    "is_directory": is_dir,
                    "modified": attr.st_mtime,
                    "permissions": oct(attr.st_mode) if attr.st_mode else None,
                })

            return results

        except Exception as e:
            logger.error(f"Directory listing failed: {e}")
            raise

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    @property
    def host(self) -> str:
        """Get host."""
        return self._host

    async def __aenter__(self) -> "SSHClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()


class SSHConnectionManager:
    """SSH connection pool manager.

    Manages multiple SSH connections with reuse and cleanup.

    Example:
        >>> manager = SSHConnectionManager(config)
        >>> client = await manager.get_connection("server.example.com", "admin")
        >>> result = await client.execute("uptime")
    """

    def __init__(self, config: SSHConfig):
        """Initialize connection manager.

        Args:
            config: SSH configuration
        """
        self._config = config
        self._connections: Dict[str, SSHClient] = {}
        self._lock = asyncio.Lock()

    def _get_connection_key(self, host: str, username: str, port: int) -> str:
        """Generate connection pool key."""
        return f"{username}@{host}:{port}"

    async def get_connection(
        self,
        host: str,
        username: str,
        port: int = 22,
        password: Optional[str] = None,
        private_key_path: Optional[str] = None,
        private_key_passphrase: Optional[str] = None,
    ) -> SSHClient:
        """Get or create SSH connection.

        Args:
            host: Remote hostname
            username: SSH username
            port: SSH port
            password: Password for authentication
            private_key_path: Path to private key
            private_key_passphrase: Passphrase for private key

        Returns:
            Connected SSHClient
        """
        key = self._get_connection_key(host, username, port)

        async with self._lock:
            # Check for existing connection
            if key in self._connections:
                client = self._connections[key]
                if client.is_connected:
                    return client
                else:
                    # Remove stale connection
                    del self._connections[key]

            # Create new connection
            client = SSHClient(
                host=host,
                username=username,
                port=port,
                config=self._config,
            )

            await client.connect(
                password=password,
                private_key_path=private_key_path,
                private_key_passphrase=private_key_passphrase,
            )

            self._connections[key] = client
            return client

    async def close_connection(self, host: str, username: str, port: int = 22) -> None:
        """Close specific connection.

        Args:
            host: Remote hostname
            username: SSH username
            port: SSH port
        """
        key = self._get_connection_key(host, username, port)

        async with self._lock:
            if key in self._connections:
                await self._connections[key].disconnect()
                del self._connections[key]

    async def close_all(self) -> None:
        """Close all connections."""
        async with self._lock:
            for client in self._connections.values():
                await client.disconnect()
            self._connections.clear()

    @property
    def connection_count(self) -> int:
        """Get number of active connections."""
        return len(self._connections)
