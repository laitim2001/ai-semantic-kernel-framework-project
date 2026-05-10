"""Sprint 57.11 Day 1 — verification_log table (US-1).

Revision ID: 0017_verification_log
Revises: 0016_sla_and_cost_ledger
Create Date: 2026-05-10

File: backend/src/infrastructure/db/migrations/versions/0017_verification_log.py
Purpose: Cat 10 Verification Loops persistence — append-only verifier execution audit.

Single TenantScopedMixin table under RLS per multi-tenant 鐵律:
    verification_log (US-1): per-verifier per-attempt outcome record

Indexes:
    ix_verification_log_tenant_id                       (single col, mirrors TenantScopedMixin)
    idx_verification_log_tenant_session_created         (tenant_id, session_id, created_at)
    idx_verification_log_tenant_created                 (tenant_id, created_at)
    idx_verification_log_tenant_passed_failed           (tenant_id, created_at)
                                                        partial WHERE passed = false

RLS policy (per check_rls_policies lint — 8th V2 lint):
    verification_log_tenant_isolation
        USING (tenant_id = current_setting('app.tenant_id')::uuid)

Modification History:
    - 2026-05-10: Initial creation (Sprint 57.11 Day 1 / US-1)

Related:
    - infrastructure/db/models/verification_log.py — VerificationLog ORM
    - sprint-57-11-plan.md §US-1 (12 columns + 3 indexes + RLS)
    - .claude/rules/multi-tenant-data.md (3 鐵律 + RLS template)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0017_verification_log"
down_revision: Union[str, None] = "0016_sla_and_cost_ledger"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create verification_log table + 4 indexes + RLS policy."""

    # ----------------------------------------------------------------
    # verification_log
    # ----------------------------------------------------------------
    op.create_table(
        "verification_log",
        sa.Column(
            "id",
            sa.BigInteger,
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "turn_index",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("verifier_name", sa.String(128), nullable=False),
        sa.Column("verifier_type", sa.String(32), nullable=False),
        sa.Column("passed", sa.Boolean, nullable=False),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("suggested_correction", sa.Text, nullable=True),
        sa.Column(
            "correction_attempt",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "verifier_type IN ('rules_based', 'llm_judge', 'external')",
            name="ck_verification_log_verifier_type",
        ),
    )

    op.create_index(
        "ix_verification_log_tenant_id",
        "verification_log",
        ["tenant_id"],
    )
    op.create_index(
        "idx_verification_log_tenant_session_created",
        "verification_log",
        ["tenant_id", "session_id", "created_at"],
    )
    op.create_index(
        "idx_verification_log_tenant_created",
        "verification_log",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "idx_verification_log_tenant_passed_failed",
        "verification_log",
        ["tenant_id", "created_at"],
        postgresql_where=sa.text("passed = false"),
    )

    # ----------------------------------------------------------------
    # RLS — per check_rls_policies lint (8th V2 lint added 56.1 Day 4)
    # ----------------------------------------------------------------
    op.execute("ALTER TABLE verification_log ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY verification_log_tenant_isolation ON verification_log "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )


def downgrade() -> None:
    """Drop verification_log table (RLS / indexes drop with table)."""

    op.execute("DROP POLICY IF EXISTS verification_log_tenant_isolation ON verification_log")
    op.execute("ALTER TABLE verification_log DISABLE ROW LEVEL SECURITY")
    op.drop_table("verification_log")
