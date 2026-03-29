# Layer 03: AG-UI Protocol

## Identity

- Files: 27 | LOC: 10,329
- Directory: `backend/src/integrations/ag_ui/`
- Phase introduced: 15 (Sprint 58) | Phase last modified: 39 (Sprint 135)

---

## File Inventory

| File | LOC | Purpose | Key Classes / Functions |
|------|-----|---------|------------------------|
| `__init__.py` | 111 | Package root re-export | — |
| `bridge.py` | 1,079 | Core SSE bridge connecting HybridOrchestratorV2 to AG-UI | `HybridEventBridge`, `RunAgentInput`, `BridgeConfig`, `create_bridge` |
| `mediator_bridge.py` | 191 | Phase 39 alternate bridge for OrchestratorMediator | `MediatorEventBridge`, `EVENT_MAP` |
| `converters.py` | 690 | Converts Hybrid internal events → AG-UI events | `EventConverters`, `HybridEvent`, `HybridEventType`, `create_converters` |
| `sse_buffer.py` | 108 | Redis-backed SSE reconnection buffer | `SSEEventBuffer` |
| `events/__init__.py` | 76 | Events sub-package exports | — |
| `events/base.py` | 115 | Base class + AGUIEventType enum + RunFinishReason | `AGUIEventType`, `BaseAGUIEvent`, `RunFinishReason` |
| `events/lifecycle.py` | 88 | Run lifecycle events | `RunStartedEvent`, `RunFinishedEvent` |
| `events/message.py` | 99 | Text streaming events | `TextMessageStartEvent`, `TextMessageContentEvent`, `TextMessageEndEvent` |
| `events/tool.py` | 146 | Tool call events | `ToolCallStartEvent`, `ToolCallArgsEvent`, `ToolCallEndEvent`, `ToolCallStatus` |
| `events/state.py` | 168 | State sync events + Custom event | `StateSnapshotEvent`, `StateDeltaEvent`, `StateDeltaItem`, `StateDeltaOperation`, `CustomEvent` |
| `events/progress.py` | 422 | Sprint 69 step-progress extension | `SubStep`, `SubStepStatus`, `StepProgressPayload`, `StepProgressTracker`, `create_step_progress_event`, `emit_step_progress` |
| `thread/__init__.py` | 60 | Thread sub-package exports | — |
| `thread/models.py` | 266 | Thread + Message data models | `AGUIThread`, `AGUIMessage`, `AGUIThreadSchema`, `AGUIMessageSchema`, `ThreadStatus`, `MessageRole` |
| `thread/storage.py` | 378 | Storage interfaces + in-memory impls | `ThreadCache`, `ThreadRepository`, `InMemoryThreadRepository`, `InMemoryCache`, `CacheProtocol`, `RepositoryProtocol` |
| `thread/manager.py` | 471 | Thread lifecycle management | `ThreadManager` |
| `thread/redis_storage.py` | 275 | Sprint 119 Redis-backed storage | `RedisCacheBackend`, `RedisThreadRepository` |
| `features/__init__.py` | 82 | Features sub-package exports | — |
| `features/agentic_chat.py` | 543 | Sprint 59-1: Real-time streaming chat | `AgenticChatHandler`, `ChatSession`, `ChatMessage`, `ChatConfig`, `ChatRole`, `create_chat_handler` |
| `features/tool_rendering.py` | 659 | Sprint 59-2: Tool result formatting | `ToolRenderingHandler`, `ToolCall`, `FormattedResult`, `ToolRenderingConfig`, `ResultType`, `ToolExecutionStatus`, `create_tool_rendering_handler` |
| `features/human_in_loop.py` | 744 | Sprint 59-3: HITL approval workflow | `HITLHandler`, `ApprovalRequest`, `ApprovalStorage`, `ApprovalStatus`, `ToolCallInfo`, `create_hitl_handler`, `get_approval_storage`, `get_hitl_handler` |
| `features/generative_ui.py` | 892 | Sprint 59-4: Workflow progress + mode switch | `GenerativeUIHandler`, `WorkflowProgress`, `WorkflowStep`, `ModeSwitchInfo`, `ModeSwitchReason`, `ProgressStatus`, `create_generative_ui_handler` |
| `features/approval_delegate.py` | 218 | Sprint 111: Bridge HITL → UnifiedApprovalManager | `AGUIApprovalDelegate` |
| `features/advanced/__init__.py` | 54 | Advanced features exports | — |
| `features/advanced/shared_state.py` | 805 | Bi-directional state sync | `SharedStateHandler`, `StateSyncManager`, `StateDiff`, `StateVersion`, `StateConflict`, `DiffOperation`, `ConflictResolutionStrategy`, `create_shared_state_handler` |
| `features/advanced/tool_ui.py` | 879 | Dynamic UI component generation from tool calls | `ToolBasedUIHandler`, `UIComponentDefinition`, `UIComponentSchema`, `FormFieldDefinition`, `TableColumnDefinition`, `ValidationResult`, `UIComponentType`, `ChartType`, `FormFieldType`, `create_tool_ui_handler` |
| `features/advanced/predictive.py` | 710 | Predictive state updates | `PredictiveStateHandler`, `PredictionResult`, `PredictionConfig`, `PredictionStatus`, `PredictionType`, `create_predictive_handler` |

**Total: 27 files, 10,329 LOC**

---

## Internal Architecture

```
backend/src/integrations/ag_ui/
│
├── events/                     [Protocol Definitions]
│   ├── base.py                 AGUIEventType enum (11 types) + BaseAGUIEvent + RunFinishReason
│   ├── lifecycle.py            RunStartedEvent, RunFinishedEvent
│   ├── message.py              TextMessageStart/Content/End events
│   ├── tool.py                 ToolCallStart/Args/End events + ToolCallStatus
│   ├── state.py                StateSnapshot, StateDelta, Custom events
│   └── progress.py             [Sprint 69] SubStep/StepProgress (CustomEvent extension)
│
├── thread/                     [Conversation State]
│   ├── models.py               AGUIThread, AGUIMessage dataclasses + Pydantic schemas
│   ├── storage.py              CacheProtocol + ThreadRepository ABC + InMemory impls
│   ├── redis_storage.py        [Sprint 119] RedisCacheBackend, RedisThreadRepository
│   └── manager.py              ThreadManager (Write-Through: cache + repo)
│
├── bridge.py                   [Primary SSE Bridge — Sprint 58, 67, 75, 101]
│   └── HybridEventBridge       Orchestrates: RunAgentInput → HybridOrchestratorV2 → SSE stream
│                               + heartbeat mechanism (S67-BF-1)
│                               + file attachment support (S75-5)
│                               + SwarmEventEmitter integration (Sprint 101)
│                               + prediction/workflow_progress custom events (S59-4, S60-3)
│
├── mediator_bridge.py          [Alternate Bridge — Sprint 135 Phase 39]
│   └── MediatorEventBridge     OrchestratorMediator → AG-UI SSE
│                               + EVENT_MAP (mediator events → AG-UI types)
│                               + SSEEventBuffer reconnection support
│
├── sse_buffer.py               [Sprint 135] Redis-backed event replay buffer
│
├── converters.py               [Event Transformation]
│   ├── HybridEventType         Internal event types (11 types)
│   ├── HybridEvent             Internal event dataclass
│   └── EventConverters         Hybrid → AG-UI conversion + content_to_chunks()
│                               + from_result() converts HybridResultV2 to event sequence
│
└── features/                   [AG-UI Feature Handlers]
    ├── agentic_chat.py         [S59-1] AgenticChatHandler: streaming chat sessions
    ├── tool_rendering.py       [S59-2] ToolRenderingHandler: result formatting
    ├── human_in_loop.py        [S59-3] HITLHandler + ApprovalStorage
    ├── generative_ui.py        [S59-4] GenerativeUIHandler: workflow progress
    ├── approval_delegate.py    [Sprint 111] AGUIApprovalDelegate → UnifiedApprovalManager
    └── advanced/
        ├── shared_state.py     [Sprint 60] SharedStateHandler + StateSyncManager
        ├── tool_ui.py          [Sprint 60] ToolBasedUIHandler: dynamic UI components
        └── predictive.py       [Sprint 60] PredictiveStateHandler: optimistic updates
```

### Data Flow

```
User HTTP Request (POST /api/v1/ag_ui/run)
    │
    ▼
api/v1/ag_ui/routes.py
    │  uses HybridEventBridge (bridge.py)
    ▼
HybridEventBridge.stream_events(RunAgentInput)
    │
    ├── 1. yield RUN_STARTED (via converters.to_run_started)
    │
    ├── 2. asyncio.Queue + execute_task():
    │       ├── emit prediction_update CustomEvent  [S60-3]
    │       ├── emit workflow_progress CustomEvent  [S59-4]
    │       ├── _build_multimodal_content()         [S75-5]
    │       └── HybridOrchestratorV2.execute(prompt)
    │                   ↓ returns HybridResultV2
    │
    ├── 3. heartbeat_task(): CustomEvent("heartbeat") every 2s [S67-BF-1]
    │
    ├── 4. converters.from_result(HybridResultV2)
    │       → TextMessageStart + TextMessageContent(chunks) + TextMessageEnd
    │       → ToolCallStart + ToolCallArgs + ToolCallEnd (per tool_result)
    │       → RUN_FINISHED
    │
    └── 5. yield each event as SSE string ("data: {...}\n\n")

--- ALTERNATE PATH (Phase 39+) ---

MediatorEventBridge.stream_events(mediator, request)
    │
    ├── 1. yield RUN_STARTED
    ├── 2. mediator.execute(OrchestratorRequest)
    │       → STEP_STARTED/FINISHED for routing
    │       → TEXT_MESSAGE_START + CONTENT(50-char chunks) + END
    └── 3. yield RUN_FINISHED (with processing_time_ms)
```

---

## Event Type Definitions

### AGUIEventType Enum (`events/base.py:21`)

| Enum Member | String Value | Category |
|-------------|-------------|----------|
| `RUN_STARTED` | `"RUN_STARTED"` | Lifecycle |
| `RUN_FINISHED` | `"RUN_FINISHED"` | Lifecycle |
| `TEXT_MESSAGE_START` | `"TEXT_MESSAGE_START"` | Text Message |
| `TEXT_MESSAGE_CONTENT` | `"TEXT_MESSAGE_CONTENT"` | Text Message |
| `TEXT_MESSAGE_END` | `"TEXT_MESSAGE_END"` | Text Message |
| `TOOL_CALL_START` | `"TOOL_CALL_START"` | Tool Call |
| `TOOL_CALL_ARGS` | `"TOOL_CALL_ARGS"` | Tool Call |
| `TOOL_CALL_END` | `"TOOL_CALL_END"` | Tool Call |
| `STATE_SNAPSHOT` | `"STATE_SNAPSHOT"` | State |
| `STATE_DELTA` | `"STATE_DELTA"` | State |
| `CUSTOM` | `"CUSTOM"` | Custom |

### RunFinishReason Enum (`events/base.py:57`)

| Value | Meaning |
|-------|---------|
| `"complete"` | Normal completion |
| `"error"` | Error occurred |
| `"cancelled"` | User cancelled |
| `"timeout"` | Execution timed out |

### BaseAGUIEvent (`events/base.py:74`)

| Field | Type | Description |
|-------|------|-------------|
| `type` | `AGUIEventType` | Event type (required) |
| `timestamp` | `datetime` | UTC timestamp (auto-generated) |

Method: `to_sse() -> str` — formats as `"data: {json}\n\n"`

### Lifecycle Events

**RunStartedEvent** (`events/lifecycle.py:21`)

| Field | Type | Description |
|-------|------|-------------|
| `type` | `Literal[RUN_STARTED]` | Fixed |
| `thread_id` | `str` | Conversation thread ID |
| `run_id` | `str` | Unique run ID |

**RunFinishedEvent** (`events/lifecycle.py:48`)

| Field | Type | Description |
|-------|------|-------------|
| `type` | `Literal[RUN_FINISHED]` | Fixed |
| `thread_id` | `str` | Conversation thread ID |
| `run_id` | `str` | Unique run ID |
| `finish_reason` | `RunFinishReason` | Completion reason |
| `error` | `Optional[str]` | Error message if failed |
| `usage` | `Optional[Dict[str, Any]]` | Token/duration statistics |

### Text Message Events

**TextMessageStartEvent** (`events/message.py:21`)

| Field | Type | Description |
|-------|------|-------------|
| `type` | `Literal[TEXT_MESSAGE_START]` | Fixed |
| `message_id` | `str` | Unique message ID |
| `role` | `str` | Default `"assistant"` |

**TextMessageContentEvent** (`events/message.py:48`)

| Field | Type | Description |
|-------|------|-------------|
| `type` | `Literal[TEXT_MESSAGE_CONTENT]` | Fixed |
| `message_id` | `str` | Unique message ID |
| `delta` | `str` | Incremental text content |

**TextMessageEndEvent** (`events/message.py:80`)

| Field | Type | Description |
|-------|------|-------------|
| `type` | `Literal[TEXT_MESSAGE_END]` | Fixed |
| `message_id` | `str` | Unique message ID |

### Tool Call Events

**ToolCallStartEvent** (`events/tool.py:39`)

| Field | Type | Description |
|-------|------|-------------|
| `type` | `Literal[TOOL_CALL_START]` | Fixed |
| `tool_call_id` | `str` | Unique tool call ID |
| `tool_name` | `str` | Name of tool |
| `parent_message_id` | `Optional[str]` | Associated message ID |

**ToolCallArgsEvent** (`events/tool.py:71`)

| Field | Type | Description |
|-------|------|-------------|
| `type` | `Literal[TOOL_CALL_ARGS]` | Fixed |
| `tool_call_id` | `str` | Tool call ID |
| `delta` | `str` | Incremental JSON args string |

**ToolCallEndEvent** (`events/tool.py:102`)

| Field | Type | Description |
|-------|------|-------------|
| `type` | `Literal[TOOL_CALL_END]` | Fixed |
| `tool_call_id` | `str` | Tool call ID |
| `status` | `ToolCallStatus` | `pending/running/success/error` |
| `result` | `Optional[Dict[str, Any]]` | Execution result |
| `error` | `Optional[str]` | Error message |

### State Events

**StateSnapshotEvent** (`events/state.py:21`)

| Field | Type | Description |
|-------|------|-------------|
| `type` | `Literal[STATE_SNAPSHOT]` | Fixed |
| `snapshot` | `Dict[str, Any]` | Full state object |
| `metadata` | `Dict[str, Any]` | threadId, runId, version etc. |

**StateDeltaEvent** (`events/state.py:105`)

| Field | Type | Description |
|-------|------|-------------|
| `type` | `Literal[STATE_DELTA]` | Fixed |
| `delta` | `List[Dict[str, Any]]` | List of state change operations |

**CustomEvent** (`events/state.py:135`)

| Field | Type | Description |
|-------|------|-------------|
| `type` | `Literal[CUSTOM]` | Fixed |
| `event_name` | `str` | Application-specific name |
| `payload` | `Dict[str, Any]` | Event data |

### Known Custom Event Names (application-level extensions)

| `event_name` | Source | Purpose |
|---|---|---|
| `"step_progress"` | `events/progress.py` | Sprint 69 hierarchical step tracking |
| `"workflow_progress"` | `bridge.py:595` | S59-4 workflow step visualization |
| `"prediction_update"` | `bridge.py:569` | S60-3 optimistic state prediction |
| `"HITL_APPROVAL_REQUIRED"` | `converters.py:601` | Sprint 66 HITL high-risk tool alert |
| `"heartbeat"` | `bridge.py` | S67-BF-1 connection keepalive |
| `"swarm_update"` | `swarm/events/emitter.py` | Sprint 101 swarm worker status |

### StateDeltaOperation (`events/state.py:58`)

| Value | Meaning |
|-------|---------|
| `"set"` | Set value |
| `"delete"` | Delete value |
| `"append"` | Append to array |
| `"increment"` | Numeric increment |

---

## Feature Modules

### features/agentic_chat.py — Sprint 59-1

**Classes:**
- `ChatRole(str, Enum)` — `USER`, `ASSISTANT`, `SYSTEM`
- `ChatMessage` (dataclass) — `message_id`, `role`, `content`, `created_at`, `metadata`
- `ChatConfig` (dataclass) — `max_history`, `chunk_size`, `include_metadata`, `system_prompt`
- `ChatSession` — tracks per-session message history
- `AgenticChatHandler` — manages streaming chat via `HybridEventBridge`

Key methods on `AgenticChatHandler`:
- `handle_message(session_id, user_message) -> AsyncGenerator[str, None]`
- `get_session(session_id) -> Optional[ChatSession]`
- `clear_session(session_id)`

### features/tool_rendering.py — Sprint 59-2

**Classes:**
- `ResultType(str, Enum)` — `JSON`, `TABLE`, `TEXT`, `CODE`, `IMAGE`, `ERROR`
- `ToolExecutionStatus(str, Enum)` — `PENDING`, `RUNNING`, `SUCCESS`, `ERROR`, `CANCELLED`
- `ToolCall` (dataclass) — tool invocation record
- `FormattedResult` (dataclass) — rendering-ready result
- `ToolRenderingConfig` (dataclass) — max output size, formatting options
- `ToolRenderingHandler` — formats raw tool results for UI display

Key methods: `format_result()`, `render_table()`, `render_code()`, `render_json()`

### features/human_in_loop.py — Sprint 59-3

**Classes:**
- `ApprovalStatus(str, Enum)` — `PENDING`, `APPROVED`, `REJECTED`, `TIMEOUT`, `CANCELLED`
- `ToolCallInfo` (dataclass) — `id`, `name`, `arguments`
- `ApprovalRequest` (dataclass) — full approval record with TTL
- `ApprovalStorage` — in-memory store with TTL-based expiry (default 5 min)
- `HITLHandler` — checks `RiskAssessmentEngine`, emits `approval_required` CustomEvents

Key methods on `HITLHandler`:
- `check_and_request_approval(tool_call) -> Optional[ApprovalRequest]`
- `handle_approval_response(request_id, approved) -> ApprovalStatus`
- `wait_for_approval(request_id, timeout) -> ApprovalStatus`

Dependencies: imports `RiskAssessmentEngine`, `RiskLevel` from `src.integrations.hybrid.risk`

### features/generative_ui.py — Sprint 59-4

**Classes:**
- `ProgressStatus(str, Enum)` — `PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED`
- `ModeSwitchReason(str, Enum)` — `USER_REQUEST`, `INTENT_CHANGE`, `ERROR_FALLBACK`, `CAPABILITY_LIMIT`
- `WorkflowStep` (dataclass) — individual step with progress percentage
- `WorkflowProgress` (dataclass) — multi-step workflow tracker
- `ModeSwitchInfo` (dataclass) — mode transition record
- `GenerativeUIHandler` — emits `workflow_progress` and `mode_switch` CustomEvents

### features/approval_delegate.py — Sprint 111

**Class:** `AGUIApprovalDelegate`
- Delegates AG-UI approval operations to `UnifiedApprovalManager`
- Maps `ApprovalSource.AG_UI` for unified tracking

Methods: `create_approval_request()`, `handle_approval_response()`, `get_pending_approvals()`, `get_approval_status()`, `cancel_approval()`

Dependencies: imports from `src.integrations.orchestration.hitl.unified_manager`

### features/advanced/shared_state.py — Sprint 60

**Classes:**
- `DiffOperation(str, Enum)` — `ADD`, `REMOVE`, `REPLACE`, `MOVE`, `COPY`, `TEST`
- `ConflictResolutionStrategy(str, Enum)` — `SERVER_WINS`, `CLIENT_WINS`, `MANUAL`, `MERGE`
- `StateDiff`, `StateVersion`, `StateConflict` — CRDT-style state tracking
- `StateSyncManager` — manages version vectors and conflict detection
- `SharedStateHandler` — bi-directional state sync via `STATE_SNAPSHOT`/`STATE_DELTA` events

### features/advanced/tool_ui.py — Sprint 60

**Classes:**
- `UIComponentType(str, Enum)` — `FORM`, `TABLE`, `CHART`, `CARD`, `BUTTON`, `TEXT`
- `ChartType(str, Enum)` — `LINE`, `BAR`, `PIE`, `SCATTER`
- `FormFieldType(str, Enum)` — `TEXT`, `NUMBER`, `SELECT`, `CHECKBOX`, `DATE`
- `FormFieldDefinition`, `TableColumnDefinition`, `UIComponentSchema`, `UIComponentDefinition`, `ValidationResult`
- `ToolBasedUIHandler` — dynamically generates `CustomEvent` payloads with UI component specs

### features/advanced/predictive.py — Sprint 60

**Classes:**
- `PredictionStatus(str, Enum)` — `PENDING`, `CONFIRMED`, `REJECTED`, `EXPIRED`
- `PredictionType(str, Enum)` — `OPTIMISTIC`, `SPECULATIVE`, `CACHED`
- `PredictionResult` (dataclass) — `prediction_id`, `status`, `confidence`, `predicted_state`
- `PredictionConfig` (dataclass) — confidence threshold, TTL settings
- `PredictiveStateHandler` — emits `prediction_update` CustomEvents before LLM response arrives

### thread/ — Sprint 58 + Sprint 119

**ThreadManager** (`thread/manager.py`) — Write-Through caching pattern:
- `get_or_create(thread_id?) -> AGUIThread`
- `append_message(thread_id, role, content, ...) -> AGUIThread`
- `append_messages(thread_id, messages) -> AGUIThread`
- `update_state(thread_id, state_updates) -> AGUIThread`
- `set_state(thread_id, state) -> AGUIThread`
- `increment_run_count(thread_id) -> int`
- `archive(thread_id) -> AGUIThread`
- `delete(thread_id) -> bool`
- `list_active(limit, offset) -> List[AGUIThread]`
- `get_messages(thread_id, limit?, offset) -> List[AGUIMessage]`
- `get_state(thread_id) -> Dict`
- `clear_messages(thread_id) -> AGUIThread`

**Storage architecture:**
- `CacheProtocol` (Protocol) + `ThreadCache` (Redis-backed, key: `ag_ui:thread:{id}`, TTL: 2h)
- `ThreadRepository` (ABC) + `InMemoryThreadRepository` (dev/test)
- `RedisCacheBackend` (Sprint 119) — implements `CacheProtocol` via `redis.asyncio`
- `RedisThreadRepository` (Sprint 119) — key: `ag_ui:thread_repo:{id}`, status index sets: `ag_ui:thread_repo_status:{status}`, default TTL: 24h

---

## Interfaces Exposed

Other modules import from `ag_ui`:

### `src/api/v1/ag_ui/routes.py`
```python
from src.integrations.ag_ui.bridge import (
    HybridEventBridge, RunAgentInput, BridgeConfig, create_bridge
)
from src.integrations.ag_ui.features.human_in_loop import (
    HITLHandler, ApprovalRequest, ApprovalStatus
)
from src.integrations.ag_ui.events import (
    RunFinishReason, CustomEvent, ...
)
```

### `src/api/v1/ag_ui/dependencies.py`
```python
from src.integrations.ag_ui.bridge import (
    HybridEventBridge, BridgeConfig, create_bridge
)
from src.integrations.ag_ui.features.human_in_loop import (
    get_hitl_handler, get_approval_storage
)
```

### `src/integrations/swarm/events/emitter.py`
```python
from src.integrations.ag_ui.events import CustomEvent
```

---

## Dependencies Consumed

| Imported Module | Imported Symbols | Used In |
|----------------|-----------------|---------|
| `src.integrations.hybrid.orchestrator_v2` | `HybridOrchestratorV2`, `HybridResultV2` | `bridge.py`, `converters.py` |
| `src.integrations.hybrid.intent` | `ExecutionMode` | `bridge.py` |
| `src.integrations.hybrid.risk` | `RiskAssessmentEngine`, `RiskLevel` | `features/human_in_loop.py` |
| `src.integrations.hybrid.risk.models` | `OperationContext`, `RiskAssessment` | `features/human_in_loop.py` |
| `src.integrations.hybrid.execution` | `ToolExecutionResult` | `converters.py` (TYPE_CHECKING) |
| `src.integrations.swarm.events` | `SwarmEventEmitter`, `create_swarm_emitter` | `bridge.py` (lazy import) |
| `src.integrations.orchestration.hitl.unified_manager` | `UnifiedApprovalManager`, `ApprovalRequest`, `ApprovalSource`, `ApprovalPriority` | `features/approval_delegate.py` |
| `src.integrations.hybrid.orchestrator.contracts` | `OrchestratorRequest` | `mediator_bridge.py` (lazy import) |
| `src.domain.files.service` | `get_file_service` | `bridge.py` S75-5 |
| `redis.asyncio` | `Redis`, `RedisError` | `thread/redis_storage.py` |
| `pydantic` | `BaseModel`, `Field` | `events/base.py`, `thread/models.py` |

---

## Known Issues

### Issue 1 — Non-True Token-by-Token Streaming (V8 Issue #AG-01)

**Severity**: HIGH

**Location**: `converters.py:275-299` (`content_to_chunks()`), `bridge.py` (stream_events)

**Description**: `HybridEventBridge` waits for the complete `HybridResultV2` from `HybridOrchestratorV2` before emitting any `TEXT_MESSAGE_CONTENT` events. Text is then split into fixed 100-character chunks and yielded sequentially. This is pseudo-streaming, not real token-by-token streaming.

**Evidence**: `content_to_chunks()` iterates `range(0, len(content), self._chunk_size)` where `chunk_size=100` (default). The `from_result()` method receives the completed `result.content` string.

**Impact**: Perceived latency is high — users see no output until the LLM completes its full response.

**Root Cause**: `HybridOrchestratorV2` does not expose a streaming API; it returns a completed `HybridResultV2` object.

### Issue 2 — MediatorEventBridge Also Uses Chunked Simulation

**Severity**: MEDIUM

**Location**: `mediator_bridge.py:127-133`

**Description**: `MediatorEventBridge` also chunks content into 50-char pieces with `await asyncio.sleep(0.01)` between chunks. Same root cause as Issue 1.

### Issue 3 — ApprovalStorage TTL Not Enforced in Production

**Severity**: MEDIUM

**Location**: `features/human_in_loop.py:157` (`ApprovalStorage`)

**Description**: `ApprovalStorage` is an in-memory dict with TTL tracked by `created_at` timestamps. TTL expiry is only checked on access (`check_expired()`), not via background cleanup. Memory can grow unbounded. Partially superseded by `AGUIApprovalDelegate` (Sprint 111) which uses `UnifiedApprovalManager`, but `HITLHandler` still uses the original `ApprovalStorage` singleton.

### Issue 4 — InMemoryCache Does Not Enforce TTL

**Severity**: LOW

**Location**: `thread/storage.py:341` (`InMemoryCache`)

**Description**: `InMemoryCache._ttls` stores TTL values but never enforces expiry. Items never expire. Documented as "Useful for testing" but used in some non-test contexts.

### Issue 5 — SwarmEventEmitter Default Callback Loses Events

**Severity**: LOW

**Location**: `bridge.py:246` (`_send_custom_event`)

**Description**: The default `_send_custom_event` callback used by `SwarmEventEmitter` only logs the event (`logger.debug`) without enqueuing it into the SSE stream. Swarm events are silently dropped unless the caller overrides the callback.

### Issue 6 — MediatorEventBridge event_loop Warning

**Severity**: LOW

**Location**: `mediator_bridge.py:182`

**Description**: Uses `asyncio.get_event_loop().create_task()` which is deprecated in Python 3.10+.

---

## Phase Evolution

| Phase | Sprint | Change |
|-------|--------|--------|
| Phase 15 | Sprint 58 | **Foundation**: `events/` (11 event types), `thread/` (InMemory), `bridge.py` (HybridEventBridge), `converters.py` |
| Phase 15 | Sprint 59 | **Basic Features**: `features/agentic_chat.py` (S59-1), `tool_rendering.py` (S59-2), `human_in_loop.py` (S59-3), `generative_ui.py` (S59-4) |
| Phase 15 | Sprint 60 | **Advanced Features**: `features/advanced/shared_state.py`, `tool_ui.py`, `predictive.py` |
| Phase 20 | Sprint 66 | **HITL Enhancement**: `converters.py` — added `HITL_APPROVAL_REQUIRED` CustomEvent for `HIGH_RISK_TOOLS = ["Write", "Edit", "MultiEdit", "Bash", "Task"]` |
| Phase 20 | Sprint 67 | **Heartbeat**: `bridge.py` — added `heartbeat_interval=2.0`, heartbeat task via `asyncio.Queue` |
| Phase 21 | Sprint 69 | **Step Progress**: `events/progress.py` — `SubStep`, `StepProgressPayload`, `StepProgressTracker` |
| Phase 22 | Sprint 75 | **File Attachments**: `bridge.py` — `RunAgentInput.file_ids`, `_build_multimodal_content()` |
| Phase 29 | Sprint 101 | **Swarm Integration**: `bridge.py` — `SwarmEventEmitter` integration, `BridgeConfig.enable_swarm_events` |
| Phase 35 | Sprint 111 | **Unified Approval**: `features/approval_delegate.py` — `AGUIApprovalDelegate` → `UnifiedApprovalManager` |
| Phase 35 | Sprint 119 | **Redis Storage**: `thread/redis_storage.py` — `RedisCacheBackend`, `RedisThreadRepository` |
| Phase 39 | Sprint 135 | **Mediator Bridge**: `mediator_bridge.py` + `sse_buffer.py` — alternate bridge for OrchestratorMediator |
