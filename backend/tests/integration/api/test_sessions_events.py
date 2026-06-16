"""
File: backend/tests/integration/api/test_sessions_events.py
Purpose: Tests for GET /api/v1/sessions/{id}/events — history replay reader (Sprint 57.125).
Category: Tests / Integration / API
Scope: Phase 57 / Sprint 57.125 / US-3 (reader)

Description:
    Verifies the session event-replay endpoint:
    - Happy path: events returned ordered by sequence_num (seeded out of order)
    - Empty for a brand-new session (200 + [], not 404)
    - Cross-tenant session → 200 + [] (never 404; never reveal existence; 鐵律)
    - Unknown session id → 200 + []
    - Item shape == {type, data, sequence_num, timestamp_ms} (the 57.126 replay contract)

Created: 2026-06-16 (Sprint 57.125)

Modification History (newest-first):
    - 2026-06-16: Initial creation (Sprint 57.125 — history replay reader)

Related:
    - api/v1/sessions.py (GET /{id}/events — list_session_events)
    - api/v1/chat/router.py (_persist_main_event — the writer)
    - sprint-57-125-plan.md §3.3
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.sessions import router as sessions_router
from infrastructure.db.models import Tenant
from infrastructure.db.models.sessions import MessageEvent
from infrastructure.db.models.sessions import Session as SessionORM
from platform_layer.identity.auth import get_current_tenant
from platform_layer.middleware.tenant_context import get_db_session_with_tenant
from tests.conftest import seed_tenant, seed_user

pytestmark = pytest.mark.asyncio


async def _seed_session(db: AsyncSession, *, tenant: Tenant, user_id: UUID) -> UUID:
    sid = uuid4()
    db.add(SessionORM(id=sid, tenant_id=tenant.id, user_id=user_id, status="active"))
    await db.flush()
    return sid


async def _seed_event(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    session_id: UUID,
    event_type: str,
    seq: int,
    data: dict[str, Any] | None = None,
) -> None:
    db.add(
        MessageEvent(
            session_id=session_id,
            tenant_id=tenant_id,
            event_type=event_type,
            event_data=data if data is not None else {"k": event_type},
            sequence_num=seq,
            timestamp_ms=1000 + seq,
        )
    )
    await db.flush()


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


async def test_events_returned_ordered_by_sequence(db_session: AsyncSession) -> None:
    """Events are returned ordered by sequence_num even when inserted out of order."""
    tenant = await seed_tenant(db_session, code="SESSEV_ORD")
    user = await seed_user(db_session, tenant, email="ev@ord.test")
    sid = await _seed_session(db_session, tenant=tenant, user_id=user.id)
    await _seed_event(db_session, tenant_id=tenant.id, session_id=sid, event_type="loop_end", seq=3)
    await _seed_event(
        db_session,
        tenant_id=tenant.id,
        session_id=sid,
        event_type="turn_start",
        seq=1,
        data={"turn_num": 0},
    )
    await _seed_event(
        db_session, tenant_id=tenant.id, session_id=sid, event_type="llm_request", seq=2
    )

    app = _build_app(db_session=db_session, tenant_id=tenant.id)
    async with _client(app) as ac:
        resp = await ac.get(f"/api/v1/sessions/{sid}/events")
    assert resp.status_code == 200, resp.text
    events = resp.json()["events"]
    assert [e["sequence_num"] for e in events] == [1, 2, 3]
    assert [e["type"] for e in events] == ["turn_start", "llm_request", "loop_end"]
    # Item shape == the 57.126 replay contract.
    assert events[0]["data"]["turn_num"] == 0
    assert events[0]["timestamp_ms"] == 1001
    assert set(events[0].keys()) == {"type", "data", "sequence_num", "timestamp_ms"}


async def test_events_empty_for_new_session(db_session: AsyncSession) -> None:
    """A session with no persisted events → 200 + [] (zero events is valid)."""
    tenant = await seed_tenant(db_session, code="SESSEV_EMPTY")
    user = await seed_user(db_session, tenant, email="ev@empty.test")
    sid = await _seed_session(db_session, tenant=tenant, user_id=user.id)

    app = _build_app(db_session=db_session, tenant_id=tenant.id)
    async with _client(app) as ac:
        resp = await ac.get(f"/api/v1/sessions/{sid}/events")
    assert resp.status_code == 200
    assert resp.json()["events"] == []


async def test_events_cross_tenant_returns_empty_not_404(db_session: AsyncSession) -> None:
    """Cross-tenant session → 200 + [] (never 404; never reveal existence; 鐵律)."""
    tenant_a = await seed_tenant(db_session, code="SESSEV_XT_A")
    tenant_b = await seed_tenant(db_session, code="SESSEV_XT_B")
    user_a = await seed_user(db_session, tenant_a, email="ev_a@xt.test")
    sid = await _seed_session(db_session, tenant=tenant_a, user_id=user_a.id)
    await _seed_event(
        db_session, tenant_id=tenant_a.id, session_id=sid, event_type="turn_start", seq=1
    )

    app_b = _build_app(db_session=db_session, tenant_id=tenant_b.id)
    async with _client(app_b) as ac:
        resp = await ac.get(f"/api/v1/sessions/{sid}/events")
    assert resp.status_code == 200
    assert resp.json()["events"] == []


async def test_events_unknown_session_returns_empty(db_session: AsyncSession) -> None:
    tenant = await seed_tenant(db_session, code="SESSEV_UNK")
    app = _build_app(db_session=db_session, tenant_id=tenant.id)
    async with _client(app) as ac:
        resp = await ac.get(f"/api/v1/sessions/{uuid4()}/events")
    assert resp.status_code == 200
    assert resp.json()["events"] == []
