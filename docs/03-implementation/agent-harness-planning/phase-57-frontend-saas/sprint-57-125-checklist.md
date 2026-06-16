# Sprint 57.125 — Checklist (chat-v2 session history replay, arc slice 1 of 2: backend SSE transcript persistence + replay endpoint. **Day-0 re-scope**: the session-LIST backend was already shipped by 57.107 B3; the residual gap is that clicking a historical session doesn't load its conversation, because the main SSE stream is unpersisted. **Writer**: persist the exact serialized main-session SSE payload to `message_events` mirroring the 57.107 sidechain observer — best-effort SAVEPOINT, `MAIN_TRANSCRIPT_OBSERVER` env-gate, monotonic `main_seq`, NO migration. **Reader**: `GET /api/v1/sessions/{id}/events` ordered replay endpoint. Backend-only; gate + probe (NOT a UI drive-through — that is 57.126). CHANGE-092 + design note 37)

[Plan](./sprint-57-125-plan.md)

---

## Day 0 — Plan-vs-Repo Verify (三-prong; the central check = D-serialize-skip-set + D-main-writer-absent) + Branch

### 0.1 Three-prong Day-0 verify (against `main` HEAD `486db0ed`) — catalogue in progress.md
- [x] **Prong 1 — path verify** ✅ all anchors present; `GET /{id}/events` undefined; `CHANGE-092`/note-`37` free
- [x] **Prong 2 — content verify** (drift findings → progress.md):
  - [x] **D-main-writer-absent** ✅ confirmed: only `router.py:525` (sidechain, keyed subagent_id) writes message_events → main rows net-new, no collision
  - [x] **D-serialize-skip-set** ✅: only `Thinking` → None (skipped); reuse the same `payload` + same skip → persisted set == streamed set; token-level deltas NOT persisted (volume manageable)
  - [x] **D-conftest-gate** ✅ (→ **D2 drift**): the flags live at `tests/integration/api/conftest.py:71,78`, NOT top-level → corrected
  - [x] **D-replay-payload-shape** ✅: `{type, data}` + injected `trace_id`; contract `{type,data,sequence_num,timestamp_ms}` recorded for 57.126
  - [x] **D-event-volume** ✅ noted: Thinking skipped → turn/span/tool-level; partition-mitigated; delta-filter deferred
- [x] **Prong 3 — schema** ✅ (→ **D1 drift**): table + partitions + `messages_default` (0028) + RLS + `idx_message_events_session` exist; columns match; latest head is `0030_tenant_skills` (NOT 0028) → still **NO migration**
- [x] **D-baselines** ✅: pytest 2703+5skip · wire 24 · Vitest 892 · mockup 51 · mypy 0/370 · run_all 10/10 (trusted from 57.124 merge)
- [x] **Catalog drift** ✅: progress.md Day-0 table written (D1 head / D2 conftest path / D3 JSONB note)
- [x] **Go/no-go** ✅: GO — scope-shift 0%

### 0.2 Branch
- [x] `git checkout -b feature/sprint-57-125-chatv2-session-transcript-persistence` (from `main` `486db0ed`) ✅

---

## Day 1 — Writer: main-session transcript persistence (US-1/2)

### 1.1 `_persist_main_event` observer + env-gate (US-1/2) ✅
- [x] **`router.py`** (EDIT): `_persist_main_event(...)` mirroring `_persist_subagent_transcript` — `MAIN_TRANSCRIPT_OBSERVER` env-gate; `begin_nested()` SAVEPOINT; `MessageEvent(...payload["type"]/payload["data"])`; best-effort except; section header (Why) + MHist + Last Modified ✅
  - DoD: best-effort SAVEPOINT → a DB flake never breaks the SSE stream ✅
- [x] **`_stream_loop_events`** (EDIT): `main_seq` + `main_transcript_on` init (mirror `tool_seq`/`sidechain_seq`); persist call before the `yield` reusing the computed `payload` (incl. active_skill); `None`/skip handled by the prior `continue` (Thinking) ✅
  - DoD: persisted set == streamed set ✅ (writer test: Thinking skipped, 3 rows for 4 yields)
- [x] **`+from typing import Any`** (helper param type); `payload["data"]` JSON-native (D3 resolved) ✅

### 1.2 Test isolation (US-2) ✅
- [x] **`tests/integration/api/conftest.py`** (EDIT — D2-corrected path): `MAIN_TRANSCRIPT_OBSERVER` `setdefault("false")` (mirror `SUBAGENT_TRANSCRIPT_OBSERVER`) ✅
  - Verify: regression 32 passed (sessions_list + observer + chat router); full pytest no row leak ✅

### 1.3 Writer tests (US-4 part 1) ✅
- [x] **`test_main_transcript_persist.py`** (NEW, co-located at `tests/integration/api/` with the sibling observer test — planned `v1/chat/` subdir was empty/no-conftest → moved): 4 tests — ordered rows + Thinking-skip / env-off no rows / main-vs-sidechain session_id separation / cross-tenant invisible ✅
  - Verify: `pytest tests/integration/api/test_main_transcript_persist.py -q` → **4 passed** ✅

### 1.4 Backend gate (partial) ✅
- [x] black/isort ✅ · flake8 clean ✅ · mypy `src` **0/370** ✅ · new tests 8 passed ✅

---

## Day 2 — Reader: replay endpoint (US-3) + stale-ref cleanup (US-6)

### 2.1 `GET /sessions/{id}/events` replay endpoint (US-3) ✅
- [x] **`sessions.py`** (EDIT): `+MessageEvent` import; `SessionEventItem` + `SessionEventsResponse`; `@router.get("/{session_id}/events")` (`list_session_events`) inline `select(MessageEvent).order_by(sequence_num)` (mirror `get_state_snapshot` RLS + redundant tenant filter); cross-tenant/new → 200 + `[]` (NOT 404); MHist ✅
  - DoD: ordered replay; empty-on-cross-tenant; empty-vs-404 difference documented in the docstring ✅
- [x] **`sessions.py` docstring** (EDIT): LIST backend (done 57.107) vs history-replay (this arc) clarified ✅

### 2.2 Reader tests (US-4 part 2) ✅
- [x] **`test_sessions_events.py`** (NEW): 4 tests — ordered (seeded out-of-order) / empty-new / cross-tenant-empty-not-404 / unknown-empty + item shape `{type,data,sequence_num,timestamp_ms}` ✅
  - Verify: `pytest tests/integration/api/test_sessions_events.py -q` → **4 passed** ✅

### 2.3 Stale-ref cleanup (US-6) ✅
- [x] **`next-phase-candidates.md:495`** (EDIT): `AD-ChatV2-SessionList-Backend` RESOLVED-by-57.107 note + `AD-ChatV2-Session-History-Replay-Phase58` arc ✅

### 2.4 Backend gate (full) ✅
- [x] black/isort ✅ · flake8 clean ✅ · mypy `src` **0/370** ✅ · run_all **10/10** (count 24) ✅ · **full backend pytest 2711 passed/5 skipped** (baseline 2703+5 → **+8**) ✅ · Vitest 892 UNCHANGED ✅ · mockup 51 UNCHANGED ✅ · migrations/events/sse/codegen/frontend UNTOUCHED ✅ · Alembic head still `0030` (D1-corrected) ✅

---

## Day 3 — Backend probe (US-5) — real chat + real backend (NOT a UI drive-through)

### 3.1 Clean restart / probe-readiness (Risk Class E — `router.py`/`sessions.py` changed) ✅
- [x] Killed stale :8000 (PID 43064 reloader + 39620 worker, 57.124 OLD code) → fresh no-reload PID 44960 sole owner + "startup complete"; `MAIN_TRANSCRIPT_OBSERVER` default on; Vite :3007 NOT stopped ✅
  - DoD: `GET /sessions/{id}/events` reachable on the NEW code ✅

### 3.2 Backend probe (gate + probe; honest non-drive-through) ✅
- [x] real-LLM chat (dev-login probe57125 → `POST /chat {mode: real_llm, session_id}`) → 16 events streamed ✅
- [x] `GET /events` → **16 rows ordered 1..16**; **streamed == persisted (order+type) TRUE** (full fidelity); item shape `{type,data,sequence_num,timestamp_ms}`; unknown session → 200 `[]` ✅
- [x] observed-vs-intended → progress.md Day 3; **honest status: gate + probe of a backend foundation, NOT a UI drive-through** (UI = 57.126) ✅

---

## Day 4 — CHANGE-092 + design note 37 + closeout

### 4.1 CHANGE-092 + design note 37 ✅
- [x] **`CHANGE-092-chatv2-session-transcript-persistence.md`** (writer + reader + probe + arc context + test delta) ✅
- [x] **`37-chatv2-session-transcript-persistence.md`** (spike-extract; 8-pt gate ~95%: persistence semantics + `{type,data,sequence_num,timestamp_ms}` replay contract for 57.126 + empty-vs-404 reader decision + rollback) ✅

### 4.2 Closeout
- [x] retrospective.md Q1-Q7 + calibration (`chatv2-transcript-persistence-spike` 0.60, parent-direct; 1st data point ratio ~1.0) + progress.md final + Design-Note-Extract self-check (§5.5) ✅
- [x] Final gate sweep: mypy **0/370** · run_all **10/10** (count 24) · full pytest **2711+5skip** (+8) · Vitest 892 UNCHANGED · mockup 51 UNCHANGED ✅
- [x] Navigators: CLAUDE.md Current-Sprint + Last-Updated ✅ · MEMORY.md pointer + subfile `project_phase57_125_*` ✅ · next-phase-candidates (`AD-ChatV2-SessionList-Backend` resolved + `AD-ChatV2-Session-History-Replay-Phase58` backend half + 57.126 logged NOT pre-written) ✅ · sprint-workflow matrix `chatv2-transcript-persistence-spike` row ✅
- [x] **Anti-pattern self-check** (retro Q5): AP-2 / AP-4 / AP-3 / AP-6 → 0 violations; v2 lints 10/10 ✅
- [ ] PR (push + open) — local commits done; **awaiting user confirm before `git push`** (destructive-confirm rule); CI → merge on green (gh-verified MERGED before main sync)
