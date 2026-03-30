# Memory Architecture — Unified Analysis

> **V9 Cross-Cutting Analysis** | **Date**: 2026-03-30 | **Scope**: memory/, knowledge/, checkpoint/, storage/, sessions/ across integrations + infrastructure + domain layers
> **Sources**: `layer-09-integrations.md` (memory/, knowledge/), `layer-11-infrastructure.md` (storage/, checkpoint/, cache/), `layer-10-domain.md` (sessions/), `mock-real-map.md` (InMemory risks)

---

## Table of Contents

1. [Three-Layer Memory Hierarchy](#1-three-layer-memory-hierarchy)
2. [State Management Components](#2-state-management-components)
3. [Checkpoint Unification](#3-checkpoint-unification)
4. [RAG Pipeline (knowledge/)](#4-rag-pipeline-knowledge)
5. [InMemory Volatility Risks](#5-inmemory-volatility-risks)
6. [Component-to-Storage Mapping](#6-component-to-storage-mapping)
7. [Migration Recommendations](#7-migration-recommendations)
8. [Architecture Summary](#8-architecture-summary)

---

## 1. Three-Layer Memory Hierarchy

IPA Platform 採用三層記憶體架構，由 `integrations/memory/unified_memory.py` 中的 `UnifiedMemoryManager` 統一協調。三層之間具備降級容錯鏈 (fallback chain): L1 不可用時降級至 L2, L2 不可用時降級至 L3。

### 1.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 IPA Platform 三層記憶體階層架構                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────┐      │
│  │  L1: 工作記憶 (Working Memory)                                    │      │
│  │  ─────────────────────────────────────────────────────────────    │      │
│  │  儲存: Redis                   TTL: 30 分鐘                      │      │
│  │  用途: Session 活躍資料、LLM 回應快取、Dialog Session 狀態        │      │
│  │  存取: 低延遲 (<1ms)           容量: 數百 MB                     │      │
│  │                                                                   │      │
│  │  元件:                                                            │      │
│  │  ├─ ConversationStateStore (prefix: conv:, TTL 24h)              │      │
│  │  ├─ LLMCacheService (content hash key, TTL configurable)         │      │
│  │  ├─ SessionStore (prefix: ipa:sessions:, TTL 24h)                │      │
│  │  └─ RedisCheckpointCache (TTL 7d)                                │      │
│  └───────────────┬───────────────────────────────────────────────────┘      │
│                  │ TTL 過期 / 容錯降級                                      │
│                  ↓                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐      │
│  │  L2: 會話記憶 (Session Memory)                                    │      │
│  │  ─────────────────────────────────────────────────────────────    │      │
│  │  儲存: PostgreSQL + Redis      保留: 7 天                        │      │
│  │  用途: Checkpoint、對話歷史、Thread 快取、Classification Cache    │      │
│  │  存取: 中延遲 (~5ms)           容量: 數十 GB                     │      │
│  │                                                                   │      │
│  │  元件:                                                            │      │
│  │  ├─ PostgresCheckpointStorage (永久, via CheckpointRepository)   │      │
│  │  ├─ SessionModel + MessageModel (DB, 對話歷史)                   │      │
│  │  ├─ ExecutionStateStore (prefix: exec:, 永久, Postgres)          │      │
│  │  ├─ ApprovalStore (prefix: ipa:approvals:, Postgres)             │      │
│  │  └─ AuditStore (prefix: ipa:audit:, 永久, Postgres)             │      │
│  │                                                                   │      │
│  │  ⚠ 已知問題: Session Memory 目前實際使用 Redis + longer TTL,     │      │
│  │    程式碼註解: "In production, this would use PostgreSQL"          │      │
│  └───────────────┬───────────────────────────────────────────────────┘      │
│                  │ TTL 過期 / 永久保存                                      │
│                  ↓                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐      │
│  │  L3: 長期記憶 (Long-Term Memory)                                  │      │
│  │  ─────────────────────────────────────────────────────────────    │      │
│  │  儲存: mem0 + Qdrant 向量資料庫   保留: 永久                     │      │
│  │  用途: Agent 學習、知識庫、語義搜尋、最佳實踐                     │      │
│  │  存取: 高延遲 (~50ms)              容量: 數百 GB+                │      │
│  │                                                                   │      │
│  │  元件:                                                            │      │
│  │  ├─ Mem0Client (mem0 SDK 封裝, Azure OpenAI / Anthropic LLM)    │      │
│  │  ├─ VectorStoreManager (Qdrant 集合管理)                         │      │
│  │  ├─ EmbeddingService (文本向量化)                                │      │
│  │  └─ RAGPipeline (端到端知識檢索)                                 │      │
│  └───────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│  ┌─── 降級容錯鏈 (Fallback Chain) ──────────────────────────────────┐      │
│  │  L1 Redis 不可用 → 降級至 L2 Session Memory (Redis longer TTL)   │      │
│  │  L2 不可用 → 降級至 L3 mem0 (永久儲存)                           │      │
│  │  Qdrant 不可用 → In-memory dict (無相似度排序, 品質大幅下降)     │      │
│  └───────────────────────────────────────────────────────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Layer Selection Logic

`UnifiedMemoryManager` 根據記憶類型 (MemoryType) 與重要性分數 (importance) 自動路由至對應層級:

| Memory Type | Importance | Target Layer | Rationale |
|-------------|-----------|-------------|-----------|
| `EVENT_RESOLUTION` | any | L3 Long-Term | 事件解決經驗需永久保存 |
| `BEST_PRACTICE` | any | L3 Long-Term | 最佳實踐為組織知識 |
| `SYSTEM_KNOWLEDGE` | any | L3 Long-Term | 系統知識需跨 Session 存取 |
| `USER_PREFERENCE` | any | L3 Long-Term | 使用者偏好需持久化 |
| `FEEDBACK` | any | L2 Session | 回饋在 Session 期間有效 |
| `CONVERSATION` | >= 0.8 | L3 Long-Term | 高價值對話永久保存 |
| `CONVERSATION` | >= 0.5 | L2 Session | 中等對話 Session 級保存 |
| `CONVERSATION` | < 0.5 | L1 Working | 低價值對話短暫保存 |
| Default | < 0.8 | L2 Session | 預設路由至 Session 層 |

---

## 2. State Management Components

### 2.1 Complete State Component Inventory

```
┌─────────────────────────────────────────────────────────────────────────────┐
│               狀態管理元件總覽 (State Management Components)                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─── 高階儲存 (High-Level Stores, Sprint 110-115) ────────────────┐      │
│  │  全部基於 StorageBackendABC (Sprint 110 介面)                     │      │
│  │                                                                   │      │
│  │  ┌──────────────────┐  ┌──────────────────┐                      │      │
│  │  │  SessionStore    │  │ ConversationState│                      │      │
│  │  │  ipa:sessions:   │  │ Store            │                      │      │
│  │  │  TTL: 24h        │  │ conv: TTL: 24h   │                      │      │
│  │  │  Backend: Redis  │  │ Backend: Redis   │                      │      │
│  │  └──────────────────┘  └──────────────────┘                      │      │
│  │                                                                   │      │
│  │  ┌──────────────────┐  ┌──────────────────┐                      │      │
│  │  │ ExecutionState   │  │  ApprovalStore   │                      │      │
│  │  │ Store            │  │  ipa:approvals:  │                      │      │
│  │  │ exec: 永久       │  │  Per-record TTL  │                      │      │
│  │  │ Backend: Postgres│  │  Backend: Postgres│                     │      │
│  │  └──────────────────┘  └──────────────────┘                      │      │
│  │                                                                   │      │
│  │  ┌──────────────────┐  ┌──────────────────┐                      │      │
│  │  │  AuditStore      │  │  TaskStore       │                      │      │
│  │  │  ipa:audit: 永久 │  │  task: 永久      │                      │      │
│  │  │  Backend: Postgres│  │  Backend: Auto   │                     │      │
│  │  └──────────────────┘  └──────────────────┘                      │      │
│  └───────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│  ┌─── 領域特定工廠 (Domain Factories, Sprint 119-120) ──────────────┐      │
│  │  全部基於 StorageBackend Protocol (Sprint 119 介面)               │      │
│  │                                                                   │      │
│  │  create_approval_storage()         → HITL ApprovalStorage         │      │
│  │  create_dialog_session_storage()   → GuidedDialog SessionStorage  │      │
│  │  create_thread_repository()        → AG-UI ThreadRepository       │      │
│  │  create_ag_ui_cache()              → AG-UI CacheProtocol          │      │
│  │  create_conversation_memory_store()→ ConversationMemoryStore      │      │
│  │  create_switch_checkpoint_storage()→ ModeSwitcher Checkpoint      │      │
│  │  create_audit_storage()            → MCP AuditStorage             │      │
│  │  create_agent_framework_checkpoint → MAF MultiTurn Checkpoint     │      │
│  │  _storage()                                                       │      │
│  │                                                                   │      │
│  │  策略: Prod = Redis 必須 | Dev = Redis + InMemory 降級            │      │
│  │        Testing = 直接 InMemory                                    │      │
│  └───────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│  ┌─── 雙重後端介面問題 (Dual Backend Interface Issue) ──────────────┐      │
│  │                                                                   │      │
│  │  Sprint 110 ABC (StorageBackendABC)                               │      │
│  │  ├─ TTL 型別: Optional[timedelta]                                │      │
│  │  ├─ 實作: InMemoryBackend, RedisBackend, PostgresBackend         │      │
│  │  └─ 使用者: 6 High-Level Stores                                  │      │
│  │                                                                   │      │
│  │  Sprint 119 Protocol (StorageBackend)                             │      │
│  │  ├─ TTL 型別: Optional[int] (seconds)                            │      │
│  │  ├─ 實作: RedisStorageBackend, InMemoryStorageBackend            │      │
│  │  └─ 使用者: 7 Domain Factories                                   │      │
│  │                                                                   │      │
│  │  ⚠ 兩套介面不相容! ABC stores 無法傳入 Protocol 消費者           │      │
│  └───────────────────────────────────────────────────────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Key Components Detail

#### SessionStore (Dict-like, Redis-backed, 24h TTL)

| Attribute | Value |
|-----------|-------|
| **Location** | `infrastructure/storage/session_store.py` |
| **Sprint** | 110 |
| **Interface** | StorageBackendABC |
| **Key Prefix** | `ipa:sessions:` |
| **TTL** | 24 hours |
| **Backend** | Redis (auto-detected), InMemory fallback in dev |
| **Purpose** | Session active state, user context, runtime config |

#### CheckpointStorage (3 backends: PostgreSQL, Redis, InMemory)

See [Section 3: Checkpoint Unification](#3-checkpoint-unification) for full details on the 4 independent checkpoint systems and the unification effort.

#### ContextBridge (Cross-Framework State Synchronization)

| Attribute | Value |
|-----------|-------|
| **Location** | `integrations/hybrid/switching/switcher.py` |
| **Sprint** | 57 (Phase 14) |
| **Purpose** | MAF <-> Claude SDK 跨框架狀態同步 |
| **Backend** | InMemoryCheckpointStorage (volatile!) |
| **Known Issue** | In-memory dict, thread-safety issue documented in CLAUDE.md |
| **Risk** | 🔴 HIGH — 進程重啟時跨框架同步狀態全部遺失 |

#### ConversationMemoryStore (InMemory Risk!)

| Attribute | Value |
|-----------|-------|
| **Location** | `domain/orchestration/memory/in_memory.py` |
| **Sprint** | P9 |
| **Status** | DEPRECATED (已被 `integrations/hybrid/` 取代) |
| **Backend** | 3 Python dicts (`_sessions`, `_turns`, `_messages`) |
| **Risk** | 🟢 LOW — 已棄用, 影響範圍小 |
| **Migration** | `create_conversation_memory_store()` factory (Sprint 119) 提供 Redis-backed 替代 |

---

## 3. Checkpoint Unification

### 3.1 Four Independent Checkpoint Systems

平台歷史演進中產生了 4 套獨立的 Checkpoint 系統:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              4 套獨立 Checkpoint 系統 → 統一註冊表                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                                  │
│  │ 1. Domain       │  │ 2. Hybrid       │                                  │
│  │ Checkpoint      │  │ Checkpoint      │                                  │
│  │ Sprint 2        │  │ Sprint 57       │                                  │
│  │ PostgreSQL      │  │ Memory/Redis/   │                                  │
│  │ UUID execution  │  │ Postgres/FS     │                                  │
│  │ _id + node_id   │  │ CheckpointType  │                                  │
│  └───────┬─────────┘  └───────┬─────────┘                                  │
│          │                     │                                            │
│          ↓                     ↓                                            │
│  ┌─────────────────────────────────────────────────────┐                   │
│  │         UnifiedCheckpointRegistry (Sprint 120)       │                   │
│  │         ─────────────────────────────────────        │                   │
│  │         CheckpointEntry (統一資料模型)                │                   │
│  │         CheckpointProvider (統一協定)                 │                   │
│  │         4 Adapters (適配器模式)                       │                   │
│  │         asyncio.Lock (執行緒安全)                     │                   │
│  └─────────────────────────────────────────────────────┘                   │
│          ↑                     ↑                                            │
│  ┌───────┴─────────┐  ┌───────┴─────────┐                                  │
│  │ 3. Agent        │  │ 4. Session      │                                  │
│  │ Framework       │  │ Recovery        │                                  │
│  │ Sprint 24       │  │ Sprint 47       │                                  │
│  │ Redis/Postgres/ │  │ Cache (Redis)   │                                  │
│  │ FS              │  │ SessionCheck-   │                                  │
│  │ session_id KV   │  │ point + TTL     │                                  │
│  └─────────────────┘  └─────────────────┘                                  │
│                                                                             │
│  統一協定:                                                                  │
│  CheckpointProvider.save_checkpoint(id, data, metadata) -> str             │
│  CheckpointProvider.load_checkpoint(id) -> Optional[Dict]                  │
│  CheckpointProvider.list_checkpoints(session_id, limit) -> List            │
│  CheckpointProvider.delete_checkpoint(id) -> bool                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Adapter Mapping

| Adapter | Wraps | Key Translation | Sprint |
|---------|-------|-----------------|--------|
| `HybridCheckpointAdapter` | `UnifiedCheckpointStorage` | unified_data stored in HybridCheckpoint.metadata | 120 |
| `DomainCheckpointAdapter` | `DatabaseCheckpointStorage` | String checkpoint_id <-> UUID; extracts execution_id | 121 |
| `AgentFrameworkCheckpointAdapter` | `BaseCheckpointStorage` | checkpoint_id as session_id; unified_data envelope | 121 |
| `SessionRecoveryCheckpointAdapter` | `SessionRecoveryManager` | checkpoint_id = session_id; 1 checkpoint/session | 121 |

### 3.3 Known Issue

`UnifiedCheckpointRegistry.cleanup_expired()` 呼叫 `list_checkpoints(limit=1000)` 後逐一 `delete_checkpoint()`, 為 O(N) 刪除操作, 大量 checkpoint 時效能堪慮。

---

## 4. RAG Pipeline (knowledge/)

### 4.1 Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    knowledge/ — RAG Pipeline 完整資料流                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ═══════════════════ 攝取管線 (Ingestion Pipeline) ═══════════════════      │
│                                                                             │
│  ① 文件輸入              ② 格式解析              ③ 文本切片                │
│  ┌──────────────┐       ┌──────────────┐       ┌──────────────┐            │
│  │  PDF / DOCX  │──────→│ DocumentParser│──────→│ DocumentChunk│            │
│  │  MD / TXT    │       │ (格式自動偵測)│       │ er           │            │
│  └──────────────┘       └──────────────┘       │ (遞迴切片)   │            │
│                                                 │ 1000 chars   │            │
│                                                 │ 200 overlap  │            │
│                                                 └──────┬───────┘            │
│                                                        │                    │
│                                                        ↓                    │
│  ④ 向量化                                      ⑤ 索引儲存                  │
│  ┌──────────────┐                              ┌──────────────┐            │
│  │ Embedding    │──── vectors ────────────────→│ VectorStore  │            │
│  │ Manager      │                              │ Manager      │            │
│  │ (Azure OpenAI│                              │ (Qdrant)     │            │
│  │  / OpenAI)   │                              │              │            │
│  └──────────────┘                              └──────────────┘            │
│                                                                             │
│  ═══════════════════ 檢索管線 (Retrieval Pipeline) ═══════════════════     │
│                                                                             │
│  ⑥ 查詢向量化           ⑦ 語義檢索              ⑧ 重排序                  │
│  ┌──────────────┐       ┌──────────────┐       ┌──────────────┐            │
│  │ User Query   │──────→│ Knowledge    │──────→│  Reranker    │            │
│  │ → embed_text()│       │ Retriever    │       │ (交叉注意力) │            │
│  └──────────────┘       │ (top-K 候選) │       │ → top-N 精排 │            │
│                          └──────────────┘       └──────┬───────┘            │
│                                                        │                    │
│                                                        ↓                    │
│  ⑨ 回答生成                                                                │
│  ┌──────────────────────────────────────────────────────────────┐          │
│  │  LLM (via llm/ module)                                       │          │
│  │  System Prompt = user_query + retrieved_docs (formatted)     │          │
│  │  → retrieve_and_format() 產生 LLM 可直接使用的 context        │          │
│  └──────────────────────────────────────────────────────────────┘          │
│                                                                             │
│  ═══════════════════ 降級策略 (Fallback Strategy) ═══════════════════      │
│                                                                             │
│  Qdrant 可用 → 正常語義搜尋 (餘弦相似度)                                   │
│  Qdrant 不可用 → In-memory dict 降級:                                       │
│    • 無相似度排序, 直接回傳 docs[:limit]                                    │
│    • Hash-based pseudo-embedding (非真實向量)                               │
│    • ⚠ 搜尋品質大幅下降                                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 RAG Component Summary

| Component | File | LOC | Key Methods |
|-----------|------|-----|-------------|
| `RAGPipeline` | `rag_pipeline.py` | ~230 | `ingest_file()`, `ingest_text()`, `retrieve()`, `retrieve_and_format()` |
| `VectorStoreManager` | `vector_store.py` | ~178 | `initialize()`, `index_documents()`, `search()`, `delete_collection()` |
| `DocumentChunker` | `chunker.py` | ~180 | `chunk()` — Recursive splitting, 1000 chars, 200 overlap |
| `DocumentParser` | `document_parser.py` | ~200 | `parse()` — Auto-detect PDF/DOCX/MD/TXT |
| `EmbeddingManager` | `embedder.py` | ~150 | `embed_text()`, `embed_batch()` — Hash fallback if no API |
| `KnowledgeRetriever` | `retriever.py` | ~150 | `retrieve()` — Search + rerank pipeline |

---

## 5. InMemory Volatility Risks

### 5.1 Complete InMemory Risk Registry

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                InMemory 揮發性儲存 — 完整風險登記表                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  風險等級    元件                        模組              衝擊              │
│  ────────   ─────                      ──────            ──────            │
│                                                                             │
│  🔴 HIGH    InMemoryCheckpointStorage  agent_framework/  工作流狀態全部遺失 │
│                                        hybrid/           進程重啟 = 從頭開始│
│                                                                             │
│  🔴 HIGH    InMemoryApprovalStorage    orchestration/    待審批項目消失     │
│                                        hitl/             安全審批鏈斷裂     │
│                                        incident/                            │
│                                                                             │
│  🟡 MEDIUM  InMemoryThreadRepository   ag_ui/thread      對話歷史遺失       │
│                                                          用戶體驗中斷       │
│                                                                             │
│  🟡 MEDIUM  InMemoryCache              ag_ui/            快取失效           │
│                                                          效能短暫下降       │
│                                                                             │
│  🟡 MEDIUM  InMemoryDialogSession      orchestration/    引導對話中斷       │
│             Storage                    guided_dialog     需重新開始對話     │
│                                                                             │
│  🟡 MEDIUM  InMemoryAuditStorage       mcp/security      稽核軌跡遺失       │
│                                                          合規風險           │
│                                                                             │
│  🟡 MEDIUM  Domain InMemory modules    domain/audit      決策追蹤遺失       │
│             (audit, routing, learning, domain/routing     路由規則遺失       │
│              versioning, devtools)     domain/learning    學習資料遺失       │
│             共 ~2,100 LOC             domain/versioning  版本歷史遺失       │
│                                        domain/devtools   開發工具狀態遺失   │
│                                                                             │
│  🟢 LOW     InMemoryConversationMemory domain/orch       已 deprecated      │
│             Store                                        影響範圍小         │
│                                                                             │
│  🟢 LOW     InMemoryTransport          mcp/core          僅測試用途         │
│                                                          生產用 Stdio       │
│                                                                             │
│  🟢 LOW     VectorStore In-memory      knowledge/        Qdrant 不可用時降級│
│             fallback                                     搜尋品質下降       │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  統計: 🔴 HIGH × 2 | 🟡 MEDIUM × 5 (+5 domain modules) | 🟢 LOW × 3      │
│  影響: 進程重啟時約 12 個元件面臨資料遺失風險                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Data Loss Impact Analysis

| Risk Level | Component | Data Lost on Restart | User-Facing Impact |
|------------|-----------|---------------------|-------------------|
| 🔴 HIGH | InMemoryCheckpointStorage | All workflow checkpoints | Multi-turn conversations reset; agent must restart from scratch |
| 🔴 HIGH | InMemoryApprovalStorage | Pending HITL approvals | Security-critical approvals vanish; users must re-approve |
| 🟡 MED | InMemoryThreadRepository | AG-UI conversation threads | Chat history disappears; users see empty conversation |
| 🟡 MED | InMemoryDialogSessionStorage | Guided dialog state | Multi-step guided dialogs reset to beginning |
| 🟡 MED | InMemoryAuditStorage | MCP security audit trail | Compliance gap; cannot trace tool usage history |
| 🟡 MED | Domain audit/routing/learning/versioning/devtools | Module-specific operational data | Audit decisions, routing rules, learning cases all lost |
| 🟢 LOW | InMemoryConversationMemoryStore | Deprecated conversation data | Minimal; deprecated module |
| 🟢 LOW | VectorStore fallback | N/A (stateless fallback) | Search quality degrades but no data loss |

---

## 6. Component-to-Storage Mapping

### 6.1 Complete Mapping Table

| Component | Module | Storage Backend | TTL | Layer | Risk |
|-----------|--------|----------------|-----|-------|------|
| `UnifiedMemoryManager` | integrations/memory | Redis + mem0/Qdrant | 30min / 7d / permanent | L1+L2+L3 | Low |
| `Mem0Client` | integrations/memory | Qdrant (local path) | Permanent | L3 | Low |
| `LLMCacheService` | infrastructure/cache | Redis | Configurable | L1 | Low |
| `SessionStore` | infrastructure/storage | Redis (ABC) | 24h | L1 | Low |
| `ConversationStateStore` | infrastructure/storage | Redis (ABC) | 24h | L1 | Low |
| `ExecutionStateStore` | infrastructure/storage | PostgreSQL (ABC) | Permanent | L2 | Low |
| `ApprovalStore` | infrastructure/storage | PostgreSQL (ABC) | Per-record | L2 | Low |
| `AuditStore` | infrastructure/storage | PostgreSQL (ABC) | Permanent | L2 | Low |
| `TaskStore` | infrastructure/storage | Auto-detected (ABC) | Permanent | L2 | Low |
| `SessionModel + MessageModel` | domain/sessions | PostgreSQL (ORM) | Permanent | L2 | Low |
| `SessionCache` | domain/sessions | Redis | TTL-based | L1 | Low |
| `SessionRecoveryManager` | domain/sessions | Redis | TTL-based | L1 | Low |
| `PostgresCheckpointStorage` | infrastructure/checkpoint | PostgreSQL | Permanent | L2 | Low |
| `RedisCheckpointCache` | infrastructure/checkpoint | Redis | 7d | L1 | Low |
| `RAGPipeline` | integrations/knowledge | Qdrant | Permanent | L3 | Low |
| `VectorStoreManager` | integrations/knowledge | Qdrant / InMemory fallback | Permanent | L3 | Medium |
| `InMemoryCheckpointStorage` | agent_framework, hybrid | Python dict | None | N/A | **HIGH** |
| `InMemoryApprovalStorage` | orchestration/hitl | Python dict | None | N/A | **HIGH** |
| `InMemoryThreadRepository` | ag_ui/thread | Python dict | None | N/A | **MEDIUM** |
| `InMemoryDialogSessionStorage` | orchestration/guided_dialog | Python dict | None | N/A | **MEDIUM** |
| `InMemoryAuditStorage` | mcp/security | Python dict | None | N/A | **MEDIUM** |
| `DecisionTracker` | integrations/audit | Python dict + optional Redis cache | None | N/A | **MEDIUM** |
| Domain InMemory (5 modules) | domain/audit,routing,learning,versioning,devtools | Python dict | None | N/A | **MEDIUM** |

### 6.2 Storage Backend Distribution

```
┌─────────────────────────────────────────────────────────────────────────────┐
│               儲存後端分佈統計                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PostgreSQL (永久)     ████████████████████  ~40%  (8 components)           │
│  Redis (TTL-based)     ██████████████████    ~35%  (7 components)           │
│  Qdrant (向量)         ████                  ~8%   (2 components)           │
│  InMemory (揮發!)      █████████             ~17%  (12 components)  ⚠      │
│                                                                             │
│  Production-Safe: 83% | Volatile Risk: 17%                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Migration Recommendations

### 7.1 Priority Migration Plan

| Priority | Component | Current | Target | Effort | Sprint Estimate |
|----------|-----------|---------|--------|--------|----------------|
| P0 🔴 | InMemoryCheckpointStorage | Python dict | Redis (via `create_agent_framework_checkpoint_storage()`) | Low — factory already exists | 1 Sprint |
| P0 🔴 | InMemoryApprovalStorage | Python dict | Redis (via `create_approval_storage()`) | Low — factory already exists | 1 Sprint |
| P1 🟡 | InMemoryThreadRepository | Python dict | Redis (via `create_thread_repository()`) | Low — factory already exists | 1 Sprint |
| P1 🟡 | InMemoryDialogSessionStorage | Python dict | Redis (via `create_dialog_session_storage()`) | Low — factory already exists | 1 Sprint |
| P1 🟡 | InMemoryAuditStorage | Python dict | Redis (via `create_audit_storage()`) | Low — factory already exists | 1 Sprint |
| P2 🟡 | Domain InMemory modules (5) | Python dicts | Redis or PostgreSQL | Medium — no factory yet | 2-3 Sprints |
| P3 | Session Memory L2 | Redis (longer TTL) | PostgreSQL (as designed) | Medium — requires schema | 2 Sprints |
| P4 | Dual backend interface | ABC + Protocol | Unified Protocol | High — breaking change | 3-4 Sprints |

### 7.2 Key Observation

Sprint 119-120 已建立 7 個領域特定工廠函式 (`storage_factories.py`), 為大部分 InMemory 元件提供了 Redis-backed 替代方案。**P0/P1 遷移的主要工作是將預設實例化從 InMemory 切換至對應工廠函式**, 程式碼改動量小但影響顯著。

### 7.3 Mem0 Async Issue

`Mem0Client` 中 `self._memory.add()`, `self._memory.search()`, `self._memory.get_all()` 為同步 mem0 SDK 呼叫, 在 `async` 方法中使用但未使用 `asyncio.to_thread()` 包裝。**建議**: 包裝為 `await asyncio.to_thread(self._memory.add, ...)` 以避免事件迴圈阻塞。

---

## 8. Architecture Summary

### 8.1 Strengths

1. **明確的三層分離**: L1 Working / L2 Session / L3 Long-Term 職責清晰
2. **降級容錯鏈**: 每一層都有 fallback 策略, 確保服務不中斷
3. **統一 Checkpoint 註冊表**: Sprint 120-121 的適配器模式成功整合 4 套歷史 Checkpoint 系統
4. **領域工廠已就緒**: Sprint 119 的 `storage_factories.py` 為 InMemory 遷移鋪好了道路
5. **RAG Pipeline 完整**: 從文件攝取到向量檢索到 LLM 回答生成的端到端流程

### 8.2 Weaknesses

1. **InMemory 元件佔 17%**: 12 個元件仍使用揮發性 Python dict 儲存, 其中 2 個為 HIGH 風險
2. **雙重後端介面**: Sprint 110 ABC 與 Sprint 119 Protocol 不相容, 增加維護成本
3. **Session Memory 未按設計實作**: L2 設計為 PostgreSQL, 但實際使用 Redis + longer TTL
4. **mem0 同步阻塞**: 長期記憶操作可能阻塞 asyncio 事件迴圈
5. **Checkpoint cleanup O(N)**: `cleanup_expired()` 逐一刪除, 大規模時效能問題

### 8.3 Overall Memory Architecture Health

```
┌─────────────────────────────────────────────────────────────────────────────┐
│               記憶體架構健康度評估                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Layer    Health    Notes                                                   │
│  ─────   ──────    ─────                                                   │
│  L1      ✅ 良好    Redis 穩定, LLM Cache 有效                              │
│  L2      ⚠ 注意    PostgreSQL 穩定但 Session Memory 未按設計實作             │
│  L3      ✅ 良好    mem0 + Qdrant 運作正常 (需修 async 問題)                 │
│  RAG     ✅ 良好    端到端管線完整, Qdrant 降級策略存在                       │
│  Checkpoint ✅ 良好  統一註冊表已建立, 4 adapters 運作中                      │
│  InMemory  🔴 風險  12 元件揮發性儲存, 2 HIGH / 5+ MEDIUM                   │
│                                                                             │
│  整體評分: B (良好, 但 InMemory 遷移為當務之急)                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

> **Document Version**: V9 R1
> **Cross-references**: `layer-09-integrations.md` Section 4-5, `layer-11-infrastructure.md` Sections 5-6, `layer-10-domain.md` Section 2-4, `mock-real-map.md` Section 2
> **Next Actions**: P0 InMemory migration (InMemoryCheckpointStorage + InMemoryApprovalStorage) should be prioritized in the next sprint cycle.
