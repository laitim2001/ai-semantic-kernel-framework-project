"""
Session Store — Sprint 110

Persistent dialog session storage backed by StorageBackendABC.
Drop-in replacement for InMemory session dicts used across the codebase.

Provides a dict-like async interface backed by Redis (with TTL) or PostgreSQL.

Usage:
    store = await SessionStore.create(backend_type="redis", ttl_hours=24)
    await store.set("session_123", {"user_id": "u1", "messages": []})
    session = await store.get("session_123")
    await store.delete("session_123")
"""

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from src.infrastructure.storage.backends.base import StorageBackendABC
from src.infrastructure.storage.backends.factory import StorageFactory

logger = logging.getLogger(__name__)


class SessionStore:
    """
    Dict-like session store backed by StorageBackendABC.

    Drop-in replacement for `self._sessions: Dict[str, Dict] = {}`
    patterns found across the codebase.

    Features:
    - Automatic TTL (default: 24 hours)
    - Backend-agnostic (Redis, PostgreSQL, or InMemory)
    - Session metadata tracking (created_at, last_accessed)
    - Batch operations for efficiency

    Args:
        backend: StorageBackendABC instance.
        default_ttl: Default TTL for sessions. None means no expiration.
    """

    def __init__(
        self,
        backend: StorageBackendABC,
        default_ttl: Optional[timedelta] = None,
    ):
        self._backend = backend
        self._default_ttl = default_ttl

    @classmethod
    async def create(
        cls,
        backend_type: str = "auto",
        ttl_hours: int = 24,
        **kwargs,
    ) -> "SessionStore":
        """
        Factory method to create a SessionStore with auto-configured backend.

        Args:
            backend_type: "memory", "redis", "postgres", or "auto".
            ttl_hours: Default session TTL in hours (default: 24).
            **kwargs: Additional backend configuration.

        Returns:
            Configured SessionStore instance.
        """
        default_ttl = timedelta(hours=ttl_hours)
        backend = await StorageFactory.create(
            name="sessions",
            backend_type=backend_type,
            default_ttl=default_ttl,
            **kwargs,
        )
        logger.info(
            f"SessionStore created with {type(backend).__name__} "
            f"(ttl={ttl_hours}h)"
        )
        return cls(backend=backend, default_ttl=default_ttl)

    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data by ID.

        Args:
            session_id: Unique session identifier.

        Returns:
            Session data dict, or None if not found/expired.
        """
        return await self._backend.get(session_id)

    async def set(
        self,
        session_id: str,
        data: Dict[str, Any],
        ttl: Optional[timedelta] = None,
    ) -> None:
        """
        Create or update a session.

        Args:
            session_id: Unique session identifier.
            data: Session data to store.
            ttl: Override TTL for this session. None uses default.
        """
        await self._backend.set(session_id, data, ttl=ttl)

    async def delete(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session to delete.

        Returns:
            True if session existed and was deleted.
        """
        return await self._backend.delete(session_id)

    async def exists(self, session_id: str) -> bool:
        """
        Check if a session exists (and is not expired).

        Args:
            session_id: Session to check.

        Returns:
            True if session exists.
        """
        return await self._backend.exists(session_id)

    async def list_sessions(self, pattern: str = "*") -> List[str]:
        """
        List session IDs matching a pattern.

        Args:
            pattern: Glob pattern (e.g., "user_123:*").

        Returns:
            List of matching session IDs.
        """
        return await self._backend.keys(pattern)

    async def count(self) -> int:
        """
        Count active (non-expired) sessions.

        Returns:
            Number of active sessions.
        """
        return await self._backend.count()

    async def get_many(
        self, session_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get multiple sessions by ID.

        Args:
            session_ids: List of session IDs.

        Returns:
            Dict mapping session_id to data (missing sessions omitted).
        """
        return await self._backend.get_many(session_ids)

    async def update(
        self,
        session_id: str,
        updates: Dict[str, Any],
        ttl: Optional[timedelta] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Partially update a session (merge updates into existing data).

        Args:
            session_id: Session to update.
            updates: Fields to merge into existing session data.
            ttl: Override TTL. None preserves existing TTL behavior.

        Returns:
            Updated session data, or None if session not found.
        """
        existing = await self._backend.get(session_id)
        if existing is None:
            return None

        if isinstance(existing, dict):
            existing.update(updates)
        else:
            existing = updates

        await self._backend.set(session_id, existing, ttl=ttl)
        return existing

    async def clear(self) -> None:
        """Delete all sessions managed by this store."""
        await self._backend.clear()
        logger.info("SessionStore: all sessions cleared")
