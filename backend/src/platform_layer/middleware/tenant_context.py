"""
File: backend/src/platform_layer/middleware/tenant_context.py
Purpose: Per-request tenant scope — extract X-Tenant-Id header + SET LOCAL app.tenant_id.
Category: Platform layer / Middleware (cross-cutting; ranges 9 governance + multi-tenancy)
Scope: Sprint 49.3 (Day 4.4 - tenant context middleware + DB session dep)
Owner: platform_layer owner

Description:
    Two collaborating pieces:

    1. TenantContextMiddleware (BaseHTTPMiddleware)
       - Reads `X-Tenant-Id` header from incoming HTTP request.
       - Validates as UUID; populates request.state.tenant_id.
       - Returns 401 (header missing) or 400 (header invalid) on error.

    2. get_db_session_with_tenant (async generator dep)
       - FastAPI dependency for per-endpoint use.
       - Reads request.state.tenant_id (set by middleware).
       - Opens an AsyncSession + executes `SET LOCAL app.tenant_id = :tid`
         so PostgreSQL RLS policies (migration 0009) filter rows correctly.
       - SET LOCAL is scoped to the current transaction so it does not
         persist across requests sharing a connection from the pool.

    Endpoints MUST use this dep (not the raw get_db_session) for any
    query that touches tenant-scoped tables. RLS will return zero rows
    if app.tenant_id is unset, so a missing dep would manifest as a
    silent empty result rather than a leak — but we still treat it as
    an error and require the dep explicitly.

    Phase 49.4+ will replace the header path with JWT extraction. The
    request.state.tenant_id contract stays identical so endpoints don't
    change.

Created: 2026-04-29 (Sprint 49.3 Day 4.4)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.3 Day 4.4)

Related:
    - 0009_rls_policies.py — the policies this dep activates per-request
    - .claude/rules/multi-tenant-data.md 鐵律 3 (every endpoint dep)
    - 14-security-deep-dive.md §RLS / SET LOCAL
    - sprint-49-3-plan.md §3 (SET LOCAL middleware)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from infrastructure.db.engine import get_session_factory


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Extract X-Tenant-Id from header + populate request.state.tenant_id.

    Returns 401 if header missing; 400 if header is not a valid UUID.

    System endpoints listed in EXEMPT_PATH_PREFIXES are skipped — they're
    infrastructure (k8s probes / OTel scrape / auth gateway dispatch) and have
    no tenant scope. Adding a path here is a deliberate decision: it MUST NOT
    touch tenant-scoped tables.
    """

    HEADER_NAME = "X-Tenant-Id"

    # Paths exempt from tenant header requirement. Sprint 49.4 Day 5 added
    # /api/v1/health for k8s probes. Add new paths only with code review.
    EXEMPT_PATH_PREFIXES: tuple[str, ...] = ("/api/v1/health",)

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request, call_next):  # type: ignore[no-untyped-def]
        path = request.url.path
        for prefix in self.EXEMPT_PATH_PREFIXES:
            if path == prefix or path.startswith(prefix + "/"):
                return await call_next(request)

        raw = request.headers.get(self.HEADER_NAME)
        if not raw:
            return JSONResponse(
                {"error": "X-Tenant-Id header required"},
                status_code=401,
            )
        try:
            tenant_id = UUID(raw)
        except ValueError:
            return JSONResponse(
                {"error": "X-Tenant-Id is not a valid UUID"},
                status_code=400,
            )
        request.state.tenant_id = tenant_id
        return await call_next(request)


async def get_db_session_with_tenant(
    request: Request,
) -> AsyncIterator[AsyncSession]:
    """FastAPI dep — open AsyncSession + SET LOCAL app.tenant_id for RLS.

    Usage:
        @router.get("/sessions")
        async def list_sessions(
            db: AsyncSession = Depends(get_db_session_with_tenant),
        ) -> list[Session]:
            return (await db.execute(select(Session))).scalars().all()

    Every Session query above is auto-filtered to the request's tenant
    by the policies in migration 0009.
    """
    if not hasattr(request.state, "tenant_id"):
        # Should never happen if TenantContextMiddleware is installed
        # before the routes; defensive raise rather than silent empty.
        raise RuntimeError(
            "request.state.tenant_id missing — TenantContextMiddleware not installed?"
        )
    tenant_id: UUID = request.state.tenant_id

    factory = get_session_factory()
    async with factory() as session:
        # set_config(...) is the function form of SET LOCAL; using it
        # via parameterised SQL avoids string-interpolating the UUID.
        # The third arg `is_local=true` mirrors SET LOCAL semantics.
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tid, true)"),
            {"tid": str(tenant_id)},
        )
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
