# =============================================================================
# IPA Platform - Intent Routes API Tests
# =============================================================================
# Phase 13: Hybrid Core Architecture
# Sprint 52: S52-3 Intent Router API Integration
#
# Unit tests for Intent Router REST API endpoints.
# =============================================================================

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from src.api.v1.claude_sdk.intent_routes import (
    router,
    get_intent_router,
    get_complexity_analyzer,
    get_multi_agent_detector,
    ClassifyIntentRequest,
    AnalyzeComplexityRequest,
    DetectMultiAgentRequest,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def client():
    """Create test client with intent router."""
    from fastapi import FastAPI
    app = FastAPI()
    # Router already has prefix="/intent"
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def mock_intent_router():
    """Create mock IntentRouter."""
    mock = MagicMock()
    mock.name = "test_router"
    mock.classifiers = []
    return mock


@pytest.fixture
def mock_complexity_analyzer():
    """Create mock ComplexityAnalyzer."""
    mock = MagicMock()
    mock.name = "test_complexity"
    return mock


@pytest.fixture
def mock_multi_agent_detector():
    """Create mock MultiAgentDetector."""
    mock = MagicMock()
    mock.name = "test_multi_agent"
    return mock


# =============================================================================
# Schema Tests
# =============================================================================

class TestSchemas:
    """Tests for Pydantic schemas."""

    def test_classify_intent_request_valid(self):
        """Test valid ClassifyIntentRequest."""
        request = ClassifyIntentRequest(
            user_input="Create a workflow",
            session_id="test-session",
        )
        assert request.user_input == "Create a workflow"
        assert request.session_id == "test-session"
        assert request.workflow_active is False  # default

    def test_classify_intent_request_with_context(self):
        """Test ClassifyIntentRequest with context."""
        request = ClassifyIntentRequest(
            user_input="Continue the task",
            workflow_active=True,
            pending_steps=3,
            current_mode="workflow_mode",
        )
        assert request.workflow_active is True
        assert request.pending_steps == 3
        assert request.current_mode == "workflow_mode"

    def test_classify_intent_request_with_history(self):
        """Test ClassifyIntentRequest with conversation history."""
        request = ClassifyIntentRequest(
            user_input="What next?",
            conversation_history=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ],
        )
        assert len(request.conversation_history) == 2

    def test_analyze_complexity_request_valid(self):
        """Test valid AnalyzeComplexityRequest."""
        request = AnalyzeComplexityRequest(
            user_input="Build a multi-step workflow with parallel execution",
        )
        assert request.user_input == "Build a multi-step workflow with parallel execution"
        assert request.include_reasoning is True  # default

    def test_detect_multi_agent_request_valid(self):
        """Test valid DetectMultiAgentRequest."""
        request = DetectMultiAgentRequest(
            user_input="Coordinate between analyst and reviewer agents",
        )
        assert request.user_input == "Coordinate between analyst and reviewer agents"
        assert request.include_domains is True  # default
        assert request.include_roles is True  # default


# =============================================================================
# GET Endpoints Tests
# =============================================================================

class TestGetEndpoints:
    """Tests for GET endpoints."""

    def test_list_classifiers(self, client):
        """Test list classifiers endpoint."""
        response = client.get("/intent/classifiers")
        assert response.status_code == 200
        data = response.json()
        assert "classifiers" in data
        assert isinstance(data["classifiers"], list)

    def test_get_stats(self, client):
        """Test get stats endpoint."""
        response = client.get("/intent/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_classifications" in data
        assert "mode_distribution" in data
        assert "avg_confidence" in data
        assert "avg_classification_time_ms" in data


# =============================================================================
# POST Endpoints Tests
# =============================================================================

class TestPostEndpoints:
    """Tests for POST endpoints."""

    def test_classify_intent_basic(self, client):
        """Test basic intent classification."""
        response = client.post(
            "/intent/classify",
            json={"user_input": "Hello, how are you?"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "final_mode" in data
        assert "confidence" in data
        assert "reasoning" in data

    def test_classify_intent_workflow_input(self, client):
        """Test intent classification with workflow keywords."""
        response = client.post(
            "/intent/classify",
            json={"user_input": "Create a new workflow for data processing"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "final_mode" in data
        # Workflow keywords should trigger workflow mode
        assert data["final_mode"] in ["workflow_mode", "chat_mode", "hybrid_mode"]

    def test_classify_intent_with_context(self, client):
        """Test intent classification with session context."""
        response = client.post(
            "/intent/classify",
            json={
                "user_input": "Continue with the task",
                "session_id": "test-session",
                "workflow_active": True,
                "pending_steps": 3,
                "current_mode": "workflow_mode",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "final_mode" in data

    def test_classify_intent_with_history(self, client):
        """Test intent classification with conversation history."""
        response = client.post(
            "/intent/classify",
            json={
                "user_input": "What next?",
                "conversation_history": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there"},
                ],
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "final_mode" in data

    def test_analyze_complexity_basic(self, client):
        """Test basic complexity analysis."""
        response = client.post(
            "/intent/analyze-complexity",
            json={"user_input": "Build a complex multi-step workflow"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_score" in data
        assert "complexity_level" in data

    def test_analyze_complexity_simple_task(self, client):
        """Test complexity analysis for simple task."""
        response = client.post(
            "/intent/analyze-complexity",
            json={"user_input": "Hello"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_score" in data
        # Total score should be between 0 and 1
        assert 0.0 <= data["total_score"] <= 1.0

    def test_analyze_complexity_with_reasoning(self, client):
        """Test complexity analysis with reasoning."""
        response = client.post(
            "/intent/analyze-complexity",
            json={
                "user_input": "Coordinate multiple agents for parallel data processing",
                "include_reasoning": True,
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "reasoning" in data or data.get("reasoning") is None

    def test_detect_multi_agent_basic(self, client):
        """Test basic multi-agent detection."""
        response = client.post(
            "/intent/detect-multi-agent",
            json={"user_input": "Coordinate analyst and reviewer"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "requires_multi_agent" in data
        assert "suggested_agent_count" in data

    def test_detect_multi_agent_single_agent_task(self, client):
        """Test multi-agent detection for single agent task."""
        response = client.post(
            "/intent/detect-multi-agent",
            json={"user_input": "What is the weather?"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "requires_multi_agent" in data
        # Simple question should not require multi-agent
        assert isinstance(data["requires_multi_agent"], bool)


# =============================================================================
# PUT Endpoints Tests
# =============================================================================

class TestPutEndpoints:
    """Tests for PUT endpoints."""

    def test_update_config_basic(self, client):
        """Test basic config update."""
        response = client.put(
            "/intent/config",
            json={"enable_llm_classifier": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert data["success"] is True

    def test_update_config_defaults(self, client):
        """Test config update with default settings."""
        response = client.put(
            "/intent/config",
            json={
                "enable_llm_classifier": True,
                "enable_rule_based": True,
                "enable_complexity_boost": True,
                "enable_multi_agent_boost": True,
                "default_mode": "chat_mode",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error handling."""

    def test_classify_intent_missing_input(self, client):
        """Test classification with missing required field."""
        response = client.post(
            "/intent/classify",
            json={}  # Missing user_input
        )
        assert response.status_code == 422  # Validation error

    def test_classify_intent_empty_input(self, client):
        """Test classification with empty input (should fail validation)."""
        response = client.post(
            "/intent/classify",
            json={"user_input": ""}
        )
        # min_length=1 should cause validation error
        assert response.status_code == 422

    def test_analyze_complexity_missing_input(self, client):
        """Test complexity analysis with missing field."""
        response = client.post(
            "/intent/analyze-complexity",
            json={}
        )
        assert response.status_code == 422

    def test_detect_multi_agent_missing_input(self, client):
        """Test multi-agent detection with missing field."""
        response = client.post(
            "/intent/detect-multi-agent",
            json={}
        )
        assert response.status_code == 422


# =============================================================================
# Statistics Tracking Tests
# =============================================================================

class TestStatisticsTracking:
    """Tests for statistics tracking."""

    def test_stats_after_classification(self, client):
        """Test that stats are tracked after classification."""
        # Perform classification
        client.post(
            "/intent/classify",
            json={"user_input": "Test input for stats"}
        )

        # Get stats
        response = client.get("/intent/stats")
        assert response.status_code == 200
        data = response.json()

        # Stats should include expected fields
        assert "total_classifications" in data
        assert "mode_distribution" in data
        assert "avg_confidence" in data

    def test_stats_confidence_in_range(self, client):
        """Test average confidence is in valid range."""
        # Perform a classification
        client.post(
            "/intent/classify",
            json={"user_input": "Explain this concept"}
        )

        # Get stats
        response = client.get("/intent/stats")
        data = response.json()

        # Average confidence should be between 0 and 1
        assert 0.0 <= data["avg_confidence"] <= 1.0


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for intent routes."""

    def test_full_classification_flow(self, client):
        """Test complete classification flow."""
        # Step 1: Classify intent
        classify_response = client.post(
            "/intent/classify",
            json={"user_input": "Create a workflow with multiple steps"}
        )
        assert classify_response.status_code == 200
        classify_data = classify_response.json()
        assert "final_mode" in classify_data

        # Step 2: Analyze complexity
        complexity_response = client.post(
            "/intent/analyze-complexity",
            json={"user_input": "Create a workflow with multiple steps"}
        )
        assert complexity_response.status_code == 200
        complexity_data = complexity_response.json()
        assert "total_score" in complexity_data

        # Step 3: Detect multi-agent needs
        multi_agent_response = client.post(
            "/intent/detect-multi-agent",
            json={"user_input": "Create a workflow with multiple steps"}
        )
        assert multi_agent_response.status_code == 200
        multi_agent_data = multi_agent_response.json()
        assert "requires_multi_agent" in multi_agent_data

        # Step 4: Check stats
        stats_response = client.get("/intent/stats")
        assert stats_response.status_code == 200

    def test_chinese_input_handling(self, client):
        """Test handling of Chinese input."""
        response = client.post(
            "/intent/classify",
            json={"user_input": "建立一個新的工作流程來處理資料"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "final_mode" in data
        assert "confidence" in data

    def test_mixed_language_input(self, client):
        """Test handling of mixed language input."""
        response = client.post(
            "/intent/classify",
            json={"user_input": "Create a workflow 來處理 data processing"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "final_mode" in data

    def test_response_structure(self, client):
        """Test that response has expected structure."""
        response = client.post(
            "/intent/classify",
            json={"user_input": "Create a multi-step automated workflow"}
        )
        assert response.status_code == 200
        data = response.json()

        # Check all expected fields
        assert "user_input" in data
        assert "final_mode" in data
        assert "confidence" in data
        assert "reasoning" in data
        assert "classifier_results" in data
        assert isinstance(data["classifier_results"], list)
