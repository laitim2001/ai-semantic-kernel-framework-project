"""SLAMetricRecorder + classify_loop_complexity tests (Sprint 56.3 Day 1 / US-1)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import pytest
from fakeredis.aioredis import FakeRedis

from platform_layer.observability.sla_monitor import (
    WINDOW_SEC,
    SLAMetricRecorder,
    classify_loop_complexity,
)


# Lightweight LoopCompleted stand-in (mirrors the 3 fields the classifier reads;
# avoids importing the full agent_harness chain in a unit test).
@dataclass
class _LoopCompletedStub:
    total_turns: int = 0
    total_tokens: int = 0


@pytest.fixture
async def fake_redis():  # type: ignore[no-untyped-def]
    client = FakeRedis(decode_responses=False)
    yield client
    await client.aclose()


@pytest.fixture
async def recorder(fake_redis):  # type: ignore[no-untyped-def]
    return SLAMetricRecorder(redis_client=fake_redis)


@pytest.mark.asyncio
async def test_record_loop_completion_writes_to_redis_sliding_window(
    recorder: SLAMetricRecorder,
    fake_redis: FakeRedis,
) -> None:
    """ZADD into sla:metrics:{tenant}:loop_simple:300s key; latency_ms = score."""
    tenant_id = uuid4()
    await recorder.record_loop_completion(
        tenant_id=tenant_id,
        latency_ms=4_200,
        complexity_category="simple",
    )
    key = f"sla:metrics:{tenant_id}:loop_simple:{WINDOW_SEC}s"
    # Read back: ZRANGE WITHSCORES returns one entry; score should equal latency_ms.
    entries = await fake_redis.zrange(key, 0, -1, withscores=True)
    assert len(entries) == 1
    _member, score = entries[0]
    assert score == 4_200.0


@pytest.mark.asyncio
async def test_get_loop_p99_returns_99th_percentile(
    recorder: SLAMetricRecorder,
) -> None:
    """Populate 100 entries; assert p99 returns the 99th-sorted latency."""
    tenant_id = uuid4()
    # Seed latencies 1..100 ms — sorted, p99 should be 99 ms.
    for latency in range(1, 101):
        await recorder.record_loop_completion(
            tenant_id=tenant_id,
            latency_ms=latency,
            complexity_category="medium",
        )
    p99 = await recorder.get_loop_p99(tenant_id, "medium")
    # p99 index = max(int(100 * 0.99) - 1, 0) = 98 → sorted[98] = 99
    assert p99 == 99.0


@pytest.mark.asyncio
async def test_classify_loop_complexity_simple() -> None:
    """≤ 3 turns + < 4K tokens → simple."""
    event = _LoopCompletedStub(total_turns=3, total_tokens=2_500)
    assert classify_loop_complexity(event) == "simple"  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_classify_loop_complexity_medium() -> None:
    """4-10 turns → medium (regardless of tokens unless ≥ 4K threshold)."""
    event = _LoopCompletedStub(total_turns=7, total_tokens=3_000)
    assert classify_loop_complexity(event) == "medium"  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_classify_loop_complexity_complex_fallback() -> None:
    """> 10 turns OR ≥ 4K tokens OR negative-fallback → complex."""
    # Path 1: > 10 turns
    e1 = _LoopCompletedStub(total_turns=12, total_tokens=1_000)
    assert classify_loop_complexity(e1) == "complex"  # type: ignore[arg-type]
    # Path 2: ≥ 4K tokens
    e2 = _LoopCompletedStub(total_turns=2, total_tokens=4_500)
    assert classify_loop_complexity(e2) == "complex"  # type: ignore[arg-type]
    # Path 3: negative / off-spec → conservative complex
    e3 = _LoopCompletedStub(total_turns=-1, total_tokens=0)
    assert classify_loop_complexity(e3) == "complex"  # type: ignore[arg-type]
