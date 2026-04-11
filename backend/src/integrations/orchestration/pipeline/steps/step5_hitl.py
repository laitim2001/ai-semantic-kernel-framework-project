"""
Step 5: HITL Gate — Conditional human approval checkpoint.

Checks risk_assessment to determine if human approval is required.
If yes: saves checkpoint, creates approval request, raises HITLPauseException.
If no: passes through silently.

May raise:
    HITLPauseException — when approval is required (HIGH/CRITICAL risk).

Phase 45: Orchestration Core (Sprint 154)
"""

import logging
from typing import Optional

from ..context import PipelineContext
from ..exceptions import HITLPauseException
from .base import PipelineStep

logger = logging.getLogger(__name__)


class HITLGateStep(PipelineStep):
    """Conditional human-in-the-loop approval gate.

    Decision logic (from V8 RiskAssessor policies):
        - risk_assessment.requires_approval == True → PAUSE
        - risk_assessment.requires_approval == False → PASS

    On pause:
        1. Saves WorkflowCheckpoint to Redis (for resume)
        2. Creates ApprovalRequest via ApprovalService
        3. Raises HITLPauseException (caught by pipeline service)

    On resume (handled by ResumeService, not this step):
        - Approved → pipeline continues from Step 6
        - Rejected → pipeline terminates with rejection status
    """

    def __init__(
        self,
        approval_service: Optional[object] = None,
        checkpoint_storage: Optional[object] = None,
    ):
        """Initialize HITLGateStep.

        Args:
            approval_service: ApprovalService instance for creating requests.
                If None, creates one with default Redis config.
            checkpoint_storage: IPACheckpointStorage for saving pipeline state.
                If None, checkpoint saving is skipped.
        """
        self._approval_service = approval_service
        self._checkpoint_storage = checkpoint_storage

    @property
    def name(self) -> str:
        return "hitl_gate"

    @property
    def step_index(self) -> int:
        return 4

    async def _execute(self, context: PipelineContext) -> PipelineContext:
        """Evaluate if approval is needed and act accordingly.

        Args:
            context: PipelineContext with risk_assessment set (from Step 4).

        Returns:
            Unchanged PipelineContext if no approval needed.

        Raises:
            HITLPauseException: If risk_assessment.requires_approval is True.
        """
        if context.risk_assessment is None:
            logger.warning("HITLGateStep: no risk_assessment, passing through")
            return context

        ra = context.risk_assessment
        rd = context.routing_decision

        # Only actionable intents (CHANGE, INCIDENT) can trigger HITL.
        # QUERY, UNKNOWN, and REQUEST are read-only / low-risk by nature.
        # This matches the PoC behavior where only CHANGE+HIGH triggered approval.
        actionable_intents = {"change", "incident"}
        intent_str = (
            rd.intent_category.value
            if rd and hasattr(rd.intent_category, "value")
            else str(rd.intent_category) if rd else "unknown"
        ).lower()

        if intent_str not in actionable_intents:
            logger.info(
                "HITLGateStep: non-actionable intent '%s', skipping approval (level=%s)",
                intent_str,
                ra.level.value if hasattr(ra.level, "value") else str(ra.level),
            )
            return context

        if not ra.requires_approval:
            logger.info(
                "HITLGateStep: approval not required (level=%s, score=%.2f)",
                ra.level.value if hasattr(ra.level, "value") else str(ra.level),
                ra.score,
            )
            return context

        # --- Approval required: save checkpoint and create request ---
        logger.info(
            "HITLGateStep: approval REQUIRED (level=%s, type=%s, policy=%s)",
            ra.level.value if hasattr(ra.level, "value") else str(ra.level),
            ra.approval_type,
            ra.policy_id,
        )

        # 1. Save checkpoint
        checkpoint_id = await self._save_checkpoint(context)
        context.checkpoint_id = checkpoint_id

        # 2. Create approval request (graceful: if service unavailable, still pause)
        try:
            approval_id = await self._create_approval(context, checkpoint_id)
        except Exception as e:
            logger.warning(
                "HITLGateStep: approval service unavailable, pausing without ID — %s",
                str(e)[:100],
            )
            approval_id = f"pending-{checkpoint_id or 'no-cp'}"

        # 3. Raise pause exception
        risk_level_str = (
            ra.level.value if hasattr(ra.level, "value") else str(ra.level)
        )

        raise HITLPauseException(
            approval_id=approval_id,
            checkpoint_id=checkpoint_id,
            risk_level=risk_level_str,
            approval_type=ra.approval_type,
        )

    async def _save_checkpoint(self, context: PipelineContext) -> str:
        """Save pipeline state to checkpoint storage.

        Args:
            context: Current pipeline context.

        Returns:
            Checkpoint ID string (empty if storage unavailable).
        """
        if self._checkpoint_storage is None:
            logger.warning("HITLGateStep: no checkpoint storage, skipping save")
            return ""

        try:
            from src.integrations.agent_framework.ipa_checkpoint_storage import (
                WorkflowCheckpoint,
            )

            checkpoint = WorkflowCheckpoint(
                workflow_name=context.session_id,
                graph_signature_hash="orchestrator-8step-v1",
                state=context.to_checkpoint_state(),
                messages={},
                iteration_count=self.step_index,
                metadata={
                    "user_id": context.user_id,
                    "pause_reason": "hitl",
                    "risk_level": (
                        context.risk_assessment.level.value
                        if hasattr(context.risk_assessment.level, "value")
                        else str(context.risk_assessment.level)
                    ),
                },
            )
            checkpoint_id = await self._checkpoint_storage.save(checkpoint)
            logger.info("HITLGateStep: checkpoint saved — %s", checkpoint_id)
            return checkpoint_id
        except Exception as e:
            logger.error("HITLGateStep: checkpoint save failed — %s", str(e)[:100])
            return ""

    async def _create_approval(
        self, context: PipelineContext, checkpoint_id: str
    ) -> str:
        """Create approval request via ApprovalService.

        Args:
            context: Current pipeline context.
            checkpoint_id: Saved checkpoint ID for resume.

        Returns:
            Approval request ID string.
        """
        approval_svc = await self._get_approval_service()

        from src.integrations.orchestration.approval.service import ApprovalRequest

        ra = context.risk_assessment
        rd = context.routing_decision

        request = ApprovalRequest(
            user_id=context.user_id,
            session_id=context.session_id,
            checkpoint_id=checkpoint_id,
            task=context.task[:500],
            risk_level=(
                ra.level.value if hasattr(ra.level, "value") else str(ra.level)
            ),
            intent_category=(
                rd.intent_category.value
                if rd and hasattr(rd.intent_category, "value")
                else str(rd.intent_category) if rd else "unknown"
            ),
            confidence=rd.confidence if rd else 0.0,
            context_summary={
                "memory_preview": context.memory_text[:200],
                "knowledge_preview": context.knowledge_text[:200],
                "risk_score": ra.score,
                "risk_reasoning": ra.reasoning[:200],
                "approval_type": ra.approval_type,
            },
        )

        approval_id = await approval_svc.create(request)
        logger.info("HITLGateStep: approval request created — %s", approval_id)
        return approval_id

    async def _get_approval_service(self) -> object:
        """Get or create ApprovalService."""
        if self._approval_service is None:
            from src.integrations.orchestration.approval.service import (
                ApprovalService,
            )

            self._approval_service = ApprovalService()
            await self._approval_service.initialize()
        return self._approval_service
