# =============================================================================
# IPA Platform - Orchestration Execution Log Repository
# =============================================================================
# Sprint 169 — Phase 47: Pipeline execution persistence
# =============================================================================

from typing import List, Optional, Tuple

from sqlalchemy import select

from src.infrastructure.database.models.orchestration_execution_log import (
    OrchestrationExecutionLog,
)
from src.infrastructure.database.repositories.base import BaseRepository


class OrchestrationExecutionLogRepository(BaseRepository[OrchestrationExecutionLog]):
    """Repository for orchestration execution log CRUD operations."""

    model = OrchestrationExecutionLog

    async def get_by_session(
        self,
        session_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[OrchestrationExecutionLog], int]:
        """List execution logs for a specific chat session."""
        return await self.list(
            page=page,
            page_size=page_size,
            order_by="created_at",
            order_desc=True,
            session_id=session_id,
        )

    async def get_by_request_id(
        self, request_id: str
    ) -> Optional[OrchestrationExecutionLog]:
        """Get a single log by its unique request_id (for dedup)."""
        return await self.get_by(request_id=request_id)

    async def get_latest_for_session(
        self, session_id: str
    ) -> Optional[OrchestrationExecutionLog]:
        """Get the most recent execution log for a session."""
        stmt = (
            select(self.model)
            .filter(self.model.session_id == session_id)
            .order_by(self.model.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
