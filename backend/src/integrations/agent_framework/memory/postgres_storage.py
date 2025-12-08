# =============================================================================
# IPA Platform - PostgreSQL Memory Storage Adapter
# =============================================================================
# Sprint 22: Memory System Migration (Phase 4)
#
# PostgreSQL-based implementation of official MemoryStorage interface.
# Provides persistent storage with SQL query capabilities.
#
# Usage:
#   from integrations.agent_framework.memory import PostgresMemoryStorage
#
#   storage = PostgresMemoryStorage(async_connection)
#   await storage.store("user:123", {"name": "Alice"})
#   data = await storage.retrieve("user:123")
#   results = await storage.search("Alice")
#
# Reference:
#   - Phase 2: domain/orchestration/memory/postgres_store.py
# =============================================================================

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Protocol, Tuple

from .base import (
    BaseMemoryStorageAdapter,
    MemoryRecord,
    MemorySearchResult,
    MemoryStorageError,
    SearchOptions,
)

logger = logging.getLogger(__name__)


# =============================================================================
# PostgreSQL Connection Protocol
# =============================================================================


class PostgresConnectionProtocol(Protocol):
    """
    PostgreSQL 連接協議。

    支持異步 PostgreSQL 連接實現（如 asyncpg, aiopg）。
    """

    async def execute(self, query: str, *args: Any) -> Any: ...
    async def fetch(self, query: str, *args: Any) -> List[Any]: ...
    async def fetchrow(self, query: str, *args: Any) -> Optional[Any]: ...
    async def fetchval(self, query: str, *args: Any) -> Optional[Any]: ...


# =============================================================================
# PostgreSQL Memory Storage
# =============================================================================


class PostgresMemoryStorage(BaseMemoryStorageAdapter):
    """
    PostgreSQL-based Memory Storage.

    使用官方 MemoryStorage 接口，保留 PostgreSQL 後端實現。

    Features:
        - 持久化存儲
        - SQL 搜索能力
        - 支持命名空間隔離
        - 支持元數據和標籤
        - 支持 JSONB 查詢

    Database Schema:
        CREATE TABLE IF NOT EXISTS memory_storage (
            id SERIAL PRIMARY KEY,
            namespace VARCHAR(255) NOT NULL,
            key VARCHAR(512) NOT NULL,
            value JSONB NOT NULL,
            metadata JSONB DEFAULT '{}',
            tags TEXT[] DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            expires_at TIMESTAMP,
            UNIQUE(namespace, key)
        );

        CREATE INDEX idx_memory_namespace ON memory_storage(namespace);
        CREATE INDEX idx_memory_key ON memory_storage(key);
        CREATE INDEX idx_memory_tags ON memory_storage USING GIN(tags);
        CREATE INDEX idx_memory_value ON memory_storage USING GIN(value);

    Example:
        ```python
        import asyncpg

        conn = await asyncpg.connect(...)
        storage = PostgresMemoryStorage(conn, namespace="myapp")

        # 存儲數據
        await storage.store("user:123", {"name": "Alice", "age": 30})

        # 檢索數據
        data = await storage.retrieve("user:123")
        print(data)  # {"name": "Alice", "age": 30}

        # 搜索數據
        results = await storage.search("Alice")
        ```
    """

    TABLE_NAME = "memory_storage"

    def __init__(
        self,
        connection: Any,
        namespace: str = "memory",
        ttl_seconds: Optional[int] = None,
        auto_create_table: bool = True,
    ):
        """
        初始化 PostgreSQL Memory Storage.

        Args:
            connection: PostgreSQL 連接實例
            namespace: 命名空間前綴
            ttl_seconds: 預設 TTL（秒）
            auto_create_table: 是否自動創建表
        """
        super().__init__(namespace=namespace, ttl_seconds=ttl_seconds)
        self._conn = connection
        self._auto_create_table = auto_create_table
        self._table_created = False

        logger.info(
            f"PostgresMemoryStorage initialized: namespace={namespace}, "
            f"ttl={ttl_seconds}s"
        )

    # =========================================================================
    # Table Management
    # =========================================================================

    async def _ensure_table(self) -> None:
        """確保表存在。"""
        if self._table_created:
            return

        if self._auto_create_table:
            await self._create_table()
            self._table_created = True

    async def _create_table(self) -> None:
        """創建存儲表。"""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
            id SERIAL PRIMARY KEY,
            namespace VARCHAR(255) NOT NULL,
            key VARCHAR(512) NOT NULL,
            value JSONB NOT NULL,
            metadata JSONB DEFAULT '{{}}',
            tags TEXT[] DEFAULT '{{}}',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            expires_at TIMESTAMP,
            UNIQUE(namespace, key)
        );
        """

        create_indexes_sql = f"""
        CREATE INDEX IF NOT EXISTS idx_memory_namespace ON {self.TABLE_NAME}(namespace);
        CREATE INDEX IF NOT EXISTS idx_memory_key ON {self.TABLE_NAME}(key);
        CREATE INDEX IF NOT EXISTS idx_memory_tags ON {self.TABLE_NAME} USING GIN(tags);
        CREATE INDEX IF NOT EXISTS idx_memory_value ON {self.TABLE_NAME} USING GIN(value);
        CREATE INDEX IF NOT EXISTS idx_memory_expires ON {self.TABLE_NAME}(expires_at);
        """

        try:
            await self._conn.execute(create_table_sql)
            await self._conn.execute(create_indexes_sql)
            logger.info(f"Table {self.TABLE_NAME} created/verified")
        except Exception as e:
            logger.error(f"Failed to create table: {e}")
            raise MemoryStorageError(f"Failed to create table: {e}") from e

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
        await self._ensure_table()

        try:
            value_json = json.dumps(value, default=str, ensure_ascii=False)
            expires_at = None

            if self._default_ttl:
                expires_at = datetime.utcnow() + timedelta(seconds=self._default_ttl)

            upsert_sql = f"""
            INSERT INTO {self.TABLE_NAME} (namespace, key, value, expires_at, updated_at)
            VALUES ($1, $2, $3::jsonb, $4, NOW())
            ON CONFLICT (namespace, key)
            DO UPDATE SET
                value = EXCLUDED.value,
                expires_at = EXCLUDED.expires_at,
                updated_at = NOW()
            """

            await self._conn.execute(
                upsert_sql,
                self._namespace,
                key,
                value_json,
                expires_at,
            )

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
            記錄值，如果不存在或已過期返回 None

        Raises:
            MemoryStorageError: 如果檢索失敗
        """
        await self._ensure_table()

        try:
            select_sql = f"""
            SELECT value FROM {self.TABLE_NAME}
            WHERE namespace = $1 AND key = $2
            AND (expires_at IS NULL OR expires_at > NOW())
            """

            row = await self._conn.fetchrow(select_sql, self._namespace, key)

            if row is None:
                return None

            value = row["value"]
            if isinstance(value, str):
                return json.loads(value)
            return value

        except Exception as e:
            logger.error(f"Failed to retrieve key {key}: {e}")
            raise MemoryStorageError(f"Failed to retrieve key {key}: {e}") from e

    async def search(self, query: str, limit: int = 10) -> List[Any]:
        """
        搜索數據（官方 API）。

        使用 PostgreSQL JSONB 和文本搜索功能。

        Args:
            query: 搜索查詢
            limit: 最大返回數量

        Returns:
            匹配的記錄列表
        """
        await self._ensure_table()

        try:
            # 使用 ILIKE 進行簡單的文本搜索
            # 對於生產環境，建議使用全文搜索或向量搜索
            search_sql = f"""
            SELECT value FROM {self.TABLE_NAME}
            WHERE namespace = $1
            AND (expires_at IS NULL OR expires_at > NOW())
            AND value::text ILIKE $2
            ORDER BY updated_at DESC
            LIMIT $3
            """

            search_pattern = f"%{query}%"
            rows = await self._conn.fetch(search_sql, self._namespace, search_pattern, limit)

            results = []
            for row in rows:
                value = row["value"]
                if isinstance(value, str):
                    value = json.loads(value)
                results.append(value)

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
        await self._ensure_table()

        try:
            delete_sql = f"""
            DELETE FROM {self.TABLE_NAME}
            WHERE namespace = $1 AND key = $2
            """

            result = await self._conn.execute(delete_sql, self._namespace, key)

            # asyncpg 返回 "DELETE N" 格式的字串
            deleted = False
            if isinstance(result, str) and result.startswith("DELETE"):
                deleted = int(result.split()[-1]) > 0

            logger.debug(f"Deleted key: {key}, success={deleted}")
            return deleted

        except Exception as e:
            logger.error(f"Failed to delete key {key}: {e}")
            return False

    # =========================================================================
    # Extended Operations
    # =========================================================================

    async def store_with_metadata(
        self,
        key: str,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """
        存儲帶元數據的記錄。

        Args:
            key: 記錄鍵
            value: 記錄值
            metadata: 元數據
            tags: 標籤列表
            ttl_seconds: TTL（秒）
        """
        await self._ensure_table()

        value_json = json.dumps(value, default=str, ensure_ascii=False)
        metadata_json = json.dumps(metadata or {}, default=str, ensure_ascii=False)
        expires_at = None

        if ttl_seconds or self._default_ttl:
            ttl = ttl_seconds or self._default_ttl
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)

        upsert_sql = f"""
        INSERT INTO {self.TABLE_NAME} (namespace, key, value, metadata, tags, expires_at, updated_at)
        VALUES ($1, $2, $3::jsonb, $4::jsonb, $5, $6, NOW())
        ON CONFLICT (namespace, key)
        DO UPDATE SET
            value = EXCLUDED.value,
            metadata = EXCLUDED.metadata,
            tags = EXCLUDED.tags,
            expires_at = EXCLUDED.expires_at,
            updated_at = NOW()
        """

        await self._conn.execute(
            upsert_sql,
            self._namespace,
            key,
            value_json,
            metadata_json,
            tags or [],
            expires_at,
        )

    async def retrieve_with_metadata(self, key: str) -> Optional[Tuple[Any, Dict[str, Any], List[str]]]:
        """
        檢索帶元數據的記錄。

        Args:
            key: 記錄鍵

        Returns:
            (value, metadata, tags) 元組，如果不存在返回 None
        """
        await self._ensure_table()

        select_sql = f"""
        SELECT value, metadata, tags FROM {self.TABLE_NAME}
        WHERE namespace = $1 AND key = $2
        AND (expires_at IS NULL OR expires_at > NOW())
        """

        row = await self._conn.fetchrow(select_sql, self._namespace, key)

        if row is None:
            return None

        value = row["value"]
        if isinstance(value, str):
            value = json.loads(value)

        metadata = row["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        return value, metadata, row["tags"] or []

    async def search_by_tags(
        self,
        tags: List[str],
        match_all: bool = False,
        limit: int = 10,
    ) -> List[Any]:
        """
        按標籤搜索記錄。

        Args:
            tags: 標籤列表
            match_all: 是否需要匹配所有標籤
            limit: 最大返回數量

        Returns:
            匹配的記錄列表
        """
        await self._ensure_table()

        if match_all:
            # 匹配所有標籤
            search_sql = f"""
            SELECT value FROM {self.TABLE_NAME}
            WHERE namespace = $1
            AND (expires_at IS NULL OR expires_at > NOW())
            AND tags @> $2
            ORDER BY updated_at DESC
            LIMIT $3
            """
        else:
            # 匹配任一標籤
            search_sql = f"""
            SELECT value FROM {self.TABLE_NAME}
            WHERE namespace = $1
            AND (expires_at IS NULL OR expires_at > NOW())
            AND tags && $2
            ORDER BY updated_at DESC
            LIMIT $3
            """

        rows = await self._conn.fetch(search_sql, self._namespace, tags, limit)

        results = []
        for row in rows:
            value = row["value"]
            if isinstance(value, str):
                value = json.loads(value)
            results.append(value)

        return results

    async def search_by_jsonb_path(
        self,
        path: str,
        value: Any,
        limit: int = 10,
    ) -> List[Any]:
        """
        按 JSONB 路徑搜索記錄。

        Args:
            path: JSONB 路徑（如 "name", "address.city"）
            value: 要匹配的值
            limit: 最大返回數量

        Returns:
            匹配的記錄列表
        """
        await self._ensure_table()

        # 構建 JSONB 路徑查詢
        path_parts = path.split(".")
        jsonb_path = "value"
        for part in path_parts:
            jsonb_path = f"{jsonb_path}->'{part}'"

        # 最後一部分使用 ->> 獲取文本
        jsonb_path = jsonb_path.rsplit("->", 1)
        jsonb_path = f"{jsonb_path[0]}->>{jsonb_path[1][1:]}"

        search_sql = f"""
        SELECT value FROM {self.TABLE_NAME}
        WHERE namespace = $1
        AND (expires_at IS NULL OR expires_at > NOW())
        AND {jsonb_path} = $2
        ORDER BY updated_at DESC
        LIMIT $3
        """

        rows = await self._conn.fetch(search_sql, self._namespace, str(value), limit)

        results = []
        for row in rows:
            val = row["value"]
            if isinstance(val, str):
                val = json.loads(val)
            results.append(val)

        return results

    async def get_keys(self, pattern: str = "%") -> List[str]:
        """
        獲取匹配模式的所有鍵。

        Args:
            pattern: SQL LIKE 模式

        Returns:
            鍵列表
        """
        await self._ensure_table()

        select_sql = f"""
        SELECT key FROM {self.TABLE_NAME}
        WHERE namespace = $1 AND key LIKE $2
        AND (expires_at IS NULL OR expires_at > NOW())
        ORDER BY key
        """

        rows = await self._conn.fetch(select_sql, self._namespace, pattern)
        return [row["key"] for row in rows]

    async def count(self) -> int:
        """
        獲取記錄總數。

        Returns:
            記錄數量
        """
        await self._ensure_table()

        count_sql = f"""
        SELECT COUNT(*) FROM {self.TABLE_NAME}
        WHERE namespace = $1
        AND (expires_at IS NULL OR expires_at > NOW())
        """

        return await self._conn.fetchval(count_sql, self._namespace) or 0

    async def clear_namespace(self) -> int:
        """
        清除命名空間下所有記錄。

        Returns:
            刪除的記錄數量
        """
        await self._ensure_table()

        delete_sql = f"""
        DELETE FROM {self.TABLE_NAME}
        WHERE namespace = $1
        """

        result = await self._conn.execute(delete_sql, self._namespace)

        deleted_count = 0
        if isinstance(result, str) and result.startswith("DELETE"):
            deleted_count = int(result.split()[-1])

        logger.info(f"Cleared namespace {self._namespace}: {deleted_count} records deleted")
        return deleted_count

    async def cleanup_expired(self) -> int:
        """
        清理過期記錄。

        Returns:
            刪除的記錄數量
        """
        await self._ensure_table()

        delete_sql = f"""
        DELETE FROM {self.TABLE_NAME}
        WHERE expires_at IS NOT NULL AND expires_at <= NOW()
        """

        result = await self._conn.execute(delete_sql)

        deleted_count = 0
        if isinstance(result, str) and result.startswith("DELETE"):
            deleted_count = int(result.split()[-1])

        logger.info(f"Cleaned up {deleted_count} expired records")
        return deleted_count

    # =========================================================================
    # Lifecycle
    # =========================================================================

    async def initialize(self) -> None:
        """初始化 PostgreSQL 連接和表。"""
        await super().initialize()
        await self._ensure_table()
        logger.info("PostgreSQL Memory Storage initialized")

    async def close(self) -> None:
        """關閉 PostgreSQL 連接。"""
        await super().close()
        # 注意：不關閉共享的 PostgreSQL 連接


# =============================================================================
# Factory Function
# =============================================================================


def create_postgres_storage(
    connection: Any,
    namespace: str = "memory",
    ttl_seconds: Optional[int] = None,
    auto_create_table: bool = True,
) -> PostgresMemoryStorage:
    """
    創建 PostgreSQL Memory Storage 實例。

    Args:
        connection: PostgreSQL 連接實例
        namespace: 命名空間前綴
        ttl_seconds: 預設 TTL（秒）
        auto_create_table: 是否自動創建表

    Returns:
        PostgresMemoryStorage 實例

    Example:
        import asyncpg

        conn = await asyncpg.connect(database="mydb")
        storage = create_postgres_storage(conn, namespace="myapp")
    """
    return PostgresMemoryStorage(
        connection=connection,
        namespace=namespace,
        ttl_seconds=ttl_seconds,
        auto_create_table=auto_create_table,
    )
