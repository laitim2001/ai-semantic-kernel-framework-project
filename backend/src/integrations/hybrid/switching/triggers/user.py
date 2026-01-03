# =============================================================================
# IPA Platform - User Request Trigger Detector
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 56: Mode Switcher & HITL - S56-2 Trigger Detectors
#
# Detects explicit user requests for mode switching.
#
# Key Features:
#   - Explicit switch command detection
#   - Mode preference keywords
#   - High confidence for explicit requests
#
# Dependencies:
#   - BaseTriggerDetector (src.integrations.hybrid.switching.triggers.base)
# =============================================================================

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.integrations.hybrid.intent.models import ExecutionMode

from ..models import ExecutionState, SwitchTrigger, SwitchTriggerType
from .base import BaseTriggerDetector, TriggerDetectorConfig

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class UserRequestConfig(TriggerDetectorConfig):
    """
    Configuration for user request trigger detector.

    Attributes:
        switch_to_workflow_phrases: Phrases indicating switch to workflow
        switch_to_chat_phrases: Phrases indicating switch to chat
        explicit_command_prefix: Prefix for explicit mode commands
        confidence_explicit: Confidence for explicit commands
        confidence_implicit: Confidence for implicit requests
    """

    switch_to_workflow_phrases: List[str] = field(
        default_factory=lambda: [
            "switch to workflow",
            "use workflow mode",
            "workflow mode",
            "structured mode",
            "enable workflow",
            "start workflow",
            "switch to structured",
            "use structured mode",
        ]
    )
    switch_to_chat_phrases: List[str] = field(
        default_factory=lambda: [
            "switch to chat",
            "use chat mode",
            "chat mode",
            "conversational mode",
            "enable chat",
            "switch to conversational",
            "use conversational mode",
            "just chat",
            "simple chat",
        ]
    )
    explicit_command_prefix: str = "/mode"
    confidence_explicit: float = 1.0
    confidence_implicit: float = 0.85


# =============================================================================
# User Request Trigger Detector
# =============================================================================


class UserRequestTriggerDetector(BaseTriggerDetector):
    """
    Detects explicit user requests for mode switching.

    Analyzes user input for explicit mode switch commands or
    phrases indicating a desire to change modes.

    Priority: Highest (user requests always take precedence)

    Examples of detected patterns:
    - "/mode workflow" - Explicit command
    - "switch to chat mode" - Implicit request
    - "use workflow mode please" - Polite implicit request

    Example:
        >>> detector = UserRequestTriggerDetector()
        >>> trigger = await detector.detect(
        ...     ExecutionMode.CHAT_MODE,
        ...     state,
        ...     "/mode workflow"
        ... )
        >>> trigger.confidence  # 1.0 for explicit commands
    """

    trigger_type = SwitchTriggerType.USER_REQUEST

    def __init__(self, config: Optional[UserRequestConfig] = None) -> None:
        """
        Initialize user request trigger detector.

        Args:
            config: User request detection configuration
        """
        # User requests have highest priority
        cfg = config or UserRequestConfig()
        cfg.priority = 1  # Highest priority
        super().__init__(cfg)
        self._user_config: UserRequestConfig = self.config  # type: ignore

        # Compile patterns
        self._workflow_patterns = [
            re.compile(r"\b" + re.escape(p) + r"\b", re.IGNORECASE)
            for p in self._user_config.switch_to_workflow_phrases
        ]
        self._chat_patterns = [
            re.compile(r"\b" + re.escape(p) + r"\b", re.IGNORECASE)
            for p in self._user_config.switch_to_chat_phrases
        ]

        # Compile explicit command pattern
        prefix = re.escape(self._user_config.explicit_command_prefix)
        self._explicit_pattern = re.compile(
            rf"{prefix}\s+(workflow|chat|structured|conversational)",
            re.IGNORECASE,
        )

    async def detect(
        self,
        current_mode: ExecutionMode,
        state: ExecutionState,
        new_input: str,
    ) -> Optional[SwitchTrigger]:
        """
        Detect if user explicitly requests mode switch.

        Args:
            current_mode: Current execution mode
            state: Current execution state
            new_input: New user input

        Returns:
            SwitchTrigger if switch is requested, None otherwise
        """
        if not self.is_enabled():
            return None

        # Check for explicit command first
        explicit_match = self._explicit_pattern.search(new_input)
        if explicit_match:
            target_mode_str = explicit_match.group(1).lower()
            target_mode = self._parse_mode(target_mode_str)

            if target_mode and target_mode != current_mode:
                reason = f"Explicit mode command: {self._user_config.explicit_command_prefix} {target_mode_str}"

                self._log_detection(
                    current_mode, target_mode, reason,
                    self._user_config.confidence_explicit,
                )

                return self._create_trigger(
                    source_mode=current_mode,
                    target_mode=target_mode,
                    reason=reason,
                    confidence=self._user_config.confidence_explicit,
                    metadata={"explicit_command": True},
                )

        # Check for implicit requests
        target_mode, matched_phrase = self._check_implicit_request(new_input)
        if target_mode and target_mode != current_mode:
            reason = f"User request: '{matched_phrase}'"

            self._log_detection(
                current_mode, target_mode, reason,
                self._user_config.confidence_implicit,
            )

            return self._create_trigger(
                source_mode=current_mode,
                target_mode=target_mode,
                reason=reason,
                confidence=self._user_config.confidence_implicit,
                metadata={"matched_phrase": matched_phrase},
            )

        return None

    def _parse_mode(self, mode_str: str) -> Optional[ExecutionMode]:
        """Parse mode string to ExecutionMode."""
        mode_map = {
            "workflow": ExecutionMode.WORKFLOW_MODE,
            "structured": ExecutionMode.WORKFLOW_MODE,
            "chat": ExecutionMode.CHAT_MODE,
            "conversational": ExecutionMode.CHAT_MODE,
        }
        return mode_map.get(mode_str.lower())

    def _check_implicit_request(
        self, text: str
    ) -> Tuple[Optional[ExecutionMode], Optional[str]]:
        """Check for implicit mode switch request."""
        # Check workflow patterns
        for i, pattern in enumerate(self._workflow_patterns):
            if pattern.search(text):
                return (
                    ExecutionMode.WORKFLOW_MODE,
                    self._user_config.switch_to_workflow_phrases[i],
                )

        # Check chat patterns
        for i, pattern in enumerate(self._chat_patterns):
            if pattern.search(text):
                return (
                    ExecutionMode.CHAT_MODE,
                    self._user_config.switch_to_chat_phrases[i],
                )

        return None, None
