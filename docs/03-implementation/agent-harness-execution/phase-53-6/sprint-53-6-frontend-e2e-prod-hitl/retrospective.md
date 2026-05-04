# Sprint 53.6 — Retrospective

**Plan**: [`../../../agent-harness-planning/phase-53-6-frontend-e2e-prod-hitl/sprint-53-6-plan.md`](../../../agent-harness-planning/phase-53-6-frontend-e2e-prod-hitl/sprint-53-6-plan.md)
**Checklist**: [`../../../agent-harness-planning/phase-53-6-frontend-e2e-prod-hitl/sprint-53-6-checklist.md`](../../../agent-harness-planning/phase-53-6-frontend-e2e-prod-hitl/sprint-53-6-checklist.md)
**Branch**: `feature/sprint-53-6-frontend-e2e-prod-hitl`
**Day count**: 4 days actual (Day 0-4 planned)
**Closing date**: 2026-05-04

---

## Q1 — Sprint Goal achieved?

**YES** ✅. All 5 USs delivered with verifiable evidence:

- **US-1 Playwright bootstrap + CI**: `@playwright/test ^1.59.1` installed; chromium 147 + headless shell downloaded; `playwright.config.ts` written; smoke spec passes locally + on CI; `.github/workflows/playwright-e2e.yml` triggers on PR + main; first run green in 59s, subsequent runs ~50s with browser cache.
- **US-2 Governance reviewer e2e**: `tests/e2e/governance/approvals.spec.ts` — 5 cases passing (main flow / reject / escalate / decide error 404 / empty list).
- **US-3 ChatV2 ApprovalCard e2e**: `tests/e2e/chat/approval-card.spec.ts` — 4 cases passing (approve / reject / risk badge CRITICAL color / server-driven approval_received).
- **US-4 Production HITL wiring**: `backend/src/api/v1/chat/handler.py` `build_handler` accepts `service_factory` arg; chat router injects via `Depends(get_service_factory)`. `_hitl_enabled()` env toggle (default ON; `HITL_ENABLED=false` opts out). Verified by `test_chat_hitl_production_wiring.py` 13 cases (5 wiring + 8 toggle parsing).
- **US-5 ServiceFactory consolidation**: `service_factory.py` provides `get_hitl_manager()` / `get_risk_policy()` / `build_audit_query()`. Migrated chat / governance / audit routers. Grep evidence: 0 inline `DefaultHITLManager(` / `AuditQuery(` / `DefaultRiskPolicy(` constructions in `backend/src/api/`.
- **D2 SSE GuardrailTriggered fix** (UNPLANNED Day 0 探勘 finding): `sse.py` isinstance branch + 3 tests + frontend defensive types — prevents production crash when US-4 wiring fires Cat 9 events through chat endpoint.

**Main flow evidence**:
- `grep -rn "DefaultHITLManager(\|AuditQuery(\|DefaultRiskPolicy(" backend/src/api/` → **0 results** in production code (factory replaced all inline construction)
- `grep -rn "from openai\|from anthropic" backend/src/api/ backend/src/platform_layer/ backend/src/agent_harness/` → only false-positive docstring matches in claude_counter.py (no SDK leak)
- `pytest --tb=line -q` → **1085 passed / 4 skipped / 0 fail** (+26 from main 1059 baseline = exactly 13 service_factory unit + 13 production wiring tests)
- Playwright e2e: **11 passed in 5.4s** (2 smoke + 5 governance + 4 chat)

---

## Q2 — Estimated vs actual hours

| US / Task | Estimated | Actual | Delta |
|-----------|-----------|--------|-------|
| Day 0 探勘 | 2-3 hr | ~1.5 hr | -1 hr |
| Day 1 D2 fix | (unplanned) | ~0.75 hr | +0.75 hr |
| Day 1 US-1 Playwright bootstrap | 4-5 hr | ~2.25 hr | -2 hr |
| Day 2 US-2 governance e2e | 4-5 hr | ~1.5 hr | -3 hr |
| Day 3 US-3 chat ApprovalCard e2e | 4-5 hr | ~1.5 hr | -3 hr |
| Day 4 US-4 + US-5 + retro + PR | 5-7 hr | ~3 hr | -3 hr |
| **TOTAL** | **18-25 hr** | **~10.5 hr** | **~50% under** |

Same ~50% over-estimate pattern as Sprint 53.4 + 53.5. Under-estimate consistent: ~7-14 hr banked across 3 sprints. **Calibration follow-up**: starting Sprint 53.7+, default new sprint estimates to 50-60% of bottom-up sum.

---

## Q3 — What went well (≥ 3 items)

1. **D11 design decision (page.route() network mocking) saved ~10 hr**. Original plan called for backend boot + DB seed + JWT issuance per spec; switched to Playwright network-layer mocking on Day 2. Pattern proved general — extended to SSE streaming on Day 3 with same `page.route()` mechanism. Cumulative speedup: governance + chat e2e ran in ~3 hr instead of estimated 8-10 hr.

2. **Day 0 探勘 caught 2 critical pre-existing bugs**:
   - **D1**: `api/dependencies.py` does not exist (planned location for DI was wrong); rerouted to `platform_layer/identity/auth.py` which is the actual single-source DI dep file.
   - **D2 (CRITICAL)**: `GuardrailTriggered` yielded 7× in `loop.py` but missing from sse.py serializer — pre-existing bug since 53.3 that escaped 53.4 + 53.5 because chat router never wired guardrails. Would have caused production crash on first US-4 deployment when any Cat 9 detection fired. Fixed Day 1 before Playwright specs touched chat endpoint.

3. **Existing 24 governance + audit endpoint tests still passed after factory migration** with only 1 small change (added `conftest.py` with `reset_service_factory()` autouse fixture). Singleton-across-event-loops issue caught early; conftest scoped narrowly to `tests/integration/api/` to avoid cross-cutting impact.

4. **Bonus**: 11 e2e specs total exceeded plan minimum of 7 (smoke 2 + governance 5 + chat 4 vs plan 2 + 4 + 3). Added "decide error 404", "empty list", and "server-driven approval_received" cases for free with mocking infrastructure.

---

## Q4 — What can improve (≥ 3 items + follow-up actions)

1. **Estimate calibration drift continues** — third consecutive sprint with ~50% over-estimate. Action: starting Sprint 53.7, multiply bottom-up totals by 0.5-0.6 (or use `min(plan_estimate, plan_estimate * 0.6)` as committed total). Add explicit "Calibration adjustment" line to plan §Workload section.

2. **V2 lint scripts have inconsistent CLI ergonomics** (D10 carryover from Day 1) — `check_ap1_pipeline_disguise.py` + `check_promptbuilder_usage.py` need explicit `--root backend/src/agent_harness` while the other 4 auto-discover. Pre-push hook could miss these if developers don't know to pass the arg. **Action (AD-Lint-1)**: write a single `scripts/lint/run_all.py` wrapper that invokes all 6 with correct args; document in `.claude/rules/sprint-workflow.md` Pre-Push section.

3. **TestClient-based integration tests cache singletons across event loops** (Day 4 finding) — required `reset_service_factory()` fixture in `conftest.py`. Pattern will repeat for any future module-level service singleton (RiskPolicy DB cache, MetricsRegistry, etc.). **Action (AD-Test-1)**: factor a shared `tests/integration/conftest.py` (one level up) with autouse fixtures resetting all known module-level caches; document the pattern in `.claude/rules/testing.md`.

4. **Backend CI didn't trigger on Day 2 + Day 3 frontend-only commits** (paths filter excludes backend/**) — initially looked like CI broke. Documented in commits but worth a one-liner in PR description so reviewer doesn't worry. **Action**: include "CI matrix expected per commit type" table in PR description template (extends AD-CI-4).

---

## Q5 — V2 9-discipline self-check

| # | Discipline | Status | Notes |
|---|-----------|--------|-------|
| 1 | Server-Side First | ✅ | All state lives backend; e2e specs are network-layer thin clients |
| 2 | LLM Provider Neutrality | ✅ | grep openai/anthropic in api/+platform_layer/+agent_harness/ → 0 (only docstring false-positives in claude_counter.py) |
| 3 | CC Reference 不照搬 | ✅ | Anthropic CC has no enterprise governance e2e or factory pattern; Playwright + ServiceFactory designed from scratch for V2 |
| 4 | 17.md Single-source | ✅ | ServiceFactory consolidates construction sites without duplicating ABCs (HITLManager / AuditQuery / RiskPolicy unchanged); chatStore approvals slice + SSE serializer remain single-source |
| 5 | 11+1 範疇歸屬 | ✅ | service_factory.py = `platform_layer/governance/`; chat handler/router = `api/v1/chat`; frontend e2e = `tests/e2e/`; SSE serializer additions = `api/v1/chat` (range 12 cross-cutting) |
| 6 | 04 anti-patterns | ✅ | AP-3: factory eliminates cross-directory scattered constructors (governance/router + audit + chat all converge); AP-4: e2e specs prove components aren't Potemkin; AP-9: build_handler verifies wiring contract |
| 7 | Sprint workflow | ✅ | plan → checklist → code → progress → retrospective (this file); Day 0/1/2/3/4 progress entries each daily |
| 8 | File header convention | ✅ | All 5 new files (service_factory.py + 2 specs + fixtures + 2 tests + conftest + workflow + config + retro) have headers per convention |
| 9 | Multi-tenant rule | ✅ | Factory stays tenant-agnostic; per-tenant routing happens inside services (notifier override map / RiskPolicy.evaluate(tenant_id)); existing 24 governance+audit tests cover cross-tenant isolation |

---

## Q6 — Audit Debt logged

### Closed by Sprint 53.6

- ✅ **AD-Front-1** Playwright bootstrap + e2e specs — `playwright.config.ts` + smoke + governance + chat specs + CI workflow all delivered
- ✅ **AD-Front-2** Production HITL wiring at chat router — `build_handler` injects `hitl_manager` from ServiceFactory; verified by 5 wiring tests + grep evidence
- ✅ **AD-Hitl-4-followup** ServiceFactory consolidation — single construction site for HITL/Audit/Risk; 0 inline ctors in api/

### New Audit Debt (logged for follow-up sprints)

| ID | Description | Target |
|----|-------------|--------|
| **AD-Lint-1** | V2 lint scripts inconsistent CLI args (`--root` only some); single `scripts/lint/run_all.py` wrapper + pre-push doc update | 53.7 / audit cycle |
| **AD-Test-1** | Module-level singletons in tests need shared autouse reset fixture; document pattern in `.claude/rules/testing.md` | 53.7 / audit cycle |
| **AD-Sprint-Plan-1** | Estimate calibration: 3 consecutive ~50% over-estimate sprints; introduce calibration multiplier in plan template | Next sprint plan template update |

### Items still pending from earlier sprints (carryover unchanged)

- 🚧 AD-Hitl-7 / AD-Hitl-8 / AD-Cat9-1/2/3/5/6/7/8/9 / AD-Cat8-2 / AD-CI-4/5/6 — see Sprint 53.5 retrospective Q6 for full list

---

## Sprint Closeout Checklist (verbatim from plan)

- [x] All 5 USs delivered with 主流量 verification
- [ ] PR open + 5 active CI checks → green (Day 4.8)
- [ ] Normal merge to main (solo-dev policy: review_count=0; no temp-relax needed) (Day 4.8)
- [x] retrospective.md filled (this file)
- [ ] Memory update (project_phase53_6_frontend_e2e_prod_hitl.md + index) (Day 4.9)
- [ ] Branch deleted (local + remote) (Day 4.9)
- [ ] V2 progress: **18/22 (82%)** (Day 4.9 memory update)
- [ ] Cat 9 production-deployable end-to-end
- [ ] AD-Front-1 closed (verified above)
- [ ] AD-Front-2 closed (verified above)
- [ ] AD-Hitl-4-followup closed (verified above)
- [ ] Branch protection required_checks updated to include Frontend E2E (admin op post-merge — Day 4.9)
