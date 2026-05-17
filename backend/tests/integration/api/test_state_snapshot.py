"""
File: backend/tests/integration/api/test_state_snapshot.py
Purpose: Integration tests for GET /api/v1/sessions/{session_id}/state (Sprint 57.19 US-B3).
Category: Tests / Integration / API
Scope: Phase 57 / Sprint 57.19 Day 2 / US-B3

Description:
    Verifies the Cat 7 state snapshot read endpoint:
    - Happy path: tenant A session has snapshot → returns latest version
    - Cross-tenant: tenant A session, queried as tenant B → 404
    - Not found: tenant A queries unknown session_id → 404

Created: 2026-05-17 (Sprint 57.19 Day 2 / US-B3)

Modification History (newest-first):
    - 2026-05-17: Initial creation (Sprint 57.19 Day 2 / US-B3)

Related:
    - api/v1/sessions.py
    - infrastructure/db/models/state.py
    - sprint-57-19-plan.md §US-B3
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.sessions import router as sessions_router
from infrastructure.db.models import Tenant
from infrastructure.db.models.sessions import Session as SessionORM
from infrastructure.db.models.state import StateSnapshot
from platform_layer.identity.auth import get_current_tenant
from platform_layer.middleware.tenant_context import get_db_session_with_tenant
from tests.conftest import seed_tenant, seed_user

pytestmark = pytest.mark.asyncio


async def _seed_session(db: AsyncSession, *, tenant: Tenant, user_id: UUID) -> SessionORM:
    row = SessionORM(tenant_id=tenant.id, user_id=user_id, status="active")
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def _seed_snapshot(
    db: AsyncSession,
    *,
    session: SessionORM,
    version: int,
    state_data: dict,
    parent_version: int | None = None,
) -> StateSnapshot:
    row = StateSnapshot(
        session_id=session.id,
        tenant_id=session.tenant_id,
        version=version,
        parent_version=parent_version,
        turn_num=version,
        state_data=state_data,
        state_hash=f"hash-v{version}",
        reason="test",
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


def _build_app(*, db_session: AsyncSession, tenant_id: UUID) -> FastAPI:
    app = FastAPI()
    app.include_router(sessions_router, prefix="/api/v1")

    async def _override_tenant() -> UUID:
        return tenant_id

    async def _override_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_current_tenant] = _override_tenant
    app.dependency_overrides[get_db_session_with_tenant] = _override_db
    return app


async def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ---------------------------------------------------------------------------
# happy path: returns latest version
# ---------------------------------------------------------------------------


async def test_state_snapshot_happy_path_latest_version(db_session: AsyncSession) -> None:
    tenant = await seed_tenant(db_session, code="STATE_HAPPY")
    user = await seed_user(db_session, tenant, email="state@happy.test")
    sess = await _seed_session(db_session, tenant=tenant, user_id=user.id)
    await _seed_snapshot(db_session, session=sess, version=1, state_data={"step": 1})
    await _seed_snapshot(
        db_session, session=sess, version=2, state_data={"step": 2}, parent_version=1
    )
    await _seed_snapshot(
        db_session, session=sess, version=3, state_data={"step": 3}, parent_version=2
    )

    app = _build_app(db_session=db_session, tenant_id=tenant.id)
    async with await _client(app) as ac:
        resp = await ac.get(f"/api/v1/sessions/{sess.id}/state")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["session_id"] == str(sess.id)
    assert body["tenant_id"] == str(tenant.id)
    assert body["version"] == 3  # latest
    assert body["state_data"] == {"step": 3}
    assert body["state_hash"] == "hash-v3"


# ---------------------------------------------------------------------------
# cross-tenant: 404 (not 403)
# ---------------------------------------------------------------------------


async def test_state_snapshot_cross_tenant_returns_404(db_session: AsyncSession) -> None:
    tenant_a = await seed_tenant(db_session, code="STATE_XT_A")
    tenant_b = await seed_tenant(db_session, code="STATE_XT_B")
    user_a = await seed_user(db_session, tenant_a, email="xt_a@state.test")
    sess_a = await _seed_session(db_session, tenant=tenant_a, user_id=user_a.id)
    await _seed_snapshot(db_session, session=sess_a, version=1, state_data={"only": "A"})

    # Query as tenant B for tenant A's session — multi-tenant rule: 404 not 403.
    app_b = _build_app(db_session=db_session, tenant_id=tenant_b.id)
    async with await _client(app_b) as ac:
        resp = await ac.get(f"/api/v1/sessions/{sess_a.id}/state")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# session not found: 404
# ---------------------------------------------------------------------------


async def test_state_snapshot_session_not_found_returns_404(db_session: AsyncSession) -> None:
    tenant = await seed_tenant(db_session, code="STATE_NOTF")
    app = _build_app(db_session=db_session, tenant_id=tenant.id)
    async with await _client(app) as ac:
        resp = await ac.get(f"/api/v1/sessions/{uuid4()}/state")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]
