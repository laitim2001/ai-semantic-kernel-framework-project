"""5-layer memory schema (Sprint 49.3 Day 2.4).

Revision ID: 0007_memory_layers
Revises: 0006_api_keys_rate_limits
Create Date: 2026-04-29

File: backend/src/infrastructure/db/migrations/versions/0007_memory_layers.py
Purpose: Create memory_system / memory_tenant / memory_role / memory_user /
         memory_session_summary tables per 09-db-schema-design.md L383-498.
Category: Infrastructure / Migration (Phase 49 Foundation)
Scope: Sprint 49.3 Day 2.4

Tables:
    Layer 1 memory_system           — global, no tenant
    Layer 2 memory_tenant           — TenantScopedMixin
    Layer 3 memory_role             — junction via role_id
    Layer 4 memory_user             — TenantScopedMixin + user_id
    Layer 5 memory_session_summary  — junction via session_id (UNIQUE)

Indexes (8 total per 09.md plus tenant mixins):
    memory_tenant: ix_memory_tenant_tenant_id (mixin) + idx_memory_tenant_category
    memory_role:   idx_memory_role_role
    memory_user:   ix_memory_user_tenant_id (mixin) + idx_memory_user_user
                   + idx_memory_user_category + idx_memory_user_expires (partial)

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.3 Day 2.4)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0007_memory_layers"
down_revision: Union[str, None] = "0006_api_keys_rate_limits"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create 5 memory tables + indexes."""

    # ----- Layer 1: memory_system (global) ----------------------------
    op.create_table(
        "memory_system",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("key", sa.String(256), nullable=False, unique=True),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("version", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ----- Layer 2: memory_tenant -------------------------------------
    op.create_table(
        "memory_tenant",
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
        sa.Column("key", sa.String(256), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("vector_id", sa.String(128), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("tenant_id", "key", name="uq_memory_tenant_key"),
    )
    op.create_index("ix_memory_tenant_tenant_id", "memory_tenant", ["tenant_id"])
    op.create_index("idx_memory_tenant_category", "memory_tenant", ["tenant_id", "category"])

    # ----- Layer 3: memory_role (junction) ----------------------------
    op.create_table(
        "memory_role",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "role_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(256), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("role_id", "key", name="uq_memory_role_key"),
    )
    op.create_index("idx_memory_role_role", "memory_role", ["role_id"])

    # ----- Layer 4: memory_user (TenantScopedMixin + user_id) ---------
    op.create_table(
        "memory_user",
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
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("vector_id", sa.String(128), nullable=True),
        sa.Column("source", sa.String(64), nullable=True),
        sa.Column(
            "source_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id"),
            nullable=True,
        ),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_memory_user_tenant_id", "memory_user", ["tenant_id"])
    op.create_index("idx_memory_user_user", "memory_user", ["user_id"])
    op.create_index("idx_memory_user_category", "memory_user", ["user_id", "category"])
    op.create_index(
        "idx_memory_user_expires",
        "memory_user",
        ["expires_at"],
        postgresql_where=sa.text("expires_at IS NOT NULL"),
    )

    # ----- Layer 5: memory_session_summary (junction) ----------------
    op.create_table(
        "memory_session_summary",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column(
            "key_decisions",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "unresolved_issues",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "extracted_to_user_memory",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column(
            "extraction_completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    """Drop in reverse order."""
    op.drop_table("memory_session_summary")

    op.drop_index("idx_memory_user_expires", table_name="memory_user")
    op.drop_index("idx_memory_user_category", table_name="memory_user")
    op.drop_index("idx_memory_user_user", table_name="memory_user")
    op.drop_index("ix_memory_user_tenant_id", table_name="memory_user")
    op.drop_table("memory_user")

    op.drop_index("idx_memory_role_role", table_name="memory_role")
    op.drop_table("memory_role")

    op.drop_index("idx_memory_tenant_category", table_name="memory_tenant")
    op.drop_index("ix_memory_tenant_tenant_id", table_name="memory_tenant")
    op.drop_table("memory_tenant")

    op.drop_table("memory_system")
