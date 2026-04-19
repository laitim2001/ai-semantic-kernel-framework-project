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
| Other | 1 | LOW — utility/minor |
| L09 Integration Enums (Wave 72) | 42 | HIGH — 12 modules, cross-doc sync |

---

## 1. Core Flow Enums (HIGH Priority)

### L02/L04: Intent & Routing

| Enum | File | Values | Purpose |
|------|------|--------|---------|
| `IntentCategoryEnum` | api/v1/orchestration/schemas.py | INCIDENT, REQUEST, CHANGE, QUERY, UNKNOWN | API-level mirror of ITIntentCategory for routing |
| `WorkflowTypeEnum` | api/v1/orchestration/schemas.py | MAGENTIC, HANDOFF, CONCURRENT, SEQUENTIAL, SIMPLE | Maps intent → workflow execution mode |
| `ApprovalType` | integrations/orchestration/hitl/controller.py | NONE, SINGLE, MULTI | HITL approval granularity (single vs multi-approver). Base: `Enum` (not `str, Enum`) |

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
| `GroupChatStatus` | integrations/agent_framework/builders/groupchat.py | IDLE, RUNNING, WAITING, PAUSED, COMPLETED, FAILED, CANCELLED | GroupChat session lifecycle state |
| `HumanInterventionDecision` | integrations/agent_framework/builders/magentic.py | APPROVE, REVISE, REJECT, CONTINUE, REPLAN, GUIDANCE | Magentic Orchestrator HITL decision options |
| `HumanInterventionKind` | integrations/agent_framework/builders/magentic.py | PLAN_REVIEW, TOOL_APPROVAL, STALL | Type of human intervention trigger |
| `ToolStatus` | integrations/agent_framework/tools/base.py | SUCCESS, FAILURE, PARTIAL, TIMEOUT, ERROR | Tool execution result status. Base: `Enum` (not `str, Enum`) |

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
| `WebSocketMessageType` | api/v1/concurrent/schemas.py | EXECUTION_STARTED, EXECUTION_COMPLETED, EXECUTION_FAILED, EXECUTION_CANCELLED, BRANCH_STARTED, BRANCH_COMPLETED, BRANCH_FAILED, BRANCH_PROGRESS, DEADLOCK_DETECTED, DEADLOCK_RESOLVED, ERROR | 11 |
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
| `PlannerActionTypeLegacy` | integrations/agent_framework/builders/magentic_migration.py | ANALYZE, PLAN, EXECUTE, EVALUATE, REPLAN, COMPLETE, FAIL | 7 | Replaced by new Magentic planner |
| `GroupChatStateLegacy` | integrations/agent_framework/builders/groupchat_migration.py | IDLE, ACTIVE, SELECTING, SPEAKING, TERMINATED, ERROR | 6 | Replaced by GroupChatStatus |
| `SpeakerSelectionMethodLegacy` | integrations/agent_framework/builders/groupchat_migration.py | AUTO, ROUND_ROBIN, RANDOM, MANUAL, PRIORITY, WEIGHTED | 6 | Retained for backward compat |
| `NestedExecutionStatusLegacy` | integrations/agent_framework/builders/workflow_executor_migration.py | PENDING, RUNNING, COMPLETED, FAILED, TIMEOUT, CANCELLED | 6 | Replaced by ExecutionStatusEnum |
| `NestedWorkflowTypeLegacy` | integrations/agent_framework/builders/workflow_executor_migration.py | INLINE, REFERENCE, DYNAMIC, RECURSIVE | 4 | Replaced by NestedWorkflowTypeEnum |
| `WorkflowScopeLegacy` | integrations/agent_framework/builders/workflow_executor_migration.py | ISOLATED, INHERITED, SHARED | 3 | Replaced by WorkflowScopeEnum |

---

## 4. Other Enums

| Enum | File | Values | Count |
|------|------|--------|-------|
| `RecursionStatus` | integrations/agent_framework/builders/nested_workflow.py | PENDING, RUNNING, COMPLETED, FAILED, DEPTH_EXCEEDED, TIMEOUT | 6 |

---

## 5. Layer 09 Integration Enums (Wave 72 Sync)

> **Source**: layer-09-integrations.md Section 17 "Enum Registry" — Wave 72 deep-dive additions.
> These enums were documented in L09 but not yet synced to this central registry.

### swarm/models.py

| Enum | File | Values | Count |
|------|------|--------|-------|
| `WorkerType` | integrations/swarm/models.py | RESEARCH, WRITER, DESIGNER, REVIEWER, COORDINATOR, ANALYST, CODER, TESTER, CUSTOM | 9 |
| `WorkerStatus` | integrations/swarm/models.py | PENDING, RUNNING, THINKING, TOOL_CALLING, COMPLETED, FAILED, CANCELLED | 7 |
| `SwarmMode` | integrations/swarm/models.py | SEQUENTIAL, PARALLEL, HIERARCHICAL | 3 |
| `SwarmStatus` | integrations/swarm/models.py | INITIALIZING, RUNNING, PAUSED, COMPLETED, FAILED | 5 |
| `ToolCallStatus` | integrations/swarm/models.py | PENDING, RUNNING, COMPLETED, FAILED | 4 |

### contracts/pipeline.py

| Enum | File | Values | Count |
|------|------|--------|-------|
| `PipelineSource` | integrations/contracts/pipeline.py | USER, SERVICENOW, PROMETHEUS, API | 4 |

### shared/protocols.py

| Enum | File | Values | Count |
|------|------|--------|-------|
| `ToolCallStatus` | integrations/shared/protocols.py | PENDING, RUNNING, COMPLETED, FAILED, CANCELLED | 5 |

> **Note**: `ToolCallStatus` is defined in both `swarm/models.py` (4 values) and `shared/protocols.py` (5 values, adds CANCELLED). These are independent definitions — see layer-09-integrations.md Issue 1 for unification recommendation.

### a2a/protocol.py

| Enum | File | Values | Count |
|------|------|--------|-------|
| `MessageType` | integrations/a2a/protocol.py | TASK_REQUEST, TASK_RESPONSE, TASK_PROGRESS, TASK_CANCEL, STATUS_UPDATE, HEARTBEAT, CAPABILITY_QUERY, CAPABILITY_RESPONSE, REGISTER, UNREGISTER, ERROR, ACK | 12 |
| `MessagePriority` | integrations/a2a/protocol.py | LOW, NORMAL, HIGH, URGENT | 4 |
| `MessageStatus` | integrations/a2a/protocol.py | PENDING, SENT, DELIVERED, PROCESSED, FAILED, EXPIRED | 6 |
| `A2AAgentStatus` | integrations/a2a/protocol.py | ONLINE, BUSY, OFFLINE, MAINTENANCE | 4 |

### patrol/types.py

| Enum | File | Values | Count |
|------|------|--------|-------|
| `PatrolStatus` | integrations/patrol/types.py | HEALTHY, WARNING, CRITICAL, UNKNOWN | 4 |
| `CheckType` | integrations/patrol/types.py | SERVICE_HEALTH, API_RESPONSE, RESOURCE_USAGE, LOG_ANALYSIS, SECURITY_SCAN | 5 |
| `ScheduleFrequency` | integrations/patrol/types.py | EVERY_5_MINUTES through WEEKLY | 7 |
| `PatrolPriority` | integrations/patrol/types.py | LOW, MEDIUM, HIGH, CRITICAL | 4 |

### memory/types.py

| Enum | File | Values | Count |
|------|------|--------|-------|
| `MemoryType` | integrations/memory/types.py | EVENT_RESOLUTION, USER_PREFERENCE, SYSTEM_KNOWLEDGE, BEST_PRACTICE, CONVERSATION, FEEDBACK | 6 |

> **Note**: `MemoryLayer` (WORKING, SESSION, LONG_TERM) was already documented in Section 1 above.

### correlation/types.py

| Enum | File | Values | Count |
|------|------|--------|-------|
| `CorrelationType` | integrations/correlation/types.py | TIME, DEPENDENCY, SEMANTIC, CAUSAL | 4 |
| `EventSeverity` | integrations/correlation/types.py | INFO, WARNING, ERROR, CRITICAL | 4 |
| `EventType` | integrations/correlation/types.py | ALERT, INCIDENT, CHANGE, DEPLOYMENT, METRIC_ANOMALY, LOG_PATTERN, SECURITY | 7 |

### rootcause/types.py

| Enum | File | Values | Count |
|------|------|--------|-------|
| `AnalysisStatus` | integrations/rootcause/types.py | PENDING, ANALYZING, COMPLETED, FAILED | 4 |
| `EvidenceType` | integrations/rootcause/types.py | LOG, METRIC, TRACE, CORRELATION, PATTERN, EXPERT | 6 |
| `RecommendationType` | integrations/rootcause/types.py | IMMEDIATE, SHORT_TERM, LONG_TERM, PREVENTIVE | 4 |

### incident/types.py

| Enum | File | Values | Count |
|------|------|--------|-------|
| `IncidentSeverity` | integrations/incident/types.py | P1 (Critical), P2 (High), P3 (Medium), P4 (Low) | 4 |
| `IncidentCategory` | integrations/incident/types.py | NETWORK, SERVER, APPLICATION, DATABASE, SECURITY, STORAGE, PERFORMANCE, AUTHENTICATION, OTHER | 9 |
| `RemediationRisk` | integrations/incident/types.py | AUTO, LOW, MEDIUM, HIGH, CRITICAL | 5 |
| `RemediationActionType` | integrations/incident/types.py | RESTART_SERVICE, CLEAR_DISK_SPACE, AD_ACCOUNT_UNLOCK, SCALE_RESOURCE, NETWORK_ACL_CHANGE, FIREWALL_RULE_CHANGE, RESTART_DATABASE, CLEAR_CACHE, ROTATE_CREDENTIALS, CUSTOM | 10 |
| `ExecutionStatus` | integrations/incident/types.py | PENDING, EXECUTING, COMPLETED, FAILED, AWAITING_APPROVAL, APPROVED, REJECTED, SKIPPED | 8 |

### learning/types.py

| Enum | File | Values | Count |
|------|------|--------|-------|
| `CaseOutcome` | integrations/learning/types.py | SUCCESS, PARTIAL_SUCCESS, FAILURE, UNKNOWN | 4 |
| `CaseCategory` | integrations/learning/types.py | INCIDENT_RESOLUTION, PERFORMANCE_OPTIMIZATION, SECURITY_RESPONSE, DEPLOYMENT_ISSUE, CONFIGURATION_CHANGE, USER_SUPPORT, SYSTEM_MAINTENANCE, OTHER | 8 |

### audit/types.py

| Enum | File | Values | Count |
|------|------|--------|-------|
| `DecisionType` | integrations/audit/types.py | PLAN_GENERATION, STEP_EXECUTION, TOOL_SELECTION, FALLBACK_SELECTION, RISK_ASSESSMENT, APPROVAL_REQUEST, OTHER | 7 |
| `DecisionOutcome` | integrations/audit/types.py | SUCCESS, PARTIAL_SUCCESS, FAILURE, PENDING, CANCELLED | 5 |
| `QualityRating` | integrations/audit/types.py | EXCELLENT (>=0.9), GOOD (>=0.7), ACCEPTABLE (>=0.5), POOR (>=0.3), UNACCEPTABLE (<0.3) | 5 |

### n8n/orchestrator.py + monitor.py

| Enum | File | Values | Count |
|------|------|--------|-------|
| `OrchestrationStatus` | integrations/n8n/orchestrator.py | PENDING, REASONING, TRANSLATING, EXECUTING, MONITORING, COMPLETED, FAILED, TIMEOUT, CANCELLED | 9 |
| `ExecutionState` | integrations/n8n/monitor.py | PENDING, RUNNING, COMPLETED, FAILED, TIMED_OUT, CANCELLED, UNKNOWN | 7 |

---

## Coverage After This Supplement

| Metric | Before R8 | After R8 | After Wave 72 Sync |
|--------|-----------|----------|---------------------|
| Documented Enums | 284/339 | 339/339 | 339 + 42 L09 enums verified |
| Enum Coverage | 83.8% | **100%** | **100%** (cross-doc synced) |

---

## Phase 45-47 Enum Additions (2026-04-19 sync)

| Enum | Source File | Values | Purpose |
|------|-------------|--------|---------|
| `ExecutionRoute` | `integrations/orchestration/dispatch/models.py:13` | `DIRECT_ANSWER="direct_answer"`, `SUBAGENT="subagent"`, `TEAM="team"` | Dispatch layer route decision. `from_string()` defaults to `TEAM` on unknown input. |
| `PipelineEventType` | `integrations/orchestration/pipeline/service.py:27-61` | 27 values: `PIPELINE_START`, `STEP_START`, `STEP_COMPLETE`, `STEP_ERROR`, `DIALOG_REQUIRED`, `HITL_REQUIRED`, `LLM_ROUTE_DECISION`, `ROUTING_COMPLETE`, `DISPATCH_START`, `AGENT_THINKING`, `AGENT_TOOL_CALL`, `AGENT_COMPLETE`, `AGENT_TEAM_CREATED`, `AGENT_MEMBER_STARTED`, `AGENT_MEMBER_THINKING`, `AGENT_MEMBER_TOOL_CALL`, `AGENT_MEMBER_COMPLETED`, `AGENT_TEAM_COMPLETED`, `AGENT_TEAM_MESSAGE`, `AGENT_INBOX_RECEIVED`, `AGENT_TASK_CLAIMED`, `AGENT_TASK_REASSIGNED`, `AGENT_APPROVAL_REQUIRED`, `EXPERT_ROSTER_PREVIEW`, `TEXT_DELTA`, `PIPELINE_COMPLETE`, `PIPELINE_ERROR` | Unified pipeline SSE event types (Phase 45 Sprint 153-156). |
| `ToolRiskLevel` | `integrations/poc/approval_gate.py:33` | `LOW`, `MEDIUM`, `HIGH` | HITL approval risk classification (PoC V4). |
| `TaskStatus` (PoC) | `integrations/poc/shared_task_list.py:29` | `PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED` | SharedTaskList task lifecycle (PoC V4). |
| `VALID_DOMAINS` (frozenset) | `integrations/orchestration/experts/registry.py:27` | `{network, database, application, security, cloud, general, custom}` | Agent Expert domain whitelist (Phase 46; declared as frozenset, not Python Enum). |

### Notes

- **Sprint 166**: `SubagentExecutor._infer_complexity()` returns string literals (`"simple"`, `"moderate"`, `"complex"`, `"auto"`) — not a formal Python Enum. Flagged for potential refactor.
- **Pipeline step order**: `MemoryStep`=0, `KnowledgeStep`=1, `IntentStep`=2, `RiskStep`=3, `HITLGateStep`=4, `LLMRouteStep`=5, `PostProcessStep`=7 (step 7 identifier) — step 6 is not present as a pipeline step; dispatch occurs inside the `LLMRouteStep` outcome.

### Updated Coverage

| Metric | After Wave 72 | Post-Phase 47 (2026-04-19) |
|--------|---------------|----------------------------|
| Documented Enums | 381 (339 base + 42 L09) | **385** (+4 new: ExecutionRoute, PipelineEventType, ToolRiskLevel, PoC TaskStatus) |
| Coverage | 100% | 100% (Phase 45-47 additions verified via actual source reading) |
