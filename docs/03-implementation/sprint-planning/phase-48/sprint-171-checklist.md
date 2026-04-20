# Sprint 171 Checklist — Consolidation 5-phase Completion

**Sprint**: 171
**Branch**: `research/memory-system-enterprise`
**Plan**: [sprint-171-plan.md](sprint-171-plan.md)

---

## Backend — Phase 2 Decay

- [ ] Formula `importance_new = importance_old * exp(-λ * days_since_access)` in `consolidation.py`
- [ ] `MEMORY_DECAY_LAMBDA` / `MEMORY_DECAY_MIN_IMPORTANCE` / `MEMORY_DECAY_SKIP_ACCESS_THRESHOLD` in `settings.py`
- [ ] `UnifiedMemoryManager.update_importance(memory_id, new_importance)` method
- [ ] Writeback for Redis tiers (JSON entry update)
- [ ] Writeback for LONG_TERM via mem0 executor + lock
- [ ] Skip logic when `access_count >= threshold`
- [ ] Floor enforcement (importance ≥ `MEMORY_DECAY_MIN_IMPORTANCE`)
- [ ] Fire-and-forget per-memory via `MemoryBackgroundTaskManager`

## Backend — Phase 5 Summarize

- [ ] K-means clustering on embeddings (k=5 default)
- [ ] Cluster filter: `size >= 5` AND all `importance < 0.3`
- [ ] LLM call via gpt-5-nano with summary prompt
- [ ] New summary memory entry creation (`MemoryType.SEMANTIC`, importance=0.5)
- [ ] `metadata.summarized_into` + `metadata.superseded_by` fields in `types.py`
- [ ] Originals marked superseded (NOT deleted — 30-day grace)
- [ ] `MEMORY_SUMMARIZE_CLUSTER_MIN_SIZE` + `MEMORY_SUMMARIZE_IMPORTANCE_CUTOFF` in settings

## Backend — Counter Cleanup

- [ ] `_cleanup_counter(memory_id, source_layer)` helper in `unified_memory.py`
- [ ] Deletes `memory:counter:{layer}:{user_id}:{id}` and `memory:accessed_at:...`
- [ ] Called by Phase 3 Promote path
- [ ] Called by Phase 4 Prune path
- [ ] NOT called on Phase 5 Summarize immediately (30-day grace)

## Backend — Observability

- [ ] `consolidation_phase2_decayed_total{tier}` metric
- [ ] `consolidation_phase5_clusters_summarized_total` metric
- [ ] Per-run summary log with all 5 phase counts + `duration_ms`

## Tests — Unit

- [ ] `test_decay_phase2.py` — formula correctness (known inputs → expected outputs)
- [ ] `test_decay_phase2.py` — floor respected
- [ ] `test_decay_phase2.py` — skip on `access_count >= 3`
- [ ] `test_decay_phase2.py` — writeback happens for each tier
- [ ] `test_summarize_phase5.py` — cluster detection with k-means
- [ ] `test_summarize_phase5.py` — filter: size=4 → no summary; size=5+low_importance → summary
- [ ] `test_summarize_phase5.py` — LLM call mocked, summary created, originals marked superseded
- [ ] `test_counter_cleanup.py` — promote removes counter + accessed_at keys
- [ ] `test_counter_cleanup.py` — prune removes counter keys
- [ ] `test_counter_cleanup.py` — summarize does NOT remove counter (grace period)

## Tests — Integration

- [ ] `test_consolidation_full_5phase.py` — seed 50 mixed memories → `force_run=True` → assert all 5 phases executed
- [ ] Phase 1: duplicates merged (existing behavior regression test)
- [ ] Phase 2: low-importance decayed, high-importance untouched
- [ ] Phase 3: `access_count >= 5` memories promoted to LONG_TERM (Qdrant scroll check)
- [ ] Phase 4: very low importance pruned
- [ ] Phase 5: low-importance clusters summarized

## Verification

- [ ] All Python files pass `black`, `isort`, `flake8`, `mypy`
- [ ] Backend starts without import errors
- [ ] Run `pytest backend/tests/unit/integrations/memory/test_decay_phase2.py test_summarize_phase5.py test_counter_cleanup.py -v`
- [ ] Run `pytest backend/tests/integration/memory/test_consolidation_full_5phase.py -v`
- [ ] Manual: trigger consolidation via `force_run=True`, inspect per-run summary log to see all 5 phase counts non-zero on suitable fixture
- [ ] Manual: after promote, `redis-cli GET memory:counter:session:{user}:{id}` returns `(nil)`
