# V9 Module Deep-Dive: Domain, Infrastructure, and Core Layers

> **Scope**: All modules under `backend/src/domain/`, `backend/src/infrastructure/`, `backend/src/core/`
> **Method**: Full source reading of key files per module, public API extraction, dependency mapping
> **Date**: 2026-03-29

---

## Table of Contents

1. [Domain Modules](#1-domain-modules)
   - 1.1 [sessions/ (33 files)](#11-sessions-33-files)
   - 1.2 [orchestration/ (22 files) -- DEPRECATED](#12-orchestration-22-files----deprecated)
   - 1.3 [workflows/ (11 files)](#13-workflows-11-files)
   - 1.4 [agents/ (7 files)](#14-agents-7-files)
   - 1.5 [connectors/ (6 files)](#15-connectors-6-files)
   - 1.6 [Small Domain Modules](#16-small-domain-modules)
2. [Infrastructure Modules](#2-infrastructure-modules)
   - 2.1 [database/ (18 files)](#21-database-18-files)
   - 2.2 [storage/ (18 files)](#22-storage-18-files)
   - 2.3 [checkpoint/ (8 files)](#23-checkpoint-8-files)
   - 2.4 [Remaining Infrastructure](#24-remaining-infrastructure)
3. [Core Modules](#3-core-modules)
   - 3.1 [security/ (7 files)](#31-security-7-files)
   - 3.2 [performance/ (11 files)](#32-performance-11-files)
   - 3.3 [sandbox/ (7 files)](#33-sandbox-7-files)
   - 3.4 [logging/ + observability/ (6 files)](#34-logging--observability-6-files)
   - 3.5 [Root Config](#35-root-config)
4. [Cross-Cutting Findings](#4-cross-cutting-findings)

---

### 三層架構堆疊總覽

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        IPA Platform 三層架構                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────── Domain Layer (業務邏輯) ──────────────────────┐     │
│  │  sessions/ (33 files) ★ CRITICAL    orchestration/ (22 files) ⚠    │     │
│  │  workflows/ (11 files)              agents/ (7 files)              │     │
│  │  connectors/ (6 files)              executions/ (4 files)          │     │
│  │  tasks/ (3)  checkpoints/ (3)       chat_history/ (2)             │     │
│  │  devtools/ (2) prompts/ (2)         templates/ (3)                │     │
│  │  triggers/ (2) versioning/ (2)      files/ (3)                    │     │
│  │  learning/ (2) auth/ (3)            notifications/ (2)             │     │
│  │  audit/ (2) routing/ (2) sandbox/ (2) llm/ (2)                    │     │
│  └────────────────────────────┬────────────────────────────────────────┘     │
│                               │ depends on                                  │
│                               ↓                                             │
│  ┌───────────────────── Infrastructure Layer (基礎設施) ─────────────┐     │
│  │  database/ (18 files)       storage/ (18 files)                    │     │
│  │  checkpoint/ (8 files)      cache/ (2 files)                       │     │
│  │  messaging/ (1 file, STUB)                                         │     │
│  │                                                                    │     │
│  │  PostgreSQL ←→ SQLAlchemy   Redis ←→ aioredis                     │     │
│  │  RabbitMQ ←→ aio-pika      S3/Local ←→ storage abstraction        │     │
│  └────────────────────────────┬────────────────────────────────────────┘     │
│                               │ depends on                                  │
│                               ↓                                             │
│  ┌───────────────────── Core Layer (跨切面工具) ─────────────────────┐     │
│  │  security/ (7 files)        performance/ (11 files)                │     │
│  │  sandbox/ (7 files)         config (settings.py, constants.py)     │     │
│  │  logging/ (3 files)         observability/ (3 files)               │     │
│  │                                                                    │     │
│  │  JWT Auth │ RBAC │ Rate Limiting │ Metrics │ Profiling │ Sandbox   │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
  ★ CRITICAL = 系統核心    ⚠ DEPRECATED = 已被 integrations/hybrid 取代
```

---

## 1. Domain Modules

### 1.1 sessions/ (33 files)

**Role**: Largest domain module. Provides the Agent-Session integration layer for conversational AI -- session lifecycle, message handling, agent execution, tool approval, streaming, error recovery, and metrics.

#### Key Classes and Public API

| Class | File | Public API |
|-------|------|------------|
| `Session` | `models.py` | `activate()`, `suspend()`, `resume()`, `end()`, `add_message()`, `is_active()`, `can_accept_message()`, `get_conversation_history()`, `to_llm_messages()`, `to_dict()`, `from_dict()` |
| `Message` | `models.py` | `add_attachment()`, `add_tool_call()`, `has_pending_tool_calls()`, `to_llm_format()`, `to_dict()`, `from_dict()` |
| `ToolCall` | `models.py` | `approve()`, `reject()`, `start_execution()`, `complete()`, `fail()`, `to_dict()`, `from_dict()` |
| `SessionConfig` | `models.py` | `is_tool_allowed()`, `to_dict()`, `from_dict()` |
| `SessionService` | `service.py` | `create_session()`, `get_session()`, `activate_session()`, `suspend_session()`, `resume_session()`, `end_session()`, `list_sessions()`, `count_sessions()`, `send_message()`, `add_assistant_message()`, `get_messages()`, `get_conversation_for_llm()`, `add_tool_call()`, `approve_tool_call()`, `reject_tool_call()`, `cleanup_expired_sessions()`, `update_session_title()`, `update_session_metadata()` |
| `SessionAgentBridge` | `bridge.py` | `process_message()` -> `AsyncIterator[ExecutionEvent]`, `handle_tool_approval()`, `get_pending_approvals()`, `cancel_pending_approvals()` |
| `AgentExecutor` | `executor.py` | `execute()` -> `AsyncGenerator[ExecutionEvent]`, `execute_sync()` -> `ExecutionResult`, `get_tool_registry()`, `set_tool_registry()`, `set_mcp_client()` |
| `SessionEventPublisher` | `events.py` | `subscribe()`, `subscribe_all()`, `unsubscribe()`, `publish()`, `session_created()`, `session_activated()`, `session_ended()`, `message_sent()`, `message_received()`, `tool_call_requested()`, `error_occurred()` |
| `ExecutionEventFactory` | `events.py` | `started()`, `content()`, `content_delta()`, `tool_call()`, `tool_result()`, `approval_required()`, `approval_response()`, `error()`, `done()`, `heartbeat()` |

#### Enums

| Enum | Values |
|------|--------|
| `SessionStatus` | CREATED, ACTIVE, SUSPENDED, ENDED |
| `MessageRole` | USER, ASSISTANT, SYSTEM, TOOL |
| `AttachmentType` | IMAGE, DOCUMENT, CODE, DATA, OTHER |
| `ToolCallStatus` | PENDING, APPROVED, REJECTED, RUNNING, COMPLETED, FAILED |
| `ExecutionEventType` | CONTENT, CONTENT_DELTA, TOOL_CALL, TOOL_RESULT, APPROVAL_REQUIRED, APPROVAL_RESPONSE, STARTED, DONE, ERROR, HEARTBEAT |
| `SessionEventType` | 17 types: session lifecycle (6), message (3), tool_call (5), attachment (2), error (1) |

#### State Machine

```
┌──────────────────────────── Session 生命週期 ─────────────────────────────┐
│                                                                           │
│   CREATED ──activate()──→ ACTIVE ←──resume()──→ SUSPENDED                │
│                             │  ↑                    │                     │
│                             │  └──resume()──────────┘                     │
│                             │                                             │
│                          end()                                            │
│                             │                                             │
│                             ↓                                             │
│                           ENDED                                           │
│                                                                           │
├──────────────────────────── ToolCall 生命週期 ────────────────────────────┤
│                                                                           │
│   PENDING ──┬── approve() ──→ APPROVED ──→ RUNNING ──┬──→ COMPLETED      │
│             │                                        │                    │
│             └── reject() ───→ REJECTED               └──→ FAILED         │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

#### Dependencies

- `src.integrations.llm.protocol.LLMServiceProtocol` (executor.py)
- `src.domain.agents.tools.registry.ToolRegistry` (executor.py)
- `src.domain.sessions.repository.SessionRepository` (service.py)
- `src.domain.sessions.cache.SessionCache` (service.py)
- `src.domain.sessions.approval.ToolApprovalManager` (bridge.py)
- `src.domain.sessions.tool_handler.ToolCallHandler` (bridge.py)

#### InMemory Status

- `SessionEventPublisher`: In-memory subscriber list with `Dict[SessionEventType, List[EventHandler]]`. Global singleton via `get_event_publisher()`.
- `SessionAgentBridge._active_contexts`: In-memory `Dict[str, ProcessingContext]` for tracking active executions.

#### Notable Design

- Bridge pattern separates session management from agent execution.
- Protocol classes (`SessionServiceProtocol`, `AgentRepositoryProtocol`, `MCPClientProtocol`) enable loose coupling.
- Factory functions (`create_session_agent_bridge`, `create_agent_executor`) for dependency injection.
- Streaming simulated via chunked non-stream responses (20-char chunks with 10ms delay). Real streaming deferred to S45-2.
- Token counting is estimated (`len(text) // 4`), not actual API usage.

---

### 1.2 orchestration/ (22 files) -- DEPRECATED

**Role**: Legacy orchestration module. Partially migrated to `integrations/agent_framework/builders/`.

#### Deprecation Status

The `__init__.py` emits `DeprecationWarning` on import. Migration table:

| Old (domain/orchestration/) | New (integrations/agent_framework/) | Status |
|----|----|----|
| `groupchat/` | `builders/groupchat.py` | Migrated |
| `handoff/` | `builders/handoff.py` | Migrated |
| `collaboration/` | integrated into GroupChatBuilderAdapter | Migrated |

#### Retained Sub-modules (Still Active)

**multiturn/session_manager.py** -- `MultiTurnSessionManager`

| Method | Signature |
|--------|-----------|
| `create_session()` | `(user_id, agent_ids?, initial_context?, timeout_seconds?, max_turns?, metadata?) -> MultiTurnSession` |
| `get_session()` | `(session_id) -> Optional[MultiTurnSession]` |
| `start_session()` | `(session_id) -> Optional[MultiTurnSession]` |
| `pause_session()` | `(session_id) -> bool` |
| `resume_session()` | `(session_id) -> Optional[MultiTurnSession]` |
| `close_session()` | `(session_id, reason?) -> bool` |
| `start_turn()` | `(session_id) -> Optional[int]` |
| `add_message()` | `(session_id, role, content, sender_id?, sender_name?, metadata?) -> Optional[SessionMessage]` |
| `execute_turn()` | `(session_id, user_input, agent_handler, agent_id?) -> Optional[SessionMessage]` |
| `list_sessions()` | `(user_id?, status?, active_only?) -> List[MultiTurnSession]` |
| `cleanup_expired_sessions()` | `() -> int` |
| `start_cleanup_task()` / `stop_cleanup_task()` | Background asyncio task |

- **InMemory**: All data in `Dict[str, MultiTurnSession]` and `Dict[str, Set[str]]`. No persistence.
- **Locking**: Per-session `asyncio.Lock` for concurrent access.

**memory/in_memory.py** -- `InMemoryConversationMemoryStore`

Implements `ConversationMemoryStore` ABC with:
- `add_message()`, `get_messages()`, `get_message_count()`, `delete_messages()`
- `save_session()`, `load_session()`, `delete_session()`, `list_sessions()`, `update_session_status()`
- `save_turn()`, `get_turns()`, `get_turn()`
- `search_by_content()` -- simple case-insensitive substring search
- `get_statistics()`, `cleanup_expired_sessions()`, `archive_session()`
- `clear()` -- wipes all data

- **InMemory**: All data in `Dict[UUID, ConversationSession]`, `Dict[UUID, List[ConversationTurn]]`, `Dict[UUID, List[MessageRecord]]`.

**planning/** -- `TaskDecomposer`, `DynamicPlanner`, `AutonomousDecisionEngine`, `TrialAndErrorEngine`

**nested/** -- `NestedWorkflowManager`, `WorkflowCompositionBuilder`, `RecursivePatternHandler`, `SubWorkflowExecutor`

#### Dependencies

- `src.domain.orchestration.memory.base.ConversationMemoryStore` (ABC)
- `src.domain.orchestration.memory.models` (ConversationSession, ConversationTurn, MessageRecord, SessionStatus)

---

### 1.3 workflows/ (11 files)

**Role**: Workflow execution engine with sequential agent orchestration and state management.

#### Key Classes

**`WorkflowExecutionService`** (`service.py`)

| Method | Signature | Notes |
|--------|-----------|-------|
| `execute_workflow()` | `(workflow_id, definition, input_data, variables?, agent_configs?) -> WorkflowExecutionResult` | Routes to official or legacy path |
| `validate_workflow()` | `(definition) -> Dict[str, Any]` | Returns `{valid, errors, warnings}` |
| `add_event_handler()` | `(handler: Callable) -> None` | For status updates |
| `get_execution_state()` | `(execution_id) -> Optional[Dict]` | Official API mode only |
| `get_all_execution_states()` | `() -> Dict[UUID, Dict]` | Official API mode only |

- **Dual Mode**: `use_official_api=False` (legacy) or `True` (MAF SequentialOrchestrationAdapter).
- **Global Singletons**: `get_workflow_execution_service(use_official_api)`, `reset_workflow_execution_service()`.

**`DeadlockDetector`** (`deadlock_detector.py`)

| Method | Signature |
|--------|-----------|
| `register_waiting()` | `(task_id, waiting_for, timeout?, priority?, metadata?) -> None` |
| `unregister()` | `(task_id) -> bool` |
| `detect_deadlock()` | `() -> Optional[List[str]]` -- DFS cycle detection |
| `get_timed_out_tasks()` | `() -> List[WaitingTask]` |
| `start_monitoring()` | `(on_deadlock?, on_timeout?, on_near_timeout?) -> None` |
| `stop_monitoring()` | `() -> None` |
| `get_statistics()` | `() -> Dict[str, Any]` |

- **Algorithm**: Wait-for graph with DFS cycle detection.
- **Resolution Strategies**: CANCEL_YOUNGEST, CANCEL_OLDEST, CANCEL_ALL, CANCEL_LOWEST_PRIORITY, NOTIFY_ONLY.
- **InMemory**: `Dict[str, WaitingTask]` for waiting tasks, `List[DeadlockInfo]` for history.

**`TimeoutHandler`** -- Static utility methods for handling task/execution timeouts and deadlocks.

#### Dependencies

- `src.domain.agents.service.AgentService` / `AgentConfig`
- `src.domain.workflows.models.WorkflowDefinition` / `WorkflowNode` / `WorkflowContext` / `NodeType`
- `src.integrations.agent_framework.core.executor.WorkflowNodeExecutor`
- `src.integrations.agent_framework.core.execution.SequentialOrchestrationAdapter`
- `src.integrations.agent_framework.core.events.WorkflowStatusEventAdapter`
- `src.integrations.agent_framework.core.state_machine.EnhancedExecutionStateMachine`

---

### 1.4 agents/ (7 files)

**Role**: Agent management service wrapping Microsoft Agent Framework operations.

#### Key Classes

**`AgentService`** (`service.py`)

| Method | Signature |
|--------|-----------|
| `initialize()` | `() -> None` -- connects via AgentExecutorAdapter |
| `shutdown()` | `() -> None` |
| `run_agent_with_config()` | `(config: AgentConfig, message: str, context?) -> AgentExecutionResult` |
| `run_simple()` | `(instructions, message, tools?) -> str` |
| `test_connection()` | `() -> bool` |

- **Adapter Pattern**: All MAF API calls delegated to `AgentExecutorAdapter` (Sprint 31 migration).
- **Global Singleton**: `get_agent_service()`, `init_agent_service()`.
- **Cost Calculation**: GPT-4o pricing ($5/M input, $15/M output).

**`ToolRegistry`** (`tools/registry.py`)

| Method | Signature |
|--------|-----------|
| `register()` | `(tool: BaseTool or Callable, name?, description?) -> None` |
| `register_class()` | `(tool_class: Type[BaseTool]) -> None` |
| `unregister()` | `(name) -> bool` |
| `get()` | `(name) -> Optional[BaseTool]` |
| `get_required()` | `(name) -> BaseTool` -- raises ToolError |
| `get_all()` | `() -> Dict[str, BaseTool]` |
| `get_functions()` | `() -> List[Callable]` -- for MAF agent tool lists |
| `get_schemas()` | `() -> Dict[str, Dict]` |
| `load_builtins()` | `() -> None` -- loads HttpTool, DateTimeTool, get_weather, search_knowledge_base, calculate |

- **Global Singleton**: `get_tool_registry()` (auto-loads builtins), `reset_tool_registry()`.
- **InMemory**: `Dict[str, BaseTool]`.

#### Dependencies

- `src.core.config.get_settings`
- `src.integrations.agent_framework.builders.AgentExecutorAdapter`
- `src.domain.agents.tools.base.BaseTool` / `FunctionTool`

---

### 1.5 connectors/ (6 files)

**Role**: Enterprise connector framework for external system integration.

#### Key Classes

**`BaseConnector`** (ABC) (`base.py`)

| Abstract Method | Signature |
|-----------------|-----------|
| `connect()` | `() -> None` |
| `disconnect()` | `() -> None` |
| `execute()` | `(operation: str, **kwargs) -> ConnectorResponse` |
| `health_check()` | `() -> ConnectorResponse` |

- `__call__()` wraps `execute()` with auto-connect and error handling.
- Properties: `config`, `status`, `last_error`, `is_connected`.
- Stats: `get_stats()`, `get_info()`.

**3 Concrete Connectors**: `ServiceNowConnector`, `Dynamics365Connector`, `SharePointConnector`.

**`ConnectorRegistry`** (`registry.py`)

| Method | Signature |
|--------|-----------|
| `register()` | `(connector: BaseConnector) -> None` |
| `register_from_config()` | `(config: ConnectorConfig) -> BaseConnector` |
| `unregister()` | `(name) -> bool` |
| `get()` | `(name) -> Optional[BaseConnector]` |
| `get_by_type()` | `(connector_type) -> List[BaseConnector]` |
| `connect_all()` | `() -> Dict[str, bool]` |
| `disconnect_all()` | `() -> None` |
| `health_check_all()` | `() -> Dict[str, ConnectorResponse]` |

- Built-in types auto-registered: `servicenow`, `dynamics365`, `sharepoint`.
- **Global Singleton**: `get_default_registry()`.
- **InMemory**: `Dict[str, BaseConnector]`.

#### Supporting Types

| Type | Key Fields |
|------|------------|
| `ConnectorConfig` | name, connector_type, base_url, auth_type (6 types), credentials, timeout, retry |
| `ConnectorResponse` | success, data, error, error_code, metadata, timestamp |
| `ConnectorError` | message, connector_name, operation, error_code, retryable |
| `ConnectorStatus` | DISCONNECTED, CONNECTING, CONNECTED, ERROR, RATE_LIMITED |
| `AuthType` | NONE, API_KEY, BASIC, OAUTH2, OAUTH2_CODE, CERTIFICATE |

---

### 1.6 Small Domain Modules

| Module | Files | Key Class | Storage | Key API |
|--------|-------|-----------|---------|---------|
| **checkpoints/** | 3 | `CheckpointService` | PostgreSQL via `CheckpointRepository` | `create_checkpoint()`, `get_pending_approvals()`, `approve_checkpoint()` (DEPRECATED), `reject_checkpoint()` (DEPRECATED), `create_checkpoint_with_approval()` (bridges to `HumanApprovalExecutor`) |
| **executions/** | 2 | `ExecutionStateMachine` | InMemory (per-instance) | `start()`, `pause()`, `resume()`, `complete()`, `fail()`, `cancel()`, `update_stats()`, `to_dict()`. States: PENDING -> RUNNING -> PAUSED -> COMPLETED/FAILED/CANCELLED |
| **audit/** | 2 | `AuditLogger` | InMemory (max 10K entries, optional repository) | `log()`, `log_workflow_event()`, `log_agent_event()`, `log_checkpoint_event()`, `log_user_event()`, `log_system_event()`, `log_error()`, `query()`, `get_execution_trail()`, `export_csv()`, `export_json()`, `subscribe()`, `get_statistics()` |
| **auth/** | 3 | `AuthService` | PostgreSQL via `UserRepository` | `register()`, `authenticate()`, `get_user_from_token()`, `refresh_access_token()`, `change_password()` |
| **files/** | 3 | `FileService` | Local filesystem via `FileStorage` | File upload, validation (type/size), user isolation, metadata management |
| **sandbox/** | 2 | `SandboxProcess` | InMemory | Sandbox process data structure with status (RUNNING, TERMINATED, TIMED_OUT), resource limits |
| **learning/** | 2 | `LearningCase` / `FewShotService` | InMemory | Learning case recording, similarity-based retrieval (SequenceMatcher), few-shot prompt building, case approval workflow |
| **routing/** | 2 | `ScenarioRouter` | InMemory | Cross-scenario routing (IT_OPS, CUSTOMER_SERVICE, FINANCE, HR, SALES), execution relationship tracking |
| **notifications/** | 2 | `TeamsNotificationService` | InMemory | Microsoft Teams Adaptive Card notifications, webhook delivery with retry, notification templates |
| **prompts/** | 2 | `PromptTemplate` / `PromptTemplateService` | YAML files | YAML template loading, Jinja2 variable substitution, template categorization (IT_OPS, CUSTOMER_SERVICE, COMMON, CUSTOM) |
| **devtools/** | 2 | `ExecutionTracer` | InMemory | Event capture (workflow/executor/LLM/tool/checkpoint/error), timeline generation, statistics, event streaming |
| **chat_history/** | 2 | `ChatHistoryModels` | InMemory | Chat history data models |
| **connectors/** | 6 | See section 1.5 | InMemory | See section 1.5 |
| **versioning/** | 2 | Version control data | InMemory | Versioning for workflows/agents |
| **templates/** | 3 | Workflow templates | InMemory | Workflow template management |
| **triggers/** | 2 | Trigger definitions | InMemory | Workflow trigger management |
| **tasks/** | 3 | `TaskModels` / `TaskService` | InMemory | `__init__.py`, `models.py`, `service.py` — Task data models and service |

#### InMemory Status Summary for Small Modules

Nearly all small domain modules use **InMemory storage** (Python dicts/lists). Only `checkpoints/` and `auth/` connect to PostgreSQL via repositories. The `files/` module uses local filesystem. All others would lose data on process restart.

---

## 2. Infrastructure Modules

### 2.1 database/ (18 files)

**Role**: Async SQLAlchemy ORM with connection pooling and repository pattern.

#### Session Management (`session.py`)

| Function/Class | Signature | Notes |
|----------------|-----------|-------|
| `get_engine()` | `() -> AsyncEngine` | Singleton, pool_size=5, max_overflow=10, NullPool for testing |
| `get_session_factory()` | `() -> async_sessionmaker[AsyncSession]` | expire_on_commit=False, autoflush=False |
| `get_session()` | `() -> AsyncGenerator[AsyncSession, None]` | FastAPI `Depends()` compatible, auto-commit/rollback |
| `DatabaseSession()` | Context manager | For use outside FastAPI (scripts, background tasks) |
| `init_db()` | `() -> None` | Startup: creates engine, verifies connection |
| `close_db()` | `() -> None` | Shutdown: disposes engine |
| `reset_db()` | `() -> None` | Testing: close + recreate |

#### BaseRepository (`repositories/base.py`)

Generic `BaseRepository[ModelT]` with:

| Method | Signature | Notes |
|--------|-----------|-------|
| `create()` | `(**kwargs) -> ModelT` | flush + refresh |
| `get()` | `(id: UUID) -> Optional[ModelT]` | By primary key |
| `get_by()` | `(**kwargs) -> Optional[ModelT]` | By arbitrary fields |
| `list()` | `(page, page_size, order_by?, order_desc?, **filters) -> Tuple[List[ModelT], int]` | Paginated with total count |
| `update()` | `(id: UUID, **kwargs) -> Optional[ModelT]` | Partial update |
| `delete()` | `(id: UUID) -> bool` | |
| `exists()` | `(id: UUID) -> bool` | |
| `count()` | `(**filters) -> int` | |

#### Concrete Repositories

6 repositories: `AgentRepository`, `WorkflowRepository`, `ExecutionRepository`, `CheckpointRepository`, `UserRepository`, `WorkflowRepository` (duplicate name).

#### ORM Models

8 models in `models/`: `Base`, `Agent`, `Workflow`, `Execution`, `Checkpoint`, `Session`, `Audit`, `User`.

#### Dependencies

- `src.core.config.get_settings` (for database_url)
- `sqlalchemy.ext.asyncio` (AsyncEngine, AsyncSession, async_sessionmaker)

---

### 2.2 storage/ (18 files)

**Role**: Key-value storage abstraction with 3 backends and 6 domain-specific stores.

#### Two Storage Generations

**Sprint 119 (Protocol-based)**:
- `StorageBackend` Protocol in `protocol.py`
- `RedisStorageBackend` in `redis_backend.py`
- `InMemoryStorageBackend` in `memory_backend.py`
- Factory: `create_storage_backend(prefix, backend?)` in `factory.py`

**Sprint 110 (ABC-based)**:
- `StorageBackendABC` in `backends/base.py`
- `InMemoryBackend` in `backends/memory.py`
- `RedisBackend` in `backends/redis_backend.py`
- `PostgresBackend` in `backends/postgres_backend.py`
- Factory: `StorageFactory.create(name, backend_type?, default_ttl?, namespace?)` in `backends/factory.py`

#### StorageBackendABC (`backends/base.py`)

| Method | Signature | Notes |
|--------|-----------|-------|
| `get()` | `(key) -> Optional[Any]` | Abstract |
| `set()` | `(key, value, ttl?: timedelta) -> None` | Abstract |
| `delete()` | `(key) -> bool` | Abstract |
| `exists()` | `(key) -> bool` | Abstract |
| `keys()` | `(pattern?) -> List[str]` | Glob pattern |
| `clear()` | `() -> None` | Abstract |
| `get_many()` | `(keys) -> Dict[str, Any]` | Default: sequential get() |
| `set_many()` | `(items, ttl?) -> None` | Default: sequential set() |
| `count()` | `() -> int` | Default: len(keys("*")) |

#### StorageFactory (`backends/factory.py`)

```python
backend = await StorageFactory.create(
    name="dialog_sessions",
    backend_type="auto",   # "memory" | "redis" | "postgres" | "auto"
    default_ttl=timedelta(hours=24),
)
```

Auto-detection priority: STORAGE_BACKEND env > APP_ENV=testing -> memory > REDIS_HOST -> redis > DB_HOST -> postgres > memory.

**Production safety**: Raises `RuntimeError` if Redis/Postgres unavailable in production (no silent fallback).

#### 6 Domain Stores

| Store | File | Purpose |
|-------|------|---------|
| `ApprovalStore` | `approval_store.py` | Tool approval state |
| `AuditStore` | `audit_store.py` | Audit log persistence |
| `ConversationStateStore` | `conversation_state.py` | Dialog conversation state |
| `ExecutionStateStore` | `execution_state.py` | Workflow execution state |
| `SessionStore` | `session_store.py` | Session persistence |
| `TaskStore` | `task_store.py` | Background task state |

#### Dependencies

- `src.infrastructure.redis_client.get_redis_client`
- `src.core.config.get_settings`

---

### 2.3 checkpoint/ (8 files)

**Role**: Unified checkpoint system coordinating 4 independent checkpoint providers.

#### CheckpointProvider Protocol (`protocol.py`)

```python
@runtime_checkable
class CheckpointProvider(Protocol):
    @property
    def provider_name(self) -> str: ...
    async def save_checkpoint(self, checkpoint_id, data, metadata?) -> str: ...
    async def load_checkpoint(self, checkpoint_id) -> Optional[Dict]: ...
    async def list_checkpoints(self, session_id?, limit?) -> List[CheckpointEntry]: ...
    async def delete_checkpoint(self, checkpoint_id) -> bool: ...
```

**CheckpointEntry** dataclass: `checkpoint_id`, `provider_name`, `session_id`, `data`, `metadata`, `created_at`, `expires_at`, `is_expired()`.

#### 4 Adapter Implementations

| Adapter | File | Provider Name |
|---------|------|---------------|
| `AgentFrameworkCheckpointAdapter` | `adapters/agent_framework_adapter.py` | `"agent_framework"` |
| `DomainCheckpointAdapter` | `adapters/domain_adapter.py` | `"domain"` |
| `HybridCheckpointAdapter` | `adapters/hybrid_adapter.py` | `"hybrid"` |
| `SessionRecoveryCheckpointAdapter` | `adapters/session_recovery_adapter.py` | `"session_recovery"` |

#### UnifiedCheckpointRegistry (`unified_registry.py`)

| Method | Signature |
|--------|-----------|
| `register_provider()` | `(provider: CheckpointProvider) -> None` |
| `unregister_provider()` | `(name) -> None` |
| `list_providers()` | `() -> List[str]` |
| `save()` | `(provider_name, checkpoint_id, data, metadata?) -> str` |
| `load()` | `(provider_name, checkpoint_id) -> Optional[Dict]` |
| `delete()` | `(provider_name, checkpoint_id) -> bool` |
| `list_all()` | `(session_id?, limit?) -> Dict[str, List[CheckpointEntry]]` |
| `cleanup_expired()` | `(max_age_hours?) -> Dict[str, int]` |
| `get_stats()` | `() -> Dict[str, Any]` |

- Thread-safe: Uses `asyncio.Lock` for provider registration.
- Error resilience: Individual provider errors are logged and skipped in aggregate operations.

---

### 2.4 Remaining Infrastructure

#### cache/llm_cache.py -- `LLMCacheService`

| Method | Signature |
|--------|-----------|
| `get()` | `(model, prompt, parameters?) -> Optional[CacheEntry]` |
| `set()` | `(model, prompt, response, parameters?, ttl_seconds?, metadata?) -> bool` |
| `delete()` | `(model, prompt, parameters?) -> bool` |
| `clear()` | `(pattern?) -> int` |
| `get_stats()` | `() -> CacheStats` |
| `warm_cache()` | `(entries: List[Dict]) -> int` |

- Key generation: SHA256 of `{model, prompt, relevant_params}`.
- Key prefix: `llm_cache:`.
- Default TTL: 3600s (1 hour).
- Tracks hit/miss stats in Redis hash `llm_cache:stats`.
- `CachedAgentService` wrapper: intercepts agent calls with automatic cache check/populate.

**Dependencies**: `redis.asyncio`.

#### distributed_lock/redis_lock.py

| Class | Type | API |
|-------|------|-----|
| `RedisDistributedLock` | Redis-based | `acquire()` (async context manager), `is_locked()`, `extend(additional_time)` |
| `InMemoryLock` | asyncio.Lock fallback | `acquire()`, `is_locked()` |

- Factory: `create_distributed_lock(lock_name, timeout?, blocking_timeout?)` -- auto-selects Redis or InMemory.
- Production safety: Raises `RuntimeError` if Redis unavailable in production.
- Uses `redis-py` built-in lock with Lua scripts for atomicity.
- Auto-release timeout prevents deadlocks.

#### workers/arq_client.py -- `ARQClient`

| Method | Signature |
|--------|-----------|
| `initialize()` | `() -> bool` |
| `enqueue()` | `(function_name, *args, job_id?, timeout?, **kwargs) -> Optional[str]` |
| `get_job_status()` | `(job_id) -> Dict[str, Any]` |
| `close()` | `() -> None` |

- Graceful degradation: Falls back to direct execution if `arq` package not installed or Redis unavailable.
- Global singleton: `get_arq_client()`.

#### redis_client.py -- Centralized Redis Factory

| Function | Signature |
|----------|-----------|
| `get_redis_client()` | `() -> Optional[aioredis.Redis]` |
| `close_redis_client()` | `() -> None` |

- Module-level singleton with `ConnectionPool(max_connections=20)`.
- Returns `None` if `REDIS_HOST` not set (graceful degradation).

#### messaging/ -- STUB

Only `__init__.py` with comment `"# Messaging infrastructure"`. RabbitMQ integration NOT implemented.

---

## 3. Core Modules

### 3.1 security/ (7 files)

#### JWT (`jwt.py`)

| Function | Signature | Notes |
|----------|-----------|-------|
| `create_access_token()` | `(user_id, role, expires_delta?) -> str` | HS256, default 60 min |
| `decode_token()` | `(token) -> TokenPayload` | Raises `ValueError` on invalid/expired |
| `create_refresh_token()` | `(user_id, role, expires_delta?) -> str` | Default 7 days, `type: "refresh"` claim |

- `TokenPayload`: `sub` (user_id), `role`, `exp`, `iat`.
- Uses `python-jose[cryptography]`.
- Config: `jwt_secret_key`, `jwt_algorithm`, `jwt_access_token_expire_minutes` from Settings.

#### RBAC (`rbac.py`)

| Class | Method | Signature |
|-------|--------|-----------|
| `RBACManager` | `assign_role()` | `(user_id, role: Role) -> None` |
| | `get_role()` | `(user_id) -> Role` (default: VIEWER) |
| | `check_permission()` | `(user_id, resource, action?) -> bool` |
| | `get_permissions()` | `(user_id) -> Set[str]` |

3 Roles with default permissions:

| Role | Permissions |
|------|------------|
| `ADMIN` | `tool:*`, `api:*`, `session:*`, `admin:*` |
| `OPERATOR` | 9 specific permissions (assess_risk, search_memory, request_approval, create_task, respond_to_user, route_intent, api:chat, api:history, session:own) |
| `VIEWER` | 6 permissions (search_memory, respond_to_user, route_intent, api:chat, api:history:read, session:own:read) |

- Wildcard matching: `tool:*` matches `tool:anything`.
- **InMemory**: `Dict[str, Role]` for user-role assignments.

#### PromptGuard (`prompt_guard.py`)

3-layer defense:

| Layer | Method | Purpose |
|-------|--------|---------|
| L1: Input Filtering | `sanitize_input(user_input) -> SanitizedInput` | Detect/neutralize 15+ injection patterns (role confusion, boundary escape, data exfiltration, code injection, XSS) |
| L2: System Prompt Isolation | `wrap_user_input(user_input) -> str` | Wraps in `<user_message>...</user_message>` |
| L3: Tool Call Validation | `validate_tool_call(tool_name, tool_args, allowed_tools) -> bool` | Whitelist check, arg key safety, arg value injection check |

- Utility: `check_input()` -- detection-only mode (no modification).
- Configurable: `max_input_length` (default 4000), `custom_patterns`.

#### Other Security Files

| File | Purpose |
|------|---------|
| `password.py` | Password hashing/verification (bcrypt) |
| `audit_report.py` | Security audit report generation |
| `tool_gateway.py` | Tool execution gateway with permission checks |

---

### 3.2 performance/ (11 files)

#### CircuitBreaker (`circuit_breaker.py`)

| Method | Signature |
|--------|-----------|
| `call()` | `(func, *args, fallback?, **kwargs) -> Any` |
| `reset()` | `() -> None` |
| `get_stats()` | `() -> dict` |

States: `CLOSED -> OPEN -> HALF_OPEN -> CLOSED`

| Parameter | Default |
|-----------|---------|
| `failure_threshold` | 5 |
| `recovery_timeout` | 60.0s |
| `success_threshold` | 2 |

- Tracks: `total_calls`, `total_failures`, `total_short_circuits`, `failure_count`.
- `CircuitOpenError` raised when open and no fallback.
- Global singleton: `get_llm_circuit_breaker()` (name: `"llm_api"`).
- Thread-safe: `asyncio.Lock`.

#### Other Performance Files

| File | Purpose |
|------|---------|
| `benchmark.py` | Performance benchmarking utilities |
| `cache_optimizer.py` | Cache strategy optimization |
| `concurrent_optimizer.py` | Concurrency tuning |
| `db_optimizer.py` | Database query optimization |
| `llm_pool.py` | LLM connection pooling |
| `metric_collector.py` | Metrics collection |
| `middleware.py` | Performance monitoring middleware |
| `optimizer.py` | General optimization utilities |
| `profiler.py` | Code profiling utilities |

---

### 3.3 sandbox/ (7 files)

**Role**: Secure code execution environment with process pool management.

#### Architecture

```
SandboxOrchestrator
  |-- WorkerInfo (pool tracking)
  |-- SandboxWorker (process execution)
  |-- ProcessSandboxConfig (security settings)
  |-- IPC (inter-process communication)
```

**`SandboxOrchestrator`** (`orchestrator.py`):
- Process pool with configurable size.
- Per-user worker affinity for session continuity.
- Idle worker cleanup.
- Graceful shutdown and automatic restart on failure.

**`SandboxWorker`** (`worker.py`): Individual sandboxed process execution.

**`ProcessSandboxConfig`** (`config.py`): Security constraints (memory limits, timeout, allowed modules).

**Domain SandboxService** (`domain/sandbox/service.py`):
- `SandboxProcess` dataclass: sandbox_id, user_id, status, environment, timeout_seconds, max_memory_mb.
- `SandboxStatus`: RUNNING, TERMINATED, TIMED_OUT.

---

### 3.4 logging/ + observability/ (6 files)

**Role**: Structured logging and OpenTelemetry observability infrastructure.

#### core/logging/ (3 files)

| File | Purpose |
|------|---------|
| `filters.py` | Log filtering and formatting |
| `middleware.py` | Request/response logging middleware |
| `setup.py` | Logging configuration and initialization |

#### core/observability/ (3 files)

| File | Purpose |
|------|---------|
| `metrics.py` | OpenTelemetry metrics collection |
| `setup.py` | Observability initialization |
| `spans.py` | Distributed tracing spans |

---

### 3.5 Root Config

#### Settings (`config.py`)

`Settings(BaseSettings)` with Pydantic Settings v2:

| Section | Key Fields |
|---------|------------|
| **Application** | `app_env` (dev/staging/prod), `log_level`, `secret_key` |
| **Database** | `db_host`, `db_port`, `db_name`, `db_user`, `db_password` -> `database_url` property |
| **Redis** | `redis_host`, `redis_port`, `redis_password` -> `redis_url` property |
| **RabbitMQ** | `rabbitmq_host/port/user/password` -> `rabbitmq_url` property |
| **Azure OpenAI** | `azure_openai_endpoint`, `azure_openai_api_key`, `azure_openai_deployment_name` (default: "gpt-5.2"), `azure_openai_api_version` |
| **LLM Service** | `llm_enabled`, `llm_provider` (azure/mock), `llm_max_retries`, `llm_timeout_seconds`, `llm_cache_enabled/ttl` |
| **JWT** | `jwt_secret_key`, `jwt_algorithm` (HS256), `jwt_access_token_expire_minutes` (60) |
| **CORS** | `cors_origins` -> `cors_origins_list` property |
| **Feature Flags** | `feature_workflow_enabled`, `feature_agent_enabled`, `feature_checkpoint_enabled` |
| **Observability** | `otel_enabled`, `otel_service_name`, `otel_exporter_otlp_endpoint`, `otel_sampling_rate`, `applicationinsights_connection_string` |
| **Logging** | `structured_logging_enabled` |

- Source: `.env` file + environment variables (case-insensitive, extra="ignore").
- Cached via `@lru_cache()` in `get_settings()`.
- `validate_security_settings()`: Warns on unsafe defaults in dev, raises in production.

#### Other Root Files

| File | Purpose |
|------|---------|
| `auth.py` | FastAPI auth dependencies (get_current_user, require_role) |
| `factories.py` | Service factory functions |
| `server_config.py` | Server configuration utilities |
| `sandbox_config.py` | Sandbox configuration utilities |

---

## 4. Cross-Cutting Findings

### 4.1 InMemory Storage Prevalence

The following components use **in-memory storage only** and will lose data on process restart:

| Component | Data at Risk |
|-----------|-------------|
| `MultiTurnSessionManager` | All multi-turn sessions |
| `InMemoryConversationMemoryStore` | Conversation history |
| `SessionEventPublisher` | Event subscriptions |
| `SessionAgentBridge._active_contexts` | Active execution contexts |
| `ExecutionStateMachine` | Per-instance execution state |
| `AuditLogger` (default) | Up to 10K audit entries |
| `ToolRegistry` | Registered tools (rebuilt on startup) |
| `ConnectorRegistry` | Registered connectors |
| `DeadlockDetector` | Waiting tasks, deadlock history |
| `RBACManager` | User-role assignments |
| `LearningCase` store | Few-shot learning cases |
| `ScenarioRouter` | Routing rules, relationships |
| `ExecutionTracer` | Trace events |

**Mitigation**: The Sprint 110/119 `StorageFactory` provides Redis/Postgres backends with auto-detection, but most domain modules do not use it yet.

### 4.2 Singleton Pattern Usage

Almost every service uses a module-level singleton with `get_*()` factory + `reset_*()` for testing:

| Singleton | Factory Function |
|-----------|-----------------|
| `AgentService` | `get_agent_service()` |
| `ToolRegistry` | `get_tool_registry()` |
| `WorkflowExecutionService` | `get_workflow_execution_service()` |
| `DeadlockDetector` | `get_deadlock_detector()` |
| `SessionEventPublisher` | `get_event_publisher()` |
| `ConnectorRegistry` | `get_default_registry()` |
| `ARQClient` | `get_arq_client()` |
| `Redis Client` | `get_redis_client()` |
| `CircuitBreaker` | `get_llm_circuit_breaker()` |
| `Settings` | `get_settings()` (lru_cache) |

### 4.3 Dual API Mode (Legacy vs Official MAF)

`WorkflowExecutionService` supports both legacy and official Microsoft Agent Framework API via `use_official_api` flag. The official path uses `SequentialOrchestrationAdapter`, `EnhancedExecutionStateMachine`, and `WorkflowStatusEventAdapter`.

### 4.4 Deprecation Map

| Deprecated | Replacement | Status |
|------------|-------------|--------|
| `domain/orchestration/groupchat/` | `integrations/agent_framework/builders/groupchat.py` | Migrated |
| `domain/orchestration/handoff/` | `integrations/agent_framework/builders/handoff.py` | Migrated |
| `CheckpointService.approve_checkpoint()` | `HumanApprovalExecutor` | Emits DeprecationWarning |
| `CheckpointService.reject_checkpoint()` | `HumanApprovalExecutor` | Emits DeprecationWarning |

### 4.5 Error Handling Patterns

- Domain services define custom exception hierarchies (e.g., `SessionServiceError` -> `SessionNotFoundError`, `SessionExpiredError`).
- `ConnectorError` includes `retryable` flag and `to_response()` conversion.
- `CircuitOpenError` for circuit breaker rejections.
- `InvalidStateTransitionError` for state machine violations.
- Bridge layer wraps all errors as `ExecutionEvent(ERROR)` for SSE/WebSocket delivery.

### 4.6 Protocol/ABC Usage

| Protocol/ABC | Location | Implementors |
|--------------|----------|------------|
| `SessionServiceProtocol` | `sessions/bridge.py` | `SessionService` |
| `AgentRepositoryProtocol` | `sessions/bridge.py` | Agent repositories |
| `MCPClientProtocol` | `sessions/executor.py` | MCP client implementations |
| `LLMServiceProtocol` | `integrations/llm/protocol.py` | Azure OpenAI, Mock LLM |
| `CheckpointProvider` | `infrastructure/checkpoint/protocol.py` | 4 adapters |
| `StorageBackendABC` | `infrastructure/storage/backends/base.py` | InMemory, Redis, Postgres |
| `StorageBackend` (Protocol) | `infrastructure/storage/protocol.py` | Redis, InMemory (Sprint 119) |
| `DistributedLock` (Protocol) | `infrastructure/distributed_lock/redis_lock.py` | RedisDistributedLock, InMemoryLock |
| `BaseConnector` (ABC) | `domain/connectors/base.py` | ServiceNow, Dynamics365, SharePoint |
| `ConversationMemoryStore` (ABC) | `domain/orchestration/memory/base.py` | InMemoryConversationMemoryStore, PostgresStore, RedisStore |
| `BaseTool` (ABC) | `domain/agents/tools/base.py` | HttpTool, DateTimeTool, FunctionTool |

---

*End of Module Deep-Dive Analysis*
