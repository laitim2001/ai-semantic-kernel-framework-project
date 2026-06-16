# CHANGE-095: chat-v2 resume transcript persistence (persist post-resume SSE events to `message_events`)

**Date**: 2026-06-16
**Sprint**: 57.128
**Scope**: api/v1/chat (the `message_events` SSE-replay ledger; sibling to the 57.125/126 send-path writer)
**AD closed**: `AD-ChatV2-Resume-Transcript-Persistence` (the pre-existing 57.125 gap re-flagged by the 57.126/127 carryovers)

## Problem

Sprint 57.125/126 built the `message_events` SSE-frame ledger + the frontend replay (click a session → `GET /sessions/{id}/events` → replay through `mergeEvent`). But the persistence observer (`_persist_main_event`) was wired ONLY into the normal-send generator `_stream_loop_events`. The HITL **resume** path has its own generator `_stream_resume_events` (a "thin mirror") that drives `loop.resume()` and yields SSE bytes but **never persisted them**. So a session that paused on a HITL approval and was later resumed had its post-resume turns missing from the replay ledger — clicking a paused-then-resumed session replayed only up to the pause, missing the post-approval answer + continuation.

## Root Cause (grep-confirmed on `main` `5ddc11cc`)

| Layer | Reality | Anchor |
|-------|---------|--------|
| Send path persists every event | `_stream_loop_events`: seeds `main_seq = _max_main_seq(...)`, persists the `user_message` row, then `_persist_main_event(payload, ...)` before each yield | `router.py:706-716` / `:768-776` |
| Resume generator omits persist | `_stream_resume_events` ("thin mirror"): `loop.resume()` → `serialize_loop_event` → `yield` — **ZERO `_persist_main_event` calls** | `router.py:1201-1223` |
| Resume endpoint had the deps | `resume_chat` (`POST /{session_id}/resume`) has `db` / `current_tenant` / `session_id` in scope but did not pass them to the generator | `router.py:1310-1363` |
| `messages` Cat-3 ledger already OK on resume | `loop.resume()` → shared `_run_turns` end_turn → `_persist_to_ledger` (57.127) → the `messages` table IS written on resume | `loop.py:2689/2721` |

The `messages` Cat-3 ledger (57.127, live multi-turn) already covered resume; only the `message_events` SSE-replay ledger (57.125/126) was missing on the resume path.

## Solution (minimal scope — user-picked via AskUserQuestion 2026-06-16)

Mirror the send-path persistence into `_stream_resume_events`. Pure backend; no new event type / wire / codegen / frontend / migration.

- **`router.py` `_stream_resume_events`** (EDIT): added kw-only params `tenant_id: UUID`, `session_id: UUID`, `db: AsyncSession | None = None` (mirror the send-path types; only `resume_chat` calls it). Seeds `main_seq = await _max_main_seq(db, tenant_id, session_id)` (arg order verified Day-0 — the 2 Explore agents disagreed; the send path settled it), then inside the `loop.resume()` loop — AFTER the `serialize_loop_event` `NotImplementedError` / `payload is None` skips and BEFORE the `yield` — `if main_transcript_on: main_seq += 1; await _persist_main_event(payload, db=db, tenant_id=tenant_id, session_id=session_id, sequence_num=main_seq)`. NO `user_message` row (resume has no new prompt). Best-effort (the helper's SAVEPOINT swallows failures → never breaks the live stream).
- **`router.py` `resume_chat`** (EDIT): threads `tenant_id=current_tenant, session_id=session_id, db=db` into the `_stream_resume_events(...)` call. Public route signature unchanged.

### Why minimal scope

The fuller option (persist the human approve/reject DECISION as its own replay event) was rejected by the user — it would need a new/wired event type → codegen + a frontend `mergeEvent` case + a wire-count bump. The decision is already auditable in the `approvals` + audit-log tables. (Bonus: the existing `approval_received` SSE event the resume now persists already surfaces the APPROVED decision inline in replay — no new event type needed.)

### Seq continuity (not double-persist)

`_max_main_seq` returns the session's current MAX `sequence_num` (the pre-pause events persisted by the original send). Seeding from it makes the post-resume events continue monotonically AFTER the pre-pause frames — the replay sorts by `sequence_num` and folds them in order. The resume persists ONLY what `loop.resume()` yields (post-resume events); no overlap with the pre-pause rows.

## Verification

- **Gates**: mypy `src` **0/372** · run_all **10/10** (wire **24**, LLM-SDK-leak clean) · full pytest **2724 passed / 5 skipped** (+4) · Vitest 904 / mockup 51 UNCHANGED (no FE edit). `black`/`isort`/`flake8` clean. No migration (`message_events_default` partition exists, `0028`).
- **Test**: `tests/integration/api/test_chat_resume_persistence.py` (4) — drives the REAL `_stream_resume_events` with a fake resuming loop: post-resume events persist (no `user_message` row; Thinking skipped) · seq continues past a pre-seeded pre-pause MAX (no collision) · gate-off no-op · cross-tenant invisible (鐵律).
- **Drive-through PASS** (MANDATORY — real chat-v2 UI + clean-restart backend + real Azure gpt-5.2, session `b78cb63d`, acme-prod HITL policy require=MEDIUM):
  - Send "use python_sandbox to compute 6 times 7" → `python_sandbox` (MEDIUM) escalates → loop pauses (HITL approval card).
  - Approve & continue → decide + resume → "42" renders live + verification passed.
  - Reload (fresh store) → click the session → the replay shows the COMPLETE conversation incl. the approval card ("Decision: APPROVED") + "42" + verification (before this it stopped at the pause).
  - `GET /sessions/b78cb63d/events` → 40 events, seq 1→40 monotonic; post-resume rows (seq 20-40: `loop_start` → `approval_received` → `tool_call_request` → `tool_call_result`=42 → … → `verification_passed` → `loop_end`).
  - Evidence: `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-128/artifacts/sprint-57-128-drivethrough-{1-paused,2-resumed,3-replay}.png` + `backend-drivethrough.log`.

## Impact

Backend-only. A HITL-paused-then-resumed chat-v2 session now replays its full post-approval continuation. The `messages` Cat-3 ledger, the send path, and the live stream are unaffected (the resume already persisted to `messages` and streamed live; only its `message_events` write was missing). The approve/reject decision remains auditable in `approvals` + audit-log.
