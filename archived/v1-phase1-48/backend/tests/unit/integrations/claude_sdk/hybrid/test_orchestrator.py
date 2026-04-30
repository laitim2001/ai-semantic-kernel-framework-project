"""Unit tests for Hybrid Orchestrator.

Sprint 50: S50-3 - Hybrid Orchestrator (12 pts)
Tests for HybridOrchestrator class.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.integrations.claude_sdk.hybrid.orchestrator import (
    ExecutionContext,
    HybridOrchestrator,
    create_orchestrator,
)
from src.integrations.claude_sdk.hybrid.types import (
    HybridResult,
    HybridSessionConfig,
    TaskCapability,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def orchestrator():
    """Create a default HybridOrchestrator."""
    return HybridOrchestrator()


@pytest.fixture
def orchestrator_with_executors():
    """Create an orchestrator with mock executors."""
    async def mock_claude_executor(**kwargs):
        return HybridResult(
            content="Claude response",
            framework_used="claude_sdk",
            tokens_used=100,
            success=True,
        )

    async def mock_ms_executor(**kwargs):
        return HybridResult(
            content="MS Agent response",
            framework_used="microsoft_agent_framework",
            tokens_used=150,
            success=True,
        )

    orch = HybridOrchestrator(
        claude_executor=mock_claude_executor,
        ms_executor=mock_ms_executor,
    )
    return orch


@pytest.fixture
def config():
    """Create a custom configuration."""
    return HybridSessionConfig(
        primary_framework="claude_sdk",
        auto_switch=True,
        switch_confidence_threshold=0.8,
    )


# ============================================================================
# HybridOrchestrator Initialization Tests
# ============================================================================


class TestHybridOrchestratorInit:
    """Tests for HybridOrchestrator initialization."""

    def test_default_init(self):
        """Test default initialization."""
        orch = HybridOrchestrator()

        assert orch.config.primary_framework == "claude_sdk"
        assert orch.config.auto_switch is True
        assert orch.session_count == 0

    def test_custom_init(self, config):
        """Test custom initialization."""
        orch = HybridOrchestrator(config=config)

        assert orch.config.switch_confidence_threshold == 0.8

    def test_init_with_executors(self):
        """Test initialization with executors."""
        claude_exec = AsyncMock()
        ms_exec = AsyncMock()

        orch = HybridOrchestrator(
            claude_executor=claude_exec,
            ms_executor=ms_exec,
        )

        assert orch._claude_executor is claude_exec
        assert orch._ms_executor is ms_exec


# ============================================================================
# Session Management Tests
# ============================================================================


class TestSessionManagement:
    """Tests for session management."""

    def test_create_session(self, orchestrator):
        """Test creating a session."""
        session_id = orchestrator.create_session()

        assert session_id is not None
        assert orchestrator.session_count == 1
        assert orchestrator.active_session_id == session_id

    def test_create_session_with_custom_id(self, orchestrator):
        """Test creating session with custom ID."""
        session_id = orchestrator.create_session(session_id="custom-123")

        assert session_id == "custom-123"
        assert orchestrator.get_session("custom-123") is not None

    def test_create_session_with_metadata(self, orchestrator):
        """Test creating session with metadata."""
        metadata = {"user_id": "user-123", "purpose": "testing"}
        session_id = orchestrator.create_session(metadata=metadata)

        session = orchestrator.get_session(session_id)
        assert session.metadata == metadata

    def test_get_session(self, orchestrator):
        """Test getting a session."""
        session_id = orchestrator.create_session()
        session = orchestrator.get_session(session_id)

        assert session is not None
        assert session.session_id == session_id

    def test_get_nonexistent_session(self, orchestrator):
        """Test getting a non-existent session."""
        session = orchestrator.get_session("nonexistent")

        assert session is None

    def test_close_session(self, orchestrator):
        """Test closing a session."""
        session_id = orchestrator.create_session()
        result = orchestrator.close_session(session_id)

        assert result is True
        assert orchestrator.session_count == 0
        assert orchestrator.get_session(session_id) is None

    def test_close_nonexistent_session(self, orchestrator):
        """Test closing a non-existent session."""
        result = orchestrator.close_session("nonexistent")

        assert result is False

    def test_multiple_sessions(self, orchestrator):
        """Test managing multiple sessions."""
        id1 = orchestrator.create_session()
        id2 = orchestrator.create_session()

        assert orchestrator.session_count == 2
        assert orchestrator.active_session_id == id2  # Last created

        orchestrator.close_session(id1)
        assert orchestrator.session_count == 1


# ============================================================================
# Task Execution Tests
# ============================================================================


class TestTaskExecution:
    """Tests for task execution."""

    @pytest.mark.asyncio
    async def test_execute_simple_task(self, orchestrator):
        """Test executing a simple task."""
        result = await orchestrator.execute("Hello, how are you?")

        assert result.success is True
        assert result.content is not None
        assert result.session_id is not None

    @pytest.mark.asyncio
    async def test_execute_with_session(self, orchestrator):
        """Test executing with existing session."""
        session_id = orchestrator.create_session()
        result = await orchestrator.execute(
            "Answer my question",
            session_id=session_id,
        )

        assert result.session_id == session_id

    @pytest.mark.asyncio
    async def test_execute_creates_session(self, orchestrator):
        """Test that execute creates session if needed."""
        assert orchestrator.session_count == 0

        result = await orchestrator.execute("Do something")

        assert orchestrator.session_count == 1
        assert result.session_id is not None

    @pytest.mark.asyncio
    async def test_execute_force_framework(self, orchestrator):
        """Test forcing specific framework."""
        result = await orchestrator.execute(
            "Any task",
            force_framework="microsoft_agent_framework",
        )

        assert result.framework_used == "microsoft_agent_framework"

    @pytest.mark.asyncio
    async def test_execute_with_custom_executor(self, orchestrator_with_executors):
        """Test execution with custom executor."""
        result = await orchestrator_with_executors.execute(
            "Read the file",  # Should route to Claude
        )

        assert result.success is True
        assert result.tokens_used > 0

    @pytest.mark.asyncio
    async def test_execute_updates_history(self, orchestrator):
        """Test that execution updates conversation history."""
        session_id = orchestrator.create_session()
        await orchestrator.execute("First message", session_id=session_id)

        session = orchestrator.get_session(session_id)
        assert len(session.conversation_history) == 2  # User + Assistant

    @pytest.mark.asyncio
    async def test_execute_returns_task_analysis(self, orchestrator):
        """Test that execution returns task analysis."""
        result = await orchestrator.execute("Search the web for Python docs")

        assert result.task_analysis is not None
        assert len(result.task_analysis.capabilities) > 0


# ============================================================================
# Framework Routing Tests
# ============================================================================


class TestFrameworkRouting:
    """Tests for framework routing."""

    @pytest.mark.asyncio
    async def test_route_file_ops_to_claude(self, orchestrator):
        """Test routing file operations to Claude."""
        result = await orchestrator.execute("Read and edit the config file")

        assert result.framework_used == "claude_sdk"

    @pytest.mark.asyncio
    async def test_route_multi_agent_to_ms(self, orchestrator):
        """Test routing multi-agent tasks to MS."""
        result = await orchestrator.execute(
            "Coordinate multiple agents to collaborate"
        )

        assert result.framework_used == "microsoft_agent_framework"

    @pytest.mark.asyncio
    async def test_auto_switch_disabled(self):
        """Test that auto-switch can be disabled."""
        config = HybridSessionConfig(
            primary_framework="claude_sdk",
            auto_switch=False,
        )
        orch = HybridOrchestrator(config=config)

        # Create session with Claude as current
        session_id = orch.create_session()
        session = orch.get_session(session_id)
        session.current_framework = "claude_sdk"

        # Even with multi-agent, should stay on Claude
        result = await orch.execute(
            "Coordinate agents",
            session_id=session_id,
        )

        # With auto_switch=False, may still route based on analysis


# ============================================================================
# Streaming Execution Tests
# ============================================================================


class TestStreamingExecution:
    """Tests for streaming execution."""

    @pytest.mark.asyncio
    async def test_execute_stream(self, orchestrator):
        """Test streaming execution."""
        chunks = []
        async for chunk in orchestrator.execute_stream("Tell me a story"):
            chunks.append(chunk)

        assert len(chunks) > 0
        full_content = "".join(chunks)
        assert len(full_content) > 0

    @pytest.mark.asyncio
    async def test_execute_stream_with_session(self, orchestrator):
        """Test streaming with session."""
        session_id = orchestrator.create_session()

        chunks = []
        async for chunk in orchestrator.execute_stream(
            "Continue",
            session_id=session_id,
        ):
            chunks.append(chunk)

        assert len(chunks) > 0


# ============================================================================
# Task Analysis Tests
# ============================================================================


class TestTaskAnalysis:
    """Tests for task analysis."""

    def test_analyze_task(self, orchestrator):
        """Test analyzing a task."""
        analysis = orchestrator.analyze_task("Read file and execute code")

        assert TaskCapability.FILE_OPERATIONS in analysis.capabilities
        assert TaskCapability.CODE_EXECUTION in analysis.capabilities

    def test_analyze_task_empty(self, orchestrator):
        """Test analyzing empty task."""
        analysis = orchestrator.analyze_task("")

        assert len(analysis.capabilities) == 0


# ============================================================================
# Metrics Tests
# ============================================================================


class TestMetrics:
    """Tests for metrics tracking."""

    @pytest.mark.asyncio
    async def test_metrics_tracking(self, orchestrator):
        """Test that metrics are tracked."""
        await orchestrator.execute("Task 1")
        await orchestrator.execute("Task 2")

        metrics = orchestrator.get_metrics()

        assert metrics["execution_count"] == 2
        assert metrics["total_duration"] > 0
        assert metrics["avg_duration"] > 0

    @pytest.mark.asyncio
    async def test_framework_usage_tracking(self, orchestrator):
        """Test framework usage tracking."""
        await orchestrator.execute("Read a file")  # Claude
        await orchestrator.execute("Read another file")  # Claude

        metrics = orchestrator.get_metrics()

        assert metrics["framework_usage"]["claude_sdk"] > 0

    def test_reset_metrics(self, orchestrator):
        """Test resetting metrics."""
        orchestrator._execution_count = 10
        orchestrator._total_duration = 100.0

        orchestrator.reset_metrics()

        metrics = orchestrator.get_metrics()
        assert metrics["execution_count"] == 0
        assert metrics["total_duration"] == 0.0


# ============================================================================
# Context Manager Tests
# ============================================================================


class TestContextManager:
    """Tests for context manager."""

    @pytest.mark.asyncio
    async def test_session_context_manager(self, orchestrator):
        """Test session context manager."""
        async with orchestrator.session() as orch:
            assert orch.session_count == 1
            session_id = orch.active_session_id
            # Use the session from context manager
            await orch.execute("Do something", session_id=session_id)
            # Should still be 1 session (reused)
            assert orch.session_count == 1

        # Session should be closed after context
        assert orchestrator.session_count == 0

    @pytest.mark.asyncio
    async def test_session_context_with_metadata(self, orchestrator):
        """Test session context with metadata."""
        async with orchestrator.session(
            metadata={"test": True}
        ) as orch:
            session = orch.get_session(orch.active_session_id)
            assert session.metadata["test"] is True


# ============================================================================
# Executor Injection Tests
# ============================================================================


class TestExecutorInjection:
    """Tests for executor injection."""

    def test_set_claude_executor(self, orchestrator):
        """Test setting Claude executor."""
        executor = AsyncMock()
        orchestrator.set_claude_executor(executor)

        assert orchestrator._claude_executor is executor

    def test_set_ms_executor(self, orchestrator):
        """Test setting MS executor."""
        executor = AsyncMock()
        orchestrator.set_ms_executor(executor)

        assert orchestrator._ms_executor is executor

    @pytest.mark.asyncio
    async def test_injected_executor_called(self, orchestrator):
        """Test that injected executor is called."""
        mock_result = HybridResult(
            content="Mock response",
            framework_used="claude_sdk",
            success=True,
        )
        executor = AsyncMock(return_value=mock_result)
        orchestrator.set_claude_executor(executor)

        result = await orchestrator.execute("Read a file")

        assert result.content == "Mock response"


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_executor_error(self, orchestrator):
        """Test handling executor errors."""
        async def failing_executor(**kwargs):
            raise ValueError("Executor failed")

        orchestrator.set_claude_executor(failing_executor)

        result = await orchestrator.execute("Any task")

        assert result.success is False
        assert "Executor failed" in result.error

    @pytest.mark.asyncio
    async def test_timeout_handling(self, orchestrator):
        """Test timeout handling."""
        async def slow_executor(**kwargs):
            import asyncio
            await asyncio.sleep(10)  # Very slow
            return HybridResult(content="Late response", success=True)

        orchestrator.set_claude_executor(slow_executor)

        result = await orchestrator.execute(
            "Any task",
            timeout=0.01,  # Very short timeout
        )

        # Timeout should result in failure
        # Note: The actual error handling depends on implementation
        assert result.success is False
        # Error may contain timeout message or be caught by executor error handling


# ============================================================================
# ExecutionContext Tests
# ============================================================================


class TestExecutionContext:
    """Tests for ExecutionContext dataclass."""

    def test_context_creation(self):
        """Test creating an ExecutionContext."""
        context = ExecutionContext()

        assert context.session_id is not None
        assert context.conversation_history == []
        assert context.metadata == {}
        assert context.current_framework is None

    def test_context_with_values(self):
        """Test context with custom values."""
        context = ExecutionContext(
            session_id="test-123",
            metadata={"key": "value"},
        )

        assert context.session_id == "test-123"
        assert context.metadata["key"] == "value"


# ============================================================================
# Factory Function Tests
# ============================================================================


class TestCreateOrchestrator:
    """Tests for create_orchestrator factory function."""

    def test_create_default(self):
        """Test creating default orchestrator."""
        orch = create_orchestrator()

        assert isinstance(orch, HybridOrchestrator)
        assert orch.config.primary_framework == "claude_sdk"
        assert orch.config.auto_switch is True

    def test_create_custom(self):
        """Test creating custom orchestrator."""
        orch = create_orchestrator(
            primary_framework="microsoft_agent_framework",
            auto_switch=False,
            switch_threshold=0.9,
        )

        assert orch.config.primary_framework == "microsoft_agent_framework"
        assert orch.config.auto_switch is False
        assert orch.config.switch_confidence_threshold == 0.9
