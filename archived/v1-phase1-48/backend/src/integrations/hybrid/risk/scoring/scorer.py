# =============================================================================
# IPA Platform - Risk Scorer
# =============================================================================
# Sprint 55: Risk Assessment Engine Core
#
# Calculates composite risk scores from multiple risk factors.
# Uses configurable weights and normalization strategies.
#
# Dependencies:
#   - RiskFactor, RiskFactorType, RiskConfig (models.py)
# =============================================================================

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..models import RiskConfig, RiskFactor, RiskFactorType, RiskLevel


class ScoringStrategy(Enum):
    """
    Strategy for combining multiple risk factors.

    - WEIGHTED_AVERAGE: Standard weighted average
    - MAX_WEIGHTED: Use the maximum weighted score
    - HYBRID: Combination of average and max
    """
    WEIGHTED_AVERAGE = "weighted_average"
    MAX_WEIGHTED = "max_weighted"
    HYBRID = "hybrid"


@dataclass
class ScoringResult:
    """
    Result of risk score calculation.

    Attributes:
        score: Final calculated score (0.0 - 1.0)
        level: Determined risk level
        strategy_used: Scoring strategy that was applied
        factor_contributions: Breakdown of each factor's contribution
        normalization_applied: Whether normalization was needed
    """
    score: float
    level: RiskLevel
    strategy_used: ScoringStrategy
    factor_contributions: Dict[str, float] = field(default_factory=dict)
    normalization_applied: bool = False


class RiskScorer:
    """
    Calculates composite risk scores from multiple risk factors.

    Supports multiple scoring strategies and configurable weights.
    Normalizes scores when weights don't sum to 1.0.

    Example:
        >>> scorer = RiskScorer(config)
        >>> factors = [
        ...     RiskFactor(RiskFactorType.OPERATION, 0.6, 0.5, "High-risk tool"),
        ...     RiskFactor(RiskFactorType.CONTEXT, 0.3, 0.3, "Dev environment"),
        ... ]
        >>> result = scorer.calculate(factors)
        >>> print(f"Score: {result.score}, Level: {result.level}")
    """

    def __init__(
        self,
        config: Optional[RiskConfig] = None,
        strategy: ScoringStrategy = ScoringStrategy.HYBRID,
    ):
        """
        Initialize the risk scorer.

        Args:
            config: Risk configuration with thresholds and weights
            strategy: Scoring strategy to use
        """
        self.config = config or RiskConfig()
        self.strategy = strategy

    def calculate(
        self,
        factors: List[RiskFactor],
        override_strategy: Optional[ScoringStrategy] = None,
    ) -> ScoringResult:
        """
        Calculate composite risk score from factors.

        Args:
            factors: List of risk factors to combine
            override_strategy: Optional strategy override

        Returns:
            ScoringResult with score, level, and breakdown
        """
        if not factors:
            return ScoringResult(
                score=0.0,
                level=RiskLevel.LOW,
                strategy_used=self.strategy,
                factor_contributions={},
                normalization_applied=False,
            )

        strategy = override_strategy or self.strategy

        # Calculate contributions for each factor
        contributions: Dict[str, float] = {}
        for i, factor in enumerate(factors):
            key = f"{factor.factor_type.value}_{i}"
            contributions[key] = factor.weighted_score()

        # Apply scoring strategy
        if strategy == ScoringStrategy.WEIGHTED_AVERAGE:
            score = self._weighted_average(factors)
        elif strategy == ScoringStrategy.MAX_WEIGHTED:
            score = self._max_weighted(factors)
        else:  # HYBRID
            score = self._hybrid_score(factors)

        # Normalize if needed
        normalization_applied = False
        if score > 1.0:
            score = 1.0
            normalization_applied = True

        # Determine risk level
        level = RiskLevel.from_score(score, self.config)

        return ScoringResult(
            score=round(score, 4),
            level=level,
            strategy_used=strategy,
            factor_contributions=contributions,
            normalization_applied=normalization_applied,
        )

    def _weighted_average(self, factors: List[RiskFactor]) -> float:
        """
        Calculate weighted average of risk factors.

        Normalizes by total weight to handle weights that don't sum to 1.0.
        """
        if not factors:
            return 0.0

        total_weighted = sum(f.weighted_score() for f in factors)
        total_weight = sum(f.weight for f in factors)

        if total_weight == 0:
            return 0.0

        return total_weighted / total_weight

    def _max_weighted(self, factors: List[RiskFactor]) -> float:
        """
        Return the maximum weighted score among factors.

        Useful when any single high-risk factor should dominate.
        """
        if not factors:
            return 0.0

        return max(f.weighted_score() for f in factors)

    def _hybrid_score(self, factors: List[RiskFactor]) -> float:
        """
        Calculate hybrid score combining average and max.

        Uses 70% weighted average + 30% max weighted.
        This balances overall risk profile with peak risk factors.
        """
        if not factors:
            return 0.0

        avg_score = self._weighted_average(factors)
        max_score = self._max_weighted(factors)

        # Blend: 70% average, 30% max
        return (avg_score * 0.7) + (max_score * 0.3)

    def calculate_by_type(
        self,
        factors: List[RiskFactor],
    ) -> Dict[RiskFactorType, ScoringResult]:
        """
        Calculate separate scores for each factor type.

        Useful for detailed risk breakdown by category.

        Args:
            factors: List of risk factors

        Returns:
            Dictionary mapping factor types to their scores
        """
        results: Dict[RiskFactorType, ScoringResult] = {}

        # Group factors by type
        by_type: Dict[RiskFactorType, List[RiskFactor]] = {}
        for factor in factors:
            if factor.factor_type not in by_type:
                by_type[factor.factor_type] = []
            by_type[factor.factor_type].append(factor)

        # Calculate score for each type
        for factor_type, type_factors in by_type.items():
            results[factor_type] = self.calculate(type_factors)

        return results

    def adjust_for_context(
        self,
        base_score: float,
        environment: str = "development",
        user_trust_level: Optional[float] = None,
    ) -> float:
        """
        Adjust risk score based on context.

        Higher risk in production, lower for trusted users.

        Args:
            base_score: Original calculated score
            environment: Execution environment
            user_trust_level: User trust score (0.0 - 1.0)

        Returns:
            Adjusted score
        """
        adjusted = base_score

        # Environment multiplier
        env_multipliers = {
            "development": 0.8,
            "staging": 1.0,
            "production": 1.3,
        }
        env_mult = env_multipliers.get(environment.lower(), 1.0)
        adjusted *= env_mult

        # User trust adjustment
        if user_trust_level is not None:
            # Higher trust = lower risk (up to 20% reduction)
            trust_adjustment = 1.0 - (user_trust_level * 0.2)
            adjusted *= trust_adjustment

        # Clamp to valid range
        return max(0.0, min(1.0, adjusted))

    def aggregate_session_risk(
        self,
        assessments: List[Dict[str, Any]],
        window_seconds: int = 300,
    ) -> ScoringResult:
        """
        Aggregate risk across multiple assessments in a session.

        Considers cumulative risk and escalation patterns.

        Args:
            assessments: List of previous assessment results
            window_seconds: Time window to consider

        Returns:
            Aggregated session risk score
        """
        if not assessments:
            return ScoringResult(
                score=0.0,
                level=RiskLevel.LOW,
                strategy_used=ScoringStrategy.WEIGHTED_AVERAGE,
            )

        # Extract scores with recency weighting
        scores = []
        for i, assessment in enumerate(assessments):
            score = assessment.get("overall_score", 0.0)
            # More recent assessments get higher weight
            recency_weight = (i + 1) / len(assessments)
            scores.append(score * recency_weight)

        # Calculate weighted average
        if scores:
            avg_score = sum(scores) / sum(
                (i + 1) / len(scores) for i in range(len(scores))
            )
        else:
            avg_score = 0.0

        # Detect escalation pattern
        if len(assessments) >= 3:
            recent_scores = [a.get("overall_score", 0.0) for a in assessments[-3:]]
            if all(
                recent_scores[i] < recent_scores[i + 1]
                for i in range(len(recent_scores) - 1)
            ):
                # Escalating pattern - increase risk
                avg_score = min(1.0, avg_score * 1.2)

        level = RiskLevel.from_score(avg_score, self.config)

        return ScoringResult(
            score=round(avg_score, 4),
            level=level,
            strategy_used=ScoringStrategy.WEIGHTED_AVERAGE,
            factor_contributions={"session_average": avg_score},
        )
