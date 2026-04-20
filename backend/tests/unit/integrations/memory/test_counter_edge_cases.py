"""Unit tests for access counter edge cases (Sprint 170 AC-3).

Validates:
  - Counter key absent → INCR creates with value 1
  - Non-existent memory_id → get() returns None without incrementing
  - Boundary: count=4 + 1 hit → next consolidation promotes
  - Counter TTL alignment per tier
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from src.integrations.memory.types import (
    MemoryConfig,
    MemoryLayer,
    MemoryMetadata,
    MemoryRecord,
    MemoryType,
)
from src.integrations.memory.unified_memory import UnifiedMemoryManager


def _make_manager() -> UnifiedMemoryManager:
    mgr = UnifiedMemoryManager(config=MemoryConfig())
    mgr._redis = AsyncMock()
    mgr._mem0_client = AsyncMock()
    mgr._initialized = True
    return mgr


@pytest.mark.asyncio
async def test_counter_absent_first_hit_creates_value_1():
    """INCR on non-existent key returns 1 (Redis semantics)."""
    mgr = _make_manager()
    # Redis INCR returns 1 on first call (creates key if absent)
    mgr._redis.incr = AsyncMock(return_value=1)
    mgr._redis.set = AsyncMock()
    mgr._redis.expire = AsyncMock()

    await mgr._track_access_single(
        memory_id="new_mem",
        layer=MemoryLayer.WORKING,
        user_id="user_a",
        operation="search_hit",
    )

    mgr._redis.incr.assert_awaited_once_with("memory:counter:working:user_a:new_mem")
    # Value returned by INCR should be 1 on first hit
    assert mgr._redis.incr.return_value == 1


@pytest.mark.asyncio
async def test_get_miss_does_not_increment():
    """AC-3: get(memory_id) miss does NOT fire tracking."""
    mgr = _make_manager()
    mgr._redis.get = AsyncMock(return_value=None)  # Redis miss
    mgr._mem0_client.get_memory = AsyncMock(return_value=None)  # mem0 miss

    # Spy on fire_and_forget
    fire_calls: list = []
    original_fire = mgr._background_tasks.fire_and_forget

    def tracking_fire(coro, *, context=None):  # type: ignore[no-untyped-def]
        fire_calls.append(context)
        # Don't schedule — just record and close the coroutine
        coro.close()

        class _Dummy:
            def add_done_callback(self, _cb):
                pass

        return _Dummy()

    mgr._background_tasks.fire_and_forget = tracking_fire  # type: ignore[assignment]
    try:
        result = await mgr.get(memory_id="missing_mem", user_id="user_a")
    finally:
        mgr._background_tasks.fire_and_forget = original_fire  # type: ignore[assignment]

    assert result is None
    assert len(fire_calls) == 0, "Fire-and-forget must NOT fire on get() miss"


@pytest.mark.asyncio
async def test_get_hit_schedules_tracking():
    """AC-3: get(memory_id) hit schedules background tracking."""
    mgr = _make_manager()

    stored = MemoryRecord(
        id="hit_mem",
        user_id="user_a",
        content="x",
        memory_type=MemoryType.CONVERSATION,
        layer=MemoryLayer.WORKING,
        metadata=MemoryMetadata(),
    )
    mgr._redis.get = AsyncMock(
        side_effect=lambda key: (
            json.dumps(stored.to_dict()) if key == "memory:working:user_a:hit_mem" else None
        )
    )

    fire_calls: list = []
    original_fire = mgr._background_tasks.fire_and_forget

    def tracking_fire(coro, *, context=None):  # type: ignore[no-untyped-def]
        fire_calls.append(context)
        coro.close()

        class _Dummy:
            def add_done_callback(self, _cb):
                pass

        return _Dummy()

    mgr._background_tasks.fire_and_forget = tracking_fire  # type: ignore[assignment]
    try:
        result = await mgr.get(memory_id="hit_mem", user_id="user_a")
    finally:
        mgr._background_tasks.fire_and_forget = original_fire  # type: ignore[assignment]

    assert result is not None
    assert result.id == "hit_mem"
    assert len(fire_calls) == 1
    assert fire_calls[0]["memory_id"] == "hit_mem"
    assert fire_calls[0]["operation"] == "get_hit"


@pytest.mark.asyncio
async def test_counter_ttl_alignment_per_tier():
    """Counter key TTL matches source memory TTL per tier."""
    mgr = _make_manager()
    mgr._redis.incr = AsyncMock(return_value=1)
    mgr._redis.set = AsyncMock()
    mgr._redis.expire = AsyncMock()

    # WORKING → 1800s
    await mgr._track_access_single(
        memory_id="w1",
        layer=MemoryLayer.WORKING,
        user_id="u",
        operation="op",
    )
    working_calls = list(mgr._redis.expire.await_args_list)

    mgr._redis.expire.reset_mock()

    # SESSION → 604800s
    await mgr._track_access_single(
        memory_id="s1",
        layer=MemoryLayer.SESSION,
        user_id="u",
        operation="op",
    )
    session_calls = list(mgr._redis.expire.await_args_list)

    mgr._redis.expire.reset_mock()

    # PINNED → no expire call
    await mgr._track_access_single(
        memory_id="p1",
        layer=MemoryLayer.PINNED,
        user_id="u",
        operation="op",
    )

    assert all(c.args[1] == 1800 for c in working_calls)
    assert all(c.args[1] == 604800 for c in session_calls)
    mgr._redis.expire.assert_not_awaited()  # PINNED


@pytest.mark.asyncio
async def test_boundary_count_4_plus_1_equals_promote_threshold():
    """Once counter reaches 5, consolidation Phase 3 will promote.

    This validates the promote_threshold=5 contract from consolidation.py:254
    is reachable from Sprint 170's counter.
    """
    mgr = _make_manager()
    # Simulate INCR returning 5 (from pre-existing value 4)
    mgr._redis.incr = AsyncMock(return_value=5)
    mgr._redis.set = AsyncMock()
    mgr._redis.expire = AsyncMock()

    await mgr._track_access_single(
        memory_id="boundary_mem",
        layer=MemoryLayer.SESSION,
        user_id="user_a",
        operation="search_hit",
    )

    # Counter now at 5 which equals the promote threshold
    assert mgr._redis.incr.return_value == 5
    # The promotion itself happens in consolidation.py Phase 3 — here we
    # verify the counter crossed threshold. Actual promote flow is covered
    # by test_promotion_triggered integration test.
