# =============================================================================
# IPA Platform - Hybrid Core API Routes
# =============================================================================
# Phase 13: Hybrid Core Architecture
# Sprint 52-54: Intent Router, Context Bridge, HybridOrchestrator
#
# REST API endpoints for hybrid core operations:
#   - POST /hybrid/analyze - Analyze user intent and determine execution mode
#   - POST /hybrid/execute - Execute task using hybrid orchestrator
#   - GET /hybrid/metrics - Get unified metrics from all components
#
# Dependencies:
#   - IntentRouter (src.integrations.hybrid.intent)
#   - HybridOrchestratorV2 (src.integrations.hybrid.orchestrator_v2)
#   - ContextBridge (src.integrations.hybrid.context)
# =============================================================================

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.integrations.hybrid.intent import (
    ExecutionMode,
    IntentRouter,
    SessionContext,
)
from src.integrations.hybrid.intent.classifiers.rule_based import RuleBasedClassifier
from src.integrations.hybrid.orchestrator_v2 import (
    HybridOrchestratorV2,
    HybridResultV2,
    OrchestratorConfig,
)
from .dependencies import get_claude_executor
from src.integrations.hybrid.context import ContextBridge

logger = logging.getLogger(__name__)


# =============================================================================
# Cross-Module Synchronization
# =============================================================================

def _sync_session_mode_cache(session_id: str, mode: ExecutionMode) -> None:
    """Synchronize session mode to switch_routes cache.

    This ensures that when execute_hybrid sets a mode (especially via force_mode),
    the switch_routes module has the correct current mode for subsequent switch operations.
    """
    try:
        from .switch_routes import set_session_mode, _session_modes
        logger.info(f"_sync_session_mode_cache: dict id={id(_session_modes)}, BEFORE sync - _session_modes = {dict(_session_modes)}")
        set_session_mode(session_id, mode)
        logger.info(f"_sync_session_mode_cache: dict id={id(_session_modes)}, AFTER sync - session={session_id}, mode={mode.value}, _session_modes = {dict(_session_modes)}")
    except ImportError as e:
        # switch_routes not available, skip sync
        logger.warning(f"_sync_session_mode_cache: ImportError - {e}")
    except Exception as e:
        logger.warning(f"Failed to sync session mode cache: {e}")

router = APIRouter(
    prefix="/hybrid",
    tags=["hybrid-core"],
    responses={
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"},
    },
)


# =============================================================================
# Singleton Instances
# =============================================================================

_intent_router: Optional[IntentRouter] = None
_orchestrator: Optional[HybridOrchestratorV2] = None
_context_bridge: Optional[ContextBridge] = None


def get_intent_router() -> IntentRouter:
    """Get or create IntentRouter singleton."""
    global _intent_router
    if _intent_router is None:
        # Initialize with default classifiers
        rule_classifier = RuleBasedClassifier()
        _intent_router = IntentRouter(
            classifiers=[rule_classifier],
            confidence_threshold=0.7,
        )
        logger.info("IntentRouter initialized with RuleBasedClassifier")
    return _intent_router


def get_orchestrator() -> HybridOrchestratorV2:
    """Get or create HybridOrchestratorV2 singleton."""
    global _orchestrator, _intent_router, _context_bridge
    if _orchestrator is None:
        _intent_router = get_intent_router()
        _context_bridge = get_context_bridge()

        # 獲取 Claude executor (如果可用)
        claude_executor = get_claude_executor()

        _orchestrator = HybridOrchestratorV2(
            config=OrchestratorConfig(),
            intent_router=_intent_router,
            context_bridge=_context_bridge,
            claude_executor=claude_executor,
        )

        if claude_executor:
            logger.info("HybridOrchestratorV2 initialized with REAL Claude executor")
        else:
            logger.warning("HybridOrchestratorV2 initialized in SIMULATION mode")
    return _orchestrator


def get_context_bridge() -> ContextBridge:
    """Get or create ContextBridge singleton."""
    global _context_bridge
    if _context_bridge is None:
        _context_bridge = ContextBridge()
        logger.info("ContextBridge initialized")
    return _context_bridge


# =============================================================================
# Request/Response Schemas
# =============================================================================


class IntentAnalyzeRequest(BaseModel):
    """Request schema for intent analysis."""
    input_text: str = Field(..., min_length=1, description="User input text to analyze")
    session_id: Optional[str] = Field(None, description="Optional session ID for context")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for analysis")


class ClassificationResultResponse(BaseModel):
    """Classification result from a single classifier."""
    classifier_name: str
    mode: str
    confidence: float
    reasoning: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntentAnalyzeResponse(BaseModel):
    """Response schema for intent analysis."""
    mode: str = Field(..., description="Detected execution mode: workflow, chat, or hybrid")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    reasoning: str = Field(..., description="Explanation for the mode decision")
    suggested_framework: str = Field(..., description="Suggested framework: maf, claude, or hybrid")
    classification_results: List[ClassificationResultResponse] = Field(
        default_factory=list,
        description="Results from individual classifiers"
    )
    detected_features: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detected features from analysis"
    )
    analysis_time_ms: float = Field(..., description="Time taken for analysis in milliseconds")


class HybridExecuteRequest(BaseModel):
    """Request schema for hybrid execution."""
    input_text: str = Field(..., min_length=1, description="Task prompt or user message")
    session_id: Optional[str] = Field(None, description="Session ID (creates new if not provided)")
    force_mode: Optional[str] = Field(
        None,
        description="Force execution mode: workflow, chat, or hybrid"
    )
    tools: Optional[List[Dict[str, Any]]] = Field(None, description="Available tools")
    max_tokens: Optional[int] = Field(None, ge=1, description="Maximum response tokens")
    timeout: Optional[float] = Field(None, ge=1.0, description="Timeout in seconds")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional execution context")


class HybridExecuteResponse(BaseModel):
    """Response schema for hybrid execution."""
    success: bool
    content: str = ""
    error: Optional[str] = None
    framework_used: str = ""
    execution_mode: str = ""
    session_id: Optional[str] = None
    intent_analysis: Optional[IntentAnalyzeResponse] = None
    tool_results: List[Dict[str, Any]] = Field(default_factory=list)
    duration: float = 0.0
    tokens_used: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UnifiedMetricsResponse(BaseModel):
    """Response schema for unified metrics."""
    orchestrator: Dict[str, Any] = Field(default_factory=dict)
    intent_router: Dict[str, Any] = Field(default_factory=dict)
    context_bridge: Dict[str, Any] = Field(default_factory=dict)
    risk_assessment: Optional[Dict[str, Any]] = None
    switch: Optional[Dict[str, Any]] = None


# =============================================================================
# Helper Functions
# =============================================================================


def _parse_execution_mode(mode_str: str) -> ExecutionMode:
    """Parse execution mode string to enum."""
    mode_map = {
        "workflow": ExecutionMode.WORKFLOW_MODE,
        "chat": ExecutionMode.CHAT_MODE,
        "hybrid": ExecutionMode.HYBRID_MODE,
    }
    if mode_str.lower() not in mode_map:
        raise ValueError(f"Invalid mode: {mode_str}")
    return mode_map[mode_str.lower()]


def _intent_analysis_to_response(analysis) -> IntentAnalyzeResponse:
    """Convert IntentAnalysis to API response."""
    classification_results = []
    for result in analysis.classification_results:
        classification_results.append(
            ClassificationResultResponse(
                classifier_name=result.classifier_name,
                mode=result.mode.value,
                confidence=result.confidence,
                reasoning=result.reasoning,
                metadata=result.metadata or {},
            )
        )

    return IntentAnalyzeResponse(
        mode=analysis.mode.value,
        confidence=analysis.confidence,
        reasoning=analysis.reasoning,
        suggested_framework=analysis.suggested_framework.value if analysis.suggested_framework else "claude",
        classification_results=classification_results,
        detected_features=analysis.detected_features or {},
        analysis_time_ms=analysis.analysis_time_ms or 0.0,  # Handle None for forced mode
    )


def _result_to_response(result: HybridResultV2) -> HybridExecuteResponse:
    """Convert HybridResultV2 to API response."""
    intent_response = None
    if result.intent_analysis:
        intent_response = _intent_analysis_to_response(result.intent_analysis)

    tool_results = []
    for tr in result.tool_results:
        tool_results.append({
            "tool_name": tr.tool_name,
            "success": tr.success,
            "result": tr.result,
            "error": tr.error,
            "source": tr.source.value if tr.source else "unknown",
            "duration_ms": tr.duration_ms,
        })

    return HybridExecuteResponse(
        success=result.success,
        content=result.content,
        error=result.error,
        framework_used=result.framework_used,
        execution_mode=result.execution_mode.value if result.execution_mode else "unknown",
        session_id=result.session_id,
        intent_analysis=intent_response,
        tool_results=tool_results,
        duration=result.duration,
        tokens_used=result.tokens_used,
        metadata=result.metadata or {},
    )


# =============================================================================
# API Routes
# =============================================================================


@router.post(
    "/analyze",
    response_model=IntentAnalyzeResponse,
    summary="Analyze user intent",
    description="Analyze user input to determine optimal execution mode (workflow, chat, or hybrid).",
)
async def analyze_intent(request: IntentAnalyzeRequest) -> IntentAnalyzeResponse:
    """
    Analyze user intent and determine execution mode.

    This endpoint uses the IntentRouter to analyze user input and determine
    whether it should be handled in workflow mode (multi-step structured),
    chat mode (conversational), or hybrid mode (dynamic switching).

    Args:
        request: Intent analysis request with input text and optional context

    Returns:
        IntentAnalyzeResponse: Analysis result with mode, confidence, and reasoning

    Example:
        POST /api/v1/hybrid/analyze
        {
            "input_text": "Create a workflow to process customer orders",
            "session_id": "sess_123"
        }
    """
    try:
        intent_router = get_intent_router()

        # Build session context if provided
        session_context = None
        if request.session_id or request.context:
            ctx = request.context or {}

            # Determine if workflow is active from context indicators
            workflow_active = bool(
                ctx.get("current_workflow") or
                ctx.get("workflow_id") or
                ctx.get("workflow_active") or
                ctx.get("workflow_step") is not None
            )

            # Extract pending steps from context
            pending_steps = ctx.get("workflow_step", 0) if workflow_active else 0

            session_context = SessionContext(
                session_id=request.session_id or "",
                workflow_active=workflow_active,
                pending_steps=pending_steps,
                context_variables=ctx,
                metadata=ctx,
            )

        # Analyze intent
        analysis = await intent_router.analyze_intent(
            user_input=request.input_text,
            session_context=session_context,
        )

        logger.info(
            f"Intent analysis: mode={analysis.mode.value}, "
            f"confidence={analysis.confidence:.2f}, "
            f"time={analysis.analysis_time_ms:.1f}ms"
        )

        return _intent_analysis_to_response(analysis)

    except Exception as e:
        logger.error(f"Intent analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Intent analysis failed: {str(e)}"
        )


@router.post(
    "/execute",
    response_model=HybridExecuteResponse,
    summary="Execute hybrid task",
    description="Execute a task using intelligent mode selection and the hybrid orchestrator.",
)
async def execute_hybrid(request: HybridExecuteRequest) -> HybridExecuteResponse:
    """
    Execute a task using the hybrid orchestrator.

    This endpoint uses HybridOrchestratorV2 to execute tasks with intelligent
    mode selection. It automatically determines the best execution mode
    (workflow, chat, or hybrid) based on the input, or uses a forced mode
    if specified.

    Args:
        request: Execution request with input text and options

    Returns:
        HybridExecuteResponse: Execution result with content and metadata

    Example:
        POST /api/v1/hybrid/execute
        {
            "input_text": "Help me analyze this data",
            "session_id": "sess_123",
            "force_mode": "chat"
        }
    """
    try:
        orchestrator = get_orchestrator()

        # Parse force_mode if provided
        force_mode = None
        if request.force_mode:
            try:
                force_mode = _parse_execution_mode(request.force_mode)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid force_mode: {request.force_mode}. "
                           f"Valid options: workflow, chat, hybrid"
                )

        # Execute task
        result = await orchestrator.execute(
            prompt=request.input_text,
            session_id=request.session_id,
            force_mode=force_mode,
            tools=request.tools,
            max_tokens=request.max_tokens,
            timeout=request.timeout,
            metadata=request.context,
        )

        logger.info(
            f"Hybrid execution: success={result.success}, "
            f"mode={result.execution_mode.value if result.execution_mode else 'unknown'}, "
            f"framework={result.framework_used}, "
            f"session_id={result.session_id}, "
            f"duration={result.duration:.2f}s"
        )

        # Sync session mode to switch_routes cache for consistency
        # This ensures subsequent switch operations know the current mode
        logger.info(
            f"Sync condition check: success={result.success}, "
            f"session_id={result.session_id}, execution_mode={result.execution_mode}"
        )
        if result.success and result.session_id and result.execution_mode:
            logger.info(f"Calling _sync_session_mode_cache for session={result.session_id}, mode={result.execution_mode}")
            _sync_session_mode_cache(result.session_id, result.execution_mode)
        else:
            logger.warning(f"Skipping sync: conditions not met")

        return _result_to_response(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Hybrid execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hybrid execution failed: {str(e)}"
        )


@router.get(
    "/metrics",
    response_model=UnifiedMetricsResponse,
    summary="Get unified metrics",
    description="Get performance metrics from all hybrid components.",
)
async def get_unified_metrics(
    include_risk: bool = Query(True, description="Include risk assessment metrics"),
    include_switch: bool = Query(True, description="Include switch metrics"),
) -> UnifiedMetricsResponse:
    """
    Get unified metrics from all hybrid components.

    This endpoint aggregates metrics from:
    - HybridOrchestratorV2: Execution counts, mode usage, success rates
    - IntentRouter: Classification statistics
    - ContextBridge: Sync statistics
    - RiskAssessmentEngine: Assessment metrics (optional)
    - ModeSwitcher: Switch metrics (optional)

    Args:
        include_risk: Whether to include risk assessment metrics
        include_switch: Whether to include switch metrics

    Returns:
        UnifiedMetricsResponse: Aggregated metrics from all components
    """
    orchestrator = get_orchestrator()
    intent_router = get_intent_router()
    context_bridge = get_context_bridge()

    # Orchestrator metrics
    orchestrator_metrics = orchestrator.get_metrics()

    # Intent router metrics
    intent_metrics = {
        "classifier_count": len(intent_router.get_classifiers()),
        "enabled_classifiers": len(intent_router.get_enabled_classifiers()),
        "confidence_threshold": intent_router.confidence_threshold,
        "default_mode": intent_router.default_mode.value,
    }

    # Context bridge metrics
    context_metrics = {
        "cached_contexts": len(context_bridge._context_cache),
    }

    # Risk assessment metrics (optional)
    risk_metrics = None
    if include_risk:
        try:
            # Import risk engine lazily to avoid circular imports
            from src.integrations.hybrid.risk.engine import create_engine
            engine = create_engine()
            risk_data = engine.get_metrics()
            risk_metrics = {
                "total_assessments": risk_data.total_assessments,
                "assessments_by_level": risk_data.assessments_by_level,
                "average_score": risk_data.average_score,
                "approval_rate": risk_data.approval_rate,
                "average_latency_ms": risk_data.average_latency_ms,
            }
        except Exception as e:
            logger.warning(f"Could not get risk metrics: {e}")
            risk_metrics = {"error": str(e)}

    # Switch metrics (optional)
    switch_metrics = None
    if include_switch:
        try:
            from src.integrations.hybrid.switching import ModeSwitcher
            # Note: We'd need to access the singleton from switch_routes
            # For now, return basic structure
            switch_metrics = {
                "available": True,
                "note": "Switch metrics available via /hybrid/switch/status/{session_id}",
            }
        except Exception as e:
            logger.warning(f"Could not get switch metrics: {e}")
            switch_metrics = {"error": str(e)}

    return UnifiedMetricsResponse(
        orchestrator=orchestrator_metrics,
        intent_router=intent_metrics,
        context_bridge=context_metrics,
        risk_assessment=risk_metrics,
        switch=switch_metrics,
    )


@router.get(
    "/status",
    summary="Get hybrid system status",
    description="Get overall status of the hybrid system.",
)
async def get_system_status() -> Dict[str, Any]:
    """
    Get overall hybrid system status.

    Returns:
        dict: System status with component availability
    """
    status_info = {
        "status": "operational",
        "components": {
            "intent_router": {"available": True, "status": "ready"},
            "orchestrator": {"available": True, "status": "ready"},
            "context_bridge": {"available": True, "status": "ready"},
            "risk_assessment": {"available": True, "status": "ready"},
            "mode_switcher": {"available": True, "status": "ready"},
        },
        "version": "2.0.0",
        "phase": "Phase 13 - Hybrid Core Architecture",
    }

    # Check each component
    try:
        get_intent_router()
    except Exception as e:
        status_info["components"]["intent_router"] = {"available": False, "error": str(e)}
        status_info["status"] = "degraded"

    try:
        get_orchestrator()
    except Exception as e:
        status_info["components"]["orchestrator"] = {"available": False, "error": str(e)}
        status_info["status"] = "degraded"

    try:
        get_context_bridge()
    except Exception as e:
        status_info["components"]["context_bridge"] = {"available": False, "error": str(e)}
        status_info["status"] = "degraded"

    return status_info
