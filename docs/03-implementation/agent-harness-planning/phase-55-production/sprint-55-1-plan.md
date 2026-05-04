# Sprint 55.1 — Business Domain Production Service Layer

> **Sprint Type**: V2 main progress sprint (Phase 55 kickoff — first business-layer production sprint)
> **Owner Categories**: Business Domain (primary; 5 domains under `business_domain/`) / Cat 2 Tools (handler swap) / Infrastructure (DB schema + Alembic migration) / Cat 12 Observability (service-layer span injection) / §Multi-tenant rule (incident table tenant_id NOT NULL + RLS)
> **Phase**: 55 (Production — 5 sprint per 06-roadmap.md but compressed to 2 in V2 closure plan; this is 1/2 toward V2 22/22)
> **Workload**: 5 days (Day 0-4); bottom-up est ~22 hr → calibrated commit **~11 hr** (multiplier **0.50** per AD-Sprint-Plan-2; 3rd reduction after 53.7=1.01 / 54.1=0.69 / 54.2=0.65 → 3-sprint mean 0.78 BELOW [0.85, 1.20] band → lowered 0.55 → 0.50 per 54.2 retrospective Q2 recommendation)
> **Branch**: `feature/sprint-55-1-business-services`
> **Plan Authority**: This document (per CLAUDE.md §Sprint Execution Workflow)
> **Roadmap Source**: 06-phase-roadmap.md §Phase 55 + 08b-business-tools-spec.md (5 domains × 18 tool spec) + 09-db-schema-design.md (incident schema reference) + 10-server-side-philosophy.md §原則 1 (multi-tenant)
> **AD closures (sub-scope)**: AD-Sprint-Plan-2 (multiplier 0.55 → 0.50 first application + 4-sprint validation in retro Q2)

---

## Sprint Goal

Bring `business_domain/` from **mock-only HTTP-backed (Level 1)** to **production-capable service layer (Level 3)** by:

- **US-1**: Add `incident` domain DB schema — new ORM model `Incident` + Alembic migration + tenant_id NOT NULL + 5 indexes; production `IncidentService` (full CRUD: list / get / create / update / close) using async SQLAlchemy
- **US-2**: Add 4 other domains' read-only tool service-layer foundations — `patrol/service.py` (get_results) + `correlation/service.py` (get_related) + `rootcause/service.py` (diagnose) + `audit_domain/service.py` (query_logs); each backed by deterministic data source (DB table OR seeded JSON fixtures); 4 service classes share `BusinessServiceBase` repository pattern
- **US-3**: Introduce `BUSINESS_DOMAIN_MODE` env flag (`mock` | `service`); refactor each `register_*_tools()` to construct mock_executor OR service per flag; `make_default_executor()` reads `settings.BUSINESS_DOMAIN_MODE`; mock pathway unchanged (default `mock` for backwards-compat in PoC)
- **US-4**: Wire `IncidentService` + 4 read-only services through `ServiceFactory` (per 53.6 pattern; reset on test fixture); handler closures call service methods instead of HTTP mock; preserve concurrency_policy + hitl_policy + risk_level (no Cat 2 ToolSpec changes)
- **US-5**: Cat 12 observability — `business_service_span` async ctx manager wraps each service method (3 metrics: business_service_duration_seconds + business_service_calls_total + business_service_errors_total) + AD-Sprint-Plan-2 closure verification + Day 4 retrospective + closeout

Sprint 結束後：(a) `incident` domain 5 tools 全部 production-deployable（DB-backed; tenant_id 強制；GDPR-aware delete via cascade ON DELETE CASCADE）；(b) 4 read-only tools 升 production service layer（mock 仍可用 via flag）；(c) `BUSINESS_DOMAIN_MODE=service` 為 V2 production default；(d) `make_default_executor(mode="service")` 跑通 chat → tool → service → DB 主流量；(e) AD-Sprint-Plan-2 first application data point captured；(f) **V2 進度 20/22 → 21/22 (95%)** — 主進度推進；剩 Phase 55.2 canary deployment 達 V2 22/22 (100%)。

**主流量驗收標準**：
- `pytest backend/tests/integration/business_domain/test_incident_main_flow.py` 跑 e2e: chat endpoint → LLM emits tool_call("mock_incident_create") → ServiceFactory → IncidentService.create() → INSERT row → return JSON → SSE event 含 incident_id
- `BUSINESS_DOMAIN_MODE=service` 環境：5 tools 全走 service path，0 HTTP call to localhost:8001
- `BUSINESS_DOMAIN_MODE=mock` 環境（default for PoC）：行為跟 51.0 一樣，0 regression
- Multi-tenant test: tenant A 創 incident → tenant B 列表查不到（RLS + WHERE tenant_id=$1 強制）
- IncidentService.list() with severity="high" filter: 1 incident matching → 1 row returned
- IncidentService.close() with `resolution=""`: raise ValueError 422（schema validation 不到 service 層）
- 4 read-only services unit test: deterministic input → deterministic output（無 mock HTTP）
- `business_service_duration_seconds` metric emitted with labels {service_name, method, tenant_id, status}
- mypy --strict 0 errors on `business_domain/`
- 6 V2 lints green（特別是 check_cross_category_import：service.py 不可 reach into agent_harness/ private modules）

---

## Background

### V2 進度

- **20/22 sprints (91%)** completed (Phase 49-55 roadmap)
- 54.2 closed (Cat 11 Subagent Orchestration Level 4 + AD-Cat10-Obs-1 closed via verification_span helper; calibration ratio 0.65)
- main HEAD: `b0e7b71a` (Sprint 54.2 closeout PR #81)
- 11 範疇 + 範疇 12 全 Level 4；本 sprint 推進業務領域 layer 從 Level 1 (mock-only) → Level 3 (production service-capable)；V2 主進度 **20/22 → 21/22 (95%)**

### 為什麼 55.1 是 Production Service Layer 而不是 5 domain × 24 tools 從零

User approved Option A (2026-05-04 session)：

1. **mock skeleton 已存在**：Phase 51.0 + 51.1 已建 `business_domain/` 完整 5-domain × 18 tool mock skeleton（mock_executor.py + tools.py + register_all_business_tools + make_default_executor）。Phase 55.1 不需從零建工具
2. **mock_executor.py 設計即「Phase 55 swap target」**：每個 mock_executor module docstring 明說「Phase 55 swap target: PagerDuty / Opsgenie / ServiceNow / D365 / SAP」。本 sprint 是預定的 swap point
3. **22 sprint 壓縮為 V2 22/22 final 2 sprints**：原 06-roadmap.md Phase 55 = 5 sprint，但 V2 closure 已壓縮為 55.1 (production service) + 55.2 (canary deployment)；2 sprint 達 V2 22/22 (100%)
4. **mock pathway 不可破壞**：51.0/51.1 PoC 跑在 mock_url=localhost:8001；BUSINESS_DOMAIN_MODE 讓兩條 path 並存，test 可選擇任一
5. **incident domain 為 production deep-dive**：5 tool 完整 lifecycle (create→update→close) 是 5 domain 中最完整 CRUD；先做 incident 完整 production，其他 4 domain 只升 read-only 即可（避免 sprint 超載）

### 既有結構（Day 0 探勘已 grep 確認）

```
backend/src/business_domain/
├── _register_all.py                                # ✅ register_all_business_tools + make_default_executor (51.0 stable)
├── __init__.py
├── patrol/
│   ├── __init__.py
│   ├── mock_executor.py                            # ✅ HTTP client to localhost:8001 (4 methods: check_servers/get_results/schedule/cancel)
│   └── tools.py                                    # ✅ 4 ToolSpec + register_patrol_tools
├── correlation/
│   ├── mock_executor.py                            # ✅ 3 methods (analyze/find_root_cause/get_related)
│   └── tools.py                                    # ✅ 3 ToolSpec
├── rootcause/
│   ├── mock_executor.py                            # ✅ 3 methods (diagnose/suggest_fix/apply_fix)
│   └── tools.py                                    # ✅ 3 ToolSpec
├── audit_domain/                                   # ⚠️ NOTE: directory name `audit_domain` (not `audit`) to avoid Python keyword collision
│   ├── mock_executor.py                            # ✅ 3 methods (query_logs/generate_report/flag_anomaly)
│   └── tools.py                                    # ✅ 3 ToolSpec
└── incident/
    ├── mock_executor.py                            # ✅ 5 methods (create/update_status/close/get/list) — Phase 55.1 swap target
    └── tools.py                                    # ✅ 5 ToolSpec (3 destructive: create/update_status/close + 2 read-only: get/list)
```

### V2 紀律 9 項對齐確認

1. **Server-Side First** ✅ Service layer 全 server-side；DB-backed；無 client-side state
2. **LLM Provider Neutrality** ✅ `business_domain/` 不 import LLM SDK；不繞過 ChatClient；CI lint check_llm_sdk_leak 強制
3. **CC Reference 不照搬** ✅ 不模仿 PagerDuty/ServiceNow integration 設計；用 V2 SQLAlchemy + service pattern
4. **17.md Single-source** ✅ 不新增 cross-category type；ToolSpec 完全沿用；`BusinessServiceBase` 是 internal base class（非 cross-category contract）
5. **11+1 範疇歸屬** ✅ 全部 service.py 在 `business_domain/{domain}/`；DB models 在 `infrastructure/db/models/business/`；Alembic migration 在 `infrastructure/db/migrations/`；無 AP-3 (Cross-Directory Scattering)
6. **04 anti-patterns** ✅ AP-3 範疇歸屬合規；AP-4 (Potemkin) — 每 service method 必有 unit test；AP-6 (Hybrid Bridge Debt) — `BUSINESS_DOMAIN_MODE` flag 是真實雙模式（PoC + production），不是「為未來預留」；AP-7 N/A (no LLM call); AP-9 N/A (verification 已在 chat 主流量); AP-10 (mock vs real divergence) — flag 強制兩條 path 用同一 service interface
7. **Sprint workflow** ✅ plan → checklist → Day 0 探勘 → code → progress → retro；本文件依 54.2 plan 結構鏡射（13 sections / Day 0-4）
8. **File header convention** ✅ 所有新建 .py / .md 含 Purpose / Category / Scope / Modification History
9. **Multi-tenant rule** 🔴 **CORE FOCUS** — `incidents` 表 tenant_id NOT NULL + 強制 WHERE filter + RLS policy + integration test cross-tenant deny

---

## User Stories

### US-1: Incident Domain DB Schema + ORM Model (Production Foundation)

**As** a Phase 55.1 implementer
**I want** `incidents` table 在 PostgreSQL 中 production-ready — ORM model `Incident` (async SQLAlchemy) + Alembic migration + tenant_id NOT NULL + 5 indexes (PK / tenant_user / severity_status / status_created / closed_at) + RLS policy
**So that** IncidentService.create/list/get/update/close 可以走真實 DB persistence；多租戶隔離 enforced；GDPR delete via tenant CASCADE

**Acceptance**:
- [ ] `infrastructure/db/models/business/incident.py` defines `Incident(Base)` class
- [ ] Columns: `id (UUID PK) / tenant_id (UUID NN FK) / user_id (UUID FK NULL) / title (VARCHAR 512 NN) / severity (Enum NN) / status (Enum NN) / alert_ids (JSONB) / resolution (TEXT) / created_at / updated_at / closed_at (NULL)`
- [ ] 5 indexes per query patterns
- [ ] Alembic migration `XXXX_add_incidents_table.py` with upgrade + downgrade + RLS policy
- [ ] `alembic upgrade head` then `alembic downgrade base` 全程 green
- [ ] CI backend-ci.yml `Alembic upgrade head` + `Alembic downgrade base` step pass

### US-2: IncidentService Production Class (Full CRUD)

**As** a Phase 55.1 implementer
**I want** `business_domain/incident/service.py` 提供 `IncidentService` class — 5 method (`create / list / get / update_status / close`) 全部 async + multi-tenant + 含 audit hook
**So that** Cat 2 ToolHandler 可呼叫 production service 取代 HTTP mock；tenant_id 由 DI 注入；error mapped 為 ToolResult error；IncidentService 不 import Cat 2 私有 module

**Acceptance**:
- [ ] `IncidentService.__init__(*, db: AsyncSession, tenant_id: UUID, tracer: Tracer)`
- [ ] `create(title: str, severity: str, alert_ids: list[str], user_id: UUID | None) -> Incident`：插入 row，severity validate，return ORM
- [ ] `list(severity: str | None, status: str | None, limit: int = 20) -> list[Incident]`：tenant filter + index hit
- [ ] `get(incident_id: UUID) -> Incident | None`：tenant filter；not found → None（caller 決定 404）
- [ ] `update_status(incident_id: UUID, status: str) -> Incident`：tenant filter + RowVersion check
- [ ] `close(incident_id: UUID, resolution: str) -> Incident`：set status=closed + closed_at=NOW() + resolution NN check
- [ ] 12 unit tests (cover all methods + tenant isolation 4 cases + 422 validation)
- [ ] mypy --strict 0 errors

### US-3: 4 Read-Only Domain Service Layer Foundation

**As** a Phase 55.1 implementer
**I want** `patrol/service.py` + `correlation/service.py` + `rootcause/service.py` + `audit_domain/service.py` 各提供 1 read-only method（per domain spec）+ 共享 `BusinessServiceBase` repository abstraction
**So that** 主流量 read-only tool path 可走 service 不走 HTTP；不需建完整 4 domain DB schema（reach 僅 incident table production）；其他 3 domain 用 deterministic seeded fixture data 即可

**Acceptance**:
- [ ] `business_domain/_base.py` 定義 `BusinessServiceBase` (tenant_id + db + tracer fields + audit hook)
- [ ] `patrol/service.py PatrolService.get_results(patrol_id)`：return seeded fixture from JSON file
- [ ] `correlation/service.py CorrelationService.get_related(alert_id, depth=1)`：deterministic graph traversal on seeded data
- [ ] `rootcause/service.py RootCauseService.diagnose(incident_id)`：query Incident table + return canned analysis (從 incident.status 推 root cause)
- [ ] `audit_domain/service.py AuditService.query_logs(time_range, filters)`：query `audit_log` table (existing from 53.4)
- [ ] 8 unit tests (4 services × 2 cases each)

### US-4: BUSINESS_DOMAIN_MODE Flag + ServiceFactory Wiring

**As** a Phase 55.1 implementer
**I want** environment flag `BUSINESS_DOMAIN_MODE` (mock|service) 決定 register_*_tools() 用 mock_executor 還是 service；`make_default_executor()` 讀取 settings；ServiceFactory pattern 提供 per-tenant DB session
**So that** PoC mode 不破壞（default `mock`）；production mode 可切換；test 可 fixture-inject 任一 path

**Acceptance**:
- [ ] `core/config.py Settings.BUSINESS_DOMAIN_MODE: Literal["mock", "service"] = "mock"`
- [ ] 5 `register_*_tools()` 接受新 kwarg `mode: str = "mock"`；mode="service" 時建 service factory；mode="mock" 行為不變
- [ ] `make_default_executor(*, mode: str | None = None)` 讀 settings；overridable
- [ ] `ServiceFactory.get_incident_service(tenant_id)` 返回 IncidentService 實例（lazy；per-request session）
- [ ] BUSINESS_DOMAIN_MODE=mock：CI passes 0 regression（51.0 + 51.1 既有 test 全 green）
- [ ] BUSINESS_DOMAIN_MODE=service：5 incident tool 走 service path; 4 read-only 走 service path
- [ ] 6 integration tests (per-mode + mode switch + ServiceFactory reset fixture per testing.md)

### US-5: Cat 12 Observability + AD-Sprint-Plan-2 Validation + Closeout

**As** a Phase 55.1 implementer
**I want** `business_service_span` async ctx manager 包覆每個 service 方法 (emit duration_seconds histogram + calls_total counter + errors_total counter; labels: service_name / method / tenant_id / status) + Day 4 retrospective Q2 calibration verify (4-sprint window)
**So that** business layer 全埋點同 Cat 11 標準；AD-Sprint-Plan-2 multiplier 0.50 首次驗證 ratio 對 [0.85, 1.20] band

**Acceptance**:
- [ ] `business_domain/_obs.py business_service_span(service_name, method, tenant_id)` async ctx mgr
- [ ] 5 method × 5 service = 25 個 service method 都用 `async with business_service_span(...)`
- [ ] 3 metrics 透過 `Tracer.record_metric()` 呼叫；mock tracer 接到對應 events
- [ ] retrospective.md Q2: actual hr / committed hr → ratio (期望 [0.85, 1.20])；4-sprint window mean re-evaluate；如 < 0.85 → 建議 0.50 → 0.40 (AD-Sprint-Plan-3)；如 ∈ [0.85, 1.20] → 鎖 0.50 為 stable

---

## Technical Specifications

### Architecture: 3-Layer Per Domain

```
┌─────────────────────────────────────────────┐
│ ToolHandler (closure in tools.py)           │  ← unchanged interface
│   - mode="mock"  → mock_executor.method()   │  ← Phase 51.0 path
│   - mode="service" → service.method()       │  ← Phase 55.1 NEW
└─────────────────────────────────────────────┘
                  ↓ (mode=service)
┌─────────────────────────────────────────────┐
│ Service Class (business_domain/{d}/service.py) │
│   - multi-tenant filter (tenant_id)          │
│   - business logic + validation              │
│   - emit business_service_span                 │
└─────────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│ ORM (infrastructure/db/models/business/)    │
│   - Incident (incident table)                │
│   - existing tables for other 4 domains      │
└─────────────────────────────────────────────┘
```

### Multi-tenant Strategy

`Incident` 表必須：
1. tenant_id NOT NULL FK to tenants(id) ON DELETE CASCADE
2. RLS policy `incident_tenant_isolation` USING `tenant_id = current_setting('app.tenant_id')::uuid`
3. 5 indexes 全帶 tenant_id（複合 key 第一個欄位）
4. application-layer query filter：每個 service method 第一行強制 WHERE tenant_id = $1

### File Layout

```
backend/src/
├── business_domain/
│   ├── _base.py                                NEW — BusinessServiceBase
│   ├── _obs.py                                  NEW — business_service_span ctx mgr
│   ├── _register_all.py                        MODIFIED — accept mode kwarg
│   ├── incident/
│   │   ├── service.py                          NEW — IncidentService
│   │   ├── tools.py                            MODIFIED — mode-aware handler
│   │   └── mock_executor.py                    UNCHANGED
│   ├── patrol/
│   │   ├── service.py                          NEW — PatrolService
│   │   └── tools.py                            MODIFIED
│   ├── correlation/
│   │   ├── service.py                          NEW — CorrelationService
│   │   └── tools.py                            MODIFIED
│   ├── rootcause/
│   │   ├── service.py                          NEW — RootCauseService
│   │   └── tools.py                            MODIFIED
│   └── audit_domain/
│       ├── service.py                          NEW — AuditService
│       └── tools.py                            MODIFIED
├── infrastructure/db/models/business/
│   ├── __init__.py                             NEW
│   └── incident.py                             NEW — Incident ORM
├── infrastructure/db/migrations/versions/
│   └── XXXX_add_incidents_table.py             NEW — Alembic migration
└── core/
    └── config.py                                MODIFIED — BUSINESS_DOMAIN_MODE
```

### Cat 12 Observability Pattern (mirror Cat 10 / Cat 11 pattern)

```python
# business_domain/_obs.py
@asynccontextmanager
async def business_service_span(
    *, service_name: str, method: str, tenant_id: UUID, tracer: Tracer | None
) -> AsyncIterator[None]:
    if tracer is None:
        yield
        return
    span = tracer.start_span(
        name=f"business_service.{service_name}.{method}",
        attributes={"service": service_name, "method": method, "tenant_id": str(tenant_id)},
    )
    start = time.monotonic()
    status = "success"
    try:
        yield
    except Exception:
        status = "error"
        tracer.record_metric("business_service_errors_total", 1.0, attributes={"service": service_name, "method": method})
        raise
    finally:
        duration = time.monotonic() - start
        tracer.record_metric("business_service_duration_seconds", duration, attributes={"service": service_name, "method": method, "status": status})
        tracer.record_metric("business_service_calls_total", 1.0, attributes={"service": service_name, "method": method, "status": status})
        span.end()
```

---

## Acceptance Criteria

### Sprint-Wide

- [ ] V2 進度 20/22 → 21/22 (95%)
- [ ] All 6 V2 lints green
- [ ] mypy --strict 0 errors
- [ ] LLM SDK leak: 0
- [ ] Anti-pattern checklist 11 項對齐
- [ ] 4 active CI checks green (Backend CI / V2 Lint / E2E Backend / Frontend E2E chromium)
- [ ] Test count baseline 1351 → ≥ 1395 (≥ +44 new = 12 IncidentService + 8 cross-domain + 8 tool integration + 8 multi-tenant + 8 obs)

### Per-User-Story

詳見 §User Stories acceptance per US.

---

## Day-by-Day Plan

### Day 0 — Setup + Day-0 探勘 + Pre-flight Verify (~1 hr)

- 0.1 Branch + plan + checklist commit
- 0.2 Day-0 探勘 — grep against repo state (verify 5 domain mock layout / Settings location / DB session factory / existing audit_log table from 53.4)
- 0.3 Calibration multiplier pre-read (54.2 ratio 0.65; 3-sprint mean 0.78; lower 0.55→0.50 first application)
- 0.4 Pre-flight verify (pytest baseline / 6 V2 lints baseline)
- 0.5 Day 0 progress.md commit + push

### Day 1 — US-1 Incident DB Schema + ORM Model + Alembic Migration (~3 hr commit)

- 1.1 New `infrastructure/db/models/business/__init__.py` + `incident.py` (Incident ORM)
- 1.2 New Alembic migration `XXXX_add_incidents_table.py`
- 1.3 5 ORM unit tests (insert / query / tenant filter / 422 / cascade delete)
- 1.4 alembic upgrade head + downgrade base verify
- 1.5 mypy + 6 V2 lints green
- 1.6 Day 1 progress.md + commit + push

### Day 2 — US-2 IncidentService Production Class (~3 hr commit)

- 2.1 New `business_domain/incident/service.py` IncidentService (5 methods)
- 2.2 New `business_domain/_base.py` BusinessServiceBase
- 2.3 New `business_domain/_obs.py` business_service_span
- 2.4 12 IncidentService unit tests (CRUD + tenant isolation + 422)
- 2.5 mypy + 6 V2 lints green
- 2.6 Day 2 progress.md + commit + push

### Day 3 — US-3 + US-4 (4 read-only services + BUSINESS_DOMAIN_MODE flag) (~3 hr commit)

- 3.1 New `patrol/service.py` + `correlation/service.py` + `rootcause/service.py` + `audit_domain/service.py`
- 3.2 8 read-only service unit tests
- 3.3 Modify `core/config.py` Settings.BUSINESS_DOMAIN_MODE
- 3.4 Modify 5 `register_*_tools()` accept mode kwarg
- 3.5 Modify `make_default_executor()` read settings
- 3.6 Modify `ServiceFactory` add `get_incident_service` (53.6 reset pattern)
- 3.7 6 integration tests (mode switch + per-mode + ServiceFactory reset)
- 3.8 Day 3 progress.md + commit + push

### Day 4 — US-5 + Retro + Closeout (~2 hr commit)

- 4.1 Wire Cat 12 obs to all 25 service methods
- 4.2 Multi-tenant integration test cross-domain (5 cases)
- 4.3 Main flow e2e test (chat → incident_create → DB row → SSE)
- 4.4 retrospective.md (6 必答題 + AD-Sprint-Plan-2 first-application calibration verify)
- 4.5 Final pytest + 6 V2 lints + LLM SDK leak final verify
- 4.6 Open PR → CI green → solo-dev merge to main
- 4.7 Closeout PR (SITUATION-V2 + CLAUDE.md update to V2 21/22)
- 4.8 Memory update + final push

---

## File Change List

| File | Status | Lines (est) |
|------|--------|-------------|
| `infrastructure/db/models/business/__init__.py` | NEW | ~10 |
| `infrastructure/db/models/business/incident.py` | NEW | ~80 |
| `infrastructure/db/migrations/versions/XXXX_add_incidents_table.py` | NEW | ~120 |
| `business_domain/_base.py` | NEW | ~50 |
| `business_domain/_obs.py` | NEW | ~50 |
| `business_domain/incident/service.py` | NEW | ~200 |
| `business_domain/incident/tools.py` | MODIFIED | +50 |
| `business_domain/patrol/service.py` | NEW | ~80 |
| `business_domain/patrol/tools.py` | MODIFIED | +30 |
| `business_domain/correlation/service.py` | NEW | ~70 |
| `business_domain/correlation/tools.py` | MODIFIED | +30 |
| `business_domain/rootcause/service.py` | NEW | ~80 |
| `business_domain/rootcause/tools.py` | MODIFIED | +30 |
| `business_domain/audit_domain/service.py` | NEW | ~80 |
| `business_domain/audit_domain/tools.py` | MODIFIED | +30 |
| `business_domain/_register_all.py` | MODIFIED | +30 |
| `core/config.py` | MODIFIED | +5 |
| `platform_layer/governance/service_factory.py` | MODIFIED | +30 |
| Tests (~44 new) | NEW | ~800 |
| docs/agent-harness-execution/phase-55/sprint-55-1/{progress,retrospective}.md | NEW | ~400 |

**Total**: ~2,260 source LOC + ~800 test LOC

---

## Dependencies & Risks

### Dependencies (must exist before code starts)

- ✅ Phase 51.0 mock skeleton (5 domain × 18 tool) — verified Day 0
- ✅ Phase 49.2 async SQLAlchemy + Alembic infra — verified Day 0
- ✅ 53.6 ServiceFactory pattern + reset_service_factory autouse fixture — verified Day 0
- ✅ 53.4 audit_log table (used by AuditService.query_logs) — verified Day 0
- ✅ Cat 12 Tracer ABC + record_metric — used by Cat 11 Day 4 (54.2)
- ⚠️ `tenants` table (multi-tenant root) — verify Day 0

### Risk Classes (per sprint-workflow.md §Common Risk Classes)

**Risk Class A (paths-filter vs required_status_checks)**: backend-only sprint → backend-ci will fire (paths include `backend/**`). Frontend E2E required check → must touch `.github/workflows/playwright-e2e.yml` header per AD-CI-5 workaround. Mitigation: Day 4 closeout commit touches workflow header.

**Risk Class B (cross-platform mypy unused-ignore)**: low risk; no new optional dependencies introduced. Mitigation: standard `# type: ignore[X, unused-ignore]` if encountered.

**Risk Class C (module-level singleton across event loops)**: HIGH RELEVANCE — IncidentService accessed via ServiceFactory (53.6 cache). Mitigation: extend `reset_service_factory()` to clear new IncidentService cache; integration `conftest.py` autouse fixture per testing.md §Module-level Singleton Reset Pattern.

### Sprint-specific Risks

| Risk | Mitigation |
|------|-----------|
| Alembic migration downgrade fails on RLS policy DROP | Test downgrade locally Day 1; explicit `DROP POLICY IF EXISTS` |
| BUSINESS_DOMAIN_MODE=mock CI regressions (51.0 tests fail) | Day 3 explicit smoke test mode=mock before mode=service |
| AD-Sprint-Plan-2 first application multiplier 0.50 too aggressive | Already conservative (3-sprint mean 0.78); if ratio < 0.50 → AD-Sprint-Plan-3 next sprint |
| 4 read-only service deterministic data fragility | Service uses **seeded fixtures** OR existing tables (rootcause reads Incident; audit reads audit_log); patrol/correlation use JSON fixtures (deterministic) |

---

## Workload

> **Bottom-up est ~22 hr → calibrated commit ~11 hr (multiplier 0.50)**
> **3-sprint window ratio mean 0.78 BELOW [0.85, 1.20] band** → multiplier reduction 0.55 → 0.50 first application this sprint per 54.2 retrospective Q2 + AD-Sprint-Plan-2

| US | Bottom-up (hr) |
|----|---------------|
| US-1 Incident DB schema + ORM + migration | 4 |
| US-2 IncidentService + base class + obs ctx mgr | 5 |
| US-3 4 read-only domains' service.py | 4 |
| US-4 BUSINESS_DOMAIN_MODE flag + ServiceFactory wiring | 4 |
| US-5 Cat 12 obs wiring + retro + closeout | 5 |
| **Total bottom-up** | **22** |
| **× 0.50 calibrated** | **11** |

Day 4 retrospective Q2 must verify: `actual_total_hr / 11 → ratio` compared to [0.85, 1.20] band; document delta + AD-Sprint-Plan-3 if needed.

---

## Out of Scope

- ❌ Real enterprise integrations (PagerDuty / Opsgenie / ServiceNow / D365 / SAP) — Phase 55.2 canary
- ❌ patrol/correlation domain DB schema (only incident gets table; others use fixtures) — defer to Phase 56+
- ❌ rootcause_apply_fix HIGH-RISK production flow — already requires HITL ALWAYS_ASK; service stub returns "approval_pending"
- ❌ Frontend pages for incident management — Phase 55.2
- ❌ Multi-tenant audit log replication / WORM strict mode — already in 53.3+
- ❌ Refactor 5 domain ToolSpec (risk_level / hitl_policy / etc.) — sealed in 51.1 / 53.3+

---

## AD Carryover Sub-Scope

### AD-Sprint-Plan-2 (calibration multiplier reduction)

**Closure plan**:
1. Sprint 55.1 plan §Workload uses **0.50** (first application)
2. Day 4 retrospective Q2 computes `actual / 11`
3. If ratio ∈ [0.85, 1.20] → close AD-Sprint-Plan-2 ✅; rule 0.50 = stable for Phase 55+
4. If ratio < 0.85 → log AD-Sprint-Plan-3 (next reduction 0.50→0.40)
5. If ratio > 1.20 → log AD-Sprint-Plan-3 (reverse: 0.50→0.55)

---

## Definition of Done

- [ ] All 5 USs acceptance criteria met
- [ ] Test count ≥ 1395 (1351 + 44 new)
- [ ] mypy --strict 0 errors
- [ ] 6 V2 lints green
- [ ] LLM SDK leak: 0
- [ ] alembic upgrade head + downgrade base both green
- [ ] BUSINESS_DOMAIN_MODE=mock 0 regression (51.0 + 51.1 tests pass)
- [ ] BUSINESS_DOMAIN_MODE=service 5 incident tools + 4 read-only services 主流量 e2e green
- [ ] AD-Sprint-Plan-2 closure or escalation logged in retrospective.md
- [ ] PR opened, CI green, merged to main
- [ ] Closeout PR merged
- [ ] SITUATION-V2 + memory + CLAUDE.md updated to V2 21/22 (95%)

---

## References

- 06-phase-roadmap.md §Phase 55
- 08b-business-tools-spec.md §Domain 1-5 (5 domains × 18 tool spec)
- 09-db-schema-design.md §incident table reference
- 10-server-side-philosophy.md §原則 1 Server-Side First + §multi-tenant
- 17-cross-category-interfaces.md §Contract 12 Tracer (used by Cat 12 obs)
- 14-security-deep-dive.md §multi-tenant RLS + GDPR cascade
- .claude/rules/multi-tenant-data.md (3 鐵律 + RLS pattern)
- .claude/rules/observability-instrumentation.md (5 必埋點 + ctx mgr pattern)
- .claude/rules/testing.md §Module-level Singleton Reset Pattern (53.6 ServiceFactory pattern)
- .claude/rules/sprint-workflow.md §Common Risk Classes (3 classes A/B/C)
- Sprint 54.2 plan + retrospective (multiplier 0.55 → 0.50 reasoning)
- Sprint 51.0/51.1 mock skeleton (existing 5 domain × 18 tool implementation)
