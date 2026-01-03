# =============================================================================
# IPA Platform - Trigger Detectors
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 56: Mode Switcher & HITL - S56-2 Trigger Detectors
#
# Trigger detector implementations for mode switching.
#
# Detectors:
#   - BaseTriggerDetector: Abstract base class
#   - ComplexityTriggerDetector: Complexity-based switching
#   - UserRequestTriggerDetector: User request detection
#   - FailureTriggerDetector: Failure recovery trigger
#   - ResourceTriggerDetector: Resource constraint trigger
#
# Dependencies:
#   - TriggerDetectorProtocol (src.integrations.hybrid.switching.switcher)
#   - SwitchTrigger (src.integrations.hybrid.switching.models)
# =============================================================================

from .base import BaseTriggerDetector, TriggerDetectorConfig
from .complexity import ComplexityTriggerDetector, ComplexityConfig
from .failure import FailureTriggerDetector, FailureConfig
from .resource import ResourceTriggerDetector, ResourceConfig
from .user import UserRequestTriggerDetector, UserRequestConfig

__all__ = [
    # Base
    "BaseTriggerDetector",
    "TriggerDetectorConfig",
    # Complexity
    "ComplexityTriggerDetector",
    "ComplexityConfig",
    # User Request
    "UserRequestTriggerDetector",
    "UserRequestConfig",
    # Failure
    "FailureTriggerDetector",
    "FailureConfig",
    # Resource
    "ResourceTriggerDetector",
    "ResourceConfig",
]
