"""
File: backend/tests/integration/api/test_admin_transcript_retention.py
Purpose: Integration tests — apply/preview /admin/tenants/{id}/transcript-retention (Sprint 57.134).
Category: Tests / Integration / API (data lifecycle)
Scope: Sprint 57.134 (transcript retention — apply/preview on the canonical tenants.retention_days)

Description:
    Verifies the transcript-retention admin endpoints (the config is the EXISTING
    tenants.retention_days column — no new config endpoint this slice):
    - POST /apply: 401/403 without admin, 404 missing, deletes rows older than
      (now - retention_days), keeps within-window rows, multi-tenant isolation, audit chain
    - GET /preview: dry-run COUNT (no deletion), 404 missing

    Seeds real Tenant -> User -> Session -> Message/MessageEvent rows with controlled
    created_at relative to now (old = now-60d, recent = now-5d) so a retention_days=30
    window (cutoff = now-30d) deletes the old + keeps the recent. The seeded dates fall in
    the 2026-04 / 2026-06 partitions (migration 0002) for a 2026-06 run.

Created: 2026-06-17 (Sprint 57.134)

Modification History (newest-first):
    - 2026-06-17: Initial creation (Sprint 57.134)
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, Request, Response
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.admin.tenants import router as admin_tenants_router
from infrastructure.db.models.audit import AuditLog
from infrastructure.db.models.identity import Tenant, TenantPlan, TenantState, User
from infrastructure.db.models.sessions import Message, MessageEvent, Session
from infrastructure.db.session import get_db_session
from platform_layer.identity.auth import require_admin_platform_role

pytestmark = pytest.mark.asyncio

_BASE_URL = "http://test"


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


def _unique_code() -> str:
    """Unique code; conftest sweeps TRANSCRIPTRET_% (committed by the apply POST)."""
    return f"TRANSCRIPTRET_{uuid4().hex[:8]}"


async def _seed_tenant(session: AsyncSession, *, retention_days: int = 30) -> Tenant:
    t = Tenant(
        code=_unique_code(),
        display_name="Retention Tenant",
        state=TenantState.ACTIVE,
        plan=TenantPlan.ENTERPRISE,
        retention_days=retention_days,
    )
    session.add(t)
    await session.flush()
    user = User(tenant_id=t.id, email=f"u_{uuid4().hex[:8]}@example.com")
    session.add(user)
    await session.flush()
    sess = Session(tenant_id=t.id, user_id=user.id, title="s", status="active")
    session.add(sess)
    await session.flush()
    t._seed_session_id = sess.id  # type: ignore[attr-defined]
    return t


async def _seed_message(
    session: AsyncSession, tenant: Tenant, *, seq: int, created_at: datetime
) -> None:
    session.add(
        Message(
            tenant_id=tenant.id,
            session_id=tenant._seed_session_id,  # type: ignore[attr-defined]
            sequence_num=seq,
            turn_num=1,
            role="user",
            content_type="text",
            content={"text": "x"},
            created_at=created_at,
        )
    )
    session.add(
        MessageEvent(
            tenant_id=tenant.id,
            session_id=tenant._seed_session_id,  # type: ignore[attr-defined]
            event_type="llm_request",
            event_data={"n": seq},
            sequence_num=seq,
            timestamp_ms=0,
            created_at=created_at,
        )
    )
    await session.flush()


async def _count_messages(session: AsyncSession, tenant_id: UUID) -> int:
    result = await session.execute(
        select(func.count()).select_from(Message).where(Message.tenant_id == tenant_id)
    )
    return int(result.scalar_one())


# === POST /apply: auth + 404 ===================================================


async def test_apply_requires_admin_role() -> None:
    app = _build_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE_URL) as ac:
        resp = await ac.post(f"/api/v1/admin/tenants/{uuid4()}/transcript-retention/apply")
    assert resp.status_code in (401, 403)


async def test_apply_tenant_not_found(db_session: AsyncSession) -> None:
    app = _build_app(db_session=db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE_URL) as ac:
        resp = await ac.post(f"/api/v1/admin/tenants/{uuid4()}/transcript-retention/apply")
    assert resp.status_code == 404


# === POST /apply: deletion + window =============================================


async def test_apply_deletes_old_keeps_recent(db_session: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    tenant = await _seed_tenant(db_session, retention_days=30)
    await _seed_message(db_session, tenant, seq=1, created_at=now - timedelta(days=60))  # old
    await _seed_message(db_session, tenant, seq=2, created_at=now - timedelta(days=5))  # recent
    assert await _count_messages(db_session, tenant.id) == 2

    app = _build_app(db_session=db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE_URL) as ac:
        resp = await ac.post(f"/api/v1/admin/tenants/{tenant.id}/transcript-retention/apply")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["retention_days"] == 30
    assert body["deleted_messages"] == 1
    assert body["deleted_events"] == 1
    # only the recent row survives
    assert await _count_messages(db_session, tenant.id) == 1


async def test_apply_multi_tenant_isolation(db_session: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    tenant_a = await _seed_tenant(db_session, retention_days=30)
    tenant_b = await _seed_tenant(db_session, retention_days=30)
    await _seed_message(db_session, tenant_a, seq=1, created_at=now - timedelta(days=60))
    await _seed_message(db_session, tenant_b, seq=1, created_at=now - timedelta(days=60))

    app = _build_app(db_session=db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE_URL) as ac:
        resp = await ac.post(f"/api/v1/admin/tenants/{tenant_a.id}/transcript-retention/apply")
    assert resp.status_code == 200, resp.text
    assert resp.json()["deleted_messages"] == 1
    # tenant B's old row is UNTOUCHED (isolation)
    assert await _count_messages(db_session, tenant_a.id) == 0
    assert await _count_messages(db_session, tenant_b.id) == 1


async def test_apply_audit_chain_emitted(db_session: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    tenant = await _seed_tenant(db_session, retention_days=30)
    await _seed_message(db_session, tenant, seq=1, created_at=now - timedelta(days=60))

    app = _build_app(db_session=db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE_URL) as ac:
        resp = await ac.post(f"/api/v1/admin/tenants/{tenant.id}/transcript-retention/apply")
    assert resp.status_code == 200, resp.text

    result = await db_session.execute(
        select(AuditLog)
        .where(AuditLog.tenant_id == tenant.id)
        .where(AuditLog.operation == "tenant_transcript_retention_apply")
    )
    entries = result.scalars().all()
    assert len(entries) == 1
    audit = entries[0]
    assert audit.resource_type == "tenant"
    assert audit.operation_data["deleted_messages"] == 1
    assert audit.operation_data["retention_days"] == 30
    assert audit.operation_result == "success"


# === GET /preview: dry-run (no deletion) ========================================


async def test_preview_counts_without_deleting(db_session: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    tenant = await _seed_tenant(db_session, retention_days=30)
    await _seed_message(db_session, tenant, seq=1, created_at=now - timedelta(days=60))  # old
    await _seed_message(db_session, tenant, seq=2, created_at=now - timedelta(days=5))  # recent

    app = _build_app(db_session=db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE_URL) as ac:
        resp = await ac.get(f"/api/v1/admin/tenants/{tenant.id}/transcript-retention/preview")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["retention_days"] == 30
    assert body["would_delete_messages"] == 1
    assert body["would_delete_events"] == 1
    # NOTHING deleted (dry-run): both rows still present
    assert await _count_messages(db_session, tenant.id) == 2


async def test_preview_tenant_not_found(db_session: AsyncSession) -> None:
    app = _build_app(db_session=db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE_URL) as ac:
        resp = await ac.get(f"/api/v1/admin/tenants/{uuid4()}/transcript-retention/preview")
    assert resp.status_code == 404
