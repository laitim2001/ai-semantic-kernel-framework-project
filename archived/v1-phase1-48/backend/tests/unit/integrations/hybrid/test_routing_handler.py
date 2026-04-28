# =============================================================================
# IPA Platform - RoutingHandler Tests
# =============================================================================
# Sprint 132: Tests for routing handler — direct routing and Phase 28 flow.
# =============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.integrations.hybrid.intent import ExecutionMode, IntentAnalysis
from src.integrations.hybrid.orchestrator.contracts import (
    HandlerResult,
    HandlerType,
    OrchestratorRequest,
)
from src.integrations.hybrid.orchestrator.handlers.routing import RoutingHandler


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_selector():
    """Create mock framework selector."""
    selector = MagicMock()
    selector.analyze_intent = AsyncMock(
        return_value=IntentAnalysis(
            mode=ExecutionMode.CHAT_MODE,
            confidence=0.9,
            reasoning="Chat intent",
            analysis_time_ms=5.0,
        )
    )
    selector.select_framework = AsyncMock(
        return_value=IntentAnalysis(
            mode=ExecutionMode.WORKFLOW_MODE,
            confidence=0.85,
            reasoning="Workflow selected",
            analysis_time_ms=8.0,
        )
    )
    return selector


@pytest.fixture
def mock_input_gateway():
    """Create mock input gateway."""
    gateway = MagicMock()
    routing_decision = MagicMock()
    routing_decision.completeness.is_sufficient = True
    routing_decision.to_dict = MagicMock(return_value={"intent": "incident"})
    gateway.process = AsyncMock(return_value=routing_decision)
    return gateway


@pytest.fixture
def mock_swarm_handler():
    """Create mock swarm handler."""
    handler = MagicMock()
    handler.is_enabled = False
    decomposition = MagicMock()
    decomposition.should_use_swarm = False
    handler.analyze_for_swarm = MagicMock(return_value=decomposition)
    return handler


@pytest.fixture
def routing_handler(mock_selector):
    """Create RoutingHandler with direct routing only."""
    return RoutingHandler(framework_selector=mock_selector)


@pytest.fixture
def phase28_routing_handler(mock_selector, mock_input_gateway, mock_swarm_handler):
    """Create RoutingHandler with Phase 28 components."""
    return RoutingHandler(
        input_gateway=mock_input_gateway,
        framework_selector=mock_selector,
        swarm_handler=mock_swarm_handler,
    )


# =============================================================================
# Test: Handler Properties
# =============================================================================


class TestRoutingHandlerProperties:
    """Tests for handler properties."""

    def test_handler_type(self, routing_handler):
        """Handler type is ROUTING."""
        assert routing_handler.handler_type == HandlerType.ROUTING

    def test_can_handle_default(self, routing_handler):
        """Handler can always handle by default."""
        request = OrchestratorRequest(content="Test")
        assert routing_handler.can_handle(request, {}) is True


# =============================================================================
# Test: Direct Routing
# =============================================================================


class TestDirectRouting:
    """Tests for direct routing flow (no InputGateway)."""

    @pytest.mark.asyncio
    async def test_direct_routing_chat(self, routing_handler, mock_selector):
        """Direct routing returns chat mode."""
        request = OrchestratorRequest(content="Hello, help me")
        context = {}
        result = await routing_handler.handle(request, context)

        assert result.success is True
        assert result.handler_type == HandlerType.ROUTING
        assert context["intent_analysis"].mode == ExecutionMode.CHAT_MODE

    @pytest.mark.asyncio
    async def test_direct_routing_force_mode(self, routing_handler):
        """Forced mode bypasses analysis."""
        request = OrchestratorRequest(
            content="Run workflow",
            force_mode=ExecutionMode.WORKFLOW_MODE,
        )
        context = {}
        result = await routing_handler.handle(request, context)

        assert result.success is True
        intent = context["intent_analysis"]
        assert intent.mode == ExecutionMode.WORKFLOW_MODE
        assert intent.confidence == 1.0

    @pytest.mark.asyncio
    async def test_direct_routing_with_session_context(self, routing_handler):
        """Routing uses conversation history from context."""
        request = OrchestratorRequest(content="Follow up")
        context = {
            "conversation_history": [{"role": "user", "content": "Hi"}],
            "current_mode": ExecutionMode.WORKFLOW_MODE,
        }
        result = await routing_handler.handle(request, context)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_direct_routing_error(self, routing_handler, mock_selector):
        """Routing error is caught gracefully."""
        mock_selector.analyze_intent = AsyncMock(
            side_effect=Exception("Analysis failed")
        )
        request = OrchestratorRequest(content="Test")
        result = await routing_handler.handle(request, {})

        assert result.success is False
        assert "Analysis failed" in result.error


# =============================================================================
# Test: Phase 28 Routing
# =============================================================================


class TestPhase28Routing:
    """Tests for Phase 28 routing flow (InputGateway)."""

    @pytest.mark.asyncio
    async def test_phase28_routing_sufficient(
        self, phase28_routing_handler, mock_input_gateway
    ):
        """Phase 28 routing with sufficient completeness."""
        source_request = MagicMock()
        source_request.content = "ETL pipeline failed"
        request = OrchestratorRequest(
            content="ETL pipeline failed",
            source_request=source_request,
        )
        context = {}
        result = await phase28_routing_handler.handle(request, context)

        assert result.success is True
        assert context["routing_decision"] is not None
        assert context["needs_dialog"] is False

    @pytest.mark.asyncio
    async def test_phase28_routing_insufficient(
        self, phase28_routing_handler, mock_input_gateway
    ):
        """Phase 28 routing with insufficient completeness."""
        routing_decision = MagicMock()
        routing_decision.completeness.is_sufficient = False
        mock_input_gateway.process = AsyncMock(return_value=routing_decision)

        source_request = MagicMock()
        source_request.content = "Something broken"
        request = OrchestratorRequest(
            content="Something broken",
            source_request=source_request,
        )
        context = {}
        result = await phase28_routing_handler.handle(request, context)

        assert result.success is True
        assert context["needs_dialog"] is True

    @pytest.mark.asyncio
    async def test_phase28_routing_swarm_eligible(
        self, phase28_routing_handler, mock_swarm_handler
    ):
        """Phase 28 routing detects swarm eligibility."""
        mock_swarm_handler.is_enabled = True
        decomposition = MagicMock()
        decomposition.should_use_swarm = True
        decomposition.subtasks = [MagicMock(), MagicMock()]
        mock_swarm_handler.analyze_for_swarm = MagicMock(return_value=decomposition)

        source_request = MagicMock()
        source_request.content = "Complex multi-step task"
        request = OrchestratorRequest(
            content="Complex multi-step task",
            source_request=source_request,
        )
        context = {}
        result = await phase28_routing_handler.handle(request, context)

        assert result.success is True
        assert result.data.get("needs_swarm") is True
        assert context.get("swarm_decomposition") is not None

    @pytest.mark.asyncio
    async def test_phase28_routing_calls_select_framework(
        self, phase28_routing_handler, mock_selector
    ):
        """Phase 28 routing calls select_framework."""
        source_request = MagicMock()
        source_request.content = "Test"
        request = OrchestratorRequest(
            content="Test",
            source_request=source_request,
        )
        await phase28_routing_handler.handle(request, {})
        mock_selector.select_framework.assert_called_once()
