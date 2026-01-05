# =============================================================================
# IPA Platform - AG-UI Event Converters
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-2: HybridEventBridge
#
# Event converters for transforming Hybrid internal events to AG-UI standard
# events. Provides conversion methods for all event types defined in AG-UI
# protocol.
#
# Dependencies:
#   - AG-UI Events (src.integrations.ag_ui.events)
#   - HybridResultV2 (src.integrations.hybrid.orchestrator_v2)
# =============================================================================

import json
import logging
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from src.integrations.ag_ui.events import (
    AGUIEventType,
    BaseAGUIEvent,
    RunFinishReason,
    RunFinishedEvent,
    RunStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
    ToolCallStatus,
    StateDeltaEvent,
    StateSnapshotEvent,
    CustomEvent,
)

if TYPE_CHECKING:
    from src.integrations.hybrid.orchestrator_v2 import HybridResultV2
    from src.integrations.hybrid.execution import ToolExecutionResult

logger = logging.getLogger(__name__)


class HybridEventType(str, Enum):
    """
    Hybrid 內部事件類型枚舉。

    定義所有 Hybrid Orchestrator 可能產生的內部事件類型。
    這些事件將被轉換為對應的 AG-UI 事件。
    """

    # 執行生命週期
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"

    # 訊息事件
    MESSAGE_START = "message_start"
    MESSAGE_CHUNK = "message_chunk"
    MESSAGE_END = "message_end"

    # 工具調用事件
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_ARGS = "tool_call_args"
    TOOL_CALL_END = "tool_call_end"

    # 狀態事件
    STATE_SNAPSHOT = "state_snapshot"
    STATE_DELTA = "state_delta"

    # 自定義事件
    CUSTOM = "custom"


@dataclass
class HybridEvent:
    """
    Hybrid 內部事件數據類。

    Attributes:
        type: 事件類型
        data: 事件數據
        thread_id: 對話線程 ID
        run_id: 執行 ID
        message_id: 訊息 ID (適用於訊息事件)
        tool_call_id: 工具調用 ID (適用於工具事件)
    """

    type: HybridEventType
    data: Dict[str, Any]
    thread_id: Optional[str] = None
    run_id: Optional[str] = None
    message_id: Optional[str] = None
    tool_call_id: Optional[str] = None


class EventConverters:
    """
    AG-UI 事件轉換器。

    將 Hybrid 內部事件轉換為 AG-UI 協議標準事件。
    支持所有 AG-UI 事件類型的轉換。

    Example:
        >>> converters = EventConverters()
        >>> event = converters.to_run_started("thread-123", "run-456")
        >>> print(event.model_dump_json())
    """

    # Event type mapping from Hybrid to AG-UI
    EVENT_MAPPING = {
        HybridEventType.EXECUTION_STARTED: AGUIEventType.RUN_STARTED,
        HybridEventType.EXECUTION_COMPLETED: AGUIEventType.RUN_FINISHED,
        HybridEventType.MESSAGE_START: AGUIEventType.TEXT_MESSAGE_START,
        HybridEventType.MESSAGE_CHUNK: AGUIEventType.TEXT_MESSAGE_CONTENT,
        HybridEventType.MESSAGE_END: AGUIEventType.TEXT_MESSAGE_END,
        HybridEventType.TOOL_CALL_START: AGUIEventType.TOOL_CALL_START,
        HybridEventType.TOOL_CALL_ARGS: AGUIEventType.TOOL_CALL_ARGS,
        HybridEventType.TOOL_CALL_END: AGUIEventType.TOOL_CALL_END,
        HybridEventType.STATE_SNAPSHOT: AGUIEventType.STATE_SNAPSHOT,
        HybridEventType.STATE_DELTA: AGUIEventType.STATE_DELTA,
        HybridEventType.CUSTOM: AGUIEventType.CUSTOM,
    }

    def __init__(
        self,
        *,
        chunk_size: int = 100,
        include_metadata: bool = True,
    ):
        """
        Initialize EventConverters.

        Args:
            chunk_size: Size of text chunks for streaming (characters)
            include_metadata: Whether to include metadata in events
        """
        self._chunk_size = chunk_size
        self._include_metadata = include_metadata

    @property
    def chunk_size(self) -> int:
        """Get chunk size for text streaming."""
        return self._chunk_size

    # =========================================================================
    # Lifecycle Events
    # =========================================================================

    def to_run_started(
        self,
        thread_id: str,
        run_id: str,
    ) -> RunStartedEvent:
        """
        Create a RunStartedEvent.

        Args:
            thread_id: Thread ID
            run_id: Run ID

        Returns:
            RunStartedEvent instance
        """
        return RunStartedEvent(
            thread_id=thread_id,
            run_id=run_id,
        )

    def to_run_finished(
        self,
        thread_id: str,
        run_id: str,
        *,
        success: bool = True,
        error: Optional[str] = None,
        usage: Optional[Dict[str, Any]] = None,
    ) -> RunFinishedEvent:
        """
        Create a RunFinishedEvent.

        Args:
            thread_id: Thread ID
            run_id: Run ID
            success: Whether execution was successful
            error: Error message if failed
            usage: Usage statistics (tokens, duration, etc.)

        Returns:
            RunFinishedEvent instance
        """
        if success:
            finish_reason = RunFinishReason.COMPLETE
        elif error and "timeout" in error.lower():
            finish_reason = RunFinishReason.TIMEOUT
        elif error and "cancel" in error.lower():
            finish_reason = RunFinishReason.CANCELLED
        else:
            finish_reason = RunFinishReason.ERROR

        return RunFinishedEvent(
            thread_id=thread_id,
            run_id=run_id,
            finish_reason=finish_reason,
            error=error if not success else None,
            usage=usage,
        )

    # =========================================================================
    # Text Message Events
    # =========================================================================

    def to_text_message_start(
        self,
        message_id: str,
        *,
        role: str = "assistant",
    ) -> TextMessageStartEvent:
        """
        Create a TextMessageStartEvent.

        Args:
            message_id: Message ID
            role: Message role (assistant, user, system)

        Returns:
            TextMessageStartEvent instance
        """
        return TextMessageStartEvent(
            message_id=message_id,
            role=role,
        )

    def to_text_message_content(
        self,
        message_id: str,
        delta: str,
    ) -> TextMessageContentEvent:
        """
        Create a TextMessageContentEvent.

        Args:
            message_id: Message ID
            delta: Text content delta

        Returns:
            TextMessageContentEvent instance
        """
        return TextMessageContentEvent(
            message_id=message_id,
            delta=delta,
        )

    def to_text_message_end(
        self,
        message_id: str,
    ) -> TextMessageEndEvent:
        """
        Create a TextMessageEndEvent.

        Args:
            message_id: Message ID

        Returns:
            TextMessageEndEvent instance
        """
        return TextMessageEndEvent(
            message_id=message_id,
        )

    def content_to_chunks(
        self,
        content: str,
        message_id: str,
    ) -> List[TextMessageContentEvent]:
        """
        Split content into chunks and create TextMessageContentEvents.

        Args:
            content: Full text content
            message_id: Message ID

        Returns:
            List of TextMessageContentEvent instances
        """
        if not content:
            return []

        events = []
        for i in range(0, len(content), self._chunk_size):
            chunk = content[i : i + self._chunk_size]
            events.append(
                self.to_text_message_content(message_id, chunk)
            )
        return events

    # =========================================================================
    # Tool Call Events
    # =========================================================================

    def to_tool_call_start(
        self,
        tool_call_id: str,
        tool_name: str,
        *,
        parent_message_id: Optional[str] = None,
    ) -> ToolCallStartEvent:
        """
        Create a ToolCallStartEvent.

        Args:
            tool_call_id: Tool call ID
            tool_name: Name of the tool
            parent_message_id: Parent message ID for association

        Returns:
            ToolCallStartEvent instance
        """
        return ToolCallStartEvent(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            parent_message_id=parent_message_id,
        )

    def to_tool_call_args(
        self,
        tool_call_id: str,
        args: Dict[str, Any],
    ) -> ToolCallArgsEvent:
        """
        Create a ToolCallArgsEvent.

        Args:
            tool_call_id: Tool call ID
            args: Tool arguments

        Returns:
            ToolCallArgsEvent instance
        """
        # Serialize arguments to JSON string
        args_json = json.dumps(args, ensure_ascii=False)
        return ToolCallArgsEvent(
            tool_call_id=tool_call_id,
            delta=args_json,
        )

    def to_tool_call_end(
        self,
        tool_call_id: str,
        *,
        success: bool = True,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> ToolCallEndEvent:
        """
        Create a ToolCallEndEvent.

        Args:
            tool_call_id: Tool call ID
            success: Whether tool call was successful
            result: Tool execution result
            error: Error message if failed

        Returns:
            ToolCallEndEvent instance
        """
        status = ToolCallStatus.SUCCESS if success else ToolCallStatus.ERROR
        return ToolCallEndEvent(
            tool_call_id=tool_call_id,
            status=status,
            result=result if success else None,
            error=error if not success else None,
        )

    # =========================================================================
    # State Events
    # =========================================================================

    def to_state_snapshot(
        self,
        state: Dict[str, Any],
    ) -> StateSnapshotEvent:
        """
        Create a StateSnapshotEvent.

        Args:
            state: Full state snapshot

        Returns:
            StateSnapshotEvent instance
        """
        return StateSnapshotEvent(snapshot=state)

    def to_state_delta(
        self,
        delta: List[Dict[str, Any]],
    ) -> StateDeltaEvent:
        """
        Create a StateDeltaEvent.

        Args:
            delta: State changes in JSON Patch format

        Returns:
            StateDeltaEvent instance
        """
        return StateDeltaEvent(delta=delta)

    # =========================================================================
    # Custom Events
    # =========================================================================

    def to_custom_event(
        self,
        name: str,
        value: Any,
    ) -> CustomEvent:
        """
        Create a CustomEvent.

        Args:
            name: Custom event name
            value: Custom event value

        Returns:
            CustomEvent instance
        """
        return CustomEvent(name=name, value=value)

    # =========================================================================
    # Generic Conversion
    # =========================================================================

    def convert(
        self,
        hybrid_event: HybridEvent,
    ) -> Optional[BaseAGUIEvent]:
        """
        Convert a Hybrid event to an AG-UI event.

        Args:
            hybrid_event: HybridEvent to convert

        Returns:
            Corresponding AG-UI event, or None if conversion not possible
        """
        try:
            event_type = hybrid_event.type
            data = hybrid_event.data

            if event_type == HybridEventType.EXECUTION_STARTED:
                return self.to_run_started(
                    thread_id=hybrid_event.thread_id or data.get("thread_id", ""),
                    run_id=hybrid_event.run_id or data.get("run_id", ""),
                )

            elif event_type == HybridEventType.EXECUTION_COMPLETED:
                return self.to_run_finished(
                    thread_id=hybrid_event.thread_id or data.get("thread_id", ""),
                    run_id=hybrid_event.run_id or data.get("run_id", ""),
                    success=data.get("success", True),
                    error=data.get("error"),
                    usage=data.get("usage"),
                )

            elif event_type == HybridEventType.MESSAGE_START:
                return self.to_text_message_start(
                    message_id=hybrid_event.message_id or data.get("message_id", ""),
                    role=data.get("role", "assistant"),
                )

            elif event_type == HybridEventType.MESSAGE_CHUNK:
                return self.to_text_message_content(
                    message_id=hybrid_event.message_id or data.get("message_id", ""),
                    delta=data.get("delta", ""),
                )

            elif event_type == HybridEventType.MESSAGE_END:
                return self.to_text_message_end(
                    message_id=hybrid_event.message_id or data.get("message_id", ""),
                )

            elif event_type == HybridEventType.TOOL_CALL_START:
                return self.to_tool_call_start(
                    tool_call_id=hybrid_event.tool_call_id or data.get("tool_call_id", ""),
                    tool_name=data.get("tool_name", ""),
                    parent_message_id=data.get("parent_message_id"),
                )

            elif event_type == HybridEventType.TOOL_CALL_ARGS:
                return self.to_tool_call_args(
                    tool_call_id=hybrid_event.tool_call_id or data.get("tool_call_id", ""),
                    args=data.get("args", {}),
                )

            elif event_type == HybridEventType.TOOL_CALL_END:
                return self.to_tool_call_end(
                    tool_call_id=hybrid_event.tool_call_id or data.get("tool_call_id", ""),
                    success=data.get("success", True),
                    result=data.get("result"),
                    error=data.get("error"),
                )

            elif event_type == HybridEventType.STATE_SNAPSHOT:
                return self.to_state_snapshot(
                    state=data.get("state", {}),
                )

            elif event_type == HybridEventType.STATE_DELTA:
                return self.to_state_delta(
                    delta=data.get("delta", []),
                )

            elif event_type == HybridEventType.CUSTOM:
                return self.to_custom_event(
                    name=data.get("name", "custom"),
                    value=data.get("value"),
                )

            else:
                logger.warning(f"Unknown hybrid event type: {event_type}")
                return None

        except Exception as e:
            logger.error(f"Failed to convert hybrid event: {e}")
            return None

    def from_result(
        self,
        result: "HybridResultV2",
        *,
        thread_id: str,
        run_id: str,
        message_id: Optional[str] = None,
    ) -> List[BaseAGUIEvent]:
        """
        Convert a HybridResultV2 to a sequence of AG-UI events.

        Generates events for:
        - RUN_STARTED
        - TEXT_MESSAGE_START
        - TEXT_MESSAGE_CONTENT (chunked)
        - TOOL_CALL events (for each tool result)
        - TEXT_MESSAGE_END
        - RUN_FINISHED

        Args:
            result: HybridResultV2 from orchestrator
            thread_id: Thread ID
            run_id: Run ID
            message_id: Optional message ID (generated if not provided)

        Returns:
            List of AG-UI events in execution order
        """
        events: List[BaseAGUIEvent] = []
        msg_id = message_id or f"msg-{uuid.uuid4().hex[:8]}"

        # 1. RUN_STARTED (already sent by bridge, so we skip it here)
        # events.append(self.to_run_started(thread_id, run_id))

        # 2. TEXT_MESSAGE_START
        events.append(self.to_text_message_start(msg_id, role="assistant"))

        # 3. TEXT_MESSAGE_CONTENT (chunked)
        if result.content:
            content_events = self.content_to_chunks(result.content, msg_id)
            events.extend(content_events)

        # 4. TOOL_CALL events (from tool_results)
        for tool_result in result.tool_results:
            tool_call_id = f"call-{uuid.uuid4().hex[:8]}"

            # Tool call start
            events.append(
                self.to_tool_call_start(
                    tool_call_id=tool_call_id,
                    tool_name=tool_result.tool_name,
                    parent_message_id=msg_id,
                )
            )

            # Tool call args (if available)
            if hasattr(tool_result, "arguments") and tool_result.arguments:
                events.append(
                    self.to_tool_call_args(
                        tool_call_id=tool_call_id,
                        args=tool_result.arguments,
                    )
                )

            # Tool call end
            events.append(
                self.to_tool_call_end(
                    tool_call_id=tool_call_id,
                    success=tool_result.success,
                    result=tool_result.result if tool_result.success else None,
                    error=tool_result.error if not tool_result.success else None,
                )
            )

        # 5. TEXT_MESSAGE_END
        events.append(self.to_text_message_end(msg_id))

        # 6. RUN_FINISHED (sent by bridge after yielding all events)
        # Included here for completeness
        usage = None
        if self._include_metadata:
            usage = {
                "tokens_used": result.tokens_used,
                "duration_ms": result.duration * 1000,
                "framework": result.framework_used,
                "mode": result.execution_mode.value if result.execution_mode else None,
            }

        events.append(
            self.to_run_finished(
                thread_id=thread_id,
                run_id=run_id,
                success=result.success,
                error=result.error,
                usage=usage,
            )
        )

        return events


def create_converters(
    *,
    chunk_size: int = 100,
    include_metadata: bool = True,
) -> EventConverters:
    """
    Factory function to create EventConverters.

    Args:
        chunk_size: Size of text chunks for streaming
        include_metadata: Whether to include metadata in events

    Returns:
        Configured EventConverters instance
    """
    return EventConverters(
        chunk_size=chunk_size,
        include_metadata=include_metadata,
    )
