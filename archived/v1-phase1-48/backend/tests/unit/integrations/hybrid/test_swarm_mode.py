# =============================================================================
# IPA Platform - Swarm Mode Handler Unit Tests
# =============================================================================
# Sprint 116: Tests for SwarmModeHandler and SwarmExecutionConfig
#
# Test Categories:
#   1. SwarmExecutionConfig: from_env, defaults
#   2. SwarmModeHandler.analyze_for_swarm: eligibility checks
#   3. SwarmModeHandler.execute_swarm: execution flows
#   4. SwarmModeHandler._aggregate_worker_results: aggregation logic
#   5. Integration with HybridOrchestratorV2: swarm in routing flow
# =============================================================================

import asyncio
import os
import pytest
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.hybrid.swarm_mode import (
    SwarmExecutionConfig,
    SwarmExecutionResult,
    SwarmModeHandler,
    SwarmTaskDecomposition,
)


# =============================================================================
# Test Helpers and Fixtures
# =============================================================================


@dataclass
class MockRoutingDecision:
    """Mock RoutingDecision for testing."""

    workflow_type: Any = None
    sub_intent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    completeness: Any = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        wt = self.workflow_type
        wt_value = wt.value if hasattr(wt, "value") else str(wt)
        return {
            "workflow_type": wt_value,
            "sub_intent": self.sub_intent,
            "metadata": self.metadata,
        }


@dataclass
class MockWorkflowType:
    """Mock WorkflowType enum."""

    value: str


@dataclass
class MockCompletenessInfo:
    """Mock CompletenessInfo."""

    is_sufficient: bool = True
    is_complete: bool = True


@pytest.fixture
def default_config():
    """Create default SwarmExecutionConfig."""
    return SwarmExecutionConfig(
        enabled=True,
        default_mode="parallel",
        max_workers=5,
        worker_timeout=30.0,
        complexity_threshold=0.7,
        min_subtasks=2,
    )


@pytest.fixture
def disabled_config():
    """Create disabled SwarmExecutionConfig."""
    return SwarmExecutionConfig(
        enabled=False,
        default_mode="parallel",
        max_workers=5,
        worker_timeout=30.0,
    )


@pytest.fixture
def mock_swarm_integration():
    """Create mock SwarmIntegration."""
    integration = MagicMock()
    integration._infer_worker_type = MagicMock(return_value=MagicMock(value="custom"))
    integration.on_coordination_started = MagicMock()
    integration.on_subtask_started = MagicMock()
    integration.on_subtask_progress = MagicMock()
    integration.on_subtask_completed = MagicMock()
    integration.on_coordination_completed = MagicMock()
    return integration


@pytest.fixture
def handler(default_config, mock_swarm_integration):
    """Create SwarmModeHandler with enabled config and mock integration."""
    return SwarmModeHandler(
        swarm_integration=mock_swarm_integration,
        config=default_config,
    )


@pytest.fixture
def disabled_handler(disabled_config, mock_swarm_integration):
    """Create SwarmModeHandler with disabled config."""
    return SwarmModeHandler(
        swarm_integration=mock_swarm_integration,
        config=disabled_config,
    )


@pytest.fixture
def concurrent_routing_decision():
    """Create routing decision with CONCURRENT workflow type and subtasks."""
    return MockRoutingDecision(
        workflow_type=MockWorkflowType(value="concurrent"),
        sub_intent="multi_task_execution",
        metadata={
            "subtasks": [
                {"id": "sub-1", "name": "Research Agent", "description": "Research topic"},
                {"id": "sub-2", "name": "Writer Agent", "description": "Write summary"},
                {"id": "sub-3", "name": "Reviewer Agent", "description": "Review output"},
            ],
        },
        completeness=MockCompletenessInfo(),
    )


@pytest.fixture
def simple_routing_decision():
    """Create routing decision with SIMPLE workflow type."""
    return MockRoutingDecision(
        workflow_type=MockWorkflowType(value="simple"),
        sub_intent="basic_query",
        metadata={},
        completeness=MockCompletenessInfo(),
    )


@pytest.fixture
def magentic_routing_decision():
    """Create routing decision with MAGENTIC workflow type."""
    return MockRoutingDecision(
        workflow_type=MockWorkflowType(value="magentic"),
        sub_intent="complex_orchestration",
        metadata={
            "subtasks": [
                {"id": "sub-1", "name": "Coordinator", "description": "Coordinate tasks"},
                {"id": "sub-2", "name": "Analyst", "description": "Analyze data"},
            ],
        },
        completeness=MockCompletenessInfo(),
    )


# =============================================================================
# 1. SwarmExecutionConfig Tests
# =============================================================================


class TestSwarmExecutionConfig:
    """Tests for SwarmExecutionConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = SwarmExecutionConfig()
        assert config.enabled is False
        assert config.default_mode == "parallel"
        assert config.max_workers == 5
        assert config.worker_timeout == 120.0
        assert config.complexity_threshold == 0.7
        assert config.min_subtasks == 2

    def test_custom_values(self):
        """Test custom configuration values."""
        config = SwarmExecutionConfig(
            enabled=True,
            default_mode="hierarchical",
            max_workers=10,
            worker_timeout=60.0,
            complexity_threshold=0.5,
            min_subtasks=3,
        )
        assert config.enabled is True
        assert config.default_mode == "hierarchical"
        assert config.max_workers == 10
        assert config.worker_timeout == 60.0
        assert config.complexity_threshold == 0.5
        assert config.min_subtasks == 3

    def test_from_env_defaults(self):
        """Test from_env with no environment variables set."""
        # Clear any existing env vars
        env_vars = [
            "SWARM_MODE_ENABLED",
            "SWARM_DEFAULT_MODE",
            "SWARM_MAX_WORKERS",
            "SWARM_WORKER_TIMEOUT",
            "SWARM_COMPLEXITY_THRESHOLD",
            "SWARM_MIN_SUBTASKS",
        ]
        with patch.dict(os.environ, {}, clear=False):
            for var in env_vars:
                os.environ.pop(var, None)
            config = SwarmExecutionConfig.from_env()
        assert config.enabled is False
        assert config.default_mode == "parallel"
        assert config.max_workers == 5

    def test_from_env_with_values(self):
        """Test from_env with environment variables set."""
        env = {
            "SWARM_MODE_ENABLED": "true",
            "SWARM_DEFAULT_MODE": "sequential",
            "SWARM_MAX_WORKERS": "8",
            "SWARM_WORKER_TIMEOUT": "60.0",
            "SWARM_COMPLEXITY_THRESHOLD": "0.8",
            "SWARM_MIN_SUBTASKS": "3",
        }
        with patch.dict(os.environ, env):
            config = SwarmExecutionConfig.from_env()
        assert config.enabled is True
        assert config.default_mode == "sequential"
        assert config.max_workers == 8
        assert config.worker_timeout == 60.0
        assert config.complexity_threshold == 0.8
        assert config.min_subtasks == 3

    def test_from_env_enabled_case_insensitive(self):
        """Test that SWARM_MODE_ENABLED is case insensitive."""
        with patch.dict(os.environ, {"SWARM_MODE_ENABLED": "TRUE"}):
            config = SwarmExecutionConfig.from_env()
        assert config.enabled is True

        with patch.dict(os.environ, {"SWARM_MODE_ENABLED": "True"}):
            config = SwarmExecutionConfig.from_env()
        assert config.enabled is True


# =============================================================================
# 2. SwarmModeHandler.analyze_for_swarm Tests
# =============================================================================


class TestAnalyzeForSwarm:
    """Tests for SwarmModeHandler.analyze_for_swarm()."""

    def test_disabled_mode_returns_false(
        self, disabled_handler, concurrent_routing_decision
    ):
        """Test that disabled config always returns should_use_swarm=False."""
        result = disabled_handler.analyze_for_swarm(concurrent_routing_decision)
        assert result.should_use_swarm is False
        assert "disabled" in result.reasoning.lower()

    def test_user_requested_swarm_overrides(self, handler, simple_routing_decision):
        """Test that user explicit request enables swarm even for SIMPLE type."""
        context = {
            "use_swarm": True,
            "subtasks": [
                {"id": "s1", "description": "Task 1"},
                {"id": "s2", "description": "Task 2"},
            ],
            "swarm_mode": "sequential",
        }
        result = handler.analyze_for_swarm(simple_routing_decision, context)
        assert result.should_use_swarm is True
        assert result.swarm_mode == "sequential"
        assert len(result.subtasks) == 2
        assert "User explicitly requested" in result.reasoning

    def test_user_requested_swarm_uses_decomposition_fallback(
        self, handler, concurrent_routing_decision
    ):
        """Test that user request without subtasks falls back to decomposition."""
        context = {"use_swarm": True}
        result = handler.analyze_for_swarm(concurrent_routing_decision, context)
        assert result.should_use_swarm is True
        assert len(result.subtasks) == 3  # from metadata

    def test_concurrent_workflow_eligible(
        self, handler, concurrent_routing_decision
    ):
        """Test that CONCURRENT workflow type is eligible for swarm."""
        result = handler.analyze_for_swarm(concurrent_routing_decision)
        assert result.should_use_swarm is True
        assert result.swarm_mode == "parallel"
        assert len(result.subtasks) == 3

    def test_magentic_workflow_eligible(
        self, handler, magentic_routing_decision
    ):
        """Test that MAGENTIC workflow type is eligible and uses hierarchical mode."""
        result = handler.analyze_for_swarm(magentic_routing_decision)
        assert result.should_use_swarm is True
        assert result.swarm_mode == "hierarchical"
        assert len(result.subtasks) == 2

    def test_simple_workflow_not_eligible(
        self, handler, simple_routing_decision
    ):
        """Test that SIMPLE workflow type is not eligible for swarm."""
        result = handler.analyze_for_swarm(simple_routing_decision)
        assert result.should_use_swarm is False
        assert "not eligible" in result.reasoning.lower()

    def test_insufficient_subtasks_not_eligible(self, handler):
        """Test that task with fewer subtasks than min_subtasks is rejected."""
        decision = MockRoutingDecision(
            workflow_type=MockWorkflowType(value="concurrent"),
            sub_intent="single_task",
            metadata={
                "subtasks": [
                    {"id": "s1", "description": "Only one task"},
                ],
            },
        )
        result = handler.analyze_for_swarm(decision)
        assert result.should_use_swarm is False
        assert "Insufficient subtasks" in result.reasoning

    def test_estimated_workers_capped_by_max_workers(self, handler):
        """Test that estimated_workers does not exceed max_workers."""
        many_subtasks = [
            {"id": f"s-{i}", "description": f"Task {i}"}
            for i in range(10)
        ]
        decision = MockRoutingDecision(
            workflow_type=MockWorkflowType(value="concurrent"),
            metadata={"subtasks": many_subtasks},
        )
        result = handler.analyze_for_swarm(decision)
        assert result.should_use_swarm is True
        assert result.estimated_workers == handler.config.max_workers  # 5

    def test_no_metadata_uses_sub_intent_fallback(self, handler):
        """Test decomposition from sub_intent when metadata is empty."""
        decision = MockRoutingDecision(
            workflow_type=MockWorkflowType(value="concurrent"),
            sub_intent="analyze_logs",
            metadata={},
        )
        result = handler.analyze_for_swarm(decision)
        # Only one subtask from sub_intent, less than min_subtasks (2)
        assert result.should_use_swarm is False

    def test_required_tools_metadata_creates_subtasks(self, handler):
        """Test decomposition from required_tools in metadata."""
        decision = MockRoutingDecision(
            workflow_type=MockWorkflowType(value="concurrent"),
            metadata={
                "required_tools": ["search_tool", "write_tool", "review_tool"],
            },
        )
        result = handler.analyze_for_swarm(decision)
        assert result.should_use_swarm is True
        assert len(result.subtasks) == 3

    def test_none_context_handled_gracefully(self, handler, concurrent_routing_decision):
        """Test that None context is handled without error."""
        result = handler.analyze_for_swarm(concurrent_routing_decision, None)
        assert result.should_use_swarm is True

    def test_empty_context_handled_gracefully(self, handler, concurrent_routing_decision):
        """Test that empty dict context works."""
        result = handler.analyze_for_swarm(concurrent_routing_decision, {})
        assert result.should_use_swarm is True

    def test_no_workflow_type_attribute(self, handler):
        """Test handling of routing decision without workflow_type attribute."""
        decision = MagicMock(spec=[])  # No attributes
        result = handler.analyze_for_swarm(decision)
        assert result.should_use_swarm is False


# =============================================================================
# 3. SwarmModeHandler.execute_swarm Tests
# =============================================================================


class TestExecuteSwarm:
    """Tests for SwarmModeHandler.execute_swarm()."""

    @pytest.mark.asyncio
    async def test_execute_swarm_success_no_executor(
        self, handler, mock_swarm_integration, concurrent_routing_decision
    ):
        """Test successful swarm execution with simulated workers (no executor)."""
        decomposition = SwarmTaskDecomposition(
            should_use_swarm=True,
            subtasks=[
                {"id": "s1", "name": "Worker A", "description": "Research topic"},
                {"id": "s2", "name": "Worker B", "description": "Write summary"},
            ],
            swarm_mode="parallel",
            estimated_workers=2,
        )

        result = await handler.execute_swarm(
            intent="Research and summarize topic",
            decomposition=decomposition,
            routing_decision=concurrent_routing_decision,
            session_id="test-session-1",
        )

        assert result.success is True
        assert result.swarm_id.startswith("swarm-")
        assert len(result.worker_results) == 2
        assert all(r["success"] for r in result.worker_results)
        assert result.total_duration > 0
        assert result.metadata["total_workers"] == 2
        assert result.metadata["completed_workers"] == 2
        assert result.metadata["failed_workers"] == 0

        # Verify integration callbacks were called
        mock_swarm_integration.on_coordination_started.assert_called_once()
        assert mock_swarm_integration.on_subtask_started.call_count == 2
        assert mock_swarm_integration.on_subtask_completed.call_count == 2
        mock_swarm_integration.on_coordination_completed.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_swarm_with_claude_executor(
        self, default_config, mock_swarm_integration, concurrent_routing_decision
    ):
        """Test swarm execution using actual claude_executor."""
        async def mock_claude_exec(**kwargs):
            return {"content": f"Result for: {kwargs.get('prompt', '')[:30]}"}

        handler = SwarmModeHandler(
            swarm_integration=mock_swarm_integration,
            config=default_config,
            claude_executor=mock_claude_exec,
        )

        decomposition = SwarmTaskDecomposition(
            should_use_swarm=True,
            subtasks=[
                {"id": "s1", "name": "Worker A", "description": "Task A"},
            ],
            swarm_mode="parallel",
            estimated_workers=1,
        )

        result = await handler.execute_swarm(
            intent="Execute task",
            decomposition=decomposition,
            routing_decision=concurrent_routing_decision,
        )

        assert result.success is True
        assert len(result.worker_results) == 1
        assert result.worker_results[0]["success"] is True
        assert "Result for:" in result.worker_results[0]["result"]

    @pytest.mark.asyncio
    async def test_execute_swarm_worker_failure(
        self, default_config, mock_swarm_integration, concurrent_routing_decision
    ):
        """Test swarm execution where a worker fails."""
        call_count = 0

        async def failing_executor(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("Worker 2 failed")
            return {"content": "Success"}

        handler = SwarmModeHandler(
            swarm_integration=mock_swarm_integration,
            config=default_config,
            claude_executor=failing_executor,
        )

        decomposition = SwarmTaskDecomposition(
            should_use_swarm=True,
            subtasks=[
                {"id": "s1", "name": "Worker A", "description": "Task A"},
                {"id": "s2", "name": "Worker B", "description": "Task B"},
            ],
            swarm_mode="parallel",
            estimated_workers=2,
        )

        result = await handler.execute_swarm(
            intent="Execute tasks",
            decomposition=decomposition,
            routing_decision=concurrent_routing_decision,
        )

        assert result.success is False  # One worker failed
        assert len(result.worker_results) == 2
        assert result.worker_results[0]["success"] is True
        assert result.worker_results[1]["success"] is False
        assert "Worker 2 failed" in result.worker_results[1]["error"]
        assert result.metadata["completed_workers"] == 1
        assert result.metadata["failed_workers"] == 1

    @pytest.mark.asyncio
    async def test_execute_swarm_all_workers_fail(
        self, default_config, mock_swarm_integration, concurrent_routing_decision
    ):
        """Test swarm execution where all workers fail."""
        async def always_failing(**kwargs):
            raise RuntimeError("Always fails")

        handler = SwarmModeHandler(
            swarm_integration=mock_swarm_integration,
            config=default_config,
            claude_executor=always_failing,
        )

        decomposition = SwarmTaskDecomposition(
            should_use_swarm=True,
            subtasks=[
                {"id": "s1", "name": "Worker A", "description": "Task A"},
                {"id": "s2", "name": "Worker B", "description": "Task B"},
            ],
            swarm_mode="parallel",
            estimated_workers=2,
        )

        result = await handler.execute_swarm(
            intent="Execute tasks",
            decomposition=decomposition,
            routing_decision=concurrent_routing_decision,
        )

        assert result.success is False
        assert result.metadata["failed_workers"] == 2

    @pytest.mark.asyncio
    async def test_execute_swarm_timeout_handling(
        self, default_config, mock_swarm_integration, concurrent_routing_decision
    ):
        """Test that worker timeout is properly handled."""
        async def slow_executor(**kwargs):
            await asyncio.sleep(10)
            return {"content": "Too slow"}

        handler = SwarmModeHandler(
            swarm_integration=mock_swarm_integration,
            config=default_config,
            claude_executor=slow_executor,
        )

        decomposition = SwarmTaskDecomposition(
            should_use_swarm=True,
            subtasks=[
                {"id": "s1", "name": "Slow Worker", "description": "Slow task"},
            ],
            swarm_mode="parallel",
            estimated_workers=1,
        )

        result = await handler.execute_swarm(
            intent="Execute slow task",
            decomposition=decomposition,
            routing_decision=concurrent_routing_decision,
            timeout=0.1,  # Very short timeout
        )

        assert result.success is False
        assert len(result.worker_results) == 1
        assert result.worker_results[0]["success"] is False

    @pytest.mark.asyncio
    async def test_execute_swarm_coordination_failure(
        self, default_config, concurrent_routing_decision
    ):
        """Test handling when SwarmIntegration.on_coordination_started raises."""
        broken_integration = MagicMock()
        broken_integration.on_coordination_started = MagicMock(
            side_effect=RuntimeError("Tracker unavailable")
        )
        broken_integration.on_coordination_completed = MagicMock()

        handler = SwarmModeHandler(
            swarm_integration=broken_integration,
            config=default_config,
        )

        decomposition = SwarmTaskDecomposition(
            should_use_swarm=True,
            subtasks=[{"id": "s1", "description": "Task"}],
            swarm_mode="parallel",
            estimated_workers=1,
        )

        result = await handler.execute_swarm(
            intent="Test",
            decomposition=decomposition,
            routing_decision=concurrent_routing_decision,
        )

        assert result.success is False
        assert "Tracker unavailable" in result.error

    @pytest.mark.asyncio
    async def test_execute_swarm_simulated_content(
        self, handler, mock_swarm_integration, concurrent_routing_decision
    ):
        """Test that simulated workers produce expected content format."""
        decomposition = SwarmTaskDecomposition(
            should_use_swarm=True,
            subtasks=[
                {"id": "s1", "name": "Worker A", "description": "Analyze data"},
            ],
            swarm_mode="parallel",
            estimated_workers=1,
        )

        result = await handler.execute_swarm(
            intent="Analyze",
            decomposition=decomposition,
            routing_decision=concurrent_routing_decision,
        )

        assert "[SWARM_WORKER]" in result.content
        assert "Analyze data" in result.content

    @pytest.mark.asyncio
    async def test_execute_swarm_session_id_in_metadata(
        self, handler, mock_swarm_integration, concurrent_routing_decision
    ):
        """Test that session_id is passed to coordination metadata."""
        decomposition = SwarmTaskDecomposition(
            should_use_swarm=True,
            subtasks=[
                {"id": "s1", "name": "Worker", "description": "Task"},
            ],
            swarm_mode="parallel",
            estimated_workers=1,
        )

        await handler.execute_swarm(
            intent="Test",
            decomposition=decomposition,
            routing_decision=concurrent_routing_decision,
            session_id="my-session-123",
        )

        call_args = mock_swarm_integration.on_coordination_started.call_args
        metadata = call_args.kwargs.get("metadata", call_args[1].get("metadata", {}))
        assert metadata["session_id"] == "my-session-123"


# =============================================================================
# 4. Aggregation Tests
# =============================================================================


class TestAggregateWorkerResults:
    """Tests for SwarmModeHandler._aggregate_worker_results()."""

    def test_all_success(self, handler):
        """Test aggregation with all successful workers."""
        results = [
            {"worker_id": "w1", "worker_name": "Worker 1", "success": True, "result": "Result A"},
            {"worker_id": "w2", "worker_name": "Worker 2", "success": True, "result": "Result B"},
        ]
        output = handler._aggregate_worker_results(results, "test intent")
        assert "[Worker 1] Result A" in output
        assert "[Worker 2] Result B" in output

    def test_mixed_success_and_failure(self, handler):
        """Test aggregation with mixed results."""
        results = [
            {"worker_id": "w1", "worker_name": "Worker 1", "success": True, "result": "OK"},
            {"worker_id": "w2", "worker_name": "Worker 2", "success": False, "error": "Boom"},
        ]
        output = handler._aggregate_worker_results(results, "test intent")
        assert "[Worker 1] OK" in output
        assert "Partial failures" in output
        assert "[Worker 2] Error: Boom" in output

    def test_all_failed(self, handler):
        """Test aggregation with all failed workers."""
        results = [
            {"worker_id": "w1", "worker_name": "Worker 1", "success": False, "error": "Err1"},
            {"worker_id": "w2", "worker_name": "Worker 2", "success": False, "error": "Err2"},
        ]
        output = handler._aggregate_worker_results(results, "test intent")
        assert "Partial failures" in output
        assert "[Worker 1] Error: Err1" in output
        assert "[Worker 2] Error: Err2" in output

    def test_empty_results(self, handler):
        """Test aggregation with empty results list."""
        output = handler._aggregate_worker_results([], "test intent")
        assert "Swarm execution completed for:" in output

    def test_empty_result_content(self, handler):
        """Test aggregation where successful workers have empty result."""
        results = [
            {"worker_id": "w1", "worker_name": "Worker 1", "success": True, "result": ""},
        ]
        output = handler._aggregate_worker_results(results, "test intent")
        # Empty result is skipped, so fallback message is used
        assert "Swarm execution completed for:" in output


# =============================================================================
# 5. Properties and Lazy Loading Tests
# =============================================================================


class TestSwarmModeHandlerProperties:
    """Tests for SwarmModeHandler properties and lazy loading."""

    def test_is_enabled_true(self, handler):
        """Test is_enabled returns True when config.enabled is True."""
        assert handler.is_enabled is True

    def test_is_enabled_false(self, disabled_handler):
        """Test is_enabled returns False when config.enabled is False."""
        assert disabled_handler.is_enabled is False

    def test_config_property(self, handler, default_config):
        """Test config property returns the stored config."""
        assert handler.config is default_config

    @patch("src.integrations.swarm.swarm_integration.SwarmIntegration")
    def test_lazy_loading_swarm_integration(self, mock_cls):
        """Test that SwarmIntegration is lazy-loaded when not provided."""
        from src.integrations.hybrid.swarm_mode import SwarmModeHandler

        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        handler = SwarmModeHandler(
            swarm_integration=None,
            config=SwarmExecutionConfig(enabled=True),
        )

        # Trigger lazy loading
        integration = handler._get_swarm_integration()
        assert integration is not None

    def test_get_workflow_type_with_enum(self, handler):
        """Test _get_workflow_type extracts value from enum."""
        decision = MockRoutingDecision(
            workflow_type=MockWorkflowType(value="concurrent"),
        )
        assert handler._get_workflow_type(decision) == "concurrent"

    def test_get_workflow_type_with_string(self, handler):
        """Test _get_workflow_type with plain string."""
        decision = MockRoutingDecision(workflow_type="simple")
        assert handler._get_workflow_type(decision) == "simple"

    def test_get_workflow_type_missing_attribute(self, handler):
        """Test _get_workflow_type returns UNKNOWN for missing attribute."""
        decision = MagicMock(spec=[])  # No workflow_type attribute
        assert handler._get_workflow_type(decision) == "UNKNOWN"

    def test_determine_swarm_mode_concurrent(self, handler):
        """Test that CONCURRENT workflow maps to parallel mode."""
        mode = handler._determine_swarm_mode("concurrent", [])
        assert mode == "parallel"

    def test_determine_swarm_mode_magentic(self, handler):
        """Test that MAGENTIC workflow maps to hierarchical mode."""
        mode = handler._determine_swarm_mode("magentic", [])
        assert mode == "hierarchical"

    def test_determine_swarm_mode_default(self, handler):
        """Test that unknown workflow type uses default mode."""
        mode = handler._determine_swarm_mode("unknown_type", [])
        assert mode == "parallel"  # default_mode


# =============================================================================
# 6. Integration with HybridOrchestratorV2 Tests
# =============================================================================


class TestOrchestratorV2SwarmIntegration:
    """Tests for Swarm integration within HybridOrchestratorV2."""

    @pytest.mark.asyncio
    async def test_orchestrator_initializes_with_swarm_handler(self):
        """Test that HybridOrchestratorV2 accepts swarm_handler parameter."""
        from src.integrations.hybrid.orchestrator_v2 import (
            HybridOrchestratorV2,
            OrchestratorConfig,
            OrchestratorMode,
        )

        mock_handler = MagicMock(spec=SwarmModeHandler)
        orchestrator = HybridOrchestratorV2(
            config=OrchestratorConfig(mode=OrchestratorMode.V2_FULL),
            swarm_handler=mock_handler,
        )

        assert orchestrator.swarm_handler is mock_handler

    @pytest.mark.asyncio
    async def test_orchestrator_without_swarm_handler(self):
        """Test that HybridOrchestratorV2 works without swarm_handler."""
        from src.integrations.hybrid.orchestrator_v2 import (
            HybridOrchestratorV2,
            OrchestratorConfig,
            OrchestratorMode,
        )

        orchestrator = HybridOrchestratorV2(
            config=OrchestratorConfig(mode=OrchestratorMode.V2_FULL),
        )

        assert orchestrator.swarm_handler is None

    def test_execution_mode_enum_has_swarm(self):
        """Test that ExecutionMode enum includes SWARM_MODE."""
        from src.integrations.hybrid.intent.models import ExecutionMode

        assert hasattr(ExecutionMode, "SWARM_MODE")
        assert ExecutionMode.SWARM_MODE.value == "swarm"

    def test_orchestrator_metrics_include_swarm(self):
        """Test that OrchestratorMetrics includes SWARM_MODE."""
        from src.integrations.hybrid.orchestrator_v2 import OrchestratorMetrics

        metrics = OrchestratorMetrics()
        assert "SWARM_MODE" in metrics.mode_usage
        assert metrics.mode_usage["SWARM_MODE"] == 0
        assert "swarm" in metrics.framework_usage

    def test_orchestrator_metrics_reset_includes_swarm(self):
        """Test that metrics reset preserves SWARM_MODE key."""
        from src.integrations.hybrid.orchestrator_v2 import OrchestratorMetrics

        metrics = OrchestratorMetrics()
        metrics.mode_usage["SWARM_MODE"] = 5
        metrics.framework_usage["swarm"] = 3
        metrics.reset()
        assert "SWARM_MODE" in metrics.mode_usage
        assert metrics.mode_usage["SWARM_MODE"] == 0
        assert "swarm" in metrics.framework_usage
        assert metrics.framework_usage["swarm"] == 0

    def test_metrics_record_swarm_execution(self):
        """Test recording a SWARM_MODE execution in metrics."""
        from src.integrations.hybrid.intent.models import ExecutionMode
        from src.integrations.hybrid.orchestrator_v2 import OrchestratorMetrics

        metrics = OrchestratorMetrics()
        metrics.record_execution(
            mode=ExecutionMode.SWARM_MODE,
            framework="swarm",
            success=True,
            duration=1.5,
        )
        assert metrics.execution_count == 1
        assert metrics.mode_usage["SWARM_MODE"] == 1
        assert metrics.framework_usage["swarm"] == 1
        assert metrics.success_count == 1
