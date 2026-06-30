# Sprint 57.151 Retrospective — cross-session conversation recall (rolling session summaries)

**Closed**: 2026-06-30 · Branch `feature/sprint-57-151-memory-session-recall` (base `main` `f664f34d`) · CHANGE-118 + design note 54 · closes `AD-Memory-Formation-Session-Recall` (缺口 2).

## Q1 — What shipped?

Filled the designed-but-unwired `memory_session_summary` table (Layer-5 persisted summary) to give the agent cross-session conversation recall. A `SessionSummarizer` (cheap-tier, provider-neutral) rides the 57.149 post-send BackgroundTask seam and upserts a rolling `{summary, key_decisions, unresolved_issues}` per session (the table's `session_id` UNIQUE); a new `MemoryRetrieval.recent_sessions()` (mirrors 57.148 `profile()`, JOINs `sessions` for tenant+user scope, excludes the current session) is injected into the PromptBuilder so a NEW session recalls the user's recent prior-session arcs. Migration `0033` adds one additive `updated_at` column. One env flag `chat_session_summary` (default ON) gates both formation + recall. Backend-only; NO new table / wire / frontend.

## Q2 — Estimate accuracy (calibration)

- Scope class **NEW `memory-session-recall-spike` 0.60**. Agent-delegated: **no** (parent-direct, `agent_factor` 1.0, 3-segment).
- Bottom-up ~7.0 hr → class-calibrated commit ~4.2 hr (mult 0.60). Actual ~4.4 hr → ratio **~1.05 IN band**.
- Why it landed clean: the Day-0 三-prong reuse-existing-table catch REMOVED the new-table/RLS work (≈ −1.5 hr) but the JOIN read + structured-JSON summary + the 3-leg drive-through balanced it. The real-code core (store + summarizer + recall + inject + 20 tests + migration) held the 0.60 per the 57.137 lesson — NOT a tiny-code-wrapped-in-ceremony 0.85. The drive-through was unusually clean (formation visible immediately in the DB; recall recited the prior arc verbatim first try; isolation 0-leak first try) — no re-architecture / no re-drive. KEEP 0.60 pending 2-3 sprint validation; if a 2nd `memory-session-recall-spike` diverges > 30%, re-point.

## Q3 — What went well?

- **Day-0 三-prong caught the single biggest risk upfront**: plan v0 invented a `memory_session` table; the grep found `memory_session_summary` ALREADY designed + created (`0007` / `09.md:481`) with richer columns (`key_decisions` / `unresolved_issues` / `extracted_to_user_memory`). Reusing it (Check-Existing 鐵律) saved ~1.5 hr + an AP-3 duplicate-table + a wrong direct-RLS migration. The plan was revised before any code (net scope reduction).
- **Riding two proven seams** (the 57.149 post-send BackgroundTask + the 57.148 `profile()` inject) meant the formation + recall wiring was thin and the gate green on the first full run.
- **The drive-through was textbook**: formation wrote all 3 columns; recall recited the billing/dual-write/invoices arc verbatim in a new session; per-user isolation gave priya 0 of dan's content. The two memory mechanisms (session summary + user fact) coexisted cleanly (dan's recall also surfaced the 57.149 "Project Aurora" fact).
- The `func.now()`-is-txn-stable subtlety was anticipated (the ordering integration test seeds explicit `updated_at`).

## Q4 — What to improve?

- The migration revision id length bit once (Day-1 `D-revision-id-len`): `0033_memory_session_summary_updated_at` (38 chars) exceeded `alembic_version.version_num VARCHAR(32)` → transactional rollback to 0031. Shortened to `0033_session_summary_updated_at` (31). **Future: keep migration revision ids ≤ 32 chars.**
- Two cheap LLM calls per send now (extract + summarize). Acceptable for the spike, but a combine-into-one is a clear follow-up (`AD-Memory-Formation-Combine-Extract-Summarize`).
- The reused table's `extracted_to_user_memory` coordination flag is a designed hook left unused — a future slice could mark a session's summary as extracted to avoid re-extracting.

## Q5 — Anti-pattern self-check

- AP-2 (no orphan): recent_sessions reachable from the PromptBuilder (drive-through proved); the summarizer reachable from the router BackgroundTask. ✅
- AP-3 (no scatter): all in 範疇 3 (memory) + its chat-path wiring; the Day-0 catch specifically PREVENTED an AP-3 duplicate table. ✅
- AP-4 (no Potemkin): drive-through proved formation writes a real row + recall recites it + result renders (NOT a stub). ✅
- AP-6 (no premature abstraction): reuses the designed table + pg_insert/ON CONFLICT (existing pattern); `SessionSummaryReader` Protocol is a minimal decoupling, not speculative. ✅
- AP-8 (PromptBuilder): SessionSummarizer is a background memory-formation caller (allowlisted with rationale, same as extraction.py). ✅
- AP-11 (no version suffix): none. ✅
- v2 lints 11/11 (incl. llm_sdk_leak + rls_policies — no new RLS table). ✅

## Q6 — Gates

mypy `src` 0/396 · run_all 11/11 · pytest 3042 passed/6 skipped (+20) · black/isort/flake8 clean · migration up→down→up clean · FE untouched (Vitest 922 / mockup 51). **Drive-through STRONG PASS** (real chat-v2 + Azure gpt-5.2; Formation + Recall + per-user isolation all verified — `artifacts/snapshot.md`).

## Q7 — Carryover (→ ADs, not future tasks)

- `AD-Memory-Session-Summary-Extract-Coordination` — set `extracted_to_user_memory` / `extraction_completed_at` to coordinate the session summary with the 57.149 auto-extract.
- `AD-Memory-Formation-Combine-Extract-Summarize` — fold the extract + summarize into one cheap LLM call (two per send today).
- `AD-Memory-Session-Summary-Incremental` — incremental (non-full-ledger) summarization for very long sessions.
- `AD-Memory-Session-Summary-Inspector-Phase58` — a chat-v2 Inspector surface for the session summary (a new wire event).
- CARRY-026 — semantic/vector ranking of session summaries (recency-only today; 57.146 EmbeddingClient + 57.147 per-tenant pattern unblock it).
- CARRY-029 — promote the in-memory `SessionLayer` working memory to DB (separate concern).

## Design Note Extract (spike sprint)

**File**: `docs/03-implementation/agent-harness-planning/54-memory-session-recall-design.md`
**Verified ratio (estimated)**: ~95% (every claim file:line / verify command; deferred items bounded in §5).
**8-Point Quality Gate**: 1.✅ section→US · 2.✅ file:line · 3.✅ decision matrix (6) · 4.✅ verify commands · 5.✅ test fixture · 6.✅ open-invariant boundary · 7.✅ rollback · 8.✅ 17.md cross-ref.
**Reviewer pass**: self-review.
