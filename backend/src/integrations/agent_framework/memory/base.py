# =============================================================================
# IPA Platform - Memory Storage Base Types
# =============================================================================
# Sprint 22: Memory System Migration (Phase 4)
#
# Base types and protocol for memory storage implementations.
# Follows official Agent Framework MemoryStorage interface.
# =============================================================================

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from uuid import UUID, uuid4

# =============================================================================
# 官方 Agent Framework API 導入
# =============================================================================
# Note: 官方 API 使用 Context 和 ContextProvider 進行上下文/記憶管理
# 我們定義自己的 MemoryStorage Protocol 以兼容自定義存儲後端
from agent_framework import Context, ContextProvider

logger = logging.getLogger(__name__)


# =============================================================================
# 異常類型
# =============================================================================


class MemoryError(Exception):
    """Memory 操作基礎異常。"""
    pass


class MemoryNotFoundError(MemoryError):
    """Memory 記錄未找到異常。"""
    pass


class MemoryStorageError(MemoryError):
    """Memory 存儲錯誤異常。"""
    pass


class MemoryValidationError(MemoryError):
    """Memory 數據驗證異常。"""
    pass


# =============================================================================
# 數據類型
# =============================================================================


@dataclass
class MemoryRecord:
    """
    Memory 記錄。

    存儲在 Memory 系統中的單個記錄。

    Attributes:
        key: 記錄的唯一鍵
        value: 記錄的值（任意 JSON 可序列化數據）
        metadata: 記錄的元數據
        created_at: 創建時間
        updated_at: 更新時間
        ttl_seconds: 生存時間（秒）
        tags: 標籤列表（用於搜索）
    """

    key: str
    value: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    ttl_seconds: Optional[int] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式。"""
        return {
            "key": self.key,
            "value": self.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "ttl_seconds": self.ttl_seconds,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryRecord":
        """從字典創建記錄。"""
        return cls(
            key=data["key"],
            value=data["value"],
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
            ttl_seconds=data.get("ttl_seconds"),
            tags=data.get("tags", []),
        )


@dataclass
class SearchOptions:
    """
    搜索選項。

    Attributes:
        limit: 最大返回數量
        offset: 偏移量
        include_metadata: 是否包含元數據
        tags_filter: 標籤過濾（AND 條件）
        score_threshold: 相似度分數閾值（用於向量搜索）
    """

    limit: int = 10
    offset: int = 0
    include_metadata: bool = True
    tags_filter: Optional[List[str]] = None
    score_threshold: Optional[float] = None


@dataclass
class MemorySearchResult:
    """
    搜索結果。

    Attributes:
        record: Memory 記錄
        score: 相似度分數（0-1）
        highlights: 高亮片段（關鍵詞搜索）
    """

    record: MemoryRecord
    score: float = 1.0
    highlights: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式。"""
        return {
            "record": self.record.to_dict(),
            "score": self.score,
            "highlights": self.highlights,
        }


# =============================================================================
# Memory Storage Protocol
# =============================================================================


@runtime_checkable
class MemoryStorageProtocol(Protocol):
    """
    Memory 存儲協議。

    定義與官方 Agent Framework MemoryStorage 兼容的接口。
    所有自定義存儲實現（Redis、PostgreSQL）必須實現此協議。

    Official API Reference:
        from agent_framework import MemoryStorage

        class MemoryStorage(Protocol):
            async def store(self, key: str, value: Any) -> None: ...
            async def retrieve(self, key: str) -> Optional[Any]: ...
            async def search(self, query: str, limit: int = 10) -> List[Any]: ...
            async def delete(self, key: str) -> bool: ...
    """

    async def store(self, key: str, value: Any) -> None:
        """
        存儲數據。

        Args:
            key: 記錄鍵
            value: 記錄值
        """
        ...

    async def retrieve(self, key: str) -> Optional[Any]:
        """
        檢索數據。

        Args:
            key: 記錄鍵

        Returns:
            記錄值，如果不存在返回 None
        """
        ...

    async def search(self, query: str, limit: int = 10) -> List[Any]:
        """
        搜索數據。

        Args:
            query: 搜索查詢
            limit: 最大返回數量

        Returns:
            匹配的記錄列表
        """
        ...

    async def delete(self, key: str) -> bool:
        """
        刪除數據。

        Args:
            key: 記錄鍵

        Returns:
            是否成功刪除
        """
        ...


# =============================================================================
# Base Memory Storage Adapter
# =============================================================================


class BaseMemoryStorageAdapter(ABC):
    """
    Memory 存儲適配器基類。

    提供通用功能和官方 API 整合。
    子類實現具體的存儲後端邏輯。
    """

    def __init__(
        self,
        namespace: str = "default",
        ttl_seconds: Optional[int] = None,
    ):
        """
        初始化適配器。

        Args:
            namespace: 命名空間（用於隔離不同應用的數據）
            ttl_seconds: 預設 TTL（秒）
        """
        self._namespace = namespace
        self._default_ttl = ttl_seconds
        self._initialized = False

        logger.info(f"BaseMemoryStorageAdapter initialized: namespace={namespace}")

    @property
    def namespace(self) -> str:
        """獲取命名空間。"""
        return self._namespace

    def _make_key(self, key: str) -> str:
        """生成帶命名空間的完整鍵。"""
        return f"{self._namespace}:{key}"

    def _strip_namespace(self, full_key: str) -> str:
        """從完整鍵中移除命名空間前綴。"""
        prefix = f"{self._namespace}:"
        if full_key.startswith(prefix):
            return full_key[len(prefix):]
        return full_key

    # =========================================================================
    # Official MemoryStorage Interface (必須實現)
    # =========================================================================

    @abstractmethod
    async def store(self, key: str, value: Any) -> None:
        """存儲數據（官方 API）。"""
        pass

    @abstractmethod
    async def retrieve(self, key: str) -> Optional[Any]:
        """檢索數據（官方 API）。"""
        pass

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[Any]:
        """搜索數據（官方 API）。"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """刪除數據（官方 API）。"""
        pass

    # =========================================================================
    # Extended Interface (擴展功能)
    # =========================================================================

    async def store_record(
        self,
        key: str,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> MemoryRecord:
        """
        存儲完整記錄（擴展 API）。

        Args:
            key: 記錄鍵
            value: 記錄值
            metadata: 元數據
            ttl_seconds: TTL（秒）
            tags: 標籤列表

        Returns:
            創建的記錄
        """
        record = MemoryRecord(
            key=key,
            value=value,
            metadata=metadata or {},
            ttl_seconds=ttl_seconds or self._default_ttl,
            tags=tags or [],
        )
        await self.store(key, record.to_dict())
        return record

    async def retrieve_record(self, key: str) -> Optional[MemoryRecord]:
        """
        檢索完整記錄（擴展 API）。

        Args:
            key: 記錄鍵

        Returns:
            記錄對象，如果不存在返回 None
        """
        data = await self.retrieve(key)
        if data is None:
            return None
        if isinstance(data, dict) and "key" in data:
            return MemoryRecord.from_dict(data)
        return MemoryRecord(key=key, value=data)

    async def search_advanced(
        self,
        query: str,
        options: Optional[SearchOptions] = None,
    ) -> List[MemorySearchResult]:
        """
        高級搜索（擴展 API）。

        Args:
            query: 搜索查詢
            options: 搜索選項

        Returns:
            搜索結果列表
        """
        opts = options or SearchOptions()
        results = await self.search(query, limit=opts.limit)

        search_results = []
        for item in results:
            if isinstance(item, dict) and "key" in item:
                record = MemoryRecord.from_dict(item)
            else:
                record = MemoryRecord(key=str(uuid4()), value=item)
            search_results.append(MemorySearchResult(record=record))

        return search_results

    async def exists(self, key: str) -> bool:
        """
        檢查記錄是否存在。

        Args:
            key: 記錄鍵

        Returns:
            是否存在
        """
        return await self.retrieve(key) is not None

    async def update(self, key: str, value: Any) -> bool:
        """
        更新記錄值。

        Args:
            key: 記錄鍵
            value: 新值

        Returns:
            是否成功更新
        """
        if not await self.exists(key):
            return False
        await self.store(key, value)
        return True

    async def get_or_create(
        self,
        key: str,
        default_value: Any,
    ) -> Any:
        """
        獲取或創建記錄。

        Args:
            key: 記錄鍵
            default_value: 預設值（如果不存在則創建）

        Returns:
            記錄值
        """
        existing = await self.retrieve(key)
        if existing is not None:
            return existing
        await self.store(key, default_value)
        return default_value

    async def clear_namespace(self) -> int:
        """
        清除命名空間下所有記錄。

        Returns:
            刪除的記錄數量
        """
        # 子類應覆寫此方法以實現高效的批量刪除
        logger.warning("clear_namespace not implemented in base class")
        return 0

    # =========================================================================
    # Lifecycle
    # =========================================================================

    async def initialize(self) -> None:
        """初始化存儲連接。"""
        self._initialized = True
        logger.debug(f"Memory storage initialized: {self.__class__.__name__}")

    async def close(self) -> None:
        """關閉存儲連接。"""
        self._initialized = False
        logger.debug(f"Memory storage closed: {self.__class__.__name__}")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(namespace={self._namespace})"
