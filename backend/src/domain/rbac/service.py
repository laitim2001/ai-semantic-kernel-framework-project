"""
RBAC Service

Sprint 3 - Story S3-1: RBAC Permission System

Provides business logic for role-based access control.
"""
from __future__ import annotations

import logging
from typing import List, Optional, Set
from uuid import UUID

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.database.models.rbac import (
    Role,
    Permission,
    user_roles,
    role_permissions,
    STANDARD_PERMISSIONS,
    ROLE_DEFINITIONS,
    RoleName,
)
from src.infrastructure.database.models.user import User

from .schemas import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleListResponse,
    PermissionResponse,
    UserPermissionsResponse,
    PermissionCheckResponse,
    RBACInitResponse,
    RoleStatsResponse,
)

logger = logging.getLogger(__name__)


class RBACService:
    """Service for RBAC operations.

    Provides methods to manage roles, permissions, and user-role assignments.

    Example:
        service = RBACService(db)
        await service.initialize_rbac()
        await service.assign_role_to_user(user_id, role_id)
    """

    def __init__(self, db: AsyncSession):
        """Initialize RBACService.

        Args:
            db: Async database session
        """
        self.db = db

    async def initialize_rbac(self) -> RBACInitResponse:
        """Initialize RBAC with standard roles and permissions.

        Creates all standard permissions and roles if they don't exist.

        Returns:
            RBACInitResponse with counts of created items
        """
        permissions_created = 0
        roles_created = 0

        # Create permissions
        permission_objects = {}
        for perm_data in STANDARD_PERMISSIONS:
            result = await self.db.execute(
                select(Permission).where(Permission.name == perm_data["name"])
            )
            perm = result.scalar_one_or_none()

            if not perm:
                perm = Permission(**perm_data)
                self.db.add(perm)
                await self.db.flush()
                permissions_created += 1
                logger.info(f"Created permission: {perm_data['name']}")

            permission_objects[perm_data["name"]] = perm

        await self.db.commit()

        # Create roles and assign permissions
        for role_name, role_config in ROLE_DEFINITIONS.items():
            result = await self.db.execute(
                select(Role)
                .options(selectinload(Role.permissions))
                .where(Role.name == role_name.value)
            )
            role = result.scalar_one_or_none()

            if not role:
                role = Role(
                    name=role_name.value,
                    description=role_config["description"],
                    priority=role_config["priority"],
                    is_system=role_config["is_system"],
                )
                self.db.add(role)
                await self.db.flush()
                roles_created += 1
                logger.info(f"Created role: {role_name.value}")

                # Re-fetch with permissions loaded
                result = await self.db.execute(
                    select(Role)
                    .options(selectinload(Role.permissions))
                    .where(Role.id == role.id)
                )
                role = result.scalar_one()

            # Assign permissions to role using explicit insert
            # First clear existing
            await self.db.execute(
                role_permissions.delete().where(role_permissions.c.role_id == role.id)
            )

            # Then insert new
            for perm_name in role_config["permissions"]:
                if perm_name in permission_objects:
                    perm = permission_objects[perm_name]
                    await self.db.execute(
                        role_permissions.insert().values(role_id=role.id, permission_id=perm.id)
                    )

        await self.db.commit()

        return RBACInitResponse(
            roles_created=roles_created,
            permissions_created=permissions_created,
            message=f"RBAC initialized: {roles_created} roles, {permissions_created} permissions created"
        )

    async def get_all_roles(self, include_inactive: bool = False) -> List[RoleListResponse]:
        """Get all roles.

        Args:
            include_inactive: Whether to include inactive roles

        Returns:
            List of roles with permission counts
        """
        query = select(Role).options(selectinload(Role.permissions))

        if not include_inactive:
            query = query.where(Role.is_active == True)

        query = query.order_by(Role.priority.desc())

        result = await self.db.execute(query)
        roles = result.scalars().all()

        return [
            RoleListResponse(
                id=role.id,
                name=role.name,
                description=role.description,
                priority=role.priority,
                is_system=role.is_system,
                is_active=role.is_active,
                permission_count=len(role.permissions),
                created_at=role.created_at,
            )
            for role in roles
        ]

    async def get_role_by_id(self, role_id: UUID) -> Optional[RoleResponse]:
        """Get role by ID with permissions.

        Args:
            role_id: Role UUID

        Returns:
            Role with permissions or None
        """
        result = await self.db.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == role_id)
        )
        role = result.scalar_one_or_none()

        if not role:
            return None

        return RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            priority=role.priority,
            is_system=role.is_system,
            is_active=role.is_active,
            permissions=[
                PermissionResponse(
                    id=p.id,
                    name=p.name,
                    resource=p.resource,
                    action=p.action,
                    description=p.description,
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                )
                for p in role.permissions
            ],
            created_at=role.created_at,
            updated_at=role.updated_at,
        )

    async def get_role_by_name(self, name: str) -> Optional[Role]:
        """Get role by name.

        Args:
            name: Role name

        Returns:
            Role model or None
        """
        result = await self.db.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.name == name)
        )
        return result.scalar_one_or_none()

    async def create_role(self, role_data: RoleCreate) -> RoleResponse:
        """Create a new role.

        Args:
            role_data: Role creation data

        Returns:
            Created role

        Raises:
            ValueError: If role name already exists
        """
        # Check for duplicate name
        existing = await self.get_role_by_name(role_data.name)
        if existing:
            raise ValueError(f"Role with name '{role_data.name}' already exists")

        # Get permissions
        permissions = []
        if role_data.permission_names:
            for perm_name in role_data.permission_names:
                result = await self.db.execute(
                    select(Permission).where(Permission.name == perm_name)
                )
                perm = result.scalar_one_or_none()
                if perm:
                    permissions.append(perm)

        role = Role(
            name=role_data.name,
            description=role_data.description,
            priority=role_data.priority,
            is_system=False,
        )
        role.permissions = permissions

        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)

        return await self.get_role_by_id(role.id)

    async def update_role(self, role_id: UUID, role_data: RoleUpdate) -> Optional[RoleResponse]:
        """Update a role.

        Args:
            role_id: Role UUID
            role_data: Update data

        Returns:
            Updated role or None

        Raises:
            ValueError: If trying to modify system role name
        """
        result = await self.db.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == role_id)
        )
        role = result.scalar_one_or_none()

        if not role:
            return None

        # Prevent modifying system role names
        if role.is_system and role_data.name and role_data.name != role.name:
            raise ValueError("Cannot change the name of a system role")

        # Update fields
        if role_data.name is not None:
            role.name = role_data.name
        if role_data.description is not None:
            role.description = role_data.description
        if role_data.priority is not None:
            role.priority = role_data.priority
        if role_data.is_active is not None:
            if role.is_system and not role_data.is_active:
                raise ValueError("Cannot deactivate a system role")
            role.is_active = role_data.is_active

        # Update permissions
        if role_data.permission_names is not None:
            permissions = []
            for perm_name in role_data.permission_names:
                result = await self.db.execute(
                    select(Permission).where(Permission.name == perm_name)
                )
                perm = result.scalar_one_or_none()
                if perm:
                    permissions.append(perm)
            role.permissions = permissions

        await self.db.commit()
        return await self.get_role_by_id(role_id)

    async def delete_role(self, role_id: UUID) -> bool:
        """Delete a role.

        Args:
            role_id: Role UUID

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If trying to delete system role
        """
        result = await self.db.execute(
            select(Role).where(Role.id == role_id)
        )
        role = result.scalar_one_or_none()

        if not role:
            return False

        if role.is_system:
            raise ValueError("Cannot delete a system role")

        await self.db.delete(role)
        await self.db.commit()
        return True

    async def get_all_permissions(self) -> List[PermissionResponse]:
        """Get all permissions.

        Returns:
            List of all permissions
        """
        result = await self.db.execute(
            select(Permission).order_by(Permission.resource, Permission.action)
        )
        permissions = result.scalars().all()

        return [
            PermissionResponse(
                id=p.id,
                name=p.name,
                resource=p.resource,
                action=p.action,
                description=p.description,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in permissions
        ]

    async def assign_role_to_user(self, user_id: UUID, role_id: UUID) -> bool:
        """Assign a role to a user.

        Args:
            user_id: User UUID
            role_id: Role UUID

        Returns:
            True if assigned, False if already assigned

        Raises:
            ValueError: If user or role not found
        """
        # Verify user exists
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        # Verify role exists
        role_result = await self.db.execute(
            select(Role).where(Role.id == role_id)
        )
        role = role_result.scalar_one_or_none()
        if not role:
            raise ValueError(f"Role with ID {role_id} not found")

        # Check if already assigned
        existing = await self.db.execute(
            select(user_roles).where(
                user_roles.c.user_id == user_id,
                user_roles.c.role_id == role_id
            )
        )
        if existing.first():
            return False

        # Assign role
        await self.db.execute(
            user_roles.insert().values(user_id=user_id, role_id=role_id)
        )
        await self.db.commit()

        logger.info(f"Assigned role '{role.name}' to user '{user.email}'")
        return True

    async def remove_role_from_user(self, user_id: UUID, role_id: UUID) -> bool:
        """Remove a role from a user.

        Args:
            user_id: User UUID
            role_id: Role UUID

        Returns:
            True if removed, False if not assigned
        """
        result = await self.db.execute(
            delete(user_roles).where(
                user_roles.c.user_id == user_id,
                user_roles.c.role_id == role_id
            )
        )
        await self.db.commit()

        return result.rowcount > 0

    async def get_user_roles(self, user_id: UUID) -> List[RoleListResponse]:
        """Get all roles for a user.

        Args:
            user_id: User UUID

        Returns:
            List of user's roles
        """
        result = await self.db.execute(
            select(Role)
            .join(user_roles, Role.id == user_roles.c.role_id)
            .where(user_roles.c.user_id == user_id)
            .options(selectinload(Role.permissions))
            .order_by(Role.priority.desc())
        )
        roles = result.scalars().all()

        return [
            RoleListResponse(
                id=role.id,
                name=role.name,
                description=role.description,
                priority=role.priority,
                is_system=role.is_system,
                is_active=role.is_active,
                permission_count=len(role.permissions),
                created_at=role.created_at,
            )
            for role in roles
        ]

    async def get_user_permissions(self, user_id: UUID) -> UserPermissionsResponse:
        """Get effective permissions for a user.

        Combines permissions from all user roles.

        Args:
            user_id: User UUID

        Returns:
            User's effective permissions

        Raises:
            ValueError: If user not found
        """
        # Get user
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        # Superusers have all permissions
        if user.is_superuser:
            all_perms_result = await self.db.execute(select(Permission))
            all_perms = all_perms_result.scalars().all()

            return UserPermissionsResponse(
                user_id=user.id,
                username=user.username,
                email=user.email,
                is_superuser=True,
                roles=["Admin (Superuser)"],
                permissions=[p.name for p in all_perms],
                highest_priority=100,
            )

        # Get user's roles with permissions
        result = await self.db.execute(
            select(Role)
            .join(user_roles, Role.id == user_roles.c.role_id)
            .where(user_roles.c.user_id == user_id)
            .where(Role.is_active == True)
            .options(selectinload(Role.permissions))
        )
        roles = result.scalars().all()

        # Combine permissions
        permissions: Set[str] = set()
        role_names: List[str] = []
        highest_priority = 0

        for role in roles:
            role_names.append(role.name)
            highest_priority = max(highest_priority, role.priority)
            for perm in role.permissions:
                permissions.add(perm.name)

        return UserPermissionsResponse(
            user_id=user.id,
            username=user.username,
            email=user.email,
            is_superuser=False,
            roles=role_names,
            permissions=sorted(permissions),
            highest_priority=highest_priority,
        )

    async def check_user_permission(
        self,
        user_id: UUID,
        resource: str,
        action: str
    ) -> PermissionCheckResponse:
        """Check if user has a specific permission.

        Args:
            user_id: User UUID
            resource: Resource type
            action: Action type

        Returns:
            Permission check result
        """
        # Get user
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return PermissionCheckResponse(
                user_id=user_id,
                resource=resource,
                action=action,
                has_permission=False,
                granted_by=None,
            )

        # Superusers have all permissions
        if user.is_superuser:
            return PermissionCheckResponse(
                user_id=user_id,
                resource=resource,
                action=action,
                has_permission=True,
                granted_by="Superuser",
            )

        # Check user's roles
        result = await self.db.execute(
            select(Role)
            .join(user_roles, Role.id == user_roles.c.role_id)
            .where(user_roles.c.user_id == user_id)
            .where(Role.is_active == True)
            .options(selectinload(Role.permissions))
        )
        roles = result.scalars().all()

        for role in roles:
            if role.has_permission(resource, action):
                return PermissionCheckResponse(
                    user_id=user_id,
                    resource=resource,
                    action=action,
                    has_permission=True,
                    granted_by=role.name,
                )

        return PermissionCheckResponse(
            user_id=user_id,
            resource=resource,
            action=action,
            has_permission=False,
            granted_by=None,
        )

    async def get_stats(self) -> RoleStatsResponse:
        """Get RBAC statistics.

        Returns:
            Statistics about roles and permissions
        """
        # Count roles
        total_roles_result = await self.db.execute(
            select(func.count(Role.id))
        )
        total_roles = total_roles_result.scalar() or 0

        active_roles_result = await self.db.execute(
            select(func.count(Role.id)).where(Role.is_active == True)
        )
        active_roles = active_roles_result.scalar() or 0

        system_roles_result = await self.db.execute(
            select(func.count(Role.id)).where(Role.is_system == True)
        )
        system_roles = system_roles_result.scalar() or 0

        # Count permissions
        total_permissions_result = await self.db.execute(
            select(func.count(Permission.id))
        )
        total_permissions = total_permissions_result.scalar() or 0

        # Count users with roles
        users_with_roles_result = await self.db.execute(
            select(func.count(func.distinct(user_roles.c.user_id)))
        )
        users_with_roles = users_with_roles_result.scalar() or 0

        return RoleStatsResponse(
            total_roles=total_roles,
            active_roles=active_roles,
            system_roles=system_roles,
            total_permissions=total_permissions,
            users_with_roles=users_with_roles,
        )
