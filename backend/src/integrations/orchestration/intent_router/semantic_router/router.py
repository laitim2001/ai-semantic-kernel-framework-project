"""
Semantic Router Implementation

Uses Aurelio Semantic Router for vector-based semantic matching.
Provides Layer 2 routing with configurable similarity threshold.

Sprint 92: Semantic Router + LLM Classifier (Phase 28)
"""

import logging
import time
from typing import Any, Dict, List, Optional

from ..models import (
    ITIntentCategory,
    RiskLevel,
    SemanticRoute,
    SemanticRouteResult,
    WorkflowType,
)

logger = logging.getLogger(__name__)


# Flag to track if semantic-router is available
_SEMANTIC_ROUTER_AVAILABLE = False
_Route = None
_AurelioRouter = None
_OpenAIEncoder = None

try:
    from semantic_router import Route
    from semantic_router.layer import RouteLayer
    from semantic_router.encoders import OpenAIEncoder

    _Route = Route
    _AurelioRouter = RouteLayer
    _OpenAIEncoder = OpenAIEncoder
    _SEMANTIC_ROUTER_AVAILABLE = True
    logger.info("Semantic Router library loaded successfully")
except ImportError:
    logger.warning(
        "semantic-router library not installed. "
        "Install with: pip install semantic-router"
    )


class SemanticRouter:
    """
    Semantic Router for IT service intent classification.

    Uses vector similarity to match user inputs against predefined routes.
    Each route contains example utterances that define the semantic space.

    Attributes:
        threshold: Minimum similarity score to consider a match (default: 0.85)
        routes: List of SemanticRoute definitions
        encoder_name: Name of the encoder model to use

    Example:
        >>> router = SemanticRouter(routes=routes, threshold=0.85)
        >>> result = await router.route("ETL 今天跑失敗了")
        >>> print(result.intent_category)  # ITIntentCategory.INCIDENT
    """

    def __init__(
        self,
        routes: Optional[List[SemanticRoute]] = None,
        threshold: float = 0.85,
        encoder_name: str = "text-embedding-3-small",
        openai_api_key: Optional[str] = None,
    ):
        """
        Initialize the Semantic Router.

        Args:
            routes: List of SemanticRoute definitions
            threshold: Minimum similarity for a match (0.0 to 1.0)
            encoder_name: OpenAI encoder model name
            openai_api_key: OpenAI API key (optional, uses env var if not provided)
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")

        self.threshold = threshold
        self.routes = routes or []
        self.encoder_name = encoder_name
        self._openai_api_key = openai_api_key
        self._router: Optional[Any] = None
        self._route_metadata: Dict[str, SemanticRoute] = {}
        self._initialized = False

        # Pre-build route metadata mapping
        for route in self.routes:
            self._route_metadata[route.name] = route

    @property
    def is_available(self) -> bool:
        """Check if semantic-router library is available."""
        return _SEMANTIC_ROUTER_AVAILABLE

    def _initialize_router(self) -> bool:
        """
        Initialize the Aurelio Router with configured routes.

        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            return True

        if not _SEMANTIC_ROUTER_AVAILABLE:
            logger.warning("Cannot initialize: semantic-router not installed")
            return False

        if not self.routes:
            logger.warning("Cannot initialize: no routes defined")
            return False

        try:
            # Create encoder
            encoder_kwargs = {"name": self.encoder_name}
            if self._openai_api_key:
                encoder_kwargs["openai_api_key"] = self._openai_api_key

            encoder = _OpenAIEncoder(**encoder_kwargs)

            # Convert SemanticRoute to Aurelio Route format
            aurelio_routes = []
            for route in self.routes:
                if not route.enabled:
                    continue

                aurelio_route = _Route(
                    name=route.name,
                    utterances=route.utterances,
                    metadata={
                        "category": route.category.value,
                        "sub_intent": route.sub_intent,
                        "workflow_type": route.workflow_type.value,
                        "risk_level": route.risk_level.value,
                        "description": route.description,
                    },
                )
                aurelio_routes.append(aurelio_route)

            # Create router layer
            self._router = _AurelioRouter(
                encoder=encoder,
                routes=aurelio_routes,
            )

            self._initialized = True
            logger.info(
                f"Semantic Router initialized with {len(aurelio_routes)} routes"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Semantic Router: {e}")
            return False

    async def route(self, user_input: str) -> SemanticRouteResult:
        """
        Route user input using semantic similarity.

        Args:
            user_input: The user's input text

        Returns:
            SemanticRouteResult with match information

        Note:
            If similarity is below threshold, returns no_match result.
        """
        start_time = time.perf_counter()

        # Check if router is available
        if not _SEMANTIC_ROUTER_AVAILABLE:
            logger.warning("Semantic routing unavailable: library not installed")
            return SemanticRouteResult.no_match()

        # Initialize if needed
        if not self._initialized:
            if not self._initialize_router():
                return SemanticRouteResult.no_match()

        try:
            # Call the router (synchronous call wrapped for async interface)
            result = self._router(user_input)

            processing_time = (time.perf_counter() - start_time) * 1000

            # Handle no match case
            if result is None or result.name is None:
                logger.debug(
                    f"No semantic match for: '{user_input[:50]}...' "
                    f"(time: {processing_time:.2f}ms)"
                )
                return SemanticRouteResult.no_match()

            # Get similarity score
            # Note: RouteLayer returns RouteChoice with similarity attribute
            similarity = getattr(result, "similarity", 0.0)

            # Check threshold
            if similarity < self.threshold:
                logger.debug(
                    f"Below threshold ({similarity:.3f} < {self.threshold}): "
                    f"'{user_input[:50]}...'"
                )
                return SemanticRouteResult.no_match(similarity=similarity)

            # Get route metadata
            route_name = result.name
            route_def = self._route_metadata.get(route_name)

            if route_def:
                return SemanticRouteResult(
                    matched=True,
                    intent_category=route_def.category,
                    sub_intent=route_def.sub_intent,
                    similarity=similarity,
                    route_name=route_name,
                    metadata={
                        "workflow_type": route_def.workflow_type.value,
                        "risk_level": route_def.risk_level.value,
                        "description": route_def.description,
                        "processing_time_ms": processing_time,
                    },
                )
            else:
                # Route found but no metadata (shouldn't happen normally)
                logger.warning(f"Route '{route_name}' has no metadata definition")
                return SemanticRouteResult(
                    matched=True,
                    similarity=similarity,
                    route_name=route_name,
                    metadata={"processing_time_ms": processing_time},
                )

        except Exception as e:
            logger.error(f"Semantic routing error: {e}")
            return SemanticRouteResult.no_match()

    def add_route(self, route: SemanticRoute) -> None:
        """
        Add a new route to the router.

        Note: Router will need to be re-initialized after adding routes.

        Args:
            route: SemanticRoute to add
        """
        self.routes.append(route)
        self._route_metadata[route.name] = route
        self._initialized = False  # Force re-initialization

    def remove_route(self, route_name: str) -> bool:
        """
        Remove a route by name.

        Args:
            route_name: Name of route to remove

        Returns:
            True if route was found and removed
        """
        for i, route in enumerate(self.routes):
            if route.name == route_name:
                self.routes.pop(i)
                self._route_metadata.pop(route_name, None)
                self._initialized = False  # Force re-initialization
                return True
        return False

    def get_route_names(self) -> List[str]:
        """Get list of all route names."""
        return [r.name for r in self.routes]

    def get_route_count(self) -> int:
        """Get total number of routes."""
        return len(self.routes)

    def get_enabled_route_count(self) -> int:
        """Get number of enabled routes."""
        return sum(1 for r in self.routes if r.enabled)


class MockSemanticRouter(SemanticRouter):
    """
    Mock Semantic Router for testing without external dependencies.

    Uses simple keyword matching instead of vector similarity.
    """

    def __init__(
        self,
        routes: Optional[List[SemanticRoute]] = None,
        threshold: float = 0.85,
        **kwargs,
    ):
        super().__init__(routes=routes, threshold=threshold, **kwargs)
        self._initialized = True  # Always initialized for mock

    @property
    def is_available(self) -> bool:
        """Mock router is always available."""
        return True

    async def route(self, user_input: str) -> SemanticRouteResult:
        """
        Mock routing using simple keyword matching.

        Args:
            user_input: The user's input text

        Returns:
            SemanticRouteResult based on keyword matching
        """
        user_input_lower = user_input.lower()

        best_match: Optional[SemanticRoute] = None
        best_score = 0.0

        for route in self.routes:
            if not route.enabled:
                continue

            # Enhanced keyword matching for Chinese text
            match_score = 0.0
            max_utterance_score = 0.0

            for utterance in route.utterances:
                utterance_lower = utterance.lower()

                # Calculate character-level overlap for Chinese text
                common_chars = 0
                for char in utterance_lower:
                    if char in user_input_lower and char not in " \t\n":
                        common_chars += 1

                # Normalize by utterance length
                if len(utterance_lower) > 0:
                    # Score based on how many chars from utterance appear in input
                    char_coverage = common_chars / len(utterance_lower.replace(" ", ""))

                    # Also check for substring matches
                    substring_bonus = 0.0
                    if utterance_lower in user_input_lower:
                        substring_bonus = 0.3
                    elif user_input_lower in utterance_lower:
                        substring_bonus = 0.2

                    utterance_score = min(char_coverage + substring_bonus, 1.0)
                    max_utterance_score = max(max_utterance_score, utterance_score)

            match_score = max_utterance_score

            if match_score > best_score:
                best_score = match_score
                best_match = route

        # Check threshold
        if best_score < self.threshold or best_match is None:
            return SemanticRouteResult.no_match(similarity=best_score)

        return SemanticRouteResult(
            matched=True,
            intent_category=best_match.category,
            sub_intent=best_match.sub_intent,
            similarity=best_score,
            route_name=best_match.name,
            metadata={
                "workflow_type": best_match.workflow_type.value,
                "risk_level": best_match.risk_level.value,
                "mock": True,
            },
        )
