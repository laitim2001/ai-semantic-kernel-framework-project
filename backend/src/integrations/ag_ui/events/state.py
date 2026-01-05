# =============================================================================
# IPA Platform - AG-UI State Events
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-4: AG-UI Event Types
#
# State events for AG-UI protocol: StateSnapshot, StateDelta, Custom.
# These events handle state synchronization and custom event extensions.
#
# Dependencies:
#   - base (AGUIEventType, BaseAGUIEvent)
# =============================================================================

from typing import Any, Dict, List, Literal, Optional

from pydantic import Field

from .base import AGUIEventType, BaseAGUIEvent


class StateSnapshotEvent(BaseAGUIEvent):
    """
    狀態快照事件。

    發送完整的狀態快照，用於初始化或同步前端狀態。
    通常在連接建立或狀態重置時發送。

    Attributes:
        type: 固定為 STATE_SNAPSHOT
        snapshot: 完整的狀態物件

    Example:
        >>> event = StateSnapshotEvent(
        ...     snapshot={
        ...         "user": {"name": "Alice", "role": "admin"},
        ...         "conversation": {"turn": 5, "context_length": 1024},
        ...         "tools": ["search", "calculate", "generate"]
        ...     }
        ... )
    """

    type: Literal[AGUIEventType.STATE_SNAPSHOT] = Field(
        default=AGUIEventType.STATE_SNAPSHOT,
        description="事件類型",
    )
    snapshot: Dict[str, Any] = Field(
        default_factory=dict,
        description="完整的狀態物件",
    )


class StateDeltaOperation(str):
    """
    狀態變更操作類型。

    用於定義 StateDelta 中的變更操作：
    - set: 設置值
    - delete: 刪除值
    - append: 追加到陣列
    - increment: 數值增加
    """

    SET = "set"
    DELETE = "delete"
    APPEND = "append"
    INCREMENT = "increment"


class StateDeltaItem:
    """
    狀態變更項目。

    表示單一狀態變更操作。

    Attributes:
        path: 狀態路徑 (如 "user.name" 或 "conversation.turn")
        operation: 操作類型
        value: 變更值 (對於 delete 操作可為 None)
    """

    def __init__(
        self,
        path: str,
        operation: str = StateDeltaOperation.SET,
        value: Any = None,
    ):
        self.path = path
        self.operation = operation
        self.value = value

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式。"""
        result = {"path": self.path, "operation": self.operation}
        if self.value is not None:
            result["value"] = self.value
        return result


class StateDeltaEvent(BaseAGUIEvent):
    """
    狀態增量更新事件。

    發送狀態的增量變更，而非完整快照。
    用於高效的狀態同步，減少傳輸數據量。

    Attributes:
        type: 固定為 STATE_DELTA
        delta: 狀態變更列表

    Example:
        >>> event = StateDeltaEvent(
        ...     delta=[
        ...         {"path": "conversation.turn", "operation": "increment", "value": 1},
        ...         {"path": "user.last_active", "operation": "set", "value": "2026-01-05T10:00:00Z"}
        ...     ]
        ... )
    """

    type: Literal[AGUIEventType.STATE_DELTA] = Field(
        default=AGUIEventType.STATE_DELTA,
        description="事件類型",
    )
    delta: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="狀態變更列表",
    )


class CustomEvent(BaseAGUIEvent):
    """
    自定義事件。

    用於擴展 AG-UI 協議，發送應用特定的事件。
    可用於進度更新、通知、自定義 UI 指令等。

    Attributes:
        type: 固定為 CUSTOM
        event_name: 自定義事件名稱
        payload: 事件數據

    Example:
        >>> # 進度更新
        >>> event = CustomEvent(
        ...     event_name="progress_update",
        ...     payload={"step": 3, "total": 5, "message": "Processing data..."}
        ... )
        >>> # 模式切換通知
        >>> event = CustomEvent(
        ...     event_name="mode_switch",
        ...     payload={"from": "workflow", "to": "chat", "reason": "User initiated"}
        ... )
    """

    type: Literal[AGUIEventType.CUSTOM] = Field(
        default=AGUIEventType.CUSTOM,
        description="事件類型",
    )
    event_name: str = Field(..., description="自定義事件名稱")
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="事件數據",
    )
