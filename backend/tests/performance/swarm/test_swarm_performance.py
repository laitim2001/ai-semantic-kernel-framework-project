"""
Agent Swarm Performance Tests

Performance tests for the Agent Swarm system.

Sprint 106 - Story 106-2: Performance Testing and Optimization

Performance Targets:
- SSE Event Latency: < 100ms
- Swarm API Response Time: < 200ms (P95)
- Worker Detail API: < 300ms (P95)
- Event Throughput: > 50 events/sec
- Memory Usage: < 50MB for 1000 events
"""

import asyncio
import gc
import sys
import time
import tracemalloc
from datetime import datetime
from statistics import mean, stdev, quantiles
from typing import List, Tuple
from unittest.mock import AsyncMock

import pytest

from src.integrations.swarm import (
    SwarmTracker,
    SwarmMode,
    WorkerType,
    SwarmStatus,
    WorkerStatus,
    AgentSwarmStatus,
    WorkerExecution,
)
from src.integrations.swarm.events import (
    SwarmEventEmitter,
    create_swarm_emitter,
)
from src.integrations.ag_ui.events import CustomEvent


# ============================================================================
# Test Configuration
# ============================================================================

THROUGHPUT_TARGET = 50  # events/sec
API_LATENCY_P95_TARGET = 200  # ms
WORKER_API_LATENCY_P95_TARGET = 300  # ms
SSE_LATENCY_TARGET = 100  # ms
MEMORY_LIMIT_MB = 50
HIGH_LOAD_EVENTS = 1000
CONCURRENT_WORKERS = 10


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def tracker():
    """Create a fresh SwarmTracker."""
    return SwarmTracker()


@pytest.fixture
def sample_swarm(tracker):
    """Create a sample swarm with workers for testing."""
    swarm = tracker.create_swarm(
        swarm_id="perf-test-swarm",
        mode=SwarmMode.PARALLEL,
    )

    for i in range(5):
        tracker.start_worker(
            "perf-test-swarm",
            f"worker-{i}",
            f"Worker{i}",
            WorkerType.ANALYST,
            f"role-{i}",
        )
        tracker.update_worker_progress("perf-test-swarm", f"worker-{i}", 50)

    return swarm


@pytest.fixture
def event_collector():
    """Create an event collector for measuring latency."""
    events: List[Tuple[CustomEvent, float]] = []

    async def collector(event: CustomEvent):
        events.append((event, time.time()))

    collector.events = events
    collector.start_time = time.time()
    return collector


@pytest.fixture
async def emitter(event_collector):
    """Create a SwarmEventEmitter with the event collector."""
    emitter = create_swarm_emitter(
        event_callback=event_collector,
        throttle_interval_ms=10,  # Fast for perf testing
        batch_size=10,
    )
    await emitter.start()
    event_collector.start_time = time.time()
    yield emitter
    await emitter.stop()


# ============================================================================
# Throughput Tests
# ============================================================================


class TestEventThroughput:
    """Test event throughput performance."""

    @pytest.mark.asyncio
    async def test_event_throughput(self, tracker, event_collector, emitter):
        """
        Test: Event throughput should be > 50 events/sec.

        This test measures how many events can be processed per second.
        """
        # Setup
        swarm = tracker.create_swarm("throughput-swarm", SwarmMode.PARALLEL)
        tracker.start_worker(
            "throughput-swarm", "worker-0", "Worker", WorkerType.ANALYST, "test"
        )

        swarm = tracker.get_swarm("throughput-swarm")
        worker = swarm.get_worker_by_id("worker-0")

        # Measure throughput
        events_sent = 0
        start_time = time.time()
        duration_target = 2.0  # seconds

        while time.time() - start_time < duration_target:
            await emitter.emit_worker_progress("throughput-swarm", worker)
            events_sent += 1

        # Wait for processing
        await asyncio.sleep(0.5)

        elapsed = time.time() - start_time
        throughput = events_sent / elapsed

        # Log results
        print(f"\n[Throughput Test]")
        print(f"  Events sent: {events_sent}")
        print(f"  Elapsed time: {elapsed:.2f}s")
        print(f"  Throughput: {throughput:.2f} events/sec")
        print(f"  Target: {THROUGHPUT_TARGET} events/sec")

        assert throughput > THROUGHPUT_TARGET, (
            f"Throughput {throughput:.2f} events/sec < {THROUGHPUT_TARGET} target"
        )

    @pytest.mark.asyncio
    async def test_batch_event_throughput(self, tracker, event_collector, emitter):
        """
        Test: Batch event sending should have higher throughput.
        """
        swarm = tracker.create_swarm("batch-swarm", SwarmMode.PARALLEL)

        for i in range(10):
            tracker.start_worker(
                "batch-swarm", f"w-{i}", f"Worker{i}", WorkerType.ANALYST, "test"
            )

        swarm = tracker.get_swarm("batch-swarm")

        # Send events for all workers
        events_sent = 0
        start_time = time.time()

        for _ in range(100):
            for worker in swarm.workers:
                await emitter.emit_worker_progress("batch-swarm", worker)
                events_sent += 1

        await asyncio.sleep(0.5)

        elapsed = time.time() - start_time
        throughput = events_sent / elapsed

        print(f"\n[Batch Throughput Test]")
        print(f"  Events sent: {events_sent}")
        print(f"  Throughput: {throughput:.2f} events/sec")

        assert throughput > THROUGHPUT_TARGET


# ============================================================================
# API Latency Tests
# ============================================================================


class TestAPILatency:
    """Test API response latency."""

    def test_tracker_get_swarm_latency(self, sample_swarm, tracker):
        """
        Test: SwarmTracker.get_swarm() should be < 5ms.
        """
        latencies: List[float] = []

        for _ in range(100):
            start = time.perf_counter()
            swarm = tracker.get_swarm("perf-test-swarm")
            elapsed = (time.perf_counter() - start) * 1000  # ms
            latencies.append(elapsed)

        avg_latency = mean(latencies)
        p95_latency = quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)

        print(f"\n[get_swarm Latency Test]")
        print(f"  Samples: {len(latencies)}")
        print(f"  Avg: {avg_latency:.3f}ms")
        print(f"  P95: {p95_latency:.3f}ms")
        print(f"  Max: {max(latencies):.3f}ms")

        assert avg_latency < 5, f"Average latency {avg_latency}ms > 5ms"

    def test_tracker_get_worker_latency(self, sample_swarm, tracker):
        """
        Test: Getting worker from swarm should be < 1ms.
        """
        swarm = tracker.get_swarm("perf-test-swarm")
        latencies: List[float] = []

        for _ in range(100):
            start = time.perf_counter()
            worker = swarm.get_worker_by_id("worker-0")
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)

        avg_latency = mean(latencies)
        p95_latency = quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)

        print(f"\n[get_worker Latency Test]")
        print(f"  Avg: {avg_latency:.4f}ms")
        print(f"  P95: {p95_latency:.4f}ms")

        assert avg_latency < 1, f"Average latency {avg_latency}ms > 1ms"

    def test_tracker_update_progress_latency(self, sample_swarm, tracker):
        """
        Test: Updating worker progress should be < 1ms.
        """
        latencies: List[float] = []

        for i in range(100):
            progress = i % 100
            start = time.perf_counter()
            tracker.update_worker_progress("perf-test-swarm", "worker-0", progress)
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)

        avg_latency = mean(latencies)
        p95_latency = quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)

        print(f"\n[update_progress Latency Test]")
        print(f"  Avg: {avg_latency:.4f}ms")
        print(f"  P95: {p95_latency:.4f}ms")

        assert avg_latency < 1

    def test_tracker_add_tool_call_latency(self, sample_swarm, tracker):
        """
        Test: Adding tool call should be < 2ms.
        """
        latencies: List[float] = []

        for i in range(100):
            start = time.perf_counter()
            tracker.add_worker_tool_call(
                "perf-test-swarm",
                "worker-0",
                tool_id=f"tc-{i}",
                tool_name="test_tool",
                is_mcp=True,
                input_params={"key": "value"},
            )
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)

        avg_latency = mean(latencies)
        p95_latency = quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)

        print(f"\n[add_tool_call Latency Test]")
        print(f"  Avg: {avg_latency:.4f}ms")
        print(f"  P95: {p95_latency:.4f}ms")

        assert avg_latency < 2


# ============================================================================
# Memory Usage Tests
# ============================================================================


class TestMemoryUsage:
    """Test memory usage under load."""

    def test_memory_usage_high_event_count(self, tracker):
        """
        Test: Memory usage should be < 50MB after 1000 events.
        """
        # Force garbage collection before test
        gc.collect()

        # Start memory tracking
        tracemalloc.start()
        initial_snapshot = tracemalloc.take_snapshot()

        # Create swarm and workers
        swarm = tracker.create_swarm("memory-swarm", SwarmMode.PARALLEL)

        for i in range(CONCURRENT_WORKERS):
            tracker.start_worker(
                "memory-swarm",
                f"worker-{i}",
                f"Worker{i}",
                WorkerType.ANALYST,
                f"role-{i}",
            )

        # Simulate high load
        for i in range(HIGH_LOAD_EVENTS):
            worker_idx = i % CONCURRENT_WORKERS

            # Add thinking content
            tracker.add_worker_thinking(
                "memory-swarm",
                f"worker-{worker_idx}",
                content=f"Thinking content block {i} with some detailed analysis...",
                token_count=50 + (i % 200),
            )

            # Add tool calls periodically
            if i % 10 == 0:
                tracker.add_worker_tool_call(
                    "memory-swarm",
                    f"worker-{worker_idx}",
                    tool_id=f"tc-{i}",
                    tool_name=f"tool_{i % 5}",
                    is_mcp=i % 2 == 0,
                    input_params={"query": f"query_{i}"},
                )
                tracker.update_tool_call_result(
                    "memory-swarm",
                    f"worker-{worker_idx}",
                    f"tc-{i}",
                    result={"result": f"result_{i}", "rows": i * 10},
                )

            # Update progress
            tracker.update_worker_progress(
                "memory-swarm",
                f"worker-{worker_idx}",
                (i * 100) // HIGH_LOAD_EVENTS,
            )

        # Take final memory snapshot
        final_snapshot = tracemalloc.take_snapshot()

        # Calculate memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        current_mb = current / (1024 * 1024)
        peak_mb = peak / (1024 * 1024)

        # Get top memory consumers
        top_stats = final_snapshot.compare_to(initial_snapshot, "lineno")[:10]

        print(f"\n[Memory Usage Test]")
        print(f"  Events processed: {HIGH_LOAD_EVENTS}")
        print(f"  Workers: {CONCURRENT_WORKERS}")
        print(f"  Current memory: {current_mb:.2f}MB")
        print(f"  Peak memory: {peak_mb:.2f}MB")
        print(f"  Target: < {MEMORY_LIMIT_MB}MB")
        print(f"\n  Top memory allocations:")
        for stat in top_stats[:5]:
            print(f"    {stat}")

        assert peak_mb < MEMORY_LIMIT_MB, (
            f"Peak memory {peak_mb:.2f}MB > {MEMORY_LIMIT_MB}MB limit"
        )

    def test_memory_cleanup_on_swarm_completion(self, tracker):
        """
        Test: Memory should be released when swarm completes.
        """
        gc.collect()
        tracemalloc.start()

        # Create and populate swarm
        swarm = tracker.create_swarm("cleanup-swarm", SwarmMode.SEQUENTIAL)
        tracker.start_worker(
            "cleanup-swarm", "worker-0", "Worker", WorkerType.ANALYST, "test"
        )

        for i in range(500):
            tracker.add_worker_thinking(
                "cleanup-swarm", "worker-0",
                content=f"Thinking block {i}...",
                token_count=100,
            )

        before_cleanup = tracemalloc.get_traced_memory()[0]

        # Complete and cleanup
        tracker.complete_worker("cleanup-swarm", "worker-0")
        tracker.complete_swarm("cleanup-swarm")

        # Force cleanup
        gc.collect()

        after_cleanup = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()

        print(f"\n[Memory Cleanup Test]")
        print(f"  Before cleanup: {before_cleanup / 1024 / 1024:.2f}MB")
        print(f"  After cleanup: {after_cleanup / 1024 / 1024:.2f}MB")


# ============================================================================
# Concurrent Access Tests
# ============================================================================


class TestConcurrentAccess:
    """Test performance under concurrent access."""

    def test_concurrent_worker_updates(self, tracker):
        """
        Test: Concurrent worker updates should not cause contention.
        """
        import threading

        swarm = tracker.create_swarm("concurrent-swarm", SwarmMode.PARALLEL)

        for i in range(CONCURRENT_WORKERS):
            tracker.start_worker(
                "concurrent-swarm",
                f"worker-{i}",
                f"Worker{i}",
                WorkerType.ANALYST,
                f"role-{i}",
            )

        errors: List[Exception] = []
        update_counts: List[int] = []

        def worker_updates(worker_id: str, updates: int):
            try:
                count = 0
                for i in range(updates):
                    tracker.update_worker_progress(
                        "concurrent-swarm", worker_id, i % 100
                    )
                    count += 1
                update_counts.append(count)
            except Exception as e:
                errors.append(e)

        # Start concurrent updates
        threads = []
        updates_per_worker = 100

        start_time = time.time()

        for i in range(CONCURRENT_WORKERS):
            t = threading.Thread(
                target=worker_updates,
                args=(f"worker-{i}", updates_per_worker),
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        elapsed = time.time() - start_time
        total_updates = sum(update_counts)
        throughput = total_updates / elapsed

        print(f"\n[Concurrent Access Test]")
        print(f"  Workers: {CONCURRENT_WORKERS}")
        print(f"  Updates per worker: {updates_per_worker}")
        print(f"  Total updates: {total_updates}")
        print(f"  Elapsed: {elapsed:.2f}s")
        print(f"  Throughput: {throughput:.0f} updates/sec")
        print(f"  Errors: {len(errors)}")

        assert len(errors) == 0, f"Concurrent access errors: {errors}"
        assert total_updates == CONCURRENT_WORKERS * updates_per_worker


# ============================================================================
# Event Emitter Performance Tests
# ============================================================================


class TestEventEmitterPerformance:
    """Test SwarmEventEmitter performance."""

    @pytest.mark.asyncio
    async def test_event_throttling_effectiveness(self, tracker, event_collector, emitter):
        """
        Test: Event throttling should reduce event volume.
        """
        swarm = tracker.create_swarm("throttle-perf-swarm", SwarmMode.SEQUENTIAL)
        tracker.start_worker(
            "throttle-perf-swarm", "worker-0", "Worker", WorkerType.ANALYST, "test"
        )

        swarm = tracker.get_swarm("throttle-perf-swarm")
        worker = swarm.get_worker_by_id("worker-0")

        # Send many rapid events
        rapid_events = 100

        for i in range(rapid_events):
            tracker.update_worker_progress("throttle-perf-swarm", "worker-0", i)
            swarm = tracker.get_swarm("throttle-perf-swarm")
            worker = swarm.get_worker_by_id("worker-0")
            await emitter.emit_worker_progress("throttle-perf-swarm", worker)

        # Wait for processing
        await asyncio.sleep(0.5)

        received_events = len(event_collector.events)
        reduction_ratio = 1 - (received_events / rapid_events)

        print(f"\n[Throttling Effectiveness Test]")
        print(f"  Events sent: {rapid_events}")
        print(f"  Events received: {received_events}")
        print(f"  Reduction ratio: {reduction_ratio:.1%}")

        # Throttling should reduce at least 50% of events
        assert reduction_ratio > 0.5, (
            f"Throttling only reduced {reduction_ratio:.1%} of events"
        )

    @pytest.mark.asyncio
    async def test_priority_event_latency(self, tracker, event_collector, emitter):
        """
        Test: Priority events (swarm_created, swarm_completed) should be immediate.
        """
        # Record start time
        start_time = time.time()
        event_collector.start_time = start_time

        # Emit priority event
        swarm = tracker.create_swarm("priority-swarm", SwarmMode.SEQUENTIAL)
        await emitter.emit_swarm_created(swarm, session_id="test")

        # Check latency
        await asyncio.sleep(0.1)

        if event_collector.events:
            event, receive_time = event_collector.events[0]
            latency_ms = (receive_time - start_time) * 1000

            print(f"\n[Priority Event Latency Test]")
            print(f"  Event: {event.event_name}")
            print(f"  Latency: {latency_ms:.2f}ms")
            print(f"  Target: < {SSE_LATENCY_TARGET}ms")

            assert latency_ms < SSE_LATENCY_TARGET, (
                f"Priority event latency {latency_ms}ms > {SSE_LATENCY_TARGET}ms"
            )


# ============================================================================
# Data Serialization Performance Tests
# ============================================================================


class TestSerializationPerformance:
    """Test data serialization performance."""

    def test_swarm_to_dict_performance(self, sample_swarm, tracker):
        """
        Test: AgentSwarmStatus.to_dict() should be < 1ms.
        """
        swarm = tracker.get_swarm("perf-test-swarm")

        # Add more data to make realistic
        for i in range(10):
            tracker.add_worker_thinking(
                "perf-test-swarm", "worker-0",
                content=f"Thinking block {i}...",
                token_count=100,
            )
            tracker.add_worker_tool_call(
                "perf-test-swarm", "worker-0",
                tool_id=f"tc-{i}",
                tool_name="test_tool",
                is_mcp=True,
                input_params={"key": "value"},
            )

        swarm = tracker.get_swarm("perf-test-swarm")
        latencies: List[float] = []

        for _ in range(100):
            start = time.perf_counter()
            data = swarm.to_dict()
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)

        avg_latency = mean(latencies)
        p95_latency = quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)

        print(f"\n[to_dict Performance Test]")
        print(f"  Avg: {avg_latency:.3f}ms")
        print(f"  P95: {p95_latency:.3f}ms")
        print(f"  Dict keys: {len(data)}")

        assert avg_latency < 1, f"to_dict avg latency {avg_latency}ms > 1ms"

    def test_swarm_to_json_performance(self, sample_swarm, tracker):
        """
        Test: AgentSwarmStatus.to_json() should be < 5ms.
        """
        swarm = tracker.get_swarm("perf-test-swarm")
        latencies: List[float] = []

        for _ in range(100):
            start = time.perf_counter()
            json_str = swarm.to_json()
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)

        avg_latency = mean(latencies)
        p95_latency = quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)

        print(f"\n[to_json Performance Test]")
        print(f"  Avg: {avg_latency:.3f}ms")
        print(f"  P95: {p95_latency:.3f}ms")
        print(f"  JSON size: {len(json_str)} bytes")

        assert avg_latency < 5, f"to_json avg latency {avg_latency}ms > 5ms"


# ============================================================================
# Performance Summary Report
# ============================================================================


class TestPerformanceSummary:
    """Generate performance summary."""

    def test_generate_performance_report(self, tracker, sample_swarm, capsys):
        """
        Generate a summary performance report.
        """
        print("\n" + "=" * 60)
        print("AGENT SWARM PERFORMANCE REPORT")
        print("=" * 60)
        print(f"\nTest Date: {datetime.now().isoformat()}")
        print(f"\nConfiguration:")
        print(f"  Throughput Target: {THROUGHPUT_TARGET} events/sec")
        print(f"  API Latency P95 Target: {API_LATENCY_P95_TARGET}ms")
        print(f"  SSE Latency Target: {SSE_LATENCY_TARGET}ms")
        print(f"  Memory Limit: {MEMORY_LIMIT_MB}MB")
        print(f"  High Load Events: {HIGH_LOAD_EVENTS}")
        print(f"  Concurrent Workers: {CONCURRENT_WORKERS}")
        print("\n" + "=" * 60)

        # Simple latency measurements
        latencies = []
        for _ in range(100):
            start = time.perf_counter()
            swarm = tracker.get_swarm("perf-test-swarm")
            latencies.append((time.perf_counter() - start) * 1000)

        print(f"\nget_swarm Latency:")
        print(f"  Min: {min(latencies):.4f}ms")
        print(f"  Avg: {mean(latencies):.4f}ms")
        print(f"  Max: {max(latencies):.4f}ms")

        print("\n" + "=" * 60)
        print("REPORT COMPLETE")
        print("=" * 60)


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
