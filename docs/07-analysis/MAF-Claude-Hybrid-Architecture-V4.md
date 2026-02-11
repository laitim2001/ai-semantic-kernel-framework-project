# IPA Platform: MAF + Claude Agent SDK Hybrid Architecture

> **Version**: 4.0
> **Date**: 2026-02-11
> **Positioning**: Agent Orchestration Platform
> **Phase**: 29 Completed (106 Sprints, ~2400 Story Points)
> **Verification**: 5 specialized analysis agents, parallel deep codebase scan
> **Previous**: V3.0 (2026-02-09)

---

## How to Read This Document

This document describes the **real state** of the IPA Platform codebase as verified on 2026-02-11.

| Status Label | Definition |
|-------------|------------|
| **REAL** | Code exists and performs its stated function |
| **REAL+MOCK** | Real implementation + Mock fallback (intentional design for offline dev) |
| **MIXED** | Has real logic but contains mock fallbacks or partial stubs |
| **STUB** | Code compiles but returns hardcoded/fake data |
| **EMPTY** | Directory exists but contains no implementation |

All file counts and line counts are from direct filesystem inspection (Glob/Grep).

---

## 1. Executive Summary

IPA Platform is an **Agent Orchestration Platform** that coordinates AI agent clusters through the Microsoft Agent Framework (MAF) + Claude Agent SDK hybrid architecture. It handles tasks requiring judgment, expertise, and human-in-the-loop collaboration.

### Platform Positioning

```
IPA Platform = Agent Orchestration Platform

「不是 n8n/Power Automate 的替代品，
  而是處理 n8n 無法處理的那些任務」

MAF (Microsoft Agent Framework)
  - 結構化編排與治理 (8 Builder Adapters)
  - 多 Agent 協作模式 (Handoff, GroupChat, Magentic)
  - 檢查點與狀態持久化
  - 企業級審計追蹤

Claude Agent SDK
  - 自主執行與深度推理
  - Agentic Loop (自主迭代直到完成)
  - Extended Thinking (複雜分析)
  - 並行 Worker 執行

AG-UI Protocol
  - 即時 Agent 狀態串流 (SSE)
  - Human-in-the-Loop 審批
  - 思考過程可視化
  - Agent Swarm 群集即時視覺化

MCP (Model Context Protocol)
  - 統一工具存取介面
  - 5 個 MCP Server (Azure, Shell, Filesystem, SSH, LDAP)
  - 28 種權限模式、16 種審計模式
```

### Architecture Overview

```
Frontend (React 18 + TypeScript + Vite, port 3005)
    |
    | HTTP / SSE
    v
Backend (FastAPI + Uvicorn, port 8000)
    |
    +-- api/v1/           39 route modules, 534 endpoints, 47 routers
    +-- integrations/     15 modules, ~314 .py files
    +-- domain/           19 modules, 112 .py files
    +-- infrastructure/   22 files (messaging EMPTY, storage EMPTY)
    +-- core/             23 files (performance, sandbox, security)
    |
    v
PostgreSQL 16 + Redis 7 + RabbitMQ (unconfigured)
```

### Key Numbers

| Metric | Count | Notes |
|--------|-------|-------|
| Backend .py files | ~630+ | integrations + domain + infra + core + api |
| Backend estimated LOC | ~130,000+ | |
| Frontend .tsx/.ts files | 203 | 110 components, 39 pages, 19 hooks, 3 stores |
| API endpoints | 534 | Across 39 route modules |
| Registered routers | 47 | In api/v1/__init__.py |
| Frontend routes | 25 | In App.tsx |
| Test files | 305 | unit 241, integration 24, e2e 19, perf 10, security 5, load 2, mocks 2, root 2 |
| Integration modules | **15** | V3 claimed 16; actual is 15 |
| Domain modules | 19 | 13 Real, 6 Mixed |
| Database ORM models | 9 | Agent, Workflow, Execution, Checkpoint, AuditLog, Session, Message, Attachment, User |

### V3 -> V4 Key Changes

| Item | V3 (2026-02-09) | V4 (2026-02-11) | Change |
|------|-----------------|-----------------|--------|
| Integration modules | 16 | **15** | Only 15 directories exist |
| MAF Builders | 12 | **8** | 6 claimed builders do not exist as files |
| Frontend files | ~180 | **203** | More precise count including all .ts/.tsx |
| Files >800 lines | 15 | **34** | V3 undercounted (26 backend + 8 frontend) |
| Vite proxy bug | Not reported | **Port 8010 != 8000** | New finding |
| Pages with mock fallback | Not reported | **10 pages** | New finding |
| `pass` statements | Not reported | **243 in 102 files** | New finding |

---

## 2. Architecture Layer Model (11 Layers)

### Layer Summary Table

| Layer | Component | Files | Status | Key Issues |
|-------|-----------|-------|--------|------------|
| L1 | Frontend | 203 .tsx/.ts | REAL | ReactFlow not installed; 54 console.log; vite proxy port wrong (8010); 10 pages silent mock fallback |
| L2 | API Routes | 137 route files | 26 Real / 11 Mixed / 2 Stub | autonomous/, rootcause/ are pure stubs |
| L3 | AG-UI Protocol | 23 files | REAL | InMemoryThreadRepository, InMemoryCache |
| L4 | Orchestration Entry | 39 files | REAL+MOCK | 14 Mock classes in __init__.py; InMemoryApprovalStorage |
| L5 | Hybrid Layer | 60 files | REAL | ContextSynchronizer: NO thread locks (critical) |
| L6 | MAF Builder Layer | 53 files | REAL+MOCK | **8 actual builders** (not 12); _MockGroupChatWorkflow |
| L7 | Claude SDK Layer | 47 files | REAL | Clean, 1 minor TODO |
| L8 | MCP Layer | 43 files | REAL | InMemoryTransport, InMemoryAuditStorage |
| L9 | Supporting Modules | 42 files | PARTIAL | correlation/rootcause return hardcoded fake data |
| L10 | Domain Layer | 112 files | 13 Real / 6 Mixed | sessions/ is largest (33 files) |
| L11 | Infrastructure | 22 files + 23 core | messaging EMPTY, storage EMPTY | No Alembic migrations |

---

### L1: Frontend (React 18 + TypeScript + Vite)

**Port**: 3005 | **Total files**: 203 .tsx/.ts

#### Pages (39 files, 25 routes)

| Route | Page | Status |
|-------|------|--------|
| `/dashboard` | DashboardPage | REAL (React Query + sub-components) |
| `/chat` | UnifiedChat | REAL (main chat interface) |
| `/agents` (+CRUD) | AgentsPage, Create, Edit, Detail | REAL + mock fallback |
| `/workflows` (+CRUD) | WorkflowsPage, Create, Edit, Detail | REAL + mock fallback |
| `/templates` | TemplatesPage | REAL + mock fallback |
| `/approvals` | ApprovalsPage | REAL + mock fallback |
| `/audit` | AuditPage | REAL + mock fallback |
| `/performance` | PerformancePage | REAL |
| `/devui/*` | DevUI (6 sub-pages) | REAL |
| `/ag-ui-demo` | AGUIDemoPage (7-feature demo) | REAL |
| `/swarm-test` | SwarmTestPage (mock + real modes) | REAL |
| `/login`, `/signup` | Auth pages | REAL |

**10 pages** contain `generateMock*()` fallback — show hardcoded data when API unreachable, with **no visual indicator** to user.

#### Components (110 .tsx files)

| Directory | Count | Key Items |
|-----------|-------|-----------|
| unified-chat/ (top) | 22 | ChatArea, ChatInput, MessageList, ChatHeader, OrchestrationPanel, ApprovalDialog, ToolCallTracker |
| unified-chat/agent-swarm/ | 15 + 4 hooks | AgentSwarmPanel, WorkerCard, WorkerDetailDrawer, ExtendedThinkingPanel, ToolCallsPanel |
| unified-chat/renderers/ | 3 | Image, Code, Text preview |
| ag-ui/advanced/ | 6 | CustomUIRenderer, DynamicForm, DynamicTable, DynamicChart |
| ag-ui/chat/ | 4 | ChatContainer, MessageBubble, MessageInput, StreamingIndicator |
| ag-ui/hitl/ | 4 | ApprovalBanner, ApprovalDialog, ApprovalList, RiskBadge |
| DevUI/ | 15 | EventDetail, Timeline, EventPanel, StatCard, EventPieChart, LiveIndicator |
| ui/ (shadcn) | 17 | Badge, Button, Card, Dialog, Input, Progress, Select, Table, etc. |
| layout/ | 4 | AppLayout, Header, Sidebar, UserMenu |
| shared/ | 3 | EmptyState, LoadingSpinner, StatusBadge |
| auth/ | 1 | ProtectedRoute |

#### Hooks (19 total)

| Location | Count | Key Hooks |
|----------|-------|-----------|
| src/hooks/ | 15 | useUnifiedChat, useAGUI, useHybridMode, useApprovalFlow, useCheckpoints, useDevToolsStream, useOrchestration, useSwarmMock, useSwarmReal |
| agent-swarm/hooks/ | 4 | useSwarmEvents, useSwarmEventHandler, useSwarmStatus, useWorkerDetail |

Note: 4 hooks not exported from barrel (useChatThreads, useFileUpload, useDevTools, useOrchestration).

#### Stores (3 Zustand stores)

| Store | Path | Middleware |
|-------|------|-----------|
| useAuthStore | store/authStore.ts | persist (localStorage) |
| useUnifiedChatStore | stores/unifiedChatStore.ts | devtools + persist |
| useSwarmStore | stores/swarmStore.ts | devtools + immer |

Note: `store/` vs `stores/` split is historical artifact.

#### Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| react | ^18.2.0 | UI framework |
| zustand | ^4.4.7 | State management |
| @tanstack/react-query | ^5.17.0 | Server state |
| tailwindcss | ^3.4.1 | CSS |
| 11x @radix-ui/* | Various | Shadcn UI primitives |
| **@xyflow/react** | **NOT INSTALLED** | **Workflow visualization missing** |

**Vite Config Issue**: `vite.config.ts` proxies `/api` to `http://localhost:8010`, but backend runs on port **8000**. Dev proxy fails unless `VITE_API_URL` is manually set.

---

### L2: API Routes (FastAPI)

**Port**: 8000 | **Modules**: 39 | **Files**: 137 | **Endpoints**: 534 | **Routers**: 47

#### Status Breakdown

| Status | Count | Key Modules |
|--------|-------|-------------|
| **REAL** | 26 | agents, workflows, executions, checkpoints, dashboard, connectors, triggers, prompts, audit, notifications, routing, templates, learning, devtools, versioning, concurrent, handoff, nested, code_interpreter, mcp, claude_sdk, ag_ui, auth, files, sandbox, memory, a2a, swarm |
| **MIXED** | 11 | cache, groupchat, planning, performance, sessions, hybrid, orchestration, patrol, correlation |
| **STUB** | 2 | autonomous (in-memory dict, simulated progress), rootcause (hardcoded templates) |

#### Largest API Modules

| Module | Endpoints | Files |
|--------|-----------|-------|
| planning/ | 46 | 3 |
| groupchat/ | 42 | 4 |
| claude_sdk/ | 40 | 9 (7 sub-routers) |
| orchestration/ | 35 | 6 |
| ag_ui/ | 29 | 5 |
| sessions/ | 23 | 5 |

---

### L3: AG-UI Protocol

**Files**: 23 | **Est. LOC**: ~5,000 | **Status**: REAL

| Component | Description |
|-----------|-------------|
| HybridEventBridge | SSE bridge: HybridOrchestrator -> frontend |
| Event Converters | MAF/Claude events -> AG-UI format |
| Thread Manager | Chat thread persistence |
| Swarm Events | Phase 29 custom events for swarm visualization |
| Features | AgenticChat, GenerativeUI, HumanInLoop, ToolRendering, PredictiveUI, SharedStateSync, ToolUI |

**Issue**: `InMemoryThreadRepository` and `InMemoryCache` are defaults — thread history lost on restart.

---

### L4: Phase 28 Orchestration Entry

**Files**: 39 | **Est. LOC**: ~16,000 | **Status**: REAL+MOCK

Three-tier intent routing architecture:

```
User Input
    |
    v
InputGateway (source detection + validation)
    |
    v
BusinessIntentRouter (three-tier waterfall)
    |-- Layer 1: PatternMatcher (regex, <10ms)
    |-- Layer 2: SemanticRouter (vector similarity, Azure OpenAI embeddings)
    |-- Layer 3: LLMClassifier (Claude Haiku / Azure GPT)
    |
    v
GuidedDialogEngine (multi-turn clarification)
    |
    v
RiskAssessor (risk scoring + policy check)
    |
    v
HITLController (human approval when needed)
```

**Critical Issue — 15 Mock classes in production source**:

These are exported in `orchestration/__init__.py` as public API:

| Mock Class | File |
|------------|------|
| MockBusinessIntentRouter | intent_router/router.py |
| MockSemanticRouter | semantic_router/router.py |
| MockLLMClassifier | llm_classifier/classifier.py |
| MockCompletenessChecker | completeness/checker.py |
| MockGuidedDialogEngine | guided_dialog/engine.py |
| MockConversationContextManager | guided_dialog/context_manager.py |
| MockQuestionGenerator | guided_dialog/generator.py |
| MockLLMClient | guided_dialog/generator.py |
| MockInputGateway | input_gateway/gateway.py |
| MockSchemaValidator | input_gateway/schema_validator.py |
| MockBaseHandler | source_handlers/base_handler.py |
| MockServiceNowHandler | source_handlers/servicenow_handler.py |
| MockPrometheusHandler | source_handlers/prometheus_handler.py |
| MockUserInputHandler | source_handlers/user_input_handler.py |
| MockNotificationService | hitl/controller.py |

Plus `InMemoryApprovalStorage` and `InMemoryDialogSessionStorage` — HITL approval records lost on restart.

---

### L5: Hybrid Layer

**Files**: 60 | **Est. LOC**: ~21,000 | **Status**: REAL

| Component | Description | LOC |
|-----------|-------------|-----|
| HybridOrchestratorV2 | Main MAF+Claude coordinator | 1,254 |
| ContextSynchronizer | Cross-framework state sync | ~500 |
| RiskEngine | Risk-based framework selection | ~600 |
| FrameworkSwitcher | Runtime MAF/Claude SDK switching | ~800 |
| IntentRouter | Intent classification | ~400 |
| CheckpointStorage | 4 backends: Postgres, Redis, Memory, Filesystem | ~500 |

**Critical Bug**: `ContextSynchronizer` uses plain Python dict with **NO asyncio.Lock or threading.Lock**. Concurrent access will corrupt state.

---

### L6: MAF Builder Layer

**Files**: 53 | **Est. LOC**: ~37,000+ | **Status**: REAL+MOCK (most mature layer)

#### Actual Builders: 8 (V3 claimed 12 — corrected)

| Builder Adapter | File | LOC | MAF Import |
|----------------|------|-----|------------|
| ConcurrentBuilderAdapter | concurrent.py | 1,633 | `ConcurrentBuilder` |
| HandoffBuilderAdapter | handoff.py | 994 | `HandoffBuilder` |
| GroupChatBuilderAdapter | groupchat.py | 1,912 | `GroupChatBuilder` |
| MagenticBuilderAdapter | magentic.py | 1,809 | `MagenticBuilder`, `StandardMagenticManager` |
| AgentExecutorAdapter | agent_executor.py | ~800 | `ChatAgent`, `ChatMessage`, `Role` |
| CodeInterpreterAdapter | code_interpreter.py | ~600 | `AssistantManagerService` |
| NestedWorkflowAdapter | nested_workflow.py | 1,307 | `WorkflowBuilder` |
| PlanningAdapter | planning.py | 1,364 | `MagenticBuilder` |

**V3 claimed 12 builders. These 6 do NOT exist as separate builder files:**

| Claimed | Reality |
|---------|---------|
| SequentialAgent | Functionality in nested_workflow.py factory function |
| SelectorAgent | Functionality in edge_routing.py as ConditionalRouter |
| UserProxyAgent | Functionality in handoff_hitl.py as HITLManager |
| TaskCentricAgent | **Not implemented** |
| MultiModalAgent | **Not implemented** |
| HybridAgent | hybrid/ module is framework switching, not an agent builder |

Additional components: GroupChatVotingAdapter, GroupChatOrchestrator, HITLManager, workflow executor + migration files, `_MockGroupChatWorkflow` fallback.

---

### L7: Claude SDK Layer

**Files**: 47 | **Est. LOC**: ~15,000 | **Status**: REAL (cleanest integration)

| Sub-module | Files | Description |
|------------|-------|-------------|
| autonomous/ | 7 | Analyzer, Planner, Executor, Verifier, Retry, Fallback, SmartFallback |
| hybrid/ | 6 | Claude-side hybrid coordination |
| hooks/ | 5 | Lifecycle hooks (base + implementations) |
| mcp/ | 5 | MCP tool integration for Claude agents |
| tools/ | 5 | Tool registry and converters |
| core/ | 4 | ClaudeSDKClient, configuration |
| Other | 15 | Extended thinking, context, helpers |

Only 1 minor TODO (`tools/registry.py`). No Mock classes.

---

### L8: MCP Layer

**Files**: 43 | **Est. LOC**: ~12,500 | **Status**: REAL

5 MCP Servers:

| Server | Files | Description |
|--------|-------|-------------|
| Azure | 4 | Azure resource management (real Azure SDK calls) |
| Filesystem | 3 | Local file operations |
| LDAP | 3 | Directory services |
| Shell | 3 | Command execution |
| SSH | 3 | Remote server management |

Core: MCPClient, ServerRegistry, PermissionManager (28 permission modes, 16 audit modes).

**Issues**: `InMemoryTransport` and `InMemoryAuditStorage` — MCP audit logs not persisted.

---

### L9: Supporting Modules

| Module | Files | Est. LOC | Status | Notes |
|--------|-------|----------|--------|-------|
| patrol/ | 11 | ~2,500 | PARTIAL | PatrolAgent + 5 check types; may not connect to real monitoring |
| swarm/ | 7 | ~2,700 | **REAL** | Thread-safe (RLock), optional Redis, cleanest module |
| llm/ | 6 | ~1,500 | REAL | Protocol + AzureOpenAI + intentional MockLLMService |
| memory/ | 5 | ~2,000 | PARTIAL | 3-layer (Redis + PostgreSQL + mem0); fallback to in-memory |
| learning/ | 5 | ~2,000 | REAL | FewShotLearner; requires initialize(); history in-memory only |
| audit/ | 4 | ~1,800 | REAL | DecisionTracker; in-memory + optional Redis; no persistent DB |
| correlation/ | 4 | ~1,800 | **STRUCTURAL STUB** | ALL 5 data methods return hardcoded fake objects |
| a2a/ | 4 | ~900 | REAL | Agent-to-Agent protocol; all state in dicts (no persistence) |
| rootcause/ | 3 | ~1,500 | **STRUCTURAL STUB** | Hardcoded historical cases; depends on correlation's fake data |

---

### L10: Domain Layer

**Files**: 112 | **Modules**: 19 | **Status**: 13 Real / 6 Mixed

#### Top Domain Modules

| Module | Files | Status | Description |
|--------|-------|--------|-------------|
| sessions/ | 33 | REAL | Session lifecycle, SSE, file analysis, tool approval, error codes, metrics, bookmarks |
| orchestration/ | 22 | MIXED | memory/ (InMemory default), multiturn/, planning/, nested/ |
| workflows/ | 11 | REAL | State machine, 4 executors, resume, deadlock detection |
| agents/ | 7 | MIXED | Built-in tools return mock data; mock response fallback |
| connectors/ | 6 | REAL | Dynamics365, ServiceNow, SharePoint |
| checkpoints/ | 3 | REAL | HITL approval/rejection workflow |
| auth/ | 3 | REAL | JWT authentication |

Other modules (2-3 files each): files, templates, audit, devtools, executions, learning, notifications, prompts, routing, sandbox, triggers, versioning.

---

### L11: Infrastructure

| Component | Files | Status | Details |
|-----------|-------|--------|---------|
| Database (session) | 1 | ACTIVE | Async SQLAlchemy, pool 5+10 |
| Database (models) | 8 | ACTIVE | 9 ORM classes |
| Database (repos) | 7 | ACTIVE | BaseRepository + 5 specific |
| Database (migrations) | 0 | **MISSING** | No Alembic setup anywhere |
| Cache (Redis) | 2 | ACTIVE | LLM cache with TTL, hit/miss stats (599 LOC) |
| Messaging (RabbitMQ) | 1 | **EMPTY** | Only `__init__.py` with 2-line comment |
| Storage | 0 | **EMPTY** | Directory exists with zero files |

Core subsystems (23 files): performance (9), sandbox (7), security (4), config (2), sandbox_config (1).

---

## 3. Dependency Graph

```
                    +------------------+
                    |   llm (Protocol  |
                    | + Azure OpenAI)  |
                    +--------+---------+
                             | used by
         +-------------------+-------------------+
         v                   v                   v
+----------------+  +----------------+  +------------------+
| agent_framework|  |   claude_sdk   |  |   orchestration  |
| (8 MAF builders)|  | (autonomous,   |  | (3-tier routing, |
|                |  |  hooks, tools) |  |  HITL, dialog)   |
+--------+-------+  +--------+-------+  +--------+---------+
         |                   |                    |
         +--------+----------+                    |
                  v                               |
          +---------------+                       |
          |    hybrid      |<---------------------+
          | (orchestrator) |
          +-------+-------+
                  |
          +-------+--------+
          v                v
+----------------+  +----------------+
|     ag_ui      |  |     swarm      |
| (SSE, events)  |  | (tracker, vis) |
+----------------+  +----------------+

+----------------+  +----------------+  +----------------+
|    memory      |--|   learning     |  |      mcp       |
| (3-layer)      |  | (few-shot)     |  | (5 servers)    |
+--------+-------+  +----------------+  +----------------+
         |
+--------+-------+  +----------------+  +----------------+
|  correlation   |--|   rootcause    |  |    patrol       |
| (STUB DATA)    |  | (STUB DATA)    |  | (checks)       |
+----------------+  +----------------+  +----------------+

+----------------+  +----------------+
|      a2a       |  |     audit      |
| (messaging)    |  | (decisions)    |
+----------------+  +----------------+
```

---

## 4. Known Issues (Verified 2026-02-11)

### Critical (Must Fix)

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| 1 | ContextSynchronizer: in-memory dict, **NO locks** | hybrid/context/sync/ | Concurrent access corrupts state |
| 2 | 15 Mock classes in orchestration public API | orchestration/__init__.py | Silent fallback to fake logic in production path |
| 3 | Correlation returns entirely **fake data** | correlation/analyzer.py L427-523 | All 5 data methods return hardcoded objects |
| 4 | RootCause returns **hardcoded cases** | rootcause/analyzer.py L203-236 | Root cause analysis is simulated |
| 5 | InMemoryApprovalStorage for HITL | orchestration/hitl/controller.py | Human approval records lost on restart |
| 6 | Messaging/RabbitMQ **completely empty** | infrastructure/messaging/ | No async messaging despite Docker config |
| 7 | Storage module **completely empty** | infrastructure/storage/ | No storage abstraction layer |
| 8 | No database migrations (Alembic) | N/A | Schema changes require manual DDL |

### High

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| 9 | InMemoryThreadRepository | ag_ui/thread/storage.py | Chat thread history lost on restart |
| 10 | InMemoryAuditStorage (MCP) | mcp/security/audit.py | MCP audit logs not persisted |
| 11 | InMemoryCheckpointStorage | hybrid/switching/switcher.py | Checkpoints volatile |
| 12 | A2A no persistent storage | integrations/a2a/ | Agent registry + messages lost on restart |
| 13 | Audit no persistent DB | integrations/audit/ | Decision records lost without Redis |
| 14 | Single Uvicorn worker + reload=True | main.py L238-243 | Production performance bottleneck |
| 15 | _MockGroupChatWorkflow in prod path | agent_framework/builders/groupchat.py | Fallback when MAF API fails |
| 16 | Vite proxy port mismatch | frontend/vite.config.ts | Proxies to 8010 instead of 8000 |
| 17 | 10 pages silent mock fallback | frontend/src/pages/ | Users see fake data without indicator |

### Medium

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| 18 | ReactFlow not installed | package.json | Workflow visualization non-functional |
| 19 | 54 console.log (46 runtime, 8 JSDoc) | frontend/src/ (12 files) | Performance + info leak |
| 20 | **34 files over 800 lines** (26 backend + 8 frontend) | See appendix | Maintainability |
| 21 | **243 `pass` statements in 102 files** | backend/src/ | Stub density indicator |
| 22 | 10 TODO in backend, 0 in frontend | Various | Code hygiene |
| 23 | store/ vs stores/ split | frontend/src/ | Inconsistent organization |
| 24 | 4 hooks not in barrel export | frontend/src/hooks/ | Import inconsistency |
| 25 | No tests for authStore/chatStore | frontend/src/ | Auth and chat stores untested |
| 26 | Root conftest.py DB fixtures commented out | backend/tests/conftest.py | Tests may not run against real DB |

---

## 5. InMemory/Mock Census

### InMemory Storage (6 instances in production path)

| # | Class | Module | File |
|---|-------|--------|------|
| 1 | InMemoryThreadRepository | ag_ui | thread/storage.py |
| 2 | InMemoryCache | ag_ui | thread/storage.py |
| 3 | InMemoryCheckpointStorage | hybrid | switching/switcher.py |
| 4 | InMemoryTransport | mcp | core/transport.py |
| 5 | InMemoryAuditStorage | mcp | security/audit.py |
| 6 | InMemoryApprovalStorage | orchestration | hitl/controller.py |

### Mock Classes in Production Source (18 instances)

| # | Class | Module |
|---|-------|--------|
| 1-15 | (See L4 table above: 15 Mock classes) | orchestration |
| 16 | _MockGroupChatWorkflow | agent_framework |
| 17 | Mock mode in executor | agent_framework |
| 18 | MockLLMService (intentional) | llm |

### API-Level In-Memory Stores

| API Route | Store | Risk |
|-----------|-------|------|
| api/v1/autonomous/ | AutonomousTaskStore (dict) | Data lost on restart |
| api/v1/rootcause/ | RootCauseStore (dict) | Data lost on restart |
| api/v1/hybrid/switch_routes | InMemoryCheckpointStorage | Checkpoints volatile |
| api/v1/orchestration/approval_routes | InMemoryApprovalStorage | Approvals lost |
| api/v1/orchestration/intent_routes | MockBusinessIntentRouter | Silent mock fallback |
| api/v1/orchestration/dialog_routes | create_mock_dialog_engine() | Silent mock fallback |
| domain/orchestration/memory/ | InMemoryConversationMemoryStore | Default memory store |
| api/v1/cache/ | AsyncMock Redis client | Cache disabled gracefully |

---

## 6. Test Coverage

**Total test files**: 305

| Category | Files | Key Areas |
|----------|-------|-----------|
| unit/ | 241 | root-level (84), integrations (114), api (18), orchestration (7), performance (6), swarm (6), domain (5) |
| integration/ | 24 | sessions, hybrid, orchestration, swarm |
| e2e/ | 19 | ag_ui, swarm, general workflows |
| performance/ | 10 | swarm, general |
| security/ | 5 | Auth, injection, XSS |
| load/ | 2 | Locust load tests |
| mocks/ | 2 | agent_framework mocks |

**Notable**: Root `conftest.py` has database/Redis/agent fixtures **all commented out**.

---

## 7. What the Platform Can and Cannot Do

### Can Do (verified working code paths)

1. **Define and manage agents** — CRUD via DB, 8 MAF builder types, Claude SDK autonomous agents
2. **Execute multi-agent workflows** — sequential, parallel, handoff, group chat, magentic patterns
3. **Route user intent** — three-tier system (pattern -> semantic -> LLM), with mock fallback
4. **Coordinate HITL approvals** — checkpoint, approve/reject, notifications (records in-memory)
5. **Stream real-time agent state** — SSE via AG-UI protocol
6. **Visualize agent swarm** — Phase 29, 15 frontend components + backend tracker
7. **Manage chat sessions** — file upload, tool calls, history, error handling
8. **Connect to 5 MCP tool servers** — Azure, Filesystem, LDAP, Shell, SSH
9. **Cache LLM responses** — Redis with TTL and hit/miss stats
10. **Provide developer tools** — execution traces, live monitoring, event filtering

### Cannot Do (verified gaps)

1. **Use RabbitMQ messaging** — empty module, zero Python code
2. **Visualize workflows as graphs** — ReactFlow not installed
3. **Perform real correlation analysis** — all data methods return hardcoded fakes
4. **Perform real root cause analysis** — hardcoded historical cases
5. **Persist HITL approvals across restarts** — InMemoryApprovalStorage
6. **Persist chat threads across restarts** — InMemoryThreadRepository
7. **Run database migrations** — no Alembic setup
8. **Run multiple workers** — single Uvicorn worker hardcoded
9. **Handle concurrent context sync safely** — no thread locks on ContextSynchronizer
10. **Store files via infrastructure layer** — storage/ directory is empty

---

## Appendix: Files Over 800 Lines (34 total)

### Backend (26 files)

| File | Lines |
|------|-------|
| integrations/agent_framework/builders/groupchat.py | 1,912 |
| api/v1/ag_ui/routes.py | 1,871 |
| integrations/agent_framework/builders/magentic.py | 1,809 |
| api/v1/groupchat/routes.py | 1,770 |
| integrations/agent_framework/builders/concurrent.py | 1,633 |
| api/v1/planning/routes.py | 1,488 |
| integrations/agent_framework/builders/planning.py | 1,364 |
| integrations/agent_framework/builders/workflow_executor.py | 1,308 |
| integrations/agent_framework/builders/nested_workflow.py | 1,307 |
| integrations/agent_framework/builders/workflow_executor_migration.py | 1,277 |
| integrations/hybrid/orchestrator_v2.py | 1,254 |
| integrations/orchestration/guided_dialog/context_manager.py | 1,163 |
| integrations/orchestration/guided_dialog/generator.py | 1,151 |
| api/v1/nested/routes.py | 1,146 |
| api/v1/concurrent/routes.py | 1,094 |
| integrations/ag_ui/bridge.py | 1,079 |
| integrations/agent_framework/builders/handoff_capability.py | 1,050 |
| integrations/agent_framework/builders/magentic_migration.py | 1,038 |
| integrations/agent_framework/builders/groupchat_migration.py | 1,028 |
| domain/sessions/tool_handler.py | 1,019 |
| api/v1/handoff/routes.py | 1,006 |
| integrations/agent_framework/builders/handoff_hitl.py | 1,005 |
| domain/orchestration/nested/context_propagation.py | 1,000 |
| integrations/agent_framework/builders/handoff.py | 994 |
| domain/connectors/sharepoint.py | 970 |
| domain/orchestration/nested/workflow_manager.py | 947 |

### Frontend (8 files)

| File | Lines |
|------|-------|
| hooks/useUnifiedChat.ts | 1,313 |
| pages/workflows/EditWorkflowPage.tsx | 1,040 |
| pages/agents/CreateAgentPage.tsx | 1,015 |
| hooks/useAGUI.ts | 982 |
| pages/agents/EditAgentPage.tsx | 958 |
| pages/UnifiedChat.tsx | 899 |
| pages/workflows/CreateWorkflowPage.tsx | 887 |
| pages/SwarmTestPage.tsx | 844 |

---

**Document End**
**Generated**: 2026-02-11 by 5 parallel analysis agents + synthesis
**Verification method**: Glob, Grep, file reading across entire codebase
**Next review**: After Phase 30 implementation
