# =============================================================================
# IPA Platform - Session Memory ORM Model
# =============================================================================
# Sprint 172 (Phase 48): L2 Session Memory lands on PostgreSQL.
#
# Replaces the Redis-only L2 store noted at
# ``integrations/memory/unified_memory.py:287`` ("In production, this would
# use PostgreSQL"). Session state now survives process restart.
#
# Dual-write contract (see UnifiedMemoryManager._store_session_memory):
#   - PostgreSQL: authoritative store
#   - Redis: write-through cache with TTL <= PG expires_at
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.models.base import Base, TimestampMixin, UUIDMixin


class SessionMemory(Base, UUIDMixin, TimestampMixin):
    """Persistent session-tier memory record (L2 store).

    Complements the Redis working-memory cache. A single logical memory
    is identified by ``memory_id`` (UUID stringified) which is unique across
    the table — the ORM primary key ``id`` is an independent UUID so repos
    can upsert by ``memory_id`` without caring about PK generation.
    """

    __tablename__ = "session_memory"

    # External memory identifier (matches MemoryRecord.id in the
    # UnifiedMemoryManager; unique across the table for upsert safety).
    memory_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    # Tenant-scope primitive (full multi-tenant scope arrives in Sprint 173).
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    # Core fields mirrored from MemoryRecord.
    content: Mapped[str] = mapped_column(Text, nullable=False)
    memory_type: Mapped[str] = mapped_column(String(64), nullable=False)
    importance: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)

    # Access tracking — PG holds the authoritative value (updated during
    # promotion/consolidation, not on every search hit). Redis counter keys
    # from Sprint 170 serve as the hot write-through cache.
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accessed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Expiration — replaces Redis TTL semantics. Background cleanup job
    # deletes rows where ``expires_at < now()`` on an hourly cadence.
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, index=True)

    # Structured metadata mirroring MemoryMetadata (includes superseded_by /
    # summarized_into from Sprint 171). Column name is ``extra_metadata`` to
    # avoid conflict with SQLAlchemy's Base.metadata registry attribute.
    extra_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)

    __table_args__ = (
        Index("ix_session_memory_user_id", "user_id"),
        Index("ix_session_memory_expires_at", "expires_at"),
        # memory_id has its own unique constraint; explicit index for lookup speed
        Index("ix_session_memory_memory_id", "memory_id", unique=True),
    )

    def __repr__(self) -> str:
        return (
            f"<SessionMemory memory_id={self.memory_id!r} user_id={self.user_id!r} "
            f"importance={self.importance} expires_at={self.expires_at}>"
        )
