# =============================================================================
# IPA Platform - Agent Repository
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Repository for Agent model operations.
# Provides specialized methods for agent management.
# =============================================================================

from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.agent import Agent
from src.infrastructure.database.repositories.base import BaseRepository


class AgentRepository(BaseRepository[Agent]):
    """
    Repository for Agent model operations.

    Extends BaseRepository with agent-specific methods:
        - get_by_name: Find agent by unique name
        - get_by_category: List agents in a category
        - get_active: List only active agents
        - search: Full-text search on name and description
    """

    model = Agent

    async def get_by_name(self, name: str) -> Optional[Agent]:
        """
        Get an agent by its unique name.

        Args:
            name: Agent name

        Returns:
            Agent instance or None if not found
        """
        return await self.get_by(name=name)

    async def get_by_category(
        self,
        category: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Agent], int]:
        """
        List agents in a specific category.

        Args:
            category: Category name
            page: Page number
            page_size: Records per page

        Returns:
            Tuple of (agents list, total count)
        """
        return await self.list(page=page, page_size=page_size, category=category)

    async def get_active(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Agent], int]:
        """
        List only active agents.

        Args:
            page: Page number
            page_size: Records per page

        Returns:
            Tuple of (agents list, total count)
        """
        return await self.list(page=page, page_size=page_size, status="active")

    async def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Agent], int]:
        """
        Search agents by name or description.

        Args:
            query: Search query string
            page: Page number
            page_size: Records per page

        Returns:
            Tuple of (matching agents, total count)
        """
        search_pattern = f"%{query}%"
        stmt = select(Agent).filter(
            (Agent.name.ilike(search_pattern))
            | (Agent.description.ilike(search_pattern))
        )

        # Count
        from sqlalchemy import func

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Paginate
        offset = (page - 1) * page_size
        stmt = stmt.order_by(Agent.name).offset(offset).limit(page_size)

        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def increment_version(self, id: UUID) -> Optional[Agent]:
        """
        Increment agent version number.

        Args:
            id: Agent UUID

        Returns:
            Updated agent or None if not found
        """
        agent = await self.get(id)
        if agent is None:
            return None

        agent.version += 1
        await self._session.flush()
        await self._session.refresh(agent)
        return agent

    async def deactivate(self, id: UUID) -> Optional[Agent]:
        """
        Set agent status to inactive.

        Args:
            id: Agent UUID

        Returns:
            Updated agent or None if not found
        """
        return await self.update(id, status="inactive")

    async def activate(self, id: UUID) -> Optional[Agent]:
        """
        Set agent status to active.

        Args:
            id: Agent UUID

        Returns:
            Updated agent or None if not found
        """
        return await self.update(id, status="active")
