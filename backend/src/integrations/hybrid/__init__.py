# =============================================================================
# IPA Platform - Hybrid Architecture Integration
# =============================================================================
# Phase 13: Hybrid Core Architecture
# Sprint 52: Intent Router & Mode Detection
# Sprint 53: Context Bridge & State Sync
# Sprint 54: HybridOrchestrator V2 Refactor
#
# This module provides the hybrid MAF + Claude SDK integration layer,
# enabling intelligent routing between workflow and chat execution modes.
#
# Key Components:
#   - IntentRouter: Intelligent intent analysis and mode detection (S52)
#   - ContextBridge: Cross-framework context synchronization (S53)
#   - UnifiedToolExecutor: Central tool execution with hooks (S54)
#   - HybridOrchestratorV2: Unified orchestration layer (S54)
#
# Dependencies:
#   - Claude SDK (src.integrations.claude_sdk)
#   - Agent Framework (src.integrations.agent_framework)
# =============================================================================

# Sprint 52: Intent Router
from src.integrations.hybrid.intent import (
    ExecutionMode,
    IntentAnalysis,
    IntentRouter,
    SessionContext,
)

# Sprint 53: Context Bridge
from src.integrations.hybrid.context import (
    ClaudeContext,
    ContextBridge,
    HybridContext,
    MAFContext,
    SyncDirection,
    SyncResult,
    SyncStrategy,
)

# Sprint 54: Unified Execution
from src.integrations.hybrid.execution import (
    MAFToolCallback,
    MAFToolResult,
    ToolExecutionResult,
    ToolRouter,
    ToolSource,
    UnifiedToolExecutor,
)

# Sprint 54: HybridOrchestrator V2
from src.integrations.hybrid.orchestrator_v2 import (
    ExecutionContextV2,
    HybridOrchestratorV2,
    HybridResultV2,
    OrchestratorConfig,
    OrchestratorMetrics,
    OrchestratorMode,
    create_orchestrator_v2,
)

# Sprint 81: Claude + MAF Fusion
from src.integrations.hybrid.claude_maf_fusion import (
    ClaudeMAFFusion,
    ClaudeDecisionEngine,
    DynamicWorkflow,
    WorkflowDefinition,
    WorkflowStep,
    WorkflowStepType,
    DecisionType,
    ClaudeDecision,
    ExecutionState,
    StepResult,
    WorkflowResult,
)

__all__ = [
    # Sprint 52: Intent Router
    "ExecutionMode",
    "IntentAnalysis",
    "IntentRouter",
    "SessionContext",
    # Sprint 53: Context Bridge
    "ContextBridge",
    "HybridContext",
    "MAFContext",
    "ClaudeContext",
    "SyncDirection",
    "SyncResult",
    "SyncStrategy",
    # Sprint 54: Unified Execution
    "UnifiedToolExecutor",
    "ToolSource",
    "ToolExecutionResult",
    "ToolRouter",
    "MAFToolCallback",
    "MAFToolResult",
    # Sprint 54: HybridOrchestrator V2
    "HybridOrchestratorV2",
    "OrchestratorMode",
    "OrchestratorConfig",
    "ExecutionContextV2",
    "HybridResultV2",
    "OrchestratorMetrics",
    "create_orchestrator_v2",
    # Sprint 81: Claude + MAF Fusion
    "ClaudeMAFFusion",
    "ClaudeDecisionEngine",
    "DynamicWorkflow",
    "WorkflowDefinition",
    "WorkflowStep",
    "WorkflowStepType",
    "DecisionType",
    "ClaudeDecision",
    "ExecutionState",
    "StepResult",
    "WorkflowResult",
]
