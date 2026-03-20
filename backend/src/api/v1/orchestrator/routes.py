"""
Orchestrator Chat API — E2E pipeline endpoint.

Sprint 108 — Phase 35 A0 core hypothesis validation.
Sprint 112 — Phase 36 Orchestrator completeness (SessionFactory + ToolRegistry).

Provides a simple chat endpoint that wires:
  InputGateway -> BusinessIntentRouter -> OrchestratorMediator -> AgentHandler -> LLM response
"""

import logging
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from src.integrations.contracts.pipeline import PipelineRequest, PipelineResponse
from src.integrations.hybrid.orchestrator.tools import OrchestratorToolRegistry
from src.integrations.hybrid.orchestrator.session_factory import OrchestratorSessionFactory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])

# ---------------------------------------------------------------------------
# Module-level singletons (shared across requests)
# ---------------------------------------------------------------------------
_bootstrap: Optional[Any] = None
_tool_registry: Optional[OrchestratorToolRegistry] = None
_session_factory: Optional[OrchestratorSessionFactory] = None


def _get_bootstrap() -> Any:
    """Lazy-initialise the OrchestratorBootstrap (Phase 39 assembly)."""
    global _bootstrap
    if _bootstrap is None:
        try:
            from src.integrations.hybrid.orchestrator.bootstrap import (
                OrchestratorBootstrap,
            )
            _bootstrap = OrchestratorBootstrap()
            # Build triggers full pipeline assembly
            _bootstrap.build()
            logger.info("Orchestrator: Bootstrap assembly complete — %s",
                         _bootstrap.health_check())
        except Exception as e:
            logger.warning("Orchestrator: Bootstrap failed: %s", e)
    return _bootstrap


def _get_tool_registry() -> OrchestratorToolRegistry:
    """Return the shared tool registry (via Bootstrap if available)."""
    global _tool_registry
    if _tool_registry is None:
        bootstrap = _get_bootstrap()
        if bootstrap and bootstrap.tool_registry:
            _tool_registry = bootstrap.tool_registry
        else:
            # Fallback: standalone registry
            _tool_registry = OrchestratorToolRegistry()
            logger.info("Orchestrator: Using standalone tool registry (bootstrap unavailable)")
    return _tool_registry


def _get_session_factory() -> OrchestratorSessionFactory:
    """Lazy-initialise and return the shared session factory.

    Uses the Bootstrap's LLM service and tool registry when available.
    """
    global _session_factory
    if _session_factory is None:
        llm_service = None
        bootstrap = _get_bootstrap()

        if bootstrap and bootstrap._llm_service:
            llm_service = bootstrap._llm_service
        else:
            try:
                from src.integrations.llm.factory import LLMServiceFactory
                llm_service = LLMServiceFactory.create(use_cache=True, cache_ttl=1800)
            except Exception as e:
                logger.warning("Session factory: LLM service unavailable: %s", e)

        _session_factory = OrchestratorSessionFactory(
            llm_service=llm_service,
            max_sessions=200,
        )
        logger.info("Orchestrator: Session factory initialized (max_sessions=200)")
    return _session_factory


# =============================================================================
# E2E Validation (Sprint 120)
# =============================================================================


@router.get("/validate")
async def orchestrator_validate() -> Dict[str, Any]:
    """Run comprehensive E2E pipeline validation.

    Checks all components assembled across Phase 35-38.
    """
    from src.integrations.hybrid.orchestrator.e2e_validator import E2EValidator
    validator = E2EValidator()
    return await validator.validate_all()


# =============================================================================
# Health Check
# =============================================================================


@router.get("/health")
async def orchestrator_health() -> Dict[str, Any]:
    """Lightweight health check for the orchestrator pipeline.

    Avoids heavy initialisation (Bootstrap, LLM connections) to prevent
    worker crashes when external services are unavailable.
    """
    components: Dict[str, str] = {}

    # Check LLM config (without connecting)
    try:
        from src.core.config import get_settings
        settings = get_settings()
        has_azure = bool(getattr(settings, "AZURE_OPENAI_ENDPOINT", None))
        has_anthropic = bool(getattr(settings, "ANTHROPIC_API_KEY", None))
        components["llm_service"] = (
            "configured" if (has_azure or has_anthropic) else "not_configured"
        )
    except Exception as e:
        components["llm_service"] = f"error: {e}"

    # Check if bootstrap singleton exists (don't create it)
    components["bootstrap"] = "initialized" if _bootstrap is not None else "not_initialized"

    # Check session factory (don't create it)
    components["session_factory"] = (
        f"available (active_sessions={_session_factory.active_count})"
        if _session_factory is not None
        else "not_initialized"
    )

    # Check tool registry (don't create it)
    try:
        if _tool_registry is not None:
            tool_count = len(_tool_registry.list_tools(role="admin"))
            components["tool_registry"] = f"{tool_count} tools registered"
        else:
            components["tool_registry"] = "not_initialized"
    except Exception as e:
        components["tool_registry"] = f"error: {e}"

    # Check Redis
    try:
        import redis
        from src.core.config import get_settings
        s = get_settings()
        r = redis.Redis(
            host=getattr(s, "REDIS_HOST", "localhost"),
            port=int(getattr(s, "REDIS_PORT", 6379)),
            socket_connect_timeout=1,
        )
        r.ping()
        components["redis"] = "healthy"
    except Exception:
        components["redis"] = "unavailable"

    overall = "healthy" if components.get("redis") == "healthy" else "degraded"

    return {
        "status": overall,
        "pipeline": "orchestrator_chat",
        "components": components,
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


@router.post("/approval/{approval_id}")
async def orchestrator_approval(approval_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle HITL approval response.

    Sprint 146: User approves or rejects a high-risk pipeline operation.
    Unblocks the waiting pipeline via asyncio.Event.
    """
    action = body.get("action", "reject")
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'")

    # Find the mediator with the pending approval
    factory = _get_session_factory()
    resolved = False
    for sid in list(factory._sessions.keys()):
        mediator = factory._sessions.get(sid)
        if mediator and hasattr(mediator, "resolve_approval"):
            if mediator.resolve_approval(approval_id, action):
                resolved = True
                break

    if not resolved:
        raise HTTPException(status_code=404, detail=f"Approval {approval_id} not found or expired")

    logger.info("HITL approval %s: %s", approval_id, action)
    return {"approval_id": approval_id, "action": action, "status": "resolved"}


@router.post("/chat/stream")
async def orchestrator_chat_stream(request: PipelineRequest):
    """SSE streaming endpoint for the orchestration pipeline.

    Sprint 145: Returns a Server-Sent Events stream with real-time
    pipeline step events (ROUTING_COMPLETE, AGENT_THINKING, TEXT_DELTA,
    TOOL_CALL_END, PIPELINE_COMPLETE).

    The frontend can consume this with fetch() + ReadableStream.
    """
    import asyncio
    from fastapi.responses import StreamingResponse
    from src.integrations.hybrid.orchestrator.sse_events import PipelineEventEmitter
    from src.integrations.hybrid.orchestrator.contracts import OrchestratorRequest
    from src.integrations.hybrid.intent import ExecutionMode

    session_id = request.session_id or "default"
    factory = _get_session_factory()
    mediator = factory.get_or_create(session_id)

    # Create event emitter for this request
    emitter = PipelineEventEmitter()

    # Build OrchestratorRequest
    request_metadata: Dict[str, Any] = dict(request.metadata) if request.metadata else {}
    request_metadata["user_id"] = request.user_id or request.source or "anonymous"

    force_mode = None
    if request.mode:
        mode_map = {
            "chat": ExecutionMode.CHAT_MODE,
            "workflow": ExecutionMode.WORKFLOW_MODE,
            "swarm": ExecutionMode.SWARM_MODE,
            "hybrid": ExecutionMode.HYBRID_MODE,
        }
        force_mode = mode_map.get(request.mode.lower())

    orchestrator_request = OrchestratorRequest(
        content=request.content,
        session_id=request.session_id,
        user_id=request.user_id or request.source or "anonymous",
        force_mode=force_mode,
        metadata=request_metadata,
    )

    async def run_pipeline():
        """Run pipeline in background, pushing events to emitter."""
        try:
            await mediator.execute(orchestrator_request, event_emitter=emitter)
        except Exception as e:
            logger.error("SSE pipeline error: %s", e, exc_info=True)
            await emitter.emit_error(str(e))

    # Start pipeline in background task
    asyncio.create_task(run_pipeline())

    # Stream events to client
    return StreamingResponse(
        emitter.stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat", response_model=PipelineResponse)
async def orchestrator_chat(request: PipelineRequest) -> PipelineResponse:
    """Execute the full E2E orchestration pipeline.

    Phase 41: All 7 pipeline steps are handled by the mediator internally:
      1. ContextHandler  — memory read + context preparation
      2. RoutingHandler  — 3-tier intent routing + framework selection
      3. DialogHandler   — guided dialog (if needed)
      4. ApprovalHandler — risk assessment + HITL approval
      5. AgentHandler    — LLM response generation
      6. ExecutionHandler — MAF/Claude/Swarm task dispatch
      7. ObservabilityHandler — metrics
    """
    start_time = time.perf_counter()

    # --- Step 1: Get or create per-session Orchestrator via SessionFactory --
    try:
        from src.integrations.hybrid.orchestrator.contracts import OrchestratorRequest

        session_id = request.session_id or "default"
        factory = _get_session_factory()
        mediator = factory.get_or_create(session_id)
        logger.info(
            "Orchestrator chat: Mediator obtained for session '%s' "
            "(active sessions: %d, handlers: %s)",
            session_id,
            factory.active_count,
            mediator.registered_handlers,
        )
    except Exception as e:
        logger.error("Orchestrator chat: Mediator creation failed: %s", e, exc_info=True)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return PipelineResponse(
            content=f"Pipeline initialization error: {e}",
            processing_time_ms=round(elapsed_ms, 2),
            is_complete=False,
        )

    # --- Step 2: Execute full mediator pipeline ----------------------------
    try:
        request_metadata: Dict[str, Any] = dict(request.metadata) if request.metadata else {}
        request_metadata["user_id"] = request.user_id or request.source or "anonymous"

        # Sprint 144: Map user-selected mode to force_mode
        force_mode = None
        if request.mode:
            from src.integrations.hybrid.intent import ExecutionMode
            mode_map = {
                "chat": ExecutionMode.CHAT_MODE,
                "workflow": ExecutionMode.WORKFLOW_MODE,
                "swarm": ExecutionMode.SWARM_MODE,
                "hybrid": ExecutionMode.HYBRID_MODE,
            }
            force_mode = mode_map.get(request.mode.lower())

        orchestrator_request = OrchestratorRequest(
            content=request.content,
            session_id=request.session_id,
            user_id=request.user_id or request.source or "anonymous",
            force_mode=force_mode,
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

    # --- Step 3: Build PipelineResponse from mediator results --------------
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # Extract routing info from mediator response metadata
    intent_category_str: Optional[str] = None
    confidence_val: Optional[float] = None
    risk_level_str: Optional[str] = None
    routing_layer_str: Optional[str] = None

    meta = response.metadata or {}
    rd = meta.get("routing_decision")
    if rd and isinstance(rd, dict):
        intent_category_str = str(rd.get("intent_category", ""))
        confidence_val = rd.get("confidence")
        risk_level_str = str(rd.get("risk_level", ""))
        routing_layer_str = rd.get("routing_layer")
    elif rd and hasattr(rd, "intent_category"):
        intent_category_str = (
            rd.intent_category.value
            if hasattr(rd.intent_category, "value")
            else str(rd.intent_category)
        )
        confidence_val = rd.confidence
        risk_level_str = (
            rd.risk_level.value
            if hasattr(rd.risk_level, "value")
            else str(rd.risk_level)
        )
        routing_layer_str = rd.routing_layer

    # Sprint 144: Extract execution_mode from response object
    execution_mode_str: Optional[str] = None
    if hasattr(response, "execution_mode") and response.execution_mode:
        em = response.execution_mode
        execution_mode_str = em.value if hasattr(em, "value") else str(em)

    # Sprint 144: Extract tool_calls from agent_response
    tool_calls_list = None
    agent_resp = meta.get("agent_response") or {}
    if isinstance(agent_resp, dict) and agent_resp.get("tool_calls"):
        tool_calls_list = agent_resp["tool_calls"]

    # Sprint 144: Extract suggested_mode from metadata
    suggested_mode_str = meta.get("suggested_mode")

    return PipelineResponse(
        content=response.content or "",
        intent_category=intent_category_str,
        confidence=confidence_val,
        risk_level=risk_level_str,
        routing_layer=routing_layer_str,
        execution_mode=execution_mode_str,
        suggested_mode=suggested_mode_str,
        framework_used=response.framework_used or "orchestrator_agent",
        session_id=response.session_id,
        is_complete=response.success,
        tool_calls=tool_calls_list,
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
