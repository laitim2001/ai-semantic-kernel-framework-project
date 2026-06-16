# CHANGE-092: chat-v2 session history replay — backend SSE transcript persistence + replay endpoint

**Date**: 2026-06-16
**Sprint**: 57.125
**Scope**: Cat 12 (Observability/persistence) + api/v1 (chat router writer + sessions reader) — backend-only
**AD**: `AD-ChatV2-Session-History-Replay-Phase58` (NEW, backend half) · `AD-ChatV2-SessionList-Backend` (closed-as-resolved)

## Problem

`AD-ChatV2-SessionList-Backend` was logged as "chat-v2 session list still DEMO-labelled; backend list endpoint still pending". **Day-0 re-scope**: that snapshot (2026-06-06) predated Sprint 57.107 B3 — the session LIST backend (`GET /api/v1/sessions`) + `SessionList.tsx` wiring + DEMO-drop + "New session"→`reset()` were already shipped. The genuine residual gap: clicking a historical session (`SessionList.tsx:70` → `setActiveSessionId`) only highlights it and does NOT load/render its past conversation — a soft Potemkin — because the main-session SSE event stream is unpersisted (`message_events` is written only for subagent sidechains; `messages` has no main-flow writer; only `state_snapshots.state_data` holds the resume LLM-message list, not the rich chat-v2 Turn stream).

## Root Cause

No durable, full-fidelity source for a historical chat-v2 conversation. The user chose **Option B** (full SSE persist + replay, a ~2-sprint arc) over a lossy `state_snapshots` transcript. This sprint (arc slice 1/2) is the backend foundation; the frontend replay is slice 2 (57.126).

## Solution

- **Writer** (`api/v1/chat/router.py`): `_persist_main_event` observer — mirrors the proven 57.107 `_persist_subagent_transcript` (best-effort `db.begin_nested()` SAVEPOINT, env-gated `MAIN_TRANSCRIPT_OBSERVER` default-on). Inside `_stream_loop_events`, persists the EXACT already-serialized SSE `payload` (incl. `active_skill`) per event to `message_events`, keyed by the MAIN `session_id` (sidechain rows key by `subagent_id` → no collision), with a monotonic `main_seq`. Persisted before the `yield`; a persist failure is logged and swallowed (never breaks the stream). `payload["data"]` is JSON-native for every serializer (UUIDs str()-coerced; `trace_id` a hex str) so it persists directly. **NO migration** — the `message_events` table + monthly partitions + `messages_default` (0028) already exist.
- **Reader** (`api/v1/sessions.py`): `GET /api/v1/sessions/{id}/events` (`list_session_events`) — inline `select(MessageEvent).order_by(sequence_num)` (mirrors `get_state_snapshot` RLS + redundant tenant filter). Returns `SessionEventsResponse{events: [{type, data, sequence_num, timestamp_ms}]}`. A cross-tenant / unknown / event-less session → 200 + `[]` (NOT 404 — zero events is valid AND cross-tenant existence must stay hidden; the deliberate difference vs `/state` is documented).
- **Test isolation** (`tests/integration/api/conftest.py`): `MAIN_TRANSCRIPT_OBSERVER=false` setdefault (mirror the sibling observer gates).
- **Stale-ref cleanup**: `next-phase-candidates.md:495` + `sessions.py` docstring corrected (LIST done 57.107 vs history-REPLAY this arc).

## Verification

- mypy `src` **0/370** · flake8 clean · run_all **10/10** (wire **24** unchanged — reused the existing serializer, no new event type) · full backend pytest **2711 passed / 5 skipped** (baseline 2703+5 → **+8** new).
- New tests (8): `test_main_transcript_persist.py` (ordered rows + Thinking-skip / env-off no rows / main-vs-sidechain `session_id` separation / cross-tenant invisible) + `test_sessions_events.py` (ordered / empty-new / cross-tenant-empty-not-404 / unknown-empty + item shape). All drive the REAL `_stream_loop_events` + `list_session_events` against real Postgres.
- **Live backend probe** (gate + probe, NOT a UI drive-through): a real-LLM chat through the running server (env default on) persisted 16 main events; `GET /events` returned them ordered 1..16 with **streamed == persisted (order + type) TRUE** (full replay fidelity); unknown session → 200 `[]`. Detail: `sprint-57-125/progress.md` Day 3.

## Impact

Backend-only. The main chat SSE stream is now durably persisted (full fidelity) + readable via `GET /{id}/events`. NO migration / new wire event / codegen / frontend / `styles-mockup.css` change (Alembic head `0030` unchanged; Vitest 892 / mockup 51 unchanged). Sets the stable contract for Sprint 57.126 (frontend: click → fetch `/events` → replay through the live `mergeEvent` reducer → render historical turns). Deferred: an event-volume delta-filter + a `message_events` retention/TTL policy (Phase 58+).
