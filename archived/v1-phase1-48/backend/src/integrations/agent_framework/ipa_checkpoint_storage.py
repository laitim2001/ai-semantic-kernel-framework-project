# =============================================================================
# IPA Checkpoint Storage (Redis-backed, Multi-Tenant)
# =============================================================================
# IPA Platform's own checkpoint storage using MAF-compatible data format
# (WorkflowCheckpoint + CheckpointStorage Protocol) for future interop,
# but checkpoint creation/resume logic is entirely IPA's own design.
#
# Multi-tenant: All keys prefixed with ipa:{user_id}:checkpoint:
# When user_id is not provided, falls back to shared namespace.
#
# Official Protocol methods (verified against installed agent_framework):
#   save(checkpoint) -> CheckpointID
#   load(checkpoint_id) -> WorkflowCheckpoint
#   get_latest(*, workflow_name) -> WorkflowCheckpoint | None
#   list_checkpoint_ids(*, workflow_name) -> list[CheckpointID]
#   list_checkpoints(*, workflow_name) -> list[WorkflowCheckpoint]
#   delete(checkpoint_id) -> bool
# =============================================================================

import json
import logging
from typing import Optional

import redis.asyncio as aioredis

from agent_framework import CheckpointStorage, WorkflowCheckpoint

logger = logging.getLogger(__name__)

_TTL_SECONDS = 86400 * 7  # 7 days default


class IPACheckpointStorage(CheckpointStorage):
    """
    Redis-backed CheckpointStorage implementing the official MAF Protocol.
    Supports multi-tenant isolation via user_id prefix.

    Usage:
        # Shared namespace (backward compatible)
        storage = IPACheckpointStorage(redis_url="redis://localhost:6379/0")

        # Per-user isolation
        storage = IPACheckpointStorage(
            redis_url="redis://localhost:6379/0",
            user_id="user-chris"
        )
        await storage.initialize()

        # Use with MAF Builder
        builder = HandoffBuilder(...).with_checkpointing(storage)

        # Or use directly
        cp_id = await storage.save(checkpoint)
        cp = await storage.load(cp_id)
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        ttl_seconds: int = _TTL_SECONDS,
        user_id: Optional[str] = None,
    ):
        self._redis_url = redis_url
        self._ttl = ttl_seconds
        self._user_id = user_id
        self._redis: Optional[aioredis.Redis] = None

        # Build key prefixes based on user_id
        if user_id:
            self._data_key = f"ipa:{user_id}:checkpoint:data"
            self._workflow_key = f"ipa:{user_id}:checkpoint:workflow"
            self._latest_key = f"ipa:{user_id}:checkpoint:latest"
        else:
            self._data_key = "ipa:checkpoint:data"
            self._workflow_key = "ipa:checkpoint:workflow"
            self._latest_key = "ipa:checkpoint:latest"

    @property
    def user_id(self) -> Optional[str]:
        return self._user_id

    async def initialize(self) -> None:
        """Connect to Redis."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                self._redis_url, decode_responses=True
            )
            await self._redis.ping()
            logger.info(
                f"IPACheckpointStorage: connected "
                f"(user={self._user_id or 'shared'})"
            )

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    def _ensure_connected(self) -> aioredis.Redis:
        if self._redis is None:
            raise RuntimeError("Not initialized. Call initialize() first.")
        return self._redis

    # ── Official Protocol Methods ──────────────────────────────────────

    async def save(self, checkpoint: WorkflowCheckpoint) -> str:
        """Save a checkpoint and return its ID."""
        r = self._ensure_connected()

        data = checkpoint.to_dict()
        # Inject user_id into checkpoint metadata for traceability
        if self._user_id and "user_id" not in data.get("metadata", {}):
            data.setdefault("metadata", {})["user_id"] = self._user_id

        data_json = json.dumps(data, default=str)

        pipe = r.pipeline()
        pipe.hset(self._data_key, checkpoint.checkpoint_id, data_json)
        pipe.sadd(
            f"{self._workflow_key}:{checkpoint.workflow_name}",
            checkpoint.checkpoint_id,
        )
        pipe.hset(
            self._latest_key, checkpoint.workflow_name, checkpoint.checkpoint_id
        )
        pipe.expire(
            f"{self._workflow_key}:{checkpoint.workflow_name}", self._ttl
        )
        await pipe.execute()

        logger.info(
            f"IPA checkpoint saved: {checkpoint.checkpoint_id[:12]}... "
            f"(workflow={checkpoint.workflow_name}, user={self._user_id or 'shared'})"
        )
        return checkpoint.checkpoint_id

    async def load(self, checkpoint_id: str) -> WorkflowCheckpoint:
        """Load a checkpoint by ID. Raises KeyError if not found."""
        r = self._ensure_connected()

        data_json = await r.hget(self._data_key, checkpoint_id)
        if not data_json:
            raise KeyError(f"Checkpoint not found: {checkpoint_id}")

        data = json.loads(data_json)
        return WorkflowCheckpoint.from_dict(data)

    async def get_latest(
        self, *, workflow_name: str
    ) -> Optional[WorkflowCheckpoint]:
        """Get the most recent checkpoint for a workflow."""
        r = self._ensure_connected()

        latest_id = await r.hget(self._latest_key, workflow_name)
        if not latest_id:
            return None

        data_json = await r.hget(self._data_key, latest_id)
        if not data_json:
            return None

        return WorkflowCheckpoint.from_dict(json.loads(data_json))

    async def list_checkpoint_ids(
        self, *, workflow_name: str
    ) -> list[str]:
        """List checkpoint IDs for a specific workflow."""
        r = self._ensure_connected()
        return list(
            await r.smembers(f"{self._workflow_key}:{workflow_name}")
        )

    async def list_checkpoints(
        self, *, workflow_name: str
    ) -> list[WorkflowCheckpoint]:
        """List full checkpoint objects for a workflow."""
        ids = await self.list_checkpoint_ids(workflow_name=workflow_name)
        results = []
        for cp_id in ids:
            try:
                cp = await self.load(cp_id)
                results.append(cp)
            except KeyError:
                continue
        return results

    async def delete(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint. Returns True if it existed."""
        r = self._ensure_connected()

        data_json = await r.hget(self._data_key, checkpoint_id)
        if not data_json:
            return False

        data = json.loads(data_json)
        wf_name = data.get("workflow_name", "")

        pipe = r.pipeline()
        pipe.hdel(self._data_key, checkpoint_id)
        if wf_name:
            pipe.srem(f"{self._workflow_key}:{wf_name}", checkpoint_id)
        await pipe.execute()

        logger.info(f"IPA checkpoint deleted: {checkpoint_id[:12]}...")
        return True
