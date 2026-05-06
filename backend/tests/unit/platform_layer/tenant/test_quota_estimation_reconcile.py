"""
File: backend/tests/unit/platform_layer/tenant/test_quota_estimation_reconcile.py
Purpose: Unit tests — QuotaEnforcer.estimate_pre_call_tokens (US-2) + record_usage (US-3 reuse).
Category: Tests / Platform / Tenant Quota
Scope: Sprint 56.2 / Day 2 / US-2 (closes AD-QuotaEstimation-1) + US-3 (closes AD-QuotaPostCall-1)
"""

from __future__ import annotations

import pytest
from fakeredis import FakeAsyncRedis

from platform_layer.tenant.plans import PlanLoader
from platform_layer.tenant.quota import QuotaEnforcer


@pytest.fixture
def loader() -> PlanLoader:
    return PlanLoader()


@pytest.fixture
async def enforcer(loader: PlanLoader) -> QuotaEnforcer:
    client = FakeAsyncRedis()
    return QuotaEnforcer(client=client, plan_loader=loader)


class TestEstimatePreCallTokens:
    """US-2 — heuristic pre-call estimate replaces fixed 1000-token reservation."""

    def test_short_message_clamped_to_floor_100(self, enforcer: QuotaEnforcer) -> None:
        # 16 chars / 4 = 4 tokens, clamped to floor 100.
        result = enforcer.estimate_pre_call_tokens("Hello world test", fallback=1000)
        assert result == 100

    def test_medium_message_returns_heuristic(self, enforcer: QuotaEnforcer) -> None:
        # 800 chars / 4 = 200 tokens (within [100, 1000]).
        msg = "x" * 800
        result = enforcer.estimate_pre_call_tokens(msg, fallback=1000)
        assert result == 200

    def test_long_message_clamped_to_fallback_ceiling(self, enforcer: QuotaEnforcer) -> None:
        # 8000 chars / 4 = 2000 tokens, clamped to fallback 1000.
        msg = "x" * 8000
        result = enforcer.estimate_pre_call_tokens(msg, fallback=1000)
        assert result == 1000

    def test_empty_message_returns_floor(self, enforcer: QuotaEnforcer) -> None:
        result = enforcer.estimate_pre_call_tokens("", fallback=1000)
        assert result == 100


class TestRecordUsageReconciliation:
    """US-3 — record_usage reconciles reservation vs actual; existing 56.1 method."""

    @pytest.mark.asyncio
    async def test_actual_under_reserved_releases_diff(self, enforcer: QuotaEnforcer) -> None:
        from uuid import uuid4

        tenant_id = uuid4()
        # Reserve 500.
        await enforcer.check_and_reserve(
            tenant_id=tenant_id, plan_name="enterprise", estimated_tokens=500
        )
        assert await enforcer.get_usage(tenant_id) == 500

        # Actual 350 → release 150.
        new_total = await enforcer.record_usage(
            tenant_id=tenant_id, actual_tokens=350, reserved_tokens=500
        )
        assert new_total == 350

    @pytest.mark.asyncio
    async def test_actual_equals_reserved_no_op(self, enforcer: QuotaEnforcer) -> None:
        from uuid import uuid4

        tenant_id = uuid4()
        await enforcer.check_and_reserve(
            tenant_id=tenant_id, plan_name="enterprise", estimated_tokens=200
        )
        new_total = await enforcer.record_usage(
            tenant_id=tenant_id, actual_tokens=200, reserved_tokens=200
        )
        assert new_total == 200

    @pytest.mark.asyncio
    async def test_actual_over_reserved_increments_diff(self, enforcer: QuotaEnforcer) -> None:
        from uuid import uuid4

        tenant_id = uuid4()
        await enforcer.check_and_reserve(
            tenant_id=tenant_id, plan_name="enterprise", estimated_tokens=100
        )
        # Estimate too low — actual 250. record_usage adds the 150 diff.
        new_total = await enforcer.record_usage(
            tenant_id=tenant_id, actual_tokens=250, reserved_tokens=100
        )
        assert new_total == 250
