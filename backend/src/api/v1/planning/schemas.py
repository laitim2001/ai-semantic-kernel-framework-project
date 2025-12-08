# =============================================================================
# IPA Platform - Planning API Schemas
# =============================================================================
# Sprint 10: S10-5 Planning API (5 points)
#
# Pydantic schemas for Planning API endpoints including task decomposition,
# dynamic planning, decision-making, and trial-and-error execution.
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Task Decomposition Schemas
# =============================================================================


class DecomposeTaskRequest(BaseModel):
    """Request to decompose a task into subtasks."""
    task_description: str = Field(..., description="Task description to decompose")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context")
    strategy: str = Field(
        default="hybrid",
        description="Decomposition strategy: hierarchical, sequential, parallel, hybrid"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "task_description": "Implement user authentication system",
                "context": {"framework": "FastAPI", "database": "PostgreSQL"},
                "strategy": "hybrid"
            }
        }
    }


class SubTaskResponse(BaseModel):
    """Response for a single subtask."""
    id: str
    name: str
    description: str
    priority: str
    status: str
    dependencies: List[str]
    estimated_duration_minutes: int
    assigned_agent_id: Optional[str] = None


class DecompositionResponse(BaseModel):
    """Response for task decomposition."""
    task_id: str
    original_task: str
    subtasks: List[SubTaskResponse]
    execution_order: List[List[str]]
    estimated_total_duration: int
    confidence_score: float
    strategy: str


class RefineDecompositionRequest(BaseModel):
    """Request to refine a decomposition based on feedback."""
    feedback: str = Field(..., description="Improvement feedback")


# =============================================================================
# Dynamic Planning Schemas
# =============================================================================


class CreatePlanRequest(BaseModel):
    """Request to create an execution plan."""
    goal: str = Field(..., description="Goal description")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context")
    deadline: Optional[datetime] = Field(None, description="Optional deadline")
    strategy: str = Field(default="hybrid", description="Decomposition strategy")

    model_config = {
        "json_schema_extra": {
            "example": {
                "goal": "Build REST API service with authentication",
                "context": {"team_size": 3},
                "deadline": "2025-12-31T23:59:59Z"
            }
        }
    }


class PlanResponse(BaseModel):
    """Response for plan operations."""
    id: str
    name: str
    goal: str
    status: str
    progress: float
    current_phase: int
    total_phases: int
    subtasks_count: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deadline: Optional[datetime] = None


class PlanStatusResponse(BaseModel):
    """Detailed plan status response."""
    id: str
    name: str
    status: str
    progress: float
    current_phase: int
    total_phases: int
    adjustments: int
    subtasks: List[Dict[str, Any]]


class ApprovePlanRequest(BaseModel):
    """Request to approve a plan."""
    approver: str = Field(..., description="Approver name/ID")


class ApproveAdjustmentRequest(BaseModel):
    """Request to approve a plan adjustment."""
    adjustment_id: str = Field(..., description="Adjustment ID to approve")
    approver: str = Field(..., description="Approver name/ID")


# =============================================================================
# Decision Schemas
# =============================================================================


class DecisionRequest(BaseModel):
    """Request for a decision."""
    situation: str = Field(..., description="Situation description")
    options: List[str] = Field(..., description="Available options")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context")
    decision_type: str = Field(
        default="routing",
        description="Decision type: routing, resource, error_handling, priority, escalation, optimization"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "situation": "Multiple agents available for task",
                "options": ["agent_a", "agent_b", "agent_c"],
                "context": {"priority": "high"},
                "decision_type": "routing"
            }
        }
    }


class DecisionOptionResponse(BaseModel):
    """Response for a decision option."""
    id: str
    name: str
    score: float


class DecisionResponse(BaseModel):
    """Response for a decision."""
    decision_id: str
    action: str
    confidence: str
    reasoning: str
    risk_level: float
    requires_approval: bool
    options: List[DecisionOptionResponse]


class ApproveDecisionRequest(BaseModel):
    """Request to approve a decision."""
    approver: str = Field(..., description="Approver name/ID")


class RejectDecisionRequest(BaseModel):
    """Request to reject a decision."""
    approver: str = Field(..., description="Approver name/ID")
    reason: str = Field(..., description="Rejection reason")


class DecisionExplanationResponse(BaseModel):
    """Response for decision explanation."""
    decision_id: str
    explanation: str


# =============================================================================
# Trial and Error Schemas
# =============================================================================


class TrialRequest(BaseModel):
    """Request to execute a task with trial and error."""
    task_id: str = Field(..., description="Task ID")
    params: Dict[str, Any] = Field(default_factory=dict, description="Execution parameters")
    strategy: str = Field(default="default", description="Execution strategy")

    model_config = {
        "json_schema_extra": {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "params": {"timeout": 30, "retry_delay": 5},
                "strategy": "default"
            }
        }
    }


class TrialResultResponse(BaseModel):
    """Response for a single trial."""
    id: str
    task_id: str
    attempt_number: int
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: int


class TrialResponse(BaseModel):
    """Response for trial execution."""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    attempts: int
    final_params: Dict[str, Any]
    final_strategy: str
    trials: Optional[List[Dict[str, Any]]] = None


class InsightResponse(BaseModel):
    """Response for a learning insight."""
    id: str
    type: str
    pattern: str
    confidence: float
    recommendation: str
    created_at: str


class InsightsListResponse(BaseModel):
    """Response for list of insights."""
    insights: List[InsightResponse]


class RecommendationResponse(BaseModel):
    """Response for a recommendation."""
    id: str
    type: str
    pattern: str
    recommendation: str
    confidence: float
    created_at: str


class RecommendationsListResponse(BaseModel):
    """Response for list of recommendations."""
    recommendations: List[RecommendationResponse]


class TrialStatisticsResponse(BaseModel):
    """Response for trial statistics."""
    total_trials: int
    success_count: int
    failure_count: int
    success_rate: float
    average_duration_ms: float
    unique_tasks: int
    insights_count: int
    known_patterns: int


# =============================================================================
# Common Schemas
# =============================================================================


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str = ""


class ErrorResponse(BaseModel):
    """Generic error response."""
    success: bool = False
    error: str
    detail: Optional[str] = None


class PaginationParams(BaseModel):
    """Pagination parameters."""
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


# =============================================================================
# Sprint 17: MagenticBuilder (Magentic One) Schemas
# =============================================================================


class MagenticParticipantSchema(BaseModel):
    """Participant in a Magentic workflow."""
    name: str = Field(..., description="參與者名稱")
    description: str = Field(default="", description="參與者描述")
    capabilities: List[str] = Field(default_factory=list, description="能力列表")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MagenticMessageSchema(BaseModel):
    """Message in a Magentic workflow."""
    role: str = Field(..., description="消息角色 (user/assistant/system/manager)")
    content: str = Field(..., description="消息內容")
    author_name: Optional[str] = Field(None, description="作者名稱")
    timestamp: Optional[float] = Field(None, description="時間戳")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CreateMagenticAdapterRequest(BaseModel):
    """Request to create a Magentic workflow adapter."""
    id: str = Field(..., description="適配器 ID")
    participants: List[MagenticParticipantSchema] = Field(..., description="參與者列表")
    max_round_count: int = Field(default=20, ge=1, le=100, description="最大輪數")
    max_stall_count: int = Field(default=3, ge=1, le=10, description="最大停滯次數")
    enable_plan_review: bool = Field(default=False, description="啟用計劃審核")
    enable_stall_intervention: bool = Field(default=False, description="啟用停滯干預")
    config: Dict[str, Any] = Field(default_factory=dict, description="額外配置")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "research-workflow",
                "participants": [
                    {"name": "researcher", "description": "Research specialist"},
                    {"name": "writer", "description": "Technical writer"},
                ],
                "max_round_count": 15,
                "max_stall_count": 3,
                "enable_plan_review": True,
            }
        }
    }


class RunMagenticWorkflowRequest(BaseModel):
    """Request to run a Magentic workflow."""
    task: str = Field(..., description="任務描述")
    timeout_seconds: Optional[float] = Field(None, ge=1, description="超時秒數")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MagenticAdapterResponse(BaseModel):
    """Response for Magentic adapter operations."""
    id: str
    status: str
    is_built: bool
    is_initialized: bool
    participants: List[str]
    config: Dict[str, Any]


class MagenticRoundSchema(BaseModel):
    """A single round of Magentic execution."""
    round_index: int
    speaker: str
    instruction: str
    response: Optional[MagenticMessageSchema] = None
    duration_seconds: float = 0.0


class MagenticResultSchema(BaseModel):
    """Result of a Magentic workflow execution."""
    status: str
    final_answer: Optional[MagenticMessageSchema] = None
    conversation: List[MagenticMessageSchema]
    rounds: List[MagenticRoundSchema]
    total_rounds: int
    total_resets: int
    participants_involved: List[str]
    duration_seconds: float
    termination_reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskLedgerSchema(BaseModel):
    """Task ledger containing facts and plan."""
    facts: MagenticMessageSchema
    plan: MagenticMessageSchema


class ProgressLedgerItemSchema(BaseModel):
    """A single item in the progress ledger."""
    reason: str
    answer: Any  # str or bool


class ProgressLedgerSchema(BaseModel):
    """Progress ledger for tracking workflow progress."""
    is_request_satisfied: ProgressLedgerItemSchema
    is_in_loop: ProgressLedgerItemSchema
    is_progress_being_made: ProgressLedgerItemSchema
    next_speaker: ProgressLedgerItemSchema
    instruction_or_question: ProgressLedgerItemSchema


class HumanInterventionRequestSchema(BaseModel):
    """Human intervention request."""
    request_id: str
    kind: str  # plan_review, tool_approval, stall
    task_text: str = ""
    facts_text: str = ""
    plan_text: str = ""
    round_index: int = 0
    stall_count: int = 0
    stall_reason: str = ""
    last_agent: str = ""


class HumanInterventionReplySchema(BaseModel):
    """Human intervention reply."""
    decision: str = Field(..., description="Decision: approve, revise, reject, continue, replan, guidance")
    edited_plan_text: Optional[str] = None
    comments: Optional[str] = None
    response_text: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "decision": "approve",
                "comments": "Plan looks good",
            }
        }
    }


class MagenticStateSchema(BaseModel):
    """Current state of a Magentic workflow."""
    id: str
    status: str
    is_built: bool
    is_initialized: bool
    round_count: int
    stall_count: int
    reset_count: int
    participants: List[str]
    pending_intervention: Optional[HumanInterventionRequestSchema] = None


# =============================================================================
# Sprint 24: PlanningAdapter Schemas
# =============================================================================


class CreatePlanningAdapterRequest(BaseModel):
    """Request to create a PlanningAdapter (Sprint 24)."""
    id: str = Field(..., description="適配器 ID")
    mode: str = Field(
        default="simple",
        description="規劃模式: simple, decomposed, decision_driven, adaptive, full"
    )
    decomposition_strategy: Optional[str] = Field(
        default=None,
        description="分解策略: sequential, hierarchical, parallel, hybrid"
    )
    enable_decision_engine: bool = Field(default=False, description="啟用決策引擎")
    enable_trial_error: bool = Field(default=False, description="啟用試錯學習")
    max_retries: int = Field(default=3, ge=1, le=10, description="最大重試次數")
    decision_rules: List[Dict[str, Any]] = Field(default_factory=list, description="決策規則")
    config: Dict[str, Any] = Field(default_factory=dict, description="額外配置")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "task-planner",
                "mode": "decomposed",
                "decomposition_strategy": "hierarchical",
                "enable_decision_engine": True,
            }
        }
    }


class RunPlanningAdapterRequest(BaseModel):
    """Request to run a PlanningAdapter (Sprint 24)."""
    goal: str = Field(..., description="規劃目標")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文")
    timeout_seconds: Optional[float] = Field(None, ge=1, description="超時秒數")

    model_config = {
        "json_schema_extra": {
            "example": {
                "goal": "Build a user authentication system",
                "context": {"framework": "FastAPI", "database": "PostgreSQL"},
            }
        }
    }


class PlanningAdapterResponse(BaseModel):
    """Response for PlanningAdapter operations (Sprint 24)."""
    id: str
    mode: str
    status: str
    has_decomposer: bool
    has_decision_engine: bool
    has_trial_error: bool
    config: Dict[str, Any]


class PlanningResultSchema(BaseModel):
    """Result of a PlanningAdapter execution (Sprint 24)."""
    plan_id: str
    goal: str
    status: str
    steps: List[Dict[str, Any]]
    decisions: List[Dict[str, Any]]
    total_duration_seconds: float
    confidence_score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Sprint 24: MultiTurnAdapter Schemas
# =============================================================================


class CreateMultiTurnAdapterRequest(BaseModel):
    """Request to create a MultiTurnAdapter (Sprint 24)."""
    session_id: Optional[str] = Field(None, description="會話 ID，不提供則自動生成")
    max_turns: int = Field(default=100, ge=1, le=1000, description="最大輪次")
    max_history_length: int = Field(default=50, ge=10, le=500, description="最大歷史長度")
    session_timeout_seconds: int = Field(default=3600, ge=60, description="會話超時時間")
    auto_save: bool = Field(default=True, description="自動保存")
    storage_type: str = Field(default="memory", description="存儲類型: memory, redis, postgres, file")
    storage_config: Dict[str, Any] = Field(default_factory=dict, description="存儲配置")

    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "user-123-session",
                "max_turns": 50,
                "storage_type": "memory",
            }
        }
    }


class AddTurnRequest(BaseModel):
    """Request to add a turn to MultiTurnAdapter (Sprint 24)."""
    user_input: str = Field(..., description="用戶輸入")
    assistant_response: Optional[str] = Field(None, description="助手回應")
    context: Optional[Dict[str, Any]] = Field(None, description="輪次上下文")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元數據")


class TurnResultSchema(BaseModel):
    """Result of a turn in MultiTurnAdapter (Sprint 24)."""
    turn_id: str
    session_id: str
    user_input: str
    assistant_response: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: float
    success: bool
    error: Optional[str] = None


class MultiTurnAdapterResponse(BaseModel):
    """Response for MultiTurnAdapter operations (Sprint 24)."""
    session_id: str
    state: str
    turn_count: int
    created_at: datetime
    updated_at: datetime
    config: Dict[str, Any]


class MultiTurnHistoryResponse(BaseModel):
    """Response for MultiTurnAdapter history (Sprint 24)."""
    session_id: str
    messages: List[Dict[str, Any]]
    turn_count: int
    total_messages: int
