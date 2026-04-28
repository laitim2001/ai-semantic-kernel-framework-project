"""
Storage Backend Factory — Sprint 119

Environment-aware factory for creating storage backends.
Supports automatic Redis detection with InMemory fallback.

Environment Variables:
    STORAGE_BACKEND: "redis" | "memory" | "auto" (default: "auto")
    APP_ENV: "development" | "staging" | "production"

Behavior:
    - auto + production: Redis required, raises if unavailable
    - auto + development: Redis preferred, InMemory fallback with WARNING
    - auto + testing: InMemory directly
    - redis: Redis required in all environments
    - memory: InMemory in all environments
"""

import logging
import os
from typing import Optional

from src.infrastructure.storage.memory_backend import InMemoryStorageBackend
from src.infrastructure.storage.protocol import StorageBackend

logger = logging.getLogger(__name__)


async def create_storage_backend(
    prefix: str,
    backend: Optional[str] = None,
    default_ttl: Optional[int] = None,
) -> StorageBackend:
    """
    Create a storage backend instance.

    Args:
        prefix: Key prefix for namespace isolation (e.g., "approval", "session").
        backend: Backend type override ("redis", "memory", or None for auto).
        default_ttl: Default TTL in seconds.

    Returns:
        StorageBackend instance (Redis or InMemory).

    Raises:
        RuntimeError: If Redis is required but unavailable.
    """
    backend_type = backend or os.environ.get("STORAGE_BACKEND", "auto")
    app_env = os.environ.get("APP_ENV", "development")

    # Explicit memory request
    if backend_type == "memory":
        logger.info(f"Storage[{prefix}]: using InMemory (explicit)")
        return InMemoryStorageBackend(prefix=prefix, default_ttl=default_ttl)

    # Explicit or auto Redis
    if backend_type in ("redis", "auto"):
        redis_backend = await _try_create_redis_backend(prefix, default_ttl)

        if redis_backend is not None:
            logger.info(f"Storage[{prefix}]: using Redis")
            return redis_backend

        # Redis unavailable — handle by environment
        if backend_type == "redis" or app_env == "production":
            raise RuntimeError(
                f"Redis unavailable for storage '{prefix}' in {app_env}. "
                f"Set REDIS_HOST or use STORAGE_BACKEND=memory."
            )

        if app_env == "testing":
            return InMemoryStorageBackend(prefix=prefix, default_ttl=default_ttl)

        # development/staging: fallback with warning
        logger.warning(
            f"Storage[{prefix}]: Redis unavailable in {app_env}, "
            f"falling back to InMemory. Data will be lost on restart."
        )
        return InMemoryStorageBackend(prefix=prefix, default_ttl=default_ttl)

    raise ValueError(f"Unknown storage backend: {backend_type}")


async def _try_create_redis_backend(
    prefix: str,
    default_ttl: Optional[int],
) -> Optional["RedisStorageBackend"]:
    """Attempt to create a Redis storage backend."""
    try:
        from src.infrastructure.redis_client import get_redis_client
        from src.infrastructure.storage.redis_backend import RedisStorageBackend

        client = await get_redis_client()
        if client is None:
            return None

        return RedisStorageBackend(
            redis_client=client,
            prefix=prefix,
            default_ttl=default_ttl,
        )
    except ImportError as e:
        logger.warning(f"Redis package not available: {e}")
        return None
    except Exception as e:
        logger.warning(f"Failed to create Redis backend for '{prefix}': {e}")
        return None
