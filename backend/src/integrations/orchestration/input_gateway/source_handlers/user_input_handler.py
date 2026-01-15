"""
User Input Source Handler

Handler for user-generated input (chat, form submissions, API calls).
Unlike system source handlers, this handler uses the FULL three-layer
routing process through BusinessIntentRouter.

Processing flow:
1. Normalize and standardize user input
2. Delegate to BusinessIntentRouter (Pattern → Semantic → LLM)
3. Enhance routing decision with metadata

Sprint 95: Story 95-5 - Implement UserInputHandler (Phase 28)
"""

import logging
import re
import time
from typing import Any, Dict, Optional, TYPE_CHECKING

from .base_handler import BaseSourceHandler
from ..models import IncomingRequest

if TYPE_CHECKING:
    from ...intent_router.models import RoutingDecision
    from ...intent_router.router import BusinessIntentRouter

logger = logging.getLogger(__name__)


class UserInputHandler(BaseSourceHandler):
    """
    User input handler that delegates to the full three-layer routing.

    Unlike ServiceNowHandler and PrometheusHandler which use simplified paths,
    UserInputHandler leverages the complete BusinessIntentRouter for:
    - Pattern Matcher (high-confidence rule-based)
    - Semantic Router (vector similarity)
    - LLM Classifier (fallback with semantic understanding)

    This provides rich classification for ambiguous user input while
    maintaining fast processing for clear requests.

    Attributes:
        business_router: BusinessIntentRouter for three-layer routing

    Example:
        >>> handler = UserInputHandler(
        ...     business_router=BusinessIntentRouter(...),
        ... )
        >>> request = IncomingRequest.from_user_input("ETL 今天跑失敗了，很緊急")
        >>> decision = await handler.process(request)
        >>> print(decision.routing_layer)  # "pattern" or "semantic" or "llm"
    """

    def __init__(
        self,
        business_router: Optional["BusinessIntentRouter"] = None,
        enable_metrics: bool = True,
    ):
        """
        Initialize UserInputHandler.

        Args:
            business_router: BusinessIntentRouter for classification
            enable_metrics: Whether to track handler metrics
        """
        super().__init__(enable_metrics=enable_metrics)
        self.business_router = business_router

    @property
    def handler_type(self) -> str:
        """Return handler type identifier."""
        return "user"

    async def process(self, request: IncomingRequest) -> "RoutingDecision":
        """
        Process a user input request through the full three-layer routing.

        Args:
            request: The user input request

        Returns:
            RoutingDecision from BusinessIntentRouter with enhanced metadata
        """
        from ...intent_router.models import (
            CompletenessInfo,
            ITIntentCategory,
            RiskLevel,
            RoutingDecision,
            WorkflowType,
        )

        start_time = time.perf_counter()

        try:
            # Validate business router is available
            if not self.business_router:
                logger.error("No BusinessIntentRouter configured for UserInputHandler")
                return self._build_error_decision(
                    "BusinessIntentRouter not configured",
                    start_time,
                )

            # Extract and normalize user input
            user_text = self._normalize_input(request)

            if not user_text:
                logger.warning("Empty user input received")
                return self._build_empty_decision(start_time)

            # Delegate to BusinessIntentRouter
            logger.debug(f"Routing user input: '{user_text[:50]}...'")
            decision = await self.business_router.route(user_text)

            # Calculate total latency (includes router latency)
            total_latency_ms = (time.perf_counter() - start_time) * 1000

            # Enhance decision with handler metadata
            enhanced_metadata = {
                **decision.metadata,
                "handler_type": self.handler_type,
                "original_input_length": len(user_text),
                "normalized": True,
                **self.extract_metadata(request),
            }

            # Record success
            self._record_success(total_latency_ms)

            # Return enhanced decision
            return RoutingDecision(
                intent_category=decision.intent_category,
                sub_intent=decision.sub_intent,
                confidence=decision.confidence,
                workflow_type=decision.workflow_type,
                risk_level=decision.risk_level,
                completeness=decision.completeness,
                routing_layer=decision.routing_layer,
                rule_id=decision.rule_id,
                reasoning=decision.reasoning,
                metadata=enhanced_metadata,
                processing_time_ms=total_latency_ms,
            )

        except Exception as e:
            logger.error(f"User input processing error: {e}", exc_info=True)
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._record_failure(latency_ms)
            return self._build_error_decision(str(e), start_time)

    def _normalize_input(self, request: IncomingRequest) -> str:
        """
        Normalize and clean user input.

        Processing:
        1. Use content field primarily
        2. Fall back to data.description or data.message
        3. Strip whitespace
        4. Collapse multiple whitespace
        5. Limit length (prevent abuse)

        Args:
            request: The incoming request

        Returns:
            Normalized input text
        """
        # Try different sources for user text
        text = request.content

        if not text and request.data:
            # Try common fields in data
            text = (
                request.data.get("description", "")
                or request.data.get("message", "")
                or request.data.get("text", "")
                or request.data.get("query", "")
                or request.data.get("input", "")
            )

        if not text:
            return ""

        # Normalize whitespace
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)

        # Limit length (prevent abuse with extremely long input)
        max_length = 10000
        if len(text) > max_length:
            logger.warning(f"User input truncated from {len(text)} to {max_length} chars")
            text = text[:max_length]

        return text

    def _build_empty_decision(self, start_time: float) -> "RoutingDecision":
        """Build decision for empty input."""
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
            risk_level=RiskLevel.LOW,
            completeness_score=0.0,
            missing_fields=["input_text"],
            layer_used="user_input_empty",
            reasoning="Empty or invalid user input",
            processing_time_ms=latency_ms,
        )

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
            layer_used="user_input_error",
            reasoning=f"Processing error: {error_message}",
            processing_time_ms=latency_ms,
        )


class MockUserInputHandler(UserInputHandler):
    """
    Mock user input handler for testing.

    Uses MockBusinessIntentRouter internally.
    """

    def __init__(self):
        """Initialize mock handler."""
        from ...intent_router.router import MockBusinessIntentRouter
        super().__init__(
            business_router=MockBusinessIntentRouter(),
            enable_metrics=False,
        )

    async def process(self, request: IncomingRequest) -> "RoutingDecision":
        """Process with mock router."""
        from ...intent_router.models import ITIntentCategory

        start_time = time.perf_counter()

        # Get normalized text
        user_text = self._normalize_input(request)

        if not user_text:
            return self._build_empty_decision(start_time)

        # Use parent's business router (MockBusinessIntentRouter)
        decision = await self.business_router.route(user_text)

        latency_ms = (time.perf_counter() - start_time) * 1000

        # Enhance with mock metadata
        decision.metadata["handler_type"] = "user_mock"
        decision.metadata["original_input_length"] = len(user_text)
        decision.processing_time_ms = latency_ms

        return decision


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "UserInputHandler",
    "MockUserInputHandler",
]
