"""
RBAC Schemas

Sprint 3 - Story S3-1: RBAC Permission System

Pydantic models for RBAC operations.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PermissionBase(BaseModel):
    """Base permission schema."""
    name: str = Field(..., description="Permission name (e.g., workflow:create)")
    resource: str = Field(..., description="Resource type")
    action: str = Field(..., description="Action type")
    description: Optional[str] = Field(None, description="Permission description")


class PermissionResponse(PermissionBase):
    """Permission response schema."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoleBase(BaseModel):
    """Base role schema."""
    name: str = Field(..., min_length=1, max_length=50, description="Role name")
    description: Optional[str] = Field(None, max_length=255, description="Role description")
    priority: int = Field(50, ge=0, le=100, description="Role priority (0-100)")


class RoleCreate(RoleBase):
    """Schema for creating a role."""
    permission_names: List[str] = Field(default_factory=list, description="List of permission names to assign")


class RoleUpdate(BaseModel):
    """Schema for updating a role."""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    priority: Optional[int] = Field(None, ge=0, le=100)
    permission_names: Optional[List[str]] = Field(None, description="List of permission names to assign")
    is_active: Optional[bool] = None


class RoleResponse(RoleBase):
    """Role response schema."""
    id: UUID
    is_system: bool
    is_active: bool
    permissions: List[PermissionResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoleListResponse(BaseModel):
    """Role list response schema."""
    id: UUID
    name: str
    description: Optional[str]
    priority: int
    is_system: bool
    is_active: bool
    permission_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class UserRoleAssignment(BaseModel):
    """Schema for assigning/removing roles from users."""
    user_id: UUID = Field(..., description="User ID")
    role_id: UUID = Field(..., description="Role ID")


class UserRoleResponse(BaseModel):
    """Response for user role assignment operations."""
    user_id: UUID
    user_email: str
    role_name: str
    action: str  # "assigned" or "removed"
    message: str


class UserPermissionsResponse(BaseModel):
    """Response containing user's effective permissions."""
    user_id: UUID
    username: str
    email: str
    is_superuser: bool
    roles: List[str]
    permissions: List[str]
    highest_priority: int

    class Config:
        from_attributes = True


class PermissionCheckRequest(BaseModel):
    """Request to check if user has permission."""
    resource: str = Field(..., description="Resource type to check")
    action: str = Field(..., description="Action to check")


class PermissionCheckResponse(BaseModel):
    """Response for permission check."""
    user_id: UUID
    resource: str
    action: str
    has_permission: bool
    granted_by: Optional[str] = Field(None, description="Role that grants this permission")


class RBACInitResponse(BaseModel):
    """Response for RBAC initialization."""
    roles_created: int
    permissions_created: int
    message: str


class RoleStatsResponse(BaseModel):
    """Statistics about roles and permissions."""
    total_roles: int
    active_roles: int
    system_roles: int
    total_permissions: int
    users_with_roles: int
