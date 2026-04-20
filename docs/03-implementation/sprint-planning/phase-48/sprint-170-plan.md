# Sprint 170 Plan — Access Tracking Reconnection

**Phase**: 48 — Memory System Improvements
**Sprint**: 170
**Branch**: `research/memory-system-enterprise`
**Worktree**: `ai-semantic-kernel-memory-research`
**Date**: 2026-04-20
**Plan Version**: v2 (integrated agent team review findings)

---

## Revision Notes (v1 → v2)

Agent team review (Backend Architect + Python Expert + Security Engineer + QA Engineer, 2026-04-20) surfaced:

- **BLOCKER**: v1 specified `HINCRBY` for Redis tiers, but `unified_memory.py:263-293` stores memory entries as `SETEX` JSON strings (not Hashes). `HINCRBY` is not usable. v2 uses **independent counter keys** with `INCR`.
- **HIGH**: v1 fire-and-forget pattern had no exception handling → audit hole. v2 mandates `done_callback` + dead-letter log + strong task reference + semaphore.
- **HIGH**: v1 claimed mem0 `asyncio.to_thread` wrapping was sufficient, but mem0 client is not thread-safe. v2 uses dedicated `ThreadPoolExecutor(max_workers=4)` + `asyncio.Lock`.
- **MEDIUM**: v1 AC-5/6/9 were too vague to verify. v2 rewrites each with specific observable conditions.
- **DECISION**: Sprint 170 scope stays narrow (access tracking only). Full async wrapping of `mem0.search()` / `mem0.get()` read paths remains in Sprint 172. Consequence: Sprint 170's fire-and-forget write benefit is partially masked by synchronous read blocking in LONG_TERM; this is explicitly acknowledged and measured via benchmark.

---

## User Stories

### US-1: Memory Access Counting Works End-to-End
- **As** a platform operator
- **I want** every memory retrieval to increment `access_count` and update `accessed_at` atomically
- **So that** downstream consolidation logic (Phase 3 Promote in `consolidation.py`) has real usage signal to work with

### US-2: Important Memories Auto-Promote to Long-Term
- **As** an IPA Platform user
- **I want** frequently accessed session/working memories to be automatically promoted to long-term storage
- **So that** repeatedly useful context persists across sessions without manual intervention

### US-3: Access Tracking Failures Are Observable and Non-Silent
- **As** a platform operator
- **I want** any failure in background access tracking to be written to a dead-letter log with full context
- **So that** audit completeness is maintained and failures don't silently erode consolidation correctness

---

## Technical Specifications

### Backend

#### 1. Counter Storage Design (v2 — replaces v1 HINCRBY)

**Redis Counter Keys (independent of memory entry)**:
```
Key pattern:  memory:counter:{layer}:{user_id}:{memory_id}
Value:        integer (access_count)
TTL:          matches source memory TTL (30m working, 7d session, none for pinned/long_term)
Atomicity:    INCR (built-in atomic)

Access time key (companion):
Key pattern:  memory:accessed_at:{layer}:{user_id}:{memory_id}
Value:        ISO8601 timestamp string
TTL:          same as counter key
Update:       SET (non-atomic acceptable; counter is source of truth)
```

**Why independent keys?** `unified_memory.py:263, 288` store memory entries as JSON via `SETEX`. Modifying entries requires read-modify-write (non-atomic, race condition). Independent counter avoids touching existing storage format and enables atomic `INCR`. Memory entry retrieval then merges counter into response.

**Mem0 LONG_TERM**:
- Still uses mem0 metadata update (no separate counter) — mem0 SDK manages its own persistence
- Metadata payload: `{"access_count": N, "accessed_at": "ISO8601"}`
- Wrapped with dedicated thread pool (see §3)

#### 2. Access Tracking Hook Points

**`unified_memory.py`**:
- `UnifiedMemoryManager.search()` — after forming result list, schedule `_track_access_batch(hits)` as background task
- `UnifiedMemoryManager.get(memory_id)` — on successful retrieval, schedule `_track_access_single(memory_id, layer)`
- **PINNED decision**: PINNED entries DO receive access tracking for observability, but `consolidation.py` Phase 3 Promote must skip PINNED (already at top tier). Add explicit guard in `consolidation.py` check.

**Retrieval merge**:
- When loading memory entry from Redis JSON, fetch counter key in parallel (`asyncio.gather`) and merge into returned `MemoryEntry.access_count`
- Negligible latency (Redis MGET of single key)

#### 3. Safe Background Task Pattern

**New utility**: `integrations/memory/background_tasks.py` (NEW file)

```python
class MemoryBackgroundTaskManager:
    """Safe fire-and-forget for memory ops with dead-letter logging."""

    def __init__(self, max_concurrency: int = 100):
        self._tasks: set[asyncio.Task] = set()             # strong references
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._dead_letter_log = logging.getLogger("memory.background.dlq")

    def fire_and_forget(self, coro, *, context: dict) -> None:
        async def _run():
            async with self._semaphore:
                try:
                    await coro
                except Exception as exc:
                    self._dead_letter_log.error(
                        "memory_background_task_failed",
                        extra={"context": context, "error": str(exc), "type": type(exc).__name__},
                        exc_info=True,
                    )
                    # Optional: publish to Redis DLQ for replay
                    # await self._dlq_store.push(context, exc)

        task = asyncio.create_task(_run())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def drain(self, timeout: float = 5.0) -> None:
        """For graceful shutdown and test teardown."""
        if self._tasks:
            await asyncio.wait(self._tasks, timeout=timeout)
```

All access tracking uses this utility. `context` dict carries `{memory_id, layer, user_id, operation}` for DLQ diagnosis.

#### 4. Mem0 Thread-Safety

**`mem0_client.py` additions**:
- Add `self._update_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="mem0-update")`
- Add `self._update_lock = asyncio.Lock()` (serializes metadata updates to avoid mem0 internal race)
- New method:
  ```python
  async def update_access_metadata(self, memory_id: str, count: int, accessed_at: datetime) -> None:
      async with self._update_lock:
          loop = asyncio.get_running_loop()
          await loop.run_in_executor(
              self._update_executor,
              self._memory.update,  # sync mem0 call
              memory_id,
              {"access_count": count, "accessed_at": accessed_at.isoformat()},
          )
  ```
- **Scope note**: this wraps only `update()`. `search()` / `get()` full async wrapping remains Sprint 172 scope.

#### 5. Consolidation Guard (minor)

**`consolidation.py` Phase 3 Promote**:
- Verify current promote target excludes PINNED (add explicit `if mem.layer == MemoryLayer.PINNED: continue`)
- No other logic change — Phase 3 already checks `access_count >= 5`, will now receive real data

#### 6. Observability

Structured log format (JSON lines):
```
{
  "event": "memory_access_tracked",
  "memory_id": "mem_abc123",
  "new_count": 6,
  "layer": "working",
  "tenant_id": "user_xyz",
  "operation": "search_hit" | "get_hit",
  "ts": "2026-04-20T10:00:00Z"
}
```

Counter metric (if prometheus client present): `memory_access_total{layer, memory_type, tenant_id}`.

---

### Testing

#### 7. Unit Tests (`tests/unit/integrations/memory/`)

**`test_access_tracking.py`** — covers per-tier increment:
- PINNED tier: search hit increments counter
- WORKING tier: search hit increments counter + counter TTL matches memory TTL
- SESSION tier: search hit increments counter + counter TTL matches
- LONG_TERM tier: search hit calls `mem0.update()` via executor

**`test_background_tasks.py`** — covers safe fire-and-forget:
- Exception in background coro → written to dead-letter log
- Semaphore caps concurrency under burst
- Strong reference retained until done
- `drain()` completes pending tasks

**`test_counter_edge_cases.py`** — covers edge cases:
- Counter key doesn't exist → first hit creates with value 1
- Counter TTL aligned with memory entry TTL
- Non-existent memory_id → `get()` miss does NOT increment
- Boundary: `access_count == 4` → 5th hit triggers promote on next consolidation run

#### 8. Integration Test

**`tests/integration/memory/test_promotion_triggered.py`** — E2E:
- Prerequisite: real Redis + Qdrant (via testcontainers)
- Steps:
  1. Seed memory at SESSION tier with `access_count=0`
  2. Call `search()` 5 times
  3. Call `manager.drain()` to ensure all background tasks done
  4. Verify counter key shows `5`
  5. Invoke consolidation with `force_run=True` bypass (add kwarg to `ConsolidationService.run_once()`)
  6. Assert memory now in Qdrant LONG_TERM collection with matching `memory_id`
  7. Assert original Redis session key has TTL removed or key deleted
- Rationale: `force_run=True` bypasses the `count % 20 == 0` throttle that makes natural trigger flaky

#### 9. Concurrency Test

**`test_access_tracking_concurrent.py`**:
- Launch 10 concurrent `search()` calls targeting same memory_id
- After drain, verify counter exactly equals 10 (validates `INCR` atomicity vs. HINCRBY race)

#### 10. Failure-Mode Test

**`test_access_tracking_failures.py`**:
- Redis disconnect mid-search → `search()` still returns results (fire-and-forget swallows Redis error)
- Dead-letter log receives entry with correct context
- mem0 `update()` raises → background task records failure, search response unaffected

#### 11. Latency Benchmark

**`scripts/benchmark_memory_search.py`** (NEW):
- Runs 1000 `search()` calls against fixture memory
- Reports P50 / P95 / P99 latency
- Output to `claudedocs/5-status/sprint-170-baseline-{pre|post}.json`
- CI gate: post-change P95 must be ≤ 105% of baseline (≤ 5% regression)

---

## File Changes

| File | Action | Purpose |
|------|--------|---------|
| `backend/src/integrations/memory/unified_memory.py` | Modify | Add counter key read/write, hook into `search()` + `get()`, integrate `MemoryBackgroundTaskManager` |
| `backend/src/integrations/memory/mem0_client.py` | Modify | Add `update_access_metadata()` with dedicated executor + lock |
| `backend/src/integrations/memory/background_tasks.py` | **Create** | `MemoryBackgroundTaskManager` — safe fire-and-forget utility |
| `backend/src/integrations/memory/types.py` | Modify | Ensure `access_count` default 0, `accessed_at` Optional[datetime] |
| `backend/src/integrations/memory/consolidation.py` | Modify (minor) | Skip PINNED in Phase 3 Promote; accept `force_run` kwarg for test injection |
| `backend/tests/unit/integrations/memory/test_access_tracking.py` | Create | Per-tier unit tests |
| `backend/tests/unit/integrations/memory/test_background_tasks.py` | Create | Safe fire-and-forget tests |
| `backend/tests/unit/integrations/memory/test_counter_edge_cases.py` | Create | Edge case tests |
| `backend/tests/unit/integrations/memory/test_access_tracking_concurrent.py` | Create | Concurrency atomicity test |
| `backend/tests/unit/integrations/memory/test_access_tracking_failures.py` | Create | Redis/mem0 failure path tests |
| `backend/tests/integration/memory/test_promotion_triggered.py` | Create | E2E promotion flow |
| `backend/scripts/benchmark_memory_search.py` | Create | Latency baseline + regression gate |
| `backend/claudedocs/5-status/sprint-170-baseline-pre.json` | Create (artifact) | Pre-change benchmark snapshot |

---

## Acceptance Criteria (v2 — precise and verifiable)

- [ ] **AC-1**: `search()` hit on PINNED/WORKING/SESSION increments `memory:counter:{layer}:{user_id}:{memory_id}` via `INCR` atomically (validated by concurrent test showing count == 10 after 10 concurrent hits)
- [ ] **AC-2**: `search()` hit on LONG_TERM calls `mem0.update_access_metadata()` via dedicated `ThreadPoolExecutor`, serialized by `asyncio.Lock` (no mem0 internal race)
- [ ] **AC-3**: `get(memory_id)` direct retrieval increments counter on hit; returns cleanly without increment on miss
- [ ] **AC-4**: `accessed_at` ISO8601 timestamp updated on every hit (observable via `redis-cli GET memory:accessed_at:{layer}:{user_id}:{memory_id}`)
- [ ] **AC-5**: After 5 hits + consolidation `force_run=True`, target `memory_id` appears in Qdrant LONG_TERM collection AND corresponding source tier key TTL removed (or key deleted) — verifiable via Qdrant Python client `scroll` + `redis-cli TTL`
- [ ] **AC-6**: P95 latency of `search()` post-change ≤ 105% of pre-change baseline, n=1000, measured by `scripts/benchmark_memory_search.py`, artifacts stored at `claudedocs/5-status/sprint-170-baseline-{pre|post}.json`
- [ ] **AC-7**: Background task failures (Redis disconnect, mem0 exception) write to `memory.background.dlq` logger with JSON context `{memory_id, layer, user_id, operation, error, type}` — validated by failure-mode tests
- [ ] **AC-8**: `MemoryBackgroundTaskManager` maintains strong task references (`self._tasks` set) and caps concurrency via `Semaphore(100)` — validated by burst test
- [ ] **AC-9**: Access events visible in structured log with fields `event=memory_access_tracked, memory_id, new_count, layer, tenant_id, operation, ts` (format spec above); if prometheus registry available, `memory_access_total{layer, memory_type, tenant_id}` counter increments
- [ ] **AC-10**: `consolidation.py` Phase 3 Promote explicitly skips PINNED layer (unit test asserts this)
- [ ] **AC-11**: All unit tests pass; integration test passes against real Redis + Qdrant via testcontainers

---

## Out of Scope (this Sprint)

- Full async wrapping of `mem0.search()` / `mem0.get()` read paths (Sprint 172)
- Consolidation Phase 2 Decay / Phase 5 Summarize implementations (Sprint 171)
- Tenant scope filtering on search (Sprint 173)
- Any change to promotion threshold (keep `>= 5` as-is)
- DLQ replay mechanism (log-only in this sprint; replay service is a future concern)

---

## Implementation Notes (from 2026-04-20 team review consensus)

Agent team v2 review reached **GREEN verdict** (backend-lead + py-reviewer + sec-reviewer + qa-reviewer). Six non-blocking items surfaced during verification — address opportunistically during implementation.

### MEDIUM — Security (propagate to Sprint 173 tenant-scope ADR)

1. **Tenant enumeration via Redis key pattern**
   - Counter key pattern `memory:counter:{layer}:{user_id}:{memory_id}` exposes `user_id` in plaintext
   - Redis `SCAN memory:counter:*` allows enumeration of active user_ids
   - **Sprint 170 action**: none (current design stays; document this in key design rationale)
   - **Sprint 173 action**: hash `user_id` in key or apply Redis ACL to restrict `SCAN` — add to tenant-scope ADR

2. **DLQ log PII retention**
   - `memory.background.dlq` logger writes `{memory_id, layer, user_id, operation, error, type}` — `user_id` counts as PII under GDPR
   - **Sprint 170 action**: none (standard operational logging applies)
   - **Sprint 177 action**: include DLQ log retention policy + redaction in GDPR `forget_user()` cross-layer deletion checklist

### MINOR — Implementation-time handling

3. **Counter key orphan cleanup on promotion**
   - When Phase 3 Promote moves memory from SESSION/WORKING to LONG_TERM, the source-tier counter key (`memory:counter:session:{user_id}:{id}`) becomes orphan
   - **Sprint 170 action**: add `_cleanup_counter(memory_id, source_layer)` called by promotion path in consolidation
   - **Sprint 171 action**: verify Phase 2 Decay and Phase 5 Summarize also clean counter keys for deleted/merged memories

4. **Verify mem0 `update()` signature**
   - `ThreadPoolExecutor.run_in_executor` passes positional args; if mem0's `update()` requires kwargs or has order-sensitive signature, wrap with `functools.partial`
   - **Sprint 170 action**: during coding, inspect `mem0` package's `Memory.update()` signature first; adjust wrapper accordingly in `mem0_client.py`

5. **Semaphore concurrency should be configurable**
   - v2 plan specifies `asyncio.Semaphore(100)` hardcoded
   - **Sprint 170 action**: source from `backend.core.settings` as `MEMORY_BACKGROUND_CONCURRENCY` (default 100) — allows ops tuning without redeploy
   - Add to `.env.example` with comment

6. **AC-6 benchmark gate enforcement mechanism**
   - Plan states "P95 ≤ 105% of baseline" but does not specify whether this is CI-enforced or PR-reviewer manual check
   - **Sprint 170 action**: during coding, decide — if CI-enforced, add step to backend test workflow that runs benchmark and compares against checked-in `baseline-pre.json`; if PR manual, document in PR template
   - Default recommendation: CI-enforced for catch-early value, but require `--skip-benchmark` override flag for emergency merges

---

## Deferred Technical Debt (explicit)

Tracking items that Sprint 172 must address:

1. `update_access_metadata()` thread pool + lock is a **temporary adapter**. Sprint 172 must decide whether to (a) extend the same pattern to all mem0 calls or (b) migrate to native async mem0 SDK if available.
2. `MemoryBackgroundTaskManager.drain()` is minimal; Sprint 172 may need DLQ replay API.
3. PINNED-layer access tracking is recorded but not consumed; future sprint may use for PINNED entry usefulness scoring.