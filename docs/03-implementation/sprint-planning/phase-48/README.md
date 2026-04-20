# Phase 48: Memory System Improvements

## Overview

Phase 48 improves the IPA Platform memory system along two axes discovered in the V9 architecture audit and `integrations/memory/` code review:

**Phase 47 delivered**: Orchestrator chat improvements (intent classifier, subagent count control, execution log persistence).

**Phase 48 delivers**:
- **Wave 1 — Fix existing defects**: access_count tracking reconnection, consolidation 5-phase completion, Session L2 PostgreSQL landing, Mem0 async unblocking.
- **Wave 2 — Enterprise-grade capabilities**: Multi-level tenant scope (org/workspace/user/agent), bitemporal support (event time vs ingestion time), Active Retrieval (MIRIX-style topic-first query transformation + multi-strategy rerank).

**Design lineage**: The existing memory system is a hybrid of Claude Code skeleton (explicit "CC Equivalent" comments in `context_budget.py` / `consolidation.py` / `extraction.py`) plus Mem0/Qdrant vector engine. Phase 48 extends along this lineage rather than replacing it.

## Sprint Overview (v2 — post 4-batch team review 2026-04-20)

| Sprint | Title | Wave | Story Points | Plan Version | Depends On |
|--------|-------|------|-------------|--------------|-----------|
| 170 | Access Tracking Reconnection | 1 — Fix | 5 | **v2 GREEN** | — |
| 171 | Consolidation 5-phase Completion | 1 — Fix | 8 | **v2** (Batch 1) | 170 |
| 172 | Session L2 PostgreSQL + Mem0 Async | 1 — Fix | 8 | **v2** (Batch 1) | 170, 171 |
| 173 | Tenant Scope Foundation + ADR-048 | 2 — Enterprise | 10 | **v2** (Batch 2, was 8) | 172 |
| 174 | Bitemporal + GDPR Tombstone coordination | 2 — Enterprise | 6 | **v2** (Batch 2, was 5) | 173, coord with 177a |
| 175 | Active Retrieval — Topic Generation | 2 — Enterprise | 8 | **v2 (partial)** (Batch 3 content lost) | 173 |
| 176 | Active Retrieval — Multi-Strategy + Cohere Rerank | 2 — Enterprise | 8 | **v2 (partial)** (Batch 3 content lost) | 175 |
| **177a** | **GDPR + Cross-Layer Saga + Audit Chain (compliance)** | 2 — Enterprise | **8** (was 5) | **v2** (split from original 177) | 170-176 |
| ~~177b~~ | **DEFERRED to Phase 49** — DevUI + V9 benchmark + docs | — | — | see `sprint-177b-deferred.md` | — |

**Total Phase 48**: ~61 Story Points (increased from 55 after review findings integration)

### Merge Order (enforced after Batch 1-4 review)

- **S170 → S171 → S172** (all edit `unified_memory.py`; linear merge to avoid conflicts)
- **S172 → S173** (scope cols need L2 PG schema from 172)
- **S173 → S174** (scope context required for bitemporal)
- **S173 → S175 → S176** (active retrieval needs scope)
- **S174 ↔ S177a** (tombstone model shared — merge order flexible, both v2 reference same `forgotten_users` schema)
- **S170-176 → S177a** (compliance layer builds on all prior)
- CI check: `alembic heads == 1` prevents parallel migration divergence

### Batch Review Status

Full review findings in `phase-48-review-consolidated.md`:
- **Batch 1** (S171+S172): 26 items (2C/1H/17M/6L) → v2 integrated
- **Batch 2** (S173+S174): 31 items (4C/8H/12M/7L) → v2 integrated, ADR-048 rewrite pending
- **Batch 3** (S175+S176): YELLOW verdict, findings body lost in delivery → v2 partial with known-risk integrations; recommend focused re-review at kickoff
- **Batch 4** (S177 → split 177a+177b): 16 items (3C/5H/6M/2L) → 177a fully v2 with saga/HMAC/tombstone; 177b deferred

### Exit Gate

Phase 48 cannot close until Sprint 177a passes all 12 compliance ACs with signed-off:
- backend-lead
- sec-lead
- compliance officer

## Architecture

### Design References

- **V9 memory architecture baseline**: `docs/07-analysis/V9/06-cross-cutting/memory-architecture.md`
- **Enterprise research series (2026-04-17)**: `docs/09-git-worktree-working-folder/knowledge-base-enterprise/02-agent-memory-deep-dive.md` and `08-ipa-platform-recommendations.md`
- **SOTA memory systems surveyed**: MemGPT/Letta, Mem0, MIRIX (6-component schema + Active Retrieval), Zep/Graphiti (bitemporal), A-MEM (memory evolution), Claude Code (`buildEffectiveSystemPrompt` + `autoDream`)

### Key Components Affected

```
backend/src/integrations/memory/
├── unified_memory.py            # Sprint 170 (access_count), 172 (L2 PostgreSQL), 173 (tenant scope), 174 (bitemporal), 175 (topic gen hook)
├── mem0_client.py               # Sprint 170 (metadata update), 172 (async wrap)
├── consolidation.py             # Sprint 171 (Phase 2 Decay, Phase 5 Summarize)
├── types.py                     # Sprint 173 (scope fields), 174 (event_time field)
├── context_budget.py            # Sprint 175-176 (Active Retrieval integration)
└── extraction.py                # Sprint 173 (scope propagation)

backend/src/integrations/orchestration/pipeline/steps/
├── step1_memory.py              # Sprint 175-176 (topic gen + multi-strategy)
└── step8_postprocess.py         # Sprint 173 (scope on write)

backend/src/infrastructure/storage/
└── session_memory.py            # Sprint 172 (NEW — L2 PostgreSQL)

backend/src/api/middleware/
└── tenant_scope.py              # Sprint 173 (NEW — JWT scope injection)
```

### Integration Points

- **Pipeline Step 1 (Memory Read)**: gains topic generation + tenant-scoped retrieval
- **Pipeline Step 8 (PostProcess)**: gains scope propagation on write
- **Agent Expert Registry (Phase 46)**: agent-level memory scope ties to expert definitions
- **Orchestration Execution Log (Phase 47 Sprint 169)**: audit trail complements new bitemporal field

### Fallback Chain (Wave 2 additions)

1. Active Retrieval topic generation — if LLM fails/timeouts, fall back to raw user query embedding
2. Cohere Rerank — if API unavailable, fall back to existing rerank logic
3. Bitemporal query — if `as_of_time` omitted, default to latest (current behavior)

## Dependencies & Risks

### Explicitly Out of Scope (deferred to later phase)

- **InMemoryCheckpointStorage / InMemoryApprovalStorage migration** (V9 P0 HIGH risks): factories exist (`create_agent_framework_checkpoint_storage()`, `create_approval_storage()`) but swap requires cross-module change beyond memory scope. Recommended for a dedicated infrastructure phase.
- **Full A-MEM memory evolution** (retroactive link updates): advanced research pattern, not immediately required for enterprise readiness.
- **Procedural memory / skill compilation**: long-term capability, requires schema design convergence first.
- **Graphiti / Neo4j integration**: evaluated in research series but too large for Phase 48 (suggested as Phase 49+ if tenant + bitemporal prove insufficient).

### Risks

| Risk | Mitigation |
|------|-----------|
| Active Retrieval adds LLM cost per query | Use `gpt-5-nano` for topic gen; measure cost/latency in Sprint 175 before rollout |
| Tenant scope breaking change for existing memory | Sprint 173 uses non-destructive rollout (default `org_id="default"` for legacy entries) |
| Session L2 migration Redis → PostgreSQL data loss | Sprint 172 includes dual-write + backfill window |
| Consolidation writes could slow background job | Sprint 171 keeps async fire-and-forget pattern from Phase 45-47 |
| **Active Retrieval topic gen adds LLM call to Pipeline Step 1 — breaks SSE first-token latency budget** | Sprint 175 must establish first-token latency baseline pre-change and guard with feature flag; fall back to raw query if `p95_topic_gen > threshold` |
| **Bitemporal `event_time` column requires Qdrant payload schema backfill** | Sprint 174 must include backfill migration script (default `event_time = created_at` for legacy entries) before enabling new writes |
| **Fire-and-forget async writes can silently fail → audit trail gaps** | All background tasks must attach `done_callback` that writes failures to dead-letter log; Sprint 170 establishes this pattern platform-wide |
| **JWT claim schema for tenant scope undefined** | Sprint 173 must begin with ADR defining claim structure, key rotation, membership validation; without this, scope enforcement is single-point-of-failure |

### Dependency Refinement (from 2026-04-20 review)

Original plan had Sprint 173 depending on 170+171+172. Review found tenant scope only needs Sprint 172's L2 PostgreSQL schema (as scope column carrier). Revised dependencies:

- Sprint 173 depends on **172 only** (not 170 or 171) — allows Wave 1 fixes to run in parallel with Wave 2 start after 172 lands
- Sprint 175 Active Retrieval depends on 173 (scope context required for safe LLM topic generation)
- Sprint 177 integration test depends on all prior sprints

## Worktree

- **Branch**: `research/memory-system-enterprise`
- **Path**: `C:\Users\Chris\Downloads\ai-semantic-kernel-memory-research`
- **Base**: main@69b5fa2 (Phase 47 merge)
- **Created**: 2026-04-19
- **Note**: Worktree was initially created as research branch. Continues to be used for Phase 48 implementation to preserve existing discussion context and avoid worktree proliferation.
