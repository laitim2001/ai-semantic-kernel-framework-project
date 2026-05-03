"""
File: backend/src/agent_harness/guardrails/audit/chain_verifier.py
Purpose: Walks a tenant's audit_log chain and recomputes hashes to detect tampering.
Category: 範疇 9 (Guardrails & Safety)
Scope: Phase 53.3 / Sprint 53.3 Day 4 (US-6 下半)

Description:
    Tamper detection: walks `audit_log` rows for a tenant in id-ascending
    order, recomputes each row's expected entry_hash from
    (prev_hash + canonical_json(operation_data) + tenant_id + timestamp_ms),
    and compares with the stored `current_log_hash`. The first mismatch
    pinpoints where the chain was broken.

    A tenant's chain is verifiable independently — cross-tenant tampering
    cannot affect verification of an unrelated tenant.

    Performance:
      - O(N) walk; N = rows in [from_id, to_id]
      - Memory: streams via paginated fetch (default 100 rows / page) to
        avoid loading entire chain into memory
      - For 100K-row chain on PG: typically completes in seconds; not for
        per-request hot path — use as scheduled audit job

Key Components:
    - ChainVerificationResult dataclass — frozen result with first-broken id
    - verify_chain() — async function; takes session_factory + tenant_id

Owner: 01-eleven-categories-spec.md §範疇 9 §audit_log_v2 verification
Single-source: existing audit_log schema (Sprint 49.3)

Created: 2026-05-03 (Sprint 53.3 Day 4)

Modification History (newest-first):
    - 2026-05-03: Initial creation (Sprint 53.3 US-6 下半)

Related:
    - guardrails/audit/worm_log.py — produces the chain via WORMAuditLog.append
    - infrastructure/db/models/audit.py — underlying ORM
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_harness.guardrails.audit.worm_log import GENESIS_HASH, compute_entry_hash
from infrastructure.db.models.audit import AuditLog

#: Async session factory matching WORMAuditLog's contract.
SessionFactory = Callable[[], AsyncSession] | Callable[[], Awaitable[AsyncSession]]


@dataclass(frozen=True)
class ChainVerificationResult:
    """Outcome of verify_chain.

    Attributes:
        valid: True iff every recomputed hash matches its stored counterpart.
        broken_at_id: id of the first row whose recomputed hash differs from
                       the stored value. None when valid=True.
        total_entries: count of rows examined (within from_id/to_id bounds).
    """

    valid: bool
    broken_at_id: int | None
    total_entries: int


async def verify_chain(
    session_factory: SessionFactory,
    tenant_id: UUID,
    *,
    from_id: int | None = None,
    to_id: int | None = None,
    page_size: int = 100,
) -> ChainVerificationResult:
    """Walk a tenant's audit_log chain and verify hash integrity.

    Args:
        session_factory: 0-arg callable returning a fresh AsyncSession.
        tenant_id: only this tenant's rows are inspected.
        from_id: optional inclusive lower bound (default: tenant's first row).
        to_id: optional inclusive upper bound (default: tenant's last row).
        page_size: rows per fetch (default 100; tune for memory vs round-trips).

    Returns:
        ChainVerificationResult with valid flag + broken_at_id pinpoint.
    """
    session_obj: Any = session_factory()
    if hasattr(session_obj, "__await__"):
        session_obj = await session_obj
    session: AsyncSession = session_obj

    try:
        last_seen_hash = GENESIS_HASH
        total = 0
        last_id = from_id - 1 if from_id is not None else 0

        while True:
            stmt = (
                select(AuditLog)
                .where(AuditLog.tenant_id == tenant_id)
                .where(AuditLog.id > last_id)
                .order_by(AuditLog.id.asc())
                .limit(page_size)
            )
            if to_id is not None:
                stmt = stmt.where(AuditLog.id <= to_id)

            result = await session.execute(stmt)
            rows = result.scalars().all()
            if not rows:
                break

            for row in rows:
                # 1. Verify prev_hash linkage
                if row.previous_log_hash != last_seen_hash:
                    return ChainVerificationResult(
                        valid=False,
                        broken_at_id=row.id,
                        total_entries=total + 1,
                    )

                # 2. Recompute entry_hash from row contents
                expected = compute_entry_hash(
                    prev_hash=row.previous_log_hash,
                    content=row.operation_data,
                    tenant_id=row.tenant_id,
                    timestamp_ms=row.timestamp_ms,
                )

                # 3. Compare with stored entry_hash
                if expected != row.current_log_hash:
                    return ChainVerificationResult(
                        valid=False,
                        broken_at_id=row.id,
                        total_entries=total + 1,
                    )

                last_seen_hash = row.current_log_hash
                last_id = row.id
                total += 1

            if len(rows) < page_size:
                break

        return ChainVerificationResult(
            valid=True,
            broken_at_id=None,
            total_entries=total,
        )
    finally:
        await session.close()
