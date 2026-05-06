"""
File: backend/src/infrastructure/db/models/cost_ledger.py
Purpose: CostLedger ORM — per-tenant per-event LLM/tool/storage cost ledger.
Category: Infrastructure / ORM (Phase 56 SaaS Stage 1 / platform_layer.billing)
Scope: Sprint 56.3 / Day 2 / US-3 Cost Ledger DB Schema

Description:
    Append-only ledger of every chargeable platform event:
    - LLM calls: input tokens / output tokens / cached input tokens (3 entries
      per call, when applicable)
    - Tool calls: 1 entry per execute, sub_type = tool_name
    - Storage: per GB-hour (deferred to Phase 57+; cost_type='storage' reserved)

    Source-of-truth for Stage 2 monthly billing run aggregation.
    `aggregate(tenant_id, month) -> AggregatedUsage` SUM-by-cost_type+sub_type
    used by the GET /api/v1/admin/tenants/{tid}/cost-summary endpoint (US-3).

    Day 0 D6 cross-table coordination note: `sessions.total_cost_usd` already
    exists at sessions.py:99 (Phase 50.2 baseline) as a per-session aggregate.
    THIS module is the source-of-truth (granular per-event); sessions.total_cost_usd
    remains as cached UI aggregate, sync to be wired in Phase 56.x audit cycle.

Key Components:
    - CostType: enum mirror of CHECK constraint
    - CostLedger: ORM (TenantScopedMixin)

Created: 2026-05-06 (Sprint 56.3 Day 2)

Modification History:
    - 2026-05-06: Initial creation (Sprint 56.3 Day 2 / US-3)

Related:
    - 15-saas-readiness.md §Billing - Cost Ledger 整合
    - sprint-56-3-plan.md §US-3 Cost Ledger DB Schema + ORM
    - migrations/versions/0016_sla_and_cost_ledger.py
    - platform_layer/billing/cost_ledger.py (US-3 — CostLedgerService)
    - platform_layer/billing/pricing.py (US-3 — PricingLoader)
    - .claude/rules/multi-tenant-data.md 鐵律 1 (tenant_id NN + RLS)
"""

from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from uuid import UUID as PyUUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base, TenantScopedMixin


class CostType(str, enum.Enum):
    """Cost ledger entry type — matches CHECK constraint on cost_ledger.cost_type."""

    LLM = "llm"
    TOOL = "tool"
    STORAGE = "storage"


class CostLedger(Base, TenantScopedMixin):
    """Per-tenant per-event cost ledger entry."""

    __tablename__ = "cost_ledger"

    id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    cost_type: Mapped[str] = mapped_column(String(32), nullable=False)
    sub_type: Mapped[str] = mapped_column(String(128), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    unit_cost_usd: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    total_cost_usd: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    session_id: Mapped[PyUUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "cost_type IN ('llm', 'tool', 'storage')",
            name="ck_cost_ledger_cost_type",
        ),
        Index(
            "idx_cost_ledger_tenant_recorded",
            "tenant_id",
            "recorded_at",
        ),
        Index(
            "idx_cost_ledger_tenant_cost_type",
            "tenant_id",
            "cost_type",
            "recorded_at",
        ),
        Index(
            "idx_cost_ledger_session",
            "session_id",
            postgresql_where=text("session_id IS NOT NULL"),
        ),
    )


__all__ = [
    "CostLedger",
    "CostType",
]
