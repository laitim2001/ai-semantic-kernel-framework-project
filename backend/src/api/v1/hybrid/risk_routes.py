# =============================================================================
# IPA Platform - Risk Assessment API Routes
# =============================================================================
# Sprint 55: S55-4 - API & ApprovalHook Integration
#
# REST API endpoints for risk assessment:
#   - POST /hybrid/risk/assess - Assess operation risk
#   - POST /hybrid/risk/assess-batch - Assess multiple operations
#   - GET /hybrid/risk/session/{session_id} - Get session risk
#   - GET /hybrid/risk/metrics - Get engine metrics
#   - DELETE /hybrid/risk/session/{session_id}/history - Clear session history
#
# Dependencies:
#   - RiskAssessmentEngine (src.integrations.hybrid.risk.engine)
#   - OperationAnalyzer (src.integrations.hybrid.risk.analyzers.operation_analyzer)
#   - ContextEvaluator (src.integrations.hybrid.risk.analyzers.context_evaluator)
#   - PatternDetector (src.integrations.hybrid.risk.analyzers.pattern_detector)
# =============================================================================

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status

from src.integrations.hybrid.risk.engine import (
    RiskAssessmentEngine,
    create_engine,
)
from src.integrations.hybrid.risk.models import (
    OperationContext,
    RiskConfig,
)
from src.integrations.hybrid.risk.analyzers.operation_analyzer import OperationAnalyzer
from src.integrations.hybrid.risk.analyzers.context_evaluator import (
    ContextEvaluator,
    UserProfile,
)
from src.integrations.hybrid.risk.analyzers.pattern_detector import PatternDetector

from .risk_schemas import (
    RiskAssessRequest,
    RiskAssessResponse,
    RiskAssessBatchRequest,
    RiskAssessBatchResponse,
    SessionRiskResponse,
    EngineMetricsResponse,
    RiskFactorResponse,
    RiskConfigUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/hybrid/risk",
    tags=["hybrid-risk"],
    responses={
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"},
    },
)


# =============================================================================
# Singleton Instances
# =============================================================================

_engine: Optional[RiskAssessmentEngine] = None
_operation_analyzer: Optional[OperationAnalyzer] = None
_context_evaluator: Optional[ContextEvaluator] = None
_pattern_detector: Optional[PatternDetector] = None


def get_engine() -> RiskAssessmentEngine:
    """Get or create RiskAssessmentEngine singleton with analyzers."""
    global _engine, _operation_analyzer, _context_evaluator, _pattern_detector

    if _engine is None:
        _engine = create_engine()

        # Create and register analyzers
        _operation_analyzer = OperationAnalyzer()
        _context_evaluator = ContextEvaluator()
        _pattern_detector = PatternDetector()

        _engine.register_analyzer(_operation_analyzer)
        _engine.register_analyzer(_context_evaluator)
        _engine.register_analyzer(_pattern_detector)

        logger.info("RiskAssessmentEngine initialized with 3 analyzers")

    return _engine


def get_operation_analyzer() -> OperationAnalyzer:
    """Get OperationAnalyzer instance."""
    get_engine()  # Ensure engine is initialized
    return _operation_analyzer


def get_context_evaluator() -> ContextEvaluator:
    """Get ContextEvaluator instance."""
    get_engine()  # Ensure engine is initialized
    return _context_evaluator


def get_pattern_detector() -> PatternDetector:
    """Get PatternDetector instance."""
    get_engine()  # Ensure engine is initialized
    return _pattern_detector


# =============================================================================
# Helper Functions
# =============================================================================


def _request_to_context(request: RiskAssessRequest) -> OperationContext:
    """Convert API request to OperationContext."""
    return OperationContext(
        tool_name=request.tool_name,
        operation_type=request.operation_type or "unknown",
        target_paths=request.target_paths or [],
        command=request.command,
        arguments=request.arguments or {},
        session_id=request.session_id,
        user_id=request.user_id,
        environment=request.environment or "development",
    )


def _assessment_to_response(assessment) -> RiskAssessResponse:
    """Convert RiskAssessment to API response."""
    return RiskAssessResponse(
        overall_level=assessment.overall_level.value,
        overall_score=assessment.overall_score,
        requires_approval=assessment.requires_approval,
        approval_reason=assessment.approval_reason,
        factors=[
            RiskFactorResponse(
                factor_type=f.factor_type.value,
                score=f.score,
                weight=f.weight,
                weighted_score=f.weighted_score(),
                description=f.description,
                source=f.source,
                metadata=f.metadata,
            )
            for f in assessment.factors
        ],
        assessment_time=assessment.assessment_time.isoformat(),
        session_id=assessment.session_id,
        metadata=assessment.metadata,
    )


# =============================================================================
# API Routes
# =============================================================================


@router.post(
    "/assess",
    response_model=RiskAssessResponse,
    summary="Assess operation risk",
    description="Perform multi-dimensional risk assessment for a single operation.",
)
async def assess_risk(request: RiskAssessRequest) -> RiskAssessResponse:
    """
    Assess risk for a single operation.

    Analyzes the operation using multiple analyzers:
    - OperationAnalyzer: Tool base risk, path sensitivity, command danger
    - ContextEvaluator: User trust level, environment risk
    - PatternDetector: Frequency anomalies, behavior patterns

    Args:
        request: Operation details to assess

    Returns:
        RiskAssessResponse: Complete risk assessment with level, score, factors

    Example:
        POST /api/v1/hybrid/risk/assess
        {
            "tool_name": "Bash",
            "command": "rm -rf /tmp/test",
            "session_id": "sess_123"
        }
    """
    try:
        engine = get_engine()
        context = _request_to_context(request)

        # Note: User profile is automatically created/managed by ContextEvaluator
        # when engine.assess() runs. Trust levels are tracked internally.

        assessment = engine.assess(context)

        logger.info(
            f"Risk assessment: {assessment.overall_level.value} "
            f"(score={assessment.overall_score:.3f}) for {request.tool_name}"
        )

        return _assessment_to_response(assessment)

    except Exception as e:
        logger.error(f"Risk assessment failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Risk assessment failed: {str(e)}"
        )


@router.post(
    "/assess-batch",
    response_model=RiskAssessBatchResponse,
    summary="Assess multiple operations",
    description="Perform risk assessment for a batch of operations.",
)
async def assess_risk_batch(
    request: RiskAssessBatchRequest
) -> RiskAssessBatchResponse:
    """
    Assess risk for multiple operations as a batch.

    Useful for evaluating multi-step workflows before execution.
    Cumulative risk increases for later operations.

    Args:
        request: List of operations to assess

    Returns:
        RiskAssessBatchResponse: Assessments for all operations
    """
    try:
        engine = get_engine()
        contexts = [_request_to_context(op) for op in request.operations]

        assessments = engine.assess_batch(contexts)

        # Calculate aggregate statistics
        scores = [a.overall_score for a in assessments]
        levels = [a.overall_level.value for a in assessments]
        approvals_required = sum(1 for a in assessments if a.requires_approval)

        return RiskAssessBatchResponse(
            assessments=[_assessment_to_response(a) for a in assessments],
            total_operations=len(assessments),
            max_risk_level=max(levels) if levels else "low",
            max_risk_score=max(scores) if scores else 0.0,
            average_risk_score=sum(scores) / len(scores) if scores else 0.0,
            approvals_required=approvals_required,
        )

    except Exception as e:
        logger.error(f"Batch risk assessment failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch risk assessment failed: {str(e)}"
        )


@router.get(
    "/session/{session_id}",
    response_model=SessionRiskResponse,
    summary="Get session risk",
    description="Get aggregated risk for a session within a time window.",
)
async def get_session_risk(
    session_id: str,
    window_seconds: int = 300,
) -> SessionRiskResponse:
    """
    Get aggregated risk profile for a session.

    Analyzes recent operations within the time window to provide
    an overall session risk score.

    Args:
        session_id: Session identifier
        window_seconds: Time window in seconds (default: 300 = 5 minutes)

    Returns:
        SessionRiskResponse: Aggregated session risk information
    """
    try:
        engine = get_engine()
        result = engine.get_session_risk(session_id, window_seconds)

        # Get pattern detector for behavior insights
        detector = get_pattern_detector()
        session_state = detector.get_session_state(session_id)

        return SessionRiskResponse(
            session_id=session_id,
            window_seconds=window_seconds,
            overall_score=result.score,
            overall_level=result.level.value,
            operations_in_window=session_state.get("operation_count", 0)
            if session_state else 0,
            strategy_used=result.strategy_used.value,
        )

    except Exception as e:
        logger.error(f"Session risk query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session risk query failed: {str(e)}"
        )


@router.get(
    "/metrics",
    response_model=EngineMetricsResponse,
    summary="Get engine metrics",
    description="Get performance metrics for the risk assessment engine.",
)
async def get_metrics() -> EngineMetricsResponse:
    """
    Get engine performance metrics.

    Returns statistics about assessments performed, risk levels,
    approval rates, and latency.

    Returns:
        EngineMetricsResponse: Engine performance statistics
    """
    engine = get_engine()
    metrics = engine.get_metrics()

    return EngineMetricsResponse(
        total_assessments=metrics.total_assessments,
        assessments_by_level=metrics.assessments_by_level,
        average_score=metrics.average_score,
        approval_rate=metrics.approval_rate,
        average_latency_ms=metrics.average_latency_ms,
    )


@router.delete(
    "/session/{session_id}/history",
    summary="Clear session history",
    description="Clear assessment history for a session.",
)
async def clear_session_history(session_id: str) -> dict:
    """
    Clear assessment history for a session.

    Removes all recorded assessments for the session.
    Useful when session is completed or for privacy.

    Args:
        session_id: Session identifier

    Returns:
        dict: Number of entries cleared
    """
    engine = get_engine()
    detector = get_pattern_detector()

    # Clear engine history
    engine_cleared = engine.clear_session_history(session_id)

    # Clear pattern detector session
    detector.clear_session(session_id)

    logger.info(f"Cleared history for session {session_id}: {engine_cleared} entries")

    return {
        "session_id": session_id,
        "entries_cleared": engine_cleared,
        "success": True,
    }


@router.post(
    "/metrics/reset",
    summary="Reset engine metrics",
    description="Reset all engine performance metrics.",
)
async def reset_metrics() -> dict:
    """
    Reset all engine metrics.

    Clears accumulated statistics. Use with caution.

    Returns:
        dict: Confirmation of reset
    """
    engine = get_engine()
    engine.reset_metrics()

    logger.info("Engine metrics reset")

    return {"success": True, "message": "Metrics reset successfully"}


@router.get(
    "/config",
    summary="Get current configuration",
    description="Get current risk assessment configuration.",
)
async def get_config() -> dict:
    """
    Get current risk configuration.

    Returns:
        dict: Current configuration values
    """
    engine = get_engine()
    config = engine.config

    return {
        "critical_threshold": config.critical_threshold,
        "high_threshold": config.high_threshold,
        "medium_threshold": config.medium_threshold,
        "operation_weight": config.operation_weight,
        "context_weight": config.context_weight,
        "pattern_weight": config.pattern_weight,
        "auto_approve_low": config.auto_approve_low,
        "auto_approve_medium": config.auto_approve_medium,
        "max_auto_approve_score": config.max_auto_approve_score,
        "enable_pattern_detection": config.enable_pattern_detection,
        "pattern_window_seconds": config.pattern_window_seconds,
    }
