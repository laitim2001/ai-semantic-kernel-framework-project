# =============================================================================
# IPA Platform - Memory Checkpoint Storage
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 57: Unified Checkpoint & Polish
#
# In-memory storage backend for HybridCheckpoint.
# Ideal for testing and development. Not suitable for production.
#
# Key Features:
#   - Fast in-memory operations
#   - No external dependencies
#   - Automatic TTL-based expiration
#   - Thread-safe with locks
#
# Dependencies:
#   - UnifiedCheckpointStorage (storage)
#   - HybridCheckpoint (models)
# =============================================================================

import asyncio
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, List, Optional, Set

from ..models import CheckpointStatus, CheckpointType, HybridCheckpoint, RestoreResult
from ..storage import (
    CheckpointQuery,
    StorageConfig,
    StorageError,
    StorageStats,
    UnifiedCheckpointStorage,
)


class MemoryCheckpointStorage(UnifiedCheckpointStorage):
    """
    In-memory storage backend for checkpoints.

    Stores checkpoints in a Python dictionary. Suitable for testing
    and development environments. Data is lost when the process ends.

    Example:
        >>> storage = MemoryCheckpointStorage()
        >>> checkpoint_id = await storage.save(checkpoint)
        >>> loaded = await storage.load(checkpoint_id)

    Thread Safety:
        All operations are protected by a lock for thread safety.
    """

    def __init__(self, config: Optional[StorageConfig] = None):
        """
        Initialize memory storage.

        Args:
            config: Storage configuration. Uses defaults if not provided.
        """
        super().__init__(config)
        self._checkpoints: Dict[str, HybridCheckpoint] = {}
        self._session_index: Dict[str, Set[str]] = {}  # session_id -> checkpoint_ids
        self._lock = Lock()

    async def save(self, checkpoint: HybridCheckpoint) -> str:
        """
        Save checkpoint to memory.

        Args:
            checkpoint: Checkpoint to save

        Returns:
            Checkpoint ID
        """
        with self._lock:
            checkpoint_id = checkpoint.checkpoint_id
            self._checkpoints[checkpoint_id] = checkpoint

            # Update session index
            session_id = checkpoint.session_id
            if session_id not in self._session_index:
                self._session_index[session_id] = set()
            self._session_index[session_id].add(checkpoint_id)

        # Enforce retention limits
        await self.enforce_retention(checkpoint.session_id)

        return checkpoint_id

    async def load(self, checkpoint_id: str) -> Optional[HybridCheckpoint]:
        """
        Load checkpoint from memory.

        Args:
            checkpoint_id: ID of checkpoint to load

        Returns:
            HybridCheckpoint if found and not expired, None otherwise
        """
        with self._lock:
            checkpoint = self._checkpoints.get(checkpoint_id)

            if checkpoint is None:
                return None

            # Check expiration
            if checkpoint.is_expired():
                return None

            return checkpoint

    async def delete(self, checkpoint_id: str) -> bool:
        """
        Delete checkpoint from memory.

        Args:
            checkpoint_id: ID of checkpoint to delete

        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if checkpoint_id not in self._checkpoints:
                return False

            checkpoint = self._checkpoints[checkpoint_id]
            session_id = checkpoint.session_id

            # Remove from main storage
            del self._checkpoints[checkpoint_id]

            # Remove from session index
            if session_id in self._session_index:
                self._session_index[session_id].discard(checkpoint_id)
                if not self._session_index[session_id]:
                    del self._session_index[session_id]

            return True

    async def exists(self, checkpoint_id: str) -> bool:
        """
        Check if checkpoint exists and is not expired.

        Args:
            checkpoint_id: ID of checkpoint to check

        Returns:
            True if exists and not expired, False otherwise
        """
        with self._lock:
            checkpoint = self._checkpoints.get(checkpoint_id)
            if checkpoint is None:
                return False
            return not checkpoint.is_expired()

    async def query(self, query: CheckpointQuery) -> List[HybridCheckpoint]:
        """
        Query checkpoints based on criteria.

        Args:
            query: Query parameters

        Returns:
            List of matching checkpoints
        """
        with self._lock:
            results: List[HybridCheckpoint] = []

            # Get candidate checkpoints
            if query.session_id:
                checkpoint_ids = self._session_index.get(query.session_id, set())
                candidates = [
                    self._checkpoints[cid]
                    for cid in checkpoint_ids
                    if cid in self._checkpoints
                ]
            else:
                candidates = list(self._checkpoints.values())

            # Apply filters
            for checkpoint in candidates:
                # Skip expired
                if checkpoint.is_expired():
                    continue

                # Filter by type
                if query.checkpoint_type and checkpoint.checkpoint_type != query.checkpoint_type:
                    continue

                # Filter by status
                if query.status and checkpoint.status != query.status:
                    continue

                # Filter by execution mode
                if query.execution_mode and checkpoint.execution_mode != query.execution_mode:
                    continue

                # Filter by creation time
                if query.created_after and checkpoint.created_at < query.created_after:
                    continue
                if query.created_before and checkpoint.created_at > query.created_before:
                    continue

                results.append(checkpoint)

            # Sort by order_by field
            if query.order_by == "created_at":
                results.sort(key=lambda c: c.created_at, reverse=not query.ascending)
            elif query.order_by == "updated_at":
                results.sort(key=lambda c: c.updated_at, reverse=not query.ascending)

            # Apply pagination
            start = query.offset
            end = start + query.limit if query.limit > 0 else None

            return results[start:end]

    async def get_stats(self) -> StorageStats:
        """
        Get storage statistics.

        Returns:
            StorageStats with current statistics
        """
        with self._lock:
            total = len(self._checkpoints)
            active = 0
            expired = 0
            oldest: Optional[datetime] = None
            newest: Optional[datetime] = None

            for checkpoint in self._checkpoints.values():
                if checkpoint.is_expired():
                    expired += 1
                else:
                    active += 1

                if oldest is None or checkpoint.created_at < oldest:
                    oldest = checkpoint.created_at
                if newest is None or checkpoint.created_at > newest:
                    newest = checkpoint.created_at

            # Estimate size (rough approximation)
            total_size = sum(
                len(str(c.to_dict())) for c in self._checkpoints.values()
            )

            return StorageStats(
                total_checkpoints=total,
                active_checkpoints=active,
                expired_checkpoints=expired,
                total_size_bytes=total_size,
                sessions_count=len(self._session_index),
                oldest_checkpoint=oldest,
                newest_checkpoint=newest,
            )

    async def cleanup_expired(self) -> int:
        """
        Remove expired checkpoints.

        Returns:
            Number of checkpoints removed
        """
        with self._lock:
            expired_ids = [
                cid for cid, c in self._checkpoints.items() if c.is_expired()
            ]

        # Delete expired checkpoints (outside lock to avoid deadlock)
        removed = 0
        for checkpoint_id in expired_ids:
            if await self.delete(checkpoint_id):
                removed += 1

        return removed

    def clear(self) -> None:
        """
        Clear all checkpoints from memory.

        WARNING: This removes all data. Use with caution.
        """
        with self._lock:
            self._checkpoints.clear()
            self._session_index.clear()

    def get_checkpoint_count(self) -> int:
        """Get total number of stored checkpoints."""
        with self._lock:
            return len(self._checkpoints)

    def get_session_count(self) -> int:
        """Get number of unique sessions."""
        with self._lock:
            return len(self._session_index)
