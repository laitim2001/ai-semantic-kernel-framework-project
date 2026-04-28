"""
Session Service

Business logic layer for Session management.
Handles session lifecycle, message processing, and agent integration.
"""

from typing import Optional, List, AsyncIterator, Dict, Any
from datetime import datetime
import logging

from src.domain.sessions.models import (
    Session,
    SessionStatus,
    SessionConfig,
    Message,
    MessageRole,
    Attachment,
    ToolCall,
)
from src.domain.sessions.repository import SessionRepository
from src.domain.sessions.cache import SessionCache
from src.domain.sessions.events import (
    SessionEventPublisher,
    SessionEventType,
    get_event_publisher,
)

logger = logging.getLogger(__name__)


class SessionServiceError(Exception):
    """Session 服務錯誤基類"""
    pass


class SessionNotFoundError(SessionServiceError):
    """Session 未找到錯誤"""
    pass


class SessionExpiredError(SessionServiceError):
    """Session 已過期錯誤"""
    pass


class SessionNotActiveError(SessionServiceError):
    """Session 非活躍狀態錯誤"""
    pass


class MessageLimitExceededError(SessionServiceError):
    """訊息數量超限錯誤"""
    pass


class SessionService:
    """Session 服務

    負責:
    - Session 生命週期管理
    - 訊息處理
    - 與 Agent 整合
    - 事件發布
    """

    def __init__(
        self,
        repository: SessionRepository,
        cache: SessionCache,
        event_publisher: Optional[SessionEventPublisher] = None,
    ):
        """初始化服務

        Args:
            repository: Session 存儲
            cache: Session 快取
            event_publisher: 事件發布器
        """
        self._repository = repository
        self._cache = cache
        self._events = event_publisher or get_event_publisher()

    # ===== Session 生命週期管理 =====

    async def create_session(
        self,
        user_id: str,
        agent_id: str,
        config: Optional[SessionConfig] = None,
        system_prompt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """創建新 Session

        Args:
            user_id: 用戶 ID
            agent_id: Agent ID
            config: Session 配置
            system_prompt: 系統提示詞
            metadata: 元數據

        Returns:
            創建的 Session
        """
        # 創建 Session
        session = Session(
            user_id=user_id,
            agent_id=agent_id,
            config=config or SessionConfig(),
            metadata=metadata or {},
        )

        # 添加系統訊息
        if system_prompt:
            system_message = Message(
                role=MessageRole.SYSTEM,
                content=system_prompt,
            )
            session.add_message(system_message)

        # 持久化
        await self._repository.create(session)
        await self._cache.set_session(session)

        # 使用戶列表快取失效
        await self._cache.invalidate_user_sessions(user_id)

        # 發布事件
        await self._events.session_created(
            session_id=session.id,
            user_id=user_id,
            agent_id=agent_id,
        )

        logger.info(f"Created session {session.id} for user {user_id}")
        return session

    async def get_session(
        self,
        session_id: str,
        include_messages: bool = True,
    ) -> Optional[Session]:
        """獲取 Session

        Args:
            session_id: Session ID
            include_messages: 是否包含訊息

        Returns:
            Session 或 None
        """
        # 先查快取
        session = await self._cache.get_session(session_id)
        if session:
            return session

        # 查資料庫
        session = await self._repository.get(session_id)
        if session:
            await self._cache.set_session(session)

        return session

    async def activate_session(self, session_id: str) -> Session:
        """激活 Session

        Args:
            session_id: Session ID

        Returns:
            激活後的 Session

        Raises:
            SessionNotFoundError: Session 未找到
            SessionExpiredError: Session 已過期
        """
        session = await self.get_session(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        if session.is_expired():
            raise SessionExpiredError(f"Session has expired: {session_id}")

        if session.status == SessionStatus.ENDED:
            raise SessionNotActiveError(f"Session has ended: {session_id}")

        session.activate()

        await self._repository.update(session)
        await self._cache.set_session(session)

        await self._events.session_activated(session_id=session_id)

        logger.info(f"Activated session {session_id}")
        return session

    async def suspend_session(self, session_id: str) -> Session:
        """暫停 Session

        Args:
            session_id: Session ID

        Returns:
            暫停後的 Session
        """
        session = await self.get_session(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        session.suspend()

        await self._repository.update(session)
        await self._cache.set_session(session)

        await self._events.publish(
            SessionEventType.SESSION_SUSPENDED,
            session_id=session_id,
        )

        logger.info(f"Suspended session {session_id}")
        return session

    async def resume_session(self, session_id: str) -> Session:
        """恢復暫停的 Session

        Args:
            session_id: Session ID

        Returns:
            恢復後的 Session
        """
        session = await self.get_session(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        if session.is_expired():
            raise SessionExpiredError(f"Session has expired: {session_id}")

        session.resume()

        await self._repository.update(session)
        await self._cache.set_session(session)

        await self._events.publish(
            SessionEventType.SESSION_RESUMED,
            session_id=session_id,
        )

        logger.info(f"Resumed session {session_id}")
        return session

    async def end_session(
        self,
        session_id: str,
        reason: Optional[str] = None,
    ) -> Session:
        """結束 Session

        Args:
            session_id: Session ID
            reason: 結束原因

        Returns:
            結束後的 Session
        """
        session = await self.get_session(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        session.end()

        await self._repository.update(session)
        await self._cache.delete_session(session_id)
        await self._cache.invalidate_user_sessions(session.user_id)

        await self._events.session_ended(
            session_id=session_id,
            reason=reason,
        )

        logger.info(f"Ended session {session_id}, reason: {reason}")
        return session

    # ===== Session 查詢 =====

    async def list_sessions(
        self,
        user_id: str,
        status: Optional[SessionStatus] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Session]:
        """列出用戶的 Sessions

        Args:
            user_id: 用戶 ID
            status: 可選狀態過濾
            limit: 返回數量限制
            offset: 跳過數量

        Returns:
            Session 列表
        """
        return await self._repository.list_by_user(
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def count_sessions(
        self,
        user_id: str,
        status: Optional[SessionStatus] = None,
    ) -> int:
        """計算用戶的 Session 數量

        Args:
            user_id: 用戶 ID
            status: 可選狀態過濾

        Returns:
            Session 數量
        """
        return await self._repository.count_by_user(user_id, status)

    # ===== 訊息處理 =====

    async def send_message(
        self,
        session_id: str,
        content: str,
        attachments: Optional[List[Attachment]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """發送用戶訊息

        Args:
            session_id: Session ID
            content: 訊息內容
            attachments: 附件列表
            metadata: 元數據

        Returns:
            創建的 Message

        Raises:
            SessionNotFoundError: Session 未找到
            SessionNotActiveError: Session 非活躍狀態
            MessageLimitExceededError: 訊息數量超限
        """
        session = await self.get_session(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        if not session.is_active():
            raise SessionNotActiveError(f"Session is not active: {session.status}")

        if not session.can_accept_message():
            raise MessageLimitExceededError(
                f"Maximum messages ({session.config.max_messages}) reached"
            )

        # 創建用戶訊息
        message = Message(
            role=MessageRole.USER,
            content=content,
            attachments=attachments or [],
            metadata=metadata or {},
        )

        # 保存訊息
        await self._repository.add_message(session_id, message)
        await self._cache.append_message(session_id, message)

        # 發布事件
        await self._events.message_sent(
            session_id=session_id,
            message_id=message.id,
            role=message.role.value,
            content_preview=content[:100],
        )

        logger.debug(f"User message sent to session {session_id}")
        return message

    async def add_assistant_message(
        self,
        session_id: str,
        content: str,
        tool_calls: Optional[List[ToolCall]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """添加助手回覆

        Args:
            session_id: Session ID
            content: 回覆內容
            tool_calls: 工具調用列表
            metadata: 元數據

        Returns:
            創建的 Message
        """
        # 創建助手訊息
        message = Message(
            role=MessageRole.ASSISTANT,
            content=content,
            tool_calls=tool_calls or [],
            metadata=metadata or {},
        )

        # 保存訊息
        await self._repository.add_message(session_id, message)
        await self._cache.append_message(session_id, message)

        # 發布事件
        await self._events.message_received(
            session_id=session_id,
            message_id=message.id,
            role=message.role.value,
            content_preview=content[:100],
        )

        logger.debug(f"Assistant message added to session {session_id}")
        return message

    async def get_messages(
        self,
        session_id: str,
        limit: int = 50,
        before_id: Optional[str] = None,
    ) -> List[Message]:
        """獲取訊息歷史

        Args:
            session_id: Session ID
            limit: 返回數量限制
            before_id: 在此 ID 之前的訊息

        Returns:
            Message 列表
        """
        # 如果沒有 before_id，先查快取
        if before_id is None:
            cached = await self._cache.get_messages(session_id, limit)
            if cached:
                return cached

        return await self._repository.get_messages(
            session_id,
            limit=limit,
            before_id=before_id,
        )

    async def get_conversation_for_llm(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """獲取 LLM 格式的對話歷史

        Args:
            session_id: Session ID
            limit: 最大訊息數量

        Returns:
            LLM 格式的訊息列表
        """
        session = await self.get_session(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        return session.to_llm_messages(include_system=True)

    # ===== 工具調用 =====

    async def add_tool_call(
        self,
        session_id: str,
        message_id: str,
        tool_call: ToolCall,
    ) -> ToolCall:
        """添加工具調用記錄

        Args:
            session_id: Session ID
            message_id: Message ID
            tool_call: 工具調用物件

        Returns:
            添加的 ToolCall
        """
        await self._events.tool_call_requested(
            session_id=session_id,
            tool_call_id=tool_call.id,
            tool_name=tool_call.tool_name,
            requires_approval=tool_call.requires_approval,
        )

        logger.debug(
            f"Tool call {tool_call.tool_name} requested in session {session_id}"
        )
        return tool_call

    async def approve_tool_call(
        self,
        session_id: str,
        tool_call_id: str,
        approver_id: str,
    ) -> None:
        """批准工具調用

        Args:
            session_id: Session ID
            tool_call_id: ToolCall ID
            approver_id: 批准者 ID
        """
        await self._events.publish(
            SessionEventType.TOOL_CALL_APPROVED,
            session_id=session_id,
            data={
                "tool_call_id": tool_call_id,
                "approver_id": approver_id,
            },
        )

        logger.info(
            f"Tool call {tool_call_id} approved by {approver_id}"
        )

    async def reject_tool_call(
        self,
        session_id: str,
        tool_call_id: str,
        approver_id: str,
        reason: Optional[str] = None,
    ) -> None:
        """拒絕工具調用

        Args:
            session_id: Session ID
            tool_call_id: ToolCall ID
            approver_id: 拒絕者 ID
            reason: 拒絕原因
        """
        await self._events.publish(
            SessionEventType.TOOL_CALL_REJECTED,
            session_id=session_id,
            data={
                "tool_call_id": tool_call_id,
                "approver_id": approver_id,
                "reason": reason,
            },
        )

        logger.info(
            f"Tool call {tool_call_id} rejected by {approver_id}, reason: {reason}"
        )

    # ===== 維護操作 =====

    async def cleanup_expired_sessions(self) -> int:
        """清理過期 Sessions

        Returns:
            清理的 Session 數量
        """
        count = await self._repository.cleanup_expired()
        if count > 0:
            logger.info(f"Cleaned up {count} expired sessions")
        return count

    async def update_session_title(
        self,
        session_id: str,
        title: str,
    ) -> Session:
        """更新 Session 標題

        Args:
            session_id: Session ID
            title: 新標題

        Returns:
            更新後的 Session
        """
        session = await self.get_session(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        session.title = title
        session.updated_at = datetime.utcnow()

        await self._repository.update(session)
        await self._cache.set_session(session)

        return session

    async def update_session_metadata(
        self,
        session_id: str,
        metadata: Dict[str, Any],
    ) -> Session:
        """更新 Session 元數據

        Args:
            session_id: Session ID
            metadata: 新元數據

        Returns:
            更新後的 Session
        """
        session = await self.get_session(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        session.metadata.update(metadata)
        session.updated_at = datetime.utcnow()

        await self._repository.update(session)
        await self._cache.set_session(session)

        return session
