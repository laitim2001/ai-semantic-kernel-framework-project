# =============================================================================
# IPA Platform - Sprint 72: Fix user_id nullable and add FK constraint
# =============================================================================
"""Sprint 72: Fix user_id to be nullable and add foreign key to users

This migration fixes:
1. Makes user_id nullable (for guest sessions)
2. Adds foreign key constraint to users table

Revision ID: 002
Revises: 001
Create Date: 2026-01-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Fix user_id column:
    - Make nullable (for guest sessions)
    - Clean orphaned user_id references
    - Add foreign key to users table
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Get foreign keys on sessions table
    fks = inspector.get_foreign_keys("sessions")
    fk_names = [fk["name"] for fk in fks]

    # Step 1: Make user_id nullable
    # PostgreSQL: ALTER COLUMN ... DROP NOT NULL
    op.alter_column(
        "sessions",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    # Step 2: Clean orphaned user_id references before adding FK
    # Set user_id to NULL where the referenced user doesn't exist
    conn.execute(
        sa.text("""
            UPDATE sessions
            SET user_id = NULL
            WHERE user_id IS NOT NULL
            AND user_id NOT IN (SELECT id FROM users)
        """)
    )

    # Step 3: Add foreign key if not exists
    if "fk_sessions_user_id_users" not in fk_names:
        op.create_foreign_key(
            "fk_sessions_user_id_users",
            "sessions",
            "users",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """
    Revert changes:
    - Drop foreign key
    - Make user_id not nullable
    """
    # Drop foreign key first
    op.drop_constraint("fk_sessions_user_id_users", "sessions", type_="foreignkey")

    # Make user_id not nullable again
    op.alter_column(
        "sessions",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
