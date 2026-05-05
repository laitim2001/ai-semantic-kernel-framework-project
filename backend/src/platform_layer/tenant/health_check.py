"""
File: backend/src/platform_layer/tenant/health_check.py
Purpose: TenantHealthChecker — 6-point health probe gating PROVISIONING → ACTIVE.
Category: Phase 56 SaaS Stage 1 (platform_layer.tenant)
Scope: Sprint 56.1 / Day 3 / US-3 part 2

Description:
    Runs 6 independent probes against tenant infrastructure; returns aggregate
    pass/fail + per-probe detail. Used by US-3 onboarding API to gate the
    PROVISIONING → ACTIVE state transition.

    Probes (per checklist 3.2):
        1. db_connection         — `SELECT 1` against AsyncSession
        2. redis_ping            — `PING` (fakeredis-aware)
        3. qdrant_ping           — placeholder True (Phase 56.x integration)
        4. sample_llm_call       — minimal `chat()` via ChatClient (optional)
        5. first_admin_user      — at least 1 user with admin role for tenant
        6. api_key_valid         — at least 1 active api_key for tenant

    Per-probe timeout = 5s. Overall budget = 30s. Each probe wrapped in
    `asyncio.wait_for` so a hanging dep does not stall the whole check.

    D24 (Day 3): `ChatClient` injection is optional — tests inject a mock
    that returns trivial output; production wires real adapter. When
    `chat_client=None`, that probe returns False with reason
    "no chat_client provided" (does not block ACTIVE if production op
    explicitly disables this probe via Phase 56.x flag).

Modification History (newest-first):
    - 2026-05-06: Initial creation (Sprint 56.1 Day 3 / US-3 part 2)

Related:
    - sprint-56-1-plan.md §US-3 Onboarding Wizard
    - onboarding.py — OnboardingTracker (auto-transition trigger)
    - lifecycle.py — TenantLifecycle.transition (PROVISIONING → ACTIVE gate)
    - infrastructure/db/models/{api_keys,identity}.py — User / Role / ApiKey ORM
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Awaitable, Callable
from uuid import UUID

from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.api_keys import ApiKey
from infrastructure.db.models.identity import Role, User, UserRole

if TYPE_CHECKING:
    from redis.asyncio import Redis


PROBE_TIMEOUT_SECONDS = 5.0
OVERALL_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class ProbeResult:
    name: str
    passed: bool
    reason: str = ""
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class HealthCheckReport:
    tenant_id: UUID
    all_passed: bool
    probe_results: list[ProbeResult] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": str(self.tenant_id),
            "all_passed": self.all_passed,
            "probes": [
                {
                    "name": p.name,
                    "passed": p.passed,
                    "reason": p.reason,
                    "duration_seconds": round(p.duration_seconds, 4),
                }
                for p in self.probe_results
            ],
        }


class TenantHealthChecker:
    """Runs 6 health probes against tenant infrastructure."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        redis_client: "Redis[bytes] | None" = None,  # type: ignore[type-arg, unused-ignore]
        chat_call: Callable[[], Awaitable[bool]] | None = None,
        qdrant_ping: Callable[[], Awaitable[bool]] | None = None,
    ) -> None:
        self._session = session
        self._redis_client = redis_client
        self._chat_call = chat_call
        self._qdrant_ping = qdrant_ping

    async def run(self, tenant_id: UUID) -> HealthCheckReport:
        async def _wrap(name: str, coro: Awaitable[tuple[bool, str]]) -> ProbeResult:
            loop = asyncio.get_running_loop()
            start = loop.time()
            try:
                passed, reason = await asyncio.wait_for(coro, timeout=PROBE_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                return ProbeResult(
                    name=name,
                    passed=False,
                    reason=f"timeout after {PROBE_TIMEOUT_SECONDS}s",
                    duration_seconds=PROBE_TIMEOUT_SECONDS,
                )
            except Exception as exc:  # noqa: BLE001 — probe boundary
                return ProbeResult(
                    name=name,
                    passed=False,
                    reason=f"error: {type(exc).__name__}: {exc}",
                    duration_seconds=loop.time() - start,
                )
            return ProbeResult(
                name=name,
                passed=passed,
                reason=reason,
                duration_seconds=loop.time() - start,
            )

        async def _all_probes() -> list[ProbeResult]:
            return [
                await _wrap("db_connection", self._db_probe()),
                await _wrap("redis_ping", self._redis_probe()),
                await _wrap("qdrant_ping", self._qdrant_probe()),
                await _wrap("sample_llm_call", self._llm_probe()),
                await _wrap("first_admin_user", self._first_admin_probe(tenant_id)),
                await _wrap("api_key_valid", self._api_key_probe(tenant_id)),
            ]

        try:
            results = await asyncio.wait_for(_all_probes(), timeout=OVERALL_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            results = [
                ProbeResult(
                    name="overall",
                    passed=False,
                    reason=f"overall timeout after {OVERALL_TIMEOUT_SECONDS}s",
                    duration_seconds=OVERALL_TIMEOUT_SECONDS,
                )
            ]

        all_passed = all(p.passed for p in results) and len(results) == 6
        return HealthCheckReport(tenant_id=tenant_id, all_passed=all_passed, probe_results=results)

    # ---- Individual probes -----------------------------------------

    async def _db_probe(self) -> tuple[bool, str]:
        result = await self._session.execute(text("SELECT 1"))
        value = result.scalar_one()
        return (value == 1, "ok" if value == 1 else f"unexpected: {value}")

    async def _redis_probe(self) -> tuple[bool, str]:
        if self._redis_client is None:
            return (False, "no redis_client provided")
        await self._redis_client.ping()
        return (True, "ok")

    async def _qdrant_probe(self) -> tuple[bool, str]:
        if self._qdrant_ping is None:
            return (True, "placeholder (Phase 56.x integrate)")
        ok = await self._qdrant_ping()
        return (ok, "ok" if ok else "qdrant ping returned False")

    async def _llm_probe(self) -> tuple[bool, str]:
        if self._chat_call is None:
            return (False, "no chat_client provided")
        ok = await self._chat_call()
        return (ok, "ok" if ok else "chat probe returned False")

    async def _first_admin_probe(self, tenant_id: UUID) -> tuple[bool, str]:
        # Find at least one user-role pair where role.code == 'admin'
        # (or 'tenant_admin') for this tenant. RBAC role enumeration
        # (D13 carryover) — accept either code pattern.
        # D26 (Sprint 56.1 Day 3): Role schema uses `code` not `name`
        # (per 09-db-schema-design.md L150-162; identity.py:212).
        stmt = (
            select(User.id)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                and_(
                    User.tenant_id == tenant_id,
                    Role.code.in_(["admin", "tenant_admin"]),
                )
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return (row is not None, "ok" if row else "no admin user for tenant")

    async def _api_key_probe(self, tenant_id: UUID) -> tuple[bool, str]:
        stmt = (
            select(ApiKey.id)
            .where(and_(ApiKey.tenant_id == tenant_id, ApiKey.status == "active"))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return (row is not None, "ok" if row else "no active api_key for tenant")
