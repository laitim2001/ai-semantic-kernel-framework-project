# =============================================================================
# IPA Platform - Approval Handler
# =============================================================================
# Sprint 132: Encapsulates RiskAssessor + HITLController logic extracted
#   from HybridOrchestratorV2._handle_hitl() and execute_with_routing().
# =============================================================================

import logging
from typing import Any, Dict, Optional

from src.integrations.hybrid.orchestrator.contracts import (
    Handler,
    HandlerResult,
    HandlerType,
    OrchestratorRequest,
)

logger = logging.getLogger(__name__)


class ApprovalHandler(Handler):
    """Handles risk assessment and HITL approval workflow.

    Encapsulates:
    - RiskAssessor for operation risk evaluation
    - HITLController for approval request creation and status checking
    """

    def __init__(
        self,
        *,
        risk_assessor: Optional[Any] = None,
        hitl_controller: Optional[Any] = None,
    ):
        self._risk_assessor = risk_assessor
        self._hitl_controller = hitl_controller

    @property
    def handler_type(self) -> HandlerType:
        return HandlerType.APPROVAL

    def can_handle(self, request: OrchestratorRequest, context: Dict[str, Any]) -> bool:
        """Only handle when in Phase 28 flow with risk/HITL components."""
        return bool(
            request.source_request
            and (self._risk_assessor or self._hitl_controller)
        )

    async def handle(
        self,
        request: OrchestratorRequest,
        context: Dict[str, Any],
    ) -> HandlerResult:
        """Execute risk assessment and HITL approval flow.

        Flow:
        1. RiskAssessor evaluates the routing decision
        2. If approval required, HITLController creates approval request
        3. Short-circuit if pending or rejected
        """
        routing_decision = context.get("routing_decision")
        if not routing_decision:
            return HandlerResult(
                success=True,
                handler_type=HandlerType.APPROVAL,
                data={"skipped": True, "reason": "No routing decision"},
            )

        try:
            # Step 1: Risk assessment
            risk_assessment = None
            if self._risk_assessor:
                logger.info("ApprovalHandler: Assessing risk")
                risk_assessment = self._risk_assessor.assess(routing_decision)
                context["risk_assessment"] = risk_assessment

            # Step 2: HITL approval if needed
            if (
                risk_assessment
                and risk_assessment.requires_approval
                and self._hitl_controller
            ):
                logger.info("ApprovalHandler: Starting HITL approval")
                approval_result = await self._hitl_controller.request_approval(
                    routing_decision=routing_decision,
                    risk_assessment=risk_assessment,
                    requester=request.requester,
                )
                context["approval_result"] = approval_result

                # Import here to avoid circular dependency
                from src.integrations.orchestration import ApprovalStatus

                if approval_result.status == ApprovalStatus.PENDING:
                    return HandlerResult(
                        success=True,
                        handler_type=HandlerType.APPROVAL,
                        should_short_circuit=True,
                        short_circuit_response={
                            "content": "Operation requires approval. Waiting for authorization.",
                            "approval_id": approval_result.request_id,
                            "status": "pending_approval",
                        },
                    )
                if approval_result.status == ApprovalStatus.REJECTED:
                    return HandlerResult(
                        success=False,
                        handler_type=HandlerType.APPROVAL,
                        should_short_circuit=True,
                        short_circuit_response={
                            "content": f"Operation rejected: {approval_result.comment or 'No reason provided'}",
                            "approval_id": approval_result.request_id,
                            "status": "rejected",
                            "rejected_by": approval_result.rejected_by,
                            "error": "Approval rejected",
                        },
                    )

            return HandlerResult(
                success=True,
                handler_type=HandlerType.APPROVAL,
                data={
                    "risk_assessment": risk_assessment,
                    "approval_required": bool(
                        risk_assessment and risk_assessment.requires_approval
                    ),
                },
            )

        except Exception as e:
            logger.error(f"ApprovalHandler error: {e}", exc_info=True)
            return HandlerResult(
                success=False,
                handler_type=HandlerType.APPROVAL,
                error=str(e),
            )
