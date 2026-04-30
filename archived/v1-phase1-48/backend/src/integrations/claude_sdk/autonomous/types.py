# =============================================================================
# IPA Platform - Claude Autonomous Planning Engine Types
# =============================================================================
# Sprint 79: S79-1 - Claude 自主規劃引擎 (13 pts)
#
# This module defines the data types for the autonomous planning engine,
# including plan structures, step definitions, and result types.
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class EventSeverity(str, Enum):
    """Event severity levels for IT incidents."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventComplexity(str, Enum):
    """Event complexity levels affecting budget_tokens allocation."""

    SIMPLE = "simple"  # 4096 tokens - e.g., restart service
    MODERATE = "moderate"  # 8192 tokens - e.g., config change
    COMPLEX = "complex"  # 16000 tokens - e.g., multi-system failure
    CRITICAL = "critical"  # 32000 tokens - e.g., security incident


class PlanStatus(str, Enum):
    """Status of an autonomous plan."""

    PENDING = "pending"  # Plan created, not yet analyzed
    ANALYZING = "analyzing"  # Analysis in progress
    PLANNED = "planned"  # Plan generated, awaiting execution
    EXECUTING = "executing"  # Plan is being executed
    VERIFYING = "verifying"  # Execution complete, verifying results
    COMPLETED = "completed"  # Plan successfully completed
    FAILED = "failed"  # Plan failed
    CANCELLED = "cancelled"  # Plan was cancelled


class StepStatus(str, Enum):
    """Status of a plan step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class RiskLevel(str, Enum):
    """Risk level assessment for a plan."""

    LOW = "low"  # No impact expected
    MEDIUM = "medium"  # Minor impact possible
    HIGH = "high"  # Significant impact possible
    CRITICAL = "critical"  # Major impact expected, requires approval


@dataclass
class EventContext:
    """Context information for an IT event."""

    event_id: str
    event_type: str
    description: str
    severity: EventSeverity
    source_system: Optional[str] = None
    affected_services: List[str] = field(default_factory=list)
    related_events: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "description": self.description,
            "severity": self.severity.value,
            "source_system": self.source_system,
            "affected_services": self.affected_services,
            "related_events": self.related_events,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


@dataclass
class AnalysisResult:
    """Result of event analysis phase."""

    event_id: str
    complexity: EventComplexity
    root_cause_hypothesis: str
    affected_components: List[str]
    recommended_actions: List[str]
    historical_similar_events: List[str] = field(default_factory=list)
    confidence_score: float = 0.0  # 0.0 to 1.0
    analysis_reasoning: str = ""
    budget_tokens_recommended: int = 8192

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "complexity": self.complexity.value,
            "root_cause_hypothesis": self.root_cause_hypothesis,
            "affected_components": self.affected_components,
            "recommended_actions": self.recommended_actions,
            "historical_similar_events": self.historical_similar_events,
            "confidence_score": self.confidence_score,
            "analysis_reasoning": self.analysis_reasoning,
            "budget_tokens_recommended": self.budget_tokens_recommended,
        }


@dataclass
class PlanStep:
    """A single step in an autonomous plan."""

    step_number: int
    action: str
    description: str
    tool_or_workflow: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    expected_outcome: str = ""
    fallback_action: Optional[str] = None
    estimated_duration_seconds: int = 60
    requires_approval: bool = False
    status: StepStatus = StepStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_number": self.step_number,
            "action": self.action,
            "description": self.description,
            "tool_or_workflow": self.tool_or_workflow,
            "parameters": self.parameters,
            "expected_outcome": self.expected_outcome,
            "fallback_action": self.fallback_action,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "requires_approval": self.requires_approval,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class AutonomousPlan:
    """An autonomous plan for handling an IT event."""

    id: str
    event_id: str
    event_context: EventContext
    complexity: EventComplexity
    analysis: Optional[AnalysisResult] = None
    steps: List[PlanStep] = field(default_factory=list)
    estimated_duration_seconds: int = 0
    risk_level: RiskLevel = RiskLevel.MEDIUM
    status: PlanStatus = PlanStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    thinking_output: Optional[str] = None  # Extended Thinking output
    verification_result: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "event_id": self.event_id,
            "event_context": self.event_context.to_dict(),
            "complexity": self.complexity.value,
            "analysis": self.analysis.to_dict() if self.analysis else None,
            "steps": [step.to_dict() for step in self.steps],
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "risk_level": self.risk_level.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "thinking_output": self.thinking_output,
            "verification_result": self.verification_result,
        }


@dataclass
class VerificationResult:
    """Result of plan execution verification."""

    plan_id: str
    success: bool
    expected_outcomes_met: List[str]
    expected_outcomes_failed: List[str]
    actual_results: Dict[str, Any]
    quality_score: float  # 0.0 to 1.0
    lessons_learned: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "plan_id": self.plan_id,
            "success": self.success,
            "expected_outcomes_met": self.expected_outcomes_met,
            "expected_outcomes_failed": self.expected_outcomes_failed,
            "actual_results": self.actual_results,
            "quality_score": self.quality_score,
            "lessons_learned": self.lessons_learned,
            "recommendations": self.recommendations,
        }


# Budget tokens mapping for Extended Thinking
COMPLEXITY_BUDGET_TOKENS: Dict[EventComplexity, int] = {
    EventComplexity.SIMPLE: 4096,
    EventComplexity.MODERATE: 8192,
    EventComplexity.COMPLEX: 16000,
    EventComplexity.CRITICAL: 32000,
}


def get_budget_tokens(complexity: EventComplexity) -> int:
    """Get recommended budget_tokens for a complexity level."""
    return COMPLEXITY_BUDGET_TOKENS.get(complexity, 8192)
