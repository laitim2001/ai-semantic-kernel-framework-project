# V9 Codebase Statistics Summary

> Generated: 2026-03-29 | Scope: Phase 1-44 | Base: Full file inventory scan

---

## 1. Overall Metrics

| Metric | Value |
|--------|-------|
| **Total Source Files** | 1,090 (793 .py + 297 .ts/.tsx) |
| **Total LOC (estimated)** | ~250,000+ (196K backend + 54K frontend) |
| **Total Phases** | 44 |
| **Total Sprints** | 152+ |
| **Total Story Points** | ~2,500+ |
| **Project Start** | 2025-11-14 |
| **Current Branch** | feature/phase-42-deep-integration |

---

## 2. Backend Breakdown (793 Python files, ~196K LOC)

### By Architectural Layer

| Layer | Directory | Files | Est. LOC | % of Backend |
|-------|-----------|-------|----------|--------------|
| L2: API Gateway | api/v1/ | 107 | ~40,000 | 30.8% |
| L4: Orchestration/Routing | integrations/orchestration/ | 39 | ~16,000 | 12.3% |
| L5: Hybrid Orchestration | integrations/hybrid/ | 75 | ~24,000 | 18.5% |
| L6: MAF Builders | integrations/agent_framework/ | 62 | ~38,000 | 29.2% |
| L7: Claude SDK | integrations/claude_sdk/ | 39 | ~15,000 | 11.5% |
| L8: MCP Tools | integrations/mcp/ | 43 | ~21,000 | 16.2% |
| L3: AG-UI Protocol | integrations/ag_ui/ | 22 | ~10,000 | 7.7% |
| L9: Supporting Integrations | integrations/{swarm,patrol,...} | 75 | ~21,300 | 12.4% |
| L10: Domain Layer | domain/ | 117 | ~47,637 | 27.8% |
| L11: Infrastructure | infrastructure/ | 54 | ~9,901 | 5.8% |
| L11: Core | core/ | 39 | ~11,945 | 7.0% |
| Middleware | middleware/ | 2 | ~107 | 0.1% |

### By Module Category

| Category | Modules | Files | % of Backend |
|----------|---------|-------|--------------|
| Integrations | 19 | 340 | 42.9% |
| API Routes | 48 | 107 | 13.5% |
| Domain | 21 | 117 | 14.8% |
| Infrastructure | 7 | 54 | 6.8% |
| Core | 5 | 39 | 4.9% |
| __init__.py | — | 184 | 23.2% |
| Middleware | 1 | 2 | 0.3% |

### Top 10 Largest Backend Modules (by file count)

| # | Module | Files | Est. LOC |
|---|--------|-------|----------|
| 1 | integrations/hybrid/ | 75 | ~24,000 |
| 2 | integrations/agent_framework/ | 62 | ~38,000 |
| 3 | integrations/mcp/ | 43 | ~21,000 |
| 4 | integrations/orchestration/ | 39 | ~16,000 |
| 5 | integrations/claude_sdk/ | 39 | ~15,000 |
| 6 | domain/sessions/ | 33 | ~15,473 |
| 7 | integrations/ag_ui/ | 22 | ~10,000 |
| 8 | domain/orchestration/ | 22 | ~11,465 |
| 9 | core/performance/ | 10 | ~5,100 |
| 10 | infrastructure/storage/ | 14 | ~3,800 |

---

## 3. Frontend Breakdown (297 TypeScript/React files, ~54K LOC)

### By Module

| Module | Files | LOC | % of Frontend |
|--------|-------|-----|---------------|
| components/unified-chat/ (core) | 29 | ~9,346 | 17.2% |
| components/unified-chat/agent-swarm/ | 16 + 12 tests + 5 hooks + 2 types | ~5,500 | 10.1% |
| components/unified-chat/renderers/ | 4 | ~709 | 1.3% |
| components/ag-ui/ | 19 | ~3,400 | 6.3% |
| components/DevUI/ | 15 | ~4,644 | 8.6% |
| components/ui/ | 18 | ~1,471 | 2.7% |
| components/workflow-editor/ | 10 | ~1,383 | 2.6% |
| components/layout/ | 5 | ~422 | 0.8% |
| components/shared/ | 4 | ~128 | 0.2% |
| components/auth/ | 1 | ~128 | 0.2% |
| hooks/ | 25 | ~11,286 | 20.8% |
| pages/ (all) | 38 | ~12,500 | 23.1% |
| api/ | 11 | ~1,824 | 3.4% |
| stores/ + store/ | 3 + 1 | ~1,693 | 3.1% |
| types/ | 4 | ~1,297 | 2.4% |
| utils/ + lib/ | 2 | ~340 | 0.6% |

### Top 10 Largest Frontend Files

| # | File | LOC |
|---|------|-----|
| 1 | pages/UnifiedChat.tsx | 1,403 |
| 2 | hooks/useUnifiedChat.ts | 1,313 |
| 3 | pages/workflows/EditWorkflowPage.tsx | 1,040 |
| 4 | pages/agents/CreateAgentPage.tsx | 1,015 |
| 5 | hooks/useAGUI.ts | 982 |
| 6 | pages/agents/EditAgentPage.tsx | 958 |
| 7 | pages/SwarmTestPage.tsx | 844 |
| 8 | hooks/useSwarmMock.ts | 623 |
| 9 | hooks/useSwarmReal.ts | 603 |
| 10 | pages/DevUI/TraceDetail.tsx | 562 |

---

## 4. API Surface

| Metric | Count |
|--------|-------|
| API Route Modules | 48 |
| Estimated Endpoints | 560+ |
| Auth-Protected Routes | ~530 (via protected_router) |
| Public Routes | ~30 (health, auth/login, auth/signup) |

---

## 5. Data Model Summary

| Layer | Type | Count |
|-------|------|-------|
| Database | SQLAlchemy Models | 8 (User, Agent, Workflow, Execution, Checkpoint, Audit, Session, Message) |
| Backend | Pydantic Schema Files | 38 |
| Backend | Pydantic BaseModel Classes | ~690 |
| Frontend | TypeScript Type Files | 4 |
| Frontend | Interface/Type Definitions | ~1,000+ |
| Frontend | Zustand Stores | 3 (auth, unifiedChat, swarm) |

---

## 6. Event & Contract Summary

| System | Event Types | Location |
|--------|-------------|----------|
| Pipeline SSE | 14 | integrations/hybrid/orchestrator/sse_events.py |
| AG-UI Protocol | 11 | integrations/ag_ui/events/ |
| Swarm Events | 9 | integrations/swarm/events/ |
| Routing Contracts | 6 enums + 2 models | integrations/orchestration/contracts.py |
| **Total** | **40+** | |

---

## 7. Testing Summary

| Category | Files | Coverage Target |
|----------|-------|-----------------|
| Backend Unit Tests | 241 | 80% fail_under |
| Backend Integration Tests | 24 | — |
| Backend E2E Tests | 19 | — |
| Backend Security Tests | 5 | — |
| Backend Performance Tests | 5 | — |
| Backend Load Tests | 2 | — |
| Frontend Unit Tests | 13 (12 swarm + 1 store) | — |
| Frontend E2E Tests | 9 | — |
| **Total Test Files** | **318** | |

---

## 8. Configuration Surface

| Category | Count |
|----------|-------|
| Environment Variables | 170+ |
| Docker Services (dev) | 6 (postgres, redis, rabbitmq, jaeger, prometheus, grafana) |
| Docker Services (prod) | 4 (backend, frontend, postgres, redis) |
| Python Dependencies | 40+ packages |
| npm Dependencies | 30+ packages |
| MCP Servers | 8 |
| MCP Tools | 64 |

---

## 9. Mock vs Real Status

| Category | Real | Mock/InMemory | Stub |
|----------|------|---------------|------|
| LLM Service | Azure OpenAI (if configured) | MockLLMService (default) | — |
| Semantic Router | Aurelio/Azure AI Search (if configured) | MockSemanticRouter (default) | — |
| LLM Classifier | Azure/Claude (if configured) | Returns UNKNOWN (default) | — |
| Message Queue | — | — | RabbitMQ (STUB, 1 line) |
| Approval Storage | 3 independent systems | All InMemory | — |
| Domain Storage | 4/21 modules use DB | 6+ modules InMemory only | — |
| Frontend Swarm | useSwarmReal.ts | useSwarmMock.ts | — |

---

## 10. Phase Coverage Delta (V8 → V9)

| Metric | V8 (2026-03-15) | V9 (2026-03-29) | Delta |
|--------|-----------------|-----------------|-------|
| Phases | 1-34 | 1-44 | +10 phases |
| Sprints | ~133 | ~152 | +19 sprints |
| Source Files | 939 | 1,090 | +151 files |
| LOC | ~160K | ~250K | +90K LOC (R4 corrected; prior V9 estimate was ~184K) |
| Features Tracked | 70+15 | TBD (V9 analysis) | — |
| Issues Tracked | 62 | TBD (V9 analysis) | — |
