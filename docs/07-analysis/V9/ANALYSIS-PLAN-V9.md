# V9 Codebase Analysis Plan

> **Target Audience**: AI assistants and developers (NOT management)
> **Optimized for**: Machine-readability, searchability, precise file-path references, structured data
> **Scope**: Phase 1-44, all 793 Python + 236 TypeScript files, 140K+ LOC
> **Base date**: 2026-03-29
> **Predecessor**: V8 (2026-03-15, covered Phase 1-34 only)

---

## 1. V8 Coverage Gap Analysis

### What V8 Covered
- Phase 1-34 (Sprint 1-133)
- 11-layer architecture snapshot at Phase 34
- 70 planned + 15 unplanned features
- 62 issues (8 CRITICAL, 16 HIGH, 22 MEDIUM, 16 LOW)
- 5 E2E flow validations

### What V8 Missed (V9 Must Cover)

| Gap | Impact | Phase |
|-----|--------|-------|
| E2E Assembly: Core Hypothesis Validation | Orchestrator Agent prototype, zero-mock verification | 35 |
| E2E Assembly: Foundation Assembly | Login → Orchestrator → Q&A → Approval trigger | 36 |
| E2E Assembly: Task Execution | Sub-agent dispatch, MCP tool execution, result aggregation | 37 |
| E2E Assembly: Memory & Knowledge | Cross-conversation memory, knowledge retrieval | 38 |
| E2E Assembly: Pipeline Assembly | Complete 10-step pipeline, async dispatch | 39 |
| Frontend Enhancement: E2E Workflow UI | UI pages for E2E, operational support | 40 |
| Chat Pipeline Integration | 10-step pipeline in chat, real-time visualization | 41 |
| E2E Pipeline Deep Integration | SSE streaming, async task dispatch, Swarm UI | 42 |
| Agent Swarm Complete Implementation | True multi-agent parallel, complex task decomposition | 43 |
| Magentic Orchestrator Agent | Multi-model dynamic selection, Manager upgrade | 44 |
| Pipeline SSE Events (14 types) | Not analyzed in V8 | 39-42 |
| Mock separation (Sprint 112) | mock.py moved from src/ to tests/ | 35+ |
| ManagerModelRegistry | Multi-model orchestration | 44 |

---

## 2. V9 Document Classification (13 Categories)

### Original 7 Categories (Revised)

| # | Category | Directory | Purpose | Est. Files |
|---|----------|-----------|---------|------------|
| 01 | Architecture Layers | `01-architecture/` | Per-layer deep analysis (11 layers) | 11 |
| 02 | Module Deep-Dive | `02-modules/` | Per-module analysis (all integration + domain) | ~30 |
| 03 | Feature Verification | `03-features/` | Per-category feature status (9 categories + unplanned) | 10 |
| 04 | E2E Flow Validation | `04-flows/` | End-to-end user journey tracing | 6+ |
| 05 | Issue Registry | `05-issues/` | Known problems, tech debt, risks | 3 |
| 06 | Cross-Cutting Concerns | `06-cross-cutting/` | Security, performance, data flow, dependencies | 4 |
| 07 | Phase Delta Tracking | `07-delta/` | V8→V9 changes by phase group | 3 |

### NEW Categories (問題 6 回答)

| # | Category | Directory | Purpose | Rationale |
|---|----------|-----------|---------|-----------|
| 08 | Data Model & Schema | `08-data-model/` | DB models, Pydantic schemas, TS types, store definitions | 8 DB models + 690 Pydantic classes + 1000+ TS types = massive data layer that V8 only mentioned in passing |
| 09 | API Endpoint Reference | `09-api-reference/` | Complete 560+ endpoint inventory with request/response | V8 only counted endpoints; developers need per-endpoint detail for integration |
| 10 | Event & Contract Map | `10-event-contracts/` | All 40+ SSE/AG-UI/Swarm/webhook event definitions | Pipeline SSE (14), AG-UI (11), Swarm (9), Routing contracts — the messaging backbone |
| 11 | Configuration & Deployment | `11-config-deploy/` | 170+ env vars, Docker, CI/CD, dependency versions | Without this, can't reproduce or deploy the system |
| 12 | Testing Landscape | `12-testing/` | 443 backend + 11 frontend tests, coverage gaps, strategy | 80% coverage target but frontend only has 2 unit tests — critical blind spot |
| 13 | Mock vs Real Map | `13-mock-real/` | Which components are mock/InMemory vs production-ready | Most critical for deployment decisions — V8 mentioned it but never systematically mapped |

### Index & Navigation

| File | Purpose |
|------|---------|
| `00-index.md` | Machine-readable master index with file paths, tags, search keywords |
| `00-stats.md` | Quantitative summary: file counts, LOC, coverage numbers |

---

## 3. Detailed File Specifications

### 3.1 Category 01: Architecture Layers (`01-architecture/`)

Each file follows this template:
```yaml
# Layer N: [Name]
## Identity
- Files: [count] | LOC: [count] | Directory: [path]
- Phase introduced: [N] | Last modified: Phase [N]

## File Inventory
| File | LOC | Purpose | Key Classes/Functions |
# (every .py/.tsx file listed)

## Internal Architecture
# Component diagram, data flow within layer

## Interfaces
# What this layer exposes (APIs, classes, events)
# What this layer consumes (from other layers)

## Known Issues
# Issues from V8 registry + new findings

## Phase Evolution
# How this layer changed across phases
```

**Files to produce:**

| File | Scope | Key Files to Read |
|------|-------|-------------------|
| `layer-01-frontend.md` | 236 TS/TSX files, 49K LOC | `frontend/src/` entire tree |
| `layer-02-api-gateway.md` | 107 route files, 46K LOC | `backend/src/api/v1/` entire tree |
| `layer-03-ag-ui.md` | 22 files, ~10K LOC | `backend/src/integrations/ag_ui/` |
| `layer-04-routing.md` | ~40 files, ~16K LOC | `backend/src/integrations/orchestration/` |
| `layer-05-orchestration.md` | 75 files, ~24K LOC | `backend/src/integrations/hybrid/` |
| `layer-06-maf-builders.md` | 62 files, ~38K LOC | `backend/src/integrations/agent_framework/` |
| `layer-07-claude-sdk.md` | 39 files, ~15K LOC | `backend/src/integrations/claude_sdk/` |
| `layer-08-mcp-tools.md` | 43 files, ~21K LOC | `backend/src/integrations/mcp/` |
| `layer-09-integrations.md` | ~50 files, ~18K LOC | `backend/src/integrations/{swarm,patrol,correlation,...}` |
| `layer-10-domain.md` | 86 files, ~47K LOC | `backend/src/domain/` |
| `layer-11-infrastructure.md` | 42 files, ~6K LOC | `backend/src/infrastructure/` + `backend/src/core/` |

**Analysis Strategy:**
1. Glob all files in the layer directory
2. Read every file (or use AST scan for large files)
3. Extract: class names, function signatures, imports, LOC
4. Map internal dependencies (which files import which)
5. Identify interfaces exposed to other layers
6. Cross-reference with V8 issue registry
7. Note any Phase 35-44 additions

---

### 3.2 Category 02: Module Deep-Dive (`02-modules/`)

Each file follows this template:
```yaml
# Module: [name]
## Identity
- Path: backend/src/integrations/[name]/
- Files: [count] | LOC: [count]
- Phase introduced: [N] | Phase last modified: [N]

## File Inventory (complete)
| File | LOC | Purpose |

## Public API
# Exported classes, functions, constants

## Dependencies
# What this module imports from other modules

## Dependents
# What other modules import from this module

## Configuration
# Required env vars, settings

## Known Issues

## Test Coverage
# Which test files cover this module
```

**Complete Module List (must cover ALL):**

**Integration Modules (19):**

| File | Module | Files | Est. LOC |
|------|--------|-------|----------|
| `mod-integration-hybrid.md` | hybrid/ | 75 | ~24K |
| `mod-integration-agent-framework.md` | agent_framework/ | 62 | ~38K |
| `mod-integration-orchestration.md` | orchestration/ | 39 | ~16K |
| `mod-integration-claude-sdk.md` | claude_sdk/ | 39 | ~15K |
| `mod-integration-mcp.md` | mcp/ | 43 | ~21K |
| `mod-integration-ag-ui.md` | ag_ui/ | 22 | ~10K |
| `mod-integration-swarm.md` | swarm/ | 8 | ~2.7K |
| `mod-integration-patrol.md` | patrol/ | 9 | ~3K |
| `mod-integration-knowledge.md` | knowledge/ | 7 | ~2K |
| `mod-integration-correlation.md` | correlation/ | 5 | ~1.5K |
| `mod-integration-incident.md` | incident/ | 5 | ~1.5K |
| `mod-integration-llm.md` | llm/ | 5 | ~1.5K |
| `mod-integration-memory.md` | memory/ | 4 | ~1.2K |
| `mod-integration-learning.md` | learning/ | 4 | ~1.2K |
| `mod-integration-rootcause.md` | rootcause/ | 4 | ~1.2K |
| `mod-integration-audit.md` | audit/ | 3 | ~1K |
| `mod-integration-a2a.md` | a2a/ | 3 | ~1K |
| `mod-integration-n8n.md` | n8n/ | 2 | ~600 |
| `mod-integration-contracts.md` | contracts/ + shared/ | 2 | ~500 |

**Domain Modules (21):**

| File | Module | Files |
|------|--------|-------|
| `mod-domain-sessions.md` | sessions/ | 26 |
| `mod-domain-orchestration.md` | orchestration/ | 17 |
| `mod-domain-workflows.md` | workflows/ | 5 |
| `mod-domain-agents.md` | agents/ | 5 |
| `mod-domain-connectors.md` | connectors/ | 5 |
| `mod-domain-remaining.md` | auth, audit, chat_history, checkpoints, devtools, executions, files, learning, notifications, prompts, routing, sandbox, tasks, templates, triggers, versioning | 16 (each 1-2 files) |

**Infrastructure + Core:**

| File | Module | Files |
|------|--------|-------|
| `mod-infra-database.md` | database/ | 15 |
| `mod-infra-storage.md` | storage/ | 16 |
| `mod-infra-checkpoint.md` | checkpoint/ | 6 |
| `mod-infra-remaining.md` | cache, distributed_lock, workers, redis_client | 4 |
| `mod-core-security.md` | core/security/ | 6 |
| `mod-core-performance.md` | core/performance/ | 10 |
| `mod-core-sandbox.md` | core/sandbox/ | 6 |
| `mod-core-remaining.md` | core/ root (config, auth, factories, logging, observability) | 11 |

**Frontend Modules:**

| File | Module | Files |
|------|--------|-------|
| `mod-fe-unified-chat.md` | components/unified-chat/ | 25+ |
| `mod-fe-agent-swarm.md` | components/unified-chat/agent-swarm/ | 8+ |
| `mod-fe-ag-ui.md` | components/ag-ui/ | 20+ |
| `mod-fe-devui.md` | components/DevUI/ + pages/DevUI/ | 20+ |
| `mod-fe-workflow-editor.md` | components/workflow-editor/ | 13 |
| `mod-fe-pages.md` | pages/ (all page components) | 35+ |
| `mod-fe-hooks.md` | hooks/ | 25 |
| `mod-fe-api-stores.md` | api/ + stores/ + store/ + types/ | 23 |

**Total: ~38 module analysis files**

**Analysis Strategy:**
1. For each module: glob all files, read each file
2. Extract all class/function definitions
3. Trace import chains to identify dependencies
4. Cross-reference with test files in `backend/tests/`
5. Check for InMemory/Mock patterns
6. Verify against V8 feature mapping

---

### 3.3 Category 03: Feature Verification (`03-features/`)

Each file follows this template:
```yaml
# Category [X]: [Name] ([N] features)

## Feature List
| ID | Feature | Status | Evidence (file:line) | Phase | Layer |

## Per-Feature Detail
### [ID] [Feature Name]
- Status: COMPLETE / PARTIAL / MOCK / STUB
- Implementation files: [list with line numbers]
- Test files: [list]
- API endpoints: [list]
- Frontend components: [list]
- Dependencies: [list]
- Known issues: [list]
- Phase history: introduced Phase [N], modified Phase [N]
```

**Files to produce:**

| File | Category | Features | V8 Status |
|------|----------|----------|-----------|
| `cat-a-agent-orchestration.md` | A: Agent Orchestration | 16 | 100% (V8) — verify still true |
| `cat-b-hitl.md` | B: Human-in-Loop | 7 | 100% (V8) — verify 3 approval systems |
| `cat-c-state-memory.md` | C: State & Memory | 5 | 100% (V8) — verify InMemory status |
| `cat-d-frontend-ui.md` | D: Frontend UI | 11 | 100% (V8) — verify Phase 40-42 additions |
| `cat-e-connectors.md` | E: Connectors & Integration | 8 | 87.5% (V8) — check if gap filled |
| `cat-f-intelligent-decision.md` | F: Intelligent Decision | 7 | 85.7% (V8) — check improvements |
| `cat-g-observability.md` | G: Observability | 5 | 40% (V8) — check Sprint 130+ fixes |
| `cat-h-swarm.md` | H: Agent Swarm | 4 | 100% (V8) — verify Phase 43 true implementation |
| `cat-i-security.md` | I: Security | 4 | 100% (V8) — re-verify |
| `cat-j-unplanned.md` | J: Unplanned + Phase 35-44 new features | 15+ TBD | NOT in V8 — full discovery needed |

**Analysis Strategy:**
1. Start from V8 feature list as baseline
2. For each feature: verify the implementation files still exist and haven't regressed
3. Check if Phase 35-44 added new features not in V8's 70+15 list
4. Trace each feature end-to-end: API → Service → Integration → Frontend
5. Classify status precisely: COMPLETE (production-ready), PARTIAL (works but limited), MOCK (uses simulated data), STUB (interface only)

---

### 3.4 Category 04: E2E Flow Validation (`04-flows/`)

Each file follows this template:
```yaml
# Flow: [Name]

## Flow Diagram
# Step-by-step with file:line references

## Step Detail
### Step N: [Description]
- Entry point: [file:line]
- Key function: [name]
- Input: [type]
- Output: [type]
- Next step trigger: [mechanism]
- Potential failures: [list]

## Mock vs Real
# Which steps use real vs mock implementations

## Test Coverage
# Which tests exercise this flow

## Known Breaks
# Where the flow is fragile or broken
```

**Files to produce:**

| File | Flow | Steps | V8 Status |
|------|------|-------|-----------|
| `flow-01-chat-message.md` | User chat → routing → execution → response | 17+ | MOSTLY CONNECTED (V8) |
| `flow-02-agent-crud.md` | Agent CRUD via API + DB | 6 | FULLY CONNECTED (V8) |
| `flow-03-workflow-execute.md` | Workflow DAG execution | 8 | MOSTLY CONNECTED (V8) |
| `flow-04-hitl-approval.md` | Risk detection → approval → continue | 12 | FRAGILE (V8) |
| `flow-05-swarm.md` | Multi-agent swarm coordination | 8 | PARTIALLY (V8) |
| `flow-06-pipeline-e2e.md` | **NEW** 10-step pipeline (Phase 39-42) | 10 | NOT IN V8 |
| `flow-07-task-dispatch.md` | **NEW** Async task dispatch + background execution | TBD | NOT IN V8 |
| `flow-08-memory-knowledge.md` | **NEW** Cross-conversation memory + knowledge retrieval | TBD | NOT IN V8 |

**Analysis Strategy:**
1. Start from V8's 5 flows as baseline
2. Add Phase 35-44 new flows (pipeline, task dispatch, memory)
3. For each flow: trace the actual code path step-by-step
4. At each step: record the exact file:line, function name, input/output
5. Flag mock/InMemory barriers in the flow
6. Cross-reference with integration tests

---

### 3.5 Category 05: Issue Registry (`05-issues/`)

| File | Scope |
|------|-------|
| `issue-registry.md` | Complete issue list (V8's 62 + new findings) |
| `critical-high-detail.md` | CRITICAL + HIGH issues with root cause analysis and fix suggestions |
| `tech-debt-tracker.md` | Technical debt items, InMemory → Persistent migration status |

**Analysis Strategy:**
1. Start from V8's 62 issues
2. For each: verify if still exists (some may have been fixed in Phase 35-44)
3. Add new issues discovered during V9 analysis
4. Classify: FIXED / STILL_OPEN / WORSENED / NEW
5. For CRITICAL/HIGH: provide root cause + suggested fix with file:line references

---

### 3.6 Category 06: Cross-Cutting Concerns (`06-cross-cutting/`)

| File | Scope | Strategy |
|------|-------|----------|
| `security-analysis.md` | Auth, RBAC, injection, MCP permissions | Grep for security patterns: SQL f-strings, JWT validation, CORS, rate limiting |
| `performance-analysis.md` | Async patterns, connection pools, caching, N+1 | Grep for: `await`, `async def`, connection pool configs, cache TTLs |
| `data-flow-map.md` | How data flows from input to storage to output | Trace key data types through all layers |
| `dependency-graph.md` | Module interdependencies, circular imports | Analyze import statements across all modules |

---

### 3.7 Category 07: Phase Delta Tracking (`07-delta/`)

| File | Scope |
|------|-------|
| `delta-phase-35-38.md` | E2E Assembly A-C: hypothesis validation, foundation, task execution, memory |
| `delta-phase-39-42.md` | Pipeline assembly, frontend enhancement, chat pipeline, deep integration |
| `delta-phase-43-44.md` | True swarm implementation, Magentic orchestrator, multi-model selection |

**Analysis Strategy:**
1. Read sprint plan + checklist files for each phase
2. Git diff between phase branches (if available)
3. Identify new files, modified files, deleted files
4. Map changes to architecture layers and modules

---

### 3.8 Category 08: Data Model & Schema (`08-data-model/`)

| File | Scope | Content |
|------|-------|---------|
| `db-models.md` | 8 SQLAlchemy models | Table schemas, relationships, indexes, JSONB columns |
| `pydantic-schemas.md` | 38 schema files, ~690 classes | Per-endpoint request/response models with field types |
| `typescript-types.md` | 4 type files, 1000+ types | Frontend type definitions, store state shapes |
| `data-flow-contracts.md` | Backend ↔ Frontend type mapping | Pydantic → JSON → TypeScript type alignment verification |

**Analysis Strategy:**
1. Read every model file, extract: table name, columns, types, relationships, constraints
2. Read every schema file, extract: class name, fields, validators, nested models
3. Read every TypeScript type file, extract: interface/type name, fields
4. Cross-reference: DB model ↔ Pydantic schema ↔ TS type for consistency

---

### 3.9 Category 09: API Endpoint Reference (`09-api-reference/`)

| File | Scope | Est. Endpoints |
|------|-------|----------------|
| `api-agents-workflows.md` | agents, workflows, executions, sessions | ~80 |
| `api-orchestration.md` | orchestration, orchestrator, routing, hybrid | ~60 |
| `api-ai-features.md` | claude_sdk, autonomous, code_interpreter, mcp | ~70 |
| `api-collaboration.md` | ag_ui, swarm, handoff, groupchat, concurrent, nested | ~80 |
| `api-management.md` | auth, audit, versioning, templates, prompts, files, tasks | ~100 |
| `api-monitoring.md` | dashboard, performance, patrol, correlation, rootcause, devtools | ~60 |
| `api-connectors.md` | connectors, n8n, a2a, knowledge, learning, memory | ~60 |
| `api-system.md` | checkpoints, cache, triggers, notifications, sandbox, planning | ~50 |

Per-endpoint detail:
```yaml
### [METHOD] /api/v1/[path]
- Router file: [file:line]
- Handler function: [name]
- Request schema: [Pydantic class name]
- Response schema: [Pydantic class name]
- Auth required: [yes/no]
- Dependencies: [service classes]
```

**Analysis Strategy:**
1. Read every router file in `backend/src/api/v1/`
2. Extract: HTTP method, path, function name, request/response schemas
3. Group by functional domain
4. Note which endpoints are protected (require auth)
5. Cross-reference with frontend API client calls

---

### 3.10 Category 10: Event & Contract Map (`10-event-contracts/`)

| File | Scope | Event Types |
|------|-------|-------------|
| `pipeline-sse-events.md` | Pipeline SSE (Phase 39-42) | 14 types |
| `ag-ui-protocol-events.md` | AG-UI Protocol (Phase 15+) | 11 types |
| `swarm-events.md` | Swarm coordination (Phase 29, 43) | 9 types |
| `routing-contracts.md` | Orchestration routing (Phase 28) | InputSource, RoutingRequest, RoutingResult |
| `webhook-schemas.md` | ServiceNow, Prometheus inbound | Webhook payload formats |
| `event-bridge-map.md` | Pipeline↔AG-UI↔Frontend event mapping | Cross-system event translation |

**Analysis Strategy:**
1. Read every event definition file
2. Extract: event name, payload schema (all fields with types), Enum values
3. Map producer → consumer for each event type
4. Verify frontend event handlers match backend event definitions
5. Identify any unhandled events or missing handlers

---

### 3.11 Category 11: Configuration & Deployment (`11-config-deploy/`)

| File | Scope |
|------|-------|
| `env-vars-reference.md` | All 170+ environment variables with defaults, required/optional, description |
| `docker-architecture.md` | Docker Compose services, multi-stage builds, networking |
| `dependency-versions.md` | Python packages (requirements.txt) + npm packages (package.json) with version constraints |
| `cicd-pipeline.md` | GitHub Actions workflow, test stages, deployment process |

**Analysis Strategy:**
1. Read `config.py`, `.env.example`, `backend/.env.example`
2. Read Docker files, CI/CD yaml
3. Read requirements.txt, package.json
4. Extract every variable, service, dependency with exact version

---

### 3.12 Category 12: Testing Landscape (`12-testing/`)

| File | Scope |
|------|-------|
| `test-inventory.md` | Complete list of 443 backend + 11 frontend test files |
| `coverage-gap-analysis.md` | Which modules/features lack tests |
| `test-infrastructure.md` | Fixtures (conftest.py), mocks, test configuration |

**Analysis Strategy:**
1. Glob all test files
2. Map test file → source module coverage
3. Identify modules with 0 test files
4. Check coverage config and actual coverage numbers
5. Note: frontend has only 2 unit tests for 200+ components — major gap

---

### 3.13 Category 13: Mock vs Real Map (`13-mock-real/`)

| File | Scope |
|------|-------|
| `mock-real-matrix.md` | Per-module status: REAL / MOCK / InMemory / FALLBACK |
| `inmemory-risk-map.md` | All InMemory storage locations + restart-loss impact |
| `fallback-patterns.md` | Code patterns that silently degrade to mock data |

**Analysis Strategy:**
1. Grep for `Mock`, `InMemory`, `mock_`, `MOCK_`, `fallback`, `simulated`
2. For each finding: classify as intentional test mock vs production fallback
3. Map against deployment scenarios: what breaks without API keys?
4. Identify the "silent degradation" paths (H-08 from V8: frontend pages using mock without user knowing)

---

## 4. Execution Strategy

### Phase A: Inventory & Index (Automated)
**Goal**: Generate complete file inventories for every module
**Method**: Glob + AST scan + line counting
**Output**: Raw file lists that feed into each analysis document
**Parallelizable**: Yes — all modules can be scanned simultaneously

### Phase B: Layer Analysis (11 parallel agents)
**Goal**: Produce `01-architecture/layer-*.md` files
**Method**: Read all files in each layer, extract architecture
**Dependencies**: Phase A file inventories
**Parallelizable**: Yes — each layer is independent

### Phase C: Module Deep-Dive (batched parallel)
**Goal**: Produce `02-modules/mod-*.md` files
**Method**: Deep read of every file in each module
**Dependencies**: Phase B layer context
**Parallelizable**: Yes in batches (5-8 modules per batch)

### Phase D: Feature Verification (sequential per category)
**Goal**: Produce `03-features/cat-*.md` files
**Method**: Cross-reference Phase B+C findings against feature list
**Dependencies**: Phase B + C results
**Parallelizable**: Partially — categories are independent but each needs B+C data

### Phase E: Flow Validation (sequential)
**Goal**: Produce `04-flows/flow-*.md` files
**Method**: Trace code paths end-to-end using Phase C module knowledge
**Dependencies**: Phase C module details
**Parallelizable**: Each flow is independent

### Phase F: Specialized Analysis (parallel)
**Goal**: Produce categories 05-13
**Method**: Targeted searches and cross-referencing
**Dependencies**: Phase B-E for context
**Parallelizable**: Yes — categories 08-13 are independent

### Phase G: Index & Validation
**Goal**: Produce `00-index.md`, `00-stats.md`, cross-validate
**Method**: Aggregate all findings, check for gaps
**Dependencies**: All previous phases

### Execution Order
```
Phase A (inventory) ──→ Phase B (layers, 11 parallel)
                    ──→ Phase C (modules, batched parallel)
                          ──→ Phase D (features)
                          ──→ Phase E (flows)
                          ──→ Phase F (specialized, parallel)
                                ──→ Phase G (index + validation)
```

### Estimated Output
- **Total analysis files**: ~85-90 files
- **Each file**: 10-40KB (machine-readable, not bloated)
- **Total analysis volume**: ~2-3 MB
- **Coverage**: 100% of source files referenced at least once

---

## 5. Quality Gates

### Per-Document Quality Checks
- [ ] Every source file in scope is referenced at least once
- [ ] Every class/function mentioned includes file:line reference
- [ ] No "probably" or "likely" — only verified facts
- [ ] Issue status verified against current code (not V8 assumptions)
- [ ] Mock/Real status verified via actual code reading
- [ ] Phase attribution verified (when was this introduced/modified)

### Cross-Document Validation
- [ ] Module dependency graph has no orphans
- [ ] Feature → Module → File mapping is complete
- [ ] Event producer → consumer mapping is complete
- [ ] API endpoint → Frontend consumer mapping is complete
- [ ] Test → Source mapping identifies all uncovered modules

---

## 6. File Naming Convention

```
# Architecture layers
01-architecture/layer-{NN}-{name}.md

# Modules
02-modules/mod-{scope}-{name}.md
  where scope = integration | domain | infra | core | fe

# Features
03-features/cat-{letter}-{name}.md

# Flows
04-flows/flow-{NN}-{name}.md

# Others
{NN}-{category}/{descriptive-name}.md
```

All file names: lowercase, hyphen-separated, no spaces.

---

## 7. Diff from V8 Approach

| Aspect | V8 | V9 |
|--------|----|----|
| Main files | 2 monolithic (169KB + 96KB) | ~90 focused files (10-40KB each) |
| Phase coverage | 1-34 | 1-44 |
| Module coverage | Summarized | Every module has own file |
| File references | Approximate counts | Exact file:line for every claim |
| Feature verification | Status labels | Status + evidence + test + API + frontend mapping |
| Event contracts | Mentioned in passing | Dedicated category with full schemas |
| Data models | Not analyzed | Dedicated category with all 690+ schemas |
| API endpoints | Counted (560) | Every endpoint documented |
| Mock/Real | Listed as issues | Dedicated category with per-module matrix |
| Testing | Not covered | Dedicated category with gap analysis |
| Config/Deploy | Not covered | Dedicated category with all 170+ vars |
| Target audience | Mixed (management + dev) | AI + developers only |
| Update strategy | Rewrite entire file | Update only affected module file |
