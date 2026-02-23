"""
Unit Tests for EmbeddingService.

Tests embedding generation, LRU cache behaviour, batch processing,
and error/retry handling with mocked Azure OpenAI client.

Sprint 115: Story 115-2 - Azure Semantic Router Components (Phase 32)
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.orchestration.intent_router.semantic_router.embedding_service import (
    EmbeddingService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_embedding_response(vectors: list[list[float]]):
    """Create a mock Azure OpenAI embeddings response."""
    response = MagicMock()
    data_items = []
    for vec in vectors:
        item = MagicMock()
        item.embedding = vec
        data_items.append(item)
    response.data = data_items
    return response


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_openai_client():
    """Patch AsyncAzureOpenAI at the module level."""
    with patch(
        "src.integrations.orchestration.intent_router.semantic_router"
        ".embedding_service.AsyncAzureOpenAI"
    ) as mock_cls:
        instance = MagicMock()
        instance.embeddings = MagicMock()
        instance.embeddings.create = AsyncMock()
        mock_cls.return_value = instance
        yield instance


@pytest.fixture
def embedding_service(mock_openai_client) -> EmbeddingService:
    """Create EmbeddingService with mocked OpenAI client."""
    svc = EmbeddingService(
        endpoint="https://test.openai.azure.com/",
        api_key="test-key",
        deployment="text-embedding-ada-002",
        cache_size=8,
        max_retries=2,
        retry_base_delay=0.01,
    )
    # Replace internal client with our mock
    svc._client = mock_openai_client
    return svc


# ===========================================================================
# TestEmbeddingService
# ===========================================================================


class TestEmbeddingService:
    """Tests for EmbeddingService."""

    def test_init_validates_endpoint(self):
        """Empty endpoint raises ValueError."""
        with pytest.raises(ValueError, match="endpoint"):
            EmbeddingService(endpoint="", api_key="key")

    def test_init_validates_api_key(self):
        """Empty api_key raises ValueError."""
        with pytest.raises(ValueError, match="api_key"):
            EmbeddingService(
                endpoint="https://test.openai.azure.com/", api_key="",
            )

    @pytest.mark.asyncio
    async def test_get_embedding_single(self, embedding_service, mock_openai_client):
        """get_embedding returns a vector for a single text."""
        expected = [0.1] * 1536
        mock_openai_client.embeddings.create.return_value = (
            _make_embedding_response([expected])
        )

        result = await embedding_service.get_embedding("hello world")

        assert result == expected
        mock_openai_client.embeddings.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_embedding_cache_hit(self, embedding_service, mock_openai_client):
        """Second call with same text returns cached result (single API call)."""
        expected = [0.2] * 1536
        mock_openai_client.embeddings.create.return_value = (
            _make_embedding_response([expected])
        )

        result_1 = await embedding_service.get_embedding("cached text")
        result_2 = await embedding_service.get_embedding("cached text")

        assert result_1 == expected
        assert result_2 == expected
        assert mock_openai_client.embeddings.create.await_count == 1

    @pytest.mark.asyncio
    async def test_get_embedding_cache_miss(self, embedding_service, mock_openai_client):
        """Different texts cause separate API calls."""
        vec_a = [0.1] * 1536
        vec_b = [0.2] * 1536
        mock_openai_client.embeddings.create.side_effect = [
            _make_embedding_response([vec_a]),
            _make_embedding_response([vec_b]),
        ]

        result_a = await embedding_service.get_embedding("text A")
        result_b = await embedding_service.get_embedding("text B")

        assert result_a == vec_a
        assert result_b == vec_b
        assert mock_openai_client.embeddings.create.await_count == 2

    @pytest.mark.asyncio
    async def test_cache_eviction(self, embedding_service, mock_openai_client):
        """Cache evicts oldest entry when exceeding max size (8)."""
        for i in range(10):
            vec = [float(i)] * 1536
            mock_openai_client.embeddings.create.return_value = (
                _make_embedding_response([vec])
            )
            await embedding_service.get_embedding(f"text_{i}")

        # The cache should have 8 entries (most recent)
        assert embedding_service.cache_info["size"] == 8

        # text_0 and text_1 should have been evicted
        # Accessing text_0 should be a cache miss
        call_count_before = mock_openai_client.embeddings.create.await_count
        vec_0 = [99.0] * 1536
        mock_openai_client.embeddings.create.return_value = (
            _make_embedding_response([vec_0])
        )
        await embedding_service.get_embedding("text_0")

        assert mock_openai_client.embeddings.create.await_count == call_count_before + 1

    @pytest.mark.asyncio
    async def test_clear_cache(self, embedding_service, mock_openai_client):
        """clear_cache empties the cache and resets statistics."""
        vec = [0.5] * 1536
        mock_openai_client.embeddings.create.return_value = (
            _make_embedding_response([vec])
        )

        await embedding_service.get_embedding("to be cleared")
        assert embedding_service.cache_info["size"] == 1

        embedding_service.clear_cache()

        assert embedding_service.cache_info["size"] == 0
        assert embedding_service.cache_info["hits"] == 0
        assert embedding_service.cache_info["misses"] == 0

    @pytest.mark.asyncio
    async def test_cache_info_statistics(self, embedding_service, mock_openai_client):
        """cache_info reports correct hit/miss counts."""
        vec = [0.3] * 1536
        mock_openai_client.embeddings.create.return_value = (
            _make_embedding_response([vec])
        )

        await embedding_service.get_embedding("stats test")  # miss
        await embedding_service.get_embedding("stats test")  # hit
        await embedding_service.get_embedding("stats test")  # hit

        info = embedding_service.cache_info
        assert info["hits"] == 2
        assert info["misses"] == 1
        assert info["size"] == 1
        assert info["max_size"] == 8

    @pytest.mark.asyncio
    async def test_get_embeddings_batch_single(
        self, embedding_service, mock_openai_client,
    ):
        """get_embeddings_batch processes a single batch."""
        vecs = [[0.1] * 1536, [0.2] * 1536]
        mock_openai_client.embeddings.create.return_value = (
            _make_embedding_response(vecs)
        )

        results = await embedding_service.get_embeddings_batch(
            ["text A", "text B"],
        )

        assert len(results) == 2
        assert results[0] == vecs[0]
        assert results[1] == vecs[1]

    @pytest.mark.asyncio
    async def test_get_embeddings_batch_uses_cache(
        self, embedding_service, mock_openai_client,
    ):
        """get_embeddings_batch skips API call for cached texts."""
        vec_cached = [0.9] * 1536
        vec_new = [0.8] * 1536

        # Pre-cache one text
        mock_openai_client.embeddings.create.return_value = (
            _make_embedding_response([vec_cached])
        )
        await embedding_service.get_embedding("cached")

        # Now batch with one cached + one new
        mock_openai_client.embeddings.create.return_value = (
            _make_embedding_response([vec_new])
        )

        results = await embedding_service.get_embeddings_batch(
            ["cached", "new text"],
        )

        assert results[0] == vec_cached
        assert results[1] == vec_new
        # First call was for pre-cache, second for the batch (only uncached)
        assert mock_openai_client.embeddings.create.await_count == 2

    @pytest.mark.asyncio
    async def test_get_embeddings_batch_all_cached(
        self, embedding_service, mock_openai_client,
    ):
        """get_embeddings_batch returns all from cache with no API call."""
        vec = [0.7] * 1536
        mock_openai_client.embeddings.create.return_value = (
            _make_embedding_response([vec])
        )
        await embedding_service.get_embedding("already cached")

        call_count = mock_openai_client.embeddings.create.await_count
        results = await embedding_service.get_embeddings_batch(
            ["already cached"],
        )

        assert results[0] == vec
        assert mock_openai_client.embeddings.create.await_count == call_count

    @pytest.mark.asyncio
    async def test_get_embeddings_batch_empty(self, embedding_service):
        """get_embeddings_batch returns empty list for empty input."""
        results = await embedding_service.get_embeddings_batch([])
        assert results == []

    @pytest.mark.asyncio
    async def test_get_embeddings_batch_multiple_batches(
        self, embedding_service, mock_openai_client,
    ):
        """get_embeddings_batch splits into multiple batches."""
        # batch_size defaults to 16; provide 20 texts
        texts = [f"text_{i}" for i in range(20)]
        vecs_batch1 = [[float(i)] * 1536 for i in range(16)]
        vecs_batch2 = [[float(i + 16)] * 1536 for i in range(4)]

        mock_openai_client.embeddings.create.side_effect = [
            _make_embedding_response(vecs_batch1),
            _make_embedding_response(vecs_batch2),
        ]

        results = await embedding_service.get_embeddings_batch(texts, batch_size=16)

        assert len(results) == 20
        assert mock_openai_client.embeddings.create.await_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self, embedding_service, mock_openai_client):
        """get_embedding retries on RateLimitError (429)."""
        from openai import RateLimitError

        rate_err = RateLimitError(
            message="Rate limited",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )
        vec = [0.4] * 1536

        mock_openai_client.embeddings.create.side_effect = [
            rate_err,
            _make_embedding_response([vec]),
        ]

        result = await embedding_service.get_embedding("retry test")

        assert result == vec
        assert mock_openai_client.embeddings.create.await_count == 2

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises(self, embedding_service, mock_openai_client):
        """get_embedding raises after max retries on persistent rate limit."""
        from openai import RateLimitError

        rate_err = RateLimitError(
            message="Rate limited",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )

        mock_openai_client.embeddings.create.side_effect = rate_err

        with pytest.raises(RateLimitError):
            await embedding_service.get_embedding("always fails")

    @pytest.mark.asyncio
    async def test_api_error_non_retryable_raises_immediately(
        self, embedding_service, mock_openai_client,
    ):
        """Non-5xx APIError is raised immediately without retry."""
        from openai import APIError

        api_err = APIError(
            message="Bad request",
            request=MagicMock(),
            body=None,
        )
        api_err.status_code = 400

        mock_openai_client.embeddings.create.side_effect = api_err

        with pytest.raises(APIError):
            await embedding_service.get_embedding("bad input")

        # Only 1 attempt (no retry for 400)
        assert mock_openai_client.embeddings.create.await_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_server_error(self, embedding_service, mock_openai_client):
        """get_embedding retries on 5xx APIError."""
        from openai import APIError

        server_err = APIError(
            message="Internal server error",
            request=MagicMock(),
            body=None,
        )
        server_err.status_code = 500

        vec = [0.6] * 1536
        mock_openai_client.embeddings.create.side_effect = [
            server_err,
            _make_embedding_response([vec]),
        ]

        result = await embedding_service.get_embedding("server error test")

        assert result == vec
        assert mock_openai_client.embeddings.create.await_count == 2
