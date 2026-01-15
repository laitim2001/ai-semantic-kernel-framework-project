"""
Business Intent Router Implementation

Coordinates three-layer intent routing with completeness checking.
Implements fallback strategy: Pattern → Semantic → LLM

Sprint 93: Story 93-1 - Implement BusinessIntentRouter (Phase 28)
"""

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from .completeness import CompletenessChecker, MockCompletenessChecker
from .llm_classifier import LLMClassifier, MockLLMClassifier
from .models import (
    CompletenessInfo,
    ITIntentCategory,
    LLMClassificationResult,
    PatternMatchResult,
    RiskLevel,
    RoutingDecision,
    SemanticRouteResult,
    WorkflowType,
)
from .pattern_matcher import PatternMatcher
from .semantic_router import MockSemanticRouter, SemanticRouter

logger = logging.getLogger(__name__)


@dataclass
class RouterConfig:
    """
    Configuration for BusinessIntentRouter.

    Attributes:
        pattern_threshold: Minimum confidence for pattern match (default: 0.90)
        semantic_threshold: Minimum similarity for semantic match (default: 0.85)
        enable_llm_fallback: Whether to use LLM as last resort (default: True)
        enable_completeness: Whether to check completeness (default: True)
        track_latency: Whether to track latency metrics (default: True)
    """
    pattern_threshold: float = 0.90
    semantic_threshold: float = 0.85
    enable_llm_fallback: bool = True
    enable_completeness: bool = True
    track_latency: bool = True

    @classmethod
    def from_env(cls) -> "RouterConfig":
        """Create configuration from environment variables."""
        return cls(
            pattern_threshold=float(
                os.getenv("PATTERN_CONFIDENCE_THRESHOLD", "0.90")
            ),
            semantic_threshold=float(
                os.getenv("SEMANTIC_SIMILARITY_THRESHOLD", "0.85")
            ),
            enable_llm_fallback=os.getenv(
                "ENABLE_LLM_FALLBACK", "true"
            ).lower() == "true",
            enable_completeness=os.getenv(
                "ENABLE_COMPLETENESS", "true"
            ).lower() == "true",
            track_latency=os.getenv(
                "TRACK_LATENCY", "true"
            ).lower() == "true",
        )


@dataclass
class RoutingMetrics:
    """
    Metrics for routing operations.

    Attributes:
        total_requests: Total number of routing requests
        pattern_matches: Count of pattern layer matches
        semantic_matches: Count of semantic layer matches
        llm_fallbacks: Count of LLM fallback invocations
        avg_latency_ms: Average latency in milliseconds
        p95_latency_ms: 95th percentile latency
    """
    total_requests: int = 0
    pattern_matches: int = 0
    semantic_matches: int = 0
    llm_fallbacks: int = 0
    latencies: List[float] = field(default_factory=list)

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency."""
        if not self.latencies:
            return 0.0
        return sum(self.latencies) / len(self.latencies)

    @property
    def p95_latency_ms(self) -> float:
        """Calculate 95th percentile latency."""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]

    def record_latency(self, latency_ms: float) -> None:
        """Record a latency measurement."""
        self.latencies.append(latency_ms)
        # Keep only last 1000 measurements
        if len(self.latencies) > 1000:
            self.latencies = self.latencies[-1000:]

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_requests": self.total_requests,
            "pattern_matches": self.pattern_matches,
            "semantic_matches": self.semantic_matches,
            "llm_fallbacks": self.llm_fallbacks,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
        }


class BusinessIntentRouter:
    """
    Three-layer intent router with completeness checking.

    Routes user input through three layers with decreasing speed but increasing accuracy:
    1. Pattern Matcher: Rule-based, high performance (< 10ms)
    2. Semantic Router: Vector similarity (< 100ms)
    3. LLM Classifier: Claude Haiku fallback (< 2000ms)

    Attributes:
        pattern_matcher: Layer 1 - Pattern matching component
        semantic_router: Layer 2 - Semantic routing component
        llm_classifier: Layer 3 - LLM classification component
        completeness_checker: Information completeness checker
        config: Router configuration

    Example:
        >>> router = BusinessIntentRouter(
        ...     pattern_matcher=PatternMatcher(rules_path="rules.yaml"),
        ...     semantic_router=SemanticRouter(routes=routes),
        ...     llm_classifier=LLMClassifier(api_key="..."),
        ... )
        >>> decision = await router.route("ETL 今天跑失敗了，很緊急")
        >>> print(decision.intent_category)  # ITIntentCategory.INCIDENT
        >>> print(decision.routing_layer)    # "pattern"
    """

    def __init__(
        self,
        pattern_matcher: PatternMatcher,
        semantic_router: SemanticRouter,
        llm_classifier: LLMClassifier,
        completeness_checker: Optional[CompletenessChecker] = None,
        config: Optional[RouterConfig] = None,
    ):
        """
        Initialize the BusinessIntentRouter.

        Args:
            pattern_matcher: Pattern matching component (Layer 1)
            semantic_router: Semantic routing component (Layer 2)
            llm_classifier: LLM classification component (Layer 3)
            completeness_checker: Completeness checker (optional)
            config: Router configuration (optional)
        """
        self.pattern_matcher = pattern_matcher
        self.semantic_router = semantic_router
        self.llm_classifier = llm_classifier
        self.completeness_checker = completeness_checker or CompletenessChecker()
        self.config = config or RouterConfig()
        self._metrics = RoutingMetrics()

    async def route(self, user_input: str) -> RoutingDecision:
        """
        Route user input through three-layer architecture.

        Attempts matching in order:
        1. Pattern Matcher (if confidence >= pattern_threshold)
        2. Semantic Router (if similarity >= semantic_threshold)
        3. LLM Classifier (final fallback)

        Args:
            user_input: The user's input text to route

        Returns:
            RoutingDecision with routing details and completeness assessment
        """
        start_time = time.perf_counter()
        self._metrics.total_requests += 1

        layer_latencies: Dict[str, float] = {}

        # Validate input
        if not user_input or not user_input.strip():
            return self._build_empty_decision(start_time)

        normalized_input = user_input.strip()

        # Layer 1: Pattern Matcher
        layer_start = time.perf_counter()
        pattern_result = self.pattern_matcher.match(normalized_input)
        layer_latencies["pattern"] = (time.perf_counter() - layer_start) * 1000

        if pattern_result.matched and pattern_result.confidence >= self.config.pattern_threshold:
            logger.info(
                f"Pattern match: {pattern_result.intent_category.value} "
                f"(confidence: {pattern_result.confidence:.2f}, "
                f"rule: {pattern_result.rule_id})"
            )
            self._metrics.pattern_matches += 1
            return self._build_decision_from_pattern(
                pattern_result,
                normalized_input,
                start_time,
                layer_latencies,
            )

        # Layer 2: Semantic Router
        layer_start = time.perf_counter()
        semantic_result = await self.semantic_router.route(normalized_input)
        layer_latencies["semantic"] = (time.perf_counter() - layer_start) * 1000

        if semantic_result.matched and semantic_result.similarity >= self.config.semantic_threshold:
            logger.info(
                f"Semantic match: {semantic_result.intent_category.value} "
                f"(similarity: {semantic_result.similarity:.2f}, "
                f"route: {semantic_result.route_name})"
            )
            self._metrics.semantic_matches += 1
            return self._build_decision_from_semantic(
                semantic_result,
                normalized_input,
                start_time,
                layer_latencies,
            )

        # Layer 3: LLM Classifier (fallback)
        if self.config.enable_llm_fallback:
            layer_start = time.perf_counter()
            llm_result = await self.llm_classifier.classify(
                normalized_input,
                include_completeness=True,
            )
            layer_latencies["llm"] = (time.perf_counter() - layer_start) * 1000

            logger.info(
                f"LLM classification: {llm_result.intent_category.value} "
                f"(confidence: {llm_result.confidence:.2f})"
            )
            self._metrics.llm_fallbacks += 1
            return self._build_decision_from_llm(
                llm_result,
                normalized_input,
                start_time,
                layer_latencies,
            )

        # No classification possible
        logger.warning(f"Unable to classify: '{normalized_input[:50]}...'")
        return self._build_unknown_decision(
            normalized_input,
            start_time,
            layer_latencies,
        )

    def _build_empty_decision(self, start_time: float) -> RoutingDecision:
        """Build decision for empty input."""
        total_latency = (time.perf_counter() - start_time) * 1000

        return RoutingDecision(
            intent_category=ITIntentCategory.UNKNOWN,
            confidence=0.0,
            routing_layer="none",
            reasoning="Empty or invalid input",
            processing_time_ms=total_latency,
        )

    def _build_decision_from_pattern(
        self,
        result: PatternMatchResult,
        user_input: str,
        start_time: float,
        layer_latencies: Dict[str, float],
    ) -> RoutingDecision:
        """Build routing decision from pattern match result."""
        total_latency = (time.perf_counter() - start_time) * 1000
        self._metrics.record_latency(total_latency)

        # Get completeness assessment
        completeness = self._get_completeness(
            result.intent_category,
            user_input,
        )

        return RoutingDecision(
            intent_category=result.intent_category or ITIntentCategory.UNKNOWN,
            sub_intent=result.sub_intent,
            confidence=result.confidence,
            workflow_type=result.workflow_type or self._get_workflow_type(result.intent_category),
            risk_level=result.risk_level or self._get_risk_level(result.intent_category, user_input),
            completeness=completeness,
            routing_layer="pattern",
            rule_id=result.rule_id,
            reasoning=f"Pattern matched: {result.matched_pattern}",
            metadata={
                "matched_pattern": result.matched_pattern,
                "match_position": result.match_position,
                "layer_latencies": layer_latencies,
            },
            processing_time_ms=total_latency,
        )

    def _build_decision_from_semantic(
        self,
        result: SemanticRouteResult,
        user_input: str,
        start_time: float,
        layer_latencies: Dict[str, float],
    ) -> RoutingDecision:
        """Build routing decision from semantic route result."""
        total_latency = (time.perf_counter() - start_time) * 1000
        self._metrics.record_latency(total_latency)

        # Get completeness assessment
        completeness = self._get_completeness(
            result.intent_category,
            user_input,
        )

        # Extract workflow and risk from metadata
        workflow_type = WorkflowType.SIMPLE
        risk_level = RiskLevel.MEDIUM

        if result.metadata:
            workflow_str = result.metadata.get("workflow_type", "simple")
            risk_str = result.metadata.get("risk_level", "medium")
            workflow_type = WorkflowType.from_string(workflow_str)
            risk_level = RiskLevel.from_string(risk_str)

        return RoutingDecision(
            intent_category=result.intent_category or ITIntentCategory.UNKNOWN,
            sub_intent=result.sub_intent,
            confidence=result.similarity,
            workflow_type=workflow_type,
            risk_level=risk_level,
            completeness=completeness,
            routing_layer="semantic",
            reasoning=f"Semantic route: {result.route_name}",
            metadata={
                "route_name": result.route_name,
                "similarity": result.similarity,
                "layer_latencies": layer_latencies,
            },
            processing_time_ms=total_latency,
        )

    def _build_decision_from_llm(
        self,
        result: LLMClassificationResult,
        user_input: str,
        start_time: float,
        layer_latencies: Dict[str, float],
    ) -> RoutingDecision:
        """Build routing decision from LLM classification result."""
        total_latency = (time.perf_counter() - start_time) * 1000
        self._metrics.record_latency(total_latency)

        # Use LLM's completeness or fallback to checker
        if result.completeness and result.completeness.completeness_score > 0:
            completeness = result.completeness
        else:
            completeness = self._get_completeness(
                result.intent_category,
                user_input,
            )

        return RoutingDecision(
            intent_category=result.intent_category,
            sub_intent=result.sub_intent,
            confidence=result.confidence,
            workflow_type=self._get_workflow_type(result.intent_category, result.sub_intent),
            risk_level=self._get_risk_level(result.intent_category, user_input),
            completeness=completeness,
            routing_layer="llm",
            reasoning=result.reasoning,
            metadata={
                "model": result.model,
                "usage": result.usage,
                "layer_latencies": layer_latencies,
            },
            processing_time_ms=total_latency,
        )

    def _build_unknown_decision(
        self,
        user_input: str,
        start_time: float,
        layer_latencies: Dict[str, float],
    ) -> RoutingDecision:
        """Build decision when no classification possible."""
        total_latency = (time.perf_counter() - start_time) * 1000
        self._metrics.record_latency(total_latency)

        return RoutingDecision(
            intent_category=ITIntentCategory.UNKNOWN,
            confidence=0.0,
            workflow_type=WorkflowType.HANDOFF,
            risk_level=RiskLevel.MEDIUM,
            completeness=CompletenessInfo(is_complete=False, completeness_score=0.0),
            routing_layer="none",
            reasoning="Unable to classify with sufficient confidence",
            metadata={
                "layer_latencies": layer_latencies,
                "input_preview": user_input[:50],
            },
            processing_time_ms=total_latency,
        )

    def _get_completeness(
        self,
        intent_category: Optional[ITIntentCategory],
        user_input: str,
    ) -> CompletenessInfo:
        """Get completeness assessment for the intent."""
        if not self.config.enable_completeness or not intent_category:
            return CompletenessInfo()

        return self.completeness_checker.check(
            intent_category=intent_category,
            user_input=user_input,
        )

    def _get_workflow_type(
        self,
        intent_category: Optional[ITIntentCategory],
        sub_intent: Optional[str] = None,
    ) -> WorkflowType:
        """
        Determine workflow type based on intent.

        Mapping:
        - INCIDENT + system_unavailable → MAGENTIC
        - INCIDENT + etl_failure → SEQUENTIAL
        - CHANGE + release_deployment → MAGENTIC
        - CHANGE + configuration_update → SEQUENTIAL
        - REQUEST → SIMPLE
        - QUERY → SIMPLE
        - UNKNOWN → HANDOFF
        """
        if not intent_category:
            return WorkflowType.HANDOFF

        # Complex incident handling
        if intent_category == ITIntentCategory.INCIDENT:
            if sub_intent in ["system_unavailable", "system_down"]:
                return WorkflowType.MAGENTIC
            return WorkflowType.SEQUENTIAL

        # Change request handling
        if intent_category == ITIntentCategory.CHANGE:
            if sub_intent in ["release_deployment", "database_change"]:
                return WorkflowType.MAGENTIC
            return WorkflowType.SEQUENTIAL

        # Simple workflows
        if intent_category in [ITIntentCategory.REQUEST, ITIntentCategory.QUERY]:
            return WorkflowType.SIMPLE

        return WorkflowType.HANDOFF

    def _get_risk_level(
        self,
        intent_category: Optional[ITIntentCategory],
        user_input: str,
    ) -> RiskLevel:
        """
        Determine risk level based on intent and keywords.

        Rules:
        - 緊急/嚴重/critical + INCIDENT → CRITICAL
        - 影響/生產 + INCIDENT → HIGH
        - 生產/資料庫 + CHANGE → HIGH
        - QUERY → LOW
        """
        if not intent_category:
            return RiskLevel.MEDIUM

        user_input_lower = user_input.lower()

        # Check for critical keywords
        critical_keywords = ["緊急", "嚴重", "critical", "urgent", "停機", "當機"]
        high_keywords = ["影響", "生產", "無法", "業務", "客戶"]

        if intent_category == ITIntentCategory.INCIDENT:
            if any(kw in user_input_lower for kw in critical_keywords):
                return RiskLevel.CRITICAL
            if any(kw in user_input_lower for kw in high_keywords):
                return RiskLevel.HIGH
            return RiskLevel.MEDIUM

        if intent_category == ITIntentCategory.CHANGE:
            if "生產" in user_input_lower or "資料庫" in user_input_lower:
                return RiskLevel.HIGH
            return RiskLevel.MEDIUM

        if intent_category == ITIntentCategory.QUERY:
            return RiskLevel.LOW

        return RiskLevel.MEDIUM

    def get_metrics(self) -> Dict[str, Any]:
        """Get routing metrics."""
        return self._metrics.to_dict()

    def reset_metrics(self) -> None:
        """Reset routing metrics."""
        self._metrics = RoutingMetrics()


class MockBusinessIntentRouter(BusinessIntentRouter):
    """
    Mock BusinessIntentRouter for testing without external dependencies.

    Uses mock implementations of all components.
    """

    def __init__(
        self,
        pattern_rules: Optional[Dict[str, Any]] = None,
        semantic_routes: Optional[List[Any]] = None,
        config: Optional[RouterConfig] = None,
    ):
        """
        Initialize mock router with optional test configurations.

        Args:
            pattern_rules: Pattern rules dictionary (optional)
            semantic_routes: List of semantic routes (optional)
            config: Router configuration (optional)
        """
        # Create mock components
        pattern_matcher = PatternMatcher(rules_dict=pattern_rules or {"rules": []})
        semantic_router = MockSemanticRouter(routes=semantic_routes or [])
        llm_classifier = MockLLMClassifier()
        completeness_checker = MockCompletenessChecker()

        super().__init__(
            pattern_matcher=pattern_matcher,
            semantic_router=semantic_router,
            llm_classifier=llm_classifier,
            completeness_checker=completeness_checker,
            config=config or RouterConfig(),
        )


# =============================================================================
# Factory Functions
# =============================================================================

def create_router(
    pattern_rules_path: Optional[str] = None,
    pattern_rules_dict: Optional[Dict[str, Any]] = None,
    semantic_routes: Optional[List[Any]] = None,
    llm_api_key: Optional[str] = None,
    config: Optional[RouterConfig] = None,
) -> BusinessIntentRouter:
    """
    Factory function to create a fully configured BusinessIntentRouter.

    Args:
        pattern_rules_path: Path to pattern rules YAML file
        pattern_rules_dict: Pattern rules dictionary (alternative to file)
        semantic_routes: List of SemanticRoute definitions
        llm_api_key: Anthropic API key for LLM classifier
        config: Router configuration

    Returns:
        Configured BusinessIntentRouter instance
    """
    # Create pattern matcher
    if pattern_rules_path:
        pattern_matcher = PatternMatcher(rules_path=pattern_rules_path)
    elif pattern_rules_dict:
        pattern_matcher = PatternMatcher(rules_dict=pattern_rules_dict)
    else:
        pattern_matcher = PatternMatcher(rules_dict={"rules": []})

    # Create semantic router
    semantic_router = SemanticRouter(routes=semantic_routes or [])

    # Create LLM classifier
    llm_classifier = LLMClassifier(api_key=llm_api_key)

    # Create completeness checker
    completeness_checker = CompletenessChecker()

    return BusinessIntentRouter(
        pattern_matcher=pattern_matcher,
        semantic_router=semantic_router,
        llm_classifier=llm_classifier,
        completeness_checker=completeness_checker,
        config=config or RouterConfig.from_env(),
    )


def create_mock_router(
    config: Optional[RouterConfig] = None,
) -> MockBusinessIntentRouter:
    """
    Factory function to create a mock router for testing.

    Args:
        config: Router configuration

    Returns:
        MockBusinessIntentRouter instance
    """
    return MockBusinessIntentRouter(config=config)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "RouterConfig",
    "RoutingMetrics",
    "BusinessIntentRouter",
    "MockBusinessIntentRouter",
    "create_router",
    "create_mock_router",
]
