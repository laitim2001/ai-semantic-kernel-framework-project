# =============================================================================
# IPA Platform - OrchestratorMediator Tests
# =============================================================================
# Sprint 132: Tests for Mediator Pattern core — event dispatch, handler
#   registration, session management, pipeline execution.
# =============================================================================

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.hybrid.intent import ExecutionMode, IntentAnalysis
from src.integrations.hybrid.orchestrator.contracts import (
    Handler,
    HandlerResult,
    HandlerType,
    OrchestratorRequest,
    OrchestratorResponse,
)
from src.integrations.hybrid.orchestrator.events import EventType, OrchestratorEvent
from src.integrations.hybrid.orchestrator.mediator import OrchestratorMediator
from src.integrations.hybrid.orchestrator.handlers.routing import RoutingHandler
from src.integrations.hybrid.orchestrator.handlers.dialog import DialogHandler
from src.integrations.hybrid.orchestrator.handlers.approval import ApprovalHandler
from src.integrations.hybrid.orchestrator.handlers.execution import ExecutionHandler
from src.integrations.hybrid.orchestrator.handlers.context import ContextHandler
from src.integrations.hybrid.orchestrator.handlers.observability import (
    ObservabilityHandler,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_framework_selector():
    """Create mock framework selector."""
    selector = MagicMock()
    selector.analyze_intent = AsyncMock(
        return_value=IntentAnalysis(
            mode=ExecutionMode.CHAT_MODE,
            confidence=0.9,
            reasoning="Conversational intent",
            analysis_time_ms=5.0,
        )
    )
    selector.select_framework = AsyncMock(
        return_value=IntentAnalysis(
            mode=ExecutionMode.CHAT_MODE,
            confidence=0.85,
            reasoning="Chat mode selected",
            analysis_time_ms=8.0,
        )
    )
    return selector


@pytest.fixture
def mock_context_bridge():
    """Create mock context bridge."""
    bridge = MagicMock()
    bridge.get_or_create_hybrid = AsyncMock(return_value=MagicMock())
    bridge.sync_after_execution = AsyncMock(return_value=MagicMock(success=True))
    return bridge


@pytest.fixture
def mock_claude_executor():
    """Create mock Claude executor."""
    return AsyncMock(return_value={"success": True, "content": "Claude response"})


@pytest.fixture
def basic_mediator(mock_framework_selector, mock_context_bridge, mock_claude_executor):
    """Create a mediator with basic handlers."""
    routing = RoutingHandler(framework_selector=mock_framework_selector)
    execution = ExecutionHandler(claude_executor=mock_claude_executor)
    context_h = ContextHandler(context_bridge=mock_context_bridge)
    observability = ObservabilityHandler()

    return OrchestratorMediator(
        routing_handler=routing,
        execution_handler=execution,
        context_handler=context_h,
        observability_handler=observability,
    )


@pytest.fixture
def empty_mediator():
    """Create mediator with no handlers."""
    return OrchestratorMediator()


# =============================================================================
# Test: Mediator Initialization
# =============================================================================


class TestMediatorInit:
    """Tests for OrchestratorMediator initialization."""

    def test_init_empty(self, empty_mediator):
        """Mediator can be created with no handlers."""
        assert empty_mediator.registered_handlers == []
        assert empty_mediator.session_count == 0

    def test_init_with_handlers(self, basic_mediator):
        """Mediator registers handlers correctly."""
        handlers = basic_mediator.registered_handlers
        assert HandlerType.ROUTING in handlers
        assert HandlerType.EXECUTION in handlers
        assert HandlerType.CONTEXT in handlers
        assert HandlerType.OBSERVABILITY in handlers

    def test_register_handler(self, empty_mediator):
        """Handler can be registered after construction."""
        handler = MagicMock(spec=Handler)
        handler.handler_type = HandlerType.ROUTING
        empty_mediator.register_handler(handler)
        assert HandlerType.ROUTING in empty_mediator.registered_handlers

    def test_get_handler(self, basic_mediator):
        """Get registered handler by type."""
        routing = basic_mediator.get_handler(HandlerType.ROUTING)
        assert routing is not None
        assert isinstance(routing, RoutingHandler)

    def test_get_handler_not_registered(self, empty_mediator):
        """Get unregistered handler returns None."""
        assert empty_mediator.get_handler(HandlerType.ROUTING) is None


# =============================================================================
# Test: Session Management
# =============================================================================


class TestMediatorSessions:
    """Tests for session management."""

    def test_create_session(self, empty_mediator):
        """Create a new session."""
        sid = empty_mediator.create_session()
        assert empty_mediator.session_count == 1
        session = empty_mediator.get_session(sid)
        assert session is not None
        assert session["session_id"] == sid

    def test_create_session_custom_id(self, empty_mediator):
        """Create session with custom ID."""
        sid = empty_mediator.create_session(session_id="custom-123")
        assert sid == "custom-123"
        assert empty_mediator.get_session("custom-123") is not None

    def test_create_session_with_metadata(self, empty_mediator):
        """Create session with metadata."""
        sid = empty_mediator.create_session(metadata={"key": "value"})
        session = empty_mediator.get_session(sid)
        assert session["metadata"] == {"key": "value"}

    def test_close_session(self, empty_mediator):
        """Close a session removes it."""
        sid = empty_mediator.create_session()
        assert empty_mediator.close_session(sid) is True
        assert empty_mediator.session_count == 0
        assert empty_mediator.get_session(sid) is None

    def test_close_nonexistent_session(self, empty_mediator):
        """Close nonexistent session returns False."""
        assert empty_mediator.close_session("nonexistent") is False

    def test_multiple_sessions(self, empty_mediator):
        """Multiple sessions can coexist."""
        s1 = empty_mediator.create_session()
        s2 = empty_mediator.create_session()
        assert empty_mediator.session_count == 2
        empty_mediator.close_session(s1)
        assert empty_mediator.session_count == 1


# =============================================================================
# Test: Pipeline Execution
# =============================================================================


class TestMediatorPipeline:
    """Tests for pipeline execution."""

    @pytest.mark.asyncio
    async def test_execute_basic(self, basic_mediator):
        """Basic execution with routing + execution handlers."""
        request = OrchestratorRequest(content="Hello, help me")
        response = await basic_mediator.execute(request)

        assert response.success is True
        assert response.content != ""
        assert response.session_id is not None
        assert response.duration > 0

    @pytest.mark.asyncio
    async def test_execute_creates_session(self, basic_mediator):
        """Execution creates session if none provided."""
        request = OrchestratorRequest(content="Test")
        response = await basic_mediator.execute(request)

        assert response.session_id is not None
        assert basic_mediator.session_count == 1

    @pytest.mark.asyncio
    async def test_execute_reuses_session(self, basic_mediator):
        """Execution reuses existing session."""
        sid = basic_mediator.create_session(session_id="reuse-123")
        request = OrchestratorRequest(content="Test", session_id="reuse-123")
        response = await basic_mediator.execute(request)

        assert response.session_id == "reuse-123"
        assert basic_mediator.session_count == 1

    @pytest.mark.asyncio
    async def test_execute_force_mode(self, basic_mediator):
        """Forced execution mode is respected."""
        request = OrchestratorRequest(
            content="Run workflow",
            force_mode=ExecutionMode.WORKFLOW_MODE,
        )
        response = await basic_mediator.execute(request)
        assert response.success is True

    @pytest.mark.asyncio
    async def test_execute_with_metadata(self, basic_mediator):
        """Metadata is passed through pipeline."""
        request = OrchestratorRequest(
            content="Test",
            metadata={"custom_key": "custom_value"},
        )
        response = await basic_mediator.execute(request)
        assert response.success is True

    @pytest.mark.asyncio
    async def test_execute_empty_mediator(self, empty_mediator):
        """Execution with no handlers returns error."""
        request = OrchestratorRequest(content="Test")
        response = await empty_mediator.execute(request)
        # Without execution handler, result should indicate failure
        assert response.success is False

    @pytest.mark.asyncio
    async def test_execute_handler_results_tracked(self, basic_mediator):
        """Handler results are tracked in response."""
        request = OrchestratorRequest(content="Test")
        response = await basic_mediator.execute(request)
        assert "routing" in response.handler_results
        assert "execution" in response.handler_results

    @pytest.mark.asyncio
    async def test_execute_updates_conversation_history(self, basic_mediator):
        """Execution updates session conversation history."""
        sid = basic_mediator.create_session(session_id="hist-123")
        request = OrchestratorRequest(content="First message", session_id="hist-123")
        await basic_mediator.execute(request)

        session = basic_mediator.get_session("hist-123")
        history = session["conversation_history"]
        assert len(history) == 2  # user + assistant
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "First message"
        assert history[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_execute_pipeline_error(self, basic_mediator):
        """Pipeline error is handled gracefully."""
        # Force routing handler to raise
        routing = basic_mediator.get_handler(HandlerType.ROUTING)
        routing._framework_selector.analyze_intent = AsyncMock(
            side_effect=Exception("Routing failed")
        )

        request = OrchestratorRequest(content="Test")
        response = await basic_mediator.execute(request)
        assert response.success is False
        assert "Routing failed" in (response.error or "")


# =============================================================================
# Test: Metrics Delegation
# =============================================================================


class TestMediatorMetrics:
    """Tests for metrics delegation."""

    def test_get_metrics(self, basic_mediator):
        """Get metrics from observability handler."""
        metrics = basic_mediator.get_metrics()
        assert isinstance(metrics, dict)
        assert "execution_count" in metrics

    def test_reset_metrics(self, basic_mediator):
        """Reset metrics via mediator."""
        basic_mediator.reset_metrics()
        metrics = basic_mediator.get_metrics()
        assert metrics["execution_count"] == 0

    def test_get_metrics_no_handler(self, empty_mediator):
        """Get metrics without handler returns empty dict."""
        assert empty_mediator.get_metrics() == {}


# =============================================================================
# Test: OrchestratorRequest / OrchestratorResponse
# =============================================================================


class TestContracts:
    """Tests for contract data classes."""

    def test_request_defaults(self):
        """OrchestratorRequest has sensible defaults."""
        req = OrchestratorRequest(content="Test")
        assert req.content == "Test"
        assert req.requester == "system"
        assert req.force_mode is None
        assert req.request_id is not None
        assert req.timestamp > 0

    def test_request_full(self):
        """OrchestratorRequest with all fields."""
        req = OrchestratorRequest(
            content="Test",
            session_id="s1",
            requester="user1",
            force_mode=ExecutionMode.WORKFLOW_MODE,
            tools=[{"name": "tool1"}],
            max_tokens=1000,
            timeout=30.0,
            metadata={"key": "val"},
        )
        assert req.session_id == "s1"
        assert req.requester == "user1"
        assert req.force_mode == ExecutionMode.WORKFLOW_MODE

    def test_response_defaults(self):
        """OrchestratorResponse has sensible defaults."""
        resp = OrchestratorResponse(success=True)
        assert resp.success is True
        assert resp.content == ""
        assert resp.error is None
        assert resp.duration == 0.0

    def test_handler_result(self):
        """HandlerResult construction."""
        result = HandlerResult(
            success=True,
            handler_type=HandlerType.ROUTING,
            data={"key": "value"},
        )
        assert result.success is True
        assert result.handler_type == HandlerType.ROUTING
        assert result.should_short_circuit is False


# =============================================================================
# Test: Events
# =============================================================================


class TestEvents:
    """Tests for event types."""

    def test_event_type_values(self):
        """EventType enum has expected values."""
        assert EventType.ROUTING_STARTED == "routing.started"
        assert EventType.PIPELINE_COMPLETED == "pipeline.completed"

    def test_orchestrator_event(self):
        """OrchestratorEvent construction."""
        event = OrchestratorEvent(event_type=EventType.ROUTING_STARTED)
        assert event.event_type == EventType.ROUTING_STARTED
        assert event.event_id is not None
        assert event.timestamp > 0

    def test_handler_type_enum(self):
        """HandlerType enum values."""
        assert HandlerType.ROUTING == "routing"
        assert HandlerType.DIALOG == "dialog"
        assert HandlerType.APPROVAL == "approval"
        assert HandlerType.EXECUTION == "execution"
        assert HandlerType.CONTEXT == "context"
        assert HandlerType.OBSERVABILITY == "observability"
