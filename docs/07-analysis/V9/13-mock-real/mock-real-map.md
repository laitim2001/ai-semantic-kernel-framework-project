# Mock vs Real Implementation Analysis — V9

> **Date**: 2026-03-29
> **Scope**: Complete `backend/src/` (integrations/, domain/, infrastructure/, api/, core/) + `frontend/src/`
> **Method**: Grep-based pattern scan for `Mock`, `InMemory`, `fallback`, `simulated`, `Dict[str` storage patterns across 939+ source files

---

## Table of Contents

1. [Per-Module Status Matrix](#1-per-module-status-matrix)
2. [InMemory Risk Map](#2-inmemory-risk-map)
3. [Fallback Patterns](#3-fallback-patterns)
4. [Mock Selection Logic](#4-mock-selection-logic)
5. [Frontend Mock/Real](#5-frontend-mockreal)
6. [Summary Tables](#6-summary-tables)

---

### Mock/Real 實作光譜

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Mock / Real 實作光譜總覽                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  REAL only          REAL + fallback      InMemory ⚠       Mock fallback    │
│  (純實作)           (降級保護)           (揮發性風險)      (假資料)          │
│  ──────────        ─────────────        ────────────      ────────────     │
│                                                                             │
│  correlation/      llm/                 agent_framework/   patrol/          │
│  a2a/              claude_sdk/          hybrid/             domain/agents/  │
│  memory/           swarm/               orchestration/      domain/routing/ │
│  learning/         knowledge/           ag_ui/              domain/orch./   │
│  n8n/              incident/            mcp/                                │
│  shared/                                rootcause/                          │
│  contracts/                                                                 │
│                                                                             │
│  ←──────────── Production Ready ──────────── Risk Zone ──────────────→     │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Fallback 策略層級:                                                         │
│                                                                             │
│  ┌─── LLM Service ──────────────────────────────────────────────┐          │
│  │  Primary: Azure OpenAI (gpt-4o)                              │          │
│  │     │ 失敗                                                    │          │
│  │     ↓                                                         │          │
│  │  Fallback: Claude SDK (SmartFallback with retry chain)        │          │
│  │     │ 失敗                                                    │          │
│  │     ↓                                                         │          │
│  │  Dev only: MockLLMService (WARNING log)                       │          │
│  │  Prod: RuntimeError (不允許靜默降級)                          │          │
│  └───────────────────────────────────────────────────────────────┘          │
│                                                                             │
│  ┌─── Knowledge/RAG ────────────────────────────────────────────┐          │
│  │  Primary: Qdrant vector store                                 │          │
│  │     │ qdrant_client 不可用                                    │          │
│  │     ↓                                                         │          │
│  │  Fallback: In-memory hash (偽 embedding, 搜尋品質大幅下降)    │          │
│  └───────────────────────────────────────────────────────────────┘          │
│                                                                             │
│  ┌─── Patrol ───────────────────────────────────────────────────┐          │
│  │  Primary: psutil (系統資源監控)                                │          │
│  │     │ psutil 未安裝                                           │          │
│  │     ↓                                                         │          │
│  │  Fallback: 偽造監控數據 (fabricated metrics)                   │          │
│  └───────────────────────────────────────────────────────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 揮發性儲存風險圖

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    InMemory 揮發性儲存 — 資料遺失風險                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Component                    Module              Risk    Impact            │
│  ─────────                   ──────              ────    ──────            │
│                                                                             │
│  InMemoryCheckpointStorage   agent_framework/    🔴 HIGH  工作流狀態全部遺失│
│                              hybrid/                      進程重啟=從頭開始 │
│                                                                             │
│  InMemoryApprovalStorage     orchestration/hitl  🔴 HIGH  待審批項目消失    │
│                              incident/                    安全審批斷裂     │
│                                                                             │
│  InMemoryThreadRepository    ag_ui/thread        🟡 MED   對話歷史遺失     │
│                                                           用戶體驗中斷     │
│                                                                             │
│  InMemoryCache               ag_ui/              🟡 MED   快取失效         │
│                                                           效能短暫下降     │
│                                                                             │
│  InMemoryDialogSession       orchestration/      🟡 MED   引導對話中斷     │
│  Storage                     guided_dialog                需重新開始對話   │
│                                                                             │
│  InMemoryConversationMemory  domain/orch         🟢 LOW   已 deprecated    │
│  Store                                                    影響範圍小       │
│                                                                             │
│  InMemoryAuditStorage        mcp/security        🟡 MED   稽核軌跡遺失    │
│                                                           合規風險         │
│                                                                             │
│  InMemoryTransport           mcp/core            🟢 LOW   僅測試用途      │
│                                                           生產用 Stdio     │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────          │
│  建議: 🔴 HIGH → 立即遷移至 Redis/PostgreSQL                               │
│        🟡 MED  → 下一 Sprint 遷移                                          │
│        🟢 LOW  → 可接受 (測試/已棄用)                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Per-Module Status Matrix

### 1.1 integrations/ Modules

| Module | Status | Evidence | Notes |
|--------|--------|----------|-------|
| **llm/** | REAL + MOCK FALLBACK | `factory.py:81-239` — Auto-detects Azure OpenAI; falls back to `MockLLMService` in dev | Production: raises `RuntimeError` if unconfigured. Dev: silent mock with WARNING |
| **agent_framework/** | REAL + InMemory | `checkpoint.py:653` — `InMemoryCheckpointStorage`; `multiturn/adapter.py:360` defaults to `InMemoryCheckpointStorage()` | Checkpoint data volatile; multi-turn conversation state lost on restart |
| **claude_sdk/** | REAL + FALLBACK | `autonomous/fallback.py` — `SmartFallback` with retry chains; `executor.py:283` — step-level fallback actions | Designed fallback system with escalation; not silent degradation |
| **hybrid/** | REAL + InMemory | `switching/switcher.py:183` — `InMemoryCheckpointStorage`; `orchestrator/mediator.py:96` — in-memory `ConversationStateStore` fallback | Context synchronizer uses in-memory dict (known thread-safety issue per CLAUDE.md) |
| **orchestration/** | REAL + MOCK FALLBACK + InMemory | `intent_routes.py:54` — `USE_REAL_ROUTER` env toggle; `hitl/controller.py:647` — `InMemoryApprovalStorage`; `guided_dialog/context_manager.py:690` — `InMemoryDialogSessionStorage` | Router falls back to mock from `tests.mocks.orchestration`; HITL approvals volatile |
| **ag_ui/** | REAL + InMemory | `thread/storage.py:276` — `InMemoryThreadRepository`; `thread/storage.py:341` — `InMemoryCache`; `sse_buffer.py:42,64` — in-memory fallback | Redis replacements exist (`redis_storage.py`) but InMemory is default instantiation |
| **swarm/** | REAL | `worker_executor.py:249` — empty content fallback generate(); `task_decomposer.py:145` — single-task fallback on LLM failure | Operational fallbacks, not mock; real LLM execution with graceful degradation |
| **mcp/** | REAL + InMemory | `core/transport.py:321` — `InMemoryTransport`; `security/audit.py:265` — `InMemoryAuditStorage` | Transport and audit trail volatile |
| **memory/** | REAL | mem0 integration with Qdrant | Requires `qdrant_client` package; data persisted to `./qdrant_data/` |
| **knowledge/** | FALLBACK | `vector_store.py:73` — in-memory fallback if `qdrant_client` missing; `embedder.py:51` — hash-based pseudo-embedding fallback | Silent degradation: search returns all docs (no similarity) when Qdrant unavailable |
| **patrol/** | MOCK FALLBACK | `checks/resource_usage.py:54` — "psutil not installed, using mock data" | Resource monitoring returns fabricated metrics without psutil |
| **learning/** | REAL | `similarity.py:264` — word-overlap fallback when no embeddings | Graceful degradation to simpler algorithm |
| **audit/** | REAL | `types.py:22` — `FALLBACK_SELECTION` event type | Tracks fallback events in audit trail |
| **correlation/** | REAL | No mock patterns; operational graceful fallback in `analyzer.py:441` ("Sprint 130: Real data, graceful fallback") | Pure logic module with graceful fallback on data source methods |
| **rootcause/** | InMemory | `case_repository.py:13` — "In-memory mode for testing and fallback"; `:582` — heuristic fallback | Case data volatile; heuristic analysis when LLM unavailable |
| **incident/** | REAL + InMemory | `executor.py:24` — imports `InMemoryApprovalStorage`; `recommender.py:289` — rule-based fallback; `analyzer.py:142` — rule-based fallback | Approval storage volatile; LLM analysis degrades to rule-based |
| **a2a/** | REAL | No mock/fallback patterns found | Protocol implementation |
| **n8n/** | REAL | `orchestrator.py:617` — placeholder reasoning function | Operational; minor placeholder in default reasoning |
| **shared/** | REAL | No mock/fallback patterns found | Protocol definitions |
| **contracts/** | REAL | No mock/fallback patterns found | Interface contracts |

### 1.2 domain/ Modules

| Module | Status | Evidence | Notes |
|--------|--------|----------|-------|
| **agents/** | MOCK | `service.py:228` — `[Mock Response]` prefix; `tools/builtin.py:415-500` — `mock_weather`, `mock_results` | Agent chat returns mock responses; built-in tools use hardcoded fake data |
| **orchestration/** | MOCK + InMemory | `nested/sub_executor.py:264` — "Mock execution without engine"; `nested/recursive_handler.py:334` — "Mock execution"; `memory/in_memory.py:29` — `InMemoryConversationMemoryStore` | Sub-workflow execution is mocked; conversation memory volatile |
| **routing/** | MOCK | `scenario_router.py:355` — "Mock execution for MVP" | Scenario routing uses mock execution path |
| **sandbox/** | SIMULATED | `service.py:91` — "Fast sandbox creation - simulated startup time < 200ms" | No real process isolation; simulated sandbox |
| **triggers/** | MOCK | `webhook.py:548` — "Mock 執行 - 開發測試用" | Webhook trigger workflow execution is mocked |
| **sessions/** | REAL | `repository.py:88` — `SQLAlchemySessionRepository` | Database-backed session persistence |
| **checkpoints/** | REAL | `service.py:526` — proper HumanApprovalExecutor | Database-backed checkpoint system |
| **connectors/** | REAL | `registry.py:43` — `ConnectorRegistry` | In-memory registry but by design (configuration, not state) |
| **workflows/** | REAL | No mock patterns found | Business logic module |
| **executions/** | REAL | No mock patterns found | Execution tracking module |

### 1.3 infrastructure/ Layer

| Module | Status | Evidence | Notes |
|--------|--------|----------|-------|
| **database/** | REAL | SQLAlchemy ORM, BaseRepository, 8 models | Production-ready PostgreSQL integration |
| **cache/** | REAL | `llm_cache.py` — Redis-backed LLM response cache | Requires Redis; no fallback |
| **storage/backends/** | REAL + FALLBACK | `factory.py:86-252` — `StorageFactory` with auto-detection: Redis > Postgres > InMemory | Production: raises `RuntimeError`. Dev: InMemory fallback with warning |
| **distributed_lock/** | FALLBACK | `redis_lock.py:154` — `InMemoryLock`; `:242` — "using in-memory lock (single-process only)" | Silent degradation to single-process lock when Redis unavailable |
| **messaging/** | STUB | Only `__init__.py` exists | RabbitMQ integration NOT implemented |
| **storage/ (file)** | REAL (partial) | Storage abstraction layer 完整實作（16 files: factory, backends/base, backends/factory, backends/memory, backends/postgres_backend, backends/redis_backend, protocol, redis_backend, memory_backend, approval_store, audit_store, conversation_state, execution_state, session_store, task_store, storage_factories） | File blob storage (S3/Azure Blob) 未實作；key-value storage abstraction 已完整實作 |

### 1.4 api/ Layer (In-Memory Stores)

| Module | Status | Evidence | Notes |
|--------|--------|----------|-------|
| **autonomous/** | InMemory | `routes.py:87` — `AutonomousTaskStore` with `self._tasks: Dict[str, Dict]` | All autonomous task tracking lost on restart |
| **rootcause/** | InMemory | `routes.py:118` — `RootCauseStore` with `self._analyses: Dict[str, Dict]` | All root cause analyses lost on restart |
| **sessions/chat** | REAL | `chat.py:178` — `SimpleAgentRepository` backed by `AsyncSession` (DB) | Database-backed |
| **cache/** | FALLBACK | `routes.py:79` — "Failed to connect to Redis: Using mock service" | Cache management API falls back to mock |
| **orchestration/** | MOCK FALLBACK | `intent_routes.py:164` — `create_mock_router()`; `dialog_routes.py:161` — `create_mock_dialog_engine()` | Both import from `tests.mocks.orchestration` on failure |

---

## 2. InMemory Risk Map

### 2.1 Explicit InMemory Classes

| # | File Path | Class Name | Data Stored | Restart Impact |
|---|-----------|------------|-------------|----------------|
| 1 | `integrations/agent_framework/checkpoint.py:653` | `InMemoryCheckpointStorage` | Agent checkpoint snapshots (state, context) | **HIGH** — Multi-turn conversation state lost; agents restart from zero |
| 2 | `integrations/ag_ui/thread/storage.py:276` | `InMemoryThreadRepository` | AG-UI thread data (messages, metadata) | **HIGH** — All chat threads and message history lost |
| 3 | `integrations/ag_ui/thread/storage.py:341` | `InMemoryCache` | Thread cache entries (TTL-based) | **MEDIUM** — Temporary cache; re-fetched from source |
| 4 | `integrations/orchestration/hitl/controller.py:647` | `InMemoryApprovalStorage` | HITL approval requests and decisions | **HIGH** — Pending approvals lost; approved actions may re-trigger |
| 5 | `integrations/orchestration/guided_dialog/context_manager.py:690` | `InMemoryDialogSessionStorage` | Multi-turn dialog session context | **HIGH** — Active guided dialog sessions terminated |
| 6 | `integrations/hybrid/switching/switcher.py:183` | `InMemoryCheckpointStorage` | MAF/Claude SDK switching checkpoints | **MEDIUM** — Framework switching state reset; may cause mode confusion |
| 7 | `integrations/mcp/core/transport.py:321` | `InMemoryTransport` | MCP message transport buffer | **LOW** — Transport is transient by nature; reconnection restores |
| 8 | `integrations/mcp/security/audit.py:265` | `InMemoryAuditStorage` | MCP security audit events | **HIGH** — Audit trail lost; compliance gap |
| 9 | `domain/orchestration/memory/in_memory.py:29` | `InMemoryConversationMemoryStore` | Conversation history and context | **HIGH** — All conversation memory wiped; agents lose context |
| 10 | `infrastructure/storage/backends/memory.py:24` | `InMemoryBackend` | Generic key-value storage (used by StorageFactory fallback) | **HIGH** — All data stored via this backend lost |
| 11 | `infrastructure/storage/memory_backend.py:17` | `InMemoryStorageBackend` | Legacy generic storage | **HIGH** — Same as above |
| 12 | `infrastructure/distributed_lock/redis_lock.py:154` | `InMemoryLock` | Distributed lock state | **MEDIUM** — Lock state reset; concurrent operations may conflict briefly |
| 13 | `integrations/ag_ui/sse_buffer.py:42,64` | (inline dict) | SSE event buffer fallback | **LOW** — SSE events are transient; clients reconnect |

### 2.2 API-Layer In-Memory Stores

| # | File Path | Class Name | Data Stored | Restart Impact |
|---|-----------|------------|-------------|----------------|
| 14 | `api/v1/autonomous/routes.py:87` | `AutonomousTaskStore` | Autonomous task state + history | **HIGH** — Running tasks lost; no recovery |
| 15 | `api/v1/rootcause/routes.py:118` | `RootCauseStore` | Root cause analysis results | **MEDIUM** — Analysis results lost; can be re-run |

---

## 3. Fallback Patterns

### 3.1 Silent Fallback Paths

| # | Location | Trigger Condition | Fallback Behavior | User Visibility |
|---|----------|-------------------|-------------------|-----------------|
| 1 | `integrations/llm/factory.py:224-239` | No `AZURE_OPENAI_*` env vars in dev environment | Falls back to `MockLLMService` returning canned responses | **LOW** — User sees generic "Mock LLM response" text; WARNING in server logs only |
| 2 | `infrastructure/storage/backends/factory.py:248-252` | Neither `REDIS_HOST` nor `DB_HOST` set in dev | Falls back to `InMemoryBackend`; data lost on restart | **LOW** — User unaware; WARNING in server logs; data silently disappears on restart |
| 3 | `infrastructure/distributed_lock/redis_lock.py:242` | Redis unavailable | Falls back to `InMemoryLock` (single-process only) | **NONE** — Completely invisible; concurrent requests may have race conditions |
| 4 | `integrations/knowledge/vector_store.py:73` | `qdrant_client` package not installed | In-memory dict fallback; search returns all documents (no similarity ranking) | **LOW** — Search results are wrong (all docs returned) but no error shown |
| 5 | `integrations/knowledge/embedder.py:51` | `EmbeddingService` unavailable | Hash-based pseudo-embedding (deterministic but semantically meaningless) | **NONE** — Embeddings generated but quality is garbage; no user-facing error |
| 6 | `integrations/patrol/checks/resource_usage.py:54` | `psutil` package not installed | Returns mock resource usage data | **NONE** — Dashboard shows fabricated CPU/memory metrics |
| 7 | `integrations/orchestration/metrics.py:35` | `opentelemetry` package not installed | No-op metrics (counters/histograms do nothing) | **NONE** — Monitoring silently disabled |
| 8 | `integrations/hybrid/orchestrator/mediator.py:96` | `ConversationStateStore` unavailable | In-memory dict for conversation state | **NONE** — Works until restart; state then lost |
| 9 | `integrations/orchestration/hitl/unified_manager.py:170` | Storage backend unavailable | In-memory fallback for HITL approvals | **LOW** — WARNING logged; approvals work but lost on restart |
| 10 | `api/v1/cache/routes.py:79` | Redis connection failure | Mock cache service | **LOW** — Cache management API returns mock data |

### 3.2 Explicit Fallback Paths (with Warning/Error)

| # | Location | Trigger Condition | Fallback Behavior | User Visibility |
|---|----------|-------------------|-------------------|-----------------|
| 11 | `api/v1/orchestration/intent_routes.py:54-170` | `USE_REAL_ROUTER=false` or real router init failure | Imports `create_mock_router` from `tests.mocks.orchestration` | **MEDIUM** — WARNING logged; routing uses pattern-only matching (no LLM Layer 3) |
| 12 | `api/v1/orchestration/dialog_routes.py:158-165` | Dialog engine creation failure | Imports `create_mock_dialog_engine` from `tests.mocks.orchestration` | **MEDIUM** — WARNING logged; guided dialog returns scripted responses |
| 13 | `integrations/llm/factory.py:226-231` | No LLM config in **production** environment | Raises `RuntimeError` (refuses to start) | **HIGH** — Application fails to start; correct behavior |
| 14 | `infrastructure/storage/backends/factory.py:242-246` | Backend unavailable in **production** | Raises `RuntimeError` (refuses to degrade) | **HIGH** — Application fails to start; correct behavior |
| 15 | `integrations/swarm/task_decomposer.py:145` | LLM decomposition failure | Single-task fallback (treats entire task as one unit) | **LOW** — Task runs as single unit instead of parallelized subtasks |
| 16 | `integrations/swarm/worker_executor.py:249-263` | Worker returns empty content | Fallback `generate()` call to LLM | **NONE** — Transparent retry; user sees final result |
| 17 | `integrations/incident/recommender.py:289` | LLM enhancement failure | Rule-based recommendations only | **LOW** — Recommendations less nuanced but functional |
| 18 | `integrations/incident/analyzer.py:142` | LLM analysis failure | Rule-based analysis only | **LOW** — Analysis less detailed but functional |

### 3.3 Designed Fallback Systems (Not Bugs)

| # | Location | Purpose | Mechanism |
|---|----------|---------|-----------|
| A | `integrations/claude_sdk/autonomous/fallback.py` | `SmartFallback` — Multi-strategy retry + escalation chain | RETRY > SIMPLIFY > SKIP > HUMAN_ESCALATION |
| B | `integrations/orchestration/intent_router/` | Three-tier routing with cascading fallback | Pattern (<10ms) > Semantic (<100ms) > LLM (<2s) |
| C | `domain/orchestration/planning/task_decomposer.py:544` | Rule-based decomposition when LLM unavailable | Structural analysis without LLM |
| D | `integrations/learning/similarity.py:264` | Word overlap similarity when no embeddings | Simple but functional text matching |

---

## 4. Mock Selection Logic

### 4.1 LLM Service Factory (`integrations/llm/factory.py`)

The `LLMServiceFactory._detect_provider()` method (line 193) implements environment-aware auto-detection:

```
Decision Tree:
1. Try pydantic Settings → azure_openai_endpoint + api_key set? → "azure"
2. Fallback: os.getenv("AZURE_OPENAI_ENDPOINT") + os.getenv("AZURE_OPENAI_API_KEY") → "azure"
3. os.getenv("TESTING") == "true" OR os.getenv("LLM_MOCK") == "true" → "mock"
4. APP_ENV == "production" → RuntimeError (refuses to start without LLM)
5. APP_ENV == "development" (default) → "mock" + WARNING log
```

**Key Environment Variables**:
- `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` → Real Azure OpenAI
- `TESTING=true` or `LLM_MOCK=true` → Explicit mock
- `APP_ENV=production` → Fail-fast (no silent degradation)
- `APP_ENV=development` (default) → Mock with warning

### 4.2 Storage Backend Factory (`infrastructure/storage/backends/factory.py`)

The `StorageFactory._resolve_backend_type()` method (line 115) implements:

```
Decision Tree:
1. Explicit backend_type parameter (not "auto") → Use as specified
2. STORAGE_BACKEND env var (not "auto") → Use as specified
3. APP_ENV == "testing" → "memory"
4. REDIS_HOST env var set → "redis"
5. DB_HOST env var set → "postgres"
6. Default → "memory"
```

**Fallback on creation failure** (`_handle_fallback`, line 229):
- `APP_ENV == "production"` → `RuntimeError` (no silent degradation)
- Any other env → `InMemoryBackend` with WARNING log: "Data will be lost on restart"

### 4.3 Intent Router (`api/v1/orchestration/intent_routes.py`)

```
Decision Tree:
1. USE_REAL_ROUTER env var (default "true") == "true"?
   a. Yes → Try to create real three-tier router with LLM
      - Success → Real router with Pattern + Semantic + LLM layers
      - Failure → Fall through to mock
   b. No → Fall through to mock
2. Mock: import create_mock_router from tests.mocks.orchestration
   → WARNING: "Not acceptable in production"
```

---

## 5. Frontend Mock/Real

### 5.1 Swarm Hook Architecture

The frontend provides two parallel hook implementations for the Agent Swarm system:

| Hook | File | Data Source | Use Case |
|------|------|-------------|----------|
| `useSwarmMock` | `frontend/src/hooks/useSwarmMock.ts` | Local React state with preset scenarios | UI development, testing without backend |
| `useSwarmReal` | `frontend/src/hooks/useSwarmReal.ts` | Backend SSE events via `EventSource` | Production use with real agent execution |

### 5.2 Selection Mechanism

In `frontend/src/pages/SwarmTestPage.tsx` (lines 157-163):

```typescript
const [testMode, setTestMode] = useState<TestMode>('mock');  // Default: mock
const mockHook = useSwarmMock();
const realHook = useSwarmReal();
// Conditionally use based on testMode state
```

**Selection**: User-driven toggle on the SwarmTestPage UI. Default is `'mock'` mode.

### 5.3 Mock Hook Capabilities (`useSwarmMock`)

- **Fully client-side**: No backend dependency
- **Preset scenarios**: ETL Pipeline, Security Audit, Data Pipeline
- **Manual controls**: Create/add/remove workers, set status/progress, add thinking/tool calls
- **State management**: React `useState` for all swarm, worker, and message state

### 5.4 Real Hook Capabilities (`useSwarmReal`)

- **Backend SSE connection**: `EventSource` to `${API_BASE_URL}/swarm/demo/events/${swarmId}`
- **Demo API**: POST to `/swarm/demo/start` to initiate backend demo scenarios
- **Live updates**: `swarm_update` and `swarm_complete` SSE event handlers
- **Connection management**: `isConnected`, `isLoading`, `error` state tracking
- **Auto-cleanup**: EventSource closed on unmount

---

## 6. Summary Tables

### Table A: Module Status Matrix

| Module | Status | Evidence (file:line) |
|--------|--------|---------------------|
| `integrations/llm` | REAL + MOCK FALLBACK | `factory.py:224` — dev mock fallback |
| `integrations/agent_framework` | REAL + InMemory | `checkpoint.py:653` — InMemoryCheckpointStorage |
| `integrations/claude_sdk` | REAL + FALLBACK | `autonomous/fallback.py:163` — SmartFallback system |
| `integrations/hybrid` | REAL + InMemory | `switching/switcher.py:183` — InMemoryCheckpointStorage |
| `integrations/orchestration` | REAL + MOCK + InMemory | `intent_routes.py:164` — mock router; `hitl/controller.py:647` — InMemoryApprovalStorage |
| `integrations/ag_ui` | REAL + InMemory | `thread/storage.py:276` — InMemoryThreadRepository |
| `integrations/swarm` | REAL | `worker_executor.py:249` — operational fallback only |
| `integrations/mcp` | REAL + InMemory | `core/transport.py:321` — InMemoryTransport; `security/audit.py:265` — InMemoryAuditStorage |
| `integrations/memory` | REAL | mem0 + Qdrant integration |
| `integrations/knowledge` | FALLBACK | `vector_store.py:73` — in-memory fallback; `embedder.py:51` — hash fallback |
| `integrations/patrol` | MOCK FALLBACK | `checks/resource_usage.py:54` — mock data without psutil |
| `integrations/learning` | REAL | `similarity.py:264` — graceful degradation |
| `integrations/audit` | REAL | `types.py:22` — FALLBACK_SELECTION event type |
| `integrations/correlation` | REAL | No mock/fallback found |
| `integrations/rootcause` | InMemory | `case_repository.py:13` — in-memory mode |
| `integrations/incident` | REAL + InMemory | `executor.py:24` — InMemoryApprovalStorage import |
| `integrations/a2a` | REAL | No mock/fallback found |
| `integrations/n8n` | REAL | `orchestrator.py:617` — placeholder reasoning function |
| `integrations/shared` | REAL | No mock/fallback found |
| `integrations/contracts` | REAL | No mock/fallback found |
| `domain/agents` | MOCK | `service.py:228` — [Mock Response]; `tools/builtin.py:415` — mock_weather |
| `domain/orchestration` | MOCK + InMemory | `nested/sub_executor.py:264` — mock execution; `memory/in_memory.py:29` |
| `domain/routing` | MOCK | `scenario_router.py:355` — mock execution for MVP |
| `domain/sandbox` | SIMULATED | `service.py:91` — simulated startup |
| `domain/triggers` | MOCK | `webhook.py:548` — mock execution |
| `domain/sessions` | REAL | `repository.py:88` — SQLAlchemy repo |
| `domain/checkpoints` | REAL | Database-backed |
| `infrastructure/database` | REAL | SQLAlchemy + PostgreSQL |
| `infrastructure/cache` | REAL | Redis-backed |
| `infrastructure/storage` | REAL + FALLBACK | `backends/factory.py:248` — InMemory fallback in dev |
| `infrastructure/distributed_lock` | FALLBACK | `redis_lock.py:154` — InMemoryLock fallback |
| `infrastructure/messaging` | STUB | Only `__init__.py` — NOT IMPLEMENTED |
| `api/v1/autonomous` | InMemory | `routes.py:87` — AutonomousTaskStore |
| `api/v1/rootcause` | InMemory | `routes.py:118` — RootCauseStore |
| `api/v1/orchestration` | MOCK FALLBACK | `intent_routes.py:164` — mock router import |
| `frontend/swarm` | MOCK + REAL | `useSwarmMock.ts` / `useSwarmReal.ts` — user toggle |

### Table B: InMemory Locations and Restart Impact

| # | Location | Class | Data Stored | Restart Impact |
|---|----------|-------|-------------|----------------|
| 1 | `integrations/agent_framework/checkpoint.py:653` | InMemoryCheckpointStorage | Agent state snapshots | **HIGH** |
| 2 | `integrations/ag_ui/thread/storage.py:276` | InMemoryThreadRepository | Chat thread history | **HIGH** |
| 3 | `integrations/ag_ui/thread/storage.py:341` | InMemoryCache | Thread cache (TTL) | **MEDIUM** |
| 4 | `integrations/orchestration/hitl/controller.py:647` | InMemoryApprovalStorage | Pending HITL approvals | **HIGH** |
| 5 | `integrations/orchestration/guided_dialog/context_manager.py:690` | InMemoryDialogSessionStorage | Dialog session context | **HIGH** |
| 6 | `integrations/hybrid/switching/switcher.py:183` | InMemoryCheckpointStorage | Framework switch state | **MEDIUM** |
| 7 | `integrations/mcp/core/transport.py:321` | InMemoryTransport | MCP message buffer | **LOW** |
| 8 | `integrations/mcp/security/audit.py:265` | InMemoryAuditStorage | MCP audit events | **HIGH** |
| 9 | `domain/orchestration/memory/in_memory.py:29` | InMemoryConversationMemoryStore | Conversation memory | **HIGH** |
| 10 | `infrastructure/storage/backends/memory.py:24` | InMemoryBackend | Generic KV storage | **HIGH** |
| 11 | `infrastructure/storage/memory_backend.py:17` | InMemoryStorageBackend | Legacy KV storage | **HIGH** |
| 12 | `infrastructure/distributed_lock/redis_lock.py:154` | InMemoryLock | Lock state | **MEDIUM** |
| 13 | `integrations/ag_ui/sse_buffer.py:42` | (inline dict) | SSE buffer | **LOW** |
| 14 | `api/v1/autonomous/routes.py:87` | AutonomousTaskStore | Task state + history | **HIGH** |
| 15 | `api/v1/rootcause/routes.py:118` | RootCauseStore | Analysis results | **MEDIUM** |

**Summary**: 9 HIGH, 4 MEDIUM, 2 LOW restart-impact InMemory locations.

### Table C: Silent Fallback Paths

| # | Location | Trigger Condition | User Visibility |
|---|----------|-------------------|-----------------|
| 1 | LLM Factory (`factory.py:234`) | No Azure OpenAI config in dev | **LOW** — Log warning only; mock responses returned |
| 2 | Storage Factory (`factory.py:248`) | No Redis/Postgres in dev | **LOW** — Log warning only; data lost on restart |
| 3 | Distributed Lock (`redis_lock.py:242`) | Redis unavailable | **NONE** — In-memory lock; race conditions possible |
| 4 | Vector Store (`vector_store.py:73`) | qdrant_client missing | **NONE** — Returns all docs; no similarity |
| 5 | Embedder (`embedder.py:51`) | EmbeddingService unavailable | **NONE** — Hash-based pseudo-embeddings |
| 6 | Patrol Resource Check (`resource_usage.py:54`) | psutil missing | **NONE** — Fabricated CPU/memory metrics |
| 7 | Orchestration Metrics (`metrics.py:35`) | OpenTelemetry missing | **NONE** — All metrics silently disabled |
| 8 | Hybrid Mediator (`mediator.py:96`) | ConversationStateStore unavailable | **NONE** — In-memory; lost on restart |
| 9 | HITL Unified Manager (`unified_manager.py:170`) | Storage backend unavailable | **LOW** — Log warning; approvals volatile |
| 10 | Cache Routes (`cache/routes.py:79`) | Redis connection failure | **LOW** — Log warning; mock cache service |
| 11 | Intent Router (`intent_routes.py:160`) | USE_REAL_ROUTER=false or init failure | **MEDIUM** — Log warning; test mock router used |
| 12 | Dialog Engine (`dialog_routes.py:160`) | Engine creation failure | **MEDIUM** — Log warning; mock dialog engine |
| 13 | Incident Recommender (`recommender.py:289`) | LLM enhancement failure | **LOW** — Rule-based only; less nuanced |
| 14 | Incident Analyzer (`analyzer.py:142`) | LLM analysis failure | **LOW** — Rule-based only; less detailed |
| 15 | Swarm Task Decomposer (`task_decomposer.py:145`) | LLM decomposition failure | **LOW** — Single-task fallback |

**Summary**: 4 NONE visibility (completely silent), 8 LOW visibility (log only), 3 MEDIUM visibility.

---

## Key Findings

### Production Safety

The two critical factories (LLM and Storage) correctly implement **fail-fast in production** (`APP_ENV=production` raises `RuntimeError`). This prevents silent degradation in production deployments. However, the remaining 13 fallback paths have **no production guard** — they silently degrade regardless of environment.

### Highest Risk Areas

1. **HITL Approval Storage** (InMemory) — Pending human approvals lost on restart could cause unauthorized actions to re-execute or approved actions to be lost.
2. **Conversation Memory** (InMemory) — All agent conversation context lost; agents restart conversations from scratch.
3. **MCP Audit Storage** (InMemory) — Compliance audit trail volatility; security events lost.
4. **Autonomous Task Store** (API-layer InMemory) — Running autonomous tasks have no recovery mechanism.
5. **Mock Agent Responses** (`domain/agents/service.py`) — The primary chat service returns `[Mock Response]` prefixed text, indicating the core chat feature is not fully production-ready.

### Mock vs Real Ratio

- **Fully Real (production-ready)**: 15 modules (correlation, a2a, audit, learning, swarm, memory, sessions, checkpoints, database, cache, workflows, executions, n8n, shared, contracts)
- **Real with InMemory risk**: 8 modules (agent_framework, ag_ui, orchestration, hybrid, mcp, rootcause, incident, storage)
- **Real with Mock fallback**: 4 modules (llm, orchestration routes, dialog routes, cache routes)
- **Predominantly Mock/Simulated**: 5 modules (agents, routing, sandbox, triggers, domain/orchestration nested)
- **Stub/Not Implemented**: 2 modules (messaging, file storage)

---

*Generated by V9 Mock/Real Analysis — 2026-03-29*
