# =============================================================================
# IPA Platform - Workflows Domain Module
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
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
]
