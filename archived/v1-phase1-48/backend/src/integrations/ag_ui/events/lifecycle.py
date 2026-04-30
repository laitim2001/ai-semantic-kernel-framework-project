# =============================================================================
# IPA Platform - AG-UI Lifecycle Events
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-4: AG-UI Event Types
#
# Lifecycle events for AG-UI protocol: RunStarted, RunFinished.
# These events mark the beginning and end of an agent run.
#
# Dependencies:
#   - base (AGUIEventType, BaseAGUIEvent, RunFinishReason)
# =============================================================================

from typing import Any, Dict, Literal, Optional

from pydantic import Field

from .base import AGUIEventType, BaseAGUIEvent, RunFinishReason


class RunStartedEvent(BaseAGUIEvent):
    """
    Run 開始事件。

    當 Agent 開始執行時發送此事件，標記一個新的執行週期開始。

    Attributes:
        type: 固定為 RUN_STARTED
        thread_id: 對話線程 ID
        run_id: 本次執行的唯一 ID

    Example:
        >>> event = RunStartedEvent(
        ...     thread_id="thread-123",
        ...     run_id="run-456"
        ... )
        >>> print(event.model_dump_json())
    """

    type: Literal[AGUIEventType.RUN_STARTED] = Field(
        default=AGUIEventType.RUN_STARTED,
        description="事件類型",
    )
    thread_id: str = Field(..., description="對話線程 ID")
    run_id: str = Field(..., description="本次執行的唯一 ID")


class RunFinishedEvent(BaseAGUIEvent):
    """
    Run 結束事件。

    當 Agent 執行完成時發送此事件，標記執行週期結束。
    包含執行結果摘要和結束原因。

    Attributes:
        type: 固定為 RUN_FINISHED
        thread_id: 對話線程 ID
        run_id: 本次執行的唯一 ID
        finish_reason: 結束原因 (complete, error, cancelled, timeout)
        error: 錯誤訊息 (當 finish_reason 為 error 時)
        usage: 資源使用統計 (可選)

    Example:
        >>> event = RunFinishedEvent(
        ...     thread_id="thread-123",
        ...     run_id="run-456",
        ...     finish_reason=RunFinishReason.COMPLETE
        ... )
    """

    type: Literal[AGUIEventType.RUN_FINISHED] = Field(
        default=AGUIEventType.RUN_FINISHED,
        description="事件類型",
    )
    thread_id: str = Field(..., description="對話線程 ID")
    run_id: str = Field(..., description="本次執行的唯一 ID")
    finish_reason: RunFinishReason = Field(
        default=RunFinishReason.COMPLETE,
        description="結束原因",
    )
    error: Optional[str] = Field(
        default=None,
        description="錯誤訊息 (當 finish_reason 為 error 時)",
    )
    usage: Optional[Dict[str, Any]] = Field(
        default=None,
        description="資源使用統計 (tokens, duration 等)",
    )
