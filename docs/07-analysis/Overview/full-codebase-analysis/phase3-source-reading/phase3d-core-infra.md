# Phase 3D: Core, Infrastructure, Middleware & main.py — Full Analysis

> Agent D1 | Full codebase analysis of the IPA Platform foundation layers
> Files analyzed: 68 Python files across 4 directories
> Date: 2026-03-15

---

## Table of Contents

1. [Summary Statistics](#1-summary-statistics)
2. [main.py — Application Entry Point](#2-mainpy--application-entry-point)
3. [core/ — Configuration, Auth, Security, Sandbox, Logging, Observability, Performance](#3-core)
4. [infrastructure/ — Database, Cache, Storage, Messaging, Checkpoint, Distributed Lock](#4-infrastructure)
5. [middleware/ — Rate Limiting](#5-middleware)
6. [Cross-Reference Matrix](#6-cross-reference-matrix)
7. [Findings and Observations](#7-findings-and-observations)

---

## 1. Summary Statistics

| Directory | .py Files | Estimated Total Lines | Key Classes/Functions |
|-----------|-----------|----------------------|----------------------|
| `backend/main.py` | 1 | 333 | `create_app`, `register_routes`, `lifespan` |
| `backend/src/core/` | 34 | ~3,800 | 45+ classes, 80+ functions |
| `backend/src/infrastructure/` | 39 | ~3,100 | 30+ classes, 60+ functions |
| `backend/src/middleware/` | 2 | ~80 | `setup_rate_limiting`, `limiter` |
| **Total** | **76** | **~7,300** | **75+ classes, 140+ functions** |

---

## 2. main.py — Application Entry Point

**File**: `backend/main.py` (333 lines)

### 2.1 Module-Level Setup
- **Version**: `__version__ = "0.2.0"`
- Imports `get_settings()` from `src.core.config`
- Conditionally sets up structured logging (structlog) if `structured_logging_enabled` is True; otherwise uses basic `logging.basicConfig`
- Holds a module-level `_otel_shutdown` callback for OpenTelemetry teardown

### 2.2 `lifespan(app)` — Async Context Manager
**Startup sequence**:
1. Logs version and environment
2. `settings.validate_security_settings()` — warns in dev, raises in production for unsafe secret_key/jwt_secret_key
3. **OpenTelemetry init** (Sprint 122) — calls `setup_observability()` if `otel_enabled`
4. **Database init** — calls `init_db()` from `infrastructure.database.session`; in dev continues on failure, in production raises
5. **Agent Service init** — calls `init_agent_service()` from `domain.agents.service`; continues on failure (mock mode fallback)

**Shutdown sequence**:
1. `close_db()` — close database connections
2. `agent_service.shutdown()` — shutdown agent service
3. `_otel_shutdown()` — shutdown OpenTelemetry

### 2.3 `create_app()` — FastAPI Factory
- Creates `FastAPI(title="IPA Platform API", lifespan=lifespan, redirect_slashes=False)`
- API docs conditional on `settings.enable_api_docs`
- **Middleware stack** (order matters):
  1. `RequestIdMiddleware` — adds request ID (from `core.logging.middleware`)
  2. `CORSMiddleware` — configured from `settings.cors_origins_list`, all methods/headers allowed, credentials=True
- **Global exception handler**: returns `detail` in dev, generic message in production
- **Rate limiting**: `setup_rate_limiting(app)` from `middleware.rate_limit`
- Calls `register_routes(app)`

### 2.4 `register_routes(app)`
- `GET /` — root info endpoint (service name, version, status)
- `GET /health` — health check: tests DB connectivity (`SELECT 1`), tests Redis connectivity (`ping`), returns overall status
- `GET /ready` — simple readiness probe
- Includes `api_router` from `src.api.v1`

### 2.5 App Instance
- `app = create_app()` at module level
- `if __name__ == "__main__"`: uses `ServerConfig` for uvicorn configuration

### 2.6 Cross-References
- Depends on: `core.config`, `core.logging`, `core.observability`, `core.server_config`, `infrastructure.database.session`, `domain.agents.service`, `middleware.rate_limit`, `api.v1`
- Health check directly uses `os.environ` for Redis config (NOTE: should use `get_settings()` per project rules)

---

## 3. core/

### 3.1 `core/__init__.py` (6 lines)
Exports: `Settings`, `get_settings`

---

### 3.2 `core/config.py` (223 lines) — Centralized Configuration

**Class**: `Settings(BaseSettings)` using Pydantic v2 `SettingsConfigDict`
- `env_file=".env"`, `case_sensitive=False`, `extra="ignore"`

**Configuration Groups**:

| Group | Settings | Defaults |
|-------|----------|----------|
| **Application** | `app_env` (dev/staging/prod), `log_level`, `secret_key` | "development", "INFO", "" |
| **PostgreSQL** | `db_host`, `db_port`, `db_name`, `db_user`, `db_password` | localhost:5432/ipa_platform/ipa_user/"" |
| **Redis** | `redis_host`, `redis_port`, `redis_password` | localhost:6379/"" |
| **RabbitMQ** | `rabbitmq_host`, `rabbitmq_port`, `rabbitmq_user`, `rabbitmq_password` | localhost:5672/guest/guest |
| **Azure OpenAI** | `azure_openai_endpoint`, `azure_openai_api_key`, `azure_openai_deployment_name`, `azure_openai_api_version` | ""/""/gpt-5.2/2024-02-15-preview |
| **LLM Service** | `llm_enabled`, `llm_provider` (azure/mock), `llm_max_retries`, `llm_timeout_seconds`, `llm_cache_enabled`, `llm_cache_ttl_seconds` | True/azure/3/60.0/True/3600 |
| **Azure Service Bus** | `azure_service_bus_connection_string` | "" |
| **JWT** | `jwt_secret_key`, `jwt_algorithm`, `jwt_access_token_expire_minutes` | ""/HS256/60 |
| **CORS** | `cors_origins` | "http://localhost:3005,http://localhost:8000" |
| **Feature Flags** | `feature_workflow_enabled`, `feature_agent_enabled`, `feature_checkpoint_enabled` | All True |
| **Dev Settings** | `enable_api_docs`, `enable_sql_logging` | True/False |
| **Observability** (Sprint 122) | `otel_enabled`, `otel_service_name`, `otel_exporter_otlp_endpoint`, `otel_sampling_rate`, `applicationinsights_connection_string` | False/"ipa-platform"/localhost:4317/1.0/"" |
| **Structured Logging** (Sprint 122) | `structured_logging_enabled` | False |

**Computed Properties**:
- `database_url` — async PostgreSQL URL (`postgresql+asyncpg://...`)
- `database_url_sync` — sync URL for Alembic
- `redis_url` — with optional password
- `rabbitmq_url` — AMQP URL
- `is_azure_openai_configured` — bool check
- `is_llm_enabled` — checks both `llm_enabled` flag and provider config
- `use_azure_service_bus` — bool check
- `cors_origins_list` — parsed comma-separated origins

**Validators**:
- `validate_log_level` — enforces valid log levels
- `validate_security_settings()` — instance method checking `secret_key` and `jwt_secret_key` against known unsafe values; warns in dev, raises `ValueError` in production

**`get_settings()`** — `@lru_cache()` singleton factory

---

### 3.3 `core/auth.py` (115 lines) — Global JWT Auth Dependency

**Sprint 111**: S111-7 — Global Auth Middleware

**Key Components**:
- `security = HTTPBearer(auto_error=True)` — mandatory JWT extraction
- `security_optional = HTTPBearer(auto_error=False)` — optional JWT extraction

**`require_auth(credentials)`** — FastAPI dependency:
- Decodes JWT using `jose.jwt.decode()` with `settings.jwt_secret_key` and `settings.jwt_algorithm`
- Extracts `sub` (user_id), `role` (default "viewer"), `email`, `exp`, `iat`
- Returns dict (NOT a User model — lightweight, no DB lookup)
- Raises `HTTPException(401)` on missing `sub` or `JWTError`

**`require_auth_optional(credentials)`** — returns `None` if no token provided, swallows `HTTPException`

**Design Note**: This is intentionally lightweight (no DB). For full User model with DB lookup, use `src.api.v1.dependencies.get_current_user`.

---

### 3.4 `core/factories.py` (188 lines) — Service Factory

**Sprint 112**: S112-2 — Environment-Aware Service Factory

**Class**: `ServiceFactory` (class-level registry pattern)

**Methods**:
- `register(service_name, real_factory, mock_factory)` — registers both implementations
- `create(service_name, **kwargs)` — environment-aware creation:
  - `testing`: mock directly
  - `production`: real only, `RuntimeError` on failure
  - `development`: real preferred, WARNING + mock fallback
- `is_registered()`, `list_services()`, `clear()`, `get_environment()`

**`register_orchestration_services()`** — registers 3 services:
1. `business_intent_router` — `create_router` / mock
2. `guided_dialog_engine` — `create_guided_dialog_engine` / mock
3. `hitl_controller` — `create_hitl_controller` / mock

Mock factories use lazy imports from `tests.mocks.orchestration`.

---

### 3.5 `core/server_config.py` (147 lines) — Uvicorn/Gunicorn Configuration

**Sprint 117**: Multi-Worker Uvicorn Configuration

**Enum**: `ServerEnvironment` — DEVELOPMENT, STAGING, PRODUCTION

**Class**: `ServerConfig`
- `workers`: 1 in dev; `CPU * 2 + 1` capped at 8 in staging/prod; `UVICORN_WORKERS` env override
- `reload`: True only in dev
- `host`: `SERVER_HOST` env, default "0.0.0.0"
- `port`: `SERVER_PORT` env, default 8000
- `log_level`: "debug" in dev, "info" otherwise
- `access_log`: disabled in production
- `worker_class`: "uvicorn.workers.UvicornWorker"
- `bind`: "{host}:{port}" for Gunicorn

---

### 3.6 `core/sandbox_config.py` (322 lines) — Per-User Sandbox Directory Isolation

**Sprint 68**: S68-1 — Sandbox Directory Structure

**Class**: `SandboxConfig`

**Directory Structure**:
```
data/
├── uploads/{user_id}/   # User uploaded files
├── sandbox/{user_id}/   # Agent working directory
├── outputs/{user_id}/   # Agent generated outputs
└── temp/                # Temporary (no user scope)
```

**Constants**:
- `MAX_UPLOAD_SIZE`: 10MB
- `ALLOWED_EXTENSIONS`: .txt, .md, .csv, .json, .xml, .yaml, .yml, .pdf, .docx, .xlsx, .pptx, .png, .jpg, .jpeg, .gif, .svg, .webp, .log, .html, .css, .sql
- `CLEANUP_AGE_DAYS`: 30

**Methods**:
- `get_user_dir(user_id, dir_type)` — returns absolute path with sanitized user_id
- `ensure_user_dirs(user_id)` — creates all user directories
- `get_user_file_path(user_id, dir_type, filename)` — sanitized path
- `is_valid_extension(filename)` — allowlist check
- `cleanup_inactive_users(max_age_days)` — removes old directories
- `get_user_storage_usage(user_id)` — calculates disk usage
- `_sanitize_user_id(user_id)` — prevents path traversal (strips `/`, `\`, `..`, allows `[a-zA-Z0-9\-_]`)
- `_sanitize_filename(filename)` — strips path components, sanitizes characters

**`init_sandbox_directories()`** — creates base structure with `.gitkeep` files

---

### 3.7 `core/security/` — JWT & Password Utilities

#### 3.7.1 `security/__init__.py` (32 lines)
Exports: `create_access_token`, `decode_token`, `TokenPayload`, `hash_password`, `verify_password`

#### 3.7.2 `security/jwt.py` (~130 lines)

**Sprint 70**: S70-1 — JWT Utilities, Phase 18: Authentication System

**Class**: `TokenPayload(BaseModel)` — `sub`, `role`, `exp`, `iat`

**Functions**:
- `create_access_token(user_id, role, expires_delta=None)` — creates HS256 JWT with `sub`, `role`, `exp`, `iat`; default expiry from `settings.jwt_access_token_expire_minutes`
- `decode_token(token)` — decodes and returns `TokenPayload`; raises `JWTError` on failure

#### 3.7.3 `security/password.py` (58 lines)

Uses `passlib.context.CryptContext` with bcrypt scheme.

**Functions**:
- `hash_password(password)` — bcrypt hash
- `verify_password(plain_password, hashed_password)` — bcrypt verify

#### 3.7.4 `security/audit_report.py` (~500 lines)

**Class**: `SecurityAuditReport` — Comprehensive security audit report generator

**Enums**: `Severity` (critical/high/medium/low/info), `ComplianceStatus` (pass/fail/partial/n/a)

**Data Classes**:
- `Vulnerability` — id, package, severity, description, fix_version, cve_id
- `ComplianceCheck` — id, name, status, details, recommendations

**`SecurityAuditReport`** fields:
- `generated_at`, `vulnerabilities`, `owasp_compliance`, `authentication_review`, `authorization_review`, `data_protection_review`, `summary`

**Key Method**: `generate()` — runs `pip-audit` subprocess for dependency scanning, performs OWASP Top 10 compliance checks, reviews auth/authz/data protection settings. Produces markdown report via `to_markdown()`.

**Static assessment data includes**:
- JWT validation: HS256, 1-hour expiry, refresh token support
- Password policy: min 12 chars, bcrypt, complexity required
- Login protection: rate limiting, max 5 attempts, 15-min lockout
- Data encryption: TLS 1.3, Azure Key Vault for credentials
- Audit log retention: 7 years

---

### 3.8 `core/sandbox/` — Process-Level Isolation for Agent Execution

**Sprint 77-78**: Phase 21 — Sandbox Security Architecture

**Architecture**:
```
Main Process                    Sandbox Process
├── API Layer           ──►     ├── ClaudeSDKClient
├── SandboxOrchestrator ◄──     ├── Tool Executor
│   └── IPC (JSON-RPC)          └── Hook Handler
├── DB Connection        X
└── Redis Connection     X      (No access to sensitive resources)
```

#### 3.8.1 `sandbox/__init__.py` (92 lines)
Exports all components from config, orchestrator, worker, ipc, adapter modules.

#### 3.8.2 `sandbox/config.py` (~250 lines) — `ProcessSandboxConfig`

**Dataclass** with env-var defaults:
- `sandbox_base_dir`: `SANDBOX_BASE_DIR` or "data/sandbox"
- `max_workers`: `SANDBOX_MAX_WORKERS` or 10
- `worker_timeout`: `SANDBOX_WORKER_TIMEOUT` or 300s
- `startup_timeout`: `SANDBOX_STARTUP_TIMEOUT` or 30s
- `idle_timeout`: `SANDBOX_IDLE_TIMEOUT` or 600s
- `max_requests_per_worker`: `SANDBOX_MAX_REQUESTS` or 100
- `allowed_env_vars`: explicit allowlist (AZURE_OPENAI_*, ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.)
- `blocked_env_prefix`: always blocked (`DB_`, `REDIS_`, `RABBITMQ_`, `JWT_`, `SECRET_`)

**Key Method**: `get_filtered_env()` — returns sanitized environment dict for subprocess, only including allowed vars, blocking sensitive prefixes.

#### 3.8.3 `sandbox/orchestrator.py` (~430 lines) — `SandboxOrchestrator`

**Dataclass**: `WorkerInfo` — tracks worker, user_id, created_at, last_used_at, request_count, is_busy

**Class**: `SandboxOrchestrator` — manages worker process pool
- **Pool management**: `_workers: Dict[str, WorkerInfo]`, uses asyncio.Lock
- **User affinity**: prefers existing idle worker for same user_id
- **Methods**:
  - `execute(user_id, message, attachments, session_id)` — routes to available/new worker
  - `stream(user_id, message, attachments, session_id)` — async iterator for streaming
  - `_get_or_create_worker(user_id)` — finds idle worker or creates new
  - `_cleanup_idle_workers()` — removes workers exceeding idle_timeout
  - `shutdown()` — graceful shutdown of all workers
  - `get_pool_stats()` — returns pool utilization metrics

#### 3.8.4 `sandbox/worker.py` (~370 lines) — `SandboxWorker`

Manages individual sandbox subprocess via `subprocess.Popen()`.

**Communication**: JSON-RPC 2.0 over stdin/stdout
- `start()` — spawns `worker_main.py` with filtered env vars
- `execute(message, attachments, session_id)` — sends request, reads response
- `stream(message, attachments, session_id)` — async iterator for streaming events
- `stop()` — graceful shutdown via IPC, then force kill
- `_build_env()` — uses `config.get_filtered_env()` to restrict subprocess environment

#### 3.8.5 `sandbox/worker_main.py` (~300 lines)

The script that runs inside the sandbox subprocess:
- Reads JSON-RPC requests from stdin
- Dispatches to Claude SDK client for execution
- Writes responses/events to stdout
- Handles `execute`, `shutdown`, `ping` methods

#### 3.8.6 `sandbox/ipc.py` (~370 lines) — IPC Protocol

**Enums**:
- `IPCEventType` — TEXT_DELTA, TEXT_COMPLETE, TOOL_CALL_START/DELTA/COMPLETE/RESULT, HITL_REQUEST/RESPONSE, RUN_STARTED/COMPLETE/ERROR, COMPLETE, ERROR, HEARTBEAT
- `IPCMethod` — EXECUTE, SHUTDOWN, PING, EVENT

**Dataclasses**:
- `IPCRequest` — method, params, id (JSON-RPC 2.0 format)
- `IPCResponse` — result, error, id
- `IPCEvent` — type, data, timestamp; has `to_sse_event()` for frontend

**Error Hierarchy**: `IPCError` > `IPCTimeoutError`, `IPCConnectionError`, `IPCProtocolError`

**Utility Functions**: `create_error_response()`, `create_success_response()`, `create_event_notification()`, `map_ipc_to_sse_event()`

**Class**: `IPCProtocol` — handles serialization/deserialization, reading lines from process stdout, writing to stdin

#### 3.8.7 `sandbox/adapter.py` (~280 lines) — High-Level Sandbox API

Module-level convenience functions:
- `is_sandbox_enabled()` — checks `SANDBOX_ENABLED` env var
- `get_sandbox_orchestrator()` — singleton orchestrator
- `shutdown_sandbox_orchestrator()` — cleanup
- `execute_in_sandbox(user_id, message, ...)` — one-shot execution
- `stream_in_sandbox(user_id, message, ...)` — streaming execution
- `get_orchestrator_stats()` — pool metrics
- `on_startup()` / `on_shutdown()` — lifespan hooks

**Dataclass**: `SandboxExecutionContext` — bundles user_id, message, attachments, session_id

---

### 3.9 `core/logging/` — Structured Logging

**Sprint 122**: Story 122-3

#### 3.9.1 `logging/__init__.py` (22 lines)
Exports: `setup_logging`, `get_logger`

#### 3.9.2 `logging/setup.py` (~140 lines)

**`setup_logging(json_output, log_level, enable_otel_correlation)`**:
- Configures structlog with processor chain:
  1. `merge_contextvars` — merge context variables
  2. `filter_by_level` — log level filtering
  3. `add_logger_name`, `add_log_level` — standard fields
  4. `TimeStamper(fmt="iso")` — ISO timestamps
  5. `_add_request_id` — injects request_id from ContextVar
  6. `SensitiveInfoFilter()` — masks passwords/secrets/tokens
  7. (optional) `_add_otel_context` — adds trace_id, span_id from OTel
  8. `StackInfoRenderer`, `format_exc_info`
  9. `JSONRenderer` or `ConsoleRenderer`
- Configures stdlib logging to route through structlog

**`get_logger(name)`** — returns structlog bound logger

**`_add_request_id(logger, method_name, event_dict)`** — reads `request_id` ContextVar
**`_add_otel_context(logger, method_name, event_dict)`** — reads OTel trace context

#### 3.9.3 `logging/middleware.py` (~70 lines)

**Class**: `RequestIdMiddleware(BaseHTTPMiddleware)`
- Generates UUID request ID per request
- Sets `X-Request-ID` response header
- Stores in `contextvars.ContextVar` for log correlation
- Reads `X-Request-ID` from incoming request header if present (tracing support)

#### 3.9.4 `logging/filters.py` (~130 lines)

**Sensitive Key Patterns**: password, secret, token, api_key, authorization, credentials, private_key, access_key, session_id (partial match, case-insensitive)

**`_is_sensitive_key(key)`** — checks against patterns
**`_mask_value(value)`** — returns `***REDACTED***`
**`_mask_dict(data)`** — recursively masks sensitive fields
**`_mask_list(data)`** — recursively masks list elements

**Class**: `SensitiveInfoFilter` — structlog processor that masks all sensitive fields in event_dict before rendering

---

### 3.10 `core/observability/` — OpenTelemetry + Azure Monitor

**Sprint 122**: Story 122-2

#### 3.10.1 `observability/__init__.py` (35 lines)
Exports: `setup_observability`, `create_span`, `record_agent_execution`, `record_llm_call`, `record_mcp_tool_call`, `get_tracer`, `get_meter`, `IPA_METRICS`

#### 3.10.2 `observability/setup.py` (~220 lines)

**`setup_observability(service_name, connection_string, otel_enabled, sampling_rate)`**:
1. Creates `Resource` with service name and version
2. Sets up `TracerProvider` with `BatchSpanProcessor`
3. Sets up `MeterProvider` with `PeriodicExportingMetricReader`
4. If `connection_string` provided: uses Azure Monitor exporters (`AzureMonitorTraceExporter`, `AzureMonitorMetricExporter`)
5. If not: uses OTLP or console exporters for local dev
6. Auto-instruments: FastAPI, httpx, Redis, asyncpg
7. Returns shutdown callback function

**`get_tracer()`** / **`get_meter()`** — return initialized or no-op instances

#### 3.10.3 `observability/spans.py` (~220 lines)

**Context Managers**:
- `create_span(name, attributes, kind)` — generic sync span creator
- `record_agent_execution(agent_id, agent_type, session_id)` — async context manager, records `agent.execute` span with duration metric
- `record_llm_call(provider, model, prompt_tokens, completion_tokens)` — async, records `llm.call` span
- `record_mcp_tool_call(tool_name, server_name)` — async, records `mcp.tool_call` span

All spans automatically set ERROR status and record exceptions on failure.

#### 3.10.4 `observability/metrics.py` (~120 lines)

**Class**: `IPA_METRICS` — pre-configured metric instruments:
- `agent_execution_count` — Counter
- `agent_execution_duration` — Histogram (ms)
- `llm_call_count` — Counter
- `llm_call_duration` — Histogram (ms)
- `llm_token_usage` — Counter (by type: prompt/completion)
- `mcp_tool_call_count` — Counter
- `mcp_tool_call_duration` — Histogram (ms)
- `http_request_count` — Counter
- `http_request_duration` — Histogram (ms)

---

### 3.11 `core/performance/` — Performance Optimization Utilities

**Sprint 12**: Integration & Polish

#### 3.11.1 `performance/__init__.py` (118 lines)
Exports all components from 7 sub-modules.

#### 3.11.2 `performance/middleware.py` (~370 lines)

**Classes**:
- `CompressionMiddleware(BaseHTTPMiddleware)` — Gzip compression for responses > minimum_size (default 500 bytes); compressible content types (JSON, text, XML)
- `TimingMiddleware(BaseHTTPMiddleware)` — adds `X-Response-Time` and `X-Request-ID` headers
- `ETagMiddleware(BaseHTTPMiddleware)` — MD5-based ETag generation and `If-None-Match` support (returns 304)
- `PerformanceMetrics` — collects request latency (P50/P95/P99), throughput, error rates, DB query times

#### 3.11.3 `performance/cache_optimizer.py` (~340 lines)

**Class**: `CacheEntry(Generic[T])` — value, created_at, ttl, access_count, last_accessed; properties: `is_expired`, `age`

**Class**: `MemoryCache` — L1 in-memory LRU cache:
- `max_size` (default 1000), `default_ttl` (default 60s)
- LRU eviction when full
- Hit/miss tracking, `get_stats()`

**Class**: `CacheOptimizer` — Multi-tier caching (Memory L1 + Redis L2):
- `get(key)` — L1 first, then L2, promotes to L1 on L2 hit
- `set(key, value, ttl)` — writes to both tiers
- `invalidate(key)` — removes from both tiers
- `warm(keys, loader)` — pre-populates cache
- `@cached(ttl)` decorator for functions

#### 3.11.4 `performance/db_optimizer.py` (~420 lines)

**Data Class**: `QueryStats` — query, duration_ms, rows_affected, timestamp, is_slow

**Class**: `QueryOptimizer`:
- `slow_query_threshold_ms` (default 100ms)
- `track_query()` — records stats, logs slow queries
- `detect_n1_queries()` — N+1 query pattern detection
- `get_report()` — aggregated query performance report
- `@track` decorator for ORM methods

**Class**: `N1QueryDetector` — detects repeated similar queries within time window

#### 3.11.5 `performance/profiler.py` (~600 lines)

**Enums**: `MetricType` (LATENCY, THROUGHPUT, MEMORY, CPU, CONCURRENCY, ERROR_RATE)

**Dataclasses**:
- `PerformanceMetric` — name, metric_type, value, unit, timestamp, tags
- `ProfileSession` — id, name, started_at, ended_at, metrics, summary
- `OptimizationRecommendation` — type, severity, message, recommendation, metric_value, threshold

**Class**: `PerformanceProfiler`:
- Session-based profiling with `start_session()` / `end_session()`
- `record_metric()` — manual metric recording
- `@measure_latency(name)` — decorator for latency tracking
- Auto-collection mode with background task
- `get_recommendations()` — generates optimization suggestions based on thresholds:
  - Latency avg > 1000ms
  - P99 > 3x average
  - Error rate > 5%
  - Memory > 80%
  - CPU > 70%

#### 3.11.6 `performance/optimizer.py` (~470 lines)

**Enum**: `OptimizationStrategy` — CACHING, BATCHING, CONNECTION_POOLING, QUERY_OPTIMIZATION, ASYNC_PROCESSING, LAZY_LOADING

**Dataclasses**:
- `BenchmarkMetrics` — avg/p95/p99 latency, throughput_rps, error_rate, total/successful requests
- `OptimizationResult` — id, target, baseline, optimized, improvement, applied_strategies

**Class**: `PerformanceOptimizer`:
- `analyze(target, benchmark_fn)` — runs benchmark, identifies bottlenecks
- `optimize(target, strategies, benchmark_fn)` — applies strategies, measures improvement
- `compare(baseline, optimized)` — calculates improvement percentages

#### 3.11.7 `performance/concurrent_optimizer.py` (~500 lines)

**Dataclasses**:
- `ConcurrencyConfig` — max_workers (10), batch_size (50), timeout_seconds (30), semaphore_limit (100), retry_count (3), retry_backoff (1.5)
- `ExecutionResult(Generic[T])` — item, result, error, duration_seconds
- `BatchExecutionStats` — total_items, successful, failed, duration, items_per_second

**Class**: `ConcurrentOptimizer(Generic[T, R])`:
- `execute_batch(items, processor)` — processes items concurrently with semaphore control
- `execute_with_retry(item, processor)` — exponential backoff retry
- `gather_results(tasks)` — collects results preserving order

**Class**: `WorkerPool` — thread pool for CPU-intensive tasks using `ThreadPoolExecutor`

#### 3.11.8 `performance/metric_collector.py` (~570 lines)

**Enums**: `CollectorType` (SYSTEM, APPLICATION, CUSTOM), `AggregationType` (SUM, AVG, MIN, MAX, COUNT, P50, P90, P95, P99)

**Dataclasses**:
- `SystemMetrics` — cpu_percent, cpu_count, memory_total_gb, memory_used_gb, disk usage, network bytes
- `ApplicationMetrics` — request_count, success_count, error_count, latency stats, cache hits/misses
- `MetricSample` — name, value, timestamp, collector_type, tags
- `AggregatedMetric` — name, aggregation_type, value, sample_count, time_range

**Class**: `MetricCollector`:
- `collect_system_metrics()` — uses `psutil` if available
- `record_sample()` — stores metric samples
- `aggregate(name, agg_type, window)` — calculates aggregations
- `start_collection(interval)` — background collection loop
- `get_dashboard_data()` — returns all metrics for display

#### 3.11.9 `performance/benchmark.py` (~580 lines)

**Enums**: `BenchmarkStatus` (PENDING, RUNNING, COMPLETED, FAILED), `ComparisonResult` (FASTER, SLOWER, SIMILAR)

**Dataclasses**:
- `BenchmarkConfig` — name, iterations (100), warmup_iterations (10), timeout_seconds (60), concurrency (1)
- `BenchmarkResult` — config, status, avg/min/max/p50/p95/p99 latency, throughput, error_rate
- `BenchmarkComparison` — baseline, candidate, latency_change_pct, throughput_change_pct, result
- `BenchmarkReport` — results, comparisons, generated_at

**Class**: `BenchmarkRunner`:
- `run(config, target_fn)` — executes benchmark with warmup
- `compare(baseline, candidate)` — generates comparison
- `generate_report(results)` — full report with all comparisons

**Decorator**: `@benchmark(name, iterations)` — wraps function for benchmarking

---

## 4. Infrastructure

### 4.1 `infrastructure/__init__.py` (1 line)
Empty (comment only: `# Messaging infrastructure` — misplaced?)

---

### 4.2 `infrastructure/cache/` — LLM Response Cache

#### 4.2.1 `cache/__init__.py` (22 lines)
Exports: `LLMCache`, `get_llm_cache`

#### 4.2.2 `cache/llm_cache.py` (~470 lines)

**Sprint 14**: LLM Response Caching

**Class**: `LLMCache`:
- **Hash Strategy**: SHA256 of `provider + model + prompt + params` for cache key
- **Storage**: Redis with configurable TTL (default from `settings.llm_cache_ttl_seconds` = 3600s)
- **Key prefix**: `llm_cache:`
- **Methods**:
  - `get(provider, model, prompt, **params)` — lookup by hash
  - `set(provider, model, prompt, response, **params)` — store with TTL
  - `invalidate(provider, model, prompt, **params)` — remove specific entry
  - `clear_all()` — flush all LLM cache entries
  - `get_stats()` — hits, misses, hit_rate, total_keys
- **Serialization**: JSON for both key params and cached responses
- Falls back gracefully if Redis unavailable (returns None on get, silently fails on set)

**`get_llm_cache()`** — singleton factory, returns None if LLM cache disabled or Redis unavailable

---

### 4.3 `infrastructure/database/` — SQLAlchemy ORM

#### 4.3.1 `database/__init__.py` (18 lines)
Exports: `Base`, `init_db`, `close_db`, `get_db`, `get_engine`

#### 4.3.2 `database/session.py` (~130 lines)

- `_engine`: `AsyncEngine` singleton using `create_async_engine(settings.database_url)`
- `_session_factory`: `async_sessionmaker` bound to engine
- `init_db()` — creates engine and runs `Base.metadata.create_all()` (auto-creates tables)
- `close_db()` — disposes engine
- `get_engine()` — returns engine instance
- `get_db()` — async generator yielding `AsyncSession` (with commit on success, rollback on error)

#### 4.3.3 Database Models (`database/models/`)

**`models/__init__.py`** (38 lines) — exports all models

**`models/base.py`** (55 lines):
- `Base(DeclarativeBase)` — SQLAlchemy declarative base
- `TimestampMixin` — provides `created_at` and `updated_at` columns (server-side defaults)
- `id` column: `UUID` primary key with `uuid4` default

**`models/agent.py`** (~110 lines) — `Agent(Base, TimestampMixin)`:

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| name | String(100) | unique, not null |
| description | Text | nullable |
| category | String(50) | default "general" |
| status | String(20) | default "active" |
| config | JSON | agent configuration |
| capabilities | JSON | agent capabilities |
| created_by | UUID | FK to users (nullable) |

**`models/workflow.py`** (~140 lines) — `Workflow(Base, TimestampMixin)`:

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| name | String(200) | not null |
| description | Text | nullable |
| status | String(20) | default "draft" |
| trigger_type | String(50) | default "manual" |
| steps | JSON | workflow step definitions |
| config | JSON | workflow configuration |
| version | Integer | default 1 |
| created_by | UUID | FK to users (nullable) |

**`models/execution.py`** (~160 lines) — `Execution(Base, TimestampMixin)`:

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| workflow_id | UUID | FK to workflows |
| agent_id | UUID | FK to agents (nullable) |
| status | String(20) | default "pending" |
| input_data | JSON | execution input |
| output_data | JSON | execution output |
| error | Text | error message |
| started_at | DateTime | nullable |
| completed_at | DateTime | nullable |
| llm_calls | Integer | default 0 |
| llm_tokens | Integer | default 0 |
| llm_cost | Numeric(10,6) | default 0 |
| triggered_by | UUID | FK to users (nullable) |

**`models/session.py`** (~200 lines) — `Session(Base, TimestampMixin)`:

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | String(100) | not null |
| title | String(200) | nullable |
| status | String(20) | default "active" |
| metadata_ | JSON | session metadata (column name "metadata") |
| messages | JSON | conversation messages array |
| agent_id | UUID | nullable |
| last_activity_at | DateTime | nullable |

**`models/user.py`** (~100 lines) — `User(Base, TimestampMixin)`:

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| email | String(255) | unique, not null |
| hashed_password | String(255) | not null |
| display_name | String(100) | nullable |
| role | String(20) | default "viewer" |
| is_active | Boolean | default True |
| last_login_at | DateTime | nullable |

**`models/audit.py`** (~120 lines) — `AuditLog(Base, TimestampMixin)`:

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| action | String(100) | not null |
| resource_type | String(50) | not null |
| resource_id | String(100) | nullable |
| user_id | UUID | FK to users (nullable) |
| details | JSON | audit details |
| ip_address | String(45) | nullable |

**`models/checkpoint.py`** (~150 lines) — `Checkpoint(Base, TimestampMixin)`:

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| execution_id | UUID | FK to executions |
| checkpoint_type | String(50) | default "approval" |
| status | String(20) | default "pending" |
| title | String(200) | nullable |
| description | Text | nullable |
| data | JSON | checkpoint payload |
| response | JSON | approval response |
| responded_by | UUID | FK to users (nullable) |
| responded_at | DateTime | nullable |
| expires_at | DateTime | nullable |

#### 4.3.4 Repositories (`database/repositories/`)

**`repositories/__init__.py`** (22 lines) — exports all repositories

**`repositories/base.py`** (~180 lines) — `BaseRepository(Generic[ModelT])`:
- `create(**kwargs)` — INSERT + flush + refresh
- `get(id)` — SELECT by UUID
- `get_by(**kwargs)` — SELECT by arbitrary fields
- `list(page, page_size, order_by, order_desc, **filters)` — paginated SELECT with filtering
- `update(id, **kwargs)` — UPDATE by UUID
- `delete(id)` — DELETE by UUID
- Returns `Tuple[List[ModelT], int]` for list operations (items + total count)

**`repositories/agent.py`** (~130 lines) — `AgentRepository(BaseRepository[Agent])`:
- `get_by_name(name)` — unique lookup
- `get_by_category(category)` — filtered list
- `get_active()` — status="active" filter
- `search(query)` — ILIKE on name and description

**`repositories/workflow.py`** (~160 lines) — `WorkflowRepository(BaseRepository[Workflow])`:
- `get_by_trigger_type(trigger_type)` — filtered list
- `get_active()` — status="active" filter
- `get_by_creator(user_id)` — created_by filter
- `search(query)` — ILIKE on name and description
- `activate(id)` / `deactivate(id)` — status management
- `increment_version(id)` — bumps version counter

**`repositories/execution.py`** (~250 lines) — `ExecutionRepository(BaseRepository[Execution])`:
- `get_by_workflow(workflow_id, status)` — filtered list
- `get_by_status(status)` — status filter
- `get_running()` — status="running" filter
- `update_stats(id, llm_calls, llm_tokens, llm_cost)` — LLM metrics update
- `complete(id, output_data, ...)` — mark completed with stats
- `fail(id, error, ...)` — mark failed with error
- `cancel(id)` — mark cancelled

**`repositories/checkpoint.py`** (~250 lines) — `CheckpointRepository(BaseRepository[Checkpoint])`:
- `get_pending(limit, execution_id)` — pending checkpoints ordered by created_at
- `get_by_execution(execution_id)` — all checkpoints for execution
- `list_by_execution(execution_id, page, page_size)` — paginated
- `update_status(id, status, response, responded_by)` — approve/reject
- `expire_old(before_date)` — mark old pending checkpoints as expired

**`repositories/user.py`** (~80 lines) — `UserRepository(BaseRepository[User])`:
- `get_by_email(email)` — unique email lookup
- `get_active_by_email(email)` — email + is_active=True

---

### 4.4 `infrastructure/messaging/` — Message Queue

**`messaging/__init__.py`** (1 line): `# Messaging infrastructure`

**CONFIRMED**: Only a 1-line comment. No RabbitMQ or Azure Service Bus implementation exists. The `Settings` class defines RabbitMQ and Azure Service Bus configuration, but the infrastructure module is entirely a stub.

---

### 4.5 `infrastructure/redis_client.py` (~140 lines) — Centralized Redis Client

**Sprint 119**: Centralized Redis Client Factory

- Module-level singletons: `_redis_client`, `_redis_pool`
- **`get_redis_client()`** — creates `ConnectionPool.from_url()` on first call:
  - `max_connections=20`
  - `decode_responses=True`
  - `socket_connect_timeout=5`, `socket_timeout=5`
  - `retry_on_timeout=True`
  - Verifies with `ping()`
  - Returns `None` if `redis_host` is empty or connection fails
- **`close_redis_client()`** — closes pool and client
- **`is_redis_available()`** — checks if client exists and can ping

---

### 4.6 `infrastructure/storage/` — Dual-Backend Storage

**Sprint 119**: Unified Storage Abstraction

#### 4.6.1 `storage/__init__.py` (27 lines)
Exports: `StorageBackend`, `RedisStorageBackend`, `InMemoryStorageBackend`, `create_storage_backend`

#### 4.6.2 `storage/protocol.py` (~100 lines) — `StorageBackend(Protocol)`

Runtime-checkable protocol defining:
- `prefix` property — namespace isolation
- `get(key)` → `Optional[Any]`
- `set(key, value, ttl=None)` → `None`
- `delete(key)` → `bool`
- `exists(key)` → `bool`
- `list_keys(pattern="*")` → `List[str]`
- `set_add(key, *members)` → `int`
- `set_remove(key, *members)` → `int`
- `set_members(key)` → `set[str]`
- `clear_all()` → `int`

#### 4.6.3 `storage/memory_backend.py` (~170 lines) — `InMemoryStorageBackend`

In-memory implementation with TTL support:
- Dict-based storage with `_data: Dict[str, Any]`
- TTL tracking via `_expiry: Dict[str, float]`
- Set operations via separate `_sets: Dict[str, set]`
- `_cleanup_expired()` — lazy cleanup on access
- Thread-safe via asyncio patterns (single-threaded event loop)

#### 4.6.4 `storage/redis_backend.py` (~230 lines) — `RedisStorageBackend`

Redis implementation with JSON serialization:
- Uses centralized `get_redis_client()`
- Key prefixing: `{prefix}:{key}`
- JSON serialize/deserialize for values
- Full set operation support via Redis SADD/SREM/SMEMBERS
- `list_keys()` uses SCAN (not KEYS) for production safety
- `clear_all()` uses SCAN + DELETE in batches

#### 4.6.5 `storage/factory.py` (~100 lines)

**`create_storage_backend(prefix, backend=None, default_ttl=None)`**:
- `backend` or `STORAGE_BACKEND` env: "redis" | "memory" | "auto"
- Auto behavior:
  - `production`: Redis required, raises `RuntimeError` if unavailable
  - `testing`: InMemory directly
  - `development`: Redis preferred, InMemory fallback with WARNING

#### 4.6.6 `storage/storage_factories.py` (~290 lines)

Additional specialized storage factories:
- `create_session_storage()` — storage for chat sessions
- `create_approval_storage()` — storage for HITL approvals
- `create_metrics_storage()` — storage for metrics data
- `create_agent_state_storage()` — storage for agent state
- Each uses domain-specific prefix and TTL defaults

---

### 4.7 `infrastructure/distributed_lock/` — Redis Distributed Locking

**Sprint 119**: Distributed Lock Support

#### 4.7.1 `distributed_lock/__init__.py` (18 lines)
Exports: `DistributedLock`, `RedisDistributedLock`, `InMemoryLock`, `create_distributed_lock`

#### 4.7.2 `distributed_lock/redis_lock.py` (~210 lines)

**Protocol**: `DistributedLock` — `lock_name`, `acquire()` (async context manager), `is_locked()`

**Class**: `RedisDistributedLock`:
- Uses Redis SET NX PX with Lua scripts for atomicity
- `timeout` (default 30s) — auto-release prevents deadlocks
- `blocking_timeout` (default 10s) — max wait for acquisition
- `lock_prefix` (default "lock") — Redis key prefix
- `_owner_id` — UUID for ownership verification
- `acquire()` — async context manager, yields on success, auto-releases
- `is_locked()` — checks if lock is held

**Class**: `InMemoryLock` — fallback using `asyncio.Lock` when Redis unavailable

**Factory**: `create_distributed_lock(name, timeout, blocking_timeout)` — auto-selects Redis or InMemory based on availability

---

### 4.8 `infrastructure/checkpoint/` — Unified Checkpoint System

**Sprint 120-121**: Checkpoint Unification

#### 4.8.1 `checkpoint/__init__.py` (27 lines)
Exports: `CheckpointEntry`, `CheckpointProvider`, `UnifiedCheckpointRegistry`

#### 4.8.2 `checkpoint/protocol.py` (~140 lines)

**Dataclass**: `CheckpointEntry`:
- `checkpoint_id` (auto UUID), `provider_name`, `session_id`, `data`, `metadata`, `created_at`, `expires_at`
- `to_dict()` / `from_dict()` serialization

**Protocol**: `CheckpointProvider` (runtime_checkable):
- `provider_name` property
- `save_checkpoint(checkpoint_id, data, metadata)` → `str`
- `load_checkpoint(checkpoint_id)` → `Optional[CheckpointEntry]`
- `delete_checkpoint(checkpoint_id)` → `bool`
- `list_checkpoints(session_id=None, limit=100)` → `List[CheckpointEntry]`

#### 4.8.3 `checkpoint/unified_registry.py` (~350 lines) — `UnifiedCheckpointRegistry`

Central coordinator for 4 checkpoint systems:
- `register_provider(provider)` / `unregister_provider(name)` — thread-safe via asyncio.Lock
- `save(provider_name, checkpoint_id, data, metadata)` — delegates to named provider
- `load(provider_name, checkpoint_id)` — delegates to named provider
- `delete(provider_name, checkpoint_id)` — delegates to named provider
- `list(provider_name, session_id, limit)` — delegates to named provider
- `search_all(session_id, limit)` — searches across ALL providers
- `get_provider(name)` — returns provider instance
- `list_providers()` — returns all provider names
- `export_all(output_path)` — exports all checkpoints to JSON file
- `get_stats()` — per-provider checkpoint counts

#### 4.8.4 Checkpoint Adapters (`checkpoint/adapters/`)

**`adapters/__init__.py`** (25 lines) — exports all 4 adapters

**4 Adapters** (each ~250-300 lines), all implementing `CheckpointProvider`:

| Adapter | Wraps | Backend | Sprint |
|---------|-------|---------|--------|
| `AgentFrameworkCheckpointAdapter` | `BaseCheckpointStorage` (agent_framework.multiturn) | Redis/Postgres/FS | 121 |
| `DomainCheckpointAdapter` | `DatabaseCheckpointStorage` (domain.checkpoints) | PostgreSQL | 121 |
| `HybridCheckpointAdapter` | `UnifiedCheckpointStorage` (hybrid.checkpoint) | Memory/Redis/Postgres/FS | 120 |
| `SessionRecoveryCheckpointAdapter` | `SessionRecoveryManager` (domain.sessions) | Cache/Redis | 121 |

Each adapter:
- Translates between its system's data model and `CheckpointEntry`
- Maps checkpoint_id to the underlying system's ID scheme (UUID, session_id, etc.)
- Implements all 4 `CheckpointProvider` methods
- Logs initialization with provider_name and backend type

---

## 5. Middleware

### 5.1 `middleware/__init__.py` (8 lines)
Exports: `setup_rate_limiting`, `limiter`

### 5.2 `middleware/rate_limit.py` (~78 lines)

**Sprint 111**: S111-9 — Rate Limiting

**Library**: slowapi

**Rate Limits**:
| Environment | Default Limit |
|-------------|---------------|
| Development | 1000/minute per IP |
| Production | 100/minute per IP |

**Components**:
- `_get_rate_limit_key(request)` — extracts client IP via `get_remote_address`
- `_get_default_limit()` — environment-aware limit string
- `limiter = Limiter(key_func=..., default_limits=[...])` — module-level instance
- `setup_rate_limiting(app)` — attaches limiter to app state, registers exception handler

**Note**: Uses in-memory storage (not Redis). Comment indicates Sprint 119 upgrade planned but not yet implemented.

---

## 6. Cross-Reference Matrix

### 6.1 core/auth.py Dependencies
| Depends On | Used By |
|------------|---------|
| `core.config.get_settings` | API v1 routers (as global dependency) |
| `jose.jwt` | `api.v1.dependencies.get_current_user` (for full User model) |
| `fastapi.security.HTTPBearer` | — |

### 6.2 core/config.py Dependencies
| Depends On | Used By |
|------------|---------|
| `pydantic_settings.BaseSettings` | Nearly every module in the application |

### 6.3 core/sandbox/ Dependencies
| Depends On | Used By |
|------------|---------|
| `core.sandbox.config.ProcessSandboxConfig` | `api.v1.claude_sdk` routes (via adapter) |
| `core.sandbox.ipc` | `integrations.claude_sdk` |

### 6.4 infrastructure/database Dependencies
| Depends On | Used By |
|------------|---------|
| `sqlalchemy`, `asyncpg` | All domain services, API routes |
| `core.config.get_settings` (for database_url) | — |

### 6.5 infrastructure/cache Dependencies
| Depends On | Used By |
|------------|---------|
| `infrastructure.redis_client` | `integrations.llm` (LLM response caching) |
| `core.config.get_settings` | — |

### 6.6 infrastructure/checkpoint Dependencies
| Depends On | Used By |
|------------|---------|
| `domain.checkpoints.storage` | API checkpoint routes |
| `domain.sessions.recovery` | Session management |
| `integrations.agent_framework.multiturn` | Agent multi-turn conversations |
| `integrations.hybrid.checkpoint` | Hybrid orchestration |

### 6.7 main.py Dependency Chain
```
main.py
├── core.config (get_settings)
├── core.logging (setup_logging, RequestIdMiddleware)
├── core.observability (setup_observability)
├── core.server_config (ServerConfig)
├── infrastructure.database.session (init_db, close_db)
├── domain.agents.service (init_agent_service)
├── middleware.rate_limit (setup_rate_limiting)
└── api.v1 (api_router)
```

---

## 7. Findings and Observations

### 7.1 Architecture Strengths

1. **Clean Separation of Concerns**: Core/Infrastructure/Domain layers are well-separated with clear responsibilities
2. **Environment-Aware Design**: ServiceFactory, storage factory, rate limiting all adapt behavior based on APP_ENV
3. **Protocol-Based Abstractions**: StorageBackend, CheckpointProvider, DistributedLock all use Python Protocols for clean interfaces
4. **Comprehensive Security**: JWT + bcrypt + sandbox isolation + sensitive data masking + path traversal prevention
5. **Observability Stack**: Full OTel integration with Azure Monitor, structured logging with request correlation, metrics collection
6. **Graceful Degradation**: Redis unavailable? Falls back to InMemory. LLM unavailable? Falls back to mock. Database fails in dev? Continues running.

### 7.2 Notable Issues

1. **Messaging is a stub**: `infrastructure/messaging/__init__.py` is literally 1 line (`# Messaging infrastructure`). RabbitMQ config exists in Settings but no implementation. Azure Service Bus config exists but no implementation.

2. **Health check uses `os.environ` directly** (main.py line 257-258): Redis health check reads `REDIS_HOST` and `REDIS_PORT` via `os.environ.get()` instead of using `get_settings()`, violating the project rule that `.env values only in pydantic Settings, not os.environ`.

3. **Rate limiter uses in-memory storage**: The slowapi limiter has `storage_uri=None` (in-memory). In multi-worker production deployments, each worker has independent rate limits. Sprint 119 comment suggests Redis upgrade was planned but not implemented.

4. **`datetime.utcnow()` deprecation**: Multiple files use `datetime.utcnow()` which is deprecated in Python 3.12+. Should use `datetime.now(timezone.utc)`.

5. **`infrastructure/__init__.py` content mismatch**: The file contains `# Messaging infrastructure` which seems like a misplaced comment from the messaging submodule.

6. **Dual sandbox config files**: Both `core/sandbox_config.py` (SandboxConfig for directory isolation) and `core/sandbox/config.py` (ProcessSandboxConfig for process isolation) exist. Different purposes but naming could be confusing.

7. **Performance module is heavy** (~3,500 lines across 8 files): Comprehensive but potentially over-engineered for current usage. Includes benchmark runner, concurrent optimizer, metric collector, profiler — unclear if all are actively used.

### 7.3 Security Assessment

| Area | Status | Implementation |
|------|--------|---------------|
| JWT Authentication | Implemented | HS256, 1-hour expiry, lightweight validation + full DB validation |
| Password Hashing | Implemented | bcrypt via passlib |
| Path Traversal Prevention | Implemented | SandboxConfig sanitizers |
| Process Isolation | Implemented | Sandbox subprocess with filtered env vars |
| Sensitive Data Masking | Implemented | structlog filter for passwords/secrets/tokens |
| Rate Limiting | Partially | In-memory only, not distributed |
| Security Audit | Implemented | Automated report generator with pip-audit + OWASP checks |
| Secret Validation | Implemented | Startup check for unsafe default values |

### 7.4 Database Schema Summary

7 SQLAlchemy models with UUID primary keys and TimestampMixin:
- **Agent** — AI agent definitions and capabilities
- **Workflow** — Workflow step definitions with versioning
- **Execution** — Workflow execution tracking with LLM cost metrics
- **Session** — Chat conversation state with message history (JSON)
- **User** — Authentication with bcrypt password and role-based access
- **AuditLog** — Action audit trail with IP tracking
- **Checkpoint** — HITL approval workflow with expiry support

All use PostgreSQL-specific UUID type and server-side timestamp defaults.

---

*Analysis complete. 76 files read across core/, infrastructure/, middleware/, and main.py.*
