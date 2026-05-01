"""platform_layer.identity — multi-tenant auth, RBAC, JWT, RLS context.

Sprint 49.2 (basic tenant_id), Sprint 49.3 (RLS policies + RBAC),
Sprint 52.5 Day 1.2 (P0 #14: JWT module + standardised FastAPI deps).
"""

from platform_layer.identity.auth import (
    get_current_tenant,
    get_current_user_id,
)
from platform_layer.identity.jwt import (
    JWTAuthError,
    JWTClaims,
    JWTExpiredError,
    JWTInvalidError,
    JWTManager,
)

__all__ = [
    "JWTAuthError",
    "JWTClaims",
    "JWTExpiredError",
    "JWTInvalidError",
    "JWTManager",
    "get_current_tenant",
    "get_current_user_id",
]
