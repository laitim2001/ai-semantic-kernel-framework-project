"""
RBAC Models - Role-Based Access Control

Sprint 3 - Story S3-1: RBAC Permission System

Provides data models for roles, permissions, and user-role associations.
"""
import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, String, Boolean, Integer, Table, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, BaseModel


# Association tables for many-to-many relationships
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)
)

role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', UUID(as_uuid=True), ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True)
)


class RoleName(str, enum.Enum):
    """Standard role names."""
    ADMIN = "Admin"
    POWER_USER = "PowerUser"
    USER = "User"
    VIEWER = "Viewer"


class ResourceType(str, enum.Enum):
    """Resource types for permissions."""
    WORKFLOW = "workflow"
    EXECUTION = "execution"
    AGENT = "agent"
    USER = "user"
    ADMIN = "admin"
    AUDIT = "audit"
    CHECKPOINT = "checkpoint"
    NOTIFICATION = "notification"
    WEBHOOK = "webhook"


class ActionType(str, enum.Enum):
    """Action types for permissions."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    CANCEL = "cancel"
    APPROVE = "approve"
    REJECT = "reject"
    ACCESS = "access"
    EXPORT = "export"


class Role(BaseModel):
    """Role model.

    Defines a role that can be assigned to users.
    Roles contain a set of permissions.

    Attributes:
        name: Unique role name (e.g., Admin, User, Viewer)
        description: Human-readable description
        priority: Higher priority = more permissions (Admin=100, Viewer=25)
        is_system: System roles cannot be deleted
        is_active: Whether the role is active
    """
    __tablename__ = "roles"

    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    priority = Column(Integer, nullable=False, default=50)
    is_system = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name}, priority={self.priority})>"

    def has_permission(self, resource: str, action: str) -> bool:
        """Check if role has a specific permission."""
        for permission in self.permissions:
            if permission.resource == resource and permission.action == action:
                return True
        return False


class Permission(BaseModel):
    """Permission model.

    Defines a single permission for a resource and action combination.

    Attributes:
        name: Unique permission name (e.g., workflow:create)
        resource: Resource type (workflow, execution, agent, etc.)
        action: Action type (create, read, update, delete, etc.)
        description: Human-readable description
    """
    __tablename__ = "permissions"

    name = Column(String(100), unique=True, nullable=False, index=True)
    resource = Column(String(50), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)
    description = Column(String(255), nullable=True)

    # Relationships
    roles = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name={self.name})>"


# Standard permissions definition
STANDARD_PERMISSIONS = [
    # Workflow permissions
    {"name": "workflow:create", "resource": "workflow", "action": "create", "description": "Create workflows"},
    {"name": "workflow:read", "resource": "workflow", "action": "read", "description": "View workflows"},
    {"name": "workflow:update", "resource": "workflow", "action": "update", "description": "Update workflows"},
    {"name": "workflow:delete", "resource": "workflow", "action": "delete", "description": "Delete workflows"},
    {"name": "workflow:execute", "resource": "workflow", "action": "execute", "description": "Execute workflows"},

    # Execution permissions
    {"name": "execution:create", "resource": "execution", "action": "create", "description": "Create executions"},
    {"name": "execution:read", "resource": "execution", "action": "read", "description": "View executions"},
    {"name": "execution:cancel", "resource": "execution", "action": "cancel", "description": "Cancel executions"},

    # Agent permissions
    {"name": "agent:create", "resource": "agent", "action": "create", "description": "Create agents"},
    {"name": "agent:read", "resource": "agent", "action": "read", "description": "View agents"},
    {"name": "agent:update", "resource": "agent", "action": "update", "description": "Update agents"},
    {"name": "agent:delete", "resource": "agent", "action": "delete", "description": "Delete agents"},

    # User permissions
    {"name": "user:read", "resource": "user", "action": "read", "description": "View users"},
    {"name": "user:create", "resource": "user", "action": "create", "description": "Create users"},
    {"name": "user:update", "resource": "user", "action": "update", "description": "Update users"},
    {"name": "user:delete", "resource": "user", "action": "delete", "description": "Delete users"},

    # Admin permissions
    {"name": "admin:access", "resource": "admin", "action": "access", "description": "Access admin dashboard"},

    # Audit permissions
    {"name": "audit:read", "resource": "audit", "action": "read", "description": "View audit logs"},
    {"name": "audit:export", "resource": "audit", "action": "export", "description": "Export audit logs"},

    # Checkpoint permissions
    {"name": "checkpoint:create", "resource": "checkpoint", "action": "create", "description": "Create checkpoints"},
    {"name": "checkpoint:read", "resource": "checkpoint", "action": "read", "description": "View checkpoints"},
    {"name": "checkpoint:approve", "resource": "checkpoint", "action": "approve", "description": "Approve checkpoints"},
    {"name": "checkpoint:reject", "resource": "checkpoint", "action": "reject", "description": "Reject checkpoints"},

    # Notification permissions
    {"name": "notification:read", "resource": "notification", "action": "read", "description": "View notifications"},
    {"name": "notification:create", "resource": "notification", "action": "create", "description": "Send notifications"},

    # Webhook permissions
    {"name": "webhook:create", "resource": "webhook", "action": "create", "description": "Create webhooks"},
    {"name": "webhook:read", "resource": "webhook", "action": "read", "description": "View webhooks"},
    {"name": "webhook:update", "resource": "webhook", "action": "update", "description": "Update webhooks"},
    {"name": "webhook:delete", "resource": "webhook", "action": "delete", "description": "Delete webhooks"},
]

# Role definitions with their permissions
ROLE_DEFINITIONS = {
    RoleName.ADMIN: {
        "description": "管理員，擁有所有權限",
        "priority": 100,
        "is_system": True,
        "permissions": [p["name"] for p in STANDARD_PERMISSIONS]  # All permissions
    },
    RoleName.POWER_USER: {
        "description": "高級用戶，可以管理工作流和執行",
        "priority": 75,
        "is_system": True,
        "permissions": [
            "workflow:create", "workflow:read", "workflow:update", "workflow:delete", "workflow:execute",
            "execution:create", "execution:read", "execution:cancel",
            "agent:create", "agent:read", "agent:update",
            "user:read",
            "checkpoint:create", "checkpoint:read", "checkpoint:approve", "checkpoint:reject",
            "notification:read", "notification:create",
            "webhook:create", "webhook:read", "webhook:update",
        ]
    },
    RoleName.USER: {
        "description": "普通用戶，可以創建和執行自己的工作流",
        "priority": 50,
        "is_system": True,
        "permissions": [
            "workflow:create", "workflow:read", "workflow:update", "workflow:execute",
            "execution:create", "execution:read",
            "agent:read",
            "user:read",
            "checkpoint:read", "checkpoint:approve", "checkpoint:reject",
            "notification:read",
            "webhook:read",
        ]
    },
    RoleName.VIEWER: {
        "description": "只讀用戶，只能查看",
        "priority": 25,
        "is_system": True,
        "permissions": [
            "workflow:read",
            "execution:read",
            "agent:read",
            "user:read",
            "checkpoint:read",
            "notification:read",
            "webhook:read",
        ]
    }
}
