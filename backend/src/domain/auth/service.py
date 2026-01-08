# =============================================================================
# IPA Platform - Auth Service
# =============================================================================
# Sprint 70: S70-2 - UserRepository + AuthService
# Phase 18: Authentication System
#
# Core authentication service providing:
#   - User registration with email uniqueness validation
#   - User authentication with password verification
#   - Token generation and refresh
#   - Current user retrieval from token
#
# Dependencies:
#   - UserRepository (src.infrastructure.database.repositories.user)
#   - Security utilities (src.core.security)
# =============================================================================

from datetime import datetime
from typing import Tuple

from src.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from src.core.security.jwt import create_refresh_token
from src.infrastructure.database.models.user import User
from src.infrastructure.database.repositories.user import UserRepository


class AuthService:
    """
    Authentication service for user registration and login.

    Provides:
        - register: Create new user with hashed password
        - authenticate: Verify credentials and return token
        - get_user_from_token: Validate token and return user
        - refresh_token: Exchange refresh token for new access token
    """

    def __init__(self, user_repo: UserRepository):
        """
        Initialize service with user repository.

        Args:
            user_repo: UserRepository instance
        """
        self.user_repo = user_repo

    async def register(
        self,
        email: str,
        password: str,
        full_name: str | None = None,
    ) -> Tuple[User, str]:
        """
        Register a new user.

        Creates user with hashed password and returns access token.

        Args:
            email: User email address
            password: Plain text password (will be hashed)
            full_name: Optional display name

        Returns:
            Tuple of (User instance, access token)

        Raises:
            ValueError: If email is already registered
        """
        # Check email uniqueness
        if await self.user_repo.email_exists(email):
            raise ValueError("Email already registered")

        # Create user with hashed password
        user = await self.user_repo.create(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role="viewer",  # Default role
            is_active=True,
        )

        # Generate access token
        token = create_access_token(
            user_id=str(user.id),
            role=user.role,
        )

        return user, token

    async def authenticate(
        self,
        email: str,
        password: str,
    ) -> Tuple[User, str, str]:
        """
        Authenticate user with email and password.

        Verifies credentials and returns access and refresh tokens.
        Updates last_login timestamp on success.

        Args:
            email: User email address
            password: Plain text password

        Returns:
            Tuple of (User instance, access token, refresh token)

        Raises:
            ValueError: If credentials are invalid or user inactive
        """
        # Get active user by email
        user = await self.user_repo.get_active_by_email(email)
        if not user:
            raise ValueError("Invalid credentials")

        # Verify password
        if not verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")

        # Update last login
        await self.user_repo.update(
            user.id,
            last_login=datetime.utcnow(),
        )

        # Generate tokens
        access_token = create_access_token(
            user_id=str(user.id),
            role=user.role,
        )
        refresh_token = create_refresh_token(
            user_id=str(user.id),
            role=user.role,
        )

        return user, access_token, refresh_token

    async def get_user_from_token(self, token: str) -> User:
        """
        Get user from JWT token.

        Decodes token and retrieves user from database.

        Args:
            token: JWT access token

        Returns:
            User instance

        Raises:
            ValueError: If token is invalid or user not found
        """
        try:
            payload = decode_token(token)
        except ValueError as e:
            raise ValueError(f"Invalid token: {e}")

        user = await self.user_repo.get(payload.sub)
        if not user:
            raise ValueError("User not found")

        if not user.is_active:
            raise ValueError("User account is inactive")

        return user

    async def refresh_access_token(self, refresh_token: str) -> Tuple[str, str]:
        """
        Exchange refresh token for new access token.

        Args:
            refresh_token: JWT refresh token

        Returns:
            Tuple of (new access token, new refresh token)

        Raises:
            ValueError: If refresh token is invalid
        """
        try:
            payload = decode_token(refresh_token)
        except ValueError as e:
            raise ValueError(f"Invalid refresh token: {e}")

        # Verify user still exists and is active
        user = await self.user_repo.get(payload.sub)
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")

        # Generate new tokens
        new_access_token = create_access_token(
            user_id=str(user.id),
            role=user.role,
        )
        new_refresh_token = create_refresh_token(
            user_id=str(user.id),
            role=user.role,
        )

        return new_access_token, new_refresh_token

    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
    ) -> bool:
        """
        Change user password.

        Args:
            user_id: User UUID
            current_password: Current plain text password
            new_password: New plain text password

        Returns:
            True if password changed successfully

        Raises:
            ValueError: If current password is incorrect or user not found
        """
        user = await self.user_repo.get(user_id)
        if not user:
            raise ValueError("User not found")

        if not verify_password(current_password, user.hashed_password):
            raise ValueError("Current password is incorrect")

        await self.user_repo.update(
            user.id,
            hashed_password=hash_password(new_password),
        )

        return True
