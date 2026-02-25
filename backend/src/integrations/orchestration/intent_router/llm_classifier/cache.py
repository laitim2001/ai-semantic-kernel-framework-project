"""
Classification Cache Implementation

Redis-backed cache for LLM classification results.
Reduces repeated LLM calls for identical or similar queries.

Sprint 128: Story 128-1 — ClassificationCache
"""

import hashlib
import json
import logging
from dataclasses import asdict
from typing import Any, Dict, Optional

from ..models import (
    CompletenessInfo,
    ITIntentCategory,
    LLMClassificationResult,
)

logger = logging.getLogger(__name__)

# Default cache TTL: 30 minutes (shorter than general LLM cache)
DEFAULT_CACHE_TTL = 1800


class ClassificationCache:
    """
    Redis-backed cache for LLM classification results.

    Caches LLMClassificationResult objects by hashing the input parameters
    (user_input + include_completeness + simplified). Uses the same SHA256
    hash pattern as CachedLLMService for consistency.

    Attributes:
        cache: Redis client instance (sync or async)
        ttl: Cache TTL in seconds
        prefix: Cache key prefix
        hits: Total cache hits
        misses: Total cache misses

    Example:
        >>> cache = ClassificationCache(redis_client, ttl=1800)
        >>> result = await cache.get("ETL failed", True, False)
        >>> if result is None:
        ...     result = await classifier.classify("ETL failed")
        ...     await cache.set("ETL failed", True, False, result)
    """

    def __init__(
        self,
        cache: Optional[Any] = None,
        ttl: int = DEFAULT_CACHE_TTL,
        prefix: str = "classify",
    ):
        """
        Initialize ClassificationCache.

        Args:
            cache: Redis client instance (sync or async). None disables caching.
            ttl: Cache TTL in seconds, default 1800 (30 minutes)
            prefix: Cache key prefix, default "classify"
        """
        self.cache = cache
        self.ttl = ttl
        self.prefix = prefix
        self.hits = 0
        self.misses = 0

        logger.info(
            f"ClassificationCache initialized: "
            f"enabled={cache is not None}, ttl={ttl}s, prefix={prefix}"
        )

    @property
    def enabled(self) -> bool:
        """Check if caching is enabled."""
        return self.cache is not None

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def _make_key(
        self,
        user_input: str,
        include_completeness: bool,
        simplified: bool,
    ) -> str:
        """
        Generate cache key from input parameters.

        Uses SHA256 hash of concatenated parameters for consistent key generation.

        Args:
            user_input: The user's input text
            include_completeness: Whether completeness was included
            simplified: Whether simplified prompt was used

        Returns:
            Cache key string: "{prefix}:{hash[:16]}"
        """
        params_str = json.dumps(
            {
                "user_input": user_input,
                "include_completeness": include_completeness,
                "simplified": simplified,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        hash_value = hashlib.sha256(params_str.encode()).hexdigest()[:16]
        return f"{self.prefix}:{hash_value}"

    async def get(
        self,
        user_input: str,
        include_completeness: bool = True,
        simplified: bool = False,
    ) -> Optional[LLMClassificationResult]:
        """
        Get cached classification result.

        Args:
            user_input: The user's input text
            include_completeness: Whether completeness was included
            simplified: Whether simplified prompt was used

        Returns:
            Cached LLMClassificationResult, or None if not cached
        """
        if not self.enabled:
            self.misses += 1
            return None

        key = self._make_key(user_input, include_completeness, simplified)

        try:
            value = await self._cache_get(key)
            if value is None:
                self.misses += 1
                return None

            self.hits += 1
            logger.debug(f"Cache hit: {key}")
            return self._deserialize(value)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            self.misses += 1
            return None

    async def set(
        self,
        user_input: str,
        include_completeness: bool,
        simplified: bool,
        result: LLMClassificationResult,
    ) -> None:
        """
        Cache a classification result.

        Args:
            user_input: The user's input text
            include_completeness: Whether completeness was included
            simplified: Whether simplified prompt was used
            result: The classification result to cache
        """
        if not self.enabled:
            return

        key = self._make_key(user_input, include_completeness, simplified)

        try:
            value = self._serialize(result)
            await self._cache_set(key, value, self.ttl)
            logger.debug(f"Cache set: {key}")
        except Exception as e:
            logger.warning(f"Cache set error: {e}")

    def _serialize(self, result: LLMClassificationResult) -> str:
        """Serialize LLMClassificationResult to JSON string."""
        data = {
            "intent_category": result.intent_category.value,
            "sub_intent": result.sub_intent,
            "confidence": result.confidence,
            "completeness": {
                "is_complete": result.completeness.is_complete,
                "missing_fields": result.completeness.missing_fields,
                "optional_missing": result.completeness.optional_missing,
                "completeness_score": result.completeness.completeness_score,
                "suggestions": result.completeness.suggestions,
            },
            "reasoning": result.reasoning,
            "raw_response": result.raw_response,
            "model": result.model,
            "usage": result.usage,
        }
        return json.dumps(data, ensure_ascii=False)

    def _deserialize(self, value: str) -> LLMClassificationResult:
        """Deserialize JSON string to LLMClassificationResult."""
        data = json.loads(value)

        completeness_data = data.get("completeness", {})
        completeness = CompletenessInfo(
            is_complete=completeness_data.get("is_complete", True),
            missing_fields=completeness_data.get("missing_fields", []),
            optional_missing=completeness_data.get("optional_missing", []),
            completeness_score=completeness_data.get("completeness_score", 1.0),
            suggestions=completeness_data.get("suggestions", []),
        )

        return LLMClassificationResult(
            intent_category=ITIntentCategory.from_string(
                data.get("intent_category", "unknown")
            ),
            sub_intent=data.get("sub_intent"),
            confidence=data.get("confidence", 0.0),
            completeness=completeness,
            reasoning=data.get("reasoning", ""),
            raw_response=data.get("raw_response", ""),
            model=data.get("model", ""),
            usage=data.get("usage", {}),
        )

    async def _cache_get(self, key: str) -> Optional[str]:
        """Get value from Redis (supports sync/async clients)."""
        if hasattr(self.cache, "get"):
            if hasattr(self.cache.get, "__await__"):
                value = await self.cache.get(key)
            else:
                value = self.cache.get(key)

            if value is not None:
                if isinstance(value, bytes):
                    return value.decode("utf-8")
                return str(value)
        return None

    async def _cache_set(self, key: str, value: str, ttl: int) -> None:
        """Set value in Redis with TTL (supports sync/async clients)."""
        if hasattr(self.cache, "setex"):
            if hasattr(self.cache.setex, "__await__"):
                await self.cache.setex(key, ttl, value)
            else:
                self.cache.setex(key, ttl, value)
        elif hasattr(self.cache, "set"):
            if hasattr(self.cache.set, "__await__"):
                await self.cache.set(key, value, ex=ttl)
            else:
                self.cache.set(key, value, ex=ttl)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with hits, misses, hit_rate, total_requests
        """
        return {
            "enabled": self.enabled,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hit_rate, 4),
            "total_requests": self.hits + self.misses,
        }

    def reset_stats(self) -> None:
        """Reset cache statistics."""
        self.hits = 0
        self.misses = 0
