"""L2 session memory restart-survival integration test (Sprint 172 AC-9).

Validates that session memories written via the dual-write path survive a
simulated backend restart — backed by PostgreSQL rather than only Redis.

Requires real PostgreSQL + Redis via testcontainers + Alembic migration
``009_session_memory`` applied. Auto-skips when infra unavailable.

Run with:
    pytest backend/tests/integration/memory/test_l2_restart_survival.py \
        -v -m integration
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest

testcontainers = pytest.importorskip(
    "testcontainers",
    reason="testcontainers required — pip install testcontainers[postgresql,redis]",
)

from testcontainers.postgres import PostgresContainer  # noqa: E402
from testcontainers.redis import RedisContainer  # noqa: E402

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def pg_container():
    with PostgresContainer("postgres:16-alpine") as container:
        yield container


@pytest.fixture(scope="module")
def redis_container():
    with RedisContainer("redis:7-alpine") as container:
        yield container


@pytest.fixture(autouse=True)
def _env(pg_container, redis_container, monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        pg_container.get_connection_url().replace("postgresql://", "postgresql+asyncpg://"),
    )
    monkeypatch.setenv("REDIS_HOST", redis_container.get_container_host_ip())
    monkeypatch.setenv("REDIS_PORT", str(redis_container.get_exposed_port(6379)))
    monkeypatch.setenv("MEMORY_L2_PG_READ_ENABLED", "true")
    yield


@pytest.mark.asyncio
async def test_session_memory_survives_restart():
    """AC-9: kill manager → new manager reads same memory from PG."""
    from src.infrastructure.database.session import close_db, init_db
    from src.integrations.memory.types import (
        MemoryConfig,
        MemoryLayer,
        MemoryMetadata,
        MemoryRecord,
        MemoryType,
    )
    from src.integrations.memory.unified_memory import UnifiedMemoryManager

    # Bootstrap DB schema (assumes alembic migration applied out-of-band,
    # or call asyncpg to create_all — pick the project's convention)
    await init_db()

    user_id = "e2e-restart-user"

    # ── Session 1: write memory
    mgr1 = UnifiedMemoryManager(config=MemoryConfig())
    await mgr1.initialize()

    record = MemoryRecord(
        id="e2e_mem_1",
        user_id=user_id,
        content="session memory under restart test",
        memory_type=MemoryType.CONVERSATION,
        layer=MemoryLayer.SESSION,
        metadata=MemoryMetadata(importance=0.6),
    )
    await mgr1._store_session_memory(record)
    await mgr1.close()

    # ── Clear Redis between sessions to simulate cache loss on restart
    import redis.asyncio as aioredis

    r = aioredis.Redis(
        host=os.environ["REDIS_HOST"],
        port=int(os.environ["REDIS_PORT"]),
        decode_responses=True,
    )
    try:
        await r.flushall()
    finally:
        await r.close()

    # ── Session 2: different manager, read via PG-first path
    mgr2 = UnifiedMemoryManager(config=MemoryConfig())
    await mgr2.initialize()

    results = await mgr2._search_session_memory(
        query="session memory under restart test",
        user_id=user_id,
        memory_types=None,
        limit=5,
    )
    await mgr2.close()

    assert len(results) >= 1
    assert any(r.memory.id == "e2e_mem_1" for r in results)

    await close_db()


@pytest.mark.asyncio
async def test_backfill_idempotent():
    """AC-4: running backfill twice produces no duplicate rows."""
    # Seed a Redis key via direct Redis access, then run backfill twice
    # (skipped when script import path isn't available in this env)
    import redis.asyncio as aioredis
    from sqlalchemy import select
    from sqlalchemy.sql import func

    from src.infrastructure.database.models.session_memory import SessionMemory
    from src.infrastructure.database.session import DatabaseSession

    r = aioredis.Redis(
        host=os.environ["REDIS_HOST"],
        port=int(os.environ["REDIS_PORT"]),
        decode_responses=True,
    )
    import json as _json

    payload = {
        "id": "idempotent_mem_1",
        "user_id": "backfill-user",
        "content": "idempotent backfill test",
        "memory_type": "conversation",
        "layer": "session",
        "metadata": {"importance": 0.4, "tags": []},
        "access_count": 0,
        "accessed_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await r.set("memory:session:backfill-user:idempotent_mem_1", _json.dumps(payload))
    finally:
        await r.close()

    # Manually invoke the backfill logic (module-level) twice
    import importlib.util

    script_path = "backend/scripts/backfill_session_memory_pg.py"
    spec = importlib.util.spec_from_file_location("backfill", script_path)
    if spec is None or spec.loader is None:
        pytest.skip("backfill script not importable from test env")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    await module._run(dry_run=False, user_filter="backfill-user")
    await module._run(dry_run=False, user_filter="backfill-user")

    async with DatabaseSession() as session:
        result = await session.execute(
            select(func.count())
            .select_from(SessionMemory)
            .where(SessionMemory.user_id == "backfill-user")
        )
        count = result.scalar() or 0

    assert count == 1, f"Expected 1 row after double-backfill, got {count}"
