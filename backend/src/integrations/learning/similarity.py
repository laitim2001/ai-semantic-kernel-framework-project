# =============================================================================
# IPA Platform - Similarity Calculator
# =============================================================================
# Sprint 80: S80-1 - Few-shot 學習系統 (8 pts)
#
# This module provides similarity calculation for case matching.
# Supports semantic similarity (embedding-based) and structural similarity.
# =============================================================================

import logging
from typing import List, Optional, Set, Tuple

from .types import Case, LearningConfig, SimilarityResult, DEFAULT_LEARNING_CONFIG


logger = logging.getLogger(__name__)


class SimilarityCalculator:
    """
    Calculator for case similarity.

    Supports:
    - Semantic similarity using embeddings (cosine similarity)
    - Structural similarity using affected systems (Jaccard similarity)
    - Combined weighted similarity
    """

    def __init__(self, config: Optional[LearningConfig] = None):
        """
        Initialize the similarity calculator.

        Args:
            config: Learning configuration. Uses defaults if not provided.
        """
        self.config = config or DEFAULT_LEARNING_CONFIG

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector.
            vec2: Second vector.

        Returns:
            Cosine similarity score (0.0 to 1.0).
        """
        if not vec1 or not vec2:
            return 0.0

        if len(vec1) != len(vec2):
            logger.warning(
                f"Vector dimension mismatch: {len(vec1)} vs {len(vec2)}"
            )
            return 0.0

        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        # Calculate magnitudes
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        similarity = dot_product / (magnitude1 * magnitude2)

        # Normalize to 0-1 range (cosine can be -1 to 1)
        return (similarity + 1) / 2

    @staticmethod
    def jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
        """
        Calculate Jaccard similarity between two sets.

        Args:
            set1: First set of items.
            set2: Second set of items.

        Returns:
            Jaccard similarity score (0.0 to 1.0).
        """
        if not set1 and not set2:
            return 1.0  # Both empty = identical

        if not set1 or not set2:
            return 0.0  # One empty = no overlap

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        return intersection / union if union > 0 else 0.0

    def calculate_semantic_similarity(
        self,
        embedding1: Optional[List[float]],
        embedding2: Optional[List[float]],
    ) -> float:
        """
        Calculate semantic similarity using embeddings.

        Args:
            embedding1: First embedding vector.
            embedding2: Second embedding vector.

        Returns:
            Semantic similarity score (0.0 to 1.0).
        """
        if not embedding1 or not embedding2:
            return 0.0

        return self.cosine_similarity(embedding1, embedding2)

    def calculate_structural_similarity(
        self,
        systems1: List[str],
        systems2: List[str],
    ) -> float:
        """
        Calculate structural similarity based on affected systems.

        Args:
            systems1: First list of affected systems.
            systems2: Second list of affected systems.

        Returns:
            Structural similarity score (0.0 to 1.0).
        """
        # Normalize system names (lowercase, strip)
        set1 = {s.lower().strip() for s in systems1}
        set2 = {s.lower().strip() for s in systems2}

        return self.jaccard_similarity(set1, set2)

    def calculate_combined_similarity(
        self,
        semantic_score: float,
        structural_score: float,
    ) -> float:
        """
        Calculate weighted combined similarity.

        Args:
            semantic_score: Semantic similarity score.
            structural_score: Structural similarity score.

        Returns:
            Combined similarity score (0.0 to 1.0).
        """
        return (
            self.config.semantic_weight * semantic_score
            + self.config.structural_weight * structural_score
        )

    def calculate_case_similarity(
        self,
        case: Case,
        query_embedding: Optional[List[float]],
        query_systems: List[str],
    ) -> SimilarityResult:
        """
        Calculate similarity between a case and a query.

        Args:
            case: The historical case to compare.
            query_embedding: Embedding of the query/event description.
            query_systems: List of affected systems in the query.

        Returns:
            SimilarityResult with all scores.
        """
        # Calculate semantic similarity
        semantic_score = self.calculate_semantic_similarity(
            case.embedding, query_embedding
        )

        # Calculate structural similarity
        structural_score = self.calculate_structural_similarity(
            case.affected_systems, query_systems
        )

        # Calculate combined score
        combined_score = self.calculate_combined_similarity(
            semantic_score, structural_score
        )

        return SimilarityResult(
            case=case,
            semantic_score=semantic_score,
            structural_score=structural_score,
            combined_score=combined_score,
        )

    def rank_cases(
        self,
        cases: List[Case],
        query_embedding: Optional[List[float]],
        query_systems: List[str],
        top_k: Optional[int] = None,
        min_score: Optional[float] = None,
    ) -> List[SimilarityResult]:
        """
        Rank cases by similarity to a query.

        Args:
            cases: List of cases to rank.
            query_embedding: Embedding of the query/event description.
            query_systems: List of affected systems in the query.
            top_k: Return only top K results. Uses config default if not provided.
            min_score: Minimum similarity score. Uses config default if not provided.

        Returns:
            List of SimilarityResult sorted by combined score (descending).
        """
        top_k = top_k or self.config.top_k_cases
        min_score = min_score if min_score is not None else self.config.min_similarity_score

        # Calculate similarity for all cases
        results = []
        for case in cases:
            result = self.calculate_case_similarity(
                case, query_embedding, query_systems
            )

            # Filter by minimum score
            if result.combined_score >= min_score:
                results.append(result)

        # Sort by combined score (descending)
        results.sort(key=lambda x: x.combined_score, reverse=True)

        # Return top K
        return results[:top_k]

    def find_most_similar(
        self,
        cases: List[Case],
        query_embedding: Optional[List[float]],
        query_systems: List[str],
    ) -> Optional[SimilarityResult]:
        """
        Find the most similar case to a query.

        Args:
            cases: List of cases to search.
            query_embedding: Embedding of the query/event description.
            query_systems: List of affected systems in the query.

        Returns:
            Most similar case result, or None if no cases meet minimum score.
        """
        results = self.rank_cases(
            cases, query_embedding, query_systems, top_k=1
        )
        return results[0] if results else None

    @staticmethod
    def text_similarity_simple(text1: str, text2: str) -> float:
        """
        Simple text similarity using word overlap (fallback when no embeddings).

        Args:
            text1: First text.
            text2: Second text.

        Returns:
            Similarity score (0.0 to 1.0).
        """
        # Tokenize (simple split)
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        # Remove common stop words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for"}
        words1 = words1 - stop_words
        words2 = words2 - stop_words

        if not words1 and not words2:
            return 1.0

        if not words1 or not words2:
            return 0.0

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0
