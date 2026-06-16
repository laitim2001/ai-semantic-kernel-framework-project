# Sprint 57.128 — Checklist (chat-v2 resume transcript persistence — persist post-resume SSE events to `message_events`. **Minimal scope** (user-picked): mirror the send-path `_persist_main_event` into `_stream_resume_events` so a paused-then-resumed session's replay shows the post-approval continuation; seed `main_seq` via `_max_main_seq` (continues past the pre-pause events); the approve/reject decision stays in `approvals` + audit-log (no new event type). **Pure backend** — 1 file EDIT (`router.py`) + 1 NEW test; ZERO frontend/CSS/Vitest/wire/codegen/migration; `loop.py` untouched (the `messages` ledger already covers resume). **Drive-through MANDATORY** — trigger a HITL pause → resume → reload → the replay now plays past the pause. CHANGE-095; continuation (NO design note).)

[Plan](./sprint-57-128-plan.md)

---

## Day 0 — Plan-vs-Repo Verify (三-prong) + Branch

### 0.1 Three-prong Day-0 verify (against `main` HEAD `5ddc11cc`)
- [x] **Prong 1 — path verify**: `api/v1/chat/router.py` exists (contains `_stream_resume_events` / `_stream_loop_events` / `_persist_main_event` / `_max_main_seq` / `resume_chat`); `loop.py` exists; `CHANGE-095` free; test path `tests/integration/api/` exists; the new `test_chat_resume_persistence.py` does NOT exist
- [x] **Prong 2 — content verify** (drift → progress.md):
  - [x] **D-max-main-seq-argorder** ⚠️ THE feasibility detail — `grep -n "def _max_main_seq" router.py` + read the signature → confirm the EXACT arg order (`db`, `tenant_id`, `session_id` in WHAT order) — the 2 Explore agents disagreed; a wrong order silently scrambles the seq seed
  - [x] **D-persist-main-event-sig** — read `_persist_main_event` (`router.py:~570-603`); confirm exact kwargs (`payload`, `db`, `tenant_id`, `session_id`, `sequence_num`) + that it's best-effort (SAVEPOINT + swallow)
  - [x] **D-resume-stream-signature** — read `_stream_resume_events` (`router.py:~1201-1223`) current params + the `loop.resume(...)` loop body (serialize → skip → yield); read `resume_chat` (`~1309-1363`) → confirm `db` / `current_tenant` / `session_id` are in scope to thread in
  - [x] **D-serialize-skip-parity** — read `_stream_loop_events`'s per-event block (`~745-777`): the `serialize_loop_event` `NotImplementedError` skip + `payload is None` skip + the persist (`~768-776`) → mirror EXACTLY in resume (persist AFTER the skip checks, BEFORE yield)
  - [x] **D-no-user-message-on-resume** — confirm the send path's `user_message` persist (`~708-716`) is BEFORE the loop (one-per-send) → resume has NO new user prompt → do NOT add a `user_message` row
  - [x] **D-replay-event-types** — confirm `frontend/src/features/chat_v2/store/chatStore.ts` `mergeEvent` already folds the event types a resume yields (tool exec / llm_response / loop_end / verification) → NO frontend change
- [x] **Prong 3 — schema verify** (light — no schema change): confirm `message_events` table + its `default` partition exist (`0028`); the resume persist reuses the SAME table/writer as the send path → NO migration, NO new column
- [x] **D-baselines** — re-assert: full pytest **2720+5skip** · wire **24** · Vitest **904** · mockup **51** · mypy `src` **0/372** · run_all **10/10** (note the intermittent `AD-Billing-Outbox-Drain-Test-Flake` may surface once; re-run confirms)
- [x] **Catalog drift** — progress.md Day-0 table (D-IDs + finding + implication; cross-ref plan §Risks)
- [x] **Go/no-go** — findings shift scope ≤20% → continue; the arg-order finding (D-max-main-seq-argorder) is the gate (wrong order = silent seq scramble)

### 0.2 Branch
- [x] `git checkout -b feature/sprint-57-128-chatv2-resume-transcript-persistence` (from `main` `5ddc11cc`) ✅ (done)

---

## Day 1 — Backend: `_stream_resume_events` persist + `resume_chat` wiring (US-1..4)

### 1.1 `_stream_resume_events` persist (US-1/2/4)
- [x] **`router.py` (EDIT)**: add params `db: AsyncSession | None = None`, `tenant_id: UUID | None = None`, `session_id: UUID | None = None`; at the top seed `main_transcript_on` + `main_seq = await _max_main_seq(<verified arg order>) if (main_transcript_on and db is not None) else 0`; inside the `async for event in loop.resume(...)` loop, AFTER the serialize + skip/None checks and BEFORE `yield`: `if main_transcript_on and db is not None: main_seq += 1; await _persist_main_event(payload, db=db, tenant_id=tenant_id, session_id=session_id, sequence_num=main_seq)`. NO `user_message` row. WHY-comment (mirror the send path + alternative considered). MHist + Last Modified
  - DoD: post-resume events persist to `message_events`; skip/None payloads NOT persisted; gate-off / `db is None` → no persist; the live stream is unaffected (best-effort)
  - Verify: `mypy src` 0; `grep -n "_persist_main_event" router.py` shows the new resume call site
- [x] **arg-order correctness**: use the EXACT `_max_main_seq` arg order confirmed in D-max-main-seq-argorder (not a guess)
  - DoD: the seq test (Day 2) asserts post-resume seq > pre-pause MAX

### 1.2 `resume_chat` endpoint wiring (US-3)
- [x] **`router.py` (EDIT)**: in `resume_chat`, pass `db=db, tenant_id=current_tenant, session_id=session_id` into `_stream_resume_events(...)`; the public route signature UNCHANGED. MHist
  - DoD: the resume StreamingResponse now persists; `mypy src` 0
  - Verify: `mypy src`; the Day-2 integration test exercises the wired resume path

### 1.3 Backend gate (partial)
- [x] black + isort + flake8 clean · mypy `src` **0** · run_all **10/10** (check_llm_sdk_leak — router.py adds NO provider import — + wire 24)
  - Verify: `cd backend && black . && isort . && flake8 . && mypy src && cd .. && python scripts/lint/run_all.py`

---

## Day 2 — Backend test (US-5) + full gate

### 2.1 Resume-persistence integration test (US-5)
- [x] **`test_chat_resume_persistence.py` (NEW)**: (a) drive a resume (a paused session, or a fake loop whose `resume()` yields a couple of events) → assert the post-resume events land in `message_events` for the session; (b) pre-seed pre-pause `message_events` rows → resume → assert post-resume `sequence_num` strictly > the pre-pause MAX (monotonic, no UNIQUE collision); (c) cross-tenant resume → does NOT write to another tenant (鐵律); (d) `MAIN_TRANSCRIPT_OBSERVER=false` → resume yields but persists nothing
  - DoD: all cases pass; Risk Class C handled (integration `get_db_session` override / autouse reset)
  - Verify: `pytest tests/integration/api/test_chat_resume_persistence.py -q` → all pass

### 2.2 Backend gate (full)
- [x] mypy `src` **0/372** · run_all **10/10** (24) · full pytest **2720+5skip + the new test** · black/isort/flake8 clean · LLM-SDK-leak clean · NO frontend/codegen/mockup change (`diff styles-mockup.css` empty; Vitest 904 / mockup 51 UNCHANGED)
  - Verify: `cd backend && mypy src && pytest -q && cd .. && python scripts/lint/run_all.py` + `git diff --stat frontend/src/styles-mockup.css` empty (note: re-run pytest once if the intermittent billing flake surfaces)

---

## Day 3 — Drive-through (US-6) — real UI + real backend + real LLM (MANDATORY, HITL pause→resume→replay)

### 3.1 Clean restart (Risk Class E — `router.py` changed)
- [x] `Win32_Process` PID/PPID/StartTime sweep → kill stale/orphan uvicorn on :8000 → fresh no-`--reload` `api.main:app` sole owner + "startup complete" + pricing-loader wired; `MAIN_TRANSCRIPT_OBSERVER` on; Vite :3007 NOT stopped
  - DoD: fresh sole :8000 owner; startup log confirms

### 3.2 Drive-through (MANDATORY — NOT gate-only)
- [x] trigger a HITL pause: real-LLM chat-v2 (Azure, dev-login) → a prompt that calls an escalating tool under acme-prod's per-tenant HITL policy → the loop pauses (UI shows awaiting-approval); note the exact tool + policy used
- [x] resume/approve via the UI (or approve endpoint) → the loop continues → the post-approval answer renders live
- [x] **THE fix**: reload (fresh store) → click the session in the SessionList → the replay now plays PAST the pause — shows the post-approval answer + continuation (before this sprint it stopped at the pause)
- [x] verify `GET /sessions/{id}/events` (or a direct `message_events` count) → post-resume rows exist with `sequence_num` continuing past the pre-pause MAX
- [x] per-control AP-4 walk + screenshots + observed-vs-intended → progress.md Day 3; **PASS** only if the reload-replay shows the post-resume continuation on real LLM

---

## Day 4 — CHANGE-095 + closeout

### 4.1 CHANGE-095
- [x] **`CHANGE-095-chatv2-resume-transcript-persistence.md`** (root cause: resume generator omitted `_persist_main_event` + the mirror fix + seq continuity + minimal-scope decision + drive-through + AD closed)

### 4.2 Closeout
- [x] retrospective.md Q1-Q7 + calibration (`chatv2-resume-persistence-wiring` 0.55, 1st data point; parent-direct, agent_factor 1.0; ratio + KEEP/re-point) + progress.md final
- [x] Final gate sweep: mypy `src` **0** · run_all **10/10** (24) · pytest **2720+5 + the new test** · Vitest **904** UNCHANGED · mockup **51** byte-identical · black/isort/flake8 clean · LLM-SDK-leak clean
- [x] Navigators: CLAUDE.md Current-Sprint + Last-Updated (minimal-touch; post-merge flip per §Sprint Closeout) · MEMORY.md pointer + subfile `project_phase57_128_*` · next-phase-candidates (**CLOSE `AD-ChatV2-Resume-Transcript-Persistence`**) · sprint-workflow matrix `chatv2-resume-persistence-wiring` 0.55 row
- [x] **Anti-pattern self-check** (retro Q5): AP-2 (resume persist on 主流量, wired from `resume_chat`) / AP-3 (one `message_events` writer reused, no duplicate) / AP-4 (real resume replay — drive-through proven LIVE) / AP-6 (no new helper/event-type — reuses `_persist_main_event`) / AP-8 (no bare persistence — reuses the observer) / AP-11 (no `_v2` suffix) → 0 violations; v2 lints 10/10
- [x] PR (push + open) → CI → merge on green (gh-verified MERGED before main sync); post-merge status flip
