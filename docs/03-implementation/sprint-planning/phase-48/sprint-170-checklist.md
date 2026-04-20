# Sprint 170 Checklist — Access Tracking Reconnection

**Sprint**: 170
**Branch**: `research/memory-system-enterprise`
**Plan**: [sprint-170-plan.md](sprint-170-plan.md) (v2)

---

## Backend — Background Task Utility

- [x] `integrations/memory/background_tasks.py` — new file
- [x] `MemoryBackgroundTaskManager` class with `self._tasks: set[asyncio.Task]` strong refs
- [x] `asyncio.Semaphore(100)` concurrency cap
- [x] `fire_and_forget()` method with context dict
- [x] Dead-letter logger (`memory.background.dlq`) with JSON context on exception
- [x] `add_done_callback(self._tasks.discard)` for cleanup
- [x] `drain(timeout)` method for graceful shutdown / test teardown

## Backend — Memory Core

- [x] `unified_memory.py` — counter key pattern helpers (`_counter_key(layer, user_id, memory_id)`)
- [x] `unified_memory.py` — `accessed_at` key pattern helpers
- [x] `unified_memory.py` — `_track_access_single()` uses `INCR` + `SET` with TTL matching source memory
- [x] `unified_memory.py` — `_track_access_batch()` for multi-hit search results
- [x] `unified_memory.py` — `search()` hook: schedule background tracking after result formed
- [x] `unified_memory.py` — `get()` hook: schedule background tracking on hit (skip on miss)
- [x] `unified_memory.py` — retrieval merges counter into `MemoryEntry.access_count` via `asyncio.gather`
- [x] Structured log `event=memory_access_tracked` with all required fields

## Backend — Mem0 Integration

- [x] `mem0_client.py` — `self._update_executor = ThreadPoolExecutor(max_workers=4)`
- [x] `mem0_client.py` — `self._update_lock = asyncio.Lock()`
- [x] `mem0_client.py` — `update_access_metadata(memory_id, count, accessed_at)` method
- [x] Uses `loop.run_in_executor(self._update_executor, self._memory.update, ...)`
- [x] Executor shutdown on client disposal

## Backend — Consolidation Guard

- [x] `consolidation.py` Phase 3 Promote — explicit `if mem.layer == MemoryLayer.PINNED: continue`
- [x] `ConsolidationService.run_once(force_run=False)` kwarg — bypasses 20-count throttle when True
- [ ] Unit test asserts PINNED skipped

## Backend — Types (minor)

- [x] `types.py` — `access_count: int = 0`
- [x] `types.py` — `accessed_at: Optional[datetime] = None`

## Tests — Unit

- [x] `tests/unit/integrations/memory/test_access_tracking.py` — PINNED tier increment
- [x] `tests/unit/integrations/memory/test_access_tracking.py` — WORKING tier increment + TTL alignment
- [x] `tests/unit/integrations/memory/test_access_tracking.py` — SESSION tier increment + TTL alignment
- [x] `tests/unit/integrations/memory/test_access_tracking.py` — LONG_TERM tier calls mem0 update via executor
- [x] `tests/unit/integrations/memory/test_background_tasks.py` — exception → DLQ log
- [x] `tests/unit/integrations/memory/test_background_tasks.py` — semaphore caps concurrency
- [x] `tests/unit/integrations/memory/test_background_tasks.py` — strong refs retained
- [x] `tests/unit/integrations/memory/test_background_tasks.py` — `drain()` completes pending
- [x] `tests/unit/integrations/memory/test_counter_edge_cases.py` — counter key absent → INCR creates with value 1
- [x] `tests/unit/integrations/memory/test_counter_edge_cases.py` — non-existent memory_id → no increment
- [x] `tests/unit/integrations/memory/test_counter_edge_cases.py` — boundary: count=4 + 1 hit → consolidation promotes
- [x] `tests/unit/integrations/memory/test_counter_edge_cases.py` — counter TTL alignment per tier

## Tests — Concurrency

- [x] `tests/unit/integrations/memory/test_access_tracking_concurrent.py` — 10 concurrent search → counter == 10 (INCR atomicity)

## Tests — Failure Modes

- [x] `tests/unit/integrations/memory/test_access_tracking_failures.py` — Redis disconnect during search → search still returns + DLQ entry recorded
- [x] `tests/unit/integrations/memory/test_access_tracking_failures.py` — mem0 `update` raises → DLQ entry + search response unaffected

## Tests — Integration

- [x] `tests/integration/memory/test_promotion_triggered.py` — testcontainers setup for Redis + Qdrant
- [x] `tests/integration/memory/test_promotion_triggered.py` — seed → 5 search → drain → force_run consolidation → Qdrant assert + Redis TTL assert

## Benchmark & Baseline

- [x] `scripts/benchmark_memory_search.py` — 1000 searches, P50/P95/P99 output
- [ ] Pre-change baseline captured: `claudedocs/5-status/sprint-170-baseline-pre.json`
- [ ] Post-change benchmark captured: `claudedocs/5-status/sprint-170-baseline-post.json`
- [ ] P95 regression ≤ 5% (post ≤ pre × 1.05)

## Verification

- [x] All Python files pass `black`, `isort`, `flake8`, `mypy`
- [ ] Backend starts without import errors
- [x] Run `pytest backend/tests/unit/integrations/memory/ -v` → all pass (20/20 in 1.28s)
- [ ] Run `pytest backend/tests/integration/memory/test_promotion_triggered.py -v` → pass
- [x] Run `pytest backend/tests/unit/integrations/memory/test_access_tracking_concurrent.py -v` → pass (validates INCR atomicity)
- [ ] Manual: `redis-cli GET memory:counter:working:{user}:{mem_id}` after single search → shows 1
- [ ] Manual: trigger consolidation via `force_run=True` → Qdrant `scroll` shows promoted memory
- [ ] Manual: inspect `memory.background.dlq` log during induced Redis failure → entry present with correct context
- [ ] Benchmark P95 regression ≤ 5% documented in `sprint-170-baseline-post.json`
