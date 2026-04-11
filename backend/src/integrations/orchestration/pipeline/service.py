"""
OrchestrationPipelineService — 8-step pipeline coordinator.

Sequences steps, handles pause/resume via exception signals, emits SSE
events for frontend streaming, and records transcript entries.

Usage:
    pipeline = OrchestrationPipelineService()
    context = PipelineContext(user_id="u1", session_id="s1", task="Check VPN")
    result_context, events = await pipeline.run(context)

Phase 45: Orchestration Core
"""

import asyncio
import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from .context import PipelineContext
from .exceptions import DialogPauseException, HITLPauseException, PipelineError
from .steps.base import PipelineStep

logger = logging.getLogger(__name__)


class PipelineEventType(str, Enum):
    """SSE event types emitted during pipeline execution."""

    PIPELINE_START = "PIPELINE_START"
    STEP_START = "STEP_START"
    STEP_COMPLETE = "STEP_COMPLETE"
    STEP_ERROR = "STEP_ERROR"
    ROUTING_COMPLETE = "ROUTING_COMPLETE"
    DIALOG_REQUIRED = "DIALOG_REQUIRED"
    HITL_REQUIRED = "HITL_REQUIRED"
    LLM_ROUTE_DECISION = "LLM_ROUTE_DECISION"
    DISPATCH_START = "DISPATCH_START"
    AGENT_THINKING = "AGENT_THINKING"
    AGENT_TOOL_CALL = "AGENT_TOOL_CALL"
    AGENT_COMPLETE = "AGENT_COMPLETE"
    TEXT_DELTA = "TEXT_DELTA"
    PIPELINE_COMPLETE = "PIPELINE_COMPLETE"
    PIPELINE_ERROR = "PIPELINE_ERROR"


class PipelineEvent:
    """An SSE event emitted during pipeline execution.

    Attributes:
        event_type: The type of event.
        data: Event payload (serializable to JSON).
        step_name: Optional step name for step-scoped events.
    """

    __slots__ = ("event_type", "data", "step_name")

    def __init__(
        self,
        event_type: PipelineEventType,
        data: Dict[str, Any],
        step_name: Optional[str] = None,
    ):
        self.event_type = event_type
        self.data = data
        self.step_name = step_name

    def to_sse(self) -> Dict[str, Any]:
        """Format for SSE streaming."""
        return {
            "event": self.event_type.value,
            "data": self.data,
        }


class OrchestrationPipelineService:
    """Coordinates the 8-step orchestration pipeline.

    Responsibilities:
        - Execute steps in sequence
        - Catch pause exceptions (HITL, Dialog) and emit SSE events
        - Record events to an asyncio.Queue for SSE streaming
        - Support resume from a specific step index
        - Record transcript entries for each step

    The service is stateless — all state lives in PipelineContext.
    A new instance can be created per request, or shared across requests.
    """

    def __init__(
        self,
        steps: Optional[List[PipelineStep]] = None,
        transcript_service: Optional[object] = None,
    ):
        """Initialize the pipeline service.

        Args:
            steps: Ordered list of PipelineStep implementations.
                If None, must call configure_steps() before run().
            transcript_service: Optional TranscriptService instance for
                recording step entries to Redis Streams.
        """
        self._steps: List[PipelineStep] = steps or []
        self._transcript_service = transcript_service

    def configure_steps(self, steps: List[PipelineStep]) -> None:
        """Set the pipeline steps. Must be called before run() if
        steps were not provided in __init__."""
        self._steps = steps

    @property
    def step_count(self) -> int:
        """Number of configured steps."""
        return len(self._steps)

    async def run(
        self,
        context: PipelineContext,
        event_queue: Optional[asyncio.Queue] = None,
        start_from_step: int = 0,
    ) -> PipelineContext:
        """Execute the pipeline from a given step.

        Args:
            context: PipelineContext with identity fields set.
            event_queue: Optional asyncio.Queue to receive PipelineEvents
                for SSE streaming. If None, events are discarded.
            start_from_step: Step index to start from (for resume).

        Returns:
            Updated PipelineContext after all steps complete (or pause).

        Raises:
            PipelineError: If an unrecoverable error occurs.
        """
        if not self._steps:
            raise PipelineError(
                "No pipeline steps configured. Call configure_steps() first.",
                step_name="pipeline",
            )

        # Emit pipeline start
        await self._emit(
            event_queue,
            PipelineEvent(
                PipelineEventType.PIPELINE_START,
                {
                    "request_id": context.request_id,
                    "session_id": context.session_id,
                    "task_preview": context.task[:100],
                    "total_steps": self.step_count,
                    "start_from": start_from_step,
                },
            ),
        )

        for step in self._steps:
            # Skip already-completed steps (for resume)
            if step.step_index < start_from_step:
                logger.debug(
                    "Skipping step [%d] %s (resuming from %d)",
                    step.step_index,
                    step.name,
                    start_from_step,
                )
                continue

            # Emit step start
            await self._emit(
                event_queue,
                PipelineEvent(
                    PipelineEventType.STEP_START,
                    {
                        "step_index": step.step_index,
                        "step_name": step.name,
                        "total_steps": self.step_count,
                    },
                    step_name=step.name,
                ),
            )

            try:
                context = await step.execute(context)

                # Emit step complete with metadata
                step_summary = self._build_step_summary(context, step)
                await self._emit(
                    event_queue,
                    PipelineEvent(
                        PipelineEventType.STEP_COMPLETE,
                        {
                            "step_index": step.step_index,
                            "step_name": step.name,
                            "latency_ms": context.step_latencies.get(step.name, 0),
                            "metadata": step_summary,
                        },
                        step_name=step.name,
                    ),
                )

                # Record transcript entry
                await self._record_transcript(context, step, "step_complete")

            except HITLPauseException as e:
                context.paused_at = "hitl"
                context.hitl_approval_id = e.approval_id
                context.checkpoint_id = e.checkpoint_id

                await self._emit(
                    event_queue,
                    PipelineEvent(
                        PipelineEventType.HITL_REQUIRED,
                        {
                            "approval_id": e.approval_id,
                            "checkpoint_id": e.checkpoint_id,
                            "risk_level": e.risk_level,
                            "approval_type": e.approval_type,
                            "step_index": step.step_index,
                        },
                        step_name=step.name,
                    ),
                )

                await self._record_transcript(context, step, "approval_required")
                logger.info(
                    "Pipeline paused at step [%d] %s — HITL required (approval=%s)",
                    step.step_index,
                    step.name,
                    e.approval_id,
                )
                return context

            except DialogPauseException as e:
                context.paused_at = "dialog"
                context.dialog_id = e.dialog_id
                context.dialog_questions = e.questions
                context.checkpoint_id = e.checkpoint_id

                await self._emit(
                    event_queue,
                    PipelineEvent(
                        PipelineEventType.DIALOG_REQUIRED,
                        {
                            "dialog_id": e.dialog_id,
                            "questions": e.questions,
                            "missing_fields": e.missing_fields,
                            "completeness_score": e.completeness_score,
                            "checkpoint_id": e.checkpoint_id,
                            "step_index": step.step_index,
                        },
                        step_name=step.name,
                    ),
                )

                await self._record_transcript(context, step, "dialog_required")
                logger.info(
                    "Pipeline paused at step [%d] %s — dialog required (%d questions)",
                    step.step_index,
                    step.name,
                    len(e.questions),
                )
                return context

            except PipelineError:
                await self._emit(
                    event_queue,
                    PipelineEvent(
                        PipelineEventType.STEP_ERROR,
                        {
                            "step_index": step.step_index,
                            "step_name": step.name,
                            "recoverable": True,
                        },
                        step_name=step.name,
                    ),
                )
                raise

            except Exception as e:
                error_msg = f"Unexpected error in step {step.name}: {str(e)[:200]}"
                logger.error(error_msg, exc_info=True)

                await self._emit(
                    event_queue,
                    PipelineEvent(
                        PipelineEventType.PIPELINE_ERROR,
                        {
                            "error": error_msg,
                            "step_index": step.step_index,
                            "step_name": step.name,
                            "recoverable": False,
                        },
                        step_name=step.name,
                    ),
                )

                await self._record_transcript(context, step, "step_error")
                raise PipelineError(
                    message=error_msg,
                    step_name=step.name,
                    recoverable=False,
                )

        # All steps completed
        await self._emit(
            event_queue,
            PipelineEvent(
                PipelineEventType.PIPELINE_COMPLETE,
                {
                    "request_id": context.request_id,
                    "session_id": context.session_id,
                    "selected_route": context.selected_route,
                    "checkpoint_id": context.checkpoint_id,
                    "total_ms": round(context.elapsed_ms, 1),
                    "completed_steps": context.completed_steps,
                },
            ),
        )

        logger.info(
            "Pipeline completed — %d steps in %.1fms (route=%s, session=%s)",
            len(context.completed_steps),
            context.elapsed_ms,
            context.selected_route,
            context.session_id,
        )

        return context

    async def _emit(
        self,
        queue: Optional[asyncio.Queue],
        event: PipelineEvent,
    ) -> None:
        """Emit a PipelineEvent to the SSE queue (if provided)."""
        if queue is not None:
            await queue.put(event)

    async def _record_transcript(
        self,
        context: PipelineContext,
        step: PipelineStep,
        entry_type: str,
    ) -> None:
        """Record a transcript entry for the completed step."""
        if self._transcript_service is None:
            return

        try:
            from src.integrations.orchestration.transcript.models import TranscriptEntry

            entry = TranscriptEntry(
                user_id=context.user_id,
                session_id=context.session_id,
                step_name=step.name,
                step_index=step.step_index,
                entry_type=entry_type,
                output_summary=self._build_step_summary(context, step),
                checkpoint_id=context.checkpoint_id,
                metadata={
                    "duration_ms": round(
                        context.step_latencies.get(step.name, 0), 1
                    ),
                },
            )
            await self._transcript_service.append(entry)
        except Exception as e:
            logger.warning(
                "Failed to record transcript for step %s: %s",
                step.name,
                str(e)[:100],
            )

    @staticmethod
    def _build_step_summary(
        context: PipelineContext, step: PipelineStep
    ) -> Dict[str, Any]:
        """Build output summary dict for a transcript entry."""
        summary: Dict[str, Any] = {"step": step.name}

        if step.name == "memory_read":
            summary["memory_chars"] = len(context.memory_text)
            summary.update(context.memory_metadata)
        elif step.name == "knowledge_search":
            summary["knowledge_chars"] = len(context.knowledge_text)
            summary.update(context.knowledge_metadata)
        elif step.name == "intent_analysis":
            if context.routing_decision:
                rd = context.routing_decision
                summary["intent"] = (
                    rd.intent_category.value
                    if hasattr(rd.intent_category, "value")
                    else str(rd.intent_category)
                )
                summary["confidence"] = rd.confidence
                summary["routing_layer"] = rd.routing_layer
        elif step.name == "risk_assessment":
            if context.risk_assessment:
                ra = context.risk_assessment
                summary["risk_level"] = (
                    ra.level.value if hasattr(ra.level, "value") else str(ra.level)
                )
                summary["requires_approval"] = ra.requires_approval
        elif step.name == "llm_route_decision":
            summary["selected_route"] = context.selected_route
            summary["reasoning"] = (context.route_reasoning or "")[:200]

        return summary


def create_default_pipeline(
    transcript_service: Optional[object] = None,
) -> OrchestrationPipelineService:
    """Factory: create pipeline with Steps 1-2 (Sprint 153 scope).

    Additional steps (3-8) will be added in Sprints 154-156.

    Args:
        transcript_service: Optional TranscriptService instance.

    Returns:
        Configured OrchestrationPipelineService.
    """
    from .steps.step1_memory import MemoryStep
    from .steps.step2_knowledge import KnowledgeStep

    steps: List[PipelineStep] = [
        MemoryStep(),
        KnowledgeStep(),
        # Sprint 154: IntentStep, RiskStep, HITLGateStep
        # Sprint 155: LLMRouteStep
        # Sprint 156: PostProcessStep
    ]

    return OrchestrationPipelineService(
        steps=steps,
        transcript_service=transcript_service,
    )
