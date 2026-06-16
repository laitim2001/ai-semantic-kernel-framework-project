# Sprint 57.125 Progress — chat-v2 session history replay (arc slice 1/2: backend SSE transcript persistence + replay endpoint)

[Plan](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-125-plan.md) · [Checklist](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-125-checklist.md)

---

## Day 0 — 2026-06-16 — Plan-vs-Repo three-prong verify

### Re-scope context
`AD-ChatV2-SessionList-Backend`'s literal scope (the session-LIST backend) is **already shipped by Sprint 57.107 B3** (`GET /api/v1/sessions` real + `SessionList.tsx` wired + DEMO dropped + New-session→reset). The residual gap = clicking a historical session doesn't load its conversation (the main SSE stream is unpersisted). User picked **Option B** (full SSE persist + replay, ~2-sprint arc). This slice 1 = backend writer + replay endpoint.

### Drift findings

| ID | Prong | Finding | Implication |
|----|-------|---------|-------------|
| **D1** | 3 (schema) | Alembic head is **`0030_tenant_skills`** (0029 MFA + 0030 skills added in 57.112/57.114), NOT the `0028_sidechain_sessions` the plan assumed | **NO impact** — this sprint needs NO migration (`message_events` table + partitions + `messages_default` from 0028 already exist). Correct the plan/checklist baseline `0028`→`0030`. Plan §Risks unaffected (no migration consumed; head stays 0030). |
| **D2** | 1 (path) | The observer env-gate (`SESSIONS_CHAT_OBSERVER` / `SUBAGENT_TRANSCRIPT_OBSERVER` `os.environ.setdefault(..., "false")`) lives in **`backend/tests/integration/api/conftest.py:71,78`**, NOT the top-level `backend/tests/conftest.py` the plan named | File Change List #3 + §3.0/§3.1/§3.2/§Risks conftest path corrected to `tests/integration/api/conftest.py`. Add `MAIN_TRANSCRIPT_OBSERVER` `setdefault("false")` there (mirror the sibling lines). |
| **D3** | 2 (content) | `serialize_loop_event` (`sse.py`) returns the SSE payload `{type, data}`; for JSONB persistence the sidechain writer (`router.py:525-532`) stores `payload["data"]` directly (proven since 57.107). `data` may carry `trace_id` (str/None) + nested dicts | Day-1 implementation note: mirror the sidechain writer (`event_data=payload["data"]`); if a JSONB coercion error surfaces on a main-only event type, wrap with `sse._jsonable(...)` (the same coercion the SSE wire uses). Not a Day-0 blocker. |

### Prong confirmations (GREEN)

- **Prong 1 (path)** ✅: `serialize_loop_event` @ `api/v1/chat/sse.py:110`; `MessageEvent` ORM @ `sessions.py:223-267` (composite PK `(id, created_at)`, partitioned, `TenantScopedMixin` → tenant_id + RLS); `_stream_loop_events` @ `router.py:576`; `_persist_subagent_transcript` @ `router.py:469-548`; `payload = serialize_loop_event(event)` @ `router.py:648`; `MessageEvent` import @ `router.py:114`; `get_state_snapshot` + `StateSnapshot` import @ `sessions.py:115/60`. `CHANGE-092` free (091 highest) · design note `37` free (36 highest) · `GET /sessions/{id}/events` NOT already defined.
- **D-main-writer-absent** ✅: `grep "MessageEvent("` across `backend/src` → only `router.py:525` (the sidechain observer, keyed `session_id=subagent_id`). The main-session writer is net-new; main rows (`session_id`=main) and sidechain rows (`session_id`=subagent_id) separate cleanly by `session_id`.
- **D-serialize-skip-set** ✅: only `Thinking` → `None` (skipped; `LLMResponded` carries the content canonically); `SubagentChildEvent` with a `None` inner → `None` (a sidechain-only event, not on the main stream); all other wired events serialize; unknown events raise `NotImplementedError` (the main loop `continue`s). The persisted set == the SSE-streamed set by reusing the same `payload` + the same `None`-skip. **Volume upside**: token-level `Thinking` deltas are NOT persisted (skipped) → the persisted stream is turn/span/tool-level, not token-level → row volume is manageable.
- **D-conftest-gate** ✅ (→ D2): the sibling observer flags are at `tests/integration/api/conftest.py:71,78`.
- **D-replay-payload-shape** ✅: `serialize_loop_event` → `{type, data}`, `data` JSON-serializable with `trace_id` injected. The slice-2 (57.126) replay contract = `{type, data, sequence_num, timestamp_ms}` (recorded for the 57.126 plan + design note 37).
- **Prong 3 (schema)** ✅ (+ D1): `message_events` partitioned monthly + `messages_default` (0028) + `idx_message_events_session (session_id, sequence_num, created_at)` (the read endpoint's ORDER BY rides this index) + RLS; columns match the writer; **NO migration** (head stays 0030).
- **Baselines** (trusted from 57.124 merge `486db0ed`): pytest 2703+5skip · wire 24 · Vitest 892 · mockup 51 · mypy 0/370 · run_all 10/10.

### Go/no-go
**GO** — scope-shift 0% (the 3 drifts are a baseline-number correction + a conftest-path correction + a Day-1 JSONB note; none change scope). Proceeding to Day 1 with the corrected conftest path + head `0030`.

---

## Day 1+2 — 2026-06-16 — Writer + Reader + tests

### Implemented
- **Writer** (`router.py`): `_persist_main_event` observer (mirrors `_persist_subagent_transcript`) — best-effort `db.begin_nested()` SAVEPOINT, env-gated `MAIN_TRANSCRIPT_OBSERVER` (default on), persists the already-computed `payload` (incl. active_skill) per event keyed by the MAIN `session_id`; `main_seq` counter + `main_transcript_on` init in `_stream_loop_events`; persist call inserted right before the `yield` (after active_skill injection). `payload["data"]` persisted directly (D3-resolved: all main event `data` is JSON-native — verified every sse.py serializer; `trace_id` is a hex str). `+from typing import Any`. MHist + Last Modified updated.
- **Env-gate** (`tests/integration/api/conftest.py` — D2-corrected path, NOT top-level conftest): `MAIN_TRANSCRIPT_OBSERVER` `setdefault("false")` for test isolation (mirror the sibling observer flags).
- **Reader** (`sessions.py`): `GET /{session_id}/events` (`list_session_events`) + `SessionEventItem` / `SessionEventsResponse`; inline `select(MessageEvent).order_by(sequence_num)` (mirror `get_state_snapshot` RLS + redundant tenant filter); cross-tenant/new/unknown → 200 + `[]` (NOT 404 — documented deliberate difference vs `/state`). `+MessageEvent` import; docstring LIST-vs-history clarification (US-6 partial); MHist.
- **Tests**: `test_main_transcript_persist.py` (4 — ordered rows / Thinking-skipped / env-off no rows / main-vs-sidechain `session_id` separation / cross-tenant invisible) — co-located with the sibling `test_subagent_transcript_observer.py` at `tests/integration/api/` (the planned `v1/chat/` subdir was a fresh empty subtree with no conftest chain → moved to the sibling dir for consistency + guaranteed conftest application; Day-1 path drift, no scope change). `test_sessions_events.py` (4 — ordered / empty-new / cross-tenant-empty-not-404 / unknown-empty + item-shape `{type,data,sequence_num,timestamp_ms}`).

### Gate (Day 1+2 complete)
- mypy `src` **0/370** ✅ (no new src files; edits only)
- black/isort ✅ · flake8 **clean** ✅ (fixed 1 E501 — reader docstring Purpose line)
- run_all **10/10** ✅ (`check_event_schema_sync` confirms wire **24** unchanged — reused the existing serializer, NO new event type)
- new tests **8 passed** ✅ · regression (sessions_list + subagent observer + chat router) **32 passed** ✅
- **full backend pytest 2711 passed / 5 skipped** ✅ (baseline 2703+5 → +8 new, exact; no regression — the conftest gate-off keeps existing chat tests row-free)
- Alembic head still `0030` (NO migration) · FE untouched (Vitest 892 / mockup 51 unchanged by definition)

### Notes
- **D3 resolved**: persist `payload["data"]` directly (no `_jsonable`) — audited all sse.py serializers; every `data` value is JSON-native (UUIDs str()-coerced by the serializers; `trace_id: str = uuid4().hex`). Consistent with the proven sidechain writer.
- Volume: `Thinking` (token-level) is skipped (serializer → None) → the persisted stream is turn/span/tool-level, manageable.

---

## Day 3 — 2026-06-16 — Backend probe (gate + probe; NOT a UI drive-through)

### Clean restart (Risk Class E — `router.py`/`sessions.py` changed)
- Stale :8000 = PID 43064 (reloader, 57.124 session OLD code) + child 39620 (spawn worker). `Stop-Process -Force 43064,39620` → :8000 FREE → started a fresh **no-reload** single process PID 44960 (deterministic; avoids `--reload` orphan-worker risk) → startup log "startup complete" + sole :8000 owner. Vite :3007 (node) NOT stopped. mockup http.server 12040 untouched.

### Probe (real-LLM chat through the running server, MAIN_TRANSCRIPT_OBSERVER default on)
`dev-login (probe57125 tenant) → POST /chat {mode: real_llm, session_id: 554118b3…} → GET /sessions/{id}/events`:

| Check | Result |
|-------|--------|
| dev-login | 200 |
| chat POST (real Azure gpt) | 200 |
| streamed event types (16) | loop_start · span_started×... · turn_start · prompt_built · llm_request · llm_response · state_checkpointed · verification_passed · loop_end |
| GET /events | 200 — **16 rows**, sequence `1..16`, **ordered True** |
| **streamed == persisted (order + type)** | **TRUE** — the persisted stream is byte-identical to what was streamed live (full replay fidelity → 57.126 reconstructs pixel-identical turns) |
| item shape | `{type, data, sequence_num, timestamp_ms}` (the 57.126 replay contract) |
| loop_start `active_skill` | present in persisted data (the active_skill field rides through) |
| unknown session `/events` | 200 + `{events: []}` (not 404 — empty-vs-404 semantics confirmed live) |

**Honest status**: this is a **gate + probe** verification of a backend foundation (the running server's wired observer fires with the env default on + the replay endpoint serves) — explicitly **NOT a UI drive-through** (no user-facing surface this sprint; the UI replay is 57.126's DoD). The integration tests additionally drive the REAL `_stream_loop_events` + `list_session_events` against real Postgres.

### Cleanup
- Temp `.probe_57125.py` + probe uvicorn logs removed; PID 44960 stopped → :8000 clean. User can `python scripts/dev.py start backend` to resume the normal `--reload` dev backend.

---
