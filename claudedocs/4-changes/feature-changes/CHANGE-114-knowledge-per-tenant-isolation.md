# CHANGE-114: knowledge connector per-tenant KB isolation (Slice 3a)

**Date**: 2026-06-27
**Sprint**: 57.147
**Scope**: Cat 2 (Tools) + `business_domain/knowledge` + adapters/infra wiring — per-tenant vector isolation

## Problem

57.146's `KnowledgeVectorIndex` retrieved from a SINGLE shared Qdrant collection (`knowledge_local_docs`) with no `tenant_id` — every tenant's agent read the same vector store. The moment real per-tenant company documents are ingested (the Slice-3 external-source goal), this leaks tenant A's docs to tenant B's agent — a multi-tenant 鐵律 violation + compliance/security failure.

## Root Cause

The vector index + tool handler carried no tenant context: `search`/`ingest` had no `tenant_id`; the handler was single-arity `(ToolCall) -> str` (no `ExecutionContext`). The per-tenant building blocks (`QdrantNamespaceStrategy` `"kb"` layer, `payload_filter`, `QdrantVectorStore.search(payload_filter=)`) existed (Sprint 49.3 + 57.146) but were unconsumed.

## Solution

Thread `tenant_id` end-to-end, **mirroring the established `memory_search` pattern** (NOT a new mechanism — the executor already auto-dispatches handler arity + the loop already builds `ExecutionContext(tenant_id=ctx.tenant_id)`):

- **`tools.py`** — `knowledge_search` → dual-arity `(ToolCall, ExecutionContext)` + `_reject_forged_scope` guard (refuses an LLM-supplied tenant scope that disagrees with the context); threads `context.tenant_id` into the vector search.
- **`vector_index.py`** — `search(query, top_k, tenant_id)` / `ingest(tenant_id)` → per-tenant collection (`QdrantNamespaceStrategy.collection_name(tid, "kb")` = `tenant_<hex>_kb`) + `payload_filter(tid)` (defense-in-depth) + per-tenant corpus subfolder (`<root>/<tenant_id>/`, shared-root fallback); each payload stamps `tenant_id`; lazy idempotent per-tenant ingest (search ensures the tenant collection first).
- **`knowledge_index.py`** — passes `docs_root` (per-tenant connector resolved at search time); singleton shape unchanged.
- **`api/main.py`** — `_ingest_knowledge` → `_warm_knowledge_index` (drop the blocking all-corpus startup ingest → lazy per-tenant on first search; the full-corpus scale problem = separate `AD-Knowledge-Connector-Ingest-Scale`).

`tenant_id=None` = 57.146 byte-identical (shared collection). No executor / loop / migration / wire / frontend change. `connector.py` UNTOUCHED.

## Verification

- Gate: pytest **2988** (+8 new) · mypy **0/392** · run_all **11/11** (incl. `check_llm_sdk_leak` — EmbeddingClient ABC keeps neutrality) · black/isort/flake8 clean · FE untouched (Vitest 922 / wire 26 / mockup 51).
- **Drive-through PASS** (real chat-v2 + real Azure gpt-5.2 + real `text-embedding-3-large` + real Qdrant, 2 tenants alpha-corp/beta-corp):
  - alpha asks Falcon → `knowledge_search` returns ONLY `falcon.md` → answer grounded (codename "Skyhook") + cites it.
  - alpha asks Condor (beta's secret) → **0 `condor.md`** retrieved → agent answers "I did not find Project Condor" → `verification_passed score=0.98`. (isolation A↛B)
  - beta asks Condor → ONLY `condor.md` (codename "Nightjar"), **0 `falcon.md` leak**. (own doc + reverse isolation B↛A)
  - Qdrant: 2 distinct collections `tenant_428d81b628084f67_kb` + `tenant_54e4e5841a7a48ca_kb`.
  - Full evidence: `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-147/progress.md` Day 3.

## Impact

Backend-only. Closes the **isolation half** of `AD-Knowledge-Connector-RBAC-Citation-Slice3`. RBAC per-doc visibility (3b) + structured citation governance (3c) + real external sources + ingest-at-scale remain open (see `next-phase-candidates.md`). The per-tenant vector-isolation pattern is reusable by the future Cat 3 memory semantic axis. Design note: `docs/03-implementation/agent-harness-planning/51-knowledge-per-tenant-isolation-design.md`.
