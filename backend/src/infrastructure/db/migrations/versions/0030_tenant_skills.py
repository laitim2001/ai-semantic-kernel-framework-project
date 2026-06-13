"""tenant_skills — per-tenant custom Skills catalog (Sprint 57.114, Skills overlay).

Revision ID: 0030_tenant_skills
Revises: 0029_user_mfa_totp
Create Date: 2026-06-13

File: backend/src/infrastructure/db/migrations/versions/0030_tenant_skills.py
Purpose: Create the tenant_skills table — a tenant authors custom skills (name +
    description + a full instruction body) via the tenant-settings "Skills" admin
    tab; a per-request resolver (platform_layer/skills) overlays these rows on the
    bundled skill set (a same-name tenant skill shadows a bundled one). DB-backed
    (listable / per-tenant) + RLS. No data-seed (new empty table). Closes the
    schema half of AD-Skills-Per-Tenant-Catalog (US-2).
Category: Infrastructure / Migration (Sprint 57.114 — Skills System per-tenant catalog)
Scope: Sprint 57.114 / US-2

Tables:
    tenant_skills
       - tenant_id FK → tenants(id) ON DELETE CASCADE (TenantScopedMixin).
       - name VARCHAR(128) / description VARCHAR(512) / instructions TEXT (all NOT NULL).
       - UNIQUE (tenant_id, name) — at most one skill per name per tenant.
       - idx_tenant_skills_tenant (tenant_id).
       - RLS: tenant_isolation_* (USING) + tenant_insert_* (WITH CHECK) + FORCE,
         mirroring 0026_invites MINUS the system-sentinel escape — tenant_skills
         has NO guest / cross-tenant lookup (the admin endpoints + the chat resolver
         always run under a real tenant context via _set_tenant), so strict
         per-tenant isolation with no escape hatch is correct + more secure.

downgrade():
    Drops both policies + the index + the table.

Modification History:
    - 2026-06-13: Initial creation (Sprint 57.114 / US-2)

Related:
    - 0026_invites.py — two-policy RLS pattern (mirror, minus the sentinel escape)
    - infrastructure/db/models/skill.py:TenantSkill — ORM
    - platform_layer/skills/service.py — TenantSkillService + resolve_tenant_skill_registry
    - sprint-57-114-plan.md §3.2
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0030_tenant_skills"
down_revision: Union[str, None] = "0029_user_mfa_totp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create tenant_skills + index + RLS (two policies, strict per-tenant, no escape)."""

    op.create_table(
        "tenant_skills",
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
        sa.Column("description", sa.String(512), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
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
        sa.UniqueConstraint("tenant_id", "name", name="uq_tenant_skills_tenant_name"),
    )
    op.create_index("idx_tenant_skills_tenant", "tenant_skills", ["tenant_id"])

    # ----- RLS (two policies, strict per-tenant — no sentinel escape) ------
    op.execute("ALTER TABLE tenant_skills ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenant_skills FORCE ROW LEVEL SECURITY")
    # USING — SELECT / UPDATE / DELETE: strict per-tenant isolation.
    op.execute("""
        CREATE POLICY tenant_isolation_tenant_skills ON tenant_skills
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        """)
    # WITH CHECK — INSERT: rows are always written under a real tenant context.
    op.execute("""
        CREATE POLICY tenant_insert_tenant_skills ON tenant_skills
            FOR INSERT
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
        """)


def downgrade() -> None:
    """Drop RLS policies + index + table."""
    op.execute("DROP POLICY IF EXISTS tenant_insert_tenant_skills ON tenant_skills")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_tenant_skills ON tenant_skills")
    op.drop_index("idx_tenant_skills_tenant", table_name="tenant_skills")
    op.drop_table("tenant_skills")
