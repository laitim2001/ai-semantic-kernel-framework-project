# =============================================================================
# IPA Platform - Approval Workflow Integration
# =============================================================================
# Phase 5: MVP Core Official API Migration
# Sprint 28, Story S28-4: Approval Workflow Integration (5 pts)
#
# This module provides integration between the workflow system and
# HumanApprovalExecutor for human-in-the-loop approval workflows.
#
# Official API Pattern (from workflows-api.md):
#   # Workflow pauses at HumanApproval
#   # Later, provide response:
#   await workflow.respond(
#       executor_name="HumanApproval",
#       response=ApprovalResponse(...)
#   )
#
# Key Features:
#   - ApprovalWorkflowManager: Manages approval workflows
#   - WorkflowApprovalAdapter: Adapts workflow respond() to HumanApprovalExecutor
#   - ApprovalWorkflowBuilder: Builder for approval-enabled workflows
#
# IMPORTANT: Uses official Agent Framework API
#   from agent_framework.workflows import Workflow
# =============================================================================

from typing import Any, Callable, Dict, List, Optional, Union
from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass, field
import asyncio
import logging

# Official Agent Framework Imports - MUST use these
# Note: Classes are directly under agent_framework, not agent_framework.workflows
from agent_framework import Workflow, Edge

# Import Sprint 28 approval components
from .approval import (
    HumanApprovalExecutor,
    ApprovalRequest,
    ApprovalResponse,
    ApprovalStatus,
    ApprovalState,
    RiskLevel,
    EscalationPolicy,
    create_approval_executor,
    create_approval_request,
    create_approval_response,
)

logger = logging.getLogger(__name__)


# =============================================================================
# ApprovalWorkflowState - Workflow State with Approvals
# =============================================================================

@dataclass
class ApprovalWorkflowState:
    """
    State tracking for workflows with approval steps.

    Attributes:
        workflow_id: Unique workflow identifier
        execution_id: Current execution identifier
        status: Current workflow status
        pending_approvals: Map of executor name to pending approval state
        completed_approvals: Map of executor name to completed approval
        created_at: When workflow started
        updated_at: Last state update
    """
    workflow_id: str
    execution_id: Optional[str] = None
    status: str = "pending"
    pending_approvals: Dict[str, ApprovalState] = field(default_factory=dict)
    completed_approvals: Dict[str, ApprovalResponse] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def has_pending_approval(self, executor_name: str) -> bool:
        """Check if there's a pending approval for the executor."""
        return executor_name in self.pending_approvals

    def get_pending_approval(self, executor_name: str) -> Optional[ApprovalState]:
        """Get pending approval state for an executor."""
        return self.pending_approvals.get(executor_name)

    def mark_approval_complete(
        self,
        executor_name: str,
        response: ApprovalResponse,
    ) -> None:
        """Mark an approval as complete."""
        if executor_name in self.pending_approvals:
            del self.pending_approvals[executor_name]
        self.completed_approvals[executor_name] = response
        self.updated_at = datetime.utcnow()


# =============================================================================
# WorkflowApprovalAdapter - Adapts workflow.respond() to HumanApprovalExecutor
# =============================================================================

class WorkflowApprovalAdapter:
    """
    Adapter that bridges workflow.respond() to HumanApprovalExecutor.

    This adapter:
    1. Intercepts workflow approval requests
    2. Routes responses to the appropriate HumanApprovalExecutor
    3. Resumes workflow execution after approval

    Example:
        >>> adapter = WorkflowApprovalAdapter()
        >>> adapter.register_executor("approval-gate", executor)

        # When workflow pauses at approval
        >>> await adapter.respond(
        ...     workflow=my_workflow,
        ...     executor_name="approval-gate",
        ...     response=ApprovalResponse(
        ...         approved=True,
        ...         reason="Looks good",
        ...         approver="admin@company.com",
        ...     )
        ... )
    """

    def __init__(self):
        """Initialize the workflow approval adapter."""
        self._executors: Dict[str, HumanApprovalExecutor] = {}
        self._workflow_states: Dict[str, ApprovalWorkflowState] = {}
        self._response_handlers: Dict[str, Callable] = {}

    def register_executor(
        self,
        name: str,
        executor: HumanApprovalExecutor,
    ) -> None:
        """
        Register a HumanApprovalExecutor.

        Args:
            name: Name to identify the executor
            executor: HumanApprovalExecutor instance
        """
        self._executors[name] = executor
        logger.info(f"Registered approval executor: {name}")

    def unregister_executor(self, name: str) -> bool:
        """
        Unregister an executor.

        Args:
            name: Executor name

        Returns:
            True if unregistered, False if not found
        """
        if name in self._executors:
            del self._executors[name]
            logger.info(f"Unregistered approval executor: {name}")
            return True
        return False

    def get_executor(self, name: str) -> Optional[HumanApprovalExecutor]:
        """
        Get a registered executor by name.

        Args:
            name: Executor name

        Returns:
            HumanApprovalExecutor or None
        """
        return self._executors.get(name)

    def register_response_handler(
        self,
        executor_name: str,
        handler: Callable,
    ) -> None:
        """
        Register a handler for approval responses.

        The handler is called after the executor processes the response.

        Args:
            executor_name: Executor name
            handler: Async callable (request, response) -> None
        """
        self._response_handlers[executor_name] = handler

    async def respond(
        self,
        workflow: Workflow,
        executor_name: str,
        response: ApprovalResponse,
        execution_context: Optional[Any] = None,
    ) -> bool:
        """
        Respond to a pending approval request.

        This implements the workflow.respond() pattern from the official API.

        Args:
            workflow: The workflow instance
            executor_name: Name of the HumanApprovalExecutor
            response: The approval response
            execution_context: Optional execution context

        Returns:
            True if response was processed successfully

        Raises:
            ValueError: If executor not found or no pending request
        """
        # Get the executor
        executor = self._executors.get(executor_name)
        if not executor:
            raise ValueError(f"Executor '{executor_name}' not registered")

        # Get pending requests for this executor
        pending = executor.get_pending_requests()
        if not pending:
            raise ValueError(f"No pending requests for executor '{executor_name}'")

        # Get the first pending request (or could match by request_id)
        state = pending[0]
        request = state.request

        # Process the response through the executor
        await executor.on_response_received(request, response, execution_context)

        # Call custom handler if registered
        handler = self._response_handlers.get(executor_name)
        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(request, response)
                else:
                    handler(request, response)
            except Exception as e:
                logger.error(f"Response handler error for {executor_name}: {e}")

        logger.info(
            f"Approval response processed for {executor_name}: "
            f"approved={response.approved}, approver={response.approver}"
        )

        return True

    async def respond_by_request_id(
        self,
        request_id: str,
        response: ApprovalResponse,
        execution_context: Optional[Any] = None,
    ) -> bool:
        """
        Respond to a specific request by ID.

        Args:
            request_id: The request ID
            response: The approval response
            execution_context: Optional execution context

        Returns:
            True if response was processed successfully
        """
        # Find the executor with this request
        for name, executor in self._executors.items():
            state = executor.get_request_state(request_id)
            if state and state.status == ApprovalStatus.PENDING:
                await executor.on_response_received(
                    state.request, response, execution_context
                )

                # Call handler
                handler = self._response_handlers.get(name)
                if handler:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(state.request, response)
                        else:
                            handler(state.request, response)
                    except Exception as e:
                        logger.error(f"Response handler error: {e}")

                return True

        raise ValueError(f"Request '{request_id}' not found in any executor")

    def get_all_pending_requests(self) -> List[Dict[str, Any]]:
        """
        Get all pending requests across all executors.

        Returns:
            List of pending request info dicts
        """
        result = []
        for name, executor in self._executors.items():
            for state in executor.get_pending_requests():
                result.append({
                    "executor_name": name,
                    "request_id": state.request.request_id,
                    "action": state.request.action,
                    "risk_level": state.request.risk_level,
                    "created_at": state.created_at.isoformat(),
                    "status": state.status.value,
                })
        return result


# =============================================================================
# ApprovalWorkflowManager - Manages Approval Workflows
# =============================================================================

class ApprovalWorkflowManager:
    """
    Manager for workflows containing approval steps.

    Coordinates workflow execution with human approval gates.

    Example:
        >>> manager = ApprovalWorkflowManager()

        # Register approval executors
        >>> manager.register_approval_executor("deploy-gate", executor)

        # Create workflow with approval
        >>> workflow = manager.create_approval_workflow(
        ...     name="deployment-workflow",
        ...     executors=[analyzer, "deploy-gate", deployer],
        ... )

        # Execute workflow (pauses at approval)
        >>> result = await manager.execute(workflow, input_data)

        # Check for pending approvals
        >>> pending = manager.get_pending_approvals()

        # Respond to approval
        >>> await manager.respond_to_approval(
        ...     executor_name="deploy-gate",
        ...     response=ApprovalResponse(approved=True, ...)
        ... )
    """

    def __init__(self):
        """Initialize the approval workflow manager."""
        self._adapter = WorkflowApprovalAdapter()
        self._workflows: Dict[str, Workflow] = {}
        self._execution_states: Dict[str, ApprovalWorkflowState] = {}

    @property
    def adapter(self) -> WorkflowApprovalAdapter:
        """Get the workflow approval adapter."""
        return self._adapter

    def register_approval_executor(
        self,
        name: str,
        executor: Optional[HumanApprovalExecutor] = None,
        escalation_policy: Optional[EscalationPolicy] = None,
    ) -> HumanApprovalExecutor:
        """
        Register an approval executor.

        If no executor provided, creates a new one.

        Args:
            name: Executor name
            executor: Optional existing executor
            escalation_policy: Optional escalation policy for new executor

        Returns:
            The registered executor
        """
        if executor is None:
            executor = create_approval_executor(
                name=name,
                timeout_minutes=(
                    escalation_policy.timeout_minutes
                    if escalation_policy else 60
                ),
            )

        self._adapter.register_executor(name, executor)
        return executor

    def get_approval_executor(self, name: str) -> Optional[HumanApprovalExecutor]:
        """Get a registered approval executor."""
        return self._adapter.get_executor(name)

    async def respond_to_approval(
        self,
        executor_name: str,
        response: ApprovalResponse,
        workflow: Optional[Workflow] = None,
    ) -> bool:
        """
        Respond to a pending approval.

        Args:
            executor_name: Name of the approval executor
            response: The approval response
            workflow: Optional workflow reference

        Returns:
            True if successful
        """
        # Use dummy workflow if not provided
        dummy_workflow = workflow or Workflow(executors=[], edges=[])
        return await self._adapter.respond(
            workflow=dummy_workflow,
            executor_name=executor_name,
            response=response,
        )

    async def respond_by_request_id(
        self,
        request_id: str,
        response: ApprovalResponse,
    ) -> bool:
        """
        Respond to a specific request by ID.

        Args:
            request_id: The request ID
            response: The approval response

        Returns:
            True if successful
        """
        return await self._adapter.respond_by_request_id(request_id, response)

    def get_pending_approvals(
        self,
        executor_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get pending approval requests.

        Args:
            executor_name: Optional filter by executor

        Returns:
            List of pending request info
        """
        all_pending = self._adapter.get_all_pending_requests()

        if executor_name:
            return [p for p in all_pending if p["executor_name"] == executor_name]

        return all_pending

    def create_approval_request(
        self,
        action: str,
        details: str,
        risk_level: Union[RiskLevel, str] = RiskLevel.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
    ) -> ApprovalRequest:
        """
        Create an approval request.

        Args:
            action: Action requiring approval
            details: Description
            risk_level: Risk level
            context: Additional context

        Returns:
            ApprovalRequest instance
        """
        return create_approval_request(
            action=action,
            details=details,
            risk_level=risk_level,
            context=context,
        )

    def create_approval_response(
        self,
        approved: bool,
        reason: str,
        approver: str,
        conditions: Optional[List[str]] = None,
    ) -> ApprovalResponse:
        """
        Create an approval response.

        Args:
            approved: Whether approved
            reason: Decision reason
            approver: Who approved/rejected
            conditions: Optional conditions

        Returns:
            ApprovalResponse instance
        """
        return create_approval_response(
            approved=approved,
            reason=reason,
            approver=approver,
            conditions=conditions,
        )


# =============================================================================
# Factory Functions
# =============================================================================

def create_workflow_approval_adapter() -> WorkflowApprovalAdapter:
    """
    Factory function to create a WorkflowApprovalAdapter.

    Returns:
        WorkflowApprovalAdapter instance
    """
    return WorkflowApprovalAdapter()


def create_approval_workflow_manager() -> ApprovalWorkflowManager:
    """
    Factory function to create an ApprovalWorkflowManager.

    Returns:
        ApprovalWorkflowManager instance
    """
    return ApprovalWorkflowManager()


# =============================================================================
# Convenience Functions
# =============================================================================

async def quick_respond(
    manager: ApprovalWorkflowManager,
    executor_name: str,
    approved: bool,
    approver: str,
    reason: Optional[str] = None,
) -> bool:
    """
    Quick helper to respond to an approval.

    Args:
        manager: ApprovalWorkflowManager instance
        executor_name: Executor name
        approved: Whether approved
        approver: Who is approving
        reason: Optional reason

    Returns:
        True if successful
    """
    response = manager.create_approval_response(
        approved=approved,
        reason=reason or ("Approved" if approved else "Rejected"),
        approver=approver,
    )
    return await manager.respond_to_approval(executor_name, response)
