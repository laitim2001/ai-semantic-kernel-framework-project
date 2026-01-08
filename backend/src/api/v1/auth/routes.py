# =============================================================================
# IPA Platform - Auth API Routes
# =============================================================================
# Sprint 70: S70-3 - Auth API Routes
# Phase 18: Authentication System
#
# Authentication API endpoints:
#   - POST /register: Create new user account
#   - POST /login: Authenticate and get tokens
#   - POST /refresh: Exchange refresh token for new access token
#   - GET /me: Get current user info
#
# Dependencies:
#   - AuthService (src.domain.auth.service)
#   - UserRepository (src.infrastructure.database.repositories.user)
# =============================================================================

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.domain.auth.schemas import (
    TokenRefresh,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from src.domain.auth.service import AuthService
from src.infrastructure.database.connection import get_session
from src.infrastructure.database.models.user import User
from src.infrastructure.database.repositories.user import UserRepository
from src.api.v1.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# =============================================================================
# Dependencies
# =============================================================================


async def get_auth_service(
    session: AsyncSession = Depends(get_session),
) -> AuthService:
    """Get AuthService instance with injected dependencies."""
    user_repo = UserRepository(session)
    return AuthService(user_repo)


# =============================================================================
# Routes
# =============================================================================


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account and return access token.",
)
async def register(
    data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Register a new user account.

    - **email**: Valid email address (must be unique)
    - **password**: Password (min 8 characters)
    - **full_name**: Optional display name

    Returns access token on successful registration.
    """
    try:
        user, access_token = await auth_service.register(
            email=data.email,
            password=data.password,
            full_name=data.full_name,
        )

        settings = get_settings()
        logger.info(f"User registered: {user.email}")

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )

    except ValueError as e:
        logger.warning(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
    description="Authenticate with email and password to get tokens.",
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Authenticate user and return tokens.

    Uses OAuth2 password flow:
    - **username**: User email address
    - **password**: User password

    Returns access and refresh tokens on success.
    """
    try:
        user, access_token, refresh_token = await auth_service.authenticate(
            email=form_data.username,  # OAuth2 uses "username" field
            password=form_data.password,
        )

        settings = get_settings()
        logger.info(f"User logged in: {user.email}")

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
            refresh_token=refresh_token,
        )

    except ValueError:
        logger.warning(f"Login failed for: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Exchange refresh token for new access token.",
)
async def refresh_token(
    data: TokenRefresh,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Exchange refresh token for new access token.

    - **refresh_token**: Valid refresh token from login

    Returns new access and refresh tokens.
    """
    try:
        new_access_token, new_refresh_token = await auth_service.refresh_access_token(
            refresh_token=data.refresh_token,
        )

        settings = get_settings()
        logger.info("Token refreshed successfully")

        return TokenResponse(
            access_token=new_access_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
            refresh_token=new_refresh_token,
        )

    except ValueError as e:
        logger.warning(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get information about the currently authenticated user.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Get current user information.

    Requires valid access token in Authorization header.
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
    )
