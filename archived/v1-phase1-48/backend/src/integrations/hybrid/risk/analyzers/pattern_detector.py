# =============================================================================
# IPA Platform - Pattern Detector
# =============================================================================
# Sprint 55: Risk Assessment Engine - S55-3
#
# Detects risk patterns including:
#   - Frequency anomalies (unusual operation rates)
#   - Behavior deviations (unexpected operation types)
#   - Risk escalation patterns (increasing risk over time)
#   - Temporal patterns (suspicious timing)
#
# Dependencies:
#   - RiskFactor, RiskFactorType, OperationContext
#     (src.integrations.hybrid.risk.models)
# =============================================================================

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Deque, Dict, List, Optional, Tuple

from ..models import OperationContext, RiskFactor, RiskFactorType, RiskLevel


class PatternType(str, Enum):
    """Types of detected patterns."""

    FREQUENCY_ANOMALY = "frequency_anomaly"
    BEHAVIOR_DEVIATION = "behavior_deviation"
    RISK_ESCALATION = "risk_escalation"
    TEMPORAL_ANOMALY = "temporal_anomaly"
    TOOL_SEQUENCE = "tool_sequence"


@dataclass
class OperationRecord:
    """Record of an operation for pattern analysis."""

    timestamp: datetime
    tool_name: str
    risk_score: float
    risk_level: RiskLevel
    user_id: Optional[str]
    session_id: Optional[str]
    metadata: Dict[str, any] = field(default_factory=dict)


@dataclass
class DetectedPattern:
    """A detected risk pattern."""

    pattern_type: PatternType
    severity: float  # 0.0 - 1.0
    description: str
    evidence: Dict[str, any]
    detected_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PatternDetectorConfig:
    """Configuration for pattern detection."""

    # Frequency detection
    frequency_window_seconds: int = 60  # Time window for frequency analysis
    max_operations_per_window: int = 20  # Max operations before flagging
    burst_threshold: int = 5  # Operations in 5 seconds = burst

    # Behavior deviation
    baseline_window_hours: int = 24  # Hours of history for baseline
    deviation_threshold: float = 0.3  # 30% deviation from baseline

    # Risk escalation
    escalation_window_count: int = 10  # Operations to check for escalation
    escalation_threshold: float = 0.15  # Score increase threshold

    # Temporal anomalies
    off_hours_start: int = 22  # 10 PM
    off_hours_end: int = 6  # 6 AM

    # Suspicious tool sequences
    suspicious_sequences: List[Tuple[str, str, str]] = field(default_factory=lambda: [
        ("Grep", "Read", "Write"),      # Search → Read → Modify
        ("Read", "Edit", "Bash"),       # Read → Edit → Execute
        ("Glob", "Read", "MultiEdit"),  # Find → Read → Bulk edit
    ])

    # History limits
    max_history_size: int = 1000  # Max operations to keep in memory
    max_session_history: int = 100  # Max operations per session

    # Weight for pattern-based risk factors
    weight: float = 0.35


class PatternDetector:
    """
    Detects risk patterns in operation sequences.

    Analyzes operation history to identify anomalies, deviations,
    and suspicious patterns that may indicate elevated risk.

    Attributes:
        config: Configuration for pattern detection
        global_history: Global operation history
        session_histories: Per-session operation histories
        user_baselines: User behavior baselines

    Example:
        >>> detector = PatternDetector()
        >>> context = OperationContext(tool_name="Bash", session_id="sess123")
        >>> factors = detector.analyze(context)
        >>> for factor in factors:
        ...     print(f"{factor.description}: {factor.score}")
    """

    def __init__(self, config: Optional[PatternDetectorConfig] = None):
        """
        Initialize PatternDetector with configuration.

        Args:
            config: Configuration for pattern detection
        """
        self.config = config or PatternDetectorConfig()
        self.global_history: Deque[OperationRecord] = deque(
            maxlen=self.config.max_history_size
        )
        self.session_histories: Dict[str, Deque[OperationRecord]] = {}
        self.user_baselines: Dict[str, Dict[str, float]] = {}

    def analyze(
        self,
        context: OperationContext,
        current_risk_score: float = 0.0,
        current_risk_level: RiskLevel = RiskLevel.LOW
    ) -> List[RiskFactor]:
        """
        Analyze operation context for risk patterns.

        Checks for frequency anomalies, behavior deviations,
        risk escalation, and other suspicious patterns.

        Args:
            context: The operation context to analyze
            current_risk_score: Current risk score for this operation
            current_risk_level: Current risk level for this operation

        Returns:
            List of identified risk factors from detected patterns
        """
        factors: List[RiskFactor] = []

        # Get session history
        session_id = context.session_id or "default"
        session_history = self._get_session_history(session_id)

        # Detect frequency anomalies
        frequency_pattern = self._detect_frequency_anomaly(session_history)
        if frequency_pattern:
            factors.append(self._pattern_to_factor(frequency_pattern))

        # Detect behavior deviation
        if context.user_id:
            deviation_pattern = self._detect_behavior_deviation(
                context.user_id, context.tool_name
            )
            if deviation_pattern:
                factors.append(self._pattern_to_factor(deviation_pattern))

        # Detect risk escalation
        escalation_pattern = self._detect_risk_escalation(
            session_history, current_risk_score
        )
        if escalation_pattern:
            factors.append(self._pattern_to_factor(escalation_pattern))

        # Detect temporal anomalies
        temporal_pattern = self._detect_temporal_anomaly()
        if temporal_pattern:
            factors.append(self._pattern_to_factor(temporal_pattern))

        # Detect suspicious tool sequences
        sequence_pattern = self._detect_tool_sequence(session_history, context.tool_name)
        if sequence_pattern:
            factors.append(self._pattern_to_factor(sequence_pattern))

        # Record this operation
        self._record_operation(
            context, current_risk_score, current_risk_level, session_id
        )

        return factors

    def _get_session_history(self, session_id: str) -> Deque[OperationRecord]:
        """Get or create session history."""
        if session_id not in self.session_histories:
            self.session_histories[session_id] = deque(
                maxlen=self.config.max_session_history
            )
        return self.session_histories[session_id]

    def _detect_frequency_anomaly(
        self,
        history: Deque[OperationRecord]
    ) -> Optional[DetectedPattern]:
        """Detect unusual operation frequency."""
        if len(history) < 2:
            return None

        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.config.frequency_window_seconds)
        burst_start = now - timedelta(seconds=5)

        # Count operations in window
        window_ops = sum(1 for op in history if op.timestamp >= window_start)
        burst_ops = sum(1 for op in history if op.timestamp >= burst_start)

        # Check for burst
        if burst_ops >= self.config.burst_threshold:
            return DetectedPattern(
                pattern_type=PatternType.FREQUENCY_ANOMALY,
                severity=0.7,
                description=f"Burst detected: {burst_ops} operations in 5 seconds",
                evidence={
                    "burst_count": burst_ops,
                    "threshold": self.config.burst_threshold,
                    "window_seconds": 5
                }
            )

        # Check for high frequency
        if window_ops >= self.config.max_operations_per_window:
            return DetectedPattern(
                pattern_type=PatternType.FREQUENCY_ANOMALY,
                severity=0.6,
                description=f"High frequency: {window_ops} operations in {self.config.frequency_window_seconds}s",
                evidence={
                    "operation_count": window_ops,
                    "threshold": self.config.max_operations_per_window,
                    "window_seconds": self.config.frequency_window_seconds
                }
            )

        return None

    def _detect_behavior_deviation(
        self,
        user_id: str,
        tool_name: str
    ) -> Optional[DetectedPattern]:
        """Detect deviation from user's baseline behavior."""
        if user_id not in self.user_baselines:
            return None

        baseline = self.user_baselines[user_id]
        if not baseline:
            return None

        # Check if tool usage deviates significantly from baseline
        tool_baseline = baseline.get(tool_name, 0.0)
        total_ops = sum(baseline.values())

        if total_ops < 10:
            return None  # Not enough data for baseline

        expected_rate = tool_baseline / total_ops if total_ops > 0 else 0

        # If this is a rarely-used tool by this user
        if expected_rate < 0.05 and tool_baseline < 5:
            return DetectedPattern(
                pattern_type=PatternType.BEHAVIOR_DEVIATION,
                severity=0.5,
                description=f"Unusual tool usage: {tool_name} (rarely used by this user)",
                evidence={
                    "user_id": user_id,
                    "tool_name": tool_name,
                    "historical_usage": tool_baseline,
                    "expected_rate": expected_rate
                }
            )

        return None

    def _detect_risk_escalation(
        self,
        history: Deque[OperationRecord],
        current_score: float
    ) -> Optional[DetectedPattern]:
        """Detect escalating risk pattern."""
        if len(history) < self.config.escalation_window_count:
            return None

        # Get recent scores
        recent = list(history)[-self.config.escalation_window_count:]
        scores = [op.risk_score for op in recent]

        # Check for consistent increase
        increases = sum(
            1 for i in range(1, len(scores))
            if scores[i] > scores[i-1]
        )

        # If most operations show increasing risk
        if increases >= len(scores) * 0.7:
            avg_increase = (scores[-1] - scores[0]) / len(scores)
            if avg_increase >= self.config.escalation_threshold:
                return DetectedPattern(
                    pattern_type=PatternType.RISK_ESCALATION,
                    severity=0.75,
                    description=f"Risk escalation detected: scores increasing by {avg_increase:.2f} per operation",
                    evidence={
                        "score_trend": scores,
                        "increase_count": increases,
                        "average_increase": avg_increase,
                        "current_score": current_score
                    }
                )

        return None

    def _detect_temporal_anomaly(self) -> Optional[DetectedPattern]:
        """Detect operations during unusual times."""
        now = datetime.utcnow()
        current_hour = now.hour

        # Check if current time is during off-hours
        if (current_hour >= self.config.off_hours_start or
                current_hour < self.config.off_hours_end):
            return DetectedPattern(
                pattern_type=PatternType.TEMPORAL_ANOMALY,
                severity=0.4,
                description=f"Operation during off-hours ({current_hour:02d}:00)",
                evidence={
                    "current_hour": current_hour,
                    "off_hours_start": self.config.off_hours_start,
                    "off_hours_end": self.config.off_hours_end
                }
            )

        return None

    def _detect_tool_sequence(
        self,
        history: Deque[OperationRecord],
        current_tool: str
    ) -> Optional[DetectedPattern]:
        """Detect suspicious tool sequences."""
        if len(history) < 2:
            return None

        # Get recent tools
        recent_tools = [op.tool_name for op in list(history)[-2:]]
        recent_tools.append(current_tool)

        # Check against suspicious sequences
        for seq in self.config.suspicious_sequences:
            if len(recent_tools) >= len(seq):
                # Check if the end of recent_tools matches the sequence
                window = recent_tools[-len(seq):]
                if tuple(window) == seq:
                    return DetectedPattern(
                        pattern_type=PatternType.TOOL_SEQUENCE,
                        severity=0.55,
                        description=f"Suspicious tool sequence detected: {' → '.join(seq)}",
                        evidence={
                            "sequence": seq,
                            "matched_tools": window
                        }
                    )

        return None

    def _pattern_to_factor(self, pattern: DetectedPattern) -> RiskFactor:
        """Convert a detected pattern to a risk factor."""
        return RiskFactor(
            factor_type=RiskFactorType.PATTERN,
            score=pattern.severity,
            weight=self.config.weight,
            description=pattern.description,
            source=pattern.pattern_type.value,
            metadata={
                "pattern_type": pattern.pattern_type.value,
                "evidence": pattern.evidence,
                "detected_at": pattern.detected_at.isoformat()
            }
        )

    def _record_operation(
        self,
        context: OperationContext,
        risk_score: float,
        risk_level: RiskLevel,
        session_id: str
    ) -> None:
        """Record an operation in history."""
        record = OperationRecord(
            timestamp=datetime.utcnow(),
            tool_name=context.tool_name,
            risk_score=risk_score,
            risk_level=risk_level,
            user_id=context.user_id,
            session_id=session_id
        )

        # Add to global history
        self.global_history.append(record)

        # Add to session history
        session_history = self._get_session_history(session_id)
        session_history.append(record)

        # Update user baseline
        if context.user_id:
            self._update_user_baseline(context.user_id, context.tool_name)

    def _update_user_baseline(self, user_id: str, tool_name: str) -> None:
        """Update user's tool usage baseline."""
        if user_id not in self.user_baselines:
            self.user_baselines[user_id] = {}

        baseline = self.user_baselines[user_id]
        baseline[tool_name] = baseline.get(tool_name, 0) + 1

    def get_session_patterns(self, session_id: str) -> List[DetectedPattern]:
        """
        Get all patterns detected in a session.

        Args:
            session_id: Session identifier

        Returns:
            List of detected patterns
        """
        if session_id not in self.session_histories:
            return []

        history = self.session_histories[session_id]
        patterns: List[DetectedPattern] = []

        # Run all detection methods
        freq_pattern = self._detect_frequency_anomaly(history)
        if freq_pattern:
            patterns.append(freq_pattern)

        if history:
            last_op = history[-1]
            escalation = self._detect_risk_escalation(history, last_op.risk_score)
            if escalation:
                patterns.append(escalation)

        return patterns

    def clear_session(self, session_id: str) -> None:
        """
        Clear session history.

        Args:
            session_id: Session identifier
        """
        if session_id in self.session_histories:
            del self.session_histories[session_id]

    def clear_all(self) -> None:
        """Clear all histories and baselines."""
        self.global_history.clear()
        self.session_histories.clear()
        self.user_baselines.clear()

    def get_user_baseline(self, user_id: str) -> Dict[str, float]:
        """
        Get user's tool usage baseline.

        Args:
            user_id: User identifier

        Returns:
            Dictionary of tool names to usage counts
        """
        return self.user_baselines.get(user_id, {})
