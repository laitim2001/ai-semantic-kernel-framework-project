# =============================================================================
# IPA Platform - Risk Assessment API Unit Tests
# =============================================================================
# Sprint 55: S55-4 - API & ApprovalHook Integration
#
# Unit tests for risk assessment API routes:
#   - POST /hybrid/risk/assess
#   - POST /hybrid/risk/assess-batch
#   - GET /hybrid/risk/session/{session_id}
#   - GET /hybrid/risk/metrics
#   - DELETE /hybrid/risk/session/{session_id}/history
#   - POST /hybrid/risk/metrics/reset
#   - GET /hybrid/risk/config
# =============================================================================

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi import status
from fastapi.testclient import TestClient

from src.integrations.hybrid.risk.models import (
    OperationContext,
    RiskAssessment,
    RiskConfig,
    RiskFactor,
    RiskFactorType,
    RiskLevel,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_operation_context():
    """Create a mock operation context."""
    return OperationContext(
        tool_name="Bash",
        operation_type="execute",
        target_paths=["/tmp/test.sh"],
        command="bash /tmp/test.sh",
        session_id="sess-123",
        user_id="user-456",
        environment="development",
    )


@pytest.fixture
def mock_risk_factor():
    """Create a mock risk factor."""
    return RiskFactor(
        factor_type=RiskFactorType.OPERATION,
        score=0.6,
        weight=0.4,
        description="Bash tool has moderate base risk",
        source="Bash",
    )


@pytest.fixture
def mock_risk_assessment(mock_risk_factor):
    """Create a mock risk assessment."""
    return RiskAssessment(
        overall_level=RiskLevel.MEDIUM,
        overall_score=0.55,
        requires_approval=False,
        approval_reason=None,
        factors=[mock_risk_factor],
        session_id="sess-123",
        assessment_time=datetime.utcnow(),
    )


@pytest.fixture
def mock_engine(mock_risk_assessment):
    """Create a mock RiskAssessmentEngine."""
    engine = MagicMock()
    engine.assess.return_value = mock_risk_assessment
    engine.assess_batch.return_value = [mock_risk_assessment]
    engine.get_session_risk.return_value = MagicMock(
        score=0.45,
        level=RiskLevel.LOW,
        strategy_used=MagicMock(value="weighted_average"),
    )
    engine.get_metrics.return_value = MagicMock(
        total_assessments=100,
        assessments_by_level={"low": 50, "medium": 30, "high": 15, "critical": 5},
        average_score=0.45,
        approval_rate=0.20,
        average_latency_ms=25.5,
    )
    engine.clear_session_history.return_value = 5
    engine.reset_metrics.return_value = None
    engine.config = RiskConfig()
    return engine


@pytest.fixture
def mock_pattern_detector():
    """Create a mock PatternDetector."""
    detector = MagicMock()
    detector.get_session_state.return_value = {"operation_count": 10}
    detector.clear_session.return_value = None
    return detector


@pytest.fixture
def client(mock_engine, mock_pattern_detector):
    """Create test client with mocked dependencies."""
    # Import here to avoid circular imports
    from main import app

    with patch(
        "src.api.v1.hybrid.risk_routes.get_engine",
        return_value=mock_engine
    ), patch(
        "src.api.v1.hybrid.risk_routes.get_pattern_detector",
        return_value=mock_pattern_detector
    ):
        yield TestClient(app)


# =============================================================================
# Test: POST /hybrid/risk/assess
# =============================================================================


class TestAssessRisk:
    """Tests for single operation risk assessment."""

    def test_assess_risk_success(self, client):
        """Test successful risk assessment."""
        response = client.post(
            "/api/v1/hybrid/risk/assess",
            json={
                "tool_name": "Bash",
                "operation_type": "execute",
                "command": "ls -la",
                "session_id": "sess-123",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "overall_level" in data
        assert "overall_score" in data
        assert "requires_approval" in data
        assert "factors" in data

    def test_assess_risk_with_paths(self, client):
        """Test risk assessment with target paths."""
        response = client.post(
            "/api/v1/hybrid/risk/assess",
            json={
                "tool_name": "Write",
                "operation_type": "write",
                "target_paths": ["/etc/config.yaml"],
                "session_id": "sess-123",
            },
        )

        assert response.status_code == status.HTTP_200_OK

    def test_assess_risk_with_user_trust(self, client):
        """Test risk assessment with user trust level."""
        response = client.post(
            "/api/v1/hybrid/risk/assess",
            json={
                "tool_name": "Bash",
                "operation_type": "execute",
                "command": "rm -rf /tmp/test",
                "session_id": "sess-123",
                "user_id": "user-456",
                "user_trust_level": "high",
            },
        )

        assert response.status_code == status.HTTP_200_OK

    def test_assess_risk_minimal_request(self, client):
        """Test risk assessment with minimal required fields."""
        response = client.post(
            "/api/v1/hybrid/risk/assess",
            json={"tool_name": "Read"},
        )

        assert response.status_code == status.HTTP_200_OK

    def test_assess_risk_missing_tool_name(self, client):
        """Test risk assessment without required tool_name."""
        response = client.post(
            "/api/v1/hybrid/risk/assess",
            json={"command": "ls"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# Test: POST /hybrid/risk/assess-batch
# =============================================================================


class TestAssessRiskBatch:
    """Tests for batch risk assessment."""

    def test_assess_batch_success(self, client):
        """Test successful batch assessment."""
        response = client.post(
            "/api/v1/hybrid/risk/assess-batch",
            json={
                "operations": [
                    {"tool_name": "Read", "target_paths": ["/config.yaml"]},
                    {"tool_name": "Bash", "command": "ls -la"},
                ]
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "assessments" in data
        assert "total_operations" in data
        assert "max_risk_level" in data
        assert "average_risk_score" in data
        assert "approvals_required" in data

    def test_assess_batch_single_operation(self, client):
        """Test batch with single operation."""
        response = client.post(
            "/api/v1/hybrid/risk/assess-batch",
            json={
                "operations": [
                    {"tool_name": "Glob", "target_paths": ["**/*.py"]},
                ]
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_operations"] == 1

    def test_assess_batch_empty_list(self, client):
        """Test batch with empty operations list."""
        response = client.post(
            "/api/v1/hybrid/risk/assess-batch",
            json={"operations": []},
        )

        # Pydantic validation should fail (min_length=1)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# Test: GET /hybrid/risk/session/{session_id}
# =============================================================================


class TestGetSessionRisk:
    """Tests for session risk query."""

    def test_get_session_risk_success(self, client):
        """Test successful session risk query."""
        response = client.get("/api/v1/hybrid/risk/session/sess-123")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"] == "sess-123"
        assert "overall_score" in data
        assert "overall_level" in data
        assert "operations_in_window" in data

    def test_get_session_risk_with_window(self, client):
        """Test session risk with custom time window."""
        response = client.get(
            "/api/v1/hybrid/risk/session/sess-123",
            params={"window_seconds": 600},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["window_seconds"] == 600


# =============================================================================
# Test: GET /hybrid/risk/metrics
# =============================================================================


class TestGetMetrics:
    """Tests for engine metrics endpoint."""

    def test_get_metrics_success(self, client):
        """Test successful metrics retrieval."""
        response = client.get("/api/v1/hybrid/risk/metrics")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_assessments" in data
        assert "assessments_by_level" in data
        assert "average_score" in data
        assert "approval_rate" in data
        assert "average_latency_ms" in data


# =============================================================================
# Test: DELETE /hybrid/risk/session/{session_id}/history
# =============================================================================


class TestClearSessionHistory:
    """Tests for clearing session history."""

    def test_clear_session_history_success(self, client):
        """Test successful history clearing."""
        response = client.delete("/api/v1/hybrid/risk/session/sess-123/history")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"] == "sess-123"
        assert data["success"] is True
        assert "entries_cleared" in data


# =============================================================================
# Test: POST /hybrid/risk/metrics/reset
# =============================================================================


class TestResetMetrics:
    """Tests for resetting engine metrics."""

    def test_reset_metrics_success(self, client):
        """Test successful metrics reset."""
        response = client.post("/api/v1/hybrid/risk/metrics/reset")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True


# =============================================================================
# Test: GET /hybrid/risk/config
# =============================================================================


class TestGetConfig:
    """Tests for getting configuration."""

    def test_get_config_success(self, client):
        """Test successful config retrieval."""
        response = client.get("/api/v1/hybrid/risk/config")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "critical_threshold" in data
        assert "high_threshold" in data
        assert "medium_threshold" in data
        assert "operation_weight" in data
        assert "context_weight" in data
        assert "pattern_weight" in data
        assert "auto_approve_low" in data
        assert "auto_approve_medium" in data


# =============================================================================
# Test: Response Format Validation
# =============================================================================


class TestResponseFormat:
    """Tests for response format validation."""

    def test_risk_level_values(self, client):
        """Test that risk levels are valid strings."""
        response = client.post(
            "/api/v1/hybrid/risk/assess",
            json={"tool_name": "Bash", "command": "ls"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["overall_level"] in ["low", "medium", "high", "critical"]

    def test_score_range(self, client):
        """Test that scores are within valid range."""
        response = client.post(
            "/api/v1/hybrid/risk/assess",
            json={"tool_name": "Bash", "command": "ls"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 0.0 <= data["overall_score"] <= 1.0

    def test_factors_structure(self, client):
        """Test that factors have correct structure."""
        response = client.post(
            "/api/v1/hybrid/risk/assess",
            json={"tool_name": "Bash", "command": "ls"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        for factor in data["factors"]:
            assert "factor_type" in factor
            assert "score" in factor
            assert "weight" in factor
            assert "weighted_score" in factor
            assert "description" in factor
