# =============================================================================
# IPA Platform - Claude Orchestrator
# =============================================================================
# Sprint 81: S81-1 - Claude 主導的多 Agent 協調 (10 pts)
#
# This module provides Claude-led multi-agent coordination capabilities.
#
# Architecture:
#   ┌─────────────────────────────────────────────────────────────┐
#   │                   Claude Orchestrator                        │
#   ├─────────────────────────────────────────────────────────────┤
#   │  1. ClaudeCoordinator                                       │
#   │     - 分析任務並選擇合適 Agent                                │
#   │     - 協調並行/串行執行                                       │
#   │     - 彙總執行結果                                           │
#   ├─────────────────────────────────────────────────────────────┤
#   │  2. TaskAllocator                                           │
#   │     - 分配子任務給 Agent                                     │
#   │     - 管理執行流程                                           │
#   │     - 處理超時和重試                                         │
#   ├─────────────────────────────────────────────────────────────┤
#   │  3. ContextManager                                          │
#   │     - 跨 Agent 上下文傳遞                                    │
#   │     - 結果合併                                               │
#   │     - 共享狀態管理                                           │
#   └─────────────────────────────────────────────────────────────┘
#
# Usage:
#   from src.integrations.claude_sdk.orchestrator import ClaudeCoordinator
#
#   coordinator = ClaudeCoordinator(claude_client)
#
#   # Register agents
#   coordinator.register_agent(AgentInfo(
#       agent_id="agent-1",
#       name="Database Agent",
#       capabilities=["database", "sql"],
#   ))
#
#   # Coordinate task
#   result = await coordinator.coordinate_agents(
#       task=ComplexTask(
#           task_id="task-1",
#           description="Analyze database performance",
#           requirements=["database", "monitoring"],
#       ),
#   )
# =============================================================================

from .types import (
    # Enums
    TaskComplexity,
    ExecutionMode,
    AgentStatus,
    SubtaskStatus,
    CoordinationStatus,
    # Data classes
    AgentInfo,
    ComplexTask,
    TaskAnalysis,
    Subtask,
    AgentSelection,
    SubtaskResult,
    CoordinationResult,
    CoordinationContext,
)

from .context_manager import ContextManager, ContextTransfer
from .task_allocator import TaskAllocator, AgentExecutor
from .coordinator import ClaudeCoordinator


__all__ = [
    # Enums
    "TaskComplexity",
    "ExecutionMode",
    "AgentStatus",
    "SubtaskStatus",
    "CoordinationStatus",
    # Data classes
    "AgentInfo",
    "ComplexTask",
    "TaskAnalysis",
    "Subtask",
    "AgentSelection",
    "SubtaskResult",
    "CoordinationResult",
    "CoordinationContext",
    # Context management
    "ContextManager",
    "ContextTransfer",
    # Task allocation
    "TaskAllocator",
    "AgentExecutor",
    # Main coordinator
    "ClaudeCoordinator",
]
