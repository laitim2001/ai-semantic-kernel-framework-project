# R8 Supplement: Previously Undocumented Enums (55)

> **Purpose**: Complete the V9 Enum coverage from 83.8% to ~100%
> **Source**: r8_gap_detection.py reverse scan of 339 total enums
> **Date**: 2026-03-30

---

## Summary

| Category | Count | Priority |
|----------|-------|----------|
| Core Flow Enums | 15 | HIGH — affect architecture understanding |
| API Schema Enums | 26 | MEDIUM — API documentation completeness |
| Legacy Enums | 6 | LOW — deprecated, note only |
| Other | 8 | LOW — utility/minor |

---

## 1. Core Flow Enums (HIGH Priority)

### L02/L04: Intent & Routing

| Enum | File | Values | Purpose |
|------|------|--------|---------|
| `IntentCategoryEnum` | api/v1/orchestration/schemas.py | INCIDENT, REQUEST, CHANGE, QUERY, UNKNOWN | API-level mirror of ITIntentCategory for routing |
| `WorkflowTypeEnum` | api/v1/orchestration/schemas.py | MAGENTIC, HANDOFF, CONCURRENT, SEQUENTIAL, SIMPLE | Maps intent → workflow execution mode |
| `ApprovalType` | integrations/orchestration/hitl/controller.py | NONE, SINGLE, MULTI | HITL approval granularity (single vs multi-approver) |

### L05: Hybrid Orchestration

| Enum | File | Values | Purpose |
|------|------|--------|---------|
| `CollaborationType` | api/v1/claude_sdk/intent_routes.py | NONE, HANDOFF, GROUPCHAT, ROUND_ROBIN, COLLABORATION, MULTI_SPECIALIST, COORDINATION, DUAL_AGENT | Multi-agent collaboration strategy selection |
| `TaskCapabilityType` | api/v1/claude_sdk/hybrid_routes.py | MULTI_AGENT, HANDOFF, FILE_OPERATIONS, CODE_EXECUTION, WEB_SEARCH, TOOL_USE, CONVERSATION, PLANNING | Task capability classification for framework routing |
| `FrameworkType` | api/v1/claude_sdk/hybrid_routes.py | CLAUDE_SDK, MICROSOFT_AGENT, AUTO | Framework selection (MAF vs Claude vs Auto) |
| `ExecutionModeType` | api/v1/claude_sdk/intent_routes.py | CHAT_MODE, WORKFLOW_MODE, HYBRID_MODE | Top-level execution mode determination |

### L06: MAF Builders

| Enum | File | Values | Purpose |
|------|------|--------|---------|
| `GroupChatStatus` | integrations/agent_framework/builders/groupchat | IDLE, RUNNING, WAITING, PAUSED, COMPLETED, FAILED, CANCELLED | GroupChat session lifecycle state |
| `HumanInterventionDecision` | integrations/agent_framework/builders/magentic | APPROVE, REVISE, REJECT, CONTINUE, REPLAN, GUIDANCE | Magentic Orchestrator HITL decision options |
| `HumanInterventionKind` | integrations/agent_framework/builders/magentic | PLAN_REVIEW, TOOL_APPROVAL, STALL | Type of human intervention trigger |
| `ToolStatus` | integrations/agent_framework/tools/base.py | SUCCESS, FAILURE, PARTIAL, TIMEOUT, ERROR | Tool execution result status |

### L09: Supporting Integrations

| Enum | File | Values | Purpose |
|------|------|--------|---------|
| `MemoryLayer` | integrations/memory/types.py | WORKING, SESSION, LONG_TERM | Three-tier memory hierarchy layer identifier |
| `DocumentFormat` | integrations/knowledge/document_parser.py | PDF, DOCX, HTML, MARKDOWN, TEXT, UNKNOWN | RAG pipeline document format detection |
| `ChunkingStrategy` | integrations/knowledge/chunker.py | RECURSIVE, FIXED_SIZE, SEMANTIC | RAG text chunking algorithm selection |
| `SkillCategory` | integrations/knowledge/agent_skills.py | INCIDENT_MANAGEMENT, CHANGE_MANAGEMENT, ENTERPRISE_ARCHITECTURE, GENERAL_IT | ITIL skill pack categorization |

---

## 2. API Schema Enums (MEDIUM Priority)

### Concurrent Execution API

| Enum | File | Values | Count |
|------|------|--------|-------|
| `WebSocketMessageType` | api/v1/concurrent/schemas.py | EXECUTION_STARTED, EXECUTION_COMPLETED, EXECUTION_FAILED, EXECUTION_CANCELLED, BRANCH_STARTED, BRANCH_COMPLETED, BRANCH_FAILED, BRANCH_PROGRESS, TASK_UPDATE, ERROR | 11 |
| `ExecutionStatusEnum` | api/v1/concurrent/schemas.py | PENDING, RUNNING, WAITING, COMPLETED, FAILED, CANCELLED, TIMED_OUT | 7 |
| `BranchStatusEnum` | api/v1/concurrent/schemas.py | PENDING, RUNNING, COMPLETED, FAILED, CANCELLED, TIMED_OUT | 6 |
| `ConcurrentModeEnum` | api/v1/concurrent/schemas.py | ALL, ANY, MAJORITY, FIRST_SUCCESS | 4 |

### Handoff API

| Enum | File | Values | Count |
|------|------|--------|-------|
| `HandoffStatusEnum` | api/v1/handoff/schemas.py | INITIATED, VALIDATING, TRANSFERRING, COMPLETED, FAILED, CANCELLED, ROLLED_BACK | 7 |
| `HITLSessionStatusEnum` | api/v1/handoff/schemas.py | ACTIVE, INPUT_RECEIVED, PROCESSING, COMPLETED, TIMEOUT, CANCELLED, ESCALATED | 7 |
| `CapabilityCategoryEnum` | api/v1/handoff/schemas.py | LANGUAGE, REASONING, KNOWLEDGE, ACTION, INTEGRATION, COMMUNICATION | 6 |
| `TriggerTypeEnum` | api/v1/handoff/schemas.py | CONDITION, EVENT, TIMEOUT, ERROR, CAPABILITY, EXPLICIT | 6 |
| `MatchStrategyEnum` | api/v1/handoff/schemas.py | BEST_FIT, FIRST_FIT, ROUND_ROBIN, LEAST_LOADED | 4 |
| `HandoffPolicyEnum` | api/v1/handoff/schemas.py | IMMEDIATE, GRACEFUL, CONDITIONAL | 3 |
| `HITLInputTypeEnum` | api/v1/handoff/schemas.py | TEXT, CHOICE, CONFIRMATION, FILE, FORM | 5 |

### Nested Workflow API

| Enum | File | Values | Count |
|------|------|--------|-------|
| `ExecutionStatusEnum` | api/v1/nested/schemas.py | PENDING, RUNNING, COMPLETED, FAILED, CANCELLED, TIMEOUT | 6 |
| `TerminationTypeEnum` | api/v1/nested/schemas.py | CONDITION, MAX_DEPTH, MAX_ITERATIONS, TIMEOUT, CONVERGENCE, USER_ABORT | 6 |
| `CompositionTypeEnum` | api/v1/nested/schemas.py | SEQUENCE, PARALLEL, CONDITIONAL, LOOP, SWITCH | 5 |
| `NestedWorkflowTypeEnum` | api/v1/nested/schemas.py | INLINE, REFERENCE, DYNAMIC, RECURSIVE | 4 |
| `PropagationTypeEnum` | api/v1/nested/schemas.py | COPY, REFERENCE, MERGE, FILTER | 4 |
| `RecursionStrategyEnum` | api/v1/nested/schemas.py | DEPTH_FIRST, BREADTH_FIRST, PARALLEL | 3 |
| `SubWorkflowExecutionModeEnum` | api/v1/nested/schemas.py | SYNC, ASYNC, FIRE_AND_FORGET, CALLBACK | 4 |
| `WorkflowScopeEnum` | api/v1/nested/schemas.py | ISOLATED, INHERITED, SHARED | 3 |

### Other API Enums

| Enum | File | Values | Count |
|------|------|--------|-------|
| `HookType` | api/v1/claude_sdk/hooks_routes.py | APPROVAL, AUDIT, RATE_LIMIT, SANDBOX, CUSTOM | 5 |
| `HookPriority` | api/v1/claude_sdk/hooks_routes.py | LOW, NORMAL, HIGH, CRITICAL | 4 |
| `MCPServerStatus` | api/v1/claude_sdk/mcp_routes.py | CONNECTED, DISCONNECTED, CONNECTING, ERROR | 4 |
| `MCPTransport` | api/v1/claude_sdk/mcp_routes.py | STDIO, HTTP, WEBSOCKET | 3 |
| `UIComponentTypeEnum` | api/v1/ag_ui/schemas.py | FORM, CHART, CARD, TABLE, CUSTOM | 5 |
| `WorkflowStepStatusEnum` | api/v1/ag_ui/schemas.py | PENDING, IN_PROGRESS, COMPLETED, FAILED, SKIPPED | 5 |
| `VoteType` | api/v1/groupchat/routes.py | YES_NO, MULTI_CHOICE, RANKING, WEIGHTED, APPROVAL | 5 |
| `VoteResult` | api/v1/groupchat/routes.py | PENDING, PASSED, REJECTED, TIE, NO_QUORUM | 5 |
| `VotingSessionStatus` | api/v1/groupchat/routes.py | PENDING, ACTIVE, CLOSED, CANCELLED | 4 |
| `WebhookAction` | api/v1/n8n/schemas.py | ANALYZE, CLASSIFY, EXECUTE, QUERY, NOTIFY | 5 |
| `N8nConnectionStatus` | api/v1/n8n/schemas.py | CONNECTED, DISCONNECTED, ERROR, UNKNOWN | 4 |
| `DemoScenario` | api/v1/swarm/demo.py | SECURITY_AUDIT, ETL_PIPELINE, DATA_PIPELINE, CUSTOM | 4 |
| `FileCategory` | api/v1/files/schemas.py | TEXT, IMAGE, PDF | 3 |
| `FileStatus` | api/v1/files/schemas.py | PENDING, UPLOADED, ERROR | 3 |

---

## 3. Legacy Enums (LOW Priority — Deprecated)

| Enum | File | Values | Count | Note |
|------|------|--------|-------|------|
| `PlannerActionTypeLegacy` | integrations/agent_framework/builders/magentic | ANALYZE, PLAN, EXECUTE, EVALUATE, REPLAN, COMPLETE, FAIL | 7 | Replaced by new Magentic planner |
| `GroupChatStateLegacy` | integrations/agent_framework/builders/groupchat | IDLE, ACTIVE, SELECTING, SPEAKING, TERMINATED, ERROR | 6 | Replaced by GroupChatStatus |
| `SpeakerSelectionMethodLegacy` | integrations/agent_framework/builders/groupchat | AUTO, ROUND_ROBIN, RANDOM, MANUAL, PRIORITY, WEIGHTED | 6 | Retained for backward compat |
| `NestedExecutionStatusLegacy` | integrations/agent_framework/builders/workflow | PENDING, RUNNING, COMPLETED, FAILED, TIMEOUT, CANCELLED | 6 | Replaced by ExecutionStatusEnum |
| `NestedWorkflowTypeLegacy` | integrations/agent_framework/builders/workflow | INLINE, REFERENCE, DYNAMIC, RECURSIVE | 4 | Replaced by NestedWorkflowTypeEnum |
| `WorkflowScopeLegacy` | integrations/agent_framework/builders/workflow | ISOLATED, INHERITED, SHARED | 3 | Replaced by WorkflowScopeEnum |

---

## 4. Other Enums

| Enum | File | Values | Count |
|------|------|--------|-------|
| `RecursionStatus` | integrations/agent_framework/builders/nested_workflow | PENDING, RUNNING, COMPLETED, FAILED, DEPTH_EXCEEDED, TIMEOUT | 6 |

---

## Coverage After This Supplement

| Metric | Before R8 | After R8 |
|--------|-----------|----------|
| Documented Enums | 284/339 | 339/339 |
| Enum Coverage | 83.8% | **100%** |
