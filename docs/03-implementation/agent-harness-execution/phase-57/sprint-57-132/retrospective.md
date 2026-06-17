# Sprint 57.132 Retrospective — chat-v2 resume-path ledger persistence

[Plan](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-132-plan.md) · [Checklist](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-132-checklist.md) · [Progress](./progress.md) · CHANGE-099

## Q1 — What shipped?
Closed `AD-ChatV2-Resume-Tool-RoundTrips` (57.129 carryover) + the sibling held-answer gap, comprehensive scope (user pick). Two `loop.py` persist call sites: **Leg 1** persists a paused-then-approved tool's `[assistant tool_use, *tool results]` round-trip in `resume()`; **Leg 2** persists the delivered held answer in `_replay_approved_output`. PURE backend (1 src + 1 test edit); +4 unit tests. Leg-1 fully drive-through proven (UI + real Azure + DB ledger); Leg-2 unit + composition verified (honest: not UI-driven).

## Q2 — Estimate accuracy / calibration
- NEW scope class **`chatv2-resume-ledger-persist-wiring`** — between 57.128's `chatv2-resume-persistence-wiring` 0.55 (1 leg, message_events) and 57.129's `chatv2-ledger-tool-roundtrips-wiring` 0.85.
- Bottom-up ~5.0 hr → committed ~3.5 hr (mult **0.70**), parent-direct (agent_factor 1.0).
- Actual ~5-5.5 hr → ratio **~1.4-1.6 OVER**. The CODE+tests were small/on-budget (~10 lines, ~1.5 hr); the over-run was the **drive-through**: HITL-policy setup + the full Leg-1 pause→approve→resume→follow-up→2×DB-verify + the **Leg-2 output-escalate dead-end** (a real-LLM trigger that didn't fire + the FE/backend investigation to confirm why).
- **Re-point 0.70 → 0.85** (1st data point). Same "ceremony-not-code-accelerated" insight as 57.120/122/123/126/129: a tiny-code, full-ceremony, parent-direct sprint WITH a mandatory HITL drive-through lands ~0.85-1.0, NOT the 0.55-0.70 pure-wiring band — the HITL drive-through staging + DB verification is the fixed-cost driver. If a 2nd lands < 0.7 at 0.85, lower again.

## Q3 — What went well?
- Day-0 三-prong fully de-risked both legs BEFORE code: D-resume-store-wired (the persist is not a no-op) + D-asst-tool-calls (serde keeps tool_calls → no dangling bare tool). Zero mid-sprint surprises in the code.
- The fix mirrored the proven 57.129 batch contract → surgical, dangling-free, atomic.
- Leg-1 drive-through gave an un-deducible end-to-end proof ("0.031" from `duration_seconds`), far stronger than an EVEN/ODD or n%2 follow-up would have been.

## Q4 — What was hard / what to improve?
- **Leg-2's output-escalate is non-deterministic to drive via real LLM**: it needs the answer to contain the default `confidential` phrase AND survive Azure content filters. My attempt produced no pause / no ledger row (content-filter early-exit, the 57.129 false-alarm class). Lesson: held-answer (output/verification) legs need a **deterministic escalate fixture** (a controllable phrase via a HarnessPolicy admin surface, or a verification-fail fixture) to be UI-drive-through-able — there is currently no admin endpoint for `escalate_output_phrases`.
- Bash `grep` returned empty for a constant that clearly exists (`CHAT_HITL_ESCALATE_OUTPUT_PHRASES`) — the Sprint 57.70 token-corruption class; re-ran via the **Grep tool** (worked). Reinforces: when Bash grep looks wrong, use the dedicated Grep tool.
- `scripts/lint/run_all.py` must run from the repo root (a stale `cwd=backend/` made 9/10 falsely FAIL @0.05s — a cwd artifact, re-run from root → 10/10).

## Q5 — Anti-pattern self-check
- AP-2 (no orphan): both call sites reachable from the main resume flow; drive-through proves Leg-1 reaches the DB. ✅
- AP-3 (no scatter): both edits in `loop.py` (Cat 1) + tests in the existing pause_resume suite. ✅
- AP-4 (no Potemkin): Leg-1 is DB-proven end-to-end; Leg-2 is unit-proven on the real path (not a stub). Honest labeling of Leg-2's non-UI-driven status (no false "verified"). ✅
- AP-6 (no premature abstraction): reused `_persist_to_ledger` / `DBMessageStore` / `message_serde` — no new ABC. ✅
- AP-8 (PromptBuilder): N/A (no prompt assembly). ✅
- AP-11 (no version suffix): none. ✅
- v2 lints 10/10.

## Q6 — Drive-through honesty (約束)
- Leg-1 (PRIMARY user-facing path = literal AD): FULL drive-through PASS (UI + backend + real LLM + DB). ✅
- Leg-2 (niche advanced path): labeled "unit + gate verified, NOT UI drive-through" — NOT claimed driven. Carryover logged. Faithful to the Drive-Through Acceptance constraint.

## Q7 — Carryover
- **NEW** `AD-ChatV2-Resume-Replay-Drive-Through` (🟡) — a deterministic output/verification-escalate drive-through for Leg-2 (needs a controllable escalate phrase admin surface OR a verification-fail fixture; the real-LLM `confidential` trigger is non-deterministic + content-filter-prone).
- Pre-existing: `AD-Billing-Outbox-Drain-Test-Flake` (did NOT surface; backend change but unrelated).
- Deferred infra (unchanged): `message_events`/`messages` consolidation; `turn_num` cross-send counter; pg_partman.

## Design Note Extract
N/A — not a spike sprint (continuation of the 57.127/129 `messages` ledger; no new contract). NO design note.
