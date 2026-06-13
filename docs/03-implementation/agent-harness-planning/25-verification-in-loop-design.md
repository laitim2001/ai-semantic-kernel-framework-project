---
title: 25-verification-in-loop design note
purpose: Spike-extract design note from Sprint 57.98; documents the verified runtime invariants of moving the Cat 10 verification gate from an outer wrapper into the orchestrator loop (`_run_turns`), with the resume path covered for free
category: V2 extension docs (post-22-sprint era)
created: 2026-06-10 (Sprint 57.98 Day 4 closeout)
sprint_source: 57.98
verified_ratio: ≥ 95% (per 8-Point Quality Gate)
status: Active
---

# 25-verification-in-loop Design Note (Sprint 57.98 extract)

> **8-Point Quality Gate self-check** is recorded in `agent-harness-execution/phase-57/sprint-57-98/retrospective.md` §Design-Note Extract (Q6). All file:line refs below are **post-edit** (Sprint 57.98 HEAD), not the Day-0 recon anchors.

## 0. Spike Summary

- **Sprint scope** (US-1..US-6): the loop receives the verifier by construction (US-1); a `_cat10_verify_gate()` runs inside `_run_turns` AFTER the Cat 9 output guardrail, BEFORE the terminator (US-2); the correction attempt count is durable across pause→resume (US-3); the max-attempts terminal is `stop_reason="verification_failed"`, the resume path is now verified, and a human-approved replay is NOT re-verified (US-4); the outer `run_with_verification` wrapper retires (US-5); a real UI + backend + Azure drive-through proves the gate is LIVE in-stream and resume re-enters the gated loop (US-6).
- **Verified period**: 2026-06-10 (Day 0 recon → Day 3 drive-through).
- **Calibration**: bottom-up ~20 hr → class-calibrated commit ~12 hr (mult 0.60, NEW `verification-in-loop-spike`) → actual ~11 hr (ratio ~0.92, IN band). `agent_factor = 1.0` (parent-direct; does NOT extend the AgentDelegated-WallClock streak).
- **Verification**: pytest **2290 passed + 4 skipped** (`-m "not real_llm"`; NET −5 vs 2295 baseline = test consolidation, no coverage loss) · mypy `src` **0/353** · `run_all` **10/10** · black/isort/flake8 clean · drive-through PASS (2 artifact PNGs).
- **Locked decisions** (AskUserQuestion 2026-06-10): gate order = **guardrail → verification**; attempt counter = **durable (checkpoint)**; max-after terminal = **`stop_reason="verification_failed"`** (A1 default; ESCALATE→A2 deferred).
- **Record**: CHANGE-065 + 17.md verifier-flow update; no new event/wire/codegen/DB/frontend change.

## 1. Decision Matrix

| Decision | Option chosen | Rejected alternative(s) | Why |
|----------|---------------|-------------------------|-----|
| **Where verification runs** | **In-loop gate** inside `_run_turns` (`loop.py:1606` + integration `:2318-2346`) | Outer wrapper `run_with_verification` around `loop.run()` (the retired 57.97 design) | The wrapper only wrapped the chat `run()` path — `loop.resume()` was streamed un-wrapped → **a resumed answer was never verified** (a real correctness hole). Each correction was a fresh top-level `run()` (full prompt re-assembly, fresh LOOP span, turn-counter reset → no Cat 4 prefix-cache hit). In-loop covers both entry points and makes correction the next turn of the SAME loop. |
| **Gate order vs the Cat 9 output guardrail** | **guardrail → verification** (verify gate slots AFTER `_cat9_output_check`, BEFORE the FINAL terminator; `loop.py:2318`) | verification → guardrail | A guardrail ESCALATE is a safety/compliance stop that must pre-empt a quality judge; verifying an answer the guardrail would block wastes a cheap-tier judge call. Mirrors the `_cat9_output_*` pause family ordering. |
| **Correction attempt counter durability** | **Durable** — rides `state.durable.metadata["verification_attempts"]` on the existing checkpoint (`loop.py:3185-3186` write, `:2805` resume-read) | (a) Transient `_run_turns` local only; (b) a new `DurableState.verification_attempts` scalar field | (a) would reset the count when a correction hits a guardrail-ESCALATE pause and resumes hours later. (b) was the Day-0 plan, but the checkpoint (de)serializer (`checkpointer.py:217/243`) is an explicit field **allowlist** → a new scalar would NOT round-trip without editing both ends + README. `metadata` round-trips verbatim (the 57.88 `pending_approval` precedent) → lower blast radius, zero serializer/migration change (**D-DAY2-1**). |
| **Max-attempts terminal** | **`LoopCompleted(stop_reason="verification_failed")`** (raw string; `loop.py:220` + `:2346`) | (a) a new `TerminationReason.VERIFICATION_FAILED` enum; (b) deliver-with-flag (deliver the answer but flag it failed); (c) ESCALATE to a human pause | (a) `stop_reason` is a raw `str` and no consumer switches on it (Day-0 Q6) → no enum needed (the 57.92/93 LoopCompleted-Nth-origin precedent). (b) would need a new event/UI flag. (c) is workflow A2 (deferred). A1 preserves today's terminal semantics. |
| **Human-approved replay re-verification** | **NOT re-verified** (by code-path isolation — `_replay_approved_output` re-emits the snapshot directly, never routes through parse→gate) | Re-verify the replayed answer | Human authority > machine judge: re-judging a HITL-APPROVED held answer would let a cheap judge override a human approval. Day-0 Q2 confirmed `_replay_approved_output` re-emits directly → satisfied without an explicit skip flag. |

## 2. Verified Invariants

### 2.1 (US-1) The loop receives the verifier by construction
- **Implementation**: `AgentLoopImpl.__init__(..., verifier_registry: "VerifierRegistry | None" = None, max_correction_attempts: int = 2)` at `backend/src/agent_harness/orchestrator_loop/loop.py:417`; stored `self._verifier_registry = verifier_registry` at `:468`. `VerifierRegistry` imported under `TYPE_CHECKING` (the gate duck-types `get_all()`/`len()`); `VerifierRegistry` ABC at `verification/registry.py:30` (`get_all()` `:40`).
- **Behavior**: optional param defaulting `None` → all existing construction sites still build; `verifier_registry is None` → the gate is skipped → byte-identical to the pre-57.98 non-verified path.
- **Verification**: `pytest backend/tests/unit/agent_harness/orchestrator_loop/test_loop_verification_gate.py::test_gate_skipped_when_empty_registry`.
- **Test fixture**: a mock `VerifierRegistry` built in `test_loop_verification_gate.py` (in-file fakes).

### 2.2 (US-2) The `_cat10_verify_gate()` runs in-loop, AFTER the guardrail, BEFORE the terminator
- **Implementation**: `_cat10_verify_gate()` at `loop.py:1606` (reads `self._verifier_registry` `:1631`, builds the correction block via `_build_correction_block()` `:350` called `:1692`, returns a `_VerifyVerdict` `:329`). Integrated in `_run_turns` gated on `self._verifier_registry is not None AND len(...) > 0` at `:2318-2319`, called `:2321`; the `is_final_answer` predicate is reused verbatim from the 57.93 output pre-gate (`should_terminate_by_stop_reason(response) or classify_output(response) == OutputType.FINAL`).
- **Behavior**: PASS → `yield VerificationPassed` → deliver (judge tokens stamped on the END_TURN terminator); FAIL with `attempts < max` → `yield VerificationFailed(correction_attempt=n)` + append the failed assistant answer + a `user`-role correction `Message` + `verification_attempts += 1` (`:2341`) + `continue` (the next turn re-answers — prefix-stable for the Cat 4 cache); FAIL at max → `LoopCompleted(stop_reason="verification_failed")` (`:2346`). The correction is a NORMAL TAO turn (turn_count increments, SAME LOOP span — not a new run), so it is naturally Inspector-visible.
- **Verification**: `pytest backend/tests/unit/agent_harness/orchestrator_loop/test_loop_verification_gate.py` (pass-delivers / fail-then-pass-reinjects-as-new-turn / fail-at-max→`verification_failed` / no-registry-skipped) + `pytest backend/tests/unit/agent_harness/verification/test_inloop_gate_tokens.py` (5 judge-token cases + non-final-skip).
- **Test fixture**: a `FakeChatClient` (tool-use + token clamp) + mock verifiers in `test_inloop_gate_tokens.py`.
- **Drive-through proof**: Loop visualizer event stream `… state_checkpointed → verification_passed (llm_judge score=0.99) → loop_end` — the `verification_passed` event sits INSIDE the loop stream, BEFORE `loop_end` (the wrapper emitted it AFTER `LoopCompleted`). Artifact `sprint-57-98-1-inloop-verification-pass.png`.

### 2.3 (US-3) The attempt counter is durable across pause→resume
- **Implementation**: written to `metadata["verification_attempts"]` only when `> 0` at `loop.py:3185-3186` (inside `_emit_state_checkpoint`); threaded through `_emit_deferred_pause` + the 3 mid-correction pause chains (between-turns / output-escalate / tool-HITL); `resume()` reads it back at `loop.py:2805` (`int(state.durable.metadata.get("verification_attempts", 0))`) → passes to `_run_turns`; a fresh `run()` passes 0 (reset).
- **Behavior**: a correction that hits a guardrail-ESCALATE pause and resumes continues counting (not reset); a fresh run starts at 0.
- **Verification**: `pytest backend/tests/unit/agent_harness/orchestrator_loop/test_loop_pause_resume.py::test_durable_counter_survives_pause_mid_correction` (resumed attempts are 1,2 — NOT 0,1,2) + `::test_fresh_run_starts_counter_at_zero` (0,1,2).
- **Test fixture**: the existing pause-resume fakes in `test_loop_pause_resume.py` + a `verifier_registry` added to the resume loop; a paused state seeded with `metadata["verification_attempts"]=1`.

### 2.4 (US-4) Terminal + resume coverage + replay-not-reverified
- **Implementation**: terminal `LoopCompleted(stop_reason="verification_failed")` (`loop.py:220` constant + `:2346`); resume coverage = NO new code (`resume()` drives the shared `_run_turns` at `loop.py:2470`, and `build_real_llm_handler` injects the registry into the ctor → the resumed answer is verified by the same gate); replay-not-reverified = `_replay_approved_output` re-emits the snapshot directly (no parse→gate).
- **Behavior**: max → `verification_failed`; a resumed continuation's final answer is verified (closes the pre-57.98 hole); an approved replay is delivered WITHOUT calling the verifier.
- **Verification**: `pytest backend/tests/unit/agent_harness/orchestrator_loop/test_loop_pause_resume.py::test_resumed_continuation_answer_is_verified` + `::test_replay_approved_output_not_reverified`.
- **Test fixture**: `test_loop_pause_resume.py` `_PassingVerifier`/`_FailingVerifier` + `_paused_state_verified(kind=tool|output, …)` helpers.
- **Drive-through proof**: input-ESCALATE "approval required" → `awaiting_approval` (checkpoint v2) → Approve & continue → APPROVED → resumed turn 5 ran through the resumed `_run_turns` (the host of the in-loop gate). Artifact `sprint-57-98-2-resume-reenters-gated-loop.png`. (Real-LLM chose a tool call on that turn, not a FINAL answer; the verified-resumed-FINAL property is the deterministic unit test above.)

### 2.5 (US-5) The wrapper retired; the flow rewired; persistence preserved
- **Implementation**: `handler.py` builds the registry BEFORE the loop and injects `verifier_registry=registry` into the ctor; all 3 builders return `AgentLoopImpl` ALONE (tuple dropped). `router.py` `loop = build_handler(...)` + `async for event in loop.run(...)` (wrapper call + import removed). `verification/correction_loop.py` **deleted** (git rm); `verification/__init__.py` drops the `run_with_verification` + `VERIFICATION_FAILED_STOP_REASON` re-exports and adds `persist_verification_event`. The per-attempt verification_log writer migrated verbatim to NEW `verification/persistence.py::persist_verification_event` (`:44`); the gate lazy-imports it from the PACKAGE.
- **Behavior**: `grep run_with_verification backend/src` → 0 (only MHist/docstring mentions); the verification_log persistence happens per-attempt in-loop; the cheap-tier judge (57.97) is preserved (`profile.cheap` unchanged).
- **Verification**: `pytest backend/tests/unit/agent_harness/verification/test_inloop_gate_persist.py` (in-loop persistence + silent-failure) + `pytest backend/tests/integration/api/test_chat_verification_smoke.py`.
- **Test fixture**: `test_inloop_gate_persist.py` patches `agent_harness.verification.persist_verification_event` (the package re-export — D-DAY2-5) + `persistence.get_session_factory`.

### 2.6 (US-1, Sprint 57.111 A3) The in-loop judge is trace-aware
- **Implementation**: `_cat10_verify_gate` (`loop.py:1649`) gains a `messages` param + builds a minimal `trace_state = LoopState(transient=TransientState(messages=...), durable=DurableState(session_id, tenant_id), version=StateVersion(...))` mirroring the Cat 4 `compact_state` build (`loop.py:2096`), then forwards `state=trace_state` to `verifier.verify` (replacing `cast(LoopState, None)` @ `:1684`). The candidate answer is appended to `messages` AFTER the gate (`:2552`) → the trace carries only PRIOR turns (no double-count). `verification/_trace.py::build_trace_block(messages, *, max_messages, char_budget)` formats the recent non-system messages (tool errors visible as `[tool] ERROR…`), bounded by env-overridable constants. `llm_judge._build_prompt(output, state)` substitutes a `{trace}` block (empty when `state is None`); `output_quality.txt` gained a `{trace}` section + a 4th "contradicts the trace" failure bullet. The `Verifier.verify` ABC widened `state: LoopState | None = None` — the 3 Cat 9 fallback judge sites (`verification/tools.py` / `cat9_mutator.py` / `cat9_fallback.py`) pass `state=None` (back-compat empty trace). + an optional `LLMJudgeVerifier(temperature=)` ctor param (benchmark uses 0.0; default 1.0 byte-identical).
- **Verification**: `pytest backend/tests/unit/agent_harness/verification/test_trace_block.py` (bounds + rendering) + `test_llm_judge_trace.py` ({trace} substitution + back-compat + temperature). Real-Azure proof = the benchmark trace_delta (§4 cheap-judge).
- **Drive-through**: Leg A (real UI + fresh A3 backend + real Azure) — chat answer "Paris." + `Verification (1) ✅` (the live gate built the trace_state + the judge verified). `loop.py` diff = 25 ins/3 del (threading only).

## 3. Cross-Category Contracts

- **No new contract / ABC / event.** The verifier registry is now **injected into `AgentLoopImpl` by construction** (Cat 1 orchestrates a Cat 10 ABC — the same cross-category pattern as `guardrail_engine` / `compactor` / `hitl_manager`; no new cross-category ABC). The `VerificationPassed` / `VerificationFailed` event contracts are **unchanged** (already carry `correction_attempt`; already wire-serialized → no codegen/`check_event_schema_sync` change).
- **Owner categories**: the gate logic = Cat 10 (Verification) living in Cat 1's `loop.py`; the durable counter = Cat 7 (State, via the checkpoint `metadata`); the correction turn visibility = Cat 12 (Observability, via the existing TAO event UI).
- **Registered at `17-cross-category-interfaces.md`**: the `VerificationResult` bubble-path row (wrapper → in-loop gate) + the `LoopCompleted` judge-token source row + a NEW `LoopCompleted` terminal origin `stop_reason="verification_failed"`. The registry is now loop-ctor-injected (was wrapper-applied); `correction_loop.py` / `run_with_verification` retired.

## 4. Open Invariants (deferred — NOT verified in this spike)

- [x] **A2 — verification-ESCALATE human-in-the-loop** ✅ SHIPPED Sprint 57.99 (feature-continuation; record = CHANGE-066 + this §4 + 17.md, NO new design note). On max-attempts AND the `chat_verification_escalate_on_max` toggle (config `__init__.py:132` → loop ctor `loop.py:429`/`:482` → MAIN real_llm wiring `handler.py:474`; default OFF = A1 byte-identical), the FAIL==max swap-point (`loop.py:2501`, guarded `... and not verification_escalated and <full HITL wiring>`) ESCALATEs via `_cat10_verification_escalate_pause()` (`loop.py:1713`) → `_emit_deferred_pause(kind="verification", verification_escalated=True)` instead of the `verification_failed` terminal. `resume()` (`loop.py:3166` `elif kind == "verification":`) APPROVE → the human OVERRIDES the verifier → `_replay_approved_output` delivers the held failed answer (terminal, no re-verify); REJECT-with-note → the note re-injects as a `user` correction Message + exactly ONE human-coached turn (`verification_attempts` forced to max + the durable `verification_escalated` flag rehydrated at `loop.py:3013` → a 2nd failure binds to the A1 terminal). No new event type (reuses `ApprovalRequested`/`ApprovalReceived`/`LLMResponded`/`LoopCompleted`; `check_event_schema_sync` green). **Reviewer UI SHIPPED Sprint 57.100** (CHANGE-067): the 57.99 backend was complete but the REJECT-with-note half was not UI-drivable (chat-v2's `HITLTurn` was tool-shaped: reject=terminate, no note input, no way to know the pause kind). 57.100 added `kind` to the `approval_requested` wire (additive field on the existing event — no new type, 22 unchanged) → `HITLTurn` branches REJECT on `kind="verification"`: reveals a coaching-note textarea (`reject-note` → `decide(id,"rejected",note)` + `resume()`), renders `kind: verification`; every other kind's reject stays byte-identical. The APPROVE half was already UI-driven (57.99); the REJECT-with-note half is now UI-drivable.
- [x] **A3 — trace-aware critique** ✅ SHIPPED Sprint 57.111 (CHANGE-078 + §2.6 + this §4). The in-loop gate threads the real `trace_state` (recent turns + tool errors) into `verifier.verify` (was `cast(LoopState, None)` @ `loop.py:1684`); the LLM judge builds a bounded `{trace}` (`verification/_trace.py::build_trace_block` + `llm_judge._build_prompt(output, state)` + `output_quality.txt` `{trace}` section); the ABC widened `state: LoopState | None` (the 3 Cat 9 fallback judge sites keep `state=None` on the back-compat empty-trace path). `loop.py` diff = 25 ins/3 del (threading only — the gate builds `trace_state` mirroring `compact_state`); wire/codegen unchanged. The cheap-judge accuracy benchmark (next item) settles the measurement half.
- [ ] **deliver-with-flag terminal** (option b): deliver the answer but flag verification failed; not chosen for A1 (would need a new event/UI flag).
- [ ] **Per-tenant verification mode / template** (Config 分層): a tenant choosing its own verification policy is workflow C (C3), not A1.
- [x] **Cheap-judge accuracy** ✅ SHIPPED Sprint 57.111 (A3; CHANGE-078). The permanent `@pytest.mark.benchmark` harness (`scripts/benchmark_judge.py` + a 28-case golden fixture `tests/fixtures/verification/judge_benchmark.yaml`, `RUN_AZURE_INTEGRATION`-gated) measured real Azure: cheap **92.86%** (stable ×2) vs strong 78.57–92.86% (Azure non-determinism on clear_pass even at temp 0) · cheap-vs-strong agreement 71–86% · **trace_delta +42.86% (stable)** — cheap-with-trace nails trace_dependent 100%, without-trace misses ~43% (the quantitative proof of US-1) · floor 70% PASS. **Verdict (design note 24 §4 settled): keep the cheap tier** — the cheap judge is accurate AND better-aligned to the lenient "default-pass, flag-only-clear-failures" contract than the strong tier (which over-flags clear_pass). The action turn remains NEVER cheap.
- [ ] **Judge-token accounting across a mid-correction pause** (D-DAY1-3): within a non-paused run the verif tokens accumulate + stamp the terminal `LoopCompleted` correctly; a rare pause-mid-correction may under-count (no `LoopCompleted` fires until resume). The attempt COUNTER is durable; the cross-pause token accounting is documented, not fixed in A1.

## 5. Rollback / Fallback

- **If this design proves wrong**: `git revert` the Sprint 57.98 commits — `correction_loop.py` is restored from git history (the wrapper was the sole rollback target; AP-11 no dual path was kept).
- **Sentinel / fallback already in place**: the `chat_verification_mode` env gate still disables verification entirely — when `!= "enabled"`, `build_real_llm_handler` injects `verifier_registry=None` → the in-loop gate is dormant → byte-identical to a non-verified run. So a production incident can be mitigated by the env flag WITHOUT a revert.
- **Estimated rollback effort**: ~1-2 hr (revert + restore the wrapper test files; the env flag is an instant kill-switch).

## 6. References

- **Sprint plan**: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-98-plan.md`
- **Sprint checklist**: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-98-checklist.md`
- **Sprint progress / retrospective**: `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-98/{progress,retrospective}.md`
- **Change record**: `claudedocs/4-changes/feature-changes/CHANGE-065-verification-in-loop.md`
- **Proposal source**: `claudedocs/1-planning/harness-deepening-proposal-20260610.md` §1 (workflow A) + §4.2 (recommended order #1)
- **Related contracts**: `17-cross-category-interfaces.md` (`VerificationResult` bubble / `LoopCompleted` judge-token + `verification_failed` terminal origin)
- **Related design notes**: `24-multi-model-profile-design.md` (the cheap-tier judge the gate routes to)
- **Related rules**: `.claude/rules/sprint-workflow.md` §Step 5.5 (spike design-note 8-pt gate) + §Common Risk Classes E (stale `--reload` backend)

## Modification History
- 2026-06-13: Sprint 57.111 A3 — §2.6 trace-aware judge + §4 A3 + cheap-judge-accuracy SHIPPED (CHANGE-078)
- 2026-06-10: Sprint 57.100 — §4 A2 reviewer UI SHIPPED (chat-v2 reject-with-note; approval_requested +kind)
- 2026-06-10: Sprint 57.99 A2 — §4 move verification-ESCALATE Open Invariant deferred → SHIPPED (file:line)
- 2026-06-10: Initial extract from Sprint 57.98 closeout (Day 4) — in-loop Cat 10 verify gate; durable attempt counter on checkpoint metadata; resume path verified for free; outer wrapper retired
