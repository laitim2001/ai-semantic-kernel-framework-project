---
title: 42-verification-key-condition design note
purpose: Spike-extract design note from Sprint 57.138; documents the measured generic-vs-key-condition judge A/B + the per-task-condition template mechanism
category: V2 extension docs (post-22-sprint era)
created: 2026-06-24 (Sprint 57.138 Day 4 closeout)
sprint_source: 57.138
verified_ratio: ≥ 95% (per 8-Point Quality Gate)
status: Active
---

# 42 — Verification Key-Condition Judge Design Note (Sprint 57.138 extract)

## 8-Point Quality Gate (self-check)

- [x] **1. Section headers map to spike user stories** (§2.1 US-1 / §2.2 US-2 / §2.3 US-3 / §2.4 US-4)
- [x] **2. Every technical claim has file:line** (key_condition.txt · llm_judge.py:123-187 · templates/__init__.py:47/64 · handler.py:660/663 · script + fixture + test paths)
- [x] **3. Decision rationale includes a comparison matrix** (§1 the generic-vs-key_condition A/B + the threshold decision)
- [x] **4. Reproducible verification command** (§2.x per invariant + §3 A/B rerun command)
- [x] **5. Test fixture reference** (`key_condition_cases.yaml` + the real-Azure cost note)
- [x] **6. Open-invariant boundary explicit** (§4 — what this spike did NOT verify)
- [x] **7. Rollback / fallback path** (§5 — default-template stays output_quality + delete the template; zero code revert)
- [x] **8. 17.md single-source cross-ref** (§3 — NO new cross-category contract; template-only, justified N/A)

---

## 0. Spike Summary

- **Sprint scope**: US-1 key_condition template · US-2 selectable via the existing lever · US-3 real-Azure A/B measurement · US-4 mandatory chat-v2 drive-through · US-5 closeout. Closes `AD-Verification-KeyCondition-PerTask` (research #8).
- **Verified period**: 2026-06-24 (Day 0–3).
- **Calibration**: bottom-up ~11 hr → class-calibrated commit ~6.6 hr (`verification-keycondition-spike` 0.60, 1st data point, agent_factor 1.0 parent-direct). Day-4 retro Q2 ratio.
- **Verification**: pytest +11 (2 template tests + 9 harness tests) → 2797 passed + 5 skip; mypy 0/374; v2 lints 10/10; 1 real-Azure A/B (11 cases × 2 templates); drive-through PASS (both arms).
- **Headline**: the per-task key_condition judge catches instruction-following violations the generic judge misses (**100% vs 83%** on the instruction_violation class, **+16.67pp**) BUT over-flags acceptable answers (**20% FP**) and costs ~1.8× the tokens → overall accuracy is a **tie** → it does NOT clear the recommendation thresholds (gain ≥ 30% AND fp ≤ 20%). `output_quality` stays default; `key_condition` ships as a selectable opt-in. #8 = directionally real, low-priority refinement (matches the reconciliation assessment).

## 1. Decision Matrix — generic `output_quality` vs `key_condition` (the spike's core evidence)

Real Azure (cheap-tier judge, temp 0.0), 11 cases × 2 templates:

| metric | generic (output_quality) | key_condition | delta | threshold |
|--------|--------------------------|---------------|-------|-----------|
| accuracy (all) | 90.91% (10/11) | 90.91% (10/11) | +0.00% | — |
| accuracy on `instruction_violation` (n=6) | 83.33% (5/6) | **100.00% (6/6)** | **+16.67pp** | gain ≥ 30% → **FAIL** |
| `false_positive_rate` on `acceptable` (n=5) | 0% | **20.00% (1/5)** | +20pp | fp ≤ 20% → at ceiling |
| tokens | 4090 | 7493 (~1.8×) | +83% | secondary cost |
| **verdict** | — | — | — | **NOT recommended (default stays output_quality)** |

**Chosen: keep `output_quality` default; ship `key_condition` as a selectable opt-in.** Reason (not "best practice"): the per-task condition hypothesis is directionally confirmed — key_condition catches every instruction violation (100% vs 83%, the 6th the generic judge missed) — but it over-flags an acceptable answer (20% FP) and costs ~1.8× tokens, so the net accuracy is a wash and it does NOT clear the pre-registered thresholds. Flipping the default would trade a sub-threshold instruction-catch gain for a real false-positive + token cost on every verification. **Rejected `key_condition`-as-default**: net accuracy tie + over-flag risk + token cost. **Rejected retiring `output_quality`**: it is the cheaper, lower-FP general judge. The mechanism still ships (option value for instruction-adherence-strict tenants, env/per-tenant togglable).

**Honesty caveat**: the generic judge is LESS blind than the theory predicted (83% on instruction_violation, not ~0%) — because the A3 trace-aware judge (Sprint 57.111) already reads `{trace}` and can reason "the user asked for exactly 3 and got 5 → contradicts the trace". So explicit per-task condition extraction adds a real-but-marginal catch (the 6th case) at a measurable FP + token cost. The 11-case corpus is a spike directional read, not a production-distribution statistic; the harness is permanent and re-runnable on a larger / harder fixture (§3 command).

## 2. Verified Invariants

### 2.1 US-1 — Per-task key-condition template (extract → check → floor)

- **Implementation**: `backend/src/agent_harness/verification/templates/key_condition.txt` — Step 1 extract the request's must-satisfy conditions from `{trace}` (count / format / ordering / inclusion / explicit constraints) with a "do not invent conditions" guard; Step 2 check `{output}` against each; Step 3 apply the generic usability floor (refuses / incoherent / empty / off-topic / contradicts-trace); verdict `passed=true` IFF every critical condition met AND floor holds. Same JSON contract `{passed, score, reason (the violated condition), suggested_correction}`.
- **Behavior**: uses the SAME `{output}` + `{trace}` placeholders as `output_quality.txt`, so `LLMJudgeVerifier._build_prompt` (`llm_judge.py:123-139`) substitutes both with NO judge code change; `_parse_response` (`llm_judge.py:141-187`) needs only `passed` so the per-condition detail rides `reason` with NO `VerificationResult` contract change. Strict superset of the generic floor (does not regress the floor categories).
- **Verification**: `cd backend && pytest tests/unit/agent_harness/verification/test_judge_templates.py -q` → 10 passed (incl. `test_key_condition_template_extracts_per_task_conditions`).
- **Test fixture**: the test reads the shipped template directly (no external fixture).

### 2.2 US-2 — Selectable via the EXISTING lever (zero code; default unchanged)

- **Implementation**: `load_template`/`list_templates` glob `*.txt` (`templates/__init__.py:47,64`) → adding `key_condition.txt` auto-makes it loadable + listed (NO `__init__.py` edit). The handler resolves the base `judge_template = settings.chat_verification_judge_template` (`handler.py:660`, env `CHAT_VERIFICATION_JUDGE_TEMPLATE`) directly, and the per-tenant override is validated `in list_templates()` (`handler.py:663`, the 57.106 C3 path). `make_chat_verifier_registry(profile.cheap, judge_template)` (`handler.py:679`) builds the judge with the selected template.
- **Behavior**: DEFAULT stays `output_quality` → dev/CI/test byte-unchanged. Only an operator who sets the env (or a per-tenant HarnessPolicy override) gets `key_condition`.
- **Verification**: `cd backend && python -c "from agent_harness.verification.templates import list_templates, load_template; assert 'key_condition' in list_templates(); assert '{output}' in load_template('key_condition'); print('OK')"`. Drive-through ARM A confirmed the env-selected template runs on the main flow.

### 2.3 US-3 — Real-Azure A/B measurement harness

- **Implementation**: `backend/scripts/benchmark_key_condition.py` (NEW; mirrors `benchmark_judge.py` scaffold: `load_cases` / `run_judge` / `build_report` / `report_to_markdown` / `_amain` / `main` + frozen `KeyCondCase`/`JudgeRun`/`KeyCondReport` dataclasses + lazy Azure import). Runs BOTH templates over the corpus (trace-aware) and computes the gain (key_cond − generic accuracy on `instruction_violation`) + false_positive_rate (acceptable wrongly failed) + `key_condition_recommended` (gain ≥ 0.30 AND fp ≤ 0.20).
- **Behavior**: a positive gain beyond GAIN_FLOOR AND fp within FP_CEILING flips `key_condition_recommended` to True; the spike measured gain +16.67% (< 30%) + fp 20% → False.
- **Verification (CI-safe)**: `cd backend && pytest tests/unit/scripts/test_benchmark_key_condition.py -q` → 9 passed (importlib-load idiom avoids the `tests.unit.scripts` shadow; a stub judge + the fixture label-consistency invariant + the gain/FP/recommendation matrix).
- **Verification (real Azure)**: `cd backend && RUN_AZURE_INTEGRATION=1 AZURE_OPENAI_*=... python scripts/benchmark_key_condition.py` → writes `benchmark_reports/` (gitignored; copied to `sprint-57-138/artifacts/key_condition_report.{md,json}`). **Cost**: ~22 Azure calls per run (11 cases × 2 templates).
- **Test fixture**: `backend/tests/fixtures/verification/key_condition_cases.yaml` (6 instruction_violation: count/oneword/ordering/unit/json/inclusion + 5 acceptable: count-met/terse/json-met/verbose-compliant/no-condition — the over-flag traps).

### 2.4 US-4 — Drive-through (real UI + backend + LLM, "兩者結合")

- **ARM A (key_condition active)** (chat-v2, real Azure gpt-5.2, jamie@acme.com·operator·acme-prod, `CHAT_VERIFICATION_JUDGE_TEMPLATE=key_condition`): "List exactly 3 primary colors." → "Red, blue, yellow" (compliant) → verification_passed (llm_judge 0.99) → loop_end stop=end_turn. The key_condition judge ran on the main flow, extracted the "exactly 3" condition, found it met → passed (no over-flag of a compliant answer).
- **ARM B (default unchanged)** (env unset → default `output_quality`): "What is the capital of France?" → "Paris" → verification_passed (0.99) → end_turn. The default path is byte-unchanged.
- **Why the CATCH is the harness not the UI**: a real LLM complies with a simple instruction on demand, so a clean instruction-violation-then-catch can't be forced in a live UI (same honest limit as 57.136's "real fail can't be forced cleanly"). The UI proves selectability + no-regression; the A/B harness (§1) proves the catch.
- **Evidence**: `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-138/artifacts/dt-57138-keycond-active-verification-passed.jpeg` + `dt-57138-default-template-no-regression.jpeg` + progress.md Day 3.

## 3. Cross-Category Contracts

**No new cross-category contract** — nothing to register in `17-cross-category-interfaces.md`. `key_condition` is a NEW judge **template** (a data file) consumed by the EXISTING `LLMJudgeVerifier` via the EXISTING `_build_prompt` `{output}`/`{trace}` substitution + the EXISTING `chat_verification_judge_template` selection wire. No new ABC, no new wire event (`WIRE_SCHEMA` stays 25), no new DB table, no `VerificationResult` field, no SSE change. Per the single-source rule, adding a 17.md row would be noise — correctly N/A.

## 4. Open Invariants (deferred / NOT verified in this spike)

- [ ] **Two-phase extract-then-check (Option B)** — a dedicated condition-extraction call feeding a per-condition check call (closer to the literal EMNLP2024 pipeline). OUT — 2× judge cost + new code → `AD-Verification-KeyCondition-TwoPhase-Phase58` (only if Option A proves material value; this spike says it does not at the current corpus).
- [ ] **Structured conditions array surfaced to the frontend** (`VerificationResult.conditions` + SSE wire + Inspector render) — OUT (contract + wire change, anti-AP-6); the per-condition detail rides `reason` → `AD-Verification-Conditions-Surface-Phase58`.
- [ ] **Flipping the default to `key_condition`** — deferred; the A/B does NOT clear the thresholds. A future A/B on a larger / instruction-heavy corpus could revisit (1-line config change).
- [ ] **Production-distribution magnitude** — the 11-case corpus compresses the signal; the harness is re-runnable on a larger / adversarial fixture for a tighter number.
- [ ] **Per-tenant key_condition opt-in driven end-to-end** — the env-selected path was driven (ARM A); the per-tenant HarnessPolicy override path (57.106 C3) is wired (`handler.py:663`) but not separately driven this sprint.

## 5. Rollback / Fallback

- **If `key_condition` ever proves harmful**: it is NOT the default — leave/set `CHAT_VERIFICATION_JUDGE_TEMPLATE=output_quality` (the pre-57.138 byte-identical path). Zero code change.
- **If the whole mechanism must be reverted**: delete `templates/key_condition.txt` (+ the harness/fixture/test + the `test_judge_templates.py` additions) — there is NO src code change to revert (the judge/loop/handler/config are untouched), so removing the template restores exact prior behavior. Estimated effort ~10 min.
- **Sentinel already in place**: the handler's per-tenant override is validated `in list_templates()` (an unknown name → the env default); an unknown env value would raise `FileNotFoundError` at judge time, but `output_quality` (the default) always exists. Misconfiguration degrades to the safe default.

## 6. References

- Sprint plan: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-138-plan.md`
- Sprint checklist: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-138-checklist.md`
- Sprint progress + retrospective: `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-138/{progress,retrospective}.md`
- Change record: `claudedocs/4-changes/feature-changes/CHANGE-105-verification-key-condition.md`
- AD source: `claudedocs/1-planning/next-phase-candidates.md` §Research-Derived Candidates (`AD-Verification-KeyCondition-PerTask`)
- Mirrored scaffold: `backend/scripts/benchmark_judge.py` (Sprint 57.111 A3) + `benchmark_correction_hygiene.py` (Sprint 57.136)
- The judge under test: `backend/src/agent_harness/verification/llm_judge.py` + `templates/output_quality.txt` (the generic baseline)
- Related design: `docs/03-implementation/agent-harness-planning/01-eleven-categories-spec.md` §範疇10 (Verification Loops)
- Research: the 2026-06-22 consolidated analysis §5 #8 (key-condition verifier, EMNLP2024)

## Modification History

- 2026-06-24: Initial extract from Sprint 57.138 closeout (Day 4) — measured +16.67pp instruction-violation gain / 20% FP / net-tie → keep output_quality default, key_condition ships as opt-in
