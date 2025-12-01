# =============================================================================
# IPA Platform - Few-shot Learning Service
# =============================================================================
# Sprint 4: Developer Experience - Few-shot Learning Mechanism
#
# Service for managing learning cases and building few-shot prompts:
#   - Recording human corrections to AI outputs
#   - Finding similar cases using text similarity
#   - Building enhanced prompts with examples
#   - Case approval workflow
#   - Learning statistics
#
# Author: IPA Platform Team
# Created: 2025-11-30
# =============================================================================

import logging
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4


logger = logging.getLogger(__name__)


class CaseStatus(str, Enum):
    """Learning case status."""

    PENDING = "pending"  # Awaiting review
    APPROVED = "approved"  # Approved for use
    REJECTED = "rejected"  # Rejected, not suitable
    ARCHIVED = "archived"  # No longer in active use


@dataclass
class LearningCase:
    """
    Learning case representing a human correction.

    Records an instance where human feedback improved or
    corrected an AI-generated output.
    """

    id: UUID
    execution_id: Optional[UUID]
    scenario: str
    original_input: str
    original_output: str
    corrected_output: str
    feedback: str
    status: CaseStatus = CaseStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    usage_count: int = 0
    effectiveness_score: float = 0.0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def approve(self, approved_by: Optional[str] = None) -> None:
        """Mark case as approved."""
        self.status = CaseStatus.APPROVED
        self.approved_at = datetime.utcnow()
        self.approved_by = approved_by

    def reject(self, reason: str) -> None:
        """Mark case as rejected."""
        self.status = CaseStatus.REJECTED
        self.rejection_reason = reason

    def archive(self) -> None:
        """Archive the case."""
        self.status = CaseStatus.ARCHIVED

    def increment_usage(self) -> None:
        """Increment usage counter."""
        self.usage_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "execution_id": str(self.execution_id) if self.execution_id else None,
            "scenario": self.scenario,
            "original_input": self.original_input,
            "original_output": self.original_output,
            "corrected_output": self.corrected_output,
            "feedback": self.feedback,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "approved_by": self.approved_by,
            "rejection_reason": self.rejection_reason,
            "usage_count": self.usage_count,
            "effectiveness_score": self.effectiveness_score,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class LearningStatistics:
    """Learning service statistics."""

    total_cases: int = 0
    approved_cases: int = 0
    pending_cases: int = 0
    rejected_cases: int = 0
    total_usage: int = 0
    by_scenario: Dict[str, int] = field(default_factory=dict)
    avg_effectiveness: float = 0.0


class LearningError(Exception):
    """Learning service error."""

    pass


class LearningService:
    """
    Few-shot Learning Service.

    Manages learning cases for improving AI responses
    through human corrections and examples.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.6,
        max_examples: int = 5,
    ):
        """
        Initialize learning service.

        Args:
            similarity_threshold: Minimum similarity score for case retrieval
            max_examples: Maximum examples in few-shot prompt
        """
        self._cases: Dict[UUID, LearningCase] = {}
        self._similarity_threshold = similarity_threshold
        self._max_examples = max_examples

        # Event handlers
        self._on_case_created: List[Callable] = []
        self._on_case_approved: List[Callable] = []

    # =========================================================================
    # Case Management
    # =========================================================================

    def record_correction(
        self,
        scenario: str,
        original_input: str,
        original_output: str,
        corrected_output: str,
        feedback: str,
        execution_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LearningCase:
        """
        Record a human correction.

        Args:
            scenario: Business scenario (e.g., "it_triage", "customer_service")
            original_input: The original input text
            original_output: The AI's original output
            corrected_output: The human-corrected output
            feedback: Human feedback explaining the correction
            execution_id: Optional execution ID for tracing
            tags: Optional tags for categorization
            metadata: Optional additional metadata

        Returns:
            Created learning case
        """
        case = LearningCase(
            id=uuid4(),
            execution_id=execution_id,
            scenario=scenario,
            original_input=original_input,
            original_output=original_output,
            corrected_output=corrected_output,
            feedback=feedback,
            tags=tags or [],
            metadata=metadata or {},
        )

        self._cases[case.id] = case

        # Notify handlers
        for handler in self._on_case_created:
            try:
                handler(case)
            except Exception as e:
                logger.error(f"Case created handler error: {e}")

        logger.info(f"Recorded learning case {case.id} for scenario {scenario}")

        return case

    def get_case(self, case_id: UUID) -> Optional[LearningCase]:
        """Get case by ID."""
        return self._cases.get(case_id)

    def list_cases(
        self,
        scenario: Optional[str] = None,
        status: Optional[CaseStatus] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[LearningCase]:
        """
        List cases with optional filtering.

        Args:
            scenario: Filter by scenario
            status: Filter by status
            tags: Filter by tags (any match)
            limit: Maximum results

        Returns:
            List of matching cases
        """
        cases = list(self._cases.values())

        if scenario:
            cases = [c for c in cases if c.scenario == scenario]

        if status:
            cases = [c for c in cases if c.status == status]

        if tags:
            cases = [c for c in cases if any(t in c.tags for t in tags)]

        # Sort by created_at descending
        cases.sort(key=lambda c: c.created_at, reverse=True)

        return cases[:limit]

    def delete_case(self, case_id: UUID) -> bool:
        """Delete a case."""
        if case_id in self._cases:
            del self._cases[case_id]
            return True
        return False

    # =========================================================================
    # Case Approval
    # =========================================================================

    def approve_case(
        self,
        case_id: UUID,
        approved_by: Optional[str] = None,
    ) -> Optional[LearningCase]:
        """
        Approve a learning case for use.

        Args:
            case_id: Case to approve
            approved_by: Approver identifier

        Returns:
            Updated case or None if not found
        """
        case = self._cases.get(case_id)
        if not case:
            return None

        case.approve(approved_by)

        # Notify handlers
        for handler in self._on_case_approved:
            try:
                handler(case)
            except Exception as e:
                logger.error(f"Case approved handler error: {e}")

        logger.info(f"Approved learning case {case_id}")

        return case

    def reject_case(
        self,
        case_id: UUID,
        reason: str,
    ) -> Optional[LearningCase]:
        """
        Reject a learning case.

        Args:
            case_id: Case to reject
            reason: Rejection reason

        Returns:
            Updated case or None if not found
        """
        case = self._cases.get(case_id)
        if not case:
            return None

        case.reject(reason)
        logger.info(f"Rejected learning case {case_id}: {reason}")

        return case

    def bulk_approve(
        self,
        case_ids: List[UUID],
        approved_by: Optional[str] = None,
    ) -> int:
        """Approve multiple cases. Returns count of approved."""
        approved = 0
        for case_id in case_ids:
            if self.approve_case(case_id, approved_by):
                approved += 1
        return approved

    # =========================================================================
    # Similarity Search
    # =========================================================================

    def get_similar_cases(
        self,
        scenario: str,
        input_text: str,
        limit: Optional[int] = None,
        approved_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Find similar learning cases for few-shot prompting.

        Uses text similarity to find relevant examples.

        Args:
            scenario: Scenario to search within
            input_text: Input text to match against
            limit: Maximum results (default: max_examples)
            approved_only: Only return approved cases

        Returns:
            List of cases with similarity scores
        """
        if limit is None:
            limit = self._max_examples

        # Get cases for scenario
        cases = [c for c in self._cases.values() if c.scenario == scenario]

        if approved_only:
            cases = [c for c in cases if c.status == CaseStatus.APPROVED]

        # Calculate similarity scores
        results = []
        for case in cases:
            similarity = self._calculate_similarity(input_text, case.original_input)

            if similarity >= self._similarity_threshold:
                results.append({
                    "case": case,
                    "similarity": similarity,
                })

        # Sort by similarity descending
        results.sort(key=lambda x: x["similarity"], reverse=True)

        # Limit results
        results = results[:limit]

        # Update usage counts
        for result in results:
            result["case"].increment_usage()

        return results

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate text similarity using SequenceMatcher.

        For MVP, uses difflib. Production should use embeddings.
        """
        if not text1 or not text2:
            return 0.0

        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    # =========================================================================
    # Few-shot Prompt Building
    # =========================================================================

    def build_few_shot_prompt(
        self,
        base_prompt: str,
        scenario: str,
        input_text: str,
        example_format: str = "standard",
    ) -> str:
        """
        Build a few-shot prompt with similar examples.

        Args:
            base_prompt: The base system prompt
            scenario: Scenario to find examples for
            input_text: Current input text
            example_format: Format style ("standard", "chat", "structured")

        Returns:
            Enhanced prompt with examples
        """
        # Get similar cases
        similar = self.get_similar_cases(
            scenario=scenario,
            input_text=input_text,
        )

        if not similar:
            return base_prompt

        # Build examples section
        examples = self._format_examples(similar, example_format)

        # Construct enhanced prompt
        enhanced_prompt = f"""{base_prompt}

## Learning Examples

The following are examples of correct responses based on human feedback:

{examples}

---

Now, please respond to the current input following the patterns shown above."""

        return enhanced_prompt

    def _format_examples(
        self,
        similar_cases: List[Dict[str, Any]],
        format_style: str,
    ) -> str:
        """Format examples based on style."""
        if format_style == "chat":
            return self._format_chat_examples(similar_cases)
        elif format_style == "structured":
            return self._format_structured_examples(similar_cases)
        else:
            return self._format_standard_examples(similar_cases)

    def _format_standard_examples(
        self,
        similar_cases: List[Dict[str, Any]],
    ) -> str:
        """Standard example format."""
        examples = []
        for i, item in enumerate(similar_cases, 1):
            case = item["case"]
            examples.append(
                f"### Example {i}\n"
                f"**Input:** {case.original_input}\n"
                f"**Correct Response:** {case.corrected_output}"
            )
        return "\n\n".join(examples)

    def _format_chat_examples(
        self,
        similar_cases: List[Dict[str, Any]],
    ) -> str:
        """Chat-style example format."""
        examples = []
        for item in similar_cases:
            case = item["case"]
            examples.append(
                f"User: {case.original_input}\n"
                f"Assistant: {case.corrected_output}"
            )
        return "\n\n".join(examples)

    def _format_structured_examples(
        self,
        similar_cases: List[Dict[str, Any]],
    ) -> str:
        """Structured example format with JSON."""
        import json

        examples = []
        for i, item in enumerate(similar_cases, 1):
            case = item["case"]
            example = {
                "input": case.original_input,
                "output": case.corrected_output,
                "similarity": round(item["similarity"], 3),
            }
            examples.append(f"Example {i}:\n```json\n{json.dumps(example, indent=2, ensure_ascii=False)}\n```")
        return "\n\n".join(examples)

    # =========================================================================
    # Effectiveness Tracking
    # =========================================================================

    def record_effectiveness(
        self,
        case_id: UUID,
        was_helpful: bool,
        score: Optional[float] = None,
    ) -> Optional[LearningCase]:
        """
        Record whether a case was helpful in improving output.

        Args:
            case_id: Case that was used
            was_helpful: Whether it improved the result
            score: Optional effectiveness score (0-1)

        Returns:
            Updated case or None if not found
        """
        case = self._cases.get(case_id)
        if not case:
            return None

        # Update effectiveness score (running average)
        if score is not None:
            current_total = case.effectiveness_score * case.usage_count
            case.effectiveness_score = (current_total + score) / (case.usage_count + 1)
        elif was_helpful:
            current_total = case.effectiveness_score * case.usage_count
            case.effectiveness_score = (current_total + 1.0) / (case.usage_count + 1)

        return case

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> LearningStatistics:
        """Get learning service statistics."""
        stats = LearningStatistics()

        stats.total_cases = len(self._cases)

        total_effectiveness = 0.0
        effectiveness_count = 0

        for case in self._cases.values():
            # Status counts
            if case.status == CaseStatus.APPROVED:
                stats.approved_cases += 1
            elif case.status == CaseStatus.PENDING:
                stats.pending_cases += 1
            elif case.status == CaseStatus.REJECTED:
                stats.rejected_cases += 1

            # Usage
            stats.total_usage += case.usage_count

            # By scenario
            stats.by_scenario[case.scenario] = (
                stats.by_scenario.get(case.scenario, 0) + 1
            )

            # Effectiveness
            if case.usage_count > 0:
                total_effectiveness += case.effectiveness_score
                effectiveness_count += 1

        if effectiveness_count > 0:
            stats.avg_effectiveness = total_effectiveness / effectiveness_count

        return stats

    def get_scenario_statistics(self, scenario: str) -> Dict[str, Any]:
        """Get statistics for a specific scenario."""
        cases = [c for c in self._cases.values() if c.scenario == scenario]

        approved = sum(1 for c in cases if c.status == CaseStatus.APPROVED)
        total_usage = sum(c.usage_count for c in cases)
        avg_effectiveness = 0.0

        used_cases = [c for c in cases if c.usage_count > 0]
        if used_cases:
            avg_effectiveness = sum(c.effectiveness_score for c in used_cases) / len(used_cases)

        return {
            "scenario": scenario,
            "total_cases": len(cases),
            "approved_cases": approved,
            "total_usage": total_usage,
            "avg_effectiveness": avg_effectiveness,
        }

    # =========================================================================
    # Event Handlers
    # =========================================================================

    def on_case_created(self, handler: Callable) -> None:
        """Register handler for case creation events."""
        self._on_case_created.append(handler)

    def on_case_approved(self, handler: Callable) -> None:
        """Register handler for case approval events."""
        self._on_case_approved.append(handler)

    # =========================================================================
    # Maintenance
    # =========================================================================

    def clear_cases(self) -> int:
        """Clear all cases. Returns count cleared."""
        count = len(self._cases)
        self._cases.clear()
        return count

    def archive_old_cases(
        self,
        days: int = 90,
        min_usage: int = 0,
    ) -> int:
        """
        Archive cases older than specified days with low usage.

        Args:
            days: Age threshold
            min_usage: Minimum usage to keep active

        Returns:
            Count of archived cases
        """
        from datetime import timedelta

        threshold = datetime.utcnow() - timedelta(days=days)
        archived = 0

        for case in self._cases.values():
            if case.status != CaseStatus.ARCHIVED:
                if case.created_at < threshold and case.usage_count <= min_usage:
                    case.archive()
                    archived += 1

        return archived
