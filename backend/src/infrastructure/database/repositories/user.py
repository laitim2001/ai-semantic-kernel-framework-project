# =============================================================================
# IPA Platform - User Repository
# =============================================================================
# Sprint 70: S70-2 - UserRepository + AuthService
# Phase 18: Authentication System
#
# Repository for User model with authentication-related queries.
#
# Dependencies:
#   - BaseRepository (src.infrastructure.database.repositories.base)
#   - User Model (src.infrastructure.database.models.user)
# =============================================================================

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.base import BaseRepository
from src.infrastructure.database.models.user import User


class UserRepository(BaseRepository[User]):
    """
    Repository for User model with authentication queries.

    Extends BaseRepository with:
        - get_by_email: Find user by email address
        - get_active_by_email: Find active user by email
    """

    model = User

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        super().__init__(session)

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.

        Args:
            email: Email address to search for

        Returns:
            User instance or None if not found

        Example:
            >>> user = await repo.get_by_email("user@example.com")
        """
        stmt = select(self.model).where(self.model.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_email(self, email: str) -> Optional[User]:
        """
        Get active user by email address.

        Only returns users where is_active=True.

        Args:
            email: Email address to search for

        Returns:
            Active User instance or None if not found or inactive

        Example:
            >>> user = await repo.get_active_by_email("user@example.com")
        """
        stmt = select(self.model).where(
            self.model.email == email,
            self.model.is_active == True,  # noqa: E712
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        """
        Check if an email is already registered.

        Args:
            email: Email address to check

        Returns:
            True if email exists, False otherwise
        """
        user = await self.get_by_email(email)
        return user is not None
