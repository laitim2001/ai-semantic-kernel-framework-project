# =============================================================================
# IPA Platform - Sprint 72: Fix full_name nullable
# =============================================================================
"""Sprint 72: Make full_name nullable

The User model defines full_name as Optional, but the database column
was NOT NULL from the original 'name' column.

Revision ID: 004
Revises: 003
Create Date: 2026-01-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make full_name nullable to match SQLAlchemy model."""
    op.alter_column(
        "users",
        "full_name",
        existing_type=sa.String(255),
        nullable=True,
    )


def downgrade() -> None:
    """Revert: make full_name NOT NULL."""
    # First set empty values to a default
    op.execute("UPDATE users SET full_name = email WHERE full_name IS NULL")

    op.alter_column(
        "users",
        "full_name",
        existing_type=sa.String(255),
        nullable=False,
    )
