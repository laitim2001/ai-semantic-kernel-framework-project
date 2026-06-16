# 37 — chat-v2 Session History Replay: backend SSE transcript persistence (spike design note)

**Purpose**: Document the persistence semantics + the 57.126 replay contract extracted from the Sprint 57.125 backend spike (arc slice 1/2).
**Category / Scope**: Cat 12 (persistence) + api/v1 / Phase 57 / Sprint 57.125
**Created**: 2026-06-16
**Last Modified**: 2026-06-16
**Status**: Active

> **Modification History**
> - 2026-06-16: Initial creation (Sprint 57.125 backend spike extract)

---

## 1. Spike Summary

**US**: as the chat-v2 frontend (Sprint 57.126), I need a durable, full-fidelity source for a historical session's conversation so clicking a session can replay it. **This slice (backend)**: persist the main-session SSE event stream + serve it back ordered.

The chat main flow streams SSE events to the client but persisted **none** of them for the main session: `_persist_subagent_transcript` (`backend/src/api/v1/chat/router.py:469-548`, Sprint 57.107) writes `message_events` only for subagent sidechains (keyed `session_id=subagent_id`); the `messages` table has no main-flow writer; only `state_snapshots.state_data` (`backend/src/infrastructure/db/models/state.py:75-107`) holds the resume LLM-message list — NOT the rich chat-v2 Turn stream. So a historical session could not be reloaded.

**Shipped**: a symmetric MAIN-session writer (`_persist_main_event`, `router.py`) persisting the EXACT serialized SSE payload to `message_events` + a `GET /api/v1/sessions/{id}/events` replay endpoint (`backend/src/api/v1/sessions.py`).

## 2. Decision Matrix

| Option | Approach | Fidelity | Cost | Verdict |
|--------|----------|----------|------|---------|
| **A** | Reconstruct turns from `state_snapshots.state_data` (the resume LLM-message list) | Lossy — user/assistant text + tool calls only; no verification/thinking/inspector streaming detail | Low (no new persistence) | ❌ rejected — lossy; the chat-v2 Turn is SSE-derived, not message-list-derived |
| **B** | Persist the EXACT serialized SSE payload → replay through the live `mergeEvent` reducer | **Full** — pixel-identical historical turns (same reducer as live) | Medium (a writer + a read endpoint; reuses an existing table + serializer) | ✅ **chosen** (user, 2026-06-16) |
| **C** | Honest-disable the click (no history) | n/a | Trivial | ❌ rejected — leaves a soft Potemkin; the user wants real replay |

**Why B is cheap**: the writer reuses the already-computed `payload = serialize_loop_event(event)` (`router.py:648`) + the proven `_persist_subagent_transcript` pattern + the existing `message_events` table/partitions → **NO migration, NO new wire event, NO new serializer**.

## 3. Verified Invariants (this spike)

- **Writer persists the exact streamed payload**: `_persist_main_event` (`router.py`, inside `_stream_loop_events`) writes `MessageEvent(session_id=<main>, tenant_id, event_type=payload["type"], event_data=payload["data"], sequence_num=main_seq++, timestamp_ms)` right before the `yield`, reusing the same `payload` (incl. `active_skill`). Verified: `tests/integration/api/test_main_transcript_persist.py::test_main_transcript_persists_ordered_events` (real `_stream_loop_events`, real Postgres).
- **Persisted set == streamed set**: only `Thinking` serializes to `None` (`backend/src/api/v1/chat/sse.py:191-194`) and is skipped by the existing `if payload is None: continue` (`router.py:653`) BEFORE the persist block → token-level deltas are not persisted; everything streamed is persisted. **Live-proven**: a real-LLM chat streamed 16 events; `GET /events` returned 16 in identical order/type (`streamed == persisted` = TRUE). See `sprint-57-125/progress.md` Day 3.
- **Best-effort, never breaks the stream**: `async with db.begin_nested()` SAVEPOINT + `except Exception: logger.exception(...)` (exact mirror of the sidechain observer). Verify: `pytest tests/integration/api/test_main_transcript_persist.py -q`.
- **Env-gated**: `MAIN_TRANSCRIPT_OBSERVER` (default `"true"`; `tests/integration/api/conftest.py:79` sets `"false"`). Verified: `test_main_transcript_env_gated_off_writes_nothing`.
- **Main / sidechain separation**: main rows key `session_id=<main>`, sidechain rows key `session_id=<subagent_id>` → no collision (independent `main_seq` / `sidechain_seq`). Verified: `test_main_and_sidechain_rows_separate_by_session_id`.
- **Reader is tenant-scoped + empty-not-404**: `list_session_events` (`sessions.py`) — inline `select(MessageEvent).where(session_id, tenant_id).order_by(sequence_num)` (RLS + redundant tenant filter); cross-tenant/unknown/event-less → 200 + `[]`. Verified: `tests/integration/api/test_sessions_events.py` (4 cases) + live (`unknown session → 200 []`).
- **JSON-native payloads**: every `sse.py` serializer's `data` dict is JSON-native (UUIDs str()-coerced at the serializer; `trace_id: str = uuid4().hex` per `backend/src/agent_harness/_contracts/observability.py:63`) → `payload["data"]` persists to JSONB directly (no `_jsonable`).

## 4. Cross-Category Contracts (57.126 replay interface)

The replay-payload contract (single-source for the 57.126 frontend plan):

```
GET /api/v1/sessions/{session_id}/events  -> 200
  { "events": [ { "type": str, "data": object, "sequence_num": int, "timestamp_ms": int }, ... ] }
```

- `type` + `data` == the live SSE frame (`serialize_loop_event` output). The 57.126 frontend feeds each `{type, data}` through the SAME `chatStore.mergeEvent` 18-case reducer it uses for the live stream → pixel-identical historical turns. No new reducer, no backend shape change.
- Ordered by `sequence_num` ascending (rides `idx_message_events_session (session_id, sequence_num, created_at)`).
- No NEW ABC / wire event registered (17.md unchanged; this reuses Cat 12 `message_events` + the Cat 6 serializer). Recorded here, not duplicated in 17.md.

## 5. Open Invariants (deferred — NOT verified this spike)

- **Frontend replay** (click → fetch `/events` → reducer-replay → render historical turns + route continuation): Sprint 57.126 (arc slice 2, NOT pre-written). The reducer's tolerance for a full replayed stream (vs incremental live) is unverified here.
- **Event volume / table growth**: a real chat persisted 16 rows; a long multi-turn session persists proportionally more. The monthly-partitioned table + `messages_default` absorb it, but a delta-filter (e.g. drop high-frequency span events) is a deferred follow-up — fidelity-first this spike.
- **Retention / TTL** on `message_events`: none (Phase 58+).
- **Replay of tool-bearing / subagent / HITL-pause sessions**: the probe covered a simple real-LLM turn (loop_start/spans/turn/prompt/llm/checkpoint/verification/loop_end). A session with tool calls, subagents, or a HITL pause persists those frames too (they serialize), but their replay reconstruction is a 57.126 concern.

## 6. Rollback

- **Disable without revert**: set `MAIN_TRANSCRIPT_OBSERVER=false` → the writer no-ops (zero rows); the endpoint returns `[]`. Zero risk to the chat flow (the writer is best-effort + post-payload).
- **Code revert**: revert the `router.py` writer + the `sessions.py` endpoint + the conftest line; no migration to undo (the `message_events` table predates this sprint and keeps its sidechain rows). Estimate: < 1 hr.
- **Forward-compat**: the persisted payload == the live wire shape; if a serializer changes in a future sprint, old rows replay with the old shape (the reducer must stay backward-tolerant — a 57.126 note).

## 7. References

- `backend/src/api/v1/chat/router.py` — `_persist_main_event` + `_stream_loop_events` (writer)
- `backend/src/api/v1/sessions.py` — `list_session_events` (reader) + `SessionEventItem` / `SessionEventsResponse`
- `backend/src/api/v1/chat/sse.py` — `serialize_loop_event` (the payload source; `Thinking → None`)
- `backend/src/infrastructure/db/models/sessions.py:223-267` — `MessageEvent` ORM (partitioned, RLS)
- `backend/tests/integration/api/test_main_transcript_persist.py` + `test_sessions_events.py`
- `docs/.../sprint-57-125/progress.md` — Day-0 drift + Day 3 live probe
- `claudedocs/4-changes/feature-changes/CHANGE-092-*.md`
- Sprint 57.107 `_persist_subagent_transcript` (the mirrored pattern)

## 8. 8-Point Quality Gate (self-review)

1. ✅ Section headers map to the spike US (replay backend). 2. ✅ Every claim has a file:line / test name. 3. ✅ Decision matrix (A/B/C + reject reasons). 4. ✅ Verification commands (pytest names + live probe). 5. ✅ Test fixtures referenced (the 2 integration files; real-LLM probe noted). 6. ✅ Open invariants explicitly fenced (57.126 + volume + retention). 7. ✅ Rollback path (env flag + revert estimate). 8. ✅ Cross-ref: no new 17.md contract (reuses Cat 12 + serializer; recorded here). **Verified ratio (estimated)**: ~95%.
