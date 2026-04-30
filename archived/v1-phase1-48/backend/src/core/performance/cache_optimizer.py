"""
IPA Platform - Cache Optimization Module

Provides cache optimization utilities including:
- Multi-tier caching (memory + Redis)
- Cache warming strategies
- Intelligent TTL management
- Cache invalidation patterns

Author: IPA Platform Team
Version: 1.0.0
"""

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TypeVar, Generic
from functools import wraps

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


# =============================================================================
# Cache Entry
# =============================================================================

@dataclass
class CacheEntry(Generic[T]):
    """Represents a cached item with metadata."""

    value: T
    created_at: float
    ttl: int  # seconds
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return time.time() > (self.created_at + self.ttl)

    @property
    def age(self) -> float:
        """Get age of entry in seconds."""
        return time.time() - self.created_at


# =============================================================================
# Memory Cache (L1)
# =============================================================================

class MemoryCache:
    """
    In-memory LRU cache for fast access.

    Used as L1 cache before Redis (L2).
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 60):
        """
        Initialize memory cache.

        Args:
            max_size: Maximum number of entries
            default_ttl: Default TTL in seconds
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        entry = self._cache.get(key)

        if entry is None:
            self._misses += 1
            return None

        if entry.is_expired:
            del self._cache[key]
            self._misses += 1
            return None

        entry.access_count += 1
        entry.last_accessed = time.time()
        self._hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        # Evict if at capacity
        if len(self._cache) >= self._max_size:
            self._evict_lru()

        self._cache[key] = CacheEntry(
            value=value,
            created_at=time.time(),
            ttl=ttl or self._default_ttl,
        )

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all entries."""
        self._cache.clear()

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return

        # Find LRU entry
        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_accessed
        )
        del self._cache[lru_key]

    @property
    def hit_rate(self) -> float:
        """Get cache hit rate."""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    @property
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate,
        }


# =============================================================================
# Cache Optimizer
# =============================================================================

class CacheOptimizer:
    """
    Intelligent caching system with multi-tier support.

    Features:
    - L1 (memory) + L2 (Redis) caching
    - Automatic cache warming
    - TTL optimization based on access patterns
    - Cache-aside pattern implementation
    """

    def __init__(
        self,
        redis_client: Optional[Any] = None,
        memory_cache_size: int = 1000,
        default_ttl: int = 300,
    ):
        """
        Initialize cache optimizer.

        Args:
            redis_client: Redis client instance
            memory_cache_size: Size of L1 memory cache
            default_ttl: Default TTL in seconds
        """
        self._redis = redis_client
        self._memory = MemoryCache(max_size=memory_cache_size, default_ttl=default_ttl)
        self._default_ttl = default_ttl
        self._warm_keys: List[str] = []

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value using cache-aside pattern.

        Checks L1 (memory) first, then L2 (Redis).
        """
        # Try L1 first
        value = self._memory.get(key)
        if value is not None:
            return value

        # Try L2 (Redis)
        if self._redis:
            try:
                redis_value = await self._redis.get(key)
                if redis_value:
                    value = json.loads(redis_value)
                    # Populate L1
                    self._memory.set(key, value)
                    return value
            except Exception as e:
                logger.warning("redis_get_error", key=key, error=str(e))

        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        cache_level: str = "both",
    ) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds
            cache_level: "memory", "redis", or "both"
        """
        effective_ttl = ttl or self._default_ttl

        # Set in L1
        if cache_level in ("memory", "both"):
            self._memory.set(key, value, effective_ttl)

        # Set in L2
        if cache_level in ("redis", "both") and self._redis:
            try:
                await self._redis.setex(
                    key,
                    effective_ttl,
                    json.dumps(value, default=str),
                )
            except Exception as e:
                logger.warning("redis_set_error", key=key, error=str(e))

    async def delete(self, key: str) -> None:
        """Delete key from all cache levels."""
        self._memory.delete(key)

        if self._redis:
            try:
                await self._redis.delete(key)
            except Exception as e:
                logger.warning("redis_delete_error", key=key, error=str(e))

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching pattern.

        Args:
            pattern: Redis key pattern (e.g., "workflow:*")

        Returns:
            Number of keys invalidated
        """
        count = 0

        # Clear matching keys from memory cache
        keys_to_delete = [
            k for k in list(self._memory._cache.keys())
            if self._match_pattern(k, pattern)
        ]
        for key in keys_to_delete:
            self._memory.delete(key)
            count += 1

        # Clear from Redis
        if self._redis:
            try:
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(
                        cursor, match=pattern, count=100
                    )
                    if keys:
                        await self._redis.delete(*keys)
                        count += len(keys)
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning("redis_invalidate_error", pattern=pattern, error=str(e))

        return count

    def _match_pattern(self, key: str, pattern: str) -> bool:
        """Simple pattern matching for memory cache."""
        import fnmatch
        return fnmatch.fnmatch(key, pattern)

    async def warm(self, warm_functions: Dict[str, Callable]) -> None:
        """
        Warm cache with pre-loaded data.

        Args:
            warm_functions: Dict of cache_key -> async function to get data
        """
        logger.info("cache_warming_start", keys=list(warm_functions.keys()))

        for key, func in warm_functions.items():
            try:
                value = await func()
                await self.set(key, value)
                self._warm_keys.append(key)
                logger.debug("cache_warmed", key=key)
            except Exception as e:
                logger.warning("cache_warm_error", key=key, error=str(e))

        logger.info("cache_warming_complete", warmed_keys=len(self._warm_keys))

    def cached(
        self,
        key_prefix: str,
        ttl: Optional[int] = None,
        key_builder: Optional[Callable[..., str]] = None,
    ) -> Callable:
        """
        Decorator for caching function results.

        Args:
            key_prefix: Prefix for cache key
            ttl: TTL in seconds
            key_builder: Function to build cache key from args

        Usage:
            @cache_optimizer.cached("user", ttl=300)
            async def get_user(user_id: str):
                return await db.get_user(user_id)
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs) -> Any:
                # Build cache key
                if key_builder:
                    cache_key = f"{key_prefix}:{key_builder(*args, **kwargs)}"
                else:
                    # Default key building
                    key_parts = [str(a) for a in args]
                    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                    key_hash = hashlib.md5(":".join(key_parts).encode()).hexdigest()[:8]
                    cache_key = f"{key_prefix}:{key_hash}"

                # Try cache
                cached_value = await self.get(cache_key)
                if cached_value is not None:
                    return cached_value

                # Call function
                result = await func(*args, **kwargs)

                # Cache result
                await self.set(cache_key, result, ttl)

                return result

            return wrapper
        return decorator

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "memory": self._memory.stats,
            "warm_keys": len(self._warm_keys),
        }


# =============================================================================
# Cache Keys
# =============================================================================

class CacheKeys:
    """Standard cache key patterns for the application."""

    # Dashboard
    DASHBOARD_STATS = "dashboard:stats"
    DASHBOARD_CHART = "dashboard:chart:{period}"

    # Workflows
    WORKFLOW_LIST = "workflows:list:{page}:{limit}"
    WORKFLOW_DETAIL = "workflow:{id}"
    WORKFLOW_EXECUTIONS = "workflow:{id}:executions"

    # Agents
    AGENT_LIST = "agents:list:{page}:{limit}"
    AGENT_DETAIL = "agent:{id}"

    # Templates
    TEMPLATE_LIST = "templates:list:{category}"
    TEMPLATE_DETAIL = "template:{id}"

    # User
    USER_PROFILE = "user:{id}:profile"
    USER_PERMISSIONS = "user:{id}:permissions"

    @classmethod
    def format(cls, template: str, **kwargs) -> str:
        """Format a cache key template with parameters."""
        return template.format(**kwargs)
