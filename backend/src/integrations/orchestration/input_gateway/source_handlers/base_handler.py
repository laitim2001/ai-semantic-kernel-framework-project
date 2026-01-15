"""
Base Source Handler Abstract Class

Defines the abstract base class for all source handlers.
Each source handler implements specialized processing logic for
requests from different sources (ServiceNow, Prometheus, User).

Sprint 95: Story 95-2 - Implement BaseSourceHandler (Phase 28)
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models import IncomingRequest

logger = logging.getLogger(__name__)


@dataclass
class HandlerMetrics:
    """
    Metrics for source handler operations.

    Attributes:
        total_processed: Total number of processed requests
        successful: Count of successful processing
        failed: Count of failed processing
        latencies: List of processing latencies (ms)
    """
    total_processed: int = 0
    successful: int = 0
    failed: int = 0
    latencies: List[float] = field(default_factory=list)

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency."""
        if not self.latencies:
            return 0.0
        return sum(self.latencies) / len(self.latencies)

    @property
    def success_rate(self) -> float:
        """Calculate success rate (0.0 to 1.0)."""
        if self.total_processed == 0:
            return 0.0
        return self.successful / self.total_processed

    def record_latency(self, latency_ms: float) -> None:
        """Record a latency measurement."""
        self.latencies.append(latency_ms)
        # Keep only last 1000 measurements
        if len(self.latencies) > 1000:
            self.latencies = self.latencies[-1000:]

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_processed": self.total_processed,
            "successful": self.successful,
            "failed": self.failed,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "success_rate": round(self.success_rate, 4),
        }


class BaseSourceHandler(ABC):
    """
    Abstract base class for source handlers.

    Source handlers process requests from specific sources and produce
    RoutingDecision objects. Each handler implements a simplified
    processing path optimized for its source type.

    Subclasses must implement:
    - process(): Main processing logic
    - handler_type: Handler type identifier (property)

    Provides common utilities:
    - build_routing_decision(): Create RoutingDecision with standard fields
    - extract_metadata(): Extract common metadata from requests
    - _record_metrics(): Track processing metrics

    Example:
        >>> class MyHandler(BaseSourceHandler):
        ...     @property
        ...     def handler_type(self) -> str:
        ...         return "my_source"
        ...
        ...     async def process(self, request: IncomingRequest) -> RoutingDecision:
        ...         # Handler-specific processing
        ...         return self.build_routing_decision(...)
    """

    def __init__(self, enable_metrics: bool = True):
        """
        Initialize the base handler.

        Args:
            enable_metrics: Whether to track handler metrics
        """
        self.enable_metrics = enable_metrics
        self._metrics = HandlerMetrics()

    @property
    @abstractmethod
    def handler_type(self) -> str:
        """
        Return the handler type identifier.

        This is used for logging and metrics tracking.

        Returns:
            Handler type string (e.g., "servicenow", "prometheus")
        """
        pass

    @abstractmethod
    async def process(self, request: IncomingRequest) -> "RoutingDecision":
        """
        Process an incoming request and return a routing decision.

        Args:
            request: The incoming request to process

        Returns:
            RoutingDecision with classification and routing information
        """
        pass

    def build_routing_decision(
        self,
        intent_category: "ITIntentCategory",
        sub_intent: Optional[str] = None,
        confidence: float = 1.0,
        workflow_type: Optional["WorkflowType"] = None,
        risk_level: Optional["RiskLevel"] = None,
        completeness_score: float = 1.0,
        missing_fields: Optional[List[str]] = None,
        layer_used: Optional[str] = None,
        reasoning: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        processing_time_ms: float = 0.0,
    ) -> "RoutingDecision":
        """
        Build a RoutingDecision with standard fields.

        Args:
            intent_category: Classified intent category
            sub_intent: More specific intent classification
            confidence: Confidence score (0.0 to 1.0)
            workflow_type: Recommended workflow type
            risk_level: Assessed risk level
            completeness_score: Information completeness (0.0 to 1.0)
            missing_fields: List of missing fields
            layer_used: Routing layer identifier
            reasoning: Explanation for the decision
            metadata: Additional context
            processing_time_ms: Processing time in milliseconds

        Returns:
            Configured RoutingDecision instance
        """
        from ...intent_router.models import (
            CompletenessInfo,
            ITIntentCategory,
            RiskLevel,
            RoutingDecision,
            WorkflowType,
        )

        # Set defaults based on intent category
        if workflow_type is None:
            workflow_type = self._default_workflow_type(intent_category)

        if risk_level is None:
            risk_level = self._default_risk_level(intent_category)

        # Create completeness info
        completeness = CompletenessInfo(
            is_complete=completeness_score >= 0.6,
            completeness_score=completeness_score,
            missing_fields=missing_fields or [],
        )

        return RoutingDecision(
            intent_category=intent_category,
            sub_intent=sub_intent,
            confidence=confidence,
            workflow_type=workflow_type,
            risk_level=risk_level,
            completeness=completeness,
            routing_layer=layer_used or f"{self.handler_type}_mapping",
            reasoning=reasoning,
            metadata=metadata or {},
            processing_time_ms=processing_time_ms,
        )

    def extract_metadata(self, request: IncomingRequest) -> Dict[str, Any]:
        """
        Extract common metadata from an incoming request.

        Args:
            request: The incoming request

        Returns:
            Dictionary of extracted metadata
        """
        return {
            "request_id": request.request_id,
            "source_type": request.source_type,
            "received_at": request.timestamp.isoformat(),
            "handler_type": self.handler_type,
            "has_content": bool(request.content),
            "has_data": bool(request.data),
        }

    def _default_workflow_type(self, intent_category: "ITIntentCategory") -> "WorkflowType":
        """
        Get default workflow type based on intent category.

        Args:
            intent_category: The intent category

        Returns:
            Default WorkflowType
        """
        from ...intent_router.models import ITIntentCategory, WorkflowType

        mapping = {
            ITIntentCategory.INCIDENT: WorkflowType.SEQUENTIAL,
            ITIntentCategory.REQUEST: WorkflowType.SIMPLE,
            ITIntentCategory.CHANGE: WorkflowType.SEQUENTIAL,
            ITIntentCategory.QUERY: WorkflowType.SIMPLE,
            ITIntentCategory.UNKNOWN: WorkflowType.HANDOFF,
        }
        return mapping.get(intent_category, WorkflowType.SIMPLE)

    def _default_risk_level(self, intent_category: "ITIntentCategory") -> "RiskLevel":
        """
        Get default risk level based on intent category.

        Args:
            intent_category: The intent category

        Returns:
            Default RiskLevel
        """
        from ...intent_router.models import ITIntentCategory, RiskLevel

        mapping = {
            ITIntentCategory.INCIDENT: RiskLevel.MEDIUM,
            ITIntentCategory.REQUEST: RiskLevel.LOW,
            ITIntentCategory.CHANGE: RiskLevel.MEDIUM,
            ITIntentCategory.QUERY: RiskLevel.LOW,
            ITIntentCategory.UNKNOWN: RiskLevel.MEDIUM,
        }
        return mapping.get(intent_category, RiskLevel.MEDIUM)

    def _record_success(self, latency_ms: float) -> None:
        """Record a successful processing."""
        if self.enable_metrics:
            self._metrics.total_processed += 1
            self._metrics.successful += 1
            self._metrics.record_latency(latency_ms)

    def _record_failure(self, latency_ms: float) -> None:
        """Record a failed processing."""
        if self.enable_metrics:
            self._metrics.total_processed += 1
            self._metrics.failed += 1
            self._metrics.record_latency(latency_ms)

    def get_metrics(self) -> Dict[str, Any]:
        """Get handler metrics."""
        return self._metrics.to_dict()

    def reset_metrics(self) -> None:
        """Reset handler metrics."""
        self._metrics = HandlerMetrics()


class MockBaseHandler(BaseSourceHandler):
    """
    Mock base handler for testing.

    Returns configurable responses based on input.
    """

    def __init__(
        self,
        handler_type_name: str = "mock",
        default_intent: str = "incident",
        default_sub_intent: str = "general",
    ):
        """
        Initialize mock handler.

        Args:
            handler_type_name: Handler type identifier
            default_intent: Default intent category to return
            default_sub_intent: Default sub-intent to return
        """
        super().__init__(enable_metrics=False)
        self._handler_type = handler_type_name
        self._default_intent = default_intent
        self._default_sub_intent = default_sub_intent

    @property
    def handler_type(self) -> str:
        """Return the handler type identifier."""
        return self._handler_type

    async def process(self, request: IncomingRequest) -> "RoutingDecision":
        """Process request with mock logic."""
        from ...intent_router.models import ITIntentCategory

        start_time = time.perf_counter()

        intent_category = ITIntentCategory.from_string(self._default_intent)

        return self.build_routing_decision(
            intent_category=intent_category,
            sub_intent=self._default_sub_intent,
            confidence=0.95,
            layer_used=f"{self.handler_type}_mock",
            reasoning="Mock handler response",
            metadata=self.extract_metadata(request),
            processing_time_ms=(time.perf_counter() - start_time) * 1000,
        )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "BaseSourceHandler",
    "MockBaseHandler",
    "HandlerMetrics",
]
