# V9 Codebase Analysis — Master Index

> **Generated**: 2026-03-29 | **Scope**: Phase 1-44 | **Predecessor**: V8 (Phase 1-34)
> **Purpose**: Machine-readable navigation index for all V9 analysis documents

---

## 1. Statistics Summary

| Metric | Value |
|--------|-------|
| **Total V9 Files** | 52+ (.md + .json) |
| **Total V9 Size** | ~6.7 MB (1.7 MB .md + 5 MB metadata JSON) |
| **Analysis Scope** | 1,029 source files (793 .py + 236 .ts/.tsx), ~327K LOC |
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
| `00-r3-final-report.md` | 8 KB | Round 3 final report: programmatic AST verification results | `report`, `round-3`, `ast`, `verification` |
| `00-r4-final-report.md` | 14 KB | Round 4 final report: full semantic coverage, corrected statistics, new issues | `report`, `round-4`, `semantic`, `final` |
| `00-verification-report.md` | 10 KB | Round 2 verification report: agent-driven source reading | `report`, `round-2`, `verification` |
| `VERIFICATION-PLAN.md` | 5 KB | Round 2 verification methodology and agent assignments | `plan`, `round-2`, `verification` |
| `ROUND3-PLAN.md` | 4 KB | Round 3 programmatic scan methodology | `plan`, `round-3`, `ast` |
| `ROUND4-PLAN.md` | 4 KB | Round 4 full semantic coverage methodology | `plan`, `round-4`, `semantic` |
| `enhanced-backend-metadata.json` | ~5 MB | Enhanced AST metadata: all 793 .py files with docstrings, enums, TODOs, configs, errors, decorators | `metadata`, `ast`, `json`, `backend`, `round-4` |

### 01-architecture (11 files + 8 verification files)

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
| `layer-05-verification.md` | — | R2: Layer 5 hybrid orchestration verification | `verification`, `round-2`, `hybrid` |
| `layer-06-07-verification.md` | — | R2: Layer 6-7 MAF + Claude SDK verification | `verification`, `round-2`, `maf`, `claude-sdk` |
| `layer-04-08-09-verification.md` | — | R2: Layer 4, 8, 9 routing + MCP + integrations verification | `verification`, `round-2`, `routing`, `mcp` |
| `layer-10-verification.md` | — | R2: Layer 10 domain verification | `verification`, `round-2`, `domain` |
| `layer-11-verification.md` | — | R2: Layer 11 infrastructure verification | `verification`, `round-2`, `infrastructure` |
| `layer-01-pages-hooks-verification.md` | — | R2: Frontend pages + hooks verification | `verification`, `round-2`, `frontend`, `hooks` |
| `layer-01-components-verification.md` | — | R2: Frontend components verification | `verification`, `round-2`, `frontend`, `components` |
| `domain-r3-verification.md` | — | R3: Domain layer AST verification | `verification`, `round-3`, `domain` |
| `infra-r3-verification.md` | — | R3: Infrastructure layer AST verification | `verification`, `round-3`, `infrastructure` |
| `frontend-r3-verification.md` | — | R3: Frontend regex scan verification | `verification`, `round-3`, `frontend` |

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
| `api-verification.md` | — | R2: API gateway verification report | `verification`, `round-2`, `api` |
| `api-r3-verification.md` | — | R3: API layer AST verification report | `verification`, `round-3`, `api` |

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

### R4-semantic (5 files — Round 4 per-file semantic summaries)

| File | Size | Description | Tags |
|------|------|-------------|------|
| `api-v1-semantic.md` | ~80 KB | Per-file semantic summaries: 107 API route files, 594 endpoints, 634 schemas | `semantic`, `round-4`, `api`, `endpoints`, `per-file` |
| `integrations-hybrid-orch-agui-semantic.md` | ~60 KB | Per-file semantic summaries: hybrid/ + orchestration/ + ag_ui/ (~130 files, ~50K LOC) | `semantic`, `round-4`, `hybrid`, `orchestration`, `ag-ui`, `per-file` |
| `integrations-maf-claude-mcp-semantic.md` | ~70 KB | Per-file semantic summaries: agent_framework/ + claude_sdk/ + mcp/ (176 files, 74K LOC) | `semantic`, `round-4`, `maf`, `claude-sdk`, `mcp`, `per-file` |
| `backend-remaining-semantic.md` | ~50 KB | Per-file semantic summaries: remaining integrations + domain/ + infrastructure/ + core/ (~287 files, ~91K LOC) | `semantic`, `round-4`, `domain`, `infrastructure`, `swarm`, `patrol`, `per-file` |
| `frontend-semantic.md` | ~40 KB | Per-file semantic summaries: all frontend src/ files (236 files, 54K LOC) | `semantic`, `round-4`, `frontend`, `react`, `hooks`, `per-file` |

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
| R4 | Semantic Summaries | 5 | ~300 KB | Per-file semantic summaries for all 832+ source files |
| — | Root Reports | 7 | ~120 KB | Plans, stats, index, round reports, metadata JSON |
| — | Enhanced Metadata | 1 | ~5 MB | Machine-readable AST metadata for all 793 .py files |

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
| What does a specific file do? | `R4-semantic/` — search the 5 semantic summary files for per-file summaries |
| What are the Round 4 corrections? | `00-r4-final-report.md` |
| What are the Round 3 AST results? | `00-r3-final-report.md` |
| What are the Round 2 verification results? | `00-verification-report.md` |
| What metadata exists for backend files? | `enhanced-backend-metadata.json` |
| How many TODOs/configs/errors exist? | `enhanced-backend-metadata.json` summary section |

---

## 5. V9 vs V8 Comparison

| Dimension | V8 (2026-03-15) | V9 (2026-03-29) |
|-----------|-----------------|-----------------|
| **Phase Coverage** | Phase 1-34 | Phase 1-44 (+10 phases) |
| **Source Files Scanned** | 939 | 1,029 (793 .py + 236 .ts/.tsx) |
| **LOC Verified** | ~140K | **327,583** (273K backend + 54K frontend) |
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
| **Semantic Coverage** | Manual reading of ~100 key files | 100% per-file semantic summaries (R4) |
| **Metadata Extraction** | None | Enhanced AST metadata for all 793 .py files |
| **Analysis Rounds** | 1 (snapshot) | 4 (structural → verification → AST → semantic) |
| **Total V9 Output** | — | 52+ files, ~6.7 MB |

### V9 New Categories (Not in V8)
- **07-delta**: Phase-by-phase incremental changes (V8 was a single snapshot)
- **08-data-model**: SQLAlchemy model and schema analysis
- **09-api-reference**: Complete REST endpoint catalog
- **10-event-contracts**: Event/message specifications
- **11-config-deploy**: Configuration and deployment analysis
- **12-testing**: Test landscape and coverage analysis
- **13-mock-real**: Mock vs real implementation maturity
- **R4-semantic**: Per-file semantic summaries for all 832+ source files (Round 4)
- **Root reports**: Round 2/3/4 reports, verification plans, enhanced metadata JSON

---

### V9 Round History

| Round | Date | Method | Coverage | Key Output |
|-------|------|--------|----------|------------|
| R1 | 2026-03-29 | Structural estimates from file inventory | 14% (121/832 files) | 32 analysis docs, ~1.1 MB |
| R2 | 2026-03-29 | Agent-driven source reading + verification | 54% (~450/832 files) | 8 verification reports |
| R3 | 2026-03-29 | Programmatic AST + regex scan | 100% structural (1,029 files) | 2 metadata JSONs, 1 final report |
| R4 | 2026-03-29 | Full semantic reading + enhanced AST + V9 sync | **100% semantic** (1,029 files) | 5 semantic files, enhanced metadata, 10 new issues |

---

*End of V9 Master Index*
