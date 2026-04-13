"""
Step 1: Memory Read — Load user memory with token budget allocation.

Extracted from PoC agent_team_poc.py lines 872-913.
Wraps UnifiedMemoryManager + ContextBudgetManager.

Outputs:
    context.memory_text — Token-budgeted memory text for downstream steps.
    context.memory_metadata — Pinned count, budget used percentage, etc.

Phase 45: Orchestration Core
"""

import logging
from typing import Optional

from ..context import PipelineContext
from .base import PipelineStep

logger = logging.getLogger(__name__)


class MemoryStep(PipelineStep):
    """Read user memory with token-aware budget allocation.

    Uses UnifiedMemoryManager (4-layer: pinned, working, session, long-term)
    and ContextBudgetManager (priority-based: pinned 30% → working 25% →
    relevant 30% → history 15%) to assemble a token-budgeted memory text.

    Graceful degradation: if memory service is unavailable, sets
    context.memory_text = "" and logs warning. Pipeline continues.
    """

    def __init__(
        self,
        memory_manager: Optional[object] = None,
        budget_manager: Optional[object] = None,
    ):
        """Initialize MemoryStep.

        Args:
            memory_manager: Pre-initialized UnifiedMemoryManager instance.
                If None, creates one on first execute.
            budget_manager: Pre-initialized ContextBudgetManager instance.
                If None, creates one on first execute.
        """
        self._memory_manager = memory_manager
        self._budget_manager = budget_manager

    @property
    def name(self) -> str:
        return "memory_read"

    @property
    def step_index(self) -> int:
        return 0

    async def _execute(self, context: PipelineContext) -> PipelineContext:
        """Read user memory and assemble token-budgeted context.

        Args:
            context: PipelineContext with user_id and task set.

        Returns:
            PipelineContext with memory_text and memory_metadata populated.
        """
        try:
            mgr = await self._get_memory_manager()
            budget_mgr = self._get_budget_manager()

            assembled_context = await budget_mgr.assemble_context(
                user_id=context.user_id,
                query=context.task,
                memory_manager=mgr,
            )

            context.memory_text = assembled_context.to_prompt_text()
            context.memory_metadata = {
                "pinned_count": getattr(assembled_context, "pinned_count", 0),
                "budget_used_pct": getattr(assembled_context, "budget_used_pct", 0),
                "status": "ok",
            }

            logger.info(
                "MemoryStep: assembled %d chars, pinned=%d, budget=%.0f%% (user=%s)",
                len(context.memory_text),
                context.memory_metadata.get("pinned_count", 0),
                context.memory_metadata.get("budget_used_pct", 0),
                context.user_id,
            )

        except Exception as e:
            logger.warning(
                "MemoryStep: memory service unavailable — %s (user=%s)",
                str(e)[:100],
                context.user_id,
            )
            context.memory_text = ""
            context.memory_metadata = {
                "status": "unavailable",
                "error": str(e)[:200],
            }

        return context

    async def _get_memory_manager(self) -> object:
        """Get or create UnifiedMemoryManager instance."""
        if self._memory_manager is None:
            from src.integrations.memory.unified_memory import UnifiedMemoryManager

            self._memory_manager = UnifiedMemoryManager()
            await self._memory_manager.initialize()
        return self._memory_manager

    def _get_budget_manager(self) -> object:
        """Get or create ContextBudgetManager instance."""
        if self._budget_manager is None:
            from src.integrations.memory.context_budget import ContextBudgetManager

            self._budget_manager = ContextBudgetManager()
        return self._budget_manager
