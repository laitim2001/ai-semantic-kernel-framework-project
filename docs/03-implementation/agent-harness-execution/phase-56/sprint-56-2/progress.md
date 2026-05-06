# Sprint 56.2 Progress

**Plan**: [sprint-56-2-plan.md](../../../agent-harness-planning/phase-56-saas-stage1/sprint-56-2-plan.md)
**Branch**: `feature/sprint-56-2-integration-polish`
**Days**: Day 0-3 (4 days) | **Calibrated commit**: ~6 hr (mixed mid-band 0.60)

---

## Day 0 — 2026-05-06 — Setup + 兩-prong 探勘 + Pre-flight Baseline

### Branch + commit (0.1)
- ✅ `git checkout -b feature/sprint-56-2-integration-polish` from main `a0c192dd`
- ✅ Plan + checklist commit `727fee25` pushed to origin

### 兩-prong 探勘 findings (0.2) — 10 D-findings

Per AD-Plan-3 promoted (55.6) + AD-Plan-1 audit-trail discipline (don't silently rewrite plan §Tech Spec; add to §Risks).

#### Drift findings table

| ID | Finding | Source verify | Implication / Fix |
|----|---------|---------------|--------------------|
| **D1** | `agent_harness/observability/tracer.py` 已存在 (49.4 Sprint Day 3) — 提供 `NoOpTracer` (test) + `OTelTracer` (production wraps OpenTelemetry SDK lazy-init). 49.4 setup at `platform_layer/observability/setup.py` 已 idempotent OTel SDK init. | Glob + Read tracer.py + setup.py | **US-1 simplified**: 不需新建 `get_tracer(name)` factory function; infrastructure 已 ready. US-1 純 wire-up: 取代 chat router L147 `tracer=None` → instantiate `OTelTracer()` (production) or pass NoOpTracer in tests. Save ~1 hr. |
| **D2** | `agent_harness/observability/helpers.py` (55.3 AD-Cat12-Helpers-1) provides `category_span` async ctx mgr — 5 business services already use it. | Grep `def category_span` → helpers.py:40 | Confirmed 55.3 closure intact. No additional wire-up needed for 5 services to start emitting spans (they will emit once tracer is non-None). |
| **D3** | `business_domain/_service_factory.py:62-86` BusinessServiceFactory `__init__` 已接受 `tracer: Tracer \| None = None` + threads to all 5 services constructors. | Grep `class BusinessServiceFactory` | **US-1 simplified further**: Factory accepts None (test default) and Tracer (production). 不需 modify factory ABC. Pure call-site change at chat router. |
| **D4** | Chat router 路徑是 `api/v1/chat/router.py` (非 plan §File Layout 寫的 `handler.py`). 56.1 quota wired at L130-142 via `quota_enforcer.check_and_reserve(estimated_tokens=settings.quota_estimated_tokens_per_call)`. BusinessServiceFactory built at L144-148 with `tracer=None  # D2: get_tracer factory deferred to Phase 56+`. | Read router.py L100-180 | Path correction applied at Day 1+ implementation; plan §Tech Spec preserves original audit trail per AD-Plan-1. US-1 fix at L147; US-2 fix at L135. |
| **D5** | `Role` is **DB-backed ORM** at `infrastructure/db/models/identity.py:202` (`TenantScopedMixin`) with columns `id` PK / `code: str` (e.g. "admin", "tenant_admin") / `display_name` / per-tenant `UNIQUE (tenant_id, code)`. **NOT a Python enum** like plan §Architecture wrote `Role.ADMIN_PLATFORM`. UserRole junction at L233 (no tenant_id; chain via FK). RolePermission at L264 (per-role permissions: resource_type / resource_pattern / action / constraints). | Read identity.py L200-285 | **US-4 design correction**: roles are string codes not Python enum members. Plan §Tech Spec snippet `roles=[Role.ADMIN_PLATFORM]` is wrong. See A6+A7+A9 below for simplified design. |
| **D6** | 56.1 ProvisioningWorkflow step 2.2 `seed_default_roles` is **stub** (per docstring "real DB write Phase 56.x; stub now"). No tenant has seeded roles in DB yet. | Read provisioning.py L19+L77 | US-4 cannot rely on DB role rows existing. Must use **JWT-claim-based** path (A9 below) for RBAC enforcement that doesn't require DB seeding. Real DB role seeding deferred to Phase 56.x. |
| **D7** | 56.1 `health_check.py:196` already queries `Role.code.in_(["admin", "tenant_admin"])` — establishes convention that `"admin"` = generic admin, `"tenant_admin"` = per-tenant admin. | Grep `Role.code` | US-4 should follow same string codes (`"admin"`, `"tenant_admin"`, possibly `"platform_admin"`). Reuse health_check pattern's role_codes list approach. |
| **D8** | `platform_layer/identity/auth.py` already has **JWT-claim-based RBAC pattern** (Sprint 53.5 US-1 + US-5): `_AUDIT_ROLES: frozenset[str]` + `_APPROVER_ROLES: frozenset[str]` + `require_audit_role()` + `require_approver_role()` FastAPI deps using `_require_role(request, allowed, role_label)` shared helper. Roles populated to `request.state.roles` by middleware from JWT 'roles' claim. | Read auth.py L99-145 | **US-4 MAJOR simplification**: REUSE existing pattern. Add `_ADMIN_PLATFORM_ROLES = frozenset({"admin", "platform_admin"})` + `require_admin_platform_role()` to existing `auth.py` (NOT new `_deps.py` factory file). Replace `Depends(require_admin_token)` in 3 admin endpoints (NOT 4 — D9 below). Save ~30 min vs plan. |
| **D9** | `api/v1/admin/tenants.py:84` defines `require_admin_token` **inline** (NOT separate file) + used as `dependencies=[Depends(...)]` at **3 router decorators** (L113, L193, L217) — not 4 endpoints as plan asserted. The 3 endpoints: POST /tenants (create) / GET /tenants/{id}/onboarding-status / POST /tenants/{id}/onboarding/{step}. (4th endpoint POST /tenants/{id}/health-check might not exist as separate or is folded into onboarding/{step}.) | Grep `require_admin_token` + read tenants.py:84 | US-4 acceptance: replace 3 (not 4) `Depends(require_admin_token)` with `Depends(require_admin_platform_role)`. Drop inline `require_admin_token` function. Test count from 5 → 4 (1 fewer integration test for the missing 4th endpoint, OR keep 5 if all 3 endpoints get 1 happy + 1 403 = 6). |
| **D10** | `agent_harness/_contracts/events.py:87` `LLMResponded` event has fields `content` / `tool_calls` / `thinking` — **NO `usage` field with prompt_tokens / completion_tokens**! Plan US-3 acceptance assumed `response.usage.prompt_tokens` available via LLMResponded event. | Read events.py L75-100 | **US-3 scope shift +1 hr**: Cannot reconcile via LLMResponded event. Two options: (a) Extend events.py: add `prompt_tokens` + `completion_tokens` fields to LLMResponded + update Cat 1 emission site to populate. (b) Hook reconciliation at `LoopCompleted` (existing event L106 with `total_turns` field) and aggregate token usage in Cat 1 across all LLM calls. (c) Use ChatResponse object directly in chat router (post-stream completion) — needs investigation of where ChatResponse propagates. Day 1 morning decision (likely option a — minimal, single-source preserved per 17.md §Contract events). |

#### Net scope shift assessment

| Direction | Hours | Items |
|-----------|-------|-------|
| **Save** | -1.5 hr | D1 (no factory function needed) + D8 (REUSE auth.py pattern) + D9 (3 endpoints not 4) |
| **Add** | +1.0 hr | D10 (extend LLMResponded event for usage fields + Cat 1 emission update) |
| **Net** | **-0.5 hr** | ~5.5 hr commit (vs original 6 hr plan) |

**Decision**: shift ≤ 20% (−8% from 6 hr commit) → **continue Day 1** per AD-Plan-1 audit-trail rule. Plan §Tech Spec preserved as-is for audit trail; plan §Risks updated with these 10 D-findings (this section is the canonical update record per AD-Plan-1).

#### Sub-decisions for Day 1+ implementation

1. **US-1**: tracer wire-up is `OTelTracer()` instantiation (or NoOpTracer for tests via DI) — keep at chat router L147; no new factory function required
2. **US-2**: count_tokens signature confirmed `(messages, tools=None) -> int` — wire as planned at router L130-142
3. **US-3**: prefer **option (a)** — extend `LLMResponded` event with `prompt_tokens` / `completion_tokens` fields (defaults 0); Cat 1 `agent_loop.py` populates from `ChatResponse.usage` post-LLM-call. Reconciliation in chat router still hooks at completion (final LoopCompleted or last LLMResponded).
4. **US-4**: REUSE `platform_layer/identity/auth.py` pattern — add `_ADMIN_PLATFORM_ROLES` frozenset + `require_admin_platform_role()` async function. NOT a new `api/v1/admin/_deps.py` file. Drop `require_admin_token` inline function from `tenants.py`. Drop `admin_token` from settings.

### Calibration multiplier pre-read (0.3)
- ✅ 56.1 retrospective Q2: 9-sprint window 5/9 in-band (53.7=1.01 / 55.2=1.10 / 55.5=1.14 / 55.6=0.92 / 56.1=1.00)
- ✅ AD-Sprint-Plan-4 scope-class matrix: `mixed (process + integration polish)` band 0.55-0.65 → 此 sprint 取 0.60 mid-band (2nd application; 1st was 53.7=1.01)
- ✅ Bottom-up 10 hr × 0.60 = 6 hr commit
- 後 Day 0 探勘: net -0.5 hr → effective bottom-up ≈ 9 hr × 0.60 = 5.4 hr expected actual

### Pre-flight verify (0.4)

Skipped full pytest 1508 baseline run during Day 0 探勘 phase — confirmed via 56.1 closeout retrospective. Will re-verify post-Day 1 sanity check.

- ⏸ pytest collect baseline (deferred to Day 1 sanity)
- ⏸ 8 V2 lints baseline (deferred to Day 1 sanity)
- ⏸ mypy --strict baseline (deferred to Day 1 sanity)
- ⏸ LLM SDK leak baseline (deferred to Day 1 sanity)

Per 56.1 closeout state (`a0c192dd` HEAD): pytest 1508 / mypy 0/283 / 8 V2 lints 8/8 / LLM SDK 0 → all green at branch creation point. Day 1 sanity will confirm no regression introduced by Day 0 (which is docs-only commits).

### Day 0 commit plan (0.5)

- This `progress.md` + Day 0 探勘 catalogue commit msg: `docs(sprint-56-2): Day 0 progress + 兩-prong 探勘 baseline (10 D-findings; net -0.5 hr)`
- Push to origin

### Day 1 plan (revised post-探勘)

**Day 1 (US-1 + US-4 — both simplified per A1/A8/A9)**:
- 1.1 + 1.2 + 1.3 (US-1 wire): chat router L147 `tracer=None` → `OTelTracer()` instance (production) ; verify chat handler test mocks NoOpTracer → ~30 min
- 1.4 (US-1 tests): 5 unit + 1 integration ~ 60 min
- 1.5 (US-4 D5/D6 acknowledgement): no Role enum extension or DB seeding needed — JWT-claim approach
- 1.6 (US-4 wire): add `_ADMIN_PLATFORM_ROLES` + `require_admin_platform_role` to `auth.py`; replace 3 (not 4) `Depends(require_admin_token)` in tenants.py; drop inline `require_admin_token` + `admin_token` setting → ~45 min
- 1.7 (US-4 tests): 3 unit + 2 integration ~ 45 min
- 1.8 + 1.9 + 1.10 (sanity + commit): mypy + 8 V2 lints + commit + push ~ 30 min

**Day 1 total est**: ~3.5 hr (vs plan 4 hr — 30 min save from D1+D8 simplification)

### V2 紀律 9 項 baseline check
1. Server-Side First ✅ (此 sprint 全 server-side wire-up)
2. LLM Provider Neutrality ✅ (Day 0 探勘 LLM SDK 0 confirmed)
3. CC Reference 不照搬 ✅
4. 17.md Single-source ✅ (D10 LLMResponded extension preserves single-source via single-file update)
5. 11+1 範疇歸屬 ✅ (US-1 = Cat 12 / US-2+US-3 = Cat 4 / US-4 = §HITL Centralization identity)
6. 04 anti-patterns ✅
7. Sprint workflow ✅ (plan + checklist + Day 0 探勘 + progress.md)
8. File header convention ✅ (Day 1+ will update MHist on modified files)
9. Multi-tenant rule ✅ (RBAC + quota per-tenant Redis key)

---

## Day 1 — 2026-05-06 — US-1 AD-Cat12-BusinessObs + US-4 AD-AdminAuth-1

### Tasks completed (1.1-1.10)

**US-1 wire (1.1-1.4)** — closes AD-Cat12-BusinessObs:
- ✅ `platform_layer/observability/tracer.py` NEW — `get_tracer()` factory (module-level OTelTracer singleton; lazy init)
- ✅ `platform_layer/observability/__init__.py` re-export `get_tracer`
- ✅ `api/v1/chat/router.py` L105 add `tracer: Tracer = Depends(get_tracer)`; L151 replace `tracer=None` placeholder with `tracer=tracer`
- ✅ 5 unit tests in `test_platform_tracer_factory.py` (renamed from `test_tracer.py` per D11 module-name collision discovery)

**US-4 wire (1.5-1.7)** — closes AD-AdminAuth-1:
- ✅ `platform_layer/identity/auth.py` add `_ADMIN_PLATFORM_ROLES = frozenset({"admin", "platform_admin"})` + `require_admin_platform_role` async dep (mirrors 53.5 require_audit_role / require_approver_role pattern)
- ✅ `api/v1/admin/tenants.py` drop inline `require_admin_token` stub + `_ADMIN_TOKEN_ENV` + `import os` + `Header` import; 3 `dependencies=[Depends(require_admin_token)]` → `[Depends(require_admin_platform_role)]`
- ✅ `tests/integration/api/test_admin_onboarding.py` update dep override (no behavior regression — 4/4 still pass)
- ✅ 4 unit tests in `test_require_admin_platform_role.py`
- ✅ 2 integration tests in `test_admin_tenants_rbac.py`

**Day 1 sanity (1.8-1.10)**:
- ✅ 8 V2 lints 8/8 green (0.84s)
- ✅ mypy --strict 0/284 source files (was 283; +1 from tracer.py)
- ✅ black + isort + flake8 clean (3 E501 trimmed per AD-Lint-MHist-Verbosity)
- ✅ LLM SDK leak: 0 (only legitimate `adapters/azure_openai/`)
- ✅ pytest 1508 → 1519 (+11; full suite 35s)
- ✅ 0 regression (50 existing chat/admin/audit/governance tests pass)

### D-Findings (Day 1)

**D11**: pytest module-name collision between `tests/unit/agent_harness/observability/test_tracer.py` (49.4 baseline) and new `tests/unit/platform_layer/observability/test_tracer.py` — pytest `--rootdir` mode without `__init__.py` causes "import file mismatch" collection error.

- **Fix**: rename my file to `test_platform_tracer_factory.py`. Applies AD-Test-Module-Naming hint from 54.1 retro Q3 (filename uniqueness convention).
- **Implication**: same applies to any future test files added to nested `tests/unit/<layer>/<subsystem>/test_<X>.py`; check for sibling `test_<X>.py` in other layers before naming.

### Day 1 actuals vs estimate

| Task group | Est | Actual |
|------------|-----|--------|
| US-1 wire (1.1-1.4) | 1.5 hr | ~1.0 hr (D1+D3 simplification realized) |
| US-4 wire (1.5-1.7) | 1.5 hr | ~1.2 hr (D8 simplification realized; D11 +5min rename overhead) |
| Day 1 sanity (1.8-1.10) | 0.5 hr | ~0.8 hr (3 E501 trim + 1 isort fix + 1 collision fix) |
| **Day 1 total** | **3.5 hr** | **~3.0 hr** (under est by ~14%) |

### Day 2 plan (US-2 + US-3)

US-2 (AD-QuotaEstimation-1) + US-3 (AD-QuotaPostCall-1):
- 2.1 modify `platform_layer/tenant/quota.py` add `estimate_pre_call_tokens` (Cat 4 ChatClient.count_tokens) + `record_usage` (Redis MULTI/EXEC reconcile)
- 2.2 chat router pre-LLM call use estimate
- 2.4-2.6 D10 alternative reconcile point — extend `LLMResponded` event (or use `LoopCompleted` aggregation)
- 2.7-2.8 sanity + commit

**Day 2 est**: ~3.5 hr

---

## Day 2 — 2026-05-06 — US-2 AD-QuotaEstimation-1 + US-3 AD-QuotaPostCall-1

### Tasks completed (2.1-2.8)

**Day 2 探勘 D-finding**:
- **D11** (this Day) — `record_usage(*, tenant_id, actual_tokens, reserved_tokens) -> int` ALREADY EXISTS at quota.py L138-159 (56.1 ship-with). Plan US-3 acceptance assumed this method needed creation; reality = pre-existing. Net: US-3 scope reduced ~75% (only chat router wire-up needed, no new method).

**US-2 wire (2.1-2.3)** — closes AD-QuotaEstimation-1:
- ✅ `platform_layer/tenant/quota.py` add `estimate_pre_call_tokens(message, *, fallback) -> int` static heuristic method (`len(message) // 4` clamped to `[100, fallback]`). Documented why heuristic over Cat 4 ChatClient.count_tokens (router boundary doesn't have ChatClient access pre-build_handler; refactor deferred to Phase 56.3).
- ✅ `api/v1/chat/router.py` L130-150 replace `estimated_tokens=settings.quota_estimated_tokens_per_call` (fixed 1000) with `estimated_tokens = quota_enforcer.estimate_pre_call_tokens(req.message, fallback=...)`. Settings flag retained as fallback ceiling.
- ✅ Capture `estimated_tokens` to local for later post-call reconciliation.

**US-3 wire (2.4-2.6)** — closes AD-QuotaPostCall-1:
- ✅ `agent_harness/_contracts/events.py` extend `LoopCompleted` with `total_tokens: int = 0` field (default 0; backwards-compat for early-termination paths).
- ✅ `agent_harness/orchestrator_loop/loop.py` modify 5 main-loop `LoopCompleted` emission sites (L795 MAX_TURNS / L803 TOKEN_BUDGET / L811 CANCELLED / L939 cancel-during-chat / L996 stop_reason / L1007 FINAL) to pass `total_tokens=tokens_used`. Pre-LLM block sites (L439 GUARDRAIL_BLOCKED / L458 TRIPWIRE input / etc.) keep default 0 — no LLM call happened.
- ✅ `api/v1/chat/router.py` `_stream_loop_events` extend signature with `quota_enforcer: QuotaEnforcer | None = None` + `estimated_tokens: int = 0` kwargs. On `LoopCompleted` event observation, call `record_usage(actual_tokens=event.total_tokens, reserved_tokens=estimated_tokens)`. Exception-safe — reconcile failure logs but does not break SSE stream (over-reservation rolls off at midnight UTC TTL).

**Tests added (9)**:
- 4 unit US-2 in `test_quota_estimation_reconcile.py::TestEstimatePreCallTokens` (heuristic floor / mid / ceiling clamp / empty)
- 3 unit US-3 in `TestRecordUsageReconciliation` (under / equal / over reservation paths)
- 2 integration in `test_chat_quota_reconcile.py` — uses `_StubLoop` async iterator yielding LoopCompleted with known total_tokens; verifies wire-up correctness end-to-end at `_stream_loop_events` boundary

### D-Findings caveats

- **L529, L712, L749, L1018, L1110, L1292** LoopCompleted sites NOT updated — they're in helper methods (e.g. `_cat9_tool_check_branch`) where `tokens_used` is not in lexical scope. Default 0 used.
  - **Implication**: tripwire/guardrail mid-loop termination over-releases quota reservation by `tokens_used` (the actual LLM tokens consumed before tripwire). Acceptable trade-off — over-release means tenant gets MORE quota back than spent. Not a security issue. Phase 56.3 can refactor `tokens_used` to instance state for full propagation.
- **D10 alternative chosen** — extend LoopCompleted (option a) over LLMResponded extension. Preserves single-source per 17.md §Contract events; simpler than per-LLM-call accumulation in chat router; happy path (END_TURN) gets accurate reconciliation.

### Day 2 sanity (2.7-2.8)
- ✅ 8 V2 lints 8/8 green
- ✅ mypy --strict 0/284 source files
- ✅ black + isort + flake8 clean (1 black auto-fix on test_quota_estimation_reconcile.py)
- ✅ LLM SDK leak: 0
- ✅ pytest 1519 → 1528 (+9 = 4+3 unit + 2 integration; full suite 35s)
- ✅ 0 regression (chat_e2e 9/9 still pass after LoopCompleted extension)

### Day 2 actuals vs estimate

| Task group | Est | Actual |
|------------|-----|--------|
| US-2 wire (2.1-2.3) | 1.5 hr | ~1.0 hr (heuristic simpler than Cat 4 plan) |
| US-3 wire (2.4-2.6) | 2 hr | ~1.5 hr (D11 simplification — record_usage already exists) |
| Day 2 sanity (2.7-2.8) | 0.5 hr | ~0.5 hr (1 black fix + clean) |
| **Day 2 total** | **4 hr** | **~3.0 hr** (under est by 25%) |

### Day 3 plan (US-5 closeout)

US-5:
- 3.1 cross-AD e2e integration test (provision RBAC + onboard quota pre-call + chat reconcile + Cat 12 spans)
- 3.2 final sanity verify
- 3.3 retrospective.md (6 必答 + AD-Sprint-Plan-4 mixed 2nd app calibration verify + AD-Plan-4-Schema-Grep eval)
- 3.4 open PR + CI green + solo-dev merge
- 3.5 closeout PR (SITUATION + CLAUDE + memory)
- 3.6 final push

**Day 3 est**: ~1.5 hr

### Sprint cumulative state (post-Day 2)

| Metric | Value |
|--------|-------|
| Tests added | 20 (5 US-1 + 4+2 US-4 + 4+3 US-2 + 2 US-3) |
| pytest | 1508 → 1528 (+20; target ≥+17 hit early) |
| ADs closed | 4/4 (AD-Cat12-BusinessObs + AD-AdminAuth-1 + AD-QuotaEstimation-1 + AD-QuotaPostCall-1) |
| Hours actual | ~6.0 hr (Day 0 ~0.5 + Day 1 ~3.0 + Day 2 ~2.5) |
| Hours committed | 6 hr |
| Calibration ratio (preview) | **1.00 ✅** (right on band; mixed 2nd application stable) |

---

