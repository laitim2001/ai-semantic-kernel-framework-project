"""Unit tests for access tracking across memory tiers (Sprint 170 AC-1 / AC-2).

Validates:
  - PINNED tier: INCR fires, no TTL applied
  - WORKING tier: INCR fires + TTL aligned to 30min (1800s)
  - SESSION tier: INCR fires + TTL aligned to 7d (604800s)
  - LONG_TERM tier: mem0.update_access_metadata called via thread executor
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.integrations.memory.types import (
    MemoryConfig,
    MemoryLayer,
    MemoryMetadata,
    MemoryRecord,
    MemoryType,
)
from src.integrations.memory.unified_memory import UnifiedMemoryManager


def _make_manager_with_mocks() -> UnifiedMemoryManager:
    """Construct manager with stubbed Redis + mem0 for pure-logic tests."""
    config = MemoryConfig()
    mgr = UnifiedMemoryManager(config=config)

    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(return_value=1)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.expire = AsyncMock(return_value=True)
    mgr._redis = mock_redis

    mock_mem0 = AsyncMock()
    mgr._mem0_client = mock_mem0

    mgr._initialized = True
    return mgr


@pytest.mark.asyncio
async def test_pinned_tier_increments_counter_without_ttl():
    """PINNED: INCR + SET fired, expire NOT called (no TTL)."""
    mgr = _make_manager_with_mocks()

    await mgr._track_access_single(
        memory_id="mem_pin_1",
        layer=MemoryLayer.PINNED,
        user_id="user_a",
        operation="search_hit",
    )

    mgr._redis.incr.assert_awaited_once_with("memory:counter:pinned:user_a:mem_pin_1")
    mgr._redis.set.assert_awaited_once()
    # PINNED has no TTL — expire should NOT be called
    mgr._redis.expire.assert_not_awaited()


@pytest.mark.asyncio
async def test_working_tier_applies_30min_ttl():
    """WORKING: TTL aligned to config.working_memory_ttl (1800s default)."""
    mgr = _make_manager_with_mocks()

    await mgr._track_access_single(
        memory_id="mem_work_1",
        layer=MemoryLayer.WORKING,
        user_id="user_a",
        operation="search_hit",
    )

    expected_ttl = mgr.config.working_memory_ttl
    assert expected_ttl == 1800  # default from types.py

    expire_calls = mgr._redis.expire.await_args_list
    assert len(expire_calls) == 2  # counter key + accessed_at key
    for call in expire_calls:
        assert call.args[1] == expected_ttl


@pytest.mark.asyncio
async def test_session_tier_applies_7day_ttl():
    """SESSION: TTL aligned to config.session_memory_ttl (604800s default)."""
    mgr = _make_manager_with_mocks()

    await mgr._track_access_single(
        memory_id="mem_sess_1",
        layer=MemoryLayer.SESSION,
        user_id="user_a",
        operation="search_hit",
    )

    expected_ttl = mgr.config.session_memory_ttl
    assert expected_ttl == 604800

    mgr._redis.incr.assert_awaited_once_with("memory:counter:session:user_a:mem_sess_1")
    expire_calls = mgr._redis.expire.await_args_list
    assert all(call.args[1] == expected_ttl for call in expire_calls)


@pytest.mark.asyncio
async def test_long_term_tier_calls_mem0_update_metadata():
    """LONG_TERM: mem0.update_access_metadata invoked (not Redis INCR)."""
    mgr = _make_manager_with_mocks()

    # Stub mem0.get_memory to return a record with current access_count=3
    existing_record = MemoryRecord(
        id="mem_lt_1",
        user_id="user_a",
        content="fixture",
        memory_type=MemoryType.SYSTEM_KNOWLEDGE,
        layer=MemoryLayer.LONG_TERM,
        metadata=MemoryMetadata(custom={"access_count": 3}),
    )
    mgr._mem0_client.get_memory = AsyncMock(return_value=existing_record)
    mgr._mem0_client.update_access_metadata = AsyncMock(return_value=True)

    await mgr._track_access_single(
        memory_id="mem_lt_1",
        layer=MemoryLayer.LONG_TERM,
        user_id="user_a",
        operation="search_hit",
    )

    # Redis INCR must NOT fire for LONG_TERM
    mgr._redis.incr.assert_not_awaited()

    # mem0 update should be called with count=4 (existing 3 + 1)
    mgr._mem0_client.update_access_metadata.assert_awaited_once()
    call_args = mgr._mem0_client.update_access_metadata.await_args
    assert call_args.args[0] == "mem_lt_1"
    assert call_args.args[1] == 4  # 3 + 1
    assert isinstance(call_args.args[2], datetime)


@pytest.mark.asyncio
async def test_structured_log_emitted(caplog):
    """AC-9: memory_access_tracked log event fires with required fields."""
    import logging

    mgr = _make_manager_with_mocks()

    with caplog.at_level(logging.INFO):
        await mgr._track_access_single(
            memory_id="mem_log_1",
            layer=MemoryLayer.WORKING,
            user_id="user_log",
            operation="get_hit",
        )

    access_logs = [r for r in caplog.records if r.__dict__.get("event") == "memory_access_tracked"]
    assert len(access_logs) == 1

    rec = access_logs[0].__dict__
    assert rec.get("memory_id") == "mem_log_1"
    assert rec.get("layer") == "working"
    assert rec.get("tenant_id") == "user_log"
    assert rec.get("operation") == "get_hit"
    assert "ts" in rec
    assert rec.get("new_count") == 1
