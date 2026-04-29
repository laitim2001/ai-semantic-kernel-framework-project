"""Audit log (append-only + hash chain) + state_snapshots TRUNCATE patch (Sprint 49.3 Day 1.2).

Revision ID: 0005_audit_log_append_only
Revises: 0004_state
Create Date: 2026-04-29

File: backend/src/infrastructure/db/migrations/versions/0005_audit_log_append_only.py
Purpose: Create audit_log table + append-only trigger pair + retro-fit
         state_snapshots STATEMENT-level TRUNCATE trigger (49.2 deferred).
Category: Infrastructure / Migration (Phase 49 Foundation)
Scope: Sprint 49.3 Day 1.2

Schema authority: 09-db-schema-design.md Group 7 Audit (L654-710).

Operations:
    1. CREATE TABLE audit_log (BIGSERIAL pk, tenant FK, hash chain cols).
    2. CREATE INDEXes per 09.md L683-687 (skip idx_audit_tenant since
       TenantScopedMixin already adds ix_audit_log_tenant_id).
    3. CREATE FUNCTION prevent_audit_modification().
    4. CREATE TRIGGER audit_log_no_update_delete (ROW BEFORE UPDATE OR DELETE).
    5. CREATE TRIGGER audit_log_no_truncate (STATEMENT BEFORE TRUNCATE).
    6. CREATE TRIGGER state_snapshots_no_truncate (49.2 deferred补装).

Append-only enforcement notes:
    - ROW-level trigger blocks UPDATE/DELETE on individual rows.
    - STATEMENT-level trigger blocks TRUNCATE (which is DDL-ish; ROW
      triggers do not fire).
    - Both reuse the same plpgsql function for DRY.
    - Application code MUST never UPDATE/DELETE; only INSERT.
    - DBA role separation (per 09.md L713-717 checklist) is operational
      hardening, NOT this migration's responsibility.

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.3 Day 1.2)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005_audit_log_append_only"
down_revision: Union[str, None] = "0004_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create audit_log + append-only triggers; retro-fit state_snapshots TRUNCATE."""

    # ----- audit_log ---------------------------------------------------
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("operation", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(256), nullable=True),
        sa.Column("operation_data", postgresql.JSONB, nullable=False),
        sa.Column("operation_result", sa.String(32), nullable=True),
        sa.Column("previous_log_hash", sa.String(64), nullable=False),
        sa.Column("current_log_hash", sa.String(64), nullable=False),
        sa.Column("timestamp_ms", sa.BigInteger, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_audit_log_tenant_id", "audit_log", ["tenant_id"])
    op.create_index(
        "idx_audit_session",
        "audit_log",
        ["session_id"],
        postgresql_where=sa.text("session_id IS NOT NULL"),
    )
    op.create_index(
        "idx_audit_user",
        "audit_log",
        ["user_id"],
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.create_index("idx_audit_operation", "audit_log", ["operation"])
    # DESC index — raw SQL since op.create_index doesn't take ORDER BY in cols
    op.execute("CREATE INDEX idx_audit_time ON audit_log (timestamp_ms DESC)")

    # ----- append-only function (audit_log) ---------------------------
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_audit_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log is append-only';
        END;
        $$ LANGUAGE plpgsql;
        """)
    # ROW-level trigger for UPDATE/DELETE
    op.execute("""
        CREATE TRIGGER audit_log_no_update_delete
            BEFORE UPDATE OR DELETE ON audit_log
            FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();
        """)
    # STATEMENT-level trigger for TRUNCATE (separate per 09.md L702-705)
    op.execute("""
        CREATE TRIGGER audit_log_no_truncate
            BEFORE TRUNCATE ON audit_log
            FOR EACH STATEMENT EXECUTE FUNCTION prevent_audit_modification();
        """)

    # ----- state_snapshots STATEMENT-level TRUNCATE trigger (49.2 deferred补装) ---
    # 49.2 only installed the ROW UPDATE/DELETE trigger; ROW triggers do not
    # fire on TRUNCATE. We reuse the same plpgsql function from 0004.
    op.execute("""
        CREATE TRIGGER state_snapshots_no_truncate
            BEFORE TRUNCATE ON state_snapshots
            FOR EACH STATEMENT EXECUTE FUNCTION prevent_state_snapshot_modification();
        """)


def downgrade() -> None:
    """Drop in reverse order."""

    # ----- state_snapshots TRUNCATE trigger (49.2 retro-fit) -----------
    op.execute("DROP TRIGGER IF EXISTS state_snapshots_no_truncate ON state_snapshots")

    # ----- audit_log triggers + function -------------------------------
    op.execute("DROP TRIGGER IF EXISTS audit_log_no_truncate ON audit_log")
    op.execute("DROP TRIGGER IF EXISTS audit_log_no_update_delete ON audit_log")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_modification()")

    # ----- audit_log indexes + table ----------------------------------
    op.execute("DROP INDEX IF EXISTS idx_audit_time")
    op.drop_index("idx_audit_operation", table_name="audit_log")
    op.drop_index("idx_audit_user", table_name="audit_log")
    op.drop_index("idx_audit_session", table_name="audit_log")
    op.drop_index("ix_audit_log_tenant_id", table_name="audit_log")
    op.drop_table("audit_log")
