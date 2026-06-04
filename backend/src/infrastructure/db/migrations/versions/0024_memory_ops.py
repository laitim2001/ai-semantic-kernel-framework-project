"""memory_ops — append-only memory write/evict ops log (Sprint 57.76).

Revision ID: 0024_memory_ops
Revises: 0023_agent_catalog
Create Date: 2026-06-04

File: backend/src/infrastructure/db/migrations/versions/0024_memory_ops.py
Purpose: Create the memory_ops table (append-only log of memory write/evict
    operations with a value snapshot, feeding the memory page RecentOps +
    TimeTravel widgets) + RLS policies. No data-seed (new empty log).
Category: Infrastructure / Migration (Sprint 57.76 — memory ops-history backend)
Scope: Sprint 57.76 / US-1 + US-5

Tables:
    memory_ops
       - Append-only record of a memory write/evict (user / tenant / role).
       - tenant_id FK → tenants(id) ON DELETE CASCADE (TenantScopedMixin).
       - No UNIQUE / no hash-chain (ops log, not tamper-evident audit; see
         plan §0 D-DAY0-6).
       - Index idx_memory_ops_tenant_created (tenant_id, created_at DESC) for
         the time-ordered-DESC read path.
       - RLS: BOTH tenant_isolation_* (USING) + tenant_insert_* (WITH CHECK)
         + FORCE, mirroring the 0023_agent_catalog.py two-policy pattern
         (the check_rls_policies V2 lint expects this).

downgrade():
    Drops both policies + the index + the table.

Modification History:
    - 2026-06-04: Initial creation (Sprint 57.76 / US-1 + US-5)

Related:
    - 0023_agent_catalog.py — two-policy RLS pattern (verbatim mirror)
    - infrastructure/db/models/memory.py:MemoryOp — ORM (same sprint)
    - agent_harness/memory/_ops_recorder.py — _record_memory_op (same sprint)
    - sprint-57-76-plan.md §3.1 / §3.2
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0024_memory_ops"
down_revision: Union[str, None] = "0023_agent_catalog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create memory_ops + index + RLS (two policies — 0023 pattern)."""

    # ----- memory_ops table --------------------------------------------
    op.create_table(
        "memory_ops",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scope", sa.String(32), nullable=False),
        sa.Column("key", sa.String(256), nullable=True),
        sa.Column("operation", sa.String(16), nullable=False),
        sa.Column("time_scale", sa.String(32), nullable=True),
        sa.Column("value_snapshot", sa.Text, nullable=True),
        sa.Column("actor", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    # TenantScopedMixin contributes ix_memory_ops_tenant_id; this composite
    # index serves the time-ordered-DESC read path (GET /memory/ops).
    op.create_index(
        "idx_memory_ops_tenant_created",
        "memory_ops",
        ["tenant_id", sa.text("created_at DESC")],
    )

    # ----- RLS (two policies — 0023 pattern; check_rls_policies lint) ---
    op.execute("ALTER TABLE memory_ops ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE memory_ops FORCE ROW LEVEL SECURITY")
    # USING — applies to SELECT / UPDATE / DELETE
    op.execute("""
        CREATE POLICY tenant_isolation_memory_ops ON memory_ops
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        """)
    # WITH CHECK — applies to INSERT / UPDATE row-target
    op.execute("""
        CREATE POLICY tenant_insert_memory_ops ON memory_ops
            FOR INSERT
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
        """)


def downgrade() -> None:
    """Drop RLS policies + index + table."""
    op.execute("DROP POLICY IF EXISTS tenant_insert_memory_ops ON memory_ops")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_memory_ops ON memory_ops")
    op.drop_index("idx_memory_ops_tenant_created", table_name="memory_ops")
    op.drop_table("memory_ops")
