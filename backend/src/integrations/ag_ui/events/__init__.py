# =============================================================================
# IPA Platform - AG-UI Events Package
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-4: AG-UI Event Types
#
# Package exports for AG-UI protocol events.
# Provides all event types for Agent-UI communication.
#
# Event Categories:
#   - Lifecycle: RunStarted, RunFinished
#   - Text Message: TextMessageStart, TextMessageContent, TextMessageEnd
#   - Tool Call: ToolCallStart, ToolCallArgs, ToolCallEnd
#   - State: StateSnapshot, StateDelta, Custom
# =============================================================================

from .base import AGUIEventType, BaseAGUIEvent, RunFinishReason
from .lifecycle import RunFinishedEvent, RunStartedEvent
from .message import (
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
)
from .state import (
    CustomEvent,
    StateDeltaEvent,
    StateDeltaItem,
    StateDeltaOperation,
    StateSnapshotEvent,
)
from .tool import (
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
    ToolCallStatus,
)

__all__ = [
    # Base
    "AGUIEventType",
    "BaseAGUIEvent",
    "RunFinishReason",
    # Lifecycle Events
    "RunStartedEvent",
    "RunFinishedEvent",
    # Text Message Events
    "TextMessageStartEvent",
    "TextMessageContentEvent",
    "TextMessageEndEvent",
    # Tool Call Events
    "ToolCallStartEvent",
    "ToolCallArgsEvent",
    "ToolCallEndEvent",
    "ToolCallStatus",
    # State Events
    "StateSnapshotEvent",
    "StateDeltaEvent",
    "StateDeltaItem",
    "StateDeltaOperation",
    "CustomEvent",
]
