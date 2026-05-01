"""
File: backend/src/infrastructure/db/base.py
Purpose: SQLAlchemy 2.0 DeclarativeBase + TenantScopedMixin enforcing multi-tenant rule 1.
Category: Infrastructure / ORM core
Scope: Sprint 49.2 (initial Async ORM foundation)
Owner: infrastructure/db owner

Description:
    Defines the V2 ORM declarative base + a mandatory mixin that any
    session-scoped table must inherit so it carries `tenant_id` NOT NULL
    + FK to tenants(id) ONDELETE CASCADE + an index.

    Per `.claude/rules/multi-tenant-data.md` 鐵律 1：
        所有業務 Table 必有 tenant_id 欄位（NOT NULL）

    Tables that DO NOT inherit TenantScopedMixin（global / cross-tenant）:
        - tenants （itself the root of the hierarchy）
        - tools_registry （global tool metadata, shared across tenants）

    All other 11 tables in Sprint 49.2 inherit this mixin:
        users / roles / user_roles / role_permissions
        sessions / messages / message_events
        tool_calls / tool_results
        state_snapshots / loop_states

Created: 2026-04-29 (Sprint 49.2 Day 1.3)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.2 Day 1.3)

Related:
    - .claude/rules/multi-tenant-data.md 鐵律 1
    - 09-db-schema-design.md §Multi-Tenant 強制標準
    - 17-cross-category-interfaces.md (no direct contract; this is infra-only)
"""

from __future__ import annotations

from uuid import UUID as PyUUID

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """V2 ORM declarative base. All ORM tables inherit from this."""


class TenantScopedMixin:
    """
    Mandatory mixin for any session-scoped / business table.

    Forces:
        - tenant_id UUID NOT NULL
        - ForeignKey to tenants(id) ON DELETE CASCADE
        - Index on tenant_id (multi-tenant query path)

    Usage:
        class User(Base, TenantScopedMixin):
            __tablename__ = "users"
            ...

    The `declared_attr` form ensures each subclass gets its own Column
    instance + correct FK target name resolution at class-creation time.
    """

    @declared_attr
    @classmethod
    def tenant_id(cls) -> Mapped[PyUUID]:
        return mapped_column(
            PgUUID(as_uuid=True),
            ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            doc="Multi-tenant scope FK; required by .claude/rules/multi-tenant-data.md 鐵律 1.",
        )


__all__ = ["Base", "TenantScopedMixin"]
