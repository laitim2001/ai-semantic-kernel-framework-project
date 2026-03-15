# Dr. API Design -- IPA Platform API Architecture Analysis

**Analyst**: Dr. API Design (API Architecture & Integration Patterns)
**Date**: 2026-03-15
**Scope**: 39 API route modules, ~540 endpoints, 47 registered routers
**Baseline**: V8 Codebase Analysis (28 agents full code reading)

---

## Executive Summary

The IPA Platform API layer is architecturally ambitious -- 47 registered routers serving ~540 endpoints across REST, SSE, and WebSocket protocols. The router assembly in `__init__.py` is well-organized with a clear public/protected split and JWT auth coverage via `protected_router`. However, the API layer suffers from **three systemic architectural defects** that block production readiness:

1. **4 fully-mock API modules** (correlation, rootcause, autonomous, patrol) that return hardcoded data despite real integration-layer implementations existing
2. **Pervasive module-level singleton anti-pattern** for dependency injection across 10+ modules
3. **Inconsistent error handling** -- no unified error envelope across route modules

**Overall API Layer Health Score**: **62/100**

| Dimension | Score | Notes |
|-----------|-------|-------|
| Route Organization | 85/100 | Clean prefix hierarchy, good tagging |
| Authentication Coverage | 90/100 | Global JWT via protected_router |
| Error Handling Consistency | 45/100 | No unified error format across modules |
| Mock/Placeholder Ratio | 50/100 | 4 of 39 modules are 100% mock |
| DI Pattern Consistency | 40/100 | Mix of proper DI and global singletons |
| Schema/Validation Quality | 80/100 | Good Pydantic usage with Field constraints |
| Protocol Integration | 75/100 | REST + SSE well-structured, WebSocket partial |
| API Documentation | 70/100 | OpenAPI auto-gen, but inconsistent summaries |

---

## 1. API Layer Panoramic Analysis

### 1.1 39 Route Modules Health Assessment

#### Tier 1: Production-Quality Routes (DB-backed, proper DI)

| Module | File | Endpoints | Storage | DI Pattern | Quality |
|--------|------|-----------|---------|------------|---------|
| `agents/` | `routes.py` | 6 | PostgreSQL via `AgentRepository` | `Depends(get_agent_repository)` | **A** |
| `workflows/` | `routes.py` | 9 | PostgreSQL via `WorkflowRepository` | `Depends(get_session)` | **A** |
| `executions/` | `routes.py` | 11 | PostgreSQL via `ExecutionRepository` | `Depends(get_session)` | **A** |
| `sessions/` | multiple | 14 | PostgreSQL + Redis | `Depends(get_session)` | **A** |
| `dashboard/` | `routes.py` | 2 | PostgreSQL (direct queries) | `Depends(get_session)` | **B+** |
| `auth/` | `routes.py` + `migration.py` | 7 | PostgreSQL via `UserRepository` | `Depends(get_session)` | **A** |

#### Tier 2: Functional Routes (Real logic, some in-memory state)

| Module | Endpoints | Storage | Integration Layer | Quality |
|--------|-----------|---------|-------------------|---------|
| `orchestration/intent_routes.py` | 4 | Singleton router | Real 3-tier routing | **B+** |
| `orchestration/routes.py` | 7 | Singleton policies | Real RiskAssessor | **B** |
| `orchestration/dialog_routes.py` | 4 | In-memory `_dialog_sessions` | Real GuidedDialogEngine | **B-** |
| `orchestration/approval_routes.py` | 4 | Via HITLController | Real HITL (Redis/InMemory) | **B** |
| `orchestration/webhook_routes.py` | 3 | Singleton receiver | Real ServiceNow handler | **B+** |
| `ag_ui/` | 29 | In-memory (4 stores) | Real HybridEventBridge | **B-** |
| `swarm/routes.py` | 3 | Via SwarmTracker | Real swarm tracking | **B+** |
| `swarm/demo.py` | 5 | SSE streaming | Demo/test endpoints | **C+** |
| `claude_sdk/` | 40 | Mixed | Claude SDK integration | **B** |
| `hybrid/` | 23 | Mixed | Hybrid orchestrator | **B** |
| `mcp/` | 13 | Configuration | Real MCP servers | **B** |
| `n8n/` | varies | Webhook + config | Real n8n integration | **B+** |
| `cache/` | 9 | Redis/InMemory | LLMCacheService | **B** |
| `checkpoints/` | 10 | In-memory default | Multiple backends available | **B-** |
| `memory/` | 7 | mem0 system | Real memory integration | **B** |
| `files/` | 6 | Filesystem | Real file handling | **B** |
| `sandbox/` | 6 | In-memory | Simulated sandbox | **C** |

#### Tier 3: Legacy/Utility Routes (In-memory, limited logic)

| Module | Endpoints | Notes | Quality |
|--------|-----------|-------|---------|
| `concurrent/` | 13 | In-memory, MAF adapter | **C+** |
| `handoff/` | 14 | In-memory, MAF adapter | **C+** |
| `groupchat/` | 42 | In-memory, MAF adapter | **C+** |
| `planning/` | 46 | In-memory, MAF adapter | **C+** |
| `nested/` | 16 | In-memory, MAF adapter | **C+** |
| `templates/` | 11 | In-memory | **C** |
| `triggers/` | 8 | In-memory | **C** |
| `connectors/` | 9 | UAT test only | **C-** |
| `routing/` | 14 | In-memory | **C** |
| `notifications/` | 11 | Teams integration | **C+** |
| `audit/` | 15 | In-memory | **C** |
| `devtools/` | 12 | In-memory traces | **C** |
| `learning/` | 13 | In-memory | **C** |
| `versioning/` | 14 | In-memory | **C** |
| `performance/` | 11 | Mostly hardcoded | **C-** |
| `prompts/` | 11 | In-memory | **C** |
| `a2a/` | 14 | In-memory | **C** |

#### Tier 4: Mock/Placeholder Routes (CRITICAL -- Returns Fake Data)

| Module | Endpoints | Mock Evidence | Quality |
|--------|-----------|---------------|---------|
| `correlation/` | 7 | **100% mock** | **F** |
| `autonomous/` | 4 | **100% mock** | **F** |
| `rootcause/` (standalone) | 4 | **100% mock** | **F** |
| `patrol/` | 9 | **100% mock** + `time.sleep()` | **F** |

### 1.2 Mock/Placeholder Inventory (Critical Detail)

#### MOCK-01: `correlation/routes.py`

- **File**: `backend/src/api/v1/correlation/routes.py`
- **All 7 endpoints are mock**:
  - `POST /correlation/analyze` -- generates fake `CorrelationModel` objects with `uuid4().hex` IDs, hardcoded scores (0.8, 0.7, etc.), fabricated evidence strings
  - `GET /correlation/{event_id}` -- returns cached fake data or triggers new fake analysis
  - `POST /correlation/rootcause/analyze` -- hardcoded root cause string: "Database connection pool exhaustion...", fake confidence `0.87`
  - `GET /correlation/rootcause/{analysis_id}` -- returns cached fake data
  - `GET /correlation/graph/{event_id}/mermaid` -- generates Mermaid from fake graph
  - `GET /correlation/graph/{event_id}/json` -- returns fake graph JSON
  - `GET /correlation/graph/{event_id}/dot` -- generates DOT from fake graph
- **Real implementation exists**: `backend/src/integrations/correlation/` (Sprint 130)
- **Wiring gap**: API routes never import from `integrations/correlation`

#### MOCK-02: `autonomous/routes.py`

- **File**: `backend/src/api/v1/autonomous/routes.py`
- **Module docstring**: "Phase 22 Testing"
- **All 4 endpoints are mock**:
  - `POST /claude/autonomous/plan` -- `AutonomousTaskStore` generates steps from hardcoded templates: `["analyze", "plan", "prepare", "execute", "validate", "cleanup", "report"]`
  - `GET /claude/autonomous/history` -- returns from in-memory dict
  - `GET /claude/autonomous/{task_id}` -- `_simulate_progress()` fakes step completion on each GET call
  - `POST /claude/autonomous/{task_id}/cancel` -- updates in-memory state
- **Real implementation exists**: `backend/src/integrations/claude_sdk/autonomous/` (full analyze->plan->execute->verify pipeline)
- **Wiring gap**: No imports from `integrations/claude_sdk/autonomous`

#### MOCK-03: `rootcause/routes.py`

- **File**: `backend/src/api/v1/rootcause/routes.py`
- **Module docstring**: "Phase 23 Testing"
- **All 4 endpoints are mock**:
  - `POST /rootcause/analyze` -- `RootCauseStore` returns hardcoded: confidence `0.87`, root cause "Database connection pool exhaustion..."
  - `GET /rootcause/{analysis_id}/hypotheses` -- returns 5 hardcoded hypotheses with fixed confidence values (0.87, 0.65, 0.55, 0.45, 0.35)
  - `GET /rootcause/{analysis_id}/recommendations` -- returns 4 hardcoded recommendations, total effort "3-4 weeks (combined estimate)"
  - `POST /rootcause/similar` -- returns 3 hardcoded patterns with fixed similarity scores (0.92, 0.78, 0.65)
- **Real implementation exists**: `backend/src/integrations/rootcause/` (Sprint 130)
- **Wiring gap**: No imports from `integrations/rootcause`

#### MOCK-04: `patrol/routes.py`

- **File**: `backend/src/api/v1/patrol/routes.py`
- **9 endpoints, all mock**:
  - `POST /patrol/trigger` -- creates simulated report in `_patrol_reports` dict, never executes real checks
  - `GET /patrol/reports` -- returns hardcoded sample report with "All systems operating normally"
  - `GET /patrol/reports/{report_id}` -- if "running", instantly simulates completion
  - `GET /patrol/schedule` -- returns 2 hardcoded schedules (daily, hourly)
  - `POST /patrol/schedule` -- stores in `_scheduled_patrols` dict only
  - `PUT /patrol/schedule/{patrol_id}` -- updates in-memory dict
  - `DELETE /patrol/schedule/{patrol_id}` -- removes from dict
  - `GET /patrol/checks` -- returns 5 hardcoded check types
  - `GET /patrol/checks/{check_type}` -- **uses blocking `time.sleep(0.1)`** in async handler, returns hardcoded "healthy" result
- **Real implementation exists**: `backend/src/integrations/patrol/` (real health checks)
- **Wiring gap**: No imports from `integrations/patrol`
- **Extra severity**: `time.sleep()` blocks the async event loop (line 528)

### 1.3 API Design Consistency Scoring

| Aspect | Compliance | Details |
|--------|-----------|---------|
| RESTful URL patterns | **80%** | Most follow `/api/v1/{resource}` pattern; exceptions: `/claude/autonomous/plan` (verb in URL), `/correlation/rootcause/analyze` (nested resource confusion) |
| HTTP method semantics | **85%** | Generally correct; some GETs have side effects (patrol execute_check) |
| Response envelope consistency | **45%** | No unified envelope; agents use `AgentResponse`, dashboard uses `DashboardStats`, orchestration uses `IntentClassifyResponse`, patrol uses raw models |
| Pagination pattern | **60%** | agents use `page/page_size`, patrol uses `limit/offset`, dashboard has none, inconsistent across modules |
| Status code usage | **75%** | 201 for creation is mostly correct; some modules return 200 for creation |
| Tag naming convention | **70%** | Mix of capitalized ("Agents"), lowercase ("patrol"), and multi-word ("Intent Classification", "Guided Dialog") |

---

## 2. Route Architecture Analysis

### 2.1 Route Organization Pattern

The route assembly follows a **two-tier public/protected pattern**:

```
api_router (prefix=/api/v1)
  +-- public_router (no auth)
  |     +-- auth_router (login, register, refresh)
  +-- protected_router (JWT required via require_auth)
        +-- 45 route modules across 10 phases
```

**Strengths**:
- Clean separation of public vs. protected routes
- Phase-based organization in comments aids maintainability
- Single `require_auth` dependency ensures no route accidentally skips auth

**Weaknesses**:
- No route grouping by business domain (observability routes mixed with CRUD routes)
- 47 routers in a single `__init__.py` creates a monolithic registration file
- No route versioning beyond `/api/v1` prefix (no v2 migration path)

### 2.2 Middleware Architecture

```
Request Flow:
  RequestIdMiddleware (Sprint 122) -- adds X-Request-ID
    -> CORSMiddleware -- cross-origin handling
      -> RateLimiter (slowapi, Sprint 111) -- in-memory rate limiting
        -> require_auth (JWT validation on protected_router)
          -> Route Handler
            -> Global Exception Handler (catch-all)
```

**Issues**:
1. **Rate limiter uses in-memory storage** (`storage_uri=None`). Each uvicorn worker has independent limits. Issue H-14 from V8 registry.
2. **No request logging middleware** beyond the RequestIdMiddleware. No structured access logging.
3. **No request size limit middleware**. Large payloads could be sent without restriction beyond individual field validators.
4. **No response compression middleware** (gzip/brotli).

### 2.3 Authentication/Authorization Coverage

| Layer | Mechanism | Coverage |
|-------|-----------|----------|
| **Global Auth** | `require_auth` on `protected_router` | All non-auth routes |
| **User Resolution** | `get_current_user` dependency | Available but NOT used on most routes |
| **Admin Check** | `get_current_active_admin` dependency | Defined but NOT applied to any route |
| **Operator Check** | `get_current_operator_or_admin` dependency | Defined but NOT applied to any route |

**Critical Gap**: RBAC dependencies (`get_current_active_admin`, `get_current_operator_or_admin`) are **defined** in `dependencies.py` but **never used** by any route handler. This means:
- `POST /cache/clear` -- any authenticated user can clear caches
- `DELETE /agents/{id}` -- any authenticated user can delete agents
- `POST /orchestration/policies/mode/{mode}` -- any authenticated user can switch risk policy mode
- `POST /orchestration/metrics/reset` -- any authenticated user can reset metrics

This confirms V8 issue **H-01**: No RBAC on destructive operations.

---

## 3. Error Handling Architecture

### 3.1 Exception Handling Patterns Analysis

Four distinct error handling patterns exist across the codebase:

#### Pattern A: Structured Error Object (Best Practice)
Used by: `orchestration/`, `ag_ui/`
```python
raise HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail={"error": "CLASSIFICATION_ERROR", "message": str(e)},
)
```

#### Pattern B: Plain String Detail
Used by: `agents/`, `dialog_routes.py`, `approval_routes.py`
```python
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail=f"Agent with id '{agent_id}' not found",
)
```

#### Pattern C: Silent Fallback (Anti-Pattern)
Used by: `dashboard/routes.py`
```python
except Exception as e:
    return DashboardStats()  # silently returns empty data
```

#### Pattern D: Global Catch-All
In `main.py`:
```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    # Returns {"error": "Internal server error"} in production
    # Returns {"error": "...", "detail": str(exc)} in development
```

### 3.2 Error Code Unification Status

| Module | Uses Error Codes | Error Format |
|--------|-----------------|--------------|
| `orchestration/` | Yes (`CLASSIFICATION_ERROR`, `POLICY_LIST_ERROR`, etc.) | `{"error": "CODE", "message": "..."}` |
| `webhook_routes.py` | Yes (`WEBHOOK_VALIDATION_ERROR`, `INVALID_PAYLOAD`, `PROCESSING_ERROR`) | `{"error": "CODE", "message": "..."}` |
| `agents/` | No | Plain string |
| `dashboard/` | No | Silent fallback |
| `patrol/` | No | Plain string |
| `correlation/` | No | Plain string |
| `autonomous/` | No | Plain string |
| `rootcause/` | No | Plain string |
| `swarm/` | No | Plain string |
| `ag_ui/` | Yes (via schemas.ErrorResponse) | Structured |
| `auth/` | Partial | Mix |

**Verdict**: Only ~30% of modules use structured error codes. There is no global `ErrorResponse` schema enforced across all routes.

### 3.3 Error Response Format Inconsistency

Three different error response shapes coexist:

```python
# Shape 1: FastAPI default (majority of routes)
{"detail": "Agent not found"}

# Shape 2: Structured (orchestration, webhooks)
{"error": "CLASSIFICATION_ERROR", "message": "Failed to classify"}

# Shape 3: Global handler (unhandled exceptions)
{"error": "Internal server error"}
```

**Recommendation**: Define a project-wide `ErrorResponse` model and enforce it via a custom exception class + exception handler.

---

## 4. Protocol Integration Analysis

### 4.1 REST API Design Quality

**Well-Designed REST Endpoints** (exemplary):
- `agents/routes.py`: Classic CRUD with proper HTTP methods, 201 for creation, 204 for deletion, UUID path params, pagination with `page/page_size`
- `workflows/routes.py`: Similar quality with proper validation
- `orchestration/webhook_routes.py`: 202 Accepted for async processing, proper header-based auth, idempotency checks

**REST Anti-Patterns Found**:

| Issue | Location | Description |
|-------|----------|-------------|
| Verb in URL | `POST /claude/autonomous/plan` | Should be `POST /claude/autonomous` |
| Nested resource confusion | `POST /correlation/rootcause/analyze` | rootcause is a separate resource, not a sub-resource of correlation |
| GET with side effects | `GET /patrol/checks/{check_type}` | Executes a check (should be POST) |
| Inconsistent pluralization | `/cache/stats` vs `/patrol/reports` vs `/rootcause/analyze` | Mix of singular and plural |
| Query string for content | `POST /orchestration/intent/quick` accepts `content: str` as body, but it is a bare string, not a JSON object | Should use request body model |

### 4.2 AG-UI SSE Protocol Implementation

**Architecture**:
```
Frontend (CopilotKit) --> POST /api/v1/ag-ui --> StreamingResponse(SSE)
                                                   |
                                             HybridEventBridge
                                                   |
                                     +---------+---------+
                                     | MAF     | Claude  |
                                     | Events  | SDK     |
                                     +---------+---------+
```

**Strengths**:
- Well-defined SSE event types via `ag_ui.events` module
- Proper `StreamingResponse` with `text/event-stream` content type
- Thread-based session management for multi-turn conversations
- 7 AG-UI features implemented (Chat, Tool Rendering, HITL, Gen UI, Tool-based Gen UI, Shared State, Predictive State)

**Weaknesses**:
- **4 separate in-memory stores** in AG-UI module (ApprovalStorage, ChatSession, SharedState, PredictiveState) -- all lost on restart (V8 C-01)
- **Test endpoints** (`/ag-ui/test/*`) not gated by environment (V8 H-02)
- **API key prefix exposed** in bridge status/reset response (V8 C-08)
- SSE reconnection logic is a stub in frontend hook
- Version string "1.0.0" is hardcoded in health check (V8 L-15)

### 4.3 MCP/A2A Protocol Integration

**MCP** (Model Context Protocol):
- 8 MCP servers with 64 tools exposed via `mcp/routes.py`
- Management API allows server listing, tool discovery, and execution
- Permission system exists (4-level RBAC) but defaults to `log` mode (V8 H-07)
- AuditLogger exists but never wired (V8 H-06)

**A2A** (Agent-to-Agent):
- 14 endpoints in `a2a/routes.py`
- Fully in-memory agent registry and message passing (V8 M-11)
- No external transport mechanism
- No inter-process communication capability

---

## 5. Dependency Injection & Service Layer

### 5.1 DI Pattern Consistency Analysis

Three DI patterns are used across the API layer:

#### Pattern 1: FastAPI Depends (Correct)
Used by: `agents/`, `workflows/`, `executions/`, `sessions/`, `dashboard/`, `auth/`, `swarm/`
```python
async def get_agent_repository(
    session: AsyncSession = Depends(get_session),
) -> AgentRepository:
    return AgentRepository(session)

@router.get("/")
async def list_agents(repo: AgentRepository = Depends(get_agent_repository)):
    ...
```
**Count**: ~8 modules (~20% of total)

#### Pattern 2: Module-Level Singleton (Anti-Pattern)
Used by: `orchestration/`, `ag_ui/`, `cache/`, `autonomous/`, `rootcause/`, `patrol/`, `correlation/`, `dialog_routes/`, `webhook_routes/`
```python
_router_instance: Optional[BusinessIntentRouter] = None

def get_router() -> BusinessIntentRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = create_router(...)
    return _router_instance
```
**Count**: ~15 modules (~38% of total)

#### Pattern 3: No DI (Direct instantiation)
Used by: `templates/`, `triggers/`, `prompts/`, `versioning/`, `learning/`, `performance/`, etc.
```python
@router.post("/")
async def create_template(request: ...):
    _templates[id] = {...}  # direct dict manipulation
```
**Count**: ~16 modules (~41% of total)

### 5.2 Service-Route Coupling Analysis

| Coupling Level | Modules | Description |
|----------------|---------|-------------|
| **Loose** (Service via DI) | agents, workflows, executions, sessions, auth | Route -> Depends -> Service -> Repository |
| **Medium** (Singleton factory) | orchestration, ag_ui, cache, webhook | Route -> get_singleton() -> Integration layer |
| **Tight** (No separation) | patrol, correlation, autonomous, rootcause | Route handler contains all business logic inline |
| **Tight** (Direct dict access) | templates, triggers, prompts, versioning | Route directly manipulates in-memory dicts |

**Tight coupling in mock modules is expected** (they are stubs), but the **singleton pattern in orchestration** is concerning because it prevents proper testing and creates hidden shared state across requests.

---

## 6. API Architecture Improvement Recommendations

### 6.1 CRITICAL (Blocks Production)

| # | Recommendation | Affected Modules | Effort |
|---|----------------|-----------------|--------|
| **R-01** | **Wire mock API routes to real integration layer**: Connect correlation, rootcause, patrol, autonomous routes to their existing `integrations/` implementations | 4 modules | 2-3 sprints |
| **R-02** | **Remove `time.sleep()` from patrol `execute_check`**: Replace with `asyncio.sleep()` or real async check execution | `patrol/routes.py:528` | 1 hour |
| **R-03** | **Remove API key prefix from AG-UI response**: Strip sensitive data from `/ag-ui/reset` response | `ag_ui/routes.py` | 1 hour |
| **R-04** | **Gate test endpoints behind environment check**: Add `APP_ENV != production` guard to AG-UI test routes | `ag_ui/routes.py` | 2 hours |

### 6.2 HIGH (Significant Quality Impact)

| # | Recommendation | Affected Modules | Effort |
|---|----------------|-----------------|--------|
| **R-05** | **Implement unified error response envelope**: Create `IPAErrorResponse(error_code, message, details, request_id)` and enforce via custom exception handler | All 39 modules | 1 sprint |
| **R-06** | **Apply RBAC to destructive operations**: Use existing `get_current_active_admin` / `get_current_operator_or_admin` on cache clear, agent delete, policy switch, metrics reset | ~10 endpoints | 3-4 hours |
| **R-07** | **Replace module-level singletons with FastAPI dependency injection**: Convert `get_router()`, `get_assessor()`, `get_dialog_engine()` etc. to `Depends()` pattern | ~15 modules | 2 sprints |
| **R-08** | **Standardize pagination**: Choose one pattern (`page/page_size` vs `limit/offset`) and enforce project-wide | All list endpoints | 1 sprint |
| **R-09** | **Configure rate limiter with Redis storage**: Replace `storage_uri=None` with Redis-backed storage for multi-worker consistency | `middleware/rate_limit.py` | 2-3 hours |

### 6.3 MEDIUM (Should Fix)

| # | Recommendation | Affected Modules | Effort |
|---|----------------|-----------------|--------|
| **R-10** | **Standardize OpenAPI tags**: Use consistent PascalCase naming, group by business domain | All routers | 3-4 hours |
| **R-11** | **Fix REST anti-patterns**: Rename verb URLs, fix GET-with-side-effects, standardize pluralization | 5-6 endpoints | 4-6 hours |
| **R-12** | **Replace `datetime.utcnow()` with `datetime.now(timezone.utc)`**: Deprecated in Python 3.12+ | `dialog_routes.py`, `patrol/routes.py`, `correlation/routes.py`, `main.py:283` | 2-3 hours |
| **R-13** | **Add response compression middleware**: Add gzip/brotli middleware for large JSON responses | `main.py` | 1 hour |
| **R-14** | **Fix dashboard N+1 query**: Replace 3-queries-per-day loop with single aggregated SQL query | `dashboard/routes.py:127-192` | 2-3 hours |
| **R-15** | **Eliminate silent error swallowing in dashboard**: Replace `except: return DashboardStats()` with proper error propagation or at minimum, logging | `dashboard/routes.py:122-124` | 1 hour |

### 6.4 LOW (Nice to Have)

| # | Recommendation | Effort |
|---|----------------|--------|
| **R-16** | **Extract route registration to separate files per phase**: Split `__init__.py` into phase-specific registrations | 2-3 hours |
| **R-17** | **Add API versioning strategy documentation**: Document v1->v2 migration plan | 1 day |
| **R-18** | **Add request/response examples to OpenAPI schemas**: Enhance Pydantic models with `model_config = {"json_schema_extra": {"examples": [...]}}` | Ongoing |
| **R-19** | **Replace `os.environ.get()` in health check and webhook_routes with `get_settings()`**: Violates project pydantic Settings convention | 2 locations |

---

## 7. Mock-to-Real Wiring Roadmap

The most impactful improvement is wiring the 4 mock modules to their existing integration-layer implementations. Here is the specific wiring plan:

### 7.1 Correlation Routes -> `integrations/correlation/`

```python
# CURRENT (mock): api/v1/correlation/routes.py
correlations = [CorrelationModel(correlation_id=f"corr_{uuid4().hex[:8]}", ...)]  # FAKE

# TARGET: Import and use real CorrelationAnalyzer
from src.integrations.correlation import CorrelationAnalyzer
analyzer = CorrelationAnalyzer()
result = await analyzer.analyze(event_id, time_window_hours=request.time_window_hours)
```

### 7.2 Rootcause Routes -> `integrations/rootcause/`

```python
# CURRENT (mock): api/v1/rootcause/routes.py
root_cause = "Database connection pool exhaustion..."  # HARDCODED
confidence = 0.87  # HARDCODED

# TARGET: Import and use real RootCauseAnalyzer
from src.integrations.rootcause import RootCauseAnalyzer
analyzer = RootCauseAnalyzer()
result = await analyzer.analyze(event_id, depth=request.analysis_depth)
```

### 7.3 Patrol Routes -> `integrations/patrol/`

```python
# CURRENT (mock): api/v1/patrol/routes.py
time.sleep(0.1)  # BLOCKS EVENT LOOP
result = {"status": "healthy", "items_passed": 5}  # FAKE

# TARGET: Import and use real patrol checks
from src.integrations.patrol import PatrolRunner
runner = PatrolRunner()
result = await runner.execute_check(check_type, target=target)
```

### 7.4 Autonomous Routes -> `integrations/claude_sdk/autonomous/`

```python
# CURRENT (mock): api/v1/autonomous/routes.py
steps = [("analyze", "..."), ("plan", "..."), ...]  # HARDCODED TEMPLATES

# TARGET: Import and use real Claude autonomous planning
from src.integrations.claude_sdk.autonomous import AutonomousPlanner
planner = AutonomousPlanner()
plan = await planner.create_plan(goal=request.goal, context=request.context)
```

---

## 8. Architecture Diagram

```
                              +------------------+
                              |   main.py        |
                              |  create_app()    |
                              +--------+---------+
                                       |
                    +------------------+------------------+
                    |                                     |
            +-------+--------+                   +--------+--------+
            | public_router  |                   | protected_router|
            | (no auth)      |                   | (JWT required)  |
            +-------+--------+                   +--------+--------+
                    |                                     |
              auth_router                    +------------+-------------+
              (7 endpoints)                  |            |             |
                                    Tier 1 (DB)   Tier 2 (Real)  Tier 3+4
                                    6 modules     18 modules     15 modules
                                    ~49 EP        ~180 EP        ~311 EP
                                       |              |              |
                                  PostgreSQL    Integration     In-Memory
                                  Repository    Layer (real)    Dict/Mock
                                       |              |
                                  +----+----+   +----+----+
                                  | Agent   |   | Orch    |
                                  | Workflow|   | AG-UI   |
                                  | Execute |   | Hybrid  |
                                  | Session |   | MCP     |
                                  | Auth    |   | Swarm   |
                                  | Dashboard   | Claude  |
                                  +---------+   | n8n     |
                                                +---------+
```

---

## 9. Metrics Summary

| Metric | Value |
|--------|-------|
| Total route modules | 39 |
| Total registered routers | 47 |
| Total estimated endpoints | ~540 |
| DB-backed modules (Tier 1) | 6 (15%) |
| Real integration modules (Tier 2) | 18 (46%) |
| In-memory/legacy modules (Tier 3) | 11 (28%) |
| **100% mock modules (Tier 4)** | **4 (10%)** |
| Modules using proper DI (Depends) | ~8 (20%) |
| Modules using singleton anti-pattern | ~15 (38%) |
| Modules with no DI | ~16 (41%) |
| Error response formats in use | 3 different shapes |
| RBAC-protected destructive endpoints | **0** |
| Pagination patterns in use | 2 (`page/page_size` and `limit/offset`) |

---

**Report Generated By**: Dr. API Design
**Analysis Date**: 2026-03-15
**Files Analyzed**: 25+ route files, main.py, dependencies.py, schemas
**Cross-Referenced**: V8 Issue Registry (62 issues), V8 Plan vs Reality Report
