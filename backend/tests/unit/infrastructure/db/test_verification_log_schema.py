"""
File: backend/tests/unit/infrastructure/db/test_verification_log_schema.py
Purpose: AC verification — verification_log ORM tablename + RLS policy presence + CHECK constraint.
Category: Tests / Infrastructure / DB / Schema verification
Scope: Sprint 57.11 Day 1 / US-1

Description:
    Verifies migration 0017_verification_log + ORM model alignment:
        1. ORM tablename = 'verification_log'
        2. VerifierType enum values match CHECK constraint values
        3. ALTER TABLE ENABLE ROW LEVEL SECURITY applied (relrowsecurity = true)
        4. Policy verification_log_tenant_isolation present
        5. 4 indexes registered (tenant_id + 3 explicit per plan)

    Live DB query (no INSERT) — schema-only inspection.

Created: 2026-05-10 (Sprint 57.11 Day 1 / US-1)
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.verification_log import VerificationLog, VerifierType


@pytest.mark.asyncio
async def test_verification_log_schema_aligns(db_session: AsyncSession) -> None:
    """Verify ORM tablename + RLS + policy + indexes + CHECK constraint."""
    # 1. ORM tablename
    assert VerificationLog.__tablename__ == "verification_log"

    # 2. VerifierType enum mirror of CHECK values
    assert {e.value for e in VerifierType} == {"rules_based", "llm_judge", "external"}

    # 3. RLS enabled at storage layer
    rls = (
        await db_session.execute(
            text("SELECT relrowsecurity FROM pg_class WHERE relname = 'verification_log'")
        )
    ).scalar()
    assert rls is True, "verification_log must have RLS enabled (relrowsecurity = true)"

    # 4. Tenant-isolation policy present
    policies = (
        await db_session.execute(
            text("SELECT polname FROM pg_policy WHERE polrelid = 'verification_log'::regclass")
        )
    ).fetchall()
    policy_names = {p[0] for p in policies}
    assert (
        "verification_log_tenant_isolation" in policy_names
    ), f"verification_log_tenant_isolation policy missing; found: {policy_names}"

    # 5. Expected indexes (4: PK + tenant_id + 3 explicit per plan)
    indexes = (
        await db_session.execute(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'verification_log' ORDER BY indexname"
            )
        )
    ).fetchall()
    index_names = {i[0] for i in indexes}
    expected = {
        "verification_log_pkey",
        "ix_verification_log_tenant_id",
        "idx_verification_log_tenant_session_created",
        "idx_verification_log_tenant_created",
        "idx_verification_log_tenant_passed_failed",
    }
    assert expected.issubset(
        index_names
    ), f"missing indexes: {expected - index_names}; found: {index_names}"

    # 6. CHECK constraint exists for verifier_type
    check_constraints = (
        await db_session.execute(
            text(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = 'verification_log'::regclass AND contype = 'c'"
            )
        )
    ).fetchall()
    constraint_names = {c[0] for c in check_constraints}
    assert (
        "ck_verification_log_verifier_type" in constraint_names
    ), f"ck_verification_log_verifier_type missing; found: {constraint_names}"
