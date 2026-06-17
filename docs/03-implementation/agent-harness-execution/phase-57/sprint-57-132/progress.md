# Sprint 57.132 Progress — chat-v2 resume-path ledger persistence

[Plan](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-132-plan.md) · [Checklist](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-132-checklist.md)

---

## Day 0 — Plan-vs-Repo Verify (三-prong) + Branch — 2026-06-17

### Three-prong verify (against `main` HEAD `75b177c0`)

**Prong 1 — path verify** ✅
- `backend/src/agent_harness/orchestrator_loop/loop.py` present (resume() @3111, `_replay_approved_output` @3505, `_persist_to_ledger` @1907).
- `backend/tests/unit/agent_harness/orchestrator_loop/test_loop_pause_resume.py` present (31 tests).
- `CHANGE-099` free (highest existing = CHANGE-098).

**Prong 2 — content verify** ✅ (all GREEN — no scope shift)

| Drift ID | Finding | Implication |
|----------|---------|-------------|
| D-resume-store-wired | `build_real_llm_handler` injects `message_store=message_store` (`handler.py:544,727`); ResumeService default builder = `build_real_llm_handler` (`service.py:121-132`, zero-divergence) | ✅ the resume loop HAS a message_store → both legs' `_persist_to_ledger` is NOT a no-op; drive-through viable |
| D-asst-tool-calls | `messages_from_metadata` → `_message_from_dict` (`loop.py:254-269`); `_emit_state_checkpoint` stores `resume_messages = [_message_to_dict(m) …]` (`:3604`) — same serde 57.129 round-trips tool_calls/tool_call_id/name | ✅ the rehydrated assistant tool_use KEEPS its tool_calls → persisting it is well-formed (no dangling bare tool) |
| D-persist-sig | `_persist_to_ledger(msgs, *, turn_num)` = best-effort `self._message_store.append(msgs, turn_num)`; guards `store is not None and msgs` (`:1907-1917`) | ✅ both new call sites are no-op-safe |
| D-replay-no-persist | `_replay_approved_output` (`:3505-3556`) re-emits LLMResponded+Thinking+LoopCompleted, NO `_persist_to_ledger` today | ✅ Leg-2 gap confirmed real |

**Prong 3 — schema verify**: N/A — no new DB table / migration / ORM column (reuses the existing `messages` ledger + `DBMessageStore`).

**Baselines (re-verified on `75b177c0`)**: run_all **10/10** green (`check_event_schema_sync` OK → wire 25 in-sync) · pause_resume test file **31 tests** (→ +3 = 34) · mockup/Vitest untouched (pure backend). mypy + full pytest captured at Day-2 gate.
- Note (tooling): `scripts/lint/run_all.py` MUST be invoked from the **repo root** (a stale `cwd=backend/` made 9/10 falsely FAIL @0.05s — a cwd artifact, not real violations; re-run from root → 10/10).

**Go/no-go**: both legs feasible (store wired + serde keeps tool_calls); 0% scope shift → **GO**.

### Branch
- `git checkout -b feature/sprint-57-132-chatv2-resume-ledger-persist` from `main` `75b177c0` ✅.

---

## Day 1-2 — Code (both legs) + gate — 2026-06-17

### Leg 1 — resume() tool round-trip persist (US-1)
- `loop.py` resume() tool-kind APPROVED branch (after the `tool` result append, before the `_run_turns` drive): backward-scan `_resume_asst_idx` = last `role=="assistant"`; `if _resume_asst_idx is not None: await self._persist_to_ledger(messages[_resume_asst_idx:], turn_num=turn_count)`. Mirrors the 57.129 atomic batch contract; reached ONLY on APPROVED+exec (REJECTED/undecided return earlier → no dangling tool_use).
- `_persist_to_ledger` docstring generalized ("+ the resume() tool-approval + held-answer replay paths").

### Leg 2 — held-answer replay persist (US-2)
- `loop.py` `_replay_approved_output` (after `yield Thinking`, before `yield LoopCompleted`): `if answer_text: await self._persist_to_ledger([Message(role="assistant", content=answer_text)], turn_num=turn_count)`. Covers BOTH output-kind (57.93) + verification-kind (57.99 A2) APPROVE. Docstring updated.

### Tests (`test_loop_pause_resume.py`, +4)
- `RecordingMessageStore` (records each append() batch) + `message_store` param on `_build_resume_loop` (default None = baseline).
- `test_resume_tool_roundtrip_persisted_atomically` (one atomic `[assistant, tool]` batch; assistant keeps tool_calls) · `test_resume_tool_roundtrip_no_store_is_noop` · `test_resume_output_approved_persists_held_answer` · `test_resume_output_rejected_persists_nothing`.

### Gate (all GREEN)
- mypy `src` **0/372** · run_all **10/10** (wire 25 in-sync · LLM-SDK-leak clean · check_event_schema_sync OK) · backend pytest **2731 passed / 5 skipped** (baseline 2727 +4) · pause_resume file 35 (31+4) · rehydration regression 6/6 · black/isort/flake8 clean.
- Scope confirmed PURE backend: `git status --short` = only `loop.py` + `test_loop_pause_resume.py` modified. Vitest / mockup / wire / codegen / migration / frontend UNTOUCHED.
- E501 caught + fixed: the new test header `Last Modified` line (107>100) trimmed.

---

## Day 3 — Drive-through (real UI + real backend + real Azure gpt-5.2) — 2026-06-17

### Clean restart (Risk Class E)
- Old :8000 backend = PID 14736, started 6/16 23:02 (OLD code, no `--reload` → single deterministic process, no spawn-worker orphans). Killed it → started fresh backend (my new code) → **PID 54504, started 6/17 10:47**, "startup complete" + "pricing loader wired" (cost ledger live), sole :8000 owner. Frontend Vite :3007 untouched (backend-only change).

### Setup
- dev-login as **dan@acme.com / acme-prod (admin)**. Tenant id `09eb1b62-9fd3-439a-8229-1c923cc667e9`.
- HITL policy was MEDIUM=auto (57.129 leftover → would auto-approve python_sandbox). PUT `/api/v1/admin/tenants/{id}/hitl-policies` `{auto_approve_max_risk: LOW, require_approval_min_risk: MEDIUM}` → MEDIUM=always_ask → python_sandbox (MEDIUM) ESCALATEs → deferred pause. (Policy left as require=MEDIUM; noted for future drive-throughs.)

### Leg 1 — tool round-trip persist — ✅ FULL DRIVE-THROUGH PASS
Session `02fa6bfb-4061-4b3a-87aa-8e4ef7f90a76`:
1. Sent "Run `random.randint(100000,999999)` in python_sandbox, reply ONLY EVEN/ODD, don't state the number." → python_sandbox tool call → **HITL approval card** (severity MEDIUM, policy always_ask, approval_id `b43f986b…`). Loop paused `awaiting_approval`.
2. Clicked **Approve & continue** (real UI button) → `resume()` → python_sandbox executed (stdout `1` = n%2 → ODD) → continuation → answer **"ODD"** + verification_passed (llm_judge 0.99) → end_turn.
3. **DB ledger PROOF** (`artifacts/verify_ledger.py 02fa6bfb…`): **4 rows** — seq=1 user / **seq=2 assistant tool_calls=python_sandbox** / **seq=3 tool stdout="1\r\n"…duration_seconds:0.031** / seq=4 assistant "ODD". Seq 2-3 = the paused tool's round-trip **persisted AT RESUME** (the Leg-1 fix). Pre-fix this resumed turn would hold only seq 1 + 4.
4. **End-to-end rehydration PROOF**: follow-up "What exact value did the tool's `duration_seconds` field have?" (POST sends only {message, session_id}, no history) → answer **"0.031"** — un-deducible from "ODD"; recoverable ONLY from the rehydrated tool result (seq 3). prompt_built `messages_count` 4→5→**8** (the round-trip rehydrated into the follow-up's prompt). Ledger grew to seq 5 (user) + seq 6 (assistant "0.031").
- Screenshot: `artifacts/drivethrough-57132-leg1-resume-ledger-PASS.jpeg` (+ `.playwright-mcp/`).
- **Observed == intended**: pause → approve → resume executes the tool → answer → the paused round-trip is in the ledger → a follow-up rehydrates it. ✅

### Leg 2 — held-answer replay persist — unit + gate verified (NOT UI drive-through; honest)
- Attempted a real-LLM output-escalate trigger (default phrase `confidential`): asked the LLM to reply with a sentence containing "confidential". The turn produced **no answer block / no new hitl_pause checkpoint / no ledger row** (state_snapshots = only post_llm; ledger unchanged at 6 rows) → the **output-escalate did not fire** (the real LLM's answer did not deterministically contain the matched phrase, likely also an Azure content-filter early-exit — the 57.129 false-alarm class). The output-escalate pause depends on non-deterministic real-LLM output, so a clean UI drive-through could not be staged this run.
- **Leg-2 IS verified** at: (a) **unit** — `test_resume_output_approved_persists_held_answer` + `test_resume_output_rejected_persists_nothing` exercise the REAL `resume()` output-kind path → `_replay_approved_output` → `_persist_to_ledger` (approved persists the held answer; rejected persists nothing); (b) **composition** — the `_persist_to_ledger` → `DBMessageStore.append` → DB primitive is RUNTIME-PROVEN by Leg-1's full drive-through (same call site family). Leg-2 is a 4-line mirror of that proven primitive.
- **Honest label**: Leg-2 = unit + gate verified, NOT UI-drive-through (per the Drive-Through Acceptance constraint — not claimed as driven). Carryover: a deterministic output/verification-escalate drive-through (needs a controllable escalate phrase / a verification-fail fixture) — `AD-ChatV2-Resume-Replay-Drive-Through`.
