"""
Storage Backend Factory — Sprint 110

Creates appropriate storage backend based on configuration.
Supports auto-detection from environment variables with graceful degradation.

Environment Variables:
    STORAGE_BACKEND: "redis" | "postgres" | "memory" | "auto" (default: "auto")
    APP_ENV: "development" | "staging" | "production" | "testing"
    REDIS_HOST: Redis server hostname
    DB_HOST: PostgreSQL server hostname

Auto-detection priority:
    1. If REDIS_HOST is set -> Redis
    2. If DB_HOST is set -> PostgreSQL
    3. Otherwise -> InMemory (with warning in non-testing environments)
"""

import logging
import os
from datetime import timedelta
from typing import Optional

from src.infrastructure.storage.backends.base import StorageBackendABC
from src.infrastructure.storage.backends.memory import InMemoryBackend

logger = logging.getLogger(__name__)


class StorageFactory:
    """
    Factory for creating storage backends.

    Usage:
        # Auto-detect from environment
        backend = await StorageFactory.create("dialog_sessions")

        # Explicit backend type
        backend = await StorageFactory.create(
            "approvals",
            backend_type="postgres",
            namespace="approvals",
        )

        # With TTL
        backend = await StorageFactory.create(
            "sessions",
            backend_type="redis",
            default_ttl=timedelta(hours=24),
        )
    """

    @staticmethod
    async def create(
        name: str,
        backend_type: str = "auto",
        default_ttl: Optional[timedelta] = None,
        namespace: Optional[str] = None,
        prefix: Optional[str] = None,
        **kwargs,
    ) -> StorageBackendABC:
        """
        Create a storage backend instance.

        Args:
            name: Storage name (used for logging and as default prefix/namespace).
            backend_type: "memory", "redis", "postgres", or "auto".
            default_ttl: Default TTL for all keys.
            namespace: PostgreSQL namespace (defaults to name).
            prefix: Redis/InMemory key prefix (defaults to "ipa:{name}").
            **kwargs: Additional backend-specific configuration.

        Returns:
            StorageBackendABC instance.

        Raises:
            RuntimeError: If required backend is unavailable in production.
            ValueError: If unknown backend_type is specified.
        """
        resolved_type = StorageFactory._resolve_backend_type(backend_type)
        app_env = os.environ.get("APP_ENV", "development")

        effective_prefix = prefix or f"ipa:{name}"
        effective_namespace = namespace or name

        if resolved_type == "memory":
            logger.info(f"StorageFactory[{name}]: using InMemoryBackend")
            return InMemoryBackend(
                prefix=effective_prefix, default_ttl=default_ttl
            )

        if resolved_type == "redis":
            backend = await StorageFactory._try_create_redis(
                name, effective_prefix, default_ttl
            )
            if backend is not None:
                return backend
            return StorageFactory._handle_fallback(
                name, app_env, "redis", effective_prefix, default_ttl
            )

        if resolved_type == "postgres":
            backend = await StorageFactory._try_create_postgres(
                name, effective_namespace, default_ttl, **kwargs
            )
            if backend is not None:
                return backend
            return StorageFactory._handle_fallback(
                name, app_env, "postgres", effective_prefix, default_ttl
            )

        raise ValueError(f"Unknown storage backend type: {backend_type}")

    @staticmethod
    def _resolve_backend_type(backend_type: str) -> str:
        """Resolve 'auto' to a concrete backend type based on environment."""
        if backend_type != "auto":
            return backend_type

        env_override = os.environ.get("STORAGE_BACKEND", "auto")
        if env_override != "auto":
            return env_override

        app_env = os.environ.get("APP_ENV", "development")
        if app_env == "testing":
            return "memory"

        # Auto-detect available backends
        redis_host = os.environ.get("REDIS_HOST", "")
        db_host = os.environ.get("DB_HOST", "")

        if redis_host:
            return "redis"
        if db_host:
            return "postgres"

        return "memory"

    @staticmethod
    async def _try_create_redis(
        name: str,
        prefix: str,
        default_ttl: Optional[timedelta],
    ) -> Optional[StorageBackendABC]:
        """Attempt to create a Redis backend."""
        try:
            from src.infrastructure.redis_client import get_redis_client
            from src.infrastructure.storage.backends.redis_backend import (
                RedisBackend,
            )

            client = await get_redis_client()
            if client is None:
                logger.warning(
                    f"StorageFactory[{name}]: Redis client unavailable"
                )
                return None

            logger.info(f"StorageFactory[{name}]: using RedisBackend")
            return RedisBackend(
                redis_client=client,
                prefix=prefix,
                default_ttl=default_ttl,
            )
        except ImportError as e:
            logger.warning(
                f"StorageFactory[{name}]: Redis package not available: {e}"
            )
            return None
        except Exception as e:
            logger.warning(
                f"StorageFactory[{name}]: failed to create Redis backend: {e}"
            )
            return None

    @staticmethod
    async def _try_create_postgres(
        name: str,
        namespace: str,
        default_ttl: Optional[timedelta],
        **kwargs,
    ) -> Optional[StorageBackendABC]:
        """Attempt to create a PostgreSQL backend."""
        try:
            from src.core.config import get_settings

            from src.infrastructure.storage.backends.postgres_backend import (
                PostgresBackend,
            )

            settings = get_settings()

            # Build DSN from settings
            # asyncpg needs postgresql:// (not postgresql+asyncpg://)
            dsn = (
                f"postgresql://{settings.db_user}:{settings.db_password}"
                f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
            )

            pool_min = kwargs.get("pool_min_size", 2)
            pool_max = kwargs.get("pool_max_size", 5)

            backend = PostgresBackend(
                dsn=dsn,
                namespace=namespace,
                default_ttl=default_ttl,
                pool_min_size=pool_min,
                pool_max_size=pool_max,
            )

            # Initialize pool and ensure table exists
            await backend._ensure_pool()

            logger.info(f"StorageFactory[{name}]: using PostgresBackend")
            return backend

        except ImportError as e:
            logger.warning(
                f"StorageFactory[{name}]: asyncpg not available: {e}"
            )
            return None
        except Exception as e:
            logger.warning(
                f"StorageFactory[{name}]: failed to create Postgres backend: {e}"
            )
            return None

    @staticmethod
    def _handle_fallback(
        name: str,
        app_env: str,
        requested_type: str,
        prefix: str,
        default_ttl: Optional[timedelta],
    ) -> InMemoryBackend:
        """
        Handle backend unavailability with environment-aware fallback.

        In production: raises RuntimeError (no silent degradation).
        In development/staging: falls back to InMemory with warning.
        """
        if app_env == "production":
            raise RuntimeError(
                f"StorageFactory[{name}]: {requested_type} backend unavailable "
                f"in production. Check service configuration."
            )

        logger.warning(
            f"StorageFactory[{name}]: {requested_type} unavailable in {app_env}, "
            f"falling back to InMemoryBackend. Data will be lost on restart."
        )
        return InMemoryBackend(prefix=prefix, default_ttl=default_ttl)
