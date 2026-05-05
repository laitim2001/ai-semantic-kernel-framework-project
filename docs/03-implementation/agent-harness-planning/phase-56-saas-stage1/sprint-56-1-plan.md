# Sprint 56.1 — SaaS Stage 1 Foundation: Backend Tenant Lifecycle + Feature Flags + RLS Hardening

> **Sprint Type**: Phase 56+ first sprint — SaaS Stage 1 backend foundation (γ option per user approval 2026-05-05)
> **Owner Categories**: §Multi-tenant rule (tenant_id 3 鐵律 SaaS-grade hardening) / Platform Layer (tenant lifecycle / feature flags / RLS) / API Layer (admin tenant CRUD + onboarding) / Cat 12 Observability (tenant lifecycle spans)
> **Phase**: 56 (SaaS Stage 1 — 1/3 sprint of Phase 56-58 SaaS Stage 1)
> **Workload**: 5 days (Day 0-4); bottom-up est ~31 hr → calibrated commit **~17 hr** (multiplier **0.55** per AD-Sprint-Plan-4 scope-class matrix `large multi-domain` first application; reserved 0.50-0.55 band, picking 0.55 mid-band)
> **Branch**: `feature/sprint-56-1-saas-tenant-foundation`
> **Plan Authority**: This document (per CLAUDE.md §Sprint Execution Workflow)
> **Roadmap Source**: 15-saas-readiness.md §Tenant Lifecycle Management + §Feature Flags + §Multi-tenancy Scaling Stage 1 + 06-phase-roadmap.md L17 (SaaS Stage 1 = Phase 56-58 per 2026-04-28 review)
> **AD logging (sub-scope)**: AD-Sprint-Plan-4 scope-class matrix `large multi-domain` first application + AD-Phase56-Roadmap-Conflict (06-phase-roadmap.md L523-527 vs L17 internal conflict — flag for cleanup in 56.x retro)

---

## Sprint Goal

Build the **backend foundation** for SaaS Stage 1 (multi-tenant internal SaaS) — tenant lifecycle management + feature flags + RLS hardening — establishing prerequisite for Phase 56.2 (SLA + Cost Ledger + Citus) and Phase 56.3 (DR + Frontend Wizard + Compliance):

- **US-1**: Tenant Provisioning API — `POST /api/v1/admin/tenants` accepting company info + plan + admin email; auto-provisioning workflow per 15-saas-readiness §Step 2 (8 sub-steps: tenants record + default roles + default policies + Qdrant namespace + system memory seed + first admin user + API key + welcome notification); state machine `[requested → provisioning → active → suspended → archived]` with valid transitions enforced
- **US-2**: Plan Template Enforcement — `config/tenant_plans.yml` with **enterprise tier only** (per user decision 2026-05-05; basic/standard deferred to Stage 2 commercial SaaS); per-tenant quota (tokens_per_day / cost_usd_per_day / sessions_per_user_concurrent / api_keys_max) enforced via middleware on chat endpoint + admin API
- **US-3**: Onboarding API — `GET /api/v1/admin/tenants/{id}/onboarding-status` returns 6-step progress (company_info / plan_selected / memory_uploaded / sso_configured / users_invited / health_check); `POST /api/v1/admin/tenants/{id}/onboarding/{step}` advances each step; tenant moves to `active` only when all 6 steps complete + health check passes
- **US-4**: Feature Flags 系統 — `core/feature_flags.py` ABC + `feature_flags` DB table (per-tenant override) + `is_enabled(flag_name, tenant_id, user_id) -> bool` + audit log on flag toggle; seed default flags per 15-saas-readiness §Predefined Flags (thinking_enabled / verification_enabled / llm_caching_enabled / pii_masking)
- **US-5**: RLS Hardening + tenant_id Index Audit + Phase 56.1 Closeout — scan all V2 business tables for (a) RLS policy enabled (b) tenant_id NOT NULL (c) tenant_id index present; fix gaps; integration test for `app.tenant_id` SET LOCAL enforcement; Day 4 retrospective + AD-Sprint-Plan-4 first application calibration verify + Phase 56-58 roadmap conflict cleanup AD logged

Sprint 結束後:
- (a) **Tenant lifecycle backend infrastructure ready** — admin can programmatically provision new tenants via API; tenant moves through state machine deterministically; onboarding progress tracked
- (b) **Enterprise plan tier enforced** — quota中位數 (tokens/cost/sessions/api_keys) enforced per-tenant on主流量
- (c) **Feature flags 系統可用** — agent_harness 與 chat handler 可以 query `feature_flags.is_enabled()` for per-tenant feature gating
- (d) **RLS hardening complete** — V2 22/22 baseline 多租戶 3 鐵律 升級為 SaaS-grade(every business table 100% RLS enabled + tenant_id NOT NULL + index;審計報告 documenting current state + fixes)
- (e) **Phase 56.2 prerequisites in place** — SLA Monitor 可以 query tenant uptime;Cost Ledger 可以 query tenant aggregates;Citus PoC 可以分片 tenant_id (index ready)
- (f) **AD-Sprint-Plan-4 first application data point** — `large multi-domain` mult 0.55 ratio recorded for matrix calibration

**主流量驗收標準**:
- `POST /api/v1/admin/tenants` 建立新 tenant → state=`provisioning` → 8 sub-steps 完成 → state=`active` (assuming all sub-step succeed); 失敗則 state=`provision_failed`
- `pytest backend/tests/integration/api/test_tenant_lifecycle.py` 跑 e2e: provision → onboarding 6-step → active → suspended → archived
- Multi-tenant integration test: tenant A provision 不影響 tenant B 既有資料(0 cross-tenant leakage at provisioning time)
- Plan quota enforcement 主流量 e2e: enterprise tier tenant 100K tokens used → next request 過 quota → 429 Too Many Requests
- Feature flag enforcement: `feature_flags.is_enabled("thinking_enabled", tenant_id=A)` 默認 True; admin override to False → next request 不啟用 thinking
- RLS audit script: `python scripts/lint/check_rls_policies.py` → 100% business tables RLS enabled + tenant_id NOT NULL + index
- mypy --strict 0 errors on `platform_layer/tenant/`, `core/feature_flags.py`, `api/v1/admin/`
- 7 V2 lints green (含 check_rls_policies new lint)

---

## Background

### V2 進度

- **22/22 sprints (100%) main progress completed** (Phase 49-55 closed) + 6 carryover bundles (53.2.5 + 53.7 + 55.3 + 55.4 + 55.5 + 55.6)
- main HEAD: `08c57e8d` (post-PR #96 triage cleanup; 0 P0/P1/P2 findings; 1 minor yellow cosmetic; 11+1 範疇 全 Level 4 / Cat 9 L5)
- pytest baseline 1463 / 6.43s; 7 V2 lints 7/7 green
- 11+1 範疇全 Level 4;5 business domain production-capable;§HITL Centralization wired 主流量;Multi-tenant 3 鐵律 enforced
- **本 sprint = Phase 56+ SaaS Stage 1 第 1 個 sprint** (1/3 of Phase 56-58 SaaS Stage 1)

### 為什麼 56.1 是 Backend Tenant Lifecycle Foundation

User approved 2026-05-05 session γ option (完整 Lifecycle 優先):

1. **Tenant Lifecycle 是其他 10 SaaS 區塊的 prerequisite** — SLA Monitor 必須 per-tenant 統計 / Cost Ledger 必須 per-tenant aggregate / Compliance Reporting 必須 per-tenant query / DR 必須 per-tenant restore;沒有 Tenant Lifecycle infrastructure 其他 區塊都建不上去
2. **單一 enterprise tier 簡化 Stage 1 scope** — 用戶決定 Stage 1 只支援 enterprise tier(per Q2 答覆);basic/standard 差異化延後到 Stage 2 commercial SaaS;這縮減 Plan template enforcement 的複雜度約 60%
3. **Cost Ledger only(no billing integration)簡化 Stage 1** — 用戶決定 Stage 1 只做 per-tenant Cost aggregation,不接 Stripe / 月結 invoice(per Q3);這把 billing 從 Stage 1 剝離,Phase 56.2 只需做 ledger
4. **Frontend Wizard 移到 Phase 56.3** — 56.1 backend scope 已滿(5 USs / ~31 hr bottom-up);frontend 需要先有 backend Onboarding API contract 才能 build;Phase 56.3 backend stable 後 build frontend
5. **Citus 移到 Phase 56.2** — Citus 是 scaling infra(SLA enabler),與 Cost Ledger / SLA Monitor 同 sprint 較自然
6. **AD-Sprint-Plan-4 scope-class matrix 首次應用** — 56.1 是 V2 22/22 closure 後第一個 main-progress sprint;`large multi-domain` 類別第一次套用(0.50-0.55 band 取 0.55 mid)

### 既有結構(Day 0 探勘 grep 將驗證以下假設)

⚠️ **以下 layout 是 plan-time 推斷;Day 0 grep 將 confirm 或 catalogue 為 D-finding**:

```
backend/src/
├── platform_layer/
│   ├── identity/                            # 假設:53.x 多租戶基礎已建立 tenants table
│   │   ├── models.py                        # ⚠️ Day 0 verify: tenants ORM model exists?
│   │   └── ...
│   ├── governance/                          # ✅ 53.4 §HITL Centralization
│   └── workers/                             # ✅ 49.4 worker queue
├── core/
│   ├── config/                              # ✅ Settings (BUSINESS_DOMAIN_MODE etc)
│   └── feature_flags.py                     # ❌ NEW (US-4)
├── api/v1/
│   ├── chat/                                # ✅ 53.6 production HITL wired
│   └── admin/                               # ⚠️ Day 0 verify: admin router exists?
│       └── tenants.py                       # ❌ NEW (US-1 + US-3)
├── infrastructure/db/
│   ├── models/
│   │   ├── tenant.py                        # ⚠️ Day 0 verify: tenant model + state column
│   │   └── feature_flag.py                  # ❌ NEW (US-4)
│   └── alembic/versions/
│       └── 0014_*.py                        # ❌ NEW (Alembic migration; current head = 0013 from 55.3)
└── platform_layer/tenant/                   # ❌ NEW package (US-1 + US-2 + US-3)
    ├── __init__.py
    ├── lifecycle.py                         # State machine
    ├── provisioning.py                      # 8-step provisioning workflow
    ├── plans.py                             # Plan template loader (enterprise only)
    ├── quota.py                             # Quota enforcement middleware
    └── onboarding.py                        # 6-step onboarding tracker
```

### 15-saas-readiness §Stage 1 SaaS Scope 對齐

Phase 56-58 SaaS Stage 1 完整 scope 11 區塊;本 sprint(56.1)涵蓋其中:

| 15-saas-readiness 區塊 | Sprint 56.1 涵蓋? | 備註 |
|---------------------|-----------------|------|
| §Tenant Lifecycle Management(Provisioning + State Machine)| ✅ US-1 | 完整 |
| §Tenant 配置範本(Plan templates)| ✅ US-2(只 enterprise)| 簡化 |
| §Tenant Onboarding 自動化(6-step)| ✅ US-3 backend API | Frontend Wizard → 56.3 |
| §Feature Flags | ✅ US-4 | 完整 |
| §Multi-tenancy Scaling Stage 1(RLS + tenant_id index)| ✅ US-5 | 完整 |
| §SLA 與監控 | ❌ Phase 56.2 | |
| §Billing 整合(Cost Ledger only) | ❌ Phase 56.2 | |
| §Disaster Recovery | ❌ Phase 56.3 | |
| §Customer Support Integration | ❌ Phase 56.3 | |
| §Compliance Reporting | ❌ Phase 56.2 + 56.3 split | |
| §Public API & Status Page | ❌ Phase 56.3 | |

### V2 紀律 9 項對齐確認

1. **Server-Side First** ✅ Tenant lifecycle 全 server-side;admin API 強 zero-trust;Provisioning workflow 不依賴 client-side state
2. **LLM Provider Neutrality** ✅ `platform_layer/tenant/` + `core/feature_flags.py` 不 import LLM SDK;CI lint check_llm_sdk_leak 強制
3. **CC Reference 不照搬** ✅ 不抄 Anthropic SaaS 的 tenant model;遵循 V2 RLS + per-request DI 模式
4. **17.md Single-source** ✅ Tenant ORM 是 platform-internal,不是 cross-category contract;Feature Flags 介面 in `core/`,non-cross-category
5. **11+1 範疇歸屬** ✅ 全部新檔在 `platform_layer/tenant/` (新 package) + `core/feature_flags.py` + `api/v1/admin/`;無 AP-3
6. **04 anti-patterns** ✅ AP-3 範疇歸屬合規;AP-4(Potemkin)— 每 module 必有 unit test + 主流量 integration test;AP-6(Hybrid Bridge Debt)— 不為「Stage 2 商業 SaaS 預留」加抽象,YAGNI;AP-9 N/A(verification 已在 chat 主流量;tenant lifecycle 有 state machine validation)
7. **Sprint workflow** ✅ plan → checklist → Day 0 探勘 → code → progress → retro;本文件依 55.2 plan 結構鏡射(14 sections / Day 0-4)
8. **File header convention** ✅ 所有新 .py 含 file header docstring;modify 既有檔加 Modification History entry
9. **Multi-tenant rule** 🔴 **CORE FOCUS** — Tenant 是 SaaS Stage 1 的根本;US-1+US-2+US-3+US-5 都圍繞 tenant_id;每查詢必過 RLS;US-5 是專門的 hardening sprint

---

## User Stories

### US-1: Tenant Provisioning API + State Machine

**As** a SaaS platform admin
**I want** `POST /api/v1/admin/tenants` API 建立 new tenant,觸發 8-step auto-provisioning workflow(per 15-saas-readiness §Step 2),tenant 狀態經 state machine `[requested → provisioning → active → suspended → archived]` (with `provision_failed` branch);8 sub-steps 包含 tenants record / default roles / default policies (HITL+Risk) / Qdrant namespace / system memory seed / first admin user / hashed API key / welcome notification stub
**So that** admin 可程式化 onboarding new tenant;state machine 限制非法 transition(e.g., archived → active 必須 explicit reactivate);failed provisioning 可 retry / 手動修復

**Acceptance**:
- [ ] `infrastructure/db/models/tenant.py` Tenant ORM model with columns: `id` UUID PK / `name` / `state` Enum(requested/provisioning/active/suspended/archived/provision_failed) / `plan` (enterprise; future-proof Enum) / `created_at` / `updated_at` / `provisioning_step` JSONB(8-step progress)/ tenant_id 自身就是主鍵
- [ ] Alembic migration 0014 建 tenants table + indexes(state for filtering / created_at)
- [ ] `platform_layer/tenant/lifecycle.py` TenantLifecycle class with state machine: `transition(tenant_id, new_state) -> Tenant`(validates allowed transitions per 15-saas-readiness §State Machine diagram); 6 valid transitions only;invalid raises `IllegalTransitionError`
- [ ] `platform_layer/tenant/provisioning.py` ProvisioningWorkflow class with 8 sub-steps:
  - 2.1 create tenants record(state=provisioning)
  - 2.2 create default roles(reuse 53.4 governance roles? — Day 0 verify)
  - 2.3 create default policies(HITLPolicy from 55.3 AD-Hitl-7 DBHITLPolicyStore + RiskPolicy from 53.4)
  - 2.4 Qdrant namespace stub(Phase 56.x integrate;此 sprint 只記 placeholder field)
  - 2.5 system memory seed stub(Phase 56.x — Memory Layer 1 system seed)
  - 2.6 create first admin user(uses 53.x identity infra)
  - 2.7 generate hashed API key(bcrypt + return one-time plaintext)
  - 2.8 emit welcome notification event(stub log + Phase 56.3 Teams integration)
- [ ] `api/v1/admin/tenants.py` `POST /api/v1/admin/tenants` endpoint with Pydantic schema(`TenantCreateRequest` / `TenantCreateResponse`); admin auth required(reuse 53.x admin role check)
- [ ] Failed sub-step → state=`provision_failed` + audit log entry + step recorded in `provisioning_step` JSONB field
- [ ] mypy --strict 0 errors;7 V2 lints green
- [ ] 8 unit tests(state machine 6 valid transitions + 2 illegal cases)+ 4 integration tests(full provisioning happy path / step 2.7 failure / retry from provision_failed / archived → active rejected)

### US-2: Plan Template Enforcement (Enterprise Tier Only)

**As** a SaaS platform admin
**I want** `config/tenant_plans.yml` 定義 `enterprise` tier(per 15-saas-readiness §Tenant 配置範本)quota + features + mcp_servers;每個 tenant 啟動時讀取 plan;quota enforcement middleware 在 chat endpoint 攔截超限請求 → 429
**So that** Stage 1 內部 SaaS 有明確 quota 限制;Phase 56.2 SLA Monitor 可以基於 quota 計算用量百分比

**Acceptance**:
- [ ] `config/tenant_plans.yml` enterprise tier definition(quota + features + mcp_servers per 15-saas-readiness L108-121)
- [ ] `platform_layer/tenant/plans.py` `PlanLoader` class with `get_plan(plan_name='enterprise') -> Plan`; cached in-memory after first load
- [ ] `platform_layer/tenant/quota.py` `QuotaEnforcer` middleware/dependency; tracks per-tenant daily usage(tokens / cost / concurrent sessions);超限 raise `HTTPException(429, "Daily quota exceeded")`
- [ ] Quota usage 暫存 Redis(per-tenant daily counter; expires at midnight UTC; Phase 56.2 sync to PostgreSQL)
- [ ] Chat endpoint integrate `Depends(quota_enforcer)`(在 53.6 production HITL wiring 之前);每 request 增加 token usage post-LLM-call
- [ ] mypy --strict 0 errors;7 V2 lints green
- [ ] 6 unit tests(plan load / quota tracker increment / quota exceed / quota reset at midnight / multi-tenant isolation / plan not found)+ 2 integration tests(chat endpoint quota exceeded → 429 / quota reset)

### US-3: Onboarding API (6-step + Health Check)

**As** a SaaS platform admin or tenant admin
**I want** `GET /api/v1/admin/tenants/{id}/onboarding-status` 返回 6-step progress + `POST /api/v1/admin/tenants/{id}/onboarding/{step}` 推進每步驟;tenant `state=provisioning` 至 `active` 之間必須 6-step 全完成 + health check pass
**So that** Frontend Wizard(Phase 56.3)可以 step-by-step 引導 tenant admin 完成 onboarding;health check 確保 active tenant 真的 ready

**Acceptance**:
- [ ] `platform_layer/tenant/onboarding.py` `OnboardingTracker` with 6 steps(per 15-saas-readiness §Onboarding Wizard L312-335):company_info / plan_selected / memory_uploaded / sso_configured / users_invited / health_check
- [ ] `tenants.onboarding_progress` JSONB column(per-step boolean + timestamp + payload)
- [ ] `GET /api/v1/admin/tenants/{id}/onboarding-status` Pydantic response with completed_steps / pending_steps / health_check object
- [ ] `POST /api/v1/admin/tenants/{id}/onboarding/{step}` accepts payload per step;validates step name;updates JSONB progress;當 6/6 完成時 trigger health check;health check pass → state transition `provisioning` → `active`
- [ ] Health check 6-points:DB connection / Redis / Qdrant ping / sample LLM call(adapter ping)/ first admin user exists / API key valid;each must pass
- [ ] State machine transition `provisioning → active` 由 onboarding 完成觸發,不能直接 admin force(integrity)
- [ ] mypy --strict 0 errors;7 V2 lints green
- [ ] 4 unit tests(step advance / health check pass / health check fail blocks active / step skip rejected)+ 3 integration tests(full 6-step flow / partial onboarding query / health check timeout)

### US-4: Feature Flags 系統

**As** a SaaS platform admin or system developer
**I want** `core/feature_flags.py` ABC + DB-backed `feature_flags` table 支援 per-tenant override + audit log;`is_enabled(flag_name, tenant_id=None, user_id=None) -> bool` 核心 API;default flags seeded from 15-saas-readiness §Predefined Flags(thinking_enabled / verification_enabled / llm_caching_enabled / pii_masking)
**So that** agent_harness 11+1 範疇 + chat handler 可以 query feature flag;tenant admin 可以 toggle;audit trail 完整

**Acceptance**:
- [ ] `infrastructure/db/models/feature_flag.py` FeatureFlag ORM model with columns: `id` PK / `name` / `default_enabled` Boolean / `tenant_overrides` JSONB / `description` / `created_at` / `updated_at`
- [ ] Alembic 0014 同 migration 建 feature_flags table
- [ ] `core/feature_flags.py` `FeatureFlagsService` class:
  - `is_enabled(flag_name, tenant_id=None, user_id=None) -> bool`(查 default → tenant override → return)
  - `set_tenant_override(flag_name, tenant_id, enabled, actor_user_id) -> None`(寫 audit log)
  - `seed_defaults() -> None`(idempotent;startup 時跑)
- [ ] Default flags seeded:thinking_enabled=True / verification_enabled=True / llm_caching_enabled=True / pii_masking=True
- [ ] Tenant override audit log(reuse 53.4 audit infrastructure)
- [ ] In-memory cache(per-tenant);invalidate on `set_tenant_override`
- [ ] mypy --strict 0 errors;7 V2 lints green
- [ ] 5 unit tests(default lookup / tenant override / audit log on set / cache invalidate / seed_defaults idempotent)+ 1 integration test(chat handler `is_enabled("thinking_enabled", tenant_id=A)` returns False after override)

### US-5: RLS Hardening + tenant_id Index Audit + Phase 56.1 Closeout

**As** a SaaS platform admin
**I want** scan all V2 business tables for(a)RLS policy enabled(b)tenant_id NOT NULL(c)tenant_id index present;identify gaps + fix;add `scripts/lint/check_rls_policies.py` CI lint(7th V2 lint already exists check_sole_mutator;此為 8th)
**So that** SaaS Stage 1 多租戶隔離 hardened to 100%;Phase 56.2 Citus PoC 可基於 tenant_id 分片(index ready);Phase 56.3 Compliance reporting 可以 query 任何 table by tenant_id

**Acceptance**:
- [ ] `scripts/lint/check_rls_policies.py` scans all `infrastructure/db/models/*.py` ORM tables;reports per-table:RLS enabled? / tenant_id column exists? / tenant_id NOT NULL? / tenant_id index?
- [ ] Audit report committed to `docs/03-implementation/agent-harness-execution/phase-56/sprint-56-1/rls-audit.md`
- [ ] Identified gaps fixed via Alembic 0014(or 0015 if separate migration cleaner);log each fix in audit report
- [ ] Add 8th V2 lint to `scripts/lint/run_all.py` orchestrator;CI workflow updated
- [ ] Integration test: `app.tenant_id` SET LOCAL session enforcement — query without SET LOCAL → returns 0 rows(RLS blocks);with SET LOCAL → returns scoped rows
- [ ] mypy --strict 0 errors;8 V2 lints green(includes new check_rls_policies)
- [ ] Day 4 retrospective.md(6 必答 + AD-Sprint-Plan-4 first application calibration verify + Phase 56-58 roadmap conflict cleanup AD logged)
- [ ] Closeout PR(SITUATION-V2 + CLAUDE.md + memory updated to Phase 56.1 closure;Phase 56-58 SaaS Stage 1 1/3 progress)

---

## Technical Specifications

### Architecture: Tenant Lifecycle State Machine

```
[requested]
    │
    │ POST /api/v1/admin/tenants
    ↓
[provisioning] ────→ [provision_failed] (any sub-step fails)
    │                       │
    │ 8 sub-steps           │ retry endpoint
    │ + onboarding 6-step   │
    │ + health check        │
    ↓                       │
[active] ←──────────────────┘
    │  ↑
    │  │ reactivate endpoint
    ↓  │
[suspended]
    │
    │ archive endpoint
    ↓
[archived] ──→ [deleted] (manual hard delete; out of state machine)
```

### Architecture: Provisioning Workflow (8 sub-steps)

```
ProvisioningWorkflow.run(tenant_id):
  1. transition(tenant_id, provisioning)
  2. for step in [
       "create_tenant_record",  # already done by API endpoint
       "seed_default_roles",
       "seed_default_policies",
       "create_qdrant_namespace_stub",  # Phase 56.x integrate
       "seed_system_memory_stub",       # Phase 56.x integrate
       "create_first_admin_user",
       "generate_api_key",
       "emit_welcome_notification_stub", # Phase 56.3 Teams integration
     ]:
        try:
            await step_fn(tenant_id)
            await mark_step_done(tenant_id, step)
        except Exception as e:
            await transition(tenant_id, provision_failed)
            await audit_log(tenant_id, step, error=e)
            raise
  3. tenant remains in provisioning until onboarding completes
```

### Architecture: Onboarding 6-step + Health Check

```
OnboardingTracker.advance(tenant_id, step, payload):
  1. validate step in 6 valid steps
  2. update tenants.onboarding_progress JSONB[step]
  3. if all 6 steps complete:
        health_check_result = await health_check(tenant_id)
        if all 6 health points pass:
            await lifecycle.transition(tenant_id, active)
        else:
            log health failure;remain provisioning
```

### File Layout

```
backend/src/
├── infrastructure/db/
│   ├── models/
│   │   ├── tenant.py                    NEW — Tenant ORM model
│   │   └── feature_flag.py              NEW — FeatureFlag ORM model
│   └── alembic/versions/
│       └── 0014_*.py                    NEW — tenants + feature_flags + RLS gap fixes
├── platform_layer/tenant/               NEW package
│   ├── __init__.py                      NEW
│   ├── lifecycle.py                     NEW — TenantLifecycle state machine
│   ├── provisioning.py                  NEW — ProvisioningWorkflow 8-step
│   ├── plans.py                         NEW — PlanLoader (enterprise only)
│   ├── quota.py                         NEW — QuotaEnforcer middleware
│   └── onboarding.py                    NEW — OnboardingTracker 6-step
├── core/
│   └── feature_flags.py                 NEW — FeatureFlagsService
├── api/v1/admin/
│   ├── __init__.py                      MODIFIED (or NEW if missing)
│   └── tenants.py                       NEW — admin tenant CRUD + onboarding API
├── config/
│   └── tenant_plans.yml                 NEW — enterprise tier config
└── scripts/lint/
    ├── check_rls_policies.py            NEW — 8th V2 lint
    └── run_all.py                       MODIFIED — add 8th lint to orchestrator

docs/03-implementation/agent-harness-execution/
└── phase-56/
    └── sprint-56-1/
        ├── progress.md                  NEW — Day 0-4 progress
        ├── retrospective.md             NEW — 6 必答 + AD calibration verify
        └── rls-audit.md                 NEW — RLS audit report

config/
└── tenant_plans.yml                     NEW
```

### Tenant ORM Model

```python
# infrastructure/db/models/tenant.py
class TenantState(str, Enum):
    REQUESTED = "requested"
    PROVISIONING = "provisioning"
    PROVISION_FAILED = "provision_failed"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"

class TenantPlan(str, Enum):
    ENTERPRISE = "enterprise"
    # Phase 56+ Stage 2: BASIC / STANDARD

class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    state: Mapped[TenantState] = mapped_column(SQLEnum(TenantState), default=TenantState.REQUESTED)
    plan: Mapped[TenantPlan] = mapped_column(SQLEnum(TenantPlan), default=TenantPlan.ENTERPRISE)
    provisioning_progress: Mapped[dict] = mapped_column(JSONB, default=dict)  # per-step boolean
    onboarding_progress: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(onupdate=func.now())
    # NO tenant_id (Tenant table itself is the registry; not multi-tenant scoped)
```

### Plan Template (Enterprise Only)

```yaml
# config/tenant_plans.yml
plans:
  enterprise:
    quota:
      tokens_per_day: 10_000_000
      cost_usd_per_day: 500
      sessions_per_user_concurrent: 50
      api_keys_max: 10
    features:
      verification: true
      thinking: true
      subagents: true
      mcp_servers: "*"
      custom_tools: true
      dedicated_support: true

# Phase 56+ Stage 2 will add basic / standard tiers
```

---

## Acceptance Criteria

### Sprint-Wide

- [ ] V2 主進度 22/22 (100%) 不變;Phase 56-58 SaaS Stage 1 進度 0/3 → 1/3
- [ ] All 8 V2 lints green (existing 7 + new check_rls_policies)
- [ ] mypy --strict 0 errors
- [ ] LLM SDK leak: 0
- [ ] Anti-pattern checklist 11 項對齐
- [ ] 5 active CI checks green (Backend CI / V2 Lint / E2E Backend / E2E Summary / Frontend E2E chromium)
- [ ] Test count baseline 1463 → ≥ 1500 (≥ +37 new = ~12 unit US-1 + ~6 unit US-2 + ~4 unit US-3 + ~5 unit US-4 + ~10 integration tests)
- [ ] AD-Sprint-Plan-4 first application captured + verdict logged in retro Q2
- [ ] AD-Phase56-Roadmap-Conflict logged for cleanup in 56.x retro

### Per-User-Story

詳見 §User Stories acceptance per US.

---

## Day-by-Day Plan

### Day 0 — Setup + Day-0 探勘 + Pre-flight Verify

- 0.1 Branch + plan + checklist commit
- 0.2 Day-0 兩-prong 探勘(per AD-Plan-3 promoted)— **Prong 1 Path Verify**:`platform_layer/tenant/` 不存在(expect)/ `core/feature_flags.py` 不存在(expect)/ `api/v1/admin/` 是否存在 / `infrastructure/db/models/tenant.py` 是否存在(53.x baseline?);**Prong 2 Content Verify**:53.4 governance roles 是否可重用(query roles ORM)/ 53.4 + 55.3 HITLPolicyStore 介面 / 55.3 Alembic head version(0013?)/ 既有 `tenants` table 是否已存在(若是,scope 收斂為 enhance 不是 create)
- 0.3 Calibration multiplier pre-read(7-sprint window 4/8 in-band per 55.6 retro;medium-backend 0.85 mean 1.03;`large multi-domain` 從 AD-Sprint-Plan-4 matrix 取 0.55 mid-band first application)
- 0.4 Pre-flight verify(pytest baseline 1463 / 7 V2 lints baseline / mypy baseline)
- 0.5 Day 0 progress.md commit + push;catalogue D-findings

### Day 1 — US-1 Tenant Provisioning API + State Machine

- 1.1 `infrastructure/db/models/tenant.py` Tenant ORM(若 Day 0 探勘確認 not exist)
- 1.2 Alembic 0014 migration(tenants table + indexes + RLS policy)
- 1.3 `platform_layer/tenant/lifecycle.py` TenantLifecycle state machine
- 1.4 `platform_layer/tenant/provisioning.py` ProvisioningWorkflow 8-step(stub Qdrant + system memory + welcome notification per Phase 56.x defer)
- 1.5 `api/v1/admin/tenants.py` `POST /api/v1/admin/tenants` endpoint
- 1.6 8 unit tests + 4 integration tests
- 1.7 mypy + 7 V2 lints green
- 1.8 Day 1 progress.md + commit + push

### Day 2 — US-2 Plan Template + US-3 Onboarding API (start)

- 2.1 `config/tenant_plans.yml` enterprise tier
- 2.2 `platform_layer/tenant/plans.py` PlanLoader
- 2.3 `platform_layer/tenant/quota.py` QuotaEnforcer middleware + Redis daily counter
- 2.4 Chat endpoint quota integration
- 2.5 `platform_layer/tenant/onboarding.py` OnboardingTracker 6-step(US-3 part 1)
- 2.6 6 unit US-2 + 2 unit US-3
- 2.7 mypy + 7 V2 lints green
- 2.8 Day 2 progress.md + commit + push

### Day 3 — US-3 Onboarding API (finish) + US-4 Feature Flags

- 3.1 `api/v1/admin/tenants.py` onboarding endpoints(GET status / POST advance step)
- 3.2 Health check 6-points implementation
- 3.3 3 integration US-3
- 3.4 `infrastructure/db/models/feature_flag.py` FeatureFlag ORM(同 Alembic 0014 same migration)
- 3.5 `core/feature_flags.py` FeatureFlagsService(default lookup / tenant override / audit log / cache)
- 3.6 5 unit US-4 + 1 integration US-4
- 3.7 mypy + 7 V2 lints green
- 3.8 Day 3 progress.md + commit + push

### Day 4 — US-5 RLS Hardening + Closeout Ceremony

- 4.1 `scripts/lint/check_rls_policies.py` 8th V2 lint
- 4.2 RLS audit report `rls-audit.md`(scan all business tables / identify gaps)
- 4.3 Alembic 0014 RLS gap fixes(append to 0014 migration if same head;or new 0015)
- 4.4 8 V2 lint orchestrator update(`run_all.py`)
- 4.5 RLS integration test(SET LOCAL enforcement)
- 4.6 Multi-tenant integration test cross-domain(verify provisioning + chat + quota + feature flag isolation)
- 4.7 Final pytest + 8 V2 lints + LLM SDK leak final verify
- 4.8 retrospective.md(6 必答 + AD-Sprint-Plan-4 first application calibration verify + Phase 56-58 roadmap conflict AD)
- 4.9 Open PR → CI green → solo-dev merge to main
- 4.10 Closeout PR(SITUATION-V2 + CLAUDE.md updates + memory snapshots)

---

## File Change List

| File | Status | Lines (est) |
|------|--------|-------------|
| `infrastructure/db/models/tenant.py` | NEW (or MODIFIED if exists) | ~80 |
| `infrastructure/db/models/feature_flag.py` | NEW | ~40 |
| `infrastructure/db/alembic/versions/0014_*.py` | NEW | ~150 |
| `platform_layer/tenant/__init__.py` | NEW | ~10 |
| `platform_layer/tenant/lifecycle.py` | NEW | ~120 |
| `platform_layer/tenant/provisioning.py` | NEW | ~180 |
| `platform_layer/tenant/plans.py` | NEW | ~80 |
| `platform_layer/tenant/quota.py` | NEW | ~120 |
| `platform_layer/tenant/onboarding.py` | NEW | ~150 |
| `core/feature_flags.py` | NEW | ~150 |
| `api/v1/admin/tenants.py` | NEW | ~200 |
| `api/v1/admin/__init__.py` | NEW or MODIFIED | ~20 |
| `config/tenant_plans.yml` | NEW | ~30 |
| `scripts/lint/check_rls_policies.py` | NEW | ~120 |
| `scripts/lint/run_all.py` | MODIFIED | +5 |
| Tests (~37 new) | NEW | ~600 |
| `docs/.../sprint-56-1/{progress,retrospective,rls-audit}.md` | NEW | ~700 |
| `memory/project_phase56_1_saas_foundation.md` | NEW | ~60 |

**Total**: ~1,455 source LOC + ~600 test LOC + ~760 docs LOC

---

## Dependencies & Risks

### Dependencies (must exist before code starts)

- ⚠️ Phase 53.x identity infrastructure(roles / users)— Day 0 grep verify
- ⚠️ Phase 53.4 governance(HITLPolicy / RiskPolicy)— Day 0 grep verify(should be present)
- ⚠️ Phase 55.3 AD-Hitl-7 DBHITLPolicyStore — Day 0 grep verify
- ⚠️ Alembic 0013 head from 55.3 — Day 0 verify head version
- ⚠️ Existing `tenants` table baseline — Day 0 grep critical(若已存在,US-1 scope 收斂為 enhance 而非 create)
- ⚠️ `api/v1/admin/` router base — Day 0 grep verify

### Risk Classes (per sprint-workflow.md §Common Risk Classes)

**Risk Class A (paths-filter vs required_status_checks)**: backend-only sprint → backend-ci will fire (paths include `backend/**`). Frontend E2E required check 已 fixed by 55.6 Option Z(paths-filter retired)— this risk class is **historically closed**.

**Risk Class B (cross-platform mypy unused-ignore)**: medium risk;new feature_flags + tenant ORM may need stub for some Alembic types. Mitigation: standard `# type: ignore[X, unused-ignore]` if encountered.

**Risk Class C (module-level singleton across event loops)**: MEDIUM RELEVANCE — `FeatureFlagsService` cache could become module-level singleton;`PlanLoader` cache too. Mitigation: per-request DI pattern (no module-level cache);若 cache 必要,加 conftest.py `reset_*` autouse fixture pattern per testing.md §Module-level Singleton Reset Pattern.

### Day 0 探勘 D-findings (catalogued 2026-05-05; per AD-Plan-1 + AD-Plan-3 promoted)

8 drift findings from Day 0 兩-prong 探勘 — full detail in [`progress.md`](../../../agent-harness-execution/phase-56/sprint-56-1/progress.md) §Day 0 Drift findings table:

| ID | Summary | Sprint Impact |
|----|---------|---------------|
| D1 | `class Tenant(Base)` 已存在於 `identity.py:67` (code/display_name/status/metadata 4 cols, 無 state Enum / plan / progress JSONB) | US-1 = ENHANCE not CREATE (~-2 hr scope save); Day 1 decides rename `status` → `state` Enum or keep both |
| D2 | V2 Alembic 在 `backend/src/infrastructure/db/migrations/versions/` (NOT `db/alembic/`); head = `0013_hitl_policies.py` (55.3); next = **0014** | §File Layout 路徑修正(applied at Day 1+ implementation; plan §Tech Spec preserves original audit trail per AD-Plan-1) |
| D3 | Audit infra spread:`AuditLog` ORM at `models/audit.py:67` + `governance/audit/query.py` + `guardrails/audit/worm_log.py` (53.3 WORM);無 single `class AuditLogger` | US-4 feature_flag override audit pathway = direct AuditLog ORM write (Day 3 design) |
| D4 | Chat router L121 `tracer=None  # D2: get_tracer factory deferred to Phase 56+` (carryover 55.2 = AD-Cat12-BusinessObs) | US-1+US-3+US-4 obs spans pass `tracer=None` to `category_span` until AD-Cat12-BusinessObs closure |
| D5 | `TenantScopedMixin` at `infrastructure/db/base.py:51` confirmed | None (assumption verified) |
| D6 | Chat router POST L89-94 uses `ServiceFactory` (53.4 governance), not `BusinessServiceFactory` | US-2 QuotaEnforcer Depends inserts after `factory + db` (Day 2 task) |
| D7 | pytest baseline **1467 collected** (+4 vs plan 1463); mypy **270 files** (+4 vs plan 266) | Test target re-baseline: 1467 → ≥ 1504 (+37 unchanged) |
| D8 | V2 lint scripts at root `scripts/lint/` (NOT `backend/scripts/lint/`); 7 scripts + run_all.py orchestrator | §US-5 + §File Layout: 8th lint at `scripts/lint/check_rls_policies.py` (root) |

**Net scope shift**: ≤ 10% (D1 saves ~2 hr; D2+D7+D8 add ~0.5 hr path corrections) → proceed Day 1 without plan re-write per AD-Plan-1 audit-trail discipline.

### Sprint-specific Risks

| Risk | Mitigation |
|------|-----------|
| 既有 `tenants` table 若已存在,US-1 scope unclear | ✅ **CLOSED by Day 0 D1**: Tenant ORM 已存在 `identity.py:67`;US-1 確認為 ENHANCE pattern;Day 1 ORM modification + Alembic 0014 加 state/plan/progress columns |
| Provisioning workflow 8-step 中 Qdrant + system memory + welcome notification 需要外部依賴 | 此 sprint 全部 stub(log + placeholder field);Phase 56.x 真實接線;sprint scope 縮減 ~3 hr |
| Quota enforcement Redis daily counter race condition | Use Redis INCR atomic;每日 00:00 UTC 重置(TTL = 24h from first set);多 worker 共享 OK |
| RLS audit 發現 gap 需大量 schema 改動 | Day 0 quick scan dryrun;若 > 5 tables 需 RLS 補,scope split — 緊急 fixes 入此 sprint;次要 deferred to Phase 56.2 |
| Feature Flags 缺 audit 介面 | Reuse 53.4 governance audit infrastructure;`set_tenant_override` 寫 audit log via existing AuditLogger |
| `large multi-domain` 0.55 mult first application 預估偏差 | 若 ratio > 1.20 → AD-Sprint-Plan-5 lift;若 < 0.85 → AD-Sprint-Plan-5 reduce;每 case logged in retro Q2 |

---

## Workload

> **Bottom-up est ~31 hr → calibrated commit ~17 hr (multiplier 0.55 per AD-Sprint-Plan-4 scope-class matrix `large multi-domain` first application)**
> **8-sprint window 4/8 in-band(`large multi-domain` 為新類別,首次套用)** — `large multi-domain` 從 AD-Sprint-Plan-4 matrix 取 0.50-0.55 band, 取 0.55 mid (per user choice)

| US | Bottom-up (hr) |
|----|---------------|
| US-1 Tenant Provisioning API + State Machine | 10 |
| US-2 Plan Template Enforcement | 4 |
| US-3 Onboarding API + Health Check | 6 |
| US-4 Feature Flags 系統 | 6 |
| US-5 RLS Hardening + index audit + closeout ceremony | 5 |
| **Total bottom-up** | **31** |
| **× 0.55 calibrated** | **17.05 ≈ 17** |

Day 4 retrospective Q2 must verify: `actual_total_hr / 17 → ratio` compared to [0.85, 1.20] band;document delta + log calibration verdict for `large multi-domain` class baseline.

---

## Out of Scope

- ❌ basic / standard plan tiers — Phase 56+ Stage 2 commercial SaaS(per user 2026-05-05 decision)
- ❌ Stripe / 月結 invoice / billing run — Phase 56.2 only does Cost Ledger aggregation;billing 在 Stage 2
- ❌ SLA Monitor implementation — Phase 56.2
- ❌ DR + WAL streaming + cross-region replication + drill runbook — Phase 56.3
- ❌ Frontend Onboarding Wizard UI — Phase 56.3
- ❌ Cost Ledger per-tenant aggregation — Phase 56.2
- ❌ Citus PoC — Phase 56.2
- ❌ Compliance Reporting endpoints(audit log / data inventory / SLA report)— Phase 56.2 + 56.3 split
- ❌ Status Page — Phase 56.3
- ❌ Customer Support tooling integration — Phase 56.3
- ❌ Public API key rotation — Phase 56.x(此 sprint 只 generate hashed key + return one-time plaintext)
- ❌ SSO / SAML integration(Entra ID / LDAP)— Phase 56.x(此 sprint onboarding step 4 是 stub field 紀錄 SSO config,不真接)
- ❌ Real Qdrant namespace creation — Phase 56.x(此 sprint provisioning step 2.4 stub)
- ❌ Real system memory Layer 1 seeding — Phase 56.x(此 sprint provisioning step 2.5 stub)
- ❌ Real Teams welcome notification — Phase 56.3(此 sprint provisioning step 2.8 stub log)

---

## AD Carryover Sub-Scope

### AD-Sprint-Plan-4 (scope-class multiplier matrix `large multi-domain` first application)

**Source**: Sprint 55.3 retrospective Q2 (calibration ratio 2.81 way over band → single global multiplier invalidated → matrix proposed)

**Closure plan**:
1. Sprint 56.1 plan §Workload uses **0.55** for `large multi-domain` class (first application of this class)
2. Day 4 retrospective Q2 computes `actual / 17`
3. If ratio ∈ [0.85, 1.20] → record `large multi-domain` baseline 0.55 ✅;rule stable for Phase 56.2 + 56.3
4. If ratio < 0.85 → log AD-Sprint-Plan-5 (lower 0.55 → 0.45)
5. If ratio > 1.20 → log AD-Sprint-Plan-5 (raise 0.55 → 0.65)

### AD-Phase56-Roadmap-Conflict (06-phase-roadmap.md L17 vs L523-527)

**Source**: Sprint 56.1 plan-time discovery — 06-phase-roadmap.md has internal conflict between L17 (says SaaS Stage 1 = Phase 56-58 per 2026-04-28 review) and L523-527 (says Phase 56=性能/K8s, 57=多模型, 58=UI/UX, 59=商業 SaaS — V1 殘留)

**Closure plan**:
1. Log AD in Sprint 56.1 retrospective Q4 V2 紀律 review
2. Phase 56.x audit cycle sprint 將 06-phase-roadmap.md L523-527 修訂為對齐 15-saas-readiness §Phase 56-58 SaaS Stage 1
3. 暫時:本 sprint 以 15-saas-readiness L17-31 + L599-611 為權威(per 文件權威排序)

---

## Definition of Done

- [ ] All 5 USs acceptance criteria met
- [ ] Test count ≥ 1500 (1463 + 37 new)
- [ ] mypy --strict 0 errors
- [ ] 8 V2 lints green (含 new check_rls_policies)
- [ ] LLM SDK leak: 0
- [ ] Anti-pattern checklist 11 項對齐
- [ ] Tenant lifecycle e2e: provision → onboarding 6-step → active → suspended → archived
- [ ] Plan quota e2e: enterprise tier tenant 100K tokens 用完 → 429
- [ ] Feature flag e2e: chat handler queries `is_enabled("thinking_enabled", tenant_id=A)` after admin override
- [ ] RLS audit report committed;all gaps fixed
- [ ] AD-Sprint-Plan-4 first application captured + verdict logged
- [ ] AD-Phase56-Roadmap-Conflict logged for cleanup
- [ ] PR opened, CI green (5 active checks), merged to main
- [ ] Closeout PR merged
- [ ] SITUATION-V2 + memory + CLAUDE.md updated to **Phase 56-58 SaaS Stage 1 1/3 (Sprint 56.1 closed)**
- [ ] Phase 56.2 readiness checklist documented in retrospective Q6 (next sprint candidate scope: SLA Monitor + Cost Ledger + Citus PoC)

---

## References

- 15-saas-readiness.md §Tenant Lifecycle Management + §Tenant 配置範本 + §Tenant Onboarding 自動化 + §Feature Flags + §Multi-tenancy Scaling Stage 1
- 06-phase-roadmap.md §L17 (SaaS Stage 1 = Phase 56-58 — authority per 2026-04-28 review)
- 10-server-side-philosophy.md §原則 1 Server-Side First + §multi-tenant
- 14-security-deep-dive.md §multi-tenant tenant_id propagation + §RLS policy
- 17-cross-category-interfaces.md §Contract 12 Tracer (used by tenant lifecycle obs spans)
- .claude/rules/multi-tenant-data.md (3 鐵律 + DI tenant propagation + RLS policy template)
- .claude/rules/observability-instrumentation.md (5 必埋點 + ctx mgr pattern)
- .claude/rules/testing.md §Module-level Singleton Reset Pattern (FeatureFlagsService cache)
- .claude/rules/sprint-workflow.md §Common Risk Classes (3 classes A/B/C) + §Step 2.5 Day-0 兩-prong 探勘 (AD-Plan-3 promoted)
- Sprint 55.2 plan + checklist (format template per AD-Sprint-Plan-1 sprint-workflow.md)
- Sprint 55.3 + 53.4 (HITLPolicy / RiskPolicy infrastructure reuse)
- Sprint 53.x identity infrastructure (roles / users / RLS baseline)
