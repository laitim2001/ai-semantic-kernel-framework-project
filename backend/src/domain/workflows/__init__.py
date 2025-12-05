# =============================================================================
# IPA Platform - Workflows Domain Module
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
# Sprint 7: Concurrent Execution Engine (Phase 2)
#
# Domain module for workflow management and execution.
# =============================================================================

from src.domain.workflows.models import (
    GatewayType,
    NodeType,
    TriggerType,
    WorkflowContext,
    WorkflowDefinition,
    WorkflowEdge,
    WorkflowNode,
)
from src.domain.workflows.schemas import (
    WorkflowCreateRequest,
    WorkflowEdgeSchema,
    WorkflowExecuteRequest,
    WorkflowExecutionResponse,
    WorkflowGraphSchema,
    WorkflowListResponse,
    WorkflowNodeSchema,
    WorkflowResponse,
    WorkflowUpdateRequest,
    WorkflowValidationResponse,
)
from src.domain.workflows.service import (
    NodeExecutionResult,
    WorkflowExecutionResult,
    WorkflowExecutionService,
    get_workflow_execution_service,
)

from src.domain.workflows.deadlock_detector import (
    DeadlockDetector,
    DeadlockInfo,
    DeadlockResolutionStrategy,
    TimeoutHandler,
    WaitingTask,
    get_deadlock_detector,
    reset_deadlock_detector,
)

__all__ = [
    # Models
    "NodeType",
    "TriggerType",
    "GatewayType",
    "WorkflowNode",
    "WorkflowEdge",
    "WorkflowDefinition",
    "WorkflowContext",
    # Schemas
    "WorkflowNodeSchema",
    "WorkflowEdgeSchema",
    "WorkflowGraphSchema",
    "WorkflowCreateRequest",
    "WorkflowUpdateRequest",
    "WorkflowResponse",
    "WorkflowListResponse",
    "WorkflowExecuteRequest",
    "WorkflowExecutionResponse",
    "WorkflowValidationResponse",
    # Service
    "NodeExecutionResult",
    "WorkflowExecutionResult",
    "WorkflowExecutionService",
    "get_workflow_execution_service",
    # Deadlock Detection (Sprint 7)
    "DeadlockDetector",
    "DeadlockInfo",
    "DeadlockResolutionStrategy",
    "TimeoutHandler",
    "WaitingTask",
    "get_deadlock_detector",
    "reset_deadlock_detector",
]
