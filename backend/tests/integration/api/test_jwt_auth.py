"""
File: backend/tests/integration/api/test_jwt_auth.py
Purpose: Integration tests for JWT-based authentication via TenantContextMiddleware.
Category: Tests / Integration / API
Scope: Sprint 52.5 Day 6.1 (P0 #14 phase 2)

Cases:
    - no Authorization header → 401
    - non-Bearer scheme (Basic / Digest) → 401
    - empty bearer (`Authorization: Bearer `) → 401
    - expired JWT → 401 with WWW-Authenticate error_description="expired"
    - bad signature → 401 with WWW-Authenticate error="invalid_token"
    - sub claim is not UUID → 401
    - **attack**: forged X-Tenant-Id header with valid JWT → JWT wins
                  (X-Tenant-Id is no longer consulted)
    - **attack**: forged X-Tenant-Id header without JWT → still 401

Created: 2026-05-01 (Sprint 52.5 Day 6.1)
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from infrastructure.db import dispose_engine
from platform_layer.identity import JWTManager
from platform_layer.middleware import TenantContextMiddleware


_SECRET = "integ-test-secret"


@pytest.fixture(autouse=True)
async def _dispose_engine_after_each_test():  # type: ignore[no-untyped-def]
    """Same engine-pool cleanup pattern as test_tenant_context.py."""
    yield
    await dispose_engine()


def _make_app(jwt_manager: JWTManager) -> FastAPI:
    app = FastAPI()
    app.add_middleware(TenantContextMiddleware, jwt_manager=jwt_manager)

    @app.get("/echo")
    async def echo(request: Request) -> dict[str, str]:
        return {
            "tenant_id": str(request.state.tenant_id),
            "user_id": str(request.state.user_id),
        }

    return app


def _mgr(*, expires_minutes: int = 60) -> JWTManager:
    return JWTManager(
        secret=_SECRET, algorithm="HS256", expires_minutes=expires_minutes
    )


@pytest.mark.asyncio
async def test_no_authorization_returns_401() -> None:
    mgr = _mgr()
    app = _make_app(mgr)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/echo")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_non_bearer_scheme_returns_401() -> None:
    mgr = _mgr()
    app = _make_app(mgr)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/echo", headers={"Authorization": "Basic abcdef"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "Authorization Bearer token required"


@pytest.mark.asyncio
async def test_empty_bearer_token_returns_401() -> None:
    mgr = _mgr()
    app = _make_app(mgr)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/echo", headers={"Authorization": "Bearer "})
    assert resp.status_code == 401
    assert resp.json()["error"] == "Bearer token is empty"


@pytest.mark.asyncio
async def test_expired_token_returns_401_with_expired_description() -> None:
    mgr = _mgr(expires_minutes=-1)  # already expired at issue time
    token = mgr.encode(sub=str(uuid4()), tenant_id=uuid4())
    app = _make_app(mgr)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/echo", headers={"Authorization": f"Bearer {token}"}
        )
    assert resp.status_code == 401
    assert resp.json()["error"] == "token expired"
    assert "expired" in resp.headers.get("www-authenticate", "").lower()


@pytest.mark.asyncio
async def test_bad_signature_returns_401() -> None:
    """Mint with one secret, verify with another → 401."""
    issuer = JWTManager(secret="other-secret", algorithm="HS256", expires_minutes=60)
    token = issuer.encode(sub=str(uuid4()), tenant_id=uuid4())
    verifier = _mgr()
    app = _make_app(verifier)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/echo", headers={"Authorization": f"Bearer {token}"}
        )
    assert resp.status_code == 401
    assert resp.json()["error"] == "token invalid"
    assert "invalid_token" in resp.headers.get("www-authenticate", "")


@pytest.mark.asyncio
async def test_sub_not_uuid_returns_401() -> None:
    """JWTManager allows arbitrary str sub (per JWT RFC); middleware enforces
    UUID for our deployment so non-UUID issuers get rejected at middleware."""
    from jose import jwt as jose_jwt

    payload = {
        "sub": "not-a-uuid",
        "tenant_id": str(uuid4()),
        "roles": [],
        "iat": 0,
        "exp": 9999999999,
    }
    token = jose_jwt.encode(payload, _SECRET, algorithm="HS256")
    app = _make_app(_mgr())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/echo", headers={"Authorization": f"Bearer {token}"}
        )
    assert resp.status_code == 401
    assert "valid UUID" in resp.json()["error"]


@pytest.mark.asyncio
async def test_forged_x_tenant_id_with_valid_jwt_jwt_wins() -> None:
    """Attack: client sends both a valid JWT AND a forged X-Tenant-Id header.

    Pre-refactor (V1) read tenant_id from X-Tenant-Id; the post-Day-6.1
    middleware ignores X-Tenant-Id entirely and uses only the JWT claim.
    """
    real_tid = uuid4()
    forged_tid = uuid4()
    mgr = _mgr()
    token = mgr.encode(sub=str(uuid4()), tenant_id=real_tid)
    app = _make_app(mgr)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/echo",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-Id": str(forged_tid),  # forged — must be ignored
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert UUID(body["tenant_id"]) == real_tid, (
        "X-Tenant-Id should be IGNORED post-refactor (P0 #14). JWT is the "
        "single canonical source of tenant_id."
    )
    assert UUID(body["tenant_id"]) != forged_tid


@pytest.mark.asyncio
async def test_forged_x_tenant_id_without_jwt_still_401() -> None:
    """No fallback path exists — X-Tenant-Id alone fails 401."""
    mgr = _mgr()
    app = _make_app(mgr)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/echo", headers={"X-Tenant-Id": str(uuid4())}
        )
    assert resp.status_code == 401
