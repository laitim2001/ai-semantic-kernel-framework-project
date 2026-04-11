"""
Step 3: Intent Analysis + Completeness Check.

Wraps V8's BusinessIntentRouter (3-tier cascade: Pattern → Semantic → LLM)
and CompletenessChecker. If information is incomplete, integrates
GuidedDialogEngine and raises DialogPauseException.

Outputs:
    context.routing_decision — V8 RoutingDecision (intent, confidence, etc.)
    context.completeness_info — V8 CompletenessInfo (is_complete, missing_fields)

May raise:
    DialogPauseException — when user input lacks required information.

Phase 45: Orchestration Core (Sprint 154)
"""

import logging
import uuid
from typing import Optional

from ..context import PipelineContext
from ..exceptions import DialogPauseException
from .base import PipelineStep

logger = logging.getLogger(__name__)


class IntentStep(PipelineStep):
    """Analyze user intent via 3-tier cascade and check completeness.

    Layer 1 (PatternMatcher): regex rules, <10ms, threshold 0.90
    Layer 2 (SemanticRouter): vector similarity, <100ms, threshold 0.85
    Layer 3 (LLMClassifier): Claude fallback, <2000ms

    After intent classification, CompletenessChecker validates that
    all required fields are present. If not, GuidedDialogEngine
    generates questions and the pipeline pauses.
    """

    def __init__(
        self,
        router: Optional[object] = None,
        completeness_checker: Optional[object] = None,
        guided_dialog_engine: Optional[object] = None,
        checkpoint_storage: Optional[object] = None,
    ):
        """Initialize IntentStep.

        Args:
            router: Pre-built BusinessIntentRouter instance.
                If None, creates one with default configuration.
            completeness_checker: Pre-built CompletenessChecker.
                If None, creates one with default rules.
            guided_dialog_engine: Pre-built GuidedDialogEngine.
                If None, dialog pause returns raw missing_fields.
            checkpoint_storage: IPACheckpointStorage for saving state on pause.
        """
        self._router = router
        self._completeness_checker = completeness_checker
        self._dialog_engine = guided_dialog_engine
        self._checkpoint_storage = checkpoint_storage

    @property
    def name(self) -> str:
        return "intent_analysis"

    @property
    def step_index(self) -> int:
        return 2

    async def _execute(self, context: PipelineContext) -> PipelineContext:
        """Route intent and check completeness.

        Args:
            context: PipelineContext with task, memory_text, knowledge_text.

        Returns:
            PipelineContext with routing_decision and completeness_info set.

        Raises:
            DialogPauseException: If required information is missing.
        """
        router = await self._get_router()

        # Run 3-tier intent classification
        routing_decision = await router.route(context.task)
        context.routing_decision = routing_decision

        logger.info(
            "IntentStep: category=%s, sub_intent=%s, confidence=%.2f, layer=%s",
            routing_decision.intent_category.value,
            routing_decision.sub_intent,
            routing_decision.confidence,
            routing_decision.routing_layer,
        )

        # Check completeness
        completeness = routing_decision.completeness
        context.completeness_info = completeness

        if not completeness.is_complete:
            logger.info(
                "IntentStep: incomplete (score=%.2f, missing=%s)",
                completeness.completeness_score,
                completeness.missing_fields,
            )
            await self._handle_incomplete(context, completeness)

        return context

    async def _handle_incomplete(
        self, context: PipelineContext, completeness: object
    ) -> None:
        """Handle incomplete user input by generating questions and pausing.

        Args:
            context: Current pipeline context.
            completeness: CompletenessInfo with missing fields.

        Raises:
            DialogPauseException: Always, to pause the pipeline.
        """
        questions = []
        dialog_id = str(uuid.uuid4())

        # Try GuidedDialogEngine for richer questions
        if self._dialog_engine is not None:
            try:
                dialog_response = await self._dialog_engine.start_dialog(context.task)
                questions = [
                    q.text if hasattr(q, "text") else str(q)
                    for q in dialog_response.questions
                ]
                if hasattr(dialog_response, "state") and dialog_response.state:
                    dialog_id = getattr(
                        dialog_response.state, "dialog_id", dialog_id
                    )
            except Exception as e:
                logger.warning(
                    "GuidedDialogEngine failed, falling back to suggestions: %s",
                    str(e)[:100],
                )

        # Fallback: use CompletenessChecker suggestions
        if not questions:
            questions = list(completeness.suggestions) if completeness.suggestions else [
                f"Please provide: {field}" for field in completeness.missing_fields
            ]

        # Save checkpoint for resume
        checkpoint_id = ""
        if self._checkpoint_storage is not None:
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
                        "pause_reason": "dialog",
                    },
                )
                checkpoint_id = await self._checkpoint_storage.save(checkpoint)
                context.checkpoint_id = checkpoint_id
            except Exception as e:
                logger.warning("Failed to save dialog checkpoint: %s", str(e)[:100])

        raise DialogPauseException(
            dialog_id=dialog_id,
            questions=questions,
            missing_fields=list(completeness.missing_fields),
            checkpoint_id=checkpoint_id,
            completeness_score=completeness.completeness_score,
        )

    async def _get_router(self) -> object:
        """Get or create BusinessIntentRouter with default configuration."""
        if self._router is None:
            from src.integrations.orchestration.intent_router.pattern_matcher.matcher import (
                PatternMatcher,
            )
            from src.integrations.orchestration.intent_router.router import (
                BusinessIntentRouter,
                RouterConfig,
            )
            from src.integrations.orchestration.intent_router.semantic_router.router import (
                SemanticRouter,
            )

            try:
                from src.integrations.orchestration.intent_router.llm_classifier.classifier import (
                    LLMClassifier,
                )
                llm_cls = LLMClassifier()
            except Exception:
                llm_cls = None

            checker = self._completeness_checker
            if checker is None:
                from src.integrations.orchestration.intent_router.completeness.checker import (
                    CompletenessChecker,
                )
                checker = CompletenessChecker()

            self._router = BusinessIntentRouter(
                pattern_matcher=PatternMatcher(),
                semantic_router=SemanticRouter(),
                llm_classifier=llm_cls,
                completeness_checker=checker,
                config=RouterConfig(
                    enable_completeness=True,
                    enable_llm_fallback=llm_cls is not None,
                ),
            )
        return self._router
