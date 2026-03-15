# Dr. Distributed -- IPA Platform Distributed Systems Architecture Analysis

**Author**: Dr. Distributed (Distributed Systems Specialist)
**Date**: 2026-03-15
**Scope**: State management, data persistence, fault tolerance, scalability
**Source**: V8 Issue Registry + full source code reading of 40+ critical modules
**Verdict**: NOT PRODUCTION-READY -- systemic in-memory storage renders the system stateless on restart

---

## Executive Summary

The IPA Platform suffers from a fundamental architectural contradiction: it is designed as an enterprise AI orchestration platform (PostgreSQL + Redis + RabbitMQ) but operates as an **ephemeral, single-process application** in practice. Over 25 modules store critical operational state exclusively in Python `dict`/`list` variables that vanish on process restart. The messaging infrastructure (RabbitMQ) is a complete stub -- one line of code. The rate limiter uses in-memory storage. More than 90 global singleton instances scatter shared mutable state across the codebase with no distributed coordination.

Under the CAP theorem, this system currently provides **CP for the PostgreSQL-backed subset** (agents, workflows, executions, checkpoints, users) but is **effectively AP=0, C=0, P=0 for everything else** -- because non-persisted state simply does not survive any partition, crash, or restart. Horizontal scaling is structurally impossible without addressing the in-memory storage problem first.

The good news: the codebase has a well-designed `StorageBackend` protocol (Sprint 119) with Redis and InMemory implementations, and 7 domain-specific storage factories (Sprint 119-120) that can select Redis in production. The problem is that **only 7 of 25+ storage consumers use these factories**, and the remaining 18+ modules hardcode raw `dict` storage with no abstraction layer.

**Estimated remediation**: 3-5 sprints for critical path, 8-12 sprints for full persistence migration.

---

## 1. InMemory Storage Panoramic Map

### 1.1 Complete Module Inventory

The following table catalogs every module using in-memory `dict`/`list`/`set` for state that should survive process restarts. Verified by reading source code for each entry.

#### Tier 1: CRITICAL -- Active User-Facing State (Data Loss = Immediate User Impact)

| # | Module | File Path | Variable(s) | Data Structure | Has Redis Alternative? | Business Impact |
|---|--------|-----------|-------------|----------------|----------------------|-----------------|
| 1 | **AG-UI ApprovalStorage** | `integrations/ag_ui/features/human_in_loop.py:188` | `self._requests: Dict[str, ApprovalRequest]` | dict | NO | Pending HITL approvals lost; high-risk operations may proceed without approval |
| 2 | **AG-UI ChatSession** | `api/v1/ag_ui/routes.py:936` | `_get_thread_state_storage() -> Dict[str, Dict]` | module-level dict | NO (inline) | All active chat threads and conversation history lost |
| 3 | **Autonomous TaskStore** | `api/v1/autonomous/routes.py:91` | `self._tasks: Dict`, `self._history: List` | dict + list | NO | All autonomous task plans and execution history lost (mock data, but user-visible) |
| 4 | **RootCause Store** | `api/v1/rootcause/routes.py:122` | `self._analyses: Dict` | dict | NO | Root cause analysis results lost (mock data) |
| 5 | **A2A AgentDiscovery** | `integrations/a2a/discovery.py:51` | `self._agents: Dict[str, AgentCapability]` | dict | NO | Agent registry lost; inter-agent communication breaks |
| 6 | **A2A MessageRouter** | `integrations/a2a/router.py:45-46` | `self._queues: Dict`, `self._messages: Dict`, `self._handlers: Dict` | 3 dicts | NO | All in-flight A2A messages and routing state lost |
| 7 | **Swarm Tracker** | `integrations/swarm/tracker.py:86` | `self._swarms: Dict[str, AgentSwarmStatus]` | dict | Optional Redis (param) | Active swarm execution state lost; frontend visualization breaks |
| 8 | **Swarm Integration** | `integrations/swarm/swarm_integration.py:70` | `self._active_swarms: Dict[str, str]` | dict | NO | Coordination-to-swarm mapping lost |

#### Tier 2: HIGH -- Operational State (Data Loss = Degraded Service)

| # | Module | File Path | Variable(s) | Data Structure | Has Redis Alternative? | Business Impact |
|---|--------|-----------|-------------|----------------|----------------------|-----------------|
| 9 | **Decision Tracker** | `integrations/audit/decision_tracker.py:53` | `self._decisions: Dict[str, DecisionAudit]` | dict | Optional Redis (fallback) | AI decision audit trail lost; compliance gap |
| 10 | **Orchestration Metrics** | `integrations/orchestration/metrics.py:336-338` | `self._counters`, `self._histograms`, `self._gauges` | 3 dicts (fallback) | OTel (if available) | Routing metrics lost; cannot monitor routing performance |
| 11 | **ContextBridge Cache** | `integrations/hybrid/context/bridge.py` | `self._context_cache: Dict[str, HybridContext]` | dict (NO lock) | NO | Cross-framework context lost; race condition risk |
| 12 | **ClaudeMAFFusion** | `integrations/hybrid/claude_maf_fusion.py:78,112-113` | `self._history`, `self._workflows`, `self._executions` | list + 2 dicts | NO | Fusion execution history and workflow mapping lost |
| 13 | **Correlation EventCollector** | `integrations/correlation/event_collector.py:69` | `self._dedup_cache: Dict[str, datetime]` | dict | NO | Dedup cache lost; duplicate event processing |
| 14 | **RootCause CaseRepository** | `integrations/rootcause/case_repository.py` | In-memory with seed data | dict | Interface exists, not wired | Historical cases for pattern matching lost |
| 15 | **MCP InMemoryAuditStorage** | `integrations/mcp/security/audit.py:265` | In-memory events list | list | Factory exists (Sprint 120) | MCP tool audit trail lost |
| 16 | **Rate Limiter** | `middleware/rate_limit.py:54-57` | `storage_uri=None` | slowapi internal dict | Planned for Redis (comment says "Sprint 119") | Rate limits reset; DDoS protection gap in multi-worker |
| 17 | **Sandbox Orchestrator** | `core/sandbox/orchestrator.py:108-109` | `self._workers`, `self._user_worker_map` | 2 dicts | NO | Worker allocation state lost; sandbox inconsistency |

#### Tier 3: MEDIUM -- Auxiliary State (Data Loss = Feature Degradation)

| # | Module | File Path | Variable(s) | Data Structure | Has Redis Alternative? | Business Impact |
|---|--------|-----------|-------------|----------------|----------------------|-----------------|
| 18 | **Dialog ContextManager** | `integrations/orchestration/guided_dialog/context_manager.py:209-210` | `self._collected_info`, `self._dialog_history` | dict + list | YES (factory) | Active guided dialog sessions lost mid-conversation |
| 19 | **ModeSwitcher Checkpoint** | `integrations/hybrid/switching/switcher.py:183` | `InMemoryCheckpointStorage` | dict | YES (factory) | Mode switch checkpoints lost |
| 20 | **InMemory ConversationMemory** | `domain/orchestration/memory/in_memory.py:29` | In-memory store | dict | YES (factory) | Conversation memory lost |
| 21 | **SessionWebSocketManager** | `api/v1/sessions/websocket.py:71` | Connection tracking | dict | NO | Active WebSocket connections unknown after restart |
| 22 | **ConcurrentConnectionManager** | `api/v1/concurrent/websocket.py:44` | Connection tracking | dict | NO | Concurrent execution WebSocket state lost |
| 23 | **Connector Registry** | `domain/connectors/registry.py:43` | `self._connectors: Dict` | dict | NO | Registered connectors must be re-registered |
| 24 | **Tool Registry** (domain) | `domain/agents/tools/registry.py:29` | `self._tools: Dict` | dict | NO | Tool registrations lost |
| 25 | **Tool Registry** (AF) | `integrations/agent_framework/tools/base.py:251` | Global registry | dict | NO | Agent framework tool registrations lost |
| 26 | **Session MetricsCollector** | `domain/sessions/metrics.py:194` | In-memory metrics | dict | NO | Session performance metrics lost |
| 27 | **DeadlockDetector** | `domain/workflows/deadlock_detector.py` | Detection state | dict | NO | Deadlock detection state reset |

### 1.2 Data Loss Risk Matrix

```
                        Frequency of Access
                   Low              High
              +------------------+------------------+
    Critical  | C-07: SQL Inject | C-01: InMemory   |
    (BLOCK    | C-08: API Key    |   25+ modules    |
     PROD)    |                  |   ALL user state |
              +------------------+------------------+
    High      | H-05: Checkpoint | H-03: Singletons |
    (DEGRADE  |   API mismatch   |   90+ globals    |
     SERVICE) | H-14: Rate Limit | H-04: No lock on |
              |                  |   ContextBridge  |
              +------------------+------------------+
    Medium    | M-09: CaseRepo   | M-10: Audit dict |
    (FEATURE  | M-11: A2A mem    | M-22: Sync file  |
     LOSS)    |                  |   I/O blocking   |
              +------------------+------------------+
```

### 1.3 Single-Instance Bottleneck Analysis

**Current deployment model**: Single uvicorn worker (development mode with `--reload`)

**What breaks with N>1 workers (multi-process)**:
- ALL 25+ in-memory stores become inconsistent (each worker has its own copy)
- Rate limiter applies per-worker, not per-IP globally
- Global singletons (90+ `global` statements found) create N independent instances
- WebSocket connections tracked per-worker only
- AG-UI approval requests visible only to the worker that created them
- Swarm tracking state fragmented across workers

**What breaks with N>1 server instances (horizontal scale)**:
- Same as above, plus:
- No shared session affinity mechanism
- No distributed lock for ContextBridge race condition (H-04)
- A2A message routing cannot cross instance boundaries
- Connector registry not synchronized across instances

---

## 2. Persistence Architecture Analysis

### 2.1 PostgreSQL Usage Analysis

**Status**: HEALTHY -- well-structured async SQLAlchemy with connection pooling

| Aspect | Assessment |
|--------|------------|
| **ORM** | SQLAlchemy 2.x async, 8 model files (Agent, Workflow, Execution, Checkpoint, Session, Audit, User, Base) |
| **Session Management** | `get_session()` dependency injection + `DatabaseSession()` context manager |
| **Connection Pool** | `pool_size=5`, `max_overflow=10`, `pool_pre_ping=True` |
| **Transaction Safety** | Auto-commit on success, auto-rollback on exception |
| **Repositories** | `BaseRepository` with generic CRUD; 7 specialized repositories |

**Coverage**: PostgreSQL backs the core CRUD entities: agents, workflows, executions, checkpoints, sessions, users, audit logs. This is roughly **30% of the system's total state**.

**Gap**: The remaining **70% of operational state** (approvals, chat sessions, swarm tracking, A2A, metrics, dialog sessions, mode switching, etc.) has NO database persistence.

### 2.2 Redis Usage Analysis

**Status**: PARTIALLY WIRED -- infrastructure exists but underutilized

| Component | Status | Notes |
|-----------|--------|-------|
| **Redis Client** | `infrastructure/redis_client.py` | Async client with singleton pool, health check |
| **StorageBackend Protocol** | `infrastructure/storage/protocol.py` | Clean interface: get/set/delete/exists/list_keys/set ops |
| **InMemoryStorageBackend** | `infrastructure/storage/memory_backend.py` | Full protocol implementation with TTL, asyncio.Lock |
| **RedisStorageBackend** | `infrastructure/storage/redis_backend.py` | Full protocol implementation with JSON serialization |
| **Storage Factory** | `infrastructure/storage/factory.py` | Environment-aware: Redis in prod, InMemory fallback in dev |
| **Domain-Specific Factories** | `infrastructure/storage/storage_factories.py` | 7 factories (Approval, Dialog, Thread, Cache, Memory, Switch, Audit, AF Checkpoint) |
| **LLM Cache** | `infrastructure/cache/llm_cache.py` | Redis-backed SHA256 cache with TTL, stats, warm-up |

**The 7 storage factories cover**:
1. ApprovalStorage (HITL) -- orchestration layer
2. DialogSessionStorage -- guided dialog
3. AG-UI ThreadRepository + Cache
4. ConversationMemoryStore
5. SwitchCheckpointStorage (mode switcher)
6. AuditStorage (MCP)
7. AgentFrameworkCheckpointStorage

**What is NOT covered by factories** (still raw in-memory):
- AG-UI HITL ApprovalStorage (separate from orchestration's)
- AG-UI chat thread state (inline module-level dict)
- Autonomous TaskStore
- RootCause Store
- A2A Discovery + Router
- Swarm Tracker
- Decision Tracker
- Orchestration Metrics
- ContextBridge cache
- ClaudeMAFFusion state
- Correlation dedup cache
- Rate limiter
- Sandbox orchestrator
- Session/Concurrent WebSocket managers
- Connector/Tool registries (2)
- Session MetricsCollector
- DeadlockDetector

### 2.3 Persistence Gap Summary

```
+-----------------------------------+--------------------+-------------------+
|  State Category                   | Persisted?         | Gap               |
+-----------------------------------+--------------------+-------------------+
|  Agent/Workflow/Execution CRUD    | YES (PostgreSQL)   | --                |
|  Checkpoint data                  | YES (PostgreSQL)   | Custom API (H-05) |
|  User accounts                    | YES (PostgreSQL)   | --                |
|  Audit log (structured)           | YES (PostgreSQL)   | --                |
|  LLM response cache               | YES (Redis)        | --                |
+-----------------------------------+--------------------+-------------------+
|  HITL approvals (orchestration)   | FACTORY (Redis/Mem)| Default=InMemory  |
|  Dialog sessions                  | FACTORY (Redis/Mem)| Default=InMemory  |
|  AG-UI threads                    | FACTORY (Redis/Mem)| Default=InMemory  |
|  Conversation memory              | FACTORY (Redis/Mem)| Default=InMemory  |
|  Mode switch checkpoints          | FACTORY (Redis/Mem)| Default=InMemory  |
|  MCP audit events                 | FACTORY (Redis/Mem)| Default=InMemory  |
|  AF checkpoints (multiturn)       | FACTORY (Redis/Mem)| Default=InMemory  |
+-----------------------------------+--------------------+-------------------+
|  AG-UI HITL approvals             | NO                 | CRITICAL          |
|  Chat thread state                | NO                 | CRITICAL          |
|  Swarm execution state            | NO                 | HIGH              |
|  A2A agent registry + messages    | NO                 | HIGH              |
|  Decision audit records           | NO (opt. Redis)    | HIGH              |
|  Orchestration metrics            | NO (opt. OTel)     | MEDIUM            |
|  ContextBridge cache              | NO                 | HIGH              |
|  Correlation dedup cache          | NO                 | MEDIUM            |
|  Rate limiter counters            | NO                 | HIGH              |
|  Sandbox worker tracking          | NO                 | MEDIUM            |
|  Connector/Tool registries        | NO                 | MEDIUM            |
|  WebSocket connection state       | NO                 | LOW (transient)   |
|  Deadlock detection state         | NO                 | LOW               |
+-----------------------------------+--------------------+-------------------+
```

---

## 3. Consistency and Fault Tolerance Analysis

### 3.1 CAP Positioning

The IPA Platform is an **unintentionally partitioned system**:

```
                    Consistency
                        |
                        |   PostgreSQL subset
                        |   (agents, workflows,
                        |    executions, users)
                        |        *
                        |
     Availability ------+------ Partition Tolerance
                        |
            * InMemory  |
              subset    |
           (approvals,  |
            chat, swarm,|
            A2A, etc.)  |
                        |
```

- **PostgreSQL subset (CP)**: Strong consistency via transactions; available only when DB is reachable
- **Redis-backed subset (AP tendency)**: Eventually consistent via TTL-based cache; Redis single-instance is a SPOF
- **InMemory subset (NONE)**: No consistency, no availability after restart, no partition tolerance

**Effective CAP Profile**: The system cannot tolerate ANY failure mode for 70% of its state.

### 3.2 Multi-Instance Deployment Issues

| Failure Scenario | Impact | Mitigation Exists? |
|-----------------|--------|-------------------|
| **Single worker restart** | All 25+ in-memory stores cleared; active chats, approvals, swarm states lost | NO |
| **Worker crash** | Same as restart + potential corrupted in-flight operations | NO |
| **Redis outage** | 7 factory-based stores fall back to InMemory; LLM cache unavailable | YES (degraded fallback) |
| **PostgreSQL outage** | Agent/workflow CRUD unavailable; session management breaks | YES (connection retry) |
| **Network partition** | Workers cannot share any state (already can't -- all in-memory) | NO |
| **Load balancer switch** | User sees different state on next request if routed to different worker | NO (no session affinity) |

### 3.3 Fault Recovery Capability

| Capability | Status | Details |
|------------|--------|---------|
| **Database auto-reconnect** | YES | `pool_pre_ping=True` in SQLAlchemy |
| **Redis reconnect** | PARTIAL | `get_redis_client()` retries but singletons may hold stale refs |
| **State recovery from crash** | NO | Only PostgreSQL-backed state survives |
| **Graceful degradation** | PARTIAL | Storage factories fall back to InMemory; no user notification |
| **Health check** | PARTIAL | `/health` checks DB and Redis but not in-memory state integrity |
| **Circuit breaker** | NO | No circuit breaker on any external service call |
| **Retry with backoff** | PARTIAL | Redis backend has `max_retries=2` but no exponential backoff |
| **Dead letter queue** | NO | Messaging infrastructure is a stub (C-06) |

---

## 4. Messaging Architecture Analysis

### 4.1 RabbitMQ Integration Status

**Status**: COMPLETE STUB

```python
# backend/src/infrastructure/messaging/__init__.py
# Messaging infrastructure
```

That is the entire content. One comment line. Despite:
- Docker Compose defining RabbitMQ on ports 5672/15672
- Settings defining `RABBITMQ_HOST`, `RABBITMQ_PORT`, `RABBITMQ_USER`, `RABBITMQ_PASSWORD`
- Architecture docs listing RabbitMQ as a core infrastructure component

**Impact**: There is NO asynchronous message processing in the entire system. All operations are synchronous request-response within a single process. This means:
- No background job processing
- No event-driven workflows
- No decoupled microservice communication
- No retry queues for failed operations
- No dead letter processing for poison messages

### 4.2 Event-Driven Architecture Maturity

| Aspect | Maturity Level | Evidence |
|--------|---------------|----------|
| **Event Definition** | 2/5 (Defined) | AG-UI events well-typed (9 swarm event types); Session events exist |
| **Event Transport** | 1/5 (Absent) | SSE for frontend push only; no backend event bus |
| **Event Processing** | 1/5 (Absent) | No consumer/subscriber infrastructure |
| **Event Sourcing** | 0/5 (None) | No event store; state is mutated in place |
| **Saga/Orchestration** | 1/5 (Manual) | HybridOrchestratorV2 does inline orchestration; no saga pattern |

**The system uses SSE (Server-Sent Events) for**:
- AG-UI protocol streaming to frontend
- Swarm execution progress updates

**But there is no backend-to-backend event system**. All inter-module communication is synchronous function calls within the same process.

---

## 5. Scalability Assessment

### 5.1 Vertical Scaling Limits

| Resource | Current Behavior | Limit |
|----------|-----------------|-------|
| **Memory** | All in-memory stores grow unbounded (most have no max_size) | OOM on long-running instance |
| **CPU** | Single event loop (async); CPU-bound ops block the loop | Single core effective utilization |
| **Connections** | DB pool: 5+10=15 max; Redis: single connection | ~15 concurrent DB operations |
| **File descriptors** | WebSocket connections + DB + Redis + HTTP clients | OS limit (~1024 default) |

**Memory leak risks**:
- `AutonomousTaskStore._tasks` and `._history` -- never cleaned
- `RootCauseStore._analyses` -- never cleaned
- `A2A MessageRouter._messages` -- never cleaned
- `DecisionTracker._decisions` -- never cleaned
- `OrchestrationMetrics` fallback counters/histograms -- accumulate forever
- `ContextBridge._context_cache` -- no eviction policy
- `AG-UI ApprovalStorage._requests` -- only explicit cleanup, no TTL sweep

### 5.2 Horizontal Scaling Blockers

**Severity**: BLOCKING -- the system CANNOT scale horizontally without these fixes:

| Blocker | Impact | Effort |
|---------|--------|--------|
| **25+ in-memory stores** | Each instance has independent state | HIGH (3-5 sprints) |
| **90+ global singletons** | Module-level `global` variables create per-process instances | HIGH (refactor to DI) |
| **Rate limiter in-memory** | Each worker has independent rate counters | LOW (1 line: add `storage_uri`) |
| **No session affinity** | Sequential requests may hit different workers | MEDIUM (Redis session store) |
| **No distributed locks** | ContextBridge race condition (H-04) | LOW (asyncio.Lock + Redis lock) |
| **WebSocket state in-memory** | WS connections tracked per-worker only | MEDIUM (Redis pub/sub) |
| **No RabbitMQ** | Background processing impossible | HIGH (implement from scratch) |

### 5.3 Scaling Roadmap

```
Phase 1: SURVIVE RESTART (Sprint N to N+2)
  ├── Wire all 7 existing storage factories to use Redis in dev
  ├── Add Redis storage_uri to rate limiter (1-line fix)
  ├── Add asyncio.Lock to ContextBridge._context_cache
  ├── Set STORAGE_BACKEND=redis as default (not "auto")
  └── Estimated: 1-2 sprints

Phase 2: PERSIST CRITICAL STATE (Sprint N+3 to N+5)
  ├── Create StorageBackend-based adapters for:
  │   ├── AG-UI HITL ApprovalStorage
  │   ├── AG-UI chat thread state
  │   ├── Swarm Tracker
  │   ├── Decision Tracker
  │   └── A2A Discovery + Router
  ├── Add max_size + TTL eviction to all remaining in-memory stores
  └── Estimated: 2-3 sprints

Phase 3: ENABLE MULTI-WORKER (Sprint N+6 to N+8)
  ├── Replace global singletons with FastAPI dependency injection
  ├── Implement Redis pub/sub for WebSocket fan-out
  ├── Add distributed locking (Redis SETNX) for critical sections
  ├── Configure sticky sessions or session affinity
  └── Estimated: 2-3 sprints

Phase 4: EVENT-DRIVEN ARCHITECTURE (Sprint N+9 to N+14)
  ├── Implement RabbitMQ publisher/consumer infrastructure
  ├── Move long-running operations to background workers
  ├── Implement saga pattern for multi-step workflows
  ├── Add dead letter queue and retry mechanisms
  └── Estimated: 4-6 sprints

Phase 5: FULL HORIZONTAL SCALE (Sprint N+15+)
  ├── PostgreSQL read replicas for query scaling
  ├── Redis Cluster for cache scaling
  ├── Container orchestration (Kubernetes) deployment
  ├── Auto-scaling policies based on metrics
  └── Estimated: Ongoing
```

---

## 6. Architecture Improvement Recommendations (By Priority)

### P0: IMMEDIATE (Current Sprint) -- Security + 1-Line Fixes

| # | Action | File | Effort | Risk |
|---|--------|------|--------|------|
| 1 | **Set `storage_uri` on rate limiter to Redis** | `middleware/rate_limit.py:57` | 1 line | DDoS gap in multi-worker |
| 2 | **Add `asyncio.Lock` to ContextBridge._context_cache** | `integrations/hybrid/context/bridge.py` | 5 lines | Race condition corrupts context |
| 3 | **Set `STORAGE_BACKEND=redis` as default in factory** | `infrastructure/storage/factory.py:48` | 1 line change | InMemory silent fallback |

### P1: SHORT-TERM (Next 2 Sprints) -- Wire Existing Factories

| # | Action | Modules | Effort | Impact |
|---|--------|---------|--------|--------|
| 4 | **Ensure all 7 storage factories actually produce Redis backends in dev** | storage_factories.py consumers | Config change | 7 modules gain persistence |
| 5 | **Add max_size limits to all unbounded in-memory stores** | 8+ modules | 2-3 days | Prevent OOM |
| 6 | **Add TTL-based eviction to ApprovalStorage, MessageRouter, TaskStore** | 3 modules | 2-3 days | Prevent memory leaks |

### P2: MEDIUM-TERM (Sprint N+3 to N+5) -- New Persistence Adapters

| # | Action | Modules | Effort | Impact |
|---|--------|---------|--------|--------|
| 7 | **Create Redis adapter for AG-UI HITL ApprovalStorage** | `ag_ui/features/human_in_loop.py` | 3-5 days | HITL approval survives restart |
| 8 | **Create Redis adapter for Swarm Tracker** | `swarm/tracker.py` | 3-5 days | Swarm state survives restart |
| 9 | **Create Redis adapter for A2A Discovery + Router** | `a2a/discovery.py`, `a2a/router.py` | 5-7 days | A2A communication persists |
| 10 | **Create Redis adapter for Decision Tracker** | `audit/decision_tracker.py` | 3-5 days | Audit compliance |
| 11 | **Move AG-UI chat thread state to StorageBackend** | `api/v1/ag_ui/routes.py` | 3-5 days | Chat history survives restart |

### P3: LONG-TERM (Sprint N+6+) -- Architecture Evolution

| # | Action | Scope | Effort | Impact |
|---|--------|-------|--------|--------|
| 12 | **Replace 90+ global singletons with FastAPI DI** | System-wide | 2-3 sprints | Testability, multi-worker support |
| 13 | **Implement RabbitMQ publisher/consumer** | `infrastructure/messaging/` | 2-3 sprints | Async processing, decoupling |
| 14 | **Implement circuit breaker pattern** | All external service calls | 1-2 sprints | Fault isolation |
| 15 | **Add event sourcing for critical state transitions** | Orchestration, Swarm | 2-3 sprints | Full audit trail, replay capability |

---

## Appendix A: Global Singleton Inventory

**Total `global` statements found**: 90+ across the backend codebase

**Highest concentration**:
- `api/v1/nested/routes.py`: 10 global singletons
- `api/v1/hybrid/core_routes.py`: 3 global singletons
- `api/v1/ag_ui/dependencies.py`: 5 global singletons
- `api/v1/claude_sdk/intent_routes.py`: 4 global singletons

**Pattern**: Nearly every API route module uses `global _instance` + `get_instance()` factory function instead of FastAPI's `Depends()` dependency injection system.

## Appendix B: Storage Backend Protocol Adoption

```
StorageBackend Protocol (Sprint 119)
  |
  +-- InMemoryStorageBackend (fully implemented)
  +-- RedisStorageBackend (fully implemented)
  |
  +-- Domain-Specific Factories (Sprint 119-120):
  |     1. create_approval_storage()        -> RedisApprovalStorage | InMemory
  |     2. create_dialog_session_storage()  -> RedisDialogSessionStorage | InMemory
  |     3. create_thread_repository()       -> RedisThreadRepository | InMemory
  |     4. create_ag_ui_cache()             -> RedisCacheBackend | InMemory
  |     5. create_conversation_memory_store() -> RedisConversationMemoryStore | InMemory
  |     6. create_switch_checkpoint_storage() -> RedisSwitchCheckpointStorage | InMemory
  |     7. create_audit_storage()           -> RedisAuditStorage | InMemory
  |     8. create_agent_framework_checkpoint_storage() -> RedisCheckpointStorage | InMemory
  |
  +-- NOT using protocol (raw dict/list):
        - AG-UI ApprovalStorage (human_in_loop.py)
        - AG-UI chat thread state (routes.py inline)
        - AutonomousTaskStore
        - RootCauseStore
        - A2A AgentDiscoveryService
        - A2A MessageRouter
        - SwarmTracker (optional Redis param, not StorageBackend)
        - DecisionTracker (custom Redis, not StorageBackend)
        - OrchestrationMetricsCollector (custom fallback)
        - ContextBridge._context_cache
        - ClaudeMAFFusion state
        - Correlation EventCollector dedup cache
        - Rate limiter (slowapi internal)
        - Sandbox orchestrator
        - WebSocket managers (2)
        - Connector/Tool registries (3)
        - Session MetricsCollector
        - DeadlockDetector
```

## Appendix C: Recommended Architecture Target State

```
                     ┌─────────────────────────────────────┐
                     │         Load Balancer               │
                     │    (sticky sessions / Redis)        │
                     └──────────────┬──────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
     ┌────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐
     │  Worker 1        │  │  Worker 2        │  │  Worker N        │
     │  (FastAPI+DI)    │  │  (FastAPI+DI)    │  │  (FastAPI+DI)    │
     │  NO global state │  │  NO global state │  │  NO global state │
     └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         │                          │                          │
  ┌──────▼──────┐          ┌────────▼────────┐        ┌───────▼───────┐
  │ PostgreSQL   │          │     Redis        │        │  RabbitMQ     │
  │ (persistent  │          │ (session state,  │        │ (async jobs,  │
  │  entities)   │          │  cache, locks,   │        │  events,      │
  │              │          │  rate limits,    │        │  dead letter)  │
  │ - Agents     │          │  pub/sub)        │        │               │
  │ - Workflows  │          │                  │        │ - Background  │
  │ - Executions │          │ - ALL operational│        │   processing  │
  │ - Users      │          │   state via      │        │ - Event bus   │
  │ - Audit log  │          │   StorageBackend │        │ - Retry queue │
  └──────────────┘          └──────────────────┘        └───────────────┘
```

---

**End of Analysis**

*This analysis is based on source code reading of 40+ backend modules and cross-referenced with the V8 Issue Registry (62 issues, 8 CRITICAL). All file paths and line numbers verified against the codebase as of 2026-03-15.*
