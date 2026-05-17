"""
File: backend/tests/integration/api/test_subagent_registry.py
Purpose: Integration tests for GET /api/v1/subagents (Sprint 57.19 US-B4 — stub w/ carryover).
Category: Tests / Integration / API
Scope: Phase 57 / Sprint 57.19 Day 2 / US-B4

Description:
    Per Sprint 57.19 Day 0 三-prong drift D-PRE-SCHEMA-3: no Subagent ORM
    exists. This endpoint returns empty list + `not_implemented_reason`
    carryover note. Tests verify the contract shape stays stable so frontend
    can wire against it; real persistence lands in AD-Subagent-RealList-Phase58.

    - Empty list happy path: any current tenant → 200 with items=[]
    - not_implemented_reason populated (frontend will render carryover banner)
    - mode filter accepted (even though irrelevant for empty list — for forward-compat)

Created: 2026-05-17 (Sprint 57.19 Day 2 / US-B4)

Modification History (newest-first):
    - 2026-05-17: Initial creation (Sprint 57.19 Day 2 / US-B4)

Related:
    - api/v1/subagents.py
    - sprint-57-19-plan.md §US-B4
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.subagents import router as subagents_router
from platform_layer.identity.auth import get_current_tenant
from platform_layer.middleware.tenant_context import get_db_session_with_tenant

pytestmark = pytest.mark.asyncio


def _build_app(*, db_session: AsyncSession | None, tenant_id: UUID) -> FastAPI:
    app = FastAPI()
    app.include_router(subagents_router, prefix="/api/v1")

    async def _override_tenant() -> UUID:
        return tenant_id

    async def _override_db() -> AsyncIterator[AsyncSession]:
        # Stub endpoint doesn't currently hit DB, but override for future.
        assert db_session is not None
        yield db_session

    app.dependency_overrides[get_current_tenant] = _override_tenant
    if db_session is not None:
        app.dependency_overrides[get_db_session_with_tenant] = _override_db
    return app


async def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ---------------------------------------------------------------------------
# empty happy path + carryover note shape
# ---------------------------------------------------------------------------


async def test_subagents_empty_with_carryover_note(db_session: AsyncSession) -> None:
    app = _build_app(db_session=db_session, tenant_id=uuid4())
    async with await _client(app) as ac:
        resp = await ac.get("/api/v1/subagents")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["items"] == []
    assert body["next_cursor"] is None
    assert body["page_size"] == 50
    assert body["not_implemented_reason"] is not None
    assert "AD-Subagent-RealList-Phase58" in body["not_implemented_reason"]


# ---------------------------------------------------------------------------
# mode filter accepted (forward-compat contract)
# ---------------------------------------------------------------------------


async def test_subagents_mode_filter_accepted(db_session: AsyncSession) -> None:
    app = _build_app(db_session=db_session, tenant_id=uuid4())
    async with await _client(app) as ac:
        resp = await ac.get("/api/v1/subagents?mode=code")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []


# ---------------------------------------------------------------------------
# invalid mode rejected (422 Unprocessable Entity from FastAPI Literal validation)
# ---------------------------------------------------------------------------


async def test_subagents_invalid_mode_rejected(db_session: AsyncSession) -> None:
    app = _build_app(db_session=db_session, tenant_id=uuid4())
    async with await _client(app) as ac:
        resp = await ac.get("/api/v1/subagents?mode=invalid_mode")
    assert resp.status_code == 422
