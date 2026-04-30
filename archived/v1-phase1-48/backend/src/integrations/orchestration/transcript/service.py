# =============================================================================
# IPA Platform - Transcript Service
# =============================================================================
# Append-only execution transcript using Redis Streams.
# Each orchestrator session gets its own stream, each subagent gets a sidechain.
#
# Key structure (multi-tenant):
#   ipa:{user_id}:transcript:{session_id}                    — main pipeline
#   ipa:{user_id}:transcript:{session_id}:agent:{agent_name} — subagent sidechain
#
# Inspired by Claude Code's JSONL transcript persistence,
# adapted for server-side Redis Streams with multi-user isolation.
# =============================================================================

import logging
from typing import Optional

import redis.asyncio as aioredis

from .models import TranscriptEntry, AgentSidechainEntry

logger = logging.getLogger(__name__)

_TTL_SECONDS = 86400 * 7  # 7 days


class TranscriptService:
    """Manages append-only execution transcripts via Redis Streams."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        ttl_seconds: int = _TTL_SECONDS,
    ):
        self._redis_url = redis_url
        self._ttl = ttl_seconds
        self._redis: Optional[aioredis.Redis] = None

    async def initialize(self) -> None:
        if self._redis is None:
            self._redis = aioredis.from_url(
                self._redis_url, decode_responses=True
            )
            await self._redis.ping()
            logger.info("TranscriptService: connected to Redis")

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    def _ensure_connected(self) -> aioredis.Redis:
        if self._redis is None:
            raise RuntimeError("TranscriptService not initialized.")
        return self._redis

    def _stream_key(self, user_id: str, session_id: str) -> str:
        return f"ipa:{user_id}:transcript:{session_id}"

    def _agent_stream_key(
        self, user_id: str, session_id: str, agent_name: str
    ) -> str:
        return f"ipa:{user_id}:transcript:{session_id}:agent:{agent_name}"

    # ── Main Pipeline Transcript ──────────────────────────────────────

    async def append(self, entry: TranscriptEntry) -> str:
        """Append a step entry to the session transcript. Returns stream entry ID."""
        r = self._ensure_connected()
        key = self._stream_key(entry.user_id, entry.session_id)

        entry_id = await r.xadd(key, entry.to_stream_dict())
        await r.expire(key, self._ttl)

        logger.debug(
            f"Transcript append: {entry.step_name} "
            f"(session={entry.session_id[:12]}, user={entry.user_id})"
        )
        return entry_id

    async def read(
        self,
        user_id: str,
        session_id: str,
        after_id: str = "0",
        limit: int = 100,
    ) -> list[TranscriptEntry]:
        """Read transcript entries from a session stream."""
        r = self._ensure_connected()
        key = self._stream_key(user_id, session_id)

        raw = await r.xrange(key, min=after_id, count=limit)
        return [
            TranscriptEntry.from_stream_dict(eid, data)
            for eid, data in raw
        ]

    async def get_last_step(
        self, user_id: str, session_id: str
    ) -> Optional[TranscriptEntry]:
        """Get the most recent transcript entry (for interruption detection)."""
        r = self._ensure_connected()
        key = self._stream_key(user_id, session_id)

        raw = await r.xrevrange(key, count=1)
        if not raw:
            return None
        eid, data = raw[0]
        return TranscriptEntry.from_stream_dict(eid, data)

    async def count(self, user_id: str, session_id: str) -> int:
        """Get number of entries in a session transcript."""
        r = self._ensure_connected()
        key = self._stream_key(user_id, session_id)
        return await r.xlen(key)

    # ── Subagent Sidechain ────────────────────────────────────────────

    async def append_agent(self, entry: AgentSidechainEntry) -> str:
        """Append an event to a subagent's sidechain transcript."""
        r = self._ensure_connected()
        key = self._agent_stream_key(
            entry.user_id, entry.session_id, entry.agent_name
        )

        entry_id = await r.xadd(key, entry.to_stream_dict())
        await r.expire(key, self._ttl)

        logger.debug(
            f"Agent sidechain append: {entry.agent_name}/{entry.event_type} "
            f"(session={entry.session_id[:12]})"
        )
        return entry_id

    async def read_agent(
        self,
        user_id: str,
        session_id: str,
        agent_name: str,
        after_id: str = "0",
        limit: int = 100,
    ) -> list[AgentSidechainEntry]:
        """Read a subagent's sidechain transcript."""
        r = self._ensure_connected()
        key = self._agent_stream_key(user_id, session_id, agent_name)

        raw = await r.xrange(key, min=after_id, count=limit)
        return [
            AgentSidechainEntry.from_stream_dict(eid, data)
            for eid, data in raw
        ]

    async def list_agent_streams(
        self, user_id: str, session_id: str
    ) -> list[str]:
        """List all subagent names that have sidechain transcripts."""
        r = self._ensure_connected()
        prefix = self._agent_stream_key(user_id, session_id, "")
        # prefix = ipa:{user_id}:transcript:{session_id}:agent:

        agent_names = []
        async for key in r.scan_iter(match=f"{prefix}*", count=50):
            # Extract agent name from key suffix
            name = key.replace(prefix, "")
            if name:
                agent_names.append(name)
        return agent_names

    # ── Session Detection ─────────────────────────────────────────────

    async def detect_interruption(
        self, user_id: str, session_id: str
    ) -> dict:
        """Detect where execution stopped. Returns status and resumable info.

        Inspired by Claude Code's detectTurnInterruption() which checks
        the last message type to determine if execution was interrupted.
        """
        last = await self.get_last_step(user_id, session_id)
        if last is None:
            return {"status": "no_transcript", "last_step": None}

        if last.entry_type == "step_error":
            return {
                "status": "error",
                "last_step": last.step_name,
                "step_index": last.step_index,
                "error": last.output_summary.get("error", "unknown"),
            }

        if last.entry_type == "approval_required":
            return {
                "status": "pending_approval",
                "last_step": last.step_name,
                "step_index": last.step_index,
                "checkpoint_id": last.checkpoint_id,
            }

        total = await self.count(user_id, session_id)
        expected_steps = 7  # orchestrator has 7 steps

        if total < expected_steps:
            return {
                "status": "interrupted",
                "last_step": last.step_name,
                "step_index": last.step_index,
                "completed_steps": total,
                "checkpoint_id": last.checkpoint_id,
            }

        return {
            "status": "complete",
            "last_step": last.step_name,
            "completed_steps": total,
        }
