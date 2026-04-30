"""
File: backend/src/agent_harness/memory/layers/session_layer.py
Purpose: Layer 5 (Session) concrete MemoryLayer — in-memory dict-backed (51.2).
Category: 範疇 3 (Memory) / Layer 5 Session
Scope: Phase 51 / Sprint 51.2 Day 2

Description:
    SessionLayer stores per-session working memory (transient hints during
    an active conversation). 51.2 design choice:
    - In-memory dict (per SessionLayer instance) keyed by tenant + session
    - 24h TTL via expires_at on each hint (lazy expiry on read)
    - NOT Redis-backed — infrastructure/cache module is still a stub at
      Sprint 49.x; CARRY-029 promotes to Redis when cache module ships

    Tenant isolation enforced via composite key: (tenant_id, session_id).
    Cross-tenant reads return empty.

Owner: 01-eleven-categories-spec.md §範疇 3 Layer 5 Session

Carry items:
    - CARRY-029 (new in 51.2): swap in-memory dict for Redis when
      infrastructure/cache lands a real client (Phase 52.x).

Created: 2026-04-30 (Sprint 51.2 Day 2.3)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID, uuid4

from agent_harness._contracts import MemoryHint, TraceContext
from agent_harness.memory._abc import MemoryLayer, MemoryScope

_TimeScale = Literal["short_term", "long_term", "semantic"]


@dataclass
class _SessionEntry:
    """Internal in-memory entry. Not exported."""

    entry_id: UUID
    tenant_id: UUID
    session_id: UUID
    content: str
    confidence: float
    created_at: datetime
    expires_at: datetime
    metadata: dict[str, object] = field(default_factory=dict)


class SessionLayer(MemoryLayer):
    """Layer 5 — per-session working memory; 51.2 in-memory dict backend."""

    scope = MemoryScope.SESSION

    def __init__(self) -> None:
        # composite key: (tenant_id, session_id) -> list of entries
        self._store: dict[tuple[UUID, UUID], list[_SessionEntry]] = {}
        self._lock = asyncio.Lock()

    async def read(
        self,
        *,
        query: str,
        tenant_id: UUID | None = None,
        user_id: UUID | None = None,  # session_id passed via this param for layer-5 only
        time_scales: tuple[_TimeScale, ...] = ("short_term",),
        max_hints: int = 10,
        trace_context: TraceContext | None = None,
    ) -> list[MemoryHint]:
        """Search session entries by substring; tenant + session_id required.

        Note: SessionLayer overloads `user_id` parameter to mean session_id
        because the ABC was designed for layers 1-4. Callers querying via
        MemoryRetrieval should pass session_id in the user_id slot for
        layer="session". The retrieval coordinator hides this detail.
        """
        if tenant_id is None or user_id is None:
            return []
        # Only short_term axis is meaningful for session layer
        if "short_term" not in time_scales:
            return []

        session_id = user_id  # see docstring
        key = (tenant_id, session_id)

        async with self._lock:
            entries = list(self._store.get(key, []))

        now = datetime.now(timezone.utc)
        # Lazy expiry: drop expired entries on read (best-effort)
        live = [e for e in entries if e.expires_at > now]
        if len(live) != len(entries):
            async with self._lock:
                self._store[key] = live

        # Substring filter
        ql = query.lower()
        matched = [e for e in live if ql in e.content.lower()]

        # Sort by confidence desc, then recency
        matched.sort(key=lambda e: (e.confidence, e.created_at), reverse=True)
        top = matched[:max_hints]

        return [self._entry_to_hint(e) for e in top]

    async def write(
        self,
        *,
        content: str,
        tenant_id: UUID | None = None,
        user_id: UUID | None = None,  # session_id slot (see read docstring)
        time_scale: _TimeScale = "short_term",
        confidence: float = 0.5,
        trace_context: TraceContext | None = None,
    ) -> UUID:
        if tenant_id is None or user_id is None:
            raise ValueError(
                "SessionLayer.write requires tenant_id and user_id (session_id slot)"
            )
        if time_scale != "short_term":
            raise ValueError(
                "SessionLayer only supports short_term writes; "
                "use UserLayer or TenantLayer for long_term."
            )

        session_id = user_id
        now = datetime.now(timezone.utc)
        entry = _SessionEntry(
            entry_id=uuid4(),
            tenant_id=tenant_id,
            session_id=session_id,
            content=content,
            confidence=round(confidence, 2),
            created_at=now,
            expires_at=now + timedelta(hours=24),
            metadata={"time_scale": "short_term"},
        )

        async with self._lock:
            self._store.setdefault((tenant_id, session_id), []).append(entry)

        return entry.entry_id

    async def evict(
        self,
        *,
        entry_id: UUID,
        tenant_id: UUID | None = None,
        trace_context: TraceContext | None = None,
    ) -> None:
        if tenant_id is None:
            return
        async with self._lock:
            for key, entries in list(self._store.items()):
                if key[0] != tenant_id:
                    continue
                self._store[key] = [e for e in entries if e.entry_id != entry_id]

    async def resolve(
        self,
        hint: MemoryHint,
        *,
        trace_context: TraceContext | None = None,
    ) -> str:
        if hint.tenant_id is None:
            return ""
        async with self._lock:
            for (tid, _sid), entries in self._store.items():
                if tid != hint.tenant_id:
                    continue
                for e in entries:
                    if e.entry_id == hint.hint_id:
                        return e.content
        return ""

    @staticmethod
    def _entry_to_hint(entry: _SessionEntry) -> MemoryHint:
        return MemoryHint(
            hint_id=entry.entry_id,
            layer="session",
            time_scale="short_term",
            summary=entry.content[:200],
            confidence=entry.confidence,
            relevance_score=entry.confidence,
            full_content_pointer=f"session:{entry.session_id}:{entry.entry_id}",
            timestamp=entry.created_at,
            expires_at=entry.expires_at,
            tenant_id=entry.tenant_id,
        )
