# Dr. Data -- IPA Platform 資料架構分析

**Generated**: 2026-03-15
**Analyst**: Dr. Data (Data Architecture Specialist)
**Scope**: PostgreSQL + Redis + RabbitMQ + InMemory stores + mem0 memory system
**Source Files Analyzed**: 45+ infrastructure/domain/integration source files, 6 Alembic migrations, V8 issue registry (62 issues)

---

## Executive Summary

IPA Platform 的資料架構呈現一個**雙層斷裂**的特徵：核心 CRUD 層（PostgreSQL + SQLAlchemy）設計合理且結構完整，但平台其餘 80% 的狀態管理依賴 InMemory dict 或未整合的 Redis，導致**重啟即遺失所有非 DB 資料**。RabbitMQ 是完全的空殼。整體評估如下：

| 維度 | 評分 | 說明 |
|------|------|------|
| **核心資料模型** | B+ | 7 張 ORM 表設計合理，UUID PK、JSONB、時間戳 mixin |
| **ORM / 查詢品質** | B- | 通用 Repository 模式良好，但有 N+1 風險和 selectin 濫用 |
| **快取架構** | C+ | LLM 快取設計完整，但 7 個 domain storage consumer 各自為政 |
| **訊息佇列** | F | RabbitMQ 設定存在但零實作，1 行 `__init__.py` |
| **Schema 演進** | C | Alembic 存在但只有 6 個 migration，且為增量修補非完整 baseline |
| **資料一致性** | C- | 無分散式交易，InMemory 和 DB 之間零一致性保證 |
| **mem0 整合** | B- | 三層記憶架構設計良好，但 Session 層落回 Redis 而非 PostgreSQL |

**最嚴重發現**：V8 Issue Registry 中 #1 號問題 (C-01) -- **20+ 個模組使用 InMemory-only 存儲**，重啟後全部遺失。這不是個別問題，而是系統性架構缺陷。

---

## 1. 資料模型分析

### 1.1 SQLAlchemy Models 清單

| Table | Model Class | File | PK | 主要欄位 | JSONB 欄位數 |
|-------|-------------|------|-----|---------|-------------|
| `users` | `User` | `models/user.py` | UUID | email, hashed_password, role, is_active | 0 |
| `agents` | `Agent` | `models/agent.py` | UUID | name (unique), instructions, status, version | 2 (tools, model_config) |
| `workflows` | `Workflow` | `models/workflow.py` | UUID | name, trigger_type, graph_definition, status | 3 (trigger_config, graph_definition) |
| `executions` | `Execution` | `models/execution.py` | UUID | workflow_id (FK), status, llm_calls/tokens/cost | 2 (result, input_data) |
| `checkpoints` | `Checkpoint` | `models/checkpoint.py` | UUID | execution_id (FK), status, step, checkpoint_type | 3 (state, payload, response) |
| `sessions` | `SessionModel` | `models/session.py` | UUID (mixin) | user_id (FK), agent_id, status, expires_at | 2 (config, session_metadata) |
| `messages` | `MessageModel` | `models/session.py` | UUID (mixin) | session_id (FK), role, content, parent_id (self-FK) | 3 (attachments_json, tool_calls_json, message_metadata) |
| `attachments` | `AttachmentModel` | `models/session.py` | UUID (mixin) | session_id (FK), message_id (FK), filename, storage_path | 1 (attachment_metadata) |
| `audit_logs` | `AuditLog` | `models/audit.py` | UUID | action, resource_type, resource_id, actor_id (FK) | 3 (old_value, new_value, extra_data) |

**總計: 9 張表, 19 個 JSONB 欄位**

### 1.2 正規化評估

**整體正規化程度: 2NF-3NF 混合**

優點:
- 核心實體（User, Agent, Workflow, Execution）正確分離為獨立表
- FK 關聯使用 `ondelete="CASCADE"` 和 `ondelete="SET NULL"` 語意正確
- UUID PK 避免了序列衝突問題

問題:
- **JSONB 過度使用 (19 欄位)**: `Agent.tools`, `Agent.model_config`, `Workflow.graph_definition` 等將結構化資料塞入 JSONB，犧牲了查詢能力和型別安全。例如 `graph_definition` 包含 nodes/edges 結構，無法被 SQL 高效查詢或加索引
- **Agent 與 Session 無直接 FK**: `SessionModel.agent_id` 是 UUID 欄位但**沒有 FK 約束**到 `agents` 表，意味著 referential integrity 不被 DB 保證
- **AuditLog 與 User 有 FK 但沒有 relationship**: `actor_id` 有 FK 但 model 中沒有定義 `relationship()`，無法做 eager load

### 1.3 關聯設計品質

```
User ─┬── 1:N ──> Workflow    (created_by FK, SET NULL)
      ├── 1:N ──> Execution   (triggered_by FK, SET NULL)
      ├── 1:N ──> SessionModel (user_id FK, SET NULL)
      └── 1:N ──> AuditLog    (actor_id FK, SET NULL, no relationship)

Workflow ── 1:N ──> Execution  (workflow_id FK, CASCADE)
Execution ── 1:N ──> Checkpoint (execution_id FK, CASCADE)
SessionModel ─┬── 1:N ──> MessageModel  (session_id FK, CASCADE, cascade="all, delete-orphan")
              └── 1:N ──> AttachmentModel (session_id FK, CASCADE, cascade="all, delete-orphan")
MessageModel ── self-referential ──> MessageModel (parent_id FK, SET NULL)
```

**缺失的關聯:**
1. `Agent` 是孤立表 -- 沒有任何其他表的 FK 指向它（`SessionModel.agent_id` 無 FK 約束）
2. `Workflow.graph_definition` 中 nodes 引用 agent_id 但以 JSONB 存儲，DB 層無法驗證

### 1.4 索引策略

| Table | 明確索引 | 評估 |
|-------|---------|------|
| `users` | email (unique) | 足夠 |
| `agents` | name (unique), category, status | 良好 |
| `workflows` | name, status | 缺少 `created_by` 索引 |
| `executions` | workflow_id, status | 良好 |
| `checkpoints` | execution_id, status | 缺少 `responded_by` 索引 |
| `sessions` | user_id, guest_user_id, status, expires_at, 複合 (user_id+status), 複合 (guest_user_id) | 優秀 -- 有條件索引 |
| `messages` | session_id, 複合 (session_id+created_at) | 良好 |
| `attachments` | session_id | 缺少 message_id 索引 |
| `audit_logs` | action, resource_type, resource_id, actor_id, timestamp | 優秀 |

**Session 表有最完整的索引策略**（包含 partial index on `expires_at` WHERE status != 'ended'），反映出這是使用最頻繁的表。

---

## 2. ORM 與查詢分析

### 2.1 查詢模式

**Repository Pattern (BaseRepository):**
- 正確使用 `select()` 和 `func.count()` 的現代 SQLAlchemy 2.0 語法
- 分頁採用 `offset/limit` 而非 keyset pagination -- 大表效能不佳
- `exists()` 方法先 `get()` 再判斷非 None，應改用 `EXISTS` 子查詢

**Async Session Management:**
```python
# session.py -- 關鍵設定
expire_on_commit=False  # 正確：避免 commit 後 lazy load 問題
autoflush=False         # 正確：手動控制 flush 時機
pool_size=5, max_overflow=10  # 總計最多 15 連線
pool_pre_ping=True     # 正確：連線健康檢查
```

自動 commit/rollback 在 `get_session()` 中實作：
```python
async with session_factory() as session:
    try:
        yield session
        await session.commit()  # 自動 commit
    except Exception:
        await session.rollback()  # 自動 rollback
        raise
```

### 2.2 N+1 風險

| 關聯 | Loading Strategy | 風險等級 |
|------|-----------------|---------|
| `Workflow.executions` | `lazy="selectin"` | **HIGH** -- 載入 Workflow 時自動載入所有 Execution |
| `Execution.checkpoints` | `lazy="selectin"` | **HIGH** -- 載入 Execution 時自動載入所有 Checkpoint |
| `SessionModel.user` | `lazy="selectin"` | MEDIUM -- 每個 Session 觸發一次 User 查詢 |
| `User.workflows` | `lazy="noload"` | SAFE -- 已明確停用 |
| `User.executions` | `lazy="noload"` | SAFE -- 已明確停用 |
| `User.sessions` | `lazy="noload"` | SAFE -- 已明確停用 |
| `SessionModel.messages` | default (lazy) | SAFE -- 需要時才載入 |

**關鍵問題**: `Workflow.executions` 使用 `selectin`，這意味著每次載入 Workflow 列表時，會為每個 Workflow 自動查詢其所有 Execution 記錄。在有大量 Execution 的情況下，這會造成嚴重的效能問題。

**V8 Issue M-03 驗證**: Dashboard chart endpoint 中確實存在 N+1 模式 -- 3 queries/day x 7 days = 21 queries。

### 2.3 Transaction 管理

- **單一 session-per-request**: FastAPI dependency `get_session()` 確保每個請求一個 session，自動 commit/rollback
- **Context manager**: `DatabaseSession()` 提供非 FastAPI 場景的 transaction 支援
- **無巢狀交易**: 沒有使用 `SAVEPOINT` 或 `begin_nested()` 的地方
- **無分散式交易**: PostgreSQL 和 Redis 操作之間沒有任何 2PC 或 saga pattern

---

## 3. 快取架構分析

### 3.1 Redis 使用場景

**集中式 Redis 客戶端** (`infrastructure/redis_client.py`, Sprint 119):
- 單一 ConnectionPool (max_connections=20)
- 自動重試 on timeout
- Health check endpoint
- Graceful shutdown

**Redis 使用者矩陣 (7 個 domain-specific storage consumers):**

| Consumer | Factory Function | Redis 實作 | InMemory Fallback | Sprint |
|----------|-----------------|-----------|-------------------|--------|
| ApprovalStorage (HITL) | `create_approval_storage()` | `RedisApprovalStorage` | `InMemoryApprovalStorage` | 119 |
| DialogSessionStorage | `create_dialog_session_storage()` | `RedisDialogSessionStorage` | `InMemoryDialogSessionStorage` | 119 |
| AG-UI ThreadRepository | `create_thread_repository()` | `RedisThreadRepository` | `InMemoryThreadRepository` | 119 |
| AG-UI Cache | `create_ag_ui_cache()` | `RedisCacheBackend` | `InMemoryCache` | 119 |
| ConversationMemoryStore | `create_conversation_memory_store()` | `RedisConversationMemoryStore` | `InMemoryConversationMemoryStore` | 119 |
| SwitchCheckpointStorage | `create_switch_checkpoint_storage()` | `RedisSwitchCheckpointStorage` | `InMemoryCheckpointStorage` | 120 |
| AuditStorage (MCP) | `create_audit_storage()` | `RedisAuditStorage` | `InMemoryAuditStorage` | 120 |
| AgentFrameworkCheckpoint | `create_agent_framework_checkpoint_storage()` | `AFRedisCheckpointStorage` | `AFInMemoryCheckpointStorage` | 120 |

**LLM Cache** (`infrastructure/cache/llm_cache.py`):
- Key pattern: `llm_cache:{SHA256(model+prompt+params)}`
- Default TTL: 3600s (1 hour)
- 包含 hit/miss 統計和 cache warming 功能
- `CachedAgentService` wrapper 自動快取 Agent 執行結果

### 3.2 快取策略評估

**Cache-Aside (Lazy Loading)** -- 所有 Redis 使用者都遵循此模式:
1. 先查 Redis
2. Miss 則查 DB/執行運算
3. 回寫 Redis

**環境感知 Factory Pattern** (Sprint 119 最佳設計之一):
```
auto + production  -> Redis required, fail fast
auto + development -> Redis preferred, InMemory fallback + WARNING
auto + testing     -> InMemory directly
memory (explicit)  -> InMemory in all environments
redis (explicit)   -> Redis required in all environments
```

**問題:**
1. **無 Cache Invalidation 策略**: LLM Cache 依賴 TTL 過期，沒有主動 invalidate 機制（例如 Agent 指令更新後，舊快取回應仍被返回）
2. **InMemory Fallback 是隱性的**: 開發環境中 Redis 不可用時自動切換到 InMemory，但只有 log warning，API 消費者無法得知當前使用的是持久化還是揮發存儲
3. **多 Consumer 共用一個 ConnectionPool**: 所有 7 個 storage consumer + LLM Cache 共用 max_connections=20 的連線池，高併發時可能不足
4. **SCAN 操作用於統計**: `get_stats()` 使用 `SCAN` 遍歷所有 key 計數 -- O(n) 複雜度，key 多時阻塞

### 3.3 快取一致性

**一致性等級: Eventually Consistent (但沒有收斂保證)**

- PostgreSQL 和 Redis 之間沒有任何同步機制
- 如果 Redis 寫入成功但 DB commit 失敗（或反之），資料不一致
- 沒有 CDC (Change Data Capture) 或 outbox pattern
- InMemory fallback 資料在重啟後完全遺失，但 DB 資料存在 -- 產生 phantom state

---

## 4. 訊息佇列分析

### 4.1 RabbitMQ 整合狀況

**結論: RabbitMQ 是 100% 空殼，零實作。**

| 層面 | 狀態 | 證據 |
|------|------|------|
| Docker Compose | 有配置 | ports 5672/15672 |
| Settings (config.py) | 有配置 | `rabbitmq_host`, `rabbitmq_port`, `rabbitmq_user`, `rabbitmq_password`, `rabbitmq_url` property |
| Infrastructure 代碼 | **空** | `messaging/__init__.py` 只有一行: `# Messaging infrastructure` |
| Publisher/Consumer | **不存在** | Grep 搜索 `pika`/`publish`/`consume` 在 src/ 中零匹配 (排除不相關的 versioning publish 和 asyncio.Queue) |
| 任何使用方 | **不存在** | 沒有任何模組 import 或使用 messaging 層 |

**V8 Issue Registry 確認**: C-06 列為 CRITICAL -- "Messaging infrastructure is a complete stub"。

### 4.2 事件驅動成熟度

雖然 RabbitMQ 未實作，平台使用了兩個替代的事件機制:

1. **SSE (Server-Sent Events)** -- AG-UI 和 Swarm 模組使用 `asyncio.Queue` 做 in-process 事件流:
   - `SwarmEventEmitter` 使用 `asyncio.Queue` 做非優先事件批量發送
   - 這是 HTTP 層的 push 機制，不是真正的訊息佇列

2. **SessionEventPublisher** -- 15 種事件類型但只是 in-process callback:
   - 沒有持久化
   - 沒有 replay 能力
   - 重啟後事件歷史遺失

**事件驅動成熟度: Level 1 (In-Process Only)**
- Level 1: In-process callbacks/queues (目前狀態)
- Level 2: Persistent message queue (計畫中但未實作)
- Level 3: Event sourcing with replay (未規劃)

---

## 5. Schema 演進

### 5.1 Migration 機制

**Alembic 已設置但使用有限:**

| Migration | Sprint | 內容 |
|-----------|--------|------|
| `001` | 72 | Session-User association: 加 user_id FK, guest_user_id |
| `002` | 72 | Fix user_id nullable and FK |
| `003` | 72 | Sync user model columns |
| `004` | 72 | Fix fullname nullable |
| `005` | 72 | Sync agent, checkpoint models |
| `006` | 72 | Sync execution model |

**全部 6 個 migration 都來自同一個 Sprint (72)，之後再無新 migration。**

### 5.2 Schema 版本管理

**問題:**
1. **無 Initial Baseline Migration**: 第一個 migration 不是 create table，而是 alter table。表的初始創建靠 `Base.metadata.create_all()` 或手動 SQL，不在 Alembic 控制下
2. **Alembic env.py 有 import 錯誤**: 嘗試 import `AgentModel` (不存在，應為 `Agent`)，靠 try/except 靜默吞掉
3. **Sprint 72 後沒有新 migration**: 意味著之後所有 model 變更（Session model 加的所有索引、Checkpoint 加的 step/checkpoint_type/state 欄位等）都不在版本控制中
4. **Migration 使用 runtime inspector 做冪等檢查**: 好做法，但掩蓋了 migration 順序問題

---

## 6. 資料流分析

### 6.1 寫入路徑

```
HTTP Request (FastAPI)
    |
    v
API Router (validates request via Pydantic schema)
    |
    v
Domain Service (business logic, state machine validation)
    |
    v
Repository (BaseRepository.create() -> session.add() -> flush() -> refresh())
    |
    v
Session auto-commit (get_session() context manager)
    |
    v
PostgreSQL (via asyncpg driver, connection pool)
```

**並行寫入 (例如 Session + Message + Redis Cache):**
```
API Router
    |
    +---> Repository.create(session)     ---> PostgreSQL
    |
    +---> Redis.setex(working_memory)    ---> Redis
    |         (NO transactional link)
    +---> SSE EventPublisher.emit()      ---> In-process Queue
```

**問題**: 上述三個寫入操作之間沒有原子性保證。如果 PostgreSQL commit 成功但 Redis 寫入失敗，狀態不一致。

### 6.2 讀取路徑

```
HTTP Request
    |
    v
API Router
    |
    +---> Redis Cache check (LLM Cache / Storage Backend)
    |         |
    |         +-- HIT  --> return cached response
    |         +-- MISS --> continue to DB
    |
    +---> Repository.get/list() ---> PostgreSQL
    |
    v
Response (to_dict() serialization via model method)
```

**注意**: 沒有 Read Replica 配置。所有讀寫都走同一個 PostgreSQL instance。

### 6.3 資料轉換層

**三層轉換:**

1. **Pydantic Schema (API 層)**: Request/Response validation
   - `backend/src/domain/agents/schemas.py`
   - `backend/src/domain/workflows/schemas.py`
   - `backend/src/domain/auth/schemas.py`

2. **Domain Model (Domain 層)**: Business logic dataclasses
   - `backend/src/domain/workflows/models.py` (WorkflowDefinition, WorkflowNode, WorkflowEdge)
   - `backend/src/domain/sessions/models.py` (Session, Message, ToolCall)
   - `backend/src/domain/orchestration/memory/models.py` (ConversationSession, ConversationTurn)

3. **SQLAlchemy ORM Model (Infrastructure 層)**: Database mapping
   - `backend/src/infrastructure/database/models/*.py`

**問題:**
- Domain Model 和 ORM Model 之間存在**重複定義**: 例如 `domain/sessions/models.py` 定義了 `Session` dataclass，而 `infrastructure/database/models/session.py` 定義了 `SessionModel` ORM class。兩者欄位不完全同步
- `to_dict()` 方法散佈在所有三層中，沒有統一的 serialization 策略
- `from_dict()` 類方法沒有驗證邏輯，可能產生不合法的 domain object

---

## 7. mem0 記憶系統分析

### 7.1 三層記憶架構

```
Layer 1: Working Memory
  Storage: Redis (key: memory:working:{user_id}:{memory_id})
  TTL: 1800s (30 min, configurable via WORKING_MEMORY_TTL)
  Fallback: Session Memory

Layer 2: Session Memory
  Storage: Redis (key: memory:session:{user_id}:{memory_id})
           (NOTE: 設計文檔說 PostgreSQL，實際實作用 Redis)
  TTL: 604800s (7 days, configurable via SESSION_MEMORY_TTL)
  Fallback: Long-term Memory (mem0)

Layer 3: Long-term Memory
  Storage: mem0 SDK -> Qdrant (local vector DB)
  TTL: Permanent
  Features: Semantic search, auto-extraction via LLM
```

### 7.2 設計 vs 實作差距

| 設計文檔聲明 | 實際實作 |
|-------------|---------|
| Session Memory 用 PostgreSQL | **實際用 Redis** (`_store_session_memory` 使用 `redis.setex`) |
| 三層分離 | Working 和 Session 都在 Redis，只有 key prefix 不同 |
| 搜索用 embedding similarity | Working/Session 搜索對每個 key **逐一計算 embedding** -- O(n) 且每次呼叫 API |
| mem0 做 memory extraction | 依賴 `from mem0 import Memory` -- 如果未安裝則完全無法初始化 |

### 7.3 可靠性評估

- **mem0 依賴**: 使用 `pip install mem0ai` 的 Memory SDK，如果未安裝只會在 `initialize()` 時 raise ImportError
- **Qdrant 本地模式**: 預設 `QDRANT_PATH=/data/mem0/qdrant`，使用本地文件存儲而非 Qdrant server
- **Embedding 效率**: `_search_working_memory()` 對每個 Redis key 的內容都呼叫 `embed_text()` -- 如果有 100 個 working memory，就是 100 次 embedding API call
- **Redis 不可用時**: 整個 Working + Session 層失效，只剩 Long-term 層可用

---

## 8. 架構改進建議

### 8.1 P0 -- 立即修復 (阻擋生產部署)

| # | 建議 | 對應 Issue | 預估工時 |
|---|------|-----------|---------|
| 1 | **實作 Redis-backed storage for all InMemory consumers** -- 已有 7 個 factory + protocol，但 9 個 API 模組和 6 個 domain 模組仍用裸 dict | C-01 | 5-8 sprints |
| 2 | **修復 SQL injection**: `integrations/agent_framework/` 中的 f-string table name interpolation | C-07 | 1 day |
| 3 | **移除 API key prefix exposure** in AG-UI bridge | C-08 | 1 hour |
| 4 | **加 FK 約束**: `SessionModel.agent_id` 應該有 FK 到 `agents.id` | -- | 1 migration |

### 8.2 P1 -- 短期改善 (1-2 Sprints)

| # | 建議 | 對應 Issue | 影響 |
|---|------|-----------|------|
| 5 | **建立 Alembic baseline migration**: 用 `alembic revision --autogenerate` 建立完整的 initial schema，確保所有 model 變更都在版本控制中 | -- | 降低部署風險 |
| 6 | **修復 N+1 查詢**: 將 `Workflow.executions` 從 `selectin` 改為 `lazy` 或 `noload`，需要時用 `options(selectinload(...))` 明確載入 | M-03 | 查詢效能提升 10-50x |
| 7 | **實作 RabbitMQ 或替代方案**: 決定是使用 RabbitMQ (已有 Docker) 還是用 Redis Pub/Sub 作為輕量替代 | C-06 | 啟用事件驅動架構 |
| 8 | **Redis ConnectionPool 調整**: 20 個連線分配給 8+ consumers，建議提升到 50 或為不同 consumer 使用獨立 pool | -- | 高併發穩定性 |
| 9 | **Offset pagination 改為 Keyset pagination**: `BaseRepository.list()` 的 `offset/limit` 在大表上效能差 | -- | 大資料集效能 |

### 8.3 P2 -- 中期架構演進 (3-5 Sprints)

| # | 建議 | 說明 |
|---|------|------|
| 10 | **統一 Serialization 層**: 用 Pydantic V2 的 `model_validator` 取代散佈在三層中的 `to_dict()/from_dict()` | 減少 bug、統一驗證 |
| 11 | **實作 Outbox Pattern**: DB 和 Redis 之間的寫入要用 outbox table + background worker 確保最終一致性 | 資料一致性保證 |
| 12 | **正規化 JSONB**: 將 `Agent.tools` 抽出為 `agent_tools` 關聯表，`Workflow.graph_definition` 抽出為 `workflow_nodes` + `workflow_edges` 表 | 查詢能力、referential integrity |
| 13 | **mem0 Session Memory 改用 PostgreSQL**: 按設計文檔將 Session Memory 從 Redis 移到 PostgreSQL，用 pgvector 做 similarity search | 持久性、設計一致性 |
| 14 | **datetime.utcnow() 全面替換**: 使用 `datetime.now(timezone.utc)` 取代已棄用的 `datetime.utcnow()` | M-01, Python 3.12+ 相容性 |

### 8.4 P3 -- 長期策略 (10x 成長規劃)

| # | 建議 | 影響 |
|---|------|------|
| 15 | **Read Replica**: 加入 PostgreSQL 讀取副本，將 dashboard / audit log 查詢導向 replica | 讀寫分離，查詢不影響寫入 |
| 16 | **Redis Cluster**: 從單節點遷移到 Redis Cluster，支持 horizontal scaling | 快取層水平擴展 |
| 17 | **Event Sourcing for Executions**: Execution 和 Checkpoint 改用 event sourcing，支持完整的 replay 和 time-travel debugging | 可審計性、可靠性 |
| 18 | **CQRS for Dashboard**: 分離讀寫模型，Dashboard 從 materialized view 或 read-optimized store 讀取 | Dashboard 效能 |

---

## Appendix A: InMemory Storage 散佈圖

以下模組使用 in-memory dict/list 作為主要存儲，**重啟後資料遺失**:

| 層 | 模組 | 存儲方式 | 有 Redis/DB 替代? |
|----|------|---------|-----------------|
| API | ag_ui (ApprovalStorage) | dict | 有 (Sprint 119 factory) |
| API | ag_ui (ChatSession) | dict | 有 (Sprint 119 factory) |
| API | ag_ui (SharedState) | dict | 無 |
| API | ag_ui (PredictiveState) | dict | 無 |
| API | checkpoints | dict | 無 |
| API | autonomous | dict + fake data | 無 (100% mock) |
| API | correlation | fake data | 無 (100% mock) |
| API | patrol | fake data | 無 (100% mock) |
| API | rootcause | fake data | 無 (100% mock) |
| Domain | learning | dict | 無 |
| Domain | templates | dict | 無 |
| Domain | routing | dict | 無 |
| Domain | triggers | dict | 無 |
| Domain | versioning | dict | 無 |
| Domain | prompts | dict | 無 |
| Integration | orchestration metrics | dict | 無 |
| Integration | audit decisions | dict | 無 |
| Integration | a2a registry | dict | 無 |
| Integration | rootcause CaseRepository | dict + seed | 無 (interface only) |
| Integration | correlation | dict | 無 |

**統計: 20 個模組中只有 3 個有 Redis 替代方案已建立。**

## Appendix B: 資料流完整性矩陣

| 操作 | PostgreSQL | Redis | InMemory | RabbitMQ | 一致性保證 |
|------|-----------|-------|----------|----------|-----------|
| User CRUD | Write/Read | -- | -- | -- | Strong (single DB) |
| Agent CRUD | Write/Read | -- | -- | -- | Strong |
| Workflow CRUD | Write/Read | -- | -- | -- | Strong |
| Execution tracking | Write/Read | -- | -- | -- | Strong |
| Session management | Write/Read | Cache (selectin) | -- | -- | Eventual (no sync) |
| Chat messages | Write/Read | -- | -- | -- | Strong |
| LLM response cache | -- | Write/Read | -- | -- | TTL-based |
| HITL Approvals | -- | Write/Read | Fallback | -- | Redis or Lost |
| Dialog sessions | -- | Write/Read | Fallback | -- | Redis or Lost |
| AG-UI threads | -- | Write/Read | Fallback | -- | Redis or Lost |
| Conversation memory | -- | Write/Read | Fallback | -- | Redis or Lost |
| Working memory (mem0) | -- | Write/Read | -- | -- | TTL-based |
| Long-term memory (mem0) | -- | -- | -- | -- | Qdrant (eventual) |
| Audit logs (DB) | Write | -- | -- | -- | Strong |
| Audit logs (MCP) | -- | -- | In-memory only | -- | **LOST on restart** |
| Event streaming | -- | -- | asyncio.Queue | -- | **LOST on restart** |
| Workflow execution events | -- | -- | -- | **NOT IMPLEMENTED** | N/A |
