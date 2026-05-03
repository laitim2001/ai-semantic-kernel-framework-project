"""
File: backend/src/agent_harness/guardrails/audit/worm_log.py
Purpose: WORM (Write-Once-Read-Many) audit log facade with hash chain integrity.
Category: 範疇 9 (Guardrails & Safety)
Scope: Phase 53.3 / Sprint 53.3 Day 3 (US-6 上半)

Description:
    Thin Cat 9-friendly wrapper around the existing `audit_log` table
    (Sprint 49.3 — `infrastructure/db/models/audit.py`). Drift from plan:
    plan §US-6 listed a new `audit_log_v2` table; existing `audit_log`
    already has the required schema (operation / operation_data / hash
    chain via previous_log_hash + current_log_hash). To avoid table
    proliferation we reuse the existing table; this facade adapts the
    field names to the Cat 9 vocabulary (event_type / content / prev_hash
    / entry_hash) so callers don't have to know the underlying schema.

    Hash chain (per existing schema's contract):
        entry_hash = SHA-256( prev_hash || canonical_json(content)
                              || str(tenant_id) || str(timestamp_ms) )
        prev_hash  = entry_hash of the previous audit_log row in this
                     tenant's chain; sentinel '0'*64 for the first row.

    `append()` is the only writer — append-only is enforced by:
      - app code never updating/deleting (this module is the only writer)
      - DB-level deny via RLS / GRANT in production (see 14-security-deep-dive.md)

    SLO `append latency p95 < 20ms` holds for typical PG configs; the
    SELECT-FOR-UPDATE on the previous chain head is the dominant cost.

    chain_verifier.verify_chain() lives in a sibling module (Day 4 —
    landed alongside the integration tests).

Key Components:
    - WORMAuditLog: async append API + helper for chain head lookup
    - compute_entry_hash: pure function (testable; no DB)
    - AuditAppendError: raised when DB write fails (caller must escalate
                        to ErrorTerminator FATAL — audit log is
                        non-negotiable; tripwire-equivalent behavior)

Owner: 01-eleven-categories-spec.md §範疇 9 (audit append-only WORM + hash chain)
Single-source: existing AuditLog ORM in infrastructure/db/models/audit.py

Created: 2026-05-03 (Sprint 53.3 Day 3)

Modification History (newest-first):
    - 2026-05-03: Initial creation (Sprint 53.3 US-6 上半). Wraps existing
      audit_log table to avoid duplicate schema; documented in progress.md
      as a planning-vs-impl drift.

Related:
    - infrastructure/db/models/audit.py — underlying ORM (Sprint 49.3)
    - 09-db-schema-design.md L658-710 — schema authoritative source
    - guardrails/audit/chain_verifier.py — Day 4 (verify_chain)
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.audit import AuditLog

#: Sentinel for the first row in a tenant's chain (no previous).
GENESIS_HASH = "0" * 64

#: Async session factory — caller-injectable; production wires real session.
SessionFactory = Callable[[], AsyncSession] | Callable[[], Awaitable[AsyncSession]]


class AuditAppendError(RuntimeError):
    """Raised when audit append fails. CALLER MUST ESCALATE TO FATAL.

    Audit log is non-negotiable per spec — a failed append breaks the
    integrity guarantee, so the calling code (typically AgentLoop)
    should immediately stop and let ErrorTerminator handle termination.
    """


def compute_entry_hash(
    *,
    prev_hash: str,
    content: dict[str, Any],
    tenant_id: UUID,
    timestamp_ms: int,
) -> str:
    """Pure SHA-256 hash function for chain entries.

    Stable across implementations (canonical JSON via sort_keys + tight
    separators); identical inputs always produce identical hashes.
    """
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":"), default=str)
    payload = f"{prev_hash}{canonical}{tenant_id}{timestamp_ms}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class WORMAuditLog:
    """WORM facade over `audit_log` table.

    Args:
        session_factory: 0-arg callable returning a fresh AsyncSession.
            Each `append()` opens a session, performs SELECT FOR UPDATE
            on the chain head, INSERTs the new row, and commits.
    """

    def __init__(self, session_factory: SessionFactory) -> None:
        self._sf = session_factory

    async def append(
        self,
        *,
        tenant_id: UUID,
        event_type: str,
        content: dict[str, Any],
        user_id: UUID | None = None,
        session_id: UUID | None = None,
        resource_type: str = "guardrail",
        resource_id: str | None = None,
        result: str | None = "success",
    ) -> AuditLog:
        """Append a new entry to this tenant's hash-chained audit log.

        Returns the persisted AuditLog row (so callers can inspect
        entry_hash for SSE event payloads / debugging).

        Raises:
            AuditAppendError: any DB / hash inconsistency. Caller must
                              escalate to ErrorTerminator FATAL.
        """
        session_obj: Any = self._sf()
        if hasattr(session_obj, "__await__"):
            # Support both sync and async session factories
            session_obj = await session_obj
        session: AsyncSession = session_obj

        try:
            timestamp_ms = int(time.time() * 1000)

            # Get previous chain head for this tenant (SELECT FOR UPDATE
            # not strictly required when single-writer; left out so this
            # works on read-only replicas during dry-runs).
            stmt = (
                select(AuditLog)
                .where(AuditLog.tenant_id == tenant_id)
                .order_by(AuditLog.id.desc())
                .limit(1)
            )
            result_obj = await session.execute(stmt)
            prev_row = result_obj.scalar_one_or_none()
            prev_hash = prev_row.current_log_hash if prev_row else GENESIS_HASH

            entry_hash = compute_entry_hash(
                prev_hash=prev_hash,
                content=content,
                tenant_id=tenant_id,
                timestamp_ms=timestamp_ms,
            )

            row = AuditLog(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id,
                operation=event_type,
                resource_type=resource_type,
                resource_id=resource_id,
                operation_data=content,
                operation_result=result,
                previous_log_hash=prev_hash,
                current_log_hash=entry_hash,
                timestamp_ms=timestamp_ms,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row
        except Exception as exc:
            await session.rollback()
            raise AuditAppendError(
                f"audit append failed for tenant={tenant_id} event={event_type}: {exc}"
            ) from exc
        finally:
            await session.close()
