"""Phase 56.1 SaaS Stage 1 foundation — Tenant lifecycle Enum + progress JSONB.

Revision ID: 0014_phase56_1_saas_foundation
Revises: 0013_hitl_policies
Create Date: 2026-05-05

File: backend/src/infrastructure/db/migrations/versions/0014_phase56_1_saas_foundation.py
Purpose: Enhance `tenants` table for SaaS Stage 1 lifecycle state machine
    (per Sprint 56.1 plan §US-1, 15-saas-readiness.md §Tenant Lifecycle).

    Day 0 D1 finding: existing `class Tenant(Base)` at identity.py:67 has
    `status: String(32)` (free-form, default "active") which is repurposed
    to a typed `state: Enum(tenant_state)` Enum with 6 lifecycle values per
    plan §Architecture state machine diagram.

    D9 finding: 0 callers read `tenant.status`, so safe rename without
    backward-compat shim.

Category: Infrastructure / Migration (Sprint 56.1 SaaS Stage 1 Day 1)
Scope: Sprint 56.1 Day 1 (US-1 closure prerequisite).

Schema changes on tenants table:
    DROP idx_tenants_status (old String index)
    DROP status (String(32))
    CREATE TYPE tenant_state ENUM ('requested', 'provisioning', 'provision_failed',
        'active', 'suspended', 'archived')
    CREATE TYPE tenant_plan ENUM ('enterprise')
    ADD state tenant_state NOT NULL DEFAULT 'requested'
    ADD plan tenant_plan NOT NULL DEFAULT 'enterprise'
    ADD provisioning_progress JSONB NOT NULL DEFAULT '{}'
    ADD onboarding_progress JSONB NOT NULL DEFAULT '{}'
    CREATE idx_tenants_state ON tenants(state)

Multi-tenant: Tenant table itself is the registry root (no tenant_id).

Modification History:
    - 2026-05-05: Initial creation (Sprint 56.1 Day 1 / part of US-1)

Related:
    - 0013_hitl_policies.py — pattern reference for ENUM creation
    - infrastructure/db/models/identity.py:Tenant — ORM model (D1 enhanced)
    - sprint-56-1-plan.md §US-1 + §Technical Specifications
    - 15-saas-readiness.md §Tenant State Machine (L73-76)
    - .claude/rules/multi-tenant-data.md
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0014_phase56_1_saas_foundation"
down_revision: Union[str, None] = "0013_hitl_policies"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Lifecycle states (per sprint-56-1-plan.md §Architecture state machine).
TENANT_STATE_VALUES = (
    "requested",
    "provisioning",
    "provision_failed",
    "active",
    "suspended",
    "archived",
)

# Plan tier (Stage 1 enterprise only; basic/standard deferred to Stage 2).
TENANT_PLAN_VALUES = ("enterprise",)


def upgrade() -> None:
    """Drop old status column + index; add state/plan Enum + progress JSONB."""

    # 1. Drop old String-based status index + column.
    op.drop_index("idx_tenants_status", table_name="tenants")
    op.drop_column("tenants", "status")

    # 2. Create Postgres ENUM types.
    tenant_state_enum = postgresql.ENUM(
        *TENANT_STATE_VALUES, name="tenant_state", create_type=False
    )
    tenant_plan_enum = postgresql.ENUM(*TENANT_PLAN_VALUES, name="tenant_plan", create_type=False)
    tenant_state_enum.create(op.get_bind(), checkfirst=True)
    tenant_plan_enum.create(op.get_bind(), checkfirst=True)

    # 3. Add state column (NN, default 'requested').
    op.add_column(
        "tenants",
        sa.Column(
            "state",
            tenant_state_enum,
            nullable=False,
            server_default=sa.text("'requested'::tenant_state"),
        ),
    )

    # 4. Add plan column (NN, default 'enterprise').
    op.add_column(
        "tenants",
        sa.Column(
            "plan",
            tenant_plan_enum,
            nullable=False,
            server_default=sa.text("'enterprise'::tenant_plan"),
        ),
    )

    # 5. Add provisioning_progress JSONB (NN, default '{}').
    op.add_column(
        "tenants",
        sa.Column(
            "provisioning_progress",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    # 6. Add onboarding_progress JSONB (NN, default '{}').
    op.add_column(
        "tenants",
        sa.Column(
            "onboarding_progress",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    # 7. Create new state index.
    op.create_index("idx_tenants_state", "tenants", ["state"])


def downgrade() -> None:
    """Reverse: drop new columns + Enum types; restore status String + index."""

    # 1. Drop new index + columns.
    op.drop_index("idx_tenants_state", table_name="tenants")
    op.drop_column("tenants", "onboarding_progress")
    op.drop_column("tenants", "provisioning_progress")
    op.drop_column("tenants", "plan")
    op.drop_column("tenants", "state")

    # 2. Drop Enum types.
    tenant_state_enum = postgresql.ENUM(
        *TENANT_STATE_VALUES, name="tenant_state", create_type=False
    )
    tenant_plan_enum = postgresql.ENUM(*TENANT_PLAN_VALUES, name="tenant_plan", create_type=False)
    tenant_plan_enum.drop(op.get_bind(), checkfirst=True)
    tenant_state_enum.drop(op.get_bind(), checkfirst=True)

    # 3. Restore old String status column + index (for rollback compatibility).
    op.add_column(
        "tenants",
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
    )
    op.create_index("idx_tenants_status", "tenants", ["status"])
