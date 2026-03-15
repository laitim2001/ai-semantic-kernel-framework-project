# Phase 4: Validated Issue Registry — Deduplicated & Classified

**Generated**: 2026-03-15
**Source**: 22 analysis agent reports (Phase 3A-3E)
**Methodology**: All issues extracted from "Issues Found", "Problems", "Key Findings", "Concerns", "Gaps", "Notable Issues" sections across all 22 reports, then deduplicated by root cause.

---

## Issue Statistics

| Metric | Count |
|--------|-------|
| **Raw issues extracted** | 147 |
| **After deduplication** | 62 |
| **CRITICAL** | 8 |
| **HIGH** | 16 |
| **MEDIUM** | 22 |
| **LOW** | 16 |

### By Layer

| Layer | Issues | Reports |
|-------|--------|---------|
| API Layer (3A) | 18 | phase3a-api-part1/2/3 |
| Domain Layer (3B) | 12 | phase3b-domain-part1/2/3 |
| Integration Layer (3C) | 19 | phase3c-* (10 reports) |
| Core/Infrastructure (3D) | 7 | phase3d-core-infra |
| Frontend (3E) | 16 | phase3e-frontend-part1/2/3/4 |

---

## 1. CRITICAL Issues (Blocks Production Use)

| ID | Issue | Affected Modules | Reported By (Agent Count) | Evidence |
|----|-------|-----------------|---------------------------|----------|
| **C-01** | **Pervasive in-memory-only storage — all state lost on restart** | API: ag_ui (ApprovalStorage, ChatSession, SharedState, PredictiveState), checkpoints, autonomous, correlation, patrol, rootcause (API routes), a2a, audit; Domain: learning, templates, routing, triggers, versioning, prompts; Integration: orchestration metrics | 3A-part1, 3A-part2, 3A-part3, 3B-part3, 3C-ag-ui, 3C-remaining (**6 agents**) | 9/13 API modules use in-memory dicts; 6/10 domain modules lack persistence; AG-UI has 4 separate in-memory stores |
| **C-02** | **API routes for correlation/ are 100% mock** — no connection to real `integrations/correlation` module despite Sprint 130 implementing real analyzers | api/v1/correlation/ | 3A-part1 (**1 agent**, confirmed by 3C-remaining) | All 7 endpoints generate fake data via `uuid4()` and hardcoded values. Real `CorrelationAnalyzer` exists in integrations but is not wired |
| **C-03** | **API routes for autonomous/ are 100% mock** — UAT stub with no real planning engine, no Claude SDK integration | api/v1/autonomous/ | 3A-part1 (**1 agent**) | `AutonomousTaskStore` generates fake steps from hardcoded templates `["analyze", "plan", "prepare", "execute", "cleanup"]`; module docstring says "Phase 22 Testing" |
| **C-04** | **API routes for rootcause/ are 100% mock** — hardcoded analysis results, despite real `RootCauseAnalyzer` existing in integrations | api/v1/rootcause/ | 3A-part3 (**1 agent**, confirmed by 3C-remaining) | All 4 endpoints return hardcoded templates; fake confidence scores (0.87, 0.65, 0.55); no AI integration; real analyzer exists in `integrations/rootcause/` |
| **C-05** | **API routes for patrol/ are mock** — simulated reports, no real execution, uses blocking `time.sleep()` in async handler | api/v1/patrol/ | 3A-part3 (**1 agent**, integration layer confirmed real checks exist) | `trigger_patrol` creates simulated report; `execute_check` uses `time.sleep(0.1)` blocking the event loop; real patrol checks exist in `integrations/patrol/` |
| **C-06** | **Messaging infrastructure is a complete stub** — RabbitMQ and Azure Service Bus config exists but no implementation | infrastructure/messaging/ | 3D-core-infra (**1 agent**) | `messaging/__init__.py` is literally 1 line: `# Messaging infrastructure`. Settings define RABBITMQ_HOST/PORT/USER/PASSWORD but nothing uses them |
| **C-07** | **SQL injection risk via f-string table name interpolation** in PostgreSQL storage backends | integrations/agent_framework/ (postgres memory store, postgres checkpoint store) | 3C-agent-framework-part2 (**1 agent**) | f-string interpolation of table names in raw SQL queries enables potential injection if table names are user-influenced |
| **C-08** | **API key prefix exposed in AG-UI bridge status/reset response** | api/v1/ag_ui/ | 3A-part1 (**1 agent**) | `/ag-ui/reset` endpoint includes Anthropic API key prefix in response payload |

---

## 2. HIGH Issues (Significant Risk)

| ID | Issue | Affected Modules | Reported By (Agent Count) | Evidence |
|----|-------|-----------------|---------------------------|----------|
| **H-01** | **No RBAC on destructive operations** — cache clear, connector execute, agent unregister accessible to any authenticated user | api/v1/cache, connectors, agents | 3A-part1, 3A-part2 (**2 agents**) | No role check on `POST /cache/clear`, connector execute, agent unregister endpoints |
| **H-02** | **Test endpoints exposed in production** — ag_ui `/test/*` routes not gated by environment | api/v1/ag_ui/ | 3A-part1 (**1 agent**) | Test endpoints accessible regardless of APP_ENV setting |
| **H-03** | **Global singleton anti-pattern** — module-level singletons make testing difficult and create hidden shared state | Pervasive: DeadlockDetector, MetricsCollector, SessionEventPublisher, cache services, approval storage, chat handler, HITL handler | 3A-part1, 3B-part3, 3C-ag-ui (**3 agents**) | `get_approval_storage()`, `get_hitl_handler()`, `_cache_service` global, module-level singleton instances across codebase |
| **H-04** | **ContextBridge._context_cache has NO locking** — race condition risk for concurrent async operations on same session | integrations/hybrid/context/bridge.py | 3C-hybrid-part1 (**1 agent**) | `_context_cache` is a plain `Dict[str, HybridContext]` with no asyncio.Lock or distributed lock protection |
| **H-05** | **Checkpoint storage uses non-official API** — 3 custom backends (Redis, Postgres, File) incompatible with official `save_checkpoint/load_checkpoint` | integrations/agent_framework/checkpoint/ | 3C-agent-framework-part2 (**1 agent**) | Custom `save/load/delete` API vs official MAF `save_checkpoint/load_checkpoint` interface |
| **H-06** | **MCP AuditLogger not wired into any server** — tool executions are not audited | integrations/mcp/ (all 8 servers) | 3C-mcp-part1 (**1 agent**) | `AuditLogger` class exists but `set_audit_logger()` never called; no tool call audit trail |
| **H-07** | **MCP default permission mode is `log` not `enforce`** — denials are logged but operations proceed | integrations/mcp/core/ | 3C-mcp-part1 (**1 agent**) | Default `MCP_PERMISSION_MODE=log` means unauthorized tool calls succeed with a log entry only |
| **H-08** | **Frontend: 10 pages silently fall back to mock data** — no visual indicator for users | Dashboard components, AgentsPage, WorkflowsPage, ApprovalsPage, AuditPage, TemplatesPage | 3E-frontend-part1 (**1 agent**) | Pages use try/catch with `generateMock*()` fallbacks; users cannot distinguish real vs mock data |
| **H-09** | **Sandbox is simulated** — no real process isolation, container usage, or enforcement | domain/sandbox/ | 3B-part3 (**1 agent**) | `creation_time_ms=150.0` hardcoded; no actual process isolation; pool counters are simplistic increment/decrement |
| **H-10** | **Deprecated domain/orchestration/ still actively imported** — maintenance burden and confusion | domain/orchestration/ (4 sub-modules: multiturn, memory, planning, nested) | 3B-part2 (**1 agent**) | All sub-modules emit DeprecationWarning but are still imported by API routes; new implementations exist in integrations/agent_framework/ |
| **H-11** | **Chat threads stored in localStorage only** — not synced to backend, lost on browser clear | frontend: UnifiedChat.tsx via useChatThreads | 3E-frontend-part1 (**1 agent**) | All chat history persisted only in browser localStorage; no backend persistence API |
| **H-12** | **D365 OData filter injection risk** — filter strings passed to OData queries without content validation | integrations/mcp/servers/d365/ | 3C-mcp-part2 (**1 agent**) | Entity name has regex validation but filter string parameters may be vulnerable to OData injection |
| **H-13** | **Azure `run_command` MCP tool lacks command content validation** — executes arbitrary commands on VMs at permission Level 3 | integrations/mcp/servers/azure/ | 3C-mcp-part2 (**1 agent**) | Even at Level 3 (ADMIN), no guardrails on command content; could execute destructive commands |
| **H-14** | **Rate limiter uses in-memory storage** — each worker has independent limits in multi-worker deployments | core/main.py (slowapi) | 3D-core-infra (**1 agent**) | `storage_uri=None` means in-memory; Sprint 119 planned Redis upgrade not implemented |
| **H-15** | **No React Error Boundary wrapping individual pages** — unhandled errors crash entire app | frontend: All pages, OrchestrationPanel, WorkerDetailDrawer, FileRenderer, CustomUIRenderer | 3E-frontend-part1, 3E-frontend-part2 (**2 agents**) | ErrorBoundary only wraps ChatArea; complex components with external data have no error isolation |
| **H-16** | **Raw SQL in domain/orchestration/postgres_store.py** — violates project ORM-only standard | domain/orchestration/ | 3B-part2 (**1 agent**) | Raw SQL queries instead of SQLAlchemy ORM; potential injection risk and maintenance burden |

---

## 3. MEDIUM Issues (Should Fix)

| ID | Issue | Affected Modules | Reported By (Agent Count) | Evidence |
|----|-------|-----------------|---------------------------|----------|
| **M-01** | **`datetime.utcnow()` deprecated in Python 3.12+** — used across multiple modules | dashboard, learning/service.py, notifications/teams.py, routing/scenario_router.py, sessions/models.py, core infra | 3A-part2, 3B-part3, 3D-core-infra (**3 agents**) | Should use `datetime.now(timezone.utc)` per Python 3.12 deprecation |
| **M-02** | **Health check uses `os.environ` directly** instead of `get_settings()` | main.py (line 257-258) | 3D-core-infra (**1 agent**) | Reads `REDIS_HOST`/`REDIS_PORT` via `os.environ.get()`, violating project pydantic Settings rule |
| **M-03** | **N+1 query pattern in dashboard chart endpoint** | api/v1/dashboard/ | 3A-part2 (**1 agent**) | 3 separate queries per day in a loop (7 days = 21 queries); should use single aggregated query |
| **M-04** | **Dashboard stats endpoint silently swallows exceptions** — returns empty data on any error | api/v1/dashboard/ | 3A-part2 (**1 agent**) | Broad try/except returns empty stats instead of error response; masks DB connection issues |
| **M-05** | **ServiceNow MCP server does not call `set_permission_checker()`** — permissions not checked | integrations/mcp/servers/servicenow/ | 3C-mcp-part1 (**1 agent**) | Only server that skips permission setup; all other servers properly configure permission checking |
| **M-06** | **Edge routing builder bypasses official MAF Edge API** — custom implementations instead of official imports | integrations/agent_framework/builders/edge_routing.py | 3C-agent-framework-part1 (**1 agent**) | Docstring references MAF Edge types but no `from agent_framework import` exists; custom FanOutStrategy/FanInAggregator/ConditionalRouter |
| **M-07** | **Streaming not implemented in Claude SDK Session.query()** | integrations/claude_sdk/session.py | 3C-claude-sdk (**1 agent**) | `stream` parameter accepted but unused; streaming only works via client.py direct calls |
| **M-08** | **MCP tool integration stubbed in Claude SDK registry** | integrations/claude_sdk/registry.py (line 85) | 3C-claude-sdk (**1 agent**) | `# TODO` comment at line 85; MCP tools cannot be auto-discovered |
| **M-09** | **CaseRepository PostgreSQL storage is interface-only** — falls back to in-memory | integrations/rootcause/case_repository.py | 3C-remaining (**1 agent**) | DB queries defined but not fully implemented; always uses in-memory with seed data |
| **M-10** | **Audit decision records stored in-memory only** — lost on restart | integrations/audit/ | 3C-remaining (**1 agent**) | Decision records in in-memory dict with no persistent backing |
| **M-11** | **A2A agent registry and messages in-memory only** — no external transport | integrations/a2a/ | 3C-remaining (**1 agent**) | Agent registry and message passing all in-memory; no inter-process communication |
| **M-12** | **Frontend Create/Edit pages ~80% code duplication** | frontend: agents/ (CreateAgentPage, EditAgentPage), workflows/ (CreateWorkflowPage, EditWorkflowPage) | 3E-frontend-part1 (**1 agent**) | Near-identical form structure, validation, tool/model lists; should extract shared AgentForm/WorkflowForm components |
| **M-13** | **~55+ console.log/warn/error statements in production frontend code** | UnifiedChat.tsx (~20), useAGUI, useSwarmReal, guestUser, various hooks | 3E-frontend-part1, 3E-frontend-part4 (**2 agents**) | Should use logging utility or remove; some are debug-gated (acceptable) |
| **M-14** | **6 of 7 AG-UI feature demos use simulated data** — misleading for evaluation | frontend: ag-ui/components/ | 3E-frontend-part1 (**1 agent**) | All demos except AgenticChatDemo use simulated data; no indicator shown |
| **M-15** | **Duplicate ApprovalDialog components** with different signatures | frontend: unified-chat/ (384 lines) vs ag-ui/ (245 lines) | 3E-frontend-part2 (**1 agent**) | unified-chat version has TimeoutCountdown; ag-ui version supports comments; different prop interfaces |
| **M-16** | **Frontend: tool lists and model providers hardcoded in form pages** | CreateAgentPage.tsx, EditAgentPage.tsx | 3E-frontend-part1 (**1 agent**) | Should fetch available tools/models from backend API |
| **M-17** | **Token estimation uses inaccurate heuristic** | UnifiedChat.tsx:476 | 3E-frontend-part1 (**1 agent**) | `~3 chars/token` heuristic when backend doesn't send TOKEN_UPDATE; inaccurate for non-English text |
| **M-18** | **SSH auto_add_host_keys enabled in dev mode** — must be disabled in production | integrations/mcp/servers/ssh/ | 3C-mcp-part2 (**1 agent**) | Accepts any host key when enabled; production deployments must verify |
| **M-19** | **PermissionManager falls back to ALL policies** when no user/role match found | integrations/mcp/core/ | 3C-mcp-part1 (**1 agent**) | May produce unexpected grants in multi-policy setups |
| **M-20** | **Swarm components lack explicit aria-labels** | frontend: WorkerCard, ToolCallItem | 3E-frontend-part2 (**1 agent**) | Accessibility gap for screen readers in swarm visualization |
| **M-21** | **StateDeltaOperation inherits from `str`** instead of using Enum | integrations/ag_ui/ | 3C-ag-ui (**1 agent**) | `StateDeltaOperation(str)` with class-level constants; inconsistent with rest of codebase Enum pattern |
| **M-22** | **FileAuditStorage uses synchronous file I/O** — blocks event loop | integrations/mcp/core/ | 3C-mcp-part1 (**1 agent**) | Should use `aiofiles` for async file operations |

---

## 4. LOW Issues (Nice to Fix)

| ID | Issue | Affected Modules | Reported By (Agent Count) | Evidence |
|----|-------|-----------------|---------------------------|----------|
| **L-01** | **UI barrel export inconsistency** — only 3 of 18 components exported from `ui/index.ts` | frontend: components/ui/index.ts | 3E-frontend-part3 (**1 agent**) | Only Button, Card, Badge exported; other 15 components imported by direct path |
| **L-02** | **dialog.tsx lowercase filename** inconsistent with PascalCase convention | frontend: components/ui/dialog.tsx | 3E-frontend-part3 (**1 agent**) | All other UI components use PascalCase filenames |
| **L-03** | **pairedEvent prop received but ignored** in DevUI panels | frontend: DevUI/LLMEventPanel.tsx, ToolEventPanel.tsx | 3E-frontend-part3 (**1 agent**) | Prop defined in interface but never used in render logic |
| **L-04** | **Header search bar non-functional** — visual only | frontend: layout/Header.tsx | 3E-frontend-part3 (**1 agent**) | Input element rendered but no search functionality connected |
| **L-05** | **Notification bell always shows red dot** — not connected to real notification system | frontend: layout/Header.tsx | 3E-frontend-part3 (**1 agent**) | Static indicator regardless of actual notification state |
| **L-06** | **Navigation items hardcoded in Sidebar** — not route-config driven | frontend: layout/Sidebar.tsx | 3E-frontend-part3 (**1 agent**) | Static navigation list; should be driven by route configuration |
| **L-07** | **2 "Coming Soon" placeholder pages** in DevUI | frontend: DevUI/LiveMonitor.tsx, DevUI/Settings.tsx | 3E-frontend-part1 (**1 agent**) | Explicitly marked as Sprint 87 placeholders |
| **L-08** | **"Use Template" button has no handler** | frontend: TemplatesPage.tsx | 3E-frontend-part1 (**1 agent**) | Button rendered but `onClick` handler not implemented |
| **L-09** | **Unused variable `cutoff` in Teams notification** | domain/notifications/teams.py:683 | 3B-part3 (**1 agent**) | Variable defined in `_check_rate_limit()` but never used |
| **L-10** | **Prompt template uses simple string replacement** but docstring claims "Jinja2 syntax" | domain/prompts/template.py | 3B-part3 (**1 agent**) | `{{variable}}` regex replacement, not actual Jinja2 engine |
| **L-11** | **Linear scan O(n) for relation queries** in scenario router | domain/routing/scenario_router.py | 3B-part3 (**1 agent**) | Should use indexed lookup for better performance |
| **L-12** | **Dual event system in sessions** — both ExecutionEvent and SessionEvent coexist | domain/sessions/ | 3B-part3 (**1 agent**) | ExecutionEvent (S45) and SessionEvent (original) create potential confusion |
| **L-13** | **5 migration shim files** in agent framework — backward compatibility facades | integrations/agent_framework/ | 3C-agent-framework-part1 (**1 agent**) | Should be tracked and removed once Phase 2 consumers are migrated |
| **L-14** | **`infrastructure/__init__.py` content mismatch** — contains misplaced comment | infrastructure/__init__.py | 3D-core-infra (**1 agent**) | File says `# Messaging infrastructure` but is the root infrastructure init |
| **L-15** | **Hardcoded AG-UI health check version "1.0.0"** | api/v1/ag_ui/ | 3A-part1 (**1 agent**) | Version string should come from package/config |
| **L-16** | **2 TODO comments for unimplemented features** in main chat page | frontend: UnifiedChat.tsx (lines 239, 732) | 3E-frontend-part1 (**1 agent**) | Orchestration UI toggles hardcoded to true; checkpoint restoration is stub only |

---

## Cross-Cutting Patterns

Issues appearing across 3+ modules, indicating systemic concerns:

### Pattern 1: In-Memory-Only Storage (20+ modules)
- **Issue ID**: C-01
- **Affected layers**: API (9 modules), Domain (6 modules), Integration (5+ modules)
- **Root cause**: Rapid prototyping without persistent storage follow-up; Redis/PostgreSQL adapters exist for some modules but not wired
- **Agent count**: 6 independent agents reported this
- **Impact**: Complete data loss on any server restart; blocks any production deployment

### Pattern 2: Mock API Routes Disconnected from Real Implementations (3 modules)
- **Issue IDs**: C-02, C-03, C-04, C-05
- **Affected modules**: correlation/, autonomous/, rootcause/, patrol/ API routes
- **Root cause**: API routes were built as Phase 22-23 UAT stubs; real implementations added later in integrations/ (Sprint 130) but API routes never updated to use them
- **Agent count**: 3 agents (3A-part1, 3A-part3, 3C-remaining)
- **Impact**: Endpoints return fake data; real analysis capabilities exist but are unreachable via REST API

### Pattern 3: Module-Level Singleton Anti-Pattern (10+ modules)
- **Issue ID**: H-03
- **Affected layers**: API (cache, approvals), Domain (deadlock detector, metrics, event publisher), Integration (AG-UI handlers)
- **Root cause**: Convenience pattern using `_global_instance` / `get_*()` factory functions instead of proper DI
- **Agent count**: 3 agents
- **Impact**: Difficult to test, hidden shared state, no clean shutdown/reset

### Pattern 4: Security Gaps in MCP Tool Execution (5+ servers)
- **Issue IDs**: H-06, H-07, M-05, M-18, M-19, H-12, H-13
- **Affected modules**: All 8 MCP servers, MCP core framework
- **Root cause**: Security features implemented but not fully wired (audit logger), or configured in permissive defaults (log mode)
- **Agent count**: 2 agents (3C-mcp-part1, 3C-mcp-part2)
- **Impact**: Tool executions not audited; unauthorized operations may proceed; command injection risks

### Pattern 5: Frontend Mock Data Fallbacks Without Indicators (10+ pages)
- **Issue IDs**: H-08, M-14
- **Affected modules**: Dashboard, AgentsPage, WorkflowsPage, ApprovalsPage, AuditPage, TemplatesPage, AG-UI demos
- **Root cause**: Silent try/catch with `generateMock*()` fallbacks for resilience, but no UI differentiation
- **Agent count**: 1 agent (comprehensive coverage)
- **Impact**: Users cannot distinguish real operational data from hardcoded mock data

### Pattern 6: `datetime.utcnow()` Deprecated Usage (6+ files)
- **Issue ID**: M-01
- **Affected layers**: API, Domain, Infrastructure
- **Root cause**: Code written before Python 3.12 deprecation; not systematically updated
- **Agent count**: 3 agents
- **Impact**: Deprecation warnings in Python 3.12+; potential removal in future Python versions

---

## Top 10 Most Impactful Issues

Ranked by: Severity (4=CRITICAL, 3=HIGH, 2=MEDIUM, 1=LOW) x Affected Module Count x Agent Report Count

| Rank | ID | Issue | Score | Breakdown |
|------|-----|-------|-------|-----------|
| 1 | **C-01** | In-memory-only storage across 20+ modules | **4 x 20 x 6 = 480** | CRITICAL, 20+ modules, 6 agents |
| 2 | **H-03** | Global singleton anti-pattern | **3 x 10 x 3 = 90** | HIGH, 10+ modules, 3 agents |
| 3 | **C-02** | Correlation API routes 100% mock | **4 x 2 x 2 = 16** | CRITICAL, 2 modules (API + integration), 2 agents |
| 4 | **C-04** | Root cause API routes 100% mock | **4 x 2 x 2 = 16** | CRITICAL, 2 modules, 2 agents |
| 5 | **M-01** | `datetime.utcnow()` deprecated | **2 x 6 x 3 = 36** | MEDIUM, 6+ files, 3 agents |
| 6 | **H-15** | Missing React Error Boundaries | **3 x 5 x 2 = 30** | HIGH, 5+ components, 2 agents |
| 7 | **H-08** | Frontend silent mock data fallbacks | **3 x 10 x 1 = 30** | HIGH, 10 pages, 1 agent |
| 8 | **C-07** | SQL injection via f-string in Postgres stores | **4 x 2 x 1 = 8** | CRITICAL, 2 stores, 1 agent |
| 9 | **C-08** | API key prefix exposed in AG-UI | **4 x 1 x 1 = 4** | CRITICAL, 1 module, 1 agent |
| 10 | **H-06** | MCP AuditLogger not wired | **3 x 8 x 1 = 24** | HIGH, 8 servers, 1 agent |

---

## Remediation Priority Roadmap

### Immediate (Sprint N)
1. **C-08**: Remove API key prefix from AG-UI reset response (1-line fix)
2. **C-07**: Replace f-string SQL with parameterized queries (2 files)
3. **H-02**: Gate test endpoints behind `APP_ENV != production` check
4. **M-02**: Replace `os.environ.get()` with `get_settings()` in health check

### Short-term (Sprint N+1 to N+2)
5. **C-02/C-04/C-05**: Wire real integration analyzers into API routes (correlation, rootcause, patrol)
6. **H-06/H-07**: Wire AuditLogger and set permission mode to `enforce` in production
7. **H-04**: Add asyncio.Lock to ContextBridge._context_cache
8. **H-01**: Add role-based checks on destructive API operations
9. **H-14**: Configure slowapi to use Redis storage URI

### Medium-term (Sprint N+3 to N+5)
10. **C-01**: Systematic persistence migration — prioritize audit, approval, chat session, a2a
11. **H-03**: Replace module-level singletons with FastAPI dependency injection
12. **H-08**: Add "Demo Data" visual indicator when mock fallbacks activate
13. **H-10**: Complete migration off deprecated domain/orchestration/ and remove dead code
14. **M-12**: Extract shared AgentForm/WorkflowForm components

### Long-term (Sprint N+6+)
15. **C-06**: Implement RabbitMQ/Azure Service Bus messaging infrastructure
16. **C-03**: Replace autonomous mock with real Claude SDK planning integration
17. **H-09**: Implement real sandbox with container/process isolation
18. **H-05**: Align checkpoint storage backends with official MAF API

---

## Appendix: Issue-to-Report Traceability

| Issue ID | Source Report(s) |
|----------|-----------------|
| C-01 | phase3a-api-layer-part1, part2, part3; phase3b-domain-layer-part3; phase3c-integration-ag-ui; phase3c-integration-remaining |
| C-02 | phase3a-api-layer-part1; phase3c-integration-remaining |
| C-03 | phase3a-api-layer-part1 |
| C-04 | phase3a-api-layer-part3; phase3c-integration-remaining |
| C-05 | phase3a-api-layer-part3; phase3c-integration-remaining |
| C-06 | phase3d-core-infra |
| C-07 | phase3c-integration-agent-framework-part2 |
| C-08 | phase3a-api-layer-part1 |
| H-01 | phase3a-api-layer-part1, part2 |
| H-02 | phase3a-api-layer-part1 |
| H-03 | phase3a-api-layer-part1; phase3b-domain-layer-part3; phase3c-integration-ag-ui |
| H-04 | phase3c-integration-hybrid-part1 |
| H-05 | phase3c-integration-agent-framework-part2 |
| H-06 | phase3c-integration-mcp-part1 |
| H-07 | phase3c-integration-mcp-part1 |
| H-08 | phase3e-frontend-part1 |
| H-09 | phase3b-domain-layer-part3 |
| H-10 | phase3b-domain-layer-part2 |
| H-11 | phase3e-frontend-part1 |
| H-12 | phase3c-integration-mcp-part2 |
| H-13 | phase3c-integration-mcp-part2 |
| H-14 | phase3d-core-infra |
| H-15 | phase3e-frontend-part1, part2 |
| H-16 | phase3b-domain-layer-part2 |
| M-01 | phase3a-api-layer-part2; phase3b-domain-layer-part3; phase3d-core-infra |
| M-02 | phase3d-core-infra |
| M-03 | phase3a-api-layer-part2 |
| M-04 | phase3a-api-layer-part2 |
| M-05 | phase3c-integration-mcp-part1 |
| M-06 | phase3c-integration-agent-framework-part1 |
| M-07 | phase3c-integration-claude-sdk |
| M-08 | phase3c-integration-claude-sdk |
| M-09 | phase3c-integration-remaining |
| M-10 | phase3c-integration-remaining |
| M-11 | phase3c-integration-remaining |
| M-12 | phase3e-frontend-part1 |
| M-13 | phase3e-frontend-part1, part4 |
| M-14 | phase3e-frontend-part1 |
| M-15 | phase3e-frontend-part2 |
| M-16 | phase3e-frontend-part1 |
| M-17 | phase3e-frontend-part1 |
| M-18 | phase3c-integration-mcp-part2 |
| M-19 | phase3c-integration-mcp-part1 |
| M-20 | phase3e-frontend-part2 |
| M-21 | phase3c-integration-ag-ui |
| M-22 | phase3c-integration-mcp-part1 |
| L-01 | phase3e-frontend-part3 |
| L-02 | phase3e-frontend-part3 |
| L-03 | phase3e-frontend-part3 |
| L-04 | phase3e-frontend-part3 |
| L-05 | phase3e-frontend-part3 |
| L-06 | phase3e-frontend-part3 |
| L-07 | phase3e-frontend-part1 |
| L-08 | phase3e-frontend-part1 |
| L-09 | phase3b-domain-layer-part3 |
| L-10 | phase3b-domain-layer-part3 |
| L-11 | phase3b-domain-layer-part3 |
| L-12 | phase3b-domain-layer-part3 |
| L-13 | phase3c-integration-agent-framework-part1 |
| L-14 | phase3d-core-infra |
| L-15 | phase3a-api-layer-part1 |
| L-16 | phase3e-frontend-part1 |
