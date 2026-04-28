# =============================================================================
# IPA Platform - LLM Cache Unit Tests
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Redis Cache Implementation
#
# Tests for the LLM cache service including:
#   - CacheEntry data structure
#   - CacheStats data structure
#   - LLMCacheService operations
#   - CachedAgentService wrapper
#   - Cache key generation
#   - Cache hit/miss tracking
# =============================================================================

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.infrastructure.cache.llm_cache import (
    CachedAgentService,
    CacheEntry,
    CacheStats,
    LLMCacheService,
)


# =============================================================================
# CacheEntry Tests
# =============================================================================


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_initialization(self):
        """Test basic initialization."""
        entry = CacheEntry(
            response="AI is artificial intelligence",
            model="gpt-4",
            prompt_hash="abc123",
        )

        assert entry.response == "AI is artificial intelligence"
        assert entry.model == "gpt-4"
        assert entry.prompt_hash == "abc123"
        assert entry.hit_count == 0
        assert entry.created_at is not None

    def test_initialization_with_metadata(self):
        """Test initialization with metadata."""
        entry = CacheEntry(
            response="Response",
            model="gpt-4",
            prompt_hash="hash",
            hit_count=5,
            metadata={"agent_id": "123"},
        )

        assert entry.hit_count == 5
        assert entry.metadata["agent_id"] == "123"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        now = datetime.utcnow()
        entry = CacheEntry(
            response="Test response",
            model="gpt-3.5",
            prompt_hash="xyz",
            created_at=now,
            metadata={"key": "value"},
        )

        result = entry.to_dict()

        assert result["response"] == "Test response"
        assert result["model"] == "gpt-3.5"
        assert result["prompt_hash"] == "xyz"
        assert result["hit_count"] == 0
        assert "created_at" in result
        assert result["metadata"]["key"] == "value"

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "response": "Cached response",
            "model": "gpt-4",
            "prompt_hash": "hash123",
            "created_at": "2024-01-15T10:30:00",
            "hit_count": 10,
            "metadata": {"source": "test"},
        }

        entry = CacheEntry.from_dict(data)

        assert entry.response == "Cached response"
        assert entry.model == "gpt-4"
        assert entry.hit_count == 10
        assert entry.metadata["source"] == "test"

    def test_from_dict_missing_created_at(self):
        """Test creating from dict without created_at."""
        data = {
            "response": "Response",
            "model": "gpt-4",
            "prompt_hash": "hash",
        }

        entry = CacheEntry.from_dict(data)
        assert entry.created_at is not None


# =============================================================================
# CacheStats Tests
# =============================================================================


class TestCacheStats:
    """Tests for CacheStats dataclass."""

    def test_initialization(self):
        """Test basic initialization."""
        stats = CacheStats()

        assert stats.total_entries == 0
        assert stats.total_hits == 0
        assert stats.total_misses == 0
        assert stats.hit_rate == 0.0
        assert stats.memory_usage_bytes == 0

    def test_initialization_with_values(self):
        """Test initialization with values."""
        stats = CacheStats(
            total_entries=100,
            total_hits=80,
            total_misses=20,
            hit_rate=0.8,
            memory_usage_bytes=1024,
        )

        assert stats.total_entries == 100
        assert stats.hit_rate == 0.8

    def test_to_dict(self):
        """Test serialization to dictionary."""
        stats = CacheStats(
            total_entries=50,
            total_hits=40,
            total_misses=10,
            hit_rate=0.8,
        )

        result = stats.to_dict()

        assert result["total_entries"] == 50
        assert result["total_hits"] == 40
        assert result["hit_rate"] == 0.8
        assert "last_reset" in result


# =============================================================================
# LLMCacheService Tests
# =============================================================================


class TestLLMCacheService:
    """Tests for LLMCacheService."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        mock = AsyncMock()
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock(return_value=True)
        mock.delete = AsyncMock(return_value=1)
        mock.hgetall = AsyncMock(return_value={})
        mock.hincrby = AsyncMock()
        mock.memory_usage = AsyncMock(return_value=0)

        # Mock scan_iter as async generator
        async def mock_scan_iter(match=None):
            if False:  # Empty generator
                yield

        mock.scan_iter = mock_scan_iter
        return mock

    @pytest.fixture
    def cache_service(self, mock_redis):
        """Create cache service with mock Redis."""
        return LLMCacheService(mock_redis, ttl_seconds=3600)

    def test_initialization(self, cache_service):
        """Test service initialization."""
        assert cache_service.enabled is True
        assert cache_service._ttl_seconds == 3600

    def test_enable_disable(self, cache_service):
        """Test enabling and disabling cache."""
        cache_service.disable()
        assert cache_service.enabled is False

        cache_service.enable()
        assert cache_service.enabled is True

    def test_generate_key(self, cache_service):
        """Test cache key generation."""
        key1 = cache_service._generate_key(
            model="gpt-4",
            prompt="What is AI?",
        )
        key2 = cache_service._generate_key(
            model="gpt-4",
            prompt="What is AI?",
        )
        key3 = cache_service._generate_key(
            model="gpt-3.5",
            prompt="What is AI?",
        )

        # Same inputs should produce same key
        assert key1 == key2

        # Different model should produce different key
        assert key1 != key3

        # Key should have prefix
        assert key1.startswith("llm_cache:")

    def test_generate_key_with_parameters(self, cache_service):
        """Test key generation with parameters."""
        key1 = cache_service._generate_key(
            model="gpt-4",
            prompt="Hello",
            parameters={"temperature": 0.7},
        )
        key2 = cache_service._generate_key(
            model="gpt-4",
            prompt="Hello",
            parameters={"temperature": 0.5},
        )

        # Different parameters should produce different keys
        assert key1 != key2

    def test_generate_key_long_prompt(self, cache_service):
        """Test key generation with long prompt."""
        long_prompt = "x" * 20000  # Exceeds MAX_PROMPT_LENGTH

        key = cache_service._generate_key(
            model="gpt-4",
            prompt=long_prompt,
        )

        # Should still generate valid key
        assert key.startswith("llm_cache:")
        assert len(key) > 0

    @pytest.mark.asyncio
    async def test_get_cache_miss(self, cache_service, mock_redis):
        """Test cache miss."""
        mock_redis.get.return_value = None

        result = await cache_service.get(
            model="gpt-4",
            prompt="What is AI?",
        )

        assert result is None
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cache_hit(self, cache_service, mock_redis):
        """Test cache hit."""
        cached_data = {
            "response": "AI is artificial intelligence",
            "model": "gpt-4",
            "prompt_hash": "abc123",
            "created_at": datetime.utcnow().isoformat(),
            "hit_count": 5,
            "metadata": {},
        }
        mock_redis.get.return_value = json.dumps(cached_data)

        result = await cache_service.get(
            model="gpt-4",
            prompt="What is AI?",
        )

        assert result is not None
        assert result.response == "AI is artificial intelligence"
        assert result.hit_count == 6  # Incremented

    @pytest.mark.asyncio
    async def test_get_disabled(self, cache_service, mock_redis):
        """Test get when cache disabled."""
        cache_service.disable()

        result = await cache_service.get(
            model="gpt-4",
            prompt="What is AI?",
        )

        assert result is None
        mock_redis.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_success(self, cache_service, mock_redis):
        """Test successful cache set."""
        result = await cache_service.set(
            model="gpt-4",
            prompt="What is AI?",
            response="AI is artificial intelligence",
        )

        assert result is True
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, cache_service, mock_redis):
        """Test set with custom TTL."""
        await cache_service.set(
            model="gpt-4",
            prompt="Test",
            response="Response",
            ttl_seconds=7200,
        )

        # Verify TTL was passed
        call_args = mock_redis.set.call_args
        assert call_args.kwargs.get("ex") == 7200

    @pytest.mark.asyncio
    async def test_set_with_metadata(self, cache_service, mock_redis):
        """Test set with metadata."""
        await cache_service.set(
            model="gpt-4",
            prompt="Test",
            response="Response",
            metadata={"agent_id": "123"},
        )

        # Verify metadata was included
        call_args = mock_redis.set.call_args
        cached_data = json.loads(call_args.args[1])
        assert cached_data["metadata"]["agent_id"] == "123"

    @pytest.mark.asyncio
    async def test_set_disabled(self, cache_service, mock_redis):
        """Test set when cache disabled."""
        cache_service.disable()

        result = await cache_service.set(
            model="gpt-4",
            prompt="Test",
            response="Response",
        )

        assert result is False
        mock_redis.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete(self, cache_service, mock_redis):
        """Test cache delete."""
        result = await cache_service.delete(
            model="gpt-4",
            prompt="What is AI?",
        )

        assert result is True
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_all(self, cache_service, mock_redis):
        """Test clearing all cache entries."""
        # Mock scan_iter to return some keys (must accept match parameter)
        async def mock_scan(match=None):
            yield "llm_cache:key1"
            yield "llm_cache:key2"

        mock_redis.scan_iter = mock_scan

        cleared = await cache_service.clear()

        assert cleared > 0
        mock_redis.delete.assert_called()

    @pytest.mark.asyncio
    async def test_get_stats(self, cache_service, mock_redis):
        """Test getting cache statistics."""
        mock_redis.hgetall.return_value = {
            b"hits": b"100",
            b"misses": b"20",
        }

        stats = await cache_service.get_stats()

        assert isinstance(stats, CacheStats)
        assert stats.total_hits == 100
        assert stats.total_misses == 20
        assert stats.hit_rate == 100 / 120

    @pytest.mark.asyncio
    async def test_reset_stats(self, cache_service, mock_redis):
        """Test resetting statistics."""
        await cache_service.reset_stats()

        mock_redis.delete.assert_called_with(cache_service.STATS_KEY)

    @pytest.mark.asyncio
    async def test_warm_cache(self, cache_service, mock_redis):
        """Test warming cache."""
        entries = [
            {"model": "gpt-4", "prompt": "Hello", "response": "Hi"},
            {"model": "gpt-4", "prompt": "Bye", "response": "Goodbye"},
        ]

        cached = await cache_service.warm_cache(entries)

        assert cached == 2
        assert mock_redis.set.call_count == 2


# =============================================================================
# CachedAgentService Tests
# =============================================================================


class TestCachedAgentService:
    """Tests for CachedAgentService."""

    @pytest.fixture
    def mock_agent_service(self):
        """Create mock agent service."""
        mock = AsyncMock()
        mock.execute = AsyncMock(return_value={
            "response": "Agent response",
            "execution_time": 1.5,
        })
        return mock

    @pytest.fixture
    def mock_cache(self):
        """Create mock cache service."""
        mock = MagicMock()
        mock.enabled = True
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock(return_value=True)
        return mock

    @pytest.fixture
    def cached_service(self, mock_agent_service, mock_cache):
        """Create cached agent service."""
        return CachedAgentService(mock_agent_service, mock_cache)

    @pytest.mark.asyncio
    async def test_execute_cache_miss(self, cached_service, mock_agent_service, mock_cache):
        """Test execution with cache miss."""
        mock_cache.get.return_value = None

        result = await cached_service.execute(
            agent_id="agent-1",
            prompt="What is AI?",
        )

        assert result["response"] == "Agent response"
        assert result["cached"] is False
        mock_agent_service.execute.assert_called_once()
        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_cache_hit(self, cached_service, mock_agent_service, mock_cache):
        """Test execution with cache hit."""
        mock_cache.get.return_value = CacheEntry(
            response="Cached response",
            model="default",
            prompt_hash="hash",
            hit_count=5,
        )

        result = await cached_service.execute(
            agent_id="agent-1",
            prompt="What is AI?",
        )

        assert result["response"] == "Cached response"
        assert result["cached"] is True
        assert result["cache_hit_count"] == 5
        mock_agent_service.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_bypass_cache(self, cached_service, mock_agent_service, mock_cache):
        """Test execution with cache bypass."""
        result = await cached_service.execute(
            agent_id="agent-1",
            prompt="What is AI?",
            bypass_cache=True,
        )

        assert result["cached"] is False
        mock_cache.get.assert_not_called()
        mock_agent_service.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_cache_disabled(self, cached_service, mock_agent_service, mock_cache):
        """Test execution when cache disabled."""
        mock_cache.enabled = False

        result = await cached_service.execute(
            agent_id="agent-1",
            prompt="What is AI?",
        )

        assert result["cached"] is False
        mock_cache.get.assert_not_called()
        mock_agent_service.execute.assert_called_once()

    def test_properties(self, cached_service, mock_agent_service, mock_cache):
        """Test property accessors."""
        assert cached_service.cache is mock_cache
        assert cached_service.agent_service is mock_agent_service


# =============================================================================
# Integration Scenario Tests
# =============================================================================


class TestCacheScenarios:
    """Tests for complete cache usage scenarios."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis with tracking."""
        mock = AsyncMock()
        mock._cache = {}
        mock._stats = {"hits": 0, "misses": 0}

        async def mock_get(key):
            if key in mock._cache:
                return mock._cache[key]
            return None

        async def mock_set(key, value, ex=None, keepttl=False):
            mock._cache[key] = value
            return True

        mock.get = mock_get
        mock.set = mock_set
        mock.delete = AsyncMock(return_value=1)
        mock.hgetall = AsyncMock(return_value={})
        mock.hincrby = AsyncMock()
        mock.memory_usage = AsyncMock(return_value=0)

        # Mock scan_iter must accept match parameter
        async def mock_scan(match=None):
            for key in list(mock._cache.keys()):
                yield key

        mock.scan_iter = mock_scan

        return mock

    @pytest.mark.asyncio
    async def test_full_cache_workflow(self, mock_redis):
        """Test complete cache workflow."""
        cache = LLMCacheService(mock_redis)

        # 1. Cache miss
        result = await cache.get(model="gpt-4", prompt="Hello")
        assert result is None

        # 2. Set cache
        await cache.set(
            model="gpt-4",
            prompt="Hello",
            response="Hi there!",
        )

        # 3. Cache hit
        result = await cache.get(model="gpt-4", prompt="Hello")
        assert result is not None
        assert result.response == "Hi there!"

    @pytest.mark.asyncio
    async def test_cache_key_consistency(self, mock_redis):
        """Test that same inputs produce same cache hits."""
        cache = LLMCacheService(mock_redis)

        # Set with specific model and prompt
        await cache.set(
            model="gpt-4",
            prompt="What is 2+2?",
            response="4",
        )

        # Get with same model and prompt
        result = await cache.get(
            model="gpt-4",
            prompt="What is 2+2?",
        )
        assert result is not None
        assert result.response == "4"

        # Different model should miss
        result = await cache.get(
            model="gpt-3.5",
            prompt="What is 2+2?",
        )
        # Would be None since we didn't cache for gpt-3.5

    @pytest.mark.asyncio
    async def test_hit_rate_tracking(self, mock_redis):
        """Test hit rate calculation."""
        cache = LLMCacheService(mock_redis)

        # Simulate hits and misses
        mock_redis.hgetall.return_value = {
            b"hits": b"60",
            b"misses": b"40",
        }

        stats = await cache.get_stats()

        assert stats.total_hits == 60
        assert stats.total_misses == 40
        assert stats.hit_rate == 0.6  # 60%
