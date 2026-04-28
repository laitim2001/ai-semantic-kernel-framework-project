# =============================================================================
# IPA Platform - Workflows Domain Module
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
# Sprint 7: Concurrent Execution Engine (Phase 2)
#
# Domain module for workflow management and execution.
# Note: Uses lazy imports for service to avoid circular imports
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

from src.domain.workflows.deadlock_detector import (
    DeadlockDetector,
    DeadlockInfo,
    DeadlockResolutionStrategy,
    TimeoutHandler,
    WaitingTask,
    get_deadlock_detector,
    reset_deadlock_detector,
)


# Lazy imports for service module to avoid circular imports
# These are imported when first accessed via __getattr__
def __getattr__(name: str):
    """Lazy import service classes to avoid circular imports."""
    if name in ("NodeExecutionResult", "WorkflowExecutionResult",
                "WorkflowExecutionService", "get_workflow_execution_service"):
        from src.domain.workflows.service import (
            NodeExecutionResult,
            WorkflowExecutionResult,
            WorkflowExecutionService,
            get_workflow_execution_service,
        )
        return {
            "NodeExecutionResult": NodeExecutionResult,
            "WorkflowExecutionResult": WorkflowExecutionResult,
            "WorkflowExecutionService": WorkflowExecutionService,
            "get_workflow_execution_service": get_workflow_execution_service,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

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
