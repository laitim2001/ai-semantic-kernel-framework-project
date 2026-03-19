"""E2E Smoke Test — validates the complete 10-step orchestration pipeline.

Tests the full end-to-end flow assembled across Phase 35-39:
  1. User input reception
  2. Memory retrieval + context injection
  3. Intent classification + risk assessment
  4. Agent selection (MAF/Claude/Swarm)
  5. Knowledge base search (search_knowledge)
  6. Memory search (search_memory)
  7. Tool execution + result collection
  8. Result synthesis
  9. Auto-summarise → Long-term Memory write
  10. Working Memory cleanup / Session Memory archive

Sprint 137 — Phase 39 E2E Assembly D.
"""

import asyncio
import pytest
from typing import Any, Dict


class TestE2EBootstrap:
    """Test that OrchestratorBootstrap assembles a working pipeline."""

    def test_bootstrap_imports(self):
        """Step 0: All assembly modules are importable."""
        from src.integrations.hybrid.orchestrator.bootstrap import OrchestratorBootstrap
        from src.integrations.hybrid.orchestrator.mediator import OrchestratorMediator
        from src.integrations.hybrid.orchestrator.tools import OrchestratorToolRegistry
        from src.integrations.hybrid.orchestrator.mcp_tool_bridge import MCPToolBridge
        assert OrchestratorBootstrap is not None
        assert OrchestratorMediator is not None

    def test_bootstrap_build(self):
        """Step 0: Bootstrap.build() returns a Mediator with handlers."""
        from src.integrations.hybrid.orchestrator.bootstrap import OrchestratorBootstrap
        bootstrap = OrchestratorBootstrap()
        mediator = bootstrap.build()
        assert mediator is not None

        health = bootstrap.health_check()
        assert health["status"] in ("healthy", "degraded")
        assert health["wired_count"] > 0

    def test_bootstrap_health_check(self):
        """Step 0: Health check reports component status."""
        from src.integrations.hybrid.orchestrator.bootstrap import OrchestratorBootstrap
        bootstrap = OrchestratorBootstrap()
        bootstrap.build()
        health = bootstrap.health_check()
        assert "components" in health
        assert "agent_handler" in health["components"]
        assert "tool_registry" in health["components"]


class TestE2EToolRegistry:
    """Test that tool registry has all tools wired."""

    def test_tool_count(self):
        """Step 5-6: All orchestrator tools are registered."""
        from src.integrations.hybrid.orchestrator.tools import OrchestratorToolRegistry
        registry = OrchestratorToolRegistry()
        tools = registry.list_tools(role="admin")
        # At least 9 built-in tools
        assert len(tools) >= 9, f"Expected >= 9 tools, got {len(tools)}"

    def test_tool_names(self):
        """Step 5-6: Expected tool names exist."""
        from src.integrations.hybrid.orchestrator.tools import OrchestratorToolRegistry
        registry = OrchestratorToolRegistry()
        expected = [
            "assess_risk", "search_memory", "request_approval",
            "create_task", "dispatch_workflow", "dispatch_swarm",
            "update_task_status", "search_knowledge",
        ]
        tool_names = [t.name for t in registry.list_tools(role="admin")]
        for name in expected:
            assert name in tool_names, f"Missing tool: {name}"

    def test_security_gateway_integration(self):
        """Step 3: SecurityGateway can be wired into registry."""
        from src.integrations.hybrid.orchestrator.tools import OrchestratorToolRegistry
        # With no gateway — should work fine
        registry = OrchestratorToolRegistry(security_gateway=None)
        assert registry._security_gateway is None

        # With mock gateway
        registry2 = OrchestratorToolRegistry(security_gateway={"mock": True})
        assert registry2._security_gateway is not None


class TestE2ETaskSystem:
    """Test task lifecycle."""

    def test_task_model(self):
        """Step 7: Task model with full lifecycle."""
        from src.domain.tasks.models import Task, TaskStatus, TaskType
        task = Task(title="Test task", task_type=TaskType.WORKFLOW)
        assert task.status == TaskStatus.PENDING
        task.mark_started()
        assert task.status == TaskStatus.IN_PROGRESS
        task.mark_completed()
        assert task.status == TaskStatus.COMPLETED
        assert task.progress == 1.0

    def test_task_failure(self):
        """Step 7: Task failure tracking."""
        from src.domain.tasks.models import Task
        task = Task(title="Failing task")
        task.mark_failed("Connection timeout")
        assert task.status.value == "failed"
        assert task.final_result is not None
        assert task.final_result.error == "Connection timeout"


class TestE2ECheckpoint:
    """Test three-layer checkpoint system."""

    def test_conversation_state_model(self):
        """Step 9-10: ConversationState lifecycle."""
        from src.infrastructure.storage.conversation_state import (
            ConversationState, ConversationMessage,
        )
        state = ConversationState(session_id="test-session")
        state.add_message("user", "Hello")
        state.add_message("assistant", "Hi there!")
        assert state.message_count == 2
        assert state.messages[0].role == "user"

    def test_execution_state_model(self):
        """Step 9: AgentExecutionState lifecycle."""
        from src.infrastructure.storage.execution_state import (
            AgentExecutionState, ToolCallRecord,
        )
        state = AgentExecutionState(
            session_id="test", execution_id="exec-1"
        )
        state.add_tool_call(ToolCallRecord(
            tool_name="search_memory", success=True
        ))
        assert len(state.tool_calls) == 1


class TestE2EMemoryKnowledge:
    """Test memory and knowledge systems."""

    def test_memory_manager_importable(self):
        """Step 2: MemoryManager is importable."""
        from src.integrations.hybrid.orchestrator.memory_manager import (
            OrchestratorMemoryManager,
        )
        mgr = OrchestratorMemoryManager()
        assert mgr is not None

    def test_memory_context_builder(self):
        """Step 2: Memory context builder formats correctly."""
        from src.integrations.hybrid.orchestrator.memory_manager import (
            OrchestratorMemoryManager,
        )
        mgr = OrchestratorMemoryManager()
        memories = [
            {"content": "Previous incident resolved", "metadata": {"summarised_at": "2026-03-15"}},
            {"content": "User prefers email notifications", "metadata": {}},
        ]
        ctx = mgr.build_memory_context(memories)
        assert "歷史記憶" in ctx
        assert "Previous incident" in ctx

    def test_rag_pipeline_importable(self):
        """Step 5: RAG pipeline is importable."""
        from src.integrations.knowledge.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline()
        assert pipeline is not None

    def test_agent_skills_loaded(self):
        """Step 5: ITIL Agent Skills are loaded."""
        from src.integrations.knowledge.agent_skills import AgentSkillsProvider
        provider = AgentSkillsProvider()
        skills = provider.list_skills()
        assert len(skills) >= 3, f"Expected >= 3 skills, got {len(skills)}"


class TestE2EResultSynthesis:
    """Test result aggregation."""

    def test_task_result_envelope(self):
        """Step 8: TaskResultEnvelope aggregation."""
        from src.integrations.hybrid.orchestrator.task_result_protocol import (
            TaskResultEnvelope, WorkerResult, WorkerType, ResultStatus,
        )
        envelope = TaskResultEnvelope(task_id="test-1", task_type="workflow")
        envelope.add_result(WorkerResult(
            worker_id="w1", worker_type=WorkerType.MAF_WORKFLOW,
            output="Step completed", status=ResultStatus.SUCCESS,
        ))
        assert envelope.worker_count == 1
        assert envelope.is_success

    def test_result_synthesiser(self):
        """Step 8: ResultSynthesiser formats single result."""
        from src.integrations.hybrid.orchestrator.result_synthesiser import (
            ResultSynthesiser,
        )
        from src.integrations.hybrid.orchestrator.task_result_protocol import (
            TaskResultEnvelope, WorkerResult, WorkerType,
        )
        synth = ResultSynthesiser()
        envelope = TaskResultEnvelope(task_id="test-2")
        envelope.add_result(WorkerResult(
            worker_id="w1", worker_type=WorkerType.DIRECT,
            output="The answer is 42",
        ))
        result = asyncio.get_event_loop().run_until_complete(
            synth.synthesise(envelope)
        )
        assert "42" in result


class TestE2ECircuitBreaker:
    """Test resilience mechanisms."""

    def test_circuit_breaker_initial_state(self):
        """Step 3: Circuit breaker starts closed."""
        from src.core.performance.circuit_breaker import (
            get_llm_circuit_breaker, CircuitState,
        )
        cb = get_llm_circuit_breaker()
        assert cb.state == CircuitState.CLOSED

    def test_circuit_breaker_stats(self):
        """Step 3: Circuit breaker reports stats."""
        from src.core.performance.circuit_breaker import get_llm_circuit_breaker
        cb = get_llm_circuit_breaker()
        stats = cb.get_stats()
        assert stats["name"] == "llm_api"
        assert "failure_threshold" in stats


class TestE2ESessionRecovery:
    """Test session resume capability."""

    def test_recovery_manager_importable(self):
        """Step 9: SessionRecoveryManager is importable."""
        from src.integrations.hybrid.orchestrator.session_recovery import (
            SessionRecoveryManager,
        )
        mgr = SessionRecoveryManager()
        assert mgr is not None

    def test_recovery_result_model(self):
        """Step 9: RecoveryResult model."""
        from src.integrations.hybrid.orchestrator.session_recovery import (
            RecoveryResult,
        )
        result = RecoveryResult(session_id="test", success=False)
        assert not result.success
        assert result.layers_restored == []


class TestE2EValidator:
    """Test the E2E validation endpoint."""

    def test_validator_importable(self):
        """Validator module loads."""
        from src.integrations.hybrid.orchestrator.e2e_validator import E2EValidator
        validator = E2EValidator()
        assert validator is not None

    def test_validator_runs(self):
        """Validator executes all checks."""
        from src.integrations.hybrid.orchestrator.e2e_validator import E2EValidator
        validator = E2EValidator()
        result = asyncio.get_event_loop().run_until_complete(
            validator.validate_all()
        )
        assert "total_checks" in result
        assert result["total_checks"] > 0
        assert result["passed"] > 0
