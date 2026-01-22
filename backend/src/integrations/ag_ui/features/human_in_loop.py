# =============================================================================
# IPA Platform - AG-UI Human-in-the-Loop Feature
# =============================================================================
# Sprint 59: AG-UI Basic Features
# S59-3: Human-in-the-Loop (8 pts)
#
# Human-in-the-Loop (HITL) handler for AG-UI protocol.
# Integrates with RiskAssessmentEngine to require approval for high-risk operations.
#
# Features:
#   - Risk-based approval requirement check
#   - Approval status storage (in-memory with TTL)
#   - Custom approval_required events
#   - Approval timeout handling (default: 5 minutes)
#
# Dependencies:
#   - RiskAssessmentEngine (src.integrations.hybrid.risk)
#   - AG-UI Events (src.integrations.ag_ui.events)
# =============================================================================

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from src.integrations.ag_ui.events import (
    AGUIEventType,
    CustomEvent,
)
from src.integrations.hybrid.risk import RiskAssessmentEngine, RiskLevel
from src.integrations.hybrid.risk.models import (
    OperationContext,
    RiskAssessment,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================

class ApprovalStatus(str, Enum):
    """
    Approval status for pending tool calls.

    Attributes:
        PENDING: Awaiting user decision
        APPROVED: User approved the operation
        REJECTED: User rejected the operation
        TIMEOUT: Approval request timed out
        CANCELLED: Approval request was cancelled
    """
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


DEFAULT_APPROVAL_TIMEOUT_SECONDS = 300  # 5 minutes


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ToolCallInfo:
    """
    Information about a tool call requiring approval.

    Attributes:
        id: Unique tool call identifier
        name: Tool name
        arguments: Tool call arguments
    """
    id: str
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ApprovalRequest:
    """
    Approval request for a high-risk operation.

    Attributes:
        approval_id: Unique approval request ID
        tool_call_id: Associated tool call ID
        tool_name: Tool being called
        arguments: Tool arguments
        risk_level: Assessed risk level
        risk_score: Assessed risk score (0.0-1.0)
        reasoning: Human-readable reason for approval requirement
        run_id: Associated run ID
        session_id: Optional session ID
        status: Current approval status
        created_at: Request creation time
        expires_at: Request expiration time
        resolved_at: When the request was resolved (approved/rejected)
        user_comment: Optional comment from approver
        metadata: Additional metadata
    """
    approval_id: str
    tool_call_id: str
    tool_name: str
    arguments: Dict[str, Any]
    risk_level: RiskLevel
    risk_score: float
    reasoning: str
    run_id: str
    session_id: Optional[str] = None
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(seconds=DEFAULT_APPROVAL_TIMEOUT_SECONDS))
    resolved_at: Optional[datetime] = None
    user_comment: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if the approval request has expired."""
        return datetime.utcnow() > self.expires_at

    def is_pending(self) -> bool:
        """Check if the request is still pending."""
        return self.status == ApprovalStatus.PENDING and not self.is_expired()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "approval_id": self.approval_id,
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "risk_level": self.risk_level.value,
            "risk_score": self.risk_score,
            "reasoning": self.reasoning,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() + "Z",
            "expires_at": self.expires_at.isoformat() + "Z",
            "resolved_at": self.resolved_at.isoformat() + "Z" if self.resolved_at else None,
            "user_comment": self.user_comment,
            "metadata": self.metadata,
        }


# =============================================================================
# Approval Storage
# =============================================================================

class ApprovalStorage:
    """
    In-memory storage for approval requests.

    Manages pending approval requests with automatic expiration cleanup.
    For production use, consider implementing Redis-based storage.

    Example:
        >>> storage = ApprovalStorage()
        >>> approval_id = await storage.create_pending(
        ...     tool_call_id="tc-123",
        ...     tool_name="Bash",
        ...     arguments={"command": "rm -rf /tmp/test"},
        ...     risk_level=RiskLevel.HIGH,
        ...     risk_score=0.75,
        ...     reasoning="High-risk shell command",
        ...     run_id="run-abc",
        ... )
        >>> await storage.update_status(approval_id, approved=True)
    """

    def __init__(
        self,
        default_timeout_seconds: int = DEFAULT_APPROVAL_TIMEOUT_SECONDS,
    ):
        """
        Initialize the approval storage.

        Args:
            default_timeout_seconds: Default timeout for approval requests
        """
        self._requests: Dict[str, ApprovalRequest] = {}
        self._default_timeout = default_timeout_seconds
        self._lock = asyncio.Lock()

    async def create_pending(
        self,
        tool_call_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        risk_level: RiskLevel,
        risk_score: float,
        reasoning: str,
        run_id: str,
        session_id: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new pending approval request.

        Args:
            tool_call_id: Tool call identifier
            tool_name: Name of the tool
            arguments: Tool call arguments
            risk_level: Assessed risk level
            risk_score: Risk score (0.0-1.0)
            reasoning: Reason for requiring approval
            run_id: Associated run ID
            session_id: Optional session ID
            timeout_seconds: Custom timeout (uses default if None)
            metadata: Additional metadata

        Returns:
            Unique approval request ID
        """
        timeout = timeout_seconds if timeout_seconds is not None else self._default_timeout
        approval_id = f"approval-{uuid.uuid4().hex[:12]}"

        request = ApprovalRequest(
            approval_id=approval_id,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            arguments=arguments,
            risk_level=risk_level,
            risk_score=risk_score,
            reasoning=reasoning,
            run_id=run_id,
            session_id=session_id,
            expires_at=datetime.utcnow() + timedelta(seconds=timeout),
            metadata=metadata or {},
        )

        async with self._lock:
            self._requests[approval_id] = request
            logger.info(
                f"Created approval request: {approval_id} "
                f"(tool={tool_name}, risk={risk_level.value})"
            )

        return approval_id

    async def get(self, approval_id: str) -> Optional[ApprovalRequest]:
        """
        Get an approval request by ID.

        Args:
            approval_id: Approval request ID

        Returns:
            ApprovalRequest or None if not found
        """
        async with self._lock:
            request = self._requests.get(approval_id)
            if request and request.is_expired() and request.status == ApprovalStatus.PENDING:
                request.status = ApprovalStatus.TIMEOUT
                request.resolved_at = datetime.utcnow()
            return request

    async def update_status(
        self,
        approval_id: str,
        approved: bool,
        user_comment: Optional[str] = None,
    ) -> bool:
        """
        Update the status of an approval request.

        Args:
            approval_id: Approval request ID
            approved: Whether the request was approved
            user_comment: Optional comment from the user

        Returns:
            True if updated successfully, False if not found or expired
        """
        async with self._lock:
            request = self._requests.get(approval_id)
            if not request:
                logger.warning(f"Approval request not found: {approval_id}")
                return False

            if request.is_expired():
                request.status = ApprovalStatus.TIMEOUT
                request.resolved_at = datetime.utcnow()
                logger.warning(f"Approval request expired: {approval_id}")
                return False

            if request.status != ApprovalStatus.PENDING:
                logger.warning(
                    f"Approval request already resolved: {approval_id} "
                    f"(status={request.status.value})"
                )
                return False

            request.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
            request.resolved_at = datetime.utcnow()
            request.user_comment = user_comment

            logger.info(
                f"Approval request resolved: {approval_id} "
                f"(status={request.status.value})"
            )
            return True

    async def get_pending(
        self,
        session_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> List[ApprovalRequest]:
        """
        Get all pending approval requests.

        Args:
            session_id: Filter by session ID
            run_id: Filter by run ID

        Returns:
            List of pending approval requests
        """
        async with self._lock:
            # Update expired requests first
            for request in self._requests.values():
                if request.is_expired() and request.status == ApprovalStatus.PENDING:
                    request.status = ApprovalStatus.TIMEOUT
                    request.resolved_at = datetime.utcnow()

            pending = [
                r for r in self._requests.values()
                if r.status == ApprovalStatus.PENDING
            ]

            if session_id:
                # Include approvals with matching session_id OR with None session_id
                # (approvals created without session context should be visible to all)
                pending = [
                    r for r in pending
                    if r.session_id == session_id or r.session_id is None
                ]
            if run_id:
                pending = [r for r in pending if r.run_id == run_id]

            return sorted(pending, key=lambda r: r.created_at)

    async def cancel(self, approval_id: str) -> bool:
        """
        Cancel a pending approval request.

        Args:
            approval_id: Approval request ID

        Returns:
            True if cancelled, False if not found or already resolved
        """
        async with self._lock:
            request = self._requests.get(approval_id)
            if not request:
                return False

            if request.status != ApprovalStatus.PENDING:
                return False

            request.status = ApprovalStatus.CANCELLED
            request.resolved_at = datetime.utcnow()
            logger.info(f"Approval request cancelled: {approval_id}")
            return True

    async def cleanup_expired(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up old resolved/expired approval requests.

        Args:
            max_age_seconds: Maximum age for requests to keep

        Returns:
            Number of requests removed
        """
        cutoff = datetime.utcnow() - timedelta(seconds=max_age_seconds)
        removed = 0

        async with self._lock:
            to_remove = [
                aid for aid, req in self._requests.items()
                if req.status != ApprovalStatus.PENDING and req.created_at < cutoff
            ]
            for aid in to_remove:
                del self._requests[aid]
                removed += 1

        if removed > 0:
            logger.info(f"Cleaned up {removed} expired approval requests")

        return removed

    def get_stats(self) -> Dict[str, int]:
        """Get storage statistics."""
        stats = {
            "total": len(self._requests),
            "pending": 0,
            "approved": 0,
            "rejected": 0,
            "timeout": 0,
            "cancelled": 0,
        }
        for request in self._requests.values():
            stats[request.status.value] = stats.get(request.status.value, 0) + 1
        return stats


# =============================================================================
# HITL Handler
# =============================================================================

class HITLHandler:
    """
    Human-in-the-Loop handler for AG-UI protocol.

    Integrates with RiskAssessmentEngine to determine when
    human approval is required for tool operations.

    Example:
        >>> risk_engine = RiskAssessmentEngine()
        >>> storage = ApprovalStorage()
        >>> hitl = HITLHandler(risk_engine, storage)
        >>>
        >>> tool_call = ToolCallInfo(id="tc-123", name="Bash", arguments={"command": "rm -rf /"})
        >>> needs_approval, assessment = await hitl.check_approval_needed(tool_call)
        >>> if needs_approval:
        ...     event = await hitl.create_approval_event(tool_call, assessment, run_id="run-1")
    """

    def __init__(
        self,
        risk_engine: RiskAssessmentEngine,
        approval_storage: ApprovalStorage,
        default_timeout_seconds: int = DEFAULT_APPROVAL_TIMEOUT_SECONDS,
    ):
        """
        Initialize the HITL handler.

        Args:
            risk_engine: Risk assessment engine instance
            approval_storage: Approval storage instance
            default_timeout_seconds: Default approval timeout
        """
        self.risk_engine = risk_engine
        self.approval_storage = approval_storage
        self.default_timeout = default_timeout_seconds

    async def check_approval_needed(
        self,
        tool_call: ToolCallInfo,
        session_id: Optional[str] = None,
        environment: str = "development",
    ) -> tuple[bool, Optional[RiskAssessment]]:
        """
        Check if approval is needed for a tool call.

        Args:
            tool_call: Tool call information
            session_id: Optional session ID for context
            environment: Execution environment

        Returns:
            Tuple of (needs_approval, risk_assessment)
        """
        # Create operation context for risk assessment
        context = OperationContext(
            tool_name=tool_call.name,
            operation_type="tool_call",
            arguments=tool_call.arguments,
            session_id=session_id,
            environment=environment,
        )

        # Extract command if Bash tool
        if tool_call.name == "Bash" and "command" in tool_call.arguments:
            context.command = tool_call.arguments["command"]

        # Extract target paths if file operation
        if "file_path" in tool_call.arguments:
            context.target_paths = [tool_call.arguments["file_path"]]
        elif "path" in tool_call.arguments:
            context.target_paths = [tool_call.arguments["path"]]

        # Perform risk assessment
        assessment = self.risk_engine.assess(context)

        needs_approval = assessment.requires_approval

        logger.debug(
            f"Approval check for {tool_call.name}: "
            f"level={assessment.overall_level.value}, "
            f"needs_approval={needs_approval}"
        )

        return needs_approval, assessment

    async def create_approval_event(
        self,
        tool_call: ToolCallInfo,
        assessment: RiskAssessment,
        run_id: str,
        session_id: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> CustomEvent:
        """
        Create an approval_required custom event.

        Args:
            tool_call: Tool call information
            assessment: Risk assessment result
            run_id: Current run ID
            session_id: Optional session ID
            timeout_seconds: Custom timeout for this request

        Returns:
            CustomEvent for approval_required
        """
        timeout = timeout_seconds or self.default_timeout

        # Create approval request in storage
        approval_id = await self.approval_storage.create_pending(
            tool_call_id=tool_call.id,
            tool_name=tool_call.name,
            arguments=tool_call.arguments,
            risk_level=assessment.overall_level,
            risk_score=assessment.overall_score,
            reasoning=assessment.approval_reason or self._generate_reasoning(assessment),
            run_id=run_id,
            session_id=session_id,
            timeout_seconds=timeout,
            metadata={
                "factors": [
                    {
                        "type": f.factor_type.value,
                        "score": f.score,
                        "description": f.description,
                    }
                    for f in assessment.factors[:5]  # Top 5 factors
                ],
            },
        )

        # Create custom event
        return CustomEvent(
            type=AGUIEventType.CUSTOM,
            event_name="approval_required",
            payload={
                "approval_id": approval_id,
                "tool_call_id": tool_call.id,
                "tool_name": tool_call.name,
                "arguments": tool_call.arguments,
                "risk_level": assessment.overall_level.value,
                "risk_score": round(assessment.overall_score, 3),
                "reasoning": assessment.approval_reason or self._generate_reasoning(assessment),
                "timeout_seconds": timeout,
                "expires_at": (
                    datetime.utcnow() + timedelta(seconds=timeout)
                ).isoformat() + "Z",
            },
        )

    async def handle_approval_response(
        self,
        approval_id: str,
        approved: bool,
        user_comment: Optional[str] = None,
    ) -> tuple[bool, Optional[ApprovalRequest]]:
        """
        Handle an approval response from the user.

        Args:
            approval_id: Approval request ID
            approved: Whether the request was approved
            user_comment: Optional comment from the user

        Returns:
            Tuple of (success, approval_request)
        """
        success = await self.approval_storage.update_status(
            approval_id=approval_id,
            approved=approved,
            user_comment=user_comment,
        )

        request = await self.approval_storage.get(approval_id)

        if success:
            logger.info(
                f"Approval response handled: {approval_id} "
                f"(approved={approved})"
            )
        else:
            logger.warning(
                f"Failed to handle approval response: {approval_id}"
            )

        return success, request

    async def wait_for_approval(
        self,
        approval_id: str,
        poll_interval_seconds: float = 0.5,
    ) -> ApprovalRequest:
        """
        Wait for an approval request to be resolved.

        Args:
            approval_id: Approval request ID
            poll_interval_seconds: Polling interval

        Returns:
            Resolved ApprovalRequest

        Raises:
            ValueError: If approval request not found
            TimeoutError: If approval times out
        """
        while True:
            request = await self.approval_storage.get(approval_id)

            if not request:
                raise ValueError(f"Approval request not found: {approval_id}")

            if request.status != ApprovalStatus.PENDING:
                return request

            if request.is_expired():
                request.status = ApprovalStatus.TIMEOUT
                return request

            await asyncio.sleep(poll_interval_seconds)

    async def create_approval_resolved_event(
        self,
        request: ApprovalRequest,
    ) -> CustomEvent:
        """
        Create an approval_resolved custom event.

        Args:
            request: Resolved approval request

        Returns:
            CustomEvent for approval_resolved
        """
        return CustomEvent(
            type=AGUIEventType.CUSTOM,
            event_name="approval_resolved",
            payload={
                "approval_id": request.approval_id,
                "tool_call_id": request.tool_call_id,
                "tool_name": request.tool_name,
                "status": request.status.value,
                "approved": request.status == ApprovalStatus.APPROVED,
                "user_comment": request.user_comment,
                "resolved_at": request.resolved_at.isoformat() + "Z" if request.resolved_at else None,
            },
        )

    def _generate_reasoning(self, assessment: RiskAssessment) -> str:
        """
        Generate human-readable reasoning from assessment.

        Args:
            assessment: Risk assessment result

        Returns:
            Reasoning string
        """
        parts = [f"Risk level: {assessment.overall_level.value.upper()}"]

        # Add top contributing factors
        sorted_factors = sorted(
            assessment.factors,
            key=lambda f: f.weighted_score(),
            reverse=True,
        )[:3]

        for factor in sorted_factors:
            if factor.weighted_score() > 0.05:
                parts.append(f"- {factor.description}")

        return " | ".join(parts)


# =============================================================================
# Factory Functions
# =============================================================================

def create_hitl_handler(
    risk_engine: Optional[RiskAssessmentEngine] = None,
    approval_storage: Optional[ApprovalStorage] = None,
    default_timeout_seconds: int = DEFAULT_APPROVAL_TIMEOUT_SECONDS,
) -> HITLHandler:
    """
    Factory function to create a configured HITLHandler.

    Args:
        risk_engine: Optional risk engine (creates new if None)
        approval_storage: Optional approval storage (creates new if None)
        default_timeout_seconds: Default approval timeout

    Returns:
        Configured HITLHandler instance
    """
    engine = risk_engine or RiskAssessmentEngine()
    storage = approval_storage or ApprovalStorage(default_timeout_seconds)

    return HITLHandler(
        risk_engine=engine,
        approval_storage=storage,
        default_timeout_seconds=default_timeout_seconds,
    )


# Global singleton instances (for dependency injection)
_default_storage: Optional[ApprovalStorage] = None
_default_handler: Optional[HITLHandler] = None


def get_approval_storage() -> ApprovalStorage:
    """Get or create the default approval storage instance."""
    global _default_storage
    if _default_storage is None:
        _default_storage = ApprovalStorage()
    return _default_storage


def get_hitl_handler() -> HITLHandler:
    """Get or create the default HITL handler instance."""
    global _default_handler
    if _default_handler is None:
        _default_handler = create_hitl_handler(
            approval_storage=get_approval_storage(),
        )
    return _default_handler
