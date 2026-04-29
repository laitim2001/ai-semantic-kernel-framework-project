"""
File: backend/src/infrastructure/db/models/tools.py
Purpose: Tools ORM models (ToolRegistry global / ToolCall + ToolResult per-tenant).
Category: Infrastructure / ORM (Tools group, per 09-db-schema-design.md Group 3)
Scope: Sprint 49.2 (Day 3.1 - tools migration + ORM)
Owner: infrastructure/db owner

Description:
    Tool execution persistence layer for V2. Maps to migration 0003_tools.

    Tables:
        tools_registry  - GLOBAL tool metadata (NO tenant_id; shared across tenants)
        tool_calls      - per-tenant tool invocation record (TenantScopedMixin)
        tool_results    - per-call result (NO tenant_id; tenant via tool_call FK chain)

Key Design Notes:
    - tools_registry is intentionally global per 09-db-schema-design.md L290-326.
      Tool definitions (e.g., "memory_search v1.0") are shared infrastructure;
      per-tenant access policy lives in role_permissions (Day 1).
    - tool_calls.message_id has NO FK constraint to messages(id):
      messages is partitioned with composite PK (id, created_at), so a single-
      column FK target is unsupported in PostgreSQL 16. We keep the column as
      plain UUID. (PG 18+ partial partition FK or composite message ref
      could revisit in Sprint 49.3+.)
    - tool_calls.approval_id has NO FK constraint here; FK to approvals(id)
      added in Sprint 49.3 (governance migration).
    - tool_results does NOT carry tenant_id per 09.md L25 list. Tenant scope
      inferred via tool_call FK chain. Junction-style.

Created: 2026-04-29 (Sprint 49.2 Day 3.1)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.2 Day 3.1)

Related:
    - 09-db-schema-design.md Group 3 Tools (L286-380)
    - .claude/rules/multi-tenant-data.md
    - infrastructure/db/base.py (TenantScopedMixin)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID as PyUUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
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
# ToolRegistry - GLOBAL tool metadata (no tenant_id)
# =====================================================================
class ToolRegistry(Base):
    """Global tool metadata. Per 09-db-schema-design.md L290-326."""

    __tablename__ = "tools_registry"

    id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'1.0'"))
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    input_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    output_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    is_mutating: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    sandbox_level: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'none'")
    )

    hitl_policy: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'auto'")
    )
    risk_level: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'low'")
    )

    required_permission: Mapped[str | None] = mapped_column(String(128))

    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'active'"))

    meta_data: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_tools_name_version"),
        Index(
            "idx_tools_status",
            "status",
            postgresql_where=text("status = 'active'"),
        ),
        Index("idx_tools_category", "category"),
    )


# =====================================================================
# ToolCall - per-tenant tool invocation
# =====================================================================
class ToolCall(Base, TenantScopedMixin):
    """Per-tenant tool invocation. Per 09-db-schema-design.md L329-360."""

    __tablename__ = "tool_calls"

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

    # No FK to messages(id) — messages PK is composite (id, created_at) due to
    # partitioning, single-column FK unsupported in PostgreSQL 16.
    message_id: Mapped[PyUUID | None] = mapped_column(PgUUID(as_uuid=True))

    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_version: Mapped[str | None] = mapped_column(String(32))

    arguments: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    permission_check_passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # FK to approvals(id) added in Sprint 49.3 governance migration
    approval_id: Mapped[PyUUID | None] = mapped_column(PgUUID(as_uuid=True))

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'pending'")
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    sandbox_used: Mapped[str | None] = mapped_column(String(32))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_tool_calls_session", "session_id"),
        Index("idx_tool_calls_status", "status"),
        Index("idx_tool_calls_tool", "tool_name"),
    )


# =====================================================================
# ToolResult - per-call result (no tenant_id; via FK chain)
# =====================================================================
class ToolResult(Base):
    """Per-call result. Per 09-db-schema-design.md L363-380."""

    __tablename__ = "tool_results"

    id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tool_call_id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tool_calls.id", ondelete="CASCADE"),
        nullable=False,
    )

    is_error: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    raw_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("idx_tool_results_call", "tool_call_id"),)


__all__ = ["ToolRegistry", "ToolCall", "ToolResult"]
