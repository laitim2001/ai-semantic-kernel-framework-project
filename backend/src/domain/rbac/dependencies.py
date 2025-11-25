"""
RBAC Dependencies

Sprint 3 - Story S3-1: RBAC Permission System

Provides FastAPI dependencies for permission checking.
"""
from __future__ import annotations

import logging
from functools import wraps
from typing import Callable, List, Optional, Set
from uuid import UUID

from fastapi import Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.database.session import get_db
from src.infrastructure.database.models.user import User
from src.infrastructure.database.models.rbac import Role, Permission, user_roles

logger = logging.getLogger(__name__)


class PermissionChecker:
    """Permission checker dependency for FastAPI.

    Checks if the current user has the required permission.

    Example:
        @router.post("/workflows/")
        async def create_workflow(
            permission: bool = Depends(PermissionChecker("workflow", "create"))
        ):
            ...
    """

    def __init__(self, resource: str, action: str):
        """Initialize permission checker.

        Args:
            resource: Resource type (e.g., "workflow")
            action: Action type (e.g., "create")
        """
        self.resource = resource
        self.action = action

    async def __call__(
        self,
        request: Request,
        db: AsyncSession = Depends(get_db),
    ) -> bool:
        """Check if current user has permission.

        Args:
            request: FastAPI request
            db: Database session

        Returns:
            True if user has permission

        Raises:
            HTTPException: If not authenticated or no permission
        """
        # Get current user from request state (set by auth middleware)
        current_user = getattr(request.state, "user", None)

        if not current_user:
            # Try to get user ID from request headers (for testing/development)
            user_id_header = request.headers.get("X-User-ID")
            if user_id_header:
                try:
                    user_id = UUID(user_id_header)
                    result = await db.execute(
                        select(User).where(User.id == user_id)
                    )
                    current_user = result.scalar_one_or_none()
                except (ValueError, Exception):
                    pass

        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Superusers have all permissions
        if current_user.is_superuser:
            return True

        # Check user's roles for permission
        result = await db.execute(
            select(Role)
            .join(user_roles, Role.id == user_roles.c.role_id)
            .where(user_roles.c.user_id == current_user.id)
            .where(Role.is_active == True)
            .options(selectinload(Role.permissions))
        )
        roles = result.scalars().all()

        for role in roles:
            if role.has_permission(self.resource, self.action):
                logger.debug(
                    f"Permission granted: {self.resource}:{self.action} "
                    f"for user {current_user.email} via role {role.name}"
                )
                return True

        logger.warning(
            f"Permission denied: {self.resource}:{self.action} "
            f"for user {current_user.email}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {self.resource}:{self.action}",
        )


def require_permission(resource: str, action: str):
    """Decorator for requiring permission on an endpoint.

    Args:
        resource: Resource type
        action: Action type

    Returns:
        Dependency that checks permission

    Example:
        @router.post("/workflows/")
        @require_permission("workflow", "create")
        async def create_workflow():
            ...
    """
    return Depends(PermissionChecker(resource, action))


async def get_current_user_permissions(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Set[str]:
    """Get all permissions for the current user.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Set of permission names

    Raises:
        HTTPException: If not authenticated
    """
    current_user = getattr(request.state, "user", None)

    if not current_user:
        user_id_header = request.headers.get("X-User-ID")
        if user_id_header:
            try:
                user_id = UUID(user_id_header)
                result = await db.execute(
                    select(User).where(User.id == user_id)
                )
                current_user = result.scalar_one_or_none()
            except (ValueError, Exception):
                pass

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Superusers have all permissions
    if current_user.is_superuser:
        result = await db.execute(select(Permission))
        permissions = result.scalars().all()
        return {p.name for p in permissions}

    # Get user's roles with permissions
    result = await db.execute(
        select(Role)
        .join(user_roles, Role.id == user_roles.c.role_id)
        .where(user_roles.c.user_id == current_user.id)
        .where(Role.is_active == True)
        .options(selectinload(Role.permissions))
    )
    roles = result.scalars().all()

    permissions: Set[str] = set()
    for role in roles:
        for perm in role.permissions:
            permissions.add(perm.name)

    return permissions


class RoleChecker:
    """Role checker dependency for FastAPI.

    Checks if the current user has one of the required roles.

    Example:
        @router.get("/admin/")
        async def admin_dashboard(
            role_check: bool = Depends(RoleChecker(["Admin", "PowerUser"]))
        ):
            ...
    """

    def __init__(self, required_roles: List[str]):
        """Initialize role checker.

        Args:
            required_roles: List of role names (user needs at least one)
        """
        self.required_roles = required_roles

    async def __call__(
        self,
        request: Request,
        db: AsyncSession = Depends(get_db),
    ) -> bool:
        """Check if current user has required role.

        Args:
            request: FastAPI request
            db: Database session

        Returns:
            True if user has role

        Raises:
            HTTPException: If not authenticated or no role
        """
        current_user = getattr(request.state, "user", None)

        if not current_user:
            user_id_header = request.headers.get("X-User-ID")
            if user_id_header:
                try:
                    user_id = UUID(user_id_header)
                    result = await db.execute(
                        select(User).where(User.id == user_id)
                    )
                    current_user = result.scalar_one_or_none()
                except (ValueError, Exception):
                    pass

        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )

        # Superusers pass all role checks
        if current_user.is_superuser:
            return True

        # Check user's roles
        result = await db.execute(
            select(Role)
            .join(user_roles, Role.id == user_roles.c.role_id)
            .where(user_roles.c.user_id == current_user.id)
            .where(Role.is_active == True)
        )
        user_roles_list = result.scalars().all()

        for role in user_roles_list:
            if role.name in self.required_roles:
                return True

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role required: one of {self.required_roles}",
        )


def require_role(*role_names: str):
    """Decorator for requiring one of the specified roles.

    Args:
        role_names: Required role names (user needs at least one)

    Returns:
        Dependency that checks role
    """
    return Depends(RoleChecker(list(role_names)))


async def require_admin(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Require admin access.

    Checks if user is superuser or has Admin role.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Current user if admin

    Raises:
        HTTPException: If not admin
    """
    current_user = getattr(request.state, "user", None)

    if not current_user:
        user_id_header = request.headers.get("X-User-ID")
        if user_id_header:
            try:
                user_id = UUID(user_id_header)
                result = await db.execute(
                    select(User).where(User.id == user_id)
                )
                current_user = result.scalar_one_or_none()
            except (ValueError, Exception):
                pass

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    if current_user.is_superuser:
        return current_user

    # Check for Admin role
    result = await db.execute(
        select(Role)
        .join(user_roles, Role.id == user_roles.c.role_id)
        .where(user_roles.c.user_id == current_user.id)
        .where(Role.name == "Admin")
        .where(Role.is_active == True)
    )
    admin_role = result.scalar_one_or_none()

    if not admin_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return current_user


async def get_current_active_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated active user.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Current user

    Raises:
        HTTPException: If not authenticated or inactive
    """
    current_user = getattr(request.state, "user", None)

    if not current_user:
        user_id_header = request.headers.get("X-User-ID")
        if user_id_header:
            try:
                user_id = UUID(user_id_header)
                result = await db.execute(
                    select(User).where(User.id == user_id)
                )
                current_user = result.scalar_one_or_none()
            except (ValueError, Exception):
                pass

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return current_user
