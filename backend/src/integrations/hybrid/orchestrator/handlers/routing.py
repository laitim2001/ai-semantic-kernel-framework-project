# =============================================================================
# IPA Platform - Routing Handler
# =============================================================================
# Sprint 132: Encapsulates InputGateway + BusinessIntentRouter +
#   FrameworkSelector routing logic extracted from HybridOrchestratorV2.
# =============================================================================

import logging
from typing import Any, Dict, Optional

from src.integrations.hybrid.intent import (
    ExecutionMode,
    FrameworkSelector,
    IntentAnalysis,
    SessionContext,
)
from src.integrations.hybrid.orchestrator.contracts import (
    Handler,
    HandlerResult,
    HandlerType,
    OrchestratorRequest,
)
from src.integrations.hybrid.orchestrator.events import EventType, RoutingEvent

logger = logging.getLogger(__name__)


class RoutingHandler(Handler):
    """Handles request routing through InputGateway and framework selection.

    Encapsulates:
    - InputGateway.process() for source identification
    - BusinessIntentRouter for IT intent classification
    - FrameworkSelector for execution mode determination
    - Completeness checking
    - Swarm mode eligibility detection
    """

    def __init__(
        self,
        *,
        input_gateway: Optional[Any] = None,
        business_router: Optional[Any] = None,
        framework_selector: Optional[FrameworkSelector] = None,
        swarm_handler: Optional[Any] = None,
    ):
        self._input_gateway = input_gateway
        self._business_router = business_router
        self._framework_selector = framework_selector or FrameworkSelector()
        self._swarm_handler = swarm_handler

    @property
    def handler_type(self) -> HandlerType:
        return HandlerType.ROUTING

    async def handle(
        self,
        request: OrchestratorRequest,
        context: Dict[str, Any],
    ) -> HandlerResult:
        """Execute routing logic.

        For Phase 28 flow (source_request present):
        1. Process through InputGateway
        2. Check completeness
        3. Check swarm eligibility

        For direct flow (no source_request):
        1. Analyze intent via FrameworkSelector
        """
        try:
            if request.source_request and self._input_gateway:
                return await self._handle_phase28_routing(request, context)
            return await self._handle_direct_routing(request, context)
        except Exception as e:
            logger.error(f"Routing handler error: {e}", exc_info=True)
            return HandlerResult(
                success=False,
                handler_type=HandlerType.ROUTING,
                error=str(e),
            )

    async def _handle_phase28_routing(
        self,
        request: OrchestratorRequest,
        context: Dict[str, Any],
    ) -> HandlerResult:
        """Phase 28 routing flow via InputGateway."""
        logger.info("RoutingHandler: Processing via InputGateway (Phase 28)")

        routing_decision = await self._input_gateway.process(request.source_request)
        context["routing_decision"] = routing_decision

        # Check completeness
        needs_dialog = not routing_decision.completeness.is_sufficient
        context["needs_dialog"] = needs_dialog

        # Check swarm eligibility
        needs_swarm = False
        swarm_decomposition = None
        if self._swarm_handler and self._swarm_handler.is_enabled:
            swarm_decomposition = self._swarm_handler.analyze_for_swarm(
                routing_decision=routing_decision,
                context=request.metadata or {},
            )
            needs_swarm = swarm_decomposition.should_use_swarm
            if needs_swarm:
                context["swarm_decomposition"] = swarm_decomposition

        # Framework selection
        session_context = context.get("session_context") or SessionContext(
            session_id=request.session_id or "",
            conversation_history=context.get("conversation_history", []),
            current_mode=context.get("current_mode", ExecutionMode.CHAT_MODE),
        )
        framework_analysis = await self._framework_selector.select_framework(
            user_input=request.content,
            session_context=session_context,
            routing_decision=routing_decision,
        )
        context["intent_analysis"] = framework_analysis
        context["execution_mode"] = framework_analysis.mode

        return HandlerResult(
            success=True,
            handler_type=HandlerType.ROUTING,
            data={
                "routing_decision": routing_decision,
                "framework_analysis": framework_analysis,
                "needs_dialog": needs_dialog,
                "needs_swarm": needs_swarm,
            },
        )

    async def _handle_direct_routing(
        self,
        request: OrchestratorRequest,
        context: Dict[str, Any],
    ) -> HandlerResult:
        """Direct routing with 3-tier intent router + FrameworkSelector.

        Phase 41: Uses BusinessIntentRouter (Pattern→Semantic→LLM) when
        available, instead of only FrameworkSelector.
        """
        logger.info("RoutingHandler: Direct intent routing")

        routing_decision = None

        # Sprint 144: Three-tier routing ALWAYS runs for security/risk assessment,
        # regardless of force_mode. Mode selection is user-controlled.
        if self._business_router:
            try:
                routing_decision = await self._business_router.route(request.content)
                context["routing_decision"] = routing_decision
                logger.info(
                    "RoutingHandler: 3-tier routed intent=%s, layer=%s, confidence=%.2f, risk=%s",
                    routing_decision.intent_category,
                    routing_decision.routing_layer,
                    routing_decision.confidence,
                    routing_decision.risk_level,
                )
            except Exception as e:
                logger.warning("RoutingHandler: 3-tier routing failed: %s", e)

        # Framework selection — force_mode takes priority
        if request.force_mode:
            intent_analysis = IntentAnalysis(
                mode=request.force_mode,
                confidence=1.0,
                reasoning=f"User-selected mode: {request.force_mode.value if hasattr(request.force_mode, 'value') else request.force_mode}",
                analysis_time_ms=0.0,
            )
        else:
            current_mode = context.get("current_mode", ExecutionMode.CHAT_MODE)
            is_workflow_active = current_mode == ExecutionMode.WORKFLOW_MODE
            pending_steps = 1 if is_workflow_active else 0

            session_context = SessionContext(
                session_id=request.session_id or "",
                conversation_history=context.get("conversation_history", []),
                current_mode=current_mode,
                workflow_active=is_workflow_active,
                pending_steps=pending_steps,
            )

            if routing_decision:
                intent_analysis = await self._framework_selector.select_framework(
                    user_input=request.content,
                    session_context=session_context,
                    routing_decision=routing_decision,
                )
            else:
                intent_analysis = await self._framework_selector.analyze_intent(
                    user_input=request.content,
                    session_context=session_context,
                )

        # Sprint 144: Generate mode suggestion from routing_decision
        # (for display only — user controls actual mode via force_mode)
        suggested_mode = None
        if routing_decision:
            rd_intent = str(getattr(routing_decision, "intent_category", "")).lower()
            rd_risk = str(getattr(routing_decision, "risk_level", "")).lower()

            if "incident" in rd_intent and "critical" in rd_risk:
                suggested_mode = "swarm"
            elif "incident" in rd_intent and "high" in rd_risk:
                suggested_mode = "workflow"
            elif "request" in rd_intent or "change" in rd_intent:
                suggested_mode = "workflow"

        context["intent_analysis"] = intent_analysis
        context["execution_mode"] = intent_analysis.mode
        if suggested_mode:
            context["suggested_mode"] = suggested_mode

        return HandlerResult(
            success=True,
            handler_type=HandlerType.ROUTING,
            data={
                "routing_decision": routing_decision,
                "intent_analysis": intent_analysis,
                "execution_mode": intent_analysis.mode,
                "suggested_mode": suggested_mode,
            },
        )
