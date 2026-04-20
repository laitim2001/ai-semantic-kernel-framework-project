"""Create session_memory table.

Sprint 172 — Phase 48: L2 session memory lands on PostgreSQL.

Replaces the Redis-only L2 cache (noted at
``integrations/memory/unified_memory.py:287``) with a durable store while
keeping Redis as a write-through cache.

Revision ID: 009_session_memory
Revises: 008_orchestration_execution_logs
Create Date: 2026-04-20
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

from alembic import op

# revision identifiers
revision: str = "009_session_memory"
down_revision: Union[str, None] = "008_orchestration_execution_logs"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "session_memory",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # External identifiers
        sa.Column("memory_id", sa.String(64), nullable=False, unique=True),
        sa.Column("user_id", sa.String(128), nullable=False),
        # Core fields
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("memory_type", sa.String(64), nullable=False),
        sa.Column(
            "importance",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.5"),
        ),
        # Access tracking (authoritative)
        sa.Column(
            "access_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("accessed_at", sa.DateTime(timezone=True), nullable=True),
        # Timestamps (from TimestampMixin)
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Expiration (replaces Redis TTL semantics)
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        # Structured metadata (column named ``extra_metadata`` to avoid
        # clash with SQLAlchemy's Base.metadata registry attribute).
        sa.Column(
            "extra_metadata",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "tags",
            ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("ARRAY[]::varchar[]"),
        ),
    )

    # Indexes for lookup + cleanup
    op.create_index(
        "ix_session_memory_user_id",
        "session_memory",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_session_memory_expires_at",
        "session_memory",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_session_memory_memory_id",
        "session_memory",
        ["memory_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_session_memory_memory_id", table_name="session_memory")
    op.drop_index("ix_session_memory_expires_at", table_name="session_memory")
    op.drop_index("ix_session_memory_user_id", table_name="session_memory")
    op.drop_table("session_memory")
