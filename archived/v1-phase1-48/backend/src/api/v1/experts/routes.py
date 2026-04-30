"""Expert Management API routes.

Full CRUD for Agent Expert definitions backed by PostgreSQL,
with YAML seeding for built-in experts.

Sprint 162 — Phase 46 Agent Expert Registry (read-only).
Sprint 163 — CRUD + DB persistence.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.agent_expert import AgentExpertRepository
from src.infrastructure.database.session import get_session
from src.integrations.orchestration.experts.registry import get_registry, reset_registry
from src.integrations.orchestration.experts.seeder import seed_builtin_experts

from .schemas import (
    ExpertCreateRequest,
    ExpertDetailResponse,
    ExpertListResponse,
    ExpertUpdateRequest,
    ReloadResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/experts", tags=["Experts"])


# ------------------------------------------------------------------
# Dependencies
# ------------------------------------------------------------------


async def _get_repo(
    session: AsyncSession = Depends(get_session),
) -> AgentExpertRepository:
    return AgentExpertRepository(session)


# ------------------------------------------------------------------
# READ
# ------------------------------------------------------------------


@router.get("/", response_model=ExpertListResponse)
async def list_experts(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    repo: AgentExpertRepository = Depends(_get_repo),
) -> ExpertListResponse:
    """List all experts from DB, optionally filtered."""
    experts = await repo.list_all(domain=domain, enabled=enabled)
    if not experts:
        # Fallback to YAML registry if DB is empty (first run before seeder)
        registry = get_registry()
        yaml_experts = registry.list_by_domain(domain) if domain else registry.list_all()
        return ExpertListResponse(
            experts=[ExpertDetailResponse(**e.to_dict(), id="", is_builtin=True, version=1) for e in yaml_experts],
            total=len(yaml_experts),
        )
    return ExpertListResponse(
        experts=[ExpertDetailResponse(**e.to_dict()) for e in experts],
        total=len(experts),
    )


@router.get("/{name}", response_model=ExpertDetailResponse)
async def get_expert(
    name: str,
    repo: AgentExpertRepository = Depends(_get_repo),
) -> ExpertDetailResponse:
    """Get a single expert by name."""
    expert = await repo.get_by_name(name)
    if expert is None:
        # Fallback to YAML registry
        registry = get_registry()
        yaml_expert = registry.get(name)
        if yaml_expert is None:
            raise HTTPException(status_code=404, detail=f"Expert not found: {name}")
        return ExpertDetailResponse(**yaml_expert.to_dict(), id="", is_builtin=True, version=1)
    return ExpertDetailResponse(**expert.to_dict())


# ------------------------------------------------------------------
# CREATE
# ------------------------------------------------------------------


@router.post("/", response_model=ExpertDetailResponse, status_code=201)
async def create_expert(
    request: ExpertCreateRequest,
    repo: AgentExpertRepository = Depends(_get_repo),
    session: AsyncSession = Depends(get_session),
) -> ExpertDetailResponse:
    """Create a new expert definition."""
    existing = await repo.get_by_name(request.name)
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"Expert already exists: {request.name}")

    expert = await repo.create(
        name=request.name,
        display_name=request.display_name,
        display_name_zh=request.display_name_zh,
        description=request.description,
        domain=request.domain,
        capabilities=request.capabilities,
        model=request.model,
        max_iterations=request.max_iterations,
        system_prompt=request.system_prompt,
        tools=request.tools,
        enabled=request.enabled,
        is_builtin=False,
        metadata_=request.metadata,
    )
    await session.commit()

    # Reload in-memory registry
    reset_registry()

    logger.info("Created expert: %s (domain=%s)", expert.name, expert.domain)
    return ExpertDetailResponse(**expert.to_dict())


# ------------------------------------------------------------------
# UPDATE
# ------------------------------------------------------------------


@router.put("/{name}", response_model=ExpertDetailResponse)
async def update_expert(
    name: str,
    request: ExpertUpdateRequest,
    repo: AgentExpertRepository = Depends(_get_repo),
    session: AsyncSession = Depends(get_session),
) -> ExpertDetailResponse:
    """Update an existing expert. Version is bumped automatically."""
    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    expert = await repo.update(name, **update_data)
    if expert is None:
        raise HTTPException(status_code=404, detail=f"Expert not found: {name}")

    await session.commit()

    # Reload in-memory registry
    reset_registry()

    logger.info("Updated expert: %s (version=%d)", expert.name, expert.version)
    return ExpertDetailResponse(**expert.to_dict())


# ------------------------------------------------------------------
# DELETE
# ------------------------------------------------------------------


@router.delete("/{name}", status_code=200)
async def delete_expert(
    name: str,
    repo: AgentExpertRepository = Depends(_get_repo),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Delete an expert. Built-in experts cannot be deleted."""
    expert = await repo.get_by_name(name)
    if expert is None:
        raise HTTPException(status_code=404, detail=f"Expert not found: {name}")

    if expert.is_builtin:
        raise HTTPException(status_code=403, detail="Cannot delete built-in expert")

    await repo.delete(name)
    await session.commit()

    # Reload in-memory registry
    reset_registry()

    logger.info("Deleted expert: %s", name)
    return {"status": "deleted", "name": name}


# ------------------------------------------------------------------
# RELOAD
# ------------------------------------------------------------------


@router.post("/reload", response_model=ReloadResponse)
async def reload_experts(
    session: AsyncSession = Depends(get_session),
) -> ReloadResponse:
    """Re-seed built-ins from YAML and reload the in-memory registry."""
    logger.info("API: triggering expert registry reload + re-seed")

    # Re-seed built-ins
    await seed_builtin_experts(session)

    # Reset in-memory registry
    reset_registry()
    registry = get_registry()
    names = registry.list_names()

    logger.info("API: registry reloaded — %d experts", len(names))
    return ReloadResponse(
        status="ok",
        experts_loaded=len(names),
        expert_names=names,
    )
