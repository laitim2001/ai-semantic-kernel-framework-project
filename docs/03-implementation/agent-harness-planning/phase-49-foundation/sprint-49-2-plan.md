# Sprint 49.2 — DB Schema + Async ORM 核心

**建立日期**：2026-04-29
**所屬 Phase**：Phase 49 — Foundation（4 sprint）
**版本**：V1.0
**Sprint 編號**：49.2（Phase 49 第 2 個 Sprint，全 22 sprint 第 2 個）
**工作量**：1 週（5 工作天，估 25h）
**Story Points**：22 點
**狀態**：📋 計劃中（待用戶 approve）
**前一 Sprint**：49.1 ✅ DONE（V1 archive + V2 5 層骨架 + 11+1 ABC + CI）
**下一 Sprint**：49.3（RLS + Audit Append-Only + Memory + Qdrant Tenant 隔離）

---

## Sprint Goal

> **建立 V2 PostgreSQL 核心 schema（13 張表）+ Async SQLAlchemy 2.0 ORM models + Alembic migration 系統 + StateVersion 雙因子樂觀鎖機制，讓後續所有業務 sprint 都能在「真實多租戶 DB + 可遷移 schema」基礎上開發。**

本 Sprint 只做「**核心 ORM 結構 + migration 可信度 + 連線正確性**」三件事。**不做** RLS / audit append-only / memory / governance / api_keys（推到 49.3）；**不做** verification / subagent / cost / llm_invocations / workers（推到 49.4 或更後）。

---

## 前置條件

| 條件 | 狀態 |
|------|------|
| Sprint 49.1 完成（V2 骨架 + CI + Docker compose）| ✅ |
| `backend/src/infrastructure/db/` 目錄存在 + README | ✅ |
| `backend/src/core/config/` Settings 已有 `database_url` | ✅ |
| Docker compose `postgres:16` service 可啟動 | ✅ |
| `backend/pyproject.toml` 已含 `sqlalchemy[asyncio]>=2.0`、`asyncpg`、`alembic`、`pydantic-settings` | ✅（49.1 寫入）|
| V2 規劃文件 `09-db-schema-design.md` 為 schema 內容權威 | ✅ |
| V2 規劃文件 `06-phase-roadmap.md` 為 sprint 範圍權威 | ✅ |
| `.claude/rules/multi-tenant-data.md` 為 tenant_id 規則權威 | ✅ |

---

## User Stories

### Story 49.2-1：可信的 schema migration 系統

**作為** V2 開發者
**我希望** Alembic 從零跑通所有 49.2 migration 並可 down 回滾，每個 revision 對應一個邏輯群組
**以便** 後續 sprint 加 schema 時有明確 pattern 可依循、CI 可重複建立乾淨 DB

### Story 49.2-2：Identity / Tenancy 基底

**作為** 多租戶平台開發者
**我希望** tenants / users / roles / user_roles / role_permissions 5 表先到位
**以便** 所有業務表可 FK 引用 `tenant_id`，符合 `.claude/rules/multi-tenant-data.md` 鐵律 1

### Story 49.2-3：Sessions / Messages 主流量持久化基礎

**作為** Phase 50 開發者
**我希望** sessions + messages（partition Day 1）+ message_events（partition Day 1）就緒
**以便** Sprint 50.1 Loop 主類能直接 persist conversation history 與 SSE event stream

### Story 49.2-4：Tools 註冊與呼叫紀錄表

**作為** Phase 51 開發者
**我希望** tools_registry / tool_calls / tool_results 就緒
**以便** Sprint 51.1 Tool Layer 註冊工具、紀錄呼叫不需自建 schema

### Story 49.2-5：State 雙因子樂觀鎖

**作為** 範疇 7 State Mgmt 維護者
**我希望** state_snapshots（append-only）+ loop_states + StateVersion 雙因子（counter + content_hash）race condition 機制
**以便** 多 worker 並行寫同 session state 時不會 silently overwrite，且 time-travel debug 完整

### Story 49.2-6：Async ORM CRUD 在真實 PostgreSQL 跑通

**作為** 整個 V2 後端開發者
**我希望** pytest fixture `db_session` 用 docker compose 的 real PostgreSQL 跑（**不用 SQLite**）
**以便** 避免 V1 教訓 AP-10（mock vs real divergence — SQLite 通過 prod PostgreSQL 失敗）

### Story 49.2-7：清掉 49.1 retrospective 兩個 action item

**作為** 規劃文件 maintainer
**我希望** Sprint 49.1 retro 列的兩件雜事在本 sprint 順手清掉
**以便** 不累積技術債到 49.3 / 49.4

具體：
1. `02-architecture-design.md` + `06-phase-roadmap.md` 把 `platform/` 改 `platform_layer/`
2. `.gitignore` 補 Python 構建產物 pattern（`*.egg-info/` / `__pycache__/` 等若有遺漏）

---

## 技術設計

### 1. Migration 編號與檔案

依 09-db-schema-design.md 第 1161 行起的 migration 順序，但 **49.2 只執行其中 4 條**：

```
backend/src/infrastructure/db/migrations/versions/
├── 0001_initial_identity.py       # Day 1 — tenants/users/roles/user_roles/role_permissions
├── 0002_sessions_partitioned.py   # Day 2 — sessions/messages(part)/message_events(part)
├── 0003_tools.py                  # Day 3 — tools_registry/tool_calls/tool_results
└── 0004_state.py                  # Day 4 — state_snapshots+trigger/loop_states
```

> **注意**：09-db-schema-design.md 寫的「0002 audit / 0003 api_keys」順序屬於 49.3（推遲）。本 sprint 用「邏輯群組順序 1-4」對應 49.2 範圍，不依 09.md 全 14 條順序。Sprint 49.3 開始時將其 migration 從 0005 起編號（audit / api_keys / memory / governance / RLS）。

### 2. ORM Module 結構

```
backend/src/infrastructure/db/
├── __init__.py
├── README.md                      # 已存在
├── engine.py                      # 新建 — async engine + session factory
├── base.py                        # 新建 — DeclarativeBase + TenantScopedMixin
├── session.py                     # 新建 — FastAPI dependency get_db_session
├── models/
│   ├── __init__.py                # re-export 所有 ORM models
│   ├── identity.py                # Day 1 — Tenant/User/Role/UserRole/RolePermission
│   ├── sessions.py                # Day 2 — Session/Message/MessageEvent
│   ├── tools.py                   # Day 3 — ToolRegistry/ToolCall/ToolResult
│   └── state.py                   # Day 4 — StateSnapshot/LoopState
├── migrations/
│   ├── env.py                     # Alembic env
│   ├── script.py.mako             # template
│   └── versions/
│       ├── 0001_initial_identity.py
│       ├── 0002_sessions_partitioned.py
│       ├── 0003_tools.py
│       └── 0004_state.py
└── alembic.ini                    # at backend/ root
```

### 3. TenantScopedMixin 強制鐵律

```python
# backend/src/infrastructure/db/base.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import UUID, ForeignKey

class Base(DeclarativeBase):
    """V2 ORM declarative base."""
    pass

class TenantScopedMixin:
    """強制 tenant_id NOT NULL。任何 session-scoped 表 inherits 此 mixin。"""
    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
```

`tenants` / 全局 `tools_registry` 不繼承（無 tenant_id）。其餘 11 張表都繼承。

### 4. StateVersion 雙因子樂觀鎖（Story 49.2-5）

**設計**：寫入 state_snapshot 時要同時驗證：
1. `version` counter（單調遞增；session 內 unique）
2. `state_hash` (SHA-256 of state_data) 與 `parent_version` 對應 row 的 hash 一致

**Insert 流程（Python 偽代碼）**：

```python
# infrastructure/db/models/state.py
async def append_snapshot(
    session: AsyncSession,
    *,
    session_id: UUID,
    state_data: dict,
    parent_version: int | None,
    expected_parent_hash: str | None,
    reason: str,
) -> StateSnapshot:
    """
    Append state snapshot with optimistic concurrency check.

    Raises:
        StateConflictError: parent_version 已被別 worker 推進，or parent_hash 不符
    """
    # 1. 算當前 state_data 的 hash
    new_hash = sha256(json.dumps(state_data, sort_keys=True).encode()).hexdigest()

    # 2. 算下一 version
    next_version = (parent_version or 0) + 1

    # 3. 驗證 parent_hash（若非 first snapshot）
    if parent_version is not None:
        parent = await session.get(StateSnapshot, ...)  # by session_id+version
        if parent is None or parent.state_hash != expected_parent_hash:
            raise StateConflictError("parent_version mismatch")

    # 4. 嘗試 INSERT；UNIQUE(session_id, version) 違規時重試
    try:
        snapshot = StateSnapshot(
            session_id=session_id,
            version=next_version,
            parent_version=parent_version,
            state_data=state_data,
            state_hash=new_hash,
            reason=reason,
        )
        session.add(snapshot)
        await session.flush()
        return snapshot
    except IntegrityError as e:
        # 另一 worker 同時推進；上層決定是否 retry
        raise StateConflictError("version race") from e
```

**Race condition test**：

```python
# tests/unit/infrastructure/db/test_state_race.py
async def test_concurrent_snapshot_insert_one_wins(db_session_factory):
    """兩個 worker 同時用同一 parent_version+1，只能一個成功。"""
    async def worker(barrier):
        async with db_session_factory() as session:
            await barrier.wait()
            return await append_snapshot(session, ..., parent_version=5, ...)

    barrier = asyncio.Barrier(2)
    results = await asyncio.gather(worker(barrier), worker(barrier), return_exceptions=True)

    successes = [r for r in results if isinstance(r, StateSnapshot)]
    failures = [r for r in results if isinstance(r, StateConflictError)]
    assert len(successes) == 1
    assert len(failures) == 1
```

### 5. Append-Only Trigger for state_snapshots

```sql
-- migration 0004
CREATE OR REPLACE FUNCTION prevent_state_snapshot_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'state_snapshots is append-only';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER state_snapshots_no_update_delete
    BEFORE UPDATE OR DELETE ON state_snapshots
    FOR EACH ROW EXECUTE FUNCTION prevent_state_snapshot_modification();
```

**Trigger 測試**：
```python
async def test_state_snapshot_cannot_be_updated(db_session):
    snapshot = await append_snapshot(db_session, ...)
    await db_session.commit()

    snapshot.reason = "tampered"
    with pytest.raises(IntegrityError, match="append-only"):
        await db_session.commit()
```

### 6. Messages / Message_events Partition Day 1

依 09-db-schema-design.md L1042-1075：

```sql
-- migration 0002
CREATE TABLE messages (
    id UUID NOT NULL,
    session_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    sequence_num INT NOT NULL,
    -- ... (per 09.md L1042-1059)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, created_at),
    UNIQUE (session_id, sequence_num, created_at)
) PARTITION BY RANGE (created_at);

-- 首兩月 partition（手動）
CREATE TABLE messages_2026_05 PARTITION OF messages
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

CREATE TABLE messages_2026_06 PARTITION OF messages
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
```

> **pg_partman 自動分區**🚧 推到 Sprint 49.3（49.2 只手動建首兩月分區）。

`message_events` 同樣月度 partition；首兩月手動。

### 7. Async Engine + Session Factory

```python
# backend/src/infrastructure/db/engine.py
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncEngine, AsyncSession
from src.core.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None

def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        s = get_settings()
        _engine = create_async_engine(
            s.database_url,
            pool_size=s.db_pool_size,
            max_overflow=s.db_pool_max_overflow,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=s.db_echo,
        )
    return _engine

def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory
```

### 8. Settings 擴充

```python
# backend/src/core/config/__init__.py 新增欄位
db_pool_size: int = 10
db_pool_max_overflow: int = 20
db_pool_recycle_sec: int = 300
db_echo: bool = False

# 49.2 暫不加 db_ssl_mode（49.3 RLS 配套處理）
```

### 9. pytest Fixture（real PostgreSQL，AP-10 對策）

```python
# backend/tests/conftest.py 擴充
@pytest_asyncio.fixture
async def db_session():
    """每個 test 一個 transaction，結束 rollback。用 real docker compose PostgreSQL。"""
    factory = get_session_factory()
    async with factory() as session:
        async with session.begin():
            yield session
            await session.rollback()  # 即使 test pass 也 rollback，保持 DB 乾淨
```

CI / 本地測試前必須 `docker compose -f docker-compose.dev.yml up -d postgres` + `alembic upgrade head`。

### 10. 49.1 Action Items 順手清

**A. `platform/` → `platform_layer/` 文件同步**：

修改：
- `docs/03-implementation/agent-harness-planning/02-architecture-design.md`
- `docs/03-implementation/agent-harness-planning/06-phase-roadmap.md`
- 任何其他規劃文件 grep 到 `platform/`（用 grep 確認）

**B. `.gitignore` Python 構建產物 pattern**：

確認以下已存在：
```
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
*.egg
.pytest_cache/
.mypy_cache/
.coverage
htmlcov/
```

---

## File Change List

### 新建（19 個 + 4 migration = 23）

```
backend/alembic.ini                                                 # +1
backend/src/infrastructure/db/engine.py                             # +1
backend/src/infrastructure/db/base.py                               # +1
backend/src/infrastructure/db/session.py                            # +1
backend/src/infrastructure/db/exceptions.py                         # +1 (StateConflictError 等)
backend/src/infrastructure/db/models/__init__.py                    # +1
backend/src/infrastructure/db/models/identity.py                    # +1
backend/src/infrastructure/db/models/sessions.py                    # +1
backend/src/infrastructure/db/models/tools.py                       # +1
backend/src/infrastructure/db/models/state.py                       # +1
backend/src/infrastructure/db/migrations/env.py                     # +1
backend/src/infrastructure/db/migrations/script.py.mako             # +1
backend/src/infrastructure/db/migrations/__init__.py                # +1
backend/src/infrastructure/db/migrations/versions/__init__.py       # +1
backend/src/infrastructure/db/migrations/versions/0001_initial_identity.py    # +1
backend/src/infrastructure/db/migrations/versions/0002_sessions_partitioned.py # +1
backend/src/infrastructure/db/migrations/versions/0003_tools.py     # +1
backend/src/infrastructure/db/migrations/versions/0004_state.py     # +1
backend/tests/conftest.py（如不存在）                                # +1
backend/tests/unit/infrastructure/db/test_engine_connect.py         # +1
backend/tests/unit/infrastructure/db/test_models_crud.py            # +1
backend/tests/unit/infrastructure/db/test_state_race.py             # +1
backend/tests/unit/infrastructure/db/test_state_append_only.py      # +1
backend/tests/unit/infrastructure/db/test_partition_routing.py      # +1
```

### 修改（4）

```
backend/src/core/config/__init__.py                  # +db_* fields
backend/src/infrastructure/db/__init__.py            # re-export engine + session
backend/src/infrastructure/db/README.md              # 49.2 status: implemented
backend/.env.example                                  # 補 db_pool_* 範例
docs/03-implementation/agent-harness-planning/02-architecture-design.md  # platform→platform_layer
docs/03-implementation/agent-harness-planning/06-phase-roadmap.md         # platform→platform_layer
```

### 不動（49.1 完成的）

- `agent_harness/_contracts/` 全部
- `adapters/_base/` 全部
- 13 範疇 ABC

---

## Acceptance Criteria

驗收 5 項（roadmap 3 項 + 2 項自加）：

- [ ] **AC-1（roadmap）**：`alembic upgrade head` 從乾淨 DB 跑通 4 個 migration 無錯誤；`alembic downgrade base` 可全 rollback
- [ ] **AC-2（roadmap）**：每張 ORM 表 ≥ 1 個 CRUD 測試（create + read + update + delete）通過，**測試使用 docker compose real PostgreSQL，禁止 SQLite**
- [ ] **AC-3（roadmap）**：StateVersion (counter + content_hash) race condition test 通過：兩 worker 並行 insert 同 parent_version+1 → 一成功一失敗
- [ ] **AC-4（自加）**：state_snapshots append-only trigger 測試通過：UPDATE / DELETE 應 raise IntegrityError
- [ ] **AC-5（自加）**：messages partition routing 測試通過：插入 created_at='2026-05-15' → 進 messages_2026_05；插入 '2026-06-15' → 進 messages_2026_06

---

## Dependencies & Risks

### 外部依賴

- ✅ Docker compose `postgres:16` service（49.1 完成）
- ⚠️ asyncpg + sqlalchemy 2.0 + alembic 版本需鎖定 — Day 1 確認 `pyproject.toml` 已釘版本

### 風險

| 風險 | 機率 | 衝擊 | 對策 |
|------|-----|------|------|
| Alembic + async engine 整合複雜 | 中 | 中 | env.py 用 SQLAlchemy 2.0 async pattern；參考官方 `migrate-asyncio` template |
| Partition migration alembic auto-generate 失準 | 高 | 中 | 0002 migration 手寫 SQL（不依賴 autogenerate） |
| Real PostgreSQL test 緩慢 | 中 | 低 | 用 transaction rollback fixture（不真寫入），單 sprint 跑時間 < 60s |
| StateVersion race test flaky | 低 | 中 | 用 `asyncio.Barrier` 嚴格同步 + 重複跑 100 次 verify |
| trigger 寫法跨 PostgreSQL 版本問題 | 低 | 低 | 鎖定 PG 16；migration 0004 註明 PG ≥ 14 |

### 推遲到後續 sprint（🚧 明示）

| 推遲項 | 推遲到 | 理由 |
|-------|--------|------|
| 🚧 audit_log + append-only + hash chain | **49.3** | 49.3 主題（RLS + Audit）|
| 🚧 api_keys / rate_limits | **49.3** | 多租戶配套 |
| 🚧 5 層 memory 表 | **49.3** | 與 RLS / Qdrant 一起 |
| 🚧 approvals / risk_assessments / guardrail_events | **49.3 / 53.4** | Governance 主題 |
| 🚧 RLS policies 全表套用 | **49.3** | 49.3 主題 |
| 🚧 verification_results | 範疇 10 sprint（54.1） | 範疇實作時建 |
| 🚧 subagent_runs / subagent_messages | 範疇 11 sprint（54.2） | 同上 |
| 🚧 worker_tasks / outbox | 49.4 | Worker queue 選型同期 |
| 🚧 cost_ledger / llm_invocations | 49.4 | Adapter 整合同期 |
| 🚧 pg_partman 自動分區 | 49.3 | 49.2 手動建首兩月即可 |
| 🚧 indexes optimization (0014) | 49.3 / 49.4 | 待負載測試後優化 |

---

## V2 紀律 9 項自檢

| # | 紀律 | 49.2 狀態 |
|---|------|----------|
| 1 | Server-Side First | ✅ 全部 server-side（DB / async pool） |
| 2 | LLM Provider Neutrality | N/A（本 sprint 無 LLM call）|
| 3 | CC Reference 不照搬 | N/A |
| 4 | 17.md Single-source | ✅ ORM models 引用 `_contracts/` 型別（如 `LoopState` shape）|
| 5 | 11+1 範疇歸屬 | ✅ 全在 `infrastructure/`（橫向支撐層，非 11+1 之一）|
| 6 | 04 anti-patterns 對齐 | ✅ 特別防 AP-10（real PG，禁 SQLite） |
| 7 | Sprint workflow（plan→checklist→code）| ✅ 本 plan + checklist 完成才 code |
| 8 | File header convention | ✅ 每個新檔案有 docstring header |
| 9 | Multi-tenant rule | ✅ TenantScopedMixin 強制；除 tenants/tools_registry 外全表帶 tenant_id |

---

## Story Points 估算

| 項目 | 點 |
|------|---|
| Day 1 — Alembic 基底 + Identity migration + ORM | 5 |
| Day 2 — Sessions migration（含 partition） + ORM + CRUD test | 5 |
| Day 3 — Tools migration + ORM + CRUD test | 4 |
| Day 4 — State migration + append-only + StateVersion race test | 6 |
| Day 5 — Settings + fixture + V2 文件 platform 同步 + closeout | 2 |
| **總計** | **22 點** |

---

## 後續 Sprint 起點

Sprint 49.2 完成後，Sprint 49.3（RLS + Audit Append-Only + Memory + Qdrant）將：

- 在現有 13 表上 ALTER + ADD RLS policies（migration 0005）
- 加 audit_log 表 + append-only trigger + hash chain（migration 0006）
- 加 api_keys / rate_limits（migration 0007）
- 加 5 層 memory 表（migration 0008）
- 加 governance（approvals / risk / guardrail）（migration 0009）
- Qdrant collections per tenant namespace
- Red-team test：跨 tenant prompt injection 0 leak

Sprint 49.3 plan 將於 49.2 完成後（rolling planning）建立。
