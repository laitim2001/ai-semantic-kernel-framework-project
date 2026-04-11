"""
PipelineContext — Carries state across all 8 pipeline steps.

Each step reads prior outputs from context and writes its own output.
The context is serializable for checkpoint persistence and SSE streaming.

Phase 45: Orchestration Core
"""

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class PipelineContext:
    """Unified context object flowing through the 8-step orchestration pipeline.

    Identity fields are required at construction. Step output fields are
    populated progressively as the pipeline advances.

    Attributes:
        user_id: Authenticated user identifier.
        session_id: Chat session identifier.
        task: The user's original input / request text.
        request_id: Unique ID for this pipeline invocation (auto-generated).

        memory_text: Token-budgeted memory text from Step 1.
        knowledge_text: Knowledge base search results from Step 2.
        routing_decision: V8 RoutingDecision from Step 3.
        completeness_info: V8 CompletenessInfo from Step 3.
        dialog_questions: Guided dialog questions if incomplete (Step 3).
        dialog_id: Dialog session ID if in guided dialog mode.
        risk_assessment: V8 RiskAssessment from Step 4.
        hitl_approval_id: Approval request ID if HITL triggered (Step 5).
        selected_route: LLM-chosen route from Step 6.
        route_reasoning: LLM reasoning for route selection.
        dispatch_result: Execution result from Step 7.

        paused_at: Pipeline pause reason ("hitl" | "dialog" | None).
        checkpoint_id: Latest checkpoint ID (for resume).
        completed_steps: Names of completed steps in order.
        step_latencies: Step name → execution time in ms.
        total_start_time: Pipeline start timestamp (epoch).
        created_at: Pipeline creation datetime.
    """

    # --- Identity (required) ---
    user_id: str
    session_id: str
    task: str
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # --- Step 1: Memory ---
    memory_text: str = ""
    memory_metadata: Dict[str, Any] = field(default_factory=dict)

    # --- Step 2: Knowledge ---
    knowledge_text: str = ""
    knowledge_metadata: Dict[str, Any] = field(default_factory=dict)

    # --- Step 3: Intent + Completeness ---
    routing_decision: Optional[Any] = None  # orchestration.intent_router.models.RoutingDecision
    completeness_info: Optional[Any] = None  # orchestration.intent_router.models.CompletenessInfo
    dialog_questions: Optional[List[str]] = None
    dialog_id: Optional[str] = None

    # --- Step 4: Risk Assessment ---
    risk_assessment: Optional[Any] = None  # orchestration.risk_assessor.assessor.RiskAssessment

    # --- Step 5: HITL Gate ---
    hitl_approval_id: Optional[str] = None

    # --- Step 6: LLM Route Decision ---
    selected_route: Optional[str] = None  # "direct_answer" | "subagent" | "team" | "swarm" | "workflow"
    route_reasoning: Optional[str] = None

    # --- Step 7: Dispatch ---
    dispatch_result: Optional[Any] = None  # dispatch.models.DispatchResult

    # --- Pipeline Control ---
    paused_at: Optional[str] = None  # "hitl" | "dialog" | None
    checkpoint_id: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    step_latencies: Dict[str, float] = field(default_factory=dict)
    total_start_time: float = field(default_factory=time.time)
    created_at: datetime = field(default_factory=datetime.utcnow)

    # --- Extensible metadata ---
    metadata: Dict[str, Any] = field(default_factory=dict)

    def mark_step_complete(self, step_name: str, latency_ms: float) -> None:
        """Record a step as completed with its latency."""
        self.completed_steps.append(step_name)
        self.step_latencies[step_name] = latency_ms

    @property
    def elapsed_ms(self) -> float:
        """Total elapsed time since pipeline start in milliseconds."""
        return (time.time() - self.total_start_time) * 1000

    @property
    def is_paused(self) -> bool:
        """Whether the pipeline is currently paused."""
        return self.paused_at is not None

    @property
    def current_step_index(self) -> int:
        """Number of completed steps (0-based index of next step)."""
        return len(self.completed_steps)

    def to_checkpoint_state(self) -> Dict[str, Any]:
        """Serialize pipeline state for checkpoint persistence.

        Returns a dict suitable for WorkflowCheckpoint.state.
        Complex objects (RoutingDecision, RiskAssessment) are converted
        via their to_dict() methods if available.
        """
        state: Dict[str, Any] = {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "task": self.task,
            "memory_text": self.memory_text[:500],
            "knowledge_text": self.knowledge_text[:500],
            "selected_route": self.selected_route,
            "route_reasoning": self.route_reasoning,
            "paused_at": self.paused_at,
            "checkpoint_id": self.checkpoint_id,
            "completed_steps": self.completed_steps,
            "step_latencies": self.step_latencies,
        }

        if self.routing_decision is not None:
            state["routing_decision"] = (
                self.routing_decision.to_dict()
                if hasattr(self.routing_decision, "to_dict")
                else str(self.routing_decision)
            )

        if self.risk_assessment is not None:
            state["risk_assessment"] = (
                self.risk_assessment.to_dict()
                if hasattr(self.risk_assessment, "to_dict")
                else str(self.risk_assessment)
            )

        return state

    def to_sse_summary(self) -> Dict[str, Any]:
        """Compact summary for SSE event streaming to frontend."""
        return {
            "request_id": self.request_id,
            "session_id": self.session_id,
            "completed_steps": self.completed_steps,
            "current_step_index": self.current_step_index,
            "paused_at": self.paused_at,
            "selected_route": self.selected_route,
            "elapsed_ms": round(self.elapsed_ms, 1),
        }
