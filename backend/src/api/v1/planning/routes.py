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

# Sprint 31: 使用 PlanningAdapter 替代直接 domain 導入
from src.integrations.agent_framework.builders.planning import (
    PlanningAdapter,
    PlanningConfig,
    PlanningMode,
    DecisionType,
    TrialStatus,
    DomainPlanStatus as PlanStatus,  # 重命名以保持 API 兼容
    DecompositionResult,
    SubTask,
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
# Singleton PlanningAdapter (Sprint 31: 統一使用適配器)
# =============================================================================

# 創建完整模式的 PlanningAdapter，包含所有 Phase 2 擴展功能
_planning_adapter = PlanningAdapter(
    id="global-planning-adapter",
    config=PlanningConfig(
        max_subtasks=20,
        max_depth=3,
        timeout_seconds=300.0,
    ),
)
# 啟用所有擴展功能
_planning_adapter.with_task_decomposition()
_planning_adapter.with_decision_engine()
_planning_adapter.with_trial_error()
_planning_adapter.with_dynamic_planner()


# =============================================================================
# Task Decomposition Endpoints
# =============================================================================


@router.post("/decompose", response_model=DecompositionResponse)
async def decompose_task(request: DecomposeTaskRequest):
    """
    Decompose a task into subtasks.

    Breaks down complex tasks into executable subtasks with
    dependency analysis and execution ordering.

    Sprint 31: 使用 PlanningAdapter.decompose_task() 替代直接 domain 調用
    """
    try:
        # Sprint 31: 使用適配器方法
        result = await _planning_adapter.decompose_task(
            task_description=request.task_description,
            context=request.context,
            strategy=request.strategy
        )

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
    """Refine a decomposition based on feedback.

    Sprint 31: 使用 PlanningAdapter.refine_decomposition() 替代直接 domain 調用
    """
    try:
        # Sprint 31: 使用適配器方法 (緩存由適配器管理)
        result = await _planning_adapter.refine_decomposition(
            task_id=task_id,
            feedback=request.feedback
        )

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
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Dynamic Planning Endpoints
# =============================================================================


@router.post("/plans", response_model=PlanResponse)
async def create_plan(request: CreatePlanRequest):
    """Create an execution plan for a goal.

    Sprint 31: 使用 PlanningAdapter.create_plan() 替代直接 domain 調用
    """
    try:
        # Sprint 31: 使用適配器方法
        plan = await _planning_adapter.create_plan(
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
    """Get plan details.

    Sprint 31: 使用 PlanningAdapter.get_plan_status() 替代直接 domain 調用
    """
    try:
        plan_uuid = UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan ID")

    # Sprint 31: 使用適配器方法
    status = _planning_adapter.get_plan_status(plan_uuid)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])

    return PlanStatusResponse(**status)


@router.get("/plans/{plan_id}/status")
async def get_plan_execution_status(plan_id: str):
    """Get plan execution status.

    Sprint 31: 使用 PlanningAdapter.get_plan_status() 替代直接 domain 調用
    """
    try:
        plan_uuid = UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan ID")

    # Sprint 31: 使用適配器方法
    status = _planning_adapter.get_plan_status(plan_uuid)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])

    return status


@router.post("/plans/{plan_id}/approve", response_model=SuccessResponse)
async def approve_plan(plan_id: str, request: ApprovePlanRequest):
    """Approve a plan for execution.

    Sprint 31: 使用 PlanningAdapter.approve_plan() 替代直接 domain 調用
    """
    try:
        plan_uuid = UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan ID")

    try:
        # Sprint 31: 使用適配器方法
        await _planning_adapter.approve_plan(plan_uuid, request.approver)
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

    Sprint 31: 使用 PlanningAdapter.execute_plan() 替代直接 domain 調用
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

    # Sprint 31: 使用適配器方法
    background_tasks.add_task(
        _planning_adapter.execute_plan,
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
    """Pause plan execution.

    Sprint 31: 使用 PlanningAdapter.pause_plan() 替代直接 domain 調用
    """
    try:
        plan_uuid = UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan ID")

    try:
        # Sprint 31: 使用適配器方法
        await _planning_adapter.pause_plan(plan_uuid)
        return SuccessResponse(message=f"Plan {plan_id} paused")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/plans/{plan_id}/adjustments/approve", response_model=SuccessResponse)
async def approve_adjustment(plan_id: str, request: ApproveAdjustmentRequest):
    """Approve a plan adjustment.

    Sprint 31: 使用 PlanningAdapter.approve_adjustment() 替代直接 domain 調用
    """
    try:
        plan_uuid = UUID(plan_id)
        adjustment_uuid = UUID(request.adjustment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    try:
        # Sprint 31: 使用適配器方法
        await _planning_adapter.approve_adjustment(
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
    """List all plans.

    Sprint 31: 使用 PlanningAdapter.list_plans() 替代直接 domain 調用
    """
    plan_status = None
    if status:
        try:
            plan_status = PlanStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Valid values: {[s.value for s in PlanStatus]}"
            )

    # Sprint 31: 使用適配器方法
    plans = _planning_adapter.list_plans(status=plan_status, limit=limit)
    return {"plans": plans, "count": len(plans)}


@router.delete("/plans/{plan_id}", response_model=SuccessResponse)
async def delete_plan(plan_id: str):
    """Delete a plan.

    Sprint 31: 使用 PlanningAdapter.delete_plan() 替代直接 domain 調用
    """
    try:
        plan_uuid = UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan ID")

    # Sprint 31: 使用適配器方法
    if _planning_adapter.delete_plan(plan_uuid):
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

    Sprint 31: 使用 PlanningAdapter.make_decision() 替代直接 domain 調用
    """
    try:
        decision_type = DecisionType(request.decision_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid decision type. Valid values: {[t.value for t in DecisionType]}"
        )

    try:
        # Sprint 31: 使用適配器方法
        result = await _planning_adapter.make_decision(
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
    """Get detailed explanation of a decision.

    Sprint 31: 使用 PlanningAdapter.explain_decision() 替代直接 domain 調用
    """
    try:
        decision_uuid = UUID(decision_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid decision ID")

    # Sprint 31: 使用適配器方法
    explanation = await _planning_adapter.explain_decision(decision_uuid)

    if explanation == "Decision not found":
        raise HTTPException(status_code=404, detail="Decision not found")

    return DecisionExplanationResponse(
        decision_id=decision_id,
        explanation=explanation
    )


@router.post("/decisions/{decision_id}/approve", response_model=SuccessResponse)
async def approve_decision(decision_id: str, request: ApproveDecisionRequest):
    """Approve a decision that requires human approval.

    Sprint 31: 使用 PlanningAdapter.approve_decision() 替代直接 domain 調用
    """
    try:
        decision_uuid = UUID(decision_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid decision ID")

    # Sprint 31: 使用適配器方法
    success = await _planning_adapter.approve_decision(decision_uuid, request.approver)
    if not success:
        raise HTTPException(status_code=404, detail="Decision not found")

    return SuccessResponse(message="Decision approved")


@router.post("/decisions/{decision_id}/reject", response_model=SuccessResponse)
async def reject_decision(decision_id: str, request: RejectDecisionRequest):
    """Reject a decision.

    Sprint 31: 使用 PlanningAdapter.reject_decision() 替代直接 domain 調用
    """
    try:
        decision_uuid = UUID(decision_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid decision ID")

    # Sprint 31: 使用適配器方法
    success = await _planning_adapter.reject_decision(
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
    """List decision history.

    Sprint 31: 使用 PlanningAdapter.get_decision_history() 替代直接 domain 調用
    """
    dt = None
    if decision_type:
        try:
            dt = DecisionType(decision_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid type. Valid values: {[t.value for t in DecisionType]}"
            )

    # Sprint 31: 使用適配器方法
    history = _planning_adapter.get_decision_history(decision_type=dt, limit=limit)
    return {"decisions": history, "count": len(history)}


@router.get("/decisions/rules")
async def list_decision_rules():
    """List all registered decision rules.

    Sprint 31: 使用 PlanningAdapter.list_decision_rules() 替代直接 domain 調用
    """
    # Sprint 31: 使用適配器方法
    rules = _planning_adapter.list_decision_rules()
    return {"rules": rules, "count": len(rules)}


# =============================================================================
# Trial and Error Endpoints
# =============================================================================


@router.post("/trial", response_model=TrialResponse)
async def execute_with_trial(request: TrialRequest):
    """
    Execute a task using trial-and-error mechanism.

    Automatically retries with parameter adjustment on failure.

    Sprint 31: 使用 PlanningAdapter.execute_trial() 替代直接 domain 調用
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

    # Sprint 31: 使用適配器方法
    result = await _planning_adapter.execute_trial(
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
    """Get learning insights from trial history.

    Sprint 31: 使用 PlanningAdapter.learn_from_history() 替代直接 domain 調用
    """
    # Sprint 31: 使用適配器方法
    insights = await _planning_adapter.learn_from_history()

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
    """Get recommendations based on learning history.

    Sprint 31: 使用 PlanningAdapter.get_trial_recommendations() 替代直接 domain 調用
    """
    # Sprint 31: 使用適配器方法
    recommendations = _planning_adapter.get_trial_recommendations(task_type=task_type)

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
    """Get overall trial execution statistics.

    Sprint 31: 使用 PlanningAdapter.get_trial_statistics() 替代直接 domain 調用
    """
    # Sprint 31: 使用適配器方法
    stats = _planning_adapter.get_trial_statistics()
    return TrialStatisticsResponse(**stats)


@router.get("/trial/history")
async def get_trial_history(
    task_id: Optional[str] = Query(None, description="Filter by task ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=500)
):
    """Get trial execution history.

    Sprint 31: 使用 PlanningAdapter.get_trial_history() 替代直接 domain 調用
    """
    task_uuid = None
    if task_id:
        try:
            task_uuid = UUID(task_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid task ID")

    # Sprint 31: 使用從適配器導入的 TrialStatus (已在檔案頂部導入)
    trial_status = None
    if status:
        try:
            trial_status = TrialStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Valid values: {[s.value for s in TrialStatus]}"
            )

    # Sprint 31: 使用適配器方法
    history = _planning_adapter.get_trial_history(
        task_id=task_uuid,
        status=trial_status,
        limit=limit
    )
    return {"trials": history, "count": len(history)}


@router.delete("/trial/history")
async def clear_trial_history(
    task_id: Optional[str] = Query(None, description="Clear only for specific task")
):
    """Clear trial history.

    Sprint 31: 使用 PlanningAdapter.clear_trial_history() 替代直接 domain 調用
    """
    task_uuid = None
    if task_id:
        try:
            task_uuid = UUID(task_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid task ID")

    # Sprint 31: 使用適配器方法
    _planning_adapter.clear_trial_history(task_id=task_uuid)
    return SuccessResponse(message="Trial history cleared")


# =============================================================================
# Sprint 17: MagenticBuilder (Magentic One) Endpoints
# =============================================================================
# Provides REST API for creating and managing Magentic workflow adapters,
# supporting multi-agent orchestration with human intervention capabilities.
# =============================================================================

from .schemas import (
    CreateMagenticAdapterRequest,
    RunMagenticWorkflowRequest,
    MagenticAdapterResponse,
    MagenticResultSchema,
    MagenticRoundSchema,
    MagenticMessageSchema,
    MagenticStateSchema,
    HumanInterventionReplySchema,
    HumanInterventionRequestSchema,
    TaskLedgerSchema,
    ProgressLedgerSchema,
    ProgressLedgerItemSchema,
)

# In-memory storage for Magentic adapters (production: use database)
_magentic_adapters: dict = {}


@router.post("/magentic/adapter", response_model=MagenticAdapterResponse)
async def create_magentic_adapter(request: CreateMagenticAdapterRequest):
    """
    Create a new Magentic workflow adapter.

    Creates an adapter for multi-agent orchestration using the Magentic One
    pattern with support for plan review and stall intervention.
    """
    try:
        from src.integrations.agent_framework.builders import (
            MagenticBuilderAdapter,
            MagenticParticipant,
            create_magentic_adapter as factory_create,
        )

        # Convert schema participants to domain objects
        participants = [
            MagenticParticipant(
                name=p.name,
                description=p.description,
                capabilities=p.capabilities,
                metadata=p.metadata,
            )
            for p in request.participants
        ]

        # Create the adapter
        adapter = factory_create(
            id=request.id,
            participants=participants,
            max_round_count=request.max_round_count,
            max_stall_count=request.max_stall_count,
        )

        # Configure optional features
        if request.enable_plan_review:
            adapter.with_plan_review(True)
        if request.enable_stall_intervention:
            adapter.with_stall_intervention(True)

        # Build the adapter
        adapter.build()

        # Store in cache
        _magentic_adapters[request.id] = adapter

        return MagenticAdapterResponse(
            id=request.id,
            status="ready",
            is_built=adapter._is_built,
            is_initialized=adapter._is_initialized,
            participants=[p.name for p in participants],
            config={
                "max_round_count": request.max_round_count,
                "max_stall_count": request.max_stall_count,
                "enable_plan_review": request.enable_plan_review,
                "enable_stall_intervention": request.enable_stall_intervention,
                **request.config,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/magentic/adapter/{adapter_id}", response_model=MagenticStateSchema)
async def get_magentic_adapter_state(adapter_id: str):
    """
    Get the current state of a Magentic adapter.

    Returns detailed state including round count, stall count, participants,
    and any pending human intervention requests.
    """
    adapter = _magentic_adapters.get(adapter_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Adapter '{adapter_id}' not found")

    try:
        state = adapter.get_state()

        # Convert pending intervention if exists
        pending_intervention = None
        if state.get("pending_intervention"):
            pi = state["pending_intervention"]
            pending_intervention = HumanInterventionRequestSchema(
                request_id=pi.request_id,
                kind=pi.kind.value if hasattr(pi.kind, "value") else str(pi.kind),
                task_text=pi.task_text,
                facts_text=pi.facts_text,
                plan_text=pi.plan_text,
                round_index=pi.round_index,
                stall_count=pi.stall_count,
                stall_reason=pi.stall_reason,
                last_agent=pi.last_agent,
            )

        return MagenticStateSchema(
            id=adapter_id,
            status=state.get("status", "unknown"),
            is_built=state.get("is_built", False),
            is_initialized=state.get("is_initialized", False),
            round_count=state.get("round_count", 0),
            stall_count=state.get("stall_count", 0),
            reset_count=state.get("reset_count", 0),
            participants=state.get("participants", []),
            pending_intervention=pending_intervention,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/magentic/adapter/{adapter_id}", response_model=SuccessResponse)
async def delete_magentic_adapter(adapter_id: str):
    """Delete a Magentic adapter."""
    if adapter_id not in _magentic_adapters:
        raise HTTPException(status_code=404, detail=f"Adapter '{adapter_id}' not found")

    try:
        adapter = _magentic_adapters.pop(adapter_id)
        # Clean up any resources if needed
        if hasattr(adapter, "cleanup"):
            await adapter.cleanup()

        return SuccessResponse(message=f"Adapter '{adapter_id}' deleted")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/magentic/adapter/{adapter_id}/run", response_model=MagenticResultSchema)
async def run_magentic_workflow(
    adapter_id: str,
    request: RunMagenticWorkflowRequest,
):
    """
    Run a Magentic workflow.

    Executes the multi-agent workflow with the given task, managing rounds
    of agent interactions until completion or termination.
    """
    adapter = _magentic_adapters.get(adapter_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Adapter '{adapter_id}' not found")

    try:
        # Run the workflow
        result = await adapter.run(
            task=request.task,
            timeout_seconds=request.timeout_seconds,
            metadata=request.metadata,
        )

        # Convert result to schema
        conversation = []
        for msg in result.conversation:
            conversation.append(
                MagenticMessageSchema(
                    role=msg.role.value if hasattr(msg.role, "value") else str(msg.role),
                    content=msg.content,
                    author_name=msg.author_name,
                    timestamp=msg.timestamp,
                    metadata=msg.metadata,
                )
            )

        rounds = []
        for r in result.rounds:
            round_response = None
            if r.response:
                round_response = MagenticMessageSchema(
                    role=r.response.role.value if hasattr(r.response.role, "value") else str(r.response.role),
                    content=r.response.content,
                    author_name=r.response.author_name,
                    timestamp=r.response.timestamp,
                    metadata=r.response.metadata,
                )
            rounds.append(
                MagenticRoundSchema(
                    round_index=r.round_index,
                    speaker=r.speaker,
                    instruction=r.instruction,
                    response=round_response,
                    duration_seconds=r.duration_seconds,
                )
            )

        final_answer = None
        if result.final_answer:
            final_answer = MagenticMessageSchema(
                role=result.final_answer.role.value if hasattr(result.final_answer.role, "value") else str(result.final_answer.role),
                content=result.final_answer.content,
                author_name=result.final_answer.author_name,
                timestamp=result.final_answer.timestamp,
                metadata=result.final_answer.metadata,
            )

        return MagenticResultSchema(
            status=result.status.value if hasattr(result.status, "value") else str(result.status),
            final_answer=final_answer,
            conversation=conversation,
            rounds=rounds,
            total_rounds=result.total_rounds,
            total_resets=result.total_resets,
            participants_involved=result.participants_involved,
            duration_seconds=result.duration_seconds,
            termination_reason=result.termination_reason,
            metadata=result.metadata,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/magentic/adapter/{adapter_id}/intervention", response_model=SuccessResponse)
async def respond_to_intervention(
    adapter_id: str,
    request: HumanInterventionReplySchema,
):
    """
    Respond to a human intervention request.

    Handles plan review approvals, stall interventions, and tool approvals
    to continue workflow execution.
    """
    adapter = _magentic_adapters.get(adapter_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Adapter '{adapter_id}' not found")

    try:
        from src.integrations.agent_framework.builders import (
            HumanInterventionReply,
            HumanInterventionDecision,
        )

        # Convert decision string to enum
        decision_map = {
            "approve": HumanInterventionDecision.APPROVE,
            "revise": HumanInterventionDecision.REVISE,
            "reject": HumanInterventionDecision.REJECT,
            "continue": HumanInterventionDecision.CONTINUE,
            "replan": HumanInterventionDecision.REPLAN,
            "guidance": HumanInterventionDecision.GUIDANCE,
        }

        decision = decision_map.get(request.decision.lower())
        if not decision:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid decision. Valid values: {list(decision_map.keys())}",
            )

        # Create reply object
        reply = HumanInterventionReply(
            decision=decision,
            edited_plan_text=request.edited_plan_text,
            comments=request.comments,
            response_text=request.response_text,
        )

        # Submit the reply
        await adapter.respond_to_intervention(reply)

        return SuccessResponse(
            message=f"Intervention response '{request.decision}' submitted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/magentic/adapters")
async def list_magentic_adapters(
    limit: int = Query(50, ge=1, le=100),
):
    """List all Magentic adapters."""
    adapters = []
    for adapter_id, adapter in list(_magentic_adapters.items())[:limit]:
        try:
            state = adapter.get_state()
            adapters.append({
                "id": adapter_id,
                "status": state.get("status", "unknown"),
                "is_built": state.get("is_built", False),
                "is_initialized": state.get("is_initialized", False),
                "round_count": state.get("round_count", 0),
                "participants": state.get("participants", []),
            })
        except Exception:
            adapters.append({
                "id": adapter_id,
                "status": "error",
                "is_built": False,
                "is_initialized": False,
                "round_count": 0,
                "participants": [],
            })

    return {"adapters": adapters, "count": len(adapters)}


@router.get("/magentic/adapter/{adapter_id}/ledger")
async def get_magentic_ledger(adapter_id: str):
    """
    Get the current Task and Progress Ledger for a Magentic adapter.

    Returns the extracted facts, plan, and progress evaluation.
    """
    adapter = _magentic_adapters.get(adapter_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Adapter '{adapter_id}' not found")

    try:
        ledger = adapter.get_ledger()
        if not ledger:
            return {"task_ledger": None, "progress_ledger": None}

        return {
            "task_ledger": {
                "facts": ledger.get("task_ledger", {}).get("facts"),
                "plan": ledger.get("task_ledger", {}).get("plan"),
            },
            "progress_ledger": ledger.get("progress_ledger"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/magentic/adapter/{adapter_id}/reset", response_model=SuccessResponse)
async def reset_magentic_adapter(adapter_id: str):
    """Reset a Magentic adapter to initial state."""
    adapter = _magentic_adapters.get(adapter_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Adapter '{adapter_id}' not found")

    try:
        await adapter.reset()
        return SuccessResponse(message=f"Adapter '{adapter_id}' reset to initial state")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Sprint 24: PlanningAdapter Endpoints
# =============================================================================
# 使用官方 MagenticBuilder 整合 Phase 2 擴展功能

from .schemas import (
    CreatePlanningAdapterRequest,
    RunPlanningAdapterRequest,
    PlanningAdapterResponse,
    PlanningResultSchema,
    CreateMultiTurnAdapterRequest,
    AddTurnRequest,
    TurnResultSchema,
    MultiTurnAdapterResponse,
    MultiTurnHistoryResponse,
)

# In-memory storage for Sprint 24 adapters
_planning_adapters: dict = {}
_multiturn_adapters: dict = {}


@router.post("/adapter/planning", response_model=PlanningAdapterResponse)
async def create_planning_adapter(request: CreatePlanningAdapterRequest):
    """
    Create a new PlanningAdapter (Sprint 24).

    使用官方 MagenticBuilder 整合 Phase 2 擴展功能。
    """
    try:
        from src.integrations.agent_framework.builders import (
            PlanningAdapter,
            PlanningMode,
            DecompositionStrategy,
            PlanningConfig,
            DecisionRule,
        )

        # Parse mode
        try:
            mode = PlanningMode(request.mode)
        except ValueError:
            mode = PlanningMode.SIMPLE

        # Parse decomposition strategy
        decomp_strategy = None
        if request.decomposition_strategy:
            try:
                decomp_strategy = DecompositionStrategy(request.decomposition_strategy)
            except ValueError:
                decomp_strategy = DecompositionStrategy.HYBRID

        # Create config
        config = PlanningConfig(
            mode=mode,
            decomposition_strategy=decomp_strategy or DecompositionStrategy.HYBRID,
            max_retries=request.max_retries,
            enable_progress_tracking=True,
        )

        # Create adapter
        adapter = PlanningAdapter(id=request.id, config=config)

        # Apply optional extensions
        if request.decomposition_strategy or request.enable_decision_engine:
            if decomp_strategy:
                adapter.with_task_decomposition(strategy=decomp_strategy)

        if request.enable_decision_engine:
            rules = [
                DecisionRule(
                    name=r.get("name", "custom_rule"),
                    condition=r.get("condition", ""),
                    action=r.get("action", ""),
                    priority=r.get("priority", 1),
                )
                for r in request.decision_rules
            ] if request.decision_rules else None
            adapter.with_decision_engine(rules=rules)

        if request.enable_trial_error:
            adapter.with_trial_error(max_retries=request.max_retries)

        # Build the adapter
        adapter.build()

        # Store adapter
        _planning_adapters[request.id] = adapter

        return PlanningAdapterResponse(
            id=request.id,
            mode=mode.value,
            status="ready",
            has_decomposer=adapter._task_decomposer is not None,
            has_decision_engine=adapter._decision_engine is not None,
            has_trial_error=adapter._trial_error_engine is not None,
            config={
                "decomposition_strategy": decomp_strategy.value if decomp_strategy else None,
                "max_retries": request.max_retries,
                **request.config,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/adapter/planning/{adapter_id}", response_model=PlanningAdapterResponse)
async def get_planning_adapter(adapter_id: str):
    """Get PlanningAdapter details."""
    adapter = _planning_adapters.get(adapter_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Adapter '{adapter_id}' not found")

    return PlanningAdapterResponse(
        id=adapter_id,
        mode=adapter._config.mode.value,
        status="ready",
        has_decomposer=adapter._task_decomposer is not None,
        has_decision_engine=adapter._decision_engine is not None,
        has_trial_error=adapter._trial_error_engine is not None,
        config={
            "decomposition_strategy": adapter._config.decomposition_strategy.value,
            "max_retries": adapter._config.max_retries,
        },
    )


@router.post("/adapter/planning/{adapter_id}/run", response_model=PlanningResultSchema)
async def run_planning_adapter(adapter_id: str, request: RunPlanningAdapterRequest):
    """Run a PlanningAdapter."""
    adapter = _planning_adapters.get(adapter_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Adapter '{adapter_id}' not found")

    try:
        import time
        start_time = time.time()

        result = await adapter.run(goal=request.goal, context=request.context)

        duration = time.time() - start_time

        return PlanningResultSchema(
            plan_id=result.plan_id,
            goal=result.goal,
            status=result.status.value,
            steps=[step.__dict__ if hasattr(step, '__dict__') else step for step in result.steps],
            decisions=[d.__dict__ if hasattr(d, '__dict__') else d for d in result.decisions],
            total_duration_seconds=duration,
            confidence_score=result.confidence_score,
            metadata=result.metadata,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/adapter/planning/{adapter_id}", response_model=SuccessResponse)
async def delete_planning_adapter(adapter_id: str):
    """Delete a PlanningAdapter."""
    if adapter_id not in _planning_adapters:
        raise HTTPException(status_code=404, detail=f"Adapter '{adapter_id}' not found")

    del _planning_adapters[adapter_id]
    return SuccessResponse(message=f"Adapter '{adapter_id}' deleted")


@router.get("/adapter/planning")
async def list_planning_adapters(
    limit: int = Query(50, ge=1, le=100),
):
    """List all PlanningAdapters."""
    adapters = []
    for adapter_id, adapter in list(_planning_adapters.items())[:limit]:
        adapters.append({
            "id": adapter_id,
            "mode": adapter._config.mode.value,
            "status": "ready",
            "has_decomposer": adapter._task_decomposer is not None,
            "has_decision_engine": adapter._decision_engine is not None,
        })
    return {"adapters": adapters, "count": len(adapters)}


# =============================================================================
# Sprint 24: MultiTurnAdapter Endpoints
# =============================================================================
# 使用官方 CheckpointStorage 整合會話管理


@router.post("/adapter/multiturn", response_model=MultiTurnAdapterResponse)
async def create_multiturn_adapter(request: CreateMultiTurnAdapterRequest):
    """
    Create a new MultiTurnAdapter (Sprint 24).

    使用官方 CheckpointStorage 管理多輪對話狀態。
    """
    try:
        from src.integrations.agent_framework.builders import (
            MultiTurnAdapter,
            create_multiturn_adapter as factory_create,
        )
        from src.integrations.agent_framework.multiturn import (
            MultiTurnConfig,
            FileCheckpointStorage,
        )

        # Create config
        config = MultiTurnConfig(
            max_turns=request.max_turns,
            max_history_length=request.max_history_length,
            session_timeout_seconds=request.session_timeout_seconds,
            auto_save=request.auto_save,
        )

        # Create storage based on type
        storage = None
        if request.storage_type == "file":
            base_path = request.storage_config.get("base_path", "/tmp/checkpoints")
            storage = FileCheckpointStorage(base_path=base_path)
        # For redis and postgres, would need actual clients
        # storage_type == "memory" uses default InMemoryCheckpointStorage

        # Create adapter
        adapter = factory_create(
            session_id=request.session_id,
            config=config,
            checkpoint_storage=storage,
        )

        # Start the session
        await adapter.start()

        # Store adapter
        _multiturn_adapters[adapter.session_id] = adapter

        info = adapter.get_session_info()

        return MultiTurnAdapterResponse(
            session_id=adapter.session_id,
            state=info.state.value,
            turn_count=info.turn_count,
            created_at=info.created_at,
            updated_at=info.updated_at,
            config={
                "max_turns": config.max_turns,
                "max_history_length": config.max_history_length,
                "auto_save": config.auto_save,
                "storage_type": request.storage_type,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/adapter/multiturn/{session_id}", response_model=MultiTurnAdapterResponse)
async def get_multiturn_adapter(session_id: str):
    """Get MultiTurnAdapter details."""
    adapter = _multiturn_adapters.get(session_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    info = adapter.get_session_info()

    return MultiTurnAdapterResponse(
        session_id=adapter.session_id,
        state=info.state.value,
        turn_count=info.turn_count,
        created_at=info.created_at,
        updated_at=info.updated_at,
        config={
            "max_turns": adapter.config.max_turns,
            "max_history_length": adapter.config.max_history_length,
            "auto_save": adapter.config.auto_save,
        },
    )


@router.post("/adapter/multiturn/{session_id}/turn", response_model=TurnResultSchema)
async def add_multiturn_turn(session_id: str, request: AddTurnRequest):
    """Add a turn to MultiTurnAdapter."""
    adapter = _multiturn_adapters.get(session_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    try:
        result = await adapter.add_turn(
            user_input=request.user_input,
            assistant_response=request.assistant_response,
            context=request.context,
            metadata=request.metadata,
        )

        return TurnResultSchema(
            turn_id=result.turn_id,
            session_id=result.session_id,
            user_input=result.input_message.content,
            assistant_response=result.output_message.content if result.output_message else None,
            context=result.context,
            duration_ms=result.duration_ms,
            success=result.success,
            error=result.error,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/adapter/multiturn/{session_id}/history", response_model=MultiTurnHistoryResponse)
async def get_multiturn_history(
    session_id: str,
    limit: Optional[int] = Query(None, ge=1, le=500),
):
    """Get MultiTurnAdapter conversation history."""
    adapter = _multiturn_adapters.get(session_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    history = adapter.get_history(n=limit)

    return MultiTurnHistoryResponse(
        session_id=session_id,
        messages=[msg.to_dict() for msg in history],
        turn_count=adapter.turn_count,
        total_messages=len(history),
    )


@router.post("/adapter/multiturn/{session_id}/checkpoint", response_model=SuccessResponse)
async def save_multiturn_checkpoint(session_id: str):
    """Save a checkpoint for MultiTurnAdapter."""
    adapter = _multiturn_adapters.get(session_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    await adapter.save_checkpoint()
    return SuccessResponse(message=f"Checkpoint saved for session '{session_id}'")


@router.post("/adapter/multiturn/{session_id}/restore", response_model=SuccessResponse)
async def restore_multiturn_checkpoint(session_id: str):
    """Restore from a checkpoint for MultiTurnAdapter."""
    adapter = _multiturn_adapters.get(session_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    success = await adapter.restore_checkpoint()
    if success:
        return SuccessResponse(message=f"Checkpoint restored for session '{session_id}'")
    else:
        raise HTTPException(status_code=404, detail="No checkpoint found")


@router.post("/adapter/multiturn/{session_id}/complete", response_model=MultiTurnAdapterResponse)
async def complete_multiturn_session(session_id: str):
    """Complete a MultiTurnAdapter session."""
    adapter = _multiturn_adapters.get(session_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    info = await adapter.complete()

    return MultiTurnAdapterResponse(
        session_id=adapter.session_id,
        state=info.state.value,
        turn_count=info.turn_count,
        created_at=info.created_at,
        updated_at=info.updated_at,
        config={
            "max_turns": adapter.config.max_turns,
        },
    )


@router.delete("/adapter/multiturn/{session_id}", response_model=SuccessResponse)
async def delete_multiturn_adapter(session_id: str):
    """Delete a MultiTurnAdapter."""
    if session_id not in _multiturn_adapters:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    adapter = _multiturn_adapters.pop(session_id)
    await adapter.clear_session()

    return SuccessResponse(message=f"Session '{session_id}' deleted")


@router.get("/adapter/multiturn")
async def list_multiturn_adapters(
    limit: int = Query(50, ge=1, le=100),
):
    """List all MultiTurnAdapters."""
    adapters = []
    for session_id, adapter in list(_multiturn_adapters.items())[:limit]:
        info = adapter.get_session_info()
        adapters.append({
            "session_id": session_id,
            "state": info.state.value,
            "turn_count": info.turn_count,
            "created_at": info.created_at.isoformat(),
        })
    return {"adapters": adapters, "count": len(adapters)}


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
            "trial_engine": "ready",
            "magentic_builder": "ready",
            "planning_adapter": "ready",  # Sprint 24
            "multiturn_adapter": "ready",  # Sprint 24
        }
    }
