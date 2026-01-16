# =============================================================================
# IPA Platform - HybridOrchestrator V2 Tests
# =============================================================================
# Sprint 54: HybridOrchestrator Refactor
#
# Unit tests for HybridOrchestratorV2, the unified orchestration layer
# integrating IntentRouter, ContextBridge, and UnifiedToolExecutor.
# =============================================================================

import pytest
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List, Optional

from src.integrations.hybrid.orchestrator_v2 import (
    HybridOrchestratorV2,
    OrchestratorMode,
    OrchestratorConfig,
    ExecutionContextV2,
    HybridResultV2,
    OrchestratorMetrics,
    create_orchestrator_v2,
)
from src.integrations.hybrid.intent import ExecutionMode, IntentAnalysis
from src.integrations.hybrid.context import (
    HybridContext,
    SyncResult,
    SyncDirection,
    SyncStrategy,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_intent_router():
    """Create mock intent router."""
    router = MagicMock()
    router.analyze_intent = AsyncMock(
        return_value=IntentAnalysis(
            mode=ExecutionMode.CHAT_MODE,
            confidence=0.9,
            reasoning="User intent is conversational",
        )
    )
    return router


@pytest.fixture
def mock_context_bridge():
    """Create mock context bridge."""
    bridge = MagicMock()
    bridge.get_or_create_hybrid = AsyncMock(
        return_value=HybridContext(
            context_id="test-context-123",
            primary_framework="claude",
        )
    )
    bridge.sync_after_execution = AsyncMock(
        return_value=SyncResult(
            success=True,
            direction=SyncDirection.BIDIRECTIONAL,
            strategy=SyncStrategy.MERGE,
            source_version=1,
            target_version=1,
            changes_applied=0,
            conflicts=[],
        )
    )
    return bridge


@pytest.fixture
def mock_tool_executor():
    """Create mock unified tool executor."""
    executor = MagicMock()
    executor.execute = AsyncMock(
        return_value=MagicMock(
            success=True,
            output="tool executed",
            execution_time_ms=100,
        )
    )
    return executor


@pytest.fixture
def mock_claude_executor():
    """Create mock Claude executor."""
    async def executor(**kwargs):
        return {
            "success": True,
            "content": "Hello! How can I help you?",
            "tokens_used": 30,
        }
    return executor


@pytest.fixture
def mock_maf_executor():
    """Create mock MAF executor."""
    async def executor(**kwargs):
        return {
            "success": True,
            "content": "workflow completed",
        }
    return executor


@pytest.fixture
def basic_config():
    """Create basic orchestrator config."""
    return OrchestratorConfig(
        mode=OrchestratorMode.V2_FULL,
        primary_framework="claude_sdk",
        auto_switch=True,
        timeout=30.0,
    )


@pytest.fixture
def orchestrator(
    basic_config,
    mock_intent_router,
    mock_context_bridge,
    mock_tool_executor,
):
    """Create orchestrator with mocked dependencies."""
    return HybridOrchestratorV2(
        config=basic_config,
        intent_router=mock_intent_router,
        context_bridge=mock_context_bridge,
        unified_executor=mock_tool_executor,
    )


# =============================================================================
# OrchestratorConfig Tests
# =============================================================================


class TestOrchestratorConfig:
    """Tests for OrchestratorConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = OrchestratorConfig()

        assert config.mode == OrchestratorMode.V2_FULL
        assert config.primary_framework == "claude_sdk"
        assert config.auto_switch is True
        assert config.switch_confidence_threshold == 0.7
        assert config.timeout == 300.0
        assert config.max_retries == 3
        assert config.enable_metrics is True
        assert config.enable_tool_callback is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = OrchestratorConfig(
            mode=OrchestratorMode.V1_COMPAT,
            primary_framework="microsoft_agent_framework",
            auto_switch=False,
            timeout=120.0,
            max_retries=5,
        )

        assert config.mode == OrchestratorMode.V1_COMPAT
        assert config.primary_framework == "microsoft_agent_framework"
        assert config.auto_switch is False
        assert config.timeout == 120.0
        assert config.max_retries == 5

    def test_v2_minimal_mode(self):
        """Test V2_MINIMAL mode configuration."""
        config = OrchestratorConfig(
            mode=OrchestratorMode.V2_MINIMAL,
            enable_tool_callback=False,
        )

        assert config.mode == OrchestratorMode.V2_MINIMAL
        assert config.enable_tool_callback is False


# =============================================================================
# ExecutionContextV2 Tests
# =============================================================================


class TestExecutionContextV2:
    """Tests for ExecutionContextV2 dataclass."""

    def test_create_context_defaults(self):
        """Test context creation with defaults."""
        context = ExecutionContextV2()

        assert context.session_id is not None
        assert context.hybrid_context is None
        assert context.intent_analysis is None
        assert context.current_mode == ExecutionMode.CHAT_MODE
        assert context.conversation_history == []
        assert context.tool_executions == []
        assert context.created_at > 0
        assert context.last_activity > 0

    def test_context_with_session_id(self):
        """Test context creation with custom session ID."""
        context = ExecutionContextV2(session_id="custom-123")

        assert context.session_id == "custom-123"

    def test_context_with_metadata(self):
        """Test context with metadata."""
        metadata = {"user_id": "user-1", "tenant": "acme"}
        context = ExecutionContextV2(metadata=metadata)

        assert context.metadata == metadata
        assert context.metadata["user_id"] == "user-1"


# =============================================================================
# HybridResultV2 Tests
# =============================================================================


class TestHybridResultV2:
    """Tests for HybridResultV2 dataclass."""

    def test_success_result(self):
        """Test successful result."""
        result = HybridResultV2(
            success=True,
            content="Hello! I can help you with that.",
            framework_used="claude_sdk",
            execution_mode=ExecutionMode.CHAT_MODE,
            duration=0.15,
        )

        assert result.success is True
        assert "Hello" in result.content
        assert result.execution_mode == ExecutionMode.CHAT_MODE
        assert result.error is None
        assert result.framework_used == "claude_sdk"

    def test_error_result(self):
        """Test error result."""
        result = HybridResultV2(
            success=False,
            error="Workflow execution failed",
            framework_used="microsoft_agent_framework",
            execution_mode=ExecutionMode.WORKFLOW_MODE,
        )

        assert result.success is False
        assert result.content == ""
        assert result.error == "Workflow execution failed"

    def test_result_with_tokens(self):
        """Test result with token usage."""
        result = HybridResultV2(
            success=True,
            content="Found 10 results",
            framework_used="claude_sdk",
            execution_mode=ExecutionMode.CHAT_MODE,
            tokens_used=150,
        )

        assert result.tokens_used == 150


# =============================================================================
# OrchestratorMetrics Tests
# =============================================================================


class TestOrchestratorMetrics:
    """Tests for OrchestratorMetrics class."""

    def test_initial_metrics(self):
        """Test initial metrics values."""
        metrics = OrchestratorMetrics()

        assert metrics.execution_count == 0
        assert metrics.total_duration == 0.0
        assert metrics.success_count == 0
        assert metrics.failure_count == 0
        assert "CHAT_MODE" in metrics.mode_usage
        assert "WORKFLOW_MODE" in metrics.mode_usage

    def test_record_execution(self):
        """Test recording execution metrics."""
        metrics = OrchestratorMetrics()

        metrics.record_execution(
            mode=ExecutionMode.CHAT_MODE,
            framework="claude_sdk",
            success=True,
            duration=0.5,
        )

        assert metrics.execution_count == 1
        assert metrics.mode_usage["CHAT_MODE"] == 1
        assert metrics.framework_usage["claude_sdk"] == 1
        assert metrics.success_count == 1
        assert metrics.total_duration == 0.5

    def test_record_workflow_execution(self):
        """Test recording workflow execution."""
        metrics = OrchestratorMetrics()

        metrics.record_execution(
            mode=ExecutionMode.WORKFLOW_MODE,
            framework="microsoft_agent_framework",
            success=True,
            duration=1.0,
        )

        assert metrics.mode_usage["WORKFLOW_MODE"] == 1
        assert metrics.framework_usage["microsoft_agent_framework"] == 1

    def test_record_error(self):
        """Test recording error metrics."""
        metrics = OrchestratorMetrics()

        metrics.record_execution(
            mode=ExecutionMode.CHAT_MODE,
            framework="claude_sdk",
            success=False,
            duration=0.1,
        )

        assert metrics.execution_count == 1
        assert metrics.failure_count == 1
        assert metrics.success_count == 0

    def test_reset(self):
        """Test resetting metrics."""
        metrics = OrchestratorMetrics()
        metrics.record_execution(ExecutionMode.CHAT_MODE, "claude_sdk", True, 1.0)

        metrics.reset()

        assert metrics.execution_count == 0
        assert metrics.success_count == 0

    def test_to_dict(self):
        """Test metrics to dictionary conversion."""
        metrics = OrchestratorMetrics()
        metrics.record_execution(ExecutionMode.CHAT_MODE, "claude_sdk", True, 1.0)

        data = metrics.to_dict()

        assert data["execution_count"] == 1
        assert data["success_count"] == 1
        assert "avg_duration" in data
        assert "success_rate" in data
        assert data["success_rate"] == 1.0


# =============================================================================
# HybridOrchestratorV2 Tests
# =============================================================================


class TestHybridOrchestratorV2:
    """Tests for HybridOrchestratorV2 class."""

    def test_initialization(self, orchestrator, basic_config):
        """Test orchestrator initialization."""
        assert orchestrator.config == basic_config
        assert orchestrator.intent_router is not None
        assert orchestrator.context_bridge is not None
        assert orchestrator.unified_executor is not None

    def test_initialization_with_defaults(self):
        """Test orchestrator initialization with defaults."""
        orchestrator = HybridOrchestratorV2()

        assert orchestrator.config is not None
        assert orchestrator.intent_router is not None
        assert orchestrator.context_bridge is not None

    def test_create_session(self, orchestrator):
        """Test session creation."""
        session_id = orchestrator.create_session()

        assert session_id is not None
        assert orchestrator.active_session_id == session_id
        assert orchestrator.session_count == 1

    def test_create_session_with_custom_id(self, orchestrator):
        """Test session creation with custom ID."""
        session_id = orchestrator.create_session(session_id="my-custom-session")

        assert session_id == "my-custom-session"
        assert orchestrator.get_session("my-custom-session") is not None

    def test_close_session(self, orchestrator):
        """Test session closing."""
        session_id = orchestrator.create_session()
        result = orchestrator.close_session(session_id)

        assert result is True
        assert orchestrator.get_session(session_id) is None
        assert orchestrator.active_session_id is None

    @pytest.mark.asyncio
    async def test_execute_chat_mode(
        self,
        orchestrator,
        mock_intent_router,
        mock_claude_executor,
    ):
        """Test execution in CHAT_MODE."""
        orchestrator._claude_executor = mock_claude_executor

        result = await orchestrator.execute(
            prompt="Hello, how are you?",
            session_id="test-session",
        )

        # Should have analyzed intent
        mock_intent_router.analyze_intent.assert_called()

        # Result should be successful
        assert result.success is True
        assert result.execution_mode == ExecutionMode.CHAT_MODE

    @pytest.mark.asyncio
    async def test_execute_workflow_mode(
        self,
        orchestrator,
        mock_intent_router,
        mock_maf_executor,
    ):
        """Test execution in WORKFLOW_MODE."""
        # Configure intent router to return WORKFLOW_MODE
        mock_intent_router.analyze_intent.return_value = IntentAnalysis(
            mode=ExecutionMode.WORKFLOW_MODE,
            confidence=0.95,
            reasoning="Task requires structured workflow",
        )
        orchestrator._maf_executor = mock_maf_executor

        result = await orchestrator.execute(
            prompt="Process the monthly report",
            session_id="test-session",
        )

        assert result.success is True
        assert result.execution_mode == ExecutionMode.WORKFLOW_MODE

    @pytest.mark.asyncio
    async def test_execute_with_force_mode(
        self,
        orchestrator,
        mock_intent_router,
        mock_claude_executor,
    ):
        """Test execution with forced mode."""
        orchestrator._claude_executor = mock_claude_executor

        # Force CHAT_MODE
        result = await orchestrator.execute(
            prompt="Do something complex",
            session_id="test-session",
            force_mode=ExecutionMode.CHAT_MODE,
        )

        # Intent router should NOT be called when mode is forced
        mock_intent_router.analyze_intent.assert_not_called()
        assert result.execution_mode == ExecutionMode.CHAT_MODE

    @pytest.mark.asyncio
    async def test_execute_context_sync(
        self,
        orchestrator,
        mock_context_bridge,
        mock_claude_executor,
    ):
        """Test context synchronization during execution."""
        orchestrator._claude_executor = mock_claude_executor

        await orchestrator.execute(
            prompt="Hello",
            session_id="test-session",
            force_mode=ExecutionMode.CHAT_MODE,
        )

        # Context bridge should be called
        mock_context_bridge.get_or_create_hybrid.assert_called()

    @pytest.mark.asyncio
    async def test_execute_no_executor(self, orchestrator):
        """Test execution without executor (simulated response)."""
        result = await orchestrator.execute(
            prompt="Hello",
            force_mode=ExecutionMode.CHAT_MODE,
        )

        # Should return simulated response
        assert result.success is True
        assert "[CHAT_MODE]" in result.content

    def test_get_metrics(self, orchestrator):
        """Test getting orchestrator metrics."""
        metrics = orchestrator.get_metrics()

        assert isinstance(metrics, dict)
        assert "execution_count" in metrics

    def test_reset_metrics(self, orchestrator):
        """Test resetting metrics."""
        orchestrator._metrics.record_execution(
            ExecutionMode.CHAT_MODE, "claude_sdk", True, 1.0
        )

        orchestrator.reset_metrics()

        metrics = orchestrator.get_metrics()
        assert metrics["execution_count"] == 0


# =============================================================================
# V1 Compatibility Tests
# =============================================================================


class TestV1Compatibility:
    """Tests for V1 compatibility methods."""

    def test_set_claude_executor(self, orchestrator, mock_claude_executor):
        """Test setting Claude executor."""
        orchestrator.set_claude_executor(mock_claude_executor)

        assert orchestrator._claude_executor == mock_claude_executor

    def test_set_maf_executor(self, orchestrator, mock_maf_executor):
        """Test setting MAF executor."""
        orchestrator.set_maf_executor(mock_maf_executor)

        assert orchestrator._maf_executor == mock_maf_executor

    def test_analyze_task(self, orchestrator, mock_intent_router):
        """Test analyze_task V1 compatibility method (sync wrapper)."""
        # This is a sync method that wraps async analyze_intent
        analysis = orchestrator.analyze_task("Process this request")

        assert analysis is not None
        assert isinstance(analysis, IntentAnalysis)


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestCreateOrchestratorV2:
    """Tests for create_orchestrator_v2 factory function."""

    def test_create_default_orchestrator(self):
        """Test creating orchestrator with defaults."""
        orchestrator = create_orchestrator_v2()

        assert isinstance(orchestrator, HybridOrchestratorV2)
        assert orchestrator.config.mode == OrchestratorMode.V2_FULL

    def test_create_with_custom_mode(self):
        """Test creating orchestrator with custom mode."""
        orchestrator = create_orchestrator_v2(
            mode=OrchestratorMode.V1_COMPAT
        )

        assert orchestrator.config.mode == OrchestratorMode.V1_COMPAT

    def test_create_with_custom_framework(self):
        """Test creating orchestrator with custom primary framework."""
        orchestrator = create_orchestrator_v2(
            primary_framework="microsoft_agent_framework"
        )

        assert orchestrator.config.primary_framework == "microsoft_agent_framework"

    def test_create_with_intent_router(self, mock_intent_router):
        """Test creating orchestrator with intent router (framework_selector)."""
        orchestrator = create_orchestrator_v2(
            intent_router=mock_intent_router
        )

        # Sprint 98: _intent_router renamed to _framework_selector
        assert orchestrator._framework_selector == mock_intent_router

    def test_create_with_context_bridge(self, mock_context_bridge):
        """Test creating orchestrator with context bridge."""
        orchestrator = create_orchestrator_v2(
            context_bridge=mock_context_bridge
        )

        assert orchestrator._context_bridge == mock_context_bridge

    def test_create_with_all_dependencies(
        self,
        mock_intent_router,
        mock_context_bridge,
        mock_tool_executor,
    ):
        """Test creating orchestrator with all dependencies."""
        orchestrator = create_orchestrator_v2(
            intent_router=mock_intent_router,
            context_bridge=mock_context_bridge,
            unified_executor=mock_tool_executor,
        )

        # Sprint 98: _intent_router renamed to _framework_selector
        assert orchestrator._framework_selector == mock_intent_router
        assert orchestrator._context_bridge == mock_context_bridge
        assert orchestrator._unified_executor == mock_tool_executor


# =============================================================================
# Integration Scenario Tests
# =============================================================================


class TestIntegrationScenarios:
    """Tests for realistic integration scenarios."""

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(
        self,
        orchestrator,
        mock_claude_executor,
    ):
        """Test multi-turn conversation scenario."""
        orchestrator._claude_executor = mock_claude_executor
        session_id = orchestrator.create_session()

        # First turn
        result1 = await orchestrator.execute(
            prompt="Hello!",
            session_id=session_id,
            force_mode=ExecutionMode.CHAT_MODE,
        )
        assert result1.success is True

        # Second turn
        result2 = await orchestrator.execute(
            prompt="Tell me more",
            session_id=session_id,
            force_mode=ExecutionMode.CHAT_MODE,
        )
        assert result2.success is True

        # History should have entries
        context = orchestrator.get_session(session_id)
        assert len(context.conversation_history) >= 2

    @pytest.mark.asyncio
    async def test_mode_switching_scenario(
        self,
        orchestrator,
        mock_intent_router,
        mock_claude_executor,
        mock_maf_executor,
    ):
        """Test switching between modes."""
        orchestrator._claude_executor = mock_claude_executor
        orchestrator._maf_executor = mock_maf_executor
        session_id = orchestrator.create_session()

        # Chat mode first
        mock_intent_router.analyze_intent.return_value = IntentAnalysis(
            mode=ExecutionMode.CHAT_MODE,
            confidence=0.9,
            reasoning="Conversational",
        )

        result1 = await orchestrator.execute(
            prompt="Hi there!",
            session_id=session_id,
        )
        assert result1.execution_mode == ExecutionMode.CHAT_MODE

        # Then workflow mode
        mock_intent_router.analyze_intent.return_value = IntentAnalysis(
            mode=ExecutionMode.WORKFLOW_MODE,
            confidence=0.95,
            reasoning="Structured task",
        )

        result2 = await orchestrator.execute(
            prompt="Run the monthly report workflow",
            session_id=session_id,
        )
        assert result2.execution_mode == ExecutionMode.WORKFLOW_MODE

    @pytest.mark.asyncio
    async def test_session_lifecycle(self, orchestrator, mock_claude_executor):
        """Test complete session lifecycle."""
        orchestrator._claude_executor = mock_claude_executor

        # Create session
        session_id = orchestrator.create_session(metadata={"user": "test"})
        assert orchestrator.session_count == 1

        # Execute in session
        result = await orchestrator.execute(
            prompt="Hello",
            session_id=session_id,
            force_mode=ExecutionMode.CHAT_MODE,
        )
        assert result.success is True

        # Get session
        context = orchestrator.get_session(session_id)
        assert context is not None
        assert context.metadata["user"] == "test"

        # Close session
        orchestrator.close_session(session_id)
        assert orchestrator.session_count == 0
