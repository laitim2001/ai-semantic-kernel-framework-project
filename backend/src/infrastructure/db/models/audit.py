"""
File: backend/src/infrastructure/db/models/audit.py
Purpose: AuditLog ORM (append-only + hash chain) per 09-db-schema-design.md Group 7.
Category: Infrastructure / ORM (Audit group)
Scope: Sprint 49.3 (Day 1.1 - audit ORM)
Owner: infrastructure/db owner

Description:
    Append-only audit trail for V2 governance / compliance.

    Schema authority: 09-db-schema-design.md L654-710.

    Append-only enforcement: ROW-level UPDATE/DELETE trigger + STATEMENT-level
    TRUNCATE trigger installed by alembic migration 0005. ORM never updates
    or deletes existing rows; only INSERT is allowed by application code.

    Hash chain: each row carries
        previous_log_hash = current_log_hash of the row before it (in tenant
                            chronological order; sentinel '0' * 64 for the
                            first row in a tenant)
        current_log_hash  = SHA-256(previous_log_hash || canonical_json(payload)
                                    || tenant_id || timestamp_ms)
    Daily / batch verification (DBA process; not in this sprint) walks the
    chain to detect any tampering at the storage layer.

Key Components:
    - AuditLog: append-only ORM row, BIGSERIAL pk + TenantScopedMixin

    Helper functions (compute hash + append) live in
    `infrastructure/db/audit_helper.py` for clarity.

Created: 2026-04-29 (Sprint 49.3 Day 1.1)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.3 Day 1.1)

Related:
    - 09-db-schema-design.md Group 7 Audit (L652-717)
    - 14-security-deep-dive.md §append-only / hash chain
    - .claude/rules/multi-tenant-data.md 鐵律 1 (TenantScopedMixin)
    - sprint-49-3-plan.md §1 Audit Log Append-Only 機制
    - alembic/versions/0005_audit_log_append_only.py
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID as PyUUID

from sqlalchemy import (
    BigInteger,
    DateTime,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base, TenantScopedMixin


class AuditLog(Base, TenantScopedMixin):
    """Append-only audit row. Per 09-db-schema-design.md L658-710.

    BIGSERIAL primary key (id is int, not UUID) — single global sequence
    is acceptable because the table is append-only and not partitioned in
    the initial schema; partitioning may be added later via pg_partman.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[PyUUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        nullable=True,
        doc="Nullable for system-initiated operations.",
    )
    session_id: Mapped[PyUUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        nullable=True,
        doc="Nullable for cross-cutting operations not tied to a session.",
    )

    operation: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        doc="e.g., tool_executed / approval_granted / state_committed.",
    )
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(256), nullable=True)

    operation_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    operation_result: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        doc="success / failure / denied. Per 09-db-schema-design.md L673.",
    )

    # Hash chain integrity
    previous_log_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="SHA-256 hex of previous row in this tenant's chain; sentinel '0'*64 for first.",
    )
    current_log_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="SHA-256 hex of (previous_log_hash || canonical(operation_data) || tenant_id || ts).",
    )

    timestamp_ms: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        doc="Precise event time in milliseconds since epoch (caller-provided).",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # NOTE: TenantScopedMixin already adds index on tenant_id;
    # we add complementary indexes per 09.md L683-687.
    __table_args__ = (
        Index(
            "idx_audit_session",
            "session_id",
            postgresql_where=text("session_id IS NOT NULL"),
        ),
        Index(
            "idx_audit_user",
            "user_id",
            postgresql_where=text("user_id IS NOT NULL"),
        ),
        Index("idx_audit_operation", "operation"),
        Index("idx_audit_time", text("timestamp_ms DESC")),
    )


__all__ = ["AuditLog"]
