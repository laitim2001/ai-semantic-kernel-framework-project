# Sprint 57.147 Plan — knowledge connector Slice 3a: per-tenant KB isolation

**Summary**: Third slice of the knowledge-connector arc — the **per-tenant isolation** half of `AD-Knowledge-Connector-RBAC-Citation-Slice3`. Today 57.146's `KnowledgeVectorIndex` retrieves from a SINGLE shared Qdrant collection (`knowledge_local_docs`) with no `tenant_id` — every tenant's agent reads the same vector store, which violates the multi-tenant 鐵律 the moment real per-tenant company docs are ingested. This sprint threads `tenant_id` end-to-end so each tenant gets its own Qdrant collection (`tenant_<hex>_kb`) + a defense-in-depth payload filter, fed by a per-tenant docs subfolder (shared-root fallback preserves 57.146 single-tenant behavior). The design **mirrors the established `memory_search` pattern** (dual-arity `(ToolCall, ExecutionContext)` handler + forgery guard) — NOT a new mechanism; every building block (`QdrantNamespaceStrategy "kb"`, `payload_filter`, `QdrantVectorStore.search(payload_filter=)`, the executor's arity auto-dispatch) already exists. **Drive-through MANDATORY** (this is a user-facing main-flow capability): 2 tenants with distinct corpora → tenant A's query retrieves ONLY A's docs, B's unique doc is invisible (falsifiable cross-tenant isolation). **Design note required** (spike — the per-tenant vector-isolation pattern is reused by the future Cat 3 memory semantic axis).

**Status**: Draft (scope approved via 3 AskUserQuestion picks 2026-06-27: Slice 3 → 3a per-tenant isolation → corpus option A per-tenant subfolder + shared fallback)
**Branch**: `feature/sprint-57-147-knowledge-per-tenant-isolation`
**Base**: `main` HEAD `91ade673` (Sprint 57.146 flip PR #347 merged — Slice 2 embedding/Qdrant)
**Slice**: closes the **isolation half** of `AD-Knowledge-Connector-RBAC-Citation-Slice3` (arc slice 3a/N; RBAC per-doc = 3b, citation governance = 3c, both deferred)
**Scope decisions**: (a) thin slice = per-tenant isolation ONLY (RBAC per-doc + citation = later slices); (b) corpus = per-tenant subfolder `<root>/<tenant_id>/` + shared-root fallback (option A — meaningful falsifiable drive-through); (c) ingest = lazy per-tenant ensure-on-first-search (idempotent; defers the startup-blocking-all-tenants scale problem to `AD-Knowledge-Connector-Ingest-Scale`); (d) mirror `memory_search` dual-arity + `ExecutionContext` + forgery guard (NOT a new mechanism — executor already auto-dispatches arity)

---

## 0. Background

### The gap (`AD-Knowledge-Connector-RBAC-Citation-Slice3`, isolation half)

- 57.146 shipped real semantic retrieval but into ONE shared collection `knowledge_local_docs` (`vector_index.py:44`).
- `KnowledgeVectorIndex.search()` / `ingest()` carry NO `tenant_id`; the handler is single-arity `(ToolCall) -> str` so it cannot see the caller's tenant.
- The per-tenant isolation building blocks exist (`QdrantNamespaceStrategy` Sprint 49.3; `QdrantVectorStore.search(payload_filter=)` 57.146) but are **unconsumed** — exactly the kind of latent multi-tenant hole the 鐵律 forbids.

### Why it matters (the missing capability)

The moment a real tenant's company documents are ingested (Slice 3 external-source goal), a shared collection leaks tenant A's docs to tenant B's agent — a compliance + security failure. Per-tenant vector isolation is the **safe foundation** that every subsequent real-source slice must sit on; it is a multi-tenant SaaS 治理剛需 (reality-audit §7.3), not an optimization.

### Root cause (recon code read, file:line; ALL re-verified §checklist 0.1)

| Layer | Reality (on `main` HEAD `91ade673`) | Anchor |
|-------|--------------------------------------|--------|
| Vector index | single shared collection, no tenant_id | `business_domain/knowledge/vector_index.py:44,112,119` |
| Tool handler | single-arity `(ToolCall) -> str`, no tenant context | `business_domain/knowledge/tools.py:91,103,116` |
| Per-tenant naming | EXISTS, unconsumed | `infrastructure/vector/qdrant_namespace.py:76,92` |
| Store filter | `search(payload_filter=None)` ALREADY accepts it | `infrastructure/vector/qdrant_client.py:114-119` |
| Executor arity dispatch | auto-detects `(call, ctx)` vs `(call)`, threads `ExecutionContext` | `agent_harness/tools/executor.py:102-108,209-216,308-320` |
| Loop → executor tenant | builds `ExecutionContext(tenant_id=ctx.tenant_id, …)` | `agent_harness/orchestrator_loop/loop.py:2925-2926,3508-3509` |
| Established mirror | `memory_search` dual-arity + forgery guard | `agent_harness/tools/memory_tools.py:81-119,262` |

→ Fix = (1) make `knowledge_search` dual-arity so it receives `context.tenant_id`; (2) thread `tenant_id` into `KnowledgeVectorIndex.search/ingest` → per-tenant collection name + payload filter + per-tenant corpus; (3) lazy idempotent per-tenant ingest. No executor / loop / migration change.

### The design (backend-only: thread tenant_id through 3 files + per-tenant corpus + lazy ingest + tests/fixtures)

```
knowledge_search handler  (tools.py)
  single-arity (call) ──▶ dual-arity (call, context: ExecutionContext)   [mirror memory_search]
    + _detect_forged_scope_args(args, context)  (reject LLM-supplied tenant_id)
    + vector_index.search(query, top_k, tenant_id=context.tenant_id)

KnowledgeVectorIndex  (vector_index.py)
  search(query, top_k, tenant_id)
    collection = QdrantNamespaceStrategy.collection_name(tenant_id, "kb")
    await self.ingest(tenant_id)                       # lazy, idempotent (count==expected → skip)
    store.search(collection, qvec, top_k, payload_filter(tenant_id))   # defense-in-depth
  ingest(tenant_id)
    connector = per-tenant LocalDocsConnector(<root>/<tenant_id>/ or <root>)   # option A + fallback
    upsert payload += {"tenant_id": str(tenant_id)}    # so payload_filter can match

composition  (knowledge_index.py)  — singleton stays process-wide; tenant_id is a SEARCH-TIME arg
startup ingest  (api/main.py)  — drop the blocking all-corpus ingest; lazy per-tenant on first search
```

WHY option A (per-tenant subfolder) over B (shared corpus, structural-only): only distinct per-tenant content makes the isolation drive-through **falsifiable** (A queries B's unique doc → 0 hits). B would pass gate but prove nothing — a retreat to gate-only (reality-audit §9 north star).

### Ground truth (recon head-start — code read on `main` HEAD `91ade673`; ALL re-verified §checklist 0.1)

- `qdrant_namespace.py:88` — collection name = `tenant_<16-hex>_<layer>`; `:103` payload filter `{"must":[{"key":"tenant_id","match":{"value":<uuid>}}]}`.
- `qdrant_client.py:127` — `models.Filter.model_validate(payload_filter)` already wired; default None = today's behavior.
- `executor.py:209-216` — dual-arity handlers get `ctx`; single-arity unchanged → backward-compatible.
- `vector_index.py:94` — `ingest()` idempotent skip when `count == expected` (per-tenant lazy ensure rides this).
- `tools.py:117` — existing fail-soft `except` keeps the keyword fallback (preserve it).

**Baselines (57.146 closeout)**: pytest 2980 (+6 skip) · wire 26 · Vitest 922 · mockup 51 · mypy 0/392 · run_all 11/11. Re-verify Day-0.

### STALE / drift findings (Day-0; full detail → progress.md — placeholder, filled in §checklist 0.1)

- **D-loop-exec-ctx-tenant** — confirm the chat 主流量 path actually reaches `loop.py:2925/3508` `ExecutionContext(tenant_id=ctx.tenant_id)` (vs a path that calls `executor.execute()` with no context → `tenant_id=None`). The whole sprint gates on a real tenant_id arriving. **#1 Day-0 risk.**
- **D-handler-arity-dispatch** — confirm `knowledge_search` registered into the SAME `handlers` dict the executor arity-dispatches (it is, via `register_knowledge_tools`); re-grep `executor.py:_is_dual_arity` covers business-domain handlers.
- **D-tenant-folder-name** — decide folder key: full `str(tenant_id)` (human-debuggable) vs the 16-hex prefix (matches collection). Plan picks full uuid; verify no path-safety regression in `LocalDocsConnector` (it `.resolve()`-confines).
- **D-startup-ingest** — `api/main.py:_ingest_knowledge` currently ingests the shared collection at startup; confirm removing/guarding it doesn't break the flag-off path (it must stay a no-op when `KNOWLEDGE_VECTOR_ENABLED=0`).

## 1. Sprint Goal

Thread `tenant_id` end-to-end through the knowledge vector path so retrieval is per-tenant isolated (own collection + payload filter + own corpus), **proven by a 2-tenant drive-through** on real chat-v2 + real Azure embedding + real Qdrant: tenant A retrieves only A's docs; B's unique doc is invisible to A (and vice-versa). PROVEN by: full gate (mypy/pytest/run_all incl. `check_llm_sdk_leak`/lint) + the MANDATORY 2-tenant drive-through (NOT gate-only). Produces **CHANGE-114** + design note `51-knowledge-per-tenant-isolation-design.md` (spike).

## 2. User Stories

- **US-1** (isolation core): 作為平台,我希望每個租戶的知識檢索打到自己的 Qdrant collection + 帶 tenant_id payload filter,以便一個租戶的 agent 永遠看不到別租戶的文件。
- **US-2** (tenant context): 作為 `knowledge_search` 工具,我希望從 `ExecutionContext`(伺服器權威,來自 JWT)拿 tenant_id 而非 LLM 參數,並拒絕偽造的 tenant 參數,以便隔離不可被 prompt 繞過。
- **US-3** (per-tenant corpus): 作為 ingest,我希望讀 `<root>/<tenant>/` 各租戶語料(無子夾則 fallback 共享 root),以便隔離可被真正證偽(A 查不到 B 的獨有文件)。
- **US-4** (drive-through, MANDATORY): 作為使用者,我希望在真 chat-v2 上看到租戶 A 問只引用 A 的來源、看不到 B 的文件,以便隔離是實機驗證而非 gate-only。
- **US-5** (closeout): CHANGE-114 + design note + retro + navigators + AD half closed.

## 3. Technical Specifications

### 3.0 Architecture (backend-only; NO migration / NO wire / NO frontend)

```
EDIT  business_domain/knowledge/vector_index.py   tenant_id in search/ingest; namespace collection; payload filter; per-tenant connector; lazy ensure
EDIT  business_domain/knowledge/tools.py          knowledge_search → dual-arity (call, ExecutionContext) + forgery guard + thread tenant_id
EDIT  business_domain/knowledge/connector.py      (if needed) per-tenant root resolver helper — else resolve in vector_index
EDIT  api/v1/chat/knowledge_index.py              singleton stays process-wide; drop build-time single connector → per-tenant at search time
EDIT  api/main.py                                 rework _ingest_knowledge: drop blocking all-corpus startup ingest → lazy per-tenant
NEW   tests/.../test_vector_index.py (additions)  per-tenant collection name + payload filter + lazy idempotent ingest
NEW   tests/.../test_knowledge_tools.py (adds)    dual-arity + forgery reject + tenant threading + 2-tenant isolation
NEW   tests/fixtures/knowledge/<tenantA>/, <tenantB>/   distinct .md corpora for the isolation test
UNTOUCHED  qdrant_client.py · qdrant_namespace.py · executor.py · loop.py · adapters/*
```

### 3.1 Vector index per-tenant (US-1/US-3) — `vector_index.py`

- `search(self, query, top_k, tenant_id: UUID)` — collection via `QdrantNamespaceStrategy.collection_name(tenant_id, "kb")`; `await self.ingest(tenant_id)` first (idempotent); pass `QdrantNamespaceStrategy.payload_filter(tenant_id)` to `store.search`.
- `ingest(self, tenant_id: UUID)` — build per-tenant `LocalDocsConnector` (`<root>/<tenant_id>/` if dir else `<root>`); upsert payload `{"source","snippet","tenant_id": str(tenant_id)}`. Keep `_EMBED_BATCH=16`.
- `__init__` keeps `embedder`/`store` but the connector becomes per-tenant-resolved (root path stored, connector built per tenant). Mirror anchor: `qdrant_namespace.py:76,92`.

### 3.2 Tool handler dual-arity + forgery guard (US-2) — `tools.py`

- `make_knowledge_search_handler` → `async def handler(call, context: ExecutionContext)`; reuse the `_detect_forged_scope_args(args, context)` shape from `memory_tools.py:81` (reject LLM-supplied `tenant_id`/`user_id`/`session_id` that disagree with context).
- Call `vector_index.search(query, top_k, tenant_id=context.tenant_id)`. Keep the fail-soft `except` → keyword fallback (the keyword path stays single-tenant/shared — acceptable: keyword is the degraded path; note in design note).
- `knowledge_search` schema MUST NOT add tenant_id (LLM cannot mention it — schema-invalid before handler), exactly like `MEMORY_SEARCH_SPEC`.

### 3.3 Composition + startup (US-3) — `knowledge_index.py` + `api/main.py`

- Singleton stays process-wide (tenant_id is a per-call arg, not a per-singleton). The vector index no longer binds one connector at build time → it resolves the per-tenant connector inside `ingest(tenant_id)`.
- `api/main.py:_ingest_knowledge` — drop the blocking all-corpus startup ingest; rely on lazy per-tenant ensure-on-first-search. Flag-off path stays a no-op.

### 3.x What is explicitly NOT done

- RBAC per-doc visibility within a tenant (Slice 3b) · structured citation governance report (Slice 3c) · real external sources / SharePoint / HTTP (separate AD) · background/offline ingest at scale (`AD-Knowledge-Connector-Ingest-Scale`) · hybrid keyword∪vector fusion · PDF/Office. Keyword fail-soft path stays shared (not per-tenant) — documented limitation.

### 3.y Validation (US-1..US-5)

Gates: mypy `src` 0 · run_all 11/11 (incl. `check_llm_sdk_leak`) · pytest 2980+new · Vitest 922 (FE untouched) · mockup 51 (`diff` empty) · `npm run lint && npm run build` (NO `--silent`; FE untouched) · black/isort/flake8 clean · LLM-SDK-leak clean. Plus the §3 MANDATORY 2-tenant drive-through.

## 4. File Change List

| # | File | Action |
|---|------|--------|
| 1 | `business_domain/knowledge/vector_index.py` | EDIT (tenant_id search/ingest + namespace + filter + per-tenant connector + lazy ensure) |
| 2 | `business_domain/knowledge/tools.py` | EDIT (dual-arity + forgery guard + thread tenant_id) |
| 3 | `business_domain/knowledge/connector.py` | EDIT (per-tenant root resolver helper — only if cleaner than resolving in #1) |
| 4 | `api/v1/chat/knowledge_index.py` | EDIT (per-tenant-at-search-time; singleton unchanged shape) |
| 5 | `api/main.py` | EDIT (drop blocking startup ingest → lazy per-tenant) |
| 6 | `tests/unit/business_domain/knowledge/test_vector_index.py` | EDIT (per-tenant collection + filter + lazy idempotent) |
| 7 | `tests/unit/business_domain/knowledge/test_knowledge_tools.py` | EDIT (dual-arity + forgery + tenant threading + isolation) |
| 8 | `tests/fixtures/knowledge/<tenantA>/*.md`, `<tenantB>/*.md` | NEW (distinct corpora) |
| — | `qdrant_client.py` · `qdrant_namespace.py` · `executor.py` · `loop.py` · `adapters/*` | **UNTOUCHED** |
| — | any Alembic migration · wire schema · frontend | **UNTOUCHED** (no DB / no event / no UI) |

## 5. Acceptance Criteria

1. `knowledge_search` is dual-arity and receives a real `context.tenant_id` on the chat path; LLM-supplied tenant args are rejected.
2. `KnowledgeVectorIndex.search/ingest` use per-tenant collection (`tenant_<hex>_kb`) + payload filter; ingest is per-tenant idempotent.
3. Per-tenant corpus: `<root>/<tenant>/` when present, shared-root fallback otherwise (57.146 single-tenant behavior byte-preserved when no subfolder + flag off).
4. Keyword fail-soft path still works (tool never goes dark on embedding/Qdrant error).
5. **Drive-through PASS (MANDATORY, real chat-v2 + Azure embedding + Qdrant, 2 tenants)** — tenant A's query cites ONLY A's source docs; B's unique doc is NOT retrieved by A (and vice-versa); screenshot + observed-vs-intended in progress.md. (NOT gate-only.)
6. `AD-Knowledge-Connector-RBAC-Citation-Slice3` isolation half CLOSED (RBAC + citation remain open as 3b/3c); CHANGE-114 + design note 51; calibration recorded; navigators + next-phase-candidates updated.

## 6. Deliverables

- [ ] US-1 per-tenant collection + payload filter in `KnowledgeVectorIndex`
- [ ] US-2 dual-arity `knowledge_search` + forgery guard (mirror memory_search)
- [ ] US-3 per-tenant corpus subfolder + shared fallback + lazy per-tenant ingest
- [ ] US-4 2-tenant isolation drive-through PASS (real UI + backend + LLM)
- [ ] US-5 CHANGE-114 + design note 51 + retro + navigators + AD-half closed

## 7. Workload Calibration

- Scope class **`knowledge-per-tenant-isolation-spike` 0.55** (NEW, 1st data point). Lighter than `knowledge-embedding-vector-spike` 0.60 (57.146) — NO new ABC / NO new infra / NO migration; this WIRES existing pieces (`QdrantNamespaceStrategy`, `payload_filter`, the executor arity dispatch) + mirrors the proven `memory_search` dual-arity. But the 2-tenant drive-through setup (distinct corpora + per-tenant JWT + lazy-ingest first-query latency) is real ceremony, so 0.55 (not lower). If 1st pt lands > 1.20, re-point toward 0.65.
- **Agent-delegated: no** (parent-direct — tenant-isolation correctness + the multi-tenant drive-through want first-party care; mirrors 57.145/146 parent-direct). `agent_factor` 1.0 → 3-segment form.
- Bottom-up est ~11 hr (vector_index ~2 · tools dual-arity+forgery ~1 · connector/ingest timing ~1.5 · startup rework ~0.5 · tests+fixtures ~2 · 2-tenant drive-through ~2 · closeout CHANGE+design-note+retro+navigators ~2) → class-calibrated commit ~6 hr (mult 0.55). Day-4 retro Q2 verifies.

## 8. Dependencies & Risks

| Risk | Mitigation |
|------|------------|
| **D-loop-exec-ctx-tenant** — chat path might call `executor.execute()` without a tenant-populated `ExecutionContext` → `tenant_id=None` → isolation can't work | Day-0 Prong-2 grep `loop.py:2925/3508` + trace the chat 主流量 to `execute(context=...)`; if None on the real path, the sprint pivots to threading tenant_id into the call site first (go/no-go gate) |
| Lazy ingest first-query latency (whole corpus embed on first search per tenant) | bounded per-tenant corpus (a handful of `.md`) ≈ 1-2 s; idempotent after; note in design note; full-corpus scale = separate `AD-Knowledge-Connector-Ingest-Scale` |
| 429 on per-tenant ingest (57.146 lesson) | keep `_EMBED_BATCH=16`; per-tenant corpora are small so well under TPM |
| **Risk Class E** (stale `--reload` / orphan spawn-worker masks the wiring) | Day-3 clean restart: `Win32_Process` PID/PPID/StartTime sweep before drive-through (`.claude/rules/sprint-workflow.md` §Common Risk Classes E) |
| Keyword fail-soft path stays shared (not per-tenant) | documented limitation — keyword is the degraded fallback; per-tenant keyword folder is a trivial follow-on if needed |
| forgery-guard false-positive on legacy callers | reuse `memory_tools._detect_forged_scope_args` tolerant rules verbatim (omit / equal / empty allowed) |

## 9. Out of Scope (this sprint; → separate slices / ADs)

- RBAC per-doc access filter within a tenant → Slice 3b (`AD-Knowledge-Connector-RBAC-Citation-Slice3` RBAC half)
- Structured citation governance report → Slice 3c
- Real external sources (SharePoint / Confluence / HTTP) → `AD-Knowledge-Connector-External-Sources`
- Background/offline idempotent ingest at scale → `AD-Knowledge-Connector-Ingest-Scale`
- Hybrid keyword∪vector fusion → `AD-Knowledge-Connector-Hybrid-Rerank`
- PDF/Office doc types → `AD-Knowledge-Connector-DocTypes`
- Cat 3 memory semantic axis on the new per-tenant pattern (CARRY-026) → separate Cat 3 sprint
