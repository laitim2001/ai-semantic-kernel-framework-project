"""Unit tests for the Expert Management API routes.

Sprint 162 — Phase 46 Agent Expert Registry.
Sprint 163 — Updated for DB-backed routes with mock repo.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1.experts.routes import router, _get_repo
from src.infrastructure.database.session import get_session
from src.integrations.orchestration.experts.registry import (
    AgentExpertDefinition,
    get_registry,
    reset_registry,
)


def _build_mock_repo():
    """Build a mock repo that delegates to the YAML registry."""
    registry = get_registry()
    repo = AsyncMock()

    async def mock_list_all(domain=None, enabled=None):
        experts = registry.list_by_domain(domain) if domain else registry.list_all()
        return [_def_to_mock_row(e) for e in experts]

    async def mock_get_by_name(name):
        e = registry.get(name)
        return _def_to_mock_row(e) if e else None

    repo.list_all = mock_list_all
    repo.get_by_name = mock_get_by_name
    return repo


def _def_to_mock_row(e: AgentExpertDefinition):
    """Convert AgentExpertDefinition to a mock DB row with to_dict()."""
    row = MagicMock()
    d = e.to_dict()
    d["id"] = "00000000-0000-0000-0000-000000000000"
    d["is_builtin"] = True
    d["version"] = 1
    d["created_at"] = None
    d["updated_at"] = None
    row.to_dict.return_value = d
    row.is_builtin = True
    return row


@pytest.fixture(autouse=True)
def _reset():
    reset_registry()
    yield
    reset_registry()


@pytest.fixture()
def client():
    """Test client with mocked DB dependencies."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    app.dependency_overrides[_get_repo] = _build_mock_repo
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

    def test_list_experts_empty_domain(self, client):
        """GET /experts/?domain=custom should return empty list."""
        resp = client.get("/api/v1/experts/?domain=custom")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0


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
        assert len(data["tools"]) > 0
        assert data["is_builtin"] is True

    def test_get_expert_not_found(self, client):
        """GET /experts/nonexistent should return 404."""
        resp = client.get("/api/v1/experts/nonexistent")
        assert resp.status_code == 404
