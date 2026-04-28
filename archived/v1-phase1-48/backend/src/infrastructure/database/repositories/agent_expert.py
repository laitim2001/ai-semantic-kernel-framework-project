# =============================================================================
# IPA Platform - Agent Expert Repository
# =============================================================================
# Sprint 163: Agent Expert CRUD + DB Persistence
# =============================================================================

from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.agent_expert import AgentExpert


class AgentExpertRepository:
    """Repository for AgentExpert CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs: Any) -> AgentExpert:
        """Create a new agent expert."""
        expert = AgentExpert(**kwargs)
        self._session.add(expert)
        await self._session.flush()
        await self._session.refresh(expert)
        return expert

    async def get_by_id(self, expert_id: str) -> Optional[AgentExpert]:
        """Get expert by UUID."""
        stmt = select(AgentExpert).where(AgentExpert.id == expert_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[AgentExpert]:
        """Get expert by unique name."""
        stmt = select(AgentExpert).where(AgentExpert.name == name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        domain: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> List[AgentExpert]:
        """List experts with optional filters."""
        stmt = select(AgentExpert).order_by(AgentExpert.name)
        if domain is not None:
            stmt = stmt.where(AgentExpert.domain == domain)
        if enabled is not None:
            stmt = stmt.where(AgentExpert.enabled == enabled)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, name: str, **kwargs: Any) -> Optional[AgentExpert]:
        """Update an expert by name. Bumps version automatically."""
        expert = await self.get_by_name(name)
        if expert is None:
            return None
        for key, value in kwargs.items():
            if key == "metadata":
                setattr(expert, "metadata_", value)
            elif hasattr(expert, key):
                setattr(expert, key, value)
        expert.version += 1
        await self._session.flush()
        await self._session.refresh(expert)
        return expert

    async def delete(self, name: str) -> bool:
        """Delete an expert by name. Returns False if not found."""
        expert = await self.get_by_name(name)
        if expert is None:
            return False
        await self._session.delete(expert)
        await self._session.flush()
        return True

    async def upsert_from_yaml(self, data: Dict[str, Any]) -> AgentExpert:
        """Insert from YAML if not exists. Skips if already in DB (idempotent)."""
        existing = await self.get_by_name(data["name"])
        if existing is not None:
            return existing
        return await self.create(
            name=data["name"],
            display_name=data.get("display_name", data["name"]),
            display_name_zh=data.get("display_name_zh", data.get("display_name", data["name"])),
            description=data.get("description", ""),
            domain=data.get("domain", "general"),
            capabilities=data.get("capabilities", []),
            model=data.get("model"),
            max_iterations=data.get("max_iterations", 5),
            system_prompt=data.get("system_prompt", ""),
            tools=data.get("tools", []),
            enabled=data.get("enabled", True),
            is_builtin=True,
            metadata_=data.get("metadata", {}),
        )

    async def count(self, **filters: Any) -> int:
        """Count experts matching filters."""
        stmt = select(func.count()).select_from(AgentExpert)
        for key, value in filters.items():
            if hasattr(AgentExpert, key):
                stmt = stmt.where(getattr(AgentExpert, key) == value)
        result = await self._session.execute(stmt)
        return result.scalar_one()
