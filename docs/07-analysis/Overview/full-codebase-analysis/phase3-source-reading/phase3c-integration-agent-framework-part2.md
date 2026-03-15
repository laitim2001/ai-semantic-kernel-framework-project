# Phase 3C: Agent Framework Integration - Part 2 Analysis

> **Scope**: `backend/src/integrations/agent_framework/` — memory/, tools/, acl/, multiturn/, assistant/, workflow.py, exceptions.py, __init__.py
> **Analyst**: Agent C2
> **Date**: 2026-03-15

---

## 1. Executive Summary

This analysis covers the non-builder portions of the agent_framework integration layer: memory storage backends, tool adapters, anti-corruption layer (ACL), multi-turn conversation management, assistant services (Azure OpenAI Assistants API), and supporting infrastructure (workflow adapter, exceptions, module init).

**Key Findings**:
- Two memory storage backends (Redis, PostgreSQL) with a well-designed Protocol/ABC base
- ACL layer provides version-resilient isolation from MAF API changes (Sprint 128)
- Multi-turn adapter integrates official CheckpointStorage with rich session lifecycle
- Checkpoint storage has 3 custom backends (Redis, Postgres, File) but they use a **non-official API** (save/load/delete) incompatible with the official save_checkpoint/load_checkpoint
- Tool system has a clean registry pattern but only one concrete tool (CodeInterpreterTool)
- Assistant module provides full Azure OpenAI Assistants API lifecycle management
- Several SQL injection risks via f-string table name interpolation in Postgres implementations

**Total files analyzed**: 20 .py files (~3,200 LOC)

---

## 2. Memory Subsystem (`memory/`)

### 2.1 Architecture

```
MemoryStorageProtocol (Protocol, runtime_checkable)
    ↑ defines: store(), retrieve(), search(), delete()

BaseMemoryStorageAdapter (ABC)
    ↑ implements: store_record(), retrieve_record(), search_advanced(),
    |             exists(), update(), get_or_create(), clear_namespace()
    |             initialize(), close()
    ├── RedisMemoryStorage
    └── PostgresMemoryStorage
```

### 2.2 Base Types (`memory/base.py`, 453 LOC)

| Type | Description |
|------|-------------|
| `MemoryRecord` | Dataclass: key, value, metadata, created_at, updated_at, ttl_seconds, tags |
| `SearchOptions` | Dataclass: limit, offset, include_metadata, tags_filter, score_threshold |
| `MemorySearchResult` | Dataclass: record, score, highlights |
| `MemoryStorageProtocol` | Protocol defining store/retrieve/search/delete |
| `BaseMemoryStorageAdapter` | ABC with namespace isolation, extended API |

**Official MAF Import**: `from agent_framework import Context, ContextProvider` (imported but not actively used in logic — only for compatibility declaration).

**Exception Hierarchy**:
- `MemoryError` (base)
  - `MemoryNotFoundError`
  - `MemoryStorageError`
  - `MemoryValidationError`

**Design Notes**:
- Namespace-based key isolation via `_make_key()` / `_strip_namespace()`
- Extended API methods (`store_record`, `retrieve_record`, `search_advanced`, `exists`, `update`, `get_or_create`) built on top of the 4 core abstract methods
- `clear_namespace()` warns "not implemented" in base — subclasses override

### 2.3 Redis Storage (`memory/redis_storage.py`, 483 LOC)

**Class**: `RedisMemoryStorage(BaseMemoryStorageAdapter)`

| Method | Description |
|--------|-------------|
| `store(key, value)` | JSON-serialize, SET with optional TTL |
| `retrieve(key)` | GET + JSON deserialize, handles bytes |
| `search(query, limit)` | SCAN all namespace keys, mget, case-insensitive substring match |
| `delete(key)` | DELETE + remove from search index |
| `store_with_ttl(key, value, ttl)` | SET with specific TTL |
| `exists(key)` | EXISTS command (overrides base) |
| `set_ttl(key, ttl)` | EXPIRE command |
| `get_keys(pattern)` | KEYS command with namespace prefix |
| `get_many(keys)` | MGET batch retrieval |
| `set_many(data)` | MSET batch storage |
| `clear_namespace()` | SCAN + DELETE loop |
| `initialize()` | Verifies connection via PING |

**Configuration**:
- Default namespace: `"memory"`
- Default TTL: 86400s (24 hours)
- `search_index_enabled`: flag exists but search index methods are no-ops (pass)

**Issues**:
1. **Search is brute-force**: SCAN + mget + substring match. Production note in comments acknowledges this. No RediSearch integration.
2. **Search index methods are stubs**: `_update_search_index()` and `_remove_from_search_index()` are empty `pass` — the `search_index_enabled` flag has no effect.
3. **get_keys uses KEYS command**: Should use SCAN for production (KEYS blocks Redis).
4. **RedisClientProtocol defined but not enforced**: Constructor accepts `Any`.

**Factory**: `create_redis_storage(redis_client, namespace, ttl_seconds)` -> `RedisMemoryStorage`

### 2.4 PostgreSQL Storage (`memory/postgres_storage.py`, 670 LOC)

**Class**: `PostgresMemoryStorage(BaseMemoryStorageAdapter)`

**Table Schema**: `memory_storage` with columns: id, namespace, key, value (JSONB), metadata (JSONB), tags (TEXT[]), created_at, updated_at, expires_at. Unique constraint on (namespace, key). GIN indexes on tags and value.

| Method | Description |
|--------|-------------|
| `store(key, value)` | UPSERT via INSERT ON CONFLICT |
| `retrieve(key)` | SELECT with expiry check |
| `search(query, limit)` | ILIKE on value::text |
| `delete(key)` | DELETE, parses "DELETE N" result |
| `store_with_metadata(...)` | UPSERT with metadata, tags, TTL |
| `retrieve_with_metadata(key)` | Returns (value, metadata, tags) tuple |
| `search_by_tags(tags, match_all)` | Uses `@>` (contains) or `&&` (overlap) operators |
| `search_by_jsonb_path(path, value)` | Builds dynamic JSONB path query |
| `get_keys(pattern)` | SELECT key with LIKE pattern |
| `count()` | COUNT with expiry check |
| `clear_namespace()` | DELETE WHERE namespace = $1 |
| `cleanup_expired()` | DELETE expired records |
| `initialize()` | Creates table and indexes if auto_create_table=True |

**Configuration**:
- Default namespace: `"memory"`
- Default TTL: None (no expiry)
- `auto_create_table`: True (creates table on first use)

**Issues**:
1. **SQL injection via TABLE_NAME**: `f"...{self.TABLE_NAME}..."` — table name is a class attribute `"memory_storage"`, currently safe but not parameterized. If subclassed with user input, could be exploitable.
2. **search_by_jsonb_path builds dynamic SQL**: `jsonb_path` constructed from user input `path.split(".")` — potential SQL injection if path is not validated.
3. **No connection pooling awareness**: Accepts single connection, not pool. Long-running operations could block.
4. **PostgresConnectionProtocol defined but not enforced**: Constructor accepts `Any`.
5. **Uses `datetime.utcnow()`**: Deprecated in Python 3.12+, should use `datetime.now(timezone.utc)`.

**Factory**: `create_postgres_storage(connection, namespace, ttl_seconds, auto_create_table)` -> `PostgresMemoryStorage`

---

## 3. Tool Subsystem (`tools/`)

### 3.1 Base Tool Framework (`tools/base.py`, 345 LOC)

**Classes**:

| Class | Description |
|-------|-------------|
| `ToolStatus` | Enum: SUCCESS, FAILURE, PARTIAL, TIMEOUT, ERROR |
| `ToolResult` | Dataclass: success, output, metadata, status, error, files. Factory methods: `success_result()`, `failure_result()`, `error_result()` |
| `ToolParameter` | Dataclass: name, type, description, required, default |
| `ToolSchema` | Dataclass: name, description, parameters, returns. Has `to_openai_function()` for OpenAI function-calling format |
| `BaseTool` | ABC with `run(**kwargs)` abstract method. Supports async context manager, lifecycle (initialize/cleanup) |
| `ToolRegistry` | Dict-based registry: register/unregister/get/list_tools/get_schemas |

**Singleton**: `get_tool_registry()` returns global `ToolRegistry` instance.

**Design Notes**:
- Clean separation of concerns: schema definition, execution, registry
- `to_openai_function()` generates OpenAI function-calling compatible schemas
- Async context manager support for resource lifecycle

### 3.2 Code Interpreter Tool (`tools/code_interpreter_tool.py`, 415 LOC)

**Class**: `CodeInterpreterTool(BaseTool)`

Wraps `CodeInterpreterAdapter` (from `builders/code_interpreter.py`) as an agent-callable tool.

**Supported Actions**:
| Action | Parameters | Description |
|--------|-----------|-------------|
| `execute` | code, timeout | Execute Python code |
| `analyze` | task, context, file_id | AI-driven task analysis |
| `visualize` | data, chart_type, title, x_label, y_label | Generate matplotlib charts |

**Chart Types**: bar, line, pie, scatter, hist, box

**Implementation Details**:
- Generates matplotlib code dynamically via `_generate_chart_code()`
- Saves charts to `chart.png` with non-interactive Agg backend
- `_owns_adapter` flag controls cleanup responsibility

**Issues**:
1. **`_execute_code` calls `self._adapter.execute()` synchronously**: The method is `async def` but calls synchronous `.execute()` — potential event loop blocking.
2. **Chart code uses string interpolation for data**: `data_json` is dumped and interpolated into Python code string — if data contains special characters, could break generated code.
3. **Hardcoded output filename**: Always saves to `chart.png`, no uniqueness.

### 3.3 Tool Registration (`tools/__init__.py`)

`register_default_tools()` registers `CodeInterpreterTool` into the global registry.

---

## 4. Anti-Corruption Layer (`acl/`)

### 4.1 Stable Interfaces (`acl/interfaces.py`, 267 LOC)

Sprint 128 Story 128-2. Defines **immutable** interfaces that isolate IPA Platform from MAF API changes.

**Frozen Dataclasses** (immutable):

| Type | Fields | Notes |
|------|--------|-------|
| `AgentConfig` | name, description, model, system_prompt, tools (tuple), metadata (tuple) | Uses tuples for frozen compatibility. Helper methods `get_tools_list()`, `get_metadata_dict()` |
| `WorkflowResult` | success, output, error, metadata (tuple) | Normalized result from any MAF workflow execution |

**Abstract Interfaces**:

| Interface | Methods | Purpose |
|-----------|---------|---------|
| `AgentBuilderInterface` | `add_agent(config)`, `build()`, `validate()` | Stable builder contract |
| `AgentRunnerInterface` | `execute(workflow, input)`, `execute_stream(workflow, input)`, `cancel(execution_id)` | Stable execution contract |
| `ToolInterface` | `get_name()`, `get_description()`, `get_schema()`, `execute(**params)` | Stable tool contract |

**Design Quality**: Excellent. Frozen dataclasses enforce immutability. Clear separation between stable interfaces (never change) and adapter implementations (change with MAF versions).

### 4.2 Version Detector (`acl/version_detector.py`, 229 LOC)

**Class**: `MAFVersionDetector` (all classmethod)

| Method | Description |
|--------|-------------|
| `detect()` | Import agent_framework, read __version__, parse, check compatibility |
| `check_api_available(api_name)` | hasattr check on agent_framework module |
| `get_available_apis()` | Check 12 expected API names |
| `is_compatible(version_info)` | Returns True if "full" or "partial" |
| `_parse_version(version_str)` | Regex parse: major.minor.patch + preview tag |

**Frozen Dataclass**: `MAFVersionInfo` — version, is_preview, major/minor/patch, preview_tag, is_available, api_compatibility.

**Known Compatible Versions**:
- `1.0.0b251204`: "full" (tested)
- `1.0.0b250101`: "partial" (untested)

**Issues**:
1. **Hardcoded compatibility map**: Only 2 versions listed. New versions default to "unknown".

### 4.3 Version Adapter (`acl/adapter.py`, 235 LOC)

**Class**: `MAFAdapter` (singleton via `get_maf_adapter()`)

| Method | Description |
|--------|-------------|
| `is_available()` | Checks if agent_framework is importable |
| `is_compatible()` | Checks compatibility level |
| `get_version_info()` | Returns MAFVersionInfo |
| `create_builder(builder_type)` | Maps type name to MAF class via BUILDER_TYPE_MAP |
| `wrap_exception(error)` | Maps MAF exceptions to AdapterError hierarchy |
| `reset()` | Clears cached detection state |

**Builder Type Map**: groupchat, handoff, concurrent, magentic, workflow -> corresponding MAF class names.

**Lazy Detection**: Version detection only happens on first access via `_ensure_detected()`.

**Exception Wrapping**: Pattern-matches error type names and messages to map to WorkflowBuildError, ExecutionError, or generic AdapterError.

---

## 5. Multi-turn Subsystem (`multiturn/`)

### 5.1 Multi-turn Adapter (`multiturn/adapter.py`, 861 LOC)

**Official MAF Imports**: `CheckpointStorage`, `InMemoryCheckpointStorage`, `WorkflowCheckpoint`

**Data Types**:

| Type | Description |
|------|-------------|
| `SessionState` | Enum: CREATED, ACTIVE, PAUSED, WAITING, COMPLETED, EXPIRED, ERROR |
| `MessageRole` | Enum: USER, ASSISTANT, SYSTEM, FUNCTION |
| `ContextScope` | Enum: TURN, SESSION, PERSISTENT |
| `Message` | Dataclass: role, content, timestamp, metadata |
| `TurnResult` | Dataclass: turn_id, session_id, input/output messages, context, duration, success |
| `SessionInfo` | Dataclass: session_id, state, timestamps, turn_count, total_tokens, metadata |
| `MultiTurnConfig` | Dataclass: max_turns(100), max_history(50), timeout(3600s), auto_save, save_interval(5), context_window(10), summarization settings |

**Supporting Classes**:

| Class | Purpose |
|-------|---------|
| `ContextManager` | Three-tier context (TURN < SESSION < PERSISTENT). Priority search from most local to most global. |
| `TurnTracker` | Message history with max_history truncation. Turn counting. Context message extraction for LLM. |

**Main Class**: `MultiTurnAdapter`

**Session Lifecycle**:
```
CREATED -> start() -> ACTIVE -> pause() -> PAUSED -> resume() -> ACTIVE -> complete() -> COMPLETED
```

**Key Methods**:

| Method | Description |
|--------|-------------|
| `start()` | Transitions CREATED -> ACTIVE |
| `pause()` | ACTIVE -> PAUSED, auto-saves checkpoint |
| `resume()` | PAUSED -> ACTIVE |
| `complete()` | Any -> COMPLETED, final save, triggers callback |
| `add_turn(user_input, response, context)` | Core conversation method. Auto-starts if CREATED. Tracks messages, manages context, auto-saves at intervals. |
| `get_history(n, include_system)` | Get conversation history |
| `get_context_messages(window_size)` | Get LLM-ready context window |
| `save_checkpoint()` | Creates WorkflowCheckpoint with full state in shared_state, calls official save_checkpoint() |
| `restore_checkpoint()` | Loads via official load_checkpoint(), restores from shared_state |
| `delete_checkpoint()` | Calls official delete_checkpoint() |
| `set_context(key, value, scope)` | Set context variable |
| `clear_session()` | Reset session data, delete checkpoint |

**Callbacks**: `on_turn_complete(callback)`, `on_session_complete(callback)` — synchronous callbacks.

**Factory Functions**:
- `create_multiturn_adapter(session_id, config, storage)` — standard factory
- `create_redis_multiturn_adapter(...)` — **raises NotImplementedError** with explanation that RedisCheckpointStorage uses IPA custom API, not official API

**Issues**:
1. **Redis multi-turn is broken**: `create_redis_multiturn_adapter()` raises NotImplementedError. The RedisCheckpointStorage uses save/load/delete instead of save_checkpoint/load_checkpoint/delete_checkpoint.
2. **Only InMemoryCheckpointStorage works**: All persistent backends (Redis, Postgres, File) in checkpoint_storage.py use the wrong API.
3. **Synchronous callbacks**: `_on_turn_complete` and `_on_session_complete` are synchronous, could block if handlers are slow.
4. **Uses `datetime.utcnow()`**: Deprecated in Python 3.12+.
5. **No thread safety**: In-memory state with no locks.

### 5.2 Checkpoint Storage (`multiturn/checkpoint_storage.py`, 492 LOC)

**Base Class**: `BaseCheckpointStorage(CheckpointStorage, ABC)` — extends official CheckpointStorage.

**Three Custom Backends**:

| Backend | Storage | TTL | Key Features |
|---------|---------|-----|--------------|
| `RedisCheckpointStorage` | Redis | Yes (default 24h) | High perf, auto-expire, distributed |
| `PostgresCheckpointStorage` | PostgreSQL | Yes (default 24h) | Persistent, UPSERT, cleanup_expired() |
| `FileCheckpointStorage` | File system | Yes (default 24h) | No deps, good for dev/test |

**CRITICAL API MISMATCH**: All three backends implement `save(session_id, state)`, `load(session_id)`, `delete(session_id)` — but the official CheckpointStorage interface requires `save_checkpoint(checkpoint)`, `load_checkpoint(checkpoint_id)`, `delete_checkpoint(checkpoint_id)`.

**Consequence**: These backends CANNOT be used with `MultiTurnAdapter` which calls the official API. Only `InMemoryCheckpointStorage` (from agent_framework) works.

**Additional Methods (shared)**:
- `list(pattern)` — list session IDs
- `extend_ttl(session_id, seconds)` — Redis only
- `cleanup_expired()` — Postgres and File only

**Issues**:
1. **API mismatch is the critical bug**: Documented in code comments but not fixed.
2. **PostgresCheckpointStorage uses f-string SQL with table name**: Same injection risk as memory Postgres.
3. **FileCheckpointStorage uses blocking I/O**: `open()` in async methods without aiofiles.
4. **FileCheckpointStorage default path is /tmp/checkpoints**: Unix-specific, not Windows-compatible.

---

## 6. Assistant Subsystem (`assistant/`)

### 6.1 Models (`assistant/models.py`, 147 LOC)

| Type | Description |
|------|-------------|
| `ExecutionStatus` | Enum: SUCCESS, ERROR, TIMEOUT, CANCELLED |
| `CodeExecutionResult` | Dataclass: status, output, execution_time, files, code_outputs |
| `AssistantConfig` | Dataclass: name, instructions, model, timeout(60s), max_retries(3) |
| `ThreadMessage` | Dataclass: role, content, file_ids |
| `AssistantInfo` | Dataclass: id, name, model, tools, created_at. Has `from_api_response()` classmethod |
| `FileInfo` | Dataclass: id, filename, bytes, created_at, purpose. Has `from_api_response()` classmethod |

### 6.2 Exceptions (`assistant/exceptions.py`, 168 LOC)

Hierarchy:
```
AssistantError (base)
├── ExecutionTimeoutError (timeout, elapsed)
├── AssistantNotFoundError (assistant_id)
├── CodeExecutionError (code, error_type)
├── AssistantCreationError
├── ThreadCreationError
├── RunError (run_id, run_status)
├── ConfigurationError
└── RateLimitError (retry_after)
```

### 6.3 AssistantManagerService (`assistant/manager.py`, 415 LOC)

**Purpose**: Full lifecycle management for Azure OpenAI Assistants with Code Interpreter.

**Constructor**: Requires Azure OpenAI endpoint, API key, deployment name (from settings or args). Creates `AzureOpenAI` client.

| Method | Description |
|--------|-------------|
| `create_assistant(name, instructions, tools, model)` | Creates assistant via beta.assistants.create |
| `get_assistant(assistant_id)` | Retrieves assistant info |
| `list_assistants(limit)` | Lists all assistants |
| `delete_assistant(assistant_id)` | Deletes assistant |
| `execute_code(assistant_id, code, timeout)` | Full Thread+Run lifecycle: create thread, send message, poll run status, extract result |
| `run_task(assistant_id, task, context, timeout)` | Task-oriented execution (LLM decides the code) |

**Execution Flow** (`execute_code`):
1. Create Thread
2. Send user message with code wrapped in markdown
3. Create Run
4. Poll run status every 1 second until completion/timeout
5. Extract result from assistant messages (text + file annotations + images)

**Issues**:
1. **Uses synchronous Azure OpenAI client**: `AzureOpenAI` (not `AsyncAzureOpenAI`). `time.sleep(1)` polling blocks the event loop in async contexts.
2. **`run_task` passes task description as `code` parameter**: Misleading — the `execute_code` method wraps it in a code execution prompt regardless.
3. **Uses beta Assistants API**: `client.beta.assistants` — this API may change.
4. **No cleanup of threads**: Created threads are never deleted.
5. **API version hardcoded**: `"2024-12-01-preview"` — may need updating.

### 6.4 FileStorageService (`assistant/files.py`, 396 LOC)

**Purpose**: Manage files uploaded to Azure OpenAI for Code Interpreter.

| Method | Description |
|--------|-------------|
| `upload(file, filename, purpose)` | Upload binary file |
| `upload_from_path(path, purpose)` | Upload from file path |
| `upload_from_bytes(content, filename, purpose)` | Upload from bytes |
| `list_files(purpose)` | List files with optional purpose filter |
| `get_file(file_id)` | Get single file info |
| `download(file_id)` | Download file content |
| `download_to_path(file_id, path)` | Download to local path |
| `delete(file_id)` | Delete single file |
| `delete_all(purpose)` | Delete all files with optional filter |

**Supported Extensions**: .csv, .xlsx, .xls, .json, .txt, .py, .md, .pdf, .png, .jpg, .jpeg, .gif, .html, .xml

**Singleton**: `get_file_service()` returns global `FileStorageService` instance.

**Issues**:
1. **Uses synchronous Azure OpenAI client**: Same blocking issue as AssistantManagerService.
2. **Lazy client initialization**: First use triggers import + client creation.
3. **Duplicate `FileInfo` class**: Both `models.py` and `files.py` define `FileInfo` with slightly different fields. The `__init__.py` imports both with alias (`StoredFileInfo`).

---

## 7. Root-Level Infrastructure

### 7.1 Workflow Adapter (`workflow.py`, 591 LOC)

**Class**: `WorkflowAdapter(BuilderAdapter)`

Wraps MAF `WorkflowBuilder` with a simplified, chainable API.

| Method | Returns | Description |
|--------|---------|-------------|
| `register_executor(factory, name)` | self | Register executor factory (lazy init) |
| `add_executor(executor)` | self | Direct executor instance (not recommended) |
| `add_edge(source, target, condition)` | self | Add directed edge |
| `add_fan_out_edges(source, targets)` | self | One-to-many broadcast |
| `add_fan_in_edges(sources, target)` | self | Many-to-one aggregation |
| `add_chain(names)` | self | Sequential chain helper |
| `set_start_executor(id)` | self | Set entry point |
| `build()` | Workflow | Build via official WorkflowBuilder |
| `run(input_data)` | Any | Execute workflow (builds if needed) |
| `run_stream(input_data)` | AsyncIterator | Stream execution |

**Configuration**: `WorkflowConfig` dataclass with id, name, description, max_iterations, enable_checkpointing, checkpoint_storage.

**Build Process**:
1. Creates `WorkflowBuilder` with max_iterations, name, description
2. Registers all executor factories
3. Wraps direct executors as factories
4. Adds all edge types (simple, fan-out, fan-in)
5. Sets start executor
6. Optionally configures checkpointing
7. Calls `builder.build()`

**Issues**:
1. **Direct executors wrapped as factories using closure**: `make_factory(exec_instance)` creates a closure that returns the same instance each time — sharing state between workflow runs.

### 7.2 Exceptions (`exceptions.py`, 400 LOC)

**Hierarchy**:
```
AdapterError (base)
├── AdapterInitializationError (adapter_name)
├── WorkflowBuildError (workflow_id)
├── ExecutionError (workflow_id, executor_id)
├── CheckpointError (checkpoint_id, operation)
├── ValidationError (validation_errors)
├── ConfigurationError (missing_keys, invalid_keys, config_source)
└── RecursionError (max_depth, current_depth, workflow_id)
```

All exceptions include `context` dict, `original_error`, `to_dict()`, and rich `__str__` / `__repr__`.

**Issue**: `RecursionError` shadows Python's built-in `RecursionError`. Should be renamed to avoid confusion (e.g., `WorkflowRecursionError`).

### 7.3 Module Init (`__init__.py`, 167 LOC)

Re-exports from base, exceptions, workflow, checkpoint, and builders submodules. Comments indicate Sprints 15-18 builders were "to be implemented" but are actually implemented in the builders directory (possibly added later without updating comments).

---

## 8. Cross-Reference: Session/Memory/Cache Integration

### Memory Storage (this analysis) vs. Infrastructure Cache (C3 scope)

| Aspect | agent_framework/memory/ | infrastructure/cache/ |
|--------|------------------------|----------------------|
| Purpose | Agent conversation/data memory | General application caching |
| Backends | Redis, PostgreSQL | Redis (likely) |
| Protocol | MemoryStorageProtocol (store/retrieve/search/delete) | Cache-specific interface |
| Namespace | Yes, string prefix | Unknown |
| TTL | Yes, configurable | Likely yes |
| Search | Keyword (Redis brute-force, Postgres ILIKE) | Likely key-based only |

### Multi-turn Checkpoint vs. Root Checkpoint Module

| Aspect | multiturn/checkpoint_storage.py | checkpoint.py (C1 scope) |
|--------|-------------------------------|--------------------------|
| API | Custom (save/load/delete) | Official (save_checkpoint/load_checkpoint) |
| Backends | Redis, Postgres, File | Postgres, Redis+Postgres cached |
| Compatibility | **BROKEN** with MultiTurnAdapter | Works with official API |
| Sprint | S24-3 | S13-3 |

**Migration Gap**: The multiturn checkpoint backends were created at Sprint 24 but never migrated to the official CheckpointStorage API that MultiTurnAdapter now uses.

---

## 9. Problems Summary

### Critical

| ID | Location | Issue |
|----|----------|-------|
| P2-01 | `multiturn/checkpoint_storage.py` | **API mismatch**: RedisCheckpointStorage, PostgresCheckpointStorage, FileCheckpointStorage implement save/load/delete instead of official save_checkpoint/load_checkpoint/delete_checkpoint. Cannot be used with MultiTurnAdapter. |
| P2-02 | `multiturn/adapter.py:856` | `create_redis_multiturn_adapter()` raises NotImplementedError — no persistent multi-turn storage works |
| P2-03 | `exceptions.py:354` | `RecursionError` shadows Python built-in `RecursionError` |

### High

| ID | Location | Issue |
|----|----------|-------|
| P2-04 | `memory/postgres_storage.py` | SQL injection risk: `search_by_jsonb_path()` builds SQL from user input without parameterization |
| P2-05 | `assistant/manager.py` | Synchronous `AzureOpenAI` client with `time.sleep(1)` polling blocks async event loop |
| P2-06 | `tools/code_interpreter_tool.py:211` | `self._adapter.execute()` called synchronously in async method |
| P2-07 | `multiturn/checkpoint_storage.py` | FileCheckpointStorage uses blocking `open()` in async methods |

### Medium

| ID | Location | Issue |
|----|----------|-------|
| P2-08 | `memory/redis_storage.py:339` | `get_keys()` uses `KEYS` command (blocks Redis in production) |
| P2-09 | `memory/redis_storage.py` | Search index methods are empty stubs (`pass`) despite `search_index_enabled` flag |
| P2-10 | `memory/postgres_storage.py`, `multiturn/checkpoint_storage.py` | f-string SQL table name interpolation (safe now but fragile) |
| P2-11 | `assistant/files.py` + `assistant/models.py` | Duplicate `FileInfo` class definitions |
| P2-12 | Multiple files | `datetime.utcnow()` deprecated in Python 3.12+ |
| P2-13 | `multiturn/checkpoint_storage.py:369` | FileCheckpointStorage default path `/tmp/checkpoints` is Unix-specific |
| P2-14 | `assistant/manager.py` | Created threads never cleaned up |
| P2-15 | `__init__.py` | Stale comments about "to be implemented" builders |

### Low

| ID | Location | Issue |
|----|----------|-------|
| P2-16 | `memory/base.py:26` | `Context`, `ContextProvider` imported from agent_framework but never used in logic |
| P2-17 | `acl/version_detector.py` | Only 2 MAF versions in hardcoded compatibility map |
| P2-18 | `tools/code_interpreter_tool.py` | Chart always saved to `chart.png` — no uniqueness |

---

## 10. Recommendations

### Immediate (Critical Fixes)

1. **Migrate multiturn checkpoint backends to official API**: Implement `save_checkpoint()`, `load_checkpoint()`, `delete_checkpoint()` in RedisCheckpointStorage, PostgresCheckpointStorage, and FileCheckpointStorage. This unblocks persistent multi-turn sessions.

2. **Rename `RecursionError`**: Change to `WorkflowRecursionError` to avoid shadowing Python built-in.

3. **Fix SQL injection in `search_by_jsonb_path()`**: Validate/whitelist path components, or use parameterized jsonpath queries.

### Short-term

4. **Switch to AsyncAzureOpenAI in assistant module**: Replace synchronous client and polling with async client to avoid blocking event loop.

5. **Replace `KEYS` with `SCAN` in `get_keys()`**: Already using SCAN pattern elsewhere in RedisMemoryStorage.

6. **Use `aiofiles` for FileCheckpointStorage**: Replace blocking `open()` with async file I/O.

### Medium-term

7. **Integrate RediSearch**: Replace brute-force SCAN+mget search with Redis Search module for production-grade memory search.

8. **Consolidate `FileInfo` classes**: Merge the duplicate definitions into a single shared model.

9. **Add thread safety**: At minimum, use `asyncio.Lock` for shared mutable state in MultiTurnAdapter and ContextManager.

---

## 11. File Inventory

| File | LOC | Sprint | Key Classes |
|------|-----|--------|-------------|
| `memory/base.py` | 453 | S22 | MemoryStorageProtocol, BaseMemoryStorageAdapter, MemoryRecord |
| `memory/redis_storage.py` | 483 | S22 | RedisMemoryStorage |
| `memory/postgres_storage.py` | 670 | S22 | PostgresMemoryStorage |
| `memory/__init__.py` | 70 | S22 | Re-exports |
| `tools/base.py` | 345 | S38 | BaseTool, ToolResult, ToolSchema, ToolRegistry |
| `tools/code_interpreter_tool.py` | 415 | S38 | CodeInterpreterTool |
| `tools/__init__.py` | 62 | S38 | register_default_tools() |
| `acl/interfaces.py` | 267 | S128 | AgentConfig, WorkflowResult, AgentBuilderInterface, AgentRunnerInterface, ToolInterface |
| `acl/version_detector.py` | 229 | S128 | MAFVersionDetector, MAFVersionInfo |
| `acl/adapter.py` | 235 | S128 | MAFAdapter, get_maf_adapter() |
| `acl/__init__.py` | 47 | S128 | Re-exports |
| `multiturn/adapter.py` | 861 | S24 | MultiTurnAdapter, ContextManager, TurnTracker, Message, SessionState |
| `multiturn/checkpoint_storage.py` | 492 | S24 | RedisCheckpointStorage, PostgresCheckpointStorage, FileCheckpointStorage |
| `multiturn/__init__.py` | 52 | S24 | Re-exports |
| `assistant/models.py` | 147 | S38 | CodeExecutionResult, AssistantConfig, AssistantInfo, FileInfo |
| `assistant/exceptions.py` | 168 | S38 | AssistantError hierarchy (8 exception types) |
| `assistant/manager.py` | 415 | S38 | AssistantManagerService |
| `assistant/files.py` | 396 | S38 | FileStorageService, get_file_service() |
| `assistant/__init__.py` | 96 | S38 | Re-exports |
| `workflow.py` | 591 | S13 | WorkflowAdapter, WorkflowConfig, EdgeConfig |
| `exceptions.py` | 400 | S13 | AdapterError hierarchy (7 exception types) |
| `__init__.py` | 167 | S13 | Module re-exports |
