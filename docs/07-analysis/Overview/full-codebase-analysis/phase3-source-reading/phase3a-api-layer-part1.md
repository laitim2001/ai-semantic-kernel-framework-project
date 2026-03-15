# Phase 3A: API Layer Analysis - Part 1

> **Scope**: `backend/src/api/v1/` — Modules: `__init__.py`, `dependencies.py`, `a2a/`, `ag_ui/`, `agents/`, `audit/`, `autonomous/`, `cache/`, `checkpoints/`, `claude_sdk/`, `code_interpreter/`, `concurrent/`, `connectors/`, `correlation/`
>
> **Total Files**: 46 Python files
> **Total LOC**: 15,868 lines
> **Analysis Date**: 2026-03-15
> **Analyst**: Agent A1

---

## Table of Contents

1. [Shared Infrastructure](#shared-infrastructure)
2. [Module-by-Module Analysis](#module-by-module-analysis)
3. [Cross-Cutting Concerns](#cross-cutting-concerns)
4. [Summary Statistics](#summary-statistics)

---

## Shared Infrastructure

### `__init__.py` (220 LOC)

**Purpose**: Central router aggregation — assembles all 47 registered routers into `api_router` under `/api/v1`.

**Architecture**:
- `api_router` (prefix `/api/v1`)
  - `public_router` — No auth required (only `auth_router`)
  - `protected_router` — All other routes, guarded by `Depends(require_auth)` (JWT)

**Key Design Decision**: Global auth at the `protected_router` level means individual routes do NOT need to add their own auth dependency unless they need the full `User` model (via `get_current_user`).

**Issues Found**:
1. Health check endpoints (`/`, `/health`, `/ready`) are on the FastAPI app directly in `main.py`, not under `/api/v1` — this is intentional but worth noting for API discovery.

---

### `dependencies.py` (180 LOC)

**Purpose**: Shared authentication dependency injection providers.

**Endpoints**: N/A (dependency module only)

**Dependencies Provided**:
| Dependency | Auth Level | Returns | DB Lookup? |
|-----------|-----------|---------|-----------|
| `get_current_user` | Required | `User` model | Yes |
| `get_current_user_optional` | Optional | `User` or `None` | Yes (if token present) |
| `get_current_active_admin` | Admin required | `User` (admin) | Yes |
| `get_current_operator_or_admin` | Operator+ | `User` (operator/admin) | Yes |

**Data Source**: PostgreSQL via `UserRepository` + JWT token decode via `src.core.security.decode_token`.

**Assessment**: COMPLETE — Well-implemented with proper error handling, inactive user checks, and role-based access control.

**Issues Found**:
1. None significant. Clean implementation.

---

## Module-by-Module Analysis

---

### a2a/
**Files**: 2 files, 245 LOC
**Endpoints**: 14 endpoints
**Sprint Reference**: Phase 23, Sprint 81 (Feature E6)
**Assessment**: COMPLETE

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/a2a/message` | POST | Send A2A message between agents | In-memory `MessageRouter` | No persistence (in-memory only) |
| `/a2a/message/{message_id}` | GET | Get message delivery status | In-memory `MessageRouter` | Lost on restart |
| `/a2a/messages/pending` | GET | List pending messages for agent | In-memory `MessageRouter` | — |
| `/a2a/conversation/{correlation_id}` | GET | Get conversation thread | In-memory `MessageRouter` | — |
| `/a2a/agents/register` | POST | Register agent with capabilities | In-memory `AgentDiscoveryService` | No persistence |
| `/a2a/agents/{agent_id}` | DELETE | Unregister agent | In-memory `AgentDiscoveryService` | — |
| `/a2a/agents` | GET | List all registered agents | In-memory `AgentDiscoveryService` | — |
| `/a2a/agents/{agent_id}` | GET | Get single agent details | In-memory `AgentDiscoveryService` | — |
| `/a2a/agents/discover` | POST | Discover agents by capability/tags | In-memory `AgentDiscoveryService` | — |
| `/a2a/agents/{agent_id}/capabilities` | GET | Get agent capabilities | In-memory `AgentDiscoveryService` | — |
| `/a2a/agents/{agent_id}/heartbeat` | POST | Update agent heartbeat | In-memory `AgentDiscoveryService` | — |
| `/a2a/agents/{agent_id}/status` | PUT | Update agent status | In-memory `AgentDiscoveryService` | — |
| `/a2a/statistics` | GET | Get discovery + router stats | In-memory both services | — |
| `/a2a/maintenance/cleanup` | POST | Clean stale agents + expired msgs | In-memory both services | — |

**Dependencies**: `src.integrations.a2a` (A2AMessage, AgentCapability, AgentDiscoveryService, DiscoveryQuery, MessageRouter, MessageType, MessagePriority, A2AAgentStatus)

**Issues Found**:
1. **In-memory only**: Both `AgentDiscoveryService` and `MessageRouter` are global singletons stored in-memory. All state lost on server restart. No database or Redis persistence.
2. **No auth beyond global**: No per-endpoint role checks. Any authenticated user can register/unregister agents.
3. **Global mutable state**: `_discovery_service` and `_message_router` are module-level globals — potential thread safety concerns.

---

### ag_ui/
**Files**: 5 files, 3,629 LOC
**Endpoints**: ~29 endpoints
**Sprint Reference**: Phase 15, Sprints 58-61, 68 (Feature E5)
**Assessment**: COMPLETE

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/ag-ui/health` | GET | Health check | Static response | Hardcoded version "1.0.0" |
| `/ag-ui/status` | GET | Bridge component status | Global state inspection | — |
| `/ag-ui/reset` | POST | Reset bridge and Claude executor | Global state reset | Exposes API key prefix in response |
| `/ag-ui` | POST | Run agent via SSE stream | Claude API / Simulation | Core SSE streaming endpoint |
| `/ag-ui/approvals/{id}/approve` | POST | Approve pending tool call | In-memory `ApprovalStorage` | — |
| `/ag-ui/approvals/{id}/reject` | POST | Reject pending tool call | In-memory `ApprovalStorage` | — |
| `/ag-ui/approvals/pending` | GET | List pending approvals | In-memory `ApprovalStorage` | — |
| `/ag-ui/approvals/stats` | GET | Approval statistics | In-memory `ApprovalStorage` | — |
| `/ag-ui/threads/{id}/state` | GET | Get shared thread state | In-memory `SharedStateHandler` | — |
| `/ag-ui/threads/{id}/state` | PATCH | Update thread state (delta/snapshot) | In-memory `SharedStateHandler` | — |
| `/ag-ui/history/{thread_id}` | GET | Get conversation history | In-memory store | — |
| `/ag-ui/history/{thread_id}` | DELETE | Clear conversation history | In-memory store | — |
| `/ag-ui/test/workflow-progress` | POST | Generate test workflow progress event | Mock data | Test-only endpoint |
| `/ag-ui/test/mode-switch` | POST | Generate test mode switch event | Mock data | Test-only endpoint |
| `/ag-ui/test/ui-component` | POST | Generate test UI component event | Mock data | Test-only endpoint |
| `/ag-ui/test/hitl` | POST | Generate test HITL approval event | Mock data | Test-only endpoint |
| `/ag-ui/test/prediction` | POST | Generate test prediction event | Mock data | Test-only endpoint |
| `/ag-ui/upload` | POST | Upload file to sandbox | Filesystem (per-user sandbox) | — |
| `/ag-ui/upload/list` | GET | List uploaded files | Filesystem | — |
| `/ag-ui/upload/{filename}` | DELETE | Delete uploaded file | Filesystem | — |
| `/ag-ui/upload/storage` | GET | Get storage usage | Filesystem | — |

**Dependencies**:
- `src.integrations.ag_ui.bridge` (HybridEventBridge, BridgeConfig, RunAgentInput)
- `src.integrations.ag_ui.features.human_in_loop` (HITLHandler, ApprovalStorage)
- `src.integrations.ag_ui.features.advanced` (SharedStateHandler)
- `src.integrations.hybrid.orchestrator_v2` (HybridOrchestratorV2)
- `src.integrations.claude_sdk.client` (ClaudeSDKClient)
- `src.core.sandbox_config` (SandboxConfig)

**Key Architecture**:
- `dependencies.py` (714 LOC) is the brain — creates Claude SDK client, builds orchestrator, manages Redis connection, provides user identification
- Supports dual mode: real Claude API calls (when `ANTHROPIC_API_KEY` set) or simulation mode (`AG_UI_SIMULATION_MODE=true`)
- SSE streaming via `StreamingResponse` with `text/event-stream` content type
- HITL approval flow: creates approval request → polls `ApprovalStorage` → returns approved/rejected

**Issues Found**:
1. **API key exposure**: `reset_bridge()` and `get_bridge_status()` return API key prefix (first 15 chars). Security risk.
2. **Test endpoints in production**: 5 test endpoints (`/test/*`) generate mock events. Should be behind a feature flag or development-only guard.
3. **Hardcoded model**: Claude model is hardcoded as `"claude-haiku-4-5-20251001"` in `dependencies.py` line 188. Should come from config.
4. **Global mutable state**: `_redis_client`, `_hybrid_bridge`, `_claude_client` are module-level globals.
5. **ApprovalStorage is in-memory**: Approval requests lost on restart. Not suitable for production.
6. **`.env` loading at import time**: `dependencies.py` manually loads `.env` via `dotenv` at module import — fragile path calculation.

---

### agents/
**Files**: 2 files, 405 LOC
**Endpoints**: 6 endpoints
**Sprint Reference**: Phase 1, Sprint 1 (Feature A1)
**Assessment**: COMPLETE

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/agents/` | POST | Create new agent (check name uniqueness) | PostgreSQL via `AgentRepository` | — |
| `/agents/` | GET | List agents with pagination, filters, search | PostgreSQL via `AgentRepository` | — |
| `/agents/{agent_id}` | GET | Get agent by UUID | PostgreSQL via `AgentRepository` | — |
| `/agents/{agent_id}` | PUT | Update agent (partial update, name uniqueness check) | PostgreSQL via `AgentRepository` | — |
| `/agents/{agent_id}` | DELETE | Delete agent by UUID | PostgreSQL via `AgentRepository` | — |
| `/agents/{agent_id}/run` | POST | Execute agent with message | PostgreSQL + `AgentService` (LLM) | Tools list is empty `[]` (comment: "resolved in S1-3") |

**Dependencies**:
- `src.domain.agents.schemas` (AgentCreateRequest, AgentUpdateRequest, AgentResponse, etc.)
- `src.domain.agents.service` (AgentService, AgentConfig)
- `src.infrastructure.database.session` (get_session)
- `src.infrastructure.database.repositories.agent` (AgentRepository)

**Data Flow**: HTTP → API Route → AgentRepository (SQLAlchemy) → PostgreSQL. For `/run`: API → AgentService → LLM (Azure OpenAI).

**Issues Found**:
1. **Empty tools in run**: `AgentConfig` is created with `tools=[]` and comment says "Tools will be resolved in S1-3" — this was Sprint 1, unclear if resolved.
2. **No response model on delete**: Returns `None` with 204 status (correct but no content validation).
3. **Version increment after update**: Calls `increment_version` as a separate DB call after `update` — should be a single transaction.

---

### audit/
**Files**: 4 files, 1,002 LOC
**Endpoints**: ~13 endpoints (7 audit + 6 decision)
**Sprint Reference**: Phase 1 Sprint 3 (Feature G1) + Phase 22 Sprint 80 (Decision Audit)
**Assessment**: COMPLETE

#### audit/routes.py (408 LOC) — Audit Logging

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/audit/logs` | GET | Query audit logs with filters (action, resource, severity, date range) | In-memory `AuditLogger` | Not database-backed |
| `/audit/logs/{entry_id}` | GET | Get single audit entry | In-memory `AuditLogger` | — |
| `/audit/executions/{execution_id}/trail` | GET | Get execution audit trail | In-memory `AuditLogger` | — |
| `/audit/statistics` | GET | Aggregate audit statistics | In-memory `AuditLogger` | — |
| `/audit/export` | GET | Export audit logs (JSON/CSV) | In-memory `AuditLogger` | — |
| `/audit/actions` | GET | List available action types | Static enum values | — |
| `/audit/resources` | GET | List available resource types | Static enum values | — |

**Dependencies**: `src.domain.audit.logger` (AuditLogger, AuditAction, AuditResource, AuditSeverity, AuditQueryParams)

#### audit/decision_routes.py (488 LOC) — Decision Audit

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/decisions` | GET | Query decision records with filters | In-memory `DecisionTracker` | — |
| `/decisions/{decision_id}` | GET | Get decision details | In-memory `DecisionTracker` | — |
| `/decisions/{decision_id}/report` | GET | Generate explainability report | `AuditReportGenerator` | — |
| `/decisions/{decision_id}/feedback` | POST | Add human feedback to decision | In-memory `DecisionTracker` | — |
| `/decisions/statistics` | GET | Decision statistics | In-memory `DecisionTracker` | — |
| `/decisions/summary` | GET | Decision summary report | `AuditReportGenerator` | — |

**Dependencies**: `src.integrations.audit` (AuditConfig, AuditQuery, AuditReportGenerator, DecisionOutcome, DecisionTracker, DecisionType)

**Issues Found**:
1. **All in-memory**: Both `AuditLogger` and `DecisionTracker` are in-memory singletons. Audit data lost on restart — critical for compliance/auditing requirements.
2. **Comment "in production, use proper DI"**: Line 56 of routes.py explicitly acknowledges this is not production-ready.
3. **No database persistence**: For a system meant to track audit trails, this is a significant gap.

---

### autonomous/
**Files**: 2 files, 379 LOC
**Endpoints**: 4 endpoints
**Sprint Reference**: Phase 22, Sprint 79 (Feature C4 related)
**Assessment**: STUB (Mock/UAT Testing Only)

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/claude/autonomous/plan` | POST | Create autonomous task plan | **In-memory mock** with generated steps | 100% mock data |
| `/claude/autonomous/{task_id}` | GET | Get task status | In-memory `AutonomousTaskStore` | — |
| `/claude/autonomous/{task_id}/cancel` | POST | Cancel running task | In-memory `AutonomousTaskStore` | — |
| `/claude/autonomous/history` | GET | Get task history (paginated) | In-memory `AutonomousTaskStore` | — |

**Dependencies**: None (no integration imports — fully self-contained mock)

**Issues Found**:
1. **100% mock implementation**: `AutonomousTaskStore` generates fake steps from hardcoded templates: `["analyze", "plan", "prepare", "execute", "cleanup"]`. No real LLM or planning engine involved.
2. **Module docstring says "Phase 22 Testing"**: This is explicitly a UAT stub.
3. **No integration with Claude SDK**: Despite the `/claude/autonomous` prefix, this module does NOT import or use Claude SDK at all.
4. **In-memory storage**: `_tasks` dict and `_history` list lost on restart.
5. **Hardcoded step templates**: Lines 128-134 define fixed mock steps regardless of input goal.

---

### cache/
**Files**: 3 files, 471 LOC
**Endpoints**: 9 endpoints
**Sprint Reference**: Phase 1, Sprint 2 (Feature C3)
**Assessment**: COMPLETE

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/cache/stats` | GET | Get cache hit/miss statistics | `LLMCacheService` (Redis) | — |
| `/cache/config` | GET | Get cache configuration | `LLMCacheService` settings | — |
| `/cache/config` | PUT | Update cache TTL and enable/disable | `LLMCacheService` settings | — |
| `/cache/get` | POST | Get cached LLM response by key | Redis via `LLMCacheService` | — |
| `/cache/set` | POST | Manually cache an LLM response | Redis via `LLMCacheService` | — |
| `/cache/{key}` | GET | Get cache entry details | Redis via `LLMCacheService` | — |
| `/cache/{key}` | DELETE | Delete specific cache entry | Redis via `LLMCacheService` | — |
| `/cache/clear` | POST | Clear cache (all or by pattern) | Redis via `LLMCacheService` | — |
| `/cache/reset-stats` | POST | Reset cache statistics counters | `LLMCacheService` | — |

**Dependencies**: `src.infrastructure.cache.LLMCacheService`

**Data Flow**: API → LLMCacheService → Redis

**Issues Found**:
1. **Global singleton**: `_cache_service` is a module-level global (line ~53). Comment: "in production, use proper DI".
2. **No auth granularity**: Any authenticated user can clear/modify cache settings. Should restrict `PUT /config`, `POST /clear`, `POST /reset-stats` to admin/operator roles.

---

### checkpoints/
**Files**: 3 files, 882 LOC
**Endpoints**: 10 endpoints
**Sprint Reference**: Phase 1, Sprint 2 (Features B1, B2)
**Assessment**: COMPLETE

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/checkpoints/` | GET | List pending checkpoints with filters | `CheckpointService` (in-memory) | — |
| `/checkpoints/{checkpoint_id}` | GET | Get checkpoint details | `CheckpointService` | — |
| `/checkpoints/{checkpoint_id}/approve` | POST | Approve checkpoint (optionally with data override) | `CheckpointService` | — |
| `/checkpoints/{checkpoint_id}/reject` | POST | Reject checkpoint with reason | `CheckpointService` | — |
| `/checkpoints/{checkpoint_id}/skip` | POST | Skip checkpoint | `CheckpointService` | — |
| `/checkpoints/execution/{execution_id}` | GET | List checkpoints for specific execution | `CheckpointService` | — |
| `/checkpoints/stats` | GET | Get checkpoint statistics | `CheckpointService` | — |
| `/checkpoints/batch/approve` | POST | Batch approve multiple checkpoints | `CheckpointService` | — |
| `/checkpoints/batch/reject` | POST | Batch reject multiple checkpoints | `CheckpointService` | — |
| `/checkpoints/{checkpoint_id}/timeout` | POST | Set custom timeout for checkpoint | `CheckpointService` | — |

**Dependencies**: `src.domain.checkpoints` (CheckpointService, CheckpointStatus, CheckpointType)

**Issues Found**:
1. **In-memory state**: CheckpointService stores state in-memory. Lost on restart.
2. **Batch operations**: Batch approve/reject iterate one-by-one with individual error handling — acceptable but not optimized.

---

### claude_sdk/
**Files**: 9 files, 3,117 LOC
**Endpoints**: ~40 endpoints (across 7 route files)
**Sprint Reference**: Phase 12, Sprints 48-51 (Features E3, E4)
**Assessment**: COMPLETE

#### claude_sdk/__init__.py (109 LOC)
Aggregates all 7 sub-routers under prefix `/claude-sdk`:
- `routes.py` → core SDK endpoints
- `autonomous_routes.py` → autonomous execution
- `hooks_routes.py` → hook lifecycle management
- `hybrid_routes.py` → hybrid orchestration
- `intent_routes.py` → intent classification
- `mcp_routes.py` → MCP server management
- `tools_routes.py` → tool management

#### claude_sdk/routes.py (224 LOC) — Core SDK

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/claude-sdk/health` | GET | Health check | Static + env check | — |
| `/claude-sdk/query` | POST | Execute Claude SDK query | Claude API via `ClaudeSDKClient` | — |
| `/claude-sdk/conversation` | POST | Multi-turn conversation | Claude API + history | — |
| `/claude-sdk/models` | GET | List available models | Static list | Hardcoded model list |
| `/claude-sdk/usage` | GET | Get usage statistics | In-memory counter | — |
| `/claude-sdk/config` | GET | Get current configuration | `ClaudeSDKClient` config | — |

**Dependencies**: `src.integrations.claude_sdk.client` (ClaudeSDKClient)

#### claude_sdk/autonomous_routes.py (435 LOC) — Autonomous Execution

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/claude-sdk/autonomous/execute` | POST | Execute autonomous task | Claude API + tool execution | — |
| `/claude-sdk/autonomous/plan` | POST | Generate execution plan | Claude API | — |
| `/claude-sdk/autonomous/status/{task_id}` | GET | Get task status | In-memory store | — |
| `/claude-sdk/autonomous/cancel/{task_id}` | POST | Cancel running task | In-memory store | — |
| `/claude-sdk/autonomous/history` | GET | Get execution history | In-memory store | — |
| `/claude-sdk/autonomous/tools` | GET | List available tools for autonomous mode | Tool registry | — |
| `/claude-sdk/autonomous/config` | GET | Get autonomous config | Static config | — |

**Dependencies**: `src.integrations.claude_sdk.autonomous` (AutonomousExecutor)

#### claude_sdk/hooks_routes.py (403 LOC) — Hook Lifecycle

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/claude-sdk/hooks` | GET | List registered hooks | In-memory `HookManager` | — |
| `/claude-sdk/hooks/{hook_name}` | GET | Get hook details | In-memory `HookManager` | — |
| `/claude-sdk/hooks/{hook_name}/enable` | POST | Enable a hook | In-memory `HookManager` | — |
| `/claude-sdk/hooks/{hook_name}/disable` | POST | Disable a hook | In-memory `HookManager` | — |
| `/claude-sdk/hooks/stats` | GET | Hook execution statistics | In-memory counters | — |
| `/claude-sdk/hooks/config` | PUT | Update hook configuration | In-memory `HookManager` | — |

**Dependencies**: `src.integrations.claude_sdk.hooks` (HookManager, various hook types)

#### claude_sdk/hybrid_routes.py (433 LOC) — Hybrid Orchestration

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/claude-sdk/hybrid/execute` | POST | Execute task with framework selection | `HybridOrchestrator` | — |
| `/claude-sdk/hybrid/analyze` | POST | Analyze task for framework fit | `CapabilityMatcher` | — |
| `/claude-sdk/hybrid/metrics` | GET | Get hybrid execution metrics | In-memory counters | — |
| `/claude-sdk/hybrid/sync` | POST | Sync context between frameworks | `ContextSynchronizer` | — |
| `/claude-sdk/hybrid/config` | GET | Get hybrid configuration | Static config | — |

**Dependencies**:
- `src.integrations.claude_sdk.hybrid.orchestrator` (HybridOrchestrator, ExecutionContext)
- `src.integrations.claude_sdk.hybrid.types` (TaskCapability, Framework, etc.)
- `src.integrations.claude_sdk.hybrid.synchronizer` (ContextSynchronizer)
- `src.integrations.claude_sdk.hybrid.capability` (CapabilityMatcher)

#### claude_sdk/intent_routes.py (569 LOC) — Intent Classification

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/claude-sdk/intent/classify` | POST | Classify user intent → execution mode | `IntentRouter` (rule-based + LLM) | — |
| `/claude-sdk/intent/analyze-complexity` | POST | Analyze task complexity | `ComplexityAnalyzer` | — |
| `/claude-sdk/intent/detect-multi-agent` | POST | Detect multi-agent needs | `MultiAgentDetector` | — |
| `/claude-sdk/intent/classifiers` | GET | List available classifiers | `IntentRouter` registry | — |
| `/claude-sdk/intent/stats` | GET | Get classification statistics | In-memory counters | — |
| `/claude-sdk/intent/config` | PUT | Update router configuration | `IntentRouter` config | — |

**Dependencies**:
- `src.integrations.hybrid.intent.router` (IntentRouter)
- `src.integrations.hybrid.intent.classifiers.rule_based` (RuleBasedClassifier)
- `src.integrations.hybrid.intent.analyzers.complexity` (ComplexityAnalyzer)
- `src.integrations.hybrid.intent.analyzers.multi_agent` (MultiAgentDetector)

#### claude_sdk/mcp_routes.py (474 LOC) — MCP Server Management

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/claude-sdk/mcp/servers` | GET | List MCP servers | `MCPManager` | — |
| `/claude-sdk/mcp/tools` | GET | List MCP tools across servers | `MCPManager` | — |
| `/claude-sdk/mcp/connect` | POST | Connect to MCP server | `MCPManager` | — |
| `/claude-sdk/mcp/disconnect/{server_name}` | POST | Disconnect from server | `MCPManager` | — |
| `/claude-sdk/mcp/execute` | POST | Execute MCP tool | `MCPManager` | — |
| `/claude-sdk/mcp/health` | GET | MCP subsystem health | `MCPManager` | — |

**Dependencies**: `src.integrations.claude_sdk.mcp.manager` (MCPManager), `src.integrations.claude_sdk.mcp.types`, `src.integrations.claude_sdk.mcp.exceptions`

#### claude_sdk/tools_routes.py (364 LOC) — Tool Management

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/claude-sdk/tools` | GET | List available tools | `tools.registry` | — |
| `/claude-sdk/tools/{tool_name}` | GET | Get tool details | `tools.registry` | — |
| `/claude-sdk/tools/execute` | POST | Execute a tool | `tools.registry.execute_tool` | — |
| `/claude-sdk/tools/validate` | POST | Validate tool parameters | `tools.registry` | — |

**Dependencies**: `src.integrations.claude_sdk.tools.registry` (get_available_tools, get_tool_instance, execute_tool, get_tool_definitions)

**Overall claude_sdk/ Issues Found**:
1. **Global singleton pattern throughout**: All sub-modules use module-level global singletons for their managers/services.
2. **Hardcoded model list**: `routes.py` returns a static list of Claude models.
3. **In-memory task storage**: Autonomous execution task state is in-memory only.
4. **No rate limiting**: Claude API calls have no rate limiting at the API layer.

---

### code_interpreter/
**Files**: 4 files, 1,553 LOC
**Endpoints**: 11 endpoints
**Sprint Reference**: Phase 8, Sprints 37-38 (Feature A10)
**Assessment**: COMPLETE

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/code-interpreter/execute` | POST | Execute code via Azure OpenAI Code Interpreter | Azure OpenAI Responses API | Requires Azure OpenAI config |
| `/code-interpreter/analyze` | POST | Analyze task (natural language → code execution) | Azure OpenAI | — |
| `/code-interpreter/sessions` | POST | Create Code Interpreter session | Azure OpenAI Assistants API | — |
| `/code-interpreter/sessions/{session_id}` | GET | Get session details | In-memory session store | — |
| `/code-interpreter/sessions` | GET | List active sessions | In-memory session store | — |
| `/code-interpreter/sessions/{session_id}` | DELETE | Close session | In-memory session store | — |
| `/code-interpreter/files/upload` | POST | Upload file for code interpretation | Azure OpenAI Files API | — |
| `/code-interpreter/files` | GET | List uploaded files | Azure OpenAI Files API | — |
| `/code-interpreter/health` | GET | Code Interpreter health check | Azure OpenAI config check | — |
| `/code-interpreter/visualizations/types` | GET | List supported chart types | Static dict | — |
| `/code-interpreter/visualizations/{file_id}` | GET | Download generated visualization | `FileStorageService` | — |
| `/code-interpreter/visualizations/generate` | POST | Generate chart from data | `CodeInterpreterAdapter` + matplotlib | — |

**Dependencies**:
- `src.integrations.agent_framework.builders.code_interpreter` (CodeInterpreterAdapter, CodeInterpreterConfig)
- `src.integrations.agent_framework.assistant` (FileStorageService, get_file_service, ConfigurationError)
- `src.core.config` (get_settings)

**Data Flow**: API → CodeInterpreterAdapter → Azure OpenAI Responses API. Visualization: API → matplotlib code generation → CodeInterpreterAdapter execution → file output.

**Issues Found**:
1. **Azure OpenAI dependency**: Requires `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` to be configured. Returns 503 if not available.
2. **Hardcoded timeout**: `CodeInterpreterConfig(timeout=60)` in visualization.py line 274.
3. **In-memory session tracking**: Session objects stored in memory, lost on restart.

---

### concurrent/
**Files**: 5 files, 2,436 LOC
**Endpoints**: ~13 REST + WebSocket endpoints
**Sprint Reference**: Phase 2, Sprint 7; Phase 3, Sprint 14; Phase 6, Sprint 31 (Feature A5)
**Assessment**: COMPLETE

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/concurrent/execute` | POST | Execute concurrent tasks (Fork-Join pattern) | `ConcurrentAPIService` → `ConcurrentBuilderAdapter` | — |
| `/concurrent/{execution_id}/status` | GET | Get execution status | In-memory `ConcurrentAPIService` | — |
| `/concurrent/{execution_id}/branches` | GET | List all branch statuses | In-memory `ConcurrentAPIService` | — |
| `/concurrent/{execution_id}/cancel` | POST | Cancel entire execution | In-memory `ConcurrentAPIService` | — |
| `/concurrent/{execution_id}/branches/{branch_id}/cancel` | POST | Cancel specific branch | In-memory `ConcurrentAPIService` | — |
| `/concurrent/stats` | GET | Get concurrent execution statistics | In-memory counters | — |
| `/concurrent/health` | GET | Health check | Static | — |
| `/concurrent/v2/execute` | POST | Execute via adapter (V2) | `ConcurrentAPIService` | Legacy + adapter dual path |
| `/concurrent/v2/{id}/status` | GET | V2 status | `ConcurrentAPIService` | — |
| `/concurrent/v2/{id}/branches` | GET | V2 branches | `ConcurrentAPIService` | — |
| `/concurrent/v2/stats` | GET | V2 statistics | `ConcurrentAPIService` | — |
| `/concurrent/ws/{execution_id}` | WebSocket | Real-time execution updates | `ConcurrentConnectionManager` | — |
| `/concurrent/ws` | WebSocket | Global event subscription | `ConcurrentConnectionManager` | — |

**Architecture**: Three-layer design:
1. `routes.py` (1094 LOC) — HTTP endpoints
2. `adapter_service.py` (518 LOC) — `ConcurrentAPIService` bridges API to adapter
3. `websocket.py` (500 LOC) — Real-time WebSocket monitoring with `ConcurrentConnectionManager`

**Dependencies**:
- `src.integrations.agent_framework.builders` (ConcurrentBuilderAdapter, ConcurrentExecutorAdapter, ConcurrentMode, FanOutRouter, FanInAggregator, etc.)
- `src.api.v1.concurrent.adapter_service` (ConcurrentAPIService)

**Data Flow**: API → ConcurrentAPIService → ConcurrentBuilderAdapter (official MAF API) → concurrent task execution → Fan-Out/Fan-In aggregation.

**Issues Found**:
1. **Dual V1/V2 endpoints**: Both legacy and adapter-based endpoints exist. V1 may be deprecated but still active.
2. **In-memory execution tracking**: `_executions` dict in `ConcurrentAPIService` — all state lost on restart.
3. **Default task executor returns input as output**: When no custom executor registered, `task_executor` just returns `{"task_id": ..., "input": ...}` (line 350-351).
4. **WebSocket connection manager is global**: `connection_manager` is a module-level singleton.

---

### connectors/
**Files**: 3 files, 749 LOC
**Endpoints**: 9 endpoints (originally listed as 8 + connect/disconnect = 9)
**Sprint Reference**: Phase 1, Sprint 2 (Feature E1)
**Assessment**: PARTIAL (UAT test connectors only)

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/connectors/` | GET | List all registered connectors | `ConnectorRegistry` (in-memory) | — |
| `/connectors/types` | GET | List available connector types | `ConnectorRegistry` | — |
| `/connectors/health` | GET | Health check all connectors | `ConnectorRegistry` → each connector | — |
| `/connectors/{name}` | GET | Get connector details and config | `ConnectorRegistry` | — |
| `/connectors/{name}/health` | GET | Health check specific connector | Individual connector | — |
| `/connectors/{name}/execute` | POST | Execute connector operation | Individual connector `__call__` | — |
| `/connectors/{name}/connect` | POST | Connect a connector | Individual connector | — |
| `/connectors/{name}/disconnect` | POST | Disconnect a connector | Individual connector | — |
| `/connectors/{name}/config` | GET | Get connector configuration | `ConnectorRegistry` | — |

**Dependencies**:
- `src.domain.connectors` (ConnectorRegistry)
- `src.domain.connectors.base` (ConnectorConfig, ConnectorResponse, AuthType)

**Issues Found**:
1. **Hardcoded test connectors**: `_register_default_connectors()` registers 3 hardcoded test connectors (servicenow, jira, teams) with fake URLs like `https://test.service-now.com`. Comment says "For UAT purposes".
2. **Global registry singleton**: `_registry: ConnectorRegistry = None` at module level. Comment: "in production, use proper DI".
3. **No real connector implementations**: The connectors are registered with test configs but no actual API integration (the base connector handles operations abstractly).
4. **No auth for destructive operations**: Any authenticated user can connect/disconnect/execute connectors.

---

### correlation/
**Files**: 2 files, 600 LOC
**Endpoints**: 7 endpoints
**Sprint Reference**: Phase 23, Sprint 82 (Features G4, G5)
**Assessment**: STUB (Mock Data)

| Endpoint | Method | Business Logic | Data Source | Problems |
|----------|--------|---------------|-------------|----------|
| `/correlation/analyze` | POST | Analyze event correlations | **Mock data generation** | 100% fake correlations |
| `/correlation/{event_id}` | GET | Get correlations for event | **Mock data generation** | 100% fake data |
| `/correlation/graph/{event_id}` | GET | Get correlation graph | **Mock graph generation** | Fake nodes/edges |
| `/correlation/statistics` | GET | Get correlation statistics | **Mock statistics** | Hardcoded numbers |
| `/correlation/timeline/{event_id}` | GET | Get event timeline | **Mock timeline** | Fake timeline entries |
| `/correlation/patterns` | GET | Get correlation patterns | **Mock patterns** | Hardcoded patterns |
| `/correlation/health` | GET | Health check | Static response | — |

**Dependencies**: None (fully self-contained mock — no integration imports)

**Issues Found**:
1. **100% mock implementation**: Every endpoint generates fake data using `uuid4()` and hardcoded values. No connection to `src.integrations.correlation` module.
2. **No real correlation engine**: Despite the `src.integrations.correlation` module existing, these routes don't import or use it.
3. **Hardcoded mock correlations**: Functions like `_generate_mock_correlations()` create fake correlation results with random scores.
4. **Hardcoded statistics**: `/statistics` endpoint returns fixed numbers that don't reflect any real data.
5. **Self-contained schemas**: Request/response models defined inline in routes.py rather than in a separate schemas file.

---

## Cross-Cutting Concerns

### 1. Authentication Pattern

All modules in this analysis are under `protected_router` which requires JWT via `require_auth`. No module adds additional auth checks (admin/operator roles), even for destructive operations like:
- `DELETE /a2a/agents/{id}` — any user can unregister agents
- `POST /cache/clear` — any user can clear the entire cache
- `POST /connectors/{name}/execute` — any user can execute connector operations
- `POST /ag-ui/reset` — any user can reset the AG-UI bridge

### 2. Data Persistence Pattern

| Module | Primary Storage | Persistent? | Production-Ready? |
|--------|----------------|-------------|-------------------|
| agents | PostgreSQL | Yes | Yes |
| cache | Redis | Yes | Yes |
| ag_ui (core) | Claude API + In-memory | Partial | Partial |
| ag_ui (upload) | Filesystem | Yes | Yes |
| a2a | In-memory | No | No |
| audit | In-memory | No | No |
| autonomous | In-memory | No | No |
| checkpoints | In-memory | No | No |
| claude_sdk | In-memory + Claude API | Partial | Partial |
| code_interpreter | Azure OpenAI + In-memory | Partial | Partial |
| concurrent | In-memory | No | No |
| connectors | In-memory | No | No |
| correlation | Mock (no real storage) | No | No |

**Summary**: Only 2 out of 13 modules have full database persistence (agents, cache). The rest rely on in-memory state that is lost on server restart.

### 3. Global Singleton Pattern

Every module uses global module-level singletons for service instances:
- `_discovery_service`, `_message_router` (a2a)
- `_hybrid_bridge`, `_claude_client`, `_redis_client` (ag_ui)
- `_audit_logger` (audit)
- `_task_store` (autonomous)
- `_cache_service` (cache)
- `_concurrent_api_service` (concurrent)
- `_registry` (connectors)

This is acknowledged in comments ("in production, use proper DI") but remains unresolved across the codebase.

### 4. Mock Data Modules

Two modules are entirely mock/stub implementations:
- **autonomous/** — 100% mock step generation, no LLM integration
- **correlation/** — 100% mock data generation, no real correlation engine

### 5. Test Endpoints in Production

- `ag_ui/routes.py` includes 5 `/test/*` endpoints that generate mock events
- These are not gated by environment or feature flags

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| Total Python files analyzed | 46 |
| Total lines of code | 15,868 |
| Total REST endpoints | ~146 |
| WebSocket endpoints | 2 |
| Modules with DB persistence | 2 (agents, cache) |
| Modules with in-memory only | 9 |
| Modules with mock/stub data | 2 (autonomous, correlation) |
| Modules using Claude API | 3 (ag_ui, claude_sdk, code_interpreter) |
| Modules using Azure OpenAI | 1 (code_interpreter) |

### Sprint Plan Cross-Reference

| Feature ID | Feature Name | Module(s) | Status |
|-----------|-------------|-----------|--------|
| A1 | Agent CRUD + Framework Core | agents/ | COMPLETE |
| A5 | Concurrent Execution (Fork-Join) | concurrent/ | COMPLETE |
| A10 | Code Interpreter | code_interpreter/ | COMPLETE |
| B1 | Checkpoint Mechanism | checkpoints/ | COMPLETE (in-memory) |
| B2 | HITL Approval Flow | checkpoints/ | COMPLETE (in-memory) |
| E1 | ServiceNow Connector | connectors/ | PARTIAL (UAT test only) |
| E3 | Claude Agent SDK | claude_sdk/ | COMPLETE |
| E5 | AG-UI Protocol (SSE) | ag_ui/ | COMPLETE |
| E6 | A2A Protocol | a2a/ | COMPLETE (in-memory) |
| G1 | Audit Logging | audit/ | COMPLETE (in-memory, no DB) |
| G4 | Event Correlation | correlation/ | STUB (100% mock) |
| G5 | Root Cause Analysis | (not in this scope — see rootcause/) | N/A |

### Top Priority Issues

1. **No persistence for 9/13 modules**: Critical for any production deployment. All in-memory state lost on restart.
2. **correlation/ is 100% mock**: Sprint 82 deliverable has no real implementation behind the API.
3. **autonomous/ is 100% mock**: Sprint 79 deliverable is a UAT stub with no real planning engine.
4. **API key exposure in ag_ui**: Bridge status/reset endpoints expose Anthropic API key prefix.
5. **No role-based access control on destructive operations**: Cache clear, connector execute, agent unregister are all accessible to any authenticated user.
6. **Test endpoints exposed in production**: ag_ui `/test/*` endpoints should be gated.
7. **Global singleton anti-pattern**: Pervasive across all modules, acknowledged but unresolved.
