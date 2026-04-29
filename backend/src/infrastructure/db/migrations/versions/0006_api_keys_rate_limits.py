"""api_keys + rate_limits (Sprint 49.3 Day 2.2).

Revision ID: 0006_api_keys_rate_limits
Revises: 0005_audit_log_append_only
Create Date: 2026-04-29

File: backend/src/infrastructure/db/migrations/versions/0006_api_keys_rate_limits.py
Purpose: Create api_keys + rate_limits tables per 09-db-schema-design.md L869-919.
Category: Infrastructure / Migration (Phase 49 Foundation)
Scope: Sprint 49.3 Day 2.2

Tables:
    1. api_keys
       - Tenant external API auth (bcrypt hash of full key + display prefix)
       - Indexes: ix_api_keys_tenant_id (mixin) + idx_api_keys_active (partial
         WHERE status='active') + idx_api_keys_prefix
    2. rate_limits
       - Per-tenant per-resource per-window quota counter
       - UNIQUE(tenant_id, resource_type, window_type, window_start)
       - Index: idx_rate_limits_lookup (tenant, resource, window_end DESC)

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.3 Day 2.2)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006_api_keys_rate_limits"
down_revision: Union[str, None] = "0005_audit_log_append_only"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create api_keys + rate_limits tables + indexes."""

    # ----- api_keys ----------------------------------------------------
    op.create_table(
        "api_keys",
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
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("key_prefix", sa.String(16), nullable=False),
        sa.Column("key_hash", sa.String(128), nullable=False),
        sa.Column(
            "permissions",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "rate_limit_tier",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'standard'"),
        ),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_api_keys_tenant_id", "api_keys", ["tenant_id"])
    op.create_index(
        "idx_api_keys_active",
        "api_keys",
        ["status"],
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_index("idx_api_keys_prefix", "api_keys", ["key_prefix"])

    # ----- rate_limits -------------------------------------------------
    op.create_table(
        "rate_limits",
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
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("window_type", sa.String(32), nullable=False),
        sa.Column("quota", sa.Integer, nullable=False),
        sa.Column("used", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "resource_type",
            "window_type",
            "window_start",
            name="uq_rate_limits_tenant_window",
        ),
    )
    op.create_index("ix_rate_limits_tenant_id", "rate_limits", ["tenant_id"])
    # DESC index on window_end — raw SQL since op.create_index doesn't take ORDER BY in cols
    op.execute(
        "CREATE INDEX idx_rate_limits_lookup ON rate_limits "
        "(tenant_id, resource_type, window_end DESC)"
    )


def downgrade() -> None:
    """Drop in reverse order."""
    op.execute("DROP INDEX IF EXISTS idx_rate_limits_lookup")
    op.drop_index("ix_rate_limits_tenant_id", table_name="rate_limits")
    op.drop_table("rate_limits")

    op.drop_index("idx_api_keys_prefix", table_name="api_keys")
    op.drop_index("idx_api_keys_active", table_name="api_keys")
    op.drop_index("ix_api_keys_tenant_id", table_name="api_keys")
    op.drop_table("api_keys")
