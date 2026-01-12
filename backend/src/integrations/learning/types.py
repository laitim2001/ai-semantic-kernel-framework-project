# =============================================================================
# IPA Platform - Learning System Types
# =============================================================================
# Sprint 80: S80-1 - Few-shot 學習系統 (8 pts)
#
# This module defines the data types for the Few-shot learning system,
# including cases, learning results, and configuration.
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class CaseOutcome(str, Enum):
    """Outcome of a historical case."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    UNKNOWN = "unknown"


class CaseCategory(str, Enum):
    """Category of case for organization."""

    INCIDENT_RESOLUTION = "incident_resolution"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    SECURITY_RESPONSE = "security_response"
    DEPLOYMENT_ISSUE = "deployment_issue"
    CONFIGURATION_CHANGE = "configuration_change"
    USER_SUPPORT = "user_support"
    SYSTEM_MAINTENANCE = "system_maintenance"
    OTHER = "other"


@dataclass
class CaseMetadata:
    """Metadata for a case."""

    source: str = ""  # Source system (e.g., "servicenow", "jira")
    event_id: Optional[str] = None
    resolution_time_seconds: Optional[int] = None
    resolver_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    custom: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "event_id": self.event_id,
            "resolution_time_seconds": self.resolution_time_seconds,
            "resolver_id": self.resolver_id,
            "tags": self.tags,
            "custom": self.custom,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CaseMetadata":
        """Create from dictionary."""
        return cls(
            source=data.get("source", ""),
            event_id=data.get("event_id"),
            resolution_time_seconds=data.get("resolution_time_seconds"),
            resolver_id=data.get("resolver_id"),
            tags=data.get("tags", []),
            custom=data.get("custom", {}),
        )


@dataclass
class Case:
    """A historical case used for Few-shot learning."""

    id: str
    title: str
    description: str
    category: CaseCategory
    outcome: CaseOutcome
    affected_systems: List[str]
    root_cause: Optional[str] = None
    resolution_steps: List[str] = field(default_factory=list)
    lessons_learned: Optional[str] = None
    quality_score: float = 0.5  # 0.0 to 1.0
    metadata: CaseMetadata = field(default_factory=CaseMetadata)
    embedding: Optional[List[float]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "outcome": self.outcome.value,
            "affected_systems": self.affected_systems,
            "root_cause": self.root_cause,
            "resolution_steps": self.resolution_steps,
            "lessons_learned": self.lessons_learned,
            "quality_score": self.quality_score,
            "metadata": self.metadata.to_dict(),
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Case":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            category=CaseCategory(data.get("category", "other")),
            outcome=CaseOutcome(data.get("outcome", "unknown")),
            affected_systems=data.get("affected_systems", []),
            root_cause=data.get("root_cause"),
            resolution_steps=data.get("resolution_steps", []),
            lessons_learned=data.get("lessons_learned"),
            quality_score=data.get("quality_score", 0.5),
            metadata=CaseMetadata.from_dict(data.get("metadata", {})),
            embedding=data.get("embedding"),
            created_at=datetime.fromisoformat(data["created_at"])
            if isinstance(data.get("created_at"), str)
            else data.get("created_at", datetime.utcnow()),
        )

    def to_example(self) -> str:
        """Convert case to a text example for Few-shot learning."""
        steps = "\n".join([f"  {i+1}. {s}" for i, s in enumerate(self.resolution_steps)])
        return f"""### Case: {self.title}
**Description**: {self.description}
**Affected Systems**: {', '.join(self.affected_systems)}
**Root Cause**: {self.root_cause or 'N/A'}
**Resolution Steps**:
{steps}
**Outcome**: {self.outcome.value}
**Lessons Learned**: {self.lessons_learned or 'N/A'}
"""


@dataclass
class SimilarityResult:
    """Result of similarity calculation."""

    case: Case
    semantic_score: float  # Cosine similarity of embeddings
    structural_score: float  # Jaccard similarity of systems
    combined_score: float  # Weighted combination

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "case": self.case.to_dict(),
            "semantic_score": self.semantic_score,
            "structural_score": self.structural_score,
            "combined_score": self.combined_score,
        }


@dataclass
class LearningResult:
    """Result of Few-shot learning enhancement."""

    original_prompt: str
    enhanced_prompt: str
    cases_used: List[Case]
    enhancement_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_prompt": self.original_prompt,
            "enhanced_prompt": self.enhanced_prompt,
            "cases_used": [c.to_dict() for c in self.cases_used],
            "enhancement_id": self.enhancement_id,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class LearningEffectiveness:
    """Tracking of learning effectiveness."""

    enhancement_id: str
    decision_id: str
    was_successful: bool
    quality_improvement: Optional[float] = None  # -1.0 to 1.0
    feedback: Optional[str] = None
    recorded_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enhancement_id": self.enhancement_id,
            "decision_id": self.decision_id,
            "was_successful": self.was_successful,
            "quality_improvement": self.quality_improvement,
            "feedback": self.feedback,
            "recorded_at": self.recorded_at.isoformat(),
        }


@dataclass
class LearningConfig:
    """Configuration for the Few-shot learning system."""

    # Case selection
    top_k_cases: int = 3
    min_quality_score: float = 0.6
    min_similarity_score: float = 0.5

    # Similarity weights
    semantic_weight: float = 0.7
    structural_weight: float = 0.3

    # Prompt enhancement
    max_examples_in_prompt: int = 3
    include_lessons_learned: bool = True
    include_resolution_steps: bool = True

    # Case library maintenance
    max_cases_per_category: int = 100
    case_expiry_days: int = 365

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "top_k_cases": self.top_k_cases,
            "min_quality_score": self.min_quality_score,
            "min_similarity_score": self.min_similarity_score,
            "semantic_weight": self.semantic_weight,
            "structural_weight": self.structural_weight,
            "max_examples_in_prompt": self.max_examples_in_prompt,
            "include_lessons_learned": self.include_lessons_learned,
            "include_resolution_steps": self.include_resolution_steps,
            "max_cases_per_category": self.max_cases_per_category,
            "case_expiry_days": self.case_expiry_days,
        }


# Default configuration
DEFAULT_LEARNING_CONFIG = LearningConfig()
