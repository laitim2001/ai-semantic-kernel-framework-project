"""
PipelineStep — Abstract base class for all pipeline steps.

Each step:
1. Receives PipelineContext with prior step outputs
2. Performs its work (may be async)
3. Writes its output into PipelineContext
4. Optionally records a TranscriptEntry
5. May raise HITLPauseException or DialogPauseException to pause

Phase 45: Orchestration Core
"""

import logging
import time
from abc import ABC, abstractmethod

from ..context import PipelineContext

logger = logging.getLogger(__name__)


class PipelineStep(ABC):
    """Abstract base class for pipeline steps.

    Subclasses must implement:
        - name: str property — unique step identifier
        - step_index: int property — 0-based position in pipeline
        - _execute: async method — the actual step logic

    The public execute() method wraps _execute with timing,
    logging, and error handling.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique step identifier (e.g., 'memory_read', 'intent_analysis')."""
        ...

    @property
    @abstractmethod
    def step_index(self) -> int:
        """0-based position in the 8-step pipeline."""
        ...

    @abstractmethod
    async def _execute(self, context: PipelineContext) -> PipelineContext:
        """Execute the step logic.

        Args:
            context: PipelineContext with prior step outputs.

        Returns:
            Updated PipelineContext with this step's outputs.

        Raises:
            HITLPauseException: If human approval is required (Step 5).
            DialogPauseException: If user input is incomplete (Step 3).
            PipelineError: If an unrecoverable error occurs.
        """
        ...

    async def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute the step with timing, logging, and error handling.

        This is the public entry point called by OrchestrationPipelineService.
        It wraps _execute with:
        - Start/end logging
        - Latency measurement
        - Step completion recording in context

        Args:
            context: PipelineContext with prior step outputs.

        Returns:
            Updated PipelineContext.

        Raises:
            HITLPauseException: Propagated from _execute.
            DialogPauseException: Propagated from _execute.
            PipelineError: Wrapped from unexpected exceptions.
        """
        logger.info(
            "Pipeline step [%d] %s — starting (session=%s)",
            self.step_index,
            self.name,
            context.session_id,
        )
        start = time.time()

        try:
            context = await self._execute(context)
            latency_ms = (time.time() - start) * 1000
            context.mark_step_complete(self.name, latency_ms)
            logger.info(
                "Pipeline step [%d] %s — completed in %.1fms",
                self.step_index,
                self.name,
                latency_ms,
            )
            return context
        except Exception:
            latency_ms = (time.time() - start) * 1000
            logger.error(
                "Pipeline step [%d] %s — failed after %.1fms",
                self.step_index,
                self.name,
                latency_ms,
                exc_info=True,
            )
            raise
