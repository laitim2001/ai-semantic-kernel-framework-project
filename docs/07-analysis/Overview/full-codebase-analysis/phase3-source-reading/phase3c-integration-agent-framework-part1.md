# Phase 3C: Agent Framework Integration Analysis (Part 1)
# builders/ + core/ + Root Files — Official API Compliance Audit

**Analysis Date**: 2026-03-15
**Analyst**: Agent C1 (Claude Opus 4.6)
**Scope**: `backend/src/integrations/agent_framework/` — 57 .py files total
**Focus**: builders/ (24 files), core/ (9 files), root files (5 files), plus supporting subdirs

---

## Executive Summary

The `agent_framework` integration module is the **largest** integration (57 files) and the **most critical** for the IPA Platform. It wraps Microsoft Agent Framework (MAF) official API using the Adapter Pattern. This audit verifies every builder and core file for compliance with the mandatory rule: **all adapters MUST import from `agent_framework` and use official Builder instances**.

### Overall Compliance Score: **STRONG** (7/7 primary builders COMPLIANT)

| Category | Files | Compliant | Conditionally Compliant | N/A (Extension/Migration) |
|----------|-------|-----------|------------------------|--------------------------|
| **Primary Builders** | 7 | 7 | 0 | 0 |
| **Migration Layers** | 4 | — | — | 4 (by design) |
| **Extension Adapters** | 10 | — | 4 | 6 (platform logic) |
| **Core Adapters** | 9 | 8 | 1 | 0 |
| **Root Files** | 5 | 5 | 0 | 0 |

---

## 1. Primary Builder Adapters (ALL COMPLIANT)

These 7 files are the **critical path** — they MUST import from `agent_framework`, create `self._builder = OfficialBuilder()`, and call `self._builder.build()`.

### 1.1 ConcurrentBuilderAdapter — `builders/concurrent.py`
| Check | Status | Detail |
|-------|--------|--------|
| Official Import | PASS | `from agent_framework import ConcurrentBuilder` (line 83) |
| Builder Instance | PASS | `self._builder = ConcurrentBuilder()` (line 796) |
| build() calls official API | PASS | `def build()` (line 1042) uses official ConcurrentBuilder |
| Adapter Pattern | PASS | Extends `BuilderAdapter` from `base.py` |
| Business Logic | ConcurrentMode enum (ALL/ANY/MAJORITY/FIRST_SUCCESS), GatewayType, JoinCondition, custom aggregators, timeout management |
| Sprint | 14, 22 |

### 1.2 HandoffBuilderAdapter — `builders/handoff.py`
| Check | Status | Detail |
|-------|--------|--------|
| Official Import | PASS | `from agent_framework import (HandoffBuilder, ...)` (line 54) |
| Builder Instance | PASS | `self._builder = HandoffBuilder()` (line 304) |
| build() calls official API | PASS | `def build()` (line 561) uses official HandoffBuilder |
| Adapter Pattern | PASS | Extends `BuilderAdapter` |
| Business Logic | HandoffMode enum, HandoffRoute config, execution result tracking, participant management |
| Sprint | 15 |

### 1.3 GroupChatBuilderAdapter — `builders/groupchat.py`
| Check | Status | Detail |
|-------|--------|--------|
| Official Import | PASS | `from agent_framework import (GroupChatBuilder, ...)` (line 83) |
| Builder Instance | PASS | `self._builder = GroupChatBuilder()` (line 1101) |
| build() calls official API | PASS | `def build()` (line 1310) uses official GroupChatBuilder |
| Adapter Pattern | PASS | Extends `BuilderAdapter` |
| Business Logic | SpeakerSelectionMethod (7 strategies: AUTO/ROUND_ROBIN/RANDOM/MANUAL/PRIORITY/EXPERTISE/VOTING), GroupChatState, participant config |
| Sprint | 16, 20 |

### 1.4 MagenticBuilderAdapter — `builders/magentic.py`
| Check | Status | Detail |
|-------|--------|--------|
| Official Import | PASS | `from agent_framework import (MagenticBuilder, ...)` (line 39) |
| Builder Instance | PASS | `self._builder = MagenticBuilder()` (line 1027) |
| build() calls official API | PASS | `def build()` (line 1257) uses official MagenticBuilder |
| Adapter Pattern | PASS | Extends `BuilderAdapter` |
| Business Logic | MagenticManagerAdapter, Task/Progress Ledger, fact extraction, planning, progress evaluation, human intervention (PLAN_REVIEW, TOOL_APPROVAL, STALL) |
| Sprint | 17 |

### 1.5 WorkflowExecutorAdapter — `builders/workflow_executor.py`
| Check | Status | Detail |
|-------|--------|--------|
| Official Import | PASS | `from agent_framework import (...)` (line 52) |
| Builder Instance | PASS | Uses official WorkflowExecutor API |
| build() calls official API | PASS | `def build()` (line 630) uses official API |
| Adapter Pattern | PASS | Extends `BuilderAdapter` |
| Business Logic | Workflow execution management, state tracking, event handling |
| Sprint | 18 |

### 1.6 NestedWorkflowAdapter — `builders/nested_workflow.py`
| Check | Status | Detail |
|-------|--------|--------|
| Official Import | PASS | `from agent_framework import WorkflowBuilder, Workflow, WorkflowExecutor` (line 71) |
| Builder Instance | PASS | `self._builder = WorkflowBuilder()` (line 615) |
| build() calls official API | PASS | `def build()` (line 879) uses official WorkflowBuilder |
| Adapter Pattern | PASS | Extends `BuilderAdapter` |
| Business Logic | Sub-workflow composition, recursion depth control, parent-child workflow linking |
| Sprint | 23 |

### 1.7 PlanningAdapter — `builders/planning.py`
| Check | Status | Detail |
|-------|--------|--------|
| Official Import | PASS | `from agent_framework import MagenticBuilder, Workflow` (line 31) |
| Builder Instance | PASS | Uses MagenticBuilder internally |
| build() calls official API | PASS | `def build()` (line 508) uses official MagenticBuilder |
| Adapter Pattern | PASS | Extends `BuilderAdapter` |
| Business Logic | Planning-specific workflow with MagenticBuilder, multi-turn integration |
| Sprint | 24 |

---

## 2. Extension Adapters (Platform Business Logic)

These files extend the primary builders with **platform-specific capabilities**. They do NOT directly wrap a MAF Builder class — they provide IPA-specific business logic that works alongside the compliant primary adapters.

### 2.1 Handoff Extensions (Sprint 21)

| File | Class | Has `from agent_framework`? | Assessment |
|------|-------|---------------------------|------------|
| `handoff_policy.py` | `HandoffPolicyAdapter` | NO | **ACCEPTABLE** — Pure platform business logic (policy mapping: IMMEDIATE/CONDITIONAL/ESCALATION/ROUND_ROBIN). Not a Builder wrapper. |
| `handoff_capability.py` | `CapabilityMatcherAdapter` | NO | **ACCEPTABLE** — Platform capability matching algorithm. Consumed by HandoffBuilderAdapter. |
| `handoff_context.py` | `ContextTransferAdapter` | NO | **ACCEPTABLE** — Context serialization/transfer between agents. Platform utility. |
| `handoff_service.py` | `HandoffService` | NO | **ACCEPTABLE** — Service orchestration class. Coordinates HandoffBuilderAdapter + policies. |
| `handoff_hitl.py` | `HITLCheckpointAdapter` | NO | **ACCEPTABLE** — Human-in-the-loop checkpoint management. Platform-specific HITL integration. |

**Verdict**: All 5 handoff extensions are **CONDITIONALLY COMPLIANT** — they provide business logic consumed by the COMPLIANT `HandoffBuilderAdapter`. They do not need direct MAF imports because they don't wrap MAF Builder classes.

### 2.2 GroupChat Extensions (Sprint 20)

| File | Class | Has `from agent_framework`? | Assessment |
|------|-------|---------------------------|------------|
| `groupchat_voting.py` | `GroupChatVotingAdapter` | NO (inherits from `GroupChatBuilderAdapter`) | **ACCEPTABLE** — Extends compliant GroupChatBuilderAdapter with voting mechanisms. Inherits official API access. |
| `groupchat_orchestrator.py` | `GroupChatOrchestrator` | NO | **ACCEPTABLE** — Pure orchestration logic (manager selection, directives, phase management). Platform coordination layer. |

### 2.3 Agent & Code Interpreter (Sprint 31, 37)

| File | Class | Has `from agent_framework`? | Assessment |
|------|-------|---------------------------|------------|
| `agent_executor.py` | `AgentExecutorAdapter` | YES (lazy: `from agent_framework import ChatAgent, ChatMessage, Role` at line 155) | **COMPLIANT** — Uses lazy import of ChatAgent for Azure OpenAI integration. |
| `code_interpreter.py` | `CodeInterpreterAdapter` | NO (uses `from openai import AzureOpenAI` directly) | **ACCEPTABLE** — Wraps Azure OpenAI Code Interpreter API directly, not a MAF Builder. Uses AzureOpenAI SDK. |

### 2.4 Edge Routing (Sprint 14)

| File | Class | Has `from agent_framework`? | Assessment |
|------|-------|---------------------------|------------|
| `edge_routing.py` | (utility functions) | **NO** | **WARNING** — Docstring references `from agent_framework import Edge, EdgeGroup, FanOutEdgeGroup, FanInEdgeGroup, SwitchCaseEdgeGroup` but **no actual import found**. File provides custom FanOutStrategy/FanInAggregator/ConditionalRouter implementations. This is a **potential compliance gap** — the file describes MAF Edge types but implements custom routing logic without importing them. |

---

## 3. Migration Layers (Backward Compatibility)

These files bridge Phase 2 APIs to Phase 3+ MAF adapters. They are **intentionally not direct MAF wrappers** — they translate old API calls to use the compliant primary adapters internally.

| File | Class | Strategy | Assessment |
|------|-------|----------|------------|
| `concurrent_migration.py` | `ConcurrentExecutorAdapter` | Wraps `ConcurrentBuilderAdapter` internally | **BY DESIGN** — Migration shim preserving Phase 2 API signatures |
| `handoff_migration.py` | `HandoffControllerAdapter` | Wraps `HandoffBuilderAdapter` internally | **BY DESIGN** — Migration from Phase 2 HandoffController |
| `groupchat_migration.py` | `GroupChatManagerAdapter` | Wraps `GroupChatBuilderAdapter` internally | **BY DESIGN** — Migration from Phase 2 GroupChatManager |
| `magentic_migration.py` | `MagenticManagerAdapter` | Extends `MagenticManagerBase` internally | **BY DESIGN** — Migration from Phase 2 DynamicPlanner |
| `workflow_executor_migration.py` | `NestedWorkflowManagerAdapter` | Wraps compliant adapters internally | **BY DESIGN** — Migration from Phase 2 workflow management |

**Verdict**: All 5 migration layers delegate to COMPLIANT primary adapters. They are **transitional code** and correctly follow the migration pattern.

---

## 4. Core Adapters (Official API Wrappers)

These files in `core/` wrap MAF core primitives (Workflow, Executor, Edge, Events).

| File | Class(es) | Import | Assessment |
|------|-----------|--------|------------|
| `core/workflow.py` | `WorkflowDefinitionAdapter` | `from agent_framework import Workflow, WorkflowBuilder, Edge, Executor` (line 37) | **COMPLIANT** — Uses WorkflowBuilder in `build()` method |
| `core/executor.py` | (Executor utilities) | `from agent_framework import Executor, WorkflowContext, handler` (line 38) | **COMPLIANT** — Wraps official Executor and handler decorator |
| `core/edge.py` | `WorkflowEdgeAdapter` | `from agent_framework import Edge` (line 29) | **COMPLIANT** — Wraps official Edge class |
| `core/events.py` | `WorkflowStatusEventAdapter` | `from agent_framework import WorkflowStatusEvent` (line 34) | **COMPLIANT** — Wraps official event system |
| `core/execution.py` | `SequentialOrchestrationAdapter`, `ExecutionAdapter` | `from agent_framework import ChatAgent, SequentialBuilder, Workflow` (line 34) | **COMPLIANT** — Uses SequentialBuilder and ChatAgent |
| `core/approval.py` | (HumanApprovalExecutor) | `from agent_framework import Executor, handler, WorkflowContext` (line 39) | **COMPLIANT** — Extends official Executor for HITL |
| `core/approval_workflow.py` | `WorkflowApprovalAdapter` | `from agent_framework import Workflow, Edge` (line 36) | **COMPLIANT** — Uses official Workflow/Edge for approval flows |
| `core/context.py` | `WorkflowContextAdapter` | NO direct import | **CONDITIONALLY COMPLIANT** — Adapts domain WorkflowContext to be *compatible* with official context interface (get/set/run_id). Does not import MAF but implements the interface contract. |
| `core/state_machine.py` | (Enhanced StateMachine) | NO direct import (uses `core/events.py` which imports MAF) | **COMPLIANT** — Integrates with MAF event system indirectly through `WorkflowStatusEventAdapter` |

---

## 5. Root Files

| File | Purpose | Assessment |
|------|---------|------------|
| `__init__.py` | Unified re-exports | **COMPLIANT** — Properly exports all adapter classes |
| `base.py` | `BaseAdapter`, `BuilderAdapter` abstract classes | **COMPLIANT** — Defines adapter contract with `_builder` pattern |
| `workflow.py` | `WorkflowAdapter` | **COMPLIANT** — `from agent_framework import WorkflowBuilder` (lazy, line 425), creates builder and calls `builder.build()` |
| `checkpoint.py` | `CheckpointStorageAdapter`, `PostgresCheckpointStorage`, `RedisCheckpointCache`, `CachedCheckpointStorage` | **COMPLIANT** — `from agent_framework import WorkflowCheckpoint` (lazy, line 102) for data conversion |
| `exceptions.py` | Custom exception hierarchy | **COMPLIANT** — Pure exception classes, no MAF dependency needed |

---

## 6. Supporting Subdirectories

### 6.1 memory/ (4 files)
| File | Import | Assessment |
|------|--------|------------|
| `base.py` | `from agent_framework import Context, ContextProvider` (line 25) | **COMPLIANT** |
| `redis_storage.py` | Extends `BaseMemoryStorageAdapter` | **COMPLIANT** (inherits) |
| `postgres_storage.py` | Extends `BaseMemoryStorageAdapter` | **COMPLIANT** (inherits) |
| `__init__.py` | Re-exports | OK |

### 6.2 multiturn/ (3 files)
| File | Import | Assessment |
|------|--------|------------|
| `adapter.py` | `from agent_framework import (...)` (line 27) | **COMPLIANT** |
| `checkpoint_storage.py` | `from agent_framework import CheckpointStorage, InMemoryCheckpointStorage` (line 31) | **COMPLIANT** |
| `__init__.py` | Re-exports | OK |

### 6.3 acl/ (4 files — Anti-Corruption Layer)
| File | Purpose | Assessment |
|------|---------|------------|
| `interfaces.py` | `AgentBuilderInterface`, `AgentRunnerInterface`, `ToolInterface` | **COMPLIANT** — Defines stable abstractions |
| `version_detector.py` | `MAFVersionDetector` | **COMPLIANT** — Detects MAF version/available APIs |
| `adapter.py` | `MAFAdapter` | **COMPLIANT** — Uses `getattr(agent_framework, maf_class_name)` dynamically (line 141) |
| `__init__.py` | Re-exports | OK |

### 6.4 tools/ (3 files)
| File | Purpose | Assessment |
|------|---------|------------|
| `base.py` | `BaseTool`, `ToolRegistry` | **ACCEPTABLE** — Platform tool abstraction, no MAF dependency needed |
| `code_interpreter_tool.py` | `CodeInterpreterTool` extends `BaseTool` | **ACCEPTABLE** — Platform tool wrapper |
| `__init__.py` | Re-exports | OK |

### 6.5 assistant/ (5 files)
| File | Purpose | Assessment |
|------|---------|------------|
| `models.py` | Data models (ExecutionStatus, CodeExecutionResult, AssistantConfig, etc.) | **ACCEPTABLE** — Pure data structures |
| `exceptions.py` | Assistant-specific exceptions | **ACCEPTABLE** — Error hierarchy |
| `files.py` | `FileStorageService` | **ACCEPTABLE** — File management utility |
| `manager.py` | `AssistantManagerService` | **ACCEPTABLE** — High-level service |
| `__init__.py` | Re-exports | OK |

---

## 7. Issues & Recommendations

### 7.1 CRITICAL Issues: None

All 7 primary builder adapters are **fully compliant** with the mandatory `from agent_framework import` + `self._builder = OfficialBuilder()` + `build()` pattern.

### 7.2 WARNINGS

| # | File | Issue | Severity | Recommendation |
|---|------|-------|----------|----------------|
| W-1 | `builders/edge_routing.py` | Docstring references MAF Edge types (Edge, EdgeGroup, FanOutEdgeGroup, FanInEdgeGroup, SwitchCaseEdgeGroup) but **no actual `from agent_framework import` exists**. Custom implementations of FanOutStrategy/FanInAggregator/ConditionalRouter bypass official Edge API. | MEDIUM | Add `from agent_framework import Edge, FanOutEdgeGroup, FanInEdgeGroup` and use official edge group classes instead of custom implementations. |
| W-2 | `core/context.py` | Implements MAF context interface (get/set/run_id) but does not import from `agent_framework`. | LOW | Consider importing the official context protocol/interface if available in MAF for type verification. Currently works via duck typing. |

### 7.3 OBSERVATIONS

| # | Observation |
|---|-------------|
| O-1 | **Lazy imports** are used in `workflow.py` (line 425), `checkpoint.py` (line 102), and `agent_executor.py` (line 155) to avoid circular dependencies. This is an accepted pattern. |
| O-2 | **5 migration files** exist as backward-compatibility shims. These should be tracked for eventual removal as Phase 2 consumers are migrated. |
| O-3 | The `acl/adapter.py` uses **dynamic import** via `getattr(agent_framework, class_name)` which is flexible but harder to statically verify. |
| O-4 | `code_interpreter.py` uses `from openai import AzureOpenAI` directly rather than MAF — this is correct because Code Interpreter is an Azure OpenAI SDK feature, not a MAF Builder. |
| O-5 | The `assistant/` subdirectory (5 files) contains pure platform data models and services with no MAF dependency, which is architecturally correct. |

---

## 8. Feature Cross-Reference (Plan Baseline A5-A16)

| Feature ID | Feature | Builder/Module | Status |
|------------|---------|---------------|--------|
| A5 | Parallel Execution | `concurrent.py` + `concurrent_migration.py` + `edge_routing.py` | COMPLIANT (primary), edge_routing has W-1 |
| A6 | Agent Handoff | `handoff.py` + `handoff_policy.py` + `handoff_capability.py` + `handoff_context.py` + `handoff_service.py` + `handoff_hitl.py` + `handoff_migration.py` | COMPLIANT (primary), extensions acceptable |
| A7 | Group Chat | `groupchat.py` + `groupchat_voting.py` + `groupchat_orchestrator.py` + `groupchat_migration.py` | COMPLIANT (primary), extensions acceptable |
| A8 | Dynamic Planning (Magentic One) | `magentic.py` + `magentic_migration.py` | COMPLIANT |
| A9 | Workflow Execution | `workflow_executor.py` + `workflow_executor_migration.py` | COMPLIANT |
| A10 | Nested Workflows | `nested_workflow.py` | COMPLIANT |
| A11 | Planning Integration | `planning.py` | COMPLIANT |
| A12 | Core Workflow | `core/workflow.py` + `core/executor.py` + `core/edge.py` | COMPLIANT |
| A13 | Events & State | `core/events.py` + `core/state_machine.py` + `core/context.py` | COMPLIANT (context has W-2) |
| A14 | Execution Management | `core/execution.py` | COMPLIANT |
| A15 | Approval/HITL | `core/approval.py` + `core/approval_workflow.py` | COMPLIANT |
| A16 | Agent Execution | `agent_executor.py` + `code_interpreter.py` | COMPLIANT |

---

## 9. Architecture Summary

```
agent_framework/ (57 files)
├── Root (5 files)
│   ├── __init__.py .............. Re-exports [COMPLIANT]
│   ├── base.py .................. BaseAdapter + BuilderAdapter [COMPLIANT]
│   ├── workflow.py .............. WorkflowAdapter → WorkflowBuilder [COMPLIANT]
│   ├── checkpoint.py ............ CheckpointStorage adapters [COMPLIANT]
│   └── exceptions.py ........... Error hierarchy [COMPLIANT]
│
├── builders/ (24 files)
│   ├── PRIMARY BUILDERS (7) — ALL COMPLIANT
│   │   ├── concurrent.py ........ → ConcurrentBuilder
│   │   ├── handoff.py ........... → HandoffBuilder
│   │   ├── groupchat.py ......... → GroupChatBuilder
│   │   ├── magentic.py .......... → MagenticBuilder
│   │   ├── workflow_executor.py . → WorkflowExecutor
│   │   ├── nested_workflow.py ... → WorkflowBuilder
│   │   └── planning.py ......... → MagenticBuilder
│   │
│   ├── EXTENSIONS (10) — Platform business logic
│   │   ├── handoff_policy.py .... Policy mapping
│   │   ├── handoff_capability.py  Capability matching
│   │   ├── handoff_context.py ... Context transfer
│   │   ├── handoff_service.py ... Service orchestration
│   │   ├── handoff_hitl.py ...... HITL checkpoints
│   │   ├── groupchat_voting.py .. Voting mechanisms
│   │   ├── groupchat_orchestrator Manager selection
│   │   ├── agent_executor.py .... ChatAgent wrapper [COMPLIANT]
│   │   ├── code_interpreter.py .. Azure OpenAI CodeInterpreter
│   │   └── edge_routing.py ...... FanOut/FanIn [WARNING W-1]
│   │
│   ├── MIGRATIONS (5) — Phase 2 backward compat
│   │   ├── concurrent_migration.py
│   │   ├── handoff_migration.py
│   │   ├── groupchat_migration.py
│   │   ├── magentic_migration.py
│   │   └── workflow_executor_migration.py
│   │
│   └── __init__.py .............. Unified exports
│
├── core/ (9 files) — 8 COMPLIANT, 1 CONDITIONAL
│   ├── workflow.py .............. → WorkflowBuilder
│   ├── executor.py .............. → Executor, handler
│   ├── edge.py .................. → Edge
│   ├── events.py ................ → WorkflowStatusEvent
│   ├── execution.py ............. → SequentialBuilder, ChatAgent
│   ├── approval.py .............. → Executor, handler
│   ├── approval_workflow.py ..... → Workflow, Edge
│   ├── context.py ............... Interface compat [CONDITIONAL W-2]
│   ├── state_machine.py ......... Event integration (indirect)
│   └── __init__.py
│
├── memory/ (4 files) — ALL COMPLIANT
├── multiturn/ (3 files) — ALL COMPLIANT
├── acl/ (4 files) — ALL COMPLIANT
├── tools/ (3 files) — ACCEPTABLE (platform utils)
└── assistant/ (5 files) — ACCEPTABLE (platform models)
```

---

## 10. Conclusion

The `agent_framework` integration module demonstrates **strong compliance** with the mandatory official API usage rules. All 7 primary builder adapters correctly:

1. Import from `agent_framework` package
2. Create `self._builder = OfficialBuilder()` instances
3. Call official `build()` methods

The architecture cleanly separates:
- **Primary adapters** (MAF wrappers) from **extension adapters** (platform logic)
- **Migration shims** (Phase 2 compat) from **production adapters**
- **Core primitives** (Workflow/Executor/Edge) from **builder specializations**

Two minor warnings exist (`edge_routing.py` missing actual MAF imports, `core/context.py` using duck typing instead of explicit MAF import) but neither represents a functional compliance violation.

**Recommendation**: Address W-1 (edge_routing.py) in the next maintenance sprint to ensure edge routing uses official MAF EdgeGroup classes rather than custom implementations.

---

*Generated by Agent C1 — Phase 3C Integration Analysis*
*Cross-reference: Features A5-A16 from plan baseline*
