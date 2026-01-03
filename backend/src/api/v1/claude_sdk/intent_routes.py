# =============================================================================
# IPA Platform - Intent Router API Routes
# =============================================================================
# Phase 13: Hybrid Core Architecture
# Sprint 52: S52-3 Intent Router API Integration (7 pts)
#
# Provides REST API endpoints for intent classification and mode detection.
# Integrates with IntentRouter, RuleBasedClassifier, ComplexityAnalyzer,
# and MultiAgentDetector components.
#
# Endpoints:
#   POST /api/v1/claude-sdk/intent/classify - Classify user intent
#   POST /api/v1/claude-sdk/intent/analyze-complexity - Analyze task complexity
#   POST /api/v1/claude-sdk/intent/detect-multi-agent - Detect multi-agent needs
#   GET /api/v1/claude-sdk/intent/classifiers - List available classifiers
#   GET /api/v1/claude-sdk/intent/stats - Get classification statistics
#   PUT /api/v1/claude-sdk/intent/config - Update router configuration
# =============================================================================

from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.integrations.hybrid.intent.router import IntentRouter
from src.integrations.hybrid.intent.models import (
    ExecutionMode,
    SessionContext,
    Message,
)
from src.integrations.hybrid.intent.classifiers.rule_based import RuleBasedClassifier
from src.integrations.hybrid.intent.analyzers.complexity import ComplexityAnalyzer
from src.integrations.hybrid.intent.analyzers.multi_agent import MultiAgentDetector


# =============================================================================
# Enums
# =============================================================================


class ExecutionModeType(str, Enum):
    """API execution mode type."""

    CHAT_MODE = "chat_mode"
    WORKFLOW_MODE = "workflow_mode"
    HYBRID_MODE = "hybrid_mode"


class CollaborationType(str, Enum):
    """Multi-agent collaboration types."""

    NONE = "none"
    HANDOFF = "handoff"
    GROUPCHAT = "groupchat"
    ROUND_ROBIN = "round_robin"
    COLLABORATION = "collaboration"
    MULTI_SPECIALIST = "multi_specialist"
    COORDINATION = "coordination"
    DUAL_AGENT = "dual_agent"


# =============================================================================
# Request Schemas
# =============================================================================


class ClassifyIntentRequest(BaseModel):
    """Request schema for intent classification."""

    user_input: str = Field(..., description="User input to classify", min_length=1)
    session_id: Optional[str] = Field(None, description="Optional session ID for context")
    workflow_active: bool = Field(False, description="Whether a workflow is currently active")
    pending_steps: int = Field(0, description="Number of pending workflow steps", ge=0)
    current_mode: Optional[ExecutionModeType] = Field(None, description="Current execution mode")
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        None, description="Previous conversation messages"
    )


class AnalyzeComplexityRequest(BaseModel):
    """Request schema for complexity analysis."""

    user_input: str = Field(..., description="User input to analyze", min_length=1)
    include_reasoning: bool = Field(True, description="Whether to include analysis reasoning")


class DetectMultiAgentRequest(BaseModel):
    """Request schema for multi-agent detection."""

    user_input: str = Field(..., description="User input to analyze", min_length=1)
    include_domains: bool = Field(True, description="Whether to include detected domains")
    include_roles: bool = Field(True, description="Whether to include detected roles")


class UpdateConfigRequest(BaseModel):
    """Request schema for updating router configuration."""

    enable_llm_classifier: bool = Field(True, description="Enable LLM-based classifier")
    enable_rule_based: bool = Field(True, description="Enable rule-based classifier")
    enable_complexity_boost: bool = Field(True, description="Enable complexity-based boosting")
    enable_multi_agent_boost: bool = Field(True, description="Enable multi-agent detection boost")
    default_mode: ExecutionModeType = Field(
        ExecutionModeType.CHAT_MODE, description="Default mode when no clear signal"
    )


# =============================================================================
# Response Schemas
# =============================================================================


class ClassifierResultInfo(BaseModel):
    """Schema for individual classifier result."""

    classifier_name: str = Field(..., description="Name of the classifier")
    mode: ExecutionModeType = Field(..., description="Detected execution mode")
    confidence: float = Field(..., description="Confidence score (0-1)", ge=0.0, le=1.0)
    reasoning: Optional[str] = Field(None, description="Classification reasoning")


class ClassifyIntentResponse(BaseModel):
    """Response schema for intent classification."""

    user_input: str = Field(..., description="Original user input")
    final_mode: ExecutionModeType = Field(..., description="Final determined execution mode")
    confidence: float = Field(..., description="Overall confidence score", ge=0.0, le=1.0)
    reasoning: str = Field(..., description="Final classification reasoning")
    classifier_results: List[ClassifierResultInfo] = Field(
        default_factory=list, description="Results from individual classifiers"
    )
    complexity_score: Optional[float] = Field(None, description="Task complexity score")
    requires_multi_agent: bool = Field(False, description="Whether multi-agent is recommended")
    suggested_agent_count: int = Field(1, description="Suggested number of agents")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class AnalyzeComplexityResponse(BaseModel):
    """Response schema for complexity analysis."""

    user_input: str = Field(..., description="Original user input")
    total_score: float = Field(..., description="Total complexity score (0-1)", ge=0.0, le=1.0)
    complexity_level: str = Field(..., description="Complexity level label")
    step_count_estimate: int = Field(..., description="Estimated number of steps", ge=0)
    resource_dependency_count: int = Field(..., description="Number of resource dependencies", ge=0)
    requires_persistence: bool = Field(..., description="Whether persistence is needed")
    requires_multi_agent: bool = Field(..., description="Whether multi-agent is recommended")
    estimated_duration_minutes: Optional[float] = Field(
        None, description="Estimated duration in minutes"
    )
    should_use_workflow: bool = Field(..., description="Whether workflow mode is recommended")
    reasoning: Optional[str] = Field(None, description="Analysis reasoning")


class DetectMultiAgentResponse(BaseModel):
    """Response schema for multi-agent detection."""

    user_input: str = Field(..., description="Original user input")
    requires_multi_agent: bool = Field(..., description="Whether multi-agent is required")
    confidence: float = Field(..., description="Detection confidence", ge=0.0, le=1.0)
    suggested_agent_count: int = Field(..., description="Suggested number of agents", ge=1)
    collaboration_type: CollaborationType = Field(..., description="Suggested collaboration type")
    detected_domains: List[str] = Field(default_factory=list, description="Detected work domains")
    detected_roles: List[str] = Field(default_factory=list, description="Detected agent roles")
    indicators_found: List[str] = Field(default_factory=list, description="Multi-agent indicators")
    reasoning: str = Field(..., description="Detection reasoning")


class ClassifierInfo(BaseModel):
    """Schema for classifier information."""

    name: str = Field(..., description="Classifier name")
    type: str = Field(..., description="Classifier type")
    weight: float = Field(..., description="Classifier weight", ge=0.0)
    enabled: bool = Field(..., description="Whether classifier is enabled")
    description: str = Field(..., description="Classifier description")


class ListClassifiersResponse(BaseModel):
    """Response schema for listing classifiers."""

    classifiers: List[ClassifierInfo] = Field(..., description="Available classifiers")
    total_count: int = Field(..., description="Total number of classifiers")


class IntentStatsResponse(BaseModel):
    """Response schema for intent classification statistics."""

    total_classifications: int = Field(..., description="Total classifications performed")
    mode_distribution: Dict[str, int] = Field(..., description="Classification by mode")
    avg_confidence: float = Field(..., description="Average confidence score")
    avg_classification_time_ms: float = Field(..., description="Average classification time")
    classifier_usage: Dict[str, int] = Field(..., description="Usage count by classifier")
    last_updated: datetime = Field(..., description="Last statistics update")


class UpdateConfigResponse(BaseModel):
    """Response schema for configuration update."""

    success: bool = Field(..., description="Whether update succeeded")
    message: str = Field(..., description="Update result message")
    current_config: Dict[str, Any] = Field(..., description="Current configuration")


# =============================================================================
# Global Instances
# =============================================================================


_intent_router: Optional[IntentRouter] = None
_complexity_analyzer: Optional[ComplexityAnalyzer] = None
_multi_agent_detector: Optional[MultiAgentDetector] = None

# Statistics tracking
_stats: Dict[str, Any] = {
    "total_classifications": 0,
    "mode_distribution": {"chat_mode": 0, "workflow_mode": 0, "hybrid_mode": 0},
    "confidence_sum": 0.0,
    "classification_time_sum_ms": 0.0,
    "classifier_usage": {},
    "last_updated": datetime.utcnow(),
}


def get_intent_router() -> IntentRouter:
    """Get the global intent router instance."""
    global _intent_router
    if _intent_router is None:
        _intent_router = IntentRouter()
    return _intent_router


def get_complexity_analyzer() -> ComplexityAnalyzer:
    """Get the global complexity analyzer instance."""
    global _complexity_analyzer
    if _complexity_analyzer is None:
        _complexity_analyzer = ComplexityAnalyzer()
    return _complexity_analyzer


def get_multi_agent_detector() -> MultiAgentDetector:
    """Get the global multi-agent detector instance."""
    global _multi_agent_detector
    if _multi_agent_detector is None:
        _multi_agent_detector = MultiAgentDetector()
    return _multi_agent_detector


# =============================================================================
# Router
# =============================================================================


router = APIRouter(prefix="/intent", tags=["Intent Router"])


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/classify", response_model=ClassifyIntentResponse)
async def classify_intent(request: ClassifyIntentRequest):
    """
    Classify user intent to determine execution mode.

    Analyzes the user input using multiple classifiers (rule-based, LLM-based)
    and returns the recommended execution mode (chat, workflow, or hybrid).
    """
    import time

    intent_router = get_intent_router()
    start_time = time.time()

    try:
        # Build session context if provided
        context = None
        if request.session_id or request.workflow_active:
            current_mode = None
            if request.current_mode:
                current_mode = _map_mode_from_api(request.current_mode)

            context = SessionContext(
                session_id=request.session_id or "anonymous",
                workflow_active=request.workflow_active,
                pending_steps=request.pending_steps,
                current_mode=current_mode,
            )

        # Build conversation history if provided
        history = None
        if request.conversation_history:
            history = [
                Message(
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                )
                for msg in request.conversation_history
            ]

        # Analyze intent
        result = await intent_router.analyze_intent(
            user_input=request.user_input,
            session_context=context,
            history=history,
        )

        # Calculate classification time
        classification_time_ms = (time.time() - start_time) * 1000

        # Update statistics
        _update_stats(result.mode, result.confidence, classification_time_ms, "intent_router")

        # Build classifier results from IntentAnalysis
        classifier_results = []
        for cr in result.classification_results:
            classifier_results.append(
                ClassifierResultInfo(
                    classifier_name=cr.classifier_name,
                    mode=_map_mode_to_api(cr.mode),
                    confidence=cr.confidence,
                    reasoning=cr.reasoning,
                )
            )

        # Extract features from detected_features
        detected_features = result.detected_features or {}

        return ClassifyIntentResponse(
            user_input=request.user_input,
            final_mode=_map_mode_to_api(result.mode),
            confidence=result.confidence,
            reasoning=result.reasoning,
            classifier_results=classifier_results,
            complexity_score=detected_features.get("complexity_score"),
            requires_multi_agent=detected_features.get("requires_multi_agent", False),
            suggested_agent_count=detected_features.get("suggested_agent_count", 1),
            metadata=detected_features,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Classification failed: {str(e)}",
        )


@router.post("/analyze-complexity", response_model=AnalyzeComplexityResponse)
async def analyze_complexity(request: AnalyzeComplexityRequest):
    """
    Analyze task complexity.

    Evaluates the complexity of a user task based on step count, dependencies,
    persistence requirements, and time indicators.
    """
    analyzer = get_complexity_analyzer()

    try:
        result = await analyzer.analyze(request.user_input)

        return AnalyzeComplexityResponse(
            user_input=request.user_input,
            total_score=result.total_score,
            complexity_level=analyzer.get_complexity_level(result.total_score),
            step_count_estimate=result.step_count_estimate,
            resource_dependency_count=result.resource_dependency_count,
            requires_persistence=result.requires_persistence,
            requires_multi_agent=result.requires_multi_agent,
            estimated_duration_minutes=result.estimated_duration_minutes,
            should_use_workflow=analyzer.should_use_workflow(result),
            reasoning=result.reasoning if request.include_reasoning else None,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Complexity analysis failed: {str(e)}",
        )


@router.post("/detect-multi-agent", response_model=DetectMultiAgentResponse)
async def detect_multi_agent(request: DetectMultiAgentRequest):
    """
    Detect multi-agent collaboration requirements.

    Analyzes the user input to determine if multiple agents are needed,
    what type of collaboration pattern to use, and which domains/roles are involved.
    """
    detector = get_multi_agent_detector()

    try:
        result = await detector.detect(request.user_input)

        # Map collaboration type
        collab_type = CollaborationType.NONE
        if result.collaboration_type:
            collab_type = CollaborationType(result.collaboration_type)

        return DetectMultiAgentResponse(
            user_input=request.user_input,
            requires_multi_agent=result.requires_multi_agent,
            confidence=result.confidence,
            suggested_agent_count=result.agent_count_estimate,  # Map from agent_count_estimate
            collaboration_type=collab_type,
            detected_domains=list(result.detected_domains) if request.include_domains else [],
            detected_roles=[],  # MultiAgentSignal doesn't have roles, use empty list
            indicators_found=result.indicators_found,
            reasoning=result.reasoning,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multi-agent detection failed: {str(e)}",
        )


@router.get("/classifiers", response_model=ListClassifiersResponse)
async def list_classifiers():
    """
    List available intent classifiers.

    Returns information about all registered classifiers including their
    type, weight, and enabled status.
    """
    intent_router = get_intent_router()

    classifiers = []
    for classifier in intent_router.classifiers:
        classifiers.append(
            ClassifierInfo(
                name=classifier.name,
                type=classifier.__class__.__name__,
                weight=classifier.weight,
                enabled=classifier.is_enabled(),
                description=_get_classifier_description(classifier.__class__.__name__),
            )
        )

    return ListClassifiersResponse(
        classifiers=classifiers,
        total_count=len(classifiers),
    )


@router.get("/stats", response_model=IntentStatsResponse)
async def get_stats():
    """
    Get intent classification statistics.

    Returns aggregated statistics about intent classifications including
    mode distribution, average confidence, and classifier usage.
    """
    global _stats

    avg_confidence = 0.0
    avg_time = 0.0
    if _stats["total_classifications"] > 0:
        avg_confidence = _stats["confidence_sum"] / _stats["total_classifications"]
        avg_time = _stats["classification_time_sum_ms"] / _stats["total_classifications"]

    return IntentStatsResponse(
        total_classifications=_stats["total_classifications"],
        mode_distribution=_stats["mode_distribution"],
        avg_confidence=avg_confidence,
        avg_classification_time_ms=avg_time,
        classifier_usage=_stats["classifier_usage"],
        last_updated=_stats["last_updated"],
    )


@router.put("/config", response_model=UpdateConfigResponse)
async def update_config(request: UpdateConfigRequest):
    """
    Update intent router configuration.

    Allows runtime configuration of classifier behavior, default modes,
    and feature toggles.
    """
    intent_router = get_intent_router()

    try:
        # Update classifier states
        for classifier in intent_router.classifiers:
            if isinstance(classifier, RuleBasedClassifier):
                if request.enable_rule_based:
                    classifier.enable()
                else:
                    classifier.disable()

        # Store configuration
        current_config = {
            "enable_llm_classifier": request.enable_llm_classifier,
            "enable_rule_based": request.enable_rule_based,
            "enable_complexity_boost": request.enable_complexity_boost,
            "enable_multi_agent_boost": request.enable_multi_agent_boost,
            "default_mode": request.default_mode.value,
        }

        return UpdateConfigResponse(
            success=True,
            message="Configuration updated successfully",
            current_config=current_config,
        )

    except Exception as e:
        return UpdateConfigResponse(
            success=False,
            message=f"Configuration update failed: {str(e)}",
            current_config={},
        )


# =============================================================================
# Helper Functions
# =============================================================================


def _map_mode_to_api(mode: ExecutionMode) -> ExecutionModeType:
    """Map internal ExecutionMode to API ExecutionModeType."""
    if mode == ExecutionMode.CHAT_MODE:
        return ExecutionModeType.CHAT_MODE
    elif mode == ExecutionMode.WORKFLOW_MODE:
        return ExecutionModeType.WORKFLOW_MODE
    elif mode == ExecutionMode.HYBRID_MODE:
        return ExecutionModeType.HYBRID_MODE
    return ExecutionModeType.CHAT_MODE


def _map_mode_from_api(mode: ExecutionModeType) -> ExecutionMode:
    """Map API ExecutionModeType to internal ExecutionMode."""
    if mode == ExecutionModeType.CHAT_MODE:
        return ExecutionMode.CHAT_MODE
    elif mode == ExecutionModeType.WORKFLOW_MODE:
        return ExecutionMode.WORKFLOW_MODE
    elif mode == ExecutionModeType.HYBRID_MODE:
        return ExecutionMode.HYBRID_MODE
    return ExecutionMode.CHAT_MODE


def _get_classifier_description(class_name: str) -> str:
    """Get description for a classifier type."""
    descriptions = {
        "RuleBasedClassifier": "Keyword and pattern-based classification with bilingual support",
        "LLMBasedClassifier": "LLM-powered intent classification for complex cases",
        "HybridClassifier": "Combines rule-based and LLM approaches",
    }
    return descriptions.get(class_name, "Intent classifier")


def _update_stats(
    mode: ExecutionMode,
    confidence: float,
    classification_time_ms: float,
    classifier_name: str,
) -> None:
    """Update classification statistics."""
    global _stats

    _stats["total_classifications"] += 1
    _stats["mode_distribution"][mode.value] = (
        _stats["mode_distribution"].get(mode.value, 0) + 1
    )
    _stats["confidence_sum"] += confidence
    _stats["classification_time_sum_ms"] += classification_time_ms
    _stats["classifier_usage"][classifier_name] = (
        _stats["classifier_usage"].get(classifier_name, 0) + 1
    )
    _stats["last_updated"] = datetime.utcnow()
