# Sprint 57.128 Plan — chat-v2 resume transcript persistence (persist post-resume SSE events to `message_events`). Closes `AD-ChatV2-Resume-Transcript-Persistence` — the pre-existing 57.125 gap the 57.126/127 carryovers flagged: the HITL resume path's SSE generator `_stream_resume_events` (`router.py:1201-1223`) is a "thin mirror" of the normal-send `_stream_loop_events` but OMITS the `_persist_main_event` call, so post-resume events stream live but are NEVER persisted to `message_events`. Symptom (user-visible): click a paused-then-resumed session in the SessionList → the replay (`GET /sessions/{id}/events` → `loadSessionHistory` → `mergeEvent`) stops at the pause point, missing the post-approval answer + continuation. **User decision (2026-06-16 AskUserQuestion): minimal scope** — persist the post-resume loop events only (mirror the send-path `_persist_main_event`); the human approve/reject DECISION stays in the `approvals` + audit-log tables (already persisted there), NOT inline in the chat replay (no new event type). **Pure backend**: wire `db`/`tenant_id`/`session_id` into `_stream_resume_events` + persist each yielded event via `_persist_main_event`, seeding `main_seq` from `_max_main_seq` so post-resume events continue monotonically AFTER the pre-pause events (the 57.126 ordering logic) — NO new event type, NO wire/codegen, NO frontend/CSS change, NO migration. **Drive-through MANDATORY** (the actual user flow: trigger a HITL pause → resume/approve → reload → the replay now shows the post-approval continuation). CHANGE-095; continuation (NOT a spike — extends the validated 57.125/126 `message_events` mechanism), so NO design note.

**Status**: Approved-to-execute (user 2026-06-16: "現在繼續執行 AD-ChatV2-Resume-Transcript-Persistence" → investigation (2 Explore sweeps) confirmed the surgical gap → AskUserQuestion picked the **minimal scope**).
**Branch**: `feature/sprint-57-128-chatv2-resume-transcript-persistence`
**Base**: `main` HEAD `5ddc11cc` (post-#303 — the 57.127 chat-v2 live multi-turn merge).
**Slice**: closes `AD-ChatV2-Resume-Transcript-Persistence` (carried from 57.125 → re-flagged in the 57.126 + 57.127 carryovers). A standalone backend wiring fix (no arc).
**Scope decisions**: (a) **minimal scope** (post-resume loop events only) over the fuller "also persist the human approval decision as a replay event" (REJECTED by user — would need a new/wired event type → codegen + frontend + wire-count bump; the decision is already auditable in `approvals` + audit-log). (b) **Mirror the EXISTING `_persist_main_event` + `_max_main_seq`** into `_stream_resume_events` — no new helper, no new contract. (c) **Continuous seq** across the pause boundary (`_max_main_seq` seeds from the session MAX → post-resume continues after the pre-pause events; the 57.126 monotonic-ordering logic, unchanged). (d) **Pure backend** — ZERO frontend / CSS / Vitest / wire / codegen / migration change (the existing `mergeEvent` replay already handles these event types — verified Day-0). (e) The `messages` Cat-3 ledger (57.127) is ALREADY persisted on resume (shared `_run_turns` end_turn → `_persist_to_ledger`) — this sprint touches ONLY the `message_events` SSE-replay ledger. (f) Nothing persisted for error/cancelled resumes (best-effort, mirrors the send path). (g) User-facing behaviour change (resumed-session replay now complete) → a real UI + real backend + real LLM **drive-through is MANDATORY** (incl. actually triggering a HITL pause + resume).

---

## 0. Background

### The bug (the 57.125 gap, re-flagged by 57.126 + 57.127 carryovers)

Sprint 57.125/126 built the `message_events` SSE-frame ledger + the frontend replay (click a session → `GET /sessions/{id}/events` → replay through `mergeEvent`). But the persistence observer (`_persist_main_event`) was wired ONLY into the normal-send generator `_stream_loop_events`. The HITL **resume** path has its own generator `_stream_resume_events` ("thin mirror") that drives `loop.resume()` and yields SSE bytes but never persists them. So a session that paused on a HITL approval and was later resumed has its post-resume turns missing from the replay ledger.

### Root cause (2 Explore sweeps, grep-confirmed — re-verified Day-0 §checklist 0.1)

| Layer | Reality (on `main` HEAD `5ddc11cc`) | Anchor |
|-------|-------------------------------------|--------|
| Normal-send persists every event | `_stream_loop_events`: seeds `main_seq = await _max_main_seq(...)`, persists the `user_message` row, then `await _persist_main_event(payload, ...)` before each yield | `router.py:706-716` (seed + user_message) / `:768-776` (per-event) |
| Resume generator omits persist | `_stream_resume_events` ("thin mirror"): `async for event in loop.resume(...)` → `serialize_loop_event` → `yield format_sse_message(...)` — **ZERO `_persist_main_event` calls** | `router.py:1201-1223` |
| Resume endpoint has the deps | `resume_chat` (`POST /{session_id}/resume`) has `db`, `current_tenant`, `session_id` in scope but does NOT pass them to `_stream_resume_events` | `router.py:1309-1363` |
| `messages` ledger already OK on resume | `loop.resume()` → shared `_run_turns` end_turn → `_persist_to_ledger` (57.127) → the Cat-3 `messages` table IS written on resume | `loop.py:2689-2692 / 2721-2724` |
| Frontend replay would stop at pause | `loadSessionHistory` fetches `/events`, sorts by `sequence_num`, replays through `mergeEvent` — if post-resume events aren't in `message_events`, the replay ends at the pause frame | `chatStore.ts:367-406` |

→ The fix must **persist the post-resume main events to `message_events`**, mirroring the send path.

### The design (mirror `_persist_main_event` into `_stream_resume_events`)

```
# resume_chat endpoint (router.py ~1309): pass the persist deps into the generator
return StreamingResponse(
    _stream_resume_events(
        result.loop,
        state=result.state,
        trace_context=trace_ctx,
        db=db,                      # NEW
        tenant_id=current_tenant,   # NEW
        session_id=session_id,      # NEW
    ), media_type="text/event-stream", ...)

# _stream_resume_events (router.py ~1201): seed + persist (mirror _stream_loop_events)
main_transcript_on = os.environ.get("MAIN_TRANSCRIPT_OBSERVER", "true").lower() == "true"
main_seq = await _max_main_seq(db, tenant_id, session_id) if (main_transcript_on and db) else 0
async for event in loop.resume(state=state, trace_context=trace_context):
    payload = serialize_loop_event(event)   # (same skip/None handling as the send path)
    if payload is None: continue
    if main_transcript_on and db is not None:
        main_seq += 1
        await _persist_main_event(payload, db=db, tenant_id=tenant_id,
                                  session_id=session_id, sequence_num=main_seq)
    yield format_sse_message(payload["type"], payload["data"])
```

**Why mirror, not refactor**: the cleanest, lowest-risk fix is to make `_stream_resume_events` carry the same best-effort persistence the send path already has. Extracting a shared "persist-while-streaming" helper across the two generators is tempting but they differ (the send path also seeds the `user_message` row + has chat-start observers); a shared helper would over-abstract for 2 call sites (AP-6). **Alternative considered + rejected**: (i) persist inside `loop.resume()` itself — the loop is provider-neutral Cat-1 and must NOT know about the `message_events` DB table (that's an API-layer concern, exactly why `_persist_main_event` lives in `router.py`); (ii) a new event type for the approval decision — rejected by the user (minimal scope).

**Why continuous seq**: `_max_main_seq` returns the session's current MAX `sequence_num` (the pre-pause events persisted by the original send). Seeding from it makes the post-resume events continue monotonically — the replay sorts by `sequence_num` and folds them after the pre-pause frames. (Same logic as the 57.126 multi-turn `main_seq` fix.)

### Ground truth (Day-0 head-start — 2 Explore sweeps on `main` HEAD `5ddc11cc`; ALL re-verified in §checklist 0.1)

- `api/v1/chat/router.py:570-603` — `_persist_main_event(payload, *, db, tenant_id, session_id, sequence_num)` (best-effort SAVEPOINT, swallow+log). **Day-0 confirms the EXACT signature + kwarg names.**
- `api/v1/chat/router.py:613-625` — `_max_main_seq(...)` — **Day-0 confirms the EXACT arg ORDER** (the 2 Explore agents disagreed: `(db, tenant_id, session_id)` vs `(db, session_id, tenant_id)` — MUST grep the def before wiring).
- `api/v1/chat/router.py:706-716` — `_stream_loop_events` seed + `user_message` persist (the pattern to mirror; the resume has no new user prompt → NO `user_message` row).
- `api/v1/chat/router.py:768-776` — `_stream_loop_events` per-event persist (the exact block to mirror).
- `api/v1/chat/router.py:1201-1223` — `_stream_resume_events` (the EDIT target).
- `api/v1/chat/router.py:1309-1363` — `resume_chat` endpoint (where `db`/`current_tenant`/`session_id` are in scope → pass to the generator).
- `agent_harness/orchestrator_loop/loop.py:2689-2692 / 2721-2724` — `_run_turns` end_turn → `_persist_to_ledger` (the `messages` ledger, ALREADY covers resume — NOT touched this sprint).
- `frontend/src/features/chat_v2/store/chatStore.ts:367-406` — `loadSessionHistory` replay (the consumer; NO change needed — verified it folds the existing event types).
- `serialize_loop_event` + `format_sse_message` — the shared serializer/framer (reused as-is).

**Baselines (57.127 closeout + #303)**: full pytest **2720+5skip** · wire **24** · Vitest **904** · mockup **51** · mypy `src` **0/372** · run_all **10/10**. Re-verify Day-0. (Note: the intermittent `test_drain_materializes_cost_ledger_parity` Risk Class C billing flake — `AD-Billing-Outbox-Drain-Test-Flake`, pre-existing, untouched — may surface once in a full run; re-run confirms 2720+5.)

### STALE / drift findings (Day-0; full detail → progress.md — placeholder, filled in §checklist 0.1)

- **D-max-main-seq-argorder** ⚠️ THE feasibility detail — the 2 Explore agents gave different arg orders for `_max_main_seq`; **grep the def signature** before wiring (a wrong order would scramble the seq seed silently).
- **D-persist-main-event-sig** — confirm `_persist_main_event`'s exact kwargs (`db` / `tenant_id` / `session_id` / `sequence_num`).
- **D-resume-stream-signature** — confirm `_stream_resume_events`'s current params + how `resume_chat` calls it (so the new params thread cleanly).
- **D-serialize-skip-parity** — confirm the send path's skip/None handling (`NotImplementedError` skip + `payload is None` skip) so the resume mirror matches exactly (don't persist a skipped/None payload).
- **D-replay-event-types** — confirm the frontend `mergeEvent` already handles the event types the resume yields (tool exec / llm_response / loop_end / verification) → no frontend change.
- **D-baselines** — re-assert the 6 gate baselines.

## 1. Sprint Goal

Close `AD-ChatV2-Resume-Transcript-Persistence`: the HITL resume path now persists its post-resume SSE events to the `message_events` ledger, so a paused-then-resumed session's replay is complete (shows the post-approval answer + continuation, not just up to the pause). The fix mirrors the normal-send persistence into `_stream_resume_events`: seed `main_seq` from `_max_main_seq` (post-resume continues monotonically after the pre-pause events) + `await _persist_main_event(payload, ...)` before each yield (best-effort, `MAIN_TRANSCRIPT_OBSERVER`-gated, `db is None`-safe), with `db`/`tenant_id`/`session_id` threaded from the `resume_chat` endpoint. Minimal scope (post-resume loop events only; the approve/reject decision stays in `approvals` + audit-log). Pure backend; ZERO frontend/CSS/Vitest/wire/codegen/migration change; the `messages` Cat-3 ledger is already covered on resume (untouched). Proven by a backend integration test (resume drives `_stream_resume_events` → the post-resume events land in `message_events` with monotonic seq continuing past the pre-pause max; cross-tenant isolation) **and a MANDATORY real UI + real backend + real LLM drive-through** (trigger a HITL pause → resume/approve → reload → the replay now shows the post-approval continuation). CHANGE-095; continuation (NO design note).

## 2. User Stories

- **US-1** (persist wiring): 作為 chat-v2 replay，我希望 `_stream_resume_events` 在每個 post-resume 事件 yield 前呼叫 `_persist_main_event`（best-effort、`MAIN_TRANSCRIPT_OBSERVER`-gated、`db is None`-safe），以便 resume 後的 turns 寫進 `message_events`。
- **US-2** (seq continuity): 作為 replay 排序，我希望 resume 的 `main_seq` 由 `_max_main_seq` 從 session MAX seed（沿用 57.126 邏輯），以便 post-resume 事件接在 pre-pause 事件之後 monotonic 排序、不碰撞。
- **US-3** (endpoint wiring): 作為 `resume_chat` endpoint，我希望把 `db` / `tenant_id` (`current_tenant`) / `session_id` 傳進 `_stream_resume_events`，以便 generator 能持久化（這些 deps 已在 endpoint scope）。
- **US-4** (parity with send path): 作為持久化邏輯，我希望 resume mirror 與 send 路徑的 skip/None 處理一致（`serialize_loop_event` 的 `NotImplementedError` skip + `payload is None` skip → 不持久化），以便不寫入半成品 payload。
- **US-5** (tests): backend 整合測試 — drive resume（mock/echo loop 或真 resume harness）→ post-resume 事件出現在 `message_events`，seq 接續 pre-pause MAX；cross-tenant resume 不寫到別 tenant；`MAIN_TRANSCRIPT_OBSERVER=false` → 不持久化（gate off）。
- **US-6** (drive-through — MANDATORY): 真 UI + 真後端 + 真 Azure：觸發一個 HITL pause（escalate tool + 對應 per-tenant policy）→ approve/resume → reload → 點該 session → replay **現在播過暫停點，顯示核准後的答案 + 後續**（之前只播到暫停）；逐控件 AP-4 walk + 截圖 + 實際-vs-預期 → progress.md。
- **US-7** (closeout): CHANGE-095 + 收尾（retro + calibration + navigators + **CLOSE the AD**）；continuation → NO design note。

## 3. Technical Specifications

### 3.0 Architecture (1 file EDIT: `_stream_resume_events` persist + `resume_chat` param threading; NO new helper / event type / frontend / wire / codegen / migration)

```
# EDIT
backend/src/api/v1/chat/router.py   (EDIT): _stream_resume_events gains db/tenant_id/session_id params
                                            + seeds main_seq via _max_main_seq + persists each event
                                            via _persist_main_event; resume_chat threads the deps in
# tests
backend/tests/integration/api/test_chat_resume_persistence.py  (NEW): resume → message_events written,
                                            seq continues past pre-pause MAX, cross-tenant [], gate-off no-op
# docs
claudedocs/4-changes/feature-changes/CHANGE-095-chatv2-resume-transcript-persistence.md  (NEW)
# UNTOUCHED: loop.py (the messages ledger already covers resume) · frontend/** · styles-mockup.css ·
#            events.py/sse.py/codegen (wire 24) · _persist_main_event / _max_main_seq (reused as-is) ·
#            no migration
```

### 3.1 `_stream_resume_events` persist (US-1/2/4) — `router.py`

- Add params `db: AsyncSession | None = None`, `tenant_id: UUID | None = None`, `session_id: UUID | None = None` (mirror the send path's available deps).
- At the top: `main_transcript_on = os.environ.get("MAIN_TRANSCRIPT_OBSERVER", "true").lower() == "true"`; `main_seq = await _max_main_seq(<verified arg order>) if (main_transcript_on and db is not None) else 0`.
- Inside the `async for event in loop.resume(...)` loop, AFTER `serialize_loop_event` + the existing skip/None handling and BEFORE `yield`: `if main_transcript_on and db is not None: main_seq += 1; await _persist_main_event(payload, db=db, tenant_id=tenant_id, session_id=session_id, sequence_num=main_seq)`.
- NO `user_message` row (resume has no new user prompt — the resume is a continuation; the original send already persisted the user prompt + the pre-pause events).
- Best-effort: `_persist_main_event` already wraps a SAVEPOINT + swallows/logs → a persist failure never breaks the live resume stream (same guarantee as the send path).

### 3.2 `resume_chat` endpoint wiring (US-3) — `router.py`

- In `resume_chat` (`POST /{session_id}/resume`), the deps `db` (`Depends(get_db_session)`), `current_tenant`, `session_id` are already present. Pass them into `_stream_resume_events(..., db=db, tenant_id=current_tenant, session_id=session_id)`.
- No signature change to the public route; only the internal generator call gains kwargs.

### 3.3 Tests (US-5) — `test_chat_resume_persistence.py`

- **resume persists**: build a paused session (or a minimal harness that drives `_stream_resume_events` with a fake loop whose `resume()` yields a couple of events) → assert the post-resume events are written to `message_events` for the session with `sequence_num` continuing from the seeded MAX. (Mirror `test_message_store.py` / the 57.125 `_persist_main_event` test harness.)
- **seq continuity**: pre-seed a few `message_events` rows (simulating the pre-pause persisted events) → resume → assert post-resume seqs are strictly > the pre-pause MAX (no collision; the UNIQUE `(session_id, sequence_num, ...)` would surface a collision).
- **cross-tenant**: a resume bound to tenant B does not write to tenant A's session rows; a reader scoped to A doesn't see B's (鐵律).
- **gate off**: `MAIN_TRANSCRIPT_OBSERVER=false` → `_stream_resume_events` yields but persists nothing.
- Risk Class C: use the integration `get_db_session` override / autouse reset if a singleton is touched.

### 3.4 Drive-through (US-6) — real UI + real backend + real LLM (MANDATORY)

1. Clean restart (Risk Class E — only `router.py` changed; `Win32_Process` PID/PPID/StartTime sweep; fresh sole :8000 owner + startup log; `MAIN_TRANSCRIPT_OBSERVER` on). Vite :3007 (node) NOT stopped.
2. Trigger a HITL pause: in chat-v2 (real Azure), send a prompt that calls a tool requiring approval (an escalating tool under the active per-tenant HITL policy — e.g. a destructive/HIGH-risk tool, or a tenant policy whose `require_approval_min_risk` catches the tool). The loop pauses → UI shows awaiting-approval.
3. Resume/approve via the UI (or the approve endpoint) → the loop continues → the post-approval answer renders live.
4. **The fix**: reload (fresh store) → click the session in the SessionList → the replay now shows the COMPLETE conversation INCLUDING the post-approval answer + continuation (before this sprint it stopped at the pause).
5. `GET /sessions/{id}/events` + a direct `message_events` count: post-resume rows exist with seq continuing past the pre-pause MAX. Per-control AP-4 walk; screenshots + observed-vs-intended → progress.md. "drive-through PASS" only if step 4 actually shows the post-resume continuation on reload.

### 3.5 What is explicitly NOT done

Persisting the human approve/reject DECISION as its own replay event (the rejected fuller scope — the decision stays in `approvals` + audit-log); a new event type / wire / codegen / frontend change; touching the `messages` Cat-3 ledger (already covers resume); persisting error/cancelled resumes; the `message_events`/`messages` consolidation (intentional dual-ledger); subagent sidechain post-resume persistence (sidechains are spawned during the initial run, not post-resume); ANY frontend / CSS / Vitest / migration change.

### 3.6 Validation (US-1..US-7)

Gates: mypy `src` **0/372** (re-assert) · run_all **10/10** (wire **24** unchanged — no codegen) · full pytest **2720+5skip + the new integration test** · Vitest **904 UNCHANGED** (no FE change) · mockup **51 UNCHANGED** (`diff styles-mockup.css` empty) · `black`/`isort`/`flake8` clean · LLM-SDK-leak clean (router.py is API-layer; no provider import added). Plus the §3.4 drive-through.

## 4. File Change List

| # | File | Action |
|---|------|--------|
| 1 | `backend/src/api/v1/chat/router.py` | EDIT — `_stream_resume_events` gains `db`/`tenant_id`/`session_id` + seeds `main_seq` via `_max_main_seq` + persists each post-resume event via `_persist_main_event`; `resume_chat` threads the deps in |
| 2 | `backend/tests/integration/api/test_chat_resume_persistence.py` | NEW — resume → `message_events` written / seq continues past pre-pause MAX / cross-tenant [] / gate-off no-op |
| 3 | `claudedocs/4-changes/feature-changes/CHANGE-095-chatv2-resume-transcript-persistence.md` | NEW — change record |
| — | `loop.py` · `_persist_main_event`/`_max_main_seq` (reused) · `frontend/**` · `styles-mockup.css` · codegen/wire · migration | **UNTOUCHED** |

## 5. Acceptance Criteria

1. **Resume persists**: `_stream_resume_events` writes each post-resume SSE event to `message_events` (best-effort, `MAIN_TRANSCRIPT_OBSERVER`-gated, `db is None`-safe), mirroring the send path.
2. **Seq continuity**: `main_seq` seeds from `_max_main_seq` (verified arg order) → post-resume `sequence_num`s are strictly > the pre-pause MAX (monotonic, no collision).
3. **Endpoint wiring**: `resume_chat` passes `db`/`current_tenant`/`session_id` into `_stream_resume_events`; the public route signature is unchanged.
4. **Parity**: the resume mirror uses the same `serialize_loop_event` skip/None handling as the send path (no half/None payload persisted); no `user_message` row (resume has no new user prompt).
5. **Multi-tenant** (鐵律): persists scoped to the session's `tenant_id`; a cross-tenant resume does not write to another tenant (test-proven).
6. **Pure backend**: `diff styles-mockup.css` empty; Vitest 904 + mockup 51 UNCHANGED; wire 24; no codegen/migration; `loop.py` untouched.
7. Gates: mypy 0 · run_all 10/10 (24) · pytest 2720+5 + the new test · black/isort/flake8 clean · LLM-SDK-leak clean.
8. **Drive-through PASS (MANDATORY, real UI + backend + LLM)**: a HITL pause → resume/approve → reload → the session replay shows the post-approval answer + continuation (NOT stopping at the pause); `message_events` has post-resume rows with continuous seq; screenshots + observed-vs-intended in progress.md. (NOT gate-only.)
9. `AD-ChatV2-Resume-Transcript-Persistence` CLOSED; CHANGE-095; calibration recorded; navigators + next-phase-candidates updated.

## 6. Deliverables

- [ ] US-1 `_stream_resume_events` persists each post-resume event via `_persist_main_event` (`router.py`)
- [ ] US-2 `main_seq` seeded from `_max_main_seq` (verified arg order); post-resume seq continues past pre-pause MAX (`router.py`)
- [ ] US-3 `resume_chat` threads `db`/`tenant_id`/`session_id` into the generator (`router.py`)
- [ ] US-4 skip/None parity with the send path; no `user_message` row on resume (`router.py`)
- [ ] US-5 integration test: resume persists / seq continuity / cross-tenant [] / gate-off no-op (`test_chat_resume_persistence.py`)
- [ ] US-6 drive-through (HITL pause → resume → reload → replay shows post-approval continuation; screenshots; MANDATORY)
- [ ] US-7 CHANGE-095 + closeout (retro + calibration + navigators + CLOSE the AD)

## 7. Workload Calibration

- Scope class **`chatv2-resume-persistence-wiring` 0.55** (NEW — a pure-backend mirror-wiring of the EXISTING `_persist_main_event` observer into the sibling `_stream_resume_events` generator: no new ABC / table / serializer / event type / wire / codegen / frontend / migration. Closest classes: `subagent-sse-relay-wiring` 0.55 (Cat 11→12 backend SSE-relay composition wiring) + lighter than `chatv2-transcript-persistence-spike` 0.60 (which BUILT the observer + read endpoint). **Ceremony-floor note** (57.120/122/123): the CODE is tiny (~10 lines + param threading) but a full-ceremony parent-direct sprint WITH a mandatory drive-through does NOT drop below ~0.55 — and the HITL drive-through SETUP (trigger a real pause → resume) is the dominant wall-clock, not the code.)
- **Agent-delegated: no** (parent-direct — the seq-seed arg-order verify, the skip/None parity, and the best-effort SAVEPOINT mirroring are precise correctness-critical wiring best hand-authored + self-verified; the drive-through requires hand-driving a HITL pause). `agent_factor` 1.0 → 3-segment form.
- Bottom-up est ~5.5 hr (Day-0 三-prong + arg-order/sig verify ~0.75 · `_stream_resume_events` persist + `resume_chat` threading ~1.0 · integration test (resume persists + seq + cross-tenant + gate-off) ~1.25 · HITL drive-through (trigger pause + resume + reload + replay) + clean restart ~1.5 · CHANGE-095 + closeout ~1.0) → class-calibrated commit ~3.0 hr (mult 0.55). Day-4 retro Q2 verifies (`chatv2-resume-persistence-wiring` 1st data point; flag if the HITL drive-through setup over-runs — the main risk).

## 8. Dependencies & Risks

| Risk | Mitigation |
|------|------------|
| **`_max_main_seq` arg order** (the 2 Explore agents disagreed: `(db, tenant_id, session_id)` vs `(db, session_id, tenant_id)`) — a wrong order silently scrambles the seq seed | **Day-0 D-max-main-seq-argorder** greps the `def _max_main_seq` signature FIRST; the seq test asserts post-resume seq > pre-pause MAX (a wrong seed would fail it) |
| **Double-persist of pre-pause events** (re-persisting what the original send already wrote) | resume persists ONLY what `loop.resume()` yields (post-resume events); the seq SEED from `_max_main_seq` continues AFTER the pre-pause events — no overlap; the test asserts strictly-increasing seq with no collision |
| **`resume_chat` lacks a dep at the call site** | Day-0 confirms `db` / `current_tenant` / `session_id` are all in `resume_chat`'s scope (the endpoint already injects them); pass them through |
| **Skip/None payload persisted** (a half-serialized event written) | mirror the send path's `serialize_loop_event` `NotImplementedError` skip + `payload is None` skip BEFORE the persist; the persist sits after the skip checks |
| **Persist failure breaks the live resume stream** | `_persist_main_event` is already best-effort (SAVEPOINT + swallow/log); a failure degrades to "not persisted", never breaks the stream (same as the send path) |
| **Multi-tenant leak** (cross-tenant resume persistence) | persist scoped to the session's `tenant_id` (from `current_tenant`); a cross-tenant resume test asserts no write to another tenant |
| **Risk Class E** — stale `--reload` backend serves pre-edit `router.py` during the drive-through | clean restart (`Win32_Process` PID/PPID/StartTime sweep; orphan spawn-workers on :8000); confirm fresh sole owner + startup log before trusting the UI |
| **Risk Class C** — test DB session/singleton across event loops | the new test uses the integration `get_db_session` override / autouse reset; no module singleton touched |
| **HITL drive-through setup** (triggering a real pause needs an escalating tool + matching per-tenant policy) | use a known escalating path (a destructive/HIGH-risk tool under acme-prod's HITL policy — per the 57.122/124 HITL work the per-tenant policy + tool risk are wired); if hard to trigger live, document the exact tool + policy used |
| **Pre-existing billing flake** (`AD-Billing-Outbox-Drain-Test-Flake`) may surface once in the full run | re-run confirms 2720+5 (do NOT skip the test); the new test is unrelated |

## 9. Out of Scope (this sprint; → separate slices / ADs)

- **The approval-decision-as-replay-event** (the fuller scope) — rejected by the user (minimal scope); the decision is auditable in `approvals` + audit-log.
- **Touching the `messages` Cat-3 ledger** — already covers resume (shared `_run_turns` → `_persist_to_ledger`, 57.127).
- **Persisting error/cancelled resumes** — best-effort, only what `loop.resume()` yields on a clean continuation.
- **Subagent sidechain post-resume persistence** — sidechains spawn during the initial run, not post-resume; out of scope.
- **`message_events`/`messages` consolidation** — the dual-ledger is intentional (different consumers); a future canonical-ledger AD.
- **`AD-ChatV2-Ledger-Tool-RoundTrips`** (57.127 carryover) — the `messages` ledger's intra-turn tool round-trips; separate.
- **ANY frontend / CSS / Vitest / wire / codegen / migration change** (pure backend; the existing `mergeEvent` replay already handles the resume event types).
