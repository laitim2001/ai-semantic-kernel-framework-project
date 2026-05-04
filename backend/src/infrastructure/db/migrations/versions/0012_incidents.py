"""Incidents table — Phase 55.1 first business-domain production table.

Revision ID: 0012_incidents
Revises: 0011_approvals_status_check
Create Date: 2026-05-04

File: backend/src/infrastructure/db/migrations/versions/0012_incidents.py
Purpose: Create `incidents` table per 08b-business-tools-spec.md §Domain 5.
    Multi-tenant via tenant_id NN + FK CASCADE; severity/status as String(32)
    + CHECK constraints (project convention; not PG ENUM types — D2 drift
    from plan §US-1 reverted).
Category: Infrastructure / Migration (Phase 55 Production)
Scope: Sprint 55.1 Day 1.3.

Tables:
    incidents — incident lifecycle table; 5 indexes; 2 CHECK constraints

Multi-tenant:
    tenant_id NN + FK tenants.id ON DELETE CASCADE — per 鐵律 1
    UNIQUE (tenant_id, id) — composite for multi-tenant query path

Indexes (5):
    idx_incidents_tenant_user                  — tenant scoping by user
    idx_incidents_severity_status              — list(severity=, status=) pattern
    idx_incidents_status_created               — list ordered by created_at
    idx_incidents_closed_at (partial)          — close() lookup
    idx_incidents_alert_ids (GIN on JSONB)     — alert correlation

CHECK constraints:
    incidents_severity_check  — severity IN ('low','medium','high','critical')
    incidents_status_check    — status IN ('open','investigating','resolved','closed')

RLS policy:
    incidents_tenant_isolation — USING tenant_id = current_setting('app.tenant_id')::uuid

Modification History:
    - 2026-05-04: Initial creation (Sprint 55.1 Day 1.3)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0012_incidents"
down_revision: Union[str, None] = "0011_approvals_status_check"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create incidents table + 5 indexes + 2 CHECK + RLS policy."""

    op.create_table(
        "incidents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column(
            "severity",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'high'"),
        ),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'open'"),
        ),
        sa.Column(
            "alert_ids",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("resolution", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "id", name="uq_incidents_tenant_id"),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="incidents_severity_check",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'investigating', 'resolved', 'closed')",
            name="incidents_status_check",
        ),
    )

    # tenant_id index (provided by TenantScopedMixin in ORM via index=True is
    # implicit at metadata create but Alembic requires explicit declaration).
    op.create_index("ix_incidents_tenant_id", "incidents", ["tenant_id"])

    # 5 composite/partial/GIN indexes
    op.create_index("idx_incidents_tenant_user", "incidents", ["tenant_id", "user_id"])
    op.create_index(
        "idx_incidents_severity_status",
        "incidents",
        ["tenant_id", "severity", "status"],
    )
    op.create_index(
        "idx_incidents_status_created",
        "incidents",
        ["tenant_id", "status", "created_at"],
    )
    op.create_index(
        "idx_incidents_closed_at",
        "incidents",
        ["tenant_id", "closed_at"],
        postgresql_where=sa.text("closed_at IS NOT NULL"),
    )
    op.create_index(
        "idx_incidents_alert_ids",
        "incidents",
        ["alert_ids"],
        postgresql_using="gin",
    )

    # RLS policy (matches 0009_rls_policies.py pattern)
    op.execute("ALTER TABLE incidents ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY incidents_tenant_isolation ON incidents "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )


def downgrade() -> None:
    """Drop policy + indexes + table (idempotent via IF EXISTS where supported)."""

    op.execute("DROP POLICY IF EXISTS incidents_tenant_isolation ON incidents")
    op.execute("ALTER TABLE incidents DISABLE ROW LEVEL SECURITY")

    # drop_index is idempotent only via if_exists kwarg (Alembic >=1.6); use
    # drop_constraint pattern. Indexes auto-drop with table on drop_table.
    op.drop_table("incidents")
