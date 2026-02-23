"""
Unit tests for RouteManager and RouteDocument.

Sprint 115: Story 115-3 - Route Management API and Data Migration

Tests CRUD operations, sync/migration, and search with fully
mocked AzureSearchClient and EmbeddingService dependencies.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.orchestration.intent_router.semantic_router.route_manager import (
    RouteDocument,
    RouteManager,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_search_client():
    """Create a mocked AzureSearchClient."""
    client = AsyncMock()
    client.upload_documents = AsyncMock(return_value=None)
    client.delete_documents = AsyncMock(return_value=None)
    client.get_document_count = AsyncMock(return_value=0)
    client.vector_search = AsyncMock(return_value=[])
    client.hybrid_search = AsyncMock(return_value=[])
    client.health_check = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_embedding_service():
    """Create a mocked EmbeddingService."""
    service = AsyncMock()
    # Default: return a dummy 1536-dim vector for each input
    service.get_embedding = AsyncMock(return_value=[0.1] * 1536)
    service.get_embeddings_batch = AsyncMock(
        side_effect=lambda texts: [[0.1] * 1536 for _ in texts]
    )
    return service


@pytest.fixture
def route_manager(mock_search_client, mock_embedding_service):
    """Create a RouteManager with mocked dependencies."""
    return RouteManager(
        search_client=mock_search_client,
        embedding_service=mock_embedding_service,
    )


# ---------------------------------------------------------------------------
# TestRouteDocument
# ---------------------------------------------------------------------------


class TestRouteDocument:
    """Tests for RouteDocument serialization."""

    def test_to_dict(self):
        """RouteDocument.to_dict() produces the expected dictionary."""
        doc = RouteDocument(
            doc_id="test-id-1",
            route_name="incident_etl",
            category="incident",
            sub_intent="etl_failure",
            utterance="ETL job failed",
            utterance_vector=[0.1, 0.2, 0.3],
            workflow_type="magentic",
            risk_level="high",
            description="ETL failures",
            enabled=True,
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

        result = doc.to_dict()

        assert result["id"] == "test-id-1"
        assert result["route_name"] == "incident_etl"
        assert result["category"] == "incident"
        assert result["sub_intent"] == "etl_failure"
        assert result["utterance"] == "ETL job failed"
        assert result["utterance_vector"] == [0.1, 0.2, 0.3]
        assert result["workflow_type"] == "magentic"
        assert result["risk_level"] == "high"
        assert result["description"] == "ETL failures"
        assert result["enabled"] is True
        assert result["created_at"] == "2026-01-01T00:00:00+00:00"
        assert result["updated_at"] == "2026-01-01T00:00:00+00:00"

    def test_from_dict(self):
        """RouteDocument.from_dict() correctly deserializes."""
        data = {
            "id": "test-id-2",
            "route_name": "request_account",
            "category": "request",
            "sub_intent": "account_creation",
            "utterance": "I need a new account",
            "utterance_vector": [0.5, 0.6],
            "workflow_type": "sequential",
            "risk_level": "low",
            "description": "Account requests",
            "enabled": False,
            "created_at": "2026-02-01T00:00:00+00:00",
            "updated_at": "2026-02-01T00:00:00+00:00",
        }

        doc = RouteDocument.from_dict(data)

        assert doc.id == "test-id-2"
        assert doc.route_name == "request_account"
        assert doc.category == "request"
        assert doc.sub_intent == "account_creation"
        assert doc.utterance == "I need a new account"
        assert doc.utterance_vector == [0.5, 0.6]
        assert doc.workflow_type == "sequential"
        assert doc.risk_level == "low"
        assert doc.enabled is False

    def test_from_dict_missing_optional_fields(self):
        """from_dict handles missing optional fields gracefully."""
        data = {
            "id": "test-id-3",
            "route_name": "minimal",
            "category": "query",
            "sub_intent": "status",
            "utterance": "status check",
        }

        doc = RouteDocument.from_dict(data)

        assert doc.id == "test-id-3"
        assert doc.utterance_vector == []
        assert doc.workflow_type == "simple"
        assert doc.risk_level == "medium"
        assert doc.description == ""
        assert doc.enabled is True

    def test_roundtrip(self):
        """to_dict -> from_dict produces an equivalent document."""
        original = RouteDocument(
            doc_id="roundtrip-id",
            route_name="change_config",
            category="change",
            sub_intent="config_update",
            utterance="Update configuration",
            utterance_vector=[1.0, 2.0, 3.0],
            workflow_type="sequential",
            risk_level="medium",
            description="Config changes",
            enabled=True,
        )

        recreated = RouteDocument.from_dict(original.to_dict())

        assert recreated.id == original.id
        assert recreated.route_name == original.route_name
        assert recreated.category == original.category
        assert recreated.utterance == original.utterance
        assert recreated.utterance_vector == original.utterance_vector


# ---------------------------------------------------------------------------
# TestRouteManager
# ---------------------------------------------------------------------------


class TestRouteManager:
    """Tests for RouteManager CRUD, sync, and search operations."""

    @pytest.mark.asyncio
    async def test_create_route(self, route_manager, mock_search_client, mock_embedding_service):
        """create_route generates embeddings and uploads documents."""
        # Ensure no existing docs
        mock_search_client.hybrid_search.return_value = []

        result = await route_manager.create_route(
            route_name="test_route",
            category="incident",
            sub_intent="test_failure",
            utterances=["test utterance 1", "test utterance 2"],
            description="Test route",
            workflow_type="magentic",
            risk_level="high",
        )

        assert result["route_name"] == "test_route"
        assert result["category"] == "incident"
        assert result["utterance_count"] == 2
        assert result["status"] == "created"

        # Verify embeddings were generated
        mock_embedding_service.get_embeddings_batch.assert_called_once_with(
            ["test utterance 1", "test utterance 2"]
        )

        # Verify upload was called with 2 documents
        mock_search_client.upload_documents.assert_called_once()
        uploaded_docs = mock_search_client.upload_documents.call_args[0][0]
        assert len(uploaded_docs) == 2
        assert uploaded_docs[0]["route_name"] == "test_route"
        assert uploaded_docs[1]["route_name"] == "test_route"

    @pytest.mark.asyncio
    async def test_create_route_duplicate_raises(self, route_manager, mock_search_client):
        """create_route raises ValueError if route already exists."""
        mock_search_client.hybrid_search.return_value = [
            {"id": "existing-1", "route_name": "dup_route"}
        ]

        with pytest.raises(ValueError, match="already exists"):
            await route_manager.create_route(
                route_name="dup_route",
                category="query",
                sub_intent="status",
                utterances=["check status"],
            )

    @pytest.mark.asyncio
    async def test_get_routes(self, route_manager, mock_search_client):
        """get_routes groups documents by route_name."""
        mock_search_client.hybrid_search.return_value = [
            {
                "id": "d1",
                "route_name": "route_a",
                "category": "incident",
                "sub_intent": "etl",
                "utterance": "u1",
                "workflow_type": "magentic",
                "risk_level": "high",
                "description": "Route A",
                "enabled": True,
            },
            {
                "id": "d2",
                "route_name": "route_a",
                "category": "incident",
                "sub_intent": "etl",
                "utterance": "u2",
                "workflow_type": "magentic",
                "risk_level": "high",
                "description": "Route A",
                "enabled": True,
            },
            {
                "id": "d3",
                "route_name": "route_b",
                "category": "request",
                "sub_intent": "account",
                "utterance": "u3",
                "workflow_type": "simple",
                "risk_level": "low",
                "description": "Route B",
                "enabled": True,
            },
        ]

        result = await route_manager.get_routes()

        assert len(result) == 2
        route_a = next(r for r in result if r["route_name"] == "route_a")
        route_b = next(r for r in result if r["route_name"] == "route_b")
        assert route_a["utterance_count"] == 2
        assert route_b["utterance_count"] == 1

    @pytest.mark.asyncio
    async def test_get_routes_with_category_filter(self, route_manager, mock_search_client):
        """get_routes passes category filter to search client."""
        mock_search_client.hybrid_search.return_value = []

        await route_manager.get_routes(category="incident")

        call_kwargs = mock_search_client.hybrid_search.call_args
        # Check both kwargs style (keyword arg) and positional
        filters_value = call_kwargs.kwargs.get(
            "filters", call_kwargs[1].get("filters", "")
        ) if call_kwargs.kwargs else ""
        assert "category eq 'incident'" in str(filters_value)

    @pytest.mark.asyncio
    async def test_get_route(self, route_manager, mock_search_client):
        """get_route returns detail for a single route."""
        mock_search_client.hybrid_search.return_value = [
            {
                "id": "d1",
                "route_name": "incident_etl",
                "category": "incident",
                "sub_intent": "etl_failure",
                "utterance": "ETL failed",
                "workflow_type": "magentic",
                "risk_level": "high",
                "description": "ETL failures",
                "enabled": True,
            },
            {
                "id": "d2",
                "route_name": "incident_etl",
                "category": "incident",
                "sub_intent": "etl_failure",
                "utterance": "Data pipeline broken",
                "workflow_type": "magentic",
                "risk_level": "high",
                "description": "ETL failures",
                "enabled": True,
            },
        ]

        result = await route_manager.get_route("incident_etl")

        assert result is not None
        assert result["route_name"] == "incident_etl"
        assert result["utterance_count"] == 2
        assert "ETL failed" in result["utterances"]
        assert "Data pipeline broken" in result["utterances"]
        assert result["document_ids"] == ["d1", "d2"]

    @pytest.mark.asyncio
    async def test_get_route_not_found(self, route_manager, mock_search_client):
        """get_route returns None when route does not exist."""
        mock_search_client.hybrid_search.return_value = []

        result = await route_manager.get_route("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_route_utterances(
        self, route_manager, mock_search_client, mock_embedding_service
    ):
        """update_route with new utterances deletes old docs and re-embeds."""
        mock_search_client.hybrid_search.return_value = [
            {
                "id": "old-1",
                "route_name": "test_route",
                "category": "incident",
                "sub_intent": "test",
                "utterance": "old utterance",
                "workflow_type": "magentic",
                "risk_level": "high",
                "description": "Test",
                "enabled": True,
                "created_at": "2026-01-01T00:00:00+00:00",
            },
        ]

        result = await route_manager.update_route(
            route_name="test_route",
            utterances=["new utterance 1", "new utterance 2"],
        )

        assert result["route_name"] == "test_route"
        assert result["utterance_count"] == 2
        assert result["status"] == "updated"

        # Old documents deleted
        mock_search_client.delete_documents.assert_called_once_with(["old-1"])

        # New embeddings generated
        mock_embedding_service.get_embeddings_batch.assert_called_once_with(
            ["new utterance 1", "new utterance 2"]
        )

        # New documents uploaded
        mock_search_client.upload_documents.assert_called_once()
        uploaded = mock_search_client.upload_documents.call_args[0][0]
        assert len(uploaded) == 2

    @pytest.mark.asyncio
    async def test_update_route_metadata(
        self, route_manager, mock_search_client, mock_embedding_service
    ):
        """update_route with metadata only patches documents without re-embedding."""
        mock_search_client.hybrid_search.return_value = [
            {
                "id": "meta-1",
                "route_name": "test_route",
                "category": "query",
                "sub_intent": "status",
                "utterance": "check status",
                "workflow_type": "simple",
                "risk_level": "low",
                "description": "Old description",
                "enabled": True,
            },
        ]

        result = await route_manager.update_route(
            route_name="test_route",
            description="New description",
            enabled=False,
        )

        assert result["status"] == "updated"

        # No embedding generation for metadata-only update
        mock_embedding_service.get_embeddings_batch.assert_not_called()

        # Upload called with patched documents
        uploaded = mock_search_client.upload_documents.call_args[0][0]
        assert len(uploaded) == 1
        assert uploaded[0]["description"] == "New description"
        assert uploaded[0]["enabled"] is False

    @pytest.mark.asyncio
    async def test_update_route_not_found(self, route_manager, mock_search_client):
        """update_route raises ValueError when route not found."""
        mock_search_client.hybrid_search.return_value = []

        with pytest.raises(ValueError, match="not found"):
            await route_manager.update_route(
                route_name="missing_route",
                description="test",
            )

    @pytest.mark.asyncio
    async def test_delete_route(self, route_manager, mock_search_client):
        """delete_route removes all documents for the route."""
        mock_search_client.hybrid_search.return_value = [
            {"id": "del-1", "route_name": "to_delete"},
            {"id": "del-2", "route_name": "to_delete"},
            {"id": "del-3", "route_name": "to_delete"},
        ]

        result = await route_manager.delete_route("to_delete")

        assert result["route_name"] == "to_delete"
        assert result["documents_deleted"] == 3
        assert result["status"] == "deleted"
        mock_search_client.delete_documents.assert_called_once_with(
            ["del-1", "del-2", "del-3"]
        )

    @pytest.mark.asyncio
    async def test_delete_route_not_found(self, route_manager, mock_search_client):
        """delete_route raises ValueError when route not found."""
        mock_search_client.hybrid_search.return_value = []

        with pytest.raises(ValueError, match="not found"):
            await route_manager.delete_route("nonexistent")

    @pytest.mark.asyncio
    async def test_sync_from_yaml(
        self, route_manager, mock_search_client, mock_embedding_service
    ):
        """sync_from_yaml uploads all 15 routes with all utterances."""
        mock_search_client.get_document_count.return_value = 75  # ~5 per route

        result = await route_manager.sync_from_yaml()

        assert result["routes_synced"] == 15
        assert result["status"] == "success"

        # Total utterances should match the sum across all 15 routes
        uploaded_docs = mock_search_client.upload_documents.call_args[0][0]
        assert len(uploaded_docs) > 0
        assert result["utterances_synced"] == len(uploaded_docs)

        # Embeddings were generated for each route
        assert mock_embedding_service.get_embeddings_batch.call_count == 15

    @pytest.mark.asyncio
    async def test_search_test(
        self, route_manager, mock_search_client, mock_embedding_service
    ):
        """search_test generates query embedding and returns formatted results."""
        mock_search_client.vector_search.return_value = [
            {
                "route_name": "incident_etl",
                "category": "incident",
                "sub_intent": "etl_failure",
                "utterance": "ETL job failed",
                "@search.score": 0.95,
                "workflow_type": "magentic",
                "risk_level": "high",
            },
            {
                "route_name": "incident_network",
                "category": "incident",
                "sub_intent": "network_issue",
                "utterance": "Network down",
                "@search.score": 0.72,
                "workflow_type": "magentic",
                "risk_level": "high",
            },
        ]

        results = await route_manager.search_test("ETL failed", top_k=3)

        assert len(results) == 2
        assert results[0]["route_name"] == "incident_etl"
        assert results[0]["score"] == 0.95
        assert results[1]["route_name"] == "incident_network"

        # Verify embedding was generated for the query
        mock_embedding_service.get_embedding.assert_called_once_with("ETL failed")

        # Verify vector search was invoked
        mock_search_client.vector_search.assert_called_once()
