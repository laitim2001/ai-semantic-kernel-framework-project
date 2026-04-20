"""Concurrency atomicity test for Sprint 170 AC-1.

Validates that 10 concurrent search() access-tracking calls against the same
memory_id produce counter == 10 (not less — which would indicate race).

This is the critical test that validates the v2 design decision to use
independent INCR counters instead of v1's HINCRBY on hash entries (which
would race against JSON read-modify-write from memory entry updates).
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from src.integrations.memory.types import MemoryConfig, MemoryLayer
from src.integrations.memory.unified_memory import UnifiedMemoryManager


class AtomicRedisCounter:
    """Mimics Redis INCR atomicity using asyncio.Lock.

    If our code used a non-atomic read-modify-write pattern instead of
    INCR, this test would fail because concurrent reads would see stale
    values and overwrite each other's increments.
    """

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}
        self._lock = asyncio.Lock()
        self._sets: dict[str, str] = {}

    async def incr(self, key: str) -> int:
        async with self._lock:
            self._counters[key] = self._counters.get(key, 0) + 1
            return self._counters[key]

    async def set(self, key: str, value: str) -> bool:
        async with self._lock:
            self._sets[key] = value
        return True

    async def expire(self, key: str, _ttl: int) -> bool:
        return True

    async def get(self, key: str):  # type: ignore[no-untyped-def]
        async with self._lock:
            if key in self._counters:
                return str(self._counters[key])
            return self._sets.get(key)


@pytest.mark.asyncio
async def test_ten_concurrent_hits_produce_counter_of_ten():
    """AC-1: 10 concurrent _track_access_single calls → counter == 10."""
    mgr = UnifiedMemoryManager(config=MemoryConfig())
    atomic_redis = AtomicRedisCounter()
    mgr._redis = atomic_redis  # type: ignore[assignment]
    mgr._mem0_client = AsyncMock()
    mgr._initialized = True

    tasks = [
        mgr._track_access_single(
            memory_id="same_mem",
            layer=MemoryLayer.WORKING,
            user_id="user_concurrent",
            operation="search_hit",
        )
        for _ in range(10)
    ]
    await asyncio.gather(*tasks)

    final_value = await atomic_redis.get("memory:counter:working:user_concurrent:same_mem")
    assert final_value is not None
    assert int(final_value) == 10, (
        f"Expected counter=10 after 10 concurrent hits, got {final_value}. "
        f"This indicates a race condition in the tracking code path."
    )


@pytest.mark.asyncio
async def test_fire_and_forget_pipeline_concurrent_burst():
    """End-to-end: fire_and_forget + semaphore under 50-hit burst → counter=50."""
    mgr = UnifiedMemoryManager(config=MemoryConfig())
    atomic_redis = AtomicRedisCounter()
    mgr._redis = atomic_redis  # type: ignore[assignment]
    mgr._mem0_client = AsyncMock()
    mgr._initialized = True

    for _ in range(50):
        mgr._background_tasks.fire_and_forget(
            mgr._track_access_single(
                memory_id="burst_mem",
                layer=MemoryLayer.SESSION,
                user_id="burst_user",
                operation="search_hit",
            ),
            context={"burst": "yes"},
        )

    await mgr._background_tasks.drain(timeout=5.0)

    final_value = await atomic_redis.get("memory:counter:session:burst_user:burst_mem")
    assert int(final_value) == 50
