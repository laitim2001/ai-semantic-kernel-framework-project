"""
File: backend/src/agent_harness/error_handling/budget.py
Purpose: Per-tenant ErrorBudget — daily / monthly counters with TTL.
Category: 範疇 8 (Error Handling)
Scope: Phase 53.2 / Sprint 53.2

Description:
    Multi-tenant error budget enforcement (per `multi-tenant-data.md`):

      - record(tenant_id, error_class) increments per-tenant per-day
        and per-month counters in a `BudgetStore` (Redis in prod;
        in-memory mock in tests).
      - is_exceeded(tenant_id) returns (True, reason) when either
        counter exceeds its cap. ErrorTerminator (US-5) consults this
        to decide whether to terminate the loop with reason
        BUDGET_EXCEEDED.

    Why per-tenant?
      - Prevents a single runaway tenant from consuming shared
        infrastructure budget (LLM cost / outbound API quota / etc).
      - YAML-tunable per-tenant overrides (`backend/config/error_budgets.yaml`).
      - Hard caps protect platform during incident; soft caps surface
        via observability.

    Why skip UNEXPECTED in counters?
      - UNEXPECTED = bug. Counting bugs against tenant's budget would
        punish them for our defect. Bugs flow to alerting (range 12)
        not budget enforcement.

Key Components:
    - BudgetStore: Protocol — increment / get / TTL-aware
    - InMemoryBudgetStore: thread-safe dict for tests + dev mode
    - TenantErrorBudget: orchestrator over a BudgetStore

Owner: 01-eleven-categories-spec.md §Cat 8 + multi-tenant-data.md
Created: 2026-05-03 (Sprint 53.2 Day 2)

Modification History (newest-first):
    - 2026-05-03: Initial creation (Sprint 53.2 Day 2) — US-4 production impl
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID

from agent_harness.error_handling._abc import ErrorClass


class BudgetStore(Protocol):
    """Storage backend for per-tenant counters.

    Implementations:
      - InMemoryBudgetStore (this file): tests + dev mode
      - RedisBudgetStore (_redis_store.py): production
    """

    async def increment(self, key: str, ttl_seconds: int) -> int:
        """Atomically INCR `key` and (re)SET TTL. Return new value."""
        ...

    async def get(self, key: str) -> int:
        """Return counter or 0 if absent / expired."""
        ...


class InMemoryBudgetStore:
    """Thread-safe in-memory store with explicit TTL handling.

    Not for production (state lost on restart, no cross-process sharing).
    Used by tests and `dev` mode where Redis is unavailable.
    """

    def __init__(self) -> None:
        self._data: dict[str, tuple[int, datetime]] = {}
        self._lock = asyncio.Lock()

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _is_expired(self, expiry: datetime) -> bool:
        return self._now() >= expiry

    async def increment(self, key: str, ttl_seconds: int) -> int:
        async with self._lock:
            now = self._now()
            current = self._data.get(key)
            if current is None or self._is_expired(current[1]):
                count = 1
            else:
                count = current[0] + 1
            from datetime import timedelta

            expiry = now + timedelta(seconds=ttl_seconds)
            self._data[key] = (count, expiry)
            return count

    async def get(self, key: str) -> int:
        async with self._lock:
            current = self._data.get(key)
            if current is None or self._is_expired(current[1]):
                return 0
            return current[0]


class TenantErrorBudget:
    """Records errors per-tenant and reports budget exceeded state.

    Daily counter: TTL ~ 2 days (covers UTC day boundary slack).
    Monthly counter: TTL ~ 32 days (covers month boundary slack).

    Usage::

        budget = TenantErrorBudget(InMemoryBudgetStore(), max_per_day=1000)
        await budget.record(tenant_id, ErrorClass.TRANSIENT)
        exceeded, reason = await budget.is_exceeded(tenant_id)
        if exceeded:
            ...  # ErrorTerminator (US-5) consumes this.
    """

    DAILY_TTL_SECONDS = 86400 * 2  # 48h headroom
    MONTHLY_TTL_SECONDS = 86400 * 32  # 32d headroom

    def __init__(
        self,
        store: BudgetStore,
        *,
        max_per_day: int = 1000,
        max_per_month: int = 20000,
    ) -> None:
        self._store = store
        self._max_per_day = max_per_day
        self._max_per_month = max_per_month

    @staticmethod
    def _day_key(tenant_id: UUID) -> str:
        date = datetime.now(timezone.utc).date().isoformat()
        return f"error_budget:{tenant_id}:day:{date}"

    @staticmethod
    def _month_key(tenant_id: UUID) -> str:
        ym = datetime.now(timezone.utc).strftime("%Y-%m")
        return f"error_budget:{tenant_id}:month:{ym}"

    async def record(self, tenant_id: UUID, error_class: ErrorClass) -> None:
        """Increment daily + monthly counters for the tenant.

        UNEXPECTED is a bug, not a tenant-attributable error — skip.
        """
        if error_class == ErrorClass.FATAL:
            # FATAL covers our "bug" / unrecognized exception bucket.
            return
        await self._store.increment(self._day_key(tenant_id), self.DAILY_TTL_SECONDS)
        await self._store.increment(self._month_key(tenant_id), self.MONTHLY_TTL_SECONDS)

    async def is_exceeded(self, tenant_id: UUID) -> tuple[bool, str | None]:
        day_count = await self._store.get(self._day_key(tenant_id))
        if day_count > self._max_per_day:
            return True, f"daily_limit ({day_count}/{self._max_per_day})"
        month_count = await self._store.get(self._month_key(tenant_id))
        if month_count > self._max_per_month:
            return True, f"monthly_limit ({month_count}/{self._max_per_month})"
        return False, None
