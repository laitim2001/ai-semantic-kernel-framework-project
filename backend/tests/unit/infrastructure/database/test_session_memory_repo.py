"""Unit tests for SessionMemoryRepository (Sprint 172 AC-1 / AC-4 / AC-5).

Uses mocked AsyncSession — integration/real-DB coverage lives in
``test_l2_restart_survival.py``. These tests validate query composition +
method contracts without Docker overhead.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.database.models.session_memory import SessionMemory
from src.infrastructure.database.repositories.session_memory import (
    SessionMemoryRepository,
)


def _make_repo():
    session = AsyncMock()
    repo = SessionMemoryRepository(session)
    return repo, session


@pytest.mark.asyncio
async def test_get_by_memory_id_returns_scalar_one_or_none():
    repo, session = _make_repo()
    mock_row = MagicMock(spec=SessionMemory)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = mock_row
    session.execute = AsyncMock(return_value=result_mock)

    returned = await repo.get_by_memory_id("mem_xyz")

    assert returned is mock_row
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_memory_id_miss_returns_none():
    repo, session = _make_repo()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=result_mock)

    returned = await repo.get_by_memory_id("missing")

    assert returned is None


@pytest.mark.asyncio
async def test_list_by_user_invokes_select_and_returns_scalars():
    repo, session = _make_repo()
    mock_rows = [MagicMock(spec=SessionMemory) for _ in range(3)]
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = mock_rows
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    session.execute = AsyncMock(return_value=result_mock)

    returned = await repo.list_by_user("user_a", limit=10)

    assert returned == mock_rows
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_by_memory_id_returns_true_when_row_removed():
    repo, session = _make_repo()
    result_mock = MagicMock()
    result_mock.rowcount = 1
    session.execute = AsyncMock(return_value=result_mock)
    session.flush = AsyncMock()

    removed = await repo.delete_by_memory_id("mem_abc")

    assert removed is True


@pytest.mark.asyncio
async def test_delete_by_memory_id_returns_false_when_no_row():
    repo, session = _make_repo()
    result_mock = MagicMock()
    result_mock.rowcount = 0
    session.execute = AsyncMock(return_value=result_mock)
    session.flush = AsyncMock()

    removed = await repo.delete_by_memory_id("mem_missing")

    assert removed is False


@pytest.mark.asyncio
async def test_delete_expired_returns_rowcount():
    """AC-5: expired rows cleanup reports count."""
    repo, session = _make_repo()
    result_mock = MagicMock()
    result_mock.rowcount = 42
    session.execute = AsyncMock(return_value=result_mock)
    session.flush = AsyncMock()

    count = await repo.delete_expired()

    assert count == 42
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_executes_pg_insert_on_conflict():
    """AC-4: upsert uses PostgreSQL ON CONFLICT via pg_insert."""
    repo, session = _make_repo()
    mock_row = MagicMock(spec=SessionMemory)
    result_mock = MagicMock()
    result_mock.scalar_one.return_value = mock_row
    session.execute = AsyncMock(return_value=result_mock)
    session.flush = AsyncMock()

    returned = await repo.upsert(
        memory_id="mem_new",
        user_id="user_a",
        content="content",
        memory_type="conversation",
        importance=0.7,
        access_count=3,
        accessed_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        extra_metadata={"source": "test"},
        tags=["t1", "t2"],
    )

    assert returned is mock_row
    session.execute.assert_awaited_once()
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_idempotent_same_memory_id_twice():
    """Running upsert twice with same memory_id produces the same row
    (relies on ON CONFLICT DO UPDATE contract — mock just confirms no
    error and single execute per call)."""
    repo, session = _make_repo()
    mock_row = MagicMock(spec=SessionMemory)
    result_mock = MagicMock()
    result_mock.scalar_one.return_value = mock_row
    session.execute = AsyncMock(return_value=result_mock)
    session.flush = AsyncMock()

    # First call
    row1 = await repo.upsert(
        memory_id="mem_idempotent",
        user_id="user_a",
        content="v1",
        memory_type="conversation",
        importance=0.5,
    )
    # Second call with updated content
    row2 = await repo.upsert(
        memory_id="mem_idempotent",
        user_id="user_a",
        content="v2",
        memory_type="conversation",
        importance=0.6,
    )

    assert row1 is mock_row
    assert row2 is mock_row
    assert session.execute.await_count == 2
