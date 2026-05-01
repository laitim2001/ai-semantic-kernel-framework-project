"""
File: backend/tests/unit/platform_layer/middleware/test_tenant_context.py
Purpose: TenantContextMiddleware (JWT-based) + get_db_session_with_tenant dep tests.
Category: Tests / Platform layer / Middleware
Scope: Sprint 49.3 Day 4.5 — Sprint 52.5 Day 6.1 (P0 #14 phase 2: JWT swap)

Modification History:
    - 2026-05-01: Sprint 52.5 Day 6.1 — switch from X-Tenant-Id header
        to Authorization Bearer JWT decode. test_invalid_uuid_returns_400
        replaced by test_invalid_token_returns_401 (UUID parsing now lives
        inside JWT decode, not from header).
    - 2026-04-29: Initial creation (Sprint 49.3 Day 4.5)
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi import Depends, FastAPI, Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db import dispose_engine
from platform_layer.identity import JWTManager
from platform_layer.middleware import (
    TenantContextMiddleware,
    get_db_session_with_tenant,
)

_TEST_SECRET = "test-secret-do-not-use-in-prod"


def _build_jwt(
    *,
    tenant_id: UUID,
    user_id: UUID,
    roles: list[str] | None = None,
    expires_minutes: int = 60,
) -> tuple[str, JWTManager]:
    """Mint a JWT signed with a deterministic test secret + return manager
    (so the middleware can be constructed with the same secret)."""
    mgr = JWTManager(secret=_TEST_SECRET, algorithm="HS256", expires_minutes=expires_minutes)
    token = mgr.encode(sub=str(user_id), tenant_id=tenant_id, roles=roles or [])
    return token, mgr


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


def _build_test_app(*, jwt_manager: JWTManager | None = None) -> FastAPI:
    """Construct a tiny FastAPI app with the middleware + 2 probe routes.

    A custom JWTManager can be passed so tests don't depend on real env
    vars / Settings — the middleware uses this manager directly to decode
    incoming Bearer tokens.
    """
    app = FastAPI()
    app.add_middleware(TenantContextMiddleware, jwt_manager=jwt_manager)

    @app.get("/whoami")
    async def whoami(request: Request) -> dict[str, str | list[str]]:
        return {
            "tenant_id": str(request.state.tenant_id),
            "user_id": str(request.state.user_id),
            "roles": request.state.roles,
        }

    @app.get("/dbprobe")
    async def dbprobe(
        db: AsyncSession = Depends(get_db_session_with_tenant),
    ) -> dict[str, str | None]:
        result = await db.execute(text("SELECT current_setting('app.tenant_id', true)"))
        return {"app_tenant_id": result.scalar_one_or_none()}

    return app


@pytest.mark.asyncio
async def test_missing_authorization_returns_401() -> None:
    """No Authorization header → 401 + Bearer realm WWW-Authenticate."""
    _, mgr = _build_jwt(tenant_id=uuid4(), user_id=uuid4())
    app = _build_test_app(jwt_manager=mgr)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/whoami")
    assert resp.status_code == 401
    assert "Bearer" in resp.headers.get("www-authenticate", "")
    assert resp.json()["error"] == "Authorization Bearer token required"


@pytest.mark.asyncio
async def test_invalid_token_returns_401() -> None:
    """Garbage token → 401 (replaces the X-Tenant-Id 400 case from V1)."""
    _, mgr = _build_jwt(tenant_id=uuid4(), user_id=uuid4())
    app = _build_test_app(jwt_manager=mgr)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/whoami", headers={"Authorization": "Bearer garbage.not.a.jwt"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "token invalid"


@pytest.mark.asyncio
async def test_valid_jwt_populates_request_state() -> None:
    """Valid JWT → tenant_id + user_id + roles all reach request.state."""
    tid = uuid4()
    uid = uuid4()
    token, mgr = _build_jwt(tenant_id=tid, user_id=uid, roles=["admin", "auditor"])
    app = _build_test_app(jwt_manager=mgr)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/whoami", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert UUID(body["tenant_id"]) == tid
    assert UUID(body["user_id"]) == uid
    assert body["roles"] == ["admin", "auditor"]


@pytest.mark.asyncio
async def test_get_db_session_with_tenant_sets_local() -> None:
    """Probe endpoint reads current_setting('app.tenant_id') and confirms
    the dep set it (per SET LOCAL via set_config(..., true))."""
    tid = uuid4()
    uid = uuid4()
    token, mgr = _build_jwt(tenant_id=tid, user_id=uid)
    app = _build_test_app(jwt_manager=mgr)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/dbprobe", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["app_tenant_id"] == str(tid)
