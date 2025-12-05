"""
Agent Framework Integration - Checkpoint Storage Adapters

提供 CheckpointStorage 的多種實現，支持不同的存儲後端。

實現:
    1. PostgresCheckpointStorage - PostgreSQL 持久化存儲
    2. RedisCheckpointCache - Redis 緩存層
    3. CachedCheckpointStorage - 組合存儲（緩存 + 持久化）
    4. CheckpointStorageAdapter - 通用適配器基類

Agent Framework 協議:
    CheckpointStorage Protocol 定義以下方法：
    - save_checkpoint(checkpoint: WorkflowCheckpoint) -> str
    - load_checkpoint(checkpoint_id: str) -> WorkflowCheckpoint | None
    - list_checkpoint_ids(workflow_id: str | None) -> list[str]
    - list_checkpoints(workflow_id: str | None) -> list[WorkflowCheckpoint]
    - delete_checkpoint(checkpoint_id: str) -> bool

使用範例:
    # PostgreSQL 存儲
    from src.integrations.agent_framework.checkpoint import PostgresCheckpointStorage

    storage = PostgresCheckpointStorage(session_factory)
    await storage.save_checkpoint(checkpoint)
    loaded = await storage.load_checkpoint(checkpoint_id)

    # 帶緩存的存儲
    from src.integrations.agent_framework.checkpoint import CachedCheckpointStorage

    cached_storage = CachedCheckpointStorage(
        storage=postgres_storage,
        cache=redis_cache,
    )
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol
import json
import logging
import uuid

from .exceptions import CheckpointError

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WorkflowCheckpointData:
    """
    工作流檢查點數據類。

    與 Agent Framework 的 WorkflowCheckpoint 保持相容，
    但添加了額外的 IPA Platform 特定字段。

    Attributes:
        checkpoint_id: 檢查點唯一標識符
        workflow_id: 工作流 ID
        timestamp: ISO 8601 格式的時間戳
        messages: 執行器之間交換的消息
        shared_state: 共享狀態數據
        iteration_count: 創建檢查點時的迭代計數
        metadata: 額外的元數據
        version: 檢查點格式版本
    """

    checkpoint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Core workflow state
    messages: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    shared_state: Dict[str, Any] = field(default_factory=dict)
    pending_request_info_events: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Runtime state
    iteration_count: int = 0

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典。"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowCheckpointData":
        """從字典創建實例。"""
        return cls(**data)

    def to_agent_framework_checkpoint(self):
        """
        轉換為 Agent Framework WorkflowCheckpoint。

        Returns:
            agent_framework.WorkflowCheckpoint 實例
        """
        try:
            from agent_framework import WorkflowCheckpoint
            return WorkflowCheckpoint(
                checkpoint_id=self.checkpoint_id,
                workflow_id=self.workflow_id,
                timestamp=self.timestamp,
                messages=self.messages,
                shared_state=self.shared_state,
                pending_request_info_events=self.pending_request_info_events,
                iteration_count=self.iteration_count,
                metadata=self.metadata,
                version=self.version,
            )
        except ImportError:
            # 如果 agent_framework 不可用，返回 None
            return None

    @classmethod
    def from_agent_framework_checkpoint(cls, checkpoint) -> "WorkflowCheckpointData":
        """
        從 Agent Framework WorkflowCheckpoint 創建實例。

        Args:
            checkpoint: agent_framework.WorkflowCheckpoint 實例

        Returns:
            WorkflowCheckpointData 實例
        """
        return cls(
            checkpoint_id=checkpoint.checkpoint_id,
            workflow_id=checkpoint.workflow_id,
            timestamp=checkpoint.timestamp,
            messages=checkpoint.messages,
            shared_state=checkpoint.shared_state,
            pending_request_info_events=getattr(checkpoint, 'pending_request_info_events', {}),
            iteration_count=checkpoint.iteration_count,
            metadata=checkpoint.metadata,
            version=checkpoint.version,
        )


class CheckpointStorageAdapter(ABC):
    """
    檢查點存儲適配器的抽象基類。

    定義所有檢查點存儲實現必須提供的介面。
    此介面與 Agent Framework 的 CheckpointStorage Protocol 相容。
    """

    @abstractmethod
    async def save_checkpoint(self, checkpoint: Any) -> str:
        """
        保存檢查點。

        Args:
            checkpoint: WorkflowCheckpoint 或 WorkflowCheckpointData 實例

        Returns:
            檢查點 ID

        Raises:
            CheckpointError: 保存失敗時
        """
        pass

    @abstractmethod
    async def load_checkpoint(self, checkpoint_id: str) -> Optional[Any]:
        """
        載入檢查點。

        Args:
            checkpoint_id: 檢查點 ID

        Returns:
            WorkflowCheckpoint 實例，如果不存在則返回 None

        Raises:
            CheckpointError: 載入失敗時
        """
        pass

    @abstractmethod
    async def list_checkpoint_ids(self, workflow_id: Optional[str] = None) -> List[str]:
        """
        列出檢查點 ID。

        Args:
            workflow_id: 可選的工作流 ID 過濾器

        Returns:
            檢查點 ID 列表
        """
        pass

    @abstractmethod
    async def list_checkpoints(self, workflow_id: Optional[str] = None) -> List[Any]:
        """
        列出檢查點。

        Args:
            workflow_id: 可選的工作流 ID 過濾器

        Returns:
            WorkflowCheckpoint 列表
        """
        pass

    @abstractmethod
    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        刪除檢查點。

        Args:
            checkpoint_id: 檢查點 ID

        Returns:
            是否成功刪除

        Raises:
            CheckpointError: 刪除失敗時
        """
        pass


class PostgresCheckpointStorage(CheckpointStorageAdapter):
    """
    PostgreSQL 檢查點存儲實現。

    使用 PostgreSQL 作為持久化存儲後端。
    適合需要可靠持久化和事務支持的場景。

    數據庫表結構:
        CREATE TABLE workflow_checkpoints (
            checkpoint_id VARCHAR(36) PRIMARY KEY,
            workflow_id VARCHAR(255) NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            messages JSONB NOT NULL DEFAULT '{}',
            shared_state JSONB NOT NULL DEFAULT '{}',
            pending_request_info_events JSONB NOT NULL DEFAULT '{}',
            iteration_count INTEGER NOT NULL DEFAULT 0,
            metadata JSONB NOT NULL DEFAULT '{}',
            version VARCHAR(10) NOT NULL DEFAULT '1.0',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        CREATE INDEX idx_checkpoint_workflow_id ON workflow_checkpoints(workflow_id);
        CREATE INDEX idx_checkpoint_timestamp ON workflow_checkpoints(timestamp);

    Attributes:
        _session_factory: SQLAlchemy 異步會話工廠

    Example:
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

        engine = create_async_engine("postgresql+asyncpg://...")
        session_factory = async_sessionmaker(engine)

        storage = PostgresCheckpointStorage(session_factory)
        await storage.save_checkpoint(checkpoint)
    """

    def __init__(self, session_factory):
        """
        初始化 PostgreSQL 存儲。

        Args:
            session_factory: SQLAlchemy 異步會話工廠
        """
        self._session_factory = session_factory
        self._logger = logging.getLogger(f"{__name__}.PostgresCheckpointStorage")

    async def save_checkpoint(self, checkpoint: Any) -> str:
        """保存檢查點到 PostgreSQL。"""
        try:
            # 轉換為內部數據格式
            if hasattr(checkpoint, 'to_dict'):
                data = checkpoint.to_dict()
            else:
                data = WorkflowCheckpointData.from_agent_framework_checkpoint(checkpoint).to_dict()

            checkpoint_id = data.get('checkpoint_id', str(uuid.uuid4()))

            async with self._session_factory() as session:
                # 使用原生 SQL 插入或更新
                query = """
                    INSERT INTO workflow_checkpoints
                    (checkpoint_id, workflow_id, timestamp, messages, shared_state,
                     pending_request_info_events, iteration_count, metadata, version)
                    VALUES (:checkpoint_id, :workflow_id, :timestamp, :messages, :shared_state,
                            :pending_request_info_events, :iteration_count, :metadata, :version)
                    ON CONFLICT (checkpoint_id)
                    DO UPDATE SET
                        workflow_id = EXCLUDED.workflow_id,
                        timestamp = EXCLUDED.timestamp,
                        messages = EXCLUDED.messages,
                        shared_state = EXCLUDED.shared_state,
                        pending_request_info_events = EXCLUDED.pending_request_info_events,
                        iteration_count = EXCLUDED.iteration_count,
                        metadata = EXCLUDED.metadata,
                        version = EXCLUDED.version,
                        updated_at = NOW()
                """
                from sqlalchemy import text
                await session.execute(
                    text(query),
                    {
                        'checkpoint_id': checkpoint_id,
                        'workflow_id': data.get('workflow_id', ''),
                        'timestamp': data.get('timestamp', datetime.now(timezone.utc).isoformat()),
                        'messages': json.dumps(data.get('messages', {})),
                        'shared_state': json.dumps(data.get('shared_state', {})),
                        'pending_request_info_events': json.dumps(data.get('pending_request_info_events', {})),
                        'iteration_count': data.get('iteration_count', 0),
                        'metadata': json.dumps(data.get('metadata', {})),
                        'version': data.get('version', '1.0'),
                    }
                )
                await session.commit()

            self._logger.info(f"Saved checkpoint {checkpoint_id} to PostgreSQL")
            return checkpoint_id

        except Exception as e:
            raise CheckpointError(
                f"Failed to save checkpoint: {e}",
                checkpoint_id=checkpoint.checkpoint_id if hasattr(checkpoint, 'checkpoint_id') else None,
                operation="save",
                original_error=e,
            )

    async def load_checkpoint(self, checkpoint_id: str) -> Optional[Any]:
        """從 PostgreSQL 載入檢查點。"""
        try:
            async with self._session_factory() as session:
                from sqlalchemy import text
                query = """
                    SELECT checkpoint_id, workflow_id, timestamp, messages, shared_state,
                           pending_request_info_events, iteration_count, metadata, version
                    FROM workflow_checkpoints
                    WHERE checkpoint_id = :checkpoint_id
                """
                result = await session.execute(text(query), {'checkpoint_id': checkpoint_id})
                row = result.fetchone()

                if not row:
                    return None

                # 構建檢查點數據
                checkpoint_data = WorkflowCheckpointData(
                    checkpoint_id=row[0],
                    workflow_id=row[1],
                    timestamp=row[2].isoformat() if hasattr(row[2], 'isoformat') else row[2],
                    messages=row[3] if isinstance(row[3], dict) else json.loads(row[3]),
                    shared_state=row[4] if isinstance(row[4], dict) else json.loads(row[4]),
                    pending_request_info_events=row[5] if isinstance(row[5], dict) else json.loads(row[5]),
                    iteration_count=row[6],
                    metadata=row[7] if isinstance(row[7], dict) else json.loads(row[7]),
                    version=row[8],
                )

                self._logger.info(f"Loaded checkpoint {checkpoint_id} from PostgreSQL")

                # 嘗試返回 Agent Framework 類型
                af_checkpoint = checkpoint_data.to_agent_framework_checkpoint()
                return af_checkpoint if af_checkpoint else checkpoint_data

        except Exception as e:
            raise CheckpointError(
                f"Failed to load checkpoint: {e}",
                checkpoint_id=checkpoint_id,
                operation="load",
                original_error=e,
            )

    async def list_checkpoint_ids(self, workflow_id: Optional[str] = None) -> List[str]:
        """列出檢查點 ID。"""
        try:
            async with self._session_factory() as session:
                from sqlalchemy import text

                if workflow_id:
                    query = """
                        SELECT checkpoint_id FROM workflow_checkpoints
                        WHERE workflow_id = :workflow_id
                        ORDER BY timestamp DESC
                    """
                    result = await session.execute(text(query), {'workflow_id': workflow_id})
                else:
                    query = """
                        SELECT checkpoint_id FROM workflow_checkpoints
                        ORDER BY timestamp DESC
                    """
                    result = await session.execute(text(query))

                return [row[0] for row in result.fetchall()]

        except Exception as e:
            raise CheckpointError(
                f"Failed to list checkpoint IDs: {e}",
                operation="list",
                original_error=e,
            )

    async def list_checkpoints(self, workflow_id: Optional[str] = None) -> List[Any]:
        """列出所有檢查點。"""
        checkpoint_ids = await self.list_checkpoint_ids(workflow_id)
        checkpoints = []
        for cp_id in checkpoint_ids:
            checkpoint = await self.load_checkpoint(cp_id)
            if checkpoint:
                checkpoints.append(checkpoint)
        return checkpoints

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """刪除檢查點。"""
        try:
            async with self._session_factory() as session:
                from sqlalchemy import text
                query = "DELETE FROM workflow_checkpoints WHERE checkpoint_id = :checkpoint_id"
                result = await session.execute(text(query), {'checkpoint_id': checkpoint_id})
                await session.commit()

                deleted = result.rowcount > 0
                if deleted:
                    self._logger.info(f"Deleted checkpoint {checkpoint_id} from PostgreSQL")
                return deleted

        except Exception as e:
            raise CheckpointError(
                f"Failed to delete checkpoint: {e}",
                checkpoint_id=checkpoint_id,
                operation="delete",
                original_error=e,
            )


class RedisCheckpointCache:
    """
    Redis 檢查點緩存層。

    提供快速的檢查點讀取緩存，用於減少資料庫訪問。

    Attributes:
        _redis: Redis 客戶端實例
        _ttl: 緩存過期時間（秒）
        _key_prefix: Redis 鍵前綴

    Example:
        import redis.asyncio as redis

        redis_client = redis.from_url("redis://localhost")
        cache = RedisCheckpointCache(redis_client, ttl_seconds=3600)

        await cache.set(checkpoint_id, checkpoint_data)
        cached = await cache.get(checkpoint_id)
    """

    def __init__(
        self,
        redis_client,
        ttl_seconds: int = 3600,
        key_prefix: str = "checkpoint:",
    ):
        """
        初始化 Redis 緩存。

        Args:
            redis_client: Redis 異步客戶端
            ttl_seconds: 緩存過期時間（秒），默認 1 小時
            key_prefix: Redis 鍵前綴
        """
        self._redis = redis_client
        self._ttl = ttl_seconds
        self._key_prefix = key_prefix
        self._logger = logging.getLogger(f"{__name__}.RedisCheckpointCache")

    def _make_key(self, checkpoint_id: str) -> str:
        """生成 Redis 鍵。"""
        return f"{self._key_prefix}{checkpoint_id}"

    async def get(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        從緩存獲取檢查點數據。

        Args:
            checkpoint_id: 檢查點 ID

        Returns:
            檢查點數據字典，如果不存在則返回 None
        """
        try:
            key = self._make_key(checkpoint_id)
            data = await self._redis.get(key)

            if data:
                self._logger.debug(f"Cache hit for checkpoint {checkpoint_id}")
                return json.loads(data)

            self._logger.debug(f"Cache miss for checkpoint {checkpoint_id}")
            return None

        except Exception as e:
            self._logger.warning(f"Failed to get from cache: {e}")
            return None

    async def set(self, checkpoint_id: str, data: Dict[str, Any]) -> None:
        """
        將檢查點數據存入緩存。

        Args:
            checkpoint_id: 檢查點 ID
            data: 檢查點數據字典
        """
        try:
            key = self._make_key(checkpoint_id)
            await self._redis.setex(key, self._ttl, json.dumps(data))
            self._logger.debug(f"Cached checkpoint {checkpoint_id} with TTL {self._ttl}s")
        except Exception as e:
            self._logger.warning(f"Failed to set cache: {e}")

    async def delete(self, checkpoint_id: str) -> None:
        """
        從緩存刪除檢查點。

        Args:
            checkpoint_id: 檢查點 ID
        """
        try:
            key = self._make_key(checkpoint_id)
            await self._redis.delete(key)
            self._logger.debug(f"Deleted checkpoint {checkpoint_id} from cache")
        except Exception as e:
            self._logger.warning(f"Failed to delete from cache: {e}")

    async def clear_workflow(self, workflow_id: str) -> int:
        """
        清除特定工作流的所有緩存檢查點。

        注意：此方法需要額外的索引支持，目前使用 SCAN 遍歷。

        Args:
            workflow_id: 工作流 ID

        Returns:
            刪除的緩存數量
        """
        # 此實現需要維護工作流到檢查點的映射
        # 簡化版本：不支持按工作流清除
        self._logger.warning("clear_workflow not fully implemented")
        return 0


class CachedCheckpointStorage(CheckpointStorageAdapter):
    """
    帶緩存的檢查點存儲。

    組合 PostgreSQL 存儲和 Redis 緩存，提供：
    - 快速讀取（緩存優先）
    - 可靠持久化（寫入同時更新存儲和緩存）
    - 一致性保證（刪除同時清理緩存和存儲）

    讀取策略:
        1. 先嘗試從 Redis 緩存讀取
        2. 緩存未命中則從 PostgreSQL 讀取
        3. 讀取成功後回填緩存

    寫入策略:
        1. 先寫入 PostgreSQL
        2. 成功後更新 Redis 緩存

    Example:
        storage = CachedCheckpointStorage(
            storage=postgres_storage,
            cache=redis_cache,
        )

        # 使用方式與普通存儲相同
        await storage.save_checkpoint(checkpoint)
        loaded = await storage.load_checkpoint(checkpoint_id)
    """

    def __init__(
        self,
        storage: PostgresCheckpointStorage,
        cache: RedisCheckpointCache,
    ):
        """
        初始化帶緩存的存儲。

        Args:
            storage: PostgreSQL 存儲實例
            cache: Redis 緩存實例
        """
        self._storage = storage
        self._cache = cache
        self._logger = logging.getLogger(f"{__name__}.CachedCheckpointStorage")

    async def save_checkpoint(self, checkpoint: Any) -> str:
        """保存檢查點（存儲 + 緩存）。"""
        # 先保存到持久存儲
        checkpoint_id = await self._storage.save_checkpoint(checkpoint)

        # 更新緩存
        if hasattr(checkpoint, 'to_dict'):
            data = checkpoint.to_dict()
        else:
            data = WorkflowCheckpointData.from_agent_framework_checkpoint(checkpoint).to_dict()

        await self._cache.set(checkpoint_id, data)

        return checkpoint_id

    async def load_checkpoint(self, checkpoint_id: str) -> Optional[Any]:
        """載入檢查點（緩存優先）。"""
        # 先嘗試緩存
        cached_data = await self._cache.get(checkpoint_id)
        if cached_data:
            checkpoint_data = WorkflowCheckpointData.from_dict(cached_data)
            af_checkpoint = checkpoint_data.to_agent_framework_checkpoint()
            return af_checkpoint if af_checkpoint else checkpoint_data

        # 從存儲載入
        checkpoint = await self._storage.load_checkpoint(checkpoint_id)
        if checkpoint:
            # 回填緩存
            if hasattr(checkpoint, 'to_dict'):
                await self._cache.set(checkpoint_id, checkpoint.to_dict())
            else:
                await self._cache.set(
                    checkpoint_id,
                    WorkflowCheckpointData.from_agent_framework_checkpoint(checkpoint).to_dict()
                )

        return checkpoint

    async def list_checkpoint_ids(self, workflow_id: Optional[str] = None) -> List[str]:
        """列出檢查點 ID（直接從存儲）。"""
        return await self._storage.list_checkpoint_ids(workflow_id)

    async def list_checkpoints(self, workflow_id: Optional[str] = None) -> List[Any]:
        """列出所有檢查點。"""
        return await self._storage.list_checkpoints(workflow_id)

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """刪除檢查點（存儲 + 緩存）。"""
        # 先刪除緩存
        await self._cache.delete(checkpoint_id)

        # 再刪除存儲
        return await self._storage.delete_checkpoint(checkpoint_id)


class InMemoryCheckpointStorage(CheckpointStorageAdapter):
    """
    內存檢查點存儲（用於測試和開發）。

    與 Agent Framework 的 InMemoryCheckpointStorage 相容。

    Example:
        storage = InMemoryCheckpointStorage()
        await storage.save_checkpoint(checkpoint)
        await storage.load_checkpoint(checkpoint_id)
    """

    def __init__(self):
        """初始化內存存儲。"""
        self._checkpoints: Dict[str, Any] = {}
        self._logger = logging.getLogger(f"{__name__}.InMemoryCheckpointStorage")

    async def save_checkpoint(self, checkpoint: Any) -> str:
        """保存檢查點到內存。"""
        checkpoint_id = checkpoint.checkpoint_id
        self._checkpoints[checkpoint_id] = checkpoint
        self._logger.debug(f"Saved checkpoint {checkpoint_id} to memory")
        return checkpoint_id

    async def load_checkpoint(self, checkpoint_id: str) -> Optional[Any]:
        """從內存載入檢查點。"""
        checkpoint = self._checkpoints.get(checkpoint_id)
        if checkpoint:
            self._logger.debug(f"Loaded checkpoint {checkpoint_id} from memory")
        return checkpoint

    async def list_checkpoint_ids(self, workflow_id: Optional[str] = None) -> List[str]:
        """列出檢查點 ID。"""
        if workflow_id is None:
            return list(self._checkpoints.keys())
        return [
            cp.checkpoint_id
            for cp in self._checkpoints.values()
            if cp.workflow_id == workflow_id
        ]

    async def list_checkpoints(self, workflow_id: Optional[str] = None) -> List[Any]:
        """列出所有檢查點。"""
        if workflow_id is None:
            return list(self._checkpoints.values())
        return [cp for cp in self._checkpoints.values() if cp.workflow_id == workflow_id]

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """刪除檢查點。"""
        if checkpoint_id in self._checkpoints:
            del self._checkpoints[checkpoint_id]
            self._logger.debug(f"Deleted checkpoint {checkpoint_id} from memory")
            return True
        return False

    def clear(self) -> None:
        """清空所有檢查點（測試用）。"""
        self._checkpoints.clear()
        self._logger.debug("Cleared all checkpoints from memory")
