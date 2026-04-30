"""
File: backend/tests/integration/mock_services/test_mock_services_startup.py
Purpose: TestClient smoke for all 7 mock_services routers (in-process).
Category: Tests / Integration / mock_services
Scope: Phase 51 / Sprint 51.0 Day 4.1

Description:
    Validates that the mock_services FastAPI app starts via lifespan loader,
    all 7 routers are mounted, and at least one happy-path endpoint per
    router responds 200. No subprocess; pure in-process TestClient (~50ms).

Created: 2026-04-30 (Sprint 51.0 Day 4)
Last Modified: 2026-04-30
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from mock_services.main import app


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    """`with TestClient(app)` is required so FastAPI lifespan loads seed.json."""
    with TestClient(app) as c:
        yield c


def test_health_returns_seed_stats(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"
    stats = payload["db_stats"]
    assert stats["customers"] == 10
    assert stats["orders"] == 50
    assert stats["incidents"] == 5
    assert stats["alerts"] == 20


def test_root_banner(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["service"] == "v2-mock-services"
    assert "warning" in payload  # must NOT use in production


def test_crm_router_mounted(client: TestClient) -> None:
    resp = client.get("/mock/crm/customers/cust_001")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Acme Corp"


def test_kb_router_mounted(client: TestClient) -> None:
    resp = client.post("/mock/kb/search", json={"query": "2FA", "top_k": 3})
    assert resp.status_code == 200
    hits = resp.json()
    assert len(hits) >= 1
    assert hits[0]["score"] == 1.0  # title match


def test_patrol_router_mounted(client: TestClient) -> None:
    resp = client.post("/mock/patrol/check_servers", json={"scope": ["web-01", "web-02"]})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 2
    assert all("server_id" in r and "health" in r for r in results)


def test_correlation_router_mounted(client: TestClient) -> None:
    resp = client.post("/mock/correlation/analyze", json={"alert_ids": ["alert_006", "alert_007"]})
    assert resp.status_code == 200
    chains = resp.json()
    assert len(chains) == 2
    assert all("primary_alert_id" in c for c in chains)


def test_rootcause_router_mounted(client: TestClient) -> None:
    resp = client.post("/mock/rootcause/diagnose", json={"incident_id": "inc_001"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["incident_id"] == "inc_001"
    assert "hypothesis" in payload
    assert 0.0 <= payload["confidence"] <= 1.0


def test_audit_router_mounted(client: TestClient) -> None:
    resp = client.post("/mock/audit/query_logs", json={"limit": 5})
    assert resp.status_code == 200
    logs = resp.json()
    assert isinstance(logs, list)
    assert len(logs) <= 5


def test_incident_router_mounted(client: TestClient) -> None:
    resp = client.get("/mock/incident/inc_002")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["id"] == "inc_002"
    assert payload["title"] == "Payment gateway 3rd-party degradation"


def test_404_for_unknown_id(client: TestClient) -> None:
    resp = client.get("/mock/crm/customers/missing_123")
    assert resp.status_code == 404


def test_apply_fix_dry_run_default(client: TestClient) -> None:
    """Sprint 51.0 §決策 5 — apply_fix dry_run=true default; mock confirms invariant."""
    resp = client.post("/mock/rootcause/apply_fix", json={"fix_id": "fix_test_001"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["dry_run"] is True
    assert payload["status"] == "dry_run_ok"


def test_incident_close_returns_pending_review(client: TestClient) -> None:
    """Sprint 51.0 §08b §Domain 5 — close is HIGH risk; mock returns closed_pending_review."""
    create_resp = client.post(
        "/mock/incident/create",
        json={"title": "Test for close", "severity": "medium"},
    )
    inc_id = create_resp.json()["id"]
    close_resp = client.post(
        "/mock/incident/close",
        json={"incident_id": inc_id, "resolution": "test resolution"},
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "closed_pending_review"
