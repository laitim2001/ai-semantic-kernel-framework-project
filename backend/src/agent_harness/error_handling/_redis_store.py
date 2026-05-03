"""
File: backend/src/agent_harness/error_handling/_redis_store.py
Purpose: Redis-backed BudgetStore for production TenantErrorBudget.
Category: 範疇 8 (Error Handling)
Scope: Phase 53.2 / Sprint 53.2

Description:
    Production impl of `BudgetStore` Protocol using `redis.asyncio`.
    Atomic INCR + EXPIRE per key.

    Why split from `budget.py`?
      - Keeps redis dependency optional at import time. Tests / dev mode
        can use `InMemoryBudgetStore` without importing redis.
      - Redis client construction is environment-specific (URL / auth /
        pool config) — caller injects the client.

    Atomicity: Each increment uses MULTI/EXEC pipeline so INCR and
    EXPIRE land in the same Redis round-trip. Idempotent under retry.

Owner: 01-eleven-categories-spec.md §Cat 8 + multi-tenant-data.md
Created: 2026-05-03 (Sprint 53.2 Day 2)

Modification History (newest-first):
    - 2026-05-03: Initial creation (Sprint 53.2 Day 2) — US-4 Redis store
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from redis.asyncio import Redis


class RedisBudgetStore:
    """BudgetStore Protocol impl over redis.asyncio.

    Caller constructs the Redis client (handles URL / auth / pool / TLS)
    and injects it. This module does not own connection lifecycle.
    """

    def __init__(self, client: "Redis[bytes]") -> None:
        self._client = client

    async def increment(self, key: str, ttl_seconds: int) -> int:
        # MULTI/EXEC pipeline — INCR + EXPIRE land atomically.
        async with self._client.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, ttl_seconds)
            results = await pipe.execute()
        return cast(int, results[0])

    async def get(self, key: str) -> int:
        raw = await self._client.get(key)
        if raw is None:
            return 0
        # redis-py returns bytes by default; decode to int.
        return int(raw)
