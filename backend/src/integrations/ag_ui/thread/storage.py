# =============================================================================
# IPA Platform - AG-UI Thread Storage
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-3: Thread Manager
#
# Storage backends for AG-UI Thread persistence.
# Implements Redis cache and PostgreSQL repository for thread storage.
#
# Architecture:
#   - ThreadCache: Redis-based caching with TTL
#   - ThreadRepository: PostgreSQL persistence
#   - Write-Through pattern: Cache + DB simultaneous writes
#
# Dependencies:
#   - redis.asyncio (RedisCache)
#   - sqlalchemy (ThreadRepository)
# =============================================================================

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol

from .models import AGUIThread

logger = logging.getLogger(__name__)


# =============================================================================
# Cache Protocol and Implementations
# =============================================================================


class CacheProtocol(Protocol):
    """Protocol for cache implementations."""

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        ...

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL."""
        ...

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        ...

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        ...


class ThreadCache:
    """
    Redis-based cache for AG-UI Threads.

    Provides fast read access to thread data with configurable TTL.
    Uses Write-Through pattern with ThreadRepository.

    Attributes:
        cache: Redis cache client
        key_prefix: Prefix for all thread cache keys
        default_ttl: Default TTL in seconds (2 hours)
    """

    DEFAULT_TTL = 7200  # 2 hours

    def __init__(
        self,
        cache: CacheProtocol,
        key_prefix: str = "ag_ui:thread",
        default_ttl: int = DEFAULT_TTL,
    ):
        """
        Initialize ThreadCache.

        Args:
            cache: Redis cache client implementing CacheProtocol
            key_prefix: Prefix for cache keys
            default_ttl: Default TTL in seconds
        """
        self.cache = cache
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl

    def _make_key(self, thread_id: str) -> str:
        """Generate cache key for thread."""
        return f"{self.key_prefix}:{thread_id}"

    async def get(self, thread_id: str) -> Optional[AGUIThread]:
        """
        Get thread from cache.

        Args:
            thread_id: Thread ID to retrieve

        Returns:
            AGUIThread if found in cache, None otherwise
        """
        key = self._make_key(thread_id)
        try:
            data = await self.cache.get(key)
            if data:
                thread_dict = json.loads(data)
                return AGUIThread.from_dict(thread_dict)
            return None
        except Exception as e:
            logger.warning(f"Failed to get thread from cache: {e}")
            return None

    async def set(
        self,
        thread: AGUIThread,
        ttl: Optional[int] = None,
    ) -> None:
        """
        Store thread in cache.

        Args:
            thread: Thread to cache
            ttl: TTL in seconds, uses default if not specified
        """
        key = self._make_key(thread.thread_id)
        ttl = ttl or self.default_ttl
        try:
            data = json.dumps(thread.to_dict())
            await self.cache.set(key, data, ttl=ttl)
            logger.debug(f"Cached thread {thread.thread_id} with TTL {ttl}s")
        except Exception as e:
            logger.warning(f"Failed to cache thread: {e}")

    async def delete(self, thread_id: str) -> bool:
        """
        Delete thread from cache.

        Args:
            thread_id: Thread ID to delete

        Returns:
            True if deleted, False otherwise
        """
        key = self._make_key(thread_id)
        try:
            return await self.cache.delete(key)
        except Exception as e:
            logger.warning(f"Failed to delete thread from cache: {e}")
            return False

    async def exists(self, thread_id: str) -> bool:
        """
        Check if thread exists in cache.

        Args:
            thread_id: Thread ID to check

        Returns:
            True if exists, False otherwise
        """
        key = self._make_key(thread_id)
        try:
            return await self.cache.exists(key)
        except Exception as e:
            logger.warning(f"Failed to check thread existence: {e}")
            return False

    async def refresh_ttl(
        self,
        thread_id: str,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Refresh TTL for cached thread.

        Args:
            thread_id: Thread ID to refresh
            ttl: New TTL in seconds

        Returns:
            True if refreshed, False otherwise
        """
        thread = await self.get(thread_id)
        if thread:
            await self.set(thread, ttl=ttl)
            return True
        return False


# =============================================================================
# Repository Protocol and Implementations
# =============================================================================


class RepositoryProtocol(Protocol):
    """Protocol for repository implementations."""

    async def save(self, thread: AGUIThread) -> None:
        """Save thread to persistent storage."""
        ...

    async def get_by_id(self, thread_id: str) -> Optional[AGUIThread]:
        """Get thread by ID."""
        ...

    async def delete(self, thread_id: str) -> bool:
        """Delete thread from storage."""
        ...


class ThreadRepository(ABC):
    """
    Abstract base class for Thread persistence.

    Subclasses implement specific storage backends (PostgreSQL, etc.)
    """

    @abstractmethod
    async def save(self, thread: AGUIThread) -> None:
        """
        Save thread to persistent storage.

        Args:
            thread: Thread to persist
        """
        pass

    @abstractmethod
    async def get_by_id(self, thread_id: str) -> Optional[AGUIThread]:
        """
        Get thread by ID from persistent storage.

        Args:
            thread_id: Thread ID to retrieve

        Returns:
            AGUIThread if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete(self, thread_id: str) -> bool:
        """
        Delete thread from persistent storage.

        Args:
            thread_id: Thread ID to delete

        Returns:
            True if deleted, False otherwise
        """
        pass

    @abstractmethod
    async def list_by_status(
        self,
        status: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AGUIThread]:
        """
        List threads by status.

        Args:
            status: Thread status to filter by
            limit: Maximum number of threads to return
            offset: Number of threads to skip

        Returns:
            List of matching threads
        """
        pass


class InMemoryThreadRepository(ThreadRepository):
    """
    In-memory implementation of ThreadRepository.

    Useful for testing and development. Data is lost on restart.
    """

    def __init__(self):
        """Initialize in-memory storage."""
        self._storage: Dict[str, Dict[str, Any]] = {}

    async def save(self, thread: AGUIThread) -> None:
        """Save thread to in-memory storage."""
        self._storage[thread.thread_id] = thread.to_dict()
        logger.debug(f"Saved thread {thread.thread_id} to in-memory storage")

    async def get_by_id(self, thread_id: str) -> Optional[AGUIThread]:
        """Get thread from in-memory storage."""
        data = self._storage.get(thread_id)
        if data:
            return AGUIThread.from_dict(data)
        return None

    async def delete(self, thread_id: str) -> bool:
        """Delete thread from in-memory storage."""
        if thread_id in self._storage:
            del self._storage[thread_id]
            logger.debug(f"Deleted thread {thread_id} from in-memory storage")
            return True
        return False

    async def list_by_status(
        self,
        status: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AGUIThread]:
        """List threads by status from in-memory storage."""
        matching = [
            AGUIThread.from_dict(data)
            for data in self._storage.values()
            if data.get("status") == status
        ]
        return matching[offset : offset + limit]

    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AGUIThread]:
        """List all threads from in-memory storage."""
        threads = [AGUIThread.from_dict(data) for data in self._storage.values()]
        # Sort by updated_at descending
        threads.sort(key=lambda t: t.updated_at, reverse=True)
        return threads[offset : offset + limit]

    async def count(self) -> int:
        """Count total threads in storage."""
        return len(self._storage)

    async def clear(self) -> None:
        """Clear all threads from storage."""
        self._storage.clear()


class InMemoryCache:
    """
    In-memory implementation of CacheProtocol.

    Useful for testing. Does not support actual TTL expiration.
    """

    def __init__(self):
        """Initialize in-memory cache."""
        self._cache: Dict[str, str] = {}
        self._ttls: Dict[str, int] = {}

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        return self._cache.get(key)

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        self._cache[key] = value
        if ttl:
            self._ttls[key] = ttl

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if key in self._cache:
            del self._cache[key]
            self._ttls.pop(key, None)
            return True
        return False

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return key in self._cache

    async def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._ttls.clear()
