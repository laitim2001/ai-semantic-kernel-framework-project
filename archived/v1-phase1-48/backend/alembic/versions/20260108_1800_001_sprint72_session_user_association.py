# =============================================================================
# IPA Platform - Sprint 72: Session User Association Migration
# =============================================================================
"""Sprint 72: Add user_id FK and guest_user_id to sessions table

This migration adds:
1. user_id column with foreign key to users table (nullable for guest sessions)
2. guest_user_id column for guest user identification
3. Indexes for efficient querying

Revision ID: 001
Revises: None (initial migration for Phase 18)
Create Date: 2026-01-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Apply Sprint 72 changes:
    - Add user_id FK to sessions table (nullable)
    - Add guest_user_id column
    - Add indexes for querying
    """
    # Check if columns already exist (idempotent migration)
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Get existing columns in sessions table
    existing_columns = [col["name"] for col in inspector.get_columns("sessions")]

    # Add user_id column if not exists
    if "user_id" not in existing_columns:
        op.add_column(
            "sessions",
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )

        # Add foreign key constraint
        op.create_foreign_key(
            "fk_sessions_user_id_users",
            "sessions",
            "users",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )

        # Add index for user_id
        op.create_index(
            "ix_sessions_user_id",
            "sessions",
            ["user_id"],
        )

    # Add guest_user_id column if not exists
    if "guest_user_id" not in existing_columns:
        op.add_column(
            "sessions",
            sa.Column(
                "guest_user_id",
                sa.String(100),
                nullable=True,
            ),
        )

        # Add index for guest_user_id
        op.create_index(
            "ix_sessions_guest_user_id",
            "sessions",
            ["guest_user_id"],
        )

    # Get existing indexes
    existing_indexes = [idx["name"] for idx in inspector.get_indexes("sessions")]

    # Add composite index for user_id + status if not exists
    if "idx_sessions_user_status" not in existing_indexes:
        op.create_index(
            "idx_sessions_user_status",
            "sessions",
            ["user_id", "status"],
        )

    # Add index for guest_user_id (secondary index)
    if "idx_sessions_guest_user" not in existing_indexes:
        op.create_index(
            "idx_sessions_guest_user",
            "sessions",
            ["guest_user_id"],
        )


def downgrade() -> None:
    """
    Rollback Sprint 72 changes:
    - Remove indexes
    - Remove guest_user_id column
    - Remove user_id FK and column
    """
    # Drop indexes first
    op.drop_index("idx_sessions_guest_user", table_name="sessions")
    op.drop_index("idx_sessions_user_status", table_name="sessions")
    op.drop_index("ix_sessions_guest_user_id", table_name="sessions")
    op.drop_index("ix_sessions_user_id", table_name="sessions")

    # Drop foreign key constraint
    op.drop_constraint("fk_sessions_user_id_users", "sessions", type_="foreignkey")

    # Drop columns
    op.drop_column("sessions", "guest_user_id")
    op.drop_column("sessions", "user_id")
