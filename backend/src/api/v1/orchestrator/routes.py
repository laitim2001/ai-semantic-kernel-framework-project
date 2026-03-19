"""
Orchestrator Chat API — E2E pipeline endpoint.

Sprint 108 — Phase 35 A0 core hypothesis validation.
Provides a simple chat endpoint that wires:
  InputGateway -> BusinessIntentRouter -> OrchestratorMediator -> AgentHandler -> LLM response
"""

import logging
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from src.integrations.contracts.pipeline import PipelineRequest, PipelineResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


# =============================================================================
# Health Check
# =============================================================================


@router.get("/health")
async def orchestrator_health() -> Dict[str, Any]:
    """Health check for the orchestrator pipeline."""
    llm_status = "unknown"
    router_status = "unknown"

    # Check LLM availability
    try:
        from src.integrations.llm.factory import LLMServiceFactory

        llm_service = LLMServiceFactory.create(use_cache=True, cache_ttl=1800)
        llm_status = "available" if llm_service else "unavailable"
    except Exception as e:
        llm_status = f"error: {e}"

    # Check router availability
    try:
        from src.integrations.orchestration.intent_router.router import (
            create_router_with_llm,
        )

        intent_router = create_router_with_llm()
        router_status = "available" if intent_router else "unavailable"
    except Exception as e:
        router_status = f"error: {e}"

    return {
        "status": "ok",
        "pipeline": "orchestrator_chat",
        "components": {
            "llm_service": llm_status,
            "intent_router": router_status,
            "mediator": "available",
            "agent_handler": "available",
        },
    }


# =============================================================================
# Intent Test Endpoint
# =============================================================================


@router.get("/test-intent")
async def test_intent(
    q: str = Query(..., description="User input to classify"),
) -> Dict[str, Any]:
    """Test intent routing without full pipeline execution.

    Calls BusinessIntentRouter.route(q) and returns the RoutingDecision fields.
    """
    start_time = time.perf_counter()

    try:
        from src.integrations.orchestration.intent_router.router import (
            create_router_with_llm,
        )

        intent_router = create_router_with_llm()
    except Exception as e:
        logger.error("Failed to create intent router: %s", e, exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=f"Intent router unavailable: {e}",
        )

    try:
        decision = await intent_router.route(q)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return {
            "input": q,
            "intent_category": (
                decision.intent_category.value
                if hasattr(decision.intent_category, "value")
                else str(decision.intent_category)
            ),
            "sub_intent": decision.sub_intent,
            "confidence": decision.confidence,
            "risk_level": (
                decision.risk_level.value
                if hasattr(decision.risk_level, "value")
                else str(decision.risk_level)
            ),
            "routing_layer": decision.routing_layer,
            "workflow_type": (
                decision.workflow_type.value
                if hasattr(decision.workflow_type, "value")
                else str(decision.workflow_type)
            ),
            "reasoning": decision.reasoning,
            "processing_time_ms": round(elapsed_ms, 2),
        }

    except Exception as e:
        logger.error("Intent routing failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Intent routing error: {e}",
        )


# =============================================================================
# Chat Endpoint — E2E Pipeline
# =============================================================================


@router.post("/chat", response_model=PipelineResponse)
async def orchestrator_chat(request: PipelineRequest) -> PipelineResponse:
    """Execute the full E2E orchestration pipeline.

    Flow:
      1. Create LLM service (or fallback to mock)
      2. Create BusinessIntentRouter with LLM
      3. Route user input to get RoutingDecision
      4. Create AgentHandler + OrchestratorMediator
      5. Execute mediator pipeline
      6. Return PipelineResponse
    """
    start_time = time.perf_counter()

    # --- Step 1: Create LLM service ----------------------------------------
    llm_service = None
    try:
        from src.integrations.llm.factory import LLMServiceFactory

        llm_service = LLMServiceFactory.create(use_cache=True, cache_ttl=1800)
        logger.info("Orchestrator chat: LLM service created successfully")
    except Exception as e:
        logger.warning("Orchestrator chat: LLM service unavailable: %s", e)

    # --- Step 2: Create intent router --------------------------------------
    routing_decision = None
    try:
        from src.integrations.orchestration.intent_router.router import (
            create_router_with_llm,
        )

        intent_router = create_router_with_llm()
        logger.info("Orchestrator chat: Intent router created")
    except Exception as e:
        logger.warning("Orchestrator chat: Intent router creation failed: %s", e)
        intent_router = None

    # --- Step 3: Route user input ------------------------------------------
    if intent_router:
        try:
            routing_decision = await intent_router.route(request.content)
            logger.info(
                "Orchestrator chat: Routed intent=%s, layer=%s, confidence=%.2f",
                routing_decision.intent_category,
                routing_decision.routing_layer,
                routing_decision.confidence,
            )
        except Exception as e:
            logger.warning("Orchestrator chat: Intent routing failed: %s", e)

    # --- Step 4: Create AgentHandler + OrchestratorMediator ----------------
    try:
        from src.integrations.hybrid.orchestrator.agent_handler import AgentHandler
        from src.integrations.hybrid.orchestrator.mediator import OrchestratorMediator
        from src.integrations.hybrid.orchestrator.contracts import OrchestratorRequest

        agent_handler = AgentHandler(llm_service=llm_service)
        mediator = OrchestratorMediator(agent_handler=agent_handler)
        logger.info("Orchestrator chat: Mediator created with AgentHandler")
    except Exception as e:
        logger.error("Orchestrator chat: Mediator creation failed: %s", e, exc_info=True)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return PipelineResponse(
            content=f"Pipeline initialization error: {e}",
            processing_time_ms=round(elapsed_ms, 2),
            is_complete=False,
        )

    # --- Step 5: Execute mediator pipeline ---------------------------------
    try:
        # Build metadata with routing decision for AgentHandler to consume
        request_metadata: Dict[str, Any] = dict(request.metadata) if request.metadata else {}
        if routing_decision:
            request_metadata["routing_decision"] = _serialize_routing_decision(
                routing_decision
            )

        orchestrator_request = OrchestratorRequest(
            content=request.content,
            session_id=request.session_id,
            metadata=request_metadata,
        )

        response = await mediator.execute(orchestrator_request)
        logger.info(
            "Orchestrator chat: Pipeline completed, success=%s, framework=%s",
            response.success,
            response.framework_used,
        )
    except Exception as e:
        logger.error("Orchestrator chat: Pipeline execution failed: %s", e, exc_info=True)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return PipelineResponse(
            content=f"Pipeline execution error: {e}",
            processing_time_ms=round(elapsed_ms, 2),
            is_complete=False,
        )

    # --- Step 6: Build PipelineResponse ------------------------------------
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    intent_category_str: Optional[str] = None
    confidence_val: Optional[float] = None
    risk_level_str: Optional[str] = None
    routing_layer_str: Optional[str] = None

    if routing_decision:
        intent_category_str = (
            routing_decision.intent_category.value
            if hasattr(routing_decision.intent_category, "value")
            else str(routing_decision.intent_category)
        )
        confidence_val = routing_decision.confidence
        risk_level_str = (
            routing_decision.risk_level.value
            if hasattr(routing_decision.risk_level, "value")
            else str(routing_decision.risk_level)
        )
        routing_layer_str = routing_decision.routing_layer

    return PipelineResponse(
        content=response.content or "",
        intent_category=intent_category_str,
        confidence=confidence_val,
        risk_level=risk_level_str,
        routing_layer=routing_layer_str,
        framework_used=response.framework_used or "orchestrator_agent",
        session_id=response.session_id,
        is_complete=response.success,
        processing_time_ms=round(elapsed_ms, 2),
    )


# =============================================================================
# Private Helpers
# =============================================================================


def _serialize_routing_decision(decision: Any) -> Dict[str, Any]:
    """Convert a RoutingDecision object into a plain dict for metadata injection."""
    return {
        "intent_category": (
            decision.intent_category.value
            if hasattr(decision.intent_category, "value")
            else str(decision.intent_category)
        ),
        "sub_intent": getattr(decision, "sub_intent", None),
        "confidence": getattr(decision, "confidence", 0.0),
        "risk_level": (
            decision.risk_level.value
            if hasattr(decision.risk_level, "value")
            else str(getattr(decision, "risk_level", "unknown"))
        ),
        "routing_layer": getattr(decision, "routing_layer", "unknown"),
        "workflow_type": (
            decision.workflow_type.value
            if hasattr(decision.workflow_type, "value")
            else str(getattr(decision, "workflow_type", "unknown"))
        ),
        "reasoning": getattr(decision, "reasoning", ""),
    }
