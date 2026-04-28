# =============================================================================
# IPA Platform - Base Trigger Detector
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 56: Mode Switcher & HITL - S56-2 Trigger Detectors
#
# Abstract base class for trigger detectors.
#
# Key Features:
#   - Common interface for all trigger detectors
#   - Configurable detection parameters
#   - Logging and metrics support
#
# Dependencies:
#   - TriggerDetectorProtocol (src.integrations.hybrid.switching.switcher)
#   - SwitchTrigger, ExecutionState (src.integrations.hybrid.switching.models)
# =============================================================================

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from src.integrations.hybrid.intent.models import ExecutionMode

from ..models import ExecutionState, SwitchTrigger, SwitchTriggerType

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class TriggerDetectorConfig:
    """
    Base configuration for trigger detectors.

    Attributes:
        enabled: Whether the detector is enabled
        priority: Detection priority (lower = higher priority)
        min_confidence: Minimum confidence threshold
        cooldown_seconds: Cooldown between detections
        metadata: Additional configuration metadata
    """

    enabled: bool = True
    priority: int = 100
    min_confidence: float = 0.5
    cooldown_seconds: int = 60
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enabled": self.enabled,
            "priority": self.priority,
            "min_confidence": self.min_confidence,
            "cooldown_seconds": self.cooldown_seconds,
            "metadata": self.metadata,
        }


# =============================================================================
# Base Trigger Detector
# =============================================================================


class BaseTriggerDetector(ABC):
    """
    Abstract base class for trigger detectors.

    Provides common functionality for all trigger detectors including
    configuration, logging, and the detection interface.

    Subclasses must implement the detect() method.

    Attributes:
        config: Detector configuration
        name: Detector name
        trigger_type: Type of trigger this detector produces

    Example:
        >>> class MyDetector(BaseTriggerDetector):
        ...     trigger_type = SwitchTriggerType.COMPLEXITY
        ...
        ...     async def detect(
        ...         self, current_mode, state, new_input
        ...     ) -> Optional[SwitchTrigger]:
        ...         # Detection logic here
        ...         return None
    """

    # Subclasses should set this
    trigger_type: SwitchTriggerType = SwitchTriggerType.MANUAL

    def __init__(self, config: Optional[TriggerDetectorConfig] = None) -> None:
        """
        Initialize base trigger detector.

        Args:
            config: Detector configuration
        """
        self.config = config or TriggerDetectorConfig()
        self.name = self.__class__.__name__
        self._detection_count = 0
        self._last_detection_time: Optional[float] = None

        logger.debug(f"Initialized {self.name} with priority {self.config.priority}")

    @abstractmethod
    async def detect(
        self,
        current_mode: ExecutionMode,
        state: ExecutionState,
        new_input: str,
    ) -> Optional[SwitchTrigger]:
        """
        Detect if mode switch is needed.

        Args:
            current_mode: Current execution mode
            state: Current execution state
            new_input: New user input

        Returns:
            SwitchTrigger if switch is needed, None otherwise
        """
        ...

    def is_enabled(self) -> bool:
        """Check if detector is enabled."""
        return self.config.enabled

    def get_priority(self) -> int:
        """Get detector priority."""
        return self.config.priority

    def get_detection_count(self) -> int:
        """Get total detection count."""
        return self._detection_count

    def _create_trigger(
        self,
        source_mode: ExecutionMode,
        target_mode: ExecutionMode,
        reason: str,
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SwitchTrigger:
        """
        Helper method to create a switch trigger.

        Args:
            source_mode: Source execution mode
            target_mode: Target execution mode
            reason: Reason for the switch
            confidence: Confidence level (0.0 to 1.0)
            metadata: Additional metadata

        Returns:
            SwitchTrigger instance
        """
        self._detection_count += 1

        return SwitchTrigger(
            trigger_type=self.trigger_type,
            source_mode=source_mode.value,
            target_mode=target_mode.value,
            reason=reason,
            confidence=min(max(confidence, 0.0), 1.0),  # Clamp to 0-1
            metadata=metadata or {},
        )

    def _log_detection(
        self,
        source_mode: ExecutionMode,
        target_mode: ExecutionMode,
        reason: str,
        confidence: float,
    ) -> None:
        """Log a detection event."""
        logger.info(
            f"{self.name} detected trigger: "
            f"{source_mode.value} -> {target_mode.value} "
            f"(confidence: {confidence:.2f}, reason: {reason})"
        )

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"trigger_type={self.trigger_type.value}, "
            f"enabled={self.config.enabled}, "
            f"priority={self.config.priority})"
        )
