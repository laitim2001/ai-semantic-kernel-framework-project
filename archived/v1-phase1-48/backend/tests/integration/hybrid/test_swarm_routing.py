# =============================================================================
# IPA Platform - Swarm Routing Integration Tests
# =============================================================================
# Sprint 116: Tests for Swarm mode integration in execute_with_routing()
#
# Tests the full flow through HybridOrchestratorV2.execute_with_routing()
# with Swarm mode enabled/disabled, verifying correct routing decisions.
#
# Test Categories:
#   1. Feature flag disabled: normal flow preserved
#   2. Feature flag enabled + eligible intent: swarm flow
#   3. Feature flag enabled + ineligible intent: normal flow
#   4. Regression: existing modes still work
# =============================================================================

import pytest
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.hybrid.intent.models import ExecutionMode
from src.integrations.hybrid.orchestrator_v2 import (
    HybridOrchestratorV2,
    HybridResultV2,
    OrchestratorConfig,
    OrchestratorMode,
)
from src.integrations.hybrid.swarm_mode import (
    SwarmExecutionConfig,
    SwarmModeHandler,
    SwarmTaskDecomposition,
    SwarmExecutionResult,
)


# =============================================================================
# Fixtures
# =============================================================================


@dataclass
class MockCompletenessInfo:
    """Mock CompletenessInfo for tests."""

    is_sufficient: bool = True
    is_complete: bool = True
    missing_fields: List[str] = field(default_factory=list)
    optional_missing: List[str] = field(default_factory=list)
    completeness_score: float = 1.0
    suggestions: List[str] = field(default_factory=list)


@dataclass
class MockWorkflowType:
    """Mock WorkflowType."""

    value: str


@dataclass
class MockRoutingDecision:
    """Mock RoutingDecision for integration tests."""

    intent_category: Any = None
    workflow_type: Any = None
    sub_intent: Optional[str] = None
    confidence: float = 0.9
    risk_level: Any = None
    completeness: Any = None
    routing_layer: str = "pattern"
    rule_id: Optional[str] = None
    reasoning: str = "Test routing"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        wt = self.workflow_type
        wt_value = wt.value if hasattr(wt, "value") else str(wt)
        return {
            "workflow_type": wt_value,
            "sub_intent": self.sub_intent,
            "metadata": self.metadata,
            "confidence": self.confidence,
        }


@dataclass
class MockRiskAssessment:
    """Mock RiskAssessment."""

    requires_approval: bool = False
    risk_level: str = "low"

    def to_dict(self) -> Dict[str, Any]:
        return {"requires_approval": self.requires_approval, "risk_level": self.risk_level}


@pytest.fixture
def mock_input_gateway():
    """Create mock InputGateway that returns a concurrent routing decision."""
    gateway = MagicMock()

    async def mock_process(request):
        return MockRoutingDecision(
            workflow_type=MockWorkflowType(value="concurrent"),
            sub_intent="multi_task",
            completeness=MockCompletenessInfo(),
            metadata={
                "subtasks": [
                    {"id": "s1", "name": "Research Agent", "description": "Research topic"},
                    {"id": "s2", "name": "Writer Agent", "description": "Write content"},
                ],
            },
        )

    gateway.process = AsyncMock(side_effect=mock_process)
    return gateway


@pytest.fixture
def mock_input_gateway_simple():
    """Create mock InputGateway that returns a simple routing decision."""
    gateway = MagicMock()

    async def mock_process(request):
        return MockRoutingDecision(
            workflow_type=MockWorkflowType(value="simple"),
            sub_intent="basic_query",
            completeness=MockCompletenessInfo(),
            metadata={},
        )

    gateway.process = AsyncMock(side_effect=mock_process)
    return gateway


@pytest.fixture
def mock_framework_selector():
    """Create mock FrameworkSelector."""
    selector = MagicMock()
    from src.integrations.hybrid.intent.models import IntentAnalysis, SuggestedFramework

    selector.select_framework = AsyncMock(
        return_value=IntentAnalysis(
            mode=ExecutionMode.CHAT_MODE,
            confidence=0.9,
            reasoning="Test framework selection",
            suggested_framework=SuggestedFramework.CLAUDE,
        )
    )
    selector.analyze_intent = AsyncMock(
        return_value=IntentAnalysis(
            mode=ExecutionMode.CHAT_MODE,
            confidence=0.9,
            reasoning="Test analysis",
        )
    )
    return selector


@pytest.fixture
def mock_context_bridge():
    """Create mock ContextBridge."""
    from src.integrations.hybrid.context import (
        HybridContext,
        SyncResult,
        SyncDirection,
        SyncStrategy,
    )

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

    async def executor(**kwargs):
        return {
            "success": True,
            "content": "Chat response from Claude",
            "tokens_used": 50,
        }

    return executor


@pytest.fixture
def mock_risk_assessor():
    """Create mock RiskAssessor."""
    assessor = MagicMock()
    assessor.assess = MagicMock(return_value=MockRiskAssessment())
    return assessor


@pytest.fixture
def mock_swarm_integration():
    """Create mock SwarmIntegration for handler."""
    integration = MagicMock()
    integration._infer_worker_type = MagicMock(return_value=MagicMock(value="custom"))
    integration.on_coordination_started = MagicMock()
    integration.on_subtask_started = MagicMock()
    integration.on_subtask_progress = MagicMock()
    integration.on_subtask_completed = MagicMock()
    integration.on_coordination_completed = MagicMock()
    return integration


@pytest.fixture
def enabled_swarm_handler(mock_swarm_integration):
    """Create SwarmModeHandler with enabled config."""
    config = SwarmExecutionConfig(
        enabled=True,
        default_mode="parallel",
        max_workers=5,
        worker_timeout=30.0,
        min_subtasks=2,
    )
    return SwarmModeHandler(
        swarm_integration=mock_swarm_integration,
        config=config,
    )


@pytest.fixture
def disabled_swarm_handler(mock_swarm_integration):
    """Create SwarmModeHandler with disabled config."""
    config = SwarmExecutionConfig(
        enabled=False,
        default_mode="parallel",
        max_workers=5,
    )
    return SwarmModeHandler(
        swarm_integration=mock_swarm_integration,
        config=config,
    )


@pytest.fixture
def incoming_request():
    """Create mock IncomingRequest."""
    request = MagicMock()
    request.content = "Research and write a report on AI trends"
    request.source_type = MagicMock(value="user")
    return request


# =============================================================================
# 1. Feature Flag Disabled: Normal Flow Preserved
# =============================================================================


class TestSwarmDisabledNormalFlow:
    """Tests that swarm disabled mode preserves normal routing flow."""

    @pytest.mark.asyncio
    async def test_disabled_swarm_bypasses_swarm_step(
        self,
        mock_input_gateway,
        mock_framework_selector,
        mock_context_bridge,
        mock_claude_executor,
        mock_risk_assessor,
        disabled_swarm_handler,
        incoming_request,
    ):
        """Test that disabled swarm handler skips swarm step entirely."""
        orchestrator = HybridOrchestratorV2(
            config=OrchestratorConfig(mode=OrchestratorMode.V2_FULL),
            input_gateway=mock_input_gateway,
            framework_selector=mock_framework_selector,
            context_bridge=mock_context_bridge,
            claude_executor=mock_claude_executor,
            risk_assessor=mock_risk_assessor,
            swarm_handler=disabled_swarm_handler,
        )

        result = await orchestrator.execute_with_routing(
            request=incoming_request,
            session_id="test-session",
        )

        # Should proceed to framework selection (Step 6), not swarm
        assert result.execution_mode != ExecutionMode.SWARM_MODE
        assert result.framework_used != "swarm"
        mock_framework_selector.select_framework.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_swarm_handler_bypasses_swarm_step(
        self,
        mock_input_gateway,
        mock_framework_selector,
        mock_context_bridge,
        mock_claude_executor,
        mock_risk_assessor,
        incoming_request,
    ):
        """Test that no swarm handler at all works correctly."""
        orchestrator = HybridOrchestratorV2(
            config=OrchestratorConfig(mode=OrchestratorMode.V2_FULL),
            input_gateway=mock_input_gateway,
            framework_selector=mock_framework_selector,
            context_bridge=mock_context_bridge,
            claude_executor=mock_claude_executor,
            risk_assessor=mock_risk_assessor,
            # No swarm_handler
        )

        result = await orchestrator.execute_with_routing(
            request=incoming_request,
            session_id="test-session",
        )

        assert result.execution_mode != ExecutionMode.SWARM_MODE
        mock_framework_selector.select_framework.assert_called_once()


# =============================================================================
# 2. Feature Flag Enabled + Eligible Intent: Swarm Flow
# =============================================================================


class TestSwarmEnabledEligibleIntent:
    """Tests that eligible intents trigger swarm execution when enabled."""

    @pytest.mark.asyncio
    async def test_concurrent_workflow_triggers_swarm(
        self,
        mock_input_gateway,
        mock_framework_selector,
        mock_context_bridge,
        mock_claude_executor,
        mock_risk_assessor,
        enabled_swarm_handler,
        incoming_request,
    ):
        """Test that CONCURRENT workflow type triggers swarm mode."""
        orchestrator = HybridOrchestratorV2(
            config=OrchestratorConfig(mode=OrchestratorMode.V2_FULL),
            input_gateway=mock_input_gateway,
            framework_selector=mock_framework_selector,
            context_bridge=mock_context_bridge,
            claude_executor=mock_claude_executor,
            risk_assessor=mock_risk_assessor,
            swarm_handler=enabled_swarm_handler,
        )

        result = await orchestrator.execute_with_routing(
            request=incoming_request,
            session_id="test-session",
        )

        # Should use swarm mode
        assert result.execution_mode == ExecutionMode.SWARM_MODE
        assert result.framework_used == "swarm"
        assert "swarm_id" in result.metadata
        assert result.metadata["phase_28_flow"] is True
        # Framework selector should NOT be called (swarm short-circuits)
        mock_framework_selector.select_framework.assert_not_called()

    @pytest.mark.asyncio
    async def test_swarm_result_contains_worker_info(
        self,
        mock_input_gateway,
        mock_framework_selector,
        mock_context_bridge,
        mock_claude_executor,
        mock_risk_assessor,
        enabled_swarm_handler,
        incoming_request,
    ):
        """Test that swarm result includes worker-level details."""
        orchestrator = HybridOrchestratorV2(
            config=OrchestratorConfig(mode=OrchestratorMode.V2_FULL),
            input_gateway=mock_input_gateway,
            framework_selector=mock_framework_selector,
            context_bridge=mock_context_bridge,
            claude_executor=mock_claude_executor,
            risk_assessor=mock_risk_assessor,
            swarm_handler=enabled_swarm_handler,
        )

        result = await orchestrator.execute_with_routing(
            request=incoming_request,
            session_id="test-session",
        )

        assert result.success is True
        assert "worker_count" in result.metadata
        assert result.metadata["worker_count"] == 2
        assert "worker_results" in result.metadata
        assert len(result.metadata["worker_results"]) == 2

    @pytest.mark.asyncio
    async def test_swarm_with_user_override_in_metadata(
        self,
        mock_input_gateway_simple,
        mock_framework_selector,
        mock_context_bridge,
        mock_claude_executor,
        mock_risk_assessor,
        enabled_swarm_handler,
        incoming_request,
    ):
        """Test swarm activation via user metadata override."""
        orchestrator = HybridOrchestratorV2(
            config=OrchestratorConfig(mode=OrchestratorMode.V2_FULL),
            input_gateway=mock_input_gateway_simple,
            framework_selector=mock_framework_selector,
            context_bridge=mock_context_bridge,
            claude_executor=mock_claude_executor,
            risk_assessor=mock_risk_assessor,
            swarm_handler=enabled_swarm_handler,
        )

        result = await orchestrator.execute_with_routing(
            request=incoming_request,
            session_id="test-session",
            metadata={
                "use_swarm": True,
                "subtasks": [
                    {"id": "s1", "name": "W1", "description": "Task 1"},
                    {"id": "s2", "name": "W2", "description": "Task 2"},
                ],
            },
        )

        assert result.execution_mode == ExecutionMode.SWARM_MODE
        assert result.framework_used == "swarm"


# =============================================================================
# 3. Feature Flag Enabled + Ineligible Intent: Normal Flow
# =============================================================================


class TestSwarmEnabledIneligibleIntent:
    """Tests that ineligible intents fall through to normal flow."""

    @pytest.mark.asyncio
    async def test_simple_workflow_skips_swarm(
        self,
        mock_input_gateway_simple,
        mock_framework_selector,
        mock_context_bridge,
        mock_claude_executor,
        mock_risk_assessor,
        enabled_swarm_handler,
        incoming_request,
    ):
        """Test that SIMPLE workflow type skips swarm and proceeds normally."""
        orchestrator = HybridOrchestratorV2(
            config=OrchestratorConfig(mode=OrchestratorMode.V2_FULL),
            input_gateway=mock_input_gateway_simple,
            framework_selector=mock_framework_selector,
            context_bridge=mock_context_bridge,
            claude_executor=mock_claude_executor,
            risk_assessor=mock_risk_assessor,
            swarm_handler=enabled_swarm_handler,
        )

        result = await orchestrator.execute_with_routing(
            request=incoming_request,
            session_id="test-session",
        )

        # Should NOT use swarm mode (SIMPLE workflow)
        assert result.execution_mode != ExecutionMode.SWARM_MODE
        assert result.framework_used != "swarm"
        # Framework selector should be called
        mock_framework_selector.select_framework.assert_called_once()


# =============================================================================
# 4. Regression: Existing Modes Still Work
# =============================================================================


class TestExistingModesRegression:
    """Regression tests to ensure existing execution modes are unaffected."""

    @pytest.mark.asyncio
    async def test_chat_mode_still_works_with_swarm_handler(
        self,
        mock_input_gateway_simple,
        mock_framework_selector,
        mock_context_bridge,
        mock_claude_executor,
        mock_risk_assessor,
        enabled_swarm_handler,
        incoming_request,
    ):
        """Test that CHAT_MODE path still works when swarm handler is present."""
        orchestrator = HybridOrchestratorV2(
            config=OrchestratorConfig(mode=OrchestratorMode.V2_FULL),
            input_gateway=mock_input_gateway_simple,
            framework_selector=mock_framework_selector,
            context_bridge=mock_context_bridge,
            claude_executor=mock_claude_executor,
            risk_assessor=mock_risk_assessor,
            swarm_handler=enabled_swarm_handler,
        )

        result = await orchestrator.execute_with_routing(
            request=incoming_request,
            session_id="test-session",
        )

        assert result.success is True
        assert result.content == "Chat response from Claude"

    @pytest.mark.asyncio
    async def test_workflow_mode_still_works_with_swarm_handler(
        self,
        mock_input_gateway_simple,
        mock_context_bridge,
        mock_risk_assessor,
        enabled_swarm_handler,
        incoming_request,
    ):
        """Test that WORKFLOW_MODE path still works when swarm handler is present."""
        from src.integrations.hybrid.intent.models import (
            IntentAnalysis,
            SuggestedFramework,
        )

        # Framework selector returns WORKFLOW_MODE
        selector = MagicMock()
        selector.select_framework = AsyncMock(
            return_value=IntentAnalysis(
                mode=ExecutionMode.WORKFLOW_MODE,
                confidence=0.95,
                reasoning="Workflow detected",
                suggested_framework=SuggestedFramework.MAF,
            )
        )
        selector.analyze_intent = AsyncMock(
            return_value=IntentAnalysis(
                mode=ExecutionMode.WORKFLOW_MODE,
                confidence=0.95,
                reasoning="Workflow",
            )
        )

        async def maf_executor(**kwargs):
            return {
                "success": True,
                "content": "Workflow completed via MAF",
            }

        orchestrator = HybridOrchestratorV2(
            config=OrchestratorConfig(mode=OrchestratorMode.V2_FULL),
            input_gateway=mock_input_gateway_simple,
            framework_selector=selector,
            context_bridge=mock_context_bridge,
            maf_executor=maf_executor,
            risk_assessor=mock_risk_assessor,
            swarm_handler=enabled_swarm_handler,
        )

        result = await orchestrator.execute_with_routing(
            request=incoming_request,
            session_id="test-session",
        )

        assert result.success is True
        assert "Workflow completed via MAF" in result.content
        assert result.execution_mode != ExecutionMode.SWARM_MODE

    @pytest.mark.asyncio
    async def test_basic_execute_unaffected_by_swarm(
        self,
        mock_framework_selector,
        mock_context_bridge,
        mock_claude_executor,
        enabled_swarm_handler,
    ):
        """Test that the basic execute() method is unaffected by swarm handler."""
        orchestrator = HybridOrchestratorV2(
            config=OrchestratorConfig(mode=OrchestratorMode.V2_FULL),
            framework_selector=mock_framework_selector,
            context_bridge=mock_context_bridge,
            claude_executor=mock_claude_executor,
            swarm_handler=enabled_swarm_handler,
        )

        result = await orchestrator.execute(
            prompt="Hello, how are you?",
            session_id="test-session",
        )

        # Basic execute() does not use swarm_handler
        assert result.success is True
        assert result.execution_mode != ExecutionMode.SWARM_MODE

    @pytest.mark.asyncio
    async def test_execute_with_routing_error_handling_preserved(
        self,
        mock_framework_selector,
        mock_context_bridge,
        mock_claude_executor,
        enabled_swarm_handler,
        incoming_request,
    ):
        """Test that error handling in execute_with_routing is preserved."""
        # No input_gateway should raise ValueError
        orchestrator = HybridOrchestratorV2(
            config=OrchestratorConfig(mode=OrchestratorMode.V2_FULL),
            # Intentionally no input_gateway
            framework_selector=mock_framework_selector,
            context_bridge=mock_context_bridge,
            claude_executor=mock_claude_executor,
            swarm_handler=enabled_swarm_handler,
        )

        with pytest.raises(ValueError, match="InputGateway not configured"):
            await orchestrator.execute_with_routing(
                request=incoming_request,
                session_id="test-session",
            )
