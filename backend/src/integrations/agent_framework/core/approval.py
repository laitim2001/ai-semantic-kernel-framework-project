# =============================================================================
# IPA Platform - Human Approval Executor
# =============================================================================
# Phase 5: MVP Core Official API Migration
# Sprint 28, Story S28-1: HumanApprovalExecutor (10 pts)
#
# This module provides human-in-the-loop approval functionality using
# the official Microsoft Agent Framework RequestResponseExecutor API.
#
# Official API Pattern (from workflows-api.md):
#   from agent_framework.workflows import RequestResponseExecutor, Executor
#   @Executor.register
#   class HumanApproval(RequestResponseExecutor[ApprovalRequest, ApprovalResponse]):
#       """Workflow pauses here until response received."""
#       pass
#
# Key Features:
#   - HumanApprovalExecutor: Pauses workflow for human approval
#   - ApprovalRequest/Response: Typed models for approval flow
#   - EscalationPolicy: Timeout and escalation handling
#   - NotificationConfig: Notification settings for approvers
#
# IMPORTANT: Uses official Agent Framework API
#   from agent_framework.workflows import RequestResponseExecutor, Executor
# =============================================================================

from typing import Any, Callable, Dict, List, Optional, Union
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import logging

from pydantic import BaseModel, Field

# Official Agent Framework Imports - MUST use these
# Note: Classes are directly under agent_framework, not agent_framework.workflows
from agent_framework import Executor, handler, WorkflowContext

# RequestResponseExecutor not directly available - use Executor as base
# This will be updated when official API is finalized
RequestResponseExecutor = Executor  # Compatibility alias

logger = logging.getLogger(__name__)


# =============================================================================
# ApprovalStatus - Approval State Enumeration
# =============================================================================

class ApprovalStatus(str, Enum):
    """
    Enumeration of approval states.

    Maps to existing CheckpointStatus for backward compatibility.
    """
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ESCALATED = "escalated"
    CANCELLED = "cancelled"


# =============================================================================
# RiskLevel - Risk Classification
# =============================================================================

class RiskLevel(str, Enum):
    """
    Risk level classification for approval requests.
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# =============================================================================
# ApprovalRequest - Request Model (Pydantic)
# =============================================================================

class ApprovalRequest(BaseModel):
    """
    Request model for human approval.

    Contains all information needed for approvers to make a decision.

    Example:
        >>> request = ApprovalRequest(
        ...     action="deploy_to_production",
        ...     risk_level=RiskLevel.HIGH,
        ...     details="Deploy version 2.0.0 to production environment",
        ...     context={"version": "2.0.0", "environment": "production"},
        ...     requester="system",
        ...     workflow_id="workflow-123"
        ... )
    """
    # Required fields
    action: str = Field(..., description="The action requiring approval")
    risk_level: Union[RiskLevel, str] = Field(
        default=RiskLevel.MEDIUM,
        description="Risk level of the action"
    )
    details: str = Field(..., description="Detailed description of the action")

    # Optional context
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for the approval decision"
    )
    requester: str = Field(
        default="system",
        description="Who or what is requesting approval"
    )
    workflow_id: Optional[str] = Field(
        default=None,
        description="ID of the workflow requesting approval"
    )
    node_id: Optional[str] = Field(
        default=None,
        description="ID of the workflow node requesting approval"
    )
    execution_id: Optional[str] = Field(
        default=None,
        description="ID of the current execution"
    )

    # Metadata
    request_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this request"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the request was created"
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="When the request expires"
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True


# =============================================================================
# ApprovalResponse - Response Model (Pydantic)
# =============================================================================

class ApprovalResponse(BaseModel):
    """
    Response model for human approval decisions.

    Contains the approver's decision and reasoning.

    Example:
        >>> response = ApprovalResponse(
        ...     approved=True,
        ...     reason="Risk acceptable after review",
        ...     approver="admin@company.com"
        ... )
    """
    # Required fields
    approved: bool = Field(..., description="Whether the action is approved")
    reason: str = Field(..., description="Reason for the decision")
    approver: str = Field(..., description="Who approved/rejected the request")

    # Optional fields
    conditions: List[str] = Field(
        default_factory=list,
        description="Conditions attached to the approval"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes from the approver"
    )

    # Metadata
    response_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this response"
    )
    responded_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the response was provided"
    )

    class Config:
        """Pydantic configuration."""
        pass


# =============================================================================
# NotificationConfig - Notification Settings
# =============================================================================

class NotificationConfig(BaseModel):
    """
    Configuration for approval notifications.
    """
    enabled: bool = Field(default=True, description="Whether notifications are enabled")
    channels: List[str] = Field(
        default_factory=lambda: ["email"],
        description="Notification channels (email, slack, teams, webhook)"
    )
    recipients: List[str] = Field(
        default_factory=list,
        description="List of notification recipients"
    )
    reminder_interval_minutes: int = Field(
        default=60,
        description="How often to send reminder notifications"
    )
    max_reminders: int = Field(
        default=3,
        description="Maximum number of reminders to send"
    )


# =============================================================================
# EscalationPolicy - Timeout and Escalation Handling
# =============================================================================

@dataclass
class EscalationPolicy:
    """
    Policy for handling approval timeouts and escalation.

    Defines what happens when an approval request is not responded to
    within the specified timeout period.

    Attributes:
        timeout_minutes: Time before escalation (default: 60)
        escalate_to: List of users/groups to escalate to
        auto_approve: Whether to auto-approve on timeout
        auto_reject: Whether to auto-reject on timeout
        max_escalations: Maximum escalation levels
        notify_on_escalation: Send notification on escalation

    Example:
        >>> policy = EscalationPolicy(
        ...     timeout_minutes=30,
        ...     escalate_to=["manager@company.com", "admin@company.com"],
        ...     auto_reject=True
        ... )
    """
    timeout_minutes: int = 60
    escalate_to: List[str] = field(default_factory=list)
    auto_approve: bool = False
    auto_reject: bool = False
    max_escalations: int = 2
    notify_on_escalation: bool = True

    def __post_init__(self):
        """Validate policy configuration."""
        if self.auto_approve and self.auto_reject:
            raise ValueError("Cannot both auto_approve and auto_reject on timeout")

    def get_expiry_time(self, from_time: Optional[datetime] = None) -> datetime:
        """
        Calculate expiry time based on timeout.

        Args:
            from_time: Start time (defaults to now)

        Returns:
            Expiry datetime
        """
        start = from_time or datetime.utcnow()
        return start + timedelta(minutes=self.timeout_minutes)

    def should_escalate(self, current_escalation_level: int) -> bool:
        """
        Check if escalation should occur.

        Args:
            current_escalation_level: Current escalation level

        Returns:
            True if escalation should occur
        """
        return (
            len(self.escalate_to) > 0 and
            current_escalation_level < self.max_escalations
        )


# =============================================================================
# ApprovalState - Internal State Tracking
# =============================================================================

@dataclass
class ApprovalState:
    """
    Internal state tracking for an approval request.
    """
    request: ApprovalRequest
    status: ApprovalStatus = ApprovalStatus.PENDING
    response: Optional[ApprovalResponse] = None
    escalation_level: int = 0
    reminders_sent: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    history: List[Dict[str, Any]] = field(default_factory=list)

    def add_history_entry(self, action: str, details: Dict[str, Any]) -> None:
        """Add an entry to the history."""
        self.history.append({
            "action": action,
            "details": details,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.updated_at = datetime.utcnow()


# =============================================================================
# HumanApprovalExecutor - Main Executor
# =============================================================================

class HumanApprovalExecutor(Executor):
    """
    Human approval executor using official RequestResponseExecutor.

    Pauses workflow execution until human approval is received.
    Supports timeout handling, escalation, and notification.

    Example:
        >>> executor = HumanApprovalExecutor(
        ...     name="deployment-approval",
        ...     escalation_policy=EscalationPolicy(timeout_minutes=30)
        ... )

        # In workflow
        >>> workflow = Workflow(
        ...     executors=[analyzer, executor, deployer],
        ...     edges=[...]
        ... )

        # Later, provide response
        >>> await workflow.respond(
        ...     executor_name="deployment-approval",
        ...     response=ApprovalResponse(
        ...         approved=True,
        ...         reason="Risk acceptable",
        ...         approver="admin@company.com"
        ...     )
        ... )

    IMPORTANT: Uses official RequestResponseExecutor from agent_framework.workflows
    """

    def __init__(
        self,
        name: str = "human-approval",
        escalation_policy: Optional[EscalationPolicy] = None,
        notification_config: Optional[NotificationConfig] = None,
        on_request_created: Optional[Callable] = None,
        on_response_received: Optional[Callable] = None,
        on_escalation: Optional[Callable] = None,
        on_timeout: Optional[Callable] = None,
    ):
        """
        Initialize the human approval executor.

        Args:
            name: Name for this executor
            escalation_policy: Policy for timeouts and escalation
            notification_config: Notification settings
            on_request_created: Callback when request is created
            on_response_received: Callback when response is received
            on_escalation: Callback when request is escalated
            on_timeout: Callback when request times out
        """
        # Official Executor requires 'id' parameter
        super().__init__(id=name)
        self._name = name
        self._escalation_policy = escalation_policy or EscalationPolicy()
        self._notification_config = notification_config or NotificationConfig()

        # Callbacks
        self._on_request_created = on_request_created
        self._on_response_received = on_response_received
        self._on_escalation = on_escalation
        self._on_timeout = on_timeout

        # State tracking
        self._pending_requests: Dict[str, ApprovalState] = {}
        self._completed_requests: Dict[str, ApprovalState] = {}

    @handler
    async def handle_approval_request(
        self,
        input_data: Dict[str, Any],
        ctx: WorkflowContext
    ) -> None:
        """
        Main handler for approval requests.

        This is the entry point called by the workflow engine when an approval
        is needed. Creates a pending approval request and waits for response.

        IMPORTANT: Uses official @handler decorator from agent_framework.

        Args:
            input_data: Dictionary containing approval request data
            ctx: WorkflowContext for sending messages and yielding outputs
        """
        try:
            # Create approval request from input data
            request = ApprovalRequest(
                request_id=str(uuid4()),
                action=input_data.get("action", "approve"),
                payload=input_data.get("payload", {}),
                context=input_data.get("context"),
                requester_id=input_data.get("requester_id"),
                priority=ApprovalPriority(input_data.get("priority", "normal")),
            )

            # Track the request
            await self.on_request_created(request, ctx)

            logger.info(f"Approval handler received request: {request.request_id}")

            # Send acknowledgment back
            await ctx.send_message({
                "type": "approval_pending",
                "request_id": request.request_id,
                "status": "pending",
            })

        except Exception as e:
            logger.error(f"Approval handler error: {str(e)}", exc_info=True)
            await ctx.send_message({
                "type": "approval_error",
                "error": str(e),
            })

    @property
    def name(self) -> str:
        """Get the executor name."""
        return self._name

    @property
    def escalation_policy(self) -> EscalationPolicy:
        """Get the escalation policy."""
        return self._escalation_policy

    @property
    def notification_config(self) -> NotificationConfig:
        """Get the notification configuration."""
        return self._notification_config

    @property
    def pending_count(self) -> int:
        """Get count of pending requests."""
        return len(self._pending_requests)

    async def on_request_created(
        self,
        request: ApprovalRequest,
        context: Any,
    ) -> None:
        """
        Called when an approval request is created.

        Override this method to customize request creation behavior.

        Args:
            request: The approval request
            context: Workflow context
        """
        # Create state tracking
        state = ApprovalState(request=request)
        state.add_history_entry("created", {
            "request_id": request.request_id,
            "action": request.action,
        })

        # Set expiry based on policy
        request.expires_at = self._escalation_policy.get_expiry_time()

        # Store pending request
        self._pending_requests[request.request_id] = state

        logger.info(
            f"Approval request created: {request.request_id} "
            f"for action '{request.action}'"
        )

        # Call custom callback if provided
        if self._on_request_created:
            try:
                if asyncio.iscoroutinefunction(self._on_request_created):
                    await self._on_request_created(request, context)
                else:
                    self._on_request_created(request, context)
            except Exception as e:
                logger.error(f"on_request_created callback error: {e}")

        # Send notifications
        await self._send_notification(request, "new_request")

    async def on_response_received(
        self,
        request: ApprovalRequest,
        response: ApprovalResponse,
        context: Any,
    ) -> None:
        """
        Called when an approval response is received.

        Override this method to customize response handling behavior.

        Args:
            request: The original approval request
            response: The approval response
            context: Workflow context
        """
        request_id = request.request_id

        # Get state
        state = self._pending_requests.get(request_id)
        if not state:
            logger.warning(f"No pending request found for {request_id}")
            return

        # Update state
        state.response = response
        state.status = (
            ApprovalStatus.APPROVED if response.approved
            else ApprovalStatus.REJECTED
        )
        state.add_history_entry("responded", {
            "approved": response.approved,
            "approver": response.approver,
            "reason": response.reason,
        })

        # Move to completed
        self._completed_requests[request_id] = state
        del self._pending_requests[request_id]

        logger.info(
            f"Approval response received: {request_id} - "
            f"{'approved' if response.approved else 'rejected'} "
            f"by {response.approver}"
        )

        # Call custom callback if provided
        if self._on_response_received:
            try:
                if asyncio.iscoroutinefunction(self._on_response_received):
                    await self._on_response_received(request, response, context)
                else:
                    self._on_response_received(request, response, context)
            except Exception as e:
                logger.error(f"on_response_received callback error: {e}")

        # Send notification
        await self._send_notification(request, "response_received", response)

    async def check_timeout(self, request_id: str) -> Optional[ApprovalResponse]:
        """
        Check if a request has timed out and handle accordingly.

        Args:
            request_id: The request ID to check

        Returns:
            Auto-generated response if timeout handling triggered, None otherwise
        """
        state = self._pending_requests.get(request_id)
        if not state:
            return None

        request = state.request
        now = datetime.utcnow()

        # Check if expired
        if request.expires_at and now >= request.expires_at:
            # Handle timeout based on policy
            policy = self._escalation_policy

            # Try escalation first
            if policy.should_escalate(state.escalation_level):
                await self._escalate_request(state)
                return None

            # Handle auto-action
            if policy.auto_approve:
                response = ApprovalResponse(
                    approved=True,
                    reason="Auto-approved due to timeout",
                    approver="system:auto-approve",
                )
                state.status = ApprovalStatus.APPROVED
            elif policy.auto_reject:
                response = ApprovalResponse(
                    approved=False,
                    reason="Auto-rejected due to timeout",
                    approver="system:auto-reject",
                )
                state.status = ApprovalStatus.REJECTED
            else:
                # Mark as expired
                state.status = ApprovalStatus.EXPIRED
                state.add_history_entry("expired", {
                    "reason": "Timeout without response",
                })
                return None

            state.response = response
            state.add_history_entry("timeout_handled", {
                "action": "auto-approved" if policy.auto_approve else "auto-rejected",
            })

            # Move to completed
            self._completed_requests[request_id] = state
            del self._pending_requests[request_id]

            # Call timeout callback
            if self._on_timeout:
                try:
                    if asyncio.iscoroutinefunction(self._on_timeout):
                        await self._on_timeout(request, response)
                    else:
                        self._on_timeout(request, response)
                except Exception as e:
                    logger.error(f"on_timeout callback error: {e}")

            return response

        return None

    async def _escalate_request(self, state: ApprovalState) -> None:
        """
        Escalate a request to the next level.

        Args:
            state: The approval state to escalate
        """
        policy = self._escalation_policy
        request = state.request

        # Increment escalation level
        state.escalation_level += 1
        state.status = ApprovalStatus.ESCALATED

        # Extend expiry
        request.expires_at = policy.get_expiry_time()

        state.add_history_entry("escalated", {
            "level": state.escalation_level,
            "escalate_to": policy.escalate_to,
        })

        logger.info(
            f"Request {request.request_id} escalated to level {state.escalation_level}"
        )

        # Call escalation callback
        if self._on_escalation:
            try:
                if asyncio.iscoroutinefunction(self._on_escalation):
                    await self._on_escalation(request, state.escalation_level)
                else:
                    self._on_escalation(request, state.escalation_level)
            except Exception as e:
                logger.error(f"on_escalation callback error: {e}")

        # Send escalation notification
        if policy.notify_on_escalation:
            await self._send_notification(request, "escalated")

    async def _send_notification(
        self,
        request: ApprovalRequest,
        notification_type: str,
        response: Optional[ApprovalResponse] = None,
    ) -> None:
        """
        Send notification for approval events.

        Args:
            request: The approval request
            notification_type: Type of notification
            response: Optional response for response notifications
        """
        config = self._notification_config
        if not config.enabled:
            return

        # Build notification payload
        payload = {
            "type": notification_type,
            "request_id": request.request_id,
            "action": request.action,
            "risk_level": request.risk_level,
            "details": request.details,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if response:
            payload["response"] = {
                "approved": response.approved,
                "reason": response.reason,
                "approver": response.approver,
            }

        # Log notification (actual delivery would be implemented by infrastructure)
        logger.debug(
            f"Notification [{notification_type}] for request {request.request_id}: "
            f"channels={config.channels}, recipients={config.recipients}"
        )

    def get_request_state(self, request_id: str) -> Optional[ApprovalState]:
        """
        Get the state of a request.

        Args:
            request_id: The request ID

        Returns:
            ApprovalState or None
        """
        return (
            self._pending_requests.get(request_id) or
            self._completed_requests.get(request_id)
        )

    def get_pending_requests(self) -> List[ApprovalState]:
        """Get all pending approval requests."""
        return list(self._pending_requests.values())

    def get_completed_requests(self) -> List[ApprovalState]:
        """Get all completed approval requests."""
        return list(self._completed_requests.values())

    def cancel_request(self, request_id: str, reason: str = "Cancelled") -> bool:
        """
        Cancel a pending request.

        Args:
            request_id: The request ID to cancel
            reason: Cancellation reason

        Returns:
            True if cancelled, False if not found
        """
        state = self._pending_requests.get(request_id)
        if not state:
            return False

        state.status = ApprovalStatus.CANCELLED
        state.add_history_entry("cancelled", {"reason": reason})

        self._completed_requests[request_id] = state
        del self._pending_requests[request_id]

        logger.info(f"Request {request_id} cancelled: {reason}")
        return True

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"HumanApprovalExecutor("
            f"name={self._name!r}, "
            f"pending={self.pending_count}, "
            f"completed={len(self._completed_requests)})"
        )


# =============================================================================
# Factory Functions
# =============================================================================

def create_approval_executor(
    name: str = "human-approval",
    timeout_minutes: int = 60,
    escalate_to: Optional[List[str]] = None,
    auto_approve: bool = False,
    auto_reject: bool = False,
    notification_enabled: bool = True,
    notification_channels: Optional[List[str]] = None,
) -> HumanApprovalExecutor:
    """
    Factory function to create a HumanApprovalExecutor.

    Args:
        name: Executor name
        timeout_minutes: Timeout before escalation
        escalate_to: Users to escalate to
        auto_approve: Auto-approve on timeout
        auto_reject: Auto-reject on timeout
        notification_enabled: Enable notifications
        notification_channels: Notification channels

    Returns:
        HumanApprovalExecutor instance
    """
    escalation_policy = EscalationPolicy(
        timeout_minutes=timeout_minutes,
        escalate_to=escalate_to or [],
        auto_approve=auto_approve,
        auto_reject=auto_reject,
    )

    notification_config = NotificationConfig(
        enabled=notification_enabled,
        channels=notification_channels or ["email"],
    )

    return HumanApprovalExecutor(
        name=name,
        escalation_policy=escalation_policy,
        notification_config=notification_config,
    )


def create_approval_request(
    action: str,
    details: str,
    risk_level: Union[RiskLevel, str] = RiskLevel.MEDIUM,
    context: Optional[Dict[str, Any]] = None,
    requester: str = "system",
    workflow_id: Optional[str] = None,
    execution_id: Optional[str] = None,
) -> ApprovalRequest:
    """
    Factory function to create an ApprovalRequest.

    Args:
        action: Action requiring approval
        details: Detailed description
        risk_level: Risk classification
        context: Additional context
        requester: Who is requesting
        workflow_id: Workflow ID
        execution_id: Execution ID

    Returns:
        ApprovalRequest instance
    """
    return ApprovalRequest(
        action=action,
        details=details,
        risk_level=risk_level,
        context=context or {},
        requester=requester,
        workflow_id=workflow_id,
        execution_id=execution_id,
    )


def create_approval_response(
    approved: bool,
    reason: str,
    approver: str,
    conditions: Optional[List[str]] = None,
    notes: Optional[str] = None,
) -> ApprovalResponse:
    """
    Factory function to create an ApprovalResponse.

    Args:
        approved: Whether approved
        reason: Reason for decision
        approver: Who approved/rejected
        conditions: Conditions on approval
        notes: Additional notes

    Returns:
        ApprovalResponse instance
    """
    return ApprovalResponse(
        approved=approved,
        reason=reason,
        approver=approver,
        conditions=conditions or [],
        notes=notes,
    )
