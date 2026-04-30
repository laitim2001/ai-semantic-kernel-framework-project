"""
File: backend/src/infrastructure/db/audit_helper.py
Purpose: Audit log hash chain helpers (compute_audit_hash + append_audit).
Category: Infrastructure / DB helper (governance support)
Scope: Sprint 49.3 (Day 1.4 - audit hash chain helpers)
Owner: infrastructure/db owner

Description:
    Stand-alone helpers around the AuditLog ORM that:
        1. compute_audit_hash — canonical SHA-256 over a row's content
           (deterministic across processes; sort_keys + tight separators).
        2. append_audit — fetches latest row_hash for the tenant, computes
           the next hash, INSERTs. Caller manages the surrounding
           transaction.

    The hash chain definition matches 09-db-schema-design.md L675-680:
        previous_log_hash := current_log_hash of the previous row in the
                             SAME tenant (sentinel '0' * 64 for first row).
        current_log_hash  := SHA-256(previous_log_hash
                                     || canonical_json(operation_data)
                                     || tenant_id
                                     || timestamp_ms)

    "Same tenant" matters: hash chains are per-tenant so cross-tenant
    insertions cannot break each other's chain.

    The append-only DB trigger guarantees no row can be modified after
    insertion; the chain prevents silent storage-layer tampering.

Created: 2026-04-29 (Sprint 49.3 Day 1.4)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.3 Day 1.4)

Related:
    - 09-db-schema-design.md Group 7 Audit (L654-717)
    - 14-security-deep-dive.md §append-only / hash chain
    - infrastructure/db/models/audit.py (AuditLog ORM)
    - sprint-49-3-plan.md §1 Audit Log Append-Only 機制
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any
from uuid import UUID as PyUUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.audit import AuditLog

# Sentinel for the first row in a tenant's chain.
SENTINEL_HASH = "0" * 64


def compute_audit_hash(
    *,
    previous_log_hash: str,
    operation_data: dict[str, Any],
    tenant_id: PyUUID,
    timestamp_ms: int,
) -> str:
    """Canonical SHA-256 of (prev_hash || sorted-json(payload) || tenant_id || ts).

    Deterministic across machines/processes:
        - sort_keys=True for JSON canonicalisation
        - tight separators (",", ":") for deterministic spacing
        - UTF-8 encoding for str-to-bytes
        - tenant_id rendered as canonical UUID string

    Args:
        previous_log_hash: 64-hex SHA-256 of the previous row in this
            tenant's chain, or SENTINEL_HASH for the first row.
        operation_data: serializable JSON object to hash.
        tenant_id: tenant UUID (used as part of the digest input).
        timestamp_ms: caller-provided event time (ms since epoch).

    Returns:
        Lowercase hex SHA-256 digest (64 chars).
    """
    payload_json = json.dumps(operation_data, sort_keys=True, separators=(",", ":"))
    base = f"{previous_log_hash}{payload_json}{tenant_id}{timestamp_ms}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


async def append_audit(
    session: AsyncSession,
    *,
    tenant_id: PyUUID,
    operation: str,
    resource_type: str,
    operation_data: dict[str, Any],
    user_id: PyUUID | None = None,
    session_id: PyUUID | None = None,
    resource_id: str | None = None,
    operation_result: str | None = None,
    timestamp_ms: int | None = None,
) -> AuditLog:
    """Append a new audit row with hash chain integrity.

    Behaviour:
        - Looks up the latest row_hash for this tenant (highest id) to use
          as previous_log_hash; uses SENTINEL_HASH if none exist yet.
        - Computes current_log_hash via compute_audit_hash().
        - INSERTs new row; the caller is responsible for commit/rollback.

    Args:
        session: AsyncSession (caller manages transaction).
        tenant_id: tenant scope (TenantScopedMixin).
        operation: e.g., "tool_executed", "approval_granted".
        resource_type: e.g., "tool", "approval", "session".
        operation_data: serializable JSON detail.
        user_id: actor UUID (None for system).
        session_id: associated session (None for cross-cutting events).
        resource_id: optional human-readable resource id.
        operation_result: "success" / "failure" / "denied" (per 09.md L673).
        timestamp_ms: explicit event time; defaults to current ms.

    Returns:
        Persisted AuditLog (refreshed; id/created_at populated).
    """
    if timestamp_ms is None:
        timestamp_ms = int(time.time() * 1000)

    # Fetch most recent row_hash for this tenant (BIGSERIAL id is the
    # canonical chronological order within a tenant; selecting by tenant
    # avoids cross-tenant interference).
    latest_row = await session.execute(
        select(AuditLog.current_log_hash)
        .where(AuditLog.tenant_id == tenant_id)
        .order_by(AuditLog.id.desc())
        .limit(1)
    )
    latest_hash = latest_row.scalar_one_or_none()
    previous_log_hash = latest_hash if latest_hash is not None else SENTINEL_HASH

    current_log_hash = compute_audit_hash(
        previous_log_hash=previous_log_hash,
        operation_data=operation_data,
        tenant_id=tenant_id,
        timestamp_ms=timestamp_ms,
    )

    row = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
        operation=operation,
        resource_type=resource_type,
        resource_id=resource_id,
        operation_data=operation_data,
        operation_result=operation_result,
        previous_log_hash=previous_log_hash,
        current_log_hash=current_log_hash,
        timestamp_ms=timestamp_ms,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


__all__ = [
    "SENTINEL_HASH",
    "compute_audit_hash",
    "append_audit",
]
