"""Embedding Manager — text vectorisation via Azure OpenAI.

Wraps the existing EmbeddingService from integrations/memory/ with
knowledge-specific defaults and batch processing.

Sprint 118 — Phase 38 E2E Assembly C.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "text-embedding-3-large"
DEFAULT_DIMENSIONS = 3072


class EmbeddingManager:
    """Manages text embedding for knowledge indexing and retrieval.

    Delegates to the platform's EmbeddingService when available,
    with fallback to a simple hash-based pseudo-embedding for
    development without API keys.

    Args:
        model: Embedding model name.
        dimensions: Output embedding dimensions.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        dimensions: int = DEFAULT_DIMENSIONS,
    ) -> None:
        self._model = model
        self._dimensions = dimensions
        self._service: Any = None
        self._initialized = False

    async def initialize(self) -> None:
        """Lazy-initialise the underlying embedding service."""
        if self._initialized:
            return
        try:
            from src.integrations.memory.embeddings import EmbeddingService
            self._service = EmbeddingService()
            await self._service.initialize()
            self._initialized = True
            logger.info("EmbeddingManager: initialized with model=%s", self._model)
        except ImportError:
            logger.warning("EmbeddingManager: EmbeddingService not available, using fallback")
            self._initialized = True
        except Exception as e:
            logger.error("EmbeddingManager: init failed: %s", e)
            self._initialized = True

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        await self.initialize()
        if self._service and hasattr(self._service, "embed_text"):
            try:
                return await self._service.embed_text(text, model=self._model)
            except Exception as e:
                logger.error("Embedding failed: %s", e)
        return self._fallback_embed(text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        await self.initialize()
        if self._service and hasattr(self._service, "embed_batch"):
            try:
                return await self._service.embed_batch(texts, model=self._model)
            except Exception as e:
                logger.error("Batch embedding failed: %s", e)
        return [self._fallback_embed(t) for t in texts]

    def _fallback_embed(self, text: str) -> List[float]:
        """Simple hash-based pseudo-embedding for development."""
        import hashlib
        h = hashlib.sha256(text.encode()).digest()
        # Generate a deterministic pseudo-vector
        vector = []
        for i in range(min(self._dimensions, 256)):
            byte_val = h[i % len(h)]
            vector.append((byte_val - 128) / 128.0)
        # Pad to target dimensions
        while len(vector) < self._dimensions:
            vector.append(0.0)
        return vector[:self._dimensions]
