"""
File: backend/src/platform_layer/middleware/tenant_context.py
Purpose: JWT-decoded tenant scope — populate request.state + SET LOCAL app.tenant_id.
Category: Platform layer / Middleware (cross-cutting; ranges 9 governance + multi-tenancy)
Scope: Sprint 49.3 (Day 4.4) — Sprint 52.5 Day 6.1 (P0 #14 phase 2: JWT swap)
Owner: platform_layer owner

Description:
    Two collaborating pieces:

    1. TenantContextMiddleware (BaseHTTPMiddleware)
       - Reads `Authorization: Bearer <jwt>` header.
       - Decodes via JWTManager (signature + expiration).
       - Populates request.state with: tenant_id (UUID), user_id (UUID),
         roles (list[str]).
       - Returns 401 (header missing / token expired / signature bad).

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

    Sprint 52.5 P0 #14 rationale: V1 W1-2 audit confirmed that reading
    tenant_id from `X-Tenant-Id` header is trivially spoofable —
    the request body / query / header are all client-controlled. Only
    JWT decoded with the server-side secret is authoritative. The
    request.state.tenant_id contract is unchanged so endpoints + the
    `get_current_tenant` dep in platform_layer.identity continue to
    work without code changes.

Created: 2026-04-29 (Sprint 49.3 Day 4.4)
Last Modified: 2026-05-01

Modification History (newest-first):
    - 2026-05-01: Sprint 52.5 Day 6.1 (P0 #14) — replace X-Tenant-Id
        header path with Authorization Bearer JWT decode. user_id +
        roles are now also populated from JWT claims. EXEMPT path
        prefixes unchanged.
    - 2026-04-29: Initial creation (Sprint 49.3 Day 4.4)

Related:
    - 0009_rls_policies.py — the policies this dep activates per-request
    - .claude/rules/multi-tenant-data.md 鐵律 3 (every endpoint dep)
    - 14-security-deep-dive.md §RLS / SET LOCAL
    - sprint-49-3-plan.md §3 (SET LOCAL middleware)
    - claudedocs/5-status/V2-AUDIT-OPEN-ISSUES-20260501.md issue #14
    - platform_layer/identity/jwt.py — JWTManager (decode source)
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
from platform_layer.identity.jwt import (
    JWTAuthError,
    JWTExpiredError,
    JWTInvalidError,
    JWTManager,
)


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Extract Bearer JWT + populate request.state.{tenant_id, user_id, roles}.

    Returns 401 on:
        - missing/empty Authorization header
        - non-Bearer scheme
        - expired token
        - invalid signature / malformed token / missing required claim

    System endpoints listed in EXEMPT_PATH_PREFIXES are skipped — they're
    infrastructure (k8s probes / OTel scrape / auth gateway dispatch) and have
    no tenant scope. Adding a path here is a deliberate decision: it MUST NOT
    touch tenant-scoped tables.
    """

    AUTH_HEADER = "Authorization"
    BEARER_PREFIX = "Bearer "

    # Paths exempt from tenant header requirement. Sprint 49.4 Day 5 added
    # /api/v1/health for k8s probes. Add new paths only with code review.
    EXEMPT_PATH_PREFIXES: tuple[str, ...] = ("/api/v1/health",)

    def __init__(
        self,
        app: ASGIApp,
        *,
        jwt_manager: JWTManager | None = None,
    ) -> None:
        super().__init__(app)
        # Lazy default — resolves Settings the first time the middleware
        # processes a request, so tests can construct the app under custom
        # JWT_SECRET env vars without ordering pain.
        self._jwt_manager = jwt_manager

    def _get_jwt_manager(self) -> JWTManager:
        if self._jwt_manager is None:
            self._jwt_manager = JWTManager()
        return self._jwt_manager

    async def dispatch(self, request, call_next):  # type: ignore[no-untyped-def]
        path = request.url.path
        for prefix in self.EXEMPT_PATH_PREFIXES:
            if path == prefix or path.startswith(prefix + "/"):
                return await call_next(request)

        raw = request.headers.get(self.AUTH_HEADER)
        if not raw or not raw.startswith(self.BEARER_PREFIX):
            return JSONResponse(
                {"error": "Authorization Bearer token required"},
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="api"'},
            )
        token = raw[len(self.BEARER_PREFIX):].strip()
        if not token:
            return JSONResponse(
                {"error": "Bearer token is empty"},
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="api"'},
            )

        try:
            claims = self._get_jwt_manager().decode(token)
        except JWTExpiredError:
            return JSONResponse(
                {"error": "token expired"},
                status_code=401,
                headers={
                    "WWW-Authenticate": 'Bearer error="invalid_token", '
                    'error_description="expired"'
                },
            )
        except JWTInvalidError:
            return JSONResponse(
                {"error": "token invalid"},
                status_code=401,
                headers={
                    "WWW-Authenticate": 'Bearer error="invalid_token"'
                },
            )
        except JWTAuthError:
            # Catch-all for any other JWTAuthError subclass added later.
            return JSONResponse(
                {"error": "authentication failed"}, status_code=401
            )

        # Parse user_id from `sub`. JWT spec stores sub as string; we expect
        # UUID-shaped values from our own issuer. If `sub` cannot parse,
        # treat as auth failure (not 500) — the issuer is misconfigured.
        try:
            user_id = UUID(claims.sub)
        except (ValueError, TypeError):
            return JSONResponse(
                {"error": "token sub is not a valid UUID"},
                status_code=401,
                headers={
                    "WWW-Authenticate": 'Bearer error="invalid_token"'
                },
            )

        request.state.tenant_id = claims.tenant_id
        request.state.user_id = user_id
        request.state.roles = list(claims.roles)
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
