"""
SwarmExecutor — Stub for deep Manager-driven analysis.

Phase 46+ will integrate with the existing swarm module at
integrations/swarm/. For now, returns a not-implemented message.

Phase 45: Orchestration Core (Sprint 155)
"""

import asyncio
from typing import Optional

from ..models import DispatchRequest, DispatchResult, ExecutionRoute
from .base import BaseExecutor


class SwarmExecutor(BaseExecutor):
    """Stub executor for swarm mode. Implemented in Phase 46."""

    @property
    def name(self) -> str:
        return "swarm"

    async def _execute(
        self,
        request: DispatchRequest,
        event_queue: Optional[asyncio.Queue] = None,
    ) -> DispatchResult:
        return DispatchResult(
            route=ExecutionRoute.SWARM,
            response_text=(
                "Swarm mode is planned for Phase 46. "
                "For complex incidents, please use 'team' mode instead."
            ),
            status="not_implemented",
        )
