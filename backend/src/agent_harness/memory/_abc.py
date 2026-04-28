"""
File: backend/src/agent_harness/memory/_abc.py
Purpose: Category 3 ABC — MemoryLayer (5-layer memory abstraction).
Category: 範疇 3 (Memory)
Scope: Phase 49 / Sprint 49.1 (stub; impl in Phase 51.2)

Description:
    Memory has 5 layers (system / tenant / role / user / session) × 3
    time scales (permanent / quarterly / daily). Each layer implements
    MemoryLayer ABC. Reads return MemoryHints (lightweight), full
    materialization is on-demand to control token cost.

Owner: 01-eleven-categories-spec.md §範疇 3
Single-source: 17.md §2.1

Created: 2026-04-29 (Sprint 49.1)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Literal
from uuid import UUID

from agent_harness._contracts import MemoryHint, TraceContext


class MemoryScope(Enum):
    """5 layers per V2 design."""

    SYSTEM = "system"
    TENANT = "tenant"
    ROLE = "role"
    USER = "user"
    SESSION = "session"


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
        max_hints: int = 10,
        trace_context: TraceContext | None = None,
    ) -> list[MemoryHint]:
        """Returns lightweight hints; resolve full content via pointer."""
        ...

    @abstractmethod
    async def write(
        self,
        *,
        content: str,
        tenant_id: UUID | None = None,
        user_id: UUID | None = None,
        ttl: Literal["permanent", "quarterly", "daily"] = "permanent",
        trace_context: TraceContext | None = None,
    ) -> UUID:
        """Returns the new entry's ID."""
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
