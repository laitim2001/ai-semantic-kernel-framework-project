# =============================================================================
# IPA Platform - Checkpoint Service
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Human-in-the-Loop
#
# Service layer for checkpoint management.
# Provides:
#   - CheckpointStatus: Status enumeration
#   - CheckpointData: Checkpoint data structure
#   - CheckpointService: Business logic for checkpoint operations
#
# The service layer orchestrates checkpoint operations and provides
# a clean interface for API endpoints and workflow integration.
# =============================================================================

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.infrastructure.database.repositories.checkpoint import CheckpointRepository

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
    Service for checkpoint business logic.

    Provides methods for:
        - Creating checkpoints for human approval
        - Listing pending approvals
        - Approving/rejecting checkpoints
        - Managing checkpoint lifecycle

    Example:
        service = CheckpointService(repository)

        # Create a checkpoint
        checkpoint = await service.create_checkpoint(
            execution_id=exec_id,
            node_id="approval-gate",
            payload={"draft": "Please review this response."},
        )

        # Get pending approvals
        pending = await service.get_pending_approvals(limit=10)

        # Approve a checkpoint
        approved = await service.approve_checkpoint(
            checkpoint_id=checkpoint.id,
            user_id=approver_id,
            response={"action": "proceed", "comment": "Looks good!"},
        )
    """

    def __init__(
        self,
        repository: CheckpointRepository,
        default_timeout_hours: int = 24,
    ):
        """
        Initialize checkpoint service.

        Args:
            repository: CheckpointRepository instance
            default_timeout_hours: Default checkpoint timeout in hours
        """
        self._repository = repository
        self._default_timeout_hours = default_timeout_hours

    async def create_checkpoint(
        self,
        execution_id: UUID,
        node_id: str,
        payload: Dict[str, Any],
        timeout_hours: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> CheckpointData:
        """
        Create a new checkpoint for human approval.

        Args:
            execution_id: Parent execution UUID
            node_id: Workflow node creating the checkpoint
            payload: Data to be reviewed by human
            timeout_hours: Hours until checkpoint expires (default from config)
            notes: Optional notes or context

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
        user_id: UUID,
        response: Optional[Dict[str, Any]] = None,
        feedback: Optional[str] = None,
    ) -> Optional[CheckpointData]:
        """
        Approve a pending checkpoint.

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
        user_id: UUID,
        reason: Optional[str] = None,
        response: Optional[Dict[str, Any]] = None,
    ) -> Optional[CheckpointData]:
        """
        Reject a pending checkpoint.

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
