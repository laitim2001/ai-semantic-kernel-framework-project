"""
DispatchService — Routes selected execution path to the correct executor.

Phase 45: Orchestration Core (Sprint 155)
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from .executors.base import BaseExecutor
from .executors.direct_answer import DirectAnswerExecutor
from .executors.subagent import SubagentExecutor
from .executors.team import TeamExecutor
from .models import DispatchRequest, DispatchResult, ExecutionRoute

logger = logging.getLogger(__name__)


class DispatchService:
    """Routes dispatch requests to the appropriate executor.

    Maintains a registry of executors keyed by ExecutionRoute.
    Custom executors can be registered to override defaults.
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        model: Optional[str] = None,
    ):
        """Initialize with default executors.

        Args:
            llm_client: Shared LLM client for all executors.
            model: Model name/deployment for LLM calls.
        """
        self._executors: Dict[ExecutionRoute, BaseExecutor] = {
            ExecutionRoute.DIRECT_ANSWER: DirectAnswerExecutor(llm_client, model),
            ExecutionRoute.SUBAGENT: SubagentExecutor(llm_client, model),
            ExecutionRoute.TEAM: TeamExecutor(llm_client, model),
        }

    def register_executor(
        self, route: ExecutionRoute, executor: BaseExecutor
    ) -> None:
        """Register a custom executor for a route."""
        self._executors[route] = executor

    async def dispatch(
        self,
        request: DispatchRequest,
        event_queue: Optional[asyncio.Queue] = None,
    ) -> DispatchResult:
        """Dispatch a request to the appropriate executor.

        Args:
            request: DispatchRequest with route and context.
            event_queue: Optional SSE event queue for streaming.

        Returns:
            DispatchResult from the executor.
        """
        executor = self._executors.get(request.route)

        if executor is None:
            logger.error(
                "No executor registered for route: %s", request.route.value
            )
            return DispatchResult(
                route=request.route,
                response_text=f"No executor for route: {request.route.value}",
                status="failed",
            )

        logger.info(
            "Dispatching to [%s] executor (session=%s)",
            request.route.value,
            request.session_id,
        )

        if event_queue is not None:
            from ..pipeline.service import PipelineEvent, PipelineEventType

            await event_queue.put(
                PipelineEvent(
                    PipelineEventType.DISPATCH_START,
                    {
                        "route": request.route.value,
                        "executor": executor.name,
                    },
                    step_name="dispatch",
                )
            )

        return await executor.execute(request, event_queue)
