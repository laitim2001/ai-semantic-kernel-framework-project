# =============================================================================
# IPA Platform - Auth Dependencies
# =============================================================================
# Sprint 75: File Upload Feature
# Phase 20: File Attachment Support
#
# Convenience dependencies for getting user ID from authenticated user.
# Re-exports common auth dependencies from src.api.v1.dependencies.
# =============================================================================

from typing import Optional

from fastapi import Depends

from src.api.v1.dependencies import (
    get_current_user,
    get_current_user_optional,
    get_current_active_admin,
    get_current_operator_or_admin,
)
from src.infrastructure.database.models.user import User


async def get_current_user_id(
    current_user: User = Depends(get_current_user),
) -> str:
    """
    Get current authenticated user's ID as string.

    Convenience dependency for routes that only need user ID.

    Usage:
        @router.get("/my-resource")
        async def my_route(user_id: str = Depends(get_current_user_id)):
            return {"user_id": user_id}
    """
    return str(current_user.id)


async def get_current_user_id_optional(
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> Optional[str]:
    """
    Get current user's ID if authenticated, otherwise None.

    Usage:
        @router.get("/public")
        async def public_route(
            user_id: Optional[str] = Depends(get_current_user_id_optional)
        ):
            return {"user_id": user_id}
    """
    return str(current_user.id) if current_user else None


# Re-export for convenience
__all__ = [
    "get_current_user",
    "get_current_user_optional",
    "get_current_user_id",
    "get_current_user_id_optional",
    "get_current_active_admin",
    "get_current_operator_or_admin",
]
