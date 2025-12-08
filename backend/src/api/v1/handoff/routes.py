# =============================================================================
# IPA Platform - Handoff API Routes
# =============================================================================
# Sprint 29: API Routes 遷移 (Phase 5)
#
# API endpoints for Agent handoff and capability matching.
#
# Migration Notes (Sprint 29):
#   - Migrated from mock implementation to HandoffService adapter
#   - Uses HandoffService from integrations.agent_framework.builders
#   - Maintains backward compatibility with existing API schemas
#   - HITL endpoints preserved for future migration to WorkflowApprovalAdapter
#
# Endpoints:
#   - POST /handoff/trigger - Trigger a handoff
#   - GET /handoff/{id}/status - Get handoff status
#   - POST /handoff/{id}/cancel - Cancel a handoff
#   - GET /handoff/history - Get handoff history
#   - POST /handoff/capability/match - Find matching agents
#   - GET /handoff/agents/{id}/capabilities - Get agent capabilities
#
# References:
#   - Sprint 29 Plan: docs/03-implementation/sprint-planning/phase-5/sprint-29-plan.md
#   - HandoffService: src/integrations/agent_framework/builders/handoff_service.py
# =============================================================================

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status

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
    # Sprint 15: HITL Schemas
    HITLInputRequestSchema,
    HITLInputTypeEnum,
    HITLPendingRequestsResponse,
    HITLSessionListResponse,
    HITLSessionSchema,
    HITLSessionStatusEnum,
    HITLSubmitInputRequest,
    HITLSubmitInputResponse,
)

# =============================================================================
# Sprint 29: Import from Adapter Layer
# =============================================================================
from src.integrations.agent_framework.builders.handoff_service import (
    HandoffService,
    HandoffRequest,
    HandoffServiceStatus,
    create_handoff_service,
)
from src.integrations.agent_framework.builders.handoff_policy import (
    LegacyHandoffPolicy,
)
from src.integrations.agent_framework.builders.handoff_capability import (
    MatchStrategy,
    AgentCapabilityInfo,
    CapabilityRequirementInfo,
    CapabilityCategory,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/handoff", tags=["Handoff"])


# =============================================================================
# Dependency Injection (Sprint 29)
# =============================================================================

# Singleton service instance
_handoff_service: Optional[HandoffService] = None


def get_handoff_service() -> HandoffService:
    """
    Get or create the HandoffService singleton.

    Returns:
        HandoffService instance
    """
    global _handoff_service
    if _handoff_service is None:
        _handoff_service = create_handoff_service()
        logger.info("HandoffService initialized for API routes")
    return _handoff_service


def reset_handoff_service() -> None:
    """Reset the service instance (for testing)."""
    global _handoff_service
    _handoff_service = None


# =============================================================================
# Status Mapping Helpers
# =============================================================================

def _map_service_status_to_api(service_status: HandoffServiceStatus) -> HandoffStatusEnum:
    """Map HandoffServiceStatus to API HandoffStatusEnum."""
    mapping = {
        HandoffServiceStatus.INITIATED: HandoffStatusEnum.INITIATED,
        HandoffServiceStatus.MATCHING: HandoffStatusEnum.VALIDATING,
        HandoffServiceStatus.CONTEXT_TRANSFER: HandoffStatusEnum.TRANSFERRING,
        HandoffServiceStatus.EXECUTING: HandoffStatusEnum.TRANSFERRING,
        HandoffServiceStatus.WAITING_INPUT: HandoffStatusEnum.TRANSFERRING,
        HandoffServiceStatus.COMPLETED: HandoffStatusEnum.COMPLETED,
        HandoffServiceStatus.FAILED: HandoffStatusEnum.FAILED,
        HandoffServiceStatus.CANCELLED: HandoffStatusEnum.CANCELLED,
        HandoffServiceStatus.ROLLED_BACK: HandoffStatusEnum.ROLLED_BACK,
    }
    return mapping.get(service_status, HandoffStatusEnum.INITIATED)


def _map_api_policy_to_legacy(api_policy: HandoffPolicyEnum) -> LegacyHandoffPolicy:
    """Map API HandoffPolicyEnum to LegacyHandoffPolicy."""
    mapping = {
        HandoffPolicyEnum.IMMEDIATE: LegacyHandoffPolicy.IMMEDIATE,
        HandoffPolicyEnum.GRACEFUL: LegacyHandoffPolicy.GRACEFUL,
        HandoffPolicyEnum.CONDITIONAL: LegacyHandoffPolicy.CONDITIONAL,
    }
    return mapping.get(api_policy, LegacyHandoffPolicy.IMMEDIATE)


def _map_api_strategy_to_adapter(api_strategy: MatchStrategyEnum) -> MatchStrategy:
    """Map API MatchStrategyEnum to adapter MatchStrategy."""
    mapping = {
        MatchStrategyEnum.BEST_FIT: MatchStrategy.BEST_FIT,
        MatchStrategyEnum.FIRST_FIT: MatchStrategy.FIRST_FIT,
        MatchStrategyEnum.ROUND_ROBIN: MatchStrategy.ROUND_ROBIN,
        MatchStrategyEnum.LEAST_LOADED: MatchStrategy.LEAST_LOADED,
    }
    return mapping.get(api_strategy, MatchStrategy.BEST_FIT)


def _map_api_category_to_adapter(api_category: CapabilityCategoryEnum) -> CapabilityCategory:
    """Map API CapabilityCategoryEnum to adapter CapabilityCategory."""
    mapping = {
        CapabilityCategoryEnum.LANGUAGE: CapabilityCategory.LANGUAGE,
        CapabilityCategoryEnum.REASONING: CapabilityCategory.REASONING,
        CapabilityCategoryEnum.KNOWLEDGE: CapabilityCategory.KNOWLEDGE,
        CapabilityCategoryEnum.ACTION: CapabilityCategory.ACTION,
        CapabilityCategoryEnum.INTEGRATION: CapabilityCategory.INTEGRATION,
        CapabilityCategoryEnum.COMMUNICATION: CapabilityCategory.COMMUNICATION,
    }
    return mapping.get(api_category, CapabilityCategory.ACTION)


# =============================================================================
# HITL Storage (preserved for future migration to WorkflowApprovalAdapter)
# =============================================================================

_hitl_sessions: Dict[UUID, Dict[str, Any]] = {}
_hitl_requests: Dict[UUID, Dict[str, Any]] = {}


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
    service: HandoffService = Depends(get_handoff_service),
) -> HandoffTriggerResponse:
    """
    Trigger a handoff between agents.

    This endpoint initiates the handoff process, transferring task
    execution from the source agent to a target agent.

    If target_agent_id is not provided, the system will attempt
    to find the best matching agent based on required_capabilities.

    Sprint 29: Now uses HandoffService adapter instead of mock.
    """
    logger.info(
        f"Handoff trigger requested: {request.source_agent_id} -> "
        f"{request.target_agent_id or 'auto-match'}"
    )

    # Create HandoffRequest for service
    handoff_request = HandoffRequest(
        source_agent_id=request.source_agent_id,
        target_agent_id=request.target_agent_id,
        policy=_map_api_policy_to_legacy(request.policy),
        required_capabilities=request.required_capabilities,
        context=request.context,
        reason=request.reason or "",
        metadata=request.metadata,
    )

    # Trigger handoff via service
    result = await service.trigger_handoff(handoff_request)

    logger.info(f"Handoff {result.handoff_id} initiated successfully")

    return HandoffTriggerResponse(
        handoff_id=result.handoff_id,
        status=_map_service_status_to_api(result.status),
        source_agent_id=result.source_agent_id,
        target_agent_id=result.target_agent_id,
        initiated_at=result.initiated_at,
        message=result.message or "Handoff initiated successfully",
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
    service: HandoffService = Depends(get_handoff_service),
) -> HandoffStatusResponse:
    """
    Get the current status of a handoff.

    Returns detailed information about the handoff progress,
    including transfer status and any error messages.

    Sprint 29: Now uses HandoffService adapter.
    """
    result = service.get_handoff_status(handoff_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Handoff {handoff_id} not found",
        )

    return HandoffStatusResponse(
        handoff_id=result.handoff_id,
        status=_map_service_status_to_api(result.status),
        source_agent_id=result.source_agent_id,
        target_agent_id=result.target_agent_id,
        policy=HandoffPolicyEnum(result.policy.value),
        progress=result.progress,
        context_transferred=result.context_transferred,
        initiated_at=result.initiated_at,
        completed_at=result.completed_at,
        error_message=result.error_message,
        metadata=result.metadata,
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
    service: HandoffService = Depends(get_handoff_service),
) -> HandoffCancelResponse:
    """
    Cancel an in-progress handoff.

    If the handoff has already begun transferring, a rollback
    will be attempted to restore the source agent's state.

    Sprint 29: Now uses HandoffService adapter.
    """
    try:
        reason = request.reason if request else None
        result = await service.cancel_handoff(handoff_id, reason=reason)

        logger.info(
            f"Handoff {handoff_id} cancelled"
            f"{' with rollback' if result.rollback_performed else ''}"
        )

        return HandoffCancelResponse(
            handoff_id=result.handoff_id,
            status=_map_service_status_to_api(result.status),
            cancelled_at=result.cancelled_at,
            rollback_performed=result.rollback_performed,
            message=result.message or "Handoff cancelled successfully",
        )
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
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
    service: HandoffService = Depends(get_handoff_service),
) -> HandoffHistoryResponse:
    """
    Get handoff history with pagination and filtering.

    Supports filtering by source agent, target agent, and status.
    Results are sorted by initiation time (newest first).

    Sprint 29: Now uses HandoffService adapter.
    """
    # Map API status filter to service status
    service_status = None
    if status_filter:
        reverse_mapping = {
            HandoffStatusEnum.INITIATED: HandoffServiceStatus.INITIATED,
            HandoffStatusEnum.VALIDATING: HandoffServiceStatus.MATCHING,
            HandoffStatusEnum.TRANSFERRING: HandoffServiceStatus.CONTEXT_TRANSFER,
            HandoffStatusEnum.COMPLETED: HandoffServiceStatus.COMPLETED,
            HandoffStatusEnum.FAILED: HandoffServiceStatus.FAILED,
            HandoffStatusEnum.CANCELLED: HandoffServiceStatus.CANCELLED,
            HandoffStatusEnum.ROLLED_BACK: HandoffServiceStatus.ROLLED_BACK,
        }
        service_status = reverse_mapping.get(status_filter)

    # Get history from service
    records, total = service.get_handoff_history(
        source_agent_id=source_agent_id,
        target_agent_id=target_agent_id,
        status_filter=service_status,
        page=page,
        page_size=page_size,
    )

    # Convert to response items
    items = []
    for record in records:
        duration = None
        if record.completed_at and record.initiated_at:
            duration = (record.completed_at - record.initiated_at).total_seconds()

        items.append(HandoffHistoryItem(
            handoff_id=record.handoff_id,
            status=_map_service_status_to_api(record.status),
            source_agent_id=record.source_agent_id,
            target_agent_id=record.target_agent_id,
            policy=HandoffPolicyEnum(record.policy.value),
            initiated_at=record.initiated_at,
            completed_at=record.completed_at,
            duration_seconds=duration,
            reason=record.reason,
        ))

    return HandoffHistoryResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
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
    service: HandoffService = Depends(get_handoff_service),
) -> CapabilityMatchResponse:
    """
    Find agents that match the specified capability requirements.

    Uses the specified strategy to select and rank matching agents.
    Can filter by availability and exclude specific agents.

    Sprint 29: Now uses HandoffService.capability_matcher adapter.
    """
    logger.info(
        f"Capability match requested: {len(request.requirements)} requirements, "
        f"strategy={request.strategy}"
    )

    # Convert API requirements to adapter format
    adapter_requirements = [
        CapabilityRequirementInfo(
            name=req.capability_name,
            min_proficiency=req.min_proficiency,
            category=_map_api_category_to_adapter(req.category) if req.category else None,
            required=req.required,
            weight=req.weight,
        )
        for req in request.requirements
    ]

    # Find matching agents
    matches = service.find_matching_agents(
        requirements=adapter_requirements,
        strategy=_map_api_strategy_to_adapter(request.strategy),
        exclude_agents=set(request.exclude_agents) if request.exclude_agents else None,
        check_availability=request.check_availability,
        max_results=request.max_results,
    )

    # Convert to response format
    response_matches = []
    for match in matches:
        # Convert agent_id string back to UUID if possible
        try:
            agent_uuid = UUID(match.agent_id)
        except ValueError:
            agent_uuid = uuid4()  # Fallback

        availability = match.availability
        response_matches.append(CapabilityMatchResult(
            agent_id=agent_uuid,
            score=match.score,
            capability_scores=match.capability_scores,
            missing_capabilities=match.missing_capabilities,
            is_available=match.is_available,
            current_load=availability.current_load if availability else 0.0,
        ))

    best_match = response_matches[0] if response_matches else None

    return CapabilityMatchResponse(
        matches=response_matches,
        total_candidates=service.capability_matcher.agent_count,
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
    service: HandoffService = Depends(get_handoff_service),
) -> AgentCapabilitiesResponse:
    """
    Get the capabilities registered for a specific agent.

    Returns all capabilities with their proficiency levels
    and categories.

    Sprint 29: Now uses HandoffService adapter.
    """
    capabilities = service.get_agent_capabilities(agent_id)

    cap_schemas = [
        AgentCapabilitySchema(
            id=uuid4(),  # Generate ID since adapter doesn't track
            name=cap.name,
            description=cap.description,
            category=CapabilityCategoryEnum(cap.category.value),
            proficiency_level=cap.proficiency,
            created_at=datetime.utcnow(),
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
    service: HandoffService = Depends(get_handoff_service),
) -> RegisterCapabilityResponse:
    """
    Register a new capability for an agent.

    If the agent already has this capability, it will be updated
    with the new proficiency level.

    Sprint 29: Now uses HandoffService adapter.
    """
    capability_id = uuid4()

    # Get existing capabilities
    existing_caps = service.get_agent_capabilities(agent_id)

    # Check if updating or creating
    existing = next(
        (c for c in existing_caps if c.name == request.name),
        None,
    )
    is_update = existing is not None

    # Create new capability info
    new_capability = AgentCapabilityInfo(
        name=request.name,
        proficiency=request.proficiency_level,
        category=_map_api_category_to_adapter(request.category),
        description=request.description,
    )

    # Update capabilities list
    if is_update:
        # Remove old, add new
        updated_caps = [c for c in existing_caps if c.name != request.name]
        updated_caps.append(new_capability)
    else:
        updated_caps = list(existing_caps)
        updated_caps.append(new_capability)

    # Register updated capabilities
    service.register_agent_capabilities(agent_id, updated_caps)

    logger.info(
        f"{'Updated' if is_update else 'Registered'} capability {request.name} "
        f"for agent {agent_id}"
    )

    return RegisterCapabilityResponse(
        capability_id=capability_id,
        agent_id=agent_id,
        name=request.name,
        message=(
            f"Capability '{request.name}' "
            f"{'updated' if is_update else 'registered'} successfully"
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
    service: HandoffService = Depends(get_handoff_service),
) -> None:
    """
    Remove a capability from an agent.

    If the capability doesn't exist, the operation succeeds silently.

    Sprint 29: Now uses HandoffService adapter.
    """
    existing_caps = service.get_agent_capabilities(agent_id)

    if not existing_caps:
        return

    # Filter out the capability to remove
    updated_caps = [c for c in existing_caps if c.name != capability_name]

    if len(updated_caps) != len(existing_caps):
        # Re-register without the removed capability
        service.register_agent_capabilities(agent_id, updated_caps)
        logger.info(f"Removed capability {capability_name} from agent {agent_id}")


# =============================================================================
# HITL (Human-in-the-Loop) Endpoints - Sprint 15
# NOTE: These endpoints are preserved for backward compatibility.
# Future migration to WorkflowApprovalAdapter (Sprint 28) is planned.
# =============================================================================


@router.get(
    "/hitl/sessions",
    response_model=HITLSessionListResponse,
    summary="List HITL Sessions",
    description="Get list of active HITL sessions",
    tags=["Handoff", "HITL"],
)
async def list_hitl_sessions(
    status_filter: Optional[HITLSessionStatusEnum] = Query(
        default=None,
        alias="status",
        description="Filter by session status",
    ),
    handoff_execution_id: Optional[UUID] = Query(
        default=None,
        description="Filter by handoff execution ID",
    ),
) -> HITLSessionListResponse:
    """
    List HITL sessions.

    Returns active sessions that are waiting for user input
    or recently completed.

    NOTE: This endpoint uses in-memory storage.
    Future migration to WorkflowApprovalAdapter planned.
    """
    sessions = list(_hitl_sessions.values())

    # Filter by status
    if status_filter:
        sessions = [s for s in sessions if s["status"] == status_filter.value]

    # Filter by handoff execution
    if handoff_execution_id:
        sessions = [
            s for s in sessions
            if s.get("handoff_execution_id") == handoff_execution_id
        ]

    # Convert to response schema
    session_schemas = []
    for s in sessions:
        current_request = None
        if s.get("current_request_id"):
            req = _hitl_requests.get(s["current_request_id"])
            if req:
                current_request = HITLInputRequestSchema(
                    request_id=req["request_id"],
                    session_id=s["session_id"],
                    prompt=req["prompt"],
                    awaiting_agent_id=req.get("awaiting_agent_id", ""),
                    input_type=HITLInputTypeEnum(req.get("input_type", "text")),
                    choices=req.get("choices", []),
                    default_value=req.get("default_value"),
                    timeout_seconds=req.get("timeout_seconds", 300),
                    expires_at=req["expires_at"],
                    conversation_summary=req.get("conversation_summary", ""),
                )

        session_schemas.append(HITLSessionSchema(
            session_id=s["session_id"],
            handoff_execution_id=s.get("handoff_execution_id"),
            status=HITLSessionStatusEnum(s["status"]),
            created_at=s["created_at"],
            updated_at=s["updated_at"],
            completed_at=s.get("completed_at"),
            current_request=current_request,
            history_count=len(s.get("history", [])),
        ))

    return HITLSessionListResponse(
        sessions=session_schemas,
        total=len(session_schemas),
    )


@router.get(
    "/hitl/sessions/{session_id}",
    response_model=HITLSessionSchema,
    responses={
        404: {"model": HandoffErrorResponse},
    },
    summary="Get HITL Session",
    description="Get details of a specific HITL session",
    tags=["Handoff", "HITL"],
)
async def get_hitl_session(
    session_id: UUID,
) -> HITLSessionSchema:
    """
    Get details of a specific HITL session.
    """
    if session_id not in _hitl_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"HITL session {session_id} not found",
        )

    s = _hitl_sessions[session_id]

    current_request = None
    if s.get("current_request_id"):
        req = _hitl_requests.get(s["current_request_id"])
        if req:
            current_request = HITLInputRequestSchema(
                request_id=req["request_id"],
                session_id=session_id,
                prompt=req["prompt"],
                awaiting_agent_id=req.get("awaiting_agent_id", ""),
                input_type=HITLInputTypeEnum(req.get("input_type", "text")),
                choices=req.get("choices", []),
                default_value=req.get("default_value"),
                timeout_seconds=req.get("timeout_seconds", 300),
                expires_at=req["expires_at"],
                conversation_summary=req.get("conversation_summary", ""),
            )

    return HITLSessionSchema(
        session_id=s["session_id"],
        handoff_execution_id=s.get("handoff_execution_id"),
        status=HITLSessionStatusEnum(s["status"]),
        created_at=s["created_at"],
        updated_at=s["updated_at"],
        completed_at=s.get("completed_at"),
        current_request=current_request,
        history_count=len(s.get("history", [])),
    )


@router.get(
    "/hitl/pending",
    response_model=HITLPendingRequestsResponse,
    summary="Get Pending HITL Requests",
    description="Get all pending HITL input requests",
    tags=["Handoff", "HITL"],
)
async def get_pending_hitl_requests() -> HITLPendingRequestsResponse:
    """
    Get all pending HITL input requests.

    Returns requests that are waiting for user input,
    sorted by urgency (expiring soon first).
    """
    now = datetime.utcnow()
    pending = []

    for req in _hitl_requests.values():
        if req.get("responded"):
            continue

        # Check if expired
        if req["expires_at"] < now:
            continue

        session = _hitl_sessions.get(req["session_id"])
        if not session or session["status"] != "active":
            continue

        pending.append(HITLInputRequestSchema(
            request_id=req["request_id"],
            session_id=req["session_id"],
            prompt=req["prompt"],
            awaiting_agent_id=req.get("awaiting_agent_id", ""),
            input_type=HITLInputTypeEnum(req.get("input_type", "text")),
            choices=req.get("choices", []),
            default_value=req.get("default_value"),
            timeout_seconds=req.get("timeout_seconds", 300),
            expires_at=req["expires_at"],
            conversation_summary=req.get("conversation_summary", ""),
        ))

    # Sort by expires_at (urgency)
    pending.sort(key=lambda r: r.expires_at)

    return HITLPendingRequestsResponse(
        requests=pending,
        total=len(pending),
    )


@router.post(
    "/hitl/submit",
    response_model=HITLSubmitInputResponse,
    responses={
        400: {"model": HandoffErrorResponse},
        404: {"model": HandoffErrorResponse},
    },
    summary="Submit HITL Input",
    description="Submit user input for a HITL request",
    tags=["Handoff", "HITL"],
)
async def submit_hitl_input(
    request: HITLSubmitInputRequest,
) -> HITLSubmitInputResponse:
    """
    Submit user input for a HITL request.

    This resumes the handoff workflow with the user's input.
    """
    if request.request_id not in _hitl_requests:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"HITL request {request.request_id} not found",
        )

    req = _hitl_requests[request.request_id]

    if req.get("responded"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"HITL request {request.request_id} already responded",
        )

    # Check expiration
    now = datetime.utcnow()
    if req["expires_at"] < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"HITL request {request.request_id} has expired",
        )

    # Update request
    response_id = uuid4()
    req["responded"] = True
    req["response_id"] = response_id
    req["input_value"] = request.input_value
    req["responded_at"] = now
    req["user_id"] = request.user_id

    # Update session
    session_id = req["session_id"]
    if session_id in _hitl_sessions:
        session = _hitl_sessions[session_id]
        session["status"] = "input_received"
        session["updated_at"] = now
        session["current_request_id"] = None
        session["history"].append({
            "type": "response",
            "request_id": str(request.request_id),
            "response_id": str(response_id),
            "timestamp": now.isoformat(),
        })

    logger.info(
        f"HITL input submitted: request={request.request_id}, "
        f"session={session_id}"
    )

    return HITLSubmitInputResponse(
        response_id=response_id,
        request_id=request.request_id,
        session_id=session_id,
        message="Input submitted successfully",
    )


@router.post(
    "/hitl/sessions/{session_id}/cancel",
    response_model=HITLSessionSchema,
    responses={
        404: {"model": HandoffErrorResponse},
    },
    summary="Cancel HITL Session",
    description="Cancel an active HITL session",
    tags=["Handoff", "HITL"],
)
async def cancel_hitl_session(
    session_id: UUID,
    reason: Optional[str] = Query(
        default=None,
        description="Cancellation reason",
    ),
) -> HITLSessionSchema:
    """
    Cancel an active HITL session.
    """
    if session_id not in _hitl_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"HITL session {session_id} not found",
        )

    session = _hitl_sessions[session_id]
    now = datetime.utcnow()

    session["status"] = "cancelled"
    session["completed_at"] = now
    session["updated_at"] = now
    if reason:
        session["cancel_reason"] = reason

    logger.info(f"HITL session cancelled: {session_id}")

    return HITLSessionSchema(
        session_id=session["session_id"],
        handoff_execution_id=session.get("handoff_execution_id"),
        status=HITLSessionStatusEnum.CANCELLED,
        created_at=session["created_at"],
        updated_at=session["updated_at"],
        completed_at=session["completed_at"],
        current_request=None,
        history_count=len(session.get("history", [])),
    )


@router.post(
    "/hitl/sessions/{session_id}/escalate",
    response_model=HITLSessionSchema,
    responses={
        404: {"model": HandoffErrorResponse},
    },
    summary="Escalate HITL Session",
    description="Escalate an active HITL session",
    tags=["Handoff", "HITL"],
)
async def escalate_hitl_session(
    session_id: UUID,
    reason: str = Query(
        ...,
        description="Escalation reason",
    ),
    target: Optional[str] = Query(
        default=None,
        description="Escalation target (e.g., supervisor)",
    ),
) -> HITLSessionSchema:
    """
    Escalate an active HITL session.

    Marks the session for human review/intervention.
    """
    if session_id not in _hitl_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"HITL session {session_id} not found",
        )

    session = _hitl_sessions[session_id]
    now = datetime.utcnow()

    session["status"] = "escalated"
    session["updated_at"] = now
    session["escalation_reason"] = reason
    session["escalation_target"] = target

    logger.warning(
        f"HITL session escalated: {session_id}, reason={reason}"
    )

    return HITLSessionSchema(
        session_id=session["session_id"],
        handoff_execution_id=session.get("handoff_execution_id"),
        status=HITLSessionStatusEnum.ESCALATED,
        created_at=session["created_at"],
        updated_at=session["updated_at"],
        completed_at=session.get("completed_at"),
        current_request=None,
        history_count=len(session.get("history", [])),
    )
