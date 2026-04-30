# =============================================================================
# IPA Platform - Sandbox Orchestrator
# =============================================================================
# Sprint 77: S77-1 - Sandbox Architecture Design & Orchestrator (13 pts)
#
# The SandboxOrchestrator manages a pool of sandbox worker processes,
# routing execution requests to available workers and handling lifecycle.
#
# Architecture:
#   ┌─────────────────────────────────────────────────────────────┐
#   │                    SandboxOrchestrator                       │
#   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
#   │  │  Worker 1   │  │  Worker 2   │  │  Worker N   │         │
#   │  │  user: A    │  │  user: B    │  │  user: A    │  (pool) │
#   │  │  idle: 30s  │  │  busy       │  │  busy       │         │
#   │  └─────────────┘  └─────────────┘  └─────────────┘         │
#   └─────────────────────────────────────────────────────────────┘
#
# Features:
#   - Process pool with configurable size
#   - Per-user worker affinity for session continuity
#   - Idle worker cleanup
#   - Graceful shutdown
#   - Automatic worker restart on failure
#
# =============================================================================

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional
from datetime import datetime

from src.core.sandbox.config import ProcessSandboxConfig
from src.core.sandbox.worker import SandboxWorker


logger = logging.getLogger(__name__)


@dataclass
class WorkerInfo:
    """Information about a worker in the pool.

    Attributes:
        worker: The SandboxWorker instance
        user_id: User ID this worker is serving
        created_at: When the worker was created
        last_used_at: When the worker was last used
        request_count: Number of requests processed
        is_busy: Whether the worker is currently processing
    """
    worker: SandboxWorker
    user_id: str
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: datetime = field(default_factory=datetime.now)
    request_count: int = 0
    is_busy: bool = False


class SandboxOrchestrator:
    """Orchestrator for managing sandbox worker processes.

    The orchestrator maintains a pool of SandboxWorker processes,
    routing execution requests to available workers based on user
    affinity and availability.

    Example:
        config = ProcessSandboxConfig(max_workers=5)
        orchestrator = SandboxOrchestrator(config)

        # Execute a request
        result = await orchestrator.execute(
            user_id="user-123",
            message="Analyze this code",
            attachments=[],
            session_id="session-456"
        )

        # Stream execution with events
        async for event in orchestrator.execute_stream(
            user_id="user-123",
            message="Generate report",
            attachments=[],
            session_id="session-456"
        ):
            print(event)

        # Cleanup
        await orchestrator.shutdown()

    Attributes:
        config: Sandbox configuration
        workers: Dictionary of active workers by ID
        user_worker_map: Mapping of user IDs to worker IDs
        lock: Asyncio lock for thread-safe operations
        cleanup_task: Background task for idle worker cleanup
    """

    def __init__(self, config: Optional[ProcessSandboxConfig] = None):
        """Initialize the orchestrator.

        Args:
            config: Optional sandbox configuration. Uses default if not provided.
        """
        self.config = config or ProcessSandboxConfig()
        self._workers: Dict[str, WorkerInfo] = {}
        self._user_worker_map: Dict[str, str] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        self._started = False
        self._worker_counter = 0

        # Validate configuration
        errors = self.config.validate()
        if errors:
            raise ValueError(f"Invalid sandbox configuration: {errors}")

        logger.info(
            f"SandboxOrchestrator initialized with max_workers={self.config.max_workers}"
        )

    async def start(self) -> None:
        """Start the orchestrator and background tasks.

        This method starts the background cleanup task for idle workers.
        Call this before using the orchestrator.
        """
        if self._started:
            return

        self._shutdown_event.clear()
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._started = True

        logger.info("SandboxOrchestrator started")

    async def shutdown(self) -> None:
        """Gracefully shutdown the orchestrator.

        Stops all workers and the cleanup task. Waits for busy workers
        to complete their current requests.
        """
        if not self._started:
            return

        logger.info("SandboxOrchestrator shutting down...")
        self._shutdown_event.set()

        # Stop cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Stop all workers
        async with self._lock:
            for worker_id, info in list(self._workers.items()):
                try:
                    await info.worker.stop()
                except Exception as e:
                    logger.error(f"Error stopping worker {worker_id}: {e}")

            self._workers.clear()
            self._user_worker_map.clear()

        self._started = False
        logger.info("SandboxOrchestrator shutdown complete")

    async def execute(
        self,
        user_id: str,
        message: str,
        attachments: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a request in a sandbox worker.

        Routes the request to an available worker, creating a new one
        if necessary and pool capacity allows.

        Args:
            user_id: User identifier for sandbox isolation
            message: The message/prompt to execute
            attachments: List of file attachments
            session_id: Optional session identifier
            config: Optional execution configuration

        Returns:
            Execution result dictionary containing:
                - content: Response content
                - tool_calls: List of tool calls made
                - tokens_used: Token usage statistics
                - duration: Execution duration in seconds

        Raises:
            RuntimeError: If orchestrator is not started or shutting down
            TimeoutError: If execution exceeds timeout
            Exception: If worker execution fails
        """
        if not self._started:
            raise RuntimeError("Orchestrator not started. Call start() first.")

        if self._shutdown_event.is_set():
            raise RuntimeError("Orchestrator is shutting down")

        # Get or create a worker for this user
        worker_info = await self._get_or_create_worker(user_id)

        try:
            worker_info.is_busy = True
            worker_info.request_count += 1

            # Execute the request
            start_time = time.time()
            result = await asyncio.wait_for(
                worker_info.worker.execute(
                    message=message,
                    attachments=attachments,
                    session_id=session_id,
                    config=config or {}
                ),
                timeout=self.config.worker_timeout
            )

            worker_info.last_used_at = datetime.now()
            result["duration"] = time.time() - start_time

            logger.debug(
                f"Worker {worker_info.worker.worker_id} completed request "
                f"for user {user_id} in {result['duration']:.2f}s"
            )

            return result

        except asyncio.TimeoutError:
            logger.error(
                f"Worker timeout for user {user_id} after {self.config.worker_timeout}s"
            )
            # Kill and remove the timed-out worker
            await self._remove_worker(worker_info.worker.worker_id)
            raise TimeoutError(f"Execution timed out after {self.config.worker_timeout} seconds")

        except Exception as e:
            logger.error(f"Worker execution error for user {user_id}: {e}")
            # Check if worker is still healthy
            if not worker_info.worker.is_running:
                await self._remove_worker(worker_info.worker.worker_id)
            raise

        finally:
            worker_info.is_busy = False

            # Check if worker should be recycled
            if worker_info.request_count >= self.config.max_requests_per_worker:
                logger.info(
                    f"Worker {worker_info.worker.worker_id} reached max requests, recycling"
                )
                await self._remove_worker(worker_info.worker.worker_id)

    async def execute_stream(
        self,
        user_id: str,
        message: str,
        attachments: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Execute a request with streaming events.

        Similar to execute() but yields events as they occur.

        Args:
            user_id: User identifier for sandbox isolation
            message: The message/prompt to execute
            attachments: List of file attachments
            session_id: Optional session identifier
            config: Optional execution configuration

        Yields:
            Event dictionaries containing:
                - type: Event type (TEXT_DELTA, TOOL_CALL, etc.)
                - data: Event-specific data

        Raises:
            RuntimeError: If orchestrator is not started or shutting down
            TimeoutError: If execution exceeds timeout
            Exception: If worker execution fails
        """
        if not self._started:
            raise RuntimeError("Orchestrator not started. Call start() first.")

        if self._shutdown_event.is_set():
            raise RuntimeError("Orchestrator is shutting down")

        worker_info = await self._get_or_create_worker(user_id)

        try:
            worker_info.is_busy = True
            worker_info.request_count += 1

            async for event in worker_info.worker.execute_stream(
                message=message,
                attachments=attachments,
                session_id=session_id,
                config=config or {}
            ):
                yield event

            worker_info.last_used_at = datetime.now()

        except Exception as e:
            logger.error(f"Worker stream error for user {user_id}: {e}")
            if not worker_info.worker.is_running:
                await self._remove_worker(worker_info.worker.worker_id)
            raise

        finally:
            worker_info.is_busy = False

    async def _get_or_create_worker(self, user_id: str) -> WorkerInfo:
        """Get an existing worker for the user or create a new one.

        Implements user affinity - tries to reuse the same worker for
        a user to maintain session context.

        Args:
            user_id: User identifier

        Returns:
            WorkerInfo for the assigned worker

        Raises:
            RuntimeError: If pool is at capacity and no workers available
        """
        async with self._lock:
            # Check if user has an existing, available worker
            if user_id in self._user_worker_map:
                worker_id = self._user_worker_map[user_id]
                if worker_id in self._workers:
                    info = self._workers[worker_id]
                    if not info.is_busy and info.worker.is_running:
                        logger.debug(f"Reusing worker {worker_id} for user {user_id}")
                        return info

            # Find an available idle worker or create new one
            for worker_id, info in self._workers.items():
                if not info.is_busy and info.worker.is_running:
                    # Reassign idle worker to this user
                    old_user = info.user_id
                    if old_user in self._user_worker_map:
                        del self._user_worker_map[old_user]

                    info.user_id = user_id
                    self._user_worker_map[user_id] = worker_id
                    logger.debug(f"Reassigning worker {worker_id} to user {user_id}")
                    return info

            # Check pool capacity
            if len(self._workers) >= self.config.max_workers:
                raise RuntimeError(
                    f"Worker pool at capacity ({self.config.max_workers}). "
                    "All workers busy."
                )

            # Create new worker
            worker_info = await self._create_worker(user_id)
            return worker_info

    async def _create_worker(self, user_id: str) -> WorkerInfo:
        """Create a new sandbox worker.

        Args:
            user_id: User identifier for the worker

        Returns:
            WorkerInfo for the new worker
        """
        self._worker_counter += 1
        worker_id = f"worker-{self._worker_counter}"

        # Ensure sandbox directory exists
        sandbox_dir = self.config.ensure_user_sandbox_dir(user_id)

        worker = SandboxWorker(
            worker_id=worker_id,
            config=self.config,
            user_id=user_id,
            sandbox_dir=sandbox_dir
        )

        # Start the worker process
        await asyncio.wait_for(
            worker.start(),
            timeout=self.config.startup_timeout
        )

        worker_info = WorkerInfo(
            worker=worker,
            user_id=user_id
        )

        self._workers[worker_id] = worker_info
        self._user_worker_map[user_id] = worker_id

        logger.info(
            f"Created worker {worker_id} for user {user_id} "
            f"(pool size: {len(self._workers)})"
        )

        return worker_info

    async def _remove_worker(self, worker_id: str) -> None:
        """Remove a worker from the pool.

        Args:
            worker_id: Worker identifier to remove
        """
        async with self._lock:
            if worker_id not in self._workers:
                return

            info = self._workers[worker_id]

            # Stop the worker
            try:
                await info.worker.stop()
            except Exception as e:
                logger.error(f"Error stopping worker {worker_id}: {e}")

            # Remove from maps
            del self._workers[worker_id]
            if info.user_id in self._user_worker_map:
                if self._user_worker_map[info.user_id] == worker_id:
                    del self._user_worker_map[info.user_id]

            logger.info(f"Removed worker {worker_id} (pool size: {len(self._workers)})")

    async def _cleanup_loop(self) -> None:
        """Background task to cleanup idle workers.

        Runs periodically to remove workers that have been idle
        longer than the configured timeout.
        """
        cleanup_interval = 60  # Check every 60 seconds

        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(cleanup_interval)
                await self._cleanup_idle_workers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup_idle_workers(self) -> None:
        """Remove workers that have been idle too long."""
        now = datetime.now()
        idle_threshold = self.config.idle_timeout

        workers_to_remove = []

        async with self._lock:
            for worker_id, info in self._workers.items():
                if info.is_busy:
                    continue

                idle_seconds = (now - info.last_used_at).total_seconds()
                if idle_seconds > idle_threshold:
                    workers_to_remove.append(worker_id)
                    logger.debug(
                        f"Worker {worker_id} idle for {idle_seconds:.0f}s, "
                        f"marking for cleanup"
                    )

        for worker_id in workers_to_remove:
            await self._remove_worker(worker_id)

        if workers_to_remove:
            logger.info(f"Cleaned up {len(workers_to_remove)} idle workers")

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get statistics about the worker pool.

        Returns:
            Dictionary containing:
                - total_workers: Total workers in pool
                - busy_workers: Currently busy workers
                - idle_workers: Currently idle workers
                - max_workers: Maximum pool size
                - user_count: Number of unique users with workers
        """
        busy_count = sum(1 for info in self._workers.values() if info.is_busy)
        idle_count = len(self._workers) - busy_count

        return {
            "total_workers": len(self._workers),
            "busy_workers": busy_count,
            "idle_workers": idle_count,
            "max_workers": self.config.max_workers,
            "user_count": len(self._user_worker_map),
        }

    @property
    def is_running(self) -> bool:
        """Check if the orchestrator is running."""
        return self._started and not self._shutdown_event.is_set()
