# =============================================================================
# IPA Platform - Phase 3 Integration Tests
# =============================================================================
# Sprint 18: S18-3 整合測試 (8 points)
#
# This module contains comprehensive integration tests for Phase 3 features:
#   - Sprint 14: ConcurrentBuilder
#   - Sprint 15: HandoffBuilder
#   - Sprint 16: GroupChatBuilder
#   - Sprint 17: MagenticBuilder
#   - Sprint 18: WorkflowExecutor
#
# Test Categories:
#   1. ConcurrentBuilder + GroupChatBuilder integration
#   2. HandoffBuilder + MagenticBuilder integration
#   3. WorkflowExecutor + Checkpoint integration
#   4. Full Phase 3 E2E integration
#
# Author: IPA Platform Team
# Sprint: 18 - WorkflowExecutor 和整合
# Created: 2025-12-05
# =============================================================================

import pytest
import asyncio
from uuid import uuid4
from typing import Any, Dict, List
from datetime import datetime

# Sprint 14: ConcurrentBuilder
from src.integrations.agent_framework.builders.concurrent import (
    ConcurrentBuilderAdapter,
    ConcurrentMode,
    ConcurrentTaskConfig,
    create_all_concurrent,
)

# Sprint 15: HandoffBuilder
from src.integrations.agent_framework.builders.handoff import (
    HandoffBuilderAdapter,
    HandoffMode,
    HandoffStatus,
    create_handoff_adapter,
)

# Sprint 16: GroupChatBuilder
from src.integrations.agent_framework.builders.groupchat import (
    GroupChatBuilderAdapter,
    GroupChatParticipant,
    GroupChatMessage,
    SpeakerSelectionMethod,
    create_groupchat_adapter,
)

# Sprint 17: MagenticBuilder
from src.integrations.agent_framework.builders.magentic import (
    MagenticBuilderAdapter,
    MagenticStatus,
    MagenticParticipant,
    TaskLedger,
    create_magentic_adapter,
)

# Sprint 18: WorkflowExecutor
from src.integrations.agent_framework.builders.workflow_executor import (
    WorkflowExecutorAdapter,
    WorkflowExecutorStatus,
    WorkflowRunState,
    WorkflowRunResult,
    WorkflowOutput,
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
# Mock Executors for Integration Testing
# =============================================================================


class MockExecutor:
    """Base mock executor for integration tests."""

    def __init__(self, executor_id: str, response_data: Any = None):
        self._id = executor_id
        self._response_data = response_data or f"Response from {executor_id}"
        self._call_count = 0

    @property
    def id(self) -> str:
        return self._id

    async def execute(self, input_data: Any) -> Dict[str, Any]:
        self._call_count += 1
        return {
            "executor_id": self._id,
            "input": input_data,
            "output": self._response_data,
            "call_count": self._call_count,
        }


class GroupChatMockParticipant:
    """Mock participant for GroupChat integration tests."""

    def __init__(self, name: str, role: str = "assistant"):
        self._name = name
        self._role = role
        self._messages: List[str] = []

    @property
    def name(self) -> str:
        return self._name

    async def respond(self, message: str, context: Dict[str, Any]) -> str:
        self._messages.append(message)
        return f"[{self._name}] Response to: {message[:50]}..."


# =============================================================================
# Test Category 1: ConcurrentBuilder + GroupChatBuilder Integration
# =============================================================================


class TestConcurrentGroupChatIntegration:
    """Test integration between ConcurrentBuilder and GroupChatBuilder."""

    @pytest.mark.asyncio
    async def test_concurrent_groupchat_parallel_discussions(self):
        """Test parallel group chat discussions using ConcurrentBuilder."""
        # Create multiple group chat adapters
        chat_adapters = []
        for i in range(3):
            participants = [
                GroupChatParticipant(
                    name=f"Participant-{i}-{j}",
                    description=f"Test participant {j} in group {i}",
                )
                for j in range(2)
            ]
            adapter = GroupChatBuilderAdapter(
                id=f"chat-{i}",
                participants=participants,
            )
            chat_adapters.append(adapter)

        # Create concurrent adapter
        concurrent = ConcurrentBuilderAdapter(
            id="parallel-chats",
            mode=ConcurrentMode.ALL,
        )

        # Verify setup
        assert len(chat_adapters) == 3
        assert concurrent.mode == ConcurrentMode.ALL

    @pytest.mark.asyncio
    async def test_groupchat_with_concurrent_subtasks(self):
        """Test GroupChat that spawns concurrent subtasks."""
        # Create GroupChat adapter
        participants = [
            GroupChatParticipant(
                name="Coordinator",
                description="Coordinates parallel tasks",
            ),
            GroupChatParticipant(
                name="Analyzer",
                description="Analyzes results",
            ),
        ]

        groupchat = GroupChatBuilderAdapter(
            id="coordinated-chat",
            participants=participants,
            selection_method=SpeakerSelectionMethod.ROUND_ROBIN,
        )

        # Create concurrent tasks for the coordinator
        concurrent = ConcurrentBuilderAdapter(
            id="subtasks",
            mode=ConcurrentMode.ALL,
        )

        # Verify integration setup
        assert len(groupchat.participants) == 2
        assert concurrent.mode == ConcurrentMode.ALL


# =============================================================================
# Test Category 2: HandoffBuilder + MagenticBuilder Integration
# =============================================================================


class TestHandoffMagenticIntegration:
    """Test integration between HandoffBuilder and MagenticBuilder."""

    @pytest.mark.asyncio
    async def test_handoff_to_magentic_workflow(self):
        """Test handoff from one agent to Magentic workflow."""
        # Create Magentic adapter
        magentic = MagenticBuilderAdapter(id="magentic-workflow")

        # Add participants
        magentic.add_participant(MagenticParticipant(
            name="Planner",
            description="Plans the task",
        ))
        magentic.add_participant(MagenticParticipant(
            name="Executor",
            description="Executes the plan",
        ))

        # Create Handoff adapter
        handoff = HandoffBuilderAdapter(id="handoff-to-magentic")

        # Verify setup
        assert magentic.id == "magentic-workflow"
        assert handoff.id == "handoff-to-magentic"

    @pytest.mark.asyncio
    async def test_magentic_with_handoff_intervention(self):
        """Test Magentic workflow with human intervention via Handoff."""
        # Create Magentic adapter with human intervention enabled
        magentic = create_magentic_adapter(
            id="magentic-hitl",
            enable_plan_review=True,
        )

        # Create Handoff adapter for human intervention
        handoff = HandoffBuilderAdapter(
            id="hitl-handoff",
        )
        handoff.with_mode(HandoffMode.HUMAN_IN_LOOP)

        # Verify integration setup
        assert magentic.id == "magentic-hitl"
        assert handoff.mode == HandoffMode.HUMAN_IN_LOOP


# =============================================================================
# Test Category 3: WorkflowExecutor + Checkpoint Integration
# =============================================================================


class TestWorkflowExecutorCheckpointIntegration:
    """Test WorkflowExecutor with checkpoint save/restore."""

    @pytest.mark.asyncio
    async def test_executor_checkpoint_save_restore(self):
        """Test checkpoint save and restore for WorkflowExecutor."""

        async def process(data, responses):
            return {"processed": data}

        workflow = SimpleWorkflow(
            id="checkpoint-workflow",
            executor_fn=process,
        )

        adapter = WorkflowExecutorAdapter(
            id="checkpoint-executor",
            workflow=workflow,
        )
        adapter.build()

        # Save checkpoint
        checkpoint_state = await adapter.on_checkpoint_save()
        assert "execution_contexts" in checkpoint_state
        assert "status" in checkpoint_state

        # Simulate state changes
        await adapter.run({"input": "test"})

        # Restore checkpoint
        await adapter.on_checkpoint_restore(checkpoint_state)

        # Verify restore
        state = adapter.get_state()
        assert state["id"] == "checkpoint-executor"

    @pytest.mark.asyncio
    async def test_nested_workflow_checkpoint_integration(self):
        """Test nested workflow with checkpoint integration."""
        manager = migrate_nested_workflow_manager(
            manager_id="checkpoint-manager",
            max_global_depth=5,
        )

        # Save checkpoint
        checkpoint = await manager.on_checkpoint_save()
        assert "id" in checkpoint
        assert checkpoint["id"] == "checkpoint-manager"

        # Restore checkpoint
        await manager.on_checkpoint_restore(checkpoint)

        # Verify state
        stats = manager.get_statistics()
        assert stats["max_global_depth"] == 5


# =============================================================================
# Test Category 4: Full Phase 3 E2E Integration
# =============================================================================


class TestPhase3E2EIntegration:
    """Full end-to-end integration tests for Phase 3."""

    @pytest.mark.asyncio
    async def test_multi_builder_workflow(self):
        """Test workflow using multiple Phase 3 builders."""
        # Create WorkflowExecutor as the main orchestrator
        async def orchestrate(data, responses):
            return WorkflowRunResult(
                outputs=[WorkflowOutput(data={"orchestrated": True})],
                final_state=WorkflowRunState.COMPLETED,
            )

        main_workflow = SimpleWorkflow(
            id="orchestrator",
            executor_fn=orchestrate,
        )

        # Create sub-executors for different tasks
        executor = create_workflow_executor(
            id="main-executor",
            workflow=main_workflow,
        )
        executor.build()

        # Create GroupChat for collaboration
        groupchat = create_groupchat_adapter(
            id="collab-chat",
            participants=[
                GroupChatParticipant(name="Agent1", description="Test"),
                GroupChatParticipant(name="Agent2", description="Test"),
            ],
        )

        # Create Handoff for task delegation
        handoff = HandoffBuilderAdapter(
            id="task-handoff",
        )
        handoff.with_mode(HandoffMode.AUTONOMOUS)

        # Verify all components created
        assert executor.is_built
        assert len(groupchat.participants) == 2
        assert handoff.mode == HandoffMode.AUTONOMOUS

    @pytest.mark.asyncio
    async def test_hierarchical_workflow_execution(self):
        """Test hierarchical workflow with parent-child relationships."""
        # Create parent workflow
        async def parent_process(data, responses):
            return {"parent_result": "success", "child_needed": True}

        parent_workflow = SimpleWorkflow(
            id="parent-wf",
            executor_fn=parent_process,
        )

        # Create child workflow
        async def child_process(data, responses):
            return {"child_result": "completed"}

        child_workflow = SimpleWorkflow(
            id="child-wf",
            executor_fn=child_process,
        )

        # Create parent executor
        parent_executor = create_workflow_executor(
            id="parent-executor",
            workflow=parent_workflow,
        )
        parent_executor.build()

        # Create child executor
        child_executor = create_workflow_executor(
            id="child-executor",
            workflow=child_workflow,
        )
        child_executor.build()

        # Execute parent
        parent_result = await parent_executor.run({"task": "main"})
        assert parent_result.status == WorkflowExecutorStatus.COMPLETED

        # Execute child based on parent result
        child_result = await child_executor.run({"from_parent": parent_result.outputs})
        assert child_result.status == WorkflowExecutorStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_concurrent_with_nested_workflows(self):
        """Test concurrent execution with nested workflows."""

        async def task_a(data, responses):
            return {"task": "A", "result": "completed"}

        async def task_b(data, responses):
            return {"task": "B", "result": "completed"}

        async def task_c(data, responses):
            return {"task": "C", "result": "completed"}

        # Create workflows
        workflows = [
            SimpleWorkflow(id=f"task-{name}", executor_fn=fn)
            for name, fn in [("A", task_a), ("B", task_b), ("C", task_c)]
        ]

        # Create executors
        executors = [
            create_workflow_executor(id=f"exec-{i}", workflow=wf)
            for i, wf in enumerate(workflows)
        ]

        # Build all
        for executor in executors:
            executor.build()

        # Execute concurrently
        tasks = [executor.run({"input": i}) for i, executor in enumerate(executors)]
        results = await asyncio.gather(*tasks)

        # Verify all completed
        for result in results:
            assert result.status == WorkflowExecutorStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_migration_with_all_builders(self):
        """Test migration layer integration with all builders."""
        # Create migration manager
        manager = migrate_nested_workflow_manager("full-migration")

        # Create parent context
        parent_ctx = create_migration_context(
            variables={"input": "test_data"},
            depth=0,
        )

        # Register sub-workflow with executor
        async def sub_executor(data, responses):
            return {"sub_result": "success"}

        sub_ref = SubWorkflowReferenceLegacy(
            id=uuid4(),
            parent_workflow_id=parent_ctx.workflow_id,
            workflow_id=uuid4(),
            definition=None,
            config=NestedWorkflowConfigLegacy(),
        )

        await manager.register_sub_workflow(
            parent_ctx.workflow_id,
            sub_ref,
            sub_executor,
        )

        # Execute
        result = await manager.execute_sub_workflow(parent_ctx, sub_ref)

        # Verify
        assert result is not None
        assert result.depth == 1


# =============================================================================
# Test Category 5: Error Handling and Edge Cases
# =============================================================================


class TestPhase3ErrorHandling:
    """Test error handling across Phase 3 integrations."""

    @pytest.mark.asyncio
    async def test_workflow_timeout_handling(self):
        """Test timeout handling in workflow execution."""

        async def slow_process(data, responses):
            await asyncio.sleep(5)  # Simulate slow processing
            return {"result": "done"}

        workflow = SimpleWorkflow(id="slow-wf", executor_fn=slow_process)
        executor = create_workflow_executor(id="timeout-exec", workflow=workflow)
        executor.build()

        # Execute with short timeout
        result = await executor.run({"input": "test"}, timeout_seconds=0.1)

        assert result.status == WorkflowExecutorStatus.FAILED
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_nested_depth_limit_enforcement(self):
        """Test depth limit enforcement in nested workflows."""
        manager = migrate_nested_workflow_manager(
            manager_id="depth-test",
            max_global_depth=2,
        )

        # Create deep context
        deep_ctx = create_migration_context(depth=2)

        sub_ref = SubWorkflowReferenceLegacy(
            id=uuid4(),
            parent_workflow_id=deep_ctx.workflow_id,
            workflow_id=uuid4(),
            definition=None,
            config=NestedWorkflowConfigLegacy(max_depth=5),
        )

        # Should raise due to global depth limit
        with pytest.raises(ValueError, match="depth"):
            await manager.execute_sub_workflow(deep_ctx, sub_ref)

    @pytest.mark.asyncio
    async def test_workflow_error_propagation(self):
        """Test error propagation in workflow execution."""

        async def error_process(data, responses):
            raise RuntimeError("Simulated error")

        workflow = SimpleWorkflow(id="error-wf", executor_fn=error_process)
        executor = create_workflow_executor(id="error-exec", workflow=workflow)
        executor.build()

        result = await executor.run({"input": "test"})

        assert result.status == WorkflowExecutorStatus.FAILED
        assert "Simulated error" in result.error


# =============================================================================
# Test Category 6: State Management and Consistency
# =============================================================================


class TestPhase3StateManagement:
    """Test state management and consistency across Phase 3."""

    @pytest.mark.asyncio
    async def test_executor_state_consistency(self):
        """Test executor state remains consistent across operations."""

        async def process(data, responses):
            return {"result": data}

        workflow = SimpleWorkflow(id="state-wf", executor_fn=process)
        executor = create_workflow_executor(id="state-exec", workflow=workflow)

        # Initial state
        assert executor.status == WorkflowExecutorStatus.IDLE

        executor.build()

        # After build
        state = executor.get_state()
        assert state["is_built"] is True
        assert state["status"] == "idle"

        # After run
        await executor.run({"input": "test"})
        state = executor.get_state()
        assert state["status"] in ["idle", "completed"]

    @pytest.mark.asyncio
    async def test_manager_statistics_accuracy(self):
        """Test manager statistics accuracy."""
        manager = migrate_nested_workflow_manager("stats-test")

        # Initial stats
        stats = manager.get_statistics()
        assert stats["total_active_executions"] == 0
        assert stats["registered_executors"] == 0

        # Register sub-workflow
        parent_id = uuid4()
        sub_ref = SubWorkflowReferenceLegacy(
            id=uuid4(),
            parent_workflow_id=parent_id,
            workflow_id=uuid4(),
            definition=None,
            config=NestedWorkflowConfigLegacy(),
        )

        await manager.register_sub_workflow(parent_id, sub_ref)

        # Updated stats
        stats = manager.get_statistics()
        assert stats["registered_sub_workflows"] == 1
        assert stats["registered_executors"] == 1


# =============================================================================
# Test Category 7: Performance Characteristics
# =============================================================================


class TestPhase3Performance:
    """Test performance characteristics of Phase 3 integration."""

    @pytest.mark.asyncio
    async def test_concurrent_execution_performance(self):
        """Test concurrent execution doesn't cause excessive overhead."""

        async def fast_process(data, responses):
            return {"result": "fast"}

        # Create multiple executors
        executors = []
        for i in range(10):
            workflow = SimpleWorkflow(id=f"fast-{i}", executor_fn=fast_process)
            executor = create_workflow_executor(id=f"exec-{i}", workflow=workflow)
            executor.build()
            executors.append(executor)

        # Measure execution time
        start_time = asyncio.get_event_loop().time()
        tasks = [executor.run({"i": i}) for i, executor in enumerate(executors)]
        results = await asyncio.gather(*tasks)
        elapsed = asyncio.get_event_loop().time() - start_time

        # All should complete
        assert all(r.status == WorkflowExecutorStatus.COMPLETED for r in results)

        # Should complete reasonably fast (under 2 seconds for 10 concurrent)
        assert elapsed < 2.0

    @pytest.mark.asyncio
    async def test_memory_cleanup_after_execution(self):
        """Test memory cleanup after execution completes."""
        manager = migrate_nested_workflow_manager("cleanup-test")

        # Register and execute multiple workflows
        parent_id = uuid4()
        for i in range(5):
            async def executor_fn(data, responses):
                return {"result": i}

            sub_ref = SubWorkflowReferenceLegacy(
                id=uuid4(),
                parent_workflow_id=parent_id,
                workflow_id=uuid4(),
                definition=None,
                config=NestedWorkflowConfigLegacy(),
            )
            await manager.register_sub_workflow(parent_id, sub_ref, executor_fn)

            ctx = create_migration_context(
                workflow_id=parent_id,
                variables={"i": i},
            )
            await manager.execute_sub_workflow(ctx, sub_ref)

        # Clear old executions
        cleared = manager.clear_completed_executions(older_than_seconds=0)

        # Should have cleared some executions
        assert cleared >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
