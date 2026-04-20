# Sprint 172 Checklist — Session L2 PostgreSQL + Mem0 Async

**Sprint**: 172
**Branch**: `research/memory-system-enterprise`
**Plan**: [sprint-172-plan.md](sprint-172-plan.md)

---

## Backend — ORM & Migration

- [ ] `SessionMemory` ORM model in `domain/sessions/models/session_memory.py`
- [ ] Columns: id/user_id/memory_id(unique)/content/memory_type/importance/access_count/accessed_at/created_at/expires_at/metadata/tags
- [ ] Indexes: `(user_id)`, `(expires_at)`, `(memory_id)` unique
- [ ] `SessionMemoryRepository` with CRUD methods
- [ ] Alembic migration (up + down)
- [ ] Model registered in `domain/sessions/models/__init__.py`

## Backend — Dual-Write Integration

- [ ] `UnifiedMemoryManager._store_session_memory()` dual-writes Redis + PG
- [ ] Redis write path unchanged (backward compat)
- [ ] PG write path using `SessionMemoryRepository.upsert()`
- [ ] `MEMORY_L2_PG_READ_ENABLED` feature flag in settings
- [ ] PG-first read path with Redis fallback when flag enabled
- [ ] `memory_l2_read_source_total{source=pg|redis}` metric

## Backend — Backfill Script

- [ ] `scripts/backfill_session_memory_pg.py` idempotent
- [ ] Scans Redis `conv:*` keys
- [ ] Upserts to PG (`ON CONFLICT DO UPDATE`)
- [ ] Progress output + summary count
- [ ] Dry-run mode

## Backend — Expiration Cleanup

- [ ] Background task `delete_expired_session_memories()` every 1h
- [ ] Registered in existing cleanup orchestration (Celery / asyncio loop)

## Backend — Mem0 Full Async

- [ ] `self._executor = ThreadPoolExecutor(max_workers=MEM0_EXECUTOR_WORKERS, thread_name_prefix="mem0")`
- [ ] `self._mutation_lock = asyncio.Lock()` for add/update/delete
- [ ] `search_memory()` via executor (no lock — read)
- [ ] `get_memory()` via executor (no lock — read)
- [ ] `get_all()` via executor (no lock — read)
- [ ] `add()` via executor + mutation lock
- [ ] `update()` via executor + mutation lock (rename Sprint 170's method to unified style)
- [ ] `delete()` via executor + mutation lock
- [ ] `close()` / `__aexit__` shuts down executor cleanly
- [ ] `MEM0_EXECUTOR_WORKERS` and `MEM0_MUTATION_LOCK_TIMEOUT` in settings

## Tests — Unit

- [ ] `test_session_memory_repo.py` — CRUD + expiration filter
- [ ] `test_session_memory_dual_write.py` — both writes succeed; failure of one doesn't kill other (graceful)
- [ ] `test_session_memory_dual_write.py` — PG-first read + Redis fallback metric
- [ ] `test_session_memory_expiration.py` — `delete_expired()` correctness
- [ ] `test_mem0_full_async.py` — all ops non-blocking (event loop lag assertion)
- [ ] `test_mem0_full_async.py` — reads parallel, mutations serialized (timing test)
- [ ] `test_mem0_full_async.py` — executor shutdown on close

## Tests — Integration

- [ ] `test_l2_restart_survival.py` — seed → simulate restart → verify PG retrieval
- [ ] `test_backfill_idempotent.py` — run twice, count rows before/after equal

## Benchmark

- [ ] `scripts/benchmark_mem0_async.py` — 100 concurrent ops, event loop lag measurement
- [ ] Pre-change baseline captured in `claudedocs/5-status/sprint-172-baseline-pre.json`
- [ ] Post-change snapshot in `sprint-172-baseline-post.json`
- [ ] Post event loop lag P95 ≤ 10ms

## Verification

- [ ] All Python files pass `black`, `isort`, `flake8`, `mypy`
- [ ] Alembic migration runs `upgrade head` without errors
- [ ] Alembic migration reverses cleanly `downgrade -1`
- [ ] Run `pytest backend/tests/unit/domain/sessions/ backend/tests/unit/integrations/memory/test_session_memory_dual_write.py test_mem0_full_async.py -v`
- [ ] Run `pytest backend/tests/integration/memory/test_l2_restart_survival.py -v`
- [ ] Manual: seed 10 session memories → kill backend → restart → `psql "SELECT COUNT(*) FROM session_memory"` returns 10
- [ ] Manual: run `backfill_session_memory_pg.py --dry-run` → verify expected count
- [ ] Run backfill for real → `MEMORY_L2_PG_READ_ENABLED=True` → observe fallback rate → expect < 1%
