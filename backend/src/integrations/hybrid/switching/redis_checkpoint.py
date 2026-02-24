"""Redis-backed checkpoint storage for ModeSwitcher.

Sprint 120 -- Story 120-1: Replace InMemoryCheckpointStorage with Redis.

Provides persistent, distributed checkpoint storage with TTL-based expiration.
Uses a secondary index (Redis Set per session) to support session-based lookups.

Key Formats:
    - switch_checkpoint:{checkpoint_id}         -> SwitchCheckpoint JSON
    - switch_checkpoint:session:{session_id}    -> Set of checkpoint_ids

Usage:
    from src.integrations.hybrid.switching.redis_checkpoint import (
        RedisSwitchCheckpointStorage,
    )

    storage = RedisSwitchCheckpointStorage(redis_client=redis)
    await storage.save_checkpoint(checkpoint)
    cp = await storage.get_checkpoint(checkpoint_id)
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis

from .models import SwitchCheckpoint

logger = logging.getLogger(__name__)


class RedisSwitchCheckpointStorage:
    """Redis implementation of CheckpointStorageProtocol for ModeSwitcher.

    Replaces InMemoryCheckpointStorage for production use.
    Stores SwitchCheckpoint as JSON with TTL-based expiration,
    and maintains a per-session index for session-scoped queries.

    Args:
        redis_client: Async Redis client instance.
        key_prefix: Prefix for all Redis keys.
        ttl_seconds: TTL for checkpoint data (default 24 hours).
    """

    DEFAULT_TTL = 86400  # 24 hours

    def __init__(
        self,
        redis_client: aioredis.Redis,
        key_prefix: str = "switch_checkpoint",
        ttl_seconds: int = DEFAULT_TTL,
    ) -> None:
        """Initialize Redis checkpoint storage.

        Args:
            redis_client: Async Redis client instance.
            key_prefix: Prefix for all Redis keys.
            ttl_seconds: TTL for checkpoint data in seconds.
        """
        self._redis = redis_client
        self._key_prefix = key_prefix
        self._ttl = ttl_seconds
        self._lock = asyncio.Lock()

    # -------------------------------------------------------------------------
    # Key helpers
    # -------------------------------------------------------------------------

    def _checkpoint_key(self, checkpoint_id: str) -> str:
        """Generate key for a single checkpoint."""
        return f"{self._key_prefix}:{checkpoint_id}"

    def _session_set_key(self, session_id: str) -> str:
        """Generate key for the per-session checkpoint index."""
        return f"{self._key_prefix}:session:{session_id}"

    # -------------------------------------------------------------------------
    # CheckpointStorageProtocol methods
    # -------------------------------------------------------------------------

    async def save_checkpoint(self, checkpoint: SwitchCheckpoint) -> str:
        """Save a checkpoint to Redis.

        Args:
            checkpoint: SwitchCheckpoint to persist.

        Returns:
            The checkpoint_id of the saved checkpoint.
        """
        key = self._checkpoint_key(checkpoint.checkpoint_id)
        data = json.dumps(checkpoint.to_dict(), default=str, ensure_ascii=False)

        try:
            async with self._lock:
                await self._redis.setex(key, self._ttl, data)

                # Maintain per-session index if session_id is present
                session_id = checkpoint.context_snapshot.get("session_id")
                if session_id:
                    session_key = self._session_set_key(session_id)
                    await self._redis.sadd(session_key, checkpoint.checkpoint_id)
                    await self._redis.expire(session_key, self._ttl)

            logger.debug(
                f"Saved switch checkpoint to Redis: {checkpoint.checkpoint_id}"
            )
        except aioredis.RedisError as e:
            logger.error(
                f"Redis error saving switch checkpoint "
                f"{checkpoint.checkpoint_id}: {e}"
            )
            raise

        return checkpoint.checkpoint_id

    async def get_checkpoint(
        self, checkpoint_id: str
    ) -> Optional[SwitchCheckpoint]:
        """Get a checkpoint by ID.

        Args:
            checkpoint_id: Unique checkpoint identifier.

        Returns:
            SwitchCheckpoint if found, None otherwise.
        """
        key = self._checkpoint_key(checkpoint_id)
        try:
            data = await self._redis.get(key)
            if data is None:
                return None
            return SwitchCheckpoint.from_dict(json.loads(data))
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(
                f"Failed to deserialize switch checkpoint "
                f"{checkpoint_id}: {e}"
            )
            return None
        except aioredis.RedisError as e:
            logger.error(
                f"Redis error getting switch checkpoint "
                f"{checkpoint_id}: {e}"
            )
            return None

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint.

        Also removes the checkpoint_id from any session index it belongs to.

        Args:
            checkpoint_id: Unique checkpoint identifier.

        Returns:
            True if the checkpoint was deleted, False if not found.
        """
        key = self._checkpoint_key(checkpoint_id)
        try:
            # Read first to clean up session index
            checkpoint = await self.get_checkpoint(checkpoint_id)

            async with self._lock:
                result = await self._redis.delete(key)

                if checkpoint is not None:
                    session_id = checkpoint.context_snapshot.get("session_id")
                    if session_id:
                        session_key = self._session_set_key(session_id)
                        await self._redis.srem(session_key, checkpoint_id)

            deleted = result > 0
            if deleted:
                logger.debug(
                    f"Deleted switch checkpoint from Redis: {checkpoint_id}"
                )
            return deleted
        except aioredis.RedisError as e:
            logger.error(
                f"Redis error deleting switch checkpoint "
                f"{checkpoint_id}: {e}"
            )
            return False

    # -------------------------------------------------------------------------
    # Extended methods (matching InMemoryCheckpointStorage interface)
    # -------------------------------------------------------------------------

    async def list_checkpoints(
        self, session_id: str
    ) -> List[SwitchCheckpoint]:
        """List all checkpoints for a session.

        Uses the per-session Redis Set index for efficient lookup.

        Args:
            session_id: Session identifier.

        Returns:
            List of SwitchCheckpoint objects for the session.
        """
        session_key = self._session_set_key(session_id)
        try:
            checkpoint_ids = await self._redis.smembers(session_key)
            checkpoints: List[SwitchCheckpoint] = []

            for cid in checkpoint_ids:
                cp = await self.get_checkpoint(cid)
                if cp is not None:
                    checkpoints.append(cp)
                else:
                    # Clean stale index entry
                    await self._redis.srem(session_key, cid)

            return checkpoints
        except aioredis.RedisError as e:
            logger.error(
                f"Redis error listing checkpoints for session "
                f"{session_id}: {e}"
            )
            return []

    async def get_latest_checkpoint(
        self, session_id: str
    ) -> Optional[SwitchCheckpoint]:
        """Get the most recent checkpoint for a session.

        Args:
            session_id: Session identifier.

        Returns:
            The most recent SwitchCheckpoint, or None if none exist.
        """
        checkpoints = await self.list_checkpoints(session_id)
        if not checkpoints:
            return None
        return max(checkpoints, key=lambda cp: cp.created_at)

    async def clear(self) -> None:
        """Clear all checkpoints managed by this storage instance.

        Scans for keys matching the prefix and removes them.
        Intended for testing compatibility.
        """
        pattern = f"{self._key_prefix}:*"
        try:
            async for key in self._redis.scan_iter(
                match=pattern, count=100
            ):
                await self._redis.delete(key)
            logger.info(
                f"Cleared all switch checkpoints with prefix "
                f"'{self._key_prefix}'"
            )
        except aioredis.RedisError as e:
            logger.error(f"Redis error clearing switch checkpoints: {e}")


__all__ = [
    "RedisSwitchCheckpointStorage",
]
