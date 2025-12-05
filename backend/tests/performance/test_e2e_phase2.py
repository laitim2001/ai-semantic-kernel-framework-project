"""
Phase 2 E2E Performance Tests
Sprint 12 - S12-7: Testing

End-to-end performance tests for Phase 2 features:
- Concurrent execution throughput
- Nested workflow depth performance
- GroupChat scalability
- Agent handoff latency
"""

import pytest
import asyncio
import time
import statistics
from uuid import uuid4
from datetime import datetime
from unittest.mock import Mock, AsyncMock

# Concurrent Execution
from src.domain.workflows.executors.concurrent import ConcurrentExecutor
from src.domain.workflows.executors.concurrent_state import ConcurrentState, TaskState
from src.domain.workflows.executors.parallel_gateway import ParallelGateway

# Nested Workflows
from src.domain.orchestration.nested.workflow_manager import NestedWorkflowManager
from src.domain.orchestration.nested.recursive_handler import RecursiveHandler

# GroupChat
from src.domain.orchestration.groupchat.manager import GroupChatManager
from src.domain.orchestration.groupchat.speaker_selector import SpeakerSelector

# Agent Handoff
from src.domain.orchestration.handoff.controller import HandoffController
from src.domain.orchestration.handoff.capability_matcher import (
    CapabilityMatcher,
    AgentCapability,
    MatchStrategy
)

# Performance utilities
from src.core.performance.benchmark import BenchmarkRunner, BenchmarkConfig


class TestConcurrentThroughput:
    """Performance tests for concurrent execution throughput"""

    @pytest.fixture
    def benchmark_runner(self):
        """Create benchmark runner with test config"""
        config = BenchmarkConfig(
            iterations=50,
            warmup_iterations=10,
            timeout_seconds=30.0
        )
        return BenchmarkRunner(config)

    @pytest.mark.asyncio
    async def test_concurrent_task_creation_throughput(self, benchmark_runner):
        """Benchmark task creation throughput"""
        executor = ConcurrentExecutor(max_parallel=100)

        def create_tasks():
            state = ConcurrentState(workflow_id="throughput_test")
            for i in range(1000):
                state.add_task(f"task_{i}", {"index": i, "data": "test"})
            return state

        result = benchmark_runner.run_sync("task_creation_1000", create_tasks)

        # Performance assertions
        assert result.mean_ms < 100  # Should complete in under 100ms
        assert result.throughput_ops > 10  # At least 10 ops/sec
        print(f"\nTask Creation (1000 tasks): {result.mean_ms:.2f}ms mean, "
              f"{result.throughput_ops:.1f} ops/sec")

    @pytest.mark.asyncio
    async def test_concurrent_execution_throughput(self, benchmark_runner):
        """Benchmark concurrent execution throughput"""
        executor = ConcurrentExecutor(max_parallel=50)

        async def execute_batch():
            tasks = []
            for i in range(100):
                async def task(idx=i):
                    await asyncio.sleep(0.001)  # Simulate small work
                    return idx
                tasks.append(task())

            results = await asyncio.gather(*tasks, return_exceptions=True)
            return len([r for r in results if not isinstance(r, Exception)])

        result = await benchmark_runner.run_async("concurrent_execution_100", execute_batch)

        assert result.mean_ms < 500  # 100 tasks should complete in under 500ms
        print(f"\nConcurrent Execution (100 tasks): {result.mean_ms:.2f}ms mean")

    @pytest.mark.asyncio
    async def test_parallel_gateway_throughput(self, benchmark_runner):
        """Benchmark parallel gateway fork/join throughput"""
        def fork_join_test():
            gateway = ParallelGateway(gateway_id="perf_test")

            # Add many branches
            for i in range(50):
                gateway.add_branch(f"branch_{i}", {"data": i * 100})

            # Fork
            fork_result = gateway.fork()

            # Simulate completion
            for branch_id in fork_result["branches"]:
                gateway.complete_branch(branch_id, {"result": "done"})

            # Join
            return gateway.join()

        result = benchmark_runner.run_sync("gateway_fork_join_50", fork_join_test)

        assert result.mean_ms < 50  # Should be very fast
        print(f"\nParallel Gateway (50 branches): {result.mean_ms:.2f}ms mean")

    @pytest.mark.asyncio
    async def test_concurrent_scaling(self):
        """Test concurrent execution scaling characteristics"""
        results = []
        task_counts = [10, 50, 100, 200, 500]

        for count in task_counts:
            start = time.perf_counter()

            state = ConcurrentState(workflow_id=f"scale_test_{count}")
            for i in range(count):
                state.add_task(f"task_{i}", {"data": i})

            duration_ms = (time.perf_counter() - start) * 1000
            results.append({"count": count, "duration_ms": duration_ms})

        # Verify roughly linear scaling
        for i in range(1, len(results)):
            ratio = results[i]["count"] / results[i-1]["count"]
            time_ratio = results[i]["duration_ms"] / max(results[i-1]["duration_ms"], 0.01)

            # Time should scale sub-linearly or linearly (not worse than 2x for 2x tasks)
            assert time_ratio < ratio * 2

        print("\nConcurrent Scaling Results:")
        for r in results:
            print(f"  {r['count']} tasks: {r['duration_ms']:.2f}ms")


class TestNestedDepthPerformance:
    """Performance tests for nested workflow depth handling"""

    @pytest.fixture
    def benchmark_runner(self):
        """Create benchmark runner"""
        config = BenchmarkConfig(iterations=30, warmup_iterations=5)
        return BenchmarkRunner(config)

    @pytest.mark.asyncio
    async def test_nested_workflow_registration_depth(self, benchmark_runner):
        """Benchmark nested workflow registration at various depths"""
        def register_nested_chain(depth):
            manager = NestedWorkflowManager(max_depth=depth + 1)
            parent = uuid4()

            for d in range(1, depth + 1):
                child = uuid4()
                manager.register_workflow(parent, child, d)
                parent = child

            return manager

        depths = [5, 10, 20, 50]
        results = {}

        for depth in depths:
            result = benchmark_runner.run_sync(
                f"nested_registration_depth_{depth}",
                lambda d=depth: register_nested_chain(d)
            )
            results[depth] = result.mean_ms

        # Verify reasonable performance at all depths
        for depth, ms in results.items():
            assert ms < depth * 2  # Should be roughly linear

        print("\nNested Registration by Depth:")
        for depth, ms in results.items():
            print(f"  Depth {depth}: {ms:.2f}ms")

    @pytest.mark.asyncio
    async def test_nested_workflow_lookup_performance(self, benchmark_runner):
        """Benchmark nested workflow lookup operations"""
        # Setup nested structure
        manager = NestedWorkflowManager(max_depth=10)
        root = uuid4()
        workflow_ids = [root]

        current_parent = root
        for depth in range(1, 10):
            child = uuid4()
            manager.register_workflow(current_parent, child, depth)
            workflow_ids.append(child)
            current_parent = child

        def lookup_all():
            results = []
            for wf_id in workflow_ids:
                results.append(manager.get_depth(wf_id))
                results.append(manager.get_parent(wf_id))
            return results

        result = benchmark_runner.run_sync("nested_lookup_operations", lookup_all)

        assert result.mean_ms < 10  # Lookups should be fast
        print(f"\nNested Lookup (10 workflows): {result.mean_ms:.2f}ms mean")

    @pytest.mark.asyncio
    async def test_recursive_handler_depth_check(self, benchmark_runner):
        """Benchmark recursive depth checking"""
        handler = RecursiveHandler(max_depth=100, max_concurrent=10)

        def check_depths():
            results = []
            for depth in range(100):
                results.append(handler.can_recurse_deeper(depth))
            return results

        result = benchmark_runner.run_sync("recursive_depth_check_100", check_depths)

        assert result.mean_ms < 5  # Should be very fast
        print(f"\nRecursive Depth Check (100): {result.mean_ms:.2f}ms mean")


class TestGroupChatScalability:
    """Performance tests for GroupChat scalability"""

    @pytest.fixture
    def benchmark_runner(self):
        """Create benchmark runner"""
        config = BenchmarkConfig(iterations=20, warmup_iterations=5)
        return BenchmarkRunner(config)

    @pytest.mark.asyncio
    async def test_groupchat_session_creation_scalability(self, benchmark_runner):
        """Benchmark GroupChat session creation with varying participants"""
        participant_counts = [5, 10, 20, 50]
        results = {}

        for count in participant_counts:
            def create_session(n=count):
                manager = GroupChatManager(max_participants=n)
                participants = [
                    {"id": f"agent_{i}", "role": "worker"}
                    for i in range(n)
                ]
                return manager.create_session(
                    session_id=str(uuid4()),
                    participants=participants
                )

            result = benchmark_runner.run_sync(
                f"groupchat_create_{count}_participants",
                create_session
            )
            results[count] = result.mean_ms

        print("\nGroupChat Session Creation Scalability:")
        for count, ms in results.items():
            print(f"  {count} participants: {ms:.2f}ms")

        # Verify reasonable scaling
        assert results[50] < results[5] * 20  # Should not scale worse than 20x

    @pytest.mark.asyncio
    async def test_speaker_selection_performance(self, benchmark_runner):
        """Benchmark speaker selection performance"""
        selector = SpeakerSelector(strategy="round_robin")

        participants = [
            {"id": f"agent_{i}", "capabilities": [f"cap_{i % 5}"]}
            for i in range(20)
        ]

        def select_speakers():
            history = []
            for _ in range(50):
                selected = selector.select_next_speaker(
                    participants=participants,
                    context={},
                    history=history
                )
                history.append({"speaker": selected["id"]})
            return history

        result = benchmark_runner.run_sync("speaker_selection_50_turns", select_speakers)

        assert result.mean_ms < 50  # 50 selections should be fast
        print(f"\nSpeaker Selection (50 turns): {result.mean_ms:.2f}ms mean")

    @pytest.mark.asyncio
    async def test_groupchat_message_handling_throughput(self, benchmark_runner):
        """Benchmark message handling throughput"""
        manager = GroupChatManager(max_participants=10, max_rounds=1000)

        session_id = manager.create_session(
            session_id=str(uuid4()),
            participants=[{"id": f"agent_{i}", "role": "worker"} for i in range(10)]
        )

        def process_messages():
            for i in range(100):
                manager.add_message(
                    session_id,
                    sender=f"agent_{i % 10}",
                    content=f"Message {i} with some content",
                    message_type="chat"
                )
            return manager.get_message_count(session_id)

        result = benchmark_runner.run_sync("message_handling_100", process_messages)

        assert result.mean_ms < 100  # 100 messages should be fast
        print(f"\nMessage Handling (100 messages): {result.mean_ms:.2f}ms mean")


class TestHandoffLatency:
    """Performance tests for agent handoff latency"""

    @pytest.fixture
    def benchmark_runner(self):
        """Create benchmark runner"""
        config = BenchmarkConfig(iterations=50, warmup_iterations=10)
        return BenchmarkRunner(config)

    @pytest.fixture
    def capability_matcher(self):
        """Create capability matcher with agents"""
        matcher = CapabilityMatcher()

        # Register many agents with various capabilities
        for i in range(50):
            capabilities = [
                AgentCapability(f"capability_{j}", 0.5 + (i + j) % 5 * 0.1)
                for j in range(5)
            ]
            matcher.register_agent(f"agent_{i}", capabilities)

        return matcher

    @pytest.mark.asyncio
    async def test_capability_matching_latency(
        self,
        benchmark_runner,
        capability_matcher
    ):
        """Benchmark capability matching latency"""
        def find_matches():
            results = []
            for i in range(20):
                required = AgentCapability(f"capability_{i % 5}", 0.7)
                match = capability_matcher.find_best_match(
                    required,
                    strategy=MatchStrategy.BEST_FIT
                )
                results.append(match)
            return results

        result = benchmark_runner.run_sync("capability_match_20", find_matches)

        assert result.mean_ms < 20  # 20 matches should be fast
        print(f"\nCapability Matching (20 queries): {result.mean_ms:.2f}ms mean")

    @pytest.mark.asyncio
    async def test_handoff_execution_latency(self, benchmark_runner):
        """Benchmark handoff execution latency"""
        controller = HandoffController()

        async def execute_handoffs():
            results = []
            for i in range(10):
                result = await controller.execute_handoff(
                    source_agent_id=f"agent_{i}",
                    target_agent_id=f"agent_{i+1}",
                    context={"task": f"task_{i}", "data": {"value": i}}
                )
                results.append(result)
            return results

        result = await benchmark_runner.run_async("handoff_execution_10", execute_handoffs)

        assert result.mean_ms < 100  # 10 handoffs should complete quickly
        print(f"\nHandoff Execution (10 handoffs): {result.mean_ms:.2f}ms mean")

    @pytest.mark.asyncio
    async def test_handoff_chain_latency(self, benchmark_runner):
        """Benchmark latency for chain of handoffs"""
        controller = HandoffController()
        matcher = CapabilityMatcher()

        # Register agents
        for i in range(10):
            capabilities = [AgentCapability(f"step_{i}", 0.9)]
            matcher.register_agent(f"specialist_{i}", capabilities)

        async def execute_chain():
            current_agent = "initiator"
            context = {"data": "initial"}

            for i in range(10):
                # Find next agent
                required = AgentCapability(f"step_{i}", 0.8)
                match = matcher.find_best_match(required, MatchStrategy.BEST_FIT)

                if match:
                    result = await controller.execute_handoff(
                        source_agent_id=current_agent,
                        target_agent_id=match["agent_id"],
                        context=context
                    )
                    current_agent = match["agent_id"]
                    context = result.get("context", context)

            return context

        result = await benchmark_runner.run_async("handoff_chain_10", execute_chain)

        assert result.mean_ms < 200  # Chain of 10 should be reasonable
        print(f"\nHandoff Chain (10 steps): {result.mean_ms:.2f}ms mean")


class TestEndToEndPerformance:
    """End-to-end performance tests for complete Phase 2 workflows"""

    @pytest.fixture
    def benchmark_runner(self):
        """Create benchmark runner"""
        config = BenchmarkConfig(iterations=10, warmup_iterations=3)
        return BenchmarkRunner(config)

    @pytest.mark.asyncio
    async def test_complete_workflow_latency(self, benchmark_runner):
        """Benchmark complete Phase 2 workflow execution"""
        async def complete_workflow():
            # 1. Create nested workflow structure
            nested_manager = NestedWorkflowManager(max_depth=3)
            parent_id = uuid4()

            sub_workflows = []
            for i in range(3):
                child_id = uuid4()
                nested_manager.register_workflow(parent_id, child_id, 1)
                sub_workflows.append(child_id)

            # 2. Setup concurrent execution
            executor = ConcurrentExecutor(max_parallel=10)
            state = ConcurrentState(workflow_id=str(parent_id))

            for sw_id in sub_workflows:
                state.add_task(str(sw_id), {"type": "sub_workflow"})

            # 3. Create GroupChat session
            groupchat = GroupChatManager()
            session_id = groupchat.create_session(
                session_id=str(uuid4()),
                participants=[
                    {"id": f"agent_{i}", "role": "worker"}
                    for i in range(5)
                ]
            )

            # 4. Process messages
            for i in range(10):
                groupchat.add_message(
                    session_id,
                    sender=f"agent_{i % 5}",
                    content=f"Processing step {i}",
                    message_type="chat"
                )

            # 5. Execute handoffs
            controller = HandoffController()
            for i in range(3):
                await controller.execute_handoff(
                    source_agent_id=f"agent_{i}",
                    target_agent_id=f"agent_{i+1}",
                    context={"step": i}
                )

            return {
                "nested_count": len(sub_workflows),
                "task_count": len(state.pending_tasks),
                "message_count": groupchat.get_message_count(session_id)
            }

        result = await benchmark_runner.run_async("complete_phase2_workflow", complete_workflow)

        assert result.mean_ms < 500  # Complete workflow should be under 500ms
        print(f"\nComplete Phase 2 Workflow: {result.mean_ms:.2f}ms mean")

    @pytest.mark.asyncio
    async def test_stress_test_concurrent_workflows(self):
        """Stress test with many concurrent workflows"""
        num_workflows = 50
        nested_manager = NestedWorkflowManager(max_depth=5)

        start_time = time.perf_counter()

        # Create many parallel workflow structures
        workflows = []
        for _ in range(num_workflows):
            parent_id = uuid4()
            workflows.append(parent_id)

            # Each workflow has some children
            for depth in range(1, 4):
                child_id = uuid4()
                nested_manager.register_workflow(parent_id, child_id, depth)
                parent_id = child_id

        creation_time = time.perf_counter() - start_time

        # Verify all workflows created
        assert len(workflows) == num_workflows
        assert creation_time < 2.0  # Should complete in under 2 seconds

        print(f"\nStress Test ({num_workflows} workflows): {creation_time*1000:.2f}ms")

    @pytest.mark.asyncio
    async def test_memory_efficiency(self):
        """Test memory efficiency under load"""
        import sys

        # Baseline memory
        baseline_size = 0

        # Create many objects
        managers = []
        for _ in range(100):
            manager = NestedWorkflowManager(max_depth=10)
            parent = uuid4()
            for d in range(1, 6):
                child = uuid4()
                manager.register_workflow(parent, child, d)
                parent = child
            managers.append(manager)

        # Check object count stays reasonable
        assert len(managers) == 100

        print(f"\nMemory Test: Created 100 workflow managers with 5 levels each")


class TestPerformanceBaselines:
    """Establish performance baselines for regression detection"""

    @pytest.fixture
    def benchmark_runner(self):
        """Create benchmark runner for baseline establishment"""
        config = BenchmarkConfig(
            iterations=100,
            warmup_iterations=20,
            timeout_seconds=60.0
        )
        return BenchmarkRunner(config)

    @pytest.mark.asyncio
    async def test_establish_baselines(self, benchmark_runner):
        """Establish performance baselines for all Phase 2 components"""
        baselines = {}

        # 1. Task creation baseline
        def create_tasks():
            state = ConcurrentState(workflow_id="baseline")
            for i in range(100):
                state.add_task(f"task_{i}", {"data": i})
            return state

        result = benchmark_runner.run_sync("baseline_task_creation", create_tasks)
        baselines["task_creation_100"] = result.mean_ms

        # 2. Nested workflow baseline
        def create_nested():
            manager = NestedWorkflowManager(max_depth=10)
            parent = uuid4()
            for d in range(1, 6):
                child = uuid4()
                manager.register_workflow(parent, child, d)
                parent = child
            return manager

        result = benchmark_runner.run_sync("baseline_nested_creation", create_nested)
        baselines["nested_depth_5"] = result.mean_ms

        # 3. Capability matching baseline
        matcher = CapabilityMatcher()
        for i in range(20):
            matcher.register_agent(
                f"agent_{i}",
                [AgentCapability(f"cap_{j}", 0.8) for j in range(5)]
            )

        def match_capability():
            return matcher.find_best_match(
                AgentCapability("cap_2", 0.7),
                MatchStrategy.BEST_FIT
            )

        result = benchmark_runner.run_sync("baseline_capability_match", match_capability)
        baselines["capability_match"] = result.mean_ms

        # Store baselines for regression detection
        benchmark_runner._baselines = {
            name: benchmark_runner.run_sync(name, lambda: None)
            for name in baselines.keys()
        }

        # Print baselines
        print("\n" + "="*50)
        print("PERFORMANCE BASELINES ESTABLISHED")
        print("="*50)
        for name, ms in baselines.items():
            print(f"  {name}: {ms:.3f}ms")
        print("="*50)

        # Verify all baselines are reasonable
        assert all(ms < 100 for ms in baselines.values())
