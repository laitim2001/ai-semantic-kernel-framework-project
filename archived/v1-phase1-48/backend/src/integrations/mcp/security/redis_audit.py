"""Redis-backed audit storage for MCP operations.

Sprint 120 -- Story 120-1: Replace InMemoryAuditStorage with Redis.

Uses a Redis Sorted Set with timestamp as score for efficient
time-range queries and automatic trimming.

Key Format:
    - mcp:audit:events  (sorted set, score = Unix timestamp)

Each member is a JSON-serialised AuditEvent string.

Usage:
    from src.integrations.mcp.security.redis_audit import RedisAuditStorage

    storage = RedisAuditStorage(redis_client=redis)
    await storage.store(event)
    events = await storage.query(AuditFilter(user_id="user123"))
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, List, Optional

import redis.asyncio as aioredis

from .audit import AuditEvent, AuditFilter, AuditStorage

logger = logging.getLogger(__name__)


class RedisAuditStorage(AuditStorage):
    """Redis implementation of AuditStorage using Sorted Sets.

    Replaces InMemoryAuditStorage for production use.
    Events are stored as JSON strings in a Sorted Set keyed by timestamp.
    Automatic trimming keeps the set within a configurable max_size.

    Args:
        redis_client: Async Redis client instance.
        key: Redis key for the sorted set.
        max_size: Maximum number of events to retain (oldest trimmed first).
    """

    DEFAULT_KEY = "mcp:audit:events"
    DEFAULT_MAX_SIZE = 10000

    def __init__(
        self,
        redis_client: aioredis.Redis,
        key: str = DEFAULT_KEY,
        max_size: int = DEFAULT_MAX_SIZE,
    ) -> None:
        """Initialize Redis audit storage.

        Args:
            redis_client: Async Redis client instance.
            key: Redis key for the sorted set.
            max_size: Maximum number of events to retain.
        """
        self._redis = redis_client
        self._key = key
        self._max_size = max_size
        self._lock = asyncio.Lock()

    # -------------------------------------------------------------------------
    # AuditStorage ABC methods
    # -------------------------------------------------------------------------

    async def store(self, event: AuditEvent) -> bool:
        """Store an audit event in Redis.

        The event is serialised to JSON and added to the sorted set
        with its timestamp as score.  After insertion, the set is
        trimmed to max_size by removing the oldest entries.

        Args:
            event: AuditEvent to store.

        Returns:
            True if stored successfully, False on error.
        """
        try:
            data = json.dumps(
                event.to_dict(), default=str, ensure_ascii=False
            )
            score = event.timestamp.timestamp()

            async with self._lock:
                await self._redis.zadd(self._key, {data: score})

                # Trim to max_size (keep only the newest max_size entries)
                current_size = await self._redis.zcard(self._key)
                if current_size > self._max_size:
                    excess = current_size - self._max_size
                    await self._redis.zremrangebyrank(
                        self._key, 0, excess - 1
                    )

            logger.debug(
                f"Stored audit event {event.event_id} "
                f"(type={event.event_type.value})"
            )
            return True
        except aioredis.RedisError as e:
            logger.error(f"Redis error storing audit event: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error storing audit event: {e}")
            return False

    async def query(
        self,
        filter: Optional[AuditFilter] = None,
    ) -> List[AuditEvent]:
        """Query stored audit events.

        If a filter with start_time / end_time is provided, the sorted
        set is queried by score range first for efficiency.  Further
        field-level filtering is applied via AuditFilter.matches().

        Args:
            filter: Optional filter criteria.

        Returns:
            List of matching AuditEvent objects, sorted newest first.
        """
        try:
            # Determine score range from filter
            min_score = "-inf"
            max_score = "+inf"
            if filter is not None:
                if filter.start_time is not None:
                    min_score = filter.start_time.timestamp()
                if filter.end_time is not None:
                    max_score = filter.end_time.timestamp()

            # Fetch members within score range (oldest to newest)
            raw_members = await self._redis.zrangebyscore(
                self._key, min_score, max_score
            )

            events: List[AuditEvent] = []
            for member in raw_members:
                try:
                    data = json.loads(member)
                    event = AuditEvent.from_dict(data)
                    if filter is None or filter.matches(event):
                        events.append(event)
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.warning(f"Invalid audit event in Redis: {e}")

            # Sort newest first
            events.sort(key=lambda e: e.timestamp, reverse=True)

            # Apply pagination from filter
            if filter is not None:
                events = events[filter.offset: filter.offset + filter.limit]
            else:
                events = events[:100]

            return events
        except aioredis.RedisError as e:
            logger.error(f"Redis error querying audit events: {e}")
            return []

    async def delete_before(self, timestamp: datetime) -> int:
        """Delete events before a timestamp.

        Uses ZREMRANGEBYSCORE for efficient removal.

        Args:
            timestamp: Delete events with timestamp before this value.

        Returns:
            Number of events deleted.
        """
        try:
            score = timestamp.timestamp()
            async with self._lock:
                deleted = await self._redis.zremrangebyscore(
                    self._key, "-inf", f"({score}"
                )
            logger.info(
                f"Deleted {deleted} audit events before "
                f"{timestamp.isoformat()}"
            )
            return deleted
        except aioredis.RedisError as e:
            logger.error(f"Redis error deleting audit events: {e}")
            return 0

    # -------------------------------------------------------------------------
    # Extra utility methods
    # -------------------------------------------------------------------------

    async def count(self) -> int:
        """Return the total number of stored audit events.

        Returns:
            Count of events in the sorted set.
        """
        try:
            return await self._redis.zcard(self._key)
        except aioredis.RedisError as e:
            logger.error(f"Redis error counting audit events: {e}")
            return 0

    async def clear(self) -> None:
        """Clear all audit events from Redis.

        Intended for testing compatibility.
        """
        try:
            await self._redis.delete(self._key)
            logger.info("Cleared all MCP audit events from Redis")
        except aioredis.RedisError as e:
            logger.error(f"Redis error clearing audit events: {e}")


__all__ = [
    "RedisAuditStorage",
]
