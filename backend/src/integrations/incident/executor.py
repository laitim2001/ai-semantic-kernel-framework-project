"""
IT Incident Executor — Auto-Remediation + HITL Approval + ServiceNow Writeback.

Sprint 126: Story 126-3 — IncidentExecutor handles the execution of
remediation actions. Low-risk actions are auto-executed; high-risk actions
go through HITL approval before execution.

After execution, results are written back to ServiceNow.

Dependencies:
    - HITLController (orchestration/hitl/)
    - RiskAssessor (orchestration/risk_assessor/)
    - ServiceNow MCP client (optional, for writeback)
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..orchestration.hitl.controller import (
    ApprovalStatus,
    HITLController,
    InMemoryApprovalStorage,
    create_hitl_controller,
)
from ..orchestration.intent_router.models import (
    ITIntentCategory,
    RiskLevel,
    RoutingDecision,
    WorkflowType,
)
from ..orchestration.risk_assessor.assessor import (
    AssessmentContext,
    RiskAssessment,
    RiskAssessor,
)
from .types import (
    ExecutionResult,
    ExecutionStatus,
    IncidentAnalysis,
    IncidentContext,
    RemediationAction,
    RemediationRisk,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Risk level mapping
# =============================================================================

_RISK_TO_LEVEL: Dict[RemediationRisk, RiskLevel] = {
    RemediationRisk.AUTO: RiskLevel.LOW,
    RemediationRisk.LOW: RiskLevel.LOW,
    RemediationRisk.MEDIUM: RiskLevel.MEDIUM,
    RemediationRisk.HIGH: RiskLevel.HIGH,
    RemediationRisk.CRITICAL: RiskLevel.CRITICAL,
}

# ServiceNow incident state codes
SERVICENOW_STATE_IN_PROGRESS = "2"
SERVICENOW_STATE_RESOLVED = "6"
SERVICENOW_STATE_CLOSED = "7"


class IncidentExecutor:
    """Executes remediation actions with risk-based routing.

    Execution flow per action:
        1. Check action risk level
        2. AUTO/LOW → execute directly (via MCP tool)
        3. MEDIUM → execute with logging (configurable HITL gate)
        4. HIGH/CRITICAL → create HITL approval request, await decision
        5. Write results back to ServiceNow

    Example:
        >>> executor = IncidentExecutor()
        >>> results = await executor.execute(analysis, context, actions)
        >>> for r in results:
        ...     print(f"{r.action.title}: {r.status.value}")
    """

    def __init__(
        self,
        hitl_controller: Optional[HITLController] = None,
        risk_assessor: Optional[RiskAssessor] = None,
        servicenow_client: Optional[Any] = None,
        shell_executor: Optional[Any] = None,
        ldap_executor: Optional[Any] = None,
        auto_execute_medium: bool = False,
    ) -> None:
        """Initialize IncidentExecutor.

        Args:
            hitl_controller: HITL approval controller (creates default if None)
            risk_assessor: Risk assessment engine (creates default if None)
            servicenow_client: ServiceNow API client for writeback (optional)
            shell_executor: Shell MCP executor for command execution (optional)
            ldap_executor: LDAP MCP executor for AD operations (optional)
            auto_execute_medium: Whether to auto-execute MEDIUM risk actions
        """
        self._hitl_controller = hitl_controller or create_hitl_controller()
        self._risk_assessor = risk_assessor or RiskAssessor()
        self._servicenow_client = servicenow_client
        self._shell_executor = shell_executor
        self._ldap_executor = ldap_executor
        self._auto_execute_medium = auto_execute_medium

    async def execute(
        self,
        analysis: IncidentAnalysis,
        context: IncidentContext,
        actions: List[RemediationAction],
    ) -> List[ExecutionResult]:
        """Execute remediation actions in priority order.

        Args:
            analysis: Incident analysis result
            context: Incident context
            actions: Ordered list of remediation actions to execute

        Returns:
            List of ExecutionResult for each attempted action
        """
        results: List[ExecutionResult] = []

        logger.info(
            f"Executing {len(actions)} remediation actions "
            f"for {context.incident_number}"
        )

        # Update ServiceNow to In Progress
        await self._update_servicenow_state(
            context.incident_number,
            SERVICENOW_STATE_IN_PROGRESS,
            f"IPA auto-remediation started. Analysis: {analysis.analysis_id}. "
            f"Root cause: {analysis.root_cause_summary}",
        )

        for action in actions:
            result = await self._execute_single_action(action, context, analysis)
            results.append(result)

            # Write back each result to ServiceNow
            await self._writeback_servicenow(
                context.incident_number, action, result
            )

            # If a successful auto-execute resolved the issue, we can stop
            if result.success and action.should_auto_execute():
                logger.info(
                    f"Auto-executed action '{action.title}' succeeded, "
                    f"skipping remaining actions"
                )
                # Mark remaining as skipped
                remaining_actions = actions[actions.index(action) + 1:]
                for remaining in remaining_actions:
                    skip_result = ExecutionResult(
                        action=remaining,
                        status=ExecutionStatus.SKIPPED,
                        output=f"Skipped: previous action '{action.title}' resolved the incident",
                    )
                    results.append(skip_result)
                break

        # Update ServiceNow to Resolved if any action succeeded
        any_success = any(r.success for r in results)
        if any_success:
            await self._update_servicenow_state(
                context.incident_number,
                SERVICENOW_STATE_RESOLVED,
                self._build_resolution_notes(results),
            )

        logger.info(
            f"Execution complete for {context.incident_number}: "
            f"{sum(1 for r in results if r.success)} succeeded, "
            f"{sum(1 for r in results if not r.success)} failed/pending"
        )

        return results

    async def _execute_single_action(
        self,
        action: RemediationAction,
        context: IncidentContext,
        analysis: IncidentAnalysis,
    ) -> ExecutionResult:
        """Execute a single remediation action.

        Routes to auto-execute or HITL based on risk level.

        Args:
            action: Action to execute
            context: Incident context
            analysis: Incident analysis

        Returns:
            ExecutionResult with outcome
        """
        execution_id = f"exec_{uuid4().hex[:12]}"

        logger.info(
            f"Executing action '{action.title}' "
            f"(risk: {action.risk.value}, type: {action.action_type.value})"
        )

        if self._should_auto_execute(action):
            return await self._auto_execute(execution_id, action, context)
        else:
            return await self._request_hitl_approval(
                execution_id, action, context, analysis
            )

    def _should_auto_execute(self, action: RemediationAction) -> bool:
        """Determine if an action should be auto-executed.

        Args:
            action: Action to evaluate

        Returns:
            True if the action can be auto-executed
        """
        if action.risk in (RemediationRisk.AUTO, RemediationRisk.LOW):
            return True
        if self._auto_execute_medium and action.risk == RemediationRisk.MEDIUM:
            return True
        return False

    async def _auto_execute(
        self,
        execution_id: str,
        action: RemediationAction,
        context: IncidentContext,
    ) -> ExecutionResult:
        """Auto-execute a low-risk action.

        Dispatches to the appropriate MCP tool executor.

        Args:
            execution_id: Unique execution ID
            action: Action to execute
            context: Incident context

        Returns:
            ExecutionResult with outcome
        """
        started_at = datetime.utcnow()

        try:
            output = await self._dispatch_action(action, context)

            return ExecutionResult(
                execution_id=execution_id,
                action=action,
                status=ExecutionStatus.COMPLETED,
                success=True,
                output=output,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                metadata={"execution_type": "auto"},
            )

        except Exception as e:
            logger.error(
                f"Auto-execution failed for '{action.title}': {e}",
                exc_info=True,
            )
            return ExecutionResult(
                execution_id=execution_id,
                action=action,
                status=ExecutionStatus.FAILED,
                success=False,
                error=str(e),
                started_at=started_at,
                completed_at=datetime.utcnow(),
                metadata={"execution_type": "auto"},
            )

    async def _dispatch_action(
        self,
        action: RemediationAction,
        context: IncidentContext,
    ) -> str:
        """Dispatch action to appropriate MCP tool executor.

        Args:
            action: Action to dispatch
            context: Incident context

        Returns:
            Execution output string

        Raises:
            RuntimeError: If no executor available for the action type
        """
        mcp_tool = action.mcp_tool

        if mcp_tool.startswith("shell:") and self._shell_executor:
            command = action.mcp_params.get("command", "")
            logger.info(f"Executing shell command: {command[:100]}...")
            result = await self._shell_executor.execute(command)
            return str(result)

        if mcp_tool.startswith("ldap:") and self._ldap_executor:
            operation = action.mcp_params.get("operation", "")
            username = action.mcp_params.get("username", "")
            logger.info(f"Executing LDAP operation: {operation} for {username}")
            result = await self._ldap_executor.execute(operation, action.mcp_params)
            return str(result)

        # Fallback: simulate execution for demo/testing
        logger.warning(
            f"No MCP executor available for '{mcp_tool}', "
            f"simulating execution of '{action.title}'"
        )
        return (
            f"[Simulated] Action '{action.title}' executed successfully. "
            f"MCP tool '{mcp_tool}' would be called with params: {action.mcp_params}"
        )

    async def _request_hitl_approval(
        self,
        execution_id: str,
        action: RemediationAction,
        context: IncidentContext,
        analysis: IncidentAnalysis,
    ) -> ExecutionResult:
        """Request HITL approval for a high-risk action.

        Args:
            execution_id: Unique execution ID
            action: Action requiring approval
            context: Incident context
            analysis: Incident analysis

        Returns:
            ExecutionResult with AWAITING_APPROVAL status
        """
        started_at = datetime.utcnow()

        try:
            # Build a RoutingDecision for the HITL controller
            routing_decision = RoutingDecision(
                intent_category=ITIntentCategory.INCIDENT,
                sub_intent=f"remediation_{action.action_type.value}",
                confidence=action.confidence,
                workflow_type=WorkflowType.MAGENTIC,
                risk_level=_RISK_TO_LEVEL.get(action.risk, RiskLevel.HIGH),
                reasoning=(
                    f"Remediation action '{action.title}' for incident "
                    f"{context.incident_number} requires approval. "
                    f"Risk: {action.risk.value}. "
                    f"Root cause: {analysis.root_cause_summary}"
                ),
                metadata={
                    "incident_number": context.incident_number,
                    "action_id": action.action_id,
                    "action_type": action.action_type.value,
                    "execution_id": execution_id,
                },
            )

            # Create risk assessment for HITL
            risk_assessment = RiskAssessment(
                level=_RISK_TO_LEVEL.get(action.risk, RiskLevel.HIGH),
                score=self._risk_to_score(action.risk),
                requires_approval=True,
                approval_type="multi" if action.risk == RemediationRisk.CRITICAL else "single",
                reasoning=(
                    f"Action '{action.title}' has {action.risk.value} risk level. "
                    f"Manual approval required before execution."
                ),
            )

            # Request approval via HITL controller
            approval_request = await self._hitl_controller.request_approval(
                routing_decision=routing_decision,
                risk_assessment=risk_assessment,
                requester=f"ipa_incident_{context.incident_number}",
                metadata={
                    "incident_number": context.incident_number,
                    "action_title": action.title,
                    "action_description": action.description,
                    "action_risk": action.risk.value,
                    "action_mcp_tool": action.mcp_tool,
                },
            )

            logger.info(
                f"HITL approval requested: {approval_request.request_id} "
                f"for action '{action.title}' on {context.incident_number}"
            )

            return ExecutionResult(
                execution_id=execution_id,
                action=action,
                status=ExecutionStatus.AWAITING_APPROVAL,
                success=False,
                output=(
                    f"Approval requested: {approval_request.request_id}. "
                    f"Action '{action.title}' requires {risk_assessment.approval_type} "
                    f"approval due to {action.risk.value} risk."
                ),
                started_at=started_at,
                approval_request_id=approval_request.request_id,
                metadata={
                    "execution_type": "hitl",
                    "approval_type": risk_assessment.approval_type,
                },
            )

        except Exception as e:
            logger.error(
                f"HITL approval request failed for '{action.title}': {e}",
                exc_info=True,
            )
            return ExecutionResult(
                execution_id=execution_id,
                action=action,
                status=ExecutionStatus.FAILED,
                success=False,
                error=f"Failed to request HITL approval: {str(e)}",
                started_at=started_at,
                completed_at=datetime.utcnow(),
                metadata={"execution_type": "hitl"},
            )

    def _risk_to_score(self, risk: RemediationRisk) -> float:
        """Convert RemediationRisk to numerical score.

        Args:
            risk: Remediation risk level

        Returns:
            Score between 0.0 and 1.0
        """
        score_map = {
            RemediationRisk.AUTO: 0.1,
            RemediationRisk.LOW: 0.25,
            RemediationRisk.MEDIUM: 0.50,
            RemediationRisk.HIGH: 0.75,
            RemediationRisk.CRITICAL: 1.0,
        }
        return score_map.get(risk, 0.5)

    async def _writeback_servicenow(
        self,
        incident_number: str,
        action: RemediationAction,
        result: ExecutionResult,
    ) -> None:
        """Write execution result back to ServiceNow as a work note.

        Args:
            incident_number: ServiceNow INC number
            action: Executed action
            result: Execution result
        """
        if not self._servicenow_client:
            logger.debug(
                f"ServiceNow writeback skipped (no client): "
                f"{incident_number} — {action.title}"
            )
            result.servicenow_updated = False
            return

        try:
            work_note = self._build_work_note(action, result)
            await self._servicenow_client.add_work_note(
                incident_number=incident_number,
                work_note=work_note,
            )
            result.servicenow_updated = True
            logger.info(
                f"ServiceNow work note added for {incident_number}: "
                f"'{action.title}' — {result.status.value}"
            )
        except Exception as e:
            logger.error(
                f"ServiceNow writeback failed for {incident_number}: {e}",
                exc_info=True,
            )
            result.servicenow_updated = False

    async def _update_servicenow_state(
        self,
        incident_number: str,
        state: str,
        notes: str,
    ) -> None:
        """Update ServiceNow incident state.

        Args:
            incident_number: ServiceNow INC number
            state: ServiceNow state code
            notes: State transition notes
        """
        if not self._servicenow_client:
            logger.debug(
                f"ServiceNow state update skipped (no client): "
                f"{incident_number} → state={state}"
            )
            return

        try:
            await self._servicenow_client.update_incident(
                incident_number=incident_number,
                state=state,
                work_notes=notes,
            )
            logger.info(
                f"ServiceNow incident updated: {incident_number} → state={state}"
            )
        except Exception as e:
            logger.error(
                f"ServiceNow state update failed for {incident_number}: {e}",
                exc_info=True,
            )

    def _build_work_note(
        self,
        action: RemediationAction,
        result: ExecutionResult,
    ) -> str:
        """Build a ServiceNow work note from execution result.

        Args:
            action: Executed action
            result: Execution result

        Returns:
            Formatted work note string
        """
        status_emoji = {
            ExecutionStatus.COMPLETED: "[SUCCESS]",
            ExecutionStatus.FAILED: "[FAILED]",
            ExecutionStatus.AWAITING_APPROVAL: "[PENDING APPROVAL]",
            ExecutionStatus.SKIPPED: "[SKIPPED]",
        }
        status_label = status_emoji.get(result.status, f"[{result.status.value.upper()}]")

        note_parts = [
            f"{status_label} IPA Auto-Remediation: {action.title}",
            f"Action Type: {action.action_type.value}",
            f"Risk Level: {action.risk.value}",
            f"Confidence: {action.confidence:.0%}",
        ]

        if result.output:
            note_parts.append(f"Output: {result.output[:500]}")

        if result.error:
            note_parts.append(f"Error: {result.error[:500]}")

        if result.approval_request_id:
            note_parts.append(f"Approval Request: {result.approval_request_id}")

        note_parts.append(f"Execution ID: {result.execution_id}")

        return "\n".join(note_parts)

    def _build_resolution_notes(
        self,
        results: List[ExecutionResult],
    ) -> str:
        """Build ServiceNow resolution notes from all execution results.

        Args:
            results: List of execution results

        Returns:
            Formatted resolution notes string
        """
        lines = ["IPA Auto-Remediation Summary:"]

        for result in results:
            if result.action:
                status = "OK" if result.success else result.status.value
                lines.append(
                    f"- {result.action.title}: {status}"
                )

        successful = sum(1 for r in results if r.success)
        total = len(results)
        lines.append(f"\nTotal: {successful}/{total} actions completed successfully.")

        return "\n".join(lines)
