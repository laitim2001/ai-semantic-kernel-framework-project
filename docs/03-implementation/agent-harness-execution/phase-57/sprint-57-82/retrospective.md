# Sprint 57.82 Retrospective — B-8 leg-1: verification judge token → cost ledger + quota

**Sprint**: 57.82
**Closed**: 2026-06-05
**Branch**: `feature/sprint-57-82-verification-cost-ledger`
**Closes**: B-8 **blocker A** / `AD-Cat10-Judge-Cost-Ledger` (billing leg of the 完整 B-8 epic)

---

## Q1. Goal achieved?

✅ Yes. When verification is enabled, the judge LLM call's tokens are now recorded in the cost ledger (as a distinct `_verification` sub_type, separate from the loop entry) and counted against tenant quota:
- `VerificationResult` +token fields; `LLMJudgeVerifier` captures `response.usage` + model.
- `LoopCompleted` +verification token fields; the correction-loop wrapper accumulates judge tokens across all verifiers + correction attempts and stamps all 3 yield points.
- `record_llm_call` +`sub_type_suffix`; router records a distinct judge entry + adds judge tokens to quota `actual_tokens`.
- Default `chat_verification_mode` UNCHANGED (`disabled`) — leg 1 is a correctness fix that activates only on the enabled path.
- Gates: mypy src/ 0 (332) / pytest 2147 (+10) / run_all 10/10.

## Q2. Estimate accuracy

- Plan: bottom-up ~5.3 hr → class-calibrated commit ~4.2 hr (`medium-backend` 0.80, `agent_factor` 1.0 parent-direct).
- Actual: ~3.5 hr. Day-0 (analysis re-verify + Explore + 2 AskUserQuestion design gates) ~1 hr; Day 1-2 code (4+3 files, cross-category) ~1.5 hr; Day 3 tests (10 new across 3 files) ~0.7 hr; Day 4 sweep + closeout ~0.3 hr.
- Ratio actual/committed ~0.83. `medium-backend` 0.80 held cleanly for a parent-direct sprint. **NOT agent-delegated** → the agent-delegated wall-clock caveat does not apply (clean human-cadence data point).
- `medium-backend` 0.80 data point: ~0.83 in-band lower edge. KEEP per 3-sprint window rule.

## Q3. What went well

- **2 design gates before code paid off**: AskUserQuestion (1) scope = 完整 B-8 (not "flip the flag blindly" — the analysis said don't); (2) judge-accounting design = Option 1 (LoopCompleted +separate verification fields → distinct sub_type). Plan was written once, no rewrite. Karpathy "present multiple interpretations, don't privately pick one" applied to a real architecture fork.
- **Day-0 corrected a stale-analysis + a subagent suggestion**: the 8-sprint-old analysis's 3 blockers all still held (re-verified). The Explore agent suggested "call `metrics_acc.on_event` in loop.py" — but verification runs in the WRAPPER after LoopCompleted, when the loop accumulator is frozen. Caught it at Day-0; the wrapper owns judge-token accumulation instead.
- **Drift D3 (sse) caught a consistency trap**: plan §3.4 said "add the fields to the LoopCompleted SSE serializer", but Day-2 read showed the serializer already omits the loop's own input/output_tokens — billing is server-side (router reads the event object). Kept verification tokens server-side too; `check_event_schema_sync` stayed green (no wire change → no frontend codegen needed). Recorded the drift instead of silently following the plan.
- **3 wrapper yield points all covered**: the accumulate-across-attempts logic + stamping non-end_turn(0)/all-pass/exhausted was the one tricky bit; test (a)-(e) pin each path (incl. the 300/30 exhausted sum across 3 attempts).
- **Scope discipline (epic split)**: leg 1 = blocker A only (pure billing, mock-verifiable); blocker B (general judge template) + C (real-LLM e2e) bundled into leg 2 because B's false-positive evaluation intrinsically needs real-LLM. Did not flip the default.

## Q4. Lessons

- **A stale analysis doc accelerates Day-0 but doesn't replace it** (same lesson as 57.81): re-running Prong 1+2 against current main confirmed the 3 blockers + surfaced that verification runs post-LoopCompleted in the wrapper (the analysis didn't line-verify the wrapper's accumulator timing).
- **"Add the field to the serializer" is not automatic**: check what sibling fields actually do first — the loop's own billing tokens were already server-side-only, so the new field should be too. Following the plan literally would have been an inconsistent, unnecessary wire change.

## Q5. Improvements next sprint

- Leg 2 (57.83) needs real Azure for blocker C — confirm Azure secrets are still configured (real-LLM went live 57.79) before drafting, and budget for a real-LLM e2e that provokes the judge (enabled mode, end_turn output) to measure false-positive rate / latency / per-chat cost. That measurement is the gate for the general-judge-template design (blocker B) and the flag flip.

## Q6. Carryover

- **B-8 leg 2 (57.83)**: blocker B (design a general final-output judge template, replacing the Cat 9-fitted `safety_review` default) + blocker C (real-LLM e2e: false-positive / latency / cost) + flip `chat_verification_mode` to `enabled`. B+C bundled (B's FP eval needs C's real-LLM).
- **Per-verifier cost attribution**: leg 1 aggregates all judge tokens into one `_verification` sub_type; a per-verifier breakdown is deferred (out of scope).
- **Correction full-loop re-run cost** (analysis §2: worst case 3× loop): the re-run loop tokens already flow through normal LoopCompleted accounting; not changed here.
- **C-15 DevOps/data-platform billing** — the bundle's remaining leg (cost_ledger 雙扣 risk); separate sprint.

## Q7. Risks

- Low. Backend + docs only; the new judge ledger entry + quota addition are best-effort (try/except, failure isolated from the SSE stream — mirrors the existing loop record). Default path (`disabled`) untouched — verification token fields stay 0 → no extra ledger entry, quota unchanged (asserted by test e + non-end_turn d). No DB/schema change (sub_type is a string column). LLM neutrality preserved (`check_llm_sdk_leak` green — capture uses neutral `TokenUsage`). The correctness claim is mock-proven; real-LLM judge billing (real `TokenUsage` from Azure) lands in leg 2's e2e. Unknown-judge-model → $0 row (observable anomaly, FIX-022 caveat), not a crash.

---

## Design Note Extract

NO — wiring + contract extension of an existing Cat 10 component (LLMJudgeVerifier / correction_loop, Sprint 54.1); 17.md §1.1 + §4.1 updated in-place; no new contract / no new domain spike.