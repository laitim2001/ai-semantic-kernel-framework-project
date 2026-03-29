# V9 Codebase Analysis — Master Index

> **Generated**: 2026-03-29 | **Scope**: Phase 1-44 | **Predecessor**: V8 (Phase 1-34)
> **Purpose**: Machine-readable navigation index for all V9 analysis documents

---

## 1. Statistics Summary

| Metric | Value |
|--------|-------|
| **Total V9 Files** | 32 (.md) |
| **Total V9 Size** | ~1,145 KB (1.12 MB) |
| **Analysis Scope** | 1,090 source files (793 .py + 297 .ts/.tsx), ~184K LOC |
| **Phases Covered** | 1-44 (152+ sprints, ~2,500+ story points) |
| **Categories** | 13 topical directories + 2 root files |
| **Date** | 2026-03-29 |

---

## 2. File Registry

### Root Files

| File | Size | Description | Tags |
|------|------|-------------|------|
| `ANALYSIS-PLAN-V9.md` | 26 KB | V9 analysis methodology, V8 gap analysis, 13-category plan | `plan`, `methodology`, `v8-gap`, `scope` |
| `00-stats.md` | 7 KB | Codebase statistics: file counts, LOC, layer breakdown | `statistics`, `metrics`, `loc`, `file-count` |
| `00-index.md` | — | This file. Master navigation index | `index`, `navigation` |

### 01-architecture (11 files)

| File | Size | Description | Tags |
|------|------|-------------|------|
| `layer-01-frontend.md` | 27 KB | L1: React 18 frontend — pages, components, hooks, stores, routing | `frontend`, `react`, `typescript`, `ui`, `components` |
| `layer-02-api-gateway.md` | 63 KB | L2: FastAPI API gateway — 39 route modules, endpoints, middleware | `api`, `fastapi`, `routes`, `endpoints`, `middleware` |
| `layer-03-ag-ui.md` | 26 KB | L3: AG-UI protocol — SSE streaming, events, handlers | `ag-ui`, `sse`, `events`, `streaming`, `protocol` |
| `layer-04-routing.md` | 43 KB | L4: Intent routing — three-tier orchestration, intent classification | `routing`, `intent`, `orchestration`, `classification` |
| `layer-05-orchestration.md` | 42 KB | L5: Hybrid orchestration — MAF+Claude SDK switching, context, risk | `orchestration`, `hybrid`, `maf`, `claude-sdk`, `switching` |
| `layer-06-maf-builders.md` | 40 KB | L6: MAF builders — 30+ builders, ConcurrentBuilder, GroupChat, Handoff | `maf`, `builders`, `agents`, `concurrent`, `groupchat` |
| `layer-07-claude-sdk.md` | 40 KB | L7: Claude SDK integration — autonomous, hooks, hybrid, MCP, tools | `claude-sdk`, `autonomous`, `hooks`, `mcp`, `tools` |
| `layer-08-mcp-tools.md` | 41 KB | L8: MCP tool servers — Azure, Filesystem, LDAP, Shell, SSH | `mcp`, `tools`, `azure`, `filesystem`, `ldap`, `shell` |
| `layer-09-integrations.md` | 45 KB | L9: Integration modules — A2A, memory, patrol, correlation, learning | `integrations`, `a2a`, `memory`, `patrol`, `correlation` |
| `layer-10-domain.md` | 44 KB | L10: Domain layer — 20 domain modules, business logic, services | `domain`, `business-logic`, `services`, `models` |
| `layer-11-infrastructure.md` | 44 KB | L11: Infrastructure — DB, cache, messaging, storage, migrations | `infrastructure`, `database`, `redis`, `rabbitmq`, `storage` |

### 02-modules (4 files)

| File | Size | Description | Tags |
|------|------|-------------|------|
| `mod-integration-batch1.md` | 38 KB | Integration modules batch 1: agent_framework, claude_sdk, ag_ui, hybrid | `modules`, `agent-framework`, `claude-sdk`, `ag-ui`, `hybrid` |
| `mod-integration-batch2.md` | 37 KB | Integration modules batch 2: orchestration, swarm, a2a, mcp | `modules`, `orchestration`, `swarm`, `a2a`, `mcp` |
| `mod-domain-infra-core.md` | 37 KB | Domain, infrastructure, and core modules analysis | `modules`, `domain`, `infrastructure`, `core` |
| `mod-frontend.md` | 36 KB | Frontend modules: pages, components, hooks, stores, API client | `modules`, `frontend`, `pages`, `hooks`, `stores` |

### 03-features (2 files)

| File | Size | Description | Tags |
|------|------|-------------|------|
| `features-cat-a-to-e.md` | 26 KB | Feature verification categories A-E (agent mgmt, workflow, execution, chat, HITL) | `features`, `agents`, `workflows`, `execution`, `chat`, `hitl` |
| `features-cat-f-to-j.md` | 35 KB | Feature verification categories F-J (monitoring, security, MCP, swarm, A2A) | `features`, `monitoring`, `security`, `mcp`, `swarm`, `a2a` |

### 04-flows (2 files)

| File | Size | Description | Tags |
|------|------|-------------|------|
| `flows-01-to-05.md` | 38 KB | E2E flows 1-5: Chat, CRUD, Workflow execution, HITL approval, Swarm | `flows`, `e2e`, `chat`, `crud`, `workflow`, `hitl`, `swarm` |
| `flows-06-to-08.md` | 28 KB | E2E flows 6-8: Pipeline assembly, autonomous agent, MCP tool chain | `flows`, `e2e`, `pipeline`, `autonomous`, `mcp` |

### 05-issues (1 file)

| File | Size | Description | Tags |
|------|------|-------------|------|
| `issue-registry.md` | 54 KB | Consolidated issue registry — all CRITICAL/HIGH/MEDIUM/LOW issues with status | `issues`, `bugs`, `critical`, `high`, `medium`, `low`, `registry` |

### 06-cross-cutting (1 file)

| File | Size | Description | Tags |
|------|------|-------------|------|
| `cross-cutting-analysis.md` | 28 KB | Cross-cutting concerns: security, error handling, logging, performance, i18n | `cross-cutting`, `security`, `error-handling`, `logging`, `performance` |

### 07-delta (3 files)

| File | Size | Description | Tags |
|------|------|-------------|------|
| `delta-phase-35-38.md` | 16 KB | Delta: Phase 35-38 changes (E2E Assembly core + foundation + task + memory) | `delta`, `phase-35`, `phase-36`, `phase-37`, `phase-38`, `e2e` |
| `delta-phase-39-42.md` | 16 KB | Delta: Phase 39-42 changes (pipeline assembly, UI, chat integration, deep integration) | `delta`, `phase-39`, `phase-40`, `phase-41`, `phase-42`, `pipeline` |
| `delta-phase-43-44.md` | 14 KB | Delta: Phase 43-44 changes (swarm deep dive, agent team PoC) | `delta`, `phase-43`, `phase-44`, `swarm`, `agent-team`, `poc` |

### 08-data-model (1 file)

| File | Size | Description | Tags |
|------|------|-------------|------|
| `data-model-analysis.md` | 45 KB | Data model: all SQLAlchemy models, relationships, migrations, schema | `data-model`, `database`, `sqlalchemy`, `models`, `migrations`, `schema` |

### 09-api-reference (1 file)

| File | Size | Description | Tags |
|------|------|-------------|------|
| `api-reference.md` | 79 KB | Complete API reference: all 39 route modules, endpoints, request/response schemas | `api`, `endpoints`, `routes`, `rest`, `schemas`, `reference` |

### 10-event-contracts (1 file)

| File | Size | Description | Tags |
|------|------|-------------|------|
| `event-contracts.md` | 27 KB | Event contracts: SSE events, WebSocket messages, AG-UI protocol events | `events`, `sse`, `websocket`, `ag-ui`, `contracts`, `protocol` |

### 11-config-deploy (1 file)

| File | Size | Description | Tags |
|------|------|-------------|------|
| `config-deploy.md` | 39 KB | Configuration and deployment: env vars, Docker, settings, service ports | `config`, `deployment`, `docker`, `env`, `settings`, `ports` |

### 12-testing (1 file)

| File | Size | Description | Tags |
|------|------|-------------|------|
| `testing-landscape.md` | 38 KB | Testing landscape: test inventory, coverage, fixtures, gaps | `testing`, `pytest`, `coverage`, `fixtures`, `test-gaps` |

### 13-mock-real (1 file)

| File | Size | Description | Tags |
|------|------|-------------|------|
| `mock-real-map.md` | 28 KB | Mock vs real implementation map: what is stub/mock vs production-ready | `mock`, `real`, `implementation`, `stub`, `production-ready` |

---

## 3. Category Index

| # | Category | Files | Total Size | Primary Purpose |
|---|----------|-------|------------|-----------------|
| 01 | Architecture | 11 | 455 KB | 11-layer deep-dive (frontend through infrastructure) |
| 02 | Modules | 4 | 148 KB | Per-module analysis (integrations, domain, frontend) |
| 03 | Features | 2 | 61 KB | 70+ feature verification across 10 categories |
| 04 | Flows | 2 | 66 KB | 8 end-to-end user journey validations |
| 05 | Issues | 1 | 54 KB | Consolidated issue registry with severity and status |
| 06 | Cross-Cutting | 1 | 28 KB | Security, logging, error handling, performance |
| 07 | Delta | 3 | 46 KB | Phase 35-44 incremental changes (V8 was Phase 1-34) |
| 08 | Data Model | 1 | 45 KB | SQLAlchemy models, relationships, schema |
| 09 | API Reference | 1 | 79 KB | Complete REST API endpoint catalog |
| 10 | Event Contracts | 1 | 27 KB | SSE/WebSocket/AG-UI event specifications |
| 11 | Config & Deploy | 1 | 39 KB | Environment, Docker, settings, ports |
| 12 | Testing | 1 | 38 KB | Test inventory, coverage, gaps |
| 13 | Mock/Real Map | 1 | 28 KB | Implementation maturity per component |

---

## 4. Quick Lookup Table

| Question | File to Read |
|----------|-------------|
| How does the 11-layer architecture work? | `01-architecture/layer-01-frontend.md` through `layer-11-infrastructure.md` |
| How does intent routing work? | `01-architecture/layer-04-routing.md` |
| How does hybrid orchestration work? | `01-architecture/layer-05-orchestration.md` |
| How do MAF builders work? | `01-architecture/layer-06-maf-builders.md` |
| How does Claude SDK integrate? | `01-architecture/layer-07-claude-sdk.md` |
| What MCP tools are available? | `01-architecture/layer-08-mcp-tools.md` |
| What are all the API endpoints? | `09-api-reference/api-reference.md` |
| What issues exist? | `05-issues/issue-registry.md` |
| What is mock vs real? | `13-mock-real/mock-real-map.md` |
| What features are implemented? | `03-features/features-cat-a-to-e.md` + `features-cat-f-to-j.md` |
| What changed in Phase 35-38? | `07-delta/delta-phase-35-38.md` |
| What changed in Phase 39-42? | `07-delta/delta-phase-39-42.md` |
| What changed in Phase 43-44? | `07-delta/delta-phase-43-44.md` |
| What does the data model look like? | `08-data-model/data-model-analysis.md` |
| What events/contracts exist? | `10-event-contracts/event-contracts.md` |
| How is testing organized? | `12-testing/testing-landscape.md` |
| What are the cross-cutting concerns? | `06-cross-cutting/cross-cutting-analysis.md` |
| How is config/deployment set up? | `11-config-deploy/config-deploy.md` |
| How does the frontend work? | `01-architecture/layer-01-frontend.md` + `02-modules/mod-frontend.md` |
| How does the API gateway work? | `01-architecture/layer-02-api-gateway.md` |
| How does AG-UI protocol work? | `01-architecture/layer-03-ag-ui.md` |
| What integration modules exist? | `02-modules/mod-integration-batch1.md` + `mod-integration-batch2.md` |
| What domain/infra modules exist? | `02-modules/mod-domain-infra-core.md` |
| What are the E2E user journeys? | `04-flows/flows-01-to-05.md` + `flows-06-to-08.md` |
| What is the codebase size? | `00-stats.md` |
| What was the V9 analysis plan? | `ANALYSIS-PLAN-V9.md` |

---

## 5. V9 vs V8 Comparison

| Dimension | V8 (2026-03-15) | V9 (2026-03-29) |
|-----------|-----------------|-----------------|
| **Phase Coverage** | Phase 1-34 | Phase 1-44 (+10 phases) |
| **Source Files Scanned** | 939 | 1,090 (+151 files) |
| **LOC Estimated** | ~140K | ~184K (+44K) |
| **Architecture Depth** | 2 monolithic docs (2,721 + 1,518 lines) | 11 per-layer files (455 KB total) |
| **Module Analysis** | Embedded in architecture doc | 4 dedicated module files (148 KB) |
| **Feature Verification** | 70 features in single doc | Split A-E / F-J for searchability (61 KB) |
| **E2E Flows** | 5 flows | 8 flows (+pipeline, autonomous, MCP chain) |
| **Issue Registry** | 62 issues in single doc | Updated consolidated registry (54 KB) |
| **Delta Coverage** | None (snapshot only) | 3 delta files covering Phase 35-44 |
| **Data Model** | Not covered | Dedicated analysis (45 KB) |
| **API Reference** | Not covered | Complete 39-module catalog (79 KB) |
| **Event Contracts** | Not covered | SSE/WS/AG-UI specifications (27 KB) |
| **Config & Deploy** | Not covered | Environment/Docker/settings (39 KB) |
| **Testing Landscape** | Not covered | Test inventory + coverage gaps (38 KB) |
| **Mock/Real Map** | Not covered | Implementation maturity map (28 KB) |
| **Cross-Cutting** | Partially in architecture doc | Dedicated analysis (28 KB) |
| **Machine Readability** | Narrative format | Structured tables, tags, quick lookup |

### V9 New Categories (Not in V8)
- **07-delta**: Phase-by-phase incremental changes (V8 was a single snapshot)
- **08-data-model**: SQLAlchemy model and schema analysis
- **09-api-reference**: Complete REST endpoint catalog
- **10-event-contracts**: Event/message specifications
- **11-config-deploy**: Configuration and deployment analysis
- **12-testing**: Test landscape and coverage analysis
- **13-mock-real**: Mock vs real implementation maturity

---

*End of V9 Master Index*
