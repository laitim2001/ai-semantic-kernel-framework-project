"""
File: backend/src/infrastructure/db/models/skill.py
Purpose: TenantSkill ORM — per-tenant custom Skills catalog (overlaid on the bundled skills).
Category: Infrastructure / ORM (platform_layer.skills — Skills System per-tenant catalog)
Scope: Sprint 57.114 / US-2 (Skills System epic — per-tenant overlay)

Description:
    A tenant authors custom skills (name + description + a full instruction body)
    via the tenant-settings "Skills" admin tab; each row is a TenantSkill. A
    per-request resolver (platform_layer/skills) loads the bundled skill set then
    overlays the tenant's rows on top (a same-name tenant skill shadows a bundled
    one — SkillRegistry.with_overlay). DB-backed (listable / revocable / per-tenant)
    + RLS (tenant_isolation), unique (tenant_id, name).

Key Components:
    - TenantSkill: ORM (TenantScopedMixin); unique (tenant_id, name)

Created: 2026-06-13 (Sprint 57.114)

Modification History:
    - 2026-06-13: Initial creation (Sprint 57.114 / US-2)

Related:
    - migrations/versions/0030_tenant_skills.py — table + RLS
    - platform_layer/skills/service.py — TenantSkillService + resolve_tenant_skill_registry
    - agent_harness/skills/registry.py — SkillRegistry.with_overlay (the overlay primitive)
    - infrastructure/db/models/invites.py:Invite — tenant-scoped ORM precedent (mirror)
    - .claude/rules/multi-tenant-data.md 鐵律 1 (tenant_id NN + RLS)
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID as PyUUID

from sqlalchemy import (
    DateTime,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base, TenantScopedMixin


class TenantSkill(Base, TenantScopedMixin):
    """A per-tenant custom skill (overlaid on the bundled set by name)."""

    __tablename__ = "tenant_skills"

    id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tenant_skills_tenant_name"),
        Index("idx_tenant_skills_tenant", "tenant_id"),
    )


__all__ = ["TenantSkill"]
