"""
File: backend/src/infrastructure/db/models/state.py
Purpose: State Mgmt ORM models + StateVersion 雙因子 append helper + append-only enforcement.
Category: Infrastructure / ORM (State group, per 09-db-schema-design.md Group 5)
Scope: Sprint 49.2 (Day 4.1-4.2 - state ORM + helper)
Owner: infrastructure/db owner

Description:
    Persistent state checkpoint layer for V2 範疇 7 (State Management).

    Tables:
        state_snapshots  - per-loop-turn append-only snapshots (TenantScopedMixin).
                           Append-only enforced by trigger created in migration 0004.
        loop_states      - cached current-version pointer per session.

    StateVersion 雙因子 (counter + content_hash) optimistic concurrency:
        On append, the caller provides parent_version + expected_parent_hash.
        Helper validates BOTH against the existing parent row, then INSERTs.
        Two concurrent workers writing parent_version+1 with same expected
        hash race on UNIQUE(session_id, version); one wins, the other gets
        StateConflictError so the caller can rebase.

    See sprint-49-2-plan.md §4 for the design.

Key Components:
    - StateSnapshot: append-only per-version snapshot row
    - LoopState: current-version pointer (cache)
    - compute_state_hash: SHA-256 of canonical-JSON state_data
    - append_snapshot: optimistic-concurrency append helper

Created: 2026-04-29 (Sprint 49.2 Day 4.1-4.2)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.2 Day 4.1-4.2)

Related:
    - 09-db-schema-design.md Group 5 State (L508-555)
    - sprint-49-2-plan.md §4 (StateVersion 雙因子)
    - infrastructure/db/exceptions.py (StateConflictError)
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import UUID as PyUUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base, TenantScopedMixin
from infrastructure.db.exceptions import StateConflictError


# =====================================================================
# StateSnapshot - per-turn append-only snapshot
# =====================================================================
class StateSnapshot(Base, TenantScopedMixin):
    """Append-only state snapshot. Per 09-db-schema-design.md L508-543."""

    __tablename__ = "state_snapshots"

    id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    session_id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version: Mapped[int | None] = mapped_column(Integer)

    turn_num: Mapped[int] = mapped_column(Integer, nullable=False)
    state_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    state_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("session_id", "version", name="uq_state_session_version"),
        Index("idx_state_snapshots_session", "session_id", text("version DESC")),
    )


# =====================================================================
# LoopState - current-version pointer (cache)
# =====================================================================
class LoopState(Base, TenantScopedMixin):
    """Per-session current-version pointer. Per 09-db-schema-design.md L548-555."""

    __tablename__ = "loop_states"

    session_id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    current_snapshot_id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("state_snapshots.id"),
        nullable=False,
    )
    current_version: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# =====================================================================
# Helpers
# =====================================================================
def compute_state_hash(state_data: dict[str, Any]) -> str:
    """Canonical SHA-256 of state_data (sorted-keys JSON encoding).

    Caller MUST use this same function on both write and read sides so
    parent-hash comparisons are stable across processes/python versions.
    """
    canonical = json.dumps(state_data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def append_snapshot(
    session: AsyncSession,
    *,
    session_id: PyUUID,
    tenant_id: PyUUID,
    state_data: dict[str, Any],
    turn_num: int,
    parent_version: int | None,
    expected_parent_hash: str | None,
    reason: str,
) -> StateSnapshot:
    """Append a state snapshot with StateVersion 雙因子 optimistic concurrency.

    Args:
        session: AsyncSession (caller manages transaction).
        session_id: target session UUID.
        tenant_id: tenant scope (TenantScopedMixin).
        state_data: serializable dict for state_data column.
        turn_num: loop turn number for the snapshot.
        parent_version: previous version's counter; None for first snapshot.
        expected_parent_hash: previous version's state_hash; None when parent_version is None.
        reason: short label (e.g., 'turn_end', 'hitl_pause', 'manual').

    Returns:
        Persisted StateSnapshot (refreshed; id/created_at populated).

    Raises:
        StateConflictError: if parent_version row not found, parent_hash
            mismatches, or another worker already inserted the same version
            (UNIQUE(session_id, version) violation).
    """
    new_hash = compute_state_hash(state_data)
    next_version = (parent_version or 0) + 1

    if parent_version is not None:
        if expected_parent_hash is None:
            raise StateConflictError("expected_parent_hash required when parent_version is set")
        result = await session.execute(
            select(StateSnapshot).where(
                (StateSnapshot.session_id == session_id) & (StateSnapshot.version == parent_version)
            )
        )
        parent = result.scalar_one_or_none()
        if parent is None:
            raise StateConflictError(f"parent_version={parent_version} not found for session")
        if parent.state_hash != expected_parent_hash:
            raise StateConflictError(
                f"parent_hash mismatch: expected {expected_parent_hash[:8]}..., "
                f"got {parent.state_hash[:8]}..."
            )

    snapshot = StateSnapshot(
        tenant_id=tenant_id,
        session_id=session_id,
        version=next_version,
        parent_version=parent_version,
        turn_num=turn_num,
        state_data=state_data,
        state_hash=new_hash,
        reason=reason,
    )
    session.add(snapshot)
    try:
        await session.flush()
    except IntegrityError as e:
        raise StateConflictError(f"concurrent insert: version={next_version} already taken") from e
    await session.refresh(snapshot)
    return snapshot


__all__ = [
    "StateSnapshot",
    "LoopState",
    "compute_state_hash",
    "append_snapshot",
]
