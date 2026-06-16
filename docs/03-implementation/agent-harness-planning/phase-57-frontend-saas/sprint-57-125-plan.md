# Sprint 57.125 Plan — chat-v2 session history replay (arc slice 1 of 2: backend SSE transcript persistence + replay endpoint). **Day-0 re-scope**: `AD-ChatV2-SessionList-Backend`'s LITERAL scope — the session-LIST backend — was ALREADY shipped by Sprint 57.107 B3 (`GET /api/v1/sessions` is real, `SessionList.tsx` is wired to `loadSessions()`, the DEMO banner is dropped, "New session" → `reset()` is no longer a dead control, the count is real). The carryover line (`next-phase-candidates.md:495` "still DEMO-labelled / backend list endpoint still pending") is **STALE**. The genuine residual gap (confirmed by reading the code): clicking a historical session (`SessionList.tsx:70` → `setActiveSessionId`) only HIGHLIGHTS it and does NOT load/render that session's past conversation — a soft Potemkin (a visible selection effect, no functional effect), because the main-session SSE event stream is NOT persisted anywhere (`message_events` is written ONLY for subagent sidechains; the `messages` table has no main-flow writer; the only persisted main conversation is `state_snapshots.state_data`, the resume LLM-message list, not the rich chat-v2 Turn stream). **User's Option-B choice (2026-06-16)**: full-fidelity SSE persist + replay (~2-sprint arc), NOT a lossy transcript. **This slice 1 (backend)**: persist the EXACT serialized main-session SSE event payload to the existing `message_events` table — mirroring the proven 57.107 `_persist_subagent_transcript` observer (best-effort SAVEPOINT, env-gated, `serialize_loop_event` → `MessageEvent` row, monotonic `sequence_num`); **NO migration** (the table + monthly partitions + the 0028 `messages_default` catch-all already exist) — plus a `GET /api/v1/sessions/{id}/events` replay endpoint returning the ordered event stream. **Slice 2 (57.126, NOT pre-written)**: the frontend — click → fetch `/events` → replay through the existing 18-case `mergeEvent` reducer → render the full historical Turn stream + route the continuation. Backend-only this sprint; verified by gate + endpoint integration tests + a real-chat DB-row probe (honest: **gate + probe, NOT a UI drive-through** — no user-facing surface lands until 57.126). CHANGE-092 + design note 37 (spike-extract). NO migration / wire (count 24) / codegen / frontend / `styles-mockup.css`.

**Status**: Approved-to-execute (user 2026-06-16: "開始執行 A 組 `AD-ChatV2-SessionList-Backend`" → Day-0 探勘 re-scoped it to the history-replay residual gap → user picked **Option B (full SSE persist + replay, ~2-sprint arc)** via AskUserQuestion 2026-06-16).
**Branch**: `feature/sprint-57-125-chatv2-session-transcript-persistence`
**Base**: `main` HEAD `486db0ed` (post-#299 — Sprint 57.124 HITL gate consolidation).
**Slice**: arc slice 1 of 2 under a re-scoped AD `AD-ChatV2-Session-History-Replay-Phase58` (NEW — the genuine residual gap). The literal `AD-ChatV2-SessionList-Backend` (the session LIST backend) is **confirmed already-done by Sprint 57.107 B3** and is closed as resolved this sprint (stale `next-phase-candidates.md:495` + `sessions.py` docstring corrected).
**Scope decisions** (AskUserQuestion 2026-06-16): (a) **Option B** — full-fidelity SSE persistence + replay (NOT the lossy `state_snapshots`-transcript Option A, NOT the honest-disable Option C); the design persists the EXACT serialized SSE payload so slice-2 replay through the live `mergeEvent` reducer reconstructs pixel-identical historical turns. (b) **2-sprint arc**, this sprint = backend (writer + replay endpoint), 57.126 = frontend (NOT pre-written, rolling discipline). (c) The writer MIRRORS the proven `_persist_subagent_transcript` (57.107) — same `message_events` table, same best-effort SAVEPOINT, same env-gate pattern, a NEW `main_seq` counter; main rows are keyed `session_id={main session}` (sidechain rows are keyed `session_id={subagent_id}`) so the two streams are cleanly separated by `session_id`. (d) NO migration (table + partitions exist) / NO new wire event / NO codegen / NO frontend / NO `styles-mockup.css`; this is a backend-only foundation sprint (gate + probe verification, honestly NOT a UI drive-through).

---

## 0. Background

### The Day-0 re-scope (why the AD's one-line is stale)

`AD-ChatV2-SessionList-Backend` was logged in the 2026-06-06 drive-through audit (`next-phase-candidates.md:495`) as "chat-v2 session list still DEMO-labelled (correct/honest); backend list endpoint still pending". That snapshot was taken BEFORE Sprint 57.107 B3 (2026-06-12). Two Explore sweeps + direct reads on `main` HEAD `486db0ed` confirm 57.107 already shipped the LIST backend:

| Sub-gap | 2026-06-06 audit state | Current state (HEAD `486db0ed`) |
|---------|------------------------|----------------------------------|
| `GET /api/v1/sessions` backend | "still pending" | ✅ REAL — `sessions.py:86-112` (`list_sessions`, per-tenant, newest-first, sidechains excluded, lineage fields) |
| `SessionList.tsx` data source | fixture (`FIXTURE_SESSIONS`) | ✅ real `chatStore.loadSessions()` on mount (`SessionList.tsx:124-129`) |
| DEMO banner / fixture honesty | DEMO-labelled fixture | ✅ banner dropped (data is real) — `SessionList.tsx:37` MHist |
| "New session" button | dead control (no onClick) | ✅ `onClick={() => reset()}` (`SessionList.tsx:147`) |
| session count | hardcoded | ✅ `sessions.length` (`SessionList.tsx:183`) |

So the literal AD is **done**. The genuine residual gap surfaced by reading `SessionItem` (`SessionList.tsx:58-115`): clicking a session row calls `setActiveSessionId(session.id)` (`:70`) — which sets the highlight only. The conversation pane renders `chatStore.turns`, which the click does NOT change → **clicking a historical session highlights it but shows the wrong/empty conversation** (a soft Potemkin: visible selection, no functional "open this conversation" effect).

### Why full history-replay needs SSE persistence first (the missing foundation)

Loading a historical session's conversation requires a persisted source to rebuild the chat-v2 Turn stream from. Day-0 Prong-2 content-verify established the persistence reality:

- **`message_events`** (`sessions.py:223-267`, partitioned monthly + `messages_default`) — currently written ONLY for subagent sidechains, by `_persist_subagent_transcript` (`router.py:469-548`, "first real consumer of that table", keyed `session_id=subagent_id`). The MAIN session's events are NOT persisted.
- **`messages`** (`sessions.py:163-217`) — schema exists, but has NO main-flow writer (no `MessageRepository`; grep `backend/src/api/v1/chat` shows no main-path `messages` insert).
- **`state_snapshots.state_data`** (`state.py:75-107`) — the only persisted main conversation, but it is the LLM message list (system/user/assistant/tool) used by `resume()` (`router.py:1211`), NOT the rich SSE-derived chat-v2 Turn (no verification/thinking/inspector streaming detail). Rebuilding `turns` from it = lossy (the rejected Option A).

The user chose **Option B**: persist the EXACT serialized SSE payload that already streams to the frontend (`payload = serialize_loop_event(event)` at `router.py:648`), so slice-2 replay feeds those identical payloads through the live 18-case `mergeEvent` reducer and reconstructs pixel-identical historical turns. The elegance: the writer reuses the already-computed `payload`; the reader returns it ordered; the frontend reducer is unchanged.

### The proven pattern this mirrors (de-risks the writer)

`_persist_subagent_transcript` (`router.py:477-548`, Sprint 57.107) is the template: a best-effort observer inside `_stream_loop_events`, `async with db.begin_nested()` SAVEPOINT (a DB flake never breaks the SSE stream), env-gated (`SUBAGENT_TRANSCRIPT_OBSERVER`, default on; `tests/conftest.py` sets false for isolation), `serialize_loop_event(ev)` → `MessageEvent(session_id=, tenant_id=, event_type=payload["type"], event_data=payload["data"], sequence_num=, timestamp_ms=)`, with a monotonic per-stream `sequence_num` (`sidechain_seq` dict). This sprint adds the symmetric MAIN-session writer: a single `main_seq` counter + a `MAIN_TRANSCRIPT_OBSERVER` env-gate, persisting the same `payload` already serialized for the SSE frame.

### Ground truth (Day-0 head-start — direct reads on `main` HEAD `486db0ed`; ALL re-verified in the formal Day-0 三-prong §checklist 0.1)

**Writer anchors:**
- `api/v1/chat/router.py:576-649` — `_stream_loop_events`; the `async for event in loop.run(...)` loop; `payload = serialize_loop_event(event)` at `:648` (reuse it); existing per-stream counters `tool_seq` (`:615`) + `sidechain_seq` (`:618`) to mirror with a new `main_seq`.
- `api/v1/chat/router.py:114` — `from infrastructure.db.models.sessions import MessageEvent` (already imported).
- `api/v1/chat/router.py:469-548` — `_persist_subagent_transcript` (the pattern to mirror, incl. the `SUBAGENT_TRANSCRIPT_OBSERVER` env-gate + `begin_nested` SAVEPOINT + `serialize_loop_event` skip handling for `None`/`NotImplementedError`).
- `serialize_loop_event` / `format_sse_message` — already imported in `router.py` (used at `:517,567,648`); some events return `None` / raise `NotImplementedError` → skipped for SSE AND for persistence (same skip).
- `tests/conftest.py` — where `SUBAGENT_TRANSCRIPT_OBSERVER` / `SESSIONS_CHAT_OBSERVER` are set false for test isolation (add `MAIN_TRANSCRIPT_OBSERVER=false`).

**Reader anchors:**
- `api/v1/sessions.py:115-166` — `get_state_snapshot` (`GET /sessions/{id}/state`): the closest sibling read endpoint — same file, same `get_current_tenant` + `get_db_session_with_tenant` (RLS) deps, same inline `select(...).where(session_id, tenant_id)` + cross-tenant-404 pattern. Mirror it for `GET /sessions/{id}/events`.
- `api/v1/sessions.py:60` — `from infrastructure.db.models.state import StateSnapshot`; add the `MessageEvent` import.
- `infrastructure/db/models/sessions.py:223-267` — `MessageEvent` ORM (columns: `session_id`, `tenant_id`, `event_type`, `event_data` JSONB, `sequence_num` BigInteger, `timestamp_ms` BigInteger, `created_at`; composite PK `(id, created_at)`; partitioned; RLS via TenantScopedMixin).

**Baselines (57.124 closeout)**: full pytest **2703+5skip** · wire **24** · Vitest **892** (FE untouched this sprint) · mockup-fidelity **51** (FE untouched) · mypy `src` **0/370** · run_all **10/10**. Re-verify Day-0.

### STALE / drift anchors to re-confirm in the formal Day-0 三-prong (§ checklist 0.1)

(1) **Prong-1 path**: all writer/reader anchors above exist; `tests/conftest.py` env-gate block exists; the new test homes + `CHANGE-092-*.md` + design-note `37-*.md` free; `GET /sessions/{id}/events` route NOT already defined. (2) **Prong-2 content** — the linchpins:
- **D-main-writer-absent (⚠️ confirms the gap)**: grep proves `message_events` has NO main-session writer today (only `_persist_subagent_transcript` keyed `session_id=subagent_id`) → main rows are net-new, no collision with sidechain rows.
- **D-serialize-skip-set**: enumerate which `LoopEvent` types `serialize_loop_event` returns `None`/raises `NotImplementedError` for (skipped) — confirm the persisted set == the SSE-streamed set (replay fidelity = exactly what the user saw live).
- **D-conftest-gate**: confirm `tests/conftest.py` sets the sibling observer flags false → add `MAIN_TRANSCRIPT_OBSERVER=false` so existing chat integration tests don't suddenly write rows (and the one new writer test sets it true explicitly).
- **D-replay-payload-shape**: confirm the persisted `payload["data"]` shape == what the frontend SSE parser consumes, so slice-2's reducer-replay contract is `{type, data}` (record it for the 57.126 plan; no frontend work this sprint).
- **D-event-volume**: note the per-chat event count (thinking/llm_request/tool/verification/turn events) → row-volume risk (partitioned table mitigates; a delta-filter is a deferred follow-up, NOT this sprint).
(3) **Prong-3 schema**: `message_events` table + monthly partitions + `messages_default` (0028) exist; RLS present; columns match the writer — **NO migration**. Confirm the latest Alembic head is `0028_sidechain_sessions` (no new migration consumed). (4) Baselines re-verify (pytest 2703+5skip / wire 24 / Vitest 892 / mockup 51 / mypy 0/370 / run_all 10/10). (5) A real-chat probe plan: drive one real-LLM chat → assert `message_events` rows accumulate for the MAIN `session_id` → `GET /sessions/{id}/events` returns them ordered (the backend-only verification; honestly NOT a UI drive-through).

## 1. Sprint Goal

The main-session chat SSE event stream is durably persisted to `message_events` (mirroring the proven 57.107 sidechain observer — best-effort SAVEPOINT, env-gated, the exact serialized SSE payload, a monotonic `main_seq`; NO migration) and is readable back, ordered, via a new `GET /api/v1/sessions/{id}/events` replay endpoint (tenant-scoped, RLS, cross-tenant-404). This is the backend foundation (arc slice 1 of 2) for chat-v2 historical-session replay; the frontend replay UI is slice 2 (57.126, not pre-written). Closes the re-scoped `AD-ChatV2-Session-History-Replay-Phase58` backend half + formally closes the stale `AD-ChatV2-SessionList-Backend` (the LIST backend was already shipped by 57.107). Proven by: integration tests (a real-LLM chat writes ordered main-session rows; env-gate off → no rows; the endpoint returns the ordered stream; cross-tenant → 404) + a real-chat DB-row probe (gate + probe, honestly NOT a UI drive-through — no user-facing surface this sprint). NO migration / wire (24) / codegen / frontend / `styles-mockup.css`. CHANGE-092 + design note 37.

## 2. User Stories

- **US-1** (writer): 作為 chat 主流量 `_stream_loop_events`，我希望每個 main-session SSE 事件以已序列化的 `payload` 持久化到 `message_events`（`session_id=主 session`、monotonic `main_seq`、best-effort SAVEPOINT、env-gated），以便歷史對話有 full-fidelity 的重播來源（鏡像 57.107 sidechain observer）。
- **US-2** (env-gate + isolation): 作為 test/ops，我希望主 transcript 寫入由 `MAIN_TRANSCRIPT_OBSERVER`（default on）控制、且 `tests/conftest.py` 預設 false，以便既有 chat 測試的 DB 隔離不受影響（鏡像 `SUBAGENT_TRANSCRIPT_OBSERVER`）。
- **US-3** (reader): 作為前端（slice 2）/ ops，我希望 `GET /api/v1/sessions/{id}/events` 回傳該 session 依 `sequence_num` 排序的事件流（tenant-scoped、RLS、cross-tenant→404），以便重播歷史對話。
- **US-4** (tests): 作為 platform，我希望測試守住：writer（真事件寫成 ordered rows / env-off 無 rows / sidechain 與 main 由 session_id 分離）+ reader（空 session 回空 / ordered / cross-tenant 404 / RLS）。
- **US-5** (backend probe): 作為 dev，我希望真 backend 驗證：跑一個 real-LLM chat → `message_events` 主 session rows 累積 → `GET /sessions/{id}/events` 回傳同一 ordered 流（誠實標 **gate + probe，非 UI drive-through**；UI 在 57.126）。
- **US-6** (stale-ref cleanup): 作為 codebase，我希望更正 stale 參照（`next-phase-candidates.md:495` 標 `AD-ChatV2-SessionList-Backend` 已由 57.107 解決 + `sessions.py` docstring 釐清 LIST vs history），以便 AD 帳實相符（Karpathy no-orphan-claims）。
- **US-7** (closeout): 作為 future dev，我希望 CHANGE-092 + 設計筆記 37（spike-extract：persistence 語意 + replay-payload 契約 + 57.126 介面 + rollback）+ 收尾，以便此 2-sprint arc 可溯且 57.126 有穩定契約可接。

## 3. Technical Specifications

### 3.0 Architecture (backend-only Cat 12 persistence + Cat 7-adjacent read; NO migration / wire / codegen / frontend)

```
# Writer (Cat 12 observability/persistence, in the chat router)
backend/src/api/v1/chat/router.py        (EDIT): _persist_main_transcript observer + main_seq + MAIN_TRANSCRIPT_OBSERVER env-gate; called in _stream_loop_events per event (reuse the already-computed payload)
# Reader (api facade, sibling of get_state_snapshot)
backend/src/api/v1/sessions.py           (EDIT): GET /sessions/{id}/events + SessionEventItem / SessionEventsResponse (inline select(MessageEvent), mirror get_state_snapshot RLS + cross-tenant-404)
# Test isolation
backend/tests/conftest.py                (EDIT): MAIN_TRANSCRIPT_OBSERVER=false (mirror SUBAGENT_TRANSCRIPT_OBSERVER)
# Tests
backend/tests/integration/api/v1/chat/test_*main_transcript*.py   (NEW): writer — real events → ordered rows; env-off → no rows; main/sidechain session_id separation
backend/tests/integration/api/test_sessions_events*.py            (NEW): reader — empty / ordered / cross-tenant 404 / RLS
# Stale-ref cleanup
claudedocs/1-planning/next-phase-candidates.md  (EDIT): AD-ChatV2-SessionList-Backend resolved-by-57.107 note + this arc
backend/src/api/v1/sessions.py                  (EDIT, same file): docstring LIST-vs-history clarification
# docs
claudedocs/4-changes/feature-changes/CHANGE-092-*.md            (NEW)
docs/.../37-chatv2-session-transcript-persistence.md            (NEW design note — spike-extract, 8-pt gate)
migrations / events.py / sse.py / codegen / frontend / styles-mockup.css: UNTOUCHED
```

### 3.1 Writer — main-session transcript observer (US-1) — `router.py`

- Add `_persist_main_transcript(events_or_payloads, *, db, tenant_id, session_id, main_seq_ref)` mirroring `_persist_subagent_transcript`: env-gate `MAIN_TRANSCRIPT_OBSERVER` (default `"true"`); `if db is None: return`; `async with db.begin_nested():` per event → `MessageEvent(session_id=session_id, tenant_id=tenant_id, event_type=payload["type"], event_data=payload["data"], sequence_num=main_seq, timestamp_ms=int(time.time()*1000))`; `except Exception: logger.exception(... best-effort)`.
- **Reuse the already-serialized `payload`**: inside the `_stream_loop_events` `async for` loop, the SSE `payload = serialize_loop_event(event)` is already computed (`:648`) before the frame is yielded. Persist using THAT payload (no double-serialize); skip when `payload is None` (the SSE path already skips `None`/`NotImplementedError`) → the persisted set == the streamed set (replay fidelity).
- `main_seq`: a per-request monotonic counter (like `tool_seq`/`sidechain_seq`); increment per persisted event so the reader can `ORDER BY sequence_num`.
- Placement: persist the main event in the same loop iteration that yields its SSE frame, AFTER `serialize_loop_event` succeeds, BEFORE/AFTER the yield (best-effort either way; persist before yield so a persist failure is logged before the byte leaves — but the SAVEPOINT means it never blocks the yield). Document the exact insertion point in progress.md.
- Multi-tenant: `tenant_id` on every row (table RLS via TenantScopedMixin). `session_id` = the MAIN session (≠ the sidechain `subagent_id` rows → clean separation by `session_id`).

### 3.2 Env-gate + test isolation (US-2) — `router.py` + `conftest.py`

- `MAIN_TRANSCRIPT_OBSERVER` default `"true"` (production persists). `tests/conftest.py` sets it `"false"` (mirror `SUBAGENT_TRANSCRIPT_OBSERVER` / `SESSIONS_CHAT_OBSERVER`) so existing chat integration tests don't write rows (and don't need partition coverage assertions). The one new writer test sets it `"true"` explicitly (monkeypatch/env) to exercise the path.

### 3.3 Reader — replay endpoint (US-3) — `sessions.py`

- `GET /api/v1/sessions/{session_id}/events` → `SessionEventsResponse(events=[SessionEventItem(type, data, sequence_num, timestamp_ms), ...])`. Inline `select(MessageEvent).where(session_id==, tenant_id==).order_by(MessageEvent.sequence_num)` (mirror `get_state_snapshot`'s inline select + RLS + redundant app-layer `tenant_id` filter). 
- **Cross-tenant / not-found semantics**: an unknown or cross-tenant `session_id` returns an **empty list** (RLS + tenant filter naturally yield 0 rows) — NOT a 404, because "no events yet" (a brand-new session) and "cross-tenant" are both legitimately empty and indistinguishable, which satisfies the multi-tenant 鐵律 (never reveal cross-tenant existence). (Contrast `get_state_snapshot`, which 404s because a session with zero snapshots is an error there; here zero events is a valid state.) Document this deliberate difference.
- `SessionEventItem`: `type: str`, `data: dict[str, Any]`, `sequence_num: int`, `timestamp_ms: int` — the exact persisted payload (the slice-2 reducer-replay contract).

### 3.4 New tests (US-4, the safety net)

- **Writer** (`test_*main_transcript*.py`): with `MAIN_TRANSCRIPT_OBSERVER=true`, drive a chat (echo_demo or a stubbed loop emitting ≥2 events) → assert `message_events` rows exist for the MAIN `session_id`, with `event_type` matching the streamed events and `sequence_num` monotonic 1..N; with the gate `false` → 0 rows; a run with a subagent → main rows (session_id=main) and sidechain rows (session_id=subagent_id) coexist without collision.
- **Reader** (`test_sessions_events*.py`): a session with persisted events → `GET /events` returns them ordered by `sequence_num`; a brand-new session id → `{events: []}`; a cross-tenant session id → `{events: []}` (RLS, not 404); the response item shape == `{type, data, sequence_num, timestamp_ms}`.

### 3.5 Backend probe (US-5) — real chat + real backend (NOT a UI drive-through)

1. Clean restart (Risk Class E — `router.py`/`sessions.py` changed; `Win32_Process` PID/PPID/StartTime sweep; confirm the fresh PID is the sole :8000 owner + a startup log line; `MAIN_TRANSCRIPT_OBSERVER` on). Vite :3007 (node) NOT stopped.
2. Drive ONE real-LLM chat via the API (or chat-v2 UI to generate a real session) → note the `session_id`.
3. Query the DB (or the new endpoint) → `message_events` for that `session_id` has the ordered event stream; `GET /api/v1/sessions/{session_id}/events` returns the same ordered payloads.
4. Record observed-vs-intended in progress.md. **Honest status**: this is a **gate + probe** verification of a backend foundation (no user-facing UI lands this sprint) — explicitly NOT a UI drive-through (that is 57.126's DoD). Per CLAUDE.md §Drive-Through, a pure-backend foundation is exempt from the UI drive-through but MUST be reported "gate + probe verified", not "verified / X% working".

### 3.6 What is explicitly NOT done

The frontend (click → fetch `/events` → reducer-replay → render historical turns + route continuation) — that is slice 2 (57.126, not pre-written); a delta-filter to reduce persisted row volume (thinking deltas etc. — a deferred optimization; the partitioned table absorbs volume for now); reconstructing turns from `state_snapshots` (the rejected lossy Option A); any `messages`-table writer (unused this arc); a retention/TTL policy on `message_events` (Phase 58+); any migration / new wire event / codegen / frontend / `styles-mockup.css` change.

### 3.7 Validation (US-1..US-7)

Gates: mypy strict `src` **0/370** · run_all **10/10** (count 24) · full pytest **2703+5skip + N** (writer + reader tests added; document the delta) · Vitest **892 UNCHANGED** (no FE) · mockup-fidelity **51 UNCHANGED** (no FE) · migrations / events / sse / codegen / frontend **UNTOUCHED** (latest Alembic head still `0028`). Plus: the §3.4 integration tests prove the writer persists the ordered stream + the reader returns it; the §3.5 probe proves a real chat writes real main-session rows readable via the endpoint.

## 4. File Change List

| # | File | Action |
|---|------|--------|
| 1 | `backend/src/api/v1/chat/router.py` | EDIT — `_persist_main_transcript` observer + `main_seq` + `MAIN_TRANSCRIPT_OBSERVER` env-gate; persist the already-serialized `payload` per event in `_stream_loop_events` |
| 2 | `backend/src/api/v1/sessions.py` | EDIT — `GET /sessions/{id}/events` + `SessionEventItem`/`SessionEventsResponse` (inline `select(MessageEvent)`, RLS, empty-on-cross-tenant); + `MessageEvent` import; + docstring LIST-vs-history clarification |
| 3 | `backend/tests/conftest.py` | EDIT — `MAIN_TRANSCRIPT_OBSERVER=false` (mirror `SUBAGENT_TRANSCRIPT_OBSERVER`) |
| 4 | `backend/tests/integration/api/v1/chat/test_main_transcript_persist.py` | NEW — writer: ordered rows / env-off no rows / main-vs-sidechain session_id separation |
| 5 | `backend/tests/integration/api/test_sessions_events.py` | NEW — reader: empty / ordered / cross-tenant empty / item shape |
| 6 | `claudedocs/1-planning/next-phase-candidates.md` | EDIT — `AD-ChatV2-SessionList-Backend` resolved-by-57.107 note + this arc (`AD-ChatV2-Session-History-Replay-Phase58`) |
| 7 | `claudedocs/4-changes/feature-changes/CHANGE-092-chatv2-session-transcript-persistence.md` | NEW — change record (writer + reader + probe + arc context) |
| 8 | `docs/03-implementation/agent-harness-planning/37-chatv2-session-transcript-persistence.md` | NEW — design note (spike-extract; 8-pt gate; persistence semantics + replay-payload contract + 57.126 interface + rollback) |
| — | migrations / `events.py` / `sse.py` / codegen / frontend / `styles-mockup.css` | **UNTOUCHED / NONE** |

## 5. Acceptance Criteria

1. **Writer**: with `MAIN_TRANSCRIPT_OBSERVER` on, a chat run persists each streamed main-session SSE event to `message_events` (`session_id`=main session, `sequence_num` monotonic, `event_type`/`event_data` == the serialized payload); the writer is a best-effort SAVEPOINT (a persist failure never breaks the SSE stream); env-gate off → 0 rows.
2. **Reader**: `GET /api/v1/sessions/{id}/events` returns the session's events ordered by `sequence_num`; a new/cross-tenant session → `{events: []}` (RLS, not 404); item shape == `{type, data, sequence_num, timestamp_ms}`.
3. **Separation**: main rows (`session_id`=main) and sidechain rows (`session_id`=subagent_id) coexist without collision (integration test with a subagent).
4. **No migration**: latest Alembic head still `0028_sidechain_sessions`; `message_events` columns/RLS unchanged; `grep` shows no new migration file.
5. **Stale-ref**: `next-phase-candidates.md:495` corrected (`AD-ChatV2-SessionList-Backend` resolved-by-57.107); `sessions.py` docstring clarifies LIST (done) vs history-replay (this arc).
6. Gates: mypy 0/370 · run_all 10/10 (count 24) · pytest 2703+5skip + documented delta · Vitest 892 UNCHANGED · mockup 51 UNCHANGED · migrations/events/sse/codegen/frontend UNTOUCHED.
7. Backend probe PASS (gate + probe, **NOT a UI drive-through**): a real-LLM chat writes ordered main-session `message_events` rows readable via `GET /sessions/{id}/events`; recorded honestly in progress.md.
8. `AD-ChatV2-Session-History-Replay-Phase58` backend half shipped + `AD-ChatV2-SessionList-Backend` closed-as-resolved; CHANGE-092 + design note 37; calibration recorded (`chatv2-transcript-persistence-spike` 0.60, parent-direct `agent_factor` 1.0); navigators + next-phase-candidates updated; 57.126 (frontend replay) logged as the next arc slice (NOT pre-written).

## 6. Deliverables

- [ ] US-1 `_persist_main_transcript` writer + `main_seq` + reuse the serialized `payload` (`router.py`)
- [ ] US-2 `MAIN_TRANSCRIPT_OBSERVER` env-gate (default on) + `conftest.py` false
- [ ] US-3 `GET /sessions/{id}/events` replay endpoint + Pydantic models (`sessions.py`)
- [ ] US-4 writer tests (ordered rows / env-off / main-vs-sidechain) + reader tests (empty / ordered / cross-tenant / shape)
- [ ] US-5 backend probe (real chat → DB rows → endpoint; gate + probe, honest non-drive-through note)
- [ ] US-6 stale-ref cleanup (`next-phase-candidates.md:495` + `sessions.py` docstring)
- [ ] US-7 CHANGE-092 + design note 37 + closeout (retro Q1-Q7 + calibration + navigators + next-phase-candidates + log 57.126 as next arc slice)

## 7. Workload Calibration

- Scope class **`chatv2-transcript-persistence-spike` 0.60** (NEW — backend SSE-stream persistence observer mirroring the proven 57.107 `_persist_subagent_transcript` + a sibling read endpoint mirroring `get_state_snapshot`; reuses an existing table/partitions/serialize machinery, NO migration). Closest existing classes: `subagent-sse-relay-wiring` 0.55 (Cat 11→12 backend composition wiring) + the read-endpoint half nudges it to 0.60. KEEP single-data-point caution; validate over 1-2 such sprints.
- **Agent-delegated: no** (parent-direct; the writer placement + the best-effort/env-gate semantics + the cross-tenant-empty-vs-404 reader decision are precise and best hand-authored + self-verified). `agent_factor` 1.0 → 3-segment form.
- Bottom-up est ~8.75 hr (Day-0 三-prong + serialize-skip-set enumeration ~0.75 · writer observer + main_seq + env-gate ~1.25 · reader endpoint + models ~1.0 · conftest gate ~0.25 · writer tests ~1.25 · reader tests ~1.25 · backend probe + clean restart ~1.0 · stale-ref cleanup ~0.25 · CHANGE-092 + design note 37 + closeout ~1.75) → class-calibrated commit ~5.25 hr (mult 0.60). Day-4 retro Q2 verifies (`chatv2-transcript-persistence-spike` 1st data point; flag if the writer placement or the probe over-runs).

## 8. Dependencies & Risks

| Risk | Mitigation |
|------|------------|
| **D-serialize-skip-set (Day-0)**: if the persisted set ≠ the SSE-streamed set, replay (57.126) drifts from what the user saw live | reuse the EXACT `payload` already computed for the SSE frame (`router.py:648`); skip when `payload is None` (same as the SSE path) → the persisted set == the streamed set by construction; Day-0 enumerate the `serialize_loop_event` `None`/`NotImplementedError` cases and record them |
| **Event volume / table growth**: persisting every event (incl. thinking/llm deltas) inflates `message_events` | the table is partitioned monthly + `messages_default` (0028) absorbs it; flag a delta-filter as a deferred follow-up AD (NOT this sprint — fidelity-first); note the per-chat row count in the probe |
| **Test isolation regression**: a default-on main observer makes existing chat integration tests write rows (partition/coverage churn) | `tests/conftest.py` sets `MAIN_TRANSCRIPT_OBSERVER=false` (mirror `SUBAGENT_TRANSCRIPT_OBSERVER`); only the new writer test flips it true; Day-0 `D-conftest-gate` confirms the conftest block |
| **Best-effort writer must never break the SSE stream** | `async with db.begin_nested()` SAVEPOINT + `except Exception: logger.exception(...)` (exact mirror of `_persist_subagent_transcript`); a writer test injects a failure and asserts the SSE stream still completes |
| **Cross-tenant reader leakage** | inline `tenant_id` filter + RLS (mirror `get_state_snapshot`); a cross-tenant session → `{events: []}` (never reveal existence); multi-tenant test asserts empty, not 404 |
| **main_seq vs sidechain_seq confusion** | they are independent per-request counters keyed by DIFFERENT `session_id`s (main vs subagent_id); a subagent integration test asserts no collision |
| **Risk Class E** — a stale `--reload` backend serves old `router.py`/`sessions.py` (no writer / no endpoint) during the probe | clean restart before the probe (`Win32_Process` PID/PPID/StartTime sweep — kill orphan spawn-workers holding :8000 via SO_REUSEADDR); confirm the fresh PID is the sole owner + a startup log line; hit `GET /events` once before trusting the result |
| **Scope creep into the frontend** | this sprint is backend-only (rolling discipline); the replay contract (`{type, data, sequence_num, timestamp_ms}`) is recorded in design note 37 for 57.126; NO frontend file is touched |
| **Pytest count moves** | document the exact added test delta in the retro; the gate asserts the final number |

## 9. Out of Scope (this sprint; → separate slices / ADs)

- **The frontend replay UI** (click → fetch `/events` → `mergeEvent` replay → render historical turns + route continuation) — arc slice 2 (`AD-ChatV2-Session-History-Replay-Phase58` frontend half), Sprint 57.126, NOT pre-written.
- **A delta-filter / event-sampling** to reduce persisted volume — deferred follow-up AD (fidelity-first this sprint).
- **A retention / TTL policy** on `message_events` — Phase 58+.
- **Reconstructing turns from `state_snapshots`** — the rejected lossy Option A.
- **Any `messages`-table writer** — unused this arc.
- Any migration / new wire event / codegen / frontend / `styles-mockup.css` change (count 24 unchanged; Alembic head `0028` unchanged).
