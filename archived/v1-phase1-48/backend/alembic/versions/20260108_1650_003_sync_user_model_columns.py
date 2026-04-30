# =============================================================================
# IPA Platform - Sprint 72: Sync User Model Columns
# =============================================================================
"""Sprint 72: Sync User Model with existing database

Rename columns to match SQLAlchemy model:
1. password_hash -> hashed_password
2. name -> full_name
3. Add last_login column

Revision ID: 003
Revises: 002
Create Date: 2026-01-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Sync users table with SQLAlchemy model:
    - Rename password_hash -> hashed_password
    - Rename name -> full_name
    - Add last_login column
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("users")]

    # Step 1: Rename password_hash to hashed_password
    if "password_hash" in columns and "hashed_password" not in columns:
        op.alter_column(
            "users",
            "password_hash",
            new_column_name="hashed_password",
        )

    # Step 2: Rename name to full_name
    if "name" in columns and "full_name" not in columns:
        op.alter_column(
            "users",
            "name",
            new_column_name="full_name",
        )

    # Step 3: Add last_login column if not exists
    columns = [col["name"] for col in inspector.get_columns("users")]
    if "last_login" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "last_login",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )


def downgrade() -> None:
    """
    Revert changes:
    - Rename hashed_password -> password_hash
    - Rename full_name -> name
    - Drop last_login column
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("users")]

    # Drop last_login
    if "last_login" in columns:
        op.drop_column("users", "last_login")

    # Rename full_name back to name
    if "full_name" in columns:
        op.alter_column(
            "users",
            "full_name",
            new_column_name="name",
        )

    # Rename hashed_password back to password_hash
    if "hashed_password" in columns:
        op.alter_column(
            "users",
            "hashed_password",
            new_column_name="password_hash",
        )
