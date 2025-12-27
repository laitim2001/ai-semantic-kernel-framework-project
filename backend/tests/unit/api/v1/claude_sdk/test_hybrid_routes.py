"""Tests for Claude SDK Hybrid API routes.

Sprint 51: S51-4 Hybrid API Routes Unit Tests
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.v1.claude_sdk.hybrid_routes import (
    router,
    FrameworkType,
    TaskCapabilityType,
)


# Create test app
app = FastAPI()
app.include_router(router, prefix="/api/v1/claude-sdk")


class TestHybridRoutes:
    """Tests for Claude SDK Hybrid API routes."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_orchestrator(self):
        """Create a mock orchestrator."""
        mock = MagicMock()
        mock.execute = AsyncMock()
        mock.analyze_task = AsyncMock()
        mock.get_metrics = MagicMock()
        return mock

    @pytest.fixture
    def mock_synchronizer(self):
        """Create a mock synchronizer."""
        mock = MagicMock()
        mock.sync = AsyncMock()
        return mock

    @pytest.fixture
    def mock_capability_matcher(self):
        """Create a mock capability matcher."""
        mock = MagicMock()
        mock.analyze = MagicMock(return_value={})
        mock.match_framework = MagicMock()
        return mock


class TestExecuteHybridEndpoint(TestHybridRoutes):
    """Tests for POST /hybrid/execute endpoint."""

    def test_execute_task_success(self, client, mock_orchestrator):
        """Test executing a task successfully."""
        # Mock the result
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.content = "Task completed"
        mock_result.tool_calls = []
        mock_result.framework_used = None
        mock_result.error = None
        mock_orchestrator.execute.return_value = mock_result

        with patch(
            "src.api.v1.claude_sdk.hybrid_routes.get_orchestrator",
            return_value=mock_orchestrator,
        ):
            response = client.post(
                "/api/v1/claude-sdk/hybrid/execute",
                json={
                    "task": "Analyze the code",
                    "preferred_framework": "auto",
                    "context": {"file": "test.py"},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["content"] == "Task completed"
            assert "session_id" in data

    def test_execute_task_with_session_id(self, client, mock_orchestrator):
        """Test executing a task with provided session ID."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.content = "Result"
        mock_result.tool_calls = []
        mock_result.framework_used = None
        mock_result.error = None
        mock_orchestrator.execute.return_value = mock_result

        with patch(
            "src.api.v1.claude_sdk.hybrid_routes.get_orchestrator",
            return_value=mock_orchestrator,
        ):
            response = client.post(
                "/api/v1/claude-sdk/hybrid/execute",
                json={
                    "task": "Do something",
                    "session_id": "my-session-123",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "my-session-123"

    def test_execute_task_with_tools(self, client, mock_orchestrator):
        """Test executing a task with tool calls."""
        mock_tool_call = MagicMock()
        mock_tool_call.name = "Read"
        mock_tool_call.arguments = {"file_path": "/test.py"}
        mock_tool_call.result = "File content"
        mock_tool_call.duration_ms = 50.5

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.content = "Analyzed file"
        mock_result.tool_calls = [mock_tool_call]
        mock_result.framework_used = None
        mock_result.error = None
        mock_orchestrator.execute.return_value = mock_result

        with patch(
            "src.api.v1.claude_sdk.hybrid_routes.get_orchestrator",
            return_value=mock_orchestrator,
        ):
            response = client.post(
                "/api/v1/claude-sdk/hybrid/execute",
                json={
                    "task": "Read and analyze file",
                    "tools": ["Read", "Grep"],
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["tool_calls"]) == 1
            assert data["tool_calls"][0]["name"] == "Read"

    def test_execute_task_error_handling(self, client, mock_orchestrator):
        """Test error handling during execution."""
        mock_orchestrator.execute.side_effect = Exception("Execution failed")

        with patch(
            "src.api.v1.claude_sdk.hybrid_routes.get_orchestrator",
            return_value=mock_orchestrator,
        ):
            response = client.post(
                "/api/v1/claude-sdk/hybrid/execute",
                json={"task": "Fail task"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "Execution failed" in data["error"]

    def test_execute_task_framework_preference(self, client, mock_orchestrator):
        """Test executing with preferred framework."""
        from src.integrations.claude_sdk.hybrid.types import Framework

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.content = "Done"
        mock_result.tool_calls = []
        mock_result.framework_used = Framework.CLAUDE_SDK
        mock_result.error = None
        mock_orchestrator.execute.return_value = mock_result

        with patch(
            "src.api.v1.claude_sdk.hybrid_routes.get_orchestrator",
            return_value=mock_orchestrator,
        ):
            response = client.post(
                "/api/v1/claude-sdk/hybrid/execute",
                json={
                    "task": "Test task",
                    "preferred_framework": "claude_sdk",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["framework_used"] == "claude_sdk"


class TestAnalyzeEndpoint(TestHybridRoutes):
    """Tests for POST /hybrid/analyze endpoint."""

    def test_analyze_task_success(
        self, client, mock_orchestrator, mock_capability_matcher
    ):
        """Test analyzing a task successfully."""
        from src.integrations.claude_sdk.hybrid.types import TaskCapability, Framework

        # Mock analysis result
        mock_analysis = MagicMock()
        mock_analysis.complexity_score = 0.7
        mock_analysis.reasoning = "Complex multi-step task"
        mock_orchestrator.analyze_task.return_value = mock_analysis

        # Mock capabilities
        mock_capability_matcher.analyze.return_value = {
            TaskCapability.CODE_EXECUTION: 0.9,
            TaskCapability.TOOL_USE: 0.8,
        }
        mock_capability_matcher.match_framework.return_value = Framework.CLAUDE_SDK

        with patch(
            "src.api.v1.claude_sdk.hybrid_routes.get_orchestrator",
            return_value=mock_orchestrator,
        ), patch(
            "src.api.v1.claude_sdk.hybrid_routes.get_capability_matcher",
            return_value=mock_capability_matcher,
        ):
            response = client.post(
                "/api/v1/claude-sdk/hybrid/analyze",
                json={
                    "task": "Analyze and execute code",
                    "context": {"language": "python"},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["task"] == "Analyze and execute code"
            assert data["complexity_score"] == 0.7
            assert data["recommended_framework"] == "claude_sdk"
            assert len(data["capabilities"]) == 2

    def test_analyze_task_error(self, client, mock_orchestrator, mock_capability_matcher):
        """Test analyze task error handling."""
        mock_orchestrator.analyze_task.side_effect = Exception("Analysis failed")

        with patch(
            "src.api.v1.claude_sdk.hybrid_routes.get_orchestrator",
            return_value=mock_orchestrator,
        ), patch(
            "src.api.v1.claude_sdk.hybrid_routes.get_capability_matcher",
            return_value=mock_capability_matcher,
        ):
            response = client.post(
                "/api/v1/claude-sdk/hybrid/analyze",
                json={"task": "Test task"},
            )
            assert response.status_code == 500
            assert "Analysis failed" in response.json()["detail"]


class TestMetricsEndpoint(TestHybridRoutes):
    """Tests for GET /hybrid/metrics endpoint."""

    def test_get_metrics_success(self, client, mock_orchestrator):
        """Test getting metrics successfully."""
        mock_metrics = MagicMock()
        mock_metrics.total_executions = 100
        mock_metrics.claude_sdk_executions = 60
        mock_metrics.ms_agent_executions = 40
        mock_metrics.avg_execution_time_ms = 250.5
        mock_metrics.success_rate = 0.95
        mock_metrics.capability_distribution = {"code_execution": 30, "tool_use": 70}
        mock_metrics.last_updated = datetime(2025, 12, 26, 10, 0, 0)
        mock_orchestrator.get_metrics.return_value = mock_metrics

        with patch(
            "src.api.v1.claude_sdk.hybrid_routes.get_orchestrator",
            return_value=mock_orchestrator,
        ):
            response = client.get("/api/v1/claude-sdk/hybrid/metrics")
            assert response.status_code == 200
            data = response.json()
            assert data["total_executions"] == 100
            assert data["claude_sdk_executions"] == 60
            assert data["ms_agent_executions"] == 40
            assert data["avg_execution_time_ms"] == 250.5
            assert data["success_rate"] == 0.95

    def test_get_metrics_error(self, client, mock_orchestrator):
        """Test metrics error handling."""
        mock_orchestrator.get_metrics.side_effect = Exception("Metrics unavailable")

        with patch(
            "src.api.v1.claude_sdk.hybrid_routes.get_orchestrator",
            return_value=mock_orchestrator,
        ):
            response = client.get("/api/v1/claude-sdk/hybrid/metrics")
            assert response.status_code == 500
            assert "Failed to get metrics" in response.json()["detail"]


class TestContextSyncEndpoint(TestHybridRoutes):
    """Tests for POST /hybrid/context/sync endpoint."""

    def test_sync_context_success(self, client, mock_synchronizer):
        """Test synchronizing context successfully."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.synced_keys = ["session_id", "history", "context"]
        mock_result.conflicts = []
        mock_result.error = None
        mock_synchronizer.sync.return_value = mock_result

        with patch(
            "src.api.v1.claude_sdk.hybrid_routes.get_synchronizer",
            return_value=mock_synchronizer,
        ):
            response = client.post(
                "/api/v1/claude-sdk/hybrid/context/sync",
                json={
                    "session_id": "session-123",
                    "source_framework": "claude_sdk",
                    "target_framework": "microsoft_agent",
                    "context": {"key": "value"},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["session_id"] == "session-123"
            assert len(data["synced_keys"]) == 3

    def test_sync_context_with_conflicts(self, client, mock_synchronizer):
        """Test synchronizing context with conflicts."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.synced_keys = ["session_id"]
        mock_result.conflicts = ["history"]
        mock_result.error = None
        mock_synchronizer.sync.return_value = mock_result

        with patch(
            "src.api.v1.claude_sdk.hybrid_routes.get_synchronizer",
            return_value=mock_synchronizer,
        ):
            response = client.post(
                "/api/v1/claude-sdk/hybrid/context/sync",
                json={
                    "session_id": "session-456",
                    "source_framework": "microsoft_agent",
                    "target_framework": "claude_sdk",
                    "context": {},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "history" in data["conflicts"]

    def test_sync_context_error(self, client, mock_synchronizer):
        """Test sync error handling."""
        mock_synchronizer.sync.side_effect = Exception("Sync failed")

        with patch(
            "src.api.v1.claude_sdk.hybrid_routes.get_synchronizer",
            return_value=mock_synchronizer,
        ):
            response = client.post(
                "/api/v1/claude-sdk/hybrid/context/sync",
                json={
                    "session_id": "session-789",
                    "source_framework": "claude_sdk",
                    "target_framework": "microsoft_agent",
                    "context": {},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "Sync failed" in data["error"]


class TestCapabilitiesEndpoint(TestHybridRoutes):
    """Tests for GET /hybrid/capabilities endpoint."""

    def test_list_capabilities(self, client):
        """Test listing framework capabilities."""
        response = client.get("/api/v1/claude-sdk/hybrid/capabilities")
        assert response.status_code == 200
        data = response.json()

        assert "capabilities" in data
        assert "claude_sdk" in data["capabilities"]
        assert "microsoft_agent" in data["capabilities"]
        assert data["total_capabilities"] > 0

        # Check Claude SDK capabilities
        claude_caps = data["capabilities"]["claude_sdk"]
        assert "tool_use" in claude_caps
        assert "conversation" in claude_caps

        # Check MS Agent capabilities
        ms_caps = data["capabilities"]["microsoft_agent"]
        assert "multi_agent" in ms_caps
        assert "handoff" in ms_caps


class TestHybridEnums:
    """Tests for hybrid enums."""

    def test_framework_type_values(self):
        """Test FrameworkType enum values."""
        assert FrameworkType.CLAUDE_SDK.value == "claude_sdk"
        assert FrameworkType.MICROSOFT_AGENT.value == "microsoft_agent"
        assert FrameworkType.AUTO.value == "auto"

    def test_task_capability_type_values(self):
        """Test TaskCapabilityType enum values."""
        assert TaskCapabilityType.MULTI_AGENT.value == "multi_agent"
        assert TaskCapabilityType.HANDOFF.value == "handoff"
        assert TaskCapabilityType.FILE_OPERATIONS.value == "file_operations"
        assert TaskCapabilityType.CODE_EXECUTION.value == "code_execution"
        assert TaskCapabilityType.WEB_SEARCH.value == "web_search"
        assert TaskCapabilityType.TOOL_USE.value == "tool_use"
        assert TaskCapabilityType.CONVERSATION.value == "conversation"
        assert TaskCapabilityType.PLANNING.value == "planning"


class TestFrameworkMapping:
    """Tests for framework mapping helpers."""

    def test_map_framework_claude_sdk(self):
        """Test mapping Claude SDK framework."""
        from src.api.v1.claude_sdk.hybrid_routes import _map_framework
        from src.integrations.claude_sdk.hybrid.types import Framework

        result = _map_framework(FrameworkType.CLAUDE_SDK)
        assert result == Framework.CLAUDE_SDK

    def test_map_framework_microsoft_agent(self):
        """Test mapping Microsoft Agent framework."""
        from src.api.v1.claude_sdk.hybrid_routes import _map_framework
        from src.integrations.claude_sdk.hybrid.types import Framework

        result = _map_framework(FrameworkType.MICROSOFT_AGENT)
        assert result == Framework.MICROSOFT_AGENT_FRAMEWORK

    def test_map_framework_auto(self):
        """Test mapping auto framework returns None."""
        from src.api.v1.claude_sdk.hybrid_routes import _map_framework

        result = _map_framework(FrameworkType.AUTO)
        assert result is None

    def test_map_framework_to_api_claude_sdk(self):
        """Test mapping internal framework to API type."""
        from src.api.v1.claude_sdk.hybrid_routes import _map_framework_to_api
        from src.integrations.claude_sdk.hybrid.types import Framework

        result = _map_framework_to_api(Framework.CLAUDE_SDK)
        assert result == FrameworkType.CLAUDE_SDK

    def test_map_framework_to_api_microsoft_agent(self):
        """Test mapping internal MS Agent to API type."""
        from src.api.v1.claude_sdk.hybrid_routes import _map_framework_to_api
        from src.integrations.claude_sdk.hybrid.types import Framework

        result = _map_framework_to_api(Framework.MICROSOFT_AGENT_FRAMEWORK)
        assert result == FrameworkType.MICROSOFT_AGENT

    def test_map_framework_to_api_none(self):
        """Test mapping None returns AUTO."""
        from src.api.v1.claude_sdk.hybrid_routes import _map_framework_to_api

        result = _map_framework_to_api(None)
        assert result == FrameworkType.AUTO
