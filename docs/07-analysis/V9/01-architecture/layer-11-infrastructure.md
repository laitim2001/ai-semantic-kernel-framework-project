# Layer 11: Infrastructure + Core

> V9 Deep Analysis | 2026-03-29 | Based on full source reading of all Python files in `infrastructure/`, `core/`, and `middleware/`

---

## 1. Identity

**Layer 11** is the foundation layer of the IPA Platform, encompassing three directories:

| Directory | File Count | Responsibility |
|-----------|-----------|----------------|
| `backend/src/infrastructure/` | 54 files (~9,901 LOC) | Database, Storage, Cache, Checkpoint, Workers, Messaging, Distributed Lock |
| `backend/src/core/` | 39 files (~11,945 LOC) | Config, Security, Performance, Sandbox, Observability, Logging, Auth |
| `backend/src/middleware/` | 2 files (~107 LOC) | Rate Limiting |

**Total: 95 Python files, ~21,953 LOC** forming the platform's persistence, security, and operational backbone.

> **R4 LOC Correction**: V9 `00-stats.md` originally claimed ~5,600 LOC for Layer 11. Actual verified count via ripgrep is **21,953 LOC** (3.9x higher). Infrastructure alone is 9,901 LOC (not ~4,000), Core is 11,945 LOC (not ~1,500). Fixed in R4 round.

### 基礎設施層架構總覽

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              Layer 11: Infrastructure + Core (95 files, 21,953 LOC)         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────── infrastructure/ (54 files, 9,901 LOC) ─────────────┐      │
│  │                                                                   │      │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │      │
│  │  │ database/    │  │  storage/    │  │ checkpoint/  │           │      │
│  │  │ (18 files)   │  │ (18 files)   │  │ (8 files)    │           │      │
│  │  │              │  │              │  │              │           │      │
│  │  │ AsyncEngine  │  │ S3 + Local   │  │ PG + Redis   │           │      │
│  │  │ SQLAlchemy   │  │ File Storage │  │ + InMemory   │           │      │
│  │  │ 9 ORM Models │  │ Sandbox FS   │  │ CachedStore  │           │      │
│  │  │ 6 Repos      │  │              │  │              │           │      │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │      │
│  │         │                 │                  │                    │      │
│  │         ↓                 ↓                  ↓                    │      │
│  │  ┌──────────────────────────────────────────────────────┐       │      │
│  │  │              PostgreSQL 16 + Redis 7                  │       │      │
│  │  └──────────────────────────────────────────────────────┘       │      │
│  │                                                                   │      │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │      │
│  │  │ cache/   │  │messaging/│  │dist_lock/ │  │  workers/ │        │      │
│  │  │LLM Cache │  │ STUB ⚠   │  │ Metrics  │  │ ARQ Queue │        │      │
│  │  │(Redis)   │  │ (1 line) │  │          │  │ (Redis)   │        │      │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │      │
│  └───────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│  ┌────────────────── core/ (39 files, 11,945 LOC) ──────────────────┐      │
│  │                                                                   │      │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │      │
│  │  │  security/   │  │ performance/ │  │  sandbox/    │           │      │
│  │  │  (7 files)   │  │ (11 files)   │  │  (7 files)   │           │      │
│  │  │              │  │              │  │              │           │      │
│  │  │  JWT Auth    │  │  Profiler    │  │  Code Exec   │           │      │
│  │  │  RBAC        │  │  Metrics     │  │  Resource    │           │      │
│  │  │  Password    │  │  Monitor     │  │  Isolation   │           │      │
│  │  └──────────────┘  └──────────────┘  └──────────────┘           │      │
│  │                                                                   │      │
│  │  ┌──────────────┐  ┌──────────────┐                              │      │
│  │  │  config.py   │  │ server_config│  Settings (Pydantic)         │      │
│  │  │  constants   │  │    .py       │  ServerConfig (Uvicorn)      │      │
│  │  └──────────────┘  └──────────────┘                              │      │
│  └───────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│  ┌──── middleware/ (2 files, 107 LOC) ──────────────────────────────┐      │
│  │  Rate Limiting middleware                                         │      │
│  └───────────────────────────────────────────────────────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 資料庫連接池與快取分層

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              PostgreSQL 連接池 + Redis 快取分層                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Application Code (Domain / API)                                            │
│       │                                                                     │
│       ↓  get_session() (DI)                                                │
│  ┌──────────────────────────────────────────────────────┐                  │
│  │  async_sessionmaker                                   │                  │
│  │  └→ AsyncEngine (create_async_engine)                 │                  │
│  │      ├─ pool_size: 5 (default)                        │                  │
│  │      ├─ max_overflow: 10                              │                  │
│  │      ├─ (pool_recycle: not set, relies on pool_pre_ping)│                  │
│  │      └─ pool_pre_ping: True (連接健康檢查)            │                  │
│  └───────────────────────────┬───────────────────────────┘                  │
│                              ↓                                              │
│  ┌──────────────────────────────────────────────────────┐                  │
│  │              PostgreSQL 16 Database                    │                  │
│  └──────────────────────────────────────────────────────┘                  │
│                                                                             │
│  ┌──── Redis 快取分層 ──────────────────────────────────┐                  │
│  │                                                       │                  │
│  │  L1: Working Memory (TTL 30min)                       │                  │
│  │  ├─ Session 活躍資料                                  │                  │
│  │  ├─ LLM 回應快取                                     │                  │
│  │  └─ Dialog Session 狀態                               │                  │
│  │       │ 過期                                          │                  │
│  │       ↓                                               │                  │
│  │  L2: Session Cache (TTL 7d)                           │                  │
│  │  ├─ Checkpoint 快取 (RedisCheckpointCache)            │                  │
│  │  ├─ Thread 對話快取                                   │                  │
│  │  └─ Classification Cache                              │                  │
│  │       │ 過期                                          │                  │
│  │       ↓                                               │                  │
│  │  L3: Persistent (PostgreSQL)                          │                  │
│  │  ├─ PostgresCheckpointStorage                         │                  │
│  │  ├─ SessionModel + MessageModel                       │                  │
│  │  └─ 永久保存 (不過期)                                 │                  │
│  │                                                       │                  │
│  └───────────────────────────────────────────────────────┘                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. File Inventory

### 2.1 infrastructure/ (54 files)

```
infrastructure/
├── __init__.py
├── redis_client.py                          # Centralized Redis client factory (Sprint 119)
│
├── database/                                # PostgreSQL via SQLAlchemy async (18 files)
│   ├── __init__.py
│   ├── session.py                           # AsyncEngine + async_sessionmaker + get_session DI
│   ├── models/                              # 9 files (base + 8 model files = 9 ORM classes)
│   │   ├── __init__.py
│   │   ├── base.py                          # Base, TimestampMixin, UUIDMixin
│   │   ├── user.py                          # User (Sprint 1 + Sprint 72)
│   │   ├── agent.py                         # Agent (Sprint 1)
│   │   ├── workflow.py                      # Workflow (Sprint 1)
│   │   ├── execution.py                     # Execution (Sprint 1)
│   │   ├── checkpoint.py                    # Checkpoint (Sprint 1)
│   │   ├── session.py                       # SessionModel + MessageModel + AttachmentModel (Sprint 72)
│   │   └── audit.py                         # AuditLog (Sprint 1)
│   └── repositories/                        # 7 files (base + 6 repos)
│       ├── __init__.py
│       ├── base.py                          # BaseRepository[ModelT] generic async CRUD
│       ├── agent.py                         # AgentRepository
│       ├── workflow.py                      # WorkflowRepository
│       ├── execution.py                     # ExecutionRepository
│       ├── checkpoint.py                    # CheckpointRepository
│       └── user.py                          # UserRepository (Sprint 70)
│
├── cache/                                   # Redis LLM caching (2 files)
│   ├── __init__.py
│   └── llm_cache.py                         # LLMCacheService + CachedAgentService (Sprint 2)
│
├── messaging/                               # STUB (1 file)
│   └── __init__.py                          # "# Messaging infrastructure" (1 line)
│
├── storage/                                 # Key-value storage layer (18 files incl. backends/)
│   ├── __init__.py
│   ├── protocol.py                          # StorageBackend Protocol (Sprint 119) -- TTL=int
│   ├── redis_backend.py                     # RedisStorageBackend (Sprint 119) -- implements Protocol
│   ├── memory_backend.py                    # InMemoryStorageBackend (Sprint 119) -- implements Protocol
│   ├── storage_factories.py                 # 8 domain-specific factories (Sprint 119-120)
│   ├── backends/                            # Sprint 110 ABC-based backends (6 files)
│   │   ├── __init__.py
│   │   ├── base.py                          # StorageBackendABC (Sprint 110) -- TTL=timedelta
│   │   ├── memory.py                        # InMemoryBackend (Sprint 110)
│   │   ├── redis_backend.py                 # RedisBackend (Sprint 110)
│   │   ├── postgres_backend.py              # PostgresBackend (Sprint 110) -- own asyncpg pool
│   │   └── factory.py                       # StorageFactory (Sprint 110)
│   ├── session_store.py                     # SessionStore (Sprint 110)
│   ├── conversation_state.py                # ConversationStateStore (Sprint 115) -- L1 layer
│   ├── execution_state.py                   # ExecutionStateStore (Sprint 115) -- L3 layer
│   ├── approval_store.py                    # ApprovalStore (Sprint 110)
│   ├── audit_store.py                       # AuditStore (Sprint 110)
│   └── task_store.py                        # TaskStore (Sprint 113)
│
├── checkpoint/                              # Unified checkpoint system (8 files incl. adapters/)
│   ├── __init__.py
│   ├── protocol.py                          # CheckpointEntry + CheckpointProvider Protocol (Sprint 120)
│   ├── unified_registry.py                  # UnifiedCheckpointRegistry (Sprint 120)
│   └── adapters/                            # 5 files (init + 4 adapters)
│       ├── __init__.py
│       ├── hybrid_adapter.py                # HybridCheckpointAdapter (Sprint 120)
│       ├── domain_adapter.py                # DomainCheckpointAdapter (Sprint 121)
│       ├── agent_framework_adapter.py       # AgentFrameworkCheckpointAdapter (Sprint 121)
│       └── session_recovery_adapter.py      # SessionRecoveryCheckpointAdapter (Sprint 121)
│
├── distributed_lock/                        # Redis-based distributed locking (2 files)
│   ├── __init__.py
│   └── redis_lock.py                        # RedisDistributedLock + InMemoryLock (Sprint 119)
│
└── workers/                                 # Background jobs (3 files)
    ├── __init__.py
    ├── arq_client.py                        # ARQClient for job submission (Sprint 136)
    └── task_functions.py                    # execute_workflow_task + execute_swarm_task (Sprint 136)
```

### 2.2 core/ (39 files)

```
core/
├── __init__.py
├── config.py                                # Settings (pydantic BaseSettings) ~30 fields
├── auth.py                                  # require_auth / require_auth_optional (Sprint 111)
├── factories.py                             # (utility factories)
├── server_config.py                         # (server configuration)
├── sandbox_config.py                        # (sandbox configuration)
│
├── security/                                # 7 files
│   ├── __init__.py
│   ├── jwt.py                               # JWT create/decode (HS256) (Sprint 70)
│   ├── password.py                          # bcrypt hash/verify via passlib (Sprint 70)
│   ├── rbac.py                              # RBACManager 3 roles (Sprint 112)
│   ├── prompt_guard.py                      # PromptGuard 3-layer (Sprint 109)
│   ├── tool_gateway.py                      # ToolSecurityGateway 4-layer (Sprint 109)
│   └── audit_report.py                      # SecurityAuditReport OWASP generator
│
├── performance/                             # 11 files
│   ├── __init__.py
│   ├── circuit_breaker.py                   # CircuitBreaker CLOSED/OPEN/HALF_OPEN (Sprint 116)
│   ├── llm_pool.py                          # LLMCallPool priority semaphore (Sprint 109)
│   ├── benchmark.py                         # BenchmarkRunner sync/async (Sprint 12)
│   ├── cache_optimizer.py
│   ├── concurrent_optimizer.py
│   ├── db_optimizer.py
│   ├── metric_collector.py
│   ├── middleware.py
│   ├── optimizer.py
│   └── profiler.py
│
├── sandbox/                                 # 7 files
│   ├── __init__.py
│   ├── config.py
│   ├── adapter.py
│   ├── ipc.py
│   ├── orchestrator.py
│   ├── worker.py
│   └── worker_main.py
│
├── observability/                           # 4 files
│   ├── __init__.py
│   ├── setup.py                             # OpenTelemetry setup
│   ├── spans.py                             # Span helpers
│   └── metrics.py                           # Metric helpers
│
└── logging/                                 # 4 files
    ├── __init__.py
    ├── setup.py                             # Structured logging setup
    ├── middleware.py                         # Request logging middleware
    └── filters.py                           # Log filters
```

### 2.3 middleware/ (2 files)

```
middleware/
├── __init__.py
└── rate_limit.py                            # slowapi rate limiter (Sprint 111)
```

---

## 3. Database Models (Complete Column Schemas)

All models use `postgresql+asyncpg://` via SQLAlchemy 2.0+ mapped_column syntax. Primary keys are UUID v4.

### 3.1 Base Classes

| Mixin | Columns | Notes |
|-------|---------|-------|
| `Base` | (none) | `DeclarativeBase` with `type_annotation_map = {datetime: DateTime(timezone=True)}` |
| `TimestampMixin` | `created_at` TIMESTAMPTZ NOT NULL server_default=now(), `updated_at` TIMESTAMPTZ NOT NULL onupdate=now() | Used by User, Agent, Workflow, Execution, Checkpoint, SessionModel |
| `UUIDMixin` | `id` UUID PK default=uuid4 | Used by SessionModel, MessageModel, AttachmentModel |

### 3.2 User (table: `users`)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, default=uuid4 | |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL, INDEX | |
| `hashed_password` | VARCHAR(255) | NOT NULL | bcrypt |
| `full_name` | VARCHAR(255) | nullable | |
| `role` | VARCHAR(50) | NOT NULL, default="viewer" | admin/operator/viewer |
| `is_active` | BOOLEAN | NOT NULL, default=True | |
| `last_login` | TIMESTAMPTZ | nullable | |
| `created_at` | TIMESTAMPTZ | NOT NULL | TimestampMixin |
| `updated_at` | TIMESTAMPTZ | NOT NULL | TimestampMixin |

**Relationships**: `workflows` (1:M), `executions` (1:M), `sessions` (1:M, Sprint 72) -- all `lazy="noload"`

### 3.3 Agent (table: `agents`)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, default=uuid4 | |
| `name` | VARCHAR(255) | UNIQUE, NOT NULL, INDEX | |
| `description` | TEXT | nullable | |
| `instructions` | TEXT | NOT NULL | System prompt |
| `category` | VARCHAR(100) | nullable, INDEX | |
| `tools` | JSONB | NOT NULL, default=list | Tool names list (Mapped type annotation is `Dict[str, Any]` despite `default=list`) |
| `model_config` | JSONB | NOT NULL, default=dict | LLM config (temp, max_tokens) |
| `max_iterations` | INTEGER | NOT NULL, default=10 | |
| `status` | VARCHAR(50) | NOT NULL, default="active", INDEX | active/inactive/deprecated |
| `version` | INTEGER | NOT NULL, default=1 | |
| `created_at` | TIMESTAMPTZ | NOT NULL | TimestampMixin |
| `updated_at` | TIMESTAMPTZ | NOT NULL | TimestampMixin |

**Methods**: `to_dict()` serialization

### 3.4 Workflow (table: `workflows`)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, default=uuid4 | |
| `name` | VARCHAR(255) | NOT NULL, INDEX | |
| `description` | TEXT | nullable | |
| `trigger_type` | VARCHAR(50) | NOT NULL, default="manual" | manual/schedule/webhook/event |
| `trigger_config` | JSONB | NOT NULL, default=dict | |
| `graph_definition` | JSONB | NOT NULL | nodes + edges |
| `status` | VARCHAR(50) | NOT NULL, default="draft", INDEX | draft/active/inactive/archived |
| `version` | INTEGER | NOT NULL, default=1 | |
| `created_by` | UUID | FK users.id ON DELETE SET NULL, nullable | |
| `created_at` | TIMESTAMPTZ | NOT NULL | TimestampMixin |
| `updated_at` | TIMESTAMPTZ | NOT NULL | TimestampMixin |

**Relationships**: `created_by_user` (M:1 User), `executions` (1:M, lazy="selectin")

### 3.5 Execution (table: `executions`)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, default=uuid4 | |
| `workflow_id` | UUID | FK workflows.id ON DELETE CASCADE, NOT NULL, INDEX | |
| `status` | VARCHAR(50) | NOT NULL, default="pending", INDEX | pending/running/paused/completed/failed/cancelled |
| `started_at` | TIMESTAMPTZ | nullable | |
| `completed_at` | TIMESTAMPTZ | nullable | |
| `result` | JSONB | nullable | Output data |
| `error` | TEXT | nullable | |
| `llm_calls` | INTEGER | NOT NULL, default=0 | |
| `llm_tokens` | INTEGER | NOT NULL, default=0 | Input + output |
| `llm_cost` | NUMERIC(10,6) | NOT NULL, default=0.000000 | USD |
| `triggered_by` | UUID | FK users.id ON DELETE SET NULL, nullable | |
| `input_data` | JSONB | nullable | |
| `created_at` | TIMESTAMPTZ | NOT NULL | TimestampMixin |
| `updated_at` | TIMESTAMPTZ | NOT NULL | TimestampMixin |

**Relationships**: `workflow` (M:1), `triggered_by_user` (M:1), `checkpoints` (1:M, lazy="selectin")
**Properties**: `duration_seconds` computed

### 3.6 Checkpoint (table: `checkpoints`)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, default=uuid4 | |
| `execution_id` | UUID | FK executions.id ON DELETE CASCADE, NOT NULL, INDEX | |
| `node_id` | VARCHAR(255) | nullable | Workflow node ID |
| `step` | VARCHAR(255) | NOT NULL, default="0" | |
| `checkpoint_type` | VARCHAR(50) | NOT NULL, default="approval" | |
| `state` | JSONB | NOT NULL, default=dict | Current workflow state |
| `status` | VARCHAR(50) | nullable, default="pending", INDEX | pending/approved/rejected/expired |
| `payload` | JSONB | nullable, default=dict | Data for human review |
| `response` | JSONB | nullable | Human response |
| `responded_by` | UUID | FK users.id ON DELETE SET NULL, nullable | |
| `responded_at` | TIMESTAMPTZ | nullable | |
| `expires_at` | TIMESTAMPTZ | nullable | |
| `notes` | TEXT | nullable | |
| `created_at` | TIMESTAMPTZ | NOT NULL | TimestampMixin |
| `updated_at` | TIMESTAMPTZ | NOT NULL | TimestampMixin |

**Properties**: `is_expired` -- uses `datetime.utcnow()` (see Known Issues)

### 3.7 SessionModel (table: `sessions`)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK (UUIDMixin) | |
| `user_id` | UUID | FK users.id ON DELETE SET NULL, nullable, INDEX | Sprint 72: nullable for guest |
| `guest_user_id` | VARCHAR(100) | nullable, INDEX | guest-xxx format |
| `agent_id` | UUID | NOT NULL, INDEX | |
| `status` | VARCHAR(20) | NOT NULL, default="created", INDEX | |
| `config` | JSONB | NOT NULL, default=dict | |
| `expires_at` | TIMESTAMPTZ | nullable, INDEX | |
| `ended_at` | TIMESTAMPTZ | nullable | |
| `title` | VARCHAR(200) | nullable | |
| `session_metadata` | JSONB | NOT NULL, default=dict | Avoids SA reserved word |
| `created_at` | TIMESTAMPTZ | NOT NULL | TimestampMixin |
| `updated_at` | TIMESTAMPTZ | NOT NULL | TimestampMixin |

**Indexes**: `idx_sessions_user_status (user_id, status)`, `idx_sessions_guest_user (guest_user_id)`, `idx_sessions_expires (expires_at WHERE status != 'ended')`
**Relationships**: `messages` (1:M cascade), `attachments` (1:M cascade), `user` (M:1 lazy="selectin")

### 3.8 MessageModel (table: `messages`)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK (UUIDMixin) | |
| `session_id` | UUID | FK sessions.id ON DELETE CASCADE, NOT NULL, INDEX | |
| `role` | VARCHAR(20) | NOT NULL | user/assistant/system |
| `content` | TEXT | NOT NULL, default="" | |
| `parent_id` | UUID | FK messages.id ON DELETE SET NULL, nullable | Branch support |
| `attachments_json` | JSONB | NOT NULL, default=list | |
| `tool_calls_json` | JSONB | NOT NULL, default=list | |
| `created_at` | TIMESTAMPTZ | NOT NULL, default=utcnow | |
| `message_metadata` | JSONB | NOT NULL, default=dict | |

**Indexes**: `idx_messages_session_created (session_id, created_at)`
**Relationships**: `session` (M:1), `parent` (self-referential)

### 3.9 AttachmentModel (table: `attachments`)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK (UUIDMixin) | |
| `session_id` | UUID | FK sessions.id ON DELETE CASCADE, NOT NULL, INDEX | |
| `message_id` | UUID | FK messages.id ON DELETE SET NULL, nullable | |
| `filename` | VARCHAR(255) | NOT NULL | |
| `content_type` | VARCHAR(100) | NOT NULL | |
| `size` | INTEGER | NOT NULL | |
| `storage_path` | VARCHAR(500) | NOT NULL | |
| `attachment_type` | VARCHAR(50) | NOT NULL | |
| `uploaded_at` | TIMESTAMPTZ | NOT NULL, default=utcnow | |
| `attachment_metadata` | JSONB | NOT NULL, default=dict | |

### 3.10 AuditLog (table: `audit_logs`)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, default=uuid4 | |
| `action` | VARCHAR(50) | NOT NULL, INDEX | create/read/update/delete/execute |
| `resource_type` | VARCHAR(50) | NOT NULL, INDEX | agent/workflow/execution |
| `resource_id` | VARCHAR(255) | nullable, INDEX | |
| `actor_id` | UUID | FK users.id ON DELETE SET NULL, nullable, INDEX | |
| `actor_ip` | VARCHAR(45) | nullable | IPv6-ready |
| `old_value` | JSONB | nullable | Previous state |
| `new_value` | JSONB | nullable | New state |
| `extra_data` | JSONB | nullable | Additional context |
| `description` | TEXT | nullable | |
| `timestamp` | TIMESTAMPTZ | NOT NULL, server_default=now(), INDEX | Immutable (no TimestampMixin) |

---

## 4. Repository Layer

### 4.1 BaseRepository[ModelT] (Generic Async CRUD)

**Location**: `infrastructure/database/repositories/base.py`

All repositories use `AsyncSession` and the `flush()` + `refresh()` pattern (not `commit()` -- commits are handled by the session context manager in `session.py`).

| Method | Signature | Notes |
|--------|-----------|-------|
| `create` | `(**kwargs) -> ModelT` | flush + refresh |
| `get` | `(id: UUID) -> Optional[ModelT]` | session.get() |
| `get_by` | `(**kwargs) -> Optional[ModelT]` | filter_by, scalar_one_or_none |
| `list` | `(page, page_size, order_by, order_desc, **filters) -> Tuple[List[ModelT], int]` | Paginated with count subquery, default order by created_at desc |
| `update` | `(id, **kwargs) -> Optional[ModelT]` | get + setattr + flush |
| `delete` | `(id) -> bool` | get + session.delete + flush |
| `exists` | `(id) -> bool` | |
| `count` | `(**filters) -> int` | |

### 4.2 Concrete Repositories

| Repository | Model | Custom Methods |
|------------|-------|----------------|
| `AgentRepository` | Agent | `get_by_name`, `get_by_category`, `get_active`, `search` (ilike), `increment_version`, `activate`, `deactivate` |
| `WorkflowRepository` | Workflow | `get_by_trigger_type`, `get_active`, `get_by_creator`, `search`, `increment_version`, `activate`, `deactivate`, `archive`, `get_scheduled_workflows` |
| `ExecutionRepository` | Execution | `get_by_workflow`, `get_by_status`, `get_running`, `get_recent`, `start`, `complete`, `fail`, `cancel`, `pause`, `resume`, `update_stats`, `get_stats_by_workflow` (aggregation) |
| `CheckpointRepository` | Checkpoint | `get_pending`, `get_by_execution`, `list_by_execution`, `update_status`, `expire_old`, `get_by_node`, `get_stats` (count by status + avg response time) |
| `UserRepository` | User | `get_by_email`, `get_active_by_email`, `email_exists` |

**Note**: `UserRepository` is NOT exported from `repositories/__init__.py` -- it is a Sprint 70 addition that was not added to `__all__`.

### 4.3 Database Session Management

**Location**: `infrastructure/database/session.py`

- **Engine**: `create_async_engine` with `pool_pre_ping=True`, pool_size=5, max_overflow=10 (production); NullPool (testing)
- **Session Factory**: `async_sessionmaker` with `expire_on_commit=False`, `autoflush=False`
- **DI Pattern**: `get_session()` -- async generator yielding `AsyncSession`, auto-commit on success, rollback on exception
- **Standalone**: `DatabaseSession()` -- `@asynccontextmanager` for use outside FastAPI
- **Lifecycle**: `init_db()` at startup, `close_db()` at shutdown

---

## 5. Storage Layer (Dual Protocol Issue)

### 5.1 The Dual Protocol Problem

The storage layer has TWO incompatible interfaces created in different sprints:

| Aspect | Sprint 110 ABC (`backends/base.py`) | Sprint 119 Protocol (`protocol.py`) |
|--------|--------------------------------------|--------------------------------------|
| **Type** | `StorageBackendABC` (ABC) | `StorageBackend` (Protocol, @runtime_checkable) |
| **TTL type** | `Optional[timedelta]` | `Optional[int]` (seconds) |
| **Key listing** | `keys(pattern)` | `list_keys(pattern)` |
| **Clear** | `clear()` -> None | `clear_all()` -> int |
| **Set operations** | Not supported | `set_add`, `set_remove`, `set_members` |
| **Prefix** | Constructor param, internal | `@property prefix` required |
| **Batch ops** | `get_many`, `set_many`, `count` | Not defined |
| **Implementations** | `InMemoryBackend`, `RedisBackend`, `PostgresBackend` | `RedisStorageBackend`, `InMemoryStorageBackend` |
| **Used by** | 6 high-level stores (SessionStore, ConversationStateStore, ExecutionStateStore, ApprovalStore, AuditStore, TaskStore) | 8 domain-specific factories in `storage_factories.py` |

**Impact**: Code must choose which interface to use. The Sprint 110 ABC stores cannot be passed to Sprint 119 consumers and vice versa. The `storage_factories.py` file (Sprint 119-120) creates backends that implement the Protocol, while `backends/factory.py` (Sprint 110) creates ABC instances.

### 5.2 Sprint 110 ABC Backends

**InMemoryBackend** (`backends/memory.py`)
- Dict + monotonic expiry timestamps, asyncio.Lock
- Prefix-based namespace isolation
- Optimized batch get/set with single lock acquisition
- Lazy expiry cleanup on read

**RedisBackend** (`backends/redis_backend.py`)
- Uses `redis.asyncio` client
- Custom JSON encoder/decoder (datetime, Enum, UUID, dataclass, set, bytes, timedelta)
- SCAN-based key listing (production-safe, no KEYS command)
- Pipeline-based batch set for efficiency
- MGET-based batch get with fallback

**PostgresBackend** (`backends/postgres_backend.py`)
- **Uses its own asyncpg connection pool** (NOT the SQLAlchemy engine)
- Generic `kv_store` table with composite PK `(namespace, key)`
- JSONB value storage with TTL via `expires_at` column
- Lazy expiry cleanup on read
- UPSERT via `INSERT ... ON CONFLICT DO UPDATE`
- Separate `cleanup_expired()` maintenance method
- Pool: configurable min/max size (default 2/10)

**StorageFactory** (`backends/factory.py`)
- Auto-detection: REDIS_HOST -> Redis, DB_HOST -> Postgres, else InMemory
- Testing env -> always InMemory
- Production fallback -> RuntimeError (no silent degradation)
- Dev/staging fallback -> InMemory with warning

### 5.3 Sprint 119 Protocol Backends

**RedisStorageBackend** (`storage/redis_backend.py`)
- Implements `StorageBackend` Protocol with `ttl: Optional[int]`
- Same JSON encoder/decoder as Sprint 110 version
- Additional: `set_add`, `set_remove`, `set_members`, `get_ttl`, `expire`

**InMemoryStorageBackend** (`storage/memory_backend.py`)
- Implements `StorageBackend` Protocol
- Additional `_sets` dict for set operations

### 5.4 Domain-Specific Storage Factories

**Location**: `storage/storage_factories.py` (Sprint 119-120)

8 factory functions creating specific storage consumers with environment-aware backend selection:

| Factory | Consumer | Preferred Backend |
|---------|----------|-------------------|
| `create_approval_storage()` | HITL ApprovalStorage | Redis |
| `create_dialog_session_storage()` | GuidedDialog SessionStorage | Redis |
| `create_thread_repository()` | AG-UI ThreadRepository | Redis |
| `create_ag_ui_cache()` | AG-UI CacheProtocol | Redis |
| `create_conversation_memory_store()` | ConversationMemoryStore | Redis |
| `create_switch_checkpoint_storage()` | ModeSwitcher Checkpoint | Redis |
| `create_audit_storage()` | MCP AuditStorage | Redis |
| `create_agent_framework_checkpoint_storage()` | MAF MultiTurn Checkpoint | Redis |

All follow the pattern: production = Redis required (RuntimeError if unavailable), dev = Redis preferred with InMemory fallback, testing = InMemory directly.

### 5.5 High-Level Stores (Sprint 110-115)

All 6 stores use `StorageBackendABC` (Sprint 110 interface):

| Store | Key Prefix | TTL | Backend Preference |
|-------|-----------|-----|-------------------|
| `SessionStore` | `ipa:sessions:` | 24h | Redis (auto) |
| `ConversationStateStore` | `conv:` | 24h | Redis (auto) -- L1 ephemeral |
| `ExecutionStateStore` | `exec:` | None (permanent) | Postgres (auto) -- L3 durable |
| `ApprovalStore` | `ipa:approvals:` | Per-record expires_at | Postgres preferred |
| `AuditStore` | `ipa:audit:` | None (permanent) | Postgres preferred |
| `TaskStore` | `task:` | None | Auto |

---

## 6. Checkpoint Unification

### 6.1 The 4 Independent Checkpoint Systems

| System | Origin | Backend | Data Model |
|--------|--------|---------|------------|
| 1. **Domain Checkpoints** | Sprint 2 | PostgreSQL (CheckpointRepository) | UUID-based execution_id + node_id |
| 2. **Hybrid Checkpoint** | Sprint 57 (Phase 14) | Memory/Redis/Postgres/FS | HybridCheckpoint with CheckpointType enum |
| 3. **Agent Framework Checkpoint** | Sprint 24 | Redis/Postgres/FS | session_id-based key-value |
| 4. **Session Recovery** | Sprint 47 (Phase 11) | Cache (Redis) | SessionCheckpoint with TTL |

### 6.2 Unified Protocol (Sprint 120)

**CheckpointEntry** (dataclass):
- `checkpoint_id`, `provider_name`, `session_id`, `data` (Dict), `metadata` (Dict), `created_at`, `expires_at`
- `to_dict()`, `from_dict()`, `is_expired()`

**CheckpointProvider** (Protocol):
- `provider_name` property
- `save_checkpoint(checkpoint_id, data, metadata) -> str`
- `load_checkpoint(checkpoint_id) -> Optional[Dict]`
- `list_checkpoints(session_id, limit) -> List[CheckpointEntry]`
- `delete_checkpoint(checkpoint_id) -> bool`

### 6.3 UnifiedCheckpointRegistry (Sprint 120)

**Location**: `checkpoint/unified_registry.py`

Central coordinator with thread-safe provider management (asyncio.Lock):

| Operation | Description |
|-----------|-------------|
| `register_provider(provider)` | Register with name uniqueness check |
| `unregister_provider(name)` | Remove provider |
| `save(provider_name, checkpoint_id, data, metadata)` | Delegate to named provider |
| `load(provider_name, checkpoint_id)` | Delegate to named provider |
| `delete(provider_name, checkpoint_id)` | Delegate to named provider |
| `list_all(session_id, limit)` | Aggregate across ALL providers |
| `cleanup_expired(max_age_hours)` | Delete expired across all providers |
| `get_stats()` | Per-provider checkpoint counts |

### 6.4 Adapters (Sprint 120-121)

| Adapter | Wraps | Key Translation |
|---------|-------|-----------------|
| `HybridCheckpointAdapter` | `UnifiedCheckpointStorage` | Stores unified_data in HybridCheckpoint.metadata |
| `DomainCheckpointAdapter` | `DatabaseCheckpointStorage` | String checkpoint_id <-> UUID; extracts execution_id from data |
| `AgentFrameworkCheckpointAdapter` | `BaseCheckpointStorage` | checkpoint_id used as session_id; wraps data in unified_data envelope |
| `SessionRecoveryCheckpointAdapter` | `SessionRecoveryManager` | checkpoint_id = session_id; 1 checkpoint per session; no scan support |

---

## 7. Security Architecture

### 7.1 Authentication (JWT)

**Location**: `core/security/jwt.py` + `core/auth.py`

| Aspect | Detail |
|--------|--------|
| **Algorithm** | HS256 (symmetric) |
| **Library** | python-jose[cryptography] |
| **Access Token** | 60 min default (configurable via `jwt_access_token_expire_minutes`) |
| **Refresh Token** | 7 days, includes `"type": "refresh"` claim |
| **Claims** | `sub` (user_id), `role`, `exp`, `iat` |
| **Validation** | `decode_token()` raises `ValueError` on invalid/expired |
| **FastAPI DI** | `require_auth` (HTTPBearer, no DB lookup), `require_auth_optional` (nullable) |

**Password Hashing** (`core/security/password.py`):
- passlib CryptContext with bcrypt, `deprecated="auto"` for automatic hash upgrade

### 7.2 Authorization (RBAC)

**Location**: `core/security/rbac.py`

| Role | Permissions |
|------|-------------|
| **ADMIN** | `tool:*`, `api:*`, `session:*`, `admin:*` (wildcard = all) |
| **OPERATOR** | `tool:assess_risk`, `tool:search_memory`, `tool:request_approval`, `tool:create_task`, `tool:respond_to_user`, `tool:route_intent`, `api:chat`, `api:history`, `session:own` |
| **VIEWER** | `tool:search_memory`, `tool:respond_to_user`, `tool:route_intent`, `api:chat`, `api:history:read`, `session:own:read` |

**Wildcard matching**: `tool:*` matches any `tool:xxx` (prefix comparison). Default role for unknown users: `VIEWER`.

### 7.3 PromptGuard (3-Layer Defense)

**Location**: `core/security/prompt_guard.py` (Sprint 109)

| Layer | Function | Mechanism |
|-------|----------|-----------|
| **L1: Input Filtering** | `sanitize_input()` | 18 regex patterns detecting role confusion, boundary escape, data exfiltration, code injection. Replaces matches with `[FILTERED]`/`[ESCAPED]`. Max input 4000 chars. |
| **L2: System Prompt Isolation** | `wrap_user_input()` | Wraps in `<user_message>...</user_message>` tags after sanitization |
| **L3: Tool Call Validation** | `validate_tool_call()` | Whitelist check + arg key safety (alphanumeric+underscore) + arg value injection check |

**Pattern Categories**: `role_confusion` (7 patterns), `boundary_escape` (6 patterns), `exfiltration` (3 patterns), `code_injection` (2 patterns), `xss` (2 escape patterns)

### 7.4 ToolSecurityGateway (4-Layer Defense)

**Location**: `core/security/tool_gateway.py` (Sprint 109)

| Layer | Function | Mechanism |
|-------|----------|-----------|
| **L1: Input Sanitization** | `_sanitize_params()` | 17 regex patterns (SQL injection, XSS, prompt injection, code execution). Recursive validation of dicts/lists. Max param value 10,000 chars. |
| **L2: Permission Check** | `_check_permission()` | Role-based tool whitelist. Admin = empty frozenset (all allowed). |
| **L3: Rate Limiting** | `_check_rate_limit()` | In-memory sliding window per user per tool. Default: 30/min, high-risk: 5/min. High-risk tools: `dispatch_workflow`, `dispatch_swarm`. |
| **L4: Audit Logging** | `_audit_log()` | Structured logging of every tool call with allowed/denied status. |

**Also provides**: `@gateway.secure_tool_call(tool_name)` decorator for async functions.

### 7.5 Security Audit Report

**Location**: `core/security/audit_report.py`

Generates OWASP Top 10 compliance reports with:
- pip-audit dependency scanning
- 10 OWASP compliance checks (8 PASS, 2 PARTIAL)
- Authentication/authorization/data protection review sections
- Markdown and JSON output formats

---

## 8. Performance

### 8.1 CircuitBreaker

**Location**: `core/performance/circuit_breaker.py` (Sprint 116)

| State | Behavior | Transition |
|-------|----------|------------|
| **CLOSED** | Normal -- requests pass through | -> OPEN when `failure_count >= failure_threshold` (default 5) |
| **OPEN** | Short-circuit -- raise `CircuitOpenError` or use fallback | -> HALF_OPEN after `recovery_timeout` (default 60s) |
| **HALF_OPEN** | Probe -- one request allowed | -> CLOSED after `success_threshold` successes (default 2); -> OPEN on failure |

**Global singleton**: `get_llm_circuit_breaker()` with name="llm_api"
**Stats**: total_calls, total_failures, total_short_circuits

### 8.2 LLMCallPool

**Location**: `core/performance/llm_pool.py` (Sprint 109)

Priority-based concurrent LLM call management:

| Priority | Value | Use Case |
|----------|-------|----------|
| CRITICAL | 0 | Emergency |
| DIRECT_RESPONSE | 1 | User-facing chat |
| INTENT_ROUTING | 2 | Intent classification |
| EXTENDED_THINKING | 3 | Deep analysis |
| SWARM_WORKER | 4 | Background swarm |

**Mechanism**: `asyncio.PriorityQueue` + `asyncio.Semaphore(max_concurrent)` with background scheduler task. Per-minute rate limiting. Token budget tracking (input/output). Singleton via `get_instance()`.

### 8.3 BenchmarkRunner

**Location**: `core/performance/benchmark.py` (Sprint 12)

Full benchmarking suite:
- Sync (`run_sync`) and async (`run_async`) function benchmarking
- Configurable: iterations, warmup, timeout, GC collection, cooldown, parallel mode
- Statistics: mean, median, std, min, max, p50/p90/p95/p99, ops/second
- Comparison with regression detection (threshold-based)
- Suite runner with report generation
- `@benchmark()` decorator

### 8.4 LLMCacheService

**Location**: `infrastructure/cache/llm_cache.py` (Sprint 2)

- SHA256 cache key from model + prompt + relevant parameters (temperature, max_tokens, top_p, frequency_penalty)
- Key format: `llm_cache:{sha256_hash}`
- Default TTL: 3600s (1 hour)
- Hit count tracking per entry
- Statistics via Redis HSET (hits/misses)
- `CachedAgentService` wrapper with bypass option
- `warm_cache()` for pre-population

---

## 9. Workers (Background Jobs)

### 9.1 ARQClient

**Location**: `infrastructure/workers/arq_client.py` (Sprint 136)

| Aspect | Detail |
|--------|--------|
| **Queue** | ARQ (Redis-based) |
| **Queue name** | `ipa:arq:queue` |
| **Fallback** | Direct execution when ARQ/Redis unavailable |
| **Singleton** | `get_arq_client()` |
| **Methods** | `initialize()`, `enqueue(function_name, *args, timeout=600)`, `get_job_status(job_id)`, `close()` |

### 9.2 Task Functions

**Location**: `infrastructure/workers/task_functions.py` (Sprint 136)

| Function | Purpose | Status |
|----------|---------|--------|
| `execute_workflow_task` | Execute MAF workflow in background | Contains TODO comment for actual executor call |
| `execute_swarm_task` | Execute swarm coordination in background | Uses SwarmIntegration |
| `_update_task_status` | Update TaskStore with progress | Internal helper |

---

## 10. Additional Infrastructure

### 10.1 Redis Client (Centralized)

**Location**: `infrastructure/redis_client.py` (Sprint 119)

Replaces 5+ scattered `get_redis()` singletons. Uses `redis.asyncio` with:
- ConnectionPool max_connections=20, decode_responses=True
- socket_connect_timeout=5, socket_timeout=5, retry_on_timeout=True
- Health check endpoint (`check_redis_health()`)
- Graceful None return on connection failure

### 10.2 Distributed Lock

**Location**: `infrastructure/distributed_lock/redis_lock.py` (Sprint 119)

| Implementation | Backend | Multi-worker Safe |
|----------------|---------|-------------------|
| `RedisDistributedLock` | Redis SET NX PX | Yes |
| `InMemoryLock` | asyncio.Lock | No (single process only) |

**Protocol**: `DistributedLock` with `acquire()` (async context manager), `is_locked()`
**Factory**: `create_distributed_lock()` auto-selects Redis or InMemory
**Features**: Configurable timeout (deadlock prevention), blocking_timeout, lock extension for long ops

### 10.3 Rate Limiting Middleware

**Location**: `middleware/rate_limit.py` (Sprint 111)

| Environment | Default Limit |
|-------------|---------------|
| Development | 1000/minute |
| Production | 100/minute |

- Uses `slowapi` with `get_remote_address` key function
- In-memory storage (TODO: upgrade to Redis in Sprint 119 -- not done)
- Route-specific limits via `@limiter.limit()` decorator (10/min login, 30/min sensitive)

---

## 11. Messaging STUB Status

**Location**: `infrastructure/messaging/__init__.py`

**Content**: `# Messaging infrastructure` (1 line, 1 file)

**Status**: RabbitMQ is configured in Docker Compose (ports 5672/15672) and in `config.py` (rabbitmq_host, rabbitmq_port, rabbitmq_user, rabbitmq_password, rabbitmq_url property). However, **zero Python publisher/consumer code exists**. The messaging infrastructure remains entirely unimplemented.

---

## 12. Configuration

**Location**: `core/config.py`

`Settings` class extends `pydantic_settings.BaseSettings` with `SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")`.

| Category | Fields |
|----------|--------|
| **Application** | `app_env` (dev/staging/prod), `log_level`, `secret_key` |
| **Database** | `db_host`, `db_port`, `db_name`, `db_user`, `db_password` + `database_url` / `database_url_sync` properties |
| **Redis** | `redis_host`, `redis_port`, `redis_password` + `redis_url` property |
| **RabbitMQ** | `rabbitmq_host`, `rabbitmq_port`, `rabbitmq_user`, `rabbitmq_password` + `rabbitmq_url` property |
| **Azure OpenAI** | `azure_openai_endpoint`, `azure_openai_api_key`, `azure_openai_deployment_name` (gpt-5.2), `azure_openai_api_version` |
| **LLM Service** | `llm_enabled`, `llm_provider` (azure/mock), `llm_max_retries`, `llm_timeout_seconds`, `llm_cache_enabled`, `llm_cache_ttl_seconds` |
| **Azure Service Bus** | `azure_service_bus_connection_string` + `use_azure_service_bus` property |
| **JWT** | `jwt_secret_key`, `jwt_algorithm` (HS256), `jwt_access_token_expire_minutes` (60) |
| **CORS** | `cors_origins` (string) + `cors_origins_list` property |
| **Feature Flags** | `feature_workflow_enabled`, `feature_agent_enabled`, `feature_checkpoint_enabled` |
| **Observability** | `otel_enabled`, `otel_service_name`, `otel_exporter_otlp_endpoint`, `otel_sampling_rate`, `applicationinsights_connection_string` |
| **Logging** | `structured_logging_enabled` |
| **Dev** | `enable_api_docs`, `enable_sql_logging` |

**Singleton**: `@lru_cache() def get_settings() -> Settings`
**Security validator**: `validate_security_settings()` raises ValueError in production for unsafe secret_key/jwt_secret_key defaults.

---

## R8 Supplement: Previously Underdocumented Classes

| Class | Module | Methods | Purpose |
|-------|--------|---------|---------|
| `MetricCollector` | core/performance/metric_collector.py | 21 | Central metric collection and aggregation service — start/stop, record_request, aggregate, export metrics |
| `PerformanceOptimizer` | core/performance/optimizer.py | 15 | Performance optimization engine — identifies bottlenecks, suggests optimizations, applies caching strategies |
| `PerformanceProfiler` | core/performance/profiler.py | 12 | Runtime performance profiler — function-level timing, memory tracking, call graph analysis |
| `SandboxOrchestrator` | core/sandbox/orchestrator.py | 12 | Orchestrator for managing sandbox worker processes — execute_stream, get_pool_stats, resource isolation |

---

## 13. Known Issues (14 Issues)

### Issue 1: DUAL STORAGE PROTOCOL (HIGH)
**Sprint 110 ABC vs Sprint 119 Protocol** -- Two incompatible storage interfaces coexist. The ABC uses `timedelta` TTL, the Protocol uses `int` seconds. Method names differ (`keys` vs `list_keys`, `clear` vs `clear_all`). Neither implements the other's interface. This creates confusion about which to use for new code.

### Issue 2: PostgresBackend SEPARATE CONNECTION POOL (HIGH)
`PostgresBackend` creates its own `asyncpg.create_pool()` independent of the SQLAlchemy `AsyncEngine`. This means two separate connection pools to the same database, with no shared connection management or lifecycle coordination.

### Issue 3: MESSAGING COMPLETELY UNIMPLEMENTED (MEDIUM)
RabbitMQ is configured in Docker Compose and `config.py` but has zero Python code. The `messaging/__init__.py` file is a single comment. This blocks event-driven workflows that rely on message queues.

### Issue 4: datetime.utcnow() DEPRECATION (MEDIUM)
Multiple files use `datetime.utcnow()` which is deprecated in Python 3.12+. Should use `datetime.now(timezone.utc)`. Affected: `CheckpointEntry.is_expired()`, `Checkpoint.is_expired`, `jwt.py` (6 occurrences), `ExecutionRepository.start/complete/fail`, `CheckpointRepository.expire_old`, `ConversationState`, `BenchmarkRunner`, `LLMCacheService`, many more.

### Issue 5: RATE LIMITER IN-MEMORY STORAGE (MEDIUM)
`middleware/rate_limit.py` uses `storage_uri=None` (in-memory). The comment says "upgrade to Redis in Sprint 119" but this was never done. In multi-worker deployments, each worker has independent rate limit counters.

### Issue 6: ToolSecurityGateway IN-MEMORY RATE COUNTERS (MEDIUM)
`tool_gateway.py` rate limiting uses in-memory `Dict[str, _RateLimitEntry]`. Comment says "Phase 36 Sprint 110 will migrate to Redis" but this was never done. Same multi-worker issue as Issue 5.

### Issue 7: UserRepository NOT EXPORTED (LOW)
`UserRepository` (Sprint 70) is not included in `repositories/__init__.py` `__all__`. Consumers must import it directly from `repositories.user`.

### Issue 8: AUDIT REPORT HARDCODED OWASP RESULTS (LOW)
`audit_report.py` OWASP compliance checks return hardcoded results, not actual runtime analysis. The report claims "AES-256 encryption" and "TLS 1.3" without verification.

### Issue 9: WORKFLOW TASK TODO (LOW)
`task_functions.py` `execute_workflow_task` contains a `TODO` comment: "Call executor with workflow_type and input_data". The actual MAF workflow execution is not wired up.

### Issue 10: AuditStore SCAN-BASED QUERYING (MEDIUM)
`AuditStore.query()` performs N+1 reads: first SCAN for index keys, then individual GET for each entry. With large audit logs, this becomes extremely slow. No pagination or cursor-based iteration.

### Issue 11: ApprovalStore INDEX KEY LEAK (LOW)
When approvals expire or are resolved, `idx:status:pending:*` index keys are cleaned up, but expired records themselves persist until TTL (which may be None for resolved records). No background cleanup of resolved approval records.

### Issue 12: JWT HS256 SYMMETRIC KEY (LOW)
Using HS256 means the same key signs and verifies. If the key leaks, tokens can be forged. RS256 (asymmetric) would be more secure for production, especially with multiple services.

### Issue 13: CHECKPOINT CLEANUP N+1 QUERY PATTERN (MEDIUM)
`UnifiedCheckpointRegistry.cleanup_expired()` calls `list_checkpoints(limit=1000)` then `delete_checkpoint()` individually for each expired entry. For providers with many checkpoints, this is an O(N) delete operation.

### Issue 14: NO ALEMBIC MIGRATIONS REFERENCED (LOW)
Database models define the schema but no Alembic migration files are referenced in the infrastructure layer. Schema changes rely on the `database_url_sync` property but no migration runner is present.

---

## 14. Phase Evolution

| Sprint | Phase | Contribution |
|--------|-------|-------------|
| **Sprint 1** | Phase 1: Core Engine | Base models (User, Agent, Workflow, Execution, Checkpoint, AuditLog), BaseRepository, session.py |
| **Sprint 2** | Phase 1: Workflows | CheckpointRepository, LLMCacheService |
| **Sprint 12** | Phase 4: Performance | BenchmarkRunner |
| **Sprint 47** | Phase 11: Sessions | Session Recovery system (consumed by adapter) |
| **Sprint 57** | Phase 14: Hybrid | Hybrid Checkpoint system (consumed by adapter) |
| **Sprint 70** | Phase 18: Auth | JWT utilities, password hashing, UserRepository |
| **Sprint 72** | Phase 18: Auth | SessionModel + MessageModel + AttachmentModel, User.sessions relationship |
| **Sprint 109** | Phase 36: Security | PromptGuard (3-layer), ToolSecurityGateway (4-layer), LLMCallPool |
| **Sprint 110** | Phase 36: Storage | StorageBackendABC, InMemoryBackend, RedisBackend, PostgresBackend, StorageFactory, 6 high-level stores |
| **Sprint 111** | Phase 31: Security | rate_limit.py middleware, require_auth global dependency |
| **Sprint 112** | Phase 36: RBAC | RBACManager with 3 roles |
| **Sprint 113** | Phase 37: E2E | TaskStore |
| **Sprint 115** | Phase 37: E2E | ConversationStateStore (L1), ExecutionStateStore (L3) |
| **Sprint 116** | Phase 37: E2E | CircuitBreaker |
| **Sprint 119** | Phase 38: Storage | StorageBackend Protocol, RedisStorageBackend, InMemoryStorageBackend, 8 domain factories, redis_client.py centralized, RedisDistributedLock |
| **Sprint 120** | Phase 38: Checkpoint | CheckpointProvider Protocol, CheckpointEntry, UnifiedCheckpointRegistry, HybridCheckpointAdapter, 3 additional factory functions |
| **Sprint 121** | Phase 38: Checkpoint | DomainCheckpointAdapter, AgentFrameworkCheckpointAdapter, SessionRecoveryCheckpointAdapter |
| **Sprint 122** | Phase 38: Observability | OpenTelemetry config fields in Settings |
| **Sprint 136** | Phase 39: Workers | ARQClient, task_functions |

---

## 15. Summary Statistics

| Metric | Count |
|--------|-------|
| Total Python files | 95 |
| SQLAlchemy models | 9 (User, Agent, Workflow, Execution, Checkpoint, SessionModel, MessageModel, AttachmentModel, AuditLog) + Base mixin |
| DB tables | 9 (users, agents, workflows, executions, checkpoints, sessions, messages, attachments, audit_logs) |
| Repositories | 6 (Base + Agent + Workflow + Execution + Checkpoint + User) |
| Storage backends (ABC) | 3 (InMemory, Redis, Postgres) |
| Storage backends (Protocol) | 2 (Redis, InMemory) |
| High-level stores | 6 (Session, Conversation, Execution, Approval, Audit, Task) |
| Checkpoint providers | 4 (Hybrid, Domain, AgentFramework, SessionRecovery) |
| Security components | 5 (JWT, Password, RBAC, PromptGuard, ToolGateway) |
| Performance components | 4 (CircuitBreaker, LLMCallPool, BenchmarkRunner, LLMCacheService) |
| Config settings | ~30 fields |
| Known issues | 14 |
