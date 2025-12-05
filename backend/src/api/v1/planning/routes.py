# =============================================================================
# IPA Platform - Planning API Routes
# =============================================================================
# Sprint 10: S10-5 Planning API (5 points)
#
# REST API endpoints for:
# - Task decomposition (/decompose)
# - Dynamic planning (/plans)
# - Autonomous decision-making (/decisions)
# - Trial-and-error execution (/trial)
# =============================================================================

from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from src.domain.orchestration.planning import (
    TaskDecomposer,
    DynamicPlanner,
    AutonomousDecisionEngine,
    TrialAndErrorEngine,
    DecisionType,
    PlanStatus,
)
from .schemas import (
    DecomposeTaskRequest,
    DecompositionResponse,
    SubTaskResponse,
    RefineDecompositionRequest,
    CreatePlanRequest,
    PlanResponse,
    PlanStatusResponse,
    ApprovePlanRequest,
    ApproveAdjustmentRequest,
    DecisionRequest,
    DecisionResponse,
    DecisionOptionResponse,
    DecisionExplanationResponse,
    ApproveDecisionRequest,
    RejectDecisionRequest,
    TrialRequest,
    TrialResponse,
    InsightsListResponse,
    InsightResponse,
    RecommendationsListResponse,
    RecommendationResponse,
    TrialStatisticsResponse,
    SuccessResponse,
)

router = APIRouter(prefix="/planning", tags=["Planning"])

# =============================================================================
# Singleton instances (in production, use dependency injection)
# =============================================================================

_task_decomposer = TaskDecomposer()
_dynamic_planner = DynamicPlanner(task_decomposer=_task_decomposer)
_decision_engine = AutonomousDecisionEngine()
_trial_engine = TrialAndErrorEngine()

# Store for decomposition results (in production, use database)
_decomposition_cache: dict = {}


# =============================================================================
# Task Decomposition Endpoints
# =============================================================================


@router.post("/decompose", response_model=DecompositionResponse)
async def decompose_task(request: DecomposeTaskRequest):
    """
    Decompose a task into subtasks.

    Breaks down complex tasks into executable subtasks with
    dependency analysis and execution ordering.
    """
    try:
        result = await _task_decomposer.decompose(
            task_description=request.task_description,
            context=request.context,
            strategy=request.strategy
        )

        # Cache the result for potential refinement
        _decomposition_cache[str(result.task_id)] = result

        return DecompositionResponse(
            task_id=str(result.task_id),
            original_task=result.original_task,
            subtasks=[
                SubTaskResponse(
                    id=str(t.id),
                    name=t.name,
                    description=t.description,
                    priority=t.priority.value,
                    status=t.status.value,
                    dependencies=[str(d) for d in t.dependencies],
                    estimated_duration_minutes=t.estimated_duration_minutes,
                    assigned_agent_id=t.assigned_agent_id
                )
                for t in result.subtasks
            ],
            execution_order=[
                [str(tid) for tid in layer]
                for layer in result.execution_order
            ],
            estimated_total_duration=result.estimated_total_duration,
            confidence_score=result.confidence_score,
            strategy=result.decomposition_strategy
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/decompose/{task_id}/refine", response_model=DecompositionResponse)
async def refine_decomposition(
    task_id: str,
    request: RefineDecompositionRequest
):
    """Refine a decomposition based on feedback."""
    original = _decomposition_cache.get(task_id)
    if not original:
        raise HTTPException(status_code=404, detail="Decomposition not found")

    try:
        result = await _task_decomposer.refine_decomposition(
            result=original,
            feedback=request.feedback
        )

        # Update cache
        _decomposition_cache[task_id] = result

        return DecompositionResponse(
            task_id=str(result.task_id),
            original_task=result.original_task,
            subtasks=[
                SubTaskResponse(
                    id=str(t.id),
                    name=t.name,
                    description=t.description,
                    priority=t.priority.value,
                    status=t.status.value,
                    dependencies=[str(d) for d in t.dependencies],
                    estimated_duration_minutes=t.estimated_duration_minutes,
                    assigned_agent_id=t.assigned_agent_id
                )
                for t in result.subtasks
            ],
            execution_order=[
                [str(tid) for tid in layer]
                for layer in result.execution_order
            ],
            estimated_total_duration=result.estimated_total_duration,
            confidence_score=result.confidence_score,
            strategy=result.decomposition_strategy
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Dynamic Planning Endpoints
# =============================================================================


@router.post("/plans", response_model=PlanResponse)
async def create_plan(request: CreatePlanRequest):
    """Create an execution plan for a goal."""
    try:
        plan = await _dynamic_planner.create_plan(
            goal=request.goal,
            context=request.context,
            deadline=request.deadline,
            strategy=request.strategy
        )

        return PlanResponse(
            id=str(plan.id),
            name=plan.name,
            goal=plan.goal,
            status=plan.status.value,
            progress=plan.progress_percentage,
            current_phase=plan.current_phase,
            total_phases=len(plan.decomposition.execution_order),
            subtasks_count=len(plan.decomposition.subtasks),
            created_at=plan.created_at,
            started_at=plan.started_at,
            completed_at=plan.completed_at,
            deadline=plan.deadline
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/plans/{plan_id}", response_model=PlanStatusResponse)
async def get_plan(plan_id: str):
    """Get plan details."""
    try:
        plan_uuid = UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan ID")

    status = _dynamic_planner.get_plan_status(plan_uuid)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])

    return PlanStatusResponse(**status)


@router.get("/plans/{plan_id}/status")
async def get_plan_execution_status(plan_id: str):
    """Get plan execution status."""
    try:
        plan_uuid = UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan ID")

    status = _dynamic_planner.get_plan_status(plan_uuid)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])

    return status


@router.post("/plans/{plan_id}/approve", response_model=SuccessResponse)
async def approve_plan(plan_id: str, request: ApprovePlanRequest):
    """Approve a plan for execution."""
    try:
        plan_uuid = UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan ID")

    try:
        await _dynamic_planner.approve_plan(plan_uuid, request.approver)
        return SuccessResponse(message=f"Plan {plan_id} approved")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/plans/{plan_id}/execute")
async def execute_plan(
    plan_id: str,
    background_tasks: BackgroundTasks
):
    """
    Start executing a plan.

    Runs in background and returns immediately.
    """
    try:
        plan_uuid = UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan ID")

    async def execution_callback(subtask):
        """Mock execution callback - in production, route to actual executors."""
        import asyncio
        await asyncio.sleep(0.1)  # Simulate execution
        return {"executed": subtask.name, "status": "success"}

    # Start execution in background
    background_tasks.add_task(
        _dynamic_planner.execute_plan,
        plan_uuid,
        execution_callback
    )

    return {
        "status": "started",
        "plan_id": plan_id,
        "message": "Plan execution started in background"
    }


@router.post("/plans/{plan_id}/pause", response_model=SuccessResponse)
async def pause_plan(plan_id: str):
    """Pause plan execution."""
    try:
        plan_uuid = UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan ID")

    try:
        await _dynamic_planner.pause_plan(plan_uuid)
        return SuccessResponse(message=f"Plan {plan_id} paused")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/plans/{plan_id}/adjustments/approve", response_model=SuccessResponse)
async def approve_adjustment(plan_id: str, request: ApproveAdjustmentRequest):
    """Approve a plan adjustment."""
    try:
        plan_uuid = UUID(plan_id)
        adjustment_uuid = UUID(request.adjustment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    try:
        await _dynamic_planner.approve_adjustment(
            plan_uuid, adjustment_uuid, request.approver
        )
        return SuccessResponse(message="Adjustment approved")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/plans")
async def list_plans(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100)
):
    """List all plans."""
    plan_status = None
    if status:
        try:
            plan_status = PlanStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Valid values: {[s.value for s in PlanStatus]}"
            )

    plans = _dynamic_planner.list_plans(status=plan_status, limit=limit)
    return {"plans": plans, "count": len(plans)}


@router.delete("/plans/{plan_id}", response_model=SuccessResponse)
async def delete_plan(plan_id: str):
    """Delete a plan."""
    try:
        plan_uuid = UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan ID")

    if _dynamic_planner.delete_plan(plan_uuid):
        return SuccessResponse(message=f"Plan {plan_id} deleted")
    else:
        raise HTTPException(status_code=404, detail="Plan not found")


# =============================================================================
# Decision Endpoints
# =============================================================================


@router.post("/decisions", response_model=DecisionResponse)
async def make_decision(request: DecisionRequest):
    """
    Request a decision.

    Evaluates options and makes an intelligent decision based on
    situation analysis and risk assessment.
    """
    try:
        decision_type = DecisionType(request.decision_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid decision type. Valid values: {[t.value for t in DecisionType]}"
        )

    try:
        result = await _decision_engine.make_decision(
            situation=request.situation,
            options=request.options,
            context=request.context,
            decision_type=decision_type
        )

        return DecisionResponse(
            decision_id=result["decision_id"],
            action=result["action"],
            confidence=result["confidence"],
            reasoning=result["reasoning"],
            risk_level=result["risk_level"],
            requires_approval=result["requires_approval"],
            options=[
                DecisionOptionResponse(
                    id=opt["id"],
                    name=opt["name"],
                    score=opt["score"]
                )
                for opt in result["options"]
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/decisions/{decision_id}/explain", response_model=DecisionExplanationResponse)
async def explain_decision(decision_id: str):
    """Get detailed explanation of a decision."""
    try:
        decision_uuid = UUID(decision_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid decision ID")

    explanation = await _decision_engine.explain_decision(decision_uuid)

    if explanation == "Decision not found":
        raise HTTPException(status_code=404, detail="Decision not found")

    return DecisionExplanationResponse(
        decision_id=decision_id,
        explanation=explanation
    )


@router.post("/decisions/{decision_id}/approve", response_model=SuccessResponse)
async def approve_decision(decision_id: str, request: ApproveDecisionRequest):
    """Approve a decision that requires human approval."""
    try:
        decision_uuid = UUID(decision_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid decision ID")

    success = await _decision_engine.approve_decision(decision_uuid, request.approver)
    if not success:
        raise HTTPException(status_code=404, detail="Decision not found")

    return SuccessResponse(message="Decision approved")


@router.post("/decisions/{decision_id}/reject", response_model=SuccessResponse)
async def reject_decision(decision_id: str, request: RejectDecisionRequest):
    """Reject a decision."""
    try:
        decision_uuid = UUID(decision_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid decision ID")

    success = await _decision_engine.reject_decision(
        decision_uuid, request.approver, request.reason
    )
    if not success:
        raise HTTPException(status_code=404, detail="Decision not found")

    return SuccessResponse(message="Decision rejected")


@router.get("/decisions")
async def list_decisions(
    decision_type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(50, ge=1, le=100)
):
    """List decision history."""
    dt = None
    if decision_type:
        try:
            dt = DecisionType(decision_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid type. Valid values: {[t.value for t in DecisionType]}"
            )

    history = _decision_engine.get_decision_history(decision_type=dt, limit=limit)
    return {"decisions": history, "count": len(history)}


@router.get("/decisions/rules")
async def list_decision_rules():
    """List all registered decision rules."""
    rules = _decision_engine.list_rules()
    return {"rules": rules, "count": len(rules)}


# =============================================================================
# Trial and Error Endpoints
# =============================================================================


@router.post("/trial", response_model=TrialResponse)
async def execute_with_trial(request: TrialRequest):
    """
    Execute a task using trial-and-error mechanism.

    Automatically retries with parameter adjustment on failure.
    """
    try:
        task_uuid = UUID(request.task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID")

    async def dummy_execution(**kwargs):
        """Dummy execution for testing - replace with actual execution logic."""
        import random
        if random.random() < 0.3:  # 30% failure rate for testing
            raise Exception("Simulated random failure")
        return {"success": True, **kwargs}

    result = await _trial_engine.execute_with_retry(
        task_id=task_uuid,
        execution_fn=dummy_execution,
        initial_params=request.params,
        strategy=request.strategy
    )

    return TrialResponse(
        success=result["success"],
        result=result.get("result"),
        error=result.get("error"),
        attempts=result["attempts"],
        final_params=result.get("final_params", {}),
        final_strategy=result.get("final_strategy", request.strategy),
        trials=result.get("trials")
    )


@router.get("/trial/insights", response_model=InsightsListResponse)
async def get_learning_insights():
    """Get learning insights from trial history."""
    insights = await _trial_engine.learn_from_history()

    return InsightsListResponse(
        insights=[
            InsightResponse(
                id=str(i.id),
                type=i.learning_type.value,
                pattern=i.pattern,
                confidence=i.confidence,
                recommendation=i.recommendation,
                created_at=i.created_at.isoformat()
            )
            for i in insights
        ]
    )


@router.get("/trial/recommendations", response_model=RecommendationsListResponse)
async def get_recommendations(
    task_type: Optional[str] = Query(None, description="Filter by task type")
):
    """Get recommendations based on learning history."""
    recommendations = _trial_engine.get_recommendations(task_type=task_type)

    return RecommendationsListResponse(
        recommendations=[
            RecommendationResponse(
                id=rec["id"],
                type=rec["type"],
                pattern=rec["pattern"],
                recommendation=rec["recommendation"],
                confidence=rec["confidence"],
                created_at=rec["created_at"]
            )
            for rec in recommendations
        ]
    )


@router.get("/trial/statistics", response_model=TrialStatisticsResponse)
async def get_trial_statistics():
    """Get overall trial execution statistics."""
    stats = _trial_engine.get_statistics()
    return TrialStatisticsResponse(**stats)


@router.get("/trial/history")
async def get_trial_history(
    task_id: Optional[str] = Query(None, description="Filter by task ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=500)
):
    """Get trial execution history."""
    task_uuid = None
    if task_id:
        try:
            task_uuid = UUID(task_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid task ID")

    from src.domain.orchestration.planning import TrialStatus
    trial_status = None
    if status:
        try:
            trial_status = TrialStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Valid values: {[s.value for s in TrialStatus]}"
            )

    history = _trial_engine.get_trial_history(
        task_id=task_uuid,
        status=trial_status,
        limit=limit
    )
    return {"trials": history, "count": len(history)}


@router.delete("/trial/history")
async def clear_trial_history(
    task_id: Optional[str] = Query(None, description="Clear only for specific task")
):
    """Clear trial history."""
    task_uuid = None
    if task_id:
        try:
            task_uuid = UUID(task_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid task ID")

    _trial_engine.clear_history(task_id=task_uuid)
    return SuccessResponse(message="Trial history cleared")


# =============================================================================
# Health Check
# =============================================================================


@router.get("/health")
async def health_check():
    """Health check for planning module."""
    return {
        "status": "healthy",
        "module": "planning",
        "components": {
            "task_decomposer": "ready",
            "dynamic_planner": "ready",
            "decision_engine": "ready",
            "trial_engine": "ready"
        }
    }
