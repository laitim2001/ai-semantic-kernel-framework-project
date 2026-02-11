# IPA Platform: Features Architecture Mapping

> **Version**: 4.0
> **Date**: 2026-02-11
> **Positioning**: Agent Orchestration Platform
> **Companion**: `MAF-Claude-Hybrid-Architecture-V4.md`
> **Phase**: 29 Completed (106 Sprints, ~2400 Story Points)
> **Verification**: 5 specialized analysis agents, direct source code inspection
> **Previous**: V3.0 (2026-02-09)

---

## How to Read This Document

Each feature is verified by checking: file exists? imports official API? constructs real objects? has substantive logic?

| Status | Definition |
|--------|-----------|
| **REAL** | File exists, substantive logic, production-ready |
| **REAL+MOCK** | Real implementation + Mock fallback when external dependency unavailable |
| **STUB** | Code exists but returns hardcoded/fake data |
| **MISSING** | No file or code found for claimed feature |

---

## 1. Feature Verification Summary

### Overall Statistics

| Status | Count | Percentage |
|--------|-------|-----------|
| REAL | 39 | 65.0% |
| REAL+MOCK | 14 | 23.3% |
| STUB | 0 | 0% |
| MISSING | 7 | 11.7% |
| **Total** | **60** | **88.3% have working code** |

> **V4 correction**: V3 claimed 65 features. V4 consolidates to **60 features** after removing 6 non-existent builder names and adding 1 newly discovered feature. See Category 1 notes.

### By Category

| Category | Features | REAL | REAL+MOCK | MISSING | Accuracy |
|----------|----------|------|-----------|---------|----------|
| 1. Agent Orchestration | 8 | 2 | 6 | 0 | 100% |
| 2. Human-in-the-Loop | 7 | 6 | 1 | 0 | 100% |
| 3. State & Memory | 5 | 5 | 0 | 0 | 100% |
| 4. Frontend Interface | 8 | 7 | 0 | 1 | 88% |
| 5. Connectivity & Integration | 11 | 8 | 3 | 0 | 100% |
| 6. Intelligent Decision | 10 | 5 | 5 | 0 | 100% |
| 7. Observability | 5 | 3 | 0 | 2 | 60% |
| 8. Agent Swarm (Phase 29) | 6 | 6 | 0 | 0 | 100% |

### V3 -> V4 Changes

| Item | V3 | V4 | Reason |
|------|-----|-----|--------|
| Total features | 65 | **60** | 6 non-existent builders removed; 1 new feature added |
| Category 1 count | 12 | **8** | Only 8 actual builder adapters exist |
| Category 7 count | 6 | **5** | correlation/rootcause reclassified as MISSING (structural stubs) |
| Overall REAL+MOCK | 57 claimed ✅ | **53 verified** | Honest recount |
| MISSING | 4 | **7** | 6 builders + 1 ReactFlow |

---

## 2. Category 1: Agent Orchestration

### V4 Correction

V3 listed 12 agent builders. **Only 8 actual builder adapter files exist.** The project uses the Adapter pattern wrapping official MAF classes, with different names than V3 claimed.

| # | Feature | Status | File Path | Evidence |
|---|---------|--------|-----------|----------|
| 1 | **ConcurrentBuilder** (parallel execution) | REAL+MOCK | `integrations/agent_framework/builders/concurrent.py` | `from agent_framework import ConcurrentBuilder`; 1,633 LOC |
| 2 | **HandoffBuilder** (agent handoff) | REAL+MOCK | `integrations/agent_framework/builders/handoff.py` | `from agent_framework import HandoffBuilder`; 994 LOC |
| 3 | **GroupChatBuilder** (multi-agent chat) | REAL+MOCK | `integrations/agent_framework/builders/groupchat.py` | `from agent_framework import GroupChatBuilder`; 1,912 LOC; `_MockGroupChatWorkflow` fallback |
| 4 | **MagenticBuilder** (manager-worker) | REAL+MOCK | `integrations/agent_framework/builders/magentic.py` | `from agent_framework import MagenticBuilder, StandardMagenticManager`; 1,809 LOC |
| 5 | **AgentExecutor** (single agent) | REAL+MOCK | `integrations/agent_framework/builders/agent_executor.py` | `from agent_framework import ChatAgent, ChatMessage, Role`; mock mode fallback |
| 6 | **CodeInterpreter** (code execution) | REAL | `integrations/agent_framework/builders/code_interpreter.py` | `AssistantManagerService`; Azure OpenAI Code Interpreter |
| 7 | **NestedWorkflow** (workflow composition) | REAL+MOCK | `integrations/agent_framework/builders/nested_workflow.py` | `from agent_framework import WorkflowBuilder`; 1,307 LOC |
| 8 | **PlanningAdapter** (plan-and-execute) | REAL | `integrations/agent_framework/builders/planning.py` | `from agent_framework import MagenticBuilder`; 1,364 LOC |

**Removed from V3 list (do not exist as builder files):**

| V3 Claimed | Reality |
|------------|---------|
| SequentialAgent Builder | Factory function in nested_workflow.py, not standalone |
| SelectorAgent Builder | ConditionalRouter in edge_routing.py |
| UserProxyAgent Builder | HITLManager in handoff_hitl.py |
| TaskCentricAgent Builder | Not implemented |
| MultiModalAgent Builder | Not implemented |
| HybridAgent Builder | hybrid/ module is framework switching, not a builder |

---

## 3. Category 2: Human-in-the-Loop (HITL)

| # | Feature | Status | File Path | Evidence |
|---|---------|--------|-----------|----------|
| 9 | **Checkpoint System** | REAL | `domain/checkpoints/storage.py`, `service.py` | `DatabaseCheckpointStorage` with PostgreSQL |
| 10 | **Approval Workflow** | REAL | `integrations/orchestration/hitl/controller.py` | `HITLController` (788 LOC); uses `InMemoryApprovalStorage` |
| 11 | **HITL Manager** | REAL | `integrations/agent_framework/builders/handoff_hitl.py` | `HITLManager`, `HITLCheckpointAdapter`, `HITLSession` |
| 12 | **Approval Handler** | REAL | `integrations/orchestration/hitl/approval_handler.py` | `ApprovalHandler` (693 LOC) |
| 13 | **Teams Notification** | REAL+MOCK | `integrations/orchestration/hitl/notification.py` | `TeamsNotificationService` (732 LOC) + `MockNotificationService` |
| 14 | **Frontend HITL Components** | REAL | `frontend/src/components/ag-ui/hitl/` | ApprovalBanner, ApprovalDialog, ApprovalList, RiskBadge |
| 15 | **Inline Approval (Chat)** | REAL | `frontend/src/components/unified-chat/ApprovalDialog.tsx`, `ApprovalMessageCard.tsx` | Integrated into unified-chat UI |

**Risk**: HITL controller uses `InMemoryApprovalStorage` by default — approval records lost on restart.

---

## 4. Category 3: State & Memory

| # | Feature | Status | File Path | Evidence |
|---|---------|--------|-----------|----------|
| 16 | **Redis Checkpoints** | REAL | `integrations/agent_framework/multiturn/checkpoint_storage.py` | `RedisCheckpointStorage` class |
| 17 | **PostgreSQL Checkpoints** | REAL | Same file | `PostgresCheckpointStorage` class |
| 18 | **Conversation Memory** | REAL | `integrations/memory/unified_memory.py` | `UnifiedMemoryManager` — 3-layer (Redis + PostgreSQL + mem0) |
| 19 | **mem0 Integration** | REAL | `integrations/memory/mem0_client.py` | `Mem0Client` wrapping mem0 SDK |
| 20 | **Embeddings Service** | REAL | `integrations/memory/embeddings.py` | `EmbeddingService` for vector search |

Three-layer memory architecture is complete: working memory (Redis) -> session memory (PostgreSQL) -> long-term memory (mem0/Qdrant).

---

## 5. Category 4: Frontend Interface

| # | Feature | Status | File Path | Evidence |
|---|---------|--------|-----------|----------|
| 21 | **Dashboard** | REAL | `pages/dashboard/DashboardPage.tsx` + 4 sub-components | React Query, real DB aggregate queries |
| 22 | **Unified Chat** | REAL | `components/unified-chat/` (27+ files) | Main chat interface, SSE streaming, tool calls |
| 23 | **Agent Management** | REAL | `pages/agents/` (4 pages) | Full CRUD with mock fallback |
| 24 | **Workflow Management** | REAL | `pages/workflows/` (4 pages) | Full CRUD with mock fallback |
| 25 | **DevUI Developer Tools** | REAL | `components/DevUI/` (15) + `pages/DevUI/` (6 pages) | Traces, live monitor, event filtering |
| 26 | **AG-UI Demo** | REAL | `pages/ag-ui/AGUIDemoPage.tsx` + 7 sub-components | 7-feature demo page |
| 27 | **Workflow Visualization** | **MISSING** | N/A | `@xyflow/react` NOT in package.json; library never installed |
| 28 | **Auth (Login/Signup)** | REAL | `pages/auth/LoginPage.tsx`, `SignupPage.tsx` | JWT auth, ProtectedRoute wrapper |

**Note**: 10 pages contain `generateMock*()` — show fake data when backend unreachable, no visual indicator.

---

## 6. Category 5: Connectivity & Integration

| # | Feature | Status | File Path | Evidence |
|---|---------|--------|-----------|----------|
| 29 | **InputGateway** | REAL | `integrations/orchestration/input_gateway/gateway.py` | Source detection, routing to handlers |
| 30 | **ServiceNow Handler** | REAL+MOCK | `integrations/orchestration/input_gateway/source_handlers/servicenow_handler.py` | Real handler + MockServiceNowHandler |
| 31 | **Prometheus Handler** | REAL+MOCK | Same path, `prometheus_handler.py` | Real handler + MockPrometheusHandler |
| 32 | **User Input Handler** | REAL+MOCK | Same path, `user_input_handler.py` | Real handler + MockUserInputHandler |
| 33 | **MCP Azure Server** | REAL | `integrations/mcp/servers/azure/` | server.py, client.py, tools/ with real Azure SDK calls |
| 34 | **MCP Filesystem Server** | REAL | `integrations/mcp/servers/filesystem/` | server.py, client.py, tools.py |
| 35 | **MCP LDAP Server** | REAL | `integrations/mcp/servers/ldap/` | server.py, client.py, tools.py |
| 36 | **MCP Shell Server** | REAL | `integrations/mcp/servers/shell/` | server.py, executor.py, tools.py |
| 37 | **MCP SSH Server** | REAL | `integrations/mcp/servers/ssh/` | server.py, client.py, tools.py |
| 38 | **A2A Protocol** | REAL | `integrations/a2a/protocol.py` | MessageType, Priority, Status enums; full protocol |
| 39 | **A2A Agent Discovery** | REAL | `integrations/a2a/discovery.py` | Agent discovery + capability matching (in-memory only) |

---

## 7. Category 6: Intelligent Decision

| # | Feature | Status | File Path | Evidence |
|---|---------|--------|-----------|----------|
| 40 | **Three-tier Intent Router** | REAL+MOCK | `integrations/orchestration/intent_router/router.py` | `BusinessIntentRouter` (639 LOC) + MockBusinessIntentRouter |
| 41 | **PatternMatcher (Tier 1)** | REAL | `integrations/orchestration/intent_router/pattern_matcher/` | Regex rules from YAML, <10ms target |
| 42 | **SemanticRouter (Tier 2)** | REAL+MOCK | `integrations/orchestration/intent_router/semantic_router/router.py` | Vector similarity + MockSemanticRouter (keyword fallback) |
| 43 | **LLMClassifier (Tier 3)** | REAL+MOCK | `integrations/orchestration/intent_router/llm_classifier/classifier.py` | `anthropic.AsyncAnthropic` + MockLLMClassifier |
| 44 | **CompletenessChecker** | REAL+MOCK | `integrations/orchestration/intent_router/completeness/` | CompletenessChecker + MockCompletenessChecker |
| 45 | **GuidedDialogEngine** | REAL+MOCK | `integrations/orchestration/guided_dialog/engine.py` | GuidedDialogEngine (593 LOC) + MockGuidedDialogEngine |
| 46 | **RiskAssessor** | REAL | `integrations/orchestration/risk_assessor/assessor.py` | RiskAssessor (639 LOC) + policies.py |
| 47 | **Autonomous Planning** | REAL | `integrations/claude_sdk/autonomous/` | 7 files: analyzer, planner, executor, verifier, retry, fallback |
| 48 | **Smart Fallback** | REAL | `integrations/claude_sdk/autonomous/fallback.py` | SmartFallback (587 LOC) — retry/switch/degrade/escalate |
| 49 | **Hybrid Framework Switching** | REAL | `integrations/hybrid/switching/` | Routes between MAF and Claude SDK at runtime |

---

## 8. Category 7: Observability

| # | Feature | Status | File Path | Evidence |
|---|---------|--------|-----------|----------|
| 50 | **Decision Audit Tracker** | REAL | `integrations/audit/decision_tracker.py` | DecisionTracker with full DecisionAudit types |
| 51 | **Audit Report Generator** | REAL | `integrations/audit/report_generator.py` | Report generation service |
| 52 | **Patrol Agent** | REAL | `integrations/patrol/agent.py` + `scheduler.py` | PatrolAgent + 5 check types + scheduler |
| 53 | **Correlation Analyzer** | **MISSING** | `integrations/correlation/analyzer.py` | **STRUCTURAL STUB**: ALL 5 data methods return hardcoded fake objects. Analysis algorithms are real but operate on fabricated data. |
| 54 | **Root Cause Analyzer** | **MISSING** | `integrations/rootcause/analyzer.py` | **STRUCTURAL STUB**: Hardcoded 2 HistoricalCase objects; depends on correlation's fake data. Claude prompt engineering is real but data pipeline is simulated. |

> **V4 reclassification**: V3 rated correlation and rootcause as REAL. V4 reclassifies them as MISSING because their data sources are entirely hardcoded — they produce **fabricated analysis results** regardless of input. The code framework exists, but the modules cannot perform their stated function.

---

## 9. Category 8: Agent Swarm (Phase 29)

| # | Feature | Status | File Path | Evidence |
|---|---------|--------|-----------|----------|
| 55 | **SwarmTracker** | REAL | `integrations/swarm/tracker.py` | Thread-safe (RLock), optional Redis, 694 LOC |
| 56 | **SwarmIntegration** | REAL | `integrations/swarm/swarm_integration.py` | Callback bridge to ClaudeCoordinator |
| 57 | **Swarm Models** | REAL | `integrations/swarm/models.py` | AgentSwarmStatus, WorkerExecution, ThinkingContent, ToolCallInfo |
| 58 | **Swarm API** | REAL | `api/v1/swarm/routes.py`, `demo.py` | 3 status endpoints + 5 demo/SSE endpoints |
| 59 | **Swarm Frontend** | REAL | `components/unified-chat/agent-swarm/` | 15 components + 4 hooks + types + SwarmTestPage |
| 60 | **Swarm SSE Events** | REAL | `integrations/swarm/events/` | SSE event streaming for real-time visualization |

Phase 29 is the cleanest and most complete module. Thread-safe, well-tested, proper separation of concerns.

---

## 10. Feature Dependency Map

```
Category 6: Intelligent Decision
    BusinessIntentRouter
        |-- PatternMatcher (Tier 1, no dependency)
        |-- SemanticRouter (Tier 2, needs embeddings)
        |-- LLMClassifier (Tier 3, needs Anthropic/Azure API)
        v
    GuidedDialogEngine (multi-turn clarification)
        v
    RiskAssessor (risk scoring)
        v
    HITLController (Category 2)

Category 1: Agent Orchestration
    8 Builder Adapters
        |-- All depend on: agent_framework package (MAF)
        |-- GroupChat, Magentic: most complex (1800+ LOC each)
        |-- CodeInterpreter: depends on Azure OpenAI
        v
    HybridOrchestratorV2 (Category 5/6 bridge)
        |-- MAF execution leg (Category 1)
        |-- Claude SDK execution leg (Category 6: #47-49)
        v
    AG-UI Event Bridge (feeds Category 4 + 8)

Category 3: State & Memory
    UnifiedMemoryManager
        |-- Layer 1: Redis (working memory)
        |-- Layer 2: PostgreSQL (session memory)
        |-- Layer 3: mem0 + Qdrant (long-term memory)
        v
    FewShotLearner (Category 6 enhancement)

Category 8: Agent Swarm
    SwarmTracker --> SwarmEventEmitter --> AG-UI SSE
                                            v
                                        SwarmTestPage (Category 4)
```

---

## 11. Risk Assessment

### Features with Data Loss Risk (in-memory storage)

| Feature | Storage | Impact |
|---------|---------|--------|
| #10 Approval Workflow | InMemoryApprovalStorage | HITL decisions lost on restart |
| #16-17 Checkpoints | InMemoryCheckpointStorage (hybrid default) | Agent state lost |
| #38-39 A2A Protocol | Plain dict storage | Agent registry + messages lost |
| #50-51 Audit | In-memory + optional Redis | Audit records lost without Redis |
| L3 AG-UI Threads | InMemoryThreadRepository | Chat history lost |
| L8 MCP Audit | InMemoryAuditStorage | MCP audit logs lost |

### Features with Mock Fallback

These features silently degrade to mock behavior when external dependencies are unavailable:

| Feature | Real Dependency | Mock Fallback |
|---------|----------------|---------------|
| #1-5, 7 Builders | agent_framework package | _MockGroupChatWorkflow, mock mode |
| #40 Intent Router | Anthropic/Azure API | MockBusinessIntentRouter |
| #42 SemanticRouter | Vector embeddings | MockSemanticRouter (keyword) |
| #43 LLMClassifier | Claude Haiku API | MockLLMClassifier |
| #45 GuidedDialog | LLM API | MockGuidedDialogEngine |
| #13 Notifications | Microsoft Teams API | MockNotificationService |
| #30-32 Source Handlers | ServiceNow/Prometheus API | Mock handlers |

### Structural Stubs (look real but produce fake results)

| Feature | Code Exists | Data Source |
|---------|-------------|-------------|
| #53 Correlation | Analysis algorithms real | ALL 5 data methods return hardcoded fakes |
| #54 Root Cause | Claude prompt engineering real | Historical cases hardcoded; depends on correlation fakes |

---

## 12. Architecture Layer -> Feature Mapping

| Layer | Features |
|-------|----------|
| L1 Frontend | #21-28 (Frontend Interface), #59 (Swarm Frontend), #14-15 (HITL Frontend) |
| L2 API | Endpoints for all 60 features |
| L3 AG-UI | #22 (Unified Chat SSE), #60 (Swarm SSE), #14-15 (HITL events) |
| L4 Orchestration | #29 (InputGateway), #40-46 (Intelligent Decision), #10-12 (HITL backend) |
| L5 Hybrid | #49 (Framework Switching), cross-cutting coordination |
| L6 MAF Builders | #1-8 (Agent Orchestration) |
| L7 Claude SDK | #47-48 (Autonomous Planning, Smart Fallback) |
| L8 MCP | #33-37 (5 MCP Servers) |
| L9 Supporting | #38-39 (A2A), #50-52 (Audit, Patrol), #53-54 (Correlation, RootCause), #18-20 (Memory) |
| L10 Domain | Business logic for agents, workflows, sessions, checkpoints, files |
| L11 Infrastructure | PostgreSQL, Redis, RabbitMQ (empty), Storage (empty) |

---

## 13. Implementation Quality by Category

| Category | Code Quality | Test Coverage | Architecture | Overall |
|----------|-------------|---------------|--------------|---------|
| 1. Agent Orchestration | Good (adapter pattern) | unit + integration | MAF-aligned | Strong, but files too large |
| 2. HITL | Good | unit + e2e | Complete lifecycle | Strong, InMemory risk |
| 3. State & Memory | Good (3-layer) | unit | Well-designed | Strong |
| 4. Frontend | Good (React patterns) | Sparse (only swarmStore tested) | Clear routing | Moderate (mock fallbacks) |
| 5. Connectivity | Good | unit | MCP standard | Strong |
| 6. Intelligent Decision | Good (3-tier) | unit + integration | Well-architected | Strong, Mock-heavy |
| 7. Observability | Mixed | unit | Audit real, correlation fake | Weak (2 structural stubs) |
| 8. Agent Swarm | Excellent | unit + integration + e2e + perf | Thread-safe, clean | Best module |

---

## 14. Recommendations (Prioritized)

### Critical

1. **Add thread locks to ContextSynchronizer** — concurrent state corruption risk
2. **Replace InMemoryApprovalStorage** — HITL approval records must persist
3. **Connect real data sources for correlation/rootcause** — currently producing fabricated results
4. **Move 15 Mock classes out of orchestration/ production source** — into tests/ or testing/ sub-package

### High

5. **Implement RabbitMQ messaging** — infrastructure/messaging/ is completely empty
6. **Add Alembic database migrations** — no schema management exists
7. **Fix Vite proxy port** — 8010 should be 8000
8. **Add visual indicator for mock fallback pages** — users cannot distinguish real vs fake data
9. **Install ReactFlow or remove .claude/skills/react-flow/** — planned feature never implemented

### Medium

10. **Split 34 files over 800 lines** — 5 files exceed 1,500 lines
11. **Remove 46 runtime console.log calls** — frontend production code
12. **Add tests for authStore and unifiedChatStore** — critical state untested
13. **Consolidate store/ and stores/ directories** — inconsistent organization
14. **Add persistent storage to A2A module** — all state lost on restart

---

**Document End**
**Generated**: 2026-02-11 by 5 parallel analysis agents + synthesis
**Verification method**: Glob, Grep, file reading across entire codebase
**Feature count**: 60 verified features (V3 claimed 65, V4 corrected to 60)
**Next review**: After Phase 30 implementation
