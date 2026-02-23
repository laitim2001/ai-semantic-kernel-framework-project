# IPA Platform: MAF + Claude Agent SDK Hybrid Architecture

> **Version**: 6.0
> **Date**: 2026-02-11
> **Positioning**: Agent Orchestration Platform
> **Phase**: 29 Completed (106 Sprints, ~2400 Story Points)
> **Verification**: Agent Team (5 specialized teammates via TeamCreate) with cross-validation
> **Previous**: V5.0 (2026-02-11), V4.0 (2026-02-11), V3.0 (2026-02-09)

---

## How to Read This Document

Every number was verified by at least one of 5 parallel Agent Team members (backend-analyst, frontend-analyst, quality-auditor, infra-security, test-analyst). Disputed items were cross-validated by multiple agents. Where V5 had errors, the actual codebase was re-inspected.

| Status Label | Definition |
|-------------|------------|
| **REAL** | Code exists and performs its stated function |
| **REAL+MOCK** | Real implementation + Mock fallback for offline/testing |
| **STUB** | Code exists but returns hardcoded/fabricated data |
| **EMPTY** | Directory exists but contains no implementation |

---

## 1. Executive Summary

IPA Platform is an **Agent Orchestration Platform** that coordinates AI agent clusters through the Microsoft Agent Framework (MAF) + Claude Agent SDK hybrid architecture.

### Platform Positioning

```
IPA Platform = Agent Orchestration Platform

MAF (Microsoft Agent Framework)
  - 9 Builder Adapters (8 with MAF imports, 1 standalone)
  - Multi-Agent patterns: Handoff, GroupChat, Magentic, Concurrent
  - Checkpoint & state persistence
  - Enterprise audit trail

Claude Agent SDK
  - Autonomous execution & deep reasoning
  - Agentic Loop + Extended Thinking
  - Parallel Worker execution

AG-UI Protocol
  - Real-time SSE agent state streaming
  - Human-in-the-Loop approval
  - Agent Swarm visualization

MCP (Model Context Protocol)
  - 5 MCP Servers (Azure, Shell, Filesystem, SSH, LDAP)
  - 28 permission patterns, 16 audit patterns
```

### Architecture Overview

```
Frontend (React 18 + TypeScript + Vite, port 3005)
    |
    | HTTP / SSE (NOTE: vite proxy targets 8010, backend runs on 8000)
    v
Backend (FastAPI + Uvicorn, port 8000)
    |
    +-- api/v1/           39 route modules, 530 endpoints, 47 routers
    +-- integrations/     16 modules, ~314 .py files
    +-- domain/           20 modules, ~115 .py files
    +-- infrastructure/   22 files (messaging EMPTY, storage EMPTY)
    +-- core/             23 files (performance, sandbox, security)
    |
    v
PostgreSQL 16 + Redis 7 + RabbitMQ (empty, not connected)
```

### Key Numbers (V6 Verified)

| Metric | V6 Count | V5 Claim | Notes |
|--------|----------|----------|-------|
| Backend .py files | ~630+ | ~630+ | Unchanged |
| Backend estimated LOC | ~130,000+ | ~130,000+ | Unchanged |
| Frontend .tsx/.ts files | **203** | 203 | Unchanged |
| API endpoints | **530** | 540 | V5 overcounted by ~10 (sub-router duplicates) |
| Registered routers (top-level) | **47** | 47 | Unchanged |
| Nested router registrations | **60** | 60 | Unchanged |
| Frontend routes (navigable) | **25** | 25 | Unchanged |
| Frontend page .tsx files | **37** | 37 | Unchanged |
| Frontend components | **110** | ~110 | Unchanged |
| Frontend hooks | **20** | 19 | V5 missed 1 (16 in hooks/ + 4 in agent-swarm/) |
| Frontend stores | **3** | 3 | Unchanged |
| Integration modules | **16** | 15 | V5 undercounted by 1 |
| Domain modules | **20** | 19 | V5 undercounted by 1 |
| API route modules | **39** | 39 | Unchanged |
| MAF Builder adapter files | **9** | 9 | Unchanged |
| MAF-importing builders | **8** | 7 | V5 wrongly excluded agent_executor.py |
| Standalone builders | **1** | 2 | Only code_interpreter.py lacks MAF import |
| Test files (pure test_*) | **247** | 305 | V5 counted all .py including __init__.py/conftest |
| Test files (all .py in tests/) | **305** | 305 | Matches when including support files |
| Files >800 lines (src+frontend) | **57** | 55 | V5 missed 2 borderline files |
| Files >1500 lines | **5** | 5 | Unchanged |
| Mock classes (production src) | **18** | 16 | V5 missed nested MockContent + MockResponse |
| InMemory storage classes | **9** | 9 | Unchanged |
| console.log (frontend) | **54** | 45 | +9 since V5 |
| `pass` statements | **204 in 84 files** | 204/84 | Unchanged |
| Ellipsis `...` statements | **119 in 39 files** | Not counted | V5 completely missed this |
| Empty function bodies total | **~323** | 204 | V5 severely underestimated (pass + ...) |
| Alembic migrations | **6** | 6 | Unchanged |
| Database ORM models | **9** | 9 | Unchanged |
| Auth-protected routes | **38/530 (7%)** | Not measured | New metric |
| API test coverage | **13/39 (33%)** | Not measured | New metric |
| Frontend unit test files | **13** | Not measured | All from Phase 29 only |
| Hooks not exported from barrel | **6** | 4 | V5 missed useSwarmMock + useSwarmReal |

### V5 -> V6 Key Changes

| Item | V5 | V6 | Resolution |
|------|-----|-----|-----------|
| MAF-importing builders | 7 | **8** | agent_executor.py DOES have MAF imports (V5 was wrong) |
| Standalone builders | 2 | **1** | Only code_interpreter.py is standalone |
| Endpoints | 540 | **530** | V5 overcounted (sub-router duplicates) |
| Mock classes | 16 | **18** | Nested MockContent + MockResponse in generator.py |
| Files >800 lines | 55 | **57** | 2 borderline files added |
| console.log | 45 | **54** | 9 new since V5 |
| Hooks total | 19 | **20** | 16 + 4 agent-swarm |
| Hooks not in barrel | 4 | **6** | +useSwarmMock, +useSwarmReal |
| Domain modules | 19 | **20** | 1 missed |
| Integration modules | 15 | **16** | 1 missed |
| Empty function bodies | 204 | **~323** | pass(204) + ellipsis(119) |
| Test files distinction | 305 (all) | **247 pure + 58 support** | Clarification |

---

## 2. Architecture Layer Model (11 Layers)

### Layer Summary Table

| Layer | Component | Files | Status | Key Issues |
|-------|-----------|-------|--------|------------|
| L1 | Frontend | 203 .tsx/.ts | REAL | ReactFlow not installed; 54 console.log; vite proxy 8010≠8000; 10 pages silent mock fallback |
| L2 | API Routes | 137 route files | REAL+MIXED | Only 7% auth coverage (38/530 endpoints); no rate limiting |
| L3 | AG-UI Protocol | 23 files | REAL | InMemoryThreadRepository, InMemoryCache |
| L4 | Orchestration Entry | 39 files | REAL+MOCK | 18 Mock classes (V5 said 16); InMemoryApprovalStorage default |
| L5 | Hybrid Layer | 60 files | REAL | ContextSynchronizer: NO thread locks (CRITICAL) |
| L6 | MAF Builder Layer | 53 files (23 in builders/) | REAL+MOCK | 9 adapters (8 MAF-importing + 1 standalone) |
| L7 | Claude SDK Layer | 47 files | REAL | Clean, well-structured |
| L8 | MCP Layer | 43 files | REAL | InMemoryTransport, InMemoryAuditStorage |
| L9 | Supporting Modules | 42 files | PARTIAL | correlation/rootcause return hardcoded fake data |
| L10 | Domain Layer | ~115 files (20 modules) | 17 Real / 2 Mixed | sessions/ largest (33 files) |
| L11 | Infrastructure | 22 files + 23 core | messaging EMPTY, storage EMPTY | Alembic exists with 6 migrations |

---

### L1: Frontend (React 18 + TypeScript + Vite)

**Port**: 3005 | **Total files**: 203 .tsx/.ts

#### Pages (37 .tsx files under pages/, 25 navigable routes)

| Route | Page | Status |
|-------|------|--------|
| `/dashboard` | DashboardPage + 4 sub-components | REAL (React Query) |
| `/chat` | UnifiedChat | REAL (SSE streaming) |
| `/performance` | PerformancePage | REAL |
| `/agents` (+CRUD) | 4 pages | REAL + mock fallback |
| `/workflows` (+CRUD) | 4 pages | REAL + mock fallback |
| `/templates` | TemplatesPage | REAL + mock fallback |
| `/approvals` | ApprovalsPage | REAL + mock fallback |
| `/audit` | AuditPage | REAL + mock fallback |
| `/devui/*` | 7 DevUI pages | REAL |
| `/ag-ui-demo` | AGUIDemoPage + 8 sub-components | REAL |
| `/swarm-test` | SwarmTestPage | REAL (mock + real modes) |
| `/login`, `/signup` | Auth pages | REAL (JWT) |

**10 pages with `generateMock*()` fallback** (silent, no visual indicator):
ApprovalsPage, WorkflowsPage, WorkflowDetailPage, TemplatesPage, AuditPage, AgentsPage, AgentDetailPage, RecentExecutions, PendingApprovals, ExecutionChart

#### Components (110 .tsx files)

| Directory | Count | Key Items |
|-----------|-------|-----------|
| unified-chat/ (top) | 25 | ChatArea, ChatInput, MessageList, OrchestrationPanel, ApprovalDialog |
| unified-chat/renderers/ | 3 | Image, Code, Text preview |
| unified-chat/agent-swarm/ | 15 + 4 hooks | AgentSwarmPanel, WorkerCard, WorkerDetailDrawer |
| ag-ui/advanced/ | 7 | CustomUIRenderer, DynamicForm, DynamicTable, DynamicChart |
| ag-ui/chat/ | 5 | ChatContainer, MessageBubble, MessageInput, StreamingIndicator |
| ag-ui/hitl/ | 4 | ApprovalBanner, ApprovalDialog, ApprovalList, RiskBadge |
| DevUI/ | 15 | EventDetail, Timeline, EventPanel, StatCard, LiveIndicator |
| ui/ (shadcn) | 17 | Badge, Button, Card, Dialog, Input, Progress, Select, Table |
| layout/ | 4 | AppLayout, Header, Sidebar, UserMenu |
| shared/ | 3 | EmptyState, LoadingSpinner, StatusBadge |
| auth/ | 1 | ProtectedRoute |

#### Hooks (20 total)

| Location | Count | Key Hooks | Not in barrel |
|----------|-------|-----------|---------------|
| src/hooks/ | 16 | useUnifiedChat, useAGUI, useHybridMode, useApprovalFlow, useSwarmMock, useSwarmReal | useChatThreads, useDevTools, useFileUpload, useOrchestration, useSwarmMock, useSwarmReal (6 not exported) |
| agent-swarm/hooks/ | 4 | useSwarmEvents, useSwarmEventHandler, useSwarmStatus, useWorkerDetail | All exported from swarm barrel |

#### Stores (3 Zustand stores)

| Store | Path | Middleware |
|-------|------|-----------|
| useAuthStore | store/authStore.ts | persist (localStorage) |
| useUnifiedChatStore | stores/unifiedChatStore.ts | devtools + persist |
| useSwarmStore | stores/swarmStore.ts | devtools + immer |

Note: `store/` vs `stores/` split remains unresolved.

#### Frontend Issues

| Issue | Severity | Details |
|-------|----------|---------|
| Vite proxy port | HIGH | `vite.config.ts` line 30: proxy targets `localhost:8010`, backend on port 8000 |
| 10 silent mock pages | HIGH | `generateMock*()` with no visual indicator |
| 54 console.log | MEDIUM | Across 12 files (V5 said 45, +9 new). authStore.ts has 5 (potential auth info leak) |
| ReactFlow not installed | MEDIUM | `.claude/skills/react-flow/` exists but library never installed |
| 8 files >800 lines | MEDIUM | useUnifiedChat.ts (1313), EditWorkflowPage (1040), CreateAgentPage (1015), useAGUI (982) |
| 6 hooks not in barrel | LOW | useChatThreads, useDevTools, useFileUpload, useOrchestration, useSwarmMock, useSwarmReal |
| store/ vs stores/ split | LOW | Inconsistent directory naming |
| Unit tests only Phase 29 | LOW | 13 test files, all from agent-swarm. ~100 other components untested |

---

### L2: API Routes (FastAPI)

**Port**: 8000 | **Total**: 39 modules, 137 .py files, 530 endpoints, 47 top-level routers

#### Router Registration (47 top-level in api/v1/__init__.py)

| Group | Routers | Count |
|-------|---------|-------|
| Core CRUD | dashboard, agents, workflows, executions, checkpoints, connectors, cache, triggers, prompts, audit, notifications, routing, templates, learning, devtools, versioning | 16 |
| Orchestration patterns | concurrent, handoff, groupchat, planning, nested, performance | 6 |
| Integrations | code_interpreter, mcp, sessions, claude_sdk | 4 |
| Hybrid (4 sub-routers) | hybrid_context, hybrid_core, hybrid_risk, hybrid_switch | 4 |
| AG-UI + Auth | ag_ui, auth, files | 3 |
| Memory + Audit | memory, decision_audit | 2 |
| Sandbox + Autonomous | sandbox, autonomous | 2 |
| Supporting | a2a, patrol, correlation, rootcause | 4 |
| Orchestration Phase 28 | orchestration, orchestration_intent, orchestration_dialog, orchestration_approval | 4 |
| Phase 29 Swarm | swarm, swarm_demo | 2 |
| **Total** | | **47** |

Nested sub-routers: claude_sdk (7), sessions (3), code_interpreter (1), ag_ui (1), auth (1) = 13 nested. Total ~60.

Top endpoint-heavy modules: planning/routes.py (46), groupchat/routes.py (41), ag_ui/routes.py (25), nested/routes.py (16).

#### API Security Issues (V6 New)

| Issue | Severity | Evidence |
|-------|----------|----------|
| **Auth coverage 7%** | CRITICAL | Only 38/530 routes use `Depends(get_current_user)` |
| **No rate limiting** | CRITICAL | No slowapi/fastapi-limiter middleware; rate limiting only exists within tool execution hooks |
| **CORS mismatch** | HIGH | Default origins include `localhost:3000` but frontend runs on `3005` |
| **Hardcoded secret default** | HIGH | `secret_key = "change-this-to-a-secure-random-string"` in config.py |

---

### L3: AG-UI Protocol

**Files**: 23 | **Status**: REAL

- SSE Bridge for real-time streaming (`integrations/ag_ui/bridge.py`, 1079 LOC)
- HITL approval events
- Swarm CustomEvent streaming
- SharedState synchronization

**Issue**: `InMemoryThreadRepository` and `InMemoryCache` for thread storage (data lost on restart).

---

### L4: Orchestration Entry (Phase 28)

**Files**: 39 | **Status**: REAL+MOCK

Key components:
- **InputGateway**: Source detection + handler routing (419 LOC)
- **BusinessIntentRouter**: Three-tier cascade (PatternMatcher -> SemanticRouter -> LLMClassifier) (639 LOC)
- **GuidedDialogEngine**: Multi-turn conversation management (593 LOC)
- **RiskAssessor**: Context-aware risk scoring (639 LOC)
- **HITLController**: Approval workflow management (788 LOC)

**18 Mock classes** found in production source (V5 said 16, missed 2 nested):

| # | Class | File |
|---|-------|------|
| 1 | MockSemanticRouter | `orchestration/intent_router/semantic_router/router.py:376` |
| 2 | MockBusinessIntentRouter | `orchestration/intent_router/router.py:527` |
| 3 | MockLLMClassifier | `orchestration/intent_router/llm_classifier/classifier.py:325` |
| 4 | MockCompletenessChecker | `orchestration/intent_router/completeness/checker.py:347` |
| 5 | MockGuidedDialogEngine | `orchestration/guided_dialog/engine.py:505` |
| 6 | MockQuestionGenerator | `orchestration/guided_dialog/generator.py:512` |
| 7 | MockLLMClient | `orchestration/guided_dialog/generator.py:1006` |
| 8 | **MockContent** | `orchestration/guided_dialog/generator.py:1036` (V5 missed) |
| 9 | **MockResponse** | `orchestration/guided_dialog/generator.py:1040` (V5 missed) |
| 10 | MockConversationContextManager | `orchestration/guided_dialog/context_manager.py:546` |
| 11 | MockInputGateway | `orchestration/input_gateway/gateway.py:304` |
| 12 | MockSchemaValidator | `orchestration/input_gateway/schema_validator.py:405` |
| 13 | MockBaseHandler | `orchestration/input_gateway/source_handlers/base_handler.py:287` |
| 14 | MockUserInputHandler | `orchestration/input_gateway/source_handlers/user_input_handler.py:247` |
| 15 | MockServiceNowHandler | `orchestration/input_gateway/source_handlers/servicenow_handler.py:339` |
| 16 | MockPrometheusHandler | `orchestration/input_gateway/source_handlers/prometheus_handler.py:357` |
| 17 | MockNotificationService | `orchestration/hitl/controller.py:691` |
| 18 | MockLLMService | `integrations/llm/mock.py:32` |

Of these, 8 orchestration Mocks + 1 LLM Mock are publicly exported via `__init__.py`.

**Critical Issue**: `InMemoryApprovalStorage` is the DEFAULT storage for HITL approvals (line 743).

---

### L5: Hybrid Orchestration Layer

**Files**: 60 | **Status**: REAL

- **HybridOrchestratorV2** (1,254 LOC) - Main orchestration engine
- **FrameworkSelector** - MAF vs Claude SDK routing
- **ContextBridge** (932 LOC) - Cross-framework context transfer
- **ContextSynchronizer** - State sync between frameworks (TWO implementations found)
- **ModeSwitcher** (829 LOC) - Runtime framework switching with 4 trigger detectors

**CRITICAL Issue**: Both ContextSynchronizer implementations use plain `Dict` storage with NO locks:
1. `claude_sdk/hybrid/synchronizer.py:278` - `self._contexts: Dict[str, ContextState] = {}`
2. `hybrid/context/sync/synchronizer.py:63` - Claims "optimistic locking" in docstring but not implemented

---

### L6: MAF Builder Layer

**Files**: 53 total (23 in builders/) | **Status**: REAL+MOCK

#### Builder Adapter Files (9 files)

| # | File | LOC | MAF Import | Status |
|---|------|-----|------------|--------|
| 1 | `workflow_executor.py` | 1,308 | `WorkflowExecutor, SubWorkflowRequestMessage` | REAL |
| 2 | `concurrent.py` | 1,633 | `ConcurrentBuilder` | REAL |
| 3 | `groupchat.py` | 1,912 | `GroupChatBuilder` | REAL+MOCK |
| 4 | `handoff.py` | 994 | `HandoffBuilder, HandoffAgentUserRequest` | REAL |
| 5 | `nested_workflow.py` | 1,307 | `WorkflowBuilder, Workflow, WorkflowExecutor` | REAL+MOCK |
| 6 | `planning.py` | 1,364 | `MagenticBuilder, Workflow` | REAL |
| 7 | `magentic.py` | 1,809 | `MagenticBuilder, StandardMagenticManager` | REAL+MOCK |
| 8 | `agent_executor.py` | 699 | `ChatAgent, ChatMessage, Role` | REAL+MOCK |
| 9 | `code_interpreter.py` | 868 | **None** (uses Azure `AssistantManagerService`) | REAL |

**V6 Correction**: V5 incorrectly stated agent_executor.py lacks MAF imports. It DOES import from agent_framework. Only code_interpreter.py is standalone.

#### Extended/Support Files (9 files)

`groupchat_voting.py` (736), `handoff_capability.py` (1,050), `handoff_context.py` (855), `handoff_hitl.py` (1,005), `handoff_policy.py` (513), `handoff_service.py` (821), `groupchat_orchestrator.py` (883), `edge_routing.py` (884), `__init__.py` (805)

#### Migration Files (5 files)

`concurrent_migration.py` (688), `groupchat_migration.py` (1,028), `handoff_migration.py` (734), `magentic_migration.py` (1,038), `workflow_executor_migration.py` (1,277)

---

### L7: Claude SDK Layer

**Files**: 47 | **Status**: REAL

- `autonomous/` (8 files) - Analyzer, Planner, Executor, Verifier, Retry, Fallback, Types
- All use `from anthropic import AsyncAnthropic` for real API calls
- Extended Thinking support in analyzer
- SmartFallback with 6 strategies (RETRY, ALTERNATIVE, SKIP, ESCALATE, ROLLBACK, ABORT)

Clean, well-structured. The most consistently real module after Swarm.

---

### L8: MCP Layer

**Files**: 43 | **Status**: REAL

| Server | Directory | Key Feature |
|--------|-----------|-------------|
| Azure | `mcp/servers/azure/` (11 files) | VM, Resource, Monitor, Network, Storage tools |
| Filesystem | `mcp/servers/filesystem/` (5 files) | Sandboxed file access |
| LDAP | `mcp/servers/ldap/` (5 files) | Directory services |
| Shell | `mcp/servers/shell/` (5 files) | Command execution |
| SSH | `mcp/servers/ssh/` (5 files) | Remote access via paramiko |

**Issues**: `InMemoryTransport` and `InMemoryAuditStorage` for MCP audit logging.

---

### L9: Supporting Modules

**Files**: 42 | **Status**: PARTIAL

| Module | Files | Status | Notes |
|--------|-------|--------|-------|
| swarm/ | 7 | REAL | Thread-safe (RLock), optional Redis |
| a2a/ | 4 | REAL | In-memory registry only, no persistence |
| audit/ | 4 | REAL | DecisionTracker with optional Redis |
| patrol/ | 11 | REAL | PatrolAgent + 5 check types + scheduler |
| memory/ | 5 | REAL | 3-layer architecture (Redis + PostgreSQL + mem0) |
| learning/ | 3 | REAL | FewShotLearner |
| llm/ | 3 | REAL+MOCK | MockLLMService fallback |
| **correlation/** | **4** | **STUB** | **ALL 5 data methods return hardcoded fakes** |
| **rootcause/** | **4** | **STUB** | **Hardcoded 2 HistoricalCase, depends on correlation fakes** |

---

### L10: Domain Layer

**Files**: ~115 across 20 modules | **Status**: 17 Real / 2 Mixed

| Module | Files | Status |
|--------|-------|--------|
| sessions/ | 33 | Real (largest) |
| orchestration/ | 22 | Real |
| agents/ | 7 | Real |
| workflows/ | 11 | Real |
| connectors/ | 6 | Real |
| executions/ | 2 | Real |
| templates/ | 3 | Real |
| checkpoints/ | 3 | Real |
| auth/ | 3 | Real |
| files/ | 3 | Real |
| routing/ | 2 | Real |
| triggers/ | 2 | Real |
| devtools/ | 2 | Real |
| prompts/ | 2 | Real |
| versioning/ | 2 | Real |
| sandbox/ | 2 | Real |
| audit/ | 2 | Real |
| notifications/ | 2 | Mixed |
| learning/ | 2 | Mixed |

---

### L11: Infrastructure

**Files**: 22 (infrastructure) + 23 (core) | **Status**: PARTIAL

| Component | Status | Notes |
|-----------|--------|-------|
| PostgreSQL (database/) | REAL | 22 files, 9 ORM models, **6 Alembic migrations** |
| Redis (cache/) | REAL | 2 files, LLM response caching; 13 files import Redis across 7 modules |
| RabbitMQ (messaging/) | **EMPTY** | Only `__init__.py` with comment. aio-pika in requirements.txt but never imported |
| Storage (storage/) | **EMPTY** | Directory does not exist at all |

#### Database Models (9 tables)

AgentModel, WorkflowModel, ExecutionModel, CheckpointModel, SessionModel, MessageModel, AttachmentModel, UserModel, AuditLog

#### Docker Services

**docker-compose.yml** (6 services): PostgreSQL 16, Redis 7, RabbitMQ 3.12, Jaeger 1.53, Prometheus v2.48.0, Grafana 10.2.2

**docker-compose.override.yml** (3 services): n8n, Prometheus v2.45.0, Grafana 10.0.0

**Issue**: Prometheus and Grafana defined in BOTH files with different versions — will cause conflicts.

#### Dependencies

**Backend**: 42 packages (requirements.txt)
**Frontend**: 23 dependencies + 20 devDependencies (package.json)

---

## 3. Known Issues (V6 Verified, 27 items)

### CRITICAL (7)

| # | Issue | Evidence | Impact |
|---|-------|----------|--------|
| 1 | **ContextSynchronizer NO locks** | Two implementations, both use plain Dict, no Lock | Concurrent state corruption |
| 2 | **18 Mock classes in production src** | 17 in orchestration + 1 in llm/mock.py (9 exported via __init__.py) | Runtime mock contamination |
| 3 | **correlation/ returns fabricated data** | All 5 data methods return hardcoded objects; comment: "模擬實現" | Produces fake analysis |
| 4 | **rootcause/ returns hardcoded cases** | `get_similar_patterns()` returns 2 hardcoded HistoricalCase | Fake root cause analysis |
| 5 | **InMemoryApprovalStorage default** | `hitl/controller.py` line 743 | HITL approvals lost on restart |
| 6 | **9 InMemory storage classes** | Across 8 files | Data loss risk on restart |
| 7 | **Auth coverage only 7%** | 38/530 endpoints protected; vast majority unprotected | **V6 NEW** |

### HIGH (8)

| # | Issue | Evidence | Impact |
|---|-------|----------|--------|
| 8 | **No HTTP rate limiting** | No slowapi/fastapi-limiter; rate limiting only in tool hooks | API abuse risk. **V6 NEW** |
| 9 | **RabbitMQ completely empty** | `infrastructure/messaging/`: only comment, zero code | No async messaging |
| 10 | **Storage module missing** | `infrastructure/storage/`: does not exist | No storage abstraction |
| 11 | **Single Uvicorn worker + reload=True** | `main.py`: no `workers` param, `reload=True` hardcoded | Production bottleneck |
| 12 | **Vite proxy port mismatch** | `vite.config.ts`: proxy targets 8010, backend on 8000 | Frontend cannot reach backend |
| 13 | **10 pages silent mock fallback** | `generateMock*()` with no visual indicator | Users see fake data |
| 14 | **code_interpreter.py lacks MAF import** | Uses Azure AssistantManagerService, not agent_framework | MAF compliance gap |
| 15 | **CORS origins mismatch** | Default includes `localhost:3000` but frontend on 3005 | **V6 NEW** |

### MEDIUM (8)

| # | Issue | Evidence | Impact |
|---|-------|----------|--------|
| 16 | **57 files >800 lines** | 49 backend + 8 frontend (5 exceed 1,500 lines) | Maintainability |
| 17 | **ReactFlow not installed** | Not in package.json | Workflow visualization missing |
| 18 | **54 console.log** | 12 frontend files; authStore.ts has 5 (auth info leak risk) | Performance + leakage |
| 19 | **~323 empty function bodies** | 204 pass + 119 ellipsis across 84+39 files | Stub density |
| 20 | **Dual checkpoint systems** | `hybrid/checkpoint/` and `agent_framework/multiturn/` independent | Architecture confusion |
| 21 | **A2A in-memory only** | Plain dict registry, no persistence | Registry lost on restart |
| 22 | **Docker Compose conflict** | Prometheus/Grafana in base+override with different versions | **V6 NEW** |
| 23 | **API test coverage 33%** | 26/39 API modules have zero route tests | **V6 NEW** |

### LOW (4)

| # | Issue | Evidence | Impact |
|---|-------|----------|--------|
| 24 | **store/ vs stores/ split** | authStore in `store/`, others in `stores/` | Inconsistent naming |
| 25 | **37 page files** | Confirmed (V3/V4 overcounted at 39) | Documentation accuracy |
| 26 | **6 unexported hooks** | useChatThreads, useDevTools, useFileUpload, useOrchestration, useSwarmMock, useSwarmReal | Potential dead code |
| 27 | **Frontend unit tests Phase 29 only** | 13 test files, ~100 components untested | **V6 NEW** |

---

## 4. Architecture Strengths

| Area | Strength |
|------|----------|
| **Agent Swarm (Phase 29)** | Cleanest module. Thread-safe (RLock), well-tested (unit+integration+e2e+perf), proper separation |
| **Three-tier Intent Router** | Real cascade with per-tier latency tracking. Pattern -> Semantic -> LLM with graceful degradation |
| **Claude SDK Autonomous** | Real Anthropic API integration with Extended Thinking, structured planning, smart fallback |
| **Memory Architecture** | 3-layer design (Redis -> PostgreSQL -> mem0) is well-architected |
| **MCP Servers** | All 5 genuine implementations with proper JSON-RPC 2.0 protocol |
| **Alembic Migrations** | 6 schema migrations covering Sprint 72+ |
| **Security Testing** | 3 security test files with comprehensive attack fixtures (SQL injection, XSS, path traversal) |

---

## 5. V6 Accuracy Methodology

### What Changed from V5

V6 used **Agent Team** (TeamCreate) instead of subagents (Task tool). Key differences:
- Teammates communicate directly with each other for cross-validation
- Shared task list with self-coordination
- Each teammate has its own independent context window
- Total: 5 specialized teammates running in parallel

### Cross-Validation Process

| Agent | Task | Key Method |
|-------|------|------------|
| backend-analyst | Backend architecture, API, domain, integrations, MAF builders | Glob + Grep + Read |
| frontend-analyst | Frontend components, pages, hooks, stores, routes | Glob + Read + package.json |
| quality-auditor | Code quality: Mocks, InMemory, pass, ellipsis, console.log, long files | Grep patterns + Read |
| infra-security | Infrastructure, security, Docker, CORS, auth, rate limiting | Read + Grep |
| test-analyst | Test coverage, gaps, quality, fixtures | Glob + Grep + Read |

### What V6 Fixed

1. **agent_executor.py MAF**: V5 wrongly said it lacks MAF imports (it does have them)
2. **Mock class count**: 16 -> 18 (nested MockContent/MockResponse in generator.py)
3. **Endpoint count**: 540 -> 530 (removed sub-router duplicate counting)
4. **Empty function bodies**: V5 only counted `pass` (204), missed `...` (119) = total 323
5. **Auth/rate limiting gaps**: V5 never measured these security metrics
6. **Test file distinction**: V5 said 305 tests without noting 58 are support files (not actual tests)

---

**Document End**
**Generated**: 2026-02-11 by Agent Team (5 teammates via TeamCreate) + lead synthesis
**Verification method**: Glob, Grep, file reading, cross-agent validation
**Next review**: After Phase 30 implementation
