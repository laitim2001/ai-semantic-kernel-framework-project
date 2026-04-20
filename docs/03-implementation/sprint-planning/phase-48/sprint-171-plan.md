# Sprint 171 Plan — Consolidation 5-phase Completion

**Phase**: 48 — Memory System Improvements
**Sprint**: 171
**Branch**: `research/memory-system-enterprise`
**Worktree**: `ai-semantic-kernel-memory-research`
**Date**: 2026-04-20
**Depends on**: Sprint 170 (requires live `access_count` + `MemoryBackgroundTaskManager`)

---

## Background

V9 audit found `consolidation.py` 5-phase flow has 3 phases as PoC-only:
- **Phase 2 Decay** (`consolidation.py:~225`) — only logs, no write to storage
- **Phase 5 Summarize** — no implementation at all
- **Phase 3 Promote** — logic exists but `access_count` was never updated (fixed in Sprint 170)

Sprint 171 completes the background consolidation loop so CC-style `autoDream` equivalent is fully operational.

Additionally addresses Sprint 170 Implementation Notes item #3 (counter key orphan cleanup).

---

## User Stories

### US-1: Importance Decay Actually Happens
- **As** a platform operator
- **I want** importance scores of memories to decay over time based on access recency
- **So that** stale low-value memories naturally drop out of relevance ranking without manual intervention

### US-2: Low-Importance Clusters Get Summarized
- **As** a platform operator
- **I want** clusters of low-importance memories to be LLM-summarized into single higher-level entries
- **So that** storage cost stays bounded while retaining semantic content

### US-3: No Orphan Counter Keys
- **As** a platform operator
- **I want** counter keys in Redis to be cleaned up when their source memory is promoted/decayed/deleted
- **So that** Redis doesn't accumulate garbage and key enumeration stays meaningful

---

## Technical Specifications

### Backend

1. **Phase 2 Decay — real implementation** (`consolidation.py`)
   - Formula: `new_importance = old_importance * exp(-λ * days_since_access)` where `λ` configurable (default 0.05 → ~half-life 14 days)
   - Write back via `UnifiedMemoryManager.update_importance(memory_id, new_importance)` (new method)
   - For Redis tiers: update JSON entry with new importance
   - For LONG_TERM: call `mem0.update()` via Sprint 170's executor + lock
   - Skip memories with `access_count >= threshold` (recent access cancels decay)
   - Use `MemoryBackgroundTaskManager.fire_and_forget` per-memory update

2. **Phase 5 Summarize — new implementation** (`consolidation.py`)
   - Cluster detection: group memories by tag + time window + semantic similarity (simple k-means on embeddings, k=5 default)
   - Filter: only clusters with all members `importance < 0.3` AND size ≥ 5
   - For each qualifying cluster:
     - Call LLM (gpt-5-nano) with prompt: "Summarize the following {N} memory entries into 1 concise statement (max 200 chars)"
     - Create new memory entry with `MemoryType.SEMANTIC`, `importance=0.5`, tags merged
     - Link original entries via `metadata.summarized_into = new_memory_id`
     - Mark originals with `metadata.superseded_by = new_memory_id` (don't delete yet — keep for 30 days as audit trail)

3. **Counter Key Orphan Cleanup** (from Sprint 170 Impl Notes #3)
   - New helper `_cleanup_counter(memory_id, source_layer)` in `unified_memory.py`
   - Deletes `memory:counter:{source_layer}:{user_id}:{memory_id}` and `memory:accessed_at:...`
   - Called by:
     - `consolidation.py` Phase 3 Promote (after successful LONG_TERM write)
     - `consolidation.py` Phase 4 Prune (when deleting memory)
     - `consolidation.py` Phase 5 Summarize (for superseded originals — but keep for 30 days grace)

4. **Decay Config Surface** (`backend/core/settings.py`)
   - `MEMORY_DECAY_LAMBDA: float = 0.05`
   - `MEMORY_DECAY_MIN_IMPORTANCE: float = 0.1` (floor)
   - `MEMORY_DECAY_SKIP_ACCESS_THRESHOLD: int = 3` (recent access cancels decay)
   - `MEMORY_SUMMARIZE_CLUSTER_MIN_SIZE: int = 5`
   - `MEMORY_SUMMARIZE_IMPORTANCE_CUTOFF: float = 0.3`

5. **Metrics & Observability**
   - `consolidation_phase2_decayed_total{tier}` counter
   - `consolidation_phase5_clusters_summarized_total` counter
   - Per-run summary log: `{phase1_merged, phase2_decayed, phase3_promoted, phase4_pruned, phase5_summarized, duration_ms}`

### Testing

6. **Unit Tests**
   - `test_decay_phase2.py` — formula correctness, floor enforcement, skip on recent access
   - `test_summarize_phase5.py` — cluster detection, LLM call mock, supersede metadata
   - `test_counter_cleanup.py` — orphan cleanup on promote/prune/summarize

7. **Integration Test**
   - `test_consolidation_full_5phase.py` — seed mixed-importance memories → force_run consolidation → verify all 5 phases executed with expected state changes

---

## File Changes

| File | Action | Purpose |
|------|--------|---------|
| `backend/src/integrations/memory/consolidation.py` | Modify | Phase 2 decay writeback, Phase 5 summarize, counter cleanup hooks |
| `backend/src/integrations/memory/unified_memory.py` | Modify | `update_importance()` method, `_cleanup_counter()` helper |
| `backend/src/integrations/memory/types.py` | Modify (minor) | Add `superseded_by`, `summarized_into` to metadata schema |
| `backend/src/core/settings.py` | Modify | 5 new decay/summarize config vars |
| `backend/tests/unit/integrations/memory/test_decay_phase2.py` | Create | Phase 2 unit tests |
| `backend/tests/unit/integrations/memory/test_summarize_phase5.py` | Create | Phase 5 unit tests |
| `backend/tests/unit/integrations/memory/test_counter_cleanup.py` | Create | Orphan cleanup tests |
| `backend/tests/integration/memory/test_consolidation_full_5phase.py` | Create | E2E 5-phase test |

---

## Acceptance Criteria

- [ ] **AC-1**: Phase 2 Decay writes back `importance` to Redis/mem0 (verifiable via storage inspection after run)
- [ ] **AC-2**: Decay skips memories with `access_count >= MEMORY_DECAY_SKIP_ACCESS_THRESHOLD`
- [ ] **AC-3**: Decay respects `MEMORY_DECAY_MIN_IMPORTANCE` floor (importance never drops below)
- [ ] **AC-4**: Phase 5 Summarize clusters low-importance memories (≥5 members, all `importance < 0.3`) into single summary entry
- [ ] **AC-5**: Superseded memories marked with `metadata.superseded_by` (not deleted immediately — 30-day grace)
- [ ] **AC-6**: Counter keys cleaned up on promote/prune/summarize — `redis-cli GET memory:counter:session:{user}:{id}` returns nil after promote
- [ ] **AC-7**: Consolidation per-run summary log includes all 5 phase counts
- [ ] **AC-8**: Metrics `consolidation_phase2_decayed_total` and `consolidation_phase5_clusters_summarized_total` increment
- [ ] **AC-9**: All unit tests pass; integration test asserts all 5 phases executed with expected state changes
- [ ] **AC-10**: No regression — Phase 1 (merge) and Phase 4 (prune) still work as before (regression tests)

---

## Out of Scope

- Immediate deletion of superseded memories (30-day grace, Phase 6 future sprint)
- Advanced clustering algorithms (HDBSCAN, hierarchical) — k-means sufficient for MVP
- LLM-as-Judge for summary quality — Sprint 176 concern
- Fine-tuned decay per MemoryType — v1 uses global λ
