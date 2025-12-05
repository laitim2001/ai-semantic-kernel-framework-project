"""
Phase 2 Integration Tests
Sprint 12 - S12-7: Testing

Integration tests for Phase 2 feature combinations:
- Concurrent execution with nested workflows
- GroupChat with dynamic planning
- Agent handoff with capability matching
- Full Phase 2 workflow integration
"""

import pytest
import asyncio
from uuid import uuid4
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

# Concurrent Execution
from src.domain.workflows.executors.concurrent import ConcurrentExecutor
from src.domain.workflows.executors.concurrent_state import ConcurrentState, TaskState
from src.domain.workflows.executors.parallel_gateway import ParallelGateway

# Agent Handoff
from src.domain.orchestration.handoff.controller import HandoffController
from src.domain.orchestration.handoff.triggers import (
    HandoffTrigger,
    TriggerType,
    TriggerConfig
)
from src.domain.orchestration.handoff.capability_matcher import (
    CapabilityMatcher,
    AgentCapability,
    MatchStrategy
)

# GroupChat
from src.domain.orchestration.groupchat.manager import GroupChatManager
from src.domain.orchestration.groupchat.speaker_selector import SpeakerSelector
from src.domain.orchestration.groupchat.termination import TerminationStrategy

# MultiTurn
from src.domain.orchestration.multiturn.session_manager import MultiTurnSessionManager
from src.domain.orchestration.multiturn.turn_tracker import TurnTracker

# Dynamic Planning
from src.domain.orchestration.planning.dynamic_planner import DynamicPlanner
from src.domain.orchestration.planning.decision_engine import DecisionEngine
from src.domain.orchestration.planning.task_decomposer import TaskDecomposer

# Nested Workflows
from src.domain.orchestration.nested.workflow_manager import NestedWorkflowManager
from src.domain.orchestration.nested.sub_executor import SubWorkflowExecutor
from src.domain.orchestration.nested.recursive_handler import RecursiveHandler

# Collaboration
from src.domain.orchestration.collaboration.protocol import CollaborationProtocol
from src.domain.orchestration.collaboration.session import CollaborationSession


class TestConcurrentWithNestedWorkflows:
    """Integration tests: Concurrent Execution + Nested Workflows"""

    @pytest.fixture
    def concurrent_executor(self):
        """Create concurrent executor"""
        return ConcurrentExecutor(max_parallel=5)

    @pytest.fixture
    def nested_manager(self):
        """Create nested workflow manager"""
        return NestedWorkflowManager(max_depth=3)

    @pytest.fixture
    def sub_executor(self):
        """Create sub-workflow executor"""
        return SubWorkflowExecutor()

    @pytest.mark.asyncio
    async def test_concurrent_nested_workflow_execution(
        self,
        concurrent_executor,
        nested_manager
    ):
        """Test concurrent execution of nested workflows"""
        # Create parent workflow
        parent_workflow_id = uuid4()

        # Create nested workflows
        nested_workflow_1 = uuid4()
        nested_workflow_2 = uuid4()

        # Register nested workflows
        nested_manager.register_workflow(
            parent_id=parent_workflow_id,
            child_id=nested_workflow_1,
            depth=1
        )
        nested_manager.register_workflow(
            parent_id=parent_workflow_id,
            child_id=nested_workflow_2,
            depth=1
        )

        # Create concurrent tasks for nested workflows
        tasks = [
            {"id": str(nested_workflow_1), "type": "nested_workflow"},
            {"id": str(nested_workflow_2), "type": "nested_workflow"}
        ]

        # Execute concurrently
        state = ConcurrentState(workflow_id=str(parent_workflow_id))
        for task in tasks:
            state.add_task(task["id"], task)

        # Verify concurrent execution state
        assert len(state.pending_tasks) == 2
        assert state.can_start_more_tasks(max_concurrent=5)

    @pytest.mark.asyncio
    async def test_parallel_gateway_with_sub_workflows(
        self,
        concurrent_executor,
        sub_executor
    ):
        """Test parallel gateway splitting to sub-workflows"""
        gateway = ParallelGateway(gateway_id="fork_1")

        # Define branches with sub-workflows
        branches = [
            {"branch_id": "branch_1", "sub_workflow": "validation_flow"},
            {"branch_id": "branch_2", "sub_workflow": "notification_flow"},
            {"branch_id": "branch_3", "sub_workflow": "logging_flow"}
        ]

        # Configure gateway
        for branch in branches:
            gateway.add_branch(branch["branch_id"], branch)

        # Fork execution
        fork_result = gateway.fork()

        assert fork_result["status"] == "forked"
        assert len(fork_result["branches"]) == 3

    @pytest.mark.asyncio
    async def test_recursive_nested_with_concurrency_limit(
        self,
        concurrent_executor,
        nested_manager
    ):
        """Test recursive workflows respect concurrency limits"""
        handler = RecursiveHandler(max_depth=3, max_concurrent=2)

        # Create recursive workflow structure
        root_id = uuid4()
        level_1 = [uuid4() for _ in range(3)]

        # Track concurrent executions
        concurrent_count = 0
        max_concurrent = 0

        async def track_execution(wf_id):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.05)
            concurrent_count -= 1
            return {"status": "completed"}

        # Register workflows
        for child_id in level_1:
            nested_manager.register_workflow(root_id, child_id, depth=1)

        # Verify depth tracking
        assert nested_manager.get_depth(level_1[0]) == 1
        assert not nested_manager.can_nest_deeper(level_1[0], max_depth=2)


class TestGroupChatWithDynamicPlanning:
    """Integration tests: GroupChat + Dynamic Planning"""

    @pytest.fixture
    def groupchat_manager(self):
        """Create GroupChat manager"""
        return GroupChatManager(max_participants=10, max_rounds=20)

    @pytest.fixture
    def dynamic_planner(self):
        """Create dynamic planner"""
        return DynamicPlanner()

    @pytest.fixture
    def decision_engine(self):
        """Create decision engine"""
        return DecisionEngine()

    @pytest.mark.asyncio
    async def test_groupchat_with_planning_coordination(
        self,
        groupchat_manager,
        dynamic_planner
    ):
        """Test GroupChat coordinating with dynamic planning"""
        # Setup participants
        participants = [
            {"id": "planner", "role": "coordinator", "capabilities": ["planning"]},
            {"id": "executor_1", "role": "worker", "capabilities": ["execution"]},
            {"id": "executor_2", "role": "worker", "capabilities": ["execution"]},
            {"id": "reviewer", "role": "validator", "capabilities": ["validation"]}
        ]

        # Initialize GroupChat
        session_id = groupchat_manager.create_session(
            session_id=str(uuid4()),
            participants=participants
        )

        # Create task through planner
        task = {
            "goal": "Process customer order",
            "complexity": "medium",
            "steps": ["validate", "process", "notify"]
        }

        plan = dynamic_planner.create_plan(task)

        # Add plan to GroupChat context
        groupchat_manager.set_context(session_id, {"plan": plan})

        # Verify integration
        context = groupchat_manager.get_context(session_id)
        assert context["plan"] is not None
        assert len(context["plan"]["steps"]) > 0

    @pytest.mark.asyncio
    async def test_speaker_selection_based_on_plan_step(
        self,
        groupchat_manager,
        dynamic_planner
    ):
        """Test speaker selection aligned with plan execution"""
        selector = SpeakerSelector(strategy="capability_based")

        # Participants with different capabilities
        participants = [
            {"id": "agent_1", "capabilities": ["data_processing", "analysis"]},
            {"id": "agent_2", "capabilities": ["validation", "reporting"]},
            {"id": "agent_3", "capabilities": ["notification", "logging"]}
        ]

        # Plan step requiring specific capability
        current_step = {"action": "validate_data", "required_capability": "validation"}

        # Select speaker based on capability
        selected = selector.select_next_speaker(
            participants=participants,
            context={"current_step": current_step},
            history=[]
        )

        assert selected["id"] == "agent_2"  # Has validation capability

    @pytest.mark.asyncio
    async def test_decision_engine_with_groupchat_voting(
        self,
        decision_engine,
        groupchat_manager
    ):
        """Test decision engine using GroupChat voting"""
        from src.domain.orchestration.groupchat.voting import VotingManager

        voting_manager = VotingManager()

        # Setup decision scenario
        decision = {
            "question": "Should we proceed with Option A or B?",
            "options": ["option_a", "option_b"],
            "voters": ["agent_1", "agent_2", "agent_3"]
        }

        # Create voting session
        vote_id = voting_manager.create_vote(
            decision["question"],
            decision["options"]
        )

        # Simulate votes
        voting_manager.cast_vote(vote_id, "agent_1", "option_a")
        voting_manager.cast_vote(vote_id, "agent_2", "option_a")
        voting_manager.cast_vote(vote_id, "agent_3", "option_b")

        # Get result
        result = voting_manager.get_result(vote_id)

        assert result["winner"] == "option_a"
        assert result["votes"]["option_a"] == 2


class TestHandoffWithCapabilityMatching:
    """Integration tests: Agent Handoff + Capability Matching"""

    @pytest.fixture
    def handoff_controller(self):
        """Create handoff controller"""
        return HandoffController()

    @pytest.fixture
    def capability_matcher(self):
        """Create capability matcher"""
        return CapabilityMatcher()

    @pytest.fixture
    def handoff_trigger(self):
        """Create handoff trigger"""
        config = TriggerConfig(
            trigger_type=TriggerType.CAPABILITY,
            conditions={"required_capability": "specialist_task"}
        )
        return HandoffTrigger(config)

    @pytest.mark.asyncio
    async def test_capability_based_handoff(
        self,
        handoff_controller,
        capability_matcher
    ):
        """Test handoff triggered by capability requirement"""
        # Define agents with capabilities
        source_agent = {
            "id": "general_agent",
            "capabilities": [
                AgentCapability(name="general_processing", level=0.8),
                AgentCapability(name="basic_analysis", level=0.7)
            ]
        }

        target_agents = [
            {
                "id": "specialist_1",
                "capabilities": [
                    AgentCapability(name="specialist_task", level=0.95),
                    AgentCapability(name="advanced_analysis", level=0.9)
                ]
            },
            {
                "id": "specialist_2",
                "capabilities": [
                    AgentCapability(name="specialist_task", level=0.85),
                    AgentCapability(name="general_processing", level=0.8)
                ]
            }
        ]

        # Register agents
        for agent in [source_agent] + target_agents:
            capability_matcher.register_agent(agent["id"], agent["capabilities"])

        # Find best match for required capability
        required = AgentCapability(name="specialist_task", level=0.9)
        match = capability_matcher.find_best_match(
            required,
            strategy=MatchStrategy.BEST_FIT
        )

        assert match["agent_id"] == "specialist_1"  # Highest capability level

        # Execute handoff
        handoff_result = await handoff_controller.execute_handoff(
            source_agent_id="general_agent",
            target_agent_id=match["agent_id"],
            context={"task": "specialist_task_execution"}
        )

        assert handoff_result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_trigger_evaluation_with_capability_check(
        self,
        handoff_trigger,
        capability_matcher
    ):
        """Test trigger evaluation using capability matching"""
        # Current context
        context = {
            "current_agent": "general_agent",
            "task_type": "specialist_task",
            "complexity": "high"
        }

        # Evaluate trigger
        should_trigger = handoff_trigger.evaluate(context)

        assert should_trigger is True

    @pytest.mark.asyncio
    async def test_handoff_chain_with_multiple_specialists(
        self,
        handoff_controller,
        capability_matcher
    ):
        """Test chain of handoffs through multiple specialists"""
        # Define workflow requiring multiple specialists
        workflow_steps = [
            {"step": 1, "capability": "data_extraction"},
            {"step": 2, "capability": "data_analysis"},
            {"step": 3, "capability": "report_generation"}
        ]

        # Register specialist agents
        specialists = [
            {"id": "extractor", "capabilities": [AgentCapability("data_extraction", 0.9)]},
            {"id": "analyst", "capabilities": [AgentCapability("data_analysis", 0.9)]},
            {"id": "reporter", "capabilities": [AgentCapability("report_generation", 0.9)]}
        ]

        for agent in specialists:
            capability_matcher.register_agent(agent["id"], agent["capabilities"])

        # Execute handoff chain
        handoff_chain = []
        current_agent = None

        for step in workflow_steps:
            required = AgentCapability(name=step["capability"], level=0.8)
            match = capability_matcher.find_best_match(required, MatchStrategy.BEST_FIT)

            if current_agent and current_agent != match["agent_id"]:
                handoff_chain.append({
                    "from": current_agent,
                    "to": match["agent_id"],
                    "step": step["step"]
                })

            current_agent = match["agent_id"]

        assert len(handoff_chain) == 2  # Two handoffs in the chain


class TestFullPhase2Integration:
    """Full integration tests covering all Phase 2 components"""

    @pytest.fixture
    def full_context(self):
        """Create full Phase 2 context"""
        return {
            "concurrent_executor": ConcurrentExecutor(max_parallel=10),
            "nested_manager": NestedWorkflowManager(max_depth=5),
            "groupchat_manager": GroupChatManager(),
            "dynamic_planner": DynamicPlanner(),
            "handoff_controller": HandoffController(),
            "capability_matcher": CapabilityMatcher(),
            "collaboration_protocol": CollaborationProtocol()
        }

    @pytest.mark.asyncio
    async def test_full_workflow_with_all_phase2_features(self, full_context):
        """Test complete workflow using all Phase 2 features"""
        # 1. Create initial plan
        task = {
            "goal": "Process complex enterprise request",
            "subtasks": [
                "data_validation",
                "parallel_processing",
                "specialist_review",
                "final_approval"
            ]
        }

        plan = full_context["dynamic_planner"].create_plan(task)

        # 2. Setup GroupChat for coordination
        session_id = full_context["groupchat_manager"].create_session(
            session_id=str(uuid4()),
            participants=[
                {"id": "coordinator", "role": "manager"},
                {"id": "worker_1", "role": "worker"},
                {"id": "worker_2", "role": "worker"},
                {"id": "specialist", "role": "specialist"}
            ]
        )

        # 3. Register agent capabilities
        full_context["capability_matcher"].register_agent(
            "coordinator",
            [AgentCapability("coordination", 0.9), AgentCapability("planning", 0.85)]
        )
        full_context["capability_matcher"].register_agent(
            "worker_1",
            [AgentCapability("data_processing", 0.9)]
        )
        full_context["capability_matcher"].register_agent(
            "worker_2",
            [AgentCapability("validation", 0.9)]
        )
        full_context["capability_matcher"].register_agent(
            "specialist",
            [AgentCapability("specialist_review", 0.95)]
        )

        # 4. Create nested workflow structure
        parent_id = uuid4()
        sub_workflow_1 = uuid4()
        sub_workflow_2 = uuid4()

        full_context["nested_manager"].register_workflow(parent_id, sub_workflow_1, 1)
        full_context["nested_manager"].register_workflow(parent_id, sub_workflow_2, 1)

        # 5. Setup concurrent execution
        state = ConcurrentState(workflow_id=str(parent_id))
        state.add_task(str(sub_workflow_1), {"type": "validation"})
        state.add_task(str(sub_workflow_2), {"type": "processing"})

        # 6. Initialize collaboration session
        collab_session = full_context["collaboration_protocol"].create_session(
            session_id=str(uuid4()),
            participants=["coordinator", "worker_1", "worker_2", "specialist"]
        )

        # Verify all components are integrated
        assert plan is not None
        assert session_id is not None
        assert len(state.pending_tasks) == 2
        assert full_context["nested_manager"].get_depth(sub_workflow_1) == 1
        assert collab_session is not None

    @pytest.mark.asyncio
    async def test_error_handling_across_phase2_components(self, full_context):
        """Test error handling and recovery across Phase 2"""
        # Test graceful degradation

        # 1. Test concurrent execution error handling
        state = ConcurrentState(workflow_id="test_workflow")
        state.add_task("task_1", {"type": "test"})
        state.mark_task_failed("task_1", Exception("Test error"))

        assert state.get_task_state("task_1") == TaskState.FAILED

        # 2. Test nested workflow depth limit
        nested_manager = full_context["nested_manager"]
        parent_id = uuid4()

        # Create deeply nested structure
        current_parent = parent_id
        for depth in range(1, 6):
            child_id = uuid4()
            nested_manager.register_workflow(current_parent, child_id, depth)
            current_parent = child_id

        # Verify max depth enforcement
        assert not nested_manager.can_nest_deeper(current_parent, max_depth=5)

        # 3. Test capability matcher with no match
        matcher = full_context["capability_matcher"]
        required = AgentCapability(name="nonexistent_capability", level=0.9)
        match = matcher.find_best_match(required, MatchStrategy.BEST_FIT)

        assert match is None or match.get("agent_id") is None

    @pytest.mark.asyncio
    async def test_performance_under_load(self, full_context):
        """Test Phase 2 components under simulated load"""
        import time

        # Create many concurrent tasks
        num_tasks = 100
        state = ConcurrentState(workflow_id="load_test")

        start_time = time.perf_counter()

        for i in range(num_tasks):
            state.add_task(f"task_{i}", {"index": i})

        task_creation_time = time.perf_counter() - start_time

        # Verify performance
        assert task_creation_time < 1.0  # Should complete in under 1 second
        assert len(state.pending_tasks) == num_tasks

        # Test parallel gateway performance
        gateway = ParallelGateway(gateway_id="perf_test")

        start_time = time.perf_counter()

        for i in range(50):
            gateway.add_branch(f"branch_{i}", {"data": i})

        fork_result = gateway.fork()

        fork_time = time.perf_counter() - start_time

        assert fork_time < 0.5  # Should complete quickly
        assert len(fork_result["branches"]) == 50


class TestCollaborationIntegration:
    """Integration tests for Collaboration features"""

    @pytest.fixture
    def collaboration_protocol(self):
        """Create collaboration protocol"""
        return CollaborationProtocol()

    @pytest.fixture
    def multiturn_manager(self):
        """Create multi-turn session manager"""
        return MultiTurnSessionManager()

    @pytest.mark.asyncio
    async def test_collaboration_with_multiturn_conversation(
        self,
        collaboration_protocol,
        multiturn_manager
    ):
        """Test collaboration protocol with multi-turn conversation"""
        # Create collaboration session
        collab_session_id = collaboration_protocol.create_session(
            session_id=str(uuid4()),
            participants=["agent_1", "agent_2", "agent_3"]
        )

        # Create multi-turn session
        turn_tracker = TurnTracker()

        # Simulate conversation turns
        turns = [
            {"speaker": "agent_1", "message": "Let's start the analysis"},
            {"speaker": "agent_2", "message": "I'll handle data processing"},
            {"speaker": "agent_3", "message": "I'll prepare the report template"},
            {"speaker": "agent_1", "message": "Great, let's proceed"}
        ]

        for turn in turns:
            turn_tracker.record_turn(
                speaker=turn["speaker"],
                message=turn["message"]
            )

        # Verify conversation tracking
        assert turn_tracker.get_turn_count() == 4
        assert turn_tracker.get_last_speaker() == "agent_1"

    @pytest.mark.asyncio
    async def test_context_propagation_in_collaboration(
        self,
        collaboration_protocol
    ):
        """Test context propagation across collaboration sessions"""
        # Create parent session
        parent_session = collaboration_protocol.create_session(
            session_id="parent_session",
            participants=["coordinator"]
        )

        # Set context
        collaboration_protocol.set_session_context(
            "parent_session",
            {"shared_data": "important_value", "config": {"timeout": 30}}
        )

        # Create child session inheriting context
        child_session = collaboration_protocol.create_session(
            session_id="child_session",
            participants=["worker"],
            parent_session_id="parent_session"
        )

        # Verify context inheritance
        child_context = collaboration_protocol.get_session_context("child_session")

        assert child_context.get("shared_data") == "important_value"
