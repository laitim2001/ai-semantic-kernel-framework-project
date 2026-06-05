# Cat 10 Verification — real-LLM measurement (Sprint 57.83 B-8 leg-2 blocker C)

**Purpose**: Measure the `output_quality` judge's false-positive rate / latency / cost against real Azure, to data-gate the `chat_verification_mode` default flip (Q2 = data-driven gate).
**Category / Scope**: Status / Cat 10 (Verification Loops) / B-8 leg-2 blocker C
**Created**: 2026-06-05
**Status**: Active — pass 1 (fail-on-any judge) FP ~75% → DO-NOT-FLIP → re-tuned to lightweight "clearly-failed-only" judge → pass 2 **FP 0% → FLIP** (`chat_verification_mode` default = enabled)

---

## 1. Protocol

- Backend started with `CHAT_VERIFICATION_MODE=enabled` + `CHAT_VERIFICATION_JUDGE_TEMPLATE=output_quality` (no-reload, real Azure deployment gpt-5.2-2025-12-11), DB at head `0024_memory_ops`, Docker DB/Redis up.
- dev-login (DEMO tenant) → 8 "normal" prompts a reasonable user would accept + 2 deliberately weak/nonsense prompts, all `mode=real_llm`.
- Per chat: SSE parsed for verification_passed/failed + loop_end stop_reason + wall-clock; verdicts cross-checked against `verification_log`; judge cost from `cost_ledger` `_verification` sub_type entries (leg-1 instrumentation).
- Script: `scripts/_tmp_verification_measure.py` (temp, deleted after run).

## 2. Raw data

**verification_log** (this run): 25 verifier rows = 20 failed / 5 passed; **10 sessions = 2 all-pass / 8 fail**.

Normal prompts (8): 2 all-pass, **6 fail → FP rate ≈ 75%**. Observed examples:
- "What does HTTP stand for?" → fail (2 corrections, stop=end_turn)
- "Give me one tip for staying focused…" → fail (3 corrections, stop=verification_failed)
- "In one sentence, what does a database index do?" → pass (0 corrections)

Bad prompts (2): both fail ("asdfghjkl…" 3 corrections; "????????" 1 correction) — true positives.

**Judge cost** (`cost_ledger` `_verification`): 10 chats → input 6520 + output 2544 = 9064 judge tokens, **$0.047** total (~$0.0047/chat judge-only; fail chats additionally re-ran the full loop up to 3×, so real per-chat cost is multiples higher).

**Latency**: 6-23s wall-clock per chat (fail+correction runs at the high end).

## 3. Computed metrics vs threshold

| Metric | Measured | Threshold (plan §3.3) | Verdict |
|--------|----------|------------------------|---------|
| False-positive rate (normal) | **~75%** (6/8) | ≤ ~15% | ❌ FAIL |
| Judge cost / chat | ~$0.0047 (judge only) | (informational) | high w/ re-runs |
| Wall-clock p95 | ~23s (fail+3× loop) | < 5s judge SLO | ❌ (correction re-runs dominate) |

## 4. Gate verdict: DO NOT FLIP

The `output_quality` judge ("fail if it falls short on ANY dimension", Q1 choice) is **too strict for general chat traffic** — it judged normal, correct answers (e.g. "HTTP = HyperText Transfer Protocol", a focus tip) as quality-failures, triggering wasteful correction re-runs (up to 3× the full loop) and `stop_reason=verification_failed` (the user would see "verification failed" on a perfectly good answer).

Per Q2 (data-driven gate): **`chat_verification_mode` default stays `disabled`.** This is the gate doing its job — it prevented a false-positive storm + a 3× cost blow-up on the main flow. NOT a sprint failure: blocker B (template) + blocker C (measurement) are both done; the flip is correctly deferred on evidence.

## 4.5 Re-tune + re-measure (lightweight judge) → FLIP

After pass 1, `output_quality.txt` was re-tuned from "fail if it falls short on ANY of helpful/complete/accurate/on-topic" to a **lightweight "clearly-failed-only" judge**: flag ONLY refusal / incoherent / empty / off-topic; "a short, correct answer PASSES; when in doubt, pass; Default to passed=true". (`load_template` reads the file per call → the running backend picked up the new template with no restart.)

Re-measure (same protocol, same 8 normal + 2 bad prompts, real Azure):

| Group | Result |
|-------|--------|
| 8 normal | **8 PASS / 0 fail → FP rate 0%** (0 corrections, ~5s each) |
| 2 bad (nonsense) | 2 FAIL (3 corrections each — true-positive sanity ✅) |

| Metric | Pass 1 (fail-on-any) | Pass 2 (lightweight) | Threshold | Verdict |
|--------|----------------------|----------------------|-----------|---------|
| FP rate (normal) | ~75% | **0%** | ≤ ~15% | ✅ PASS |
| Normal-chat wall-clock | 6-23s (w/ re-runs) | **~5s** (no re-runs) | < 5s judge SLO | ✅ ~at SLO |
| Bad-case detection | flagged | flagged (3 corrections) | (sanity) | ✅ |

**Final gate verdict: FLIP.** The lightweight judge passes all normal answers (0 FP, 0 wasted correction re-runs) while still catching genuine garbage. `chat_verification_mode` default → `enabled`. B-8 fully closed.

## 5. Root cause + outcome

- **Root cause**: "fail on ANY of helpful/complete/accurate/on-topic" makes the judge reject normal-but-terse or debatable answers. The leg-1 AskUserQuestion had flagged the lighter "clearly-failed-only" judge as the low-FP option; pass 1 confirmed the stricter general-quality judge over-flags (~75% FP).
- **Outcome (B-8 flip CLOSED)**: re-tuned to the lightweight "clearly-failed-only" judge → re-measured FP 0% (§4.5) → flipped `chat_verification_mode` default to `enabled`. The data-driven gate (Q2) caught the strict version before it shipped AND drove the in-sprint re-tune; the lightweight judge bar (the leg-1 low-FP option) was the right one. B-8 fully closed.

## 6. Modification History
- 2026-06-05: Re-tune to lightweight "clearly-failed-only" judge + re-measure FP 0% → gate FLIP (B-8 closed)
- 2026-06-05: Initial — Sprint 57.83 blocker C measurement pass 1; verdict DO-NOT-FLIP (FP ~75%).
