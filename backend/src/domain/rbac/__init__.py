"""
RBAC Domain Module

Sprint 3 - Story S3-1: RBAC Permission System

Provides role-based access control functionality.
"""
from .schemas import (
    RoleBase,
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    PermissionBase,
    PermissionResponse,
    UserRoleAssignment,
    UserPermissionsResponse,
)
from .service import RBACService
from .dependencies import (
    require_permission,
    require_role,
    require_admin,
    get_current_user_permissions,
    PermissionChecker,
)

__all__ = [
    # Schemas
    "RoleBase",
    "RoleCreate",
    "RoleUpdate",
    "RoleResponse",
    "PermissionBase",
    "PermissionResponse",
    "UserRoleAssignment",
    "UserPermissionsResponse",
    # Service
    "RBACService",
    # Dependencies
    "require_permission",
    "require_role",
    "require_admin",
    "get_current_user_permissions",
    "PermissionChecker",
]
