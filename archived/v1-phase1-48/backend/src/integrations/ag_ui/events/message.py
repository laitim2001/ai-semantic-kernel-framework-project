# =============================================================================
# IPA Platform - AG-UI Text Message Events
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-4: AG-UI Event Types
#
# Text message events for AG-UI protocol: TextMessageStart, TextMessageContent,
# TextMessageEnd. These events handle streaming text responses from agents.
#
# Dependencies:
#   - base (AGUIEventType, BaseAGUIEvent)
# =============================================================================

from typing import Literal, Optional

from pydantic import Field

from .base import AGUIEventType, BaseAGUIEvent


class TextMessageStartEvent(BaseAGUIEvent):
    """
    文字訊息開始事件。

    當 Agent 開始生成文字回應時發送此事件，標記一個新訊息的開始。

    Attributes:
        type: 固定為 TEXT_MESSAGE_START
        message_id: 訊息唯一 ID
        role: 訊息角色 (assistant, user, system)

    Example:
        >>> event = TextMessageStartEvent(
        ...     message_id="msg-123",
        ...     role="assistant"
        ... )
        >>> print(event.model_dump_json())
    """

    type: Literal[AGUIEventType.TEXT_MESSAGE_START] = Field(
        default=AGUIEventType.TEXT_MESSAGE_START,
        description="事件類型",
    )
    message_id: str = Field(..., description="訊息唯一 ID")
    role: str = Field(default="assistant", description="訊息角色 (assistant, user, system)")


class TextMessageContentEvent(BaseAGUIEvent):
    """
    文字訊息內容事件。

    當 Agent 生成文字內容時持續發送此事件，用於串流輸出文字。
    每個事件包含一小段增量文字 (delta)。

    Attributes:
        type: 固定為 TEXT_MESSAGE_CONTENT
        message_id: 訊息唯一 ID
        delta: 增量文字內容

    Example:
        >>> event = TextMessageContentEvent(
        ...     message_id="msg-123",
        ...     delta="Hello, "
        ... )
        >>> # 後續事件
        >>> event2 = TextMessageContentEvent(
        ...     message_id="msg-123",
        ...     delta="how can I help you?"
        ... )
    """

    type: Literal[AGUIEventType.TEXT_MESSAGE_CONTENT] = Field(
        default=AGUIEventType.TEXT_MESSAGE_CONTENT,
        description="事件類型",
    )
    message_id: str = Field(..., description="訊息唯一 ID")
    delta: str = Field(..., description="增量文字內容")


class TextMessageEndEvent(BaseAGUIEvent):
    """
    文字訊息結束事件。

    當 Agent 完成文字回應生成時發送此事件，標記訊息結束。

    Attributes:
        type: 固定為 TEXT_MESSAGE_END
        message_id: 訊息唯一 ID

    Example:
        >>> event = TextMessageEndEvent(message_id="msg-123")
        >>> print(event.model_dump_json())
    """

    type: Literal[AGUIEventType.TEXT_MESSAGE_END] = Field(
        default=AGUIEventType.TEXT_MESSAGE_END,
        description="事件類型",
    )
    message_id: str = Field(..., description="訊息唯一 ID")
