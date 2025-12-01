# =============================================================================
# IPA Platform - Approval Gateway Executor
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Human-in-the-Loop
#
# Human approval gateway executor for workflow pausing.
# Provides:
#   - HumanApprovalRequest: Data structure for approval requests
#   - ApprovalResponse: Response from human approval
#   - ApprovalGateway: Executor for approval workflow nodes
#
# The approval gateway pauses workflow execution, creates a checkpoint,
# and waits for human approval before continuing.
# =============================================================================

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable
from uuid import UUID

from src.domain.checkpoints import CheckpointService, CheckpointStatus, CheckpointData

logger = logging.getLogger(__name__)


class ApprovalAction(str, Enum):
    """
    Possible approval actions.

    Values:
        APPROVE: Continue workflow execution
        REJECT: Stop workflow execution
        MODIFY: Modify response and continue
        RETRY: Request agent to retry with feedback
    """

    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"
    RETRY = "retry"


@dataclass
class HumanApprovalRequest:
    """
    Data structure for human approval requests.

    Contains all information needed for a human reviewer to make
    an informed decision about the agent's output.

    Attributes:
        execution_id: Parent workflow execution UUID
        node_id: ID of the approval gateway node
        agent_id: ID of the agent that produced the output
        prompt: Original prompt given to the agent
        content: Agent's output content to review
        context: Additional context for the reviewer
        iteration: Number of times this content has been reviewed
        metadata: Additional metadata about the request
    """

    execution_id: UUID
    node_id: str
    agent_id: Optional[UUID] = None
    prompt: str = ""
    content: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    iteration: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "execution_id": str(self.execution_id),
            "node_id": self.node_id,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "prompt": self.prompt,
            "content": self.content,
            "context": self.context,
            "iteration": self.iteration,
            "metadata": self.metadata,
        }

    def to_checkpoint_payload(self) -> Dict[str, Any]:
        """Convert to checkpoint payload format."""
        return {
            "type": "human_approval",
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "prompt": self.prompt,
            "content": self.content,
            "context": self.context,
            "iteration": self.iteration,
            "metadata": self.metadata,
        }


@dataclass
class ApprovalResponse:
    """
    Response from human approval.

    Contains the human's decision and any modifications or feedback.

    Attributes:
        action: The approval action taken
        user_id: User who made the decision
        modified_content: Modified content (if action is MODIFY)
        feedback: Feedback for the agent (if action is RETRY)
        notes: Additional notes from reviewer
        responded_at: When the response was given
    """

    action: ApprovalAction
    user_id: UUID
    modified_content: Optional[str] = None
    feedback: Optional[str] = None
    notes: Optional[str] = None
    responded_at: Optional[datetime] = None

    def __post_init__(self):
        if self.responded_at is None:
            self.responded_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "action": self.action.value,
            "user_id": str(self.user_id),
            "modified_content": self.modified_content,
            "feedback": self.feedback,
            "notes": self.notes,
            "responded_at": self.responded_at.isoformat() if self.responded_at else None,
        }


class ApprovalGateway:
    """
    Approval gateway executor for human-in-the-loop workflows.

    Handles the creation of checkpoints when human approval is needed,
    and processes approval responses to continue or stop workflow execution.

    Lifecycle:
        1. on_agent_response() - Called when agent produces output
        2. Creates checkpoint and pauses workflow
        3. Human reviews and responds via checkpoint API
        4. on_human_feedback() - Called when human responds
        5. on_checkpoint_restore() - Restores state for continuation

    Example:
        gateway = ApprovalGateway(checkpoint_service)

        # When agent produces output
        checkpoint_id = await gateway.on_agent_response(
            HumanApprovalRequest(
                execution_id=exec_id,
                node_id="review-gate",
                content="Agent's draft response",
            )
        )

        # Workflow pauses here...

        # When human approves
        response = ApprovalResponse(
            action=ApprovalAction.APPROVE,
            user_id=reviewer_id,
        )
        result = await gateway.on_human_feedback(checkpoint_id, response)
    """

    def __init__(
        self,
        checkpoint_service: CheckpointService,
        timeout_hours: int = 24,
        max_iterations: int = 3,
    ):
        """
        Initialize ApprovalGateway.

        Args:
            checkpoint_service: Service for checkpoint operations
            timeout_hours: Hours before approval request expires
            max_iterations: Maximum retry iterations allowed
        """
        self._checkpoint_service = checkpoint_service
        self._timeout_hours = timeout_hours
        self._max_iterations = max_iterations
        self._pending_requests: Dict[UUID, HumanApprovalRequest] = {}

    async def on_agent_response(
        self,
        request: HumanApprovalRequest,
    ) -> UUID:
        """
        Handle agent response by creating approval checkpoint.

        Called when an agent produces output that requires human review.
        Creates a checkpoint and returns the checkpoint ID for tracking.

        Args:
            request: Human approval request with agent output

        Returns:
            Checkpoint UUID for tracking the approval

        Raises:
            ValueError: If max iterations exceeded
        """
        if request.iteration > self._max_iterations:
            raise ValueError(
                f"Maximum approval iterations ({self._max_iterations}) exceeded. "
                f"Consider adjusting agent instructions or accepting the output."
            )

        logger.info(
            f"Creating approval checkpoint for execution {request.execution_id} "
            f"at node {request.node_id}, iteration {request.iteration}"
        )

        # Create checkpoint for human review
        checkpoint = await self._checkpoint_service.create_checkpoint(
            execution_id=request.execution_id,
            node_id=request.node_id,
            payload=request.to_checkpoint_payload(),
            timeout_hours=self._timeout_hours,
            notes=f"Approval request iteration {request.iteration}",
        )

        # Store request for later retrieval
        self._pending_requests[checkpoint.id] = request

        logger.info(f"Created checkpoint {checkpoint.id} for approval")
        return checkpoint.id

    async def on_human_feedback(
        self,
        checkpoint_id: UUID,
        response: ApprovalResponse,
    ) -> Dict[str, Any]:
        """
        Process human feedback and update checkpoint.

        Handles the different approval actions and returns
        the result for workflow continuation.

        Args:
            checkpoint_id: Checkpoint UUID
            response: Human's approval response

        Returns:
            Dictionary with action result and continuation data

        Raises:
            ValueError: If checkpoint not found or already processed
        """
        logger.info(
            f"Processing approval response for checkpoint {checkpoint_id}: "
            f"action={response.action.value}"
        )

        # Get original request
        original_request = self._pending_requests.get(checkpoint_id)

        if response.action == ApprovalAction.APPROVE:
            # Approve the checkpoint
            await self._checkpoint_service.approve_checkpoint(
                checkpoint_id=checkpoint_id,
                user_id=response.user_id,
                response=response.to_dict(),
            )

            return {
                "action": "continue",
                "content": original_request.content if original_request else None,
                "checkpoint_id": str(checkpoint_id),
                "approved_by": str(response.user_id),
            }

        elif response.action == ApprovalAction.REJECT:
            # Reject the checkpoint
            await self._checkpoint_service.reject_checkpoint(
                checkpoint_id=checkpoint_id,
                user_id=response.user_id,
                reason=response.notes or "Rejected by reviewer",
            )

            return {
                "action": "stop",
                "reason": response.notes or "Rejected by reviewer",
                "checkpoint_id": str(checkpoint_id),
                "rejected_by": str(response.user_id),
            }

        elif response.action == ApprovalAction.MODIFY:
            # Approve with modifications
            await self._checkpoint_service.approve_checkpoint(
                checkpoint_id=checkpoint_id,
                user_id=response.user_id,
                response={
                    **response.to_dict(),
                    "original_content": original_request.content if original_request else None,
                },
            )

            return {
                "action": "continue",
                "content": response.modified_content,
                "checkpoint_id": str(checkpoint_id),
                "modified_by": str(response.user_id),
            }

        elif response.action == ApprovalAction.RETRY:
            # Mark checkpoint but request retry
            await self._checkpoint_service.reject_checkpoint(
                checkpoint_id=checkpoint_id,
                user_id=response.user_id,
                reason=f"Retry requested: {response.feedback}",
                response=response.to_dict(),
            )

            return {
                "action": "retry",
                "feedback": response.feedback,
                "iteration": original_request.iteration + 1 if original_request else 2,
                "checkpoint_id": str(checkpoint_id),
                "requested_by": str(response.user_id),
            }

        else:
            raise ValueError(f"Unknown approval action: {response.action}")

    async def on_checkpoint_save(
        self,
        execution_id: UUID,
        node_id: str,
        state: Dict[str, Any],
    ) -> UUID:
        """
        Save workflow state at checkpoint.

        Called when workflow needs to persist its state before pausing.

        Args:
            execution_id: Execution UUID
            node_id: Current node ID
            state: Workflow state to persist

        Returns:
            Checkpoint UUID
        """
        checkpoint = await self._checkpoint_service.create_checkpoint(
            execution_id=execution_id,
            node_id=node_id,
            payload={
                "type": "state_checkpoint",
                "state": state,
            },
            timeout_hours=self._timeout_hours * 2,  # State checkpoints last longer
            notes="Workflow state checkpoint",
        )

        logger.info(f"Saved state checkpoint {checkpoint.id} for execution {execution_id}")
        return checkpoint.id

    async def on_checkpoint_restore(
        self,
        checkpoint_id: UUID,
    ) -> Optional[Dict[str, Any]]:
        """
        Restore workflow state from checkpoint.

        Called when resuming a paused workflow.

        Args:
            checkpoint_id: Checkpoint UUID to restore from

        Returns:
            Restored state data or None if not found
        """
        checkpoint = await self._checkpoint_service.get_checkpoint(checkpoint_id)

        if checkpoint is None:
            logger.warning(f"Checkpoint {checkpoint_id} not found for restore")
            return None

        if checkpoint.status != CheckpointStatus.APPROVED:
            logger.warning(
                f"Cannot restore from checkpoint {checkpoint_id} "
                f"in {checkpoint.status} status"
            )
            return None

        payload = checkpoint.payload or {}
        if payload.get("type") == "state_checkpoint":
            return payload.get("state", {})

        return payload

    async def get_pending_approvals_for_execution(
        self,
        execution_id: UUID,
    ) -> List[CheckpointData]:
        """
        Get pending approval requests for an execution.

        Args:
            execution_id: Execution UUID

        Returns:
            List of pending checkpoints
        """
        return await self._checkpoint_service.get_pending_approvals(
            execution_id=execution_id,
        )

    def clear_pending_request(self, checkpoint_id: UUID) -> None:
        """
        Clear a pending request from memory.

        Args:
            checkpoint_id: Checkpoint UUID
        """
        if checkpoint_id in self._pending_requests:
            del self._pending_requests[checkpoint_id]
