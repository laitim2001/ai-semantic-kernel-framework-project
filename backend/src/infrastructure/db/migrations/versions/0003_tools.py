"""Tools registry/calls/results (Sprint 49.2 Day 3.2).

Revision ID: 0003_tools
Revises: 0002_sessions_partitioned
Create Date: 2026-04-29

File: backend/src/infrastructure/db/migrations/versions/0003_tools.py
Purpose: Create tools_registry (global) + tool_calls (per-tenant) + tool_results.
Category: Infrastructure / Migration (Phase 49 Foundation)
Scope: Sprint 49.2 Day 3.2

Tables:
    1. tools_registry  - GLOBAL (no tenant_id; shared metadata across tenants)
    2. tool_calls      - per-tenant (TenantScopedMixin); FK to sessions
    3. tool_results    - per-call (no tenant_id; tenant via FK chain)

Per 09-db-schema-design.md Group 3 (L286-380).

Notes:
    - tool_calls.message_id: NO FK to messages(id) because messages has
      composite PK (id, created_at) for partitioning. Plain UUID column.
    - tool_calls.approval_id: NO FK in 49.2; FK to approvals(id) added in
      Sprint 49.3 governance migration.

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.2 Day 3.2)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003_tools"
down_revision: Union[str, None] = "0002_sessions_partitioned"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create tools_registry / tool_calls / tool_results."""

    # ----- tools_registry (GLOBAL, no tenant_id) ----------------------
    op.create_table(
        "tools_registry",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("version", sa.String(32), nullable=False, server_default=sa.text("'1.0'")),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("input_schema", postgresql.JSONB, nullable=False),
        sa.Column("output_schema", postgresql.JSONB, nullable=False),
        sa.Column(
            "is_mutating",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column(
            "sandbox_level",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'none'"),
        ),
        sa.Column(
            "hitl_policy",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'auto'"),
        ),
        sa.Column(
            "risk_level",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'low'"),
        ),
        sa.Column("required_permission", sa.String(128), nullable=True),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
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
        sa.UniqueConstraint("name", "version", name="uq_tools_name_version"),
    )
    op.create_index(
        "idx_tools_status",
        "tools_registry",
        ["status"],
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_index("idx_tools_category", "tools_registry", ["category"])

    # ----- tool_calls (per-tenant) ------------------------------------
    op.create_table(
        "tool_calls",
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
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # message_id: no FK (messages has composite PK due to partitioning)
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tool_name", sa.String(128), nullable=False),
        sa.Column("tool_version", sa.String(32), nullable=True),
        sa.Column("arguments", postgresql.JSONB, nullable=False),
        sa.Column("permission_check_passed", sa.Boolean, nullable=False),
        # approval_id: FK added in 49.3 governance migration
        sa.Column("approval_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("sandbox_used", sa.String(32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_tool_calls_tenant_id", "tool_calls", ["tenant_id"])
    op.create_index("idx_tool_calls_session", "tool_calls", ["session_id"])
    op.create_index("idx_tool_calls_status", "tool_calls", ["status"])
    op.create_index("idx_tool_calls_tool", "tool_calls", ["tool_name"])

    # ----- tool_results (no tenant_id; via FK chain) ------------------
    op.create_table(
        "tool_results",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tool_call_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tool_calls.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "is_error",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column("result", postgresql.JSONB, nullable=False),
        sa.Column("raw_size_bytes", sa.Integer, nullable=False),
        sa.Column(
            "truncated",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_tool_results_call", "tool_results", ["tool_call_id"])


def downgrade() -> None:
    """Drop in reverse dependency order."""
    op.drop_index("idx_tool_results_call", table_name="tool_results")
    op.drop_table("tool_results")

    op.drop_index("idx_tool_calls_tool", table_name="tool_calls")
    op.drop_index("idx_tool_calls_status", table_name="tool_calls")
    op.drop_index("idx_tool_calls_session", table_name="tool_calls")
    op.drop_index("ix_tool_calls_tenant_id", table_name="tool_calls")
    op.drop_table("tool_calls")

    op.drop_index("idx_tools_category", table_name="tools_registry")
    op.drop_index("idx_tools_status", table_name="tools_registry")
    op.drop_table("tools_registry")
