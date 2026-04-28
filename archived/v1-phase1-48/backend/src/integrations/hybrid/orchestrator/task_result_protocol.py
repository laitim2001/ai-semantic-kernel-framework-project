"""TaskResult Protocol — unified result format for all worker types.

Normalises output from MAF Workflows, Claude Workers, and Swarm
coordination into a single ``TaskResultEnvelope`` that the Orchestrator
can pass to the LLM result synthesiser.

Sprint 114 — Phase 37 E2E Assembly B.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class WorkerType(str, Enum):
    """Origin of the task result."""

    MAF_WORKFLOW = "maf_workflow"
    CLAUDE_WORKER = "claude_worker"
    SWARM = "swarm"
    DIRECT = "direct"  # Orchestrator direct response


class ResultStatus(str, Enum):
    """Outcome status."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class WorkerResult(BaseModel):
    """Single worker output within a task."""

    worker_id: str
    worker_type: WorkerType
    worker_name: str = ""
    status: ResultStatus = ResultStatus.SUCCESS
    output: Any = None
    error: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    tokens_used: int = 0
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskResultEnvelope(BaseModel):
    """Unified envelope wrapping one or more worker results for a task.

    The Orchestrator uses this to:
    1. Track which workers contributed to the task.
    2. Pass all results to the LLM synthesiser for final response.
    3. Persist results in the Task Registry.
    """

    task_id: str
    task_type: str = "manual"
    overall_status: ResultStatus = ResultStatus.SUCCESS
    worker_results: List[WorkerResult] = Field(default_factory=list)
    synthesised_response: Optional[str] = None
    total_duration_ms: float = 0.0
    total_tokens: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_result(self, result: WorkerResult) -> None:
        """Append a worker result and update aggregates."""
        self.worker_results.append(result)
        self.total_duration_ms += result.duration_ms
        self.total_tokens += result.tokens_used
        # Overall status degrades if any worker fails
        if result.status == ResultStatus.FAILED:
            self.overall_status = ResultStatus.PARTIAL
        elif result.status == ResultStatus.TIMEOUT:
            if self.overall_status != ResultStatus.PARTIAL:
                self.overall_status = ResultStatus.PARTIAL

    @property
    def is_success(self) -> bool:
        return self.overall_status == ResultStatus.SUCCESS

    @property
    def worker_count(self) -> int:
        return len(self.worker_results)

    def get_outputs(self) -> List[Any]:
        """Extract non-None outputs from all workers."""
        return [r.output for r in self.worker_results if r.output is not None]


class TaskResultNormaliser:
    """Converts raw framework outputs into ``WorkerResult`` instances.

    Each normaliser method handles one framework's output format.
    """

    @staticmethod
    def from_maf_execution(
        task_id: str,
        execution_result: Any,
        duration_ms: float = 0.0,
    ) -> WorkerResult:
        """Normalise a MAF WorkflowExecutor result."""
        output = None
        status = ResultStatus.SUCCESS
        error = None
        tool_calls: List[Dict[str, Any]] = []

        if isinstance(execution_result, dict):
            output = execution_result.get("result") or execution_result.get("output")
            if execution_result.get("error"):
                status = ResultStatus.FAILED
                error = str(execution_result["error"])
            tool_calls = execution_result.get("tool_calls", [])
        elif hasattr(execution_result, "content"):
            output = execution_result.content
        else:
            output = str(execution_result) if execution_result else None

        return WorkerResult(
            worker_id=f"maf-{task_id[:8]}",
            worker_type=WorkerType.MAF_WORKFLOW,
            worker_name="MAF Workflow Engine",
            status=status,
            output=output,
            error=error,
            tool_calls=tool_calls,
            duration_ms=duration_ms,
        )

    @staticmethod
    def from_claude_response(
        task_id: str,
        response: Any,
        duration_ms: float = 0.0,
        tokens_used: int = 0,
    ) -> WorkerResult:
        """Normalise a Claude SDK worker response."""
        output = None
        status = ResultStatus.SUCCESS
        error = None
        tool_calls: List[Dict[str, Any]] = []

        if isinstance(response, dict):
            output = response.get("content") or response.get("result")
            if response.get("error"):
                status = ResultStatus.FAILED
                error = str(response["error"])
            tool_calls = response.get("tool_calls", [])
            tokens_used = response.get("tokens_used", tokens_used)
        elif isinstance(response, str):
            output = response
        elif hasattr(response, "content"):
            output = response.content
            if hasattr(response, "usage"):
                tokens_used = getattr(response.usage, "total_tokens", tokens_used)
        else:
            output = str(response) if response else None

        return WorkerResult(
            worker_id=f"claude-{task_id[:8]}",
            worker_type=WorkerType.CLAUDE_WORKER,
            worker_name="Claude Worker",
            status=status,
            output=output,
            error=error,
            tool_calls=tool_calls,
            tokens_used=tokens_used,
            duration_ms=duration_ms,
        )

    @staticmethod
    def from_swarm_coordination(
        task_id: str,
        coordination_result: Any,
        duration_ms: float = 0.0,
    ) -> WorkerResult:
        """Normalise a Swarm coordination result."""
        output = None
        status = ResultStatus.SUCCESS
        error = None
        sub_results: List[Dict[str, Any]] = []

        if isinstance(coordination_result, dict):
            output = coordination_result.get("result") or coordination_result.get("summary")
            if coordination_result.get("error"):
                status = ResultStatus.FAILED
                error = str(coordination_result["error"])
            sub_results = coordination_result.get("worker_results", [])
            swarm_status = coordination_result.get("status", "")
            if swarm_status == "failed":
                status = ResultStatus.FAILED
        elif hasattr(coordination_result, "status"):
            output = getattr(coordination_result, "summary", str(coordination_result))
            cr_status = getattr(coordination_result, "status", None)
            if cr_status and str(cr_status).lower() == "failed":
                status = ResultStatus.FAILED
                error = getattr(coordination_result, "error", None)
        else:
            output = str(coordination_result) if coordination_result else None

        return WorkerResult(
            worker_id=f"swarm-{task_id[:8]}",
            worker_type=WorkerType.SWARM,
            worker_name="Swarm Coordination",
            status=status,
            output=output,
            error=error,
            tool_calls=sub_results,
            duration_ms=duration_ms,
        )
