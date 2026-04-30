"""State snapshots (append-only) + loop_states (Sprint 49.2 Day 4.3).

Revision ID: 0004_state
Revises: 0003_tools
Create Date: 2026-04-29

File: backend/src/infrastructure/db/migrations/versions/0004_state.py
Purpose: Create state_snapshots (append-only via trigger) + loop_states + sessions FK.
Category: Infrastructure / Migration (Phase 49 Foundation)
Scope: Sprint 49.2 Day 4.3

Tables/Schema:
    1. state_snapshots
       - per-tenant, per-session append-only history
       - UNIQUE(session_id, version) for StateVersion 雙因子 race
       - DESC index for fast latest-version lookup
    2. loop_states (cache)
       - per-session current-version pointer
    3. trigger 'state_snapshots_no_update_delete'
       - Raises 'state_snapshots is append-only' on UPDATE/DELETE attempts
    4. sessions.current_state_snapshot_id
       - FK constraint added (was placeholder column in 0002)

Per 09-db-schema-design.md Group 5 State (L508-555).

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.2 Day 4.3)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004_state"
down_revision: Union[str, None] = "0003_tools"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create state_snapshots (append-only) + loop_states + sessions FK + trigger."""

    # ----- state_snapshots ---------------------------------------------
    op.create_table(
        "state_snapshots",
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
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("parent_version", sa.Integer, nullable=True),
        sa.Column("turn_num", sa.Integer, nullable=False),
        sa.Column("state_data", postgresql.JSONB, nullable=False),
        sa.Column("state_hash", sa.String(64), nullable=False),
        sa.Column("reason", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("session_id", "version", name="uq_state_session_version"),
    )
    op.create_index("ix_state_snapshots_tenant_id", "state_snapshots", ["tenant_id"])
    # DESC index — raw SQL since op.create_index doesn't take ORDER BY in cols
    op.execute(
        "CREATE INDEX idx_state_snapshots_session ON state_snapshots " "(session_id, version DESC)"
    )

    # ----- append-only trigger -----------------------------------------
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_state_snapshot_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'state_snapshots is append-only';
        END;
        $$ LANGUAGE plpgsql;
        """)
    op.execute("""
        CREATE TRIGGER state_snapshots_no_update_delete
            BEFORE UPDATE OR DELETE ON state_snapshots
            FOR EACH ROW EXECUTE FUNCTION prevent_state_snapshot_modification();
        """)

    # ----- loop_states -------------------------------------------------
    op.create_table(
        "loop_states",
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "current_snapshot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("state_snapshots.id"),
            nullable=False,
        ),
        sa.Column("current_version", sa.Integer, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_loop_states_tenant_id", "loop_states", ["tenant_id"])

    # ----- sessions.current_state_snapshot_id FK (deferred from 0002) -
    op.create_foreign_key(
        "fk_sessions_current_snapshot",
        "sessions",
        "state_snapshots",
        ["current_state_snapshot_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Drop in reverse order. Trigger + function dropped explicitly."""
    op.drop_constraint("fk_sessions_current_snapshot", "sessions", type_="foreignkey")

    op.drop_index("ix_loop_states_tenant_id", table_name="loop_states")
    op.drop_table("loop_states")

    op.execute("DROP TRIGGER IF EXISTS state_snapshots_no_update_delete ON state_snapshots")
    op.execute("DROP FUNCTION IF EXISTS prevent_state_snapshot_modification()")

    op.execute("DROP INDEX IF EXISTS idx_state_snapshots_session")
    op.drop_index("ix_state_snapshots_tenant_id", table_name="state_snapshots")
    op.drop_table("state_snapshots")
