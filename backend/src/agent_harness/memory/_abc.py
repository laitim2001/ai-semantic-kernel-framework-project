"""
File: backend/src/agent_harness/memory/_abc.py
Purpose: Category 3 ABC — MemoryLayer (5-layer × 3-time-scale memory abstraction).
Category: 範疇 3 (Memory)
Scope: Phase 49 / Sprint 49.1 (stub); Phase 51 / Sprint 51.2 Day 1 (time_scale axis)

Description:
    Memory has dual axes: 5 scopes (system / tenant / role / user / session)
    × 3 time scales (short_term / long_term / semantic). Each concrete layer
    implements MemoryLayer ABC. Reads return MemoryHints (lightweight); full
    materialization is on-demand to control token cost.

    Sprint 51.2 Day 1 changes write() signature: ttl literal is replaced by
    time_scale, aligning with 01-eleven-categories-spec.md §範疇 3 dual-axis
    matrix. TTL becomes per-scope policy mapping inside concrete layers
    (e.g., short_term → 24h Redis TTL; long_term → NULL or 90d per scope;
    semantic → indexed without TTL).

Owner: 01-eleven-categories-spec.md §範疇 3
Single-source: 17.md §2.1

Created: 2026-04-29 (Sprint 49.1)
Last Modified: 2026-04-30 (Sprint 51.2 Day 1)

Modification History (newest-first):
    - 2026-04-30: write() signature ttl→time_scale per Sprint 51.2 plan §2.3 —
      breaking ABC change at stub stage (no concrete impls yet)
    - 2026-04-29: Initial creation (Sprint 49.1)

Related:
    - 01-eleven-categories-spec.md §範疇 3 — dual-axis matrix definition
    - 17-cross-category-interfaces.md §2.1 — single-source ABC row
    - sprint-51-2-plan.md §2.3 — write() signature change rationale
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Literal
from uuid import UUID

from agent_harness._contracts import MemoryHint, TraceContext


class MemoryScope(Enum):
    """5 layers per V2 design (axis 1: scope)."""

    SYSTEM = "system"
    TENANT = "tenant"
    ROLE = "role"
    USER = "user"
    SESSION = "session"


class MemoryTimeScale(Enum):
    """3 time scales per V2 design (axis 2: time_scale).

    Sprint 51.2 introduces this enum to match Literal type used in
    write()/read() signatures. TTL mapping is per-scope concrete-layer
    responsibility, not ABC concern.
    """

    SHORT_TERM = "short_term"  # working memory; per-session; Redis or in-mem
    LONG_TERM = "long_term"  # durable; cross-session; PostgreSQL
    SEMANTIC = "semantic"  # vector-indexed; Qdrant (Sprint 51.2 stub)


class MemoryLayer(ABC):
    """One layer of memory (system / tenant / role / user / session)."""

    scope: MemoryScope

    @abstractmethod
    async def read(
        self,
        *,
        query: str,
        tenant_id: UUID | None = None,
        user_id: UUID | None = None,
        time_scales: tuple[Literal["short_term", "long_term", "semantic"], ...] = ("long_term",),
        max_hints: int = 10,
        trace_context: TraceContext | None = None,
    ) -> list[MemoryHint]:
        """Returns lightweight hints; resolve full content via pointer.

        time_scales filters which sub-stores to query (e.g., long_term only,
        or both long_term + semantic). Concrete layers may not support all
        time scales (e.g., system layer typically only long_term).
        """
        ...

    @abstractmethod
    async def write(
        self,
        *,
        content: str,
        tenant_id: UUID | None = None,
        user_id: UUID | None = None,
        time_scale: Literal["short_term", "long_term", "semantic"] = "long_term",
        confidence: float = 0.5,
        trace_context: TraceContext | None = None,
    ) -> UUID:
        """Returns the new entry's ID.

        time_scale routes to underlying store (Redis / PostgreSQL / Qdrant)
        and determines TTL policy (per-scope mapping inside concrete layer).
        confidence is memory-intrinsic credibility; relevance_score is
        per-query and computed at read() time.
        """
        ...

    @abstractmethod
    async def evict(
        self,
        *,
        entry_id: UUID,
        tenant_id: UUID | None = None,
        trace_context: TraceContext | None = None,
    ) -> None: ...

    @abstractmethod
    async def resolve(
        self,
        hint: MemoryHint,
        *,
        trace_context: TraceContext | None = None,
    ) -> str:
        """Materializes full content from a hint (on-demand)."""
        ...
