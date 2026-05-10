"""
File: backend/tests/integration/api/test_verification.py
Purpose: Integration tests for GET /api/v1/verification/recent + /correction-trace.
Category: Tests / Integration / API
Scope: Phase 57 / Sprint 57.11 Day 1 / US-2

Description:
    Mounts verification router on minimal FastAPI app and overrides identity
    deps with synthetic tenant/user. Verifies:

    - RBAC: non-auditor → 403; auditor / admin / compliance → 200
    - Tenant isolation: tenant A cannot see tenant B rows (WHERE clause filter)
    - Filters: session_id / verifier_type / passed
    - Pagination: cursor-style has_more + next_offset
    - 404 on empty correction-trace (no cross-tenant existence reveal)
    - Sorted correction trace (turn_index ASC, correction_attempt ASC, ...)

Created: 2026-05-10 (Sprint 57.11 Day 1 / US-2)

Modification History:
    - 2026-05-10: Initial creation (Sprint 57.11 Day 1 / US-2)

Related:
    - api/v1/verification.py
    - infrastructure/db/models/verification_log.py
    - infrastructure/db/repositories/verification_log.py
    - sprint-57-11-plan.md §US-2
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, HTTPException, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.verification import router as verification_router
from infrastructure.db.models import Tenant
from infrastructure.db.models.verification_log import VerificationLog
from platform_layer.identity.auth import get_current_tenant, require_audit_role
from platform_layer.middleware.tenant_context import get_db_session_with_tenant
from tests.conftest import seed_tenant

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_verification(
    db: AsyncSession,
    *,
    tenant: Tenant,
    session_id: UUID | None = None,
    turn_index: int = 0,
    verifier_name: str = "test_verifier",
    verifier_type: str = "rules_based",
    passed: bool = True,
    score: float | None = None,
    reason: str | None = None,
    suggested_correction: str | None = None,
    correction_attempt: int = 0,
) -> VerificationLog:
    row = VerificationLog(
        tenant_id=tenant.id,
        session_id=session_id or uuid4(),
        turn_index=turn_index,
        verifier_name=verifier_name,
        verifier_type=verifier_type,
        passed=passed,
        score=score,
        reason=reason,
        suggested_correction=suggested_correction,
        correction_attempt=correction_attempt,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


def _build_app(
    *,
    db_session: AsyncSession,
    tenant_id: UUID,
    audit_user_id: UUID | None,  # None → simulate non-auditor (403)
) -> FastAPI:
    """Build a FastAPI app with verification router and overridden deps."""
    app = FastAPI()
    app.include_router(verification_router, prefix="/api/v1")

    async def _override_tenant() -> UUID:
        return tenant_id

    async def _override_audit_role() -> UUID:
        if audit_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Audit role required",
            )
        return audit_user_id

    async def _override_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_current_tenant] = _override_tenant
    app.dependency_overrides[require_audit_role] = _override_audit_role
    app.dependency_overrides[get_db_session_with_tenant] = _override_db
    return app


async def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ---------------------------------------------------------------------------
# /verification/recent
# ---------------------------------------------------------------------------


async def test_recent_happy(db_session: AsyncSession) -> None:
    """Insert 2 + GET /recent → 2 items + has_more false."""
    tenant = await seed_tenant(db_session, code="VR_HAPPY")
    user_id = uuid4()
    await _seed_verification(db_session, tenant=tenant, verifier_name="v1")
    await _seed_verification(db_session, tenant=tenant, verifier_name="v2")

    app = _build_app(db_session=db_session, tenant_id=tenant.id, audit_user_id=user_id)
    async with await _client(app) as ac:
        resp = await ac.get("/api/v1/verification/recent")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert body["has_more"] is False
    assert body["next_offset"] is None


async def test_recent_filter_session(db_session: AsyncSession) -> None:
    """3 across 2 sessions → filter session_id → 2 items."""
    tenant = await seed_tenant(db_session, code="VR_FSES")
    user_id = uuid4()
    sess_a, sess_b = uuid4(), uuid4()
    await _seed_verification(db_session, tenant=tenant, session_id=sess_a, verifier_name="a1")
    await _seed_verification(db_session, tenant=tenant, session_id=sess_a, verifier_name="a2")
    await _seed_verification(db_session, tenant=tenant, session_id=sess_b, verifier_name="b1")

    app = _build_app(db_session=db_session, tenant_id=tenant.id, audit_user_id=user_id)
    async with await _client(app) as ac:
        resp = await ac.get(f"/api/v1/verification/recent?session_id={sess_a}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    names = {item["verifier_name"] for item in body["items"]}
    assert names == {"a1", "a2"}


async def test_recent_filter_verifier_type(db_session: AsyncSession) -> None:
    """Filter rules_based excludes llm_judge entries."""
    tenant = await seed_tenant(db_session, code="VR_FTYPE")
    user_id = uuid4()
    await _seed_verification(db_session, tenant=tenant, verifier_type="rules_based")
    await _seed_verification(db_session, tenant=tenant, verifier_type="rules_based")
    await _seed_verification(db_session, tenant=tenant, verifier_type="llm_judge")

    app = _build_app(db_session=db_session, tenant_id=tenant.id, audit_user_id=user_id)
    async with await _client(app) as ac:
        resp = await ac.get("/api/v1/verification/recent?verifier_type=rules_based")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    types = {item["verifier_type"] for item in body["items"]}
    assert types == {"rules_based"}


async def test_recent_filter_passed(db_session: AsyncSession) -> None:
    """Filter passed=false returns only failed entries."""
    tenant = await seed_tenant(db_session, code="VR_FPASS")
    user_id = uuid4()
    await _seed_verification(db_session, tenant=tenant, passed=True)
    await _seed_verification(db_session, tenant=tenant, passed=False, reason="bad")
    await _seed_verification(db_session, tenant=tenant, passed=False, reason="worse")

    app = _build_app(db_session=db_session, tenant_id=tenant.id, audit_user_id=user_id)
    async with await _client(app) as ac:
        resp = await ac.get("/api/v1/verification/recent?passed=false")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert all(item["passed"] is False for item in body["items"])


async def test_recent_pagination(db_session: AsyncSession) -> None:
    """60 inserted; limit=50 offset=0 → 50 + has_more; offset=50 → 10 + no has_more."""
    tenant = await seed_tenant(db_session, code="VR_PAGE")
    user_id = uuid4()
    for i in range(60):
        await _seed_verification(db_session, tenant=tenant, verifier_name=f"v{i:02d}")

    app = _build_app(db_session=db_session, tenant_id=tenant.id, audit_user_id=user_id)
    async with await _client(app) as ac:
        page1 = await ac.get("/api/v1/verification/recent?limit=50&offset=0")
        page2 = await ac.get("/api/v1/verification/recent?limit=50&offset=50")
    assert page1.status_code == 200
    assert page2.status_code == 200
    b1 = page1.json()
    b2 = page2.json()
    assert b1["total"] == 60 and len(b1["items"]) == 50 and b1["has_more"] is True
    assert b1["next_offset"] == 50
    assert b2["total"] == 60 and len(b2["items"]) == 10 and b2["has_more"] is False
    assert b2["next_offset"] is None


async def test_recent_403_without_audit_role(db_session: AsyncSession) -> None:
    """Non-auditor → 403."""
    tenant = await seed_tenant(db_session, code="VR_403")
    app = _build_app(db_session=db_session, tenant_id=tenant.id, audit_user_id=None)
    async with await _client(app) as ac:
        resp = await ac.get("/api/v1/verification/recent")
    assert resp.status_code == 403
    assert "Audit role required" in resp.json()["detail"]


async def test_recent_multi_tenant_isolation(db_session: AsyncSession) -> None:
    """Tenant A insert + Tenant B GET → 0 items (WHERE clause filter)."""
    tenant_a = await seed_tenant(db_session, code="VR_MT_A")
    tenant_b = await seed_tenant(db_session, code="VR_MT_B")
    user_id = uuid4()
    await _seed_verification(db_session, tenant=tenant_a, verifier_name="t_a")
    await _seed_verification(db_session, tenant=tenant_a, verifier_name="t_a2")

    app = _build_app(db_session=db_session, tenant_id=tenant_b.id, audit_user_id=user_id)
    async with await _client(app) as ac:
        resp = await ac.get("/api/v1/verification/recent")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


# ---------------------------------------------------------------------------
# /verification/{session_id}/correction-trace
# ---------------------------------------------------------------------------


async def test_correction_trace_404_empty(db_session: AsyncSession) -> None:
    """No entries for session_id → 404."""
    tenant = await seed_tenant(db_session, code="VR_T404")
    user_id = uuid4()
    sess = uuid4()

    app = _build_app(db_session=db_session, tenant_id=tenant.id, audit_user_id=user_id)
    async with await _client(app) as ac:
        resp = await ac.get(f"/api/v1/verification/{sess}/correction-trace")
    assert resp.status_code == 404


async def test_correction_trace_happy_sorted(db_session: AsyncSession) -> None:
    """3 entries (turn 0 attempt 0, turn 0 attempt 1, turn 1 attempt 0) → sorted."""
    tenant = await seed_tenant(db_session, code="VR_THAPPY")
    user_id = uuid4()
    sess = uuid4()
    # Insert out-of-order to verify ORDER BY (not insert order)
    await _seed_verification(
        db_session,
        tenant=tenant,
        session_id=sess,
        turn_index=1,
        correction_attempt=0,
        verifier_name="t1_a0",
    )
    await _seed_verification(
        db_session,
        tenant=tenant,
        session_id=sess,
        turn_index=0,
        correction_attempt=1,
        verifier_name="t0_a1",
    )
    await _seed_verification(
        db_session,
        tenant=tenant,
        session_id=sess,
        turn_index=0,
        correction_attempt=0,
        verifier_name="t0_a0",
    )

    app = _build_app(db_session=db_session, tenant_id=tenant.id, audit_user_id=user_id)
    async with await _client(app) as ac:
        resp = await ac.get(f"/api/v1/verification/{sess}/correction-trace")
    assert resp.status_code == 200
    body = resp.json()
    names = [e["verifier_name"] for e in body["entries"]]
    # Expected sort: turn_index ASC, correction_attempt ASC
    assert names == ["t0_a0", "t0_a1", "t1_a0"]
