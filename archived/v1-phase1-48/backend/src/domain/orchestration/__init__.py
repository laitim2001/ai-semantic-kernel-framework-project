# =============================================================================
# IPA Platform - Orchestration Module
# =============================================================================
# Sprint 25: 清理、測試、文檔 (Phase 4 最後一個 Sprint)
#
# DEPRECATED - 此模組已遷移到適配器層
#
# 已遷移的模組:
#   - groupchat/ -> integrations/agent_framework/builders/groupchat.py
#   - handoff/ -> integrations/agent_framework/builders/handoff.py
#   - collaboration/ -> 已整合到 GroupChatBuilderAdapter
#
# 保留的擴展功能:
#   - nested/ - 上下文傳播和遞歸處理
#   - planning/ - 任務分解和決策引擎
#   - memory/ - 後端存儲實現
#   - multiturn/ - 會話管理
#
# 請使用適配器層進行新開發:
#   from src.integrations.agent_framework.builders import (
#       GroupChatBuilderAdapter,
#       HandoffBuilderAdapter,
#       ConcurrentBuilderAdapter,
#       NestedWorkflowAdapter,
#       PlanningAdapter,
#       MultiTurnAdapter,
#   )
# =============================================================================

import warnings

# 發出棄用警告
warnings.warn(
    "domain.orchestration 模組已棄用。"
    "請使用 integrations.agent_framework.builders 中的適配器。",
    DeprecationWarning,
    stacklevel=2,
)

# 保留的模組導出 (擴展功能)
from src.domain.orchestration.nested import (
    CompositionType,
    NestedWorkflowConfig,
    NestedWorkflowManager,
    NestedWorkflowType,
    PropagationType,
    RecursionStrategy,
    RecursivePatternHandler,
    SubWorkflowExecutionMode,
    SubWorkflowExecutor,
    TerminationType,
    WorkflowCompositionBuilder,
    WorkflowScope,
)

from src.domain.orchestration.planning import (
    TaskDecomposer,
    DynamicPlanner,
    AutonomousDecisionEngine,
    TrialAndErrorEngine,
    DecisionType,
    PlanStatus,
)

from src.domain.orchestration.memory import (
    InMemoryConversationMemoryStore,
    ConversationSession,
    ConversationTurn,
    ConversationMemoryStore,
)

from src.domain.orchestration.multiturn import (
    MultiTurnSessionManager,
    MultiTurnSession,
    SessionStatus,
)

__all__ = [
    # Nested Workflow (擴展功能 - 保留)
    "CompositionType",
    "NestedWorkflowConfig",
    "NestedWorkflowManager",
    "NestedWorkflowType",
    "PropagationType",
    "RecursionStrategy",
    "RecursivePatternHandler",
    "SubWorkflowExecutionMode",
    "SubWorkflowExecutor",
    "TerminationType",
    "WorkflowCompositionBuilder",
    "WorkflowScope",
    # Planning (擴展功能 - 保留)
    "TaskDecomposer",
    "DynamicPlanner",
    "AutonomousDecisionEngine",
    "TrialAndErrorEngine",
    "DecisionType",
    "PlanStatus",
    # Memory (後端實現 - 保留)
    "InMemoryConversationMemoryStore",
    "ConversationSession",
    "ConversationTurn",
    "ConversationMemoryStore",
    # Multi-turn (會話管理 - 保留)
    "MultiTurnSessionManager",
    "MultiTurnSession",
    "SessionStatus",
]
