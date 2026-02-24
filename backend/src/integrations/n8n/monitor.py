"""n8n Execution Monitor.

Provides execution monitoring for n8n workflows with polling,
timeout handling, retry logic, and progress notification.

Features:
    - Configurable polling interval with exponential backoff
    - Timeout handling with configurable limits
    - Failure retry with configurable attempts
    - Progress callback notifications
    - SSE-compatible progress events

Environment Variables:
    N8N_MONITOR_POLL_INTERVAL: Initial poll interval in seconds (default: 2)
    N8N_MONITOR_MAX_POLL_INTERVAL: Maximum poll interval in seconds (default: 30)
    N8N_MONITOR_DEFAULT_TIMEOUT: Default monitoring timeout (default: 300)
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from src.integrations.mcp.servers.n8n.client import (
    N8nApiClient,
    N8nApiError,
    N8nConnectionError,
    N8nNotFoundError,
    ExecutionStatus,
)

logger = logging.getLogger(__name__)


class ExecutionState(str, Enum):
    """State of a monitored n8n execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


@dataclass
class MonitorConfig:
    """Configuration for execution monitoring.

    Attributes:
        poll_interval: Initial polling interval in seconds
        max_poll_interval: Maximum polling interval (backoff cap)
        backoff_factor: Multiplier for exponential backoff
        default_timeout: Default timeout for monitoring in seconds
        max_retries_on_error: Retries on transient API errors during polling
        progress_update_interval: Minimum interval between progress notifications
    """

    poll_interval: float = 2.0
    max_poll_interval: float = 30.0
    backoff_factor: float = 1.5
    default_timeout: float = 300.0
    max_retries_on_error: int = 3
    progress_update_interval: float = 5.0

    @classmethod
    def from_env(cls) -> "MonitorConfig":
        """Create configuration from environment variables.

        Returns:
            MonitorConfig instance
        """
        return cls(
            poll_interval=float(os.environ.get("N8N_MONITOR_POLL_INTERVAL", "2")),
            max_poll_interval=float(os.environ.get("N8N_MONITOR_MAX_POLL_INTERVAL", "30")),
            default_timeout=float(os.environ.get("N8N_MONITOR_DEFAULT_TIMEOUT", "300")),
        )


@dataclass
class ExecutionProgress:
    """Progress update for a monitored execution.

    Attributes:
        execution_id: n8n execution ID
        state: Current execution state
        progress_pct: Progress percentage (0-100), estimated
        message: Human-readable status message
        started_at: When execution started
        timestamp: When this progress update was generated
        output_data: Partial output data if available
        error: Error message if failed
        poll_count: Number of poll attempts so far
    """

    execution_id: str
    state: ExecutionState
    progress_pct: float = 0.0
    message: str = ""
    started_at: Optional[datetime] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    poll_count: int = 0


@dataclass
class MonitorResult:
    """Final result of execution monitoring.

    Attributes:
        execution_id: n8n execution ID
        status: Final execution state
        output_data: Execution output data
        error: Error message if failed
        started_at: When execution started
        finished_at: When execution finished
        duration_ms: Execution duration in milliseconds
        total_polls: Total number of poll requests made
    """

    execution_id: str
    status: ExecutionState
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    total_polls: int = 0


class ExecutionMonitor:
    """Monitors n8n workflow execution status.

    Polls the n8n API to track execution progress, handles timeouts,
    and provides progress callbacks for real-time updates (e.g., SSE).

    Example:
        >>> client = N8nApiClient(config)
        >>> monitor = ExecutionMonitor(client)
        >>>
        >>> # Simple wait for completion
        >>> result = await monitor.wait_for_completion("exec-123", timeout=120)
        >>> print(result.status)  # ExecutionState.COMPLETED
        >>>
        >>> # With progress callback
        >>> def on_progress(progress):
        ...     print(f"{progress.progress_pct}%: {progress.message}")
        >>> result = await monitor.wait_for_completion(
        ...     "exec-123", timeout=120, progress_callback=on_progress
        ... )
    """

    def __init__(
        self,
        client: N8nApiClient,
        config: Optional[MonitorConfig] = None,
    ):
        """Initialize the execution monitor.

        Args:
            client: N8nApiClient instance for API calls
            config: Monitor configuration (optional)
        """
        self._client = client
        self._config = config or MonitorConfig()
        self._active_monitors: Dict[str, bool] = {}

        logger.info(
            f"ExecutionMonitor initialized: poll_interval={self._config.poll_interval}s, "
            f"timeout={self._config.default_timeout}s"
        )

    async def wait_for_completion(
        self,
        execution_id: str,
        timeout: Optional[float] = None,
        progress_callback: Optional[Callable[[ExecutionProgress], None]] = None,
    ) -> MonitorResult:
        """Wait for an n8n execution to complete.

        Polls the execution status at increasing intervals until the
        execution completes, fails, or times out.

        Args:
            execution_id: n8n execution ID to monitor
            timeout: Timeout in seconds (default from config)
            progress_callback: Optional callback for progress updates

        Returns:
            MonitorResult with final status and output
        """
        timeout = timeout or self._config.default_timeout
        self._active_monitors[execution_id] = True
        poll_count = 0
        error_count = 0
        current_interval = self._config.poll_interval
        started_at = datetime.utcnow()
        deadline = started_at + timedelta(seconds=timeout)
        last_progress_time = datetime.utcnow()

        logger.info(
            f"Monitoring execution {execution_id}: timeout={timeout}s"
        )

        try:
            while datetime.utcnow() < deadline:
                if not self._active_monitors.get(execution_id, False):
                    logger.info(f"Monitoring cancelled for {execution_id}")
                    return MonitorResult(
                        execution_id=execution_id,
                        status=ExecutionState.CANCELLED,
                        total_polls=poll_count,
                    )

                # Poll execution status
                try:
                    execution = await self._client.get_execution(execution_id)
                    poll_count += 1
                    error_count = 0  # Reset on success

                    state = self._map_status(execution.get("status", "unknown"))
                    exec_started = execution.get("startedAt")
                    exec_finished = execution.get("stoppedAt")

                    # Send progress update
                    now = datetime.utcnow()
                    if (
                        progress_callback
                        and (now - last_progress_time).total_seconds()
                        >= self._config.progress_update_interval
                    ):
                        elapsed = (now - started_at).total_seconds()
                        progress_pct = min(
                            (elapsed / timeout) * 100, 99.0
                        ) if state == ExecutionState.RUNNING else (
                            100.0 if state == ExecutionState.COMPLETED else 0.0
                        )

                        progress = ExecutionProgress(
                            execution_id=execution_id,
                            state=state,
                            progress_pct=progress_pct,
                            message=f"Execution {state.value} (poll #{poll_count})",
                            started_at=started_at,
                            poll_count=poll_count,
                        )
                        try:
                            progress_callback(progress)
                        except Exception as e:
                            logger.warning(f"Progress callback error: {e}")
                        last_progress_time = now

                    # Check terminal states
                    if state == ExecutionState.COMPLETED:
                        duration = None
                        if exec_started and exec_finished:
                            duration = self._parse_duration(exec_started, exec_finished)

                        # Send final progress
                        if progress_callback:
                            progress_callback(ExecutionProgress(
                                execution_id=execution_id,
                                state=ExecutionState.COMPLETED,
                                progress_pct=100.0,
                                message="Execution completed successfully",
                                output_data=execution.get("data"),
                                poll_count=poll_count,
                            ))

                        return MonitorResult(
                            execution_id=execution_id,
                            status=ExecutionState.COMPLETED,
                            output_data=execution.get("data"),
                            started_at=started_at,
                            finished_at=datetime.utcnow(),
                            duration_ms=duration,
                            total_polls=poll_count,
                        )

                    if state == ExecutionState.FAILED:
                        error_msg = self._extract_error(execution)

                        if progress_callback:
                            progress_callback(ExecutionProgress(
                                execution_id=execution_id,
                                state=ExecutionState.FAILED,
                                progress_pct=0.0,
                                message="Execution failed",
                                error=error_msg,
                                poll_count=poll_count,
                            ))

                        return MonitorResult(
                            execution_id=execution_id,
                            status=ExecutionState.FAILED,
                            error=error_msg,
                            started_at=started_at,
                            finished_at=datetime.utcnow(),
                            total_polls=poll_count,
                        )

                except N8nNotFoundError:
                    logger.warning(f"Execution {execution_id} not found")
                    return MonitorResult(
                        execution_id=execution_id,
                        status=ExecutionState.FAILED,
                        error=f"Execution {execution_id} not found in n8n",
                        total_polls=poll_count,
                    )

                except (N8nConnectionError, N8nApiError) as e:
                    error_count += 1
                    if error_count >= self._config.max_retries_on_error:
                        logger.error(
                            f"Monitoring {execution_id} failed after "
                            f"{error_count} consecutive errors: {e}"
                        )
                        return MonitorResult(
                            execution_id=execution_id,
                            status=ExecutionState.FAILED,
                            error=f"Monitoring failed after {error_count} errors: {e}",
                            total_polls=poll_count,
                        )
                    logger.warning(
                        f"Monitoring {execution_id} error #{error_count}: {e}, retrying"
                    )

                # Wait before next poll (exponential backoff)
                await asyncio.sleep(current_interval)
                current_interval = min(
                    current_interval * self._config.backoff_factor,
                    self._config.max_poll_interval,
                )

            # Timeout reached
            logger.warning(f"Monitoring {execution_id} timed out after {timeout}s")

            if progress_callback:
                progress_callback(ExecutionProgress(
                    execution_id=execution_id,
                    state=ExecutionState.TIMED_OUT,
                    progress_pct=0.0,
                    message=f"Monitoring timed out after {timeout:.0f}s",
                    poll_count=poll_count,
                ))

            return MonitorResult(
                execution_id=execution_id,
                status=ExecutionState.TIMED_OUT,
                error=f"Monitoring timed out after {timeout:.0f}s ({poll_count} polls)",
                started_at=started_at,
                finished_at=datetime.utcnow(),
                total_polls=poll_count,
            )

        finally:
            self._active_monitors.pop(execution_id, None)

    def cancel(self, execution_id: str) -> bool:
        """Cancel monitoring for an execution.

        Args:
            execution_id: n8n execution ID

        Returns:
            True if monitoring was active and cancelled
        """
        if execution_id in self._active_monitors:
            self._active_monitors[execution_id] = False
            logger.info(f"Monitoring cancelled for {execution_id}")
            return True
        return False

    def is_monitoring(self, execution_id: str) -> bool:
        """Check if an execution is being monitored.

        Args:
            execution_id: n8n execution ID

        Returns:
            True if actively monitoring
        """
        return self._active_monitors.get(execution_id, False)

    @property
    def active_count(self) -> int:
        """Get number of active monitors."""
        return sum(1 for v in self._active_monitors.values() if v)

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _map_status(n8n_status: str) -> ExecutionState:
        """Map n8n execution status to ExecutionState.

        Args:
            n8n_status: Status string from n8n API

        Returns:
            Corresponding ExecutionState
        """
        status_map = {
            "new": ExecutionState.PENDING,
            "running": ExecutionState.RUNNING,
            "success": ExecutionState.COMPLETED,
            "error": ExecutionState.FAILED,
            "waiting": ExecutionState.RUNNING,
            "crashed": ExecutionState.FAILED,
        }
        return status_map.get(n8n_status.lower(), ExecutionState.UNKNOWN)

    @staticmethod
    def _extract_error(execution: Dict[str, Any]) -> str:
        """Extract error message from an n8n execution response.

        Args:
            execution: n8n execution response dict

        Returns:
            Error message string
        """
        # Check various locations for error info
        if "error" in execution:
            error = execution["error"]
            if isinstance(error, dict):
                return error.get("message", str(error))
            return str(error)

        data = execution.get("data", {})
        if isinstance(data, dict):
            result_data = data.get("resultData", {})
            if isinstance(result_data, dict):
                error = result_data.get("error", {})
                if isinstance(error, dict):
                    return error.get("message", "Unknown execution error")
                if error:
                    return str(error)

        return "Execution failed with unknown error"

    @staticmethod
    def _parse_duration(started_at: str, stopped_at: str) -> Optional[int]:
        """Parse duration from n8n timestamp strings.

        Args:
            started_at: ISO format start time
            stopped_at: ISO format stop time

        Returns:
            Duration in milliseconds or None
        """
        try:
            start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            stop = datetime.fromisoformat(stopped_at.replace("Z", "+00:00"))
            return int((stop - start).total_seconds() * 1000)
        except (ValueError, TypeError):
            return None
