# =============================================================================
# IPA Platform - Nested Workflows Module
# =============================================================================
# Sprint 11: Nested Workflows & Advanced Orchestration
#
# This module provides nested workflow capabilities including:
# - Nested workflow management
# - Sub-workflow execution
# - Recursive pattern handling
# - Workflow composition building
# - Context propagation
# =============================================================================

from .workflow_manager import (
    NestedWorkflowType,
    WorkflowScope,
    NestedWorkflowConfig,
    SubWorkflowReference,
    NestedExecutionContext,
    NestedWorkflowManager,
)
from .sub_executor import (
    SubWorkflowExecutionMode,
    SubExecutionState,
    SubWorkflowExecutor,
)
from .recursive_handler import (
    RecursionStrategy,
    TerminationType,
    RecursionConfig,
    RecursionState,
    RecursivePatternHandler,
)
from .composition_builder import (
    CompositionType,
    WorkflowNode,
    CompositionBlock,
    WorkflowCompositionBuilder,
)
from .context_propagation import (
    PropagationType,
    VariableScopeType,
    DataFlowDirection,
    VariableDescriptor,
    PropagationRule,
    DataFlowEvent,
    VariableScope,
    ContextPropagator,
    DataFlowTracker,
)

__all__ = [
    # Workflow Manager
    "NestedWorkflowType",
    "WorkflowScope",
    "NestedWorkflowConfig",
    "SubWorkflowReference",
    "NestedExecutionContext",
    "NestedWorkflowManager",
    # Sub Executor
    "SubWorkflowExecutionMode",
    "SubExecutionState",
    "SubWorkflowExecutor",
    # Recursive Handler
    "RecursionStrategy",
    "TerminationType",
    "RecursionConfig",
    "RecursionState",
    "RecursivePatternHandler",
    # Composition Builder
    "CompositionType",
    "WorkflowNode",
    "CompositionBlock",
    "WorkflowCompositionBuilder",
    # Context Propagation
    "PropagationType",
    "VariableScopeType",
    "DataFlowDirection",
    "VariableDescriptor",
    "PropagationRule",
    "DataFlowEvent",
    "VariableScope",
    "ContextPropagator",
    "DataFlowTracker",
]
