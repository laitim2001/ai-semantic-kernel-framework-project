"""Expert Management API routes.

Provides read-only access to the Agent Expert Registry and a
hot-reload endpoint for refreshing YAML definitions at runtime.

Sprint 162 — Phase 46 Agent Expert Registry.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.integrations.orchestration.experts.registry import get_registry, reset_registry

from .schemas import ExpertListResponse, ExpertResponse, ReloadResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/experts", tags=["Experts"])


@router.get("/", response_model=ExpertListResponse)
async def list_experts(
    domain: Optional[str] = Query(None, description="Filter by domain"),
) -> ExpertListResponse:
    """List all registered experts, optionally filtered by domain."""
    registry = get_registry()

    if domain:
        experts = registry.list_by_domain(domain)
    else:
        experts = registry.list_all()

    return ExpertListResponse(
        experts=[ExpertResponse(**e.to_dict()) for e in experts],
        total=len(experts),
    )


@router.get("/{name}", response_model=ExpertResponse)
async def get_expert(name: str) -> ExpertResponse:
    """Get a single expert definition by name."""
    registry = get_registry()
    expert = registry.get(name)

    if expert is None:
        raise HTTPException(status_code=404, detail=f"Expert not found: {name}")

    return ExpertResponse(**expert.to_dict())


@router.post("/reload", response_model=ReloadResponse)
async def reload_experts() -> ReloadResponse:
    """Hot-reload all expert definitions from disk."""
    logger.info("API: triggering expert registry reload")

    # Reset singleton so it re-reads from disk
    reset_registry()
    registry = get_registry()

    names = registry.list_names()
    logger.info("API: registry reloaded — %d experts", len(names))

    return ReloadResponse(
        status="ok",
        experts_loaded=len(names),
        expert_names=names,
    )
