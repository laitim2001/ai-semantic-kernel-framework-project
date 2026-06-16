# Sprint 57.128 Progress — chat-v2 resume transcript persistence (persist post-resume SSE events to `message_events`)

[Plan](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-128-plan.md) · [Checklist](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-128-checklist.md)

**Branch**: `feature/sprint-57-128-chatv2-resume-transcript-persistence` (from `main` `5ddc11cc`)
**AD**: `AD-ChatV2-Resume-Transcript-Persistence` (the pre-existing 57.125 gap re-flagged by the 57.126/127 carryovers)
**Scope**: minimal (user-picked via AskUserQuestion 2026-06-16) — persist post-resume loop events only; the approve/reject decision stays in `approvals` + audit-log.

---

## Day 0 — Plan-vs-Repo Verify (三-prong) — 2026-06-16

Investigation: 2 Explore sweeps (resume request+SSE path / two-ledger interaction) + direct reads on `main` HEAD `5ddc11cc`.

### Drift findings

| D-ID | Finding | Implication |
|------|---------|-------------|
| **D-max-main-seq-argorder** ✅ RESOLVED | The 2 Explore agents disagreed on the arg order. The send path (`router.py:707`) calls `_max_main_seq(db, tenant_id, session_id)`; the def (`:613-617`) is `(db, tenant_id, session_id)`. **Order = `(db, tenant_id, session_id)`** (Agent A correct; Agent B's example was wrong). | Use `_max_main_seq(db, tenant_id, session_id)` in the resume mirror. A wrong order would have silently scrambled the seq seed. |
| **D-persist-main-event-sig** ✅ | `_persist_main_event(payload, *, db, tenant_id, session_id, sequence_num)` (`:570-577`); `db is None` → early return; best-effort `begin_nested()` SAVEPOINT + swallow/log (`:586-603`). Writes `MessageEvent(event_type=payload["type"], event_data=payload["data"], ...)`. | Reuse as-is; pass the same kwargs from the resume mirror. |
| **D-resume-stream-signature** ✅ | `_stream_resume_events(loop, *, state, trace_context)` (`:1201-1206`); body (`:1215-1223`) = `async for event in loop.resume(...)` → `serialize_loop_event` → `except NotImplementedError: continue` → `if payload is None: continue` → `yield format_sse_message(...)`. `resume_chat` (`:1310-1363`) has `current_tenant` / `current_user` / `db` in scope; calls the generator at `:1350-1354`. | Add `db`/`tenant_id`/`session_id` params + thread them from `resume_chat`. Feasible — all deps in scope. |
| **D-serialize-skip-parity** ✅ | Send path (`:745-777`): `serialize_loop_event` → `NotImplementedError` skip → `payload is None` skip → (active_skill inject — send-only) → `if main_transcript_on: main_seq += 1; _persist_main_event(...)` → `yield`. Note `:768` is `if main_transcript_on:` (NOT `and db`) — `db is None` handled inside the helpers. | Mirror EXACTLY: persist AFTER the skip checks, BEFORE yield; `if main_transcript_on:` guard. |
| **D-no-user-message-on-resume** ✅ | The send path persists a `user_message` row (`:708-716`) BEFORE `loop.run()` (one per send). | Resume has NO new user prompt → do NOT add a `user_message` row. The resume just continues; the original send already persisted the user prompt + pre-pause events. |
| **D-resume-yields-both-outcomes** 🆕 | `resume_chat` docstring (`:1325-1329`): APPROVED → run pending tool + continue to end_turn; REJECTED/ESCALATED → GuardrailTriggered(block) + terminate. BOTH produce a valid SSE stream. | Persisting the resume events is correct for BOTH outcomes (the replay shows the outcome — approved continuation OR the block). No special-casing. |
| **D-replay-event-types** ✅ | The resume yields the SAME `serialize_loop_event` output as the send path (tool exec / llm_response / loop_end / verification / guardrail). `mergeEvent` already folds these (it handles every send-path event). | NO frontend change — by construction, if `mergeEvent` handles send-path events it handles resume events identically. |
| **D-partition-coverage** 🟢 (Prong 3) | `message_events_default` partition exists (`0028:76`); the resume persist reuses the SAME `message_events` table/writer. | NO migration, NO new column. |
| **D-baselines** ✅ | full pytest **2720+5skip** · wire **24** · Vitest **904** · mockup **51** · mypy `src` **0/372** · run_all **10/10** (57.127 + #303). Note the intermittent `AD-Billing-Outbox-Drain-Test-Flake` may surface once; re-run confirms. | Re-assert at the gate. |

### Scope deltas from Day-0
None — the plan's anchors all verified clean. The ONLY plan-time uncertainty (`_max_main_seq` arg order) resolved to `(db, tenant_id, session_id)`. No migration (default partition exists). Scope unchanged → **go/no-go: CONTINUE Day 1**.

### Go / No-Go
✅ **GO** — the fix is exactly as scoped: mirror `_persist_main_event` into `_stream_resume_events` (verified arg order, skip/None parity, deps in scope), thread deps from `resume_chat`. Pure backend, no migration, no frontend.

---

## Day 1-2 — Backend implementation + test — 2026-06-16

### Implemented
- **`router.py` `_stream_resume_events`** (EDIT): added kw-only params `tenant_id: UUID`, `session_id: UUID`, `db: AsyncSession | None = None` (mirror the send-path types — only `resume_chat` calls it, no test caller, so required params are clean for mypy). Seeds `main_transcript_on` + `main_seq = await _max_main_seq(db, tenant_id, session_id) if main_transcript_on else 0`; inside the `async for ... loop.resume(...)` loop, AFTER the `serialize_loop_event` skip/None checks and BEFORE `yield`, `if main_transcript_on: main_seq += 1; await _persist_main_event(payload, db=db, tenant_id=tenant_id, session_id=session_id, sequence_num=main_seq)`. No `user_message` row (resume has no new prompt). WHY-docstring + file-header MHist.
- **`router.py` `resume_chat`** (EDIT): threads `tenant_id=current_tenant, session_id=session_id, db=db` into the `_stream_resume_events(...)` call (deps already in scope). Public route signature unchanged.

### Test (US-5)
- **`test_chat_resume_persistence.py`** (NEW, integration, 4 passed): drives the REAL `_stream_resume_events` with a fake `_ResumingLoop` (mirrors `test_main_transcript_persist.py`): (a) post-resume events persist (turn_start/llm_request/loop_end; Thinking skipped; NO user_message row), (b) seq continues past a pre-seeded pre-pause MAX (5 pre-pause → seq 6,7,8, no collision), (c) gate-off (`MAIN_TRANSCRIPT_OBSERVER=false`) → no rows, (d) cross-tenant invisible (鐵律).

### Gate (Day 1-2)
black/isort/flake8 clean · mypy `src` **0/372** · run_all **10/10** (wire **24**, LLM-SDK-leak clean) · full pytest **2724 passed / 5 skipped** (+4) · frontend UNCHANGED (no FE edit). (1st background full-run crashed on a pytest-capture I/O error — infra, not test failures; clean foreground re-run = 2724+5.) NO migration (`message_events_default` partition exists, 0028).

---

## Day 3 — Drive-through (real UI + real backend + real LLM) — 2026-06-16

**MANDATORY** per US-6. The actual user flow: HITL pause → approve/resume → reload → replay shows the post-approval continuation.

### Setup (Risk Class E — clean restart)
- Pre-check: `Win32_Process` sweep → only unrelated `http.server 8090`; :8000 FREE (no orphan). Frontend :3007 up (node — NOT stopped).
- Clean no-`--reload` `uvicorn api.main:app` → sole :8000 owner **PID 42600**; startup log `startup complete` (serves the post-edit `router.py`).
- Precondition (deterministic pause trigger): dev-login as **dan@acme.com** (admin/platform_admin) → set acme-prod HITL policy via an authenticated in-page `PUT /admin/tenants/{tid}/hitl-policies` `{auto_approve_max_risk: LOW, require_approval_min_risk: MEDIUM}` (200). `python_sandbox` = `risk_level=MEDIUM, destructive=False` → MEDIUM ≥ require → escalates → pause (the 57.122-validated trigger).

### Driven flow (real chat-v2 UI via Playwright, real Azure gpt-5.2, session `b78cb63d`)
| Step | Action | Observed | Verdict |
|------|--------|----------|---------|
| 1 | Send "Use the python_sandbox tool to compute 6 times 7…" | Agent calls `python_sandbox` `{"code":"print(6*7)"}` → loop pauses; HITL approval card (MEDIUM, `always_ask`, approval_id `6b76c575…`); loop trace ends `loop_end stop=awaiting_approval`; `messages_count=4` | ✅ pause |
| 2 | Click **Approve & continue** | `decide` (POST `/governance/approvals/{id}/decide`) → `resume` (POST `/chat/{id}/resume`) → loop continues → **"42"** renders live + verification passed | ✅ resume |
| 3 | Reload (fresh store, empty pane) → click the session in SessionList | testid `session-item-b78cb63d…` → `loadSessionHistory` replays `/events` → **COMPLETE replay**: user prompt → python_sandbox → approval card ("Decision: APPROVED") → **"42"** → "Verification passed" | ✅ **THE fix** |

### Three-layer proof (all PASS)
1. **Writer (`message_events`)** — `GET /sessions/b78cb63d/events` → **40 events, seq 1→40 monotonic**. Pre-pause (seq 1-19): user_message → … → `approval_requested` → `loop_end` (awaiting_approval). **Post-resume (seq 20-40) — persisted by the fix**: `loop_start` → `approval_received` → `tool_call_request` → **`tool_call_result`** (=42) → … → `verification_passed` → `loop_end`. Before this sprint the session would have stopped at seq 19.
2. **Seq continuity** — `_max_main_seq` seeded the resume at 19 → post-resume continued 20+ with NO collision (the 57.126 ordering logic).
3. **Replay (user-facing payoff)** — reload + click → the replay renders the FULL conversation incl. the post-approval answer (42) + the APPROVED decision card + verification, NOT stopping at the pause.

### AP-4 per-control walk
- Composer / send: works. ✅ · Approve button: fires decide+resume, real effect. ✅ · python_sandbox tool block + 42 result: real (not fixture). ✅ · HITL card "Decision: APPROVED": real `approval_received` replay. ✅ · Inspector populated. ✅ · No dead control / no fixture.

### Evidence
- `artifacts/sprint-57-128-drivethrough-1-paused.png` (HITL approval card) · `-2-resumed.png` (42 live) · `-3-replay.png` (complete replay after reload+click) · `backend-drivethrough.log`.

### Verdict
✅ **DRIVE-THROUGH PASS** — the resumed-session replay is now complete on real Azure gpt-5.2 through the real chat-v2 UI. `AD-ChatV2-Resume-Transcript-Persistence` behavior satisfied.

---

## Day 4 — Closeout — 2026-06-16

- Drive-through PASS recorded (Day 3) + 3 screenshots/log in `artifacts/`.
- CHANGE-095 (`claudedocs/4-changes/feature-changes/CHANGE-095-chatv2-resume-transcript-persistence.md`).
- retrospective.md: Q1-Q7 + calibration (`chatv2-resume-persistence-wiring` 0.55, 1st data point).
- Navigators: CLAUDE.md Current Sprint + Last Updated; MEMORY.md pointer; memory subfile `project_phase57_128_*.md`; sprint-workflow matrix row.
- `AD-ChatV2-Resume-Transcript-Persistence` CLOSED in next-phase-candidates.
- Continuation (extends the validated 57.125/126 `message_events` mechanism) → NO design note.

### Final gate (Day 4)
- black/isort/flake8 clean · mypy `src` **0/372** · run_all **10/10** (wire **24**) · frontend UNCHANGED (Vitest 904 / mockup 51; no FE edit) · full pytest **2724 passed / 5 skipped** (+4 vs the 2720 baseline). The intermittent `AD-Billing-Outbox-Drain-Test-Flake` did NOT surface on the clean re-run.
