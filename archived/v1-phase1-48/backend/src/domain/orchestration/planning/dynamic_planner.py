# =============================================================================
# IPA Platform - Dynamic Planner
# =============================================================================
# Sprint 10: S10-2 DynamicPlanner (8 points)
#
# Dynamic planning engine that creates, monitors, and adapts execution plans
# based on real-time feedback and changing conditions.
#
# Features:
# - Plan creation from task decompositions
# - Real-time progress monitoring
# - Automatic replanning on failures
# - Event-driven notification system
# - Human approval workflow for plan adjustments
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol
from uuid import UUID, uuid4
import asyncio

from .task_decomposer import (
    TaskDecomposer,
    DecompositionResult,
    SubTask,
    TaskStatus,
)


class PlanStatus(str, Enum):
    """Execution plan status."""
    DRAFT = "draft"
    APPROVED = "approved"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    REPLANNING = "replanning"


class PlanEvent(str, Enum):
    """Plan execution events."""
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    RESOURCE_UNAVAILABLE = "resource_unavailable"
    NEW_INFORMATION = "new_information"
    USER_INTERVENTION = "user_intervention"
    DEADLINE_APPROACHING = "deadline_approaching"
    PLAN_CREATED = "plan_created"
    PLAN_APPROVED = "plan_approved"
    PLAN_STARTED = "plan_started"
    PLAN_COMPLETED = "plan_completed"
    PLAN_FAILED = "plan_failed"
    REPLANNING_STARTED = "replanning_started"
    REPLANNING_COMPLETED = "replanning_completed"


class LLMServiceProtocol(Protocol):
    """Protocol for LLM service interface."""

    async def generate(self, prompt: str, max_tokens: int = 2000) -> str:
        """Generate text from a prompt."""
        ...


class DecisionEngineProtocol(Protocol):
    """Protocol for decision engine interface."""

    async def make_decision(
        self,
        situation: str,
        options: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a decision based on situation and options."""
        ...


@dataclass
class PlanAdjustment:
    """
    Represents an adjustment made to a plan.

    Tracks what triggered the adjustment, what changed, and approval status.
    """
    id: UUID
    plan_id: UUID
    trigger_event: PlanEvent
    original_state: Dict[str, Any]
    new_state: Dict[str, Any]
    reason: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    approved: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert adjustment to dictionary."""
        return {
            "id": str(self.id),
            "plan_id": str(self.plan_id),
            "trigger_event": self.trigger_event.value,
            "original_state": self.original_state,
            "new_state": self.new_state,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
            "approved": self.approved,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
        }

    def approve(self, approver: str) -> None:
        """Approve this adjustment."""
        self.approved = True
        self.approved_by = approver
        self.approved_at = datetime.utcnow()


@dataclass
class ExecutionPlan:
    """
    Represents an execution plan.

    Contains the decomposed tasks, current status, progress, and history
    of any adjustments made during execution.
    """
    id: UUID
    name: str
    description: str
    goal: str
    decomposition: DecompositionResult
    status: PlanStatus = PlanStatus.DRAFT
    current_phase: int = 0
    progress_percentage: float = 0.0
    adjustments: List[PlanAdjustment] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "goal": self.goal,
            "status": self.status.value,
            "current_phase": self.current_phase,
            "progress_percentage": self.progress_percentage,
            "total_phases": len(self.decomposition.execution_order),
            "subtasks_count": len(self.decomposition.subtasks),
            "adjustments_count": len(self.adjustments),
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "metadata": self.metadata,
        }

    def get_progress(self) -> Dict[str, Any]:
        """Get detailed progress information."""
        progress = self.decomposition.get_progress()
        return {
            **progress,
            "current_phase": self.current_phase,
            "total_phases": len(self.decomposition.execution_order),
            "status": self.status.value,
        }


class DynamicPlanner:
    """
    Dynamic Planning Engine.

    Responsible for:
    - Creating execution plans from goals
    - Monitoring execution progress
    - Dynamically adjusting plans based on conditions
    - Handling exceptions and replanning
    """

    def __init__(
        self,
        task_decomposer: Optional[TaskDecomposer] = None,
        decision_engine: Optional[DecisionEngineProtocol] = None,
        llm_service: Optional[LLMServiceProtocol] = None,
        require_approval_for_changes: bool = True,
        failure_threshold: float = 0.3,
        monitoring_interval_seconds: int = 60
    ):
        """
        Initialize the DynamicPlanner.

        Args:
            task_decomposer: TaskDecomposer for breaking down goals
            decision_engine: Decision engine for making adjustment decisions
            llm_service: LLM service for analysis
            require_approval_for_changes: Whether plan changes require approval
            failure_threshold: Failure rate threshold triggering replanning
            monitoring_interval_seconds: How often to check plan status
        """
        self.decomposer = task_decomposer or TaskDecomposer()
        self.decision_engine = decision_engine
        self.llm_service = llm_service
        self.require_approval = require_approval_for_changes
        self.failure_threshold = failure_threshold
        self.monitoring_interval = monitoring_interval_seconds

        # Plan storage
        self._plans: Dict[UUID, ExecutionPlan] = {}

        # Event handlers
        self._event_handlers: Dict[PlanEvent, List[Callable]] = {
            event: [] for event in PlanEvent
        }

        # Monitoring tasks
        self._monitoring_tasks: Dict[UUID, asyncio.Task] = {}

    async def create_plan(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        deadline: Optional[datetime] = None,
        strategy: str = "hybrid"
    ) -> ExecutionPlan:
        """
        Create an execution plan for a goal.

        Args:
            goal: Goal description
            context: Optional context information
            deadline: Optional deadline
            strategy: Decomposition strategy

        Returns:
            ExecutionPlan ready for approval and execution
        """
        # Decompose the goal into tasks
        decomposition = await self.decomposer.decompose(
            task_description=goal,
            context=context,
            strategy=strategy
        )

        plan = ExecutionPlan(
            id=uuid4(),
            name=f"Plan for: {goal[:50]}..." if len(goal) > 50 else f"Plan for: {goal}",
            description=goal,
            goal=goal,
            decomposition=decomposition,
            deadline=deadline,
            metadata={"context": context, "strategy": strategy}
        )

        self._plans[plan.id] = plan
        await self._emit_event(PlanEvent.PLAN_CREATED, plan, None)

        return plan

    async def approve_plan(self, plan_id: UUID, approver: str) -> None:
        """
        Approve a plan for execution.

        Args:
            plan_id: ID of the plan to approve
            approver: Name/ID of the approver
        """
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        if plan.status != PlanStatus.DRAFT:
            raise ValueError(f"Plan is not in draft state: {plan.status}")

        plan.status = PlanStatus.APPROVED
        plan.metadata["approved_by"] = approver
        plan.metadata["approved_at"] = datetime.utcnow().isoformat()

        await self._emit_event(PlanEvent.PLAN_APPROVED, plan, None)

    async def execute_plan(
        self,
        plan_id: UUID,
        execution_callback: Callable[[SubTask], Any]
    ) -> Dict[str, Any]:
        """
        Execute a plan.

        Args:
            plan_id: ID of the plan to execute
            execution_callback: Callback function to execute each subtask

        Returns:
            Execution results
        """
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        if plan.status not in [PlanStatus.APPROVED, PlanStatus.PAUSED]:
            raise ValueError(f"Plan is not in executable state: {plan.status}")

        plan.status = PlanStatus.EXECUTING
        plan.started_at = plan.started_at or datetime.utcnow()

        # Start monitoring
        self._start_monitoring(plan_id)

        await self._emit_event(PlanEvent.PLAN_STARTED, plan, None)

        results = []
        execution_order = plan.decomposition.execution_order

        try:
            for phase_index, phase_tasks in enumerate(execution_order):
                plan.current_phase = phase_index

                # Execute tasks in this phase in parallel
                phase_results = await self._execute_phase(
                    plan=plan,
                    task_ids=phase_tasks,
                    callback=execution_callback
                )
                results.extend(phase_results)

                # Update progress
                self._update_progress(plan)

                # Check if replanning is needed
                if await self._should_replan(plan, phase_results):
                    await self._replan(plan, phase_results)

            plan.status = PlanStatus.COMPLETED
            plan.completed_at = datetime.utcnow()
            await self._emit_event(PlanEvent.PLAN_COMPLETED, plan, None)

        except Exception as e:
            plan.status = PlanStatus.FAILED
            plan.metadata["failure_reason"] = str(e)
            await self._emit_event(PlanEvent.PLAN_FAILED, plan, None)
            raise

        finally:
            self._stop_monitoring(plan_id)

        return {
            "plan_id": str(plan_id),
            "status": plan.status.value,
            "results": results,
            "adjustments_made": len(plan.adjustments),
            "completed_at": plan.completed_at.isoformat() if plan.completed_at else None,
        }

    async def _execute_phase(
        self,
        plan: ExecutionPlan,
        task_ids: List[UUID],
        callback: Callable
    ) -> List[Dict[str, Any]]:
        """Execute a single phase of tasks."""
        task_index = {t.id: t for t in plan.decomposition.subtasks}

        async def execute_single_task(task_id: UUID) -> Dict[str, Any]:
            task = task_index.get(task_id)
            if not task:
                return {"task_id": str(task_id), "status": "not_found"}

            task.status = TaskStatus.IN_PROGRESS
            task.started_at = datetime.utcnow()

            await self._emit_event(PlanEvent.TASK_STARTED, plan, task)

            try:
                result = await callback(task)
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.utcnow()
                if task.started_at:
                    task.actual_duration_minutes = int(
                        (task.completed_at - task.started_at).total_seconds() / 60
                    )
                task.outputs = result if isinstance(result, dict) else {"result": result}

                await self._emit_event(PlanEvent.TASK_COMPLETED, plan, task)

                return {
                    "task_id": str(task_id),
                    "task_name": task.name,
                    "status": "completed",
                    "result": result
                }

            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error_message = str(e)
                task.completed_at = datetime.utcnow()

                await self._emit_event(PlanEvent.TASK_FAILED, plan, task)

                return {
                    "task_id": str(task_id),
                    "task_name": task.name,
                    "status": "failed",
                    "error": str(e)
                }

        # Execute all tasks in this phase in parallel
        tasks = [execute_single_task(tid) for tid in task_ids]
        return await asyncio.gather(*tasks)

    def _update_progress(self, plan: ExecutionPlan) -> None:
        """Update the plan's progress percentage."""
        progress = plan.decomposition.get_progress()
        plan.progress_percentage = progress["progress_percentage"]

    async def _should_replan(
        self,
        plan: ExecutionPlan,
        phase_results: List[Dict[str, Any]]
    ) -> bool:
        """Determine if replanning is needed."""
        if not phase_results:
            return False

        # Check failure rate
        failed_tasks = [r for r in phase_results if r["status"] == "failed"]
        if len(failed_tasks) / len(phase_results) > self.failure_threshold:
            return True

        # Check deadline
        if plan.deadline:
            remaining_tasks = sum(
                1 for t in plan.decomposition.subtasks
                if t.status in [TaskStatus.PENDING, TaskStatus.READY]
            )
            # Estimate remaining time (30 min per task as default)
            avg_duration = 30
            estimated_remaining = remaining_tasks * avg_duration

            if datetime.utcnow() + timedelta(minutes=estimated_remaining) > plan.deadline:
                await self._emit_event(PlanEvent.DEADLINE_APPROACHING, plan, None)
                return True

        return False

    async def _replan(
        self,
        plan: ExecutionPlan,
        recent_results: List[Dict[str, Any]]
    ) -> None:
        """Replan based on current situation."""
        plan.status = PlanStatus.REPLANNING
        await self._emit_event(PlanEvent.REPLANNING_STARTED, plan, None)

        # Analyze current situation
        analysis = await self._analyze_situation(plan, recent_results)

        # Determine best action
        if self.decision_engine:
            decision = await self.decision_engine.make_decision(
                situation=analysis.get("analysis", "Replanning needed"),
                options=[
                    "retry_failed_tasks",
                    "skip_failed_tasks",
                    "modify_remaining_tasks",
                    "abort_plan"
                ],
                context={"plan_id": str(plan.id), "results": recent_results}
            )
        else:
            # Default decision: retry if few failures, skip if many
            failed_count = analysis.get("failed_count", 0)
            decision = {
                "action": "retry_failed_tasks" if failed_count <= 2 else "skip_failed_tasks"
            }

        # Record adjustment
        adjustment = PlanAdjustment(
            id=uuid4(),
            plan_id=plan.id,
            trigger_event=PlanEvent.TASK_FAILED,
            original_state={"results": recent_results},
            new_state={"decision": decision},
            reason=analysis.get("reason", "Automatic replanning")
        )

        if self.require_approval:
            # Wait for approval before applying
            adjustment.approved = False
            plan.adjustments.append(adjustment)
            plan.status = PlanStatus.PAUSED
        else:
            adjustment.approved = True
            adjustment.approved_by = "system"
            adjustment.approved_at = datetime.utcnow()
            plan.adjustments.append(adjustment)
            await self._apply_adjustment(plan, decision)
            plan.status = PlanStatus.EXECUTING

        await self._emit_event(PlanEvent.REPLANNING_COMPLETED, plan, None)

    async def _analyze_situation(
        self,
        plan: ExecutionPlan,
        recent_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze current execution situation."""
        failed_tasks = [r for r in recent_results if r["status"] == "failed"]
        completed_tasks = [r for r in recent_results if r["status"] == "completed"]

        analysis = {
            "failed_count": len(failed_tasks),
            "completed_count": len(completed_tasks),
            "success_rate": len(completed_tasks) / len(recent_results) if recent_results else 0,
            "failed_errors": [r.get("error") for r in failed_tasks],
        }

        if self.llm_service:
            prompt = f"""
            Analyze the following execution situation and provide recommendations:

            Plan Goal: {plan.goal}
            Current Progress: {plan.progress_percentage:.1f}%
            Deadline: {plan.deadline}

            Recent Results:
            - Successful: {len(completed_tasks)} tasks
            - Failed: {len(failed_tasks)} tasks
            - Error Details: {[r.get('error') for r in failed_tasks]}

            Please analyze the situation and suggest the next action.
            """

            response = await self.llm_service.generate(
                prompt=prompt,
                max_tokens=500
            )
            analysis["analysis"] = response
            analysis["reason"] = "LLM situation analysis"
        else:
            analysis["analysis"] = f"Automatic analysis: {len(failed_tasks)} failures detected"
            analysis["reason"] = "Rule-based analysis"

        return analysis

    async def _apply_adjustment(
        self,
        plan: ExecutionPlan,
        decision: Dict[str, Any]
    ) -> None:
        """Apply a plan adjustment based on decision."""
        action = decision.get("action")

        if action == "retry_failed_tasks":
            # Reset failed tasks to ready
            for task in plan.decomposition.subtasks:
                if task.status == TaskStatus.FAILED:
                    task.status = TaskStatus.READY
                    task.error_message = None
                    task.started_at = None
                    task.completed_at = None

        elif action == "skip_failed_tasks":
            # Mark failed tasks as completed (skipped)
            for task in plan.decomposition.subtasks:
                if task.status == TaskStatus.FAILED:
                    task.status = TaskStatus.COMPLETED
                    task.metadata["skipped"] = True

        elif action == "modify_remaining_tasks":
            # Modify remaining pending tasks
            modifications = decision.get("modifications", {})
            for task in plan.decomposition.subtasks:
                if task.status == TaskStatus.PENDING:
                    if str(task.id) in modifications:
                        task.description = modifications[str(task.id)]

        elif action == "abort_plan":
            plan.status = PlanStatus.FAILED
            plan.metadata["aborted"] = True
            plan.metadata["abort_reason"] = decision.get("reason", "Manual abort")

    def _start_monitoring(self, plan_id: UUID) -> None:
        """Start monitoring a plan's execution."""
        async def monitor():
            while True:
                await asyncio.sleep(self.monitoring_interval)
                plan = self._plans.get(plan_id)
                if not plan or plan.status != PlanStatus.EXECUTING:
                    break

                # Check for deadline issues
                if plan.deadline and datetime.utcnow() > plan.deadline:
                    await self._emit_event(PlanEvent.DEADLINE_APPROACHING, plan, None)

        self._monitoring_tasks[plan_id] = asyncio.create_task(monitor())

    def _stop_monitoring(self, plan_id: UUID) -> None:
        """Stop monitoring a plan."""
        task = self._monitoring_tasks.pop(plan_id, None)
        if task:
            task.cancel()

    async def _emit_event(
        self,
        event: PlanEvent,
        plan: ExecutionPlan,
        task: Optional[SubTask]
    ) -> None:
        """Emit a plan event to registered handlers."""
        for handler in self._event_handlers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(plan, task)
                else:
                    handler(plan, task)
            except Exception:
                pass  # Don't let handler errors stop execution

    def on_event(
        self,
        event: PlanEvent,
        handler: Callable[[ExecutionPlan, Optional[SubTask]], Any]
    ) -> None:
        """
        Register an event handler.

        Args:
            event: Event type to listen for
            handler: Handler function (can be sync or async)
        """
        self._event_handlers[event].append(handler)

    def off_event(
        self,
        event: PlanEvent,
        handler: Callable
    ) -> None:
        """Remove an event handler."""
        handlers = self._event_handlers.get(event, [])
        if handler in handlers:
            handlers.remove(handler)

    async def pause_plan(self, plan_id: UUID) -> None:
        """Pause a plan's execution."""
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        if plan.status == PlanStatus.EXECUTING:
            plan.status = PlanStatus.PAUSED
            self._stop_monitoring(plan_id)

    async def resume_plan(
        self,
        plan_id: UUID,
        execution_callback: Callable[[SubTask], Any]
    ) -> Dict[str, Any]:
        """Resume a paused plan."""
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        if plan.status != PlanStatus.PAUSED:
            raise ValueError(f"Plan is not paused: {plan.status}")

        return await self.execute_plan(plan_id, execution_callback)

    async def approve_adjustment(
        self,
        plan_id: UUID,
        adjustment_id: UUID,
        approver: str
    ) -> None:
        """Approve a pending plan adjustment."""
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        adjustment = next(
            (a for a in plan.adjustments if a.id == adjustment_id),
            None
        )
        if not adjustment:
            raise ValueError(f"Adjustment {adjustment_id} not found")

        adjustment.approve(approver)

        # Apply the adjustment
        await self._apply_adjustment(plan, adjustment.new_state.get("decision", {}))

    def get_plan(self, plan_id: UUID) -> Optional[ExecutionPlan]:
        """Get a plan by ID."""
        return self._plans.get(plan_id)

    def get_plan_status(self, plan_id: UUID) -> Dict[str, Any]:
        """Get detailed plan status."""
        plan = self._plans.get(plan_id)
        if not plan:
            return {"error": "Plan not found"}

        return {
            "id": str(plan.id),
            "name": plan.name,
            "status": plan.status.value,
            "progress": plan.progress_percentage,
            "current_phase": plan.current_phase,
            "total_phases": len(plan.decomposition.execution_order),
            "adjustments": len(plan.adjustments),
            "subtasks": [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "status": t.status.value,
                    "priority": t.priority.value,
                }
                for t in plan.decomposition.subtasks
            ]
        }

    def list_plans(
        self,
        status: Optional[PlanStatus] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List plans, optionally filtered by status."""
        plans = list(self._plans.values())

        if status:
            plans = [p for p in plans if p.status == status]

        # Sort by created_at descending
        plans.sort(key=lambda p: p.created_at, reverse=True)

        return [p.to_dict() for p in plans[:limit]]

    def delete_plan(self, plan_id: UUID) -> bool:
        """Delete a plan."""
        if plan_id in self._plans:
            self._stop_monitoring(plan_id)
            del self._plans[plan_id]
            return True
        return False
