# Phase 3A: API Layer Analysis - Part 2

> **Scope**: `backend/src/api/v1/` — dashboard, devtools, executions, groupchat, handoff, hybrid, learning, mcp, memory, n8n, nested, notifications
> **Analyzed by**: Agent A2
> **Date**: 2026-03-15
> **Total Files**: 42 files, 14,974 LOC

---

## Summary Statistics

| Module | Files | LOC | Endpoints | Assessment | Sprint/Phase |
|--------|-------|-----|-----------|------------|--------------|
| dashboard/ | 2 | 196 | 2 | COMPLETE | Phase 1 |
| devtools/ | 3 | 616 | 12 | COMPLETE | Sprint 4 (Phase 1) |
| executions/ | 3 | 1,045 | 10 | COMPLETE | Sprint 1, 29 (Phase 1, 5) |
| groupchat/ | 4 | 2,785 | 42 | COMPLETE | Sprint 9, 20, 32 (Phase 2, 4) |
| handoff/ | 3 | 1,834 | 14 | COMPLETE | Sprint 8, 29 (Phase 2, 5) |
| hybrid/ | 9 | 3,295 | 23 | COMPLETE | Sprint 52-56 (Phase 13-14) |
| learning/ | 3 | 585 | 13 | COMPLETE | Sprint 4 (Phase 1) |
| mcp/ | 3 | 856 | 13 | COMPLETE | Phase 8-10 |
| memory/ | 3 | 688 | 7 | COMPLETE | Sprint 79 (Phase 22) |
| n8n/ | 3 | 814 | 7 | COMPLETE | Phase 1 |
| nested/ | 3 | 1,712 | 16 | COMPLETE | Sprint 11, 23 (Phase 2, 4) |
| notifications/ | 3 | 548 | 11 | COMPLETE | Sprint 3 (Phase 1) |
| **TOTAL** | **42** | **14,974** | **170** | | |

---

## Module Analysis

### dashboard/
**Files**: 2 files, 196 LOC
**Endpoints**: 2 endpoints

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/dashboard/stats` | GET | Aggregates counts of workflows, agents, executions, checkpoints; calculates success rate and daily execution count | SQLAlchemy queries against Workflow, Agent, Execution, Checkpoint DB models | Silent exception swallowing returns empty stats on any error |
| `/dashboard/executions/chart` | GET | Returns per-day execution counts (completed/failed/running) for last N days | SQLAlchemy count queries per day per status | N+1 query pattern: 3 separate queries per day in a loop (7 days = 21 queries); uses `datetime.utcnow()` (deprecated) |

**Dependencies**: `src.infrastructure.database.session`, `src.infrastructure.database.models.{workflow,execution,agent,checkpoint}`
**Sprint Reference**: Phase 1 (Foundation)
**Assessment**: COMPLETE
**Issues Found**:
- Performance: N+1 query pattern in chart endpoint (3 queries x N days)
- `datetime.utcnow()` usage (deprecated in Python 3.12+)
- Broad exception catch returns empty data instead of error response; masks DB issues

---

### devtools/
**Files**: 3 files, 616 LOC
**Endpoints**: 12 endpoints

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/devtools/health` | GET | Health check with active trace count | In-memory ExecutionTracer singleton | None |
| `/devtools/traces` | GET | List traces with optional workflow_id/status filter | In-memory ExecutionTracer | None |
| `/devtools/traces` | POST | Start new execution trace | In-memory ExecutionTracer | None |
| `/devtools/traces/{execution_id}` | GET | Get trace details | In-memory ExecutionTracer | None |
| `/devtools/traces/{execution_id}/end` | POST | End a trace with status and result | In-memory ExecutionTracer | None |
| `/devtools/traces/{execution_id}` | DELETE | Delete a trace | In-memory ExecutionTracer | None |
| `/devtools/traces/{execution_id}/events` | POST | Add event to trace (validates type & severity) | In-memory ExecutionTracer | None |
| `/devtools/traces/{execution_id}/events` | GET | List events with optional type/severity/executor filter | In-memory ExecutionTracer | None |
| `/devtools/traces/{execution_id}/spans` | POST | Start a new span within a trace | In-memory ExecutionTracer | None |
| `/devtools/spans/{span_id}/end` | POST | End a span | In-memory ExecutionTracer | None |
| `/devtools/traces/{execution_id}/timeline` | GET | Get timeline for visualization | In-memory ExecutionTracer | None |
| `/devtools/traces/{execution_id}/statistics` | GET | Get trace statistics (LLM calls, tool calls, errors, etc.) | In-memory ExecutionTracer | None |

**Dependencies**: `src.domain.devtools.ExecutionTracer`, `src.domain.devtools.TraceEventType`, `src.domain.devtools.tracer.TraceSeverity`
**Sprint Reference**: Sprint 4, Phase 1 (Developer Experience)
**Assessment**: COMPLETE
**Issues Found**:
- All trace data is in-memory only (global singleton `_tracer`); data lost on restart
- No database persistence for traces
- No authentication/authorization on debug endpoints

---

### executions/
**Files**: 3 files, 1,045 LOC
**Endpoints**: 10 endpoints

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/executions/` | GET | List executions with pagination, filter by workflow_id or status | ExecutionRepository (PostgreSQL) | None |
| `/executions/` | POST | Create new execution record | ExecutionRepository | None |
| `/executions/{execution_id}` | GET | Get execution detail with LLM stats | ExecutionRepository | None |
| `/executions/{execution_id}/cancel` | POST | Cancel execution; validates state transition via EnhancedExecutionStateMachine | ExecutionRepository + state machine | None |
| `/executions/{execution_id}/transitions` | GET | Get valid state transitions for current status | EnhancedExecutionStateMachine class methods | None |
| `/executions/status/running` | GET | Get all running executions | ExecutionRepository | None |
| `/executions/status/recent` | GET | Get most recent executions (limit param) | ExecutionRepository | None |
| `/executions/workflows/{workflow_id}/stats` | GET | Aggregated execution stats for a workflow | ExecutionRepository | None |
| `/executions/{execution_id}/resume` | POST | Resume paused execution after checkpoint approval | CheckpointService + WorkflowResumeService | Imports inside function body (lazy import) |
| `/executions/{execution_id}/resume-status` | GET | Get resume status (can_resume, pending checkpoints) | CheckpointService + WorkflowResumeService | Imports inside function body; accesses `repo._session` (private attribute) |
| `/executions/{execution_id}/shutdown` | POST | Graceful shutdown with optional checkpoint save and resource cleanup | ExecutionRepository | Checkpoint save is log-only ("In production, this would persist"); resource cleanup is log-only |

**Dependencies**: `src.integrations.agent_framework.core.state_machine.EnhancedExecutionStateMachine`, `src.domain.executions.ExecutionStatus`, `src.infrastructure.database.repositories.execution.ExecutionRepository`, `src.domain.checkpoints.CheckpointService`, `src.domain.workflows.resume_service.WorkflowResumeService`
**Sprint Reference**: Sprint 1 (Phase 1), Sprint 29 (Phase 5 migration), Phase 12 (graceful shutdown)
**Assessment**: COMPLETE
**Issues Found**:
- Shutdown endpoint: checkpoint save and resource cleanup are stub implementations (log-only, noted as "In production, this would persist/release")
- Resume endpoints use lazy imports inside function body
- Resume endpoint accesses private `repo._session` attribute directly
- `datetime.utcnow()` usage (deprecated)

---

### groupchat/
**Files**: 4 files, 2,785 LOC
**Endpoints**: 42 endpoints

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| **GroupChat CRUD (14)** | | | | |
| `/groupchat/` | POST | Create group chat with participants and config | In-memory dict `_group_chats` | In-memory storage |
| `/groupchat/` | GET | List all group chats | In-memory dict | In-memory storage |
| `/groupchat/{group_id}` | GET | Get specific group chat | In-memory dict | In-memory storage |
| `/groupchat/{group_id}/config` | PATCH | Update group chat config | In-memory dict | In-memory storage |
| `/groupchat/{group_id}/agents/{agent_id}` | POST | Add agent to group chat | In-memory dict | In-memory storage |
| `/groupchat/{group_id}/agents/{agent_id}` | DELETE | Remove agent from group chat | In-memory dict | In-memory storage |
| `/groupchat/{group_id}/start` | POST | Start conversation (runs rounds) | GroupChatBuilderAdapter | In-memory storage |
| `/groupchat/{group_id}/message` | POST | Send message to group chat | GroupChatBuilderAdapter | In-memory storage |
| `/groupchat/{group_id}/messages` | GET | Get all messages | In-memory dict | In-memory storage |
| `/groupchat/{group_id}/transcript` | GET | Get chat transcript | In-memory dict | In-memory storage |
| `/groupchat/{group_id}/summary` | GET | Get summary with stats | In-memory dict | In-memory storage |
| `/groupchat/{group_id}/terminate` | POST | Terminate group chat | In-memory dict | In-memory storage |
| `/groupchat/{group_id}` | DELETE | Delete group chat | In-memory dict | In-memory storage |
| `/groupchat/{group_id}/ws` | WebSocket | Real-time group chat via WebSocket | In-memory dict | In-memory storage |
| **Multi-turn Sessions (8)** | | | | |
| `/groupchat/sessions/` | POST | Create multi-turn session | MultiTurnAPIService (in-memory) | In-memory storage |
| `/groupchat/sessions/` | GET | List sessions | MultiTurnAPIService | In-memory storage |
| `/groupchat/sessions/{session_id}` | GET | Get session details | MultiTurnAPIService | In-memory storage |
| `/groupchat/sessions/{session_id}/turns` | POST | Execute a turn | MultiTurnAPIService | Uses mock_agent_handler |
| `/groupchat/sessions/{session_id}/history` | GET | Get session history | MultiTurnAPIService | In-memory storage |
| `/groupchat/sessions/{session_id}/context` | PATCH | Update session context | MultiTurnAPIService | In-memory storage |
| `/groupchat/sessions/{session_id}/close` | POST | Close session | MultiTurnAPIService | In-memory storage |
| `/groupchat/sessions/{session_id}` | DELETE | Delete session | MultiTurnAPIService | In-memory storage |
| **Voting (12)** | | | | |
| `/groupchat/voting/` | POST | Create voting session | GroupChatVotingAdapter | In-memory storage |
| `/groupchat/voting/` | GET | List voting sessions | In-memory dict `_voting_sessions` | In-memory storage |
| `/groupchat/voting/{session_id}` | GET | Get voting session | In-memory dict | In-memory storage |
| `/groupchat/voting/{session_id}/vote` | POST | Cast vote | GroupChatVotingAdapter | In-memory storage |
| `/groupchat/voting/{session_id}/vote/{voter_id}` | PATCH | Update vote | GroupChatVotingAdapter | In-memory storage |
| `/groupchat/voting/{session_id}/vote/{voter_id}` | DELETE | Retract vote | GroupChatVotingAdapter | In-memory storage |
| `/groupchat/voting/{session_id}/votes` | GET | Get all votes | In-memory dict | In-memory storage |
| `/groupchat/voting/{session_id}/calculate` | POST | Calculate voting result | GroupChatVotingAdapter | In-memory storage |
| `/groupchat/voting/{session_id}/statistics` | GET | Get voting statistics | GroupChatVotingAdapter | In-memory storage |
| `/groupchat/voting/{session_id}/close` | POST | Close voting | In-memory dict | In-memory storage |
| `/groupchat/voting/{session_id}/cancel` | POST | Cancel voting | In-memory dict | In-memory storage |
| `/groupchat/voting/{session_id}` | DELETE | Delete voting session | In-memory dict | In-memory storage |
| **Adapter (8)** | | | | |
| `/groupchat/adapter/` | POST | Create adapter instance | In-memory dict `_adapters` | In-memory storage |
| `/groupchat/adapter/` | GET | List adapters | In-memory dict | In-memory storage |
| `/groupchat/adapter/{adapter_id}` | GET | Get adapter | In-memory dict | In-memory storage |
| `/groupchat/adapter/{adapter_id}/run` | POST | Run group chat through adapter | GroupChatBuilderAdapter | In-memory storage |
| `/groupchat/adapter/{adapter_id}/participants` | POST | Add participant to adapter | In-memory dict | In-memory storage |
| `/groupchat/adapter/{adapter_id}/participants/{name}` | DELETE | Remove participant | In-memory dict | In-memory storage |
| `/groupchat/adapter/{adapter_id}` | DELETE | Delete adapter | In-memory dict | In-memory storage |
| `/groupchat/orchestrator/select` | POST | Select orchestration manager | In-memory logic | In-memory storage |

**Dependencies**: `src.integrations.agent_framework.builders.{GroupChatBuilderAdapter, GroupChatVotingAdapter}`, `src.integrations.agent_framework.multiturn.MultiTurnAdapter`
**Sprint Reference**: Sprint 9 (Phase 2), Sprint 20 (Phase 4 adapter migration), Sprint 32 (multi-turn migration)
**Assessment**: COMPLETE (functionally) but all in-memory
**Issues Found**:
- **ALL state is in-memory** (comment: "In-Memory State for MVP - replace with proper DI in production")
- Multi-turn session turns use `mock_agent_handler` that returns a hardcoded string
- No database persistence for any groupchat, session, voting, or adapter data
- Data lost on server restart
- Largest route file in this scope (1,770 LOC)

---

### handoff/
**Files**: 3 files, 1,834 LOC
**Endpoints**: 14 endpoints

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/handoff/trigger` | POST | Trigger agent handoff with source/target/policy | HandoffService adapter | None |
| `/handoff/{handoff_id}/status` | GET | Get handoff status | HandoffService | None |
| `/handoff/{handoff_id}/cancel` | POST | Cancel an active handoff | HandoffService | None |
| `/handoff/history` | GET | Get handoff history with filters | HandoffService | None |
| `/handoff/capability/match` | POST | Find agents matching capability requirements | HandoffService (CapabilityMatcher) | None |
| `/handoff/agents/{agent_id}/capabilities` | GET | Get agent capabilities | HandoffService | None |
| `/handoff/agents/{agent_id}/capabilities` | POST | Register new capability for agent | HandoffService | None |
| `/handoff/agents/{agent_id}/capabilities/{capability_name}` | DELETE | Remove capability from agent | HandoffService | None |
| `/handoff/hitl/sessions` | GET | List HITL sessions | In-memory `_hitl_sessions` dict | In-memory, HITL not fully migrated |
| `/handoff/hitl/sessions/{session_id}` | GET | Get HITL session details | In-memory dict | In-memory |
| `/handoff/hitl/pending` | GET | Get pending HITL requests | In-memory dict | In-memory |
| `/handoff/hitl/submit` | POST | Submit HITL input/response | In-memory dict | In-memory |
| `/handoff/hitl/sessions/{session_id}/cancel` | POST | Cancel HITL session | In-memory dict | In-memory |
| `/handoff/hitl/sessions/{session_id}/escalate` | POST | Escalate HITL session | In-memory dict | In-memory |

**Dependencies**: `src.integrations.agent_framework.builders.handoff_service.HandoffService`, `src.integrations.agent_framework.builders.handoff_policy.LegacyHandoffPolicy`, `src.integrations.agent_framework.builders.handoff_capability.{MatchStrategy, AgentCapabilityInfo, CapabilityCategory}`
**Sprint Reference**: Sprint 8 (Phase 2), Sprint 29 (Phase 5 adapter migration)
**Assessment**: COMPLETE (core handoff), PARTIAL (HITL endpoints)
**Issues Found**:
- Core handoff endpoints properly use HandoffService adapter (migrated Sprint 29)
- HITL endpoints (6 of 14) still use in-memory dict storage, noted as "preserved for future migration to WorkflowApprovalAdapter"
- HandoffService is a module-level singleton (not DI-managed)

---

### hybrid/
**Files**: 9 files, 3,295 LOC
**Endpoints**: 23 endpoints (across 4 route files)

#### hybrid/core_routes.py (4 endpoints)

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/hybrid/analyze` | POST | Analyze input and recommend MAF vs Claude SDK mode | ContextBridge + HybridAnalyzer | None |
| `/hybrid/execute` | POST | Execute operation in hybrid mode | ContextBridge + HybridExecutor | None |
| `/hybrid/metrics` | GET | Get hybrid execution metrics | In-memory metrics collector | None |
| `/hybrid/status` | GET | Get hybrid system status | ContextBridge state | None |

#### hybrid/context_routes.py (5 endpoints)

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/hybrid/context/{session_id}` | GET | Get hybrid context for session | ContextBridge | None |
| `/hybrid/context/{session_id}/status` | GET | Get sync status for session | ContextSynchronizer | None |
| `/hybrid/context/sync` | POST | Trigger manual context sync between MAF and Claude | ContextSynchronizer | None |
| `/hybrid/context/merge` | POST | Merge MAF and Claude contexts | ContextBridge | "Create placeholder contexts if IDs provided" comment |
| `/hybrid/context` | GET | List all hybrid contexts | ContextBridge | None |

#### hybrid/switch_routes.py (7 endpoints)

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/hybrid/switch` | POST | Switch between MAF and Claude SDK modes | ModeSwitcher | None |
| `/hybrid/switch/status/{session_id}` | GET | Get current mode status | ModeSwitcher | None |
| `/hybrid/switch/rollback` | POST | Rollback to previous mode | ModeSwitcher | None |
| `/hybrid/switch/history/{session_id}` | GET | Get mode switch history | ModeSwitcher | None |
| `/hybrid/switch/checkpoints/{session_id}` | GET | Get mode checkpoints | ModeSwitcher | None |
| `/hybrid/switch/checkpoints/{session_id}/{checkpoint_id}` | DELETE | Delete checkpoint | ModeSwitcher | None |
| `/hybrid/switch/history/{session_id}` | DELETE | Clear switch history | ModeSwitcher | None |

#### hybrid/risk_routes.py (7 endpoints)

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/hybrid/risk/assess` | POST | Multi-dimensional risk assessment for operation | RiskEngine (ToolEvaluator + ContextEvaluator + PatternDetector) | None |
| `/hybrid/risk/assess-batch` | POST | Batch risk assessment for multiple operations | RiskEngine | None |
| `/hybrid/risk/session/{session_id}` | GET | Get session risk profile | RiskEngine | None |
| `/hybrid/risk/metrics` | GET | Get risk engine metrics | RiskEngine | None |
| `/hybrid/risk/session/{session_id}/history` | DELETE | Clear session risk history | RiskEngine | None |
| `/hybrid/risk/metrics/reset` | POST | Reset risk metrics | RiskEngine | None |
| `/hybrid/risk/config` | GET | Get risk engine configuration | RiskEngine | None |

**Dependencies**: `src.integrations.hybrid.context.bridge.ContextBridge`, `src.integrations.hybrid.context.sync.synchronizer.ContextSynchronizer`, `src.integrations.hybrid.context.sync.events.SyncEventPublisher`, `src.integrations.hybrid.context.models.*`, `src.integrations.hybrid.switching.switcher.ModeSwitcher`, `src.integrations.hybrid.risk.*`
**Sprint Reference**: Sprint 52-56 (Phase 13-14)
**Assessment**: COMPLETE
**Issues Found**:
- Shared singleton pattern between core_routes and context_routes (ContextBridge)
- One placeholder context comment in merge endpoint
- Separate schema files for each route group (good separation but 4 schema files total)
- `dependencies.py` provides shared DI functions across hybrid sub-modules

---

### learning/
**Files**: 3 files, 585 LOC
**Endpoints**: 13 endpoints

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/learning/health` | GET | Health check for learning service | FewShotLearningService (in-memory) | None |
| `/learning/statistics` | GET | Get overall learning statistics | FewShotLearningService | None |
| `/learning/corrections` | POST | Record a correction (new learning case) | FewShotLearningService | None |
| `/learning/cases` | GET | List learning cases with pagination/filter | FewShotLearningService | None |
| `/learning/cases/{case_id}` | GET | Get learning case details | FewShotLearningService | None |
| `/learning/cases/{case_id}` | DELETE | Delete a learning case | FewShotLearningService | None |
| `/learning/cases/{case_id}/approve` | POST | Approve a learning case | FewShotLearningService | None |
| `/learning/cases/{case_id}/reject` | POST | Reject a learning case | FewShotLearningService | None |
| `/learning/cases/bulk-approve` | POST | Bulk approve multiple cases | FewShotLearningService | None |
| `/learning/similar` | POST | Find similar cases by scenario/input | FewShotLearningService | None |
| `/learning/prompt` | POST | Build few-shot prompt from approved cases | FewShotLearningService | None |
| `/learning/cases/{case_id}/effectiveness` | POST | Record case effectiveness feedback | FewShotLearningService | None |
| `/learning/scenarios/{scenario_name}/statistics` | GET | Get per-scenario statistics | FewShotLearningService | None |

**Dependencies**: `src.domain.learning.FewShotLearningService`
**Sprint Reference**: Sprint 4 (Phase 1, Developer Experience)
**Assessment**: COMPLETE
**Issues Found**:
- FewShotLearningService is a module-level singleton (in-memory)
- No database persistence for learning cases
- Clean API design with proper request/response schemas

---

### mcp/
**Files**: 3 files, 856 LOC
**Endpoints**: 13 endpoints

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/mcp/servers` | GET | List all registered MCP servers | MCPServerRegistry (in-memory) | None |
| `/mcp/servers` | POST | Register a new MCP server | MCPServerRegistry | None |
| `/mcp/servers/{server_name}` | GET | Get server details | MCPServerRegistry | None |
| `/mcp/servers/{server_name}` | DELETE | Unregister a server | MCPServerRegistry | None |
| `/mcp/servers/{server_name}/connect` | POST | Connect to an MCP server | MCPServerRegistry | None |
| `/mcp/servers/{server_name}/disconnect` | POST | Disconnect from server | MCPServerRegistry | None |
| `/mcp/servers/{server_name}/tools` | GET | List tools for a specific server | MCPServerRegistry | None |
| `/mcp/tools` | GET | List all available tools across servers | MCPServerRegistry | None |
| `/mcp/tools/execute` | POST | Execute a tool on a connected server | MCPServerRegistry | None |
| `/mcp/status` | GET | Get registry status summary | MCPServerRegistry | None |
| `/mcp/audit` | GET | Query audit logs | MCPAuditLogger | None |
| `/mcp/connect-all` | POST | Connect to all registered servers | MCPServerRegistry | None |
| `/mcp/disconnect-all` | POST | Disconnect from all servers | MCPServerRegistry | None |

**Dependencies**: `src.integrations.mcp.registry.MCPServerRegistry`, `src.integrations.mcp.registry.MCPAuditLogger`
**Sprint Reference**: Phase 8-10
**Assessment**: COMPLETE
**Issues Found**:
- MCPServerRegistry is in-memory singleton
- Well-structured with proper error handling and audit logging
- Includes bulk connect/disconnect operations

---

### memory/
**Files**: 3 files, 688 LOC
**Endpoints**: 7 endpoints

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/memory/add` | POST | Add new memory to specified layer | UnifiedMemoryManager | None |
| `/memory/search` | POST | Search memories by query and optional filters | UnifiedMemoryManager | None |
| `/memory/user/{user_id}` | GET | Get all memories for a user | UnifiedMemoryManager | None |
| `/memory/{memory_id}` | DELETE | Delete memory by ID | UnifiedMemoryManager | None |
| `/memory/promote` | POST | Promote memory to a higher layer (working -> episodic -> semantic) | UnifiedMemoryManager | None |
| `/memory/context` | POST | Get context-relevant memories for current situation | UnifiedMemoryManager | None |
| `/memory/health` | GET | Health check for memory system | UnifiedMemoryManager | None |

**Dependencies**: `src.integrations.memory.{UnifiedMemoryManager, MemoryLayer, MemoryMetadata, MemoryType}`
**Sprint Reference**: Sprint 79 (Phase 22)
**Assessment**: COMPLETE
**Issues Found**:
- Clean, well-structured API with proper schema validation
- UnifiedMemoryManager wraps mem0 integration
- No issues found; proper three-layer memory model (working, episodic, semantic)

---

### n8n/
**Files**: 3 files, 814 LOC
**Endpoints**: 7 endpoints

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/n8n/webhook` | POST | Receive general n8n webhook with HMAC verification | `_process_webhook()` internal handler | None |
| `/n8n/webhook/{workflow_id}` | POST | Receive workflow-specific webhook with HMAC verification | `_process_webhook()` | None |
| `/n8n/status` | GET | Check n8n connection status (uses N8nApiClient) | N8nApiClient health_check | None |
| `/n8n/config` | GET | Get n8n configuration (secrets masked) | Module-level `_n8n_config` dict | In-memory config |
| `/n8n/config` | PUT | Update n8n configuration | Module-level `_n8n_config` dict | In-memory config; changes lost on restart |
| `/n8n/callback` | POST | Receive callback from IPA orchestration | In-memory `_callback_store` dict | In-memory storage |
| `/n8n/callback/{orchestration_id}` | GET | Get callback result by orchestration ID | In-memory `_callback_store` | In-memory storage |

**Dependencies**: `src.integrations.mcp.servers.n8n.client.{N8nApiClient, N8nConfig}` (lazy import in status endpoint)
**Sprint Reference**: Phase 1
**Assessment**: COMPLETE
**Issues Found**:
- `_n8n_config` is a module-level dict initialized from env vars; runtime updates lost on restart
- `_callback_store` is in-memory dict; no persistence for callback results
- HMAC verification properly implemented for webhook security
- Lazy import of N8nApiClient inside endpoint function
- Config initialized from `os.environ` directly instead of using pydantic Settings

---

### nested/
**Files**: 3 files, 1,712 LOC
**Endpoints**: 16 endpoints

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/nested/configs` | POST | Create nested workflow configuration | NestedWorkflowAdapter | None |
| `/nested/configs` | GET | List nested workflow configurations | NestedWorkflowAdapter | None |
| `/nested/configs/{config_id}` | GET | Get specific configuration | NestedWorkflowAdapter | None |
| `/nested/configs/{config_id}` | DELETE | Delete configuration | NestedWorkflowAdapter | None |
| `/nested/sub-workflows/execute` | POST | Execute a sub-workflow | NestedWorkflowAdapter | None |
| `/nested/sub-workflows/batch` | POST | Batch execute multiple sub-workflows | NestedWorkflowAdapter | None |
| `/nested/sub-workflows/{execution_id}/status` | GET | Get sub-workflow execution status | NestedWorkflowAdapter | None |
| `/nested/sub-workflows/{execution_id}/cancel` | POST | Cancel sub-workflow execution | NestedWorkflowAdapter | None |
| `/nested/recursive/execute` | POST | Execute recursive workflow | NestedWorkflowAdapter | None |
| `/nested/recursive/{execution_id}/status` | GET | Get recursion status with depth info | NestedWorkflowAdapter | None |
| `/nested/compositions` | POST | Create workflow composition | NestedWorkflowAdapter | None |
| `/nested/compositions/execute` | POST | Execute composition (sequential/parallel) | NestedWorkflowAdapter | None |
| `/nested/context/propagate` | POST | Propagate context between workflows | NestedWorkflowAdapter | None |
| `/nested/context/flow/{workflow_id}` | GET | Get data flow events | NestedWorkflowAdapter | None |
| `/nested/context/tracker/stats` | GET | Get context tracker statistics | NestedWorkflowAdapter | None |
| `/nested/stats` | GET | Get nested workflow statistics | NestedWorkflowAdapter | None |

**Dependencies**: `src.integrations.agent_framework.builders.nested_workflow_adapter.NestedWorkflowAdapter`
**Sprint Reference**: Sprint 11 (Phase 2), Sprint 23 (Phase 4 adapter migration)
**Assessment**: COMPLETE
**Issues Found**:
- Well-structured with proper adapter pattern usage
- NestedWorkflowAdapter wraps Agent Framework APIs
- Large schema file (549 LOC) with comprehensive type definitions
- Supports advanced features: recursive workflows, batch execution, compositions

---

### notifications/
**Files**: 3 files, 548 LOC
**Endpoints**: 11 endpoints

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/notifications/approval` | POST | Send Teams approval notification (Adaptive Card) | TeamsNotificationService | None |
| `/notifications/completion` | POST | Send completion notification | TeamsNotificationService | None |
| `/notifications/error` | POST | Send error alert notification | TeamsNotificationService | None |
| `/notifications/custom` | POST | Send custom notification | TeamsNotificationService | None |
| `/notifications/history` | GET | Get notification history with filters | TeamsNotificationService | None |
| `/notifications/statistics` | GET | Get notification statistics | TeamsNotificationService | None |
| `/notifications/history` | DELETE | Clear notification history | TeamsNotificationService | None |
| `/notifications/config` | GET | Get current notification config | TeamsNotificationService | None |
| `/notifications/config` | PUT | Update notification config | TeamsNotificationService | None |
| `/notifications/types` | GET | List available notification types | TeamsNotificationService | None |
| `/notifications/health` | GET | Health check | TeamsNotificationService | None |

**Dependencies**: `src.domain.notifications.{TeamsNotificationService, TeamsNotificationConfig, NotificationPriority, NotificationType}`
**Sprint Reference**: Sprint 3 (Phase 1)
**Assessment**: COMPLETE
**Issues Found**:
- TeamsNotificationService is a module-level singleton
- Clean implementation delegating to domain layer
- No database persistence (service manages its own state)

---

## Cross-Module Analysis

### Feature Mapping to Plan Baseline

| Feature ID | Feature | Modules | Status |
|-----------|---------|---------|--------|
| A5 | Execution Management | executions/ | COMPLETE - DB-backed, state machine validated |
| A6 | Agent Orchestration (GroupChat) | groupchat/ | COMPLETE - but in-memory only |
| A7 | Agent Handoff | handoff/ | COMPLETE - core migrated, HITL partial |
| A8 | Nested Workflows | nested/ | COMPLETE - adapter pattern |
| A9 | Developer Tools | devtools/ | COMPLETE - in-memory traces |
| B3 | n8n Integration | n8n/ | COMPLETE - webhook + HMAC security |
| B4 | MCP Server Management | mcp/ | COMPLETE - registry + audit |
| C4 | Notifications | notifications/ | COMPLETE - Teams integration |
| C5 | Dashboard Analytics | dashboard/ | COMPLETE - real DB queries |
| E2 | Hybrid MAF+SDK | hybrid/ | COMPLETE - full 23-endpoint suite |
| E7 | Memory System | memory/ | COMPLETE - three-layer mem0 |

### Recurring Issues Summary

| Issue Category | Affected Modules | Severity |
|----------------|-----------------|----------|
| **In-memory storage (no DB persistence)** | groupchat, devtools, learning, handoff (HITL), n8n (config/callbacks) | HIGH |
| **Module-level singletons** | devtools, learning, notifications, handoff, mcp, n8n | MEDIUM |
| **`datetime.utcnow()` deprecated** | dashboard, executions | LOW |
| **Lazy imports inside functions** | executions (resume) | LOW |
| **Private attribute access** | executions (`repo._session`) | LOW |
| **Stub/log-only implementations** | executions (shutdown checkpoint/cleanup) | MEDIUM |
| **Mock handlers** | groupchat (mock_agent_handler) | MEDIUM |
| **Config via os.environ** | n8n (should use pydantic Settings) | LOW |

### Data Flow Patterns

1. **DB-Backed (Production-Ready)**: dashboard, executions -- queries PostgreSQL via repositories
2. **Adapter-Delegated**: groupchat (GroupChatBuilderAdapter), handoff (HandoffService), nested (NestedWorkflowAdapter), hybrid (ContextBridge/ModeSwitcher/RiskEngine) -- delegates to integration layer adapters
3. **Domain-Service Delegated**: learning (FewShotLearningService), notifications (TeamsNotificationService) -- delegates to domain layer services
4. **Integration-Delegated**: mcp (MCPServerRegistry), memory (UnifiedMemoryManager) -- delegates to integration modules
5. **In-Memory Only**: n8n config/callbacks -- pure module-level state

### Architecture Quality Assessment

- **Best**: executions/, hybrid/, nested/, memory/ -- proper DI, adapter patterns, comprehensive schemas
- **Good**: handoff/ (core), mcp/, notifications/, learning/ -- clean delegation but singleton pattern
- **Needs Work**: groupchat/ (massive 1770 LOC route file, all in-memory), n8n/ (env-based config, in-memory state), dashboard/ (N+1 queries)
- **Acceptable for Dev**: devtools/ (in-memory by design for debugging tools)
