# =============================================================================
# IPA Platform - Swarm Mode Handler for HybridOrchestratorV2
# =============================================================================
# Sprint 116: Integrates Swarm execution into the main execute_with_routing() flow.
# Enables multi-agent collaboration as a first-class execution mode.
#
# Dependencies:
#   - SwarmIntegration (src.integrations.swarm)
#   - SwarmMode, SwarmStatus (src.integrations.swarm.models)
#
# Key Classes:
#   - SwarmExecutionConfig: Configuration dataclass for Swarm execution mode
#   - SwarmTaskDecomposition: Result of task decomposition analysis
#   - SwarmExecutionResult: Result from Swarm execution
#   - SwarmModeHandler: Main handler coordinating SwarmIntegration
# =============================================================================

import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.integrations.swarm.swarm_integration import SwarmIntegration

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class SwarmExecutionConfig:
    """
    Configuration for Swarm execution mode.

    Attributes:
        enabled: Whether Swarm mode is enabled (feature flag)
        default_mode: Default swarm execution pattern (sequential, parallel, hierarchical)
        max_workers: Maximum number of concurrent workers
        worker_timeout: Timeout for individual worker execution in seconds
        complexity_threshold: Intent complexity threshold to trigger swarm
        min_subtasks: Minimum subtasks required to justify swarm mode
    """

    enabled: bool = False
    default_mode: str = "parallel"
    max_workers: int = 5
    worker_timeout: float = 120.0
    complexity_threshold: float = 0.7
    min_subtasks: int = 2

    @classmethod
    def from_env(cls) -> "SwarmExecutionConfig":
        """
        Create configuration from environment variables.

        Environment variables:
            SWARM_MODE_ENABLED: Enable/disable swarm mode (default: false)
            SWARM_DEFAULT_MODE: Default mode (default: parallel)
            SWARM_MAX_WORKERS: Max concurrent workers (default: 5)
            SWARM_WORKER_TIMEOUT: Worker timeout seconds (default: 120.0)
            SWARM_COMPLEXITY_THRESHOLD: Complexity threshold (default: 0.7)
            SWARM_MIN_SUBTASKS: Minimum subtasks (default: 2)

        Returns:
            SwarmExecutionConfig instance
        """
        return cls(
            enabled=os.getenv("SWARM_MODE_ENABLED", "false").lower() == "true",
            default_mode=os.getenv("SWARM_DEFAULT_MODE", "parallel"),
            max_workers=int(os.getenv("SWARM_MAX_WORKERS", "5")),
            worker_timeout=float(os.getenv("SWARM_WORKER_TIMEOUT", "120.0")),
            complexity_threshold=float(os.getenv("SWARM_COMPLEXITY_THRESHOLD", "0.7")),
            min_subtasks=int(os.getenv("SWARM_MIN_SUBTASKS", "2")),
        )


# =============================================================================
# Result Data Classes
# =============================================================================


@dataclass
class SwarmTaskDecomposition:
    """
    Result of decomposing a task into subtasks for Swarm execution.

    Attributes:
        should_use_swarm: Whether swarm mode should be activated
        subtasks: List of subtask definitions
        swarm_mode: Selected swarm execution mode
        reasoning: Human-readable explanation for the decision
        estimated_workers: Number of workers that will be used
    """

    should_use_swarm: bool
    subtasks: List[Dict[str, Any]] = field(default_factory=list)
    swarm_mode: str = "parallel"
    reasoning: str = ""
    estimated_workers: int = 0


@dataclass
class SwarmExecutionResult:
    """
    Result from Swarm execution.

    Attributes:
        success: Whether the overall execution succeeded
        swarm_id: Unique identifier for this swarm run
        content: Aggregated content from all workers
        error: Error message if execution failed
        worker_results: Individual results from each worker
        total_duration: Total execution duration in seconds
        metadata: Additional execution metadata
    """

    success: bool
    swarm_id: str
    content: str = ""
    error: Optional[str] = None
    worker_results: List[Dict[str, Any]] = field(default_factory=list)
    total_duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Swarm Mode Handler
# =============================================================================


class SwarmModeHandler:
    """
    Swarm Mode Handler -- integrates multi-agent swarm execution into main flow.

    Sprint 116: Coordinates SwarmIntegration within HybridOrchestratorV2.execute_with_routing().

    Responsibilities:
    - Determine if Swarm mode should be used (based on intent complexity, workflow type, etc.)
    - Decompose tasks into subtasks for worker distribution
    - Execute via SwarmIntegration callbacks
    - Aggregate worker results into unified response

    Usage:
        handler = SwarmModeHandler(swarm_integration=integration)

        decomposition = handler.analyze_for_swarm(routing_decision, context)
        if decomposition.should_use_swarm:
            result = await handler.execute_swarm(
                intent=request.content,
                decomposition=decomposition,
                routing_decision=routing_decision,
            )
    """

    # Workflow types eligible for swarm mode
    SWARM_ELIGIBLE_WORKFLOW_TYPES = frozenset({
        "CONCURRENT", "MAGENTIC", "concurrent", "magentic",
    })

    def __init__(
        self,
        swarm_integration: Optional["SwarmIntegration"] = None,
        config: Optional[SwarmExecutionConfig] = None,
        claude_executor: Optional[Callable] = None,
    ):
        """
        Initialize SwarmModeHandler.

        Args:
            swarm_integration: SwarmIntegration for tracking (lazy-loaded if None)
            config: Swarm execution configuration
            claude_executor: Executor function for individual worker tasks
        """
        self._swarm_integration = swarm_integration
        self._config = config or SwarmExecutionConfig.from_env()
        self._claude_executor = claude_executor
        logger.info(
            f"SwarmModeHandler initialized: enabled={self._config.enabled}, "
            f"default_mode={self._config.default_mode}, "
            f"max_workers={self._config.max_workers}"
        )

    @property
    def is_enabled(self) -> bool:
        """Check if Swarm mode is enabled."""
        return self._config.enabled

    @property
    def config(self) -> SwarmExecutionConfig:
        """Get current configuration."""
        return self._config

    def _get_swarm_integration(self) -> "SwarmIntegration":
        """
        Get or create SwarmIntegration (lazy loading).

        Returns:
            SwarmIntegration instance
        """
        if self._swarm_integration is None:
            from src.integrations.swarm.swarm_integration import SwarmIntegration

            self._swarm_integration = SwarmIntegration()
        return self._swarm_integration

    # =========================================================================
    # Analysis Methods
    # =========================================================================

    def analyze_for_swarm(
        self,
        routing_decision: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> SwarmTaskDecomposition:
        """
        Analyze whether the task should use Swarm execution mode.

        Decision criteria:
        1. Swarm mode must be enabled (feature flag)
        2. WorkflowType must be CONCURRENT, MAGENTIC, or explicitly SWARM
        3. Task must have sufficient complexity (multiple sub-intents or tools)
        4. Context may override (user explicit request for swarm)

        Args:
            routing_decision: RoutingDecision from BusinessIntentRouter
            context: Optional additional context

        Returns:
            SwarmTaskDecomposition with analysis result
        """
        context = context or {}

        # Check 1: Feature flag
        if not self._config.enabled:
            return SwarmTaskDecomposition(
                should_use_swarm=False,
                reasoning="Swarm mode is disabled (SWARM_MODE_ENABLED=false)",
            )

        # Check 2: Explicit user request
        user_requested_swarm = context.get("use_swarm", False)
        if user_requested_swarm:
            subtasks = context.get("subtasks", [])
            if not subtasks:
                subtasks = self._decompose_from_decision(routing_decision)
            return SwarmTaskDecomposition(
                should_use_swarm=True,
                subtasks=subtasks,
                swarm_mode=context.get("swarm_mode", self._config.default_mode),
                reasoning="User explicitly requested swarm mode",
                estimated_workers=min(len(subtasks), self._config.max_workers),
            )

        # Check 3: Workflow type analysis
        workflow_type = self._get_workflow_type(routing_decision)

        if workflow_type not in self.SWARM_ELIGIBLE_WORKFLOW_TYPES:
            return SwarmTaskDecomposition(
                should_use_swarm=False,
                reasoning=(
                    f"Workflow type '{workflow_type}' is not eligible for swarm "
                    f"(eligible: {sorted(self.SWARM_ELIGIBLE_WORKFLOW_TYPES)})"
                ),
            )

        # Check 4: Decompose and validate minimum subtasks
        subtasks = self._decompose_from_decision(routing_decision)
        if len(subtasks) < self._config.min_subtasks:
            return SwarmTaskDecomposition(
                should_use_swarm=False,
                subtasks=subtasks,
                reasoning=(
                    f"Insufficient subtasks ({len(subtasks)}) for swarm mode "
                    f"(minimum: {self._config.min_subtasks})"
                ),
            )

        # Determine swarm mode based on workflow type
        swarm_mode = self._determine_swarm_mode(workflow_type, subtasks)

        return SwarmTaskDecomposition(
            should_use_swarm=True,
            subtasks=subtasks,
            swarm_mode=swarm_mode,
            reasoning=(
                f"Task eligible for swarm: workflow_type={workflow_type}, "
                f"subtask_count={len(subtasks)}, mode={swarm_mode}"
            ),
            estimated_workers=min(len(subtasks), self._config.max_workers),
        )

    def _get_workflow_type(self, routing_decision: Any) -> str:
        """
        Extract workflow type from routing decision.

        Args:
            routing_decision: RoutingDecision object or compatible

        Returns:
            Workflow type string
        """
        if hasattr(routing_decision, "workflow_type"):
            wt = routing_decision.workflow_type
            return wt.value if hasattr(wt, "value") else str(wt)
        return "UNKNOWN"

    def _decompose_from_decision(
        self, routing_decision: Any
    ) -> List[Dict[str, Any]]:
        """
        Decompose routing decision into subtasks.

        Uses the routing decision's metadata to identify natural task boundaries.
        Falls back to sub_intent based decomposition if no explicit subtasks are found.

        Args:
            routing_decision: RoutingDecision from BusinessIntentRouter

        Returns:
            List of subtask dictionaries
        """
        subtasks: List[Dict[str, Any]] = []

        # Extract from metadata if available
        if hasattr(routing_decision, "metadata") and routing_decision.metadata:
            meta = routing_decision.metadata
            if isinstance(meta, dict):
                # Check for explicit subtasks in metadata
                if "subtasks" in meta:
                    return list(meta["subtasks"])
                # Check for required tools (each tool group = potential subtask)
                if "required_tools" in meta:
                    for i, tool_group in enumerate(meta["required_tools"]):
                        subtasks.append({
                            "id": f"subtask-{i + 1}",
                            "description": f"Execute tool group: {tool_group}",
                            "tools": (
                                [tool_group]
                                if isinstance(tool_group, str)
                                else tool_group
                            ),
                        })

        # Fallback: create subtasks from intent description
        if not subtasks and hasattr(routing_decision, "sub_intent"):
            sub_intent = routing_decision.sub_intent
            if sub_intent:
                subtasks.append({
                    "id": "subtask-1",
                    "description": f"Execute primary intent: {sub_intent}",
                })

        return subtasks

    def _determine_swarm_mode(
        self, workflow_type: str, subtasks: List[Dict[str, Any]]
    ) -> str:
        """
        Determine optimal swarm execution mode based on workflow type and subtasks.

        Args:
            workflow_type: Detected workflow type
            subtasks: Decomposed subtask list

        Returns:
            Swarm mode string (sequential, parallel, or hierarchical)
        """
        if workflow_type in ("CONCURRENT", "concurrent"):
            return "parallel"
        elif workflow_type in ("MAGENTIC", "magentic"):
            # Magentic-One pattern: hierarchical with coordinator
            return "hierarchical"
        return self._config.default_mode

    # =========================================================================
    # Execution Methods
    # =========================================================================

    async def execute_swarm(
        self,
        intent: str,
        decomposition: SwarmTaskDecomposition,
        routing_decision: Any,
        session_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> SwarmExecutionResult:
        """
        Execute task using Swarm mode.

        Flow:
        1. Create swarm via SwarmIntegration.on_coordination_started()
        2. Assign workers to subtasks
        3. Execute each worker (via claude_executor or simulated)
        4. Track progress via SwarmIntegration callbacks
        5. Aggregate results

        Args:
            intent: The user's original intent/query
            decomposition: Task decomposition result from analyze_for_swarm()
            routing_decision: The original routing decision
            session_id: Optional session identifier
            timeout: Execution timeout in seconds

        Returns:
            SwarmExecutionResult with aggregated results
        """
        start_time = time.time()
        swarm_id = f"swarm-{uuid.uuid4().hex[:12]}"
        integration = self._get_swarm_integration()
        timeout = timeout or self._config.worker_timeout

        try:
            # Import SwarmMode and SwarmStatus enums
            from src.integrations.swarm.models import (
                SwarmMode,
                SwarmStatus,
                WorkerStatus,
            )

            # Step 1: Start coordination
            mode_map = {
                "sequential": SwarmMode.SEQUENTIAL,
                "parallel": SwarmMode.PARALLEL,
                "hierarchical": SwarmMode.HIERARCHICAL,
            }
            swarm_mode = mode_map.get(
                decomposition.swarm_mode, SwarmMode.PARALLEL
            )

            integration.on_coordination_started(
                swarm_id=swarm_id,
                mode=swarm_mode,
                subtasks=decomposition.subtasks,
                metadata={
                    "intent": intent,
                    "session_id": session_id,
                    "workflow_type": self._get_workflow_type(routing_decision),
                },
            )

            # Step 2: Execute workers
            worker_results = await self._execute_all_workers(
                swarm_id=swarm_id,
                subtasks=decomposition.subtasks,
                intent=intent,
                integration=integration,
                timeout=timeout,
            )

            # Step 3: Complete coordination
            all_success = all(r["success"] for r in worker_results)
            final_status = (
                SwarmStatus.COMPLETED if all_success else SwarmStatus.FAILED
            )
            integration.on_coordination_completed(
                swarm_id=swarm_id, status=final_status
            )

            # Step 4: Aggregate results
            aggregated_content = self._aggregate_worker_results(
                worker_results, intent
            )

            completed_count = sum(
                1 for r in worker_results if r["success"]
            )
            failed_count = sum(
                1 for r in worker_results if not r["success"]
            )

            return SwarmExecutionResult(
                success=all_success,
                swarm_id=swarm_id,
                content=aggregated_content,
                worker_results=worker_results,
                total_duration=time.time() - start_time,
                metadata={
                    "mode": decomposition.swarm_mode,
                    "total_workers": len(decomposition.subtasks),
                    "completed_workers": completed_count,
                    "failed_workers": failed_count,
                },
            )
        except Exception as e:
            logger.error(f"Swarm execution failed: {e}", exc_info=True)
            self._try_fail_coordination(integration, swarm_id)

            return SwarmExecutionResult(
                success=False,
                swarm_id=swarm_id,
                error=str(e),
                total_duration=time.time() - start_time,
            )

    async def _execute_all_workers(
        self,
        swarm_id: str,
        subtasks: List[Dict[str, Any]],
        intent: str,
        integration: "SwarmIntegration",
        timeout: float,
    ) -> List[Dict[str, Any]]:
        """
        Execute all worker tasks sequentially.

        Args:
            swarm_id: The swarm identifier
            subtasks: List of subtask definitions
            intent: Original user intent
            integration: SwarmIntegration instance
            timeout: Per-worker timeout in seconds

        Returns:
            List of worker result dictionaries
        """
        worker_results: List[Dict[str, Any]] = []

        for i, subtask in enumerate(subtasks):
            worker_id = f"worker-{i + 1}"
            worker_name = subtask.get("name", f"Worker {i + 1}")
            task_desc = subtask.get("description", f"Subtask {i + 1}")

            # Infer worker type from name and description
            worker_type = integration._infer_worker_type(worker_name, task_desc)

            # Start worker
            integration.on_subtask_started(
                swarm_id=swarm_id,
                worker_id=worker_id,
                worker_name=worker_name,
                worker_type=worker_type,
                role=task_desc,
                task_description=task_desc,
            )

            # Execute worker task
            worker_result = await self._execute_single_worker(
                swarm_id=swarm_id,
                worker_id=worker_id,
                worker_name=worker_name,
                task_description=task_desc,
                intent=intent,
                integration=integration,
                timeout=timeout,
            )
            worker_results.append(worker_result)

        return worker_results

    async def _execute_single_worker(
        self,
        swarm_id: str,
        worker_id: str,
        worker_name: str,
        task_description: str,
        intent: str,
        integration: "SwarmIntegration",
        timeout: float,
    ) -> Dict[str, Any]:
        """
        Execute a single worker task with error handling.

        Args:
            swarm_id: The swarm identifier
            worker_id: The worker identifier
            worker_name: Display name of the worker
            task_description: Task to execute
            intent: Original user intent
            integration: SwarmIntegration instance
            timeout: Timeout in seconds

        Returns:
            Worker result dictionary
        """
        from src.integrations.swarm.models import WorkerStatus

        try:
            worker_result_content = await self._execute_worker_task(
                swarm_id=swarm_id,
                worker_id=worker_id,
                task_description=task_description,
                intent=intent,
                integration=integration,
                timeout=timeout,
            )

            # Complete worker successfully
            integration.on_subtask_completed(
                swarm_id=swarm_id,
                worker_id=worker_id,
                status=WorkerStatus.COMPLETED,
            )

            return {
                "worker_id": worker_id,
                "worker_name": worker_name,
                "task": task_description,
                "success": True,
                "result": worker_result_content,
            }

        except Exception as e:
            logger.error(f"Worker {worker_id} failed: {e}")
            integration.on_subtask_completed(
                swarm_id=swarm_id,
                worker_id=worker_id,
                status=WorkerStatus.FAILED,
                error=str(e),
            )
            return {
                "worker_id": worker_id,
                "worker_name": worker_name,
                "task": task_description,
                "success": False,
                "error": str(e),
            }

    async def _execute_worker_task(
        self,
        swarm_id: str,
        worker_id: str,
        task_description: str,
        intent: str,
        integration: "SwarmIntegration",
        timeout: float,
    ) -> str:
        """
        Execute a single worker task.

        Uses claude_executor if available, otherwise returns simulated result.

        Args:
            swarm_id: The swarm identifier
            worker_id: The worker identifier
            task_description: Description of the task to execute
            intent: Original user intent
            integration: SwarmIntegration instance for progress tracking
            timeout: Execution timeout in seconds

        Returns:
            Worker output content string
        """
        # Report initial progress
        integration.on_subtask_progress(
            swarm_id=swarm_id,
            worker_id=worker_id,
            progress=10,
            current_task=f"Starting: {task_description[:80]}",
        )

        if self._claude_executor:
            import asyncio

            result = await asyncio.wait_for(
                self._claude_executor(
                    prompt=(
                        f"Execute subtask: {task_description}\n\n"
                        f"Original intent: {intent}"
                    ),
                    history=[],
                    tools=None,
                    max_tokens=None,
                ),
                timeout=timeout,
            )

            # Report completion progress
            integration.on_subtask_progress(
                swarm_id=swarm_id,
                worker_id=worker_id,
                progress=100,
                current_task="Completed",
            )

            if isinstance(result, dict):
                return result.get("content", str(result))
            return str(result)
        else:
            # Simulated execution (no executor available)
            integration.on_subtask_progress(
                swarm_id=swarm_id,
                worker_id=worker_id,
                progress=100,
                current_task="Completed (simulated)",
            )
            return f"[SWARM_WORKER] Processed: {task_description}"

    # =========================================================================
    # Aggregation Methods
    # =========================================================================

    def _aggregate_worker_results(
        self,
        worker_results: List[Dict[str, Any]],
        intent: str,
    ) -> str:
        """
        Aggregate results from all workers into a unified response.

        Args:
            worker_results: List of worker result dictionaries
            intent: Original user intent

        Returns:
            Aggregated response string
        """
        successful = [r for r in worker_results if r["success"]]
        failed = [r for r in worker_results if not r["success"]]

        parts: List[str] = []

        if successful:
            for r in successful:
                result_text = r.get("result", "")
                if result_text:
                    parts.append(f"[{r['worker_name']}] {result_text}")

        if failed:
            error_parts = []
            for r in failed:
                error_parts.append(
                    f"[{r['worker_name']}] Error: {r.get('error', 'Unknown')}"
                )
            parts.append(
                f"\nPartial failures:\n" + "\n".join(error_parts)
            )

        if parts:
            return "\n\n".join(parts)
        return f"Swarm execution completed for: {intent[:100]}"

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _try_fail_coordination(
        self,
        integration: "SwarmIntegration",
        swarm_id: str,
    ) -> None:
        """
        Attempt to mark coordination as failed.

        Suppresses any exception to avoid masking the original error.

        Args:
            integration: SwarmIntegration instance
            swarm_id: The swarm identifier
        """
        try:
            from src.integrations.swarm.models import SwarmStatus

            integration.on_coordination_completed(
                swarm_id=swarm_id, status=SwarmStatus.FAILED
            )
        except Exception:
            logger.warning(
                f"Failed to mark coordination {swarm_id} as failed",
                exc_info=True,
            )
