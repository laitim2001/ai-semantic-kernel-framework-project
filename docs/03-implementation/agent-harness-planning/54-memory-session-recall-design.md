# 54 — Cross-Session Conversation Recall (rolling session summaries)

**Purpose**: Design note extracted from Sprint 57.151's real implementation — fill the designed-but-unwired `memory_session_summary` table to give the agent cross-session conversation recall (缺口 2).
**Category / Scope**: 範疇 3 (Memory) / Phase 57 / Sprint 57.151
**Created**: 2026-06-30
**Status**: Active (shipped, drive-through STRONG PASS)
**Closes**: `AD-Memory-Formation-Session-Recall`

> **Modification History**
> - 2026-06-30: Initial extraction (Sprint 57.151)

---

## 1. Spike Summary (US-1/2/3 — what was wired)

The memory-formation arc recalled discrete user FACTS (57.148/149/150) but not the *conversation arc* of a prior session. This spike wires the designed Layer-5 table `memory_session_summary` into a rolling per-session summary (formed on the post-send seam) + a cross-session recall injected into the prompt — so a NEW session answers "what were we working on last time?".

- US-1 storage: `memory_session_summary` += `updated_at` (`infrastructure/db/models/memory.py:326-333`; migration `0033_session_summary_updated_at.py`) + `DBSessionSummaryStore` (`agent_harness/memory/session_summary_store.py`).
- US-2 formation: `SessionSummarizer.summarize_and_store` (`agent_harness/memory/session_summarizer.py:88-119`) on the post-send BackgroundTask (`api/v1/chat/router.py:710-721`).
- US-3 recall: `MemoryRetrieval.recent_sessions` (`agent_harness/memory/retrieval.py:166-216`) injected at `DefaultPromptBuilder.build` (`agent_harness/prompt_builder/builder.py:287-313`).

## 2. Decision Matrix

| Decision | Options | Chosen | Why (rejected alternatives) |
|----------|---------|--------|------------------------------|
| **Storage table** | (a) NEW `memory_session` table / (b) REUSE designed `memory_session_summary` / (c) fold into `memory_user` | **(b) reuse** | Day-0 三-prong found `memory_session_summary` ALREADY created (`0007_memory_layers.py:221`) + designed for exactly this (`09-db-schema-design.md:481`). (a) = AP-3 duplicate-table + wrong-RLS migration; (c) would dilute `profile()` identity top-k (the 57.150 dilution). |
| **Formation trigger** | (a) rolling-per-send / (b) summarize-prior-on-new-session / (c) on-session-end | **(a) rolling-per-send** | A chat session has no clean "end" event (HTTP, user just stops); rolling on the existing 57.149 post-send seam keeps the summary always-current + reuses the loaded ledger for free. (b) needs "which is the last session" logic + first-recall latency; (c) has no trigger. |
| **Recall scope read** | (a) MemoryLayer.read ABC / (b) dedicated `recent_sessions()` method | **(b) dedicated method** | The read is cross-session-by-user (not query-gated), which doesn't fit `MemoryLayer.read(query, …)`. Mirrors the 57.148 `profile()` always-on precedent exactly. |
| **RLS on the recall** | (a) rely on explicit WHERE / (b) explicit WHERE + set_config | **(b) both** | `memory_session_summary` is junction (no RLS) but the JOIN target `sessions` IS FORCE RLS (`0009_rls_policies.py:79`) → `set_config('app.tenant_id')` REQUIRED or the JOIN returns nothing; explicit `s.tenant_id`/`s.user_id` filter = defense-in-depth. |
| **Summary shape** | (a) plain text / (b) structured {summary, key_decisions, unresolved_issues} | **(b) structured** | The designed table has all 3 columns — populating them makes recall richer ("decided X / left off on Y") at no extra cost (one JSON summary call). |
| **Gate** | (a) per-feature flags / (b) one flag for both | **(b) one `chat_session_summary`** | Gates formation (router) + recall (store-threading in `make_chat_memory_deps`) together → fully byte-identical when off; recall-on-formation-off is not a real use case. |

## 3. Verified Invariants (drive-through + tests)

- **Formation writes the designed columns** — drive-through: dan's session A → `memory_session_summary` row with `summary` + `key_decisions=['Use a dual-write pattern…']` + `unresolved_issues=['…JSONB column or a separate normalized table']`. Verify: `pytest tests/integration/memory/test_session_summary_store.py::test_upsert_same_session_one_row`.
- **One row per session (rolling upsert)** — the `session_id` UNIQUE + ON CONFLICT means a 2nd send UPDATEs the row, never inserts a 2nd. Verify: same test (id1 == id2, count == 1).
- **Recall surfaces the prior session, excluding current** — drive-through: NEW session B recalled session A's arc verbatim (Verification 0.98). Verify: `pytest tests/unit/agent_harness/prompt_builder/test_builder_session_recall.py::test_recent_sessions_injected_excluding_current` + `tests/integration/memory/test_session_summary_store.py::test_recent_for_user_orders_and_excludes`.
- **Per-user isolation** — drive-through: priya (same tenant) saw 0 of dan's content (`dan_content_leak: false`). Verify: `test_session_summary_store.py::test_recent_for_user_per_user_isolation` + `::test_recent_for_user_per_tenant_isolation`.
- **Byte-identical when off** — Verify: `test_retrieval_recent_sessions.py::test_recent_sessions_no_store_returns_empty` + `make_chat_session_summary_store` returns None when `chat_session_summary` off.
- **Provider-neutral** — `SessionSummarizer` uses the ChatClient ABC; AP-8 allowlist entry (background memory-formation, same as `extraction.py`). Verify: `python scripts/lint/run_all.py` (llm_sdk_leak + check_promptbuilder_usage green).

Test fixtures: real-Postgres integration uses the conftest `db_session` + `seed_tenant`/`seed_user` + a local `_seed_session`/`_seed_summary` (explicit `updated_at` because `func.now()` is txn-stable within one test transaction). Drive-through DB inspector: `%TEMP%/claude_57151_db.py`.

## 4. Cross-Category Contracts (17.md single-source)

No NEW cross-category ABC contract. `recent_sessions()` is an additive method on the existing `MemoryRetrieval` coordinator (範疇 3, owner of memory retrieval per `17-cross-category-interfaces.md §2.1`); `SessionSummaryReader` is an internal Protocol (not a cross-category contract). The recall flows 範疇 3 → 範疇 5 (PromptBuilder) via the existing `memory_layers` dict the builder already consumes — no new interface. The formation rides the existing post-send BackgroundTask (範疇 12 cross-cutting / chat router), reusing the 57.149 seam. So 17.md needs no new entry (additive within Cat 3's existing surface).

## 5. Open Invariants (deferred — NOT verified this sprint)

- `extracted_to_user_memory` / `extraction_completed_at` coordination with the 57.149 auto-extract (mark a session's summary as extracted) — `AD-Memory-Session-Summary-Extract-Coordination`.
- Combining extract + summarize into ONE LLM call (two cheap calls per send today) — `AD-Memory-Formation-Combine-Extract-Summarize`.
- Incremental summarization for very long ledgers (re-summarizes the whole ledger each send) — `AD-Memory-Session-Summary-Incremental`.
- Semantic/vector ranking of session summaries (recency-ordered only) — CARRY-026 (the 57.146 EmbeddingClient + 57.147 per-tenant pattern unblock it).
- A chat-v2 Inspector surface for session summaries (no new wire event this sprint) — `AD-Memory-Session-Summary-Inspector-Phase58`.
- In-memory `SessionLayer` → DB promotion — CARRY-029 (separate concern; this added a sibling persisted summary path only).

## 6. Rollback

Backend-only, additive, flag-gated. To disable at runtime: set `CHAT_SESSION_SUMMARY=false` → no formation + no recall (byte-identical to 57.150), no redeploy. To revert the code: the migration `0033` is a pure additive `ADD COLUMN updated_at` (drop via `alembic downgrade -1`); the new store/summarizer/recent_sessions are additive (default-None ctor preserves all existing construction); the builder recall block + router summarize call are guarded by the store/summarizer being present. Estimated revert: < 1 day (drop migration + remove the additive files + the 3 wiring edits). The designed `memory_session_summary` table itself stays (it predates this sprint).

## 7. References

- `09-db-schema-design.md` L481-498 — the designed `memory_session_summary` schema.
- `0007_memory_layers.py:219-265` (create) / `0009_rls_policies.py:27-29` (junction, no direct RLS).
- `agent_harness/memory/layers/user_layer.py:170-199` — the 57.150 upsert pattern mirrored.
- `agent_harness/state_mgmt/message_store.py:111-122` — the own-session set_config FORCE-RLS pattern mirrored.
- `agent_harness/memory/retrieval.py:127-163` — the 57.148 `profile()` always-on inject precedent.
- `api/v1/chat/router.py:673-722` — the post-send `_maybe_auto_extract` seam.
- CHANGE-118 · `sprint-57-151-plan.md` · `sprint-57-151/artifacts/snapshot.md` (drive-through).

## 8. 8-Point Quality Gate self-check

1. ✅ Section headers map to US (§1 US-1/2/3). 2. ✅ Every technical claim has file:line. 3. ✅ Decision matrix (§2, 6 decisions with rejected alternatives). 4. ✅ Verification commands (§3, pytest per invariant + run_all). 5. ✅ Test fixture reference (§3 conftest + DB inspector). 6. ✅ Open invariants explicitly bounded (§5, verified vs deferred). 7. ✅ Rollback path (§6, env flag + migration downgrade). 8. ✅ 17.md cross-ref (§4 — additive, no new contract).
