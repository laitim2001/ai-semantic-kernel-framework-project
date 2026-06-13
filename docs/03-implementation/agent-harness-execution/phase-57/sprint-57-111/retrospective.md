# Sprint 57.111 Retrospective — A3: trace-aware critique verifier + permanent cheap-judge accuracy benchmark

**Closed**: 2026-06-13 · **Slice**: A3 (the LAST harness-deepening slice; closes the 10-slice set — only non-mandatory follow-ons remain) · **Branch**: `feature/sprint-57-111-trace-aware-critique-benchmark`

## Q1 — What shipped

1. **US-1 trace-aware critique** — the in-loop Cat 10 LLM judge now sees recent turns + tool errors, not just the final string. The single load-bearing change was `loop.py:1684` `state=cast(LoopState, None)` → a real `trace_state` the gate builds from its `messages` (mirroring the Cat 4 `compact_state` idiom). `verification/_trace.py` (bounded formatter) + `llm_judge._build_prompt(output, state)` substitutes `{trace}` + `output_quality.txt` gained a `{trace}` section + an optional judge `temperature`. ABC widened `state: LoopState | None` (removed the 4-site `cast(None)` type-lie). `loop.py` diff = 25 ins/3 del, threading only.
2. **US-2 permanent cheap-judge benchmark** — `scripts/benchmark_judge.py` (load/run/score + `main()` CLI) + a 28-case hand-labeled golden fixture + a `@pytest.mark.benchmark` real-LLM wrapper + 9 CI-safe logic tests + the `benchmark` marker. Re-runnable two ways (`pytest -m benchmark` / `python scripts/benchmark_judge.py`).
3. **The verdict** — real Azure: cheap **92.86%** (stable), trace_delta **+42.86%** (stable), floor PASS → **keep the cheap tier** (settles design note 24's open invariant with a number).

## Q2 — Estimate accuracy / calibration

- Scope class **NEW `verification-trace-and-benchmark-spike` 0.60** (1st data point) — a new-domain spike touching `loop.py` (trace threading) + a greenfield eval harness. Sibling of `verification-in-loop-spike` 0.60 (57.98).
- Bottom-up est ~13.5 hr → class-calibrated commit ~8 hr (mult 0.60). **Agent-delegated: no** (parent-direct — the loop threading is correctness-sensitive + golden-dataset labeling is judgment; `agent_factor = 1.0`).
- **Actual ≈ committed** (ratio ~1.0–1.1, IN band upper edge). The over-edge was the drive-through + tooling discovery loop (the `tests.unit.scripts` import shadow D12, the cp950 `print` crash D-DAY3-1, the `api.main:app` startup-path correction, 2 MHist E501s caught at the Day-3 sweep) — the same "dt discovery loop pushes a clean spike to the band's upper edge" shape as 57.109/57.110. KEEP 0.60, single data point.

## Q3 — What went well

- **The ABC was already trace-ready** — A1's `state` param meant US-1 was "stop passing None + read it", not a new contract. Day-0 Prong-2 caught the 4-site `cast(None)` pattern → scoped trace-awareness to the gate, kept the 3 fallback paths on the back-compat empty-trace path.
- **The benchmark proved US-1 better than the UI could** — `trace_delta +42.86%` over 7 trace_dependent cases (stable ×2) is a stronger, quantitative proof than a single UI fail observation, AND it surfaced a genuine surprise (the STRONG tier over-flags clear_pass; the cheap tier is better-aligned to the lenient contract).
- **Day-0 三-prong paid off again** — D2 (no `LoopState` in `_run_turns`) + D3 (`compact_state` build idiom) + D6 (CI has no `-m` filter → skipif gate, dropped a file) settled the design before Day-1 code.

## Q4 — What to improve / carryover ADs

- **AD-Lint-MHist-Verbosity recurred 3× — one escaped to CI** — 3 MHist lines slipped E501 this sprint: 2 (`_abc.py`/`llm_judge.py`) caught at the Day-3 sweep, **1 (`loop.py:48`, 108 chars) escaped to CI** (`flake8 src/ tests/` red on PR #286) → CI-hotfixed. **Root process miss**: my local flake8 ran TARGETED files (`flake8 <specific paths>`), NOT the FULL `flake8 src/ tests/` that CI runs — a targeted sweep that didn't re-hit loop.py:48 after the header edit. **Lesson (reinforced hard)**: run the FULL `flake8 src/ tests/` (CI-identical command) before declaring flake8 clean, AND re-run after EVERY MHist/header edit (they land post-test-run, after the targeted sweep). The targeted-flake8 shortcut is the bug.
- **`AD-Benchmark-Live-Trace-Fail-Drive`** (🟢) — a live chat trace-dependent FAIL was not engineered (gpt-5.2 won't claim success after a tool error w/o a config change). A future drive could swap the live judge template to `forced_fail_trace.txt` (created this sprint, unused) or inject a tool-error scenario to show the trace-citing critique in the UI. The behavior is proven quantitatively (Leg B); the UI fail-render is the gap.
- **`AD-Strong-Tier-Over-Flags-ClearPass`** (🟢) — the benchmark surfaced the strong tier (gpt-5.2) flagging good short answers as failures (clear_pass 37.5–87.5%, run-variant even at temp 0). Worth a follow-up: is the judge template too strict for the strong model, or is the strong model genuinely noisier as a lenient judge? Affects any future "move judge to strong" decision.
- **`AD-Benchmark-Floor-Calibration`** (🟢) — `CHEAP_ACCURACY_FLOOR=0.70` is a first guess; the real run (cheap 92.86%) suggests headroom to raise it (~0.85) once 2-3 runs confirm stability.

## Q5 — V2 discipline check (9)

1. Server-Side First ✅ 2. LLM Neutrality ✅ (`_trace`/benchmark operate on the `Verifier`/`Message` ABCs; no SDK import; `check_llm_sdk_leak` green) 3. CC not copied ✅ 4. 17.md single-source — N/A (Verifier ABC `state` widened to Optional; the contract row may want a note — Day-4 17.md check) 5. 範疇 ✅ (Cat 10 + Cat 1 gate threading + eval tooling in `scripts/`) 6. anti-patterns ✅ (no Potemkin — the benchmark is exercised; the trace-aware path drive-driven; honest dt scope recorded) 7. workflow ✅ 8. file header ✅ (MHist 1-line, E501-fixed) 9. multi-tenant — N/A (no DB).

## Q6 — Spike Design Note Extract (§5.5 — A3 is a spike)

**File**: extends `25-verification-in-loop-design.md` §2.6 (trace-aware) + §4 open-invariants SHIPPED + `24-multi-model-profile-design.md` §4 verdict (design note 26 NOT created — A3 is the natural continuation of note 25's verification-in-loop design).
**8-Point Quality Gate**:
- [x] 1. Section header maps to the A3 user story (§2.6 "US-1 trace-aware critique")
- [x] 2. Each claim has file:line (`loop.py:1684` gate / `_trace.py` / `llm_judge.py:_build_prompt` / `_abc.py` widen)
- [x] 3. Decision rationale (build trace_state vs thread state — D3 `compact_state` idiom; floor on unambiguous categories)
- [x] 4. Verification command (`RUN_AZURE_INTEGRATION=1 python scripts/benchmark_judge.py` / `pytest -m benchmark`)
- [x] 5. Test fixture reference (`tests/fixtures/verification/judge_benchmark.yaml`, 28 cases)
- [x] 6. Open invariant boundary (verified: trace-aware path + benchmark verdict; deferred: live trace-fail UI render `AD-Benchmark-Live-Trace-Fail-Drive`)
- [x] 7. Rollback (revert the gate arg + the ABC widen restores `state=None`; the benchmark is additive/on-demand)
- [x] 8. 17.md cross-ref (Verifier ABC §2.1 — `state` now Optional)
**Verified ratio (est)**: ~95% (every design claim has a real anchor + the benchmark is a real-Azure measurement).

## Q7 — Outcome

A3 SHIPPED. The harness-deepening 10-slice mandatory + optional set is COMPLETE (A1→A2→B1→B2a→B2b→C1→B3→UX→C2→B4→A3). The agent harness now: verifies in-loop (A1), escalates to a human on max-fail (A2), and critiques trace-aware (A3); cheap-tier verification is measured + confirmed (92.86%, keep cheap). Remaining work is the `next-phase-candidates.md` pool (Skills system, IAM Block B/C, SOC 2 + SBOM, frontend mockup rebuild, non-Azure adapters) — none mandatory to the harness.
