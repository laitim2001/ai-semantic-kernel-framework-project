# =============================================================================
# IPA Platform - Multi-Turn Session Manager
# =============================================================================
# Sprint 9: S9-3 MultiTurnSessionManager (8 points)
#
# Manages multi-turn conversation sessions with lifecycle control,
# context persistence, and agent coordination.
# =============================================================================

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    """Status of a multi-turn session.

    會話狀態:
    - CREATED: 已創建，等待開始
    - ACTIVE: 活躍中
    - PAUSED: 暫停
    - WAITING_INPUT: 等待用戶輸入
    - EXPIRED: 已過期
    - COMPLETED: 已完成
    - TERMINATED: 已終止
    """
    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    WAITING_INPUT = "waiting_input"
    EXPIRED = "expired"
    COMPLETED = "completed"
    TERMINATED = "terminated"


@dataclass
class SessionMessage:
    """A message within a multi-turn session.

    會話中的訊息。

    Attributes:
        message_id: 訊息唯一標識符
        session_id: 所屬會話 ID
        turn_number: 所屬輪次
        role: 發送者角色（user/agent/system）
        content: 訊息內容
        sender_id: 發送者 ID
        sender_name: 發送者名稱
        timestamp: 發送時間
        metadata: 額外元數據
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
    def from_dict(cls, data: Dict[str, Any]) -> "SessionMessage":
        """Create from dictionary."""
        return cls(
            message_id=data["message_id"],
            session_id=data["session_id"],
            turn_number=data["turn_number"],
            role=data["role"],
            content=data["content"],
            sender_id=data.get("sender_id"),
            sender_name=data.get("sender_name"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if isinstance(data["timestamp"], str) else data["timestamp"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class MultiTurnSession:
    """Represents a multi-turn conversation session.

    多輪對話會話，追蹤對話的完整生命週期。

    Attributes:
        session_id: 會話唯一標識符
        user_id: 用戶 ID
        agent_ids: 參與的 Agent ID 列表
        status: 會話狀態
        context: 會話上下文
        history: 對話歷史
        current_turn: 當前輪次
        max_turns: 最大輪次限制
        timeout_seconds: 超時時間（秒）
        created_at: 創建時間
        last_activity: 最後活動時間
        expires_at: 過期時間
        metadata: 額外元數據
    """
    session_id: str
    user_id: str
    agent_ids: List[str] = field(default_factory=list)
    status: SessionStatus = SessionStatus.CREATED
    context: Dict[str, Any] = field(default_factory=dict)
    history: List[SessionMessage] = field(default_factory=list)
    current_turn: int = 0
    max_turns: int = 50
    timeout_seconds: int = 1800  # 30 minutes
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Calculate expiration time after initialization."""
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(seconds=self.timeout_seconds)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "agent_ids": self.agent_ids,
            "status": self.status.value,
            "context": self.context,
            "history": [m.to_dict() for m in self.history],
            "current_turn": self.current_turn,
            "max_turns": self.max_turns,
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.metadata,
        }

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

    @property
    def message_count(self) -> int:
        """Get total message count."""
        return len(self.history)

    @property
    def turn_messages(self) -> List[SessionMessage]:
        """Get messages for current turn."""
        return [m for m in self.history if m.turn_number == self.current_turn]

    def update_activity(self) -> None:
        """Update last activity timestamp and extend expiration."""
        self.last_activity = datetime.utcnow()
        self.expires_at = self.last_activity + timedelta(seconds=self.timeout_seconds)


class MultiTurnSessionManager:
    """Manages multi-turn conversation sessions.

    多輪對話會話管理器，負責會話的創建、更新、恢復和清理。

    主要功能:
    - 創建和管理多輪會話
    - 追蹤會話輪次
    - 維護會話上下文
    - 處理會話過期和清理
    - 支持會話暫停和恢復

    Example:
        ```python
        manager = MultiTurnSessionManager()

        # 創建會話
        session = await manager.create_session(
            user_id="user-123",
            agent_ids=["agent-1", "agent-2"],
        )

        # 執行一輪對話
        response = await manager.execute_turn(
            session_id=session.session_id,
            user_input="Hello, can you help me?",
            agent_handler=my_agent_handler,
        )
        ```
    """

    def __init__(
        self,
        default_timeout: int = 1800,
        default_max_turns: int = 50,
        cleanup_interval: int = 300,  # 5 minutes
    ):
        """Initialize the MultiTurnSessionManager.

        Args:
            default_timeout: 默認會話超時時間（秒）
            default_max_turns: 默認最大輪次
            cleanup_interval: 清理過期會話的間隔（秒）
        """
        self._sessions: Dict[str, MultiTurnSession] = {}
        self._user_sessions: Dict[str, Set[str]] = {}  # user_id -> session_ids
        self._default_timeout = default_timeout
        self._default_max_turns = default_max_turns
        self._cleanup_interval = cleanup_interval
        self._locks: Dict[str, asyncio.Lock] = {}
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

        logger.info("MultiTurnSessionManager initialized")

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

        創建新的多輪對話會話。

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
        session_id = str(uuid.uuid4())

        session = MultiTurnSession(
            session_id=session_id,
            user_id=user_id,
            agent_ids=agent_ids or [],
            status=SessionStatus.CREATED,
            context=initial_context or {},
            timeout_seconds=timeout_seconds or self._default_timeout,
            max_turns=max_turns or self._default_max_turns,
            metadata=metadata or {},
        )

        self._sessions[session_id] = session
        self._locks[session_id] = asyncio.Lock()

        # Track user sessions
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = set()
        self._user_sessions[user_id].add(session_id)

        logger.info(f"Created session {session_id} for user {user_id}")
        await self._emit_event("session_created", session)

        return session

    async def get_session(self, session_id: str) -> Optional[MultiTurnSession]:
        """Get a session by ID.

        Args:
            session_id: 會話 ID

        Returns:
            會話，如果不存在則返回 None
        """
        session = self._sessions.get(session_id)

        # Check if expired
        if session and session.is_expired:
            await self._expire_session(session)
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
        if not session:
            return None

        async with self._locks[session_id]:
            if context:
                session.context.update(context)
            if metadata:
                session.metadata.update(metadata)
            session.update_activity()

        logger.debug(f"Updated session {session_id}")
        return session

    async def close_session(
        self,
        session_id: str,
        reason: str = "User requested",
    ) -> bool:
        """Close a session.

        關閉會話。

        Args:
            session_id: 會話 ID
            reason: 關閉原因

        Returns:
            是否成功關閉
        """
        session = await self.get_session(session_id)
        if not session:
            return False

        async with self._locks[session_id]:
            session.status = SessionStatus.COMPLETED
            session.metadata["close_reason"] = reason

        logger.info(f"Closed session {session_id}: {reason}")
        await self._emit_event("session_closed", session)

        return True

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        刪除會話。

        Args:
            session_id: 會話 ID

        Returns:
            是否成功刪除
        """
        session = self._sessions.pop(session_id, None)
        if not session:
            return False

        self._locks.pop(session_id, None)

        # Remove from user sessions
        if session.user_id in self._user_sessions:
            self._user_sessions[session.user_id].discard(session_id)

        logger.info(f"Deleted session {session_id}")
        await self._emit_event("session_deleted", session)

        return True

    # =========================================================================
    # Session Control
    # =========================================================================

    async def start_session(self, session_id: str) -> Optional[MultiTurnSession]:
        """Start a session.

        開始會話。

        Args:
            session_id: 會話 ID

        Returns:
            更新後的會話
        """
        session = await self.get_session(session_id)
        if not session:
            return None

        if session.status != SessionStatus.CREATED:
            logger.warning(f"Cannot start session {session_id} in status {session.status}")
            return None

        async with self._locks[session_id]:
            session.status = SessionStatus.ACTIVE
            session.current_turn = 1
            session.update_activity()

        logger.info(f"Started session {session_id}")
        await self._emit_event("session_started", session)

        return session

    async def pause_session(self, session_id: str) -> bool:
        """Pause a session.

        暫停會話。

        Args:
            session_id: 會話 ID

        Returns:
            是否成功暫停
        """
        session = await self.get_session(session_id)
        if not session or not session.is_active:
            return False

        async with self._locks[session_id]:
            session.status = SessionStatus.PAUSED
            session.update_activity()

        logger.info(f"Paused session {session_id}")
        await self._emit_event("session_paused", session)

        return True

    async def resume_session(self, session_id: str) -> Optional[MultiTurnSession]:
        """Resume a paused session.

        恢復暫停的會話。

        Args:
            session_id: 會話 ID

        Returns:
            更新後的會話
        """
        session = await self.get_session(session_id)
        if not session or session.status != SessionStatus.PAUSED:
            return None

        async with self._locks[session_id]:
            session.status = SessionStatus.ACTIVE
            session.update_activity()

        logger.info(f"Resumed session {session_id}")
        await self._emit_event("session_resumed", session)

        return session

    # =========================================================================
    # Turn Management
    # =========================================================================

    async def start_turn(self, session_id: str) -> Optional[int]:
        """Start a new turn in the session.

        開始新的一輪。

        Args:
            session_id: 會話 ID

        Returns:
            新的輪次號
        """
        session = await self.get_session(session_id)
        if not session or not session.is_active:
            return None

        async with self._locks[session_id]:
            session.current_turn += 1
            session.update_activity()

            # Check max turns
            if session.current_turn > session.max_turns:
                session.status = SessionStatus.COMPLETED
                session.metadata["close_reason"] = "Max turns reached"
                logger.info(f"Session {session_id} reached max turns")
                await self._emit_event("session_completed", session)
                return None

        await self._emit_event("turn_started", {
            "session_id": session_id,
            "turn": session.current_turn,
        })

        return session.current_turn

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sender_id: Optional[str] = None,
        sender_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[SessionMessage]:
        """Add a message to the session.

        添加訊息到會話。

        Args:
            session_id: 會話 ID
            role: 發送者角色
            content: 訊息內容
            sender_id: 發送者 ID
            sender_name: 發送者名稱
            metadata: 額外元數據

        Returns:
            創建的訊息
        """
        session = await self.get_session(session_id)
        if not session:
            return None

        async with self._locks[session_id]:
            message = SessionMessage(
                message_id=str(uuid.uuid4()),
                session_id=session_id,
                turn_number=session.current_turn,
                role=role,
                content=content,
                sender_id=sender_id,
                sender_name=sender_name,
                metadata=metadata or {},
            )
            session.history.append(message)
            session.update_activity()

        await self._emit_event("message_added", message)

        return message

    async def get_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
        turn_number: Optional[int] = None,
    ) -> List[SessionMessage]:
        """Get session message history.

        獲取會話歷史。

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

    async def execute_turn(
        self,
        session_id: str,
        user_input: str,
        agent_handler: Callable[[str, str, List[SessionMessage]], str],
        agent_id: Optional[str] = None,
    ) -> Optional[SessionMessage]:
        """Execute a complete turn with user input and agent response.

        執行一輪完整的對話。

        Args:
            session_id: 會話 ID
            user_input: 用戶輸入
            agent_handler: Agent 處理函數
            agent_id: 指定的 Agent ID

        Returns:
            Agent 回應訊息
        """
        session = await self.get_session(session_id)
        if not session:
            return None

        # Start session if needed
        if session.status == SessionStatus.CREATED:
            await self.start_session(session_id)
            session = await self.get_session(session_id)

        if not session or not session.is_active:
            return None

        # Add user message
        await self.add_message(
            session_id=session_id,
            role="user",
            content=user_input,
            sender_id=session.user_id,
            sender_name="User",
        )

        # Get agent response
        try:
            # Use first agent if not specified
            selected_agent = agent_id or (session.agent_ids[0] if session.agent_ids else None)

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                agent_handler,
                selected_agent,
                user_input,
                session.history[-10:],  # Last 10 messages for context
            )

            # Add agent response
            agent_message = await self.add_message(
                session_id=session_id,
                role="agent",
                content=response,
                sender_id=selected_agent,
                sender_name=f"Agent {selected_agent}",
            )

            return agent_message

        except Exception as e:
            logger.error(f"Agent handler error in session {session_id}: {e}")
            return None

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

        列出會話。

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

        # Filter out expired sessions
        active_sessions = []
        for session in sessions:
            if session.is_expired:
                await self._expire_session(session)
            else:
                active_sessions.append(session)

        return active_sessions

    async def list_active_sessions(
        self,
        user_id: Optional[str] = None,
    ) -> List[MultiTurnSession]:
        """List active sessions.

        列出活躍的會話。

        Args:
            user_id: 按用戶過濾

        Returns:
            活躍會話列表
        """
        return await self.list_sessions(user_id=user_id, active_only=True)

    async def get_user_session_count(self, user_id: str) -> int:
        """Get the number of sessions for a user.

        獲取用戶的會話數量。

        Args:
            user_id: 用戶 ID

        Returns:
            會話數量
        """
        sessions = await self.list_sessions(user_id=user_id)
        return len(sessions)

    # =========================================================================
    # Cleanup and Maintenance
    # =========================================================================

    async def _expire_session(self, session: MultiTurnSession) -> None:
        """Mark a session as expired."""
        if session.status not in [SessionStatus.EXPIRED, SessionStatus.COMPLETED]:
            session.status = SessionStatus.EXPIRED
            session.metadata["close_reason"] = "Session expired"
            logger.info(f"Session {session.session_id} expired")
            await self._emit_event("session_expired", session)

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions.

        清理過期會話。

        Returns:
            清理的會話數量
        """
        expired_count = 0

        for session in list(self._sessions.values()):
            if session.is_expired:
                await self._expire_session(session)
                expired_count += 1

        logger.info(f"Cleaned up {expired_count} expired sessions")
        return expired_count

    async def start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        if self._cleanup_task is not None:
            return

        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(self._cleanup_interval)
                    await self.cleanup_expired_sessions()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Cleanup task error: {e}")

        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info("Started session cleanup task")

    async def stop_cleanup_task(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Stopped session cleanup task")

    # =========================================================================
    # Event Handling
    # =========================================================================

    def on_event(self, event_type: str, handler: Callable) -> None:
        """Register an event handler.

        Args:
            event_type: 事件類型
            handler: 事件處理函數
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    async def _emit_event(self, event_type: str, data: Any) -> None:
        """Emit an event to registered handlers."""
        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Event handler error for {event_type}: {e}")
