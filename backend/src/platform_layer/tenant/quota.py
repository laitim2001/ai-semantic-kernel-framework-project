"""
File: backend/src/platform_layer/tenant/quota.py
Purpose: QuotaEnforcer — per-tenant daily token cap with atomic Redis counter.
Category: Phase 56 SaaS Stage 1 (platform_layer.tenant)
Scope: Sprint 56.1 / Day 2 / US-2 Plan Template Enforcement

Description:
    Enforces `tokens_per_day` cap from PlanLoader on every chat call.
    Pattern mirrors 53.2 RedisBudgetStore (Cat 8 ErrorBudget) — atomic
    INCR + EXPIRE via MULTI/EXEC pipeline so concurrent callers cannot
    race-condition past the cap.

    Key shape: `quota:tokens:{tenant_id}:{YYYY-MM-DD}` (UTC date stamp).
    TTL = 24 h on first INCR; subsequent INCRs leave TTL alone unless the
    key was already evicted (cold-start). Day 2 ships with `check_and_reserve`
    (pre-LLM probe) + `record_usage` (post-LLM commit). Both atomic.

    Multi-tenant isolation: tenant_id is part of the key — Redis cannot
    cross-tenant leak counters. Per-tenant Plan resolves quota cap at
    enforce time so plan upgrades propagate without restart.

    Pattern: caller injects `redis.asyncio.Redis` (this module owns no
    connection lifecycle — same as RedisBudgetStore per 53.2 D-finding).

Key Components:
    - QuotaExceededError: raised on cap breach; carries retry_after_seconds
    - QuotaEnforcer: probe + commit + reset helpers
    - get_quota_enforcer / reset_quota_enforcer: FastAPI Depends + tests hook

Modification History (newest-first):
    - 2026-05-06: Initial creation (Sprint 56.1 Day 2 / US-2)

Related:
    - sprint-56-1-plan.md §US-2 Plan Template Enforcement
    - 53.2 RedisBudgetStore at agent_harness/error_handling/_redis_store.py
    - plans.py — provides PlanQuota.tokens_per_day cap
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, cast
from uuid import UUID

from platform_layer.tenant.plans import PlanLoader, get_plan_loader

if TYPE_CHECKING:
    from redis.asyncio import Redis


class QuotaExceededError(Exception):
    """Raised when a tenant's daily token quota would be exceeded.

    `retry_after_seconds` is the seconds remaining until the next UTC
    midnight; FastAPI handler should surface as `Retry-After` header on
    the 429 response.
    """

    def __init__(
        self,
        tenant_id: UUID,
        used: int,
        cap: int,
        retry_after_seconds: int,
    ) -> None:
        self.tenant_id = tenant_id
        self.used = used
        self.cap = cap
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            f"tenant {tenant_id} daily token quota exceeded: "
            f"used={used} cap={cap}; retry_after={retry_after_seconds}s"
        )


class QuotaEnforcer:
    """Per-tenant daily quota gate backed by Redis INCR/EXPIRE pipeline."""

    _TTL_SECONDS = 24 * 3600  # 24 h sliding TTL

    def __init__(
        self,
        client: "Redis[bytes]",  # type: ignore[type-arg, unused-ignore]
        plan_loader: PlanLoader | None = None,
    ) -> None:
        self._client = client
        self._plan_loader = plan_loader or get_plan_loader()

    @staticmethod
    def _today_utc() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    @staticmethod
    def _seconds_until_midnight_utc() -> int:
        now = datetime.now(timezone.utc)
        # Truncate to start of next UTC day.
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() + 86400
        return max(1, int(tomorrow - now.timestamp()))

    def _key(self, tenant_id: UUID) -> str:
        return f"quota:tokens:{tenant_id}:{self._today_utc()}"

    async def _resolve_cap(self, plan_name: str) -> int:
        plan = self._plan_loader.get_plan(plan_name)
        return plan.quota.tokens_per_day

    async def check_and_reserve(
        self,
        *,
        tenant_id: UUID,
        plan_name: str,
        estimated_tokens: int,
    ) -> int:
        """Atomically reserve `estimated_tokens` against today's counter.

        Returns the post-reservation total. Raises `QuotaExceededError`
        if the reservation would breach the cap (counter is rolled back
        when this happens, preserving accuracy for honest callers).
        """
        cap = await self._resolve_cap(plan_name)
        key = self._key(tenant_id)
        async with self._client.pipeline(transaction=True) as pipe:
            pipe.incrby(key, estimated_tokens)
            pipe.expire(key, self._TTL_SECONDS)
            results = await pipe.execute()
        new_total = cast(int, results[0])
        if new_total > cap:
            # Roll back so subsequent (smaller) requests still see honest count.
            await self._client.decrby(key, estimated_tokens)
            raise QuotaExceededError(
                tenant_id=tenant_id,
                used=new_total - estimated_tokens,
                cap=cap,
                retry_after_seconds=self._seconds_until_midnight_utc(),
            )
        return new_total

    async def record_usage(
        self,
        *,
        tenant_id: UUID,
        actual_tokens: int,
        reserved_tokens: int,
    ) -> int:
        """Reconcile reservation with actual LLM usage.

        Use after the LLM call returns the real prompt+completion total.
        `actual_tokens > reserved_tokens` increments the diff;
        `actual_tokens < reserved_tokens` decrements the diff.
        """
        delta = actual_tokens - reserved_tokens
        if delta == 0:
            return await self.get_usage(tenant_id)
        key = self._key(tenant_id)
        if delta > 0:
            await self._client.incrby(key, delta)
        else:
            await self._client.decrby(key, -delta)
        return await self.get_usage(tenant_id)

    async def get_usage(self, tenant_id: UUID) -> int:
        """Read today's counter (0 if no usage yet)."""
        raw = await self._client.get(self._key(tenant_id))
        if raw is None:
            return 0
        return int(raw)


# Module-level singleton — reset hook per testing.md §Module-level Singleton Reset Pattern.
_enforcer: QuotaEnforcer | None = None


def get_quota_enforcer() -> QuotaEnforcer:
    """FastAPI Depends accessor (strict — raises if uninitialised).

    Real wiring done at app startup (api/main.py creates Redis client +
    calls `set_quota_enforcer`). Tests patch via `set_quota_enforcer`
    with a fakeredis-backed instance.
    """
    if _enforcer is None:
        raise RuntimeError(
            "QuotaEnforcer not initialised; call set_quota_enforcer() at "
            "app startup or in test fixture"
        )
    return _enforcer


def maybe_get_quota_enforcer() -> QuotaEnforcer | None:
    """FastAPI Depends accessor (lenient — returns None if uninitialised).

    Used by chat router so existing tests / dev mode without Redis still
    pass when ``quota_enforcement_enabled=False``. The router gates on
    settings flag *and* enforcer-not-None before attempting enforcement.
    """
    return _enforcer


def set_quota_enforcer(enforcer: QuotaEnforcer | None) -> None:
    """Install singleton (app startup or tests fixture)."""
    global _enforcer
    _enforcer = enforcer


def reset_quota_enforcer() -> None:
    """Test isolation hook (per testing.md §Module-level Singleton Reset Pattern)."""
    global _enforcer
    _enforcer = None
