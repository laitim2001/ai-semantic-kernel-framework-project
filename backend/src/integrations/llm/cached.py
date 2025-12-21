# =============================================================================
# IPA Platform - Cached LLM Service
# =============================================================================
# Sprint 34: S34-2 LLM Service Factory (5 points)
#
# Caching wrapper for LLM services using Redis.
# Reduces API costs and latency for repeated queries.
#
# Features:
#   - Redis-based response caching
#   - Configurable TTL per operation type
#   - Hash-based cache keys
#   - Automatic cache invalidation
#   - Fallback on cache miss
# =============================================================================

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from .protocol import LLMServiceProtocol

logger = logging.getLogger(__name__)


class CachedLLMService:
    """帶緩存的 LLM 服務包裝器。

    使用 Redis 緩存 LLM 回應，減少 API 調用成本和延遲。
    包裝任何實現 LLMServiceProtocol 的服務。

    Attributes:
        inner_service: 被包裝的 LLM 服務
        cache: Redis 緩存實例
        default_ttl: 預設緩存 TTL（秒）
        prefix: 緩存鍵前綴

    Example:
        ```python
        from redis import Redis

        inner = AzureOpenAILLMService()
        cache = Redis(host='localhost', port=6379)

        cached_service = CachedLLMService(
            inner_service=inner,
            cache=cache,
            default_ttl=3600,  # 1 小時
        )

        # 第一次調用 - 調用 LLM 並緩存
        response1 = await cached_service.generate("Hello")

        # 第二次調用 - 從緩存返回
        response2 = await cached_service.generate("Hello")  # 毫秒級返回
        ```
    """

    def __init__(
        self,
        inner_service: LLMServiceProtocol,
        cache: Optional[Any] = None,
        default_ttl: int = 3600,
        prefix: str = "llm_cache",
        enabled: bool = True,
    ):
        """初始化緩存 LLM 服務。

        Args:
            inner_service: 被包裝的 LLM 服務
            cache: Redis 緩存實例，如為 None 則禁用緩存
            default_ttl: 預設緩存 TTL（秒），預設 3600（1 小時）
            prefix: 緩存鍵前綴，預設 "llm_cache"
            enabled: 是否啟用緩存，預設 True
        """
        self.inner_service = inner_service
        self.cache = cache
        self.default_ttl = default_ttl
        self.prefix = prefix
        self.enabled = enabled and cache is not None

        # 統計
        self.cache_hits = 0
        self.cache_misses = 0

        logger.info(
            f"CachedLLMService initialized: "
            f"enabled={self.enabled}, "
            f"ttl={self.default_ttl}s, "
            f"prefix={self.prefix}"
        )

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        """生成文本回應（帶緩存）。

        Args:
            prompt: 輸入提示詞
            max_tokens: 最大 token 數
            temperature: 溫度參數
            stop: 停止序列
            **kwargs: 額外參數

        Returns:
            生成的文本或緩存的回應
        """
        # 緩存鍵
        cache_key = self._make_cache_key(
            "generate",
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop,
        )

        # 嘗試從緩存獲取
        if self.enabled:
            cached = await self._get_from_cache(cache_key)
            if cached is not None:
                self.cache_hits += 1
                logger.debug(f"Cache hit for generate: {cache_key[:20]}...")
                return cached

        # 緩存未命中，調用內部服務
        self.cache_misses += 1
        response = await self.inner_service.generate(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop,
            **kwargs,
        )

        # 存入緩存
        if self.enabled:
            await self._set_to_cache(cache_key, response)

        return response

    async def generate_structured(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        max_tokens: int = 2000,
        temperature: float = 0.3,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """生成結構化回應（帶緩存）。

        Args:
            prompt: 輸入提示詞
            output_schema: 輸出 schema
            max_tokens: 最大 token 數
            temperature: 溫度參數
            **kwargs: 額外參數

        Returns:
            結構化回應或緩存的回應
        """
        # 緩存鍵
        cache_key = self._make_cache_key(
            "generate_structured",
            prompt=prompt,
            output_schema=output_schema,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # 嘗試從緩存獲取
        if self.enabled:
            cached = await self._get_from_cache(cache_key)
            if cached is not None:
                self.cache_hits += 1
                logger.debug(f"Cache hit for generate_structured: {cache_key[:20]}...")
                return json.loads(cached)

        # 緩存未命中，調用內部服務
        self.cache_misses += 1
        response = await self.inner_service.generate_structured(
            prompt=prompt,
            output_schema=output_schema,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

        # 存入緩存
        if self.enabled:
            await self._set_to_cache(cache_key, json.dumps(response))

        return response

    def _make_cache_key(self, operation: str, **params: Any) -> str:
        """生成緩存鍵。

        使用參數的 SHA256 哈希作為緩存鍵。

        Args:
            operation: 操作類型
            **params: 操作參數

        Returns:
            緩存鍵字符串
        """
        # 序列化參數
        params_str = json.dumps(params, sort_keys=True, ensure_ascii=False)

        # 計算哈希
        hash_value = hashlib.sha256(params_str.encode()).hexdigest()[:16]

        return f"{self.prefix}:{operation}:{hash_value}"

    async def _get_from_cache(self, key: str) -> Optional[str]:
        """從緩存獲取值。

        Args:
            key: 緩存鍵

        Returns:
            緩存值，如不存在則返回 None
        """
        if not self.cache:
            return None

        try:
            # 支援同步和異步 Redis 客戶端
            if hasattr(self.cache, "get"):
                if hasattr(self.cache.get, "__await__"):
                    # 異步客戶端
                    value = await self.cache.get(key)
                else:
                    # 同步客戶端
                    value = self.cache.get(key)

                if value is not None:
                    if isinstance(value, bytes):
                        return value.decode("utf-8")
                    return str(value)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")

        return None

    async def _set_to_cache(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """設置緩存值。

        Args:
            key: 緩存鍵
            value: 緩存值
            ttl: TTL（秒），如為 None 則使用預設值
        """
        if not self.cache:
            return

        ttl = ttl or self.default_ttl

        try:
            # 支援同步和異步 Redis 客戶端
            if hasattr(self.cache, "setex"):
                if hasattr(self.cache.setex, "__await__"):
                    # 異步客戶端
                    await self.cache.setex(key, ttl, value)
                else:
                    # 同步客戶端
                    self.cache.setex(key, ttl, value)
            elif hasattr(self.cache, "set"):
                if hasattr(self.cache.set, "__await__"):
                    await self.cache.set(key, value, ex=ttl)
                else:
                    self.cache.set(key, value, ex=ttl)
        except Exception as e:
            logger.warning(f"Cache set error: {e}")

    async def invalidate(self, pattern: Optional[str] = None) -> int:
        """使緩存失效。

        Args:
            pattern: 緩存鍵模式，如為 None 則清除所有

        Returns:
            清除的鍵數量
        """
        if not self.cache:
            return 0

        try:
            search_pattern = pattern or f"{self.prefix}:*"

            # 獲取匹配的鍵
            if hasattr(self.cache, "keys"):
                if hasattr(self.cache.keys, "__await__"):
                    keys = await self.cache.keys(search_pattern)
                else:
                    keys = self.cache.keys(search_pattern)

                if keys:
                    if hasattr(self.cache, "delete"):
                        if hasattr(self.cache.delete, "__await__"):
                            await self.cache.delete(*keys)
                        else:
                            self.cache.delete(*keys)
                    return len(keys)
        except Exception as e:
            logger.warning(f"Cache invalidate error: {e}")

        return 0

    def get_stats(self) -> Dict[str, Any]:
        """獲取緩存統計。

        Returns:
            統計字典
        """
        total = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total if total > 0 else 0.0

        return {
            "enabled": self.enabled,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": hit_rate,
            "total_requests": total,
        }

    def reset_stats(self) -> None:
        """重置統計。"""
        self.cache_hits = 0
        self.cache_misses = 0
        logger.debug("CachedLLMService stats reset")

    async def close(self) -> None:
        """關閉服務。"""
        await self.inner_service.close()
        logger.info("CachedLLMService closed")

    async def __aenter__(self) -> "CachedLLMService":
        """異步上下文管理器進入。"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """異步上下文管理器退出。"""
        await self.close()
