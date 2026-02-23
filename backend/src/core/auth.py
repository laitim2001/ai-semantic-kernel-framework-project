# =============================================================================
# IPA Platform - Global Authentication Dependency
# =============================================================================
# Sprint 111: S111-7 - Global Auth Middleware
# Phase 31: Security Hardening + Quick Wins
#
# Lightweight JWT validation dependency for global route protection.
# Does NOT require database lookup — only validates JWT token structure
# and extracts claims. Use this for router-level dependencies.
#
# For full user validation with DB lookup, use:
#   src.api.v1.dependencies.get_current_user
#
# Dependencies:
#   - python-jose[cryptography]
#   - Settings (src.core.config)
# =============================================================================

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from src.core.config import get_settings

logger = logging.getLogger(__name__)

# HTTPBearer scheme — extracts token from "Authorization: Bearer <token>" header
# auto_error=True means missing token returns 401 automatically
security = HTTPBearer(
    scheme_name="JWT",
    description="JWT Bearer token authentication",
    auto_error=True,
)

# Optional version — returns None if token is missing (for public routes)
security_optional = HTTPBearer(
    scheme_name="JWT",
    description="JWT Bearer token authentication (optional)",
    auto_error=False,
)


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Lightweight JWT token validation (no DB lookup).

    Validates the JWT token and extracts claims. Returns a dict with:
    - user_id: The subject (sub) claim
    - role: The user role
    - Additional JWT claims

    This is used as a global router dependency to ensure all protected
    endpoints require a valid JWT token.

    For endpoints that need the full User model from database, use
    src.api.v1.dependencies.get_current_user instead.

    Raises:
        HTTPException(401): If token is missing, invalid, or expired
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return {
            "user_id": user_id,
            "role": payload.get("role", "viewer"),
            "email": payload.get("email"),
            "exp": payload.get("exp"),
            "iat": payload.get("iat"),
        }

    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_auth_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
) -> Optional[dict]:
    """
    Optional JWT validation. Returns None if no token is provided.

    Useful for endpoints that work differently for authenticated vs anonymous users.
    """
    if not credentials:
        return None

    try:
        return await require_auth(credentials)
    except HTTPException:
        return None
