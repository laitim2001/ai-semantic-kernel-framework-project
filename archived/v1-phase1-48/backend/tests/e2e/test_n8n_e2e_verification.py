"""Sprint 127 Story 127-1: Comprehensive n8n End-to-End Verification Tests.

Covers all three n8n integration modes with full mocked I/O:
    - Mode 1: IPA triggers n8n workflow (N8nApiClient)
    - Mode 2: n8n triggers IPA via webhook (routes + HMAC)
    - Mode 3: Bidirectional orchestration (N8nOrchestrator)
    - Fault tolerance: retries, timeouts, error escalation
    - Concurrency: parallel workflow triggers and orchestrations

Total: 29 tests across 5 test classes.

Author: IPA Platform Team
Sprint: 127 (Phase 34)
"""

import asyncio
import hashlib
import hmac as hmac_mod
import logging
from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.integrations.mcp.servers.n8n.client import (
    ExecutionStatus,
    N8nApiClient,
    N8nApiError,
    N8nAuthenticationError,
    N8nConfig,
    N8nConnectionError,
    N8nNotFoundError,
    N8nRateLimitError,
)
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

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_config(
    max_retries: int = 3,
    timeout: int = 30,
    retry_base_delay: float = 0.001,
) -> N8nConfig:
    """Create an N8nConfig suitable for fast unit-level E2E tests."""
    return N8nConfig(
        base_url="http://n8n-test:5678",
        api_key="test-api-key-e2e",
        timeout=timeout,
        max_retries=max_retries,
        retry_base_delay=retry_base_delay,
    )


def _mock_httpx_response(
    status_code: int = 200,
    json_data: Any = None,
    text: str = "",
    headers: Dict[str, str] | None = None,
) -> MagicMock:
    """Build a mock httpx.Response with the given properties."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.text = text or (str(json_data) if json_data else "")
    resp.content = resp.text.encode()
    resp.headers = headers or {}
    return resp


def _fast_monitor_config() -> MonitorConfig:
    """MonitorConfig with minimal delays for testing."""
    return MonitorConfig(
        poll_interval=0.01,
        max_poll_interval=0.05,
        backoff_factor=1.0,
        default_timeout=0.5,
        max_retries_on_error=2,
        progress_update_interval=0.0,
    )


# ===========================================================================
# Mode 1: IPA triggers n8n workflow
# ===========================================================================


class TestN8nMode1IpaTriggers:
    """Mode 1 verification: IPA-side N8nApiClient operations."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_mode1_trigger_workflow_success(self) -> None:
        """Execute a workflow and verify the execution result is returned."""
        config = _make_config()
        client = N8nApiClient(config)

        execution_payload = {
            "data": {
                "executionId": "exec-001",
                "status": "success",
                "data": {"output": "password_reset_complete"},
            }
        }
        mock_resp = _mock_httpx_response(200, execution_payload)

        with patch.object(
            client._client, "request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.return_value = mock_resp
            result = await client.execute_workflow(
                "wf-reset-pwd", data={"user": "john"}
            )

        assert result["data"]["executionId"] == "exec-001"
        assert result["data"]["status"] == "success"
        mock_req.assert_awaited_once()
        call_kwargs = mock_req.call_args
        assert call_kwargs.kwargs["method"] == "POST"
        assert "/workflows/wf-reset-pwd/execute" in call_kwargs.kwargs["url"]

        await client.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_mode1_list_workflows(self) -> None:
        """List workflows and verify data structure returned."""
        config = _make_config()
        client = N8nApiClient(config)

        workflows_payload = {
            "data": [
                {"id": "wf-1", "name": "Incident Auto-Remediation", "active": True},
                {"id": "wf-2", "name": "Password Reset", "active": False},
            ],
            "nextCursor": None,
        }
        mock_resp = _mock_httpx_response(200, workflows_payload)

        with patch.object(
            client._client, "request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.return_value = mock_resp
            result = await client.list_workflows(active=True, limit=10)

        assert len(result["data"]) == 2
        assert result["data"][0]["id"] == "wf-1"
        assert result["data"][1]["name"] == "Password Reset"
        assert result["nextCursor"] is None

        await client.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_mode1_get_workflow_details(self) -> None:
        """Retrieve a single workflow definition and verify its fields."""
        config = _make_config()
        client = N8nApiClient(config)

        workflow_detail = {
            "id": "wf-1",
            "name": "Incident Auto-Remediation",
            "active": True,
            "nodes": [{"type": "webhook"}, {"type": "httpRequest"}],
            "connections": {"webhook": {"main": [[{"node": "httpRequest"}]]}},
        }
        mock_resp = _mock_httpx_response(200, workflow_detail)

        with patch.object(
            client._client, "request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.return_value = mock_resp
            result = await client.get_workflow("wf-1")

        assert result["id"] == "wf-1"
        assert result["active"] is True
        assert len(result["nodes"]) == 2

        await client.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_mode1_activate_workflow(self) -> None:
        """Activate a workflow and verify the updated status."""
        config = _make_config()
        client = N8nApiClient(config)

        updated_wf = {"id": "wf-1", "active": True, "name": "Incident AR"}
        mock_resp = _mock_httpx_response(200, updated_wf)

        with patch.object(
            client._client, "request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.return_value = mock_resp
            result = await client.activate_workflow("wf-1", active=True)

        assert result["active"] is True
        call_kwargs = mock_req.call_args
        assert call_kwargs.kwargs["method"] == "PATCH"
        assert call_kwargs.kwargs["json"] == {"active": True}

        await client.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_mode1_get_execution_status(self) -> None:
        """Get execution details and verify status tracking fields."""
        config = _make_config()
        client = N8nApiClient(config)

        execution_detail = {
            "id": "exec-500",
            "status": "running",
            "workflowId": "wf-1",
            "startedAt": "2026-02-25T10:00:00.000Z",
        }
        mock_resp = _mock_httpx_response(200, execution_detail)

        with patch.object(
            client._client, "request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.return_value = mock_resp
            result = await client.get_execution("exec-500")

        assert result["id"] == "exec-500"
        assert result["status"] == "running"
        assert result["workflowId"] == "wf-1"

        await client.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_mode1_list_executions_filtered(self) -> None:
        """List executions with workflow_id and status filters applied."""
        config = _make_config()
        client = N8nApiClient(config)

        executions_payload = {
            "data": [
                {"id": "exec-10", "status": "error", "workflowId": "wf-3"},
                {"id": "exec-11", "status": "error", "workflowId": "wf-3"},
            ],
            "nextCursor": None,
        }
        mock_resp = _mock_httpx_response(200, executions_payload)

        with patch.object(
            client._client, "request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.return_value = mock_resp
            result = await client.list_executions(
                workflow_id="wf-3", status="error", limit=5
            )

        assert len(result["data"]) == 2
        assert all(e["status"] == "error" for e in result["data"])

        call_kwargs = mock_req.call_args
        params = call_kwargs.kwargs.get("params", {})
        assert params["workflowId"] == "wf-3"
        assert params["status"] == "error"
        assert params["limit"] == 5

        await client.close()


# ===========================================================================
# Mode 2: n8n triggers IPA via webhook
# ===========================================================================


class TestN8nMode2WebhookTrigger:
    """Mode 2 verification: n8n sends payload to IPA webhook."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_mode2_webhook_receives_payload(self) -> None:
        """Webhook processes an incoming n8n analyze-action payload."""
        from src.api.v1.n8n.routes import _process_webhook
        from src.api.v1.n8n.schemas import N8nWebhookPayload, WebhookAction

        payload = N8nWebhookPayload(
            workflow_id="wf-sn-incident",
            execution_id="exec-999",
            action=WebhookAction.ANALYZE,
            data={"incident_id": "INC0012345", "description": "Server CPU spike"},
        )

        result = await _process_webhook(payload)

        assert result["action"] == "analyze"
        assert "analysis" in result
        assert result["analysis"]["source_workflow"] == "wf-sn-incident"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_mode2_webhook_authentication_valid(self) -> None:
        """Valid HMAC signature is accepted by the verification function."""
        from src.api.v1.n8n import routes as n8n_routes

        secret = "test-webhook-secret-e2e"
        original_secret = n8n_routes._WEBHOOK_HMAC_SECRET
        try:
            n8n_routes._WEBHOOK_HMAC_SECRET = secret

            body = b'{"workflow_id":"wf-1","action":"analyze"}'
            expected_sig = hmac_mod.new(
                secret.encode("utf-8"), body, hashlib.sha256
            ).hexdigest()
            signature = f"sha256={expected_sig}"

            is_valid = n8n_routes._verify_hmac_signature(body, signature)
            assert is_valid is True
        finally:
            n8n_routes._WEBHOOK_HMAC_SECRET = original_secret

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_mode2_webhook_authentication_invalid(self) -> None:
        """Invalid HMAC signature is rejected."""
        from src.api.v1.n8n import routes as n8n_routes

        secret = "test-webhook-secret-e2e"
        original_secret = n8n_routes._WEBHOOK_HMAC_SECRET
        try:
            n8n_routes._WEBHOOK_HMAC_SECRET = secret

            body = b'{"workflow_id":"wf-1","action":"analyze"}'
            invalid_signature = "sha256=0000000000000000000000000000000000000000000000"

            is_valid = n8n_routes._verify_hmac_signature(body, invalid_signature)
            assert is_valid is False

            is_valid_none = n8n_routes._verify_hmac_signature(body, None)
            assert is_valid_none is False
        finally:
            n8n_routes._WEBHOOK_HMAC_SECRET = original_secret

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_mode2_webhook_payload_transform(self) -> None:
        """Webhook payload transforms correctly from n8n format to IPA handler."""
        from src.api.v1.n8n.routes import _process_webhook
        from src.api.v1.n8n.schemas import N8nWebhookPayload, WebhookAction

        payload = N8nWebhookPayload(
            workflow_id="wf-ticket-triage",
            execution_id="exec-T1",
            action=WebhookAction.EXECUTE,
            data={
                "ticket_id": "TICKET-500",
                "priority": "critical",
                "category": "infrastructure",
            },
            callback_url="http://n8n:5678/webhook/ipa-result",
            metadata={"source": "servicenow"},
        )

        result = await _process_webhook(payload)

        assert result["action"] == "execute"
        assert "execution" in result
        assert result["execution"]["source_workflow"] == "wf-ticket-triage"
        assert "ticket_id" in result["execution"]["data_keys"]
        assert "priority" in result["execution"]["data_keys"]


# ===========================================================================
# Mode 3: Bidirectional orchestration
# ===========================================================================


class TestN8nMode3Orchestration:
    """Mode 3 verification: IPA reasoning + n8n execution + monitoring."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_mode3_full_orchestration_success(self) -> None:
        """Full 6-phase orchestration completes successfully end-to-end."""
        config = _make_config()
        monitor_cfg = _fast_monitor_config()

        async def mock_reasoning(
            user_input: str, context: Dict[str, Any]
        ) -> ReasoningResult:
            return ReasoningResult(
                intent="REQUEST",
                sub_intent="password_reset",
                confidence=0.95,
                recommended_workflow="wf-pwd-reset",
                workflow_input={"user": "john"},
                risk_level="low",
                requires_approval=False,
            )

        orchestrator = N8nOrchestrator(
            config=config,
            monitor_config=monitor_cfg,
            reasoning_fn=mock_reasoning,
        )

        # Mock execute_workflow to return synchronous success
        exec_response = {
            "data": {
                "executionId": "exec-orch-001",
                "status": "success",
                "data": {"result": "password_reset_done"},
            }
        }
        mock_exec_resp = _mock_httpx_response(200, exec_response)

        with patch.object(
            orchestrator._client._client, "request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.return_value = mock_exec_resp

            request = OrchestrationRequest(
                user_input="Reset password for user john",
                request_id="orch-test-001",
            )
            result = await orchestrator.orchestrate(request)

        assert result.status == OrchestrationStatus.COMPLETED
        assert result.request_id == "orch-test-001"
        assert result.reasoning is not None
        assert result.reasoning.intent == "REQUEST"
        assert result.reasoning.confidence == 0.95
        assert result.execution_id == "exec-orch-001"
        assert result.execution_result is not None
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.duration_ms is not None and result.duration_ms >= 0

        await orchestrator.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_mode3_orchestration_with_custom_reasoning(self) -> None:
        """Custom reasoning function drives workflow selection."""
        config = _make_config()
        monitor_cfg = _fast_monitor_config()

        async def custom_reasoning(
            user_input: str, context: Dict[str, Any]
        ) -> ReasoningResult:
            return ReasoningResult(
                intent="INCIDENT",
                sub_intent="server_outage",
                confidence=0.88,
                recommended_workflow="wf-incident-auto-remediate",
                workflow_input={"server": "prod-db-01"},
                risk_level="low",
                requires_approval=False,
            )

        orchestrator = N8nOrchestrator(
            config=config,
            monitor_config=monitor_cfg,
            reasoning_fn=custom_reasoning,
        )

        exec_response = {
            "data": {
                "executionId": "exec-incident-01",
                "status": "success",
                "data": {"remediation": "service_restarted"},
            }
        }
        mock_resp = _mock_httpx_response(200, exec_response)

        with patch.object(
            orchestrator._client._client, "request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.return_value = mock_resp

            request = OrchestrationRequest(
                user_input="prod-db-01 is down",
                request_id="orch-custom-001",
            )
            result = await orchestrator.orchestrate(request)

        assert result.status == OrchestrationStatus.COMPLETED
        assert result.reasoning is not None
        assert result.reasoning.intent == "INCIDENT"
        assert result.reasoning.recommended_workflow == "wf-incident-auto-remediate"

        # Verify that execute_workflow was called with the correct workflow
        call_kwargs = mock_req.call_args
        assert "wf-incident-auto-remediate" in call_kwargs.kwargs["url"]

        await orchestrator.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_mode3_orchestration_hitl_blocks_high_risk(self) -> None:
        """High-risk reasoning triggers HITL block with PENDING status."""
        config = _make_config()
        monitor_cfg = _fast_monitor_config()

        async def high_risk_reasoning(
            user_input: str, context: Dict[str, Any]
        ) -> ReasoningResult:
            return ReasoningResult(
                intent="CHANGE",
                sub_intent="production_deployment",
                confidence=0.92,
                recommended_workflow="wf-deploy-prod",
                workflow_input={"version": "v2.0"},
                risk_level="high",
                requires_approval=True,
            )

        orchestrator = N8nOrchestrator(
            config=config,
            monitor_config=monitor_cfg,
            reasoning_fn=high_risk_reasoning,
        )

        request = OrchestrationRequest(
            user_input="Deploy v2.0 to production",
            request_id="orch-hitl-001",
        )
        result = await orchestrator.orchestrate(request)

        assert result.status == OrchestrationStatus.PENDING
        assert result.reasoning is not None
        assert result.reasoning.risk_level == "high"
        assert result.reasoning.requires_approval is True
        assert result.error is not None
        assert "HITL" in result.error
        # Workflow should NOT have been executed
        assert result.execution_id is None

        await orchestrator.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_mode3_orchestration_no_workflow_id(self) -> None:
        """No workflow_id from reasoning returns FAILED status."""
        config = _make_config()
        monitor_cfg = _fast_monitor_config()

        async def no_workflow_reasoning(
            user_input: str, context: Dict[str, Any]
        ) -> ReasoningResult:
            return ReasoningResult(
                intent="UNKNOWN",
                sub_intent="",
                confidence=0.3,
                recommended_workflow=None,
                risk_level="low",
                requires_approval=False,
            )

        orchestrator = N8nOrchestrator(
            config=config,
            monitor_config=monitor_cfg,
            reasoning_fn=no_workflow_reasoning,
        )

        request = OrchestrationRequest(
            user_input="Something ambiguous",
            request_id="orch-nowf-001",
        )
        result = await orchestrator.orchestrate(request)

        assert result.status == OrchestrationStatus.FAILED
        assert result.error is not None
        assert "No workflow_id" in result.error

        await orchestrator.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_mode3_progress_history_recorded(self) -> None:
        """Progress history captures all phase entries during orchestration."""
        config = _make_config()
        monitor_cfg = _fast_monitor_config()

        async def mock_reasoning(
            user_input: str, context: Dict[str, Any]
        ) -> ReasoningResult:
            return ReasoningResult(
                intent="QUERY",
                sub_intent="status_check",
                confidence=0.85,
                recommended_workflow="wf-status-query",
                workflow_input={"server": "web-01"},
                risk_level="low",
                requires_approval=False,
            )

        orchestrator = N8nOrchestrator(
            config=config,
            monitor_config=monitor_cfg,
            reasoning_fn=mock_reasoning,
        )

        exec_response = {
            "data": {
                "executionId": "exec-prog-001",
                "status": "success",
                "data": {"server_status": "healthy"},
            }
        }
        mock_resp = _mock_httpx_response(200, exec_response)

        with patch.object(
            orchestrator._client._client, "request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.return_value = mock_resp

            request = OrchestrationRequest(
                user_input="Check status of web-01",
                request_id="orch-progress-001",
            )
            result = await orchestrator.orchestrate(request)

        assert result.status == OrchestrationStatus.COMPLETED
        history = result.progress_history
        assert len(history) >= 3, f"Expected >=3 progress entries, got {len(history)}"

        phases = [entry["phase"] for entry in history]
        assert "reasoning" in phases, "reasoning phase missing from history"
        assert "translation" in phases, "translation phase missing from history"
        assert "execution" in phases, "execution phase missing from history"

        reasoning_entries = [e for e in history if e["phase"] == "reasoning"]
        assert any(e.get("status") == "started" for e in reasoning_entries)
        assert any(e.get("status") == "completed" for e in reasoning_entries)

        await orchestrator.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_mode3_callback_handling(self) -> None:
        """handle_callback stores data for an active orchestration."""
        config = _make_config()
        orchestrator = N8nOrchestrator(config=config)

        request_id = "orch-cb-001"
        # Simulate an active orchestration by injecting into internal state
        orchestrator._active_orchestrations[request_id] = OrchestrationStatus.MONITORING

        callback_data = {
            "status": "success",
            "execution_id": "exec-cb-001",
            "data": {"output": "remediation_complete"},
        }

        accepted = orchestrator.handle_callback(request_id, callback_data)

        assert accepted is True
        assert request_id in orchestrator._callback_results
        stored = orchestrator._callback_results[request_id]
        assert stored["status"] == "success"

        await orchestrator.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_mode3_callback_unknown_request(self) -> None:
        """handle_callback returns False for an unknown request_id."""
        config = _make_config()
        orchestrator = N8nOrchestrator(config=config)

        accepted = orchestrator.handle_callback(
            "nonexistent-request",
            {"status": "success"},
        )

        assert accepted is False

        await orchestrator.close()


# ===========================================================================
# Fault tolerance
# ===========================================================================


class TestN8nFaultTolerance:
    """Fault tolerance: retries, errors, timeouts, cancellation."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_connection_error_retry(self) -> None:
        """Client retries on transient connection errors before succeeding."""
        config = _make_config(max_retries=3, retry_base_delay=0.001)
        client = N8nApiClient(config)

        success_resp = _mock_httpx_response(
            200, {"data": [{"id": "wf-1"}], "nextCursor": None}
        )

        call_count = 0

        async def side_effect(**kwargs: Any) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("Connection refused")
            return success_resp

        with patch.object(
            client._client, "request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.side_effect = side_effect
            result = await client.list_workflows()

        assert result["data"][0]["id"] == "wf-1"
        assert call_count == 3, f"Expected 3 attempts, got {call_count}"

        await client.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_connection_error_exhausted(self) -> None:
        """All retries fail and N8nConnectionError is raised."""
        config = _make_config(max_retries=2, retry_base_delay=0.001)
        client = N8nApiClient(config)

        with patch.object(
            client._client, "request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.side_effect = httpx.ConnectError("Connection refused")

            with pytest.raises(N8nConnectionError) as exc_info:
                await client.list_workflows()

            assert "2 attempts" in str(exc_info.value)
            assert mock_req.await_count == 2

        await client.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_not_found_error_no_retry(self) -> None:
        """404 raises N8nNotFoundError immediately without retrying."""
        config = _make_config(max_retries=3)
        client = N8nApiClient(config)

        mock_resp = _mock_httpx_response(404, text="Not Found")

        with patch.object(
            client._client, "request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.return_value = mock_resp

            with pytest.raises(N8nNotFoundError) as exc_info:
                await client.get_workflow("nonexistent-wf")

            assert exc_info.value.status_code == 404
            assert mock_req.await_count == 1  # No retry

        await client.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_rate_limit_retry(self) -> None:
        """429 with Retry-After header triggers delay then retry."""
        config = _make_config(max_retries=3, retry_base_delay=0.001)
        client = N8nApiClient(config)

        rate_limit_resp = _mock_httpx_response(
            429, text="Rate limited", headers={"Retry-After": "0"}
        )
        success_resp = _mock_httpx_response(200, {"data": [], "nextCursor": None})

        call_count = 0

        async def side_effect(**kwargs: Any) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return rate_limit_resp
            return success_resp

        with patch.object(
            client._client, "request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.side_effect = side_effect
            result = await client.list_workflows()

        assert result == {"data": [], "nextCursor": None}
        assert call_count == 2

        await client.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_auth_error_no_retry(self) -> None:
        """401 raises N8nAuthenticationError immediately without retrying."""
        config = _make_config(max_retries=3)
        client = N8nApiClient(config)

        mock_resp = _mock_httpx_response(401, text="Unauthorized")

        with patch.object(
            client._client, "request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.return_value = mock_resp

            with pytest.raises(N8nAuthenticationError) as exc_info:
                await client.list_workflows()

            assert exc_info.value.status_code == 401
            assert mock_req.await_count == 1  # No retry

        await client.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_orchestration_timeout(self) -> None:
        """Orchestration with very short timeout returns TIMEOUT status."""
        config = _make_config()
        monitor_cfg = _fast_monitor_config()

        async def slow_reasoning(
            user_input: str, context: Dict[str, Any]
        ) -> ReasoningResult:
            await asyncio.sleep(2.0)  # Exceeds timeout
            return ReasoningResult(intent="QUERY")

        orchestrator = N8nOrchestrator(
            config=config,
            monitor_config=monitor_cfg,
            reasoning_fn=slow_reasoning,
        )

        request = OrchestrationRequest(
            user_input="Something slow",
            request_id="orch-timeout-001",
            timeout=0,  # Immediate timeout (capped to min of timeout, 60)
        )

        # The reasoning phase uses asyncio.wait_for with min(timeout, 60)
        # With timeout=0, this should timeout almost immediately
        # But the implementation uses min(request.timeout, 60) which is 0
        # So asyncio.wait_for with timeout=0 should raise TimeoutError
        result = await orchestrator.orchestrate(request)

        assert result.status == OrchestrationStatus.TIMEOUT
        assert result.error is not None

        await orchestrator.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_monitor_timeout(self) -> None:
        """ExecutionMonitor polls until timeout and returns TIMED_OUT."""
        config = _make_config()
        client = N8nApiClient(config)
        monitor_cfg = _fast_monitor_config()
        monitor = ExecutionMonitor(client=client, config=monitor_cfg)

        running_resp = {
            "id": "exec-mon-timeout",
            "status": "running",
            "startedAt": "2026-02-25T10:00:00Z",
        }
        mock_resp = _mock_httpx_response(200, running_resp)

        with patch.object(
            client._client, "request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.return_value = mock_resp

            result = await monitor.wait_for_completion(
                execution_id="exec-mon-timeout",
                timeout=0.1,
            )

        assert result.status == ExecutionState.TIMED_OUT
        assert result.total_polls >= 1
        assert result.error is not None
        assert "timed out" in result.error.lower()

        await client.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_monitor_execution_failure(self) -> None:
        """Monitor detects n8n execution failure and returns FAILED."""
        config = _make_config()
        client = N8nApiClient(config)
        monitor_cfg = _fast_monitor_config()
        monitor = ExecutionMonitor(client=client, config=monitor_cfg)

        failed_resp = {
            "id": "exec-mon-fail",
            "status": "error",
            "error": {"message": "Node timeout on HTTP Request"},
        }
        mock_resp = _mock_httpx_response(200, failed_resp)

        with patch.object(
            client._client, "request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.return_value = mock_resp

            result = await monitor.wait_for_completion(
                execution_id="exec-mon-fail",
                timeout=5.0,
            )

        assert result.status == ExecutionState.FAILED
        assert result.error is not None
        assert "Node timeout" in result.error
        assert result.total_polls >= 1

        await client.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_monitor_cancellation(self) -> None:
        """Cancelling an active monitor returns CANCELLED state."""
        config = _make_config()
        client = N8nApiClient(config)
        monitor_cfg = _fast_monitor_config()
        monitor_cfg.default_timeout = 10.0
        monitor = ExecutionMonitor(client=client, config=monitor_cfg)

        running_resp = {
            "id": "exec-cancel",
            "status": "running",
        }
        mock_resp = _mock_httpx_response(200, running_resp)

        async def cancel_after_delay() -> None:
            await asyncio.sleep(0.05)
            monitor.cancel("exec-cancel")

        with patch.object(
            client._client, "request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.return_value = mock_resp

            cancel_task = asyncio.create_task(cancel_after_delay())
            result = await monitor.wait_for_completion(
                execution_id="exec-cancel",
                timeout=5.0,
            )
            await cancel_task

        assert result.status == ExecutionState.CANCELLED

        await client.close()


# ===========================================================================
# Concurrency
# ===========================================================================


class TestN8nConcurrency:
    """Concurrency verification: parallel triggers and orchestrations."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_10_concurrent_workflow_triggers(self) -> None:
        """10 concurrent execute_workflow calls all complete without error."""
        config = _make_config()
        client = N8nApiClient(config)

        call_counter = 0

        async def mock_request(**kwargs: Any) -> MagicMock:
            nonlocal call_counter
            call_counter += 1
            idx = call_counter
            await asyncio.sleep(0.001)  # Simulate tiny latency
            return _mock_httpx_response(
                200,
                {
                    "data": {
                        "executionId": f"exec-conc-{idx}",
                        "status": "success",
                    }
                },
            )

        with patch.object(
            client._client, "request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.side_effect = mock_request

            tasks = [
                client.execute_workflow(f"wf-{i}", data={"index": i})
                for i in range(10)
            ]
            results = await asyncio.gather(*tasks)

        assert len(results) == 10
        execution_ids = [r["data"]["executionId"] for r in results]
        assert len(set(execution_ids)) == 10  # All unique
        assert call_counter == 10

        await client.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_concurrent_orchestrations(self) -> None:
        """5 concurrent orchestrations all complete independently."""
        config = _make_config()
        monitor_cfg = _fast_monitor_config()

        async def mock_reasoning(
            user_input: str, context: Dict[str, Any]
        ) -> ReasoningResult:
            await asyncio.sleep(0.001)
            return ReasoningResult(
                intent="REQUEST",
                sub_intent="general",
                confidence=0.9,
                recommended_workflow="wf-general",
                workflow_input={"input": user_input},
                risk_level="low",
                requires_approval=False,
            )

        orchestrator = N8nOrchestrator(
            config=config,
            monitor_config=monitor_cfg,
            reasoning_fn=mock_reasoning,
        )

        counter = 0

        async def mock_request(**kwargs: Any) -> MagicMock:
            nonlocal counter
            counter += 1
            idx = counter
            return _mock_httpx_response(
                200,
                {
                    "data": {
                        "executionId": f"exec-conc-orch-{idx}",
                        "status": "success",
                        "data": {"done": True},
                    }
                },
            )

        with patch.object(
            orchestrator._client._client, "request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.side_effect = mock_request

            tasks = [
                orchestrator.orchestrate(
                    OrchestrationRequest(
                        user_input=f"Request number {i}",
                        request_id=f"orch-conc-{i}",
                    )
                )
                for i in range(5)
            ]
            results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert all(r.status == OrchestrationStatus.COMPLETED for r in results)

        request_ids = {r.request_id for r in results}
        assert len(request_ids) == 5  # All unique

        await orchestrator.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_active_count_tracking(self) -> None:
        """get_active_count() reflects the number of in-flight orchestrations."""
        config = _make_config()
        monitor_cfg = _fast_monitor_config()

        barrier = asyncio.Event()
        observed_counts: list[int] = []

        async def slow_reasoning(
            user_input: str, context: Dict[str, Any]
        ) -> ReasoningResult:
            # Record active count while all orchestrations are in-flight
            observed_counts.append(orchestrator.get_active_count())
            await barrier.wait()
            return ReasoningResult(
                intent="QUERY",
                confidence=0.9,
                recommended_workflow="wf-count-test",
                risk_level="low",
                requires_approval=False,
            )

        orchestrator = N8nOrchestrator(
            config=config,
            monitor_config=monitor_cfg,
            reasoning_fn=slow_reasoning,
        )

        async def mock_request(**kwargs: Any) -> MagicMock:
            return _mock_httpx_response(
                200,
                {
                    "data": {
                        "executionId": "exec-count",
                        "status": "success",
                        "data": {},
                    }
                },
            )

        with patch.object(
            orchestrator._client._client, "request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.side_effect = mock_request

            num_concurrent = 3
            tasks = [
                asyncio.create_task(
                    orchestrator.orchestrate(
                        OrchestrationRequest(
                            user_input=f"Count test {i}",
                            request_id=f"orch-count-{i}",
                        )
                    )
                )
                for i in range(num_concurrent)
            ]

            # Wait briefly for all tasks to enter reasoning and record count
            await asyncio.sleep(0.05)

            # All should be active now
            count_before_release = orchestrator.get_active_count()

            # Release the barrier so all orchestrations can proceed
            barrier.set()

            results = await asyncio.gather(*tasks)

        # After all complete, active count should be 0
        assert orchestrator.get_active_count() == 0

        # While in-flight, at least one observation should show >1 active
        assert count_before_release == num_concurrent, (
            f"Expected {num_concurrent} active orchestrations, got {count_before_release}"
        )
        assert all(r.status == OrchestrationStatus.COMPLETED for r in results)

        await orchestrator.close()
