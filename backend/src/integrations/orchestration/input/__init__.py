"""
Orchestration Input Processing Module.

Sprint 114: AD 場景基礎建設 (Phase 32)
Sprint 116: L4a Input Processing Contracts (Phase 34)
Sprint 126: IT Incident Handler (Phase 34)

Provides ServiceNow webhook integration, RITM-to-intent mapping,
IT incident handling, and L4a input processing contracts.
"""

from .servicenow_webhook import (
    ServiceNowRITMEvent,
    ServiceNowWebhookReceiver,
    WebhookAuthConfig,
    WebhookValidationError,
)
from .ritm_intent_mapper import (
    IntentMappingResult,
    RITMIntentMapper,
)

# Sprint 116: L4a Contracts
from .contracts import (
    InputProcessorProtocol,
    InputValidationResult,
    InputValidatorProtocol,
    InputProcessingMetrics,
)

# Sprint 126: IT Incident Handler
from .incident_handler import (
    IncidentHandler,
    IncidentSubCategory,
    ServiceNowINCEvent,
)

__all__ = [
    "ServiceNowRITMEvent",
    "ServiceNowWebhookReceiver",
    "WebhookAuthConfig",
    "WebhookValidationError",
    "IntentMappingResult",
    "RITMIntentMapper",
    # Sprint 116: L4a Contracts
    "InputProcessorProtocol",
    "InputValidationResult",
    "InputValidatorProtocol",
    "InputProcessingMetrics",
    # Sprint 126: IT Incident Handler
    "IncidentHandler",
    "IncidentSubCategory",
    "ServiceNowINCEvent",
]
