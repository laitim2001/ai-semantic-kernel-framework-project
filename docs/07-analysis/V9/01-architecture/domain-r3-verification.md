# Domain Layer (R3) — Programmatic Verification Report

> **Generated**: 2026-03-29 | **Source**: `backend-metadata.json` (AST scan)
> **Scope**: All files under `backend/src/domain/`
> **Comparand**: `layer-10-domain.md` (V9 Deep Architecture Analysis)

---

## 1. Overall Summary

| Metric | Value |
|--------|-------|
| Total Files | 117 |
| Code Files (non-init) | 86 |
| `__init__.py` Files | 31 |
| Total LOC | 47,637 |
| Total Classes (AST) | 392 |
| Total Functions (AST) | 60 |
| Sub-module Directories | 21 (+1 root) |

## 2. V9 Claim vs Metadata — Top-Level

| Metric | V9 Claimed | Actual (Metadata) | Match? |
|--------|-----------|-------------------|--------|
| Total Python Files | 117 | 117 | EXACT |
| Total LOC | ~47,637 | 47,637 | EXACT |
| Total Modules | 21 dirs + 1 root | 21 dirs + 1 root | EXACT |
| Critical Module | sessions/ (33 files, ~15,473 LOC) | sessions/ (33 files, 15,473 LOC) | see below |
| Deprecated Module | orchestration/ (22 files, ~11,465 LOC) | orchestration/ (22 files, 11,465 LOC) | see below |

**Verdict**: V9 top-level claims are **fully confirmed** by programmatic scan.

## 3. Per-Module Breakdown with V9 Comparison

| Module | V9 Files | Actual Files | V9 ~LOC | Actual LOC | Files Match | LOC Delta |
|--------|----------|-------------|---------|-----------|-------------|-----------|
| `agents` | 7 | 7 | 2,500 | 1,904 | EXACT | -596 |
| `audit` | 2 | 2 | 400 | 758 | EXACT | +358 |
| `auth` | 3 | 3 | 600 | 350 | EXACT | -250 |
| `chat_history` | 2 | 2 | 300 | 80 | EXACT | -220 |
| `checkpoints` | 3 | 3 | 1,500 | 1,017 | EXACT | -483 |
| `connectors` | 6 | 6 | 1,800 | 3,680 | EXACT | +1,880 |
| `devtools` | 2 | 2 | 350 | 801 | EXACT | +451 |
| `executions` | 2 | 2 | 800 | 465 | EXACT | -335 |
| `files` | 3 | 3 | 600 | 554 | EXACT | -46 |
| `learning` | 2 | 2 | 400 | 678 | EXACT | +278 |
| `notifications` | 2 | 2 | 400 | 814 | EXACT | +414 |
| `orchestration` | 22 | 22 | 11,465 | 11,465 | EXACT | 0 |
| `prompts` | 2 | 2 | 400 | 597 | EXACT | +197 |
| `routing` | 2 | 2 | 400 | 687 | EXACT | +287 |
| `sandbox` | 2 | 2 | 300 | 363 | EXACT | +63 |
| `sessions` | 33 | 33 | 15,473 | 15,473 | EXACT | 0 |
| `tasks` | 2 | 3 | 300 | 343 | DIFF (+1) | +43 |
| `templates` | 3 | 3 | 700 | 944 | EXACT | +244 |
| `triggers` | 2 | 2 | 500 | 679 | EXACT | +179 |
| `versioning` | 2 | 2 | 400 | 769 | EXACT | +369 |
| `workflows` | 11 | 11 | 5,500 | 5,215 | EXACT | -285 |

**File count match rate**: 20/21 modules (95%)
**Mismatched modules**: tasks

## 4. Detailed File Listings Per Module

### Module: `domain/(root)`

**Summary**: 1 files, 1 LOC, 0 classes, 0 functions

| # | File Path | LOC | Classes | Functions |
|---|-----------|-----|---------|-----------|
| 1 | `src/domain/__init__.py` | 1 | 0 | 0 |

### Module: `domain/agents`

**Summary**: 7 files, 1,904 LOC, 20 classes, 10 functions

| # | File Path | LOC | Classes | Functions |
|---|-----------|-----|---------|-----------|
| 1 | `src/domain/agents/__init__.py` | 29 | 0 | 0 |
| 2 | `src/domain/agents/schemas.py` | 156 | 10 | 0 |
| 3 | `src/domain/agents/service.py` | 341 | 3 | 2 |
| 4 | `src/domain/agents/tools/__init__.py` | 63 | 0 | 0 |
| 5 | `src/domain/agents/tools/base.py` | 382 | 4 | 3 |
| 6 | `src/domain/agents/tools/builtin.py` | 557 | 2 | 3 |
| 7 | `src/domain/agents/tools/registry.py` | 376 | 1 | 2 |

**Classes in `domain/agents`**:

- `AgentConfig` -- `src/domain/agents/service.py`
- `AgentCreateRequest` -- `src/domain/agents/schemas.py`
- `AgentExecutionResult` -- `src/domain/agents/service.py`
- `AgentListResponse` -- `src/domain/agents/schemas.py`
- `AgentResponse` -- `src/domain/agents/schemas.py`
- `AgentRunRequest` -- `src/domain/agents/schemas.py`
- `AgentRunResponse` -- `src/domain/agents/schemas.py`
- `AgentService` -- `src/domain/agents/service.py`
- `AgentUpdateRequest` -- `src/domain/agents/schemas.py`
- `BaseTool` -- `src/domain/agents/tools/base.py`
- `Config` -- `src/domain/agents/schemas.py`
- `Config` -- `src/domain/agents/schemas.py`
- `Config` -- `src/domain/agents/schemas.py`
- `Config` -- `src/domain/agents/schemas.py`
- `DateTimeTool` -- `src/domain/agents/tools/builtin.py`
- `FunctionTool` -- `src/domain/agents/tools/base.py`
- `HttpTool` -- `src/domain/agents/tools/builtin.py`
- `ToolError` -- `src/domain/agents/tools/base.py`
- `ToolRegistry` -- `src/domain/agents/tools/registry.py`
- `ToolResult` -- `src/domain/agents/tools/base.py`

### Module: `domain/audit`

**Summary**: 2 files, 758 LOC, 7 classes, 0 functions

| # | File Path | LOC | Classes | Functions |
|---|-----------|-----|---------|-----------|
| 1 | `src/domain/audit/__init__.py` | 30 | 0 | 0 |
| 2 | `src/domain/audit/logger.py` | 728 | 7 | 0 |

**Classes in `domain/audit`**:

- `AuditAction` -- `src/domain/audit/logger.py`
- `AuditEntry` -- `src/domain/audit/logger.py`
- `AuditError` -- `src/domain/audit/logger.py`
- `AuditLogger` -- `src/domain/audit/logger.py`
- `AuditQueryParams` -- `src/domain/audit/logger.py`
- `AuditResource` -- `src/domain/audit/logger.py`
- `AuditSeverity` -- `src/domain/audit/logger.py`

### Module: `domain/auth`

**Summary**: 3 files, 350 LOC, 7 classes, 0 functions

| # | File Path | LOC | Classes | Functions |
|---|-----------|-----|---------|-----------|
| 1 | `src/domain/auth/__init__.py` | 30 | 0 | 0 |
| 2 | `src/domain/auth/schemas.py` | 81 | 6 | 0 |
| 3 | `src/domain/auth/service.py` | 239 | 1 | 0 |

**Classes in `domain/auth`**:

- `AuthService` -- `src/domain/auth/service.py`
- `PasswordChange` -- `src/domain/auth/schemas.py`
- `TokenRefresh` -- `src/domain/auth/schemas.py`
- `TokenResponse` -- `src/domain/auth/schemas.py`
- `UserCreate` -- `src/domain/auth/schemas.py`
- `UserLogin` -- `src/domain/auth/schemas.py`
- `UserResponse` -- `src/domain/auth/schemas.py`

### Module: `domain/chat_history`

**Summary**: 2 files, 80 LOC, 3 classes, 0 functions

| # | File Path | LOC | Classes | Functions |
|---|-----------|-----|---------|-----------|
| 1 | `src/domain/chat_history/__init__.py` | 13 | 0 | 0 |
| 2 | `src/domain/chat_history/models.py` | 67 | 3 | 0 |

**Classes in `domain/chat_history`**:

- `ChatHistorySync` -- `src/domain/chat_history/models.py`
- `ChatMessage` -- `src/domain/chat_history/models.py`
- `ChatSyncResponse` -- `src/domain/chat_history/models.py`

### Module: `domain/checkpoints`

**Summary**: 3 files, 1,017 LOC, 5 classes, 0 functions

| # | File Path | LOC | Classes | Functions |
|---|-----------|-----|---------|-----------|
| 1 | `src/domain/checkpoints/__init__.py` | 41 | 0 | 0 |
| 2 | `src/domain/checkpoints/service.py` | 676 | 3 | 0 |
| 3 | `src/domain/checkpoints/storage.py` | 300 | 2 | 0 |

**Classes in `domain/checkpoints`**:

- `CheckpointData` -- `src/domain/checkpoints/service.py`
- `CheckpointService` -- `src/domain/checkpoints/service.py`
- `CheckpointStatus` -- `src/domain/checkpoints/service.py`
- `CheckpointStorage` -- `src/domain/checkpoints/storage.py`
- `DatabaseCheckpointStorage` -- `src/domain/checkpoints/storage.py`

### Module: `domain/connectors`

**Summary**: 6 files, 3,680 LOC, 10 classes, 2 functions

| # | File Path | LOC | Classes | Functions |
|---|-----------|-----|---------|-----------|
| 1 | `src/domain/connectors/__init__.py` | 57 | 0 | 0 |
| 2 | `src/domain/connectors/base.py` | 480 | 6 | 0 |
| 3 | `src/domain/connectors/dynamics365.py` | 920 | 1 | 0 |
| 4 | `src/domain/connectors/registry.py` | 441 | 1 | 2 |
| 5 | `src/domain/connectors/servicenow.py` | 812 | 1 | 0 |
| 6 | `src/domain/connectors/sharepoint.py` | 970 | 1 | 0 |

**Classes in `domain/connectors`**:

- `AuthType` -- `src/domain/connectors/base.py`
- `BaseConnector` -- `src/domain/connectors/base.py`
- `ConnectorConfig` -- `src/domain/connectors/base.py`
- `ConnectorError` -- `src/domain/connectors/base.py`
- `ConnectorRegistry` -- `src/domain/connectors/registry.py`
- `ConnectorResponse` -- `src/domain/connectors/base.py`
- `ConnectorStatus` -- `src/domain/connectors/base.py`
- `Dynamics365Connector` -- `src/domain/connectors/dynamics365.py`
- `ServiceNowConnector` -- `src/domain/connectors/servicenow.py`
- `SharePointConnector` -- `src/domain/connectors/sharepoint.py`

### Module: `domain/devtools`

**Summary**: 2 files, 801 LOC, 9 classes, 0 functions

| # | File Path | LOC | Classes | Functions |
|---|-----------|-----|---------|-----------|
| 1 | `src/domain/devtools/__init__.py` | 24 | 0 | 0 |
| 2 | `src/domain/devtools/tracer.py` | 777 | 9 | 0 |

**Classes in `domain/devtools`**:

- `ExecutionTrace` -- `src/domain/devtools/tracer.py`
- `ExecutionTracer` -- `src/domain/devtools/tracer.py`
- `TimelineEntry` -- `src/domain/devtools/tracer.py`
- `TraceEvent` -- `src/domain/devtools/tracer.py`
- `TraceEventType` -- `src/domain/devtools/tracer.py`
- `TraceSeverity` -- `src/domain/devtools/tracer.py`
- `TraceSpan` -- `src/domain/devtools/tracer.py`
- `TraceStatistics` -- `src/domain/devtools/tracer.py`
- `TracerError` -- `src/domain/devtools/tracer.py`

### Module: `domain/executions`

**Summary**: 2 files, 465 LOC, 3 classes, 2 functions

| # | File Path | LOC | Classes | Functions |
|---|-----------|-----|---------|-----------|
| 1 | `src/domain/executions/__init__.py` | 37 | 0 | 0 |
| 2 | `src/domain/executions/state_machine.py` | 428 | 3 | 2 |

**Classes in `domain/executions`**:

- `ExecutionStateMachine` -- `src/domain/executions/state_machine.py`
- `ExecutionStatus` -- `src/domain/executions/state_machine.py`
- `InvalidStateTransitionError` -- `src/domain/executions/state_machine.py`

### Module: `domain/files`

**Summary**: 3 files, 554 LOC, 3 classes, 2 functions

| # | File Path | LOC | Classes | Functions |
|---|-----------|-----|---------|-----------|
| 1 | `src/domain/files/__init__.py` | 13 | 0 | 0 |
| 2 | `src/domain/files/service.py` | 318 | 2 | 1 |
| 3 | `src/domain/files/storage.py` | 223 | 1 | 1 |

**Classes in `domain/files`**:

- `FileService` -- `src/domain/files/service.py`
- `FileStorage` -- `src/domain/files/storage.py`
- `FileValidationError` -- `src/domain/files/service.py`

### Module: `domain/learning`

**Summary**: 2 files, 678 LOC, 5 classes, 0 functions

| # | File Path | LOC | Classes | Functions |
|---|-----------|-----|---------|-----------|
| 1 | `src/domain/learning/__init__.py` | 31 | 0 | 0 |
| 2 | `src/domain/learning/service.py` | 647 | 5 | 0 |

**Classes in `domain/learning`**:

- `CaseStatus` -- `src/domain/learning/service.py`
- `LearningCase` -- `src/domain/learning/service.py`
- `LearningError` -- `src/domain/learning/service.py`
- `LearningService` -- `src/domain/learning/service.py`
- `LearningStatistics` -- `src/domain/learning/service.py`

### Module: `domain/notifications`

**Summary**: 2 files, 814 LOC, 7 classes, 0 functions

| # | File Path | LOC | Classes | Functions |
|---|-----------|-----|---------|-----------|
| 1 | `src/domain/notifications/__init__.py` | 39 | 0 | 0 |
| 2 | `src/domain/notifications/teams.py` | 775 | 7 | 0 |

**Classes in `domain/notifications`**:

- `NotificationError` -- `src/domain/notifications/teams.py`
- `NotificationPriority` -- `src/domain/notifications/teams.py`
- `NotificationResult` -- `src/domain/notifications/teams.py`
- `NotificationType` -- `src/domain/notifications/teams.py`
- `TeamsCard` -- `src/domain/notifications/teams.py`
- `TeamsNotificationConfig` -- `src/domain/notifications/teams.py`
- `TeamsNotificationService` -- `src/domain/notifications/teams.py`

### Module: `domain/orchestration`

**Summary**: 22 files, 11,465 LOC, 82 classes, 9 functions

| # | File Path | LOC | Classes | Functions |
|---|-----------|-----|---------|-----------|
| 1 | `src/domain/orchestration/__init__.py` | 108 | 0 | 0 |
| 2 | `src/domain/orchestration/memory/__init__.py` | 54 | 0 | 0 |
| 3 | `src/domain/orchestration/memory/base.py` | 414 | 1 | 0 |
| 4 | `src/domain/orchestration/memory/in_memory.py` | 331 | 1 | 0 |
| 5 | `src/domain/orchestration/memory/models.py` | 277 | 4 | 0 |
| 6 | `src/domain/orchestration/memory/postgres_store.py` | 542 | 2 | 0 |
| 7 | `src/domain/orchestration/memory/redis_store.py` | 480 | 2 | 0 |
| 8 | `src/domain/orchestration/multiturn/__init__.py` | 57 | 0 | 0 |
| 9 | `src/domain/orchestration/multiturn/context_manager.py` | 526 | 3 | 0 |
| 10 | `src/domain/orchestration/multiturn/session_manager.py` | 823 | 4 | 1 |
| 11 | `src/domain/orchestration/multiturn/turn_tracker.py` | 456 | 4 | 0 |
| 12 | `src/domain/orchestration/nested/__init__.py` | 101 | 0 | 0 |
| 13 | `src/domain/orchestration/nested/composition_builder.py` | 771 | 4 | 0 |
| 14 | `src/domain/orchestration/nested/context_propagation.py` | 1000 | 9 | 3 |
| 15 | `src/domain/orchestration/nested/recursive_handler.py` | 695 | 5 | 0 |
| 16 | `src/domain/orchestration/nested/sub_executor.py` | 640 | 5 | 0 |
| 17 | `src/domain/orchestration/nested/workflow_manager.py` | 947 | 8 | 3 |
| 18 | `src/domain/orchestration/planning/__init__.py` | 87 | 0 | 0 |
| 19 | `src/domain/orchestration/planning/decision_engine.py` | 724 | 7 | 0 |
| 20 | `src/domain/orchestration/planning/dynamic_planner.py` | 748 | 7 | 2 |
| 21 | `src/domain/orchestration/planning/task_decomposer.py` | 791 | 9 | 0 |
| 22 | `src/domain/orchestration/planning/trial_error.py` | 893 | 7 | 0 |

**Classes in `domain/orchestration`**:

- `AgentRegistryProtocol` -- `src/domain/orchestration/planning/task_decomposer.py`
- `AutonomousDecisionEngine` -- `src/domain/orchestration/planning/decision_engine.py`
- `CheckpointServiceProtocol` -- `src/domain/orchestration/nested/sub_executor.py`
- `CompositionBlock` -- `src/domain/orchestration/nested/composition_builder.py`
- `CompositionType` -- `src/domain/orchestration/nested/composition_builder.py`
- `ContextEntry` -- `src/domain/orchestration/multiturn/context_manager.py`
- `ContextPropagator` -- `src/domain/orchestration/nested/context_propagation.py`
- `ContextScope` -- `src/domain/orchestration/multiturn/context_manager.py`
- `ConversationMemoryStore` -- `src/domain/orchestration/memory/base.py`
- `ConversationSession` -- `src/domain/orchestration/memory/models.py`
- `ConversationTurn` -- `src/domain/orchestration/memory/models.py`
- `DataFlowDirection` -- `src/domain/orchestration/nested/context_propagation.py`
- `DataFlowEvent` -- `src/domain/orchestration/nested/context_propagation.py`
- `DataFlowTracker` -- `src/domain/orchestration/nested/context_propagation.py`
- `DatabaseSessionProtocol` -- `src/domain/orchestration/memory/postgres_store.py`
- `Decision` -- `src/domain/orchestration/planning/decision_engine.py`
- `DecisionConfidence` -- `src/domain/orchestration/planning/decision_engine.py`
- `DecisionEngineProtocol` -- `src/domain/orchestration/planning/dynamic_planner.py`
- `DecisionOption` -- `src/domain/orchestration/planning/decision_engine.py`
- `DecisionRule` -- `src/domain/orchestration/planning/decision_engine.py`
- `DecisionType` -- `src/domain/orchestration/planning/decision_engine.py`
- `DecompositionResult` -- `src/domain/orchestration/planning/task_decomposer.py`
- `DecompositionStrategy` -- `src/domain/orchestration/planning/task_decomposer.py`
- `DependencyType` -- `src/domain/orchestration/planning/task_decomposer.py`
- `DynamicPlanner` -- `src/domain/orchestration/planning/dynamic_planner.py`
- `ErrorFix` -- `src/domain/orchestration/planning/trial_error.py`
- `ExecutionPlan` -- `src/domain/orchestration/planning/dynamic_planner.py`
- `ExecutionServiceProtocol` -- `src/domain/orchestration/nested/workflow_manager.py`
- `InMemoryConversationMemoryStore` -- `src/domain/orchestration/memory/in_memory.py`
- `LLMServiceProtocol` -- `src/domain/orchestration/planning/decision_engine.py`
- `LLMServiceProtocol` -- `src/domain/orchestration/planning/dynamic_planner.py`
- `LLMServiceProtocol` -- `src/domain/orchestration/planning/task_decomposer.py`
- `LLMServiceProtocol` -- `src/domain/orchestration/planning/trial_error.py`
- `LearningInsight` -- `src/domain/orchestration/planning/trial_error.py`
- `LearningType` -- `src/domain/orchestration/planning/trial_error.py`
- `MessageRecord` -- `src/domain/orchestration/memory/models.py`
- `MultiTurnSession` -- `src/domain/orchestration/multiturn/session_manager.py`
- `MultiTurnSessionManager` -- `src/domain/orchestration/multiturn/session_manager.py`
- `NestedExecutionContext` -- `src/domain/orchestration/nested/workflow_manager.py`
- `NestedWorkflowConfig` -- `src/domain/orchestration/nested/workflow_manager.py`
- `NestedWorkflowManager` -- `src/domain/orchestration/nested/workflow_manager.py`
- `NestedWorkflowType` -- `src/domain/orchestration/nested/workflow_manager.py`
- `PlanAdjustment` -- `src/domain/orchestration/planning/dynamic_planner.py`
- `PlanEvent` -- `src/domain/orchestration/planning/dynamic_planner.py`
- `PlanStatus` -- `src/domain/orchestration/planning/dynamic_planner.py`
- `PostgresConversationMemoryStore` -- `src/domain/orchestration/memory/postgres_store.py`
- `PropagationRule` -- `src/domain/orchestration/nested/context_propagation.py`
- `PropagationType` -- `src/domain/orchestration/nested/context_propagation.py`
- `RecursionConfig` -- `src/domain/orchestration/nested/recursive_handler.py`
- `RecursionState` -- `src/domain/orchestration/nested/recursive_handler.py`
- `RecursionStrategy` -- `src/domain/orchestration/nested/recursive_handler.py`
- `RecursivePatternHandler` -- `src/domain/orchestration/nested/recursive_handler.py`
- `RedisClientProtocol` -- `src/domain/orchestration/memory/redis_store.py`
- `RedisConversationMemoryStore` -- `src/domain/orchestration/memory/redis_store.py`
- `SessionContextManager` -- `src/domain/orchestration/multiturn/context_manager.py`
- `SessionMessage` -- `src/domain/orchestration/multiturn/session_manager.py`
- `SessionStatus` -- `src/domain/orchestration/memory/models.py`
- `SessionStatus` -- `src/domain/orchestration/multiturn/session_manager.py`
- `SubExecutionState` -- `src/domain/orchestration/nested/sub_executor.py`
- `SubTask` -- `src/domain/orchestration/planning/task_decomposer.py`
- `SubWorkflowExecutionMode` -- `src/domain/orchestration/nested/sub_executor.py`
- `SubWorkflowExecutor` -- `src/domain/orchestration/nested/sub_executor.py`
- `SubWorkflowReference` -- `src/domain/orchestration/nested/workflow_manager.py`
- `TaskDecomposer` -- `src/domain/orchestration/planning/task_decomposer.py`
- `TaskPriority` -- `src/domain/orchestration/planning/task_decomposer.py`
- `TaskStatus` -- `src/domain/orchestration/planning/task_decomposer.py`
- `TerminationType` -- `src/domain/orchestration/nested/recursive_handler.py`
- `Trial` -- `src/domain/orchestration/planning/trial_error.py`
- `TrialAndErrorEngine` -- `src/domain/orchestration/planning/trial_error.py`
- `TrialStatus` -- `src/domain/orchestration/planning/trial_error.py`
- `Turn` -- `src/domain/orchestration/multiturn/turn_tracker.py`
- `TurnMessage` -- `src/domain/orchestration/multiturn/turn_tracker.py`
- `TurnStatus` -- `src/domain/orchestration/multiturn/turn_tracker.py`
- `TurnTracker` -- `src/domain/orchestration/multiturn/turn_tracker.py`
- `VariableDescriptor` -- `src/domain/orchestration/nested/context_propagation.py`
- `VariableScope` -- `src/domain/orchestration/nested/context_propagation.py`
- `VariableScopeType` -- `src/domain/orchestration/nested/context_propagation.py`
- `WorkflowCompositionBuilder` -- `src/domain/orchestration/nested/composition_builder.py`
- `WorkflowEngineProtocol` -- `src/domain/orchestration/nested/sub_executor.py`
- `WorkflowNode` -- `src/domain/orchestration/nested/composition_builder.py`
- `WorkflowScope` -- `src/domain/orchestration/nested/workflow_manager.py`
- `WorkflowServiceProtocol` -- `src/domain/orchestration/nested/workflow_manager.py`

### Module: `domain/prompts`

**Summary**: 2 files, 597 LOC, 7 classes, 0 functions

| # | File Path | LOC | Classes | Functions |
|---|-----------|-----|---------|-----------|
| 1 | `src/domain/prompts/__init__.py` | 30 | 0 | 0 |
| 2 | `src/domain/prompts/template.py` | 567 | 7 | 0 |

**Classes in `domain/prompts`**:

- `PromptCategory` -- `src/domain/prompts/template.py`
- `PromptTemplate` -- `src/domain/prompts/template.py`
- `PromptTemplateError` -- `src/domain/prompts/template.py`
- `PromptTemplateManager` -- `src/domain/prompts/template.py`
- `TemplateNotFoundError` -- `src/domain/prompts/template.py`
- `TemplateRenderError` -- `src/domain/prompts/template.py`
- `TemplateValidationError` -- `src/domain/prompts/template.py`

### Module: `domain/routing`

**Summary**: 2 files, 687 LOC, 7 classes, 1 functions

| # | File Path | LOC | Classes | Functions |
|---|-----------|-----|---------|-----------|
| 1 | `src/domain/routing/__init__.py` | 43 | 0 | 0 |
| 2 | `src/domain/routing/scenario_router.py` | 644 | 7 | 1 |

**Classes in `domain/routing`**:

- `ExecutionRelation` -- `src/domain/routing/scenario_router.py`
- `RelationType` -- `src/domain/routing/scenario_router.py`
- `RoutingError` -- `src/domain/routing/scenario_router.py`
- `RoutingResult` -- `src/domain/routing/scenario_router.py`
- `Scenario` -- `src/domain/routing/scenario_router.py`
- `ScenarioConfig` -- `src/domain/routing/scenario_router.py`
- `ScenarioRouter` -- `src/domain/routing/scenario_router.py`

### Module: `domain/sandbox`

**Summary**: 2 files, 363 LOC, 5 classes, 0 functions

| # | File Path | LOC | Classes | Functions |
|---|-----------|-----|---------|-----------|
| 1 | `src/domain/sandbox/__init__.py` | 19 | 0 | 0 |
| 2 | `src/domain/sandbox/service.py` | 344 | 5 | 0 |

**Classes in `domain/sandbox`**:

- `IPCMessageType` -- `src/domain/sandbox/service.py`
- `IPCResponse` -- `src/domain/sandbox/service.py`
- `SandboxProcess` -- `src/domain/sandbox/service.py`
- `SandboxService` -- `src/domain/sandbox/service.py`
- `SandboxStatus` -- `src/domain/sandbox/service.py`

### Module: `domain/sessions`

**Summary**: 33 files, 15,473 LOC, 123 classes, 18 functions

| # | File Path | LOC | Classes | Functions |
|---|-----------|-----|---------|-----------|
| 1 | `src/domain/sessions/__init__.py` | 176 | 0 | 0 |
| 2 | `src/domain/sessions/approval.py` | 582 | 8 | 1 |
| 3 | `src/domain/sessions/bridge.py` | 872 | 11 | 1 |
| 4 | `src/domain/sessions/cache.py` | 389 | 1 | 0 |
| 5 | `src/domain/sessions/error_handler.py` | 390 | 3 | 1 |
| 6 | `src/domain/sessions/events.py` | 829 | 9 | 2 |
| 7 | `src/domain/sessions/executor.py` | 667 | 7 | 1 |
| 8 | `src/domain/sessions/features/__init__.py` | 37 | 0 | 0 |
| 9 | `src/domain/sessions/features/statistics.py` | 426 | 4 | 0 |
| 10 | `src/domain/sessions/features/tags.py` | 450 | 3 | 0 |
| 11 | `src/domain/sessions/features/templates.py` | 513 | 3 | 0 |
| 12 | `src/domain/sessions/files/__init__.py` | 96 | 0 | 0 |
| 13 | `src/domain/sessions/files/analyzer.py` | 350 | 3 | 0 |
| 14 | `src/domain/sessions/files/code_analyzer.py` | 396 | 0 | 0 |
| 15 | `src/domain/sessions/files/code_generator.py` | 318 | 1 | 0 |
| 16 | `src/domain/sessions/files/data_analyzer.py` | 638 | 1 | 1 |
| 17 | `src/domain/sessions/files/data_exporter.py` | 496 | 1 | 0 |
| 18 | `src/domain/sessions/files/document_analyzer.py` | 391 | 1 | 0 |
| 19 | `src/domain/sessions/files/generator.py` | 362 | 2 | 0 |
| 20 | `src/domain/sessions/files/image_analyzer.py` | 401 | 1 | 0 |
| 21 | `src/domain/sessions/files/report_generator.py` | 453 | 1 | 0 |
| 22 | `src/domain/sessions/files/types.py` | 241 | 7 | 0 |
| 23 | `src/domain/sessions/history/__init__.py` | 37 | 0 | 0 |
| 24 | `src/domain/sessions/history/bookmarks.py` | 488 | 3 | 0 |
| 25 | `src/domain/sessions/history/manager.py` | 458 | 3 | 0 |
| 26 | `src/domain/sessions/history/search.py` | 547 | 6 | 0 |
| 27 | `src/domain/sessions/metrics.py` | 607 | 7 | 8 |
| 28 | `src/domain/sessions/models.py` | 687 | 9 | 0 |
| 29 | `src/domain/sessions/recovery.py` | 380 | 4 | 1 |
| 30 | `src/domain/sessions/repository.py` | 405 | 2 | 0 |
| 31 | `src/domain/sessions/service.py` | 625 | 6 | 0 |
| 32 | `src/domain/sessions/streaming.py` | 747 | 6 | 1 |
| 33 | `src/domain/sessions/tool_handler.py` | 1019 | 10 | 1 |

**Classes in `domain/sessions`**:

- `AgentConfig` -- `src/domain/sessions/executor.py`
- `AgentExecutor` -- `src/domain/sessions/executor.py`
- `AgentNotFoundError` -- `src/domain/sessions/bridge.py`
- `AgentRepositoryProtocol` -- `src/domain/sessions/bridge.py`
- `AnalysisRequest` -- `src/domain/sessions/files/types.py`
- `AnalysisResult` -- `src/domain/sessions/files/types.py`
- `AnalysisType` -- `src/domain/sessions/files/types.py`
- `ApprovalAlreadyResolvedError` -- `src/domain/sessions/approval.py`
- `ApprovalCacheProtocol` -- `src/domain/sessions/approval.py`
- `ApprovalError` -- `src/domain/sessions/approval.py`
- `ApprovalExpiredError` -- `src/domain/sessions/approval.py`
- `ApprovalNotFoundError` -- `src/domain/sessions/approval.py`
- `ApprovalStatus` -- `src/domain/sessions/approval.py`
- `Attachment` -- `src/domain/sessions/models.py`
- `AttachmentType` -- `src/domain/sessions/models.py`
- `BaseAnalyzer` -- `src/domain/sessions/files/analyzer.py`
- `BaseGenerator` -- `src/domain/sessions/files/generator.py`
- `Bookmark` -- `src/domain/sessions/history/bookmarks.py`
- `BookmarkFilter` -- `src/domain/sessions/history/bookmarks.py`
- `BookmarkService` -- `src/domain/sessions/history/bookmarks.py`
- `BridgeConfig` -- `src/domain/sessions/bridge.py`
- `BridgeError` -- `src/domain/sessions/bridge.py`
- `CacheProtocol` -- `src/domain/sessions/recovery.py`
- `ChatMessage` -- `src/domain/sessions/executor.py`
- `CheckpointType` -- `src/domain/sessions/recovery.py`
- `CodeGenerator` -- `src/domain/sessions/files/code_generator.py`
- `Counter` -- `src/domain/sessions/metrics.py`
- `DataAnalyzer` -- `src/domain/sessions/files/data_analyzer.py`
- `DataExporter` -- `src/domain/sessions/files/data_exporter.py`
- `DocumentAnalyzer` -- `src/domain/sessions/files/document_analyzer.py`
- `ExecutionConfig` -- `src/domain/sessions/executor.py`
- `ExecutionEvent` -- `src/domain/sessions/events.py`
- `ExecutionEventFactory` -- `src/domain/sessions/events.py`
- `ExecutionEventType` -- `src/domain/sessions/events.py`
- `ExecutionResult` -- `src/domain/sessions/executor.py`
- `ExportFormat` -- `src/domain/sessions/files/types.py`
- `FileAnalyzer` -- `src/domain/sessions/files/analyzer.py`
- `FileGenerator` -- `src/domain/sessions/files/generator.py`
- `Gauge` -- `src/domain/sessions/metrics.py`
- `GenerationRequest` -- `src/domain/sessions/files/types.py`
- `GenerationResult` -- `src/domain/sessions/files/types.py`
- `GenerationType` -- `src/domain/sessions/files/types.py`
- `GenericAnalyzer` -- `src/domain/sessions/files/analyzer.py`
- `Histogram` -- `src/domain/sessions/metrics.py`
- `HistoryFilter` -- `src/domain/sessions/history/manager.py`
- `HistoryManager` -- `src/domain/sessions/history/manager.py`
- `HistoryPage` -- `src/domain/sessions/history/manager.py`
- `ImageAnalyzer` -- `src/domain/sessions/files/image_analyzer.py`
- `MCPClientProtocol` -- `src/domain/sessions/executor.py`
- `MCPClientProtocol` -- `src/domain/sessions/tool_handler.py`
- `MaxIterationsExceededError` -- `src/domain/sessions/bridge.py`
- `Message` -- `src/domain/sessions/models.py`
- `MessageLimitExceededError` -- `src/domain/sessions/service.py`
- `MessageRole` -- `src/domain/sessions/executor.py`
- `MessageRole` -- `src/domain/sessions/models.py`
- `MessageStatistics` -- `src/domain/sessions/features/statistics.py`
- `MetricType` -- `src/domain/sessions/metrics.py`
- `MetricValue` -- `src/domain/sessions/metrics.py`
- `MetricsCollector` -- `src/domain/sessions/metrics.py`
- `ParsedToolCall` -- `src/domain/sessions/tool_handler.py`
- `PendingApprovalError` -- `src/domain/sessions/bridge.py`
- `ProcessingContext` -- `src/domain/sessions/bridge.py`
- `ReportGenerator` -- `src/domain/sessions/files/report_generator.py`
- `SQLAlchemySessionRepository` -- `src/domain/sessions/repository.py`
- `SearchQuery` -- `src/domain/sessions/history/search.py`
- `SearchResponse` -- `src/domain/sessions/history/search.py`
- `SearchResult` -- `src/domain/sessions/history/search.py`
- `SearchScope` -- `src/domain/sessions/history/search.py`
- `SearchService` -- `src/domain/sessions/history/search.py`
- `SearchSortBy` -- `src/domain/sessions/history/search.py`
- `Session` -- `src/domain/sessions/models.py`
- `SessionAgentBridge` -- `src/domain/sessions/bridge.py`
- `SessionCache` -- `src/domain/sessions/cache.py`
- `SessionCheckpoint` -- `src/domain/sessions/recovery.py`
- `SessionConfig` -- `src/domain/sessions/models.py`
- `SessionError` -- `src/domain/sessions/error_handler.py`
- `SessionErrorCode` -- `src/domain/sessions/error_handler.py`
- `SessionErrorHandler` -- `src/domain/sessions/error_handler.py`
- `SessionEvent` -- `src/domain/sessions/events.py`
- `SessionEventPublisher` -- `src/domain/sessions/events.py`
- `SessionEventType` -- `src/domain/sessions/events.py`
- `SessionExpiredError` -- `src/domain/sessions/service.py`
- `SessionNotActiveError` -- `src/domain/sessions/bridge.py`
- `SessionNotActiveError` -- `src/domain/sessions/service.py`
- `SessionNotFoundError` -- `src/domain/sessions/bridge.py`
- `SessionNotFoundError` -- `src/domain/sessions/service.py`
- `SessionRecoveryManager` -- `src/domain/sessions/recovery.py`
- `SessionRepository` -- `src/domain/sessions/repository.py`
- `SessionService` -- `src/domain/sessions/service.py`
- `SessionServiceError` -- `src/domain/sessions/service.py`
- `SessionServiceProtocol` -- `src/domain/sessions/bridge.py`
- `SessionStatistics` -- `src/domain/sessions/features/statistics.py`
- `SessionStatus` -- `src/domain/sessions/models.py`
- `SessionTag` -- `src/domain/sessions/features/tags.py`
- `SessionTemplate` -- `src/domain/sessions/features/templates.py`
- `StatisticsService` -- `src/domain/sessions/features/statistics.py`
- `StreamConfig` -- `src/domain/sessions/streaming.py`
- `StreamState` -- `src/domain/sessions/streaming.py`
- `StreamStats` -- `src/domain/sessions/streaming.py`
- `StreamingLLMHandler` -- `src/domain/sessions/streaming.py`
- `Tag` -- `src/domain/sessions/features/tags.py`
- `TagService` -- `src/domain/sessions/features/tags.py`
- `TemplateCategory` -- `src/domain/sessions/features/templates.py`
- `TemplateService` -- `src/domain/sessions/features/templates.py`
- `TimingContext` -- `src/domain/sessions/metrics.py`
- `TokenCounter` -- `src/domain/sessions/streaming.py`
- `ToolApprovalManager` -- `src/domain/sessions/approval.py`
- `ToolApprovalRequest` -- `src/domain/sessions/approval.py`
- `ToolCall` -- `src/domain/sessions/models.py`
- `ToolCallDelta` -- `src/domain/sessions/streaming.py`
- `ToolCallHandler` -- `src/domain/sessions/tool_handler.py`
- `ToolCallInfo` -- `src/domain/sessions/events.py`
- `ToolCallParser` -- `src/domain/sessions/tool_handler.py`
- `ToolCallStatus` -- `src/domain/sessions/models.py`
- `ToolExecutionResult` -- `src/domain/sessions/tool_handler.py`
- `ToolHandlerConfig` -- `src/domain/sessions/tool_handler.py`
- `ToolHandlerStats` -- `src/domain/sessions/tool_handler.py`
- `ToolPermission` -- `src/domain/sessions/tool_handler.py`
- `ToolRegistryProtocol` -- `src/domain/sessions/tool_handler.py`
- `ToolResultInfo` -- `src/domain/sessions/events.py`
- `ToolSource` -- `src/domain/sessions/tool_handler.py`
- `UsageInfo` -- `src/domain/sessions/events.py`
- `UserStatistics` -- `src/domain/sessions/features/statistics.py`

### Module: `domain/tasks`

**Summary**: 3 files, 343 LOC, 6 classes, 0 functions

| # | File Path | LOC | Classes | Functions |
|---|-----------|-----|---------|-----------|
| 1 | `src/domain/tasks/__init__.py` | 22 | 0 | 0 |
| 2 | `src/domain/tasks/models.py` | 127 | 5 | 0 |
| 3 | `src/domain/tasks/service.py` | 194 | 1 | 0 |

**Classes in `domain/tasks`**:

- `Task` -- `src/domain/tasks/models.py`
- `TaskPriority` -- `src/domain/tasks/models.py`
- `TaskResult` -- `src/domain/tasks/models.py`
- `TaskService` -- `src/domain/tasks/service.py`
- `TaskStatus` -- `src/domain/tasks/models.py`
- `TaskType` -- `src/domain/tasks/models.py`

### Module: `domain/templates`

**Summary**: 3 files, 944 LOC, 9 classes, 0 functions

| # | File Path | LOC | Classes | Functions |
|---|-----------|-----|---------|-----------|
| 1 | `src/domain/templates/__init__.py` | 36 | 0 | 0 |
| 2 | `src/domain/templates/models.py` | 375 | 7 | 0 |
| 3 | `src/domain/templates/service.py` | 533 | 2 | 0 |

**Classes in `domain/templates`**:

- `AgentTemplate` -- `src/domain/templates/models.py`
- `ParameterType` -- `src/domain/templates/models.py`
- `TemplateCategory` -- `src/domain/templates/models.py`
- `TemplateError` -- `src/domain/templates/service.py`
- `TemplateExample` -- `src/domain/templates/models.py`
- `TemplateParameter` -- `src/domain/templates/models.py`
- `TemplateService` -- `src/domain/templates/service.py`
- `TemplateStatus` -- `src/domain/templates/models.py`
- `TemplateVersion` -- `src/domain/templates/models.py`

### Module: `domain/triggers`

**Summary**: 2 files, 679 LOC, 11 classes, 0 functions

| # | File Path | LOC | Classes | Functions |
|---|-----------|-----|---------|-----------|
| 1 | `src/domain/triggers/__init__.py` | 25 | 0 | 0 |
| 2 | `src/domain/triggers/webhook.py` | 654 | 11 | 0 |

**Classes in `domain/triggers`**:

- `SignatureAlgorithm` -- `src/domain/triggers/webhook.py`
- `SignatureVerificationError` -- `src/domain/triggers/webhook.py`
- `TriggerExecutionError` -- `src/domain/triggers/webhook.py`
- `TriggerResult` -- `src/domain/triggers/webhook.py`
- `WebhookConfigNotFoundError` -- `src/domain/triggers/webhook.py`
- `WebhookDisabledError` -- `src/domain/triggers/webhook.py`
- `WebhookError` -- `src/domain/triggers/webhook.py`
- `WebhookPayload` -- `src/domain/triggers/webhook.py`
- `WebhookStatus` -- `src/domain/triggers/webhook.py`
- `WebhookTriggerConfig` -- `src/domain/triggers/webhook.py`
- `WebhookTriggerService` -- `src/domain/triggers/webhook.py`

### Module: `domain/versioning`

**Summary**: 2 files, 769 LOC, 10 classes, 0 functions

| # | File Path | LOC | Classes | Functions |
|---|-----------|-----|---------|-----------|
| 1 | `src/domain/versioning/__init__.py` | 24 | 0 | 0 |
| 2 | `src/domain/versioning/service.py` | 745 | 10 | 0 |

**Classes in `domain/versioning`**:

- `ChangeType` -- `src/domain/versioning/service.py`
- `DiffHunk` -- `src/domain/versioning/service.py`
- `DiffLine` -- `src/domain/versioning/service.py`
- `SemanticVersion` -- `src/domain/versioning/service.py`
- `TemplateVersion` -- `src/domain/versioning/service.py`
- `VersionDiff` -- `src/domain/versioning/service.py`
- `VersionStatistics` -- `src/domain/versioning/service.py`
- `VersionStatus` -- `src/domain/versioning/service.py`
- `VersioningError` -- `src/domain/versioning/service.py`
- `VersioningService` -- `src/domain/versioning/service.py`

### Module: `domain/workflows`

**Summary**: 11 files, 5,215 LOC, 53 classes, 16 functions

| # | File Path | LOC | Classes | Functions |
|---|-----------|-----|---------|-----------|
| 1 | `src/domain/workflows/__init__.py` | 97 | 0 | 1 |
| 2 | `src/domain/workflows/deadlock_detector.py` | 717 | 5 | 3 |
| 3 | `src/domain/workflows/executors/__init__.py` | 101 | 0 | 0 |
| 4 | `src/domain/workflows/executors/approval.py` | 427 | 4 | 0 |
| 5 | `src/domain/workflows/executors/concurrent.py` | 618 | 4 | 5 |
| 6 | `src/domain/workflows/executors/concurrent_state.py` | 654 | 4 | 2 |
| 7 | `src/domain/workflows/executors/parallel_gateway.py` | 734 | 6 | 1 |
| 8 | `src/domain/workflows/models.py` | 376 | 7 | 0 |
| 9 | `src/domain/workflows/resume_service.py` | 416 | 3 | 0 |
| 10 | `src/domain/workflows/schemas.py` | 268 | 17 | 0 |
| 11 | `src/domain/workflows/service.py` | 807 | 3 | 4 |

**Classes in `domain/workflows`**:

- `ApprovalAction` -- `src/domain/workflows/executors/approval.py`
- `ApprovalGateway` -- `src/domain/workflows/executors/approval.py`
- `ApprovalResponse` -- `src/domain/workflows/executors/approval.py`
- `BranchStatus` -- `src/domain/workflows/executors/concurrent_state.py`
- `ConcurrentExecutionState` -- `src/domain/workflows/executors/concurrent_state.py`
- `ConcurrentExecutor` -- `src/domain/workflows/executors/concurrent.py`
- `ConcurrentMode` -- `src/domain/workflows/executors/concurrent.py`
- `ConcurrentResult` -- `src/domain/workflows/executors/concurrent.py`
- `ConcurrentStateManager` -- `src/domain/workflows/executors/concurrent_state.py`
- `ConcurrentTask` -- `src/domain/workflows/executors/concurrent.py`
- `Config` -- `src/domain/workflows/schemas.py`
- `Config` -- `src/domain/workflows/schemas.py`
- `Config` -- `src/domain/workflows/schemas.py`
- `Config` -- `src/domain/workflows/schemas.py`
- `Config` -- `src/domain/workflows/schemas.py`
- `Config` -- `src/domain/workflows/schemas.py`
- `DeadlockDetector` -- `src/domain/workflows/deadlock_detector.py`
- `DeadlockInfo` -- `src/domain/workflows/deadlock_detector.py`
- `DeadlockResolutionStrategy` -- `src/domain/workflows/deadlock_detector.py`
- `ForkBranchConfig` -- `src/domain/workflows/executors/parallel_gateway.py`
- `GatewayType` -- `src/domain/workflows/models.py`
- `HumanApprovalRequest` -- `src/domain/workflows/executors/approval.py`
- `JoinStrategy` -- `src/domain/workflows/executors/parallel_gateway.py`
- `MergeStrategy` -- `src/domain/workflows/executors/parallel_gateway.py`
- `NodeExecutionResult` -- `src/domain/workflows/schemas.py`
- `NodeExecutionResult` -- `src/domain/workflows/service.py`
- `NodeType` -- `src/domain/workflows/models.py`
- `ParallelBranch` -- `src/domain/workflows/executors/concurrent_state.py`
- `ParallelForkGateway` -- `src/domain/workflows/executors/parallel_gateway.py`
- `ParallelGatewayConfig` -- `src/domain/workflows/executors/parallel_gateway.py`
- `ParallelJoinGateway` -- `src/domain/workflows/executors/parallel_gateway.py`
- `ResumeResult` -- `src/domain/workflows/resume_service.py`
- `ResumeStatus` -- `src/domain/workflows/resume_service.py`
- `TimeoutHandler` -- `src/domain/workflows/deadlock_detector.py`
- `TriggerType` -- `src/domain/workflows/models.py`
- `WaitingTask` -- `src/domain/workflows/deadlock_detector.py`
- `WorkflowContext` -- `src/domain/workflows/models.py`
- `WorkflowCreateRequest` -- `src/domain/workflows/schemas.py`
- `WorkflowDefinition` -- `src/domain/workflows/models.py`
- `WorkflowEdge` -- `src/domain/workflows/models.py`
- `WorkflowEdgeSchema` -- `src/domain/workflows/schemas.py`
- `WorkflowExecuteRequest` -- `src/domain/workflows/schemas.py`
- `WorkflowExecutionResponse` -- `src/domain/workflows/schemas.py`
- `WorkflowExecutionResult` -- `src/domain/workflows/service.py`
- `WorkflowExecutionService` -- `src/domain/workflows/service.py`
- `WorkflowGraphSchema` -- `src/domain/workflows/schemas.py`
- `WorkflowListResponse` -- `src/domain/workflows/schemas.py`
- `WorkflowNode` -- `src/domain/workflows/models.py`
- `WorkflowNodeSchema` -- `src/domain/workflows/schemas.py`
- `WorkflowResponse` -- `src/domain/workflows/schemas.py`
- `WorkflowResumeService` -- `src/domain/workflows/resume_service.py`
- `WorkflowUpdateRequest` -- `src/domain/workflows/schemas.py`
- `WorkflowValidationResponse` -- `src/domain/workflows/schemas.py`

---

## 5. Critical Path Module: `domain/sessions` -- Full Detail

| Metric | Value |
|--------|-------|
| Total Files | 33 |
| Code Files | 29 |
| Init Files | 4 |
| Total LOC | 15,473 |
| Total Classes | 123 |
| Total Functions | 18 |
| % of Domain Layer | 32.5% LOC |

### 5.1 All Files with All Class Names and Methods

#### `src/domain/sessions/__init__.py`
- **LOC**: 176
- **Classes**: none

#### `src/domain/sessions/approval.py`
- **LOC**: 582
- **Classes** (8):
  - `ApprovalStatus` -- methods: (none)
  - `ToolApprovalRequest` -- methods: is_pending, is_expired, time_remaining, tool_name, tool_arguments, to_dict, from_dict
  - `ApprovalCacheProtocol` -- methods: get, setex, delete, scan, keys
  - `ApprovalError` -- methods: (none)
  - `ApprovalNotFoundError` -- methods: (none)
  - `ApprovalAlreadyResolvedError` -- methods: (none)
  - `ApprovalExpiredError` -- methods: (none)
  - `ToolApprovalManager` -- methods: __init__, create_approval_request, get_approval_request, resolve_approval, approve, reject, get_pending_approvals, get_all_approvals, cancel_approval, cleanup_expired, _approval_key, _session_approvals_key, _update_request, _add_to_session_list, _get_session_approval_ids
- **Functions** (1): create_approval_manager

#### `src/domain/sessions/bridge.py`
- **LOC**: 872
- **Classes** (11):
  - `SessionServiceProtocol` -- methods: get_session, send_message, add_assistant_message, get_messages, get_conversation_for_llm
  - `AgentRepositoryProtocol` -- methods: get
  - `BridgeConfig` -- methods: (none)
  - `ProcessingContext` -- methods: (none)
  - `BridgeError` -- methods: (none)
  - `SessionNotFoundError` -- methods: (none)
  - `SessionNotActiveError` -- methods: (none)
  - `AgentNotFoundError` -- methods: (none)
  - `MaxIterationsExceededError` -- methods: (none)
  - `PendingApprovalError` -- methods: (none)
  - `SessionAgentBridge` -- methods: __init__, process_message, handle_tool_approval, get_pending_approvals, cancel_pending_approvals, _get_active_session, _get_agent_config, _execute_with_tools, _continue_after_approval, _requires_approval
- **Functions** (1): create_session_agent_bridge

#### `src/domain/sessions/cache.py`
- **LOC**: 389
- **Classes** (1):
  - `SessionCache` -- methods: __init__, get_session, set_session, delete_session, extend_session, update_session_status, get_messages, append_message, clear_messages, get_user_sessions, set_user_sessions, invalidate_user_sessions, _user_sessions_key, get_sessions_batch, set_sessions_batch, ... (+3 more)

#### `src/domain/sessions/error_handler.py`
- **LOC**: 390
- **Classes** (3):
  - `SessionErrorCode` -- methods: (none)
  - `SessionError` -- methods: __init__, http_status, to_dict, to_event, from_exception
  - `SessionErrorHandler` -- methods: __init__, _calculate_delay, handle_llm_error, handle_tool_error, with_retry, safe_execute
- **Functions** (1): create_error_handler

#### `src/domain/sessions/events.py`
- **LOC**: 829
- **Classes** (9):
  - `ExecutionEventType` -- methods: (none)
  - `ToolCallInfo` -- methods: to_dict
  - `ToolResultInfo` -- methods: to_dict
  - `UsageInfo` -- methods: to_dict
  - `ExecutionEvent` -- methods: to_dict, to_sse, to_json, from_dict
  - `ExecutionEventFactory` -- methods: started, content, content_delta, tool_call, tool_result, approval_required, approval_response, error, done, heartbeat
  - `SessionEventType` -- methods: (none)
  - `SessionEvent` -- methods: to_dict, from_dict
  - `SessionEventPublisher` -- methods: __init__, subscribe, subscribe_all, unsubscribe, publish, _safe_call, session_created, session_activated, session_ended, message_sent, message_received, tool_call_requested, error_occurred
- **Functions** (2): get_event_publisher, reset_event_publisher

#### `src/domain/sessions/executor.py`
- **LOC**: 667
- **Classes** (7):
  - `MessageRole` -- methods: (none)
  - `ChatMessage` -- methods: to_dict
  - `AgentConfig` -- methods: from_agent
  - `ExecutionConfig` -- methods: (none)
  - `ExecutionResult` -- methods: (none)
  - `MCPClientProtocol` -- methods: call_tool, get_available_tools
  - `AgentExecutor` -- methods: __init__, execute, execute_sync, _build_messages, _get_available_tools, _call_llm, get_tool_registry, get_mcp_client, set_tool_registry, set_mcp_client
- **Functions** (1): create_agent_executor

#### `src/domain/sessions/features/__init__.py`
- **LOC**: 37
- **Classes**: none

#### `src/domain/sessions/features/statistics.py`
- **LOC**: 426
- **Classes** (4):
  - `MessageStatistics` -- methods: (none)
  - `SessionStatistics` -- methods: (none)
  - `UserStatistics` -- methods: (none)
  - `StatisticsService` -- methods: __init__, get_statistics, get_user_statistics, refresh_statistics, invalidate_statistics, invalidate_user_statistics, _calculate_session_statistics, _calculate_user_statistics, _is_stale, get_statistics_summary, export_statistics

#### `src/domain/sessions/features/tags.py`
- **LOC**: 450
- **Classes** (3):
  - `Tag` -- methods: (none)
  - `SessionTag` -- methods: (none)
  - `TagService` -- methods: __init__, create_tag, get_tag, get_tag_by_name, get_user_tags, update_tag, delete_tag, add_tag_to_session, remove_tag_from_session, get_session_tags, get_sessions_by_tag, get_popular_tags, suggest_tags, _normalize_tag_name, _generate_color, ... (+2 more)

#### `src/domain/sessions/features/templates.py`
- **LOC**: 513
- **Classes** (3):
  - `TemplateCategory` -- methods: (none)
  - `SessionTemplate` -- methods: (none)
  - `TemplateService` -- methods: __init__, create_template, create_from_session, get_template, get_user_templates, update_template, delete_template, apply_template, get_popular_templates, export_template, import_template, _parse_system_template, _invalidate_cache

#### `src/domain/sessions/files/__init__.py`
- **LOC**: 96
- **Classes**: none

#### `src/domain/sessions/files/analyzer.py`
- **LOC**: 350
- **Classes** (3):
  - `BaseAnalyzer` -- methods: analyze, supports, _read_file_content, _get_file_extension, _get_file_metadata, _format_size
  - `GenericAnalyzer` -- methods: analyze, supports
  - `FileAnalyzer` -- methods: __init__, _register_analyzers, register_analyzer, get_analyzer, analyze, batch_analyze, is_supported, get_supported_extensions, detect_attachment_type

#### `src/domain/sessions/files/code_analyzer.py`
- **LOC**: 396
- **Classes**: none

#### `src/domain/sessions/files/code_generator.py`
- **LOC**: 318
- **Classes** (1):
  - `CodeGenerator` -- methods: __init__, supports, generate, _generate_header, _format_code, _format_python, _format_javascript, generate_code_file, get_supported_languages, get_extension

#### `src/domain/sessions/files/data_analyzer.py`
- **LOC**: 638
- **Classes** (1):
  - `DataAnalyzer` -- methods: __init__, supports, analyze, _read_data, _read_csv, _read_json, _read_excel, _read_xml, _read_yaml, _read_parquet, _read_generic, _analyze_summary, _analyze_statistics, _analyze_transform, _analyze_query, ... (+7 more)
- **Functions** (1): element_to_dict

#### `src/domain/sessions/files/data_exporter.py`
- **LOC**: 496
- **Classes** (1):
  - `DataExporter` -- methods: __init__, supports, generate, _parse_data, _export_csv, _export_json, _export_excel, _export_xml, _xml_escape, _xml_safe_tag, export_data, export_analysis_results, export_table, get_supported_formats

#### `src/domain/sessions/files/document_analyzer.py`
- **LOC**: 391
- **Classes** (1):
  - `DocumentAnalyzer` -- methods: __init__, supports, analyze, _extract_text, _extract_pdf_text, _extract_docx_text, _extract_rtf_text, _analyze_summary, _analyze_extract, _analyze_query, _analyze_statistics, _compute_text_statistics, _simple_search, _generate_llm_summary, _query_with_llm

#### `src/domain/sessions/files/generator.py`
- **LOC**: 362
- **Classes** (2):
  - `BaseGenerator` -- methods: generate, supports
  - `FileGenerator` -- methods: __init__, _register_generators, register_generator, get_generator, generate, generate_file, get_download_url, _generate_download_token, verify_download_token, _detect_type, get_content_type

#### `src/domain/sessions/files/image_analyzer.py`
- **LOC**: 401
- **Classes** (1):
  - `ImageAnalyzer` -- methods: __init__, supports, analyze, _read_image, _get_image_info, _analyze_summary, _analyze_extract, _analyze_query, _describe_with_llm, _extract_text_ocr, _extract_text_with_llm, _query_with_llm, _create_thumbnail_base64

#### `src/domain/sessions/files/report_generator.py`
- **LOC**: 453
- **Classes** (1):
  - `ReportGenerator` -- methods: __init__, supports, generate, _generate_html_report, _generate_markdown_report, _markdown_to_html, _generate_toc, _generate_markdown_toc, generate_report, generate_analysis_report

#### `src/domain/sessions/files/types.py`
- **LOC**: 241
- **Classes** (7):
  - `AnalysisType` -- methods: (none)
  - `GenerationType` -- methods: (none)
  - `ExportFormat` -- methods: (none)
  - `AnalysisRequest` -- methods: to_dict, from_dict
  - `AnalysisResult` -- methods: to_dict, from_dict, error_result
  - `GenerationRequest` -- methods: to_dict
  - `GenerationResult` -- methods: to_dict

#### `src/domain/sessions/history/__init__.py`
- **LOC**: 37
- **Classes**: none

#### `src/domain/sessions/history/bookmarks.py`
- **LOC**: 488
- **Classes** (3):
  - `Bookmark` -- methods: (none)
  - `BookmarkFilter` -- methods: (none)
  - `BookmarkService` -- methods: __init__, create_bookmark, get_bookmark, get_bookmark_by_message, get_user_bookmarks, get_session_bookmarks, update_bookmark, delete_bookmark, add_tags, remove_tags, get_user_tags, export_bookmarks, _invalidate_user_cache, _convert_filter

#### `src/domain/sessions/history/manager.py`
- **LOC**: 458
- **Classes** (3):
  - `HistoryFilter` -- methods: (none)
  - `HistoryPage` -- methods: (none)
  - `HistoryManager` -- methods: __init__, get_history, get_recent_messages, get_message_context, get_conversation_turns, export_history, _export_json, _export_markdown, _export_text, clear_history, cleanup_old_history, _build_cache_key, _convert_filter

#### `src/domain/sessions/history/search.py`
- **LOC**: 547
- **Classes** (6):
  - `SearchScope` -- methods: (none)
  - `SearchSortBy` -- methods: (none)
  - `SearchQuery` -- methods: (none)
  - `SearchResult` -- methods: (none)
  - `SearchResponse` -- methods: (none)
  - `SearchService` -- methods: __init__, search, search_in_session, search_user_messages, _search_with_engine, _search_with_database, _preprocess_query, _build_filters, _build_sort, _calculate_simple_score, _generate_highlights, _parse_message, _get_suggestions, index_message, remove_from_index, ... (+1 more)

#### `src/domain/sessions/metrics.py`
- **LOC**: 607
- **Classes** (7):
  - `MetricType` -- methods: (none)
  - `MetricValue` -- methods: to_dict
  - `Counter` -- methods: __init__, _key, inc, get, reset
  - `Histogram` -- methods: __init__, _key, observe, get_observations, get_count, get_sum, get_average, get_percentile, reset
  - `Gauge` -- methods: __init__, _key, set, inc, dec, get, reset
  - `MetricsCollector` -- methods: __init__, record_message, record_user_message, record_assistant_message, record_system_message, record_tool_call, record_tool_success, record_tool_failure, record_tool_timeout, record_tool_execution_time, record_error, record_approval_request, record_approval_granted, record_approval_denied, record_approval_timeout, ... (+8 more)
  - `TimingContext` -- methods: __init__, __enter__, __exit__, __aenter__, __aexit__
- **Functions** (8): track_time, track_tool_time, get_metrics_collector, create_metrics_collector, decorator, decorator, async wrapper, async wrapper

#### `src/domain/sessions/models.py`
- **LOC**: 687
- **Classes** (9):
  - `SessionStatus` -- methods: (none)
  - `MessageRole` -- methods: (none)
  - `AttachmentType` -- methods: (none)
  - `ToolCallStatus` -- methods: (none)
  - `Attachment` -- methods: from_upload, _detect_type, to_dict, from_dict
  - `ToolCall` -- methods: approve, reject, start_execution, complete, fail, to_dict, from_dict
  - `Message` -- methods: add_attachment, add_tool_call, has_pending_tool_calls, to_dict, from_dict, to_llm_format
  - `SessionConfig` -- methods: to_dict, from_dict, is_tool_allowed
  - `Session` -- methods: __post_init__, activate, suspend, resume, end, is_expired, is_active, can_accept_message, add_message, _generate_title, _extend_expiry, get_conversation_history, get_last_message, get_message_count, get_attachment_count, ... (+3 more)

#### `src/domain/sessions/recovery.py`
- **LOC**: 380
- **Classes** (4):
  - `CheckpointType` -- methods: (none)
  - `SessionCheckpoint` -- methods: to_dict, from_dict, is_expired
  - `CacheProtocol` -- methods: get, set, delete, exists
  - `SessionRecoveryManager` -- methods: __init__, _checkpoint_key, _event_buffer_key, _reconnect_key, save_checkpoint, get_checkpoint, delete_checkpoint, restore_from_checkpoint, buffer_event, get_buffered_events, clear_event_buffer, handle_websocket_reconnect, save_reconnect_info, get_reconnect_info, clear_reconnect_info, ... (+2 more)
- **Functions** (1): create_recovery_manager

#### `src/domain/sessions/repository.py`
- **LOC**: 405
- **Classes** (2):
  - `SessionRepository` -- methods: create, get, update, delete, list_by_user, add_message, get_messages, cleanup_expired
  - `SQLAlchemySessionRepository` -- methods: __init__, create, get, update, delete, list_by_user, add_message, get_messages, cleanup_expired, count_by_user, get_active_sessions, _to_domain, _message_to_domain

#### `src/domain/sessions/service.py`
- **LOC**: 625
- **Classes** (6):
  - `SessionServiceError` -- methods: (none)
  - `SessionNotFoundError` -- methods: (none)
  - `SessionExpiredError` -- methods: (none)
  - `SessionNotActiveError` -- methods: (none)
  - `MessageLimitExceededError` -- methods: (none)
  - `SessionService` -- methods: __init__, create_session, get_session, activate_session, suspend_session, resume_session, end_session, list_sessions, count_sessions, send_message, add_assistant_message, get_messages, get_conversation_for_llm, add_tool_call, approve_tool_call, ... (+4 more)

#### `src/domain/sessions/streaming.py`
- **LOC**: 747
- **Classes** (6):
  - `StreamState` -- methods: (none)
  - `StreamConfig` -- methods: (none)
  - `StreamStats` -- methods: time_to_first_token_ms, total_duration_ms, total_tokens, to_dict
  - `ToolCallDelta` -- methods: (none)
  - `TokenCounter` -- methods: __init__, count_tokens, count_messages
  - `StreamingLLMHandler` -- methods: __init__, stream, stream_simple, cancel, state, _call_with_retry, _heartbeat_loop, _parse_tool_arguments, close, __aenter__, __aexit__
- **Functions** (1): create_streaming_handler

#### `src/domain/sessions/tool_handler.py`
- **LOC**: 1019
- **Classes** (10):
  - `ToolSource` -- methods: (none)
  - `ToolPermission` -- methods: (none)
  - `ToolRegistryProtocol` -- methods: get, get_all, get_schemas
  - `MCPClientProtocol` -- methods: call_tool, list_tools, connected_servers
  - `ParsedToolCall` -- methods: to_tool_call_info
  - `ToolExecutionResult` -- methods: to_tool_result_info, to_llm_message
  - `ToolHandlerConfig` -- methods: (none)
  - `ToolHandlerStats` -- methods: record_call, success_rate, average_execution_time_ms
  - `ToolCallParser` -- methods: parse_from_response, parse_from_message, _parse_openai_tool_call, _parse_dict_tool_call, _determine_source
  - `ToolCallHandler` -- methods: __init__, handle_tool_calls, execute_tool, parse_tool_calls, get_available_tools, reset_round_count, results_to_messages, _check_permission, _is_tool_allowed, _execute_local_tool, _execute_mcp_tool, _get_mcp_tool_name, _execute_parallel, _handle_approval_call
- **Functions** (1): create_tool_handler

### 5.2 Sessions Class Coverage: V9 Named vs Metadata

- **V9 named classes**: 51
- **Actual classes in metadata**: 119
- **V9 classes confirmed in metadata**: 50 (98%)
- **V9 classes NOT found in metadata**: 1
- **Metadata classes NOT mentioned in V9**: 69

**V9 Named But NOT in Metadata** (possible V9 errors or name mismatches):

- `CodeAnalyzer`

**In Metadata But NOT Named in V9** (classes V9 omitted or only referenced generically):

- `AgentConfig`
- `AgentNotFoundError`
- `AgentRepositoryProtocol`
- `AnalysisRequest`
- `AnalysisResult`
- `AnalysisType`
- `ApprovalAlreadyResolvedError`
- `ApprovalCacheProtocol`
- `ApprovalError`
- `ApprovalExpiredError`
- `ApprovalNotFoundError`
- `AttachmentType`
- `BaseAnalyzer`
- `BaseGenerator`
- `Bookmark`
- `BookmarkFilter`
- `BridgeConfig`
- `BridgeError`
- `CacheProtocol`
- `ChatMessage`
- `CheckpointType`
- `Counter`
- `ExecutionConfig`
- `ExecutionResult`
- `ExportFormat`
- `Gauge`
- `GenerationRequest`
- `GenerationResult`
- `GenerationType`
- `GenericAnalyzer`
- `Histogram`
- `HistoryFilter`
- `HistoryPage`
- `MCPClientProtocol`
- `MaxIterationsExceededError`
- `MessageLimitExceededError`
- `MessageRole`
- `MessageStatistics`
- `MetricType`
- `MetricValue`
- `ParsedToolCall`
- `PendingApprovalError`
- `ProcessingContext`
- `SQLAlchemySessionRepository`
- `SearchQuery`
- `SearchResponse`
- `SearchResult`
- `SearchScope`
- `SearchSortBy`
- `SessionCheckpoint`
- `SessionError`
- `SessionErrorCode`
- `SessionExpiredError`
- `SessionNotActiveError`
- `SessionNotFoundError`
- `SessionServiceError`
- `SessionServiceProtocol`
- `SessionStatistics`
- `SessionTag`
- `SessionTemplate`
- `StreamConfig`
- `Tag`
- `TemplateCategory`
- `TimingContext`
- `ToolExecutionResult`
- `ToolHandlerConfig`
- `ToolRegistryProtocol`
- `ToolSource`
- `UserStatistics`

---

## 6. Full Domain Class Gap Analysis: V9 vs Metadata

| Metric | Count |
|--------|-------|
| V9 explicitly named classes | 89 |
| Metadata total unique classes | 365 |
| V9 classes confirmed in metadata | 88 (98%) |
| V9 classes NOT in metadata | 1 |
| Metadata classes not named in V9 | 277 |

### 6.1 V9 Named Classes NOT Found in Metadata

These classes were explicitly named in V9 analysis but do not appear in the AST scan.
This may indicate V9 name errors, aliases, or classes defined differently.

- `CodeAnalyzer`

### 6.2 Metadata Classes NOT Named in V9

These classes exist in the codebase but were not explicitly mentioned by name in V9.
V9 may have referenced them generically or omitted them for brevity.

| # | Class Name | Module |
|---|-----------|--------|
| 1 | `AgentConfig` | `sessions` |
| 2 | `AgentCreateRequest` | `agents` |
| 3 | `AgentExecutionResult` | `agents` |
| 4 | `AgentListResponse` | `agents` |
| 5 | `AgentNotFoundError` | `sessions` |
| 6 | `AgentRegistryProtocol` | `orchestration` |
| 7 | `AgentRepositoryProtocol` | `sessions` |
| 8 | `AgentResponse` | `agents` |
| 9 | `AgentRunRequest` | `agents` |
| 10 | `AgentRunResponse` | `agents` |
| 11 | `AgentTemplate` | `templates` |
| 12 | `AgentUpdateRequest` | `agents` |
| 13 | `AnalysisRequest` | `sessions` |
| 14 | `AnalysisResult` | `sessions` |
| 15 | `AnalysisType` | `sessions` |
| 16 | `ApprovalAction` | `workflows` |
| 17 | `ApprovalAlreadyResolvedError` | `sessions` |
| 18 | `ApprovalCacheProtocol` | `sessions` |
| 19 | `ApprovalError` | `sessions` |
| 20 | `ApprovalExpiredError` | `sessions` |
| 21 | `ApprovalGateway` | `workflows` |
| 22 | `ApprovalNotFoundError` | `sessions` |
| 23 | `ApprovalResponse` | `workflows` |
| 24 | `AttachmentType` | `sessions` |
| 25 | `AuditAction` | `audit` |
| 26 | `AuditEntry` | `audit` |
| 27 | `AuditError` | `audit` |
| 28 | `AuditQueryParams` | `audit` |
| 29 | `AuditResource` | `audit` |
| 30 | `AuditSeverity` | `audit` |
| 31 | `AuthService` | `auth` |
| 32 | `AuthType` | `connectors` |
| 33 | `BaseAnalyzer` | `sessions` |
| 34 | `BaseGenerator` | `sessions` |
| 35 | `Bookmark` | `sessions` |
| 36 | `BookmarkFilter` | `sessions` |
| 37 | `BranchStatus` | `workflows` |
| 38 | `BridgeConfig` | `sessions` |
| 39 | `BridgeError` | `sessions` |
| 40 | `CacheProtocol` | `sessions` |
| 41 | `CaseStatus` | `learning` |
| 42 | `ChangeType` | `versioning` |
| 43 | `ChatHistorySync` | `chat_history` |
| 44 | `ChatMessage` | `sessions` |
| 45 | `ChatSyncResponse` | `chat_history` |
| 46 | `CheckpointData` | `checkpoints` |
| 47 | `CheckpointServiceProtocol` | `orchestration` |
| 48 | `CheckpointStatus` | `checkpoints` |
| 49 | `CheckpointType` | `sessions` |
| 50 | `CompositionBlock` | `orchestration` |
| 51 | `CompositionType` | `orchestration` |
| 52 | `ConcurrentExecutionState` | `workflows` |
| 53 | `ConcurrentExecutor` | `workflows` |
| 54 | `ConcurrentMode` | `workflows` |
| 55 | `ConcurrentResult` | `workflows` |
| 56 | `ConcurrentStateManager` | `workflows` |
| 57 | `ConcurrentTask` | `workflows` |
| 58 | `Config` | `workflows` |
| 59 | `ConnectorConfig` | `connectors` |
| 60 | `ConnectorError` | `connectors` |
| 61 | `ConnectorResponse` | `connectors` |
| 62 | `ConnectorStatus` | `connectors` |
| 63 | `ContextEntry` | `orchestration` |
| 64 | `ContextScope` | `orchestration` |
| 65 | `ConversationSession` | `orchestration` |
| 66 | `ConversationTurn` | `orchestration` |
| 67 | `Counter` | `sessions` |
| 68 | `DataFlowDirection` | `orchestration` |
| 69 | `DataFlowEvent` | `orchestration` |
| 70 | `DataFlowTracker` | `orchestration` |
| 71 | `DatabaseCheckpointStorage` | `checkpoints` |
| 72 | `DatabaseSessionProtocol` | `orchestration` |
| 73 | `DeadlockInfo` | `workflows` |
| 74 | `DeadlockResolutionStrategy` | `workflows` |
| 75 | `Decision` | `orchestration` |
| 76 | `DecisionConfidence` | `orchestration` |
| 77 | `DecisionEngineProtocol` | `orchestration` |
| 78 | `DecisionOption` | `orchestration` |
| 79 | `DecisionRule` | `orchestration` |
| 80 | `DecisionType` | `orchestration` |
| 81 | `DecompositionResult` | `orchestration` |
| 82 | `DecompositionStrategy` | `orchestration` |
| 83 | `DependencyType` | `orchestration` |
| 84 | `DiffHunk` | `versioning` |
| 85 | `DiffLine` | `versioning` |
| 86 | `ErrorFix` | `orchestration` |
| 87 | `ExecutionConfig` | `sessions` |
| 88 | `ExecutionPlan` | `orchestration` |
| 89 | `ExecutionRelation` | `routing` |
| 90 | `ExecutionResult` | `sessions` |
| 91 | `ExecutionServiceProtocol` | `orchestration` |
| 92 | `ExecutionStatus` | `executions` |
| 93 | `ExecutionTrace` | `devtools` |
| 94 | `ExecutionTracer` | `devtools` |
| 95 | `ExportFormat` | `sessions` |
| 96 | `FileService` | `files` |
| 97 | `FileStorage` | `files` |
| 98 | `FileValidationError` | `files` |
| 99 | `ForkBranchConfig` | `workflows` |
| 100 | `GatewayType` | `workflows` |
| 101 | `Gauge` | `sessions` |
| 102 | `GenerationRequest` | `sessions` |
| 103 | `GenerationResult` | `sessions` |
| 104 | `GenerationType` | `sessions` |
| 105 | `GenericAnalyzer` | `sessions` |
| 106 | `Histogram` | `sessions` |
| 107 | `HistoryFilter` | `sessions` |
| 108 | `HistoryPage` | `sessions` |
| 109 | `HumanApprovalRequest` | `workflows` |
| 110 | `IPCMessageType` | `sandbox` |
| 111 | `IPCResponse` | `sandbox` |
| 112 | `InvalidStateTransitionError` | `executions` |
| 113 | `JoinStrategy` | `workflows` |
| 114 | `LLMServiceProtocol` | `orchestration` |
| 115 | `LearningCase` | `learning` |
| 116 | `LearningError` | `learning` |
| 117 | `LearningInsight` | `orchestration` |
| 118 | `LearningStatistics` | `learning` |
| 119 | `LearningType` | `orchestration` |
| 120 | `MCPClientProtocol` | `sessions` |
| 121 | `MaxIterationsExceededError` | `sessions` |
| 122 | `MergeStrategy` | `workflows` |
| 123 | `MessageLimitExceededError` | `sessions` |
| 124 | `MessageRecord` | `orchestration` |
| 125 | `MessageRole` | `sessions` |
| 126 | `MessageStatistics` | `sessions` |
| 127 | `MetricType` | `sessions` |
| 128 | `MetricValue` | `sessions` |
| 129 | `MultiTurnSession` | `orchestration` |
| 130 | `NestedExecutionContext` | `orchestration` |
| 131 | `NestedWorkflowConfig` | `orchestration` |
| 132 | `NestedWorkflowType` | `orchestration` |
| 133 | `NodeExecutionResult` | `workflows` |
| 134 | `NodeType` | `workflows` |
| 135 | `NotificationError` | `notifications` |
| 136 | `NotificationPriority` | `notifications` |
| 137 | `NotificationResult` | `notifications` |
| 138 | `NotificationType` | `notifications` |
| 139 | `ParallelBranch` | `workflows` |
| 140 | `ParallelForkGateway` | `workflows` |
| 141 | `ParallelGatewayConfig` | `workflows` |
| 142 | `ParallelJoinGateway` | `workflows` |
| 143 | `ParameterType` | `templates` |
| 144 | `ParsedToolCall` | `sessions` |
| 145 | `PasswordChange` | `auth` |
| 146 | `PendingApprovalError` | `sessions` |
| 147 | `PlanAdjustment` | `orchestration` |
| 148 | `PlanEvent` | `orchestration` |
| 149 | `PlanStatus` | `orchestration` |
| 150 | `ProcessingContext` | `sessions` |
| 151 | `PromptCategory` | `prompts` |
| 152 | `PromptTemplateError` | `prompts` |
| 153 | `PropagationRule` | `orchestration` |
| 154 | `PropagationType` | `orchestration` |
| 155 | `RecursionConfig` | `orchestration` |
| 156 | `RecursionState` | `orchestration` |
| 157 | `RecursionStrategy` | `orchestration` |
| 158 | `RedisClientProtocol` | `orchestration` |
| 159 | `RelationType` | `routing` |
| 160 | `ResumeResult` | `workflows` |
| 161 | `ResumeStatus` | `workflows` |
| 162 | `RoutingError` | `routing` |
| 163 | `RoutingResult` | `routing` |
| 164 | `SQLAlchemySessionRepository` | `sessions` |
| 165 | `SandboxProcess` | `sandbox` |
| 166 | `SandboxService` | `sandbox` |
| 167 | `SandboxStatus` | `sandbox` |
| 168 | `Scenario` | `routing` |
| 169 | `ScenarioConfig` | `routing` |
| 170 | `SearchQuery` | `sessions` |
| 171 | `SearchResponse` | `sessions` |
| 172 | `SearchResult` | `sessions` |
| 173 | `SearchScope` | `sessions` |
| 174 | `SearchSortBy` | `sessions` |
| 175 | `SemanticVersion` | `versioning` |
| 176 | `SessionCheckpoint` | `sessions` |
| 177 | `SessionError` | `sessions` |
| 178 | `SessionErrorCode` | `sessions` |
| 179 | `SessionExpiredError` | `sessions` |
| 180 | `SessionMessage` | `orchestration` |
| 181 | `SessionNotActiveError` | `sessions` |
| 182 | `SessionNotFoundError` | `sessions` |
| 183 | `SessionServiceError` | `sessions` |
| 184 | `SessionServiceProtocol` | `sessions` |
| 185 | `SessionStatistics` | `sessions` |
| 186 | `SessionTag` | `sessions` |
| 187 | `SessionTemplate` | `sessions` |
| 188 | `SignatureAlgorithm` | `triggers` |
| 189 | `SignatureVerificationError` | `triggers` |
| 190 | `StreamConfig` | `sessions` |
| 191 | `SubExecutionState` | `orchestration` |
| 192 | `SubTask` | `orchestration` |
| 193 | `SubWorkflowExecutionMode` | `orchestration` |
| 194 | `SubWorkflowReference` | `orchestration` |
| 195 | `Tag` | `sessions` |
| 196 | `Task` | `tasks` |
| 197 | `TaskPriority` | `tasks` |
| 198 | `TaskResult` | `tasks` |
| 199 | `TaskService` | `tasks` |
| 200 | `TaskStatus` | `tasks` |
| 201 | `TaskType` | `tasks` |
| 202 | `TeamsCard` | `notifications` |
| 203 | `TeamsNotificationConfig` | `notifications` |
| 204 | `TemplateCategory` | `templates` |
| 205 | `TemplateError` | `templates` |
| 206 | `TemplateExample` | `templates` |
| 207 | `TemplateNotFoundError` | `prompts` |
| 208 | `TemplateParameter` | `templates` |
| 209 | `TemplateRenderError` | `prompts` |
| 210 | `TemplateStatus` | `templates` |
| 211 | `TemplateValidationError` | `prompts` |
| 212 | `TemplateVersion` | `versioning` |
| 213 | `TerminationType` | `orchestration` |
| 214 | `TimelineEntry` | `devtools` |
| 215 | `TimeoutHandler` | `workflows` |
| 216 | `TimingContext` | `sessions` |
| 217 | `TokenRefresh` | `auth` |
| 218 | `TokenResponse` | `auth` |
| 219 | `ToolError` | `agents` |
| 220 | `ToolExecutionResult` | `sessions` |
| 221 | `ToolHandlerConfig` | `sessions` |
| 222 | `ToolRegistryProtocol` | `sessions` |
| 223 | `ToolResult` | `agents` |
| 224 | `ToolSource` | `sessions` |
| 225 | `TraceEvent` | `devtools` |
| 226 | `TraceEventType` | `devtools` |
| 227 | `TraceSeverity` | `devtools` |
| 228 | `TraceSpan` | `devtools` |
| 229 | `TraceStatistics` | `devtools` |
| 230 | `TracerError` | `devtools` |
| 231 | `Trial` | `orchestration` |
| 232 | `TrialStatus` | `orchestration` |
| 233 | `TriggerExecutionError` | `triggers` |
| 234 | `TriggerResult` | `triggers` |
| 235 | `TriggerType` | `workflows` |
| 236 | `Turn` | `orchestration` |
| 237 | `TurnMessage` | `orchestration` |
| 238 | `TurnStatus` | `orchestration` |
| 239 | `UserCreate` | `auth` |
| 240 | `UserLogin` | `auth` |
| 241 | `UserResponse` | `auth` |
| 242 | `UserStatistics` | `sessions` |
| 243 | `VariableDescriptor` | `orchestration` |
| 244 | `VariableScope` | `orchestration` |
| 245 | `VariableScopeType` | `orchestration` |
| 246 | `VersionDiff` | `versioning` |
| 247 | `VersionStatistics` | `versioning` |
| 248 | `VersionStatus` | `versioning` |
| 249 | `VersioningError` | `versioning` |
| 250 | `VersioningService` | `versioning` |
| 251 | `WaitingTask` | `workflows` |
| 252 | `WebhookConfigNotFoundError` | `triggers` |
| 253 | `WebhookDisabledError` | `triggers` |
| 254 | `WebhookError` | `triggers` |
| 255 | `WebhookPayload` | `triggers` |
| 256 | `WebhookStatus` | `triggers` |
| 257 | `WebhookTriggerConfig` | `triggers` |
| 258 | `WebhookTriggerService` | `triggers` |
| 259 | `WorkflowContext` | `workflows` |
| 260 | `WorkflowCreateRequest` | `workflows` |
| 261 | `WorkflowDefinition` | `workflows` |
| 262 | `WorkflowEdge` | `workflows` |
| 263 | `WorkflowEdgeSchema` | `workflows` |
| 264 | `WorkflowEngineProtocol` | `orchestration` |
| 265 | `WorkflowExecuteRequest` | `workflows` |
| 266 | `WorkflowExecutionResponse` | `workflows` |
| 267 | `WorkflowExecutionResult` | `workflows` |
| 268 | `WorkflowGraphSchema` | `workflows` |
| 269 | `WorkflowListResponse` | `workflows` |
| 270 | `WorkflowNode` | `workflows` |
| 271 | `WorkflowNodeSchema` | `workflows` |
| 272 | `WorkflowResponse` | `workflows` |
| 273 | `WorkflowResumeService` | `workflows` |
| 274 | `WorkflowScope` | `orchestration` |
| 275 | `WorkflowServiceProtocol` | `orchestration` |
| 276 | `WorkflowUpdateRequest` | `workflows` |
| 277 | `WorkflowValidationResponse` | `workflows` |

---

## 7. All Domain Classes -- Complete Master List

Complete list of all classes found in `src/domain/` by AST scan, sorted by module.

| # | Class Name | Module | File |
|---|-----------|--------|------|
| 1 | `AgentConfig` | `agents` | `src/domain/agents/service.py` |
| 2 | `AgentCreateRequest` | `agents` | `src/domain/agents/schemas.py` |
| 3 | `AgentExecutionResult` | `agents` | `src/domain/agents/service.py` |
| 4 | `AgentListResponse` | `agents` | `src/domain/agents/schemas.py` |
| 5 | `AgentResponse` | `agents` | `src/domain/agents/schemas.py` |
| 6 | `AgentRunRequest` | `agents` | `src/domain/agents/schemas.py` |
| 7 | `AgentRunResponse` | `agents` | `src/domain/agents/schemas.py` |
| 8 | `AgentService` | `agents` | `src/domain/agents/service.py` |
| 9 | `AgentUpdateRequest` | `agents` | `src/domain/agents/schemas.py` |
| 10 | `BaseTool` | `agents` | `src/domain/agents/tools/base.py` |
| 11 | `Config` | `agents` | `src/domain/agents/schemas.py` |
| 12 | `Config` | `agents` | `src/domain/agents/schemas.py` |
| 13 | `Config` | `agents` | `src/domain/agents/schemas.py` |
| 14 | `Config` | `agents` | `src/domain/agents/schemas.py` |
| 15 | `DateTimeTool` | `agents` | `src/domain/agents/tools/builtin.py` |
| 16 | `FunctionTool` | `agents` | `src/domain/agents/tools/base.py` |
| 17 | `HttpTool` | `agents` | `src/domain/agents/tools/builtin.py` |
| 18 | `ToolError` | `agents` | `src/domain/agents/tools/base.py` |
| 19 | `ToolRegistry` | `agents` | `src/domain/agents/tools/registry.py` |
| 20 | `ToolResult` | `agents` | `src/domain/agents/tools/base.py` |
| 21 | `AuditAction` | `audit` | `src/domain/audit/logger.py` |
| 22 | `AuditEntry` | `audit` | `src/domain/audit/logger.py` |
| 23 | `AuditError` | `audit` | `src/domain/audit/logger.py` |
| 24 | `AuditLogger` | `audit` | `src/domain/audit/logger.py` |
| 25 | `AuditQueryParams` | `audit` | `src/domain/audit/logger.py` |
| 26 | `AuditResource` | `audit` | `src/domain/audit/logger.py` |
| 27 | `AuditSeverity` | `audit` | `src/domain/audit/logger.py` |
| 28 | `AuthService` | `auth` | `src/domain/auth/service.py` |
| 29 | `PasswordChange` | `auth` | `src/domain/auth/schemas.py` |
| 30 | `TokenRefresh` | `auth` | `src/domain/auth/schemas.py` |
| 31 | `TokenResponse` | `auth` | `src/domain/auth/schemas.py` |
| 32 | `UserCreate` | `auth` | `src/domain/auth/schemas.py` |
| 33 | `UserLogin` | `auth` | `src/domain/auth/schemas.py` |
| 34 | `UserResponse` | `auth` | `src/domain/auth/schemas.py` |
| 35 | `ChatHistorySync` | `chat_history` | `src/domain/chat_history/models.py` |
| 36 | `ChatMessage` | `chat_history` | `src/domain/chat_history/models.py` |
| 37 | `ChatSyncResponse` | `chat_history` | `src/domain/chat_history/models.py` |
| 38 | `CheckpointData` | `checkpoints` | `src/domain/checkpoints/service.py` |
| 39 | `CheckpointService` | `checkpoints` | `src/domain/checkpoints/service.py` |
| 40 | `CheckpointStatus` | `checkpoints` | `src/domain/checkpoints/service.py` |
| 41 | `CheckpointStorage` | `checkpoints` | `src/domain/checkpoints/storage.py` |
| 42 | `DatabaseCheckpointStorage` | `checkpoints` | `src/domain/checkpoints/storage.py` |
| 43 | `AuthType` | `connectors` | `src/domain/connectors/base.py` |
| 44 | `BaseConnector` | `connectors` | `src/domain/connectors/base.py` |
| 45 | `ConnectorConfig` | `connectors` | `src/domain/connectors/base.py` |
| 46 | `ConnectorError` | `connectors` | `src/domain/connectors/base.py` |
| 47 | `ConnectorRegistry` | `connectors` | `src/domain/connectors/registry.py` |
| 48 | `ConnectorResponse` | `connectors` | `src/domain/connectors/base.py` |
| 49 | `ConnectorStatus` | `connectors` | `src/domain/connectors/base.py` |
| 50 | `Dynamics365Connector` | `connectors` | `src/domain/connectors/dynamics365.py` |
| 51 | `ServiceNowConnector` | `connectors` | `src/domain/connectors/servicenow.py` |
| 52 | `SharePointConnector` | `connectors` | `src/domain/connectors/sharepoint.py` |
| 53 | `ExecutionTrace` | `devtools` | `src/domain/devtools/tracer.py` |
| 54 | `ExecutionTracer` | `devtools` | `src/domain/devtools/tracer.py` |
| 55 | `TimelineEntry` | `devtools` | `src/domain/devtools/tracer.py` |
| 56 | `TraceEvent` | `devtools` | `src/domain/devtools/tracer.py` |
| 57 | `TraceEventType` | `devtools` | `src/domain/devtools/tracer.py` |
| 58 | `TraceSeverity` | `devtools` | `src/domain/devtools/tracer.py` |
| 59 | `TraceSpan` | `devtools` | `src/domain/devtools/tracer.py` |
| 60 | `TraceStatistics` | `devtools` | `src/domain/devtools/tracer.py` |
| 61 | `TracerError` | `devtools` | `src/domain/devtools/tracer.py` |
| 62 | `ExecutionStateMachine` | `executions` | `src/domain/executions/state_machine.py` |
| 63 | `ExecutionStatus` | `executions` | `src/domain/executions/state_machine.py` |
| 64 | `InvalidStateTransitionError` | `executions` | `src/domain/executions/state_machine.py` |
| 65 | `FileService` | `files` | `src/domain/files/service.py` |
| 66 | `FileStorage` | `files` | `src/domain/files/storage.py` |
| 67 | `FileValidationError` | `files` | `src/domain/files/service.py` |
| 68 | `CaseStatus` | `learning` | `src/domain/learning/service.py` |
| 69 | `LearningCase` | `learning` | `src/domain/learning/service.py` |
| 70 | `LearningError` | `learning` | `src/domain/learning/service.py` |
| 71 | `LearningService` | `learning` | `src/domain/learning/service.py` |
| 72 | `LearningStatistics` | `learning` | `src/domain/learning/service.py` |
| 73 | `NotificationError` | `notifications` | `src/domain/notifications/teams.py` |
| 74 | `NotificationPriority` | `notifications` | `src/domain/notifications/teams.py` |
| 75 | `NotificationResult` | `notifications` | `src/domain/notifications/teams.py` |
| 76 | `NotificationType` | `notifications` | `src/domain/notifications/teams.py` |
| 77 | `TeamsCard` | `notifications` | `src/domain/notifications/teams.py` |
| 78 | `TeamsNotificationConfig` | `notifications` | `src/domain/notifications/teams.py` |
| 79 | `TeamsNotificationService` | `notifications` | `src/domain/notifications/teams.py` |
| 80 | `AgentRegistryProtocol` | `orchestration` | `src/domain/orchestration/planning/task_decomposer.py` |
| 81 | `AutonomousDecisionEngine` | `orchestration` | `src/domain/orchestration/planning/decision_engine.py` |
| 82 | `CheckpointServiceProtocol` | `orchestration` | `src/domain/orchestration/nested/sub_executor.py` |
| 83 | `CompositionBlock` | `orchestration` | `src/domain/orchestration/nested/composition_builder.py` |
| 84 | `CompositionType` | `orchestration` | `src/domain/orchestration/nested/composition_builder.py` |
| 85 | `ContextEntry` | `orchestration` | `src/domain/orchestration/multiturn/context_manager.py` |
| 86 | `ContextPropagator` | `orchestration` | `src/domain/orchestration/nested/context_propagation.py` |
| 87 | `ContextScope` | `orchestration` | `src/domain/orchestration/multiturn/context_manager.py` |
| 88 | `ConversationMemoryStore` | `orchestration` | `src/domain/orchestration/memory/base.py` |
| 89 | `ConversationSession` | `orchestration` | `src/domain/orchestration/memory/models.py` |
| 90 | `ConversationTurn` | `orchestration` | `src/domain/orchestration/memory/models.py` |
| 91 | `DataFlowDirection` | `orchestration` | `src/domain/orchestration/nested/context_propagation.py` |
| 92 | `DataFlowEvent` | `orchestration` | `src/domain/orchestration/nested/context_propagation.py` |
| 93 | `DataFlowTracker` | `orchestration` | `src/domain/orchestration/nested/context_propagation.py` |
| 94 | `DatabaseSessionProtocol` | `orchestration` | `src/domain/orchestration/memory/postgres_store.py` |
| 95 | `Decision` | `orchestration` | `src/domain/orchestration/planning/decision_engine.py` |
| 96 | `DecisionConfidence` | `orchestration` | `src/domain/orchestration/planning/decision_engine.py` |
| 97 | `DecisionEngineProtocol` | `orchestration` | `src/domain/orchestration/planning/dynamic_planner.py` |
| 98 | `DecisionOption` | `orchestration` | `src/domain/orchestration/planning/decision_engine.py` |
| 99 | `DecisionRule` | `orchestration` | `src/domain/orchestration/planning/decision_engine.py` |
| 100 | `DecisionType` | `orchestration` | `src/domain/orchestration/planning/decision_engine.py` |
| 101 | `DecompositionResult` | `orchestration` | `src/domain/orchestration/planning/task_decomposer.py` |
| 102 | `DecompositionStrategy` | `orchestration` | `src/domain/orchestration/planning/task_decomposer.py` |
| 103 | `DependencyType` | `orchestration` | `src/domain/orchestration/planning/task_decomposer.py` |
| 104 | `DynamicPlanner` | `orchestration` | `src/domain/orchestration/planning/dynamic_planner.py` |
| 105 | `ErrorFix` | `orchestration` | `src/domain/orchestration/planning/trial_error.py` |
| 106 | `ExecutionPlan` | `orchestration` | `src/domain/orchestration/planning/dynamic_planner.py` |
| 107 | `ExecutionServiceProtocol` | `orchestration` | `src/domain/orchestration/nested/workflow_manager.py` |
| 108 | `InMemoryConversationMemoryStore` | `orchestration` | `src/domain/orchestration/memory/in_memory.py` |
| 109 | `LLMServiceProtocol` | `orchestration` | `src/domain/orchestration/planning/decision_engine.py` |
| 110 | `LLMServiceProtocol` | `orchestration` | `src/domain/orchestration/planning/dynamic_planner.py` |
| 111 | `LLMServiceProtocol` | `orchestration` | `src/domain/orchestration/planning/task_decomposer.py` |
| 112 | `LLMServiceProtocol` | `orchestration` | `src/domain/orchestration/planning/trial_error.py` |
| 113 | `LearningInsight` | `orchestration` | `src/domain/orchestration/planning/trial_error.py` |
| 114 | `LearningType` | `orchestration` | `src/domain/orchestration/planning/trial_error.py` |
| 115 | `MessageRecord` | `orchestration` | `src/domain/orchestration/memory/models.py` |
| 116 | `MultiTurnSession` | `orchestration` | `src/domain/orchestration/multiturn/session_manager.py` |
| 117 | `MultiTurnSessionManager` | `orchestration` | `src/domain/orchestration/multiturn/session_manager.py` |
| 118 | `NestedExecutionContext` | `orchestration` | `src/domain/orchestration/nested/workflow_manager.py` |
| 119 | `NestedWorkflowConfig` | `orchestration` | `src/domain/orchestration/nested/workflow_manager.py` |
| 120 | `NestedWorkflowManager` | `orchestration` | `src/domain/orchestration/nested/workflow_manager.py` |
| 121 | `NestedWorkflowType` | `orchestration` | `src/domain/orchestration/nested/workflow_manager.py` |
| 122 | `PlanAdjustment` | `orchestration` | `src/domain/orchestration/planning/dynamic_planner.py` |
| 123 | `PlanEvent` | `orchestration` | `src/domain/orchestration/planning/dynamic_planner.py` |
| 124 | `PlanStatus` | `orchestration` | `src/domain/orchestration/planning/dynamic_planner.py` |
| 125 | `PostgresConversationMemoryStore` | `orchestration` | `src/domain/orchestration/memory/postgres_store.py` |
| 126 | `PropagationRule` | `orchestration` | `src/domain/orchestration/nested/context_propagation.py` |
| 127 | `PropagationType` | `orchestration` | `src/domain/orchestration/nested/context_propagation.py` |
| 128 | `RecursionConfig` | `orchestration` | `src/domain/orchestration/nested/recursive_handler.py` |
| 129 | `RecursionState` | `orchestration` | `src/domain/orchestration/nested/recursive_handler.py` |
| 130 | `RecursionStrategy` | `orchestration` | `src/domain/orchestration/nested/recursive_handler.py` |
| 131 | `RecursivePatternHandler` | `orchestration` | `src/domain/orchestration/nested/recursive_handler.py` |
| 132 | `RedisClientProtocol` | `orchestration` | `src/domain/orchestration/memory/redis_store.py` |
| 133 | `RedisConversationMemoryStore` | `orchestration` | `src/domain/orchestration/memory/redis_store.py` |
| 134 | `SessionContextManager` | `orchestration` | `src/domain/orchestration/multiturn/context_manager.py` |
| 135 | `SessionMessage` | `orchestration` | `src/domain/orchestration/multiturn/session_manager.py` |
| 136 | `SessionStatus` | `orchestration` | `src/domain/orchestration/memory/models.py` |
| 137 | `SessionStatus` | `orchestration` | `src/domain/orchestration/multiturn/session_manager.py` |
| 138 | `SubExecutionState` | `orchestration` | `src/domain/orchestration/nested/sub_executor.py` |
| 139 | `SubTask` | `orchestration` | `src/domain/orchestration/planning/task_decomposer.py` |
| 140 | `SubWorkflowExecutionMode` | `orchestration` | `src/domain/orchestration/nested/sub_executor.py` |
| 141 | `SubWorkflowExecutor` | `orchestration` | `src/domain/orchestration/nested/sub_executor.py` |
| 142 | `SubWorkflowReference` | `orchestration` | `src/domain/orchestration/nested/workflow_manager.py` |
| 143 | `TaskDecomposer` | `orchestration` | `src/domain/orchestration/planning/task_decomposer.py` |
| 144 | `TaskPriority` | `orchestration` | `src/domain/orchestration/planning/task_decomposer.py` |
| 145 | `TaskStatus` | `orchestration` | `src/domain/orchestration/planning/task_decomposer.py` |
| 146 | `TerminationType` | `orchestration` | `src/domain/orchestration/nested/recursive_handler.py` |
| 147 | `Trial` | `orchestration` | `src/domain/orchestration/planning/trial_error.py` |
| 148 | `TrialAndErrorEngine` | `orchestration` | `src/domain/orchestration/planning/trial_error.py` |
| 149 | `TrialStatus` | `orchestration` | `src/domain/orchestration/planning/trial_error.py` |
| 150 | `Turn` | `orchestration` | `src/domain/orchestration/multiturn/turn_tracker.py` |
| 151 | `TurnMessage` | `orchestration` | `src/domain/orchestration/multiturn/turn_tracker.py` |
| 152 | `TurnStatus` | `orchestration` | `src/domain/orchestration/multiturn/turn_tracker.py` |
| 153 | `TurnTracker` | `orchestration` | `src/domain/orchestration/multiturn/turn_tracker.py` |
| 154 | `VariableDescriptor` | `orchestration` | `src/domain/orchestration/nested/context_propagation.py` |
| 155 | `VariableScope` | `orchestration` | `src/domain/orchestration/nested/context_propagation.py` |
| 156 | `VariableScopeType` | `orchestration` | `src/domain/orchestration/nested/context_propagation.py` |
| 157 | `WorkflowCompositionBuilder` | `orchestration` | `src/domain/orchestration/nested/composition_builder.py` |
| 158 | `WorkflowEngineProtocol` | `orchestration` | `src/domain/orchestration/nested/sub_executor.py` |
| 159 | `WorkflowNode` | `orchestration` | `src/domain/orchestration/nested/composition_builder.py` |
| 160 | `WorkflowScope` | `orchestration` | `src/domain/orchestration/nested/workflow_manager.py` |
| 161 | `WorkflowServiceProtocol` | `orchestration` | `src/domain/orchestration/nested/workflow_manager.py` |
| 162 | `PromptCategory` | `prompts` | `src/domain/prompts/template.py` |
| 163 | `PromptTemplate` | `prompts` | `src/domain/prompts/template.py` |
| 164 | `PromptTemplateError` | `prompts` | `src/domain/prompts/template.py` |
| 165 | `PromptTemplateManager` | `prompts` | `src/domain/prompts/template.py` |
| 166 | `TemplateNotFoundError` | `prompts` | `src/domain/prompts/template.py` |
| 167 | `TemplateRenderError` | `prompts` | `src/domain/prompts/template.py` |
| 168 | `TemplateValidationError` | `prompts` | `src/domain/prompts/template.py` |
| 169 | `ExecutionRelation` | `routing` | `src/domain/routing/scenario_router.py` |
| 170 | `RelationType` | `routing` | `src/domain/routing/scenario_router.py` |
| 171 | `RoutingError` | `routing` | `src/domain/routing/scenario_router.py` |
| 172 | `RoutingResult` | `routing` | `src/domain/routing/scenario_router.py` |
| 173 | `Scenario` | `routing` | `src/domain/routing/scenario_router.py` |
| 174 | `ScenarioConfig` | `routing` | `src/domain/routing/scenario_router.py` |
| 175 | `ScenarioRouter` | `routing` | `src/domain/routing/scenario_router.py` |
| 176 | `IPCMessageType` | `sandbox` | `src/domain/sandbox/service.py` |
| 177 | `IPCResponse` | `sandbox` | `src/domain/sandbox/service.py` |
| 178 | `SandboxProcess` | `sandbox` | `src/domain/sandbox/service.py` |
| 179 | `SandboxService` | `sandbox` | `src/domain/sandbox/service.py` |
| 180 | `SandboxStatus` | `sandbox` | `src/domain/sandbox/service.py` |
| 181 | `AgentConfig` | `sessions` | `src/domain/sessions/executor.py` |
| 182 | `AgentExecutor` | `sessions` | `src/domain/sessions/executor.py` |
| 183 | `AgentNotFoundError` | `sessions` | `src/domain/sessions/bridge.py` |
| 184 | `AgentRepositoryProtocol` | `sessions` | `src/domain/sessions/bridge.py` |
| 185 | `AnalysisRequest` | `sessions` | `src/domain/sessions/files/types.py` |
| 186 | `AnalysisResult` | `sessions` | `src/domain/sessions/files/types.py` |
| 187 | `AnalysisType` | `sessions` | `src/domain/sessions/files/types.py` |
| 188 | `ApprovalAlreadyResolvedError` | `sessions` | `src/domain/sessions/approval.py` |
| 189 | `ApprovalCacheProtocol` | `sessions` | `src/domain/sessions/approval.py` |
| 190 | `ApprovalError` | `sessions` | `src/domain/sessions/approval.py` |
| 191 | `ApprovalExpiredError` | `sessions` | `src/domain/sessions/approval.py` |
| 192 | `ApprovalNotFoundError` | `sessions` | `src/domain/sessions/approval.py` |
| 193 | `ApprovalStatus` | `sessions` | `src/domain/sessions/approval.py` |
| 194 | `Attachment` | `sessions` | `src/domain/sessions/models.py` |
| 195 | `AttachmentType` | `sessions` | `src/domain/sessions/models.py` |
| 196 | `BaseAnalyzer` | `sessions` | `src/domain/sessions/files/analyzer.py` |
| 197 | `BaseGenerator` | `sessions` | `src/domain/sessions/files/generator.py` |
| 198 | `Bookmark` | `sessions` | `src/domain/sessions/history/bookmarks.py` |
| 199 | `BookmarkFilter` | `sessions` | `src/domain/sessions/history/bookmarks.py` |
| 200 | `BookmarkService` | `sessions` | `src/domain/sessions/history/bookmarks.py` |
| 201 | `BridgeConfig` | `sessions` | `src/domain/sessions/bridge.py` |
| 202 | `BridgeError` | `sessions` | `src/domain/sessions/bridge.py` |
| 203 | `CacheProtocol` | `sessions` | `src/domain/sessions/recovery.py` |
| 204 | `ChatMessage` | `sessions` | `src/domain/sessions/executor.py` |
| 205 | `CheckpointType` | `sessions` | `src/domain/sessions/recovery.py` |
| 206 | `CodeGenerator` | `sessions` | `src/domain/sessions/files/code_generator.py` |
| 207 | `Counter` | `sessions` | `src/domain/sessions/metrics.py` |
| 208 | `DataAnalyzer` | `sessions` | `src/domain/sessions/files/data_analyzer.py` |
| 209 | `DataExporter` | `sessions` | `src/domain/sessions/files/data_exporter.py` |
| 210 | `DocumentAnalyzer` | `sessions` | `src/domain/sessions/files/document_analyzer.py` |
| 211 | `ExecutionConfig` | `sessions` | `src/domain/sessions/executor.py` |
| 212 | `ExecutionEvent` | `sessions` | `src/domain/sessions/events.py` |
| 213 | `ExecutionEventFactory` | `sessions` | `src/domain/sessions/events.py` |
| 214 | `ExecutionEventType` | `sessions` | `src/domain/sessions/events.py` |
| 215 | `ExecutionResult` | `sessions` | `src/domain/sessions/executor.py` |
| 216 | `ExportFormat` | `sessions` | `src/domain/sessions/files/types.py` |
| 217 | `FileAnalyzer` | `sessions` | `src/domain/sessions/files/analyzer.py` |
| 218 | `FileGenerator` | `sessions` | `src/domain/sessions/files/generator.py` |
| 219 | `Gauge` | `sessions` | `src/domain/sessions/metrics.py` |
| 220 | `GenerationRequest` | `sessions` | `src/domain/sessions/files/types.py` |
| 221 | `GenerationResult` | `sessions` | `src/domain/sessions/files/types.py` |
| 222 | `GenerationType` | `sessions` | `src/domain/sessions/files/types.py` |
| 223 | `GenericAnalyzer` | `sessions` | `src/domain/sessions/files/analyzer.py` |
| 224 | `Histogram` | `sessions` | `src/domain/sessions/metrics.py` |
| 225 | `HistoryFilter` | `sessions` | `src/domain/sessions/history/manager.py` |
| 226 | `HistoryManager` | `sessions` | `src/domain/sessions/history/manager.py` |
| 227 | `HistoryPage` | `sessions` | `src/domain/sessions/history/manager.py` |
| 228 | `ImageAnalyzer` | `sessions` | `src/domain/sessions/files/image_analyzer.py` |
| 229 | `MCPClientProtocol` | `sessions` | `src/domain/sessions/executor.py` |
| 230 | `MCPClientProtocol` | `sessions` | `src/domain/sessions/tool_handler.py` |
| 231 | `MaxIterationsExceededError` | `sessions` | `src/domain/sessions/bridge.py` |
| 232 | `Message` | `sessions` | `src/domain/sessions/models.py` |
| 233 | `MessageLimitExceededError` | `sessions` | `src/domain/sessions/service.py` |
| 234 | `MessageRole` | `sessions` | `src/domain/sessions/executor.py` |
| 235 | `MessageRole` | `sessions` | `src/domain/sessions/models.py` |
| 236 | `MessageStatistics` | `sessions` | `src/domain/sessions/features/statistics.py` |
| 237 | `MetricType` | `sessions` | `src/domain/sessions/metrics.py` |
| 238 | `MetricValue` | `sessions` | `src/domain/sessions/metrics.py` |
| 239 | `MetricsCollector` | `sessions` | `src/domain/sessions/metrics.py` |
| 240 | `ParsedToolCall` | `sessions` | `src/domain/sessions/tool_handler.py` |
| 241 | `PendingApprovalError` | `sessions` | `src/domain/sessions/bridge.py` |
| 242 | `ProcessingContext` | `sessions` | `src/domain/sessions/bridge.py` |
| 243 | `ReportGenerator` | `sessions` | `src/domain/sessions/files/report_generator.py` |
| 244 | `SQLAlchemySessionRepository` | `sessions` | `src/domain/sessions/repository.py` |
| 245 | `SearchQuery` | `sessions` | `src/domain/sessions/history/search.py` |
| 246 | `SearchResponse` | `sessions` | `src/domain/sessions/history/search.py` |
| 247 | `SearchResult` | `sessions` | `src/domain/sessions/history/search.py` |
| 248 | `SearchScope` | `sessions` | `src/domain/sessions/history/search.py` |
| 249 | `SearchService` | `sessions` | `src/domain/sessions/history/search.py` |
| 250 | `SearchSortBy` | `sessions` | `src/domain/sessions/history/search.py` |
| 251 | `Session` | `sessions` | `src/domain/sessions/models.py` |
| 252 | `SessionAgentBridge` | `sessions` | `src/domain/sessions/bridge.py` |
| 253 | `SessionCache` | `sessions` | `src/domain/sessions/cache.py` |
| 254 | `SessionCheckpoint` | `sessions` | `src/domain/sessions/recovery.py` |
| 255 | `SessionConfig` | `sessions` | `src/domain/sessions/models.py` |
| 256 | `SessionError` | `sessions` | `src/domain/sessions/error_handler.py` |
| 257 | `SessionErrorCode` | `sessions` | `src/domain/sessions/error_handler.py` |
| 258 | `SessionErrorHandler` | `sessions` | `src/domain/sessions/error_handler.py` |
| 259 | `SessionEvent` | `sessions` | `src/domain/sessions/events.py` |
| 260 | `SessionEventPublisher` | `sessions` | `src/domain/sessions/events.py` |
| 261 | `SessionEventType` | `sessions` | `src/domain/sessions/events.py` |
| 262 | `SessionExpiredError` | `sessions` | `src/domain/sessions/service.py` |
| 263 | `SessionNotActiveError` | `sessions` | `src/domain/sessions/bridge.py` |
| 264 | `SessionNotActiveError` | `sessions` | `src/domain/sessions/service.py` |
| 265 | `SessionNotFoundError` | `sessions` | `src/domain/sessions/bridge.py` |
| 266 | `SessionNotFoundError` | `sessions` | `src/domain/sessions/service.py` |
| 267 | `SessionRecoveryManager` | `sessions` | `src/domain/sessions/recovery.py` |
| 268 | `SessionRepository` | `sessions` | `src/domain/sessions/repository.py` |
| 269 | `SessionService` | `sessions` | `src/domain/sessions/service.py` |
| 270 | `SessionServiceError` | `sessions` | `src/domain/sessions/service.py` |
| 271 | `SessionServiceProtocol` | `sessions` | `src/domain/sessions/bridge.py` |
| 272 | `SessionStatistics` | `sessions` | `src/domain/sessions/features/statistics.py` |
| 273 | `SessionStatus` | `sessions` | `src/domain/sessions/models.py` |
| 274 | `SessionTag` | `sessions` | `src/domain/sessions/features/tags.py` |
| 275 | `SessionTemplate` | `sessions` | `src/domain/sessions/features/templates.py` |
| 276 | `StatisticsService` | `sessions` | `src/domain/sessions/features/statistics.py` |
| 277 | `StreamConfig` | `sessions` | `src/domain/sessions/streaming.py` |
| 278 | `StreamState` | `sessions` | `src/domain/sessions/streaming.py` |
| 279 | `StreamStats` | `sessions` | `src/domain/sessions/streaming.py` |
| 280 | `StreamingLLMHandler` | `sessions` | `src/domain/sessions/streaming.py` |
| 281 | `Tag` | `sessions` | `src/domain/sessions/features/tags.py` |
| 282 | `TagService` | `sessions` | `src/domain/sessions/features/tags.py` |
| 283 | `TemplateCategory` | `sessions` | `src/domain/sessions/features/templates.py` |
| 284 | `TemplateService` | `sessions` | `src/domain/sessions/features/templates.py` |
| 285 | `TimingContext` | `sessions` | `src/domain/sessions/metrics.py` |
| 286 | `TokenCounter` | `sessions` | `src/domain/sessions/streaming.py` |
| 287 | `ToolApprovalManager` | `sessions` | `src/domain/sessions/approval.py` |
| 288 | `ToolApprovalRequest` | `sessions` | `src/domain/sessions/approval.py` |
| 289 | `ToolCall` | `sessions` | `src/domain/sessions/models.py` |
| 290 | `ToolCallDelta` | `sessions` | `src/domain/sessions/streaming.py` |
| 291 | `ToolCallHandler` | `sessions` | `src/domain/sessions/tool_handler.py` |
| 292 | `ToolCallInfo` | `sessions` | `src/domain/sessions/events.py` |
| 293 | `ToolCallParser` | `sessions` | `src/domain/sessions/tool_handler.py` |
| 294 | `ToolCallStatus` | `sessions` | `src/domain/sessions/models.py` |
| 295 | `ToolExecutionResult` | `sessions` | `src/domain/sessions/tool_handler.py` |
| 296 | `ToolHandlerConfig` | `sessions` | `src/domain/sessions/tool_handler.py` |
| 297 | `ToolHandlerStats` | `sessions` | `src/domain/sessions/tool_handler.py` |
| 298 | `ToolPermission` | `sessions` | `src/domain/sessions/tool_handler.py` |
| 299 | `ToolRegistryProtocol` | `sessions` | `src/domain/sessions/tool_handler.py` |
| 300 | `ToolResultInfo` | `sessions` | `src/domain/sessions/events.py` |
| 301 | `ToolSource` | `sessions` | `src/domain/sessions/tool_handler.py` |
| 302 | `UsageInfo` | `sessions` | `src/domain/sessions/events.py` |
| 303 | `UserStatistics` | `sessions` | `src/domain/sessions/features/statistics.py` |
| 304 | `Task` | `tasks` | `src/domain/tasks/models.py` |
| 305 | `TaskPriority` | `tasks` | `src/domain/tasks/models.py` |
| 306 | `TaskResult` | `tasks` | `src/domain/tasks/models.py` |
| 307 | `TaskService` | `tasks` | `src/domain/tasks/service.py` |
| 308 | `TaskStatus` | `tasks` | `src/domain/tasks/models.py` |
| 309 | `TaskType` | `tasks` | `src/domain/tasks/models.py` |
| 310 | `AgentTemplate` | `templates` | `src/domain/templates/models.py` |
| 311 | `ParameterType` | `templates` | `src/domain/templates/models.py` |
| 312 | `TemplateCategory` | `templates` | `src/domain/templates/models.py` |
| 313 | `TemplateError` | `templates` | `src/domain/templates/service.py` |
| 314 | `TemplateExample` | `templates` | `src/domain/templates/models.py` |
| 315 | `TemplateParameter` | `templates` | `src/domain/templates/models.py` |
| 316 | `TemplateService` | `templates` | `src/domain/templates/service.py` |
| 317 | `TemplateStatus` | `templates` | `src/domain/templates/models.py` |
| 318 | `TemplateVersion` | `templates` | `src/domain/templates/models.py` |
| 319 | `SignatureAlgorithm` | `triggers` | `src/domain/triggers/webhook.py` |
| 320 | `SignatureVerificationError` | `triggers` | `src/domain/triggers/webhook.py` |
| 321 | `TriggerExecutionError` | `triggers` | `src/domain/triggers/webhook.py` |
| 322 | `TriggerResult` | `triggers` | `src/domain/triggers/webhook.py` |
| 323 | `WebhookConfigNotFoundError` | `triggers` | `src/domain/triggers/webhook.py` |
| 324 | `WebhookDisabledError` | `triggers` | `src/domain/triggers/webhook.py` |
| 325 | `WebhookError` | `triggers` | `src/domain/triggers/webhook.py` |
| 326 | `WebhookPayload` | `triggers` | `src/domain/triggers/webhook.py` |
| 327 | `WebhookStatus` | `triggers` | `src/domain/triggers/webhook.py` |
| 328 | `WebhookTriggerConfig` | `triggers` | `src/domain/triggers/webhook.py` |
| 329 | `WebhookTriggerService` | `triggers` | `src/domain/triggers/webhook.py` |
| 330 | `ChangeType` | `versioning` | `src/domain/versioning/service.py` |
| 331 | `DiffHunk` | `versioning` | `src/domain/versioning/service.py` |
| 332 | `DiffLine` | `versioning` | `src/domain/versioning/service.py` |
| 333 | `SemanticVersion` | `versioning` | `src/domain/versioning/service.py` |
| 334 | `TemplateVersion` | `versioning` | `src/domain/versioning/service.py` |
| 335 | `VersionDiff` | `versioning` | `src/domain/versioning/service.py` |
| 336 | `VersionStatistics` | `versioning` | `src/domain/versioning/service.py` |
| 337 | `VersionStatus` | `versioning` | `src/domain/versioning/service.py` |
| 338 | `VersioningError` | `versioning` | `src/domain/versioning/service.py` |
| 339 | `VersioningService` | `versioning` | `src/domain/versioning/service.py` |
| 340 | `ApprovalAction` | `workflows` | `src/domain/workflows/executors/approval.py` |
| 341 | `ApprovalGateway` | `workflows` | `src/domain/workflows/executors/approval.py` |
| 342 | `ApprovalResponse` | `workflows` | `src/domain/workflows/executors/approval.py` |
| 343 | `BranchStatus` | `workflows` | `src/domain/workflows/executors/concurrent_state.py` |
| 344 | `ConcurrentExecutionState` | `workflows` | `src/domain/workflows/executors/concurrent_state.py` |
| 345 | `ConcurrentExecutor` | `workflows` | `src/domain/workflows/executors/concurrent.py` |
| 346 | `ConcurrentMode` | `workflows` | `src/domain/workflows/executors/concurrent.py` |
| 347 | `ConcurrentResult` | `workflows` | `src/domain/workflows/executors/concurrent.py` |
| 348 | `ConcurrentStateManager` | `workflows` | `src/domain/workflows/executors/concurrent_state.py` |
| 349 | `ConcurrentTask` | `workflows` | `src/domain/workflows/executors/concurrent.py` |
| 350 | `Config` | `workflows` | `src/domain/workflows/schemas.py` |
| 351 | `Config` | `workflows` | `src/domain/workflows/schemas.py` |
| 352 | `Config` | `workflows` | `src/domain/workflows/schemas.py` |
| 353 | `Config` | `workflows` | `src/domain/workflows/schemas.py` |
| 354 | `Config` | `workflows` | `src/domain/workflows/schemas.py` |
| 355 | `Config` | `workflows` | `src/domain/workflows/schemas.py` |
| 356 | `DeadlockDetector` | `workflows` | `src/domain/workflows/deadlock_detector.py` |
| 357 | `DeadlockInfo` | `workflows` | `src/domain/workflows/deadlock_detector.py` |
| 358 | `DeadlockResolutionStrategy` | `workflows` | `src/domain/workflows/deadlock_detector.py` |
| 359 | `ForkBranchConfig` | `workflows` | `src/domain/workflows/executors/parallel_gateway.py` |
| 360 | `GatewayType` | `workflows` | `src/domain/workflows/models.py` |
| 361 | `HumanApprovalRequest` | `workflows` | `src/domain/workflows/executors/approval.py` |
| 362 | `JoinStrategy` | `workflows` | `src/domain/workflows/executors/parallel_gateway.py` |
| 363 | `MergeStrategy` | `workflows` | `src/domain/workflows/executors/parallel_gateway.py` |
| 364 | `NodeExecutionResult` | `workflows` | `src/domain/workflows/schemas.py` |
| 365 | `NodeExecutionResult` | `workflows` | `src/domain/workflows/service.py` |
| 366 | `NodeType` | `workflows` | `src/domain/workflows/models.py` |
| 367 | `ParallelBranch` | `workflows` | `src/domain/workflows/executors/concurrent_state.py` |
| 368 | `ParallelForkGateway` | `workflows` | `src/domain/workflows/executors/parallel_gateway.py` |
| 369 | `ParallelGatewayConfig` | `workflows` | `src/domain/workflows/executors/parallel_gateway.py` |
| 370 | `ParallelJoinGateway` | `workflows` | `src/domain/workflows/executors/parallel_gateway.py` |
| 371 | `ResumeResult` | `workflows` | `src/domain/workflows/resume_service.py` |
| 372 | `ResumeStatus` | `workflows` | `src/domain/workflows/resume_service.py` |
| 373 | `TimeoutHandler` | `workflows` | `src/domain/workflows/deadlock_detector.py` |
| 374 | `TriggerType` | `workflows` | `src/domain/workflows/models.py` |
| 375 | `WaitingTask` | `workflows` | `src/domain/workflows/deadlock_detector.py` |
| 376 | `WorkflowContext` | `workflows` | `src/domain/workflows/models.py` |
| 377 | `WorkflowCreateRequest` | `workflows` | `src/domain/workflows/schemas.py` |
| 378 | `WorkflowDefinition` | `workflows` | `src/domain/workflows/models.py` |
| 379 | `WorkflowEdge` | `workflows` | `src/domain/workflows/models.py` |
| 380 | `WorkflowEdgeSchema` | `workflows` | `src/domain/workflows/schemas.py` |
| 381 | `WorkflowExecuteRequest` | `workflows` | `src/domain/workflows/schemas.py` |
| 382 | `WorkflowExecutionResponse` | `workflows` | `src/domain/workflows/schemas.py` |
| 383 | `WorkflowExecutionResult` | `workflows` | `src/domain/workflows/service.py` |
| 384 | `WorkflowExecutionService` | `workflows` | `src/domain/workflows/service.py` |
| 385 | `WorkflowGraphSchema` | `workflows` | `src/domain/workflows/schemas.py` |
| 386 | `WorkflowListResponse` | `workflows` | `src/domain/workflows/schemas.py` |
| 387 | `WorkflowNode` | `workflows` | `src/domain/workflows/models.py` |
| 388 | `WorkflowNodeSchema` | `workflows` | `src/domain/workflows/schemas.py` |
| 389 | `WorkflowResponse` | `workflows` | `src/domain/workflows/schemas.py` |
| 390 | `WorkflowResumeService` | `workflows` | `src/domain/workflows/resume_service.py` |
| 391 | `WorkflowUpdateRequest` | `workflows` | `src/domain/workflows/schemas.py` |
| 392 | `WorkflowValidationResponse` | `workflows` | `src/domain/workflows/schemas.py` |

**Total unique class names**: 365
**Total class entries (including duplicates)**: 392
