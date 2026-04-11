"""
Step 8: Post-Processing — Checkpoint save + async memory extraction.

Extracted from PoC agent_team_poc.py lines 1240-1374.
Runs AFTER dispatch completes. Saves final checkpoint and
fires async memory extraction (non-blocking).

Phase 45: Orchestration Core (Sprint 156)
"""

import asyncio
import logging
from typing import Optional

from ..context import PipelineContext
from .base import PipelineStep

logger = logging.getLogger(__name__)


class PostProcessStep(PipelineStep):
    """Post-dispatch processing: checkpoint + memory extraction.

    1. Save final WorkflowCheckpoint to Redis (for audit/resume)
    2. Fire-and-forget async memory extraction via MemoryExtractionService
    3. Optionally trigger memory consolidation if threshold reached

    This step NEVER blocks the response — extraction runs in background.
    """

    def __init__(
        self,
        checkpoint_storage: Optional[object] = None,
        memory_manager: Optional[object] = None,
    ):
        """Initialize PostProcessStep.

        Args:
            checkpoint_storage: IPACheckpointStorage instance.
            memory_manager: UnifiedMemoryManager for extraction service.
        """
        self._checkpoint_storage = checkpoint_storage
        self._memory_manager = memory_manager

    @property
    def name(self) -> str:
        return "post_process"

    @property
    def step_index(self) -> int:
        return 7

    async def _execute(self, context: PipelineContext) -> PipelineContext:
        """Save checkpoint and schedule async memory extraction.

        Args:
            context: PipelineContext with all prior step outputs.

        Returns:
            PipelineContext with checkpoint_id updated.
        """
        # 1. Save final checkpoint
        checkpoint_id = await self._save_checkpoint(context)
        context.checkpoint_id = checkpoint_id

        # 2. Schedule async memory extraction (non-blocking)
        await self._schedule_memory_extraction(context)

        return context

    async def _save_checkpoint(self, context: PipelineContext) -> str:
        """Save final pipeline state to checkpoint storage."""
        if self._checkpoint_storage is None:
            logger.debug("PostProcessStep: no checkpoint storage, skipping")
            return ""

        try:
            from src.integrations.agent_framework.ipa_checkpoint_storage import (
                WorkflowCheckpoint,
            )

            # Build response preview from dispatch result
            response_preview = ""
            if context.dispatch_result is not None:
                response_preview = getattr(
                    context.dispatch_result, "response_text", ""
                )[:500]

            checkpoint = WorkflowCheckpoint(
                workflow_name=context.session_id,
                graph_signature_hash="orchestrator-8step-v1",
                state={
                    **context.to_checkpoint_state(),
                    "pipeline_step": 8,
                    "route_decision": context.selected_route,
                    "dispatch_status": (
                        context.dispatch_result.status
                        if context.dispatch_result
                        else "none"
                    ),
                },
                messages={
                    "orchestrator": [
                        {"role": "user", "content": context.task},
                        {"role": "assistant", "content": response_preview},
                    ]
                },
                iteration_count=self.step_index,
                metadata={
                    "user_id": context.user_id,
                    "task_preview": context.task[:100],
                    "route": context.selected_route,
                    "session_id": context.session_id,
                    "source": "orchestration-pipeline-v1",
                },
            )

            checkpoint_id = await self._checkpoint_storage.save(checkpoint)
            logger.info("PostProcessStep: checkpoint saved — %s", checkpoint_id)
            return checkpoint_id

        except Exception as e:
            logger.error("PostProcessStep: checkpoint save failed — %s", str(e)[:100])
            return ""

    async def _schedule_memory_extraction(self, context: PipelineContext) -> None:
        """Fire-and-forget async memory extraction.

        Uses MemoryExtractionService to extract structured facts,
        preferences, decisions, and patterns from the conversation.
        Also checks if memory consolidation is due.
        """
        try:
            from src.integrations.memory.extraction import MemoryExtractionService

            mgr = self._memory_manager
            if mgr is None:
                from src.integrations.memory.unified_memory import UnifiedMemoryManager

                mgr = UnifiedMemoryManager()
                await mgr.initialize()

            extraction_svc = MemoryExtractionService(mgr)

            # Build response text from dispatch result
            response_text = ""
            if context.dispatch_result is not None:
                response_text = getattr(
                    context.dispatch_result, "response_text", ""
                )[:2000]

            # Build pipeline context for extraction
            pipeline_ctx = {
                "route_decision": context.selected_route or "",
                "risk_level": (
                    context.risk_assessment.level.value
                    if context.risk_assessment
                    and hasattr(context.risk_assessment.level, "value")
                    else ""
                ),
                "intent_category": (
                    context.routing_decision.intent_category.value
                    if context.routing_decision
                    and hasattr(context.routing_decision.intent_category, "value")
                    else ""
                ),
            }

            # Fire-and-forget: extraction runs in background
            asyncio.create_task(
                extraction_svc.extract_and_store(
                    user_id=context.user_id,
                    session_id=context.session_id,
                    user_message=context.task,
                    assistant_response=response_text,
                    pipeline_context=pipeline_ctx,
                )
            )

            # Check consolidation threshold
            try:
                from src.integrations.memory.consolidation import (
                    MemoryConsolidationService,
                )

                consolidation_svc = MemoryConsolidationService(mgr)
                should_consolidate = await consolidation_svc.increment_and_check(
                    context.user_id
                )
                if should_consolidate:
                    asyncio.create_task(
                        consolidation_svc.run_consolidation(context.user_id)
                    )
                    logger.info(
                        "PostProcessStep: consolidation triggered for user=%s",
                        context.user_id,
                    )
            except ImportError:
                pass  # consolidation module not available

            logger.info(
                "PostProcessStep: memory extraction scheduled (user=%s)",
                context.user_id,
            )

        except Exception as e:
            logger.warning(
                "PostProcessStep: memory extraction failed — %s", str(e)[:100]
            )
