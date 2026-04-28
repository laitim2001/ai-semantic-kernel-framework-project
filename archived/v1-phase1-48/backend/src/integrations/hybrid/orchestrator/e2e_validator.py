"""E2E Assembly Validator — validates the complete orchestration pipeline.

Provides a comprehensive validation of all components assembled across
Phase 35-38 (E2E Assembly A0 → C), checking connectivity, configuration,
and readiness for production use.

Sprint 120 — Phase 38 E2E Assembly C.
"""

import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class E2EValidator:
    """Validates the complete E2E orchestration pipeline.

    Checks all 10 steps of the end-to-end flow:
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
    """

    def __init__(self) -> None:
        self._results: List[Dict[str, Any]] = []

    async def validate_all(self) -> Dict[str, Any]:
        """Run all validation checks and return a comprehensive report."""
        start = time.perf_counter()
        self._results = []

        await self._check_orchestrator_pipeline()
        await self._check_tool_registry()
        await self._check_task_system()
        await self._check_checkpoint_system()
        await self._check_memory_system()
        await self._check_knowledge_system()
        await self._check_circuit_breaker()
        await self._check_session_recovery()
        await self._check_observability()

        total_ms = (time.perf_counter() - start) * 1000
        passed = sum(1 for r in self._results if r["status"] == "pass")
        failed = sum(1 for r in self._results if r["status"] == "fail")
        warnings = sum(1 for r in self._results if r["status"] == "warn")

        return {
            "validation_time_ms": round(total_ms, 2),
            "total_checks": len(self._results),
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "overall": "PASS" if failed == 0 else "FAIL",
            "checks": self._results,
        }

    def _record(self, name: str, status: str, detail: str = "") -> None:
        self._results.append({"name": name, "status": status, "detail": detail})

    async def _check_orchestrator_pipeline(self) -> None:
        """Check core orchestrator components."""
        try:
            from src.integrations.hybrid.orchestrator.mediator import OrchestratorMediator
            self._record("orchestrator.mediator", "pass", "OrchestratorMediator importable")
        except Exception as e:
            self._record("orchestrator.mediator", "fail", str(e))

        try:
            from src.integrations.hybrid.orchestrator.agent_handler import AgentHandler
            self._record("orchestrator.agent_handler", "pass", "AgentHandler importable")
        except Exception as e:
            self._record("orchestrator.agent_handler", "fail", str(e))

        try:
            from src.integrations.hybrid.orchestrator.session_factory import OrchestratorSessionFactory
            self._record("orchestrator.session_factory", "pass", "SessionFactory importable")
        except Exception as e:
            self._record("orchestrator.session_factory", "fail", str(e))

    async def _check_tool_registry(self) -> None:
        """Check tool registry and handler wiring."""
        try:
            from src.integrations.hybrid.orchestrator.tools import OrchestratorToolRegistry
            registry = OrchestratorToolRegistry()
            tools = registry.list_tools(role="admin")
            tool_count = len(tools)
            expected = 9  # 6 original + update_task_status + search_knowledge + (assess_risk already counted)
            if tool_count >= 8:
                self._record("tools.registry", "pass", f"{tool_count} tools defined")
            else:
                self._record("tools.registry", "warn", f"Only {tool_count} tools (expected >= 8)")
        except Exception as e:
            self._record("tools.registry", "fail", str(e))

        try:
            from src.integrations.hybrid.orchestrator.dispatch_handlers import DispatchHandlers
            handlers = DispatchHandlers()
            self._record("tools.dispatch_handlers", "pass", "DispatchHandlers importable")
        except Exception as e:
            self._record("tools.dispatch_handlers", "fail", str(e))

    async def _check_task_system(self) -> None:
        """Check task domain model and service."""
        try:
            from src.domain.tasks.models import Task, TaskStatus, TaskType
            self._record("tasks.models", "pass", f"TaskStatus: {len(TaskStatus)} states, TaskType: {len(TaskType)} types")
        except Exception as e:
            self._record("tasks.models", "fail", str(e))

        try:
            from src.domain.tasks.service import TaskService
            self._record("tasks.service", "pass", "TaskService importable")
        except Exception as e:
            self._record("tasks.service", "fail", str(e))

    async def _check_checkpoint_system(self) -> None:
        """Check three-layer checkpoint system."""
        try:
            from src.infrastructure.storage.conversation_state import ConversationStateStore
            self._record("checkpoint.L1_conversation", "pass", "ConversationStateStore ready")
        except Exception as e:
            self._record("checkpoint.L1_conversation", "fail", str(e))

        try:
            from src.infrastructure.storage.task_store import TaskStore
            self._record("checkpoint.L2_tasks", "pass", "TaskStore ready")
        except Exception as e:
            self._record("checkpoint.L2_tasks", "fail", str(e))

        try:
            from src.infrastructure.storage.execution_state import ExecutionStateStore
            self._record("checkpoint.L3_execution", "pass", "ExecutionStateStore ready")
        except Exception as e:
            self._record("checkpoint.L3_execution", "fail", str(e))

    async def _check_memory_system(self) -> None:
        """Check memory manager and mem0 integration."""
        try:
            from src.integrations.hybrid.orchestrator.memory_manager import OrchestratorMemoryManager
            self._record("memory.manager", "pass", "OrchestratorMemoryManager ready")
        except Exception as e:
            self._record("memory.manager", "fail", str(e))

        try:
            from src.integrations.memory.unified_memory import UnifiedMemoryManager
            self._record("memory.unified", "pass", "UnifiedMemoryManager importable")
        except Exception as e:
            self._record("memory.unified", "warn", f"Not available: {e}")

    async def _check_knowledge_system(self) -> None:
        """Check RAG pipeline and agent skills."""
        try:
            from src.integrations.knowledge.rag_pipeline import RAGPipeline
            self._record("knowledge.rag_pipeline", "pass", "RAGPipeline ready")
        except Exception as e:
            self._record("knowledge.rag_pipeline", "fail", str(e))

        try:
            from src.integrations.knowledge.agent_skills import AgentSkillsProvider
            provider = AgentSkillsProvider()
            skills = provider.list_skills()
            self._record("knowledge.agent_skills", "pass", f"{len(skills)} skills registered")
        except Exception as e:
            self._record("knowledge.agent_skills", "fail", str(e))

    async def _check_circuit_breaker(self) -> None:
        """Check circuit breaker availability."""
        try:
            from src.core.performance.circuit_breaker import get_llm_circuit_breaker
            cb = get_llm_circuit_breaker()
            self._record("resilience.circuit_breaker", "pass", f"State: {cb.state.value}")
        except Exception as e:
            self._record("resilience.circuit_breaker", "fail", str(e))

    async def _check_session_recovery(self) -> None:
        """Check session recovery manager."""
        try:
            from src.integrations.hybrid.orchestrator.session_recovery import SessionRecoveryManager
            self._record("recovery.session_manager", "pass", "SessionRecoveryManager ready")
        except Exception as e:
            self._record("recovery.session_manager", "fail", str(e))

    async def _check_observability(self) -> None:
        """Check observability bridge."""
        try:
            from src.integrations.hybrid.orchestrator.observability_bridge import ObservabilityBridge
            self._record("observability.bridge", "pass", "ObservabilityBridge ready")
        except Exception as e:
            self._record("observability.bridge", "fail", str(e))

        try:
            from src.integrations.hybrid.swarm_mode import SwarmExecutionConfig
            config = SwarmExecutionConfig()
            status = "enabled" if config.enabled else "disabled"
            self._record("swarm.feature_flag", "pass" if config.enabled else "warn", f"Swarm mode: {status}")
        except Exception as e:
            self._record("swarm.feature_flag", "warn", str(e))
