# Phase 3C: AG-UI Protocol Integration Analysis

> Agent C10 | 24 files | ~7,554 LOC | Feature E5 (AG-UI Protocol)
> Base path: `backend/src/integrations/ag_ui/`

---

## 1. Module Architecture Overview

```
ag_ui/
├── __init__.py              # Package exports (111 LOC)
├── bridge.py                # HybridEventBridge — SSE streaming core (1,080 LOC)
├── converters.py            # Event converters: Hybrid -> AG-UI (691 LOC)
├── events/                  # AG-UI event type definitions
│   ├── __init__.py          # Event exports (77 LOC)
│   ├── base.py              # BaseAGUIEvent + AGUIEventType enum (116 LOC)
│   ├── lifecycle.py         # RunStarted, RunFinished (89 LOC)
│   ├── message.py           # TextMessage Start/Content/End (100 LOC)
│   ├── tool.py              # ToolCall Start/Args/End (147 LOC)
│   ├── state.py             # StateSnapshot, StateDelta, Custom (169 LOC)
│   └── progress.py          # StepProgress with sub-steps (423 LOC)
├── thread/                  # Conversation thread management
│   ├── __init__.py          # Thread exports (61 LOC)
│   ├── models.py            # AGUIThread, AGUIMessage, schemas (267 LOC)
│   ├── storage.py           # InMemory + abstract cache/repo (379 LOC)
│   ├── manager.py           # ThreadManager with Write-Through (472 LOC)
│   └── redis_storage.py     # Redis implementations (276 LOC) [Sprint 119]
├── features/                # AG-UI feature handlers
│   ├── __init__.py          # Feature exports (83 LOC)
│   ├── agentic_chat.py      # AgenticChatHandler (544 LOC) [S59-1]
│   ├── tool_rendering.py    # ToolRenderingHandler (660 LOC) [S59-2]
│   ├── human_in_loop.py     # HITLHandler + ApprovalStorage (745 LOC) [S59-3]
│   ├── generative_ui.py     # GenerativeUIHandler (893 LOC) [S59-4]
│   └── advanced/
│       ├── __init__.py      # Advanced feature exports (55 LOC)
│       ├── tool_ui.py       # ToolBasedUIHandler (880 LOC) [S60-1]
│       ├── shared_state.py  # SharedStateHandler (806 LOC) [S60-2]
│       └── predictive.py    # PredictiveStateHandler (711 LOC) [S60-3]
```

**Total**: 24 files, approximately 7,554 lines of code.

---

## 2. Event Types — Full AG-UI Protocol Coverage

### 2.1 AGUIEventType Enum (11 event types)

| Event Type | Category | Pydantic Model | Description |
|-----------|----------|----------------|-------------|
| `RUN_STARTED` | Lifecycle | `RunStartedEvent` | Agent run begins (thread_id, run_id) |
| `RUN_FINISHED` | Lifecycle | `RunFinishedEvent` | Agent run ends (finish_reason, error, usage) |
| `TEXT_MESSAGE_START` | Message | `TextMessageStartEvent` | Message streaming begins (message_id, role) |
| `TEXT_MESSAGE_CONTENT` | Message | `TextMessageContentEvent` | Text chunk delta (message_id, delta) |
| `TEXT_MESSAGE_END` | Message | `TextMessageEndEvent` | Message streaming ends (message_id) |
| `TOOL_CALL_START` | Tool | `ToolCallStartEvent` | Tool invocation begins (tool_call_id, tool_name) |
| `TOOL_CALL_ARGS` | Tool | `ToolCallArgsEvent` | Tool arguments delta (tool_call_id, JSON delta) |
| `TOOL_CALL_END` | Tool | `ToolCallEndEvent` | Tool invocation ends (status, result, error) |
| `STATE_SNAPSHOT` | State | `StateSnapshotEvent` | Full state snapshot (snapshot dict) |
| `STATE_DELTA` | State | `StateDeltaEvent` | Incremental state update (JSON Patch delta) |
| `CUSTOM` | Custom | `CustomEvent` | Extensible events (event_name, payload) |

### 2.2 RunFinishReason Enum

- `COMPLETE` — Normal completion
- `ERROR` — Execution error
- `CANCELLED` — User cancellation
- `TIMEOUT` — Execution timeout

### 2.3 ToolCallStatus Enum

- `PENDING`, `RUNNING`, `SUCCESS`, `ERROR`

### 2.4 BaseAGUIEvent

All events inherit from `BaseAGUIEvent(BaseModel)`:
- `type: AGUIEventType` — Event discriminator
- `timestamp: datetime` — UTC timestamp
- `to_sse() -> str` — Formats as `data: {json}\n\n`

### 2.5 StepProgress Events (Sprint 69)

Sub-step level progress tracking via `CustomEvent`:
- `SubStep` dataclass with `PENDING/RUNNING/COMPLETED/FAILED/SKIPPED` states
- `StepProgressPayload` — step_id, step_name, current/total, substeps
- `StepProgressTracker` — manages step state with throttled emission (max 2/sec)

---

## 3. Converters — Hybrid-to-AG-UI Event Mapping

### 3.1 HybridEventType Enum (Internal Events)

| Internal Event | AG-UI Event |
|---------------|-------------|
| `EXECUTION_STARTED` | `RUN_STARTED` |
| `EXECUTION_COMPLETED` | `RUN_FINISHED` |
| `MESSAGE_START` | `TEXT_MESSAGE_START` |
| `MESSAGE_CHUNK` | `TEXT_MESSAGE_CONTENT` |
| `MESSAGE_END` | `TEXT_MESSAGE_END` |
| `TOOL_CALL_START` | `TOOL_CALL_START` |
| `TOOL_CALL_ARGS` | `TOOL_CALL_ARGS` |
| `TOOL_CALL_END` | `TOOL_CALL_END` |
| `STATE_SNAPSHOT` | `STATE_SNAPSHOT` |
| `STATE_DELTA` | `STATE_DELTA` |
| `CUSTOM` | `CUSTOM` |

### 3.2 EventConverters Class

- **Generic `convert()`** — Dispatches `HybridEvent` to the appropriate factory method
- **`from_result(HybridResultV2)`** — Converts a complete orchestrator result into a sequence of AG-UI events: `TEXT_MESSAGE_START -> TEXT_MESSAGE_CONTENT (chunked) -> TOOL_CALL events -> TEXT_MESSAGE_END -> RUN_FINISHED`
- **`content_to_chunks()`** — Splits text into chunks (default 100 chars) for streaming
- **HITL Integration (Sprint 66)** — High-risk tools (`Write`, `Edit`, `MultiEdit`, `Bash`, `Task`) emit additional `HITL_APPROVAL_REQUIRED` custom events
- **Usage metadata** — Includes `tokens_used`, `duration_ms`, `framework`, `mode` in `RUN_FINISHED`

---

## 4. HybridEventBridge — SSE Streaming Core

### 4.1 Architecture

```
RunAgentInput
    ↓
HybridEventBridge.stream_events()
    ├── emit RUN_STARTED
    ├── start heartbeat_task (async)
    │   ├── heartbeat CustomEvents every 2s
    │   └── check pending HITL approvals
    ├── start execute_task (async)
    │   ├── emit prediction_update (optimistic)
    │   ├── emit workflow_progress (3 steps)
    │   ├── orchestrator.execute()
    │   ├── emit workflow_progress (complete)
    │   └── emit prediction_update (confirmed)
    ├── yield events from asyncio.Queue
    ├── converters.from_result() → TEXT/TOOL events
    └── emit RUN_FINISHED
         ↓
    SSE formatted: "data: {...}\n\n"
```

### 4.2 Key Features

| Feature | Sprint | Description |
|---------|--------|-------------|
| Core SSE streaming | S58-2 | `stream_events()` yields SSE strings, `stream_events_raw()` yields event objects |
| Simulation mode | S58-2 | Mock responses when orchestrator not configured |
| Heartbeat mechanism | S67-BF-1 | 2-second interval heartbeats during execution; checks HITL pending approvals |
| File attachment support | S75-5 | `_build_multimodal_content()` supports images (base64), PDFs, text files |
| Swarm event integration | S101 | `SwarmEventEmitter` with throttling (200ms) and batching (size 5) |
| Workflow progress | S59-4 | 3-step progress events: Preparing -> Processing -> Completed |
| Predictive state | S60-3 | Optimistic state predictions with confirmation/rollback |

### 4.3 RunAgentInput

```python
@dataclass
class RunAgentInput:
    prompt: str
    thread_id: str
    run_id: Optional[str]      # auto-generated if None
    session_id: Optional[str]
    force_mode: Optional[ExecutionMode]
    tools: Optional[List[Dict]]
    max_tokens: Optional[int]
    timeout: Optional[float]
    metadata: Dict[str, Any]
    file_ids: Optional[List[str]]  # Sprint 75
```

### 4.4 BridgeConfig

| Setting | Default | Description |
|---------|---------|-------------|
| `chunk_size` | 100 | Characters per text chunk |
| `include_metadata` | True | Include usage stats in RUN_FINISHED |
| `emit_state_events` | True | Emit STATE_SNAPSHOT/DELTA |
| `emit_custom_events` | True | Emit CUSTOM events |
| `heartbeat_interval` | 2.0s | Heartbeat frequency |
| `enable_swarm_events` | True | Enable Swarm event emitter |
| `swarm_throttle_interval_ms` | 200 | Swarm event throttle |
| `swarm_batch_size` | 5 | Swarm event batch size |

---

## 5. Thread Management

### 5.1 Data Models

**AGUIThread**:
- `thread_id`, `created_at`, `updated_at`
- `messages: List[AGUIMessage]`
- `state: Dict[str, Any]` — Shared state accessible to agents
- `status: ThreadStatus` — `ACTIVE | IDLE | ARCHIVED | DELETED`
- `run_count: int`
- Methods: `add_message()`, `update_state()`, `increment_run_count()`, `archive()`

**AGUIMessage**:
- `message_id`, `role: MessageRole`, `content`
- `tool_calls: List[Dict]`, `tool_call_id: Optional[str]`
- `MessageRole`: `USER | ASSISTANT | SYSTEM | TOOL`

**Pydantic Schemas**: `AGUIThreadSchema`, `AGUIMessageSchema` for API serialization.

### 5.2 Storage Architecture

```
ThreadManager (Write-Through)
    ├── ThreadCache (Redis or InMemory)
    │   ├── key: "ag_ui:thread:{thread_id}"
    │   ├── TTL: 2 hours default
    │   └── CacheProtocol interface
    └── ThreadRepository (Redis or InMemory)
        ├── key: "ag_ui:thread_repo:{thread_id}"
        ├── Status index: "ag_ui:thread_repo_status:{status}" (Redis Set)
        └── All-threads index: "ag_ui:thread_repo_all" (Redis Set)
```

### 5.3 Storage Implementations

| Implementation | Type | Persistence | Sprint |
|---------------|------|-------------|--------|
| `InMemoryCache` | CacheProtocol | None (lost on restart) | S58 |
| `InMemoryThreadRepository` | ThreadRepository | None | S58 |
| `RedisCacheBackend` | CacheProtocol | Redis with TTL | S119 |
| `RedisThreadRepository` | ThreadRepository | Redis with 24h TTL + status indexing | S119 |

### 5.4 ThreadManager Operations

- **`get_or_create(thread_id)`** — Cache-first retrieval, auto-creates if missing
- **`append_message(thread_id, role, content)`** — Adds message, persists Write-Through
- **`update_state(thread_id, updates)`** — Merge state updates
- **`set_state(thread_id, state)`** — Replace state entirely
- **`increment_run_count(thread_id)`** — Track run count
- **`archive(thread_id)`** — Set status to ARCHIVED
- **`delete(thread_id)`** — Remove from cache and repository
- **`list_active(limit, offset)`** — List active threads

---

## 6. Features — Basic (Sprint 59)

### 6.1 Agentic Chat (S59-1, 7 pts)

**AgenticChatHandler** — Streaming conversation handler:
- Manages `ChatSession` instances (in-memory)
- `handle_chat()` — Main entry: creates session -> adds user message -> streams via bridge -> collects assistant response -> adds to history
- `handle_chat_sse()` — Same but yields SSE strings
- `emit_typing_indicator()` — Typing status custom event
- `ChatConfig`: max_history_length=50, default_timeout=300s, stream_chunk_size=100

### 6.2 Tool Rendering (S59-2, 7 pts)

**ToolRenderingHandler** — Result type detection and formatting:
- **Result types**: `TEXT | JSON | TABLE | IMAGE | CODE | ERROR | UNKNOWN`
- **Auto-detection**: Inspects result structure, tool name, content patterns
- **Formatters**: `_format_text()`, `_format_json()`, `_format_table()`, `_format_image()`, `_format_code()`, `_format_error()`
- **Display hints**: `text`, `truncated-text`, `json-tree`, `data-table`, `image`, `code-block`, `error`
- **Config**: max_text_length=10000, max_json_depth=10, max_table_rows=100, image_max_size_kb=5120

### 6.3 Human-in-the-Loop (S59-3, 8 pts)

**HITLHandler** — Risk-based approval workflow:
- Integrates with `RiskAssessmentEngine` for risk scoring
- `check_approval_needed(tool_call)` — Creates `OperationContext`, assesses risk
- `create_approval_event()` — Emits `approval_required` custom event with risk details
- `handle_approval_response()` — Processes approve/reject
- `wait_for_approval()` — Async polling (0.5s intervals)
- `create_approval_resolved_event()` — Emits `approval_resolved` custom event

**ApprovalStorage** — In-memory with TTL:
- `create_pending()` — Creates request with 5-minute default timeout
- `update_status()` — Approve/reject with comment
- `get_pending()` — Filter by session/run, auto-expires timed-out requests
- `cleanup_expired()` — Remove old resolved requests
- Thread-safe with `asyncio.Lock`
- **Singleton pattern**: `get_approval_storage()`, `get_hitl_handler()`

### 6.4 Generative UI (S59-4, 6 pts)

**GenerativeUIHandler** — Progress and mode switch events:
- **Workflow Progress**: `emit_progress_event()`, `emit_step_started()`, `emit_step_completed()`, `emit_step_failed()`
- **Mode Switch**: `emit_mode_switch_event()`, `emit_mode_switch_from_result()`, `emit_mode_switch_started()`, `emit_mode_switch_completed()`
- **Workflow Management**: `start_workflow()`, `get_workflow_progress()`, `complete_workflow()`, `cancel_workflow()`
- **Integration**: Connects to `ModeSwitcher` from hybrid switching module
- **Custom event names**: `workflow_progress`, `mode_switch`
- **Event history**: Keeps last 100 events for debugging

---

## 7. Features — Advanced (Sprint 60)

### 7.1 Tool-based Generative UI (S60-1, 8 pts)

**ToolBasedUIHandler** — Dynamic UI component generation:

| Component Type | Helper Method | Props |
|---------------|---------------|-------|
| `FORM` | `emit_form_component()` | fields, submitLabel, cancelLabel, layout |
| `CHART` | `emit_chart_component()` | chartType (line/bar/pie/area/scatter/doughnut), data, axes |
| `CARD` | `emit_card_component()` | title, subtitle, content, image, icon, actions, footer |
| `TABLE` | `emit_table_component()` | columns, data, pagination, pageSize, sortable, filterable |
| `CUSTOM` | `emit_custom_component()` | componentName, props, children, styles |

- **Schema validation**: Required/optional fields, validators per component type
- **Component lifecycle**: render -> update -> remove via `ui_component` custom events
- **Component registry**: Tracks all emitted components by ID

### 7.2 Shared State (S60-2, 8 pts)

**SharedStateHandler + StateSyncManager**:

- **State diffing**: Recursive comparison with `DiffOperation` (ADD, REMOVE, REPLACE, MOVE)
- **Delta events**: Efficient incremental sync via `StateDeltaEvent`
- **Snapshot events**: Full state sync via `StateSnapshotEvent`
- **Version tracking**: `StateVersion` with version number and timestamp
- **Conflict resolution strategies**: `SERVER_WINS | CLIENT_WINS | LAST_WRITE_WINS | MERGE | MANUAL`
- **State history**: Configurable max_history (default 100) with rollback support
- **Client updates**: `apply_client_update()` merges with conflict detection
- **Rollback**: `rollback_to_version()` restores historical state

### 7.3 Predictive State Updates (S60-3, 6 pts)

**PredictiveStateHandler**:

- **Prediction types**: `OPTIMISTIC` (apply immediately) | `SPECULATIVE` (pattern-based) | `PREFETCH`
- **Prediction status**: `PENDING -> CONFIRMED | ROLLED_BACK | EXPIRED | CONFLICTED`
- **Confidence scoring**: Base confidence adjusted by learned patterns and change complexity
- **Pattern learning**: `_update_pattern_confidence()` — increases on success (+0.02), decreases on failure (-0.1)
- **Conflict detection**: `_check_conflict()` — recursive comparison of predicted vs actual state
- **Auto-rollback**: Configurable auto-rollback on server conflicts
- **Expiration**: Default 30s TTL, auto-rollback on expiry
- **Config**: min_confidence=0.5, max_pending=10 per thread

---

## 8. Protocol Compliance Assessment

### 8.1 AG-UI Protocol Spec Coverage

| AG-UI Feature | Status | Implementation |
|--------------|--------|----------------|
| RUN_STARTED / RUN_FINISHED | Implemented | `lifecycle.py`, `bridge.py` |
| TEXT_MESSAGE_START/CONTENT/END | Implemented | `message.py`, `converters.py` |
| TOOL_CALL_START/ARGS/END | Implemented | `tool.py`, `converters.py` |
| STATE_SNAPSHOT | Implemented | `state.py`, `shared_state.py` |
| STATE_DELTA | Implemented | `state.py`, `shared_state.py` |
| CUSTOM events | Implemented | `state.py`, all feature handlers |
| SSE streaming | Implemented | `bridge.py` — `data: {json}\n\n` format |
| Thread management | Implemented | `thread/` — full CRUD with caching |
| Agentic Chat | Implemented | `features/agentic_chat.py` |
| Tool Rendering | Implemented | `features/tool_rendering.py` |
| Human-in-the-Loop | Implemented | `features/human_in_loop.py` |
| Generative UI | Implemented | `features/generative_ui.py` |
| Tool-based Gen UI | Implemented | `features/advanced/tool_ui.py` |
| Shared State | Implemented | `features/advanced/shared_state.py` |
| Predictive State | Implemented | `features/advanced/predictive.py` |

### 8.2 Feature Count vs Phase 15 Plan

Phase 15 planned **7 core features** for AG-UI. The implementation delivers:

1. Agentic Chat (S59-1)
2. Tool Rendering (S59-2)
3. Human-in-the-Loop (S59-3)
4. Generative UI / Workflow Progress (S59-4)
5. Tool-based Generative UI (S60-1)
6. Shared State (S60-2)
7. Predictive State Updates (S60-3)

**All 7 planned features are implemented.** Additionally, the following enhancements were added in later sprints:

| Enhancement | Sprint | Description |
|------------|--------|-------------|
| HITL tool event enhancement | S66 | High-risk tool detection with `HITL_APPROVAL_REQUIRED` events |
| Heartbeat mechanism | S67-BF-1 | SSE keepalive during long-running operations |
| Step progress tracking | S69 | Sub-step level progress with throttling |
| File attachment support | S75 | Multimodal content (images, PDFs, text files) |
| Swarm event integration | S101 | Agent Swarm SSE events with throttle/batch |
| Redis thread storage | S119 | Production-ready persistent thread storage |

---

## 9. Cross-Module Dependencies

```
ag_ui/bridge.py
    ← hybrid/orchestrator_v2.py  (HybridOrchestratorV2.execute())
    ← hybrid/intent.py           (ExecutionMode)
    ← swarm/events.py            (SwarmEventEmitter)
    ← domain/files/service.py    (FileService for attachments)

ag_ui/converters.py
    ← hybrid/orchestrator_v2.py  (HybridResultV2)
    ← hybrid/execution.py        (ToolExecutionResult)

ag_ui/features/human_in_loop.py
    ← hybrid/risk/               (RiskAssessmentEngine, RiskLevel)

ag_ui/features/generative_ui.py
    ← hybrid/switching/          (ModeSwitcher, SwitchResult, SwitchTrigger)

ag_ui/features/tool_rendering.py
    ← hybrid/execution/          (UnifiedToolExecutor)
```

---

## 10. Key Observations and Findings

### 10.1 Strengths

1. **Complete protocol coverage** — All 11 AG-UI event types implemented with proper Pydantic models and SSE serialization.
2. **Well-structured layering** — Clean separation: events (data models) -> converters (transformation) -> bridge (streaming) -> features (handlers).
3. **Production-ready thread storage** — Both InMemory (dev/test) and Redis (production) implementations with Write-Through caching pattern.
4. **Comprehensive HITL** — Full approval workflow with risk assessment integration, timeout handling, and thread-safe async storage.
5. **Advanced state management** — Shared state with diffing, versioning, conflict resolution, and predictive optimistic updates.
6. **Extensibility** — CustomEvent type enables unlimited extension (heartbeat, workflow_progress, mode_switch, approval_required, ui_component, prediction_update, step_progress, typing_indicator, HITL_APPROVAL_REQUIRED).

### 10.2 Areas for Improvement

1. **ApprovalStorage is in-memory** — The HITL approval storage uses `asyncio.Lock` and in-memory dict. For production multi-instance deployments, this needs a Redis-backed implementation (similar to what was done for ThreadRepository in Sprint 119).
2. **ChatSession storage is in-memory** — `AgenticChatHandler._sessions` dict loses data on restart. No Redis implementation exists.
3. **SharedStateHandler is in-memory** — State, versions, and history are all stored in-memory dicts. No persistent backing store.
4. **PredictiveStateHandler is in-memory** — Predictions, thread mappings, and pattern confidence all lost on restart.
5. **StateDeltaOperation class issue** — `StateDeltaOperation(str)` inherits from `str` but defines class-level constants instead of using `Enum`. This is functional but inconsistent with the rest of the codebase which uses `str, Enum` pattern.
6. **No streaming from orchestrator** — The bridge receives the complete `HybridResultV2` and then simulates streaming by chunking. True token-by-token streaming from the LLM is not implemented.

### 10.3 Custom Event Registry

The following custom event names are used across the codebase:

| Event Name | Source | Purpose |
|-----------|--------|---------|
| `heartbeat` | bridge.py | SSE connection keepalive |
| `workflow_progress` | bridge.py, generative_ui.py | Multi-step progress tracking |
| `prediction_update` | bridge.py, predictive.py | Optimistic state updates |
| `approval_required` | human_in_loop.py, converters.py | HITL approval request |
| `approval_resolved` | human_in_loop.py | HITL approval response |
| `HITL_APPROVAL_REQUIRED` | converters.py | High-risk tool detection |
| `typing_indicator` | agentic_chat.py | Typing status |
| `tool_status` | tool_rendering.py | Tool execution progress |
| `mode_switch` | generative_ui.py | Execution mode transition |
| `step_progress` | progress.py | Sub-step level progress |
| `ui_component` | tool_ui.py | Dynamic UI component render/update/remove |

---

## 11. Summary Statistics

| Metric | Value |
|--------|-------|
| Total files | 24 |
| Total LOC (approx) | ~7,554 |
| AG-UI event types | 11 |
| Custom event names | 11 |
| Feature handlers | 7 (4 basic + 3 advanced) |
| Storage backends | 4 (2 InMemory + 2 Redis) |
| Sprints involved | S58, S59, S60, S66, S67, S69, S75, S101, S119 |
| Pydantic models | 14 |
| Dataclasses | 20+ |
| Factory functions | 8 |
| Protocol compliance | Full (all 7 planned features + 6 enhancements) |
