"""Server configuration with environment-aware defaults.

Provides environment-aware server configuration for development, staging,
and production environments. Supports Gunicorn multi-worker deployment
and Uvicorn single-worker development mode.

Sprint 117 — Multi-Worker Uvicorn Configuration
"""

import multiprocessing
import os
from enum import Enum
from typing import Optional


class ServerEnvironment(str, Enum):
    """Server deployment environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class ServerConfig:
    """Environment-aware server configuration.

    Reads configuration from environment variables with sensible defaults
    for each environment. Supports Gunicorn multi-worker deployment in
    staging/production and Uvicorn single-worker with hot-reload in development.

    Environment Variables:
        SERVER_ENV: deployment environment (development|staging|production)
        UVICORN_WORKERS: override worker count (staging/production only)
        SERVER_HOST: bind address (default: 0.0.0.0)
        SERVER_PORT: bind port (default: 8000)
        LOG_LEVEL: log verbosity (default: debug in dev, info otherwise)

    Example:
        >>> config = ServerConfig()
        >>> config.workers  # 1 in development
        >>> config = ServerConfig(env="production")
        >>> config.workers  # min(cpu_count * 2 + 1, 8) in production
    """

    def __init__(self, env: Optional[str] = None) -> None:
        raw_env = env or os.environ.get("SERVER_ENV", "development")
        try:
            self.environment = ServerEnvironment(raw_env.lower())
        except ValueError:
            self.environment = ServerEnvironment.DEVELOPMENT

    @property
    def workers(self) -> int:
        """Number of worker processes.

        Development: always 1 (for hot-reload compatibility).
        Staging/Production: CPU * 2 + 1, capped at 8.
        Can be overridden via UVICORN_WORKERS environment variable.
        """
        if self.environment == ServerEnvironment.DEVELOPMENT:
            return 1

        env_workers = os.environ.get("UVICORN_WORKERS")
        if env_workers is not None:
            try:
                val = int(env_workers)
                return max(1, min(val, 32))
            except (ValueError, TypeError):
                pass

        cpu_count = multiprocessing.cpu_count()
        return min(cpu_count * 2 + 1, 8)

    @property
    def reload(self) -> bool:
        """Enable hot-reload (development only)."""
        return self.environment == ServerEnvironment.DEVELOPMENT

    @property
    def host(self) -> str:
        """Server bind address."""
        return os.environ.get("SERVER_HOST", "0.0.0.0")

    @property
    def port(self) -> int:
        """Server bind port."""
        raw = os.environ.get("SERVER_PORT")
        if raw is not None:
            try:
                return int(raw)
            except (ValueError, TypeError):
                pass
        return 8000

    @property
    def log_level(self) -> str:
        """Logging verbosity level."""
        if self.environment == ServerEnvironment.DEVELOPMENT:
            return os.environ.get("LOG_LEVEL", "debug").lower()
        return os.environ.get("LOG_LEVEL", "info").lower()

    @property
    def access_log(self) -> bool:
        """Enable access logging (disabled in production for performance)."""
        return self.environment != ServerEnvironment.PRODUCTION

    @property
    def worker_class(self) -> str:
        """Gunicorn worker class."""
        return "uvicorn.workers.UvicornWorker"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == ServerEnvironment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == ServerEnvironment.PRODUCTION

    @property
    def bind(self) -> str:
        """Gunicorn bind string (host:port)."""
        return f"{self.host}:{self.port}"

    def to_dict(self) -> dict:
        """Export configuration as dictionary."""
        return {
            "environment": self.environment.value,
            "workers": self.workers,
            "reload": self.reload,
            "host": self.host,
            "port": self.port,
            "log_level": self.log_level,
            "access_log": self.access_log,
            "worker_class": self.worker_class,
            "bind": self.bind,
        }

    def __repr__(self) -> str:
        return (
            f"ServerConfig(env={self.environment.value}, "
            f"workers={self.workers}, reload={self.reload}, "
            f"bind={self.bind})"
        )
