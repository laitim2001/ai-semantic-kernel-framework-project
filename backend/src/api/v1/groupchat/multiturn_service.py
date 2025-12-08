# =============================================================================
# IPA Platform - GroupChat Multi-turn API Service
# =============================================================================
# Sprint 32: S32-2 會話層遷移
#
# 此服務包裝 MultiTurnAdapter 以提供與舊 domain 層 API 兼容的接口。
# 用於 groupchat/routes.py 中的 Multi-turn Session 端點。
#
# 架構更新 (Sprint 32):
#   - 使用 integrations.agent_framework.multiturn.MultiTurnAdapter
#   - 不再依賴 domain.orchestration.multiturn
#   - 不再依賴 domain.orchestration.memory
#
# 官方 API 使用:
#   - CheckpointStorage (透過 MultiTurnAdapter)
#   - InMemoryCheckpointStorage (默認存儲)
# =============================================================================

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

# 使用適配器層 (取代 domain 層)
from src.integrations.agent_framework.multiturn import (
    MultiTurnAdapter,
    SessionState,
    Message,
    MessageRole,
    TurnResult,
    SessionInfo,
    MultiTurnConfig,
    create_multiturn_adapter,
)

logger = logging.getLogger(__name__)


# =============================================================================
# 兼容性類型 (對應舊 domain 層 API)
# =============================================================================

class SessionStatus(str, Enum):
    """Session status enum for API compatibility.

    映射到 SessionState:
    - CREATED -> CREATED
    - ACTIVE -> ACTIVE
    - PAUSED -> PAUSED
    - WAITING_INPUT -> WAITING
    - EXPIRED -> EXPIRED
    - COMPLETED -> COMPLETED
    - TERMINATED -> ERROR
    """
    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    WAITING_INPUT = "waiting_input"
    EXPIRED = "expired"
    COMPLETED = "completed"
    TERMINATED = "terminated"

    @classmethod
    def from_session_state(cls, state: SessionState) -> "SessionStatus":
        """Convert SessionState to SessionStatus."""
        mapping = {
            SessionState.CREATED: cls.CREATED,
            SessionState.ACTIVE: cls.ACTIVE,
            SessionState.PAUSED: cls.PAUSED,
            SessionState.WAITING: cls.WAITING_INPUT,
            SessionState.COMPLETED: cls.COMPLETED,
            SessionState.EXPIRED: cls.EXPIRED,
            SessionState.ERROR: cls.TERMINATED,
        }
        return mapping.get(state, cls.ACTIVE)


@dataclass
class SessionMessage:
    """Session message for API compatibility.

    對應舊 domain 層 SessionMessage。
    """
    message_id: str
    session_id: str
    turn_number: int
    role: str
    content: str
    sender_id: Optional[str] = None
    sender_name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "message_id": self.message_id,
            "session_id": self.session_id,
            "turn_number": self.turn_number,
            "role": self.role,
            "content": self.content,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_adapter_message(
        cls,
        msg: Message,
        session_id: str,
        turn_number: int,
    ) -> "SessionMessage":
        """Create from adapter Message."""
        return cls(
            message_id=str(uuid4()),
            session_id=session_id,
            turn_number=turn_number,
            role=msg.role.value,
            content=msg.content,
            sender_id=msg.metadata.get("sender_id"),
            sender_name=msg.metadata.get("sender_name"),
            timestamp=msg.timestamp,
            metadata=msg.metadata,
        )


@dataclass
class MultiTurnSession:
    """Multi-turn session for API compatibility.

    對應舊 domain 層 MultiTurnSession。
    """
    session_id: str
    user_id: str
    agent_ids: List[str] = field(default_factory=list)
    status: SessionStatus = SessionStatus.CREATED
    context: Dict[str, Any] = field(default_factory=dict)
    history: List[SessionMessage] = field(default_factory=list)
    current_turn: int = 0
    max_turns: int = 50
    timeout_seconds: int = 1800
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Calculate expiration time after initialization."""
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(seconds=self.timeout_seconds)

    @property
    def is_active(self) -> bool:
        """Check if session is active."""
        return self.status in [SessionStatus.ACTIVE, SessionStatus.WAITING_INPUT]

    @property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False


# =============================================================================
# Multi-turn API Service
# =============================================================================

class MultiTurnAPIService:
    """Multi-turn API Service wrapping MultiTurnAdapter.

    提供與舊 MultiTurnSessionManager 相同的 API 接口，
    但內部使用 MultiTurnAdapter 實現。

    Sprint 32: S32-2 會話層遷移的核心組件。

    Example:
        ```python
        service = MultiTurnAPIService()

        # 創建會話
        session = await service.create_session(user_id="user-123")

        # 執行輪次
        response = await service.execute_turn(
            session_id=session.session_id,
            user_input="Hello!",
            agent_handler=my_handler,
        )
        ```
    """

    def __init__(
        self,
        default_timeout: int = 1800,
        default_max_turns: int = 50,
    ):
        """Initialize MultiTurnAPIService.

        Args:
            default_timeout: 默認會話超時時間（秒）
            default_max_turns: 默認最大輪次
        """
        self._default_timeout = default_timeout
        self._default_max_turns = default_max_turns

        # 會話存儲
        self._adapters: Dict[str, MultiTurnAdapter] = {}
        self._sessions: Dict[str, MultiTurnSession] = {}
        self._user_sessions: Dict[str, Set[str]] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

        logger.info("MultiTurnAPIService 初始化完成 (使用 MultiTurnAdapter)")

    # =========================================================================
    # Session Lifecycle
    # =========================================================================

    async def create_session(
        self,
        user_id: str,
        agent_ids: Optional[List[str]] = None,
        initial_context: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
        max_turns: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MultiTurnSession:
        """Create a new multi-turn session.

        Args:
            user_id: 用戶 ID
            agent_ids: 參與的 Agent ID 列表
            initial_context: 初始上下文
            timeout_seconds: 超時時間
            max_turns: 最大輪次
            metadata: 額外元數據

        Returns:
            創建的會話
        """
        session_id = str(uuid4())
        timeout = timeout_seconds or self._default_timeout
        max_t = max_turns or self._default_max_turns

        # 創建 MultiTurnAdapter
        config = MultiTurnConfig(
            max_turns=max_t,
            session_timeout_seconds=timeout,
        )
        adapter = create_multiturn_adapter(
            session_id=session_id,
            config=config,
        )

        # 設置初始上下文
        if initial_context:
            for key, value in initial_context.items():
                adapter.set_context(key, value)

        # 創建兼容的 session 對象
        session = MultiTurnSession(
            session_id=session_id,
            user_id=user_id,
            agent_ids=agent_ids or [],
            status=SessionStatus.CREATED,
            context=initial_context or {},
            max_turns=max_t,
            timeout_seconds=timeout,
            metadata=metadata or {},
        )

        # 存儲
        self._adapters[session_id] = adapter
        self._sessions[session_id] = session
        self._locks[session_id] = asyncio.Lock()

        # 追蹤用戶會話
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = set()
        self._user_sessions[user_id].add(session_id)

        logger.info(f"創建會話 {session_id} (用戶: {user_id})")
        return session

    async def get_session(self, session_id: str) -> Optional[MultiTurnSession]:
        """Get a session by ID.

        Args:
            session_id: 會話 ID

        Returns:
            會話，如果不存在則返回 None
        """
        session = self._sessions.get(session_id)

        # 檢查是否過期
        if session and session.is_expired:
            await self._expire_session(session_id)
            return None

        return session

    async def update_session(
        self,
        session_id: str,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[MultiTurnSession]:
        """Update session context and metadata.

        Args:
            session_id: 會話 ID
            context: 要更新的上下文
            metadata: 要更新的元數據

        Returns:
            更新後的會話
        """
        session = await self.get_session(session_id)
        adapter = self._adapters.get(session_id)

        if not session or not adapter:
            return None

        async with self._locks[session_id]:
            if context:
                session.context.update(context)
                for key, value in context.items():
                    adapter.set_context(key, value)
            if metadata:
                session.metadata.update(metadata)
            session.last_activity = datetime.utcnow()

        return session

    async def close_session(
        self,
        session_id: str,
        reason: str = "User requested",
    ) -> bool:
        """Close a session.

        Args:
            session_id: 會話 ID
            reason: 關閉原因

        Returns:
            是否成功關閉
        """
        session = await self.get_session(session_id)
        adapter = self._adapters.get(session_id)

        if not session:
            return False

        async with self._locks[session_id]:
            session.status = SessionStatus.COMPLETED
            session.metadata["close_reason"] = reason

            if adapter:
                await adapter.complete()

        logger.info(f"關閉會話 {session_id}: {reason}")
        return True

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: 會話 ID

        Returns:
            是否成功刪除
        """
        session = self._sessions.pop(session_id, None)
        adapter = self._adapters.pop(session_id, None)
        self._locks.pop(session_id, None)

        if not session:
            return False

        # 清理 adapter checkpoint
        if adapter:
            await adapter.delete_checkpoint()

        # 移除用戶會話關聯
        if session.user_id in self._user_sessions:
            self._user_sessions[session.user_id].discard(session_id)

        logger.info(f"刪除會話 {session_id}")
        return True

    # =========================================================================
    # Turn Management
    # =========================================================================

    async def execute_turn(
        self,
        session_id: str,
        user_input: str,
        agent_handler: Callable[[str, str, List], str],
        agent_id: Optional[str] = None,
    ) -> Optional[SessionMessage]:
        """Execute a complete turn with user input and agent response.

        Args:
            session_id: 會話 ID
            user_input: 用戶輸入
            agent_handler: Agent 處理函數 (agent_id, input, history) -> response
            agent_id: 指定的 Agent ID

        Returns:
            Agent 回應訊息
        """
        session = await self.get_session(session_id)
        adapter = self._adapters.get(session_id)

        if not session or not adapter:
            return None

        # 啟動會話 (如需要)
        if session.status == SessionStatus.CREATED:
            session.status = SessionStatus.ACTIVE
            await adapter.start()

        if not session.is_active:
            return None

        async with self._locks[session_id]:
            # 獲取 agent 回應
            try:
                selected_agent = agent_id or (session.agent_ids[0] if session.agent_ids else None)

                # 調用 agent handler
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    agent_handler,
                    selected_agent,
                    user_input,
                    session.history[-10:],
                )

                # 通過 adapter 添加輪次
                turn_result = await adapter.add_turn(
                    user_input=user_input,
                    assistant_response=response,
                    metadata={
                        "sender_id": selected_agent,
                        "sender_name": f"Agent {selected_agent}",
                    },
                )

                # 更新 session
                session.current_turn = adapter.turn_count
                session.last_activity = datetime.utcnow()

                # 創建 SessionMessage 用於 API 回應
                agent_message = SessionMessage(
                    message_id=turn_result.turn_id,
                    session_id=session_id,
                    turn_number=session.current_turn,
                    role="agent",
                    content=response,
                    sender_id=selected_agent,
                    sender_name=f"Agent {selected_agent}",
                    timestamp=datetime.utcnow(),
                )

                # 更新 history
                user_msg = SessionMessage(
                    message_id=f"{turn_result.turn_id}-user",
                    session_id=session_id,
                    turn_number=session.current_turn,
                    role="user",
                    content=user_input,
                    sender_id=session.user_id,
                    sender_name="User",
                    timestamp=datetime.utcnow(),
                )
                session.history.append(user_msg)
                session.history.append(agent_message)

                return agent_message

            except Exception as e:
                logger.error(f"執行輪次錯誤 (session={session_id}): {e}")
                return None

    async def get_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
        turn_number: Optional[int] = None,
    ) -> List[SessionMessage]:
        """Get session message history.

        Args:
            session_id: 會話 ID
            limit: 最大訊息數
            turn_number: 只返回指定輪次的訊息

        Returns:
            訊息列表
        """
        session = await self.get_session(session_id)
        if not session:
            return []

        messages = session.history

        if turn_number is not None:
            messages = [m for m in messages if m.turn_number == turn_number]

        if limit:
            messages = messages[-limit:]

        return messages

    # =========================================================================
    # Query Methods
    # =========================================================================

    async def list_sessions(
        self,
        user_id: Optional[str] = None,
        status: Optional[SessionStatus] = None,
        active_only: bool = False,
    ) -> List[MultiTurnSession]:
        """List sessions with optional filters.

        Args:
            user_id: 按用戶過濾
            status: 按狀態過濾
            active_only: 只返回活躍會話

        Returns:
            會話列表
        """
        sessions = list(self._sessions.values())

        if user_id:
            session_ids = self._user_sessions.get(user_id, set())
            sessions = [s for s in sessions if s.session_id in session_ids]

        if status:
            sessions = [s for s in sessions if s.status == status]

        if active_only:
            sessions = [s for s in sessions if s.is_active]

        # 過濾過期會話
        active_sessions = []
        for session in sessions:
            if session.is_expired:
                await self._expire_session(session.session_id)
            else:
                active_sessions.append(session)

        return active_sessions

    # =========================================================================
    # Internal Methods
    # =========================================================================

    async def _expire_session(self, session_id: str) -> None:
        """Mark a session as expired."""
        session = self._sessions.get(session_id)
        adapter = self._adapters.get(session_id)

        if session and session.status not in [SessionStatus.EXPIRED, SessionStatus.COMPLETED]:
            session.status = SessionStatus.EXPIRED
            session.metadata["close_reason"] = "Session expired"

            if adapter:
                await adapter.complete()

            logger.info(f"會話過期: {session_id}")


# =============================================================================
# 全局實例
# =============================================================================

_multiturn_service: Optional[MultiTurnAPIService] = None


def get_multiturn_service() -> MultiTurnAPIService:
    """Get or create the global MultiTurnAPIService instance.

    Returns:
        MultiTurnAPIService 單例實例
    """
    global _multiturn_service
    if _multiturn_service is None:
        _multiturn_service = MultiTurnAPIService()
    return _multiturn_service
