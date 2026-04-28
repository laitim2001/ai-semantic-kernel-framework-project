"""
ClassificationCache Tests

Tests Redis-backed cache for LLM classification results.

Sprint 128: Story 128-3
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.integrations.orchestration.intent_router.llm_classifier.cache import (
    ClassificationCache,
)
from src.integrations.orchestration.intent_router.models import (
    CompletenessInfo,
    ITIntentCategory,
    LLMClassificationResult,
)


# =============================================================================
# Helpers
# =============================================================================


def _make_result(
    category: ITIntentCategory = ITIntentCategory.INCIDENT,
    confidence: float = 0.95,
) -> LLMClassificationResult:
    """Create a test LLMClassificationResult."""
    return LLMClassificationResult(
        intent_category=category,
        sub_intent="etl_failure",
        confidence=confidence,
        completeness=CompletenessInfo(
            is_complete=True,
            completeness_score=0.9,
        ),
        reasoning="Test reasoning",
        raw_response='{"intent_category": "incident"}',
        model="test-model",
        usage={"input_tokens": 100},
    )


def _make_mock_redis() -> MagicMock:
    """Create a mock Redis client with sync-like interface."""
    mock = MagicMock()
    mock.get = MagicMock(return_value=None)
    mock.setex = MagicMock()
    return mock


# =============================================================================
# Tests
# =============================================================================


class TestClassificationCacheInit:
    """Tests for cache initialization."""

    def test_enabled_with_cache(self):
        """Cache is enabled when Redis client is provided."""
        cache = ClassificationCache(cache=MagicMock())
        assert cache.enabled is True

    def test_disabled_without_cache(self):
        """Cache is disabled when no Redis client."""
        cache = ClassificationCache(cache=None)
        assert cache.enabled is False

    def test_custom_ttl(self):
        """Custom TTL is set correctly."""
        cache = ClassificationCache(cache=MagicMock(), ttl=900)
        assert cache.ttl == 900

    def test_custom_prefix(self):
        """Custom prefix is set correctly."""
        cache = ClassificationCache(cache=MagicMock(), prefix="test_classify")
        assert cache.prefix == "test_classify"


class TestClassificationCacheHitMiss:
    """Tests for cache hit and miss behavior."""

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self):
        """Cache miss returns None and increments miss counter."""
        mock_redis = _make_mock_redis()
        mock_redis.get.return_value = None
        cache = ClassificationCache(cache=mock_redis)

        result = await cache.get("test input")

        assert result is None
        assert cache.misses == 1
        assert cache.hits == 0

    @pytest.mark.asyncio
    async def test_cache_hit_returns_result(self):
        """Cache hit returns deserialized result and increments hit counter."""
        test_result = _make_result()
        cache = ClassificationCache(cache=MagicMock())

        # Serialize manually to simulate Redis stored value
        serialized = cache._serialize(test_result)
        cache.cache.get = MagicMock(return_value=serialized)

        result = await cache.get("test input")

        assert result is not None
        assert result.intent_category == ITIntentCategory.INCIDENT
        assert result.confidence == 0.95
        assert cache.hits == 1

    @pytest.mark.asyncio
    async def test_cache_set_stores_result(self):
        """Set stores serialized result in Redis with TTL."""
        mock_redis = _make_mock_redis()
        cache = ClassificationCache(cache=mock_redis, ttl=1800)
        test_result = _make_result()

        await cache.set("test input", True, False, test_result)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args[0]
        assert call_args[1] == 1800  # TTL
        stored_json = json.loads(call_args[2])
        assert stored_json["intent_category"] == "incident"

    @pytest.mark.asyncio
    async def test_cache_disabled_passthrough(self):
        """Disabled cache always returns None, no Redis calls."""
        cache = ClassificationCache(cache=None)

        result = await cache.get("test input")

        assert result is None
        assert cache.misses == 1


class TestClassificationCacheSerialization:
    """Tests for serialization/deserialization."""

    def test_serialize_deserialize_roundtrip(self):
        """Serialization round-trip preserves all fields."""
        cache = ClassificationCache(cache=MagicMock())
        original = _make_result()

        serialized = cache._serialize(original)
        deserialized = cache._deserialize(serialized)

        assert deserialized.intent_category == original.intent_category
        assert deserialized.sub_intent == original.sub_intent
        assert deserialized.confidence == original.confidence
        assert deserialized.reasoning == original.reasoning
        assert deserialized.completeness.is_complete == original.completeness.is_complete

    def test_serialize_with_completeness(self):
        """Serialization includes completeness info."""
        cache = ClassificationCache(cache=MagicMock())
        result = LLMClassificationResult(
            intent_category=ITIntentCategory.REQUEST,
            confidence=0.85,
            completeness=CompletenessInfo(
                is_complete=False,
                missing_fields=["申請人", "原因"],
                completeness_score=0.4,
            ),
        )

        serialized = cache._serialize(result)
        data = json.loads(serialized)

        assert data["completeness"]["is_complete"] is False
        assert "申請人" in data["completeness"]["missing_fields"]


class TestClassificationCacheKeyGeneration:
    """Tests for cache key generation."""

    def test_same_input_same_key(self):
        """Same input produces same cache key."""
        cache = ClassificationCache(cache=MagicMock())
        key1 = cache._make_key("test input", True, False)
        key2 = cache._make_key("test input", True, False)
        assert key1 == key2

    def test_different_input_different_key(self):
        """Different inputs produce different keys."""
        cache = ClassificationCache(cache=MagicMock())
        key1 = cache._make_key("input A", True, False)
        key2 = cache._make_key("input B", True, False)
        assert key1 != key2

    def test_different_flags_different_key(self):
        """Different flags produce different keys."""
        cache = ClassificationCache(cache=MagicMock())
        key1 = cache._make_key("test", True, False)
        key2 = cache._make_key("test", False, False)
        key3 = cache._make_key("test", True, True)
        assert key1 != key2
        assert key1 != key3

    def test_key_has_prefix(self):
        """Key starts with configured prefix."""
        cache = ClassificationCache(cache=MagicMock(), prefix="myprefix")
        key = cache._make_key("test", True, False)
        assert key.startswith("myprefix:")


class TestClassificationCacheStats:
    """Tests for cache statistics."""

    @pytest.mark.asyncio
    async def test_stats_tracking(self):
        """Stats correctly track hits and misses."""
        mock_redis = _make_mock_redis()
        cache = ClassificationCache(cache=mock_redis)

        # 2 misses
        await cache.get("miss1")
        await cache.get("miss2")

        stats = cache.get_stats()
        assert stats["misses"] == 2
        assert stats["hits"] == 0
        assert stats["hit_rate"] == 0.0
        assert stats["total_requests"] == 2

    def test_hit_rate_calculation(self):
        """Hit rate is correctly calculated."""
        cache = ClassificationCache(cache=MagicMock())
        cache.hits = 3
        cache.misses = 7
        assert cache.hit_rate == 0.3

    def test_reset_stats(self):
        """Stats reset clears all counters."""
        cache = ClassificationCache(cache=MagicMock())
        cache.hits = 10
        cache.misses = 5
        cache.reset_stats()
        assert cache.hits == 0
        assert cache.misses == 0
