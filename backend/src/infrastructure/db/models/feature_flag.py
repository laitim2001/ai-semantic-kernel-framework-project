"""
File: backend/src/infrastructure/db/models/feature_flag.py
Purpose: FeatureFlag ORM — global registry with per-tenant overrides in JSONB.
Category: Infrastructure / ORM (SaaS Stage 1 feature flag system)
Scope: Sprint 56.1 / Day 3 / US-4 Feature Flags

Description:
    Global registry table for feature flags (no `tenant_id` column). The
    `tenant_overrides` JSONB stores per-tenant booleans keyed by tenant
    UUID string. Lookup precedence:
        1. tenant_overrides[str(tenant_id)] if present
        2. default_enabled fallback

    Multi-tenant rule §Rule 1: business tables MUST have tenant_id.
    feature_flags is a *registry* / *configuration* table (analogous to
    `tools_registry`), not a business table. Per-tenant overrides live in
    JSONB. RLS NOT applied (the table is read by all tenants; the JSONB
    field encodes per-tenant policy).

    Audit invariant: every `set_tenant_override` must call
    `infrastructure.db.audit_helper.append_audit` so the chain records who
    flipped which flag for which tenant.

Modification History (newest-first):
    - 2026-05-06: Initial creation (Sprint 56.1 Day 3 / US-4)

Related:
    - core/feature_flags.py — FeatureFlagsService (lookup + set + audit)
    - 0015_feature_flags.py — Alembic migration
    - sprint-56-1-plan.md §US-4 Feature Flags
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base


class FeatureFlag(Base):
    """Global feature flag with default + per-tenant override JSONB."""

    __tablename__ = "feature_flags"

    name: Mapped[str] = mapped_column(String(128), primary_key=True)
    default_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    tenant_overrides: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"FeatureFlag(name={self.name!r}, default_enabled={self.default_enabled})"
