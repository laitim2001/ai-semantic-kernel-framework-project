"""
File: backend/tests/integration/api/test_admin_tenant_identity.py
Purpose: Integration tests — GET /admin/tenants/{tenant_id}/identity (Sprint 57.50).
Category: Tests / Integration / API (Phase 58+ Backend Schema Extension wave)
Scope: Sprint 57.50 Day 1 Option A (closes AD-TenantSettings-IdentityFixture-Cleanup)

Description:
    Verifies the GET /admin/tenants/{tenant_id}/identity endpoint
    (Day 0.8 Option A — fixture-projection from tenant.meta_data["identity"]):
    - 401 when no JWT context
    - 404 when tenant not found
    - 200 returns DEFAULT_IDENTITY (4 fields) when meta_data has no
      "identity" key
    - 200 returns tenant-overridden values when meta_data["identity"] is set
    - 200 falls back per-field when meta_data["identity"] is partial
    - Response shape: provider + scim_enabled + allowed_domains + mfa_required
    - Multi-tenant isolation (tenant A's override does NOT show in tenant B)

Created: 2026-05-26 (Sprint 57.50 Day 1)

Modification History (newest-first):
    - 2026-05-26: Initial creation (Sprint 57.50 Day 1 — Identity admin GET Option A)
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, Request, Response
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.admin.tenants import router as admin_tenants_router
from infrastructure.db.models.identity import Tenant, TenantPlan, TenantState
from infrastructure.db.session import get_db_session
from platform_layer.identity.auth import require_admin_platform_role

pytestmark = pytest.mark.asyncio


def _build_app(db_session: AsyncSession | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(admin_tenants_router, prefix="/api/v1")

    @app.middleware("http")
    async def _populate_test_state(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        user_header = request.headers.get("X-Test-User")
        roles_header = request.headers.get("X-Test-Roles")
        tenant_header = request.headers.get("X-Test-Tenant")
        request.state.user_id = UUID(user_header) if user_header else None
        request.state.roles = json.loads(roles_header) if roles_header else None
        request.state.tenant_id = UUID(tenant_header) if tenant_header else None
        return await call_next(request)

    if db_session is not None:

        async def _override_session() -> AsyncIterator[AsyncSession]:
            yield db_session

        async def _override_admin() -> UUID:
            return UUID("00000000-0000-0000-0000-000000000001")

        app.dependency_overrides[get_db_session] = _override_session
        app.dependency_overrides[require_admin_platform_role] = _override_admin

    return app


async def _seed_tenant(
    session: AsyncSession,
    *,
    code: str,
    meta_data: dict[str, Any] | None = None,
) -> Tenant:
    t = Tenant(
        code=code,
        display_name=f"Tenant {code}",
        state=TenantState.ACTIVE,
        plan=TenantPlan.ENTERPRISE,
        meta_data=meta_data or {},
    )
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t


async def test_get_identity_401_without_auth() -> None:
    app = _build_app()
    tenant_id = uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/api/v1/admin/tenants/{tenant_id}/identity")
    assert resp.status_code == 401


async def test_get_identity_404_when_tenant_not_found(db_session: AsyncSession) -> None:
    app = _build_app(db_session=db_session)
    missing_id = uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/api/v1/admin/tenants/{missing_id}/identity")
    assert resp.status_code == 404


async def test_get_identity_returns_defaults_when_no_override(
    db_session: AsyncSession,
) -> None:
    """meta_data lacks identity → DEFAULT_IDENTITY (4 fields)."""
    tenant = await _seed_tenant(db_session, code="ID_DEF_T1")
    app = _build_app(db_session=db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/api/v1/admin/tenants/{tenant.id}/identity")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["provider"] == "SAML 2.0 · WorkOS"
    assert body["scim_enabled"] is True
    assert body["allowed_domains"] == ["acme.com", "acme.io"]
    assert body["mfa_required"] is True


async def test_get_identity_applies_tenant_override(db_session: AsyncSession) -> None:
    """meta_data['identity'] is honoured when present."""
    custom = {
        "provider": "Okta",
        "scim_enabled": False,
        "allowed_domains": ["custom.com"],
        "mfa_required": False,
    }
    tenant = await _seed_tenant(
        db_session,
        code="ID_OVR_T1",
        meta_data={"identity": custom},
    )
    app = _build_app(db_session=db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/api/v1/admin/tenants/{tenant.id}/identity")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["provider"] == "Okta"
    assert body["scim_enabled"] is False
    assert body["allowed_domains"] == ["custom.com"]
    assert body["mfa_required"] is False


async def test_get_identity_partial_meta_data_falls_back_per_field(
    db_session: AsyncSession,
) -> None:
    """Partial identity dict → per-field fallback to DEFAULT_IDENTITY."""
    tenant = await _seed_tenant(
        db_session,
        code="ID_PARTIAL_T1",
        meta_data={"identity": {"provider": "Custom"}},
    )
    app = _build_app(db_session=db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/api/v1/admin/tenants/{tenant.id}/identity")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["provider"] == "Custom"
    # The other 3 fields fall back to DEFAULT_IDENTITY values
    assert body["scim_enabled"] is True
    assert body["allowed_domains"] == ["acme.com", "acme.io"]
    assert body["mfa_required"] is True


async def test_get_identity_response_shape(db_session: AsyncSession) -> None:
    tenant = await _seed_tenant(db_session, code="ID_SHAPE_T1")
    app = _build_app(db_session=db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/api/v1/admin/tenants/{tenant.id}/identity")
    body = resp.json()
    assert {"provider", "scim_enabled", "allowed_domains", "mfa_required"}.issubset(
        set(body.keys())
    )


async def test_get_identity_tenant_isolation(db_session: AsyncSession) -> None:
    """Tenant A's override must NOT leak into Tenant B (multi-tenant rule)."""
    tenant_a = await _seed_tenant(
        db_session,
        code="ID_ISO_A",
        meta_data={
            "identity": {
                "provider": "Okta-Custom-A",
                "scim_enabled": False,
                "allowed_domains": ["secret-a.com"],
                "mfa_required": False,
            }
        },
    )
    tenant_b = await _seed_tenant(db_session, code="ID_ISO_B")
    app = _build_app(db_session=db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp_a = await ac.get(f"/api/v1/admin/tenants/{tenant_a.id}/identity")
        resp_b = await ac.get(f"/api/v1/admin/tenants/{tenant_b.id}/identity")
    assert resp_a.status_code == 200 and resp_b.status_code == 200
    body_a = resp_a.json()
    body_b = resp_b.json()
    # Tenant A: override visible
    assert body_a["provider"] == "Okta-Custom-A"
    assert body_a["allowed_domains"] == ["secret-a.com"]
    # Tenant B: DEFAULT_IDENTITY (no leak from A)
    assert body_b["provider"] == "SAML 2.0 · WorkOS"
    assert body_b["allowed_domains"] == ["acme.com", "acme.io"]
