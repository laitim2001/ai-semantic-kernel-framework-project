# =============================================================================
# IPA Platform - Handoff Controller
# =============================================================================
# Sprint 8: Agent Handoff & Collaboration (Phase 2)
#
# Core handoff controller for managing Agent task transfers.
# Supports three handoff policies:
#   - IMMEDIATE: Immediate transfer without waiting
#   - GRACEFUL: Wait for current task completion before transfer
#   - CONDITIONAL: Transfer based on condition evaluation
#
# References:
#   - Microsoft Agent Framework Handoff API concepts
#   - Sprint 8 Plan: docs/03-implementation/sprint-planning/phase-2/sprint-8-plan.md
# =============================================================================

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class HandoffStatus(str, Enum):
    """
    Handoff execution status.

    States:
        INITIATED: Handoff request created
        VALIDATING: Validating conditions and agent availability
        TRANSFERRING: Context transfer in progress
        COMPLETED: Handoff completed successfully
        FAILED: Handoff failed
        CANCELLED: Handoff was cancelled
        ROLLED_BACK: Handoff was rolled back after failure
    """
    INITIATED = "initiated"
    VALIDATING = "validating"
    TRANSFERRING = "transferring"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


class HandoffPolicy(str, Enum):
    """
    Handoff execution policy.

    Policies:
        IMMEDIATE: Transfer immediately without waiting for current task
        GRACEFUL: Wait for current task completion before transfer
        CONDITIONAL: Evaluate conditions before deciding to transfer
    """
    IMMEDIATE = "immediate"
    GRACEFUL = "graceful"
    CONDITIONAL = "conditional"


@dataclass
class HandoffContext:
    """
    Context data to be transferred during handoff.

    Attributes:
        task_id: Identifier of the task being transferred
        task_state: Current state of the task (variables, progress, etc.)
        conversation_history: History of conversation/interactions
        metadata: Additional metadata for the handoff
        priority: Task priority level (higher = more important)
        timeout: Maximum time (seconds) to complete handoff
    """
    task_id: str
    task_state: Dict[str, Any]
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    timeout: int = 300  # seconds


@dataclass
class HandoffRequest:
    """
    Handoff request containing all transfer information.

    Attributes:
        id: Unique identifier for this handoff request
        source_agent_id: Agent initiating the handoff
        target_agent_id: Agent receiving the handoff
        context: Context data to transfer
        policy: Handoff execution policy
        reason: Reason for the handoff
        conditions: Optional conditions for CONDITIONAL policy
        created_at: Timestamp of request creation
    """
    id: UUID = field(default_factory=uuid4)
    source_agent_id: Optional[UUID] = None
    target_agent_id: Optional[UUID] = None
    context: Optional[HandoffContext] = None
    policy: HandoffPolicy = HandoffPolicy.GRACEFUL
    reason: str = ""
    conditions: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class HandoffResult:
    """
    Result of handoff execution.

    Attributes:
        request_id: ID of the original request
        status: Final status of the handoff
        source_agent_id: Source agent that initiated handoff
        target_agent_id: Target agent that received handoff
        started_at: When handoff execution started
        completed_at: When handoff completed
        duration_ms: Total duration in milliseconds
        error: Error message if failed
        rollback_performed: Whether rollback was executed
        transferred_context: Summary of transferred context
    """
    request_id: UUID
    status: HandoffStatus
    source_agent_id: UUID
    target_agent_id: UUID
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    rollback_performed: bool = False
    transferred_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HandoffState:
    """
    Tracks the current state of an active handoff.

    Attributes:
        handoff_id: Unique identifier for this handoff
        source_agent_id: Agent initiating the handoff
        target_agent_id: Agent receiving the handoff
        status: Current status
        context: Context being transferred
        started_at: When handoff started
        completed_at: When handoff completed
        error: Error message if any
    """
    handoff_id: UUID
    source_agent_id: UUID
    target_agent_id: UUID
    status: HandoffStatus
    context: Optional[HandoffContext] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class HandoffController:
    """
    Controller for managing Agent handoff operations.

    Provides functionality for:
        - Initiating handoff requests between agents
        - Executing handoffs with different policies
        - Managing context transfer
        - Rollback on failure
        - Audit logging

    Usage:
        controller = HandoffController(agent_service, audit_logger)

        request = await controller.initiate_handoff(
            source_agent_id=uuid1,
            target_agent_id=uuid2,
            context=HandoffContext(task_id="task-1", task_state={}),
            policy=HandoffPolicy.GRACEFUL,
        )

        result = await controller.execute_handoff(request)
    """

    def __init__(
        self,
        agent_service: Any = None,
        audit_logger: Any = None,
        context_transfer_manager: Any = None,
    ) -> None:
        """
        Initialize HandoffController.

        Args:
            agent_service: Service for agent operations
            audit_logger: Logger for audit events
            context_transfer_manager: Manager for context transfer operations
        """
        self._agent_service = agent_service
        self._audit = audit_logger
        self._context_transfer = context_transfer_manager

        # Active handoffs tracking
        self._active_handoffs: Dict[UUID, HandoffRequest] = {}
        self._handoff_states: Dict[UUID, HandoffState] = {}

        # Event handlers
        self._on_handoff_complete: List[Callable] = []
        self._on_handoff_failed: List[Callable] = []

        logger.info("HandoffController initialized")

    @property
    def active_handoffs(self) -> Dict[UUID, HandoffRequest]:
        """Get dictionary of active handoff requests."""
        return self._active_handoffs.copy()

    @property
    def handoff_states(self) -> Dict[UUID, HandoffState]:
        """Get dictionary of handoff states."""
        return self._handoff_states.copy()

    def register_completion_handler(self, handler: Callable) -> None:
        """Register a handler for handoff completion events."""
        self._on_handoff_complete.append(handler)

    def register_failure_handler(self, handler: Callable) -> None:
        """Register a handler for handoff failure events."""
        self._on_handoff_failed.append(handler)

    async def initiate_handoff(
        self,
        source_agent_id: UUID,
        target_agent_id: UUID,
        context: HandoffContext,
        policy: HandoffPolicy = HandoffPolicy.GRACEFUL,
        reason: str = "",
        conditions: Dict[str, Any] = None,
    ) -> HandoffRequest:
        """
        Initiate a handoff request.

        Args:
            source_agent_id: Agent initiating the handoff
            target_agent_id: Agent to receive the handoff
            context: Context data to transfer
            policy: Handoff execution policy
            reason: Reason for the handoff
            conditions: Conditions for CONDITIONAL policy

        Returns:
            HandoffRequest with generated ID

        Raises:
            ValueError: If required parameters are missing
        """
        if not source_agent_id or not target_agent_id:
            raise ValueError("Both source_agent_id and target_agent_id are required")

        if source_agent_id == target_agent_id:
            raise ValueError("Source and target agents cannot be the same")

        request = HandoffRequest(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            context=context,
            policy=policy,
            reason=reason,
            conditions=conditions or {},
        )

        # Track active handoff
        self._active_handoffs[request.id] = request

        # Create initial state
        self._handoff_states[request.id] = HandoffState(
            handoff_id=request.id,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            status=HandoffStatus.INITIATED,
            context=context,
        )

        # Log audit event
        await self._log_audit(
            action="handoff.initiated",
            details={
                "handoff_id": str(request.id),
                "source_agent": str(source_agent_id),
                "target_agent": str(target_agent_id),
                "policy": policy.value,
                "reason": reason,
            },
        )

        logger.info(
            f"Handoff initiated: {request.id} "
            f"from {source_agent_id} to {target_agent_id} "
            f"policy={policy.value}"
        )

        return request

    async def execute_handoff(self, request: HandoffRequest) -> HandoffResult:
        """
        Execute a handoff request.

        Args:
            request: The handoff request to execute

        Returns:
            HandoffResult with execution outcome
        """
        start_time = datetime.utcnow()

        try:
            # Update state to validating
            await self._update_state(request.id, HandoffStatus.VALIDATING)

            # Validate handoff conditions
            await self._validate_handoff(request)

            # Execute based on policy
            if request.policy == HandoffPolicy.IMMEDIATE:
                result = await self._execute_immediate_handoff(request)
            elif request.policy == HandoffPolicy.GRACEFUL:
                result = await self._execute_graceful_handoff(request)
            else:  # CONDITIONAL
                result = await self._execute_conditional_handoff(request)

            # Calculate duration
            result.completed_at = datetime.utcnow()
            result.duration_ms = int(
                (result.completed_at - start_time).total_seconds() * 1000
            )

            # Cleanup
            self._cleanup_handoff(request.id)

            # Notify handlers
            await self._notify_completion(result)

            return result

        except Exception as e:
            logger.error(f"Handoff execution failed: {e}", exc_info=True)

            # Attempt rollback
            rollback_success = await self._rollback_handoff(request)

            # Create failure result
            result = HandoffResult(
                request_id=request.id,
                status=HandoffStatus.FAILED,
                source_agent_id=request.source_agent_id,
                target_agent_id=request.target_agent_id,
                started_at=start_time,
                completed_at=datetime.utcnow(),
                error=str(e),
                rollback_performed=rollback_success,
            )

            result.duration_ms = int(
                (result.completed_at - start_time).total_seconds() * 1000
            )

            # Cleanup
            self._cleanup_handoff(request.id)

            # Notify handlers
            await self._notify_failure(result)

            return result

    async def cancel_handoff(self, handoff_id: UUID) -> bool:
        """
        Cancel an active handoff.

        Args:
            handoff_id: ID of the handoff to cancel

        Returns:
            True if cancelled successfully, False if not found
        """
        if handoff_id not in self._active_handoffs:
            logger.warning(f"Cannot cancel: handoff {handoff_id} not found")
            return False

        await self._update_state(handoff_id, HandoffStatus.CANCELLED)

        await self._log_audit(
            action="handoff.cancelled",
            details={"handoff_id": str(handoff_id)},
        )

        self._cleanup_handoff(handoff_id)

        logger.info(f"Handoff cancelled: {handoff_id}")
        return True

    async def get_handoff_status(self, handoff_id: UUID) -> Optional[HandoffState]:
        """
        Get the current state of a handoff.

        Args:
            handoff_id: ID of the handoff

        Returns:
            HandoffState if found, None otherwise
        """
        return self._handoff_states.get(handoff_id)

    # =========================================================================
    # Private Methods
    # =========================================================================

    async def _validate_handoff(self, request: HandoffRequest) -> None:
        """
        Validate handoff conditions before execution.

        Args:
            request: The handoff request to validate

        Raises:
            ValueError: If validation fails
        """
        # Validate source agent
        if self._agent_service:
            source_agent = await self._agent_service.get_agent(request.source_agent_id)
            if not source_agent:
                raise ValueError(f"Source agent {request.source_agent_id} not found")

            # Validate target agent
            target_agent = await self._agent_service.get_agent(request.target_agent_id)
            if not target_agent:
                raise ValueError(f"Target agent {request.target_agent_id} not found")

            # Check target agent capability
            if not await self._check_capability(target_agent, request.context):
                raise ValueError("Target agent lacks required capabilities")

        logger.debug(f"Handoff validation passed: {request.id}")

    async def _check_capability(
        self,
        agent: Any,
        context: HandoffContext,
    ) -> bool:
        """
        Check if agent has capability to handle the task.

        Args:
            agent: The agent to check
            context: The context containing task requirements

        Returns:
            True if agent has required capability
        """
        # TODO: Integrate with CapabilityMatcher (S8-4)
        return True

    async def _execute_immediate_handoff(
        self,
        request: HandoffRequest,
    ) -> HandoffResult:
        """
        Execute immediate handoff without waiting.

        Args:
            request: The handoff request

        Returns:
            HandoffResult with outcome
        """
        await self._update_state(request.id, HandoffStatus.TRANSFERRING)

        # 1. Pause source agent immediately
        if self._agent_service:
            await self._agent_service.pause_agent(request.source_agent_id)

        # 2. Transfer context
        transferred = await self._transfer_context(request)

        # 3. Activate target agent
        if self._agent_service:
            await self._agent_service.activate_agent(
                request.target_agent_id,
                context=request.context.task_state,
            )

        # 4. Release source agent
        if self._agent_service:
            await self._agent_service.release_agent(request.source_agent_id)

        await self._update_state(request.id, HandoffStatus.COMPLETED)

        await self._log_audit(
            action="handoff.completed",
            details={
                "handoff_id": str(request.id),
                "policy": "immediate",
                "source_agent": str(request.source_agent_id),
                "target_agent": str(request.target_agent_id),
            },
        )

        return HandoffResult(
            request_id=request.id,
            status=HandoffStatus.COMPLETED,
            source_agent_id=request.source_agent_id,
            target_agent_id=request.target_agent_id,
            transferred_context=transferred,
        )

    async def _execute_graceful_handoff(
        self,
        request: HandoffRequest,
    ) -> HandoffResult:
        """
        Execute graceful handoff waiting for current task.

        Args:
            request: The handoff request

        Returns:
            HandoffResult with outcome
        """
        # 1. Mark source agent as pending handoff
        if self._agent_service:
            await self._agent_service.mark_handoff_pending(request.source_agent_id)

        # 2. Wait for current task to complete
        await self._wait_for_completion(
            request.source_agent_id,
            timeout=request.context.timeout if request.context else 300,
        )

        # 3. Execute actual transfer (same as immediate)
        return await self._execute_immediate_handoff(request)

    async def _execute_conditional_handoff(
        self,
        request: HandoffRequest,
    ) -> HandoffResult:
        """
        Execute conditional handoff based on conditions.

        Args:
            request: The handoff request

        Returns:
            HandoffResult with outcome
        """
        # Evaluate conditions
        should_handoff = await self._evaluate_conditions(request)

        if should_handoff:
            # Proceed with graceful handoff
            return await self._execute_graceful_handoff(request)
        else:
            await self._update_state(request.id, HandoffStatus.FAILED)

            return HandoffResult(
                request_id=request.id,
                status=HandoffStatus.FAILED,
                source_agent_id=request.source_agent_id,
                target_agent_id=request.target_agent_id,
                error="Handoff conditions not met",
            )

    async def _transfer_context(self, request: HandoffRequest) -> Dict[str, Any]:
        """
        Transfer context to target agent.

        Args:
            request: The handoff request

        Returns:
            Dictionary summarizing transferred context
        """
        if not request.context:
            return {}

        context_data = {
            "task_id": request.context.task_id,
            "task_state": request.context.task_state,
            "conversation_history": request.context.conversation_history,
            "metadata": request.context.metadata,
            "handoff_reason": request.reason,
            "source_agent_id": str(request.source_agent_id),
        }

        # Use context transfer manager if available
        if self._context_transfer:
            await self._context_transfer.transfer(
                request.target_agent_id,
                context_data,
            )
        elif self._agent_service:
            await self._agent_service.inject_context(
                request.target_agent_id,
                context_data,
            )

        logger.debug(f"Context transferred for handoff {request.id}")

        return {
            "task_id": request.context.task_id,
            "state_keys": list(request.context.task_state.keys()),
            "history_length": len(request.context.conversation_history),
        }

    async def _wait_for_completion(
        self,
        agent_id: UUID,
        timeout: int,
    ) -> None:
        """
        Wait for agent to complete current task.

        Args:
            agent_id: Agent to wait for
            timeout: Maximum wait time in seconds

        Raises:
            TimeoutError: If agent doesn't complete within timeout
        """
        start_time = datetime.utcnow()

        while True:
            if self._agent_service:
                status = await self._agent_service.get_agent_status(agent_id)

                if status in ["idle", "ready", "completed"]:
                    logger.debug(f"Agent {agent_id} ready for handoff")
                    return
            else:
                # No agent service, assume ready immediately
                return

            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed > timeout:
                raise TimeoutError(
                    f"Agent {agent_id} did not complete within {timeout}s timeout"
                )

            await asyncio.sleep(1)

    async def _evaluate_conditions(self, request: HandoffRequest) -> bool:
        """
        Evaluate conditions for conditional handoff.

        Args:
            request: The handoff request

        Returns:
            True if conditions are met
        """
        if not request.conditions:
            return True

        # TODO: Integrate with HandoffTriggerEvaluator (S8-2)
        # For now, return True if conditions exist
        return True

    async def _rollback_handoff(self, request: HandoffRequest) -> bool:
        """
        Rollback a failed handoff.

        Args:
            request: The failed handoff request

        Returns:
            True if rollback succeeded
        """
        try:
            await self._update_state(request.id, HandoffStatus.ROLLED_BACK)

            # Restore source agent
            if self._agent_service:
                await self._agent_service.restore_agent(request.source_agent_id)

            await self._log_audit(
                action="handoff.rolled_back",
                details={
                    "handoff_id": str(request.id),
                    "source_agent": str(request.source_agent_id),
                    "target_agent": str(request.target_agent_id),
                },
            )

            logger.info(f"Handoff rolled back: {request.id}")
            return True

        except Exception as e:
            logger.error(f"Rollback failed for handoff {request.id}: {e}")

            await self._log_audit(
                action="handoff.rollback_failed",
                details={
                    "handoff_id": str(request.id),
                    "error": str(e),
                },
            )

            return False

    async def _update_state(
        self,
        handoff_id: UUID,
        status: HandoffStatus,
        error: str = None,
    ) -> None:
        """
        Update handoff state.

        Args:
            handoff_id: ID of the handoff
            status: New status
            error: Optional error message
        """
        if handoff_id in self._handoff_states:
            state = self._handoff_states[handoff_id]
            state.status = status
            if error:
                state.error = error
            if status in [
                HandoffStatus.COMPLETED,
                HandoffStatus.FAILED,
                HandoffStatus.CANCELLED,
                HandoffStatus.ROLLED_BACK,
            ]:
                state.completed_at = datetime.utcnow()

    def _cleanup_handoff(self, handoff_id: UUID) -> None:
        """
        Cleanup handoff from active tracking.

        Args:
            handoff_id: ID of the handoff to cleanup
        """
        if handoff_id in self._active_handoffs:
            del self._active_handoffs[handoff_id]

    async def _log_audit(
        self,
        action: str,
        details: Dict[str, Any],
    ) -> None:
        """
        Log audit event.

        Args:
            action: Action name
            details: Event details
        """
        if self._audit:
            try:
                await self._audit.log(
                    action=action,
                    actor="system",
                    actor_type="system",
                    details=details,
                )
            except Exception as e:
                logger.warning(f"Failed to log audit event: {e}")

    async def _notify_completion(self, result: HandoffResult) -> None:
        """Notify completion handlers."""
        for handler in self._on_handoff_complete:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(result)
                else:
                    handler(result)
            except Exception as e:
                logger.error(f"Completion handler failed: {e}")

    async def _notify_failure(self, result: HandoffResult) -> None:
        """Notify failure handlers."""
        for handler in self._on_handoff_failed:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(result)
                else:
                    handler(result)
            except Exception as e:
                logger.error(f"Failure handler failed: {e}")
