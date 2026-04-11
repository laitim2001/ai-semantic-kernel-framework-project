"""
WorkflowExecutor — Stub for structured process execution.

Phase 46+ will integrate with n8n workflows or structured
process engines. For now, returns a not-implemented message.

Phase 45: Orchestration Core (Sprint 155)
"""

import asyncio
from typing import Optional

from ..models import DispatchRequest, DispatchResult, ExecutionRoute
from .base import BaseExecutor


class WorkflowExecutor(BaseExecutor):
    """Stub executor for workflow mode. Implemented in Phase 46."""

    @property
    def name(self) -> str:
        return "workflow"

    async def _execute(
        self,
        request: DispatchRequest,
        event_queue: Optional[asyncio.Queue] = None,
    ) -> DispatchResult:
        return DispatchResult(
            route=ExecutionRoute.WORKFLOW,
            response_text=(
                "Workflow mode is planned for Phase 46. "
                "For structured processes, please use 'team' mode instead."
            ),
            status="not_implemented",
        )
