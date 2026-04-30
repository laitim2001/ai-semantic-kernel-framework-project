# =============================================================================
# IPA Platform - Claude Autonomous Planning Engine
# =============================================================================
# Sprint 79: S79-1 - Claude 自主規劃引擎 (13 pts)
# Sprint 80: S80-3 - Trial-and-Error 智能回退 (6 pts)
#
# This module provides autonomous planning capabilities for IT event handling.
#
# Architecture:
#   ┌─────────────────────────────────────────────────────────────┐
#   │                  Claude 自主規劃引擎                          │
#   ├─────────────────────────────────────────────────────────────┤
#   │  Phase 1: 分析 (Analyzer) → Extended Thinking               │
#   │  Phase 2: 規劃 (Planner) → 自主決策樹生成                    │
#   │  Phase 3: 執行 (Executor) → 工具調用和 Workflow 整合         │
#   │  Phase 4: 驗證 (Verifier) → 結果驗證和學習                   │
#   │  Fallback: 智能回退 (SmartFallback) → 錯誤恢復和重試         │
#   └─────────────────────────────────────────────────────────────┘
#
# Usage:
#   from src.integrations.claude_sdk.autonomous import (
#       AutonomousPlanner,
#       EventAnalyzer,
#       PlanExecutor,
#       ResultVerifier,
#   )
#
#   # Create planner
#   planner = AutonomousPlanner(client)
#
#   # Generate plan
#   plan = await planner.generate_plan(event_context)
#
#   # Execute plan
#   executor = PlanExecutor(tool_executors)
#   async for event in executor.execute_stream(plan):
#       print(event)
#
#   # Verify results
#   verifier = ResultVerifier(client)
#   result = await verifier.verify(plan)
# =============================================================================

from .types import (
    # Enums
    EventSeverity,
    EventComplexity,
    PlanStatus,
    StepStatus,
    RiskLevel,
    # Data classes
    EventContext,
    AnalysisResult,
    PlanStep,
    AutonomousPlan,
    VerificationResult,
    # Utilities
    COMPLEXITY_BUDGET_TOKENS,
    get_budget_tokens,
)

from .analyzer import EventAnalyzer
from .planner import AutonomousPlanner
from .executor import PlanExecutor, ExecutionEvent, ExecutionEventType
from .verifier import ResultVerifier

# Sprint 80: S80-3 - Trial-and-Error 智能回退
from .retry import (
    FailureType,
    RetryConfig,
    RetryAttempt,
    RetryResult,
    RetryPolicy,
    DEFAULT_RETRY_CONFIG,
    with_retry,
)
from .fallback import (
    FallbackStrategy,
    FailureAnalysis,
    FallbackAction,
    FailurePattern,
    FallbackResult,
    FallbackConfig,
    SmartFallback,
    DEFAULT_FALLBACK_CONFIG,
)


__all__ = [
    # Enums
    "EventSeverity",
    "EventComplexity",
    "PlanStatus",
    "StepStatus",
    "RiskLevel",
    # Data classes
    "EventContext",
    "AnalysisResult",
    "PlanStep",
    "AutonomousPlan",
    "VerificationResult",
    # Utilities
    "COMPLEXITY_BUDGET_TOKENS",
    "get_budget_tokens",
    # Core components
    "EventAnalyzer",
    "AutonomousPlanner",
    "PlanExecutor",
    "ExecutionEvent",
    "ExecutionEventType",
    "ResultVerifier",
    # Sprint 80: Retry and Fallback
    "FailureType",
    "RetryConfig",
    "RetryAttempt",
    "RetryResult",
    "RetryPolicy",
    "DEFAULT_RETRY_CONFIG",
    "with_retry",
    "FallbackStrategy",
    "FailureAnalysis",
    "FallbackAction",
    "FailurePattern",
    "FallbackResult",
    "FallbackConfig",
    "SmartFallback",
    "DEFAULT_FALLBACK_CONFIG",
]
