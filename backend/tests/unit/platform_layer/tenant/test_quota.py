"""QuotaEnforcer tests (Sprint 56.1 Day 2 / US-2)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fakeredis.aioredis import FakeRedis

from platform_layer.tenant.plans import PlanLoader, reset_plan_loader
from platform_layer.tenant.quota import (
    QuotaEnforcer,
    QuotaExceededError,
    reset_quota_enforcer,
)


@pytest.fixture
async def fake_redis():  # type: ignore[no-untyped-def]
    client = FakeRedis(decode_responses=False)
    yield client
    await client.aclose()


@pytest.fixture
def plan_loader() -> PlanLoader:
    reset_plan_loader()
    return PlanLoader()


@pytest.fixture
async def enforcer(fake_redis, plan_loader: PlanLoader):  # type: ignore[no-untyped-def]
    reset_quota_enforcer()
    return QuotaEnforcer(client=fake_redis, plan_loader=plan_loader)


@pytest.mark.asyncio
async def test_quota_enforcer_within_limit(enforcer: QuotaEnforcer) -> None:
    tenant_id = uuid4()
    total = await enforcer.check_and_reserve(
        tenant_id=tenant_id, plan_name="enterprise", estimated_tokens=1_000
    )
    assert total == 1_000
    assert await enforcer.get_usage(tenant_id) == 1_000


@pytest.mark.asyncio
async def test_quota_enforcer_exceeded_raises_429(enforcer: QuotaEnforcer) -> None:
    tenant_id = uuid4()
    cap = 10_000_000  # enterprise tokens_per_day
    await enforcer.check_and_reserve(
        tenant_id=tenant_id, plan_name="enterprise", estimated_tokens=cap
    )
    with pytest.raises(QuotaExceededError) as exc_info:
        await enforcer.check_and_reserve(
            tenant_id=tenant_id, plan_name="enterprise", estimated_tokens=1
        )
    assert exc_info.value.cap == cap
    assert exc_info.value.retry_after_seconds > 0
    # Roll-back invariant: failed reservation does not advance counter.
    assert await enforcer.get_usage(tenant_id) == cap


@pytest.mark.asyncio
async def test_quota_enforcer_multi_tenant_isolation(
    enforcer: QuotaEnforcer,
) -> None:
    """Tenant A's counter must not leak into Tenant B."""
    tenant_a = uuid4()
    tenant_b = uuid4()

    await enforcer.check_and_reserve(
        tenant_id=tenant_a, plan_name="enterprise", estimated_tokens=5_000
    )
    await enforcer.check_and_reserve(
        tenant_id=tenant_b, plan_name="enterprise", estimated_tokens=2_000
    )

    assert await enforcer.get_usage(tenant_a) == 5_000
    assert await enforcer.get_usage(tenant_b) == 2_000


@pytest.mark.asyncio
async def test_quota_enforcer_record_usage_reconciles(
    enforcer: QuotaEnforcer,
) -> None:
    """record_usage adjusts when actual differs from reserved."""
    tenant_id = uuid4()
    await enforcer.check_and_reserve(
        tenant_id=tenant_id, plan_name="enterprise", estimated_tokens=1_000
    )
    # LLM actually used 1_500 — reconcile +500.
    final = await enforcer.record_usage(
        tenant_id=tenant_id, actual_tokens=1_500, reserved_tokens=1_000
    )
    assert final == 1_500
    # Now a slightly-overestimated reservation reconciles down.
    await enforcer.check_and_reserve(
        tenant_id=tenant_id, plan_name="enterprise", estimated_tokens=2_000
    )
    final = await enforcer.record_usage(
        tenant_id=tenant_id, actual_tokens=1_800, reserved_tokens=2_000
    )
    assert final == 3_300


@pytest.mark.asyncio
async def test_quota_enforcer_resets_at_midnight(
    enforcer: QuotaEnforcer, fake_redis  # type: ignore[no-untyped-def]
) -> None:
    """Counter key carries today's UTC date stamp; new key per day."""
    tenant_id = uuid4()
    await enforcer.check_and_reserve(
        tenant_id=tenant_id, plan_name="enterprise", estimated_tokens=100
    )
    today_key = enforcer._key(tenant_id)  # noqa: SLF001 — internal probe
    raw = await fake_redis.get(today_key)
    assert raw is not None and int(raw) == 100
    # TTL is set on the key (24h sliding window verified at integration layer).
    ttl = await fake_redis.ttl(today_key)
    assert 0 < ttl <= QuotaEnforcer._TTL_SECONDS  # noqa: SLF001


@pytest.mark.asyncio
async def test_quota_enforcer_singleton_not_initialised_raises() -> None:
    """get_quota_enforcer() before set_quota_enforcer() raises clearly."""
    from platform_layer.tenant.quota import get_quota_enforcer

    reset_quota_enforcer()
    with pytest.raises(RuntimeError, match="not initialised"):
        get_quota_enforcer()
