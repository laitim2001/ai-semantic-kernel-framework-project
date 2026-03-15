# Phase 4: E2E Flow Validation — 5 User Journeys

> **Analyst**: E2E Flow Validator
> **Date**: 2026-03-15
> **Source Reports**: 14 Phase 3 analysis reports (3A parts 1-3, 3B parts 1+3, 3C hybrid/orchestration/claude-sdk/ag-ui/remaining, 3D core-infra, 3E parts 1+2+4)
> **Methodology**: Trace each step in the chain across analysis reports, verify connections exist, flag broken links and mock bypasses

---

## Table of Contents

1. [Flow 1: Chat Message (Primary Journey)](#flow-1-chat-message-primary-journey)
2. [Flow 2: Agent CRUD](#flow-2-agent-crud)
3. [Flow 3: Workflow Execution](#flow-3-workflow-execution)
4. [Flow 4: HITL Approval](#flow-4-hitl-approval)
5. [Flow 5: Swarm Multi-Agent](#flow-5-swarm-multi-agent)
6. [Summary Matrix](#summary-matrix)
7. [Critical Findings](#critical-findings)

---

## Flow 1: Chat Message (Primary Journey)

**Expected Chain**: Frontend (UnifiedChat.tsx) → useUnifiedChat hook → API client → POST /api/v1/ag-ui or /orchestration/ → BusinessIntentRouter (3-tier) → LLMServiceFactory → Azure OpenAI → SSE response → AG-UI EventBridge → Frontend state update

### Step-by-Step Trace

| Step | Component | Report Source | Status | Evidence |
|------|-----------|--------------|--------|----------|
| 1. User types message | `UnifiedChat.tsx` (~900 LOC) | 3E-part1 §2 | **CONNECTED** | Calls `sendMessage()` from `useUnifiedChat` hook. Props include `onSend`, `onModeChange`, orchestration state. |
| 2. useUnifiedChat processes | `useUnifiedChat.ts` (~750 LOC) | 3E-part4 §2.1 | **CONNECTED** | POST to AG-UI SSE endpoint (`/api/v1/ag-ui`) via fetch-based SSE. Handles 15 SSE event types. Syncs to Zustand store. |
| 3. Orchestration routing | `useOrchestration.ts` (353 LOC) | 3E-part4 §2.2 | **CONNECTED** | Calls `orchestrationApi.classify()` → POST `/orchestration/intent/classify`. Manages phase state machine: idle → routing → dialog → risk_assessment → executing. |
| 4. API route receives | `orchestration/intent_routes.py` | 3A-part3 §orchestration | **CONNECTED** | `classify_intent` endpoint uses real `BusinessIntentRouter` or mock fallback. |
| 5. BusinessIntentRouter 3-tier | `intent_router/router.py` | 3C-orchestration §6 | **CONNECTED** | Three-tier cascade: PatternMatcher (<10ms) → SemanticRouter (<100ms) → LLMClassifier (<2s). Returns `RoutingDecision` with intent, workflow_type, risk_level. |
| 5a. Tier 1: PatternMatcher | `pattern_matcher/matcher.py` + `rules.yaml` | 3C-orchestration §3 | **CONNECTED** | 30+ regex rules in YAML, pre-compiled. Fixed confidence 0.95. Bilingual (EN+ZH-TW). **REAL**. |
| 5b. Tier 2: SemanticRouter | `semantic_router/router.py` | 3C-orchestration §4 | **CONNECTED** | Uses `semantic-router` library with OpenAI/Azure OpenAI embeddings. 15 predefined routes. Gracefully skips if library not installed. **REAL when configured**. |
| 5c. Tier 3: LLMClassifier | `llm_classifier/classifier.py` | 3C-orchestration §5 | **CONNECTED** | Uses `LLMServiceProtocol` → `LLMServiceFactory.create()`. Returns UNKNOWN with 0.0 confidence if unconfigured. **REAL when configured**. |
| 6. LLMServiceFactory | `integrations/llm/` | 3C-remaining §llm | **CONNECTED** | Real Azure OpenAI via `openai` SDK. Supports Azure/Anthropic/Mock providers. Auto-detects from env vars. |
| 7. CompletenessChecker | `completeness/checker.py` | 3C-orchestration §7 | **CONNECTED** | Rule-based keyword field extraction. Returns `CompletenessInfo`. |
| 8. GuidedDialogEngine | `guided_dialog/engine.py` | 3C-orchestration §10 | **CONNECTED** | Multi-turn template-based questions. In-memory session storage. |
| 9. AG-UI SSE endpoint | `ag_ui/routes.py` POST `/ag-ui` | 3A-part1 §ag_ui | **CONNECTED** | Core SSE streaming endpoint. Creates `RunAgentInput`, calls `HybridEventBridge.stream_events()`. |
| 10. HybridEventBridge | `ag_ui/bridge.py` (1,080 LOC) | 3C-ag-ui §4 | **CONNECTED** | Emits RUN_STARTED → heartbeat task → execute_task (calls orchestrator) → converters.from_result() → TEXT/TOOL events → RUN_FINISHED. Yields SSE strings. |
| 11. HybridOrchestratorV2 | `hybrid/orchestrator_v2.py` (1,254 LOC) | 3C-hybrid §6 | **CONNECTED** | Deprecated God Object, now facade delegating to `OrchestratorMediator` (Sprint 132). 13 injectable dependencies. |
| 12. OrchestratorMediator | `hybrid/orchestrator/mediator.py` | 3C-hybrid §6.3 | **CONNECTED** | 6-handler chain: Routing → Dialog → Approval → Execution → Context → Observability. |
| 13. Framework execution | `claude_executor` or `maf_executor` | 3C-hybrid §7.1 | **CONNECTED** | Routes to Claude SDK `query()` or MAF executor based on mode selection. |
| 14. ClaudeSDKClient | `claude_sdk/client.py` (357 LOC) | 3C-claude-sdk §3.1 | **CONNECTED** | Uses `AsyncAnthropic` directly. `query()` → `QueryExecutor.execute_query()` with agentic loop. **REAL Anthropic SDK**. |
| 15. SSE event conversion | `ag_ui/converters.py` (691 LOC) | 3C-ag-ui §3 | **CONNECTED** | `EventConverters.from_result()` converts `HybridResultV2` to AG-UI events sequence. Content chunked for streaming. |
| 16. Frontend SSE parsing | `useUnifiedChat.ts` SSE reader | 3E-part4 §2.1 | **CONNECTED** | Reads SSE via ReadableStream with TextDecoder. Manual `data:` prefix parsing. Accumulates deltas into messages. |
| 17. UI state update | Zustand store + React state | 3E-part4 §2.1 | **CONNECTED** | Syncs to `useUnifiedChatStore` via useEffect. Messages displayed in `ChatArea` → `MessageList`. |

### Broken Links

| # | Location | Issue | Severity |
|---|----------|-------|----------|
| BL-1.1 | Bridge → Orchestrator | **Simulated streaming**: Bridge receives COMPLETE `HybridResultV2` then simulates streaming by chunking text (100 chars/chunk). NOT true token-by-token streaming from LLM. | **MEDIUM** |
| BL-1.2 | Intent route fallback | `classify_intent` falls back to mock router if real `BusinessIntentRouter` initialization fails. No indicator to user. | **MEDIUM** |
| BL-1.3 | Orchestration metrics | `get_metrics()` returns **hardcoded zeros**. `reset_metrics()` is a no-op stub. | **LOW** |

### Mock Bypasses

| # | Component | Bypass | Impact |
|---|-----------|--------|--------|
| MB-1.1 | SemanticRouter | Returns `no_match()` if `semantic-router` library not installed. | Tier 2 silently skipped. |
| MB-1.2 | LLMClassifier | Returns `UNKNOWN` with 0.0 confidence if no LLM service configured. | Tier 3 silently skipped — everything falls to UNKNOWN/HANDOFF. |
| MB-1.3 | AG-UI Bridge | Simulation mode when orchestrator not configured — returns mock responses. | Full mock bypass in dev. |
| MB-1.4 | ClaudeSDKClient | ag_ui `dependencies.py` supports `AG_UI_SIMULATION_MODE=true` — skips real Claude API. | Dev-only, but no guard against production. |

### Data Persistence

| Point | Storage | Persistent? |
|-------|---------|-------------|
| Chat threads | localStorage (frontend) | Yes (browser-local only, NOT server-persisted) |
| Dialog sessions | In-memory dict (`_dialog_sessions`) | **No** — lost on restart |
| AG-UI thread state | InMemory or Redis (`ThreadManager`) | Redis = Yes; InMemory = No |
| Approval requests | In-memory `ApprovalStorage` | **No** — lost on restart |
| Classification cache | In-memory dict | **No** — lost on restart |
| Orchestration context | In-memory `ContextBridge._context_cache` | **No** — lost on restart, also NOT thread-safe |

### Flow 1 Verdict: **MOSTLY CONNECTED**

The primary chat flow is end-to-end connected with real code at every step. However:
- Streaming is simulated (chunked post-completion, not real-time from LLM)
- Multiple in-memory stores lose state on restart
- Tiers 2 and 3 of routing silently degrade without credentials

---

## Flow 2: Agent CRUD

**Expected Chain**: Frontend (AgentsPage) → React Query → Fetch API → POST /api/v1/agents/ → AgentService → AgentRepository → PostgreSQL → Response → UI update

### Step-by-Step Trace

| Step | Component | Report Source | Status | Evidence |
|------|-----------|--------------|--------|----------|
| 1. AgentsPage list | `AgentsPage.tsx` (~230 LOC) | 3E-part1 §5.1 | **CONNECTED** | `GET /agents/?search={query}` via React Query. Falls back to `generateMockAgents()` on API failure. |
| 2. CreateAgentPage form | `CreateAgentPage.tsx` (~750 LOC) | 3E-part1 §5.3 | **CONNECTED** | 4-step wizard, `POST /agents/` on submit. |
| 3. API route | `agents/routes.py` (405 LOC) | 3A-part1 §agents | **CONNECTED** | 6 endpoints: CRUD + `/run`. Uses `AgentRepository` with SQLAlchemy. |
| 4. AgentRepository | `infrastructure/database/repositories/agent.py` | 3B-part1 §agents | **CONNECTED** | Full SQLAlchemy async implementation. PostgreSQL persistence. |
| 5. Agent DB model | `infrastructure/database/models/agent.py` | 3D §infrastructure | **CONNECTED** | SQLAlchemy model with id, name, description, instructions, category, tools, status, version, timestamps. |
| 6. Response → UI | React Query cache invalidation | 3E-part1 §5 | **CONNECTED** | `useMutation` with `onSuccess` → `queryClient.invalidateQueries(['agents'])`. |

### Broken Links

| # | Location | Issue | Severity |
|---|----------|-------|----------|
| BL-2.1 | AgentsPage fallback | `generateMockAgents()` returns 4 hardcoded agents on ANY API failure. No visual indicator of mock data. | **MEDIUM** |
| BL-2.2 | Agent run endpoint | `POST /agents/{id}/run` creates `AgentConfig` with `tools=[]` — comment: "Tools will be resolved in S1-3". Unclear if resolved. | **LOW** |
| BL-2.3 | Version increment | `increment_version` after `update` is a separate DB call — should be single transaction. | **LOW** |

### Mock Bypasses

| # | Component | Bypass | Impact |
|---|-----------|--------|--------|
| MB-2.1 | AgentsPage | `generateMockAgents()` on API error | Users see fake agents without knowing |
| MB-2.2 | AgentDetailPage | `generateMockAgent(id)` on API error | User sees fake agent details |

### Data Persistence

| Point | Storage | Persistent? |
|-------|---------|-------------|
| Agent records | PostgreSQL via `AgentRepository` | **Yes** |
| Agent version | PostgreSQL (version column) | **Yes** |
| Tool registry | In-memory `ToolRegistry` | No — rebuilt on startup |

### Flow 2 Verdict: **FULLY CONNECTED**

Agent CRUD is the best-persisted flow in the system. The full chain from frontend to PostgreSQL is real and connected. The only concern is silent mock fallback in the frontend on API errors.

---

## Flow 3: Workflow Execution

**Expected Chain**: Frontend (WorkflowDetailPage) → API → POST /api/v1/workflows/{id}/execute → WorkflowExecutionService → WorkflowEngine → Agent invocation → Checkpoint → DB persist

### Step-by-Step Trace

| Step | Component | Report Source | Status | Evidence |
|------|-----------|--------------|--------|----------|
| 1. WorkflowDetailPage | `WorkflowDetailPage.tsx` (~400 LOC) | 3E-part1 §6.2 | **CONNECTED** | `POST /workflows/{id}/execute` via React mutation. Shows execution dialog with result. Real API, no mock fallback. |
| 2. API route | `workflows/routes.py` (~942 LOC) | 3A-part3 §workflows | **CONNECTED** | `execute_workflow` endpoint. Uses `WorkflowDefinitionAdapter.run()` from Agent Framework. |
| 3. WorkflowRepository | `infrastructure/database/repositories/workflow.py` | 3A-part3 §workflows | **CONNECTED** | Full SQLAlchemy async. PostgreSQL persistence. Graph visualization with topological sort. |
| 4. WorkflowExecutionService | `domain/workflows/service.py` (~700 LOC) | 3B-part3 §11.3 | **CONNECTED** | Main engine: creates result → traverses DAG → executes nodes sequentially. `_execute_node()` dispatches by node type. |
| 5. Agent node execution | `_execute_agent_node()` → `AgentService.invoke_agent()` | 3B-part3 §11.3 | **CONNECTED** | Calls agent via adapter pattern. Sprint 27 migration to official API. |
| 6. ExecutionStateMachine | `domain/executions/state_machine.py` (428 LOC) | 3B-part1 §executions | **CONNECTED** | Pure domain object. PENDING → RUNNING → COMPLETED/FAILED/CANCELLED. History tracking. |
| 7. Execution DB persist | `ExecutionRepository` (PostgreSQL) | 3A-part2 §executions | **CONNECTED** | `POST /executions/` creates record. `GET /executions/` lists with pagination. DB-backed. |
| 8. Checkpoint creation | `CheckpointService` | 3B-part1 §checkpoints | **CONNECTED** | DB-backed via `CheckpointRepository` + `DatabaseCheckpointStorage`. States: PENDING → APPROVED/REJECTED/EXPIRED. |
| 9. Resume service | `WorkflowResumeService` (~400 LOC) | 3B-part3 §11.4 | **CONNECTED** | Validates checkpoint → restores state → identifies next node → re-executes. |

### Broken Links

| # | Location | Issue | Severity |
|---|----------|-------|----------|
| BL-3.1 | Execution shutdown | `POST /executions/{id}/shutdown` — checkpoint save is **log-only stub**: "In production, this would persist". Resource cleanup is also log-only. | **HIGH** |
| BL-3.2 | Resume endpoint | Accesses private `repo._session` attribute directly. Uses lazy imports inside function body. | **LOW** |
| BL-3.3 | Decision node | `_evaluate_condition()` uses simple expression evaluation — limited condition syntax. | **LOW** |

### Mock Bypasses

| # | Component | Bypass | Impact |
|---|-----------|--------|--------|
| MB-3.1 | AgentService.run_agent_with_config | Returns mock result if no adapter initialized. | Workflow agent nodes return fake results without adapter. |

### Data Persistence

| Point | Storage | Persistent? |
|-------|---------|-------------|
| Workflow definitions | PostgreSQL via `WorkflowRepository` | **Yes** |
| Execution records | PostgreSQL via `ExecutionRepository` | **Yes** |
| Checkpoints | PostgreSQL via `CheckpointRepository` | **Yes** |
| State machine state | In-memory (caller's responsibility to persist) | Depends on caller |
| DAG graph layout | PostgreSQL (graph JSON in workflow record) | **Yes** |

### Flow 3 Verdict: **MOSTLY CONNECTED**

The workflow execution chain is well-persisted to PostgreSQL throughout. The major gap is the shutdown endpoint which stubs checkpoint persistence. The execution path from UI to agent invocation to DB is real.

---

## Flow 4: HITL Approval

**Expected Chain**: Tool call with HIGH risk → RiskAssessmentEngine → ApprovalHook → SSE approval event → Frontend ApprovalMessageCard → User approves → POST /approve → Resume execution

### Step-by-Step Trace

| Step | Component | Report Source | Status | Evidence |
|------|-----------|--------------|--------|----------|
| 1. Tool call detected | `QueryExecutor` agentic loop | 3C-claude-sdk §3.3 | **CONNECTED** | Detects `tool_use` blocks in Claude response. Runs hook chain before execution. |
| 2. Hook chain invoked | `HookChain` → `ApprovalHook` (priority 90) | 3C-claude-sdk §5.2 | **CONNECTED** | `on_tool_call(context) -> HookResult`. ApprovalHook checks Write/Edit/MultiEdit/Bash/Task tools. 5-min timeout. |
| 3. Risk assessment | `RiskAssessmentEngine` (560 LOC) | 3C-hybrid §5 | **CONNECTED** | 7 factor types, 3 scoring strategies. HIGH (0.6-0.85) = requires approval. Tool base risks: Write=0.4, Bash=0.6. |
| 4. HITLHandler | `ag_ui/features/human_in_loop.py` (745 LOC) | 3C-ag-ui §6.3 | **CONNECTED** | `check_approval_needed()` → `create_approval_event()` → emits `approval_required` custom event. |
| 5. ApprovalStorage | `ag_ui/features/human_in_loop.py` | 3C-ag-ui §6.3 | **CONNECTED** | In-memory with asyncio.Lock. `create_pending()` with 5-min TTL. Auto-expires timed-out requests. |
| 6. SSE event emission | `HITL_APPROVAL_REQUIRED` custom event | 3C-ag-ui §3.2 | **CONNECTED** | Converters emit custom event for high-risk tools (Write, Edit, MultiEdit, Bash, Task). Sprint 66 enhancement. |
| 7. Frontend receives | `useUnifiedChat.ts` CUSTOM event handler | 3E-part4 §2.1 | **CONNECTED** | Handles `APPROVAL_REQUIRED` custom event type. Adds to `pendingApprovals` state. |
| 8. ApprovalMessageCard | `ApprovalMessageCard.tsx` (491 LOC) | 3E-part2 §2.2 | **CONNECTED** | Inline card with countdown timer, risk-based styling (low/medium/high/critical), approve/reject buttons. |
| 9. User approves | Button click → `onApprove` | 3E-part2 §2.2 | **CONNECTED** | Calls `approveToolCall(approvalId)` from `useUnifiedChat`. |
| 10. POST approval | `POST /ag-ui/approvals/{id}/approve` | 3A-part1 §ag_ui | **CONNECTED** | Updates `ApprovalStorage` status. |
| 11. Bridge heartbeat | `HybridEventBridge` heartbeat task | 3C-ag-ui §4 | **CONNECTED** | 2-second heartbeat checks pending HITL approvals. When approved, continues execution. |
| 12. Resume execution | `wait_for_approval()` resolves | 3C-ag-ui §6.3 | **CONNECTED** | Async polling (0.5s intervals) on ApprovalStorage. Resumes tool execution on approval. |

### Broken Links

| # | Location | Issue | Severity |
|---|----------|-------|----------|
| BL-4.1 | ApprovalStorage | **In-memory only** — approval requests lost on restart. Multi-instance deployments cannot share approval state. | **HIGH** |
| BL-4.2 | Dual approval systems | Two independent approval systems exist: (a) `ag_ui/features/human_in_loop.py` ApprovalStorage for SSE-based approvals, (b) `orchestration/hitl_routes.py` HITLController for orchestration approvals. These are NOT connected to each other. | **HIGH** |
| BL-4.3 | Checkpoint approvals | `domain/checkpoints/CheckpointService` has DEPRECATED `approve_checkpoint()` / `reject_checkpoint()` methods pointing to `HumanApprovalExecutor` — a third approval path. | **MEDIUM** |

### Mock Bypasses

| # | Component | Bypass | Impact |
|---|-----------|--------|--------|
| MB-4.1 | AG-UI test endpoints | 5 `/test/*` endpoints generate mock approval events. Not gated by env/feature flag. | Test data could appear in production. |

### Data Persistence

| Point | Storage | Persistent? |
|-------|---------|-------------|
| Pending approvals (AG-UI) | In-memory `ApprovalStorage` | **No** — lost on restart |
| Pending approvals (Orchestration) | HITLController (Redis or In-memory) | Redis = Yes; In-memory = No |
| Checkpoint approvals | PostgreSQL via CheckpointRepository | **Yes** |
| Approval history | Not stored anywhere | **No** |

### Flow 4 Verdict: **CONNECTED but FRAGILE**

The HITL approval flow works end-to-end for the AG-UI path. However, three separate, unconnected approval systems exist (AG-UI ApprovalStorage, orchestration HITLController, checkpoint service). The AG-UI path uses in-memory storage only, making it unsuitable for production multi-instance deployments.

---

## Flow 5: Swarm Multi-Agent

**Expected Chain**: Frontend → POST /api/v1/swarm/demo/start → SwarmManager → ClaudeCoordinator → Multiple workers → SSE events → SwarmPanel → WorkerCards

### Step-by-Step Trace

| Step | Component | Report Source | Status | Evidence |
|------|-----------|--------------|--------|----------|
| 1. SwarmTestPage | `SwarmTestPage.tsx` (~845 LOC) | 3E-part1 §3 | **CONNECTED** | Real mode: POST `/swarm/demo/start` + SSE event subscription. Mock mode: `useSwarmMock` hook for UI testing. |
| 2. API route | `swarm/routes.py` (~835 LOC) | 3A-part3 §swarm | **CONNECTED** | `start_demo` endpoint creates `SwarmIntegration` → runs as background asyncio task. SSE via `/swarm/demo/events/{id}`. |
| 3. SwarmIntegration | `swarm/swarm_integration.py` (~405 LOC) | 3C-remaining §swarm | **CONNECTED** | Bridge between `ClaudeCoordinator` and `SwarmTracker`. Callback-based interface. |
| 4. ClaudeCoordinator | `claude_sdk/orchestrator/coordinator.py` (522 LOC) | 3C-claude-sdk §9.2 | **CONNECTED** | Task analysis → agent selection → subtask allocation → parallel/sequential execution → result aggregation. |
| 5. SwarmTracker | `swarm/tracker.py` (~694 LOC) | 3C-remaining §swarm | **CONNECTED** | State management for swarms/workers. In-memory dict + optional Redis. Thread-safe via `threading.RLock`. |
| 6. SwarmEventEmitter | `swarm/events/emitter.py` (~635 LOC) | 3C-remaining §swarm | **CONNECTED** | Emits AG-UI `CustomEvent` objects. Throttling (200ms), batching (size 5), priority events bypass queue. |
| 7. SSE event stream | `GET /swarm/demo/events/{id}` | 3A-part3 §swarm | **CONNECTED** | Polls `SwarmTracker` at 200ms intervals. Yields SSE strings. |
| 8. Frontend processing | `useSwarmReal` / `useSwarmEventHandler` | 3E-part2 §3 (agent-swarm) | **CONNECTED** | SSE event handling with 9 event types. Updates swarm state. |
| 9. SwarmPanel display | `AgentSwarmPanel` + `WorkerCard` components | 3E-part2 §3 | **CONNECTED** | 15 components + 4 hooks. Worker cards with status, progress, thinking, tool calls. |

### Broken Links

| # | Location | Issue | Severity |
|---|----------|-------|----------|
| BL-5.1 | Demo stop | `stop_demo` only marks status in dict but does NOT cancel the asyncio background task. | **MEDIUM** |
| BL-5.2 | SSE polling | Event generator polls SwarmTracker at 200ms intervals — push-based events would be more efficient. | **LOW** |
| BL-5.3 | Demo vs Real | The `/swarm/demo/start` endpoint runs a simulated demo execution, NOT real multi-agent coordination via ClaudeCoordinator with actual LLM calls. The demo generates simulated worker progress events. | **HIGH** |

### Mock Bypasses

| # | Component | Bypass | Impact |
|---|-----------|--------|--------|
| MB-5.1 | Demo execution | The "demo" endpoints simulate swarm execution with predetermined scenarios. Real `ClaudeCoordinator` integration exists but is NOT wired to the demo API. | Demo shows simulated, not real, multi-agent work. |
| MB-5.2 | SwarmTestPage mock mode | `useSwarmMock` hook provides full client-side simulation with preset scenarios. | UI testing only, no backend. |

### Data Persistence

| Point | Storage | Persistent? |
|-------|---------|-------------|
| Swarm state | In-memory dict + optional Redis | Redis = Yes; In-memory = No |
| Worker executions | In-memory (within SwarmTracker) | **No** — lost on restart |
| Demo state | In-memory `_active_demos` dict | **No** — lost on restart |
| Event history | Not stored | **No** |

### Flow 5 Verdict: **PARTIALLY CONNECTED**

The infrastructure is fully built: SwarmTracker, SwarmEventEmitter, SwarmIntegration callbacks, ClaudeCoordinator, and frontend visualization are all real and connected. However, the API demo endpoint runs SIMULATED swarm executions rather than wiring to the real ClaudeCoordinator with actual LLM calls. The real multi-agent path (ClaudeCoordinator → actual agent execution) exists in code but is not exposed through the demo API.

---

## Summary Matrix

| Flow | Frontend → API | API → Business Logic | Business Logic → Data | Data → Response | Overall |
|------|---------------|---------------------|----------------------|----------------|---------|
| **1. Chat Message** | CONNECTED | CONNECTED | CONNECTED (multiple tiers) | CONNECTED (SSE) | **MOSTLY CONNECTED** |
| **2. Agent CRUD** | CONNECTED (mock fallback) | CONNECTED | CONNECTED (PostgreSQL) | CONNECTED | **FULLY CONNECTED** |
| **3. Workflow Execution** | CONNECTED | CONNECTED | CONNECTED (PostgreSQL) | CONNECTED | **MOSTLY CONNECTED** |
| **4. HITL Approval** | CONNECTED | CONNECTED | CONNECTED (in-memory) | CONNECTED (SSE) | **CONNECTED but FRAGILE** |
| **5. Swarm Multi-Agent** | CONNECTED | CONNECTED (demo only) | CONNECTED (in-memory) | CONNECTED (SSE) | **PARTIALLY CONNECTED** |

---

## Critical Findings

### 1. Three Unconnected Approval Systems (HIGH)

The platform has three independent, incompatible approval mechanisms:

| System | Location | Storage | Used By |
|--------|----------|---------|---------|
| AG-UI ApprovalStorage | `ag_ui/features/human_in_loop.py` | In-memory dict | Chat SSE flow |
| Orchestration HITLController | `orchestration/hitl_routes.py` | Redis or in-memory | Orchestration routing |
| Checkpoint Service | `domain/checkpoints/` | PostgreSQL | Workflow execution |

These three systems do not share state, cannot be queried together, and have different persistence guarantees. A user approving via the chat UI (AG-UI) does not affect orchestration approvals, and vice versa.

### 2. Simulated Streaming (MEDIUM)

The AG-UI bridge receives the COMPLETE `HybridResultV2` from the orchestrator and then simulates streaming by chunking text into 100-character segments. This means the user sees "streaming" but the entire response was already computed before any text appears. True token-by-token streaming from the LLM is not implemented.

### 3. In-Memory State Fragility (HIGH)

Critical flow state stored only in-memory (lost on restart):

| Component | Data Lost |
|-----------|-----------|
| ApprovalStorage | All pending approvals |
| Dialog sessions | All in-progress guided dialogs |
| ContextBridge cache | All hybrid context state |
| Classification cache | All cached LLM classifications |
| Swarm state (without Redis) | All swarm/worker tracking |

### 4. Silent Mock Fallback (MEDIUM)

10 frontend pages silently fall back to mock data on API failure with NO visual indicator. Users cannot distinguish real data from mock data. Pages affected: AgentsPage, AgentDetailPage, WorkflowsPage, ApprovalsPage, AuditPage, TemplatesPage, PerformancePage, ExecutionChart, PendingApprovals, RecentExecutions.

### 5. Swarm Demo is Simulated (MEDIUM)

The swarm demo API (`/swarm/demo/start`) runs predetermined simulation scenarios rather than real multi-agent coordination. The real `ClaudeCoordinator` with actual LLM calls exists in `claude_sdk/orchestrator/` but is not wired to the demo endpoint. The entire swarm visualization shows simulated progress, not real agent work.

### 6. Intent Router Graceful Degradation (LOW-MEDIUM)

Without proper credentials configured:
- Tier 2 (SemanticRouter): silently returns no-match
- Tier 3 (LLMClassifier): silently returns UNKNOWN with 0.0 confidence
- Result: ALL messages classified as UNKNOWN with HANDOFF workflow type — effectively disabling intelligent routing

### 7. ContextBridge Thread Safety (MEDIUM)

`ContextBridge._context_cache` (plain `Dict[str, HybridContext]`) has NO locking. Multiple concurrent async operations on the same session can corrupt cache state. The `ContextSynchronizer` has per-session locks, but the bridge-level cache does not.

---

## Appendix: Cross-Layer Connection Map

```
Frontend Layer                API Layer                    Integration Layer              Domain Layer              Infrastructure
─────────────                ─────────                    ─────────────────              ────────────              ──────────────
UnifiedChat.tsx              ag_ui/routes.py              ag_ui/bridge.py
  └─useUnifiedChat ─SSE──►  POST /ag-ui ──────────►     HybridEventBridge
                                                           └─ HybridOrchestratorV2
                             orchestration/               │  └─ OrchestratorMediator
  └─useOrchestration ────►  intent_routes.py ──────►     │     ├─ RoutingHandler ──►   BusinessIntentRouter
                                                          │     ├─ DialogHandler ──►    GuidedDialogEngine
                                                          │     ├─ ApprovalHandler ──►  RiskAssessmentEngine
                                                          │     └─ ExecutionHandler
                                                          │        ├─ claude_executor ─► ClaudeSDKClient ──► Anthropic API
                                                          │        └─ maf_executor ────► AgentExecutorAdapter ──► Azure OpenAI
                                                          └─ EventConverters ──► SSE events ──► Frontend

AgentsPage.tsx               agents/routes.py                                            AgentService              AgentRepository ──► PostgreSQL
  └─React Query ──GET/POST►  CRUD endpoints ──────────────────────────────────────────► schemas.py                models.agent

WorkflowDetailPage.tsx       workflows/routes.py                                         WorkflowExecutionService  WorkflowRepository ──► PostgreSQL
  └─React Query ──POST ──►   execute endpoint ────────────────────────────────────────► DAG traversal             ExecutionRepository ──► PostgreSQL
                                                                                         CheckpointService         CheckpointRepository ──► PostgreSQL

SwarmTestPage.tsx            swarm/routes.py              swarm/swarm_integration.py
  └─useSwarmReal ──SSE ──►   demo/start ──────────►      SwarmTracker ──────────────────────────────────────────► In-memory (+ optional Redis)
                              demo/events/{id} ◄──SSE──   SwarmEventEmitter
```

---

*Analysis completed. All 14 Phase 3 analysis reports cross-referenced for 5 end-to-end user journeys.*
