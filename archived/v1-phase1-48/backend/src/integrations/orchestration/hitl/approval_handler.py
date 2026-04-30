"""
Approval Handler Implementation

Handles approval operations and integrates with Redis for state persistence.
Provides high-level approval operations with history tracking.

Sprint 97: Story 97-2 - Implement ApprovalHandler (Phase 28)
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from .controller import (
    ApprovalEvent,
    ApprovalRequest,
    ApprovalStatus,
    ApprovalStorage,
    ApprovalType,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Redis Storage Implementation
# =============================================================================


class RedisApprovalStorage:
    """
    Redis-based storage for approval requests.

    Provides persistent storage with TTL-based expiration.

    Key Formats:
        - approval:{request_id} -> ApprovalRequest JSON
        - approval_history:{request_id} -> List[ApprovalEvent] JSON
        - approval_pending -> Set of pending request IDs

    TTL Settings:
        - Pending requests: 30 minutes (configurable)
        - Completed requests: 7 days (for audit)
    """

    DEFAULT_PENDING_TTL = 30 * 60  # 30 minutes
    DEFAULT_COMPLETED_TTL = 7 * 24 * 60 * 60  # 7 days

    def __init__(
        self,
        redis_client: Any,  # redis.Redis or aioredis.Redis
        key_prefix: str = "approval",
        pending_ttl: int = DEFAULT_PENDING_TTL,
        completed_ttl: int = DEFAULT_COMPLETED_TTL,
    ):
        """
        Initialize Redis storage.

        Args:
            redis_client: Redis client instance
            key_prefix: Prefix for all keys
            pending_ttl: TTL for pending requests in seconds
            completed_ttl: TTL for completed requests in seconds
        """
        self.redis = redis_client
        self.key_prefix = key_prefix
        self.pending_ttl = pending_ttl
        self.completed_ttl = completed_ttl

    def _request_key(self, request_id: str) -> str:
        """Generate key for approval request."""
        return f"{self.key_prefix}:{request_id}"

    def _history_key(self, request_id: str) -> str:
        """Generate key for approval history."""
        return f"{self.key_prefix}_history:{request_id}"

    def _pending_set_key(self) -> str:
        """Generate key for pending requests set."""
        return f"{self.key_prefix}_pending"

    async def save(self, request: ApprovalRequest) -> None:
        """
        Save an approval request to Redis.

        Args:
            request: ApprovalRequest to save
        """
        key = self._request_key(request.request_id)
        data = json.dumps(request.to_dict())

        # Determine TTL based on status
        ttl = self.pending_ttl if request.status == ApprovalStatus.PENDING else self.completed_ttl

        # Save request
        await self.redis.setex(key, ttl, data)

        # Add to pending set if pending
        if request.status == ApprovalStatus.PENDING:
            await self.redis.sadd(self._pending_set_key(), request.request_id)
        else:
            await self.redis.srem(self._pending_set_key(), request.request_id)

        # Save history separately
        history_key = self._history_key(request.request_id)
        history_data = json.dumps([e.to_dict() for e in request.history])
        await self.redis.setex(history_key, self.completed_ttl, history_data)

        logger.debug(f"Saved approval request to Redis: {request.request_id}")

    async def get(self, request_id: str) -> Optional[ApprovalRequest]:
        """
        Get an approval request from Redis.

        Args:
            request_id: Request ID to retrieve

        Returns:
            ApprovalRequest or None if not found
        """
        key = self._request_key(request_id)
        data = await self.redis.get(key)

        if not data:
            return None

        try:
            request_dict = json.loads(data)
            return self._dict_to_request(request_dict)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to deserialize approval request: {e}")
            return None

    async def update(self, request: ApprovalRequest) -> None:
        """
        Update an existing approval request.

        Args:
            request: ApprovalRequest to update
        """
        await self.save(request)

    async def delete(self, request_id: str) -> None:
        """
        Delete an approval request.

        Args:
            request_id: Request ID to delete
        """
        key = self._request_key(request_id)
        history_key = self._history_key(request_id)

        await self.redis.delete(key, history_key)
        await self.redis.srem(self._pending_set_key(), request_id)

        logger.debug(f"Deleted approval request from Redis: {request_id}")

    async def list_pending(self) -> List[ApprovalRequest]:
        """
        List all pending approval requests.

        Returns:
            List of pending ApprovalRequest objects
        """
        pending_ids = await self.redis.smembers(self._pending_set_key())
        requests = []

        for request_id in pending_ids:
            request = await self.get(request_id.decode() if isinstance(request_id, bytes) else request_id)
            if request and request.status == ApprovalStatus.PENDING:
                requests.append(request)
            elif request is None:
                # Clean up stale ID
                await self.redis.srem(self._pending_set_key(), request_id)

        return requests

    async def get_history(self, request_id: str) -> List[ApprovalEvent]:
        """
        Get approval history for a request.

        Args:
            request_id: Request ID

        Returns:
            List of ApprovalEvent objects
        """
        history_key = self._history_key(request_id)
        data = await self.redis.get(history_key)

        if not data:
            return []

        try:
            events_data = json.loads(data)
            return [self._dict_to_event(e) for e in events_data]
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to deserialize approval history: {e}")
            return []

    def _dict_to_request(self, data: Dict[str, Any]) -> ApprovalRequest:
        """Convert dictionary to ApprovalRequest."""
        from ..intent_router.models import RoutingDecision
        from ..risk_assessor.assessor import RiskAssessment

        # Parse nested objects
        routing_decision = RoutingDecision.from_dict(data["routing_decision"])
        risk_assessment = self._dict_to_risk_assessment(data["risk_assessment"])

        # Parse history
        history = [self._dict_to_event(e) for e in data.get("history", [])]

        return ApprovalRequest(
            request_id=data["request_id"],
            routing_decision=routing_decision,
            risk_assessment=risk_assessment,
            requester=data["requester"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            status=ApprovalStatus(data["status"]),
            approval_type=ApprovalType(data["approval_type"]),
            approvers=data.get("approvers", []),
            approved_by=data.get("approved_by"),
            approved_at=datetime.fromisoformat(data["approved_at"]) if data.get("approved_at") else None,
            rejected_by=data.get("rejected_by"),
            rejected_at=datetime.fromisoformat(data["rejected_at"]) if data.get("rejected_at") else None,
            comment=data.get("comment"),
            history=history,
            metadata=data.get("metadata", {}),
        )

    def _dict_to_event(self, data: Dict[str, Any]) -> ApprovalEvent:
        """Convert dictionary to ApprovalEvent."""
        return ApprovalEvent(
            event_type=data["event_type"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            actor=data.get("actor", "system"),
            comment=data.get("comment"),
            metadata=data.get("metadata", {}),
        )

    def _dict_to_risk_assessment(self, data: Dict[str, Any]) -> "RiskAssessment":
        """Convert dictionary to RiskAssessment."""
        from ..risk_assessor.assessor import RiskAssessment, RiskFactor
        from ..intent_router.models import RiskLevel

        factors = [
            RiskFactor(
                name=f["name"],
                description=f["description"],
                weight=f.get("weight", 0.0),
                value=f.get("value"),
                impact=f.get("impact", "neutral"),
            )
            for f in data.get("factors", [])
        ]

        return RiskAssessment(
            level=RiskLevel(data["level"]),
            score=data.get("score", 0.0),
            requires_approval=data.get("requires_approval", False),
            approval_type=data.get("approval_type", "none"),
            factors=factors,
            reasoning=data.get("reasoning", ""),
            policy_id=data.get("policy_id"),
            adjustments_applied=data.get("adjustments_applied", []),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.utcnow(),
        )


# =============================================================================
# Approval Handler
# =============================================================================


@dataclass
class ApprovalResult:
    """
    Result of an approval operation.

    Attributes:
        success: Whether the operation succeeded
        request: Updated ApprovalRequest
        message: Human-readable message
        error: Error message if failed
    """

    success: bool
    request: Optional[ApprovalRequest] = None
    message: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "request": self.request.to_dict() if self.request else None,
            "message": self.message,
            "error": self.error,
        }


class ApprovalHandler:
    """
    High-level handler for approval operations.

    Provides simplified approve/reject operations with:
    - Input validation
    - Audit logging
    - Result formatting
    - Error handling

    Example:
        >>> storage = RedisApprovalStorage(redis_client)
        >>> handler = ApprovalHandler(storage)
        >>> result = await handler.approve(
        ...     request_id="abc-123",
        ...     approver="admin@example.com",
        ...     comment="Approved for production deployment",
        ... )
        >>> if result.success:
        ...     print(f"Approved: {result.request.request_id}")
    """

    def __init__(
        self,
        storage: ApprovalStorage,
        audit_logger: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ):
        """
        Initialize approval handler.

        Args:
            storage: Storage backend for approval requests
            audit_logger: Optional callback for audit logging
        """
        self.storage = storage
        self.audit_logger = audit_logger or self._default_audit_logger

    async def approve(
        self,
        request_id: str,
        approver: str,
        comment: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ApprovalResult:
        """
        Approve a pending request.

        Args:
            request_id: Request ID to approve
            approver: User approving the request
            comment: Optional approval comment
            metadata: Optional additional metadata

        Returns:
            ApprovalResult with success status and updated request
        """
        # Validate inputs
        if not request_id or not approver:
            return ApprovalResult(
                success=False,
                error="request_id and approver are required",
            )

        try:
            # Get request
            request = await self.storage.get(request_id)
            if not request:
                return ApprovalResult(
                    success=False,
                    error=f"Approval request not found: {request_id}",
                )

            # Validate status
            if request.status != ApprovalStatus.PENDING:
                return ApprovalResult(
                    success=False,
                    request=request,
                    error=f"Request is not pending (status: {request.status.value})",
                )

            # Check expiration
            if request.is_expired():
                request.status = ApprovalStatus.EXPIRED
                request.history.append(
                    ApprovalEvent(
                        event_type="expired",
                        actor="system",
                        comment="Request expired before approval",
                    )
                )
                await self.storage.update(request)
                return ApprovalResult(
                    success=False,
                    request=request,
                    error="Request has expired",
                )

            # Check approver authorization
            if request.approvers and approver not in request.approvers:
                return ApprovalResult(
                    success=False,
                    request=request,
                    error=f"User {approver} is not authorized to approve this request",
                )

            # Approve
            now = datetime.utcnow()
            request.status = ApprovalStatus.APPROVED
            request.approved_by = approver
            request.approved_at = now
            request.comment = comment

            event_metadata = metadata or {}
            request.history.append(
                ApprovalEvent(
                    event_type="approved",
                    timestamp=now,
                    actor=approver,
                    comment=comment or "Request approved",
                    metadata=event_metadata,
                )
            )

            await self.storage.update(request)

            # Audit log
            self.audit_logger(
                "approval_approved",
                {
                    "request_id": request_id,
                    "approver": approver,
                    "comment": comment,
                    "intent_category": request.routing_decision.intent_category.value,
                    "sub_intent": request.routing_decision.sub_intent,
                    "risk_level": request.risk_assessment.level.value,
                },
            )

            return ApprovalResult(
                success=True,
                request=request,
                message=f"Request {request_id} approved by {approver}",
            )

        except Exception as e:
            logger.error(f"Error approving request {request_id}: {e}")
            return ApprovalResult(
                success=False,
                error=str(e),
            )

    async def reject(
        self,
        request_id: str,
        rejector: str,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ApprovalResult:
        """
        Reject a pending request.

        Args:
            request_id: Request ID to reject
            rejector: User rejecting the request
            reason: Optional rejection reason
            metadata: Optional additional metadata

        Returns:
            ApprovalResult with success status and updated request
        """
        # Validate inputs
        if not request_id or not rejector:
            return ApprovalResult(
                success=False,
                error="request_id and rejector are required",
            )

        try:
            # Get request
            request = await self.storage.get(request_id)
            if not request:
                return ApprovalResult(
                    success=False,
                    error=f"Approval request not found: {request_id}",
                )

            # Validate status
            if request.status != ApprovalStatus.PENDING:
                return ApprovalResult(
                    success=False,
                    request=request,
                    error=f"Request is not pending (status: {request.status.value})",
                )

            # Check expiration
            if request.is_expired():
                request.status = ApprovalStatus.EXPIRED
                request.history.append(
                    ApprovalEvent(
                        event_type="expired",
                        actor="system",
                        comment="Request expired before rejection",
                    )
                )
                await self.storage.update(request)
                return ApprovalResult(
                    success=False,
                    request=request,
                    error="Request has expired",
                )

            # Reject
            now = datetime.utcnow()
            request.status = ApprovalStatus.REJECTED
            request.rejected_by = rejector
            request.rejected_at = now
            request.comment = reason

            event_metadata = metadata or {}
            request.history.append(
                ApprovalEvent(
                    event_type="rejected",
                    timestamp=now,
                    actor=rejector,
                    comment=reason or "Request rejected",
                    metadata=event_metadata,
                )
            )

            await self.storage.update(request)

            # Audit log
            self.audit_logger(
                "approval_rejected",
                {
                    "request_id": request_id,
                    "rejector": rejector,
                    "reason": reason,
                    "intent_category": request.routing_decision.intent_category.value,
                    "sub_intent": request.routing_decision.sub_intent,
                    "risk_level": request.risk_assessment.level.value,
                },
            )

            return ApprovalResult(
                success=True,
                request=request,
                message=f"Request {request_id} rejected by {rejector}",
            )

        except Exception as e:
            logger.error(f"Error rejecting request {request_id}: {e}")
            return ApprovalResult(
                success=False,
                error=str(e),
            )

    async def get_request_status(self, request_id: str) -> ApprovalResult:
        """
        Get the current status of a request.

        Args:
            request_id: Request ID to check

        Returns:
            ApprovalResult with current request state
        """
        try:
            request = await self.storage.get(request_id)
            if not request:
                return ApprovalResult(
                    success=False,
                    error=f"Approval request not found: {request_id}",
                )

            # Check for expiration
            if request.status == ApprovalStatus.PENDING and request.is_expired():
                request.status = ApprovalStatus.EXPIRED
                request.history.append(
                    ApprovalEvent(
                        event_type="expired",
                        actor="system",
                        comment="Request expired",
                    )
                )
                await self.storage.update(request)

            return ApprovalResult(
                success=True,
                request=request,
                message=f"Request status: {request.status.value}",
            )

        except Exception as e:
            logger.error(f"Error getting request status {request_id}: {e}")
            return ApprovalResult(
                success=False,
                error=str(e),
            )

    async def get_history(self, request_id: str) -> List[ApprovalEvent]:
        """
        Get approval history for a request.

        Args:
            request_id: Request ID

        Returns:
            List of ApprovalEvent objects
        """
        request = await self.storage.get(request_id)
        if not request:
            return []
        return request.history

    async def list_pending_by_approver(self, approver: str) -> List[ApprovalRequest]:
        """
        List pending requests that a specific user can approve.

        Args:
            approver: User identifier

        Returns:
            List of pending ApprovalRequest objects
        """
        all_pending = await self.storage.list_pending()
        return [
            r for r in all_pending
            if not r.approvers or approver in r.approvers
        ]

    def _default_audit_logger(self, event_type: str, data: Dict[str, Any]) -> None:
        """Default audit logger using standard logging."""
        logger.info(f"AUDIT [{event_type}]: {json.dumps(data)}")


# =============================================================================
# Factory Functions
# =============================================================================


def create_approval_handler(
    storage: ApprovalStorage,
    audit_logger: Optional[Callable[[str, Dict[str, Any]], None]] = None,
) -> ApprovalHandler:
    """
    Factory function to create an ApprovalHandler.

    Args:
        storage: Storage backend
        audit_logger: Optional audit logger callback

    Returns:
        ApprovalHandler instance
    """
    return ApprovalHandler(storage=storage, audit_logger=audit_logger)


def create_redis_storage(
    redis_client: Any,
    key_prefix: str = "approval",
) -> RedisApprovalStorage:
    """
    Factory function to create Redis storage.

    Args:
        redis_client: Redis client instance
        key_prefix: Key prefix for storage

    Returns:
        RedisApprovalStorage instance
    """
    return RedisApprovalStorage(redis_client=redis_client, key_prefix=key_prefix)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Storage
    "RedisApprovalStorage",
    # Handler
    "ApprovalResult",
    "ApprovalHandler",
    # Factory functions
    "create_approval_handler",
    "create_redis_storage",
]
