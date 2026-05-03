"""
File: backend/tests/unit/agent_harness/error_handling/test_budget.py
Purpose: Unit tests for TenantErrorBudget + InMemoryBudgetStore (Cat 8 US-4).
Category: Tests / 範疇 8
Scope: Phase 53.2 / Sprint 53.2

Created: 2026-05-03 (Sprint 53.2 Day 2)
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from agent_harness.error_handling._abc import ErrorClass
from agent_harness.error_handling.budget import (
    InMemoryBudgetStore,
    TenantErrorBudget,
)

# === InMemoryBudgetStore basics =============================================


class TestInMemoryStore:
    @pytest.mark.asyncio
    async def test_first_increment_returns_one(self) -> None:
        store = InMemoryBudgetStore()
        assert await store.increment("k", ttl_seconds=60) == 1

    @pytest.mark.asyncio
    async def test_consecutive_increments_accumulate(self) -> None:
        store = InMemoryBudgetStore()
        for i in range(5):
            assert await store.increment("k", ttl_seconds=60) == i + 1

    @pytest.mark.asyncio
    async def test_get_returns_zero_for_absent_key(self) -> None:
        store = InMemoryBudgetStore()
        assert await store.get("absent") == 0

    @pytest.mark.asyncio
    async def test_concurrent_increments_under_lock(self) -> None:
        store = InMemoryBudgetStore()
        await asyncio.gather(*[store.increment("k", 60) for _ in range(20)])
        assert await store.get("k") == 20


# === TenantErrorBudget.record ==============================================


class TestRecord:
    @pytest.mark.asyncio
    async def test_record_increments_day_and_month(self) -> None:
        store = InMemoryBudgetStore()
        budget = TenantErrorBudget(store, max_per_day=100, max_per_month=1000)
        tid = uuid4()
        await budget.record(tid, ErrorClass.TRANSIENT)

        # Inspect underlying counters via known key shape
        day_key = TenantErrorBudget._day_key(tid)
        month_key = TenantErrorBudget._month_key(tid)
        assert await store.get(day_key) == 1
        assert await store.get(month_key) == 1

    @pytest.mark.asyncio
    async def test_fatal_skipped(self) -> None:
        """FATAL = bug; should NOT consume tenant budget."""
        store = InMemoryBudgetStore()
        budget = TenantErrorBudget(store)
        tid = uuid4()
        await budget.record(tid, ErrorClass.FATAL)
        assert await store.get(TenantErrorBudget._day_key(tid)) == 0
        assert await store.get(TenantErrorBudget._month_key(tid)) == 0

    @pytest.mark.asyncio
    async def test_llm_recoverable_counted(self) -> None:
        store = InMemoryBudgetStore()
        budget = TenantErrorBudget(store)
        tid = uuid4()
        await budget.record(tid, ErrorClass.LLM_RECOVERABLE)
        await budget.record(tid, ErrorClass.HITL_RECOVERABLE)
        assert await store.get(TenantErrorBudget._day_key(tid)) == 2


# === TenantErrorBudget.is_exceeded =========================================


class TestIsExceeded:
    @pytest.mark.asyncio
    async def test_returns_false_when_within_limits(self) -> None:
        store = InMemoryBudgetStore()
        budget = TenantErrorBudget(store, max_per_day=10, max_per_month=100)
        tid = uuid4()
        for _ in range(5):
            await budget.record(tid, ErrorClass.TRANSIENT)
        exceeded, reason = await budget.is_exceeded(tid)
        assert exceeded is False
        assert reason is None

    @pytest.mark.asyncio
    async def test_returns_true_when_daily_limit_hit(self) -> None:
        store = InMemoryBudgetStore()
        budget = TenantErrorBudget(store, max_per_day=3, max_per_month=1000)
        tid = uuid4()
        for _ in range(4):  # 4 > 3 → exceeded
            await budget.record(tid, ErrorClass.TRANSIENT)
        exceeded, reason = await budget.is_exceeded(tid)
        assert exceeded is True
        assert reason is not None
        assert "daily_limit" in reason

    @pytest.mark.asyncio
    async def test_returns_true_when_monthly_limit_hit(self) -> None:
        store = InMemoryBudgetStore()
        # Set day limit higher than the trip count, but month limit lower
        budget = TenantErrorBudget(store, max_per_day=100, max_per_month=2)
        tid = uuid4()
        for _ in range(3):  # 3 > 2 → monthly exceeded
            await budget.record(tid, ErrorClass.TRANSIENT)
        exceeded, reason = await budget.is_exceeded(tid)
        assert exceeded is True
        assert reason is not None
        assert "monthly_limit" in reason


# === multi-tenant isolation ================================================


class TestMultiTenantIsolation:
    @pytest.mark.asyncio
    async def test_tenant_a_exhaust_does_not_affect_tenant_b(self) -> None:
        store = InMemoryBudgetStore()
        budget = TenantErrorBudget(store, max_per_day=2, max_per_month=100)
        tenant_a = uuid4()
        tenant_b = uuid4()
        for _ in range(3):
            await budget.record(tenant_a, ErrorClass.TRANSIENT)

        a_exceeded, _ = await budget.is_exceeded(tenant_a)
        b_exceeded, _ = await budget.is_exceeded(tenant_b)
        assert a_exceeded is True
        assert b_exceeded is False
