# =============================================================================
# IPA Platform - Workflow Repository
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Repository for Workflow model operations.
# Provides specialized methods for workflow management.
# =============================================================================

from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.workflow import Workflow
from src.infrastructure.database.repositories.base import BaseRepository


class WorkflowRepository(BaseRepository[Workflow]):
    """
    Repository for Workflow model operations.

    Extends BaseRepository with workflow-specific methods:
        - get_by_trigger_type: List workflows by trigger type
        - get_active: List only active workflows
        - get_by_creator: List workflows created by a user
        - activate/deactivate: Status management
    """

    model = Workflow

    async def get_by_trigger_type(
        self,
        trigger_type: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Workflow], int]:
        """
        List workflows by trigger type.

        Args:
            trigger_type: Trigger type (manual, schedule, webhook, event)
            page: Page number
            page_size: Records per page

        Returns:
            Tuple of (workflows list, total count)
        """
        return await self.list(
            page=page, page_size=page_size, trigger_type=trigger_type
        )

    async def get_active(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Workflow], int]:
        """
        List only active workflows.

        Args:
            page: Page number
            page_size: Records per page

        Returns:
            Tuple of (workflows list, total count)
        """
        return await self.list(page=page, page_size=page_size, status="active")

    async def get_by_creator(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Workflow], int]:
        """
        List workflows created by a specific user.

        Args:
            user_id: Creator's user ID
            page: Page number
            page_size: Records per page

        Returns:
            Tuple of (workflows list, total count)
        """
        return await self.list(page=page, page_size=page_size, created_by=user_id)

    async def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Workflow], int]:
        """
        Search workflows by name or description.

        Args:
            query: Search query string
            page: Page number
            page_size: Records per page

        Returns:
            Tuple of (matching workflows, total count)
        """
        search_pattern = f"%{query}%"
        stmt = select(Workflow).filter(
            (Workflow.name.ilike(search_pattern))
            | (Workflow.description.ilike(search_pattern))
        )

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Paginate
        offset = (page - 1) * page_size
        stmt = stmt.order_by(Workflow.name).offset(offset).limit(page_size)

        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def increment_version(self, id: UUID) -> Optional[Workflow]:
        """
        Increment workflow version number.

        Args:
            id: Workflow UUID

        Returns:
            Updated workflow or None if not found
        """
        workflow = await self.get(id)
        if workflow is None:
            return None

        workflow.version += 1
        await self._session.flush()
        await self._session.refresh(workflow)
        return workflow

    async def activate(self, id: UUID) -> Optional[Workflow]:
        """
        Set workflow status to active.

        Args:
            id: Workflow UUID

        Returns:
            Updated workflow or None if not found
        """
        return await self.update(id, status="active")

    async def deactivate(self, id: UUID) -> Optional[Workflow]:
        """
        Set workflow status to inactive.

        Args:
            id: Workflow UUID

        Returns:
            Updated workflow or None if not found
        """
        return await self.update(id, status="inactive")

    async def archive(self, id: UUID) -> Optional[Workflow]:
        """
        Set workflow status to archived.

        Args:
            id: Workflow UUID

        Returns:
            Updated workflow or None if not found
        """
        return await self.update(id, status="archived")

    async def get_scheduled_workflows(self) -> List[Workflow]:
        """
        Get all active workflows with schedule triggers.

        Returns:
            List of workflows with schedule triggers
        """
        stmt = (
            select(Workflow)
            .filter(Workflow.trigger_type == "schedule")
            .filter(Workflow.status == "active")
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
