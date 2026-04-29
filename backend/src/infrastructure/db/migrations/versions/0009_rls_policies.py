"""Row-Level Security policies on 13 tenant-scoped tables (Sprint 49.3 Day 4.2).

Revision ID: 0009_rls_policies
Revises: 0008_governance
Create Date: 2026-04-29

File: backend/src/infrastructure/db/migrations/versions/0009_rls_policies.py
Purpose: Install PostgreSQL RLS policies on all tables with direct tenant_id.
Category: Infrastructure / Migration (Phase 49 Foundation - security)
Scope: Sprint 49.3 Day 4.2

Tables receiving RLS (13 — those with direct tenant_id column):
    1.  users
    2.  roles
    3.  sessions
    4.  messages           (partitioned; RLS on parent inherits to partitions per PG 11+)
    5.  message_events     (partitioned)
    6.  tool_calls
    7.  state_snapshots
    8.  loop_states
    9.  api_keys
    10. rate_limits
    11. audit_log
    12. memory_tenant
    13. memory_user

Tables NOT receiving direct RLS (junction-style; tenant via FK chain):
    user_roles / role_permissions / tool_results / memory_role /
    memory_session_summary / approvals / risk_assessments /
    guardrail_events. Application code MUST JOIN through the FK chain
    (e.g. approvals → sessions WHERE tenant_id = current). RLS on the
    upstream FK target (sessions/users/roles) prevents cross-tenant
    leakage at one hop; deeper chains rely on app-layer filtering.

Tables intentionally global (no RLS):
    tenants / tools_registry / memory_system

Per-table policy pattern:
    ALTER TABLE <t> ENABLE ROW LEVEL SECURITY;
    ALTER TABLE <t> FORCE ROW LEVEL SECURITY;  -- even table owner is forced
    CREATE POLICY tenant_isolation_<t> ON <t>
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
    CREATE POLICY tenant_insert_<t> ON <t>
        FOR INSERT
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

The `, true` second argument to current_setting makes it return NULL if
unset (instead of raising), so a query without SET LOCAL simply matches
nothing (= empty result, not error). This is the desired safety default.

pg_partman setup (49.2 deferred):
    pg_partman is NOT included in the postgres:16-alpine image used by
    docker-compose.dev.yml. Installing it requires switching to the full
    `postgres:16` image plus a custom Dockerfile, which is outside the
    Sprint 49.3 scope. Marked 🚧 carryover → Sprint 49.4 (alongside the
    image / Dockerfile / CI service refresh in 49.4 lint+infra work).

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.3 Day 4.2)
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009_rls_policies"
down_revision: Union[str, None] = "0008_governance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 13 tables with direct tenant_id; RLS applies per (1) ENABLE/FORCE
# and (2) per-table policies for SELECT/UPDATE/DELETE (USING) + INSERT (CHECK).
RLS_TABLES: tuple[str, ...] = (
    "users",
    "roles",
    "sessions",
    "messages",
    "message_events",
    "tool_calls",
    "state_snapshots",
    "loop_states",
    "api_keys",
    "rate_limits",
    "audit_log",
    "memory_tenant",
    "memory_user",
)


def upgrade() -> None:
    """Enable + force RLS and install isolation policies on 13 tables."""
    for tbl in RLS_TABLES:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY")
        # USING — applies to SELECT / UPDATE / DELETE
        op.execute(f"""
            CREATE POLICY tenant_isolation_{tbl} ON {tbl}
                USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
            """)
        # WITH CHECK — applies to INSERT / UPDATE row-target
        op.execute(f"""
            CREATE POLICY tenant_insert_{tbl} ON {tbl}
                FOR INSERT
                WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
            """)


def downgrade() -> None:
    """Drop policies and disable RLS in reverse table order."""
    for tbl in reversed(RLS_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_insert_{tbl} ON {tbl}")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{tbl} ON {tbl}")
        op.execute(f"ALTER TABLE {tbl} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY")
