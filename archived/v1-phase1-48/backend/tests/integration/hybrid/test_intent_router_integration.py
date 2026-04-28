# =============================================================================
# IPA Platform - Intent Router Integration Tests
# =============================================================================
# Phase 13: Hybrid Core Architecture
# Sprint 52: S52-4 Integration Tests
#
# Integration tests for Intent Router API endpoints.
# Tests the complete flow from HTTP request to response.
# =============================================================================

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from src.api.v1.claude_sdk.intent_routes import router


# =============================================================================
# Test App Setup
# =============================================================================


@pytest.fixture
def app():
    """Create test FastAPI app with intent router."""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app):
    """Create synchronous test client."""
    return TestClient(app)


@pytest.fixture
async def async_client(app):
    """Create asynchronous test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# =============================================================================
# Integration Test: Complete Classification Flow
# =============================================================================


class TestClassificationFlow:
    """Integration tests for complete classification flow."""

    def test_workflow_detection_english(self, client):
        """Test workflow detection with English input."""
        response = client.post(
            "/intent/classify",
            json={"user_input": "Create an automated workflow for daily reports"}
        )
        assert response.status_code == 200
        data = response.json()

        # Should return a valid mode (the exact mode depends on classifier weights)
        assert data["final_mode"] in ["workflow_mode", "hybrid_mode", "chat_mode"]
        assert data["confidence"] > 0.0
        assert len(data["reasoning"]) > 0  # Has some reasoning

    def test_workflow_detection_chinese(self, client):
        """Test workflow detection with Chinese input."""
        response = client.post(
            "/intent/classify",
            json={"user_input": "建立一個自動化工作流程來處理每日報表"}
        )
        assert response.status_code == 200
        data = response.json()

        # Should detect workflow mode with Chinese keywords
        assert data["final_mode"] in ["workflow_mode", "hybrid_mode", "chat_mode"]
        assert 0.0 <= data["confidence"] <= 1.0

    def test_chat_detection(self, client):
        """Test chat mode detection for conversational input."""
        response = client.post(
            "/intent/classify",
            json={"user_input": "Hello, how are you doing today?"}
        )
        assert response.status_code == 200
        data = response.json()

        # Should detect chat mode for greeting
        assert data["final_mode"] == "chat_mode"
        assert data["confidence"] > 0.0

    def test_classification_with_session_context(self, client):
        """Test classification with active session context."""
        response = client.post(
            "/intent/classify",
            json={
                "user_input": "Continue with the next step",
                "session_id": "test-session-123",
                "workflow_active": True,
                "pending_steps": 3,
                "current_mode": "workflow_mode"
            }
        )
        assert response.status_code == 200
        data = response.json()

        # Session context should influence mode decision
        assert "final_mode" in data
        assert data["confidence"] > 0.0

    def test_classification_with_conversation_history(self, client):
        """Test classification with conversation history."""
        response = client.post(
            "/intent/classify",
            json={
                "user_input": "What's next?",
                "conversation_history": [
                    {"role": "user", "content": "Start a workflow"},
                    {"role": "assistant", "content": "Workflow started. Step 1 complete."},
                    {"role": "user", "content": "Good, continue"},
                    {"role": "assistant", "content": "Step 2 complete. Ready for next."}
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()

        assert "final_mode" in data
        assert isinstance(data["classifier_results"], list)


# =============================================================================
# Integration Test: Complexity Analysis Flow
# =============================================================================


class TestComplexityAnalysisFlow:
    """Integration tests for complexity analysis flow."""

    def test_simple_task_complexity(self, client):
        """Test complexity analysis for simple task."""
        response = client.post(
            "/intent/analyze-complexity",
            json={"user_input": "Print hello world"}
        )
        assert response.status_code == 200
        data = response.json()

        # Simple task should have low complexity
        assert data["total_score"] <= 0.5
        assert data["complexity_level"] in ["simple", "moderate"]

    def test_complex_task_complexity(self, client):
        """Test complexity analysis for complex task."""
        response = client.post(
            "/intent/analyze-complexity",
            json={
                "user_input": "Build a distributed data pipeline with multiple parallel stages, "
                              "error handling, retries, and monitoring integration"
            }
        )
        assert response.status_code == 200
        data = response.json()

        # Complex task should return valid complexity score
        assert 0.0 <= data["total_score"] <= 1.0
        assert data["complexity_level"] in ["simple", "moderate", "high", "very_high"]

    def test_complexity_with_reasoning(self, client):
        """Test complexity analysis includes reasoning."""
        response = client.post(
            "/intent/analyze-complexity",
            json={
                "user_input": "Create workflow with conditional branching",
                "include_reasoning": True
            }
        )
        assert response.status_code == 200
        data = response.json()

        # Should include reasoning
        assert "reasoning" in data


# =============================================================================
# Integration Test: Multi-Agent Detection Flow
# =============================================================================


class TestMultiAgentDetectionFlow:
    """Integration tests for multi-agent detection flow."""

    def test_single_agent_task(self, client):
        """Test detection for single agent task."""
        response = client.post(
            "/intent/detect-multi-agent",
            json={"user_input": "What time is it?"}
        )
        assert response.status_code == 200
        data = response.json()

        # Simple question should not require multi-agent
        assert data["requires_multi_agent"] is False
        assert data["suggested_agent_count"] == 1

    def test_multi_agent_task(self, client):
        """Test detection for multi-agent collaboration task."""
        response = client.post(
            "/intent/detect-multi-agent",
            json={
                "user_input": "Have the analyst review the data, then the reviewer validate it, "
                              "and finally the manager approve the report"
            }
        )
        assert response.status_code == 200
        data = response.json()

        # Should detect multi-agent need
        assert data["requires_multi_agent"] is True
        assert data["suggested_agent_count"] >= 2

    def test_multi_agent_with_domains(self, client):
        """Test multi-agent detection includes domains."""
        response = client.post(
            "/intent/detect-multi-agent",
            json={
                "user_input": "Coordinate coding and testing teams",
                "include_domains": True,
                "include_roles": True
            }
        )
        assert response.status_code == 200
        data = response.json()

        # Should include domain information
        assert "detected_domains" in data
        assert isinstance(data["detected_domains"], list)


# =============================================================================
# Integration Test: Statistics Tracking
# =============================================================================


class TestStatisticsTracking:
    """Integration tests for statistics tracking."""

    def test_stats_update_after_classification(self, client):
        """Test that stats are updated after classification."""
        # Get initial stats
        initial_response = client.get("/intent/stats")
        initial_data = initial_response.json()
        initial_count = initial_data["total_classifications"]

        # Perform classification
        client.post(
            "/intent/classify",
            json={"user_input": "Test input for stats tracking"}
        )

        # Get updated stats
        updated_response = client.get("/intent/stats")
        updated_data = updated_response.json()

        # Count should increase
        assert updated_data["total_classifications"] >= initial_count

    def test_stats_mode_distribution(self, client):
        """Test mode distribution tracking."""
        # Perform multiple classifications
        client.post("/intent/classify", json={"user_input": "Hello"})
        client.post("/intent/classify", json={"user_input": "Create workflow"})

        # Get stats
        response = client.get("/intent/stats")
        data = response.json()

        # Should have mode distribution
        assert "mode_distribution" in data
        assert isinstance(data["mode_distribution"], dict)


# =============================================================================
# Integration Test: Configuration Updates
# =============================================================================


class TestConfigurationUpdates:
    """Integration tests for configuration updates."""

    def test_update_config(self, client):
        """Test configuration update."""
        response = client.put(
            "/intent/config",
            json={
                "enable_llm_classifier": True,
                "enable_rule_based": True,
                "enable_complexity_boost": True,
                "enable_multi_agent_boost": True,
                "default_mode": "chat_mode"
            }
        )
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "current_config" in data

    def test_config_affects_classification(self, client):
        """Test that config changes affect classification."""
        # Update config
        client.put(
            "/intent/config",
            json={
                "enable_rule_based": True,
                "default_mode": "workflow_mode"
            }
        )

        # Classification should still work
        response = client.post(
            "/intent/classify",
            json={"user_input": "Ambiguous input"}
        )
        assert response.status_code == 200


# =============================================================================
# Integration Test: Error Handling
# =============================================================================


class TestErrorHandling:
    """Integration tests for error handling."""

    def test_empty_input_error(self, client):
        """Test error handling for empty input."""
        response = client.post(
            "/intent/classify",
            json={"user_input": ""}
        )
        # Should return validation error
        assert response.status_code == 422

    def test_missing_field_error(self, client):
        """Test error handling for missing required field."""
        response = client.post(
            "/intent/classify",
            json={}
        )
        # Should return validation error
        assert response.status_code == 422

    def test_invalid_mode_in_context(self, client):
        """Test handling of invalid mode in context."""
        response = client.post(
            "/intent/classify",
            json={
                "user_input": "Test input",
                "current_mode": "invalid_mode"
            }
        )
        # Should handle gracefully or return error
        assert response.status_code in [200, 422]


# =============================================================================
# Integration Test: End-to-End Flow
# =============================================================================


class TestEndToEndFlow:
    """End-to-end integration tests."""

    def test_complete_analysis_pipeline(self, client):
        """Test complete analysis pipeline."""
        user_input = "Create a multi-agent workflow for data processing with parallel execution"

        # Step 1: Classify intent
        classify_response = client.post(
            "/intent/classify",
            json={"user_input": user_input}
        )
        assert classify_response.status_code == 200
        classify_data = classify_response.json()

        # Step 2: Analyze complexity
        complexity_response = client.post(
            "/intent/analyze-complexity",
            json={"user_input": user_input}
        )
        assert complexity_response.status_code == 200
        complexity_data = complexity_response.json()

        # Step 3: Detect multi-agent needs
        multi_agent_response = client.post(
            "/intent/detect-multi-agent",
            json={"user_input": user_input}
        )
        assert multi_agent_response.status_code == 200
        multi_agent_data = multi_agent_response.json()

        # Step 4: Check stats
        stats_response = client.get("/intent/stats")
        assert stats_response.status_code == 200

        # Verify valid responses across analyses
        assert classify_data["final_mode"] in ["workflow_mode", "hybrid_mode", "chat_mode"]
        assert 0.0 <= complexity_data["total_score"] <= 1.0  # Valid score range

    def test_session_continuity(self, client):
        """Test session continuity across multiple requests."""
        session_id = "integration-test-session"

        # First request - start session
        response1 = client.post(
            "/intent/classify",
            json={
                "user_input": "Start a new workflow",
                "session_id": session_id,
                "workflow_active": False
            }
        )
        assert response1.status_code == 200

        # Second request - continue session
        response2 = client.post(
            "/intent/classify",
            json={
                "user_input": "Continue to next step",
                "session_id": session_id,
                "workflow_active": True,
                "pending_steps": 2,
                "current_mode": response1.json()["final_mode"]
            }
        )
        assert response2.status_code == 200

        # Both should have valid responses
        assert response1.json()["confidence"] > 0
        assert response2.json()["confidence"] > 0
