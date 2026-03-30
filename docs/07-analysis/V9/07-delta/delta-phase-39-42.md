# Delta Report: Phase 39-42 (Pipeline Assembly + Frontend + Deep Integration)

> V8 -> V9 Changes | Sprints 134-147 | ~142 Story Points
> Period: 2026-03-25 ~ 2026-03-29 (estimated)

---

### Phase 39-42 組裝缺口與解決方案

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              Phase 39-42 三大組裝缺口 → 解決方案                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  問題: Phase 35-38 建了 ~60 files / 10K+ LOC，但各模組獨立無法運行         │
│                                                                             │
│  ┌─── Gap #1: Assembly Gap ──────────────────────────────────────┐          │
│  │  OrchestratorMediator 7 handlers 全部 = None                  │          │
│  │                    ↓ 解決方案                                  │          │
│  │  OrchestratorBootstrap (factory method)                        │          │
│  │  一次初始化: 7 handlers + MCP + Memory + ToolSecurity          │          │
│  └───────────────────────────────────────────────────────────────┘          │
│                                                                             │
│  ┌─── Gap #2: No Background Execution ───────────────────────────┐          │
│  │  所有執行綁定 HTTP request lifecycle                           │          │
│  │                    ↓ 解決方案                                  │          │
│  │  ARQ Redis-backed queue                                        │          │
│  │  dispatch_workflow / dispatch_swarm → background workers        │          │
│  └───────────────────────────────────────────────────────────────┘          │
│                                                                             │
│  ┌─── Gap #3: Old/New System Coexistence ────────────────────────┐          │
│  │  AG-UI bridge 仍連接舊 HybridOrchestratorV2                   │          │
│  │                    ↓ 解決方案                                  │          │
│  │  MediatorEventBridge                                           │          │
│  │  Mediator events → AG-UI SSE format (thinking, tool-call)      │          │
│  └───────────────────────────────────────────────────────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Handler 接線拓撲

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              OrchestratorBootstrap → 7 Handler 接線拓撲                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  OrchestratorBootstrap.create()                                             │
│       │                                                                     │
│       ├──→ ContextHandler ────────→ MemoryManager                          │
│       │                              (自動記憶注入)                         │
│       │                                                                     │
│       ├──→ RoutingHandler ────────→ InputGateway                           │
│       │                           → FrameworkSelector                       │
│       │                           → BusinessIntentRouter                    │
│       │                                                                     │
│       ├──→ DialogHandler ─────────→ GuidedDialogEngine                     │
│       │                              (條件觸發: 資訊不完整時)              │
│       │                                                                     │
│       ├──→ ApprovalHandler ───────→ RiskAssessor (7 維度)                  │
│       │                           → UnifiedApprovalManager                  │
│       │                           → HITL Controller (PostgreSQL)            │
│       │                                                                     │
│       ├──→ AgentHandler ──────────→ Azure OpenAI (function calling)         │
│       │                           → FrameworkSelector (MAF/Claude/Swarm)    │
│       │                                                                     │
│       ├──→ ExecutionHandler ──────→ MAF Executor                           │
│       │                           → Claude Executor                         │
│       │                           → SwarmHandler                            │
│       │                           → ARQ BackgroundQueue                     │
│       │                                                                     │
│       └──→ ObservabilityHandler ──→ Metrics Collector                      │
│                                   → CheckpointStorage                       │
│                                   → PipelineEventEmitter → SSE             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 39: E2E Assembly D — Pipeline Assembly & Wiring
- **Sprints**: 134-137
- **Story Points**: ~44
- **Status**: Completed

### Core Problem
Phase 35-38 built ~60 files / ~10K+ LOC of core modules, but they existed independently without startup code to wire them into a runnable end-to-end pipeline. Three CRITICAL gaps:
1. **Assembly Gap**: OrchestratorMediator's 7 handlers all default to `None` — no bootstrap code
2. **No Background Execution**: All execution tied to HTTP request lifecycle
3. **Old/New System Coexistence**: AG-UI bridge still connected to old `HybridOrchestratorV2`

### New Files Added

**Backend — Bootstrap & Wiring**
| File | Purpose |
|------|---------|
| `backend/src/integrations/hybrid/orchestrator/bootstrap.py` | OrchestratorBootstrap: factory method wiring all 7 handlers + MCP + Memory + ToolSecurity in one initialization |
| `backend/src/integrations/hybrid/orchestrator/events.py` | MediatorEventBridge: adapts OrchestratorMediator events to AG-UI event format |
| `backend/src/integrations/hybrid/orchestrator/mcp_tool_bridge.py` | MCP tool dynamic registration into OrchestratorToolRegistry |
| `backend/src/integrations/hybrid/orchestrator/sse_events.py` | SSE event definitions for pipeline streaming |

**Backend — Handler Wiring**
| File | Purpose |
|------|---------|
| `backend/src/integrations/hybrid/orchestrator/handlers/routing.py` | RoutingHandler: InputGateway + FrameworkSelector wiring |
| `backend/src/integrations/hybrid/orchestrator/handlers/approval.py` | ApprovalHandler: RiskAssessor + HITL wiring |
| `backend/src/integrations/hybrid/orchestrator/handlers/execution.py` | ExecutionHandler: MAF executor + Claude executor + SwarmHandler wiring |
| `backend/src/integrations/hybrid/orchestrator/handlers/context.py` | ContextHandler: MemoryManager integration for auto memory injection |
| `backend/src/integrations/hybrid/orchestrator/handlers/dialog.py` | DialogHandler: GuidedDialogEngine wiring |
| `backend/src/integrations/hybrid/orchestrator/handlers/observability.py` | ObservabilityHandler: metrics + checkpoint wiring |

### Modified Files
| File | Change |
|------|--------|
| `backend/src/integrations/hybrid/orchestrator/mediator.py` | Connected to all 7 real handler implementations instead of None defaults |
| `backend/src/api/v1/ag_ui/` routes | AG-UI `/run` endpoint switched to MediatorEventBridge (from old HybridOrchestratorV2) |
| `backend/src/integrations/orchestration/hitl/controller.py` | HITL approval persisted to PostgreSQL (replaced in-memory) |
| `backend/src/integrations/orchestration/risk_assessor/assessor.py` | Unified with RiskAssessmentEngine |

### Architecture Changes
- **OrchestratorBootstrap**: Single factory method that assembles the complete runnable Mediator pipeline in one call. Wires: InputGateway -> RoutingHandler -> FrameworkSelector -> RiskAssessor -> ApprovalHandler -> AgentHandler -> ExecutionHandler -> ResultSynthesiser -> ObservabilityHandler
- **AG-UI Bridge Migration**: SSE streaming moved from old `HybridOrchestratorV2` to new `MediatorEventBridge`, supporting intermediate events (thinking tokens, tool-call progress)
- **Background Task Execution (ARQ)**: Long-running tasks submitted to ARQ Redis-backed queue instead of blocking HTTP connections. `dispatch_workflow` and `dispatch_swarm` now submit to background workers
- **Session-aware SSE**: User disconnect/reconnect doesn't lose events; session-based SSE channels
- **ToolSecurityGateway Integration**: Injected into OrchestratorToolRegistry.execute() — all tool calls pass through security layer
- **Risk Engine Unification**: Merged `RiskAssessor` and `RiskAssessmentEngine` into single component
- **Extended Thinking Mode**: Execution mode for deep analysis tasks
- **MCP Dynamic Registration**: MCP tools automatically discovered and registered at bootstrap

### Features Added
- OrchestratorBootstrap builds complete runnable Mediator pipeline in one call
- E2E flow: Auth -> Session -> Mediator -> Worker -> Response fully connected
- AG-UI SSE streaming uses new MediatorEventBridge with intermediate events
- Long-running tasks execute in background via ARQ (not blocking HTTP)
- Session close/reopen reconnects to background tasks
- MCP tools discoverable and callable by Orchestrator Agent
- ToolSecurityGateway intercepts all tool calls
- HITL approval persisted to PostgreSQL
- E2E 10-step smoke test passing

### Issues Fixed
- **Assembly Gap** (CRITICAL): All 7 handlers wired to real dependencies
- **No HTTP Entry Point** (CRITICAL): OrchestratorMediator now accessible via AG-UI endpoints
- **Old/New Coexistence** (HIGH): AG-UI bridge fully migrated to new system
- **Background Execution** (CRITICAL): ARQ integration for async task execution
- **Risk Engine Duplication** (MEDIUM): Two risk engines unified

---

## Phase 40: Frontend Enhancement — E2E Workflow UI
- **Sprints**: 138-140
- **Story Points**: ~30
- **Status**: Completed

### Core Problem
Backend API was 95% ready (~50+ endpoints), but frontend lacked pages and components for the full E2E workflow. 4 critical gaps: Chat not connected to new pipeline, no Session management UI, no Task tracking UI, no Knowledge/Memory management UI.

### New Files Added

**Frontend — API Endpoints**
| File | Purpose |
|------|---------|
| `frontend/src/api/endpoints/orchestrator.ts` | Orchestrator Chat API client |
| `frontend/src/api/endpoints/sessions.ts` | Session CRUD + Recovery API client |
| `frontend/src/api/endpoints/tasks.ts` | Task CRUD API client |
| `frontend/src/api/endpoints/knowledge.ts` | Knowledge base API client |
| `frontend/src/api/endpoints/memory.ts` | Memory system API client |

**Frontend — Custom Hooks**
| File | Purpose |
|------|---------|
| `frontend/src/hooks/useOrchestratorChat.ts` | Orchestrator chat hook (SSE event handling) |
| `frontend/src/hooks/useSessions.ts` | Session management hooks (CRUD + Resume) |
| `frontend/src/hooks/useTasks.ts` | Task management hooks |
| `frontend/src/hooks/useKnowledge.ts` | Knowledge base hooks |
| `frontend/src/hooks/useMemory.ts` | Memory system hooks |

**Frontend — New Pages**
| File | Purpose |
|------|---------|
| `frontend/src/pages/sessions/SessionsPage.tsx` | Session list page (active + recoverable sessions) |
| `frontend/src/pages/sessions/SessionDetailPage.tsx` | Session detail page |
| `frontend/src/pages/tasks/TaskDashboardPage.tsx` | Task dashboard (dispatch tracking + progress) |
| `frontend/src/pages/tasks/TaskDetailPage.tsx` | Task detail page |
| `frontend/src/pages/knowledge/KnowledgePage.tsx` | Knowledge base management (upload, index, search) |
| `frontend/src/pages/memory/MemoryPage.tsx` | Memory viewer (search history memories) |

**Frontend — Chat Inline Components**
| File | Purpose |
|------|---------|
| `frontend/src/components/unified-chat/IntentStatusChip.tsx` | Inline intent/risk/mode status indicator in chat messages |
| `frontend/src/components/unified-chat/TaskProgressCard.tsx` | Inline task progress card with progress bar in chat timeline |
| `frontend/src/components/unified-chat/MemoryHint.tsx` | Memory hint bar above chat input showing relevant memories |

### Modified Files
| File | Change |
|------|--------|
| Sidebar navigation | Added entries: Sessions, Task Center, Knowledge Base, Memory System |
| `frontend/src/pages/UnifiedChat.tsx` | Enhanced to support orchestrator pipeline connection |
| ChatHistoryPanel | Added "Recoverable Sessions" section alongside existing thread list |

### Architecture Changes
- **Chat-Centric Design**: Core workflow stays in Chat page; inline cards (IntentStatusChip, TaskProgressCard, MemoryHint) replace page jumps
- **Progressive Disclosure**: Simple Q&A shows minimal UI; Workflow/Swarm mode expands to show detailed components
- **Sidebar Navigation Expansion**: 5 new entries (Sessions, Tasks, Knowledge, Memory + enhanced Chat)
- **React Query Integration**: All new pages/hooks use React Query for data fetching with caching
- **Zustand State Management**: Consistent state management across new components

### Features Added
- Users can send requests to `/orchestrator/chat` from Chat page
- Session list with all sessions + Resume for interrupted sessions
- Task Dashboard tracking dispatched task progress
- Knowledge base page: document upload, index status, search
- Memory page: view and search historical memories
- Inline IntentStatusChip showing intent/risk/mode in chat
- Inline TaskProgressCard with progress bar for dispatched tasks
- MemoryHint above input showing relevant past memories
- All new pages use Shadcn UI + TypeScript + React Query

### Issues Fixed
- **Chat Not Connected** (CRITICAL): UnifiedChat now routes to `/orchestrator/chat`
- **No Session Management** (HIGH): Full Session CRUD + Resume UI
- **No Task Visibility** (HIGH): Task Dashboard with real-time progress
- **No Knowledge/Memory UI** (MEDIUM): Management pages for both systems

---

## Phase 41: Chat Pipeline Integration — E2E Visualization
- **Sprints**: 141-143
- **Story Points**: ~28
- **Status**: In Planning

### Core Problem
Phase 40 built standalone pages and components, but UnifiedChat still used old orchestration flow (REST one-shot call), not connected to the new `/orchestrator/chat` SSE streaming pipeline. Users couldn't see intent classification, task dispatch, tool calls, or memory retrieval steps in real-time.

### Planned Changes

**Architecture Decision**: Unified SSE Pipeline (Plan A selected)
- POST `/orchestrator/chat` sends message, gets session_id + sync response
- SSE `/ag-ui/run-v2` receives intermediate events (thinking, tools, progress)
- Frontend-only changes, no backend modifications needed

**Key Modifications Planned**
| File | Change |
|------|--------|
| `pages/UnifiedChat.tsx` | Eliminate dual path, unify to orchestrator pipeline |
| `hooks/useUnifiedChat.ts` | Redirect `sendMessage()` to `/orchestrator/chat` |
| `hooks/useOrchestratorChat.ts` | Enhanced SSE event processing for pipeline intermediate events |
| `components/unified-chat/MessageList.tsx` | Extended timeline supporting 4 item types (intent, task, tool, memory) |
| `components/unified-chat/ChatArea.tsx` | Pass orchestration metadata to MessageList |

**Sprint 141 (~10 SP)**: Chat -> Orchestrator Pipeline connection
**Sprint 142 (~10 SP)**: Inline component embedding + tool call display
**Sprint 143 (~8 SP)**: Memory integration + Session Resume UI + polish

### Planned Features
- IntentStatusChip displayed after each user message (intent + risk + execution mode)
- TaskProgressCard with real-time progress when tasks are dispatched
- ToolCallTracker showing tool execution in real-time
- LLM response with true token streaming (replacing fake typewriter effect)
- MemoryHint above input when relevant memories exist
- Session Resume restores conversation history with previous pipeline state
- All 10 E2E steps have visual representation in Chat

---

## Phase 42: E2E Pipeline Deep Integration — SSE + Task Dispatch + Swarm UI
- **Sprints**: 144-147
- **Story Points**: ~40
- **Status**: In Planning (current branch: feature/phase-42-deep-integration)

### Core Problem
Phase 41 connected Chat to the pipeline, but 5 critical blockers remained:
1. **FrameworkSelector empty classifiers**: `classifiers=[]` at init, everything routes to CHAT_MODE
2. **AgentHandler no Function Calling**: Uses `generate()` not `tool_use` API; LLM cannot actually invoke tools
3. **SSE completely disconnected**: MediatorEventBridge exists but no endpoint uses it
4. **OrchestratorMemoryManager.memory_client=None**: Bootstrap doesn't pass mem0/UnifiedMemoryManager
5. **Session/Checkpoint in-memory only**: Mediator uses Python dict, SessionRecoveryManager has no API

### Planned Changes

**Sprint 144 (~10 SP)**: FrameworkSelector + Function Calling + Memory Fix
| Story | Description |
|-------|-------------|
| S144-1 | Register LLM-based classifier in FrameworkSelector; combine keyword + RoutingDecision rules |
| S144-2 | Replace `generate()` with Azure OpenAI function calling API; define 6 tool schemas |
| S144-3 | Bootstrap passes UnifiedMemoryManager to OrchestratorMemoryManager |

**Sprint 145 (~12 SP)**: Orchestrator SSE Streaming Endpoint
| Story | Description |
|-------|-------------|
| S145-1 | `POST /orchestrator/chat/stream` SSE endpoint; pipeline events per step |
| S145-2 | Frontend SSE reception; real token streaming replaces typewriter |
| S145-3 | MediatorEventBridge maps pipeline events to AG-UI events |

**Sprint 146 (~10 SP)**: Swarm UI Integration + HITL Approval
| Story | Description |
|-------|-------------|
| S146-1 | AgentSwarmPanel embedded in Chat; swarmStore populated via SSE |
| S146-2 | HITL approval flow: high-risk ops pause pipeline, SSE pushes APPROVAL_REQUIRED |
| S146-3 | Fix GuidedDialogEngine and HITLController initialization |

**Sprint 147 (~8 SP)**: Session Persistence + RAG + Checkpoint + QA
| Story | Description |
|-------|-------------|
| S147-1 | Mediator uses ConversationStateStore (Redis/PostgreSQL) instead of Python dict |
| S147-2 | CheckpointStorage switched to PostgresCheckpointStorage |
| S147-3 | search_knowledge tool callable via function calling; results injected into LLM prompt |
| S147-4 | 6 scenarios (A-F) fully demonstrable in Chat; Playwright automation |

### Planned Architecture Changes
- **New SSE Endpoint**: `POST /orchestrator/chat/stream` with pipeline events: PIPELINE_START -> ROUTING_COMPLETE -> APPROVAL_REQUIRED -> AGENT_THINKING -> TOOL_CALL_START -> TOOL_CALL_END -> TEXT_DELTA -> TASK_DISPATCHED -> SWARM_WORKER_START -> SWARM_PROGRESS -> PIPELINE_COMPLETE
- **Function Calling**: AgentHandler switches from text generation to Azure OpenAI function calling with 6 tool schemas (create_task, dispatch_workflow, dispatch_swarm, assess_risk, search_memory, search_knowledge)
- **Intelligent Mode Selection**: FrameworkSelector uses keyword + RoutingDecision combination rules instead of empty classifiers
- **Swarm in Chat**: AgentSwarmPanel and WorkerCards rendered inside Chat area via swarmStore populated by SSE events
- **HITL Pipeline Pause**: Async event + callback pattern allows pipeline to pause mid-execution for human approval
- **Session Persistence**: Mediator state migrated from Python dict to Redis/PostgreSQL
- **RAG in Pipeline**: search_knowledge available as function calling tool; results feed into LLM context

### Planned Features
- FrameworkSelector correctly routes to CHAT/WORKFLOW/SWARM modes
- LLM autonomously invokes tools via function calling
- True SSE streaming with per-step pipeline events
- Swarm AgentSwarmPanel with WorkerCards in Chat
- HITL approval inline in Chat (pause + approve/reject + resume)
- Session and checkpoint persisted to PostgreSQL
- RAG knowledge retrieval integrated into pipeline
- 6 E2E scenarios demonstrable with Playwright tests

---

## Summary: Phase 39-42 Delta

### Aggregate Metrics
| Metric | Value |
|--------|-------|
| Total Sprints | 14 (134-147) |
| Total Story Points | ~142 |
| New Backend Files | ~12+ (bootstrap, handlers, events, SSE) |
| New Frontend Files | ~18+ (5 API, 5 hooks, 5 pages, 3 chat components) |
| Status | Phase 39-40: Completed / Phase 41-42: In Planning |

### Key Transformation
**Before (Post Phase 38)**: All modules exist but unassembled — 7 handlers default to None, AG-UI uses old bridge, no background execution, no frontend for new features.

**After (Post Phase 42)**: Complete assembled pipeline with OrchestratorBootstrap, SSE streaming, function calling, Swarm UI in Chat, HITL approval flow, session persistence, and RAG integration. Frontend fully connected with 5 new pages and 3 inline chat components.

### Sprint Number Gap Note
Sprints 121-133 correspond to earlier work (MAF RC4 upgrade, analysis, etc.) that is not part of the E2E Assembly plan. The E2E Assembly resumes at Sprint 134 (Phase 39) after Phase 38's Sprint 120.
