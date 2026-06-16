# Sprint 57.128 Retrospective — chat-v2 resume transcript persistence

**Closed**: 2026-06-16
**Branch**: `feature/sprint-57-128-chatv2-resume-transcript-persistence` (from `main` `5ddc11cc`)
**AD closed**: `AD-ChatV2-Resume-Transcript-Persistence`
**Class**: `chatv2-resume-persistence-wiring` 0.55 (NEW, 1st data point) · parent-direct · `agent_factor` 1.0

---

## Q1 — What shipped?

The HITL resume path now persists its post-resume SSE events to the `message_events` ledger, so a paused-then-resumed chat-v2 session's replay is complete (shows the post-approval answer + continuation, not just up to the pause). One file edit: `_stream_resume_events` mirrors the send-path `_persist_main_event` (seq seeded from `_max_main_seq`, best-effort, gate-respecting, no `user_message` row); `resume_chat` threads `db`/`tenant_id`/`session_id` in. Pure backend; no new event type / wire / codegen / frontend / migration. The `messages` Cat-3 ledger already covered resume (untouched).

**Files**: 1 EDIT (`api/v1/chat/router.py`) + 1 NEW test + CHANGE-095.

## Q2 — Calibration

- **Class**: `chatv2-resume-persistence-wiring` **0.55** (NEW). Closest: `subagent-sse-relay-wiring` 0.55 (backend SSE-relay composition wiring); lighter than `chatv2-transcript-persistence-spike` 0.60 (which BUILT the observer). Pure mirror-wiring of an EXISTING observer into a sibling generator.
- **Agent-delegated: no** (parent-direct). The seq-seed arg-order verify, the skip/None parity, and the best-effort SAVEPOINT mirroring are correctness-critical; the HITL drive-through required hand-driving a pause→approve→resume→reload. `agent_factor` 1.0 → 3-segment.
- **Bottom-up est ~5.5 hr → class-calibrated commit ~3.0 hr (mult 0.55)**.
- **Actual ~3.4 hr** → ratio vs committed **~1.13 (near band-top, IN band)**. The CODE was tiny (~12 lines + param threading, ~0.5 hr) but the **HITL drive-through dominated** (~1.5 hr: 3 Explore sweeps incl. the HITL recipe + the admin policy setup + the pause trigger + approve + reload + replay + screenshots) — exactly the cost driver the plan §7 flagged. Day-0 三-prong + the test were ~1.0 hr; closeout ~0.5 hr.
- **Verdict**: KEEP 0.55 (1st data point, ~1.13 IN band). The HITL drive-through setup is the variance source — if a 2nd `chatv2-resume-persistence-wiring` (or any HITL-drive-through sprint) lands > 1.20, re-point toward 0.65.

## Q3 — What went well?

1. **Day-0 caught the arg-order disagreement** — the 2 Explore agents gave conflicting `_max_main_seq` arg orders (`(db, tenant_id, session_id)` vs `(db, session_id, tenant_id)`); Day-0 Prong-2 grep settled it from the send-path call site (`router.py:707`) BEFORE coding. A wrong order would have silently scrambled the seq seed (the seq-continuity test would have caught it, but at higher cost).
2. **A perfect sibling test harness existed** — `test_main_transcript_persist.py` (57.125) gave the exact fake-loop + DB-assertion pattern; the new test was a direct mirror (fake `resume()` instead of `run()`).
3. **The fix matched the prior author's intent** — `_stream_loop_events` already had a comment (`router.py:761`) anticipating "the resume mirror" → the field stays null. The seam was designed to be mirrored.
4. **The drive-through was decisive + layered** — `/events` returning 40 events (seq 1→40, post-resume 20-40) is a clean persistence proof; the reload-replay showing 42 + the APPROVED card is the user-facing proof. The minimal scope even surfaced the approval decision in replay (the existing `approval_received` event), a free win.

## Q4 — What to improve?

1. **HITL drive-throughs are expensive to set up** — triggering a real pause needs an admin policy PUT + an escalating tool the LLM will call (`python_sandbox`). The 3rd Explore sweep (the HITL recipe) was necessary but added wall-clock. Lesson: for HITL-touching sprints, budget the drive-through setup explicitly (the plan did flag it — calibration confirmed it was the cost driver).
2. **Background full-pytest + concurrent agent crashed pytest-capture** — running the full suite in the background while an Explore agent ran caused a `_pytest/capture.py` "I/O operation on closed file" crash (188 spurious "errors"). Lesson: run the full suite foreground, or don't spawn agents that touch the terminal concurrently.

## Q5 — Anti-pattern self-check (0 violations)

- **AP-2** (no side-track): the resume persist is on the 主流量, wired from `resume_chat`, exercised by the drive-through. ✅
- **AP-3** (one home): reuses the EXISTING `_persist_main_event` writer — no duplicate persistence logic. ✅
- **AP-4** (no Potemkin): real resume replay proven LIVE (40 events, reload-replay shows 42). ✅
- **AP-6** (no speculation): no new event type / helper — minimal mirror of the existing observer. ✅
- **AP-8** (no bare persistence): reuses `_persist_main_event` + `_max_main_seq`. ✅
- **AP-11** (no version suffix): no `_v2`. ✅

## Q6 — Drive-through (MANDATORY — PASS)

Real chat-v2 UI + clean-restart backend (PID 42600) + real Azure gpt-5.2, session `b78cb63d`, acme-prod HITL policy require=MEDIUM:
- "use python_sandbox to compute 6 times 7" → `python_sandbox` escalates → HITL pause.
- Approve & continue → resume → "42" live + verification passed.
- Reload → click session → COMPLETE replay (user prompt → python_sandbox → "Decision: APPROVED" card → 42 → verification).
- `/sessions/b78cb63d/events` → 40 events, seq 1→40; post-resume seq 20-40 (`approval_received` → `tool_call_result`=42 → `verification_passed` → `loop_end`). 3 screenshots in `artifacts/`.

## Q7 — Carryover (→ next-phase-candidates.md)

- No NEW carryover from this sprint.
- Still open (carried): `AD-ChatV2-Ledger-Tool-RoundTrips` (57.127 — `messages` ledger intra-turn tool round-trips); `AD-Billing-Outbox-Drain-Test-Flake` (intermittent Risk Class C billing flake, pre-existing); the deferred infra (canonical-ledger consolidation, pg_partman).
