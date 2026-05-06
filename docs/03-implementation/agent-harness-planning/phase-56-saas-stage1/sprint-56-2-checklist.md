# Sprint 56.2 — Phase 56.x Integration Polish Bundle: Cat 12 Business Obs + Quota Pre/Post-Call Wiring + Admin RBAC — Checklist

**Plan**: [sprint-56-2-plan.md](sprint-56-2-plan.md)
**Branch**: `feature/sprint-56-2-integration-polish`
**Day count**: 4 (Day 0-3) | **Bottom-up est**: ~10 hr | **Calibrated commit**: ~6 hr (multiplier **0.60** per AD-Sprint-Plan-4 scope-class matrix `mixed (process + integration polish)` 2nd application; reserved 0.55-0.65 band, picking 0.60 mid-band)

> **格式遵守**: 每 Day 同 56.1 結構(progress.md update + sanity + commit + verify CI)。每 task 3-6 sub-bullets(case / DoD / Verify command)。Per AD-Lint-2 (53.7) — 不寫 per-day calibrated hour targets;只寫 sprint-aggregate calibration verify in retro。Per AD-Plan-3 promoted (55.6) — Day 0 兩-prong 探勘(Path Verify + Content Verify)是 mandatory。Day count 4(scope-difference via content not structure)— 對比 56.1 31 hr/5 days,此 sprint 10 hr/4 days。

---

## Day 0 — Setup + Day-0 兩-prong 探勘 + Pre-flight Verify

### 0.1 Branch + plan + checklist commit
- [ ] **Verify on main + clean** — `git status --short` empty + HEAD `a0c192dd`(post-PR #98 56.1 closeout)
- [ ] **Create branch + push plan/checklist** — `git checkout -b feature/sprint-56-2-integration-polish`
- [ ] **Stage + commit plan + checklist + push branch** — commit msg `chore(docs, sprint-56-2): plan + checklist for Phase 56.2 integration polish bundle`

### 0.2 Day-0 兩-prong 探勘 — verify plan §Technical Spec assertions against actual repo state

Per AD-Plan-3 promoted (55.6) — Prong 1 Path Verify + Prong 2 Content Verify;catalogue D-findings.

**Prong 1: Path Verify (existence checks)**
- [ ] **Verify `platform_layer/observability/tracer.py` exists?** — Glob check (expect: not exist; new factory)
- [ ] **Verify `platform_layer/observability/helpers.py` exists** — confirm 55.3 AD-Cat12-Helpers-1 closure (`category_span` here)
- [ ] **Verify `platform_layer/governance/role_enum.py` exists?** — Glob check + read existing Role enum;若不存在 may be `roles.py` or different file
- [ ] **Verify `api/v1/admin/_deps.py` exists?** — Glob check (expect: not exist; new factory)
- [ ] **Verify `api/v1/admin/tenants.py` `require_admin_token` reference** — `grep -n "require_admin_token" api/v1/admin/tenants.py` confirm 56.1 stub usage 4 endpoints
- [ ] **Verify `core/config/settings.py` `quota_estimated_tokens_per_call` + `admin_token`** — `grep -n "quota_estimated_tokens_per_call\|admin_token" core/config/settings.py`
- [ ] **Verify 49.4 OpenTelemetry SDK init point** — `grep -rn "TracerProvider\|set_tracer_provider" backend/src/` find baseline init location

**Prong 2: Content Verify (semantic checks)**
- [ ] **Verify Cat 4 ChatClient ABC `count_tokens` signature** — `grep -A 5 "def count_tokens" adapters/_base/chat_client.py` confirm signature `(messages, tools=None) -> int`
- [ ] **Verify 53.4 Role enum content** — read `platform_layer/governance/role_enum.py` (or whatever file) confirm whether ADMIN_TENANT / ADMIN_PLATFORM exist;catalogue as D-finding if missing
- [ ] **Verify 53.x identity `User` ORM + role query helper** — `grep -rn "class User\|def query_user_roles" infrastructure/db/models/ platform_layer/` confirm reusable
- [ ] **Verify 50.2 SSE LLMResponded event** — `grep -rn "LLMResponded\|class LLMResponded" agent_harness/orchestrator_loop/` confirm event class + emission in `_stream_loop_events`
- [ ] **Verify 55.1 BusinessServiceFactory `__init__` signature** — `grep -A 10 "class BusinessServiceFactory" business_domain/_service_factory.py` confirm tracer param exists (Optional? required?)
- [ ] **Verify 56.1 QuotaEnforcer interface** — `grep -A 10 "class QuotaEnforcer\|def check_and_reserve" platform_layer/tenant/quota.py` confirm method signatures
- [ ] **Verify 56.1 chat router quota integration** — `grep -n "QuotaEnforcer\|quota_estimated_tokens_per_call\|check_and_reserve" api/v1/chat/handler.py` confirm where 1000 reservation happens

**Catalogue findings**
- [ ] **Catalogue all D-findings in progress.md** — format `D{N}` ID + Finding + Implication;link to plan §Risks update if scope shift > 20%
- [ ] **Decide go/no-go** — findings shift scope ≤ 20% → continue Day 1;20-50% → revise plan §Acceptance + §Workload + re-confirm with user;> 50% → abort sprint redraft

### 0.3 Calibration multiplier pre-read
- [ ] **Read 56.1 retrospective Q2** — confirm 9-sprint window 5/9 in-band (53.7=1.01 / 55.2=1.10 / 55.5=1.14 / 55.6=0.92 / 56.1=1.00)
- [ ] **Confirm AD-Sprint-Plan-4 scope-class matrix** — `mixed (process + integration polish)` band 0.55-0.65;mixed 1-data-point baseline 53.7=1.01 ✅;此 sprint picks 0.60 mid-band as 2nd application
- [ ] **Compute 56.2 bottom-up** — 10 hr × 0.60 = 6 hr commit
- [ ] **Document predicted vs banked** — `mixed` 2nd application;1-data-point baseline 鎖定;若此 sprint ratio ∈ band → mixed mean 從 1 → 2 data points;若 outside band → AD-Sprint-Plan-6 logged

### 0.4 Pre-flight verify (main green baseline)
- [ ] **pytest collect baseline** — expect `1508 collected` (per 56.1 closeout main HEAD `a0c192dd`)
- [ ] **8 V2 lints via run_all.py** — `python scripts/lint/run_all.py` → 8/8 green
- [ ] **Backend full pytest baseline** — `python -m pytest` → 1508 passed / 4 skipped / 0 fail
- [ ] **mypy --strict baseline** — `python -m mypy backend/src --strict` → 0 errors
- [ ] **LLM SDK leak baseline** — `grep -rn "^(from |import )(openai|anthropic|agent_framework)" backend/src/agent_harness backend/src/business_domain backend/src/platform_layer backend/src/core` → 0

### 0.5 Day 0 progress.md
- [ ] **Create `docs/03-implementation/agent-harness-execution/phase-56/sprint-56-2/progress.md`** — Day 0 entry with探勘 findings + baseline + Day 1 plan + scope shifts (if any)
- [ ] **Commit + push Day 0** — commit msg `docs(sprint-56-2): Day 0 progress + 兩-prong 探勘 baseline`

---

## Day 1 — US-1 AD-Cat12-BusinessObs + US-4 AD-AdminAuth-1

### 1.1 Tracer factory
- [ ] **Create `platform_layer/observability/tracer.py`** — `get_tracer(name: str) -> Tracer` factory function
- [ ] **Use OpenTelemetry SDK** — `opentelemetry.trace.get_tracer(name, version="56.2")`(reuse 49.4 TracerProvider)
- [ ] **Idempotent** — same name returns same tracer (OTel SDK 內部 cached)
- [ ] **File header docstring** — Purpose / Category 12 / Created / Modification History
- DoD: mypy strict green;import works
- Verify: `python -c "from platform_layer.observability.tracer import get_tracer; t = get_tracer('test'); print(t)"`

### 1.2 BusinessServiceFactory tracer wiring
- [ ] **Modify `business_domain/_service_factory.py`** — `__init__(db, tenant_id, tracer: Tracer)`(remove `Optional` if was Optional;default fallback = `get_tracer("business_service")`)
- [ ] **5 services constructor pass-through** — IncidentService / PatrolService / CorrelationService / RootCauseService / AuditService 全接受 tracer
- [ ] **Update file header Modification History** — Sprint 56.2 — thread real tracer (closes AD-Cat12-BusinessObs)
- DoD: mypy strict green
- Verify: `python -c "from business_domain._service_factory import BusinessServiceFactory; bf = BusinessServiceFactory(None, 'tid', None); print(bf.tracer)"`

### 1.3 Chat router thread real tracer
- [ ] **Modify `api/v1/chat/handler.py`** — replace `tracer=None  # D2: get_tracer factory deferred to Phase 56+` with `tracer=get_tracer("chat_handler")`
- [ ] **BusinessServiceFactory call site** — `BusinessServiceFactory(db, tenant_id, tracer=tracer)`
- [ ] **Update file header Modification History** — Sprint 56.2 — real tracer threaded (closes 55.1 D5 + 55.2 D2 + 56.1 D4)
- DoD: existing tests still pass;chat handler integration test span visible
- Verify: `python -m pytest backend/tests/integration/api/test_chat_quota_estimation.py -v` (will pass after Day 2;Day 1 only verify import works)

### 1.4 5 unit US-1 + 1 integration US-1
**Unit (5)**
- [ ] **test_get_tracer_returns_tracer_instance** — basic factory smoke test
- [ ] **test_get_tracer_same_name_idempotent** — same name → same tracer object
- [ ] **test_business_service_factory_accepts_real_tracer** — factory __init__ accepts non-None tracer
- [ ] **test_incident_service_emits_span_with_real_tracer** — service method emits span via category_span;assert span recorded by mock tracer collector
- [ ] **test_span_attrs_include_tenant_id_service_name_method_name** — span attrs comply with .claude/rules/observability-instrumentation.md 5 必埋點

**Integration (1)**
- [ ] **test_chat_request_emits_full_span_hierarchy** — POST chat → assert span tree 包含 chat_handler → business_service_call → service_method 至少 3 層;每 span attrs 含 tenant_id

DoD: 6 tests pass < 5s

### 1.5 Role enum extension (if needed per Day 0)
- [ ] **Read 53.4 Role enum file** (per Day 0 path verify location)
- [ ] **Add ADMIN_TENANT / ADMIN_PLATFORM if missing** — keep alphabetical or by-role-tier order;file header MHist + Sprint 56.2 — extend roles for AD-AdminAuth-1
- [ ] **Alembic migration** — if Role is DB-backed enum (likely yes);if Python enum only,no migration needed
- DoD: mypy strict green
- Verify: `python -c "from platform_layer.governance.role_enum import Role; print(Role.ADMIN_TENANT, Role.ADMIN_PLATFORM)"`

### 1.6 admin _deps.py — get_admin_user factory
- [ ] **Create `api/v1/admin/_deps.py`** — `get_admin_user(roles: list[Role]) -> Callable` FastAPI dep factory
- [ ] **Inner `_dependency`** — query current user roles → check at least 1 role in `roles` parameter list → 403 if not
- [ ] **Reuse 53.x identity `get_current_user`** — from existing FastAPI dep
- [ ] **403 error message** — "Insufficient role" (don't leak whether user authenticated;return 401 if no auth header)
- [ ] **File header docstring**
- DoD: mypy strict green
- Verify: `python -c "from api.v1.admin._deps import get_admin_user; from platform_layer.governance.role_enum import Role; print(get_admin_user([Role.ADMIN_PLATFORM]))"`

### 1.7 admin tenants.py — replace stub with RBAC dep
- [ ] **Modify `api/v1/admin/tenants.py`** — 4 endpoints (POST tenants / GET onboarding-status / POST onboarding/{step} / GET tenants/{id})
- [ ] **Replace `Depends(require_admin_token)` with `Depends(get_admin_user(roles=[Role.ADMIN_PLATFORM]))`** in all 4
- [ ] **Drop `require_admin_token` import + function** (if only used in tenants.py)
- [ ] **Settings cleanup** — `core/config/settings.py` 移除 `admin_token` field;`.env.example` 註明該欄位廢棄
- [ ] **Update file header MHist** — Sprint 56.2 — replace stub with RBAC dep (closes AD-AdminAuth-1)
- DoD: mypy strict green;existing 56.1 admin tenant tests pass with new RBAC dep
- Verify: `python -m pytest backend/tests/integration/api/test_admin_tenants.py -v`

### 1.8 3 unit US-4 + 2 integration US-4
**Unit (3)**
- [ ] **test_get_admin_user_happy_with_required_role** — user has ADMIN_PLATFORM → returns user
- [ ] **test_get_admin_user_403_without_required_role** — user has only ADMIN_TENANT but endpoint requires ADMIN_PLATFORM → 403
- [ ] **test_get_admin_user_401_unauthenticated** — no auth header → 401 (via get_current_user)

**Integration (2)**
- [ ] **test_admin_tenants_post_with_admin_role** — auth as ADMIN_PLATFORM user → POST /admin/tenants → 201
- [ ] **test_admin_tenants_post_without_admin_role_403** — auth as regular user → POST → 403

DoD: 5 tests pass < 3s

### 1.9 Day 1 sanity checks
- [ ] **mypy --strict** — 0 errors
- [ ] **black + isort + flake8** — clean
- [ ] **8 V2 lints via run_all.py** — 8/8 green
- [ ] **Backend full pytest** — 1508 + 11 (5+1 US-1 + 3+2 US-4) = 1519 passed
- [ ] **53.6 production HITL regression** — no regression
- [ ] **LLM SDK leak** — 0

### 1.10 Day 1 commit + push + progress.md
- [ ] **Stage + commit Day 1** — commit msg `feat(observability, governance, sprint-56-2): real tracer + RBAC admin dep (US-1 + US-4 close AD-Cat12-BusinessObs + AD-AdminAuth-1)`
- [ ] **Update progress.md** with Day 1 actuals + drift findings if any
- [ ] **Push to origin**

---

## Day 2 — US-2 AD-QuotaEstimation-1 + US-3 AD-QuotaPostCall-1

### 2.1 QuotaEnforcer.estimate_pre_call_tokens
- [ ] **Modify `platform_layer/tenant/quota.py`** — add `async def estimate_pre_call_tokens(self, messages, tools, model_name) -> int`
- [ ] **Via Cat 4 ChatClient.count_tokens** — `await self.chat_client.count_tokens(messages=messages, tools=tools)`
- [ ] **Graceful fallback** — if count_tokens raises NotImplementedError or returns -1 → fallback to settings.quota_estimated_tokens_per_call + audit log warning
- [ ] **Update file header MHist** — Sprint 56.2 — pre-call estimate (closes AD-QuotaEstimation-1)
- DoD: mypy strict green
- Verify: `python -m pytest backend/tests/unit/platform_layer/tenant/test_quota_estimation.py -v`

### 2.2 Chat router pre-LLM estimate wiring
- [ ] **Modify `api/v1/chat/handler.py`** — replace `quota.check_and_reserve(tenant_id, settings.quota_estimated_tokens_per_call)` with:
  ```
  estimate = await quota.estimate_pre_call_tokens(messages, tools, model_name)
  await quota.check_and_reserve(tenant_id, estimate)
  ```
- [ ] **Settings.quota_estimated_tokens_per_call** — keep as fallback; standalone usage 移除 (only used inside `estimate_pre_call_tokens` graceful fallback now)
- [ ] **Settings docstring** — mark deprecated; "Phase 56.3 will remove. Used only as fallback when Cat 4 token counter unavailable."
- [ ] **Update file header MHist**
- DoD: existing 56.1 chat tests pass
- Verify: `python -m pytest backend/tests/integration/api/test_chat_quota_estimation.py -v`

### 2.3 3 unit US-2 + 1 integration US-2
**Unit (3)**
- [ ] **test_estimate_pre_call_tokens_happy** — Cat 4 count_tokens returns 200 → estimate returns 200
- [ ] **test_estimate_pre_call_tokens_fallback** — count_tokens raises → fallback to 1000 + audit log warning
- [ ] **test_quota_check_and_reserve_uses_estimate** — request with 200-token estimate → reservation = 200 (not 1000)

**Integration (1)**
- [ ] **test_chat_quota_uses_real_estimate** — POST chat with 200-token prompt → Redis counter incremented by ~200 (not 1000);allow ±10% tokenizer variance

DoD: 4 tests pass < 5s

### 2.4 QuotaEnforcer.record_usage
- [ ] **Modify `platform_layer/tenant/quota.py`** — add `async def record_usage(self, tenant_id, actual_input, actual_output, reserved) -> None`
- [ ] **Redis MULTI/EXEC atomic** — pipeline:
  - DECRBY by `(reserved - actual_input)` (release over-reservation;若 negative,no-op)
  - INCRBY by `actual_output` (add output tokens)
- [ ] **Audit log entry** — actor / tenant_id / actual_input / actual_output / reserved / delta via 53.4 AuditLogger
- [ ] **Edge case** — actual_input > reserved (estimate too low) → no DECRBY,但加 audit warning
- [ ] **Update file header MHist** — Sprint 56.2 — post-call reconciliation (closes AD-QuotaPostCall-1)
- DoD: mypy strict green;fakeredis test
- Verify: `python -m pytest backend/tests/unit/platform_layer/tenant/test_quota_reconciliation.py -v`

### 2.5 Chat router LLMResponded hook
- [ ] **Modify `api/v1/chat/handler.py` `_stream_loop_events`** — in LLMResponded event handler (or natural completion + error + cancel paths) call:
  ```
  await quota.record_usage(
      tenant_id=tenant_id,
      actual_input=response.usage.prompt_tokens,
      actual_output=response.usage.completion_tokens,
      reserved=estimate_from_pre_call,
  )
  ```
- [ ] **Cancel / error paths** — also reconcile with `actual_output=0`(release full over-reservation)
- [ ] **Update file header MHist**
- DoD: SSE stream still works;chat handler test green
- Verify: `python -m pytest backend/tests/integration/api/test_chat_quota_reconciliation.py -v`

### 2.6 3 unit US-3 + 1 integration US-3
**Unit (3)**
- [ ] **test_record_usage_releases_over_reservation** — reserved=500, actual_input=300 → DECRBY 200 + INCRBY actual_output
- [ ] **test_record_usage_under_reservation_no_decrby** — actual_input > reserved → no DECRBY + audit warning
- [ ] **test_record_usage_cancel_path_releases_full** — cancel: actual_output=0 → DECRBY (reserved - actual_input) only

**Integration (1)**
- [ ] **test_chat_quota_reconciliation_releases_overreservation** — POST chat reserves 500 (estimated) → actual 350 input + 100 output → daily counter delta = 350 + 100 = 450 (not 500);Redis state verified

DoD: 4 tests pass < 5s

### 2.7 Day 2 sanity checks
- [ ] **mypy --strict** — 0 errors
- [ ] **black + isort + flake8** — clean
- [ ] **8 V2 lints** — 8/8 green
- [ ] **Backend full pytest** — 1519 + 4 + 4 = 1527 passed (over target 1525)
- [ ] **53.6 production HITL regression** — no regression
- [ ] **LLM SDK leak** — 0

### 2.8 Day 2 commit + push + progress.md
- [ ] **Stage + commit Day 2** — commit msg `feat(quota, sprint-56-2): pre-call estimate + post-call reconciliation (US-2 + US-3 close AD-QuotaEstimation-1 + AD-QuotaPostCall-1)`
- [ ] **Update progress.md** with Day 2 actuals
- [ ] **Push to origin**

---

## Day 3 — US-5 Closeout Ceremony

### 3.1 Cross-AD e2e integration test
- [ ] **Create `backend/tests/integration/api/test_phase56_2_e2e.py`** — exercises all 4 ADs in single flow
- [ ] **Step 1 RBAC** — auth as ADMIN_PLATFORM → POST /admin/tenants → 201 (US-4)
- [ ] **Step 2 Provisioning** — provision workflow runs;tenant moves to PROVISIONING
- [ ] **Step 3 Onboarding** — 6 steps advance;tenant transitions to ACTIVE (56.1 reuse)
- [ ] **Step 4 Chat with quota** — POST /chat with 300-token prompt → estimate 300 reserved (US-2) → LLM responds → reconcile actual 280+150 (US-3)
- [ ] **Step 5 Cat 12 spans visible** — assert span tree includes chat_handler → business_service_call → service_method;all spans tagged tenant_id (US-1)
- [ ] **Step 6 Quota counter** — final Redis counter = 280+150 (not 300) → over-reservation released
- DoD: e2e test passes < 30s
- Verify: `python -m pytest backend/tests/integration/api/test_phase56_2_e2e.py -v`

### 3.2 Final sanity verify
- [ ] **Backend full pytest** — ≥ 1525 (target 1508 + 17 new = 1525;allow over)
- [ ] **mypy --strict** — 0 errors
- [ ] **8 V2 lints** — 8/8 green
- [ ] **LLM SDK leak** — 0
- [ ] **Alembic upgrade head + downgrade base** — full cycle clean (no Day 2 ORM changes if Role enum was Python-only)

### 3.3 retrospective.md (6 必答)
- [ ] **Q1** Sprint goal achievement — 4 ADs closed?(AD-Cat12-BusinessObs + AD-QuotaEstimation-1 + AD-QuotaPostCall-1 + AD-AdminAuth-1)Phase 56-58 SaaS Stage 1 1/3 → 2/3?
- [ ] **Q2** Calibration verify — `actual_total_hr / 6` → ratio (期望 [0.85, 1.20]);record `mixed` 2nd data point;mixed window 從 1 → 2 data points;若 < 0.85 → AD-Sprint-Plan-6(0.60→0.50);若 > 1.20 → AD-Sprint-Plan-6(0.60→0.70);若 ∈ band → 鎖 0.60 stable for next mixed sprint
- [ ] **Q3** D-findings drift catalogue — Day 0 兩-prong 探勘 + Day 1-2 drift summary + AD-Plan-4-Schema-Grep evaluation(56.1 1-sprint evidence + 此 sprint Day 0 是否 column-level drift?若無 → defer 56.3 retro;若 yes → 2 data points → consider promotion)
- [ ] **Q4** V2 紀律 9 項 review — confirm all 9 still green at Phase 56.2 closure
- [ ] **Q5** Phase 56.2 summary + Phase 56.3 readiness — Phase 56.3 candidate scope (SLA Monitor + Cost Ledger + Citus PoC + Compliance partial GDPR);user will approve Phase 56.3 scope after this sprint
- [ ] **Q6** Solo-dev policy validation — solo-dev merge worked? CI green via paths-filter-retired pattern (per 55.6 Option Z)?

### 3.4 Open PR + CI green + solo-dev merge
- [ ] **Push final commit + open PR** — PR title `feat(observability, governance, quota, sprint-56-2): Phase 56.x integration polish bundle — Cat 12 BusinessObs + Quota Pre/Post-Call + Admin RBAC`
- [ ] **Wait CI green** — 5 active checks (Backend CI / V2 Lint / E2E Backend / E2E Summary / Frontend E2E chromium)
- [ ] **Solo-dev normal merge to main** — squash merge

### 3.5 Closeout PR (Phase 56.2 ceremony)
- [ ] **Branch `chore/sprint-56-2-closeout`**
- [ ] **Update SITUATION-V2-SESSION-START.md**:
  - §8 Open Items mark AD-Cat12-BusinessObs / AD-QuotaEstimation-1 / AD-QuotaPostCall-1 / AD-AdminAuth-1 as ✅ closed
  - §9 milestones row + Last Updated + Update history (Phase 56.2 closed;SaaS Stage 1 2/3 progress)
- [ ] **Update CLAUDE.md** — V2 status block "V2 重構完成 + Phase 56-58 SaaS Stage 1 進度 2/3"
- [ ] **Update memory `MEMORY.md`** — Phase 56.2 entry
- [ ] **Open closeout PR + merge** — solo-dev normal merge

### 3.6 Memory snapshot + final push
- [ ] **Create `memory/project_phase56_2_polish_bundle.md`** — Sprint 56.2 summary (4 ADs closed + cross-AD e2e + calibration verdict)
- [ ] **Verify main HEAD + working tree clean + delete merged branches** — `git status --short` empty;`gh pr merge --delete-branch` for both PRs
- [ ] **Final Phase 56.2 milestone push** — all branches synced;SITUATION + CLAUDE + memory updated
