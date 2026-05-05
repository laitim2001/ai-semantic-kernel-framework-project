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
- [x] **Read `backend/src/core/config/__init__.py`** existing settings pattern (D6 drift: path is package not single file) — `business_domain_mode: Literal["mock", "service"] = "mock"` pattern confirmed as mirror

### AD-Cat10-Wire-1 — Implementation (Option E 2-mode + always-call-wrapper)

- [x] **Add `chat_verification_mode` field to `core/config/__init__.py`** ✅
  - **2-mode** `Literal["disabled", "enabled"]` (revised post-D4+D5)
  - Default: `"disabled"` (backwards-compatible via `verifier_registry=None`)
  - Description: cite AD-Cat10-Wire-1 + 2-mode semantics + always-call-wrapper rationale
  - File header MHist updated per AD-Lint-3 1-line
- [x] **Create `backend/src/api/v1/chat/_verifier_factory.py`** ✅ (54 LOC)
  - `build_default_verifier_registry() -> VerifierRegistry` returning registry with `RulesBasedVerifier(rules=[])` registered
  - `select_verifier_registry(mode: VerificationMode) -> VerifierRegistry | None` mode-dispatch helper
  - File header per file-header-convention.md (MHist 1-line)
- [x] **Edit `backend/src/api/v1/chat/router.py` `_stream_loop_events()` L197** ✅
  - Always-call-wrapper pattern via `run_with_verification(agent_loop=loop, verifier_registry=select_verifier_registry(...), max_correction_attempts=2)`
  - Settings cached lookup inside `_stream_loop_events()` for per-request mode resolution
  - File header MHist compressed to 5 1-line entries (E501 compliant)

### AD-Cat10-Wire-1 — Tests

- [x] **Create `backend/tests/unit/api/v1/chat/test_verification_wire.py`** ✅ (4/4 PASS in 0.99s)
  - test_factory_default_contains_rules_based_no_op (factory returns VerifierRegistry with 1 RulesBasedVerifier with empty rules)
  - test_disabled_mode_injects_none_registry (mode "disabled" → returns None)
  - test_enabled_mode_injects_populated_registry (mode "enabled" → returns populated registry)
  - test_invalid_mode_raises (pydantic Literal rejects "shadow" 3-mode legacy)
  - DoD: 4/4 PASS ✅
- [x] **Add 1 integration test** — `backend/tests/integration/api/test_chat_verification_smoke.py` (NEW) ✅ (1/1 PASS in 0.48s)
  - test_chat_router_verification_smoke_2_modes (disabled preserves echo stream + no verification events;enabled adds verification_passed event from no-op RulesBasedVerifier)
  - DoD: 1 PASS ✅

### Day 1 Wrap

- [x] **Run pytest** — 4 unit (test_verification_wire) + 1 integration (test_chat_verification_smoke) + chat regression (71/71) + full pytest **1451 passed / 4 skipped** (+5 from 1446 baseline) ✅
- [x] **Lint chain**: black ✅ + isort ✅ + flake8 ✅ (7 E501 caught initially → all fixed via AD-Lint-3 compression) + mypy --strict ✅ (0 errors) + 7 V2 lints ✅ (0.82s)
- [x] **LLM SDK leak check**: ✅ 0 (`check_llm_sdk_leak` in V2 lints suite)
- [x] **Update Day 1 progress.md** entry — actual ~2 hr / D6 drift / lint results / test counts
- [ ] **Commit Day 1**
  - Commit: `feat(api, sprint-55-5): close AD-Cat10-Wire-1 (chat router 2-mode CHAT_VERIFICATION_MODE wire; Option E post-D4+D5)`
- [ ] **Push branch**

---

## Day 2 — AD-Cat10-Obs-Cat9Wrappers (validate D19 reuse-inner-tracer design)

### Day 2 Pre-code reading (~10 min) — AD-Plan-3 third application

- [x] **Read `cat9_fallback.py`** (137 lines) — wrapper IS-A Guardrail; **0 verification_span imports/calls** ✓
- [x] **Read `cat9_mutator.py`** (125 lines) — same pattern; **0 verification_span imports/calls** ✓
- [x] **Read `verification/_obs.py`** (49 lines) — `verification_span` async ctx mgr delegating to `category_span` (55.3 AD-Cat12-Helpers-1); D7 drift caught: docstring lists 4 callers but cat9 wrappers are indirect (not direct) per 54.2 D19
- [x] **Read existing verification_span callers** — direct = rules_based + llm_judge; indirect = cat9_fallback / cat9_mutator (via inner judge dependency)

### AD-Cat10-Obs-Cat9Wrappers — Validation Decision

- [x] **Decision logged in progress.md**: KEEP reuse-inner (no double instrumentation) per 54.2 D19 intent + Cat 12 helpers minimal-overhead philosophy
- [x] **No code change to wrapper logic** (documentation + sentinel only)

### AD-Cat10-Obs-Cat9Wrappers — Documentation

- [x] **Edit `cat9_fallback.py` module docstring** ✅
  - Added "Observability Design (54.2 D19 + 55.5 AD-Cat10-Obs-Cat9Wrappers validation)" section
  - Cited single-span rationale + sentinel test path
  - File header MHist 1-line entry (compressed to 92 chars per AD-Lint-3 D9)
- [x] **Edit `cat9_mutator.py` module docstring** ✅
  - Same pattern as cat9_fallback + cross-reference
  - MHist 1-line entry (compressed)
- [x] **Edit `_obs.py` module docstring (D7 fix)** ✅
  - Clarify direct callers (rules_based + llm_judge) vs indirect users (cat9 wrappers via inner judge dependency)
  - MHist 1-line entry

### AD-Cat10-Obs-Cat9Wrappers — Sentinel Tests

- [x] **Create `backend/tests/unit/agent_harness/verification/test_cat9_wrappers_obs.py`** ✅ (3/3 PASS in 0.26s)
  - **D8 drift caught**: first-pass naive string-search false-positive on docstring text → rewrote to AST walk (only Import / ImportFrom / Call nodes counted)
  - test_cat9_fallback_does_not_import_verification_span (AST walk → 0 findings)
  - test_cat9_mutator_does_not_import_verification_span (AST walk → 0 findings)
  - test_cat9_wrappers_docstrings_document_reuse_inner_design (assert "Observability Design" + "D19" + "AD-Cat10-Obs-Cat9Wrappers" in both wrapper docstrings)
  - DoD: 3/3 PASS ✅

### Day 2 Wrap

- [x] **Run pytest** — verification + chat regression 114 PASS in 1.92s; full pytest **1454 passed / 4 skipped** in 31.28s (+3 Day 2; cumulative +8 from 1446) ✅
- [x] **Lint chain**: black ✅ (1 reformatted) + isort ✅ + flake8 ✅ (2 E501 → AD-Lint-3 compressed) + mypy --strict ✅ (0) + 7 V2 lints ✅ (7/7 in 0.77s) + LLM SDK leak ✅ (0)
- [x] **Update Day 2 progress.md** entry — actual ~1.5 hr (ratio 1.0 in band) / D7+D8+D9 drifts
- [ ] **Commit Day 2**
  - Commit: `test(verification, sprint-55-5): close AD-Cat10-Obs-Cat9Wrappers (D19 reuse-inner-tracer sentinel)`
- [ ] **Push branch**

---

## Day 3 — Buffer / SITUATION pre-update / Memory pre-draft

> **If Day 1+2 land cleanly**: Day 3 used for SITUATION + memory pre-draft (closeout work moved earlier)
> **If Day 1+2 overran**: Day 3 absorbs overflow + lint re-run

### Day 3 (clean path) — 2026-05-05 ✅

- [x] **Decision: clean path** (both ADs closed Day 1+2 on schedule;no overflow)
- [x] **SITUATION + memory pre-draft DEFERRED to Day 4 closeout commit** (cleaner single commit than split pre-draft)
- [x] **Re-run full pytest** → 1454 passed / 4 skipped in 30.98s (cumulative +8 from 1446;target +6 hit 33% over)
- [x] **Re-run full lint chain** → 7 V2 lints 7/7 green (0.83s) + flake8 src/ OK
- [x] **Update Day 3 progress.md** entry — decision rationale + safety results
- [ ] **Commit Day 3** (progress.md only)
  - Commit: `chore(docs, sprint-55-5): Day 3 buffer — safety re-validation`
- [ ] **Push branch**

### Day 3 (overflow path; not needed)

- N/A — Day 1+2 closed on schedule

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
| AD-Cat10-Wire-1 | ✅ closed Day 1 (Option E 2-mode post-D4+D5) | 4 unit + 1 integration = 5 | `60e65a6a` |
| AD-Cat10-Obs-Cat9Wrappers | ✅ closed Day 2 (KEEP reuse-inner per 54.2 D19) | 3 sentinel via AST walk | Day 2 commit pending |
| AD-Plan-3 (process; first application) | ✅ Day 0/1/2 ROI validated (D1+D2+D4+D5+D7 caught — 5 wrong-content drifts AD-Plan-2 alone misses) | — (process AD) | embedded in Day 0/1/2 commits |
| AD-Sprint-Plan-5 (process; first refinement) | ⏳ Day 4 calibration | — (process AD) | Day 4 retro |
| **Total** | **2/2 backend closed** | **+8 actual (5+3 = target hit exactly)** | — |

---

**Status**: Day 0 — Plan + Checklist drafted (this commit pending). Pending user approval before Day 1 code starts.
