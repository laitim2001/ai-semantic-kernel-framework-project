"""Governance — approvals + risk_assessments + guardrail_events (Sprint 49.3 Day 3.4).

Revision ID: 0008_governance
Revises: 0007_memory_layers
Create Date: 2026-04-29

File: backend/src/infrastructure/db/migrations/versions/0008_governance.py
Purpose: Create 3 governance tables per 09-db-schema-design.md L562-648.
Category: Infrastructure / Migration (Phase 49 Foundation)
Scope: Sprint 49.3 Day 3.4

Tables:
    approvals          — HITL audit (state machine pending/approved/rejected/expired)
    risk_assessments   — Pre-action risk scoring
    guardrail_events   — Per-check log (input/output/tool/tripwire)

All 3 are junction-via-session (no direct tenant_id; tenant via session chain).
guardrail_events.session_id is NULLABLE for pre-session input layer.

Indexes (7 total):
    approvals: idx_approvals_status + idx_approvals_session + idx_approvals_pending (partial)
    risk_assessments: idx_risk_session
    guardrail_events: idx_guardrail_events_session + idx_guardrail_events_layer
                      + idx_guardrail_events_failed (partial)

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.3 Day 3.4)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0008_governance"
down_revision: Union[str, None] = "0007_memory_layers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create 3 governance tables + 7 indexes."""

    # ----- approvals --------------------------------------------------
    op.create_table(
        "approvals",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("action_summary", sa.Text, nullable=False),
        sa.Column("action_payload", postgresql.JSONB, nullable=False),
        sa.Column("risk_level", sa.String(32), nullable=False),
        sa.Column("risk_score", sa.Numeric(3, 2), nullable=True),
        sa.Column("risk_reasoning", sa.Text, nullable=True),
        sa.Column("required_approver_role", sa.String(64), nullable=True),
        sa.Column(
            "approver_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("decision_reason", sa.Text, nullable=True),
        sa.Column(
            "teams_notification_sent",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column("teams_message_id", sa.String(256), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_approvals_status", "approvals", ["status"])
    op.create_index("idx_approvals_session", "approvals", ["session_id"])
    op.create_index(
        "idx_approvals_pending",
        "approvals",
        ["created_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )

    # ----- risk_assessments -------------------------------------------
    op.create_table(
        "risk_assessments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tool_call_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tool_calls.id"),
            nullable=True,
        ),
        sa.Column("risk_level", sa.String(32), nullable=False),
        sa.Column("risk_score", sa.Numeric(3, 2), nullable=False),
        sa.Column(
            "triggered_rules",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("requires_approval", sa.Boolean, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_risk_session", "risk_assessments", ["session_id"])

    # ----- guardrail_events -------------------------------------------
    op.create_table(
        "guardrail_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("layer", sa.String(32), nullable=False),
        sa.Column("check_type", sa.String(64), nullable=False),
        sa.Column("passed", sa.Boolean, nullable=False),
        sa.Column("severity", sa.String(32), nullable=True),
        sa.Column("detected_pattern", sa.Text, nullable=True),
        sa.Column("action_taken", sa.String(64), nullable=True),
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
    )
    op.create_index("idx_guardrail_events_session", "guardrail_events", ["session_id"])
    op.create_index("idx_guardrail_events_layer", "guardrail_events", ["layer"])
    op.create_index(
        "idx_guardrail_events_failed",
        "guardrail_events",
        ["created_at"],
        postgresql_where=sa.text("passed = FALSE"),
    )


def downgrade() -> None:
    """Drop in reverse order."""
    op.drop_index("idx_guardrail_events_failed", table_name="guardrail_events")
    op.drop_index("idx_guardrail_events_layer", table_name="guardrail_events")
    op.drop_index("idx_guardrail_events_session", table_name="guardrail_events")
    op.drop_table("guardrail_events")

    op.drop_index("idx_risk_session", table_name="risk_assessments")
    op.drop_table("risk_assessments")

    op.drop_index("idx_approvals_pending", table_name="approvals")
    op.drop_index("idx_approvals_session", table_name="approvals")
    op.drop_index("idx_approvals_status", table_name="approvals")
    op.drop_table("approvals")
