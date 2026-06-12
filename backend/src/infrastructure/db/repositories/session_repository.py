"""
File: backend/src/infrastructure/db/repositories/session_repository.py
Purpose: SessionRepository — DAO for sessions table (chat session lifecycle).
Category: Infrastructure / Repositories (Sprint 57.7 US-R1 / AD-Reality-3a)
Scope: Phase 57 / Sprint 57.7 Day 3 Tier 2

Description:
    Encapsulates Session ORM operations for chat router observer wiring.
    Sprint 57.6 left sessions/tool_calls deferred (AD-Reality-3a/3b) under
    the assumption that JWT user_id extraction infra was missing. Day 3
    探勘 found `TenantContextMiddleware.dispatch` at tenant_context.py:174
    already populates `request.state.user_id` from JWT claim.sub UUID
    parsing → unblocked.

    create_session():
        Best-effort INSERT — caller wraps in try/except so DB flake doesn't
        cascade into chat 503. Uses Session.user_id (NOT NULL FK to users.id)
        + tenant_id (TenantScopedMixin) + provided session_id (PK).

Created: 2026-05-10 (Sprint 57.7 Day 3 Tier 2)
Last Modified: 2026-06-02

Modification History (newest-first):
    - 2026-06-12: Sprint 57.107 B3 — sidechain params + list_sessions (top-level, newest-first)
    - 2026-06-02: Sprint 57.68 A-3b — handoff params + get_session + mark_handed_off
    - 2026-05-10: Initial creation (Sprint 57.7 US-R1 — AD-Reality-3a closure)

Related:
    - infrastructure/db/models/sessions.py (Session ORM)
    - api/v1/chat/router.py (consumer at chat POST entry)
    - tests/unit/infrastructure/db/repositories/test_session_repository.py
"""

from __future__ import annotations

import logging
from typing import Any, cast
from uuid import UUID

from sqlalchemy import CursorResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.sessions import Session

logger = logging.getLogger(__name__)


class SessionRepository:
    """DAO for sessions table — chat lifecycle persistence."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_session(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        tenant_id: UUID,
        title: str | None = None,
        handoff_parent_id: UUID | None = None,
        meta_data: dict[str, Any] | None = None,
        parent_session_id: UUID | None = None,
        is_sidechain: bool = False,
    ) -> Session:
        """INSERT a new session row.

        Caller responsible for transaction lifecycle (commit / rollback /
        SAVEPOINT). Returns the Session instance with server-generated
        timestamps populated AFTER `await self._db.flush()`.

        Args:
            session_id: Session UUID (caller-generated; matches SSE X-Session-Id header).
            user_id: Authenticated user from request.state.user_id.
            tenant_id: Multi-tenant scope from request.state.tenant_id.
            title: Optional session title (e.g. derived from first message).
            handoff_parent_id: Sprint 57.68 — parent session UUID when this row
                is booted by a Cat 11 HANDOFF; None for normal chat sessions.
            meta_data: Sprint 57.68 — optional JSONB metadata (e.g.
                {"agent_role": target_agent} for handoff-booted sessions);
                None falls back to the column server_default '{}'.
            parent_session_id: Sprint 57.107 — the parent session when this row
                is a subagent SIDECHAIN transcript (CC parentUuid borrow);
                None for top-level sessions.
            is_sidechain: Sprint 57.107 — True for subagent child transcript
                rows (excluded from top-level listings).

        Returns:
            Session: ORM instance with id + tenant_id + user_id committed.

        Raises:
            sqlalchemy.exc.IntegrityError: FK violation (user_id missing
                in users table; tenant_id missing in tenants table;
                handoff_parent_id missing in sessions table).
        """
        session = Session(
            id=session_id,
            user_id=user_id,
            tenant_id=tenant_id,
            title=title,
            status="active",
            handoff_parent_id=handoff_parent_id,
            parent_session_id=parent_session_id,
            is_sidechain=is_sidechain,
        )
        # Only set meta_data when provided so the column server_default '{}'
        # applies for normal sessions (avoid overriding with an empty dict).
        if meta_data is not None:
            session.meta_data = meta_data
        self._db.add(session)
        await self._db.flush()
        logger.debug(
            "session_repository.create_session ok",
            extra={
                "session_id": str(session_id),
                "user_id": str(user_id),
                "tenant_id": str(tenant_id),
                "handoff_parent_id": str(handoff_parent_id) if handoff_parent_id else None,
            },
        )
        return session

    async def get_session(self, *, session_id: UUID, tenant_id: UUID) -> Session | None:
        """Fetch a session scoped by tenant (multi-tenant 鐵律).

        Returns None when the session does not exist OR belongs to another
        tenant (the tenant filter prevents cross-tenant disclosure).
        """
        stmt = select(Session).where((Session.id == session_id) & (Session.tenant_id == tenant_id))
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_sessions(self, *, tenant_id: UUID, limit: int = 50) -> list[Session]:
        """List top-level sessions for a tenant, newest-first (Sprint 57.107).

        Excludes sidechain rows (subagent child transcripts) so the chat
        session list stays a top-level view; sidechains are reachable via
        their parent (`parent_session_id`). Tenant-scoped (multi-tenant 鐵律).
        """
        stmt = (
            select(Session)
            .where((Session.tenant_id == tenant_id) & (Session.is_sidechain.is_(False)))
            .order_by(Session.started_at.desc())
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def mark_handed_off(self, *, session_id: UUID, tenant_id: UUID) -> int:
        """Mark a session status='handed_off' (Sprint 57.68 HANDOFF).

        Tenant-scoped UPDATE (multi-tenant 鐵律): only rows in the caller's
        tenant are affected. Caller manages the transaction.

        Returns:
            Number of rows updated (0 when the session does not exist in this
            tenant — caller should treat 0 as a missing/foreign parent).
        """
        stmt = (
            update(Session)
            .where((Session.id == session_id) & (Session.tenant_id == tenant_id))
            .values(status="handed_off")
        )
        result = cast("CursorResult[Any]", await self._db.execute(stmt))
        return result.rowcount or 0


__all__ = ["SessionRepository"]
