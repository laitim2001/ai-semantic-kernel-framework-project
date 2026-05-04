"""HITL policies — per-tenant HITLPolicy DB persistence (Sprint 55.3 / AD-Hitl-7).

Revision ID: 0013_hitl_policies
Revises: 0012_incidents
Create Date: 2026-05-04

File: backend/src/infrastructure/db/migrations/versions/0013_hitl_policies.py
Purpose: Create `hitl_policies` table per AD-Hitl-7 (Sprint 53.4 retro Q5).
    Schema columns mirror `agent_harness/_contracts/hitl.py:HITLPolicy`
    dataclass fields (auto_approve_max_risk / require_approval_min_risk /
    reviewer_groups_by_risk / sla_seconds_by_risk).

    D6 drift correction (Sprint 55.3 Day 3): plan §AD-Hitl-7 stated
    column names risk_thresholds/approver_roles/sla_seconds/escalation_chain
    that did NOT match the actual HITLPolicy dataclass fields. Schema below
    matches the dataclass directly so DBHITLPolicyStore can hydrate without
    rename/alias logic.

Category: Infrastructure / Migration (Sprint 55.3 Audit Cycle)
Scope: Sprint 55.3 Day 3 (closes AD-Hitl-7).

Tables:
    hitl_policies — per-tenant HITLPolicy override storage; UNIQUE (tenant_id)

Multi-tenant:
    tenant_id NN + FK tenants.id ON DELETE CASCADE — per 鐵律 1
    UNIQUE (tenant_id) — per-tenant single policy row (variants by category
    deferred until policy versioning is needed)

Indexes (1):
    idx_hitl_policies_tenant — tenant lookup (also satisfies UNIQUE)

CHECK constraints (2):
    hitl_policies_auto_approve_check  — auto_approve_max_risk in 4 RiskLevel values
    hitl_policies_require_approval_check — require_approval_min_risk same set

RLS policy:
    hitl_policies_tenant_isolation — USING tenant_id = current_setting('app.tenant_id')::uuid

Modification History:
    - 2026-05-04: Initial creation (Sprint 55.3 Day 3 / closes AD-Hitl-7)

Related:
    - 0012_incidents.py — pattern reference for RLS + multi-tenant
    - agent_harness/_contracts/hitl.py — HITLPolicy dataclass (single source)
    - 09-db-schema-design.md §HITL — referenced (not pre-defined; this table is new)
    - .claude/rules/multi-tenant-data.md 鐵律 1
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0013_hitl_policies"
down_revision: Union[str, None] = "0012_incidents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create hitl_policies table + index + 2 CHECK + RLS policy."""

    op.create_table(
        "hitl_policies",
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
        # Mirrors HITLPolicy.auto_approve_max_risk: RiskLevel
        sa.Column(
            "auto_approve_max_risk",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'LOW'"),
        ),
        # Mirrors HITLPolicy.require_approval_min_risk: RiskLevel
        sa.Column(
            "require_approval_min_risk",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'MEDIUM'"),
        ),
        # Mirrors HITLPolicy.reviewer_groups_by_risk: dict[RiskLevel, list[str]]
        sa.Column(
            "reviewer_groups_by_risk",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        # Mirrors HITLPolicy.sla_seconds_by_risk: dict[RiskLevel, int]
        sa.Column(
            "sla_seconds_by_risk",
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
        sa.UniqueConstraint("tenant_id", name="uq_hitl_policies_tenant"),
        sa.CheckConstraint(
            "auto_approve_max_risk IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="hitl_policies_auto_approve_check",
        ),
        sa.CheckConstraint(
            "require_approval_min_risk IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="hitl_policies_require_approval_check",
        ),
    )

    op.create_index("idx_hitl_policies_tenant", "hitl_policies", ["tenant_id"])

    # RLS policy (matches 0009_rls_policies.py / 0012_incidents.py pattern)
    op.execute("ALTER TABLE hitl_policies ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY hitl_policies_tenant_isolation ON hitl_policies "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )


def downgrade() -> None:
    """Drop policy + table (indexes auto-drop with table)."""

    op.execute("DROP POLICY IF EXISTS hitl_policies_tenant_isolation ON hitl_policies")
    op.execute("ALTER TABLE hitl_policies DISABLE ROW LEVEL SECURITY")
    op.drop_table("hitl_policies")
