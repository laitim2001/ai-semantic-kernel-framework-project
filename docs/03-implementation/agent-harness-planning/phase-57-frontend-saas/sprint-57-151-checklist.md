# Sprint 57.151 — Checklist (cross-session conversation recall via rolling session summaries)

[Plan](./sprint-57-151-plan.md)

---

## Day 0 — Plan-vs-Repo Verify (三-prong) + Branch

### 0.1 Three-prong Day-0 verify (against `main` HEAD `f664f34d`) — DONE (drift caught, plan revised)
- [x] **Prong 1 — path verify**: EDIT targets exist — `memory.py`, `retrieval.py`, `memory/__init__.py`, `builder.py`, `_category_factories.py`, `handler.py`, `router.py`, `core/config/__init__.py`; NEW free — `0033_session_summary_updated_at.py`, `session_summary_store.py`, `session_summarizer.py`, the 4 test files, `CHANGE-118-*.md`; migration `0032` is latest (→ 0033 next)
- [x] **Prong 2 — content verify** (drift → progress.md):
  - [x] **D-table-already-exists** 🔴 MAJOR — `memory_session_summary` ALREADY created (`0007_memory_layers.py:221`) + ORM'd (`MemorySessionSummary`, `memory.py:284`) + designed (`09-db-schema-design.md:481`, "Layer 5 持久化"): `session_id UNIQUE` + `summary` + `key_decisions`/`unresolved_issues` JSONB + `extracted_to_user_memory`. → REVISE: reuse it; drop new-table migration; only add `updated_at`. (Check-Existing 鐵律; saved ~1.5 hr + AP-3 duplicate-table + wrong-RLS migration.)
  - [x] **D-junction-no-rls** — `0009_rls_policies.py:27-29` lists `memory_session_summary` as junction (NO direct RLS, tenant via session FK); `sessions` IS FORCE RLS (`:79`) → recall JOIN needs `set_config`. NO `rls_policies` lint change (no new RLS table).
  - [x] **D-no-updated-at** — `MemorySessionSummary` has only `created_at` → add additive `updated_at` (0033, backfill = created_at) for rolling recency.
  - [x] **D-sessions-cols** — `Session(Base, TenantScopedMixin)` → `tenant_id` (mixin) + `user_id` (`sessions.py:86`) → recall JOIN filters both.
  - [x] **D-make-memory-deps-callers** — 2 callers `handler.py:364` + `:848`, both unpack `(retrieval, layers)`; threading `MemoryRetrieval(..., session_summary_store=)` is additive (default-None) — breaks neither.
  - [x] **D-memoryhint-fields** — `MemoryHint` required: hint_id/layer/time_scale/summary/confidence/relevance_score/full_content_pointer/timestamp (`_contracts/memory.py:52-71`).
  - [x] **D-upsert-pattern** — `user_layer.py:170-199` (57.150 `pg_insert … on_conflict_do_update`; here conflict target = `index_elements=[session_id]`) + `message_store.py:111-122` (own-session `set_config` FORCE-RLS) are the patterns to mirror.
  - [ ] **D-builder-session-slot** — confirm at impl time that `memory_layers["session"]` is normally empty on the chat path so the prepend renders the recall hints cleanly
- [x] **Prong 3 — schema verify**: reuse `memory_session_summary` (`memory.py:284`); only additive `updated_at`; `0032` latest → `0033`; NO new RLS table (junction by design)
- [ ] **D-baselines** — pytest 3022 · wire 26 · Vitest 922 · mockup 51 · mypy 0/393 · run_all 11/11 (re-verify Day 2 + Day 4)
- [x] **Catalog drift** — progress.md Day-0 table (D-table-already-exists + 6 D-IDs + finding + implication)
- [x] **Go/no-go** — scope-shift ~15-20% (storage mechanics: new-table → reuse+additive-column + JOIN read), NET REDUCTION, approved forks + user-facing behavior UNCHANGED → proceed (no re-approval needed — corrects implementation to match design)

### 0.2 Branch
- [x] `git checkout -b feature/sprint-57-151-memory-session-recall` (from `main` `f664f34d`)

---

## Day 1 — Storage: reuse table + updated_at + DBSessionSummaryStore (US-1)

### 1.1 MemorySessionSummary += updated_at
- [x] **`memory.py`**: add `updated_at: Mapped[datetime]` (DateTime tz, nullable=False, server_default=func.now()) to `MemorySessionSummary` (everything else already exists)
  - DoD: additive; mypy clean ✅
  - Verify: `mypy ... memory.py` ✅ Success

### 1.2 Migration 0033 (additive)
- [x] **`0033_session_summary_updated_at.py`** (revises 0032): `add_column updated_at` (server_default now()) + `UPDATE … SET updated_at = created_at` backfill; downgrade `drop_column`. NO table create, NO RLS change
  - DoD: additive only; backfill sets existing rows to created_at ✅ (revision id ≤ 32 chars — D-revision-id-len)
  - Verify: `alembic upgrade head` → `downgrade -1` → `upgrade head` ✅ clean (final head 0033; updated_at + dedup_key both verified present)

### 1.3 DBSessionSummaryStore
- [x] **`session_summary_store.py`**: `upsert_summary(session_id, summary, key_decisions, unresolved_issues)` (pg_insert ON CONFLICT index_elements=[session_id] → set summary/key_decisions/unresolved_issues/updated_at, returning id) + `recent_for_user(tenant_id, user_id, exclude_session_id, limit)` (JOIN sessions WHERE tenant+user, session != exclude, ORDER BY updated_at DESC LIMIT) returning small frozen rows; own-session + `set_config` (sessions FORCE RLS)
  - DoD: mirrors `DBMessageStore` session pattern + 57.150 upsert; mypy clean ✅
  - Verify: `mypy ... session_summary_store.py` ✅ Success

### 1.x Partial gate
- [x] mypy clean (new + edited Day-1 files) · migration up→down→up clean · black/isort/flake8 clean (2 E501 docstring lines trimmed)

---

## Day 2 — Formation + Recall + wiring + tests (US-2, US-3) + full gate

### 2.1 SessionSummarizer (US-2)
- [x] **`session_summarizer.py`**: `SessionSummarizer(chat_client, store)` + `summarize_and_store(messages, session_id, trace_context)` cheap-tier ChatClient → tolerant-parse JSON `{summary, key_decisions[], unresolved_issues[]}` → `store.upsert_summary(...)`; empty ledger / blank → no-op; provider-neutral (no openai/anthropic import)
  - DoD: mirrors `MemoryExtractor` shape; llm_sdk_leak clean ✅ (+ AP-8 allowlist entry, D-ap8-summarizer-allowlist)
  - Verify: `pytest test_session_summarizer.py` ✅ 6 passed

### 2.2 recent_sessions() + builder inject (US-3)
- [x] **`retrieval.py`**: `MemoryRetrieval.__init__(..., session_summary_store=None)` + `SessionSummaryReader` Protocol + `recent_sessions(tenant,user,exclude_session_id,top_k)` → list[MemoryHint](layer="session"); [] when store/tenant/user None ✅
- [x] **`builder.py`**: sibling block after profile() (`:265-286`) — call `recent_sessions(exclude=state.durable.session_id)`, prepend into `memory_layers["session"]` (dedup hint_id), try/except graceful-degrade; new `_recent_sessions_top_k` field (default 3); D-builder-session-slot confirmed (session slot normally empty) ✅
  - DoD: byte-identical when store absent; degrade never crashes build ✅
  - Verify: `pytest test_retrieval_recent_sessions.py test_builder_session_recall.py` ✅ 5 + 4 passed

### 2.3 Wiring + config (US-1/2/3)
- [x] **`_category_factories.py`**: `make_chat_session_summary_store(db)` + thread store into `make_chat_memory_deps` `MemoryRetrieval(..., session_summary_store=)` (gated `settings.chat_session_summary`); **`handler.py`**: `ChatMemoryExtractContext.extractor → Optional + += summarizer`; `build_chat_memory_extractor` builds both gated by their flags; **`router.py`**: `_maybe_auto_extract` runs extractor (if not None + user) + summarizer (if not None) sharing one ledger + extends build gate to `auto_extract OR session_summary`; **`core/config`**: `chat_session_summary: bool = True`
  - DoD: flag off → no store threaded + no summarize → byte-identical 57.150; mypy clean ✅
  - Verify: `pytest tests/.../chat/ -k "memory or extract or summary"` + `mypy src` ✅ (test_memory_auto_extract 5 passed; mypy 0/396)

### 2.4 Memory store integration tests
- [x] **`test_session_summary_store.py`** (real PG, commit→flush shared-session per Risk C; seed a real `sessions` row for the JOIN): upsert same session ×2 → 1 row (summary/decisions refreshed); recent_for_user JOIN ordering updated_at DESC; exclude-current; per-tenant isolation; per-user isolation; empty → []
  - Verify: `pytest tests/integration/memory/test_session_summary_store.py` ✅ 5 passed

### 2.5 Full gate
- [x] mypy `src` 0/396 · run_all 11/11 (incl. llm_sdk_leak + rls_policies UNCHANGED) · backend pytest 3042 passed/6skip (+20) · Vitest 922 (untouched) · mockup 51 (untouched) · black/isort/flake8 clean · migration up→down→up clean

---

## Day 3 — Drive-through (US-4) — real UI + real backend + real LLM

### 3.1 Clean restart (Risk Class E)
- [x] Killed stale port-8000 backend (PID 43620, 57.150 leftover) + 0 orphan spawn-workers (Win32_Process sweep); port 8000 sole owner; fresh no-reload uvicorn branch code (PID 61048, `CHAT_SESSION_SUMMARY` default ON, migrated DB head 0033); startup clean (`load_dotenv`→Azure); node vite (31616) + claude-code UNTOUCHED

### 3.2 Drive-through (MANDATORY — NOT gate-only) — real Azure gpt-5.2 — ALL PASS
- [x] **Formation (session A `bac53436`, dan)**: distinctive turn (billing MongoDB→Postgres / dual-write / invoices JSONB-vs-table) → agent acknowledged + Verification 0.99 (RENDERED) → post-send BackgroundTask wrote `memory_session_summary` with ALL 3 columns populated (summary + key_decisions + unresolved_issues); DB inspector confirmed
- [x] **THE fix — recall (NEW session B `760d5db9`, dan)**: "what were we working on last session?" → agent recalled A's arc verbatim (billing migration / dual-write / invoice line items JSONB vs separate table), Verification 0.98; B excludes itself (B's summary absent at recall anyway). Bonus: 57.149 "Project Aurora" user fact coexists
- [x] **Per-user isolation (priya, same tenant)**: same question → "I don't have any stored notes or session memory…" + only priya's OWN SOC 2 profile; **0 leak** of dan's billing content (`dan_content_leak: false`); `memory_search` hints `[]`
- [x] Screenshots (`dt151-recall-session-b.png` + `dt151-isolation-priya.png`) + observed-vs-intended → progress.md Day 3 + `artifacts/snapshot.md`

---

## Day 4 — CHANGE-118 + design note 54 + closeout

### 4.1 CHANGE-118 + design note 54
- [x] **`CHANGE-118-memory-session-recall.md`** (gap: facts recalled but not conversation arc → new session amnesia; fix: fill the designed `memory_session_summary` via rolling upsert + recent_sessions() recall; migration 0033 additive updated_at; drive-through STRONG PASS; AD closed)
- [x] **design note 54** (`54-memory-session-recall-design.md`, spike sprint — 8-point quality gate self-checked: section→US / file:line per claim / decision matrix (6 decisions: reuse-table vs new-table; rolling-per-send vs lazy; etc.) / verify command / test fixture / open-invariant boundary / rollback / 17.md cross-ref — additive, no new contract)

### 4.2 Closeout
- [x] retrospective.md Q1-Q7 + calibration (NEW `memory-session-recall-spike` 0.60, 1st pt ~1.05 IN band → KEEP; Day-0 reuse-table catch noted)
- [x] Final gate sweep: mypy 0/396 · run_all 11/11 · pytest 3042/6skip (Day 2.5; no code change since) · Vitest 922 · mockup 51 · migration up→down→up · llm_sdk_leak (in run_all)
- [x] Navigators: CLAUDE.md Current-Sprint (PR-pending) + Last-Updated · MEMORY.md pointer + subfile `project_phase57_151_memory_session_recall.md` · next-phase-candidates (CLOSE `AD-Memory-Formation-Session-Recall` + new carryover ADs; arc 57.148→151 closed) · sprint-workflow matrix (NEW `memory-session-recall-spike` 0.60 row)
- [x] Anti-pattern self-check (retro Q5): AP-2/3/4/6/8/11 all ✅/N/A; v2 lints 11/11 (incl. llm_sdk_leak + rls_policies)
- [ ] **Commit** → ⏳ PR push + open → CI → merge: PENDING USER CONFIRMATION (push is outward-facing per Developer Preferences) → post-merge status flip after gh-verified MERGED
