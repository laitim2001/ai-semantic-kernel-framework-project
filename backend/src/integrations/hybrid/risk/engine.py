# =============================================================================
# IPA Platform - Risk Assessment Engine
# =============================================================================
# Sprint 55: Risk Assessment Engine Core
#
# Main engine for multi-dimensional risk assessment.
# Coordinates analyzers, evaluators, and scorers to produce
# comprehensive risk assessments for hybrid orchestration.
#
# Dependencies:
#   - RiskScorer (scoring/scorer.py)
#   - Models (models.py)
# =============================================================================

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Protocol, TYPE_CHECKING

from .models import (
    OperationContext,
    RiskAssessment,
    RiskConfig,
    RiskFactor,
    RiskFactorType,
    RiskLevel,
)
from .scoring.scorer import RiskScorer, ScoringResult, ScoringStrategy

if TYPE_CHECKING:
    from ..context.bridge import ContextBridge

logger = logging.getLogger(__name__)


class AnalyzerProtocol(Protocol):
    """Protocol for risk analyzers."""

    def analyze(self, context: OperationContext) -> List[RiskFactor]:
        """Analyze operation context and return risk factors."""
        ...


@dataclass
class EngineMetrics:
    """
    Metrics for tracking engine performance.

    Attributes:
        total_assessments: Total number of assessments performed
        assessments_by_level: Count by risk level
        average_score: Running average of scores
        approval_rate: Rate of operations requiring approval
        average_latency_ms: Average assessment time
    """
    total_assessments: int = 0
    assessments_by_level: Dict[str, int] = field(default_factory=lambda: {
        "low": 0, "medium": 0, "high": 0, "critical": 0
    })
    total_score: float = 0.0
    approvals_required: int = 0
    total_latency_ms: float = 0.0

    @property
    def average_score(self) -> float:
        """Calculate average risk score."""
        if self.total_assessments == 0:
            return 0.0
        return self.total_score / self.total_assessments

    @property
    def approval_rate(self) -> float:
        """Calculate rate of operations requiring approval."""
        if self.total_assessments == 0:
            return 0.0
        return self.approvals_required / self.total_assessments

    @property
    def average_latency_ms(self) -> float:
        """Calculate average assessment latency."""
        if self.total_assessments == 0:
            return 0.0
        return self.total_latency_ms / self.total_assessments


@dataclass
class AssessmentHistory:
    """
    Tracks recent assessments for pattern detection.

    Maintains a sliding window of assessments for
    detecting escalation patterns and frequency anomalies.
    """
    max_size: int = 100
    entries: List[RiskAssessment] = field(default_factory=list)

    def add(self, assessment: RiskAssessment) -> None:
        """Add assessment to history, maintaining max size."""
        self.entries.append(assessment)
        if len(self.entries) > self.max_size:
            self.entries.pop(0)

    def get_recent(
        self,
        seconds: int = 300,
        session_id: Optional[str] = None,
    ) -> List[RiskAssessment]:
        """Get assessments within time window."""
        cutoff = datetime.utcnow() - timedelta(seconds=seconds)
        recent = [
            e for e in self.entries
            if e.assessment_time >= cutoff
        ]
        if session_id:
            recent = [e for e in recent if e.session_id == session_id]
        return recent

    def clear_session(self, session_id: str) -> int:
        """Clear assessments for a specific session."""
        original_count = len(self.entries)
        self.entries = [
            e for e in self.entries
            if e.session_id != session_id
        ]
        return original_count - len(self.entries)


class RiskAssessmentEngine:
    """
    Main engine for multi-dimensional risk assessment.

    Coordinates multiple analyzers to produce comprehensive
    risk assessments that drive HITL approval decisions.

    Example:
        >>> engine = RiskAssessmentEngine()
        >>> context = OperationContext(
        ...     tool_name="Bash",
        ...     command="rm -rf /tmp/test",
        ... )
        >>> assessment = engine.assess(context)
        >>> if assessment.requires_approval:
        ...     request_human_approval(assessment)
    """

    def __init__(
        self,
        config: Optional[RiskConfig] = None,
        scorer: Optional[RiskScorer] = None,
        analyzers: Optional[List[AnalyzerProtocol]] = None,
    ):
        """
        Initialize the risk assessment engine.

        Args:
            config: Risk configuration with thresholds
            scorer: Custom risk scorer instance
            analyzers: List of risk analyzers to use
        """
        self.config = config or RiskConfig()
        self.scorer = scorer or RiskScorer(self.config)
        self._analyzers: List[AnalyzerProtocol] = analyzers or []
        self._metrics = EngineMetrics()
        self._history = AssessmentHistory()
        self._hooks: Dict[str, List[Callable]] = {
            "pre_assess": [],
            "post_assess": [],
            "on_high_risk": [],
        }
        logger.info(
            f"RiskAssessmentEngine initialized with {len(self._analyzers)} analyzers"
        )

    def register_analyzer(self, analyzer: AnalyzerProtocol) -> None:
        """
        Register a risk analyzer.

        Args:
            analyzer: Analyzer implementing AnalyzerProtocol
        """
        self._analyzers.append(analyzer)
        logger.debug(f"Registered analyzer: {type(analyzer).__name__}")

    def register_hook(
        self,
        hook_type: str,
        callback: Callable,
    ) -> None:
        """
        Register a lifecycle hook.

        Args:
            hook_type: Type of hook (pre_assess, post_assess, on_high_risk)
            callback: Function to call
        """
        if hook_type not in self._hooks:
            raise ValueError(f"Unknown hook type: {hook_type}")
        self._hooks[hook_type].append(callback)

    def assess(
        self,
        context: OperationContext,
        include_history: bool = True,
    ) -> RiskAssessment:
        """
        Perform risk assessment for an operation.

        Coordinates all registered analyzers and produces
        a comprehensive risk assessment.

        Args:
            context: Operation context to assess
            include_history: Whether to consider historical patterns

        Returns:
            Complete risk assessment with level, score, and factors
        """
        start_time = datetime.utcnow()

        # Run pre-assessment hooks
        self._run_hooks("pre_assess", context)

        # Collect risk factors from all analyzers
        all_factors: List[RiskFactor] = []
        for analyzer in self._analyzers:
            try:
                factors = analyzer.analyze(context)
                all_factors.extend(factors)
            except Exception as e:
                logger.error(f"Analyzer {type(analyzer).__name__} failed: {e}")
                # Add error as a risk factor
                all_factors.append(RiskFactor(
                    factor_type=RiskFactorType.PATTERN,
                    score=0.1,
                    weight=0.1,
                    description=f"Analyzer error: {type(analyzer).__name__}",
                    source="engine",
                    metadata={"error": str(e)},
                ))

        # Add base operation risk if no analyzers
        if not all_factors:
            all_factors = self._get_base_factors(context)

        # Consider historical patterns
        if include_history and self.config.enable_pattern_detection:
            history_factors = self._analyze_history(context)
            all_factors.extend(history_factors)

        # Calculate composite score
        scoring_result = self.scorer.calculate(all_factors)

        # Adjust for context
        adjusted_score = self.scorer.adjust_for_context(
            scoring_result.score,
            environment=context.environment,
        )

        # Determine final level and approval requirement
        final_level = RiskLevel.from_score(adjusted_score, self.config)
        requires_approval = final_level.requires_approval()
        approval_reason = self._get_approval_reason(
            final_level, all_factors, context
        ) if requires_approval else None

        # Create assessment
        assessment = RiskAssessment(
            overall_level=final_level,
            overall_score=adjusted_score,
            factors=all_factors,
            requires_approval=requires_approval,
            approval_reason=approval_reason,
            session_id=context.session_id,
            metadata={
                "tool": context.tool_name,
                "environment": context.environment,
                "analyzer_count": len(self._analyzers),
                "factor_count": len(all_factors),
                "scoring_strategy": scoring_result.strategy_used.value,
            },
        )

        # Update history and metrics
        self._history.add(assessment)
        self._update_metrics(assessment, start_time)

        # Run post-assessment hooks
        self._run_hooks("post_assess", assessment)

        # Run high-risk hooks if applicable
        if final_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            self._run_hooks("on_high_risk", assessment)

        logger.info(
            f"Assessment complete: {final_level.value} "
            f"(score={adjusted_score:.3f}, factors={len(all_factors)})"
        )

        return assessment

    def assess_batch(
        self,
        contexts: List[OperationContext],
    ) -> List[RiskAssessment]:
        """
        Assess multiple operations as a batch.

        Useful for evaluating multi-step workflows.

        Args:
            contexts: List of operation contexts

        Returns:
            List of assessments in order
        """
        assessments = []
        cumulative_risk = 0.0

        for i, context in enumerate(contexts):
            assessment = self.assess(context)

            # Increase risk for later operations in batch
            if i > 0:
                batch_factor = RiskFactor(
                    factor_type=RiskFactorType.PATTERN,
                    score=min(0.3, cumulative_risk * 0.1),
                    weight=0.2,
                    description=f"Batch operation {i+1}/{len(contexts)}",
                    source="batch",
                    metadata={"position": i, "total": len(contexts)},
                )
                assessment.factors.append(batch_factor)

            cumulative_risk += assessment.overall_score
            assessments.append(assessment)

        return assessments

    def get_session_risk(
        self,
        session_id: str,
        window_seconds: Optional[int] = None,
    ) -> ScoringResult:
        """
        Get aggregated risk for a session.

        Args:
            session_id: Session identifier
            window_seconds: Time window (uses config default if None)

        Returns:
            Aggregated session risk score
        """
        window = window_seconds or self.config.pattern_window_seconds
        recent = self._history.get_recent(window, session_id)

        if not recent:
            return ScoringResult(
                score=0.0,
                level=RiskLevel.LOW,
                strategy_used=ScoringStrategy.WEIGHTED_AVERAGE,
            )

        assessments = [a.to_dict() for a in recent]
        return self.scorer.aggregate_session_risk(assessments, window)

    def clear_session_history(self, session_id: str) -> int:
        """
        Clear assessment history for a session.

        Args:
            session_id: Session identifier

        Returns:
            Number of entries cleared
        """
        return self._history.clear_session(session_id)

    def get_metrics(self) -> EngineMetrics:
        """Get engine performance metrics."""
        return self._metrics

    def reset_metrics(self) -> None:
        """Reset all engine metrics."""
        self._metrics = EngineMetrics()

    def _get_base_factors(
        self,
        context: OperationContext,
    ) -> List[RiskFactor]:
        """
        Get base risk factors when no analyzers are registered.

        Provides minimal risk assessment based on tool name.
        """
        # Base risk by tool type
        tool_base_risk = {
            "Read": 0.1,
            "Glob": 0.1,
            "Grep": 0.1,
            "Write": 0.4,
            "Edit": 0.4,
            "MultiEdit": 0.5,
            "Bash": 0.6,
            "Task": 0.3,
        }

        base_score = tool_base_risk.get(context.tool_name, 0.3)

        return [
            RiskFactor(
                factor_type=RiskFactorType.OPERATION,
                score=base_score,
                weight=self.config.operation_weight,
                description=f"Base risk for {context.tool_name}",
                source=context.tool_name,
            )
        ]

    def _analyze_history(
        self,
        context: OperationContext,
    ) -> List[RiskFactor]:
        """
        Analyze historical patterns for additional risk factors.

        Detects frequency anomalies and escalation patterns.
        """
        factors: List[RiskFactor] = []

        if not context.session_id:
            return factors

        recent = self._history.get_recent(
            self.config.pattern_window_seconds,
            context.session_id,
        )

        if not recent:
            return factors

        # Frequency analysis
        if len(recent) > 10:
            factors.append(RiskFactor(
                factor_type=RiskFactorType.FREQUENCY,
                score=min(0.5, len(recent) * 0.03),
                weight=0.15,
                description=f"High operation frequency: {len(recent)} in window",
                source="history",
                metadata={"count": len(recent)},
            ))

        # Escalation pattern
        if len(recent) >= 3:
            scores = [a.overall_score for a in recent[-3:]]
            if all(scores[i] < scores[i+1] for i in range(len(scores)-1)):
                factors.append(RiskFactor(
                    factor_type=RiskFactorType.ESCALATION,
                    score=0.4,
                    weight=0.2,
                    description="Risk escalation pattern detected",
                    source="history",
                    metadata={"recent_scores": scores},
                ))

        return factors

    def _get_approval_reason(
        self,
        level: RiskLevel,
        factors: List[RiskFactor],
        context: OperationContext,
    ) -> str:
        """
        Generate human-readable approval reason.

        Creates a clear explanation of why approval is required.
        """
        reasons = []

        if level == RiskLevel.CRITICAL:
            reasons.append(f"Critical risk level ({level.value})")
        else:
            reasons.append(f"High risk level ({level.value})")

        # Add top contributing factors
        sorted_factors = sorted(
            factors,
            key=lambda f: f.weighted_score(),
            reverse=True,
        )[:3]

        for factor in sorted_factors:
            if factor.weighted_score() > 0.1:
                reasons.append(f"- {factor.description}")

        return " | ".join(reasons)

    def _update_metrics(
        self,
        assessment: RiskAssessment,
        start_time: datetime,
    ) -> None:
        """Update engine metrics with assessment results."""
        self._metrics.total_assessments += 1
        self._metrics.assessments_by_level[assessment.overall_level.value] += 1
        self._metrics.total_score += assessment.overall_score
        if assessment.requires_approval:
            self._metrics.approvals_required += 1

        latency = (datetime.utcnow() - start_time).total_seconds() * 1000
        self._metrics.total_latency_ms += latency

    def _run_hooks(self, hook_type: str, data: Any) -> None:
        """Run all hooks of a specific type."""
        for hook in self._hooks.get(hook_type, []):
            try:
                hook(data)
            except Exception as e:
                logger.error(f"Hook {hook_type} failed: {e}")


def create_engine(
    config: Optional[RiskConfig] = None,
    with_default_analyzers: bool = False,
) -> RiskAssessmentEngine:
    """
    Factory function to create a configured RiskAssessmentEngine.

    Args:
        config: Optional custom configuration
        with_default_analyzers: Whether to register default analyzers

    Returns:
        Configured engine instance
    """
    engine = RiskAssessmentEngine(config=config)

    if with_default_analyzers:
        # Analyzers will be added in S55-2 and S55-3
        logger.info("Default analyzers will be registered when available")

    return engine
