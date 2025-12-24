"""
Session Events

Event definitions and publisher for Session domain events.
Supports async event publishing for real-time updates and audit logging.

Sprint 45 新增:
- ExecutionEventType: Agent 執行事件類型
- ExecutionEvent: Agent 執行事件（支援 WebSocket/SSE 串流）
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable, Awaitable, Union
from datetime import datetime
import uuid
import asyncio
import logging
import json

logger = logging.getLogger(__name__)


# =============================================================================
# Sprint 45: ExecutionEvent 系統 (S45-4)
# =============================================================================

class ExecutionEventType(str, Enum):
    """Agent 執行事件類型

    用於 AgentExecutor 串流回應，支援 WebSocket 和 SSE 兩種通訊方式。

    分類:
    - 內容事件: 文字回應內容
    - 工具事件: 工具調用和結果
    - 狀態事件: 執行生命週期
    - 系統事件: 連接維護
    """

    # 內容事件 - 文字回應
    CONTENT = "content"              # 完整內容（非串流模式）
    CONTENT_DELTA = "content_delta"  # 串流內容片段

    # 工具事件 - 工具調用流程
    TOOL_CALL = "tool_call"                    # 工具調用請求
    TOOL_RESULT = "tool_result"                # 工具執行結果
    APPROVAL_REQUIRED = "approval_required"    # 需要人工審批
    APPROVAL_RESPONSE = "approval_response"    # 審批回應

    # 狀態事件 - 執行生命週期
    STARTED = "started"    # 執行開始
    DONE = "done"          # 執行完成
    ERROR = "error"        # 執行錯誤

    # 系統事件 - 連接維護
    HEARTBEAT = "heartbeat"  # 心跳保活


@dataclass
class ToolCallInfo:
    """工具調用信息"""
    id: str                              # 工具調用 ID
    name: str                            # 工具名稱
    arguments: Dict[str, Any]            # 工具參數
    requires_approval: bool = False      # 是否需要審批

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments,
            "requires_approval": self.requires_approval,
        }


@dataclass
class ToolResultInfo:
    """工具結果信息"""
    tool_call_id: str                    # 對應的工具調用 ID
    name: str                            # 工具名稱
    result: Any                          # 執行結果
    success: bool = True                 # 是否成功
    error_message: Optional[str] = None  # 錯誤訊息

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_call_id": self.tool_call_id,
            "name": self.name,
            "result": self.result,
            "success": self.success,
            "error_message": self.error_message,
        }


@dataclass
class UsageInfo:
    """Token 使用量信息"""
    prompt_tokens: int = 0       # Prompt tokens
    completion_tokens: int = 0   # Completion tokens
    total_tokens: int = 0        # 總 tokens

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class ExecutionEvent:
    """Agent 執行事件

    用於 AgentExecutor 的串流回應，支援:
    - WebSocket: JSON 格式推送
    - SSE: Server-Sent Events 格式

    Attributes:
        id: 事件唯一 ID
        event_type: 事件類型
        session_id: Session ID
        execution_id: 執行 ID
        timestamp: 事件時間戳
        content: 文字內容（CONTENT/CONTENT_DELTA 事件）
        tool_call: 工具調用信息（TOOL_CALL 事件）
        tool_result: 工具結果信息（TOOL_RESULT 事件）
        error: 錯誤信息（ERROR 事件）
        usage: Token 使用量（DONE 事件）
        metadata: 額外元數據
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: ExecutionEventType = ExecutionEventType.STARTED
    session_id: str = ""
    execution_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # 內容相關
    content: Optional[str] = None

    # 工具相關
    tool_call: Optional[ToolCallInfo] = None
    tool_result: Optional[ToolResultInfo] = None

    # 審批相關
    approval_request_id: Optional[str] = None
    approval_status: Optional[str] = None  # "approved" | "rejected"
    approval_feedback: Optional[str] = None

    # 錯誤相關
    error: Optional[str] = None
    error_code: Optional[str] = None

    # 完成相關
    usage: Optional[UsageInfo] = None
    finish_reason: Optional[str] = None  # "stop" | "tool_calls" | "length" | "error"

    # 元數據
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典（用於 WebSocket JSON）"""
        result = {
            "id": self.id,
            "event": self.event_type.value,
            "session_id": self.session_id,
            "execution_id": self.execution_id,
            "timestamp": self.timestamp.isoformat(),
        }

        # 根據事件類型添加相關字段
        if self.event_type in (ExecutionEventType.CONTENT, ExecutionEventType.CONTENT_DELTA):
            result["content"] = self.content or ""

        elif self.event_type == ExecutionEventType.TOOL_CALL:
            if self.tool_call:
                result["tool_call"] = self.tool_call.to_dict()

        elif self.event_type == ExecutionEventType.TOOL_RESULT:
            if self.tool_result:
                result["tool_result"] = self.tool_result.to_dict()

        elif self.event_type == ExecutionEventType.APPROVAL_REQUIRED:
            result["approval_request_id"] = self.approval_request_id
            if self.tool_call:
                result["tool_call"] = self.tool_call.to_dict()

        elif self.event_type == ExecutionEventType.APPROVAL_RESPONSE:
            result["approval_request_id"] = self.approval_request_id
            result["approval_status"] = self.approval_status
            result["approval_feedback"] = self.approval_feedback

        elif self.event_type == ExecutionEventType.ERROR:
            result["error"] = self.error
            result["error_code"] = self.error_code

        elif self.event_type == ExecutionEventType.DONE:
            result["finish_reason"] = self.finish_reason
            if self.usage:
                result["usage"] = self.usage.to_dict()

        # 添加元數據（如果有）
        if self.metadata:
            result["metadata"] = self.metadata

        return result

    def to_sse(self) -> str:
        """轉換為 SSE 格式

        格式:
            event: {event_type}
            data: {json_data}

        Returns:
            SSE 格式字串
        """
        data = self.to_dict()
        json_data = json.dumps(data, ensure_ascii=False)
        return f"event: {self.event_type.value}\ndata: {json_data}\n\n"

    def to_json(self) -> str:
        """轉換為 JSON 字串（用於 WebSocket）"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionEvent":
        """從字典創建事件"""
        event = cls(
            id=data.get("id", str(uuid.uuid4())),
            event_type=ExecutionEventType(data.get("event", "started")),
            session_id=data.get("session_id", ""),
            execution_id=data.get("execution_id", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.utcnow(),
            content=data.get("content"),
            error=data.get("error"),
            error_code=data.get("error_code"),
            finish_reason=data.get("finish_reason"),
            approval_request_id=data.get("approval_request_id"),
            approval_status=data.get("approval_status"),
            approval_feedback=data.get("approval_feedback"),
            metadata=data.get("metadata", {}),
        )

        # 解析工具調用
        if "tool_call" in data and data["tool_call"]:
            tc = data["tool_call"]
            event.tool_call = ToolCallInfo(
                id=tc.get("id", ""),
                name=tc.get("name", ""),
                arguments=tc.get("arguments", {}),
                requires_approval=tc.get("requires_approval", False),
            )

        # 解析工具結果
        if "tool_result" in data and data["tool_result"]:
            tr = data["tool_result"]
            event.tool_result = ToolResultInfo(
                tool_call_id=tr.get("tool_call_id", ""),
                name=tr.get("name", ""),
                result=tr.get("result"),
                success=tr.get("success", True),
                error_message=tr.get("error_message"),
            )

        # 解析使用量
        if "usage" in data and data["usage"]:
            u = data["usage"]
            event.usage = UsageInfo(
                prompt_tokens=u.get("prompt_tokens", 0),
                completion_tokens=u.get("completion_tokens", 0),
                total_tokens=u.get("total_tokens", 0),
            )

        return event


# ExecutionEvent 工廠方法
class ExecutionEventFactory:
    """ExecutionEvent 工廠類別

    提供便捷方法創建各類型事件。
    """

    @staticmethod
    def started(
        session_id: str,
        execution_id: str,
        **metadata
    ) -> ExecutionEvent:
        """創建執行開始事件"""
        return ExecutionEvent(
            event_type=ExecutionEventType.STARTED,
            session_id=session_id,
            execution_id=execution_id,
            metadata=metadata,
        )

    @staticmethod
    def content(
        session_id: str,
        execution_id: str,
        content: str,
        **metadata
    ) -> ExecutionEvent:
        """創建完整內容事件"""
        return ExecutionEvent(
            event_type=ExecutionEventType.CONTENT,
            session_id=session_id,
            execution_id=execution_id,
            content=content,
            metadata=metadata,
        )

    @staticmethod
    def content_delta(
        session_id: str,
        execution_id: str,
        delta: str,
        **metadata
    ) -> ExecutionEvent:
        """創建串流內容片段事件"""
        return ExecutionEvent(
            event_type=ExecutionEventType.CONTENT_DELTA,
            session_id=session_id,
            execution_id=execution_id,
            content=delta,
            metadata=metadata,
        )

    @staticmethod
    def tool_call(
        session_id: str,
        execution_id: str,
        tool_call_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        requires_approval: bool = False,
        **metadata
    ) -> ExecutionEvent:
        """創建工具調用事件"""
        return ExecutionEvent(
            event_type=ExecutionEventType.TOOL_CALL,
            session_id=session_id,
            execution_id=execution_id,
            tool_call=ToolCallInfo(
                id=tool_call_id,
                name=tool_name,
                arguments=arguments,
                requires_approval=requires_approval,
            ),
            metadata=metadata,
        )

    @staticmethod
    def tool_result(
        session_id: str,
        execution_id: str,
        tool_call_id: str,
        tool_name: str,
        result: Any,
        success: bool = True,
        error_message: Optional[str] = None,
        **metadata
    ) -> ExecutionEvent:
        """創建工具結果事件"""
        return ExecutionEvent(
            event_type=ExecutionEventType.TOOL_RESULT,
            session_id=session_id,
            execution_id=execution_id,
            tool_result=ToolResultInfo(
                tool_call_id=tool_call_id,
                name=tool_name,
                result=result,
                success=success,
                error_message=error_message,
            ),
            metadata=metadata,
        )

    @staticmethod
    def approval_required(
        session_id: str,
        execution_id: str,
        approval_request_id: str,
        tool_call_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        **metadata
    ) -> ExecutionEvent:
        """創建需要審批事件"""
        return ExecutionEvent(
            event_type=ExecutionEventType.APPROVAL_REQUIRED,
            session_id=session_id,
            execution_id=execution_id,
            approval_request_id=approval_request_id,
            tool_call=ToolCallInfo(
                id=tool_call_id,
                name=tool_name,
                arguments=arguments,
                requires_approval=True,
            ),
            metadata=metadata,
        )

    @staticmethod
    def approval_response(
        session_id: str,
        execution_id: str,
        approval_request_id: str,
        approved: bool,
        feedback: Optional[str] = None,
        **metadata
    ) -> ExecutionEvent:
        """創建審批回應事件"""
        return ExecutionEvent(
            event_type=ExecutionEventType.APPROVAL_RESPONSE,
            session_id=session_id,
            execution_id=execution_id,
            approval_request_id=approval_request_id,
            approval_status="approved" if approved else "rejected",
            approval_feedback=feedback,
            metadata=metadata,
        )

    @staticmethod
    def error(
        session_id: str,
        execution_id: str,
        error_message: str,
        error_code: Optional[str] = None,
        **metadata
    ) -> ExecutionEvent:
        """創建錯誤事件"""
        return ExecutionEvent(
            event_type=ExecutionEventType.ERROR,
            session_id=session_id,
            execution_id=execution_id,
            error=error_message,
            error_code=error_code,
            metadata=metadata,
        )

    @staticmethod
    def done(
        session_id: str,
        execution_id: str,
        finish_reason: str = "stop",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        **metadata
    ) -> ExecutionEvent:
        """創建執行完成事件"""
        return ExecutionEvent(
            event_type=ExecutionEventType.DONE,
            session_id=session_id,
            execution_id=execution_id,
            finish_reason=finish_reason,
            usage=UsageInfo(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            metadata=metadata,
        )

    @staticmethod
    def heartbeat(
        session_id: str,
        execution_id: str,
    ) -> ExecutionEvent:
        """創建心跳事件"""
        return ExecutionEvent(
            event_type=ExecutionEventType.HEARTBEAT,
            session_id=session_id,
            execution_id=execution_id,
        )


# =============================================================================
# 原有 SessionEvent 系統
# =============================================================================


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
