"""
File: backend/tests/integration/api/test_sessions_list.py
Purpose: Integration tests for GET /api/v1/sessions (Sprint 57.107 US-3 — lineage list).
Category: Tests / Integration / API
Scope: Phase 57 / Sprint 57.107 Day 2 / US-3

Description:
    Verifies the top-level session list endpoint:
    - Happy path: newest-first + handoff lineage fields (handoff_parent_id +
      meta_data agent_role projected)
    - Sidechain rows (is_sidechain=True subagent transcripts) are excluded
    - Tenant isolation: tenant B sees none of tenant A's sessions (鐵律)
    - Empty tenant → empty list (200, not 404)

Created: 2026-06-12 (Sprint 57.107 Day 2 / US-3)

Modification History (newest-first):
    - 2026-06-12: Initial creation (Sprint 57.107 Day 2 / US-3)

Related:
    - api/v1/sessions.py (GET /sessions)
    - infrastructure/db/repositories/session_repository.py (list_sessions)
    - sprint-57-107-plan.md §3.3
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.sessions import router as sessions_router
from infrastructure.db.models import Tenant
from infrastructure.db.models.sessions import Session as SessionORM
from platform_layer.identity.auth import get_current_tenant
from platform_layer.middleware.tenant_context import get_db_session_with_tenant
from tests.conftest import seed_tenant, seed_user

pytestmark = pytest.mark.asyncio


async def _seed_session(
    db: AsyncSession,
    *,
    tenant: Tenant,
    user_id: UUID,
    title: str | None = None,
    status: str = "active",
    handoff_parent_id: UUID | None = None,
    parent_session_id: UUID | None = None,
    is_sidechain: bool = False,
    meta_data: dict | None = None,
    started_at: datetime | None = None,
) -> SessionORM:
    row = SessionORM(
        tenant_id=tenant.id,
        user_id=user_id,
        title=title,
        status=status,
        handoff_parent_id=handoff_parent_id,
        parent_session_id=parent_session_id,
        is_sidechain=is_sidechain,
    )
    if meta_data is not None:
        row.meta_data = meta_data
    if started_at is not None:
        row.started_at = started_at
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


def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_list_sessions_newest_first_with_lineage(db_session: AsyncSession) -> None:
    """Two sessions newest-first; the handoff child carries lineage fields."""
    tenant = await seed_tenant(db_session, code="SESSLIST_HAPPY")
    user = await seed_user(db_session, tenant, email="list@happy.test")
    t0 = datetime(2026, 6, 12, 10, 0, tzinfo=timezone.utc)
    parent = await _seed_session(
        db_session, tenant=tenant, user_id=user.id, title="Parent chat", started_at=t0
    )
    child = await _seed_session(
        db_session,
        tenant=tenant,
        user_id=user.id,
        title="Handoff → reviewer",
        status="active",
        handoff_parent_id=parent.id,
        meta_data={"agent_role": "reviewer"},
        started_at=t0 + timedelta(minutes=5),
    )

    app = _build_app(db_session=db_session, tenant_id=tenant.id)
    async with _client(app) as ac:
        resp = await ac.get("/api/v1/sessions")
    assert resp.status_code == 200, resp.text
    sessions = resp.json()["sessions"]
    assert [s["id"] for s in sessions] == [str(child.id), str(parent.id)]  # newest-first
    assert sessions[0]["handoff_parent_id"] == str(parent.id)
    assert sessions[0]["agent_role"] == "reviewer"
    assert sessions[1]["handoff_parent_id"] is None
    assert sessions[1]["agent_role"] is None


async def test_list_sessions_excludes_sidechains(db_session: AsyncSession) -> None:
    """Sidechain rows (subagent transcripts) never appear in the top-level list."""
    tenant = await seed_tenant(db_session, code="SESSLIST_SIDE")
    user = await seed_user(db_session, tenant, email="list@side.test")
    parent = await _seed_session(db_session, tenant=tenant, user_id=user.id, title="Top-level")
    await _seed_session(
        db_session,
        tenant=tenant,
        user_id=user.id,
        title="Subagent · fork",
        parent_session_id=parent.id,
        is_sidechain=True,
        meta_data={"mode": "fork"},
    )

    app = _build_app(db_session=db_session, tenant_id=tenant.id)
    async with _client(app) as ac:
        resp = await ac.get("/api/v1/sessions")
    assert resp.status_code == 200
    sessions = resp.json()["sessions"]
    assert [s["id"] for s in sessions] == [str(parent.id)]


async def test_list_sessions_tenant_isolation(db_session: AsyncSession) -> None:
    """Tenant B sees none of tenant A's sessions (multi-tenant 鐵律)."""
    tenant_a = await seed_tenant(db_session, code="SESSLIST_XT_A")
    tenant_b = await seed_tenant(db_session, code="SESSLIST_XT_B")
    user_a = await seed_user(db_session, tenant_a, email="xt_a@list.test")
    await _seed_session(db_session, tenant=tenant_a, user_id=user_a.id, title="A only")

    app_b = _build_app(db_session=db_session, tenant_id=tenant_b.id)
    async with _client(app_b) as ac:
        resp = await ac.get("/api/v1/sessions")
    assert resp.status_code == 200
    assert resp.json()["sessions"] == []


async def test_list_sessions_empty_tenant_returns_empty_list(db_session: AsyncSession) -> None:
    tenant = await seed_tenant(db_session, code="SESSLIST_EMPTY")
    app = _build_app(db_session=db_session, tenant_id=tenant.id)
    async with _client(app) as ac:
        resp = await ac.get("/api/v1/sessions")
    assert resp.status_code == 200
    assert resp.json()["sessions"] == []
