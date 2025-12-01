# =============================================================================
# IPA Platform - Workflow Resume Service
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Human-in-the-Loop
#
# Service for resuming paused workflow executions.
# Provides:
#   - WorkflowResumeService: Resume paused workflows from checkpoints
#   - ResumeResult: Result of resume operations
#
# Handles workflow state restoration and continuation after human approval.
# =============================================================================

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.domain.checkpoints import CheckpointService, CheckpointStatus, CheckpointData
from src.domain.executions import ExecutionStateMachine, ExecutionStatus
from src.infrastructure.database.repositories.execution import ExecutionRepository

logger = logging.getLogger(__name__)


class ResumeStatus(str, Enum):
    """
    Status of resume operation.

    Values:
        SUCCESS: Workflow resumed successfully
        NOT_FOUND: Execution or checkpoint not found
        INVALID_STATE: Execution not in valid state for resume
        CHECKPOINT_PENDING: Checkpoint still awaiting approval
        CHECKPOINT_REJECTED: Checkpoint was rejected
        CHECKPOINT_EXPIRED: Checkpoint has expired
        ERROR: Resume failed with error
    """

    SUCCESS = "success"
    NOT_FOUND = "not_found"
    INVALID_STATE = "invalid_state"
    CHECKPOINT_PENDING = "checkpoint_pending"
    CHECKPOINT_REJECTED = "checkpoint_rejected"
    CHECKPOINT_EXPIRED = "checkpoint_expired"
    ERROR = "error"


@dataclass
class ResumeResult:
    """
    Result of a workflow resume operation.

    Attributes:
        status: Status of the resume operation
        execution_id: Execution UUID
        checkpoint_id: Checkpoint UUID (if applicable)
        message: Human-readable status message
        resumed_at: When the workflow was resumed
        next_node_id: Next node to execute (if resumed)
        restored_state: Restored workflow state (if any)
    """

    status: ResumeStatus
    execution_id: UUID
    checkpoint_id: Optional[UUID] = None
    message: str = ""
    resumed_at: Optional[datetime] = None
    next_node_id: Optional[str] = None
    restored_state: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "status": self.status.value,
            "execution_id": str(self.execution_id),
            "checkpoint_id": str(self.checkpoint_id) if self.checkpoint_id else None,
            "message": self.message,
            "resumed_at": self.resumed_at.isoformat() if self.resumed_at else None,
            "next_node_id": self.next_node_id,
            "restored_state": self.restored_state,
        }


class WorkflowResumeService:
    """
    Service for resuming paused workflow executions.

    Handles workflow continuation after human approval, including:
    - State restoration from checkpoints
    - Execution status updates
    - Validation of resume conditions

    Example:
        service = WorkflowResumeService(checkpoint_service, execution_repo)

        # Resume after approval
        result = await service.resume_from_checkpoint(
            execution_id=exec_id,
            checkpoint_id=checkpoint_id,
        )

        if result.status == ResumeStatus.SUCCESS:
            # Continue workflow from next_node_id
            pass
    """

    def __init__(
        self,
        checkpoint_service: CheckpointService,
        execution_repository: ExecutionRepository,
    ):
        """
        Initialize WorkflowResumeService.

        Args:
            checkpoint_service: Service for checkpoint operations
            execution_repository: Repository for execution operations
        """
        self._checkpoint_service = checkpoint_service
        self._execution_repo = execution_repository

    async def resume_from_checkpoint(
        self,
        execution_id: UUID,
        checkpoint_id: UUID,
    ) -> ResumeResult:
        """
        Resume workflow execution from a checkpoint.

        Validates that the checkpoint is approved and execution is paused,
        then restores state and marks execution as running.

        Args:
            execution_id: Execution UUID
            checkpoint_id: Approved checkpoint UUID

        Returns:
            ResumeResult with status and restored state
        """
        logger.info(
            f"Attempting to resume execution {execution_id} "
            f"from checkpoint {checkpoint_id}"
        )

        # Get execution
        execution = await self._execution_repo.get(execution_id)
        if execution is None:
            return ResumeResult(
                status=ResumeStatus.NOT_FOUND,
                execution_id=execution_id,
                checkpoint_id=checkpoint_id,
                message=f"Execution {execution_id} not found",
            )

        # Validate execution is paused
        if execution.status != ExecutionStatus.PAUSED.value:
            return ResumeResult(
                status=ResumeStatus.INVALID_STATE,
                execution_id=execution_id,
                checkpoint_id=checkpoint_id,
                message=f"Execution is in {execution.status} state, not paused",
            )

        # Get checkpoint
        checkpoint = await self._checkpoint_service.get_checkpoint(checkpoint_id)
        if checkpoint is None:
            return ResumeResult(
                status=ResumeStatus.NOT_FOUND,
                execution_id=execution_id,
                checkpoint_id=checkpoint_id,
                message=f"Checkpoint {checkpoint_id} not found",
            )

        # Validate checkpoint belongs to this execution
        if checkpoint.execution_id != execution_id:
            return ResumeResult(
                status=ResumeStatus.INVALID_STATE,
                execution_id=execution_id,
                checkpoint_id=checkpoint_id,
                message="Checkpoint does not belong to this execution",
            )

        # Check checkpoint status
        if checkpoint.status == CheckpointStatus.PENDING:
            return ResumeResult(
                status=ResumeStatus.CHECKPOINT_PENDING,
                execution_id=execution_id,
                checkpoint_id=checkpoint_id,
                message="Checkpoint is still awaiting approval",
            )

        if checkpoint.status == CheckpointStatus.REJECTED:
            return ResumeResult(
                status=ResumeStatus.CHECKPOINT_REJECTED,
                execution_id=execution_id,
                checkpoint_id=checkpoint_id,
                message="Checkpoint was rejected",
            )

        if checkpoint.status == CheckpointStatus.EXPIRED:
            return ResumeResult(
                status=ResumeStatus.CHECKPOINT_EXPIRED,
                execution_id=execution_id,
                checkpoint_id=checkpoint_id,
                message="Checkpoint has expired",
            )

        if checkpoint.status != CheckpointStatus.APPROVED:
            return ResumeResult(
                status=ResumeStatus.INVALID_STATE,
                execution_id=execution_id,
                checkpoint_id=checkpoint_id,
                message=f"Unexpected checkpoint status: {checkpoint.status}",
            )

        # Resume execution
        try:
            await self._execution_repo.resume(execution_id)

            # Extract restored state from checkpoint
            restored_state = None
            payload = checkpoint.payload or {}

            if payload.get("type") == "state_checkpoint":
                restored_state = payload.get("state", {})
            elif payload.get("type") == "human_approval":
                # Include approval response data
                restored_state = {
                    "approval_response": checkpoint.response,
                    "approved_content": payload.get("content"),
                    "iteration": payload.get("iteration", 1),
                }

            logger.info(
                f"Successfully resumed execution {execution_id} "
                f"from checkpoint {checkpoint_id}"
            )

            return ResumeResult(
                status=ResumeStatus.SUCCESS,
                execution_id=execution_id,
                checkpoint_id=checkpoint_id,
                message="Workflow resumed successfully",
                resumed_at=datetime.utcnow(),
                next_node_id=checkpoint.node_id,
                restored_state=restored_state,
            )

        except Exception as e:
            logger.error(f"Error resuming execution {execution_id}: {e}")
            return ResumeResult(
                status=ResumeStatus.ERROR,
                execution_id=execution_id,
                checkpoint_id=checkpoint_id,
                message=f"Resume failed: {str(e)}",
            )

    async def resume_with_approval(
        self,
        execution_id: UUID,
        user_id: UUID,
        response: Optional[Dict[str, Any]] = None,
    ) -> ResumeResult:
        """
        Approve pending checkpoint and resume workflow.

        Convenience method that finds the latest pending checkpoint,
        approves it, and resumes execution.

        Args:
            execution_id: Execution UUID
            user_id: User approving the checkpoint
            response: Optional response data

        Returns:
            ResumeResult with status
        """
        logger.info(
            f"Resuming execution {execution_id} with approval from user {user_id}"
        )

        # Find pending checkpoint for execution
        pending = await self._checkpoint_service.get_pending_approvals(
            execution_id=execution_id,
            limit=1,
        )

        if not pending:
            return ResumeResult(
                status=ResumeStatus.NOT_FOUND,
                execution_id=execution_id,
                message="No pending checkpoint found for this execution",
            )

        checkpoint = pending[0]

        # Approve the checkpoint
        approved = await self._checkpoint_service.approve_checkpoint(
            checkpoint_id=checkpoint.id,
            user_id=user_id,
            response=response,
        )

        if approved is None:
            return ResumeResult(
                status=ResumeStatus.ERROR,
                execution_id=execution_id,
                checkpoint_id=checkpoint.id,
                message="Failed to approve checkpoint",
            )

        # Resume from checkpoint
        return await self.resume_from_checkpoint(execution_id, checkpoint.id)

    async def get_resume_status(
        self,
        execution_id: UUID,
    ) -> Dict[str, Any]:
        """
        Get the resume status for an execution.

        Returns information about pending checkpoints and whether
        the execution can be resumed.

        Args:
            execution_id: Execution UUID

        Returns:
            Dictionary with resume status information
        """
        execution = await self._execution_repo.get(execution_id)

        if execution is None:
            return {
                "can_resume": False,
                "reason": "Execution not found",
            }

        if execution.status != ExecutionStatus.PAUSED.value:
            return {
                "can_resume": False,
                "reason": f"Execution is in {execution.status} state",
                "current_status": execution.status,
            }

        # Get pending checkpoints
        pending = await self._checkpoint_service.get_pending_approvals(
            execution_id=execution_id,
        )

        # Get approved checkpoints not yet processed
        all_checkpoints = await self._checkpoint_service.get_checkpoints_by_execution(
            execution_id=execution_id,
        )

        approved_checkpoints = [
            cp for cp in all_checkpoints
            if cp.status == CheckpointStatus.APPROVED
        ]

        return {
            "can_resume": len(approved_checkpoints) > 0,
            "reason": "Approved checkpoint available" if approved_checkpoints else "Awaiting approval",
            "current_status": execution.status,
            "pending_count": len(pending),
            "approved_count": len(approved_checkpoints),
            "pending_checkpoints": [
                {
                    "id": str(cp.id),
                    "node_id": cp.node_id,
                    "created_at": cp.created_at.isoformat() if cp.created_at else None,
                }
                for cp in pending
            ],
        }

    async def cancel_paused_execution(
        self,
        execution_id: UUID,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Cancel a paused execution.

        Args:
            execution_id: Execution UUID
            reason: Optional cancellation reason

        Returns:
            True if cancelled, False otherwise
        """
        execution = await self._execution_repo.get(execution_id)

        if execution is None:
            return False

        if execution.status != ExecutionStatus.PAUSED.value:
            logger.warning(
                f"Cannot cancel execution {execution_id} "
                f"in {execution.status} state"
            )
            return False

        # Cancel the execution
        cancelled = await self._execution_repo.cancel(execution_id)

        if cancelled:
            logger.info(
                f"Cancelled paused execution {execution_id}: {reason or 'No reason'}"
            )
            return True

        return False
