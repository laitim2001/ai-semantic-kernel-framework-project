"""
Azure Semantic Router Implementation

Uses Azure AI Search for vector similarity matching instead of the
Aurelio semantic-router library. Produces ``SemanticRouteResult`` objects
compatible with ``BusinessIntentRouter._build_decision_from_semantic()``.

Sprint 115: Story 115-2 - Azure Semantic Router Components (Phase 32)
"""

import logging
import time
from typing import Any, Dict, List, Optional

from ..models import (
    ITIntentCategory,
    RiskLevel,
    SemanticRouteResult,
    WorkflowType,
)
from .azure_search_client import AzureSearchClient
from .embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class AzureSemanticRouter:
    """Semantic router using Azure AI Search for vector similarity matching.

    Generates an embedding for the user input via ``EmbeddingService``,
    searches the Azure AI Search index via ``AzureSearchClient``, and
    returns the best match as a ``SemanticRouteResult``.

    The result includes metadata fields (``workflow_type``, ``risk_level``,
    ``description``, ``processing_time_ms``) so that the downstream
    ``BusinessIntentRouter._build_decision_from_semantic()`` can consume
    it without changes.

    Attributes:
        similarity_threshold: Minimum cosine similarity to accept a match.
        top_k: Default number of nearest neighbours to retrieve.
    """

    def __init__(
        self,
        search_client: AzureSearchClient,
        embedding_service: EmbeddingService,
        similarity_threshold: float = 0.85,
        top_k: int = 3,
    ) -> None:
        """Initialize the Azure Semantic Router.

        Args:
            search_client: Configured ``AzureSearchClient`` instance.
            embedding_service: Configured ``EmbeddingService`` instance.
            similarity_threshold: Minimum similarity for a positive match.
            top_k: Number of nearest neighbours to retrieve per search.

        Raises:
            ValueError: If *similarity_threshold* is outside [0, 1].
        """
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError("similarity_threshold must be between 0.0 and 1.0")

        self._search_client = search_client
        self._embedding_service = embedding_service
        self.similarity_threshold = similarity_threshold
        self.top_k = top_k
        self._available: Optional[bool] = None

        logger.info(
            "AzureSemanticRouter initialized: threshold=%.2f, top_k=%d",
            similarity_threshold,
            top_k,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_similarity(document: Dict[str, Any]) -> float:
        """Extract the similarity score from an Azure Search result.

        For pure vector search Azure AI Search returns
        ``@search.score`` in the range [0, 1] when using cosine metric.
        """
        return float(document.get("@search.score", 0.0))

    @staticmethod
    def _document_to_result(
        document: Dict[str, Any],
        similarity: float,
        processing_time_ms: float,
    ) -> SemanticRouteResult:
        """Convert an Azure Search document into a ``SemanticRouteResult``."""
        category_str = document.get("category", "unknown")
        intent_category = ITIntentCategory.from_string(category_str)

        workflow_str = document.get("workflow_type", "simple")
        risk_str = document.get("risk_level", "medium")

        return SemanticRouteResult(
            matched=True,
            intent_category=intent_category,
            sub_intent=document.get("sub_intent"),
            similarity=similarity,
            route_name=document.get("route_name"),
            metadata={
                "workflow_type": workflow_str,
                "risk_level": risk_str,
                "description": document.get("description", ""),
                "processing_time_ms": processing_time_ms,
            },
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def route(self, user_input: str) -> SemanticRouteResult:
        """Route user input using Azure AI Search vector similarity.

        Steps:
        1. Generate embedding for *user_input*.
        2. Perform vector search on the Azure AI Search index.
        3. Filter results by ``similarity_threshold``.
        4. Return the best match as a ``SemanticRouteResult``.

        Args:
            user_input: User's natural-language input text.

        Returns:
            ``SemanticRouteResult`` with match information. Returns
            ``SemanticRouteResult.no_match()`` when no result exceeds
            the similarity threshold or when an error occurs.
        """
        start_time = time.perf_counter()

        try:
            # Step 1: generate embedding
            vector = await self._embedding_service.get_embedding(user_input)

            # Step 2: vector search
            results = await self._search_client.vector_search(
                vector=vector,
                top_k=self.top_k,
                filters="enabled eq true",
            )

            processing_time_ms = (time.perf_counter() - start_time) * 1000

            if not results:
                logger.debug(
                    "No Azure Search results for: '%s' (%.1fms)",
                    user_input[:50],
                    processing_time_ms,
                )
                return SemanticRouteResult.no_match()

            # Step 3: pick best result and check threshold
            best = results[0]
            similarity = self._extract_similarity(best)

            if similarity < self.similarity_threshold:
                logger.debug(
                    "Below threshold (%.3f < %.3f): '%s'",
                    similarity,
                    self.similarity_threshold,
                    user_input[:50],
                )
                return SemanticRouteResult.no_match(similarity=similarity)

            # Step 4: build result
            result = self._document_to_result(best, similarity, processing_time_ms)

            logger.info(
                "Azure semantic match: %s (similarity=%.3f, route=%s, %.1fms)",
                result.intent_category.value if result.intent_category else "unknown",
                similarity,
                result.route_name,
                processing_time_ms,
            )
            return result

        except Exception as exc:
            processing_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "Azure semantic routing error (%.1fms): %s",
                processing_time_ms,
                exc,
            )
            return SemanticRouteResult.no_match()

    async def route_with_scores(
        self,
        user_input: str,
        top_k: Optional[int] = None,
    ) -> List[SemanticRouteResult]:
        """Route with multiple results and their similarity scores.

        Returns all results that exceed ``similarity_threshold``, ordered
        by descending similarity.

        Args:
            user_input: User's natural-language input text.
            top_k: Override number of results (uses instance default if None).

        Returns:
            List of ``SemanticRouteResult`` objects sorted by similarity.
        """
        effective_top_k = top_k if top_k is not None else self.top_k
        start_time = time.perf_counter()

        try:
            vector = await self._embedding_service.get_embedding(user_input)
            results = await self._search_client.vector_search(
                vector=vector,
                top_k=effective_top_k,
                filters="enabled eq true",
            )

            processing_time_ms = (time.perf_counter() - start_time) * 1000

            matched: List[SemanticRouteResult] = []
            for doc in results:
                similarity = self._extract_similarity(doc)
                if similarity >= self.similarity_threshold:
                    matched.append(
                        self._document_to_result(doc, similarity, processing_time_ms)
                    )

            logger.debug(
                "Azure route_with_scores: %d/%d above threshold (%.1fms)",
                len(matched),
                len(results),
                processing_time_ms,
            )
            return matched

        except Exception as exc:
            logger.error("Azure route_with_scores error: %s", exc)
            return []

    @property
    def is_available(self) -> bool:
        """Check if Azure Search is accessible.

        Caches the result of the first successful health check.
        Subsequent calls return the cached value unless it was False.

        Returns:
            True if the service responds, False otherwise.
        """
        # Synchronous property -- cannot await.  Return cached or False.
        if self._available is True:
            return True
        return False

    async def check_availability(self) -> bool:
        """Async health check that updates the cached ``is_available`` state.

        Returns:
            True if the search service is reachable.
        """
        try:
            healthy = await self._search_client.health_check()
            self._available = healthy
            return healthy
        except Exception as exc:
            logger.warning("Azure Search availability check failed: %s", exc)
            self._available = False
            return False
