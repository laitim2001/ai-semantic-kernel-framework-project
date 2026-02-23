"""
Azure OpenAI Embedding Service with LRU Caching

Generates text embeddings via Azure OpenAI with an in-memory
OrderedDict-based LRU cache to reduce redundant API calls.

Sprint 115: Story 115-2 - Azure Semantic Router Components (Phase 32)
"""

import asyncio
import logging
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from openai import AsyncAzureOpenAI, APIError, RateLimitError

logger = logging.getLogger(__name__)

# Default retry configuration
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_RETRY_BASE_DELAY = 1.0


class EmbeddingService:
    """Azure OpenAI embedding service with LRU caching.

    Uses ``openai.AsyncAzureOpenAI`` to generate text embeddings and
    caches results in an OrderedDict-based LRU cache (max *cache_size*
    entries). Cache keys are the raw input text.

    Attributes:
        deployment: Azure OpenAI embedding deployment name.
        cache_size: Maximum number of cached embeddings.
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment: str = "text-embedding-ada-002",
        api_version: str = "2024-02-15-preview",
        cache_size: int = 1024,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        retry_base_delay: float = _DEFAULT_RETRY_BASE_DELAY,
    ) -> None:
        """Initialize the embedding service.

        Args:
            endpoint: Azure OpenAI endpoint URL.
            api_key: Azure OpenAI API key.
            deployment: Embedding model deployment name.
            api_version: Azure OpenAI API version.
            cache_size: Max entries in the LRU cache.
            max_retries: Maximum retry attempts on rate-limit / transient errors.
            retry_base_delay: Base delay (seconds) for exponential backoff.
        """
        if not endpoint:
            raise ValueError("endpoint must not be empty")
        if not api_key:
            raise ValueError("api_key must not be empty")

        self.deployment = deployment
        self.cache_size = cache_size
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay

        self._client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )

        # OrderedDict-based LRU cache
        self._cache: OrderedDict[str, List[float]] = OrderedDict()
        self._cache_hits: int = 0
        self._cache_misses: int = 0

        logger.info(
            "EmbeddingService initialized: deployment=%s, cache_size=%d",
            deployment,
            cache_size,
        )

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _cache_get(self, key: str) -> Optional[List[float]]:
        """Retrieve from cache and move to end (most-recently used)."""
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache_hits += 1
            return self._cache[key]
        self._cache_misses += 1
        return None

    def _cache_put(self, key: str, value: List[float]) -> None:
        """Insert into cache, evicting the oldest entry if at capacity."""
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = value
            return

        if len(self._cache) >= self.cache_size:
            self._cache.popitem(last=False)

        self._cache[key] = value

    # ------------------------------------------------------------------
    # Retry helper
    # ------------------------------------------------------------------

    async def _call_with_retry(
        self,
        texts: List[str],
    ) -> List[List[float]]:
        """Call Azure OpenAI embeddings endpoint with exponential backoff.

        Retries on ``RateLimitError`` (HTTP 429) and transient ``APIError``.
        """
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.embeddings.create(
                    input=texts,
                    model=self.deployment,
                )
                return [item.embedding for item in response.data]
            except RateLimitError as exc:
                last_exception = exc
                delay = self.retry_base_delay * (2 ** attempt)
                logger.warning(
                    "Embedding rate limited (attempt %d/%d), retrying in %.1fs",
                    attempt + 1,
                    self.max_retries + 1,
                    delay,
                )
                await asyncio.sleep(delay)
            except APIError as exc:
                last_exception = exc
                status = getattr(exc, "status_code", None)
                if status and status >= 500:
                    delay = self.retry_base_delay * (2 ** attempt)
                    logger.warning(
                        "Embedding API error %s (attempt %d/%d), retrying in %.1fs",
                        status,
                        attempt + 1,
                        self.max_retries + 1,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise

        raise last_exception  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for a single text string.

        Checks the LRU cache first. On a miss the Azure OpenAI API is
        called and the result is cached.

        Args:
            text: Input text to embed.

        Returns:
            Embedding vector as a list of floats.

        Raises:
            openai.APIError: On non-retriable API failures.
        """
        cached = self._cache_get(text)
        if cached is not None:
            logger.debug("Embedding cache hit for text (len=%d)", len(text))
            return cached

        start = time.perf_counter()
        vectors = await self._call_with_retry([text])
        elapsed_ms = (time.perf_counter() - start) * 1000

        embedding = vectors[0]
        self._cache_put(text, embedding)

        logger.debug(
            "Embedding generated in %.1fms (dim=%d)",
            elapsed_ms,
            len(embedding),
        )
        return embedding

    async def get_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 16,
    ) -> List[List[float]]:
        """Get embeddings for multiple texts in batches.

        Cached texts are served from the cache; only uncached texts are
        sent to the API. Results are returned in the same order as the
        input ``texts`` list.

        Args:
            texts: List of input texts.
            batch_size: Number of texts per API call.

        Returns:
            List of embedding vectors in input order.
        """
        if not texts:
            return []

        # Separate cached vs uncached
        results: Dict[int, List[float]] = {}
        uncached_indices: List[int] = []
        uncached_texts: List[str] = []

        for idx, text in enumerate(texts):
            cached = self._cache_get(text)
            if cached is not None:
                results[idx] = cached
            else:
                uncached_indices.append(idx)
                uncached_texts.append(text)

        if not uncached_texts:
            return [results[i] for i in range(len(texts))]

        # Split uncached into batches
        batches: List[List[str]] = []
        for i in range(0, len(uncached_texts), batch_size):
            batches.append(uncached_texts[i : i + batch_size])

        # Process batches concurrently
        batch_results = await asyncio.gather(
            *(self._call_with_retry(batch) for batch in batches)
        )

        # Flatten and assign to results
        flat_vectors: List[List[float]] = []
        for batch_vectors in batch_results:
            flat_vectors.extend(batch_vectors)

        for vec_idx, orig_idx in enumerate(uncached_indices):
            embedding = flat_vectors[vec_idx]
            results[orig_idx] = embedding
            self._cache_put(uncached_texts[vec_idx], embedding)

        return [results[i] for i in range(len(texts))]

    def clear_cache(self) -> None:
        """Clear the embedding cache and reset statistics."""
        self._cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        logger.info("Embedding cache cleared")

    @property
    def cache_info(self) -> Dict[str, int]:
        """Get cache statistics.

        Returns:
            Dict with size, hits, misses, and max_size.
        """
        return {
            "size": len(self._cache),
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "max_size": self.cache_size,
        }
