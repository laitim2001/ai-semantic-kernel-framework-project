"""Sprint 56.1 Day 3 — feature_flags global registry table (US-4).

Revision ID: 0015_feature_flags
Revises: 0014_phase56_1_saas_foundation
Create Date: 2026-05-06

File: backend/src/infrastructure/db/migrations/versions/0015_feature_flags.py
Purpose: Add `feature_flags` global registry table with per-tenant
    overrides stored in JSONB.

Multi-tenant rule deviation note:
    `feature_flags` is a *registry* / *configuration* table (analogous to
    `tools_registry`), NOT a business table. It does NOT carry a
    `tenant_id` column and is NOT under RLS. Per-tenant overrides are
    encoded in `tenant_overrides JSONB` (dict[str(tenant_uuid), bool]).

    Rationale: every tenant queries the same flag registry to learn
    "is feature X enabled for me?". Adding tenant_id would force one row
    per (flag, tenant) pair (~ N × T rows) without adding isolation
    benefit; JSONB keeps the canonical flag list global + lets us audit
    per-flag changes via the existing audit_log chain (call site:
    `core.feature_flags.FeatureFlagsService.set_tenant_override` ->
    `infrastructure.db.audit_helper.append_audit`).

Modification History:
    - 2026-05-06: Initial creation (Sprint 56.1 Day 3 / US-4)

Related:
    - infrastructure/db/models/feature_flag.py — ORM
    - core/feature_flags.py — FeatureFlagsService
    - sprint-56-1-plan.md §US-4 + checklist 3.4
    - .claude/rules/multi-tenant-data.md (registry table exception)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0015_feature_flags"
down_revision: Union[str, None] = "0014_phase56_1_saas_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create feature_flags global registry table."""

    op.create_table(
        "feature_flags",
        sa.Column("name", sa.String(128), primary_key=True),
        sa.Column(
            "default_enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "tenant_overrides",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("description", sa.Text, nullable=True),
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


def downgrade() -> None:
    """Drop feature_flags table."""

    op.drop_table("feature_flags")
