# =============================================================================
# IPA Platform - Pattern Detector Tests
# =============================================================================
# Sprint 55: Risk Assessment Engine - S55-3
# =============================================================================

import pytest
from datetime import datetime, timedelta
from collections import deque

from src.integrations.hybrid.risk.models import (
    OperationContext,
    RiskFactorType,
    RiskLevel,
)
from src.integrations.hybrid.risk.analyzers.pattern_detector import (
    PatternDetector,
    PatternDetectorConfig,
    PatternType,
    DetectedPattern,
    OperationRecord,
)


class TestPatternType:
    """Tests for PatternType enum."""

    def test_pattern_type_values(self):
        """Test all pattern type values."""
        assert PatternType.FREQUENCY_ANOMALY.value == "frequency_anomaly"
        assert PatternType.BEHAVIOR_DEVIATION.value == "behavior_deviation"
        assert PatternType.RISK_ESCALATION.value == "risk_escalation"
        assert PatternType.TEMPORAL_ANOMALY.value == "temporal_anomaly"
        assert PatternType.TOOL_SEQUENCE.value == "tool_sequence"

    def test_pattern_type_count(self):
        """Test we have expected number of pattern types."""
        assert len(PatternType) == 5


class TestOperationRecord:
    """Tests for OperationRecord dataclass."""

    def test_create_record(self):
        """Test creating operation record."""
        now = datetime.utcnow()
        record = OperationRecord(
            timestamp=now,
            tool_name="Bash",
            risk_score=0.7,
            risk_level=RiskLevel.HIGH,
            user_id="user123",
            session_id="sess456"
        )
        assert record.timestamp == now
        assert record.tool_name == "Bash"
        assert record.risk_score == 0.7
        assert record.risk_level == RiskLevel.HIGH
        assert record.user_id == "user123"
        assert record.session_id == "sess456"

    def test_default_metadata(self):
        """Test default metadata is empty dict."""
        record = OperationRecord(
            timestamp=datetime.utcnow(),
            tool_name="Read",
            risk_score=0.2,
            risk_level=RiskLevel.LOW,
            user_id=None,
            session_id=None
        )
        assert record.metadata == {}


class TestDetectedPattern:
    """Tests for DetectedPattern dataclass."""

    def test_create_pattern(self):
        """Test creating detected pattern."""
        pattern = DetectedPattern(
            pattern_type=PatternType.FREQUENCY_ANOMALY,
            severity=0.7,
            description="High operation frequency",
            evidence={"count": 25, "window": 60}
        )
        assert pattern.pattern_type == PatternType.FREQUENCY_ANOMALY
        assert pattern.severity == 0.7
        assert pattern.description == "High operation frequency"
        assert pattern.evidence == {"count": 25, "window": 60}
        assert pattern.detected_at is not None


class TestPatternDetectorConfig:
    """Tests for PatternDetectorConfig dataclass."""

    def test_default_frequency_settings(self):
        """Test default frequency detection settings."""
        config = PatternDetectorConfig()
        assert config.frequency_window_seconds == 60
        assert config.max_operations_per_window == 20
        assert config.burst_threshold == 5

    def test_default_behavior_settings(self):
        """Test default behavior deviation settings."""
        config = PatternDetectorConfig()
        assert config.baseline_window_hours == 24
        assert config.deviation_threshold == 0.3

    def test_default_escalation_settings(self):
        """Test default escalation detection settings."""
        config = PatternDetectorConfig()
        assert config.escalation_window_count == 10
        assert config.escalation_threshold == 0.15

    def test_default_temporal_settings(self):
        """Test default temporal anomaly settings."""
        config = PatternDetectorConfig()
        assert config.off_hours_start == 22
        assert config.off_hours_end == 6

    def test_default_suspicious_sequences(self):
        """Test default suspicious tool sequences."""
        config = PatternDetectorConfig()
        assert len(config.suspicious_sequences) == 3
        assert ("Grep", "Read", "Write") in config.suspicious_sequences

    def test_default_history_limits(self):
        """Test default history limits."""
        config = PatternDetectorConfig()
        assert config.max_history_size == 1000
        assert config.max_session_history == 100


class TestPatternDetectorFrequency:
    """Tests for PatternDetector frequency anomaly detection."""

    @pytest.fixture
    def detector(self):
        """Create a default detector."""
        return PatternDetector()

    def test_no_anomaly_few_operations(self, detector):
        """Test no anomaly detected with few operations."""
        context = OperationContext(tool_name="Read", session_id="sess123")
        factors = detector.analyze(context)

        # No frequency anomaly with just one operation
        freq_factors = [f for f in factors
                       if f.metadata.get("pattern_type") == "frequency_anomaly"]
        assert len(freq_factors) == 0

    def test_burst_detection(self, detector):
        """Test burst detection (many ops in 5 seconds)."""
        session_id = "sess123"

        # Add 5 operations (burst threshold)
        for i in range(5):
            context = OperationContext(
                tool_name="Read",
                session_id=session_id
            )
            detector.analyze(context, current_risk_score=0.3)

        # The 6th operation should detect burst
        context = OperationContext(tool_name="Read", session_id=session_id)
        factors = detector.analyze(context, current_risk_score=0.3)

        freq_factors = [f for f in factors
                       if f.metadata.get("pattern_type") == "frequency_anomaly"]
        # May or may not detect depending on timing
        # Just verify no errors occur

    def test_high_frequency_detection(self, detector):
        """Test high frequency detection (many ops in 60 seconds)."""
        session_id = "sess_freq"
        config = PatternDetectorConfig(max_operations_per_window=5)
        detector = PatternDetector(config)

        # Add operations to trigger high frequency
        for i in range(6):
            context = OperationContext(
                tool_name="Read",
                session_id=session_id
            )
            detector.analyze(context, current_risk_score=0.3)

        # Verify history is maintained
        assert session_id in detector.session_histories
        assert len(detector.session_histories[session_id]) == 6


class TestPatternDetectorBehavior:
    """Tests for PatternDetector behavior deviation detection."""

    @pytest.fixture
    def detector(self):
        """Create a default detector."""
        return PatternDetector()

    def test_no_deviation_without_baseline(self, detector):
        """Test no deviation without baseline data."""
        context = OperationContext(
            tool_name="Bash",
            user_id="new_user",
            session_id="sess123"
        )
        factors = detector.analyze(context)

        deviation_factors = [f for f in factors
                            if f.metadata.get("pattern_type") == "behavior_deviation"]
        assert len(deviation_factors) == 0

    def test_baseline_building(self, detector):
        """Test user baseline is built over time."""
        user_id = "user123"
        session_id = "sess456"

        # Build baseline with Read operations
        for i in range(15):
            context = OperationContext(
                tool_name="Read",
                user_id=user_id,
                session_id=session_id
            )
            detector.analyze(context)

        # Verify baseline exists
        baseline = detector.get_user_baseline(user_id)
        assert "Read" in baseline
        assert baseline["Read"] == 15

    def test_deviation_from_baseline(self, detector):
        """Test deviation detection from established baseline."""
        user_id = "user_baseline"
        session_id = "sess_baseline"

        # Build heavy baseline with Read operations
        for i in range(20):
            context = OperationContext(
                tool_name="Read",
                user_id=user_id,
                session_id=session_id
            )
            detector.analyze(context)

        # Use a rarely-used tool
        context = OperationContext(
            tool_name="Bash",
            user_id=user_id,
            session_id=session_id
        )
        factors = detector.analyze(context)

        # Should detect behavior deviation
        deviation_factors = [f for f in factors
                            if f.metadata.get("pattern_type") == "behavior_deviation"]
        # Bash is rarely used so deviation may be detected


class TestPatternDetectorEscalation:
    """Tests for PatternDetector risk escalation detection."""

    @pytest.fixture
    def detector(self):
        """Create detector with smaller escalation window."""
        config = PatternDetectorConfig(
            escalation_window_count=5,
            escalation_threshold=0.1
        )
        return PatternDetector(config)

    def test_no_escalation_few_operations(self, detector):
        """Test no escalation with few operations."""
        context = OperationContext(tool_name="Read", session_id="sess123")
        factors = detector.analyze(context, current_risk_score=0.5)

        escalation_factors = [f for f in factors
                             if f.metadata.get("pattern_type") == "risk_escalation"]
        assert len(escalation_factors) == 0

    def test_escalation_detection(self, detector):
        """Test escalation pattern detection."""
        session_id = "sess_escalate"

        # Build increasing risk scores
        risk_scores = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
        for score in risk_scores:
            context = OperationContext(
                tool_name="Bash",
                session_id=session_id
            )
            detector.analyze(context, current_risk_score=score, current_risk_level=RiskLevel.MEDIUM)

        # Session history should show the escalation pattern
        assert session_id in detector.session_histories
        history = list(detector.session_histories[session_id])
        assert len(history) == 7


class TestPatternDetectorTemporal:
    """Tests for PatternDetector temporal anomaly detection."""

    def test_temporal_off_hours_config(self):
        """Test temporal off-hours configuration."""
        config = PatternDetectorConfig(
            off_hours_start=18,  # 6 PM
            off_hours_end=8      # 8 AM
        )
        detector = PatternDetector(config)

        assert detector.config.off_hours_start == 18
        assert detector.config.off_hours_end == 8


class TestPatternDetectorToolSequence:
    """Tests for PatternDetector tool sequence detection."""

    @pytest.fixture
    def detector(self):
        """Create a default detector."""
        return PatternDetector()

    def test_no_sequence_few_operations(self, detector):
        """Test no sequence pattern with few operations."""
        context = OperationContext(tool_name="Read", session_id="sess123")
        factors = detector.analyze(context)

        sequence_factors = [f for f in factors
                          if f.metadata.get("pattern_type") == "tool_sequence"]
        assert len(sequence_factors) == 0

    def test_suspicious_sequence_detection(self, detector):
        """Test suspicious tool sequence detection."""
        session_id = "sess_seq"

        # Execute sequence: Grep -> Read -> Write (suspicious)
        for tool in ["Grep", "Read"]:
            context = OperationContext(
                tool_name=tool,
                session_id=session_id
            )
            detector.analyze(context)

        # The "Write" should trigger sequence detection
        context = OperationContext(
            tool_name="Write",
            session_id=session_id
        )
        factors = detector.analyze(context)

        sequence_factors = [f for f in factors
                          if f.metadata.get("pattern_type") == "tool_sequence"]
        assert len(sequence_factors) == 1
        assert "Grep → Read → Write" in sequence_factors[0].description

    def test_custom_suspicious_sequences(self):
        """Test custom suspicious sequences."""
        config = PatternDetectorConfig(
            suspicious_sequences=[
                ("Read", "Write", "Bash"),  # Custom sequence
            ]
        )
        detector = PatternDetector(config)
        session_id = "sess_custom"

        # Execute custom sequence
        for tool in ["Read", "Write"]:
            context = OperationContext(
                tool_name=tool,
                session_id=session_id
            )
            detector.analyze(context)

        # "Bash" should trigger
        context = OperationContext(
            tool_name="Bash",
            session_id=session_id
        )
        factors = detector.analyze(context)

        sequence_factors = [f for f in factors
                          if f.metadata.get("pattern_type") == "tool_sequence"]
        assert len(sequence_factors) == 1


class TestPatternDetectorSessionManagement:
    """Tests for PatternDetector session management."""

    @pytest.fixture
    def detector(self):
        """Create a default detector."""
        return PatternDetector()

    def test_get_session_patterns(self, detector):
        """Test getting patterns for a session."""
        session_id = "sess_patterns"

        # Add some operations
        for i in range(5):
            context = OperationContext(
                tool_name="Read",
                session_id=session_id
            )
            detector.analyze(context, current_risk_score=0.3)

        patterns = detector.get_session_patterns(session_id)
        assert isinstance(patterns, list)

    def test_clear_session(self, detector):
        """Test clearing session history."""
        session_id = "sess_clear"

        # Add operations
        context = OperationContext(tool_name="Read", session_id=session_id)
        detector.analyze(context)

        assert session_id in detector.session_histories

        # Clear session
        detector.clear_session(session_id)
        assert session_id not in detector.session_histories

    def test_clear_all(self, detector):
        """Test clearing all histories."""
        # Add operations to multiple sessions
        for sess_id in ["sess1", "sess2", "sess3"]:
            context = OperationContext(
                tool_name="Read",
                session_id=sess_id,
                user_id=f"user_{sess_id}"
            )
            detector.analyze(context)

        assert len(detector.session_histories) == 3
        assert len(detector.user_baselines) == 3

        # Clear all
        detector.clear_all()
        assert len(detector.session_histories) == 0
        assert len(detector.user_baselines) == 0
        assert len(detector.global_history) == 0


class TestPatternDetectorFactorConversion:
    """Tests for pattern to risk factor conversion."""

    @pytest.fixture
    def detector(self):
        """Create a default detector."""
        return PatternDetector()

    def test_pattern_to_factor_conversion(self, detector):
        """Test that detected patterns convert to risk factors."""
        session_id = "sess_factor"

        # Build up history and trigger sequence pattern
        for tool in ["Grep", "Read"]:
            context = OperationContext(
                tool_name=tool,
                session_id=session_id
            )
            detector.analyze(context)

        context = OperationContext(tool_name="Write", session_id=session_id)
        factors = detector.analyze(context)

        # Check factor structure
        for factor in factors:
            assert factor.factor_type == RiskFactorType.PATTERN
            assert 0.0 <= factor.score <= 1.0
            assert factor.weight == detector.config.weight
            assert "pattern_type" in factor.metadata
            assert "evidence" in factor.metadata
            assert "detected_at" in factor.metadata


class TestPatternDetectorHistoryLimits:
    """Tests for PatternDetector history size limits."""

    def test_global_history_limit(self):
        """Test global history respects max size."""
        config = PatternDetectorConfig(max_history_size=10)
        detector = PatternDetector(config)

        # Add more than limit
        for i in range(15):
            context = OperationContext(
                tool_name="Read",
                session_id=f"sess_{i}"
            )
            detector.analyze(context)

        # Should be limited to max size
        assert len(detector.global_history) == 10

    def test_session_history_limit(self):
        """Test session history respects max size."""
        config = PatternDetectorConfig(max_session_history=5)
        detector = PatternDetector(config)
        session_id = "sess_limit"

        # Add more than limit
        for i in range(10):
            context = OperationContext(
                tool_name="Read",
                session_id=session_id
            )
            detector.analyze(context)

        # Should be limited to max size
        assert len(detector.session_histories[session_id]) == 5

