# Sprint 56.2 — Phase 56.x Integration Polish Bundle: Cat 12 Business Obs + Quota Pre/Post-Call Wiring + Admin RBAC

> **Sprint Type**: Phase 56+ second sprint — Polish Bundle (方案 A per user approval 2026-05-06) — solves blocker dependencies for Phase 56.3 SLA Monitor + Cost Ledger + Citus PoC
> **Owner Categories**: §HITL Centralization (governance role enumeration / admin RBAC) / Cat 12 Observability (tracer factory + tenant lifecycle / business domain spans) / Cat 4 Context Mgmt (token counter pre-call) / §Multi-tenant rule (quota Redis counter reconciliation)
> **Phase**: 56 (SaaS Stage 1 — 2/3 sprint of Phase 56-58 SaaS Stage 1)
> **Workload**: 4 days (Day 0-3); bottom-up est ~10 hr → calibrated commit **~6 hr** (multiplier **0.60** per AD-Sprint-Plan-4 scope-class matrix `mixed (process + integration polish)` — band 0.55-0.65, picking 0.60 mid-band)
> **Branch**: `feature/sprint-56-2-integration-polish`
> **Plan Authority**: This document (per CLAUDE.md §Sprint Execution Workflow)
> **Roadmap Source**: 15-saas-readiness.md §SLA Monitoring + §Cost Ledger (unblocking dependencies) + Sprint 56.1 retrospective Q5 (Phase 56.x carryover ADs)
> **AD logging (sub-scope)**: AD-Sprint-Plan-4 scope-class matrix `mixed` first application (53.7 was prior `mixed` data point ratio 1.01 ✅)

---

## Sprint Goal

Close **4 Phase 56.x carryover ADs** that unblock Phase 56.3 SaaS Stage 1 backend production-readiness (SLA Monitor + Cost Ledger + Citus PoC). All 4 are integration polish — wire-up of existing infrastructure, not new feature creation:

- **US-1**: AD-Cat12-BusinessObs — implement `get_tracer()` factory in `platform_layer/observability/`; thread real Tracer through chat router → BusinessServiceFactory → 5 business services (Incident / Patrol / Correlation / RootCause / Audit); 9 service methods emit Cat 12 spans with real tracer instead of `tracer=None` placeholder per Sprint 55.1 D5 + 55.2 D2 + 56.1 D4
- **US-2**: AD-QuotaEstimation-1 — replace fixed `quota_estimated_tokens_per_call=1000` config setting with Cat 4 token counter pre-call estimation; QuotaEnforcer pre-call gate uses real estimate; 56.1 hardcoded reservation eliminated
- **US-3**: AD-QuotaPostCall-1 — wire LLMResponded event hook in `_stream_loop_events` to call `quota_enforcer.record_usage(actual_tokens, reserved_tokens)` after natural loop completion; reconciles actual vs reserved tokens; over-reservation released back to daily counter
- **US-4**: AD-AdminAuth-1 — replace `require_admin_token` stub (X-Admin-Token header check against env var) with real RBAC role check via 53.4 governance role enumeration (`Role.ADMIN_TENANT` / `Role.ADMIN_PLATFORM`); admin endpoints under `api/v1/admin/` use new dependency
- **US-5**: Sprint 56.2 Closeout — cross-AD integration test (provision tenant via 53.4 RBAC + onboard with quota pre-call + chat with quota reconciliation + Cat 12 spans visible end-to-end) + retrospective + AD-Sprint-Plan-4 `mixed` 2nd application calibration verify (53.7 ratio 1.01 baseline)

Sprint 結束後:
- (a) **Cat 12 obs spans 主流量 visible** — chat router 入口到 5 business service methods 全鏈路 spans 可追蹤;Phase 56.3 SLA Monitor 可基於 spans 計算 per-tenant uptime / latency
- (b) **Quota enforcement accurate** — pre-call estimate 用 Cat 4 真 token counter(不是固定 1000);post-call reconciliation 釋放未使用 reservation;Cost Ledger (Phase 56.3) 可基於精確 token usage 計算 cost
- (c) **Admin endpoint 安全** — 53.4 RBAC role check 取代 stub token;AD-AdminAuth-1 production-ready;審計 trail 包含 actor user_id 而非 anonymous admin token
- (d) **Phase 56.3 prerequisites in place** — SLA Monitor / Cost Ledger / Citus PoC 三大 56.3 區塊的依賴 ADs 全部 closed
- (e) **AD-Sprint-Plan-4 `mixed` 2-data-point baseline** — 53.7 ratio 1.01 + 56.2 ratio (this sprint) 形成 mixed class window

**主流量驗收標準**:
- `POST /api/v1/admin/tenants` 用 53.4 RBAC role check(非 X-Admin-Token stub);non-admin user → 403
- Chat endpoint POST request → Cat 4 token counter 估算 input tokens → QuotaEnforcer 預扣;LLM 完成 → 實際 tokens reconcile → over-reservation 釋放
- Chat endpoint trace ID → span hierarchy 包含:chat_handler → business_service_call (per service method) → 9 个 obs spans 全 visible
- pytest baseline 1508 → ≥ 1525 (≥ +17 new)
- mypy --strict 0 errors on `platform_layer/observability/`, `platform_layer/tenant/quota.py`, `platform_layer/governance/`, `api/v1/admin/`
- 8 V2 lints green (含 56.1 新加 check_rls_policies)

---

## Background

### V2 進度

- **22/22 sprints (100%) main progress completed** + **Phase 56-58 SaaS Stage 1 1/3** (Sprint 56.1 closed 2026-05-06)
- main HEAD: `a0c192dd` (Sprint 56.1 closeout PR #98)
- pytest baseline 1508 / mypy --strict 0/283 source files / 8 V2 lints 8/8 green
- 56.1 calibration `large multi-domain` 0.55 mid-band 1st application ratio **1.00 ✅ bullseye**
- 9-sprint window 5/9 in-band (53.7=1.01 / 55.2=1.10 / 55.5=1.14 / 55.6=0.92 / 56.1=1.00) — first crossing 50% threshold
- **本 sprint = Phase 56+ SaaS Stage 1 第 2 個 sprint** (2/3 of Phase 56-58 SaaS Stage 1)

### 為什麼 56.2 是 Polish Bundle 而不是 SLA Monitor + Cost Ledger

User approved 2026-05-06 session 方案 A (Polish Bundle 優先 — 解阻型):

1. **AD-Cat12-BusinessObs 是 SLA Monitor 直接前置依賴** — SLA Monitor 必須基於 Cat 12 spans 計算 per-tenant uptime / latency / error rate;若 spans 還用 `tracer=None` placeholder,SLA Monitor 建不起來
2. **AD-QuotaEstimation-1 + AD-QuotaPostCall-1 是 Cost Ledger 直接前置依賴** — Cost Ledger 必須基於精確 token usage(actual + reservation 對齐)計算 cost;56.1 fixed `quota_estimated_tokens_per_call=1000` 不夠精確
3. **AD-AdminAuth-1 是 SaaS Stage 1 安全合規前置** — SaaS Stage 1 admin API 不能用 X-Admin-Token stub 上 production;Phase 56.3 customer support / public API 都需要 RBAC 已就位
4. **Mixed class 1-day rest after 56.1 large multi-domain** — calibration window 多樣性需要;連續 2 sprint 同 class 不利 calibration 收斂
5. **AD-Sprint-Plan-4 `mixed` 2nd application** — 53.7 ratio 1.01 ✅ 為 1st mixed data point;56.2 為 2nd;mixed mean 將從 1-data-point 升到 2-data-point 較穩固
6. **49.2 cache delivery 不入 56.2** — 56.1 retrospective 提及 carryover 但 §8 Open Items 未 tracked 為明確 AD;scope 不清晰,defer to 56.x audit cycle 評估後再 schedule

### 既有結構(Day 0 探勘 grep 將驗證以下假設)

⚠️ **以下 layout 是 plan-time 推斷;Day 0 grep 將 confirm 或 catalogue 為 D-finding**:

```
backend/src/
├── platform_layer/
│   ├── observability/                       # ⚠️ Day 0 verify: 是否已存在 + helpers.py 現狀
│   │   ├── helpers.py                       # ✅ 55.3 AD-Cat12-Helpers-1 (category_span)
│   │   ├── tracer.py                        # ❌ NEW (US-1: get_tracer factory)
│   │   └── ...
│   ├── governance/
│   │   ├── role_enum.py                     # ⚠️ Day 0 verify: 53.4 Role enum 是否含 ADMIN_TENANT / ADMIN_PLATFORM
│   │   └── service_factory.py               # ✅ 53.6 ServiceFactory consolidation
│   └── tenant/                              # ✅ 56.1 (lifecycle + provisioning + plans + quota + onboarding)
│       └── quota.py                         # ⚠️ MODIFY (US-2 + US-3: pre-call estimate + post-call reconcile)
├── core/
│   ├── config/                              # ⚠️ MODIFY (US-2: drop quota_estimated_tokens_per_call setting OR add fallback flag)
│   └── feature_flags.py                     # ✅ 56.1 US-4
├── api/v1/
│   ├── admin/                               # ⚠️ MODIFY (US-4: replace require_admin_token with RBAC dep)
│   │   ├── tenants.py                       # ✅ 56.1 US-1 + US-3
│   │   └── _deps.py                         # ❌ NEW or MODIFY (US-4: get_admin_user dep)
│   └── chat/
│       └── handler.py                       # ⚠️ MODIFY (US-1: thread real tracer; US-2 + US-3: quota wire)
└── business_domain/
    └── _service_factory.py                  # ⚠️ MODIFY (US-1: BusinessServiceFactory accepts real Tracer)
```

### Sprint 56.1 retrospective Q5 對齐確認

Sprint 56.1 retrospective Q5 列出 Phase 56.x carryover ADs:
- AD-AdminAuth-1 (D13): replace stub `require_admin_token` ✅ 此 sprint US-4
- AD-QuotaEstimation-1 (D19): wire Cat 4 token counter pre-call ✅ 此 sprint US-2
- AD-QuotaPostCall-1 (D20): LLMResponded event hook reconciliation ✅ 此 sprint US-3
- AD-Cat12-BusinessObs (carryover from 55.1): thread real tracer through chat router → BusinessServiceFactory → 5 services ✅ 此 sprint US-1
- AD-Plan-4-Schema-Grep (D26+D27 process insight): defer evaluation to Phase 56.2 retro ✅ 此 sprint retro Q3 evaluate

### V2 紀律 9 項對齐確認

1. **Server-Side First** ✅ 全 server-side wire-up;tracer factory injection / quota Redis counter / RBAC role check 全 server-controlled
2. **LLM Provider Neutrality** ✅ Cat 4 token counter 透過 ChatClient ABC `count_tokens()`;不引入 SDK 直 import
3. **CC Reference 不照搬** ✅ Cat 12 spans 用 OpenTelemetry SDK(已在 49.4 引入);quota 用 Redis 模式;不抄 CC tracing 模型
4. **17.md Single-source** ✅ Tracer ABC 與 ChatClient.count_tokens / span ctx mgr 已在 17.md §Contract 12 + §Contract 8 single-source;此 sprint 是 wire-up 不重新定義
5. **11+1 範疇歸屬** ✅ US-1 = 範疇 12 / US-2+US-3 = 範疇 4 + multi-tenant / US-4 = §HITL Centralization role enum 擴展;每檔案明確歸屬一範疇;無 AP-3
6. **04 anti-patterns** ✅ AP-3 範疇歸屬合規;AP-4(Potemkin)— 4 個 AD 全有實際 wire-up + 主流量 e2e 測試;AP-6(Hybrid Bridge Debt)— 不為「Stage 2 商業 SaaS 預留」加抽象;AP-9(Verification)— US-1 wire-up 後 AgentLoop verification 仍走主流量
7. **Sprint workflow** ✅ plan → checklist → Day 0 探勘 → code → progress → retro;本文件依 56.1 plan 結構鏡射(14 sections / 4 days Day 0-3)
8. **File header convention** ✅ 所有 modify 檔案加 Modification History entry;新檔(US-1 tracer factory / US-4 _deps.py)含 file header docstring
9. **Multi-tenant rule** ✅ Quota counter per-tenant Redis key / Tracer per-trace tenant_id attribute / RBAC role check 含 tenant_id scope

---

## User Stories

### US-1: AD-Cat12-BusinessObs — Real Tracer Threading

**As** a Phase 56.3 SLA Monitor implementer
**I want** Cat 12 Tracer factory implemented and threaded through chat router → BusinessServiceFactory → 5 business services (Incident / Patrol / Correlation / RootCause / Audit) so 9 service methods emit real spans (not `tracer=None` placeholder)
**So that** Phase 56.3 SLA Monitor can compute per-tenant uptime / latency / error rate from Cat 12 span data;Sprint 55.1 D5 + 55.2 D2 + 56.1 D4 carryover all closed

**Acceptance**:
- [ ] `platform_layer/observability/tracer.py` `get_tracer(name: str) -> Tracer` factory function (uses OpenTelemetry SDK initialized at app startup;reuse 49.4 tracing infra)
- [ ] BusinessServiceFactory `__init__` 接受 real Tracer instance (not `Tracer | None`);default 走 `get_tracer("business_service")`;測試可注入 mock
- [ ] Chat router(`api/v1/chat/handler.py`)初始化 BusinessServiceFactory 時傳入 `tracer=get_tracer("chat_handler")`(替換 56.1 D2 註解 `tracer=None`)
- [ ] 5 business services(IncidentService / PatrolService / CorrelationService / RootCauseService / AuditService)的 9 service methods 透過 `category_span` ctx mgr 正確發出 spans;每 span attrs 含 `tenant_id`, `service_name`, `method_name`, `category_id=12`(per .claude/rules/observability-instrumentation.md 5 必埋點)
- [ ] mypy --strict 0 errors;8 V2 lints green
- [ ] 5 unit tests(`get_tracer` factory / BusinessServiceFactory tracer wiring / 1 service emits real span / 1 service span attrs correct / chat router → service span hierarchy)
- [ ] 1 integration test(`test_chat_request_emits_full_span_hierarchy` — POST chat → assert span tree 包含 chat_handler → business_service_call → service_method 至少 3 層 + tenant_id attr 在所有 spans)

### US-2: AD-QuotaEstimation-1 — Cat 4 Token Counter Pre-Call

**As** a Phase 56.3 Cost Ledger implementer
**I want** QuotaEnforcer pre-call gate uses Cat 4 ChatClient `count_tokens(messages)` for accurate input token estimation (replacing fixed `quota_estimated_tokens_per_call=1000` setting from 56.1 D19)
**So that** Cost Ledger can compute precise cost based on actual estimated input tokens before LLM call;over-reservation reduced from worst-case 1000 to actual ≈100-500 typical

**Acceptance**:
- [ ] `platform_layer/tenant/quota.py` `QuotaEnforcer.estimate_pre_call_tokens(messages, tools, model_name) -> int` 新方法(via ChatClient adapter `count_tokens`)
- [ ] Chat router pre-LLM call 改用 `quota.check_and_reserve(tenant_id, estimated_tokens)`(取代 56.1 fixed 1000 reservation)
- [ ] `core/config/settings.py` `quota_estimated_tokens_per_call` setting 標為 deprecated(保留 1 sprint 作 fallback;Phase 56.3 移除);加 docstring 註明
- [ ] Estimation failure(adapter 不支援 count_tokens) → graceful fallback to settings.quota_estimated_tokens_per_call(audit log warning)
- [ ] mypy --strict 0 errors;8 V2 lints green
- [ ] 3 unit tests(`estimate_pre_call_tokens` happy path / count_tokens fallback / quota check uses estimate)
- [ ] 1 integration test(`test_chat_quota_uses_real_estimate` — POST chat with 200-token prompt → assert reservation ≈ 200 not 1000)

### US-3: AD-QuotaPostCall-1 — LLMResponded Reconciliation

**As** a Phase 56.3 Cost Ledger implementer
**I want** post-LLM-call reconciliation hook in chat router `_stream_loop_events` that calls `quota_enforcer.record_usage(actual_input_tokens, actual_output_tokens, reserved_tokens)` releasing over-reservation back to daily counter
**So that** quota daily counter reflects real usage(input+output tokens)not over-conservative reservation;Cost Ledger ledger entries match actual API spend

**Acceptance**:
- [ ] `platform_layer/tenant/quota.py` `QuotaEnforcer.record_usage(tenant_id, actual_input, actual_output, reserved) -> None` 新方法(Redis DECRBY for over-reservation release;LLM output tokens 加總)
- [ ] Chat router `_stream_loop_events` LLMResponded event handler hook(reuse 50.2 SSE event 機制)→ on completion / error / cancel → call `record_usage`
- [ ] Reservation release atomic via Redis MULTI/EXEC(mirror 53.2 RedisBudgetStore + 56.1 QuotaEnforcer pattern)
- [ ] Audit log entry per reconciliation(actor / tenant_id / actual_input / actual_output / reserved / delta)
- [ ] mypy --strict 0 errors;8 V2 lints green
- [ ] 3 unit tests(`record_usage` happy path / over-reservation released / cancel/error path also reconciles)
- [ ] 1 integration test(`test_chat_quota_reconciliation_releases_overreservation` — POST chat reserves 500 → actual 350 → daily counter 釋放 150)

### US-4: AD-AdminAuth-1 — RBAC Role Check Replacement

**As** a SaaS platform admin
**I want** admin endpoints under `api/v1/admin/` use 53.4 governance Role enumeration (`Role.ADMIN_TENANT` / `Role.ADMIN_PLATFORM`) instead of 56.1 D13 stub `require_admin_token` (X-Admin-Token header check against env var)
**So that** admin actions audit trail records actor user_id + role(not anonymous token);non-admin user → 403;multi-tenant admin separation possible(tenant admin 不能 cross-tenant)

**Acceptance**:
- [ ] `platform_layer/governance/role_enum.py` 確認(or extend) `Role` enum 含 `ADMIN_TENANT` + `ADMIN_PLATFORM`(per Day 0 探勘 — 若已存在 reuse)
- [ ] `api/v1/admin/_deps.py`(NEW or MODIFY)`get_admin_user(roles: list[Role]) -> User` FastAPI dependency factory;接受 required roles list;驗證 current user 至少有 1 role
- [ ] `api/v1/admin/tenants.py` 4 endpoints (POST tenants / GET onboarding-status / POST onboarding/{step} / GET tenants/{id}) 改用 `Depends(get_admin_user(roles=[Role.ADMIN_PLATFORM]))`(刪除 56.1 require_admin_token stub)
- [ ] `core/config/settings.py` 移除 `admin_token` setting(若有)+ 文件化於 `.env.example` 該欄位廢棄
- [ ] 403 error message 友善(不洩漏 user 是否存在 / 是否 authenticated)
- [ ] mypy --strict 0 errors;8 V2 lints green
- [ ] 3 unit tests(`get_admin_user` happy / wrong role 403 / unauthenticated 401)
- [ ] 2 integration tests(`test_admin_tenants_post_with_admin_role` / `test_admin_tenants_post_without_admin_role_403`)

### US-5: Sprint 56.2 Closeout — Cross-AD Integration Test + Retrospective

**As** a Sprint 56.2 author
**I want** end-to-end integration test that exercises all 4 ADs in single chat session(provision tenant via RBAC → onboarding with quota pre-call estimate → chat with quota post-call reconciliation → Cat 12 spans visible at every layer)+ Day 3 retrospective + AD-Plan-4-Schema-Grep 評估 + closeout PR
**So that** Sprint 56.2 verified production-deployable;Phase 56.3 SLA Monitor + Cost Ledger 直接可用 56.2 infrastructure

**Acceptance**:
- [ ] `tests/integration/api/test_phase56_2_e2e.py` cross-AD integration test:provision tenant(US-4 RBAC)→ onboard 6-step → chat (US-2 pre-call estimate + US-3 post-call reconcile + US-1 Cat 12 spans)→ assert spans + quota counter + RBAC audit trail consistent
- [ ] Day 3 retrospective.md(6 必答):
  - Q1 Sprint goal achievement(4 ADs closed?Phase 56.x integration polish complete?)
  - Q2 Calibration verify — `actual_total_hr / 6` ratio(期望 [0.85, 1.20]);record `mixed` 2nd data point(53.7=1.01 baseline);if ∈ band → mixed mean 從 1-data-point 升到 2-data-point;else log AD-Sprint-Plan-6
  - Q3 D-findings drift catalogue + AD-Plan-4-Schema-Grep 評估(56.1 D26+D27 column-level drift evidence — 1 sprint 不夠;defer to 56.3 retro for 2nd data point)
  - Q4 V2 紀律 9 項 review
  - Q5 Phase 56.2 summary + Phase 56.3 readiness — Phase 56.3 candidate scope confirmed(SLA Monitor + Cost Ledger + Citus PoC + Compliance partial);user approve direction 必先
  - Q6 Solo-dev policy validation
- [ ] Closeout PR(SITUATION-V2 §9 milestones + CLAUDE.md status block + memory snapshot `project_phase56_2_polish_bundle.md`)
- [ ] mypy --strict 0 errors;8 V2 lints green;LLM SDK leak 0
- [ ] Final pytest count ≥ 1525(1508 + 17 new = 5+1+3+1+3+1+3+2 unit/integration)

---

## Technical Specifications

### Architecture: Tracer Factory + Threading

```
App startup:
  init_otel_tracer_provider()  # 49.4 baseline

get_tracer("chat_handler"):
  return tracer_provider.get_tracer("chat_handler", version="56.2")

Chat router:
  tracer = get_tracer("chat_handler")
  service_factory = BusinessServiceFactory(db, tenant_id, tracer)
                                            ─┴─ real, not None

BusinessServiceFactory.get_incident_service():
  return IncidentService(db, tenant_id, tracer=self.tracer)

IncidentService.create_incident():
  async with category_span("incident_create", tracer=self.tracer, attrs={...}):
    ...
```

### Architecture: Quota Pre/Post-Call Reconciliation

```
QuotaEnforcer (per request):
  1. estimate = await self.estimate_pre_call_tokens(messages, tools, model)
                                  ↑ Cat 4 ChatClient.count_tokens()
  2. await self.check_and_reserve(tenant_id, estimate)
                                  ↑ Redis INCR by `estimate`; raise 429 if over quota

  [LLM call happens]

  3. on LLMResponded / error / cancel:
       actual_input = response.usage.prompt_tokens
       actual_output = response.usage.completion_tokens
       await self.record_usage(tenant_id, actual_input, actual_output, reserved=estimate)
                                  ↑ Redis MULTI/EXEC:
                                    - DECRBY by (reserved - actual_input)  # release over-reservation
                                    - INCRBY by actual_output               # add output tokens
```

### Architecture: RBAC Admin Dependency

```
api/v1/admin/_deps.py:
  def get_admin_user(roles: list[Role]) -> Callable:
      async def _dependency(
          db: AsyncSession = Depends(get_db),
          current_user: User = Depends(get_current_user),  # 53.x identity
      ) -> User:
          user_roles = await query_user_roles(db, current_user.id)
          if not any(r in roles for r in user_roles):
              raise HTTPException(403, "Insufficient role")
          return current_user
      return _dependency

api/v1/admin/tenants.py:
  @router.post("/tenants")
  async def create_tenant(
      payload: TenantCreateRequest,
      admin: User = Depends(get_admin_user(roles=[Role.ADMIN_PLATFORM])),
      ...
  ): ...
```

### File Layout

```
backend/src/
├── platform_layer/
│   ├── observability/
│   │   └── tracer.py                     NEW — get_tracer(name) factory
│   ├── governance/
│   │   └── role_enum.py                  MODIFIED (if missing ADMIN_TENANT/ADMIN_PLATFORM)
│   └── tenant/
│       └── quota.py                      MODIFIED — estimate_pre_call_tokens + record_usage
├── core/
│   └── config/
│       └── settings.py                   MODIFIED — deprecate quota_estimated_tokens_per_call; remove admin_token
├── api/v1/
│   ├── admin/
│   │   ├── _deps.py                      NEW — get_admin_user dep factory
│   │   └── tenants.py                    MODIFIED — replace require_admin_token with Depends(get_admin_user)
│   └── chat/
│       └── handler.py                    MODIFIED — thread real tracer + quota pre-call estimate + post-call reconcile
├── business_domain/
│   └── _service_factory.py               MODIFIED — accept real Tracer (not Tracer | None)

backend/tests/
├── unit/
│   ├── platform_layer/
│   │   ├── observability/test_tracer.py          NEW
│   │   ├── tenant/test_quota_estimation.py       NEW
│   │   └── tenant/test_quota_reconciliation.py   NEW
│   └── api/v1/admin/test_admin_deps.py           NEW
└── integration/
    └── api/
        ├── test_chat_quota_estimation.py         NEW
        ├── test_chat_quota_reconciliation.py     NEW
        ├── test_admin_tenants_rbac.py            NEW
        └── test_phase56_2_e2e.py                 NEW

docs/03-implementation/agent-harness-execution/
└── phase-56/
    └── sprint-56-2/
        ├── progress.md                  NEW — Day 0-3 progress
        └── retrospective.md             NEW — 6 必答 + AD calibration verify
```

---

## Acceptance Criteria

### Sprint-Wide

- [ ] V2 主進度 22/22 (100%) 不變;Phase 56-58 SaaS Stage 1 進度 1/3 → 2/3
- [ ] All 8 V2 lints green
- [ ] mypy --strict 0 errors
- [ ] LLM SDK leak: 0
- [ ] Anti-pattern checklist 11 項對齐
- [ ] 5 active CI checks green
- [ ] Test count baseline 1508 → ≥ 1525 (+17 new = 5 unit US-1 + 3 unit US-2 + 3 unit US-3 + 3 unit US-4 + 4 integration cross-AD)
- [ ] AD-Sprint-Plan-4 `mixed` 2nd application captured + verdict logged in retro Q2
- [ ] AD-Plan-4-Schema-Grep evaluation logged in retro Q3 (defer to 56.3 retro for 2nd data point per 1-sprint evidence rule)

### Per-User-Story

詳見 §User Stories acceptance per US.

---

## Day-by-Day Plan

### Day 0 — Setup + Day-0 兩-prong 探勘 + Pre-flight Verify

- 0.1 Branch + plan + checklist commit
- 0.2 Day-0 兩-prong 探勘(per AD-Plan-3 promoted)— **Prong 1 Path Verify**:`platform_layer/observability/tracer.py` 是否存在(expect: not exist)/ `platform_layer/governance/role_enum.py` 結構 / `api/v1/admin/_deps.py` 是否存在 / 56.1 `quota.py` 現狀 / 49.4 OpenTelemetry SDK 初始化點;**Prong 2 Content Verify**:53.4 governance `Role` enum 是否含 ADMIN_TENANT / ADMIN_PLATFORM(若不含,US-4 scope 含 enum extension)/ Cat 4 ChatClient ABC `count_tokens` 簽名 / 50.2 SSE LLMResponded event 結構 / 55.1 BusinessServiceFactory `__init__` 接受 tracer 參數類型(`Tracer | None`?)/ 56.1 quota.py `check_and_reserve` 與 settings `quota_estimated_tokens_per_call` 使用點
- 0.3 Calibration multiplier pre-read(9-sprint window 5/9 in-band per 56.1 retro;`mixed` 1-data-point 53.7=1.01;此 sprint 為 mixed 2nd application 取 0.60 mid-band)
- 0.4 Pre-flight verify(pytest baseline 1508 / 8 V2 lints baseline / mypy baseline / LLM SDK leak baseline)
- 0.5 Day 0 progress.md commit + push;catalogue D-findings;若 scope shift > 20% revise plan §Risks per AD-Plan-1 audit-trail

### Day 1 — US-1 AD-Cat12-BusinessObs + US-4 AD-AdminAuth-1

- 1.1 `platform_layer/observability/tracer.py` `get_tracer` factory(reuse 49.4 OTel)
- 1.2 BusinessServiceFactory `__init__` 接受 real Tracer(not Optional);default fallback to `get_tracer("business_service")`;測試可注入 mock
- 1.3 Chat router 初始化 BusinessServiceFactory 傳入 real tracer
- 1.4 5 unit US-1 + 1 integration US-1
- 1.5 `platform_layer/governance/role_enum.py` ADMIN_TENANT / ADMIN_PLATFORM enum extension(if needed per Day 0)
- 1.6 `api/v1/admin/_deps.py` `get_admin_user` factory
- 1.7 `api/v1/admin/tenants.py` 4 endpoints 改用 RBAC dep
- 1.8 3 unit US-4 + 2 integration US-4
- 1.9 mypy + 8 V2 lints green
- 1.10 Day 1 progress.md + commit + push

### Day 2 — US-2 AD-QuotaEstimation-1 + US-3 AD-QuotaPostCall-1

- 2.1 `platform_layer/tenant/quota.py` `estimate_pre_call_tokens` 方法(via Cat 4 ChatClient.count_tokens)
- 2.2 Chat router pre-LLM 改用 estimate(取代 fixed 1000 reservation)
- 2.3 Settings `quota_estimated_tokens_per_call` 標 deprecated(保留 fallback 1 sprint)
- 2.4 3 unit US-2 + 1 integration US-2
- 2.5 `platform_layer/tenant/quota.py` `record_usage` 方法(Redis MULTI/EXEC release over-reservation + add output tokens)
- 2.6 Chat router `_stream_loop_events` LLMResponded hook → `record_usage`
- 2.7 3 unit US-3 + 1 integration US-3
- 2.8 mypy + 8 V2 lints green
- 2.9 Day 2 progress.md + commit + push

### Day 3 — US-5 Closeout Ceremony

- 3.1 Cross-AD e2e integration test `test_phase56_2_e2e.py`(provision RBAC + onboard quota pre-call + chat reconcile + Cat 12 spans visible)
- 3.2 Final pytest + 8 V2 lints + LLM SDK leak verify
- 3.3 retrospective.md(6 必答 + AD-Sprint-Plan-4 mixed 2nd app calibration verify + AD-Plan-4-Schema-Grep evaluation)
- 3.4 Open PR → CI green → solo-dev squash merge to main
- 3.5 Closeout PR(SITUATION-V2 §9 + CLAUDE.md + memory)
- 3.6 Memory snapshot + final push

---

## File Change List

| File | Status | Lines (est) |
|------|--------|-------------|
| `platform_layer/observability/tracer.py` | NEW | ~50 |
| `platform_layer/governance/role_enum.py` | MODIFIED | +10 |
| `platform_layer/tenant/quota.py` | MODIFIED | +80 |
| `core/config/settings.py` | MODIFIED | +5/-3 |
| `api/v1/admin/_deps.py` | NEW | ~60 |
| `api/v1/admin/tenants.py` | MODIFIED | +5/-10 |
| `api/v1/chat/handler.py` | MODIFIED | +30 |
| `business_domain/_service_factory.py` | MODIFIED | +5/-3 |
| Tests (~17 new) | NEW | ~400 |
| `docs/.../sprint-56-2/{progress,retrospective}.md` | NEW | ~500 |
| `memory/project_phase56_2_polish_bundle.md` | NEW | ~50 |

**Total**: ~250 source LOC + ~400 test LOC + ~550 docs LOC

---

## Dependencies & Risks

### Dependencies (must exist before code starts)

- ⚠️ Phase 49.4 OpenTelemetry SDK 已初始化 — Day 0 grep verify
- ⚠️ Cat 4 ChatClient ABC `count_tokens(messages, tools=None) -> int` 已實作 — Day 0 grep verify (per 17.md Contract 8)
- ⚠️ 53.4 governance `Role` enum 已存在 — Day 0 grep verify(若缺 ADMIN_TENANT / ADMIN_PLATFORM,US-4 scope 含 enum extension ~30 min)
- ⚠️ 53.x identity `User` ORM + `query_user_roles` helper — Day 0 grep verify
- ⚠️ 50.2 SSE LLMResponded event in `_stream_loop_events` — Day 0 grep verify
- ⚠️ 55.1 BusinessServiceFactory `__init__` 接受 tracer 參數 — Day 0 grep verify(若不接受,需 modify factory ABC)
- ⚠️ 56.1 QuotaEnforcer.check_and_reserve 已實作 — Day 0 grep verify
- ⚠️ 56.1 Settings `quota_estimated_tokens_per_call` 已存在 — Day 0 grep verify

### Risk Classes (per sprint-workflow.md §Common Risk Classes)

**Risk Class A (paths-filter vs required_status_checks)**: 已 closed by 55.6 Option Z (paths-filter retired永久);此 sprint 不適用。

**Risk Class B (cross-platform mypy unused-ignore)**: low risk;此 sprint 大多 modify 既有檔案,新檔少。

**Risk Class C (module-level singleton across event loops)**: MEDIUM RELEVANCE — Tracer factory `get_tracer` 可能用 module-level cache(OTel SDK 內部 already singleton-style)。Mitigation: per-test reset via OTel SDK API;不在 conftest.py 加 reset fixture(OTel 自己處理)。

### Day 0 探勘 D-findings (catalogued during Day 0 兩-prong 探勘)

> 起草時無 D-findings;Day 0 探勘後 fill in this table per AD-Plan-1 + AD-Plan-3 promoted。

### Sprint-specific Risks

| Risk | Mitigation |
|------|-----------|
| 53.4 Role enum 不含 ADMIN_TENANT / ADMIN_PLATFORM | Day 0 grep verify;若缺則 US-4 scope +30 min 加 enum value + Alembic migration(Day 0 即決定是否需要;若是 → Day 1 morning extend plan) |
| BusinessServiceFactory `__init__` 簽名變更 breaking change for 5 services | 5 services constructor 接受 `tracer: Tracer | None = None` default(向後相容);chat router 顯式傳 tracer;測試保持 None default |
| Cat 4 ChatClient `count_tokens` 不存在或簽名異 | Day 0 grep verify;若簽名異(e.g. 不接受 tools 參數)→ US-2 fallback 用 simpler estimation(message length × 4);AD-QuotaEstimation-2 logged for next sprint |
| 50.2 SSE LLMResponded event hook 不存在 | Day 0 grep verify;若缺 hook,US-3 加 SSE event emission(scope +1 hr);若 chat router 結構不同需 architecture review pause |
| Quota Redis race condition under load | MULTI/EXEC atomic mirror 56.1 + 53.2 pattern;單 worker 測試夠;multi-worker production load test → Phase 56.3 SLA Monitor 整合測試 |
| `mixed` 0.60 mult 2nd app 預估偏差 | 若 ratio > 1.20 → AD-Sprint-Plan-6 lift(0.60 → 0.70);若 < 0.85 → AD-Sprint-Plan-6 reduce(0.60 → 0.50);每 case logged in retro Q2 |
| OTel tracer 在測試環境 noisy / context bleed | Test fixture clean tracer state per test;OTel SDK `force_flush` + `shutdown` between integration tests |

---

## Workload

> **Bottom-up est ~10 hr → calibrated commit ~6 hr (multiplier 0.60 per AD-Sprint-Plan-4 scope-class matrix `mixed (process + integration polish)` 2nd application)**
> **9-sprint window 5/9 in-band(`mixed` 1-data-point 53.7=1.01)** — `mixed` 從 AD-Sprint-Plan-4 matrix 取 0.55-0.65 band, 取 0.60 mid

| US | Bottom-up (hr) |
|----|---------------|
| US-1 AD-Cat12-BusinessObs (tracer factory + threading + 5 services + 6 tests) | 3.5 |
| US-2 AD-QuotaEstimation-1 (Cat 4 wire + fallback + 4 tests) | 1.5 |
| US-3 AD-QuotaPostCall-1 (LLMResponded hook + reconcile + 4 tests) | 2 |
| US-4 AD-AdminAuth-1 (RBAC dep + 4 endpoints update + 5 tests) | 1.5 |
| US-5 Closeout (e2e test + retro + ceremony) | 1.5 |
| **Total bottom-up** | **10** |
| **× 0.60 calibrated** | **6** |

Day 3 retrospective Q2 must verify: `actual_total_hr / 6 → ratio` compared to [0.85, 1.20] band;document delta + log calibration verdict for `mixed` class 2nd data point。

---

## Out of Scope

- ❌ SLA Monitor implementation — Phase 56.3
- ❌ Cost Ledger per-tenant aggregation + ledger DB schema — Phase 56.3
- ❌ Citus PoC — Phase 56.3
- ❌ Compliance partial (GDPR right-to-erasure) — Phase 56.3
- ❌ Frontend Onboarding Wizard UI — Phase 56.3
- ❌ DR + WAL streaming + cross-region replication — Phase 56.3
- ❌ Status Page / Customer Support tooling — Phase 56.3
- ❌ Stripe / 月結 invoice / billing run — Stage 2 commercial SaaS
- ❌ `quota_estimated_tokens_per_call` setting 完全移除 — 此 sprint 標 deprecated;Phase 56.3 移除(留 1 sprint fallback)
- ❌ 49.2 cache infrastructure delivery — 56.1 retro 提及但 §8 未 tracked;defer 56.x audit cycle 評估後再 schedule
- ❌ Multi-worker quota production load test — Phase 56.3 SLA Monitor 整合測試
- ❌ Real Teams welcome notification(56.1 provisioning step 2.8 stub remains)— Phase 56.3
- ❌ Real Qdrant namespace + system memory seeding(56.1 provisioning step 2.4-2.5 stub remains)— Phase 56.x
- ❌ AD-Plan-4-Schema-Grep formal promotion — defer to 56.3 retro for 2nd data point(per 1-sprint evidence rule);此 sprint retro Q3 評估記錄
- ❌ AD-Sprint-Plan-2 / AD-Phase56-Calibration formal closure — already superseded by AD-Sprint-Plan-4 per 55.6 triage cleanup;不再追蹤

---

## AD Carryover Sub-Scope

### AD-Cat12-BusinessObs (closure plan via US-1)

**Source**: Sprint 55.1 D5 + 55.2 D2 + 56.1 D4 — `tracer=None` placeholder accumulated across 3 sprints;Cat 12 obs spans 主流量 visible 是 SLA Monitor 前置依賴

**Closure plan**:
1. US-1 implement `get_tracer` factory + thread real Tracer through chat → BusinessServiceFactory → 5 services
2. 9 service methods 透過 `category_span` ctx mgr 發出 spans(無變更 spans 內容,只 wire real tracer 替代 None)
3. Day 1 完成 + integration test verifies span hierarchy
4. Sprint 56.2 closure 後 AD-Cat12-BusinessObs 標 ✅ closed in §8 Open Items

### AD-QuotaEstimation-1 (closure plan via US-2)

**Source**: Sprint 56.1 D19 — `quota_estimated_tokens_per_call=1000` fixed setting 不精確;Cost Ledger 需要精確 input token estimate

**Closure plan**:
1. US-2 wire Cat 4 ChatClient.count_tokens to QuotaEnforcer.estimate_pre_call_tokens
2. Settings `quota_estimated_tokens_per_call` 標 deprecated;Phase 56.3 移除
3. Sprint 56.2 closure 後 AD-QuotaEstimation-1 標 ✅ closed in §8

### AD-QuotaPostCall-1 (closure plan via US-3)

**Source**: Sprint 56.1 D20 — Quota daily counter 缺 post-call reconciliation;over-reservation 不釋放;Cost Ledger 無法 match actual API spend

**Closure plan**:
1. US-3 implement `record_usage` with Redis MULTI/EXEC release over-reservation + add output tokens
2. Chat router `_stream_loop_events` LLMResponded hook 完成 / error / cancel 都 reconcile
3. Sprint 56.2 closure 後 AD-QuotaPostCall-1 標 ✅ closed in §8

### AD-AdminAuth-1 (closure plan via US-4)

**Source**: Sprint 56.1 D13 — `require_admin_token` 是 X-Admin-Token header check stub;不能上 production

**Closure plan**:
1. US-4 implement `get_admin_user(roles)` FastAPI dep factory using 53.4 Role enum
2. 4 admin endpoints 改用 RBAC dep;Settings `admin_token` 移除
3. Sprint 56.2 closure 後 AD-AdminAuth-1 標 ✅ closed in §8

### AD-Sprint-Plan-4 `mixed` 2nd application

**Source**: Sprint 55.3 retrospective Q2 (calibration matrix proposed) → 53.7 retro 1.01 baseline (mixed 1-data-point) → 此 sprint 為 mixed 2nd application

**Closure plan**:
1. Sprint 56.2 plan §Workload uses **0.60** for `mixed` class (2nd application)
2. Day 3 retrospective Q2 computes `actual / 6`
3. If ratio ∈ [0.85, 1.20] → record `mixed` 2-data-point baseline (53.7=1.01 + 56.2=ratio);mixed mean 計算
4. If ratio < 0.85 → log AD-Sprint-Plan-6 (lower 0.60 → 0.50)
5. If ratio > 1.20 → log AD-Sprint-Plan-6 (raise 0.60 → 0.70)
6. mixed window 從 1 → 2 data points;3 data points 之前不調整 mid-band

### AD-Plan-4-Schema-Grep evaluation (defer)

**Source**: Sprint 56.1 retrospective Q3 process insight — D26+D27 column-level drift caught at first test run;考慮擴展 Prong 2 Content Verify 含 schema column grep at Day 0

**Closure plan**:
1. Day 3 retrospective Q3 evaluate evidence(56.1 1-sprint;此 sprint Day 0 探勘是否再現 column-level drift?)
2. 1-sprint evidence 不足以 promote;defer evaluation to Phase 56.3 retro for 2nd data point per 1-sprint evidence rule
3. AD-Plan-4-Schema-Grep 保持 candidate status(不 promoted;不 dropped)

---

## Definition of Done

- [ ] All 5 USs acceptance criteria met
- [ ] Test count ≥ 1525 (1508 + 17 new)
- [ ] mypy --strict 0 errors
- [ ] 8 V2 lints green
- [ ] LLM SDK leak: 0
- [ ] Anti-pattern checklist 11 項對齐
- [ ] AD-Cat12-BusinessObs / AD-QuotaEstimation-1 / AD-QuotaPostCall-1 / AD-AdminAuth-1 全 ✅ closed in SITUATION §8
- [ ] AD-Sprint-Plan-4 `mixed` 2nd application captured + verdict logged
- [ ] AD-Plan-4-Schema-Grep evaluation logged (defer to 56.3 retro)
- [ ] Cross-AD e2e integration test passed (provision RBAC + onboard quota pre-call + chat reconcile + Cat 12 spans visible)
- [ ] PR opened, CI green (5 active checks), solo-dev merged to main
- [ ] Closeout PR merged
- [ ] SITUATION-V2 + memory + CLAUDE.md updated to **Phase 56-58 SaaS Stage 1 2/3 (Sprint 56.2 closed)**
- [ ] Phase 56.3 readiness checklist documented in retrospective Q5 (next sprint candidate scope: SLA Monitor + Cost Ledger + Citus PoC + Compliance partial)

---

## References

- 15-saas-readiness.md §SLA Monitoring + §Cost Ledger (unblocking dependencies for Phase 56.3)
- 17-cross-category-interfaces.md §Contract 8 ChatClient.count_tokens + §Contract 12 Tracer
- 10-server-side-philosophy.md §原則 1 Server-Side First + §multi-tenant
- 14-security-deep-dive.md §RBAC + §multi-tenant tenant_id propagation
- .claude/rules/observability-instrumentation.md (5 必埋點 + ctx mgr pattern)
- .claude/rules/multi-tenant-data.md (3 鐵律)
- .claude/rules/sprint-workflow.md §Step 2.5 Day-0 兩-prong 探勘 + §Common Risk Classes
- Sprint 56.1 plan + checklist (format template per AD-Sprint-Plan-1)
- Sprint 56.1 retrospective Q5 (Phase 56.x carryover ADs source)
- Sprint 53.7 (`mixed` class 1st data point ratio 1.01 baseline)
- Sprint 53.4 (governance Role enum + RBAC infrastructure)
- Sprint 55.1 (BusinessServiceFactory pattern)
- Sprint 49.4 (OpenTelemetry SDK initialization)
