# Sprint 57.98 Retrospective — Verification into the loop (A1)

**Plan**: [`sprint-57-98-plan.md`](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-98-plan.md) · **Checklist**: [`sprint-57-98-checklist.md`](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-98-checklist.md) · **Progress**: [`progress.md`](./progress.md)
**Branch**: `feature/sprint-57-98-verification-in-loop` (from `main` `84389e91`) · **Closed**: 2026-06-10
**Design note**: [`25-verification-in-loop-design.md`](../../../agent-harness-planning/25-verification-in-loop-design.md) · **Change record**: `CHANGE-065`

---

## Q1 — What was delivered (vs plan)?

All 6 user stories shipped, gate-green + drive-through PASS:

- **US-1** — `AgentLoopImpl.__init__` gains `verifier_registry` (+ `max_correction_attempts=2`); optional, default `None` → byte-identical when absent. ✅
- **US-2** — `_cat10_verify_gate()` runs in `_run_turns` AFTER the Cat 9 output guardrail, BEFORE the terminator (locked guardrail→verification order); PASS→deliver / FAIL<max→re-inject the failed answer + a `user` correction `Message` + `continue` (the next turn re-answers, same LOOP span) / FAIL==max→`LoopCompleted(stop_reason="verification_failed")`. ✅
- **US-3** — the attempt counter is durable across pause→resume via `metadata["verification_attempts"]` on the checkpoint (design pivot D-DAY2-1 from the planned `DurableState` scalar — the checkpoint serializer is an allowlist). ✅
- **US-4** — terminal `verification_failed`; the resume path is now verified for free (`resume()` drives the shared `_run_turns` + the ctor injection); `_replay_approved_output` is NOT re-verified (code-path isolation). ✅ — **this closes a real correctness hole**: pre-57.98 a HITL-paused→resumed answer was delivered UN-verified.
- **US-5** — the `run_with_verification` wrapper is deleted (sole consumer was the router); `handler.py` injects the registry into the ctor; the verification_log persistence migrated to `verification/persistence.py`; the 2 wrapper test files converted (Never-Delete via git mv). ✅
- **US-6** — drive-through PASS (real UI + backend + Azure gpt-5.2): the gate fires IN-STREAM before `loop_end`; `resume()` re-enters the gated loop. ✅

**Scope held**: no A2 (ESCALATE), no A3 (trace-critique), no deliver-with-flag, no per-tenant policy. `events.py` / `ModelProfile` / frontend / DB diff = 0.

## Q2 — Estimate accuracy / calibration

- **Scope class**: `verification-in-loop-spike` (NEW, 0.60 mid-high) — 1st data point. A new-domain `loop.py`-core spike, analogous to `subagent-child-loop-spike` 0.60 (57.94).
- Bottom-up est ~20 hr → class-calibrated commit ~12 hr (mult 0.60) → **actual ~11 hr** → ratio (actual/committed) ≈ **0.92** — **IN band** (target ~1.0; lower-trigger is 3-consec <0.7). KEEP 0.60 pending 2-3 sprint validation.
- **`agent_factor` = 1.0** (Agent-delegated: **no** — parent-direct). The in-loop critique re-loop + the durable-counter-across-resume + the drive-through were loop-core correctness work; this does NOT extend the AgentDelegated-WallClock streak.
- Recorded: `calibration-log.md §3` + `sprint-workflow.md §Scope-class multiplier matrix`.

## Q3 — What went well

- **Day-0 three-prong recon paid off (again)**: 7 Prong-2 confirmations + 7 drift findings, ALL reducing or confirming scope (≈0% shift). The keystone insight — `resume()` drives the shared `_run_turns` (the 57.89/90 payoff) so the gate covers resume for FREE — turned a feared "loop surgery" into a ctor-param + one gate method.
- **The metadata pivot (D-DAY2-1)** avoided a serializer/migration change: carrying the counter on `metadata` (the 57.88 `pending_approval` precedent) instead of a new `DurableState` scalar kept the blast radius minimal and round-trip proven.
- **The wrapper deletion resolved a lint cycle for free (D-DAY2-3)**: removing `run_with_verification` killed the `__init__`→wrapper→`orchestrator_loop` import cycle, letting `loop.py` switch to the clean PACKAGE import → `check_cross_category_import` green.
- **Drive-through gave the structural proof**: the `verification_passed` event sitting IN-STREAM before `loop_end` (vs the wrapper's after-`LoopCompleted` emission) is the visible, unfakeable proof the gate moved into the loop.

## Q4 — What to improve (lessons / ADs)

- **D-DAY2-2 — Day-0 Q7 undercount**: Day-0 claimed "the router is the SOLE tuple-unpacker"; reality = production `resume/service.py` + 7 test files also unpacked. *Lesson*: when a return-shape changes, grep the unpacker pattern (`X, _ = build_…`) across **both** src AND tests at Day-0, not just non-test consumers. (Folded into the existing Prong-2 discipline; no new rule needed — the existing "claimed-but-missing-X grep" covers it if applied to the unpacker site.)
- **D-DAY2-4 — a default-ON gate perturbs mock-loop wiring tests** (the 20-min runtime scare): injecting a REAL `LLMJudgeVerifier` made the keystone/tier2 wiring tests (which build a real_llm handler + drive a mock loop to FINAL) fire the gate on a fake-Azure endpoint that RETRIES. *Lesson*: a wiring test that builds a real-LLM handler but swaps the loop's chat client must pin `CHAT_VERIFICATION_MODE=disabled` (+ `get_settings.cache_clear()`) — the gate's verifier has its OWN client, not the swapped mock. This is a Risk-Class-C-adjacent pattern (a newly-default-ON cross-cutting gear surfaces in unrelated wiring suites); candidate for a `testing.md` note if it recurs.
- **Honest drive-through gaps**: a real gpt-5.2 answer passes the output_quality judge first try (score 0.99), so the literal fail-then-pass correction + the verified-resumed-FINAL answer could not be forced with a real judge → both are deterministically unit-proven, NOT drive-driven. Marked as such (no "verified" claimed for the un-driven legs). A strict-judge template to force a real fail-then-pass is a carryover.

## Q5 — Carryover / open items (→ next-phase-candidates.md)

- **A2** — verification-ESCALATE human-in-the-loop (max-attempts → `_emit_deferred_pause(kind="verification")` + approve/reject-with-note → human-coached correction). The natural next slice of workflow A.
- **A3** — trace-aware critique verifier (sees recent turns/tool errors) + a formal cheap-judge accuracy benchmark (design-note 24 carryover).
- **deliver-with-flag terminal** (option b) — needs a new event/UI flag.
- **per-tenant verification mode/template** (Config 分層 = workflow C / C3).
- **cheap-judge accuracy** — whether the cheap tier over/under-corrects vs strong (A3).
- **judge-token accounting across a mid-correction pause** (D-DAY1-3) — may under-count on a rare pause-mid-correction.
- **strict-judge drive-through** — a template to force a real fail-then-pass + verified-resumed-FINAL for a future drive-through.

## Q6 — Design-Note Extract (spike sprint — 8-Point Quality Gate self-check)

**File**: `docs/03-implementation/agent-harness-planning/25-verification-in-loop-design.md`
**Verified ratio (estimated)**: ~96% (every §2 invariant + §1 matrix row backed by a post-edit file:line + a `pytest` command; §4 Open Invariants explicitly fenced as NOT-verified).

| # | Gate item | Pass |
|---|-----------|------|
| 1 | Section header maps to spike US | ✅ §2.1–2.5 = US-1..US-5; §0 = US-6 drive-through |
| 2 | each technical claim has file:line | ✅ post-edit refs (`loop.py:417/468/1606/2318-2346/2805/3185-3186/220`; `persistence.py:44`; `registry.py:30/40`) |
| 3 | Decision matrix (≥4 rows) | ✅ 5 rows (where-verify / gate-order / counter-durability / terminal / replay) + chosen + rejected + why |
| 4 | verification command (reproducible) | ✅ `pytest …/test_loop_verification_gate.py` + `…/test_loop_pause_resume.py::…` + the drive-through reproduce |
| 5 | test fixture reference | ✅ mock registry + `FakeChatClient` + pause-resume fakes + converted persist fixtures + artifact PNGs |
| 6 | Open invariants split (fenced) | ✅ §4 (A2 / A3 / deliver-with-flag / per-tenant / cheap-judge accuracy / cross-pause tokens) explicitly NOT-verified |
| 7 | rollback path | ✅ §5 (git revert restores `correction_loop.py`; the `chat_verification_mode` env flag is an instant kill-switch) |
| 8 | 17.md cross-ref | ✅ §3 (`VerificationResult` bubble / `LoopCompleted` judge-token + `verification_failed` terminal origin; registry loop-injected) |

**Reviewer pass**: self-review (solo-dev). 8/8.

## Q7 — Risk classes hit / discipline

- **Risk Class E (stale `--reload` backend)** — MATERIALIZED + handled: the running backend (parent 26332 + worker 56968) was 6/9 = pre-57.98 (still the wrapper). Clean restart (kill both → verify `:8000` FREE + no orphan → fresh PID 40280) before the drive-through. 8th consecutive sprint (57.91-98) bitten by this; the §Risk Class E `Get-CimInstance Win32_Process` PID/PPID/StartTime sweep held.
- **Risk Class C (test isolation)** — adjacent: D-DAY2-4 (a default-ON gate firing in wiring suites) is a "newly-default-ON cross-cutting gear surfaces in unrelated suites" variant; fixed by env-pinning the wiring helpers.
- **Discipline self-check**: no future sprint plans pre-written (A2 is the next slice, written only when A1 closes); no plan/checklist skipped; no unchecked `[ ]` deleted (the superseded `DurableState`-scalar items marked 🚧 + reason); the retrospective records lessons, not future sprint tasks.

---

**Verdict**: A1 done — the Cat 10 verification gate is a real in-loop pre-delivery gear (not an outer wrapper), the resume correctness hole is closed, the wrapper is retired, and the move is drive-through-proven LIVE. push + PR pending user authorization.
