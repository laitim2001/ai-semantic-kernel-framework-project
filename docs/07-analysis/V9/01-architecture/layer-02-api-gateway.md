# Layer 02: API Gateway

## Identity

- Files: 152 | LOC: 47,376
- Directory: `backend/src/api/v1/`
- Framework: FastAPI 0.100+ | Port: 8000
- Phase introduced: 1 (Sprint 1) | Phase last modified: 38 (Sprint 119)
- Route modules: 48 directories | Route files: 64 `.py` files
- Registered routers: 47 (1 public + 46 protected)
- Total endpoints: 560+ (REST) + 3 WebSocket

---

## File Inventory

### Infrastructure Files

| File | LOC | Purpose |
|------|-----|---------|
| `__init__.py` | 252 | Router aggregation — assembles api_router, public_router, protected_router |
| `dependencies.py` | 181 | Shared DI providers — `get_current_user`, `get_current_user_optional`, `get_current_active_admin`, `get_current_operator_or_admin` |

### Route Module Inventory (48 modules, 64 route files)

#### Phase 1: Foundation (17 modules)

| Module | Route Files | Endpoints | Prefix | Tags |
|--------|-------------|-----------|--------|------|
| `agents/` | `routes.py` | 6 | `/agents` | Agents |
| `workflows/` | `routes.py`, `graph_routes.py` | 9 + 3 = 12 | `/workflows` | Workflows, Workflow Graph |
| `executions/` | `routes.py` | 11 | `/executions` | Executions |
| `checkpoints/` | `routes.py` | 10 | `/checkpoints` | Checkpoints |
| `templates/` | `routes.py` | 11 | `/templates` | templates |
| `triggers/` | `routes.py` | 8 | `/triggers` | Triggers |
| `connectors/` | `routes.py` | 9 | `/connectors` | Connectors |
| `routing/` | `routes.py` | 14 | `/routing` | routing |
| `notifications/` | `routes.py` | 11 | `/notifications` | notifications |
| `audit/` | `routes.py`, `decision_routes.py` | 8 + 7 = 15 | `/audit`, `/audit/decisions` | Audit, Decision Audit |
| `cache/` | `routes.py` | 9 | `/cache` | Cache |
| `prompts/` | `routes.py` | 11 | `/prompts` | Prompts |
| `learning/` | `routes.py` | 13 | `/learning` | learning |
| `devtools/` | `routes.py` | 12 | `/devtools` | devtools |
| `dashboard/` | `routes.py` | 2 | `/dashboard` | Dashboard |
| `versioning/` | `routes.py` | 14 | `/versions` | versioning |
| `performance/` | `routes.py` | 11 | `/performance` | Performance |

#### Phase 2: Advanced Orchestration (5 modules)

| Module | Route Files | Endpoints | Prefix | Tags |
|--------|-------------|-----------|--------|------|
| `concurrent/` | `routes.py`, `websocket.py` | 13 + 2 WS = 15 | `/concurrent` | concurrent, concurrent-websocket |
| `handoff/` | `routes.py` | 14 | `/handoff` | Handoff |
| `groupchat/` | `routes.py` | 42 | `/groupchat` | GroupChat |
| `planning/` | `routes.py` | 46 | `/planning` | Planning |
| `nested/` | `routes.py` | 16 | `/nested` | Nested |

#### Phase 8-10: Extended Features (3 modules)

| Module | Route Files | Endpoints | Prefix | Tags |
|--------|-------------|-----------|--------|------|
| `code_interpreter/` | `routes.py`, `visualization.py` | 11 + 3 = 14 | `/code-interpreter` | Code Interpreter |
| `mcp/` | `routes.py` | 13 | `/mcp` | MCP |
| `sessions/` | `routes.py`, `chat.py`, `websocket.py` | 14 + 6 + 1 WS + 2 = 23 | `/sessions` | sessions, sessions-chat, sessions-websocket |

#### Phase 12: Claude Agent SDK (7 route files)

| Module | Route Files | Endpoints | Prefix | Tags |
|--------|-------------|-----------|--------|------|
| `claude_sdk/` | `routes.py` | 6 | `/claude-sdk` | Claude SDK |
| | `autonomous_routes.py` | 7 | `/claude-sdk/autonomous` | Claude SDK Autonomous |
| | `hooks_routes.py` | 6 | `/claude-sdk/hooks` | Claude SDK Hooks |
| | `hybrid_routes.py` | 5 | `/claude-sdk/hybrid` | Claude SDK Hybrid |
| | `intent_routes.py` | 6 | `/claude-sdk/intent` | Intent Router |
| | `mcp_routes.py` | 6 | `/claude-sdk/mcp` | Claude SDK MCP |
| | `tools_routes.py` | 4 | `/claude-sdk/tools` | Claude SDK Tools |

#### Phase 13-14: Hybrid MAF+Claude SDK (4 route files)

| Module | Route Files | Endpoints | Prefix | Tags |
|--------|-------------|-----------|--------|------|
| `hybrid/` | `context_routes.py` | 5 | `/hybrid/context` | Hybrid Context |
| | `core_routes.py` | 4 | `/hybrid` | Hybrid |
| | `risk_routes.py` | 7 | `/hybrid/risk` | Hybrid Risk |
| | `switch_routes.py` | 7 | `/hybrid/switch` | Hybrid Switch |

#### Phase 15: AG-UI Protocol (1 module)

| Module | Route Files | Endpoints | Prefix | Tags |
|--------|-------------|-----------|--------|------|
| `ag_ui/` | `routes.py`, `upload.py` | 29 + 4 = 33 | `/ag-ui`, `/ag-ui/upload` | ag-ui, File Upload |

#### Phase 18-22: Platform Features (5 modules)

| Module | Route Files | Endpoints | Prefix | Tags |
|--------|-------------|-----------|--------|------|
| `auth/` | `routes.py`, `migration.py` | 4 + 1 = 5 | `/auth` | Authentication |
| `files/` | `routes.py` | 6 | `/files` | Files |
| `memory/` | `routes.py` | 7 | `/memory` | Memory |
| `sandbox/` | `routes.py` | 6 | `/sandbox` | sandbox |
| `autonomous/` | `routes.py` | 4 | `/claude/autonomous` | Autonomous Planning |

#### Phase 23: Observability (4 modules)

| Module | Route Files | Endpoints | Prefix | Tags |
|--------|-------------|-----------|--------|------|
| `a2a/` | `routes.py` | 14 | `/a2a` | A2A Communication |
| `patrol/` | `routes.py` | 9 | `/patrol` | patrol |
| `correlation/` | `routes.py` | 7 | `/correlation` | correlation |
| `rootcause/` | `routes.py` | 4 | `/rootcause` | Root Cause Analysis |

#### Phase 28: Three-Tier Routing (6 route files)

| Module | Route Files | Endpoints | Prefix | Tags |
|--------|-------------|-----------|--------|------|
| `orchestration/` | `routes.py` | 7 | `/orchestration` | Orchestration |
| | `intent_routes.py` | 4 | `/orchestration/intent` | Intent Classification |
| | `dialog_routes.py` | 4 | `/orchestration/dialog` | Guided Dialog |
| | `approval_routes.py` | 4 | `/orchestration/approvals` | HITL Approvals |
| | `webhook_routes.py` | 3 | `/orchestration/webhooks` | orchestration-webhooks |
| | `route_management.py` | 7 | `/orchestration/routes` | orchestration-routes |

#### Phase 29: Agent Swarm (2 route files)

| Module | Route Files | Endpoints | Prefix | Tags |
|--------|-------------|-----------|--------|------|
| `swarm/` | `routes.py` | 3 | `/swarm` | Swarm |
| | `demo.py` | 5 | `/swarm/demo` | Swarm Demo |

#### Phase 34-38: Late Additions (6 modules)

| Module | Route Files | Endpoints | Prefix | Tags |
|--------|-------------|-----------|--------|------|
| `n8n/` | `routes.py` | 7 | `/n8n` | n8n Integration |
| `orchestrator/` | `routes.py` | 6 | `/orchestrator` | orchestrator |
| | `session_routes.py` | 2 | `/sessions` | sessions-resume |
| `chat_history/` | `routes.py` | 3 | `/chat-history` | Chat History |
| `tasks/` | `routes.py` | 9 | `/tasks` | tasks |
| `knowledge/` | `routes.py` | 7 | `/knowledge` | knowledge |

---

## Internal Architecture

### Router Assembly Structure

```
main.py
└── create_app()
    ├── RequestIdMiddleware            (Sprint 122)
    ├── CORSMiddleware                 (configurable origins)
    ├── RateLimitMiddleware            (slowapi, Sprint 111)
    ├── Global Exception Handler       (env-aware: dev=detail, prod=generic)
    │
    ├── GET  /                         Health — API info
    ├── GET  /health                   Health — DB + Redis status check
    ├── GET  /ready                    Readiness — K8s/Azure probe
    │
    └── include_router(api_router)     prefix=/api/v1
        │
        ├── public_router              (no auth)
        │   └── auth_router            /auth — login, register, refresh, me, migrate
        │
        └── protected_router           (Depends(require_auth) — JWT required)
            ├── Phase 1 Foundation     17 routers (agents, workflows, executions, ...)
            ├── Phase 2 Orchestration  6 routers (concurrent, handoff, groupchat, ...)
            ├── Phase 8-10 Extended    3 routers (code_interpreter, mcp, sessions)
            ├── Phase 12 Claude SDK    1 composite router (7 sub-routers)
            ├── Phase 13-14 Hybrid     4 routers (context, core, risk, switch)
            ├── Phase 15 AG-UI         1 composite router (routes + upload)
            ├── Phase 18-22 Platform   5 routers (auth migration, files, memory, sandbox, autonomous)
            ├── Phase 23 Observability 4 routers (a2a, patrol, correlation, rootcause)
            ├── Phase 28 Routing       6 routers (orchestration, intent, dialog, approval, webhook, route_mgmt)
            ├── Phase 29 Swarm         2 routers (swarm status, swarm demo)
            └── Phase 34-38 Late       6 routers (n8n, orchestrator, session_resume, chat_history, tasks, knowledge)
```

### Router Registration Order

A critical detail: `session_resume_router` (prefix `/sessions`) is registered **before** `sessions_router` (also prefix `/sessions`) to prevent the `/{session_id}` wildcard from capturing `/recoverable` and `/resume` paths. This ordering dependency is documented inline in `__init__.py`.

### Dependency Injection Pattern

```
Request
  ↓
protected_router → require_auth(credentials) → JWT claims dict {user_id, role}
  ↓
Route handler
  ↓
get_session() → AsyncSession (SQLAlchemy)
  ↓
Repository(session) → domain operations
```

Two auth layers are available:

| Dependency | Layer | DB Lookup | Returns |
|-----------|-------|-----------|---------|
| `require_auth` (core/auth.py) | Global on protected_router | No | `dict` with JWT claims |
| `get_current_user` (dependencies.py) | Per-route opt-in | Yes | `User` ORM model |
| `get_current_active_admin` | Per-route opt-in | Yes | `User` (role=admin) |
| `get_current_operator_or_admin` | Per-route opt-in | Yes | `User` (role in admin, operator) |

---

## Endpoint Catalog

### Domain A: Core Entity Management (78 endpoints)

CRUD operations for primary platform resources.

| Method | Path | Auth | Module | Description |
|--------|------|------|--------|-------------|
| POST | `/agents/` | JWT | agents | Create agent |
| GET | `/agents/` | JWT | agents | List agents (paginated) |
| GET | `/agents/{agent_id}` | JWT | agents | Get agent by ID |
| PUT | `/agents/{agent_id}` | JWT | agents | Update agent |
| DELETE | `/agents/{agent_id}` | JWT | agents | Delete agent |
| POST | `/agents/{agent_id}/run` | JWT | agents | Run agent with message |
| POST | `/workflows/` | JWT | workflows | Create workflow |
| GET | `/workflows/` | JWT | workflows | List workflows (paginated) |
| GET | `/workflows/{workflow_id}` | JWT | workflows | Get workflow |
| PUT | `/workflows/{workflow_id}` | JWT | workflows | Update workflow |
| DELETE | `/workflows/{workflow_id}` | JWT | workflows | Delete workflow |
| POST | `/workflows/{workflow_id}/execute` | JWT | workflows | Execute workflow |
| POST | `/workflows/{workflow_id}/validate` | JWT | workflows | Validate workflow definition |
| POST | `/workflows/{workflow_id}/activate` | JWT | workflows | Activate workflow |
| POST | `/workflows/{workflow_id}/deactivate` | JWT | workflows | Deactivate workflow |
| GET | `/workflows/{workflow_id}/graph` | JWT | graph_routes | Get workflow graph |
| PUT | `/workflows/{workflow_id}/graph` | JWT | graph_routes | Update workflow graph |
| POST | `/workflows/{workflow_id}/graph/validate` | JWT | graph_routes | Validate graph |
| GET | `/executions/` | JWT | executions | List executions |
| POST | `/executions/` | JWT | executions | Create execution |
| GET | `/executions/{execution_id}` | JWT | executions | Get execution |
| POST | `/executions/{execution_id}/cancel` | JWT | executions | Cancel execution |
| GET | `/executions/{execution_id}/transitions` | JWT | executions | Get valid transitions |
| GET | `/executions/status/running` | JWT | executions | List running executions |
| GET | `/executions/status/recent` | JWT | executions | List recent executions |
| GET | `/executions/workflows/{workflow_id}/stats` | JWT | executions | Workflow execution stats |
| POST | `/executions/{execution_id}/resume` | JWT | executions | Resume execution |
| GET | `/executions/{execution_id}/resume-status` | JWT | executions | Get resume status |
| POST | `/executions/{execution_id}/shutdown` | JWT | executions | Shutdown execution |
| GET | `/checkpoints/` | JWT | checkpoints | List checkpoints |
| GET | `/checkpoints/{checkpoint_id}` | JWT | checkpoints | Get checkpoint |
| POST | `/checkpoints/` | JWT | checkpoints | Create checkpoint |
| POST | `/checkpoints/{checkpoint_id}/approve` | JWT | checkpoints | Approve checkpoint |
| GET | `/checkpoints/executions/{execution_id}` | JWT | checkpoints | List by execution |
| GET | `/checkpoints/pending` | JWT | checkpoints | List pending |
| POST | `/checkpoints/{checkpoint_id}/reject` | JWT | checkpoints | Reject checkpoint |
| POST | `/checkpoints/{checkpoint_id}/modify` | JWT | checkpoints | Modify checkpoint |
| GET | `/checkpoints/statistics` | JWT | checkpoints | Checkpoint statistics |
| POST | `/checkpoints/{checkpoint_id}/timeout` | JWT | checkpoints | Set timeout |
| POST | `/templates/search` | JWT | templates | Search templates |
| GET | `/templates/` | JWT | templates | List templates |
| GET | `/templates/{template_id}` | JWT | templates | Get template |
| POST | `/templates/{template_id}/instantiate` | JWT | templates | Instantiate template |
| POST | `/templates/{template_id}/rate` | JWT | templates | Rate template |
| GET | `/templates/health` | JWT | templates | Health check |
| GET | `/templates/statistics/summary` | JWT | templates | Statistics summary |
| GET | `/templates/categories/list` | JWT | templates | List categories |
| GET | `/templates/popular/list` | JWT | templates | Popular templates |
| GET | `/templates/top-rated/list` | JWT | templates | Top rated templates |
| GET | `/templates/similar/{template_id}` | JWT | templates | Similar templates |
| POST | `/triggers/` | JWT | triggers | Create trigger |
| GET | `/triggers/` | JWT | triggers | List triggers |
| POST | `/triggers/test` | JWT | triggers | Test trigger |
| GET | `/triggers/{trigger_id}` | JWT | triggers | Get trigger |
| PUT | `/triggers/{trigger_id}` | JWT | triggers | Update trigger |
| DELETE | `/triggers/{trigger_id}` | JWT | triggers | Delete trigger |
| POST | `/triggers/{trigger_id}/activate` | JWT | triggers | Activate trigger |
| GET | `/triggers/statistics` | JWT | triggers | Trigger statistics |
| GET | `/connectors/` | JWT | connectors | List connectors |
| GET | `/connectors/{connector_id}` | JWT | connectors | Get connector |
| GET | `/connectors/types` | JWT | connectors | List connector types |
| GET | `/connectors/{connector_id}/config` | JWT | connectors | Get connector config |
| GET | `/connectors/{connector_id}/status` | JWT | connectors | Get connector status |
| GET | `/connectors/{connector_id}/metrics` | JWT | connectors | Get connector metrics |
| POST | `/connectors/` | JWT | connectors | Create connector |
| POST | `/connectors/{connector_id}/test` | JWT | connectors | Test connector |
| POST | `/connectors/{connector_id}/sync` | JWT | connectors | Sync connector |
| POST | `/tasks/` | JWT | tasks | Create task |
| GET | `/tasks/` | JWT | tasks | List tasks |
| GET | `/tasks/{task_id}` | JWT | tasks | Get task |
| PUT | `/tasks/{task_id}` | JWT | tasks | Update task |
| DELETE | `/tasks/{task_id}` | JWT | tasks | Delete task |
| POST | `/tasks/{task_id}/start` | JWT | tasks | Start task |
| POST | `/tasks/{task_id}/complete` | JWT | tasks | Complete task |
| POST | `/tasks/{task_id}/fail` | JWT | tasks | Fail task |
| POST | `/tasks/{task_id}/progress` | JWT | tasks | Update progress |

### Domain B: AI Agent Operations (148 endpoints)

Claude SDK, hybrid operations, planning, groupchat, handoff, concurrent execution, and nested workflows.

| Method | Path | Auth | Module | Description |
|--------|------|------|--------|-------------|
| **Claude SDK Core** | | | | |
| POST | `/claude-sdk/query` | JWT | claude_sdk | Query Claude SDK |
| POST | `/claude-sdk/sessions` | JWT | claude_sdk | Create SDK session |
| POST | `/claude-sdk/sessions/{session_id}/message` | JWT | claude_sdk | Send message |
| DELETE | `/claude-sdk/sessions/{session_id}` | JWT | claude_sdk | Close session |
| GET | `/claude-sdk/sessions/{session_id}/history` | JWT | claude_sdk | Session history |
| GET | `/claude-sdk/health` | JWT | claude_sdk | SDK health |
| **Claude SDK Autonomous** | | | | |
| POST | `/claude-sdk/autonomous/plan` | JWT | autonomous_routes | Create plan |
| GET | `/claude-sdk/autonomous/{plan_id}` | JWT | autonomous_routes | Get plan |
| POST | `/claude-sdk/autonomous/{plan_id}/execute` | JWT | autonomous_routes | Execute plan |
| DELETE | `/claude-sdk/autonomous/{plan_id}` | JWT | autonomous_routes | Delete plan |
| GET | `/claude-sdk/autonomous/` | JWT | autonomous_routes | List plans |
| POST | `/claude-sdk/autonomous/estimate` | JWT | autonomous_routes | Estimate plan |
| POST | `/claude-sdk/autonomous/{plan_id}/verify` | JWT | autonomous_routes | Verify plan |
| **Claude SDK Hooks** | | | | |
| GET | `/claude-sdk/hooks` | JWT | hooks_routes | List hooks |
| GET | `/claude-sdk/hooks/{hook_id}` | JWT | hooks_routes | Get hook |
| POST | `/claude-sdk/hooks/register` | JWT | hooks_routes | Register hook |
| DELETE | `/claude-sdk/hooks/{hook_id}` | JWT | hooks_routes | Delete hook |
| PUT | `/claude-sdk/hooks/{hook_id}/enable` | JWT | hooks_routes | Enable hook |
| PUT | `/claude-sdk/hooks/{hook_id}/disable` | JWT | hooks_routes | Disable hook |
| **Claude SDK Hybrid** | | | | |
| POST | `/claude-sdk/hybrid/execute` | JWT | hybrid_routes | Hybrid execute |
| POST | `/claude-sdk/hybrid/analyze` | JWT | hybrid_routes | Hybrid analyze |
| GET | `/claude-sdk/hybrid/metrics` | JWT | hybrid_routes | Hybrid metrics |
| POST | `/claude-sdk/hybrid/context/sync` | JWT | hybrid_routes | Context sync |
| GET | `/claude-sdk/hybrid/capabilities` | JWT | hybrid_routes | List capabilities |
| **Claude SDK Intent** | | | | |
| POST | `/claude-sdk/intent/classify` | JWT | intent_routes | Classify intent |
| POST | `/claude-sdk/intent/analyze-complexity` | JWT | intent_routes | Analyze complexity |
| POST | `/claude-sdk/intent/detect-multi-agent` | JWT | intent_routes | Detect multi-agent need |
| GET | `/claude-sdk/intent/classifiers` | JWT | intent_routes | List classifiers |
| GET | `/claude-sdk/intent/stats` | JWT | intent_routes | Intent stats |
| PUT | `/claude-sdk/intent/config` | JWT | intent_routes | Update config |
| **Claude SDK MCP** | | | | |
| GET | `/claude-sdk/mcp/servers` | JWT | mcp_routes | List MCP servers |
| POST | `/claude-sdk/mcp/servers/connect` | JWT | mcp_routes | Connect server |
| POST | `/claude-sdk/mcp/servers/{server_id}/disconnect` | JWT | mcp_routes | Disconnect server |
| GET | `/claude-sdk/mcp/servers/{server_id}/health` | JWT | mcp_routes | Server health |
| GET | `/claude-sdk/mcp/tools` | JWT | mcp_routes | List tools |
| POST | `/claude-sdk/mcp/tools/execute` | JWT | mcp_routes | Execute tool |
| **Claude SDK Tools** | | | | |
| GET | `/claude-sdk/tools` | JWT | tools_routes | List tools |
| GET | `/claude-sdk/tools/{name}` | JWT | tools_routes | Get tool by name |
| POST | `/claude-sdk/tools/execute` | JWT | tools_routes | Execute tool |
| POST | `/claude-sdk/tools/validate` | JWT | tools_routes | Validate tool |
| **Hybrid MAF+SDK** | | | | |
| GET | `/hybrid/context/` | JWT | context_routes | Get context |
| GET | `/hybrid/context/{session_id}` | JWT | context_routes | Get session context |
| POST | `/hybrid/context/sync` | JWT | context_routes | Sync context |
| POST | `/hybrid/context/merge` | JWT | context_routes | Merge context |
| GET | `/hybrid/context/health` | JWT | context_routes | Context health |
| POST | `/hybrid/execute` | JWT | core_routes | Hybrid execute |
| POST | `/hybrid/analyze` | JWT | core_routes | Hybrid analyze |
| GET | `/hybrid/status` | JWT | core_routes | Hybrid status |
| GET | `/hybrid/health` | JWT | core_routes | Hybrid health |
| POST | `/hybrid/risk/assess` | JWT | risk_routes | Risk assessment |
| POST | `/hybrid/risk/batch` | JWT | risk_routes | Batch risk assessment |
| GET | `/hybrid/risk/policies` | JWT | risk_routes | List risk policies |
| GET | `/hybrid/risk/history` | JWT | risk_routes | Risk history |
| DELETE | `/hybrid/risk/cache` | JWT | risk_routes | Clear risk cache |
| POST | `/hybrid/risk/validate` | JWT | risk_routes | Validate risk policy |
| GET | `/hybrid/risk/health` | JWT | risk_routes | Risk health |
| POST | `/hybrid/switch/mode` | JWT | switch_routes | Switch mode |
| GET | `/hybrid/switch/status` | JWT | switch_routes | Switch status |
| POST | `/hybrid/switch/auto` | JWT | switch_routes | Auto switch |
| GET | `/hybrid/switch/history` | JWT | switch_routes | Switch history |
| GET | `/hybrid/switch/health` | JWT | switch_routes | Switch health |
| DELETE | `/hybrid/switch/sessions/{session_id}` | JWT | switch_routes | Clear session |
| DELETE | `/hybrid/switch/cache` | JWT | switch_routes | Clear cache |
| **Planning** (46 endpoints) | | | | |
| POST | `/planning/decompose` | JWT | planning | Decompose task |
| POST | `/planning/decompose/{task_id}/refine` | JWT | planning | Refine decomposition |
| POST | `/planning/plans` | JWT | planning | Create plan |
| GET | `/planning/plans/{plan_id}` | JWT | planning | Get plan |
| GET | `/planning/plans/{plan_id}/status` | JWT | planning | Plan status |
| POST | `/planning/plans/{plan_id}/approve` | JWT | planning | Approve plan |
| POST | `/planning/plans/{plan_id}/execute` | JWT | planning | Execute plan |
| POST | `/planning/plans/{plan_id}/pause` | JWT | planning | Pause plan |
| POST | `/planning/plans/{plan_id}/adjustments/approve` | JWT | planning | Approve adjustments |
| GET | `/planning/plans` | JWT | planning | List plans |
| DELETE | `/planning/plans/{plan_id}` | JWT | planning | Delete plan |
| POST | `/planning/decisions` | JWT | planning | Create decision |
| GET | `/planning/decisions/{decision_id}/explain` | JWT | planning | Explain decision |
| POST | `/planning/decisions/{decision_id}/approve` | JWT | planning | Approve decision |
| POST | `/planning/decisions/{decision_id}/reject` | JWT | planning | Reject decision |
| GET | `/planning/decisions` | JWT | planning | List decisions |
| GET | `/planning/decisions/rules` | JWT | planning | Decision rules |
| POST | `/planning/trial` | JWT | planning | Create trial |
| GET | `/planning/trial/insights` | JWT | planning | Trial insights |
| GET | `/planning/trial/recommendations` | JWT | planning | Recommendations |
| GET | `/planning/trial/statistics` | JWT | planning | Trial stats |
| GET | `/planning/trial/history` | JWT | planning | Trial history |
| DELETE | `/planning/trial/history` | JWT | planning | Clear trial history |
| POST | `/planning/magentic/adapter` | JWT | planning | Create Magentic adapter |
| GET | `/planning/magentic/adapter/{id}` | JWT | planning | Get Magentic adapter |
| DELETE | `/planning/magentic/adapter/{id}` | JWT | planning | Delete Magentic adapter |
| POST | `/planning/magentic/adapter/{id}/run` | JWT | planning | Run Magentic adapter |
| POST | `/planning/magentic/adapter/{id}/intervention` | JWT | planning | Intervene |
| GET | `/planning/magentic/adapters` | JWT | planning | List Magentic adapters |
| GET | `/planning/magentic/adapter/{id}/ledger` | JWT | planning | Get ledger |
| POST | `/planning/magentic/adapter/{id}/reset` | JWT | planning | Reset adapter |
| POST | `/planning/adapter/planning` | JWT | planning | Create planning adapter |
| GET | `/planning/adapter/planning/{id}` | JWT | planning | Get planning adapter |
| POST | `/planning/adapter/planning/{id}/run` | JWT | planning | Run planning adapter |
| DELETE | `/planning/adapter/planning/{id}` | JWT | planning | Delete planning adapter |
| GET | `/planning/adapter/planning` | JWT | planning | List planning adapters |
| POST | `/planning/adapter/multiturn` | JWT | planning | Create multi-turn |
| GET | `/planning/adapter/multiturn/{id}` | JWT | planning | Get multi-turn |
| POST | `/planning/adapter/multiturn/{id}/turn` | JWT | planning | Submit turn |
| GET | `/planning/adapter/multiturn/{id}/history` | JWT | planning | Turn history |
| POST | `/planning/adapter/multiturn/{id}/checkpoint` | JWT | planning | Save checkpoint |
| POST | `/planning/adapter/multiturn/{id}/restore` | JWT | planning | Restore checkpoint |
| POST | `/planning/adapter/multiturn/{id}/complete` | JWT | planning | Complete session |
| DELETE | `/planning/adapter/multiturn/{id}` | JWT | planning | Delete session |
| GET | `/planning/adapter/multiturn` | JWT | planning | List sessions |
| GET | `/planning/health` | JWT | planning | Health check |
| **GroupChat** (42 endpoints) | | | | |
| POST | `/groupchat/` | JWT | groupchat | Create group |
| GET | `/groupchat/` | JWT | groupchat | List groups |
| GET | `/groupchat/{group_id}` | JWT | groupchat | Get group |
| PATCH | `/groupchat/{group_id}/config` | JWT | groupchat | Update config |
| POST | `/groupchat/{group_id}/agents/{agent_id}` | JWT | groupchat | Add agent |
| DELETE | `/groupchat/{group_id}/agents/{agent_id}` | JWT | groupchat | Remove agent |
| POST | `/groupchat/{group_id}/start` | JWT | groupchat | Start conversation |
| POST | `/groupchat/{group_id}/message` | JWT | groupchat | Send message |
| GET | `/groupchat/{group_id}/messages` | JWT | groupchat | Get messages |
| GET | `/groupchat/{group_id}/transcript` | JWT | groupchat | Get transcript |
| GET | `/groupchat/{group_id}/summary` | JWT | groupchat | Get summary |
| POST | `/groupchat/{group_id}/terminate` | JWT | groupchat | Terminate |
| DELETE | `/groupchat/{group_id}` | JWT | groupchat | Delete group |
| WS | `/groupchat/{group_id}/ws` | — | groupchat | WebSocket real-time |
| POST | `/groupchat/sessions/` | JWT | groupchat | Create session |
| GET | `/groupchat/sessions/` | JWT | groupchat | List sessions |
| GET | `/groupchat/sessions/{id}` | JWT | groupchat | Get session |
| POST | `/groupchat/sessions/{id}/turns` | JWT | groupchat | Submit turn |
| GET | `/groupchat/sessions/{id}/history` | JWT | groupchat | Session history |
| PATCH | `/groupchat/sessions/{id}/context` | JWT | groupchat | Update context |
| POST | `/groupchat/sessions/{id}/close` | JWT | groupchat | Close session |
| DELETE | `/groupchat/sessions/{id}` | JWT | groupchat | Delete session |
| POST | `/groupchat/voting/` | JWT | groupchat | Create voting |
| GET | `/groupchat/voting/` | JWT | groupchat | List voting |
| GET | `/groupchat/voting/{id}` | JWT | groupchat | Get voting |
| POST | `/groupchat/voting/{id}/vote` | JWT | groupchat | Cast vote |
| PATCH | `/groupchat/voting/{id}/vote/{voter_id}` | JWT | groupchat | Update vote |
| DELETE | `/groupchat/voting/{id}/vote/{voter_id}` | JWT | groupchat | Delete vote |
| GET | `/groupchat/voting/{id}/votes` | JWT | groupchat | List votes |
| POST | `/groupchat/voting/{id}/calculate` | JWT | groupchat | Calculate results |
| GET | `/groupchat/voting/{id}/statistics` | JWT | groupchat | Voting stats |
| POST | `/groupchat/voting/{id}/close` | JWT | groupchat | Close voting |
| POST | `/groupchat/voting/{id}/cancel` | JWT | groupchat | Cancel voting |
| DELETE | `/groupchat/voting/{id}` | JWT | groupchat | Delete voting |
| POST | `/groupchat/adapter/` | JWT | groupchat | Create adapter |
| GET | `/groupchat/adapter/` | JWT | groupchat | List adapters |
| GET | `/groupchat/adapter/{id}` | JWT | groupchat | Get adapter |
| POST | `/groupchat/adapter/{id}/run` | JWT | groupchat | Run adapter |
| POST | `/groupchat/adapter/{id}/participants` | JWT | groupchat | Add participant |
| DELETE | `/groupchat/adapter/{id}/participants/{name}` | JWT | groupchat | Remove participant |
| DELETE | `/groupchat/adapter/{id}` | JWT | groupchat | Delete adapter |
| POST | `/groupchat/orchestrator/select` | JWT | groupchat | Manager selection |
| **Handoff** (14 endpoints) | | | | |
| POST | `/handoff/` | JWT | handoff | Create handoff |
| GET | `/handoff/` | JWT | handoff | List handoffs |
| POST | `/handoff/initiate` | JWT | handoff | Initiate handoff |
| GET | `/handoff/{handoff_id}` | JWT | handoff | Get handoff |
| POST | `/handoff/{handoff_id}/execute` | JWT | handoff | Execute handoff |
| GET | `/handoff/{handoff_id}/status` | JWT | handoff | Handoff status |
| POST | `/handoff/{handoff_id}/rollback` | JWT | handoff | Rollback handoff |
| DELETE | `/handoff/{handoff_id}` | JWT | handoff | Delete handoff |
| GET | `/handoff/types` | JWT | handoff | List handoff types |
| GET | `/handoff/statistics` | JWT | handoff | Handoff statistics |
| GET | `/handoff/{handoff_id}/history` | JWT | handoff | Handoff history |
| POST | `/handoff/adapter` | JWT | handoff | Create adapter |
| POST | `/handoff/adapter/{id}/run` | JWT | handoff | Run adapter |
| POST | `/handoff/adapter/{id}/perform` | JWT | handoff | Perform handoff |
| **Concurrent** (13 + 2 WS) | | | | |
| POST | `/concurrent/` | JWT | concurrent | Create fork-join |
| GET | `/concurrent/` | JWT | concurrent | List executions |
| GET | `/concurrent/{execution_id}` | JWT | concurrent | Get execution |
| GET | `/concurrent/{execution_id}/tasks` | JWT | concurrent | List tasks |
| POST | `/concurrent/{execution_id}/cancel` | JWT | concurrent | Cancel execution |
| POST | `/concurrent/{execution_id}/retry` | JWT | concurrent | Retry execution |
| GET | `/concurrent/{execution_id}/progress` | JWT | concurrent | Execution progress |
| GET | `/concurrent/{execution_id}/result` | JWT | concurrent | Execution result |
| POST | `/concurrent/{execution_id}/barrier` | JWT | concurrent | Set barrier |
| GET | `/concurrent/statistics` | JWT | concurrent | Statistics |
| GET | `/concurrent/metrics` | JWT | concurrent | Metrics |
| GET | `/concurrent/health` | JWT | concurrent | Health check |
| GET | `/concurrent/{execution_id}/timeline` | JWT | concurrent | Timeline |
| WS | `/concurrent/ws/{execution_id}` | — | concurrent | WebSocket (execution) |
| WS | `/concurrent/ws` | — | concurrent | WebSocket (global) |
| **Nested** (16 endpoints) | | | | |
| POST | `/nested/` | JWT | nested | Create nested workflow |
| GET | `/nested/` | JWT | nested | List nested workflows |
| GET | `/nested/{workflow_id}` | JWT | nested | Get workflow |
| DELETE | `/nested/{workflow_id}` | JWT | nested | Delete workflow |
| POST | `/nested/{workflow_id}/execute` | JWT | nested | Execute workflow |
| POST | `/nested/{workflow_id}/validate` | JWT | nested | Validate workflow |
| GET | `/nested/{workflow_id}/status` | JWT | nested | Workflow status |
| POST | `/nested/{workflow_id}/cancel` | JWT | nested | Cancel workflow |
| POST | `/nested/{workflow_id}/retry` | JWT | nested | Retry workflow |
| GET | `/nested/{workflow_id}/progress` | JWT | nested | Get progress |
| POST | `/nested/adapter` | JWT | nested | Create adapter |
| POST | `/nested/adapter/{id}/run` | JWT | nested | Run adapter |
| POST | `/nested/adapter/{id}/step` | JWT | nested | Step adapter |
| GET | `/nested/adapter/{id}/state` | JWT | nested | Get state |
| GET | `/nested/adapter/{id}/children` | JWT | nested | Get children |
| GET | `/nested/health` | JWT | nested | Health check |

### Domain C: Real-Time & Collaboration (56 endpoints)

Sessions, chat, AG-UI streaming, and swarm visualization.

| Method | Path | Auth | Module | Description |
|--------|------|------|--------|-------------|
| **Sessions** (14 endpoints) | | | | |
| POST | `/sessions/` | JWT | sessions | Create session |
| GET | `/sessions/` | JWT | sessions | List sessions |
| GET | `/sessions/{session_id}` | JWT | sessions | Get session |
| PATCH | `/sessions/{session_id}` | JWT | sessions | Update session |
| DELETE | `/sessions/{session_id}` | JWT | sessions | Delete session |
| POST | `/sessions/{session_id}/end` | JWT | sessions | End session |
| POST | `/sessions/{session_id}/messages` | JWT | sessions | Add message |
| POST | `/sessions/{session_id}/tool-calls` | JWT | sessions | Add tool call |
| GET | `/sessions/{session_id}/messages` | JWT | sessions | List messages |
| POST | `/sessions/{session_id}/tool-calls/{id}/approve` | JWT | sessions | Approve tool call |
| POST | `/sessions/{session_id}/tool-calls/{id}/reject` | JWT | sessions | Reject tool call |
| GET | `/sessions/{session_id}/tool-calls` | JWT | sessions | List tool calls |
| GET | `/sessions/{session_id}/statistics` | JWT | sessions | Session stats |
| POST | `/sessions/{session_id}/export` | JWT | sessions | Export session |
| **Sessions Chat** (6 endpoints) | | | | |
| POST | `/sessions/{session_id}/chat` | JWT | sessions/chat | Send message (sync) |
| POST | `/sessions/{session_id}/chat/stream` | JWT | sessions/chat | Send message (SSE) |
| GET | `/sessions/{session_id}/chat/history` | JWT | sessions/chat | Chat history |
| POST | `/sessions/{session_id}/chat/feedback` | JWT | sessions/chat | Submit feedback |
| DELETE | `/sessions/{session_id}/chat/history` | JWT | sessions/chat | Clear history |
| GET | `/sessions/{session_id}/chat/export` | JWT | sessions/chat | Export chat |
| **Sessions WebSocket** | | | | |
| WS | `/sessions/{session_id}/ws` | — | sessions/ws | Real-time WebSocket |
| GET | `/sessions/{session_id}/ws/status` | JWT | sessions/ws | WS status |
| POST | `/sessions/{session_id}/ws/broadcast` | JWT | sessions/ws | WS broadcast |
| **Session Resume** (2 endpoints) | | | | |
| GET | `/sessions/recoverable` | JWT | orchestrator/session | List recoverable |
| POST | `/sessions/{session_id}/resume` | JWT | orchestrator/session | Resume session |
| **Chat History** (3 endpoints) | | | | |
| POST | `/chat-history/sync` | JWT | chat_history | Sync history |
| GET | `/chat-history/{session_id}` | JWT | chat_history | Get history |
| DELETE | `/chat-history/{session_id}` | JWT | chat_history | Delete history |
| **AG-UI** (29 endpoints) | | | | |
| GET | `/ag-ui/health` | JWT | ag_ui | Health check |
| GET | `/ag-ui/config` | JWT | ag_ui | Get config |
| POST | `/ag-ui/run` | JWT | ag_ui | Run agent (SSE stream) |
| POST | `/ag-ui/run/sync` | JWT | ag_ui | Run agent (sync) |
| POST | `/ag-ui/run/advanced` | JWT | ag_ui | Run advanced (SSE) |
| GET | `/ag-ui/threads` | JWT | ag_ui | List threads |
| GET | `/ag-ui/threads/{thread_id}` | JWT | ag_ui | Get thread |
| GET | `/ag-ui/threads/{thread_id}/messages` | JWT | ag_ui | Thread messages |
| GET | `/ag-ui/threads/{thread_id}/state` | JWT | ag_ui | Thread state |
| POST | `/ag-ui/threads/{thread_id}/state` | JWT | ag_ui | Update state |
| POST | `/ag-ui/threads/{thread_id}/message` | JWT | ag_ui | Add message |
| POST | `/ag-ui/hitl/request` | JWT | ag_ui | HITL request |
| GET | `/ag-ui/hitl/pending` | JWT | ag_ui | Pending approvals |
| PATCH | `/ag-ui/hitl/{approval_id}` | JWT | ag_ui | Respond to approval |
| DELETE | `/ag-ui/hitl/{approval_id}` | JWT | ag_ui | Cancel approval |
| POST | `/ag-ui/tool-ui/render` | JWT | ag_ui | Render tool UI |
| POST | `/ag-ui/tool-ui/form/submit` | JWT | ag_ui | Submit form |
| POST | `/ag-ui/tool-ui/validate` | JWT | ag_ui | Validate tool UI |
| POST | `/ag-ui/shared-state/init` | JWT | ag_ui | Init shared state |
| POST | `/ag-ui/shared-state/update` | JWT | ag_ui | Update state |
| POST | `/ag-ui/shared-state/subscribe` | JWT | ag_ui | Subscribe to state |
| POST | `/ag-ui/shared-state/broadcast` | JWT | ag_ui | Broadcast state |
| POST | `/ag-ui/predictive/predict` | JWT | ag_ui | Predict state |
| POST | `/ag-ui/predictive/confirm` | JWT | ag_ui | Confirm prediction |
| POST | `/ag-ui/upload` | JWT | ag_ui/upload | Upload file |
| GET | `/ag-ui/upload/list` | JWT | ag_ui/upload | List files |
| DELETE | `/ag-ui/upload/{filename}` | JWT | ag_ui/upload | Delete file |
| GET | `/ag-ui/upload/storage` | JWT | ag_ui/upload | Storage info |
| **Swarm** (8 endpoints) | | | | |
| GET | `/swarm/` | JWT | swarm | Swarm status |
| GET | `/swarm/{swarm_id}` | JWT | swarm | Get swarm |
| GET | `/swarm/{swarm_id}/workers` | JWT | swarm | List workers |
| POST | `/swarm/demo/start` | JWT | swarm/demo | Start demo swarm |
| GET | `/swarm/demo/events/{swarm_id}` | JWT | swarm/demo | SSE event stream |
| POST | `/swarm/demo/cancel/{swarm_id}` | JWT | swarm/demo | Cancel demo |
| GET | `/swarm/demo/status/{swarm_id}` | JWT | swarm/demo | Demo status |
| GET | `/swarm/demo/list` | JWT | swarm/demo | List demos |

### Domain D: Orchestration & Routing (58 endpoints)

Three-tier intent routing, orchestrator chat pipeline, cross-scenario routing, and n8n integration.

| Method | Path | Auth | Module | Description |
|--------|------|------|--------|-------------|
| **Orchestration Policies** (7 endpoints) | | | | |
| GET | `/orchestration/policies` | JWT | orchestration | List policies |
| GET | `/orchestration/policies/{intent_category}` | JWT | orchestration | Get policies by category |
| POST | `/orchestration/policies/mode/{mode}` | JWT | orchestration | Set policy mode |
| POST | `/orchestration/risk/assess` | JWT | orchestration | Risk assessment |
| GET | `/orchestration/metrics` | JWT | orchestration | Get metrics |
| POST | `/orchestration/metrics/reset` | JWT | orchestration | Reset metrics |
| GET | `/orchestration/health` | JWT | orchestration | Health check |
| **Orchestration Intent** (4 endpoints) | | | | |
| POST | `/orchestration/intent/classify` | JWT | intent_routes | Classify intent |
| POST | `/orchestration/intent/test` | JWT | intent_routes | Test classification |
| POST | `/orchestration/intent/classify/batch` | JWT | intent_routes | Batch classify |
| POST | `/orchestration/intent/quick` | JWT | intent_routes | Quick classify |
| **Orchestration Dialog** (4 endpoints) | | | | |
| POST | `/orchestration/dialog/start` | JWT | dialog_routes | Start dialog |
| POST | `/orchestration/dialog/{dialog_id}/respond` | JWT | dialog_routes | Respond to dialog |
| GET | `/orchestration/dialog/{dialog_id}/status` | JWT | dialog_routes | Dialog status |
| DELETE | `/orchestration/dialog/{dialog_id}` | JWT | dialog_routes | Delete dialog |
| **Orchestration Approvals** (4 endpoints) | | | | |
| GET | `/orchestration/approvals` | JWT | approval_routes | List approvals |
| GET | `/orchestration/approvals/{approval_id}` | JWT | approval_routes | Get approval |
| POST | `/orchestration/approvals/{approval_id}/decision` | JWT | approval_routes | Submit decision |
| POST | `/orchestration/approvals/{approval_id}/callback` | JWT | approval_routes | Approval callback |
| **Orchestration Webhooks** (3 endpoints) | | | | |
| POST | `/orchestration/webhooks/servicenow` | JWT | webhook_routes | ServiceNow webhook |
| GET | `/orchestration/webhooks/servicenow/health` | JWT | webhook_routes | Webhook health |
| POST | `/orchestration/webhooks/servicenow/incident` | JWT | webhook_routes | Incident webhook |
| **Orchestration Route Management** (7 endpoints) | | | | |
| POST | `/orchestration/routes` | JWT | route_mgmt | Create route |
| GET | `/orchestration/routes` | JWT | route_mgmt | List routes |
| GET | `/orchestration/routes/{route_name}` | JWT | route_mgmt | Get route |
| PUT | `/orchestration/routes/{route_name}` | JWT | route_mgmt | Update route |
| DELETE | `/orchestration/routes/{route_name}` | JWT | route_mgmt | Delete route |
| POST | `/orchestration/routes/sync` | JWT | route_mgmt | Sync routes |
| POST | `/orchestration/routes/search` | JWT | route_mgmt | Search routes |
| **Orchestrator Chat** (6 endpoints) | | | | |
| GET | `/orchestrator/validate` | JWT | orchestrator | Validate pipeline |
| GET | `/orchestrator/health` | JWT | orchestrator | Health check |
| GET | `/orchestrator/test-intent` | JWT | orchestrator | Test intent |
| POST | `/orchestrator/approval/{approval_id}` | JWT | orchestrator | Submit approval |
| POST | `/orchestrator/chat/stream` | JWT | orchestrator | Chat SSE stream |
| POST | `/orchestrator/chat` | JWT | orchestrator | Chat sync |
| **Cross-Scenario Routing** (14 endpoints) | | | | |
| POST | `/routing/route` | JWT | routing | Route request |
| POST | `/routing/relations` | JWT | routing | Create relation |
| GET | `/routing/executions/{id}/relations` | JWT | routing | Get relations |
| GET | `/routing/executions/{id}/chain` | JWT | routing | Get chain |
| GET | `/routing/relations/{id}` | JWT | routing | Get relation |
| DELETE | `/routing/relations/{id}` | JWT | routing | Delete relation |
| GET | `/routing/scenarios` | JWT | routing | List scenarios |
| GET | `/routing/scenarios/{name}` | JWT | routing | Get scenario |
| PUT | `/routing/scenarios/{name}` | JWT | routing | Update scenario |
| POST | `/routing/scenarios/{name}/workflow` | JWT | routing | Attach workflow |
| GET | `/routing/relation-types` | JWT | routing | List relation types |
| GET | `/routing/statistics` | JWT | routing | Routing statistics |
| DELETE | `/routing/relations` | JWT | routing | Clear relations |
| GET | `/routing/health` | JWT | routing | Health check |
| **n8n Integration** (7 endpoints) | | | | |
| POST | `/n8n/webhooks` | JWT | n8n | Create webhook |
| POST | `/n8n/webhooks/invoke` | JWT | n8n | Invoke webhook |
| GET | `/n8n/webhooks` | JWT | n8n | List webhooks |
| GET | `/n8n/webhooks/{webhook_id}` | JWT | n8n | Get webhook |
| PUT | `/n8n/webhooks/{webhook_id}` | JWT | n8n | Update webhook |
| POST | `/n8n/workflows/execute` | JWT | n8n | Execute workflow |
| GET | `/n8n/health` | JWT | n8n | Health check |

### Domain E: Monitoring & Observability (80 endpoints)

Audit, performance, patrol, correlation, root cause analysis, devtools, notifications, and dashboard.

| Method | Path | Auth | Module | Description |
|--------|------|------|--------|-------------|
| **Audit** (8 endpoints) | | | | |
| GET | `/audit/` | JWT | audit | List audit logs |
| GET | `/audit/{audit_id}` | JWT | audit | Get audit entry |
| GET | `/audit/executions/{id}` | JWT | audit | Audit by execution |
| GET | `/audit/agents/{id}` | JWT | audit | Audit by agent |
| GET | `/audit/workflows/{id}` | JWT | audit | Audit by workflow |
| GET | `/audit/statistics` | JWT | audit | Audit statistics |
| GET | `/audit/types` | JWT | audit | List audit types |
| GET | `/audit/export` | JWT | audit | Export audit data |
| **Decision Audit** (7 endpoints) | | | | |
| GET | `/audit/decisions/` | JWT | decision_audit | List decisions |
| GET | `/audit/decisions/{decision_id}` | JWT | decision_audit | Get decision |
| GET | `/audit/decisions/statistics` | JWT | decision_audit | Decision stats |
| POST | `/audit/decisions/analyze` | JWT | decision_audit | Analyze decisions |
| GET | `/audit/decisions/agents/{agent_id}` | JWT | decision_audit | Decisions by agent |
| GET | `/audit/decisions/sessions/{session_id}` | JWT | decision_audit | Decisions by session |
| GET | `/audit/decisions/export` | JWT | decision_audit | Export decisions |
| **Performance** (11 endpoints) | | | | |
| GET | `/performance/metrics` | JWT | performance | Get metrics |
| POST | `/performance/profile/start` | JWT | performance | Start profiling |
| POST | `/performance/profile/stop` | JWT | performance | Stop profiling |
| POST | `/performance/profile/metric` | JWT | performance | Record metric |
| GET | `/performance/profile/sessions` | JWT | performance | List sessions |
| GET | `/performance/profile/summary/{id}` | JWT | performance | Profile summary |
| POST | `/performance/optimize` | JWT | performance | Run optimization |
| GET | `/performance/collector/summary` | JWT | performance | Collector summary |
| GET | `/performance/collector/alerts` | JWT | performance | Collector alerts |
| POST | `/performance/collector/threshold` | JWT | performance | Set threshold |
| GET | `/performance/health` | JWT | performance | Health check |
| **Patrol** (9 endpoints) | | | | |
| POST | `/patrol/trigger` | JWT | patrol | Trigger patrol |
| GET | `/patrol/reports` | JWT | patrol | List reports |
| GET | `/patrol/reports/{report_id}` | JWT | patrol | Get report |
| GET | `/patrol/schedule` | JWT | patrol | List schedules |
| POST | `/patrol/schedule` | JWT | patrol | Create schedule |
| PUT | `/patrol/schedule/{patrol_id}` | JWT | patrol | Update schedule |
| DELETE | `/patrol/schedule/{patrol_id}` | JWT | patrol | Delete schedule |
| GET | `/patrol/checks` | JWT | patrol | List check types |
| GET | `/patrol/checks/{check_type}` | JWT | patrol | Run check |
| **Correlation** (7 endpoints) | | | | |
| POST | `/correlation/analyze` | JWT | correlation | Analyze events |
| GET | `/correlation/{event_id}` | JWT | correlation | Get correlation |
| POST | `/correlation/rootcause/analyze` | JWT | correlation | Root cause analysis |
| GET | `/correlation/rootcause/{analysis_id}` | JWT | correlation | Get analysis |
| GET | `/correlation/graph/{event_id}/mermaid` | JWT | correlation | Mermaid graph |
| GET | `/correlation/graph/{event_id}/json` | JWT | correlation | JSON graph |
| GET | `/correlation/graph/{event_id}/dot` | JWT | correlation | DOT graph |
| **Root Cause** (4 endpoints) | | | | |
| POST | `/rootcause/analyze` | JWT | rootcause | Analyze root cause |
| GET | `/rootcause/{analysis_id}/hypotheses` | JWT | rootcause | Get hypotheses |
| GET | `/rootcause/{analysis_id}/recommendations` | JWT | rootcause | Get recommendations |
| POST | `/rootcause/similar` | JWT | rootcause | Find similar patterns |
| **DevTools** (12 endpoints) | | | | |
| GET | `/devtools/health` | JWT | devtools | Health check |
| GET | `/devtools/traces` | JWT | devtools | List traces |
| POST | `/devtools/traces` | JWT | devtools | Create trace |
| GET | `/devtools/traces/{execution_id}` | JWT | devtools | Get trace |
| POST | `/devtools/traces/{execution_id}/end` | JWT | devtools | End trace |
| DELETE | `/devtools/traces/{execution_id}` | JWT | devtools | Delete trace |
| POST | `/devtools/traces/{execution_id}/events` | JWT | devtools | Add event |
| GET | `/devtools/traces/{execution_id}/events` | JWT | devtools | List events |
| POST | `/devtools/traces/{execution_id}/spans` | JWT | devtools | Create span |
| POST | `/devtools/spans/{span_id}/end` | JWT | devtools | End span |
| GET | `/devtools/traces/{execution_id}/timeline` | JWT | devtools | Get timeline |
| GET | `/devtools/traces/{execution_id}/statistics` | JWT | devtools | Trace stats |
| **Notifications** (11 endpoints) | | | | |
| POST | `/notifications/approval` | JWT | notifications | Send approval |
| POST | `/notifications/completion` | JWT | notifications | Send completion |
| POST | `/notifications/error` | JWT | notifications | Send error |
| POST | `/notifications/custom` | JWT | notifications | Send custom |
| GET | `/notifications/history` | JWT | notifications | List history |
| GET | `/notifications/statistics` | JWT | notifications | Get stats |
| DELETE | `/notifications/history` | JWT | notifications | Clear history |
| GET | `/notifications/config` | JWT | notifications | Get config |
| PUT | `/notifications/config` | JWT | notifications | Update config |
| GET | `/notifications/types` | JWT | notifications | List types |
| GET | `/notifications/health` | JWT | notifications | Health check |
| **Dashboard** (2 endpoints) | | | | |
| GET | `/dashboard/stats` | JWT | dashboard | Dashboard stats |
| GET | `/dashboard/executions/chart` | JWT | dashboard | Execution chart |

### Domain F: Platform Infrastructure (55 endpoints)

Auth, files, memory, sandbox, cache, knowledge, versioning, prompts, learning, and code interpreter.

| Method | Path | Auth | Module | Description |
|--------|------|------|--------|-------------|
| **Auth** (5 endpoints) | | | | |
| POST | `/auth/register` | Public | auth | Register user |
| POST | `/auth/login` | Public | auth | Login (get JWT) |
| POST | `/auth/refresh` | Public | auth | Refresh token |
| GET | `/auth/me` | Public | auth | Get current user |
| POST | `/auth/migrate` | Public | auth/migration | Migrate guest data |
| **Files** (6 endpoints) | | | | |
| POST | `/files/` | JWT | files | Upload file |
| GET | `/files/` | JWT | files | List files |
| GET | `/files/{file_id}` | JWT | files | Get file metadata |
| GET | `/files/{file_id}/download` | JWT | files | Download file |
| GET | `/files/{file_id}/preview` | JWT | files | Preview file |
| DELETE | `/files/{file_id}` | JWT | files | Delete file |
| **Memory** (7 endpoints) | | | | |
| POST | `/memory/add` | JWT | memory | Add memory |
| POST | `/memory/search` | JWT | memory | Search memories |
| GET | `/memory/user/{user_id}` | JWT | memory | Get user memories |
| DELETE | `/memory/{memory_id}` | JWT | memory | Delete memory |
| POST | `/memory/promote` | JWT | memory | Promote memory |
| POST | `/memory/context` | JWT | memory | Get context memories |
| GET | `/memory/health` | JWT | memory | Memory health |
| **Sandbox** (6 endpoints) | | | | |
| GET | `/sandbox/pool/status` | JWT | sandbox | Pool status |
| POST | `/sandbox/pool/cleanup` | JWT | sandbox | Pool cleanup |
| POST | `/sandbox/` | JWT | sandbox | Create sandbox |
| GET | `/sandbox/{sandbox_id}` | JWT | sandbox | Get sandbox |
| DELETE | `/sandbox/{sandbox_id}` | JWT | sandbox | Delete sandbox |
| POST | `/sandbox/{sandbox_id}/ipc` | JWT | sandbox | IPC message |
| **Cache** (9 endpoints) | | | | |
| GET | `/cache/` | JWT | cache | List cache entries |
| GET | `/cache/{key}` | JWT | cache | Get cache entry |
| POST | `/cache/` | JWT | cache | Set cache entry |
| POST | `/cache/invalidate` | JWT | cache | Invalidate entry |
| POST | `/cache/warmup` | JWT | cache | Warmup cache |
| POST | `/cache/clear` | JWT | cache | Clear all cache |
| POST | `/cache/bulk` | JWT | cache | Bulk operations |
| POST | `/cache/preload` | JWT | cache | Preload cache |
| POST | `/cache/analyze` | JWT | cache | Analyze cache |
| **Knowledge** (7 endpoints) | | | | |
| POST | `/knowledge/ingest` | JWT | knowledge | Ingest document |
| POST | `/knowledge/search` | JWT | knowledge | Search knowledge |
| GET | `/knowledge/collections` | JWT | knowledge | List collections |
| DELETE | `/knowledge/collections` | JWT | knowledge | Delete collections |
| GET | `/knowledge/skills` | JWT | knowledge | List skills |
| GET | `/knowledge/skills/{skill_id}` | JWT | knowledge | Get skill |
| GET | `/knowledge/skills/search/query` | JWT | knowledge | Search skills |
| **Versioning** (14 endpoints) | | | | |
| GET | `/versions/health` | JWT | versioning | Health check |
| GET | `/versions/statistics` | JWT | versioning | Statistics |
| POST | `/versions/compare` | JWT | versioning | Compare versions |
| POST | `/versions/` | JWT | versioning | Create version |
| GET | `/versions/` | JWT | versioning | List versions |
| GET | `/versions/{version_id}` | JWT | versioning | Get version |
| DELETE | `/versions/{version_id}` | JWT | versioning | Delete version |
| POST | `/versions/{version_id}/publish` | JWT | versioning | Publish version |
| POST | `/versions/{version_id}/deprecate` | JWT | versioning | Deprecate version |
| POST | `/versions/{version_id}/archive` | JWT | versioning | Archive version |
| GET | `/versions/templates/{id}/versions` | JWT | versioning | Template versions |
| GET | `/versions/templates/{id}/latest` | JWT | versioning | Latest version |
| POST | `/versions/templates/{id}/rollback` | JWT | versioning | Rollback |
| GET | `/versions/templates/{id}/statistics` | JWT | versioning | Template stats |
| **Autonomous Planning** (4 endpoints) | | | | |
| POST | `/claude/autonomous/plan` | JWT | autonomous | Create plan |
| GET | `/claude/autonomous/history` | JWT | autonomous | Plan history |
| GET | `/claude/autonomous/{task_id}` | JWT | autonomous | Get plan |
| POST | `/claude/autonomous/{task_id}/cancel` | JWT | autonomous | Cancel plan |
| **A2A Protocol** (14 endpoints) | | | | |
| POST | `/a2a/message` | JWT | a2a | Send message |
| GET | `/a2a/message/{message_id}` | JWT | a2a | Get message |
| GET | `/a2a/messages/pending` | JWT | a2a | Pending messages |
| GET | `/a2a/conversation/{correlation_id}` | JWT | a2a | Get conversation |
| POST | `/a2a/agents/register` | JWT | a2a | Register agent |
| DELETE | `/a2a/agents/{agent_id}` | JWT | a2a | Unregister agent |
| GET | `/a2a/agents` | JWT | a2a | List agents |
| GET | `/a2a/agents/{agent_id}` | JWT | a2a | Get agent |
| POST | `/a2a/agents/discover` | JWT | a2a | Discover agents |
| GET | `/a2a/agents/{agent_id}/capabilities` | JWT | a2a | Agent capabilities |
| POST | `/a2a/agents/{agent_id}/heartbeat` | JWT | a2a | Agent heartbeat |
| PUT | `/a2a/agents/{agent_id}/status` | JWT | a2a | Update status |
| GET | `/a2a/statistics` | JWT | a2a | A2A statistics |
| POST | `/a2a/maintenance/cleanup` | JWT | a2a | Cleanup |
| **MCP** (13 endpoints) | | | | |
| GET | `/mcp/servers` | JWT | mcp | List servers |
| POST | `/mcp/servers` | JWT | mcp | Register server |
| GET | `/mcp/servers/{server_id}` | JWT | mcp | Get server |
| DELETE | `/mcp/servers/{server_id}` | JWT | mcp | Remove server |
| POST | `/mcp/servers/{server_id}/connect` | JWT | mcp | Connect server |
| POST | `/mcp/servers/{server_id}/disconnect` | JWT | mcp | Disconnect server |
| GET | `/mcp/tools` | JWT | mcp | List tools |
| GET | `/mcp/tools/{tool_name}` | JWT | mcp | Get tool |
| POST | `/mcp/tools/execute` | JWT | mcp | Execute tool |
| GET | `/mcp/health` | JWT | mcp | Health check |
| GET | `/mcp/servers/{server_id}/health` | JWT | mcp | Server health |
| POST | `/mcp/servers/discover` | JWT | mcp | Discover servers |
| POST | `/mcp/servers/test` | JWT | mcp | Test connection |
| **Code Interpreter** (14 endpoints) | | | | |
| GET | `/code-interpreter/health` | JWT | code_interpreter | Health check |
| POST | `/code-interpreter/sessions` | JWT | code_interpreter | Create session |
| POST | `/code-interpreter/sessions/{id}/execute` | JWT | code_interpreter | Execute code |
| POST | `/code-interpreter/sessions/{id}/upload` | JWT | code_interpreter | Upload file |
| DELETE | `/code-interpreter/sessions/{id}` | JWT | code_interpreter | Delete session |
| GET | `/code-interpreter/sessions/{id}/files` | JWT | code_interpreter | List files |
| POST | `/code-interpreter/execute` | JWT | code_interpreter | Quick execute |
| GET | `/code-interpreter/sessions` | JWT | code_interpreter | List sessions |
| GET | `/code-interpreter/sessions/{id}` | JWT | code_interpreter | Get session |
| DELETE | `/code-interpreter/sessions/{id}/files/{file_id}` | JWT | code_interpreter | Delete file |
| GET | `/code-interpreter/languages` | JWT | code_interpreter | Supported languages |
| GET | `/code-interpreter/sessions/{id}/visualizations` | JWT | visualization | List visualizations |
| GET | `/code-interpreter/visualizations/{viz_id}` | JWT | visualization | Get visualization |
| POST | `/code-interpreter/visualizations/render` | JWT | visualization | Render visualization |

### System Endpoints (3 endpoints, no auth)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | None | API information |
| GET | `/health` | None | Health check (DB + Redis) |
| GET | `/ready` | None | Readiness probe |

---

## Authentication Pattern

### Two-Layer JWT Architecture

```
Layer 1: Global Auth Guard (require_auth)
├── Applied via: protected_router = APIRouter(dependencies=[Depends(require_auth)])
├── Mechanism: HTTPBearer → JWT decode → claims dict
├── No DB lookup: Fast, stateless validation
├── Returns: {user_id, role, exp, iat, ...}
└── Scope: ALL routes under protected_router

Layer 2: Per-Route User Resolution (get_current_user)
├── Applied via: Depends(get_current_user) in individual route handlers
├── Mechanism: OAuth2PasswordBearer → JWT decode → DB lookup → User model
├── DB lookup: Yes, retrieves full User record
├── Checks: is_active flag
└── Scope: Optional, only where full User model is needed
```

### Role-Based Access Control

| Role | Dependency | Access Level |
|------|-----------|-------------|
| Any authenticated | `require_auth` | Read/write own resources |
| Any authenticated | `get_current_user` | Full user model access |
| Operator + Admin | `get_current_operator_or_admin` | Operational actions |
| Admin only | `get_current_active_admin` | Administrative actions |

### Public Endpoints

Only the `/auth/*` routes and system health endpoints (`/`, `/health`, `/ready`) bypass JWT authentication.

---

## Common Patterns

### Pagination

Standard query-parameter pagination used across list endpoints:

```python
page: int = Query(default=1, ge=1)
page_size: int = Query(default=20, ge=1, le=100)
```

Response format:
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

### Error Handling

Consistent use of FastAPI `HTTPException` with standard status codes:

| Status Code | Usage |
|-------------|-------|
| 201 | Created (POST success) |
| 204 | No Content (DELETE success) |
| 400 | Bad Request (validation, invalid state) |
| 401 | Unauthorized (invalid/missing JWT) |
| 403 | Forbidden (insufficient role) |
| 404 | Not Found (resource does not exist) |
| 409 | Conflict (duplicate name/key) |
| 422 | Unprocessable Entity (Pydantic validation) |
| 500 | Internal Server Error (caught exceptions) |

Global exception handler in `main.py` catches all unhandled exceptions:
- Development: returns `detail` with error message
- Production: returns generic "Internal server error"

### Dependency Injection

The DI pattern follows a consistent structure across all modules:

1. **Repository DI**: `get_session() → Repository(session)`
2. **Service DI**: `get_agent_service() → AgentService`
3. **Auth DI**: `require_auth()` at router level, `get_current_user()` at route level

### Streaming (SSE)

Multiple modules support Server-Sent Events:
- `ag_ui/routes.py` — Primary SSE streaming via `HybridEventBridge`
- `sessions/chat.py` — Chat streaming endpoint
- `swarm/demo.py` — Swarm progress events
- `orchestrator/routes.py` — Orchestrator chat streaming

### Middleware Stack

Applied in order (outermost first):

1. **RequestIdMiddleware** (Sprint 122) — Adds `X-Request-ID` header
2. **CORSMiddleware** — Configurable origins via settings
3. **RateLimitMiddleware** (Sprint 111) — slowapi-based rate limiting
4. **Global Exception Handler** — Environment-aware error responses

---

## Known Issues

### 1. Route Prefix Collision Risk

**Severity**: Medium

The `session_resume_router` (prefix `/sessions`) and `sessions_router` (also prefix `/sessions`) create a collision risk. The workaround is registration order — `session_resume_router` MUST be registered before `sessions_router`. This is documented in `__init__.py` but is fragile.

### 2. Inconsistent Tag Naming

**Severity**: Low

Tag names mix conventions: PascalCase (`"Agents"`, `"GroupChat"`), lowercase (`"routing"`, `"patrol"`, `"devtools"`), and kebab-case (`"ag-ui"`, `"sessions-chat"`). This affects OpenAPI documentation grouping.

### 3. Large Monolithic Route Files

**Severity**: Medium

Several route files are excessively large:
- `planning/routes.py` — 46 endpoints (decomposition + plans + decisions + trial + magentic + planning adapter + multiturn)
- `groupchat/routes.py` — 42 endpoints (groups + sessions + voting + adapter + orchestrator)
- `ag_ui/routes.py` — 29 endpoints (run + threads + HITL + tool-ui + shared-state + predictive)

These could benefit from splitting into sub-route files.

### 4. Duplicate Prefix Ambiguity

**Severity**: Low

Two separate `/mcp` prefixes exist:
- `api/v1/mcp/routes.py` — MCP server management (Phase 9)
- `api/v1/claude_sdk/mcp_routes.py` — Claude SDK MCP integration (Phase 12)

Actual paths differ (`/mcp/*` vs `/claude-sdk/mcp/*`) but the conceptual overlap may confuse developers.

### 5. WebSocket Auth Gap

**Severity**: Medium

WebSocket endpoints (`groupchat/{group_id}/ws`, `concurrent/ws/{execution_id}`, `sessions/{session_id}/ws`) are not covered by the `protected_router`'s JWT dependency since WebSocket connections don't pass through standard HTTP middleware in the same way. Auth must be handled within each WebSocket handler.

### 6. Missing Response Models on Some Endpoints

**Severity**: Low

A few endpoints (e.g., some in `planning/routes.py`, `orchestrator/routes.py`) return raw dicts without explicit `response_model` declarations, reducing OpenAPI documentation quality.

---

## Phase Evolution

| Phase | Sprint | Modules Added | Endpoints Added | Key Capability |
|-------|--------|---------------|-----------------|----------------|
| 1 | 1-6 | 17 (agents, workflows, executions, ...) | ~166 | Foundation CRUD, DevTools, Dashboard |
| 2 | 7-12 | 5 (concurrent, handoff, groupchat, planning, nested) + performance | ~102 | Multi-agent orchestration |
| 8 | 37 | code_interpreter | 14 | Code execution |
| 9 | 39-41 | mcp | 13 | MCP server management |
| 10 | 42-47 | sessions (routes + chat + websocket) | 23 | Session mode, multi-turn, WebSocket |
| 12 | 48-51 | claude_sdk (7 route files) | 40 | Claude Agent SDK integration |
| 13-14 | 52-56 | hybrid (4 route files) | 23 | Hybrid MAF+Claude SDK |
| 15 | 58-60 | ag_ui | 33 | AG-UI Protocol SSE streaming |
| 18 | 70-72 | auth | 5 | JWT authentication |
| 20 | 75 | files | 6 | File attachment |
| 21 | 77-78 | sandbox | 6 | Sandbox security |
| 22 | 79-80 | memory, autonomous, decision_audit | 18 | Memory system, autonomous planning |
| 23 | 81-82 | a2a, patrol, correlation, rootcause | 34 | Observability |
| 28 | 96-98, 114-115 | orchestration (6 route files) | 29 | Three-tier intent routing |
| 29 | 100, 107 | swarm | 8 | Agent swarm visualization |
| 34 | 124, 133 | n8n, workflow graph | 10 | n8n integration, graph viz |
| 35 | 108 | orchestrator | 6 | E2E chat pipeline |
| 36 | 111 | chat_history | 3 | Chat history sync |
| 37 | 113, 115 | tasks, session_resume | 11 | Task management, session resume |
| 38 | 119 | knowledge | 7 | Knowledge management |

### Growth Trajectory

```
Phase  1:  166 endpoints  (Foundation)
Phase  2:  268 endpoints  (+102 orchestration)
Phase 10:  318 endpoints  (+50 code/mcp/sessions)
Phase 12:  358 endpoints  (+40 Claude SDK)
Phase 15:  414 endpoints  (+56 hybrid/ag-ui)
Phase 22:  438 endpoints  (+24 auth/files/memory/sandbox)
Phase 23:  472 endpoints  (+34 observability)
Phase 28:  501 endpoints  (+29 three-tier routing)
Phase 29:  509 endpoints  (+8 swarm)
Phase 38:  560 endpoints  (+51 n8n/orchestrator/tasks/knowledge)
```

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total Python files | 152 |
| Total LOC | 47,376 |
| Route modules (directories) | 48 |
| Route files | 64 |
| Registered routers | 47 |
| REST endpoints | ~560 |
| WebSocket endpoints | 3 |
| SSE streaming endpoints | 4 |
| Public endpoints | 5 (auth) + 3 (health) = 8 |
| Protected endpoints | ~555 |
| Largest module (endpoints) | planning (46) |
| Smallest module (endpoints) | dashboard (2) |
| Phases spanning | Phase 1 through Phase 38 |
| Authentication | JWT (two-layer: global guard + per-route user) |
| Rate limiting | slowapi (Sprint 111) |
| Middleware layers | 3 (RequestID, CORS, RateLimit) |
