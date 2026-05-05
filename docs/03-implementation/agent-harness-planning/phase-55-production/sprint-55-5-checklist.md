# Sprint 55.5 — Checklist

[Plan](./sprint-55-5-plan.md)

> **Note**: Per **AD-Lint-2** (Sprint 55.3), per-day "Estimated X hours" headers dropped from this template. Sprint-aggregate estimate in plan §Workload only. Day-level actuals → progress.md.
>
> Per **AD-Plan-2** (Sprint 55.3), every plan §File Change List entry was Day-0 path-verified (Glob-checked exists for edits / not-exist for creates). 7 paths verified ✓ in plan.
>
> Per **AD-Plan-3 first application** (Sprint 55.5 NEW from 55.4 retro), Day-0 探勘 ALSO greps plan-asserted code patterns within existing files. 2 wrong-content drifts caught at Day 0 (D1+D2).

---

## Day 0 — Setup + Day-0 探勘 + Plan/Checklist Drafting

- [x] **Working tree clean verified on main `8acf301f`**
  - DoD: `git status --short` returns empty
- [x] **Feature branch created**
  - Branch: `feature/sprint-55-5-audit-cycle-mini-3-cat10-wire`
- [x] **Day-0 探勘 grep (AD-Plan-1 + AD-Plan-2 + AD-Plan-3 first application)**
  - 4 grep + 2 Glob covering 5 candidate ADs (Option A scope-down to 2 backend ADs)
  - **AD-Plan-3 content-keyword grep catches**:
    - **D1**: `run_with_verification` in 5 files (sse.py / tools.py / cat9_mutator.py / correction_loop.py / __init__.py) but NOT call site at chat router; `router.py:197` invokes `loop.run()` directly → AD-Cat10-Wire-1 = **completely unwired** (not partial as 54.1 retro narrative implied)
    - **D2**: `cat9_fallback.py` + `cat9_mutator.py` have **0 direct `verification_span` calls** (54.2 D19 reuse-inner design preserved); Obs-Cat9Wrappers scope = validate intentional + add docstring + sentinel test
  - **D3**: `run_with_verification` shipped 54.1 already in `correction_loop.py` + `__init__.py` re-export — no wrapper code needs writing; pure plug-in at chat router
- [x] **Read Sprint 55.4 plan template**
  - 13 sections / Day 0-4 confirmed
- [x] **Write `sprint-55-5-plan.md`**
  - 13 sections mirror 55.4
  - 2 ADs (Wire-1 + Obs-Cat9Wrappers) detailed
  - 2 process AD applications (AD-Plan-3 + AD-Sprint-Plan-5) explicit
- [x] **Write `sprint-55-5-checklist.md`** (this file)
- [ ] **Write Day 0 `progress.md` entry**
  - Path: `docs/03-implementation/agent-harness-execution/phase-55/sprint-55-5/progress.md`
- [ ] **Commit Day 0** (plan + checklist + progress)
  - Commit: `chore(docs, sprint-55-5): Day 0 plan + checklist + progress`
- [ ] **Push branch**

---

## Day 1 — AD-Cat10-Wire-1 (chat router default-wire `run_with_verification` — Option E 2-mode post-D4+D5)

### Day 1 Pre-code reading (~15 min)

- [x] **Read `backend/src/api/v1/chat/router.py`** full file (270 lines) — wrap target = `_stream_loop_events()` L197, NOT `chat()` endpoint;`loop.run(session_id=..., user_input=..., trace_context=...)` direct call
- [x] **Read `backend/src/agent_harness/verification/correction_loop.py`** — **D4 caught**:real signature uses `verifier_registry` (registry-based) + `agent_loop` param + NO `mode` param + `verifier_registry=None or empty` transparently delegates to `loop.run()` (54.1 backwards-compat)
- [x] **Read `backend/src/agent_harness/verification/__init__.py`** — Cat 10 public API re-exports include `run_with_verification` + `VerifierRegistry` + `RulesBasedVerifier` ✓
- [ ] **Read `backend/src/core/config.py`** existing settings pattern — choose pydantic Field pattern (mirror existing fields)

### AD-Cat10-Wire-1 — Implementation (Option E 2-mode + always-call-wrapper)

- [ ] **Add `chat_verification_mode` field to `core/config.py`**
  - **2-mode** `Literal["disabled", "enabled"]` (revised post-D4+D5)
  - Default: `"disabled"` (backwards-compatible via `verifier_registry=None`)
  - Description: cite AD-Cat10-Wire-1 + 2-mode semantics + always-call-wrapper rationale
  - Update file header MHist (per AD-Lint-3 1-line)
- [ ] **Create `backend/src/api/v1/chat/_verifier_factory.py`**
  - `build_default_verifier_registry() -> VerifierRegistry` returning `VerifierRegistry` with `RulesBasedVerifier(rules=[])` registered
  - File header per file-header-convention.md
- [ ] **Edit `backend/src/api/v1/chat/router.py` `_stream_loop_events()` L197**
  - Always-call-wrapper pattern:
    ```python
    verifier_registry = build_default_verifier_registry() if settings.chat_verification_mode == "enabled" else None
    async for event in run_with_verification(
        agent_loop=loop, session_id=session_id, user_input=user_input,
        trace_context=trace_context, verifier_registry=verifier_registry,
        max_correction_attempts=2,
    ):
    ```
  - Preserve existing serialize_loop_event + format_sse_message + LoopCompleted exit
  - Update file header MHist (per AD-Lint-3 1-line)

### AD-Cat10-Wire-1 — Tests

- [ ] **Create `backend/tests/unit/api/v1/chat/test_verification_wire.py`**
  - test_disabled_mode_injects_none_registry (default settings → `verifier_registry=None` passed to wrapper → wrapper delegates to loop.run)
  - test_enabled_mode_injects_populated_registry (settings override → `verifier_registry` populated with default RulesBasedVerifier)
  - test_verifier_factory_default_contains_rules_based_no_op (factory returns VerifierRegistry with 1 RulesBasedVerifier with empty rules)
  - test_invalid_mode_raises (pydantic Literal validation rejects unknown mode like "shadow")
  - DoD: 4/4 tests PASS
- [ ] **Add 1 integration test** — `backend/tests/integration/api/test_chat_verification_smoke.py` (NEW)
  - 2-mode TestClient SSE smoke (disabled / enabled);assert event stream identical when disabled (byte-for-byte equiv to direct loop.run()) + VerificationPassed event present when enabled
  - DoD: 1 test PASS

### Day 1 Wrap

- [ ] **Run pytest** — `python -m pytest backend/tests/unit/api/v1/chat/ backend/tests/integration/api/ -v`
  - DoD: 6 new tests PASS;regression 0
- [ ] **Lint chain**: black + isort + flake8 + mypy --strict + 7 V2 lints (`python scripts/lint/run_all.py`)
- [ ] **LLM SDK leak check**: `grep -r "from openai\|from anthropic\|import openai\|import anthropic" backend/src/api backend/src/agent_harness` → 0
- [ ] **Update Day 1 progress.md** entry — actual hours / drift findings if any / lint results
- [ ] **Commit Day 1**
  - Commit: `feat(api, sprint-55-5): close AD-Cat10-Wire-1 (chat router 3-mode CHAT_VERIFICATION_MODE wire)`
- [ ] **Push branch**

---

## Day 2 — AD-Cat10-Obs-Cat9Wrappers (validate D19 reuse-inner-tracer design)

### Day 2 Pre-code reading (~10 min)

- [ ] **Read `backend/src/agent_harness/verification/cat9_fallback.py`** — full file (~80-100 lines) understanding wrapper logic + delegation to inner judge
- [ ] **Read `backend/src/agent_harness/verification/cat9_mutator.py`** — full file
- [ ] **Read `backend/src/agent_harness/verification/_obs.py`** — verification_span helper signature
- [ ] **Read `backend/src/agent_harness/verification/llm_judge.py`** — confirm inner judge emits verification_span (the span we're "reusing")
- [ ] **Read 54.2 retro D19 specifically** — confirm intent statement ("wrappers reuse inner tracer; do not double-instrument")

### AD-Cat10-Obs-Cat9Wrappers — Validation Decision

- [ ] **Decision logged in progress.md**: KEEP reuse-inner (no double instrumentation) per 54.2 D19 intent + Cat 12 helpers minimal-overhead philosophy
- [ ] **No code change to wrapper logic** (only docstring + sentinel test)

### AD-Cat10-Obs-Cat9Wrappers — Documentation

- [ ] **Edit `cat9_fallback.py` module docstring**
  - Add "Observability Design (54.2 D19 + 55.5 AD-Cat10-Obs-Cat9Wrappers validation)" section
  - Cite single-span rationale + sentinel test path
  - Update file header MHist (per AD-Lint-3 1-line)
- [ ] **Edit `cat9_mutator.py` module docstring**
  - Same pattern as cat9_fallback
  - Update MHist

### AD-Cat10-Obs-Cat9Wrappers — Sentinel Tests

- [ ] **Create `backend/tests/unit/agent_harness/verification/test_cat9_wrappers_obs.py`**
  - test_cat9_fallback_emits_single_span_via_inner_judge (mock tracer; assert span count = 1 from inner)
  - test_cat9_mutator_emits_single_span_via_inner_judge (same pattern)
  - test_cat9_wrappers_do_not_call_verification_span_directly (AST or import scan: assert 0 direct verification_span imports/calls in wrappers)
  - DoD: 3/3 tests PASS

### Day 2 Wrap

- [ ] **Run pytest** — `python -m pytest backend/tests/unit/agent_harness/verification/ -v`
  - DoD: 3 new tests PASS;Cat 10 regression 0
- [ ] **Lint chain**: black + isort + flake8 + mypy --strict + 7 V2 lints
- [ ] **Update Day 2 progress.md** entry
- [ ] **Commit Day 2**
  - Commit: `test(verification, sprint-55-5): close AD-Cat10-Obs-Cat9Wrappers (D19 reuse-inner-tracer sentinel)`
- [ ] **Push branch**

---

## Day 3 — Buffer / SITUATION pre-update / Memory pre-draft

> **If Day 1+2 land cleanly**: Day 3 used for SITUATION + memory pre-draft (closeout work moved earlier)
> **If Day 1+2 overran**: Day 3 absorbs overflow + lint re-run

### Day 3 (clean path)

- [ ] **Pre-draft SITUATION-V2-SESSION-START.md §8 + §9 entry** (commit deferred to Day 4)
- [ ] **Pre-draft `memory/project_phase55_5_audit_cycle_3.md`** (commit deferred to Day 4)
- [ ] **Re-run full pytest** to confirm cumulative 1446 → ≥1452 (target +6;6 tests added: 5 Wire-1 unit + 1 Wire-1 integration + 3 Obs-Cat9Wrappers = 9 actually;target may exceed)
- [ ] **Re-run full lint chain** for safety
- [ ] **Update Day 3 progress.md** entry

### Day 3 (overflow path; if needed)

- [ ] **Absorb Day 1 overflow** (router.py edit complications / unexpected test failures)
- [ ] **Absorb Day 2 overflow** (sentinel test fixture complications)
- [ ] **Update Day 3 progress.md** entry with overflow rationale

---

## Day 4 — Retrospective + Closeout

- [ ] **Verify all 2 ADs closed** (acceptance criteria)
  - AD-Cat10-Wire-1: 3-mode CHAT_VERIFICATION_MODE + factory + 6 tests green
  - AD-Cat10-Obs-Cat9Wrappers: D19 validated + 2 docstrings + 3 sentinel tests green
- [ ] **Run full pytest baseline**
  - Target: 1446 → ≥1452 (+6 minimum;actual +9 expected: 5+1+3)
- [ ] **Run full lint chain**
  - black + isort + flake8 + mypy --strict + 7 V2 lints
- [ ] **LLM SDK leak check** — 0
- [ ] **Compute calibration ratio** (AD-Sprint-Plan-5 medium-backend 0.75 + 0.05 surcharge 1st application)
  - Sum actual hours Day 0-4
  - Ratio = actual / committed (committed = ~7 hr per plan §Workload)
  - Document in retro Q2 + Q6
- [ ] **Catalog final drift findings** (D1-Dn cumulative)
- [ ] **Write `retrospective.md`** (6 必答 Q1-Q6)
  - Q1 What went well
  - Q2 What didn't go well + ratio + scope-class verification
  - Q3 Generalizable lessons (especially AD-Plan-3 first-application ROI evidence)
  - Q4 Audit Debt deferred (carryover candidates for 55.6+)
  - Q5 Next steps (rolling planning — 55.6 candidate scope only;Group D remaining 2 ADs OR Group F frontend OR Group H CI/infra)
  - Q6 AD-Sprint-Plan-5 medium-backend 0.75 + 0.05 surcharge 1st application + AD-Plan-3 promotion-to-validated-rule recommendation
- [ ] **Update `claudedocs/6-ai-assistant/prompts/SITUATION-V2-SESSION-START.md`**
  - §8 close 2 ADs (AD-Cat10-Wire-1 + AD-Cat10-Obs-Cat9Wrappers)
  - §8 promote AD-Plan-3 from "candidate" to "validated" (or close it after first ROI evidence)
  - §8 mark AD-Sprint-Plan-5 calibration evidence row
  - Add new ADs (if any logged from this sprint)
  - §9 milestones row +Sprint 55.5 (V2 22/22 unchanged — audit cycle bundle)
  - Footer Last Updated + Update history +1 row
- [ ] **Update memory**
  - `memory/project_phase55_5_audit_cycle_3.md` — new
  - `memory/MEMORY.md` — index +1 line
- [ ] **Commit Day 4**
  - Commit: `docs(retro, sprint-55-5): retrospective + 2 AD closure summary + AD-Plan-3 ROI validation`
- [ ] **Push branch**
- [ ] **Open PR**
  - Title: `Sprint 55.5: Audit Cycle Mini-Sprint #3 — close AD-Cat10-Wire-1 + AD-Cat10-Obs-Cat9Wrappers (Group D narrow)`
- [ ] **Watch CI green** — apply paths-filter workaround for Frontend E2E if needed (per AD-CI-5)
- [ ] **Merge PR** — solo-dev policy, review_count=0
- [ ] **Closeout PR for SHA fill-in** if needed (SITUATION §9 + memory file SHA)
- [ ] **Final verify on main** — clean

---

## Tracker

| AD | Status | Tests Added | Commit |
|----|--------|-------------|--------|
| AD-Cat10-Wire-1 | ⏳ Day 1 pending (Option E 2-mode post-D4+D5) | 0 → target 4 unit + 1 integration | — |
| AD-Cat10-Obs-Cat9Wrappers | ⏳ Day 2 pending | 0 → target 3 sentinel | — |
| AD-Plan-3 (process; first application) | ✅ Day 0 ROI validated (D1+D2 caught) + Day 1 morning extension (D4+D5 caught wrong-API drift) | — (process AD) | Day 0 + Day 1 commits |
| AD-Sprint-Plan-5 (process; first refinement) | ⏳ Day 4 calibration | — (process AD) | Day 4 retro |
| **Total** | **0/2 backend closed** | **+8 expected (4+1+3)** | — |

---

**Status**: Day 0 — Plan + Checklist drafted (this commit pending). Pending user approval before Day 1 code starts.
