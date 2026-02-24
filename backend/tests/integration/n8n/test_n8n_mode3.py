"""Integration Tests for n8n Mode 3 — Bidirectional Orchestration & Callback Endpoint.

Sprint 125: n8n Mode 3 — IPA reasoning + n8n workflow execution

Tests cover:
    - Full orchestration lifecycle (request -> reasoning -> translate -> execute -> complete)
    - Custom reasoning function injection
    - High-risk orchestration blocking (HITL approval)
    - Progress callback forwarding and history tracking
    - Multiple concurrent orchestrations
    - Callback POST endpoint acceptance
    - Callback GET result retrieval
    - Callback 404 for unknown orchestration
    - HMAC signature verification on callback
    - Invalid payload rejection (422)
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1.n8n.routes import router
from src.api.v1.n8n.schemas import N8nCallbackPayload
from src.integrations.mcp.servers.n8n.client import N8nApiClient, N8nConfig
from src.integrations.n8n.monitor import (
    ExecutionMonitor,
    ExecutionProgress,
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
    """Create test n8n configuration."""
    return N8nConfig(
        base_url="http://test:5678",
        api_key="test-key",
        timeout=5,
        max_retries=1,
    )


@pytest.fixture
def monitor_config():
    """Create a fast monitor configuration for tests."""
    return MonitorConfig(
        poll_interval=0.01,
        max_poll_interval=0.05,
        backoff_factor=1.1,
        default_timeout=5.0,
        max_retries_on_error=2,
        progress_update_interval=0.0,
    )


@pytest.fixture
def mock_n8n_client(n8n_config):
    """Create a mock N8nApiClient with pre-configured responses."""
    client = N8nApiClient(n8n_config)

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.json.return_value = {}
    client._client.request = AsyncMock(return_value=mock_response)

    return client


@pytest.fixture
def test_client():
    """Create test client with the n8n router mounted."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


def _make_execute_response(execution_id: str = "exec-001", exec_status: str = "success"):
    """Helper: build a mock httpx.Response for execute_workflow."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.headers = {}
    resp.json.return_value = {
        "data": {
            "executionId": execution_id,
            "status": exec_status,
            "data": {"result": "ok"},
        },
    }
    return resp


async def _custom_reasoning(user_input: str, context: dict) -> ReasoningResult:
    """Custom reasoning function for testing injection."""
    return ReasoningResult(
        intent="CUSTOM_INTENT",
        sub_intent="custom_sub",
        confidence=0.99,
        recommended_workflow="wf-custom-001",
        workflow_input={"custom_key": user_input},
        risk_level="low",
        requires_approval=False,
        reasoning_metadata={"source": "custom_fn"},
    )


async def _high_risk_reasoning(user_input: str, context: dict) -> ReasoningResult:
    """Reasoning function that always returns high risk."""
    return ReasoningResult(
        intent="CHANGE",
        sub_intent="dangerous_change",
        confidence=0.95,
        recommended_workflow="wf-danger-001",
        workflow_input={"input": user_input},
        risk_level="critical",
        requires_approval=True,
        reasoning_metadata={"source": "high_risk_fn"},
    )


# ---------------------------------------------------------------------------
# TestMode3OrchestratorE2E
# ---------------------------------------------------------------------------


class TestMode3OrchestratorE2E:
    """End-to-end tests for Mode 3 bidirectional orchestration."""

    @pytest.mark.asyncio
    async def test_full_orchestration_sync(self, n8n_config, monitor_config):
        """Test the complete synchronous orchestration lifecycle.

        Flow: request -> reasoning -> translate -> execute -> complete.
        When the n8n execution returns status=success synchronously,
        the orchestrator should skip polling and return COMPLETED directly.
        """
        orchestrator = N8nOrchestrator(
            config=n8n_config,
            monitor_config=monitor_config,
        )

        # Mock the internal client's execute_workflow to return success synchronously
        orchestrator._client._client.request = AsyncMock(
            return_value=_make_execute_response("exec-sync-001", "success")
        )

        request = OrchestrationRequest(
            user_input="Check status of server web-01",
            context={"environment": "production"},
            workflow_id="wf-status-check",
            timeout=30,
        )

        result = await orchestrator.orchestrate(request)

        # Verify final result
        assert result.status == OrchestrationStatus.COMPLETED
        assert result.request_id == request.request_id
        assert result.reasoning is not None
        assert result.reasoning.intent == "QUERY"
        assert result.execution_id == "exec-sync-001"
        assert result.execution_result is not None
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.duration_ms is not None
        assert result.duration_ms >= 0

        # Verify progress history covers all phases
        phases_seen = [entry["phase"] for entry in result.progress_history]
        assert "reasoning" in phases_seen
        assert "translation" in phases_seen
        assert "execution" in phases_seen

        await orchestrator.close()

    @pytest.mark.asyncio
    async def test_orchestration_with_custom_reasoning_fn(
        self, n8n_config, monitor_config
    ):
        """Test orchestration with an injected custom reasoning function."""
        orchestrator = N8nOrchestrator(
            config=n8n_config,
            monitor_config=monitor_config,
            reasoning_fn=_custom_reasoning,
        )

        orchestrator._client._client.request = AsyncMock(
            return_value=_make_execute_response("exec-custom-001", "success")
        )

        request = OrchestrationRequest(
            user_input="Do something custom",
            context={"source": "test"},
            timeout=30,
        )

        result = await orchestrator.orchestrate(request)

        assert result.status == OrchestrationStatus.COMPLETED
        assert result.reasoning is not None
        assert result.reasoning.intent == "CUSTOM_INTENT"
        assert result.reasoning.sub_intent == "custom_sub"
        assert result.reasoning.confidence == 0.99
        assert result.reasoning.reasoning_metadata["source"] == "custom_fn"
        # The custom reasoning recommends wf-custom-001
        assert result.execution_id == "exec-custom-001"

        await orchestrator.close()

    @pytest.mark.asyncio
    async def test_orchestration_high_risk_blocks(self, n8n_config, monitor_config):
        """Test that high/critical risk operations are blocked pending HITL approval.

        The orchestrator should return PENDING status with an error message
        indicating that HITL approval is required, and should NOT execute
        the n8n workflow.
        """
        orchestrator = N8nOrchestrator(
            config=n8n_config,
            monitor_config=monitor_config,
            reasoning_fn=_high_risk_reasoning,
        )

        # The execute_workflow should never be called for high-risk
        orchestrator._client.execute_workflow = AsyncMock(
            side_effect=AssertionError("Should not execute high-risk workflow")
        )

        request = OrchestrationRequest(
            user_input="Delete all production databases",
            context={"environment": "production"},
            workflow_id="wf-danger-001",
            timeout=30,
        )

        result = await orchestrator.orchestrate(request)

        assert result.status == OrchestrationStatus.PENDING
        assert result.reasoning is not None
        assert result.reasoning.risk_level == "critical"
        assert result.reasoning.requires_approval is True
        assert result.error is not None
        assert "HITL" in result.error or "approval" in result.error.lower()
        # Execution should not have happened
        assert result.execution_id is None
        orchestrator._client.execute_workflow.assert_not_called()

        await orchestrator.close()

    @pytest.mark.asyncio
    async def test_orchestration_with_progress_callback(
        self, n8n_config, monitor_config
    ):
        """Test that progress history accumulates entries during orchestration.

        Even for synchronous completions, the progress_history list should
        contain reasoning/translation/execution phase entries.
        """
        orchestrator = N8nOrchestrator(
            config=n8n_config,
            monitor_config=monitor_config,
        )

        orchestrator._client._client.request = AsyncMock(
            return_value=_make_execute_response("exec-progress-001", "success")
        )

        request = OrchestrationRequest(
            user_input="Check info about network segment",
            context={},
            workflow_id="wf-info-check",
            timeout=30,
        )

        result = await orchestrator.orchestrate(request)

        assert result.status == OrchestrationStatus.COMPLETED
        assert len(result.progress_history) >= 3

        # Validate structure of progress entries
        for entry in result.progress_history:
            assert "phase" in entry
            assert "status" in entry
            assert "timestamp" in entry

        # Verify reasoning phase entries
        reasoning_entries = [
            e for e in result.progress_history if e["phase"] == "reasoning"
        ]
        assert len(reasoning_entries) >= 2  # started + completed
        reasoning_completed = [
            e for e in reasoning_entries if e["status"] == "completed"
        ]
        assert len(reasoning_completed) == 1
        assert "intent" in reasoning_completed[0]
        assert "confidence" in reasoning_completed[0]

        await orchestrator.close()

    @pytest.mark.asyncio
    async def test_multiple_concurrent_orchestrations(
        self, n8n_config, monitor_config
    ):
        """Test running multiple orchestrations concurrently.

        Each orchestration should complete independently with its own
        request_id, reasoning result, and execution result.
        """
        orchestrator = N8nOrchestrator(
            config=n8n_config,
            monitor_config=monitor_config,
        )

        # Each call returns a unique execution ID based on call count
        call_count = 0

        def _make_response(**kwargs):
            nonlocal call_count
            call_count += 1
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.headers = {}
            resp.json.return_value = {
                "data": {
                    "executionId": f"exec-concurrent-{call_count:03d}",
                    "status": "success",
                    "data": {"result": f"output-{call_count}"},
                },
            }
            return resp

        orchestrator._client._client.request = AsyncMock(side_effect=_make_response)

        requests = [
            OrchestrationRequest(
                user_input=f"Check status of server-{i}",
                context={"index": i},
                workflow_id="wf-status-check",
                timeout=30,
            )
            for i in range(5)
        ]

        results = await asyncio.gather(
            *[orchestrator.orchestrate(req) for req in requests]
        )

        assert len(results) == 5

        request_ids = set()
        for result in results:
            assert result.status == OrchestrationStatus.COMPLETED
            assert result.reasoning is not None
            assert result.execution_id is not None
            assert result.request_id not in request_ids, "Duplicate request_id detected"
            request_ids.add(result.request_id)

        # All orchestrations cleaned up
        assert orchestrator.get_active_count() == 0

        await orchestrator.close()


# ---------------------------------------------------------------------------
# TestCallbackEndpointE2E
# ---------------------------------------------------------------------------


class TestCallbackEndpointE2E:
    """End-to-end tests for the n8n callback API endpoint."""

    def test_callback_accepted(self, test_client):
        """Test POST /api/v1/n8n/callback with a valid payload returns success."""
        payload = {
            "orchestration_id": "orch-test-001",
            "execution_id": "exec-test-001",
            "status": "success",
            "data": {"output": "workflow completed", "items_processed": 42},
            "metadata": {"workflow_name": "password-reset"},
        }

        response = test_client.post("/api/v1/n8n/callback", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["orchestration_id"] == "orch-test-001"
        assert "accepted" in body["message"].lower() or "callback" in body["message"].lower()

    def test_callback_get_result(self, test_client):
        """Test POST then GET /api/v1/n8n/callback/{id} retrieves stored data."""
        orchestration_id = "orch-get-test-001"

        # Step 1: POST the callback
        post_payload = {
            "orchestration_id": orchestration_id,
            "execution_id": "exec-get-001",
            "status": "success",
            "data": {"result_key": "result_value"},
            "progress": 100.0,
            "metadata": {"source": "test"},
        }
        post_response = test_client.post("/api/v1/n8n/callback", json=post_payload)
        assert post_response.status_code == 200

        # Step 2: GET the result
        get_response = test_client.get(
            f"/api/v1/n8n/callback/{orchestration_id}"
        )
        assert get_response.status_code == 200

        body = get_response.json()
        assert body["orchestration_id"] == orchestration_id
        assert "callback" in body
        callback_data = body["callback"]
        assert callback_data["execution_id"] == "exec-get-001"
        assert callback_data["status"] == "success"
        assert callback_data["data"]["result_key"] == "result_value"
        assert callback_data["progress"] == 100.0
        assert "received_at" in callback_data

    def test_callback_get_not_found(self, test_client):
        """Test GET /api/v1/n8n/callback/{id} for a non-existent orchestration returns 404."""
        response = test_client.get(
            "/api/v1/n8n/callback/non-existent-orchestration-id"
        )

        assert response.status_code == 404
        body = response.json()
        assert "detail" in body
        assert "non-existent-orchestration-id" in body["detail"]

    @patch.dict("os.environ", {}, clear=False)
    def test_callback_hmac_verification(self, test_client):
        """Test HMAC signature verification on the callback endpoint.

        When N8N_WEBHOOK_HMAC_SECRET is configured, requests without
        a valid X-N8N-Signature header should be rejected with 401.
        """
        import hashlib
        import hmac as hmac_module
        import json

        # Create a dedicated app + client with HMAC configured
        with patch(
            "src.api.v1.n8n.routes._WEBHOOK_HMAC_SECRET",
            "test-hmac-secret-key",
        ):
            hmac_app = FastAPI()
            # Re-import the router module to pick up the patched secret
            # Since _verify_hmac_signature reads the module-level variable,
            # patching it before the request is sufficient.
            hmac_app.include_router(router, prefix="/api/v1")
            hmac_client = TestClient(hmac_app)

            payload = {
                "orchestration_id": "orch-hmac-001",
                "execution_id": "exec-hmac-001",
                "status": "success",
                "data": {},
            }

            # Request WITHOUT signature should be rejected
            response_no_sig = hmac_client.post(
                "/api/v1/n8n/callback",
                json=payload,
            )
            assert response_no_sig.status_code == 401

            # Request WITH valid signature should be accepted
            payload_bytes = json.dumps(payload).encode("utf-8")
            expected_sig = hmac_module.new(
                "test-hmac-secret-key".encode("utf-8"),
                payload_bytes,
                hashlib.sha256,
            ).hexdigest()

            response_valid = hmac_client.post(
                "/api/v1/n8n/callback",
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-N8N-Signature": f"sha256={expected_sig}",
                },
            )
            assert response_valid.status_code == 200
            assert response_valid.json()["success"] is True

    def test_callback_invalid_payload(self, test_client):
        """Test POST /api/v1/n8n/callback with missing required fields returns 422."""
        # Missing orchestration_id, execution_id, status
        invalid_payloads = [
            {},
            {"orchestration_id": "orch-001"},
            {"orchestration_id": "orch-001", "execution_id": "exec-001"},
            {"execution_id": "exec-001", "status": "success"},
        ]

        for payload in invalid_payloads:
            response = test_client.post("/api/v1/n8n/callback", json=payload)
            assert response.status_code == 422, (
                f"Expected 422 for payload {payload}, got {response.status_code}"
            )
