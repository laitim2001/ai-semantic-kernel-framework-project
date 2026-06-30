"""memory_session_summary.updated_at — rolling-summary recency (Sprint 57.151).

Revision ID: 0033_session_summary_updated_at
Revises: 0032_memory_user_dedup_key
Create Date: 2026-06-30

File: backend/src/infrastructure/db/migrations/versions/0033_session_summary_updated_at.py
Purpose: Add an additive updated_at column to the designed-but-unwired
    memory_session_summary table (Layer 5 persisted summary) so a per-session
    rolling summary can be ordered by recency for cross-session recall. Closes
    AD-Memory-Formation-Session-Recall (缺口 2): the memory-formation arc recalls
    discrete user facts (57.148/149/150) but not the conversation arc of a prior
    session; this sprint fills memory_session_summary via a rolling upsert
    (one row per session — the session_id UNIQUE) and recalls the user's recent
    prior-session summaries (ORDER BY updated_at DESC). The table already exists
    (0007_memory_layers) — this migration ONLY adds updated_at.
Category: Infrastructure / Migration (Sprint 57.151 — Cat 3 Memory session recall)
Scope: Sprint 57.151 / US-1

Note: the revision id is kept ≤ 32 chars — alembic_version.version_num is
    VARCHAR(32) (the long form 0033_memory_session_summary_updated_at = 38 chars
    raised StringDataRightTruncationError on the version write — Day-1 finding).

upgrade():
    1. Add memory_session_summary.updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
       (additive; existing rows get now() during the ALTER).
    2. Backfill updated_at = created_at so pre-existing rows reflect their real
       creation time, not the migration time.

    No table create (memory_session_summary lands in 0007). No RLS change — the
    table is junction-style (tenant via session FK; NO direct RLS — 0009 docstring),
    so it is NOT in RLS_TABLES.

downgrade():
    Drop the updated_at column.

Modification History:
    - 2026-06-30: Initial creation (Sprint 57.151 / US-1)

Related:
    - 0032_memory_user_dedup_key.py — recent migration (mirror)
    - infrastructure/db/models/memory.py:MemorySessionSummary — ORM (+ updated_at)
    - agent_harness/memory/session_summary_store.py — DBSessionSummaryStore (orders by updated_at)
    - sprint-57-151-plan.md §3.1
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0033_session_summary_updated_at"
down_revision: Union[str, None] = "0032_memory_user_dedup_key"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Backfill pre-existing rows to their creation time (not the migration's now()).
_BACKFILL_SQL = """
    UPDATE memory_session_summary
       SET updated_at = created_at
"""


def upgrade() -> None:
    """Add updated_at (additive) + backfill = created_at."""
    op.add_column(
        "memory_session_summary",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.execute(_BACKFILL_SQL)


def downgrade() -> None:
    """Drop the updated_at column."""
    op.drop_column("memory_session_summary", "updated_at")
