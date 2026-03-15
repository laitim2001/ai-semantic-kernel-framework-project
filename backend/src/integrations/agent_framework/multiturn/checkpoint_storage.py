# =============================================================================
# IPA Platform - Checkpoint Storage Implementations
# =============================================================================
# Sprint 24: S24-3 Multi-turn 遷移到 Checkpoint (8 points)
#
# 自定義 Checkpoint 存儲實現，擴展官方 CheckpointStorage 接口。
#
# 官方 API 使用說明:
#   - 內存存儲: 直接使用官方 InMemoryCheckpointStorage
#   - 持久化存儲: 以下擴展類使用 IPA 自定義接口（save/load/delete）
#
# IPA 擴展存儲後端（非官方 API）:
#   - RedisCheckpointStorage: Redis 存儲（IPA 自定義接口）
#   - PostgresCheckpointStorage: PostgreSQL 存儲（IPA 自定義接口）
#   - FileCheckpointStorage: 文件系統存儲（IPA 自定義接口）
#
# 注意: 這些擴展存儲使用 save/load/delete 方法，不是官方的
#       save_checkpoint/load_checkpoint/delete_checkpoint 方法。
#       如需符合官方 API，請使用官方 InMemoryCheckpointStorage 或
#       FileCheckpointStorage（from agent_framework）。
# =============================================================================

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import logging

# 官方 Agent Framework API
from agent_framework import CheckpointStorage, InMemoryCheckpointStorage

logger = logging.getLogger(__name__)


# =============================================================================
# 抽象基類
# =============================================================================

class BaseCheckpointStorage(CheckpointStorage, ABC):
    """Checkpoint 存儲抽象基類。

    提供通用的存儲方法和配置。
    """

    def __init__(
        self,
        namespace: str = "multiturn",
        ttl_seconds: int = 86400,  # 24 小時
    ):
        """初始化存儲。

        Args:
            namespace: 命名空間，用於隔離不同應用的數據
            ttl_seconds: 數據過期時間（秒）
        """
        self._namespace = namespace
        self._ttl_seconds = ttl_seconds

    def _make_key(self, session_id: str) -> str:
        """生成存儲鍵。"""
        return f"{self._namespace}:checkpoint:{session_id}"

    def _serialize(self, state: Any) -> str:
        """序列化狀態。"""
        return json.dumps(state, default=str, ensure_ascii=False)

    def _deserialize(self, data: str) -> Any:
        """反序列化狀態。"""
        return json.loads(data)


# =============================================================================
# Redis 實現
# =============================================================================

class RedisCheckpointStorage(BaseCheckpointStorage):
    """使用 Redis 的 Checkpoint 存儲。

    特點:
    - 高性能讀寫
    - 自動過期
    - 分布式支持

    Example:
        ```python
        import redis.asyncio as redis

        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        storage = RedisCheckpointStorage(redis_client)

        await storage.save("session-1", {"history": [...], "context": {...}})
        state = await storage.load("session-1")
        ```
    """

    def __init__(
        self,
        redis_client: Any,
        namespace: str = "multiturn",
        ttl_seconds: int = 86400,
    ):
        """初始化 Redis 存儲。

        Args:
            redis_client: Redis 客戶端（支持 async）
            namespace: 命名空間
            ttl_seconds: 過期時間
        """
        super().__init__(namespace=namespace, ttl_seconds=ttl_seconds)
        self._redis = redis_client

    async def save(self, session_id: str, state: Any) -> None:
        """保存狀態到 Redis。

        Args:
            session_id: 會話 ID
            state: 要保存的狀態
        """
        key = self._make_key(session_id)
        data = self._serialize(state)

        await self._redis.set(key, data, ex=self._ttl_seconds)
        logger.debug(f"Redis 保存 checkpoint: {session_id}")

    async def load(self, session_id: str) -> Optional[Any]:
        """從 Redis 載入狀態。

        Args:
            session_id: 會話 ID

        Returns:
            狀態數據，如果不存在則返回 None
        """
        key = self._make_key(session_id)
        data = await self._redis.get(key)

        if data:
            logger.debug(f"Redis 載入 checkpoint: {session_id}")
            return self._deserialize(data)

        return None

    async def delete(self, session_id: str) -> bool:
        """從 Redis 刪除狀態。

        Args:
            session_id: 會話 ID

        Returns:
            是否成功刪除
        """
        key = self._make_key(session_id)
        result = await self._redis.delete(key)

        if result > 0:
            logger.debug(f"Redis 刪除 checkpoint: {session_id}")
            return True
        return False

    async def list(self, pattern: str = "*") -> List[str]:
        """列出匹配的會話 ID。

        Args:
            pattern: 匹配模式

        Returns:
            會話 ID 列表
        """
        key_pattern = f"{self._namespace}:checkpoint:{pattern}"
        keys = await self._redis.keys(key_pattern)

        # 提取會話 ID
        prefix_len = len(f"{self._namespace}:checkpoint:")
        return [key.decode()[prefix_len:] if isinstance(key, bytes) else key[prefix_len:] for key in keys]

    async def extend_ttl(self, session_id: str, additional_seconds: int) -> bool:
        """延長過期時間。

        Args:
            session_id: 會話 ID
            additional_seconds: 額外的秒數

        Returns:
            是否成功
        """
        key = self._make_key(session_id)
        ttl = await self._redis.ttl(key)

        if ttl > 0:
            new_ttl = ttl + additional_seconds
            await self._redis.expire(key, new_ttl)
            return True
        return False


# =============================================================================
# PostgreSQL 實現
# =============================================================================

class PostgresCheckpointStorage(BaseCheckpointStorage):
    """使用 PostgreSQL 的 Checkpoint 存儲。

    特點:
    - 持久化存儲
    - 事務支持
    - 複雜查詢能力

    需要的表結構:
    ```sql
    CREATE TABLE checkpoints (
        session_id VARCHAR(255) PRIMARY KEY,
        namespace VARCHAR(255) NOT NULL,
        state JSONB NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP
    );
    CREATE INDEX idx_checkpoints_namespace ON checkpoints(namespace);
    CREATE INDEX idx_checkpoints_expires ON checkpoints(expires_at);
    ```
    """

    def __init__(
        self,
        db_pool: Any,
        table_name: str = "checkpoints",
        namespace: str = "multiturn",
        ttl_seconds: int = 86400,
    ):
        """初始化 PostgreSQL 存儲。

        Args:
            db_pool: 數據庫連接池（asyncpg）
            table_name: 表名
            namespace: 命名空間
            ttl_seconds: 過期時間
        """
        super().__init__(namespace=namespace, ttl_seconds=ttl_seconds)
        self._pool = db_pool
        self._table = table_name

    async def save(self, session_id: str, state: Any) -> None:
        """保存狀態到 PostgreSQL。"""
        expires_at = datetime.utcnow() + timedelta(seconds=self._ttl_seconds)

        query = f"""
        INSERT INTO {self._table} (session_id, namespace, state, updated_at, expires_at)
        VALUES ($1, $2, $3, CURRENT_TIMESTAMP, $4)
        ON CONFLICT (session_id)
        DO UPDATE SET state = $3, updated_at = CURRENT_TIMESTAMP, expires_at = $4
        """

        async with self._pool.acquire() as conn:
            await conn.execute(
                query,
                session_id,
                self._namespace,
                json.dumps(state, default=str),
                expires_at,
            )

        logger.debug(f"PostgreSQL 保存 checkpoint: {session_id}")

    async def load(self, session_id: str) -> Optional[Any]:
        """從 PostgreSQL 載入狀態。"""
        query = f"""
        SELECT state FROM {self._table}
        WHERE session_id = $1
          AND namespace = $2
          AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
        """

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, session_id, self._namespace)

        if row:
            logger.debug(f"PostgreSQL 載入 checkpoint: {session_id}")
            return json.loads(row["state"])

        return None

    async def delete(self, session_id: str) -> bool:
        """從 PostgreSQL 刪除狀態。"""
        query = f"""
        DELETE FROM {self._table}
        WHERE session_id = $1 AND namespace = $2
        """

        async with self._pool.acquire() as conn:
            result = await conn.execute(query, session_id, self._namespace)

        deleted = result.endswith("1") if isinstance(result, str) else False
        if deleted:
            logger.debug(f"PostgreSQL 刪除 checkpoint: {session_id}")
        return deleted

    async def list(self, pattern: str = "*") -> List[str]:
        """列出匹配的會話 ID。"""
        if pattern == "*":
            query = f"""
            SELECT session_id FROM {self._table}
            WHERE namespace = $1
              AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            ORDER BY updated_at DESC
            """
            params = [self._namespace]
        else:
            query = f"""
            SELECT session_id FROM {self._table}
            WHERE namespace = $1
              AND session_id LIKE $2
              AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            ORDER BY updated_at DESC
            """
            params = [self._namespace, pattern.replace("*", "%")]

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [row["session_id"] for row in rows]

    async def cleanup_expired(self) -> int:
        """清理過期的 checkpoint。

        Returns:
            清理的記錄數
        """
        query = f"""
        DELETE FROM {self._table}
        WHERE expires_at < CURRENT_TIMESTAMP
        """

        async with self._pool.acquire() as conn:
            result = await conn.execute(query)

        # 解析刪除的行數
        try:
            count = int(result.split()[-1])
        except (ValueError, IndexError):
            count = 0

        if count > 0:
            logger.info(f"PostgreSQL 清理 {count} 個過期 checkpoint")
        return count


# =============================================================================
# 文件系統實現
# =============================================================================

class FileCheckpointStorage(BaseCheckpointStorage):
    """使用文件系統的 Checkpoint 存儲。

    特點:
    - 無需額外依賴
    - 適合開發和測試
    - 簡單易用

    Example:
        ```python
        storage = FileCheckpointStorage(base_path="/tmp/checkpoints")
        await storage.save("session-1", {"history": [...]})
        ```
    """

    def __init__(
        self,
        base_path: str = "/tmp/checkpoints",
        namespace: str = "multiturn",
        ttl_seconds: int = 86400,
    ):
        """初始化文件存儲。

        Args:
            base_path: 基礎目錄路徑
            namespace: 命名空間
            ttl_seconds: 過期時間
        """
        super().__init__(namespace=namespace, ttl_seconds=ttl_seconds)
        self._base_path = Path(base_path) / namespace
        self._base_path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, session_id: str) -> Path:
        """獲取文件路徑。"""
        # 使用會話 ID 作為文件名，添加 .json 擴展名
        safe_id = session_id.replace("/", "_").replace("\\", "_")
        return self._base_path / f"{safe_id}.json"

    async def save(self, session_id: str, state: Any) -> None:
        """保存狀態到文件。"""
        file_path = self._get_file_path(session_id)

        data = {
            "session_id": session_id,
            "state": state,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(seconds=self._ttl_seconds)).isoformat(),
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, default=str, ensure_ascii=False, indent=2)

        logger.debug(f"文件系統保存 checkpoint: {session_id}")

    async def load(self, session_id: str) -> Optional[Any]:
        """從文件載入狀態。"""
        file_path = self._get_file_path(session_id)

        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 檢查是否過期
            expires_at = datetime.fromisoformat(data.get("expires_at", ""))
            if expires_at < datetime.utcnow():
                # 已過期，刪除文件
                file_path.unlink()
                return None

            logger.debug(f"文件系統載入 checkpoint: {session_id}")
            return data.get("state")

        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    async def delete(self, session_id: str) -> bool:
        """從文件系統刪除狀態。"""
        file_path = self._get_file_path(session_id)

        if file_path.exists():
            file_path.unlink()
            logger.debug(f"文件系統刪除 checkpoint: {session_id}")
            return True
        return False

    async def list(self, pattern: str = "*") -> List[str]:
        """列出匹配的會話 ID。"""
        if pattern == "*":
            files = self._base_path.glob("*.json")
        else:
            files = self._base_path.glob(f"{pattern.replace('*', '*')}.json")

        session_ids = []
        for file_path in files:
            session_id = file_path.stem
            # 檢查是否過期
            state = await self.load(session_id)
            if state is not None:
                session_ids.append(session_id)

        return session_ids

    async def cleanup_expired(self) -> int:
        """清理過期的 checkpoint。"""
        count = 0
        for file_path in self._base_path.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                expires_at = datetime.fromisoformat(data.get("expires_at", ""))
                if expires_at < datetime.utcnow():
                    file_path.unlink()
                    count += 1
            except (json.JSONDecodeError, KeyError, ValueError):
                pass

        if count > 0:
            logger.info(f"文件系統清理 {count} 個過期 checkpoint")
        return count


# =============================================================================
# 注意：內存存儲請使用官方 InMemoryCheckpointStorage
# =============================================================================
# 官方已提供 InMemoryCheckpointStorage，請直接使用：
#
# from agent_framework import InMemoryCheckpointStorage
# storage = InMemoryCheckpointStorage()
#
# 官方 API 方法：
#   - save_checkpoint(checkpoint: WorkflowCheckpoint) -> str
#   - load_checkpoint(checkpoint_id: str) -> WorkflowCheckpoint | None
#   - delete_checkpoint(checkpoint_id: str) -> bool
#   - list_checkpoint_ids(workflow_id: str | None) -> list[str]
#   - list_checkpoints(workflow_id: str | None) -> list[WorkflowCheckpoint]
# =============================================================================
