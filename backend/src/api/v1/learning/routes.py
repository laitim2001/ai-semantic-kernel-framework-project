# =============================================================================
# IPA Platform - Learning API Routes
# =============================================================================
# Sprint 4: Developer Experience - Few-shot Learning Mechanism
#
# REST API endpoints for learning case management:
#   - POST /learning/corrections - Record a correction
#   - GET /learning/cases - List cases
#   - GET /learning/cases/{id} - Get case details
#   - DELETE /learning/cases/{id} - Delete a case
#   - POST /learning/cases/{id}/approve - Approve case
#   - POST /learning/cases/{id}/reject - Reject case
#   - POST /learning/cases/bulk-approve - Bulk approve
#   - POST /learning/similar - Find similar cases
#   - POST /learning/prompt - Build few-shot prompt
#   - POST /learning/cases/{id}/effectiveness - Record effectiveness
#   - GET /learning/statistics - Get statistics
#   - GET /learning/scenarios/{name}/statistics - Scenario statistics
#   - GET /learning/health - Health check
#
# Author: IPA Platform Team
# Created: 2025-11-30
# =============================================================================

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from src.api.v1.learning.schemas import (
    ApproveRequest,
    BuildPromptRequest,
    BuildPromptResponse,
    BulkApproveRequest,
    BulkApproveResponse,
    CaseListResponse,
    CaseResponse,
    HealthCheckResponse,
    LearningStatisticsResponse,
    RecordCorrectionRequest,
    RecordEffectivenessRequest,
    RejectRequest,
    ScenarioStatisticsResponse,
    SimilarCaseItem,
    SimilarCasesRequest,
    SimilarCasesResponse,
)
from src.domain.learning import (
    CaseStatus,
    LearningCase,
    LearningService,
)


router = APIRouter(prefix="/learning", tags=["learning"])


# =============================================================================
# Service Instance Management
# =============================================================================

_learning_service: Optional[LearningService] = None


def get_learning_service() -> LearningService:
    """Get or create learning service instance."""
    global _learning_service
    if _learning_service is None:
        _learning_service = LearningService()
    return _learning_service


def set_learning_service(service: LearningService) -> None:
    """Set learning service instance (for testing)."""
    global _learning_service
    _learning_service = service


# =============================================================================
# Helper Functions
# =============================================================================


def _to_case_response(case: LearningCase) -> CaseResponse:
    """Convert case to response."""
    return CaseResponse(
        id=case.id,
        execution_id=case.execution_id,
        scenario=case.scenario,
        original_input=case.original_input,
        original_output=case.original_output,
        corrected_output=case.corrected_output,
        feedback=case.feedback,
        status=case.status.value,
        created_at=case.created_at,
        approved_at=case.approved_at,
        approved_by=case.approved_by,
        rejection_reason=case.rejection_reason,
        usage_count=case.usage_count,
        effectiveness_score=case.effectiveness_score,
        tags=case.tags,
        metadata=case.metadata,
    )


# =============================================================================
# Static Routes (before dynamic routes)
# =============================================================================


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Check learning service health."""
    service = get_learning_service()
    stats = service.get_statistics()

    return HealthCheckResponse(
        service="learning",
        status="healthy",
        total_cases=stats.total_cases,
        approved_cases=stats.approved_cases,
    )


@router.get("/statistics", response_model=LearningStatisticsResponse)
async def get_statistics():
    """Get learning service statistics."""
    service = get_learning_service()
    stats = service.get_statistics()

    return LearningStatisticsResponse(
        total_cases=stats.total_cases,
        approved_cases=stats.approved_cases,
        pending_cases=stats.pending_cases,
        rejected_cases=stats.rejected_cases,
        total_usage=stats.total_usage,
        by_scenario=stats.by_scenario,
        avg_effectiveness=stats.avg_effectiveness,
    )


# =============================================================================
# Case Management
# =============================================================================


@router.post("/corrections", response_model=CaseResponse)
async def record_correction(request: RecordCorrectionRequest):
    """
    Record a human correction.

    Creates a learning case from a human correction to an AI output.
    The case starts in 'pending' status and needs approval before use.
    """
    service = get_learning_service()

    case = service.record_correction(
        scenario=request.scenario,
        original_input=request.original_input,
        original_output=request.original_output,
        corrected_output=request.corrected_output,
        feedback=request.feedback,
        execution_id=request.execution_id,
        tags=request.tags,
        metadata=request.metadata,
    )

    return _to_case_response(case)


@router.get("/cases", response_model=CaseListResponse)
async def list_cases(
    scenario: Optional[str] = Query(None, description="Filter by scenario"),
    status: Optional[str] = Query(None, description="Filter by status"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
):
    """List learning cases with optional filtering."""
    service = get_learning_service()

    # Parse status
    case_status = None
    if status:
        try:
            case_status = CaseStatus(status.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    # Parse tags
    tag_list = None
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]

    cases = service.list_cases(
        scenario=scenario,
        status=case_status,
        tags=tag_list,
        limit=limit,
    )

    return CaseListResponse(
        cases=[_to_case_response(c) for c in cases],
        total=len(cases),
    )


@router.get("/cases/{case_id}", response_model=CaseResponse)
async def get_case(case_id: UUID):
    """Get case details by ID."""
    service = get_learning_service()

    case = service.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")

    return _to_case_response(case)


@router.delete("/cases/{case_id}")
async def delete_case(case_id: UUID):
    """Delete a learning case."""
    service = get_learning_service()

    if service.delete_case(case_id):
        return {"message": "Case deleted", "case_id": str(case_id)}
    else:
        raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")


# =============================================================================
# Approval Workflow
# =============================================================================


@router.post("/cases/{case_id}/approve", response_model=CaseResponse)
async def approve_case(case_id: UUID, request: ApproveRequest):
    """Approve a learning case for use."""
    service = get_learning_service()

    case = service.approve_case(case_id, request.approved_by)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")

    return _to_case_response(case)


@router.post("/cases/{case_id}/reject", response_model=CaseResponse)
async def reject_case(case_id: UUID, request: RejectRequest):
    """Reject a learning case."""
    service = get_learning_service()

    case = service.reject_case(case_id, request.reason)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")

    return _to_case_response(case)


@router.post("/cases/bulk-approve", response_model=BulkApproveResponse)
async def bulk_approve_cases(request: BulkApproveRequest):
    """Approve multiple cases at once."""
    service = get_learning_service()

    approved = service.bulk_approve(request.case_ids, request.approved_by)

    return BulkApproveResponse(
        approved_count=approved,
        total_requested=len(request.case_ids),
    )


# =============================================================================
# Similarity Search and Few-shot
# =============================================================================


@router.post("/similar", response_model=SimilarCasesResponse)
async def find_similar_cases(request: SimilarCasesRequest):
    """
    Find similar learning cases.

    Searches for cases with similar input text for few-shot learning.
    """
    service = get_learning_service()

    similar = service.get_similar_cases(
        scenario=request.scenario,
        input_text=request.input_text,
        limit=request.limit,
        approved_only=request.approved_only,
    )

    return SimilarCasesResponse(
        results=[
            SimilarCaseItem(
                case=_to_case_response(s["case"]),
                similarity=s["similarity"],
            )
            for s in similar
        ],
        query_input=request.input_text[:100],  # Truncate for response
        total=len(similar),
    )


@router.post("/prompt", response_model=BuildPromptResponse)
async def build_few_shot_prompt(request: BuildPromptRequest):
    """
    Build a few-shot prompt with similar examples.

    Enhances the base prompt with relevant examples from learning cases.
    """
    service = get_learning_service()

    enhanced_prompt = service.build_few_shot_prompt(
        base_prompt=request.base_prompt,
        scenario=request.scenario,
        input_text=request.input_text,
        example_format=request.example_format,
    )

    # Count examples used
    similar = service.get_similar_cases(
        scenario=request.scenario,
        input_text=request.input_text,
    )

    return BuildPromptResponse(
        enhanced_prompt=enhanced_prompt,
        examples_used=len(similar),
        scenario=request.scenario,
    )


# =============================================================================
# Effectiveness Tracking
# =============================================================================


@router.post("/cases/{case_id}/effectiveness", response_model=CaseResponse)
async def record_effectiveness(case_id: UUID, request: RecordEffectivenessRequest):
    """Record whether a case was helpful."""
    service = get_learning_service()

    case = service.record_effectiveness(
        case_id=case_id,
        was_helpful=request.was_helpful,
        score=request.score,
    )

    if not case:
        raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")

    return _to_case_response(case)


# =============================================================================
# Scenario Statistics
# =============================================================================


@router.get("/scenarios/{scenario_name}/statistics", response_model=ScenarioStatisticsResponse)
async def get_scenario_statistics(scenario_name: str):
    """Get statistics for a specific scenario."""
    service = get_learning_service()
    stats = service.get_scenario_statistics(scenario_name)

    return ScenarioStatisticsResponse(
        scenario=stats["scenario"],
        total_cases=stats["total_cases"],
        approved_cases=stats["approved_cases"],
        total_usage=stats["total_usage"],
        avg_effectiveness=stats["avg_effectiveness"],
    )
