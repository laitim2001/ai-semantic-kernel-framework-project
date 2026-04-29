"""
File: backend/src/infrastructure/db/models/identity.py
Purpose: Identity / Tenancy ORM models — Tenant, User, Role, UserRole, RolePermission.
Category: Infrastructure / ORM (Identity & Tenancy group, per 09-db-schema-design.md Group 1)
Scope: Sprint 49.2 (initial Identity ORM)
Owner: infrastructure/db owner

Description:
    Multi-tenant identity foundation for V2. Maps to migration 0001_initial_identity.

    Hierarchy (per 09-db-schema-design.md L114-191):
        tenants (root, no tenant_id)
        ├── users (TenantScopedMixin)
        ├── roles (TenantScopedMixin)
        ├── user_roles (junction; NO tenant_id; tenant inferred via FK chain)
        └── role_permissions (NO tenant_id; tenant inferred via role)

    All session-scoped tables in subsequent migrations (sessions, tools,
    state, etc.) FK back to `tenants.id` directly via TenantScopedMixin.

Key Components:
    - Tenant: top-level multi-tenant root
    - User: per-tenant user identity (Entra ID / LDAP friendly via external_id)
    - Role: per-tenant RBAC role (e.g., "finance_manager")
    - UserRole: many-to-many user ↔ role mapping
    - RolePermission: per-role action permissions (resource_type / pattern / action)

Created: 2026-04-29 (Sprint 49.2 Day 1.5)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.2 Day 1.5)

Related:
    - 09-db-schema-design.md §Group 1 Identity & Tenancy (L114-191)
    - .claude/rules/multi-tenant-data.md 鐵律 1
    - infrastructure/db/base.py (Base, TenantScopedMixin)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID as PyUUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base, TenantScopedMixin


# =====================================================================
# Tenant — root of the multi-tenant hierarchy (no tenant_id itself)
# =====================================================================
class Tenant(Base):
    """Top-level tenant. Per 09-db-schema-design.md L114-127."""

    __tablename__ = "tenants"

    id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    meta_data: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (Index("idx_tenants_status", "status"),)


# =====================================================================
# User — per-tenant user identity
# =====================================================================
class User(Base, TenantScopedMixin):
    """Per-tenant user. Per 09-db-schema-design.md L130-147."""

    __tablename__ = "users"

    id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    email: Mapped[str] = mapped_column(String(256), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(256))
    external_id: Mapped[str | None] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    preferences: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        # idx_users_tenant is auto-created by TenantScopedMixin (index=True)
        Index(
            "idx_users_external",
            "external_id",
            postgresql_where=text("external_id IS NOT NULL"),
        ),
    )


# =====================================================================
# Role — per-tenant RBAC role
# =====================================================================
class Role(Base, TenantScopedMixin):
    """Per-tenant RBAC role. Per 09-db-schema-design.md L150-162."""

    __tablename__ = "roles"

    id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    meta_data: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_roles_tenant_code"),)


# =====================================================================
# UserRole — junction table (no tenant_id; tenant inferred via FK chain)
# =====================================================================
class UserRole(Base):
    """User ↔ Role many-to-many junction. Per 09-db-schema-design.md L165-173."""

    __tablename__ = "user_roles"

    user_id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    granted_by: Mapped[PyUUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    __table_args__ = (PrimaryKeyConstraint("user_id", "role_id", name="pk_user_roles"),)


# =====================================================================
# RolePermission — per-role action permissions (no tenant_id; via role)
# =====================================================================
class RolePermission(Base):
    """Per-role permission entry. Per 09-db-schema-design.md L176-189."""

    __tablename__ = "role_permissions"

    id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    role_id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_pattern: Mapped[str] = mapped_column(String(256), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    constraints: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    __table_args__ = (
        UniqueConstraint(
            "role_id",
            "resource_type",
            "resource_pattern",
            "action",
            name="uq_role_perms_full",
        ),
        Index("idx_role_perms_role", "role_id"),
    )


__all__ = ["Tenant", "User", "Role", "UserRole", "RolePermission"]
