"""Unit tests for n8n ExecutionMonitor.

Tests execution monitoring, polling logic, timeout handling, retry
behaviour, progress callbacks, and cancellation.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.mcp.servers.n8n.client import (
    N8nApiClient,
    N8nApiError,
    N8nConfig,
    N8nConnectionError,
    N8nNotFoundError,
)
from src.integrations.n8n.monitor import (
    ExecutionMonitor,
    ExecutionProgress,
    ExecutionState,
    MonitorConfig,
    MonitorResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_n8n_config() -> N8nConfig:
    """Create a test N8nConfig instance."""
    return N8nConfig(base_url="http://test:5678", api_key="test-key")


def _make_fast_monitor_config(**overrides) -> MonitorConfig:
    """Create a MonitorConfig with tiny intervals for fast tests."""
    defaults = {
        "poll_interval": 0.01,
        "max_poll_interval": 0.02,
        "backoff_factor": 1.0,
        "default_timeout": 5.0,
        "max_retries_on_error": 3,
        "progress_update_interval": 0.0,
    }
    defaults.update(overrides)
    return MonitorConfig(**defaults)


def _make_execution_response(
    status: str = "running",
    data: dict | None = None,
    error: dict | str | None = None,
    started_at: str | None = None,
    stopped_at: str | None = None,
) -> dict:
    """Build a mock n8n execution response dict."""
    resp: dict = {"status": status}
    if data is not None:
        resp["data"] = data
    if error is not None:
        resp["error"] = error
    if started_at is not None:
        resp["startedAt"] = started_at
    if stopped_at is not None:
        resp["stoppedAt"] = stopped_at
    return resp


def _build_monitor(
    side_effect=None,
    return_value=None,
    config: MonitorConfig | None = None,
) -> tuple[ExecutionMonitor, AsyncMock]:
    """Build an ExecutionMonitor with a mocked client.

    Returns:
        (monitor, mock_get_execution) tuple.
    """
    mock_client = MagicMock(spec=N8nApiClient)
    mock_get_execution = AsyncMock(
        side_effect=side_effect,
        return_value=return_value,
    )
    mock_client.get_execution = mock_get_execution
    monitor = ExecutionMonitor(
        client=mock_client,
        config=config or _make_fast_monitor_config(),
    )
    return monitor, mock_get_execution


# ===================================================================
# TestMonitorConfig
# ===================================================================

class TestMonitorConfig:
    """Tests for MonitorConfig dataclass."""

    def test_default_values(self):
        """Default values match documented constants."""
        cfg = MonitorConfig()

        assert cfg.poll_interval == 2.0
        assert cfg.max_poll_interval == 30.0
        assert cfg.backoff_factor == 1.5
        assert cfg.default_timeout == 300.0
        assert cfg.max_retries_on_error == 3
        assert cfg.progress_update_interval == 5.0

    def test_from_env(self, monkeypatch):
        """from_env reads N8N_MONITOR_* environment variables."""
        monkeypatch.setenv("N8N_MONITOR_POLL_INTERVAL", "0.5")
        monkeypatch.setenv("N8N_MONITOR_MAX_POLL_INTERVAL", "10")
        monkeypatch.setenv("N8N_MONITOR_DEFAULT_TIMEOUT", "60")

        cfg = MonitorConfig.from_env()

        assert cfg.poll_interval == 0.5
        assert cfg.max_poll_interval == 10.0
        assert cfg.default_timeout == 60.0
        # Fields NOT set via env keep their constructor defaults
        assert cfg.backoff_factor == 1.5
        assert cfg.max_retries_on_error == 3

    def test_custom_config(self):
        """Constructor accepts arbitrary overrides."""
        cfg = MonitorConfig(
            poll_interval=0.1,
            max_poll_interval=1.0,
            backoff_factor=2.0,
            default_timeout=10.0,
            max_retries_on_error=5,
            progress_update_interval=1.0,
        )

        assert cfg.poll_interval == 0.1
        assert cfg.max_poll_interval == 1.0
        assert cfg.backoff_factor == 2.0
        assert cfg.default_timeout == 10.0
        assert cfg.max_retries_on_error == 5
        assert cfg.progress_update_interval == 1.0


# ===================================================================
# TestExecutionState
# ===================================================================

class TestExecutionState:
    """Tests for ExecutionState mapping via _map_status."""

    def test_status_mapping(self):
        """Known n8n statuses map to the correct ExecutionState."""
        expected = {
            "success": ExecutionState.COMPLETED,
            "error": ExecutionState.FAILED,
            "running": ExecutionState.RUNNING,
            "new": ExecutionState.PENDING,
            "waiting": ExecutionState.RUNNING,
            "crashed": ExecutionState.FAILED,
        }
        for n8n_status, expected_state in expected.items():
            result = ExecutionMonitor._map_status(n8n_status)
            assert result == expected_state, (
                f"_map_status('{n8n_status}') returned {result}, "
                f"expected {expected_state}"
            )

    def test_unknown_status_mapping(self):
        """Unrecognised n8n statuses map to UNKNOWN."""
        for unknown in ("queued", "paused", "banana", ""):
            result = ExecutionMonitor._map_status(unknown)
            assert result == ExecutionState.UNKNOWN, (
                f"_map_status('{unknown}') returned {result}, expected UNKNOWN"
            )


# ===================================================================
# TestExecutionProgress
# ===================================================================

class TestExecutionProgress:
    """Tests for ExecutionProgress dataclass."""

    def test_default_values(self):
        """Defaults are sensible when only required fields are given."""
        progress = ExecutionProgress(
            execution_id="exec-1",
            state=ExecutionState.RUNNING,
        )

        assert progress.execution_id == "exec-1"
        assert progress.state == ExecutionState.RUNNING
        assert progress.progress_pct == 0.0
        assert progress.message == ""
        assert progress.started_at is None
        assert progress.output_data is None
        assert progress.error is None
        assert progress.poll_count == 0
        assert isinstance(progress.timestamp, datetime)

    def test_custom_progress(self):
        """All fields can be set explicitly."""
        now = datetime.utcnow()
        progress = ExecutionProgress(
            execution_id="exec-99",
            state=ExecutionState.COMPLETED,
            progress_pct=100.0,
            message="Done",
            started_at=now,
            timestamp=now,
            output_data={"key": "value"},
            error=None,
            poll_count=5,
        )

        assert progress.execution_id == "exec-99"
        assert progress.state == ExecutionState.COMPLETED
        assert progress.progress_pct == 100.0
        assert progress.message == "Done"
        assert progress.started_at == now
        assert progress.timestamp == now
        assert progress.output_data == {"key": "value"}
        assert progress.error is None
        assert progress.poll_count == 5


# ===================================================================
# TestWaitForCompletion
# ===================================================================

class TestWaitForCompletion:
    """Tests for ExecutionMonitor.wait_for_completion."""

    @pytest.mark.asyncio
    async def test_execution_completes_immediately(self):
        """First poll returns 'success' — monitor returns COMPLETED."""
        monitor, mock_get = _build_monitor(
            return_value=_make_execution_response(
                status="success",
                data={"resultData": {"output": "ok"}},
                started_at="2026-01-01T00:00:00Z",
                stopped_at="2026-01-01T00:00:05Z",
            ),
        )

        result = await monitor.wait_for_completion("exec-1", timeout=5.0)

        assert result.status == ExecutionState.COMPLETED
        assert result.execution_id == "exec-1"
        assert result.total_polls == 1
        assert result.output_data == {"resultData": {"output": "ok"}}
        assert result.duration_ms == 5000
        assert result.error is None
        mock_get.assert_awaited_once_with("exec-1")

    @pytest.mark.asyncio
    async def test_execution_completes_after_polls(self):
        """Execution is 'running' twice then 'success'."""
        monitor, mock_get = _build_monitor(
            side_effect=[
                _make_execution_response(status="running"),
                _make_execution_response(status="running"),
                _make_execution_response(
                    status="success",
                    data={"final": True},
                ),
            ],
        )

        result = await monitor.wait_for_completion("exec-2", timeout=5.0)

        assert result.status == ExecutionState.COMPLETED
        assert result.total_polls == 3
        assert result.output_data == {"final": True}

    @pytest.mark.asyncio
    async def test_execution_fails(self):
        """First poll returns 'error' — monitor returns FAILED."""
        monitor, _ = _build_monitor(
            return_value=_make_execution_response(
                status="error",
                error={"message": "Node timeout"},
            ),
        )

        result = await monitor.wait_for_completion("exec-3", timeout=5.0)

        assert result.status == ExecutionState.FAILED
        assert result.total_polls == 1
        assert result.error == "Node timeout"

    @pytest.mark.asyncio
    async def test_execution_timeout(self):
        """Execution never reaches a terminal state within timeout."""
        monitor, _ = _build_monitor(
            return_value=_make_execution_response(status="running"),
            config=_make_fast_monitor_config(default_timeout=0.05),
        )

        result = await monitor.wait_for_completion("exec-4")

        assert result.status == ExecutionState.TIMED_OUT
        assert "timed out" in result.error.lower()
        assert result.total_polls >= 1

    @pytest.mark.asyncio
    async def test_execution_not_found(self):
        """get_execution raises N8nNotFoundError — returns FAILED immediately."""
        monitor, mock_get = _build_monitor()
        mock_get.side_effect = N8nNotFoundError("Not found", status_code=404)

        result = await monitor.wait_for_completion("exec-missing", timeout=5.0)

        assert result.status == ExecutionState.FAILED
        assert "not found" in result.error.lower()
        assert result.total_polls == 0

    @pytest.mark.asyncio
    async def test_connection_errors_with_retry(self):
        """Transient connection errors are retried, then execution succeeds."""
        monitor, mock_get = _build_monitor(
            side_effect=[
                N8nConnectionError("Connection refused"),
                N8nConnectionError("Connection refused"),
                _make_execution_response(status="success", data={"ok": True}),
            ],
            config=_make_fast_monitor_config(max_retries_on_error=5),
        )

        result = await monitor.wait_for_completion("exec-retry", timeout=5.0)

        assert result.status == ExecutionState.COMPLETED
        assert result.output_data == {"ok": True}
        assert mock_get.await_count == 3

    @pytest.mark.asyncio
    async def test_connection_errors_exceed_max(self):
        """Too many consecutive connection errors cause FAILED result."""
        errors = [
            N8nConnectionError("fail")
            for _ in range(3)
        ]
        monitor, _ = _build_monitor(
            side_effect=errors,
            config=_make_fast_monitor_config(max_retries_on_error=3),
        )

        result = await monitor.wait_for_completion("exec-err", timeout=5.0)

        assert result.status == ExecutionState.FAILED
        assert "3 errors" in result.error

    @pytest.mark.asyncio
    async def test_progress_callback_called(self):
        """Progress callback receives ExecutionProgress updates."""
        monitor, _ = _build_monitor(
            side_effect=[
                _make_execution_response(status="running"),
                _make_execution_response(
                    status="success",
                    data={"done": True},
                ),
            ],
            config=_make_fast_monitor_config(progress_update_interval=0.0),
        )

        received: list[ExecutionProgress] = []
        callback = MagicMock(side_effect=lambda p: received.append(p))

        result = await monitor.wait_for_completion(
            "exec-cb",
            timeout=5.0,
            progress_callback=callback,
        )

        assert result.status == ExecutionState.COMPLETED
        # At minimum, the final COMPLETED progress is always sent
        assert callback.call_count >= 1
        # The last callback should be the COMPLETED notification
        last_progress = received[-1]
        assert last_progress.state == ExecutionState.COMPLETED
        assert last_progress.progress_pct == 100.0

    @pytest.mark.asyncio
    async def test_api_error_with_retry(self):
        """N8nApiError (non-connection) also triggers retry logic."""
        monitor, mock_get = _build_monitor(
            side_effect=[
                N8nApiError("Server error", status_code=500),
                _make_execution_response(status="success"),
            ],
            config=_make_fast_monitor_config(max_retries_on_error=3),
        )

        result = await monitor.wait_for_completion("exec-api-err", timeout=5.0)

        assert result.status == ExecutionState.COMPLETED
        assert mock_get.await_count == 2

    @pytest.mark.asyncio
    async def test_execution_with_explicit_timeout_override(self):
        """Explicit timeout parameter overrides the config default."""
        monitor, _ = _build_monitor(
            return_value=_make_execution_response(status="running"),
            config=_make_fast_monitor_config(default_timeout=999.0),
        )

        result = await monitor.wait_for_completion("exec-to", timeout=0.05)

        assert result.status == ExecutionState.TIMED_OUT
        assert "timed out" in result.error.lower()


# ===================================================================
# TestCancel
# ===================================================================

class TestCancel:
    """Tests for ExecutionMonitor.cancel."""

    @pytest.mark.asyncio
    async def test_cancel_active_monitor(self):
        """Cancelling an active monitor returns CANCELLED result."""
        monitor, _ = _build_monitor(
            return_value=_make_execution_response(status="running"),
            config=_make_fast_monitor_config(default_timeout=10.0),
        )

        async def cancel_after_delay():
            await asyncio.sleep(0.05)
            cancelled = monitor.cancel("exec-cancel")
            assert cancelled is True

        task = asyncio.create_task(cancel_after_delay())
        result = await monitor.wait_for_completion("exec-cancel", timeout=10.0)
        await task

        assert result.status == ExecutionState.CANCELLED
        assert result.execution_id == "exec-cancel"

    def test_cancel_nonexistent(self):
        """Cancelling a non-active execution returns False."""
        monitor, _ = _build_monitor()

        assert monitor.cancel("does-not-exist") is False


# ===================================================================
# TestIsMonitoringAndActiveCount
# ===================================================================

class TestIsMonitoringAndActiveCount:
    """Tests for is_monitoring and active_count properties."""

    @pytest.mark.asyncio
    async def test_is_monitoring_during_execution(self):
        """is_monitoring returns True while wait_for_completion is running."""
        monitor, _ = _build_monitor(
            return_value=_make_execution_response(status="running"),
            config=_make_fast_monitor_config(default_timeout=10.0),
        )

        observed_monitoring = False

        async def check_and_cancel():
            nonlocal observed_monitoring
            await asyncio.sleep(0.03)
            observed_monitoring = monitor.is_monitoring("exec-check")
            monitor.cancel("exec-check")

        task = asyncio.create_task(check_and_cancel())
        await monitor.wait_for_completion("exec-check", timeout=10.0)
        await task

        assert observed_monitoring is True
        # After completion, monitoring should be cleaned up
        assert monitor.is_monitoring("exec-check") is False

    def test_is_monitoring_not_active(self):
        """is_monitoring returns False for unknown execution IDs."""
        monitor, _ = _build_monitor()
        assert monitor.is_monitoring("unknown-id") is False

    def test_active_count_starts_at_zero(self):
        """active_count is 0 when no monitors are running."""
        monitor, _ = _build_monitor()
        assert monitor.active_count == 0


# ===================================================================
# TestErrorExtraction
# ===================================================================

class TestErrorExtraction:
    """Tests for ExecutionMonitor._extract_error."""

    def test_extract_error_from_error_field(self):
        """Error is extracted from top-level 'error' dict."""
        execution = {
            "status": "error",
            "error": {"message": "Workflow node crashed"},
        }

        result = ExecutionMonitor._extract_error(execution)
        assert result == "Workflow node crashed"

    def test_extract_error_from_error_string(self):
        """Error is extracted when top-level 'error' is a plain string."""
        execution = {
            "status": "error",
            "error": "Something went wrong",
        }

        result = ExecutionMonitor._extract_error(execution)
        assert result == "Something went wrong"

    def test_extract_error_from_result_data(self):
        """Error is extracted from data.resultData.error.message path."""
        execution = {
            "status": "error",
            "data": {
                "resultData": {
                    "error": {"message": "HTTP 502 Bad Gateway"},
                },
            },
        }

        result = ExecutionMonitor._extract_error(execution)
        assert result == "HTTP 502 Bad Gateway"

    def test_extract_error_fallback(self):
        """Returns fallback message when no error info is found."""
        # When data.resultData.error is an empty dict, the fallback from
        # error.get("message", "Unknown execution error") is used.
        execution = {"status": "error"}

        result = ExecutionMonitor._extract_error(execution)
        assert result == "Unknown execution error"


# ===================================================================
# TestMonitorResult
# ===================================================================

class TestMonitorResult:
    """Tests for MonitorResult dataclass."""

    def test_default_values(self):
        """Defaults are sensible for a minimal result."""
        result = MonitorResult(
            execution_id="exec-r",
            status=ExecutionState.COMPLETED,
        )

        assert result.execution_id == "exec-r"
        assert result.status == ExecutionState.COMPLETED
        assert result.output_data is None
        assert result.error is None
        assert result.started_at is None
        assert result.finished_at is None
        assert result.duration_ms is None
        assert result.total_polls == 0
