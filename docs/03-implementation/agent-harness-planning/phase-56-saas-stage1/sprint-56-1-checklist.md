# Sprint 56.1 — SaaS Stage 1 Foundation: Backend Tenant Lifecycle + Feature Flags + RLS Hardening — Checklist

**Plan**: [sprint-56-1-plan.md](sprint-56-1-plan.md)
**Branch**: `feature/sprint-56-1-saas-tenant-foundation`
**Day count**: 5 (Day 0-4) | **Bottom-up est**: ~31 hr | **Calibrated commit**: ~17 hr (multiplier **0.55** per AD-Sprint-Plan-4 scope-class matrix `large multi-domain` first application; reserved 0.50-0.55 band, picking 0.55 mid-band)

> **格式遵守**: 每 Day 同 55.2 結構(progress.md update + sanity + commit + verify CI)。每 task 3-6 sub-bullets(case / DoD / Verify command)。Per AD-Lint-2 (53.7) — 不寫 per-day calibrated hour targets;只寫 sprint-aggregate calibration verify in retro. Per AD-Plan-3 promoted (55.6) — Day 0 兩-prong 探勘(Path Verify + Content Verify)是 mandatory.

---

## Day 0 — Setup + Day-0 兩-prong 探勘 + Pre-flight Verify

### 0.1 Branch + plan + checklist commit
- [ ] **Verify on main + clean** — `git status --short` empty + HEAD `08c57e8d`(post-PR #96 triage cleanup)
- [ ] **Create branch + push plan/checklist** — `git checkout -b feature/sprint-56-1-saas-tenant-foundation`
- [ ] **Stage + commit plan + checklist + push branch** — commit msg `chore(docs, sprint-56-1): plan + checklist for Phase 56.1 SaaS Stage 1 foundation`

### 0.2 Day-0 兩-prong 探勘 — verify plan §Technical Spec assertions against actual repo state

Per AD-Plan-3 promoted (55.6) — Prong 1 Path Verify + Prong 2 Content Verify;catalogue D-findings.

**Prong 1: Path Verify (existence checks)**
- [ ] **Verify `infrastructure/db/models/tenant.py` exists?** — Glob check;若已存在 → US-1 改 enhance 不是 create → catalogue as D1 + plan §Risks update
- [ ] **Verify `core/feature_flags.py` exists?** — Glob check (expect: not exist)
- [ ] **Verify `platform_layer/tenant/` directory exists?** — Glob check (expect: not exist; new package)
- [ ] **Verify `api/v1/admin/` directory + router exists?** — Glob check;若不存在,US-1 + US-3 需建 router base
- [ ] **Verify `config/tenant_plans.yml` exists?** — Glob check (expect: not exist)
- [ ] **Verify `scripts/lint/check_rls_policies.py` exists?** — Glob check (expect: not exist; 8th V2 lint)
- [ ] **Verify Alembic head version** — `alembic heads` → confirm 0013 from 55.3 AD-Hitl-7 hitl_policies (next migration = 0014)
- [ ] **Verify existing `tenants` table** — `grep -rn "class Tenant" infrastructure/db/models/` + `grep -rn "tenants" infrastructure/db/alembic/versions/` → if existing, scope 收斂為 enhance

**Prong 2: Content Verify (semantic checks)**
- [ ] **Verify 53.x identity infrastructure roles/users ORM** — `grep -rn "class Role\|class User" infrastructure/db/models/` confirm exists with expected columns
- [ ] **Verify 53.4 governance HITLPolicy + RiskPolicy** — `grep -rn "class HITLPolicy\|class RiskPolicy" platform_layer/governance/` confirm exists for ProvisioningWorkflow step 2.3 to seed
- [ ] **Verify 55.3 AD-Hitl-7 DBHITLPolicyStore exists** — `grep -rn "class DBHITLPolicyStore" platform_layer/governance/` (per 55.3 AD-Hitl-7 closure)
- [ ] **Verify 53.4 AuditLogger interface for feature_flag override audit** — `grep -rn "class AuditLogger\|def log_audit" platform_layer/governance/` confirm reusable interface
- [ ] **Verify chat handler current Depends chain** — `grep -n "def chat\|@router.post.*chat" api/v1/chat/handler.py`; document current `Depends` list (db / tenant / tracer)
- [ ] **Verify 55.1 BusinessServiceFactory pattern as reference** — `grep -n "class BusinessServiceFactory" business_domain/_service_factory.py` for per-request DI pattern (we mirror in tenant lifecycle)
- [ ] **Verify Cat 12 Tracer + tracer factory** — `grep -rn "def get_tracer\|class Tracer" platform_layer/observability/` for tenant lifecycle span emission

**Catalogue findings**
- [ ] **Catalogue all D-findings in progress.md** — format `D{N}` ID + Finding + Implication;link to plan §Risks update if scope shift > 20%

### 0.3 Calibration multiplier pre-read
- [ ] **Read 55.6 retrospective Q2** — confirm 8-sprint window 4/8 in-band; medium-backend mean 1.03 (2-data-point); large multi-domain has no prior data points
- [ ] **Confirm AD-Sprint-Plan-4 scope-class matrix** — `large multi-domain` band 0.50-0.55; this sprint picks 0.55 mid-band (per user choice 2026-05-05)
- [ ] **Compute 56.1 bottom-up** — 31 hr × 0.55 = 17.05 ≈ 17 hr commit
- [ ] **Document predicted vs banked** — first application of `large multi-domain`; no banking carryover; record baseline data point this sprint

### 0.4 Pre-flight verify (main green baseline)
- [ ] **pytest collect baseline** — expect `1463 collected` (per 55.6 closeout main HEAD `08c57e8d`)
- [ ] **7 V2 lints via run_all.py** — `python scripts/lint/run_all.py` → 7/7 green
- [ ] **Backend full pytest baseline** — `python -m pytest` → 1463 passed / 4 skipped / 0 fail
- [ ] **mypy --strict baseline** — `mypy backend/src --strict` → 0 errors
- [ ] **LLM SDK leak baseline** — `grep -rn "^(from |import )(openai|anthropic|agent_framework)" backend/src/agent_harness backend/src/business_domain backend/src/platform_layer backend/src/core` → 0

### 0.5 Day 0 progress.md
- [ ] **Create `docs/03-implementation/agent-harness-execution/phase-56/sprint-56-1/progress.md`** — Day 0 entry with探勘 findings + baseline + Day 1 plan + scope shifts (if any)
- [ ] **Commit + push Day 0** — commit msg `docs(sprint-56-1): Day 0 progress + 兩-prong 探勘 baseline`

---

## Day 1 — US-1 Tenant Provisioning API + State Machine

### 1.1 Tenant ORM model
- [ ] **Create `infrastructure/db/models/tenant.py`** (or enhance existing per Day 0 D-finding) — `Tenant` class with columns(id UUID PK / name / state Enum / plan Enum / provisioning_progress JSONB / onboarding_progress JSONB / created_at / updated_at)
- [ ] **Define `TenantState` Enum** — REQUESTED / PROVISIONING / PROVISION_FAILED / ACTIVE / SUSPENDED / ARCHIVED
- [ ] **Define `TenantPlan` Enum** — ENTERPRISE only(future-proof for Stage 2)
- [ ] **Add file header docstring** — Purpose / Category / Created / Modification History
- DoD: mypy --strict green; black + isort + flake8 green
- Verify: `python -c "from infrastructure.db.models.tenant import Tenant, TenantState, TenantPlan; print('OK')"`

### 1.2 Alembic 0014 migration (tenants table)
- [ ] **Create `infrastructure/db/alembic/versions/0014_*.py`** — auto-generate via `alembic revision --autogenerate -m "Phase 56.1 tenants + feature_flags + RLS hardening"`
- [ ] **Manual review migration script** — confirm tenants table + indexes(state / created_at)+ RLS policy(no tenant_id since Tenant table itself is registry)
- [ ] **Test up + down migration** — `alembic upgrade head` + `alembic downgrade -1` + `alembic upgrade head`
- DoD: alembic cycle clean
- Verify: `alembic upgrade head && alembic downgrade base && alembic upgrade head`

### 1.3 TenantLifecycle state machine
- [ ] **Create `platform_layer/tenant/__init__.py`** — package marker
- [ ] **Create `platform_layer/tenant/lifecycle.py`** — `TenantLifecycle` class with `transition(tenant_id, new_state) -> Tenant`
- [ ] **Define VALID_TRANSITIONS dict** — 6 valid transitions(per plan §Architecture state machine diagram)
- [ ] **Raise IllegalTransitionError** for invalid transitions
- [ ] **Audit log on every transition** — reuse 53.4 AuditLogger
- DoD: mypy strict green; lints green
- Verify: `python -m pytest backend/tests/unit/platform_layer/tenant/test_lifecycle.py -v`

### 1.4 ProvisioningWorkflow 8-step
- [ ] **Create `platform_layer/tenant/provisioning.py`** — `ProvisioningWorkflow` class with `run(tenant_id) -> Tenant`
- [ ] **Implement 8 sub-steps** — create_tenant_record(API done) / seed_default_roles / seed_default_policies(HITL+Risk) / qdrant_namespace_stub / system_memory_seed_stub / create_first_admin_user / generate_api_key / emit_welcome_notification_stub
- [ ] **Each step exception-safe** — failure transitions to PROVISION_FAILED + audit log + raise
- [ ] **Idempotent retry** — re-run from PROVISION_FAILED skips already-completed steps
- [ ] **Cat 12 obs span per step** — `async with category_span("tenant_provisioning_step", attrs={step}):`
- DoD: mypy strict green
- Verify: `python -m pytest backend/tests/unit/platform_layer/tenant/test_provisioning.py -v`

### 1.5 admin tenants API endpoint
- [ ] **Create `api/v1/admin/__init__.py`** (or modify existing) — admin router base
- [ ] **Create `api/v1/admin/tenants.py`** — `POST /api/v1/admin/tenants` endpoint
- [ ] **Pydantic schemas** — `TenantCreateRequest(name, plan='enterprise', admin_email)` + `TenantCreateResponse(tenant_id, state='provisioning', estimated_ready_in_seconds)`
- [ ] **Admin auth dependency** — reuse 53.x admin role check
- [ ] **Trigger ProvisioningWorkflow async** — return 201 Created with provisioning state
- [ ] **Update file header Modification History**
- DoD: mypy strict green; lints green
- Verify: `python -m pytest backend/tests/integration/api/test_admin_tenants.py -v`

### 1.6 8 unit + 4 integration tests
**Unit tests (state machine)**
- [ ] **test_lifecycle_requested_to_provisioning_valid** — happy path
- [ ] **test_lifecycle_provisioning_to_active_valid** — happy path
- [ ] **test_lifecycle_active_to_suspended_valid**
- [ ] **test_lifecycle_suspended_to_active_valid**
- [ ] **test_lifecycle_active_to_archived_valid**
- [ ] **test_lifecycle_provisioning_to_provision_failed_valid**
- [ ] **test_lifecycle_archived_to_active_illegal** — IllegalTransitionError
- [ ] **test_lifecycle_active_to_requested_illegal** — IllegalTransitionError

**Integration tests (provisioning workflow)**
- [ ] **test_provisioning_full_happy_path** — POST creates tenant → 8 steps complete → state=provisioning(awaits onboarding to active)
- [ ] **test_provisioning_step_failure_transitions_to_provision_failed** — mock step 2.7 (API key gen) fail → state=provision_failed + audit log
- [ ] **test_provisioning_retry_from_provision_failed** — retry resumes from failed step
- [ ] **test_provisioning_archived_tenant_cannot_reactivate_directly** — archived → active rejected; must go via reactivate explicit path

DoD: 12 tests pass < 5s

### 1.7 Day 1 sanity checks
- [ ] **mypy --strict** — 0 errors
- [ ] **black + isort + flake8** — clean
- [ ] **7 V2 lints via run_all.py** — 7/7 green
- [ ] **Backend full pytest** — 1463 + 12 = 1475 passed
- [ ] **LLM SDK leak in platform_layer/** — 0

### 1.8 Day 1 commit + push + progress.md
- [ ] **Stage + commit Day 1 source + tests + Alembic** — commit msg `feat(platform-tenant, sprint-56-1): tenant ORM + state machine + provisioning workflow + admin API (US-1)`
- [ ] **Update progress.md** with Day 1 actuals + drift findings if any
- [ ] **Push to origin**

---

## Day 2 — US-2 Plan Template + US-3 Onboarding API (start)

### 2.1 Plan template config + loader
- [ ] **Create `config/tenant_plans.yml`** — enterprise tier definition(quota + features + mcp_servers per plan §Plan Template L420-441)
- [ ] **Create `platform_layer/tenant/plans.py`** — `PlanLoader` class with `get_plan(plan_name='enterprise') -> Plan`
- [ ] **In-memory cache** after first load; idempotent reload
- [ ] **Pydantic Plan model** — quota / features / mcp_servers fields with validation
- DoD: mypy strict green
- Verify: `python -c "from platform_layer.tenant.plans import PlanLoader; print(PlanLoader().get_plan('enterprise'))"`

### 2.2 QuotaEnforcer middleware
- [ ] **Create `platform_layer/tenant/quota.py`** — `QuotaEnforcer` FastAPI dependency
- [ ] **Redis daily counter** — INCR atomic + TTL 24h(reset midnight UTC)
- [ ] **Per-tenant tracking** — `quota:tenant_id:tokens:YYYY-MM-DD` key pattern
- [ ] **Quota exceeded raise HTTPException(429)** — clear error message + retry-after header
- [ ] **Increment counter post-LLM-call** — wrapper utility for chat handler
- DoD: mypy strict green; Redis fakeredis mock for tests
- Verify: `python -m pytest backend/tests/unit/platform_layer/tenant/test_quota.py -v`

### 2.3 Chat endpoint quota integration
- [ ] **Modify chat endpoint** — add `quota: QuotaEnforcer = Depends(get_quota_enforcer)` after current Depends chain
- [ ] **Pre-call quota check** — `quota.check(tenant_id)` before LLM call;raise 429 if exceeded
- [ ] **Post-call increment** — `quota.increment(tenant_id, tokens_used)` after LLM call
- [ ] **Update file header Modification History**
- DoD: existing 53.6 production HITL tests still pass
- Verify: `python -m pytest backend/tests/integration/api/test_chat_quota.py -v`

### 2.4 OnboardingTracker (US-3 part 1: backend logic)
- [ ] **Create `platform_layer/tenant/onboarding.py`** — `OnboardingTracker` with 6 valid steps
- [ ] **Define VALID_STEPS list** — company_info / plan_selected / memory_uploaded / sso_configured / users_invited / health_check(per 15-saas-readiness §Onboarding Wizard L312-335)
- [ ] **`advance(tenant_id, step, payload) -> dict`** — updates tenants.onboarding_progress JSONB
- [ ] **`is_complete(tenant_id) -> bool`** — all 6 steps done
- [ ] **Trigger transition to ACTIVE** when 6/6 complete + health check pass(US-3 part 2 health check on Day 3)
- DoD: mypy strict green
- Verify: `python -m pytest backend/tests/unit/platform_layer/tenant/test_onboarding.py -v`

### 2.5 6 unit US-2 + 2 unit US-3
**US-2 (6 tests)**
- [ ] **test_plan_loader_loads_enterprise_tier** — basic load + cache
- [ ] **test_plan_loader_unknown_plan_raises** — ValueError or KeyError
- [ ] **test_quota_enforcer_within_limit** — passes through
- [ ] **test_quota_enforcer_exceeded_raises_429** — HTTPException(429)
- [ ] **test_quota_enforcer_resets_at_midnight** — TTL behavior
- [ ] **test_quota_enforcer_multi_tenant_isolation** — tenant A counter independent of B

**US-3 (2 tests)**
- [ ] **test_onboarding_tracker_advance_step** — JSONB update
- [ ] **test_onboarding_tracker_invalid_step_raises** — step not in VALID_STEPS

DoD: 8 tests pass < 2s

### 2.6 Day 2 sanity checks
- [ ] **mypy --strict** — 0 errors
- [ ] **black + isort + flake8** — clean
- [ ] **7 V2 lints** — 7/7 green
- [ ] **Backend full pytest** — 1475 + 8 = 1483 passed
- [ ] **53.6 production HITL regression** — no regression
- [ ] **LLM SDK leak** — 0

### 2.7 Day 2 commit + push + progress.md
- [ ] **Stage + commit Day 2** — commit msg `feat(platform-tenant, sprint-56-1): plan template enforcement + onboarding tracker (US-2 + US-3 part 1)`
- [ ] **Update progress.md** with Day 2 actuals
- [ ] **Push to origin**

---

## Day 3 — US-3 Onboarding API (finish) + US-4 Feature Flags

### 3.1 Onboarding API endpoints
- [ ] **Add `GET /api/v1/admin/tenants/{id}/onboarding-status`** — Pydantic response with completed_steps / pending_steps / health_check
- [ ] **Add `POST /api/v1/admin/tenants/{id}/onboarding/{step}`** — accepts payload per step
- [ ] **Step validation** — return 400 if invalid step name
- [ ] **Auto-transition trigger** — when 6/6 complete + health check pass → state=ACTIVE
- [ ] **Update file header Modification History**
- DoD: mypy strict green
- Verify: `python -m pytest backend/tests/integration/api/test_admin_onboarding.py -v`

### 3.2 Health check 6-points
- [ ] **DB connection check** — `SELECT 1`
- [ ] **Redis ping** — fakeredis-aware
- [ ] **Qdrant ping stub** — Phase 56.x integrate;此 sprint return True placeholder
- [ ] **Sample LLM call (adapter ping)** — minimal `chat(messages=[{role: 'user', content: 'ping'}], max_tokens=5)` via Cat 6 adapter
- [ ] **First admin user exists query** — verify users table has user with admin role for this tenant
- [ ] **API key valid query** — verify api_keys table has entry for this tenant
- [ ] **Each check timeout 5s** — overall 30s budget
- DoD: mypy strict green
- Verify: `python -m pytest backend/tests/unit/platform_layer/tenant/test_health_check.py -v`

### 3.3 3 integration US-3 tests
- [ ] **test_onboarding_full_6_step_flow** — provision tenant → 6 POST advance → state transitions to ACTIVE
- [ ] **test_onboarding_partial_status_query** — GET status returns partial progress
- [ ] **test_onboarding_health_check_failure_blocks_active** — health check fails → state remains PROVISIONING + log

DoD: 3 tests pass < 5s

### 3.4 FeatureFlag ORM model + Alembic migration extension
- [ ] **Create `infrastructure/db/models/feature_flag.py`** — `FeatureFlag` class(name PK / default_enabled / tenant_overrides JSONB / description / created_at / updated_at)
- [ ] **Extend Alembic 0014 (or create 0015)** — add feature_flags table
- [ ] **Update file header Modification History**
- DoD: alembic up + down clean
- Verify: `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`

### 3.5 FeatureFlagsService
- [ ] **Create `core/feature_flags.py`** — `FeatureFlagsService` class
- [ ] **`is_enabled(flag_name, tenant_id=None, user_id=None) -> bool`** — default → tenant override → return
- [ ] **`set_tenant_override(flag_name, tenant_id, enabled, actor_user_id) -> None`** — writes audit log via 53.4 AuditLogger
- [ ] **`seed_defaults() -> None`** — idempotent;startup hook
- [ ] **In-memory cache per-tenant** — invalidate on `set_tenant_override`
- [ ] **Default flags seeded** — thinking_enabled / verification_enabled / llm_caching_enabled / pii_masking all = True
- DoD: mypy strict green
- Verify: `python -m pytest backend/tests/unit/core/test_feature_flags.py -v`

### 3.6 5 unit US-4 + 1 integration US-4
**Unit (5)**
- [ ] **test_feature_flag_default_lookup** — flag not overridden returns default
- [ ] **test_feature_flag_tenant_override_takes_precedence** — override returned over default
- [ ] **test_feature_flag_set_override_writes_audit** — AuditLogger called
- [ ] **test_feature_flag_cache_invalidate_on_set** — second is_enabled call sees new value
- [ ] **test_feature_flag_seed_defaults_idempotent** — running twice doesn't error or duplicate

**Integration (1)**
- [ ] **test_chat_handler_thinking_enabled_per_tenant_override** — tenant A overrides thinking_enabled=False;chat handler queries returns False;thinking not invoked

DoD: 6 tests pass < 3s

### 3.7 Day 3 sanity checks
- [ ] **mypy --strict** — 0 errors
- [ ] **7 V2 lints** — 7/7 green(check_cross_category_import: feature_flags 在 core/ 是合法 cross-layer)
- [ ] **Backend full pytest** — 1483 + 6 + 3 = 1492 passed
- [ ] **53.6 production HITL regression** — no regression
- [ ] **LLM SDK leak** — 0

### 3.8 Day 3 commit + push + progress.md
- [ ] **Stage + commit Day 3** — commit msg `feat(platform-tenant, core, sprint-56-1): onboarding API + health check + feature flags (US-3 part 2 + US-4)`
- [ ] **Update progress.md** with Day 3 actuals
- [ ] **Push to origin**

---

## Day 4 — US-5 RLS Hardening + Closeout Ceremony

### 4.1 check_rls_policies.py 8th V2 lint
- [ ] **Create `scripts/lint/check_rls_policies.py`** — scans `infrastructure/db/models/*.py` for ORM tables
- [ ] **Per-table check** — RLS enabled? / tenant_id column exists? / tenant_id NOT NULL? / tenant_id index?
- [ ] **Output report format** — JSON or table;exit code non-zero if gaps
- [ ] **Whitelist for legitimate non-multi-tenant tables** — Tenant / FeatureFlag / Alembic version / etc(global tables)
- DoD: lint script runs clean on green codebase
- Verify: `python scripts/lint/check_rls_policies.py`

### 4.2 RLS audit report
- [ ] **Create `docs/03-implementation/agent-harness-execution/phase-56/sprint-56-1/rls-audit.md`** — list every business table + status
- [ ] **Identify gaps** — table-by-table report;count must be 0 for new tables;document existing gaps from V2 baseline
- [ ] **Document fix plan** — for each gap, Alembic migration step

### 4.3 Alembic RLS gap fixes
- [ ] **Extend Alembic 0014 (or create 0015)** — RLS gap fixes per audit report
- [ ] **Per-table** — `ALTER TABLE … ENABLE ROW LEVEL SECURITY;` + `CREATE POLICY tenant_isolation_<table> ON <table> USING (tenant_id = current_setting('app.tenant_id')::uuid);`
- [ ] **tenant_id index where missing** — `CREATE INDEX IF NOT EXISTS idx_<table>_tenant_id ON <table>(tenant_id);`
- [ ] **Test up + down migration** — alembic cycle clean
- DoD: alembic up + down clean

### 4.4 8 V2 lint orchestrator update
- [ ] **Modify `scripts/lint/run_all.py`** — add `check_rls_policies.py` to the 7-script orchestrator → 8 scripts
- [ ] **Update CI workflow** — `.github/workflows/v2-lints.yml` includes new script(if not already auto-discovered by run_all)
- [ ] **Update file header Modification History**
- DoD: `python scripts/lint/run_all.py` → 8/8 green

### 4.5 RLS integration test
- [ ] **test_rls_set_local_enforcement_no_tenant_blocks** — query without `SET LOCAL app.tenant_id` → 0 rows returned
- [ ] **test_rls_set_local_enforcement_correct_tenant_returns** — `SET LOCAL app.tenant_id = '...'` → returns scoped rows
- [ ] **test_rls_set_local_cross_tenant_blocked** — tenant A SET LOCAL → tenant B's rows invisible

DoD: 3 tests pass < 5s

### 4.6 Multi-tenant integration test cross-domain
- [ ] **test_full_lifecycle_multi_tenant_isolation** — provision tenant A and B concurrently → onboarding 各 6-step → both reach ACTIVE → quota counters independent → feature flags overrides independent
- [ ] **test_audit_chain_after_lifecycle_ops** — audit log integrity preserved across tenant lifecycle ops

DoD: 2 tests pass < 10s

### 4.7 Final pytest + lints + LLM SDK leak final verify
- [ ] **Backend full pytest** — ≥ 1500 (target: 1463 + 37 new = 1500;allow over)
- [ ] **mypy --strict** — 0 errors
- [ ] **8 V2 lints** — 8/8 green
- [ ] **LLM SDK leak** — 0
- [ ] **Alembic upgrade head + downgrade base** — 0014/0015 cycle still green

### 4.8 retrospective.md (6 必答)
- [ ] **Q1** Sprint goal achievement — 5 USs all closed?Phase 56-58 SaaS Stage 1 1/3 reached?
- [ ] **Q2** Calibration verify — `actual_total_hr / 17` → ratio (期望 [0.85, 1.20]);record `large multi-domain` baseline 0.55;if < 0.85 → AD-Sprint-Plan-5(0.55→0.45);if > 1.20 → AD-Sprint-Plan-5(0.55→0.65);if ∈ band → 鎖 0.55 stable for Phase 56.2 + 56.3
- [ ] **Q3** D-findings drift catalogue — Day 0 兩-prong 探勘 + Day 1-3 drift summary
- [ ] **Q4** V2 紀律 9 項 review — confirm all 9 still green at Phase 56.1 closure;log AD-Phase56-Roadmap-Conflict for cleanup in 56.x audit cycle
- [ ] **Q5** Phase 56.1 summary + Phase 56.2 readiness — Phase 56.2 candidate scope confirmed (SLA Monitor + Cost Ledger + Citus PoC + Compliance partial); user will approve Phase 56.2 scope after this sprint
- [ ] **Q6** Solo-dev policy validation — solo-dev merge worked? CI green via paths-filter-retired pattern?

### 4.9 Open PR + CI green + solo-dev merge
- [ ] **Push final commit + open PR** — PR title `feat(platform-tenant, core, sprint-56-1): SaaS Stage 1 foundation — tenant lifecycle + feature flags + RLS hardening`
- [ ] **Wait CI green** — 5 active checks (Backend CI / V2 Lint / E2E Backend / E2E Summary / Frontend E2E chromium)
- [ ] **Solo-dev normal merge to main** — squash merge

### 4.10 Closeout PR (Phase 56.1 ceremony)
- [ ] **Branch `chore/sprint-56-1-closeout`**
- [ ] **Update SITUATION-V2-SESSION-START.md** — §9 milestones row + Last Updated + Update history (Phase 56.1 closed; SaaS Stage 1 1/3 progress)
- [ ] **Update CLAUDE.md** — V2 status block "V2 重構完成 + Phase 56-58 SaaS Stage 1 進度 1/3"
- [ ] **Open closeout PR + merge** — solo-dev normal merge

### 4.11 Memory snapshot + final push
- [ ] **Create `memory/project_phase56_1_saas_foundation.md`** — Sprint 56.1 summary
- [ ] **Update `memory/MEMORY.md`** index — entry for new memory file
- [ ] **Verify main HEAD + working tree clean + delete merged branches** — `git status --short` empty;`gh pr merge --delete-branch` for both PRs
- [ ] **Final Phase 56.1 milestone push** — all branches synced;SITUATION + CLAUDE + memory updated
