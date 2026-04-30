# =============================================================================
# IPA Platform - AG-UI Event Base
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-4: AG-UI Event Types
#
# Base classes and enums for AG-UI protocol events.
# Follows CopilotKit AG-UI specification for event-based agent communication.
#
# Dependencies:
#   - pydantic (BaseModel, Field)
# =============================================================================

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AGUIEventType(str, Enum):
    """
    AG-UI 事件類型枚舉。

    定義所有 AG-UI 協議支持的事件類型，用於 Agent-UI 通訊。

    Categories:
        - Lifecycle: RUN_STARTED, RUN_FINISHED
        - Text Message: TEXT_MESSAGE_START, TEXT_MESSAGE_CONTENT, TEXT_MESSAGE_END
        - Tool Call: TOOL_CALL_START, TOOL_CALL_ARGS, TOOL_CALL_END
        - State: STATE_SNAPSHOT, STATE_DELTA
        - Custom: CUSTOM
    """

    # 生命週期事件 (Lifecycle Events)
    RUN_STARTED = "RUN_STARTED"
    RUN_FINISHED = "RUN_FINISHED"

    # 文字訊息事件 (Text Message Events)
    TEXT_MESSAGE_START = "TEXT_MESSAGE_START"
    TEXT_MESSAGE_CONTENT = "TEXT_MESSAGE_CONTENT"
    TEXT_MESSAGE_END = "TEXT_MESSAGE_END"

    # 工具調用事件 (Tool Call Events)
    TOOL_CALL_START = "TOOL_CALL_START"
    TOOL_CALL_ARGS = "TOOL_CALL_ARGS"
    TOOL_CALL_END = "TOOL_CALL_END"

    # 狀態事件 (State Events)
    STATE_SNAPSHOT = "STATE_SNAPSHOT"
    STATE_DELTA = "STATE_DELTA"

    # 自定義事件 (Custom Events)
    CUSTOM = "CUSTOM"


class RunFinishReason(str, Enum):
    """
    Run 結束原因枚舉。

    Attributes:
        COMPLETE: 正常完成
        ERROR: 發生錯誤
        CANCELLED: 用戶取消
        TIMEOUT: 執行超時
    """

    COMPLETE = "complete"
    ERROR = "error"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class BaseAGUIEvent(BaseModel):
    """
    AG-UI 事件基類。

    所有 AG-UI 事件都繼承自此基類，提供共同的字段和序列化行為。

    Attributes:
        type: 事件類型
        timestamp: 事件產生時間 (UTC)

    Example:
        >>> event = BaseAGUIEvent(type=AGUIEventType.RUN_STARTED)
        >>> print(event.model_dump_json())
        {"type": "RUN_STARTED", "timestamp": "2026-01-05T10:00:00Z"}
    """

    type: AGUIEventType = Field(..., description="事件類型")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="事件產生時間 (UTC)",
    )

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat() + "Z" if v else None,
        },
        "use_enum_values": True,
    }

    def to_sse(self) -> str:
        """
        將事件格式化為 SSE (Server-Sent Events) 字串。

        Returns:
            SSE 格式字串: "data: {json}\n\n"

        Example:
            >>> event = BaseAGUIEvent(type=AGUIEventType.RUN_STARTED)
            >>> print(event.to_sse())
            data: {"type": "RUN_STARTED", ...}\n\n
        """
        return f"data: {self.model_dump_json()}\n\n"
