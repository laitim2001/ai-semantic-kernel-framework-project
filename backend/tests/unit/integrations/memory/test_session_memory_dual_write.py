"""Dual-write tests for L2 session memory (Sprint 172 AC-2 / AC-3).

Validates the PG-first + Redis-best-effort contract:
  - PG success + Redis success → both receive the record
  - PG failure → operation raises, Redis not written
  - PG success + Redis failure → operation proceeds, warning logged
  - Read path PG-first with fallback + source metric log
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.memory.types import (
    MemoryConfig,
    MemoryLayer,
    MemoryMetadata,
    MemoryRecord,
    MemoryType,
)
from src.integrations.memory.unified_memory import UnifiedMemoryManager


def _make_record(memory_id: str = "mem_dual") -> MemoryRecord:
    return MemoryRecord(
        id=memory_id,
        user_id="user_dual",
        content="dual-write fixture",
        memory_type=MemoryType.CONVERSATION,
        layer=MemoryLayer.SESSION,
        metadata=MemoryMetadata(importance=0.5, tags=["t"]),
    )


def _mock_session_factory(upsert_result=None, upsert_raises: Exception | None = None):
    """Produce an async-context-manager factory yielding a stub AsyncSession.

    Returned factory also exposes ``session_mock`` and ``upsert_calls`` so
    assertions can peek at invocations.
    """
    session_mock = AsyncMock()

    upsert_calls: list[dict] = []

    async def _fake_upsert(**kwargs):
        upsert_calls.append(kwargs)
        if upsert_raises is not None:
            raise upsert_raises
        return upsert_result or MagicMock()

    patcher = patch(
        "src.infrastructure.database.repositories.session_memory.SessionMemoryRepository",
        autospec=True,
    )

    @asynccontextmanager
    async def _factory():
        mock_cls = patcher.start()
        repo_instance = mock_cls.return_value
        repo_instance.upsert = AsyncMock(side_effect=_fake_upsert)
        try:
            yield session_mock
        finally:
            patcher.stop()

    _factory.upsert_calls = upsert_calls  # type: ignore[attr-defined]
    _factory.session_mock = session_mock  # type: ignore[attr-defined]
    return _factory


def _make_manager(session_factory, redis_mock) -> UnifiedMemoryManager:
    mgr = UnifiedMemoryManager(
        config=MemoryConfig(),
        session_factory=session_factory,
    )
    mgr._redis = redis_mock
    mgr._mem0_client = AsyncMock()
    mgr._initialized = True
    return mgr


@pytest.mark.asyncio
async def test_pg_success_redis_success_both_write():
    """Both writes succeed → PG called, Redis setex called."""
    factory = _mock_session_factory()
    redis_mock = AsyncMock()
    redis_mock.setex = AsyncMock(return_value=True)
    mgr = _make_manager(factory, redis_mock)

    await mgr._store_session_memory(_make_record())

    # PG upsert called
    assert len(factory.upsert_calls) == 1
    assert factory.upsert_calls[0]["memory_id"] == "mem_dual"
    # Redis cache written
    redis_mock.setex.assert_awaited_once()


@pytest.mark.asyncio
async def test_pg_failure_raises_no_redis_write():
    """v2 HIGH: PG is authoritative — failure must raise without Redis orphan."""
    factory = _mock_session_factory(upsert_raises=RuntimeError("pg down"))
    redis_mock = AsyncMock()
    redis_mock.setex = AsyncMock()
    mgr = _make_manager(factory, redis_mock)

    with pytest.raises(RuntimeError, match="pg down"):
        await mgr._store_session_memory(_make_record())

    redis_mock.setex.assert_not_awaited()


@pytest.mark.asyncio
async def test_pg_success_redis_failure_does_not_raise(caplog):
    """Redis cache failure is best-effort — operation continues silently."""
    factory = _mock_session_factory()
    redis_mock = AsyncMock()
    redis_mock.setex = AsyncMock(side_effect=ConnectionError("redis down"))
    mgr = _make_manager(factory, redis_mock)

    with caplog.at_level(logging.WARNING):
        # Should NOT raise
        await mgr._store_session_memory(_make_record())

    assert len(factory.upsert_calls) == 1
    # Warning logged for Redis failure
    assert any(
        "session_memory_redis_cache_failed" in record.message
        or record.__dict__.get("event") == "session_memory_redis_cache_failed"
        for record in caplog.records
    ) or any("session_memory_redis_cache_failed" in str(r) for r in caplog.records)


@pytest.mark.asyncio
async def test_no_pg_factory_falls_back_to_redis_only():
    """Legacy path (no PG wired) keeps pre-Sprint-172 Redis-only semantics."""
    redis_mock = AsyncMock()
    redis_mock.setex = AsyncMock(return_value=True)

    # Force PG context to be unavailable by monkey-patching the import
    with patch(
        "src.infrastructure.database.session.DatabaseSession",
        side_effect=Exception("no db"),
    ):
        mgr = UnifiedMemoryManager(config=MemoryConfig(), session_factory=None)
        mgr._redis = redis_mock
        mgr._mem0_client = AsyncMock()
        mgr._initialized = True

        await mgr._store_session_memory(_make_record())

    # Only Redis write happened; PG path unavailable
    redis_mock.setex.assert_awaited_once()


@pytest.mark.asyncio
async def test_pg_first_read_returns_pg_results_when_flag_enabled(caplog):
    """AC-3: MEMORY_L2_PG_READ_ENABLED=True → PG branch taken + source=pg log."""
    from datetime import datetime, timezone

    # Need a proper async factory that yields via `async with`
    session_mock = AsyncMock()

    @asynccontextmanager
    async def _real_factory():
        yield session_mock

    # Build manager with flag on
    config = MemoryConfig()
    config.memory_l2_pg_read_enabled = True  # type: ignore[misc]
    mgr = UnifiedMemoryManager(config=config, session_factory=_real_factory)

    # Stub repo.list_by_user via the class import path
    fake_rows = [
        MagicMock(
            memory_id="m1",
            user_id="u",
            content="hello world",
            memory_type="conversation",
            importance=0.5,
            access_count=0,
            accessed_at=None,
            created_at=datetime.now(timezone.utc),
            extra_metadata={"importance": 0.5, "tags": []},
        )
    ]
    embed_service = MagicMock()
    embed_service.embed_text = AsyncMock(return_value=[1.0, 0.0])
    mgr._embedding_service = embed_service
    mgr._initialized = True

    with patch(
        "src.infrastructure.database.repositories.session_memory.SessionMemoryRepository"
    ) as repo_cls:
        repo_instance = repo_cls.return_value
        repo_instance.list_by_user = AsyncMock(return_value=fake_rows)

        with caplog.at_level(logging.INFO):
            results = await mgr._search_session_memory(
                query="hello", user_id="u", memory_types=None, limit=5
            )

    assert len(results) == 1
    assert results[0].memory.id == "m1"
    # Source label logged
    assert any(
        rec.__dict__.get("event") == "memory_l2_read_source" and rec.__dict__.get("source") == "pg"
        for rec in caplog.records
    )


@pytest.mark.asyncio
async def test_flag_enabled_but_pg_unavailable_logs_redis_fallback(caplog):
    """When flag on but PG factory raises, source=redis_fallback is logged."""

    # Manager with flag on but factory raising on entry
    @asynccontextmanager
    async def _raising_factory():
        raise ConnectionError("pg unavailable")
        yield  # unreachable, satisfies generator contract

    config = MemoryConfig()
    config.memory_l2_pg_read_enabled = True  # type: ignore[misc]
    mgr = UnifiedMemoryManager(config=config, session_factory=_raising_factory)

    # Redis fallback set up with zero keys (empty result)
    redis_mock = AsyncMock()

    async def _empty_scan(*_args, **_kwargs):
        # Async iterator yielding no keys
        if False:
            yield  # pragma: no cover

    redis_mock.scan_iter = _empty_scan
    mgr._redis = redis_mock
    mgr._embedding_service = MagicMock()
    mgr._embedding_service.embed_text = AsyncMock(return_value=[1.0])
    mgr._initialized = True

    with caplog.at_level(logging.INFO):
        results = await mgr._search_session_memory(
            query="q", user_id="u", memory_types=None, limit=5
        )

    assert results == []
    assert any(
        rec.__dict__.get("event") == "memory_l2_read_source"
        and rec.__dict__.get("source") == "redis_fallback"
        for rec in caplog.records
    )
