"""
File: backend/tests/unit/platform_layer/middleware/test_tenant_context.py
Purpose: TenantContextMiddleware + get_db_session_with_tenant dep tests.
Category: Tests / Platform layer / Middleware
Scope: Sprint 49.3 Day 4.5

Tests:
    1. test_missing_header_returns_401
    2. test_invalid_uuid_returns_400
    3. test_valid_uuid_populates_request_state
    4. test_get_db_session_with_tenant_sets_local

Created: 2026-04-29 (Sprint 49.3 Day 4.5)
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi import Depends, FastAPI, Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db import dispose_engine
from platform_layer.middleware import (
    TenantContextMiddleware,
    get_db_session_with_tenant,
)


@pytest.fixture(autouse=True)
async def _dispose_engine_after_each_test():  # type: ignore[no-untyped-def]
    """Dispose the singleton engine after each test so the next test —
    possibly in a different file with its own event loop — gets a clean
    engine. Otherwise the pool retains asyncpg connections bound to
    this test's loop and the next file's first test fails on cleanup
    with `Event loop is closed`. Same root-cause fix as conftest's
    db_session fixture, but FastAPI dep here doesn't go through that
    fixture.
    """
    yield
    await dispose_engine()


def _build_test_app() -> FastAPI:
    """Construct a tiny FastAPI app with the middleware + 2 probe routes."""
    app = FastAPI()
    app.add_middleware(TenantContextMiddleware)

    @app.get("/whoami")
    async def whoami(request: Request) -> dict[str, str]:
        return {"tenant_id": str(request.state.tenant_id)}

    @app.get("/dbprobe")
    async def dbprobe(
        db: AsyncSession = Depends(get_db_session_with_tenant),
    ) -> dict[str, str | None]:
        result = await db.execute(text("SELECT current_setting('app.tenant_id', true)"))
        return {"app_tenant_id": result.scalar_one_or_none()}

    return app


@pytest.mark.asyncio
async def test_missing_header_returns_401() -> None:
    app = _build_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/whoami")
    assert resp.status_code == 401
    assert "X-Tenant-Id" in resp.json()["error"]


@pytest.mark.asyncio
async def test_invalid_uuid_returns_400() -> None:
    app = _build_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/whoami", headers={"X-Tenant-Id": "not-a-uuid"})
    assert resp.status_code == 400
    assert "valid UUID" in resp.json()["error"]


@pytest.mark.asyncio
async def test_valid_uuid_populates_request_state() -> None:
    app = _build_test_app()
    tid = str(uuid4())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/whoami", headers={"X-Tenant-Id": tid})
    assert resp.status_code == 200
    assert resp.json() == {"tenant_id": tid}
    # Round-trip preserves the canonical UUID form
    assert UUID(resp.json()["tenant_id"]) == UUID(tid)


@pytest.mark.asyncio
async def test_get_db_session_with_tenant_sets_local() -> None:
    """Probe endpoint reads current_setting('app.tenant_id') and confirms
    the dep set it (per SET LOCAL via set_config(..., true))."""
    app = _build_test_app()
    tid = str(uuid4())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/dbprobe", headers={"X-Tenant-Id": tid})
    assert resp.status_code == 200
    assert resp.json()["app_tenant_id"] == tid
