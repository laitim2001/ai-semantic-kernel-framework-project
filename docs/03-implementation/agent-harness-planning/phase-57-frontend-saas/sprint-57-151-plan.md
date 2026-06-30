# Sprint 57.151 Plan — cross-session conversation recall via rolling session summaries

**Summary**: Closes `AD-Memory-Formation-Session-Recall` (缺口 2, the memory-formation arc's conversation-recall slice). The arc so far (57.148 identity inject / 57.149 auto-extract / 57.150 dedup) recalls discrete user FACTS but NOT what was *discussed/decided* in a prior session — open a new session and the agent has zero recollection of the prior conversation arc. **Day-0 三-prong found the storage table is ALREADY designed + created**: `memory_session_summary` (Layer 5 持久化, `0007_memory_layers.py:221` / ORM `MemorySessionSummary` / `09-db-schema-design.md:481`) with `session_id UNIQUE` + `summary` + `key_decisions`/`unresolved_issues` JSONB + an `extracted_to_user_memory` coordination flag — designed for exactly this. So this sprint REUSES that table (NOT a new one), adds one additive `updated_at` column for rolling-recency ordering, fills it via a cheap-tier `SessionSummarizer` riding the proven 57.149 post-send `BackgroundTask` seam, and recalls via a new `MemoryRetrieval.recent_sessions()` (mirrors 57.148 `profile()`) injected into `PromptBuilder.build()` so a NEW session surfaces the user's recent prior-session summaries (excluding the current session). Backend-only, NO wire(26)/frontend. Key scope decisions (AskUserQuestion 2026-06-30): (full vertical slice) + (rolling-summary-per-send trigger). Drive-through MANDATORY (user-facing recall). Design note REQUIRED (spike sprint — new Cat 3 store + summarizer + recall contract).

**Status**: Approved-to-execute (user AskUserQuestion 2026-06-30: Q1 "完整垂直切片" + Q2 "每次 send 後滾動更新"); Day-0 三-prong revised the storage mechanics (reuse existing table) — approved forks + user-facing behavior UNCHANGED.
**Branch**: `feature/sprint-57-151-memory-session-recall`
**Base**: `main` HEAD `f664f34d` (Sprint 57.150 flip #355 — memory upsert-dedup MERGED)
**Slice**: closes `AD-Memory-Formation-Session-Recall` (memory-formation arc, conversation-recall slice; arc = 57.148 identity → 57.149 auto-extract → 57.150 dedup → **this** session-recall)
**Scope decisions**: (a) REUSE the existing designed `memory_session_summary` table (Day-0 catch — NOT a new `memory_session` table); add one additive `updated_at` column for rolling recency; (b) form the rolling summary in the post-send `BackgroundTask` (ride the 57.149 `_maybe_auto_extract` seam, cheap tier) — always-current, handles "chat session has no clean end"; (c) recall via a new `MemoryRetrieval.recent_sessions()` mirroring `profile()`, injected as `layer="session"` hints, JOINing `sessions` to scope by tenant+user and exclude the current session; (d) one env flag `chat_session_summary` (default ON) gates BOTH formation + recall → byte-identical when off.

---

## 0. Background

### The gap (`AD-Memory-Formation-Session-Recall`, 缺口 2)

- The memory-formation arc (57.148/149/150) forms + recalls discrete durable USER FACTS ("name is Chris", "owns the Knowledge Connector").
- It does NOT capture the CONVERSATION ARC of a session — "last time we debugged the OIDC callback and decided to pin the redirect URI, left off on the refresh-token path".
- Open a NEW session and ask "what were we working on last time?" → the agent recalls nothing (auto-extract only grabs durable user preferences, never "we discussed X / decided Y").

### Why it matters (the missing capability)

A professional teammate remembers the *thread* of prior work, not just facts about you. Cross-session conversation recall is what makes the agent feel continuous across sessions instead of amnesiac each new chat — a core item of the "Memory-equipped" + "human professional team" vision pillars.

### Root cause (recon code read, file:line; ALL re-verified §checklist 0.1)

| Layer | Reality (on `main` HEAD `f664f34d`) | Anchor |
|-------|-------------------------------------|--------|
| Layer 5 persisted-summary table ALREADY EXISTS | `memory_session_summary` — `session_id UNIQUE` + `summary` + `key_decisions`/`unresolved_issues` JSONB + `extracted_to_user_memory` flag; junction (tenant via session FK, NO direct tenant_id, NO direct RLS) | `memory.py:284-325` / `0007_memory_layers.py:221` / `09-db-schema-design.md:481` |
| …but it is UNWIRED | no store / no writer / no reader; `key_decisions`/`unresolved_issues` never populated | (grep: 0 non-model refs) |
| Layer 5 working memory is transient | in-memory dict, per-(tenant,session), NOT persisted (separate concern, CARRY-029) | `session_layer.py:60-63` |
| Prior-session transcripts ARE persisted | `messages` table, per-session, RLS, durable — the summarizer's input | `message_store.py:124-150` |
| Formation seam exists + loads the ledger | post-send `BackgroundTask` already loads the ledger + has tenant/session/user + cheap tier | `router.py:673-708` (`_maybe_auto_extract`) |
| Always-on recall inject pattern exists | `profile()` pulls standing facts, prepended every turn (NOT query-gated) | `retrieval.py:127-163` + `builder.py:265-286` |
| `sessions` is FORCE RLS + has user_id/tenant_id | the recall JOIN needs `set_config('app.tenant_id')` to read it | `sessions.py:76-86` / `0009_rls_policies.py:79` |

→ The fix: fill the existing `memory_session_summary` table (rolling upsert keyed on its `session_id UNIQUE`), form it on the post-send seam (new cheap-tier summarizer), and recall the user's recent prior-session summaries via a new `recent_sessions()` (JOIN `sessions` for tenant+user scope, exclude current) injected into the prompt.

### The design (backend-only: reuse 1 table + 1 additive column + 1 store + 1 summarizer + 1 retrieval method + 1 builder inject + wiring; NO new table/wire/frontend)

```
FORMATION (post-send BackgroundTask, ride 57.149 seam):
  router._maybe_auto_extract(ctx)                       # already loads `ledger`
    └─ ctx.summarizer.summarize_and_store(ledger, session_id)
         └─ cheap ChatClient.chat("summarize → JSON {summary, key_decisions[], unresolved_issues[]}")
         └─ DBSessionSummaryStore.upsert_summary(session_id, summary, key_decisions, unresolved_issues)
              └─ pg_insert(MemorySessionSummary).on_conflict_do_update(            # mirror 57.150
                    index_elements=[session_id], set_={summary, key_decisions, unresolved_issues, updated_at})
                 # ONE rolling row per session (session_id is UNIQUE — designed)

RECALL (every turn, mirror 57.148 profile()):
  PromptBuilder.build()
    └─ retrieval.recent_sessions(tenant, user, exclude_session_id=current, top_k)
         └─ DBSessionSummaryStore.recent_for_user(...)
              └─ SELECT mss.session_id, mss.summary, mss.unresolved_issues, mss.updated_at
                 FROM memory_session_summary mss JOIN sessions s ON s.id = mss.session_id
                 WHERE s.tenant_id=:t AND s.user_id=:u AND mss.session_id != :exclude
                 ORDER BY mss.updated_at DESC LIMIT :n           # set_config — sessions is FORCE RLS
         └─ → list[MemoryHint](layer="session")
    └─ prepend into memory_layers["session"]  (reuses scope-grouped render + Tier2 budget cap)

GATE: settings.chat_session_summary (default True)
  off → make_chat_memory_deps threads no store → recent_sessions() == []   (recall byte-identical)
      → router skips summarize_and_store                                    (formation byte-identical)
```

WHY reuse the table over a new one: `memory_session_summary` is the *designed* Layer 5 persistence (Check-Existing 鐵律) — building a parallel `memory_session` would be AP-3 scatter + duplicate the designed schema. WHY rolling-per-send over summarize-prior-on-new-session: a chat session has no clean "end" event; rolling on the existing post-send seam keeps the summary always-current and reuses the loaded `ledger` for free. WHY `key_decisions`/`unresolved_issues` too: the table is designed with those columns — populating them makes recall richer ("we *decided* X, *left off* on Y") at no extra cost (one structured-JSON summary call).

### Ground truth (recon head-start — code read on `main` HEAD `f664f34d`; ALL re-verified §checklist 0.1)

- `memory.py:284-325` — `MemorySessionSummary` ORM (`Base`, NOT TenantScopedMixin): `session_id` FK+UNIQUE, `summary` Text, `key_decisions`/`unresolved_issues` JSONB default `[]`, `extracted_to_user_memory` Bool, `extraction_completed_at`, `created_at` — **NO `updated_at`** (this sprint adds it).
- `0007_memory_layers.py:219-265` — the create_table; `0009_rls_policies.py:27-29` lists `memory_session_summary` as junction (NO direct RLS) — so 0033 adds NO RLS.
- `sessions.py:76-93` — `Session(Base, TenantScopedMixin)` → `tenant_id` (mixin) + `user_id` + `status`; `idx_sessions_tenant_user`. `0009_rls_policies.py:79` — `sessions` IS FORCE RLS → the recall JOIN needs `set_config`.
- `message_store.py:100-122` — own-session + `set_config('app.tenant_id', …, true)` FORCE-RLS pattern to mirror in the store.
- `user_layer.py:170-199` — the `pg_insert … on_conflict_do_update` upsert pattern (57.150) to mirror for `upsert_summary` (here the conflict target is `index_elements=[session_id]`, the UNIQUE column).
- `router.py:673-708` — `_maybe_auto_extract` already does `ledger = await ctx.message_store.load()`; `:439-443` build gate; `:488-494` BackgroundTask wiring.
- `handler.py:796-855` — `ChatMemoryExtractContext` frozen dataclass + `build_chat_memory_extractor`; cheap tier = `profile.cheap` (`:852`); `make_chat_memory_deps` callers = `:364` (loop prompt builder) + `:848` (extract ctx) — both get the store via the factory automatically.
- `_category_factories.py:264-307` — `make_chat_memory_deps(db)` builds `MemoryRetrieval(layers=...)`; `:378-399` `make_chat_message_store` own-session factory to mirror.
- `builder.py:265-286` — the `profile()` prepend block to mirror; `:252` has `state.durable.session_id`, `:265` has `user_id`.
- `retrieval.py:127-163` — `profile()` shape to mirror for `recent_sessions()`.
- `_contracts/memory.py:52-71` — `MemoryHint` required fields.
- `core/config/__init__.py:170` — `chat_memory_auto_extract: bool = True` sibling for the new flag.
- migrations latest = `0032_memory_user_dedup_key.py` → next `0033`.

**Baselines (57.150 closeout)**: pytest 3022 · wire 26 · Vitest 922 · mockup 51 · mypy 0/393 · run_all 11/11. Re-verify Day-0.

### STALE / drift findings (Day-0; full detail → progress.md — placeholder, filled in §checklist 0.1)

- **D-table-already-exists** 🔴 (MAJOR catch) — plan v0 invented a `memory_session` table; the designed `memory_session_summary` already exists + is created (`0007`) + ORM'd (`memory.py:284`). REVISED: reuse it; drop the new-table migration; only add an additive `updated_at` column. Saves ~1.5 hr + an AP-3 duplicate-table violation + a wrong-RLS migration.
- **D-junction-no-rls** — `memory_session_summary` is junction (NO direct RLS); the recall JOINs `sessions` (FORCE RLS) → the store's own session MUST `set_config('app.tenant_id')`. No `rls_policies` lint change (no new RLS table).
- **D-no-updated-at** — the table has only `created_at`; rolling recency needs `updated_at` → additive column in 0033 (backfill = created_at).
- **D-memoryhint-fields** — re-confirm `MemoryHint` required fields before building hints in `recent_sessions()`.
- **D-make-memory-deps-callers** — `make_chat_memory_deps` has 2 callers (`handler.py:364` + `:848`); threading a new `MemoryRetrieval(..., session_summary_store=)` arg is additive (default-None).
- **D-builder-session-slot** — confirm `memory_layers["session"]` is normally empty on the chat path so the prepend renders the recall hints cleanly.

## 1. Sprint Goal

Deliver cross-session conversation recall by filling the designed-but-unwired `memory_session_summary` table: after a session's conversation a cheap-tier rolling summary (summary + key_decisions + unresolved_issues) is upserted (one row per session, the table's `session_id UNIQUE`); a NEW session injects the user's recent prior-session summaries into the prompt (JOIN `sessions` for tenant+user scope, excluding the current session) so the agent answers "what were we working on last time?" with the real prior-session content. PROVEN by gates (mypy/run_all/pytest + new tests + migration up-down-up) **and a MANDATORY drive-through** (real chat-v2 + real Azure: session A discusses a distinctive topic → NEW session B recalls it → a different user sees nothing). Produces CHANGE-118 + design note 54.

## 2. User Stories

- **US-1** (storage): 作為平台，我希望既有的 `memory_session_summary` 表被接上（補 `updated_at` + 一個 upsert/read store），以便跨 session 回憶有可靠且符合設計的儲存底座。
- **US-2** (formation): 作為使用者，我希望每次對話後系統自動（cheap-tier、背景、best-effort）滾動更新「本 session」摘要（summary + 關鍵決定 + 未解議題），以便我不需手動標記就能在日後回憶。
- **US-3** (recall): 作為使用者，我希望開新 session 時 agent 能回憶我近期其他 session 討論/決定了什麼（排除當前 session、租戶+使用者隔離），以便延續工作而非每次從零開始。
- **US-4** (drive-through, MANDATORY): 作為驗證者，我要在真 UI + 真後端 + 真 LLM 上實機走完 session A 討論 → 新 session B 回憶 → 不同 user 零洩漏，證明非 Potemkin。
- **US-5** (closeout): 作為維護者，我要 CHANGE-118 + design note 54 + retrospective + navigators，關閉 `AD-Memory-Formation-Session-Recall`。

## 3. Technical Specifications

### 3.0 Architecture (backend-only; NO new table / wire / frontend / new SSE event)

```
NEW:
  infrastructure/db/migrations/versions/0033_session_summary_updated_at.py  — ADD COLUMN updated_at (additive)
  agent_harness/memory/session_summary_store.py                  — DBSessionSummaryStore (upsert + recent_for_user JOIN sessions)
  agent_harness/memory/session_summarizer.py                     — SessionSummarizer (cheap ChatClient → JSON → store)
EDIT:
  infrastructure/db/models/memory.py                             — MemorySessionSummary += updated_at Mapped
  agent_harness/memory/retrieval.py                              — recent_sessions() + optional ctor store
  agent_harness/memory/__init__.py                               — exports
  agent_harness/prompt_builder/builder.py                        — recall inject block (mirror profile())
  api/v1/chat/_category_factories.py                             — make_chat_session_summary_store + thread into make_chat_memory_deps
  api/v1/chat/handler.py                                         — ChatMemoryExtractContext += summarizer; build_chat_memory_extractor
  api/v1/chat/router.py                                          — _maybe_auto_extract calls summarizer (flag-gated)
  core/config/__init__.py                                        — chat_session_summary: bool = True
UNTOUCHED:
  the memory_session_summary TABLE structure (only +updated_at) / its junction-no-RLS design
  agent_harness/memory/layers/session_layer.py                   — in-memory working memory (CARRY-029, out of scope)
  agent_harness/orchestrator_loop/loop.py                        — recall is in the PromptBuilder, not the loop
  wire schema (stays 26) / frontend / no new SSE event
```

### 3.1 Storage (US-1) — `memory.py` ORM += updated_at + `0033` additive migration

- `MemorySessionSummary` ORM: add `updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())`. Everything else (session_id UNIQUE, summary, key_decisions, unresolved_issues, extracted_to_user_memory, extraction_completed_at, created_at) already exists.
- Migration `0033` (revises `0032`): `op.add_column("memory_session_summary", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))` + `op.execute("UPDATE memory_session_summary SET updated_at = created_at")` (backfill existing rows to their created time, not now()). `downgrade` drops the column. NO table create, NO RLS change (the table stays junction-no-RLS by design).
- Index: add `Index("idx_memory_session_summary_updated", "updated_at")` is optional (recall filters by the JOINed sessions first; the result set per user is small) — SKIP to keep the migration minimal (note in §9).

### 3.2 Store (US-1) — `session_summary_store.py` (NEW)

- `DBSessionSummaryStore(session_factory)` — own short-lived session per call + `set_config('app.tenant_id', …, true)` (REQUIRED for the recall JOIN — `sessions` is FORCE RLS), mirrors `DBMessageStore` (`message_store.py:111-122`).
- `async upsert_summary(*, session_id, summary, key_decisions, unresolved_issues) -> UUID` — `pg_insert(MemorySessionSummary).values(...).on_conflict_do_update(index_elements=[MemorySessionSummary.session_id], set_={"summary", "key_decisions", "unresolved_issues", "updated_at": func.now()}).returning(id)` (mirror 57.150; conflict target = the `session_id` UNIQUE). Own-session commit; best-effort caller. (No tenant_id on the row — the session_id is server-authoritative; a session belongs to exactly one tenant via FK.)
- `async recent_for_user(*, tenant_id, user_id, exclude_session_id, limit) -> list[_SummaryRow]` — `SELECT mss.session_id, mss.summary, mss.unresolved_issues, mss.updated_at FROM memory_session_summary mss JOIN sessions s ON s.id = mss.session_id WHERE s.tenant_id=:t AND s.user_id=:u AND mss.session_id != :exclude ORDER BY mss.updated_at DESC LIMIT :n`. `set_config` first (sessions FORCE RLS). Returns small frozen rows (NOT ORM — avoid detached-instance). The explicit `s.tenant_id`/`s.user_id` filter + RLS = defense-in-depth.

### 3.3 Summarizer (US-2) — `session_summarizer.py` (NEW)

- `SessionSummarizer(chat_client: ChatClient, store: DBSessionSummaryStore)` — provider-neutral (ChatClient ABC; NO openai/anthropic import — mirror `MemoryExtractor`).
- `async summarize_and_store(*, messages, session_id, trace_context) -> None` — render messages (local helper, mirror `MemoryExtractor._render_messages`) → `chat_client.chat(_SUMMARY_PROMPT)` temperature 0 → tolerant-parse JSON `{summary, key_decisions[], unresolved_issues[]}` (reuse the MemoryExtractor parse shape) → `store.upsert_summary(session_id, summary, key_decisions, unresolved_issues)`. Empty ledger / blank summary → no-op. Best-effort (caller swallows).
- `_SUMMARY_PROMPT`: "Summarize this conversation. Return strict JSON: {\"summary\": 1-3 sentences capturing the topic + where it left off, \"key_decisions\": [...], \"unresolved_issues\": [...]}. No prose outside the JSON."

### 3.4 Recall (US-3) — `retrieval.py` + `builder.py`

- `MemoryRetrieval.__init__(layers, *, session_summary_store=None)` — additive optional param (default None preserves every existing construction).
- `async recent_sessions(*, tenant_id, user_id, exclude_session_id, top_k=3, trace_context=None) -> list[MemoryHint]` — mirror `profile()`: returns [] when tenant/user None OR store absent; else `store.recent_for_user(...)` → `MemoryHint(layer="session", time_scale="long_term", summary=(summary + optional "; left off: " + unresolved)[:200], full_content_pointer=f"memory_session_summary:{session_id}", timestamp=updated_at, confidence=0.6, relevance_score=0.6, tenant_id=tenant_id)`.
- `builder.py build()` — after the 57.148 `profile()` block (`:265-286`), add a sibling block: when `user_id` is not None, call `recent_sessions(exclude_session_id=state.durable.session_id, top_k=self._recent_sessions_top_k)`, prepend the hints into `memory_layers["session"]` (dedup by hint_id), graceful-degrade on exception (mirror the profile() try/except). The existing `_apply_memory_budget` + scope-grouped render handle the rest. New `_recent_sessions_top_k` ctor field (default 3).

### 3.5 Wiring (US-1/2/3) — factories + handler + router + config

- `_category_factories.py`: `make_chat_session_summary_store(db) -> DBSessionSummaryStore | None` (None when flag off OR db None; mirror `make_chat_message_store`). `make_chat_memory_deps(db)` threads the store into `MemoryRetrieval(layers, session_summary_store=store_or_None)` — gated on `settings.chat_session_summary`. (Both `make_chat_memory_deps` callers — loop builder + extract ctx — get the store for free.)
- `handler.py`: `ChatMemoryExtractContext += summarizer: SessionSummarizer | None`; `build_chat_memory_extractor` builds the summarizer (cheap `profile.cheap` + a `DBSessionSummaryStore`) when the flag is on.
- `router.py`: `_maybe_auto_extract` — after the existing extract, if `ctx.summarizer` is not None, `await ctx.summarizer.summarize_and_store(messages=ledger, session_id=session_id, trace_context=trace_context)` (same loaded `ledger`, best-effort, same try/except). The build gate at `:439-443` extends to `(req.mode == "real_llm" and (settings.chat_memory_auto_extract or settings.chat_session_summary))` so the ctx is built when EITHER is on; each sub-step self-gates.
- `core/config/__init__.py`: `chat_session_summary: bool = True`.

### 3.x What is explicitly NOT done

- Building a new `memory_session` table (Day-0 catch — the designed `memory_session_summary` already exists; reuse it).
- Setting `extracted_to_user_memory` / `extraction_completed_at` to coordinate the summary with the 57.149 auto-extract — designed hook, deferred → carryover `AD-Memory-Session-Summary-Extract-Coordination`.
- Promoting the in-memory `SessionLayer` working-memory dict to DB (CARRY-029).
- Combining extract + summarize into ONE LLM call (two cheap calls per send now) — carryover `AD-Memory-Formation-Combine-Extract-Summarize`.
- Incremental summarization for very long ledgers (re-summarizes the whole ledger each send) — carryover `AD-Memory-Session-Summary-Incremental`.
- Semantic similarity recall / ranking of session summaries (recency-ordered only) — CARRY-026.
- A chat-v2 Inspector surface for session summaries (no new wire event) — carryover `AD-Memory-Session-Summary-Inspector-Phase58`.

### 3.y Validation (US-1..US-5)

Gates: mypy `src` (+ new files + migration) · run_all 11/11 (incl. llm_sdk_leak + rls_policies — UNCHANGED, no new RLS table) · pytest 3022 + new · Vitest 922 (untouched) · mockup 51 (untouched, `diff` empty) · `npm run lint && npm run build` (NO `--silent`; FE untouched so no-op) · black/isort/flake8 clean · LLM-SDK-leak clean. Plus the §US-4 drive-through (MANDATORY).

## 4. File Change List

| # | File | Action |
|---|------|--------|
| 1 | `infrastructure/db/models/memory.py` | EDIT (MemorySessionSummary += updated_at) |
| 2 | `infrastructure/db/migrations/versions/0033_session_summary_updated_at.py` | NEW (additive ADD COLUMN) |
| 3 | `agent_harness/memory/session_summary_store.py` | NEW (upsert + recent_for_user JOIN sessions) |
| 4 | `agent_harness/memory/session_summarizer.py` | NEW (cheap ChatClient → JSON → store) |
| 5 | `agent_harness/memory/retrieval.py` | EDIT (recent_sessions + ctor store) |
| 6 | `agent_harness/memory/__init__.py` | EDIT (exports) |
| 7 | `agent_harness/prompt_builder/builder.py` | EDIT (recall inject block + top_k field) |
| 8 | `api/v1/chat/_category_factories.py` | EDIT (summary-store factory + thread into memory deps) |
| 9 | `api/v1/chat/handler.py` | EDIT (ChatMemoryExtractContext += summarizer; build_chat_memory_extractor) |
| 10 | `api/v1/chat/router.py` | EDIT (_maybe_auto_extract summarize + gate) |
| 11 | `core/config/__init__.py` | EDIT (chat_session_summary flag) |
| 12 | `tests/integration/memory/test_session_summary_store.py` | NEW (real PG: upsert one-per-session, recent JOIN ordering/exclude/per-tenant/per-user) |
| 13 | `tests/unit/agent_harness/memory/test_session_summarizer.py` | NEW (mock ChatClient → store called; empty ledger no-op; JSON parse) |
| 14 | `tests/unit/agent_harness/memory/test_retrieval_recent_sessions.py` | NEW (hints shape; absent store → []; exclude-current) |
| 15 | `tests/unit/agent_harness/prompt_builder/test_builder_session_recall.py` | NEW (prepend into session slot; empty when no store; degrade on error) |
| — | `memory_session_summary` table structure | **REUSED** (only +updated_at; NOT a new table) |
| — | `agent_harness/memory/layers/session_layer.py` | **UNTOUCHED** (CARRY-029) |
| — | `agent_harness/orchestrator_loop/loop.py` / wire schema / frontend | **UNTOUCHED** (wire stays 26) |

## 5. Acceptance Criteria

1. `memory_session_summary` gains `updated_at` (additive, backfill = created_at); migration `0033` up→down→up clean; NO new table, NO RLS change.
2. `DBSessionSummaryStore.upsert_summary` writes exactly one row per session (the `session_id UNIQUE`); a second call UPDATEs summary/key_decisions/unresolved_issues/updated_at, never inserts a 2nd row (real-PG test).
3. `recent_for_user` JOINs `sessions`, returns the user's summaries `updated_at DESC`, EXCLUDES the passed current session, and is per-tenant + per-user isolated (real-PG test, `set_config` + explicit filter).
4. `MemoryRetrieval.recent_sessions()` returns `[]` when the store is absent (byte-identical-off) and `layer="session"` hints otherwise; `PromptBuilder.build()` prepends them into the session slot and degrades on error (unit tests).
5. `chat_session_summary=false` → no store threaded + no summarize call → recall returns [] + formation skipped (byte-identical to 57.150).
6. **Drive-through PASS (MANDATORY, real UI + backend + LLM)** — session A discusses a distinctive topic → after the turn, a `memory_session_summary` row exists for A (summary + key_decisions + unresolved_issues populated, `updated_at` bumps across turns); NEW session B "what were we working on last time?" → agent recalls A's summary (excluding B); a DIFFERENT user sees none of A's summaries. Screenshot + observed-vs-intended in progress.md. (NOT gate-only.)
7. `AD-Memory-Formation-Session-Recall` CLOSED; CHANGE-118 + design note 54 (8-point gate); calibration recorded; navigators + next-phase-candidates updated.

## 6. Deliverables

- [ ] US-1 `memory_session_summary` += updated_at (migration 0033) + `DBSessionSummaryStore`
- [ ] US-2 `SessionSummarizer` + post-send formation wiring (flag-gated)
- [ ] US-3 `recent_sessions()` + builder recall inject + recall wiring (flag-gated)
- [ ] US-4 drive-through PASS (real chat-v2 + Azure: A→B recall + per-user isolation)
- [ ] US-5 CHANGE-118 + design note 54 + retrospective + navigators (AD closed)

## 7. Workload Calibration

- Scope class **NEW `memory-session-recall-spike` 0.60** (Cat 3 new-domain FULL vertical slice: additive migration + new store (with a JOIN read) + new summarizer + new recall method + builder inject + wiring + drive-through. Anchored to `memory-formation-identity-spike` 0.60 (57.148) + `task-primitive-spike` 0.60 (57.140) — same greenfield-Cat-3 + main-flow-wiring shape; the Day-0 reuse-existing-table catch REMOVES the new-table/RLS work (≈ −1.5 hr) but the JOIN read + structured-JSON summary + the richer drive-through balance it. The real-code core (≥~3.5 hr: store + summarizer + recall + inject + tests) holds the 0.60 per the 57.137 lesson, NOT a tiny-code-wrapped-in-ceremony 0.85. If a 2nd `memory-session-recall-spike` diverges > 30%, re-point.)
- **Agent-delegated: no** (parent-direct, consistent with the whole memory arc 57.148/149/150). `agent_factor` 1.0 → 3-segment form.
- Bottom-up est ~7.0 hr (migration+ORM ~0.5 / store ~1.5 / summarizer ~1.0 / recall+inject ~1.5 / wiring ~1.0 / tests ~1.5) → class-calibrated commit ~4.2 hr (mult 0.60). Day-4 retro Q2 verifies.

## 8. Dependencies & Risks

| Risk | Mitigation |
|------|------------|
| Recall JOIN sees no `sessions` rows (FORCE RLS) | the store's own session `set_config('app.tenant_id', tenant, true)` before the JOIN (mirror `DBMessageStore._set_tenant`); explicit `s.tenant_id`/`s.user_id` filter = defense-in-depth. |
| Stale `--reload` / orphan spawn-worker masks the new wiring at drive-through | Risk Class E — clean restart: kill stale uvicorn + verify sole port owner + startup log; the BackgroundTask + new store open own sessions. |
| BackgroundTask runs AFTER the response → B's first turn has no B-summary yet (correct: recall excludes B anyway) | By design — `recent_sessions(exclude=current)` never surfaces the current session; the drive-through validates A is recalled in a SEPARATE new session B. |
| Two cheap LLM calls per send (extract + summarize) | Accepted for the spike (both cheap-tier, background, best-effort); combine-into-one is carryover `AD-Memory-Formation-Combine-Extract-Summarize`. |
| `make_chat_memory_deps` new ctor arg breaks 2 callers | Additive default-None on `MemoryRetrieval.__init__`; Day-0 D-make-memory-deps-callers confirmed both callers unpack `(retrieval, layers)` unchanged. |
| Long ledger → expensive re-summarize each send | Accepted (bounded by compaction); incremental = carryover `AD-Memory-Session-Summary-Incremental`. |

## 9. Out of Scope (this sprint; → separate slices / ADs)

- A `memory_session` new table — superseded by reusing `memory_session_summary` (Day-0 catch).
- `extracted_to_user_memory` / `extraction_completed_at` coordination with the 57.149 auto-extract — `AD-Memory-Session-Summary-Extract-Coordination`.
- An `idx_memory_session_summary_updated` index — skipped (per-user result set is tiny); add if recall latency shows up.
- In-memory `SessionLayer` → DB promotion — CARRY-029.
- Semantic/vector ranking of session summaries — CARRY-026.
- Combine extract+summarize into one LLM call — `AD-Memory-Formation-Combine-Extract-Summarize`.
- Incremental (non-full-ledger) summarization — `AD-Memory-Session-Summary-Incremental`.
- chat-v2 Inspector surface for session summaries — `AD-Memory-Session-Summary-Inspector-Phase58`.
