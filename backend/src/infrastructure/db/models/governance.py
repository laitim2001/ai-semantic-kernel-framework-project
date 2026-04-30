"""
File: backend/src/infrastructure/db/models/governance.py
Purpose: Governance ORM — Approval (HITL) / RiskAssessment / GuardrailEvent.
Category: Infrastructure / ORM (Governance / 範疇 9 + HITL schema layer)
Scope: Sprint 49.3 (Day 3.1-3.3 - governance 3 tables)
Owner: infrastructure/db owner

Description:
    Three persistence tables that range 9 (Guardrails) + range 9-HITL
    (Approvals) + range 12 (Observability for risk audit) consume.

    Table layout (per 09-db-schema-design.md L562-648):
        approvals          — HITL audit trail; pending/approved/rejected/expired
        risk_assessments   — Pre-action risk scoring; may trigger approval
        guardrail_events   — Per-check log (input/output/tool/tripwire layers)

    Junction-via-session pattern:
        09.md authority shows NO direct tenant_id on these 3 tables;
        tenant is resolved via session_id → sessions.tenant_id chain.
        Same junction pattern as memory_session_summary / user_roles /
        role_permissions (49.2). The plan said "TenantScopedMixin"; we
        align to 09.md.

        For cross-tenant query safety, callers must JOIN sessions on
        session_id and filter sessions.tenant_id. RLS policies in 0009
        (Day 4) will enforce the same boundary at the storage layer for
        any direct query that lacks the JOIN.

    guardrail_events.session_id is nullable: tripwires fired during
    pre-session checks (input layer) may not have a session yet.
    For those rows, tenant is unresolvable from this table alone;
    callers should embed tenant context in the metadata JSONB.

Created: 2026-04-29 (Sprint 49.3 Day 3.1-3.3)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.3 Day 3.1-3.3)

Related:
    - 09-db-schema-design.md Group 6 Governance (L560-648)
    - 14-security-deep-dive.md §HITL / risk gating
    - 17-cross-category-interfaces.md §Contract 9 ApprovalRequest
    - .claude/rules/multi-tenant-data.md 鐵律 1 (junction-table exemptions)
    - sprint-49-3-plan.md §Story 49.3-5
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID as PyUUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base


# ============================================================================
# approvals — HITL audit trail
# ============================================================================
class Approval(Base):
    """HITL approval record. Per 09-db-schema-design.md L566-601.

    State machine: pending → approved | rejected | expired.
    Junction via session_id (no direct tenant_id; tenant via session chain).
    """

    __tablename__ = "approvals"

    id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    session_id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # What needs approval
    action_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="tool_call / send_email / modify_data",
    )
    action_summary: Mapped[str] = mapped_column(Text, nullable=False)
    action_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Risk snapshot at request time
    risk_level: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        doc="low / medium / high / critical",
    )
    risk_score: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    risk_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Approver
    required_approver_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approver_user_id: Mapped[PyUUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    # State
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'pending'"),
        doc="pending / approved / rejected / expired",
    )
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Notification (Teams integration; populated when sent)
    teams_notification_sent: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("FALSE"),
    )
    teams_message_id: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_approvals_status", "status"),
        Index("idx_approvals_session", "session_id"),
        Index(
            "idx_approvals_pending",
            "created_at",
            postgresql_where=text("status = 'pending'"),
        ),
    )


# ============================================================================
# risk_assessments — pre-action risk scoring
# ============================================================================
class RiskAssessment(Base):
    """Per-call risk record. Per 09-db-schema-design.md L605-622.

    Junction via session_id. May reference an originating tool_call_id.
    """

    __tablename__ = "risk_assessments"

    id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    session_id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    tool_call_id: Mapped[PyUUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tool_calls.id"),
        nullable=True,
    )

    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_score: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)

    triggered_rules: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        doc="Policy rule names that fired.",
    )
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("idx_risk_session", "session_id"),)


# ============================================================================
# guardrail_events — per-check log
# ============================================================================
class GuardrailEvent(Base):
    """Guardrail check record. Per 09-db-schema-design.md L628-648.

    session_id is NULLABLE — input-layer tripwires may fire pre-session.
    Layers: input / output / tool / tripwire.
    Action_taken: allow / block / tripwire_fired.
    """

    __tablename__ = "guardrail_events"

    id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    session_id: Mapped[PyUUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=True,
        doc="Nullable: pre-session input checks may not have a session yet.",
    )

    layer: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        doc="input / output / tool / tripwire",
    )
    check_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="pii / jailbreak / toxicity / permission",
    )

    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    severity: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        doc="info / warning / error / critical",
    )

    detected_pattern: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_taken: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        doc="allow / block / tripwire_fired",
    )

    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_guardrail_events_session", "session_id"),
        Index("idx_guardrail_events_layer", "layer"),
        Index(
            "idx_guardrail_events_failed",
            "created_at",
            postgresql_where=text("passed = FALSE"),
        ),
    )


__all__ = ["Approval", "RiskAssessment", "GuardrailEvent"]
