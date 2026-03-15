# Phase 3B: Domain Layer Analysis (Part 1)

> **Scope**: `backend/src/domain/` — agents/, audit/, auth/, checkpoints/, connectors/, devtools/, executions/, files/
> **Agent**: B1
> **Date**: 2026-03-15
> **Total Files**: 28 Python files
> **Total LOC**: ~8,654 lines

---

## Summary

| Module | Files | LOC | Classes | Assessment |
|--------|-------|-----|---------|------------|
| agents/ | 7 | 1,904 | 10 | COMPLETE |
| audit/ | 2 | 758 | 6 | COMPLETE |
| auth/ | 3 | 350 | 7 | COMPLETE |
| checkpoints/ | 3 | 1,017 | 5 | COMPLETE |
| connectors/ | 6 | 3,680 | 10 | COMPLETE |
| devtools/ | 2 | 801 | 7 | COMPLETE |
| executions/ | 2 | 465 | 3 | COMPLETE |
| files/ | 3 | 554 | 4 | COMPLETE |

---

## domain/agents/

**Files**: 7 files, 1,904 LOC
**Sprint Reference**: Sprint 1 (Core Engine), Sprint 31 (AgentExecutorAdapter Migration)
**Classes**: AgentConfig, AgentExecutionResult, AgentService, AgentCreateRequest, AgentUpdateRequest, AgentResponse, AgentListResponse, AgentRunRequest, AgentRunResponse, ToolResult, ToolError, BaseTool, FunctionTool, HttpTool, DateTimeTool, ToolRegistry

### File Inventory

| File | LOC | Purpose |
|------|-----|---------|
| `__init__.py` | 29 | Module exports |
| `schemas.py` | 157 | Pydantic request/response schemas |
| `service.py` | 342 | AgentService - core agent operations via adapter pattern |
| `tools/__init__.py` | 63 | Tools sub-module exports |
| `tools/base.py` | 383 | BaseTool ABC, FunctionTool wrapper, @tool decorator |
| `tools/builtin.py` | 558 | HttpTool, DateTimeTool, get_weather, search_knowledge_base, calculate |
| `tools/registry.py` | 377 | ToolRegistry singleton for tool management |

### Class.Method Detail

| Class.Method | Business Logic | Persistence | Status |
|-------------|---------------|-------------|--------|
| `AgentConfig` (dataclass) | Agent configuration: name, instructions, tools, model_config, max_iterations | N/A | COMPLETE |
| `AgentExecutionResult` (dataclass) | Execution result: text, llm_calls, llm_tokens, llm_cost, tool_calls | N/A | COMPLETE |
| `AgentService.__init__` | Gets settings, initializes adapter reference | None | COMPLETE |
| `AgentService.initialize` | Initializes via AgentExecutorAdapter (Sprint 31 migration) | None | COMPLETE |
| `AgentService.shutdown` | Shuts down adapter, clears references | None | COMPLETE |
| `AgentService.run_agent_with_config` | Converts AgentConfig to AdapterConfig, executes via adapter, returns mock if no adapter | None (delegates to adapter) | COMPLETE |
| `AgentService.run_simple` | Convenience wrapper around run_agent_with_config | None | COMPLETE |
| `AgentService.test_connection` | Tests Azure OpenAI connection via adapter | None | COMPLETE |
| `AgentService._calculate_cost` | GPT-4o pricing: $5/M input, $15/M output tokens | None | COMPLETE |
| `get_agent_service` | Singleton factory for AgentService | Global variable | COMPLETE |
| `init_agent_service` | Initialize and return global AgentService | Global variable | COMPLETE |
| `BaseTool.execute` | Abstract method for tool execution | None | COMPLETE (ABC) |
| `BaseTool.__call__` | Error-safe wrapper around execute | None | COMPLETE |
| `BaseTool.as_function` | Converts tool to callable for Agent Framework | None | COMPLETE |
| `BaseTool.get_schema` | Auto-generates JSON Schema from method signature | None | COMPLETE |
| `FunctionTool.execute` | Executes wrapped sync/async function | None | COMPLETE |
| `HttpTool.execute` | HTTP GET/POST/PUT/DELETE via httpx with timeout/error handling | None | COMPLETE |
| `DateTimeTool.execute` | now/format/convert operations with timezone support | None | COMPLETE |
| `get_weather` | Mock weather data (demo only) | None | MOCK |
| `search_knowledge_base` | Mock knowledge search (demo only) | None | MOCK |
| `calculate` | Basic math: add/subtract/multiply/divide | None | COMPLETE |
| `ToolRegistry.register` | Register BaseTool instance or callable function | In-memory dict | COMPLETE |
| `ToolRegistry.register_class` | Lazy instantiation registration | In-memory dict | COMPLETE |
| `ToolRegistry.get` / `get_required` | Retrieve tool by name | In-memory dict | COMPLETE |
| `ToolRegistry.get_functions` | Get all tools as callables for agent framework | In-memory dict | COMPLETE |
| `ToolRegistry.load_builtins` | Loads HttpTool, DateTimeTool, get_weather, search_knowledge_base, calculate | In-memory dict | COMPLETE |
| `get_tool_registry` | Singleton factory with auto-load builtins | Global variable | COMPLETE |

### Data Models (Pydantic)

| Model | Fields | Validation |
|-------|--------|------------|
| `AgentCreateRequest` | name (1-255), description, instructions (min 1), category (max 100), tools[], model_config_data{}, max_iterations (1-100) | Field constraints |
| `AgentUpdateRequest` | All optional; status pattern: active\|inactive\|deprecated | Regex pattern |
| `AgentResponse` | id (UUID), name, description, instructions, category, tools[], model_config_data{}, max_iterations, status, version, created_at, updated_at | from_attributes=True |
| `AgentListResponse` | items[], total, page, page_size | Pagination |
| `AgentRunRequest` | message (min 1), context{}, tools_override[] | Field constraints |
| `AgentRunResponse` | result, stats{}, tool_calls[] | None |

### Persistence

- **In-memory**: ToolRegistry uses dict-based storage (singleton pattern)
- **No direct DB**: AgentService delegates all persistence to AgentExecutorAdapter in integrations layer
- **Singleton pattern**: Both AgentService and ToolRegistry use global singleton with factory functions

### Dependencies

- `src.core.config.get_settings` — Application settings
- `src.integrations.agent_framework.builders` — AgentExecutorAdapter, AgentExecutorConfig, AgentExecutorResult
- `httpx` — HTTP client (for HttpTool)
- `pydantic` — Schema validation

### Issues Found

1. **Mock tools**: `get_weather` and `search_knowledge_base` are mock implementations returning hardcoded data — acceptable for demo but noted
2. **No DB persistence for agents**: Agent CRUD operations are not in this service; this is purely an execution service. Agent persistence is handled elsewhere (infrastructure layer)
3. **Password complexity**: Comment "Add more complexity rules as needed" in auth schemas — only length>=8 is enforced

### Assessment: COMPLETE

Well-structured module with clean separation. Sprint 31 migration to adapter pattern is properly implemented. Tool framework is extensible with both class-based and decorator-based patterns.

---

## domain/audit/

**Files**: 2 files, 758 LOC
**Sprint Reference**: Sprint 3 (Integration & Reliability)
**Classes**: AuditAction (Enum), AuditResource (Enum), AuditSeverity (Enum), AuditEntry (dataclass), AuditQueryParams (dataclass), AuditError, AuditLogger

### File Inventory

| File | LOC | Purpose |
|------|-----|---------|
| `__init__.py` | 30 | Module exports |
| `logger.py` | 728 | Complete audit logging system |

### Class.Method Detail

| Class.Method | Business Logic | Persistence | Status |
|-------------|---------------|-------------|--------|
| `AuditAction` (Enum) | 20 action types: workflow CRUD, execution lifecycle, checkpoint events, agent events, user auth, config changes, webhook/notification | N/A | COMPLETE |
| `AuditResource` (Enum) | 9 resource types: workflow, agent, execution, checkpoint, user, system, webhook, notification, template | N/A | COMPLETE |
| `AuditSeverity` (Enum) | 4 levels: info, warning, error, critical | N/A | COMPLETE |
| `AuditEntry` (dataclass) | Fields: id, action, resource, resource_id, actor_id, actor_name, timestamp, severity, details{}, ip_address, user_agent, execution_id, workflow_id | N/A | COMPLETE |
| `AuditEntry.to_dict` | Serializes to dictionary | N/A | COMPLETE |
| `AuditEntry.from_dict` | Deserializes from dictionary (classmethod) | N/A | COMPLETE |
| `AuditQueryParams` (dataclass) | Query filters: resource, action, actor_id, severity, start_date, end_date, resource_id, execution_id, limit, offset | N/A | COMPLETE |
| `AuditLogger.__init__` | Initializes with max_entries limit and in-memory list | In-memory list | COMPLETE |
| `AuditLogger.log` | Core logging method — creates AuditEntry, stores, notifies subscribers | In-memory list | COMPLETE |
| `AuditLogger.log_workflow_event` | Convenience for workflow-related audit entries | In-memory list | COMPLETE |
| `AuditLogger.log_agent_event` | Convenience for agent-related audit entries | In-memory list | COMPLETE |
| `AuditLogger.log_checkpoint_event` | Convenience for checkpoint-related audit entries | In-memory list | COMPLETE |
| `AuditLogger.log_user_event` | Convenience for user-related audit entries | In-memory list | COMPLETE |
| `AuditLogger.log_system_event` | Convenience for system-related audit entries | In-memory list | COMPLETE |
| `AuditLogger.log_error` | Logs error-severity entries with exception details | In-memory list | COMPLETE |
| `AuditLogger.query` | Filters entries by AuditQueryParams (resource, action, severity, date range, etc.) | In-memory list | COMPLETE |
| `AuditLogger.get_entry` | Retrieve single entry by UUID | In-memory list | COMPLETE |
| `AuditLogger.get_execution_trail` | Get ordered audit trail for a specific execution | In-memory list | COMPLETE |
| `AuditLogger.count` | Count entries matching query params | In-memory list | COMPLETE |
| `AuditLogger.export_csv` | Export filtered entries to CSV string | In-memory list | COMPLETE |
| `AuditLogger.export_json` | Export filtered entries to JSON string | In-memory list | COMPLETE |
| `AuditLogger.subscribe` | Register callback for real-time audit notifications | Callback list | COMPLETE |
| `AuditLogger.unsubscribe` | Remove callback | Callback list | COMPLETE |
| `AuditLogger.get_statistics` | Aggregate stats by action type, resource type, severity, hourly distribution | In-memory list | COMPLETE |
| `AuditLogger._store_entry` | Internal: appends to list, enforces max_entries (FIFO eviction) | In-memory list | COMPLETE |
| `AuditLogger._notify_subscribers` | Internal: calls registered callbacks | Callback list | COMPLETE |
| `AuditLogger.clear` | Remove all entries | In-memory list | COMPLETE |
| `AuditLogger.get_entry_count` | Return count of stored entries | In-memory list | COMPLETE |

### Persistence

- **In-memory only**: All audit entries stored in a Python list with max_entries limit (FIFO eviction)
- **No database persistence**: Entries are lost on restart
- **Export capability**: CSV and JSON export available for external persistence

### Dependencies

- Standard library only: `csv`, `io`, `logging`, `dataclasses`, `datetime`, `enum`, `typing`, `uuid`

### Issues Found

1. **In-memory only storage**: Audit logs are stored in-memory with FIFO eviction — entries lost on restart. For a compliance-critical audit system, this should persist to database
2. **No integration with database**: Despite the infrastructure layer having database capabilities, audit entries are not persisted to PostgreSQL
3. **Max entries limit**: Oldest entries silently evicted when limit reached — no warning or archival mechanism

### Assessment: COMPLETE (functionally complete but architecture concern)

The audit logger is feature-rich with querying, filtering, export, statistics, and pub/sub. However, the in-memory-only storage is a significant architectural concern for a production audit system.

---

## domain/auth/

**Files**: 3 files, 350 LOC
**Sprint Reference**: Sprint 70 (Phase 18: Authentication System)
**Classes**: AuthService, UserCreate, UserLogin, UserResponse, TokenResponse, TokenRefresh, PasswordChange, PasswordChangeResponse

### File Inventory

| File | LOC | Purpose |
|------|-----|---------|
| `__init__.py` | 30 | Module exports |
| `schemas.py` | 81 | Pydantic schemas for auth API |
| `service.py` | 239 | AuthService with registration, login, token management |

### Class.Method Detail

| Class.Method | Business Logic | Persistence | Status |
|-------------|---------------|-------------|--------|
| `AuthService.__init__` | Accepts UserRepository dependency | Repository pattern | COMPLETE |
| `AuthService.register` | Email uniqueness check, password hashing, user creation, token generation | Real DB via UserRepository | COMPLETE |
| `AuthService.authenticate` | Email lookup, password verification, last_login update, token pair generation | Real DB via UserRepository | COMPLETE |
| `AuthService.get_user_from_token` | JWT decode, user lookup by subject, active status check | Real DB via UserRepository | COMPLETE |
| `AuthService.refresh_access_token` | Refresh token decode, user lookup, new token pair generation | Real DB via UserRepository | COMPLETE |
| `AuthService.change_password` | Current password verification, new password hashing, update | Real DB via UserRepository | COMPLETE |

### Data Models (Pydantic)

| Model | Fields | Validation |
|-------|--------|------------|
| `UserCreate` | email (EmailStr), password (min 8), full_name (max 255) | field_validator for password complexity |
| `UserLogin` | email (EmailStr), password | Standard |
| `UserResponse` | id, email, full_name, role, is_active, created_at, last_login | from_attributes=True |
| `TokenResponse` | access_token, token_type ("bearer"), expires_in (3600), refresh_token | Standard |
| `TokenRefresh` | refresh_token | Standard |
| `PasswordChange` | current_password, new_password (min 8) | Standard |
| `PasswordChangeResponse` | message, changed_at | Standard |

### Business Rules

1. **Email uniqueness**: Enforced at service level before creation
2. **Password hashing**: Uses `src.core.security.hash_password` / `verify_password`
3. **JWT tokens**: Access + refresh token pair, created via `src.core.security.jwt`
4. **Active user check**: Token validation verifies user is active
5. **Last login tracking**: Updated on successful authentication

### Persistence

- **Real DB**: Uses `UserRepository` from infrastructure layer
- **SQLAlchemy model**: `User` from `src.infrastructure.database.models.user`

### Dependencies

- `src.core.security` — hash_password, verify_password, create_access_token, decode_token
- `src.core.security.jwt` — create_refresh_token
- `src.infrastructure.database.models.user` — User model
- `src.infrastructure.database.repositories.user` — UserRepository
- `pydantic` — Schema validation with EmailStr

### Issues Found

1. **Password complexity**: Only length >= 8 enforced; comment says "Add more complexity rules as needed" — no uppercase/number/special char requirements
2. **No rate limiting**: No brute-force protection at service level
3. **No account lockout**: No mechanism to lock account after failed attempts

### Assessment: COMPLETE

Solid authentication service with proper patterns: dependency injection, password hashing, JWT tokens, repository pattern. Minor gaps in password complexity and brute-force protection.

---

## domain/checkpoints/

**Files**: 3 files, 1,017 LOC
**Sprint Reference**: Sprint 2 (Workflow & Checkpoints), Sprint 28 (Official API Migration)
**Classes**: CheckpointStatus (Enum), CheckpointData (dataclass), CheckpointService, CheckpointStorage (ABC), DatabaseCheckpointStorage

### File Inventory

| File | LOC | Purpose |
|------|-----|---------|
| `__init__.py` | 41 | Module exports |
| `service.py` | 676 | CheckpointService with approval workflow |
| `storage.py` | 300 | Abstract storage + PostgreSQL implementation |

### Class.Method Detail

| Class.Method | Business Logic | Persistence | Status |
|-------------|---------------|-------------|--------|
| `CheckpointStatus` (Enum) | 4 states: PENDING, APPROVED, REJECTED, EXPIRED | N/A | COMPLETE |
| `CheckpointData` (dataclass) | Fields: id, execution_id, name, status, description, required_role, response, responded_by, responded_at, created_at, expires_at, metadata{} | N/A | COMPLETE |
| `CheckpointData.from_model` | Converts DB model to dataclass | N/A | COMPLETE |
| `CheckpointData.to_dict` | Serializes to dictionary | N/A | COMPLETE |
| `CheckpointService.__init__` | Accepts repository, optional timeout config, optional callbacks | Repository pattern | COMPLETE |
| `CheckpointService.create_checkpoint` | Creates checkpoint with execution_id, name, optional timeout, optional required_role | Real DB via CheckpointRepository | COMPLETE |
| `CheckpointService.get_checkpoint` | Retrieve by ID | Real DB | COMPLETE |
| `CheckpointService.get_pending_approvals` | List pending checkpoints with optional execution_id filter | Real DB | COMPLETE |
| `CheckpointService.get_checkpoints_by_execution` | List all checkpoints for an execution | Real DB | COMPLETE |
| `CheckpointService.approve_checkpoint` | **DEPRECATED** — emits deprecation warning, use HumanApprovalExecutor | Real DB | DEPRECATED |
| `CheckpointService.reject_checkpoint` | **DEPRECATED** — emits deprecation warning, use HumanApprovalExecutor | Real DB | DEPRECATED |
| `CheckpointService.expire_old_checkpoints` | Batch expire past-due pending checkpoints | Real DB | COMPLETE |
| `CheckpointService.get_stats` | Checkpoint statistics (counts by status) | Real DB | COMPLETE |
| `CheckpointService.delete_checkpoint` | Remove checkpoint by ID | Real DB | COMPLETE |
| `CheckpointService.set_approval_executor` | Set HumanApprovalExecutor reference | In-memory ref | COMPLETE |
| `CheckpointService.get_approval_executor` | Get HumanApprovalExecutor reference | In-memory ref | COMPLETE |
| `CheckpointService.create_checkpoint_with_approval` | Creates checkpoint AND approval request via HumanApprovalExecutor | Real DB + Adapter | COMPLETE |
| `CheckpointService.handle_approval_response` | Processes approval/rejection response via HumanApprovalExecutor | Real DB + Adapter | COMPLETE |
| `CheckpointStorage` (ABC) | Abstract: save_checkpoint, load_checkpoint, list_checkpoints, delete_checkpoint | Abstract | COMPLETE |
| `DatabaseCheckpointStorage.__init__` | Wraps CheckpointRepository | Repository pattern | COMPLETE |
| `DatabaseCheckpointStorage.save_checkpoint` | Saves state as JSON to DB | Real DB via CheckpointRepository | COMPLETE |
| `DatabaseCheckpointStorage.load_checkpoint` | Loads and deserializes checkpoint state | Real DB | COMPLETE |
| `DatabaseCheckpointStorage.list_checkpoints` | Lists checkpoints for execution, optional status filter | Real DB | COMPLETE |
| `DatabaseCheckpointStorage.delete_checkpoint` | Removes checkpoint from DB | Real DB | COMPLETE |
| `DatabaseCheckpointStorage.update_checkpoint_status` | Updates status with response data | Real DB | COMPLETE |

### State Transitions

```
PENDING -> APPROVED (human approved)
PENDING -> REJECTED (human rejected)
PENDING -> EXPIRED (timeout reached)
```

### Persistence

- **Real DB**: CheckpointRepository + DatabaseCheckpointStorage backed by PostgreSQL
- **SQLAlchemy model**: `Checkpoint` from `src.infrastructure.database.models.checkpoint`
- **JSON serialization**: State data stored as JSON in checkpoint records

### Dependencies

- `src.infrastructure.database.repositories.checkpoint` — CheckpointRepository
- `src.infrastructure.database.models.checkpoint` — Checkpoint model
- `src.integrations.agent_framework.core.approval` — HumanApprovalExecutor (TYPE_CHECKING only)

### Issues Found

1. **Deprecation in progress**: `approve_checkpoint` and `reject_checkpoint` are deprecated with warnings pointing to HumanApprovalExecutor — clean migration path but old methods still callable
2. **No notification mechanism**: Unlike the audit logger, checkpoint service has no built-in subscriber notification for approval events (though callbacks are configurable)

### Assessment: COMPLETE

Well-architected with clean separation between service, storage abstraction, and database implementation. Sprint 28 migration to HumanApprovalExecutor is properly handled with deprecation warnings.

---

## domain/connectors/

**Files**: 6 files, 3,680 LOC
**Sprint Reference**: Sprint 2 (Workflow & Checkpoints — Cross-System Integration)
**Classes**: ConnectorStatus (Enum), AuthType (Enum), ConnectorConfig (dataclass), ConnectorResponse (dataclass), ConnectorError, BaseConnector (ABC), ServiceNowConnector, Dynamics365Connector, SharePointConnector, ConnectorRegistry

### File Inventory

| File | LOC | Purpose |
|------|-----|---------|
| `__init__.py` | 57 | Module exports |
| `base.py` | 480 | Base classes: ConnectorStatus, AuthType, ConnectorConfig, ConnectorResponse, ConnectorError, BaseConnector |
| `dynamics365.py` | 920 | Dynamics 365 CRM connector (customer, contact, account, case operations) |
| `servicenow.py` | 812 | ServiceNow ITSM connector (incident, change, CMDB operations) |
| `sharepoint.py` | 970 | SharePoint connector (document, site, list operations) |
| `registry.py` | 441 | ConnectorRegistry singleton for connector management |

### Class.Method Detail — Base

| Class.Method | Business Logic | Persistence | Status |
|-------------|---------------|-------------|--------|
| `ConnectorStatus` (Enum) | 5 states: DISCONNECTED, CONNECTING, CONNECTED, ERROR, RATE_LIMITED | N/A | COMPLETE |
| `AuthType` (Enum) | 6 types: NONE, API_KEY, BASIC, OAUTH2, OAUTH2_CODE, CERTIFICATE | N/A | COMPLETE |
| `ConnectorConfig` (dataclass) | name, connector_type, base_url, auth_type, credentials{}, timeout, max_retries, custom_headers{}, metadata{} | N/A | COMPLETE |
| `ConnectorResponse` (dataclass) | success, data, error, status_code, metadata{} | N/A | COMPLETE |
| `ConnectorError` | Custom exception with message, connector_name, operation, status_code, original_error | N/A | COMPLETE |
| `BaseConnector.__init__` | Stores config, initializes status tracking and stats counters | In-memory | COMPLETE |
| `BaseConnector.connect` | Abstract — establish external connection | Abstract | COMPLETE |
| `BaseConnector.disconnect` | Abstract — close external connection | Abstract | COMPLETE |
| `BaseConnector.execute` | Abstract — execute named operation | Abstract | COMPLETE |
| `BaseConnector.health_check` | Abstract — check external system health | Abstract | COMPLETE |
| `BaseConnector.__call__` | Callable wrapper around execute with stats tracking | In-memory stats | COMPLETE |
| `BaseConnector.get_stats` | Returns call count, success/error counts, last call time | In-memory stats | COMPLETE |
| `BaseConnector.get_info` | Returns connector metadata (name, type, status, base_url) | In-memory | COMPLETE |

### Class.Method Detail — ServiceNow

| Class.Method | Business Logic | Persistence | Status |
|-------------|---------------|-------------|--------|
| `ServiceNowConnector.__init__` | Configures ServiceNow REST API client | In-memory | COMPLETE |
| `ServiceNowConnector.connect` | Authenticates via Basic/OAuth2, tests connection | External API | COMPLETE |
| `ServiceNowConnector.disconnect` | Closes HTTP client | External API | COMPLETE |
| `ServiceNowConnector.execute` | Routes to operation methods (get/list/create/update incident, change, CMDB) | External API | COMPLETE |
| `ServiceNowConnector.health_check` | Calls ServiceNow stats API | External API | COMPLETE |

### Class.Method Detail — Dynamics365

| Class.Method | Business Logic | Persistence | Status |
|-------------|---------------|-------------|--------|
| `Dynamics365Connector.__init__` | Configures D365 OData API client with Azure AD auth | In-memory | COMPLETE |
| `Dynamics365Connector.connect` | OAuth2 authentication via Azure AD | External API | COMPLETE |
| `Dynamics365Connector._authenticate` | MSAL/OAuth2 token acquisition | External API | COMPLETE |
| `Dynamics365Connector._ensure_token_valid` | Token refresh before expiry | External API | COMPLETE |
| `Dynamics365Connector.execute` | Routes: get/list/search customer/contact/account, get/list/create/update case | External API | COMPLETE |
| `Dynamics365Connector.health_check` | Tests D365 API connectivity | External API | COMPLETE |

### Class.Method Detail — SharePoint

| Class.Method | Business Logic | Persistence | Status |
|-------------|---------------|-------------|--------|
| `SharePointConnector.__init__` | Configures SharePoint Graph API client | In-memory | COMPLETE |
| `SharePointConnector.connect` | OAuth2 via Azure AD, resolves site ID | External API | COMPLETE |
| `SharePointConnector._authenticate` | MSAL token acquisition | External API | COMPLETE |
| `SharePointConnector._resolve_site_id` | Resolves SharePoint site by hostname/path | External API | COMPLETE |
| `SharePointConnector.execute` | Routes: list/get/search/download/upload document, list sites/lists/items | External API | COMPLETE |
| `SharePointConnector.health_check` | Tests Graph API connectivity | External API | COMPLETE |

### Class.Method Detail — Registry

| Class.Method | Business Logic | Persistence | Status |
|-------------|---------------|-------------|--------|
| `ConnectorRegistry.__init__` | Initializes empty registry, registers builtin types | In-memory dict | COMPLETE |
| `ConnectorRegistry._register_builtin_types` | Registers ServiceNow, Dynamics365, SharePoint classes | In-memory dict | COMPLETE |
| `ConnectorRegistry.register_type` (classmethod) | Register connector class by type name | Class-level dict | COMPLETE |
| `ConnectorRegistry.register` | Register connector instance | In-memory dict | COMPLETE |
| `ConnectorRegistry.register_from_config` | Instantiate and register from ConnectorConfig | In-memory dict | COMPLETE |
| `ConnectorRegistry.unregister` | Remove connector, disconnect if connected | In-memory dict | COMPLETE |
| `ConnectorRegistry.get` / `get_or_raise` | Retrieve connector by name | In-memory dict | COMPLETE |
| `ConnectorRegistry.get_by_type` | Filter connectors by type | In-memory dict | COMPLETE |
| `ConnectorRegistry.connect_all` | Connect all registered connectors | In-memory dict | COMPLETE |
| `ConnectorRegistry.disconnect_all` | Disconnect all connectors | In-memory dict | COMPLETE |
| `ConnectorRegistry.health_check_all` | Health check all connectors | In-memory dict | COMPLETE |
| `ConnectorRegistry.get_health_summary` | Aggregate health results into summary | In-memory dict | COMPLETE |
| `ConnectorRegistry.update_config` | Update connector config parameters | In-memory dict | COMPLETE |
| `get_default_registry` | Singleton factory | Global variable | COMPLETE |
| `reset_default_registry` | Reset singleton (for testing) | Global variable | COMPLETE |

### Persistence

- **In-memory**: Registry and connector state stored in-memory
- **External APIs**: All connectors interact with external enterprise systems (ServiceNow, D365, SharePoint)
- **No local DB**: Connector configurations not persisted to database

### Dependencies

- `httpx` — HTTP client for API calls
- Standard library: `abc`, `dataclasses`, `enum`, `typing`, `datetime`

### Issues Found

1. **No configuration persistence**: Connector configs are in-memory only; not loaded from database or config files
2. **Thread safety**: ConnectorRegistry explicitly noted as NOT thread-safe
3. **No retry logic in base**: While `max_retries` is in ConnectorConfig, retry logic implementation is left to individual connectors
4. **Credentials in memory**: OAuth tokens and credentials stored in plain connector attributes

### Assessment: COMPLETE

Comprehensive connector framework with well-designed abstraction. Three enterprise connectors (ServiceNow, Dynamics365, SharePoint) with full CRUD operations. Registry pattern provides good management. The largest module in this analysis by LOC.

---

## domain/devtools/

**Files**: 2 files, 801 LOC
**Sprint Reference**: Sprint 4 (Developer Experience — DevUI Visual Debugging)
**Classes**: TraceEventType (Enum), TraceSeverity (Enum), TraceEvent (dataclass), TraceSpan (dataclass), ExecutionTrace (dataclass), TimelineEntry (dataclass), TraceStatistics (dataclass), TracerError, ExecutionTracer

### File Inventory

| File | LOC | Purpose |
|------|-----|---------|
| `__init__.py` | 24 | Module exports |
| `tracer.py` | 777 | Complete execution tracing system |

### Class.Method Detail

| Class.Method | Business Logic | Persistence | Status |
|-------------|---------------|-------------|--------|
| `TraceEventType` (Enum) | 20 event types: workflow start/end/pause/resume, executor start/end, LLM request/response, tool call/result, checkpoint created/approved/rejected, decision, branch, loop iteration, error, warning, retry, debug, custom | N/A | COMPLETE |
| `TraceSeverity` (Enum) | 5 levels: debug, info, warning, error, critical | N/A | COMPLETE |
| `TraceEvent` (dataclass) | id, trace_id, event_type, timestamp, data{}, severity, parent_event_id, executor_id, step_number, tags[], metadata{} | N/A | COMPLETE |
| `TraceSpan` (dataclass) | id, trace_id, name, started_at, ended_at, events[], metadata{} | N/A | COMPLETE |
| `TraceSpan.duration_ms` | Calculates span duration in milliseconds | N/A | COMPLETE |
| `ExecutionTrace` (dataclass) | execution_id, started_at, ended_at, events[], spans[], metadata{} | N/A | COMPLETE |
| `ExecutionTrace.duration_ms` | Calculates trace duration in milliseconds | N/A | COMPLETE |
| `TimelineEntry` (dataclass) | timestamp, event_type, label, details, severity, duration_ms, metadata{} | N/A | COMPLETE |
| `TraceStatistics` (dataclass) | total_events, events_by_type{}, events_by_severity{}, total_duration_ms, llm_calls, tool_calls, errors, warnings | N/A | COMPLETE |
| `ExecutionTracer.__init__` | Initializes traces dict, spans dict, handlers list, subscribers list | In-memory dicts | COMPLETE |
| `ExecutionTracer.start_trace` | Creates new ExecutionTrace for execution_id | In-memory dict | COMPLETE |
| `ExecutionTracer.end_trace` | Sets ended_at timestamp on trace | In-memory dict | COMPLETE |
| `ExecutionTracer.get_trace` | Retrieve trace by execution_id | In-memory dict | COMPLETE |
| `ExecutionTracer.delete_trace` | Remove trace | In-memory dict | COMPLETE |
| `ExecutionTracer.list_traces` | List traces with optional limit/offset | In-memory dict | COMPLETE |
| `ExecutionTracer.add_event` | Add TraceEvent to trace, notify handlers/subscribers | In-memory dict | COMPLETE |
| `ExecutionTracer.get_events` | Get filtered events for a trace (by type, severity, executor) | In-memory dict | COMPLETE |
| `ExecutionTracer.start_span` | Create named span within a trace | In-memory dict | COMPLETE |
| `ExecutionTracer.end_span` | End span, calculate duration | In-memory dict | COMPLETE |
| `ExecutionTracer.get_span` | Retrieve span by ID | In-memory dict | COMPLETE |
| `ExecutionTracer.get_timeline` | Generate ordered TimelineEntry list for visualization | In-memory dict | COMPLETE |
| `ExecutionTracer._create_timeline_entry` | Convert TraceEvent to TimelineEntry | N/A | COMPLETE |
| `ExecutionTracer._get_event_label` | Human-readable label from event type | N/A | COMPLETE |
| `ExecutionTracer._get_event_details` | Extract detail string from event data | N/A | COMPLETE |
| `ExecutionTracer.get_statistics` | Calculate TraceStatistics from events | In-memory dict | COMPLETE |
| `ExecutionTracer.on_event` | Register event type handler callback | Callback list | COMPLETE |
| `ExecutionTracer.subscribe` | Register general event subscriber | Callback list | COMPLETE |
| `ExecutionTracer.unsubscribe` | Remove subscriber | Callback list | COMPLETE |
| `ExecutionTracer.clear_all` | Remove all traces and spans | In-memory dicts | COMPLETE |
| `ExecutionTracer.get_trace_count` | Count stored traces | In-memory dict | COMPLETE |

### Persistence

- **In-memory only**: All traces, events, and spans stored in Python dicts
- **No database persistence**: Traces lost on restart
- **Timeline generation**: Creates ordered timeline for DevUI visualization

### Dependencies

- Standard library only: `dataclasses`, `datetime`, `enum`, `typing`, `uuid`, `logging`

### Issues Found

1. **In-memory only**: Like audit, traces are lost on restart — acceptable for dev tools but limits production debugging
2. **No size limits**: Unlike AuditLogger (which has max_entries), ExecutionTracer has no built-in eviction policy — potential memory leak with many traces
3. **No persistence option**: No abstract storage interface like checkpoints has — making it harder to add DB persistence later

### Assessment: COMPLETE

Feature-rich execution tracing system designed for DevUI visualization. Supports events, spans, timeline generation, statistics, and pub/sub. In-memory-only design is appropriate for development tools but should have size limits.

---

## domain/executions/

**Files**: 2 files, 465 LOC
**Sprint Reference**: Sprint 1 (Core Engine)
**Classes**: ExecutionStatus (Enum), InvalidStateTransitionError, ExecutionStateMachine

### File Inventory

| File | LOC | Purpose |
|------|-----|---------|
| `__init__.py` | 37 | Module exports |
| `state_machine.py` | 428 | Execution lifecycle state machine |

### Class.Method Detail

| Class.Method | Business Logic | Persistence | Status |
|-------------|---------------|-------------|--------|
| `ExecutionStatus` (Enum) | 6 states: PENDING, RUNNING, PAUSED, COMPLETED, FAILED, CANCELLED | N/A | COMPLETE |
| `InvalidStateTransitionError` | Exception with from_status, to_status, valid_transitions | N/A | COMPLETE |
| `ExecutionStateMachine.__init__` | Initializes with execution_id, optional workflow_id, initial status PENDING | In-memory | COMPLETE |
| `ExecutionStateMachine.status` (property) | Current status getter | In-memory | COMPLETE |
| `ExecutionStateMachine.can_transition` (classmethod) | Checks if transition is valid per TRANSITIONS dict | N/A | COMPLETE |
| `ExecutionStateMachine.is_terminal` (classmethod) | Checks if status is terminal (COMPLETED, FAILED, CANCELLED) | N/A | COMPLETE |
| `ExecutionStateMachine.get_valid_transitions` (classmethod) | Returns set of valid next states | N/A | COMPLETE |
| `ExecutionStateMachine.transition` | Validates and executes state transition, records history | In-memory | COMPLETE |
| `ExecutionStateMachine._record_transition` | Records transition in history list | In-memory list | COMPLETE |
| `ExecutionStateMachine.start` | PENDING -> RUNNING, sets started_at | In-memory | COMPLETE |
| `ExecutionStateMachine.pause` | RUNNING -> PAUSED | In-memory | COMPLETE |
| `ExecutionStateMachine.resume` | PAUSED -> RUNNING | In-memory | COMPLETE |
| `ExecutionStateMachine.complete` | RUNNING -> COMPLETED, sets ended_at, records llm_calls/tokens/cost | In-memory | COMPLETE |
| `ExecutionStateMachine.fail` | RUNNING -> FAILED, sets ended_at, records error_message/error_type | In-memory | COMPLETE |
| `ExecutionStateMachine.cancel` | Any non-terminal -> CANCELLED, sets ended_at | In-memory | COMPLETE |
| `ExecutionStateMachine.update_stats` | Updates llm_calls, llm_tokens, llm_cost counters | In-memory | COMPLETE |
| `ExecutionStateMachine.get_duration_seconds` | Calculates execution duration | In-memory | COMPLETE |
| `ExecutionStateMachine.get_history` | Returns transition history list | In-memory list | COMPLETE |
| `ExecutionStateMachine.to_dict` | Serializes full state machine state | In-memory | COMPLETE |
| `create_execution_state_machine` | Factory function | N/A | COMPLETE |
| `validate_transition` | Standalone validation function (string-based) | N/A | COMPLETE |

### State Transitions

```
PENDING  -> RUNNING, CANCELLED
RUNNING  -> PAUSED, COMPLETED, FAILED, CANCELLED
PAUSED   -> RUNNING, CANCELLED
COMPLETED -> (terminal)
FAILED    -> (terminal)
CANCELLED -> (terminal)
```

### Persistence

- **In-memory only**: State machine is a pure domain object — does not persist itself
- **Designed for integration**: Expected to be used by services that handle DB persistence
- **History tracking**: Maintains transition history in-memory list

### Dependencies

- Standard library only: `logging`, `datetime`, `decimal`, `enum`, `typing`, `uuid`

### Issues Found

1. **No direct persistence**: State machine is purely in-memory; persistence is the caller's responsibility (correct pattern)
2. **Decimal import unused**: `from decimal import Decimal` imported but usage not visible in method signatures (may be used internally for cost calculations)

### Assessment: COMPLETE

Textbook state machine implementation with proper transition validation, terminal state handling, history tracking, and serialization. Clean, focused domain object.

---

## domain/files/

**Files**: 3 files, 554 LOC
**Sprint Reference**: Sprint 75 (Phase 20: File Attachment Support)
**Classes**: FileValidationError, FileService, FileStorage

### File Inventory

| File | LOC | Purpose |
|------|-----|---------|
| `__init__.py` | 13 | Module exports |
| `storage.py` | 223 | FileStorage for filesystem persistence |
| `service.py` | 318 | FileService with validation and metadata management |

### Class.Method Detail

| Class.Method | Business Logic | Persistence | Status |
|-------------|---------------|-------------|--------|
| `FileValidationError.__init__` | Custom exception with code and message | N/A | COMPLETE |
| `FileService.__init__` | Accepts optional FileStorage, defaults to global singleton | Filesystem | COMPLETE |
| `FileService.validate_file` | MIME type detection (from extension or upload), allowed type check, size limit enforcement per type | N/A | COMPLETE |
| `FileService.upload_file` | Validates file, generates ID, saves via storage, creates metadata record | Filesystem + in-memory metadata dict | COMPLETE |
| `FileService.get_file_metadata` | Retrieve FileMetadata by file_id | In-memory dict | COMPLETE |
| `FileService.get_user_files` | List files for a user with optional category/status filter, pagination | In-memory dict | COMPLETE |
| `FileService.delete_file` | User ownership check, filesystem delete, metadata removal | Filesystem + in-memory dict | COMPLETE |
| `FileService.get_file_content` | Read file bytes with user ownership check | Filesystem | COMPLETE |
| `FileService.get_file_content_text` | Read file as text with encoding parameter | Filesystem | COMPLETE |
| `FileService.get_file_base64` | Read file and encode as base64 | Filesystem | COMPLETE |
| `FileService.is_image_file` | Check if file MIME type is image/* | In-memory dict | COMPLETE |
| `FileService.is_text_file` | Check if file MIME type is text/* | In-memory dict | COMPLETE |
| `FileService.is_pdf_file` | Check if file MIME type is application/pdf | In-memory dict | COMPLETE |
| `get_file_service` | Singleton factory | Global variable | COMPLETE |
| `FileStorage.__init__` | Creates base upload directory (default: backend/data/uploads) | Filesystem | COMPLETE |
| `FileStorage.get_user_dir` | Get/create user-specific upload directory | Filesystem | COMPLETE |
| `FileStorage.generate_file_id` | UUID4 generation | N/A | COMPLETE |
| `FileStorage.get_file_extension` | Extract extension from filename | N/A | COMPLETE |
| `FileStorage.save_file` | Write bytes to user_dir/file_id.ext | Filesystem | COMPLETE |
| `FileStorage.read_file` | Read bytes from storage path | Filesystem | COMPLETE |
| `FileStorage.read_file_text` | Read text with encoding | Filesystem | COMPLETE |
| `FileStorage.delete_file` | Remove file from filesystem | Filesystem | COMPLETE |
| `FileStorage.file_exists` | Check file existence | Filesystem | COMPLETE |
| `FileStorage.get_full_path` | Resolve absolute path | Filesystem | COMPLETE |
| `FileStorage.get_file_size` | Get file size in bytes | Filesystem | COMPLETE |
| `FileStorage.cleanup_user_files` | Delete all files for a user | Filesystem | COMPLETE |
| `FileStorage.list_user_files` | List all files in user directory | Filesystem | COMPLETE |
| `get_file_storage` | Singleton factory | Global variable | COMPLETE |

### Business Rules

1. **MIME type validation**: Checks against allowed types list from schemas
2. **Size limits**: Per-MIME-type size limits (e.g., images vs documents)
3. **User isolation**: Files stored in user-specific directories (data/uploads/{user_id}/)
4. **User ownership**: File access/delete requires matching user_id

### Persistence

- **Filesystem**: Files stored on local disk at `backend/data/uploads/{user_id}/{file_id}.{ext}`
- **In-memory metadata**: `FileMetadata` stored in dict within FileService (lost on restart)
- **No DB persistence for metadata**: File metadata not stored in database

### Dependencies

- `src.api.v1.files.schemas` — FileCategory, FileMetadata, FileStatus, FileUploadResponse, MIME type utilities
- `pathlib` — Path operations
- `base64` — Base64 encoding
- `mimetypes` — MIME type detection

### Issues Found

1. **Metadata in-memory only**: FileMetadata stored in dict — lost on restart. Should persist to database
2. **Cross-layer dependency**: FileService imports from `src.api.v1.files.schemas` — domain layer importing from API layer violates clean architecture (dependency should be inverted)
3. **No virus scanning**: No malware check on uploaded files
4. **No deduplication**: Same file uploaded twice creates two copies
5. **Local filesystem only**: No cloud storage support (S3, Azure Blob, etc.)

### Assessment: COMPLETE

Functional file management with user isolation, validation, and multiple read formats. However, has a significant architecture violation (domain importing from API layer) and metadata is not persisted to database.

---

## Cross-Module Analysis

### Persistence Summary

| Module | Storage Type | DB Integration | Data Loss on Restart |
|--------|-------------|----------------|---------------------|
| agents/ | In-memory (registry), Adapter delegation | No direct DB | Yes (registry) |
| audit/ | In-memory list | No DB | **Yes (all audit data)** |
| auth/ | Real DB via Repository | Full DB | No |
| checkpoints/ | Real DB via Repository + Storage | Full DB | No |
| connectors/ | In-memory (registry + state) | No DB | Yes (configs) |
| devtools/ | In-memory dicts | No DB | Yes (all traces) |
| executions/ | In-memory (pure domain object) | No direct DB (caller's responsibility) | N/A |
| files/ | Filesystem + in-memory metadata | No DB for metadata | **Yes (metadata)** |

### Architecture Concerns

1. **Audit data loss**: In-memory audit storage is a compliance risk
2. **File metadata loss**: FileMetadata not persisted to DB
3. **Clean architecture violation**: `files/service.py` imports from `src.api.v1.files.schemas`
4. **No size limits in devtools**: ExecutionTracer can grow unbounded
5. **Thread safety**: ConnectorRegistry explicitly not thread-safe

### Sprint Cross-Reference

| Module | Sprint | Phase | Plan Reference |
|--------|--------|-------|---------------|
| agents/ | Sprint 1, Sprint 31 | Phase 1, Phase 8 | A1 |
| audit/ | Sprint 3 | Phase 1 | G1 |
| auth/ | Sprint 70 | Phase 18 | I1 |
| checkpoints/ | Sprint 2, Sprint 28 | Phase 1, Phase 7 | B1 |
| connectors/ | Sprint 2 | Phase 1 | E1 |
| devtools/ | Sprint 4 | Phase 1 | G2 |
| executions/ | Sprint 1 | Phase 1 | A4 |
| files/ | Sprint 75 | Phase 20 | Phase 20 |

### Quality Metrics

| Metric | Count |
|--------|-------|
| Total files analyzed | 28 |
| Total LOC | ~8,654 |
| Total classes | 52+ |
| Modules using real DB | 2 (auth, checkpoints) |
| Modules using in-memory only | 4 (audit, connectors, devtools, executions) |
| Modules with mixed persistence | 2 (agents, files) |
| Mock implementations | 2 (get_weather, search_knowledge_base) |
| Deprecated methods | 2 (approve_checkpoint, reject_checkpoint) |
| Architecture violations | 1 (files imports from API layer) |
| TODO/stub implementations | 0 |
| Empty methods | 0 |
