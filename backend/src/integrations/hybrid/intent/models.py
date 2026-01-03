# =============================================================================
# IPA Platform - Intent Analysis Models
# =============================================================================
# Phase 13: Hybrid Core Architecture
# Sprint 52: Intent Router & Mode Detection
#
# Data models for intent analysis and execution mode detection.
#
# Key Models:
#   - ExecutionMode: Enum for execution modes
#   - IntentAnalysis: Analysis result with mode and confidence
#   - SessionContext: Session context for analysis
#   - ClassificationResult: Result from individual classifiers
#
# Dependencies:
#   - pydantic (BaseModel, Field)
# =============================================================================

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExecutionMode(str, Enum):
    """
    Execution mode enum for the hybrid architecture.

    Modes:
        WORKFLOW_MODE: Multi-step workflows with MAF orchestration
        CHAT_MODE: Simple conversational interactions with Claude
        HYBRID_MODE: Dynamic mode that can switch between workflow and chat
    """

    WORKFLOW_MODE = "workflow"
    CHAT_MODE = "chat"
    HYBRID_MODE = "hybrid"


class SuggestedFramework(str, Enum):
    """
    Suggested framework for execution.

    Frameworks:
        MAF: Microsoft Agent Framework - for complex multi-agent workflows
        CLAUDE: Claude SDK - for conversational AI tasks
        HYBRID: Combination of both frameworks
    """

    MAF = "maf"
    CLAUDE = "claude"
    HYBRID = "hybrid"


class ClassificationResult(BaseModel):
    """
    Result from an individual classifier.

    Attributes:
        mode: Detected execution mode
        confidence: Confidence score (0.0 to 1.0)
        reasoning: Explanation for the classification
        classifier_name: Name of the classifier that produced this result
        metadata: Additional metadata from the classifier
    """

    mode: ExecutionMode
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    classifier_name: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntentAnalysis(BaseModel):
    """
    Complete intent analysis result.

    This is the main output from the IntentRouter, containing the detected
    execution mode, confidence level, reasoning, and suggested framework.

    Attributes:
        mode: Detected execution mode
        confidence: Overall confidence score (0.0 to 1.0)
        reasoning: Human-readable explanation for the mode selection
        suggested_framework: Recommended framework for execution
        classification_results: Results from individual classifiers
        detected_features: Features detected in the input
        analysis_time_ms: Time taken for analysis in milliseconds
        created_at: Timestamp when analysis was created

    Example:
        >>> analysis = IntentAnalysis(
        ...     mode=ExecutionMode.WORKFLOW_MODE,
        ...     confidence=0.85,
        ...     reasoning="Multi-step task with agent collaboration detected",
        ...     suggested_framework=SuggestedFramework.MAF
        ... )
    """

    mode: ExecutionMode
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    suggested_framework: SuggestedFramework = SuggestedFramework.CLAUDE
    classification_results: List[ClassificationResult] = Field(default_factory=list)
    detected_features: Dict[str, Any] = Field(default_factory=dict)
    analysis_time_ms: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class SessionContext(BaseModel):
    """
    Session context for intent analysis.

    Provides additional context from the current session to help
    the intent router make more accurate decisions.

    Attributes:
        session_id: Unique session identifier
        current_mode: Current execution mode (if any)
        message_count: Number of messages in the session
        tool_call_count: Number of tool calls made
        workflow_active: Whether a workflow is currently active
        pending_steps: Number of pending workflow steps
        context_variables: Additional context variables
        conversation_summary: Optional summary of the conversation
        last_activity: Timestamp of last activity

    Example:
        >>> context = SessionContext(
        ...     session_id="sess_123",
        ...     current_mode=ExecutionMode.CHAT_MODE,
        ...     message_count=5
        ... )
    """

    session_id: Optional[str] = None
    current_mode: Optional[ExecutionMode] = None
    message_count: int = 0
    tool_call_count: int = 0
    workflow_active: bool = False
    pending_steps: int = 0
    context_variables: Dict[str, Any] = Field(default_factory=dict)
    conversation_summary: Optional[str] = None
    last_activity: Optional[datetime] = None


class Message(BaseModel):
    """
    Message model for conversation history.

    Attributes:
        role: Message role (user, assistant, system)
        content: Message content
        timestamp: When the message was created
        tool_calls: List of tool calls in this message
    """

    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)


class ComplexityScore(BaseModel):
    """
    Complexity analysis score.

    Attributes:
        total_score: Overall complexity score (0.0 to 1.0)
        step_count_estimate: Estimated number of steps
        resource_dependency_count: Number of resource dependencies
        estimated_duration_minutes: Estimated execution duration (None if unknown)
        requires_persistence: Whether state persistence is needed
        requires_multi_agent: Whether multiple agents are needed
        reasoning: Explanation of the complexity analysis
    """

    total_score: float = Field(ge=0.0, le=1.0)
    step_count_estimate: int = 0
    resource_dependency_count: int = 0
    estimated_duration_minutes: Optional[float] = None
    requires_persistence: bool = False
    requires_multi_agent: bool = False
    reasoning: str = ""


class MultiAgentAnalysis(BaseModel):
    """
    Multi-agent requirement analysis.

    Attributes:
        requires_multi_agent: Whether multiple agents are needed
        detected_agent_types: Types of agents detected as needed
        collaboration_pattern: Detected collaboration pattern
        confidence: Confidence in the analysis
        reasoning: Explanation of the analysis
    """

    requires_multi_agent: bool = False
    detected_agent_types: List[str] = Field(default_factory=list)
    collaboration_pattern: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    reasoning: str = ""
