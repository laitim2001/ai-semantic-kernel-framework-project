# =============================================================================
# IPA Platform - Embedding Service
# =============================================================================
# Sprint 79: S79-2 - mem0 長期記憶整合 (10 pts)
#
# This module provides embedding generation for memory content.
# Supports batch processing and caching for efficiency.
#
# Architecture:
#   EmbeddingService
#   ├── embed_text()      - Generate embedding for single text
#   ├── embed_batch()     - Generate embeddings for multiple texts
#   └── compute_similarity() - Calculate cosine similarity
# =============================================================================

import logging
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .types import MemoryConfig, DEFAULT_MEMORY_CONFIG


logger = logging.getLogger(__name__)


class EmbeddingCache:
    """Simple in-memory cache for embeddings with TTL."""

    def __init__(self, ttl_seconds: int = 3600):
        """
        Initialize the cache.

        Args:
            ttl_seconds: Time-to-live for cached items in seconds.
        """
        self._cache: Dict[str, Tuple[List[float], datetime]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)

    def _get_key(self, text: str, model: str) -> str:
        """Generate cache key from text and model."""
        content = f"{model}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()

    def get(self, text: str, model: str) -> Optional[List[float]]:
        """
        Get cached embedding.

        Args:
            text: The text that was embedded.
            model: The model used for embedding.

        Returns:
            Cached embedding if found and not expired, None otherwise.
        """
        key = self._get_key(text, model)
        if key in self._cache:
            embedding, timestamp = self._cache[key]
            if datetime.utcnow() - timestamp < self._ttl:
                return embedding
            # Expired, remove from cache
            del self._cache[key]
        return None

    def set(self, text: str, model: str, embedding: List[float]) -> None:
        """
        Cache an embedding.

        Args:
            text: The text that was embedded.
            model: The model used for embedding.
            embedding: The generated embedding.
        """
        key = self._get_key(text, model)
        self._cache[key] = (embedding, datetime.utcnow())

    def clear(self) -> None:
        """Clear all cached embeddings."""
        self._cache.clear()

    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.

        Returns:
            Number of entries removed.
        """
        now = datetime.utcnow()
        expired_keys = [
            key
            for key, (_, timestamp) in self._cache.items()
            if now - timestamp >= self._ttl
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)


class EmbeddingService:
    """
    Service for generating text embeddings.

    Uses OpenAI's embedding models with caching and batch processing.
    """

    def __init__(self, config: Optional[MemoryConfig] = None):
        """
        Initialize the embedding service.

        Args:
            config: Memory configuration. Uses defaults if not provided.
        """
        self.config = config or DEFAULT_MEMORY_CONFIG
        self._client = None
        self._cache = EmbeddingCache()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the OpenAI client."""
        if self._initialized:
            return

        try:
            import os
            from openai import AsyncOpenAI

            # Initialize OpenAI client
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                # Try Azure OpenAI
                azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
                azure_key = os.getenv("AZURE_OPENAI_API_KEY")

                if azure_endpoint and azure_key:
                    from openai import AsyncAzureOpenAI

                    self._client = AsyncAzureOpenAI(
                        api_key=azure_key,
                        azure_endpoint=azure_endpoint,
                        api_version="2024-02-01",
                    )
                else:
                    raise ValueError(
                        "No OpenAI API key found. Set OPENAI_API_KEY or "
                        "AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY"
                    )
            else:
                self._client = AsyncOpenAI(api_key=api_key)

            self._initialized = True
            logger.info("Embedding service initialized successfully")

        except ImportError:
            logger.error("OpenAI SDK not installed. Install with: pip install openai")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize embedding service: {e}")
            raise

    def _ensure_initialized(self) -> None:
        """Ensure the service is initialized."""
        if not self._initialized:
            raise RuntimeError(
                "EmbeddingService not initialized. Call initialize() first."
            )

    async def embed_text(
        self,
        text: str,
        use_cache: bool = True,
    ) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: The text to embed.
            use_cache: Whether to use caching.

        Returns:
            Embedding vector as a list of floats.
        """
        self._ensure_initialized()

        # Check cache
        if use_cache:
            cached = self._cache.get(text, self.config.embedding_model)
            if cached:
                logger.debug(f"Cache hit for embedding: {text[:50]}...")
                return cached

        try:
            # Generate embedding
            response = await self._client.embeddings.create(
                model=self.config.embedding_model,
                input=text,
            )

            embedding = response.data[0].embedding

            # Cache result
            if use_cache:
                self._cache.set(text, self.config.embedding_model, embedding)

            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    async def embed_batch(
        self,
        texts: List[str],
        use_cache: bool = True,
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Processes in batches according to config.embedding_batch_size.

        Args:
            texts: List of texts to embed.
            use_cache: Whether to use caching.

        Returns:
            List of embedding vectors.
        """
        self._ensure_initialized()

        if not texts:
            return []

        embeddings: List[Optional[List[float]]] = [None] * len(texts)
        texts_to_embed: List[Tuple[int, str]] = []

        # Check cache for each text
        if use_cache:
            for i, text in enumerate(texts):
                cached = self._cache.get(text, self.config.embedding_model)
                if cached:
                    embeddings[i] = cached
                else:
                    texts_to_embed.append((i, text))
        else:
            texts_to_embed = list(enumerate(texts))

        # Generate embeddings for uncached texts
        if texts_to_embed:
            try:
                # Process in batches
                batch_size = self.config.embedding_batch_size
                for batch_start in range(0, len(texts_to_embed), batch_size):
                    batch = texts_to_embed[batch_start : batch_start + batch_size]
                    batch_texts = [text for _, text in batch]

                    response = await self._client.embeddings.create(
                        model=self.config.embedding_model,
                        input=batch_texts,
                    )

                    # Assign embeddings to correct positions
                    for j, emb_data in enumerate(response.data):
                        original_idx = batch[j][0]
                        embedding = emb_data.embedding
                        embeddings[original_idx] = embedding

                        # Cache result
                        if use_cache:
                            self._cache.set(
                                batch[j][1],
                                self.config.embedding_model,
                                embedding,
                            )

                logger.info(
                    f"Generated {len(texts_to_embed)} embeddings "
                    f"({len(texts)} total with {len(texts) - len(texts_to_embed)} cached)"
                )

            except Exception as e:
                logger.error(f"Failed to generate batch embeddings: {e}")
                raise

        return embeddings  # type: ignore

    @staticmethod
    def compute_similarity(
        embedding1: List[float],
        embedding2: List[float],
    ) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector.
            embedding2: Second embedding vector.

        Returns:
            Cosine similarity score (0.0 to 1.0).
        """
        if len(embedding1) != len(embedding2):
            raise ValueError(
                f"Embedding dimensions must match: {len(embedding1)} vs {len(embedding2)}"
            )

        # Compute dot product
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))

        # Compute magnitudes
        magnitude1 = sum(a * a for a in embedding1) ** 0.5
        magnitude2 = sum(b * b for b in embedding2) ** 0.5

        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    @staticmethod
    def find_most_similar(
        query_embedding: List[float],
        embeddings: List[List[float]],
        top_k: int = 10,
    ) -> List[Tuple[int, float]]:
        """
        Find the most similar embeddings to a query.

        Args:
            query_embedding: The query embedding to compare against.
            embeddings: List of embeddings to search.
            top_k: Number of top results to return.

        Returns:
            List of (index, similarity_score) tuples, sorted by score descending.
        """
        similarities = [
            (i, EmbeddingService.compute_similarity(query_embedding, emb))
            for i, emb in enumerate(embeddings)
        ]

        # Sort by similarity score descending
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._cache.clear()
        logger.info("Embedding cache cleared")

    def cleanup_cache(self) -> int:
        """
        Remove expired entries from cache.

        Returns:
            Number of entries removed.
        """
        removed = self._cache.cleanup_expired()
        if removed > 0:
            logger.info(f"Removed {removed} expired cache entries")
        return removed

    async def close(self) -> None:
        """Clean up resources."""
        self._cache.clear()
        self._client = None
        self._initialized = False
        logger.info("Embedding service closed")
