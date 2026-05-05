# Sprint 55.5 — Plan

**Sprint**: 55.5
**Phase**: 55 (V2 Production / Audit Cycle)
**Type**: Audit Cycle Mini-Sprint #3 (Group D narrow — Cat 10 backend audit)
**Branch**: `feature/sprint-55-5-audit-cycle-mini-3-cat10-wire`
**Start Date**: 2026-05-05
**Target End Date**: 2026-05-09 (5 days, Day 0-4)
**Plan Format Template**: Sprint 55.4 (13 sections / Day 0-4)
**Status**: Day 0 — pending user approval before Day 1 code starts

> **Note**: Per **AD-Lint-2** (Sprint 55.3), per-day "Estimated X hours" headers dropped from checklist template. Sprint-aggregate estimate in §Workload only. Day-level actuals → progress.md.
>
> Per **AD-Plan-2** (Sprint 55.3), every plan §File Change List entry was Day-0 path-verified.
>
> Per **AD-Plan-3 first application** (Sprint 55.5 NEW from 55.4 retro), Day-0 探勘 ALSO greps plan-asserted code patterns within existing files (catches D5-class drifts where file exists but content differs from plan §Spec). 2 wrong-content drifts caught at Day 0 (D1+D2) — ROI validated.

---

## Sprint Goal

Wire `run_with_verification(loop, verifier=...)` into chat router (AD-Cat10-Wire-1) with 3-mode `CHAT_VERIFICATION_MODE` feature flag (disabled/shadow/enforce), and validate Cat 9 wrappers' D19 reuse-inner-tracer design (AD-Cat10-Obs-Cat9Wrappers) — closing 2 of 4 Cat 10 backend audit ADs in audit cycle Mini-Sprint #3 narrow scope (Option A approved by user 2026-05-05).

---

## Background

V2 22/22 (100%) closure achieved at Sprint 55.2 (2026-05-04). Phase 55+ enters audit cycle phase that systematically closes Audit Debts accumulated during V2 build phases (49-55):

- **53.2.5** = CI carryover bundle
- **53.7** = audit cleanup (9 ADs closed)
- **55.3** = Mini-Sprint #1 (Groups A + G — Cat 7 lint + Cat 12 helper + Hitl-7) — 6 ADs closed
- **55.4** = Mini-Sprint #2 (Groups B + C — Cat 8 + Cat 9 backend) — 4 ADs closed (AD-Cat8-2 deferred to 55.5 per D6)
- **55.5** (this sprint) = Mini-Sprint #3 narrow (Group D — Cat 10 backend audit, narrow scope)

**Group D originally listed 4 Cat 10 backend ADs**:
1. AD-Cat10-Wire-1 — chat router default-wire `run_with_verification`
2. AD-Cat10-VisualVerifier — Playwright screenshot verifier (FRONTEND green field, ~150+ LOC)
3. AD-Cat10-Frontend-Panel — verification_panel UI (FRONTEND green field, ~200+ LOC)
4. AD-Cat10-Obs-Cat9Wrappers — Cat 9 wrappers separate observability span (54.2 D19 deferred decision)

**Option A (this sprint, approved by user)**: ONLY Wire-1 + Obs-Cat9Wrappers (both backend, both surgical) + 2 process AD applications (AD-Plan-3 + AD-Sprint-Plan-5).

**Out-of-scope (deferred to future)**:
- AD-Cat10-VisualVerifier → Phase 56+ (frontend feature; needs Playwright infra; not audit cycle scope)
- AD-Cat10-Frontend-Panel → Phase 56+ (frontend feature; not audit cycle scope)
- AD-Cat8-2 (full retry-with-backoff) → 55.6+ dedicated medium-backend sprint (D6 from 55.4 confirmed dead state; needs full design)

This sprint also serves as:
- **First application of AD-Plan-3** (Day-0 content-keyword grep within asserted files) — 2 wrong-content drifts caught at Day 0 → ROI validated
- **First application of AD-Sprint-Plan-5** medium-backend multiplier refinement (0.65 → 0.75 + audit-cycle-overhead +0.05 = 0.80; Day 0 ~2 hr fixed offset excluded from bottom-up)

---

## Audit Debt Items

### AD-Cat10-Wire-1 — Chat Router Default-Wire `run_with_verification`

**Origin**: 54.1 retrospective Q5; carried through 54.2 / 55.1 / 55.2 / 55.3 / 55.4 retros
**Severity**: ⚠️ Medium — Cat 10 verification infra exists but main流量 chat router invokes `loop.run()` directly, bypassing verification entirely
**Day-0 探勘 finding (D1 — AD-Plan-3 first application)**:
- Plan assumed AD-Cat10-Wire-1 was "partially wired" (per 54.1 retro narrative)
- Actual Day-0 探勘: `run_with_verification` only used in 5 places — `correction_loop.py` (the wrapper itself) + `cat9_mutator.py` + `tools.py` (verify tool) + `__init__.py` (re-export) + `sse.py:245` (event handler comment) + `router.py:25/44` (docstring mention only)
- **Real chat invoke at `router.py:197` is `async for event in loop.run(...)` — completely unwired** (D3: `run_with_verification` is shipped 54.1 + verification module re-exports; just unwired at chat invocation point)
- Scope = pure plug-in at router.py:197 + `CHAT_VERIFICATION_MODE` feature flag (3-mode) + default verifier choice (RulesBasedVerifier with empty rules as no-op default; configurable)

**Acceptance**:
- `router.py` chat invoke wraps `loop.run()` via `run_with_verification(loop, ..., verifier=verifier)` when `CHAT_VERIFICATION_MODE != "disabled"`
- 3-mode feature flag: `disabled` (default; pass-through;no-op), `shadow` (run wrapper, log failure but do not block), `enforce` (run wrapper, raise on failure)
- Verifier injection via factory pattern (mirror 55.1 BusinessServiceFactory)
- Default verifier when wired: `RulesBasedVerifier(rules=[])` (no-op behavior) — caller can override
- 4-5 unit tests + 1 integration test (chat router smoke: disabled / shadow / enforce)
- Backwards-compatible: production default `disabled` → existing behavior preserved
- 17.md §2.1 ChatClient ABC + Cat 10 contracts unchanged (no new dataclass, no schema change)

### AD-Cat10-Obs-Cat9Wrappers — Validate D19 Reuse-Inner-Tracer Design

**Origin**: 54.2 retro D19 — Cat 9 fallback / mutator wrappers (`cat9_fallback.py` + `cat9_mutator.py`) intentionally reuse inner judge tracer instead of emitting independent `verification_span`. Deferred validation: confirm intentional + decide whether to keep reuse or add wrapper-level independent span.

**Severity**: 🟡 Low-Medium — observability completeness only; not blocking production
**Day-0 探勘 finding (D2 — AD-Plan-3 first application)**:
- Plan §Spec assumed wrappers might already have `verification_span` calls (from 54.2 D19 narrative ambiguity)
- Actual Day-0 探勘: `cat9_fallback.py` + `cat9_mutator.py` have **0 direct `verification_span` or `category_span` calls** — D19 design preserved (reuse-inner pattern)
- Scope = (a) verify D19 reuse-inner is intentional design + (b) decide policy: KEEP reuse-inner (1 span per verify) OR ADD independent wrapper span (2 spans per verify, double instrumentation) + (c) add docstring + sentinel test enforcing chosen policy

**Acceptance**:
- Decision: KEEP reuse-inner (no double instrumentation; aligned with Cat 12 helpers minimal-overhead philosophy)
- `cat9_fallback.py` + `cat9_mutator.py` get docstring section explaining D19 reuse-inner design + reference to 54.2 retro
- 1 sentinel unit test ensuring wrappers DON'T emit independent verification_span (verifies via tracer mock counts: 1 span from inner judge, not 2)
- Optionally: 1 integration test confirming production trace shows 1 verification_span per Cat 9 wrapper invocation (deferred to AD-Cat10-Obs-Cat9Wrappers-Integration if needed)

### Process ADs (apply during this sprint)

**AD-Plan-3 first application** (NEW from 55.4 retro):
- Day-0 探勘 grep extends from path-verify (AD-Plan-2) to also content-keyword grep within plan-asserted files
- This sprint Day 0: 4 grep + 2 Glob = 2 wrong-content drifts caught (D1 Wire-1 unwired + D2 Obs-Cat9Wrappers no spans)
- ROI: ~30 min Day 0 cost prevented ~2-3 hr mid-Day-1 re-work
- Document outcome in retro Q1 + Q3 for AD-Plan-3 ratification (promote from "candidate" to "validated rule")

**AD-Sprint-Plan-5 first refinement** (NEW from 55.4 retro):
- Apply medium-backend multiplier 0.65 → **0.75** lift (1st refinement)
- Apply audit-cycle-overhead surcharge **+0.05** (this sprint includes AD-Plan-3 + AD-Sprint-Plan-5 process applications) → **0.80**
- Apply Day 0 fixed offset (~2 hr) excluded from bottom-up est
- Document calibration in retro Q2 + Q6 for matrix iteration

---

## Technical Specifications

### AD-Cat10-Wire-1 Implementation

**File**: `backend/src/api/v1/chat/router.py`

```python
# Sprint 55.5 — wire run_with_verification (Cat 10 default-wire per AD-Cat10-Wire-1)
# Mode determined by CHAT_VERIFICATION_MODE env var:
#   - "disabled" (default): pass-through to loop.run() (existing behavior)
#   - "shadow":  wrap with run_with_verification; on verification failure,
#                log + emit VerificationFailed event but do NOT block correction
#   - "enforce": wrap with run_with_verification; on verification failure,
#                trigger correction loop (run_with_verification's existing behavior)

from agent_harness.verification import RulesBasedVerifier, run_with_verification
from core.config import settings

verification_mode = settings.CHAT_VERIFICATION_MODE  # "disabled" | "shadow" | "enforce"

if verification_mode == "disabled":
    event_iterator = loop.run(
        messages=...,
        tools=...,
        trace_context=...,
    )
else:
    verifier = _build_default_verifier()  # RulesBasedVerifier(rules=[]) by default
    event_iterator = run_with_verification(
        loop=loop,
        messages=...,
        tools=...,
        verifier=verifier,
        mode=verification_mode,  # "shadow" or "enforce"
        trace_context=...,
    )

async for event in event_iterator:
    yield event
```

**File**: `backend/src/core/config.py`

```python
# Sprint 55.5 — Cat 10 verification mode (AD-Cat10-Wire-1)
CHAT_VERIFICATION_MODE: Literal["disabled", "shadow", "enforce"] = Field(
    default="disabled",
    description=(
        "Cat 10 verification wiring at chat router. "
        "'disabled' = pass-through (default); 'shadow' = log failures, don't block; "
        "'enforce' = trigger correction loop on failure."
    ),
)
```

**File**: `backend/src/api/v1/chat/_verifier_factory.py` (NEW)

```python
"""
File: backend/src/api/v1/chat/_verifier_factory.py
Purpose: Build default Cat 10 verifier for chat router wiring per AD-Cat10-Wire-1.
Category: API / Cat 10 wiring (delegates to agent_harness.verification owner)
Created: 2026-05-05 (Sprint 55.5)
Last Modified: 2026-05-05

Modification History (newest-first):
    - 2026-05-05: Initial creation (Sprint 55.5) — Cat 10 chat router wiring per AD-Cat10-Wire-1
"""
from agent_harness.verification import RulesBasedVerifier, Verifier

def build_default_verifier() -> Verifier:
    """Default no-op verifier; production callers can override via injection."""
    return RulesBasedVerifier(rules=[])
```

### AD-Cat10-Obs-Cat9Wrappers Implementation

**File**: `backend/src/agent_harness/verification/cat9_fallback.py` (edit docstring)

Add module-level docstring section:

```python
"""
...existing docstring...

Observability Design (54.2 D19 + 55.5 AD-Cat10-Obs-Cat9Wrappers validation):
    This wrapper REUSES the inner judge's verification_span — it does NOT
    emit an independent wrapper-level span. Rationale:
    - Single span per verify invocation matches Cat 12 helper minimal-overhead philosophy
    - Wrapper logic (fallback decision) does not warrant separate span; inner
      judge's span attributes capture verifier identity + result
    - Avoids double-instrumentation noise in distributed traces

    Sentinel: tests/unit/agent_harness/verification/test_cat9_wrappers_obs.py
    enforces this invariant (asserts wrapper invocation produces exactly 1 span).
"""
```

**File**: `backend/tests/unit/agent_harness/verification/test_cat9_wrappers_obs.py` (NEW)

```python
"""
File: backend/tests/unit/agent_harness/verification/test_cat9_wrappers_obs.py
Purpose: Sentinel test enforcing 54.2 D19 reuse-inner-tracer design for Cat 9 wrappers.
Category: 範疇 10 (Verification Loops) / Tests
Created: 2026-05-05 (Sprint 55.5)
Last Modified: 2026-05-05

Modification History (newest-first):
    - 2026-05-05: Initial creation (Sprint 55.5) — close AD-Cat10-Obs-Cat9Wrappers per validated D19 design
"""
# Tests:
#   1. test_cat9_fallback_emits_single_span_via_inner_judge
#   2. test_cat9_mutator_emits_single_span_via_inner_judge
#   3. test_cat9_wrappers_do_not_call_verification_span_directly (AST/import check)
```

---

## Acceptance Criteria

- [ ] AD-Cat10-Wire-1: router.py:197 wraps loop.run via run_with_verification when mode != disabled
- [ ] AD-Cat10-Wire-1: 3-mode feature flag CHAT_VERIFICATION_MODE in core.config (default "disabled")
- [ ] AD-Cat10-Wire-1: 4-5 unit tests + 1 integration test (chat router smoke: disabled / shadow / enforce)
- [ ] AD-Cat10-Wire-1: Backwards-compatible — production default `disabled` preserves existing behavior
- [ ] AD-Cat10-Obs-Cat9Wrappers: Decision documented (KEEP reuse-inner; no double instrumentation)
- [ ] AD-Cat10-Obs-Cat9Wrappers: Docstring sections in cat9_fallback.py + cat9_mutator.py with D19 reference
- [ ] AD-Cat10-Obs-Cat9Wrappers: Sentinel test enforces wrapper produces 1 span per invocation
- [ ] Pytest delta ≥ +6 (1446 → ≥1452)
- [ ] 7 V2 lints 7/7 green
- [ ] mypy --strict 0 errors
- [ ] black + isort + flake8 clean
- [ ] LLM SDK leak 0
- [ ] AD-Plan-3 retrospective Q1 + Q3 (validate ROI for promotion)
- [ ] AD-Sprint-Plan-5 retrospective Q2 + Q6 (medium-backend mult 0.75 + 0.05 surcharge calibration)

---

## Day-by-Day Plan

### Day 0 — Setup + 探勘 + Plan/Checklist Drafting (~2 hr fixed offset)

- Working tree clean check on main `8acf301f`
- Feature branch creation
- Day-0 探勘: 4 grep + 2 Glob covering 5 candidate ADs (Option A scope-down to 2 backend ADs after探勘)
- AD-Plan-3 first application: content-keyword grep catches D1 (Wire-1 unwired) + D2 (Obs-Cat9Wrappers no spans)
- 3 drift findings catalogued (D1-D3)
- Plan + checklist drafting (mirror 55.4 13 sections / Day 0-4)
- Day 0 progress.md entry
- Commit Day 0 + push

### Day 1 — AD-Cat10-Wire-1 Implementation (~3 hr)

- Add `CHAT_VERIFICATION_MODE` to `core/config.py`
- Create `backend/src/api/v1/chat/_verifier_factory.py` with `build_default_verifier()`
- Edit `router.py:197` to dispatch on verification mode
- Add 4-5 unit tests in new `tests/unit/api/v1/chat/test_verification_wire.py`:
  - test_disabled_mode_passes_through
  - test_shadow_mode_wraps_loop
  - test_enforce_mode_wraps_loop
  - test_verifier_factory_default_no_op
  - test_invalid_mode_raises (config validation)
- Add 1 integration test in existing `tests/integration/api/test_chat_smoke.py` or NEW file:
  - test_chat_router_verification_smoke (3 modes via TestClient)
- Lint chain: black + isort + flake8 + mypy strict + 7 V2 lints
- Commit + push
- Day 1 progress.md entry

### Day 2 — AD-Cat10-Obs-Cat9Wrappers Validation (~1.5 hr)

- Edit `cat9_fallback.py` module docstring (add Observability Design section)
- Edit `cat9_mutator.py` module docstring (add Observability Design section)
- Create `tests/unit/agent_harness/verification/test_cat9_wrappers_obs.py` (3 sentinel tests)
- Lint chain
- Commit + push
- Day 2 progress.md entry

### Day 3 — Buffer / Doc Polish (~0.5-1 hr if Day 1+2 land cleanly)

- If Day 1+2 finished on time → use Day 3 for SITUATION-V2-SESSION-START.md §8 pre-update + memory file pre-draft
- If Day 1+2 overran → Day 3 absorbs overflow
- Lint chain re-run for safety
- Day 3 progress.md entry

### Day 4 — Retrospective + Closeout (~1.5 hr)

- Run full pytest baseline (target 1446 → ≥1452)
- Run full lint chain (black + isort + flake8 + mypy strict + 7 V2 lints)
- LLM SDK leak check
- Calibration ratio computation (AD-Sprint-Plan-5 1st application)
- Catalog final drift findings (D1-Dn)
- Write retrospective.md (6 必答 Q1-Q6) — Q6 specifically AD-Sprint-Plan-5 medium-backend 0.75 + 0.05 surcharge first validation
- Update SITUATION-V2-SESSION-START.md §8 + §9 + history row
- Update memory: `project_phase55_5_audit_cycle_3.md` + MEMORY.md +1 line
- Commit closeout
- Push branch + open PR
- Watch CI green (apply paths-filter workaround if needed per AD-CI-5)
- Merge PR (solo-dev policy)
- Closeout PR for SHA fill-in if needed
- Final verify on main (clean)

---

## File Change List (Day-0 Path-Verified per AD-Plan-2 + Content-Verified per AD-Plan-3)

### Backend (NEW files)

| Path | Verified | Purpose |
|------|----------|---------|
| `backend/src/api/v1/chat/_verifier_factory.py` | ✅ Glob: not-exists (will create) | Cat 10 verifier factory for chat router |
| `backend/tests/unit/api/v1/chat/test_verification_wire.py` | ✅ Glob: not-exists (will create) | Wire-1 unit tests (4-5) |
| `backend/tests/unit/agent_harness/verification/test_cat9_wrappers_obs.py` | ✅ Glob: not-exists (will create) | D19 reuse-inner sentinel (3 tests) |

### Backend (EDIT existing files)

| Path | Verified | Edit |
|------|----------|------|
| `backend/src/api/v1/chat/router.py` | ✅ Glob: exists; L197 confirmed `loop.run(` | Wrap with `run_with_verification` when mode != disabled |
| `backend/src/core/config.py` | ✅ Glob: exists | Add `CHAT_VERIFICATION_MODE` field |
| `backend/src/agent_harness/verification/cat9_fallback.py` | ✅ Glob: exists; content-grep confirmed 0 `verification_span` calls | Add Observability Design docstring section |
| `backend/src/agent_harness/verification/cat9_mutator.py` | ✅ Glob: exists; content-grep confirmed 0 `verification_span` calls | Add Observability Design docstring section |

### Backend (POSSIBLY EDIT — pending Day 1 read)

| Path | Note |
|------|------|
| `backend/tests/integration/api/test_chat_smoke.py` (or similar) | Smoke test add-on; path TBD by Day 1 read |

### Docs

| Path | Edit |
|------|------|
| `docs/03-implementation/agent-harness-planning/phase-55-production/sprint-55-5-plan.md` | NEW (this file) |
| `docs/03-implementation/agent-harness-planning/phase-55-production/sprint-55-5-checklist.md` | NEW |
| `docs/03-implementation/agent-harness-execution/phase-55/sprint-55-5/progress.md` | NEW (Day 0-4 entries) |
| `docs/03-implementation/agent-harness-execution/phase-55/sprint-55-5/retrospective.md` | NEW (Day 4) |
| `claudedocs/6-ai-assistant/prompts/SITUATION-V2-SESSION-START.md` | EDIT (§8 close 2 ADs + new ADs;§9 +Sprint 55.5 row;footer + history) |
| `.github/workflows/playwright-e2e.yml` | EDIT header (paths-filter workaround per AD-CI-5 if needed) |

**Total**: 3 NEW backend files + 4 EDIT backend files + 4 NEW/EDIT docs = ~11 files

---

## Dependencies & Risks

### Dependencies

- `agent_harness.verification.run_with_verification` shipped in Sprint 54.1 (D3 confirmed: already in `__init__.py` re-export + `correction_loop.py`) → no wrapper code needs writing
- `RulesBasedVerifier` shipped in Sprint 54.1 → factory default
- `pydantic-settings` (existing in `core/config.py`) → feature flag pattern
- 17.md §2.1 Verifier ABC + Cat 10 LoopEvents (VerificationPassed / Failed / Correction) → already shipped 54.1, used as-is

### Risks (per .claude/rules/sprint-workflow.md §Common Risk Classes)

| Class | Symptom | Workaround | Long-term |
|-------|---------|------------|-----------|
| **A: paths-filter** | Backend-only PR may not fire Frontend E2E required check | Touch `.github/workflows/playwright-e2e.yml` header (AD-CI-5 pattern; 53.7+ established) | AD-CI-5 (infra track) |
| **B: cross-platform mypy** | strict mode platform divergence | `# type: ignore[X, unused-ignore]` pattern | AD-Test-1 closed by 53.7 |
| **C: module-level singleton** | TestClient event-loop reset | `tests/integration/api/conftest.py` autouse fixture | DI-injected per-request refactor (deferred) |

### Sprint-specific risks

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| AD-Cat10-Wire-1 wraps router.py incorrectly (router.py is non-trivial; 200+ lines) | Medium | Day 1 morning: full read router.py before edit; mirror 55.1 BusinessServiceFactory pattern |
| run_with_verification signature changed since 54.1 | Low | Day 1 read `correction_loop.py:run_with_verification` to confirm signature first |
| CHAT_VERIFICATION_MODE config validation fails on existing deployments missing env var | Low | Default = "disabled" → existing prod deploys silently get pass-through behavior |
| Sentinel test for D19 design fails (wrappers DO emit independent span) | Low (探勘 already confirmed 0 calls) | If false alarm: switch to ADD independent span path + update plan |

---

## Workload (per AD-Sprint-Plan-5 medium-backend class refinement)

**Calibration formula** (AD-Sprint-Plan-5 1st refinement):

```
multiplier = 0.75 (medium-backend, lifted from 0.65 per Sprint 55.4 ratio 1.36 evidence)
            + 0.05 (audit-cycle-overhead surcharge: this sprint includes AD-Plan-3 + AD-Sprint-Plan-5 process applications)
            = 0.80

Day 0 ~2 hr fixed offset (excluded from bottom-up)
Day 4 retro + closeout ~1.5 hr (process overhead, included in committed)
```

### Bottom-up estimate (feature work only; Day 1-3)

| Item | Hours |
|------|-------|
| AD-Cat10-Wire-1 (router edit + feature flag + factory + 5 unit + 1 integration test) | 3 |
| AD-Cat10-Obs-Cat9Wrappers (validate D19 + 2 docstrings + 3 sentinel tests) | 1.5 |
| **Bottom-up total (feature)** | **4.5** |

### Calibrated commitment

```
Bottom-up est ~4.5 hr → calibrated commit ~4.5 × 0.80 = 3.6 hr (multiplier 0.80)
                     → + Day 0 fixed offset 2 hr
                     → + Day 4 retro + closeout 1.5 hr
                     → total committed ≈ 7 hr (rounded)
```

**Plan committed: ~7 hr total over 5 days (Day 0-4)**

---

## Out of Scope

| Item | Reason | Target |
|------|--------|--------|
| AD-Cat10-VisualVerifier | Frontend green field; needs Playwright screenshot infra; not audit cycle scope | Phase 56+ frontend Group F sprint |
| AD-Cat10-Frontend-Panel | Pure frontend feature; not audit cycle scope | Phase 56+ frontend Group F sprint |
| AD-Cat8-2 retry-with-backoff (full design) | D6 (55.4) confirmed 100% dead state; needs dedicated medium-backend production sprint | 55.6+ dedicated sprint |
| Cat 10 documentation site | Out of audit cycle scope | Phase 56+ docs sprint |
| Verifier integration with Anthropic LLMJudge | LLM Provider Neutrality preserved via existing 54.1 LLMJudgeVerifier; no new provider wiring | Existing 54.1 functionality sufficient |

---

## AD Carryover Sub-Scope

If 55.5 hits time-box pressure, **rolling carryover** priority (largest to smallest):

1. AD-Cat10-Obs-Cat9Wrappers Day 2 → 55.6 (low severity; documentation + sentinel only)
2. AD-Cat10-Wire-1 integration test Day 1 → 55.6 (unit tests stay in 55.5; integration only deferred)

> **Note**: Carryover should be exception, not rule. 55.5 calibration validation depends on closing all 2 ADs in current sprint.

---

## Definition of Done

- ☐ **2 ADs** closed per acceptance criteria (AD-Cat10-Wire-1 + AD-Cat10-Obs-Cat9Wrappers)
- ☐ Tests added ≥ +6 (cumulative 1446 → ≥1452)
- ☐ 7 V2 lints green
- ☐ pytest unit + integration green
- ☐ mypy --strict 0 errors
- ☐ LLM SDK leak 0 (CI enforced)
- ☐ black + isort + flake8 green
- ☐ Calibration ratio computed in retro Q2 (AD-Sprint-Plan-5 medium-backend 0.75 + 0.05 surcharge 1st application)
- ☐ Drift findings catalogued (D1-Dn)
- ☐ retrospective.md with 6 必答 Q1-Q6
- ☐ SITUATION-V2-SESSION-START.md §8 updated (close 2 AD; promote AD-Plan-3 to validated rule; mark AD-Sprint-Plan-5 calibration evidence)
- ☐ PR opened + CI green + merged to main
- ☐ Closeout PR for SHA fill-in if needed

---

## References

- **`SITUATION-V2-SESSION-START.md`** §8 Open Items (source of 2 ADs + 2 process AD applications)
- **Sprint 55.4 retrospective.md** — origin of AD-Sprint-Plan-5 + AD-Plan-3 + AD-Cat10-Wire-1 carryover
- **Sprint 54.1 retrospective.md** — origin of AD-Cat10-Wire-1 + AD-Cat10-VisualVerifier + AD-Cat10-Frontend-Panel
- **Sprint 54.2 retrospective.md** — origin of AD-Cat10-Obs-Cat9Wrappers (D19)
- **Sprint 55.4 plan + checklist** — format template (13 sections / Day 0-4)
- **`.claude/rules/sprint-workflow.md`** §Step 2.5 (Day-0 verify) + §Workload Calibration + §Common Risk Classes
- **`.claude/rules/file-header-convention.md`** §格式 (1-line MHist)
- **`.claude/rules/anti-patterns-checklist.md`** AP-9 verification + AP-2 no orphan wire
- **`backend/src/agent_harness/verification/correction_loop.py`** — `run_with_verification` shipped 54.1
- **`backend/src/agent_harness/verification/__init__.py`** — Cat 10 public API re-exports
- **17-cross-category-interfaces.md** §2.1 Verifier ABC + Cat 10 LoopEvents

---

**Status**: Day 0 — pending user approval before Day 1 code starts.
