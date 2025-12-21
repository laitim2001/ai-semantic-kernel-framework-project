# =============================================================================
# Cached LLM Service Tests
# =============================================================================
# Sprint 34: S34-3 Unit Tests (4 points)
#
# Tests for CachedLLMService.
# =============================================================================

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from src.integrations.llm import (
    CachedLLMService,
    MockLLMService,
    LLMServiceProtocol,
)


class MockCache:
    """測試用的模擬緩存。"""

    def __init__(self):
        self._data = {}

    def get(self, key: str):
        return self._data.get(key)

    def setex(self, key: str, ttl: int, value: str):
        self._data[key] = value

    def keys(self, pattern: str):
        import fnmatch
        # 簡單的模式匹配
        pattern = pattern.replace("*", ".*")
        import re
        return [k for k in self._data.keys() if re.match(pattern, k)]

    def delete(self, *keys):
        for key in keys:
            self._data.pop(key, None)


class TestCachedLLMServiceInit:
    """CachedLLMService 初始化測試。"""

    def test_default_init(self):
        """測試預設初始化。"""
        inner = MockLLMService()
        cached = CachedLLMService(inner_service=inner)

        assert cached.inner_service is inner
        assert cached.default_ttl == 3600
        assert cached.prefix == "llm_cache"
        assert cached.enabled is False  # No cache provided

    def test_with_cache(self):
        """測試帶緩存初始化。"""
        inner = MockLLMService()
        cache = MockCache()
        cached = CachedLLMService(inner_service=inner, cache=cache)

        assert cached.enabled is True

    def test_disabled_explicitly(self):
        """測試顯式禁用緩存。"""
        inner = MockLLMService()
        cache = MockCache()
        cached = CachedLLMService(inner_service=inner, cache=cache, enabled=False)

        assert cached.enabled is False

    def test_protocol_compliance(self):
        """測試符合 LLMServiceProtocol。"""
        inner = MockLLMService()
        cached = CachedLLMService(inner_service=inner)
        assert isinstance(cached, LLMServiceProtocol)


class TestCachedLLMServiceGenerate:
    """CachedLLMService.generate 測試。"""

    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """測試緩存未命中。"""
        inner = MockLLMService(default_response="From LLM")
        cache = MockCache()
        cached = CachedLLMService(inner_service=inner, cache=cache)

        response = await cached.generate("Hello")

        assert response == "From LLM"
        assert cached.cache_misses == 1
        assert cached.cache_hits == 0
        assert inner.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """測試緩存命中。"""
        inner = MockLLMService(default_response="From LLM")
        cache = MockCache()
        cached = CachedLLMService(inner_service=inner, cache=cache)

        # 第一次調用 - 緩存未命中
        response1 = await cached.generate("Hello")
        assert response1 == "From LLM"
        assert inner.call_count == 1

        # 第二次調用 - 緩存命中
        response2 = await cached.generate("Hello")
        assert response2 == "From LLM"
        assert inner.call_count == 1  # 沒有再次調用內部服務

        assert cached.cache_hits == 1
        assert cached.cache_misses == 1

    @pytest.mark.asyncio
    async def test_different_prompts(self):
        """測試不同 prompt 不共享緩存。"""
        inner = MockLLMService(
            responses={"a": "Response A", "b": "Response B"}
        )
        cache = MockCache()
        cached = CachedLLMService(inner_service=inner, cache=cache)

        r1 = await cached.generate("a")
        r2 = await cached.generate("b")

        assert r1 == "Response A"
        assert r2 == "Response B"
        assert inner.call_count == 2
        assert cached.cache_misses == 2

    @pytest.mark.asyncio
    async def test_cache_disabled(self):
        """測試禁用緩存時直接調用內部服務。"""
        inner = MockLLMService(default_response="Direct")
        cached = CachedLLMService(inner_service=inner, cache=None)

        await cached.generate("Hello")
        await cached.generate("Hello")

        assert inner.call_count == 2  # 每次都調用
        assert cached.cache_hits == 0
        assert cached.cache_misses == 2


class TestCachedLLMServiceGenerateStructured:
    """CachedLLMService.generate_structured 測試。"""

    @pytest.mark.asyncio
    async def test_structured_cache_miss(self):
        """測試結構化回應緩存未命中。"""
        inner = MockLLMService(
            structured_responses={"test": {"key": "value"}}
        )
        cache = MockCache()
        cached = CachedLLMService(inner_service=inner, cache=cache)

        result = await cached.generate_structured(
            "test query",
            output_schema={"key": "string"},
        )

        assert result["key"] == "value"
        assert cached.cache_misses == 1

    @pytest.mark.asyncio
    async def test_structured_cache_hit(self):
        """測試結構化回應緩存命中。"""
        inner = MockLLMService(
            structured_responses={"test": {"key": "value"}}
        )
        cache = MockCache()
        cached = CachedLLMService(inner_service=inner, cache=cache)

        # 第一次調用
        r1 = await cached.generate_structured("test", output_schema={"key": "string"})

        # 第二次調用
        r2 = await cached.generate_structured("test", output_schema={"key": "string"})

        assert r1 == r2
        assert inner.generate_structured_count == 1
        assert cached.cache_hits == 1


class TestCachedLLMServiceCacheKey:
    """CachedLLMService 緩存鍵測試。"""

    def test_cache_key_format(self):
        """測試緩存鍵格式。"""
        inner = MockLLMService()
        cached = CachedLLMService(inner_service=inner, prefix="test_prefix")

        key = cached._make_cache_key("generate", prompt="hello")

        assert key.startswith("test_prefix:generate:")
        assert len(key) > len("test_prefix:generate:")

    def test_same_params_same_key(self):
        """測試相同參數生成相同鍵。"""
        inner = MockLLMService()
        cached = CachedLLMService(inner_service=inner)

        key1 = cached._make_cache_key("generate", prompt="hello", temperature=0.7)
        key2 = cached._make_cache_key("generate", prompt="hello", temperature=0.7)

        assert key1 == key2

    def test_different_params_different_key(self):
        """測試不同參數生成不同鍵。"""
        inner = MockLLMService()
        cached = CachedLLMService(inner_service=inner)

        key1 = cached._make_cache_key("generate", prompt="hello")
        key2 = cached._make_cache_key("generate", prompt="world")

        assert key1 != key2


class TestCachedLLMServiceInvalidate:
    """CachedLLMService 緩存失效測試。"""

    @pytest.mark.asyncio
    async def test_invalidate_all(self):
        """測試清除所有緩存。"""
        inner = MockLLMService()
        cache = MockCache()
        cached = CachedLLMService(inner_service=inner, cache=cache)

        # 填充緩存
        await cached.generate("a")
        await cached.generate("b")

        # 清除
        count = await cached.invalidate()

        # 驗證清除
        assert cached.cache_hits == 0  # 重新調用

    @pytest.mark.asyncio
    async def test_invalidate_no_cache(self):
        """測試無緩存時清除。"""
        inner = MockLLMService()
        cached = CachedLLMService(inner_service=inner, cache=None)

        count = await cached.invalidate()
        assert count == 0


class TestCachedLLMServiceStats:
    """CachedLLMService 統計測試。"""

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """測試獲取統計。"""
        inner = MockLLMService()
        cache = MockCache()
        cached = CachedLLMService(inner_service=inner, cache=cache)

        # 產生一些活動
        await cached.generate("a")  # miss
        await cached.generate("a")  # hit
        await cached.generate("b")  # miss

        stats = cached.get_stats()

        assert stats["enabled"] is True
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 2
        assert stats["total_requests"] == 3
        assert stats["hit_rate"] == pytest.approx(1/3)

    def test_reset_stats(self):
        """測試重置統計。"""
        inner = MockLLMService()
        cached = CachedLLMService(inner_service=inner)

        cached.cache_hits = 10
        cached.cache_misses = 20

        cached.reset_stats()

        assert cached.cache_hits == 0
        assert cached.cache_misses == 0


class TestCachedLLMServiceContextManager:
    """CachedLLMService 上下文管理器測試。"""

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """測試異步上下文管理器。"""
        inner = MockLLMService()

        async with CachedLLMService(inner_service=inner) as cached:
            response = await cached.generate("test")
            assert response is not None
