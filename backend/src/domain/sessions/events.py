"""
Session Events

Event definitions and publisher for Session domain events.
Supports async event publishing for real-time updates and audit logging.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable, Awaitable
from datetime import datetime
import uuid
import asyncio
import logging

logger = logging.getLogger(__name__)


class SessionEventType(str, Enum):
    """Session 事件類型"""

    # Session 生命週期事件
    SESSION_CREATED = "session.created"
    SESSION_ACTIVATED = "session.activated"
    SESSION_SUSPENDED = "session.suspended"
    SESSION_RESUMED = "session.resumed"
    SESSION_ENDED = "session.ended"
    SESSION_EXPIRED = "session.expired"

    # 訊息事件
    MESSAGE_SENT = "message.sent"
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_STREAMING = "message.streaming"

    # 工具調用事件
    TOOL_CALL_REQUESTED = "tool_call.requested"
    TOOL_CALL_APPROVED = "tool_call.approved"
    TOOL_CALL_REJECTED = "tool_call.rejected"
    TOOL_CALL_COMPLETED = "tool_call.completed"
    TOOL_CALL_FAILED = "tool_call.failed"

    # 附件事件
    ATTACHMENT_UPLOADED = "attachment.uploaded"
    ATTACHMENT_DELETED = "attachment.deleted"

    # 錯誤事件
    ERROR_OCCURRED = "error.occurred"


@dataclass
class SessionEvent:
    """Session 事件

    所有 Session 相關事件的基礎類別。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: SessionEventType = SessionEventType.SESSION_CREATED
    session_id: str = ""
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionEvent":
        """從字典創建"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            event_type=SessionEventType(data.get("event_type", "session.created")),
            session_id=data.get("session_id", ""),
            user_id=data.get("user_id"),
            agent_id=data.get("agent_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.utcnow(),
            data=data.get("data", {}),
            metadata=data.get("metadata", {}),
        )


# 事件處理器類型
EventHandler = Callable[[SessionEvent], Awaitable[None]]


class SessionEventPublisher:
    """Session 事件發布器

    支援:
    - 本地事件訂閱/發布
    - 可擴展至消息隊列 (RabbitMQ, Redis Pub/Sub)
    """

    def __init__(self):
        """初始化事件發布器"""
        self._handlers: Dict[SessionEventType, List[EventHandler]] = {}
        self._global_handlers: List[EventHandler] = []

    def subscribe(
        self,
        event_type: SessionEventType,
        handler: EventHandler,
    ) -> None:
        """訂閱特定事件類型

        Args:
            event_type: 事件類型
            handler: 事件處理器
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """訂閱所有事件

        Args:
            handler: 事件處理器
        """
        self._global_handlers.append(handler)

    def unsubscribe(
        self,
        event_type: SessionEventType,
        handler: EventHandler,
    ) -> None:
        """取消訂閱

        Args:
            event_type: 事件類型
            handler: 事件處理器
        """
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h != handler
            ]

    async def publish(
        self,
        event_type: SessionEventType,
        session_id: str,
        data: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionEvent:
        """發布事件

        Args:
            event_type: 事件類型
            session_id: Session ID
            data: 事件數據
            user_id: 用戶 ID
            agent_id: Agent ID
            metadata: 元數據

        Returns:
            發布的事件
        """
        event = SessionEvent(
            event_type=event_type,
            session_id=session_id,
            user_id=user_id,
            agent_id=agent_id,
            data=data or {},
            metadata=metadata or {},
        )

        # 收集所有要執行的處理器
        handlers = []

        # 特定類型的處理器
        if event_type in self._handlers:
            handlers.extend(self._handlers[event_type])

        # 全局處理器
        handlers.extend(self._global_handlers)

        # 並發執行所有處理器
        if handlers:
            await asyncio.gather(
                *[self._safe_call(h, event) for h in handlers],
                return_exceptions=True
            )

        logger.debug(
            f"Published event: {event_type.value} for session {session_id}"
        )

        return event

    async def _safe_call(
        self,
        handler: EventHandler,
        event: SessionEvent,
    ) -> None:
        """安全地調用處理器

        Args:
            handler: 事件處理器
            event: 事件
        """
        try:
            await handler(event)
        except Exception as e:
            logger.error(
                f"Error in event handler for {event.event_type.value}: {e}",
                exc_info=True
            )

    # ===== 便捷方法 =====

    async def session_created(
        self,
        session_id: str,
        user_id: str,
        agent_id: str,
        **extra_data,
    ) -> SessionEvent:
        """發布 Session 創建事件"""
        return await self.publish(
            SessionEventType.SESSION_CREATED,
            session_id=session_id,
            user_id=user_id,
            agent_id=agent_id,
            data=extra_data,
        )

    async def session_activated(
        self,
        session_id: str,
        **extra_data,
    ) -> SessionEvent:
        """發布 Session 激活事件"""
        return await self.publish(
            SessionEventType.SESSION_ACTIVATED,
            session_id=session_id,
            data=extra_data,
        )

    async def session_ended(
        self,
        session_id: str,
        reason: Optional[str] = None,
        **extra_data,
    ) -> SessionEvent:
        """發布 Session 結束事件"""
        data = {"reason": reason, **extra_data} if reason else extra_data
        return await self.publish(
            SessionEventType.SESSION_ENDED,
            session_id=session_id,
            data=data,
        )

    async def message_sent(
        self,
        session_id: str,
        message_id: str,
        role: str,
        content_preview: str,
        **extra_data,
    ) -> SessionEvent:
        """發布訊息發送事件"""
        return await self.publish(
            SessionEventType.MESSAGE_SENT,
            session_id=session_id,
            data={
                "message_id": message_id,
                "role": role,
                "content_preview": content_preview[:100],
                **extra_data,
            },
        )

    async def message_received(
        self,
        session_id: str,
        message_id: str,
        role: str,
        content_preview: str,
        **extra_data,
    ) -> SessionEvent:
        """發布訊息接收事件"""
        return await self.publish(
            SessionEventType.MESSAGE_RECEIVED,
            session_id=session_id,
            data={
                "message_id": message_id,
                "role": role,
                "content_preview": content_preview[:100],
                **extra_data,
            },
        )

    async def tool_call_requested(
        self,
        session_id: str,
        tool_call_id: str,
        tool_name: str,
        requires_approval: bool,
        **extra_data,
    ) -> SessionEvent:
        """發布工具調用請求事件"""
        return await self.publish(
            SessionEventType.TOOL_CALL_REQUESTED,
            session_id=session_id,
            data={
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "requires_approval": requires_approval,
                **extra_data,
            },
        )

    async def error_occurred(
        self,
        session_id: str,
        error_type: str,
        error_message: str,
        **extra_data,
    ) -> SessionEvent:
        """發布錯誤事件"""
        return await self.publish(
            SessionEventType.ERROR_OCCURRED,
            session_id=session_id,
            data={
                "error_type": error_type,
                "error_message": error_message,
                **extra_data,
            },
        )


# 全局事件發布器實例
_event_publisher: Optional[SessionEventPublisher] = None


def get_event_publisher() -> SessionEventPublisher:
    """獲取全局事件發布器

    Returns:
        SessionEventPublisher 實例
    """
    global _event_publisher
    if _event_publisher is None:
        _event_publisher = SessionEventPublisher()
    return _event_publisher


def reset_event_publisher() -> None:
    """重置全局事件發布器 (用於測試)"""
    global _event_publisher
    _event_publisher = None
