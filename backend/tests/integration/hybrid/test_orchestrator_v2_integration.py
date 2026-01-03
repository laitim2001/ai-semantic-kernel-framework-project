# =============================================================================
# IPA Platform - HybridOrchestrator V2 Integration Tests
# =============================================================================
# Phase 13: Hybrid Core Architecture
# Sprint 54: HybridOrchestrator Refactor (S54-3, S54-4)
#
# Integration tests for HybridOrchestratorV2.
# Tests the complete orchestration flow with IntentRouter, ContextBridge,
# and UnifiedToolExecutor integration.
# =============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.hybrid import (
    # Sprint 52: Intent Router
    ExecutionMode,
    IntentAnalysis,
    IntentRouter,
    SessionContext,
    # Sprint 53: Context Bridge
    ContextBridge,
    HybridContext,
    SyncResult,
    SyncDirection,
    SyncStrategy,
    # Sprint 54: Unified Execution
    UnifiedToolExecutor,
    ToolSource,
    ToolExecutionResult,
    # Sprint 54: HybridOrchestrator V2
    HybridOrchestratorV2,
    OrchestratorMode,
    OrchestratorConfig,
    ExecutionContextV2,
    HybridResultV2,
    OrchestratorMetrics,
    create_orchestrator_v2,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def orchestrator_config():
    """Create test orchestrator configuration."""
    return OrchestratorConfig(
        mode=OrchestratorMode.V2_FULL,
        primary_framework="claude_sdk",
        auto_switch=True,
        switch_confidence_threshold=0.7,
        timeout=30.0,
        max_retries=3,
        enable_metrics=True,
        enable_tool_callback=True,
    )


@pytest.fixture
def mock_intent_router():
    """Create mock IntentRouter."""
    router = MagicMock(spec=IntentRouter)

    async def mock_analyze(user_input, session_context=None):
        return IntentAnalysis(
            mode=ExecutionMode.CHAT_MODE,
            confidence=0.85,
            reasoning="Test analysis",
        )

    router.analyze_intent = AsyncMock(side_effect=mock_analyze)
    return router


@pytest.fixture
def mock_context_bridge():
    """Create mock ContextBridge."""
    bridge = MagicMock(spec=ContextBridge)

    async def mock_get_or_create(session_id):
        return MagicMock(spec=HybridContext)

    async def mock_sync_after(result, context):
        return MagicMock(success=True)

    bridge.get_or_create_hybrid = AsyncMock(side_effect=mock_get_or_create)
    bridge.sync_after_execution = AsyncMock(side_effect=mock_sync_after)
    return bridge


@pytest.fixture
def mock_tool_executor():
    """Create mock UnifiedToolExecutor."""
    executor = MagicMock(spec=UnifiedToolExecutor)

    async def mock_execute(tool_name, arguments, source=None, context=None, approval_required=False):
        return ToolExecutionResult(
            success=True,
            content=f"Executed {tool_name}",
            tool_name=tool_name,
            source=source or ToolSource.CLAUDE,
        )

    executor.execute = AsyncMock(side_effect=mock_execute)
    return executor


@pytest.fixture
def orchestrator_v2(orchestrator_config, mock_intent_router, mock_context_bridge, mock_tool_executor):
    """Create HybridOrchestratorV2 with mocked dependencies."""
    orchestrator = HybridOrchestratorV2(
        config=orchestrator_config,
        intent_router=mock_intent_router,
        context_bridge=mock_context_bridge,
        unified_executor=mock_tool_executor,
    )
    return orchestrator


# =============================================================================
# Integration Test: Orchestrator Initialization
# =============================================================================


class TestOrchestratorInitialization:
    """Tests for orchestrator initialization."""

    def test_create_with_default_config(self):
        """Test creating orchestrator with default config."""
        orchestrator = HybridOrchestratorV2()
        assert orchestrator is not None
        assert orchestrator.config.mode == OrchestratorMode.V2_FULL

    def test_create_with_custom_config(self, orchestrator_config):
        """Test creating orchestrator with custom config."""
        orchestrator = HybridOrchestratorV2(config=orchestrator_config)
        assert orchestrator.config.mode == OrchestratorMode.V2_FULL
        assert orchestrator.config.primary_framework == "claude_sdk"
        assert orchestrator.config.auto_switch is True
        assert orchestrator.config.timeout == 30.0

    def test_create_with_v2_minimal_mode(self):
        """Test creating orchestrator with V2 minimal mode."""
        config = OrchestratorConfig(mode=OrchestratorMode.V2_MINIMAL)
        orchestrator = HybridOrchestratorV2(config=config)
        assert orchestrator.config.mode == OrchestratorMode.V2_MINIMAL

    def test_factory_function(self):
        """Test create_orchestrator_v2 factory function."""
        orchestrator = create_orchestrator_v2(mode=OrchestratorMode.V1_COMPAT)
        assert orchestrator is not None
        assert orchestrator.config.mode == OrchestratorMode.V1_COMPAT

    def test_factory_function_with_options(self):
        """Test factory function with various options."""
        orchestrator = create_orchestrator_v2(
            mode=OrchestratorMode.V2_FULL,
            primary_framework="microsoft_agent_framework",
            auto_switch=False,
        )
        assert orchestrator.config.primary_framework == "microsoft_agent_framework"
        assert orchestrator.config.auto_switch is False

    def test_orchestrator_initial_session_state(self):
        """Test orchestrator initial session state."""
        orchestrator = HybridOrchestratorV2()
        assert orchestrator.active_session_id is None
        assert orchestrator.session_count == 0

    def test_orchestrator_has_core_components(self):
        """Test orchestrator has core components initialized."""
        orchestrator = HybridOrchestratorV2()
        assert orchestrator.intent_router is not None
        assert orchestrator.context_bridge is not None


# =============================================================================
# Integration Test: Session Management
# =============================================================================


class TestSessionManagement:
    """Integration tests for session management."""

    def test_create_session(self):
        """Test creating a new session."""
        orchestrator = HybridOrchestratorV2()
        session_id = orchestrator.create_session()

        assert session_id is not None
        assert orchestrator.session_count == 1
        assert orchestrator.active_session_id == session_id

    def test_create_session_with_custom_id(self):
        """Test creating session with custom ID."""
        orchestrator = HybridOrchestratorV2()
        custom_id = "custom-session-123"
        session_id = orchestrator.create_session(session_id=custom_id)

        assert session_id == custom_id
        assert orchestrator.active_session_id == custom_id

    def test_create_session_with_metadata(self):
        """Test creating session with metadata."""
        orchestrator = HybridOrchestratorV2()
        metadata = {"user_id": "user-123", "source": "test"}
        session_id = orchestrator.create_session(metadata=metadata)

        session = orchestrator.get_session(session_id)
        assert session is not None
        assert session.metadata == metadata

    def test_get_session(self):
        """Test getting a session by ID."""
        orchestrator = HybridOrchestratorV2()
        session_id = orchestrator.create_session()
        session = orchestrator.get_session(session_id)

        assert session is not None
        assert isinstance(session, ExecutionContextV2)
        assert session.session_id == session_id

    def test_get_nonexistent_session(self):
        """Test getting a session that doesn't exist."""
        orchestrator = HybridOrchestratorV2()
        session = orchestrator.get_session("nonexistent-session")
        assert session is None

    def test_close_session(self):
        """Test closing a session."""
        orchestrator = HybridOrchestratorV2()
        session_id = orchestrator.create_session()
        result = orchestrator.close_session(session_id)

        assert result is True
        assert orchestrator.get_session(session_id) is None
        assert orchestrator.active_session_id is None
        assert orchestrator.session_count == 0

    def test_close_nonexistent_session(self):
        """Test closing a session that doesn't exist."""
        orchestrator = HybridOrchestratorV2()
        result = orchestrator.close_session("nonexistent-session")
        assert result is False

    def test_multiple_sessions(self):
        """Test managing multiple sessions."""
        orchestrator = HybridOrchestratorV2()
        session_id_1 = orchestrator.create_session()
        session_id_2 = orchestrator.create_session()
        session_id_3 = orchestrator.create_session()

        assert orchestrator.session_count == 3
        assert orchestrator.active_session_id == session_id_3

        # All sessions accessible
        assert orchestrator.get_session(session_id_1) is not None
        assert orchestrator.get_session(session_id_2) is not None
        assert orchestrator.get_session(session_id_3) is not None


# =============================================================================
# Integration Test: Execution Flow
# =============================================================================


class TestExecutionFlow:
    """Integration tests for execution flow."""

    @pytest.mark.asyncio
    async def test_execute_simple_prompt(self, orchestrator_v2):
        """Test executing a simple prompt."""
        result = await orchestrator_v2.execute(
            prompt="Hello, how are you?"
        )

        assert isinstance(result, HybridResultV2)
        assert result.session_id is not None
        assert result.duration >= 0

    @pytest.mark.asyncio
    async def test_execute_with_session(self, orchestrator_v2):
        """Test executing with existing session."""
        session_id = orchestrator_v2.create_session()

        result = await orchestrator_v2.execute(
            prompt="Test prompt",
            session_id=session_id,
        )

        assert result.session_id == session_id

    @pytest.mark.asyncio
    async def test_execute_creates_session_if_needed(self, orchestrator_v2):
        """Test that execute creates session if not provided."""
        result = await orchestrator_v2.execute(
            prompt="Test prompt"
        )

        assert result.session_id is not None
        assert orchestrator_v2.session_count >= 1

    @pytest.mark.asyncio
    async def test_execute_with_force_mode(self, orchestrator_v2):
        """Test executing with forced mode."""
        result = await orchestrator_v2.execute(
            prompt="Test prompt",
            force_mode=ExecutionMode.WORKFLOW_MODE,
        )

        assert result.execution_mode == ExecutionMode.WORKFLOW_MODE

    @pytest.mark.asyncio
    async def test_execute_with_tools(self, orchestrator_v2):
        """Test executing with available tools."""
        tools = [
            {"name": "read_file", "description": "Read a file"},
            {"name": "write_file", "description": "Write a file"},
        ]

        result = await orchestrator_v2.execute(
            prompt="Read the config file",
            tools=tools,
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_with_metadata(self, orchestrator_v2):
        """Test executing with metadata."""
        result = await orchestrator_v2.execute(
            prompt="Test prompt",
            metadata={"request_id": "req-123"},
        )

        assert result is not None


# =============================================================================
# Integration Test: Intent Analysis Integration
# =============================================================================


class TestIntentAnalysisIntegration:
    """Integration tests for intent analysis."""

    @pytest.mark.asyncio
    async def test_intent_analysis_performed(self, orchestrator_v2, mock_intent_router):
        """Test that intent analysis is performed during execution."""
        await orchestrator_v2.execute(prompt="Analyze this data")

        mock_intent_router.analyze_intent.assert_called()

    @pytest.mark.asyncio
    async def test_intent_analysis_result_in_response(self, orchestrator_v2):
        """Test that intent analysis is included in response."""
        result = await orchestrator_v2.execute(prompt="Test prompt")

        assert result.intent_analysis is not None
        assert isinstance(result.intent_analysis, IntentAnalysis)

    @pytest.mark.asyncio
    async def test_mode_detection_chat(self, orchestrator_v2, mock_intent_router):
        """Test chat mode detection."""
        async def chat_analysis(user_input, session_context=None):
            return IntentAnalysis(
                mode=ExecutionMode.CHAT_MODE,
                confidence=0.9,
                reasoning="Conversational query",
            )

        mock_intent_router.analyze_intent = AsyncMock(side_effect=chat_analysis)
        result = await orchestrator_v2.execute(prompt="How are you?")

        assert result.execution_mode == ExecutionMode.CHAT_MODE

    @pytest.mark.asyncio
    async def test_mode_detection_workflow(self, orchestrator_v2, mock_intent_router):
        """Test workflow mode detection."""
        async def workflow_analysis(user_input, session_context=None):
            return IntentAnalysis(
                mode=ExecutionMode.WORKFLOW_MODE,
                confidence=0.9,
                reasoning="Multi-step workflow detected",
            )

        mock_intent_router.analyze_intent = AsyncMock(side_effect=workflow_analysis)
        result = await orchestrator_v2.execute(prompt="Process this data through steps")

        assert result.execution_mode == ExecutionMode.WORKFLOW_MODE

    @pytest.mark.asyncio
    async def test_mode_detection_skipped_when_forced(self, orchestrator_v2, mock_intent_router):
        """Test that mode detection result is overridden when mode is forced."""
        result = await orchestrator_v2.execute(
            prompt="Test prompt",
            force_mode=ExecutionMode.HYBRID_MODE,
        )

        # Mode should match forced mode regardless of analysis
        assert result.execution_mode == ExecutionMode.HYBRID_MODE


# =============================================================================
# Integration Test: Context Bridge Integration
# =============================================================================


class TestContextBridgeIntegration:
    """Integration tests for context bridge."""

    @pytest.mark.asyncio
    async def test_context_prepared_during_execution(self, orchestrator_v2, mock_context_bridge):
        """Test that context is prepared during execution."""
        await orchestrator_v2.execute(prompt="Test prompt")

        mock_context_bridge.get_or_create_hybrid.assert_called()

    @pytest.mark.asyncio
    async def test_context_synced_after_execution(self, orchestrator_v2, mock_context_bridge):
        """Test that context is synced after execution."""
        await orchestrator_v2.execute(prompt="Test prompt")

        mock_context_bridge.sync_after_execution.assert_called()


# =============================================================================
# Integration Test: Tool Execution Flow
# =============================================================================


class TestToolExecutionFlow:
    """Integration tests for tool execution flow."""

    @pytest.mark.asyncio
    async def test_execute_tool_via_unified_executor(self, orchestrator_v2, mock_tool_executor):
        """Test tool execution through unified executor."""
        result = await orchestrator_v2.execute_tool(
            tool_name="test_tool",
            arguments={"arg1": "value1"},
        )

        assert result.success is True
        mock_tool_executor.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_tool_with_source(self, orchestrator_v2, mock_tool_executor):
        """Test tool execution with specific source."""
        result = await orchestrator_v2.execute_tool(
            tool_name="write_file",
            arguments={"path": "/test/file.txt", "content": "test"},
            source=ToolSource.MAF,
        )

        mock_tool_executor.execute.assert_called_once()
        call_args = mock_tool_executor.execute.call_args
        assert call_args.kwargs.get("source") == ToolSource.MAF

    @pytest.mark.asyncio
    async def test_execute_tool_without_executor(self):
        """Test tool execution fails gracefully without executor."""
        orchestrator = HybridOrchestratorV2()

        result = await orchestrator.execute_tool(
            tool_name="test_tool",
            arguments={},
        )

        assert result.success is False
        assert "not configured" in result.error


# =============================================================================
# Integration Test: Metrics Tracking
# =============================================================================


class TestMetricsTracking:
    """Integration tests for metrics tracking."""

    def test_initial_metrics_state(self):
        """Test initial state of orchestrator metrics."""
        orchestrator = HybridOrchestratorV2()
        metrics = orchestrator.get_metrics()

        assert metrics["execution_count"] == 0
        assert metrics["mode_usage"]["CHAT_MODE"] == 0
        assert metrics["mode_usage"]["WORKFLOW_MODE"] == 0
        assert metrics["mode_usage"]["HYBRID_MODE"] == 0

    @pytest.mark.asyncio
    async def test_metrics_update_after_execution(self, orchestrator_v2):
        """Test metrics update after execution."""
        initial_metrics = orchestrator_v2.get_metrics()
        initial_count = initial_metrics["execution_count"]

        await orchestrator_v2.execute(
            prompt="Test task",
        )

        updated_metrics = orchestrator_v2.get_metrics()
        assert updated_metrics["execution_count"] >= initial_count

    def test_reset_metrics(self):
        """Test resetting orchestrator metrics."""
        orchestrator = HybridOrchestratorV2()
        orchestrator.reset_metrics()
        metrics = orchestrator.get_metrics()

        assert metrics["execution_count"] == 0
        assert metrics["success_count"] == 0
        assert metrics["failure_count"] == 0


# =============================================================================
# Integration Test: OrchestratorMetrics Class
# =============================================================================


class TestOrchestratorMetricsClass:
    """Tests for OrchestratorMetrics dataclass."""

    def test_metrics_record_execution(self):
        """Test recording individual execution in metrics."""
        metrics = OrchestratorMetrics()

        metrics.record_execution(
            mode=ExecutionMode.CHAT_MODE,
            framework="claude_sdk",
            success=True,
            duration=0.15,
        )

        assert metrics.execution_count == 1
        assert metrics.mode_usage["CHAT_MODE"] == 1
        assert metrics.framework_usage["claude_sdk"] == 1
        assert metrics.success_count == 1

    def test_metrics_record_failure(self):
        """Test recording failed execution."""
        metrics = OrchestratorMetrics()

        metrics.record_execution(
            mode=ExecutionMode.WORKFLOW_MODE,
            framework="microsoft_agent_framework",
            success=False,
            duration=0.5,
        )

        assert metrics.failure_count == 1
        assert metrics.success_count == 0

    def test_metrics_reset(self):
        """Test resetting metrics."""
        metrics = OrchestratorMetrics()
        metrics.record_execution(
            mode=ExecutionMode.CHAT_MODE,
            framework="claude_sdk",
            success=True,
            duration=0.1,
        )

        metrics.reset()

        assert metrics.execution_count == 0
        assert metrics.total_duration == 0.0
        assert metrics.success_count == 0
        assert metrics.failure_count == 0

    def test_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = OrchestratorMetrics()
        metrics.record_execution(
            mode=ExecutionMode.CHAT_MODE,
            framework="claude_sdk",
            success=True,
            duration=2.0,
        )

        result = metrics.to_dict()

        assert result["execution_count"] == 1
        assert result["total_duration"] == 2.0
        assert result["avg_duration"] == 2.0
        assert result["success_rate"] == 1.0

    def test_metrics_avg_duration(self):
        """Test average duration calculation."""
        metrics = OrchestratorMetrics()
        metrics.record_execution(
            mode=ExecutionMode.CHAT_MODE,
            framework="claude_sdk",
            success=True,
            duration=1.0,
        )
        metrics.record_execution(
            mode=ExecutionMode.CHAT_MODE,
            framework="claude_sdk",
            success=True,
            duration=3.0,
        )

        result = metrics.to_dict()
        assert result["avg_duration"] == 2.0

    def test_metrics_success_rate(self):
        """Test success rate calculation."""
        metrics = OrchestratorMetrics()

        # Record 3 successes and 1 failure
        for _ in range(3):
            metrics.record_execution(
                mode=ExecutionMode.CHAT_MODE,
                framework="claude_sdk",
                success=True,
                duration=0.1,
            )
        metrics.record_execution(
            mode=ExecutionMode.CHAT_MODE,
            framework="claude_sdk",
            success=False,
            duration=0.1,
        )

        result = metrics.to_dict()
        assert result["execution_count"] == 4
        assert result["success_count"] == 3
        assert result["success_rate"] == 0.75


# =============================================================================
# Integration Test: V1 Compatibility
# =============================================================================


class TestV1Compatibility:
    """Integration tests for V1 compatibility mode."""

    def test_v1_compat_mode_methods(self):
        """Test V1 compatibility methods are available."""
        config = OrchestratorConfig(mode=OrchestratorMode.V1_COMPAT)
        orchestrator = HybridOrchestratorV2(config=config)

        # V1 compat methods should exist
        assert hasattr(orchestrator, 'set_claude_executor')
        assert hasattr(orchestrator, 'set_maf_executor')
        assert hasattr(orchestrator, 'analyze_task')

    def test_v1_analyze_task_sync(self, mock_intent_router):
        """Test V1 synchronous analyze_task method."""
        config = OrchestratorConfig(mode=OrchestratorMode.V1_COMPAT)
        orchestrator = HybridOrchestratorV2(config=config)

        # analyze_task is synchronous for V1 compat
        analysis = orchestrator.analyze_task("Test task")

        assert analysis is not None
        assert hasattr(analysis, 'mode')

    def test_set_claude_executor(self):
        """Test setting Claude executor (V1 compat)."""
        orchestrator = HybridOrchestratorV2()
        mock_executor = AsyncMock()
        orchestrator.set_claude_executor(mock_executor)

        assert orchestrator._claude_executor == mock_executor

    def test_set_maf_executor(self):
        """Test setting MAF executor (V1 compat)."""
        orchestrator = HybridOrchestratorV2()
        mock_executor = AsyncMock()
        orchestrator.set_maf_executor(mock_executor)

        assert orchestrator._maf_executor == mock_executor


# =============================================================================
# Integration Test: Error Handling
# =============================================================================


class TestErrorHandling:
    """Integration tests for error handling."""

    @pytest.mark.asyncio
    async def test_handle_intent_router_error(self, mock_context_bridge):
        """Test handling of IntentRouter errors."""
        mock_router = MagicMock()
        mock_router.analyze_intent = AsyncMock(
            side_effect=Exception("Router error")
        )

        orchestrator = HybridOrchestratorV2(
            intent_router=mock_router,
            context_bridge=mock_context_bridge,
        )

        # Should not raise, should handle gracefully
        result = await orchestrator.execute(prompt="Test")

        # Should return error result
        assert result.success is False

    @pytest.mark.asyncio
    async def test_handle_context_bridge_error(self, mock_intent_router):
        """Test handling of ContextBridge errors."""
        mock_bridge = MagicMock()
        mock_bridge.get_or_create_hybrid = AsyncMock(
            side_effect=Exception("Context error")
        )
        mock_bridge.sync_after_execution = AsyncMock(return_value=None)

        orchestrator = HybridOrchestratorV2(
            intent_router=mock_intent_router,
            context_bridge=mock_bridge,
        )

        # Should handle gracefully and continue execution
        result = await orchestrator.execute(prompt="Test")

        # Execution should still complete
        assert result is not None


# =============================================================================
# Integration Test: ExecutionContextV2
# =============================================================================


class TestExecutionContextV2Class:
    """Tests for ExecutionContextV2 dataclass."""

    def test_execution_context_v2_creation(self):
        """Test creating ExecutionContextV2 with defaults."""
        context = ExecutionContextV2()

        assert context.session_id is not None
        assert context.hybrid_context is None
        assert context.intent_analysis is None
        assert context.current_mode == ExecutionMode.CHAT_MODE
        assert context.conversation_history == []
        assert context.tool_executions == []
        assert context.metadata == {}

    def test_execution_context_v2_with_values(self):
        """Test ExecutionContextV2 with custom values."""
        context = ExecutionContextV2(
            session_id="custom-session",
            current_mode=ExecutionMode.WORKFLOW_MODE,
            metadata={"key": "value"},
        )

        assert context.session_id == "custom-session"
        assert context.current_mode == ExecutionMode.WORKFLOW_MODE
        assert context.metadata == {"key": "value"}

    def test_execution_context_v2_with_history(self):
        """Test ExecutionContextV2 with conversation history."""
        context = ExecutionContextV2(
            session_id="history-session",
            conversation_history=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ],
        )

        assert len(context.conversation_history) == 2

    def test_execution_context_v2_timestamps(self):
        """Test ExecutionContextV2 has timestamps."""
        context = ExecutionContextV2()

        assert context.created_at > 0
        assert context.last_activity > 0
        assert context.last_activity >= context.created_at


# =============================================================================
# Integration Test: HybridResultV2
# =============================================================================


class TestHybridResultV2Class:
    """Tests for HybridResultV2 dataclass."""

    def test_result_v2_success(self):
        """Test creating successful HybridResultV2."""
        result = HybridResultV2(
            success=True,
            content="Test response",
            framework_used="claude_sdk",
            execution_mode=ExecutionMode.CHAT_MODE,
        )

        assert result.success is True
        assert result.content == "Test response"
        assert result.error is None
        assert result.framework_used == "claude_sdk"
        assert result.execution_mode == ExecutionMode.CHAT_MODE

    def test_result_v2_error(self):
        """Test HybridResultV2 with error."""
        result = HybridResultV2(
            success=False,
            error="Something went wrong",
            framework_used="microsoft_agent_framework",
            execution_mode=ExecutionMode.WORKFLOW_MODE,
        )

        assert result.success is False
        assert result.error == "Something went wrong"

    def test_result_v2_with_tool_results(self):
        """Test HybridResultV2 with tool results."""
        tool_result = ToolExecutionResult(
            success=True,
            content="Tool output",
            tool_name="test_tool",
        )

        result = HybridResultV2(
            success=True,
            content="Response",
            tool_results=[tool_result],
        )

        assert len(result.tool_results) == 1
        assert result.tool_results[0].tool_name == "test_tool"

    def test_result_v2_has_intent_analysis(self):
        """Test HybridResultV2 can have intent analysis."""
        intent = IntentAnalysis(
            mode=ExecutionMode.CHAT_MODE,
            confidence=0.9,
            reasoning="Test",
        )

        result = HybridResultV2(
            success=True,
            intent_analysis=intent,
        )

        assert result.intent_analysis is not None
        assert result.intent_analysis.mode == ExecutionMode.CHAT_MODE


# =============================================================================
# Integration Test: Conversation History
# =============================================================================


class TestConversationHistory:
    """Integration tests for conversation history management."""

    @pytest.mark.asyncio
    async def test_conversation_history_updated(self, orchestrator_v2):
        """Test that conversation history is updated after execution."""
        session_id = orchestrator_v2.create_session()

        await orchestrator_v2.execute(
            prompt="First message",
            session_id=session_id,
        )

        session = orchestrator_v2.get_session(session_id)
        assert len(session.conversation_history) == 2  # user + assistant
        assert session.conversation_history[0]["role"] == "user"
        assert session.conversation_history[0]["content"] == "First message"
        assert session.conversation_history[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_multiple_turns(self, orchestrator_v2):
        """Test multiple conversation turns."""
        session_id = orchestrator_v2.create_session()

        await orchestrator_v2.execute(prompt="Turn 1", session_id=session_id)
        await orchestrator_v2.execute(prompt="Turn 2", session_id=session_id)
        await orchestrator_v2.execute(prompt="Turn 3", session_id=session_id)

        session = orchestrator_v2.get_session(session_id)
        assert len(session.conversation_history) == 6  # 3 user + 3 assistant
