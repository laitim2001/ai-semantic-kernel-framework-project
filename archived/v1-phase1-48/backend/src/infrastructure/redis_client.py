"""
Centralized Redis Client Factory — Sprint 119

Provides a single, shared async Redis connection pool for the entire application.
Replaces 5+ scattered get_redis() singletons with one centralized factory.

Usage:
    from src.infrastructure.redis_client import get_redis_client, close_redis_client

    # Get shared client (creates on first call)
    client = await get_redis_client()

    # Use in FastAPI lifespan
    @asynccontextmanager
    async def lifespan(app):
        yield
        await close_redis_client()
"""

import logging
from typing import Optional

import redis.asyncio as aioredis

from src.core.config import get_settings

logger = logging.getLogger(__name__)

# Module-level singleton
_redis_client: Optional[aioredis.Redis] = None
_redis_pool: Optional[aioredis.ConnectionPool] = None


async def get_redis_client() -> Optional[aioredis.Redis]:
    """
    Get the shared async Redis client.

    Creates a connection pool on first call. Returns None if Redis
    is not configured (REDIS_HOST not set).

    Returns:
        Async Redis client instance, or None if unavailable.
    """
    global _redis_client, _redis_pool

    if _redis_client is not None:
        return _redis_client

    settings = get_settings()

    if not settings.redis_host:
        logger.warning("Redis not configured: REDIS_HOST is empty")
        return None

    try:
        _redis_pool = aioredis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=20,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        _redis_client = aioredis.Redis(connection_pool=_redis_pool)

        # Verify connectivity
        await _redis_client.ping()
        logger.info(
            f"Redis connected: {settings.redis_host}:{settings.redis_port} "
            f"(pool max=20)"
        )
        return _redis_client

    except (aioredis.ConnectionError, aioredis.TimeoutError, OSError) as e:
        logger.error(f"Redis connection failed: {e}")
        _redis_client = None
        _redis_pool = None
        return None
    except Exception as e:
        logger.error(f"Unexpected Redis error: {e}", exc_info=True)
        _redis_client = None
        _redis_pool = None
        return None


async def close_redis_client() -> None:
    """
    Close the shared Redis client and connection pool.

    Call this during application shutdown.
    """
    global _redis_client, _redis_pool

    if _redis_client is not None:
        try:
            await _redis_client.aclose()
            logger.info("Redis client closed")
        except Exception as e:
            logger.warning(f"Error closing Redis client: {e}")
        finally:
            _redis_client = None

    if _redis_pool is not None:
        try:
            await _redis_pool.disconnect()
            logger.info("Redis connection pool disconnected")
        except Exception as e:
            logger.warning(f"Error disconnecting Redis pool: {e}")
        finally:
            _redis_pool = None


def is_redis_available() -> bool:
    """
    Check if Redis client is initialized and presumably connected.

    This does NOT ping Redis — use for quick synchronous checks only.
    """
    return _redis_client is not None


async def check_redis_health() -> dict:
    """
    Health check for Redis connection.

    Returns:
        Dict with status, latency, and info.
    """
    import time

    client = await get_redis_client()
    if client is None:
        return {"status": "unavailable", "error": "Redis client not initialized"}

    try:
        start = time.monotonic()
        await client.ping()
        latency_ms = (time.monotonic() - start) * 1000

        info = await client.info(section="memory")
        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "used_memory_human": info.get("used_memory_human", "unknown"),
            "connected_clients": info.get("connected_clients", "unknown"),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def reset_redis_client() -> None:
    """
    Reset the module-level singleton (for testing only).

    This does NOT close connections — call close_redis_client() first.
    """
    global _redis_client, _redis_pool
    _redis_client = None
    _redis_pool = None
