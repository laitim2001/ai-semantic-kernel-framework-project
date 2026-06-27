# Knowledge Connector Slice 3a — Per-Tenant KB Isolation (Design Note)

**Purpose**: Extract the verified design of the per-tenant vector-isolation path from the Sprint 57.147 implementation — the pattern the future Cat 3 memory semantic axis reuses.
**Category / Scope**: Cat 2 (Tools) + Adapters/Infra (QdrantNamespaceStrategy) / Phase 57 / Sprint 57.147
**Created**: 2026-06-27
**Status**: Active (verified ratio ~95%)
**Author**: self (solo-dev)

> **Modification History**
> - 2026-06-27: Initial extract from Sprint 57.147 (AD-Knowledge-Connector-RBAC-Citation-Slice3 isolation half)

---

## 1. Spike Summary (US → what shipped)

Third slice of the knowledge-connector arc — the **isolation half** of `AD-Knowledge-Connector-RBAC-Citation-Slice3`. Threads `tenant_id` end-to-end so each tenant's KB retrieval is physically isolated.

- **US-1** per-tenant Qdrant collection + `tenant_id` payload filter (defense-in-depth).
- **US-2** `knowledge_search` dual-arity handler reads server-authoritative `tenant_id` from `ExecutionContext` + forgery guard.
- **US-3** per-tenant corpus subfolder `<root>/<tenant_id>/` (shared-root fallback) + lazy idempotent per-tenant ingest.
- **US-4** 2-tenant drive-through PASS (real chat-v2 + Azure embedding + Qdrant). **US-5** closeout.

## 2. Decision Matrix

### How tenant_id reaches a process-wide tool handler

| Option | Mechanism | Decision |
|--------|-----------|----------|
| **Dual-arity handler `(ToolCall, ExecutionContext)`** | executor auto-detects arity (`executor.py:213`) + threads `ExecutionContext(tenant_id=ctx.tenant_id)` built by the loop (`loop.py:2925`) | **CHOSEN** — mirrors `memory_search` (Sprint 52.5); ZERO executor/loop change |
| LLM supplies tenant_id in tool args | — | rejected — forgeable (W3-2 mirror vuln); guarded against |
| Per-request vector index instance | rebuild singleton per tenant | rejected — the singleton stays process-wide; tenant_id is a per-CALL arg |

### Corpus source (for a falsifiable isolation drive-through)

| Option | Drive-through strength | Decision |
|--------|------------------------|----------|
| **Per-tenant subfolder `<root>/<tenant_id>/` + shared fallback** | strong — A queries B's unique content → 0 hits (distinct corpora) | **CHOSEN** (user pick) |
| Shared corpus + structural-only isolation | weak — identical content can't prove content isolation | rejected — would retreat to gate-only |

### Ingest timing

Lazy per-tenant ensure-on-first-search (idempotent skip when `count == expected`) — NOT a blocking all-tenant startup ingest (that's the `AD-Knowledge-Connector-Ingest-Scale` concern; the full default corpus is 418 files / 3818 sections per the 57.146 finding).

## 3. Verified Invariants (file:line + verification)

1. **Per-tenant collection name** — `_collection_for(tenant_id)` → `QdrantNamespaceStrategy.collection_name(tid, "kb")` (`tenant_<16hex>_kb`); None → shared `knowledge_local_docs`. `business_domain/knowledge/vector_index.py:_collection_for`. Verify: `test_vector_index.py::test_ingest_is_per_tenant_collection`.
2. **Defense-in-depth payload filter** — `search` passes `QdrantNamespaceStrategy.payload_filter(tid)` (`{"must":[{"key":"tenant_id","match":{"value":<uuid>}}]}`, `qdrant_namespace.py:103`) to `QdrantVectorStore.search(payload_filter=)` (`qdrant_client.py:114-127`); each ingest payload stamps `tenant_id`. Verify: `test_vector_index.py::test_payload_filter_rejects_cross_tenant_row`.
3. **Per-tenant corpus + fallback** — `_connector_for(tid)` → `<root>/<tenant_id>/` when it `is_dir()`, else `<root>`. `vector_index.py:_connector_for`. Verify: drive-through (alpha reads `<alpha>/falcon.md`, beta reads `<beta>/condor.md`).
4. **Lazy idempotent per-tenant ingest** — `search()` `await self.ingest(tenant_id)` first; `ingest` skips when `count == expected`. `vector_index.py:ingest/search`. Verify: `test_vector_index.py::test_lazy_ingest_idempotent_per_tenant` (asserts 2nd search adds only a 1-vector query batch, no corpus re-embed).
5. **Dual-arity handler + tenant threading** — `make_knowledge_search_handler` → `async def handler(call, context: ExecutionContext)`; `vector_index.search(..., tenant_id=context.tenant_id)`. `business_domain/knowledge/tools.py:155`. Verify: `test_knowledge_tools.py::test_handler_threads_context_tenant_to_vector_index`.
6. **Forgery guard** — `_reject_forged_scope(args, context)` refuses an arg `tenant_id`/`user_id`/`session_id` disagreeing with the context (tolerant: omit/equal/empty OK); mirrors `memory_tools._detect_forged_scope_args`. `tools.py:64`. Verify: `test_knowledge_tools.py::test_handler_rejects_forged_tenant_arg` + `::test_handler_allows_matching_tenant_arg`.
7. **Executor auto-dispatch (no executor change)** — `_handler_takes_context(call.name, handler)` → `handler(call, ctx)`. `agent_harness/tools/executor.py:213` + arity cache `:308-320`. Verify: drive-through (knowledge_search ran dual-arity on the chat path).
8. **Loop threads real tenant_id** — `exec_ctx = ExecutionContext(tenant_id=ctx.tenant_id, …)` + `execute(tc, context=exec_ctx)`. `agent_harness/orchestrator_loop/loop.py:2925-2959` (main path) + `:3508-3515` (resume). Verify: drive-through (per-tenant retrieval observed).
9. **tenant_id=None = 57.146 byte-identical** — None → shared collection + shared root + no payload filter. Verify: `test_vector_index.py::test_tenant_id_none_uses_shared_collection`.
10. **Lazy startup (no blocking ingest)** — `_warm_knowledge_index` memoizes the singleton, no `ingest()`. `api/main.py:_warm_knowledge_index`. Verify: drive-through startup log `ready (lazy per-tenant ingest)` (~1s).
11. **Drive-through (real, NOT gate-only)** — 2 tenants, distinct corpora: alpha asks Falcon → only `falcon.md` cited (Skyhook); alpha asks Condor → **0 `condor.md`**, "I did not find Project Condor" (judge 0.98); beta asks Condor → only `condor.md` (Nightjar), **0 `falcon.md` leak**; Qdrant 2 distinct collections (`tenant_428…_kb` / `tenant_54e…_kb`). Reproduce: progress.md Day 3.

## 4. Cross-Category Contracts

- **No new 17.md contract / wire event / DB migration.** Reuses: `QdrantNamespaceStrategy` (Infra, Sprint 49.3 — first real consumer of its `"kb"` layer + `payload_filter`), the dual-arity `ToolHandler` union (`agent_harness/tools/__init__.py:106`), the executor's arity auto-dispatch (Sprint 52.5 P0 #18), and the loop's `ExecutionContext(tenant_id=…)` threading. The `EmbeddingClient` ABC + `QdrantVectorStore` (57.146) are reused unchanged.
- **Reuse note**: the per-tenant collection + payload-filter pattern is the exact shape the Cat 3 memory semantic axis (CARRY-026) will adopt — `QdrantNamespaceStrategy` already enumerates `user_memory`/`tenant_memory`/`session_memory` layers alongside `kb`.

## 5. Open Invariants (deferred — NOT verified this sprint)

| Item | Status | Where |
|------|--------|-------|
| RBAC per-doc access filter within a tenant | deferred | Slice 3b (`AD-Knowledge-Connector-RBAC-Citation-Slice3` RBAC half) |
| Structured citation governance report | deferred | Slice 3c |
| Keyword fail-soft path is NOT per-tenant (stays shared root) | known limitation | keyword is the degraded fallback; per-tenant keyword folder is a trivial follow-on |
| Real external sources (SharePoint/Confluence/HTTP) | deferred | `AD-Knowledge-Connector-External-Sources` |
| Background/offline ingest at scale (full 3818-section corpus) | deferred | `AD-Knowledge-Connector-Ingest-Scale` |
| Hybrid keyword∪vector fusion | deferred | `AD-Knowledge-Connector-Hybrid-Rerank` |
| Cat 3 memory semantic axis on this pattern | unblocked, NOT wired | separate Cat 3 sprint (CARRY-026) |

**Boundary statement**: verified = per-tenant collection + payload filter + per-tenant corpus + lazy ingest + forgery-guarded dual-arity handler, end-to-end on the real chat path, bidirectional isolation proven at BOTH the agent-answer and physical Qdrant-collection layers. NOT verified = RBAC per-doc, citation governance, external sources, large-corpus ingest, hybrid fusion.

## 6. Rollback

- Per-call: a `tenant_id=None` call path is byte-identical to 57.146 (shared collection). Disable the whole vector path via `KNOWLEDGE_VECTOR_ENABLED=0` → `get_knowledge_vector_index()` returns None → keyword path (57.145).
- Full revert: revert the 4 src EDITs (`vector_index.py`/`tools.py`/`knowledge_index.py`/`api/main.py`) + the 2 test EDITs. < 1 hr; no migration, no sentinel, no DB state (per-tenant Qdrant collections are derived from the `.md` source-of-truth — drop `tenant_*_kb` to reset). 57.146 single-tenant path is untouched underneath.

## 7. References

- `business_domain/knowledge/{vector_index,tools}.py` · `api/v1/chat/knowledge_index.py` · `api/main.py`
- `infrastructure/vector/qdrant_namespace.py` (per-tenant naming + payload filter — first real KB consumer) · `qdrant_client.py` (`search(payload_filter=)`)
- `agent_harness/tools/{executor.py,memory_tools.py}` (dual-arity protocol + forgery-guard mirror) · `orchestrator_loop/loop.py:2925` (ExecutionContext threading)
- `50-knowledge-embedding-vector-design.md` (Slice 2) · `49-knowledge-connector-first-real-source-design.md` (Slice 1)
- `.claude/rules/multi-tenant-data.md` (tenant isolation 鐵律) · CHANGE-114 · Sprint 57.147 plan/checklist/progress/retrospective

## 8. Modification History

- 2026-06-27: Initial creation (Sprint 57.147) — per-tenant KB isolation design extract.
