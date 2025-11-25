"""
RBAC API Routes

Sprint 3 - Story S3-1: RBAC Permission System

Provides REST API endpoints for role and permission management.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.session import get_db
from src.domain.rbac.service import RBACService
from src.domain.rbac.schemas import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleListResponse,
    PermissionResponse,
    UserRoleAssignment,
    UserRoleResponse,
    UserPermissionsResponse,
    PermissionCheckRequest,
    PermissionCheckResponse,
    RBACInitResponse,
    RoleStatsResponse,
)
from src.domain.rbac.dependencies import require_admin, PermissionChecker

router = APIRouter(prefix="/rbac", tags=["rbac"])


# =============================================================================
# Initialization Endpoints
# =============================================================================

@router.post(
    "/initialize",
    response_model=RBACInitResponse,
    summary="Initialize RBAC system",
    description="Initialize the RBAC system with standard roles and permissions. Safe to call multiple times.",
)
async def initialize_rbac(
    db: AsyncSession = Depends(get_db),
) -> RBACInitResponse:
    """Initialize RBAC with standard roles and permissions.

    This endpoint is idempotent - calling it multiple times is safe.
    It will only create roles and permissions that don't already exist.
    """
    service = RBACService(db)
    return await service.initialize_rbac()


@router.get(
    "/stats",
    response_model=RoleStatsResponse,
    summary="Get RBAC statistics",
)
async def get_rbac_stats(
    db: AsyncSession = Depends(get_db),
) -> RoleStatsResponse:
    """Get statistics about roles and permissions."""
    service = RBACService(db)
    return await service.get_stats()


# =============================================================================
# Role Management Endpoints
# =============================================================================

@router.get(
    "/roles",
    response_model=List[RoleListResponse],
    summary="List all roles",
)
async def list_roles(
    include_inactive: bool = Query(False, description="Include inactive roles"),
    db: AsyncSession = Depends(get_db),
) -> List[RoleListResponse]:
    """Get all roles."""
    service = RBACService(db)
    return await service.get_all_roles(include_inactive=include_inactive)


@router.get(
    "/roles/{role_id}",
    response_model=RoleResponse,
    summary="Get role by ID",
)
async def get_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> RoleResponse:
    """Get role details including permissions."""
    service = RBACService(db)
    role = await service.get_role_by_id(role_id)

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found",
        )

    return role


@router.post(
    "/roles",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new role",
)
async def create_role(
    role_data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    # _admin: bool = Depends(PermissionChecker("admin", "access")),  # Uncomment when auth is ready
) -> RoleResponse:
    """Create a new custom role.

    System roles cannot be created via API.
    """
    service = RBACService(db)

    try:
        return await service.create_role(role_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put(
    "/roles/{role_id}",
    response_model=RoleResponse,
    summary="Update a role",
)
async def update_role(
    role_id: UUID,
    role_data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    # _admin: bool = Depends(PermissionChecker("admin", "access")),
) -> RoleResponse:
    """Update a role.

    System role names cannot be changed.
    """
    service = RBACService(db)

    try:
        role = await service.update_role(role_id, role_data)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role with ID {role_id} not found",
            )
        return role
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a role",
)
async def delete_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    # _admin: bool = Depends(PermissionChecker("admin", "access")),
):
    """Delete a custom role.

    System roles cannot be deleted.
    """
    service = RBACService(db)

    try:
        deleted = await service.delete_role(role_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role with ID {role_id} not found",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# =============================================================================
# Permission Endpoints
# =============================================================================

@router.get(
    "/permissions",
    response_model=List[PermissionResponse],
    summary="List all permissions",
)
async def list_permissions(
    db: AsyncSession = Depends(get_db),
) -> List[PermissionResponse]:
    """Get all available permissions."""
    service = RBACService(db)
    return await service.get_all_permissions()


# =============================================================================
# User Role Assignment Endpoints
# =============================================================================

@router.post(
    "/users/{user_id}/roles/{role_id}",
    response_model=UserRoleResponse,
    summary="Assign role to user",
)
async def assign_role_to_user(
    user_id: UUID,
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    # _admin: bool = Depends(PermissionChecker("admin", "access")),
) -> UserRoleResponse:
    """Assign a role to a user."""
    service = RBACService(db)

    try:
        # Get user and role info for response
        from src.infrastructure.database.models.user import User
        from src.infrastructure.database.models.rbac import Role
        from sqlalchemy import select

        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        role_result = await db.execute(select(Role).where(Role.id == role_id))
        role = role_result.scalar_one_or_none()

        assigned = await service.assign_role_to_user(user_id, role_id)

        return UserRoleResponse(
            user_id=user_id,
            user_email=user.email if user else "unknown",
            role_name=role.name if role else "unknown",
            action="assigned" if assigned else "already_assigned",
            message=f"Role '{role.name}' assigned to user '{user.email}'"
            if assigned else f"User already has role '{role.name}'",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete(
    "/users/{user_id}/roles/{role_id}",
    response_model=UserRoleResponse,
    summary="Remove role from user",
)
async def remove_role_from_user(
    user_id: UUID,
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    # _admin: bool = Depends(PermissionChecker("admin", "access")),
) -> UserRoleResponse:
    """Remove a role from a user."""
    service = RBACService(db)

    # Get user and role info for response
    from src.infrastructure.database.models.user import User
    from src.infrastructure.database.models.rbac import Role
    from sqlalchemy import select

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    role_result = await db.execute(select(Role).where(Role.id == role_id))
    role = role_result.scalar_one_or_none()

    removed = await service.remove_role_from_user(user_id, role_id)

    return UserRoleResponse(
        user_id=user_id,
        user_email=user.email if user else "unknown",
        role_name=role.name if role else "unknown",
        action="removed" if removed else "not_assigned",
        message=f"Role '{role.name}' removed from user '{user.email}'"
        if removed else f"User did not have role '{role.name}'",
    )


@router.get(
    "/users/{user_id}/roles",
    response_model=List[RoleListResponse],
    summary="Get user's roles",
)
async def get_user_roles(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> List[RoleListResponse]:
    """Get all roles assigned to a user."""
    service = RBACService(db)
    return await service.get_user_roles(user_id)


@router.get(
    "/users/{user_id}/permissions",
    response_model=UserPermissionsResponse,
    summary="Get user's effective permissions",
)
async def get_user_permissions(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> UserPermissionsResponse:
    """Get all effective permissions for a user.

    Combines permissions from all assigned roles.
    """
    service = RBACService(db)

    try:
        return await service.get_user_permissions(user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# =============================================================================
# Permission Check Endpoints
# =============================================================================

@router.post(
    "/users/{user_id}/check-permission",
    response_model=PermissionCheckResponse,
    summary="Check user permission",
)
async def check_user_permission(
    user_id: UUID,
    permission: PermissionCheckRequest,
    db: AsyncSession = Depends(get_db),
) -> PermissionCheckResponse:
    """Check if a user has a specific permission."""
    service = RBACService(db)
    return await service.check_user_permission(
        user_id,
        permission.resource,
        permission.action,
    )


@router.get(
    "/check/{resource}/{action}",
    response_model=PermissionCheckResponse,
    summary="Check current user's permission",
)
async def check_current_user_permission(
    resource: str,
    action: str,
    user_id: Optional[UUID] = Query(None, description="User ID (for testing)"),
    db: AsyncSession = Depends(get_db),
) -> PermissionCheckResponse:
    """Check if the current user has a specific permission.

    For development/testing, pass user_id as query parameter.
    """
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id query parameter required (authentication not yet implemented)",
        )

    service = RBACService(db)
    return await service.check_user_permission(user_id, resource, action)
