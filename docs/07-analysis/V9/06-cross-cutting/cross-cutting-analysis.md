# V9 Cross-Cutting Concerns Analysis

> **Scope**: Cross-layer patterns spanning all 11 architecture layers
> **Date**: 2026-03-29
> **Method**: Source code reading + grep-based pattern analysis + V9 layer report synthesis
> **Focus**: Security, Performance, Data Flow, Dependencies

---

## Table of Contents

1. [Security Analysis](#1-security-analysis)
2. [Performance Analysis](#2-performance-analysis)
3. [Data Flow Map](#3-data-flow-map)
4. [Dependency Graph](#4-dependency-graph)

---

## 1. Security Analysis

### 1.1 Authentication Architecture

**JWT Token Management** (`core/security/jwt.py`)

| Attribute | Value | Assessment |
|-----------|-------|------------|
| Algorithm | HS256 (symmetric) | MEDIUM risk -- RS256 (asymmetric) preferred for production |
| Secret source | `settings.jwt_secret_key` via pydantic Settings | OK -- not hardcoded |
| Access token TTL | `jwt_access_token_expire_minutes` (configurable) | OK |
| Refresh token TTL | 7 days (hardcoded) | LOW risk -- should be configurable |
| Token type field | `"type": "refresh"` in refresh tokens only | MEDIUM risk -- access tokens lack `"type"` claim, no audience/issuer claims |
| Datetime API | `datetime.utcnow()` (deprecated in Python 3.12+) | LOW -- should migrate to `datetime.now(UTC)` |

**API Gateway Auth** (`api/v1/dependencies.py`)

The API layer uses FastAPI Depends for auth injection:
- `get_current_user` -- JWT extraction + decode
- `get_current_user_optional` -- Allows unauthenticated access
- `get_current_active_admin` -- Admin role check
- `get_current_operator_or_admin` -- Operator+ role check

**Gap**: 1 public router + 46 protected routers registered in `api/v1/__init__.py`. The public router bypasses auth entirely. No CORS origin whitelist was found in the security scan (CORS configuration is likely in `main.py` but not validated per-environment).

### 1.2 RBAC System

The platform has **two parallel RBAC implementations** that are NOT integrated:

| System | Location | Scope | Storage |
|--------|----------|-------|---------|
| **Platform RBAC** | `core/security/rbac.py` | API resources, sessions | In-memory dict |
| **Tool Gateway RBAC** | `core/security/tool_gateway.py` | Orchestrator tool calls | In-memory dict |
| **MCP Permissions** | `mcp/security/permissions.py` | MCP server/tool access | In-memory dict |

**Critical Gaps**:

1. **Three separate permission stores**: `RBACManager._user_roles`, `ToolSecurityGateway._permissions`, and `PermissionManager._policies` all maintain independent in-memory dictionaries. A user's role in Platform RBAC is not automatically propagated to Tool Gateway or MCP Permissions.

2. **In-memory only**: All three systems lose state on restart. The `RBACManager` defaults unknown users to `Role.VIEWER`, which is a safe default, but means no persistent user-role mappings exist.

3. **Action parameter ignored**: `RBACManager.check_permission()` accepts an `action` parameter but the docstring states it is "currently accepted but not enforced beyond presence in the permission set." The check is resource-string-based only.

4. **Admin wildcard divergence**: Platform RBAC uses `"tool:*"` wildcard matching. Tool Gateway uses `frozenset()` (empty set = all allowed). MCP Permissions uses `fnmatch` glob patterns (`"*"`). Three different wildcard semantics for the same concept.

5. **Role enum duplication**: `core/security/rbac.py` defines `Role(str, Enum)` and `core/security/tool_gateway.py` defines a separate `UserRole(str, Enum)` with identical values `(admin, operator, viewer)`. These are not the same type.

### 1.3 Prompt Injection Defense

**PromptGuard** (`core/security/prompt_guard.py`) implements 3-layer defense:

| Layer | Function | Coverage |
|-------|----------|----------|
| L1: Input Filtering | `sanitize_input()` | 17 regex patterns: role confusion (7), boundary escape (7), data exfiltration (3) + 2 XSS escape patterns |
| L2: System Prompt Isolation | `wrap_user_input()` | Wraps user text in `<user_message>` tags |
| L3: Tool Call Validation | `validate_tool_call()` | Whitelist check + arg key safety + arg value injection scan |

**ToolSecurityGateway** (`core/security/tool_gateway.py`) adds a second injection scan specifically for tool call parameters, with 17 additional patterns covering SQL injection (`; DROP`, `UNION SELECT`), code injection (`exec(`, `eval(`, `__import__(`), and prompt injection (`IGNORE PREVIOUS`).

**Assessment**:
- **Strength**: Defense-in-depth with two independent scanning layers.
- **Gap**: PromptGuard is instantiated per-use, not enforced as middleware. There is no evidence of PromptGuard being called automatically in the chat pipeline -- it must be explicitly invoked by calling code.
- **Gap**: No Content Security Policy (CSP) headers found in grep scan.

### 1.4 MCP Security

**Command Whitelist** (`mcp/security/command_whitelist.py`):
- 3-tier classification: `allowed` (71 whitelisted commands) / `blocked` (23 dangerous patterns) / `requires_approval` (everything else triggers HITL).
- Blocked patterns cover destructive operations (`rm -rf /`, `format C:`, `shutdown`, fork bombs).
- Whitelist includes potentially dangerous commands: `sed`, `awk`, `tar`, `gzip` can modify files. `curl`, `wget` can exfiltrate data. `env`, `printenv` expose environment variables (including secrets).
- `sudo` prefix is stripped before whitelist check, meaning `sudo rm` extracts `rm` (which is not in blocked patterns without `-rf /`).

**Permission Manager** (`mcp/security/permissions.py`):
- Supports policy-based ABAC with glob patterns, priority ordering, and deny lists.
- Supports dynamic conditions (time range, IP whitelist, custom evaluators).
- **Gap**: No default policies are loaded at startup. The system starts with an empty policy set, meaning all access is denied by default (safe) but no policies are pre-configured for the 5 MCP server implementations.

### 1.5 SQL Injection Risk

**Grep results for f-string SQL**:

| File | Pattern | Risk |
|------|---------|------|
| `hybrid/checkpoint/backends/postgres.py:233` | `f"DELETE FROM {self._table_name} WHERE id = :id"` | MEDIUM -- table name from constructor, not user input. Parameters are bound via `:id`. |
| `hybrid/checkpoint/backends/postgres.py:479` | `f"DROP TABLE IF EXISTS {self._table_name} CASCADE"` | HIGH -- DDL with f-string interpolation. `_table_name` is set at construction from config, but if config is tainted, this enables schema destruction. |

Both cases use `_table_name` which is set during `__init__()` from a config parameter, not from user input. The actual query parameters (`id`) use SQLAlchemy `text()` with named bindings (`:id`), which is safe. Risk is limited to misconfigured table names at deployment time.

**No raw SQL with user-supplied values was found.** The main database layer uses SQLAlchemy ORM throughout.

### 1.6 Hardcoded Secrets Scan

No hardcoded production secrets found. Observations:
- `rabbitmq_password: str = "guest"` in `core/config.py` -- safe, this is the default env fallback.
- `password="redis_password"` in `api/v1/cache/routes.py:74` -- appears to be a demo/example value in a cache management endpoint.
- All credential patterns use `os.environ.get()` or pydantic `Settings` with empty-string defaults.
- The `patrol/checks/security_scan.py` module itself contains a hardcoded secret scanner with patterns for passwords, API keys, secrets, and tokens.

---

## 2. Performance Analysis

### 2.1 Async Pattern Usage

The platform is **fully async** at the API layer using FastAPI's native async support. Key patterns:

| Pattern | Count | Locations |
|---------|-------|-----------|
| `asyncio.gather` | 15+ call sites | Workflow executors, patrol checks, swarm demos, orchestration planners |
| `asyncio.Lock` | 16+ instances | Memory backends, SSH client, checkpoint registry, sandbox, patrol, WebSocket, LLM pool |
| `asyncio.Semaphore` | 6+ instances | Parallel gateway, concurrent executor, LLM pool, concurrent optimizer, sub-executor |
| `asyncio.Queue` | 3+ instances | Swarm event emitter, AG-UI bridge, concurrent optimizer |

**`asyncio.gather` usage patterns**:
- Workflow parallel gateway: Semaphore-bounded `gather` with `return_exceptions=True` for concurrent node execution.
- Patrol agent: `gather(*tasks, return_exceptions=True)` for parallel health checks.
- Tool handler: `gather(*tasks, return_exceptions=True)` for parallel tool execution.
- **All gather calls use `return_exceptions=True`** -- this is good practice, preventing one failure from cancelling all tasks.

**Potential issue**: `ContextSynchronizer` (`hybrid/context/sync/synchronizer.py`) uses an in-memory dict without `asyncio.Lock`. This is documented as a known thread-safety issue in the Hybrid CLAUDE.md. Under concurrent requests sharing the same synchronizer instance, dict mutations could interleave.

### 2.2 Connection Pooling

**Primary Database Pool** (`infrastructure/database/session.py`):

| Setting | Value | Assessment |
|---------|-------|------------|
| Engine | `create_async_engine` (asyncpg) | OK -- fully async |
| `pool_size` | 5 | LOW for production (handles 5 concurrent DB connections) |
| `max_overflow` | 10 | Total max = 15 connections |
| `pool_pre_ping` | True | OK -- detects stale connections |
| `pool_recycle` | Not set | WARNING -- long-lived connections may hit PostgreSQL timeout |
| Testing | `NullPool` | OK -- correct for test isolation |

**DB Optimizer Profiles** (`core/performance/db_optimizer.py`):

| Profile | pool_size | max_overflow | pool_timeout | pool_recycle |
|---------|-----------|-------------|-------------|-------------|
| Development | 5 | 10 | 30s | 1800s (30m) |
| Production | 20 | 30 | 30s | 3600s (1h) |
| High Performance | 50 | 50 | 10s | 1800s (30m) |

**Gap**: The `session.py` always uses the development profile (pool_size=5). The optimizer profiles exist but there is no evidence they are applied to the actual engine. This means **production deployments use 5-connection pool** -- a significant bottleneck under load.

**Dual Pool Risk**: The checkpoint postgres backend (`hybrid/checkpoint/backends/postgres.py`) creates its own `create_async_engine` separate from the main database session. This means the application could have two independent connection pools to the same database, doubling connection consumption and bypassing the pool_size limit.

**LDAP Connection Pool**: `mcp/servers/ldap/ad_config.py` configures `pool_size=5` (env: `LDAP_POOL_SIZE`), validated range 1-50.

### 2.3 Caching Strategy

| Cache Layer | Backend | TTL | Scope |
|-------------|---------|-----|-------|
| LLM Response Cache | Redis | 24 hours (86400s) | Model + prompt hash |
| Classification Cache | In-memory | Per-session | LLM classifier results |
| Session Cache | Redis | Configurable | Session state |
| AG-UI Thread Storage | Redis | Configurable | Thread state |
| Conversation Context | Redis / In-memory | Session-scoped | Dialog context |
| Checkpoint Storage | Memory / Redis / Postgres / FS | Configurable TTL | Execution checkpoints |

**Gap**: No centralized cache invalidation strategy. Each subsystem manages its own cache independently. There is no cache warming or preloading mechanism.

**Gap**: The LLM Response Cache uses `sha256(prompt)[:16]` as the key suffix. With 16 hex characters (64 bits), collision probability is non-trivial at high volume (birthday paradox). A longer hash prefix would be safer.

### 2.4 N+1 Query Risks

The repository layer uses SQLAlchemy ORM with relationships. Key observations:
- `BaseRepository.get_all()` uses `query.offset(skip).limit(limit).all()` without eager loading.
- Relationships defined with `relationship()` default to lazy loading.
- No `selectinload()` or `joinedload()` patterns were found in the grep scan.

**Assessment**: HIGH risk of N+1 queries when accessing related objects (e.g., loading agents with their workflows, executions with their checkpoints). Each access to a lazy-loaded relationship triggers a separate SQL query.

### 2.5 Circuit Breaker

**Implementation** (`core/performance/circuit_breaker.py`):
- Classic 3-state pattern: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
- Global singleton via `get_llm_circuit_breaker()`
- Config: `failure_threshold=5`, `recovery_timeout=60s`, `success_threshold=2`
- Protected by `asyncio.Lock` for thread safety
- Tracks metrics: total calls, failures, short-circuits

**Assessment**:
- **Strength**: Properly protects LLM API calls from cascade failure.
- **Gap**: Only one global circuit breaker exists. If the platform calls multiple LLM providers (Azure OpenAI, Anthropic, OpenAI), a failure in one provider opens the circuit for all. Per-provider circuit breakers would be more resilient.
- **Gap**: No integration with rate limiting (`tool_gateway.py` rate limiter is independent). A coordinated backpressure system would combine circuit breaker state with rate limit decisions.

### 2.6 Rate Limiting

Two independent rate limiters exist:

| System | Location | Storage | Scope |
|--------|----------|---------|-------|
| Tool Gateway | `core/security/tool_gateway.py` | In-memory dict | Per-user per-tool (30/min default, 5/min high-risk) |
| API Middleware | `middleware/rate_limit.py` | In-memory / Redis | HTTP endpoint level |

**Gap**: Tool Gateway rate limiter uses in-memory storage with a comment: "Phase 36 Sprint 110 will migrate to Redis." This migration appears not yet completed, meaning rate limits reset on restart and are not shared across multiple backend instances.

---

## 3. Data Flow Map

### 3.1 Complete Request-Response Chain

```
USER INPUT (browser/API client)
    |
    v
[L01: Frontend] React 18 + TypeScript
    | Fetch API (NOT Axios) -> HTTP POST /api/v1/sessions/{id}/chat
    | Headers: Authorization: Bearer <JWT>
    v
[L02: API Gateway] FastAPI (port 8000)
    | dependencies.py: get_current_user() -> JWT decode -> TokenPayload
    | sessions/chat.py: ChatRequest validation (Pydantic)
    | SSE response via StreamingResponse
    v
[L03: AG-UI Bridge] ag_ui/bridge.py
    | Converts HTTP request to AG-UI protocol events
    | Emits: RunStarted, TextMessageStart events
    | Sets up asyncio.Queue for event collection
    v
[L04: Input & Routing] orchestration/intent_router/
    | Three-tier cascade:
    |   L4a: PatternMatcher (<10ms) -- regex rules, YAML config
    |   L4b: SemanticRouter (<100ms) -- vector similarity (Aurelio/Azure AI Search)
    |   L4c: LLMClassifier (<2000ms) -- Claude Haiku fallback
    | Output: RoutingDecision { intent_category, risk_level, workflow_type }
    | + CompletenessChecker -- validates required fields
    | + RiskAssessor -- 7-dimension risk scoring
    v
[L05: Hybrid Orchestration] hybrid/orchestrator/mediator.py
    | OrchestratorMediator 9-step pipeline:
    |   1. RoutingHandler -- IT intent + FrameworkSelector -> ExecutionMode
    |   2. DialogHandler -- GuidedDialogEngine (if fields incomplete, max 5 turns)
    |   3. ApprovalHandler -- RiskAssessor + HITLController (if HIGH/CRITICAL risk)
    |   4. ContextHandler -- ContextBridge (MAF <-> Claude state sync)
    |   5. ExecutionHandler -- Dispatch to selected framework
    |   6. ObservabilityHandler -- Metrics recording
    | SSE: PipelineEventEmitter -> 14 event types
    v
[L06: MAF Builders] agent_framework/builders/
    | OR
[L07: Claude SDK] claude_sdk/client.py
    | OR
[Swarm Mode] swarm/manager.py
    |
    | ExecutionHandler dispatches based on ExecutionMode:
    |   WORKFLOW -> MAF builders (ConcurrentBuilder, HandoffBuilder, etc.)
    |   CHAT -> Claude SDK (AsyncAnthropic client)
    |   HYBRID -> ClaudeMAFFusion (Claude decisions in MAF workflows)
    |   SWARM -> SwarmModeHandler -> SwarmManager + WorkerExecutors
    v
[LLM API Call]
    | CircuitBreaker.execute() wraps the call
    | LLMServiceProtocol -> LLMServiceFactory -> provider client
    |   Azure OpenAI: azure-openai SDK
    |   Anthropic: anthropic.AsyncAnthropic
    | Response includes: text content + tool_calls[]
    v
[L08: MCP Tools] (if tool calls present)
    | UnifiedToolExecutor -> ToolRouter
    |   Hook pipeline: Approval -> Audit -> RateLimit -> Sandbox
    |   ToolSecurityGateway.validate_tool_call() (4-layer security)
    |   MCPClient -> MCPProtocol -> Transport -> MCP Server
    |   5 servers: Azure, Filesystem, Shell, LDAP, SSH
    |   CommandWhitelist for Shell/SSH (allowed/blocked/requires_approval)
    | Tool results fed back to LLM for next iteration
    v
[L09: Supporting Integrations]
    | Memory: mem0 (Qdrant vector store) -> search_memory tool
    | Audit: DecisionTracker -> audit trail
    | Correlation: Multi-agent event correlation
    | Learning: Few-shot example retrieval
    v
[L10: Domain Layer]
    | SessionService -> session state management
    | AgentService -> agent configuration
    | WorkflowService -> workflow definition + execution
    | CheckpointService -> HITL checkpoint lifecycle
    v
[L11: Infrastructure Layer]
    | PostgreSQL (asyncpg): Sessions, Agents, Workflows, Executions, Users
    | Redis: Cache, Session state, HITL approval queue, Pub/Sub
    | RabbitMQ: Configured but NOT implemented (stub only)
    v
[Response Assembly]
    | AG-UI events streamed back via SSE:
    |   TextMessageContent (incremental text chunks)
    |   ToolCallStart / ToolCallEnd (tool execution visibility)
    |   StateSnapshotStart (UI state updates)
    |   RunCompleted / RunFailed (terminal events)
    v
[L01: Frontend] React 18
    | unified-chat/ component processes SSE events
    | agent-swarm/ visualization for multi-agent views
    | Zustand stores for state management
    v
USER SEES RESPONSE
```

### 3.2 Data Transformation Points

| Boundary | Input Format | Output Format | Transformer |
|----------|-------------|---------------|-------------|
| Frontend -> API | JSON `ChatRequest` | Pydantic model | FastAPI auto-validation |
| API -> AG-UI | Pydantic model | `BaseAGUIEvent` | `ag_ui/bridge.py` |
| AG-UI -> Routing | AG-UI event | `RoutingDecision` | `BusinessIntentRouter` |
| Routing -> Orchestration | `RoutingDecision` | `OrchestratorRequest` | `RoutingHandler` |
| Orchestration -> LLM | `OrchestratorRequest` | LLM message format | `AgentHandler` |
| LLM -> Tool Execution | Tool call JSON | `ToolCallValidation` | `ToolSecurityGateway` |
| Tool -> MCP | Tool params | `MCPRequest` (JSON-RPC 2.0) | `MCPClient` |
| MCP -> LLM | Tool result | LLM message format | `ResultHandler` |
| LLM -> AG-UI | LLM response | SSE event stream | `PipelineEventEmitter` |
| AG-UI -> Frontend | SSE events | React state updates | Zustand stores |

### 3.3 State Persistence Points

| State | Storage | Persistence |
|-------|---------|-------------|
| User session | PostgreSQL + Redis cache | Durable |
| Chat history | PostgreSQL | Durable |
| Execution state | PostgreSQL + in-memory | Durable (DB) / Volatile (memory) |
| HITL approval queue | Redis | Semi-durable (survives restart if Redis AOF enabled) |
| Checkpoint data | Memory / Redis / Postgres / FS (4 backends) | Depends on backend selection (default: Memory = volatile) |
| Conversation context | In-memory dict (ContextSynchronizer) | VOLATILE -- lost on restart |
| MCP permissions | In-memory dict | VOLATILE -- lost on restart |
| RBAC user-role mapping | In-memory dict | VOLATILE -- lost on restart |
| Rate limit counters | In-memory dict | VOLATILE -- lost on restart |
| Circuit breaker state | In-memory | VOLATILE -- lost on restart |

**Critical observation**: 6 out of 10 state categories use volatile in-memory storage as default. This means a backend restart resets all permissions, rate limits, circuit breaker state, and conversation context. Only PostgreSQL-backed state (sessions, history, executions) survives restarts.

---

## 4. Dependency Graph

### 4.1 Import Statistics

| Source Module | Imported By (file count) | Fan-Out (imports others) |
|---------------|-------------------------|--------------------------|
| `src.core.config` | 49+ files | 0 (leaf) |
| `src.infrastructure.*` | 76 files (164 imports) | Moderate |
| `src.core.*` | 49 files (81 imports) | Low |
| `src.integrations.*` | 100+ files | High |
| `src.domain.*` | 100+ files | Moderate |

### 4.2 Module Dependency Map

```
                    src.core.config (leaf -- no deps)
                         ^
                         |
        +----------------+----------------+
        |                |                |
   src.core.*     src.infrastructure.*  src.domain.*
   (security,     (database, cache,    (agents, workflows,
    performance,   storage, redis)      sessions, auth)
    sandbox)            ^                    ^
        ^               |                    |
        |          +----+----+               |
        |          |         |               |
        +-----src.integrations.*-------------+
              (hybrid, orchestration, claude_sdk,
               agent_framework, mcp, swarm, ag_ui,
               llm, memory, patrol, audit, etc.)
                         ^
                         |
                   src.api.v1.*
                   (47 route modules)
```

### 4.3 Highest Fan-In Modules (Most Depended Upon)

| Module | Depended on by | Role |
|--------|---------------|------|
| **`integrations/hybrid/`** | api routes, ag_ui, claude_sdk, swarm | Central orchestration hub |
| **`integrations/agent_framework/core/`** | domain/workflows, api/checkpoints, api/workflows | MAF execution primitives |
| **`domain/workflows/models`** | agent_framework, api, domain/workflows/* | Workflow data structures |
| **`domain/sessions/`** | api/sessions (3 route files), ag_ui bridge | Session lifecycle |
| **`integrations/llm/`** | sessions/chat, domain/sessions/executor | LLM provider abstraction |
| **`integrations/ag_ui/events`** | swarm/events, ag_ui/features/*, mediator_bridge | Event type definitions |
| **`core/config`** | Nearly every module (49+ files) | Configuration singleton |
| **`infrastructure/database/`** | All domain services, API routes | Data access |

### 4.4 Cross-Layer Dependency Violations

| Violation | Source | Target | Issue |
|-----------|--------|--------|-------|
| Domain -> Integration | `domain/workflows/service.py` | `integrations/agent_framework/core/executor` | Domain layer directly imports integration layer (should go through an abstraction) |
| Domain -> Integration | `domain/checkpoints/service.py` | `integrations/agent_framework/core/approval` | Checkpoint service tightly coupled to MAF approval |
| Integration -> Integration | `integrations/swarm/worker_executor.py` | `integrations/hybrid/orchestrator/sse_events` | Swarm module depends on Hybrid module internals |
| Integration -> Integration | `integrations/ag_ui/features/human_in_loop.py` | `integrations/hybrid/risk` | AG-UI feature directly imports Hybrid risk engine |
| Integration -> Integration | `integrations/ag_ui/features/generative_ui.py` | `integrations/hybrid/switching` | AG-UI depends on Hybrid switching internals |
| Integration -> Domain | `integrations/agent_framework/core/workflow.py` | `domain/workflows/models` | Bidirectional dependency between framework and domain |
| Infrastructure -> Domain | `infrastructure/storage/storage_factories.py` | `domain/orchestration/memory/in_memory` | Infrastructure depends upward on domain |
| Infrastructure -> Domain | `infrastructure/checkpoint/adapters/domain_adapter.py` | `domain/checkpoints/storage` | Checkpoint adapter depends on domain storage |

### 4.5 Circular Dependency Risks

**Risk 1: hybrid <-> agent_framework**
- `hybrid/orchestrator/handlers/execution.py` imports `agent_framework` builders
- `agent_framework/core/workflow.py` imports `domain/workflows/models`
- `hybrid/switching/triggers/*` imports `hybrid/intent/models`
- These form a deep dependency chain but no direct circular import detected (Python handles via lazy imports).

**Risk 2: ag_ui <-> hybrid**
- `ag_ui/features/human_in_loop.py` imports `hybrid/risk`
- `ag_ui/features/generative_ui.py` imports `hybrid/switching`
- `ag_ui/features/tool_rendering.py` imports `hybrid/execution`
- `ag_ui/mediator_bridge.py` imports `hybrid/orchestrator/contracts`
- `hybrid/orchestrator/sse_events.py` is imported by `swarm/worker_executor.py`
- AG-UI is deeply coupled to Hybrid internals. If Hybrid refactors, AG-UI features break.

**Risk 3: infrastructure -> domain (inverted dependency)**
- `infrastructure/storage/storage_factories.py` imports from `domain/orchestration/memory/`
- `infrastructure/checkpoint/adapters/` imports from `domain/checkpoints/`
- This violates the layered architecture principle where infrastructure should not depend on domain. The adapters should be in the domain or integration layer.

### 4.6 Module Coupling Summary

```
HIGH coupling (>10 cross-module imports):
  hybrid/ -----> agent_framework/, claude_sdk/, orchestration/, ag_ui/, swarm/
  api/v1/ -----> domain/* (expected), integrations/* (many direct imports)

MEDIUM coupling (5-10 cross-module imports):
  ag_ui/ ------> hybrid/ (4 feature files import hybrid)
  claude_sdk/ -> hybrid/, swarm/ (coordinator imports)
  domain/ -----> integrations/ (workflows, checkpoints -- violation)

LOW coupling (<5 cross-module imports):
  mcp/ ---------> (mostly self-contained, only imported by claude_sdk/mcp)
  patrol/ ------> (self-contained scheduler + checks)
  memory/ ------> (self-contained mem0 wrapper)
  audit/ -------> (self-contained tracker)
```

---

## Summary: Top Cross-Cutting Risks

| # | Risk | Severity | Layers Affected | Recommendation |
|---|------|----------|-----------------|----------------|
| 1 | **Volatile state everywhere** -- 6/10 state categories use in-memory storage as default | CRITICAL | L04, L05, L08 | Migrate RBAC, rate limits, circuit breaker, and checkpoint defaults to Redis |
| 2 | **Three parallel RBAC systems** not integrated | HIGH | L02, L05, L08 | Unify into single PermissionManager with Redis-backed storage |
| 3 | **Database pool_size=5 in production** -- optimizer profiles not applied to actual engine | HIGH | L11 | Wire `db_optimizer.py` profiles into `session.py` based on `app_env` |
| 4 | **N+1 query risk** -- no eager loading in repository layer | HIGH | L10, L11 | Add `selectinload()` for common relationship access patterns |
| 5 | **ContextSynchronizer thread-safety** -- in-memory dict without locks | HIGH | L05 | Add `asyncio.Lock` or migrate to Redis-backed state |
| 6 | **Domain -> Integration dependency violations** -- 2 domain modules import integration code | MEDIUM | L05, L10 | Introduce abstraction interfaces in domain layer |
| 7 | **Infrastructure -> Domain inverted dependency** -- 2 infra modules import domain code | MEDIUM | L10, L11 | Move adapter code to integration layer |
| 8 | **AG-UI deeply coupled to Hybrid internals** -- 4 feature files import hybrid submodules | MEDIUM | L03, L05 | Define stable interface contracts between AG-UI and Hybrid |
| 9 | **Single global circuit breaker** for all LLM providers | MEDIUM | L06, L07 | Create per-provider circuit breakers |
| 10 | **PromptGuard not enforced as middleware** -- must be explicitly called | MEDIUM | L02, L05 | Add FastAPI middleware that auto-applies PromptGuard to chat endpoints |
| 11 | **Dual database connection pools** -- checkpoint backend creates separate engine | LOW | L05, L11 | Share the main engine via dependency injection |
| 12 | **MCP whitelist includes data-exfiltration commands** (`curl`, `wget`, `env`, `printenv`) | LOW | L08 | Move `curl`/`wget`/`env`/`printenv` to `requires_approval` tier |

---

*Analysis based on V9 architecture layer reports and direct source code reading of 939+ backend files.*
