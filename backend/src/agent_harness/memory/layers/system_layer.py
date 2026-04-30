"""
File: backend/src/agent_harness/memory/layers/system_layer.py
Purpose: Layer 1 (System) concrete MemoryLayer — PostgreSQL memory_system; read-only.
Category: 範疇 3 (Memory) / Layer 1 System
Scope: Phase 51 / Sprint 51.2 Day 2

Description:
    SystemLayer stores global system rules / safety policies / compliance
    constants. Per spec, system layer is read-only at runtime; writes
    happen only via admin migrations (out of scope for the agent loop).

    51.2 implementation:
    - read() searches memory_system table by ILIKE (no tenant filter — global)
    - write() raises PermissionError (caller must catch or expect failure)
    - evict() also raises PermissionError
    - time_scales filter: only long_term supported; others return empty

Owner: 01-eleven-categories-spec.md §範疇 3 Layer 1 System
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_harness._contracts import MemoryHint, TraceContext
from agent_harness.memory._abc import MemoryLayer, MemoryScope
from infrastructure.db.models.memory import MemorySystem

_TimeScale = Literal["short_term", "long_term", "semantic"]


class SystemReadOnlyError(PermissionError):
    """Raised when attempting to write to or evict from the system layer."""


class SystemLayer(MemoryLayer):
    """Layer 1 — global system policies / rules; read-only at runtime."""

    scope = MemoryScope.SYSTEM

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def read(
        self,
        *,
        query: str,
        tenant_id: UUID | None = None,  # unused (global)
        user_id: UUID | None = None,  # unused
        time_scales: tuple[_TimeScale, ...] = ("long_term",),
        max_hints: int = 10,
        trace_context: TraceContext | None = None,
    ) -> list[MemoryHint]:
        # System layer is durable-only (versioned policies); other axes empty.
        if "long_term" not in time_scales:
            return []

        async with self._session_factory() as session:
            stmt = (
                select(MemorySystem)
                .where(
                    or_(
                        MemorySystem.content.ilike(f"%{query}%"),
                        MemorySystem.category.ilike(f"%{query}%"),
                        MemorySystem.key.ilike(f"%{query}%"),
                    )
                )
                .order_by(MemorySystem.version.desc())
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
        confidence: float = 1.0,
        trace_context: TraceContext | None = None,
    ) -> UUID:
        raise SystemReadOnlyError(
            "SystemLayer is read-only at runtime; "
            "use admin migrations to update system_policies."
        )

    async def evict(
        self,
        *,
        entry_id: UUID,
        tenant_id: UUID | None = None,
        trace_context: TraceContext | None = None,
    ) -> None:
        raise SystemReadOnlyError(
            "SystemLayer is read-only at runtime; cannot evict."
        )

    async def resolve(
        self,
        hint: MemoryHint,
        *,
        trace_context: TraceContext | None = None,
    ) -> str:
        async with self._session_factory() as session:
            stmt = select(MemorySystem.content).where(MemorySystem.id == hint.hint_id)
            result = (await session.execute(stmt)).scalar_one_or_none()
        return result if result is not None else ""

    @staticmethod
    def _row_to_hint(row: MemorySystem, *, query: str) -> MemoryHint:
        relevance_score = 0.9 if query.lower() in (row.content or "").lower() else 0.5
        return MemoryHint(
            hint_id=row.id,
            layer="system",
            time_scale="long_term",
            summary=(row.content or "")[:200],
            confidence=1.0,  # system policies are authoritative
            relevance_score=relevance_score,
            full_content_pointer=f"memory_system:{row.id}",
            timestamp=row.created_at,
            tenant_id=None,  # global
        )
