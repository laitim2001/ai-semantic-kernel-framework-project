"""
File: backend/tests/integration/api/test_memory_query_extension.py
Purpose: Integration tests for Sprint 57.19 US-B2 extension of GET /api/v1/memory/recent.
Category: Tests / Integration / API
Scope: Phase 57 / Sprint 57.19 Day 2 / US-B2

Description:
    Verifies the NEW optional query params added to /recent:
    - scope_id (UUID): filter within layer (user_id; tenant cross-check)
    - time_scale (enum): only for layer=user; permanent / quarterly / daily

    Pre-existing /recent behaviour (layer + offset + limit + tenant isolation) is
    covered by tests/integration/api/test_memory.py (Sprint 57.12 baseline).

Created: 2026-05-17 (Sprint 57.19 Day 2 / US-B2)

Modification History (newest-first):
    - 2026-05-17: Initial creation (Sprint 57.19 Day 2 / US-B2)

Related:
    - api/v1/memory.py (endpoint under test — US-B2 extension)
    - tests/integration/api/test_memory.py (sibling Sprint 57.12 baseline)
    - sprint-57-19-plan.md §US-B2
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.memory import router as memory_router
from infrastructure.db.models import Tenant
from infrastructure.db.models.memory import MemoryUser
from platform_layer.identity.auth import get_current_tenant, require_audit_role
from platform_layer.middleware.tenant_context import get_db_session_with_tenant
from tests.conftest import seed_tenant, seed_user

pytestmark = pytest.mark.asyncio


async def _seed_user_memory(
    db: AsyncSession,
    *,
    tenant: Tenant,
    user_id: UUID,
    content: str = "user fact",
    expires_at: datetime | None = None,
) -> MemoryUser:
    row = MemoryUser(
        tenant_id=tenant.id,
        user_id=user_id,
        category="fact",
        content=content,
        expires_at=expires_at,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


def _build_app(*, db_session: AsyncSession, tenant_id: UUID) -> FastAPI:
    app = FastAPI()
    app.include_router(memory_router, prefix="/api/v1")

    async def _override_tenant() -> UUID:
        return tenant_id

    async def _override_audit_role() -> UUID:
        return uuid4()

    async def _override_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_current_tenant] = _override_tenant
    app.dependency_overrides[require_audit_role] = _override_audit_role
    app.dependency_overrides[get_db_session_with_tenant] = _override_db
    return app


async def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ---------------------------------------------------------------------------
# US-B2: scope_id filter on layer=user
# ---------------------------------------------------------------------------


async def test_recent_user_scope_id_filter(db_session: AsyncSession) -> None:
    """When layer=user and scope_id=<user_uuid>, only that user's rows return."""
    tenant = await seed_tenant(db_session, code="MEMQ_SCP_USR")
    user_a = await seed_user(db_session, tenant, email="a@memq.test")
    user_b = await seed_user(db_session, tenant, email="b@memq.test")
    await _seed_user_memory(db_session, tenant=tenant, user_id=user_a.id, content="A1")
    await _seed_user_memory(db_session, tenant=tenant, user_id=user_a.id, content="A2")
    await _seed_user_memory(db_session, tenant=tenant, user_id=user_b.id, content="B1")

    app = _build_app(db_session=db_session, tenant_id=tenant.id)
    async with await _client(app) as ac:
        resp = await ac.get(f"/api/v1/memory/recent?layer=user&scope_id={user_a.id}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 2
    assert all(item["scope_id"] == str(user_a.id) for item in body["items"])


# ---------------------------------------------------------------------------
# US-B2: time_scale=permanent on layer=user
# ---------------------------------------------------------------------------


async def test_recent_user_time_scale_permanent(db_session: AsyncSession) -> None:
    """time_scale=permanent returns only rows with expires_at IS NULL."""
    tenant = await seed_tenant(db_session, code="MEMQ_TS_PERM")
    user = await seed_user(db_session, tenant, email="ts@memq.test")
    # 2 permanent (expires_at=None) + 1 with future expiry
    await _seed_user_memory(db_session, tenant=tenant, user_id=user.id, content="perm-1")
    await _seed_user_memory(db_session, tenant=tenant, user_id=user.id, content="perm-2")
    await _seed_user_memory(
        db_session,
        tenant=tenant,
        user_id=user.id,
        content="quarterly",
        expires_at=datetime.now(UTC) + timedelta(days=60),
    )

    app = _build_app(db_session=db_session, tenant_id=tenant.id)
    async with await _client(app) as ac:
        resp = await ac.get("/api/v1/memory/recent?layer=user&time_scale=permanent")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 2
    assert all(item["expires_at_ms"] is None for item in body["items"])


# ---------------------------------------------------------------------------
# US-B2: tenant scope_id mismatch returns 404
# ---------------------------------------------------------------------------


async def test_recent_tenant_scope_id_mismatch_404(db_session: AsyncSession) -> None:
    """layer=tenant + scope_id != current_tenant → 404 (multi-tenant rule)."""
    tenant = await seed_tenant(db_session, code="MEMQ_TM_NOPE")
    other_uuid = uuid4()

    app = _build_app(db_session=db_session, tenant_id=tenant.id)
    async with await _client(app) as ac:
        resp = await ac.get(f"/api/v1/memory/recent?layer=tenant&scope_id={other_uuid}")
    assert resp.status_code == 404
    assert "does not match" in resp.json()["detail"]
