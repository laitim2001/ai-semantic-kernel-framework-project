"""Unit tests for Consolidation Phase 2 Decay (Sprint 171 AC-1 / AC-2 / AC-3)."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.integrations.memory.background_tasks import MemoryBackgroundTaskManager
from src.integrations.memory.consolidation import MemoryConsolidationService
from src.integrations.memory.types import (
    MemoryConfig,
    MemoryLayer,
    MemoryMetadata,
    MemoryRecord,
    MemoryType,
)


def _make_record(
    mem_id: str,
    importance: float,
    access_count: int = 0,
    days_old: int = 14,
    layer: MemoryLayer = MemoryLayer.SESSION,
) -> MemoryRecord:
    now = datetime.now(timezone.utc)
    accessed = now - timedelta(days=days_old)
    return MemoryRecord(
        id=mem_id,
        user_id="user_decay",
        content=f"fixture {mem_id}",
        memory_type=MemoryType.CONVERSATION,
        layer=layer,
        metadata=MemoryMetadata(importance=importance),
        accessed_at=accessed,
        access_count=access_count,
    )


def _make_service(records: list[MemoryRecord]) -> tuple[MemoryConsolidationService, AsyncMock]:
    """Build consolidation service with mocked memory_manager."""
    config = MemoryConfig()
    mgr = MagicMock()
    mgr.config = config
    mgr.get_user_memories = AsyncMock(return_value=records)
    mgr.update_importance = AsyncMock(return_value=True)
    mgr._embedding_service = MagicMock()
    mgr._background_tasks = MemoryBackgroundTaskManager(max_concurrency=10)
    svc = MemoryConsolidationService(memory_manager=mgr)
    return svc, mgr


@pytest.mark.asyncio
async def test_decay_formula_correctness():
    """AC-1: new = old * exp(-λ * days) — verify against known values."""
    record = _make_record("m1", importance=0.8, days_old=14)
    svc, mgr = _make_service([record])

    count = await svc._apply_decay("user_decay")
    await mgr._background_tasks.drain(timeout=2.0)

    assert count == 1
    mgr.update_importance.assert_awaited_once()
    call = mgr.update_importance.await_args.kwargs
    expected = 0.8 * math.exp(-0.05 * 14)  # ≈ 0.3975
    assert abs(call["new_importance"] - expected) < 0.001
    assert call["memory_id"] == "m1"
    assert call["layer"] == MemoryLayer.SESSION


@pytest.mark.asyncio
async def test_decay_floor_enforcement():
    """AC-3: importance never drops below MEMORY_DECAY_MIN_IMPORTANCE."""
    # Start at 0.12 with 100 days old → raw new ≈ 0.12 * exp(-5) ≈ 0.00081
    record = _make_record("m_floor", importance=0.12, days_old=100)
    svc, mgr = _make_service([record])

    await svc._apply_decay("user_decay")
    await mgr._background_tasks.drain(timeout=2.0)

    call = mgr.update_importance.await_args.kwargs
    # Floor = 0.1; raw decayed value (~0.00081) should be clamped to 0.1
    assert call["new_importance"] == pytest.approx(0.1, abs=1e-9)


@pytest.mark.asyncio
async def test_decay_skip_on_high_access_count():
    """AC-2: memory with access_count >= threshold is not decayed."""
    # Default threshold = 3
    active_record = _make_record("active", importance=0.8, access_count=5, days_old=30)
    stale_record = _make_record("stale", importance=0.8, access_count=0, days_old=30)
    svc, mgr = _make_service([active_record, stale_record])

    count = await svc._apply_decay("user_decay")
    await mgr._background_tasks.drain(timeout=2.0)

    assert count == 1, "Only the stale record should have been decayed"
    # update_importance should be called only once (for 'stale')
    assert mgr.update_importance.await_count == 1
    call = mgr.update_importance.await_args.kwargs
    assert call["memory_id"] == "stale"


@pytest.mark.asyncio
async def test_decay_writeback_dispatched_per_tier():
    """Writeback reaches update_importance() for SESSION and LONG_TERM alike."""
    session = _make_record("s1", importance=0.8, days_old=30, layer=MemoryLayer.SESSION)
    long_term = _make_record("lt1", importance=0.8, days_old=30, layer=MemoryLayer.LONG_TERM)
    svc, mgr = _make_service([session, long_term])

    count = await svc._apply_decay("user_decay")
    await mgr._background_tasks.drain(timeout=2.0)

    assert count == 2
    assert mgr.update_importance.await_count == 2
    layers_called = {call.kwargs["layer"] for call in mgr.update_importance.await_args_list}
    assert layers_called == {MemoryLayer.SESSION, MemoryLayer.LONG_TERM}


@pytest.mark.asyncio
async def test_decay_null_accessed_at_falls_back_to_created_at():
    """v2 MEDIUM fix: accessed_at=None uses created_at for days calculation."""
    now = datetime.now(timezone.utc)
    record = MemoryRecord(
        id="never_accessed",
        user_id="user_decay",
        content="x",
        memory_type=MemoryType.CONVERSATION,
        layer=MemoryLayer.SESSION,
        metadata=MemoryMetadata(importance=0.8),
        created_at=now - timedelta(days=14),
        accessed_at=None,
        access_count=0,
    )
    svc, mgr = _make_service([record])

    await svc._apply_decay("user_decay")
    await mgr._background_tasks.drain(timeout=2.0)

    assert mgr.update_importance.await_count == 1
    call = mgr.update_importance.await_args.kwargs
    # Same as 14-day decay since created_at was 14 days ago
    expected = 0.8 * math.exp(-0.05 * 14)
    assert abs(call["new_importance"] - expected) < 0.01
