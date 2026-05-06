"""Sprint 56.3 Day 2 — sla_violations + sla_reports + cost_ledger tables (US-2 + US-3).

Revision ID: 0016_sla_and_cost_ledger
Revises: 0015_feature_flags
Create Date: 2026-05-06

File: backend/src/infrastructure/db/migrations/versions/0016_sla_and_cost_ledger.py
Purpose: Phase 56-58 SaaS Stage 1 monitoring + billing tables.

Three TenantScopedMixin tables — all under RLS per multi-tenant 鐵律:
    - sla_violations  (US-2): append-only SLA threshold breach record
    - sla_reports     (US-2): per-tenant per-month aggregate cache
    - cost_ledger     (US-3): per-tenant per-event LLM/tool/storage cost ledger

All 3 tables are indexed on tenant_id (via TenantScopedMixin) plus
domain-specific indexes for query patterns:
    sla_violations:  idx_sla_violations_tenant_detected (tenant_id, detected_at)
    sla_reports:     uq_sla_reports_tenant_month (UNIQUE tenant_id, month)
    cost_ledger:     idx_cost_ledger_tenant_recorded
                     idx_cost_ledger_tenant_cost_type
                     idx_cost_ledger_session (partial WHERE session_id NOT NULL)

RLS policies (per check_rls_policies lint — 8th V2 lint):
    sla_violations_tenant_isolation
    sla_reports_tenant_isolation
    cost_ledger_tenant_isolation

Modification History:
    - 2026-05-06: Initial creation (Sprint 56.3 Day 2 / US-2 + US-3)

Related:
    - infrastructure/db/models/sla.py — SLAViolation + SLAReport ORM
    - infrastructure/db/models/cost_ledger.py — CostLedger ORM
    - sprint-56-3-plan.md §US-2 + §US-3
    - .claude/rules/multi-tenant-data.md (3 鐵律 + RLS template)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0016_sla_and_cost_ledger"
down_revision: Union[str, None] = "0015_feature_flags"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create 3 tables + indexes + RLS policies."""

    # ----------------------------------------------------------------
    # sla_violations
    # ----------------------------------------------------------------
    op.create_table(
        "sla_violations",
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
        sa.Column("metric_type", sa.String(64), nullable=False),
        sa.Column("threshold_pct", sa.Numeric(8, 4), nullable=False),
        sa.Column("actual_pct", sa.Numeric(8, 4), nullable=False),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.UniqueConstraint("tenant_id", "id", name="uq_sla_violations_tenant_id"),
        sa.CheckConstraint(
            "metric_type IN ('availability', 'api_p99', 'loop_simple_p99', "
            "'loop_medium_p99', 'loop_complex_p99', 'hitl_queue_notif_p99')",
            name="ck_sla_violations_metric_type",
        ),
        sa.CheckConstraint(
            "severity IN ('minor', 'major', 'critical')",
            name="ck_sla_violations_severity",
        ),
    )
    op.create_index("ix_sla_violations_tenant_id", "sla_violations", ["tenant_id"])
    op.create_index(
        "idx_sla_violations_tenant_detected",
        "sla_violations",
        ["tenant_id", "detected_at"],
    )

    # ----------------------------------------------------------------
    # sla_reports
    # ----------------------------------------------------------------
    op.create_table(
        "sla_reports",
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
        sa.Column("month", sa.String(7), nullable=False),
        sa.Column(
            "availability_pct",
            sa.Numeric(8, 4),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("api_p99_ms", sa.Integer, nullable=True),
        sa.Column("loop_simple_p99_ms", sa.Integer, nullable=True),
        sa.Column("loop_medium_p99_ms", sa.Integer, nullable=True),
        sa.Column("loop_complex_p99_ms", sa.Integer, nullable=True),
        sa.Column("hitl_queue_notif_p99_ms", sa.Integer, nullable=True),
        sa.Column(
            "violations_count",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("tenant_id", "month", name="uq_sla_reports_tenant_month"),
    )
    op.create_index("ix_sla_reports_tenant_id", "sla_reports", ["tenant_id"])

    # ----------------------------------------------------------------
    # cost_ledger
    # ----------------------------------------------------------------
    op.create_table(
        "cost_ledger",
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
        sa.Column("cost_type", sa.String(32), nullable=False),
        sa.Column("sub_type", sa.String(128), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 4), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("unit_cost_usd", sa.Numeric(20, 10), nullable=False),
        sa.Column("total_cost_usd", sa.Numeric(20, 10), nullable=False),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "cost_type IN ('llm', 'tool', 'storage')",
            name="ck_cost_ledger_cost_type",
        ),
    )
    op.create_index("ix_cost_ledger_tenant_id", "cost_ledger", ["tenant_id"])
    op.create_index(
        "idx_cost_ledger_tenant_recorded",
        "cost_ledger",
        ["tenant_id", "recorded_at"],
    )
    op.create_index(
        "idx_cost_ledger_tenant_cost_type",
        "cost_ledger",
        ["tenant_id", "cost_type", "recorded_at"],
    )
    op.create_index(
        "idx_cost_ledger_session",
        "cost_ledger",
        ["session_id"],
        postgresql_where=sa.text("session_id IS NOT NULL"),
    )

    # ----------------------------------------------------------------
    # RLS — per check_rls_policies lint (8th V2 lint added 56.1 Day 4)
    # ----------------------------------------------------------------
    op.execute("ALTER TABLE sla_violations ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY sla_violations_tenant_isolation ON sla_violations "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )

    op.execute("ALTER TABLE sla_reports ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY sla_reports_tenant_isolation ON sla_reports "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )

    op.execute("ALTER TABLE cost_ledger ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY cost_ledger_tenant_isolation ON cost_ledger "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )


def downgrade() -> None:
    """Drop 3 tables (RLS / indexes drop with table)."""

    # Drop policies first (FK CASCADE clears them anyway, but explicit)
    op.execute("DROP POLICY IF EXISTS cost_ledger_tenant_isolation ON cost_ledger")
    op.execute("ALTER TABLE cost_ledger DISABLE ROW LEVEL SECURITY")
    op.drop_table("cost_ledger")

    op.execute("DROP POLICY IF EXISTS sla_reports_tenant_isolation ON sla_reports")
    op.execute("ALTER TABLE sla_reports DISABLE ROW LEVEL SECURITY")
    op.drop_table("sla_reports")

    op.execute("DROP POLICY IF EXISTS sla_violations_tenant_isolation ON sla_violations")
    op.execute("ALTER TABLE sla_violations DISABLE ROW LEVEL SECURITY")
    op.drop_table("sla_violations")
