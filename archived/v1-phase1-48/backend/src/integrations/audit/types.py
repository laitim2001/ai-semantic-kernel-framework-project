# =============================================================================
# IPA Platform - Decision Audit Types
# =============================================================================
# Sprint 80: S80-2 - 自主決策審計追蹤 (8 pts)
#
# This module defines the data types for decision auditing,
# including audit records, reports, and configuration.
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class DecisionType(str, Enum):
    """Type of decision made."""

    PLAN_GENERATION = "plan_generation"
    STEP_EXECUTION = "step_execution"
    TOOL_SELECTION = "tool_selection"
    FALLBACK_SELECTION = "fallback_selection"
    RISK_ASSESSMENT = "risk_assessment"
    APPROVAL_REQUEST = "approval_request"
    OTHER = "other"


class DecisionOutcome(str, Enum):
    """Outcome of a decision."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    PENDING = "pending"
    CANCELLED = "cancelled"


class QualityRating(str, Enum):
    """Quality rating for a decision."""

    EXCELLENT = "excellent"  # 0.9-1.0
    GOOD = "good"  # 0.7-0.9
    ACCEPTABLE = "acceptable"  # 0.5-0.7
    POOR = "poor"  # 0.3-0.5
    UNACCEPTABLE = "unacceptable"  # 0.0-0.3


@dataclass
class DecisionContext:
    """Context in which a decision was made."""

    event_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    plan_id: Optional[str] = None
    step_number: Optional[int] = None
    input_data: Dict[str, Any] = field(default_factory=dict)
    system_state: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "plan_id": self.plan_id,
            "step_number": self.step_number,
            "input_data": self.input_data,
            "system_state": self.system_state,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DecisionContext":
        """Create from dictionary."""
        return cls(
            event_id=data.get("event_id"),
            session_id=data.get("session_id"),
            user_id=data.get("user_id"),
            plan_id=data.get("plan_id"),
            step_number=data.get("step_number"),
            input_data=data.get("input_data", {}),
            system_state=data.get("system_state", {}),
        )


@dataclass
class ThinkingProcess:
    """Record of the AI's thinking process."""

    raw_thinking: str = ""  # Extended Thinking output
    key_considerations: List[str] = field(default_factory=list)
    assumptions_made: List[str] = field(default_factory=list)
    risks_identified: List[str] = field(default_factory=list)
    budget_tokens_used: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "raw_thinking": self.raw_thinking,
            "key_considerations": self.key_considerations,
            "assumptions_made": self.assumptions_made,
            "risks_identified": self.risks_identified,
            "budget_tokens_used": self.budget_tokens_used,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThinkingProcess":
        """Create from dictionary."""
        return cls(
            raw_thinking=data.get("raw_thinking", ""),
            key_considerations=data.get("key_considerations", []),
            assumptions_made=data.get("assumptions_made", []),
            risks_identified=data.get("risks_identified", []),
            budget_tokens_used=data.get("budget_tokens_used"),
        )


@dataclass
class AlternativeConsidered:
    """An alternative that was considered but not selected."""

    description: str
    reason_not_selected: str
    estimated_risk: float = 0.5  # 0.0 to 1.0
    estimated_success_probability: float = 0.5  # 0.0 to 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "description": self.description,
            "reason_not_selected": self.reason_not_selected,
            "estimated_risk": self.estimated_risk,
            "estimated_success_probability": self.estimated_success_probability,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AlternativeConsidered":
        """Create from dictionary."""
        return cls(
            description=data["description"],
            reason_not_selected=data["reason_not_selected"],
            estimated_risk=data.get("estimated_risk", 0.5),
            estimated_success_probability=data.get("estimated_success_probability", 0.5),
        )


@dataclass
class DecisionAudit:
    """Complete audit record for a decision."""

    decision_id: str
    decision_type: DecisionType
    timestamp: datetime
    context: DecisionContext
    thinking_process: ThinkingProcess
    selected_action: str
    action_details: Dict[str, Any]
    alternatives_considered: List[AlternativeConsidered]
    confidence_score: float  # 0.0 to 1.0
    outcome: DecisionOutcome = DecisionOutcome.PENDING
    outcome_details: Optional[str] = None
    quality_score: Optional[float] = None
    quality_rating: Optional[QualityRating] = None
    feedback: Optional[str] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "decision_id": self.decision_id,
            "decision_type": self.decision_type.value,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context.to_dict(),
            "thinking_process": self.thinking_process.to_dict(),
            "selected_action": self.selected_action,
            "action_details": self.action_details,
            "alternatives_considered": [a.to_dict() for a in self.alternatives_considered],
            "confidence_score": self.confidence_score,
            "outcome": self.outcome.value,
            "outcome_details": self.outcome_details,
            "quality_score": self.quality_score,
            "quality_rating": self.quality_rating.value if self.quality_rating else None,
            "feedback": self.feedback,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DecisionAudit":
        """Create from dictionary."""
        return cls(
            decision_id=data["decision_id"],
            decision_type=DecisionType(data["decision_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if isinstance(data["timestamp"], str)
            else data["timestamp"],
            context=DecisionContext.from_dict(data.get("context", {})),
            thinking_process=ThinkingProcess.from_dict(data.get("thinking_process", {})),
            selected_action=data["selected_action"],
            action_details=data.get("action_details", {}),
            alternatives_considered=[
                AlternativeConsidered.from_dict(a)
                for a in data.get("alternatives_considered", [])
            ],
            confidence_score=data.get("confidence_score", 0.5),
            outcome=DecisionOutcome(data.get("outcome", "pending")),
            outcome_details=data.get("outcome_details"),
            quality_score=data.get("quality_score"),
            quality_rating=QualityRating(data["quality_rating"])
            if data.get("quality_rating")
            else None,
            feedback=data.get("feedback"),
            updated_at=datetime.fromisoformat(data["updated_at"])
            if data.get("updated_at")
            else None,
        )


@dataclass
class AuditReport:
    """Explanatory report for a decision."""

    decision_id: str
    title: str
    summary: str
    detailed_explanation: str
    key_factors: List[str]
    risk_analysis: str
    recommendations: List[str]
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "decision_id": self.decision_id,
            "title": self.title,
            "summary": self.summary,
            "detailed_explanation": self.detailed_explanation,
            "key_factors": self.key_factors,
            "risk_analysis": self.risk_analysis,
            "recommendations": self.recommendations,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class AuditQuery:
    """Query parameters for searching audit records."""

    user_id: Optional[str] = None
    session_id: Optional[str] = None
    event_id: Optional[str] = None
    plan_id: Optional[str] = None
    decision_type: Optional[DecisionType] = None
    outcome: Optional[DecisionOutcome] = None
    min_confidence: Optional[float] = None
    max_confidence: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 50
    offset: int = 0


@dataclass
class AuditConfig:
    """Configuration for the audit system."""

    # Storage
    enable_redis_cache: bool = True
    cache_ttl_seconds: int = 3600
    archive_after_days: int = 90

    # Logging
    log_thinking_process: bool = True
    log_alternatives: bool = True
    max_thinking_length: int = 10000

    # Quality scoring
    auto_score_outcomes: bool = True
    require_manual_review_below: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enable_redis_cache": self.enable_redis_cache,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "archive_after_days": self.archive_after_days,
            "log_thinking_process": self.log_thinking_process,
            "log_alternatives": self.log_alternatives,
            "max_thinking_length": self.max_thinking_length,
            "auto_score_outcomes": self.auto_score_outcomes,
            "require_manual_review_below": self.require_manual_review_below,
        }


# Default configuration
DEFAULT_AUDIT_CONFIG = AuditConfig()
