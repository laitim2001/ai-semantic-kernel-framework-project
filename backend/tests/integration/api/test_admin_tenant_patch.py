"""
File: backend/tests/integration/api/test_admin_tenant_patch.py
Purpose: Integration tests — PATCH /admin/tenants/{tenant_id} endpoint (Sprint 57.3 US-2).
Category: Tests / Integration / API (Phase 57+ SaaS Frontend 2/N)
Scope: Sprint 57.3 / Day 2 / US-2

Description:
    Verifies the PATCH /admin/tenants/{tenant_id} partial update endpoint:
    - 401 / 403 / 404 (auth + lookup errors)
    - 422 immutable field rejection (Pydantic extra='forbid')
    - 422 display_name too long (>256 chars)
    - 200 happy paths: display_name only / meta_data only / both
    - 200 no-op (empty payload or unchanged values) — no audit entry
    - Audit chain entry written with operation='tenant_settings_updated' +
      operation_data containing changed_fields + old_values + new_values

    Mirrors test_admin_tenant_get.py pattern (FastAPI test app + role
    middleware + db_session + require_admin_platform_role overrides).

Created: 2026-05-07 (Sprint 57.3 Day 2)
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, Request, Response
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.admin.tenants import router as admin_tenants_router
from infrastructure.db.models.audit import AuditLog
from infrastructure.db.session import get_db_session
from platform_layer.identity.auth import require_admin_platform_role
from tests.conftest import seed_tenant

pytestmark = pytest.mark.asyncio


def _build_app(db_session: AsyncSession | None = None) -> FastAPI:
    """Build app with admin tenants router + role middleware + optional DB override."""
    app = FastAPI()
    app.include_router(admin_tenants_router, prefix="/api/v1")

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

    if db_session is not None:

        async def _override_session() -> AsyncIterator[AsyncSession]:
            yield db_session

        async def _override_admin() -> UUID:
            return UUID("00000000-0000-0000-0000-000000000001")

        app.dependency_overrides[get_db_session] = _override_session
        app.dependency_overrides[require_admin_platform_role] = _override_admin

    return app


# ---------------------------------------------------------------------
# Auth + lookup error paths (3 tests)
# ---------------------------------------------------------------------


async def test_patch_401_without_auth() -> None:
    """No X-Test-User header → 401."""
    app = _build_app()
    tenant_id = uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.patch(
            f"/api/v1/admin/tenants/{tenant_id}",
            json={"display_name": "X"},
        )
    assert resp.status_code == 401


async def test_patch_403_wrong_role() -> None:
    """tenant_admin role insufficient → 403."""
    app = _build_app()
    user_id = uuid4()
    tenant_id = uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.patch(
            f"/api/v1/admin/tenants/{tenant_id}",
            json={"display_name": "X"},
            headers={
                "X-Test-User": str(user_id),
                "X-Test-Roles": json.dumps(["tenant_admin"]),
            },
        )
    assert resp.status_code == 403


async def test_patch_404_not_found(db_session: AsyncSession) -> None:
    """Admin auth + random UUID not in DB → 404."""
    app = _build_app(db_session=db_session)
    transport = ASGITransport(app=app)
    random_tenant_id = uuid4()
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.patch(
            f"/api/v1/admin/tenants/{random_tenant_id}",
            json={"display_name": "X"},
        )
    assert resp.status_code == 404


# ---------------------------------------------------------------------
# Validation error paths (2 tests)
# ---------------------------------------------------------------------


async def test_patch_immutable_field_rejected(db_session: AsyncSession) -> None:
    """Pydantic extra='forbid' rejects any field other than display_name + meta_data → 422."""
    t = await seed_tenant(db_session, code="IMMUTABLE_TEST")
    app = _build_app(db_session=db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Try to change immutable plan field — should be rejected.
        resp = await ac.patch(
            f"/api/v1/admin/tenants/{t.id}",
            json={"plan": "STANDARD"},
        )
    assert resp.status_code == 422


async def test_patch_display_name_too_long(db_session: AsyncSession) -> None:
    """display_name > 256 chars → 422."""
    t = await seed_tenant(db_session, code="TOO_LONG_TEST")
    app = _build_app(db_session=db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.patch(
            f"/api/v1/admin/tenants/{t.id}",
            json={"display_name": "X" * 257},
        )
    assert resp.status_code == 422


# ---------------------------------------------------------------------
# Happy path + audit chain (3 tests)
# ---------------------------------------------------------------------


async def test_patch_display_name_only(db_session: AsyncSession) -> None:
    """display_name update → 200 + name changed + 1 audit entry."""
    t = await seed_tenant(db_session, code="DN_ONLY", display_name="Original")
    app = _build_app(db_session=db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.patch(
            f"/api/v1/admin/tenants/{t.id}",
            json={"display_name": "Renamed"},
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["display_name"] == "Renamed"

    # Verify audit chain entry written.
    result = await db_session.execute(
        select(AuditLog)
        .where(AuditLog.tenant_id == t.id)
        .where(AuditLog.operation == "tenant_settings_updated")
    )
    entries = result.scalars().all()
    assert len(entries) == 1
    audit = entries[0]
    assert audit.operation_data["changed_fields"] == ["display_name"]
    assert audit.operation_data["old_values"]["display_name"] == "Original"
    assert audit.operation_data["new_values"]["display_name"] == "Renamed"


async def test_patch_meta_data_only(db_session: AsyncSession) -> None:
    """meta_data update → 200 + JSONB updated + 1 audit entry."""
    t = await seed_tenant(db_session, code="META_ONLY")
    app = _build_app(db_session=db_session)
    transport = ASGITransport(app=app)
    new_meta = {"region": "us-west", "tier_override": "platinum"}
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.patch(
            f"/api/v1/admin/tenants/{t.id}",
            json={"meta_data": new_meta},
        )
    assert resp.status_code == 200
    assert resp.json()["meta_data"] == new_meta

    result = await db_session.execute(
        select(AuditLog)
        .where(AuditLog.tenant_id == t.id)
        .where(AuditLog.operation == "tenant_settings_updated")
    )
    entries = result.scalars().all()
    assert len(entries) == 1
    assert entries[0].operation_data["changed_fields"] == ["meta_data"]


async def test_patch_both_fields(db_session: AsyncSession) -> None:
    """display_name + meta_data both → 200 + both updated + 1 audit entry with both fields."""
    t = await seed_tenant(db_session, code="BOTH_FIELDS", display_name="Before")
    app = _build_app(db_session=db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.patch(
            f"/api/v1/admin/tenants/{t.id}",
            json={"display_name": "After", "meta_data": {"k": "v"}},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["display_name"] == "After"
    assert body["meta_data"] == {"k": "v"}

    result = await db_session.execute(
        select(AuditLog)
        .where(AuditLog.tenant_id == t.id)
        .where(AuditLog.operation == "tenant_settings_updated")
    )
    entries = result.scalars().all()
    # Single audit entry with both fields in changed_fields list.
    assert len(entries) == 1
    assert set(entries[0].operation_data["changed_fields"]) == {"display_name", "meta_data"}


# ---------------------------------------------------------------------
# No-op short-circuit (1 test)
# ---------------------------------------------------------------------


async def test_patch_no_op(db_session: AsyncSession) -> None:
    """Empty payload → 200 + no audit entry (short-circuit)."""
    t = await seed_tenant(db_session, code="NO_OP")
    app = _build_app(db_session=db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.patch(
            f"/api/v1/admin/tenants/{t.id}",
            json={},
        )
    assert resp.status_code == 200

    # No audit entry should have been written.
    result = await db_session.execute(
        select(AuditLog)
        .where(AuditLog.tenant_id == t.id)
        .where(AuditLog.operation == "tenant_settings_updated")
    )
    entries = result.scalars().all()
    assert len(entries) == 0
