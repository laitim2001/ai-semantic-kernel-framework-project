"""sidechain_sessions — subagent transcript lineage + DEFAULT partitions (Sprint 57.107, B3).

Revision ID: 0028_sidechain_sessions
Revises: 0027_user_password_hash
Create Date: 2026-06-12

File: backend/src/infrastructure/db/migrations/versions/0028_sidechain_sessions.py
Purpose: (1) Add sidechain lineage columns to sessions (CC parentUuid/isSidechain
    borrow): a FORK/TEAMMATE subagent child persists as a sidechain session row
    nested under its parent — DISTINCT from handoff_parent_id (control transfer
    between top-level sessions). (2) Add DEFAULT partitions to the partitioned
    messages + message_events tables — migration 0002 created month partitions
    only through 2026_06 with no creation helper anywhere, so BOTH tables would
    become un-writable on 2026-07-01 (Sprint 57.107 Day-0 finding D4). A DEFAULT
    partition makes every INSERT land regardless of created_at month.
Category: Infrastructure / Migration (Sprint 57.107 — B3 subagent transcripts)
Scope: Sprint 57.107 / US-4

Columns:
    sessions.parent_session_id UUID NULL — FK sessions(id) ON DELETE SET NULL.
    sessions.is_sidechain BOOLEAN NOT NULL DEFAULT FALSE.
    + partial index idx_sessions_sidechain_parent (WHERE is_sidechain).

RLS:
    No new policy. sessions already has tenant_isolation RLS; the new columns
    inherit it. message_events DEFAULT partition inherits the parent table's
    policies (PostgreSQL partition semantics).
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0028_sidechain_sessions"
down_revision: Union[str, None] = "0027_user_password_hash"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    """Add sidechain lineage columns + DEFAULT partitions (D4 time-bomb fix)."""
    # --- sessions: sidechain lineage (CC parentUuid/isSidechain borrow) -----
    op.add_column(
        "sessions",
        sa.Column(
            "parent_session_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "sessions",
        sa.Column(
            "is_sidechain",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
    )
    op.create_index(
        "idx_sessions_sidechain_parent",
        "sessions",
        ["parent_session_id"],
        postgresql_where=sa.text("is_sidechain"),
    )

    # --- DEFAULT partitions (Day-0 D4): months only exist through 2026_06 ---
    # Without these, INSERTs into messages / message_events fail from
    # 2026-07-01 (no covering partition). DEFAULT catches all rows outside the
    # explicit month ranges; explicit month partitions can still be attached
    # later (pg_partman-style automation stays deferred per 0002 notes).
    op.execute("CREATE TABLE messages_default PARTITION OF messages DEFAULT")
    op.execute("CREATE TABLE message_events_default PARTITION OF message_events DEFAULT")


def downgrade() -> None:
    """Drop DEFAULT partitions + sidechain columns."""
    op.execute("DROP TABLE IF EXISTS message_events_default")
    op.execute("DROP TABLE IF EXISTS messages_default")
    op.drop_index("idx_sessions_sidechain_parent", table_name="sessions")
    op.drop_column("sessions", "is_sidechain")
    op.drop_column("sessions", "parent_session_id")
