"""
File: backend/tests/unit/runtime/workers/test_agent_loop_worker.py
Purpose: Unit tests for AgentLoopWorker against MockQueueBackend (no broker).
Category: Tests / Runtime
Scope: Phase 49 / Sprint 49.4 Day 2

Coverage:
- Worker init + happy-path execution
- Worker poll-and-execute with default handler
- Worker cancel propagation
- Worker retry on transient error
"""

from __future__ import annotations

import pytest

from runtime.workers import (
    AgentLoopWorker,
    MockQueueBackend,
    TaskEnvelope,
    TaskStatus,
    WorkerConfig,
)


@pytest.fixture
def backend() -> MockQueueBackend:
    return MockQueueBackend()


@pytest.fixture
def fast_config() -> WorkerConfig:
    """Config with near-zero backoff so retry tests don't add real wall time."""
    return WorkerConfig(
        poll_interval_sec=0.01, retry_backoff_base_sec=0.001, retry_backoff_factor=1.0
    )


@pytest.mark.asyncio
async def test_worker_init_default(backend: MockQueueBackend) -> None:
    """Worker constructs with sensible defaults; default handler attached."""
    worker = AgentLoopWorker(backend)
    assert worker.backend is backend
    assert worker.handler is not None
    assert worker.config.poll_interval_sec > 0


@pytest.mark.asyncio
async def test_worker_poll_and_execute_returns_result(backend: MockQueueBackend) -> None:
    """Submit one task; worker.run_once() executes default handler and writes COMPLETED."""
    envelope = TaskEnvelope.new(
        tenant_id="tenant-a",
        payload={"hello": "world"},
        trace_id="trace-001",
    )
    await backend.submit(envelope)

    worker = AgentLoopWorker(backend)
    result = await worker.run_once()

    assert result is not None
    assert result.status == TaskStatus.COMPLETED
    assert result.task_id == envelope.task_id
    # default handler echoes the payload
    assert result.result == {"echo": {"hello": "world"}}


@pytest.mark.asyncio
async def test_worker_cancel_returns_cancelled_status(backend: MockQueueBackend) -> None:
    """Cancel before run_once() → run_once skips execution + reports CANCELLED."""
    envelope = TaskEnvelope.new(tenant_id="tenant-a", payload={"x": 1}, trace_id="trace-002")
    await backend.submit(envelope)
    await backend.cancel(envelope.task_id)

    worker = AgentLoopWorker(backend)
    # The cancelled task was removed from pending → run_once returns None
    result = await worker.run_once()
    assert result is None  # queue empty after cancel

    # but polling the task_id directly shows CANCELLED
    poll = await backend.poll(envelope.task_id)
    assert poll.status == TaskStatus.CANCELLED


@pytest.mark.asyncio
async def test_worker_retry_then_succeed(
    backend: MockQueueBackend, fast_config: WorkerConfig
) -> None:
    """Handler raises on first 2 attempts, succeeds on 3rd. Retry within max_retries=3."""
    call_count = 0

    async def flaky_handler(envelope: TaskEnvelope) -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RuntimeError(f"transient failure {call_count}")
        return {"attempts": call_count}

    envelope = TaskEnvelope.new(
        tenant_id="tenant-a",
        payload={"task": "flaky"},
        trace_id="trace-003",
        max_retries=3,
    )
    await backend.submit(envelope)

    worker = AgentLoopWorker(backend, handler=flaky_handler, config=fast_config)
    result = await worker.run_once()

    assert result is not None
    assert result.status == TaskStatus.COMPLETED
    assert result.result == {"attempts": 3}
    assert call_count == 3


@pytest.mark.asyncio
async def test_worker_retry_exhausted_marks_failed(
    backend: MockQueueBackend, fast_config: WorkerConfig
) -> None:
    """Handler always fails; worker exhausts max_retries and writes FAILED."""

    async def always_fails(envelope: TaskEnvelope) -> dict[str, object]:
        raise RuntimeError("permanent failure")

    envelope = TaskEnvelope.new(
        tenant_id="tenant-a",
        payload={"x": 1},
        trace_id="trace-004",
        max_retries=2,
    )
    await backend.submit(envelope)

    worker = AgentLoopWorker(backend, handler=always_fails, config=fast_config)
    result = await worker.run_once()

    assert result is not None
    assert result.status == TaskStatus.FAILED
    assert result.error is not None
    assert "permanent failure" in result.error
