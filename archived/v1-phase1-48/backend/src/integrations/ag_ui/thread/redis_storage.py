"""
Redis Storage Implementations for AG-UI Thread — Sprint 119

Provides Redis-backed implementations for:
- RedisCacheBackend: Implements CacheProtocol for ThreadCache
- RedisThreadRepository: Implements ThreadRepository for persistent thread storage

These replace the InMemory implementations for production use.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis

from .models import AGUIThread
from .storage import CacheProtocol, ThreadRepository

logger = logging.getLogger(__name__)


class RedisCacheBackend:
    """
    Redis implementation of CacheProtocol.

    Replaces InMemoryCache for production use with ThreadCache.
    Provides actual TTL expiration and persistence across restarts.

    Args:
        redis_client: Async Redis client.
        key_prefix: Prefix for all cache keys.
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        key_prefix: str = "ag_ui:cache",
    ):
        self._redis = redis_client
        self._key_prefix = key_prefix

    def _make_key(self, key: str) -> str:
        """Build full Redis key."""
        return f"{self._key_prefix}:{key}"

    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis cache."""
        full_key = self._make_key(key)
        try:
            return await self._redis.get(full_key)
        except aioredis.RedisError as e:
            logger.error(f"Redis cache GET error for {full_key}: {e}")
            return None

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """Set value in Redis cache with optional TTL."""
        full_key = self._make_key(key)
        try:
            if ttl is not None:
                await self._redis.setex(full_key, ttl, value)
            else:
                await self._redis.set(full_key, value)
        except aioredis.RedisError as e:
            logger.error(f"Redis cache SET error for {full_key}: {e}")
            raise

    async def delete(self, key: str) -> bool:
        """Delete key from Redis cache."""
        full_key = self._make_key(key)
        try:
            result = await self._redis.delete(full_key)
            return result > 0
        except aioredis.RedisError as e:
            logger.error(f"Redis cache DELETE error for {full_key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache."""
        full_key = self._make_key(key)
        try:
            return bool(await self._redis.exists(full_key))
        except aioredis.RedisError as e:
            logger.error(f"Redis cache EXISTS error for {full_key}: {e}")
            return False

    async def clear(self) -> None:
        """Clear all cache entries with this prefix."""
        pattern = f"{self._key_prefix}:*"
        try:
            async for key in self._redis.scan_iter(match=pattern, count=100):
                await self._redis.delete(key)
            logger.info(f"Cleared AG-UI cache with prefix '{self._key_prefix}'")
        except aioredis.RedisError as e:
            logger.error(f"Redis cache CLEAR error: {e}")


class RedisThreadRepository(ThreadRepository):
    """
    Redis implementation of ThreadRepository.

    Replaces InMemoryThreadRepository for production use.
    Stores threads as JSON with status indexing via Redis sets.

    Key Formats:
        - ag_ui:thread:{thread_id} -> Thread JSON
        - ag_ui:thread_status:{status} -> Set of thread IDs

    Args:
        redis_client: Async Redis client.
        key_prefix: Prefix for all thread keys.
        default_ttl: TTL for thread data (None = no expiry).
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        key_prefix: str = "ag_ui:thread_repo",
        default_ttl: Optional[int] = 86400,  # 24 hours default
    ):
        self._redis = redis_client
        self._key_prefix = key_prefix
        self._default_ttl = default_ttl

    def _thread_key(self, thread_id: str) -> str:
        """Generate key for thread data."""
        return f"{self._key_prefix}:{thread_id}"

    def _status_set_key(self, status: str) -> str:
        """Generate key for status index set."""
        return f"{self._key_prefix}_status:{status}"

    def _all_threads_key(self) -> str:
        """Generate key for all threads set."""
        return f"{self._key_prefix}_all"

    async def save(self, thread: AGUIThread) -> None:
        """Save thread to Redis with status indexing."""
        thread_key = self._thread_key(thread.thread_id)
        data = json.dumps(thread.to_dict(), default=str)

        try:
            # Save thread data
            if self._default_ttl:
                await self._redis.setex(thread_key, self._default_ttl, data)
            else:
                await self._redis.set(thread_key, data)

            # Update status index
            status = thread.status if hasattr(thread, "status") else "unknown"
            status_key = self._status_set_key(status)
            await self._redis.sadd(status_key, thread.thread_id)
            await self._redis.sadd(self._all_threads_key(), thread.thread_id)

            logger.debug(f"Saved thread {thread.thread_id} to Redis (status={status})")
        except aioredis.RedisError as e:
            logger.error(f"Redis save error for thread {thread.thread_id}: {e}")
            raise

    async def get_by_id(self, thread_id: str) -> Optional[AGUIThread]:
        """Get thread from Redis by ID."""
        thread_key = self._thread_key(thread_id)
        try:
            data = await self._redis.get(thread_key)
            if data is None:
                return None
            thread_dict = json.loads(data)
            return AGUIThread.from_dict(thread_dict)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to deserialize thread {thread_id}: {e}")
            return None
        except aioredis.RedisError as e:
            logger.error(f"Redis get error for thread {thread_id}: {e}")
            return None

    async def delete(self, thread_id: str) -> bool:
        """Delete thread from Redis and all status indices."""
        thread_key = self._thread_key(thread_id)
        try:
            # Get thread to find its status for index cleanup
            thread = await self.get_by_id(thread_id)

            result = await self._redis.delete(thread_key)
            await self._redis.srem(self._all_threads_key(), thread_id)

            # Clean status index
            if thread and hasattr(thread, "status"):
                status_key = self._status_set_key(thread.status)
                await self._redis.srem(status_key, thread_id)

            return result > 0
        except aioredis.RedisError as e:
            logger.error(f"Redis delete error for thread {thread_id}: {e}")
            return False

    async def list_by_status(
        self,
        status: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AGUIThread]:
        """List threads by status using Redis set index."""
        status_key = self._status_set_key(status)
        try:
            thread_ids = await self._redis.smembers(status_key)
            thread_ids_list = sorted(thread_ids)  # Stable ordering

            # Apply pagination
            paginated = thread_ids_list[offset: offset + limit]

            threads = []
            for tid in paginated:
                thread = await self.get_by_id(tid)
                if thread is not None:
                    threads.append(thread)
                else:
                    # Clean stale index entry
                    await self._redis.srem(status_key, tid)

            return threads
        except aioredis.RedisError as e:
            logger.error(f"Redis list_by_status error for status={status}: {e}")
            return []

    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AGUIThread]:
        """List all threads from Redis."""
        try:
            all_ids = await self._redis.smembers(self._all_threads_key())
            all_ids_list = sorted(all_ids)
            paginated = all_ids_list[offset: offset + limit]

            threads = []
            for tid in paginated:
                thread = await self.get_by_id(tid)
                if thread is not None:
                    threads.append(thread)

            # Sort by updated_at descending
            threads.sort(
                key=lambda t: t.updated_at if hasattr(t, "updated_at") else "",
                reverse=True,
            )
            return threads
        except aioredis.RedisError as e:
            logger.error(f"Redis list_all error: {e}")
            return []

    async def count(self) -> int:
        """Count total threads in Redis."""
        try:
            return await self._redis.scard(self._all_threads_key())
        except aioredis.RedisError as e:
            logger.error(f"Redis count error: {e}")
            return 0

    async def clear(self) -> None:
        """Clear all threads from Redis."""
        try:
            all_ids = await self._redis.smembers(self._all_threads_key())
            for tid in all_ids:
                await self._redis.delete(self._thread_key(tid))

            # Clean all status sets
            pattern = f"{self._key_prefix}_status:*"
            async for key in self._redis.scan_iter(match=pattern, count=100):
                await self._redis.delete(key)

            await self._redis.delete(self._all_threads_key())
            logger.info("Cleared all AG-UI threads from Redis")
        except aioredis.RedisError as e:
            logger.error(f"Redis clear error: {e}")
