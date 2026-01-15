"""
Core Data Models for Intent Router

Defines the fundamental data structures for the three-layer routing system:
- ITIntentCategory: ITIL-based intent classification
- CompletenessInfo: Information completeness assessment
- RoutingDecision: Final routing decision with metadata
- PatternMatchResult: Result from pattern matching layer

Sprint 91: Pattern Matcher + Rule Definition (Phase 28)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ITIntentCategory(Enum):
    """
    IT Service Management intent categories based on ITIL framework.

    Categories:
    - INCIDENT: Unplanned interruption or degradation of service
    - REQUEST: Formal request for service or information
    - CHANGE: Request for modification to IT infrastructure
    - QUERY: General inquiry or information request
    - UNKNOWN: Cannot be classified with sufficient confidence
    """
    INCIDENT = "incident"
    REQUEST = "request"
    CHANGE = "change"
    QUERY = "query"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str) -> "ITIntentCategory":
        """Convert string to ITIntentCategory enum."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.UNKNOWN


class RiskLevel(Enum):
    """
    Risk level classification for routing decisions.

    Levels:
    - CRITICAL: Immediate attention required, business impact
    - HIGH: Urgent, significant impact
    - MEDIUM: Standard priority
    - LOW: Can be scheduled
    """
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @classmethod
    def from_string(cls, value: str) -> "RiskLevel":
        """Convert string to RiskLevel enum."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.MEDIUM


class WorkflowType(Enum):
    """
    Workflow type for handling different intents.

    Types:
    - MAGENTIC: Multi-agent orchestration for complex tasks
    - HANDOFF: Human handoff for ambiguous cases
    - CONCURRENT: Parallel processing workflow
    - SEQUENTIAL: Sequential step-by-step workflow
    - SIMPLE: Direct single-agent response
    """
    MAGENTIC = "magentic"
    HANDOFF = "handoff"
    CONCURRENT = "concurrent"
    SEQUENTIAL = "sequential"
    SIMPLE = "simple"

    @classmethod
    def from_string(cls, value: str) -> "WorkflowType":
        """Convert string to WorkflowType enum."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.SIMPLE


@dataclass
class CompletenessInfo:
    """
    Information completeness assessment for routing decisions.

    Attributes:
        is_complete: Whether all required information is present
        missing_fields: List of missing required fields
        optional_missing: List of missing optional fields
        completeness_score: Score from 0.0 to 1.0
        suggestions: Suggestions for gathering missing information
    """
    is_complete: bool = True
    missing_fields: List[str] = field(default_factory=list)
    optional_missing: List[str] = field(default_factory=list)
    completeness_score: float = 1.0
    suggestions: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate completeness score range."""
        if not 0.0 <= self.completeness_score <= 1.0:
            raise ValueError("completeness_score must be between 0.0 and 1.0")


@dataclass
class PatternMatchResult:
    """
    Result from the pattern matching layer.

    Attributes:
        matched: Whether a pattern was matched
        intent_category: Detected intent category
        sub_intent: More specific intent classification
        confidence: Confidence score (0.0 to 1.0)
        rule_id: ID of the matched rule
        workflow_type: Suggested workflow type
        risk_level: Assessed risk level
        matched_pattern: The actual pattern that matched
        match_position: Position in input where match occurred
    """
    matched: bool
    intent_category: Optional[ITIntentCategory] = None
    sub_intent: Optional[str] = None
    confidence: float = 0.0
    rule_id: Optional[str] = None
    workflow_type: Optional[WorkflowType] = None
    risk_level: Optional[RiskLevel] = None
    matched_pattern: Optional[str] = None
    match_position: Optional[int] = None

    def __post_init__(self):
        """Validate confidence score range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

    @classmethod
    def no_match(cls) -> "PatternMatchResult":
        """Factory method for creating a no-match result."""
        return cls(matched=False, confidence=0.0)


@dataclass
class RoutingDecision:
    """
    Final routing decision with complete metadata.

    Attributes:
        intent_category: Primary intent classification
        sub_intent: More specific intent type
        confidence: Overall confidence score
        workflow_type: Recommended workflow
        risk_level: Assessed risk level
        completeness: Information completeness assessment
        routing_layer: Which layer made the decision (pattern/llm/human)
        rule_id: ID of rule used (if pattern matched)
        reasoning: Explanation for the routing decision
        metadata: Additional context and debugging info
        timestamp: When the decision was made
        processing_time_ms: Time taken to make decision
    """
    intent_category: ITIntentCategory
    sub_intent: Optional[str] = None
    confidence: float = 0.0
    workflow_type: WorkflowType = WorkflowType.SIMPLE
    risk_level: RiskLevel = RiskLevel.MEDIUM
    completeness: CompletenessInfo = field(default_factory=CompletenessInfo)
    routing_layer: str = "pattern"
    rule_id: Optional[str] = None
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    processing_time_ms: float = 0.0

    def __post_init__(self):
        """Validate confidence score range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "intent_category": self.intent_category.value,
            "sub_intent": self.sub_intent,
            "confidence": self.confidence,
            "workflow_type": self.workflow_type.value,
            "risk_level": self.risk_level.value,
            "completeness": {
                "is_complete": self.completeness.is_complete,
                "missing_fields": self.completeness.missing_fields,
                "optional_missing": self.completeness.optional_missing,
                "completeness_score": self.completeness.completeness_score,
                "suggestions": self.completeness.suggestions,
            },
            "routing_layer": self.routing_layer,
            "rule_id": self.rule_id,
            "reasoning": self.reasoning,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "processing_time_ms": self.processing_time_ms,
        }

    @classmethod
    def from_pattern_match(
        cls,
        result: PatternMatchResult,
        processing_time_ms: float = 0.0,
    ) -> "RoutingDecision":
        """
        Factory method to create RoutingDecision from PatternMatchResult.

        Args:
            result: The pattern match result
            processing_time_ms: Processing time in milliseconds

        Returns:
            RoutingDecision instance
        """
        if not result.matched:
            return cls(
                intent_category=ITIntentCategory.UNKNOWN,
                confidence=0.0,
                routing_layer="pattern",
                reasoning="No pattern matched",
                processing_time_ms=processing_time_ms,
            )

        return cls(
            intent_category=result.intent_category or ITIntentCategory.UNKNOWN,
            sub_intent=result.sub_intent,
            confidence=result.confidence,
            workflow_type=result.workflow_type or WorkflowType.SIMPLE,
            risk_level=result.risk_level or RiskLevel.MEDIUM,
            routing_layer="pattern",
            rule_id=result.rule_id,
            reasoning=f"Pattern matched: {result.matched_pattern}",
            metadata={
                "matched_pattern": result.matched_pattern,
                "match_position": result.match_position,
            },
            processing_time_ms=processing_time_ms,
        )


@dataclass
class PatternRule:
    """
    Definition of a pattern matching rule.

    Attributes:
        id: Unique rule identifier
        category: Intent category this rule matches
        sub_intent: More specific intent type
        patterns: List of regex patterns to match
        priority: Rule priority (higher = checked first)
        workflow_type: Suggested workflow type
        risk_level: Default risk level
        description: Human-readable description
        enabled: Whether the rule is active
    """
    id: str
    category: ITIntentCategory
    sub_intent: str
    patterns: List[str]
    priority: int = 100
    workflow_type: WorkflowType = WorkflowType.SIMPLE
    risk_level: RiskLevel = RiskLevel.MEDIUM
    description: str = ""
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "category": self.category.value,
            "sub_intent": self.sub_intent,
            "patterns": self.patterns,
            "priority": self.priority,
            "workflow_type": self.workflow_type.value,
            "risk_level": self.risk_level.value,
            "description": self.description,
            "enabled": self.enabled,
        }


# =============================================================================
# Sprint 92: Semantic Router + LLM Classifier Models
# =============================================================================


@dataclass
class SemanticRouteResult:
    """
    Result from the semantic routing layer.

    Attributes:
        matched: Whether a semantic route was matched above threshold
        intent_category: Detected intent category
        sub_intent: More specific intent classification
        similarity: Similarity score from vector comparison (0.0 to 1.0)
        route_name: Name of the matched semantic route
        metadata: Additional route metadata
    """
    matched: bool
    intent_category: Optional[ITIntentCategory] = None
    sub_intent: Optional[str] = None
    similarity: float = 0.0
    route_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate similarity score range."""
        if not 0.0 <= self.similarity <= 1.0:
            raise ValueError("similarity must be between 0.0 and 1.0")

    @classmethod
    def no_match(cls, similarity: float = 0.0) -> "SemanticRouteResult":
        """Factory method for creating a no-match result."""
        return cls(matched=False, similarity=similarity)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "matched": self.matched,
            "intent_category": self.intent_category.value if self.intent_category else None,
            "sub_intent": self.sub_intent,
            "similarity": self.similarity,
            "route_name": self.route_name,
            "metadata": self.metadata,
        }


@dataclass
class LLMClassificationResult:
    """
    Result from the LLM classification layer.

    Attributes:
        intent_category: Classified intent category
        sub_intent: More specific intent classification
        confidence: Classification confidence score (0.0 to 1.0)
        completeness: Information completeness assessment
        reasoning: LLM's reasoning for the classification
        raw_response: Raw response text from LLM
        model: Model used for classification
        usage: Token usage statistics
    """
    intent_category: ITIntentCategory
    sub_intent: Optional[str] = None
    confidence: float = 0.0
    completeness: CompletenessInfo = field(default_factory=CompletenessInfo)
    reasoning: str = ""
    raw_response: str = ""
    model: str = ""
    usage: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        """Validate confidence score range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "intent_category": self.intent_category.value,
            "sub_intent": self.sub_intent,
            "confidence": self.confidence,
            "completeness": {
                "is_complete": self.completeness.is_complete,
                "missing_fields": self.completeness.missing_fields,
                "optional_missing": self.completeness.optional_missing,
                "completeness_score": self.completeness.completeness_score,
                "suggestions": self.completeness.suggestions,
            },
            "reasoning": self.reasoning,
            "model": self.model,
            "usage": self.usage,
        }

    @classmethod
    def from_pattern_fallback(
        cls,
        pattern_result: PatternMatchResult,
    ) -> "LLMClassificationResult":
        """
        Create LLMClassificationResult from pattern match as fallback.

        Used when pattern match is sufficient and LLM classification is skipped.
        """
        return cls(
            intent_category=pattern_result.intent_category or ITIntentCategory.UNKNOWN,
            sub_intent=pattern_result.sub_intent,
            confidence=pattern_result.confidence,
            reasoning=f"Classified via pattern match: {pattern_result.matched_pattern}",
        )


@dataclass
class SemanticRoute:
    """
    Definition of a semantic route for vector-based matching.

    Attributes:
        name: Unique route name
        category: Intent category this route maps to
        sub_intent: More specific intent classification
        utterances: Example utterances for this route (used for training)
        description: Human-readable description
        workflow_type: Suggested workflow type
        risk_level: Default risk level
        enabled: Whether the route is active
        metadata: Additional route metadata
    """
    name: str
    category: ITIntentCategory
    sub_intent: str
    utterances: List[str]
    description: str = ""
    workflow_type: WorkflowType = WorkflowType.SIMPLE
    risk_level: RiskLevel = RiskLevel.MEDIUM
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "category": self.category.value,
            "sub_intent": self.sub_intent,
            "utterances": self.utterances,
            "description": self.description,
            "workflow_type": self.workflow_type.value,
            "risk_level": self.risk_level.value,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }
