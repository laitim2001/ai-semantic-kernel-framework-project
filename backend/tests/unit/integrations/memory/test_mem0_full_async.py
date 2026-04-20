"""Sprint 172 mem0 full async wrapping tests (AC-6 / AC-7 / AC-8).

Validates:
  - All sync SDK calls routed through the shared ThreadPoolExecutor
  - Reads (search/get/get_all) do NOT acquire the mutation lock
  - Mutations (add/update/delete) acquire the lock
  - Lock timeout raises ``Mem0LockTimeout``
  - ``close()`` cleanly shuts down the executor
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock

import pytest

from src.integrations.memory.mem0_client import Mem0Client, Mem0LockTimeout
from src.integrations.memory.types import MemoryConfig, MemorySearchQuery


def _make_client() -> Mem0Client:
    client = Mem0Client(config=MemoryConfig())
    client._memory = MagicMock()  # stand-in for mem0.Memory — sync calls only
    client._initialized = True
    return client


@pytest.mark.asyncio
async def test_run_read_uses_executor_no_lock():
    """AC-8: _run_read invokes sync fn via executor without locking."""
    client = _make_client()
    expected = {"ok": True}

    def sync_op(**kwargs):
        # Sleep briefly to verify we're not blocking the event loop
        time.sleep(0.01)
        return expected

    result = await client._run_read(sync_op, foo=1, bar=2)
    assert result == expected
    # Mutation lock must remain unlocked (no acquire happened)
    assert client._mutation_lock is not None
    assert not client._mutation_lock.locked()
    await client.close()


@pytest.mark.asyncio
async def test_run_mutate_acquires_lock():
    """AC-8: _run_mutate serialises concurrent mutations."""
    client = _make_client()
    client.config.mem0_mutation_lock_timeout = 5.0  # generous

    concurrency_counter = {"current": 0, "peak": 0}

    def sync_op(**_kwargs):
        concurrency_counter["current"] += 1
        concurrency_counter["peak"] = max(
            concurrency_counter["peak"], concurrency_counter["current"]
        )
        time.sleep(0.03)  # simulate I/O so races can happen
        concurrency_counter["current"] -= 1
        return True

    # 5 concurrent mutations — with lock, peak must be <= 1
    await asyncio.gather(*(client._run_mutate(sync_op) for _ in range(5)))

    assert concurrency_counter["peak"] <= 1
    await client.close()


@pytest.mark.asyncio
async def test_run_mutate_timeout_raises_mem0_lock_timeout():
    """AC-8 / v2 HIGH: mutation timeout converts to Mem0LockTimeout."""
    client = _make_client()
    client.config.mem0_mutation_lock_timeout = 0.05  # 50ms — tight

    # Priming call holds the lock for 0.2s
    async def hold_lock():
        def slow_sync(**_kwargs):
            time.sleep(0.2)
            return None

        await client._run_mutate(slow_sync)

    prime_task = asyncio.create_task(hold_lock())
    # Give primer time to acquire the lock
    await asyncio.sleep(0.02)

    # This second mutation should hit the 50ms timeout and raise
    def second_op(**_kwargs):
        return None

    with pytest.raises(Mem0LockTimeout, match="5"):
        await client._run_mutate(second_op)

    # Wait for primer to complete so executor can shut down cleanly
    await prime_task
    await client.close()


@pytest.mark.asyncio
async def test_reads_run_in_parallel():
    """AC-8: reads do not block each other — concurrent time ~= max op time."""
    client = _make_client()

    def slow_read(**_kwargs):
        time.sleep(0.05)
        return "ok"

    t0 = time.perf_counter()
    # 4 concurrent reads; serial would be 200ms, parallel ~= 50-60ms
    await asyncio.gather(*(client._run_read(slow_read) for _ in range(4)))
    elapsed = time.perf_counter() - t0

    # Allow generous margin for Windows thread-pool overhead
    assert elapsed < 0.15, f"Reads appear serialised: elapsed={elapsed:.3f}s"
    await client.close()


@pytest.mark.asyncio
async def test_search_memory_uses_run_read_path():
    """AC-6: search_memory routes through the executor helper."""
    client = _make_client()
    # Stub mem0 search to return empty list
    client._memory.search = MagicMock(return_value=[])

    query = MemorySearchQuery(query="hello", user_id="u", limit=5)
    results = await client.search_memory(query)

    assert results == []
    client._memory.search.assert_called_once()
    # After completion the lock should never have been acquired for a read
    assert not client._mutation_lock.locked()
    await client.close()


@pytest.mark.asyncio
async def test_close_shuts_down_executor():
    """Close idempotently releases the executor and lock."""
    client = _make_client()
    # Warm up the lazy executor
    await client._run_read(lambda: True)
    assert client._executor is not None

    await client.close()
    # After close, both resources cleared
    assert client._executor is None
    assert client._mutation_lock is None


@pytest.mark.asyncio
async def test_update_access_metadata_still_works_after_refactor():
    """Sprint 170 metadata helper must keep working via the new _run_mutate."""
    from datetime import datetime, timezone

    client = _make_client()
    client._memory.update = MagicMock(return_value=True)

    ok = await client.update_access_metadata(
        memory_id="mem_a",
        count=7,
        accessed_at=datetime.now(timezone.utc),
    )

    assert ok is True
    client._memory.update.assert_called_once()
    kwargs = client._memory.update.call_args.kwargs
    assert kwargs["memory_id"] == "mem_a"
    assert kwargs["metadata"]["access_count"] == 7
    await client.close()
