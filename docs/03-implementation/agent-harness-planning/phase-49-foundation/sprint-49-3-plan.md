# Sprint 49.3 — RLS + Audit Append-Only + Memory + Qdrant Tenant 隔離

**建立日期**：2026-04-29
**所屬 Phase**：Phase 49 — Foundation（4 sprint）
**版本**：V1.0
**Sprint 編號**：49.3（Phase 49 第 3 個 Sprint，全 22 sprint 第 3 個）
**工作量**：1 週（5 工作天，估 28h）
**Story Points**：26 點
**狀態**：📋 計劃中（待用戶 approve）
**前一 Sprint**：49.2 ✅ DONE（DB Schema + Async ORM + StateVersion 雙因子）
**下一 Sprint**：49.4（Adapters + Worker Queue 選型 + OTel + Lint Rules）

---

## Sprint Goal

> **在 Sprint 49.2 已建好的 13 張表基礎上，補齊 Phase 50+ 業務開發必須先到位的「安全基線」：14+ 表 RLS policies + audit_log（append-only + hash chain + STATEMENT TRUNCATE trigger）+ 5 層 memory + governance（approvals / risk / guardrail）+ api_keys / rate_limits + per-request `SET LOCAL app.tenant_id` middleware + Qdrant tenant namespace 抽象 + 跨 tenant 紅隊測試。**

本 Sprint 完成後：所有後續業務 sprint 寫入 DB 都受 RLS 強制隔離；audit log 不可竄改；HITL approval / risk assessment / guardrail event 三條 trail 就緒；5 層 memory schema 可被範疇 3（Phase 51.2）直接落地；Qdrant 接入有 tenant-aware namespace 對應規則。

**不做**：actual Qdrant client integration（推到 51.2 memory）；audit_log 後續分析工具（推到 SaaS Stage）；row-level rotate api_keys（推到 53.x security hardening）。

---

## 前置條件

| 條件 | 狀態 |
|------|------|
| Sprint 49.2 完成（13 表 + 4 migrations + 29 tests）| ✅ |
| `backend/src/infrastructure/db/` 4 modules + 13 ORM models | ✅ |
| `backend/alembic/versions/0001-0004` migrations 在 head | ✅ |
| Docker compose `postgres:16` 已驗證 RLS 支援（PG 16 內建）| ✅ |
| `09-db-schema-design.md` audit / memory / governance schema 為權威 | ✅ |
| `14-security-deep-dive.md` RLS / append-only / GDPR 為權威 | ✅ |
| `.claude/rules/multi-tenant-data.md` 三鐵律為強制 | ✅ |
| `.claude/rules/observability-instrumentation.md` 範疇 12 埋點 | ✅ |

---

## User Stories

### Story 49.3-1：所有 session-scoped 表 RLS 強制隔離

**作為** 多租戶平台維運者
**我希望** 14+ 張 session-scoped 表全部有 PostgreSQL RLS policies + per-request `SET LOCAL app.tenant_id` middleware
**以便** 任何 query bug、任何 SQL injection、任何 ORM forgot-to-filter 情境都不能跨租戶讀取或寫入

### Story 49.3-2：Audit log 不可竄改

**作為** 合規負責人
**我希望** audit_log 表（DB 觸發器強制 append-only + hash chain + STATEMENT-level TRUNCATE trigger）就緒
**以便** 所有業務操作有不可竄改的審計軌跡（UPDATE / DELETE / TRUNCATE 全擋）

### Story 49.3-3：API key + rate limit schema

**作為** Phase 55 SaaS 對外 API 開發者
**我希望** api_keys + rate_limits schema 就緒（含 hash 儲存 + 過期 + revoke）
**以便** 後續可直接基於本 schema 建 admin endpoint，不重做 schema design

### Story 49.3-4：5 層 memory schema

**作為** 範疇 3 Memory（Phase 51.2）開發者
**我希望** memory_system / memory_tenant / memory_role / memory_user / memory_session_summary 5 表就緒
**以便** Phase 51.2 直接寫 retrieval / extraction 邏輯，schema 不阻塞

### Story 49.3-5：Governance 三條 trail

**作為** 範疇 9 Guardrails（Phase 53.3）+ HITL（53.4）開發者
**我希望** approvals / risk_assessments / guardrail_events 三表就緒
**以便** 後續 HITL 接 frontend 不需返工 schema、guardrail 觸發有持久化標的

### Story 49.3-6：Qdrant tenant-aware namespace 抽象

**作為** Phase 51.2 vector retrieval 開發者
**我希望** Qdrant collection 命名 + payload tenant_id filter 規則明文 + 抽象介面（不接實際 client）
**以便** Phase 51.2 接 Qdrant client 時遵循統一命名規則、跨 tenant 不混用 collection

### Story 49.3-7：跨 tenant 紅隊測試 0 leak

**作為** 安全架構師
**我希望** Phase 49.3 結束有自動化 red-team test：偽造 tenant_id / 移除 SET LOCAL / SQL injection / prompt injection 場景全部 0 leak
**以便** 進 Phase 50 主流量開發前，多租戶隔離 baseline 已驗證

### Story 49.3-8：清掉 49.2 retrospective 帶過來的 action items

**作為** 規劃文件 maintainer
**我希望** 49.2 retro 列的 (1) TRUNCATE STATEMENT trigger 補裝（state_snapshots + audit_log 一起）+ (2) pg_partman rolling +6 months partitions 自動化在本 sprint 順手清掉
**以便** 不累積技術債到 49.4 + Phase 50 主流量開發無 partition NOW() 撞牆風險

---

## 範疇歸屬

| 工作項 | 範疇 | 文件位置 |
|--------|------|---------|
| Audit log table + append-only trigger | infrastructure（跨範疇 governance 用） | `backend/src/infrastructure/db/models/audit.py` |
| API keys + rate limits | infrastructure（identity domain） | `backend/src/infrastructure/db/models/identity.py` 擴充 |
| 5 layer memory tables | 範疇 3 Memory（schema layer） | `backend/src/infrastructure/db/models/memory.py` |
| Governance 3 tables | 範疇 9 Guardrails / HITL | `backend/src/infrastructure/db/models/governance.py` |
| RLS policies | 跨範疇 cross-cutting | `backend/alembic/versions/0009_rls_policies.py` |
| `SET LOCAL` middleware | platform_layer | `backend/src/platform_layer/middleware/tenant_context.py` |
| Qdrant namespace abstraction | infrastructure（vector layer） | `backend/src/infrastructure/vector/qdrant_namespace.py` |
| Red-team tests | tests/security | `backend/tests/security/test_red_team_isolation.py` |

---

## 技術設計

### 1. Audit Log Append-Only 機制（Story 49.3-2）

**Schema**（per 09-db-schema-design.md L678-720）：

```sql
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    user_id UUID,
    operation VARCHAR(128) NOT NULL,
    resource_type VARCHAR(64),
    resource_id VARCHAR(256),
    access_allowed BOOLEAN NOT NULL,
    payload JSONB,
    prev_hash CHAR(64),                      -- SHA-256 of previous row
    row_hash CHAR(64) NOT NULL,              -- SHA-256(prev_hash || serialized columns)
    timestamp_ms BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- 月度 partition（49.3 含 2026-04 / 05 / 06 三個月）
CREATE TABLE audit_log_2026_04 PARTITION OF audit_log FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE audit_log_2026_05 PARTITION OF audit_log FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE audit_log_2026_06 PARTITION OF audit_log FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');

CREATE INDEX idx_audit_log_tenant_time ON audit_log(tenant_id, created_at DESC);
```

**ROW-level UPDATE/DELETE 觸發器**（已在 49.2 學會的 pattern）：

```sql
CREATE OR REPLACE FUNCTION audit_log_row_immutable() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only; UPDATE/DELETE forbidden';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_log_no_update
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_row_immutable();
```

**STATEMENT-level TRUNCATE 觸發器**（49.2 deferred → 49.3 補）：

```sql
CREATE OR REPLACE FUNCTION audit_log_truncate_immutable() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only; TRUNCATE forbidden';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_log_no_truncate
    BEFORE TRUNCATE ON audit_log
    FOR EACH STATEMENT EXECUTE FUNCTION audit_log_truncate_immutable();

-- 同理補裝 state_snapshots 的 STATEMENT TRUNCATE trigger（49.2 deferred）
CREATE TRIGGER trg_state_snapshots_no_truncate
    BEFORE TRUNCATE ON state_snapshots
    FOR EACH STATEMENT EXECUTE FUNCTION state_snapshots_truncate_immutable();
```

**Hash chain helper（Python）**：

```python
def compute_audit_hash(prev_hash: str | None, payload: dict, tenant_id: UUID, ts_ms: int) -> str:
    """SHA-256(prev_hash || canonical_json(payload) || tenant_id || ts_ms)"""
    base = (prev_hash or "0" * 64) + json.dumps(payload, sort_keys=True) + str(tenant_id) + str(ts_ms)
    return hashlib.sha256(base.encode()).hexdigest()

async def append_audit(session, *, tenant_id, user_id, operation, resource_type, resource_id, allowed, payload):
    """Append a new audit row, computing prev_hash from latest existing row in this tenant partition."""
    latest = await session.execute(
        select(AuditLog.row_hash)
        .where(AuditLog.tenant_id == tenant_id)
        .order_by(AuditLog.id.desc())
        .limit(1)
    )
    prev_hash = latest.scalar_one_or_none()
    ts_ms = int(time.time() * 1000)
    row_hash = compute_audit_hash(prev_hash, payload, tenant_id, ts_ms)
    row = AuditLog(
        tenant_id=tenant_id, user_id=user_id, operation=operation, resource_type=resource_type,
        resource_id=resource_id, access_allowed=allowed, payload=payload,
        prev_hash=prev_hash, row_hash=row_hash, timestamp_ms=ts_ms,
    )
    session.add(row)
    return row
```

### 2. RLS Policies（Story 49.3-1）

**所有 tenant-scoped 表（14+ 張）必須**：

```sql
ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;
ALTER TABLE <table> FORCE ROW LEVEL SECURITY;  -- 即使 owner 也強制

CREATE POLICY tenant_isolation_<table> ON <table>
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_insert_<table> ON <table>
    FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);
```

**14 張表清單**（49.2 已 13 表 + 49.3 新增 9 表 - 5 全局表）：
- session-scoped：users / roles / sessions / messages / message_events / tool_calls / state_snapshots / loop_states / api_keys / rate_limits / approvals / risk_assessments / guardrail_events / audit_log（**14 張**）
- 全局表（不掛 RLS）：tenants（root）/ tools_registry（global metadata）/ user_roles（junction，via FK chain）/ role_permissions（同）/ tool_results（via tool_call → session）/ memory_system（global facts）

### 3. `SET LOCAL app.tenant_id` Middleware（Story 49.3-1）

```python
# backend/src/platform_layer/middleware/tenant_context.py
class TenantContextMiddleware(BaseHTTPMiddleware):
    """Extract tenant_id from JWT, set per-request DB session local."""

    async def dispatch(self, request: Request, call_next):
        # Phase 49.3 stub: 從 header X-Tenant-Id 讀（49.4+ 會接 JWT）
        tenant_id_str = request.headers.get("X-Tenant-Id")
        if not tenant_id_str:
            return JSONResponse({"error": "X-Tenant-Id required"}, status_code=401)

        try:
            tenant_id = UUID(tenant_id_str)
        except ValueError:
            return JSONResponse({"error": "Invalid tenant_id format"}, status_code=400)

        request.state.tenant_id = tenant_id
        return await call_next(request)
```

```python
# 配套 dependency（注入到 endpoint）
async def get_db_session_with_tenant(request: Request) -> AsyncIterator[AsyncSession]:
    tenant_id = request.state.tenant_id
    async with async_session_factory() as session:
        await session.execute(
            text("SET LOCAL app.tenant_id = :tid"),
            {"tid": str(tenant_id)}
        )
        yield session
```

### 4. Qdrant Namespace 抽象（Story 49.3-6）

**不接實際 Qdrant client（推 51.2）**，本 sprint 只定義 contract：

```python
# backend/src/infrastructure/vector/qdrant_namespace.py
class QdrantNamespaceStrategy:
    """Tenant-aware Qdrant collection naming + filter rules."""

    @staticmethod
    def collection_name(tenant_id: UUID, layer: Literal["user_memory", "session_memory", "kb"]) -> str:
        """e.g., tenant_<uuid_short>_user_memory"""
        return f"tenant_{str(tenant_id).replace('-', '')[:16]}_{layer}"

    @staticmethod
    def payload_filter(tenant_id: UUID) -> dict:
        """Filter payload to ensure tenant_id match in addition to collection scope (defense-in-depth)."""
        return {"must": [{"key": "tenant_id", "match": {"value": str(tenant_id)}}]}
```

### 5. pg_partman Rolling +6 months（49.2 carried over）

```sql
CREATE EXTENSION IF NOT EXISTS pg_partman;

SELECT partman.create_parent(
    p_parent_table => 'public.messages',
    p_control => 'created_at',
    p_type => 'native',
    p_interval => '1 month',
    p_premake => 6
);

SELECT partman.create_parent('public.message_events', 'created_at', 'native', '1 month', 6);
SELECT partman.create_parent('public.audit_log', 'created_at', 'native', '1 month', 6);
```

---

## 預期 Schema 變動清單

### 新增 5 個 migrations

| Revision | 主題 | 主要變動 |
|---------|------|--------|
| `0005_audit_log` | audit_log + 3 partitions + ROW + STATEMENT triggers + state_snapshots TRUNCATE trigger 補 | 1 表 + 3 partitions + 4 triggers + 2 functions |
| `0006_api_keys_rate_limits` | api_keys + rate_limits | 2 表 + 4 indexes |
| `0007_memory_layers` | memory_system / memory_tenant / memory_role / memory_user / memory_session_summary | 5 表 + 8 indexes |
| `0008_governance` | approvals / risk_assessments / guardrail_events | 3 表 + 6 indexes |
| `0009_rls_policies_pg_partman` | 14 表 RLS + pg_partman rolling | 14×2 policies + pg_partman setup |

### 新增 4 個 ORM model files

- `backend/src/infrastructure/db/models/audit.py` — AuditLog
- `backend/src/infrastructure/db/models/memory.py` — 5 個 memory layer classes
- `backend/src/infrastructure/db/models/governance.py` — Approval / RiskAssessment / GuardrailEvent
- `backend/src/infrastructure/db/models/identity.py` 擴充 — ApiKey / RateLimit

### 新增 platform layer middleware（首發）

- `backend/src/platform_layer/middleware/__init__.py`
- `backend/src/platform_layer/middleware/tenant_context.py` — TenantContextMiddleware

### 新增 vector infrastructure

- `backend/src/infrastructure/vector/__init__.py`
- `backend/src/infrastructure/vector/qdrant_namespace.py`

### 新增 helper / utility

- `backend/src/infrastructure/db/audit_helper.py` — `append_audit()` + `compute_audit_hash()`

### 新增測試 8 套

- `tests/unit/infrastructure/db/test_audit_append_only.py` — UPDATE/DELETE/TRUNCATE 三擋 + hash chain 驗證
- `tests/unit/infrastructure/db/test_memory_models_crud.py` — 5 層 CRUD + tenant 隔離
- `tests/unit/infrastructure/db/test_governance_models_crud.py` — approvals workflow stub
- `tests/unit/infrastructure/db/test_api_keys_crud.py`
- `tests/unit/infrastructure/db/test_rls_enforcement.py` — set local 切換 / 跨 tenant 0 leak
- `tests/unit/platform_layer/middleware/test_tenant_context.py`
- `tests/unit/infrastructure/vector/test_qdrant_namespace.py`
- `tests/security/test_red_team_isolation.py` — 紅隊跨 tenant 攻擊全擋

---

## Acceptance Criteria

### AC-1：5 個 migrations 可正向 + 反向跑通

```bash
alembic downgrade base
alembic upgrade head
# Should: 20 tables (49.2) + 14 tables (49.3) - 5 全局重疊 = ~29 tables
# Plus: 6 audit triggers + 14 RLS policies × 2 (USING + INSERT) = 28 policies + pg_partman setup
```

### AC-2：Audit append-only 在 DB 層強制

```python
# 應全部 raise DBAPIError
session.execute(update(AuditLog).where(...))   # ❌ row trigger
session.execute(delete(AuditLog).where(...))   # ❌ row trigger
session.execute(text("TRUNCATE audit_log"))    # ❌ statement trigger
```

### AC-3：Hash chain 驗證

```python
# 每 row 的 row_hash == sha256(prev_hash || canonical(payload) || tenant_id || ts)
# 且 row N 的 prev_hash == row N-1 的 row_hash
```

### AC-4：14 表 RLS 跨 tenant 0 leak

```python
# 在 tenant_a SET LOCAL，不可讀 tenant_b 的 messages / audit / approvals 任何資料
# pytest red-team 套件 0 fail
```

### AC-5：5 層 memory schema CRUD + tenant 隔離

```python
# 5 個 memory layer 類別都繼承 TenantScopedMixin
# CRUD 跨 tenant 不可見
```

### AC-6：Governance 3 表 workflow stub

```python
# 可寫入 approval（pending → approved/rejected）
# 可寫入 risk_assessment 含 score + recommendation
# 可寫入 guardrail_event 含 detector + severity + action_taken
```

### AC-7：Tenant context middleware + per-request SET LOCAL

```python
# Request 帶 X-Tenant-Id → middleware 設 request.state.tenant_id
# Endpoint dependency `get_db_session_with_tenant` 自動 SET LOCAL
# 缺 X-Tenant-Id → 401
```

### AC-8：Qdrant namespace 規則 + payload filter（不接實際 client）

```python
# QdrantNamespaceStrategy.collection_name(tenant_a, "user_memory") != for tenant_b
# payload_filter 含 tenant_id must clause
```

### AC-9：49.2 carried-over 兩件清掉

```python
# state_snapshots TRUNCATE 觸發器：raise
# pg_partman setup 後，message / audit_log 自動 +6 months
```

### AC-10：紅隊測試套件 0 leak

```python
# 6 個攻擊向量全部 deny:
# 1. 偽造 X-Tenant-Id（使用其他 tenant 的 UUID）→ RLS 阻擋（query 看不到）
# 2. 移除 SET LOCAL → query 拿空（current_setting 為 NULL）
# 3. SQL injection 嘗試 SET app.tenant_id → 應被 cast::uuid 擋
# 4. UPDATE audit_log 嘗試 → trigger raise
# 5. TRUNCATE audit_log / state_snapshots → trigger raise
# 6. 跨 collection Qdrant payload 不含 tenant_id filter → namespace 強制 prefix 不重疊
```

### AC-11：CI 通過

```yaml
- alembic upgrade head + verify table count
- alembic downgrade base + verify clean
- pytest backend/tests/unit/infrastructure/db/ + tests/security/ 全綠
- mypy strict on new files
- LLM SDK leak grep on new files: 0
- flake8 + isort + black 全過
```

---

## Day-by-Day 工作分解

### Day 1（估 5h）— Audit log 完整鏈

1.1 設計 audit_log schema + 3 partition + ORM model（30 min）
1.2 寫 alembic migration 0005（含 ROW UPDATE/DELETE trigger + STATEMENT TRUNCATE trigger + state_snapshots TRUNCATE trigger 補裝）（90 min）
1.3 alembic upgrade + 表結構 verify（20 min）
1.4 audit_helper.py：`compute_audit_hash` + `append_audit`（45 min）
1.5 test_audit_append_only.py：5 tests（UPDATE / DELETE / TRUNCATE / hash chain / partition routing）（90 min）
1.6 commit Day 1（10 min）

### Day 2（估 6h）— api_keys + rate_limits + 5 memory tables

2.1 設計 api_keys（含 hash, last_4, expires_at, revoked_at）+ rate_limits + ORM models（30 min）
2.2 寫 0006 migration（45 min）
2.3 設計 5 memory tables（system 為全局；其他 4 帶 TenantScopedMixin；session_summary 含 created_at index）+ ORM models（60 min）
2.4 寫 0007 migration（60 min）
2.5 alembic upgrade + 結構 verify（15 min）
2.6 test_api_keys_crud + test_memory_models_crud（90 min）
2.7 commit Day 2（10 min）

### Day 3（估 5h）— Governance 3 表

3.1 設計 approvals（pending/approved/rejected workflow + actor_user_id + reason + payload）（30 min）
3.2 設計 risk_assessments（score 0-100, severity enum, recommendation, blocked bool）（30 min）
3.3 設計 guardrail_events（detector_type, severity, action_taken, payload）+ ORM models（30 min）
3.4 寫 0008 migration + alembic upgrade（60 min）
3.5 test_governance_models_crud（含 approval state machine + risk + guardrail 三段案例）（90 min）
3.6 commit Day 3（10 min）

### Day 4（估 7h）— RLS + middleware + pg_partman

4.1 列 14 表 RLS policy 表（30 min）
4.2 寫 0009 migration（含 14 表 ENABLE RLS + FORCE RLS + 14×2 policies + pg_partman 3 setup）（120 min）
4.3 alembic upgrade + verify policies（30 min）
4.4 platform_layer/middleware/tenant_context.py + `get_db_session_with_tenant` dependency（60 min）
4.5 test_tenant_context middleware（含 missing header / invalid uuid / valid 三案例）（45 min）
4.6 test_rls_enforcement.py（含 set / unset local + 跨 tenant select / insert / update 全 0 leak）（90 min）
4.7 commit Day 4（10 min）

### Day 5（估 5h）— Qdrant abstraction + 紅隊 + closeout

5.1 infrastructure/vector/qdrant_namespace.py（45 min）
5.2 test_qdrant_namespace.py（30 min）
5.3 tests/security/test_red_team_isolation.py（6 攻擊向量）（90 min）
5.4 全套 pytest + alembic cycle 驗收（30 min）
5.5 mypy strict + flake8 + LLM leak grep（20 min）
5.6 progress.md / retrospective.md / checklist 全 [x] / Phase 49 README 更新（55 min）
5.7 commit Day 5 closeout（10 min）

---

## 風險 / 已知不確定

| 風險 | 機率 | 影響 | 對策 |
|------|------|------|------|
| RLS policy 與 ORM relationship eager-load 衝突 | 中 | 中 | 主要用 explicit query；relationship lazy load；test_rls 抓出 |
| pg_partman extension 在 docker `postgres:16-alpine` 預設沒裝 | 中 | 中 | 改 `postgres:16` full image OR 改 dockerfile 補裝；先在 49.3 試，失敗則延後到 49.4 |
| `current_setting('app.tenant_id', true)::uuid` 在 missing setting 時行為（return NULL vs raise）| 低 | 低 | `, true)` 第二參數確保 missing return NULL；policy 用 = 比對 NULL 自動不匹配 = 不 leak |
| 14 表 RLS migration 過大導致 alembic timeout | 低 | 中 | 拆 0009a / 0009b 兩個 migration（preventive） |
| pgcrypto 或 hash chain 計算性能問題 | 低 | 低 | append_audit 寫入路徑只 hash 一次；read 路徑不重算 |
| 紅隊測試 6 向量某個 leak | 中 | 高 | 設計時 defense-in-depth（namespace + payload filter + RLS 三層）|

---

## 引用

- **06-phase-roadmap.md** §Phase 49 / Sprint 49.3 — 範圍權威
- **09-db-schema-design.md** — audit / memory / governance / api_keys schema 權威
- **14-security-deep-dive.md** — RLS / append-only / hash chain / GDPR 權威
- **17-cross-category-interfaces.md** — Contract 9 (HITL ApprovalRequest) / Contract 12 (Tracer)
- **.claude/rules/multi-tenant-data.md** — 三鐵律 + 紅隊測試案例
- **.claude/rules/observability-instrumentation.md** — 範疇 12 埋點
- **.claude/rules/anti-patterns-checklist.md** — AP-3 (cross-directory scattering 避免) / AP-10 (mock vs real)
- **Sprint 49.2 retrospective.md** — Carried-over action items
- **Sprint 49.2 plan + checklist** — 格式 + workflow 範本

---

**狀態**：📋 計劃中，等用戶 approve 才開 branch + code。

**用戶 approve 後執行**：建 `feature/phase-49-sprint-3-rls-audit-memory` branch + Day 1 開工。
