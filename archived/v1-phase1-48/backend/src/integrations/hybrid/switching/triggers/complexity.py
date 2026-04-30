# =============================================================================
# IPA Platform - Complexity Trigger Detector
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 56: Mode Switcher & HITL - S56-2 Trigger Detectors
#
# Detects mode switch need based on task complexity changes.
#
# Key Features:
#   - Keyword-based complexity detection
#   - Step count threshold analysis
#   - Tool usage pattern recognition
#   - Workflow indicator detection
#
# Dependencies:
#   - BaseTriggerDetector (src.integrations.hybrid.switching.triggers.base)
# =============================================================================

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from src.integrations.hybrid.intent.models import ExecutionMode

from ..models import ExecutionState, SwitchTrigger, SwitchTriggerType
from .base import BaseTriggerDetector, TriggerDetectorConfig

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class ComplexityConfig(TriggerDetectorConfig):
    """
    Configuration for complexity trigger detector.

    Attributes:
        step_threshold: Number of steps before suggesting workflow mode
        tool_threshold: Number of tool calls before suggesting workflow mode
        multi_step_keywords: Keywords indicating multi-step tasks
        workflow_keywords: Keywords suggesting structured workflow
        chat_keywords: Keywords suggesting simple conversation
        base_confidence: Base confidence for complexity detection
        keyword_confidence_boost: Confidence boost per keyword match
    """

    step_threshold: int = 3
    tool_threshold: int = 2
    multi_step_keywords: List[str] = field(
        default_factory=lambda: [
            "step by step",
            "steps",
            "first",
            "then",
            "after that",
            "finally",
            "workflow",
            "process",
            "procedure",
            "sequence",
            "multi-step",
            "multiple steps",
        ]
    )
    workflow_keywords: List[str] = field(
        default_factory=lambda: [
            "create workflow",
            "automate",
            "schedule",
            "batch",
            "pipeline",
            "orchestrate",
            "deploy",
            "integrate",
        ]
    )
    chat_keywords: List[str] = field(
        default_factory=lambda: [
            "what is",
            "how do i",
            "explain",
            "tell me",
            "help me understand",
            "quick question",
            "just",
            "simple",
        ]
    )
    base_confidence: float = 0.6
    keyword_confidence_boost: float = 0.1


# =============================================================================
# Complexity Trigger Detector
# =============================================================================


class ComplexityTriggerDetector(BaseTriggerDetector):
    """
    Detects mode switch based on task complexity.

    Analyzes user input and execution state to determine if the task
    complexity warrants a mode switch between Chat and Workflow modes.

    Switches to WORKFLOW_MODE when:
    - Multi-step task keywords detected
    - Step count exceeds threshold
    - Multiple tool calls expected

    Switches to CHAT_MODE when:
    - Simple conversational patterns detected
    - Task has been simplified
    - User requests direct interaction

    Example:
        >>> detector = ComplexityTriggerDetector()
        >>> trigger = await detector.detect(
        ...     ExecutionMode.CHAT_MODE,
        ...     state,
        ...     "I need to create a step by step workflow for data processing"
        ... )
        >>> if trigger:
        ...     print(f"Switch to {trigger.target_mode}")
    """

    trigger_type = SwitchTriggerType.COMPLEXITY

    def __init__(self, config: Optional[ComplexityConfig] = None) -> None:
        """
        Initialize complexity trigger detector.

        Args:
            config: Complexity detection configuration
        """
        super().__init__(config or ComplexityConfig())
        self._complexity_config: ComplexityConfig = self.config  # type: ignore

        # Pre-compile keyword patterns for efficiency
        self._multi_step_patterns = self._compile_patterns(
            self._complexity_config.multi_step_keywords
        )
        self._workflow_patterns = self._compile_patterns(
            self._complexity_config.workflow_keywords
        )
        self._chat_patterns = self._compile_patterns(
            self._complexity_config.chat_keywords
        )

    def _compile_patterns(self, keywords: List[str]) -> List[re.Pattern]:
        """Compile keyword patterns for efficient matching."""
        return [
            re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
            for kw in keywords
        ]

    async def detect(
        self,
        current_mode: ExecutionMode,
        state: ExecutionState,
        new_input: str,
    ) -> Optional[SwitchTrigger]:
        """
        Detect if complexity-based mode switch is needed.

        Args:
            current_mode: Current execution mode
            state: Current execution state
            new_input: New user input

        Returns:
            SwitchTrigger if switch is needed, None otherwise
        """
        if not self.is_enabled():
            return None

        input_lower = new_input.lower()

        # Analyze complexity signals
        multi_step_matches = self._count_pattern_matches(
            input_lower, self._multi_step_patterns
        )
        workflow_matches = self._count_pattern_matches(
            input_lower, self._workflow_patterns
        )
        chat_matches = self._count_pattern_matches(
            input_lower, self._chat_patterns
        )

        # Calculate complexity score
        complexity_score = self._calculate_complexity_score(
            multi_step_matches=multi_step_matches,
            workflow_matches=workflow_matches,
            chat_matches=chat_matches,
            step_count=state.step_count,
            tool_call_count=state.tool_call_count,
        )

        logger.debug(
            f"Complexity analysis: score={complexity_score:.2f}, "
            f"multi_step={multi_step_matches}, workflow={workflow_matches}, "
            f"chat={chat_matches}"
        )

        # Determine target mode based on complexity
        if current_mode == ExecutionMode.CHAT_MODE:
            # In chat mode, check if should switch to workflow
            if complexity_score >= 0.7:
                confidence = self._calculate_confidence(
                    multi_step_matches, workflow_matches
                )
                reason = self._build_switch_to_workflow_reason(
                    multi_step_matches, workflow_matches, state
                )

                self._log_detection(
                    current_mode, ExecutionMode.WORKFLOW_MODE, reason, confidence
                )

                return self._create_trigger(
                    source_mode=current_mode,
                    target_mode=ExecutionMode.WORKFLOW_MODE,
                    reason=reason,
                    confidence=confidence,
                    metadata={
                        "complexity_score": complexity_score,
                        "multi_step_matches": multi_step_matches,
                        "workflow_matches": workflow_matches,
                        "step_count": state.step_count,
                    },
                )

        elif current_mode == ExecutionMode.WORKFLOW_MODE:
            # In workflow mode, check if should switch to chat
            if complexity_score <= 0.3 and chat_matches > 0:
                confidence = self._calculate_confidence(chat_matches, 0)
                reason = self._build_switch_to_chat_reason(chat_matches)

                self._log_detection(
                    current_mode, ExecutionMode.CHAT_MODE, reason, confidence
                )

                return self._create_trigger(
                    source_mode=current_mode,
                    target_mode=ExecutionMode.CHAT_MODE,
                    reason=reason,
                    confidence=confidence,
                    metadata={
                        "complexity_score": complexity_score,
                        "chat_matches": chat_matches,
                    },
                )

        return None

    def _count_pattern_matches(
        self, text: str, patterns: List[re.Pattern]
    ) -> int:
        """Count pattern matches in text."""
        return sum(1 for p in patterns if p.search(text))

    def _calculate_complexity_score(
        self,
        multi_step_matches: int,
        workflow_matches: int,
        chat_matches: int,
        step_count: int,
        tool_call_count: int,
    ) -> float:
        """
        Calculate complexity score from various signals.

        Returns a score between 0.0 (simple) and 1.0 (complex).
        """
        score = 0.0

        # Keyword-based scoring (more generous to trigger on keywords)
        score += min(multi_step_matches * 0.35, 0.7)
        score += min(workflow_matches * 0.35, 0.7)  # Workflow keywords are strong indicators
        score -= min(chat_matches * 0.2, 0.4)

        # State-based scoring
        if step_count >= self._complexity_config.step_threshold:
            score += 0.3
        if tool_call_count >= self._complexity_config.tool_threshold:
            score += 0.15

        # Clamp to 0-1
        return max(min(score, 1.0), 0.0)

    def _calculate_confidence(
        self, primary_matches: int, secondary_matches: int
    ) -> float:
        """Calculate detection confidence."""
        confidence = self._complexity_config.base_confidence
        confidence += primary_matches * self._complexity_config.keyword_confidence_boost
        confidence += secondary_matches * (
            self._complexity_config.keyword_confidence_boost / 2
        )
        return min(confidence, 0.95)

    def _build_switch_to_workflow_reason(
        self,
        multi_step_matches: int,
        workflow_matches: int,
        state: ExecutionState,
    ) -> str:
        """Build reason string for switching to workflow mode."""
        reasons = []

        if multi_step_matches > 0:
            reasons.append(f"{multi_step_matches} multi-step indicators")
        if workflow_matches > 0:
            reasons.append(f"{workflow_matches} workflow keywords")
        if state.step_count >= self._complexity_config.step_threshold:
            reasons.append(f"step count ({state.step_count}) exceeds threshold")

        return "Complex task detected: " + ", ".join(reasons) if reasons else "Complex task pattern"

    def _build_switch_to_chat_reason(self, chat_matches: int) -> str:
        """Build reason string for switching to chat mode."""
        return f"Simple conversational pattern detected ({chat_matches} indicators)"
