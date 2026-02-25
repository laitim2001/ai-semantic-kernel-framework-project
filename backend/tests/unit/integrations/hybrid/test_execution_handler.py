# =============================================================================
# IPA Platform - ExecutionHandler Tests
# =============================================================================
# Sprint 132: Tests for execution handler — MAF/Claude/Swarm dispatch.
# =============================================================================

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.integrations.hybrid.intent import ExecutionMode, IntentAnalysis
from src.integrations.hybrid.execution import ToolExecutionResult, ToolSource
from src.integrations.hybrid.orchestrator.contracts import (
    HandlerType,
    OrchestratorRequest,
)
from src.integrations.hybrid.orchestrator.handlers.execution import ExecutionHandler


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_claude_executor():
    """Create mock Claude executor."""
    return AsyncMock(
        return_value={
            "success": True,
            "content": "Claude response",
            "tokens_used": 100,
        }
    )


@pytest.fixture
def mock_maf_executor():
    """Create mock MAF executor."""
    return AsyncMock(
        return_value={
            "success": True,
            "content": "MAF response",
            "tokens_used": 50,
        }
    )


@pytest.fixture
def mock_swarm_handler():
    """Create mock swarm handler."""
    handler = MagicMock()
    swarm_result = MagicMock()
    swarm_result.success = True
    swarm_result.content = "Swarm result"
    swarm_result.error = None
    swarm_result.swarm_id = "swarm-123"
    swarm_result.worker_results = [{"id": "w1", "status": "done"}]
    handler.execute_swarm = AsyncMock(return_value=swarm_result)
    return handler


@pytest.fixture
def chat_handler(mock_claude_executor):
    """ExecutionHandler with Claude executor only."""
    return ExecutionHandler(claude_executor=mock_claude_executor)


@pytest.fixture
def workflow_handler(mock_maf_executor, mock_claude_executor):
    """ExecutionHandler with both executors."""
    return ExecutionHandler(
        claude_executor=mock_claude_executor,
        maf_executor=mock_maf_executor,
    )


@pytest.fixture
def swarm_execution_handler(mock_claude_executor, mock_swarm_handler):
    """ExecutionHandler with swarm handler."""
    return ExecutionHandler(
        claude_executor=mock_claude_executor,
        swarm_handler=mock_swarm_handler,
    )


@pytest.fixture
def no_executor_handler():
    """ExecutionHandler with no executors."""
    return ExecutionHandler()


# =============================================================================
# Test: Handler Properties
# =============================================================================


class TestExecutionHandlerProperties:
    """Tests for handler properties."""

    def test_handler_type(self, chat_handler):
        """Handler type is EXECUTION."""
        assert chat_handler.handler_type == HandlerType.EXECUTION


# =============================================================================
# Test: Chat Mode Execution
# =============================================================================


class TestChatModeExecution:
    """Tests for CHAT_MODE execution."""

    @pytest.mark.asyncio
    async def test_chat_mode_success(self, chat_handler, mock_claude_executor):
        """Chat mode executes via Claude."""
        request = OrchestratorRequest(content="Hello")
        context = {"execution_mode": ExecutionMode.CHAT_MODE}
        result = await chat_handler.handle(request, context)

        assert result.success is True
        assert result.data["framework_used"] == "claude_sdk"
        assert result.data["content"] == "Claude response"
        mock_claude_executor.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_mode_with_history(self, chat_handler, mock_claude_executor):
        """Chat mode passes conversation history."""
        request = OrchestratorRequest(content="Follow up")
        context = {
            "execution_mode": ExecutionMode.CHAT_MODE,
            "conversation_history": [{"role": "user", "content": "Hi"}],
        }
        await chat_handler.handle(request, context)
        call_kwargs = mock_claude_executor.call_args
        assert call_kwargs.kwargs.get("history") or call_kwargs[1].get("history")

    @pytest.mark.asyncio
    async def test_chat_mode_multimodal(self, chat_handler, mock_claude_executor):
        """Chat mode supports multimodal content."""
        request = OrchestratorRequest(content="Describe image")
        context = {
            "execution_mode": ExecutionMode.CHAT_MODE,
            "metadata": {"multimodal_content": [{"type": "image", "url": "test.png"}]},
        }
        await chat_handler.handle(request, context)
        call_kwargs = mock_claude_executor.call_args
        # multimodal_content should be passed through
        assert "multimodal_content" in str(call_kwargs)

    @pytest.mark.asyncio
    async def test_chat_mode_simulated(self, no_executor_handler):
        """Chat mode returns simulated response when no executor."""
        request = OrchestratorRequest(content="Test")
        context = {"execution_mode": ExecutionMode.CHAT_MODE}
        result = await no_executor_handler.handle(request, context)

        assert result.success is True
        assert "[CHAT_MODE]" in result.data["content"]


# =============================================================================
# Test: Workflow Mode Execution
# =============================================================================


class TestWorkflowModeExecution:
    """Tests for WORKFLOW_MODE execution."""

    @pytest.mark.asyncio
    async def test_workflow_mode_maf(self, workflow_handler, mock_maf_executor):
        """Workflow mode uses MAF executor."""
        request = OrchestratorRequest(content="Run workflow")
        context = {"execution_mode": ExecutionMode.WORKFLOW_MODE}
        result = await workflow_handler.handle(request, context)

        assert result.success is True
        assert result.data["framework_used"] == "microsoft_agent_framework"
        mock_maf_executor.assert_called_once()

    @pytest.mark.asyncio
    async def test_workflow_mode_claude_fallback(
        self, chat_handler, mock_claude_executor
    ):
        """Workflow mode falls back to Claude when MAF unavailable."""
        request = OrchestratorRequest(content="Run workflow")
        context = {"execution_mode": ExecutionMode.WORKFLOW_MODE}
        result = await chat_handler.handle(request, context)

        assert result.success is True
        assert result.data["framework_used"] == "claude_sdk"

    @pytest.mark.asyncio
    async def test_workflow_mode_simulated(self, no_executor_handler):
        """Workflow mode returns simulated response when no executor."""
        request = OrchestratorRequest(content="Test")
        context = {"execution_mode": ExecutionMode.WORKFLOW_MODE}
        result = await no_executor_handler.handle(request, context)

        assert result.success is True
        assert "[WORKFLOW_MODE]" in result.data["content"]


# =============================================================================
# Test: Hybrid Mode Execution
# =============================================================================


class TestHybridModeExecution:
    """Tests for HYBRID_MODE execution."""

    @pytest.mark.asyncio
    async def test_hybrid_mode_chat_default(self, chat_handler):
        """Hybrid mode defaults to chat when no MAF confidence."""
        request = OrchestratorRequest(content="Help me")
        context = {"execution_mode": ExecutionMode.HYBRID_MODE}
        result = await chat_handler.handle(request, context)

        assert result.success is True
        assert result.data["execution_mode"] == ExecutionMode.HYBRID_MODE

    @pytest.mark.asyncio
    async def test_hybrid_mode_maf_high_confidence(self, workflow_handler):
        """Hybrid mode uses MAF when MAF confidence is high."""
        intent = MagicMock()
        intent.suggested_framework = MagicMock()
        intent.suggested_framework.maf_confidence = 0.9

        request = OrchestratorRequest(content="Run complex task")
        context = {
            "execution_mode": ExecutionMode.HYBRID_MODE,
            "intent_analysis": intent,
        }
        result = await workflow_handler.handle(request, context)

        assert result.success is True
        assert result.data["execution_mode"] == ExecutionMode.HYBRID_MODE


# =============================================================================
# Test: Swarm Mode Execution
# =============================================================================


class TestSwarmModeExecution:
    """Tests for SWARM_MODE execution."""

    @pytest.mark.asyncio
    async def test_swarm_mode(self, swarm_execution_handler, mock_swarm_handler):
        """Swarm mode executes via swarm handler."""
        decomposition = MagicMock()
        decomposition.subtasks = [MagicMock(), MagicMock()]
        decomposition.swarm_mode = "parallel"

        request = OrchestratorRequest(content="Multi-agent task")
        context = {
            "swarm_decomposition": decomposition,
            "routing_decision": MagicMock(),
        }
        result = await swarm_execution_handler.handle(request, context)

        assert result.success is True
        assert result.data["framework_used"] == "swarm"
        assert result.data["execution_mode"] == ExecutionMode.SWARM_MODE
        mock_swarm_handler.execute_swarm.assert_called_once()


# =============================================================================
# Test: Error Handling
# =============================================================================


class TestExecutionErrors:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_executor_exception(self, chat_handler, mock_claude_executor):
        """Executor exception is caught."""
        mock_claude_executor.side_effect = Exception("API error")
        request = OrchestratorRequest(content="Test")
        context = {"execution_mode": ExecutionMode.CHAT_MODE}
        result = await chat_handler.handle(request, context)

        assert result.success is False
        assert "API error" in result.error

    @pytest.mark.asyncio
    async def test_timeout_error(self, chat_handler, mock_claude_executor):
        """Timeout error is caught."""
        mock_claude_executor.side_effect = asyncio.TimeoutError()
        request = OrchestratorRequest(content="Test", timeout=5.0)
        context = {"execution_mode": ExecutionMode.CHAT_MODE}
        result = await chat_handler.handle(request, context)

        assert result.success is False
        assert "timed out" in result.error


# =============================================================================
# Test: Tool Result Extraction
# =============================================================================


class TestToolResultExtraction:
    """Tests for _extract_tool_results."""

    def test_extract_dict_tool_calls(self):
        """Extract tool results from dict format."""
        raw = {
            "tool_calls": [
                {"name": "search", "id": "t1", "args": {"query": "test"}},
                {"name": "read", "id": "t2", "args": {"path": "/etc"}},
            ]
        }
        results = ExecutionHandler._extract_tool_results(raw, "claude_sdk")
        assert len(results) == 2
        assert results[0].tool_name == "search"
        assert results[0].source == ToolSource.CLAUDE
        assert results[1].tool_name == "read"

    def test_extract_object_tool_calls(self):
        """Extract tool results from object format."""
        tc = MagicMock()
        tc.name = "tool1"
        tc.id = "t1"
        tc.args = {}
        raw = {"tool_calls": [tc]}
        results = ExecutionHandler._extract_tool_results(raw, "microsoft_agent_framework")
        assert len(results) == 1
        assert results[0].source == ToolSource.MAF

    def test_extract_empty_tool_calls(self):
        """Extract returns empty list when no tool calls."""
        results = ExecutionHandler._extract_tool_results({}, "claude_sdk")
        assert results == []

    def test_extract_maf_source(self):
        """MAF framework uses MAF tool source."""
        raw = {"tool_calls": [{"name": "t", "id": "1", "args": {}}]}
        results = ExecutionHandler._extract_tool_results(
            raw, "microsoft_agent_framework"
        )
        assert results[0].source == ToolSource.MAF
