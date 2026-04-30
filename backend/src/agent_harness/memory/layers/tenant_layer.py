"""
File: backend/src/agent_harness/memory/layers/tenant_layer.py
Purpose: Layer 2 (Tenant) concrete MemoryLayer — PostgreSQL memory_tenant backed.
Category: 範疇 3 (Memory) / Layer 2 Tenant
Scope: Phase 51 / Sprint 51.2 Day 2

Description:
    TenantLayer stores tenant-wide knowledge: playbooks, SOPs, FAQs, domain
    knowledge. Maps onto MemoryTenant ORM (49.3 schema). 51.2 simplification:
    - Long-term axis only (semantic axis = empty until CARRY-026 Qdrant)
    - Substring match (ILIKE) for query
    - Tenant-scoped queries enforced at DB level

Owner: 01-eleven-categories-spec.md §範疇 3 Layer 2 Tenant
Single-source: 17.md §2.1

Created: 2026-04-30 (Sprint 51.2 Day 2)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_harness._contracts import MemoryHint, TraceContext
from agent_harness.memory._abc import MemoryLayer, MemoryScope
from infrastructure.db.models.memory import MemoryTenant

_TimeScale = Literal["short_term", "long_term", "semantic"]


class TenantLayer(MemoryLayer):
    """Layer 2 — tenant-wide memory backed by PostgreSQL memory_tenant."""

    scope = MemoryScope.TENANT

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def read(
        self,
        *,
        query: str,
        tenant_id: UUID | None = None,
        user_id: UUID | None = None,  # unused at tenant level
        time_scales: tuple[_TimeScale, ...] = ("long_term",),
        max_hints: int = 10,
        trace_context: TraceContext | None = None,
    ) -> list[MemoryHint]:
        if tenant_id is None:
            return []

        # Semantic-only: stub (CARRY-026)
        if time_scales == ("semantic",):
            return []

        async with self._session_factory() as session:
            stmt = (
                select(MemoryTenant)
                .where(
                    MemoryTenant.tenant_id == tenant_id,
                    or_(
                        MemoryTenant.content.ilike(f"%{query}%"),
                        MemoryTenant.category.ilike(f"%{query}%"),
                        MemoryTenant.key.ilike(f"%{query}%"),
                    ),
                )
                .order_by(MemoryTenant.updated_at.desc())
                .limit(max_hints)
            )
            rows = (await session.execute(stmt)).scalars().all()

        return [self._row_to_hint(row, query=query) for row in rows]

    async def write(
        self,
        *,
        content: str,
        tenant_id: UUID | None = None,
        user_id: UUID | None = None,  # unused
        time_scale: _TimeScale = "long_term",
        confidence: float = 0.5,
        trace_context: TraceContext | None = None,
    ) -> UUID:
        if tenant_id is None:
            raise ValueError("TenantLayer.write requires tenant_id")

        if time_scale == "short_term":
            # Tenant layer is intended for durable knowledge; short_term is
            # a no-op that warns rather than fails (caller should use SessionLayer).
            raise ValueError(
                "TenantLayer does not support short_term writes; "
                "use SessionLayer for working memory."
            )

        metadata: dict[str, Any] = {
            "time_scale": time_scale,
            "confidence": round(confidence, 2),
        }

        new_id = uuid4()
        async with self._session_factory() as session:
            row = MemoryTenant(
                id=new_id,
                tenant_id=tenant_id,
                key=f"hint-{new_id}",
                category="domain_knowledge",
                content=content,
                metadata_=metadata,
            )
            session.add(row)
            await session.commit()

        return new_id

    async def evict(
        self,
        *,
        entry_id: UUID,
        tenant_id: UUID | None = None,
        trace_context: TraceContext | None = None,
    ) -> None:
        if tenant_id is None:
            return
        async with self._session_factory() as session:
            await session.execute(
                delete(MemoryTenant).where(
                    MemoryTenant.id == entry_id,
                    MemoryTenant.tenant_id == tenant_id,
                )
            )
            await session.commit()

    async def resolve(
        self,
        hint: MemoryHint,
        *,
        trace_context: TraceContext | None = None,
    ) -> str:
        async with self._session_factory() as session:
            stmt = select(MemoryTenant.content).where(MemoryTenant.id == hint.hint_id)
            if hint.tenant_id is not None:
                stmt = stmt.where(MemoryTenant.tenant_id == hint.tenant_id)
            result = (await session.execute(stmt)).scalar_one_or_none()
        return result if result is not None else ""

    @staticmethod
    def _row_to_hint(row: MemoryTenant, *, query: str) -> MemoryHint:
        meta = row.metadata_ or {}
        time_scale = meta.get("time_scale", "long_term")
        if time_scale not in ("short_term", "long_term", "semantic"):
            time_scale = "long_term"

        confidence_value = float(meta.get("confidence", 0.6))
        relevance_score = 0.7 if query.lower() in (row.content or "").lower() else 0.3

        # row.created_at type is datetime per ORM mapping
        timestamp: datetime = row.created_at

        return MemoryHint(
            hint_id=row.id,
            layer="tenant",
            time_scale=time_scale,
            summary=(row.content or "")[:200],
            confidence=confidence_value,
            relevance_score=relevance_score,
            full_content_pointer=f"memory_tenant:{row.id}",
            timestamp=timestamp,
            tenant_id=row.tenant_id,
        )
