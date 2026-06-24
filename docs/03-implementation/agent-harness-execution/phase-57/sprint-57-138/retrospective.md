# Sprint 57.138 Retrospective — verification key-condition judge (per-task condition template + A/B accuracy spike)

[Plan](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-138-plan.md) · [Checklist](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-138-checklist.md) · [Progress](./progress.md)

**Closed**: 2026-06-24 · **Branch**: `feature/sprint-57-138-verification-key-condition` · **Base**: main `57423a80`

---

## Q1. What was delivered?

A thin evidence-first spike closing `AD-Verification-KeyCondition-PerTask` (research #8, the 3rd item in the canonical research §5 order after #6 + #3). A NEW `key_condition.txt` judge template extracts the request's per-task must-satisfy conditions (count / format / ordering / inclusion) and checks each — a superset of the generic `output_quality` 5-failure-mode floor — selectable via the EXISTING `chat_verification_judge_template` lever (DEFAULT unchanged). A permanent real-Azure A/B harness measured it before deciding the default. **Verdict: keep `output_quality` default** — key_condition catches instruction-following violations the generic judge misses (100% vs 83% on instruction_violation, +16.67pp) BUT over-flags acceptable answers (20% FP) + costs ~1.8× tokens → net accuracy tie → does NOT clear the recommendation thresholds; `key_condition` ships as a selectable opt-in. Backend-only, NO loop.py / config / handler / migration / wire / frontend change. CHANGE-105 + design note 42.

## Q2. Calibration — estimate vs actual

- **Scope class**: `verification-keycondition-spike` **0.60** (NEW, 1st data point). Analogous to `verification-context-hygiene-spike` 0.60 (57.136) + `verification-trace-and-benchmark-spike` 0.60 (57.111) + `verification-in-loop-spike` 0.60 (57.98) — a Cat 10 verification spike paired with a measurement harness + drive-through.
- **Agent-delegated: no** (parent-direct; the value is the key-condition prompt design + the A/B evidence judgment + the instruction-following corpus, not mechanical pattern reuse). `agent_factor` 1.0 → 3-segment form.
- **Estimate**: bottom-up ~11 hr → class-calibrated commit ~6.6 hr (mult 0.60).
- **Actual**: ~6.5 hr (Day 0 三-prong ~0.75 · Day 1 template+selectability+test ~1.25 · Day 2 harness+corpus+CI test+A/B ~2.5 · Day 3 drive-through ~1 · Day 4 closeout ~1, overlapping same-day). **Ratio actual/committed ≈ 0.98 — IN band.** Single data point → KEEP 0.60 pending 2–3 sprint validation. If a 2nd `verification-keycondition-spike` diverges > 30%, re-point.
- This spike was LIGHTER on src than 57.136/137 (a template data file + a harness script; NO loop.py/config edit — Day-0 found the lever auto-selectable via glob, dropping the planned `__init__.py` edit). The plan §7 flagged the ceremony-not-code-accelerated risk; it did NOT fire — the harness (~3 hr) is a real-code core, so the 0.60 held (consistent with the 57.137 lesson: a >~3 hr real implementation core holds the spike multiplier).

## Q3. What went well?

- **Evidence-first discipline held**: measured the generic-vs-key-condition gap with a real-Azure A/B BEFORE recommending a default flip. The number (gain +16.67% / fp 20% / net tie) gated the decision — a blind flip to key_condition would have shipped a real false-positive + token cost for a sub-threshold gain. A "directionally real but inconclusive" result is a valid spike outcome (same as 57.136).
- **Day-0 三-prong = zero drift + scope reduction**: all 6 D-rows GREEN; D-list-templates found `list_templates()`/`load_template` glob `*.txt` → `key_condition` auto-selectable with ZERO `templates/__init__.py` edit (the planned file #6 dropped). The whole sprint touched NO src code (template = data file; harness = new script; 1 test edit).
- **Maximally surgical via existing machinery**: the spike rides the glob template loader + the existing `chat_verification_judge_template` wire + the `benchmark_judge.py` scaffold + the A3 `{trace}` placeholder. No new primitive, ABC, contract, wire event, schema, or loop/config/handler change — the lowest-risk shape possible.
- **DEFAULT unchanged = zero rollback risk**: there is no src code to revert; deleting the template restores exact prior behavior. The handler's `in list_templates()` validation + the `output_quality` default mean any misconfiguration degrades safely.
- **Drive-through "兩者結合" was honest**: ARM A proved the key_condition template selectable + running on the main flow + passing a compliant answer (no over-flag); ARM B proved the default unchanged. We did NOT claim the UI drove the catch (a real LLM complies on demand — the catch is the deterministic A/B harness; stated plainly, same as 57.136).
- **57.136 partial-gate lesson applied**: Day 1 ran the full `test_judge_templates.py` surface (not just the new test); no late regressions.

## Q4. What to improve next sprint?

- **Corpus size for a tighter number**: 11 cases is a spike directional read; the A/B's net-tie verdict could shift on a larger / instruction-heavy corpus. The harness is permanent + re-runnable — a future sprint wanting a production-distribution number can extend the fixture (the GAIN_FLOOR/FP_CEILING thresholds are already parameterized).
- **A3 trace-awareness confound**: the generic judge scored 83% on instruction_violation (not ~0%) because it already reads `{trace}` and can infer "asked 3, got 5 → contradicts". The A/B would isolate the key-condition contribution more cleanly if it ALSO ran a no-trace generic arm (like benchmark_judge's trace_delta) — noted for a follow-on if #8 is revisited.

## Q5. Anti-pattern self-check (04-anti-patterns / 11-point)

- **AP-1** (pipeline-as-loop): N/A — no loop logic; a judge template.
- **AP-2** (orphan/dead code): ✅ the template is reachable via the existing selection wire + tested + drive-through-verified active; the harness has a real A/B run + CI-safe tests. No dead path.
- **AP-3** (cross-dir scatter): ✅ Cat 10 template in `verification/templates/`; Cat 10 eval in `scripts/` + `tests/`. Each in its home.
- **AP-4** (Potemkin): ✅ the template actually changes the judge's reasoning (drive-through ARM A ran it + it passed a compliant answer); the harness produces a real number; the A/B verdict is honest (NOT recommended — a negative-ish result, not a rubber stamp).
- **AP-6** (future-proofing): ✅ two-phase Option B + structured-conditions surface + default-flip all explicitly OUT (→ Phase 58 ADs); template-only this sprint, no speculative contract.
- **AP-8** (no centralized PromptBuilder): N/A — the judge uses the existing `_build_prompt`; the template is just a new prompt string.
- **AP-11** (version suffix / misnaming): ✅ no `_v2`/`_old`; `key_condition` names exactly what it does.
- **v2 lints**: 10/10 (incl. check_llm_sdk_leak — the harness uses the Verifier ABC; the Azure profile is built only in `main()`).

## Q6. Process lesson (for the matrix / future plans)

**The cheapest spike shape is one that rides an existing selection wire — and Day-0 Prong-2 can prove the code change is ZERO before any code is written.** This spike's entire mechanism is a data file (a new template) made live by the existing glob loader + the existing `chat_verification_judge_template` setting. Day-0 D-list-templates (reading `templates/__init__.py`) confirmed `list_templates()` globs → the planned `__init__.py` edit was unnecessary → the sprint touched zero src code. The lesson: when planning a "new variant of an existing thing" spike, Day-0 should specifically check whether the existing selection/registration mechanism is dynamic (glob / registry) vs hardcoded — a dynamic one makes the variant a pure data + measurement add (lowest risk). (Recorded; consistent with the 57.137 D-list-templates-style finding.)

## Q7. Carryover / open items

- `AD-Verification-KeyCondition-TwoPhase-Phase58` — dedicated extract-then-check pipeline (only if a future A/B shows Option A's single-call gain is materially capped by the single call).
- `AD-Verification-Conditions-Surface-Phase58` — surface the structured conditions array (`VerificationResult.conditions` + SSE + Inspector).
- Larger / instruction-heavy A/B corpus + a no-trace generic arm (to isolate the key-condition contribution from A3 trace-awareness) — the harness is permanent + re-runnable.
- `AD-Verification-KeyCondition-PerTask` itself — **CLOSED** (mechanism shipped + measured; directionally real but below the default-flip thresholds; ships as opt-in).
- **Next per the canonical research §5 order**: #4 `AD-Context-Layered-Compaction-ACON`.

---

## Design Note Extract (spike sprint)

**File**: `docs/03-implementation/agent-harness-planning/42-verification-key-condition-design.md`
**Verified ratio (estimated)**: ≥ 95% (every claim file:line-anchored; the A/B is a reproducible real-Azure run)
**8-Point Quality Gate**:
- [x] 1. Section header maps to US
- [x] 2. file:line references
- [x] 3. Decision matrix (the generic-vs-key_condition A/B)
- [x] 4. Verification command (per invariant + A/B rerun)
- [x] 5. Test fixture (`key_condition_cases.yaml` + real-Azure cost note)
- [x] 6. Open-invariant boundary
- [x] 7. Rollback path (default-template stays output_quality + delete the template; zero code revert)
- [x] 8. 17.md cross-ref (NO new contract — template-only, justified N/A)

**Reviewer pass**: self-review (solo-dev)
