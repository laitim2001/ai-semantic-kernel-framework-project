# =============================================================================
# IPA Platform - Agent Framework Core Adapters
# =============================================================================
# Phase 5: MVP Core Official API Migration
# Sprint 26: Workflow Model Migration
# Sprint 27: Execution Engine Migration
# Sprint 28: Human Approval Migration
#
# This module provides adapters that connect the existing Phase 1 MVP
# domain models to the official Microsoft Agent Framework API:
#
#   Sprint 26:
#   - WorkflowNodeExecutor: Adapts WorkflowNode → Executor
#   - WorkflowEdgeAdapter: Adapts WorkflowEdge → Edge
#   - WorkflowDefinitionAdapter: Adapts WorkflowDefinition → Workflow
#   - WorkflowContextAdapter: Adapts WorkflowContext → official context
#
#   Sprint 27:
#   - SequentialOrchestrationAdapter: Sequential execution via official API
#   - ExecutorAgentWrapper: Adapts Executor → ChatAgent
#   - ExecutionAdapter: High-level execution interface
#
#   Sprint 28:
#   - HumanApprovalExecutor: Human-in-the-loop approval via RequestResponseExecutor
#   - ApprovalRequest/Response: Typed approval models
#   - EscalationPolicy: Timeout and escalation handling
#
# IMPORTANT: All adapters MUST use official Agent Framework imports:
#   from agent_framework.workflows import Executor, Edge, Workflow
#   from agent_framework.workflows import RequestResponseExecutor
#   from agent_framework.workflows.orchestrations import SequentialOrchestration
#
# Reference: .claude/skills/microsoft-agent-framework/references/workflows-api.md
# =============================================================================

from .executor import (
    NodeInput,
    NodeOutput,
    WorkflowNodeExecutor,
)

from .edge import (
    ConditionEvaluator,
    WorkflowEdgeAdapter,
    create_edge,
    create_edge_from_start,
    create_edge_to_end,
    convert_edges,
)

from .workflow import (
    WorkflowDefinitionAdapter,
    WorkflowRunResult,
    create_workflow_adapter,
    build_simple_workflow,
    build_branching_workflow,
)

from .context import (
    WorkflowContextAdapter,
    create_context,
    adapt_context,
    merge_contexts,
)

from .execution import (
    SequentialOrchestrationAdapter,
    SequentialExecutionResult,
    ExecutorAgentWrapper,
    ExecutionAdapter,
    ExecutionResult,
    ExecutionError,
    create_sequential_orchestration,
    create_execution_adapter,
    wrap_executor_as_agent,
)

from .events import (
    WorkflowStatusEventAdapter,
    ExecutionStatus,
    EventType,
    InternalExecutionEvent,
    EventFilter,
    create_event_adapter,
    create_event,
    create_event_filter,
)

from .state_machine import (
    EnhancedExecutionStateMachine,
    StateMachineManager,
    create_enhanced_state_machine,
    wrap_state_machine,
    EVENT_TO_DOMAIN_STATUS,
    DOMAIN_TO_EVENT_STATUS,
)

from .approval import (
    HumanApprovalExecutor,
    ApprovalRequest,
    ApprovalResponse,
    ApprovalStatus,
    ApprovalState,
    RiskLevel,
    EscalationPolicy,
    NotificationConfig,
    create_approval_executor,
    create_approval_request,
    create_approval_response,
)

from .approval_workflow import (
    WorkflowApprovalAdapter,
    ApprovalWorkflowManager,
    ApprovalWorkflowState,
    create_workflow_approval_adapter,
    create_approval_workflow_manager,
    quick_respond,
)

__all__ = [
    # S26-1: Executor
    "NodeInput",
    "NodeOutput",
    "WorkflowNodeExecutor",
    # S26-2: Edge
    "ConditionEvaluator",
    "WorkflowEdgeAdapter",
    "create_edge",
    "create_edge_from_start",
    "create_edge_to_end",
    "convert_edges",
    # S26-3: Workflow
    "WorkflowDefinitionAdapter",
    "WorkflowRunResult",
    "create_workflow_adapter",
    "build_simple_workflow",
    "build_branching_workflow",
    # S26-4: Context
    "WorkflowContextAdapter",
    "create_context",
    "adapt_context",
    "merge_contexts",
    # S27-1: Sequential Orchestration
    "SequentialOrchestrationAdapter",
    "SequentialExecutionResult",
    "ExecutorAgentWrapper",
    "ExecutionAdapter",
    "ExecutionResult",
    "ExecutionError",
    "create_sequential_orchestration",
    "create_execution_adapter",
    "wrap_executor_as_agent",
    # S27-2: Workflow Status Events
    "WorkflowStatusEventAdapter",
    "ExecutionStatus",
    "EventType",
    "InternalExecutionEvent",
    "EventFilter",
    "create_event_adapter",
    "create_event",
    "create_event_filter",
    # S27-3: Enhanced State Machine
    "EnhancedExecutionStateMachine",
    "StateMachineManager",
    "create_enhanced_state_machine",
    "wrap_state_machine",
    "EVENT_TO_DOMAIN_STATUS",
    "DOMAIN_TO_EVENT_STATUS",
    # S28-1: Human Approval Executor
    "HumanApprovalExecutor",
    "ApprovalRequest",
    "ApprovalResponse",
    "ApprovalStatus",
    "ApprovalState",
    "RiskLevel",
    "EscalationPolicy",
    "NotificationConfig",
    "create_approval_executor",
    "create_approval_request",
    "create_approval_response",
    # S28-4: Approval Workflow Integration
    "WorkflowApprovalAdapter",
    "ApprovalWorkflowManager",
    "ApprovalWorkflowState",
    "create_workflow_approval_adapter",
    "create_approval_workflow_manager",
    "quick_respond",
]
