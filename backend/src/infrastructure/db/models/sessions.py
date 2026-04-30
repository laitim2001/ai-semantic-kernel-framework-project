"""
File: backend/src/infrastructure/db/models/sessions.py
Purpose: Sessions/Conversations ORM models (Session/Message/MessageEvent, partitioned).
Category: Infrastructure / ORM (Sessions & Conversations group, per 09-db-schema-design.md Group 2)
Scope: Sprint 49.2 (Day 2.1 — sessions partition + ORM)
Owner: infrastructure/db owner

Description:
    Session-scoped persistence for V2 conversational state. Maps to
    migration 0002_sessions_partitioned.

    Tables:
        sessions          - per-tenant conversation root (NOT partitioned)
        messages          - per-session message ledger (PARTITIONED by created_at month)
        message_events    - per-session SSE event stream (PARTITIONED by created_at month)

    Partition design (per 09-db-schema-design.md L1040-1095):
        - Partition by RANGE (created_at) at monthly boundaries
        - Composite PK (id, created_at) required by PostgreSQL partitioning rule
        - UNIQUE constraint must include partition key column
        - Sprint 49.2 manually creates first 2 months (2026_05, 2026_06)
        - pg_partman automation deferred to Sprint 49.3

    Key Design Notes:
        - sessions.current_state_snapshot_id: nullable UUID, FK constraint to
          state_snapshots(id) added in migration 0004 (chicken-and-egg avoidance)
        - messages.is_compacted + compacted_from_ids tracking: 49.2 keeps
          is_compacted bool only; compacted_from_ids array deferred per 09.md L1055
          to a separate `message_compaction_links` table in Sprint 49.3+

Created: 2026-04-29 (Sprint 49.2 Day 2.1)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.2 Day 2.1)

Related:
    - 09-db-schema-design.md §Group 2 Sessions & Conversations (L196-281, L1040-1095)
    - .claude/rules/multi-tenant-data.md 鐵律 1 (tenant_id NOT NULL on session-scoped tables)
    - infrastructure/db/base.py (TenantScopedMixin)
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID as PyUUID

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base, TenantScopedMixin


# =====================================================================
# Session - per-tenant conversation root (not partitioned)
# =====================================================================
class Session(Base, TenantScopedMixin):
    """Per-tenant conversation. Per 09-db-schema-design.md L196-225."""

    __tablename__ = "sessions"

    id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    title: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")

    # FK constraint to state_snapshots(id) added in migration 0004
    current_state_snapshot_id: Mapped[PyUUID | None] = mapped_column(
        PgUUID(as_uuid=True), nullable=True
    )

    total_turns: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(14, 6), nullable=False, server_default=text("0")
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    meta_data: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    __table_args__ = (
        Index("idx_sessions_tenant_user", "tenant_id", "user_id"),
        Index("idx_sessions_status", "status"),
        Index("idx_sessions_active", text("last_active_at DESC")),
    )


# =====================================================================
# Message - per-session message ledger (PARTITIONED by created_at)
# =====================================================================
class Message(Base, TenantScopedMixin):
    """
    Per-session message. Per 09-db-schema-design.md L227-261 + L1042-1075.

    Partitioned by RANGE (created_at) monthly. Composite PK includes
    created_at because PostgreSQL requires partition key in PK.
    """

    __tablename__ = "messages"

    id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        nullable=False,
        server_default=text("gen_random_uuid()"),
    )
    session_id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    sequence_num: Mapped[int] = mapped_column(Integer, nullable=False)
    turn_num: Mapped[int] = mapped_column(Integer, nullable=False)

    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    model: Mapped[str | None] = mapped_column(String(64))
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)

    is_compacted: Mapped[bool] = mapped_column(nullable=False, server_default=text("FALSE"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        # PK includes created_at because partition key must be in PK
        PrimaryKeyConstraint("id", "created_at", name="pk_messages"),
        # UNIQUE must include partition key (PostgreSQL rule)
        UniqueConstraint(
            "session_id",
            "sequence_num",
            "created_at",
            name="uq_messages_session_seq",
        ),
        Index("idx_messages_tenant_session", "tenant_id", "session_id", "created_at"),
        Index("idx_messages_role", "role"),
        # Partition by RANGE (created_at) — monthly partitions
        {"postgresql_partition_by": "RANGE (created_at)"},
    )


# =====================================================================
# MessageEvent - per-session SSE event stream (PARTITIONED by created_at)
# =====================================================================
class MessageEvent(Base, TenantScopedMixin):
    """
    SSE event stream persistence. Per 09-db-schema-design.md L267-281.

    Used for replay / debug. Partitioned by created_at monthly.
    Sprint 49.2 keeps first 2 months (2026_05, 2026_06); pg_partman
    automation deferred to Sprint 49.3.
    """

    __tablename__ = "message_events"

    id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        nullable=False,
        server_default=text("gen_random_uuid()"),
    )
    session_id: Mapped[PyUUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    sequence_num: Mapped[int] = mapped_column(BigInteger, nullable=False)
    timestamp_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        PrimaryKeyConstraint("id", "created_at", name="pk_message_events"),
        Index(
            "idx_message_events_session",
            "session_id",
            "sequence_num",
            "created_at",
        ),
        Index("idx_message_events_type", "event_type"),
        {"postgresql_partition_by": "RANGE (created_at)"},
    )


__all__ = ["Session", "Message", "MessageEvent"]
