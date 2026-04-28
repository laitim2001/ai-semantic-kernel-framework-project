# =============================================================================
# IPA Platform - Redis Checkpoint Storage
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 57: Unified Checkpoint & Polish
#
# Redis storage backend for HybridCheckpoint.
# Primary storage for fast access with automatic TTL expiration.
#
# Key Features:
#   - Fast read/write operations
#   - Automatic TTL-based expiration
#   - Session-based indexing with sorted sets
#   - Atomic operations for data integrity
#
# Dependencies:
#   - redis.asyncio (Redis async client)
#   - UnifiedCheckpointStorage (storage)
#   - HybridCheckpoint (models)
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models import CheckpointStatus, CheckpointType, HybridCheckpoint, RestoreResult
from ..storage import (
    CheckpointQuery,
    StorageConfig,
    StorageConnectionError,
    StorageError,
    StorageStats,
    UnifiedCheckpointStorage,
)


class RedisCheckpointStorage(UnifiedCheckpointStorage):
    """
    Redis storage backend for checkpoints.

    Stores checkpoints in Redis with automatic TTL expiration.
    Uses sorted sets for session-based indexing and efficient queries.

    Key Structure:
        - checkpoint:{id} - Serialized checkpoint data
        - session:{session_id}:checkpoints - Sorted set of checkpoint IDs (by timestamp)
        - checkpoint:stats - Global statistics

    Example:
        >>> from redis.asyncio import Redis
        >>> redis = Redis(host='localhost', port=6379)
        >>> storage = RedisCheckpointStorage(redis_client=redis)
        >>> checkpoint_id = await storage.save(checkpoint)

    Note:
        Requires redis.asyncio package.
    """

    def __init__(
        self,
        redis_client: Any = None,
        config: Optional[StorageConfig] = None,
        key_prefix: str = "ipa:checkpoint",
    ):
        """
        Initialize Redis storage.

        Args:
            redis_client: Redis async client instance
            config: Storage configuration
            key_prefix: Prefix for all Redis keys
        """
        super().__init__(config)
        self._redis = redis_client
        self._key_prefix = key_prefix

    def _checkpoint_key(self, checkpoint_id: str) -> str:
        """Generate Redis key for checkpoint data."""
        return f"{self._key_prefix}:data:{checkpoint_id}"

    def _session_key(self, session_id: str) -> str:
        """Generate Redis key for session index."""
        return f"{self._key_prefix}:session:{session_id}"

    def _stats_key(self) -> str:
        """Generate Redis key for statistics."""
        return f"{self._key_prefix}:stats"

    async def _ensure_connected(self) -> None:
        """Verify Redis connection is available."""
        if self._redis is None:
            raise StorageConnectionError("Redis client not configured")

        try:
            await self._redis.ping()
        except Exception as e:
            raise StorageConnectionError(f"Redis connection failed: {e}")

    async def save(self, checkpoint: HybridCheckpoint) -> str:
        """
        Save checkpoint to Redis.

        Args:
            checkpoint: Checkpoint to save

        Returns:
            Checkpoint ID

        Raises:
            StorageError: If save operation fails
        """
        await self._ensure_connected()

        checkpoint_id = checkpoint.checkpoint_id
        session_id = checkpoint.session_id
        timestamp = checkpoint.created_at.timestamp()

        try:
            # Serialize checkpoint
            data = self._serialize(checkpoint)

            # Store checkpoint with TTL
            checkpoint_key = self._checkpoint_key(checkpoint_id)
            await self._redis.setex(
                checkpoint_key,
                self.config.ttl_seconds,
                data,
            )

            # Add to session index (sorted set by timestamp)
            session_key = self._session_key(session_id)
            await self._redis.zadd(session_key, {checkpoint_id: timestamp})
            await self._redis.expire(session_key, self.config.ttl_seconds)

            # Update statistics
            await self._redis.hincrby(self._stats_key(), "total_saves", 1)

            # Enforce retention limits
            await self.enforce_retention(session_id)

            return checkpoint_id

        except Exception as e:
            raise StorageError(f"Failed to save checkpoint: {e}")

    async def load(self, checkpoint_id: str) -> Optional[HybridCheckpoint]:
        """
        Load checkpoint from Redis.

        Args:
            checkpoint_id: ID of checkpoint to load

        Returns:
            HybridCheckpoint if found, None otherwise
        """
        await self._ensure_connected()

        try:
            checkpoint_key = self._checkpoint_key(checkpoint_id)
            data = await self._redis.get(checkpoint_key)

            if data is None:
                return None

            checkpoint = self._deserialize(data)

            # Check if expired (Redis TTL should handle this, but double-check)
            if checkpoint.is_expired():
                await self.delete(checkpoint_id)
                return None

            return checkpoint

        except Exception as e:
            raise StorageError(f"Failed to load checkpoint: {e}")

    async def delete(self, checkpoint_id: str) -> bool:
        """
        Delete checkpoint from Redis.

        Args:
            checkpoint_id: ID of checkpoint to delete

        Returns:
            True if deleted, False if not found
        """
        await self._ensure_connected()

        try:
            # Get checkpoint to find session_id
            checkpoint = await self.load(checkpoint_id)
            if checkpoint is None:
                # Try to delete anyway in case load failed
                deleted = await self._redis.delete(self._checkpoint_key(checkpoint_id))
                return deleted > 0

            session_id = checkpoint.session_id

            # Delete checkpoint data
            checkpoint_key = self._checkpoint_key(checkpoint_id)
            deleted = await self._redis.delete(checkpoint_key)

            # Remove from session index
            session_key = self._session_key(session_id)
            await self._redis.zrem(session_key, checkpoint_id)

            return deleted > 0

        except Exception as e:
            raise StorageError(f"Failed to delete checkpoint: {e}")

    async def exists(self, checkpoint_id: str) -> bool:
        """
        Check if checkpoint exists in Redis.

        Args:
            checkpoint_id: ID of checkpoint to check

        Returns:
            True if exists, False otherwise
        """
        await self._ensure_connected()

        try:
            checkpoint_key = self._checkpoint_key(checkpoint_id)
            return await self._redis.exists(checkpoint_key) > 0
        except Exception as e:
            raise StorageError(f"Failed to check checkpoint existence: {e}")

    async def query(self, query: CheckpointQuery) -> List[HybridCheckpoint]:
        """
        Query checkpoints based on criteria.

        For session-specific queries, uses the session index for efficiency.
        For general queries, scans all checkpoints (less efficient).

        Args:
            query: Query parameters

        Returns:
            List of matching checkpoints
        """
        await self._ensure_connected()

        try:
            results: List[HybridCheckpoint] = []

            if query.session_id:
                # Use session index for efficient lookup
                session_key = self._session_key(query.session_id)

                # Get checkpoint IDs from sorted set
                if query.ascending:
                    checkpoint_ids = await self._redis.zrange(
                        session_key, 0, -1
                    )
                else:
                    checkpoint_ids = await self._redis.zrevrange(
                        session_key, 0, -1
                    )

                # Load each checkpoint
                for cid_bytes in checkpoint_ids:
                    cid = cid_bytes.decode() if isinstance(cid_bytes, bytes) else cid_bytes
                    checkpoint = await self.load(cid)
                    if checkpoint:
                        results.append(checkpoint)
            else:
                # Scan all checkpoints (less efficient)
                pattern = f"{self._key_prefix}:data:*"
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(
                        cursor=cursor, match=pattern, count=100
                    )
                    for key in keys:
                        data = await self._redis.get(key)
                        if data:
                            checkpoint = self._deserialize(data)
                            if not checkpoint.is_expired():
                                results.append(checkpoint)
                    if cursor == 0:
                        break

            # Apply additional filters
            filtered = []
            for checkpoint in results:
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

                filtered.append(checkpoint)

            # Sort results
            if query.order_by == "created_at":
                filtered.sort(key=lambda c: c.created_at, reverse=not query.ascending)
            elif query.order_by == "updated_at":
                filtered.sort(key=lambda c: c.updated_at, reverse=not query.ascending)

            # Apply pagination
            start = query.offset
            end = start + query.limit if query.limit > 0 else None

            return filtered[start:end]

        except Exception as e:
            raise StorageError(f"Failed to query checkpoints: {e}")

    async def get_stats(self) -> StorageStats:
        """
        Get storage statistics.

        Returns:
            StorageStats with current statistics
        """
        await self._ensure_connected()

        try:
            # Count checkpoints
            pattern = f"{self._key_prefix}:data:*"
            total = 0
            active = 0
            expired = 0
            total_size = 0
            oldest: Optional[datetime] = None
            newest: Optional[datetime] = None

            cursor = 0
            while True:
                cursor, keys = await self._redis.scan(
                    cursor=cursor, match=pattern, count=100
                )
                for key in keys:
                    total += 1
                    data = await self._redis.get(key)
                    if data:
                        total_size += len(data)
                        checkpoint = self._deserialize(data)
                        if checkpoint.is_expired():
                            expired += 1
                        else:
                            active += 1

                        if oldest is None or checkpoint.created_at < oldest:
                            oldest = checkpoint.created_at
                        if newest is None or checkpoint.created_at > newest:
                            newest = checkpoint.created_at

                if cursor == 0:
                    break

            # Count sessions
            session_pattern = f"{self._key_prefix}:session:*"
            sessions_count = 0
            cursor = 0
            while True:
                cursor, keys = await self._redis.scan(
                    cursor=cursor, match=session_pattern, count=100
                )
                sessions_count += len(keys)
                if cursor == 0:
                    break

            return StorageStats(
                total_checkpoints=total,
                active_checkpoints=active,
                expired_checkpoints=expired,
                total_size_bytes=total_size,
                sessions_count=sessions_count,
                oldest_checkpoint=oldest,
                newest_checkpoint=newest,
            )

        except Exception as e:
            raise StorageError(f"Failed to get storage stats: {e}")

    async def cleanup_expired(self) -> int:
        """
        Remove expired checkpoints.

        Note: Redis TTL handles most expiration automatically.
        This method cleans up session indexes for expired checkpoints.

        Returns:
            Number of checkpoints cleaned up
        """
        await self._ensure_connected()

        try:
            removed = 0

            # Scan all session indexes
            session_pattern = f"{self._key_prefix}:session:*"
            cursor = 0
            while True:
                cursor, keys = await self._redis.scan(
                    cursor=cursor, match=session_pattern, count=100
                )

                for session_key in keys:
                    # Get all checkpoint IDs in session
                    checkpoint_ids = await self._redis.zrange(session_key, 0, -1)

                    for cid_bytes in checkpoint_ids:
                        cid = cid_bytes.decode() if isinstance(cid_bytes, bytes) else cid_bytes
                        checkpoint_key = self._checkpoint_key(cid)

                        # Check if checkpoint data still exists
                        if not await self._redis.exists(checkpoint_key):
                            # Remove from session index
                            await self._redis.zrem(session_key, cid)
                            removed += 1

                if cursor == 0:
                    break

            return removed

        except Exception as e:
            raise StorageError(f"Failed to cleanup expired checkpoints: {e}")

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
