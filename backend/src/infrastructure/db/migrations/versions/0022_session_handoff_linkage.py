"""session handoff linkage — sessions.handoff_parent_id self-FK (Sprint 57.68).

Revision ID: 0022_session_handoff_linkage
Revises: 0021_rate_limit_alerts
Create Date: 2026-06-02

File: backend/src/infrastructure/db/migrations/versions/0022_session_handoff_linkage.py
Purpose: Add sessions.handoff_parent_id (nullable self-FK → sessions.id) + index
    so a Cat 11 HANDOFF-booted child session links back to its parent. No RLS
    change — sessions is already an RLS / TenantScopedMixin table and adding a
    nullable column does not alter tenant scoping (check_rls_policies stays
    green). The target persona is stored in meta_data["agent_role"] (existing
    JSONB column — no schema change). status="handed_off" reuses the existing
    free-text String(32) status column (no enum / type change).
Category: Infrastructure / Migration (Cat 11 HANDOFF session-boot)
Scope: Sprint 57.68 A-3b / US-2 (platform session-boot)

Column:
    sessions.handoff_parent_id
       - UUID NULL, FK → sessions(id) ON DELETE SET NULL (parent deletion keeps
         the child but drops the dangling link).
       - Index idx_sessions_handoff_parent for handoff-chain child lookups.

No data migration: the column starts NULL for all existing rows; it is only
    populated at runtime when HandoffService.boot_handoff creates a child.

downgrade():
    Drops the index + column.

Modification History:
    - 2026-06-02: Initial creation (Sprint 57.68 A-3b / US-2 — HANDOFF linkage)

Related:
    - 0021_rate_limit_alerts.py — prior head (down_revision)
    - infrastructure/db/models/sessions.py:Session — ORM (same sprint)
    - platform_layer/handoff/service.py — writes the column at runtime
    - sprint-57-68-plan.md §3.6
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0022_session_handoff_linkage"
down_revision: Union[str, None] = "0021_rate_limit_alerts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add sessions.handoff_parent_id self-FK + index (no RLS / data change)."""
    op.add_column(
        "sessions",
        sa.Column(
            "handoff_parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_sessions_handoff_parent",
        "sessions",
        ["handoff_parent_id"],
    )


def downgrade() -> None:
    """Drop the index + column."""
    op.drop_index("idx_sessions_handoff_parent", table_name="sessions")
    op.drop_column("sessions", "handoff_parent_id")
