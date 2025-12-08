# =============================================================================
# IPA Platform - Redis Memory Storage Adapter
# =============================================================================
# Sprint 22: Memory System Migration (Phase 4)
#
# Redis-based implementation of official MemoryStorage interface.
# Provides fast key-value storage with TTL support.
#
# Usage:
#   from integrations.agent_framework.memory import RedisMemoryStorage
#
#   storage = RedisMemoryStorage(redis_client)
#   await storage.store("user:123", {"name": "Alice"})
#   data = await storage.retrieve("user:123")
#   results = await storage.search("Alice")
#
# Reference:
#   - Phase 2: domain/orchestration/memory/redis_store.py
# =============================================================================

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Protocol

from .base import (
    BaseMemoryStorageAdapter,
    MemoryRecord,
    MemorySearchResult,
    MemoryStorageError,
    SearchOptions,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Redis Client Protocol
# =============================================================================


class RedisClientProtocol(Protocol):
    """
    Redis 客戶端協議。

    支持同步和異步 Redis 客戶端實現。
    """

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> Any: ...
    async def get(self, key: str) -> Optional[bytes]: ...
    async def delete(self, *keys: str) -> int: ...
    async def exists(self, key: str) -> int: ...
    async def expire(self, key: str, seconds: int) -> bool: ...
    async def keys(self, pattern: str) -> List[bytes]: ...
    async def scan(self, cursor: int, match: str, count: int) -> tuple: ...
    async def mget(self, *keys: str) -> List[Optional[bytes]]: ...
    async def mset(self, mapping: Dict[str, str]) -> bool: ...


# =============================================================================
# Redis Memory Storage
# =============================================================================


class RedisMemoryStorage(BaseMemoryStorageAdapter):
    """
    Redis-based Memory Storage.

    使用官方 MemoryStorage 接口，保留 Redis 後端實現。

    Features:
        - 支持 TTL 自動過期
        - 支持命名空間隔離
        - 支持關鍵詞搜索
        - 支持批量操作

    Example:
        ```python
        import redis.asyncio as redis

        redis_client = redis.Redis(host="localhost", port=6379)
        storage = RedisMemoryStorage(redis_client, namespace="myapp")

        # 存儲數據
        await storage.store("user:123", {"name": "Alice", "age": 30})

        # 檢索數據
        data = await storage.retrieve("user:123")
        print(data)  # {"name": "Alice", "age": 30}

        # 搜索數據
        results = await storage.search("Alice")
        ```
    """

    def __init__(
        self,
        redis_client: Any,
        namespace: str = "memory",
        ttl_seconds: Optional[int] = 86400,  # 24 hours default
        search_index_enabled: bool = True,
    ):
        """
        初始化 Redis Memory Storage.

        Args:
            redis_client: Redis 客戶端實例
            namespace: 命名空間前綴
            ttl_seconds: 預設 TTL（秒）
            search_index_enabled: 是否啟用搜索索引
        """
        super().__init__(namespace=namespace, ttl_seconds=ttl_seconds)
        self._redis = redis_client
        self._search_index_enabled = search_index_enabled
        self._search_index_key = f"{namespace}:search_index"

        logger.info(
            f"RedisMemoryStorage initialized: namespace={namespace}, "
            f"ttl={ttl_seconds}s, search_index={search_index_enabled}"
        )

    # =========================================================================
    # Official MemoryStorage Interface Implementation
    # =========================================================================

    async def store(self, key: str, value: Any) -> None:
        """
        存儲數據（官方 API）。

        Args:
            key: 記錄鍵
            value: 記錄值（將被 JSON 序列化）

        Raises:
            MemoryStorageError: 如果存儲失敗
        """
        try:
            full_key = self._make_key(key)
            value_json = json.dumps(value, default=str, ensure_ascii=False)

            if self._default_ttl:
                await self._redis.set(full_key, value_json, ex=self._default_ttl)
            else:
                await self._redis.set(full_key, value_json)

            # 更新搜索索引
            if self._search_index_enabled:
                await self._update_search_index(key, value)

            logger.debug(f"Stored key: {key}")

        except Exception as e:
            logger.error(f"Failed to store key {key}: {e}")
            raise MemoryStorageError(f"Failed to store key {key}: {e}") from e

    async def retrieve(self, key: str) -> Optional[Any]:
        """
        檢索數據（官方 API）。

        Args:
            key: 記錄鍵

        Returns:
            記錄值，如果不存在返回 None

        Raises:
            MemoryStorageError: 如果檢索失敗
        """
        try:
            full_key = self._make_key(key)
            data = await self._redis.get(full_key)

            if data is None:
                return None

            data_str = data.decode("utf-8") if isinstance(data, bytes) else data
            return json.loads(data_str)

        except json.JSONDecodeError:
            # 如果不是 JSON，返回原始字串
            return data.decode("utf-8") if isinstance(data, bytes) else data

        except Exception as e:
            logger.error(f"Failed to retrieve key {key}: {e}")
            raise MemoryStorageError(f"Failed to retrieve key {key}: {e}") from e

    async def search(self, query: str, limit: int = 10) -> List[Any]:
        """
        搜索數據（官方 API）。

        實現簡單的關鍵詞搜索。對於生產環境，建議使用
        Redis Search 或外部搜索引擎。

        Args:
            query: 搜索查詢
            limit: 最大返回數量

        Returns:
            匹配的記錄列表
        """
        try:
            results = []
            query_lower = query.lower()

            # 掃描所有鍵
            pattern = f"{self._namespace}:*"
            cursor = 0
            scanned_keys: List[str] = []

            while len(scanned_keys) < limit * 10:  # 掃描更多以找到匹配
                cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)

                for key in keys:
                    key_str = key.decode("utf-8") if isinstance(key, bytes) else key
                    scanned_keys.append(key_str)

                if cursor == 0:
                    break

            # 批量獲取並過濾
            if scanned_keys:
                values = await self._redis.mget(*scanned_keys)

                for key_str, value in zip(scanned_keys, values):
                    if value is None:
                        continue

                    try:
                        value_str = value.decode("utf-8") if isinstance(value, bytes) else value

                        # 檢查是否匹配查詢
                        if query_lower in value_str.lower():
                            data = json.loads(value_str)
                            results.append(data)

                            if len(results) >= limit:
                                break

                    except (json.JSONDecodeError, AttributeError):
                        continue

            logger.debug(f"Search '{query}' found {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Failed to search '{query}': {e}")
            return []

    async def delete(self, key: str) -> bool:
        """
        刪除數據（官方 API）。

        Args:
            key: 記錄鍵

        Returns:
            是否成功刪除
        """
        try:
            full_key = self._make_key(key)
            deleted = await self._redis.delete(full_key)

            # 從搜索索引移除
            if self._search_index_enabled:
                await self._remove_from_search_index(key)

            logger.debug(f"Deleted key: {key}, success={deleted > 0}")
            return deleted > 0

        except Exception as e:
            logger.error(f"Failed to delete key {key}: {e}")
            return False

    # =========================================================================
    # Extended Operations
    # =========================================================================

    async def store_with_ttl(
        self,
        key: str,
        value: Any,
        ttl_seconds: int,
    ) -> None:
        """
        存儲數據並設置特定 TTL。

        Args:
            key: 記錄鍵
            value: 記錄值
            ttl_seconds: TTL（秒）
        """
        full_key = self._make_key(key)
        value_json = json.dumps(value, default=str, ensure_ascii=False)
        await self._redis.set(full_key, value_json, ex=ttl_seconds)

        if self._search_index_enabled:
            await self._update_search_index(key, value)

    async def exists(self, key: str) -> bool:
        """
        檢查記錄是否存在。

        Args:
            key: 記錄鍵

        Returns:
            是否存在
        """
        full_key = self._make_key(key)
        return await self._redis.exists(full_key) > 0

    async def set_ttl(self, key: str, ttl_seconds: int) -> bool:
        """
        設置記錄的 TTL。

        Args:
            key: 記錄鍵
            ttl_seconds: TTL（秒）

        Returns:
            是否成功設置
        """
        full_key = self._make_key(key)
        return await self._redis.expire(full_key, ttl_seconds)

    async def get_keys(self, pattern: str = "*") -> List[str]:
        """
        獲取匹配模式的所有鍵。

        Args:
            pattern: 匹配模式

        Returns:
            鍵列表
        """
        full_pattern = self._make_key(pattern)
        keys = await self._redis.keys(full_pattern)
        return [self._strip_namespace(k.decode("utf-8") if isinstance(k, bytes) else k) for k in keys]

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        批量獲取多個記錄。

        Args:
            keys: 記錄鍵列表

        Returns:
            鍵值字典
        """
        full_keys = [self._make_key(k) for k in keys]
        values = await self._redis.mget(*full_keys)

        result = {}
        for key, value in zip(keys, values):
            if value is not None:
                try:
                    value_str = value.decode("utf-8") if isinstance(value, bytes) else value
                    result[key] = json.loads(value_str)
                except (json.JSONDecodeError, AttributeError):
                    result[key] = value

        return result

    async def set_many(self, data: Dict[str, Any]) -> bool:
        """
        批量設置多個記錄。

        Args:
            data: 鍵值字典

        Returns:
            是否成功
        """
        mapping = {}
        for key, value in data.items():
            full_key = self._make_key(key)
            mapping[full_key] = json.dumps(value, default=str, ensure_ascii=False)

        await self._redis.mset(mapping)

        if self._search_index_enabled:
            for key, value in data.items():
                await self._update_search_index(key, value)

        return True

    async def clear_namespace(self) -> int:
        """
        清除命名空間下所有記錄。

        Returns:
            刪除的記錄數量
        """
        pattern = f"{self._namespace}:*"
        cursor = 0
        deleted_count = 0

        while True:
            cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)

            if keys:
                deleted_count += await self._redis.delete(*keys)

            if cursor == 0:
                break

        logger.info(f"Cleared namespace {self._namespace}: {deleted_count} keys deleted")
        return deleted_count

    # =========================================================================
    # Search Index Operations
    # =========================================================================

    async def _update_search_index(self, key: str, value: Any) -> None:
        """
        更新搜索索引。

        將值的文本表示添加到搜索索引中。
        """
        # 簡單實現：存儲鍵和文本的映射
        # 生產環境應使用 Redis Search 或 Elasticsearch
        pass  # 當前搜索直接掃描鍵值

    async def _remove_from_search_index(self, key: str) -> None:
        """從搜索索引移除。"""
        pass  # 當前搜索直接掃描鍵值

    # =========================================================================
    # Lifecycle
    # =========================================================================

    async def initialize(self) -> None:
        """初始化 Redis 連接。"""
        await super().initialize()
        # 驗證連接
        try:
            await self._redis.ping()
            logger.info("Redis connection verified")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise MemoryStorageError(f"Redis connection failed: {e}") from e

    async def close(self) -> None:
        """關閉 Redis 連接。"""
        await super().close()
        # 注意：不關閉共享的 Redis 客戶端


# =============================================================================
# Factory Function
# =============================================================================


def create_redis_storage(
    redis_client: Any,
    namespace: str = "memory",
    ttl_seconds: Optional[int] = 86400,
) -> RedisMemoryStorage:
    """
    創建 Redis Memory Storage 實例。

    Args:
        redis_client: Redis 客戶端實例
        namespace: 命名空間前綴
        ttl_seconds: 預設 TTL（秒）

    Returns:
        RedisMemoryStorage 實例

    Example:
        import redis.asyncio as redis

        client = redis.Redis(host="localhost", port=6379)
        storage = create_redis_storage(client, namespace="myapp")
    """
    return RedisMemoryStorage(
        redis_client=redis_client,
        namespace=namespace,
        ttl_seconds=ttl_seconds,
    )
