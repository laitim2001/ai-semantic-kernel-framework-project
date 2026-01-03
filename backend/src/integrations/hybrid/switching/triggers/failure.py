# =============================================================================
# IPA Platform - Failure Trigger Detector
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 56: Mode Switcher & HITL - S56-2 Trigger Detectors
#
# Detects mode switch need based on consecutive failures.
#
# Key Features:
#   - Consecutive failure threshold detection
#   - Error pattern analysis
#   - Recovery mode suggestion
#   - Diagnostic mode triggering
#
# Dependencies:
#   - BaseTriggerDetector (src.integrations.hybrid.switching.triggers.base)
# =============================================================================

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.integrations.hybrid.intent.models import ExecutionMode

from ..models import ExecutionState, SwitchTrigger, SwitchTriggerType
from .base import BaseTriggerDetector, TriggerDetectorConfig

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class FailureConfig(TriggerDetectorConfig):
    """
    Configuration for failure trigger detector.

    Attributes:
        failure_threshold: Consecutive failures before triggering switch
        error_keywords: Keywords indicating errors in user input
        recovery_window_seconds: Window to consider for failure counting
        base_confidence: Base confidence for failure detection
        confidence_per_failure: Confidence increase per additional failure
    """

    failure_threshold: int = 3
    error_keywords: List[str] = field(
        default_factory=lambda: [
            "error",
            "failed",
            "not working",
            "broken",
            "doesn't work",
            "can't",
            "cannot",
            "stuck",
            "help",
            "wrong",
            "problem",
            "issue",
        ]
    )
    recovery_window_seconds: int = 300  # 5 minutes
    base_confidence: float = 0.7
    confidence_per_failure: float = 0.1


# =============================================================================
# Failure Trigger Detector
# =============================================================================


class FailureTriggerDetector(BaseTriggerDetector):
    """
    Detects mode switch based on consecutive failures.

    Monitors execution state for consecutive failures and suggests
    switching to a different mode for recovery or diagnosis.

    Behavior:
    - In WORKFLOW_MODE with failures: Switch to CHAT_MODE for diagnosis
    - In CHAT_MODE with failures: Switch to WORKFLOW_MODE for structured approach

    The detector also analyzes user input for error-related keywords
    that might indicate frustration or issues.

    Example:
        >>> detector = FailureTriggerDetector()
        >>> state = ExecutionState(
        ...     session_id="sess-123",
        ...     current_mode="workflow",
        ...     consecutive_failures=3
        ... )
        >>> trigger = await detector.detect(
        ...     ExecutionMode.WORKFLOW_MODE,
        ...     state,
        ...     "This workflow keeps failing"
        ... )
    """

    trigger_type = SwitchTriggerType.FAILURE

    def __init__(self, config: Optional[FailureConfig] = None) -> None:
        """
        Initialize failure trigger detector.

        Args:
            config: Failure detection configuration
        """
        # Failure detection has high priority (after user requests)
        cfg = config or FailureConfig()
        cfg.priority = 10
        super().__init__(cfg)
        self._failure_config: FailureConfig = self.config  # type: ignore

        # Compile error patterns
        self._error_patterns = [
            re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
            for kw in self._failure_config.error_keywords
        ]

    async def detect(
        self,
        current_mode: ExecutionMode,
        state: ExecutionState,
        new_input: str,
    ) -> Optional[SwitchTrigger]:
        """
        Detect if failure-based mode switch is needed.

        Args:
            current_mode: Current execution mode
            state: Current execution state
            new_input: New user input

        Returns:
            SwitchTrigger if switch is needed, None otherwise
        """
        if not self.is_enabled():
            return None

        # Count error keywords in input
        error_keyword_count = self._count_error_keywords(new_input)

        # Check if failures exceed threshold
        failures = state.consecutive_failures
        threshold = self._failure_config.failure_threshold

        logger.debug(
            f"Failure analysis: consecutive_failures={failures}, "
            f"threshold={threshold}, error_keywords={error_keyword_count}"
        )

        # Determine if switch is needed
        should_switch = False
        reason_parts = []

        if failures >= threshold:
            should_switch = True
            reason_parts.append(f"{failures} consecutive failures")

        # Error keywords can lower the threshold
        if error_keyword_count >= 2 and failures >= threshold - 1:
            should_switch = True
            reason_parts.append(f"error indicators in input ({error_keyword_count})")

        if not should_switch:
            return None

        # Determine target mode (opposite of current)
        if current_mode == ExecutionMode.WORKFLOW_MODE:
            target_mode = ExecutionMode.CHAT_MODE
            recovery_type = "diagnostic chat"
        else:
            target_mode = ExecutionMode.WORKFLOW_MODE
            recovery_type = "structured workflow"

        # Calculate confidence
        confidence = self._calculate_confidence(failures, error_keyword_count)

        reason = f"Failure recovery needed: {', '.join(reason_parts)}. Switching to {recovery_type}."

        self._log_detection(current_mode, target_mode, reason, confidence)

        return self._create_trigger(
            source_mode=current_mode,
            target_mode=target_mode,
            reason=reason,
            confidence=confidence,
            metadata={
                "consecutive_failures": failures,
                "error_keyword_count": error_keyword_count,
                "recovery_type": recovery_type,
            },
        )

    def _count_error_keywords(self, text: str) -> int:
        """Count error-related keywords in text."""
        return sum(1 for p in self._error_patterns if p.search(text))

    def _calculate_confidence(
        self, failures: int, error_keywords: int
    ) -> float:
        """Calculate detection confidence."""
        confidence = self._failure_config.base_confidence

        # Add confidence per failure above threshold
        extra_failures = failures - self._failure_config.failure_threshold
        if extra_failures > 0:
            confidence += extra_failures * self._failure_config.confidence_per_failure

        # Add small boost for error keywords
        confidence += error_keywords * 0.05

        return min(confidence, 0.95)
