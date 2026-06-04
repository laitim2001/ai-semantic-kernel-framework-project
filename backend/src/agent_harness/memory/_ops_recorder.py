"""
File: backend/src/agent_harness/memory/_ops_recorder.py
Purpose: Shared helper to append a memory_ops row inside the calling layer's txn.
Category: 範疇 3 (Memory)
Scope: Phase 57 / Sprint 57.76 (US-2 / US-3)

Description:
    _record_memory_op() is the single insertion point for the append-only
    memory_ops log. It is called by each DB-backed memory layer
    (user / tenant / role) on write() / evict(), inside the layer's OWN
    `async with session` block, BEFORE the layer commits.

    Risk Class C (plan §8 R1): the recorder takes the LAYER's session and only
    `session.add(...)` — it NEVER opens a new session and NEVER commits. The
    layer's existing `await session.commit()` flushes the op row in the SAME
    transaction as the underlying write/evict, so a rollback of the layer
    operation also rolls back the op row (atomic).

Key Components:
    - _record_memory_op(session, *, ...): build + session.add() a MemoryOp.

Created: 2026-06-04 (Sprint 57.76)
Last Modified: 2026-06-04

Modification History (newest-first):
    - 2026-06-04: Initial creation (Sprint 57.76) — shared layer ops recorder

Related:
    - infrastructure/db/models/memory.py:MemoryOp (ORM)
    - agent_harness/memory/layers/{user,tenant,role}_layer.py (callers)
    - sprint-57-76-plan.md §3.3 (layer emit; Risk C same-txn)
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.memory import MemoryOp


def _record_memory_op(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID | None,
    scope: str,
    key: str | None,
    operation: str,
    time_scale: str | None,
    value_snapshot: str | None,
    actor: str | None,
) -> None:
    """Append one MemoryOp row to the LAYER's session (same txn — Risk C).

    Does not commit; the caller's existing `session.commit()` persists this row
    atomically with the underlying write/evict.
    """
    session.add(
        MemoryOp(
            tenant_id=tenant_id,
            user_id=user_id,
            scope=scope,
            key=key,
            operation=operation,
            time_scale=time_scale,
            value_snapshot=value_snapshot,
            actor=actor,
        )
    )
