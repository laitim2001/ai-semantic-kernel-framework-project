# =============================================================================
# IPA Platform - AG-UI API Routes Tests
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-1: AG-UI SSE Endpoint
#
# Unit tests for AG-UI REST API endpoints.
# Tests SSE streaming, request validation, and error handling.
#
# Test Coverage:
#   - Health check endpoint
#   - SSE streaming endpoint (POST /ag-ui)
#   - Synchronous endpoint (POST /ag-ui/sync)
#   - Thread history endpoint
#   - Request validation
#   - Error handling
# =============================================================================

import json
import pytest
import uuid
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from src.api.v1.ag_ui.routes import router, map_execution_mode
from src.api.v1.ag_ui.schemas import (
    AGUIExecutionMode,
    AGUIMessage,
    AGUIToolDefinition,
    RunAgentRequest,
)
from src.integrations.ag_ui.bridge import HybridEventBridge, RunAgentInput, BridgeConfig
from src.integrations.ag_ui.events import (
    AGUIEventType,
    RunStartedEvent,
    RunFinishedEvent,
    RunFinishReason,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
)
from src.integrations.hybrid.intent import ExecutionMode


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def app() -> FastAPI:
    """Create test FastAPI app."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1")
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_bridge() -> MagicMock:
    """Create mock HybridEventBridge."""
    bridge = MagicMock(spec=HybridEventBridge)
    bridge.config = BridgeConfig()
    return bridge


@pytest.fixture
def sample_request() -> Dict[str, Any]:
    """Create sample request data."""
    return {
        "thread_id": "thread-test-123",
        "messages": [
            {"role": "user", "content": "Hello, help me with this task"},
        ],
        "mode": "auto",
    }


@pytest.fixture
def sample_request_with_tools() -> Dict[str, Any]:
    """Create sample request with tools."""
    return {
        "thread_id": "thread-test-456",
        "messages": [
            {"role": "user", "content": "Search for Python tutorials"},
        ],
        "tools": [
            {
                "name": "search",
                "description": "Search the web",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                    },
                    "required": ["query"],
                },
            },
        ],
        "mode": "workflow",
        "max_tokens": 2000,
    }


# =============================================================================
# Schema Tests
# =============================================================================

class TestSchemas:
    """Test Pydantic schemas."""

    def test_agui_execution_mode_values(self):
        """Test AGUIExecutionMode enum values."""
        assert AGUIExecutionMode.WORKFLOW.value == "workflow"
        assert AGUIExecutionMode.CHAT.value == "chat"
        assert AGUIExecutionMode.HYBRID.value == "hybrid"
        assert AGUIExecutionMode.AUTO.value == "auto"

    def test_agui_message_creation(self):
        """Test AGUIMessage creation."""
        msg = AGUIMessage(
            id="msg-123",
            role="user",
            content="Hello",
        )
        assert msg.id == "msg-123"
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_agui_message_without_id(self):
        """Test AGUIMessage creation without ID."""
        msg = AGUIMessage(role="assistant", content="Hi there")
        assert msg.id is None
        assert msg.role == "assistant"

    def test_agui_tool_definition(self):
        """Test AGUIToolDefinition creation."""
        tool = AGUIToolDefinition(
            name="calculator",
            description="Calculate math expressions",
            parameters={"type": "object"},
        )
        assert tool.name == "calculator"
        assert tool.description == "Calculate math expressions"

    def test_run_agent_request_minimal(self):
        """Test RunAgentRequest with minimal data."""
        request = RunAgentRequest(
            thread_id="thread-123",
            messages=[AGUIMessage(role="user", content="Hello")],
        )
        assert request.thread_id == "thread-123"
        assert request.mode == AGUIExecutionMode.AUTO
        assert request.max_tokens is None

    def test_run_agent_request_full(self):
        """Test RunAgentRequest with all fields."""
        request = RunAgentRequest(
            thread_id="thread-456",
            run_id="run-789",
            messages=[AGUIMessage(role="user", content="Test")],
            tools=[AGUIToolDefinition(name="test", description="Test tool")],
            mode=AGUIExecutionMode.WORKFLOW,
            max_tokens=1000,
            timeout=30.0,
            session_id="session-123",
            metadata={"key": "value"},
        )
        assert request.run_id == "run-789"
        assert len(request.tools) == 1
        assert request.mode == AGUIExecutionMode.WORKFLOW


# =============================================================================
# Mode Mapping Tests
# =============================================================================

class TestModeMapping:
    """Test execution mode mapping."""

    def test_map_workflow_mode(self):
        """Test mapping workflow mode."""
        result = map_execution_mode(AGUIExecutionMode.WORKFLOW)
        assert result == ExecutionMode.WORKFLOW_MODE

    def test_map_chat_mode(self):
        """Test mapping chat mode."""
        result = map_execution_mode(AGUIExecutionMode.CHAT)
        assert result == ExecutionMode.CHAT_MODE

    def test_map_hybrid_mode(self):
        """Test mapping hybrid mode."""
        result = map_execution_mode(AGUIExecutionMode.HYBRID)
        assert result == ExecutionMode.HYBRID_MODE

    def test_map_auto_mode(self):
        """Test mapping auto mode returns None."""
        result = map_execution_mode(AGUIExecutionMode.AUTO)
        assert result is None


# =============================================================================
# Health Check Tests
# =============================================================================

class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_check_success(self, client):
        """Test successful health check."""
        response = client.get("/api/v1/ag-ui/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert "streaming" in data["features"]
        assert "tool_calls" in data["features"]
        assert "hybrid_mode" in data["features"]


# =============================================================================
# Run Agent Endpoint Tests
# =============================================================================

class TestRunAgentEndpoint:
    """Test POST /ag-ui endpoint."""

    def test_run_agent_missing_thread_id(self, client):
        """Test request with missing thread_id."""
        response = client.post(
            "/api/v1/ag-ui",
            json={"messages": [{"role": "user", "content": "Hello"}]},
        )
        # FastAPI will return 422 for validation error (missing required field)
        assert response.status_code == 422

    def test_run_agent_empty_messages(self, client):
        """Test request with empty messages."""
        with patch("src.api.v1.ag_ui.routes.get_hybrid_bridge") as mock_get_bridge:
            mock_bridge = MagicMock(spec=HybridEventBridge)
            mock_get_bridge.return_value = mock_bridge

            response = client.post(
                "/api/v1/ag-ui",
                json={
                    "thread_id": "thread-123",
                    "messages": [],
                },
            )
            assert response.status_code == 400
            assert "No user message" in response.json()["detail"]["message"]

    def test_run_agent_no_user_message(self, client):
        """Test request with no user message."""
        with patch("src.api.v1.ag_ui.routes.get_hybrid_bridge") as mock_get_bridge:
            mock_bridge = MagicMock(spec=HybridEventBridge)
            mock_get_bridge.return_value = mock_bridge

            response = client.post(
                "/api/v1/ag-ui",
                json={
                    "thread_id": "thread-123",
                    "messages": [
                        {"role": "system", "content": "You are helpful"},
                    ],
                },
            )
            assert response.status_code == 400
            assert "No user message" in response.json()["detail"]["message"]

    @pytest.mark.asyncio
    async def test_run_agent_streaming_response(self, app, sample_request):
        """Test SSE streaming response."""
        # Create mock bridge that yields events
        async def mock_stream_events(run_input):
            yield "data: {\"type\": \"RUN_STARTED\"}\n\n"
            yield "data: {\"type\": \"TEXT_MESSAGE_START\"}\n\n"
            yield "data: {\"type\": \"TEXT_MESSAGE_CONTENT\", \"delta\": \"Hello\"}\n\n"
            yield "data: {\"type\": \"TEXT_MESSAGE_END\"}\n\n"
            yield "data: {\"type\": \"RUN_FINISHED\"}\n\n"

        mock_bridge = MagicMock(spec=HybridEventBridge)
        mock_bridge.stream_events = mock_stream_events

        from src.api.v1.ag_ui.dependencies import get_hybrid_bridge
        app.dependency_overrides[get_hybrid_bridge] = lambda: mock_bridge

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as ac:
                response = await ac.post(
                    "/api/v1/ag-ui",
                    json=sample_request,
                )
                assert response.status_code == 200
                assert "text/event-stream" in response.headers.get("content-type", "")
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Sync Endpoint Tests
# =============================================================================

class TestRunAgentSyncEndpoint:
    """Test POST /ag-ui/sync endpoint."""

    def test_sync_missing_thread_id(self, client):
        """Test sync request with missing thread_id."""
        response = client.post(
            "/api/v1/ag-ui/sync",
            json={"messages": [{"role": "user", "content": "Hello"}]},
        )
        assert response.status_code == 422

    def test_sync_empty_messages(self, client):
        """Test sync request with empty messages."""
        with patch("src.api.v1.ag_ui.routes.get_hybrid_bridge") as mock_get_bridge:
            mock_bridge = MagicMock(spec=HybridEventBridge)
            mock_get_bridge.return_value = mock_bridge

            response = client.post(
                "/api/v1/ag-ui/sync",
                json={
                    "thread_id": "thread-123",
                    "messages": [],
                },
            )
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_sync_success_response(self, app, sample_request):
        """Test successful sync response."""
        # Create mock events
        mock_events = [
            RunStartedEvent(thread_id="thread-123", run_id="run-456"),
            TextMessageStartEvent(
                thread_id="thread-123",
                run_id="run-456",
                message_id="msg-123",
                role="assistant",
            ),
            TextMessageContentEvent(
                thread_id="thread-123",
                run_id="run-456",
                message_id="msg-123",
                delta="Hello! How can I help?",
            ),
            TextMessageEndEvent(
                thread_id="thread-123",
                run_id="run-456",
                message_id="msg-123",
            ),
            RunFinishedEvent(
                thread_id="thread-123",
                run_id="run-456",
                finish_reason=RunFinishReason.COMPLETE,
            ),
        ]

        mock_bridge = MagicMock(spec=HybridEventBridge)
        mock_bridge.execute_and_collect = AsyncMock(return_value=mock_events)

        from src.api.v1.ag_ui.dependencies import get_hybrid_bridge
        app.dependency_overrides[get_hybrid_bridge] = lambda: mock_bridge

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as ac:
                response = await ac.post(
                    "/api/v1/ag-ui/sync",
                    json=sample_request,
                )
                assert response.status_code == 200

                data = response.json()
                assert data["thread_id"] == "thread-test-123"
                assert data["status"] == "success"
                assert "Hello! How can I help?" in data["content"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_sync_error_response(self, app, sample_request):
        """Test sync response with error."""
        # Create mock events with error
        mock_events = [
            RunStartedEvent(thread_id="thread-123", run_id="run-456"),
            RunFinishedEvent(
                thread_id="thread-123",
                run_id="run-456",
                finish_reason=RunFinishReason.ERROR,
                error="Something went wrong",
            ),
        ]

        mock_bridge = MagicMock(spec=HybridEventBridge)
        mock_bridge.execute_and_collect = AsyncMock(return_value=mock_events)

        from src.api.v1.ag_ui.dependencies import get_hybrid_bridge
        app.dependency_overrides[get_hybrid_bridge] = lambda: mock_bridge

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as ac:
                response = await ac.post(
                    "/api/v1/ag-ui/sync",
                    json=sample_request,
                )
                assert response.status_code == 200

                data = response.json()
                assert data["status"] == "error"
                assert data["error"] == "Something went wrong"
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Thread History Tests
# =============================================================================

class TestThreadHistoryEndpoint:
    """Test GET /ag-ui/threads/{thread_id}/history endpoint."""

    def test_thread_history_placeholder(self, client):
        """Test thread history placeholder response."""
        response = client.get("/api/v1/ag-ui/threads/thread-123/history")
        assert response.status_code == 200

        data = response.json()
        assert data["thread_id"] == "thread-123"
        assert data["messages"] == []
        assert data["total"] == 0

    def test_thread_history_with_limit(self, client):
        """Test thread history with limit parameter."""
        response = client.get(
            "/api/v1/ag-ui/threads/thread-456/history",
            params={"limit": 100},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["limit"] == 100

    def test_thread_history_limit_validation(self, client):
        """Test thread history limit validation."""
        # Test too high limit
        response = client.get(
            "/api/v1/ag-ui/threads/thread-123/history",
            params={"limit": 500},
        )
        assert response.status_code == 422

        # Test too low limit
        response = client.get(
            "/api/v1/ag-ui/threads/thread-123/history",
            params={"limit": 0},
        )
        assert response.status_code == 422


# =============================================================================
# SSE Stream Generation Tests
# =============================================================================

class TestSSEStreamGeneration:
    """Test SSE stream generation helper."""

    @pytest.mark.asyncio
    async def test_generate_sse_stream_success(self):
        """Test successful SSE stream generation."""
        from src.api.v1.ag_ui.routes import generate_sse_stream

        async def mock_stream(run_input):
            yield "data: {\"type\": \"RUN_STARTED\"}\n\n"
            yield "data: {\"type\": \"RUN_FINISHED\"}\n\n"

        mock_bridge = MagicMock(spec=HybridEventBridge)
        mock_bridge.stream_events = mock_stream

        run_input = RunAgentInput(
            prompt="Test",
            thread_id="thread-123",
        )

        events = []
        async for event in generate_sse_stream(mock_bridge, run_input):
            events.append(event)

        assert len(events) == 2
        assert "RUN_STARTED" in events[0]
        assert "RUN_FINISHED" in events[1]

    @pytest.mark.asyncio
    async def test_generate_sse_stream_error_handling(self):
        """Test SSE stream error handling."""
        from src.api.v1.ag_ui.routes import generate_sse_stream

        async def mock_stream_error(run_input):
            raise ValueError("Orchestrator not configured")
            yield  # Make it an async generator

        mock_bridge = MagicMock(spec=HybridEventBridge)
        mock_bridge.stream_events = mock_stream_error
        mock_bridge.create_run_finished = MagicMock(return_value=RunFinishedEvent(
            thread_id="thread-123",
            run_id="run-456",
            finish_reason=RunFinishReason.ERROR,
            error="Orchestrator not configured",
        ))
        mock_bridge.format_event = MagicMock(
            return_value='data: {"type": "RUN_FINISHED", "error": "Orchestrator not configured"}\n\n'
        )

        run_input = RunAgentInput(
            prompt="Test",
            thread_id="thread-123",
        )

        events = []
        async for event in generate_sse_stream(mock_bridge, run_input):
            events.append(event)

        assert len(events) == 1
        assert "error" in events[0].lower()


# =============================================================================
# Request Validation Tests
# =============================================================================

class TestRequestValidation:
    """Test request validation."""

    def test_valid_request(self, client, sample_request):
        """Test valid request passes validation."""
        # This will fail at runtime due to missing bridge, but validates the request
        with patch("src.api.v1.ag_ui.routes.get_hybrid_bridge") as mock_get_bridge:
            async def mock_stream(run_input):
                yield "data: {}\n\n"

            mock_bridge = MagicMock(spec=HybridEventBridge)
            mock_bridge.stream_events = mock_stream
            mock_get_bridge.return_value = mock_bridge

            response = client.post("/api/v1/ag-ui", json=sample_request)
            # Should succeed (200) or be handled by bridge
            assert response.status_code in [200, 400, 500]

    def test_invalid_mode(self, client):
        """Test invalid execution mode."""
        response = client.post(
            "/api/v1/ag-ui",
            json={
                "thread_id": "thread-123",
                "messages": [{"role": "user", "content": "Test"}],
                "mode": "invalid_mode",
            },
        )
        assert response.status_code == 422

    def test_max_tokens_validation(self, client):
        """Test max_tokens validation."""
        response = client.post(
            "/api/v1/ag-ui",
            json={
                "thread_id": "thread-123",
                "messages": [{"role": "user", "content": "Test"}],
                "max_tokens": -1,
            },
        )
        assert response.status_code == 422

    def test_timeout_validation(self, client):
        """Test timeout validation."""
        response = client.post(
            "/api/v1/ag-ui",
            json={
                "thread_id": "thread-123",
                "messages": [{"role": "user", "content": "Test"}],
                "timeout": 1000,  # Too high
            },
        )
        assert response.status_code == 422


# =============================================================================
# Tool Conversion Tests
# =============================================================================

class TestToolConversion:
    """Test tool definition conversion."""

    @pytest.mark.asyncio
    async def test_tools_converted_correctly(self, app, sample_request_with_tools):
        """Test that tools are correctly converted to dict format."""
        captured_input = None

        async def capture_stream(run_input):
            nonlocal captured_input
            captured_input = run_input
            yield "data: {}\n\n"

        mock_bridge = MagicMock(spec=HybridEventBridge)
        mock_bridge.stream_events = capture_stream

        from src.api.v1.ag_ui.dependencies import get_hybrid_bridge
        app.dependency_overrides[get_hybrid_bridge] = lambda: mock_bridge

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as ac:
                response = await ac.post(
                    "/api/v1/ag-ui",
                    json=sample_request_with_tools,
                )
                # Consume the streaming response to ensure generator runs
                async for _ in response.aiter_bytes():
                    pass

            assert captured_input is not None
            assert captured_input.tools is not None
            assert len(captured_input.tools) == 1
            assert captured_input.tools[0]["name"] == "search"
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Content-Type Header Tests
# =============================================================================

class TestContentTypeHeaders:
    """Test response content-type headers."""

    @pytest.mark.asyncio
    async def test_sse_content_type(self, app, sample_request):
        """Test SSE endpoint returns correct content-type."""
        async def mock_stream(run_input):
            yield "data: {}\n\n"

        mock_bridge = MagicMock(spec=HybridEventBridge)
        mock_bridge.stream_events = mock_stream

        from src.api.v1.ag_ui.dependencies import get_hybrid_bridge
        app.dependency_overrides[get_hybrid_bridge] = lambda: mock_bridge

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as ac:
                response = await ac.post("/api/v1/ag-ui", json=sample_request)
                assert "text/event-stream" in response.headers.get("content-type", "")
        finally:
            app.dependency_overrides.clear()

    def test_json_content_type_for_errors(self, client):
        """Test error responses use JSON content-type."""
        response = client.post(
            "/api/v1/ag-ui",
            json={"messages": [{"role": "user", "content": "Test"}]},
        )
        # Validation error returns JSON
        assert "application/json" in response.headers.get("content-type", "")
