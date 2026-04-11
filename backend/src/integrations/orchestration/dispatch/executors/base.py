"""
BaseExecutor — Abstract base class for all dispatch executors.

Phase 45: Orchestration Core (Sprint 155)
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

from ..models import DispatchRequest, DispatchResult

logger = logging.getLogger(__name__)


class BaseExecutor(ABC):
    """Abstract base for dispatch executors.

    Subclasses must implement:
        - name: str property — executor identifier
        - _execute: async method — the actual execution logic
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Executor identifier (e.g., 'direct_answer', 'subagent')."""
        ...

    @abstractmethod
    async def _execute(
        self,
        request: DispatchRequest,
        event_queue: Optional[asyncio.Queue] = None,
    ) -> DispatchResult:
        """Execute the dispatch request.

        Args:
            request: DispatchRequest with task and context.
            event_queue: Optional SSE event queue for streaming progress.

        Returns:
            DispatchResult with execution output.
        """
        ...

    async def execute(
        self,
        request: DispatchRequest,
        event_queue: Optional[asyncio.Queue] = None,
    ) -> DispatchResult:
        """Public entry point with logging wrapper."""
        logger.info(
            "Executor [%s] starting — task=%s..., user=%s",
            self.name,
            request.task[:50],
            request.user_id,
        )

        result = await self._execute(request, event_queue)

        logger.info(
            "Executor [%s] completed — status=%s, agents=%d, duration=%.1fms",
            self.name,
            result.status,
            len(result.agent_results),
            result.duration_ms,
        )
        return result
