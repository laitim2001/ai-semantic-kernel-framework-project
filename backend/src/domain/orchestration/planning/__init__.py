# =============================================================================
# IPA Platform - Planning Module
# =============================================================================
# Sprint 10: Dynamic Planning & Autonomous Decision (42 points)
# Sprint 30: 棄用警告 - 請使用適配器層
#
# DEPRECATED: 此模組已棄用，請使用適配器層
#
# 推薦使用:
#   from src.integrations.agent_framework.builders import (
#       PlanningAdapter,
#       TaskDecomposerAdapter,
#       DynamicPlannerAdapter,
#   )
#
# 或使用 API 服務:
#   from src.api.v1.planning.routes import planning_* endpoints
#
# 此模組將在未來版本中移除
# =============================================================================

import warnings

warnings.warn(
    "domain.orchestration.planning 模組已棄用。"
    "請使用 integrations.agent_framework.builders.PlanningAdapter",
    DeprecationWarning,
    stacklevel=2,
)

from .task_decomposer import (
    TaskDecomposer,
    TaskPriority,
    TaskStatus,
    DependencyType,
    SubTask,
    DecompositionResult,
)
from .dynamic_planner import (
    DynamicPlanner,
    PlanStatus,
    PlanEvent,
    PlanAdjustment,
    ExecutionPlan,
)
from .decision_engine import (
    AutonomousDecisionEngine,
    DecisionType,
    DecisionConfidence,
    DecisionOption,
    Decision,
)
from .trial_error import (
    TrialAndErrorEngine,
    TrialStatus,
    LearningType,
    Trial,
    LearningInsight,
)

__all__ = [
    # Task Decomposer
    "TaskDecomposer",
    "TaskPriority",
    "TaskStatus",
    "DependencyType",
    "SubTask",
    "DecompositionResult",
    # Dynamic Planner
    "DynamicPlanner",
    "PlanStatus",
    "PlanEvent",
    "PlanAdjustment",
    "ExecutionPlan",
    # Decision Engine
    "AutonomousDecisionEngine",
    "DecisionType",
    "DecisionConfidence",
    "DecisionOption",
    "Decision",
    # Trial and Error
    "TrialAndErrorEngine",
    "TrialStatus",
    "LearningType",
    "Trial",
    "LearningInsight",
]
