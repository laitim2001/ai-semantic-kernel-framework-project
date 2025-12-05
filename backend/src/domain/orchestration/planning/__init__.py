# =============================================================================
# IPA Platform - Planning Module
# =============================================================================
# Sprint 10: Dynamic Planning & Autonomous Decision (42 points)
#
# This module provides intelligent task decomposition, dynamic planning,
# autonomous decision-making, and trial-and-error learning capabilities.
#
# Components:
# - TaskDecomposer: Breaks down complex tasks into executable subtasks
# - DynamicPlanner: Creates and executes adaptive execution plans
# - AutonomousDecisionEngine: Makes intelligent decisions with explainability
# - TrialAndErrorEngine: Learns from failures and improves over time
# =============================================================================

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
