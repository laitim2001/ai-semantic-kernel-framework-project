# =============================================================================
# IPA Platform - Backward Compatibility Tests
# =============================================================================
# Sprint 132: Verify HybridOrchestratorV2 backward compatibility after
#   Mediator Pattern refactoring. All existing public API must work unchanged.
# =============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.hybrid.intent import ExecutionMode, IntentAnalysis
from src.integrations.hybrid.context import (
    ContextBridge,
    HybridContext,
    SyncResult,
    SyncDirection,
    SyncStrategy,
)
from src.integrations.hybrid.orchestrator_v2 import (
    HybridOrchestratorV2,
    OrchestratorMode,
    OrchestratorConfig,
    ExecutionContextV2,
    HybridResultV2,
    OrchestratorMetrics,
    create_orchestrator_v2,
)
from src.integrations.hybrid.orchestrator.mediator import OrchestratorMediator
from src.integrations.hybrid.orchestrator.contracts import HandlerType


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
            reasoning="Chat intent",
            analysis_time_ms=5.0,
        )
    )
    return router


@pytest.fixture
def mock_context_bridge():
    """Create mock context bridge."""
    bridge = MagicMock()
    bridge.get_or_create_hybrid = AsyncMock(
        return_value=HybridContext(
            context_id="test-ctx",
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
def mock_claude_executor():
    """Create mock Claude executor."""
    return AsyncMock(
        return_value={"success": True, "content": "Test response", "tokens_used": 50}
    )


@pytest.fixture
def orchestrator(mock_intent_router, mock_context_bridge, mock_claude_executor):
    """Create HybridOrchestratorV2 with mock dependencies."""
    return HybridOrchestratorV2(
        config=OrchestratorConfig(),
        intent_router=mock_intent_router,
        context_bridge=mock_context_bridge,
        claude_executor=mock_claude_executor,
    )


# =============================================================================
# Test: Mediator Integration
# =============================================================================


class TestMediatorIntegration:
    """Tests for mediator integration with HybridOrchestratorV2."""

    def test_mediator_created(self, orchestrator):
        """Orchestrator creates a mediator instance."""
        assert orchestrator.mediator is not None
        assert isinstance(orchestrator.mediator, OrchestratorMediator)

    def test_mediator_has_all_handlers(self, orchestrator):
        """Mediator has all 6 handler types registered."""
        handlers = orchestrator.mediator.registered_handlers
        assert HandlerType.ROUTING in handlers
        assert HandlerType.DIALOG in handlers
        assert HandlerType.APPROVAL in handlers
        assert HandlerType.EXECUTION in handlers
        assert HandlerType.CONTEXT in handlers
        assert HandlerType.OBSERVABILITY in handlers

    def test_mediator_shares_metrics(self, orchestrator):
        """Mediator shares metrics instance with orchestrator."""
        # Both should reference the same metrics object
        orch_metrics = orchestrator.get_metrics()
        mediator_metrics = orchestrator.mediator.get_metrics()
        assert orch_metrics == mediator_metrics


# =============================================================================
# Test: Existing API Surface
# =============================================================================


class TestExistingAPI:
    """Tests that all existing public API methods still work."""

    def test_config_property(self, orchestrator):
        """config property works."""
        config = orchestrator.config
        assert isinstance(config, OrchestratorConfig)
        assert config.mode == OrchestratorMode.V2_FULL

    def test_session_management(self, orchestrator):
        """create_session, get_session, close_session work."""
        sid = orchestrator.create_session(metadata={"test": True})
        assert orchestrator.session_count == 1
        assert orchestrator.active_session_id == sid

        session = orchestrator.get_session(sid)
        assert session is not None

        assert orchestrator.close_session(sid) is True
        assert orchestrator.session_count == 0

    def test_framework_selector_property(self, orchestrator):
        """framework_selector property works."""
        assert orchestrator.framework_selector is not None

    def test_intent_router_property(self, orchestrator):
        """intent_router backward compat property works."""
        assert orchestrator.intent_router is not None
        assert orchestrator.intent_router is orchestrator.framework_selector

    def test_context_bridge_property(self, orchestrator):
        """context_bridge property works."""
        assert orchestrator.context_bridge is not None

    def test_phase28_properties(self, orchestrator):
        """Phase 28 component properties work."""
        assert orchestrator.input_gateway is None  # Not configured
        assert orchestrator.business_router is None
        assert orchestrator.guided_dialog is None
        assert orchestrator.risk_assessor is None
        assert orchestrator.hitl_controller is None
        assert orchestrator.has_phase_28_components() is False

    def test_swarm_handler_property(self, orchestrator):
        """swarm_handler property works."""
        assert orchestrator.swarm_handler is None

    def test_unified_executor_property(self, orchestrator):
        """unified_executor property works."""
        assert orchestrator.unified_executor is None

    @pytest.mark.asyncio
    async def test_execute_method(self, orchestrator, mock_claude_executor):
        """execute() method works exactly as before."""
        result = await orchestrator.execute(
            prompt="Hello, help me",
            session_id=None,
            force_mode=None,
        )
        assert isinstance(result, HybridResultV2)
        assert result.success is True
        assert result.content == "Test response"
        assert result.session_id is not None

    @pytest.mark.asyncio
    async def test_execute_with_force_mode(self, orchestrator):
        """execute() with force_mode works."""
        result = await orchestrator.execute(
            prompt="Run workflow",
            force_mode=ExecutionMode.WORKFLOW_MODE,
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_with_session(self, orchestrator):
        """execute() reuses existing session."""
        sid = orchestrator.create_session(session_id="test-session")
        result = await orchestrator.execute(
            prompt="Test",
            session_id="test-session",
        )
        assert result.session_id == "test-session"

    def test_get_metrics(self, orchestrator):
        """get_metrics() returns dict."""
        metrics = orchestrator.get_metrics()
        assert isinstance(metrics, dict)
        assert "execution_count" in metrics

    def test_reset_metrics(self, orchestrator):
        """reset_metrics() works."""
        orchestrator.reset_metrics()
        metrics = orchestrator.get_metrics()
        assert metrics["execution_count"] == 0

    def test_v1_compat_methods(self, orchestrator):
        """V1 compatibility methods exist."""
        assert hasattr(orchestrator, "analyze_task")
        assert hasattr(orchestrator, "set_claude_executor")
        assert hasattr(orchestrator, "set_maf_executor")


# =============================================================================
# Test: Factory Function
# =============================================================================


class TestFactoryFunction:
    """Tests for create_orchestrator_v2 factory."""

    def test_factory_default(self):
        """Factory creates orchestrator with defaults."""
        orch = create_orchestrator_v2()
        assert orch is not None
        assert orch.config.mode == OrchestratorMode.V2_FULL
        assert orch.mediator is not None

    def test_factory_custom_mode(self):
        """Factory creates orchestrator with custom mode."""
        orch = create_orchestrator_v2(mode=OrchestratorMode.V2_MINIMAL)
        assert orch.config.mode == OrchestratorMode.V2_MINIMAL

    def test_factory_with_intent_router(self, mock_intent_router):
        """Factory accepts intent_router."""
        orch = create_orchestrator_v2(intent_router=mock_intent_router)
        assert orch.framework_selector is mock_intent_router


# =============================================================================
# Test: Data Classes
# =============================================================================


class TestDataClasses:
    """Tests for data class backward compatibility."""

    def test_orchestrator_mode_enum(self):
        """OrchestratorMode enum values preserved."""
        assert OrchestratorMode.V1_COMPAT == "v1_compat"
        assert OrchestratorMode.V2_FULL == "v2_full"
        assert OrchestratorMode.V2_MINIMAL == "v2_minimal"

    def test_orchestrator_config(self):
        """OrchestratorConfig defaults preserved."""
        config = OrchestratorConfig()
        assert config.mode == OrchestratorMode.V2_FULL
        assert config.primary_framework == "claude_sdk"
        assert config.auto_switch is True
        assert config.switch_confidence_threshold == 0.7
        assert config.timeout == 300.0
        assert config.max_retries == 3

    def test_execution_context_v2(self):
        """ExecutionContextV2 creation preserved."""
        ctx = ExecutionContextV2()
        assert ctx.session_id is not None
        assert ctx.current_mode == ExecutionMode.CHAT_MODE
        assert ctx.conversation_history == []

    def test_hybrid_result_v2(self):
        """HybridResultV2 creation preserved."""
        result = HybridResultV2(success=True, content="Test")
        assert result.success is True
        assert result.content == "Test"
        assert result.error is None

    def test_orchestrator_metrics(self):
        """OrchestratorMetrics preserved."""
        metrics = OrchestratorMetrics()
        assert metrics.execution_count == 0

        metrics.record_execution(
            mode=ExecutionMode.CHAT_MODE,
            framework="claude_sdk",
            success=True,
            duration=1.0,
        )
        assert metrics.execution_count == 1
        assert metrics.success_count == 1

        d = metrics.to_dict()
        assert d["execution_count"] == 1
        assert d["success_rate"] == 1.0

        metrics.reset()
        assert metrics.execution_count == 0


# =============================================================================
# Test: Import Paths
# =============================================================================


class TestImportPaths:
    """Tests that all import paths still work."""

    def test_import_from_orchestrator_v2(self):
        """Direct imports from orchestrator_v2 work."""
        from src.integrations.hybrid.orchestrator_v2 import (
            HybridOrchestratorV2,
            OrchestratorMode,
            OrchestratorConfig,
            ExecutionContextV2,
            HybridResultV2,
            OrchestratorMetrics,
            create_orchestrator_v2,
        )
        assert HybridOrchestratorV2 is not None

    def test_import_from_hybrid_init(self):
        """Imports from hybrid __init__ work."""
        from src.integrations.hybrid import (
            HybridOrchestratorV2,
            OrchestratorMode,
            OrchestratorConfig,
            ExecutionContextV2,
            HybridResultV2,
            OrchestratorMetrics,
            create_orchestrator_v2,
        )
        assert HybridOrchestratorV2 is not None

    def test_import_mediator_from_hybrid(self):
        """New mediator imports from hybrid __init__ work."""
        from src.integrations.hybrid import (
            OrchestratorMediator,
            Handler,
            HandlerResult,
            HandlerType,
            OrchestratorRequest,
            OrchestratorResponse,
            EventType,
            RoutingHandler,
            DialogHandler,
            ApprovalHandler,
            ExecutionHandler,
            ContextHandler,
            ObservabilityHandler,
        )
        assert OrchestratorMediator is not None
        assert HandlerType.ROUTING == "routing"

    def test_import_from_orchestrator_package(self):
        """Imports from orchestrator package work."""
        from src.integrations.hybrid.orchestrator import (
            OrchestratorMediator,
            Handler,
            HandlerResult,
            HandlerType,
            OrchestratorRequest,
            OrchestratorResponse,
            EventType,
        )
        assert OrchestratorMediator is not None
