"""
Orchestration API Routes

Main routes for orchestration module including policy management and metrics.

Sprint 96: Story 96-5 - API Route Implementation (Phase 28)
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status

from src.integrations.orchestration import (
    RiskAssessor,
    RiskPolicies,
)
from src.integrations.orchestration.risk_assessor.policies import (
    create_default_policies,
    create_strict_policies,
    create_relaxed_policies,
)

from . import schemas

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/orchestration",
    tags=["Orchestration"],
    responses={
        500: {"model": schemas.ErrorResponse, "description": "Internal Server Error"},
    },
)


# =============================================================================
# Singleton Instances (Module-level)
# =============================================================================

_policies: RiskPolicies = None
_assessor: RiskAssessor = None


def get_policies() -> RiskPolicies:
    """Get or create RiskPolicies singleton."""
    global _policies
    if _policies is None:
        _policies = create_default_policies()
    return _policies


def get_assessor() -> RiskAssessor:
    """Get or create RiskAssessor singleton."""
    global _assessor
    if _assessor is None:
        _assessor = RiskAssessor(policies=get_policies())
    return _assessor


# =============================================================================
# Policy Management Routes
# =============================================================================


@router.get(
    "/policies",
    response_model=schemas.PolicyListResponse,
    summary="List all risk policies",
    description="Get all configured risk policies for intent classification.",
)
async def list_policies() -> schemas.PolicyListResponse:
    """List all risk policies."""
    try:
        policies = get_policies()
        policy_list = []

        for policy in policies.get_all_policies():
            policy_list.append(
                schemas.PolicyResponse(
                    id=policy.id,
                    intent_category=schemas.IntentCategoryEnum(policy.intent_category.value),
                    sub_intent=policy.sub_intent,
                    default_risk_level=schemas.RiskLevelEnum(policy.default_risk_level.value),
                    requires_approval=policy.requires_approval,
                    approval_type=policy.approval_type,
                    factors=policy.factors,
                    description=policy.description,
                )
            )

        return schemas.PolicyListResponse(
            policies=policy_list,
            count=len(policy_list),
        )

    except Exception as e:
        logger.error(f"Failed to list policies: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "POLICY_LIST_ERROR", "message": str(e)},
        )


@router.get(
    "/policies/{intent_category}",
    response_model=schemas.PolicyListResponse,
    summary="List policies by category",
    description="Get risk policies for a specific intent category.",
)
async def list_policies_by_category(
    intent_category: schemas.IntentCategoryEnum,
) -> schemas.PolicyListResponse:
    """List policies by intent category."""
    try:
        from src.integrations.orchestration.intent_router.models import ITIntentCategory

        policies = get_policies()
        category = ITIntentCategory.from_string(intent_category.value)
        category_policies = policies.get_policies_for_category(category)

        policy_list = []
        for policy in category_policies:
            policy_list.append(
                schemas.PolicyResponse(
                    id=policy.id,
                    intent_category=schemas.IntentCategoryEnum(policy.intent_category.value),
                    sub_intent=policy.sub_intent,
                    default_risk_level=schemas.RiskLevelEnum(policy.default_risk_level.value),
                    requires_approval=policy.requires_approval,
                    approval_type=policy.approval_type,
                    factors=policy.factors,
                    description=policy.description,
                )
            )

        return schemas.PolicyListResponse(
            policies=policy_list,
            count=len(policy_list),
        )

    except Exception as e:
        logger.error(f"Failed to list policies by category: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "POLICY_LIST_ERROR", "message": str(e)},
        )


@router.post(
    "/policies/mode/{mode}",
    response_model=schemas.PolicyListResponse,
    summary="Switch policy mode",
    description="Switch between default, strict, and relaxed policy modes.",
)
async def switch_policy_mode(
    mode: str,
) -> schemas.PolicyListResponse:
    """Switch policy mode."""
    global _policies, _assessor

    try:
        if mode == "default":
            _policies = create_default_policies()
        elif mode == "strict":
            _policies = create_strict_policies()
        elif mode == "relaxed":
            _policies = create_relaxed_policies()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_MODE",
                    "message": f"Invalid mode: {mode}. Use 'default', 'strict', or 'relaxed'.",
                },
            )

        # Reset assessor to use new policies
        _assessor = RiskAssessor(policies=_policies)

        logger.info(f"Switched policy mode to: {mode}")

        # Return updated policy list
        return await list_policies()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to switch policy mode: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "MODE_SWITCH_ERROR", "message": str(e)},
        )


# =============================================================================
# Risk Assessment Routes
# =============================================================================


@router.post(
    "/risk/assess",
    response_model=schemas.RiskAssessmentResponse,
    summary="Assess risk for intent",
    description="Perform standalone risk assessment for an intent.",
)
async def assess_risk(
    request: schemas.RiskAssessmentRequest,
) -> schemas.RiskAssessmentResponse:
    """Assess risk for an intent."""
    try:
        from src.integrations.orchestration.intent_router.models import ITIntentCategory
        from src.integrations.orchestration.risk_assessor import AssessmentContext

        assessor = get_assessor()

        # Convert request to internal types
        intent_category = ITIntentCategory.from_string(request.intent_category.value)

        # Build context if provided
        context = None
        if request.context:
            context = AssessmentContext.from_dict(request.context)

        # Perform assessment
        assessment = assessor.assess_from_intent(
            intent_category=intent_category,
            sub_intent=request.sub_intent,
            context=context,
        )

        # Convert factors
        factor_responses = [
            schemas.RiskFactorResponse(
                name=f.name,
                description=f.description,
                weight=f.weight,
                value=f.value,
                impact=f.impact,
            )
            for f in assessment.factors
        ]

        return schemas.RiskAssessmentResponse(
            level=schemas.RiskLevelEnum(assessment.level.value),
            score=assessment.score,
            requires_approval=assessment.requires_approval,
            approval_type=assessment.approval_type,
            factors=factor_responses,
            reasoning=assessment.reasoning,
            policy_id=assessment.policy_id,
            adjustments_applied=assessment.adjustments_applied,
        )

    except Exception as e:
        logger.error(f"Failed to assess risk: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "RISK_ASSESSMENT_ERROR", "message": str(e)},
        )


# =============================================================================
# Metrics Routes
# =============================================================================


@router.get(
    "/metrics",
    response_model=schemas.MetricsResponse,
    summary="Get routing metrics",
    description="Get performance metrics for the intent routing system.",
)
async def get_metrics() -> schemas.MetricsResponse:
    """Get routing metrics."""
    try:
        # Note: In production, this would aggregate metrics from router instances
        # For now, return placeholder metrics
        return schemas.MetricsResponse(
            total_requests=0,
            pattern_matches=0,
            semantic_matches=0,
            llm_fallbacks=0,
            avg_latency_ms=0.0,
            p95_latency_ms=0.0,
        )

    except Exception as e:
        logger.error(f"Failed to get metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "METRICS_ERROR", "message": str(e)},
        )


@router.post(
    "/metrics/reset",
    response_model=Dict[str, str],
    summary="Reset routing metrics",
    description="Reset all routing metrics to zero.",
)
async def reset_metrics() -> Dict[str, str]:
    """Reset routing metrics."""
    try:
        # In production, this would reset router metrics
        logger.info("Metrics reset requested")
        return {"status": "success", "message": "Metrics reset successfully"}

    except Exception as e:
        logger.error(f"Failed to reset metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "METRICS_RESET_ERROR", "message": str(e)},
        )


# =============================================================================
# Health Check
# =============================================================================


@router.get(
    "/health",
    summary="Orchestration health check",
    description="Check orchestration module health status.",
)
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "module": "orchestration",
        "components": {
            "risk_assessor": "ready",
            "policies": f"{len(get_policies())} policies loaded",
        },
    }
