"""Sessions / Messages (partitioned) / MessageEvents (partitioned) (Sprint 49.2 Day 2.2).

Revision ID: 0002_sessions_partitioned
Revises: 0001_initial_identity
Create Date: 2026-04-29

File: backend/src/infrastructure/db/migrations/versions/0002_sessions_partitioned.py
Purpose: Create sessions + messages (partitioned) + message_events (partitioned).
Category: Infrastructure / Migration (Phase 49 Foundation)
Scope: Sprint 49.2 Day 2.2

Tables created:
    1. sessions          (NOT partitioned; per-tenant conversation root)
    2. messages          (PARTITIONED BY RANGE (created_at); 3 months created)
       - messages_2026_04  : 2026-04-01 to 2026-05-01 (current month for default NOW())
       - messages_2026_05  : 2026-05-01 to 2026-06-01
       - messages_2026_06  : 2026-06-01 to 2026-07-01
    3. message_events    (PARTITIONED BY RANGE (created_at); 3 months created)
       - message_events_2026_04
       - message_events_2026_05
       - message_events_2026_06

Per 09-db-schema-design.md §Group 2 (L196-281, L1042-1095).

Multi-tenant rule (鐵律 1):
    All 3 tables carry tenant_id NOT NULL via TenantScopedMixin.

Partition design notes:
    - PostgreSQL requires partition key in PRIMARY KEY → composite PK (id, created_at)
    - PostgreSQL requires UNIQUE constraints to include partition key → adds created_at
    - pg_partman automation deferred to Sprint 49.3 (49.2 manually creates 2 months)

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.2 Day 2.2)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_sessions_partitioned"
down_revision: Union[str, None] = "0001_initial_identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Sessions + partitioned Messages + partitioned MessageEvents."""

    # ----- sessions (not partitioned) ---------------------------------
    op.create_table(
        "sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        # FK constraint to state_snapshots(id) added in 0004
        sa.Column(
            "current_state_snapshot_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("total_turns", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("total_tokens", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column(
            "total_cost_usd",
            sa.Numeric(14, 6),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_active_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index("ix_sessions_tenant_id", "sessions", ["tenant_id"])
    op.create_index("idx_sessions_tenant_user", "sessions", ["tenant_id", "user_id"])
    op.create_index("idx_sessions_status", "sessions", ["status"])
    # DESC index — use raw SQL since op.create_index doesn't handle ORDER BY
    op.execute("CREATE INDEX idx_sessions_active ON sessions (last_active_at DESC)")

    # ----- messages (PARTITIONED) -------------------------------------
    op.create_table(
        "messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence_num", sa.Integer, nullable=False),
        sa.Column("turn_num", sa.Integer, nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("content_type", sa.String(32), nullable=False),
        sa.Column("content", postgresql.JSONB, nullable=False),
        sa.Column("model", sa.String(64), nullable=True),
        sa.Column("tokens_in", sa.Integer, nullable=True),
        sa.Column("tokens_out", sa.Integer, nullable=True),
        sa.Column(
            "is_compacted",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", "created_at", name="pk_messages"),
        sa.UniqueConstraint(
            "session_id",
            "sequence_num",
            "created_at",
            name="uq_messages_session_seq",
        ),
        postgresql_partition_by="RANGE (created_at)",
    )
    # Partition children — 49.2 Day 1 starts 2026-04-29, so include 2026-04
    op.execute(
        "CREATE TABLE messages_2026_04 PARTITION OF messages "
        "FOR VALUES FROM ('2026-04-01') TO ('2026-05-01')"
    )
    op.execute(
        "CREATE TABLE messages_2026_05 PARTITION OF messages "
        "FOR VALUES FROM ('2026-05-01') TO ('2026-06-01')"
    )
    op.execute(
        "CREATE TABLE messages_2026_06 PARTITION OF messages "
        "FOR VALUES FROM ('2026-06-01') TO ('2026-07-01')"
    )
    # Indexes on the parent table propagate to all partitions (PG 11+)
    op.create_index("ix_messages_tenant_id", "messages", ["tenant_id"])
    op.create_index(
        "idx_messages_tenant_session",
        "messages",
        ["tenant_id", "session_id", "created_at"],
    )
    op.create_index("idx_messages_role", "messages", ["role"])

    # ----- message_events (PARTITIONED) -------------------------------
    op.create_table(
        "message_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("event_data", postgresql.JSONB, nullable=False),
        sa.Column("sequence_num", sa.BigInteger, nullable=False),
        sa.Column("timestamp_ms", sa.BigInteger, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", "created_at", name="pk_message_events"),
        postgresql_partition_by="RANGE (created_at)",
    )
    op.execute(
        "CREATE TABLE message_events_2026_04 PARTITION OF message_events "
        "FOR VALUES FROM ('2026-04-01') TO ('2026-05-01')"
    )
    op.execute(
        "CREATE TABLE message_events_2026_05 PARTITION OF message_events "
        "FOR VALUES FROM ('2026-05-01') TO ('2026-06-01')"
    )
    op.execute(
        "CREATE TABLE message_events_2026_06 PARTITION OF message_events "
        "FOR VALUES FROM ('2026-06-01') TO ('2026-07-01')"
    )
    op.create_index("ix_message_events_tenant_id", "message_events", ["tenant_id"])
    op.create_index(
        "idx_message_events_session",
        "message_events",
        ["session_id", "sequence_num", "created_at"],
    )
    op.create_index("idx_message_events_type", "message_events", ["event_type"])


def downgrade() -> None:
    """Drop in reverse dependency order. Partitions drop cascades from parent."""
    # message_events
    op.drop_index("idx_message_events_type", table_name="message_events")
    op.drop_index("idx_message_events_session", table_name="message_events")
    op.drop_index("ix_message_events_tenant_id", table_name="message_events")
    # Dropping the partitioned parent drops all attached partitions
    op.drop_table("message_events")

    # messages
    op.drop_index("idx_messages_role", table_name="messages")
    op.drop_index("idx_messages_tenant_session", table_name="messages")
    op.drop_index("ix_messages_tenant_id", table_name="messages")
    op.drop_table("messages")

    # sessions
    op.execute("DROP INDEX IF EXISTS idx_sessions_active")
    op.drop_index("idx_sessions_status", table_name="sessions")
    op.drop_index("idx_sessions_tenant_user", table_name="sessions")
    op.drop_index("ix_sessions_tenant_id", table_name="sessions")
    op.drop_table("sessions")
