"""Unit tests for MemoryBackgroundTaskManager (Sprint 170).

Validates:
  - Exception in coroutine → DLQ log entry with context
  - Semaphore caps concurrency under burst
  - Strong task references retained until done
  - drain() waits for pending tasks
"""

from __future__ import annotations

import asyncio
import logging

import pytest

from src.integrations.memory.background_tasks import (
    _DLQ_LOGGER_NAME,
    MemoryBackgroundTaskManager,
)


@pytest.mark.asyncio
async def test_exception_writes_to_dead_letter_log(caplog):
    """AC-7: Background task failure writes to memory.background.dlq with context."""
    mgr = MemoryBackgroundTaskManager(max_concurrency=10)

    async def failing_coro() -> None:
        raise RuntimeError("synthetic failure for DLQ test")

    with caplog.at_level(logging.ERROR, logger=_DLQ_LOGGER_NAME):
        mgr.fire_and_forget(
            failing_coro(),
            context={
                "memory_id": "mem_test_123",
                "layer": "working",
                "user_id": "user_xyz",
                "operation": "search_hit",
            },
        )
        await mgr.drain(timeout=2.0)

    dlq_records = [r for r in caplog.records if r.name == _DLQ_LOGGER_NAME]
    assert len(dlq_records) == 1, "Expected exactly one DLQ entry"

    record = dlq_records[0]
    assert record.levelname == "ERROR"
    ctx = record.__dict__.get("context", {})
    assert ctx.get("memory_id") == "mem_test_123"
    assert ctx.get("layer") == "working"
    assert ctx.get("user_id") == "user_xyz"
    assert ctx.get("operation") == "search_hit"
    assert record.__dict__.get("error_type") == "RuntimeError"
    assert "synthetic failure for DLQ test" in record.__dict__.get("error", "")


@pytest.mark.asyncio
async def test_semaphore_caps_concurrency_under_burst():
    """AC-8: Semaphore limits concurrent task execution."""
    max_concurrency = 3
    mgr = MemoryBackgroundTaskManager(max_concurrency=max_concurrency)

    concurrent_counter = {"current": 0, "peak": 0}
    release_event = asyncio.Event()

    async def tracked_coro() -> None:
        concurrent_counter["current"] += 1
        concurrent_counter["peak"] = max(concurrent_counter["peak"], concurrent_counter["current"])
        await release_event.wait()
        concurrent_counter["current"] -= 1

    # Fire 10 tasks; only `max_concurrency` should run concurrently
    for _ in range(10):
        mgr.fire_and_forget(tracked_coro(), context={"burst": "test"})

    # Give event loop a tick to schedule all coroutines
    await asyncio.sleep(0.05)
    assert (
        concurrent_counter["peak"] <= max_concurrency
    ), f"Peak {concurrent_counter['peak']} exceeded cap {max_concurrency}"

    # Release all blocked tasks
    release_event.set()
    await mgr.drain(timeout=5.0)
    assert mgr.pending_count == 0


@pytest.mark.asyncio
async def test_strong_references_retained_until_done():
    """AC-8: Tasks are tracked in _tasks set; not GC-dropped mid-flight."""
    mgr = MemoryBackgroundTaskManager(max_concurrency=10)

    hold_event = asyncio.Event()
    completed_flag = {"done": False}

    async def delayed_coro() -> None:
        await hold_event.wait()
        completed_flag["done"] = True

    task = mgr.fire_and_forget(delayed_coro(), context={"test": "strong_ref"})
    await asyncio.sleep(0.01)  # let scheduler pick up

    # While pending, task must be tracked
    assert mgr.pending_count == 1
    assert task in mgr._tasks  # type: ignore[attr-defined]

    # Release and drain
    hold_event.set()
    await mgr.drain(timeout=2.0)

    assert completed_flag["done"] is True
    assert mgr.pending_count == 0  # cleaned up via done_callback


@pytest.mark.asyncio
async def test_drain_completes_pending_tasks():
    """AC-8: drain() awaits in-flight tasks before returning."""
    mgr = MemoryBackgroundTaskManager(max_concurrency=10)

    finished_ids: list[int] = []

    async def worker(idx: int) -> None:
        await asyncio.sleep(0.02)
        finished_ids.append(idx)

    for i in range(5):
        mgr.fire_and_forget(worker(i), context={"idx": i})

    drained = await mgr.drain(timeout=2.0)

    assert drained is True
    assert sorted(finished_ids) == [0, 1, 2, 3, 4]


@pytest.mark.asyncio
async def test_invalid_concurrency_rejected():
    """Constructor validates max_concurrency >= 1."""
    with pytest.raises(ValueError, match=">= 1"):
        MemoryBackgroundTaskManager(max_concurrency=0)
    with pytest.raises(ValueError, match=">= 1"):
        MemoryBackgroundTaskManager(max_concurrency=-5)
