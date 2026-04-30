# =============================================================================
# IPA Platform - Risk Assessment Models
# =============================================================================
# Sprint 55: Risk Assessment Engine Core
#
# Core data models for risk assessment:
# - RiskLevel: LOW, MEDIUM, HIGH, CRITICAL
# - RiskFactor: Individual risk factor with score and weight
# - RiskAssessment: Complete assessment result
# - RiskConfig: Configurable thresholds and weights
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class RiskLevel(Enum):
    """
    Risk level classification for operations.

    Determines the approval requirement level:
    - LOW: Auto-approved, minimal risk
    - MEDIUM: Auto-approved with logging
    - HIGH: Requires human approval
    - CRITICAL: Requires immediate attention and approval
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def from_score(cls, score: float, config: "RiskConfig") -> "RiskLevel":
        """Determine risk level from score using config thresholds."""
        if score >= config.critical_threshold:
            return cls.CRITICAL
        elif score >= config.high_threshold:
            return cls.HIGH
        elif score >= config.medium_threshold:
            return cls.MEDIUM
        return cls.LOW

    def requires_approval(self) -> bool:
        """Check if this risk level requires human approval."""
        return self in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    def __lt__(self, other: "RiskLevel") -> bool:
        """Enable comparison for risk level ordering."""
        order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        return order.index(self) < order.index(other)


class RiskFactorType(Enum):
    """
    Types of risk factors considered in assessment.

    Categorizes different sources of risk:
    - OPERATION: Tool/action type risk
    - CONTEXT: Session and behavioral context
    - PATTERN: Behavioral patterns and anomalies
    - PATH: File path sensitivity
    - COMMAND: Command execution risk
    - FREQUENCY: Operation frequency anomalies
    - ESCALATION: Risk escalation patterns
    - USER: User trust level risk
    - ENVIRONMENT: Deployment environment risk
    """
    OPERATION = "operation"
    CONTEXT = "context"
    PATTERN = "pattern"
    PATH = "path"
    COMMAND = "command"
    FREQUENCY = "frequency"
    ESCALATION = "escalation"
    USER = "user"
    ENVIRONMENT = "environment"


@dataclass
class RiskFactor:
    """
    Individual risk factor contributing to overall assessment.

    Attributes:
        factor_type: Category of the risk factor
        score: Risk score (0.0 - 1.0)
        weight: Weight in overall calculation (0.0 - 1.0)
        description: Human-readable description of the risk
        source: Source of the risk (tool name, path, command, etc.)
        metadata: Additional context information
    """
    factor_type: RiskFactorType
    score: float
    weight: float
    description: str
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate score and weight bounds."""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"Score must be between 0.0 and 1.0, got {self.score}")
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"Weight must be between 0.0 and 1.0, got {self.weight}")

    def weighted_score(self) -> float:
        """Calculate weighted contribution to overall risk."""
        return self.score * self.weight


@dataclass
class RiskAssessment:
    """
    Complete risk assessment result.

    Represents the outcome of multi-dimensional risk analysis,
    including overall level, contributing factors, and metadata.

    Attributes:
        overall_level: Final risk level classification
        overall_score: Composite risk score (0.0 - 1.0)
        factors: List of contributing risk factors
        requires_approval: Whether human approval is required
        approval_reason: Reason for requiring approval (if applicable)
        assessment_time: When the assessment was performed
        session_id: Optional session identifier
        metadata: Additional assessment context
    """
    overall_level: RiskLevel
    overall_score: float
    factors: List[RiskFactor]
    requires_approval: bool
    approval_reason: Optional[str] = None
    assessment_time: datetime = field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate overall score bounds."""
        if not 0.0 <= self.overall_score <= 1.0:
            raise ValueError(
                f"Overall score must be between 0.0 and 1.0, got {self.overall_score}"
            )

    def get_factors_by_type(self, factor_type: RiskFactorType) -> List[RiskFactor]:
        """Get all factors of a specific type."""
        return [f for f in self.factors if f.factor_type == factor_type]

    def get_highest_factor(self) -> Optional[RiskFactor]:
        """Get the factor with the highest weighted score."""
        if not self.factors:
            return None
        return max(self.factors, key=lambda f: f.weighted_score())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "overall_level": self.overall_level.value,
            "overall_score": self.overall_score,
            "factors": [
                {
                    "factor_type": f.factor_type.value,
                    "score": f.score,
                    "weight": f.weight,
                    "description": f.description,
                    "source": f.source,
                    "metadata": f.metadata,
                }
                for f in self.factors
            ],
            "requires_approval": self.requires_approval,
            "approval_reason": self.approval_reason,
            "assessment_time": self.assessment_time.isoformat(),
            "session_id": self.session_id,
            "metadata": self.metadata,
        }


@dataclass
class RiskConfig:
    """
    Configuration for risk assessment thresholds and weights.

    Allows customization of risk level boundaries and factor weights
    for different environments or use cases.

    Attributes:
        critical_threshold: Score threshold for CRITICAL level (default: 0.9)
        high_threshold: Score threshold for HIGH level (default: 0.7)
        medium_threshold: Score threshold for MEDIUM level (default: 0.4)
        operation_weight: Weight for operation-based risk factors
        context_weight: Weight for context-based risk factors
        pattern_weight: Weight for pattern-based risk factors
        auto_approve_low: Auto-approve LOW risk operations
        auto_approve_medium: Auto-approve MEDIUM risk operations
        max_auto_approve_score: Maximum score for auto-approval
        enable_pattern_detection: Enable behavioral pattern detection
        pattern_window_seconds: Time window for pattern detection
    """
    # Level thresholds
    critical_threshold: float = 0.9
    high_threshold: float = 0.7
    medium_threshold: float = 0.4

    # Factor weights (should sum to approximately 1.0)
    operation_weight: float = 0.5
    context_weight: float = 0.3
    pattern_weight: float = 0.2

    # Auto-approval settings
    auto_approve_low: bool = True
    auto_approve_medium: bool = True
    max_auto_approve_score: float = 0.6

    # Pattern detection settings
    enable_pattern_detection: bool = True
    pattern_window_seconds: int = 300  # 5 minutes

    def __post_init__(self) -> None:
        """Validate threshold ordering and bounds."""
        # Validate threshold ordering
        if not (
            self.medium_threshold < self.high_threshold < self.critical_threshold
        ):
            raise ValueError(
                "Thresholds must be in order: medium < high < critical"
            )
        # Validate threshold bounds
        for name, value in [
            ("critical_threshold", self.critical_threshold),
            ("high_threshold", self.high_threshold),
            ("medium_threshold", self.medium_threshold),
        ]:
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0.0 and 1.0")
        # Validate weight bounds
        for name, value in [
            ("operation_weight", self.operation_weight),
            ("context_weight", self.context_weight),
            ("pattern_weight", self.pattern_weight),
        ]:
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0.0 and 1.0")

    def should_auto_approve(self, level: RiskLevel, score: float) -> bool:
        """Determine if a risk level/score combination should be auto-approved."""
        if score > self.max_auto_approve_score:
            return False
        if level == RiskLevel.LOW:
            return self.auto_approve_low
        if level == RiskLevel.MEDIUM:
            return self.auto_approve_medium
        return False  # HIGH and CRITICAL always require approval


@dataclass
class OperationContext:
    """
    Context information for a single operation being assessed.

    Provides all necessary information for risk assessment
    of a tool operation or command.

    Attributes:
        tool_name: Name of the tool being used
        operation_type: Type of operation (read, write, execute, etc.)
        target_paths: File/resource paths being accessed
        command: Command string (for Bash operations)
        arguments: Tool arguments/parameters
        session_id: Current session identifier
        user_id: Optional user identifier
        environment: Execution environment (development, staging, production)
        timestamp: When the operation was requested
        previous_operations: Recent operations in this session
    """
    tool_name: str
    operation_type: str = "unknown"
    target_paths: List[str] = field(default_factory=list)
    command: Optional[str] = None
    arguments: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    environment: str = "development"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    previous_operations: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "tool_name": self.tool_name,
            "operation_type": self.operation_type,
            "target_paths": self.target_paths,
            "command": self.command,
            "arguments": self.arguments,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "environment": self.environment,
            "timestamp": self.timestamp.isoformat(),
            "previous_operations_count": len(self.previous_operations),
        }
