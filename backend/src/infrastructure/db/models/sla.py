"""
File: backend/src/infrastructure/db/models/sla.py
Purpose: SLAViolation + SLAReport ORM — per-tenant SLA tracking + monthly aggregate.
Category: Infrastructure / ORM (Phase 56 SaaS Stage 1 / platform_layer.observability)
Scope: Sprint 56.3 / Day 2 / US-2 SLA Monthly Report

Description:
    Two tables backing the SLAReportGenerator (US-2):

    `sla_violations` — append-only record of every SLA threshold breach
        detected by SLAReportGenerator while computing monthly reports.
        Each row is a single (tenant, metric, month) violation event;
        `resolved_at` set when next month's report shows compliance.

    `sla_reports` — per-tenant per-month aggregate cached for fast
        admin endpoint reads. UNIQUE (tenant_id, month) — exactly one row
        per tenant-month. Generated lazily on first GET, then cached.

    Both tables inherit TenantScopedMixin (multi-tenant 鐵律 1: tenant_id NN
    + FK CASCADE + RLS via 0016 migration).

Key Components:
    - SLASeverity: enum mirror of CHECK constraint
    - SLAMetricType: enum mirror of metric_type values
    - SLAViolation: ORM
    - SLAReport: ORM

Created: 2026-05-06 (Sprint 56.3 Day 2)

Modification History:
    - 2026-05-06: Initial creation (Sprint 56.3 Day 2 / US-2)

Related:
    - 15-saas-readiness.md §SLA 承諾 + §SLA 監控
    - sprint-56-3-plan.md §US-2 SLA Monthly Report + DB Schema
    - migrations/versions/0016_sla_and_cost_ledger.py
    - platform_layer/observability/sla_monitor.py (US-1 — SLAMetricRecorder)
    - .claude/rules/multi-tenant-data.md 鐵律 1 (tenant_id NN + RLS)
"""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID as PyUUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base, TenantScopedMixin


class SLASeverity(str, enum.Enum):
    """SLA violation severity — matches CHECK constraint on sla_violations.severity."""

    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


class SLAMetricType(str, enum.Enum):
    """SLA metric type — matches CHECK constraint on sla_violations.metric_type."""

    AVAILABILITY = "availability"
    API_P99 = "api_p99"
    LOOP_SIMPLE_P99 = "loop_simple_p99"
    LOOP_MEDIUM_P99 = "loop_medium_p99"
    LOOP_COMPLEX_P99 = "loop_complex_p99"
    HITL_QUEUE_NOTIF_P99 = "hitl_queue_notif_p99"


class SLAViolation(Base, TenantScopedMixin):
    """Append-only SLA threshold breach record."""

    __tablename__ = "sla_violations"

    id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    metric_type: Mapped[str] = mapped_column(String(64), nullable=False)
    threshold_pct: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    actual_pct: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_sla_violations_tenant_id"),
        CheckConstraint(
            "metric_type IN ('availability', 'api_p99', 'loop_simple_p99', "
            "'loop_medium_p99', 'loop_complex_p99', 'hitl_queue_notif_p99')",
            name="ck_sla_violations_metric_type",
        ),
        CheckConstraint(
            "severity IN ('minor', 'major', 'critical')",
            name="ck_sla_violations_severity",
        ),
        Index(
            "idx_sla_violations_tenant_detected",
            "tenant_id",
            "detected_at",
        ),
    )


class SLAReport(Base, TenantScopedMixin):
    """Per-tenant per-month SLA aggregate cache."""

    __tablename__ = "sla_reports"

    id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    month: Mapped[str] = mapped_column(String(7), nullable=False)  # 'YYYY-MM'
    availability_pct: Mapped[float] = mapped_column(
        Numeric(8, 4), nullable=False, server_default=text("0")
    )
    api_p99_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    loop_simple_p99_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    loop_medium_p99_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    loop_complex_p99_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hitl_queue_notif_p99_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    violations_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (UniqueConstraint("tenant_id", "month", name="uq_sla_reports_tenant_month"),)


__all__ = [
    "SLAMetricType",
    "SLAReport",
    "SLASeverity",
    "SLAViolation",
]
