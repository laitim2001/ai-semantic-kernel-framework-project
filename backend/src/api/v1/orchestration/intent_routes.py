"""
Intent Classification API Routes

Routes for intent classification and testing endpoints.

Sprint 96: Story 96-5 - API Route Implementation (Phase 28)
"""

import logging
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, status

from src.integrations.orchestration import (
    BusinessIntentRouter,
    MockBusinessIntentRouter,
    RiskAssessor,
    RiskPolicies,
    RouterConfig,
)
from src.integrations.orchestration.intent_router.models import (
    ITIntentCategory,
    RiskLevel,
)
from src.integrations.orchestration.risk_assessor import AssessmentContext

from . import schemas
from .routes import get_assessor, get_policies

logger = logging.getLogger(__name__)

intent_router = APIRouter(
    prefix="/orchestration/intent",
    tags=["Intent Classification"],
    responses={
        500: {"model": schemas.ErrorResponse, "description": "Internal Server Error"},
    },
)


# =============================================================================
# Singleton Router Instance
# =============================================================================

_router_instance: Optional[MockBusinessIntentRouter] = None


def get_router() -> MockBusinessIntentRouter:
    """Get or create router singleton."""
    global _router_instance
    if _router_instance is None:
        _router_instance = MockBusinessIntentRouter(
            config=RouterConfig(
                pattern_threshold=0.90,
                semantic_threshold=0.85,
                enable_llm_fallback=True,
                enable_completeness=True,
            )
        )
    return _router_instance


# =============================================================================
# Intent Classification Routes
# =============================================================================


@intent_router.post(
    "/classify",
    response_model=schemas.IntentClassifyResponse,
    summary="Classify user intent",
    description="Classify user input and return routing decision with optional risk assessment.",
)
async def classify_intent(
    request: schemas.IntentClassifyRequest,
) -> schemas.IntentClassifyResponse:
    """
    Classify user intent and return routing decision.

    The classification goes through three layers:
    1. Pattern Matcher (rule-based, < 10ms)
    2. Semantic Router (vector similarity, < 100ms)
    3. LLM Classifier (Claude Haiku, < 2000ms)

    Returns the routing decision with completeness assessment and optional risk evaluation.
    """
    try:
        router = get_router()
        assessor = get_assessor()

        # Perform routing
        routing_decision = await router.route(request.content)

        # Build completeness response
        completeness_response = schemas.CompletenessInfoResponse(
            is_complete=routing_decision.completeness.is_complete,
            missing_fields=routing_decision.completeness.missing_fields,
            optional_missing=routing_decision.completeness.optional_missing,
            completeness_score=routing_decision.completeness.completeness_score,
            suggestions=routing_decision.completeness.suggestions,
        )

        # Build routing decision response
        decision_response = schemas.RoutingDecisionResponse(
            intent_category=schemas.IntentCategoryEnum(
                routing_decision.intent_category.value
            ),
            sub_intent=routing_decision.sub_intent,
            confidence=routing_decision.confidence,
            workflow_type=schemas.WorkflowTypeEnum(routing_decision.workflow_type.value),
            risk_level=schemas.RiskLevelEnum(routing_decision.risk_level.value),
            completeness=completeness_response,
            routing_layer=routing_decision.routing_layer,
            rule_id=routing_decision.rule_id,
            reasoning=routing_decision.reasoning,
            processing_time_ms=routing_decision.processing_time_ms,
            timestamp=routing_decision.timestamp,
        )

        # Perform risk assessment if requested
        risk_assessment_response = None
        if request.include_risk_assessment:
            # Build context from request
            context = None
            if request.context:
                context = AssessmentContext.from_dict(request.context)

            assessment = assessor.assess(routing_decision, context)

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

            risk_assessment_response = schemas.RiskAssessmentResponse(
                level=schemas.RiskLevelEnum(assessment.level.value),
                score=assessment.score,
                requires_approval=assessment.requires_approval,
                approval_type=assessment.approval_type,
                factors=factor_responses,
                reasoning=assessment.reasoning,
                policy_id=assessment.policy_id,
                adjustments_applied=assessment.adjustments_applied,
            )

        return schemas.IntentClassifyResponse(
            routing_decision=decision_response,
            risk_assessment=risk_assessment_response,
            metadata={
                "source": request.source,
                "router_version": "1.0.0",
            },
        )

    except Exception as e:
        logger.error(f"Failed to classify intent: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "CLASSIFICATION_ERROR", "message": str(e)},
        )


@intent_router.post(
    "/test",
    response_model=schemas.IntentTestResponse,
    summary="Test intent classification",
    description="Test intent classification with detailed layer-by-layer results (debug mode).",
)
async def test_intent(
    request: schemas.IntentTestRequest,
) -> schemas.IntentTestResponse:
    """
    Test intent classification with detailed layer results.

    This endpoint is for debugging and testing purposes.
    Returns results from each classification layer.
    """
    try:
        start_time = time.perf_counter()
        router = get_router()

        layer_results = []

        # Layer 1: Pattern Matcher
        pattern_start = time.perf_counter()
        pattern_result = router.pattern_matcher.match(request.content)
        pattern_latency = (time.perf_counter() - pattern_start) * 1000

        layer_results.append(
            schemas.LayerResultResponse(
                layer="pattern",
                matched=pattern_result.matched,
                confidence=pattern_result.confidence,
                result={
                    "intent_category": (
                        pattern_result.intent_category.value
                        if pattern_result.intent_category
                        else None
                    ),
                    "sub_intent": pattern_result.sub_intent,
                    "rule_id": pattern_result.rule_id,
                    "matched_pattern": pattern_result.matched_pattern,
                }
                if pattern_result.matched
                else None,
                latency_ms=pattern_latency,
            )
        )

        # Layer 2: Semantic Router
        semantic_start = time.perf_counter()
        semantic_result = await router.semantic_router.route(request.content)
        semantic_latency = (time.perf_counter() - semantic_start) * 1000

        layer_results.append(
            schemas.LayerResultResponse(
                layer="semantic",
                matched=semantic_result.matched,
                confidence=semantic_result.similarity,
                result={
                    "intent_category": (
                        semantic_result.intent_category.value
                        if semantic_result.intent_category
                        else None
                    ),
                    "sub_intent": semantic_result.sub_intent,
                    "route_name": semantic_result.route_name,
                }
                if semantic_result.matched
                else None,
                latency_ms=semantic_latency,
            )
        )

        # Layer 3: LLM Classifier (mock in test mode)
        llm_start = time.perf_counter()
        llm_result = await router.llm_classifier.classify(request.content)
        llm_latency = (time.perf_counter() - llm_start) * 1000

        layer_results.append(
            schemas.LayerResultResponse(
                layer="llm",
                matched=True,  # LLM always produces a result
                confidence=llm_result.confidence,
                result={
                    "intent_category": llm_result.intent_category.value,
                    "sub_intent": llm_result.sub_intent,
                    "reasoning": llm_result.reasoning,
                    "model": llm_result.model,
                },
                latency_ms=llm_latency,
            )
        )

        # Get final routing decision
        routing_decision = await router.route(request.content)
        total_latency = (time.perf_counter() - start_time) * 1000

        # Build completeness response
        completeness_response = schemas.CompletenessInfoResponse(
            is_complete=routing_decision.completeness.is_complete,
            missing_fields=routing_decision.completeness.missing_fields,
            optional_missing=routing_decision.completeness.optional_missing,
            completeness_score=routing_decision.completeness.completeness_score,
            suggestions=routing_decision.completeness.suggestions,
        )

        # Build final decision response
        decision_response = schemas.RoutingDecisionResponse(
            intent_category=schemas.IntentCategoryEnum(
                routing_decision.intent_category.value
            ),
            sub_intent=routing_decision.sub_intent,
            confidence=routing_decision.confidence,
            workflow_type=schemas.WorkflowTypeEnum(routing_decision.workflow_type.value),
            risk_level=schemas.RiskLevelEnum(routing_decision.risk_level.value),
            completeness=completeness_response,
            routing_layer=routing_decision.routing_layer,
            rule_id=routing_decision.rule_id,
            reasoning=routing_decision.reasoning,
            processing_time_ms=routing_decision.processing_time_ms,
            timestamp=routing_decision.timestamp,
        )

        return schemas.IntentTestResponse(
            input=request.content,
            final_decision=decision_response,
            layer_results=layer_results,
            total_latency_ms=total_latency,
        )

    except Exception as e:
        logger.error(f"Failed to test intent: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "TEST_ERROR", "message": str(e)},
        )


# =============================================================================
# Batch Classification
# =============================================================================


@intent_router.post(
    "/classify/batch",
    summary="Batch classify intents",
    description="Classify multiple inputs in a batch.",
)
async def batch_classify(
    requests: list[schemas.IntentClassifyRequest],
) -> list[schemas.IntentClassifyResponse]:
    """Classify multiple inputs in batch."""
    try:
        results = []
        for request in requests:
            result = await classify_intent(request)
            results.append(result)
        return results

    except Exception as e:
        logger.error(f"Failed to batch classify: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "BATCH_CLASSIFICATION_ERROR", "message": str(e)},
        )


# =============================================================================
# Quick Classification (Simplified Response)
# =============================================================================


@intent_router.post(
    "/quick",
    summary="Quick intent classification",
    description="Simplified classification returning only essential fields.",
)
async def quick_classify(
    content: str,
) -> Dict[str, Any]:
    """
    Quick classification with minimal response.

    Returns only:
    - intent_category
    - sub_intent
    - confidence
    - risk_level
    - requires_approval
    """
    try:
        router = get_router()
        assessor = get_assessor()

        routing_decision = await router.route(content)
        assessment = assessor.assess(routing_decision)

        return {
            "intent_category": routing_decision.intent_category.value,
            "sub_intent": routing_decision.sub_intent,
            "confidence": round(routing_decision.confidence, 2),
            "risk_level": assessment.level.value,
            "requires_approval": assessment.requires_approval,
        }

    except Exception as e:
        logger.error(f"Failed to quick classify: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "QUICK_CLASSIFICATION_ERROR", "message": str(e)},
        )
