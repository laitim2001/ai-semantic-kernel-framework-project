# =============================================================================
# IPA Platform - AG-UI Integration Package
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-2: HybridEventBridge
# S58-3: Thread Manager
# S58-4: AG-UI Event Types
#
# AG-UI (Agent-UI) protocol integration for CopilotKit-compatible
# Agent-to-UI communication via Server-Sent Events (SSE).
#
# Sub-packages:
#   - events: AG-UI protocol event types
#   - thread: Thread management for conversation state
#   - bridge: HybridEventBridge for converting internal events to AG-UI format
#   - converters: Event conversion utilities
# =============================================================================

# Event Types (S58-4)
from .events import (
    AGUIEventType,
    BaseAGUIEvent,
    CustomEvent,
    RunFinishedEvent,
    RunFinishReason,
    RunStartedEvent,
    StateDeltaEvent,
    StateSnapshotEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
    ToolCallStatus,
)

# Thread Management (S58-3)
from .thread import (
    AGUIMessage,
    AGUIMessageSchema,
    AGUIThread,
    AGUIThreadSchema,
    CacheProtocol,
    InMemoryCache,
    InMemoryThreadRepository,
    MessageRole,
    ThreadCache,
    ThreadManager,
    ThreadRepository,
    ThreadStatus,
)

# Bridge & Converters (S58-2)
from .bridge import (
    BridgeConfig,
    HybridEventBridge,
    RunAgentInput,
    create_bridge,
)
from .converters import (
    EventConverters,
    HybridEvent,
    HybridEventType,
    create_converters,
)

__all__ = [
    # Event Types (S58-4)
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
    "CustomEvent",
    # Thread Management (S58-3)
    "ThreadManager",
    "AGUIThread",
    "AGUIMessage",
    "ThreadStatus",
    "MessageRole",
    "AGUIThreadSchema",
    "AGUIMessageSchema",
    "ThreadCache",
    "ThreadRepository",
    "InMemoryThreadRepository",
    "InMemoryCache",
    "CacheProtocol",
    # Bridge & Converters (S58-2)
    "HybridEventBridge",
    "RunAgentInput",
    "BridgeConfig",
    "create_bridge",
    "EventConverters",
    "HybridEventType",
    "HybridEvent",
    "create_converters",
]
