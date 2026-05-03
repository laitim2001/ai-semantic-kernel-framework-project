"""
File: backend/src/platform_layer/identity/auth.py
Purpose: FastAPI dependencies — get_current_tenant + get_current_user_id from
JWT-decoded request.state populated by TenantContextMiddleware.
Category: Platform layer / Identity (cross-cutting; multi-tenant 鐵律 3 dep)
Scope: Sprint 52.5 Day 1.2 (P0 #14 — replaces middleware/{tenant,auth}.py V1 stubs)
Owner: platform_layer/identity owner

Description:
    These deps are the *single canonical source* for tenant/user identity
    in V2. Every business endpoint MUST use them (or downstream wrappers
    like `get_db_session_with_tenant`) to ensure tenant_id is taken from
    the verified JWT, never from request bodies / query params / headers.

    `request.state.tenant_id` and `request.state.user_id` are populated
    by `TenantContextMiddleware` (Day 6.1 will rewrite that middleware
    to JWT-decode; Day 1.2 ships the deps + JWTManager so endpoints can
    declare `Depends(get_current_tenant)` immediately).

    Until Day 6.1 lands, callers will receive 401 because middleware
    still reads X-Tenant-Id (no user_id set). This is acceptable: the
    failing-fast behaviour is preferable to silent fallback to header
    spoofing — i.e. no production endpoint shall be wired up until the
    middleware change is in.

Key Components:
    - get_current_tenant(request) -> UUID
    - get_current_user_id(request) -> UUID

Created: 2026-05-01 (Sprint 52.5 Day 1.2)
Last Modified: 2026-05-01

Modification History:
    - 2026-05-04: Add require_audit_role RBAC dep (Sprint 53.5 US-5 — auditor / admin / compliance)
    - 2026-05-01: Initial creation (Sprint 52.5 Day 1.2) — replaces V1 stubs

Related:
    - platform_layer/identity/jwt.py — JWT decode (authoritative source)
    - platform_layer/middleware/tenant_context.py — populates request.state
    - .claude/rules/multi-tenant-data.md 鐵律 3 (every business endpoint)
    - claudedocs/5-status/V2-AUDIT-OPEN-ISSUES-20260501.md — issue #14
    - V1 stubs (to be removed Day 6): backend/src/middleware/{tenant,auth}.py
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, Request, status

_AUTH_REQUIRED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Authentication required",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_tenant(request: Request) -> UUID:
    """Return UUID of the authenticated tenant.

    Reads `request.state.tenant_id` populated by TenantContextMiddleware
    after successful JWT decode. Raises 401 if absent — this should be
    impossible if middleware is installed before the routes; the explicit
    raise (rather than silent default) prevents endpoints from running
    against a missing tenant_id (which would mean RLS sees nothing AND
    rows could be inserted without tenant scope).
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id is None:
        raise _AUTH_REQUIRED
    if not isinstance(tenant_id, UUID):
        # Defensive: middleware contract is to set a UUID. If it isn't,
        # something upstream is wrong; fail fast rather than coerce.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="tenant_id middleware contract violated",
        )
    return tenant_id


async def get_current_user_id(request: Request) -> UUID:
    """Return UUID of the authenticated user.

    Same shape as `get_current_tenant`, populated from JWT `sub` claim.
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise _AUTH_REQUIRED
    if not isinstance(user_id, UUID):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="user_id middleware contract violated",
        )
    return user_id


# RBAC roles permitted to read audit_log (Sprint 53.5 US-5).
# Single-source: JWT 'roles' claim list[str].
_AUDIT_ROLES: frozenset[str] = frozenset({"auditor", "admin", "compliance"})


async def require_audit_role(request: Request) -> UUID:
    """Authorize the caller for audit endpoints.

    Returns the authenticated user_id once role membership is verified.
    Raises 401 if no JWT context (middleware must run first); 403 if the
    JWT's roles claim does not intersect _AUDIT_ROLES.

    Used by GET /api/v1/audit/log and /api/v1/audit/verify-chain.
    """
    user_id = await get_current_user_id(request)
    roles = getattr(request.state, "roles", None)
    if not isinstance(roles, list):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="roles middleware contract violated",
        )
    if not any(r in _AUDIT_ROLES for r in roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Audit role required",
        )
    return user_id


__all__ = [
    "get_current_tenant",
    "get_current_user_id",
    "require_audit_role",
]
