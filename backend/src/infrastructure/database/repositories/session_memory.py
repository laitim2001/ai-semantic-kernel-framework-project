# =============================================================================
# IPA Platform - Session Memory Repository
# =============================================================================
# Sprint 172 (Phase 48): CRUD + upsert + expiration cleanup for L2 store.
#
# The repository is the authoritative path for persistent session memory.
# The Redis cache layer is handled directly by UnifiedMemoryManager.
# =============================================================================

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.infrastructure.database.models.session_memory import SessionMemory
from src.infrastructure.database.repositories.base import BaseRepository


class SessionMemoryRepository(BaseRepository[SessionMemory]):
    """Persistence operations for ``SessionMemory`` rows.

    Provides ``upsert`` via PostgreSQL ``ON CONFLICT (memory_id) DO UPDATE``
    so that the dual-write path from ``UnifiedMemoryManager`` is idempotent.
    """

    model = SessionMemory

    async def get_by_memory_id(self, memory_id: str) -> Optional[SessionMemory]:
        """Return the record matching ``memory_id`` or ``None``."""
        stmt = select(SessionMemory).where(SessionMemory.memory_id == memory_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: str,
        limit: int = 100,
    ) -> List[SessionMemory]:
        """List unexpired session memories for a user.

        Filters out ``expires_at < now()`` defensively — the cleanup job
        removes them eventually, but readers should not see stale rows.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            select(SessionMemory)
            .where(
                SessionMemory.user_id == user_id,
                # Either no expiry or still valid
                (SessionMemory.expires_at.is_(None)) | (SessionMemory.expires_at > now),
            )
            .order_by(SessionMemory.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def upsert(
        self,
        memory_id: str,
        user_id: str,
        content: str,
        memory_type: str,
        importance: float,
        access_count: int = 0,
        accessed_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        extra_metadata: Optional[dict] = None,
        tags: Optional[List[str]] = None,
    ) -> SessionMemory:
        """Insert or update a session memory row.

        Uses PostgreSQL ``ON CONFLICT (memory_id) DO UPDATE`` for atomicity.
        Backfill script relies on this to be idempotent (running twice
        produces no duplicates — AC-4 of plan).
        """
        payload = {
            "memory_id": memory_id,
            "user_id": user_id,
            "content": content,
            "memory_type": memory_type,
            "importance": importance,
            "access_count": access_count,
            "accessed_at": accessed_at,
            "expires_at": expires_at,
            "extra_metadata": extra_metadata or {},
            "tags": tags or [],
        }

        stmt = pg_insert(SessionMemory).values(**payload)
        # DO UPDATE on the subset that should be overwritten on second insert.
        # ``memory_id`` and ``id`` are immutable per logical memory.
        update_payload = {
            "user_id": stmt.excluded.user_id,
            "content": stmt.excluded.content,
            "memory_type": stmt.excluded.memory_type,
            "importance": stmt.excluded.importance,
            "access_count": stmt.excluded.access_count,
            "accessed_at": stmt.excluded.accessed_at,
            "expires_at": stmt.excluded.expires_at,
            "extra_metadata": stmt.excluded.extra_metadata,
            "tags": stmt.excluded.tags,
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=[SessionMemory.memory_id],
            set_=update_payload,
        ).returning(SessionMemory)

        result = await self._session.execute(stmt)
        await self._session.flush()
        # ``returning`` with on_conflict returns the row regardless of branch
        row = result.scalar_one()
        return row

    async def delete_by_memory_id(self, memory_id: str) -> bool:
        """Delete the row matching ``memory_id``. Returns True if a row was
        removed."""
        stmt = sa_delete(SessionMemory).where(SessionMemory.memory_id == memory_id)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return (result.rowcount or 0) > 0

    async def delete_expired(self) -> int:
        """Remove rows whose ``expires_at`` is in the past.

        Returns the number of rows deleted. Intended to be called by a
        periodic background task (see Sprint 172 plan §6 expiration cleanup).
        """
        now = datetime.now(timezone.utc)
        stmt = sa_delete(SessionMemory).where(
            SessionMemory.expires_at.is_not(None),
            SessionMemory.expires_at < now,
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount or 0
