"""Unit tests for the Expert Management API routes.

Sprint 162 — Phase 46 Agent Expert Registry.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1.experts.routes import router
from src.integrations.orchestration.experts.registry import reset_registry


@pytest.fixture(autouse=True)
def _reset():
    reset_registry()
    yield
    reset_registry()


@pytest.fixture()
def client():
    """Create a test client with just the experts router."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


# ------------------------------------------------------------------
# GET /experts/
# ------------------------------------------------------------------


class TestListExperts:
    def test_list_experts(self, client):
        """GET /experts/ should return all 6 built-in experts."""
        resp = client.get("/api/v1/experts/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 6
        names = [e["name"] for e in data["experts"]]
        assert "network_expert" in names
        assert "general" in names

    def test_list_experts_by_domain(self, client):
        """GET /experts/?domain=network should return only network experts."""
        resp = client.get("/api/v1/experts/?domain=network")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["experts"][0]["name"] == "network_expert"
        assert data["experts"][0]["domain"] == "network"

    def test_list_experts_empty_domain(self, client):
        """GET /experts/?domain=custom should return empty list."""
        resp = client.get("/api/v1/experts/?domain=custom")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["experts"] == []


# ------------------------------------------------------------------
# GET /experts/{name}
# ------------------------------------------------------------------


class TestGetExpert:
    def test_get_expert_by_name(self, client):
        """GET /experts/network_expert should return full expert details."""
        resp = client.get("/api/v1/experts/network_expert")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "network_expert"
        assert data["domain"] == "network"
        assert data["display_name"] == "Network Expert"
        assert data["display_name_zh"] == "網路專家"
        assert len(data["tools"]) > 0
        assert len(data["capabilities"]) > 0
        assert data["enabled"] is True

    def test_get_expert_not_found(self, client):
        """GET /experts/nonexistent should return 404."""
        resp = client.get("/api/v1/experts/nonexistent")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# ------------------------------------------------------------------
# POST /experts/reload
# ------------------------------------------------------------------


class TestReloadExperts:
    def test_reload_experts(self, client):
        """POST /experts/reload should return updated expert count."""
        resp = client.post("/api/v1/experts/reload")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["experts_loaded"] == 6
        assert "network_expert" in data["expert_names"]
        assert "general" in data["expert_names"]
