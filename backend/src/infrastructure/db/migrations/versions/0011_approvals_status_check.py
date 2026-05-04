"""Add CHECK constraint on approvals.status (closes AD-Hitl-8).

Revision ID: 0011_approvals_status_check
Revises: 0010_pg_partman
Create Date: 2026-05-04

File: backend/src/infrastructure/db/migrations/versions/0011_approvals_status_check.py
Purpose: Add a DB-level CHECK constraint on `approvals.status` that limits
    values to the five states the application emits — `pending`, `approved`,
    `rejected`, `escalated`, `expired`. Closes AD-Hitl-8 (53.4 retrospective Q6).
Category: Infrastructure / Migration (Sprint 53.7 audit cycle)
Scope: Sprint 53.7 US-2 / Day 2.

Background:
    The `approvals` table was created by 0008_governance.py with `status` as
    a plain `String(32)` column with default `'pending'` and NO check
    constraint. The application enforces the four allowed values via the
    HITL state machine, but the database schema would silently accept any
    string -- a typo or buggy code path could persist e.g. `'approve'` or
    `'cancelled'` undetected.

    Sprint 53.4 added `escalated` as a fourth decision (in addition to the
    original `pending` / `approved` / `rejected`). 53.4 retrospective Q6
    logged AD-Hitl-8 to make the schema match the enum the application
    actually relies on.

    This is a fresh ADD (not DROP+ADD) because no prior CHECK constraint
    existed on `status`. Pre-53.7 plan §Technical Spec assumed an existing
    constraint to update; Sprint 53.7 Day 2 探勘 found there is none. The
    revised approach is simpler: ADD on upgrade / DROP IF EXISTS on
    downgrade.

What this migration DOES:
    upgrade():
        Adds named CHECK constraint `approvals_status_check` requiring
        status IN ('pending', 'approved', 'rejected', 'escalated').
    downgrade():
        Drops `approvals_status_check`. (Safe even on databases that never
        received the upgrade, thanks to IF EXISTS.)

Safety:
    - PostgreSQL >= 12: ADD CONSTRAINT with NOT VALID + VALIDATE is the
      production-safe pattern for huge tables. The `approvals` table is
      expected to stay small (HITL queue depth, not event log), so plain
      ADD CONSTRAINT (which acquires a brief AccessExclusiveLock + scans
      existing rows) is acceptable.
    - Existing rows are guaranteed to satisfy the new constraint because
      the application has only ever written one of the four values.
"""

from __future__ import annotations

from typing import Union

from alembic import op

revision: str = "0011_approvals_status_check"
down_revision: Union[str, None] = "0010_pg_partman"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE approvals ADD CONSTRAINT approvals_status_check "
        "CHECK (status IN ('pending', 'approved', 'rejected', 'escalated', 'expired'))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE approvals DROP CONSTRAINT IF EXISTS approvals_status_check")
