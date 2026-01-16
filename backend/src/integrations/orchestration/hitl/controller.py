"""
HITL (Human-in-the-Loop) Controller Implementation

Core controller for managing human approval workflows in high-risk operations.
Coordinates approval requests, status tracking, and result processing.

Sprint 97: Story 97-1 - Implement HITLController (Phase 28)
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol

from ..intent_router.models import RoutingDecision
from ..risk_assessor.assessor import RiskAssessment

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Data Classes
# =============================================================================


class ApprovalStatus(Enum):
    """
    Status of an approval request.

    States:
        PENDING: Waiting for approval decision
        APPROVED: Request has been approved
        REJECTED: Request has been rejected
        EXPIRED: Request timed out without decision
        CANCELLED: Request was cancelled by requester
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ApprovalType(Enum):
    """
    Type of approval required.

    Types:
        NONE: No approval required
        SINGLE: Single approver required
        MULTI: Multiple approvers required (quorum-based)
    """

    NONE = "none"
    SINGLE = "single"
    MULTI = "multi"


@dataclass
class ApprovalEvent:
    """
    Event in approval history.

    Attributes:
        event_type: Type of event (created, approved, rejected, expired, cancelled)
        timestamp: When the event occurred
        actor: Who triggered the event (system or user identifier)
        comment: Optional comment or reason
        metadata: Additional event metadata
    """

    event_type: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    actor: str = "system"
    comment: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "actor": self.actor,
            "comment": self.comment,
            "metadata": self.metadata,
        }


@dataclass
class ApprovalRequest:
    """
    Approval request data structure.

    Attributes:
        request_id: Unique identifier for the request
        routing_decision: The routing decision that triggered this request
        risk_assessment: Risk assessment for the operation
        requester: User or system that initiated the request
        created_at: When the request was created
        expires_at: When the request will expire
        status: Current approval status
        approval_type: Type of approval required
        approvers: List of users who can approve
        approved_by: User who approved (if approved)
        approved_at: When approval was granted
        rejected_by: User who rejected (if rejected)
        rejected_at: When rejection occurred
        comment: Approval/rejection comment
        history: List of approval events
        metadata: Additional request metadata
    """

    request_id: str
    routing_decision: RoutingDecision
    risk_assessment: RiskAssessment
    requester: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    status: ApprovalStatus = ApprovalStatus.PENDING
    approval_type: ApprovalType = ApprovalType.SINGLE
    approvers: List[str] = field(default_factory=list)
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    comment: Optional[str] = None
    history: List[ApprovalEvent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Add creation event to history."""
        if not self.history:
            self.history.append(
                ApprovalEvent(
                    event_type="created",
                    actor=self.requester,
                    comment="Approval request created",
                )
            )

    def is_expired(self) -> bool:
        """Check if request has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def is_terminal(self) -> bool:
        """Check if request is in a terminal state."""
        return self.status in (
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.EXPIRED,
            ApprovalStatus.CANCELLED,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "request_id": self.request_id,
            "routing_decision": self.routing_decision.to_dict(),
            "risk_assessment": self.risk_assessment.to_dict(),
            "requester": self.requester,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status.value,
            "approval_type": self.approval_type.value,
            "approvers": self.approvers,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejected_by": self.rejected_by,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
            "comment": self.comment,
            "history": [e.to_dict() for e in self.history],
            "metadata": self.metadata,
        }


# =============================================================================
# Protocol Definitions
# =============================================================================


class ApprovalStorage(Protocol):
    """
    Protocol for approval storage backends.

    Implementations should provide persistent storage for approval requests.
    """

    async def save(self, request: ApprovalRequest) -> None:
        """Save an approval request."""
        ...

    async def get(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get an approval request by ID."""
        ...

    async def update(self, request: ApprovalRequest) -> None:
        """Update an existing approval request."""
        ...

    async def delete(self, request_id: str) -> None:
        """Delete an approval request."""
        ...

    async def list_pending(self) -> List[ApprovalRequest]:
        """List all pending approval requests."""
        ...


class NotificationService(Protocol):
    """
    Protocol for notification services.

    Implementations should provide notification delivery for approval requests.
    """

    async def send_approval_request(self, request: ApprovalRequest) -> bool:
        """Send approval request notification."""
        ...

    async def send_approval_result(
        self, request: ApprovalRequest, approved: bool
    ) -> bool:
        """Send approval result notification."""
        ...


# =============================================================================
# HITL Controller
# =============================================================================


class HITLController:
    """
    Human-in-the-Loop Controller for approval workflow management.

    Coordinates the entire approval lifecycle:
    1. Creates approval requests for high-risk operations
    2. Tracks approval status
    3. Processes approval/rejection decisions
    4. Handles timeouts and cancellations

    Attributes:
        storage: Storage backend for approval requests
        notification_service: Service for sending notifications
        default_timeout_minutes: Default timeout for approval requests

    Example:
        >>> storage = InMemoryApprovalStorage()
        >>> notification = TeamsNotificationService(webhook_url)
        >>> controller = HITLController(storage, notification)
        >>> request = await controller.request_approval(
        ...     routing_decision=decision,
        ...     risk_assessment=assessment,
        ...     requester="user@example.com",
        ... )
        >>> print(request.status)  # ApprovalStatus.PENDING
    """

    def __init__(
        self,
        storage: ApprovalStorage,
        notification_service: Optional[NotificationService] = None,
        default_timeout_minutes: int = 30,
    ):
        """
        Initialize HITL Controller.

        Args:
            storage: Storage backend for approval requests
            notification_service: Optional notification service
            default_timeout_minutes: Default timeout for requests (default: 30)
        """
        self.storage = storage
        self.notification_service = notification_service
        self.default_timeout_minutes = default_timeout_minutes

        # Callbacks for approval events
        self._on_approved_callbacks: List[Callable[[ApprovalRequest], None]] = []
        self._on_rejected_callbacks: List[Callable[[ApprovalRequest], None]] = []
        self._on_expired_callbacks: List[Callable[[ApprovalRequest], None]] = []

    async def request_approval(
        self,
        routing_decision: RoutingDecision,
        risk_assessment: RiskAssessment,
        requester: str,
        timeout_minutes: Optional[int] = None,
        approvers: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ApprovalRequest:
        """
        Create a new approval request.

        Args:
            routing_decision: The routing decision requiring approval
            risk_assessment: Risk assessment for the operation
            requester: User or system requesting approval
            timeout_minutes: Custom timeout (uses default if None)
            approvers: List of users who can approve (optional)
            metadata: Additional metadata (optional)

        Returns:
            Created ApprovalRequest

        Raises:
            ValueError: If risk assessment doesn't require approval
        """
        # Validate that approval is actually required
        if not risk_assessment.requires_approval:
            raise ValueError(
                "Risk assessment does not require approval. "
                "Use RiskAssessor to determine if HITL is needed."
            )

        # Determine approval type from risk assessment
        approval_type = ApprovalType.NONE
        if risk_assessment.approval_type == "single":
            approval_type = ApprovalType.SINGLE
        elif risk_assessment.approval_type == "multi":
            approval_type = ApprovalType.MULTI

        # Calculate expiration
        timeout = timeout_minutes or self.default_timeout_minutes
        expires_at = datetime.utcnow() + timedelta(minutes=timeout)

        # Create request
        request = ApprovalRequest(
            request_id=str(uuid.uuid4()),
            routing_decision=routing_decision,
            risk_assessment=risk_assessment,
            requester=requester,
            expires_at=expires_at,
            approval_type=approval_type,
            approvers=approvers or [],
            metadata=metadata or {},
        )

        # Save to storage
        await self.storage.save(request)

        # Send notification
        if self.notification_service:
            try:
                await self.notification_service.send_approval_request(request)
                request.history.append(
                    ApprovalEvent(
                        event_type="notification_sent",
                        actor="system",
                        comment="Approval notification sent",
                    )
                )
                await self.storage.update(request)
            except Exception as e:
                logger.error(f"Failed to send approval notification: {e}")
                request.history.append(
                    ApprovalEvent(
                        event_type="notification_failed",
                        actor="system",
                        comment=f"Notification failed: {str(e)}",
                    )
                )
                await self.storage.update(request)

        logger.info(
            f"Approval request created: {request.request_id} "
            f"(type: {approval_type.value}, expires: {expires_at})"
        )

        return request

    async def check_status(self, request_id: str) -> ApprovalStatus:
        """
        Check the current status of an approval request.

        Automatically marks expired requests as EXPIRED.

        Args:
            request_id: The request ID to check

        Returns:
            Current ApprovalStatus

        Raises:
            ValueError: If request not found
        """
        request = await self.storage.get(request_id)
        if not request:
            raise ValueError(f"Approval request not found: {request_id}")

        # Check for expiration
        if request.status == ApprovalStatus.PENDING and request.is_expired():
            request.status = ApprovalStatus.EXPIRED
            request.history.append(
                ApprovalEvent(
                    event_type="expired",
                    actor="system",
                    comment="Request expired without decision",
                )
            )
            await self.storage.update(request)

            # Trigger expired callbacks
            for callback in self._on_expired_callbacks:
                try:
                    callback(request)
                except Exception as e:
                    logger.error(f"Expired callback error: {e}")

            logger.info(f"Approval request expired: {request_id}")

        return request.status

    async def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """
        Get an approval request by ID.

        Args:
            request_id: The request ID to retrieve

        Returns:
            ApprovalRequest or None if not found
        """
        request = await self.storage.get(request_id)
        if request and request.status == ApprovalStatus.PENDING and request.is_expired():
            # Auto-update expired status
            await self.check_status(request_id)
            request = await self.storage.get(request_id)
        return request

    async def process_approval(
        self,
        request_id: str,
        approved: bool,
        approver: str,
        comment: Optional[str] = None,
    ) -> ApprovalRequest:
        """
        Process an approval decision.

        Args:
            request_id: The request ID to process
            approved: Whether the request is approved
            approver: User making the decision
            comment: Optional comment or reason

        Returns:
            Updated ApprovalRequest

        Raises:
            ValueError: If request not found or not pending
        """
        request = await self.storage.get(request_id)
        if not request:
            raise ValueError(f"Approval request not found: {request_id}")

        # Check if request is still pending
        if request.status != ApprovalStatus.PENDING:
            raise ValueError(
                f"Request {request_id} is not pending "
                f"(current status: {request.status.value})"
            )

        # Check for expiration
        if request.is_expired():
            request.status = ApprovalStatus.EXPIRED
            request.history.append(
                ApprovalEvent(
                    event_type="expired",
                    actor="system",
                    comment="Request expired before decision",
                )
            )
            await self.storage.update(request)
            raise ValueError(f"Request {request_id} has expired")

        # Process decision
        now = datetime.utcnow()
        if approved:
            request.status = ApprovalStatus.APPROVED
            request.approved_by = approver
            request.approved_at = now
            request.comment = comment
            request.history.append(
                ApprovalEvent(
                    event_type="approved",
                    actor=approver,
                    comment=comment or "Request approved",
                )
            )

            # Trigger approved callbacks
            for callback in self._on_approved_callbacks:
                try:
                    callback(request)
                except Exception as e:
                    logger.error(f"Approved callback error: {e}")

            logger.info(f"Approval request approved: {request_id} by {approver}")
        else:
            request.status = ApprovalStatus.REJECTED
            request.rejected_by = approver
            request.rejected_at = now
            request.comment = comment
            request.history.append(
                ApprovalEvent(
                    event_type="rejected",
                    actor=approver,
                    comment=comment or "Request rejected",
                )
            )

            # Trigger rejected callbacks
            for callback in self._on_rejected_callbacks:
                try:
                    callback(request)
                except Exception as e:
                    logger.error(f"Rejected callback error: {e}")

            logger.info(f"Approval request rejected: {request_id} by {approver}")

        # Save updated request
        await self.storage.update(request)

        # Send result notification
        if self.notification_service:
            try:
                await self.notification_service.send_approval_result(request, approved)
            except Exception as e:
                logger.error(f"Failed to send result notification: {e}")

        return request

    async def cancel_approval(
        self,
        request_id: str,
        canceller: str,
        reason: Optional[str] = None,
    ) -> ApprovalRequest:
        """
        Cancel a pending approval request.

        Args:
            request_id: The request ID to cancel
            canceller: User cancelling the request
            reason: Optional cancellation reason

        Returns:
            Updated ApprovalRequest

        Raises:
            ValueError: If request not found or not pending
        """
        request = await self.storage.get(request_id)
        if not request:
            raise ValueError(f"Approval request not found: {request_id}")

        if request.status != ApprovalStatus.PENDING:
            raise ValueError(
                f"Request {request_id} is not pending "
                f"(current status: {request.status.value})"
            )

        # Cancel the request
        request.status = ApprovalStatus.CANCELLED
        request.history.append(
            ApprovalEvent(
                event_type="cancelled",
                actor=canceller,
                comment=reason or "Request cancelled by user",
            )
        )

        await self.storage.update(request)

        logger.info(f"Approval request cancelled: {request_id} by {canceller}")

        return request

    async def list_pending_requests(
        self,
        approver: Optional[str] = None,
    ) -> List[ApprovalRequest]:
        """
        List all pending approval requests.

        Args:
            approver: Optional filter by approver

        Returns:
            List of pending ApprovalRequest objects
        """
        pending = await self.storage.list_pending()

        # Filter by approver if specified
        if approver:
            pending = [
                r for r in pending
                if not r.approvers or approver in r.approvers
            ]

        # Check for expired requests
        for request in pending:
            if request.is_expired():
                await self.check_status(request.request_id)

        # Re-fetch to get updated statuses
        return await self.storage.list_pending()

    def on_approved(self, callback: Callable[[ApprovalRequest], None]) -> None:
        """
        Register a callback for approved requests.

        Args:
            callback: Function to call when a request is approved
        """
        self._on_approved_callbacks.append(callback)

    def on_rejected(self, callback: Callable[[ApprovalRequest], None]) -> None:
        """
        Register a callback for rejected requests.

        Args:
            callback: Function to call when a request is rejected
        """
        self._on_rejected_callbacks.append(callback)

    def on_expired(self, callback: Callable[[ApprovalRequest], None]) -> None:
        """
        Register a callback for expired requests.

        Args:
            callback: Function to call when a request expires
        """
        self._on_expired_callbacks.append(callback)


# =============================================================================
# In-Memory Storage Implementation
# =============================================================================


class InMemoryApprovalStorage:
    """
    In-memory storage for approval requests.

    Suitable for testing and development. Not persistent across restarts.
    """

    def __init__(self) -> None:
        """Initialize in-memory storage."""
        self._requests: Dict[str, ApprovalRequest] = {}

    async def save(self, request: ApprovalRequest) -> None:
        """Save an approval request."""
        self._requests[request.request_id] = request

    async def get(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get an approval request by ID."""
        return self._requests.get(request_id)

    async def update(self, request: ApprovalRequest) -> None:
        """Update an existing approval request."""
        self._requests[request.request_id] = request

    async def delete(self, request_id: str) -> None:
        """Delete an approval request."""
        self._requests.pop(request_id, None)

    async def list_pending(self) -> List[ApprovalRequest]:
        """List all pending approval requests."""
        return [
            r for r in self._requests.values()
            if r.status == ApprovalStatus.PENDING
        ]

    def clear(self) -> None:
        """Clear all stored requests."""
        self._requests.clear()


# =============================================================================
# Mock Notification Service
# =============================================================================


class MockNotificationService:
    """
    Mock notification service for testing.

    Records all notifications without actually sending them.
    """

    def __init__(self) -> None:
        """Initialize mock notification service."""
        self.sent_requests: List[ApprovalRequest] = []
        self.sent_results: List[tuple[ApprovalRequest, bool]] = []

    async def send_approval_request(self, request: ApprovalRequest) -> bool:
        """Record approval request notification."""
        self.sent_requests.append(request)
        return True

    async def send_approval_result(
        self, request: ApprovalRequest, approved: bool
    ) -> bool:
        """Record approval result notification."""
        self.sent_results.append((request, approved))
        return True

    def clear(self) -> None:
        """Clear recorded notifications."""
        self.sent_requests.clear()
        self.sent_results.clear()


# =============================================================================
# Factory Functions
# =============================================================================


def create_hitl_controller(
    storage: Optional[ApprovalStorage] = None,
    notification_service: Optional[NotificationService] = None,
    default_timeout_minutes: int = 30,
) -> HITLController:
    """
    Factory function to create a HITLController.

    Args:
        storage: Storage backend (uses InMemoryApprovalStorage if None)
        notification_service: Notification service (optional)
        default_timeout_minutes: Default timeout for requests

    Returns:
        HITLController instance
    """
    return HITLController(
        storage=storage or InMemoryApprovalStorage(),
        notification_service=notification_service,
        default_timeout_minutes=default_timeout_minutes,
    )


def create_mock_hitl_controller() -> tuple[HITLController, InMemoryApprovalStorage, MockNotificationService]:
    """
    Factory function to create a mock HITL controller for testing.

    Returns:
        Tuple of (HITLController, storage, notification_service)
    """
    storage = InMemoryApprovalStorage()
    notification = MockNotificationService()
    controller = HITLController(
        storage=storage,
        notification_service=notification,
        default_timeout_minutes=30,
    )
    return controller, storage, notification


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    "ApprovalStatus",
    "ApprovalType",
    # Data classes
    "ApprovalEvent",
    "ApprovalRequest",
    # Protocols
    "ApprovalStorage",
    "NotificationService",
    # Controller
    "HITLController",
    # Implementations
    "InMemoryApprovalStorage",
    "MockNotificationService",
    # Factory functions
    "create_hitl_controller",
    "create_mock_hitl_controller",
]
