"""
Redis Distributed Lock — Sprint 119

Provides distributed locking for multi-worker environments using Redis.

Features:
- Async context manager interface
- Configurable timeout and blocking timeout
- Lock renewal for long-running operations
- Automatic fallback to asyncio.Lock when Redis is unavailable
- Atomic acquire/release operations

Usage:
    lock = RedisDistributedLock(redis_client, "my_lock", timeout=30)
    async with lock.acquire():
        # Critical section protected across all workers
        pass
"""

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Protocol, runtime_checkable

import redis.asyncio as aioredis
from redis.exceptions import LockError, LockNotOwnedError

logger = logging.getLogger(__name__)


@runtime_checkable
class DistributedLock(Protocol):
    """Protocol for distributed lock implementations."""

    @property
    def lock_name(self) -> str:
        """Return the lock name."""
        ...

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[None, None]:
        """Acquire the lock as an async context manager."""
        ...

    async def is_locked(self) -> bool:
        """Check if the lock is currently held."""
        ...


class RedisDistributedLock:
    """
    Redis-based distributed lock using SET NX PX.

    Provides mutual exclusion across multiple workers/processes.
    Uses redis-py's built-in lock mechanism with Lua scripts for atomicity.

    Args:
        redis_client: Async Redis client.
        lock_name: Unique name for the lock.
        timeout: Lock auto-release timeout in seconds (prevents deadlocks).
        blocking_timeout: Max wait time when acquiring the lock.
        lock_prefix: Redis key prefix for lock keys.
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        lock_name: str,
        timeout: int = 30,
        blocking_timeout: int = 10,
        lock_prefix: str = "lock",
    ):
        self._redis = redis_client
        self._lock_name = lock_name
        self._timeout = timeout
        self._blocking_timeout = blocking_timeout
        self._lock_key = f"{lock_prefix}:{lock_name}"
        self._owner_id = str(uuid.uuid4())

    @property
    def lock_name(self) -> str:
        """Return the lock name."""
        return self._lock_name

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[None, None]:
        """
        Acquire the distributed lock.

        Raises:
            TimeoutError: If lock cannot be acquired within blocking_timeout.
            redis.RedisError: On Redis communication failure.
        """
        lock = self._redis.lock(
            self._lock_key,
            timeout=self._timeout,
            blocking_timeout=self._blocking_timeout,
        )

        acquired = await lock.acquire(blocking=True)
        if not acquired:
            raise TimeoutError(
                f"Failed to acquire distributed lock '{self._lock_name}' "
                f"within {self._blocking_timeout}s"
            )

        logger.debug(f"Acquired lock: {self._lock_name}")
        try:
            yield
        finally:
            try:
                await lock.release()
                logger.debug(f"Released lock: {self._lock_name}")
            except LockNotOwnedError:
                logger.warning(
                    f"Lock '{self._lock_name}' expired before release "
                    f"(timeout={self._timeout}s). Consider increasing timeout."
                )
            except aioredis.RedisError as e:
                logger.error(f"Error releasing lock '{self._lock_name}': {e}")

    async def is_locked(self) -> bool:
        """Check if the lock is currently held by any worker."""
        try:
            return bool(await self._redis.exists(self._lock_key))
        except aioredis.RedisError:
            return False

    async def extend(self, additional_time: int = 30) -> bool:
        """
        Extend the lock timeout for long-running operations.

        Args:
            additional_time: Additional seconds to add to the lock TTL.

        Returns:
            True if successfully extended.
        """
        lock = self._redis.lock(
            self._lock_key,
            timeout=self._timeout,
        )
        try:
            await lock.extend(additional_time)
            logger.debug(f"Extended lock '{self._lock_name}' by {additional_time}s")
            return True
        except (LockNotOwnedError, LockError) as e:
            logger.warning(f"Cannot extend lock '{self._lock_name}': {e}")
            return False


class InMemoryLock:
    """
    In-memory lock fallback using asyncio.Lock.

    Used when Redis is unavailable. Only provides mutual exclusion
    within a single process — NOT safe for multi-worker deployments.

    Args:
        lock_name: Name identifier for the lock.
        timeout: Acquire timeout in seconds (approximate).
    """

    def __init__(self, lock_name: str, timeout: int = 30):
        self._lock_name = lock_name
        self._timeout = timeout
        self._lock = asyncio.Lock()

    @property
    def lock_name(self) -> str:
        """Return the lock name."""
        return self._lock_name

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[None, None]:
        """Acquire the in-memory lock with timeout."""
        try:
            acquired = await asyncio.wait_for(
                self._lock.acquire(),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Failed to acquire in-memory lock '{self._lock_name}' "
                f"within {self._timeout}s"
            )

        logger.debug(f"Acquired in-memory lock: {self._lock_name}")
        try:
            yield
        finally:
            self._lock.release()
            logger.debug(f"Released in-memory lock: {self._lock_name}")

    async def is_locked(self) -> bool:
        """Check if the lock is currently held."""
        return self._lock.locked()


async def create_distributed_lock(
    lock_name: str,
    timeout: int = 30,
    blocking_timeout: int = 10,
) -> DistributedLock:
    """
    Factory function to create a distributed lock.

    Automatically selects Redis or InMemory based on availability.

    Args:
        lock_name: Unique name for the lock.
        timeout: Lock auto-release timeout in seconds.
        blocking_timeout: Max wait time for acquiring the lock.

    Returns:
        DistributedLock instance (Redis or InMemory fallback).
    """
    app_env = os.environ.get("APP_ENV", "development")

    try:
        from src.infrastructure.redis_client import get_redis_client

        client = await get_redis_client()
        if client is not None:
            logger.info(f"Lock[{lock_name}]: using Redis distributed lock")
            return RedisDistributedLock(
                redis_client=client,
                lock_name=lock_name,
                timeout=timeout,
                blocking_timeout=blocking_timeout,
            )
    except Exception as e:
        if app_env == "production":
            raise RuntimeError(
                f"Redis required for distributed lock '{lock_name}' in production: {e}"
            ) from e
        logger.warning(f"Redis unavailable for lock '{lock_name}': {e}")

    logger.warning(
        f"Lock[{lock_name}]: using in-memory lock (single-process only). "
        f"NOT safe for multi-worker deployment."
    )
    return InMemoryLock(lock_name=lock_name, timeout=timeout)
