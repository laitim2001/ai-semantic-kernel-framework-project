"""Tests for /api/v1/health (liveness) + /api/v1/health/ready (readiness).

Sprint 49.4 Day 5.1.

The readiness path needs a real DB engine; we reuse the conftest.db_session
which is gated by docker compose postgres being up. If postgres is unreachable
the readiness test verifies the 503 path.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from api.main import create_app
from infrastructure.db import dispose_engine


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_each_test() -> None:
    """49.3 retrospective lesson: tests using FastAPI/httpx share an engine
    singleton with conftest.db_session. Without disposing, the next test
    file's first test sees a connection on a closed event loop."""
    yield
    await dispose_engine()


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_liveness_returns_ok(client: TestClient) -> None:
    """GET /api/v1/health → 200 with status=ok and version present."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"].startswith("2.0.0")


def test_readiness_endpoint_responds(client: TestClient) -> None:
    """GET /api/v1/health/ready → 200 (deps healthy) or 503 (deps degraded);
    must always include checks list with postgres entry."""
    resp = client.get("/api/v1/health/ready")
    assert resp.status_code in (200, 503)
    body = resp.json()
    assert body["status"] in ("ready", "degraded")
    assert isinstance(body["checks"], list)
    names = [c["name"] for c in body["checks"]]
    assert "postgres" in names
