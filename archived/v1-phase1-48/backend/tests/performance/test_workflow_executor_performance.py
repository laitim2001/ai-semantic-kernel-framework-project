# =============================================================================
# IPA Platform - WorkflowExecutor Performance Tests
# =============================================================================
# Sprint 18: S18-4 性能測試和優化 (5 points)
#
# This module contains performance tests for WorkflowExecutor and
# Phase 3 integration components.
#
# Performance Test Categories:
#   1. Concurrent execution throughput
#   2. Nested workflow depth performance
#   3. Checkpoint save/restore latency
#   4. Memory usage patterns
#   5. Request/response coordination overhead
#
# Author: IPA Platform Team
# Sprint: 18 - WorkflowExecutor 和整合
# Created: 2025-12-05
# =============================================================================

import pytest
import asyncio
import time
import sys
from uuid import uuid4
from typing import List, Dict, Any
from dataclasses import dataclass

from src.integrations.agent_framework.builders.workflow_executor import (
    WorkflowExecutorAdapter,
    WorkflowExecutorStatus,
    WorkflowRunState,
    WorkflowRunResult,
    WorkflowOutput,
    ExecutionContext,
    SimpleWorkflow,
    create_workflow_executor,
)

from src.integrations.agent_framework.builders.workflow_executor_migration import (
    NestedWorkflowManagerAdapter,
    NestedExecutionContextLegacy,
    SubWorkflowReferenceLegacy,
    NestedWorkflowConfigLegacy,
    migrate_nested_workflow_manager,
    create_migration_context,
)


# =============================================================================
# Performance Test Utilities
# =============================================================================


@dataclass
class PerformanceMetrics:
    """Container for performance test metrics."""
    test_name: str
    duration_seconds: float
    operations_count: int
    throughput_per_second: float
    avg_latency_ms: float
    max_latency_ms: float
    min_latency_ms: float
    memory_delta_mb: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "duration_seconds": round(self.duration_seconds, 4),
            "operations_count": self.operations_count,
            "throughput_per_second": round(self.throughput_per_second, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "max_latency_ms": round(self.max_latency_ms, 2),
            "min_latency_ms": round(self.min_latency_ms, 2),
            "memory_delta_mb": round(self.memory_delta_mb, 2),
        }


def calculate_metrics(
    test_name: str,
    latencies: List[float],
    total_duration: float,
) -> PerformanceMetrics:
    """Calculate performance metrics from latency data."""
    count = len(latencies)
    avg_latency = sum(latencies) / count if count > 0 else 0
    max_latency = max(latencies) if latencies else 0
    min_latency = min(latencies) if latencies else 0
    throughput = count / total_duration if total_duration > 0 else 0

    return PerformanceMetrics(
        test_name=test_name,
        duration_seconds=total_duration,
        operations_count=count,
        throughput_per_second=throughput,
        avg_latency_ms=avg_latency * 1000,
        max_latency_ms=max_latency * 1000,
        min_latency_ms=min_latency * 1000,
    )


# =============================================================================
# Test Category 1: Concurrent Execution Throughput
# =============================================================================


class TestConcurrentThroughput:
    """Test concurrent execution throughput."""

    @pytest.mark.asyncio
    async def test_sequential_execution_baseline(self):
        """Establish baseline with sequential execution."""
        async def simple_process(data, responses):
            return {"result": data}

        workflow = SimpleWorkflow(id="seq-wf", executor_fn=simple_process)
        executor = create_workflow_executor(id="seq-exec", workflow=workflow)
        executor.build()

        latencies = []
        total_count = 100

        start_time = time.time()
        for i in range(total_count):
            op_start = time.time()
            await executor.run({"i": i})
            latencies.append(time.time() - op_start)
        total_duration = time.time() - start_time

        metrics = calculate_metrics("sequential_baseline", latencies, total_duration)

        # Verify baseline performance
        assert metrics.avg_latency_ms < 50  # Should be fast
        assert metrics.throughput_per_second > 20  # At least 20 ops/sec

    @pytest.mark.asyncio
    async def test_concurrent_10_executors(self):
        """Test throughput with 10 concurrent executors."""
        async def process(data, responses):
            await asyncio.sleep(0.001)  # Simulate minimal work
            return {"result": data}

        # Create 10 executors
        executors = []
        for i in range(10):
            workflow = SimpleWorkflow(id=f"wf-{i}", executor_fn=process)
            executor = create_workflow_executor(id=f"exec-{i}", workflow=workflow)
            executor.build()
            executors.append(executor)

        latencies = []
        total_count = 100

        start_time = time.time()
        for batch_start in range(0, total_count, 10):
            batch_tasks = [
                executors[i].run({"batch": batch_start, "i": i})
                for i in range(10)
            ]
            op_start = time.time()
            await asyncio.gather(*batch_tasks)
            latencies.append(time.time() - op_start)
        total_duration = time.time() - start_time

        metrics = calculate_metrics("concurrent_10", latencies, total_duration)

        # Concurrent should be faster than sequential
        assert metrics.throughput_per_second > 10

    @pytest.mark.asyncio
    async def test_concurrent_50_executors(self):
        """Test throughput with 50 concurrent executors."""
        async def process(data, responses):
            return {"result": data}

        # Create 50 executors
        executors = []
        for i in range(50):
            workflow = SimpleWorkflow(id=f"wf-{i}", executor_fn=process)
            executor = create_workflow_executor(id=f"exec-{i}", workflow=workflow)
            executor.build()
            executors.append(executor)

        start_time = time.time()
        tasks = [executor.run({"i": i}) for i, executor in enumerate(executors)]
        results = await asyncio.gather(*tasks)
        total_duration = time.time() - start_time

        # All should complete
        assert all(r.status == WorkflowExecutorStatus.COMPLETED for r in results)

        # Should complete in reasonable time
        assert total_duration < 5.0  # Under 5 seconds for 50 concurrent


# =============================================================================
# Test Category 2: Nested Workflow Depth Performance
# =============================================================================


class TestNestedDepthPerformance:
    """Test nested workflow depth performance."""

    @pytest.mark.asyncio
    async def test_depth_1_latency(self):
        """Test latency at depth 1."""
        manager = migrate_nested_workflow_manager("depth-1-test")

        async def executor_fn(data, responses):
            return {"depth": 1}

        parent_id = uuid4()
        sub_ref = SubWorkflowReferenceLegacy(
            id=uuid4(),
            parent_workflow_id=parent_id,
            workflow_id=uuid4(),
            definition=None,
            config=NestedWorkflowConfigLegacy(max_depth=5),
        )

        await manager.register_sub_workflow(parent_id, sub_ref, executor_fn)

        latencies = []
        for _ in range(50):
            ctx = create_migration_context(workflow_id=parent_id, depth=0)
            start = time.time()
            await manager.execute_sub_workflow(ctx, sub_ref)
            latencies.append(time.time() - start)

        avg_latency = sum(latencies) / len(latencies) * 1000
        assert avg_latency < 100  # Under 100ms average

    @pytest.mark.asyncio
    async def test_depth_scaling(self):
        """Test how latency scales with depth."""
        depth_latencies = {}

        for max_depth in [1, 2, 3, 4, 5]:
            manager = migrate_nested_workflow_manager(
                f"depth-{max_depth}-test",
                max_global_depth=max_depth + 1,
            )

            async def executor_fn(data, responses):
                return {"depth": max_depth}

            parent_id = uuid4()
            sub_ref = SubWorkflowReferenceLegacy(
                id=uuid4(),
                parent_workflow_id=parent_id,
                workflow_id=uuid4(),
                definition=None,
                config=NestedWorkflowConfigLegacy(max_depth=max_depth + 1),
            )

            await manager.register_sub_workflow(parent_id, sub_ref, executor_fn)

            latencies = []
            for _ in range(20):
                ctx = create_migration_context(
                    workflow_id=parent_id,
                    depth=max_depth - 1,
                )
                start = time.time()
                await manager.execute_sub_workflow(ctx, sub_ref)
                latencies.append(time.time() - start)

            depth_latencies[max_depth] = sum(latencies) / len(latencies) * 1000

        # Verify latency doesn't grow exponentially
        for depth in range(2, 6):
            # Each depth should not more than double the latency
            assert depth_latencies[depth] < depth_latencies[depth - 1] * 3


# =============================================================================
# Test Category 3: Checkpoint Save/Restore Latency
# =============================================================================


class TestCheckpointPerformance:
    """Test checkpoint save/restore performance."""

    @pytest.mark.asyncio
    async def test_checkpoint_save_latency(self):
        """Test checkpoint save latency."""
        async def process(data, responses):
            return {"result": data}

        workflow = SimpleWorkflow(id="ckpt-wf", executor_fn=process)
        executor = create_workflow_executor(id="ckpt-exec", workflow=workflow)
        executor.build()

        latencies = []
        for _ in range(100):
            start = time.time()
            await executor.on_checkpoint_save()
            latencies.append(time.time() - start)

        avg_latency = sum(latencies) / len(latencies) * 1000
        max_latency = max(latencies) * 1000

        assert avg_latency < 10  # Under 10ms average
        assert max_latency < 50  # Under 50ms max

    @pytest.mark.asyncio
    async def test_checkpoint_restore_latency(self):
        """Test checkpoint restore latency."""
        async def process(data, responses):
            return {"result": data}

        workflow = SimpleWorkflow(id="ckpt-wf", executor_fn=process)
        executor = create_workflow_executor(id="ckpt-exec", workflow=workflow)
        executor.build()

        # Save checkpoint
        checkpoint = await executor.on_checkpoint_save()

        latencies = []
        for _ in range(100):
            start = time.time()
            await executor.on_checkpoint_restore(checkpoint)
            latencies.append(time.time() - start)

        avg_latency = sum(latencies) / len(latencies) * 1000

        assert avg_latency < 10  # Under 10ms average

    @pytest.mark.asyncio
    async def test_checkpoint_with_active_executions(self):
        """Test checkpoint with multiple active executions."""
        manager = migrate_nested_workflow_manager("ckpt-active-test")

        # Create multiple active contexts
        for i in range(10):
            ctx = NestedExecutionContextLegacy(
                execution_id=uuid4(),
                parent_execution_id=None,
                workflow_id=uuid4(),
                depth=0,
                path=[],
                variables={"i": i},
            )
            manager._active_executions[ctx.execution_id] = ctx

        latencies = []
        for _ in range(50):
            start = time.time()
            await manager.on_checkpoint_save()
            latencies.append(time.time() - start)

        avg_latency = sum(latencies) / len(latencies) * 1000

        # Should still be fast with active executions
        assert avg_latency < 20  # Under 20ms average


# =============================================================================
# Test Category 4: Memory Usage Patterns
# =============================================================================


class TestMemoryUsage:
    """Test memory usage patterns."""

    @pytest.mark.asyncio
    async def test_execution_cleanup(self):
        """Test that completed executions are cleaned up."""
        manager = migrate_nested_workflow_manager("cleanup-test")

        async def executor_fn(data, responses):
            return {"result": "done"}

        parent_id = uuid4()
        sub_ref = SubWorkflowReferenceLegacy(
            id=uuid4(),
            parent_workflow_id=parent_id,
            workflow_id=uuid4(),
            definition=None,
            config=NestedWorkflowConfigLegacy(),
        )

        await manager.register_sub_workflow(parent_id, sub_ref, executor_fn)

        # Execute many times
        for i in range(100):
            ctx = create_migration_context(workflow_id=parent_id)
            await manager.execute_sub_workflow(ctx, sub_ref)

        # Clear completed
        cleared = manager.clear_completed_executions(older_than_seconds=0)

        # Most should be cleared
        stats = manager.get_statistics()
        assert stats["total_active_executions"] < 10

    @pytest.mark.asyncio
    async def test_executor_reuse(self):
        """Test executor reuse doesn't accumulate memory."""
        async def process(data, responses):
            return {"result": data}

        workflow = SimpleWorkflow(id="reuse-wf", executor_fn=process)
        executor = create_workflow_executor(id="reuse-exec", workflow=workflow)
        executor.build()

        # Run many times
        for i in range(1000):
            await executor.run({"i": i})
            executor.clear_events()  # Clear event history

        # Check state is clean
        state = executor.get_state()
        assert state["active_executions"] == 0


# =============================================================================
# Test Category 5: Request/Response Coordination Overhead
# =============================================================================


class TestRequestResponseOverhead:
    """Test request/response coordination overhead."""

    @pytest.mark.asyncio
    async def test_single_request_response_cycle(self):
        """Test single request/response cycle latency."""
        from src.integrations.agent_framework.builders.workflow_executor import (
            RequestInfoEvent,
        )

        call_count = 0

        async def requesting_process(data, responses):
            nonlocal call_count
            call_count += 1

            if call_count == 1 and not responses:
                event = RequestInfoEvent(
                    request_id="req-1",
                    data="need info",
                    response_type=str,
                )
                return WorkflowRunResult(
                    request_info_events=[event],
                    final_state=WorkflowRunState.IN_PROGRESS_PENDING_REQUESTS,
                )
            return WorkflowRunResult(
                outputs=[WorkflowOutput(data={"done": True})],
                final_state=WorkflowRunState.COMPLETED,
            )

        workflow = SimpleWorkflow(id="req-wf", executor_fn=requesting_process)
        executor = create_workflow_executor(id="req-exec", workflow=workflow)
        executor.build()

        latencies = []
        for _ in range(50):
            call_count = 0
            start = time.time()

            # Initial run
            result = await executor.run({"input": "test"})

            if result.pending_requests:
                request = result.pending_requests[0]
                response = request.create_response("response")
                await executor.send_response(response)

            latencies.append(time.time() - start)

        avg_latency = sum(latencies) / len(latencies) * 1000

        # Request/response cycle should add minimal overhead
        assert avg_latency < 50  # Under 50ms average


# =============================================================================
# Performance Benchmarks
# =============================================================================


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""

    @pytest.mark.asyncio
    async def test_workflow_executor_benchmark(self):
        """Comprehensive workflow executor benchmark."""
        async def process(data, responses):
            return {"result": data.get("i", 0) * 2}

        workflow = SimpleWorkflow(id="bench-wf", executor_fn=process)
        executor = create_workflow_executor(id="bench-exec", workflow=workflow)
        executor.build()

        # Warm up
        for i in range(10):
            await executor.run({"i": i})

        # Benchmark
        latencies = []
        start_time = time.time()

        for i in range(1000):
            op_start = time.time()
            result = await executor.run({"i": i})
            latencies.append(time.time() - op_start)

            assert result.status == WorkflowExecutorStatus.COMPLETED

        total_duration = time.time() - start_time

        metrics = calculate_metrics("executor_benchmark", latencies, total_duration)

        # Performance assertions
        assert metrics.throughput_per_second > 100  # At least 100 ops/sec
        assert metrics.avg_latency_ms < 20  # Under 20ms average

    @pytest.mark.asyncio
    async def test_migration_layer_benchmark(self):
        """Benchmark migration layer overhead."""
        manager = migrate_nested_workflow_manager("bench-manager")

        async def executor_fn(data, responses):
            return {"result": "done"}

        parent_id = uuid4()
        sub_ref = SubWorkflowReferenceLegacy(
            id=uuid4(),
            parent_workflow_id=parent_id,
            workflow_id=uuid4(),
            definition=None,
            config=NestedWorkflowConfigLegacy(),
        )

        await manager.register_sub_workflow(parent_id, sub_ref, executor_fn)

        # Warm up
        for _ in range(10):
            ctx = create_migration_context(workflow_id=parent_id)
            await manager.execute_sub_workflow(ctx, sub_ref)

        # Benchmark
        latencies = []
        start_time = time.time()

        for i in range(500):
            ctx = create_migration_context(
                workflow_id=parent_id,
                variables={"i": i},
            )
            op_start = time.time()
            await manager.execute_sub_workflow(ctx, sub_ref)
            latencies.append(time.time() - op_start)

        total_duration = time.time() - start_time

        metrics = calculate_metrics("migration_benchmark", latencies, total_duration)

        # Migration layer should add minimal overhead
        assert metrics.throughput_per_second > 50  # At least 50 ops/sec
        assert metrics.avg_latency_ms < 30  # Under 30ms average


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
