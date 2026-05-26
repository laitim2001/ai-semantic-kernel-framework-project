"""
File: backend/src/platform_layer/governance/hitl/policy_store.py
Purpose: DBHITLPolicyStore — DB-backed HITLPolicyStore implementation.
Category: Platform / Governance / HITL
Scope: Sprint 55.3 Day 3 (closes AD-Hitl-7)

Description:
    Concrete `HITLPolicyStore` ABC impl reading per-tenant policy rows from
    `hitl_policies` table (Alembic 0013). Returns None when no row exists;
    DefaultHITLManager handles fallback to construction-time default_policy.

    Tenant isolation:
        The query filters WHERE tenant_id = :tid. RLS policy on
        hitl_policies (per 0013 migration) enforces the same boundary
        at the storage layer for any direct query that lacks the JOIN
        (defense-in-depth).

    Hydration:
        Schema columns mirror HITLPolicy dataclass fields (D6-corrected
        Sprint 55.3 Day 3); RiskLevel enum values stored as VARCHAR(32)
        and converted via RiskLevel(value) on read. JSONB columns
        (reviewer_groups_by_risk, sla_seconds_by_risk) are dict[str, ...]
        on Python side; keys are RiskLevel.value strings, converted back
        to RiskLevel enum members on hydration.

Created: 2026-05-04 (Sprint 55.3 Day 3)

Modification History:
    - 2026-05-26: Sprint 57.54 — add put() upsert via pg_insert.on_conflict_do_update (Track A)
    - 2026-05-04: Initial creation (Sprint 55.3 / closes AD-Hitl-7)

Related:
    - agent_harness/hitl/_abc.py — HITLPolicyStore ABC
    - agent_harness/_contracts/hitl.py — HITLPolicy / RiskLevel single-source
    - infrastructure/db/models/governance.py — HitlPolicyRow ORM
    - infrastructure/db/migrations/versions/0013_hitl_policies.py — schema
    - .hitl.manager — consumer (DefaultHITLManager wires this)
"""

from __future__ import annotations

from typing import Any, Callable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from agent_harness._contracts.hitl import HITLPolicy, RiskLevel
from agent_harness.hitl import HITLPolicyStore
from infrastructure.db.models.governance import HitlPolicyRow

SessionFactory = Callable[[], Any]


class DBHITLPolicyStore(HITLPolicyStore):
    """DB-backed HITLPolicyStore.

    Args:
        session_factory: callable returning an async-context-manager-yielding
            AsyncSession. Same factory threading pattern as DefaultHITLManager
            (Sprint 53.4 US-2).
    """

    def __init__(self, *, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def get(self, tenant_id: UUID) -> HITLPolicy | None:
        """Return per-tenant policy; None if no override row exists."""
        async with self._session_factory() as session:
            stmt = select(HitlPolicyRow).where(HitlPolicyRow.tenant_id == tenant_id)
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return _row_to_policy(row, tenant_id)

    async def put(self, tenant_id: UUID, policy: HITLPolicy) -> HITLPolicy:
        """Upsert per-tenant HITLPolicy; returns the persisted policy.

        Uses PostgreSQL ON CONFLICT (tenant_id) DO UPDATE upsert for atomicity.
        The updated_at column rotates server-side via func.now() in the set_
        clause (server_default applies only to INSERT path).

        Args:
            tenant_id: Owning tenant UUID; used as conflict key + final tenant
                stamp on the returned dataclass.
            policy: HITLPolicy composite (4 fields). The dataclass's own
                tenant_id is ignored in favour of the explicit `tenant_id`
                argument so callers cannot accidentally write a row scoped to
                the wrong tenant.

        Returns:
            HITLPolicy hydrated from the upserted row.
        """
        async with self._session_factory() as session:
            # JSONB columns store dict[str, V]; convert from dict[RiskLevel, V].
            reviewer_groups_jsonb = {k.value: v for k, v in policy.reviewer_groups_by_risk.items()}
            sla_seconds_jsonb = {k.value: v for k, v in policy.sla_seconds_by_risk.items()}
            stmt = (
                pg_insert(HitlPolicyRow)
                .values(
                    tenant_id=tenant_id,
                    auto_approve_max_risk=policy.auto_approve_max_risk.value,
                    require_approval_min_risk=policy.require_approval_min_risk.value,
                    reviewer_groups_by_risk=reviewer_groups_jsonb,
                    sla_seconds_by_risk=sla_seconds_jsonb,
                )
                .on_conflict_do_update(
                    index_elements=["tenant_id"],
                    set_={
                        "auto_approve_max_risk": policy.auto_approve_max_risk.value,
                        "require_approval_min_risk": (policy.require_approval_min_risk.value),
                        "reviewer_groups_by_risk": reviewer_groups_jsonb,
                        "sla_seconds_by_risk": sla_seconds_jsonb,
                        "updated_at": func.now(),
                    },
                )
                .returning(HitlPolicyRow)
            )
            result = await session.execute(stmt)
            await session.commit()
            row = result.scalar_one()
            return _row_to_policy(row, tenant_id)


def _row_to_policy(row: HitlPolicyRow, tenant_id: UUID) -> HITLPolicy:
    """Hydrate HitlPolicyRow → HITLPolicy.

    Converts VARCHAR risk-level columns + JSONB dict columns back to
    typed RiskLevel + dict[RiskLevel, ...] structures.
    """
    return HITLPolicy(
        tenant_id=tenant_id,
        auto_approve_max_risk=RiskLevel(row.auto_approve_max_risk),
        require_approval_min_risk=RiskLevel(row.require_approval_min_risk),
        reviewer_groups_by_risk=_hydrate_risk_dict(row.reviewer_groups_by_risk),
        sla_seconds_by_risk=_hydrate_risk_dict(row.sla_seconds_by_risk),
    )


def _hydrate_risk_dict(raw: dict[str, Any]) -> dict[RiskLevel, Any]:
    """Convert JSONB dict[str, V] → dict[RiskLevel, V]; tolerates missing keys."""
    if not raw:
        return {}
    return {RiskLevel(k): v for k, v in raw.items() if k in RiskLevel.__members__}
