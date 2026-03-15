# Phase 3B: Domain Layer Analysis — Part 3

> **Scope**: `backend/src/domain/` — learning/, notifications/, prompts/, routing/, sandbox/, sessions/, templates/, triggers/, versioning/, workflows/
>
> **Agent**: B3 | **Date**: 2026-03-15 | **Total Files**: 55 Python files | **Total LOC**: ~14,800+

---

## Table of Contents

1. [Module Summary Matrix](#1-module-summary-matrix)
2. [learning/ Module](#2-learning-module)
3. [notifications/ Module](#3-notifications-module)
4. [prompts/ Module](#4-prompts-module)
5. [routing/ Module](#5-routing-module)
6. [sandbox/ Module](#6-sandbox-module)
7. [sessions/ Module (Critical)](#7-sessions-module-critical)
8. [templates/ Module](#8-templates-module)
9. [triggers/ Module](#9-triggers-module)
10. [versioning/ Module](#10-versioning-module)
11. [workflows/ Module](#11-workflows-module)
12. [Cross-References](#12-cross-references)
13. [Problems and Issues](#13-problems-and-issues)

---

## 1. Module Summary Matrix

| Module | Files | LOC (est.) | Key Classes | Sprint | Persistence |
|--------|-------|------------|-------------|--------|-------------|
| learning/ | 2 | ~648 | LearningService, LearningCase | S4 | In-memory dict |
| notifications/ | 2 | ~776 | TeamsNotificationService | S3 | In-memory history |
| prompts/ | 2 | ~568 | PromptTemplateManager | S3 | In-memory dict |
| routing/ | 2 | ~645 | ScenarioRouter | S3 | In-memory list |
| sandbox/ | 2 | ~345 | SandboxService | Phase 21 | In-memory dict |
| **sessions/** | **33** | **~12,272** | SessionService, AgentExecutor, SessionAgentBridge, ToolCallHandler, ToolApprovalManager, etc. | S45-S47 | SQLAlchemy + Redis |
| templates/ | 3 | ~750 | TemplateService, AgentTemplate | S4 | In-memory dict |
| triggers/ | 2 | ~550 | WebhookTriggerService | S3 | In-memory dict |
| versioning/ | 2 | ~650 | VersioningService | S4 | In-memory dict |
| workflows/ | 11 | ~2,600 | WorkflowExecutionService, DeadlockDetector, ParallelGateway | S1, S7, S27 | In-memory + callbacks |

---

## 2. learning/ Module

**Path**: `backend/src/domain/learning/`
**Files**: 2 (`__init__.py` 31 LOC, `service.py` 648 LOC)
**Sprint**: S4 (Developer Experience - Few-shot Learning)

### Classes

| Class | Type | Description |
|-------|------|-------------|
| `CaseStatus` | Enum | PENDING, APPROVED, REJECTED, ARCHIVED |
| `LearningCase` | @dataclass | Stores human correction with original/corrected output, feedback, effectiveness_score |
| `LearningStatistics` | @dataclass | Aggregate stats: total, approved, pending, rejected, by_scenario |
| `LearningError` | Exception | Base error class |
| `LearningService` | Service | Core service managing few-shot learning cases |

### LearningService Methods

| Method | Purpose |
|--------|---------|
| `record_correction()` | Records human correction with scenario, input/output pair, feedback |
| `get_case()` / `list_cases()` / `delete_case()` | CRUD operations |
| `approve_case()` / `reject_case()` / `bulk_approve()` | Case approval workflow |
| `get_similar_cases()` | Text similarity search using `SequenceMatcher` (threshold-based) |
| `build_few_shot_prompt()` | Builds enhanced prompts with similar examples (standard/chat/structured formats) |
| `record_effectiveness()` | Tracks running average effectiveness score |
| `get_statistics()` / `get_scenario_statistics()` | Aggregate metrics |
| `archive_old_cases()` | Archives cases older than N days with low usage |

### Dependencies
- `difflib.SequenceMatcher` for similarity calculation
- No external dependencies (pure Python)

### Issues
- **In-memory only**: `_cases: Dict[UUID, LearningCase]` — no database persistence
- Comment notes "Production should use embeddings" for similarity (line 388)
- `datetime.utcnow()` deprecated in Python 3.12+

---

## 3. notifications/ Module

**Path**: `backend/src/domain/notifications/`
**Files**: 2 (`__init__.py` 39 LOC, `teams.py` 776 LOC)
**Sprint**: S3 (Integration & Reliability)

### Classes

| Class | Type | Description |
|-------|------|-------------|
| `NotificationType` | Enum | 11 types: APPROVAL_REQUEST/REMINDER, EXECUTION_STARTED/COMPLETED/FAILED/CANCELLED, ERROR/WARNING/INFO_ALERT, SYSTEM_MAINTENANCE/STATUS |
| `NotificationPriority` | Enum | LOW, NORMAL, HIGH, URGENT |
| `NotificationError` | Exception | With notification_type, retry_count, original_error |
| `TeamsNotificationConfig` | @dataclass | webhook_url, retry_count(3), retry_delay(1s), timeout(10s), rate limit(30/min) |
| `NotificationResult` | @dataclass | Result with notification_id, success, retry_count, response_code |
| `TeamsCard` | @dataclass | Adaptive Card v1.4 with body/actions, `to_payload()` |
| `TeamsNotificationService` | Service | Full Teams notification service |

### TeamsNotificationService Methods

| Method | Purpose |
|--------|---------|
| `send_approval_request()` | Sends approval card with priority emoji, reviewer info |
| `send_execution_completed()` | Sends completion card with status, duration, step count |
| `send_error_alert()` | Sends error alert with severity levels |
| `send_custom_notification()` | Arbitrary Adaptive Card content |
| `_send_card()` | Core send with retry (exponential backoff), rate limiting |
| `_send_request()` | Uses httpx for actual HTTP POST |
| `get_history()` / `get_statistics()` | Notification tracking |

### Dependencies
- `httpx` (optional, imported at runtime)
- `asyncio` for retry delays

### Issues
- Rate limiting uses `datetime.utcnow()` (deprecated)
- `_check_rate_limit()` has unused variable `cutoff` (line 683)
- Card content uses Traditional Chinese UI strings (appropriate for target market)

---

## 4. prompts/ Module

**Path**: `backend/src/domain/prompts/`
**Files**: 2 (`__init__.py` 30 LOC, `template.py` 568 LOC)
**Sprint**: S3 (Integration & Reliability)

### Classes

| Class | Type | Description |
|-------|------|-------------|
| `PromptCategory` | Enum | IT_OPERATIONS, CUSTOMER_SERVICE, COMMON, CUSTOM |
| `PromptTemplate` | @dataclass | Template with `{{variable}}` syntax, auto-extraction, versioning |
| `PromptTemplateError` | Exception | Base with error code |
| `TemplateNotFoundError` | Exception | Template ID not found |
| `TemplateRenderError` | Exception | Missing variables |
| `TemplateValidationError` | Exception | Invalid template |
| `PromptTemplateManager` | Service | Load from YAML, render with variable substitution, validate |

### Key Features
- YAML file loading (`.yaml` and `.yml`)
- Variable extraction via regex `\{\{\s*(\w+)\s*\}\}`
- Strict/non-strict rendering modes
- Template validation (ID format, bracket matching)
- Template search by keyword

### Dependencies
- `yaml` (PyYAML)
- `re` for variable extraction

### Issues
- In-memory only (`_templates: Dict[str, PromptTemplate]`)
- Simple string replacement instead of Jinja2 (despite docstring mentioning Jinja2 syntax)

---

## 5. routing/ Module

**Path**: `backend/src/domain/routing/`
**Files**: 2 (`__init__.py` 43 LOC, `scenario_router.py` 645 LOC)
**Sprint**: S3 (Cross-Scenario Collaboration)

### Classes

| Class | Type | Description |
|-------|------|-------------|
| `Scenario` | Enum | IT_OPERATIONS, CUSTOMER_SERVICE, FINANCE, HR, SALES |
| `RelationType` | Enum | 8 types: ROUTED_TO/FROM, PARENT/CHILD, SIBLING, ESCALATED_TO/FROM, REFERENCES/REFERENCED_BY |
| `RoutingError` | Exception | With source/target scenario, execution_id |
| `ScenarioConfig` | @dataclass | Per-scenario config with allowed_targets, auto_route |
| `ExecutionRelation` | @dataclass | Bidirectional relationship between executions |
| `RoutingResult` | @dataclass | Routing operation outcome |
| `ScenarioRouter` | Service | Cross-scenario routing with relationship tracking |

### ScenarioRouter Methods

| Method | Purpose |
|--------|---------|
| `route_to_scenario()` | Routes execution between scenarios with validation, creates bidirectional relations |
| `get_related_executions()` | Queries relations by direction (outgoing/incoming/both) |
| `get_execution_chain()` | DFS traversal for full execution chain |
| `create_relation()` / `delete_relation()` | Manual relation management |
| `get_statistics()` | Routing stats by scenario and relation type |

### Key Design
- Default scenario configs initialized with allowed routing targets
- Execution callback for triggering target workflows
- Audit callback for logging
- Automatic reverse relation creation

### Dependencies
- `asyncio` for async execution/audit callbacks

### Issues
- In-memory storage (`_relations: List[ExecutionRelation]`)
- Mock execution in MVP (generates random UUID when no callback)
- Linear scan for relation queries (O(n))

---

## 6. sandbox/ Module

**Path**: `backend/src/domain/sandbox/`
**Files**: 2 (`__init__.py` 19 LOC, `service.py` 345 LOC)
**Sprint**: Phase 21 (Sandbox Security)

### Classes

| Class | Type | Description |
|-------|------|-------------|
| `SandboxStatus` | Enum | RUNNING, TERMINATED, TIMED_OUT |
| `IPCMessageType` | Enum | EXECUTE, ENV_CHECK, FS_CHECK, NET_CHECK |
| `SandboxProcess` | @dataclass | Process data with user_id, memory limits, uptime |
| `IPCResponse` | @dataclass | IPC response with latency, success, error |
| `SandboxService` | Service | Sandbox process management |

### Security Features

| Check | Implementation |
|-------|---------------|
| **Environment Variables** | Allowlist (ANTHROPIC_API_KEY, OPENAI_API_KEY, PATH, HOME) / Blocklist (AWS_SECRET, DB_PASSWORD, etc.) |
| **File System** | Path traversal detection (../, URL-encoded, double-encoded), sandbox boundary enforcement, symlink blocking |
| **Network** | Host allowlist (api.anthropic.com, api.openai.com, localhost) |

### Key Methods
- `create_sandbox()` — Creates with user_id, environment, timeout, memory limits
- `send_ipc_message()` — Dispatches to type-specific handlers
- `_handle_fs_check()` — Comprehensive path traversal prevention (12+ patterns)
- `get_pool_status()` / `cleanup_pool()` — Process pool management

### Issues
- Simulated, not real sandbox — `creation_time_ms=150.0` hardcoded
- No actual process isolation or container usage
- Pool counters are simplistic (increment/decrement without real process tracking)

---

## 7. sessions/ Module (Critical)

**Path**: `backend/src/domain/sessions/`
**Files**: 33 | **LOC**: ~12,272
**Sprints**: S45 (Core), S46 (Bridge), S47 (Error/Recovery/Metrics)

This is the **largest and most critical** domain module, providing the complete Agent-Session integration layer for conversational AI.

### 7.1 Architecture Overview

```
SessionAgentBridge (bridge.py)
    ├── SessionService (service.py)
    │   ├── SessionRepository (repository.py) → SQLAlchemy/PostgreSQL
    │   ├── SessionCache (cache.py) → Redis
    │   └── SessionEventPublisher (events.py)
    ├── AgentExecutor (executor.py)
    │   └── StreamingLLMHandler (streaming.py)
    ├── ToolCallHandler (tool_handler.py)
    │   └── ToolApprovalManager (approval.py)
    ├── SessionErrorHandler (error_handler.py)
    ├── SessionRecoveryManager (recovery.py)
    └── MetricsCollector (metrics.py)
```

### 7.2 Core Files

#### models.py (~560 LOC)

**Domain models for sessions**:

| Class | Type | Key Fields |
|-------|------|------------|
| `SessionStatus` | Enum | CREATED, ACTIVE, SUSPENDED (commented out in some), ENDED |
| `MessageRole` | Enum | USER, ASSISTANT, SYSTEM, TOOL |
| `AttachmentType` | Enum | IMAGE, DOCUMENT, CODE, DATA, OTHER |
| `ToolCallStatus` | Enum | PENDING, APPROVED, REJECTED, RUNNING, COMPLETED, FAILED |
| `Attachment` | @dataclass | file_name, content_type, size, url, `from_upload()` factory, `_detect_type()` |
| `ToolCall` | @dataclass | tool_name, arguments, status lifecycle: `approve()` → `start_execution()` → `complete()`/`fail()` |
| `Message` | @dataclass | role, content, attachments, tool_calls, `to_llm_format()` (handles image attachments) |
| `SessionConfig` | @dataclass | max_messages(100), max_attachments(10), max_attachment_size(10MB), timeout_minutes(60), enable_code_interpreter, enable_mcp_tools, tool whitelist/blacklist |
| `Session` | @dataclass | State machine: CREATED → ACTIVE ↔ SUSPENDED → ENDED, `is_expired()`, `can_accept_message()` |

#### service.py (~620 LOC)

**SessionService** — Session lifecycle management:

| Method | Purpose |
|--------|---------|
| `create_session()` | Creates session with config, agent_id, user_id |
| `get_session()` | Cache-first lookup with DB fallback |
| `activate_session()` | CREATED → ACTIVE transition |
| `suspend_session()` / `resume_session()` | ACTIVE ↔ SUSPENDED |
| `end_session()` | Ends session with summary |
| `send_message()` | Adds user message, validates limits, publishes events |
| `add_assistant_message()` | Adds assistant response |
| `get_conversation_for_llm()` | Formats messages for LLM API |
| `add_tool_call()` / `approve_tool_call()` / `reject_tool_call()` | Tool call lifecycle |
| `cleanup_expired_sessions()` | Batch expiration cleanup |

**Error Classes**: SessionServiceError, SessionNotFoundError, SessionExpiredError, SessionNotActiveError, MessageLimitExceededError

**Dependencies**: SessionRepository, SessionCache, SessionEventPublisher

#### repository.py (~380 LOC)

**Persistence layer**:

| Class | Description |
|-------|-------------|
| `SessionRepository` | ABC defining interface: create, get, update, delete, list_by_user, add_message, get_messages, cleanup_expired |
| `SQLAlchemySessionRepository` | Full SQLAlchemy implementation with `_to_domain()` and `_message_to_domain()` converters |

**Key Methods**: `count_by_user()`, `get_active_sessions()`, async operations throughout.

**Dependencies**: SQLAlchemy AsyncSession, infrastructure DB models

#### cache.py (~370 LOC)

**Redis caching layer** — `SessionCache`:

| Method | Purpose |
|--------|---------|
| `get_session()` / `set_session()` | Session object caching with TTL |
| `extend_session()` | Extend TTL for active sessions |
| `update_session_status()` | Partial update without full deserialization |
| `get_messages()` / `append_message()` / `clear_messages()` | Message list caching |
| `get_user_sessions()` / `set_user_sessions()` | User session list caching |
| `get_sessions_batch()` / `set_sessions_batch()` | Batch operations |
| `get_cache_stats()` / `health_check()` / `flush_all()` | Operational |

**Dependencies**: Redis (aioredis), JSON serialization

### 7.3 Execution Pipeline

#### executor.py (~660 LOC)

**AgentExecutor** — Core LLM interaction:

| Class | Description |
|-------|-------------|
| `MessageRole` | Enum: SYSTEM, USER, ASSISTANT, TOOL |
| `ChatMessage` | @dataclass with role, content, tool_calls, tool_call_id |
| `AgentConfig` | @dataclass with agent_id, name, instructions, model, temperature, max_tokens, tools, `from_agent()` factory |
| `ExecutionConfig` | @dataclass with max_iterations(10), timeout_seconds(120), enable_streaming, enable_tools |
| `ExecutionResult` | @dataclass with content, tool_calls, finish_reason, usage (prompt/completion/total tokens) |
| `MCPClientProtocol` | Protocol defining `call_tool()`, `get_available_tools()` |
| `AgentExecutor` | Main executor class |

**AgentExecutor Key Methods**:

| Method | Purpose |
|--------|---------|
| `execute()` | Main execution loop: builds messages → gets tools → calls LLM → returns result |
| `execute_sync()` | Synchronous wrapper |
| `_build_messages()` | Constructs message array from system prompt + history + current input |
| `_get_available_tools()` | Merges local tool registry + MCP tools into OpenAI-format schemas |
| `_call_llm()` | Calls LLM client with messages, tools, model config |
| `set_tool_registry()` / `set_mcp_client()` | Configurable tool sources |

**Factory**: `create_agent_executor(agent_config, llm_client, tool_registry, mcp_client, execution_config)`

#### streaming.py (~730 LOC)

**StreamingLLMHandler** — SSE streaming support:

| Class | Description |
|-------|-------------|
| `StreamState` | Enum: IDLE, STREAMING, PAUSED, COMPLETED, ERROR, CANCELLED |
| `StreamConfig` | @dataclass with timeout(120s), heartbeat_interval(15s), max_retries(3), buffer_size(100) |
| `StreamStats` | @dataclass tracking first_token_at, tokens count, duration, `time_to_first_token_ms` property |
| `ToolCallDelta` | @dataclass for incremental tool call parsing |
| `TokenCounter` | Tiktoken-based token counting (model-aware) |
| `StreamingLLMHandler` | Main streaming handler |

**StreamingLLMHandler Key Methods**:

| Method | Purpose |
|--------|---------|
| `stream()` | Main streaming loop: yields ExecutionEvents (STARTED → CONTENT_DELTA* → TOOL_CALL* → DONE) |
| `stream_simple()` | Simplified non-event streaming (yields content strings) |
| `cancel()` | Cancels in-progress stream |
| `_call_with_retry()` | Retry with exponential backoff for transient errors |
| `_heartbeat_loop()` | Periodic heartbeat during long operations |
| `_parse_tool_arguments()` | JSON parsing for incremental tool call arguments |
| `close()` | Cleanup, supports async context manager |

**Factory**: `create_streaming_handler(llm_client, config)`

### 7.4 Tool System

#### tool_handler.py (~1010 LOC)

**ToolCallHandler** — Tool execution framework:

| Class | Description |
|-------|-------------|
| `ToolSource` | Enum: LOCAL, MCP, BUILTIN |
| `ToolPermission` | Enum: ALLOWED, BLOCKED, REQUIRES_APPROVAL |
| `ToolRegistryProtocol` | Protocol: get(), get_all(), get_schemas() |
| `MCPClientProtocol` | Protocol: call_tool(), list_tools(), connected_servers |
| `ParsedToolCall` | @dataclass: id, name, arguments, source, `to_tool_call_info()` |
| `ToolExecutionResult` | @dataclass: tool_call_id, name, result, error, execution_time_ms, `to_llm_message()` |
| `ToolHandlerConfig` | @dataclass: max_rounds(5), parallel_execution(True), approval_required(False), tool whitelist/blacklist, timeout(30s) |
| `ToolHandlerStats` | @dataclass: total/success/failed counts, avg execution time |
| `ToolCallParser` | Parses tool calls from LLM responses (OpenAI format + dict format) |
| `ToolCallHandler` | Main handler |

**ToolCallHandler Key Methods**:

| Method | Purpose |
|--------|---------|
| `handle_tool_calls()` | Orchestrates: parse → check permission → execute or request approval → return results |
| `execute_tool()` | Single tool execution with timeout |
| `parse_tool_calls()` | Delegates to ToolCallParser |
| `get_available_tools()` | Merges local + MCP tool schemas |
| `_check_permission()` | Whitelist/blacklist/approval logic |
| `_execute_local_tool()` | Executes from local registry |
| `_execute_mcp_tool()` | Executes via MCP client (parses server_name from tool name) |
| `_execute_parallel()` | Parallel execution of multiple tool calls |
| `_handle_approval_call()` | Creates approval request, suspends execution |

**Factory**: `create_tool_handler(tool_registry, mcp_client, approval_manager, config)`

#### approval.py (~580 LOC)

**ToolApprovalManager** — Approval workflow:

| Class | Description |
|-------|-------------|
| `ApprovalStatus` | Enum: PENDING, APPROVED, REJECTED, EXPIRED, CANCELLED |
| `ToolApprovalRequest` | @dataclass with tool_call, session_id, timeout, `is_pending`, `is_expired`, `time_remaining` properties |
| `ApprovalCacheProtocol` | Protocol for Redis-like cache |
| `ApprovalError` / `ApprovalNotFoundError` / `ApprovalAlreadyResolvedError` / `ApprovalExpiredError` | Error classes |
| `ToolApprovalManager` | Manager using Redis for persistence |

**ToolApprovalManager Key Methods**:

| Method | Purpose |
|--------|---------|
| `create_approval_request()` | Creates request, stores in Redis with TTL |
| `get_approval_request()` | Retrieves from Redis, checks expiration |
| `resolve_approval()` | Approve/reject with validation |
| `approve()` / `reject()` | Convenience wrappers |
| `get_pending_approvals()` | Lists pending approvals for a session |
| `cancel_approval()` | Cancels pending approval |
| `cleanup_expired()` | Removes expired approvals |

**Persistence**: Redis with JSON serialization, TTL-based expiration

### 7.5 Bridge Layer

#### bridge.py (~850 LOC)

**SessionAgentBridge** — Central integration point (Sprint S46):

| Class | Description |
|-------|-------------|
| `SessionServiceProtocol` | Protocol defining session service interface |
| `AgentRepositoryProtocol` | Protocol for agent lookup |
| `BridgeConfig` | @dataclass: max_iterations(10), default_timeout(120), enable_streaming(True), enable_approval(True) |
| `ProcessingContext` | @dataclass: session, agent_config, iteration, pending_approvals |
| `BridgeError` / `SessionNotFoundError` / `SessionNotActiveError` / `AgentNotFoundError` / `MaxIterationsExceededError` / `PendingApprovalError` | Error hierarchy |
| `SessionAgentBridge` | Main bridge class |

**SessionAgentBridge Key Methods**:

| Method | Purpose |
|--------|---------|
| `process_message()` | Main entry: validates session → sends user message → executes agent → handles tool calls → returns events |
| `handle_tool_approval()` | Resolves pending approval → continues execution |
| `get_pending_approvals()` | Lists pending approvals for session |
| `cancel_pending_approvals()` | Cancels all pending approvals |
| `_get_active_session()` | Validates session is active |
| `_get_agent_config()` | Loads agent and creates AgentConfig |
| `_execute_with_tools()` | Main execution loop: LLM call → tool calls → approval check → iterate |
| `_continue_after_approval()` | Resumes execution after tool approval |
| `_requires_approval()` | Checks if tool needs approval based on config |

**Factory**: `create_session_agent_bridge(session_service, agent_repository, llm_client, ...)`

### 7.6 Error Handling, Recovery, and Metrics

#### error_handler.py (~390 LOC)

**SessionErrorHandler** — Comprehensive error handling (S47-2):

| Class | Description |
|-------|-------------|
| `SessionErrorCode` | Enum with 24 error codes across 6 categories: Session (4), Agent (3), LLM (5), Tool (5), Approval (3), System (4) |
| `SessionError` | Exception with error_code, details, http_status property, `to_event()` for SSE |
| `SessionErrorHandler` | Handler with retry logic |

**Key Methods**:
- `handle_llm_error()` — Handles timeout, API error, rate limit, content filter with appropriate retry/backoff
- `handle_tool_error()` — Handles tool execution, timeout, permission errors
- `with_retry()` — Generic retry wrapper with configurable max_retries, delay, backoff
- `safe_execute()` — Exception-safe wrapper returning error events

**HTTP Status Mapping**: Error codes mapped to 400/401/403/404/408/429/500/503 status codes

#### recovery.py (~380 LOC)

**SessionRecoveryManager** — Checkpoint and reconnection (S47-2):

| Class | Description |
|-------|-------------|
| `CheckpointType` | Enum: EXECUTION_START, TOOL_CALL, APPROVAL_PENDING, CONTENT_PARTIAL, EXECUTION_COMPLETE |
| `SessionCheckpoint` | @dataclass with session_id, state dict, expiration, `is_expired` property |
| `CacheProtocol` | Protocol for cache backend |
| `SessionRecoveryManager` | Recovery manager |

**Key Methods**:
- `save_checkpoint()` / `get_checkpoint()` / `delete_checkpoint()` — Checkpoint CRUD
- `restore_from_checkpoint()` — Restores session state and returns buffered events
- `buffer_event()` / `get_buffered_events()` / `clear_event_buffer()` — Event buffer for reconnection
- `handle_websocket_reconnect()` — Full reconnection flow: checks checkpoint → replays buffered events
- `save_reconnect_info()` / `get_reconnect_info()` — Tracks reconnection state
- `create_reconnect_event()` / `create_recovery_event()` — Event factories

#### metrics.py (~540 LOC)

**MetricsCollector** — Prometheus-style metrics (S47-3):

| Class | Description |
|-------|-------------|
| `MetricType` | Enum: COUNTER, HISTOGRAM, GAUGE |
| `MetricValue` | @dataclass with name, value, labels, timestamp |
| `Counter` | Increment-only counter with labels |
| `Histogram` | Distribution tracking with configurable buckets |
| `Gauge` | Up/down gauge metric |
| `MetricsCollector` | Centralized collector singleton |

**Metrics Tracked**:
- **Messages**: Total, by role (user/assistant/system), by session
- **Tool Calls**: Total, success, failure, timeout, execution time histogram
- **Errors**: By error code
- **Approvals**: Requested, granted, denied, timeout
- **Response Time**: LLM response time histogram
- **Token Usage**: Prompt, completion, total tokens by model
- **Sessions**: Active sessions gauge, WebSocket connections gauge

**Decorators**: `@track_time(metric_name, collector)`, `@track_tool_time(collector)`

### 7.7 files/ Subdirectory (~4,142 LOC)

File analysis and generation system:

| File | LOC | Class | Purpose |
|------|-----|-------|---------|
| `types.py` | 241 | `AnalysisType`, `GenerationType`, `AnalysisRequest`, `AnalysisResult`, `GenerationRequest`, `GenerationResult` | Type definitions and request/result models |
| `__init__.py` | 96 | — | Exports: FileAnalyzer, DocumentAnalyzer, ImageAnalyzer, CodeAnalyzer, DataAnalyzer, FileGenerator, CodeGenerator, ReportGenerator, DataExporter |
| `analyzer.py` | 350 | `BaseAnalyzer`, `FileAnalyzer` | Base analyzer class + dispatcher that routes to specialized analyzers |
| `document_analyzer.py` | 391 | `DocumentAnalyzer` | PDF/DOCX/TXT analysis: summary, extraction, Q&A |
| `image_analyzer.py` | 401 | `ImageAnalyzer` | Image analysis: describe, OCR, classify, detect objects |
| `code_analyzer.py` | 396 | `CodeAnalyzer` | Code analysis: review, explain, optimize, security audit |
| `data_analyzer.py` | 638 | `DataAnalyzer` | CSV/JSON/Excel/XML/YAML/Parquet: summary, statistics, transform, query, visualize |
| `generator.py` | 362 | `BaseGenerator`, `FileGenerator` | Base generator + dispatcher |
| `code_generator.py` | 318 | `CodeGenerator` | Code generation from specs |
| `report_generator.py` | 453 | `ReportGenerator` | Report generation (summary, analysis, compliance) |
| `data_exporter.py` | 496 | `DataExporter` | Data export to CSV/JSON/Excel formats |

**Architecture**: Strategy pattern — `FileAnalyzer` and `FileGenerator` dispatch to specialized implementations based on `AttachmentType`.

### 7.8 history/ Subdirectory (~1,530 LOC)

| File | LOC | Class | Purpose |
|------|-----|-------|---------|
| `__init__.py` | 37 | — | Exports |
| `manager.py` | 458 | `HistoryFilter`, `HistoryPage`, `HistoryManager` | Paginated history with export (JSON/Markdown/Text), cleanup |
| `bookmarks.py` | 488 | `Bookmark`, `BookmarkFilter`, `BookmarkService` | Message bookmarking with tags, export |
| `search.py` | 547 | `SearchScope`, `SearchSortBy`, `SearchQuery`, `SearchResult`, `SearchResponse`, `SearchService` | Full-text search with Elasticsearch/database fallback, indexing, suggestions |

### 7.9 features/ Subdirectory (~1,426 LOC)

| File | LOC | Class | Purpose |
|------|-----|-------|---------|
| `__init__.py` | 37 | — | Exports |
| `tags.py` | 450 | `Tag`, `SessionTag`, `TagService` | Session tagging with color generation, suggestions, popular tags |
| `statistics.py` | 426 | `MessageStatistics`, `SessionStatistics`, `UserStatistics`, `StatisticsService` | Session/user statistics with caching, staleness detection |
| `templates.py` | 513 | `TemplateCategory`, `SessionTemplate`, `TemplateService` | Session templates: create from session, apply to new session, popular templates |

### 7.10 events.py (~830 LOC)

**Dual event system**:

1. **ExecutionEvent System** (S45-4):
   - `ExecutionEventType` — 27+ types: STARTED, CONTENT, CONTENT_DELTA, TOOL_CALL, TOOL_RESULT, APPROVAL_REQUIRED, APPROVAL_RESPONSE, ERROR, DONE, HEARTBEAT, etc.
   - `ExecutionEvent` — @dataclass with type, data, session_id, `to_sse()`, `to_json()`, `from_dict()`
   - `ExecutionEventFactory` — Factory methods for all event types
   - Supporting: `ToolCallInfo`, `ToolResultInfo`, `UsageInfo`

2. **SessionEvent System** (Original):
   - `SessionEventType` — 15+ types: SESSION_CREATED/ACTIVATED/ENDED, MESSAGE_SENT/RECEIVED, TOOL_CALL_REQUESTED, ERROR_OCCURRED, etc.
   - `SessionEvent` — @dataclass with type, session_id, data
   - `SessionEventPublisher` — Pub/sub with type-specific and wildcard subscriptions, async handler support

**Singleton**: `get_event_publisher()` / `reset_event_publisher()`

---

## 8. templates/ Module

**Path**: `backend/src/domain/templates/`
**Files**: 3 (`__init__.py` 15 LOC, `models.py` ~350 LOC, `service.py` ~400 LOC)
**Sprint**: S4 (Developer Experience - Agent Template Marketplace)

### Classes

| Class | Type | Description |
|-------|------|-------------|
| `TemplateCategory` | Enum | IT_OPERATIONS, CUSTOMER_SERVICE, MONITORING, APPROVAL, REPORTING, KNOWLEDGE, CUSTOM |
| `TemplateStatus` | Enum | DRAFT, PUBLISHED, DEPRECATED, ARCHIVED |
| `ParameterType` | Enum | STRING, NUMBER, INTEGER, BOOLEAN, LIST, OBJECT |
| `TemplateParameter` | @dataclass | Parameter with type, validation (required, default, options, min/max, pattern) |
| `TemplateExample` | @dataclass | Input/output example for demonstration |
| `TemplateVersion` | @dataclass | Version info with changelog, deprecation |
| `AgentTemplate` | @dataclass | Full template: identity, classification, agent config (instructions, tools, capabilities), metadata (usage_count, rating), examples, version history |
| `TemplateError` | Exception | Base error |
| `TemplateService` | Service | CRUD, YAML loading, search, instantiation, version management |

### TemplateService Key Methods
- `load_templates()` — Load from YAML directory
- `search_templates()` — Text similarity search using SequenceMatcher
- `instantiate_template()` — Create agent from template with parameter validation
- `clone_template()` — Deep copy with new ID
- `rate_template()` — Running average rating system
- `get_popular_templates()` — Sort by usage count

### Issues
- In-memory storage only
- `SequenceMatcher` for search similarity (same as learning/)

---

## 9. triggers/ Module

**Path**: `backend/src/domain/triggers/`
**Files**: 2 (`__init__.py` 25 LOC, `webhook.py` ~550 LOC)
**Sprint**: S3 (Integration & Reliability - n8n trigger)

### Classes

| Class | Type | Description |
|-------|------|-------------|
| `WebhookStatus` | Enum | PENDING, PROCESSING, COMPLETED, FAILED, RETRYING |
| `SignatureAlgorithm` | Enum | SHA256, SHA1 |
| `WebhookTriggerConfig` | @dataclass | workflow_id, secret, callback_url, retry config (max_retries, retry_delay, max_retry_delay), algorithm |
| `WebhookPayload` | @dataclass | data, headers, signature, timestamp, source; `from_request()` factory |
| `TriggerResult` | @dataclass | Result with execution_id, status, retries |
| `WebhookError` | Exception | With status_code |
| `WebhookTriggerService` | Service | Webhook processing with HMAC validation |

### Key Features
- **HMAC-SHA256 signature verification** with constant-time comparison (`hmac.compare_digest`)
- **Exponential backoff retry** with max delay cap
- **Workflow triggering** via callback function
- **Success/failure callbacks** for notification

### Issues
- In-memory config storage
- Timestamp validation commented out or basic

---

## 10. versioning/ Module

**Path**: `backend/src/domain/versioning/`
**Files**: 2 (`__init__.py` 24 LOC, `service.py` ~650 LOC)
**Sprint**: S4 (Developer Experience - Template Version Management)

### Classes

| Class | Type | Description |
|-------|------|-------------|
| `VersionStatus` | Enum | DRAFT, PUBLISHED, DEPRECATED, ARCHIVED |
| `ChangeType` | Enum | MAJOR, MINOR, PATCH |
| `SemanticVersion` | @dataclass | major.minor.patch with `parse()`, `increment()`, comparison operators |
| `TemplateVersion` | @dataclass | Full version with template_id, version, content snapshot, changelog, author, status |
| `VersionDiff` | @dataclass | Diff between versions with added/removed/modified lines |
| `VersioningError` | Exception | Base error |
| `VersioningService` | Service | Version management |

### VersioningService Key Methods
- `create_version()` — Creates new version with auto-increment based on ChangeType
- `get_version()` / `list_versions()` / `get_latest_version()` — Retrieval
- `compare_versions()` — Generates unified diff using `difflib`
- `rollback_to_version()` — Creates new version from old content
- `publish_version()` / `deprecate_version()` — Status management
- `get_version_history()` — Chronological version list

### Issues
- In-memory storage (`_versions: Dict[str, List[TemplateVersion]]`)
- No actual template content linking (versions stored independently)

---

## 11. workflows/ Module

**Path**: `backend/src/domain/workflows/`
**Files**: 11 (`__init__.py` + models.py + schemas.py + service.py + resume_service.py + deadlock_detector.py + executors/[4 files])
**Sprints**: S1 (Core Engine), S7 (Concurrent Execution), S27 (Official API Migration)

### 11.1 models.py (~350 LOC)

| Class | Type | Description |
|-------|------|-------------|
| `NodeType` | Enum | START, END, AGENT, DECISION, MERGE, FORK, JOIN, HUMAN_APPROVAL, NOTIFICATION |
| `TriggerType` | Enum | MANUAL, SCHEDULE, WEBHOOK, EVENT |
| `GatewayType` | Enum | EXCLUSIVE, PARALLEL, INCLUSIVE |
| `WorkflowNode` | @dataclass | Node with id, type, agent_id, config, position |
| `WorkflowEdge` | @dataclass | Edge with source, target, condition, label |
| `WorkflowDefinition` | @dataclass | Full DAG: nodes, edges, triggers, `get_start_node()`, `get_outgoing_edges()` |
| `WorkflowContext` | @dataclass | Execution context: variables, history, current_node |

### 11.2 schemas.py (~250 LOC)

Pydantic-like request/response schemas: `WorkflowNodeSchema`, `WorkflowEdgeSchema`, `WorkflowGraphSchema`, `WorkflowCreateRequest`, `WorkflowUpdateRequest`, `WorkflowResponse`, `WorkflowListResponse`, `WorkflowExecuteRequest`, `WorkflowExecutionResponse`, `WorkflowValidationResponse`.

### 11.3 service.py (~700 LOC)

**WorkflowExecutionService** — Main execution engine:

| Class | Description |
|-------|-------------|
| `NodeExecutionResult` | Result with node_id, type, output, error, llm_tokens, llm_cost, timing |
| `WorkflowExecutionResult` | Aggregated: execution_id, status, node_results, total_llm_calls/tokens/cost, duration |
| `WorkflowExecutionService` | Core execution service |

**Key Methods**:
- `execute_workflow()` — Main execution: creates result → traverses DAG → executes nodes sequentially → handles state transitions
- `_execute_node()` — Dispatches to node-type-specific handlers
- `_execute_agent_node()` — Calls agent via `AgentService.invoke_agent()`
- `_execute_decision_node()` — Evaluates conditions on edges
- `_evaluate_condition()` — Simple expression evaluation

**Sprint 27 Integration**: Imports from `integrations/agent_framework/core/` for `WorkflowNodeExecutor`, `SequentialOrchestrationAdapter`, `EnhancedExecutionStateMachine`, `WorkflowStatusEventAdapter`.

**Singleton**: `get_workflow_execution_service()`

### 11.4 resume_service.py (~400 LOC)

**WorkflowResumeService** — Resumes paused workflows:

| Class | Description |
|-------|-------------|
| `ResumeStatus` | Enum: SUCCESS, NOT_FOUND, INVALID_STATE, CHECKPOINT_PENDING/REJECTED/EXPIRED, ERROR |
| `ResumeResult` | @dataclass with status, execution_id, checkpoint_id, next_node_id, restored_state |
| `WorkflowResumeService` | Resume service |

**Key Methods**:
- `resume_from_checkpoint()` — Validates checkpoint status → restores state → identifies next node → triggers re-execution
- `can_resume()` — Checks if execution can be resumed
- `get_resume_state()` — Gets current resume state

**Dependencies**: CheckpointService, ExecutionStateMachine, ExecutionRepository

### 11.5 deadlock_detector.py (~650 LOC)

**DeadlockDetector** — Wait-for graph cycle detection:

| Class | Description |
|-------|-------------|
| `DeadlockResolutionStrategy` | Enum: CANCEL_YOUNGEST/OLDEST/ALL/LOWEST_PRIORITY, NOTIFY_ONLY |
| `WaitingTask` | @dataclass: task_id, waiting_for set, timeout, priority, metadata, `is_timed_out` |
| `DeadlockInfo` | @dataclass: cycle list, detected_at, resolved, resolution_strategy |
| `DeadlockDetector` | Detector with DFS cycle detection |
| `TimeoutHandler` | Task/execution timeout management |

**DeadlockDetector Key Methods**:
- `register_wait()` / `unregister_wait()` — Build wait-for graph
- `detect_deadlocks()` — DFS cycle detection in wait-for graph
- `resolve_deadlock()` — Applies resolution strategy (cancel youngest/oldest/all/lowest priority)
- `_find_cycles()` — Classic DFS with coloring (WHITE/GRAY/BLACK)
- `get_wait_graph()` — Returns current graph state

**TimeoutHandler Key Methods**:
- `register_task()` / `complete_task()` — Task timeout tracking
- `check_timeouts()` — Returns list of timed-out tasks
- `set_execution_timeout()` / `check_execution_timeout()` — Global execution timeout

**Singleton**: `get_deadlock_detector()` / `reset_deadlock_detector()`

### 11.6 executors/ Subdirectory

#### approval.py (~420 LOC)

**ApprovalGateway** — Human approval for workflow nodes:

| Class | Description |
|-------|-------------|
| `ApprovalAction` | Enum: APPROVE, REJECT, MODIFY, RETRY |
| `HumanApprovalRequest` | @dataclass with execution_id, node_id, agent_id, prompt, content, context, iteration |
| `ApprovalResponse` | @dataclass with action, modified_content, feedback, reviewer |
| `ApprovalGateway` | Executor for approval workflow nodes |

**Key Methods**:
- `execute()` — Pauses workflow, creates checkpoint, waits for human decision
- `handle_response()` — Processes approval/rejection/modification/retry
- `get_pending_approvals()` — Lists pending approvals for execution

**Dependencies**: `CheckpointService`, `CheckpointStatus`, `CheckpointData`

#### concurrent.py (~580 LOC)

**ConcurrentExecutor** — Parallel branch execution:

**Key Methods**:
- `execute_parallel()` — Runs multiple nodes concurrently with configurable max concurrency
- `execute_with_gateway()` — Fork-join pattern with state management
- `_execute_branch()` — Single branch execution with error handling

#### concurrent_state.py (~600 LOC)

**ConcurrentStateManager** — State tracking for parallel execution:

| Class | Description |
|-------|-------------|
| `BranchStatus` | Enum: PENDING, RUNNING, COMPLETED, FAILED, CANCELLED, TIMED_OUT |
| `ParallelBranch` | @dataclass: branch_id, node_ids, status, result, timing |
| `ConcurrentExecutionState` | Full state for a parallel execution region |
| `ConcurrentStateManager` | Singleton state manager |

**Key Methods**:
- `create_state()` / `get_state()` / `delete_state()` — State lifecycle
- `update_branch_status()` / `set_branch_result()` — Branch tracking
- `is_complete()` / `get_completed_results()` — Completion checking

**Singleton**: `get_state_manager()`

#### parallel_gateway.py (~700 LOC)

**ParallelForkGateway / ParallelJoinGateway** — Fork-join pattern:

| Class | Description |
|-------|-------------|
| `JoinStrategy` | Enum: WAIT_ALL, WAIT_ANY, WAIT_MAJORITY, WAIT_N |
| `MergeStrategy` | Enum: COLLECT_ALL, MERGE_DICT, FIRST_RESULT, AGGREGATE |
| `ParallelGatewayConfig` | @dataclass: max_concurrency, timeout, join_strategy, merge_strategy, wait_n_count |
| `ParallelForkGateway` | Forks execution into parallel branches |
| `ParallelJoinGateway` | Joins branches with configurable merge |

**Key Methods**:
- Fork: `execute()` — Creates branches, registers with state manager
- Join: `execute()` — Waits per join strategy, merges per merge strategy
- `_merge_results()` — Applies merge strategy (collect_all, merge_dict, first_result, aggregate)

---

## 12. Cross-References

### sessions/ → Other Agents' Scope

| Dependency | Target | Agent |
|------------|--------|-------|
| `src.integrations.agent_framework.core.*` | executor.py, state_machine | C1-C2 |
| `src.integrations.orchestration.*` | Intent routing | C1-C2 |
| `src.infrastructure.database.*` | Repository layer | A1-A2 |
| `src.domain.agents.service` | AgentService | A2 |

### workflows/ → Other Agents' Scope

| Dependency | Target | Agent |
|------------|--------|-------|
| `src.domain.agents.service.AgentService` | Agent invocation | A2 |
| `src.integrations.agent_framework.core.executor` | WorkflowNodeExecutor | C1-C2 |
| `src.integrations.agent_framework.core.orchestration` | SequentialOrchestrationAdapter | C1-C2 |
| `src.integrations.agent_framework.core.state_machine` | EnhancedExecutionStateMachine | C1-C2 |
| `src.integrations.agent_framework.core.events` | WorkflowStatusEventAdapter | C1-C2 |
| `src.domain.checkpoints` | CheckpointService | A2 |
| `src.domain.executions` | ExecutionStateMachine | A2 |

### learning/ → Plan Feature Area A11
- `LearningService` provides few-shot learning infrastructure
- `build_few_shot_prompt()` can be used to enhance any LLM interaction
- Currently uses `SequenceMatcher`; production plan calls for embedding-based similarity

---

## 13. Problems and Issues

### Critical Issues

| # | Module | Issue | Severity |
|---|--------|-------|----------|
| 1 | learning/, templates/, routing/, triggers/, versioning/, prompts/ | **In-memory only storage** — all data lost on restart | HIGH |
| 2 | sandbox/ | **Simulated sandbox** — no real process isolation | HIGH |
| 3 | notifications/teams.py:683 | Unused variable `cutoff` in `_check_rate_limit()` | LOW |

### Code Quality Issues

| # | Module | Issue | Files |
|---|--------|-------|-------|
| 4 | Multiple | `datetime.utcnow()` deprecated in Python 3.12+ | learning/service.py, notifications/teams.py, routing/scenario_router.py, sessions/models.py, etc. |
| 5 | prompts/template.py | Docstring says "Jinja2 syntax" but uses simple string replacement | template.py |
| 6 | routing/scenario_router.py | Linear scan O(n) for relation queries | scenario_router.py |

### Architecture Concerns

| # | Concern | Detail |
|---|---------|--------|
| 7 | **Dual event system in sessions** | Both `ExecutionEvent` (S45) and `SessionEvent` (original) coexist — potential confusion |
| 8 | **No database persistence** for 6 of 10 modules | Only sessions/ and workflows/ (via integrations) have real persistence |
| 9 | **Singleton patterns** | DeadlockDetector, MetricsCollector, SessionEventPublisher use module-level singletons — harder to test |
| 10 | **Large bridge.py** | SessionAgentBridge at ~850 LOC handles message processing, tool approval, execution loops — could benefit from decomposition |

### Missing Features / TODOs

| # | Module | Note |
|---|--------|------|
| 11 | learning/ | "Production should use embeddings" (line 388) |
| 12 | versioning/ | "Branch management (future)" in header |
| 13 | sessions/history/search.py | Elasticsearch integration defined but may not be fully wired |
| 14 | sandbox/ | "In production, this would use process pooling" comment |

---

*Analysis completed by Agent B3. All 55 Python files across 10 domain subdirectories have been fully analyzed.*
