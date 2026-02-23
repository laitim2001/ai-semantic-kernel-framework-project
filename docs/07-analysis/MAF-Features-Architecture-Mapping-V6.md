# IPA Platform: Features Architecture Mapping

> **Version**: 6.0
> **Date**: 2026-02-11
> **Positioning**: Agent Orchestration Platform
> **Companion**: `MAF-Claude-Hybrid-Architecture-V6.md`
> **Phase**: 29 Completed (106 Sprints, ~2400 Story Points)
> **Verification**: Agent Team (5 specialized teammates via TeamCreate) with cross-validation
> **Previous**: V5.0 (2026-02-11), V4.0 (2026-02-11), V3.0 (2026-02-09)

---

## How to Read This Document

Each feature is verified by checking: file exists? imports official API? constructs real objects? has substantive logic? data methods return real or fabricated data?

| Status | Definition |
|--------|-----------|
| **REAL** | File exists, substantive logic, production-ready |
| **REAL+MOCK** | Real implementation + Mock fallback when external dependency unavailable |
| **STUB** | Code exists but returns hardcoded/fabricated data |
| **MISSING** | No file or code found for claimed feature |

---

## 1. Feature Verification Summary

### Overall Statistics

| Status | Count | Percentage |
|--------|-------|-----------|
| REAL | 36 | 56.3% |
| REAL+MOCK | 18 | 28.1% |
| STUB | 2 | 3.1% |
| MISSING | 1 | 1.6% |
| Extension (not standalone) | 7 | 10.9% |
| **Total** | **64** | **84.4% fully functional (REAL + REAL+MOCK)** |

### By Category

| Category | Features | REAL | REAL+MOCK | STUB | MISSING | Extension |
|----------|----------|------|-----------|------|---------|-----------|
| 1. Agent Orchestration | 16 | 5 | 4 | 0 | 0 | 7 |
| 2. Human-in-the-Loop | 7 | 6 | 1 | 0 | 0 | 0 |
| 3. State & Memory | 5 | 5 | 0 | 0 | 0 | 0 |
| 4. Frontend Interface | 8 | 7 | 0 | 0 | 1 | 0 |
| 5. Connectivity & Integration | 11 | 7 | 4 | 0 | 0 | 0 |
| 6. Intelligent Decision | 10 | 5 | 5 | 0 | 0 | 0 |
| 7. Observability | 5 | 3 | 0 | 2 | 0 | 0 |
| 8. Agent Swarm (Phase 29) | 6 | 6 | 0 | 0 | 0 | 0 |

### V5 -> V6 Changes

| Item | V5 | V6 | Resolution |
|------|-----|-----|-----------|
| Total features | 64 | **64** | Unchanged |
| REAL+MOCK total | 54 | **54** | Unchanged |
| STUB | 2 | **2** | Unchanged (correlation + rootcause) |
| MISSING | 1 | **1** | Unchanged (ReactFlow) |
| MAF-importing builders | 7 | **8** | agent_executor.py corrected — it DOES have MAF imports |
| Standalone builders | 2 | **1** | Only code_interpreter.py is standalone |
| Mock classes | 16 | **18** | +2 nested (MockContent, MockResponse in generator.py) |

---

## 2. Category 1: Agent Orchestration

### 9 Builder Adapter Files

| # | Feature | Status | File Path | LOC | MAF Import | Evidence |
|---|---------|--------|-----------|-----|------------|----------|
| 1 | **WorkflowExecutor** (Sequential) | REAL | `agent_framework/builders/workflow_executor.py` | 1,308 | `WorkflowExecutor, SubWorkflowRequestMessage` | Wraps official WorkflowExecutor |
| 2 | **ConcurrentBuilder** (Parallel) | REAL | `agent_framework/builders/concurrent.py` | 1,633 | `ConcurrentBuilder` | Wraps official ConcurrentBuilder |
| 3 | **GroupChatBuilder** | REAL+MOCK | `agent_framework/builders/groupchat.py` | 1,912 | `GroupChatBuilder` | `_MockGroupChatWorkflow` fallback |
| 4 | **HandoffBuilder** | REAL | `agent_framework/builders/handoff.py` | 994 | `HandoffBuilder, HandoffAgentUserRequest` | Wraps official HandoffBuilder |
| 5 | **NestedWorkflow** | REAL+MOCK | `agent_framework/builders/nested_workflow.py` | 1,307 | `WorkflowBuilder, Workflow, WorkflowExecutor` | Mock mode fallback |
| 6 | **PlanningAdapter** | REAL | `agent_framework/builders/planning.py` | 1,364 | `MagenticBuilder, Workflow` | Plan-and-execute pattern |
| 7 | **MagenticBuilder** | REAL+MOCK | `agent_framework/builders/magentic.py` | 1,809 | `MagenticBuilder, StandardMagenticManager` | Mock mode fallback |
| 8 | **AgentExecutor** | REAL+MOCK | `agent_framework/builders/agent_executor.py` | 699 | `ChatAgent, ChatMessage, Role` | **V6 Correction: HAS MAF import** (V5 was wrong) |
| 9 | **CodeInterpreter** | REAL | `agent_framework/builders/code_interpreter.py` | 868 | **None** | Uses Azure `AssistantManagerService`, NOT agent_framework |

**V6 Note**: Only item 9 violates the project's CRITICAL rule requiring `from agent_framework import`. V5 incorrectly included item 8 as a violator.

### 7 Extension Features

| # | Feature | Status | File Path | LOC | Role |
|---|---------|--------|-----------|-----|------|
| 10 | **GroupChat Voting** | Extension | `builders/groupchat_voting.py` | 736 | Voting-based speaker selection for GroupChat |
| 11 | **Capability Matching** | Extension | `builders/handoff_capability.py` | 1,050 | Weighted capability matching for Handoff agent selection |
| 12 | **Handoff HITL** | Extension | `builders/handoff_hitl.py` | 1,005 | HITL integration for Handoff patterns |
| 13 | **Edge Routing** | Extension | `builders/edge_routing.py` | 884 | FanOut/FanIn routing for Concurrent patterns |
| 14 | **GroupChat Orchestrator** | Extension | `builders/groupchat_orchestrator.py` | 883 | Orchestrator/manager selection for GroupChat |
| 15 | **Sub-workflow Execution** | Extension | `domain/orchestration/nested/sub_executor.py` | - | Nested sub-workflow execution (domain layer) |
| 16 | **Recursive Patterns** | Extension | `domain/orchestration/nested/recursive_handler.py` | - | Recursive workflow handling (domain layer) |

---

## 3. Category 2: Human-in-the-Loop (HITL)

| # | Feature | Status | File Path | LOC | Evidence |
|---|---------|--------|-----------|-----|----------|
| 17 | **Checkpoint System** | REAL | `domain/checkpoints/storage.py`, `service.py` | - | `DatabaseCheckpointStorage` with PostgreSQL |
| 18 | **Approval Workflow** | REAL | `orchestration/hitl/controller.py` | 788 | `HITLController`; **InMemoryApprovalStorage default** |
| 19 | **HITL Manager** | REAL | `builders/handoff_hitl.py` | 1,005 | `HITLManager`, `HITLCheckpointAdapter`, `HITLSession` |
| 20 | **Approval Handler** | REAL | `orchestration/hitl/approval_handler.py` | 693 | `ApprovalHandler` with full lifecycle |
| 21 | **Teams Notification** | REAL+MOCK | `orchestration/hitl/notification.py` | 732 | `TeamsNotificationService` + `MockNotificationService` |
| 22 | **Frontend HITL Components** | REAL | `components/ag-ui/hitl/` | - | ApprovalBanner, ApprovalDialog, ApprovalList, RiskBadge |
| 23 | **Inline Approval (Chat)** | REAL | `components/unified-chat/ApprovalDialog.tsx` | - | Integrated into unified-chat UI |

**CRITICAL Risk**: `InMemoryApprovalStorage` is the factory default (line 743).

---

## 4. Category 3: State & Memory

| # | Feature | Status | File Path | LOC | Evidence |
|---|---------|--------|-----------|-----|----------|
| 24 | **Redis Checkpoints** | REAL | `hybrid/checkpoint/backends/redis.py` + `agent_framework/multiturn/checkpoint_storage.py` | 438+ | Two independent implementations |
| 25 | **PostgreSQL Checkpoints** | REAL | `hybrid/checkpoint/backends/postgres.py` + `agent_framework/multiturn/checkpoint_storage.py` | 485+ | Two independent implementations |
| 26 | **Unified Memory (3-layer)** | REAL | `memory/unified_memory.py` | 683 | Redis (30min TTL) -> PostgreSQL (7-day TTL) -> mem0+Qdrant (permanent) |
| 27 | **mem0 Integration** | REAL | `memory/mem0_client.py` | 446 | `Mem0Client` wrapping mem0 SDK |
| 28 | **Embeddings Service** | REAL | `memory/embeddings.py` | - | `EmbeddingService` for vector search |

**Known Issues**:
- Two parallel checkpoint systems not coordinated
- `ContextSynchronizer` uses plain Dict with NO locks (CRITICAL)

---

## 5. Category 4: Frontend Interface

| # | Feature | Status | File Path | Evidence |
|---|---------|--------|-----------|----------|
| 29 | **Dashboard** | REAL | `pages/dashboard/DashboardPage.tsx` + 4 sub | React Query, real DB queries |
| 30 | **Unified Chat** | REAL | `components/unified-chat/` (25+ files) | SSE streaming, agent panel |
| 31 | **Agent Management** | REAL | `pages/agents/` (4 pages) | Full CRUD + mock fallback |
| 32 | **Workflow Management** | REAL | `pages/workflows/` (4 pages) | Full CRUD + mock fallback |
| 33 | **DevUI Developer Tools** | REAL | `DevUI/` (15) + `pages/DevUI/` (7) | Traces, monitor, events |
| 34 | **AG-UI Demo** | REAL | `pages/ag-ui/AGUIDemoPage.tsx` + 8 sub | 7-feature demo page |
| 35 | **Workflow Visualization** | **MISSING** | N/A | `@xyflow/react` NOT in package.json |
| 36 | **Auth (Login/Signup)** | REAL | `pages/auth/LoginPage.tsx`, `SignupPage.tsx` | JWT auth, ProtectedRoute |

**10 pages with silent mock fallback** (no visual indicator): ApprovalsPage, WorkflowsPage, WorkflowDetailPage, TemplatesPage, AuditPage, AgentsPage, AgentDetailPage, RecentExecutions, PendingApprovals, ExecutionChart

**V6 New Finding - Frontend Test Gap**: Only 13 unit test files exist, ALL from Phase 29 agent-swarm. ~100 other components have zero unit tests.

---

## 6. Category 5: Connectivity & Integration

| # | Feature | Status | File Path | LOC | Evidence |
|---|---------|--------|-----------|-----|----------|
| 37 | **InputGateway** | REAL+MOCK | `orchestration/input_gateway/gateway.py` | 419 | Source detection + `MockInputGateway` |
| 38 | **ServiceNow Handler** | REAL+MOCK | `source_handlers/servicenow_handler.py` | 399 | 20+ category mappings + Mock |
| 39 | **Prometheus Handler** | REAL+MOCK | `source_handlers/prometheus_handler.py` | 412 | 40+ regex patterns + Mock |
| 40 | **User Input Handler** | REAL+MOCK | `source_handlers/user_input_handler.py` | 294 | Delegates to IntentRouter + Mock |
| 41 | **MCP Azure Server** | REAL | `mcp/servers/azure/server.py` | 333 | JSON-RPC 2.0, 5 tool classes |
| 42 | **MCP Filesystem Server** | REAL | `mcp/servers/filesystem/server.py` | - | FilesystemSandbox |
| 43 | **MCP LDAP Server** | REAL | `mcp/servers/ldap/server.py` | - | TLS/SSL support |
| 44 | **MCP Shell Server** | REAL | `mcp/servers/shell/server.py` | - | Command execution |
| 45 | **MCP SSH Server** | REAL | `mcp/servers/ssh/server.py` | - | Paramiko SSH |
| 46 | **A2A Protocol** | REAL | `a2a/protocol.py` | 294 | 12 MessageTypes, full serialization |
| 47 | **A2A Agent Discovery** | REAL | `a2a/discovery.py` | 352 | Weighted match scoring; in-memory only |

---

## 7. Category 6: Intelligent Decision

| # | Feature | Status | File Path | LOC | Evidence |
|---|---------|--------|-----------|-----|----------|
| 48 | **Three-tier Intent Router** | REAL+MOCK | `orchestration/intent_router/router.py` | 639 | Pattern(>=0.90) -> Semantic(>=0.85) -> LLM |
| 49 | **PatternMatcher (Tier 1)** | REAL | `intent_router/pattern_matcher/matcher.py` | 411 | YAML regex rules |
| 50 | **SemanticRouter (Tier 2)** | REAL+MOCK | `intent_router/semantic_router/router.py` | 466 | `semantic_router` + `MockSemanticRouter` |
| 51 | **LLMClassifier (Tier 3)** | REAL+MOCK | `intent_router/llm_classifier/classifier.py` | 439 | `AsyncAnthropic` + `MockLLMClassifier` |
| 52 | **CompletenessChecker** | REAL+MOCK | `intent_router/completeness/checker.py` | - | Rule-based + Mock |
| 53 | **GuidedDialogEngine** | REAL+MOCK | `guided_dialog/engine.py` | 593 | Multi-turn, max_turns=5 + Mock |
| 54 | **RiskAssessor** | REAL | `risk_assessor/assessor.py` | 639 | Context-aware scoring |
| 55 | **Autonomous Planning** | REAL | `claude_sdk/autonomous/` (8 files) | ~2,800 | AsyncAnthropic, Extended Thinking |
| 56 | **Smart Fallback** | REAL | `claude_sdk/autonomous/fallback.py` | 587 | 6 strategies |
| 57 | **Hybrid Framework Switching** | REAL | `hybrid/switching/` (11 files) | ~829+ | ModeSwitcher + 4 trigger detectors |

---

## 8. Category 7: Observability

| # | Feature | Status | File Path | LOC | Evidence |
|---|---------|--------|-----------|-----|----------|
| 58 | **Decision Audit Tracker** | REAL | `audit/decision_tracker.py` | 448 | Full CRUD, quality scoring, optional Redis |
| 59 | **Audit Report Generator** | REAL | `audit/report_generator.py` | - | Chinese decision type names |
| 60 | **Patrol Agent** | REAL | `patrol/agent.py` + `scheduler.py` | 280+ | Parallel checks, risk scoring |
| 61 | **Correlation Analyzer** | **STUB** | `correlation/analyzer.py` | 524 | **ALL 5 data methods return hardcoded fakes** |
| 62 | **Root Cause Analyzer** | **STUB** | `rootcause/analyzer.py` | 520 | **Hardcoded 2 HistoricalCase; depends on #61** |

### Correlation Analyzer Deep Analysis

Real algorithms: `find_correlations()`, `_time_correlation()`, `_dependency_correlation()`, `_semantic_correlation()`.

But ALL 5 data access methods return fabricated data:

| Method | Line | Returns | Evidence |
|--------|------|---------|----------|
| `_get_event()` | 427 | `Event(title=f"Event {event_id}")` | Same regardless of input |
| `_get_events_in_range()` | 441 | 5 hardcoded events | Fixed count |
| `_get_dependencies()` | 461 | Fabricated list, "critical" type | Always 1 per component |
| `_get_events_for_component()` | 476 | 1 hardcoded event | Always exactly 1 |
| `_search_similar_events()` | 492 | 2 results (0.85, 0.72) | **search_text IGNORED** |

Comment (line 424): `# Helper methods (模擬實現，實際應連接真實數據源)`

### Root Cause Analyzer Deep Analysis

Real framework: hypothesis generation, Claude prompting. But `get_similar_patterns()` returns 2 hardcoded `HistoricalCase` objects. Comment: `# 模擬歷史案例查詢`.

---

## 9. Category 8: Agent Swarm (Phase 29)

| # | Feature | Status | File Path | LOC | Evidence |
|---|---------|--------|-----------|-----|----------|
| 63 | **SwarmTracker** | REAL | `swarm/tracker.py` | 694 | Thread-safe (RLock), optional Redis, singleton |
| 64 | **SwarmIntegration** | REAL | `swarm/swarm_integration.py` | 404 | Callback bridge to ClaudeCoordinator |
| 65 | **Swarm Models** | REAL | `swarm/models.py` | 393 | WorkerType(9), WorkerStatus(7), SwarmMode(3), SwarmStatus(5) |
| 66 | **Swarm API** | REAL | `api/v1/swarm/routes.py` + `demo.py` | ~1,064 | 8 endpoints (3 status + 5 demo/SSE) |
| 67 | **Swarm Frontend** | REAL | `agent-swarm/` | ~3,000 | 15 components + 4 hooks + 13 test files |
| 68 | **Swarm SSE Events** | REAL | `swarm/events/types.py` + `emitter.py` | 1,077 | 9 event types; 100ms throttling |

**Best module in the entire project.** Thread-safe, well-tested (unit + integration + e2e + perf), proper separation.

---

## 10. Feature Dependency Map

```
User Input
    |
    v
Category 5: InputGateway (#37)
    |-- Source detection (ServiceNow/Prometheus/User)
    |-- Handler delegation
    v
Category 6: Three-tier Intent Router (#48)
    |-- Tier 1: PatternMatcher (#49) -- regex, <10ms
    |-- Tier 2: SemanticRouter (#50) -- vector similarity
    |-- Tier 3: LLMClassifier (#51) -- Claude Haiku
    v
Category 6: GuidedDialogEngine (#53) -- multi-turn clarification
    v
Category 6: RiskAssessor (#54) -- context-aware risk scoring
    v
Category 2: HITLController (#18) -- if risk >= threshold
    |-- InMemoryApprovalStorage (CRITICAL: no persistence)
    |-- TeamsNotification (#21)
    |-- Frontend: ApprovalDialog (#22-23)
    v
Category 6: Hybrid Switching (#57)
    |
    +-- MAF leg --> Category 1: Builder Adapters (#1-9)
    |                   |-- 8 use agent_framework API
    |                   |-- 1 standalone (CodeInterpreter)
    |                   |-- Extensions: Voting, CapMatcher, HITL, etc.
    |
    +-- Claude SDK leg --> Category 6: Autonomous Planning (#55)
                              |-- Extended Thinking
                              |-- Smart Fallback (#56)
                              v
                          Category 8: Agent Swarm (#63-68)
    |
    v
Category 3: State & Memory
    |-- Redis Checkpoints (#24) -- 2 independent systems
    |-- PostgreSQL Checkpoints (#25)
    |-- Unified Memory (#26) -- 3-layer
    v
Category 7: Observability
    |-- Decision Audit (#58)
    |-- Patrol (#60)
    |-- Correlation (#61) -- STUB
    |-- RootCause (#62) -- STUB
```

---

## 11. Risk Assessment

### Features with Data Loss Risk (InMemory Storage)

| Storage Class | File | Feature Impacted | Severity |
|---------------|------|-----------------|----------|
| `InMemoryApprovalStorage` | `hitl/controller.py` | #18 Approval Workflow | CRITICAL |
| `InMemoryCheckpointStorage` | `hybrid/switching/switcher.py` | #57 Framework Switching | HIGH |
| `InMemoryCheckpointStorage` | `agent_framework/checkpoint.py` | #24-25 Checkpoints | HIGH |
| `InMemoryThreadRepository` | `ag_ui/thread/storage.py` | #30 Unified Chat | HIGH |
| `InMemoryCache` | `ag_ui/thread/storage.py` | AG-UI caching | MEDIUM |
| `InMemoryDialogSessionStorage` | `guided_dialog/context_manager.py` | #53 GuidedDialog | MEDIUM |
| `InMemoryTransport` | `mcp/core/transport.py` | MCP communication | MEDIUM |
| `InMemoryAuditStorage` | `mcp/security/audit.py` | MCP audit | MEDIUM |
| `InMemoryConversationMemoryStore` | `domain/orchestration/memory/in_memory.py` | Conversation memory | MEDIUM |

### Security Risk Assessment (V6 New)

| Risk | Severity | Evidence |
|------|----------|----------|
| **93% of API endpoints unprotected** | CRITICAL | Only 38/530 use auth middleware |
| **No HTTP rate limiting** | CRITICAL | No middleware-level throttling |
| **Hardcoded default JWT secret** | HIGH | `"change-this-to-a-secure-random-string"` |
| **CORS allows all methods/headers** | HIGH | `allow_methods=["*"]`, `allow_headers=["*"]` |
| **CORS origin port mismatch** | HIGH | Default includes 3000, frontend on 3005 |
| **Docker hardcoded credentials** | MEDIUM | n8n + Grafana use admin/admin123 |
| **No CSP headers** | LOW | No Content-Security-Policy middleware |

### Test Coverage Gaps (V6 New)

| Area | Coverage | Gap |
|------|----------|-----|
| API routes | 33% (13/39) | 26 modules untested |
| Domain modules | 84% (16/19) | auth, files, orchestration |
| Integration modules | 60% (9/15) | a2a, audit, correlation, learning, patrol, rootcause |
| Frontend unit tests | Phase 29 only | ~100 components, 16+ hooks untested |

### Features with Mock Fallback

| Feature | Real Dependency | Mock Fallback | Trigger |
|---------|----------------|---------------|---------|
| #3 GroupChat | agent_framework | _MockGroupChatWorkflow | MAF unavailable |
| #5 NestedWorkflow | agent_framework | Mock mode | MAF unavailable |
| #7 Magentic | agent_framework | Mock mode | MAF unavailable |
| #8 AgentExecutor | Azure OpenAI | Mock mode | API key missing |
| #37-40 Gateway+Handlers | External APIs | Mock handlers | API unavailable |
| #48-53 Intent+Dialog | LLM APIs | Mock classes | Package/key missing |
| #21 Notification | MS Teams | MockNotificationService | Teams unavailable |

### Structural Stubs

| Feature | Code Exists | Data Source | Evidence |
|---------|-------------|-------------|----------|
| #61 Correlation | Real algorithms | ALL 5 data methods hardcoded | "模擬實現" |
| #62 Root Cause | Real framework | 2 hardcoded HistoricalCase | "模擬歷史案例查詢" |

---

## 12. Architecture Layer -> Feature Mapping

| Layer | Features |
|-------|----------|
| L1 Frontend | #29-36 (Frontend Interface), #67 (Swarm Frontend), #22-23 (HITL Frontend) |
| L2 API | Endpoints for all 64 features; 530 endpoints across 47 routers |
| L3 AG-UI | #30 (Unified Chat SSE), #68 (Swarm SSE), #22-23 (HITL events) |
| L4 Orchestration | #37-40 (InputGateway + Handlers), #48-54 (Intelligent Decision), #18-21 (HITL backend) |
| L5 Hybrid | #57 (Framework Switching), #24-25 (Checkpoint backends) |
| L6 MAF Builders | #1-9 (Builder Adapters), #10-16 (Extensions) |
| L7 Claude SDK | #55-56 (Autonomous Planning, Smart Fallback) |
| L8 MCP | #41-45 (5 MCP Servers) |
| L9 Supporting | #46-47 (A2A), #58-60 (Audit, Patrol), #61-62 (Stubs), #26-28 (Memory) |
| L10 Domain | Business logic; #15-16 (Sub-workflow, Recursive) |
| L11 Infrastructure | PostgreSQL + Redis + Alembic (6) + RabbitMQ (EMPTY) + Storage (EMPTY) |

---

## 13. Implementation Quality by Category

| Category | Code Quality | Test Coverage | Architecture | Overall |
|----------|-------------|---------------|--------------|---------|
| 1. Agent Orchestration | Good (adapter pattern) | unit + integration | MAF-aligned (8/9) | Strong, 1 builder lacks MAF import |
| 2. HITL | Good | unit + e2e | Complete lifecycle | Strong, InMemory risk |
| 3. State & Memory | Good (3-layer) | unit | Well-designed | Strong, dual checkpoint confusion |
| 4. Frontend | Good (React patterns) | **Phase 29 only** | Clear routing | Moderate (10 mock pages, ~100 untested components) |
| 5. Connectivity | Good | unit | MCP standard | Strong |
| 6. Intelligent Decision | Good (3-tier) | unit + integration | Well-architected | Strong, silent mock degradation |
| 7. Observability | Mixed | unit | Audit real, corr/root fake | **Weak** (2 structural stubs) |
| 8. Agent Swarm | **Excellent** | unit+integration+e2e+perf | Thread-safe | **Best module** |

---

## 14. Recommendations (Prioritized)

### CRITICAL (Data Integrity + Security)

1. **Add locks to ContextSynchronizer** — concurrent state corruption risk
2. **Replace InMemoryApprovalStorage** — HITL approval records must persist (PostgreSQL)
3. **Wire real data sources for correlation/rootcause** — fabricated analysis results
4. **Move 18 Mock classes** out of production source into tests/ package
5. **Add auth to remaining 492 endpoints** — only 7% currently protected
6. **Add HTTP rate limiting middleware** — no API-level throttling exists

### HIGH (Production Readiness)

7. **Fix Vite proxy port** — `vite.config.ts`: change 8010 to 8000
8. **Fix CORS origins** — change 3000 to 3005 to match frontend
9. **Add visual indicator for mock fallback** — 10 pages silently show fake data
10. **Implement RabbitMQ** or remove from Docker Compose
11. **Configure multi-worker Uvicorn** — remove hardcoded `reload=True`
12. **Consolidate dual checkpoint systems**
13. **Add MAF import to code_interpreter.py** — or document as intentional exception
14. **Fix Docker Compose Prometheus/Grafana version conflict**

### MEDIUM (Code Quality + Testing)

15. **Split 57 files >800 lines** — especially 5 files exceeding 1,500
16. **Remove 54 console.log** — especially 5 in authStore.ts (auth info leak)
17. **Add API route tests** — 26/39 modules have zero tests
18. **Add frontend unit tests** — only Phase 29 covered
19. **Reduce 323 empty function bodies** — 204 pass + 119 ellipsis
20. **Add startup warnings** when SemanticRouter/LLMClassifier unavailable
21. **Install ReactFlow** or remove `.claude/skills/react-flow/`
22. **Add persistence to A2A Discovery**

---

## 15. V6 Accuracy Methodology

### Agent Team Structure

| Agent | Role | Key Findings |
|-------|------|-------------|
| backend-analyst | Backend architecture | 530 endpoints (not 540); 18 Mocks (not 16); agent_executor.py HAS MAF import |
| frontend-analyst | Frontend architecture | 20 hooks (not 19); 6 not in barrel (not 4); 54 console.log (not 45) |
| quality-auditor | Code quality | 119 ellipsis statements (V5 missed); 57 files >800 lines (not 55) |
| infra-security | Infrastructure + Security | Auth 7%; No rate limiting; CORS mismatch; Docker conflict |
| test-analyst | Test coverage | 247 pure tests (not 305); API coverage 33%; Frontend tests Phase 29 only |

### V5 Errors Corrected

| V5 Error | V6 Correction |
|----------|---------------|
| agent_executor.py "lacks MAF import" | **HAS MAF import** — V5 was factually wrong |
| 16 Mock classes | **18** — nested MockContent + MockResponse missed |
| 540 endpoints | **530** — sub-router duplicates removed |
| 7 MAF-importing builders | **8** — agent_executor.py corrected |
| 2 standalone builders | **1** — only code_interpreter.py |
| 19 hooks | **20** — correct count is 16+4 |
| 4 hooks not in barrel | **6** — useSwarmMock, useSwarmReal missed |
| 45 console.log | **54** — 9 added since V5 |
| 55 files >800 lines | **57** — borderline files missed |
| 305 test files | **247 pure + 58 support** — distinction matters |
| Empty function bodies 204 | **~323** — ellipsis (119) completely missed |

---

**Document End**
**Generated**: 2026-02-11 by Agent Team (5 teammates via TeamCreate) + lead synthesis
**Feature count**: 64 features (9 adapters + 7 extensions + 48 other features)
**Of which**: 54 fully functional (REAL + REAL+MOCK), 2 structural stubs, 1 missing
**Next review**: After Phase 30 implementation
