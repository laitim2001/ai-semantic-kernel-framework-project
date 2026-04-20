# Sprint 172 Plan — Session L2 PostgreSQL + Mem0 Full Async Wrapping

**Phase**: 48 — Memory System Improvements
**Sprint**: 172
**Branch**: `research/memory-system-enterprise`
**Worktree**: `ai-semantic-kernel-memory-research`
**Date**: 2026-04-20
**Depends on**: Sprint 170 (`MemoryBackgroundTaskManager` + mem0 update executor established)

---

## Background

Two V9-audit-identified defects addressed together because they share the same migration window:

1. **L2 Session Memory never landed on PostgreSQL** — `unified_memory.py:287` note: "In production, this would use PostgreSQL". Currently uses Redis with longer TTL. Means process restart loses session state.

2. **Mem0 SDK sync calls in async methods** — `mem0_client.py:238, 283, etc.` blocks asyncio event loop under high QPS. Sprint 170 wrapped `update()` only as temporary adapter. Sprint 172 finishes the job — wrap `search()`, `get()`, `add()`, `get_all()`, `delete()`.

Also resolves **Sprint 170 Deferred Technical Debt items #1 and #2**.

---

## User Stories

### US-1: Session Memory Survives Process Restart
- **As** an IPA Platform user
- **I want** my session state (7-day TTL memories) to survive backend restarts
- **So that** conversations in progress don't lose context on deploy

### US-2: Memory Retrieval Never Blocks Event Loop
- **As** a platform operator
- **I want** every mem0 SDK call wrapped in `asyncio.to_thread` / executor
- **So that** high-concurrency retrieval doesn't stall other async work (SSE streams, pipeline steps)

### US-3: Dual-Write Migration for Safe Rollout
- **As** a platform operator
- **I want** L2 Session Memory to dual-write Redis + PostgreSQL during migration
- **So that** failure rollback is possible without data loss

---

## Technical Specifications

### Backend — L2 PostgreSQL Landing

1. **ORM Model** (`domain/sessions/models/session_memory.py`)
   - Table: `session_memory`
   - Columns: `id UUID PK`, `user_id`, `memory_id` (unique), `content TEXT`, `memory_type`, `importance FLOAT`, `access_count INT`, `accessed_at TIMESTAMPTZ`, `created_at`, `expires_at TIMESTAMPTZ`, `metadata JSONB`, `tags TEXT[]`
   - Indexes: `(user_id)`, `(expires_at)` for cleanup, `(memory_id)` unique

2. **Repository** (`domain/sessions/repositories/session_memory.py`)
   - `get_by_memory_id(memory_id)`, `list_by_user(user_id, limit)`, `upsert(entry)`, `delete_expired()`, `delete(memory_id)`
   - Extends `BaseRepository`

3. **Alembic Migration**
   - `migrations/versions/XXX_add_session_memory_table.py`
   - Up: create table + indexes
   - Down: drop table

4. **Dual-Write Strategy**
   - `UnifiedMemoryManager._store_session_memory()` modified:
     - Write to Redis (existing code path) AND `session_memory_repo.upsert()`
     - Read: try PostgreSQL first; fallback to Redis; log fallback rate
     - Feature flag `MEMORY_L2_PG_READ_ENABLED` (default False in dev, True in prod after migration)

5. **Backfill Script** (`scripts/backfill_session_memory_pg.py`)
   - Reads all `conv:*` keys from Redis
   - Upserts into PostgreSQL
   - Idempotent (uses `ON CONFLICT (memory_id) DO UPDATE`)
   - Run once before enabling `MEMORY_L2_PG_READ_ENABLED=True`

6. **Expiration Cleanup**
   - Background task (Celery or asyncio loop) deletes `expires_at < now()` every 1 hour
   - Replaces Redis TTL semantics in PostgreSQL

### Backend — Mem0 Full Async Wrapping

7. **Mem0Client refactor** (`mem0_client.py`)
   - Expand Sprint 170's pattern to all sync calls:
     - `search_memory()` → `await loop.run_in_executor(self._executor, self._memory.search, ...)`
     - `get_memory()` → similar
     - `add()` → similar
     - `get_all()` → similar
     - `delete()` → similar
   - `self._update_executor` renamed to `self._executor` (shared for all sync ops)
   - `max_workers=8` (up from 4 since more ops share the pool)
   - `asyncio.Lock` only on mutating ops (`add`, `update`, `delete`); reads (`search`, `get`, `get_all`) use executor without lock
   - Executor shutdown in `close()` / `__aexit__`

8. **Concurrency Configuration**
   - `MEM0_EXECUTOR_WORKERS: int = 8` in settings
   - `MEM0_MUTATION_LOCK_TIMEOUT: float = 5.0` seconds

### Testing

9. **Unit Tests**
   - `test_session_memory_repo.py` — CRUD operations
   - `test_session_memory_dual_write.py` — Redis+PG write, PG-first read, fallback
   - `test_session_memory_expiration.py` — `delete_expired()` correctness
   - `test_mem0_full_async.py` — all 5 ops non-blocking (measure event loop lag)

10. **Integration Test**
    - `test_l2_restart_survival.py` — seed session memory → kill+restart backend → verify memory retrievable from PG
    - `test_backfill_idempotent.py` — run backfill twice, verify no duplicates

11. **Performance Benchmark**
    - `scripts/benchmark_mem0_async.py` — concurrent 100 searches, measure P95 event loop lag (should be < 10ms post-wrap)

---

## File Changes

| File | Action | Purpose |
|------|--------|---------|
| `backend/src/domain/sessions/models/session_memory.py` | Create | ORM model |
| `backend/src/domain/sessions/repositories/session_memory.py` | Create | Repository |
| `backend/alembic/versions/XXX_add_session_memory.py` | Create | Migration |
| `backend/src/integrations/memory/unified_memory.py` | Modify | Dual-write + PG-first read logic |
| `backend/src/integrations/memory/mem0_client.py` | Modify | All 5 ops wrapped in executor |
| `backend/scripts/backfill_session_memory_pg.py` | Create | One-time migration |
| `backend/scripts/benchmark_mem0_async.py` | Create | Perf benchmark |
| `backend/src/core/settings.py` | Modify | Feature flag + mem0 concurrency config |
| `backend/src/infrastructure/messaging/cleanup_tasks.py` (or similar) | Modify | Session memory expiration task |
| `backend/tests/unit/domain/sessions/test_session_memory_repo.py` | Create | Repo tests |
| `backend/tests/unit/integrations/memory/test_session_memory_dual_write.py` | Create | Dual-write tests |
| `backend/tests/unit/integrations/memory/test_mem0_full_async.py` | Create | Async wrapping tests |
| `backend/tests/integration/memory/test_l2_restart_survival.py` | Create | Restart E2E |

---

## Acceptance Criteria

- [ ] **AC-1**: `session_memory` table created via Alembic migration; indexes present
- [ ] **AC-2**: `UnifiedMemoryManager._store_session_memory()` dual-writes Redis + PG (no regressions in Redis behavior)
- [ ] **AC-3**: `MEMORY_L2_PG_READ_ENABLED=True` → reads from PG first, Redis fallback rate logged as metric
- [ ] **AC-4**: Backfill script idempotent — running twice produces no duplicates
- [ ] **AC-5**: Expiration background task deletes rows where `expires_at < now()` every 1h
- [ ] **AC-6**: All 5 mem0 ops (`search`, `get`, `add`, `update`, `get_all`, `delete`) wrapped in executor
- [ ] **AC-7**: Event loop lag during concurrent 100 mem0 ops stays < 10ms P95 (measurable via benchmark)
- [ ] **AC-8**: `asyncio.Lock` serializes mutations only; reads proceed in parallel (measurable via timing)
- [ ] **AC-9**: Restart survival test — kill backend mid-conversation → restart → same session memory accessible
- [ ] **AC-10**: All unit tests pass; integration test with real PG passes

---

## Out of Scope

- Migration of existing Redis session keys in production (ops task, not code)
- Tenant scope columns (Sprint 173 will add `org_id` / `workspace_id`)
- Native async mem0 SDK adoption (no stable release yet; revisit Sprint 178+)
- Bitemporal fields on session_memory (Sprint 174 will extend)
