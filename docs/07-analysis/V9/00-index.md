# V9 Codebase Analysis — Master Index

> **Generated**: 2026-03-29 | **Scope**: Phase 1-44 | **Predecessor**: V8 (Phase 1-34)
> **Purpose**: Machine-readable navigation index for all V9 analysis documents

---

## 1. Statistics Summary

| Metric | Value |
|--------|-------|
| **Total V9 Files** | 36 analysis .md files (13 dirs) + 60+ verification archive files |
| **Analysis Scope** | 1,029 source files (793 .py + 236 .ts/.tsx), 327,583 LOC |
| **Phases Covered** | 1-44 (152+ sprints, ~2,500+ story points) |
| **Categories** | 13 topical directories (01-13) + _verification/ archive |
| **Verification Rounds** | R1-R9 (9 rounds, 94.5% programmatic + AI semantic) |
| **Last Updated** | 2026-03-31 |

---

## 2. File Registry

### Root Files (V9/)

| File | Size | Description | Tags |
|------|------|-------------|------|
| `00-index.md` | — | This file. Master navigation index | `index`, `navigation` |
| `00-stats.md` | 7 KB | Codebase statistics: file counts, LOC, layer breakdown | `statistics`, `metrics`, `loc`, `file-count` |
| `r5-imports.json` | — | Round 5 import scan data (JSON) | `imports`, `json`, `round-5` |

### Verification Plans & Reports (_verification/)

> All plans, round reports, semantic summaries, and metadata reside under `_verification/`.

| File | Location | Size | Description | Tags |
|------|----------|------|-------------|------|
| `ANALYSIS-PLAN-V9.md` | `_verification/plans/` | 26 KB | V9 analysis methodology, V8 gap analysis, 13-category plan | `plan`, `methodology`, `v8-gap`, `scope` |
| `VERIFICATION-PLAN.md` | `_verification/plans/` | 5 KB | Round 2 verification methodology and agent assignments | `plan`, `round-2`, `verification` |
| `ROUND3-PLAN.md` | `_verification/plans/` | 4 KB | Round 3 programmatic scan methodology | `plan`, `round-3`, `ast` |
| `ROUND4-PLAN.md` | `_verification/plans/` | 4 KB | Round 4 full semantic coverage methodology | `plan`, `round-4`, `semantic` |
| `ROUND5-PLAN.md` | `_verification/plans/` | — | Round 5 programmatic re-scan plan | `plan`, `round-5` |
| `ROUND6-PLAN.md` | `_verification/plans/` | — | Round 6 validation plan | `plan`, `round-6` |
| `00-verification-report.md` | `_verification/reports/` | 10 KB | Round 2 verification report: agent-driven source reading | `report`, `round-2`, `verification` |
| `00-r3-final-report.md` | `_verification/reports/` | 8 KB | Round 3 final report: programmatic AST verification results | `report`, `round-3`, `ast`, `verification` |
| `00-r4-final-report.md` | `_verification/reports/` | 14 KB | Round 4 final report: full semantic coverage, corrected statistics, new issues | `report`, `round-4`, `semantic`, `final` |
| `r6-validation-report.md` | `_verification/reports/` | — | Round 6 validation report | `report`, `round-6`, `validation` |
| `r7-validation-report.md` | `_verification/reports/` | — | Round 7 validation report | `report`, `round-7`, `validation` |
| `r7-enhanced-validation-report.md` | `_verification/reports/` | — | Round 7 enhanced validation report (7 dimensions) | `report`, `round-7`, `enhanced` |
| `r8-gap-report.md` | `_verification/reports/` | — | Round 8 gap analysis report | `report`, `round-8`, `gap` |
| `r8-per-layer-coverage.md` | `_verification/reports/` | — | Round 8 per-layer coverage report | `report`, `round-8`, `coverage` |
| `r9-semantic-verification-report.md` | `_verification/reports/` | — | Round 9 semantic verification report | `report`, `round-9`, `semantic` |
| `enhanced-backend-metadata.json` | `_verification/r5-data/` | ~5 MB | Enhanced AST metadata: all 793 .py files with docstrings, enums, TODOs, configs, errors, decorators | `metadata`, `ast`, `json`, `backend` |
| `backend-metadata.json` | `_verification/r5-data/` | — | Backend AST metadata (base) | `metadata`, `ast`, `json`, `backend` |
| `frontend-metadata.json` | `_verification/r5-data/` | — | Frontend metadata scan results | `metadata`, `json`, `frontend` |
| `r5-comparison-report.md` | `_verification/r5-data/` | — | Round 5 comparison report (markdown) | `report`, `round-5`, `comparison` |

> **Additional JSON data files** (not individually listed): `_verification/r5-data/` also contains 7 programmatic scan artifacts (`r5-classes.json`, `r5-enums.json`, `r5-frontend.json`, `r5-imports.json`, `r5-routes.json`, `r5-schemas.json`, `r5-comparison-report.json`). `_verification/reports/` contains `r6-validation-report.json`.

### 01-architecture (11 files)

| File | Size | Description | Tags |
|------|------|-------------|------|
| `layer-01-frontend.md` | 27 KB | L1: React 18 frontend — pages, components, hooks, stores, routing | `frontend`, `react`, `typescript`, `ui`, `components` |
| `layer-02-api-gateway.md` | 63 KB | L2: FastAPI API gateway — 39 route modules, endpoints, middleware | `api`, `fastapi`, `routes`, `endpoints`, `middleware` |
| `layer-03-ag-ui.md` | 26 KB | L3: AG-UI protocol — SSE streaming, events, handlers | `ag-ui`, `sse`, `events`, `streaming`, `protocol` |
| `layer-04-routing.md` | 43 KB | L4: Intent routing — three-tier orchestration, intent classification | `routing`, `intent`, `orchestration`, `classification` |
| `layer-05-orchestration.md` | 42 KB | L5: Hybrid orchestration — MAF+Claude SDK switching, context, risk | `orchestration`, `hybrid`, `maf`, `claude-sdk`, `switching` |
| `layer-06-maf-builders.md` | 40 KB | L6: MAF builders — 23 builders, ConcurrentBuilder, GroupChat, Handoff | `maf`, `builders`, `agents`, `concurrent`, `groupchat` |
| `layer-07-claude-sdk.md` | 40 KB | L7: Claude SDK integration — autonomous, hooks, hybrid, MCP, tools | `claude-sdk`, `autonomous`, `hooks`, `mcp`, `tools` |
| `layer-08-mcp-tools.md` | 41 KB | L8: MCP tool servers — Azure, Filesystem, LDAP, Shell, SSH | `mcp`, `tools`, `azure`, `filesystem`, `ldap`, `shell` |
| `layer-09-integrations.md` | 45 KB | L9: Integration modules — A2A, memory, patrol, correlation, learning | `integrations`, `a2a`, `memory`, `patrol`, `correlation` |
| `layer-10-domain.md` | 44 KB | L10: Domain layer — 20 domain modules, business logic, services | `domain`, `business-logic`, `services`, `models` |
| `layer-11-infrastructure.md` | 44 KB | L11: Infrastructure — DB, cache, messaging, storage, migrations | `infrastructure`, `database`, `redis`, `rabbitmq`, `storage` |

> Layer verification files are in `_verification/layer-verification/` — see [Verification Archive](#verification-archive) below.

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

### 06-cross-cutting (5 files)

| File | Size | Description | Tags |
|------|------|-------------|------|
| `cross-cutting-analysis.md` | 28 KB | Cross-cutting concerns: error handling, logging, performance, i18n | `cross-cutting`, `error-handling`, `logging`, `performance` |
| `security-architecture.md` | — | 6-Layer Defense-in-Depth security model analysis | `security`, `defense-in-depth`, `authentication`, `authorization` |
| `dependency-analysis.md` | — | Full backend dependency graph across 27 top-level modules, 793 Python files | `dependencies`, `imports`, `coupling`, `fan-in`, `fan-out` |
| `enum-registry.md` | — | Consolidated registry of all enums across backend and frontend | `enums`, `registry`, `constants`, `types` |
| `memory-architecture.md` | — | Memory system architecture analysis (mem0, Qdrant, session memory) | `memory`, `mem0`, `qdrant`, `session`, `architecture` |

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

> API verification files are in `_verification/layer-verification/` — see [Verification Archive](#verification-archive) below.

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

### R4-semantic (5 files — in `_verification/R4-semantic/`)

> These files reside at `_verification/R4-semantic/`, not at the V9 root.

| File | Size | Description | Tags |
|------|------|-------------|------|
| `api-v1-semantic.md` | ~80 KB | Per-file semantic summaries: 107 API route files, 572 endpoints, 634 schemas | `semantic`, `round-4`, `api`, `endpoints`, `per-file` |
| `integrations-hybrid-orch-agui-semantic.md` | ~60 KB | Per-file semantic summaries: hybrid/ + orchestration/ + ag_ui/ (~130 files, ~50K LOC) | `semantic`, `round-4`, `hybrid`, `orchestration`, `ag-ui`, `per-file` |
| `integrations-maf-claude-mcp-semantic.md` | ~70 KB | Per-file semantic summaries: agent_framework/ + claude_sdk/ + mcp/ (176 files, 74K LOC) | `semantic`, `round-4`, `maf`, `claude-sdk`, `mcp`, `per-file` |
| `backend-remaining-semantic.md` | ~50 KB | Per-file semantic summaries: remaining integrations + domain/ + infrastructure/ + core/ (~287 files, ~91K LOC) | `semantic`, `round-4`, `domain`, `infrastructure`, `swarm`, `patrol`, `per-file` |
| `frontend-semantic.md` | ~40 KB | Per-file semantic summaries: all frontend src/ files (236 files, 54K LOC) | `semantic`, `round-4`, `frontend`, `react`, `hooks`, `per-file` |

### Verification Archive (_verification/) {#verification-archive}

> Complete listing of the `_verification/` directory. These files provide evidence trails for each analysis round.

#### _verification/layer-verification/ (12 files)

| File | Description |
|------|-------------|
| `layer-01-pages-hooks-verification.md` | R2: Frontend pages + hooks verification |
| `layer-01-components-verification.md` | R2: Frontend components verification |
| `layer-04-08-09-verification.md` | R2: Layer 4, 8, 9 routing + MCP + integrations verification |
| `layer-05-verification.md` | R2: Layer 5 hybrid orchestration verification |
| `layer-06-07-verification.md` | R2: Layer 6-7 MAF + Claude SDK verification |
| `layer-10-verification.md` | R2: Layer 10 domain verification |
| `layer-11-verification.md` | R2: Layer 11 infrastructure verification |
| `api-verification.md` | R2: API gateway verification report |
| `api-r3-verification.md` | R3: API layer AST verification report |
| `domain-r3-verification.md` | R3: Domain layer AST verification |
| `infra-r3-verification.md` | R3: Infrastructure layer AST verification |
| `frontend-r3-verification.md` | R3: Frontend regex scan verification |

#### _verification/ top-level wave verification files (29 files)

| File | Description |
|------|-------------|
| `verification-report.md` | 50-point verification across two V9 analysis files |
| `verification-L04-L05.md` | Layer 4-5 verification results |
| `verification-L04-L05-signatures.md` | Layer 4-5 function signature verification |
| `v9-wave4-L06-L07-verification.md` | Wave 4: Layer 6-7 deep verification |
| `deep-verification-L01-L02-L03.md` | Deep verification of Layers 1-3 |
| `wave3-L08-L09-verification.md` | Wave 3: Layer 8-9 verification |
| `wave6-L10-L11-verification.md` | Wave 6: Layer 10-11 verification |
| `wave6-verification-cat-f-to-j.md` | Wave 6: Features categories F-J verification |
| `wave6-verification-report.md` | Wave 6: consolidated verification report |
| `wave14-re-verification-results.md` | Wave 14: re-verification of flows |
| `wave-14-15-28-re-verification-report.md` | Wave 14/15/28 re-verification report |
| `wave26-verification-cat-a-to-e.md` | Wave 26: Features categories A-E verification |
| `wave32-stats-cross-file-alignment.md` | Wave 32: Stats + cross-file alignment check |
| `wave50-final-cross-file-alignment.md` | Wave 50: Final cross-file alignment verification |
| `wave-re-verify-flows-01-to-08.md` | Re-verification of all 8 E2E flows |
| `mod-integration-batch1-verification.md` | Module integration batch 1 verification |
| `mod-integration-batch2-verification.md` | Module integration batch 2 verification |
| `mod-domain-infra-core-verification.md` | Domain/Infra/Core module verification |
| `mod-frontend-verification.md` | Frontend module verification |
| `testing-landscape-verification.md` | Testing landscape verification |
| `mock-real-map-verification.md` | Mock/real map verification |
| `issue-registry-verification-report.md` | Issue registry verification |
| `delta-verification-report.md` | Delta analysis verification |
| `delta-phase-35-38-verification-report.md` | Delta Phase 35-38 verification |
| `api-reference-verification-front-half.md` | API reference verification (front half) |
| `api-reference-verification-back-half.md` | API reference verification (back half) |
| `enum-registry-verification-report.md` | Enum registry verification |
| `flows-01-to-05-verification-report.md` | Flows 1-5 verification |
| `flows-06-to-08-verification-results.md` | Flows 6-8 verification |

---

## 3. Category Index

| # | Category | Files | Total Size | Primary Purpose |
|---|----------|-------|------------|-----------------|
| 01 | Architecture | 11 | 455 KB | 11-layer deep-dive (frontend through infrastructure) |
| 02 | Modules | 4 | 148 KB | Per-module analysis (integrations, domain, frontend) |
| 03 | Features | 2 | 61 KB | 70+ feature verification across 10 categories |
| 04 | Flows | 2 | 66 KB | 8 end-to-end user journey validations |
| 05 | Issues | 1 | 54 KB | Consolidated issue registry with severity and status |
| 06 | Cross-Cutting | 5 | ~80 KB | Security, dependencies, enums, memory, error handling, logging |
| 07 | Delta | 3 | 46 KB | Phase 35-44 incremental changes (V8 was Phase 1-34) |
| 08 | Data Model | 1 | 45 KB | SQLAlchemy models, relationships, schema |
| 09 | API Reference | 1 | 79 KB | Complete REST API endpoint catalog |
| 10 | Event Contracts | 1 | 27 KB | SSE/WebSocket/AG-UI event specifications |
| 11 | Config & Deploy | 1 | 39 KB | Environment, Docker, settings, ports |
| 12 | Testing | 1 | 38 KB | Test inventory, coverage, gaps |
| 13 | Mock/Real Map | 1 | 28 KB | Implementation maturity per component |
| — | Root Files | 2 | ~10 KB | Stats, index (+ r5-imports.json) |
| — | _verification/ | 60+ | ~2 MB | Plans (6), reports (10), R4-semantic (5), layer verifications (11), wave verifications (20+), r5-data (10+) |

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
| What is the security architecture? | `06-cross-cutting/security-architecture.md` |
| What are the module dependencies? | `06-cross-cutting/dependency-analysis.md` |
| What enums/constants exist? | `06-cross-cutting/enum-registry.md` |
| How does memory/session work? | `06-cross-cutting/memory-architecture.md` |
| How is config/deployment set up? | `11-config-deploy/config-deploy.md` |
| How does the frontend work? | `01-architecture/layer-01-frontend.md` + `02-modules/mod-frontend.md` |
| How does the API gateway work? | `01-architecture/layer-02-api-gateway.md` |
| How does AG-UI protocol work? | `01-architecture/layer-03-ag-ui.md` |
| What integration modules exist? | `02-modules/mod-integration-batch1.md` + `mod-integration-batch2.md` |
| What domain/infra modules exist? | `02-modules/mod-domain-infra-core.md` |
| What are the E2E user journeys? | `04-flows/flows-01-to-05.md` + `flows-06-to-08.md` |
| What is the codebase size? | `00-stats.md` |
| What was the V9 analysis plan? | `_verification/plans/ANALYSIS-PLAN-V9.md` |
| What does a specific file do? | `_verification/R4-semantic/` — search the 5 semantic summary files for per-file summaries |
| What are the Round 4 corrections? | `_verification/reports/00-r4-final-report.md` |
| What are the Round 3 AST results? | `_verification/reports/00-r3-final-report.md` |
| What are the Round 2 verification results? | `_verification/reports/00-verification-report.md` |
| What metadata exists for backend files? | `_verification/r5-data/enhanced-backend-metadata.json` |
| How many TODOs/configs/errors exist? | `_verification/r5-data/enhanced-backend-metadata.json` summary section |

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
| **Cross-Cutting** | Partially in architecture doc | 5 dedicated files: analysis + security + dependencies + enums + memory (~80 KB) |
| **Machine Readability** | Narrative format | Structured tables, tags, quick lookup |
| **Semantic Coverage** | Manual reading of ~100 key files | 100% per-file semantic summaries (R4) |
| **Metadata Extraction** | None | Enhanced AST metadata for all 793 .py files |
| **Analysis Rounds** | 1 (snapshot) | 9 rounds (structural → verification → AST → semantic → programmatic → validation x3 → semantic verification) |
| **Total V9 Output** | — | 36 analysis + 60+ verification files, ~8+ MB |

### V9 New Categories (Not in V8)
- **07-delta**: Phase-by-phase incremental changes (V8 was a single snapshot)
- **08-data-model**: SQLAlchemy model and schema analysis
- **09-api-reference**: Complete REST endpoint catalog
- **10-event-contracts**: Event/message specifications
- **11-config-deploy**: Configuration and deployment analysis
- **12-testing**: Test landscape and coverage analysis
- **13-mock-real**: Mock vs real implementation maturity
- **R4-semantic** (in `_verification/`): Per-file semantic summaries for all 832+ source files (Round 4)
- **06-cross-cutting** expanded: security architecture, dependency analysis, enum registry, memory architecture (4 new files)
- **_verification/**: 60+ files across plans (6), reports (10), R4-semantic (5), layer verifications (12), wave verifications (29), r5-data (10+)

---

### V9 Round History

| Round | Date | Method | Coverage | Key Output |
|-------|------|--------|----------|------------|
| R1 | 2026-03-29 | Structural estimates from file inventory | 14% (121/832 files) | 32 analysis docs, ~1.1 MB |
| R2 | 2026-03-29 | Agent-driven source reading + verification | 54% (~450/832 files) | 12 verification reports |
| R3 | 2026-03-29 | Programmatic AST + regex scan | 100% structural (1,029 files) | 2 metadata JSONs, 1 final report |
| R4 | 2026-03-29 | Full semantic reading + enhanced AST + V9 sync | **100% semantic** (1,029 files) | 5 semantic files, enhanced metadata, 10 new issues |
| R5 | 2026-03-30 | Programmatic re-scan + comparison | 100% | r5-data JSON artifacts, comparison report |
| R6 | 2026-03-30 | Cross-file validation | 100% | Validation report (md + json) |
| R7 | 2026-03-30 | Enhanced 7-dimension validation | 100% | 2 validation reports |
| R8 | 2026-03-30 | Per-layer coverage + gap analysis | 100% | Gap report, coverage report |
| R9 | 2026-03-31 | Deep semantic verification (50-pt waves) | 100% | 29 wave verification reports |

---

*End of V9 Master Index*
