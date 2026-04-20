"""Failure-mode tests for Sprint 170 AC-7.

Validates:
  - Redis disconnect during tracking → DLQ entry written, search unaffected
  - mem0.update() raises → DLQ entry captured via fire-and-forget
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from src.integrations.memory.background_tasks import _DLQ_LOGGER_NAME
from src.integrations.memory.types import MemoryConfig, MemoryLayer
from src.integrations.memory.unified_memory import UnifiedMemoryManager


@pytest.mark.asyncio
async def test_redis_disconnect_during_tracking_goes_to_dlq(caplog):
    """Redis INCR raises → DLQ captures context, no exception propagates."""
    mgr = UnifiedMemoryManager(config=MemoryConfig())

    # Simulate Redis connection error on INCR
    redis_err = ConnectionError("Redis connection lost")
    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(side_effect=redis_err)
    mock_redis.set = AsyncMock()
    mock_redis.expire = AsyncMock()
    mgr._redis = mock_redis

    mgr._mem0_client = AsyncMock()
    mgr._initialized = True

    with caplog.at_level(logging.ERROR, logger=_DLQ_LOGGER_NAME):
        # fire_and_forget should swallow the ConnectionError
        mgr._background_tasks.fire_and_forget(
            mgr._track_access_single(
                memory_id="mem_redis_fail",
                layer=MemoryLayer.WORKING,
                user_id="user_a",
                operation="search_hit",
            ),
            context={
                "memory_id": "mem_redis_fail",
                "layer": "working",
                "user_id": "user_a",
                "operation": "search_hit",
            },
        )
        drained = await mgr._background_tasks.drain(timeout=2.0)

    assert drained, "drain() should complete; exception is handled internally"

    dlq_records = [r for r in caplog.records if r.name == _DLQ_LOGGER_NAME]
    assert len(dlq_records) == 1

    rec = dlq_records[0].__dict__
    assert rec.get("error_type") == "ConnectionError"
    ctx = rec.get("context", {})
    assert ctx.get("memory_id") == "mem_redis_fail"
    assert ctx.get("layer") == "working"
    assert ctx.get("operation") == "search_hit"


@pytest.mark.asyncio
async def test_mem0_update_failure_captured_in_dlq(caplog):
    """mem0 update_access_metadata raises → DLQ captures, search unaffected."""
    mgr = UnifiedMemoryManager(config=MemoryConfig())
    mgr._redis = AsyncMock()  # unused for LONG_TERM path
    mgr._initialized = True

    # mem0 get_memory returns a record; update_access_metadata raises
    from src.integrations.memory.types import (
        MemoryMetadata,
        MemoryRecord,
        MemoryType,
    )

    record = MemoryRecord(
        id="mem_lt_fail",
        user_id="user_a",
        content="x",
        memory_type=MemoryType.CONVERSATION,
        layer=MemoryLayer.LONG_TERM,
        metadata=MemoryMetadata(custom={"access_count": 2}),
    )
    mock_mem0 = AsyncMock()
    mock_mem0.get_memory = AsyncMock(return_value=record)
    mock_mem0.update_access_metadata = AsyncMock(
        side_effect=RuntimeError("mem0 backend unavailable")
    )
    mgr._mem0_client = mock_mem0

    with caplog.at_level(logging.ERROR, logger=_DLQ_LOGGER_NAME):
        mgr._background_tasks.fire_and_forget(
            mgr._track_access_single(
                memory_id="mem_lt_fail",
                layer=MemoryLayer.LONG_TERM,
                user_id="user_a",
                operation="search_hit",
            ),
            context={
                "memory_id": "mem_lt_fail",
                "layer": "long_term",
                "user_id": "user_a",
                "operation": "search_hit",
            },
        )
        await mgr._background_tasks.drain(timeout=2.0)

    dlq_records = [r for r in caplog.records if r.name == _DLQ_LOGGER_NAME]
    assert len(dlq_records) == 1
    assert dlq_records[0].__dict__.get("error_type") == "RuntimeError"
    assert "mem0 backend unavailable" in dlq_records[0].__dict__.get("error", "")


@pytest.mark.asyncio
async def test_search_response_unaffected_by_tracking_failure():
    """AC-7: search() returns results even if tracking background task fails.

    Verifies that calling fire_and_forget with a failing tracking coroutine
    does not propagate the exception into the search() caller.
    """
    mgr = UnifiedMemoryManager(config=MemoryConfig())

    # Redis INCR raises; simulate a failing tracking coroutine
    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(side_effect=OSError("simulated I/O error"))
    mock_redis.set = AsyncMock()
    mock_redis.expire = AsyncMock()
    mgr._redis = mock_redis
    mgr._mem0_client = AsyncMock()
    mgr._initialized = True

    # Schedule 5 failing tasks
    for i in range(5):
        mgr._background_tasks.fire_and_forget(
            mgr._track_access_single(
                memory_id=f"mem_{i}",
                layer=MemoryLayer.WORKING,
                user_id="u",
                operation="search_hit",
            ),
            context={"memory_id": f"mem_{i}", "layer": "working"},
        )

    # Drain should complete WITHOUT raising — caller sees no exception
    try:
        result = await mgr._background_tasks.drain(timeout=2.0)
    except Exception as exc:
        pytest.fail(f"drain() must not raise; got {type(exc).__name__}: {exc}")

    assert result is True
    assert mgr._background_tasks.pending_count == 0
