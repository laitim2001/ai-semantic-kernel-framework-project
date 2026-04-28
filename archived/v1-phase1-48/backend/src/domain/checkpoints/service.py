# =============================================================================
# IPA Platform - Checkpoint Service
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Human-in-the-Loop
# Sprint 28: Refactored for Official API Migration
#
# Service layer for checkpoint STORAGE management.
# Provides:
#   - CheckpointStatus: Status enumeration
#   - CheckpointData: Checkpoint data structure
#   - CheckpointService: Business logic for checkpoint operations
#
# IMPORTANT (Sprint 28):
#   - Storage operations remain in CheckpointService
#   - Approval operations are DEPRECATED - use HumanApprovalExecutor instead
#   - approve_checkpoint() and reject_checkpoint() emit deprecation warnings
#   - For new code, use:
#       from src.integrations.agent_framework.core import HumanApprovalExecutor
#
# The service layer orchestrates checkpoint operations and provides
# a clean interface for API endpoints and workflow integration.
# =============================================================================

import logging
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
from uuid import UUID

from src.infrastructure.database.repositories.checkpoint import CheckpointRepository

# Type checking imports to avoid circular dependencies
if TYPE_CHECKING:
    from src.integrations.agent_framework.core.approval import (
        HumanApprovalExecutor,
        ApprovalRequest,
        ApprovalResponse,
    )

logger = logging.getLogger(__name__)


class CheckpointStatus(str, Enum):
    """
    Checkpoint status enumeration.

    Status lifecycle:
        PENDING → APPROVED (human approved)
        PENDING → REJECTED (human rejected)
        PENDING → EXPIRED (timeout reached)

    Values:
        PENDING: Waiting for human response
        APPROVED: Human approved continuation
        REJECTED: Human rejected, workflow will terminate/retry
        EXPIRED: No response within timeout period
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class CheckpointData:
    """
    Checkpoint data structure for API responses.

    Attributes:
        id: Checkpoint UUID
        execution_id: Parent execution UUID
        node_id: Workflow node that created the checkpoint
        status: Current checkpoint status
        payload: Data to review
        response: Human response (if any)
        responded_by: User who responded
        responded_at: When response was received
        expires_at: When checkpoint will expire
        created_at: When checkpoint was created
        notes: Additional notes or metadata
    """

    id: UUID
    execution_id: UUID
    node_id: str
    status: CheckpointStatus
    payload: Dict[str, Any] = field(default_factory=dict)
    response: Optional[Dict[str, Any]] = None
    responded_by: Optional[UUID] = None
    responded_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    notes: Optional[str] = None

    @classmethod
    def from_model(cls, checkpoint) -> "CheckpointData":
        """
        Create CheckpointData from database model.

        Args:
            checkpoint: Checkpoint database model instance

        Returns:
            CheckpointData instance
        """
        try:
            status = CheckpointStatus(checkpoint.status)
        except ValueError:
            status = CheckpointStatus.PENDING

        return cls(
            id=checkpoint.id,
            execution_id=checkpoint.execution_id,
            node_id=checkpoint.node_id,
            status=status,
            payload=checkpoint.payload or {},
            response=checkpoint.response,
            responded_by=checkpoint.responded_by,
            responded_at=checkpoint.responded_at,
            expires_at=checkpoint.expires_at,
            created_at=checkpoint.created_at,
            notes=checkpoint.notes,
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "id": str(self.id),
            "execution_id": str(self.execution_id),
            "node_id": self.node_id,
            "status": self.status.value,
            "payload": self.payload,
            "response": self.response,
            "responded_by": str(self.responded_by) if self.responded_by else None,
            "responded_at": self.responded_at.isoformat() if self.responded_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "notes": self.notes,
        }


class CheckpointService:
    """
    Service for checkpoint STORAGE operations.

    Sprint 28 Update:
        - Storage operations (create, get, list, delete) remain here
        - Approval operations (approve, reject) are DEPRECATED
        - For approval logic, use HumanApprovalExecutor from official API

    Provides methods for:
        - Creating checkpoints for human approval
        - Listing pending approvals
        - Approving/rejecting checkpoints (DEPRECATED)
        - Managing checkpoint lifecycle

    Example (Storage):
        service = CheckpointService(repository)

        # Create a checkpoint
        checkpoint = await service.create_checkpoint(
            execution_id=exec_id,
            node_id="approval-gate",
            payload={"draft": "Please review this response."},
        )

        # Get pending approvals
        pending = await service.get_pending_approvals(limit=10)

    Example (NEW - Official API):
        from src.integrations.agent_framework.core import (
            HumanApprovalExecutor,
            ApprovalRequest,
            ApprovalResponse,
        )

        executor = HumanApprovalExecutor(name="approval-gate")

        # In workflow
        request = ApprovalRequest(
            action="approve_draft",
            details="Please review this response.",
            risk_level="medium",
        )

        # Later, respond via workflow
        await workflow.respond(
            executor_name="approval-gate",
            response=ApprovalResponse(
                approved=True,
                reason="Looks good!",
                approver="user@company.com",
            )
        )
    """

    def __init__(
        self,
        repository: CheckpointRepository,
        default_timeout_hours: int = 24,
        approval_executor: Optional["HumanApprovalExecutor"] = None,
    ):
        """
        Initialize checkpoint service.

        Args:
            repository: CheckpointRepository instance
            default_timeout_hours: Default checkpoint timeout in hours
            approval_executor: Optional HumanApprovalExecutor for new API integration
        """
        self._repository = repository
        self._default_timeout_hours = default_timeout_hours
        self._approval_executor = approval_executor

    async def create_checkpoint(
        self,
        execution_id: UUID,
        node_id: str,
        payload: Dict[str, Any],
        timeout_hours: Optional[int] = None,
        notes: Optional[str] = None,
        step: str = "0",
        checkpoint_type: str = "approval",
        state: Optional[Dict[str, Any]] = None,
    ) -> CheckpointData:
        """
        Create a new checkpoint for human approval.

        Args:
            execution_id: Parent execution UUID
            node_id: Workflow node creating the checkpoint
            payload: Data to be reviewed by human
            timeout_hours: Hours until checkpoint expires (default from config)
            notes: Optional notes or context
            step: Step identifier in workflow (default "0")
            checkpoint_type: Type of checkpoint (approval, review, input)
            state: Current workflow state

        Returns:
            Created checkpoint data
        """
        # Calculate expiration time
        timeout = timeout_hours or self._default_timeout_hours
        expires_at = datetime.utcnow() + timedelta(hours=timeout)

        checkpoint = await self._repository.create(
            execution_id=execution_id,
            node_id=node_id,
            status=CheckpointStatus.PENDING.value,
            payload=payload,
            expires_at=expires_at,
            notes=notes,
            step=step,
            checkpoint_type=checkpoint_type,
            state=state or {},
        )

        logger.info(
            f"Created checkpoint {checkpoint.id} for execution {execution_id} "
            f"at node {node_id}, expires at {expires_at}"
        )

        return CheckpointData.from_model(checkpoint)

    async def get_checkpoint(self, checkpoint_id: UUID) -> Optional[CheckpointData]:
        """
        Get a checkpoint by ID.

        Args:
            checkpoint_id: Checkpoint UUID

        Returns:
            Checkpoint data or None if not found
        """
        checkpoint = await self._repository.get(checkpoint_id)
        if checkpoint is None:
            return None

        return CheckpointData.from_model(checkpoint)

    async def get_pending_approvals(
        self,
        limit: int = 50,
        execution_id: Optional[UUID] = None,
    ) -> List[CheckpointData]:
        """
        Get pending checkpoints awaiting approval.

        Args:
            limit: Maximum number to return
            execution_id: Optional filter by execution

        Returns:
            List of pending checkpoint data
        """
        checkpoints = await self._repository.get_pending(
            limit=limit,
            execution_id=execution_id,
        )

        return [CheckpointData.from_model(cp) for cp in checkpoints]

    async def get_checkpoints_by_execution(
        self,
        execution_id: UUID,
        include_expired: bool = False,
    ) -> List[CheckpointData]:
        """
        Get all checkpoints for an execution.

        Args:
            execution_id: Execution UUID
            include_expired: Whether to include expired checkpoints

        Returns:
            List of checkpoint data
        """
        checkpoints = await self._repository.get_by_execution(
            execution_id=execution_id,
            include_expired=include_expired,
        )

        return [CheckpointData.from_model(cp) for cp in checkpoints]

    async def approve_checkpoint(
        self,
        checkpoint_id: UUID,
        user_id: Optional[UUID] = None,
        response: Optional[Dict[str, Any]] = None,
        feedback: Optional[str] = None,
    ) -> Optional[CheckpointData]:
        """
        Approve a pending checkpoint.

        .. deprecated::
            Use HumanApprovalExecutor with workflow.respond() instead.
            See Sprint 28 migration guide.

        Args:
            checkpoint_id: Checkpoint UUID
            user_id: User approving the checkpoint
            response: Optional response data (e.g., modifications)
            feedback: Optional feedback text

        Returns:
            Updated checkpoint data or None if not found

        Raises:
            ValueError: If checkpoint is not in PENDING status
        """
        warnings.warn(
            "approve_checkpoint() is deprecated. "
            "Use HumanApprovalExecutor with workflow.respond() instead. "
            "See: from src.integrations.agent_framework.core import HumanApprovalExecutor",
            DeprecationWarning,
            stacklevel=2,
        )

        checkpoint = await self._repository.get(checkpoint_id)
        if checkpoint is None:
            return None

        if checkpoint.status != CheckpointStatus.PENDING.value:
            raise ValueError(
                f"Cannot approve checkpoint in {checkpoint.status} status. "
                f"Only PENDING checkpoints can be approved."
            )

        # Build response data
        response_data = response or {}
        if feedback:
            response_data["feedback"] = feedback

        updated = await self._repository.update_status(
            checkpoint_id=checkpoint_id,
            status=CheckpointStatus.APPROVED.value,
            response=response_data,
            responded_by=user_id,
        )

        if updated:
            logger.info(
                f"Checkpoint {checkpoint_id} approved by user {user_id}"
            )
            return CheckpointData.from_model(updated)

        return None

    async def reject_checkpoint(
        self,
        checkpoint_id: UUID,
        user_id: Optional[UUID] = None,
        reason: Optional[str] = None,
        response: Optional[Dict[str, Any]] = None,
    ) -> Optional[CheckpointData]:
        """
        Reject a pending checkpoint.

        .. deprecated::
            Use HumanApprovalExecutor with workflow.respond() instead.
            See Sprint 28 migration guide.

        Args:
            checkpoint_id: Checkpoint UUID
            user_id: User rejecting the checkpoint
            reason: Reason for rejection
            response: Optional additional response data

        Returns:
            Updated checkpoint data or None if not found

        Raises:
            ValueError: If checkpoint is not in PENDING status
        """
        warnings.warn(
            "reject_checkpoint() is deprecated. "
            "Use HumanApprovalExecutor with workflow.respond() instead. "
            "See: from src.integrations.agent_framework.core import HumanApprovalExecutor",
            DeprecationWarning,
            stacklevel=2,
        )

        checkpoint = await self._repository.get(checkpoint_id)
        if checkpoint is None:
            return None

        if checkpoint.status != CheckpointStatus.PENDING.value:
            raise ValueError(
                f"Cannot reject checkpoint in {checkpoint.status} status. "
                f"Only PENDING checkpoints can be rejected."
            )

        # Build response data
        response_data = response or {}
        if reason:
            response_data["rejection_reason"] = reason

        updated = await self._repository.update_status(
            checkpoint_id=checkpoint_id,
            status=CheckpointStatus.REJECTED.value,
            response=response_data,
            responded_by=user_id,
        )

        if updated:
            logger.info(
                f"Checkpoint {checkpoint_id} rejected by user {user_id}: {reason}"
            )
            return CheckpointData.from_model(updated)

        return None

    async def expire_old_checkpoints(self) -> int:
        """
        Expire checkpoints past their expiration time.

        Returns:
            Number of checkpoints expired
        """
        count = await self._repository.expire_old()

        if count > 0:
            logger.info(f"Expired {count} old checkpoints")

        return count

    async def get_stats(
        self,
        execution_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Get checkpoint statistics.

        Args:
            execution_id: Optional filter by execution

        Returns:
            Dictionary with statistics
        """
        return await self._repository.get_stats(execution_id)

    async def delete_checkpoint(self, checkpoint_id: UUID) -> bool:
        """
        Delete a checkpoint.

        Args:
            checkpoint_id: Checkpoint UUID

        Returns:
            True if deleted, False if not found
        """
        return await self._repository.delete(checkpoint_id)

    # =========================================================================
    # Sprint 28: HumanApprovalExecutor Integration Methods
    # =========================================================================

    def set_approval_executor(
        self,
        executor: "HumanApprovalExecutor",
    ) -> None:
        """
        Set the HumanApprovalExecutor for official API integration.

        Args:
            executor: HumanApprovalExecutor instance
        """
        self._approval_executor = executor
        logger.info(
            f"CheckpointService integrated with HumanApprovalExecutor: {executor.name}"
        )

    def get_approval_executor(self) -> Optional["HumanApprovalExecutor"]:
        """
        Get the configured HumanApprovalExecutor.

        Returns:
            HumanApprovalExecutor or None if not configured
        """
        return self._approval_executor

    async def create_checkpoint_with_approval(
        self,
        execution_id: UUID,
        node_id: str,
        payload: Dict[str, Any],
        timeout_hours: Optional[int] = None,
        notes: Optional[str] = None,
        action: Optional[str] = None,
        risk_level: Optional[str] = None,
    ) -> CheckpointData:
        """
        Create checkpoint and register with HumanApprovalExecutor.

        This method bridges the legacy checkpoint storage with the new
        HumanApprovalExecutor system. It:
        1. Creates a checkpoint in the database (storage)
        2. Registers an approval request with HumanApprovalExecutor (if configured)

        Args:
            execution_id: Parent execution UUID
            node_id: Workflow node creating the checkpoint
            payload: Data to be reviewed by human
            timeout_hours: Hours until checkpoint expires
            notes: Optional notes or context
            action: Optional action description for approval request
            risk_level: Optional risk level (low, medium, high, critical)

        Returns:
            Created checkpoint data
        """
        # Create checkpoint in storage
        checkpoint = await self.create_checkpoint(
            execution_id=execution_id,
            node_id=node_id,
            payload=payload,
            timeout_hours=timeout_hours,
            notes=notes,
        )

        # Register with approval executor if configured
        if self._approval_executor:
            try:
                # Import here to avoid circular dependency
                from src.integrations.agent_framework.core.approval import (
                    ApprovalRequest,
                    RiskLevel,
                )

                # Build approval request
                request = ApprovalRequest(
                    action=action or f"approve_{node_id}",
                    details=notes or str(payload),
                    risk_level=risk_level or "medium",
                    context={
                        "checkpoint_id": str(checkpoint.id),
                        "execution_id": str(execution_id),
                        "node_id": node_id,
                        "payload": payload,
                    },
                    requester="checkpoint_service",
                    workflow_id=None,  # Can be set by caller
                    execution_id=str(execution_id),
                )

                # Register with executor
                await self._approval_executor.on_request_created(request, None)

                logger.info(
                    f"Checkpoint {checkpoint.id} registered with approval executor"
                )
            except Exception as e:
                logger.error(
                    f"Failed to register checkpoint with approval executor: {e}"
                )

        return checkpoint

    async def handle_approval_response(
        self,
        checkpoint_id: UUID,
        approved: bool,
        approver: str,
        reason: str,
        conditions: Optional[List[str]] = None,
    ) -> Optional[CheckpointData]:
        """
        Handle approval response and update checkpoint.

        This method bridges the HumanApprovalExecutor response back to
        the legacy checkpoint storage system.

        Args:
            checkpoint_id: Checkpoint UUID
            approved: Whether approved
            approver: Who approved/rejected
            reason: Reason for decision
            conditions: Optional conditions on approval

        Returns:
            Updated checkpoint data or None if not found
        """
        checkpoint = await self._repository.get(checkpoint_id)
        if checkpoint is None:
            return None

        if checkpoint.status != CheckpointStatus.PENDING.value:
            logger.warning(
                f"Checkpoint {checkpoint_id} not in PENDING status, "
                f"current status: {checkpoint.status}"
            )
            return None

        # Build response data
        response_data = {
            "approved": approved,
            "reason": reason,
            "conditions": conditions or [],
        }

        # Update status
        new_status = (
            CheckpointStatus.APPROVED.value if approved
            else CheckpointStatus.REJECTED.value
        )

        updated = await self._repository.update_status(
            checkpoint_id=checkpoint_id,
            status=new_status,
            response=response_data,
            responded_by=None,  # Using approver string instead of UUID
        )

        if updated:
            # Update notes with approver info
            if updated.notes:
                updated.notes = f"{updated.notes}\nApproved by: {approver}"
            else:
                updated.notes = f"Approved by: {approver}"

            logger.info(
                f"Checkpoint {checkpoint_id} "
                f"{'approved' if approved else 'rejected'} "
                f"via HumanApprovalExecutor by {approver}"
            )
            return CheckpointData.from_model(updated)

        return None
