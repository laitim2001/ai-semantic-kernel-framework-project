# =============================================================================
# IPA Platform - MagenticBuilder Migration Layer
# =============================================================================
# Sprint 17: S17-3 Task/Progress Ledger 整合 (8 points)
#            S17-4 Human Intervention 系統 (8 points)
#
# This module provides migration utilities for transitioning from Phase 2
# DynamicPlanner to Agent Framework MagenticBuilder.
#
# Key Features:
# - Legacy DynamicPlanner type definitions
# - Conversion functions between legacy and new formats
# - MagenticManagerAdapter for DynamicPlanner compatibility
# - Human Intervention handlers for PLAN_REVIEW, TOOL_APPROVAL, STALL
#
# Reference: Phase 2 domain/orchestration/planning/dynamic_planner.py
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import UUID, uuid4
import asyncio
import logging

from .magentic import (
    MagenticStatus,
    HumanInterventionKind,
    HumanInterventionDecision,
    MessageRole,
    MagenticMessage,
    MagenticParticipant,
    MagenticContext,
    TaskLedger,
    ProgressLedger,
    ProgressLedgerItem,
    HumanInterventionRequest,
    HumanInterventionReply,
    MagenticResult,
    MagenticManagerBase,
    MagenticBuilderAdapter,
    MAGENTIC_MANAGER_NAME,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Legacy Enums (Phase 2 Compatibility)
# =============================================================================


class DynamicPlannerStateLegacy(str, Enum):
    """Legacy DynamicPlanner states from Phase 2."""

    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    EVALUATING = "evaluating"
    REPLANNING = "replanning"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


class PlannerActionTypeLegacy(str, Enum):
    """Legacy planner action types from Phase 2."""

    ANALYZE = "analyze"
    PLAN = "plan"
    EXECUTE = "execute"
    EVALUATE = "evaluate"
    REPLAN = "replan"
    COMPLETE = "complete"
    FAIL = "fail"


# =============================================================================
# Legacy Data Classes (Phase 2 Compatibility)
# =============================================================================


@dataclass
class PlanStepLegacy:
    """Legacy plan step from Phase 2 DynamicPlanner."""

    step_id: str
    description: str
    agent_name: str
    status: str = "pending"  # pending, in_progress, completed, failed
    dependencies: List[str] = field(default_factory=list)
    result: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_id": self.step_id,
            "description": self.description,
            "agent_name": self.agent_name,
            "status": self.status,
            "dependencies": self.dependencies,
            "result": self.result,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlanStepLegacy":
        """Create from dictionary."""
        return cls(
            step_id=data.get("step_id", str(uuid4())),
            description=data.get("description", ""),
            agent_name=data.get("agent_name", ""),
            status=data.get("status", "pending"),
            dependencies=data.get("dependencies", []),
            result=data.get("result"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class DynamicPlanLegacy:
    """Legacy dynamic plan from Phase 2."""

    plan_id: str
    task_description: str
    steps: List[PlanStepLegacy]
    facts: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = self.created_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "plan_id": self.plan_id,
            "task_description": self.task_description,
            "steps": [s.to_dict() for s in self.steps],
            "facts": self.facts,
            "assumptions": self.assumptions,
            "constraints": self.constraints,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "version": self.version,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DynamicPlanLegacy":
        """Create from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)

        return cls(
            plan_id=data.get("plan_id", str(uuid4())),
            task_description=data.get("task_description", ""),
            steps=[PlanStepLegacy.from_dict(s) for s in data.get("steps", [])],
            facts=data.get("facts", []),
            assumptions=data.get("assumptions", []),
            constraints=data.get("constraints", []),
            created_at=created_at,
            updated_at=updated_at,
            version=data.get("version", 1),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ProgressEvaluationLegacy:
    """Legacy progress evaluation from Phase 2."""

    is_complete: bool = False
    is_stalled: bool = False
    progress_percentage: float = 0.0
    completed_steps: List[str] = field(default_factory=list)
    pending_steps: List[str] = field(default_factory=list)
    blocked_steps: List[str] = field(default_factory=list)
    next_step: Optional[str] = None
    stall_reason: Optional[str] = None
    recommendation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_complete": self.is_complete,
            "is_stalled": self.is_stalled,
            "progress_percentage": self.progress_percentage,
            "completed_steps": self.completed_steps,
            "pending_steps": self.pending_steps,
            "blocked_steps": self.blocked_steps,
            "next_step": self.next_step,
            "stall_reason": self.stall_reason,
            "recommendation": self.recommendation,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProgressEvaluationLegacy":
        """Create from dictionary."""
        return cls(
            is_complete=data.get("is_complete", False),
            is_stalled=data.get("is_stalled", False),
            progress_percentage=data.get("progress_percentage", 0.0),
            completed_steps=data.get("completed_steps", []),
            pending_steps=data.get("pending_steps", []),
            blocked_steps=data.get("blocked_steps", []),
            next_step=data.get("next_step"),
            stall_reason=data.get("stall_reason"),
            recommendation=data.get("recommendation"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class DynamicPlannerContextLegacy:
    """Legacy DynamicPlanner context from Phase 2."""

    task: str
    agents: Dict[str, str]  # name -> description
    current_plan: Optional[DynamicPlanLegacy] = None
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    iteration_count: int = 0
    max_iterations: int = 20
    stall_count: int = 0
    max_stall_count: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task": self.task,
            "agents": self.agents,
            "current_plan": self.current_plan.to_dict() if self.current_plan else None,
            "conversation_history": self.conversation_history,
            "iteration_count": self.iteration_count,
            "max_iterations": self.max_iterations,
            "stall_count": self.stall_count,
            "max_stall_count": self.max_stall_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DynamicPlannerContextLegacy":
        """Create from dictionary."""
        plan_data = data.get("current_plan")
        return cls(
            task=data.get("task", ""),
            agents=data.get("agents", {}),
            current_plan=DynamicPlanLegacy.from_dict(plan_data) if plan_data else None,
            conversation_history=data.get("conversation_history", []),
            iteration_count=data.get("iteration_count", 0),
            max_iterations=data.get("max_iterations", 20),
            stall_count=data.get("stall_count", 0),
            max_stall_count=data.get("max_stall_count", 3),
            metadata=data.get("metadata", {}),
        )


@dataclass
class DynamicPlannerResultLegacy:
    """Legacy DynamicPlanner result from Phase 2."""

    status: DynamicPlannerStateLegacy
    final_answer: Optional[str] = None
    plan: Optional[DynamicPlanLegacy] = None
    progress: Optional[ProgressEvaluationLegacy] = None
    iterations: int = 0
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value if isinstance(self.status, DynamicPlannerStateLegacy) else self.status,
            "final_answer": self.final_answer,
            "plan": self.plan.to_dict() if self.plan else None,
            "progress": self.progress.to_dict() if self.progress else None,
            "iterations": self.iterations,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


# =============================================================================
# Conversion Functions
# =============================================================================


def convert_legacy_state_to_magentic(state: DynamicPlannerStateLegacy) -> MagenticStatus:
    """Convert legacy DynamicPlanner state to MagenticStatus."""
    mapping = {
        DynamicPlannerStateLegacy.IDLE: MagenticStatus.IDLE,
        DynamicPlannerStateLegacy.PLANNING: MagenticStatus.PLANNING,
        DynamicPlannerStateLegacy.EXECUTING: MagenticStatus.EXECUTING,
        DynamicPlannerStateLegacy.EVALUATING: MagenticStatus.EXECUTING,
        DynamicPlannerStateLegacy.REPLANNING: MagenticStatus.REPLANNING,
        DynamicPlannerStateLegacy.WAITING: MagenticStatus.WAITING_APPROVAL,
        DynamicPlannerStateLegacy.COMPLETED: MagenticStatus.COMPLETED,
        DynamicPlannerStateLegacy.FAILED: MagenticStatus.FAILED,
    }
    return mapping.get(state, MagenticStatus.IDLE)


def convert_magentic_status_to_legacy(status: MagenticStatus) -> DynamicPlannerStateLegacy:
    """Convert MagenticStatus to legacy DynamicPlanner state."""
    mapping = {
        MagenticStatus.IDLE: DynamicPlannerStateLegacy.IDLE,
        MagenticStatus.PLANNING: DynamicPlannerStateLegacy.PLANNING,
        MagenticStatus.EXECUTING: DynamicPlannerStateLegacy.EXECUTING,
        MagenticStatus.WAITING_APPROVAL: DynamicPlannerStateLegacy.WAITING,
        MagenticStatus.STALLED: DynamicPlannerStateLegacy.WAITING,
        MagenticStatus.REPLANNING: DynamicPlannerStateLegacy.REPLANNING,
        MagenticStatus.COMPLETED: DynamicPlannerStateLegacy.COMPLETED,
        MagenticStatus.FAILED: DynamicPlannerStateLegacy.FAILED,
        MagenticStatus.CANCELLED: DynamicPlannerStateLegacy.FAILED,
    }
    return mapping.get(status, DynamicPlannerStateLegacy.IDLE)


def convert_legacy_context_to_magentic(
    legacy_context: DynamicPlannerContextLegacy,
) -> MagenticContext:
    """Convert legacy DynamicPlanner context to MagenticContext."""
    # Convert task to message
    task_message = MagenticMessage(
        role=MessageRole.USER,
        content=legacy_context.task,
    )

    # Convert conversation history
    chat_history: List[MagenticMessage] = []
    for msg in legacy_context.conversation_history:
        role = msg.get("role", "user")
        if isinstance(role, str):
            try:
                role = MessageRole(role)
            except ValueError:
                role = MessageRole.USER

        chat_history.append(MagenticMessage(
            role=role,
            content=msg.get("content", ""),
            author_name=msg.get("author_name"),
            timestamp=msg.get("timestamp"),
            metadata=msg.get("metadata", {}),
        ))

    return MagenticContext(
        task=task_message,
        chat_history=chat_history,
        participant_descriptions=legacy_context.agents,
        round_count=legacy_context.iteration_count,
        stall_count=legacy_context.stall_count,
    )


def convert_magentic_context_to_legacy(
    context: MagenticContext,
    max_iterations: int = 20,
    max_stall_count: int = 3,
) -> DynamicPlannerContextLegacy:
    """Convert MagenticContext to legacy DynamicPlanner context."""
    # Convert chat history
    conversation_history: List[Dict[str, Any]] = []
    for msg in context.chat_history:
        conversation_history.append({
            "role": msg.role.value if isinstance(msg.role, MessageRole) else msg.role,
            "content": msg.content,
            "author_name": msg.author_name,
            "timestamp": msg.timestamp,
            "metadata": msg.metadata,
        })

    return DynamicPlannerContextLegacy(
        task=context.task.content,
        agents=context.participant_descriptions,
        conversation_history=conversation_history,
        iteration_count=context.round_count,
        max_iterations=max_iterations,
        stall_count=context.stall_count,
        max_stall_count=max_stall_count,
    )


def convert_legacy_plan_to_task_ledger(plan: DynamicPlanLegacy) -> TaskLedger:
    """Convert legacy DynamicPlan to TaskLedger."""
    # Convert facts and assumptions to facts message
    facts_content = "FACTS:\n"
    facts_content += "\n".join(f"- {f}" for f in plan.facts)
    facts_content += "\n\nASSUMPTIONS:\n"
    facts_content += "\n".join(f"- {a}" for a in plan.assumptions)

    facts_message = MagenticMessage(
        role=MessageRole.ASSISTANT,
        content=facts_content,
        author_name=MAGENTIC_MANAGER_NAME,
    )

    # Convert steps to plan message
    plan_content = f"PLAN (v{plan.version}):\n"
    for i, step in enumerate(plan.steps, 1):
        status_icon = {"pending": "⏳", "in_progress": "🔄", "completed": "✅", "failed": "❌"}.get(step.status, "⏳")
        plan_content += f"{i}. [{status_icon}] {step.description} ({step.agent_name})\n"

    if plan.constraints:
        plan_content += "\nCONSTRAINTS:\n"
        plan_content += "\n".join(f"- {c}" for c in plan.constraints)

    plan_message = MagenticMessage(
        role=MessageRole.ASSISTANT,
        content=plan_content,
        author_name=MAGENTIC_MANAGER_NAME,
    )

    return TaskLedger(facts=facts_message, plan=plan_message)


def convert_task_ledger_to_legacy_plan(
    ledger: TaskLedger,
    task_description: str,
) -> DynamicPlanLegacy:
    """Convert TaskLedger to legacy DynamicPlan."""
    # Parse facts from ledger
    facts: List[str] = []
    assumptions: List[str] = []

    facts_text = ledger.facts.content
    in_facts = False
    in_assumptions = False

    for line in facts_text.split("\n"):
        line = line.strip()
        if "FACTS:" in line.upper():
            in_facts = True
            in_assumptions = False
            continue
        if "ASSUMPTIONS:" in line.upper():
            in_facts = False
            in_assumptions = True
            continue

        if line.startswith("-"):
            item = line[1:].strip()
            if in_facts:
                facts.append(item)
            elif in_assumptions:
                assumptions.append(item)

    # Parse plan steps (simplified)
    steps: List[PlanStepLegacy] = []
    plan_text = ledger.plan.content

    import re
    step_pattern = r"(\d+)\.\s*\[([^\]]*)\]\s*(.+?)\s*\(([^)]+)\)"
    for match in re.finditer(step_pattern, plan_text):
        step_num, status_icon, description, agent_name = match.groups()
        status = {
            "⏳": "pending",
            "🔄": "in_progress",
            "✅": "completed",
            "❌": "failed",
        }.get(status_icon.strip(), "pending")

        steps.append(PlanStepLegacy(
            step_id=f"step_{step_num}",
            description=description.strip(),
            agent_name=agent_name.strip(),
            status=status,
        ))

    return DynamicPlanLegacy(
        plan_id=str(uuid4()),
        task_description=task_description,
        steps=steps,
        facts=facts,
        assumptions=assumptions,
    )


def convert_legacy_progress_to_ledger(
    progress: ProgressEvaluationLegacy,
    participants: Dict[str, str],
) -> ProgressLedger:
    """Convert legacy ProgressEvaluation to ProgressLedger."""
    # Determine next speaker
    next_speaker = progress.next_step
    if not next_speaker or next_speaker not in participants:
        next_speaker = list(participants.keys())[0] if participants else "agent"

    # Create instruction
    instruction = progress.recommendation or "Please continue with the next step."

    return ProgressLedger(
        is_request_satisfied=ProgressLedgerItem(
            reason="Task completion check",
            answer=progress.is_complete,
        ),
        is_in_loop=ProgressLedgerItem(
            reason=progress.stall_reason or "No loop detected",
            answer=progress.is_stalled,
        ),
        is_progress_being_made=ProgressLedgerItem(
            reason=f"Progress: {progress.progress_percentage:.1f}%",
            answer=not progress.is_stalled,
        ),
        next_speaker=ProgressLedgerItem(
            reason="Based on pending steps",
            answer=next_speaker,
        ),
        instruction_or_question=ProgressLedgerItem(
            reason="Next action",
            answer=instruction,
        ),
    )


def convert_progress_ledger_to_legacy(ledger: ProgressLedger) -> ProgressEvaluationLegacy:
    """Convert ProgressLedger to legacy ProgressEvaluation."""
    return ProgressEvaluationLegacy(
        is_complete=ledger.is_complete,
        is_stalled=ledger.is_stalled,
        next_step=ledger.selected_speaker,
        stall_reason=ledger.is_in_loop.reason if ledger.is_stalled else None,
        recommendation=ledger.instruction,
    )


def convert_magentic_result_to_legacy(result: MagenticResult) -> DynamicPlannerResultLegacy:
    """Convert MagenticResult to legacy DynamicPlannerResult."""
    return DynamicPlannerResultLegacy(
        status=convert_magentic_status_to_legacy(result.status),
        final_answer=result.final_answer.content if result.final_answer else None,
        iterations=result.total_rounds,
        duration_seconds=result.duration_seconds,
        error_message=result.termination_reason if result.status == MagenticStatus.FAILED else None,
        metadata=result.metadata,
    )


# =============================================================================
# Human Intervention Handler
# =============================================================================


class HumanInterventionHandler:
    """
    Handler for human intervention in Magentic workflows.

    Provides callbacks and state management for:
    - Plan review (PLAN_REVIEW)
    - Tool approval (TOOL_APPROVAL)
    - Stall intervention (STALL)
    """

    def __init__(
        self,
        on_plan_review: Optional[Callable[[HumanInterventionRequest], HumanInterventionReply]] = None,
        on_tool_approval: Optional[Callable[[HumanInterventionRequest], HumanInterventionReply]] = None,
        on_stall: Optional[Callable[[HumanInterventionRequest], HumanInterventionReply]] = None,
        auto_approve_plan: bool = False,
        auto_approve_tools: bool = True,
        auto_replan_on_stall: bool = True,
    ):
        """
        Initialize the handler.

        Args:
            on_plan_review: Callback for plan review requests
            on_tool_approval: Callback for tool approval requests
            on_stall: Callback for stall intervention requests
            auto_approve_plan: Auto-approve plans if no callback
            auto_approve_tools: Auto-approve tools if no callback
            auto_replan_on_stall: Auto-replan on stall if no callback
        """
        self._on_plan_review = on_plan_review
        self._on_tool_approval = on_tool_approval
        self._on_stall = on_stall

        self._auto_approve_plan = auto_approve_plan
        self._auto_approve_tools = auto_approve_tools
        self._auto_replan_on_stall = auto_replan_on_stall

        # Pending requests
        self._pending_requests: Dict[str, HumanInterventionRequest] = {}

    def handle_request(
        self,
        request: HumanInterventionRequest,
    ) -> HumanInterventionReply:
        """
        Handle a human intervention request.

        Args:
            request: The intervention request

        Returns:
            Reply with the decision
        """
        self._pending_requests[request.request_id] = request

        if request.kind == HumanInterventionKind.PLAN_REVIEW:
            return self._handle_plan_review(request)
        elif request.kind == HumanInterventionKind.TOOL_APPROVAL:
            return self._handle_tool_approval(request)
        elif request.kind == HumanInterventionKind.STALL:
            return self._handle_stall(request)
        else:
            return HumanInterventionReply(
                decision=HumanInterventionDecision.APPROVE,
            )

    def _handle_plan_review(
        self,
        request: HumanInterventionRequest,
    ) -> HumanInterventionReply:
        """Handle plan review request."""
        if self._on_plan_review:
            return self._on_plan_review(request)

        if self._auto_approve_plan:
            return HumanInterventionReply(
                decision=HumanInterventionDecision.APPROVE,
            )

        # Default: Return approval with no edits
        return HumanInterventionReply(
            decision=HumanInterventionDecision.APPROVE,
            comments="Auto-approved by handler",
        )

    def _handle_tool_approval(
        self,
        request: HumanInterventionRequest,
    ) -> HumanInterventionReply:
        """Handle tool approval request."""
        if self._on_tool_approval:
            return self._on_tool_approval(request)

        if self._auto_approve_tools:
            return HumanInterventionReply(
                decision=HumanInterventionDecision.APPROVE,
            )

        # Default: Reject
        return HumanInterventionReply(
            decision=HumanInterventionDecision.REJECT,
            comments="Tool approval required",
        )

    def _handle_stall(
        self,
        request: HumanInterventionRequest,
    ) -> HumanInterventionReply:
        """Handle stall intervention request."""
        if self._on_stall:
            return self._on_stall(request)

        if self._auto_replan_on_stall:
            return HumanInterventionReply(
                decision=HumanInterventionDecision.REPLAN,
                comments=f"Auto-replan after {request.stall_count} stalls",
            )

        # Default: Continue
        return HumanInterventionReply(
            decision=HumanInterventionDecision.CONTINUE,
            comments="Continuing despite stall",
        )

    def submit_reply(
        self,
        request_id: str,
        reply: HumanInterventionReply,
    ) -> bool:
        """
        Submit a reply to a pending request.

        Args:
            request_id: ID of the pending request
            reply: The reply to submit

        Returns:
            True if the request was found and reply submitted
        """
        if request_id in self._pending_requests:
            del self._pending_requests[request_id]
            return True
        return False

    def get_pending_requests(self) -> List[HumanInterventionRequest]:
        """Get all pending intervention requests."""
        return list(self._pending_requests.values())

    def clear_pending(self) -> None:
        """Clear all pending requests."""
        self._pending_requests.clear()


# =============================================================================
# Migration Manager Adapter
# =============================================================================


class MagenticManagerAdapter(MagenticManagerBase):
    """
    Adapter that wraps legacy DynamicPlanner planning logic.

    Allows existing Phase 2 DynamicPlanner implementations to work
    with the new MagenticBuilder system.
    """

    def __init__(
        self,
        legacy_plan_func: Optional[Callable] = None,
        legacy_evaluate_func: Optional[Callable] = None,
        legacy_replan_func: Optional[Callable] = None,
        legacy_finalize_func: Optional[Callable] = None,
        *,
        max_stall_count: int = 3,
        max_reset_count: Optional[int] = None,
        max_round_count: Optional[int] = None,
    ):
        """
        Initialize the adapter.

        Args:
            legacy_plan_func: Legacy planning function
            legacy_evaluate_func: Legacy progress evaluation function
            legacy_replan_func: Legacy replanning function
            legacy_finalize_func: Legacy finalization function
            max_stall_count: Maximum stalls before intervention
            max_reset_count: Maximum resets allowed
            max_round_count: Maximum rounds allowed
        """
        super().__init__(
            max_stall_count=max_stall_count,
            max_reset_count=max_reset_count,
            max_round_count=max_round_count,
        )

        self._legacy_plan_func = legacy_plan_func
        self._legacy_evaluate_func = legacy_evaluate_func
        self._legacy_replan_func = legacy_replan_func
        self._legacy_finalize_func = legacy_finalize_func

        self._legacy_plan: Optional[DynamicPlanLegacy] = None

    async def plan(self, context: MagenticContext) -> MagenticMessage:
        """Create a plan using legacy planning logic."""
        if self._legacy_plan_func:
            # Convert context to legacy format
            legacy_context = convert_magentic_context_to_legacy(
                context,
                max_iterations=self.max_round_count or 20,
                max_stall_count=self.max_stall_count,
            )

            # Call legacy function
            if asyncio.iscoroutinefunction(self._legacy_plan_func):
                legacy_plan = await self._legacy_plan_func(legacy_context)
            else:
                legacy_plan = self._legacy_plan_func(legacy_context)

            if isinstance(legacy_plan, DynamicPlanLegacy):
                self._legacy_plan = legacy_plan
                self.task_ledger = convert_legacy_plan_to_task_ledger(legacy_plan)

                return MagenticMessage(
                    role=MessageRole.ASSISTANT,
                    content=f"Plan created: {legacy_plan.task_description}\n\n{self.task_ledger.plan.content}",
                    author_name=MAGENTIC_MANAGER_NAME,
                )

        # Fallback: Create a simple plan
        task_text = context.task.content
        team_text = "\n".join(f"- {name}: {desc}" for name, desc in context.participant_descriptions.items())

        content = f"""Task Ledger:

TASK: {task_text}

TEAM:
{team_text}

PLAN:
1. Analyze the task requirements
2. Execute using available agents
3. Validate results
"""
        self.task_ledger = TaskLedger(
            facts=MagenticMessage(role=MessageRole.ASSISTANT, content="Facts pending analysis"),
            plan=MagenticMessage(role=MessageRole.ASSISTANT, content=content),
        )

        return MagenticMessage(
            role=MessageRole.ASSISTANT,
            content=content,
            author_name=MAGENTIC_MANAGER_NAME,
        )

    async def replan(self, context: MagenticContext) -> MagenticMessage:
        """Replan using legacy replanning logic."""
        if self._legacy_replan_func:
            legacy_context = convert_magentic_context_to_legacy(context)

            if asyncio.iscoroutinefunction(self._legacy_replan_func):
                legacy_plan = await self._legacy_replan_func(legacy_context)
            else:
                legacy_plan = self._legacy_replan_func(legacy_context)

            if isinstance(legacy_plan, DynamicPlanLegacy):
                self._legacy_plan = legacy_plan
                self.task_ledger = convert_legacy_plan_to_task_ledger(legacy_plan)

                return MagenticMessage(
                    role=MessageRole.ASSISTANT,
                    content=f"Replanned (v{legacy_plan.version}): {self.task_ledger.plan.content}",
                    author_name=MAGENTIC_MANAGER_NAME,
                )

        # Fallback
        return MagenticMessage(
            role=MessageRole.ASSISTANT,
            content=f"Replanned after reset #{context.reset_count}",
            author_name=MAGENTIC_MANAGER_NAME,
        )

    async def create_progress_ledger(self, context: MagenticContext) -> ProgressLedger:
        """Evaluate progress using legacy evaluation logic."""
        if self._legacy_evaluate_func:
            legacy_context = convert_magentic_context_to_legacy(context)

            if asyncio.iscoroutinefunction(self._legacy_evaluate_func):
                legacy_progress = await self._legacy_evaluate_func(legacy_context)
            else:
                legacy_progress = self._legacy_evaluate_func(legacy_context)

            if isinstance(legacy_progress, ProgressEvaluationLegacy):
                return convert_legacy_progress_to_ledger(
                    legacy_progress,
                    context.participant_descriptions,
                )

        # Fallback: Simple progress check
        default_speaker = list(context.participant_descriptions.keys())[0] if context.participant_descriptions else "agent"

        return ProgressLedger(
            is_request_satisfied=ProgressLedgerItem(
                reason=f"Round {context.round_count}",
                answer=context.round_count >= (self.max_round_count or 20),
            ),
            is_in_loop=ProgressLedgerItem(
                reason="Loop check",
                answer=False,
            ),
            is_progress_being_made=ProgressLedgerItem(
                reason="Progress check",
                answer=True,
            ),
            next_speaker=ProgressLedgerItem(
                reason="Sequential selection",
                answer=default_speaker,
            ),
            instruction_or_question=ProgressLedgerItem(
                reason="Continue task",
                answer="Please proceed with the task.",
            ),
        )

    async def prepare_final_answer(self, context: MagenticContext) -> MagenticMessage:
        """Prepare final answer using legacy finalization logic."""
        if self._legacy_finalize_func:
            legacy_context = convert_magentic_context_to_legacy(context)

            if asyncio.iscoroutinefunction(self._legacy_finalize_func):
                result = await self._legacy_finalize_func(legacy_context)
            else:
                result = self._legacy_finalize_func(legacy_context)

            if isinstance(result, str):
                return MagenticMessage(
                    role=MessageRole.ASSISTANT,
                    content=result,
                    author_name=MAGENTIC_MANAGER_NAME,
                )

        # Fallback: Summarize conversation
        summary = "Task completed.\n\nConversation summary:\n"
        for msg in context.chat_history[-5:]:
            summary += f"- [{msg.author_name or msg.role.value}]: {msg.content[:100]}...\n"

        return MagenticMessage(
            role=MessageRole.ASSISTANT,
            content=summary,
            author_name=MAGENTIC_MANAGER_NAME,
        )


# =============================================================================
# Factory Functions
# =============================================================================


def migrate_dynamic_planner(
    id: str,
    participants: Dict[str, Any],
    legacy_plan_func: Optional[Callable] = None,
    legacy_evaluate_func: Optional[Callable] = None,
    legacy_replan_func: Optional[Callable] = None,
    legacy_finalize_func: Optional[Callable] = None,
    max_round_count: int = 20,
    max_stall_count: int = 3,
    enable_plan_review: bool = False,
) -> MagenticBuilderAdapter:
    """
    Migrate a legacy DynamicPlanner to MagenticBuilder.

    Args:
        id: Workflow identifier
        participants: Participant definitions
        legacy_plan_func: Legacy planning function
        legacy_evaluate_func: Legacy evaluation function
        legacy_replan_func: Legacy replanning function
        legacy_finalize_func: Legacy finalization function
        max_round_count: Maximum execution rounds
        max_stall_count: Maximum stalls
        enable_plan_review: Enable plan review

    Returns:
        Configured MagenticBuilderAdapter
    """
    # Create adapter
    adapter = MagenticBuilderAdapter(id=id)

    # Add participants
    for name, participant in participants.items():
        if isinstance(participant, MagenticParticipant):
            adapter._participants[name] = participant
        elif isinstance(participant, dict):
            adapter._participants[name] = MagenticParticipant.from_dict(participant)
        else:
            adapter._participants[name] = MagenticParticipant(
                name=name,
                description=str(participant),
            )

    # Create migration manager
    manager = MagenticManagerAdapter(
        legacy_plan_func=legacy_plan_func,
        legacy_evaluate_func=legacy_evaluate_func,
        legacy_replan_func=legacy_replan_func,
        legacy_finalize_func=legacy_finalize_func,
        max_round_count=max_round_count,
        max_stall_count=max_stall_count,
    )

    adapter.with_manager(manager)

    if enable_plan_review:
        adapter.with_plan_review(enable=True)

    return adapter.build()


def create_intervention_handler(
    auto_approve_plan: bool = False,
    auto_approve_tools: bool = True,
    auto_replan_on_stall: bool = True,
) -> HumanInterventionHandler:
    """
    Create a human intervention handler with default settings.

    Args:
        auto_approve_plan: Auto-approve plans
        auto_approve_tools: Auto-approve tools
        auto_replan_on_stall: Auto-replan on stall

    Returns:
        Configured handler
    """
    return HumanInterventionHandler(
        auto_approve_plan=auto_approve_plan,
        auto_approve_tools=auto_approve_tools,
        auto_replan_on_stall=auto_replan_on_stall,
    )


# =============================================================================
# Exports
# =============================================================================


__all__ = [
    # Legacy Enums
    "DynamicPlannerStateLegacy",
    "PlannerActionTypeLegacy",
    # Legacy Data Classes
    "PlanStepLegacy",
    "DynamicPlanLegacy",
    "ProgressEvaluationLegacy",
    "DynamicPlannerContextLegacy",
    "DynamicPlannerResultLegacy",
    # Conversion Functions
    "convert_legacy_state_to_magentic",
    "convert_magentic_status_to_legacy",
    "convert_legacy_context_to_magentic",
    "convert_magentic_context_to_legacy",
    "convert_legacy_plan_to_task_ledger",
    "convert_task_ledger_to_legacy_plan",
    "convert_legacy_progress_to_ledger",
    "convert_progress_ledger_to_legacy",
    "convert_magentic_result_to_legacy",
    # Human Intervention
    "HumanInterventionHandler",
    # Migration Manager
    "MagenticManagerAdapter",
    # Factory Functions
    "migrate_dynamic_planner",
    "create_intervention_handler",
]
