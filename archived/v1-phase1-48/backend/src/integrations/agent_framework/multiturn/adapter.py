# =============================================================================
# IPA Platform - Multi-turn Adapter
# =============================================================================
# Sprint 24: S24-3 Multi-turn 遷移到 Checkpoint (8 points)
#
# 多輪對話適配器，整合官方 CheckpointStorage 與 Phase 2 會話管理。
#
# 官方 API 使用:
#   - CheckpointStorage: 官方狀態持久化 Protocol
#   - InMemoryCheckpointStorage: 官方內存存儲實現
#   - WorkflowCheckpoint: 官方檢查點數據類
#
# Phase 2 擴展:
#   - SessionManager: 會話生命週期管理
#   - TurnTracker: 輪次追蹤
#   - ContextManager: 上下文作用域管理
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
import logging
import uuid

# 官方 Agent Framework API
from agent_framework import (
    CheckpointStorage,
    InMemoryCheckpointStorage,
    WorkflowCheckpoint,
)

logger = logging.getLogger(__name__)


# =============================================================================
# 枚舉類型
# =============================================================================

class SessionState(str, Enum):
    """會話狀態。"""

    CREATED = "created"          # 已創建，尚未開始
    ACTIVE = "active"            # 活躍中
    PAUSED = "paused"            # 已暫停
    WAITING = "waiting"          # 等待用戶輸入
    COMPLETED = "completed"      # 已完成
    EXPIRED = "expired"          # 已過期
    ERROR = "error"              # 錯誤狀態


class MessageRole(str, Enum):
    """消息角色。"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    FUNCTION = "function"


class ContextScope(str, Enum):
    """上下文作用域。"""

    TURN = "turn"            # 單輪有效
    SESSION = "session"      # 會話有效
    PERSISTENT = "persistent"  # 持久化


# =============================================================================
# 數據類
# =============================================================================

@dataclass
class Message:
    """對話消息。"""

    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典。"""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """從字典創建。"""
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class TurnResult:
    """輪次結果。"""

    turn_id: str
    session_id: str
    input_message: Message
    output_message: Optional[Message] = None
    context: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典。"""
        return {
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "input_message": self.input_message.to_dict(),
            "output_message": self.output_message.to_dict() if self.output_message else None,
            "context": self.context,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class SessionInfo:
    """會話信息。"""

    session_id: str
    state: SessionState
    created_at: datetime
    updated_at: datetime
    turn_count: int = 0
    total_tokens: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典。"""
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "turn_count": self.turn_count,
            "total_tokens": self.total_tokens,
            "metadata": self.metadata,
        }


@dataclass
class MultiTurnConfig:
    """多輪對話配置。"""

    max_turns: int = 100                    # 最大輪次
    max_history_length: int = 50            # 最大歷史長度
    session_timeout_seconds: int = 3600     # 會話超時時間
    auto_save: bool = True                  # 自動保存
    save_interval_turns: int = 5            # 保存間隔（輪次）
    context_window_size: int = 10           # 上下文窗口大小
    enable_summarization: bool = True       # 啟用摘要
    summarization_threshold: int = 20       # 摘要閾值


# =============================================================================
# 上下文管理器
# =============================================================================

class ContextManager:
    """上下文管理器。

    管理不同作用域的上下文變量。
    """

    def __init__(self):
        """初始化上下文管理器。"""
        self._contexts: Dict[ContextScope, Dict[str, Any]] = {
            ContextScope.TURN: {},
            ContextScope.SESSION: {},
            ContextScope.PERSISTENT: {},
        }

    def set(self, key: str, value: Any, scope: ContextScope = ContextScope.SESSION) -> None:
        """設置上下文變量。"""
        self._contexts[scope][key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """獲取上下文變量（按作用域優先級）。"""
        # 從最局部到最全局搜索
        for scope in [ContextScope.TURN, ContextScope.SESSION, ContextScope.PERSISTENT]:
            if key in self._contexts[scope]:
                return self._contexts[scope][key]
        return default

    def get_all(self, scope: Optional[ContextScope] = None) -> Dict[str, Any]:
        """獲取所有上下文變量。"""
        if scope:
            return dict(self._contexts[scope])

        # 合併所有作用域
        merged = {}
        for s in [ContextScope.PERSISTENT, ContextScope.SESSION, ContextScope.TURN]:
            merged.update(self._contexts[s])
        return merged

    def clear_turn(self) -> None:
        """清除輪次上下文。"""
        self._contexts[ContextScope.TURN] = {}

    def clear_session(self) -> None:
        """清除會話上下文。"""
        self._contexts[ContextScope.SESSION] = {}
        self._contexts[ContextScope.TURN] = {}

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典。"""
        return {
            scope.value: dict(context)
            for scope, context in self._contexts.items()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextManager":
        """從字典創建。"""
        manager = cls()
        for scope_str, context in data.items():
            scope = ContextScope(scope_str)
            manager._contexts[scope] = dict(context)
        return manager


# =============================================================================
# 輪次追蹤器
# =============================================================================

class TurnTracker:
    """輪次追蹤器。

    追蹤對話輪次和歷史。
    """

    def __init__(self, max_history: int = 50):
        """初始化輪次追蹤器。"""
        self._max_history = max_history
        self._history: List[Message] = []
        self._turn_results: List[TurnResult] = []
        self._current_turn: int = 0

    @property
    def current_turn(self) -> int:
        """獲取當前輪次。"""
        return self._current_turn

    @property
    def history(self) -> List[Message]:
        """獲取歷史消息。"""
        return list(self._history)

    def add_message(self, message: Message) -> None:
        """添加消息到歷史。"""
        self._history.append(message)

        # 限制歷史長度
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def add_turn_result(self, result: TurnResult) -> None:
        """添加輪次結果。"""
        self._turn_results.append(result)
        self._current_turn += 1

    def get_recent_messages(self, n: int = 10) -> List[Message]:
        """獲取最近的消息。"""
        return self._history[-n:]

    def get_messages_for_context(self, window_size: int = 10) -> List[Dict[str, Any]]:
        """獲取上下文消息（用於 LLM）。"""
        messages = self.get_recent_messages(window_size)
        return [msg.to_dict() for msg in messages]

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典。"""
        return {
            "max_history": self._max_history,
            "history": [msg.to_dict() for msg in self._history],
            "turn_results": [tr.to_dict() for tr in self._turn_results],
            "current_turn": self._current_turn,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TurnTracker":
        """從字典創建。"""
        tracker = cls(max_history=data.get("max_history", 50))
        tracker._history = [Message.from_dict(m) for m in data.get("history", [])]
        tracker._current_turn = data.get("current_turn", 0)
        return tracker


# =============================================================================
# MultiTurnAdapter 主類
# =============================================================================

class MultiTurnAdapter:
    """多輪對話適配器。

    整合官方 CheckpointStorage 與 Phase 2 會話管理功能。

    官方 API:
    - 使用 CheckpointStorage 進行狀態持久化
    - 支持 MemoryCheckpointStorage 作為默認存儲

    Phase 2 擴展:
    - 會話生命週期管理
    - 輪次追蹤
    - 上下文作用域管理

    Example:
        ```python
        # 創建適配器
        adapter = MultiTurnAdapter("session-1")

        # 添加對話輪次
        result = await adapter.add_turn(
            user_input="Hello, how are you?",
            assistant_response="I'm doing well, thank you!"
        )

        # 獲取對話歷史
        history = adapter.get_history()

        # 保存檢查點
        await adapter.save_checkpoint()

        # 恢復檢查點
        await adapter.restore_checkpoint()
        ```
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        config: Optional[MultiTurnConfig] = None,
        checkpoint_storage: Optional[CheckpointStorage] = None,
    ):
        """初始化多輪對話適配器。

        Args:
            session_id: 會話 ID，如果不提供則自動生成
            config: 多輪對話配置
            checkpoint_storage: Checkpoint 存儲，默認使用 MemoryCheckpointStorage
        """
        # 會話基本信息
        self._session_id = session_id or str(uuid.uuid4())
        self._config = config or MultiTurnConfig()

        # 官方 API - Checkpoint 存儲（使用官方 InMemoryCheckpointStorage）
        self._checkpoint_storage = checkpoint_storage or InMemoryCheckpointStorage()

        # Phase 2 組件
        self._context_manager = ContextManager()
        self._turn_tracker = TurnTracker(max_history=self._config.max_history_length)

        # 會話狀態
        self._state = SessionState.CREATED
        self._created_at = datetime.utcnow()
        self._updated_at = datetime.utcnow()
        self._total_tokens = 0
        self._metadata: Dict[str, Any] = {}

        # 回調函數
        self._on_turn_complete: Optional[Callable[[TurnResult], None]] = None
        self._on_session_complete: Optional[Callable[[SessionInfo], None]] = None

        logger.info(f"MultiTurnAdapter 初始化: session_id={self._session_id}")

    # =========================================================================
    # 屬性
    # =========================================================================

    @property
    def session_id(self) -> str:
        """獲取會話 ID。"""
        return self._session_id

    @property
    def state(self) -> SessionState:
        """獲取會話狀態。"""
        return self._state

    @property
    def turn_count(self) -> int:
        """獲取輪次數。"""
        return self._turn_tracker.current_turn

    @property
    def config(self) -> MultiTurnConfig:
        """獲取配置。"""
        return self._config

    # =========================================================================
    # 會話生命週期
    # =========================================================================

    async def start(self) -> "MultiTurnAdapter":
        """開始會話。"""
        if self._state != SessionState.CREATED:
            raise ValueError(f"無法開始會話，當前狀態: {self._state}")

        self._state = SessionState.ACTIVE
        self._updated_at = datetime.utcnow()

        logger.info(f"會話開始: {self._session_id}")
        return self

    async def pause(self) -> "MultiTurnAdapter":
        """暫停會話。"""
        if self._state != SessionState.ACTIVE:
            raise ValueError(f"無法暫停會話，當前狀態: {self._state}")

        self._state = SessionState.PAUSED
        self._updated_at = datetime.utcnow()

        # 自動保存檢查點
        if self._config.auto_save:
            await self.save_checkpoint()

        logger.info(f"會話暫停: {self._session_id}")
        return self

    async def resume(self) -> "MultiTurnAdapter":
        """恢復會話。"""
        if self._state != SessionState.PAUSED:
            raise ValueError(f"無法恢復會話，當前狀態: {self._state}")

        self._state = SessionState.ACTIVE
        self._updated_at = datetime.utcnow()

        logger.info(f"會話恢復: {self._session_id}")
        return self

    async def complete(self) -> SessionInfo:
        """完成會話。"""
        self._state = SessionState.COMPLETED
        self._updated_at = datetime.utcnow()

        # 最終保存
        if self._config.auto_save:
            await self.save_checkpoint()

        info = self.get_session_info()

        # 觸發回調
        if self._on_session_complete:
            self._on_session_complete(info)

        logger.info(f"會話完成: {self._session_id}, 輪次: {self.turn_count}")
        return info

    # =========================================================================
    # 對話操作
    # =========================================================================

    async def add_turn(
        self,
        user_input: str,
        assistant_response: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TurnResult:
        """添加對話輪次。

        Args:
            user_input: 用戶輸入
            assistant_response: 助手回應（可選，如果不提供則只記錄用戶輸入）
            context: 輪次上下文
            metadata: 元數據

        Returns:
            輪次結果
        """
        import time
        start_time = time.time()

        # 確保會話處於活躍狀態
        if self._state == SessionState.CREATED:
            await self.start()
        elif self._state not in [SessionState.ACTIVE, SessionState.WAITING]:
            raise ValueError(f"無法添加輪次，會話狀態: {self._state}")

        # 檢查輪次限制
        if self.turn_count >= self._config.max_turns:
            raise ValueError(f"已達到最大輪次限制: {self._config.max_turns}")

        # 清除上一輪的輪次上下文
        self._context_manager.clear_turn()

        # 設置新的輪次上下文
        if context:
            for key, value in context.items():
                self._context_manager.set(key, value, ContextScope.TURN)

        # 創建用戶消息
        user_message = Message(
            role=MessageRole.USER,
            content=user_input,
            metadata=metadata or {},
        )
        self._turn_tracker.add_message(user_message)

        # 創建助手消息（如果提供）
        assistant_message = None
        if assistant_response:
            assistant_message = Message(
                role=MessageRole.ASSISTANT,
                content=assistant_response,
                metadata=metadata or {},
            )
            self._turn_tracker.add_message(assistant_message)

        # 計算耗時
        duration_ms = (time.time() - start_time) * 1000

        # 創建輪次結果
        turn_id = f"{self._session_id}-turn-{self.turn_count + 1}"
        result = TurnResult(
            turn_id=turn_id,
            session_id=self._session_id,
            input_message=user_message,
            output_message=assistant_message,
            context=self._context_manager.get_all(ContextScope.TURN),
            duration_ms=duration_ms,
            success=True,
        )

        self._turn_tracker.add_turn_result(result)
        self._updated_at = datetime.utcnow()

        # 觸發回調
        if self._on_turn_complete:
            self._on_turn_complete(result)

        # 自動保存
        if self._config.auto_save and self.turn_count % self._config.save_interval_turns == 0:
            await self.save_checkpoint()

        logger.debug(f"輪次完成: {turn_id}")
        return result

    def get_history(
        self,
        n: Optional[int] = None,
        include_system: bool = True,
    ) -> List[Message]:
        """獲取對話歷史。

        Args:
            n: 獲取最近 n 條消息，如果不提供則返回全部
            include_system: 是否包含系統消息

        Returns:
            消息列表
        """
        history = self._turn_tracker.history

        if not include_system:
            history = [m for m in history if m.role != MessageRole.SYSTEM]

        if n:
            history = history[-n:]

        return history

    def get_context_messages(self, window_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """獲取用於 LLM 的上下文消息。

        Args:
            window_size: 上下文窗口大小

        Returns:
            消息字典列表
        """
        size = window_size or self._config.context_window_size
        return self._turn_tracker.get_messages_for_context(size)

    async def add_system_message(self, content: str) -> None:
        """添加系統消息。

        Args:
            content: 消息內容
        """
        message = Message(
            role=MessageRole.SYSTEM,
            content=content,
        )
        self._turn_tracker.add_message(message)

    # =========================================================================
    # 上下文操作
    # =========================================================================

    def set_context(
        self,
        key: str,
        value: Any,
        scope: ContextScope = ContextScope.SESSION,
    ) -> None:
        """設置上下文變量。"""
        self._context_manager.set(key, value, scope)

    def get_context(self, key: str, default: Any = None) -> Any:
        """獲取上下文變量。"""
        return self._context_manager.get(key, default)

    def get_all_context(self) -> Dict[str, Any]:
        """獲取所有上下文變量。"""
        return self._context_manager.get_all()

    # =========================================================================
    # Checkpoint 操作（使用官方 API）
    # =========================================================================

    async def save_checkpoint(self) -> str:
        """保存檢查點到 CheckpointStorage。

        使用官方 WorkflowCheckpoint 格式：
        - checkpoint_id: 使用 session_id 作為唯一標識
        - workflow_id: 使用 session_id 作為工作流標識
        - shared_state: 存儲完整的會話狀態

        Returns:
            checkpoint_id
        """
        state = self._get_full_state()

        # 創建官方 WorkflowCheckpoint 對象
        checkpoint = WorkflowCheckpoint(
            checkpoint_id=self._session_id,
            workflow_id=self._session_id,
            shared_state=state,  # IPA 狀態存儲在 shared_state 中
            metadata={"adapter": "MultiTurnAdapter", "version": "1.0"},
        )

        # 調用官方 API
        checkpoint_id = await self._checkpoint_storage.save_checkpoint(checkpoint)
        logger.debug(f"檢查點已保存: {checkpoint_id}")
        return checkpoint_id

    async def restore_checkpoint(self) -> bool:
        """從 CheckpointStorage 恢復檢查點。

        使用官方 load_checkpoint API，從 WorkflowCheckpoint.shared_state 提取狀態。

        Returns:
            是否成功恢復
        """
        # 調用官方 API
        checkpoint = await self._checkpoint_storage.load_checkpoint(self._session_id)

        if checkpoint:
            # 從 WorkflowCheckpoint.shared_state 提取 IPA 狀態
            state = checkpoint.shared_state
            self._restore_from_state(state)
            logger.info(f"檢查點已恢復: {self._session_id}")
            return True

        logger.warning(f"未找到檢查點: {self._session_id}")
        return False

    async def delete_checkpoint(self) -> bool:
        """刪除檢查點。

        使用官方 delete_checkpoint API。

        Returns:
            是否成功刪除
        """
        # 調用官方 API
        result = await self._checkpoint_storage.delete_checkpoint(self._session_id)
        if result:
            logger.debug(f"檢查點已刪除: {self._session_id}")
        return result

    def _get_full_state(self) -> Dict[str, Any]:
        """獲取完整狀態用於保存。"""
        return {
            "session_id": self._session_id,
            "state": self._state.value,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
            "total_tokens": self._total_tokens,
            "metadata": self._metadata,
            "config": {
                "max_turns": self._config.max_turns,
                "max_history_length": self._config.max_history_length,
                "session_timeout_seconds": self._config.session_timeout_seconds,
                "auto_save": self._config.auto_save,
                "save_interval_turns": self._config.save_interval_turns,
                "context_window_size": self._config.context_window_size,
                "enable_summarization": self._config.enable_summarization,
                "summarization_threshold": self._config.summarization_threshold,
            },
            "context_manager": self._context_manager.to_dict(),
            "turn_tracker": self._turn_tracker.to_dict(),
        }

    def _restore_from_state(self, state: Dict[str, Any]) -> None:
        """從狀態恢復。"""
        self._session_id = state["session_id"]
        self._state = SessionState(state["state"])
        self._created_at = datetime.fromisoformat(state["created_at"])
        self._updated_at = datetime.fromisoformat(state["updated_at"])
        self._total_tokens = state.get("total_tokens", 0)
        self._metadata = state.get("metadata", {})

        # 恢復配置
        if "config" in state:
            cfg = state["config"]
            self._config = MultiTurnConfig(
                max_turns=cfg.get("max_turns", 100),
                max_history_length=cfg.get("max_history_length", 50),
                session_timeout_seconds=cfg.get("session_timeout_seconds", 3600),
                auto_save=cfg.get("auto_save", True),
                save_interval_turns=cfg.get("save_interval_turns", 5),
                context_window_size=cfg.get("context_window_size", 10),
                enable_summarization=cfg.get("enable_summarization", True),
                summarization_threshold=cfg.get("summarization_threshold", 20),
            )

        # 恢復上下文管理器
        if "context_manager" in state:
            self._context_manager = ContextManager.from_dict(state["context_manager"])

        # 恢復輪次追蹤器
        if "turn_tracker" in state:
            self._turn_tracker = TurnTracker.from_dict(state["turn_tracker"])

    # =========================================================================
    # 會話信息
    # =========================================================================

    def get_session_info(self) -> SessionInfo:
        """獲取會話信息。"""
        return SessionInfo(
            session_id=self._session_id,
            state=self._state,
            created_at=self._created_at,
            updated_at=self._updated_at,
            turn_count=self.turn_count,
            total_tokens=self._total_tokens,
            metadata=self._metadata,
        )

    # =========================================================================
    # 回調設置
    # =========================================================================

    def on_turn_complete(self, callback: Callable[[TurnResult], None]) -> "MultiTurnAdapter":
        """設置輪次完成回調。"""
        self._on_turn_complete = callback
        return self

    def on_session_complete(self, callback: Callable[[SessionInfo], None]) -> "MultiTurnAdapter":
        """設置會話完成回調。"""
        self._on_session_complete = callback
        return self

    # =========================================================================
    # 清理操作
    # =========================================================================

    async def clear_session(self) -> None:
        """清除會話數據（保留配置）。"""
        self._context_manager.clear_session()
        self._turn_tracker = TurnTracker(max_history=self._config.max_history_length)
        self._state = SessionState.CREATED
        self._updated_at = datetime.utcnow()

        await self.delete_checkpoint()
        logger.info(f"會話已清除: {self._session_id}")


# =============================================================================
# 工廠函數
# =============================================================================

def create_multiturn_adapter(
    session_id: Optional[str] = None,
    config: Optional[MultiTurnConfig] = None,
    checkpoint_storage: Optional[CheckpointStorage] = None,
) -> MultiTurnAdapter:
    """創建多輪對話適配器。

    Args:
        session_id: 會話 ID
        config: 配置
        checkpoint_storage: Checkpoint 存儲

    Returns:
        MultiTurnAdapter 實例

    Example:
        ```python
        # 使用默認配置
        adapter = create_multiturn_adapter()

        # 自定義配置
        adapter = create_multiturn_adapter(
            session_id="my-session",
            config=MultiTurnConfig(max_turns=50),
        )
        ```
    """
    return MultiTurnAdapter(
        session_id=session_id,
        config=config,
        checkpoint_storage=checkpoint_storage,
    )


def create_redis_multiturn_adapter(
    redis_client: Any,
    session_id: Optional[str] = None,
    config: Optional[MultiTurnConfig] = None,
    namespace: str = "multiturn",
    ttl_seconds: int = 86400,
) -> MultiTurnAdapter:
    """創建使用 Redis 存儲的多輪對話適配器。

    ⚠️ 警告: 此函數目前暫停使用。
    RedisCheckpointStorage 使用 IPA 自定義接口（save/load/delete），
    而 MultiTurnAdapter 已更新為使用官方 API（save_checkpoint/load_checkpoint）。
    如需 Redis 支持，請使用默認的 InMemoryCheckpointStorage 或等待後續更新。

    Args:
        redis_client: Redis 客戶端
        session_id: 會話 ID
        config: 配置
        namespace: Redis 命名空間
        ttl_seconds: 過期時間

    Returns:
        MultiTurnAdapter 實例

    Raises:
        NotImplementedError: 此函數目前暫停使用

    Example:
        ```python
        # 目前請使用默認的 InMemoryCheckpointStorage
        adapter = create_multiturn_adapter(session_id="my-session")
        ```
    """
    raise NotImplementedError(
        "create_redis_multiturn_adapter 暫停使用。"
        "RedisCheckpointStorage 尚未遷移至官方 API (save_checkpoint/load_checkpoint)。"
        "請使用 create_multiturn_adapter() 搭配默認的 InMemoryCheckpointStorage。"
    )
