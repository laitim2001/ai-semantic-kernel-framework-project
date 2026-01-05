# =============================================================================
# IPA Platform - AG-UI Tool Call Events
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-4: AG-UI Event Types
#
# Tool call events for AG-UI protocol: ToolCallStart, ToolCallArgs, ToolCallEnd.
# These events handle tool/function calling from agents.
#
# Dependencies:
#   - base (AGUIEventType, BaseAGUIEvent)
# =============================================================================

from enum import Enum
from typing import Any, Dict, Literal, Optional

from pydantic import Field

from .base import AGUIEventType, BaseAGUIEvent


class ToolCallStatus(str, Enum):
    """
    工具調用狀態枚舉。

    Attributes:
        PENDING: 等待執行
        RUNNING: 執行中
        SUCCESS: 執行成功
        ERROR: 執行失敗
    """

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


class ToolCallStartEvent(BaseAGUIEvent):
    """
    工具調用開始事件。

    當 Agent 決定調用工具時發送此事件，標記工具調用的開始。

    Attributes:
        type: 固定為 TOOL_CALL_START
        tool_call_id: 工具調用唯一 ID
        tool_name: 工具名稱
        parent_message_id: 父訊息 ID (可選，用於關聯訊息)

    Example:
        >>> event = ToolCallStartEvent(
        ...     tool_call_id="call-123",
        ...     tool_name="search_documents",
        ...     parent_message_id="msg-456"
        ... )
    """

    type: Literal[AGUIEventType.TOOL_CALL_START] = Field(
        default=AGUIEventType.TOOL_CALL_START,
        description="事件類型",
    )
    tool_call_id: str = Field(..., description="工具調用唯一 ID")
    tool_name: str = Field(..., description="工具名稱")
    parent_message_id: Optional[str] = Field(
        default=None,
        description="父訊息 ID (用於關聯訊息)",
    )


class ToolCallArgsEvent(BaseAGUIEvent):
    """
    工具調用參數事件。

    用於串流傳輸工具調用的參數。對於大型參數，可以分多次發送。

    Attributes:
        type: 固定為 TOOL_CALL_ARGS
        tool_call_id: 工具調用唯一 ID
        delta: 增量參數 JSON 字串

    Example:
        >>> event = ToolCallArgsEvent(
        ...     tool_call_id="call-123",
        ...     delta='{"query": "IPA Platform"'
        ... )
        >>> # 後續事件
        >>> event2 = ToolCallArgsEvent(
        ...     tool_call_id="call-123",
        ...     delta=', "limit": 10}'
        ... )
    """

    type: Literal[AGUIEventType.TOOL_CALL_ARGS] = Field(
        default=AGUIEventType.TOOL_CALL_ARGS,
        description="事件類型",
    )
    tool_call_id: str = Field(..., description="工具調用唯一 ID")
    delta: str = Field(..., description="增量參數 JSON 字串")


class ToolCallEndEvent(BaseAGUIEvent):
    """
    工具調用結束事件。

    當工具調用完成時發送此事件，包含執行結果或錯誤訊息。

    Attributes:
        type: 固定為 TOOL_CALL_END
        tool_call_id: 工具調用唯一 ID
        status: 調用狀態 (success, error)
        result: 執行結果 (可選)
        error: 錯誤訊息 (當 status 為 error 時)

    Example:
        >>> # 成功情況
        >>> event = ToolCallEndEvent(
        ...     tool_call_id="call-123",
        ...     status=ToolCallStatus.SUCCESS,
        ...     result={"documents": [...]}
        ... )
        >>> # 錯誤情況
        >>> event = ToolCallEndEvent(
        ...     tool_call_id="call-123",
        ...     status=ToolCallStatus.ERROR,
        ...     error="Connection timeout"
        ... )
    """

    type: Literal[AGUIEventType.TOOL_CALL_END] = Field(
        default=AGUIEventType.TOOL_CALL_END,
        description="事件類型",
    )
    tool_call_id: str = Field(..., description="工具調用唯一 ID")
    status: ToolCallStatus = Field(
        default=ToolCallStatus.SUCCESS,
        description="調用狀態",
    )
    result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="執行結果",
    )
    error: Optional[str] = Field(
        default=None,
        description="錯誤訊息 (當 status 為 error 時)",
    )
