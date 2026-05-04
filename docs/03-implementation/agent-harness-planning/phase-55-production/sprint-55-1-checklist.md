# Sprint 55.1 — Business Domain Production Service Layer — Checklist

**Plan**: [sprint-55-1-plan.md](sprint-55-1-plan.md)
**Branch**: `feature/sprint-55-1-business-services`
**Day count**: 5 (Day 0-4) | **Bottom-up est**: ~22 hr | **Calibrated commit**: ~11 hr (multiplier **0.50** per AD-Sprint-Plan-2; **first application** after 53.7=1.01 / 54.1=0.69 / 54.2=0.65 → 3-sprint mean 0.78 BELOW [0.85, 1.20] band → reduce 0.55 → 0.50)

> **格式遵守**：每 Day 同 54.2 結構（progress.md update + sanity + commit + verify CI）。每 task 3-6 sub-bullets（case / DoD / Verify command）。Per AD-Lint-2 (53.7) — 不寫 per-day calibrated hour targets；只寫 sprint-aggregate calibration verify in retro。

---

## Day 0 — Setup + Day-0 探勘 + Pre-flight Verify

### 0.1 Branch + plan + checklist commit
- [x] **Verify on main + clean** ✅ HEAD `b0e7b71a`
- [x] **Create branch + push plan/checklist** ✅ `feature/sprint-55-1-business-services` created
- [x] **Stage + commit plan + checklist + push branch** ✅ commit `3fb6c084` pushed (785 insertions)

### 0.2 Day-0 探勘 — verify plan §Technical Spec assertions against actual repo state ✅

Per AD-Plan-1 (53.7) + feedback_day0_must_grep_plan_assumptions.md — grep each plan claim, not memory.

- [x] **Verify 5 domain mock skeleton intact** ✅ 10 files present
- [x] **Verify _register_all.py + make_default_executor** ✅ `_register_all.py:49,72`
- [x] **Verify Settings location + existing fields** 🚨 **D1**: actual is package `core/config/__init__.py` (not file `core/config.py`); snake_case fields; `business_domain_mode` to add Day 3
- [x] **Verify async SQLAlchemy session factory** ✅ `infrastructure/db/session.py` + `engine.py`
- [x] **Verify existing tenants + audit_log tables** ✅ 11 Alembic migrations (0001 tenants / 0005 audit_log / 0009 RLS)
- [x] **Verify ServiceFactory + reset pattern** ✅ class line 75; reset_service_factory line 215
- [x] **Verify Tracer ABC + record_metric signature** ✅ `observability/_abc.py:32` (class) + `:36` start_span + `:48` record_metric
- [x] **Catalogue D1 in progress.md** ✅ documented; cosmetic fix only (no scope change)

### 0.3 Calibration multiplier pre-read ✅
- [x] **Read 54.2 retrospective Q2** ✅ ratio 0.65; 3-sprint mean 0.78 BELOW band
- [x] **Compute 55.1 bottom-up** ✅ 22 hr × 0.50 = 11 hr commit
- [x] **Document predicted vs banked** ✅ ~10 hr banked from 53.7+54.1+54.2; 0.50 conservative

### 0.4 Pre-flight verify (main green baseline) ✅
- [x] **pytest collect baseline** ✅ **1355 collected** (= 1351 passed + 4 skipped; D2 false-alarm reconciled)
- [x] **6 V2 lints via run_all.py** ✅ **6/6 green** in 0.65s
- [x] **Backend full pytest baseline** ✅ **1351 passed / 4 skipped / 0 fail** in 28.12s
- [x] **mypy --strict baseline** ✅ **0 errors / 255 files**

### 0.5 Day 0 progress.md ✅
- [x] **Create `docs/03-implementation/agent-harness-execution/phase-55/sprint-55-1/progress.md`** ✅ Day 0 entry with 8 verify + D1 + baseline + Day 1 plan
- [x] **Commit + push Day 0** ✅ commit `8632d2eb` pushed (2 commits ahead of main)

---

## Day 1 — US-1 Incident DB Schema + ORM Model + Alembic Migration ✅

### 1.1 New `infrastructure/db/models/business/__init__.py` ✅
- [x] **Create __init__.py** ✅ re-exports `Incident / IncidentSeverity / IncidentStatus`

### 1.2 New `infrastructure/db/models/business/incident.py` ✅
- [x] **Define Incident(Base, TenantScopedMixin) ORM class** ✅ ~180 lines; file header complete
- [x] **Define IncidentSeverity + IncidentStatus Python enums** ✅ str-Enum (LOW/MEDIUM/HIGH/CRITICAL + OPEN/INVESTIGATING/RESOLVED/CLOSED)
- [x] **Define UNIQUE + 2 CHECK + 5 indexes** ✅
  - 🚨 **D2 (convention)**: plan said PG ENUM types; project convention is `String(32) + CHECK constraint` (per 0011_approvals_status_check + Approval pattern). Reverted to convention.
  - UNIQUE (tenant_id, id); CHECK severity / CHECK status
  - 5 indexes: tenant_user / severity_status / status_created / closed_at (partial) / alert_ids (GIN)
- DoD: mypy --strict green ✅; black formatted ✅; flake8 ✅

### 1.3 New Alembic migration `0012_incidents.py` ✅
- [x] **upgrade()** ✅ create_table + ix_incidents_tenant_id + 5 indexes + 2 CHECK + RLS policy
- [x] **downgrade()** ✅ DROP POLICY IF EXISTS + DISABLE RLS + drop_table (cascades indexes)
- [x] **Verify cycle** ✅ `alembic upgrade head` → `downgrade base` → `upgrade head` 全程 green

### 1.4 5 ORM unit tests ✅
- [x] **test_incident_create** ✅
- [x] **test_incident_tenant_filter** ✅
- [x] **test_incident_severity_check_constraint** ✅ (renamed from "_enum_validation"; CHECK constraint pattern)
- [x] **test_incident_status_default_open** ✅
- [x] **test_incident_tenant_cascade_delete** ✅
- DoD: `pytest tests/unit/infrastructure/db/test_incident_model.py -v` → **5 passed in 0.28s** ✅

### 1.5 Day 1 sanity checks ✅
- [x] **mypy --strict** ✅ 0 errors / 258 files (was 255 + 3 new)
- [x] **black + isort + flake8** ✅ all clean
- [x] **6 V2 lints via run_all.py** ✅ 6/6 green in 2.11s
- [x] **Backend full pytest** ✅ **1356 passed / 4 skipped / 0 fail** in 29.31s (= 1351 + 5)
- [x] **LLM SDK leak in models/business/** ✅ 0

### 1.6 Day 1 commit + push + progress.md ✅
- [x] **Stage + commit Day 1 source + tests + alembic migration** ✅ commit `2a9e79fb` (7 files / +630 / -48)
- [x] **Update progress.md** with Day 1 actuals + D2 + D3 fix ✅
- [x] **Push to origin** ✅ on `feature/sprint-55-1-business-services`

---

## Day 2 — US-2 IncidentService Production Class ✅

### 2.1 New `business_domain/_base.py` BusinessServiceBase ✅
- [x] **Define BusinessServiceBase** ✅ ~70 lines; fields (db / tenant_id / tracer); `audit_event()` wraps `append_audit` with tenant binding
- 🚨 **D6 (signature)**: plan said `_audit_hook(operation, resource_id, **extra)`; actual `append_audit` takes `operation`/`resource_type`/`operation_data` as separate kwargs + `user_id` (not `actor_user_id`). Aligned to actual signature.

### 2.2 New `business_domain/_obs.py` business_service_span ✅
- [x] **Define `business_service_span` async ctx manager** ✅ ~70 lines (file header heavy); span-only; SpanCategory.TOOLS
- [x] **3 unit tests** ✅ (noop / TOOLS span emitted / exception propagates) — 3 passed in 0.05s
- 🚨 **D5 (scope)**: plan §US-5 specified 3 metrics emitted. Reverted to span-only matching `verification_span` precedent (54.2 US-5 AD-Cat10-Obs-1). Metric emission deferred to AD-Cat12-Helpers-1 (54.2 retro Q6 carryover). Reason: avoid duplicating MetricEvent construction across 25 service methods; OTel impl provides span timing.

### 2.3 New `business_domain/incident/service.py` IncidentService ✅
- [x] **IncidentService(BusinessServiceBase)** ✅ 5 async methods (create / list / get / update_status / close); ~210 lines
- [x] All methods wrapped `async with business_service_span(...)` ✅
- [x] All queries include `WHERE tenant_id = self.tenant_id` ✅
- [x] `close()` validates resolution ≥ 1 char (whitespace-only also rejected) ✅
- [x] `update_status()` raises ValueError if not in tenant scope ✅
- [x] `create / update_status / close` call `audit_event(...)` ✅
- DoD: mypy strict green ✅; black + isort + flake8 green ✅

### 2.4 12 IncidentService unit tests ✅
- [x] **test_create_returns_incident / _default_severity_high / _emits_audit** ✅
- [x] **test_list_filters_by_severity / _by_status / _pagination_limit** ✅
- [x] **test_get_returns_none_when_not_found / _cross_tenant_returns_none** ✅
- [x] **test_update_status_transitions / _cross_tenant_raises** ✅
- [x] **test_close_sets_closed_at_now / _empty_resolution_raises_value_error** ✅
- DoD: 12 passed in 0.66s (15 total Day 2 with obs tests in 0.71s) ✅

### 2.5 Day 2 sanity checks ✅
- [x] **mypy --strict** ✅ 0 errors / 261 files (was 258 + 3 new)
- [x] **black + isort + flake8** ✅ all clean (1 F401 fixed)
- [x] **6 V2 lints via run_all.py** ✅ 6/6 green in 0.67s
- [x] **Backend full pytest** ✅ **1371 passed / 4 skipped / 0 fail** in 28.70s (= 1356 + 15)
- [x] **LLM SDK leak in business_domain/** ✅ 0

### 2.6 Day 2 commit + push + progress.md
- [ ] **Stage + commit Day 2** (next)
- [ ] **Update progress.md** Day 2 actuals (D4 + D5 + D6 + D7)
- [ ] **Push**

---

## Day 3 — US-3 + US-4 (4 Read-Only Services + BUSINESS_DOMAIN_MODE Flag)

### 3.1 New 4 read-only service.py files

#### 3.1a `business_domain/patrol/service.py PatrolService`
- [ ] **PatrolService.get_results(*, patrol_id: str) -> dict** — read seeded fixture from `business_domain/patrol/_fixtures/patrol_results.json`
- [ ] Fixture contains 5 deterministic patrol_id entries
- [ ] Wrapped with business_service_span

#### 3.1b `business_domain/correlation/service.py CorrelationService`
- [ ] **CorrelationService.get_related(*, alert_id: str, depth: int = 1) -> list[dict]** — deterministic graph traversal on seeded `_fixtures/correlation_graph.json`
- [ ] depth ∈ {1, 2, 3}; raises ValueError otherwise

#### 3.1c `business_domain/rootcause/service.py RootCauseService`
- [ ] **RootCauseService.diagnose(*, incident_id: UUID) -> dict** — read Incident from DB (US-1 table) + return canned analysis dict based on `incident.status`
- [ ] Tenant-filtered query

#### 3.1d `business_domain/audit_domain/service.py AuditService`
- [ ] **AuditService.query_logs(*, time_range: tuple[datetime, datetime], filters: dict | None = None) -> list[dict]** — query existing `audit_log` table (53.4)
- [ ] Tenant-filtered

### 3.2 8 read-only service unit tests
- [ ] PatrolService: 2 cases (existing patrol_id / not-found)
- [ ] CorrelationService: 2 cases (depth=1 / invalid depth raises)
- [ ] RootCauseService: 2 cases (incident found returns analysis / cross-tenant returns ValueError)
- [ ] AuditService: 2 cases (query within range / empty range returns [])
- DoD: 8 passed

### 3.3 Modify `core/config.py` Settings
- [ ] **Add `BUSINESS_DOMAIN_MODE: Literal["mock", "service"] = "mock"`**
- [ ] Update Settings docstring + Modification History
- DoD: env var override works (`BUSINESS_DOMAIN_MODE=service` → settings.BUSINESS_DOMAIN_MODE == "service")

### 3.4 Modify 5 `register_*_tools()` accept mode kwarg
- [ ] Each `register_{domain}_tools(registry, handlers, *, mock_url=DEFAULT_BASE_URL, mode: str = "mock")` — handler closures branch on mode
- [ ] mode="mock": existing 51.0 path (mock_executor)
- [ ] mode="service": new path (service class via ServiceFactory)
- [ ] mode invalid: raise ValueError

### 3.5 Modify `make_default_executor()` read settings
- [ ] **`make_default_executor(*, mock_url=DEFAULT_MOCK_URL, tracer=None, mode: str | None = None)`**
- [ ] If `mode is None`: read `settings.BUSINESS_DOMAIN_MODE`
- [ ] Pass `mode` through to `register_all_business_tools()`

### 3.6 Modify `ServiceFactory` add 5 service getters
- [ ] **`get_incident_service(tenant_id: UUID, db: AsyncSession) -> IncidentService`**
- [ ] **`get_patrol_service(tenant_id) -> PatrolService`** + 3 others
- [ ] **`reset_service_factory()`** clears 5 new caches (per testing.md §Module-level Singleton Reset Pattern)
- [ ] Update `tests/integration/api/conftest.py` autouse fixture (already exists; no change needed if reset_service_factory updated)

### 3.7 6 integration tests
- [ ] **test_mode_mock_unchanged_behavior** — BUSINESS_DOMAIN_MODE=mock, all 18 tools work as 51.0 baseline
- [ ] **test_mode_service_incident_create_persists_to_db** — mode=service, create incident → SELECT verifies row
- [ ] **test_mode_switch_per_test** — autouse fixture allows different mode per test
- [ ] **test_service_factory_reset_isolates_event_loops** — 53.6 pattern verification (no event-loop-closed cascade)
- [ ] **test_make_default_executor_reads_settings** — env var override applies
- [ ] **test_make_default_executor_explicit_mode_overrides_settings** — explicit kwarg wins
- DoD: 6 passed

### 3.8 Day 3 sanity checks
- [ ] **mypy --strict** green
- [ ] **6 V2 lints via run_all.py** green (especially check_cross_category_import: service.py NOT importing agent_harness/ private modules)
- [ ] **Backend full pytest** ≥ 1385 passed (= 1371 + 14 new = 8 services + 6 integration)
- [ ] **51.0 + 51.1 baseline tests pass** (BUSINESS_DOMAIN_MODE=mock regression check) — explicit `pytest tests/unit/business_domain -v` 0 fail
- [ ] **LLM SDK leak** — 0

### 3.9 Day 3 commit + push + progress.md
- [ ] **Stage + commit Day 3**
- [ ] **Update progress.md** Day 3 actuals
- [ ] **Push**

---

## Day 4 — US-5 Cat 12 Obs + Retro + Closeout

### 4.1 Verify Cat 12 obs wired to all 25 service methods
- [ ] **Audit grep**: `grep -c "business_service_span" backend/src/business_domain/*/service.py`
- [ ] DoD: each service.py has ≥ 1 `business_service_span` per method (incident=5, patrol=1, correlation=1, rootcause=1, audit_domain=1 = 9 in 5 files; remaining 16 from incident's create/list/get/update_status/close detailed metrics)
- [ ] Adjust expectation: minimum is **9 wraps** for 1 method per service + incident's 5 methods all wrapped

### 4.2 Multi-tenant integration tests (cross-domain)
- [ ] **test_incident_create_isolates_by_tenant** — tenant A creates → tenant B list() returns empty
- [ ] **test_rootcause_diagnose_isolates_by_tenant** — RootCauseService respects tenant_id
- [ ] **test_audit_query_isolates_by_tenant**
- [ ] **test_rls_policy_enforced_at_db_layer** — SET LOCAL app.tenant_id then SELECT incidents → only own rows visible
- [ ] **test_cross_tenant_404** — GET /incidents/{id} as wrong tenant → 404 (hide existence)
- DoD: 5 passed

### 4.3 Main flow e2e test
- [ ] **test_chat_to_incident_create_persists_to_db** (NEW)
  - POST /api/v1/chat with prompt forcing tool_call(mock_incident_create) [BUSINESS_DOMAIN_MODE=service]
  - Verify SSE stream contains tool_call_completed event
  - Verify INSERT row in incidents table with correct tenant_id
  - Verify tracer.record_metric called for business_service_duration_seconds
- DoD: e2e green; ~1 test added

### 4.4 retrospective.md
- [ ] **Q1**: Sprint goal achievement summary
- [ ] **Q2**: Calibration verify — actual_total_hr vs committed 11 hr → ratio
  - if [0.85, 1.20]: close AD-Sprint-Plan-2 ✅
  - if < 0.85: log AD-Sprint-Plan-3 (0.50 → 0.40)
  - if > 1.20: log AD-Sprint-Plan-3 (0.50 → 0.55)
- [ ] **Q3**: Drift findings catalogue (D1, D2, ...)
- [ ] **Q4**: V2 紀律 9 項 review
- [ ] **Q5**: Sprint 55.2 candidate scope (canary deployment / real enterprise integration / SaaS Stage 0 cutover prep)
- [ ] **Q6**: Open AD list (any new ones logged)

### 4.5 Final pytest + lints + LLM SDK leak final verify
- [ ] **Backend full pytest** ≥ 1395 passed (= 1351 + 44 new)
- [ ] **mypy --strict** green
- [ ] **6 V2 lints** green
- [ ] **LLM SDK leak** — 0
- [ ] **alembic upgrade head + downgrade base** both green

### 4.6 Open PR + CI green + solo-dev merge
- [ ] **Push final commit + open PR**
  - Title: `feat(business_domain, sprint-55-1): production service layer + BUSINESS_DOMAIN_MODE flag + V2 21/22`
  - PR body: link plan + checklist + retrospective; list 5 USs + 44 new tests
- [ ] **Wait CI green** (5 active checks: backend-ci / V2 Lint / E2E Backend / E2E Summary / Frontend E2E chromium headless)
  - Frontend E2E required → touch `.github/workflows/playwright-e2e.yml` header per AD-CI-5 if needed
- [ ] **Solo-dev normal merge to main** (review_count=0; no temp-relax needed since 53.2 policy)

### 4.7 Closeout PR
- [ ] **Branch `chore/sprint-55-1-closeout`**
- [ ] **Update SITUATION-V2-SESSION-START.md** §8 + §9 (V2 21/22 = 95%)
- [ ] **Update CLAUDE.md** L48-50 V2 progress + main HEAD
- [ ] **Touch backend-ci.yml header** (paths-filter workaround for docs-only PR)
- [ ] **Touch playwright-e2e.yml header** (Frontend E2E required check)
- [ ] **Open closeout PR + merge**

### 4.8 Memory update + final push
- [ ] **Create `memory/project_phase55_1_business_services.md`**
- [ ] **Update `memory/MEMORY.md`** index
- [ ] **Verify main HEAD** is closeout PR merge
- [ ] **Verify working tree clean**
- [ ] **Delete merged branches** (feature + chore)
