# =============================================================================
# IPA Platform - Risk Models Tests
# =============================================================================
# Sprint 55: Risk Assessment Engine Core
# =============================================================================

import pytest
from datetime import datetime

from src.integrations.hybrid.risk.models import (
    RiskLevel,
    RiskFactor,
    RiskFactorType,
    RiskAssessment,
    RiskConfig,
    OperationContext,
)


class TestRiskLevel:
    """Tests for RiskLevel enum."""

    def test_risk_level_values(self):
        """Test risk level enum values."""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"

    def test_from_score_low(self):
        """Test LOW level from score."""
        config = RiskConfig()
        level = RiskLevel.from_score(0.2, config)
        assert level == RiskLevel.LOW

    def test_from_score_medium(self):
        """Test MEDIUM level from score."""
        config = RiskConfig()
        level = RiskLevel.from_score(0.5, config)
        assert level == RiskLevel.MEDIUM

    def test_from_score_high(self):
        """Test HIGH level from score."""
        config = RiskConfig()
        level = RiskLevel.from_score(0.75, config)
        assert level == RiskLevel.HIGH

    def test_from_score_critical(self):
        """Test CRITICAL level from score."""
        config = RiskConfig()
        level = RiskLevel.from_score(0.95, config)
        assert level == RiskLevel.CRITICAL

    def test_from_score_boundary_medium(self):
        """Test boundary between LOW and MEDIUM."""
        config = RiskConfig(medium_threshold=0.4)
        assert RiskLevel.from_score(0.39, config) == RiskLevel.LOW
        assert RiskLevel.from_score(0.4, config) == RiskLevel.MEDIUM

    def test_from_score_boundary_high(self):
        """Test boundary between MEDIUM and HIGH."""
        config = RiskConfig(high_threshold=0.7)
        assert RiskLevel.from_score(0.69, config) == RiskLevel.MEDIUM
        assert RiskLevel.from_score(0.7, config) == RiskLevel.HIGH

    def test_from_score_boundary_critical(self):
        """Test boundary between HIGH and CRITICAL."""
        config = RiskConfig(critical_threshold=0.9)
        assert RiskLevel.from_score(0.89, config) == RiskLevel.HIGH
        assert RiskLevel.from_score(0.9, config) == RiskLevel.CRITICAL

    def test_requires_approval_low(self):
        """Test LOW does not require approval."""
        assert RiskLevel.LOW.requires_approval() is False

    def test_requires_approval_medium(self):
        """Test MEDIUM does not require approval."""
        assert RiskLevel.MEDIUM.requires_approval() is False

    def test_requires_approval_high(self):
        """Test HIGH requires approval."""
        assert RiskLevel.HIGH.requires_approval() is True

    def test_requires_approval_critical(self):
        """Test CRITICAL requires approval."""
        assert RiskLevel.CRITICAL.requires_approval() is True

    def test_level_comparison(self):
        """Test risk level ordering."""
        assert RiskLevel.LOW < RiskLevel.MEDIUM
        assert RiskLevel.MEDIUM < RiskLevel.HIGH
        assert RiskLevel.HIGH < RiskLevel.CRITICAL
        assert not RiskLevel.HIGH < RiskLevel.LOW


class TestRiskFactorType:
    """Tests for RiskFactorType enum."""

    def test_factor_type_values(self):
        """Test all factor type values exist."""
        assert RiskFactorType.OPERATION.value == "operation"
        assert RiskFactorType.CONTEXT.value == "context"
        assert RiskFactorType.PATTERN.value == "pattern"
        assert RiskFactorType.PATH.value == "path"
        assert RiskFactorType.COMMAND.value == "command"
        assert RiskFactorType.FREQUENCY.value == "frequency"
        assert RiskFactorType.ESCALATION.value == "escalation"


class TestRiskFactor:
    """Tests for RiskFactor dataclass."""

    def test_basic_creation(self):
        """Test basic factor creation."""
        factor = RiskFactor(
            factor_type=RiskFactorType.OPERATION,
            score=0.5,
            weight=0.3,
            description="Test factor",
        )
        assert factor.factor_type == RiskFactorType.OPERATION
        assert factor.score == 0.5
        assert factor.weight == 0.3
        assert factor.description == "Test factor"
        assert factor.source is None
        assert factor.metadata == {}

    def test_with_all_fields(self):
        """Test factor with all fields."""
        factor = RiskFactor(
            factor_type=RiskFactorType.PATH,
            score=0.8,
            weight=0.5,
            description="Sensitive path",
            source="/etc/passwd",
            metadata={"reason": "system file"},
        )
        assert factor.source == "/etc/passwd"
        assert factor.metadata["reason"] == "system file"

    def test_weighted_score(self):
        """Test weighted score calculation."""
        factor = RiskFactor(
            factor_type=RiskFactorType.OPERATION,
            score=0.6,
            weight=0.5,
            description="Test",
        )
        assert factor.weighted_score() == 0.3

    def test_score_validation_too_high(self):
        """Test score validation for too high value."""
        with pytest.raises(ValueError, match="Score must be between"):
            RiskFactor(
                factor_type=RiskFactorType.OPERATION,
                score=1.5,
                weight=0.5,
                description="Test",
            )

    def test_score_validation_negative(self):
        """Test score validation for negative value."""
        with pytest.raises(ValueError, match="Score must be between"):
            RiskFactor(
                factor_type=RiskFactorType.OPERATION,
                score=-0.1,
                weight=0.5,
                description="Test",
            )

    def test_weight_validation_too_high(self):
        """Test weight validation for too high value."""
        with pytest.raises(ValueError, match="Weight must be between"):
            RiskFactor(
                factor_type=RiskFactorType.OPERATION,
                score=0.5,
                weight=1.5,
                description="Test",
            )

    def test_weight_validation_negative(self):
        """Test weight validation for negative value."""
        with pytest.raises(ValueError, match="Weight must be between"):
            RiskFactor(
                factor_type=RiskFactorType.OPERATION,
                score=0.5,
                weight=-0.1,
                description="Test",
            )


class TestRiskAssessment:
    """Tests for RiskAssessment dataclass."""

    def test_basic_creation(self):
        """Test basic assessment creation."""
        assessment = RiskAssessment(
            overall_level=RiskLevel.MEDIUM,
            overall_score=0.5,
            factors=[],
            requires_approval=False,
        )
        assert assessment.overall_level == RiskLevel.MEDIUM
        assert assessment.overall_score == 0.5
        assert assessment.factors == []
        assert assessment.requires_approval is False
        assert assessment.approval_reason is None
        assert assessment.session_id is None

    def test_with_factors(self):
        """Test assessment with factors."""
        factor = RiskFactor(
            factor_type=RiskFactorType.OPERATION,
            score=0.5,
            weight=0.5,
            description="Test",
        )
        assessment = RiskAssessment(
            overall_level=RiskLevel.HIGH,
            overall_score=0.75,
            factors=[factor],
            requires_approval=True,
            approval_reason="High risk operation",
        )
        assert len(assessment.factors) == 1
        assert assessment.approval_reason == "High risk operation"

    def test_get_factors_by_type(self):
        """Test filtering factors by type."""
        factors = [
            RiskFactor(RiskFactorType.OPERATION, 0.5, 0.3, "Op1"),
            RiskFactor(RiskFactorType.PATH, 0.6, 0.3, "Path1"),
            RiskFactor(RiskFactorType.OPERATION, 0.4, 0.3, "Op2"),
        ]
        assessment = RiskAssessment(
            overall_level=RiskLevel.MEDIUM,
            overall_score=0.5,
            factors=factors,
            requires_approval=False,
        )

        op_factors = assessment.get_factors_by_type(RiskFactorType.OPERATION)
        assert len(op_factors) == 2

        path_factors = assessment.get_factors_by_type(RiskFactorType.PATH)
        assert len(path_factors) == 1

    def test_get_highest_factor(self):
        """Test getting highest weighted score factor."""
        factors = [
            RiskFactor(RiskFactorType.OPERATION, 0.5, 0.3, "Op"),  # 0.15
            RiskFactor(RiskFactorType.PATH, 0.8, 0.5, "Path"),     # 0.40
            RiskFactor(RiskFactorType.COMMAND, 0.6, 0.3, "Cmd"),   # 0.18
        ]
        assessment = RiskAssessment(
            overall_level=RiskLevel.HIGH,
            overall_score=0.7,
            factors=factors,
            requires_approval=True,
        )

        highest = assessment.get_highest_factor()
        assert highest is not None
        assert highest.factor_type == RiskFactorType.PATH
        assert highest.weighted_score() == 0.4

    def test_get_highest_factor_empty(self):
        """Test getting highest factor when no factors."""
        assessment = RiskAssessment(
            overall_level=RiskLevel.LOW,
            overall_score=0.1,
            factors=[],
            requires_approval=False,
        )
        assert assessment.get_highest_factor() is None

    def test_to_dict(self):
        """Test serialization to dictionary."""
        factor = RiskFactor(RiskFactorType.OPERATION, 0.5, 0.3, "Test")
        assessment = RiskAssessment(
            overall_level=RiskLevel.MEDIUM,
            overall_score=0.5,
            factors=[factor],
            requires_approval=False,
            session_id="test-session",
        )

        result = assessment.to_dict()

        assert result["overall_level"] == "medium"
        assert result["overall_score"] == 0.5
        assert len(result["factors"]) == 1
        assert result["factors"][0]["factor_type"] == "operation"
        assert result["requires_approval"] is False
        assert result["session_id"] == "test-session"

    def test_score_validation_too_high(self):
        """Test score validation for too high value."""
        with pytest.raises(ValueError, match="Overall score must be between"):
            RiskAssessment(
                overall_level=RiskLevel.CRITICAL,
                overall_score=1.5,
                factors=[],
                requires_approval=True,
            )


class TestRiskConfig:
    """Tests for RiskConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RiskConfig()
        assert config.critical_threshold == 0.9
        assert config.high_threshold == 0.7
        assert config.medium_threshold == 0.4
        assert config.operation_weight == 0.5
        assert config.context_weight == 0.3
        assert config.pattern_weight == 0.2
        assert config.auto_approve_low is True
        assert config.auto_approve_medium is True
        assert config.max_auto_approve_score == 0.6
        assert config.enable_pattern_detection is True
        assert config.pattern_window_seconds == 300

    def test_custom_thresholds(self):
        """Test custom threshold configuration."""
        config = RiskConfig(
            critical_threshold=0.95,
            high_threshold=0.8,
            medium_threshold=0.5,
        )
        assert config.critical_threshold == 0.95
        assert config.high_threshold == 0.8
        assert config.medium_threshold == 0.5

    def test_threshold_ordering_validation(self):
        """Test threshold ordering validation."""
        with pytest.raises(ValueError, match="Thresholds must be in order"):
            RiskConfig(
                critical_threshold=0.7,
                high_threshold=0.9,  # higher than critical
                medium_threshold=0.4,
            )

    def test_threshold_bound_validation(self):
        """Test threshold bound validation."""
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            RiskConfig(critical_threshold=1.5)

    def test_weight_bound_validation(self):
        """Test weight bound validation."""
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            RiskConfig(operation_weight=1.5)

    def test_should_auto_approve_low(self):
        """Test auto-approval for LOW risk."""
        config = RiskConfig(auto_approve_low=True)
        assert config.should_auto_approve(RiskLevel.LOW, 0.3) is True

    def test_should_auto_approve_medium(self):
        """Test auto-approval for MEDIUM risk."""
        config = RiskConfig(auto_approve_medium=True)
        assert config.should_auto_approve(RiskLevel.MEDIUM, 0.5) is True

    def test_should_not_auto_approve_high_score(self):
        """Test no auto-approval when score exceeds max."""
        config = RiskConfig(max_auto_approve_score=0.5)
        assert config.should_auto_approve(RiskLevel.LOW, 0.6) is False

    def test_should_not_auto_approve_high_level(self):
        """Test no auto-approval for HIGH risk."""
        config = RiskConfig()
        assert config.should_auto_approve(RiskLevel.HIGH, 0.5) is False

    def test_should_not_auto_approve_critical(self):
        """Test no auto-approval for CRITICAL risk."""
        config = RiskConfig()
        assert config.should_auto_approve(RiskLevel.CRITICAL, 0.5) is False


class TestOperationContext:
    """Tests for OperationContext dataclass."""

    def test_basic_creation(self):
        """Test basic context creation."""
        context = OperationContext(tool_name="Read")
        assert context.tool_name == "Read"
        assert context.operation_type == "unknown"
        assert context.target_paths == []
        assert context.command is None
        assert context.environment == "development"

    def test_with_all_fields(self):
        """Test context with all fields."""
        context = OperationContext(
            tool_name="Bash",
            operation_type="execute",
            target_paths=["/tmp/test.sh"],
            command="./test.sh",
            arguments={"timeout": 30},
            session_id="session-123",
            user_id="user-456",
            environment="production",
        )
        assert context.tool_name == "Bash"
        assert context.operation_type == "execute"
        assert context.target_paths == ["/tmp/test.sh"]
        assert context.command == "./test.sh"
        assert context.arguments["timeout"] == 30
        assert context.session_id == "session-123"
        assert context.user_id == "user-456"
        assert context.environment == "production"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        context = OperationContext(
            tool_name="Edit",
            target_paths=["/app/config.py"],
            session_id="test-session",
        )

        result = context.to_dict()

        assert result["tool_name"] == "Edit"
        assert result["target_paths"] == ["/app/config.py"]
        assert result["session_id"] == "test-session"
        assert "timestamp" in result
        assert result["previous_operations_count"] == 0
