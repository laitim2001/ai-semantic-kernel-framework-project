# =============================================================================
# IPA Platform - Autonomous Planning API Routes
# =============================================================================
# Sprint 79: S79-1 - Claude 自主規劃引擎 (13 pts)
#
# API endpoints for the autonomous planning engine.
#
# Endpoints:
#   POST   /api/v1/claude/autonomous/plan          - Generate plan
#   GET    /api/v1/claude/autonomous/{plan_id}     - Get plan details
#   POST   /api/v1/claude/autonomous/{plan_id}/execute - Execute plan
#   DELETE /api/v1/claude/autonomous/{plan_id}     - Delete plan
#   GET    /api/v1/claude/autonomous               - List plans
#   POST   /api/v1/claude/autonomous/estimate      - Estimate resources
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json

from src.integrations.claude_sdk.client import ClaudeSDKClient
from src.integrations.claude_sdk.autonomous import (
    AutonomousPlanner,
    EventAnalyzer,
    EventContext,
    EventSeverity,
    PlanExecutor,
    PlanStatus,
    ResultVerifier,
)


router = APIRouter(tags=["Claude Autonomous Planning"])


# --- Request/Response Schemas ---


class EventContextSchema(BaseModel):
    """Schema for event context input."""

    event_id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Type of event (e.g., 'incident', 'alert')")
    description: str = Field(..., description="Event description")
    severity: str = Field(
        "medium", description="Severity level: low, medium, high, critical"
    )
    source_system: Optional[str] = Field(None, description="Source system name")
    affected_services: List[str] = Field(
        default_factory=list, description="List of affected services"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class GeneratePlanRequest(BaseModel):
    """Request schema for plan generation."""

    event: EventContextSchema
    budget_tokens: Optional[int] = Field(
        None, ge=4096, le=128000, description="Budget tokens for Extended Thinking"
    )


class PlanStepSchema(BaseModel):
    """Schema for a plan step."""

    step_number: int
    action: str
    description: str
    tool_or_workflow: str
    parameters: Dict[str, Any]
    expected_outcome: str
    fallback_action: Optional[str]
    estimated_duration_seconds: int
    requires_approval: bool
    status: str


class AnalysisResultSchema(BaseModel):
    """Schema for analysis result."""

    complexity: str
    root_cause_hypothesis: str
    affected_components: List[str]
    recommended_actions: List[str]
    confidence_score: float


class PlanResponse(BaseModel):
    """Response schema for plan details."""

    id: str
    event_id: str
    complexity: str
    risk_level: str
    status: str
    analysis: Optional[AnalysisResultSchema] = None
    steps: List[PlanStepSchema] = []
    estimated_duration_seconds: int
    created_at: datetime
    updated_at: datetime
    error: Optional[str] = None


class ExecutePlanRequest(BaseModel):
    """Request schema for plan execution."""

    confirm: bool = Field(..., description="Confirmation to execute")
    options: Dict[str, Any] = Field(
        default_factory=dict, description="Execution options"
    )


class EstimateRequest(BaseModel):
    """Request schema for resource estimation."""

    event: EventContextSchema


class EstimateResponse(BaseModel):
    """Response schema for resource estimation."""

    complexity: str
    budget_tokens: int
    estimated_duration_seconds: int
    suggested_tools: List[str]


class PlanListResponse(BaseModel):
    """Response schema for plan list."""

    plans: List[PlanResponse]
    total: int


# --- Planner Instance ---

_planner: Optional[AutonomousPlanner] = None
_executor: Optional[PlanExecutor] = None
_verifier: Optional[ResultVerifier] = None


def get_planner() -> AutonomousPlanner:
    """Get or create the autonomous planner."""
    global _planner
    if _planner is None:
        from anthropic import AsyncAnthropic
        import os

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="ANTHROPIC_API_KEY not configured",
            )
        client = AsyncAnthropic(api_key=api_key)
        _planner = AutonomousPlanner(client)
    return _planner


def get_executor() -> PlanExecutor:
    """Get or create the plan executor."""
    global _executor
    if _executor is None:
        _executor = PlanExecutor()
        # Register default tool executors (placeholder)
        _executor.register_tool("manual", lambda n, p: "Manual step acknowledged")
    return _executor


def get_verifier() -> ResultVerifier:
    """Get or create the result verifier."""
    global _verifier
    if _verifier is None:
        from anthropic import AsyncAnthropic
        import os

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="ANTHROPIC_API_KEY not configured",
            )
        client = AsyncAnthropic(api_key=api_key)
        _verifier = ResultVerifier(client)
    return _verifier


def _event_schema_to_context(event: EventContextSchema) -> EventContext:
    """Convert schema to EventContext."""
    return EventContext(
        event_id=event.event_id,
        event_type=event.event_type,
        description=event.description,
        severity=EventSeverity(event.severity.lower()),
        source_system=event.source_system,
        affected_services=event.affected_services,
        metadata=event.metadata,
        timestamp=datetime.utcnow(),
    )


def _plan_to_response(plan) -> PlanResponse:
    """Convert AutonomousPlan to response schema."""
    analysis = None
    if plan.analysis:
        analysis = AnalysisResultSchema(
            complexity=plan.analysis.complexity.value,
            root_cause_hypothesis=plan.analysis.root_cause_hypothesis,
            affected_components=plan.analysis.affected_components,
            recommended_actions=plan.analysis.recommended_actions,
            confidence_score=plan.analysis.confidence_score,
        )

    steps = [
        PlanStepSchema(
            step_number=s.step_number,
            action=s.action,
            description=s.description,
            tool_or_workflow=s.tool_or_workflow,
            parameters=s.parameters,
            expected_outcome=s.expected_outcome,
            fallback_action=s.fallback_action,
            estimated_duration_seconds=s.estimated_duration_seconds,
            requires_approval=s.requires_approval,
            status=s.status.value,
        )
        for s in plan.steps
    ]

    return PlanResponse(
        id=plan.id,
        event_id=plan.event_id,
        complexity=plan.complexity.value,
        risk_level=plan.risk_level.value,
        status=plan.status.value,
        analysis=analysis,
        steps=steps,
        estimated_duration_seconds=plan.estimated_duration_seconds,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        error=plan.error,
    )


# --- Endpoints ---


@router.post("/plan", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def generate_plan(
    request: GeneratePlanRequest,
    planner: AutonomousPlanner = Depends(get_planner),
):
    """
    Generate an autonomous execution plan for an IT event.

    Uses Claude's Extended Thinking capability to analyze the event
    and generate a structured, executable plan.

    Returns the plan with steps, risk assessment, and estimated duration.
    """
    try:
        event_context = _event_schema_to_context(request.event)
        plan = await planner.generate_plan(
            event_context=event_context,
            budget_tokens=request.budget_tokens,
        )
        return _plan_to_response(plan)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Plan generation failed: {str(e)}",
        )


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: str,
    planner: AutonomousPlanner = Depends(get_planner),
):
    """
    Get details of a specific plan.
    """
    plan = planner.get_plan(plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )
    return _plan_to_response(plan)


@router.post("/{plan_id}/execute")
async def execute_plan(
    plan_id: str,
    request: ExecutePlanRequest,
    planner: AutonomousPlanner = Depends(get_planner),
    executor: PlanExecutor = Depends(get_executor),
):
    """
    Execute a plan with streaming progress events.

    Returns Server-Sent Events (SSE) stream with execution progress.
    """
    if not request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Execution not confirmed. Set confirm=true to proceed.",
        )

    plan = planner.get_plan(plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    if plan.status not in [PlanStatus.PLANNED, PlanStatus.PENDING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plan cannot be executed in status: {plan.status.value}",
        )

    async def event_stream():
        """Generate SSE events from execution."""
        async for event in executor.execute_stream(plan):
            yield f"data: {json.dumps(event.to_dict())}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: str,
    planner: AutonomousPlanner = Depends(get_planner),
):
    """
    Delete a plan.
    """
    if not planner.delete_plan(plan_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )


@router.get("/", response_model=PlanListResponse)
async def list_plans(
    event_id: Optional[str] = None,
    status: Optional[str] = None,
    planner: AutonomousPlanner = Depends(get_planner),
):
    """
    List all plans with optional filtering.
    """
    status_filter = None
    if status:
        try:
            status_filter = PlanStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}",
            )

    plans = planner.list_plans(event_id=event_id, status=status_filter)

    return PlanListResponse(
        plans=[_plan_to_response(p) for p in plans],
        total=len(plans),
    )


@router.post("/estimate", response_model=EstimateResponse)
async def estimate_resources(
    request: EstimateRequest,
    planner: AutonomousPlanner = Depends(get_planner),
):
    """
    Estimate resources needed for handling an event.

    Returns complexity assessment, recommended budget_tokens,
    estimated duration, and suggested tools.
    """
    event_context = _event_schema_to_context(request.event)
    estimate = await planner.estimate_resources(event_context)

    return EstimateResponse(
        complexity=estimate["complexity"],
        budget_tokens=estimate["budget_tokens"],
        estimated_duration_seconds=estimate["estimated_duration_seconds"],
        suggested_tools=estimate["suggested_tools"],
    )


@router.post("/{plan_id}/verify", response_model=Dict[str, Any])
async def verify_plan(
    plan_id: str,
    planner: AutonomousPlanner = Depends(get_planner),
    verifier: ResultVerifier = Depends(get_verifier),
):
    """
    Verify the execution results of a completed plan.

    Returns verification result with quality score and lessons learned.
    """
    plan = planner.get_plan(plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    if plan.status not in [PlanStatus.COMPLETED, PlanStatus.VERIFYING, PlanStatus.FAILED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plan must be completed or failed to verify. Current status: {plan.status.value}",
        )

    result = await verifier.verify(plan)
    return result.to_dict()
