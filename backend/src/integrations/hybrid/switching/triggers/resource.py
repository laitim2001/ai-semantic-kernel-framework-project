# =============================================================================
# IPA Platform - Resource Trigger Detector
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 56: Mode Switcher & HITL - S56-2 Trigger Detectors
#
# Detects mode switch need based on resource constraints.
#
# Key Features:
#   - Token usage threshold detection
#   - Memory usage monitoring
#   - Time constraint analysis
#   - Context window management
#
# Dependencies:
#   - BaseTriggerDetector (src.integrations.hybrid.switching.triggers.base)
# =============================================================================

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from src.integrations.hybrid.intent.models import ExecutionMode

from ..models import ExecutionState, SwitchTrigger, SwitchTriggerType
from .base import BaseTriggerDetector, TriggerDetectorConfig

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class ResourceConfig(TriggerDetectorConfig):
    """
    Configuration for resource trigger detector.

    Attributes:
        token_threshold: Token usage percentage threshold (0-1)
        memory_threshold: Memory usage percentage threshold (0-1)
        context_threshold: Context window usage percentage threshold (0-1)
        time_threshold_seconds: Maximum time before suggesting switch
        base_confidence: Base confidence for resource detection
    """

    token_threshold: float = 0.8
    memory_threshold: float = 0.85
    context_threshold: float = 0.75
    time_threshold_seconds: int = 600  # 10 minutes
    base_confidence: float = 0.75


# =============================================================================
# Resource Trigger Detector
# =============================================================================


class ResourceTriggerDetector(BaseTriggerDetector):
    """
    Detects mode switch based on resource constraints.

    Monitors execution state for resource usage and suggests
    mode switches to optimize resource utilization.

    Resource types monitored:
    - token_usage: Token consumption
    - memory_usage: Memory consumption
    - context_usage: Context window utilization
    - execution_time: Time spent in current mode

    Behavior:
    - High resource usage in CHAT_MODE: Switch to WORKFLOW for efficiency
    - High resource usage in WORKFLOW_MODE: Switch to CHAT for simplification

    Example:
        >>> detector = ResourceTriggerDetector()
        >>> state = ExecutionState(
        ...     session_id="sess-123",
        ...     current_mode="chat",
        ...     resource_usage={"token_usage": 0.85}
        ... )
        >>> trigger = await detector.detect(
        ...     ExecutionMode.CHAT_MODE,
        ...     state,
        ...     "Continue the conversation"
        ... )
    """

    trigger_type = SwitchTriggerType.RESOURCE

    def __init__(self, config: Optional[ResourceConfig] = None) -> None:
        """
        Initialize resource trigger detector.

        Args:
            config: Resource detection configuration
        """
        cfg = config or ResourceConfig()
        cfg.priority = 50  # Medium priority
        super().__init__(cfg)
        self._resource_config: ResourceConfig = self.config  # type: ignore

    async def detect(
        self,
        current_mode: ExecutionMode,
        state: ExecutionState,
        new_input: str,
    ) -> Optional[SwitchTrigger]:
        """
        Detect if resource-based mode switch is needed.

        Args:
            current_mode: Current execution mode
            state: Current execution state
            new_input: New user input

        Returns:
            SwitchTrigger if switch is needed, None otherwise
        """
        if not self.is_enabled():
            return None

        resource_usage = state.resource_usage or {}

        # Analyze resource constraints
        constraints = self._analyze_constraints(resource_usage)

        if not constraints:
            return None

        # Determine target mode based on current mode and constraints
        target_mode, reason = self._determine_target_mode(
            current_mode, constraints
        )

        if target_mode is None or target_mode == current_mode:
            return None

        # Calculate confidence based on constraint severity
        confidence = self._calculate_confidence(constraints)

        self._log_detection(current_mode, target_mode, reason, confidence)

        return self._create_trigger(
            source_mode=current_mode,
            target_mode=target_mode,
            reason=reason,
            confidence=confidence,
            metadata={
                "constraints": constraints,
                "resource_usage": resource_usage,
            },
        )

    def _analyze_constraints(
        self, resource_usage: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Analyze resource usage for constraints.

        Returns dict of constraint name -> usage percentage for any
        resources exceeding their thresholds.
        """
        constraints = {}

        # Check token usage
        token_usage = resource_usage.get("token_usage", 0)
        if token_usage >= self._resource_config.token_threshold:
            constraints["token_usage"] = token_usage

        # Check memory usage
        memory_usage = resource_usage.get("memory_usage", 0)
        if memory_usage >= self._resource_config.memory_threshold:
            constraints["memory_usage"] = memory_usage

        # Check context usage
        context_usage = resource_usage.get("context_usage", 0)
        if context_usage >= self._resource_config.context_threshold:
            constraints["context_usage"] = context_usage

        logger.debug(
            f"Resource analysis: token={token_usage:.2f}, "
            f"memory={memory_usage:.2f}, context={context_usage:.2f}, "
            f"constraints={list(constraints.keys())}"
        )

        return constraints

    def _determine_target_mode(
        self,
        current_mode: ExecutionMode,
        constraints: Dict[str, float],
    ) -> tuple[Optional[ExecutionMode], str]:
        """
        Determine target mode based on constraints.

        Returns (target_mode, reason) tuple.
        """
        # Build constraint description
        constraint_desc = ", ".join(
            f"{k}={v:.0%}" for k, v in constraints.items()
        )

        if current_mode == ExecutionMode.CHAT_MODE:
            # High resource in chat -> switch to workflow for efficiency
            if "token_usage" in constraints or "context_usage" in constraints:
                return (
                    ExecutionMode.WORKFLOW_MODE,
                    f"High resource usage in chat mode ({constraint_desc}). "
                    "Switching to workflow for efficient processing.",
                )

        elif current_mode == ExecutionMode.WORKFLOW_MODE:
            # High resource in workflow -> switch to chat for simplification
            if "memory_usage" in constraints:
                return (
                    ExecutionMode.CHAT_MODE,
                    f"High memory usage in workflow mode ({constraint_desc}). "
                    "Switching to chat for lighter operation.",
                )

        # Default: stay in current mode
        return None, ""

    def _calculate_confidence(self, constraints: Dict[str, float]) -> float:
        """Calculate detection confidence based on constraint severity."""
        if not constraints:
            return 0.0

        # Use maximum constraint value as base
        max_constraint = max(constraints.values())

        # Scale confidence based on how far above threshold
        base = self._resource_config.base_confidence
        severity_boost = (max_constraint - 0.7) * 0.5  # 0.7 is baseline

        return min(base + severity_boost, 0.95)
