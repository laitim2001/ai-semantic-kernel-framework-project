"""pg_partman extension install + ops runbook for create_parent (Sprint 49.4 Day 4.6).

Revision ID: 0010_pg_partman
Revises: 0009_rls_policies
Create Date: 2026-04-29

File: backend/src/infrastructure/db/migrations/versions/0010_pg_partman.py
Purpose: Install pg_partman extension; document create_parent ops runbook.
Category: Infrastructure / Migration (Phase 49 Foundation closeout)
Scope: Sprint 49.4 Day 4.6 — clears 49.3 retrospective Action item #1.

Background:
    Sprint 49.2 created messages / message_events as partitioned tables with
    3 manually-created monthly partitions. Sprint 49.3 audit_log is a single
    table (per 09.md L658). Sprint 49.3 carryover #1 noted that
    `postgres:16-alpine` lacks the postgresql-16-partman package, so we
    deferred extension install + automated rolling partitioning.

    Sprint 49.4 swapped the dev image to a custom postgres:16 build with
    pg_partman installed (docker/Dockerfile.postgres). This migration installs
    the extension into the database.

    create_parent() registration of messages / message_events is INTENTIONALLY
    not done in this migration:

    1. The existing partitions were created BEFORE pg_partman; running
       create_parent on a pre-partitioned table requires migrating
       existing partitions to partman naming convention. That's a one-time
       prod-data exercise, not a schema migration.
    2. Dev / CI databases recreate from scratch; there's no data loss risk
       to verify.
    3. The ops runbook below documents how to invoke create_parent in
       production when ready (typically before Phase 50.1 first prod deploy).

What this migration DOES:
    1. CREATE EXTENSION IF NOT EXISTS pg_partman
    2. (downgrade) DROP EXTENSION pg_partman

OPS RUNBOOK — create_parent for production (DO NOT include here):

    -- Run AFTER deploying postgres:16 image and applying alembic upgrade head.
    -- Run as superuser or partman owner.

    -- messages: monthly partitions, premake 6 months ahead
    SELECT partman.create_parent(
        p_parent_table => 'public.messages',
        p_control => 'created_at',
        p_type => 'native',
        p_interval => '1 month',
        p_premake => 6
    );

    -- message_events: same
    SELECT partman.create_parent(
        p_parent_table => 'public.message_events',
        p_control => 'created_at',
        p_type => 'native',
        p_interval => '1 month',
        p_premake => 6
    );

    -- audit_log is currently NOT partitioned (single table per 09.md L658).
    -- If audit volume crosses ~10M rows in prod, consider:
    --   ALTER TABLE audit_log RENAME TO audit_log_legacy;
    --   CREATE TABLE audit_log (...) PARTITION BY RANGE (created_at);
    --   SELECT partman.create_parent(...);
    --   INSERT INTO audit_log SELECT * FROM audit_log_legacy;
    -- This is OUT OF SCOPE for Sprint 49.4.

    -- pg_partman_bgw is configured in shared_preload_libraries via
    -- docker/postgres-init/10-pg-partman-shared-preload.sh. It auto-creates
    -- new partitions hourly per pg_partman_bgw.interval = 3600.

Revision graph:
    0009_rls_policies -> 0010_pg_partman -> (next sprint)
"""

from __future__ import annotations

from alembic import op

revision = "0010_pg_partman"
down_revision = "0009_rls_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_partman")


def downgrade() -> None:
    # Note: this drops the extension only; if create_parent has been called
    # in production, run partman.undo_partition() for each registered parent
    # FIRST (manual ops step) before downgrading this migration.
    op.execute("DROP EXTENSION IF EXISTS pg_partman")
