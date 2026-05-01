"""
File: backend/src/agent_harness/memory/layers/role_layer.py
Purpose: Layer 3 (Role) concrete MemoryLayer — PostgreSQL memory_role; simplified.
Category: 範疇 3 (Memory) / Layer 3 Role
Scope: Phase 51 / Sprint 51.2 Day 2

Description:
    RoleLayer stores per-role policies / workflows / approval rules. Per
    sprint-51-2-plan.md §2.1 "9/15 cell" scope, role layer is simplified
    in 51.2:
    - read() supported (admin-seeded data)
    - write() raises NotImplementedError; admin UI / migration writes
      memory_role rows out-of-band (Phase 53+ work)
    - evict() raises NotImplementedError
    - Tenant resolution via FK chain (role_id -> roles.tenant_id) — 51.2 takes
      tenant_id as caller-provided + relies on caller to resolve role list

Owner: 01-eleven-categories-spec.md §範疇 3 Layer 3 Role
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_harness._contracts import MemoryHint, TraceContext
from agent_harness.memory._abc import MemoryLayer, MemoryScope
from infrastructure.db.models.memory import MemoryRole

_TimeScale = Literal["short_term", "long_term", "semantic"]


class RoleLayer(MemoryLayer):
    """Layer 3 — per-role memory; simplified read-only impl in 51.2."""

    scope = MemoryScope.ROLE

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def read(
        self,
        *,
        query: str,
        tenant_id: UUID | None = None,  # used only as future hook (51.2 ignores)
        user_id: UUID | None = None,  # unused
        time_scales: tuple[_TimeScale, ...] = ("long_term",),
        max_hints: int = 10,
        trace_context: TraceContext | None = None,
    ) -> list[MemoryHint]:
        # 51.2 simplification: long_term only; tenant filtering via role chain
        # is admin-managed (out of scope for this sprint)
        if "long_term" not in time_scales:
            return []

        async with self._session_factory() as session:
            stmt = (
                select(MemoryRole)
                .where(
                    or_(
                        MemoryRole.content.ilike(f"%{query}%"),
                        MemoryRole.category.ilike(f"%{query}%"),
                        MemoryRole.key.ilike(f"%{query}%"),
                    )
                )
                .order_by(MemoryRole.created_at.desc())
                .limit(max_hints)
            )
            rows = (await session.execute(stmt)).scalars().all()

        return [self._row_to_hint(row, query=query) for row in rows]

    async def write(
        self,
        *,
        content: str,
        tenant_id: UUID | None = None,
        user_id: UUID | None = None,
        time_scale: _TimeScale = "long_term",
        confidence: float = 0.5,
        trace_context: TraceContext | None = None,
    ) -> UUID:
        raise NotImplementedError(
            "RoleLayer write is admin-managed (Phase 53+); "
            "use admin UI / migration to populate memory_role table."
        )

    async def evict(
        self,
        *,
        entry_id: UUID,
        tenant_id: UUID | None = None,
        trace_context: TraceContext | None = None,
    ) -> None:
        raise NotImplementedError("RoleLayer evict is admin-managed (Phase 53+).")

    async def resolve(
        self,
        hint: MemoryHint,
        *,
        trace_context: TraceContext | None = None,
    ) -> str:
        async with self._session_factory() as session:
            stmt = select(MemoryRole.content).where(MemoryRole.id == hint.hint_id)
            result = (await session.execute(stmt)).scalar_one_or_none()
        return result if result is not None else ""

    @staticmethod
    def _row_to_hint(row: MemoryRole, *, query: str) -> MemoryHint:
        relevance_score = 0.7 if query.lower() in (row.content or "").lower() else 0.3
        return MemoryHint(
            hint_id=row.id,
            layer="role",
            time_scale="long_term",
            summary=(row.content or "")[:200],
            confidence=0.7,  # role-level rules are admin-curated
            relevance_score=relevance_score,
            full_content_pointer=f"memory_role:{row.id}",
            timestamp=row.created_at,
            tenant_id=None,  # 51.2 simplification (resolved via FK chain)
        )
