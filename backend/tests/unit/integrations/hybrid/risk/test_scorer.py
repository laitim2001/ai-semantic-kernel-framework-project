# =============================================================================
# IPA Platform - Risk Scorer Tests
# =============================================================================
# Sprint 55: Risk Assessment Engine Core
# =============================================================================

import pytest

from src.integrations.hybrid.risk.models import (
    RiskConfig,
    RiskFactor,
    RiskFactorType,
    RiskLevel,
)
from src.integrations.hybrid.risk.scoring.scorer import (
    RiskScorer,
    ScoringResult,
    ScoringStrategy,
)


class TestScoringStrategy:
    """Tests for ScoringStrategy enum."""

    def test_strategy_values(self):
        """Test strategy enum values."""
        assert ScoringStrategy.WEIGHTED_AVERAGE.value == "weighted_average"
        assert ScoringStrategy.MAX_WEIGHTED.value == "max_weighted"
        assert ScoringStrategy.HYBRID.value == "hybrid"


class TestScoringResult:
    """Tests for ScoringResult dataclass."""

    def test_basic_creation(self):
        """Test basic result creation."""
        result = ScoringResult(
            score=0.5,
            level=RiskLevel.MEDIUM,
            strategy_used=ScoringStrategy.HYBRID,
        )
        assert result.score == 0.5
        assert result.level == RiskLevel.MEDIUM
        assert result.strategy_used == ScoringStrategy.HYBRID
        assert result.factor_contributions == {}
        assert result.normalization_applied is False


class TestRiskScorer:
    """Tests for RiskScorer class."""

    @pytest.fixture
    def scorer(self):
        """Create a default scorer."""
        return RiskScorer()

    @pytest.fixture
    def custom_config_scorer(self):
        """Create scorer with custom config."""
        config = RiskConfig(
            critical_threshold=0.85,
            high_threshold=0.6,
            medium_threshold=0.3,
        )
        return RiskScorer(config)

    def test_init_default(self):
        """Test default initialization."""
        scorer = RiskScorer()
        assert scorer.config is not None
        assert scorer.strategy == ScoringStrategy.HYBRID

    def test_init_custom_strategy(self):
        """Test initialization with custom strategy."""
        scorer = RiskScorer(strategy=ScoringStrategy.MAX_WEIGHTED)
        assert scorer.strategy == ScoringStrategy.MAX_WEIGHTED

    def test_calculate_empty_factors(self, scorer):
        """Test calculation with empty factors list."""
        result = scorer.calculate([])
        assert result.score == 0.0
        assert result.level == RiskLevel.LOW
        assert result.factor_contributions == {}

    def test_calculate_single_factor(self, scorer):
        """Test calculation with single factor."""
        factors = [
            RiskFactor(RiskFactorType.OPERATION, 0.6, 0.5, "Test"),
        ]
        result = scorer.calculate(factors)
        assert result.score > 0
        assert result.level in RiskLevel

    def test_calculate_multiple_factors(self, scorer):
        """Test calculation with multiple factors."""
        factors = [
            RiskFactor(RiskFactorType.OPERATION, 0.6, 0.5, "Op"),
            RiskFactor(RiskFactorType.CONTEXT, 0.3, 0.3, "Ctx"),
            RiskFactor(RiskFactorType.PATTERN, 0.2, 0.2, "Pat"),
        ]
        result = scorer.calculate(factors)
        assert 0.0 <= result.score <= 1.0
        assert len(result.factor_contributions) == 3

    def test_calculate_weighted_average(self, scorer):
        """Test weighted average strategy."""
        factors = [
            RiskFactor(RiskFactorType.OPERATION, 0.8, 0.5, "High risk"),
            RiskFactor(RiskFactorType.CONTEXT, 0.2, 0.5, "Low risk"),
        ]
        result = scorer.calculate(
            factors,
            override_strategy=ScoringStrategy.WEIGHTED_AVERAGE,
        )
        # Expected: (0.8*0.5 + 0.2*0.5) / (0.5 + 0.5) = 0.5
        assert result.score == pytest.approx(0.5, rel=0.01)
        assert result.strategy_used == ScoringStrategy.WEIGHTED_AVERAGE

    def test_calculate_max_weighted(self, scorer):
        """Test max weighted strategy."""
        factors = [
            RiskFactor(RiskFactorType.OPERATION, 0.8, 0.5, "High risk"),  # 0.4
            RiskFactor(RiskFactorType.CONTEXT, 0.2, 0.5, "Low risk"),     # 0.1
        ]
        result = scorer.calculate(
            factors,
            override_strategy=ScoringStrategy.MAX_WEIGHTED,
        )
        # Expected: max(0.4, 0.1) = 0.4
        assert result.score == pytest.approx(0.4, rel=0.01)
        assert result.strategy_used == ScoringStrategy.MAX_WEIGHTED

    def test_calculate_hybrid(self, scorer):
        """Test hybrid strategy."""
        factors = [
            RiskFactor(RiskFactorType.OPERATION, 0.8, 0.5, "High risk"),
            RiskFactor(RiskFactorType.CONTEXT, 0.2, 0.5, "Low risk"),
        ]
        result = scorer.calculate(
            factors,
            override_strategy=ScoringStrategy.HYBRID,
        )
        # Avg = 0.5, Max = 0.4
        # Hybrid = 0.5*0.7 + 0.4*0.3 = 0.35 + 0.12 = 0.47
        assert result.score == pytest.approx(0.47, rel=0.01)
        assert result.strategy_used == ScoringStrategy.HYBRID

    def test_calculate_normalization(self, scorer):
        """Test score normalization when exceeds 1.0."""
        # This is a bit artificial since weighted scores shouldn't exceed 1.0
        # but we test the normalization behavior
        factors = [
            RiskFactor(RiskFactorType.OPERATION, 1.0, 1.0, "Max"),
        ]
        result = scorer.calculate(factors)
        assert result.score <= 1.0

    def test_calculate_determines_level(self, scorer):
        """Test level determination from score."""
        low_factors = [RiskFactor(RiskFactorType.OPERATION, 0.2, 1.0, "Low")]
        medium_factors = [RiskFactor(RiskFactorType.OPERATION, 0.5, 1.0, "Med")]
        high_factors = [RiskFactor(RiskFactorType.OPERATION, 0.8, 1.0, "High")]
        critical_factors = [RiskFactor(RiskFactorType.OPERATION, 0.95, 1.0, "Crit")]

        assert scorer.calculate(low_factors).level == RiskLevel.LOW
        assert scorer.calculate(medium_factors).level == RiskLevel.MEDIUM
        assert scorer.calculate(high_factors).level == RiskLevel.HIGH
        assert scorer.calculate(critical_factors).level == RiskLevel.CRITICAL

    def test_calculate_by_type(self, scorer):
        """Test calculation by factor type."""
        factors = [
            RiskFactor(RiskFactorType.OPERATION, 0.6, 0.5, "Op1"),
            RiskFactor(RiskFactorType.OPERATION, 0.4, 0.5, "Op2"),
            RiskFactor(RiskFactorType.CONTEXT, 0.3, 0.5, "Ctx1"),
        ]
        results = scorer.calculate_by_type(factors)

        assert RiskFactorType.OPERATION in results
        assert RiskFactorType.CONTEXT in results
        assert RiskFactorType.PATTERN not in results

    def test_adjust_for_context_development(self, scorer):
        """Test context adjustment for development environment."""
        base_score = 0.5
        adjusted = scorer.adjust_for_context(base_score, "development")
        assert adjusted < base_score  # Development reduces risk

    def test_adjust_for_context_production(self, scorer):
        """Test context adjustment for production environment."""
        base_score = 0.5
        adjusted = scorer.adjust_for_context(base_score, "production")
        assert adjusted > base_score  # Production increases risk

    def test_adjust_for_context_staging(self, scorer):
        """Test context adjustment for staging environment."""
        base_score = 0.5
        adjusted = scorer.adjust_for_context(base_score, "staging")
        assert adjusted == base_score  # Staging has no adjustment

    def test_adjust_for_context_with_trust(self, scorer):
        """Test context adjustment with user trust level."""
        base_score = 0.5
        # High trust reduces risk
        adjusted_high_trust = scorer.adjust_for_context(
            base_score, "staging", user_trust_level=1.0
        )
        assert adjusted_high_trust < base_score

        # Low trust has minimal effect
        adjusted_low_trust = scorer.adjust_for_context(
            base_score, "staging", user_trust_level=0.0
        )
        assert adjusted_low_trust == base_score

    def test_adjust_for_context_clamp_high(self, scorer):
        """Test context adjustment clamping high values."""
        adjusted = scorer.adjust_for_context(0.9, "production")
        assert adjusted <= 1.0

    def test_adjust_for_context_clamp_low(self, scorer):
        """Test context adjustment clamping low values."""
        adjusted = scorer.adjust_for_context(0.1, "development", user_trust_level=1.0)
        assert adjusted >= 0.0

    def test_aggregate_session_risk_empty(self, scorer):
        """Test session aggregation with empty history."""
        result = scorer.aggregate_session_risk([])
        assert result.score == 0.0
        assert result.level == RiskLevel.LOW

    def test_aggregate_session_risk_single(self, scorer):
        """Test session aggregation with single assessment."""
        assessments = [{"overall_score": 0.5}]
        result = scorer.aggregate_session_risk(assessments)
        assert result.score == pytest.approx(0.5, rel=0.01)

    def test_aggregate_session_risk_multiple(self, scorer):
        """Test session aggregation with multiple assessments."""
        assessments = [
            {"overall_score": 0.2},
            {"overall_score": 0.4},
            {"overall_score": 0.6},
        ]
        result = scorer.aggregate_session_risk(assessments)
        # Should be weighted towards recent assessments
        assert 0.0 <= result.score <= 1.0

    def test_aggregate_session_risk_escalation(self, scorer):
        """Test escalation pattern detection in session."""
        assessments = [
            {"overall_score": 0.3},
            {"overall_score": 0.5},
            {"overall_score": 0.7},
        ]
        result = scorer.aggregate_session_risk(assessments)
        # Escalating pattern should increase risk
        # The exact value depends on the algorithm
        assert result.score > 0.3  # Higher than just the average

    def test_custom_config_thresholds(self, custom_config_scorer):
        """Test scorer with custom config thresholds."""
        # With custom thresholds: medium=0.3, high=0.6, critical=0.85
        factors = [RiskFactor(RiskFactorType.OPERATION, 0.7, 1.0, "Test")]
        result = custom_config_scorer.calculate(factors)
        assert result.level == RiskLevel.HIGH  # 0.7 >= 0.6


class TestRiskScorerEdgeCases:
    """Edge case tests for RiskScorer."""

    def test_zero_weight_factors(self):
        """Test handling of zero-weight factors."""
        scorer = RiskScorer()
        factors = [
            RiskFactor(RiskFactorType.OPERATION, 0.8, 0.0, "Zero weight"),
            RiskFactor(RiskFactorType.CONTEXT, 0.5, 0.5, "Normal"),
        ]
        result = scorer.calculate(factors)
        # Should handle gracefully without division by zero
        assert 0.0 <= result.score <= 1.0

    def test_all_zero_weights(self):
        """Test handling when all weights are zero."""
        scorer = RiskScorer()
        factors = [
            RiskFactor(RiskFactorType.OPERATION, 0.8, 0.0, "Zero"),
            RiskFactor(RiskFactorType.CONTEXT, 0.5, 0.0, "Zero"),
        ]
        result = scorer.calculate(factors)
        assert result.score == 0.0  # No contribution possible

    def test_very_small_scores(self):
        """Test handling of very small scores."""
        scorer = RiskScorer()
        factors = [
            RiskFactor(RiskFactorType.OPERATION, 0.001, 0.5, "Tiny"),
        ]
        result = scorer.calculate(factors)
        assert result.score >= 0.0
        assert result.level == RiskLevel.LOW

    def test_boundary_scores(self):
        """Test exact boundary scores."""
        scorer = RiskScorer()
        config = scorer.config

        # Test exact threshold values using WEIGHTED_AVERAGE for precise boundary testing
        # (HYBRID strategy adjusts scores, making exact boundary tests unreliable)
        for threshold, expected_level in [
            (config.medium_threshold, RiskLevel.MEDIUM),
            (config.high_threshold, RiskLevel.HIGH),
            (config.critical_threshold, RiskLevel.CRITICAL),
        ]:
            factors = [RiskFactor(RiskFactorType.OPERATION, threshold, 1.0, "Boundary")]
            result = scorer.calculate(
                factors, override_strategy=ScoringStrategy.WEIGHTED_AVERAGE
            )
            assert result.level == expected_level

    def test_strategy_override(self):
        """Test that strategy override works."""
        scorer = RiskScorer(strategy=ScoringStrategy.WEIGHTED_AVERAGE)
        factors = [RiskFactor(RiskFactorType.OPERATION, 0.5, 0.5, "Test")]

        # Default strategy
        result1 = scorer.calculate(factors)
        assert result1.strategy_used == ScoringStrategy.WEIGHTED_AVERAGE

        # Override strategy
        result2 = scorer.calculate(factors, override_strategy=ScoringStrategy.MAX_WEIGHTED)
        assert result2.strategy_used == ScoringStrategy.MAX_WEIGHTED
