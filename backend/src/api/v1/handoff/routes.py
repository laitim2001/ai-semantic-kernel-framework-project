# =============================================================================
# IPA Platform - Handoff API Routes
# =============================================================================
# Sprint 8: Agent Handoff & Collaboration (Phase 2)
#
# API endpoints for Agent handoff and capability matching.
# Endpoints:
#   - POST /handoff/trigger - Trigger a handoff
#   - GET /handoff/{id}/status - Get handoff status
#   - POST /handoff/{id}/cancel - Cancel a handoff
#   - GET /handoff/history - Get handoff history
#   - POST /handoff/capability/match - Find matching agents
#   - GET /handoff/agents/{id}/capabilities - Get agent capabilities
#
# References:
#   - Sprint 8 Plan: docs/03-implementation/sprint-planning/phase-2/sprint-8-plan.md
# =============================================================================

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, status

from src.api.v1.handoff.schemas import (
    AgentCapabilitiesResponse,
    AgentCapabilitySchema,
    CapabilityCategoryEnum,
    CapabilityMatchRequest,
    CapabilityMatchResponse,
    CapabilityMatchResult,
    HandoffCancelRequest,
    HandoffCancelResponse,
    HandoffErrorResponse,
    HandoffHistoryItem,
    HandoffHistoryResponse,
    HandoffPolicyEnum,
    HandoffStatusEnum,
    HandoffStatusResponse,
    HandoffTriggerRequest,
    HandoffTriggerResponse,
    MatchStrategyEnum,
    RegisterCapabilityRequest,
    RegisterCapabilityResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/handoff", tags=["Handoff"])

# =============================================================================
# In-Memory Storage (for demonstration)
# =============================================================================

# Handoff records storage
_handoffs: Dict[UUID, Dict[str, Any]] = {}

# Agent capabilities storage
_agent_capabilities: Dict[UUID, List[Dict[str, Any]]] = {}

# Agent availability
_agent_availability: Dict[UUID, Dict[str, Any]] = {}


# =============================================================================
# Handoff Trigger Endpoints
# =============================================================================

@router.post(
    "/trigger",
    response_model=HandoffTriggerResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": HandoffErrorResponse},
        404: {"model": HandoffErrorResponse},
    },
    summary="Trigger Agent Handoff",
    description="Initiate a handoff from source agent to target agent",
)
async def trigger_handoff(
    request: HandoffTriggerRequest,
) -> HandoffTriggerResponse:
    """
    Trigger a handoff between agents.

    This endpoint initiates the handoff process, transferring task
    execution from the source agent to a target agent.

    If target_agent_id is not provided, the system will attempt
    to find the best matching agent based on required_capabilities.
    """
    logger.info(
        f"Handoff trigger requested: {request.source_agent_id} -> "
        f"{request.target_agent_id or 'auto-match'}"
    )

    # Generate handoff ID
    handoff_id = uuid4()

    # Determine target agent
    target_agent_id = request.target_agent_id
    if not target_agent_id and request.required_capabilities:
        # Auto-match based on capabilities
        target_agent_id = _find_matching_agent(
            request.required_capabilities,
            exclude=[request.source_agent_id],
        )

    # Create handoff record
    now = datetime.utcnow()
    handoff = {
        "handoff_id": handoff_id,
        "status": HandoffStatusEnum.INITIATED,
        "source_agent_id": request.source_agent_id,
        "target_agent_id": target_agent_id,
        "policy": request.policy,
        "context": request.context,
        "progress": 0.0,
        "context_transferred": False,
        "initiated_at": now,
        "completed_at": None,
        "reason": request.reason,
        "metadata": request.metadata,
    }
    _handoffs[handoff_id] = handoff

    logger.info(f"Handoff {handoff_id} initiated successfully")

    return HandoffTriggerResponse(
        handoff_id=handoff_id,
        status=HandoffStatusEnum.INITIATED,
        source_agent_id=request.source_agent_id,
        target_agent_id=target_agent_id,
        initiated_at=now,
        message="Handoff initiated successfully",
    )


@router.get(
    "/{handoff_id}/status",
    response_model=HandoffStatusResponse,
    responses={
        404: {"model": HandoffErrorResponse},
    },
    summary="Get Handoff Status",
    description="Get the current status of a handoff",
)
async def get_handoff_status(
    handoff_id: UUID,
) -> HandoffStatusResponse:
    """
    Get the current status of a handoff.

    Returns detailed information about the handoff progress,
    including transfer status and any error messages.
    """
    if handoff_id not in _handoffs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Handoff {handoff_id} not found",
        )

    handoff = _handoffs[handoff_id]

    return HandoffStatusResponse(
        handoff_id=handoff["handoff_id"],
        status=handoff["status"],
        source_agent_id=handoff["source_agent_id"],
        target_agent_id=handoff["target_agent_id"],
        policy=handoff["policy"],
        progress=handoff["progress"],
        context_transferred=handoff["context_transferred"],
        initiated_at=handoff["initiated_at"],
        completed_at=handoff.get("completed_at"),
        error_message=handoff.get("error_message"),
        metadata=handoff.get("metadata", {}),
    )


@router.post(
    "/{handoff_id}/cancel",
    response_model=HandoffCancelResponse,
    responses={
        400: {"model": HandoffErrorResponse},
        404: {"model": HandoffErrorResponse},
    },
    summary="Cancel Handoff",
    description="Cancel an in-progress handoff",
)
async def cancel_handoff(
    handoff_id: UUID,
    request: Optional[HandoffCancelRequest] = None,
) -> HandoffCancelResponse:
    """
    Cancel an in-progress handoff.

    If the handoff has already begun transferring, a rollback
    will be attempted to restore the source agent's state.
    """
    if handoff_id not in _handoffs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Handoff {handoff_id} not found",
        )

    handoff = _handoffs[handoff_id]

    # Check if cancellable
    if handoff["status"] in (
        HandoffStatusEnum.COMPLETED,
        HandoffStatusEnum.CANCELLED,
        HandoffStatusEnum.ROLLED_BACK,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Handoff {handoff_id} cannot be cancelled (status: {handoff['status']})",
        )

    # Perform cancellation
    now = datetime.utcnow()
    rollback_needed = handoff["context_transferred"]

    handoff["status"] = (
        HandoffStatusEnum.ROLLED_BACK if rollback_needed
        else HandoffStatusEnum.CANCELLED
    )
    handoff["completed_at"] = now

    if request and request.reason:
        handoff["metadata"]["cancel_reason"] = request.reason

    logger.info(
        f"Handoff {handoff_id} cancelled"
        f"{' with rollback' if rollback_needed else ''}"
    )

    return HandoffCancelResponse(
        handoff_id=handoff_id,
        status=handoff["status"],
        cancelled_at=now,
        rollback_performed=rollback_needed,
        message=(
            "Handoff cancelled with rollback"
            if rollback_needed
            else "Handoff cancelled successfully"
        ),
    )


@router.get(
    "/history",
    response_model=HandoffHistoryResponse,
    summary="Get Handoff History",
    description="Get paginated handoff history",
)
async def get_handoff_history(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    source_agent_id: Optional[UUID] = Query(
        default=None,
        description="Filter by source agent",
    ),
    target_agent_id: Optional[UUID] = Query(
        default=None,
        description="Filter by target agent",
    ),
    status_filter: Optional[HandoffStatusEnum] = Query(
        default=None,
        alias="status",
        description="Filter by status",
    ),
) -> HandoffHistoryResponse:
    """
    Get handoff history with pagination and filtering.

    Supports filtering by source agent, target agent, and status.
    Results are sorted by initiation time (newest first).
    """
    # Filter handoffs
    filtered = list(_handoffs.values())

    if source_agent_id:
        filtered = [h for h in filtered if h["source_agent_id"] == source_agent_id]

    if target_agent_id:
        filtered = [h for h in filtered if h["target_agent_id"] == target_agent_id]

    if status_filter:
        filtered = [h for h in filtered if h["status"] == status_filter]

    # Sort by initiated_at descending
    filtered.sort(key=lambda h: h["initiated_at"], reverse=True)

    # Paginate
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = filtered[start:end]

    # Convert to response items
    items = []
    for h in page_items:
        duration = None
        if h.get("completed_at") and h.get("initiated_at"):
            duration = (h["completed_at"] - h["initiated_at"]).total_seconds()

        items.append(HandoffHistoryItem(
            handoff_id=h["handoff_id"],
            status=h["status"],
            source_agent_id=h["source_agent_id"],
            target_agent_id=h["target_agent_id"],
            policy=h["policy"],
            initiated_at=h["initiated_at"],
            completed_at=h.get("completed_at"),
            duration_seconds=duration,
            reason=h.get("reason"),
        ))

    return HandoffHistoryResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=end < total,
    )


# =============================================================================
# Capability Matching Endpoints
# =============================================================================

@router.post(
    "/capability/match",
    response_model=CapabilityMatchResponse,
    summary="Find Matching Agents",
    description="Find agents matching capability requirements",
)
async def match_capabilities(
    request: CapabilityMatchRequest,
) -> CapabilityMatchResponse:
    """
    Find agents that match the specified capability requirements.

    Uses the specified strategy to select and rank matching agents.
    Can filter by availability and exclude specific agents.
    """
    logger.info(
        f"Capability match requested: {len(request.requirements)} requirements, "
        f"strategy={request.strategy}"
    )

    matches: List[CapabilityMatchResult] = []
    exclude_set = set(request.exclude_agents)

    # Evaluate each agent
    for agent_id, capabilities in _agent_capabilities.items():
        if agent_id in exclude_set:
            continue

        # Check availability if requested
        availability = _agent_availability.get(agent_id, {})
        is_available = availability.get("is_available", True)
        current_load = availability.get("current_load", 0.0)

        if request.check_availability and not is_available:
            continue

        # Calculate match score
        score, capability_scores, missing = _calculate_match_score(
            capabilities,
            request.requirements,
        )

        # Skip if missing required capabilities
        if missing:
            continue

        matches.append(CapabilityMatchResult(
            agent_id=agent_id,
            score=score,
            capability_scores=capability_scores,
            missing_capabilities=[],
            is_available=is_available,
            current_load=current_load,
        ))

    # Sort by strategy
    if request.strategy == MatchStrategyEnum.BEST_FIT:
        matches.sort(key=lambda m: m.score, reverse=True)
    elif request.strategy == MatchStrategyEnum.LEAST_LOADED:
        matches.sort(key=lambda m: (m.current_load, -m.score))
    # FIRST_FIT and ROUND_ROBIN use default order

    # Limit results
    matches = matches[:request.max_results]

    best_match = matches[0] if matches else None

    return CapabilityMatchResponse(
        matches=matches,
        total_candidates=len(_agent_capabilities),
        strategy_used=request.strategy,
        best_match=best_match,
    )


@router.get(
    "/agents/{agent_id}/capabilities",
    response_model=AgentCapabilitiesResponse,
    responses={
        404: {"model": HandoffErrorResponse},
    },
    summary="Get Agent Capabilities",
    description="Get all capabilities registered for an agent",
)
async def get_agent_capabilities(
    agent_id: UUID,
) -> AgentCapabilitiesResponse:
    """
    Get the capabilities registered for a specific agent.

    Returns all capabilities with their proficiency levels
    and categories.
    """
    if agent_id not in _agent_capabilities:
        # Return empty list for unknown agents (not error)
        return AgentCapabilitiesResponse(
            agent_id=agent_id,
            capabilities=[],
            total_capabilities=0,
        )

    capabilities = _agent_capabilities[agent_id]

    cap_schemas = [
        AgentCapabilitySchema(
            id=cap["id"],
            name=cap["name"],
            description=cap.get("description", ""),
            category=cap["category"],
            proficiency_level=cap["proficiency_level"],
            created_at=cap["created_at"],
        )
        for cap in capabilities
    ]

    return AgentCapabilitiesResponse(
        agent_id=agent_id,
        capabilities=cap_schemas,
        total_capabilities=len(cap_schemas),
    )


@router.post(
    "/agents/{agent_id}/capabilities",
    response_model=RegisterCapabilityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Agent Capability",
    description="Register a new capability for an agent",
)
async def register_capability(
    agent_id: UUID,
    request: RegisterCapabilityRequest,
) -> RegisterCapabilityResponse:
    """
    Register a new capability for an agent.

    If the agent already has this capability, it will be updated
    with the new proficiency level.
    """
    capability_id = uuid4()
    now = datetime.utcnow()

    capability = {
        "id": capability_id,
        "name": request.name,
        "description": request.description,
        "category": request.category,
        "proficiency_level": request.proficiency_level,
        "created_at": now,
    }

    # Initialize agent's capability list if needed
    if agent_id not in _agent_capabilities:
        _agent_capabilities[agent_id] = []

    # Check for existing capability with same name
    existing = next(
        (c for c in _agent_capabilities[agent_id] if c["name"] == request.name),
        None,
    )
    if existing:
        # Update existing
        existing["proficiency_level"] = request.proficiency_level
        existing["description"] = request.description
        existing["category"] = request.category
        capability_id = existing["id"]
        logger.info(f"Updated capability {request.name} for agent {agent_id}")
    else:
        # Add new
        _agent_capabilities[agent_id].append(capability)
        logger.info(f"Registered capability {request.name} for agent {agent_id}")

    return RegisterCapabilityResponse(
        capability_id=capability_id,
        agent_id=agent_id,
        name=request.name,
        message=(
            f"Capability '{request.name}' "
            f"{'updated' if existing else 'registered'} successfully"
        ),
    )


@router.delete(
    "/agents/{agent_id}/capabilities/{capability_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove Agent Capability",
    description="Remove a capability from an agent",
)
async def remove_capability(
    agent_id: UUID,
    capability_name: str,
) -> None:
    """
    Remove a capability from an agent.

    If the capability doesn't exist, the operation succeeds silently.
    """
    if agent_id not in _agent_capabilities:
        return

    _agent_capabilities[agent_id] = [
        c for c in _agent_capabilities[agent_id]
        if c["name"] != capability_name
    ]

    logger.info(f"Removed capability {capability_name} from agent {agent_id}")


# =============================================================================
# Helper Functions
# =============================================================================

def _find_matching_agent(
    required_capabilities: List[str],
    exclude: List[UUID],
) -> Optional[UUID]:
    """Find the best matching agent for required capabilities."""
    exclude_set = set(exclude)
    best_agent = None
    best_score = 0.0

    for agent_id, capabilities in _agent_capabilities.items():
        if agent_id in exclude_set:
            continue

        # Check if agent has all required capabilities
        cap_names = {c["name"] for c in capabilities}
        if not all(req in cap_names for req in required_capabilities):
            continue

        # Calculate simple score (average proficiency)
        relevant_caps = [
            c for c in capabilities
            if c["name"] in required_capabilities
        ]
        if relevant_caps:
            score = sum(c["proficiency_level"] for c in relevant_caps) / len(relevant_caps)
            if score > best_score:
                best_score = score
                best_agent = agent_id

    return best_agent


def _calculate_match_score(
    agent_capabilities: List[Dict[str, Any]],
    requirements: List[Any],
) -> tuple[float, Dict[str, float], List[str]]:
    """Calculate match score for agent against requirements."""
    cap_map = {c["name"]: c for c in agent_capabilities}
    capability_scores: Dict[str, float] = {}
    missing: List[str] = []
    total_weight = 0.0
    weighted_score = 0.0

    for req in requirements:
        cap = cap_map.get(req.capability_name)

        if cap is None:
            if req.required:
                missing.append(req.capability_name)
            capability_scores[req.capability_name] = 0.0
            continue

        # Score based on proficiency
        proficiency = cap["proficiency_level"]
        if proficiency >= req.min_proficiency:
            score = min(1.0, proficiency + 0.1)
        else:
            score = proficiency * 0.5

        capability_scores[req.capability_name] = score
        weighted_score += score * req.weight
        total_weight += req.weight

    overall_score = weighted_score / total_weight if total_weight > 0 else 0.0

    return overall_score, capability_scores, missing
