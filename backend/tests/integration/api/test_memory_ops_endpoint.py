"""
File: backend/tests/integration/api/test_memory_ops_endpoint.py
Purpose: Integration tests for GET /api/v1/memory/ops (Sprint 57.76).
Category: Tests / Integration / API
Scope: Phase 57 / Sprint 57.76 (US-4 / US-6)

Description:
    Mounts the memory router on a minimal FastAPI app and overrides the
    identity + db deps with a synthetic tenant/audit user + the test
    db_session (mirrors test_memory_matrix.py). Verifies:

    - Tenant-scoped, created_at DESC ordering.
    - Cursor pagination via `before` (created_at_ms).
    - require_audit_role 403 for non-audit role.
    - Cross-tenant isolation (tenant A excludes tenant B's ops).

Created: 2026-06-04 (Sprint 57.76)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, HTTPException, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.memory import router as memory_router
from infrastructure.db.models import Tenant
from infrastructure.db.models.memory import MemoryOp
from platform_layer.identity.auth import get_current_tenant, require_audit_role
from platform_layer.middleware.tenant_context import get_db_session_with_tenant
from tests.conftest import seed_tenant, seed_user

pytestmark = pytest.mark.asyncio


async def _seed_op(
    db: AsyncSession,
    *,
    tenant: Tenant,
    user_id: UUID,
    content: str,
    operation: str = "WRITE",
    created_at: datetime | None = None,
) -> MemoryOp:
    row = MemoryOp(
        tenant_id=tenant.id,
        user_id=user_id,
        scope="user",
        key="general",
        operation=operation,
        time_scale="long_term",
        value_snapshot=content,
        actor=str(user_id),
    )
    if created_at is not None:
        row.created_at = created_at
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


def _build_app(
    *,
    db_session: AsyncSession,
    tenant_id: UUID,
    audit_user_id: UUID | None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(memory_router, prefix="/api/v1")

    async def _override_tenant() -> UUID:
        return tenant_id

    async def _override_audit_role() -> UUID:
        if audit_user_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Audit role required")
        return audit_user_id

    async def _override_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_current_tenant] = _override_tenant
    app.dependency_overrides[require_audit_role] = _override_audit_role
    app.dependency_overrides[get_db_session_with_tenant] = _override_db
    return app


async def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ---------------------------------------------------------------------------
# Happy path + ordering
# ---------------------------------------------------------------------------


async def test_ops_time_ordered_desc(db_session: AsyncSession) -> None:
    tenant = await seed_tenant(db_session, code="OPS_EP_ORD")
    user = await seed_user(db_session, tenant, email="ord@opsep.test")
    base = datetime.now(UTC)
    await _seed_op(
        db_session,
        tenant=tenant,
        user_id=user.id,
        content="oldest",
        created_at=base - timedelta(minutes=2),
    )
    await _seed_op(
        db_session,
        tenant=tenant,
        user_id=user.id,
        content="middle",
        created_at=base - timedelta(minutes=1),
    )
    await _seed_op(db_session, tenant=tenant, user_id=user.id, content="newest", created_at=base)

    app = _build_app(db_session=db_session, tenant_id=tenant.id, audit_user_id=uuid4())
    async with await _client(app) as ac:
        resp = await ac.get("/api/v1/memory/ops")
    assert resp.status_code == 200
    body = resp.json()
    contents = [o["value_snapshot"] for o in body["ops"]]
    assert contents == ["newest", "middle", "oldest"]
    assert body["ops"][0]["op"] == "WRITE"
    assert body["ops"][0]["scope"] == "user"


async def test_ops_pagination_cursor(db_session: AsyncSession) -> None:
    tenant = await seed_tenant(db_session, code="OPS_EP_PAGE")
    user = await seed_user(db_session, tenant, email="page@opsep.test")
    base = datetime.now(UTC)
    for i in range(3):
        await _seed_op(
            db_session,
            tenant=tenant,
            user_id=user.id,
            content=f"op{i}",
            created_at=base - timedelta(minutes=i),
        )

    app = _build_app(db_session=db_session, tenant_id=tenant.id, audit_user_id=uuid4())
    async with await _client(app) as ac:
        # First page: limit 2 → newest 2; next_cursor set (page full).
        resp1 = await ac.get("/api/v1/memory/ops", params={"limit": 2})
        body1 = resp1.json()
        assert [o["value_snapshot"] for o in body1["ops"]] == ["op0", "op1"]
        assert body1["next_cursor"] is not None

        # Second page: before=next_cursor → strictly older → op2 only; no more.
        resp2 = await ac.get(
            "/api/v1/memory/ops", params={"limit": 2, "before": body1["next_cursor"]}
        )
        body2 = resp2.json()
        assert [o["value_snapshot"] for o in body2["ops"]] == ["op2"]
        assert body2["next_cursor"] is None


# ---------------------------------------------------------------------------
# RBAC + cross-tenant
# ---------------------------------------------------------------------------


async def test_ops_403_when_non_auditor(db_session: AsyncSession) -> None:
    tenant = await seed_tenant(db_session, code="OPS_EP_403")
    app = _build_app(db_session=db_session, tenant_id=tenant.id, audit_user_id=None)
    async with await _client(app) as ac:
        resp = await ac.get("/api/v1/memory/ops")
    assert resp.status_code == 403


async def test_ops_cross_tenant_isolation(db_session: AsyncSession) -> None:
    """Tenant A's ops feed EXCLUDES tenant B's ops (explicit tenant_id filter)."""
    tenant_a = await seed_tenant(db_session, code="OPS_EP_ISO_A")
    tenant_b = await seed_tenant(db_session, code="OPS_EP_ISO_B")
    user_a = await seed_user(db_session, tenant_a, email="a@opsiso.test")
    user_b = await seed_user(db_session, tenant_b, email="b@opsiso.test")
    await _seed_op(db_session, tenant=tenant_a, user_id=user_a.id, content="A only")
    await _seed_op(db_session, tenant=tenant_b, user_id=user_b.id, content="B1")
    await _seed_op(db_session, tenant=tenant_b, user_id=user_b.id, content="B2")

    app = _build_app(db_session=db_session, tenant_id=tenant_a.id, audit_user_id=uuid4())
    async with await _client(app) as ac:
        resp = await ac.get("/api/v1/memory/ops")
    body = resp.json()
    assert [o["value_snapshot"] for o in body["ops"]] == ["A only"]


async def test_ops_empty(db_session: AsyncSession) -> None:
    tenant = await seed_tenant(db_session, code="OPS_EP_EMPTY")
    app = _build_app(db_session=db_session, tenant_id=tenant.id, audit_user_id=uuid4())
    async with await _client(app) as ac:
        resp = await ac.get("/api/v1/memory/ops")
    body = resp.json()
    assert body["ops"] == []
    assert body["next_cursor"] is None
