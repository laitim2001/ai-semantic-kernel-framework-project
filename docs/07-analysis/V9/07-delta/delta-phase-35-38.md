# Delta Report: Phase 35-38 (E2E Assembly A0-C)

> V8 -> V9 Changes | Sprints 107-120 | ~149 Story Points
> Period: 2026-03-19 ~ 2026-03-25 (estimated)

---

### Phase 35-38 斷點修復與 E2E 組裝時間線

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              Phase 35-38 E2E Assembly 時間線                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Sprint:  107──108──109──110──111──112──113──114──115──116──117──118──119──120│
│  Phase:   ├─P35─┤   ├──── Phase 36 ────┤   ├──── Phase 37 ────┤   ├P38┤   │
│                                                                             │
│  ① 斷點修復 (Phase 35, S107-108)                                           │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │  Breakpoint #1: AG-UI ──✗──→ InputGateway  → ✓ 修復資料流     │        │
│  │  Breakpoint #2: InputGateway ──✗──→ Mediator → ✓ 修復連接     │        │
│  │  C-07 SQL Injection (CRITICAL) → ✓ 參數化查詢修復             │        │
│  └─────────────────────────────────────────────────────────────────┘        │
│                                                                             │
│  ② 三層路由啟動 (Phase 35-36)                                              │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │  L1 PatternMatcher ✓ (regex, <1ms)                              │        │
│  │  L2 SemanticRouter ✗ (本階段跳過)                                │        │
│  │  L3 LLMClassifier  ✓ (Azure GPT-4o, 語義分類)                   │        │
│  └─────────────────────────────────────────────────────────────────┘        │
│                                                                             │
│  ③ 安全強化 (Phase 36, S113)                                               │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │  + PromptGuard (提示注入防護)                                   │        │
│  │  + ToolGateway (工具存取閘門)                                   │        │
│  │  + MCP Permission Checker                                       │        │
│  └─────────────────────────────────────────────────────────────────┘        │
│                                                                             │
│  ④ 合約與基礎設施 (Phase 37-38, S116-120)                                 │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │  + contracts.py (orchestration ↔ hybrid 跨模組合約)              │        │
│  │  + UnifiedApprovalManager (S111)                                 │        │
│  │  + Redis 集中化 (S119)                                           │        │
│  │  + ServiceNow MCP Server (S117)                                  │        │
│  └─────────────────────────────────────────────────────────────────┘        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### E2E 資料流 (Phase 35 修復後)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              Phase 35 修復後端到端資料流                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Chat UI (React)                                                            │
│     │ POST /api/v1/ag-ui/run                                               │
│     ↓                                                                       │
│  AG-UI Route ──── 修復 Breakpoint #1 ────→ InputGateway                    │
│                                               │ validate + sanitize         │
│                                               │ (C-07 SQL fix)             │
│                                               ↓                             │
│                   修復 Breakpoint #2 ────→ OrchestratorMediator             │
│                                               │                             │
│                                               ↓                             │
│                                          Intent Router                      │
│                                          ┌─── L1 Pattern ───┐              │
│                                          │  match? → route   │              │
│                                          │  else ↓           │              │
│                                          │  L2 (skipped)     │              │
│                                          │  else ↓           │              │
│                                          │  L3 LLM Classify  │              │
│                                          └───────┬───────────┘              │
│                                                  │                          │
│                                                  ↓                          │
│                                          AgentHandler                       │
│                                          │ Azure OpenAI GPT-4o              │
│                                          │ function calling                 │
│                                          ↓                                  │
│                                          Response ──→ SSE ──→ Chat UI      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 35: E2E Assembly A0 — Core Hypothesis Validation
- **Sprints**: 107-108
- **Story Points**: ~15
- **Status**: Completed

### New Files Added

**Backend — Orchestrator Core**
| File | Purpose |
|------|---------|
| `backend/src/integrations/hybrid/orchestrator/agent_handler.py` | LLM decision engine for OrchestratorMediator; uses Azure OpenAI function calling with `assess_risk()`, `search_memory()`, `request_approval()` and other registered tools via OrchestratorToolRegistry |
| `backend/src/integrations/hybrid/orchestrator/contracts.py` | Cross-module contract interfaces (Handler, HandlerResult, HandlerType, OrchestratorRequest) between `orchestration/` and `hybrid/` |
| `backend/src/integrations/orchestration/contracts.py` | Orchestration-side contract definitions |

### Modified Files
| File | Change |
|------|--------|
| `backend/src/api/v1/ag_ui/` | Fixed breakpoint #1: AG-UI chat endpoint -> InputGateway data flow |
| `backend/src/integrations/orchestration/input_gateway/gateway.py` | Fixed breakpoint #2: InputGateway -> OrchestratorMediator connection |
| `backend/src/integrations/orchestration/intent_router/router.py` | Enabled L1 PatternMatcher + L3 LLMClassifier routing |
| `backend/src/integrations/orchestration/intent_router/pattern_matcher/matcher.py` | Pattern matching for INCIDENT/QUERY/REQUEST intents |
| `backend/src/integrations/orchestration/intent_router/llm_classifier/classifier.py` | LLM-based semantic intent classification |

### Architecture Changes
- **Hybrid Orchestrator Model**: OrchestratorMediator retained for deterministic logic; AgentHandler added as LLM decision engine alongside it
- **FrameworkSelector**: Routes to Azure OpenAI (gpt-4o) as default, Claude as fallback
- **Three-layer Intent Routing**: L1 PatternMatcher (fast regex) + L3 LLMClassifier (semantic). L2 skipped this phase
- **Cross-module Contracts**: Pydantic-based interface definitions between orchestration/ and hybrid/ modules
- **C-07 SQL Injection Fix**: Security prerequisite fixed in `agent_framework/memory/postgres_storage.py` (parameterized queries)

### Features Added
- AgentHandler receives user input, calls LLM, returns structured responses
- Intent routing correctly classifies at least 3 intent types (INCIDENT, QUERY, REQUEST)
- End-to-end flow: Chat UI -> AG-UI -> InputGateway -> Mediator -> AgentHandler -> LLM -> Response
- Zero-mock validation (real Azure OpenAI API throughout)

### Issues Fixed
- **C-07 SQL Injection** (CRITICAL): Fixed in `agent_framework/memory/postgres_storage.py` with parameterized queries
- **Breakpoint #1**: AG-UI -> InputGateway data flow disconnection
- **Breakpoint #2**: InputGateway -> OrchestratorMediator data flow disconnection

---

## Phase 36: E2E Assembly A1 — Foundation Assembly
- **Sprints**: 109-112
- **Story Points**: ~48
- **Status**: Completed

### New Files Added

**Backend — Security Layer**
| File | Purpose |
|------|---------|
| `backend/src/core/security/tool_gateway.py` | Tool Security Gateway: input sanitization, permission check, rate limiting, audit logging for all tool calls |
| `backend/src/core/security/prompt_guard.py` | Prompt Injection defense: L1 input filtering, L2 system prompt isolation, L3 tool call validation |
| `backend/src/core/security/rbac.py` | Basic RBAC: Admin / Operator / Viewer role-based access control |
| `backend/src/core/security/audit_report.py` | Audit logging infrastructure |

**Backend — Orchestrator Enhancement**
| File | Purpose |
|------|---------|
| `backend/src/integrations/hybrid/orchestrator/tools.py` | New Orchestrator tools: `assess_risk()`, `search_memory()`, `request_approval()`, `create_task()` |
| `backend/src/integrations/hybrid/orchestrator/session_factory.py` | Per-Session Orchestrator instance manager with shared LLM Pool |

**Backend — HITL Unification**
| File | Purpose |
|------|---------|
| `backend/src/integrations/orchestration/hitl/unified_manager.py` | Unified approval manager consolidating 4-5 approval systems into one HITLController |
| `backend/src/integrations/orchestration/hitl/controller.py` | Central HITLController: single entry point for all approval flows |

### Modified Files
| File | Change |
|------|--------|
| `backend/src/integrations/orchestration/hitl/approval_handler.py` | Delegate to unified HITLController instead of independent storage |
| AG-UI ApprovalStorage | Changed to delegate to HITLController |
| Claude SDK ApprovalHook | Changed to delegate to HITLController |
| MAF handoff_hitl | Shared state with HITLController |
| Multiple InMemory stores (~15 modules) | Migrated to Redis (sessions, rate limiter) and PostgreSQL (approval, audit, checkpoint) |

### Architecture Changes
- **Tool Security Gateway**: All Orchestrator tool calls must pass through SecurityGateway (Input Sanitization -> Permission Check -> Rate Limit -> Audit)
- **Prompt Injection 3-Layer Defense**: L1 regex filtering, L2 delimiter token isolation, L3 tool call parameter validation
- **LLM Call Pool**: `asyncio.Semaphore` concurrency control + Priority Queue (P0 Direct Answer > P1 Intent Route > P2 Extended Thinking > P3 Swarm)
- **InMemory -> Persistent Storage Migration**: Dialog Sessions -> Redis (TTL), Approval State -> PostgreSQL, Audit Log -> PostgreSQL, Rate Limiter -> Redis, Checkpoint -> PostgreSQL. At least 15/28+ InMemory stores migrated
- **Unified Approval System**: 4-5 scattered approval systems consolidated into 1 HITLController with PostgreSQL persistence
- **Per-Session Orchestrator**: Each session gets independent Agent instance sharing a common LLM Pool
- **Tools Classification**: Synchronous Tools (< 5s) vs Async Dispatch Tools (return task_id)

### Features Added
- End-to-end login -> conversation -> intent understanding -> answer/approval flow
- Tool Security Gateway with full audit trail
- Prompt injection defense (>95% test pass rate target)
- LLM API concurrency control with priority queue
- Service restart no longer loses session or approval state
- Chat history backend sync (localStorage -> PostgreSQL)
- SSE streaming integration for real-time conversation
- Basic RBAC (Admin/Operator/Viewer) controlling tool call permissions

### Issues Fixed
- **H-04**: ContextSynchronizer race condition fixed with `asyncio.Lock`
- **InMemory Persistence** (multiple CRITICAL): Core state stores migrated to Redis/PostgreSQL
- **Approval Fragmentation** (HIGH): 4-5 independent approval systems unified

---

## Phase 37: E2E Assembly B — Task Execution Assembly
- **Sprints**: 113-116
- **Story Points**: ~48
- **Status**: Completed

### New Files Added

**Backend — Task Dispatch & Registry**
| File | Purpose |
|------|---------|
| `backend/src/integrations/hybrid/orchestrator/dispatch_handlers.py` | Dispatch tools: `dispatch_workflow()` (async/MAF), `dispatch_to_claude()` (sync/Claude), `dispatch_swarm()` (async/Swarm) |
| `backend/src/integrations/hybrid/orchestrator/task_result_protocol.py` | Unified TaskResult protocol for worker result return format |
| `backend/src/integrations/hybrid/orchestrator/result_synthesiser.py` | LLM-based result aggregation: synthesize multiple worker results into unified response |
| `backend/src/integrations/hybrid/orchestrator/session_recovery.py` | SessionRecoveryManager: `GET /sessions` -> `POST /sessions/{id}/resume` |
| `backend/src/integrations/hybrid/orchestrator/observability_bridge.py` | Circuit breaker + observability layer for LLM API failure degradation |
| `backend/src/integrations/hybrid/orchestrator/e2e_validator.py` | End-to-end validation utilities |

**Backend — Checkpoint System**
| File | Purpose |
|------|---------|
| `backend/src/infrastructure/database/repositories/checkpoint.py` | PostgreSQL checkpoint repository |
| `backend/src/infrastructure/database/models/checkpoint.py` | Checkpoint database model |

**API — Task Management**
| File | Purpose |
|------|---------|
| Task CRUD endpoints | `POST/GET/PUT/DELETE /api/v1/tasks`, `GET /api/v1/sessions`, `POST /api/v1/sessions/{id}/resume` |

### Modified Files
| File | Change |
|------|--------|
| `backend/src/integrations/hybrid/orchestrator/mediator.py` | Integrated ExecutionHandler with MAF/Claude/Swarm dispatch |
| `backend/src/integrations/agent_framework/checkpoint.py` | Enhanced with PostgreSQL backend support |
| `backend/src/integrations/agent_framework/multiturn/checkpoint_storage.py` | Migrated to PostgreSQL |
| `backend/src/integrations/swarm/swarm_integration.py` | Integrated with Orchestrator dispatch path |

### Architecture Changes
- **Three-tier Checkpoint**: L1 Conversation State (Redis, TTL 24h) / L2 Task State (PostgreSQL, permanent) / L3 Agent Execution State (PostgreSQL, permanent)
- **Task Registry**: PostgreSQL-backed task tracking (task_id, type, status, progress, assigned_agent, input_params, partial_results, checkpoint_data)
- **Async Dispatch Model**: `dispatch_workflow` and `dispatch_swarm` are asynchronous (return task_id, execute in background); `dispatch_to_claude` is synchronous
- **Session Resume**: Close and reopen sessions with full progress recovery via SessionRecoveryManager
- **Circuit Breaker**: LLM API failure triggers degradation mode with auto-recovery
- **Background Response**: MAF RC4 `continuation_token` for long-running tasks
- **ARQ Task Scheduling**: Long-duration Swarm/Workflow tasks don't occupy HTTP connections
- **Swarm Integration**: Moved from Demo API to Orchestrator `dispatch_swarm()` path with feature flag
- **G3/G4/G5 STUB Connection**: Patrol / Correlation / RootCause stub APIs connected end-to-end

### Features Added
- Orchestrator dispatches tasks to 3 worker types (MAF Workflow, Claude Worker, Swarm)
- Unified TaskResult protocol for worker result aggregation
- LLM-based result synthesis from multiple workers
- Task CRUD API + frontend task list page
- Three-layer checkpoint with automatic state persistence
- Session resume across service restarts
- Circuit breaker for LLM API outages
- Real-time SSE progress push to frontend
- Swarm enabled via feature flag (`SwarmModeHandler enabled=True`)

### Issues Fixed
- **Async Task Loss**: Task Registry persistence + ARQ retry mechanism
- **Session State Loss on Restart**: Three-layer checkpoint system
- **HTTP Connection Blocking**: ARQ background execution for long tasks

---

## Phase 38: E2E Assembly C — Memory & Knowledge Assembly
- **Sprints**: 117-120
- **Story Points**: ~38
- **Status**: Completed

### New Files Added

**Backend — Memory System**
| File | Purpose |
|------|---------|
| `backend/src/integrations/memory/unified_memory.py` | Unified memory manager: three-tier memory (Working/Session/Long-term) with automatic promotion |
| `backend/src/integrations/memory/mem0_client.py` | mem0 client integration for Long-term Memory (episodic + semantic) |
| `backend/src/integrations/memory/embeddings.py` | Embedding utilities for memory search |
| `backend/src/integrations/memory/types.py` | Memory type definitions |
| `backend/src/integrations/hybrid/orchestrator/memory_manager.py` | OrchestratorMemoryManager: orchestrates memory read/write within pipeline |

**Backend — Knowledge/RAG System**
| File | Purpose |
|------|---------|
| `backend/src/integrations/knowledge/document_parser.py` | Document parser: PDF / Word / HTML / Markdown |
| `backend/src/integrations/knowledge/chunker.py` | Chunking: recursive + semantic chunking strategies |
| `backend/src/integrations/knowledge/embedder.py` | Azure OpenAI text-embedding-3-large integration |
| `backend/src/integrations/knowledge/vector_store.py` | Qdrant collection management (create, update, delete) |
| `backend/src/integrations/knowledge/retriever.py` | Hybrid search (vector + keyword) + cross-encoder reranking |
| `backend/src/integrations/knowledge/rag_pipeline.py` | Complete RAG pipeline: parse -> chunk -> embed -> index -> retrieve -> rerank |
| `backend/src/integrations/knowledge/agent_skills.py` | MAF Agent Skills: ITIL SOP packaging (Incident Management, Change Management, Enterprise Architecture) via FileAgentSkillsProvider |

### Modified Files
| File | Change |
|------|--------|
| `backend/src/integrations/hybrid/orchestrator/tools.py` | Added `search_memory()` and `search_knowledge()` function tools |
| `backend/src/integrations/hybrid/orchestrator/agent_handler.py` | Memory retrieval injection into LLM context at conversation start |
| `backend/src/integrations/hybrid/orchestrator/mediator.py` | Integrated memory write on conversation end, memory read on conversation start |

### Architecture Changes
- **Three-tier Memory System**:
  - Layer 1: Working Memory (Redis, TTL 30min) — current conversation context, tool results
  - Layer 2: Session Memory (PostgreSQL, TTL 7d) — conversation summaries, task records
  - Layer 3: Long-term Memory (mem0 + Qdrant) — episodic memory (events, lessons), semantic memory (patterns)
  - Automatic promotion: Working -> Session -> Long-term on conversation end
- **RAG Pipeline**: Document Parse -> Chunking -> Embedding (text-embedding-3-large) -> Vector Index (Qdrant) -> Hybrid Search + Reranking
- **Agentic RAG**: Orchestrator Agent autonomously decides when/what to search via `search_knowledge()` function tool
- **Agent Skills**: ITIL SOPs packaged as MAF Agent Skills via FileAgentSkillsProvider (RC4 `context_provider` singular API)
- **Memory Injection**: New conversations automatically retrieve relevant memories and inject into LLM context

### Features Added
- Automatic conversation summary generation on dialogue end, written to mem0 Long-term Memory
- Automatic relevant memory retrieval and context injection at conversation start
- `search_memory()` tool: semantic search + time range + user filter
- Complete RAG pipeline for enterprise knowledge base
- `search_knowledge()` tool: Orchestrator autonomously decides when to search
- ITIL SOP Agent Skills (Incident Management, Change Management, Enterprise Architecture)
- Knowledge base management UI: document upload, index status, search test
- Knowledge base CRUD API
- Cross-session memory persistence verification
- Complete 10-step end-to-end flow test
- V9 codebase analysis baseline

### Issues Fixed
- **Memory Isolation**: Three-tier memory with proper TTL and promotion prevents memory leakage
- **Knowledge Gap**: RAG pipeline provides enterprise knowledge access previously unavailable
- **Context Loss**: Automatic memory injection ensures Orchestrator retains cross-session knowledge

---

## Summary: Phase 35-38 Delta (V8 -> V9)

### Aggregate Metrics
| Metric | Value |
|--------|-------|
| Total Sprints | 14 (107-120) |
| Total Story Points | ~149 |
| New Backend Python Files | ~40+ |
| New Frontend Files | 0 (Phase 35-38 focused on backend) |
| New Modules | memory/, knowledge/, hybrid/orchestrator/ (24 files) |
| Architecture Layers Added | Security Gateway, LLM Call Pool, Three-tier Memory, RAG Pipeline, Three-tier Checkpoint |

### V8 Issues Resolved
| Issue ID | Severity | Description |
|----------|----------|-------------|
| C-07 | CRITICAL | SQL Injection in `agent_framework/memory/postgres_storage.py` |
| H-04 | HIGH | ContextSynchronizer race condition |
| InMemory stores | CRITICAL | 15+ InMemory stores migrated to Redis/PostgreSQL |
| Approval fragmentation | HIGH | 4-5 scattered approval systems unified |
| No E2E flow | CRITICAL | Platform never ran end-to-end; now fully connected |
| No memory/knowledge | HIGH | No cross-session memory or knowledge retrieval |

### Key Architecture Transformation
**Before (V8)**: 70+ modules built independently, never connected end-to-end. No persistent state, no memory, no knowledge retrieval, fragmented approval.

**After (Phase 38)**: All core modules wired into a functioning pipeline: Auth -> Session -> Intent Route -> Risk Assess -> Approve -> Agent Execute -> Memory -> Response. Three-tier persistence (Redis/PostgreSQL/Qdrant), unified approval, RAG knowledge base, and automatic cross-session memory.
