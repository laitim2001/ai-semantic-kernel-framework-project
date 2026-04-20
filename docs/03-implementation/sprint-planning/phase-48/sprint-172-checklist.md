# Sprint 172 Checklist — Session L2 PostgreSQL + Mem0 Async

**Sprint**: 172
**Branch**: `research/memory-system-enterprise`
**Plan**: [sprint-172-plan.md](sprint-172-plan.md)

---

## Backend — ORM & Migration

- [x] `SessionMemory` ORM model in `infrastructure/database/models/session_memory.py`
- [x] Columns: id/user_id/memory_id(unique)/content/memory_type/importance/access_count/accessed_at/created_at/expires_at/extra_metadata/tags
- [x] Indexes: `(user_id)`, `(expires_at)`, `(memory_id)` unique
- [x] `SessionMemoryRepository` with CRUD methods
- [x] Alembic migration (up + down)
- [x] Model registered in `infrastructure/database/models/__init__.py`

## Backend — Dual-Write Integration

- [x] `UnifiedMemoryManager._store_session_memory()` dual-writes Redis + PG
- [x] Redis write path unchanged (backward compat)
- [x] PG write path using `SessionMemoryRepository.upsert()`
- [x] `MEMORY_L2_PG_READ_ENABLED` feature flag in settings
- [x] PG-first read path with Redis fallback when flag enabled
- [x] `memory_l2_read_source_total{source=pg|redis}` metric (log-based event)

## Backend — Backfill Script

- [x] `scripts/backfill_session_memory_pg.py` idempotent
- [x] Scans Redis `memory:session:*` keys
- [x] Upserts to PG (`ON CONFLICT DO UPDATE`)
- [x] Progress output + summary count
- [x] Dry-run mode

## Backend — Expiration Cleanup

- [x] `SessionMemoryRepository.delete_expired()` implemented
- [ ] Registered in existing cleanup orchestration (Celery / asyncio loop)

## Backend — Mem0 Full Async

- [x] `self._executor = ThreadPoolExecutor(max_workers=MEM0_EXECUTOR_WORKERS, thread_name_prefix="mem0")`
- [x] `self._mutation_lock = asyncio.Lock()` for add/update/delete
- [x] `search_memory()` via executor (no lock — read)
- [x] `get_memory()` via executor (no lock — read)
- [x] `get_all()` via executor (no lock — read)
- [x] `add()` via executor + mutation lock
- [x] `update()` via executor + mutation lock (rename Sprint 170's method to unified style)
- [x] `delete()` via executor + mutation lock
- [x] `close()` / `__aexit__` shuts down executor cleanly
- [x] `MEM0_EXECUTOR_WORKERS` and `MEM0_MUTATION_LOCK_TIMEOUT` in settings

## Tests — Unit

- [x] `test_session_memory_repo.py` — CRUD + expiration filter
- [x] `test_session_memory_dual_write.py` — both writes succeed; failure of one doesn't kill other (graceful)
- [x] `test_session_memory_dual_write.py` — PG-first read + Redis fallback metric
- [ ] `test_session_memory_expiration.py` — `delete_expired()` correctness (merged into repo test)
- [x] `test_mem0_full_async.py` — all ops non-blocking (event loop lag assertion)
- [x] `test_mem0_full_async.py` — reads parallel, mutations serialized (timing test)
- [x] `test_mem0_full_async.py` — executor shutdown on close

## Tests — Integration

- [x] `test_l2_restart_survival.py` — seed → simulate restart → verify PG retrieval
- [x] `test_backfill_idempotent.py` — run twice, count rows before/after equal (merged into restart_survival)

## Benchmark

- [x] `scripts/benchmark_mem0_async.py` — 100 concurrent ops, event loop lag measurement
- [ ] Pre-change baseline captured in `claudedocs/5-status/sprint-172-baseline-pre.json`
- [ ] Post-change snapshot in `sprint-172-baseline-post.json`
- [ ] Post event loop lag P95 ≤ 10ms

## Verification

- [x] All Python files pass `black`, `isort`, `flake8`, `mypy`
- [ ] Alembic migration runs `upgrade head` without errors
- [ ] Alembic migration reverses cleanly `downgrade -1`
- [x] Run `pytest backend/tests/unit/domain/sessions/ backend/tests/unit/integrations/memory/test_session_memory_dual_write.py test_mem0_full_async.py -v`
- [ ] Run `pytest backend/tests/integration/memory/test_l2_restart_survival.py -v`
- [ ] Manual: seed 10 session memories → kill backend → restart → `psql "SELECT COUNT(*) FROM session_memory"` returns 10
- [ ] Manual: run `backfill_session_memory_pg.py --dry-run` → verify expected count
- [ ] Run backfill for real → `MEMORY_L2_PG_READ_ENABLED=True` → observe fallback rate → expect < 1%
