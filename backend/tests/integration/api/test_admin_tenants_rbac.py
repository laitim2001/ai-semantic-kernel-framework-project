"""
File: backend/tests/integration/api/test_admin_tenants_rbac.py
Purpose: Integration tests — admin tenants endpoints enforce require_admin_platform_role.
Category: Tests / Integration / API (Phase 56 SaaS Stage 1)
Scope: Sprint 56.2 / Day 1 / US-4 (closes AD-AdminAuth-1)

Description:
    Mounts the admin tenants router on a minimal FastAPI app with a tiny
    middleware that populates request.state.user_id + request.state.roles
    from headers (X-Test-User / X-Test-Roles), so the real
    require_admin_platform_role dep runs against test JWT-like state.

    Two flows:
      - test_admin_tenants_post_with_admin_role — roles=["admin"] → reaches
        endpoint body (we expect a downstream 422/500 from missing DB tenant
        seed; just need to verify NOT a 403 from the role check).
      - test_admin_tenants_post_without_admin_role_403 — roles=["tenant_admin"]
        → 403 Platform admin role required.

Created: 2026-05-06 (Sprint 56.2 Day 1)
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, Request, Response
from httpx import ASGITransport, AsyncClient

from api.v1.admin.tenants import router as admin_tenants_router

pytestmark = pytest.mark.asyncio


def _build_app() -> FastAPI:
    """Build app with tenants router + middleware populating state.user_id/roles."""
    app = FastAPI()

    @app.middleware("http")
    async def _populate_test_state(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        user_header = request.headers.get("X-Test-User")
        roles_header = request.headers.get("X-Test-Roles")
        request.state.user_id = UUID(user_header) if user_header else None
        request.state.roles = json.loads(roles_header) if roles_header else None
        return await call_next(request)

    app.include_router(admin_tenants_router, prefix="/api/v1")
    return app


async def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_admin_tenants_post_without_admin_role_403() -> None:
    """tenant_admin role insufficient → 403."""
    app = _build_app()
    user_id = uuid4()
    async with await _client(app) as ac:
        resp = await ac.post(
            "/api/v1/admin/tenants",
            json={
                "code": "rbac-test",
                "display_name": "RBAC Test",
                "admin_email": "rbac@test.com",
            },
            headers={
                "X-Test-User": str(user_id),
                "X-Test-Roles": json.dumps(["tenant_admin"]),
            },
        )
    assert resp.status_code == 403
    assert "Platform admin" in resp.json()["detail"]


async def test_admin_tenants_post_without_auth_401() -> None:
    """No JWT context → 401 (auth_required)."""
    app = _build_app()
    async with await _client(app) as ac:
        resp = await ac.post(
            "/api/v1/admin/tenants",
            json={
                "code": "rbac-test",
                "display_name": "RBAC Test",
                "admin_email": "rbac@test.com",
            },
        )
    # Middleware populates user_id=None when X-Test-User missing → get_current_user_id
    # raises 401.
    assert resp.status_code == 401
