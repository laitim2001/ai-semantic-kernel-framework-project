"""
ServiceNow Source Handler

Specialized handler for ServiceNow webhook requests.
Uses mapping table for category → IT Intent conversion,
falls back to PatternMatcher when subcategory is insufficient.

This handler implements a SIMPLIFIED processing path:
1. Schema validation (optional)
2. Mapping table lookup
3. PatternMatcher fallback (if needed)
4. SKIPS Semantic Router and LLM Classifier

Target latency: < 10ms

Sprint 95: Story 95-3 - Implement ServiceNowHandler (Phase 28)
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from .base_handler import BaseSourceHandler
from ..models import IncomingRequest

if TYPE_CHECKING:
    from ...intent_router.models import RoutingDecision, ITIntentCategory, RiskLevel, WorkflowType
    from ...intent_router.pattern_matcher import PatternMatcher
    from ..schema_validator import SchemaValidator

logger = logging.getLogger(__name__)


class ServiceNowHandler(BaseSourceHandler):
    """
    ServiceNow webhook handler with mapping table and pattern fallback.

    Processing flow:
    1. Validate ServiceNow webhook schema (if validator provided)
    2. Look up category/subcategory in mapping table
    3. If mapping found → return RoutingDecision (fast path)
    4. If no mapping → use PatternMatcher on short_description
    5. SKIP Semantic Router and LLM Classifier

    This ensures system source requests are processed quickly (< 10ms)
    while still providing accurate classification.

    Attributes:
        schema_validator: Optional schema validator
        pattern_matcher: Optional pattern matcher for fallback
        CATEGORY_MAPPING: Static mapping table

    Example:
        >>> handler = ServiceNowHandler(
        ...     schema_validator=SchemaValidator(),
        ...     pattern_matcher=PatternMatcher(...),
        ... )
        >>> request = IncomingRequest.from_servicenow_webhook({
        ...     "number": "INC0012345",
        ...     "category": "incident",
        ...     "subcategory": "software",
        ...     "short_description": "ETL Pipeline 失敗"
        ... })
        >>> decision = await handler.process(request)
        >>> print(decision.intent_category)  # ITIntentCategory.INCIDENT
        >>> print(decision.sub_intent)       # "software_issue"
        >>> print(decision.layer_used)       # "servicenow_mapping"
    """

    # =============================================================================
    # Category Mapping Table
    # =============================================================================
    # Format: "category/subcategory" → (intent_category, sub_intent)

    CATEGORY_MAPPING: Dict[str, Tuple[str, str]] = {
        # Incident categories
        "incident/hardware": ("incident", "hardware_failure"),
        "incident/software": ("incident", "software_issue"),
        "incident/network": ("incident", "network_failure"),
        "incident/database": ("incident", "database_issue"),
        "incident/security": ("incident", "security_incident"),
        "incident/performance": ("incident", "performance_issue"),
        "incident/application": ("incident", "application_error"),
        "incident/infrastructure": ("incident", "infrastructure_issue"),

        # Request categories
        "request/account": ("request", "account_request"),
        "request/access": ("request", "access_request"),
        "request/software": ("request", "software_request"),
        "request/hardware": ("request", "hardware_request"),
        "request/service": ("request", "service_request"),
        "request/information": ("query", "information_request"),

        # Change categories
        "change/standard": ("change", "standard_change"),
        "change/emergency": ("change", "emergency_change"),
        "change/normal": ("change", "normal_change"),
        "change/deployment": ("change", "release_deployment"),
        "change/configuration": ("change", "configuration_update"),

        # Query/Problem categories (mapped to query intent)
        "problem/": ("incident", "recurring_issue"),
    }

    # Priority to risk level mapping
    PRIORITY_RISK_MAPPING: Dict[str, str] = {
        "1": "critical",  # Critical
        "2": "high",      # High
        "3": "medium",    # Medium
        "4": "low",       # Low
        "5": "low",       # Planning
    }

    # Sub-intent to workflow mapping
    WORKFLOW_MAPPING: Dict[str, str] = {
        # Critical incidents need multi-agent
        "service_down": "magentic",
        "security_incident": "magentic",
        "database_issue": "magentic",

        # Standard incidents need sequential
        "hardware_failure": "sequential",
        "software_issue": "sequential",
        "network_failure": "sequential",
        "performance_issue": "sequential",
        "application_error": "sequential",
        "infrastructure_issue": "sequential",
        "recurring_issue": "sequential",

        # Changes need sequential
        "standard_change": "sequential",
        "emergency_change": "magentic",
        "normal_change": "sequential",
        "release_deployment": "magentic",
        "configuration_update": "sequential",

        # Requests are simple
        "account_request": "simple",
        "access_request": "simple",
        "software_request": "simple",
        "hardware_request": "simple",
        "service_request": "simple",

        # Queries are simple
        "information_request": "simple",
    }

    def __init__(
        self,
        schema_validator: Optional["SchemaValidator"] = None,
        pattern_matcher: Optional["PatternMatcher"] = None,
        enable_metrics: bool = True,
    ):
        """
        Initialize ServiceNowHandler.

        Args:
            schema_validator: Schema validator for ServiceNow webhooks
            pattern_matcher: Pattern matcher for fallback classification
            enable_metrics: Whether to track handler metrics
        """
        super().__init__(enable_metrics=enable_metrics)
        self.schema_validator = schema_validator
        self.pattern_matcher = pattern_matcher

    @property
    def handler_type(self) -> str:
        """Return handler type identifier."""
        return "servicenow"

    async def process(self, request: IncomingRequest) -> "RoutingDecision":
        """
        Process a ServiceNow webhook request.

        Args:
            request: The ServiceNow webhook request

        Returns:
            RoutingDecision with classification and routing information
        """
        from ...intent_router.models import (
            ITIntentCategory,
            RiskLevel,
            WorkflowType,
        )

        start_time = time.perf_counter()

        try:
            # Extract ServiceNow data
            data = request.data
            if not data:
                logger.warning("Empty ServiceNow webhook data")
                return self._build_error_decision(
                    "Empty webhook data",
                    start_time,
                )

            # Optional schema validation
            if self.schema_validator:
                try:
                    validated_data = self.schema_validator.validate(
                        data,
                        schema="servicenow",
                    )
                    data = validated_data
                except Exception as e:
                    logger.warning(f"ServiceNow schema validation failed: {e}")
                    # Continue with original data

            # Extract key fields
            category = data.get("category", "").lower()
            subcategory = data.get("subcategory", "").lower()
            short_description = data.get("short_description", "")
            priority = str(data.get("priority", "3"))
            number = data.get("number", "")

            # Try mapping table lookup
            mapping_key = f"{category}/{subcategory}"
            mapping = self.CATEGORY_MAPPING.get(mapping_key)

            # Try category-only mapping if specific mapping not found
            if not mapping:
                mapping_key = f"{category}/"
                mapping = self.CATEGORY_MAPPING.get(mapping_key)

            if mapping:
                intent_category_str, sub_intent = mapping
                intent_category = ITIntentCategory.from_string(intent_category_str)
                layer_used = "servicenow_mapping"
                confidence = 1.0
                reasoning = f"Mapped from ServiceNow category: {mapping_key}"

                logger.debug(
                    f"ServiceNow mapping: {mapping_key} → "
                    f"{intent_category.value}/{sub_intent}"
                )
            elif self.pattern_matcher and short_description:
                # Fallback to pattern matcher
                pattern_result = self.pattern_matcher.match(short_description)

                if pattern_result.matched:
                    intent_category = pattern_result.intent_category or ITIntentCategory.INCIDENT
                    sub_intent = pattern_result.sub_intent or "general_incident"
                    layer_used = "servicenow_pattern"
                    confidence = pattern_result.confidence
                    reasoning = f"Pattern matched: {pattern_result.matched_pattern}"

                    logger.debug(
                        f"ServiceNow pattern fallback: {short_description[:30]}... → "
                        f"{intent_category.value}/{sub_intent}"
                    )
                else:
                    # Default to incident if no mapping or pattern
                    intent_category = ITIntentCategory.INCIDENT
                    sub_intent = "general_incident"
                    layer_used = "servicenow_default"
                    confidence = 0.7
                    reasoning = "Default classification (no mapping or pattern match)"
            else:
                # Default when no pattern matcher available
                intent_category = ITIntentCategory.INCIDENT
                sub_intent = "general_incident"
                layer_used = "servicenow_default"
                confidence = 0.7
                reasoning = "Default classification"

            # Determine risk level from priority
            risk_str = self.PRIORITY_RISK_MAPPING.get(priority, "medium")
            risk_level = RiskLevel.from_string(risk_str)

            # Determine workflow type
            workflow_str = self.WORKFLOW_MAPPING.get(sub_intent, "sequential")
            workflow_type = WorkflowType.from_string(workflow_str)

            # Calculate latency
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Build metadata
            metadata = {
                "servicenow_number": number,
                "servicenow_category": category,
                "servicenow_subcategory": subcategory,
                "servicenow_priority": priority,
                "mapping_key": mapping_key if mapping else None,
                **self.extract_metadata(request),
            }

            # Record success
            self._record_success(latency_ms)

            return self.build_routing_decision(
                intent_category=intent_category,
                sub_intent=sub_intent,
                confidence=confidence,
                workflow_type=workflow_type,
                risk_level=risk_level,
                completeness_score=1.0,  # System source is always complete
                layer_used=layer_used,
                reasoning=reasoning,
                metadata=metadata,
                processing_time_ms=latency_ms,
            )

        except Exception as e:
            logger.error(f"ServiceNow processing error: {e}", exc_info=True)
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._record_failure(latency_ms)
            return self._build_error_decision(str(e), start_time)

    def _build_error_decision(
        self,
        error_message: str,
        start_time: float,
    ) -> "RoutingDecision":
        """Build error routing decision."""
        from ...intent_router.models import (
            ITIntentCategory,
            RiskLevel,
            WorkflowType,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000

        return self.build_routing_decision(
            intent_category=ITIntentCategory.UNKNOWN,
            sub_intent=None,
            confidence=0.0,
            workflow_type=WorkflowType.HANDOFF,
            risk_level=RiskLevel.MEDIUM,
            completeness_score=0.0,
            layer_used="servicenow_error",
            reasoning=f"Processing error: {error_message}",
            processing_time_ms=latency_ms,
        )


class MockServiceNowHandler(ServiceNowHandler):
    """
    Mock ServiceNow handler for testing.

    Processes requests without actual schema validation or pattern matching.
    """

    def __init__(self):
        """Initialize mock handler."""
        super().__init__(
            schema_validator=None,
            pattern_matcher=None,
            enable_metrics=False,
        )

    async def process(self, request: IncomingRequest) -> "RoutingDecision":
        """Process with mock logic - simplified for testing."""
        from ...intent_router.models import ITIntentCategory

        start_time = time.perf_counter()

        # Extract basic fields
        data = request.data
        category = data.get("category", "incident").lower()
        subcategory = data.get("subcategory", "").lower()

        # Try mapping
        mapping_key = f"{category}/{subcategory}"
        mapping = self.CATEGORY_MAPPING.get(mapping_key)

        if mapping:
            intent_str, sub_intent = mapping
            intent_category = ITIntentCategory.from_string(intent_str)
        else:
            intent_category = ITIntentCategory.INCIDENT
            sub_intent = "general_incident"

        latency_ms = (time.perf_counter() - start_time) * 1000

        return self.build_routing_decision(
            intent_category=intent_category,
            sub_intent=sub_intent,
            confidence=0.95,
            layer_used="servicenow_mock",
            reasoning="Mock ServiceNow handler response",
            metadata={
                "servicenow_number": data.get("number"),
                "servicenow_category": category,
            },
            processing_time_ms=latency_ms,
        )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "ServiceNowHandler",
    "MockServiceNowHandler",
]
