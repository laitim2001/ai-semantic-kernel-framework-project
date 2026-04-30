# =============================================================================
# IPA Platform - Nested Workflows Module
# =============================================================================
# Sprint 11: Nested Workflows & Advanced Orchestration
# Sprint 30: 棄用警告 - 請使用適配器層
#
# DEPRECATED: 此模組已棄用，請使用適配器層
#
# 推薦使用:
#   from src.integrations.agent_framework.builders import (
#       NestedWorkflowAdapter,
#       CompositionBuilderAdapter,
#   )
#
# 或使用 API 服務:
#   from src.api.v1.nested.routes import nested_* endpoints
#
# 此模組將在未來版本中移除
# =============================================================================

import warnings

warnings.warn(
    "domain.orchestration.nested 模組已棄用。"
    "請使用 integrations.agent_framework.builders.NestedWorkflowAdapter",
    DeprecationWarning,
    stacklevel=2,
)

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
