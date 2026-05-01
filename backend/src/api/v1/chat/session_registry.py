"""
File: backend/src/api/v1/chat/session_registry.py
Purpose: Tenant-scoped in-memory session_id → status / cancel-event registry.
Category: api/v1/chat
Scope: Phase 50 / Sprint 50.2 (Day 1.2) — Sprint 52.5 Day 2 (P0 #11 tenant-scope)

Description:
    Minimal session bookkeeping. Tracks running loop runs by
    (tenant_id, session_id) tuple with three pieces of state:
        - status: "running" | "completed" | "cancelled"
        - started_at: when register() was called
        - cancel_event: asyncio.Event the loop runner can poll for early exit

    Storage shape: ``dict[tenant_id, dict[session_id, SessionEntry]]``.
    All public methods take ``tenant_id`` as the first positional argument
    after ``self``. Cross-tenant lookups always return None (or False / no-op
    on cancel / mark_completed) — the API never reveals "session exists in
    another tenant", so callers must surface 404 either way.

    Sprint 52.5 P0 #11 rationale: V1 W3-2 audit verified the registry was a
    process-wide dict shared across tenants. SessionRegistry is the only
    in-memory tenant boundary in 50.2 main flow until Phase 53.1 swaps
    this for DB-persisted state — therefore it MUST enforce tenant
    isolation at the storage layer, not just the API layer.

    Thread-safety: protected by a single ``asyncio.Lock``. Reads + writes
    take the same lock to avoid mid-update tearing.

    DEPRECATED-IN: Phase 53.1 — when Checkpointer / State Mgmt + Temporal
    queue backend land, this in-memory registry should be replaced by
    DB-persisted session state. Keeping the leading SessionRegistry class
    intentionally narrow so the swap is mechanical.

Key Components:
    - SessionEntry: dataclass holding (status / started_at / cancel_event)
    - SessionRegistry: register / get / cancel / mark_completed / cleanup,
      all keyed by (tenant_id, session_id)

Created: 2026-04-30 (Sprint 50.2 Day 1.2)
Last Modified: 2026-05-01

Modification History (newest-first):
    - 2026-05-01: Sprint 52.5 Day 2.1 (P0 #11) — refactor storage to
        nested dict[tenant_id][session_id]; all methods take tenant_id.
        Cross-tenant lookups return None / False / no-op. Pre-existing
        single-arg callers must update or break loudly via TypeError
        (no shim — V2 audit P0 demands explicit tenant scoping).
    - 2026-04-30: Initial creation (Sprint 50.2 Day 1.2) — in-memory
        registry with asyncio.Lock + cancel signal. DEPRECATED-IN: 53.1.

Related:
    - .router (creates entries on POST; reads on GET sessions/{id})
    - .claude/rules/multi-tenant-data.md 鐵律 1-3
    - claudedocs/5-status/V2-AUDIT-W3-2-PHASE50-2.md (audit source)
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
    """Tenant-scoped in-memory session map. DEPRECATED-IN: 53.1 (DB-backed replacement).

    Storage: ``dict[tenant_id, dict[session_id, SessionEntry]]``. Cross-tenant
    queries always return None / False; the registry never reveals that a
    session_id exists under a different tenant.
    """

    def __init__(self) -> None:
        self._tenants: dict[UUID, dict[UUID, SessionEntry]] = {}
        self._lock = asyncio.Lock()

    async def register(
        self, tenant_id: UUID, session_id: UUID
    ) -> SessionEntry:
        """Insert a new running entry under ``tenant_id``. Idempotent on existing.

        Two different tenants may register the same session_id; entries are
        independent (separate cancel_event, separate status).
        """
        async with self._lock:
            sessions = self._tenants.setdefault(tenant_id, {})
            existing = sessions.get(session_id)
            if existing is not None:
                return existing
            entry = SessionEntry()
            sessions[session_id] = entry
            return entry

    async def get(
        self, tenant_id: UUID, session_id: UUID
    ) -> SessionEntry | None:
        """Return entry for (tenant, session) — or None if either is absent."""
        async with self._lock:
            sessions = self._tenants.get(tenant_id)
            if sessions is None:
                return None
            return sessions.get(session_id)

    async def cancel(
        self, tenant_id: UUID, session_id: UUID
    ) -> bool:
        """Set status=cancelled + signal cancel_event. Returns True if found.

        Cross-tenant cancel attempts return False (treated as not-found).
        """
        async with self._lock:
            sessions = self._tenants.get(tenant_id)
            if sessions is None:
                return False
            entry = sessions.get(session_id)
            if entry is None:
                return False
            if entry.status == "running":
                entry.status = "cancelled"
            entry.cancel_event.set()
            return True

    async def mark_completed(
        self, tenant_id: UUID, session_id: UUID
    ) -> None:
        """Mark running entry completed. No-op on missing or cancelled entry.

        Cross-tenant calls are no-ops — the registry never silently mutates
        an entry belonging to another tenant.
        """
        async with self._lock:
            sessions = self._tenants.get(tenant_id)
            if sessions is None:
                return
            entry = sessions.get(session_id)
            if entry is not None and entry.status == "running":
                entry.status = "completed"

    async def cleanup(
        self, tenant_id: UUID, session_id: UUID
    ) -> None:
        """Remove entry; idempotent on missing id or absent tenant.

        If tenant has no remaining sessions after removal, the tenant entry
        itself is also dropped to avoid unbounded dict growth from short-lived
        tenants (e.g. probe / smoke-test workloads).
        """
        async with self._lock:
            sessions = self._tenants.get(tenant_id)
            if sessions is None:
                return
            sessions.pop(session_id, None)
            if not sessions:
                del self._tenants[tenant_id]


# Module-level singleton — shared across router handlers within a single
# FastAPI app instance. Tests instantiate their own SessionRegistry to avoid
# state leakage.
_default_registry = SessionRegistry()


def get_default_registry() -> SessionRegistry:
    return _default_registry
