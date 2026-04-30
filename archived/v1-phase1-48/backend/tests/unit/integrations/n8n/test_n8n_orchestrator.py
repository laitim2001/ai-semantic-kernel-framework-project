"""Tests for N8nOrchestrator.

Sprint 125: n8n Integration — Mode 3 Bidirectional Orchestrator

Tests cover:
    - OrchestrationRequest dataclass defaults and custom values
    - ReasoningResult dataclass defaults and custom values
    - Default reasoning function (keyword-based intent classification)
    - Full orchestration flow (sync completion, async monitoring, errors)
    - HITL approval blocking for high-risk operations
    - Timeout handling during orchestration
    - Error handling for N8nNotFoundError, N8nConnectionError, N8nApiError
    - Callback handling for active and unknown requests
    - Orchestrator lifecycle (context manager, close)
"""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.mcp.servers.n8n.client import (
    N8nApiError,
    N8nConfig,
    N8nConnectionError,
    N8nNotFoundError,
)
from src.integrations.n8n.monitor import (
    ExecutionMonitor,
    ExecutionState,
    MonitorConfig,
    MonitorResult,
)
from src.integrations.n8n.orchestrator import (
    N8nOrchestrator,
    OrchestrationRequest,
    OrchestrationResult,
    OrchestrationStatus,
    ReasoningResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def n8n_config():
    """Create a test N8nConfig."""
    return N8nConfig(
        base_url="http://test:5678",
        api_key="test-key",
        timeout=10,
        max_retries=1,
        retry_base_delay=0.01,
    )


@pytest.fixture
def monitor_config():
    """Create a fast monitor config for testing."""
    return MonitorConfig(
        poll_interval=0.01,
        max_poll_interval=0.05,
        default_timeout=5.0,
        max_retries_on_error=1,
        progress_update_interval=0.01,
    )


@pytest.fixture
def orchestrator(n8n_config, monitor_config):
    """Create an N8nOrchestrator with mocked internals."""
    orch = N8nOrchestrator(config=n8n_config, monitor_config=monitor_config)
    # Mock the underlying API client to prevent real HTTP calls
    orch._client = MagicMock()
    orch._client.execute_workflow = AsyncMock()
    orch._client.close = AsyncMock()
    return orch


@pytest.fixture
def sync_success_response():
    """A synchronous success response from n8n execute_workflow."""
    return {
        "data": {
            "executionId": "exec-001",
            "status": "success",
            "data": {"result": "password_reset_complete", "user": "john"},
        },
    }


@pytest.fixture
def async_running_response():
    """An async running response from n8n execute_workflow."""
    return {
        "data": {
            "executionId": "exec-002",
            "status": "running",
        },
    }


# ---------------------------------------------------------------------------
# TestOrchestrationRequest
# ---------------------------------------------------------------------------


class TestOrchestrationRequest:
    """Tests for OrchestrationRequest dataclass."""

    def test_default_values(self):
        """Test auto-generated request_id and default timeout of 300."""
        request = OrchestrationRequest(user_input="test input")

        # request_id should be a valid UUID string
        uuid.UUID(request.request_id)  # Raises ValueError if invalid
        assert request.timeout == 300
        assert request.context == {}
        assert request.workflow_id is None
        assert request.workflow_params == {}
        assert request.callback_url is None
        assert request.metadata == {}

    def test_custom_values(self):
        """Test that custom values are preserved correctly."""
        request = OrchestrationRequest(
            user_input="reset password for user john",
            context={"session_id": "sess-1"},
            workflow_id="wf-password-reset",
            workflow_params={"priority": "high"},
            timeout=120,
            callback_url="http://callback.example.com/webhook",
            metadata={"source": "chatbot"},
            request_id="custom-req-id",
        )

        assert request.user_input == "reset password for user john"
        assert request.context == {"session_id": "sess-1"}
        assert request.workflow_id == "wf-password-reset"
        assert request.workflow_params == {"priority": "high"}
        assert request.timeout == 120
        assert request.callback_url == "http://callback.example.com/webhook"
        assert request.metadata == {"source": "chatbot"}
        assert request.request_id == "custom-req-id"

    def test_metadata_handling(self):
        """Test that metadata dict is independent between instances."""
        request_a = OrchestrationRequest(
            user_input="input a",
            metadata={"key": "a"},
        )
        request_b = OrchestrationRequest(
            user_input="input b",
            metadata={"key": "b"},
        )

        assert request_a.metadata != request_b.metadata
        assert request_a.metadata == {"key": "a"}
        assert request_b.metadata == {"key": "b"}

        # Default metadata should also be independent
        request_c = OrchestrationRequest(user_input="input c")
        request_d = OrchestrationRequest(user_input="input d")
        request_c.metadata["added"] = True
        assert "added" not in request_d.metadata


# ---------------------------------------------------------------------------
# TestReasoningResult
# ---------------------------------------------------------------------------


class TestReasoningResult:
    """Tests for ReasoningResult dataclass."""

    def test_default_values(self):
        """Test default values for ReasoningResult."""
        result = ReasoningResult(intent="QUERY")

        assert result.intent == "QUERY"
        assert result.sub_intent == ""
        assert result.confidence == 0.0
        assert result.recommended_workflow is None
        assert result.workflow_input == {}
        assert result.risk_level == "low"
        assert result.requires_approval is False
        assert result.reasoning_metadata == {}

    def test_custom_reasoning(self):
        """Test ReasoningResult with custom values."""
        result = ReasoningResult(
            intent="INCIDENT",
            sub_intent="system_failure",
            confidence=0.95,
            recommended_workflow="wf-incident-001",
            workflow_input={"severity": "P1"},
            risk_level="critical",
            requires_approval=True,
            reasoning_metadata={"model": "gpt-4o", "tokens": 150},
        )

        assert result.intent == "INCIDENT"
        assert result.sub_intent == "system_failure"
        assert result.confidence == 0.95
        assert result.recommended_workflow == "wf-incident-001"
        assert result.workflow_input == {"severity": "P1"}
        assert result.risk_level == "critical"
        assert result.requires_approval is True
        assert result.reasoning_metadata["model"] == "gpt-4o"


# ---------------------------------------------------------------------------
# TestDefaultReasoning
# ---------------------------------------------------------------------------


class TestDefaultReasoning:
    """Tests for the _default_reasoning static method."""

    @pytest.mark.asyncio
    async def test_incident_classification(self):
        """Test that keywords 'down', 'error', 'fail' classify as INCIDENT."""
        for keyword in ("down", "error", "fail", "crash", "outage"):
            result = await N8nOrchestrator._default_reasoning(
                f"The server is {keyword}",
                {},
            )
            assert result.intent == "INCIDENT", f"Failed for keyword: {keyword}"
            assert result.sub_intent == "system_failure"
            assert result.risk_level == "high"
            assert result.requires_approval is True

    @pytest.mark.asyncio
    async def test_request_classification(self):
        """Test that keywords 'reset', 'password' classify as REQUEST."""
        for keyword in ("reset", "password", "account", "access"):
            result = await N8nOrchestrator._default_reasoning(
                f"Please {keyword} my credentials",
                {},
            )
            assert result.intent == "REQUEST", f"Failed for keyword: {keyword}"
            assert result.sub_intent == "account_management"
            assert result.risk_level == "medium"

    @pytest.mark.asyncio
    async def test_change_classification(self):
        """Test that keywords 'update', 'change' classify as CHANGE."""
        for keyword in ("update", "change", "modify", "config"):
            result = await N8nOrchestrator._default_reasoning(
                f"Please {keyword} the setting",
                {},
            )
            assert result.intent == "CHANGE", f"Failed for keyword: {keyword}"
            assert result.sub_intent == "configuration_change"
            assert result.risk_level == "medium"

    @pytest.mark.asyncio
    async def test_query_classification(self):
        """Test that keywords 'status', 'info' classify as QUERY."""
        for keyword in ("status", "info", "what", "how", "check"):
            result = await N8nOrchestrator._default_reasoning(
                f"Can you {keyword} that",
                {},
            )
            assert result.intent == "QUERY", f"Failed for keyword: {keyword}"
            assert result.sub_intent == "information_request"
            assert result.risk_level == "low"

    @pytest.mark.asyncio
    async def test_unknown_classification(self):
        """Test that unrecognized input classifies as UNKNOWN."""
        result = await N8nOrchestrator._default_reasoning(
            "The sky is blue today",
            {},
        )

        assert result.intent == "UNKNOWN"
        assert result.sub_intent == ""
        assert result.risk_level == "low"
        assert result.confidence == 0.75
        assert result.reasoning_metadata["method"] == "keyword_default"


# ---------------------------------------------------------------------------
# TestOrchestrate
# ---------------------------------------------------------------------------


class TestOrchestrate:
    """Tests for the orchestrate() method."""

    @pytest.mark.asyncio
    async def test_successful_orchestration_sync(
        self, orchestrator, sync_success_response
    ):
        """Test successful orchestration when workflow returns synchronously."""
        # Set up a reasoning function that returns a known result
        reasoning = ReasoningResult(
            intent="REQUEST",
            sub_intent="password_reset",
            confidence=0.9,
            recommended_workflow="wf-pw-reset",
            risk_level="low",
            requires_approval=False,
        )
        orchestrator._reasoning_fn = AsyncMock(return_value=reasoning)
        orchestrator._client.execute_workflow = AsyncMock(
            return_value=sync_success_response
        )

        request = OrchestrationRequest(
            user_input="Reset password for user john",
            request_id="req-sync-001",
        )

        result = await orchestrator.orchestrate(request)

        assert result.request_id == "req-sync-001"
        assert result.status == OrchestrationStatus.COMPLETED
        assert result.reasoning is reasoning
        assert result.execution_id == "exec-001"
        assert result.execution_result is not None
        assert result.execution_result["result"] == "password_reset_complete"
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.duration_ms is not None
        assert result.duration_ms >= 0
        assert len(result.progress_history) > 0

    @pytest.mark.asyncio
    async def test_orchestration_with_monitoring(
        self, orchestrator, async_running_response
    ):
        """Test orchestration that requires async monitoring via wait_for_completion."""
        reasoning = ReasoningResult(
            intent="CHANGE",
            sub_intent="config_change",
            confidence=0.85,
            recommended_workflow="wf-config",
            risk_level="low",
            requires_approval=False,
        )
        orchestrator._reasoning_fn = AsyncMock(return_value=reasoning)
        orchestrator._client.execute_workflow = AsyncMock(
            return_value=async_running_response
        )

        # Mock the monitor's wait_for_completion to return a completed result
        completed_monitor_result = MonitorResult(
            execution_id="exec-002",
            status=ExecutionState.COMPLETED,
            output_data={"config_updated": True},
            total_polls=3,
        )
        orchestrator._monitor.wait_for_completion = AsyncMock(
            return_value=completed_monitor_result
        )

        request = OrchestrationRequest(
            user_input="Update DNS config",
            request_id="req-async-001",
            timeout=300,
        )

        result = await orchestrator.orchestrate(request)

        assert result.status == OrchestrationStatus.COMPLETED
        assert result.execution_id == "exec-002"
        assert result.execution_result == {"config_updated": True}
        orchestrator._monitor.wait_for_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestration_no_workflow_id(self, orchestrator):
        """Test orchestration fails when no workflow_id and reasoning doesn't recommend one."""
        reasoning = ReasoningResult(
            intent="UNKNOWN",
            confidence=0.3,
            recommended_workflow=None,
            risk_level="low",
            requires_approval=False,
        )
        orchestrator._reasoning_fn = AsyncMock(return_value=reasoning)

        request = OrchestrationRequest(
            user_input="Do something vague",
            workflow_id=None,
            request_id="req-no-wf",
        )

        result = await orchestrator.orchestrate(request)

        assert result.status == OrchestrationStatus.FAILED
        assert "No workflow_id" in result.error
        assert result.reasoning is reasoning

    @pytest.mark.asyncio
    async def test_orchestration_hitl_blocks_high_risk(self, orchestrator):
        """Test that high-risk operations are blocked pending HITL approval."""
        reasoning = ReasoningResult(
            intent="INCIDENT",
            sub_intent="system_failure",
            confidence=0.95,
            recommended_workflow="wf-incident",
            risk_level="high",
            requires_approval=True,
        )
        orchestrator._reasoning_fn = AsyncMock(return_value=reasoning)

        request = OrchestrationRequest(
            user_input="Server is down, auto-restart all services",
            request_id="req-hitl-001",
        )

        result = await orchestrator.orchestrate(request)

        assert result.status == OrchestrationStatus.PENDING
        assert "HITL approval required" in result.error
        assert result.reasoning is reasoning
        # Workflow should NOT have been executed
        orchestrator._client.execute_workflow.assert_not_called()

    @pytest.mark.asyncio
    async def test_orchestration_critical_risk_also_blocked(self, orchestrator):
        """Test that critical-risk operations are also blocked by HITL."""
        reasoning = ReasoningResult(
            intent="CHANGE",
            sub_intent="destructive_change",
            confidence=0.99,
            recommended_workflow="wf-destroy",
            risk_level="critical",
            requires_approval=True,
        )
        orchestrator._reasoning_fn = AsyncMock(return_value=reasoning)

        request = OrchestrationRequest(
            user_input="Delete all production databases",
            request_id="req-critical-001",
        )

        result = await orchestrator.orchestrate(request)

        assert result.status == OrchestrationStatus.PENDING
        assert "HITL approval required" in result.error

    @pytest.mark.asyncio
    async def test_orchestration_timeout(self, orchestrator):
        """Test orchestration times out when reasoning exceeds timeout."""
        # Simulate a reasoning function that takes too long
        async def slow_reasoning(user_input, context):
            await asyncio.sleep(10)
            return ReasoningResult(intent="QUERY")

        orchestrator._reasoning_fn = slow_reasoning

        request = OrchestrationRequest(
            user_input="What is the server status",
            timeout=0,  # Immediate timeout
            request_id="req-timeout-001",
        )

        result = await orchestrator.orchestrate(request)

        assert result.status == OrchestrationStatus.TIMEOUT
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_orchestration_workflow_not_found(self, orchestrator):
        """Test orchestration handles N8nNotFoundError from execute_workflow."""
        reasoning = ReasoningResult(
            intent="REQUEST",
            recommended_workflow="wf-nonexistent",
            risk_level="low",
            requires_approval=False,
        )
        orchestrator._reasoning_fn = AsyncMock(return_value=reasoning)
        orchestrator._client.execute_workflow = AsyncMock(
            side_effect=N8nNotFoundError("Workflow wf-nonexistent not found")
        )

        request = OrchestrationRequest(
            user_input="Reset password",
            request_id="req-notfound-001",
        )

        result = await orchestrator.orchestrate(request)

        assert result.status == OrchestrationStatus.FAILED
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_orchestration_connection_error(self, orchestrator):
        """Test orchestration handles N8nConnectionError from execute_workflow."""
        reasoning = ReasoningResult(
            intent="REQUEST",
            recommended_workflow="wf-reset",
            risk_level="low",
            requires_approval=False,
        )
        orchestrator._reasoning_fn = AsyncMock(return_value=reasoning)
        orchestrator._client.execute_workflow = AsyncMock(
            side_effect=N8nConnectionError("Connection refused")
        )

        request = OrchestrationRequest(
            user_input="Reset password",
            request_id="req-conn-err-001",
        )

        result = await orchestrator.orchestrate(request)

        assert result.status == OrchestrationStatus.FAILED
        assert "connection error" in result.error.lower()

    @pytest.mark.asyncio
    async def test_orchestration_api_error(self, orchestrator):
        """Test orchestration handles N8nApiError from execute_workflow."""
        reasoning = ReasoningResult(
            intent="REQUEST",
            recommended_workflow="wf-reset",
            risk_level="low",
            requires_approval=False,
        )
        orchestrator._reasoning_fn = AsyncMock(return_value=reasoning)
        orchestrator._client.execute_workflow = AsyncMock(
            side_effect=N8nApiError("Internal Server Error", status_code=500)
        )

        request = OrchestrationRequest(
            user_input="Reset password",
            request_id="req-api-err-001",
        )

        result = await orchestrator.orchestrate(request)

        assert result.status == OrchestrationStatus.FAILED
        assert "API error" in result.error

    @pytest.mark.asyncio
    async def test_orchestration_monitor_timeout(
        self, orchestrator, async_running_response
    ):
        """Test orchestration returns TIMEOUT when monitor reports TIMED_OUT."""
        reasoning = ReasoningResult(
            intent="CHANGE",
            recommended_workflow="wf-slow",
            risk_level="low",
            requires_approval=False,
        )
        orchestrator._reasoning_fn = AsyncMock(return_value=reasoning)
        orchestrator._client.execute_workflow = AsyncMock(
            return_value=async_running_response
        )

        timed_out_result = MonitorResult(
            execution_id="exec-002",
            status=ExecutionState.TIMED_OUT,
            error="Monitoring timed out after 60s",
            total_polls=30,
        )
        orchestrator._monitor.wait_for_completion = AsyncMock(
            return_value=timed_out_result
        )

        request = OrchestrationRequest(
            user_input="Run long migration",
            request_id="req-mon-timeout",
            timeout=300,
        )

        result = await orchestrator.orchestrate(request)

        assert result.status == OrchestrationStatus.TIMEOUT
        assert result.execution_id == "exec-002"

    @pytest.mark.asyncio
    async def test_orchestration_monitor_failure(
        self, orchestrator, async_running_response
    ):
        """Test orchestration returns FAILED when monitor reports FAILED."""
        reasoning = ReasoningResult(
            intent="CHANGE",
            recommended_workflow="wf-failing",
            risk_level="low",
            requires_approval=False,
        )
        orchestrator._reasoning_fn = AsyncMock(return_value=reasoning)
        orchestrator._client.execute_workflow = AsyncMock(
            return_value=async_running_response
        )

        failed_result = MonitorResult(
            execution_id="exec-002",
            status=ExecutionState.FAILED,
            error="Workflow node error: Invalid API key",
            total_polls=5,
        )
        orchestrator._monitor.wait_for_completion = AsyncMock(
            return_value=failed_result
        )

        request = OrchestrationRequest(
            user_input="Run broken workflow",
            request_id="req-mon-fail",
            timeout=300,
        )

        result = await orchestrator.orchestrate(request)

        assert result.status == OrchestrationStatus.FAILED
        assert "Invalid API key" in result.error

    @pytest.mark.asyncio
    async def test_orchestration_uses_request_workflow_id_over_reasoning(
        self, orchestrator, sync_success_response
    ):
        """Test that explicit workflow_id on request takes precedence."""
        reasoning = ReasoningResult(
            intent="REQUEST",
            recommended_workflow="wf-recommended",
            risk_level="low",
            requires_approval=False,
        )
        orchestrator._reasoning_fn = AsyncMock(return_value=reasoning)
        orchestrator._client.execute_workflow = AsyncMock(
            return_value=sync_success_response
        )

        request = OrchestrationRequest(
            user_input="Reset password",
            workflow_id="wf-explicit",
            request_id="req-explicit-wf",
        )

        await orchestrator.orchestrate(request)

        # Verify execute_workflow was called with the explicit workflow_id
        call_args = orchestrator._client.execute_workflow.call_args
        assert call_args.kwargs["workflow_id"] == "wf-explicit"

    @pytest.mark.asyncio
    async def test_orchestration_cleans_up_active_state(self, orchestrator):
        """Test that orchestration cleans up _active_orchestrations after completion."""
        reasoning = ReasoningResult(
            intent="UNKNOWN",
            recommended_workflow=None,
            risk_level="low",
            requires_approval=False,
        )
        orchestrator._reasoning_fn = AsyncMock(return_value=reasoning)

        request = OrchestrationRequest(
            user_input="vague input",
            request_id="req-cleanup",
        )

        assert orchestrator.get_active_count() == 0

        await orchestrator.orchestrate(request)

        # After orchestration completes, state should be cleaned up
        assert orchestrator.get_status("req-cleanup") is None
        assert orchestrator.get_active_count() == 0


# ---------------------------------------------------------------------------
# TestCallbackHandling
# ---------------------------------------------------------------------------


class TestCallbackHandling:
    """Tests for handle_callback and get_status methods."""

    def test_handle_callback_unknown_request(self, orchestrator):
        """Test that callback for unknown request_id returns False."""
        result = orchestrator.handle_callback(
            request_id="nonexistent-req",
            callback_data={"status": "success"},
        )

        assert result is False

    def test_handle_callback_active_request(self, orchestrator):
        """Test that callback for an active request_id returns True."""
        # Simulate an active orchestration by manually adding to the dict
        orchestrator._active_orchestrations["active-req"] = (
            OrchestrationStatus.MONITORING
        )

        result = orchestrator.handle_callback(
            request_id="active-req",
            callback_data={"status": "success", "data": {"key": "value"}},
        )

        assert result is True
        assert "active-req" in orchestrator._callback_results
        assert orchestrator._callback_results["active-req"]["status"] == "success"

    def test_get_status(self, orchestrator):
        """Test get_status returns correct status or None."""
        # No active orchestrations
        assert orchestrator.get_status("unknown-id") is None

        # Add an active orchestration
        orchestrator._active_orchestrations["test-id"] = (
            OrchestrationStatus.EXECUTING
        )
        assert orchestrator.get_status("test-id") == OrchestrationStatus.EXECUTING

        # Different status
        orchestrator._active_orchestrations["test-id"] = (
            OrchestrationStatus.MONITORING
        )
        assert orchestrator.get_status("test-id") == OrchestrationStatus.MONITORING


# ---------------------------------------------------------------------------
# TestLifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    """Tests for orchestrator lifecycle management."""

    @pytest.mark.asyncio
    async def test_context_manager(self, n8n_config, monitor_config):
        """Test async context manager calls close on exit."""
        async with N8nOrchestrator(
            config=n8n_config, monitor_config=monitor_config
        ) as orch:
            assert isinstance(orch, N8nOrchestrator)
            # Manually inject some state to verify close() clears it
            orch._active_orchestrations["test"] = OrchestrationStatus.PENDING
            orch._progress_callbacks["test"] = [lambda p: None]
            orch._callback_results["test"] = {"status": "done"}
            # Mock client.close to avoid real HTTP teardown
            orch._client.close = AsyncMock()

        # After exiting context, all state should be cleared
        assert len(orch._active_orchestrations) == 0
        assert len(orch._progress_callbacks) == 0
        assert len(orch._callback_results) == 0
        orch._client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self, orchestrator):
        """Test close() clears all internal state and closes client."""
        # Set up some state
        orchestrator._active_orchestrations["a"] = OrchestrationStatus.EXECUTING
        orchestrator._progress_callbacks["a"] = [lambda p: None]
        orchestrator._callback_results["a"] = {"data": "test"}

        await orchestrator.close()

        assert len(orchestrator._active_orchestrations) == 0
        assert len(orchestrator._progress_callbacks) == 0
        assert len(orchestrator._callback_results) == 0
        orchestrator._client.close.assert_called_once()
