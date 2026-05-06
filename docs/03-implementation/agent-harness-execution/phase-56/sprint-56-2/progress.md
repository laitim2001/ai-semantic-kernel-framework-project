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
