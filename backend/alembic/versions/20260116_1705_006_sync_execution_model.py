"""Sync execution model with database schema

This migration adds missing columns to executions table:
- result (JSONB) - copies from output_data
- triggered_by (UUID FK to users)
- updated_at (timestamp)

Revision ID: 006_sync_executions
Revises: 005_sync_models
Create Date: 2026-01-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


# revision identifiers, used by Alembic.
revision: str = '006_sync_executions'
down_revision: Union[str, None] = '005_sync_models'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing columns to executions table."""

    # Add result column (copy from output_data if exists)
    op.add_column('executions', sa.Column('result', JSONB(), nullable=True))

    # Copy data from output_data to result
    op.execute("""
        UPDATE executions
        SET result = output_data
        WHERE result IS NULL AND output_data IS NOT NULL
    """)

    # Add triggered_by column with foreign key
    op.add_column('executions', sa.Column('triggered_by', UUID(as_uuid=True), nullable=True))

    # Add foreign key constraint for triggered_by
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users') THEN
                ALTER TABLE executions
                ADD CONSTRAINT fk_executions_triggered_by_users
                FOREIGN KEY (triggered_by) REFERENCES users(id) ON DELETE SET NULL;
            END IF;
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # Add updated_at column if not exists
    op.execute("""
        DO $$
        BEGIN
            ALTER TABLE executions ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        EXCEPTION
            WHEN duplicate_column THEN NULL;
        END $$;
    """)


def downgrade() -> None:
    """Remove the added columns."""

    # Drop foreign key if exists
    op.execute("""
        ALTER TABLE executions
        DROP CONSTRAINT IF EXISTS fk_executions_triggered_by_users
    """)

    op.drop_column('executions', 'triggered_by')
    op.drop_column('executions', 'result')

    # Note: Not dropping updated_at as it may have been added elsewhere
