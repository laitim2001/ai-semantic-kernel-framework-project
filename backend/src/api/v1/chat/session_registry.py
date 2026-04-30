"""
File: backend/src/api/v1/chat/session_registry.py
Purpose: In-memory session_id → status / cancel-event registry.
Category: api/v1/chat
Scope: Phase 50 / Sprint 50.2 (Day 1.2)

Description:
    Minimal session bookkeeping for Phase 50.2. Tracks running loop runs by
    session_id with three pieces of state:
        - status: "running" | "completed" | "cancelled"
        - started_at: when register() was called
        - cancel_event: asyncio.Event the loop runner can poll for early exit

    DEPRECATED-IN: Phase 53.1 — when Checkpointer / State Mgmt + Temporal queue
    backend land, this in-memory registry should be replaced by DB-persisted
    session state. The leading SessionRegistry class is intentionally narrow
    so the swap is mechanical.

    Thread-safety: protected by a single `asyncio.Lock`; all mutations go
    through register() / mark_completed() / cancel(). Concurrent reads via
    get() / get_status() take the same lock to avoid mid-update tearing.

Key Components:
    - SessionEntry: dataclass holding (status / started_at / cancel_event)
    - SessionRegistry: register / get / cancel / mark_completed / cleanup

Created: 2026-04-30 (Sprint 50.2 Day 1.2)
Last Modified: 2026-04-30

Modification History (newest-first):
    - 2026-04-30: Initial creation (Sprint 50.2 Day 1.2) — in-memory registry
        with asyncio.Lock + cancel signal. DEPRECATED-IN: 53.1.

Related:
    - .router (creates entries on POST; reads on GET sessions/{id})
    - 06-phase-roadmap.md §Phase 53.1 (HITL pause/resume + persistence)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

SessionStatus = Literal["running", "completed", "cancelled"]


@dataclass
class SessionEntry:
    """Per-session state held by SessionRegistry. Not exposed to API surface."""

    status: SessionStatus = "running"
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)


class SessionRegistry:
    """In-memory session map. DEPRECATED-IN: 53.1 (DB-backed replacement)."""

    def __init__(self) -> None:
        self._entries: dict[UUID, SessionEntry] = {}
        self._lock = asyncio.Lock()

    async def register(self, session_id: UUID) -> SessionEntry:
        """Insert a new running entry. Idempotent on existing session_id."""
        async with self._lock:
            if session_id in self._entries:
                return self._entries[session_id]
            entry = SessionEntry()
            self._entries[session_id] = entry
            return entry

    async def get(self, session_id: UUID) -> SessionEntry | None:
        async with self._lock:
            return self._entries.get(session_id)

    async def cancel(self, session_id: UUID) -> bool:
        """Set status=cancelled + signal cancel_event. Returns True if found."""
        async with self._lock:
            entry = self._entries.get(session_id)
            if entry is None:
                return False
            if entry.status == "running":
                entry.status = "cancelled"
            entry.cancel_event.set()
            return True

    async def mark_completed(self, session_id: UUID) -> None:
        async with self._lock:
            entry = self._entries.get(session_id)
            if entry is not None and entry.status == "running":
                entry.status = "completed"

    async def cleanup(self, session_id: UUID) -> None:
        """Remove entry; idempotent on missing id."""
        async with self._lock:
            self._entries.pop(session_id, None)


# Module-level singleton — shared across router handlers within a single
# FastAPI app instance. Tests instantiate their own SessionRegistry to avoid
# state leakage.
_default_registry = SessionRegistry()


def get_default_registry() -> SessionRegistry:
    return _default_registry
