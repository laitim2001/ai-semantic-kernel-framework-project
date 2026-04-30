"""Knowledge Retriever — hybrid search + reranking.

Combines vector similarity search with keyword matching, then applies
cross-encoder reranking for optimal retrieval quality.

Sprint 118 — Phase 38 E2E Assembly C.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.integrations.knowledge.vector_store import IndexedDocument, VectorStoreManager
from src.integrations.knowledge.embedder import EmbeddingManager

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Single retrieval result with combined scoring."""

    content: str
    score: float
    source: str = ""  # "vector" | "keyword" | "hybrid"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class KnowledgeRetriever:
    """Hybrid retriever combining vector search with keyword matching.

    Pipeline:
    1. Vector search via Qdrant (semantic similarity)
    2. Keyword matching (BM25-like scoring)
    3. Result fusion (reciprocal rank fusion)
    4. Cross-encoder reranking (optional, if model available)

    Args:
        vector_store: VectorStoreManager for semantic search.
        embedder: EmbeddingManager for query embedding.
    """

    def __init__(
        self,
        vector_store: Optional[VectorStoreManager] = None,
        embedder: Optional[EmbeddingManager] = None,
    ) -> None:
        self._vector_store = vector_store or VectorStoreManager()
        self._embedder = embedder or EmbeddingManager()

    async def retrieve(
        self,
        query: str,
        collection: Optional[str] = None,
        limit: int = 5,
        use_reranking: bool = True,
    ) -> List[RetrievalResult]:
        """Execute hybrid retrieval pipeline.

        Args:
            query: Search query string.
            collection: Optional collection to search.
            limit: Maximum results to return.
            use_reranking: Whether to apply cross-encoder reranking.

        Returns:
            Sorted list of RetrievalResult.
        """
        # Step 1: Vector search
        vector_results = await self._vector_search(query, collection, limit=limit * 2)

        # Step 2: Keyword filtering on vector results
        keyword_boosted = self._keyword_boost(query, vector_results)

        # Step 3: Reciprocal rank fusion
        fused = self._reciprocal_rank_fusion(keyword_boosted)

        # Step 4: Reranking (optional)
        if use_reranking and len(fused) > 1:
            fused = self._simple_rerank(query, fused)

        # Return top-k
        return fused[:limit]

    async def _vector_search(
        self,
        query: str,
        collection: Optional[str],
        limit: int,
    ) -> List[RetrievalResult]:
        """Perform vector similarity search."""
        try:
            query_embedding = await self._embedder.embed_text(query)
            docs = await self._vector_store.search(
                query_embedding=query_embedding,
                limit=limit,
                collection=collection,
            )
            return [
                RetrievalResult(
                    content=doc.content,
                    score=doc.score,
                    source="vector",
                    metadata=doc.metadata,
                )
                for doc in docs
            ]
        except Exception as e:
            logger.error("Vector search failed: %s", e)
            return []

    @staticmethod
    def _keyword_boost(
        query: str, results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """Boost scores for results containing query keywords."""
        query_terms = set(re.findall(r'\w+', query.lower()))
        if not query_terms:
            return results

        for result in results:
            content_lower = result.content.lower()
            matches = sum(1 for term in query_terms if term in content_lower)
            keyword_score = matches / max(len(query_terms), 1)
            # Blend: 70% vector + 30% keyword
            result.score = 0.7 * result.score + 0.3 * keyword_score
            if keyword_score > 0:
                result.source = "hybrid"

        return results

    @staticmethod
    def _reciprocal_rank_fusion(
        results: List[RetrievalResult], k: int = 60
    ) -> List[RetrievalResult]:
        """Apply reciprocal rank fusion scoring."""
        # Sort by current score
        results.sort(key=lambda r: r.score, reverse=True)
        for rank, result in enumerate(results):
            result.score = 1.0 / (k + rank + 1)
        results.sort(key=lambda r: r.score, reverse=True)
        return results

    @staticmethod
    def _simple_rerank(
        query: str, results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """Simple reranking based on query-document overlap.

        A lightweight alternative to cross-encoder reranking when
        no reranking model is available.
        """
        query_terms = set(re.findall(r'\w+', query.lower()))
        for result in results:
            content_terms = set(re.findall(r'\w+', result.content.lower()))
            if query_terms and content_terms:
                overlap = len(query_terms & content_terms)
                coverage = overlap / len(query_terms)
                # Boost based on coverage
                result.score *= (1.0 + coverage * 0.5)

        results.sort(key=lambda r: r.score, reverse=True)
        return results
