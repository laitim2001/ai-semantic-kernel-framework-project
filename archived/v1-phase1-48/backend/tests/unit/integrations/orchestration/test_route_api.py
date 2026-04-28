"""
Unit tests for Route Management API endpoints.

Sprint 115: Story 115-3 - Route Management API and Data Migration

Tests all 7 endpoints with a mocked RouteManager dependency using
FastAPI TestClient with dependency override.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1.orchestration.route_management import (
    get_route_manager,
    route_management_router,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_route_manager():
    """Create a fully mocked RouteManager."""
    manager = AsyncMock()
    manager.create_route = AsyncMock()
    manager.get_routes = AsyncMock(return_value=[])
    manager.get_route = AsyncMock(return_value=None)
    manager.update_route = AsyncMock()
    manager.delete_route = AsyncMock()
    manager.sync_from_yaml = AsyncMock()
    manager.search_test = AsyncMock(return_value=[])
    return manager


@pytest.fixture
def app(mock_route_manager):
    """Create a FastAPI app with route_management_router and overridden dependency."""
    test_app = FastAPI()
    test_app.include_router(route_management_router)

    # Override the factory to return the mock
    test_app.dependency_overrides[get_route_manager] = lambda: mock_route_manager

    return test_app


@pytest.fixture
def client(app):
    """Create a TestClient for the app."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCreateRouteEndpoint:
    """Tests for POST /orchestration/routes."""

    def test_create_route_success(self, client, mock_route_manager):
        """Successful route creation returns 201."""
        mock_route_manager.create_route.return_value = {
            "route_name": "test_route",
            "category": "incident",
            "sub_intent": "test",
            "utterance_count": 2,
            "workflow_type": "magentic",
            "risk_level": "high",
            "description": "Test",
            "enabled": True,
            "status": "created",
        }

        response = client.post(
            "/orchestration/routes",
            json={
                "route_name": "test_route",
                "category": "incident",
                "sub_intent": "test",
                "utterances": ["utterance 1", "utterance 2"],
                "description": "Test",
                "workflow_type": "magentic",
                "risk_level": "high",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["route_name"] == "test_route"
        assert data["utterance_count"] == 2
        assert data["status"] == "created"

    def test_create_route_invalid_category(self, client, mock_route_manager):
        """Invalid category returns 422 validation error."""
        response = client.post(
            "/orchestration/routes",
            json={
                "route_name": "test",
                "category": "invalid_category",
                "sub_intent": "test",
                "utterances": ["test"],
            },
        )

        assert response.status_code == 422

    def test_create_route_missing_name(self, client, mock_route_manager):
        """Missing route_name returns 422."""
        response = client.post(
            "/orchestration/routes",
            json={
                "category": "incident",
                "sub_intent": "test",
                "utterances": ["test"],
            },
        )

        assert response.status_code == 422

    def test_create_route_empty_utterances(self, client, mock_route_manager):
        """Empty utterances list returns 422."""
        response = client.post(
            "/orchestration/routes",
            json={
                "route_name": "test",
                "category": "incident",
                "sub_intent": "test",
                "utterances": [],
            },
        )

        assert response.status_code == 422

    def test_create_route_conflict(self, client, mock_route_manager):
        """Duplicate route returns 409 conflict."""
        mock_route_manager.create_route.side_effect = ValueError("already exists")

        response = client.post(
            "/orchestration/routes",
            json={
                "route_name": "duplicate",
                "category": "query",
                "sub_intent": "status",
                "utterances": ["test"],
            },
        )

        assert response.status_code == 409


class TestListRoutesEndpoint:
    """Tests for GET /orchestration/routes."""

    def test_list_routes_success(self, client, mock_route_manager):
        """List routes returns 200 with route list."""
        mock_route_manager.get_routes.return_value = [
            {
                "route_name": "route_a",
                "category": "incident",
                "sub_intent": "etl",
                "utterance_count": 5,
                "workflow_type": "magentic",
                "risk_level": "high",
                "description": "A",
                "enabled": True,
            },
            {
                "route_name": "route_b",
                "category": "query",
                "sub_intent": "status",
                "utterance_count": 3,
                "workflow_type": "simple",
                "risk_level": "low",
                "description": "B",
                "enabled": True,
            },
        ]

        response = client.get("/orchestration/routes")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["route_name"] == "route_a"

    def test_list_routes_with_category_filter(self, client, mock_route_manager):
        """Category query parameter is passed to manager."""
        mock_route_manager.get_routes.return_value = []

        response = client.get("/orchestration/routes?category=incident")

        assert response.status_code == 200
        mock_route_manager.get_routes.assert_called_once_with(
            category="incident", enabled=None
        )

    def test_list_routes_with_enabled_filter(self, client, mock_route_manager):
        """Enabled query parameter is passed to manager."""
        mock_route_manager.get_routes.return_value = []

        response = client.get("/orchestration/routes?enabled=true")

        assert response.status_code == 200
        mock_route_manager.get_routes.assert_called_once_with(
            category=None, enabled=True
        )

    def test_list_routes_empty(self, client, mock_route_manager):
        """Empty result returns 200 with empty list."""
        mock_route_manager.get_routes.return_value = []

        response = client.get("/orchestration/routes")

        assert response.status_code == 200
        assert response.json() == []


class TestGetRouteEndpoint:
    """Tests for GET /orchestration/routes/{route_name}."""

    def test_get_route_success(self, client, mock_route_manager):
        """Found route returns 200 with detail."""
        mock_route_manager.get_route.return_value = {
            "route_name": "incident_etl",
            "category": "incident",
            "sub_intent": "etl_failure",
            "utterances": ["ETL failed", "Data pipeline broken"],
            "utterance_count": 2,
            "workflow_type": "magentic",
            "risk_level": "high",
            "description": "ETL failures",
            "enabled": True,
            "document_ids": ["d1", "d2"],
        }

        response = client.get("/orchestration/routes/incident_etl")

        assert response.status_code == 200
        data = response.json()
        assert data["route_name"] == "incident_etl"
        assert len(data["utterances"]) == 2

    def test_get_route_not_found(self, client, mock_route_manager):
        """Missing route returns 404."""
        mock_route_manager.get_route.return_value = None

        response = client.get("/orchestration/routes/nonexistent")

        assert response.status_code == 404


class TestUpdateRouteEndpoint:
    """Tests for PUT /orchestration/routes/{route_name}."""

    def test_update_route_success(self, client, mock_route_manager):
        """Successful update returns 200."""
        mock_route_manager.update_route.return_value = {
            "route_name": "test_route",
            "utterance_count": 3,
            "status": "updated",
        }

        response = client.put(
            "/orchestration/routes/test_route",
            json={"description": "Updated description"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "updated"

    def test_update_route_with_utterances(self, client, mock_route_manager):
        """Update with new utterances triggers re-embedding."""
        mock_route_manager.update_route.return_value = {
            "route_name": "test_route",
            "utterance_count": 2,
            "status": "updated",
        }

        response = client.put(
            "/orchestration/routes/test_route",
            json={"utterances": ["new 1", "new 2"]},
        )

        assert response.status_code == 200
        mock_route_manager.update_route.assert_called_once()

    def test_update_route_not_found(self, client, mock_route_manager):
        """Update of missing route returns 404."""
        mock_route_manager.update_route.side_effect = ValueError("not found")

        response = client.put(
            "/orchestration/routes/missing",
            json={"description": "test"},
        )

        assert response.status_code == 404


class TestDeleteRouteEndpoint:
    """Tests for DELETE /orchestration/routes/{route_name}."""

    def test_delete_route_success(self, client, mock_route_manager):
        """Successful delete returns 200."""
        mock_route_manager.delete_route.return_value = {
            "route_name": "to_delete",
            "documents_deleted": 5,
            "status": "deleted",
        }

        response = client.delete("/orchestration/routes/to_delete")

        assert response.status_code == 200
        data = response.json()
        assert data["documents_deleted"] == 5
        assert data["status"] == "deleted"

    def test_delete_route_not_found(self, client, mock_route_manager):
        """Delete of missing route returns 404."""
        mock_route_manager.delete_route.side_effect = ValueError("not found")

        response = client.delete("/orchestration/routes/missing")

        assert response.status_code == 404


class TestSyncRoutesEndpoint:
    """Tests for POST /orchestration/routes/sync."""

    def test_sync_routes_success(self, client, mock_route_manager):
        """Successful sync returns 200 with stats."""
        mock_route_manager.sync_from_yaml.return_value = {
            "routes_synced": 15,
            "utterances_synced": 75,
            "documents_in_index": 75,
            "status": "success",
        }

        response = client.post("/orchestration/routes/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["routes_synced"] == 15
        assert data["utterances_synced"] == 75
        assert data["status"] == "success"

    def test_sync_routes_failure(self, client, mock_route_manager):
        """Sync failure returns 500."""
        mock_route_manager.sync_from_yaml.side_effect = RuntimeError("upload failed")

        response = client.post("/orchestration/routes/sync")

        assert response.status_code == 500


class TestSearchEndpoint:
    """Tests for POST /orchestration/routes/search."""

    def test_search_success(self, client, mock_route_manager):
        """Successful search returns 200 with results."""
        mock_route_manager.search_test.return_value = [
            {
                "route_name": "incident_etl",
                "category": "incident",
                "sub_intent": "etl_failure",
                "utterance": "ETL failed",
                "score": 0.95,
                "workflow_type": "magentic",
                "risk_level": "high",
            },
        ]

        response = client.post(
            "/orchestration/routes/search",
            json={"query": "ETL job broken", "top_k": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["route_name"] == "incident_etl"
        assert data[0]["score"] == 0.95

    def test_search_empty_query(self, client, mock_route_manager):
        """Empty query returns 422 validation error."""
        response = client.post(
            "/orchestration/routes/search",
            json={"query": "", "top_k": 5},
        )

        assert response.status_code == 422

    def test_search_top_k_bounds(self, client, mock_route_manager):
        """top_k outside 1-20 returns 422."""
        response = client.post(
            "/orchestration/routes/search",
            json={"query": "test", "top_k": 25},
        )
        assert response.status_code == 422

        response = client.post(
            "/orchestration/routes/search",
            json={"query": "test", "top_k": 0},
        )
        assert response.status_code == 422


class TestAzureNotEnabled:
    """Tests that endpoints return 503 when Azure Search is disabled."""

    def test_azure_not_enabled_returns_503(self):
        """When USE_AZURE_SEARCH is not true, endpoints return 503."""
        test_app = FastAPI()
        test_app.include_router(route_management_router)
        # Do NOT override get_route_manager, so the real factory runs
        test_client = TestClient(test_app, raise_server_exceptions=False)

        with patch.dict("os.environ", {"USE_AZURE_SEARCH": "false"}, clear=False):
            response = test_client.get("/orchestration/routes")
            assert response.status_code == 503
            assert "Azure AI Search is not enabled" in response.json()["detail"]

    def test_azure_not_set_returns_503(self):
        """When USE_AZURE_SEARCH env var is absent, endpoints return 503."""
        test_app = FastAPI()
        test_app.include_router(route_management_router)
        test_client = TestClient(test_app, raise_server_exceptions=False)

        with patch.dict("os.environ", {}, clear=False):
            # Ensure the env var is not set
            import os
            os.environ.pop("USE_AZURE_SEARCH", None)

            response = test_client.post(
                "/orchestration/routes",
                json={
                    "route_name": "test",
                    "category": "query",
                    "sub_intent": "status",
                    "utterances": ["test"],
                },
            )
            assert response.status_code == 503
