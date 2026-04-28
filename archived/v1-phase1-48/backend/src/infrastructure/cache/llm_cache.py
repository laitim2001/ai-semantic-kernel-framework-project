# =============================================================================
# IPA Platform - LLM Cache Service
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Redis Cache Implementation
#
# LLM response caching service using Redis for performance optimization.
# Provides:
#   - LLMCacheService: Core caching service with SHA256 key generation
#   - CachedAgentService: Wrapper for AgentService with automatic caching
#
# Features:
#   - Configurable TTL (Time To Live)
#   - SHA256-based cache key generation
#   - Cache statistics and monitoring
#   - Bypass option for fresh responses
#
# Usage:
#   cache_service = LLMCacheService(redis_client)
#
#   # Cache a response
#   await cache_service.set(
#       model="gpt-4",
#       prompt="What is AI?",
#       response="AI is...",
#       ttl_seconds=3600,
#   )
#
#   # Get cached response
#   cached = await cache_service.get(model="gpt-4", prompt="What is AI?")
# =============================================================================

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class CacheEntry:
    """
    Cached LLM response entry.

    Attributes:
        response: The cached response content
        model: Model used for generation
        prompt_hash: SHA256 hash of the prompt
        created_at: When entry was created
        hit_count: Number of times this entry was retrieved
        metadata: Additional metadata
    """

    response: str
    model: str
    prompt_hash: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    hit_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "response": self.response,
            "model": self.model,
            "prompt_hash": self.prompt_hash,
            "created_at": self.created_at.isoformat(),
            "hit_count": self.hit_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        """Create from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.utcnow()

        return cls(
            response=data.get("response", ""),
            model=data.get("model", ""),
            prompt_hash=data.get("prompt_hash", ""),
            created_at=created_at,
            hit_count=data.get("hit_count", 0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CacheStats:
    """
    Cache statistics.

    Attributes:
        total_entries: Total cached entries
        total_hits: Total cache hits
        total_misses: Total cache misses
        hit_rate: Cache hit rate (0.0 - 1.0)
        memory_usage_bytes: Estimated memory usage
        last_reset: When stats were last reset
    """

    total_entries: int = 0
    total_hits: int = 0
    total_misses: int = 0
    hit_rate: float = 0.0
    memory_usage_bytes: int = 0
    last_reset: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_entries": self.total_entries,
            "total_hits": self.total_hits,
            "total_misses": self.total_misses,
            "hit_rate": round(self.hit_rate, 4),
            "memory_usage_bytes": self.memory_usage_bytes,
            "last_reset": self.last_reset.isoformat(),
        }


# =============================================================================
# LLM Cache Service
# =============================================================================


class LLMCacheService:
    """
    LLM response caching service using Redis.

    Provides efficient caching of LLM responses with:
    - SHA256-based cache key generation
    - Configurable TTL per entry
    - Hit/miss statistics
    - Memory usage tracking

    Example:
        cache = LLMCacheService(redis_client)

        # Check for cached response
        cached = await cache.get(model="gpt-4", prompt="Hello")
        if cached:
            return cached.response

        # Generate and cache new response
        response = await llm.generate(prompt)
        await cache.set(
            model="gpt-4",
            prompt="Hello",
            response=response,
        )
    """

    # Cache key prefix
    KEY_PREFIX = "llm_cache:"
    STATS_KEY = "llm_cache:stats"

    # Default settings
    DEFAULT_TTL_SECONDS = 3600  # 1 hour
    MAX_PROMPT_LENGTH = 10000  # Characters for key generation

    def __init__(
        self,
        redis_client: redis.Redis,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        enabled: bool = True,
    ):
        """
        Initialize LLM cache service.

        Args:
            redis_client: Redis async client
            ttl_seconds: Default TTL for cache entries
            enabled: Whether caching is enabled
        """
        self._redis = redis_client
        self._ttl_seconds = ttl_seconds
        self._enabled = enabled
        self._local_stats = CacheStats()

    @property
    def enabled(self) -> bool:
        """Check if caching is enabled."""
        return self._enabled

    def enable(self) -> None:
        """Enable caching."""
        self._enabled = True
        logger.info("LLM cache enabled")

    def disable(self) -> None:
        """Disable caching."""
        self._enabled = False
        logger.info("LLM cache disabled")

    def _generate_key(
        self,
        model: str,
        prompt: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate SHA256 cache key from model, prompt, and parameters.

        Args:
            model: Model identifier
            prompt: The prompt text
            parameters: Optional generation parameters

        Returns:
            SHA256 hash as cache key
        """
        # Truncate very long prompts
        prompt_text = prompt[:self.MAX_PROMPT_LENGTH] if prompt else ""

        # Build key components
        key_data = {
            "model": model,
            "prompt": prompt_text,
        }

        if parameters:
            # Include relevant parameters that affect output
            relevant_params = {
                k: v for k, v in parameters.items()
                if k in ("temperature", "max_tokens", "top_p", "frequency_penalty")
            }
            if relevant_params:
                key_data["params"] = relevant_params

        # Generate SHA256 hash
        key_string = json.dumps(key_data, sort_keys=True)
        hash_value = hashlib.sha256(key_string.encode()).hexdigest()

        return f"{self.KEY_PREFIX}{hash_value}"

    async def get(
        self,
        model: str,
        prompt: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Optional[CacheEntry]:
        """
        Get cached LLM response.

        Args:
            model: Model identifier
            prompt: The prompt text
            parameters: Optional generation parameters

        Returns:
            CacheEntry if found, None otherwise
        """
        if not self._enabled:
            return None

        try:
            key = self._generate_key(model, prompt, parameters)
            data = await self._redis.get(key)

            if data is None:
                self._local_stats.total_misses += 1
                await self._increment_stat("misses")
                return None

            # Parse cached entry
            entry_data = json.loads(data)
            entry = CacheEntry.from_dict(entry_data)

            # Update hit count
            entry.hit_count += 1
            self._local_stats.total_hits += 1
            await self._increment_stat("hits")

            # Update stored entry with new hit count
            entry_data["hit_count"] = entry.hit_count
            await self._redis.set(key, json.dumps(entry_data), keepttl=True)

            logger.debug(f"Cache hit for key: {key[:32]}...")
            return entry

        except Exception as e:
            logger.error(f"Error getting from cache: {e}")
            self._local_stats.total_misses += 1
            return None

    async def set(
        self,
        model: str,
        prompt: str,
        response: str,
        parameters: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Cache an LLM response.

        Args:
            model: Model identifier
            prompt: The prompt text
            response: The response to cache
            parameters: Optional generation parameters
            ttl_seconds: TTL override (uses default if not specified)
            metadata: Additional metadata to store

        Returns:
            True if cached successfully
        """
        if not self._enabled:
            return False

        try:
            key = self._generate_key(model, prompt, parameters)
            ttl = ttl_seconds if ttl_seconds is not None else self._ttl_seconds

            entry = CacheEntry(
                response=response,
                model=model,
                prompt_hash=key.replace(self.KEY_PREFIX, ""),
                hit_count=0,
                metadata=metadata or {},
            )

            await self._redis.set(
                key,
                json.dumps(entry.to_dict()),
                ex=ttl,
            )

            await self._increment_stat("entries")
            logger.debug(f"Cached response for key: {key[:32]}... (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Error setting cache: {e}")
            return False

    async def delete(
        self,
        model: str,
        prompt: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Delete a cached entry.

        Args:
            model: Model identifier
            prompt: The prompt text
            parameters: Optional generation parameters

        Returns:
            True if deleted
        """
        try:
            key = self._generate_key(model, prompt, parameters)
            result = await self._redis.delete(key)
            return result > 0

        except Exception as e:
            logger.error(f"Error deleting from cache: {e}")
            return False

    async def clear(self, pattern: Optional[str] = None) -> int:
        """
        Clear cache entries.

        Args:
            pattern: Optional pattern to match (e.g., "*gpt-4*")
                    If not specified, clears all LLM cache entries

        Returns:
            Number of entries cleared
        """
        try:
            search_pattern = f"{self.KEY_PREFIX}*"
            if pattern:
                search_pattern = f"{self.KEY_PREFIX}*{pattern}*"

            keys = []
            async for key in self._redis.scan_iter(match=search_pattern):
                keys.append(key)

            if keys:
                deleted = await self._redis.delete(*keys)
                logger.info(f"Cleared {deleted} cache entries")
                return deleted

            return 0

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return 0

    async def get_stats(self) -> CacheStats:
        """
        Get cache statistics.

        Returns:
            CacheStats with current statistics
        """
        try:
            # Get entry count
            entry_count = 0
            async for _ in self._redis.scan_iter(match=f"{self.KEY_PREFIX}*"):
                entry_count += 1

            # Get stored stats
            stats_data = await self._redis.hgetall(self.STATS_KEY)

            hits = int(stats_data.get(b"hits", 0))
            misses = int(stats_data.get(b"misses", 0))
            total = hits + misses

            hit_rate = hits / total if total > 0 else 0.0

            # Estimate memory usage (rough estimate)
            memory_info = await self._redis.memory_usage(self.STATS_KEY) or 0

            return CacheStats(
                total_entries=entry_count,
                total_hits=hits,
                total_misses=misses,
                hit_rate=hit_rate,
                memory_usage_bytes=memory_info,
                last_reset=self._local_stats.last_reset,
            )

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return self._local_stats

    async def reset_stats(self) -> None:
        """Reset cache statistics."""
        try:
            await self._redis.delete(self.STATS_KEY)
            self._local_stats = CacheStats()
            logger.info("Cache statistics reset")

        except Exception as e:
            logger.error(f"Error resetting stats: {e}")

    async def _increment_stat(self, stat_name: str, amount: int = 1) -> None:
        """Increment a statistic counter."""
        try:
            await self._redis.hincrby(self.STATS_KEY, stat_name, amount)
        except Exception as e:
            logger.error(f"Error incrementing stat {stat_name}: {e}")

    async def warm_cache(
        self,
        entries: List[Dict[str, Any]],
    ) -> int:
        """
        Pre-populate cache with entries.

        Args:
            entries: List of dicts with model, prompt, response

        Returns:
            Number of entries cached
        """
        cached = 0

        for entry in entries:
            success = await self.set(
                model=entry.get("model", ""),
                prompt=entry.get("prompt", ""),
                response=entry.get("response", ""),
                metadata=entry.get("metadata"),
            )
            if success:
                cached += 1

        logger.info(f"Warmed cache with {cached}/{len(entries)} entries")
        return cached


# =============================================================================
# Cached Agent Service
# =============================================================================


class CachedAgentService:
    """
    Wrapper around AgentService with automatic caching.

    Intercepts LLM calls and caches responses for repeated queries.
    Supports cache bypass for fresh responses.

    Example:
        agent_service = AgentService(...)
        cached_service = CachedAgentService(agent_service, cache)

        # Use cached service instead
        result = await cached_service.execute(
            agent_id=agent_id,
            prompt="What is AI?",
        )
    """

    def __init__(
        self,
        agent_service: Any,  # AgentService type
        cache_service: LLMCacheService,
    ):
        """
        Initialize cached agent service.

        Args:
            agent_service: Underlying AgentService
            cache_service: LLM cache service
        """
        self._agent_service = agent_service
        self._cache = cache_service

    async def execute(
        self,
        agent_id: str,
        prompt: str,
        bypass_cache: bool = False,
        **kwargs,
    ) -> Any:
        """
        Execute agent with caching.

        Args:
            agent_id: Agent identifier
            prompt: The prompt to send
            bypass_cache: Skip cache lookup if True
            **kwargs: Additional arguments for agent

        Returns:
            Agent execution result
        """
        # Get model from agent config (simplified - would need actual lookup)
        model = kwargs.get("model", "default")

        # Check cache unless bypassed
        if not bypass_cache and self._cache.enabled:
            cached = await self._cache.get(
                model=model,
                prompt=prompt,
                parameters=kwargs,
            )

            if cached:
                logger.info(f"Using cached response for agent {agent_id}")
                return {
                    "response": cached.response,
                    "cached": True,
                    "cache_hit_count": cached.hit_count,
                }

        # Execute agent
        result = await self._agent_service.execute(
            agent_id=agent_id,
            prompt=prompt,
            **kwargs,
        )

        # Cache response
        if self._cache.enabled and result.get("response"):
            await self._cache.set(
                model=model,
                prompt=prompt,
                response=result.get("response", ""),
                parameters=kwargs,
                metadata={
                    "agent_id": agent_id,
                    "execution_time": result.get("execution_time"),
                },
            )

        result["cached"] = False
        return result

    @property
    def cache(self) -> LLMCacheService:
        """Get underlying cache service."""
        return self._cache

    @property
    def agent_service(self) -> Any:
        """Get underlying agent service."""
        return self._agent_service
