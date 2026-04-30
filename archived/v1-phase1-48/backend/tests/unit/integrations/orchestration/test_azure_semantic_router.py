"""
Unit Tests for Azure Semantic Router Components.

Tests AzureSearchClient, AzureSemanticRouter with mocked Azure services.

Sprint 115: Story 115-2 - Azure Semantic Router Components (Phase 32)
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.orchestration.intent_router.models import (
    ITIntentCategory,
    RiskLevel,
    SemanticRouteResult,
    WorkflowType,
)
from src.integrations.orchestration.intent_router.semantic_router.azure_search_client import (
    AzureSearchClient,
)
from src.integrations.orchestration.intent_router.semantic_router.azure_semantic_router import (
    AzureSemanticRouter,
)
from src.integrations.orchestration.intent_router.semantic_router.embedding_service import (
    EmbeddingService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_search_result(
    route_name: str = "incident_etl",
    category: str = "incident",
    sub_intent: str = "etl_failure",
    score: float = 0.92,
    workflow_type: str = "magentic",
    risk_level: str = "high",
    description: str = "ETL job failures",
    enabled: bool = True,
) -> dict:
    """Create a dict mimicking an Azure AI Search result document."""
    return {
        "id": f"doc_{route_name}_1",
        "route_name": route_name,
        "category": category,
        "sub_intent": sub_intent,
        "@search.score": score,
        "workflow_type": workflow_type,
        "risk_level": risk_level,
        "description": description,
        "enabled": enabled,
        "utterance": "ETL 今天跑失敗了",
    }


def _make_upload_result(succeeded: bool = True) -> MagicMock:
    """Create a mock upload result item."""
    item = MagicMock()
    item.succeeded = succeeded
    return item


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_search_sdk():
    """Patch azure.search.documents.SearchClient at the module level."""
    with patch(
        "src.integrations.orchestration.intent_router.semantic_router"
        ".azure_search_client.SearchClient"
    ) as mock_cls:
        instance = MagicMock()
        mock_cls.return_value = instance
        yield instance


@pytest.fixture
def search_client(mock_search_sdk) -> AzureSearchClient:
    """Create AzureSearchClient with mocked SDK."""
    return AzureSearchClient(
        endpoint="https://test.search.windows.net",
        api_key="test-key",
        index_name="semantic-routes",
        max_retries=1,
        retry_base_delay=0.01,
    )


@pytest.fixture
def mock_embedding_service() -> EmbeddingService:
    """Create a mocked EmbeddingService."""
    svc = MagicMock(spec=EmbeddingService)
    svc.get_embedding = AsyncMock(return_value=[0.1] * 1536)
    svc.get_embeddings_batch = AsyncMock(return_value=[[0.1] * 1536])
    return svc


@pytest.fixture
def mock_search_client_async() -> AzureSearchClient:
    """Create a mocked AzureSearchClient with async methods."""
    client = MagicMock(spec=AzureSearchClient)
    client.vector_search = AsyncMock(return_value=[_make_search_result()])
    client.hybrid_search = AsyncMock(return_value=[_make_search_result()])
    client.health_check = AsyncMock(return_value=True)
    client.upload_documents = AsyncMock(
        return_value={"total": 1, "succeeded": 1, "failed": 0}
    )
    client.delete_documents = AsyncMock(
        return_value={"total": 1, "succeeded": 1, "failed": 0}
    )
    client.get_document = AsyncMock(return_value=_make_search_result())
    client.get_document_count = AsyncMock(return_value=15)
    return client


@pytest.fixture
def azure_router(
    mock_search_client_async,
    mock_embedding_service,
) -> AzureSemanticRouter:
    """Create AzureSemanticRouter with mocked dependencies."""
    return AzureSemanticRouter(
        search_client=mock_search_client_async,
        embedding_service=mock_embedding_service,
        similarity_threshold=0.85,
        top_k=3,
    )


# ===========================================================================
# TestAzureSearchClient
# ===========================================================================


class TestAzureSearchClient:
    """Tests for AzureSearchClient."""

    def test_init_validates_endpoint(self):
        """Empty endpoint raises ValueError."""
        with pytest.raises(ValueError, match="endpoint"):
            AzureSearchClient(endpoint="", api_key="key")

    def test_init_validates_api_key(self):
        """Empty api_key raises ValueError."""
        with pytest.raises(ValueError, match="api_key"):
            AzureSearchClient(endpoint="https://x.search.windows.net", api_key="")

    @pytest.mark.asyncio
    async def test_vector_search_returns_results(self, search_client, mock_search_sdk):
        """vector_search returns list of document dicts."""
        mock_search_sdk.search.return_value = iter(
            [_make_search_result(score=0.95)]
        )

        results = await search_client.vector_search(
            vector=[0.1] * 1536, top_k=3,
        )

        assert len(results) == 1
        assert results[0]["route_name"] == "incident_etl"
        assert results[0]["@search.score"] == 0.95

    @pytest.mark.asyncio
    async def test_vector_search_with_filter(self, search_client, mock_search_sdk):
        """vector_search passes filter to SDK."""
        mock_search_sdk.search.return_value = iter([])

        await search_client.vector_search(
            vector=[0.1] * 1536, top_k=5, filters="enabled eq true",
        )

        call_kwargs = mock_search_sdk.search.call_args
        assert call_kwargs.kwargs.get("filter") == "enabled eq true"

    @pytest.mark.asyncio
    async def test_vector_search_empty_results(self, search_client, mock_search_sdk):
        """vector_search returns empty list when no documents match."""
        mock_search_sdk.search.return_value = iter([])

        results = await search_client.vector_search(vector=[0.1] * 1536)

        assert results == []

    @pytest.mark.asyncio
    async def test_hybrid_search_returns_results(self, search_client, mock_search_sdk):
        """hybrid_search combines text and vector search."""
        mock_search_sdk.search.return_value = iter(
            [_make_search_result(score=0.90)]
        )

        results = await search_client.hybrid_search(
            query="ETL failed", vector=[0.1] * 1536, top_k=3,
        )

        assert len(results) == 1
        call_kwargs = mock_search_sdk.search.call_args
        assert call_kwargs.kwargs.get("search_text") == "ETL failed"

    @pytest.mark.asyncio
    async def test_upload_documents(self, search_client, mock_search_sdk):
        """upload_documents returns success counts."""
        mock_search_sdk.merge_or_upload_documents.return_value = [
            _make_upload_result(True),
            _make_upload_result(True),
        ]

        result = await search_client.upload_documents(
            [{"id": "1"}, {"id": "2"}]
        )

        assert result["total"] == 2
        assert result["succeeded"] == 2
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_upload_documents_partial_failure(self, search_client, mock_search_sdk):
        """upload_documents reports partial failures."""
        mock_search_sdk.merge_or_upload_documents.return_value = [
            _make_upload_result(True),
            _make_upload_result(False),
        ]

        result = await search_client.upload_documents(
            [{"id": "1"}, {"id": "2"}]
        )

        assert result["succeeded"] == 1
        assert result["failed"] == 1

    @pytest.mark.asyncio
    async def test_delete_documents(self, search_client, mock_search_sdk):
        """delete_documents calls SDK with correct document dicts."""
        mock_search_sdk.delete_documents.return_value = [
            _make_upload_result(True),
        ]

        result = await search_client.delete_documents(["doc_1"])

        assert result["total"] == 1
        assert result["succeeded"] == 1

    @pytest.mark.asyncio
    async def test_get_document_found(self, search_client, mock_search_sdk):
        """get_document returns document dict when found."""
        mock_search_sdk.get_document.return_value = _make_search_result()

        doc = await search_client.get_document("doc_incident_etl_1")

        assert doc is not None
        assert doc["route_name"] == "incident_etl"

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, search_client, mock_search_sdk):
        """get_document returns None for missing document."""
        from azure.core.exceptions import ResourceNotFoundError

        mock_search_sdk.get_document.side_effect = ResourceNotFoundError("Not found")

        doc = await search_client.get_document("nonexistent")

        assert doc is None

    @pytest.mark.asyncio
    async def test_get_document_count(self, search_client, mock_search_sdk):
        """get_document_count returns integer count."""
        mock_search_sdk.get_document_count.return_value = 42

        count = await search_client.get_document_count()

        assert count == 42

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, search_client, mock_search_sdk):
        """health_check returns True when service responds."""
        mock_search_sdk.get_document_count.return_value = 10

        result = await search_client.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, search_client, mock_search_sdk):
        """health_check returns False when service fails."""
        mock_search_sdk.get_document_count.side_effect = Exception("Connection refused")

        result = await search_client.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_retry_on_429(self, search_client, mock_search_sdk):
        """vector_search retries on HTTP 429 (rate limit)."""
        from azure.core.exceptions import HttpResponseError

        error_429 = HttpResponseError(message="Rate limited")
        error_429.status_code = 429

        mock_search_sdk.search.side_effect = [
            error_429,
            iter([_make_search_result(score=0.88)]),
        ]

        results = await search_client.vector_search(vector=[0.1] * 1536)

        assert len(results) == 1
        assert mock_search_sdk.search.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises(self, search_client, mock_search_sdk):
        """vector_search raises after max retries exhausted."""
        from azure.core.exceptions import HttpResponseError

        error_500 = HttpResponseError(message="Server error")
        error_500.status_code = 500

        mock_search_sdk.search.side_effect = error_500

        with pytest.raises(HttpResponseError):
            await search_client.vector_search(vector=[0.1] * 1536)


# ===========================================================================
# TestAzureSemanticRouter
# ===========================================================================


class TestAzureSemanticRouter:
    """Tests for AzureSemanticRouter."""

    def test_init_validates_threshold(self):
        """Invalid similarity_threshold raises ValueError."""
        with pytest.raises(ValueError, match="similarity_threshold"):
            AzureSemanticRouter(
                search_client=MagicMock(),
                embedding_service=MagicMock(),
                similarity_threshold=1.5,
            )

    @pytest.mark.asyncio
    async def test_route_match(self, azure_router, mock_search_client_async):
        """route returns matched result above threshold."""
        mock_search_client_async.vector_search.return_value = [
            _make_search_result(score=0.92),
        ]

        result = await azure_router.route("ETL 今天跑失敗了")

        assert result.matched is True
        assert result.intent_category == ITIntentCategory.INCIDENT
        assert result.sub_intent == "etl_failure"
        assert result.similarity == 0.92
        assert result.route_name == "incident_etl"
        assert result.metadata["workflow_type"] == "magentic"
        assert result.metadata["risk_level"] == "high"
        assert "processing_time_ms" in result.metadata

    @pytest.mark.asyncio
    async def test_route_no_match_empty_results(
        self, azure_router, mock_search_client_async,
    ):
        """route returns no_match when search returns empty."""
        mock_search_client_async.vector_search.return_value = []

        result = await azure_router.route("random gibberish text")

        assert result.matched is False
        assert result.similarity == 0.0

    @pytest.mark.asyncio
    async def test_route_below_threshold(
        self, azure_router, mock_search_client_async,
    ):
        """route returns no_match when similarity is below threshold."""
        mock_search_client_async.vector_search.return_value = [
            _make_search_result(score=0.60),
        ]

        result = await azure_router.route("some unrelated input")

        assert result.matched is False
        assert result.similarity == 0.60

    @pytest.mark.asyncio
    async def test_route_error_returns_no_match(
        self, azure_router, mock_embedding_service,
    ):
        """route returns no_match on unexpected error."""
        mock_embedding_service.get_embedding.side_effect = Exception("API down")

        result = await azure_router.route("test input")

        assert result.matched is False

    @pytest.mark.asyncio
    async def test_route_with_scores(
        self, azure_router, mock_search_client_async,
    ):
        """route_with_scores returns multiple results above threshold."""
        mock_search_client_async.vector_search.return_value = [
            _make_search_result(route_name="incident_etl", score=0.95),
            _make_search_result(
                route_name="incident_network",
                category="incident",
                sub_intent="network_issue",
                score=0.88,
            ),
            _make_search_result(
                route_name="query_status",
                category="query",
                sub_intent="status_inquiry",
                score=0.70,
            ),
        ]

        results = await azure_router.route_with_scores("ETL failure")

        assert len(results) == 2  # only 0.95 and 0.88 above 0.85
        assert results[0].similarity == 0.95
        assert results[1].similarity == 0.88

    @pytest.mark.asyncio
    async def test_route_with_scores_custom_top_k(
        self, azure_router, mock_search_client_async,
    ):
        """route_with_scores uses custom top_k."""
        mock_search_client_async.vector_search.return_value = [
            _make_search_result(score=0.93),
        ]

        results = await azure_router.route_with_scores("test", top_k=10)

        call_kwargs = mock_search_client_async.vector_search.call_args
        assert call_kwargs.kwargs.get("top_k") == 10
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_route_with_scores_error_returns_empty(
        self, azure_router, mock_embedding_service,
    ):
        """route_with_scores returns empty list on error."""
        mock_embedding_service.get_embedding.side_effect = RuntimeError("fail")

        results = await azure_router.route_with_scores("test")

        assert results == []

    def test_is_available_default(self, azure_router):
        """is_available is False before any check."""
        assert azure_router.is_available is False

    @pytest.mark.asyncio
    async def test_check_availability_healthy(
        self, azure_router, mock_search_client_async,
    ):
        """check_availability returns True and updates is_available."""
        mock_search_client_async.health_check.return_value = True

        result = await azure_router.check_availability()

        assert result is True
        assert azure_router.is_available is True

    @pytest.mark.asyncio
    async def test_check_availability_unhealthy(
        self, azure_router, mock_search_client_async,
    ):
        """check_availability returns False on failure."""
        mock_search_client_async.health_check.return_value = False

        result = await azure_router.check_availability()

        assert result is False
        assert azure_router.is_available is False

    @pytest.mark.asyncio
    async def test_route_passes_enabled_filter(
        self, azure_router, mock_search_client_async,
    ):
        """route passes 'enabled eq true' filter to search client."""
        mock_search_client_async.vector_search.return_value = [
            _make_search_result(score=0.90),
        ]

        await azure_router.route("test")

        call_kwargs = mock_search_client_async.vector_search.call_args
        assert call_kwargs.kwargs.get("filters") == "enabled eq true"

    @pytest.mark.asyncio
    async def test_route_result_metadata_structure(
        self, azure_router, mock_search_client_async,
    ):
        """route result metadata contains required keys for BusinessIntentRouter."""
        mock_search_client_async.vector_search.return_value = [
            _make_search_result(score=0.90),
        ]

        result = await azure_router.route("ETL job failed")

        required_keys = {"workflow_type", "risk_level", "description", "processing_time_ms"}
        assert required_keys.issubset(set(result.metadata.keys()))

    @pytest.mark.asyncio
    async def test_route_unknown_category_maps_to_unknown(
        self, azure_router, mock_search_client_async,
    ):
        """Unknown category string maps to ITIntentCategory.UNKNOWN."""
        mock_search_client_async.vector_search.return_value = [
            _make_search_result(category="nonexistent_category", score=0.90),
        ]

        result = await azure_router.route("test input")

        assert result.matched is True
        assert result.intent_category == ITIntentCategory.UNKNOWN
