# =============================================================================
# IPA Platform - Execution Repository
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Repository for Execution model operations.
# Provides specialized methods for execution tracking.
# =============================================================================

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.execution import Execution
from src.infrastructure.database.repositories.base import BaseRepository


class ExecutionRepository(BaseRepository[Execution]):
    """
    Repository for Execution model operations.

    Extends BaseRepository with execution-specific methods:
        - get_by_workflow: List executions for a workflow
        - get_by_status: List executions by status
        - get_running: List currently running executions
        - update_stats: Update LLM statistics
        - complete/fail/cancel: Status transitions
    """

    model = Execution

    async def get_by_workflow(
        self,
        workflow_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> Tuple[List[Execution], int]:
        """
        List executions for a specific workflow.

        Args:
            workflow_id: Workflow UUID
            page: Page number
            page_size: Records per page
            status: Optional status filter

        Returns:
            Tuple of (executions list, total count)
        """
        filters: Dict[str, Any] = {"workflow_id": workflow_id}
        if status:
            filters["status"] = status

        return await self.list(
            page=page,
            page_size=page_size,
            order_by="created_at",
            order_desc=True,
            **filters,
        )

    async def get_by_status(
        self,
        status: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Execution], int]:
        """
        List executions by status.

        Args:
            status: Execution status
            page: Page number
            page_size: Records per page

        Returns:
            Tuple of (executions list, total count)
        """
        return await self.list(
            page=page,
            page_size=page_size,
            order_by="created_at",
            order_desc=True,
            status=status,
        )

    async def get_running(self) -> List[Execution]:
        """
        Get all currently running executions.

        Returns:
            List of running executions
        """
        stmt = (
            select(Execution)
            .filter(Execution.status == "running")
            .order_by(Execution.started_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent(self, limit: int = 10) -> List[Execution]:
        """
        Get most recent executions.

        Args:
            limit: Maximum number of executions

        Returns:
            List of recent executions
        """
        stmt = (
            select(Execution)
            .order_by(Execution.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def start(
        self,
        id: UUID,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Execution]:
        """
        Mark execution as started.

        Args:
            id: Execution UUID
            input_data: Optional input data

        Returns:
            Updated execution or None if not found
        """
        update_data: Dict[str, Any] = {
            "status": "running",
            "started_at": datetime.utcnow(),
        }
        if input_data:
            update_data["input_data"] = input_data

        return await self.update(id, **update_data)

    async def complete(
        self,
        id: UUID,
        result: Dict[str, Any],
        llm_calls: int = 0,
        llm_tokens: int = 0,
        llm_cost: float = 0.0,
    ) -> Optional[Execution]:
        """
        Mark execution as completed with results.

        Args:
            id: Execution UUID
            result: Execution output
            llm_calls: Total LLM API calls
            llm_tokens: Total tokens used
            llm_cost: Estimated cost in USD

        Returns:
            Updated execution or None if not found
        """
        return await self.update(
            id,
            status="completed",
            completed_at=datetime.utcnow(),
            result=result,
            llm_calls=llm_calls,
            llm_tokens=llm_tokens,
            llm_cost=Decimal(str(llm_cost)),
        )

    async def fail(
        self,
        id: UUID,
        error: str,
        llm_calls: int = 0,
        llm_tokens: int = 0,
        llm_cost: float = 0.0,
    ) -> Optional[Execution]:
        """
        Mark execution as failed with error.

        Args:
            id: Execution UUID
            error: Error message
            llm_calls: Total LLM API calls
            llm_tokens: Total tokens used
            llm_cost: Estimated cost in USD

        Returns:
            Updated execution or None if not found
        """
        return await self.update(
            id,
            status="failed",
            completed_at=datetime.utcnow(),
            error=error,
            llm_calls=llm_calls,
            llm_tokens=llm_tokens,
            llm_cost=Decimal(str(llm_cost)),
        )

    async def cancel(self, id: UUID) -> Optional[Execution]:
        """
        Mark execution as cancelled.

        Args:
            id: Execution UUID

        Returns:
            Updated execution or None if not found
        """
        return await self.update(
            id,
            status="cancelled",
            completed_at=datetime.utcnow(),
        )

    async def pause(self, id: UUID) -> Optional[Execution]:
        """
        Mark execution as paused (waiting for human input).

        Args:
            id: Execution UUID

        Returns:
            Updated execution or None if not found
        """
        return await self.update(id, status="paused")

    async def resume(self, id: UUID) -> Optional[Execution]:
        """
        Resume a paused execution.

        Args:
            id: Execution UUID

        Returns:
            Updated execution or None if not found
        """
        return await self.update(id, status="running")

    async def update_stats(
        self,
        id: UUID,
        llm_calls: int,
        llm_tokens: int,
        llm_cost: float,
    ) -> Optional[Execution]:
        """
        Update LLM usage statistics.

        Args:
            id: Execution UUID
            llm_calls: Additional LLM calls
            llm_tokens: Additional tokens
            llm_cost: Additional cost

        Returns:
            Updated execution or None if not found
        """
        execution = await self.get(id)
        if execution is None:
            return None

        execution.llm_calls += llm_calls
        execution.llm_tokens += llm_tokens
        execution.llm_cost += Decimal(str(llm_cost))

        await self._session.flush()
        await self._session.refresh(execution)
        return execution

    async def get_stats_by_workflow(
        self,
        workflow_id: UUID,
    ) -> Dict[str, Any]:
        """
        Get aggregated statistics for a workflow.

        Args:
            workflow_id: Workflow UUID

        Returns:
            Dictionary with statistics
        """
        stmt = select(
            func.count(Execution.id).label("total_executions"),
            func.sum(Execution.llm_calls).label("total_llm_calls"),
            func.sum(Execution.llm_tokens).label("total_llm_tokens"),
            func.sum(Execution.llm_cost).label("total_llm_cost"),
            func.avg(
                func.extract("epoch", Execution.completed_at - Execution.started_at)
            ).label("avg_duration_seconds"),
        ).filter(
            Execution.workflow_id == workflow_id,
            Execution.status == "completed",
        )

        result = await self._session.execute(stmt)
        row = result.one()

        return {
            "total_executions": row.total_executions or 0,
            "total_llm_calls": row.total_llm_calls or 0,
            "total_llm_tokens": row.total_llm_tokens or 0,
            "total_llm_cost": float(row.total_llm_cost or 0),
            "avg_duration_seconds": float(row.avg_duration_seconds or 0),
        }
