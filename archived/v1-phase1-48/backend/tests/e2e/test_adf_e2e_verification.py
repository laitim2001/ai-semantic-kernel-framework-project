"""
End-to-End Verification Tests for Azure Data Factory (ADF) Pipeline.

Sprint 127: Story 127-2 — ADF E2E Verification (Phase 34)

Tests the full ADF pipeline lifecycle: list/get/run/monitor/cancel
with mocked Azure REST API responses via httpx.AsyncClient.

All external I/O is mocked. No real Azure connections are made.
"""

import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.integrations.mcp.servers.adf.client import (
    AdfApiClient,
    AdfAuthenticationError,
    AdfConfig,
    AdfNotFoundError,
    PipelineRunStatus,
)
from src.integrations.mcp.servers.adf.server import AdfMCPServer


# ---------------------------------------------------------------------------
# Shared Helpers
# ---------------------------------------------------------------------------


def _make_adf_config() -> AdfConfig:
    """Create a test ADF configuration (no real Azure credentials)."""
    return AdfConfig(
        subscription_id="test-sub-001",
        resource_group="test-rg",
        factory_name="test-adf-factory",
        tenant_id="test-tenant-id",
        client_id="test-client-id",
        client_secret="test-client-secret",
        timeout=5,
        max_retries=1,
        retry_base_delay=0.01,
    )


def _make_response(
    status_code: int,
    json_data: Dict[str, Any],
    headers: Dict[str, str] | None = None,
) -> httpx.Response:
    """Create a mock httpx.Response with the given status and JSON body."""
    response = httpx.Response(
        status_code=status_code,
        json=json_data,
        headers=headers or {},
        request=httpx.Request("GET", "https://management.azure.com/test"),
    )
    return response


def _make_token_response() -> httpx.Response:
    """Create a successful OAuth2 token response."""
    return _make_response(200, {
        "access_token": "mock-access-token-adf-e2e",
        "expires_in": 3600,
        "token_type": "Bearer",
    })


def _make_pipeline_list_response(pipeline_names: List[str]) -> httpx.Response:
    """Create a pipeline list response."""
    pipelines = [
        {
            "name": name,
            "id": f"/subscriptions/test/resourceGroups/test/providers/Microsoft.DataFactory/"
                  f"factories/test/pipelines/{name}",
            "type": "Microsoft.DataFactory/factories/pipelines",
            "properties": {"activities": []},
        }
        for name in pipeline_names
    ]
    return _make_response(200, {"value": pipelines})


def _make_pipeline_detail_response(pipeline_name: str) -> httpx.Response:
    """Create a single pipeline detail response."""
    return _make_response(200, {
        "name": pipeline_name,
        "id": f"/subscriptions/test/resourceGroups/test/providers/Microsoft.DataFactory/"
              f"factories/test/pipelines/{pipeline_name}",
        "type": "Microsoft.DataFactory/factories/pipelines",
        "properties": {
            "activities": [
                {"name": "CopyData", "type": "Copy"},
                {"name": "Transform", "type": "DataFlow"},
            ],
            "parameters": {
                "inputPath": {"type": "String"},
                "outputPath": {"type": "String"},
            },
        },
    })


def _make_run_trigger_response(run_id: str) -> httpx.Response:
    """Create a pipeline run trigger response."""
    return _make_response(200, {"runId": run_id})


def _make_run_status_response(
    run_id: str,
    status: str,
    output: Dict[str, Any] | None = None,
    message: str = "",
) -> httpx.Response:
    """Create a pipeline run status response."""
    body: Dict[str, Any] = {
        "runId": run_id,
        "pipelineName": "test-pipeline",
        "status": status,
        "runStart": "2026-02-25T10:00:00Z",
        "message": message,
    }
    if status == PipelineRunStatus.SUCCEEDED.value:
        body["runEnd"] = "2026-02-25T10:05:00Z"
        body["durationInMs"] = 300000
        body["output"] = output or {"rowsCopied": 15000}
    elif status == PipelineRunStatus.FAILED.value:
        body["runEnd"] = "2026-02-25T10:03:00Z"
        body["message"] = message or "Pipeline execution failed: data source unreachable"
    return _make_response(200, body)


# ---------------------------------------------------------------------------
# E2E: Pipeline Trigger and Monitor
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestAdfPipelineTriggerAndMonitor:
    """E2E: Full ADF pipeline lifecycle — list, get, run, monitor."""

    @pytest.mark.asyncio
    async def test_full_pipeline_lifecycle(self) -> None:
        """Test complete lifecycle: list pipelines -> get pipeline -> run -> check status."""
        config = _make_adf_config()
        client = AdfApiClient(config)

        # Sequence of responses the mock client will return
        mock_responses = [
            # Token acquisition
            _make_token_response(),
            # list_pipelines
            _make_pipeline_list_response(["etl-daily", "etl-hourly", "data-transform"]),
            # get_pipeline("etl-daily")
            _make_pipeline_detail_response("etl-daily"),
            # run_pipeline("etl-daily")
            _make_run_trigger_response("run-lifecycle-001"),
            # get_pipeline_run("run-lifecycle-001") -> Succeeded
            _make_run_status_response(
                "run-lifecycle-001",
                PipelineRunStatus.SUCCEEDED.value,
                output={"rowsCopied": 25000},
            ),
        ]

        call_idx = 0

        async def mock_request(*args: Any, **kwargs: Any) -> httpx.Response:
            nonlocal call_idx
            resp = mock_responses[call_idx]
            call_idx += 1
            return resp

        client._client = MagicMock()
        client._client.aclose = AsyncMock()
        client._client.post = AsyncMock(side_effect=mock_request)
        client._client.request = AsyncMock(side_effect=mock_request)

        try:
            # Step 1: List pipelines
            pipelines = await client.list_pipelines()
            assert "value" in pipelines
            assert len(pipelines["value"]) == 3
            pipeline_names = [p["name"] for p in pipelines["value"]]
            assert "etl-daily" in pipeline_names

            # Step 2: Get pipeline detail
            pipeline = await client.get_pipeline("etl-daily")
            assert pipeline["name"] == "etl-daily"
            assert len(pipeline["properties"]["activities"]) == 2

            # Step 3: Trigger pipeline run
            run_result = await client.run_pipeline("etl-daily")
            assert run_result["runId"] == "run-lifecycle-001"

            # Step 4: Get run status
            run_status = await client.get_pipeline_run("run-lifecycle-001")
            assert run_status["status"] == PipelineRunStatus.SUCCEEDED.value
            assert run_status["output"]["rowsCopied"] == 25000
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_pipeline_trigger_with_params(self) -> None:
        """Test running a pipeline with custom parameters and verifying they are passed."""
        config = _make_adf_config()
        client = AdfApiClient(config)

        captured_json: List[Dict[str, Any]] = []

        async def mock_request(*args: Any, **kwargs: Any) -> httpx.Response:
            # post(url, ...) puts url in args[0]; request(method, url, ...) in args[1]
            all_args = " ".join(str(a) for a in args) + " " + str(kwargs.get("url", ""))
            if "oauth2" in all_args or "token" in all_args:
                return _make_token_response()
            # Capture the JSON data sent to createRun
            if "createRun" in all_args:
                json_data = kwargs.get("json", {})
                captured_json.append(json_data)
                return _make_run_trigger_response("run-params-001")
            return _make_response(200, {})

        client._client = MagicMock()
        client._client.aclose = AsyncMock()
        client._client.post = AsyncMock(side_effect=mock_request)
        client._client.request = AsyncMock(side_effect=mock_request)

        try:
            params = {
                "inputPath": "wasbs://raw-data@storage.blob.core.windows.net/2026/02/25",
                "outputPath": "wasbs://processed@storage.blob.core.windows.net/2026/02/25",
                "batchSize": 5000,
            }

            result = await client.run_pipeline("etl-parameterized", parameters=params)
            assert result["runId"] == "run-params-001"

            # Verify parameters were passed to the API
            assert len(captured_json) == 1
            sent_params = captured_json[0]
            assert sent_params["inputPath"] == params["inputPath"]
            assert sent_params["outputPath"] == params["outputPath"]
            assert sent_params["batchSize"] == 5000
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_pipeline_run_monitoring_until_success(self) -> None:
        """Test polling pipeline status through Queued -> InProgress -> Succeeded transitions."""
        config = _make_adf_config()
        client = AdfApiClient(config)

        # Status progression: Queued -> InProgress -> Succeeded
        status_sequence = [
            _make_token_response(),
            # run_pipeline
            _make_run_trigger_response("run-monitor-001"),
            # poll 1: Queued
            _make_run_status_response("run-monitor-001", PipelineRunStatus.QUEUED.value),
            # poll 2: InProgress
            _make_run_status_response("run-monitor-001", PipelineRunStatus.IN_PROGRESS.value),
            # poll 3: Succeeded
            _make_run_status_response(
                "run-monitor-001",
                PipelineRunStatus.SUCCEEDED.value,
                output={"rowsCopied": 10000},
            ),
        ]

        call_idx = 0

        async def mock_request(*args: Any, **kwargs: Any) -> httpx.Response:
            nonlocal call_idx
            resp = status_sequence[call_idx]
            call_idx += 1
            return resp

        client._client = MagicMock()
        client._client.aclose = AsyncMock()
        client._client.post = AsyncMock(side_effect=mock_request)
        client._client.request = AsyncMock(side_effect=mock_request)

        try:
            # Trigger run
            run_result = await client.run_pipeline("etl-daily")
            assert run_result["runId"] == "run-monitor-001"

            # Poll until success
            observed_statuses: List[str] = []
            for _ in range(3):
                status_resp = await client.get_pipeline_run("run-monitor-001")
                observed_statuses.append(status_resp["status"])
                if status_resp["status"] == PipelineRunStatus.SUCCEEDED.value:
                    break

            assert observed_statuses == [
                PipelineRunStatus.QUEUED.value,
                PipelineRunStatus.IN_PROGRESS.value,
                PipelineRunStatus.SUCCEEDED.value,
            ]
        finally:
            await client.close()


# ---------------------------------------------------------------------------
# E2E: Pipeline Cancellation
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestAdfPipelineCancellation:
    """E2E: Pipeline run cancellation scenarios."""

    @pytest.mark.asyncio
    async def test_cancel_running_pipeline(self) -> None:
        """Test triggering a pipeline run and then cancelling it successfully."""
        config = _make_adf_config()
        client = AdfApiClient(config)

        responses = [
            _make_token_response(),
            # run_pipeline
            _make_run_trigger_response("run-cancel-001"),
            # cancel_pipeline_run -> 200 empty
            _make_response(200, {}),
            # get_pipeline_run -> Cancelled
            _make_run_status_response("run-cancel-001", PipelineRunStatus.CANCELLED.value),
        ]

        call_idx = 0

        async def mock_request(*args: Any, **kwargs: Any) -> httpx.Response:
            nonlocal call_idx
            resp = responses[call_idx]
            call_idx += 1
            return resp

        client._client = MagicMock()
        client._client.aclose = AsyncMock()
        client._client.post = AsyncMock(side_effect=mock_request)
        client._client.request = AsyncMock(side_effect=mock_request)

        try:
            # Trigger run
            run_result = await client.run_pipeline("etl-daily")
            run_id = run_result["runId"]
            assert run_id == "run-cancel-001"

            # Cancel the run
            cancel_result = await client.cancel_pipeline_run(run_id)
            assert cancel_result == {}

            # Verify status is Cancelled
            status = await client.get_pipeline_run(run_id)
            assert status["status"] == PipelineRunStatus.CANCELLED.value
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_run(self) -> None:
        """Test cancelling a non-existent run raises AdfNotFoundError."""
        config = _make_adf_config()
        client = AdfApiClient(config)

        async def mock_request(*args: Any, **kwargs: Any) -> httpx.Response:
            all_args = " ".join(str(a) for a in args) + " " + str(kwargs.get("url", ""))
            if "oauth2" in all_args or "token" in all_args:
                return _make_token_response()
            # Return 404 for cancel
            return _make_response(
                404, {"error": {"code": "PipelineRunNotFound", "message": "Run not found"}},
            )

        client._client = MagicMock()
        client._client.aclose = AsyncMock()
        client._client.post = AsyncMock(side_effect=mock_request)
        client._client.request = AsyncMock(side_effect=mock_request)

        try:
            with pytest.raises(AdfNotFoundError):
                await client.cancel_pipeline_run("nonexistent-run-999")
        finally:
            await client.close()


# ---------------------------------------------------------------------------
# E2E: Error Handling
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestAdfErrorHandling:
    """E2E: ADF error handling — not found, failures, auth errors."""

    @pytest.mark.asyncio
    async def test_pipeline_not_found(self) -> None:
        """Test getting a non-existent pipeline raises AdfNotFoundError."""
        config = _make_adf_config()
        client = AdfApiClient(config)

        async def mock_request(*args: Any, **kwargs: Any) -> httpx.Response:
            all_args = " ".join(str(a) for a in args) + " " + str(kwargs.get("url", ""))
            if "oauth2" in all_args or "token" in all_args:
                return _make_token_response()
            return _make_response(404, {
                "error": {"code": "PipelineNotFound", "message": "Pipeline does not exist"},
            })

        client._client = MagicMock()
        client._client.aclose = AsyncMock()
        client._client.post = AsyncMock(side_effect=mock_request)
        client._client.request = AsyncMock(side_effect=mock_request)

        try:
            with pytest.raises(AdfNotFoundError) as exc_info:
                await client.get_pipeline("nonexistent-pipeline")
            assert exc_info.value.status_code == 404
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_pipeline_run_failure(self) -> None:
        """Test that a pipeline returning Failed status carries error information."""
        config = _make_adf_config()
        client = AdfApiClient(config)

        responses = [
            _make_token_response(),
            _make_run_trigger_response("run-fail-001"),
            _make_run_status_response(
                "run-fail-001",
                PipelineRunStatus.FAILED.value,
                message="Source dataset connection timeout after 30 seconds",
            ),
        ]

        call_idx = 0

        async def mock_request(*args: Any, **kwargs: Any) -> httpx.Response:
            nonlocal call_idx
            resp = responses[call_idx]
            call_idx += 1
            return resp

        client._client = MagicMock()
        client._client.aclose = AsyncMock()
        client._client.post = AsyncMock(side_effect=mock_request)
        client._client.request = AsyncMock(side_effect=mock_request)

        try:
            run_result = await client.run_pipeline("etl-fragile")
            run_id = run_result["runId"]

            status_resp = await client.get_pipeline_run(run_id)
            assert status_resp["status"] == PipelineRunStatus.FAILED.value
            assert "connection timeout" in status_resp["message"]
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_auth_error_handling(self) -> None:
        """Test that a 401 response raises AdfAuthenticationError."""
        config = _make_adf_config()
        client = AdfApiClient(config)

        # Token request itself returns 401
        async def mock_post(*args: Any, **kwargs: Any) -> httpx.Response:
            return _make_response(401, {
                "error": "invalid_client",
                "error_description": "Client authentication failed",
            })

        client._client = MagicMock()
        client._client.aclose = AsyncMock()
        client._client.post = AsyncMock(side_effect=mock_post)
        client._client.request = AsyncMock(side_effect=mock_post)

        try:
            with pytest.raises(AdfAuthenticationError):
                await client.list_pipelines()
        finally:
            await client.close()


# ---------------------------------------------------------------------------
# E2E: Concurrent Pipelines
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestAdfConcurrentPipelines:
    """E2E: Multiple concurrent pipeline executions."""

    @pytest.mark.asyncio
    async def test_multiple_pipeline_runs(self) -> None:
        """Test triggering 3 pipelines concurrently, all complete successfully."""
        config = _make_adf_config()

        pipeline_data = [
            ("etl-customers", "run-multi-001"),
            ("etl-orders", "run-multi-002"),
            ("etl-products", "run-multi-003"),
        ]

        async def run_single_pipeline(
            pipeline_name: str, run_id: str
        ) -> Dict[str, Any]:
            """Simulate running a single pipeline with its own mocked client."""
            client = AdfApiClient(config)

            responses = [
                _make_token_response(),
                _make_run_trigger_response(run_id),
                _make_run_status_response(
                    run_id,
                    PipelineRunStatus.SUCCEEDED.value,
                    output={"pipeline": pipeline_name, "rowsProcessed": 1000},
                ),
            ]
            call_idx = 0

            async def mock_request(*args: Any, **kwargs: Any) -> httpx.Response:
                nonlocal call_idx
                resp = responses[call_idx]
                call_idx += 1
                return resp

            client._client = MagicMock()
            client._client.aclose = AsyncMock()
            client._client.post = AsyncMock(side_effect=mock_request)
            client._client.request = AsyncMock(side_effect=mock_request)

            try:
                trigger = await client.run_pipeline(pipeline_name)
                status = await client.get_pipeline_run(trigger["runId"])
                return status
            finally:
                await client.close()

        results = await asyncio.gather(
            *[run_single_pipeline(name, rid) for name, rid in pipeline_data]
        )

        assert len(results) == 3
        for result in results:
            assert result["status"] == PipelineRunStatus.SUCCEEDED.value
            assert "rowsProcessed" in result.get("output", {})

    @pytest.mark.asyncio
    async def test_mixed_pipeline_results(self) -> None:
        """Test 3 pipelines: one succeeds, one fails, one cancelled."""
        config = _make_adf_config()

        scenarios = [
            ("etl-success", "run-mix-001", PipelineRunStatus.SUCCEEDED.value, ""),
            ("etl-fail", "run-mix-002", PipelineRunStatus.FAILED.value, "Data source offline"),
            ("etl-cancel", "run-mix-003", PipelineRunStatus.CANCELLED.value, ""),
        ]

        async def run_scenario(
            pipeline_name: str,
            run_id: str,
            final_status: str,
            message: str,
        ) -> Dict[str, Any]:
            """Simulate a single pipeline scenario with specific outcome."""
            client = AdfApiClient(config)

            responses = [
                _make_token_response(),
                _make_run_trigger_response(run_id),
                _make_run_status_response(run_id, final_status, message=message),
            ]
            call_idx = 0

            async def mock_request(*args: Any, **kwargs: Any) -> httpx.Response:
                nonlocal call_idx
                resp = responses[call_idx]
                call_idx += 1
                return resp

            client._client = MagicMock()
            client._client.aclose = AsyncMock()
            client._client.post = AsyncMock(side_effect=mock_request)
            client._client.request = AsyncMock(side_effect=mock_request)

            try:
                trigger = await client.run_pipeline(pipeline_name)
                status = await client.get_pipeline_run(trigger["runId"])
                return status
            finally:
                await client.close()

        results = await asyncio.gather(
            *[run_scenario(name, rid, status, msg) for name, rid, status, msg in scenarios]
        )

        assert len(results) == 3
        assert results[0]["status"] == PipelineRunStatus.SUCCEEDED.value
        assert results[1]["status"] == PipelineRunStatus.FAILED.value
        assert "Data source offline" in results[1]["message"]
        assert results[2]["status"] == PipelineRunStatus.CANCELLED.value
