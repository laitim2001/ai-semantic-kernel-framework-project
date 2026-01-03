# =============================================================================
# IPA Platform - Context Evaluator Tests
# =============================================================================
# Sprint 55: Risk Assessment Engine - S55-3
# =============================================================================

import pytest
from datetime import datetime, timedelta

from src.integrations.hybrid.risk.models import (
    OperationContext,
    RiskFactorType,
)
from src.integrations.hybrid.risk.analyzers.context_evaluator import (
    ContextEvaluator,
    ContextEvaluatorConfig,
    UserTrustLevel,
    UserProfile,
    SessionContext,
)


class TestUserTrustLevel:
    """Tests for UserTrustLevel enum."""

    def test_trust_level_values(self):
        """Test all trust level values."""
        assert UserTrustLevel.NEW.value == "new"
        assert UserTrustLevel.LOW.value == "low"
        assert UserTrustLevel.MEDIUM.value == "medium"
        assert UserTrustLevel.HIGH.value == "high"
        assert UserTrustLevel.TRUSTED.value == "trusted"

    def test_trust_level_ordering(self):
        """Test trust levels have expected ordering semantically."""
        levels = [UserTrustLevel.NEW, UserTrustLevel.LOW, UserTrustLevel.MEDIUM,
                  UserTrustLevel.HIGH, UserTrustLevel.TRUSTED]
        assert len(levels) == 5


class TestUserProfile:
    """Tests for UserProfile dataclass."""

    def test_default_values(self):
        """Test default user profile values."""
        profile = UserProfile(user_id="user123")
        assert profile.user_id == "user123"
        assert profile.trust_level == UserTrustLevel.NEW
        assert profile.total_operations == 0
        assert profile.violations == 0

    def test_custom_values(self):
        """Test custom user profile values."""
        profile = UserProfile(
            user_id="user456",
            trust_level=UserTrustLevel.HIGH,
            total_operations=100,
            successful_operations=95,
            violations=2
        )
        assert profile.trust_level == UserTrustLevel.HIGH
        assert profile.total_operations == 100


class TestSessionContext:
    """Tests for SessionContext dataclass."""

    def test_default_values(self):
        """Test default session context values."""
        session = SessionContext(session_id="sess123", user_id="user456")
        assert session.session_id == "sess123"
        assert session.user_id == "user456"
        assert session.operation_count == 0
        assert session.high_risk_count == 0


class TestContextEvaluatorConfig:
    """Tests for ContextEvaluatorConfig dataclass."""

    def test_default_trust_multipliers(self):
        """Test default trust multipliers."""
        config = ContextEvaluatorConfig()
        assert config.trust_multipliers[UserTrustLevel.NEW] == 1.3
        assert config.trust_multipliers[UserTrustLevel.TRUSTED] == 0.7

    def test_default_environment_multipliers(self):
        """Test default environment multipliers."""
        config = ContextEvaluatorConfig()
        assert config.environment_multipliers["development"] == 0.8
        assert config.environment_multipliers["production"] == 1.3


class TestContextEvaluatorUserTrust:
    """Tests for ContextEvaluator user trust analysis."""

    @pytest.fixture
    def evaluator(self):
        """Create a default evaluator."""
        return ContextEvaluator()

    def test_analyze_unknown_user(self, evaluator):
        """Test analysis for unknown user (no user_id)."""
        context = OperationContext(tool_name="Read")
        factors = evaluator.analyze(context)

        user_factors = [f for f in factors if f.factor_type == RiskFactorType.USER]
        assert len(user_factors) == 1
        assert user_factors[0].score == 0.6  # Higher score for unknown

    def test_analyze_new_user(self, evaluator):
        """Test analysis for new user."""
        context = OperationContext(tool_name="Read", user_id="new_user")
        factors = evaluator.analyze(context)

        user_factors = [f for f in factors if f.factor_type == RiskFactorType.USER]
        assert len(user_factors) == 1
        # New user multiplier is 1.3, so 0.3 * 1.3 = 0.39
        assert user_factors[0].score == pytest.approx(0.39, rel=0.01)

    def test_analyze_trusted_user(self, evaluator):
        """Test analysis for trusted user."""
        evaluator.set_user_trust_level("trusted_user", UserTrustLevel.TRUSTED)
        context = OperationContext(tool_name="Read", user_id="trusted_user")
        factors = evaluator.analyze(context)

        user_factors = [f for f in factors if f.factor_type == RiskFactorType.USER]
        assert len(user_factors) == 1
        # Trusted multiplier is 0.7, so 0.3 * 0.7 = 0.21
        assert user_factors[0].score == pytest.approx(0.21, rel=0.01)

    def test_get_user_trust_level(self, evaluator):
        """Test getting user trust level."""
        assert evaluator.get_user_trust_level("unknown") == UserTrustLevel.NEW

    def test_set_user_trust_level(self, evaluator):
        """Test setting user trust level."""
        evaluator.set_user_trust_level("user123", UserTrustLevel.HIGH)
        assert evaluator.get_user_trust_level("user123") == UserTrustLevel.HIGH


class TestContextEvaluatorEnvironment:
    """Tests for ContextEvaluator environment analysis."""

    @pytest.fixture
    def evaluator(self):
        """Create a default evaluator."""
        return ContextEvaluator()

    def test_analyze_development(self, evaluator):
        """Test analysis for development environment."""
        context = OperationContext(tool_name="Read", environment="development")
        factors = evaluator.analyze(context)

        env_factors = [f for f in factors if f.factor_type == RiskFactorType.ENVIRONMENT]
        assert len(env_factors) == 1
        assert env_factors[0].score == 0.15  # Lower in development

    def test_analyze_production(self, evaluator):
        """Test analysis for production environment."""
        context = OperationContext(tool_name="Read", environment="production")
        factors = evaluator.analyze(context)

        env_factors = [f for f in factors if f.factor_type == RiskFactorType.ENVIRONMENT]
        assert len(env_factors) == 1
        assert env_factors[0].score == 0.5  # Higher in production

    def test_analyze_staging(self, evaluator):
        """Test analysis for staging environment."""
        context = OperationContext(tool_name="Read", environment="staging")
        factors = evaluator.analyze(context)

        env_factors = [f for f in factors if f.factor_type == RiskFactorType.ENVIRONMENT]
        assert len(env_factors) == 1
        assert env_factors[0].score == 0.3  # Baseline

    def test_get_environment_multiplier(self, evaluator):
        """Test getting environment multiplier."""
        assert evaluator.get_environment_multiplier("development") == 0.8
        assert evaluator.get_environment_multiplier("production") == 1.3
        assert evaluator.get_environment_multiplier("unknown") == 1.0


class TestContextEvaluatorSession:
    """Tests for ContextEvaluator session analysis."""

    @pytest.fixture
    def evaluator(self):
        """Create a default evaluator."""
        return ContextEvaluator()

    def test_analyze_no_session(self, evaluator):
        """Test analysis without session ID."""
        context = OperationContext(tool_name="Read", user_id="user123")
        factors = evaluator.analyze(context)

        context_factors = [f for f in factors if f.factor_type == RiskFactorType.CONTEXT]
        assert len(context_factors) == 0  # No session means no session-based factors

    def test_analyze_new_session(self, evaluator):
        """Test analysis for new session."""
        context = OperationContext(
            tool_name="Read",
            user_id="user123",
            session_id="sess456"
        )
        factors = evaluator.analyze(context)

        # New session should not have any context issues
        context_factors = [f for f in factors if f.factor_type == RiskFactorType.CONTEXT]
        assert len(context_factors) == 0

    def test_analyze_high_risk_session(self, evaluator):
        """Test analysis for session with many high-risk operations."""
        # Create session with high-risk count
        session = evaluator._get_or_create_session("sess123", "user123")
        session.high_risk_count = 5
        session.operation_count = 10

        context = OperationContext(
            tool_name="Bash",
            user_id="user123",
            session_id="sess123"
        )
        factors = evaluator.analyze(context)

        context_factors = [f for f in factors if f.factor_type == RiskFactorType.CONTEXT]
        assert len(context_factors) >= 1
        assert any("high-risk" in f.description.lower() for f in context_factors)

    def test_analyze_high_rejection_rate(self, evaluator):
        """Test analysis for session with high rejection rate."""
        session = evaluator._get_or_create_session("sess123", "user123")
        session.operation_count = 10
        session.rejected_count = 5  # 50% rejection rate

        context = OperationContext(
            tool_name="Read",
            user_id="user123",
            session_id="sess123"
        )
        factors = evaluator.analyze(context)

        context_factors = [f for f in factors if f.factor_type == RiskFactorType.CONTEXT]
        assert any("rejection" in f.description.lower() for f in context_factors)

    def test_update_session(self, evaluator):
        """Test updating session context."""
        session = evaluator._get_or_create_session("sess123", "user123")
        evaluator.update_session("sess123", is_sensitive=True, is_high_risk=True)

        assert session.operation_count == 1
        assert session.sensitive_operation_count == 1
        assert session.high_risk_count == 1

    def test_get_session_context(self, evaluator):
        """Test getting session context."""
        evaluator._get_or_create_session("sess123", "user123")
        session = evaluator.get_session_context("sess123")
        assert session is not None
        assert session.session_id == "sess123"

    def test_clear_session(self, evaluator):
        """Test clearing session context."""
        evaluator._get_or_create_session("sess123", "user123")
        evaluator.clear_session("sess123")
        assert evaluator.get_session_context("sess123") is None


class TestContextEvaluatorTrustUpdate:
    """Tests for ContextEvaluator trust level updates."""

    @pytest.fixture
    def evaluator(self):
        """Create a default evaluator."""
        return ContextEvaluator()

    def test_update_trust_success(self, evaluator):
        """Test trust update after successful operation."""
        trust = evaluator.update_user_trust("user123", operation_success=True)
        profile = evaluator._get_or_create_profile("user123")
        assert profile.total_operations == 1
        assert profile.successful_operations == 1

    def test_update_trust_violation(self, evaluator):
        """Test trust update after violation."""
        evaluator.set_user_trust_level("user123", UserTrustLevel.HIGH)

        # Multiple violations should cause downgrade
        for _ in range(3):
            evaluator.update_user_trust("user123", operation_success=False, is_violation=True)

        assert evaluator.get_user_trust_level("user123") == UserTrustLevel.MEDIUM

    def test_update_trust_high_risk(self, evaluator):
        """Test trust update after high-risk operation."""
        evaluator.update_user_trust("user123", operation_success=True, is_high_risk=True)
        profile = evaluator._get_or_create_profile("user123")
        assert profile.high_risk_operations == 1


class TestContextEvaluatorCustomConfig:
    """Tests for ContextEvaluator with custom configuration."""

    def test_custom_trust_multipliers(self):
        """Test with custom trust multipliers."""
        config = ContextEvaluatorConfig(
            trust_multipliers={
                UserTrustLevel.NEW: 2.0,
                UserTrustLevel.TRUSTED: 0.5,
            }
        )
        evaluator = ContextEvaluator(config)

        context = OperationContext(tool_name="Read", user_id="new_user")
        factors = evaluator.analyze(context)

        user_factors = [f for f in factors if f.factor_type == RiskFactorType.USER]
        # 0.3 * 2.0 = 0.6
        assert user_factors[0].score == pytest.approx(0.6, rel=0.01)

    def test_custom_thresholds(self):
        """Test with custom session thresholds."""
        config = ContextEvaluatorConfig(
            high_risk_session_threshold=2  # Lower threshold
        )
        evaluator = ContextEvaluator(config)

        session = evaluator._get_or_create_session("sess123", "user123")
        session.high_risk_count = 2

        context = OperationContext(
            tool_name="Bash",
            session_id="sess123"
        )
        factors = evaluator.analyze(context)

        context_factors = [f for f in factors if f.factor_type == RiskFactorType.CONTEXT]
        assert len(context_factors) >= 1
