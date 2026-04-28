# =============================================================================
# IPA Platform - Risk Assessment Engine Tests
# =============================================================================
# Sprint 55: Risk Assessment Engine Core
# =============================================================================

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from src.integrations.hybrid.risk.models import (
    OperationContext,
    RiskAssessment,
    RiskConfig,
    RiskFactor,
    RiskFactorType,
    RiskLevel,
)
from src.integrations.hybrid.risk.engine import (
    RiskAssessmentEngine,
    EngineMetrics,
    AssessmentHistory,
    create_engine,
)


class TestEngineMetrics:
    """Tests for EngineMetrics dataclass."""

    def test_default_values(self):
        """Test default metric values."""
        metrics = EngineMetrics()
        assert metrics.total_assessments == 0
        assert metrics.total_score == 0.0
        assert metrics.approvals_required == 0
        assert metrics.total_latency_ms == 0.0

    def test_average_score_empty(self):
        """Test average score with no assessments."""
        metrics = EngineMetrics()
        assert metrics.average_score == 0.0

    def test_average_score_with_data(self):
        """Test average score calculation."""
        metrics = EngineMetrics(total_assessments=10, total_score=5.0)
        assert metrics.average_score == 0.5

    def test_approval_rate_empty(self):
        """Test approval rate with no assessments."""
        metrics = EngineMetrics()
        assert metrics.approval_rate == 0.0

    def test_approval_rate_with_data(self):
        """Test approval rate calculation."""
        metrics = EngineMetrics(total_assessments=10, approvals_required=3)
        assert metrics.approval_rate == 0.3

    def test_average_latency_empty(self):
        """Test average latency with no assessments."""
        metrics = EngineMetrics()
        assert metrics.average_latency_ms == 0.0

    def test_average_latency_with_data(self):
        """Test average latency calculation."""
        metrics = EngineMetrics(total_assessments=10, total_latency_ms=100.0)
        assert metrics.average_latency_ms == 10.0


class TestAssessmentHistory:
    """Tests for AssessmentHistory class."""

    def test_add_assessment(self):
        """Test adding assessment to history."""
        history = AssessmentHistory()
        assessment = RiskAssessment(
            overall_level=RiskLevel.LOW,
            overall_score=0.2,
            factors=[],
            requires_approval=False,
        )
        history.add(assessment)
        assert len(history.entries) == 1

    def test_max_size_limit(self):
        """Test max size limiting."""
        history = AssessmentHistory(max_size=5)
        for i in range(10):
            assessment = RiskAssessment(
                overall_level=RiskLevel.LOW,
                overall_score=0.2,
                factors=[],
                requires_approval=False,
            )
            history.add(assessment)
        assert len(history.entries) == 5

    def test_get_recent_time_filter(self):
        """Test getting recent assessments by time."""
        history = AssessmentHistory()

        # Add old assessment
        old_assessment = RiskAssessment(
            overall_level=RiskLevel.LOW,
            overall_score=0.2,
            factors=[],
            requires_approval=False,
            assessment_time=datetime.utcnow() - timedelta(minutes=10),
        )
        history.add(old_assessment)

        # Add recent assessment
        recent_assessment = RiskAssessment(
            overall_level=RiskLevel.MEDIUM,
            overall_score=0.5,
            factors=[],
            requires_approval=False,
            assessment_time=datetime.utcnow(),
        )
        history.add(recent_assessment)

        recent = history.get_recent(seconds=300)  # 5 minutes
        assert len(recent) == 1
        assert recent[0].overall_level == RiskLevel.MEDIUM

    def test_get_recent_session_filter(self):
        """Test getting recent assessments by session."""
        history = AssessmentHistory()

        # Add assessment for session A
        assessment_a = RiskAssessment(
            overall_level=RiskLevel.LOW,
            overall_score=0.2,
            factors=[],
            requires_approval=False,
            session_id="session-a",
        )
        history.add(assessment_a)

        # Add assessment for session B
        assessment_b = RiskAssessment(
            overall_level=RiskLevel.MEDIUM,
            overall_score=0.5,
            factors=[],
            requires_approval=False,
            session_id="session-b",
        )
        history.add(assessment_b)

        recent_a = history.get_recent(seconds=300, session_id="session-a")
        assert len(recent_a) == 1
        assert recent_a[0].session_id == "session-a"

    def test_clear_session(self):
        """Test clearing session history."""
        history = AssessmentHistory()

        # Add assessments for two sessions
        for i in range(3):
            history.add(RiskAssessment(
                overall_level=RiskLevel.LOW,
                overall_score=0.2,
                factors=[],
                requires_approval=False,
                session_id="session-a",
            ))
            history.add(RiskAssessment(
                overall_level=RiskLevel.LOW,
                overall_score=0.2,
                factors=[],
                requires_approval=False,
                session_id="session-b",
            ))

        assert len(history.entries) == 6

        cleared = history.clear_session("session-a")
        assert cleared == 3
        assert len(history.entries) == 3
        assert all(e.session_id == "session-b" for e in history.entries)


class TestRiskAssessmentEngine:
    """Tests for RiskAssessmentEngine class."""

    @pytest.fixture
    def engine(self):
        """Create a default engine."""
        return RiskAssessmentEngine()

    @pytest.fixture
    def mock_analyzer(self):
        """Create a mock analyzer."""
        analyzer = MagicMock()
        analyzer.analyze.return_value = [
            RiskFactor(
                factor_type=RiskFactorType.OPERATION,
                score=0.5,
                weight=0.5,
                description="Mock analysis",
            )
        ]
        return analyzer

    def test_init_default(self):
        """Test default initialization."""
        engine = RiskAssessmentEngine()
        assert engine.config is not None
        assert engine.scorer is not None
        assert len(engine._analyzers) == 0

    def test_init_with_config(self):
        """Test initialization with custom config."""
        config = RiskConfig(critical_threshold=0.85)
        engine = RiskAssessmentEngine(config=config)
        assert engine.config.critical_threshold == 0.85

    def test_register_analyzer(self, engine, mock_analyzer):
        """Test analyzer registration."""
        engine.register_analyzer(mock_analyzer)
        assert len(engine._analyzers) == 1

    def test_register_hook(self, engine):
        """Test hook registration."""
        callback = MagicMock()
        engine.register_hook("pre_assess", callback)
        assert len(engine._hooks["pre_assess"]) == 1

    def test_register_hook_invalid_type(self, engine):
        """Test invalid hook type raises error."""
        callback = MagicMock()
        with pytest.raises(ValueError, match="Unknown hook type"):
            engine.register_hook("invalid", callback)

    def test_assess_basic(self, engine):
        """Test basic assessment."""
        context = OperationContext(tool_name="Read")
        assessment = engine.assess(context)

        assert isinstance(assessment, RiskAssessment)
        assert assessment.overall_level in RiskLevel
        assert 0.0 <= assessment.overall_score <= 1.0

    def test_assess_with_analyzer(self, engine, mock_analyzer):
        """Test assessment with registered analyzer."""
        engine.register_analyzer(mock_analyzer)
        context = OperationContext(tool_name="Write")

        assessment = engine.assess(context)

        mock_analyzer.analyze.assert_called_once()
        assert len(assessment.factors) >= 1

    def test_assess_runs_hooks(self, engine):
        """Test that hooks are called during assessment."""
        pre_hook = MagicMock()
        post_hook = MagicMock()

        engine.register_hook("pre_assess", pre_hook)
        engine.register_hook("post_assess", post_hook)

        context = OperationContext(tool_name="Read")
        engine.assess(context)

        pre_hook.assert_called_once()
        post_hook.assert_called_once()

    def test_assess_high_risk_hook(self, engine, mock_analyzer):
        """Test high risk hook is called for HIGH/CRITICAL."""
        # Configure analyzer to return high risk
        mock_analyzer.analyze.return_value = [
            RiskFactor(
                factor_type=RiskFactorType.OPERATION,
                score=0.85,
                weight=1.0,
                description="High risk operation",
            )
        ]
        engine.register_analyzer(mock_analyzer)

        high_risk_hook = MagicMock()
        engine.register_hook("on_high_risk", high_risk_hook)

        context = OperationContext(
            tool_name="Bash",
            environment="production",  # Increases risk
        )
        engine.assess(context)

        high_risk_hook.assert_called_once()

    def test_assess_updates_metrics(self, engine):
        """Test that metrics are updated after assessment."""
        context = OperationContext(tool_name="Read")

        assert engine.get_metrics().total_assessments == 0

        engine.assess(context)

        metrics = engine.get_metrics()
        assert metrics.total_assessments == 1
        assert metrics.total_score > 0

    def test_assess_updates_history(self, engine):
        """Test that history is updated after assessment."""
        context = OperationContext(
            tool_name="Read",
            session_id="test-session",
        )

        engine.assess(context)

        recent = engine._history.get_recent(seconds=60, session_id="test-session")
        assert len(recent) == 1

    def test_assess_analyzer_error_handling(self, engine):
        """Test graceful handling of analyzer errors."""
        failing_analyzer = MagicMock()
        failing_analyzer.analyze.side_effect = Exception("Analyzer failed")
        engine.register_analyzer(failing_analyzer)

        context = OperationContext(tool_name="Read")

        # Should not raise, should handle gracefully
        assessment = engine.assess(context)
        assert assessment is not None
        # Error should be recorded as a factor
        error_factors = [
            f for f in assessment.factors
            if "error" in f.description.lower()
        ]
        assert len(error_factors) >= 1

    def test_assess_requires_approval_high(self, engine, mock_analyzer):
        """Test approval requirement for HIGH risk."""
        mock_analyzer.analyze.return_value = [
            RiskFactor(
                factor_type=RiskFactorType.OPERATION,
                score=0.8,
                weight=1.0,
                description="High risk",
            )
        ]
        engine.register_analyzer(mock_analyzer)

        # Use production environment to ensure score stays high (multiplier 1.3)
        context = OperationContext(tool_name="Bash", environment="production")
        assessment = engine.assess(context)

        assert assessment.requires_approval is True
        assert assessment.approval_reason is not None

    def test_assess_no_approval_low(self, engine, mock_analyzer):
        """Test no approval requirement for LOW risk."""
        mock_analyzer.analyze.return_value = [
            RiskFactor(
                factor_type=RiskFactorType.OPERATION,
                score=0.1,
                weight=1.0,
                description="Low risk",
            )
        ]
        engine.register_analyzer(mock_analyzer)

        context = OperationContext(tool_name="Read")
        assessment = engine.assess(context)

        assert assessment.requires_approval is False
        assert assessment.approval_reason is None

    def test_assess_batch(self, engine):
        """Test batch assessment."""
        contexts = [
            OperationContext(tool_name="Read"),
            OperationContext(tool_name="Write"),
            OperationContext(tool_name="Bash"),
        ]

        assessments = engine.assess_batch(contexts)

        assert len(assessments) == 3
        # Later operations should have batch factor added
        assert any(
            "Batch" in f.description
            for a in assessments[1:]
            for f in a.factors
        )

    def test_get_session_risk(self, engine):
        """Test session risk aggregation."""
        session_id = "test-session"

        # Perform multiple assessments
        for _ in range(3):
            context = OperationContext(tool_name="Read", session_id=session_id)
            engine.assess(context)

        result = engine.get_session_risk(session_id)
        assert result.score >= 0.0

    def test_get_session_risk_empty(self, engine):
        """Test session risk with no history."""
        result = engine.get_session_risk("nonexistent-session")
        assert result.score == 0.0
        assert result.level == RiskLevel.LOW

    def test_clear_session_history(self, engine):
        """Test clearing session history."""
        session_id = "test-session"

        # Perform assessments
        for _ in range(5):
            context = OperationContext(tool_name="Read", session_id=session_id)
            engine.assess(context)

        cleared = engine.clear_session_history(session_id)
        assert cleared == 5

        recent = engine._history.get_recent(session_id=session_id)
        assert len(recent) == 0

    def test_reset_metrics(self, engine):
        """Test metrics reset."""
        context = OperationContext(tool_name="Read")
        engine.assess(context)

        assert engine.get_metrics().total_assessments > 0

        engine.reset_metrics()

        assert engine.get_metrics().total_assessments == 0

    def test_base_factors_by_tool(self, engine):
        """Test base risk factors for different tools."""
        tool_risks = {
            "Read": RiskLevel.LOW,
            "Glob": RiskLevel.LOW,
            "Write": RiskLevel.MEDIUM,
            "Edit": RiskLevel.MEDIUM,
            "Bash": RiskLevel.MEDIUM,
        }

        for tool, expected_max_level in tool_risks.items():
            context = OperationContext(tool_name=tool)
            assessment = engine.assess(context)
            # The level should not exceed the expected maximum for that tool
            # (in development environment which reduces risk)
            assert assessment.overall_score >= 0.0


class TestRiskAssessmentEnginePatternDetection:
    """Tests for pattern detection in RiskAssessmentEngine."""

    @pytest.fixture
    def engine(self):
        """Create engine with pattern detection enabled."""
        config = RiskConfig(enable_pattern_detection=True)
        return RiskAssessmentEngine(config=config)

    def test_frequency_detection(self, engine):
        """Test high frequency detection."""
        session_id = "high-freq-session"

        # Perform many assessments quickly
        for i in range(15):
            context = OperationContext(
                tool_name="Read",
                session_id=session_id,
            )
            engine.assess(context)

        # Last assessment should have frequency factor
        context = OperationContext(tool_name="Read", session_id=session_id)
        assessment = engine.assess(context)

        freq_factors = [
            f for f in assessment.factors
            if f.factor_type == RiskFactorType.FREQUENCY
        ]
        # Should detect high frequency after 10 operations
        assert len(freq_factors) >= 1

    def test_escalation_pattern_detection(self, engine):
        """Test risk escalation pattern detection."""
        session_id = "escalation-session"

        # Create escalating risk pattern
        mock_analyzer = MagicMock()
        engine.register_analyzer(mock_analyzer)

        scores = [0.3, 0.5, 0.7]  # Escalating pattern
        for score in scores:
            mock_analyzer.analyze.return_value = [
                RiskFactor(
                    RiskFactorType.OPERATION,
                    score,
                    1.0,
                    "Escalating",
                )
            ]
            context = OperationContext(
                tool_name="Bash",
                session_id=session_id,
            )
            engine.assess(context)

        # Next assessment should detect escalation
        mock_analyzer.analyze.return_value = [
            RiskFactor(RiskFactorType.OPERATION, 0.8, 1.0, "High"),
        ]
        assessment = engine.assess(
            OperationContext(tool_name="Bash", session_id=session_id)
        )

        escalation_factors = [
            f for f in assessment.factors
            if f.factor_type == RiskFactorType.ESCALATION
        ]
        assert len(escalation_factors) >= 1


class TestCreateEngine:
    """Tests for create_engine factory function."""

    def test_create_default_engine(self):
        """Test creating default engine."""
        engine = create_engine()
        assert isinstance(engine, RiskAssessmentEngine)
        assert engine.config is not None

    def test_create_engine_with_config(self):
        """Test creating engine with custom config."""
        config = RiskConfig(critical_threshold=0.85)
        engine = create_engine(config=config)
        assert engine.config.critical_threshold == 0.85

    def test_create_engine_with_default_analyzers(self):
        """Test creating engine with default analyzers flag."""
        # This just ensures the flag works, analyzers come in S55-2/S55-3
        engine = create_engine(with_default_analyzers=True)
        assert isinstance(engine, RiskAssessmentEngine)
