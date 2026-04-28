# =============================================================================
# IPA Platform - Decision Audit API Routes
# =============================================================================
# Sprint 80: S80-2 - 自主決策審計追蹤 (8 pts)
#
# REST API endpoints for Decision Audit management:
#   - GET /decisions - 查詢決策記錄
#   - GET /decisions/{id} - 獲取決策詳情
#   - GET /decisions/{id}/report - 獲取可解釋性報告
#   - POST /decisions/{id}/feedback - 添加反饋
#   - GET /decisions/statistics - 決策統計信息
#   - GET /decisions/summary - 決策摘要報告
# =============================================================================

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.integrations.audit import (
    AuditConfig,
    AuditQuery,
    AuditReportGenerator,
    DecisionOutcome,
    DecisionTracker,
    DecisionType,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Schemas
# =============================================================================


class ThinkingProcessResponse(BaseModel):
    """Thinking process response schema."""

    raw_thinking: str = ""
    key_considerations: List[str] = Field(default_factory=list)
    assumptions_made: List[str] = Field(default_factory=list)
    risks_identified: List[str] = Field(default_factory=list)
    budget_tokens_used: Optional[int] = None


class AlternativeResponse(BaseModel):
    """Alternative considered response schema."""

    description: str
    reason_not_selected: str
    estimated_risk: float
    estimated_success_probability: float


class DecisionContextResponse(BaseModel):
    """Decision context response schema."""

    event_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    plan_id: Optional[str] = None
    step_number: Optional[int] = None
    input_data: Dict[str, Any] = Field(default_factory=dict)
    system_state: Dict[str, Any] = Field(default_factory=dict)


class DecisionAuditResponse(BaseModel):
    """Decision audit response schema."""

    decision_id: str
    decision_type: str
    timestamp: datetime
    context: DecisionContextResponse
    thinking_process: ThinkingProcessResponse
    selected_action: str
    action_details: Dict[str, Any]
    alternatives_considered: List[AlternativeResponse]
    confidence_score: float
    outcome: str
    outcome_details: Optional[str] = None
    quality_score: Optional[float] = None
    quality_rating: Optional[str] = None
    feedback: Optional[str] = None
    updated_at: Optional[datetime] = None


class DecisionListResponse(BaseModel):
    """Decision list response schema."""

    items: List[DecisionAuditResponse]
    total: int
    offset: int
    limit: int


class AuditReportResponse(BaseModel):
    """Audit report response schema."""

    decision_id: str
    title: str
    summary: str
    detailed_explanation: str
    key_factors: List[str]
    risk_analysis: str
    recommendations: List[str]
    generated_at: datetime


class FeedbackRequest(BaseModel):
    """Feedback request schema."""

    feedback: str = Field(..., min_length=1, description="反饋內容")
    quality_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="品質評分 (0.0-1.0)"
    )


class StatisticsResponse(BaseModel):
    """Statistics response schema."""

    total_decisions: int
    by_type: Dict[str, int]
    by_outcome: Dict[str, int]
    avg_confidence: float
    avg_quality: float
    success_rate: float


class SummaryReportResponse(BaseModel):
    """Summary report response schema."""

    total_decisions: int
    period: Optional[Dict[str, str]] = None
    statistics: Dict[str, Any]
    by_type: Dict[str, int]
    summary: str


# =============================================================================
# Router Setup
# =============================================================================

router = APIRouter(
    prefix="/decisions",
    tags=["decision-audit"],
    responses={
        500: {"description": "Internal server error"},
    },
)


# =============================================================================
# Dependency Injection
# =============================================================================

# Global tracker instance (in production, use proper DI)
_decision_tracker: Optional[DecisionTracker] = None
_report_generator: Optional[AuditReportGenerator] = None


async def get_decision_tracker() -> DecisionTracker:
    """Get or create decision tracker."""
    global _decision_tracker

    if _decision_tracker is None:
        _decision_tracker = DecisionTracker()
        await _decision_tracker.initialize()

    return _decision_tracker


def get_report_generator() -> AuditReportGenerator:
    """Get or create report generator."""
    global _report_generator

    if _report_generator is None:
        _report_generator = AuditReportGenerator()

    return _report_generator


# =============================================================================
# Helper Functions
# =============================================================================


def _audit_to_response(audit) -> DecisionAuditResponse:
    """Convert DecisionAudit to response schema."""
    return DecisionAuditResponse(
        decision_id=audit.decision_id,
        decision_type=audit.decision_type.value,
        timestamp=audit.timestamp,
        context=DecisionContextResponse(
            event_id=audit.context.event_id,
            session_id=audit.context.session_id,
            user_id=audit.context.user_id,
            plan_id=audit.context.plan_id,
            step_number=audit.context.step_number,
            input_data=audit.context.input_data,
            system_state=audit.context.system_state,
        ),
        thinking_process=ThinkingProcessResponse(
            raw_thinking=audit.thinking_process.raw_thinking,
            key_considerations=audit.thinking_process.key_considerations,
            assumptions_made=audit.thinking_process.assumptions_made,
            risks_identified=audit.thinking_process.risks_identified,
            budget_tokens_used=audit.thinking_process.budget_tokens_used,
        ),
        selected_action=audit.selected_action,
        action_details=audit.action_details,
        alternatives_considered=[
            AlternativeResponse(
                description=alt.description,
                reason_not_selected=alt.reason_not_selected,
                estimated_risk=alt.estimated_risk,
                estimated_success_probability=alt.estimated_success_probability,
            )
            for alt in audit.alternatives_considered
        ],
        confidence_score=audit.confidence_score,
        outcome=audit.outcome.value,
        outcome_details=audit.outcome_details,
        quality_score=audit.quality_score,
        quality_rating=audit.quality_rating.value if audit.quality_rating else None,
        feedback=audit.feedback,
        updated_at=audit.updated_at,
    )


# =============================================================================
# Query Endpoints
# =============================================================================


@router.get(
    "",
    response_model=DecisionListResponse,
    summary="查詢決策記錄",
    description="獲取決策記錄列表，支持多條件過濾",
)
async def list_decisions(
    user_id: Optional[str] = Query(None, description="用戶 ID 過濾"),
    session_id: Optional[str] = Query(None, description="Session ID 過濾"),
    event_id: Optional[str] = Query(None, description="事件 ID 過濾"),
    plan_id: Optional[str] = Query(None, description="計劃 ID 過濾"),
    decision_type: Optional[str] = Query(None, description="決策類型過濾"),
    outcome: Optional[str] = Query(None, description="結果過濾"),
    min_confidence: Optional[float] = Query(
        None, ge=0.0, le=1.0, description="最低信心度"
    ),
    max_confidence: Optional[float] = Query(
        None, ge=0.0, le=1.0, description="最高信心度"
    ),
    start_time: Optional[datetime] = Query(None, description="開始時間"),
    end_time: Optional[datetime] = Query(None, description="結束時間"),
    limit: int = Query(50, ge=1, le=500, description="返回數量"),
    offset: int = Query(0, ge=0, description="跳過數量"),
    tracker: DecisionTracker = Depends(get_decision_tracker),
) -> DecisionListResponse:
    """查詢決策記錄."""
    # Parse decision type
    parsed_decision_type = None
    if decision_type:
        try:
            parsed_decision_type = DecisionType(decision_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid decision_type: {decision_type}",
            )

    # Parse outcome
    parsed_outcome = None
    if outcome:
        try:
            parsed_outcome = DecisionOutcome(outcome)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid outcome: {outcome}",
            )

    query = AuditQuery(
        user_id=user_id,
        session_id=session_id,
        event_id=event_id,
        plan_id=plan_id,
        decision_type=parsed_decision_type,
        outcome=parsed_outcome,
        min_confidence=min_confidence,
        max_confidence=max_confidence,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )

    decisions = await tracker.query_decisions(query)
    total = len(tracker._decisions)  # In production, use proper count query

    return DecisionListResponse(
        items=[_audit_to_response(d) for d in decisions],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{decision_id}",
    response_model=DecisionAuditResponse,
    summary="獲取決策詳情",
    description="獲取指定 ID 的決策詳細信息",
)
async def get_decision(
    decision_id: str,
    tracker: DecisionTracker = Depends(get_decision_tracker),
) -> DecisionAuditResponse:
    """獲取單個決策詳情."""
    decision = await tracker.get_decision(decision_id)

    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision not found: {decision_id}",
        )

    return _audit_to_response(decision)


@router.get(
    "/{decision_id}/report",
    response_model=AuditReportResponse,
    summary="獲取可解釋性報告",
    description="生成決策的可解釋性報告，說明決策原因和建議",
)
async def get_decision_report(
    decision_id: str,
    tracker: DecisionTracker = Depends(get_decision_tracker),
    generator: AuditReportGenerator = Depends(get_report_generator),
) -> AuditReportResponse:
    """獲取決策的可解釋性報告."""
    decision = await tracker.get_decision(decision_id)

    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision not found: {decision_id}",
        )

    report = generator.generate_report(decision)

    return AuditReportResponse(
        decision_id=report.decision_id,
        title=report.title,
        summary=report.summary,
        detailed_explanation=report.detailed_explanation,
        key_factors=report.key_factors,
        risk_analysis=report.risk_analysis,
        recommendations=report.recommendations,
        generated_at=report.generated_at,
    )


# =============================================================================
# Feedback Endpoint
# =============================================================================


@router.post(
    "/{decision_id}/feedback",
    response_model=DecisionAuditResponse,
    summary="添加決策反饋",
    description="為決策添加人工反饋和品質評分",
)
async def add_feedback(
    decision_id: str,
    request: FeedbackRequest,
    tracker: DecisionTracker = Depends(get_decision_tracker),
) -> DecisionAuditResponse:
    """添加決策反饋."""
    updated = await tracker.add_feedback(
        decision_id=decision_id,
        feedback=request.feedback,
        quality_score=request.quality_score,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision not found: {decision_id}",
        )

    return _audit_to_response(updated)


# =============================================================================
# Statistics Endpoints
# =============================================================================


@router.get(
    "/statistics",
    response_model=StatisticsResponse,
    summary="獲取決策統計",
    description="獲取決策的統計信息",
)
async def get_statistics(
    user_id: Optional[str] = Query(None, description="用戶 ID 過濾"),
    start_time: Optional[datetime] = Query(None, description="開始時間"),
    end_time: Optional[datetime] = Query(None, description="結束時間"),
    tracker: DecisionTracker = Depends(get_decision_tracker),
) -> StatisticsResponse:
    """獲取決策統計信息."""
    stats = await tracker.get_statistics(
        user_id=user_id,
        start_time=start_time,
        end_time=end_time,
    )

    return StatisticsResponse(
        total_decisions=stats["total_decisions"],
        by_type=stats["by_type"],
        by_outcome=stats["by_outcome"],
        avg_confidence=stats["avg_confidence"],
        avg_quality=stats["avg_quality"],
        success_rate=stats.get("success_rate", 0.0),
    )


@router.get(
    "/summary",
    response_model=SummaryReportResponse,
    summary="獲取摘要報告",
    description="生成決策的摘要報告",
)
async def get_summary_report(
    user_id: Optional[str] = Query(None, description="用戶 ID 過濾"),
    start_time: Optional[datetime] = Query(None, description="開始時間"),
    end_time: Optional[datetime] = Query(None, description="結束時間"),
    limit: int = Query(100, ge=1, le=1000, description="決策數量限制"),
    tracker: DecisionTracker = Depends(get_decision_tracker),
    generator: AuditReportGenerator = Depends(get_report_generator),
) -> SummaryReportResponse:
    """生成決策摘要報告."""
    query = AuditQuery(
        user_id=user_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )

    decisions = await tracker.query_decisions(query)
    summary = generator.generate_summary_report(decisions)

    return SummaryReportResponse(
        total_decisions=summary["total_decisions"],
        period=summary.get("period"),
        statistics=summary.get("statistics", {}),
        by_type=summary.get("by_type", {}),
        summary=summary["summary"],
    )


# =============================================================================
# Health Check
# =============================================================================


@router.get(
    "/health",
    summary="健康檢查",
    description="決策審計服務健康檢查",
)
async def health_check(
    tracker: DecisionTracker = Depends(get_decision_tracker),
) -> dict:
    """健康檢查."""
    return {
        "status": "healthy",
        "service": "decision-audit",
        "decision_count": len(tracker._decisions),
        "timestamp": datetime.utcnow().isoformat(),
    }
