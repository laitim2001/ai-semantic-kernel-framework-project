# CHANGE-118: cross-session conversation recall via rolling session summaries

**Date**: 2026-06-30
**Sprint**: 57.151
**Scope**: 範疇 3 (Memory) — backend-only (NO wire/frontend); closes `AD-Memory-Formation-Session-Recall` (缺口 2)

## Problem

The memory-formation arc (57.148 identity inject / 57.149 auto-extract / 57.150 dedup) recalls discrete durable USER FACTS but NOT what was *discussed / decided* in a prior session. Open a new chat session and ask "what were we working on last time?" → the agent recalls nothing about the prior conversation arc (auto-extract only grabs durable user preferences, never "we discussed X / decided Y / left off on Z"). This is the last open gap of the memory-formation arc — the agent feels amnesiac about prior work threads each new session.

## Root Cause

The designed Layer-5 persisted-summary table `memory_session_summary` (created in `0007_memory_layers`, ORM `MemorySessionSummary`, per `09-db-schema-design.md` L481 — `session_id UNIQUE` + `summary` + `key_decisions`/`unresolved_issues` JSONB + an `extracted_to_user_memory` coordination flag) existed but was **never wired**: no writer, no reader, the JSONB columns never populated. The in-memory `SessionLayer` (working memory) is a separate, transient concern (CARRY-029).

## Solution

Filled the designed `memory_session_summary` table end-to-end (Day-0 三-prong caught that plan v0 had invented a duplicate `memory_session` table — reused the designed one instead, per Check-Existing):

- **Storage**: additive `updated_at` column (migration `0033`, backfill = created_at) for rolling-recency ordering; the table stays junction-style (no direct RLS — tenant via the session FK).
- **Store** `DBSessionSummaryStore` (`agent_harness/memory/session_summary_store.py`): `upsert_summary` (pg_insert ON CONFLICT on the `session_id` UNIQUE — one rolling row per session, mirrors 57.150) + `recent_for_user` (JOIN `sessions` to scope by tenant + user, exclude the current session, ORDER BY updated_at DESC; own-session + `set_config` since `sessions` is FORCE RLS).
- **Formation** `SessionSummarizer` (`session_summarizer.py`): cheap-tier ChatClient (provider-neutral) → structured JSON `{summary, key_decisions[], unresolved_issues[]}` → upsert. Driven from the post-send `BackgroundTask` (rides the 57.149 `_maybe_auto_extract` seam, reuses the loaded ledger), so the summary is always-current and a chat session needs no clean "end".
- **Recall** `MemoryRetrieval.recent_sessions()` (mirrors 57.148 `profile()`) → `layer="session"` hints injected into `DefaultPromptBuilder.build()` (prepended into the session slot, graceful-degrade) so a NEW session surfaces the user's recent prior-session summaries excluding the current one.
- **Gate**: one env flag `chat_session_summary` (default ON) gates BOTH formation + recall (store not threaded / no summarize when off → byte-identical to 57.150).

Code: `infrastructure/db/models/memory.py` (+updated_at) · `migrations/versions/0033_session_summary_updated_at.py` · `agent_harness/memory/{session_summary_store,session_summarizer}.py` · `retrieval.py` (recent_sessions + SessionSummaryReader Protocol) · `memory/__init__.py` · `prompt_builder/builder.py` (recall inject) · `api/v1/chat/{_category_factories,handler,router}.py` · `core/config/__init__.py` · 4 test files + 1 AP-8 allowlist entry.

## Verification

- Gates: mypy `src` 0/396 · run_all 11/11 (incl. llm_sdk_leak + rls_policies) · pytest 3042 passed/6 skipped (+20: 5 store integration + 6 summarizer + 5 recent_sessions + 4 builder recall) · black/isort/flake8 clean · migration up→down→up clean · FE untouched (Vitest 922 / mockup 51).
- **Drive-through STRONG PASS** (real chat-v2 + real Azure gpt-5.2, see `sprint-57-151/artifacts/snapshot.md`): Leg 1 — dan's session A (billing MongoDB→Postgres / dual-write / invoices JSONB-vs-table) → `memory_session_summary` row with all 3 columns populated; Leg 2 — NEW session B recalled A's arc verbatim (Verification 0.98); Leg 3 — priya (same tenant) saw 0 of dan's content (`dan_content_leak: false`), only her own profile.

## Impact

Backend-only (範疇 3 Memory + its formation seam in the chat router + the recall inject in the PromptBuilder). NO wire schema change (stays 26), NO frontend, NO new SSE event. `chat_session_summary=false` is byte-identical to 57.150. Two cheap LLM calls per send now (extract + summarize) — accepted for the spike (carryover to combine). The reused table's `extracted_to_user_memory` coordination flag is left at default (carryover).
