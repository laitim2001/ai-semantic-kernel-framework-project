# Sprint 55.2 — V2 22/22 Closure — Progress Log

**Plan**: [sprint-55-2-plan.md](../../../agent-harness-planning/phase-55-production/sprint-55-2-plan.md)
**Checklist**: [sprint-55-2-checklist.md](../../../agent-harness-planning/phase-55-production/sprint-55-2-checklist.md)
**Branch**: `feature/sprint-55-2-v2-closure`
**PR**: #85 (draft, opened Day 0)

---

## Day 0 — Setup + 探勘 + Pre-flight Verify (2026-05-04)

### 0.1 Branch + plan + checklist commit ✅

- ✅ Verified main HEAD `7ef94d30` (post 55.1 closeout PR #83)
- ✅ Pre-55.2 housekeeping: 55.1 checklist `[x]` bookkeeping commit `6b6d48c8` (PR #84) merged main
- ✅ Branch `feature/sprint-55-2-v2-closure` created from main
- ✅ Plan + checklist staged + committed `bba58d58` (764 insertions; 2 files)
- ✅ Pushed to origin; draft PR #85 opened

### 0.2 Day-0 探勘 — verify plan §Technical Spec assertions against actual repo state ✅

Per AD-Plan-1 (53.7) + feedback_day0_must_grep_plan_assumptions.md.

| # | Verify | Status |
|---|--------|--------|
| 1 | 4 deferred domain tools.py NO mode kwarg | ✅ confirmed: rootcause:121 / correlation:119 / patrol:158 — only `mock_url` kwarg present; no `mode:` |
| 2 | incident/tools.py reference pattern | ✅ confirmed: `_build_service_handlers` + `_serialize_incident` + `mode == 'service'` all present from 55.1 |
| 3 | BusinessServiceFactory + 5 service builders | ✅ confirmed: `_service_factory.py:73-87` `get_(incident|patrol|correlation|rootcause|audit)_service` |
| 4 | settings.business_domain_mode field | ✅ confirmed: `core/config/__init__.py:56` `business_domain_mode: Literal["mock", "service"] = "mock"` |
| 5 | chat handler current DI structure | ⚠️ **D3**: `router.py` has `Depends(get_current_tenant)` but `handler.py:91+154` calls `make_default_executor()` with NO mode/factory_provider args; will raise ValueError if BUSINESS_DOMAIN_MODE=service |
| 6 | get_tracer Depends factory exists | 🚨 **D2**: NOT FOUND — grep `def get_tracer\|tracer:.*Depends` returned 0 matches in backend/src |
| 7 | 4 deferred domain service classes ready | 🚨 **D1**: each service.py has only **1 method** (patrol.get_results / correlation.get_related / rootcause.diagnose / audit.query_logs) — NOT all mock_executor methods |
| 8 | _register_all.py current threading pattern | ⚠️ **D4**: `register_all_business_tools` ALREADY has `mode` + `factory_provider` kwargs (55.1) — only incident gets them threaded; 4 deferred domains' calls still use `mock_url` only |
| 9 | Catalogue D-findings | ✅ documented below |

### Drift Findings (D1-D5)

#### 🚨 D1 — 4 deferred service.py only 1 method each (scope clarification)

**Source**: 55.1 plan US-3 spec — only required 1 read-only method per domain (foundational).

| Domain | service.py methods | mock_executor methods | Sentinel handlers needed |
|--------|---------------------|----------------------|--------------------------|
| patrol | `get_results` | `check_servers / get_results / schedule / cancel` | 3 (check_servers/schedule/cancel) |
| correlation | `get_related` | `analyze / find_root_cause / get_related` | 2 (analyze/find_root_cause) |
| rootcause | `diagnose` | `diagnose / suggest_fix / apply_fix` | 2 (suggest_fix sentinel; apply_fix already pre-planned as `approval_pending`) |
| audit_domain | `query_logs` | `query_logs / generate_report / flag_anomaly` | 2 (generate_report/flag_anomaly) |
| **Total** | **4 real** | **13 mock** | **9 sentinel** |

**Mitigation**: Day 1+2 service-mode handlers will return `{"status": "service_path_pending", "method": "<name>"}` for the 9 unmapped methods + real factory_provider().get_*_service().method(...) calls for the 4 mapped methods. Plan §US-1 acceptance ("每 handler 用 factory_provider().get_*_service() per-call") still satisfied — handler calls factory; just doesn't always invoke a method.

**AD-BusinessDomainPartialSwap-1 closure logic** unchanged: uniform mode kwarg accepted across 5 domains; no crash on `mode='service'`. Real method implementation for the 9 deferred → Phase 56+.

#### 🚨 D2 — get_tracer Depends factory MISSING

**Mitigation Day 3 US-3**: Use **Option B** = pass `tracer=None` to BusinessServiceFactory (factory ABC already supports `tracer: Tracer | None = None`). Avoid scope creep adding new infrastructure factory in Sprint 55.2; defer Option A (new get_tracer Depends) to Phase 56+.

**Impact**: Cat 12 obs spans for business services will be **no-op in production main flow** until get_tracer factory added. business_service_span ctx mgr already handles `tracer is None` → yields without span (per 55.1 _obs.py).

#### ⚠️ D3 — handler.py builders need DI threading

**Source**: `handler.py:91 build_echo_demo_handler` + `handler.py:154 build_real_llm_handler` both call `make_default_executor()` no-args. These are called by router endpoints (router.py:87/202/226 already have `current_tenant` Depends).

**Mitigation Day 3 US-3**: Modify `build_echo_demo_handler` + `build_real_llm_handler` signatures to accept `tenant_id: UUID, db: AsyncSession, factory_provider: Callable | None = None`; thread to `make_default_executor`. Router endpoint adds `Depends(get_db)` if missing. Backwards-compat: `factory_provider=None` default keeps existing callers working in mode='mock'.

#### ⚠️ D4 — _register_all.py mode kwargs already threaded for incident only

**Source**: 55.1 D9 deferral. `register_all_business_tools` already accepts `mode + factory_provider` (good); but only incident's call uses them; patrol/correlation/rootcause/audit calls use `mock_url=mock_url` only.

**Mitigation**: Day 3 US-2 single edit — propagate kwargs to all 5 register_*_tools calls (after Day 1+2 add mode kwarg to those functions).

#### 🚨 D5 — V2 lints `run_all.py` requires project-root cwd

**Source**: 0.4 pre-flight initial run from `cd backend && python ../scripts/lint/run_all.py` returned 0/6 green (all FAIL); rerun from project root returned 6/6 green in 0.71s.

**Mitigation**: Always run V2 lints from project root. Catalogue as known footgun for future Day 0 探勘 docs.

### 0.3 Calibration multiplier pre-read ✅

- ✅ 55.1 retrospective Q2 confirmed: ratio **0.68** (actual ~7.5 hr / committed 11 hr)
- ✅ 4-sprint mean: 1.01 + 0.69 + 0.65 + 0.68 = 0.7575 → **0.76 BELOW [0.85, 1.20] band**
- ✅ Multiplier reduction: 0.50 → **0.40** (AD-Sprint-Plan-3 first application)
- ✅ Bottom-up est ~17 hr × 0.40 = **6.8 ≈ 7 hr** committed

**Banked from 53.7+54.1+54.2+55.1**: ~12-14 hr below committed across 4 sprints; sustained pattern justifies 0.40.

### 0.4 Pre-flight verify (main green baseline) ✅

| Check | Baseline | Notes |
|-------|----------|-------|
| pytest collect | **1399 collected** (= 1395 passed + 4 skipped) | matches 55.1 closeout state |
| 6 V2 lints | **6/6 green** in 0.71s | from project root cwd (D5) |
| mypy --strict | **0 errors / 266 files** | matches 55.1 |
| LLM SDK leak | **0** in agent_harness/ | grep `^(from\|import) (openai\|anthropic\|agent_framework)` |

### 0.5 Day 0 progress.md ✅ (this file)

---

### Day 0 totals

- Time: ~1 hr (探勘 + baseline + progress.md)
- Drift findings: 5 (D1-D5)
- AD pre-emptively logged: 0 (D-findings within sprint scope; mitigation already in plan/checklist)

---

## Day 1 — US-1 patrol + correlation tools.py mode swap (2026-05-04) ✅

### 1.1 patrol/tools.py mode swap ✅

- ✅ Added imports: `from collections.abc import Callable` + `from business_domain._service_factory import BusinessServiceFactory`
- ✅ Updated file header with Sprint 55.2 Day 1.1 section + Modification History entry
- ✅ Added `_build_service_handlers(factory_provider)` — 4 handlers:
  - `h_get` (mock_patrol_get_results) → real `factory_provider().get_patrol_service().get_results(patrol_id=...)`
  - `h_check`, `h_schedule`, `h_cancel` → sentinel `{"status": "service_path_pending", "method": "<name>"}`
- ✅ Modified `register_patrol_tools(... mode='mock'|'service', factory_provider=None)` — mock branch unchanged; service branch raises ValueError if no factory_provider; invalid mode → ValueError

### 1.2 correlation/tools.py mode swap ✅

- ✅ Same pattern as 1.1
- ✅ `_build_service_handlers` 3 handlers:
  - `h_get_related` (mock_correlation_get_related) → real `factory_provider().get_correlation_service().get_related(alert_id, depth)`
  - `h_analyze`, `h_find_rc` → sentinel
- ✅ `register_correlation_tools(... mode='mock'|'service', factory_provider=None)`

### 1.3 6 unit tests ✅

File: `backend/tests/unit/business_domain/test_partial_swap.py` (NEW; cross-domain consolidated per 55.1 `test_factory_and_mode.py` style)

⚠️ **D6 (test file location)**: checklist 1.1/1.2 verify cmd referenced `test_patrol_tools.py` + `test_correlation_tools.py` per-domain; consolidated to single cross-domain `test_partial_swap.py` for clarity (mirrors 55.1 test_factory_and_mode.py). Day 2 rootcause + audit_domain tests will extend same file.

- ✅ test_register_patrol_tools_mode_mock_uses_executor
- ✅ test_register_patrol_tools_mode_service_requires_factory_provider
- ✅ test_register_patrol_tools_mode_service_get_results_invokes_service (real e2e + sentinel verify)
- ✅ test_register_correlation_tools_mode_mock_uses_executor
- ✅ test_register_correlation_tools_mode_service_requires_factory_provider
- ✅ test_register_correlation_tools_mode_service_get_related_invokes_service (real e2e + sentinel verify)
- DoD: **6 passed in 0.35s** ✅

### 1.4 Day 1 sanity checks ✅

| Check | Result |
|-------|--------|
| black | ✅ 3 files unchanged |
| isort | ✅ clean |
| flake8 | ✅ clean |
| mypy --strict | ✅ 0 errors / 266 files |
| 6 V2 lints (project root cwd) | ✅ 6/6 green in 0.65s |
| Backend full pytest | ✅ **1401 passed / 4 skipped / 0 fail** in 29.87s (= 1395 + 6 — plan target hit exactly) |
| LLM SDK leak | ✅ 0 (Day 0 baseline still) |

### 1.5 Day 1 commit + push + progress.md ✅ (this entry)

### Day 1 totals

- Time: ~1.2 hr (calibrated estimate hit; bottom-up was ~3 hr)
- Drift findings: 1 (D6 — test file location consolidation)
- AD: AD-BusinessDomainPartialSwap-1 partial closure (2/4 domains done; rootcause + audit_domain Day 2)
- Files modified: 2 (patrol/tools.py +69 / correlation/tools.py +49)
- Files added: 1 (test_partial_swap.py 156 lines)

### Next: Day 2 — US-1 rootcause + audit_domain tools.py mode swap

Same pattern. Service classes for these domains:
- RootCauseService.diagnose (1 real) + suggest_fix / apply_fix (2 sentinel; apply_fix returns "approval_pending" sentinel for HITL ALWAYS_ASK alignment per plan)
- AuditService.query_logs (1 real) + generate_report / flag_anomaly (2 sentinel)

6 unit tests (3 rootcause + 3 audit_domain) extending test_partial_swap.py.

After Day 2, AD-BusinessDomainPartialSwap-1 fully closed (4/4 domains uniformly mode-aware).
