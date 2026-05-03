"""
File: backend/tests/integration/agent_harness/error_handling/test_redis_budget_store.py
Purpose: Integration tests for RedisBudgetStore using fakeredis (Sprint 53.3 US-8 / AD-Cat8-1).
Category: Tests / Integration / 範疇 8
Scope: Phase 53.3 / Sprint 53.3 Day 4

Description:
    53.2 closeout left RedisBudgetStore at 0% coverage because CI has no
    Redis service. This test file uses fakeredis>=2.20 (added Day 0
    pyproject dev dep) to verify MULTI/EXEC pipeline behavior end-to-end
    without requiring a real Redis cluster.

    fakeredis emulates the redis-py async API faithfully for INCR /
    EXPIRE / TTL / GET / pipeline(transaction=True) — sufficient for
    BudgetStore contract tests.

Created: 2026-05-03 (Sprint 53.3 Day 4 — closes AD-Cat8-1)
"""

from __future__ import annotations

import asyncio

import pytest
from fakeredis.aioredis import FakeRedis

from agent_harness.error_handling._redis_store import RedisBudgetStore


@pytest.fixture
async def fake_redis():  # type: ignore[no-untyped-def]
    """Per-test FakeRedis client (clean state)."""
    client = FakeRedis(decode_responses=False)
    yield client
    await client.aclose()


@pytest.fixture
async def store(fake_redis):  # type: ignore[no-untyped-def]
    return RedisBudgetStore(client=fake_redis)


# === Increment basics =====================================================


@pytest.mark.asyncio
async def test_increment_returns_running_count(store) -> None:  # type: ignore[no-untyped-def]
    """First increment returns 1; second returns 2."""
    assert await store.increment("budget:tenant_a:day:2026-05-03", ttl_seconds=86400) == 1
    assert await store.increment("budget:tenant_a:day:2026-05-03", ttl_seconds=86400) == 2
    assert await store.increment("budget:tenant_a:day:2026-05-03", ttl_seconds=86400) == 3


@pytest.mark.asyncio
async def test_increment_atomicity_concurrent(store) -> None:  # type: ignore[no-untyped-def]
    """100 concurrent increments → final count exactly 100."""
    coros = [store.increment("counter:concurrent", ttl_seconds=60) for _ in range(100)]
    results = await asyncio.gather(*coros)
    # Each should have a unique value (1..100); final get returns 100
    assert sorted(results) == list(range(1, 101))
    assert await store.get("counter:concurrent") == 100


# === Get =================================================================


@pytest.mark.asyncio
async def test_get_returns_zero_for_missing_key(store) -> None:  # type: ignore[no-untyped-def]
    """Per BudgetStore contract: missing key → 0 (not error)."""
    assert await store.get("never_set") == 0


@pytest.mark.asyncio
async def test_get_returns_decoded_int(store) -> None:  # type: ignore[no-untyped-def]
    """redis-py returns bytes; store decodes to int."""
    await store.increment("counter:1", ttl_seconds=60)
    await store.increment("counter:1", ttl_seconds=60)
    assert isinstance(await store.get("counter:1"), int)
    assert await store.get("counter:1") == 2


# === TTL behavior ========================================================


@pytest.mark.asyncio
async def test_ttl_set_on_increment(fake_redis, store) -> None:  # type: ignore[no-untyped-def]
    """EXPIRE lands atomically with INCR via pipeline."""
    await store.increment("counter:ttl", ttl_seconds=120)
    ttl = await fake_redis.ttl(b"counter:ttl")
    # Range: should be slightly less than 120 due to fake-clock granularity
    assert 110 < ttl <= 120


@pytest.mark.asyncio
async def test_ttl_refreshes_on_subsequent_increment(  # type: ignore[no-untyped-def]
    fake_redis, store
) -> None:
    """Each increment refreshes EXPIRE — sliding-window semantics."""
    await store.increment("counter:slide", ttl_seconds=30)
    # If we increment again with longer TTL, the new TTL should win
    await store.increment("counter:slide", ttl_seconds=300)
    ttl = await fake_redis.ttl(b"counter:slide")
    assert ttl > 100  # well above original 30


# === Multi-tenant key isolation ==========================================


@pytest.mark.asyncio
async def test_multi_tenant_keys_isolated(store) -> None:  # type: ignore[no-untyped-def]
    """Increments to tenant_a's key don't affect tenant_b's count."""
    for _ in range(5):
        await store.increment("budget:tenant_a:day", ttl_seconds=60)
    for _ in range(3):
        await store.increment("budget:tenant_b:day", ttl_seconds=60)

    assert await store.get("budget:tenant_a:day") == 5
    assert await store.get("budget:tenant_b:day") == 3
    # Cross-checks: each tenant unaffected by the other's writes
    assert await store.get("budget:tenant_a:day") + await store.get("budget:tenant_b:day") == 8


# === Pipeline transaction semantics ======================================


@pytest.mark.asyncio
async def test_pipeline_returns_first_result_as_running_count(  # type: ignore[no-untyped-def]
    store,
) -> None:
    """RedisBudgetStore.increment returns INCR's result (not EXPIRE's bool)."""
    n1 = await store.increment("p1", ttl_seconds=10)
    n2 = await store.increment("p1", ttl_seconds=10)
    assert (n1, n2) == (1, 2)


# === Mixed scenario =======================================================


@pytest.mark.asyncio
async def test_full_budget_workflow(store) -> None:  # type: ignore[no-untyped-def]
    """Realistic: error budget for a tenant accumulates over the day,
    each call records the current count, get() reads aggregate.
    """
    key = "budget:tenant_xyz:day:2026-05-03"
    seen: list[int] = []
    for _ in range(10):
        seen.append(await store.increment(key, ttl_seconds=86400))
    assert seen == list(range(1, 11))
    assert await store.get(key) == 10
