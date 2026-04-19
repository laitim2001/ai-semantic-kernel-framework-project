# Feature Verification: Categories F-J

> **V9 Analysis** | Base date: 2026-03-29
> **Scope**: Phase 1-44, Categories F (Intelligent Decision), G (Observability), H (Agent Swarm), I (Security), J (Unplanned + Phase 35-44 New Features)
> **Predecessor**: V8 (2026-03-15, Phase 1-34)
> **Method**: Full source code reading of all implementation files + LOC verification

---

## Summary

| Category | Features | V8 Status | V9 Status | Change |
|----------|----------|-----------|-----------|--------|
| F. Intelligent Decision | 7 | 85.7% (6/7) | 85.7% (6/7) | No change — F7 API stub remains |
| G. Observability | 5 | 40% (2/5) | 40% (2/5) | No change — G3/G4/G5 API stubs still disconnected |
| H. Agent Swarm | 4 | 100% (4/4) | 100% (4/4) | Upgraded — Phase 43 added real LLM execution engine |
| I. Security | 4 | 100% (4/4) | 100% (4/4) | Expanded — Phase 36 added PromptGuard + ToolGateway |
| J. Unplanned + New | 15 (V8) | — | 26+ features | 11+ NEW features from Phase 35-44 |

---

### F-J 類功能狀態總覽

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Categories F-J 功能完成度與演進                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  F. Intelligent Decision (7)  ██████░          6/7    86% (F7 API stub)    │
│     F1 LLM ✓ → F2 IntentRouter ✓ → F3 3-Tier ✓ → F4 Dialog ✓            │
│     F5 BizRouter ✓ → F6 LLMClassifier ✓ → F7 Autonomous ◐               │
│                                                                             │
│  G. Observability (5)         ██░░░            2/5    40% (3 stubs)        │
│     G1 Metrics ✓ → G2 HealthCheck ✓                                       │
│     G3 Patrol ◐ → G4 Correlation ◐ → G5 RootCause ◐                      │
│                                                                             │
│  H. Agent Swarm (4)           ████             4/4   100% ↑ UPGRADED      │
│     H1 SwarmEngine ✓ → H2 Visualization ✓ → H3 Events ✓ → H4 Tools ✓   │
│     Phase 43: mock → real LLM execution engine                             │
│                                                                             │
│  I. Security (4)              ████             4/4   100% ↑ EXPANDED      │
│     I1 PromptGuard ✓ → I2 ToolGateway ✓ → I3 Sandbox ✓ → I4 AuditLog ✓ │
│     Phase 36: +PromptGuard +ToolGateway                                    │
│                                                                             │
│  J. Unplanned + New (26+)     ██████████████████████████   Phase 35-44    │
│     三層路由 / OrchestratorMediator / ContextBridge / Bootstrap             │
│     Agent Team PoC / Swarm Real Engine / MediatorEventBridge               │
│     +11 NEW features since V8                                              │
│                                                                             │
│  ✓ = COMPLETE   ◐ = PARTIAL/STUB   ↑ = V8→V9 升級                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 智慧決策功能鏈 (Category F)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Intelligent Decision 功能流程                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  用戶輸入                                                                   │
│     │                                                                       │
│     ↓                                                                       │
│  F1 LLM Service Layer ──→ Azure OpenAI / Claude / Mock                     │
│     │  (llm/ 6 files, 1,907 LOC)                                           │
│     ↓                                                                       │
│  F2 Intent Router (Hybrid) ──→ IT意圖分類 + 框架選擇                       │
│     │  (hybrid/intent/ 10 files, 2,367 LOC)                                │
│     ↓                                                                       │
│  F3 Three-tier Routing ──→ L1 Pattern → L2 Semantic → L3 LLM              │
│     │  (orchestration/intent_router/ 23 files, ~7,115 LOC)                 │
│     │                                                                       │
│     ├──→ 需要澄清? ──→ F4 Guided Dialog Engine                            │
│     │                    (4 files, ~3,407 LOC)                              │
│     │                                                                       │
│     ├──→ 業務意圖? ──→ F5 Business Intent Router                           │
│     │                    (router.py, 622 LOC)                               │
│     │                                                                       │
│     └──→ 複雜推理? ──→ F6 LLM Classifier                                  │
│                          (4 files, 1,269 LOC)                               │
│                             │                                               │
│                             ↓                                               │
│                       F7 Autonomous Planning                                │
│                          SDK: ✓ (8 files, 2,823 LOC)                       │
│                          API: ◐ (STUB, 未接線)                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Swarm 與 Security 功能演進時間線

```
┌─────────────────────────────────────────────────────────────────────────────┐
│               Phase 演進時間線 (Category H + I)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase:  29      36       39       42       43       44                     │
│          │       │        │        │        │        │                      │
│  ────────┼───────┼────────┼────────┼────────┼────────┼──→                  │
│          │       │        │        │        │        │                      │
│  H1 ─────┤       │        │        │    ┌───┤        │  SwarmEngine         │
│  Swarm   │ mock  │        │        │    │real│       │  mock → real LLM    │
│  Engine  │events │        │        │    │exec│       │                      │
│          │       │        │        │        │        │                      │
│  H2 ─────┤       │        │        │    ┌───┤        │  SwarmVisualization  │
│  Viz     │ basic │        │        │    │fix │       │  bug fixes Phase 43 │
│          │       │        │        │        │        │                      │
│  H3 ─────┤       │        │        │        │        │  SwarmEvents         │
│  Events  │ SSE   │        │        │        │        │  (stable since P29) │
│          │       │        │        │        │        │                      │
│  H4 ─────┤       │        │        │    ┌───┤        │  SwarmTools          │
│  Tools   │ none  │        │        │    │tool│       │  per-worker registry │
│          │       │        │        │    │reg │       │                      │
│  ────────┼───────┼────────┼────────┼────────┼────────┼──→                  │
│          │       │        │        │        │        │                      │
│  I1 ─────│───────┤        │        │        │        │  PromptGuard         │
│          │       │ new    │        │        │        │  Phase 36 新增       │
│          │       │        │        │        │        │                      │
│  I2 ─────│───────┤        │        │        │        │  ToolGateway         │
│          │       │ new    │        │        │        │  Phase 36 新增       │
│          │       │        │        │        │        │                      │
│  I3 ─────┤       │        │        │        │        │  Sandbox             │
│          │ exist │        │        │        │        │  (stable since P1)  │
│          │       │        │        │        │        │                      │
│  I4 ─────┤       │        │        │        │        │  AuditLog            │
│          │ exist │        │        │        │        │  (stable since P1)  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Category F: Intelligent Decision (7 features)

### Feature List

| ID | Feature | V8 Status | V9 Status | Evidence | Phase | Layer |
|----|---------|-----------|-----------|----------|-------|-------|
| F1 | LLM Service Layer | COMPLETE | COMPLETE | `integrations/llm/` (6 files, 1,907 LOC) | 1 | L9 |
| F2 | Intent Router (Hybrid) | COMPLETE | COMPLETE | `hybrid/intent/` (10 files, 2,367 LOC) | 13 | L5 |
| F3 | Three-tier Routing | COMPLETE | COMPLETE | `orchestration/intent_router/` (23 files, ~7,115 LOC) | 28 | L4 |
| F4 | Guided Dialog Engine | COMPLETE | COMPLETE | `orchestration/guided_dialog/` (4 files, ~3,407 LOC) | 28 | L4 |
| F5 | Business Intent Router | COMPLETE | COMPLETE | `orchestration/intent_router/router.py` (622 LOC) | 28 | L4 |
| F6 | LLM Classifier | COMPLETE | COMPLETE | `orchestration/intent_router/llm_classifier/` (4 files, 1,269 LOC) | 28 | L4 |
| F7 | Claude Autonomous Planning | SPLIT | SPLIT | API: `api/v1/autonomous/` (STUB) / Integration: `claude_sdk/autonomous/` (8 files, 2,823 LOC, COMPLETE) | 22 | L7/L2 |

### Per-Feature Detail

#### F1: LLM Service Layer
- **Status**: COMPLETE
- **Implementation files**:
  - `integrations/llm/azure_openai.py` (557 LOC) — AzureOpenAILLMService, real `openai.AsyncAzureOpenAI` SDK
  - `integrations/llm/cached.py` (349 LOC) — CachedLLMService with Redis cache
  - `integrations/llm/factory.py` (350 LOC) — Factory pattern, auto-detect environment
  - `integrations/llm/mock.py` (369 LOC) — MockLLMService for testing
  - `integrations/llm/protocol.py` (233 LOC) — LLMServiceProtocol interface
- **Dependencies**: openai SDK, Azure OpenAI credentials, Redis (cache)
- **Data persistence**: Redis (LLM response cache)
- **Known issues**: None
- **Phase history**: Introduced Phase 1 (S34-36), stable

#### F2: Intent Router (Hybrid)
- **Status**: COMPLETE
- **Implementation files**:
  - `hybrid/intent/router.py` (500 LOC) — FrameworkSelector, two-layer routing (IT intent + framework selection)
  - `hybrid/intent/classifiers/rule_based.py` (467 LOC) — RuleBasedClassifier (EN+ZH-TW bilingual)
  - `hybrid/intent/classifiers/routing_decision.py` (184 LOC) — RoutingDecision model
  - `hybrid/intent/analyzers/complexity.py` (427 LOC) — ComplexityAnalyzer (step/dependency scoring)
  - `hybrid/intent/analyzers/multi_agent.py` (566 LOC) — MultiAgentDetector
  - `hybrid/intent/models.py` (223 LOC) — ExecutionMode, IntentAnalysis
- **Dependencies**: BusinessIntentRouter (downstream)
- **Data persistence**: InMemory (session context)
- **Known issues**: None
- **Phase history**: Introduced Phase 13 (S52), renamed Phase 28 (S98)

#### F3: Three-tier Routing (Pattern -> Semantic -> LLM)
- **Status**: COMPLETE
- **Implementation files**:
  - `orchestration/intent_router/pattern_matcher/matcher.py` (410 LOC) — Tier 1 (<10ms, 30+ regex rules, YAML config)
  - `orchestration/intent_router/semantic_router/router.py` (375 LOC) — Tier 2 (<100ms, vector similarity)
  - `orchestration/intent_router/semantic_router/routes.py` (372 LOC) — 15 route definitions
  - `orchestration/intent_router/semantic_router/azure_semantic_router.py` (273 LOC) — Azure AI Search integration
  - `orchestration/intent_router/semantic_router/embedding_service.py` (275 LOC) — Azure OpenAI embeddings
  - `orchestration/intent_router/llm_classifier/classifier.py` (293 LOC) — Tier 3 (<2000ms, real LLM API)
  - `orchestration/intent_router/llm_classifier/prompts.py` (230 LOC) — Prompt templates
  - `orchestration/intent_router/llm_classifier/cache.py` (274 LOC) — Classification cache
  - `orchestration/intent_router/llm_classifier/evaluation.py` (472 LOC) — Evaluation suite
  - `orchestration/intent_router/completeness/checker.py` (376 LOC) — CompletenessChecker
  - `orchestration/intent_router/completeness/rules.py` (658 LOC) — Per-intent field rules
  - `orchestration/intent_router/models.py` (449 LOC) — ITIntentCategory, RoutingDecision, RiskLevel
  - `orchestration/intent_router/contracts.py` (134 LOC) — Protocol definitions
- **Total LOC**: ~7,115 (across 23 files, including Azure Semantic Router + __init__.py files)
- **Dependencies**: LLMServiceProtocol, Azure OpenAI (embeddings), Azure AI Search
- **Data persistence**: InMemory (classification cache)
- **Known issues**: None — uses real embeddings, not mock
- **Phase history**: Introduced Phase 28 (S91-97), enhanced S115, S128

#### F4: Guided Dialog Engine
- **Status**: COMPLETE
- **Implementation files**:
  - `orchestration/guided_dialog/engine.py` (547 LOC) — GuidedDialogEngine, state machine INITIAL->GATHERING->COMPLETE/HANDOFF
  - `orchestration/guided_dialog/context_manager.py` (1,101 LOC) — ConversationContextManager, incremental field extraction
  - `orchestration/guided_dialog/generator.py` (1,044 LOC) — QuestionGenerator, template-based (ZH-TW)
  - `orchestration/guided_dialog/refinement_rules.py` (622 LOC) — Sub-intent refinement
- **Total LOC**: ~3,407 (including __init__.py; 3,314 non-init)
- **Dependencies**: BusinessIntentRouter (initial classification), CompletenessChecker
- **Data persistence**: InMemory (`_dialog_sessions` dict)
- **Known issues**: In-memory session storage (C-01)
- **Phase history**: Introduced Phase 28 (S94, S97)

#### F5: Business Intent Router
- **Status**: COMPLETE
- **Implementation files**:
  - `orchestration/intent_router/router.py` (622 LOC) — BusinessIntentRouter, three-layer coordinator
- **Dependencies**: PatternMatcher, SemanticRouter, LLMClassifier, CompletenessChecker
- **Data persistence**: N/A (coordinator)
- **Known issues**: None
- **Phase history**: Introduced Phase 28 (S96)

#### F6: LLM Classifier
- **Status**: COMPLETE
- **Implementation files**:
  - `orchestration/intent_router/llm_classifier/classifier.py` (293 LOC) — Real LLM call via LLMServiceProtocol
  - `orchestration/intent_router/llm_classifier/prompts.py` (230 LOC) — Prompt templates
  - `orchestration/intent_router/llm_classifier/cache.py` (274 LOC) — InMemory cache
  - `orchestration/intent_router/llm_classifier/evaluation.py` (472 LOC) — Evaluation suite
- **Total LOC**: 1,269
- **Dependencies**: LLMServiceProtocol (Azure OpenAI/Claude/Mock)
- **Data persistence**: InMemory (classification cache)
- **Known issues**: Graceful degradation to mock when real router init fails (F6 fallback pattern)
- **Phase history**: Introduced Phase 28 (S97), enhanced S128

#### F7: Claude Autonomous Planning
- **Status**: SPLIT (API: STUB / Integration: COMPLETE) — **Unchanged from V8**
- **Implementation files**:
  - API: `api/v1/autonomous/routes.py` — 100% mock, generates fake steps `["analyze","plan","prepare","execute","cleanup"]`
  - Integration: `claude_sdk/autonomous/` (8 files, 2,823 LOC):
    - `analyzer.py` (346 LOC) — EventAnalyzer (Extended Thinking)
    - `planner.py` (375 LOC) — AutonomousPlanner (decision tree)
    - `executor.py` (397 LOC) — PlanExecutor (streaming)
    - `verifier.py` (353 LOC) — ResultVerifier (validation + learning)
    - `retry.py` (393 LOC) — RetryPolicy (failure classification)
    - `fallback.py` (587 LOC) — SmartFallback (6 strategies)
    - `types.py` (244 LOC) — Type definitions
- **Dependencies**: API: None. Integration: anthropic SDK
- **Known issues**: API routes NOT connected to integration layer (C-03). API docstring says "Phase 22 Testing"
- **Phase history**: Introduced Phase 22 (S79), integration layer complete, API never wired

---

## Category G: Observability (5 features)

### Feature List

| ID | Feature | V8 Status | V9 Status | Evidence | Phase | Layer |
|----|---------|-----------|-----------|----------|-------|-------|
| G1 | Audit Logging | COMPLETE | COMPLETE | `domain/audit/` (758 LOC) + `api/v1/audit/` | 1 | L9 |
| G2 | DevUI Tracing | COMPLETE | COMPLETE | `domain/devtools/tracer.py` (777 LOC) + `api/v1/devtools/` | 4 | L9 |
| G3 | Patrol Monitoring | SPLIT | SPLIT | API: `api/v1/patrol/` (STUB) / Integration: `integrations/patrol/` (11 files, 2,541 LOC, COMPLETE) | 23 | L11 |
| G4 | Event Correlation | SPLIT | SPLIT | API: `api/v1/correlation/` (STUB) / Integration: `integrations/correlation/` (6 files, 2,181 LOC, COMPLETE) | 23 | L11 |
| G5 | Root Cause Analysis | SPLIT | SPLIT | API: `api/v1/rootcause/` (STUB) / Integration: `integrations/rootcause/` (5 files, 1,920 LOC, COMPLETE) | 23 | L11 |

### Per-Feature Detail

#### G1: Audit Logging
- **Status**: COMPLETE
- **Implementation files**:
  - `domain/audit/logger.py` (728 LOC) — AuditLogger, 20 action types, 9 resource types, 4 severity levels
  - `api/v1/audit/` — 7 audit + 6 decision endpoints, CSV/JSON export
- **Data persistence**: **InMemory only** (list, max_entries limit) — No DB persistence
- **Known issues**: In-memory audit is compliance risk (C-01). Restart loses all audit history
- **Phase history**: Introduced Phase 1 (S3), stable

#### G2: DevUI Tracing
- **Status**: COMPLETE
- **Implementation files**:
  - `domain/devtools/tracer.py` (777 LOC) — ExecutionTracer, trace/span/event system
  - `api/v1/devtools/` — 12 endpoints, timeline visualization, event filtering, statistics
- **Data persistence**: **InMemory** (traces dict, can grow unbounded)
- **Known issues**: In-memory traces can grow unbounded (C-01), no eviction policy
- **Phase history**: Introduced Phase 4 (S66-68)

#### G3: Patrol Monitoring
- **Status**: SPLIT — **Unchanged from V8**
- **Implementation files**:
  - API: `api/v1/patrol/routes.py` — 9 endpoints, ALL STUB (mock/hardcoded responses)
  - Integration: `integrations/patrol/` (11 files, 2,541 LOC):
    - `agent.py` (454 LOC) — PatrolAgent, main scheduling loop
    - `scheduler.py` (362 LOC) — Check scheduling
    - `checks/service_health.py` (189 LOC) — HTTP health checks
    - `checks/resource_usage.py` (233 LOC) — psutil system monitoring
    - `checks/api_response.py` (250 LOC) — API response validation
    - `checks/log_analysis.py` (244 LOC) — Log pattern detection
    - `checks/security_scan.py` (312 LOC) — Security scanning
    - `types.py` (238 LOC) — Type definitions
- **Dependencies**: psutil, httpx (integration layer only)
- **Known issues**: API routes NOT connected to integration layer (C-05). API uses blocking `time.sleep()` in async handlers
- **V9 Delta**: Sprint 130 was mentioned as a fix target in V8, but API stubs remain disconnected. Integration layer works correctly with real system checks (psutil, HTTP)
- **Phase history**: Introduced Phase 23 (S82), integration fixed S130, API never wired

#### G4: Event Correlation
- **Status**: SPLIT — **Unchanged from V8**
- **Implementation files**:
  - API: `api/v1/correlation/routes.py` — 7 endpoints, ALL STUB (100% mock, uuid4() + hardcoded)
  - Integration: `integrations/correlation/` (6 files, 2,181 LOC):
    - `analyzer.py` (539 LOC) — CorrelationAnalyzer
    - `data_source.py` (646 LOC) — EventDataSource (Azure Monitor/App Insights REST API)
    - `event_collector.py` (321 LOC) — EventCollector (deduplication + aggregation)
    - `graph.py` (430 LOC) — Correlation graph analysis
    - `types.py` (184 LOC) — Type definitions
- **Dependencies**: Azure Monitor REST API, App Insights (integration layer)
- **Known issues**: API routes NOT connected to integration layer (C-02). Integration layer has real Azure Monitor integration post-Sprint 130
- **V9 Delta**: Sprint 130 fixed integration layer to use real EventDataSource and graceful degradation (empty results instead of fake data). API layer remains fully mocked
- **Phase history**: Introduced Phase 23 (S82), integration fixed S130, API never wired

#### G5: Root Cause Analysis
- **Status**: SPLIT — **Unchanged from V8**
- **Implementation files**:
  - API: `api/v1/rootcause/routes.py` — 4 endpoints, ALL STUB (hardcoded responses)
  - Integration: `integrations/rootcause/` (5 files, 1,920 LOC):
    - `analyzer.py` (516 LOC) — RootCauseAnalyzer
    - `case_matcher.py` (520 LOC) — CaseMatcher (multi-dimensional scoring: text similarity + category + severity + recency)
    - `case_repository.py` (636 LOC) — CaseRepository (15 real IT Ops seed cases)
    - `types.py` (190 LOC) — Type definitions
- **Dependencies**: CorrelationAnalyzer (upstream)
- **Known issues**: API routes NOT connected to integration layer (C-04). Integration layer uses real case matching with seed data
- **V9 Delta**: Sprint 130 fixed integration layer. CaseRepository now has 15 real IT Ops seed cases for matching. API layer still hardcoded
- **Phase history**: Introduced Phase 23 (S82), integration fixed S130, API never wired

### G Category Summary

The observability category remains the weakest at 40% full completion (only G1+G2 are end-to-end functional). G3/G4/G5 all have complete integration layers (total 6,642 LOC of real implementation) but their API routes remain disconnected stubs. **The gap is specifically at the API wiring layer** -- wiring these API routes to the existing integration code would immediately bring the category to 100%.

---

## Category H: Agent Swarm (4 features)

### Feature List

| ID | Feature | V8 Status | V9 Status | Evidence | Phase | Layer |
|----|---------|-----------|-----------|----------|-------|-------|
| H1 | Swarm Manager + Workers | COMPLETE | COMPLETE (Upgraded) | `integrations/swarm/` (10 files, 3,461 LOC) | 29, 43 | L11 |
| H2 | Swarm SSE Events | COMPLETE | COMPLETE | `integrations/swarm/events/` (3 files, 1,132 LOC) | 29 | L3/L11 |
| H3 | Swarm Frontend Panel | COMPLETE | COMPLETE | `components/agent-swarm/` (15+4+2 files) | 29, 43 | L1 |
| H4 | Swarm Tests | COMPLETE | COMPLETE | `components/agent-swarm/__tests__/` | 29 | — |

### Per-Feature Detail

#### H1: Swarm Manager + Workers
- **Status**: COMPLETE — **Significantly upgraded in Phase 43**
- **Implementation files**:
  - `integrations/swarm/tracker.py` (693 LOC) — SwarmTracker, thread-safe state management (optional Redis)
  - `integrations/swarm/swarm_integration.py` (404 LOC) — SwarmIntegrationBridge, ClaudeCoordinator callbacks
  - `integrations/swarm/models.py` (393 LOC) — AgentSwarmStatus, WorkerExecution, SwarmMode, 9+ enums
  - **NEW Phase 43 files**:
    - `integrations/swarm/task_decomposer.py` (221 LOC) — **TaskDecomposer**: LLM-powered task decomposition via `generate_structured()`, produces parallel sub-tasks assigned to specialist roles
    - `integrations/swarm/worker_executor.py` (402 LOC) — **SwarmWorkerExecutor**: Individual worker agent execution with real LLM + function calling loop (max 5 tool iterations), emits SSE events for thinking/tool_call/progress
    - `integrations/swarm/worker_roles.py` (91 LOC) — **5 specialist roles**: network_expert, db_expert, app_expert, security_expert, general — each with ZH-TW system prompts and tool whitelists
  - `api/v1/swarm/` — 8 endpoints (status, workers, demo, SSE stream)
- **Total LOC**: 3,461 (up from ~1,100 in V8)
- **Dependencies**: ClaudeCoordinator (claude_sdk/orchestrator), LLMServiceProtocol
- **Data persistence**: InMemory + optional Redis
- **V9 Delta**: Phase 43 (Sprint 148) added **real multi-agent execution**: TaskDecomposer breaks complex requests into sub-tasks, SwarmWorkerExecutor runs each worker with independent LLM + function calling loops, worker_roles defines 5 IT operations specialist agents. This transforms swarm from a demo/visualization system into a genuine parallel multi-agent execution engine
- **Known issues**: None
- **Phase history**: Introduced Phase 29 (S100-102), **major upgrade Phase 43 (S148)** — real LLM-powered task decomposition and worker execution

#### H2: Swarm SSE Events
- **Status**: COMPLETE
- **Implementation files**:
  - `integrations/swarm/events/emitter.py` (634 LOC) — SwarmEventEmitter, AG-UI CustomEvent emission, event throttling (100ms default), batch sending, priority event handling
  - `integrations/swarm/events/types.py` (443 LOC) — 9 event payload dataclasses (SwarmCreated, SwarmStatusUpdate, SwarmCompleted, WorkerStarted, WorkerProgress, WorkerThinking, WorkerToolCall, WorkerMessage, WorkerCompleted)
- **Total LOC**: 1,132
- **Dependencies**: AG-UI CustomEvent (`src.integrations.ag_ui.events`)
- **Known issues**: None
- **Phase history**: Introduced Phase 29 (S101-103)

#### H3: Swarm Frontend Panel
- **Status**: COMPLETE
- **Implementation files**: `frontend/src/components/unified-chat/agent-swarm/` — 15 components + 4 hooks + 2 type files (~4,700 LOC)
  - AgentSwarmPanel, WorkerCard, WorkerCardList, WorkerDetailDrawer, ExtendedThinkingPanel, ToolCallsPanel, ToolCallItem, OverallProgress, SwarmHeader
  - Hooks: useSwarmEvents, useWorkerDetail, useSwarmStatus, useSwarmEventHandler
- **Dependencies**: Backend swarm SSE API, Zustand store
- **V9 Delta**: Phase 43 fixed worker card accumulation bug, improved detail drawer auth display
- **Known issues**: None
- **Phase history**: Introduced Phase 29 (S104-105), bug fixes Phase 43

#### H4: Swarm Tests
- **Status**: COMPLETE
- **Implementation files**: `frontend/src/components/unified-chat/agent-swarm/__tests__/` (12 test files)
- **Known issues**: None
- **Phase history**: Introduced Phase 29 (S106)

### H Category Summary

Phase 43 represents a qualitative upgrade for the Swarm system. V8 documented a complete visualization/demo system. V9 confirms that Phase 43 added a **real execution engine**: TaskDecomposer (LLM-powered task splitting), SwarmWorkerExecutor (independent LLM + function calling per worker), and 5 specialist worker_roles. The backend grew from ~1,100 LOC to 3,461 LOC. The swarm is now a genuine parallel multi-agent system, not just a visualization layer.

---

## Category I: Security (4 features)

### Feature List

| ID | Feature | V8 Status | V9 Status | Evidence | Phase | Layer |
|----|---------|-----------|-----------|----------|-------|-------|
| I1 | JWT Authentication | COMPLETE | COMPLETE | `core/security/jwt.py` (164 LOC) + `core/security/password.py` (58 LOC) | 22 | L10 |
| I2 | Global Auth Middleware | COMPLETE | COMPLETE | `core/auth.py` (require_auth) | 35 | L10 |
| I3 | Sandbox Isolation | COMPLETE | COMPLETE | `core/sandbox/` (7 files) | 22 | L10 |
| I4 | MCP Permission System | COMPLETE | COMPLETE | `mcp/security/` (6 files, 1,818 LOC) | 9 | L8 |

### Per-Feature Detail

#### I1: JWT Authentication
- **Status**: COMPLETE
- **Implementation files**:
  - `core/security/jwt.py` (164 LOC) — JWT (HS256, 1-hour expiry), create_access_token, decode_token
  - `core/security/password.py` (58 LOC) — bcrypt via passlib, hash_password, verify_password
- **Dependencies**: python-jose, passlib, infrastructure/database
- **Data persistence**: PostgreSQL (User model)
- **Known issues**: JWT secret hardcoded `"change-this-to-a-secure-random-string"` (needs production config)
- **Phase history**: Introduced Phase 22 (S70)

#### I2: Global Auth Middleware
- **Status**: COMPLETE
- **Implementation files**:
  - `core/auth.py` — `require_auth` with auth dependency injection
- **Dependencies**: JWT auth (I1)
- **Known issues**: No RBAC role checks on destructive operations (H-01). Rate limiter is in-memory (H-14)
- **V9 Delta**: `core/security/rbac.py` (153 LOC) exists now, providing basic `Role` enum (ADMIN/OPERATOR/VIEWER) and permission checking — but it is NOT wired into the auth middleware. RBAC remains a separate unused utility
- **Phase history**: Introduced Phase 35 (S111)

#### I3: Sandbox Isolation
- **Status**: COMPLETE
- **Implementation files**:
  - `core/sandbox/config.py` — ProcessSandboxConfig
  - `core/sandbox/ipc.py` — IPC communication
  - `api/v1/sandbox/` — 6 endpoints
- **Dependencies**: subprocess
- **Known issues**: Simulated sandbox, not real container isolation (H-09). Environment variable filtering + sensitive data masking + path traversal prevention
- **Phase history**: Introduced Phase 22 (S77-78)

#### I4: MCP Permission System
- **Status**: COMPLETE
- **Implementation files**:
  - `mcp/security/permissions.py` (458 LOC) — 4-level RBAC (NONE/READ/EXECUTE/ADMIN), glob patterns, priority-based evaluation, deny-first
  - `mcp/security/permission_checker.py` (182 LOC) — MCPPermissionChecker
  - `mcp/security/audit.py` (686 LOC) — MCP audit logging
  - `mcp/security/command_whitelist.py` (224 LOC) — Shell command whitelist
  - `mcp/security/redis_audit.py` (225 LOC) — Redis-backed audit persistence
- **Total LOC**: 1,818
- **Dependencies**: MCPProtocol
- **Data persistence**: InMemory (policy storage), optional Redis (audit)
- **Known issues**: Default mode is "log" (does not block). Dev/test environment auto-grants ADMIN (H-07)
- **Phase history**: Introduced Phase 9 (S39), enhanced S113

### I Category Summary

All 4 security features remain COMPLETE. V9 notes that Phase 36 (Sprint 109) added significant security enhancements that were NOT tracked in V8's feature list: PromptGuard (380 LOC, 3-layer prompt injection defense) and ToolGateway (594 LOC, 4-layer tool call security). These are tracked in Category J as new features. RBAC utility exists at `core/security/rbac.py` but is not wired into middleware.

---

## Category J: Unplanned + Phase 35-44 New Features

### V8 Unplanned Features (15) — Status Update

| # | Feature | V8 Status | V9 Status | Evidence |
|---|---------|-----------|-----------|----------|
| U1 | 3 Extra MCP Servers (n8n, ADF, D365) | COMPLETE | COMPLETE | `mcp/servers/{n8n,adf,d365}/` — 70 tools total (across all 9 servers) |
| U2 | Learning / Few-Shot System | COMPLETE | COMPLETE | `integrations/learning/` — LearningService + SequenceMatcher |
| U3 | Notification System | COMPLETE | COMPLETE | `api/v1/notifications/` — 11 endpoints, Adaptive Cards v1.4 |
| U4 | IT Incident Processing | COMPLETE | COMPLETE | `integrations/incident/` — full correlation + rootcause + LLM pipeline |
| U5 | Shared Protocols Module | COMPLETE | COMPLETE | `integrations/shared/protocols.py` |
| U6 | Performance Monitoring API | PARTIAL | PARTIAL | `api/v1/performance/` — 11 endpoints, Phase2 stats hardcoded |
| U7 | Prompt Management API | COMPLETE | COMPLETE | `api/v1/prompts/` — 11 endpoints |
| U8 | Routing Engine API | COMPLETE | COMPLETE | `api/v1/routing/` — 14 endpoints, ScenarioRouter |
| U9 | Version Control API | COMPLETE | COMPLETE | `api/v1/versioning/` — 14 endpoints |
| U10 | Trigger/Webhook API | COMPLETE | COMPLETE | `api/v1/triggers/` — 9 endpoints |
| U11 | Mediator Pattern Refactor | COMPLETE | COMPLETE (Expanded) | `hybrid/orchestrator/mediator.py` (844 LOC) + 7 handlers (1,160 LOC in handlers/ + AgentHandler) |
| U12 | Extended Thinking (Claude) | COMPLETE | COMPLETE | `claude_sdk/client.py` — beta header streaming |
| U13 | Multi-Agent Coordinator | COMPLETE | COMPLETE | `claude_sdk/orchestrator/coordinator.py` — ClaudeCoordinator + TaskAllocator |
| U14 | Orchestration Metrics (OTel) | COMPLETE | COMPLETE | `orchestration/metrics.py` (893 LOC) — dual-mode OTel + fallback |
| U15 | Structured Logging + OTel | COMPLETE | COMPLETE | `core/observability/` (4 files, 695 LOC) — metrics.py, setup.py, spans.py |

### NEW Phase 35-44 Features (Not in V8)

| # | Feature | Phase | Sprint | Status | Implementation | LOC |
|---|---------|-------|--------|--------|----------------|-----|
| J1 | Pipeline Contract System | 35 | S108 | COMPLETE | `integrations/contracts/pipeline.py` — PipelineRequest/PipelineResponse, PipelineSource enum, cross-module decoupling | 52 |
| J2 | OrchestratorMediator (Full Pipeline) | 35-39 | S132-134 | COMPLETE | `hybrid/orchestrator/mediator.py` (844 LOC) — Central coordinator with 7-handler chain: Context->Routing->Dialog->Approval->Agent->Execution->Observability | 844 |
| J3 | OrchestratorBootstrap (Wiring Factory) | 39 | S134 | COMPLETE | `hybrid/orchestrator/bootstrap.py` (511 LOC) — Assembles fully-wired OrchestratorMediator with all 7 handlers connected to real dependencies. Graceful degradation | 511 |
| J4 | AgentHandler (LLM Decision Engine) | 35, 42 | S107, S144 | COMPLETE | `hybrid/orchestrator/agent_handler.py` (425 LOC) — LLM-powered response generation with function calling loop (max 5 iterations). Can short-circuit pipeline for simple requests | 425 |
| J5 | OrchestratorToolRegistry | 37, 42 | S112, S144 | COMPLETE | `hybrid/orchestrator/tools.py` (393 LOC) — Tool registration, discovery, and execution for Orchestrator Agent. Provides tool definitions for LLM function calling | 393 |
| J6 | PromptGuard (Injection Defense) | 36 | S109 | COMPLETE | `core/security/prompt_guard.py` (380 LOC) — 3-layer defense: L1 Input Filtering (regex patterns), L2 System Prompt Isolation (boundary enforcement), L3 Tool Call Validation (whitelist) | 380 |
| J7 | ToolSecurityGateway | 36 | S109 | COMPLETE | `core/security/tool_gateway.py` (594 LOC) — 4-layer security: Input Sanitization, Permission Check (UserRole RBAC), Rate Limiting (per-user per-tool), Audit Logging | 594 |
| J8 | UnifiedApprovalManager | 35 | S111 | COMPLETE | `orchestration/hitl/unified_manager.py` (545 LOC) — Single source of truth for ALL approval workflows. Consolidates 4-5 independent approval systems. Lifecycle: PENDING->APPROVED/REJECTED/EXPIRED/CANCELLED. Uses PostgreSQL ApprovalStore | 545 |
| J9 | Knowledge RAG Pipeline | 38 | S118 | COMPLETE | `integrations/knowledge/` (8 files, 1,318 LOC): rag_pipeline.py (229), document_parser.py (185), chunker.py (203), embedder.py (89), vector_store.py (177), retriever.py (168), agent_skills.py (242) — Full RAG: Document->Parse->Chunk->Embed->Index->Retrieve->Augment | 1,318 |
| J10 | Pipeline SSE Events | 39-42 | S134+ | COMPLETE | `hybrid/orchestrator/sse_events.py` (157 LOC) — SSE event emission for pipeline stages (routing, dialog, approval, execution, completion). Integrates with AG-UI bridge | 157 |
| J11 | Dispatch Handlers (MAF/Claude/Swarm) | 37, 42 | S112, S144 | COMPLETE | `hybrid/orchestrator/dispatch_handlers.py` (470 LOC) — Routes execution to MAF builders, Claude SDK, or Swarm based on routing decision. Handles mode-specific execution patterns | 470 |
| J12 | Session Recovery | 39 | S134 | COMPLETE | `hybrid/orchestrator/session_recovery.py` (226 LOC) — Session state recovery from checkpoint storage after crash/restart | 226 |
| J13 | E2E Validator | 39 | S134 | COMPLETE | `hybrid/orchestrator/e2e_validator.py` (206 LOC) — End-to-end pipeline validation, health checks for all handler dependencies | 206 |
| J14 | Orchestrator Memory Manager | 38 | S118 | COMPLETE | `hybrid/orchestrator/memory_manager.py` (446 LOC) — Cross-conversation memory management, integrates with mem0 for persistent context across sessions | 446 |
| J15 | Observability Bridge | 39 | S134 | COMPLETE | `hybrid/orchestrator/observability_bridge.py` (194 LOC) — Bridges OrchestrationMetricsCollector into the mediator pipeline for per-step metrics | 194 |
| J16 | Result Synthesiser | 39 | S134 | COMPLETE | `hybrid/orchestrator/result_synthesiser.py` (155 LOC) — Aggregates multi-source execution results into unified PipelineResponse | 155 |
| J17 | Swarm Task Decomposer | 43 | S148 | COMPLETE | `integrations/swarm/task_decomposer.py` (221 LOC) — LLM-powered task decomposition, parallel sub-task generation with specialist role assignment | 221 |
| J18 | Swarm Worker Executor | 43 | S148 | COMPLETE | `integrations/swarm/worker_executor.py` (402 LOC) — Independent worker LLM + function calling loop, SSE event emission for thinking/tool_call/progress | 402 |
| J19 | Swarm Worker Roles | 43 | S148 | COMPLETE | `integrations/swarm/worker_roles.py` (91 LOC) — 5 specialist roles (network, db, app, security, general) with ZH-TW system prompts and tool whitelists | 91 |
| J20 | MagenticBuilder Multi-Model | 44 | S17+ | COMPLETE | `agent_framework/builders/magentic.py` (1,810 LOC) — MagenticBuilderAdapter wrapping official MagenticBuilder. Dynamic planning, task/progress ledger, human intervention (PLAN_REVIEW, TOOL_APPROVAL, STALL). Imports from `agent_framework.orchestrations` | 1,810 |
| J21 | Security Audit Report | 36 | S109 | COMPLETE | `core/security/audit_report.py` (466 LOC) — Structured security audit report generation | 466 |
| J22 | RBAC Utility | 35 | S111 | PARTIAL | `core/security/rbac.py` (153 LOC) — Role enum (ADMIN/OPERATOR/VIEWER) + RBACManager permission checking utility. **NOT wired** into auth middleware | 153 |

### Per-Feature Detail (Key New Features)

#### J2: OrchestratorMediator
- **Status**: COMPLETE
- **Sprint**: S132-134
- **Implementation**: `hybrid/orchestrator/mediator.py` (844 LOC)
- **Business logic**: Central coordinator replacing HybridOrchestratorV2 God Object. Implements Mediator Pattern with 7 loosely-coupled handlers in a pipeline chain. Each handler encapsulates a single responsibility (SRP)
- **Handler chain**: ContextHandler (130 LOC) -> RoutingHandler (226 LOC) -> DialogHandler (120 LOC) -> ApprovalHandler (136 LOC) -> AgentHandler (425 LOC) -> ExecutionHandler (458 LOC) -> ObservabilityHandler (90 LOC)
- **Total handler LOC**: 1,160 (across 6 files in `handlers/`)
- **Dependencies**: All orchestration + hybrid subsystems
- **Known issues**: None — well-structured decomposition
- **Phase history**: Introduced Phase 35 (S132), wired Phase 39 (S134)

#### J4: AgentHandler (LLM Decision Engine)
- **Status**: COMPLETE
- **Sprint**: S107 (introduced), S144 (function calling)
- **Implementation**: `hybrid/orchestrator/agent_handler.py` (425 LOC)
- **Business logic**: LLM-powered response generation positioned in mediator pipeline after Approval and before Execution. Implements function calling loop with max 5 iterations. Can short-circuit pipeline for simple conversational requests (skipping Execution handler). Uses OrchestratorToolRegistry for tool definitions
- **Dependencies**: LLMServiceProtocol, OrchestratorToolRegistry
- **Known issues**: None
- **Phase history**: Introduced Phase 35 (S107), function calling added Phase 42 (S144)

#### J8: UnifiedApprovalManager
- **Status**: COMPLETE
- **Sprint**: S111
- **Implementation**: `orchestration/hitl/unified_manager.py` (545 LOC)
- **Business logic**: Single source of truth for ALL approval workflows across the platform. Consolidates 4-5 independent approval systems (Orchestration HITLController, AG-UI SSE, Claude SDK ApprovalHook, MAF Approval). Uses PostgreSQL ApprovalStore for persistence. Supports lifecycle: PENDING -> APPROVED/REJECTED/EXPIRED/CANCELLED. Notification routing (Teams, SSE)
- **Dependencies**: `infrastructure/storage/approval_store.py` (PostgreSQL)
- **Data persistence**: **PostgreSQL** (via ApprovalStore) — one of the few features with real DB persistence
- **Known issues**: None
- **Phase history**: Introduced Phase 35 (S111)

#### J9: Knowledge RAG Pipeline
- **Status**: COMPLETE
- **Sprint**: S118
- **Implementation**: `integrations/knowledge/` (8 files, 1,318 LOC)
- **Business logic**: End-to-end RAG pipeline. Two workflows: (1) Ingestion: Document -> Parse -> Chunk -> Embed -> Index; (2) Retrieval: Query -> Embed -> Search -> Rerank -> Augment. Supports recursive chunking strategy with configurable chunk_size/overlap. Uses Azure OpenAI embeddings via EmbeddingManager
- **Components**:
  - `rag_pipeline.py` (229 LOC) — RAGPipeline orchestrator
  - `document_parser.py` (185 LOC) — Multi-format document parsing
  - `chunker.py` (203 LOC) — DocumentChunker with RecursiveStrategy
  - `embedder.py` (89 LOC) — EmbeddingManager (Azure OpenAI)
  - `vector_store.py` (177 LOC) — VectorStoreManager
  - `retriever.py` (168 LOC) — KnowledgeRetriever with reranking
  - `agent_skills.py` (242 LOC) — Agent skill definitions for knowledge operations
- **Dependencies**: Azure OpenAI (embeddings), vector store backend
- **Data persistence**: Vector store (configurable)
- **Known issues**: None
- **Phase history**: Introduced Phase 38 (S118)

#### J20: MagenticBuilder Multi-Model
- **Status**: COMPLETE
- **Sprint**: S17 (initial), evolved through Phase 44
- **Implementation**: `agent_framework/builders/magentic.py` (1,810 LOC)
- **Business logic**: MagenticBuilderAdapter wrapping official `agent_framework.orchestrations.MagenticBuilder`. Supports dynamic planning with task/progress ledger (fact extraction, planning, progress evaluation). Human intervention: PLAN_REVIEW, TOOL_APPROVAL, STALL. MagenticManagerAdapter for custom manager behaviors
- **Dependencies**: `agent_framework.orchestrations` (MagenticBuilder, MagenticManagerBase, StandardMagenticManager)
- **Known issues**: None — uses official MAF API imports as required
- **Phase history**: Introduced Sprint 17, major enhancement Phase 44

---

## Cross-Category Analysis

### LOC Growth V8 -> V9

| Area | V8 LOC | V9 LOC | Delta |
|------|--------|--------|-------|
| Orchestration intent_router/ | ~5,000 | ~7,115 | +2,115 |
| Orchestration guided_dialog/ | ~3,529 | ~3,407 | -122 (refactored) |
| Swarm integrations/ | ~1,100 | 3,461 | **+2,361** |
| Hybrid orchestrator/ | — (new) | 6,073 | **+6,073** |
| Knowledge/ | — (new) | 1,318 | **+1,318** |
| Core security/ | — (not tracked) | 1,872 | **+1,872** |

### Maturity Assessment Update (V9)

| Category | V8 Maturity | V9 Maturity | Rationale |
|----------|-------------|-------------|-----------|
| F. Intelligent Decision | L2-L3 | L2-L3 | Unchanged — real LLM routing (L3), F7 API stub (L0) |
| G. Observability | L1 | L1 | Unchanged — 3 API stubs still disconnected |
| H. Agent Swarm | L2 | **L2-L3** | Upgraded — real LLM execution engine, still InMemory default |
| I. Security | L2 | **L2** | Enhanced — PromptGuard + ToolGateway added, RBAC not wired |
| J. New Features | — | **L2-L3** | Mediator (L3), RAG Pipeline (L2), UnifiedApproval (L3, PostgreSQL) |

### Priority Actions

1. **Wire G3/G4/G5 API routes** to existing integration layers — immediate 40% -> 100% for Category G
2. **Wire F7 API routes** to existing Claude SDK autonomous integration — fixes F7 SPLIT status
3. **Wire RBAC (I2)** into auth middleware — `core/security/rbac.py` exists but unused
4. **Persist G1/G2** to database — audit and tracing currently InMemory only

---

> **Generated**: 2026-03-29 | V9 Codebase Analysis
> **Method**: Full source code reading of all implementation files listed above
> **Scope**: 792 Python files, Phase 1-44 (Sprint 1-148+)

---

## Phase 45-47 Feature Additions (2026-04-19 sync)

### Category K: Unified Orchestration Pipeline (Phase 45)

| ID | Feature | Status | Evidence | Notes |
|----|---------|--------|----------|-------|
| K-01 | Unified 8-step orchestration pipeline | ✅ PRODUCTION | `integrations/orchestration/pipeline/service.py` (569 LOC) + 7 steps | Sprint 153-156 |
| K-02 | 27 PipelineEventType SSE events | ✅ PRODUCTION | `pipeline/service.py:27-61` | Covers lifecycle, step tracking, HITL/dialog pauses, agent team events |
| K-03 | Dialog pause + resume at Step 3 | ✅ PRODUCTION | `DialogPauseException` + `ResumeService` | Guided dialog for missing fields |
| K-04 | HITL pause + resume at Step 5 | ✅ PRODUCTION | `HITLPauseException` + `ApprovalService` | HIGH/CRITICAL risk gate |
| K-05 | Fast-path for high-confidence intent | ✅ PRODUCTION | `Step6LLMRoute` fast-path for QUERY/REQUEST confidence ≥ 0.92 | Bypasses LLM call |
| K-06 | Execution log persistence | ✅ PRODUCTION (Phase 47 W1) | `pipeline/persistence.py` + `orchestration_execution_log` ORM | Persists memory/knowledge text |
| K-07 | Transcript service (Redis Streams) | ✅ PRODUCTION | `transcript/service.py` | Per-session transcript |
| K-08 | Checkpoint-based resume | ✅ PRODUCTION | `resume/service.py` | Re-enters pipeline at paused step |

### Category L: Agent Expert Registry (Phase 46)

| ID | Feature | Status | Evidence | Notes |
|----|---------|--------|----------|-------|
| L-01 | YAML-based expert definitions | ✅ PRODUCTION | `experts/definitions/*.yaml` (6 builtin) | network/database/cloud/application/security/general |
| L-02 | Expert CRUD REST API | ✅ PRODUCTION | `api/v1/experts/routes.py` (6 endpoints) | Sprint 162-163 |
| L-03 | DB-backed expert persistence | ✅ PRODUCTION | `infrastructure/database/models/agent_expert.py` + repo | Sprint 163 |
| L-04 | Three-tier fallback (DB → YAML → worker_roles) | ✅ PRODUCTION | `registry.py:get_or_fallback()` | Graceful degradation |
| L-05 | Hot-reload registry | ✅ PRODUCTION | `POST /experts/reload` | Sprint 162 |
| L-06 | Built-in protection (is_builtin) | ✅ PRODUCTION | `routes.py` returns 403 on delete | Prevents accidental removal |
| L-07 | Version auto-bump on update | ✅ PRODUCTION | Repository `update()` method | Optimistic locking hint |
| L-08 | Domain-specific tool schemas | ✅ PRODUCTION | `domain_tools.py` DOMAIN_TOOLS dict + resolve_tools() | Sprint 160 |
| L-09 | Tool validation on YAML load | ✅ PRODUCTION | `tool_validator.py` | Schema validation |
| L-10 | Frontend Expert management UI | ✅ PRODUCTION | `pages/agent-experts/*.tsx` (4 pages) | Sprint 164 |
| L-11 | Expert domain/capability badges | ✅ PRODUCTION | `unified-chat/agent-team/ExpertBadges.tsx` | Sprint 161 |
| L-12 | Expert Roster Preview | ✅ PRODUCTION | `AgentRosterPanel.tsx` + `expertSelectionStore` | Sprint 165 |

### Category M: PoC Agent Team V4

| ID | Feature | Status | Evidence | Notes |
|----|---------|--------|----------|-------|
| M-01 | CC-style persistent agent loop | ✅ PRODUCTION (via TeamExecutor) | `poc/agent_work_loop.py` (1002 LOC) | Phase A/B/C loop |
| M-02 | SharedTaskList (in-memory) | ✅ PRODUCTION | `poc/shared_task_list.py` (370) | threading.Lock thread-safe |
| M-03 | Redis-backed task list | ✅ PRODUCTION | `poc/redis_task_list.py` (442) | Redis Streams + Hash, 1h TTL |
| M-04 | Event-driven HITL approval | ✅ PRODUCTION | `poc/approval_gate.py` | Zero-CPU asyncio.Event.wait() |
| M-05 | Inter-agent directed messages | ✅ PRODUCTION | `TeamMessage.to_agent` field | Per-agent inbox stream |
| M-06 | Task reassignment on failure | ✅ PRODUCTION | `SharedTaskList.reassign_task()` | With retry_count tracking |
| M-07 | 15-second communication window | ✅ PRODUCTION | `agent_work_loop.py` | Post-all-done comm phase |
| M-08 | AnthropicChatClient for MAF | ✅ PRODUCTION | `agent_framework/clients/anthropic_chat_client.py` (393) | Claude API as MAF ChatClient |
| M-09 | LLMCallPool concurrency control | ✅ PRODUCTION | integrated into `llm/` | Prevents rate-limit |

### Category N: Dynamic Agent Scaling (Sprint 166)

| ID | Feature | Status | Evidence |
|----|---------|--------|----------|
| N-01 | Dynamic agent count per task complexity | ✅ PRODUCTION | `dispatch/executors/subagent.py::_infer_complexity()` |
| N-02 | Complexity inference rules | ✅ PRODUCTION | Pipeline rules (risk + intent) + task text overrides; MAX_SUBTASKS=10 cap |

### Feature Count Update

| Metric | V9 Baseline | Post-Phase 47 |
|--------|-------------|---------------|
| Feature categories | A-J (10) | **A-N (14)** (+K Pipeline, +L Expert Registry, +M PoC Team V4, +N Dynamic Scaling) |
| Total features | 70+15 | **~110+** (+~30 new features) |

---

*Phase 45-47 features appended 2026-04-19 from source reading + commit messages (`git log 50ec420..HEAD`).*
