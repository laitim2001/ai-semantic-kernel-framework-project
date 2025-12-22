"""MCP Configuration Loader.

This module handles loading MCP server configurations from various sources:
    - YAML configuration files
    - Environment variables
    - Programmatic configuration

Example YAML configuration:
    servers:
      - name: azure-mcp
        command: python
        args: ["-m", "mcp_servers.azure"]
        env:
          AZURE_SUBSCRIPTION_ID: ${AZURE_SUBSCRIPTION_ID}
        enabled: true
        timeout: 30

      - name: github-mcp
        command: npx
        args: ["-y", "@modelcontextprotocol/server-github"]
        env:
          GITHUB_PERSONAL_ACCESS_TOKEN: ${GITHUB_TOKEN}
        enabled: true

Example:
    >>> loader = ConfigLoader()
    >>> servers = loader.load_from_file("config/mcp-servers.yaml")
    >>> for server in servers:
    ...     print(f"{server.name}: {server.command}")
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path
import logging
import os
import re

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from .server_registry import RegisteredServer

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Configuration loading or parsing error."""

    pass


@dataclass
class ServerDefinition:
    """Server definition from configuration.

    Attributes:
        name: Unique server identifier
        command: Command to execute
        args: Command arguments
        env: Environment variables
        transport: Transport type (stdio, sse, websocket)
        timeout: Default timeout in seconds
        enabled: Whether server should be auto-connected
        cwd: Working directory for the server process
        description: Human-readable description
        tags: Optional tags for categorization
    """

    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    transport: str = "stdio"
    timeout: float = 30.0
    enabled: bool = True
    cwd: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_registered_server(self) -> RegisteredServer:
        """Convert to RegisteredServer.

        Returns:
            RegisteredServer instance
        """
        return RegisteredServer(
            name=self.name,
            command=self.command,
            args=self.args,
            env=self.env,
            transport=self.transport,
            timeout=self.timeout,
            enabled=self.enabled,
            cwd=self.cwd,
        )


class ConfigLoader:
    """MCP Configuration Loader.

    Handles loading and parsing MCP server configurations from
    various sources including YAML files and environment variables.

    Attributes:
        env_prefix: Prefix for environment variable lookups

    Example:
        >>> loader = ConfigLoader(env_prefix="MCP_")
        >>> servers = loader.load_from_file("config/mcp-servers.yaml")
        >>> registry = ServerRegistry()
        >>> for server in servers:
        ...     await registry.register(server.to_registered_server())
    """

    # Pattern for environment variable substitution: ${VAR_NAME}
    ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")

    def __init__(self, env_prefix: str = "MCP_"):
        """Initialize configuration loader.

        Args:
            env_prefix: Prefix for environment variable lookups
        """
        self._env_prefix = env_prefix
        self._config_cache: Dict[str, List[ServerDefinition]] = {}

    def load_from_file(
        self,
        file_path: str,
        reload: bool = False,
    ) -> List[ServerDefinition]:
        """Load server configurations from a YAML file.

        Args:
            file_path: Path to YAML configuration file
            reload: Force reload even if cached

        Returns:
            List of ServerDefinition instances

        Raises:
            ConfigError: If file not found or parsing fails
        """
        if not YAML_AVAILABLE:
            raise ConfigError(
                "PyYAML is required for YAML configuration. "
                "Install with: pip install pyyaml"
            )

        path = Path(file_path)

        if not reload and str(path) in self._config_cache:
            return self._config_cache[str(path)]

        if not path.exists():
            raise ConfigError(f"Configuration file not found: {file_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if not config:
                logger.warning(f"Empty configuration file: {file_path}")
                return []

            servers = self._parse_config(config)
            self._config_cache[str(path)] = servers

            logger.info(
                f"Loaded {len(servers)} server configurations from {file_path}"
            )
            return servers

        except yaml.YAMLError as e:
            raise ConfigError(f"YAML parsing error in {file_path}: {e}") from e
        except Exception as e:
            raise ConfigError(
                f"Error loading configuration from {file_path}: {e}"
            ) from e

    def load_from_dict(
        self,
        config: Dict[str, Any],
    ) -> List[ServerDefinition]:
        """Load server configurations from a dictionary.

        Args:
            config: Configuration dictionary

        Returns:
            List of ServerDefinition instances
        """
        return self._parse_config(config)

    def load_from_env(self) -> List[ServerDefinition]:
        """Load server configurations from environment variables.

        Environment variable format:
            MCP_SERVER_1_NAME=my-server
            MCP_SERVER_1_COMMAND=python
            MCP_SERVER_1_ARGS=-m,mcp_servers.example
            MCP_SERVER_1_ENABLED=true

        Returns:
            List of ServerDefinition instances
        """
        servers = []
        server_configs: Dict[str, Dict[str, str]] = {}

        # Collect all MCP server environment variables
        prefix = f"{self._env_prefix}SERVER_"

        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue

            # Parse key: MCP_SERVER_1_NAME -> (1, NAME)
            parts = key[len(prefix) :].split("_", 1)
            if len(parts) != 2:
                continue

            server_id, field = parts
            if server_id not in server_configs:
                server_configs[server_id] = {}
            server_configs[server_id][field.lower()] = value

        # Convert to ServerDefinition
        for server_id, config in sorted(server_configs.items()):
            if "name" not in config or "command" not in config:
                logger.warning(
                    f"Skipping incomplete server config {server_id}: "
                    f"missing name or command"
                )
                continue

            try:
                args = []
                if "args" in config:
                    args = config["args"].split(",")

                env = {}
                if "env" in config:
                    for pair in config["env"].split(","):
                        if "=" in pair:
                            k, v = pair.split("=", 1)
                            env[k] = self._substitute_env_vars(v)

                enabled = config.get("enabled", "true").lower() == "true"
                timeout = float(config.get("timeout", "30"))

                servers.append(
                    ServerDefinition(
                        name=config["name"],
                        command=config["command"],
                        args=args,
                        env=env,
                        enabled=enabled,
                        timeout=timeout,
                    )
                )

            except Exception as e:
                logger.warning(
                    f"Error parsing server config {server_id}: {e}"
                )

        if servers:
            logger.info(
                f"Loaded {len(servers)} server configurations from environment"
            )

        return servers

    def _parse_config(
        self,
        config: Dict[str, Any],
    ) -> List[ServerDefinition]:
        """Parse configuration dictionary into server definitions.

        Args:
            config: Configuration dictionary

        Returns:
            List of ServerDefinition instances
        """
        servers = []
        server_list = config.get("servers", [])

        if not isinstance(server_list, list):
            raise ConfigError("'servers' must be a list")

        for idx, server_config in enumerate(server_list):
            try:
                server = self._parse_server_config(server_config)
                servers.append(server)
            except Exception as e:
                logger.warning(
                    f"Error parsing server config at index {idx}: {e}"
                )

        return servers

    def _parse_server_config(
        self,
        config: Dict[str, Any],
    ) -> ServerDefinition:
        """Parse a single server configuration.

        Args:
            config: Server configuration dictionary

        Returns:
            ServerDefinition instance
        """
        if "name" not in config:
            raise ConfigError("Server config missing 'name'")
        if "command" not in config:
            raise ConfigError("Server config missing 'command'")

        # Process environment variables in env dict
        env = {}
        raw_env = config.get("env", {})
        if isinstance(raw_env, dict):
            for key, value in raw_env.items():
                if isinstance(value, str):
                    env[key] = self._substitute_env_vars(value)
                else:
                    env[key] = str(value)

        # Process args
        args = config.get("args", [])
        if isinstance(args, str):
            args = args.split()

        return ServerDefinition(
            name=config["name"],
            command=config["command"],
            args=args,
            env=env,
            transport=config.get("transport", "stdio"),
            timeout=float(config.get("timeout", 30)),
            enabled=config.get("enabled", True),
            cwd=config.get("cwd"),
            description=config.get("description"),
            tags=config.get("tags", []),
        )

    def _substitute_env_vars(self, value: str) -> str:
        """Substitute environment variables in a string.

        Replaces ${VAR_NAME} with the value of VAR_NAME from environment.

        Args:
            value: String potentially containing ${VAR_NAME} patterns

        Returns:
            String with environment variables substituted
        """

        def replace(match):
            var_name = match.group(1)
            env_value = os.environ.get(var_name, "")
            if not env_value:
                logger.warning(
                    f"Environment variable not found: {var_name}"
                )
            return env_value

        return self.ENV_VAR_PATTERN.sub(replace, value)

    def validate_config(
        self,
        config: Dict[str, Any],
    ) -> List[str]:
        """Validate a configuration dictionary.

        Args:
            config: Configuration dictionary to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if "servers" not in config:
            errors.append("Missing 'servers' key in configuration")
            return errors

        servers = config.get("servers", [])
        if not isinstance(servers, list):
            errors.append("'servers' must be a list")
            return errors

        names_seen = set()

        for idx, server in enumerate(servers):
            prefix = f"servers[{idx}]"

            if not isinstance(server, dict):
                errors.append(f"{prefix}: must be a dictionary")
                continue

            if "name" not in server:
                errors.append(f"{prefix}: missing required field 'name'")
            else:
                name = server["name"]
                if name in names_seen:
                    errors.append(f"{prefix}: duplicate server name '{name}'")
                names_seen.add(name)

            if "command" not in server:
                errors.append(f"{prefix}: missing required field 'command'")

            transport = server.get("transport", "stdio")
            if transport not in ("stdio", "sse", "websocket"):
                errors.append(
                    f"{prefix}: invalid transport '{transport}', "
                    f"must be stdio, sse, or websocket"
                )

            timeout = server.get("timeout")
            if timeout is not None:
                try:
                    float(timeout)
                except (TypeError, ValueError):
                    errors.append(
                        f"{prefix}: timeout must be a number"
                    )

        return errors

    def clear_cache(self) -> None:
        """Clear the configuration cache."""
        self._config_cache.clear()
