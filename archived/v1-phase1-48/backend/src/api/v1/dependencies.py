# =============================================================================
# IPA Platform - API Dependencies
# =============================================================================
# Sprint 70: S70-4 - Auth Dependency Injection
# Phase 18: Authentication System
#
# Common dependency injection providers for API routes.
# Provides authentication dependencies:
#   - get_current_user: Required authentication
#   - get_current_user_optional: Optional authentication
#
# Dependencies:
#   - Security utilities (src.core.security)
#   - UserRepository (src.infrastructure.database.repositories.user)
# =============================================================================

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import decode_token
from src.infrastructure.database import get_session
from src.infrastructure.database.models.user import User
from src.infrastructure.database.repositories.user import UserRepository

logger = logging.getLogger(__name__)


# =============================================================================
# OAuth2 Schemes
# =============================================================================

# Required token - raises 401 if not provided
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scheme_name="JWT",
    description="JWT Bearer token authentication",
)

# Optional token - returns None if not provided
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scheme_name="JWT",
    description="JWT Bearer token authentication (optional)",
    auto_error=False,
)


# =============================================================================
# Authentication Dependencies
# =============================================================================


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Get current authenticated user from JWT token.

    Validates the token and retrieves the user from database.
    Returns 401 if token is invalid or user not found.

    Usage:
        @router.get("/protected")
        async def protected_route(
            current_user: User = Depends(get_current_user)
        ):
            return {"user": current_user.email}
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        user_id = payload.sub
        if not user_id:
            raise credentials_exception
    except ValueError as e:
        logger.warning(f"Token validation failed: {e}")
        raise credentials_exception

    user_repo = UserRepository(session)
    user = await user_repo.get(user_id)

    if not user:
        logger.warning(f"User not found for token: {user_id}")
        raise credentials_exception

    if not user.is_active:
        logger.warning(f"Inactive user attempted access: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    session: AsyncSession = Depends(get_session),
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise None.

    For routes that work with or without authentication.
    Does not raise error if token is missing or invalid.

    Usage:
        @router.get("/public")
        async def public_route(
            current_user: Optional[User] = Depends(get_current_user_optional)
        ):
            if current_user:
                return {"greeting": f"Hello, {current_user.email}!"}
            return {"greeting": "Hello, guest!"}
    """
    if not token:
        return None

    try:
        return await get_current_user(token, session)
    except HTTPException:
        return None


async def get_current_active_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current user and verify admin role.

    Returns 403 if user is not an admin.

    Usage:
        @router.delete("/admin-only/{id}")
        async def admin_route(
            admin: User = Depends(get_current_active_admin)
        ):
            return {"admin": admin.email}
    """
    if current_user.role != "admin":
        logger.warning(f"Non-admin user attempted admin action: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def get_current_operator_or_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current user and verify operator or admin role.

    Returns 403 if user is viewer only.

    Usage:
        @router.post("/operator-action")
        async def operator_route(
            user: User = Depends(get_current_operator_or_admin)
        ):
            return {"user": user.email}
    """
    if current_user.role not in ("admin", "operator"):
        logger.warning(f"Viewer attempted operator action: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator or admin access required",
        )
    return current_user
