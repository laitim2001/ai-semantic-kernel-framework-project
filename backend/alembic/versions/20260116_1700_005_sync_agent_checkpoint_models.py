"""Sync agent and checkpoint models with database schema

This migration adds missing columns to match ORM model definitions:
- agents table: instructions, model_config, max_iterations
- checkpoints table: node_id, payload, response, responded_by, responded_at, expires_at, notes

Revision ID: 005_sync_models
Revises: 20260108_1655_004_fix_fullname_nullable
Create Date: 2026-01-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


# revision identifiers, used by Alembic.
revision: str = '005_sync_models'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing columns to agents and checkpoints tables."""

    # =========================================================================
    # AGENTS TABLE - Add missing columns
    # =========================================================================

    # Add instructions column (copy from code if exists)
    op.add_column('agents', sa.Column('instructions', sa.Text(), nullable=True))

    # Copy data from 'code' to 'instructions' if 'code' column exists
    op.execute("""
        UPDATE agents
        SET instructions = COALESCE(code, '')
        WHERE instructions IS NULL
    """)

    # Make instructions NOT NULL after data migration
    op.alter_column('agents', 'instructions',
                    existing_type=sa.Text(),
                    nullable=False,
                    server_default='')

    # Add model_config column (copy from config if exists)
    op.add_column('agents', sa.Column('model_config', JSONB(), nullable=True, server_default='{}'))

    # Copy data from 'config' to 'model_config' if 'config' column exists
    op.execute("""
        UPDATE agents
        SET model_config = COALESCE(config, '{}'::jsonb)
        WHERE model_config IS NULL OR model_config = '{}'::jsonb
    """)

    # Make model_config NOT NULL
    op.alter_column('agents', 'model_config',
                    existing_type=JSONB(),
                    nullable=False,
                    server_default='{}')

    # Add max_iterations column with default
    op.add_column('agents', sa.Column('max_iterations', sa.Integer(), nullable=False, server_default='10'))

    # =========================================================================
    # CHECKPOINTS TABLE - Add missing columns
    # =========================================================================

    # Add node_id column
    op.add_column('checkpoints', sa.Column('node_id', sa.String(255), nullable=True))

    # Add payload column (copy from request_data if exists)
    op.add_column('checkpoints', sa.Column('payload', JSONB(), nullable=True, server_default='{}'))

    # Copy data from request_data to payload
    op.execute("""
        UPDATE checkpoints
        SET payload = COALESCE(request_data, '{}'::jsonb)
        WHERE payload IS NULL OR payload = '{}'::jsonb
    """)

    # Add response column (copy from response_data if exists)
    op.add_column('checkpoints', sa.Column('response', JSONB(), nullable=True))

    # Copy data from response_data to response
    op.execute("""
        UPDATE checkpoints
        SET response = response_data
        WHERE response IS NULL AND response_data IS NOT NULL
    """)

    # Add responded_by column (copy from approved_by if exists)
    op.add_column('checkpoints', sa.Column('responded_by', UUID(as_uuid=True), nullable=True))

    # Copy data from approved_by to responded_by
    op.execute("""
        UPDATE checkpoints
        SET responded_by = approved_by
        WHERE responded_by IS NULL AND approved_by IS NOT NULL
    """)

    # Add foreign key constraint for responded_by (referencing users.id)
    # Note: Using conditional check since users table might not exist in all environments
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users') THEN
                ALTER TABLE checkpoints
                ADD CONSTRAINT fk_checkpoints_responded_by_users
                FOREIGN KEY (responded_by) REFERENCES users(id) ON DELETE SET NULL;
            END IF;
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # Add responded_at column
    op.add_column('checkpoints', sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True))

    # Add expires_at column (copy from timeout_at if exists)
    op.add_column('checkpoints', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))

    # Copy data from timeout_at to expires_at
    op.execute("""
        UPDATE checkpoints
        SET expires_at = timeout_at
        WHERE expires_at IS NULL AND timeout_at IS NOT NULL
    """)

    # Add notes column (copy from feedback if exists)
    op.add_column('checkpoints', sa.Column('notes', sa.Text(), nullable=True))

    # Copy data from feedback to notes
    op.execute("""
        UPDATE checkpoints
        SET notes = feedback
        WHERE notes IS NULL AND feedback IS NOT NULL
    """)


def downgrade() -> None:
    """Remove the added columns."""

    # Remove from checkpoints
    op.drop_column('checkpoints', 'notes')
    op.drop_column('checkpoints', 'expires_at')
    op.drop_column('checkpoints', 'responded_at')

    # Drop foreign key if exists
    op.execute("""
        ALTER TABLE checkpoints
        DROP CONSTRAINT IF EXISTS fk_checkpoints_responded_by_users
    """)

    op.drop_column('checkpoints', 'responded_by')
    op.drop_column('checkpoints', 'response')
    op.drop_column('checkpoints', 'payload')
    op.drop_column('checkpoints', 'node_id')

    # Remove from agents
    op.drop_column('agents', 'max_iterations')
    op.drop_column('agents', 'model_config')
    op.drop_column('agents', 'instructions')
