# =============================================================================
# IPA Platform - Approval Service (Lightweight PoC)
# =============================================================================
# Redis-backed approval request management for HITL flow.
# Supports: create, list pending, approve, reject, get by ID.
#
# Key structure:
#   ipa:{user_id}:approval:{approval_id}   — approval request JSON
#   ipa:approvals:pending                   — SET of pending approval IDs
#
# TTL: 7 days (matching checkpoint TTL)
# =============================================================================

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_TTL_SECONDS = 86400 * 7  # 7 days


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class ApprovalRequest:
    """A HITL approval request tied to a checkpoint."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    session_id: str = ""
    checkpoint_id: str = ""
    task: str = ""
    risk_level: str = ""
    intent_category: str = ""
    confidence: float = 0.0
    status: str = ApprovalStatus.PENDING.value
    context_summary: dict = field(default_factory=dict)  # memory, knowledge, intent
    decided_by: Optional[str] = None
    decided_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ApprovalRequest":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ApprovalService:
    """Manages HITL approval requests via Redis."""

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

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    def _ensure_connected(self) -> aioredis.Redis:
        if self._redis is None:
            raise RuntimeError("ApprovalService not initialized.")
        return self._redis

    def _key(self, user_id: str, approval_id: str) -> str:
        return f"ipa:{user_id}:approval:{approval_id}"

    # ── Create ────────────────────────────────────────────────────────

    async def create(self, request: ApprovalRequest) -> str:
        """Create a new approval request. Returns approval_id."""
        r = self._ensure_connected()

        key = self._key(request.user_id, request.id)
        pipe = r.pipeline()
        pipe.set(key, json.dumps(request.to_dict(), default=str), ex=self._ttl)
        pipe.sadd("ipa:approvals:pending", f"{request.user_id}:{request.id}")
        await pipe.execute()

        logger.info(
            f"Approval created: {request.id[:12]}... "
            f"(user={request.user_id}, risk={request.risk_level})"
        )
        return request.id

    # ── Get ───────────────────────────────────────────────────────────

    async def get(self, user_id: str, approval_id: str) -> Optional[ApprovalRequest]:
        """Get an approval request by ID."""
        r = self._ensure_connected()
        data = await r.get(self._key(user_id, approval_id))
        if not data:
            return None
        return ApprovalRequest.from_dict(json.loads(data))

    # ── List Pending ──────────────────────────────────────────────────

    async def list_pending(self) -> list[ApprovalRequest]:
        """List all pending approval requests (across all users)."""
        r = self._ensure_connected()
        pending_ids = await r.smembers("ipa:approvals:pending")
        results = []
        for composite_id in pending_ids:
            parts = composite_id.split(":", 1)
            if len(parts) != 2:
                continue
            uid, aid = parts
            req = await self.get(uid, aid)
            if req and req.status == ApprovalStatus.PENDING.value:
                results.append(req)
            elif req and req.status != ApprovalStatus.PENDING.value:
                # Clean up stale entry
                await r.srem("ipa:approvals:pending", composite_id)
        return sorted(results, key=lambda x: x.created_at, reverse=True)

    # ── Decide (Approve / Reject) ─────────────────────────────────────

    async def decide(
        self,
        user_id: str,
        approval_id: str,
        status: ApprovalStatus,
        decided_by: str = "manager",
        reason: Optional[str] = None,
    ) -> Optional[ApprovalRequest]:
        """Approve or reject a request. Returns updated request."""
        r = self._ensure_connected()

        req = await self.get(user_id, approval_id)
        if not req:
            return None

        if req.status != ApprovalStatus.PENDING.value:
            logger.warning(f"Approval {approval_id[:12]} already decided: {req.status}")
            return req

        req.status = status.value
        req.decided_by = decided_by
        req.decided_at = datetime.now(timezone.utc).isoformat()
        if reason:
            req.rejection_reason = reason

        # Update in Redis
        key = self._key(user_id, approval_id)
        pipe = r.pipeline()
        pipe.set(key, json.dumps(req.to_dict(), default=str), ex=self._ttl)
        pipe.srem("ipa:approvals:pending", f"{user_id}:{approval_id}")
        await pipe.execute()

        logger.info(
            f"Approval {approval_id[:12]} → {status.value} "
            f"(by={decided_by}, user={user_id})"
        )
        return req
