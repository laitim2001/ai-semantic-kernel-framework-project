# Sprint 57.147 — Checklist (knowledge connector Slice 3a: per-tenant KB isolation)

[Plan](./sprint-57-147-plan.md)

---

## Day 0 — Plan-vs-Repo Verify (三-prong) + Branch

### 0.1 Three-prong Day-0 verify (against `main` HEAD `91ade673`)
- [x] **Prong 1 — path verify**: edit targets exist (`vector_index.py`/`tools.py`/`connector.py`/`knowledge_index.py`/`api/main.py`/the 2 test files); `CHANGE-114` + design note `51-*` free; `tests/fixtures/knowledge/` NEW path clear
- [x] **Prong 2 — content verify** (drift → progress.md):
  - [x] **D-loop-exec-ctx-tenant** (#1 RISK) — 🟢 GREEN: `loop.py:2925-2929` builds `ExecutionContext(tenant_id=ctx.tenant_id)` + `:2957-2959` `execute(tc, context=exec_ctx)`; `:3508-3515` resume path same
  - [x] **D-handler-arity-dispatch** — 🟢 `executor.py:213` `_handler_takes_context` generic per-handler cache (`:308-320`) covers business-domain handlers
  - [x] **D-memory-mirror** — 🟢 `memory_tools.py:81-119,254-289` `_detect_forged_scope_args` + dual-arity current (mirror source)
  - [x] **D-startup-ingest** — 🟢 `api/main.py:403-423` `_ingest_knowledge` calls `index.ingest()` (no tenant) → MUST rework to lazy (done: `_warm_knowledge_index`)
  - [x] **D-namespace-api** — 🟢 `collection_name(tid,"kb")` + `payload_filter(tid)` + `QdrantVectorStore.search(payload_filter=)` confirmed unchanged
- [x] **Prong 3 — schema verify**: N/A (no DB table / migration / ORM column — Qdrant collections only, no Postgres)
- [x] **D-baselines** — knowledge module 34 pass/1 skip; full suite trusted from 57.146 (pytest 2980+6skip · wire 26 · Vitest 922 · mockup 51 · mypy 0/392 · run_all 11/11)
- [x] **Catalog drift** — progress.md Day-0 table (5 D-… findings, all GREEN, no scope shift)
- [x] **Go/no-go** — D-loop-exec-ctx-tenant GREEN → **GO** (0% scope shift)

### 0.2 Branch
- [x] `git checkout -b feature/sprint-57-147-knowledge-per-tenant-isolation` (from `main` `91ade673`)

---

## Day 1 — Isolation core: vector index + tool handler (US-1/US-2)

### 1.1 Per-tenant vector index — `vector_index.py`
- [x] **`search(query, top_k, tenant_id)` per-tenant collection + payload filter**
  - DoD: collection = `QdrantNamespaceStrategy.collection_name(tenant_id,"kb")`; `store.search(..., payload_filter=QdrantNamespaceStrategy.payload_filter(tenant_id))`; lazy `await self.ingest(tenant_id)` first ✅
  - Verify: `pytest tests/unit/business_domain/knowledge/test_vector_index.py -q` ✅
- [x] **`ingest(tenant_id)` per-tenant corpus + payload tenant_id**
  - DoD: per-tenant `LocalDocsConnector(<root>/<tenant_id>/ or <root>)` via `_connector_for`; upsert payload += `{"tenant_id": str(tenant_id)}`; idempotent skip when `count==expected`; `_EMBED_BATCH=16` kept ✅
  - Verify: `test_vector_index.py::test_ingest_is_per_tenant_collection` + `::test_lazy_ingest_idempotent_per_tenant` ✅

### 1.2 Dual-arity tool handler + forgery guard — `tools.py`
- [x] **`make_knowledge_search_handler` → dual-arity `(call, context: ExecutionContext)`**
  - DoD: `_reject_forged_scope` mirrors `memory_tools._detect_forged_scope_args`; `vector_index.search(query, top_k, tenant_id=context.tenant_id)`; fail-soft `except` → keyword fallback preserved; schema unchanged (no tenant_id property) ✅
  - Verify: `test_knowledge_tools.py::test_handler_threads_context_tenant_to_vector_index` + `::test_handler_rejects_forged_tenant_arg` + `::test_handler_allows_matching_tenant_arg` ✅

### 1.x partial gate
- [x] backend `black . && isort . && flake8 . && mypy .` clean on touched files ✅ (fixed 2 docstring E501 + 1 MHist 2-line→1-line)

---

## Day 2 — Composition + startup + tests (US-3)

### 2.1 Composition + startup rework — `knowledge_index.py` + `api/main.py`
- [x] **Singleton process-wide; tenant_id per-call; lazy startup**
  - DoD: index takes `docs_root` (per-tenant connector resolved inside `ingest`); `_ingest_knowledge`→`_warm_knowledge_index` drops blocking all-corpus ingest → lazy per-tenant; flag-off stays no-op ✅
  - Verify: full pytest (knowledge_index existing tests pass; startup log `ready (lazy per-tenant ingest)` at drive-through) ✅

### 2.2 Per-tenant fixtures + isolation test
- [x] **2 distinct corpora + isolation unit test**
  - DoD: isolation tests use self-contained **tempdir** per-tenant subfolders (committed `tests/fixtures/` NOT needed — drive-through uses real-tenant-UUID corpora; scope reduction noted progress Day 1-2); `test_vector_index.py::test_tenant_a_cannot_retrieve_tenant_b_doc` (A's query for B-unique → 0 A-hits) + `::test_payload_filter_rejects_cross_tenant_row` ✅
  - Verify: `pytest tests/unit/business_domain/knowledge/ -q` → 42 pass/1 skip ✅

### 2.x Full gate
- [x] mypy `src` **0/392** · run_all **11/11** (incl. `check_llm_sdk_leak`) · backend pytest **2988**(+8) · Vitest 922 (FE untouched) · mockup 51 (FE untouched) · black/isort/flake8 clean · LLM-SDK-leak clean ✅

---

## Day 3 — Drive-through (US-4) — real chat-v2 + real Azure embedding + real Qdrant (2 tenants)
_(MANDATORY — user-facing main-flow capability; NOT gate-only.)_

### 3.1 Clean restart (Risk Class E)
- [x] `Win32_Process` sweep: single stale uvicorn (PID 57560, no `--reload` child), killed; port 8000 FREE + 0 python remaining; node (frontend@3007 + claude code) UNTOUCHED; relaunched single-process no-`--reload` + `KNOWLEDGE_VECTOR_ENABLED=1` + per-tenant corpora seeded ✅

### 3.2 Drive-through (MANDATORY — NOT gate-only)
- [x] Tenant alpha (real JWT) → Falcon query → `knowledge_search` cites ONLY `falcon.md` (codename Skyhook); BONUS output-ESCALATE HITL → approve ✅
- [x] Tenant beta (real JWT) → Condor query → cites ONLY `condor.md` (codename Nightjar), 0 `falcon.md` leak ✅
- [x] **THE isolation proof**: alpha queries Condor (beta's) → **0 `condor.md`, agent "I did not find Project Condor"** (judge 0.98); Qdrant 2 distinct `tenant_428d…_kb` / `tenant_54e4…_kb`; bidirectional A↛B + B↛A ✅
- [x] Per-control AP-4 walk: knowledge_search fires (TOOL_EXEC 2265ms), real snippets render, source paths real, no fixture/DEMO leakage ✅
- [x] Screenshot (`sprint-57-147-drivethrough-beta-condor-isolation.png`) + observed-vs-intended → progress.md Day 3 (trace_ids + collection names) ✅

---

## Day 4 — CHANGE-114 + closeout

### 4.1 CHANGE-114 + design note
- [x] **`CHANGE-114-knowledge-per-tenant-isolation.md`** (gap + fix + 2-tenant drive-through PASS + AD-half closed) ✅
- [x] **`51-knowledge-per-tenant-isolation-design.md`** (spike design note — 8-point gate; the per-tenant vector-isolation pattern Cat 3 memory will reuse) ✅

### 4.2 Closeout
- [x] retrospective.md Q1-Q7 + calibration (`knowledge-per-tenant-isolation-spike` 0.55, 1st data point, ratio ~1.0-1.15 IN band → KEEP) ✅
- [x] Final gate sweep: mypy 0/392 · run_all 11/11 · pytest 2988 · Vitest 922 · mockup 51 · lint · LLM-SDK-leak ✅
- [x] Navigators: CLAUDE.md Current-Sprint + Last-Updated · MEMORY.md pointer + subfile · next-phase-candidates (CLOSE isolation half of `AD-Knowledge-Connector-RBAC-Citation-Slice3`; RBAC + citation stay open) · sprint-workflow matrix (new `knowledge-per-tenant-isolation-spike` 0.55 row) ✅
- [x] Anti-pattern self-check (retro Q5): AP-2/3/4/6/8/11 → no violations; v2 lints 11/11 ✅
- [ ] **Commit** → ⏳ PR push + open → CI → merge: PENDING USER CONFIRMATION (push is outward-facing per Developer Preferences) → post-merge status flip after gh-verified MERGED
