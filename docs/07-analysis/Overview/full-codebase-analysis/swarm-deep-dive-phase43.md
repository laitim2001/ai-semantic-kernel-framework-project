# Swarm System Deep-Dive Inventory for Phase 43 Planning

> Generated: 2026-03-21 | Scope: ALL Swarm-related code across backend + frontend

---

## 1. BACKEND: `backend/src/integrations/swarm/` (7 files)

### 1.1 models.py — Core Data Structures

**Enums:**
| Enum | Values | Line |
|------|--------|------|
| `WorkerType(str, Enum)` | research, writer, designer, reviewer, coordinator, analyst, coder, tester, custom | L15-28 |
| `WorkerStatus(str, Enum)` | pending, running, thinking, tool_calling, completed, failed, cancelled | L31-42 |
| `SwarmMode(str, Enum)` | sequential, parallel, hierarchical | L45-52 |
| `SwarmStatus(str, Enum)` | initializing, running, paused, completed, failed | L55-64 |
| `ToolCallStatus(str, Enum)` | pending, running, completed, failed | L67-72 |

**Dataclasses:**
| Class | Key Fields | Line |
|-------|-----------|------|
| `ToolCallInfo` | tool_id, tool_name, is_mcp, input_params, status, result, error, started_at, completed_at, duration_ms | L76-120 |
| `ThinkingContent` | content, timestamp, token_count | L123-151 |
| `WorkerMessage` | role, content, timestamp, tool_call_id | L154-192 |
| `WorkerExecution` | worker_id, worker_name, worker_type, role, status, progress, current_task, tool_calls[], thinking_contents[], messages[], started_at, completed_at, error, metadata | L195-270 |
| `AgentSwarmStatus` | swarm_id, mode, status, workers[], started_at, completed_at, metadata | L273-340 |

**Computed properties on AgentSwarmStatus:**
- `overall_progress` — average of all workers' progress
- `total_tool_calls` — sum across all workers
- `completed_tool_calls` — sum of completed tool calls
- `to_dict()` / `from_dict()` / `to_json()` / `from_json()` — full serialization

**Status: REAL** — Complete, well-designed data models with full serialization support.

---

### 1.2 tracker.py — SwarmTracker (State Management)

**File:** `backend/src/integrations/swarm/tracker.py`

**Class:** `SwarmTracker` (L43)
- Thread-safe via `threading.RLock`
- In-memory `Dict[str, AgentSwarmStatus]` storage
- Optional Redis persistence (not connected)
- Callbacks: `on_swarm_update`, `on_worker_update`

**Public Methods:**
| Method | Signature | Purpose |
|--------|-----------|---------|
| `create_swarm` | `(swarm_id, mode, metadata?) -> AgentSwarmStatus` | Create new swarm |
| `get_swarm` | `(swarm_id) -> AgentSwarmStatus?` | Get swarm by ID |
| `start_worker` | `(swarm_id, worker_id, worker_name, worker_type, role) -> WorkerExecution` | Register and start worker |
| `update_worker_progress` | `(swarm_id, worker_id, progress, current_task?) -> WorkerExecution` | Update worker progress (0-100) |
| `complete_worker` | `(swarm_id, worker_id, status?, error?) -> WorkerExecution` | Mark worker completed/failed |
| `complete_swarm` | `(swarm_id, status?) -> AgentSwarmStatus` | Mark swarm completed/failed |
| `add_worker_thinking` | `(swarm_id, worker_id, content, token_count?) -> ThinkingContent` | Add thinking block |
| `add_worker_tool_call` | `(swarm_id, worker_id, tool_id, tool_name, is_mcp, input_params) -> ToolCallInfo` | Register tool call |
| `update_tool_call_result` | `(swarm_id, worker_id, tool_id, result?, error?) -> ToolCallInfo` | Complete tool call |
| `add_worker_message` | `(swarm_id, worker_id, role, content) -> WorkerMessage` | Add conversation message |
| `get_worker_by_id` | `(swarm_id, worker_id) -> WorkerExecution?` | Get single worker |

**Singleton pattern:** `get_swarm_tracker()` / `set_swarm_tracker()` module-level functions.

**Custom Exceptions:** `SwarmNotFoundError`, `WorkerNotFoundError`, `ToolCallNotFoundError`

**Status: REAL** — Fully implemented, thread-safe, feature-complete state tracker. Redis persistence coded but not wired.

---

### 1.3 swarm_integration.py — SwarmIntegration (Facade)

**File:** `backend/src/integrations/swarm/swarm_integration.py`

**Class:** `SwarmIntegration` (L28) — Integration layer connecting ClaudeCoordinator to SwarmTracker.

**Constructor:** `(tracker?: SwarmTracker, auto_generate_ids: bool = True)`

**Key Methods:**
| Method | Purpose |
|--------|---------|
| `on_coordination_started(swarm_id, mode, subtasks, metadata?)` | Creates swarm + registers subtask metadata |
| `on_subtask_started(swarm_id, worker_id, worker_name, worker_type, role, task_description?)` | Starts a worker |
| `on_subtask_progress(swarm_id, worker_id, progress, current_task?)` | Updates worker progress |
| `on_subtask_completed(swarm_id, worker_id, status, error?)` | Completes a worker |
| `on_coordination_completed(swarm_id, status?)` | Completes the swarm |
| `on_tool_call(swarm_id, worker_id, tool_id, tool_name, is_mcp, input_params)` | Registers a tool call |
| `on_tool_result(swarm_id, worker_id, tool_id, result?, error?)` | Completes a tool call |
| `on_thinking(swarm_id, worker_id, content, token_count?)` | Adds thinking content |

**Helper:** `_infer_worker_type(name, role) -> WorkerType` — Keyword-based inference from name/role strings.

**Status: REAL** — Complete facade over SwarmTracker. All methods delegate to tracker. No LLM calls.

---

### 1.4 events/ — Event System (SSE)

#### events/types.py — Event Payload Definitions

**File:** `backend/src/integrations/swarm/events/types.py` (Sprint 101)

**Event Names (SwarmEventNames class):**
```
SWARM_CREATED, SWARM_STATUS_UPDATE, SWARM_COMPLETED
WORKER_STARTED, WORKER_PROGRESS, WORKER_THINKING, WORKER_TOOL_CALL, WORKER_MESSAGE, WORKER_COMPLETED
```

**Payload Dataclasses (all have `to_dict()`):**
| Payload | Key Fields |
|---------|-----------|
| `SwarmCreatedPayload` | swarm_id, session_id, mode, workers[], created_at |
| `SwarmStatusUpdatePayload` | swarm_id, session_id, mode, status, total_workers, overall_progress, workers[], metadata |
| `SwarmCompletedPayload` | swarm_id, status, summary, total_duration_ms, completed_at |
| `WorkerStartedPayload` | swarm_id, worker_id, worker_name, worker_type, role, task_description, started_at |
| `WorkerProgressPayload` | swarm_id, worker_id, progress, current_task |
| `WorkerThinkingPayload` | swarm_id, worker_id, content, token_count |
| `WorkerToolCallPayload` | swarm_id, worker_id, tool_call_id, tool_name, is_mcp, input_args, status |
| `WorkerMessagePayload` | swarm_id, worker_id, role, content |
| `WorkerCompletedPayload` | swarm_id, worker_id, status, duration_ms, error |

#### events/emitter.py — SwarmEventEmitter

**File:** `backend/src/integrations/swarm/events/emitter.py` (Sprint 101)

**Class:** `SwarmEventEmitter` (L56) — Converts Swarm state changes into AG-UI CustomEvents.

**Features:**
- Event throttling (configurable interval, default 200ms)
- Batch sending (configurable batch_size, default 5)
- Priority events (immediate send, bypasses throttle)
- Async event queue with background sender task

**Methods:** `emit_swarm_created()`, `emit_swarm_status_update()`, `emit_swarm_completed()`, `emit_worker_started()`, `emit_worker_progress()`, `emit_worker_thinking()`, `emit_worker_tool_call()`, `emit_worker_message()`, `emit_worker_completed()`

**Factory:** `create_swarm_emitter(callback, throttle?, batch_size?) -> SwarmEventEmitter`

**CRITICAL FINDING:** SwarmEventEmitter is fully implemented but **NOT connected** to the SwarmModeHandler execution path. The demo.py SSE uses a polling approach instead, NOT the emitter.

---

### 1.5 `__init__.py` — Public Exports

Exports ALL models, tracker, integration, event types, and emitter. Clean public API.

---

## 2. BACKEND: `backend/src/integrations/hybrid/swarm_mode.py`

### 2.1 SwarmModeHandler (Sprint 116)

**File:** `backend/src/integrations/hybrid/swarm_mode.py`

**Config Dataclass:** `SwarmExecutionConfig` (L37)
- `enabled: bool = True`
- `default_mode: str = "parallel"`
- `max_workers: int = 5`
- `worker_timeout: float = 120.0`
- `complexity_threshold: float = 0.7`
- `min_subtasks: int = 2`
- `from_env()` classmethod reads `SWARM_*` env vars

**Result Dataclasses:**
- `SwarmTaskDecomposition` — should_use_swarm, subtasks[], swarm_mode, reasoning, estimated_workers
- `SwarmExecutionResult` — success, swarm_id, content, error, worker_results[], total_duration, metadata

**Class:** `SwarmModeHandler` (L137)

**Constructor:** `(swarm_integration?, config?, claude_executor?)`

**Analysis Methods:**
| Method | Purpose | Lines |
|--------|---------|-------|
| `analyze_for_swarm(routing_decision, context?)` | Decides if swarm mode should activate | L216-296 |
| `_get_workflow_type(routing_decision)` | Extracts workflow type | L298-311 |
| `_decompose_from_decision(routing_decision)` | Builds subtask list from metadata/sub_intent | L313-359 |
| `_determine_swarm_mode(workflow_type, subtasks)` | Maps workflow to swarm mode | L361-379 |

**Swarm Eligibility:** Only `CONCURRENT` and `MAGENTIC` workflow types are eligible.

**Decision Flow in `analyze_for_swarm()`:**
1. Check feature flag (SWARM_MODE_ENABLED)
2. Check explicit user request (`context.use_swarm`)
3. Check workflow type eligibility
4. Decompose into subtasks, check `min_subtasks` threshold
5. Return `SwarmTaskDecomposition`

**Execution Methods:**
| Method | Purpose | Lines |
|--------|---------|-------|
| `execute_swarm(intent, decomposition, routing_decision, session_id?, timeout?)` | Main execution entry | L385-499 |
| `_execute_all_workers(swarm_id, subtasks, intent, integration, timeout)` | Runs workers **SEQUENTIALLY** (even in parallel mode!) | L501-554 |
| `_execute_single_worker(...)` | Single worker with error handling | L556-622 |
| `_execute_worker_task(...)` | **ACTUAL EXECUTION** | L624-692 |
| `_aggregate_worker_results(worker_results, intent)` | String concatenation of results | L698-736 |

### CRITICAL: `_execute_worker_task()` (L624-692)

This is the core execution logic:

```python
if self._claude_executor:
    # REAL: Calls claude_executor with prompt + intent
    result = await asyncio.wait_for(
        self._claude_executor(
            prompt=f"Execute subtask: {task_description}\nOriginal intent: {intent}",
            history=[], tools=None, max_tokens=None,
        ),
        timeout=timeout,
    )
else:
    # STUB: Returns simulated result
    return f"[SWARM_WORKER] Processed: {task_description}"
```

**FINDINGS:**
1. **Workers execute SEQUENTIALLY** in `_execute_all_workers()` — regardless of swarm_mode (parallel/sequential/hierarchical). There is no `asyncio.gather()`.
2. **No tool routing** — workers call `claude_executor` with `tools=None`, meaning no MCP/MAF tools are available to workers.
3. **No thinking/tool_call events** emitted during real execution — only `on_subtask_progress` at 10% and 100%.
4. **No streaming** — worker results are collected then aggregated as plain strings.
5. **claude_executor** may or may not be wired — depends on how `HybridOrchestratorV2` constructs the handler.

---

## 3. BACKEND: `backend/src/api/v1/swarm/` (API Layer)

### 3.1 routes.py — Status API (3 endpoints)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `GET /api/v1/swarm/{swarm_id}` | GET | Get swarm status |
| `GET /api/v1/swarm/{swarm_id}/workers` | GET | List all workers |
| `GET /api/v1/swarm/{swarm_id}/workers/{worker_id}` | GET | Get worker detail |

All read from `SwarmTracker` singleton. Response schemas include full tool_calls, thinking_contents, messages.

### 3.2 demo.py — Demo API (5 endpoints + SSE)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `POST /api/v1/swarm/demo/start` | POST | Start demo swarm |
| `GET /api/v1/swarm/demo/status/{swarm_id}` | GET | Get demo status |
| `POST /api/v1/swarm/demo/stop/{swarm_id}` | POST | Stop demo |
| `GET /api/v1/swarm/demo/scenarios` | GET | List scenarios |
| `GET /api/v1/swarm/demo/events/{swarm_id}` | GET | **SSE stream** |

**Demo Scenarios:**
| Scenario | Workers | Duration |
|----------|---------|----------|
| `security_audit` | 4 (Network Scanner, Vulnerability Analyzer, Compliance Checker, Report Generator) | ~18s |
| `etl_pipeline` | 3 (Log Analyzer, Schema Inspector, Fix Designer) | ~13s |
| `data_pipeline` | 2 (Quality Monitor, Performance Analyzer) | ~9s |
| `custom` | User-defined | User-defined |

**SSE Flow:**
1. `POST /demo/start` triggers `run_demo_swarm()` as BackgroundTask
2. `run_demo_swarm()` uses `SwarmIntegration` to create swarm and simulate workers
3. `_run_worker()` simulates progress in 10 steps with thinking + tool_calls at intervals
4. SSE generator (`swarm_event_generator`) **polls** SwarmTracker every 200ms
5. Sends `swarm_update` events (full state snapshot) when state changes
6. Sends `swarm_complete` event when done

**CRITICAL:** SSE uses polling/snapshot approach, NOT the SwarmEventEmitter. Events are `swarm_update` and `swarm_complete` (custom names), NOT the AG-UI CustomEvent format defined in events/types.py.

---

## 4. BACKEND: `backend/src/integrations/hybrid/orchestrator/handlers/execution.py`

### 4.1 ExecutionHandler SWARM_MODE Integration

**Constructor accepts:** `swarm_handler: Optional[Any]` (L49)

**Flow in `handle()` (L62-75):**
```python
swarm_decomposition = context.get("swarm_decomposition")
if swarm_decomposition and self._swarm_handler:
    return await self._execute_swarm(request, context, swarm_decomposition)
```

**`_execute_swarm()` (L219-252):**
- Calls `self._swarm_handler.execute_swarm(intent, decomposition, routing_decision, session_id, timeout)`
- Returns `HandlerResult` with content, swarm_id, worker_results, execution_mode=SWARM_MODE

**FINDING:** The swarm path is structurally connected in the handler chain, but activation depends on `swarm_decomposition` being set in the context by a prior handler (likely the analysis/routing handler calling `SwarmModeHandler.analyze_for_swarm()`).

---

## 5. FRONTEND: Components (`frontend/src/components/unified-chat/agent-swarm/`)

### 5.1 File Inventory (21 files)

| File | Size | Sprint | Purpose |
|------|------|--------|---------|
| `AgentSwarmPanel.tsx` | 4.7KB | 102 | Main panel (SwarmHeader + OverallProgress + WorkerCardList) |
| `WorkerCard.tsx` | 6.8KB | 102 | Single worker card with status, progress, type icons |
| `WorkerCardList.tsx` | 1.7KB | 102 | Grid layout of WorkerCards |
| `WorkerDetailDrawer.tsx` | 9.2KB | 103 | Sheet drawer with tabs for worker details |
| `WorkerDetailHeader.tsx` | 5.5KB | 103 | Worker detail header with status badge |
| `ExtendedThinkingPanel.tsx` | 8.0KB | 103 | Collapsible thinking content blocks |
| `ToolCallsPanel.tsx` | 3.0KB | 103 | List of tool calls with status |
| `ToolCallItem.tsx` | 10.1KB | 103 | Individual tool call with input/output JSON |
| `CheckpointPanel.tsx` | 3.2KB | 103 | Checkpoint ID + backend display |
| `CurrentTask.tsx` | 3.1KB | 103 | Current task description display |
| `MessageHistory.tsx` | 7.2KB | 103 | Conversation message list |
| `SwarmHeader.tsx` | 3.8KB | 102 | Swarm title + mode badge + status |
| `OverallProgress.tsx` | 2.1KB | 102 | Progress bar with percentage |
| `SwarmStatusBadges.tsx` | 3.5KB | 102 | Worker status badge summary |
| `WorkerActionList.tsx` | 9.4KB | 103 | Combined actions view |
| `index.ts` | 2.1KB | — | Barrel exports |
| `types/index.ts` | 6.4KB | 101-102 | All UI type definitions |
| `types/events.ts` | 7.0KB | 101 | SSE event type definitions |
| `hooks/useWorkerDetail.ts` | 7.6KB | 103 | Fetches worker detail via REST API with polling |
| `hooks/useSwarmEvents.ts` | 7.3KB | 101 | Dispatches SSE events to handlers |
| `__tests__/` | — | — | Test directory |

### 5.2 Key Props Interfaces

**AgentSwarmPanelProps:**
```typescript
{
  swarmStatus: UIAgentSwarmStatus | null;
  onWorkerClick?: (worker: UIWorkerSummary) => void;
  isLoading?: boolean;
  className?: string;
}
```

**WorkerCardProps:**
```typescript
{
  worker: UIWorkerSummary;
  index: number;
  isSelected?: boolean;
  onClick?: () => void;
}
```

**WorkerDetailDrawerProps:**
```typescript
{
  open: boolean;
  onClose: () => void;
  swarmId: string;
  worker: UIWorkerSummary | null;
  workerDetail?: WorkerDetail;  // External detail for mock/test
  className?: string;
}
```

### 5.3 Key UI Types (`types/index.ts`)

```typescript
type WorkerType = 'claude_sdk' | 'maf' | 'hybrid' | 'research' | 'custom';
type WorkerStatus = 'pending' | 'running' | 'paused' | 'completed' | 'failed';
type SwarmMode = 'sequential' | 'parallel' | 'pipeline' | 'hierarchical' | 'hybrid';
type SwarmStatus = 'initializing' | 'executing' | 'aggregating' | 'completed' | 'failed';

interface UIAgentSwarmStatus {
  swarmId, sessionId, mode, status, totalWorkers, overallProgress,
  workers: UIWorkerSummary[], createdAt, completedAt?, metadata
}

interface UIWorkerSummary {
  workerId, workerName, workerType, role, status, progress,
  currentAction?, toolCallsCount, createdAt, startedAt?, completedAt?
}

interface WorkerDetail extends UIWorkerSummary {
  taskId, taskDescription, thinkingHistory: ThinkingContent[],
  toolCalls: ToolCallInfo[], messages: WorkerMessage[],
  result?, error?, checkpointId?, checkpointBackend?
}
```

### 5.4 SSE Event Types (`types/events.ts`)

9 event names matching backend exactly:
`swarm_created`, `swarm_status_update`, `swarm_completed`, `worker_started`, `worker_progress`, `worker_thinking`, `worker_tool_call`, `worker_message`, `worker_completed`

All payload interfaces defined with snake_case (SSE format).

**MISMATCH:** Frontend events.ts expects AG-UI CustomEvent format (`{type: 'CUSTOM', event_name, payload}`), but the demo SSE sends raw `swarm_update`/`swarm_complete` events. The `useSwarmEvents` hook handles AG-UI format; `useSwarmReal` handles demo format.

---

## 6. FRONTEND: Hooks

### 6.1 `hooks/useSwarmMock.ts` (24KB)

Client-side mock with full state management. No backend needed.

**Return Interface (UseSwarmMockReturn):**
- State: swarmStatus, selectedWorkerId, selectedWorkerDetail, isDrawerOpen, mockMessages
- Swarm Actions: createSwarm, addWorker, removeWorker, completeSwarm, failSwarm, resetSwarm
- Worker Actions: setWorkerStatus, setWorkerProgress, addThinking, addToolCall, addMessage, completeWorker, failWorker
- UI Actions: selectWorker, openDrawer, closeDrawer
- Scenarios: `loadETLScenario()`, `loadSecurityAuditScenario()`, `loadDataPipelineScenario()`

**Preset Scenarios:**
- ETL: 3 workers (sequential) — diagnostic, remediation, verification
- Security Audit: 4 workers (parallel)
- Data Pipeline: 2 workers (parallel)

### 6.2 `hooks/useSwarmReal.ts` (22KB)

Connects to demo backend via REST + SSE.

**Return Interface (UseSwarmRealReturn):**
- State: swarmStatus, selectedWorkerId, selectedWorkerDetail, isDrawerOpen, mockMessages
- Connection: isConnected, isLoading, error, isCompleted
- Demo Actions: `startDemo(request)`, `stopDemo()`, `loadScenarios()`
- UI Actions: selectWorker, openDrawer, closeDrawer

**SSE Connection Flow:**
1. `startDemo()` calls `POST /api/v1/swarm/demo/start`
2. Opens `EventSource` to `/api/v1/swarm/demo/events/{swarm_id}`
3. Listens for `swarm_update` and `swarm_complete` events
4. Maps snake_case backend data to camelCase UI types

### 6.3 `hooks/useSwarmEvents.ts` (7KB)

Generic SSE event dispatcher for AG-UI CustomEvent format.

**Handles:** All 9 event types via `SwarmEventHandlers` interface with optional callbacks: `onSwarmCreated`, `onSwarmStatusUpdate`, `onSwarmCompleted`, `onWorkerStarted`, `onWorkerProgress`, `onWorkerThinking`, `onWorkerToolCall`, `onWorkerMessage`, `onWorkerCompleted`, `onError`.

**NOTE:** This hook is designed for the AG-UI event format but is NOT used by useSwarmReal (which uses its own parsing). This hook is the correct one for Phase 43 real integration.

### 6.4 `hooks/useWorkerDetail.ts` (7KB)

REST API fetcher for worker detail with optional polling.

**Fetches:** `GET /api/v1/swarm/{swarmId}/workers/{workerId}`
**Transforms:** snake_case API -> camelCase WorkerDetail
**Polling:** Configurable interval, only when worker is running.

---

## 7. FRONTEND: `stores/swarmStore.ts` (Zustand)

**State:**
```typescript
swarmStatus: UIAgentSwarmStatus | null
selectedWorkerId: string | null
selectedWorkerDetail: WorkerDetail | null
isDrawerOpen: boolean
isLoading: boolean
error: string | null
```

**Actions:**
| Action | Signature | Purpose |
|--------|-----------|---------|
| `setSwarmStatus` | `(status) => void` | Set entire swarm status |
| `updateSwarmProgress` | `(progress) => void` | Update overall progress |
| `completeSwarm` | `(status, completedAt?) => void` | Mark swarm done |
| `addWorker` | `(worker) => void` | Add worker to list |
| `updateWorkerProgress` | `(payload: WorkerProgressPayload) => void` | Update worker progress |
| `updateWorkerThinking` | `(payload: WorkerThinkingPayload) => void` | Add thinking to worker detail |
| `updateWorkerToolCall` | `(payload: WorkerToolCallPayload) => void` | Add tool call to worker detail |
| `completeWorker` | `(payload: WorkerCompletedPayload) => void` | Mark worker done |
| `selectWorker` | `(worker) => void` | Select worker for drawer |
| `setWorkerDetail` | `(detail) => void` | Set detailed view |
| `openDrawer` / `closeDrawer` | `() => void` | Toggle drawer |
| `reset` | `() => void` | Reset all state |

Uses `immer` for immutable updates and `devtools` middleware.

---

## 8. SUMMARY: What's Real vs Stub vs Disconnected

### REAL (Production-ready infrastructure):
| Component | Status |
|-----------|--------|
| `models.py` (all data structures) | Complete, serializable |
| `tracker.py` (SwarmTracker) | Complete, thread-safe |
| `swarm_integration.py` (facade) | Complete, all callbacks |
| `events/types.py` (event payloads) | Complete, 9 event types |
| `events/emitter.py` (SwarmEventEmitter) | Complete with throttle/batch |
| `api/v1/swarm/routes.py` (status API) | 3 REST endpoints working |
| `api/v1/swarm/demo.py` (demo API + SSE) | Full simulation working |
| Frontend: all 15 components | Complete UI |
| Frontend: useSwarmMock hook | Full mock with 3 scenarios |
| Frontend: useSwarmReal hook | Connected to demo SSE |
| Frontend: useSwarmEvents hook | AG-UI event dispatcher |
| Frontend: useWorkerDetail hook | REST fetcher with polling |
| Frontend: swarmStore (Zustand) | Full state management |

### STUB / PARTIALLY IMPLEMENTED:
| Component | Issue |
|-----------|-------|
| `SwarmModeHandler._execute_worker_task()` | Falls back to `"[SWARM_WORKER] Processed: ..."` when no claude_executor |
| `SwarmModeHandler._execute_all_workers()` | **Always sequential** — no parallel execution |
| Worker execution | **No tools** — `tools=None` passed to claude_executor |
| Worker execution | **No thinking/tool_call events** during real execution |
| Worker execution | **No streaming** — results collected then aggregated |

### DISCONNECTED:
| Component | Issue |
|-----------|-------|
| `SwarmEventEmitter` | Built but NOT wired to execution path or SSE endpoint |
| `useSwarmEvents` hook | Expects AG-UI CustomEvent format, not used by useSwarmReal |
| `swarmStore` | Not used by useSwarmMock or useSwarmReal (they manage own state) |
| Demo SSE vs Real SSE | Demo uses polling+snapshot; real path has no SSE at all |
| Redis persistence in tracker | Coded but not connected |

---

## 9. GAP ANALYSIS for Phase 43

### Critical Gaps (must fix for real E2E):
1. **Workers always sequential** — `_execute_all_workers` needs `asyncio.gather()` for parallel mode
2. **No tools for workers** — Each worker needs tool access (MCP/MAF) based on subtask
3. **No real SSE streaming** — SwarmEventEmitter exists but is not connected to any SSE endpoint for real execution
4. **No thinking/tool events** — Real execution only reports 10% and 100% progress, no intermediate events
5. **Demo SSE format != AG-UI format** — Two incompatible event systems exist
6. **swarmStore unused** — useSwarmMock and useSwarmReal manage their own state instead

### Medium Gaps:
7. **No hierarchical mode** — Only "parallel" (sequential) and "sequential" exist
8. **No worker-to-worker communication** — Workers are fully isolated
9. **No result aggregation via LLM** — Results are just string-concatenated
10. **Frontend type mismatches** — Backend `WorkerType` has 9 values, frontend has 5
11. **No error recovery** — Failed workers stop the sequence, no retry

### Nice-to-haves:
12. Redis persistence for SwarmTracker
13. Worker checkpointing
14. Partial result streaming
15. Worker dependency graph for hierarchical mode
