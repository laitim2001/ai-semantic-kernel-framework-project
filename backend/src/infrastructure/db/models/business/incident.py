"""
File: backend/src/infrastructure/db/models/business/incident.py
Purpose: Incident ORM (Phase 55.1) — production-grade incident lifecycle table.
Category: Infrastructure / ORM (Business domain — incident, per 08b §Domain 5)
Scope: Sprint 55.1 / Day 1.2
Owner: business_domain/incident owner; FK chain back to TenantScopedMixin

Description:
    First true business-table for V2 production. Maps to migration
    0012_incidents (Day 1.3). Multi-tenant via TenantScopedMixin (ten_id NN
    + FK CASCADE to tenants.id + index — per multi-tenant 鐵律 1).

    Lifecycle states:
        open → investigating → resolved → closed
    Severity:
        low / medium / high / critical
    Both stored as String(32) + DB-level CHECK constraint (project convention,
    per 0011_approvals_status_check.py + governance.Approval pattern; D2 drift
    from plan §US-1 which suggested PostgreSQL ENUM types — reverted to match
    existing schema convention).

Key Components:
    - IncidentSeverity: 4-value Python enum (mirrors CHECK constraint)
    - IncidentStatus: 4-value Python enum
    - Incident: ORM class with 5 indexes:
        idx_incidents_tenant_user
        idx_incidents_severity_status
        idx_incidents_status_created
        idx_incidents_closed_at (partial WHERE closed_at IS NOT NULL)
        idx_incidents_alert_ids (GIN on JSONB)

Created: 2026-05-04 (Sprint 55.1 Day 1)
Last Modified: 2026-05-04

Modification History:
    - 2026-05-04: Initial creation (Sprint 55.1 Day 1)

Related:
    - 08b-business-tools-spec.md §Domain 5 Incident (5 tools spec)
    - 09-db-schema-design.md (general business table conventions)
    - .claude/rules/multi-tenant-data.md 鐵律 1 (tenant_id NN + RLS)
    - infrastructure/db/base.py (Base + TenantScopedMixin)
    - migrations/versions/0012_incidents.py (creates this table)
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any
from uuid import UUID as PyUUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base, TenantScopedMixin


# =====================================================================
# Severity / Status Python enums (mirror DB CHECK constraint values)
# =====================================================================
class IncidentSeverity(str, enum.Enum):
    """Incident severity — matches CHECK constraint on incidents.severity."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, enum.Enum):
    """Incident lifecycle state — matches CHECK constraint on incidents.status."""

    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


# =====================================================================
# Incident — production incident lifecycle (per 08b §Domain 5)
# =====================================================================
class Incident(Base, TenantScopedMixin):
    """Per 08b-business-tools-spec.md §Domain 5 — incident lifecycle table.

    State machine: open → investigating → resolved → closed.
    `close()` sets closed_at = NOW() + resolution NOT NULL.
    All 5 indexes lead with tenant_id (composite) for multi-tenant query path.
    """

    __tablename__ = "incidents"

    id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    # tenant_id provided by TenantScopedMixin (NN + FK CASCADE + index)

    user_id: Mapped[PyUUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Reporting user; nullable when synthesized by automation.",
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    severity: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'high'"),
        doc="low / medium / high / critical (CHECK enforced)",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'open'"),
        doc="open / investigating / resolved / closed (CHECK enforced)",
    )

    alert_ids: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        doc="Array of linked alert ids (correlation reference).",
    )
    resolution: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Resolution note set on close().",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_incidents_tenant_id"),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="incidents_severity_check",
        ),
        CheckConstraint(
            "status IN ('open', 'investigating', 'resolved', 'closed')",
            name="incidents_status_check",
        ),
        Index("idx_incidents_tenant_user", "tenant_id", "user_id"),
        Index("idx_incidents_severity_status", "tenant_id", "severity", "status"),
        Index("idx_incidents_status_created", "tenant_id", "status", "created_at"),
        Index(
            "idx_incidents_closed_at",
            "tenant_id",
            "closed_at",
            postgresql_where=text("closed_at IS NOT NULL"),
        ),
        Index(
            "idx_incidents_alert_ids",
            "alert_ids",
            postgresql_using="gin",
        ),
    )


__all__ = ["Incident", "IncidentSeverity", "IncidentStatus"]
