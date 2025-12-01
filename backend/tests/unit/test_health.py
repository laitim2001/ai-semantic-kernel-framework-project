# =============================================================================
# IPA Platform - Health Endpoint Tests
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Tests for the health check and readiness endpoints.
# =============================================================================


def test_root_endpoint(client):
    """Test root endpoint returns API information."""
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["service"] == "IPA Platform API"
    assert data["status"] == "running"
    assert data["framework"] == "Microsoft Agent Framework"
    assert "version" in data


def test_health_endpoint(client):
    """
    Test health check endpoint.

    Note: In test environment without database, status may be "degraded".
    This is expected behavior - the API is still functional.
    """
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    # Accept both healthy and degraded status (degraded when no DB in test env)
    assert data["status"] in ["healthy", "degraded"]
    assert "version" in data
    assert "timestamp" in data
    assert "checks" in data
    assert data["checks"]["api"] == "ok"


def test_health_endpoint_returns_database_status(client):
    """Test health check includes database status."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    # Database check should be present
    assert "database" in data["checks"]
    # In test env without DB, it will be "degraded"
    assert data["checks"]["database"] in ["ok", "degraded"]


def test_readiness_endpoint(client):
    """Test readiness check endpoint."""
    response = client.get("/ready")
    assert response.status_code == 200

    data = response.json()
    assert data["ready"] is True
    assert "version" in data
