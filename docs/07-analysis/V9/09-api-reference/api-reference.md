# IPA Platform — API Endpoint Reference (V9)

> **Generated**: 2026-03-29 | **Source**: V9 codebase analysis + AST scan of 64 route files across 48 modules
> **Base URL**: `http://localhost:8000/api/v1` | **Framework**: FastAPI 0.100+
> **Total Endpoints**: 563 REST + 3 WebSocket = **588 endpoints**

---

## Table of Contents

1. [System Endpoints (No Auth)](#system-endpoints)
2. [Domain A: Core Entity Management (588 endpoints)](#domain-a-core-entity-management)
3. [Domain B: AI Agent Operations (588 endpoints)](#domain-b-ai-agent-operations)
4. [Domain C: Real-Time & Collaboration (588 endpoints)](#domain-c-real-time--collaboration)
5. [Domain D: Orchestration & Routing (588 endpoints)](#domain-d-orchestration--routing)
6. [Domain E: Monitoring & Observability (588 endpoints)](#domain-e-monitoring--observability)
7. [Domain F: Platform Infrastructure (588 endpoints)](#domain-f-platform-infrastructure)
8. [Authentication](#authentication)
9. [Common Patterns](#common-patterns)
10. [Error Codes](#error-codes)

---

## Authentication Overview

| Layer | Dependency | DB Lookup | Returns | Scope |
|-------|-----------|-----------|---------|-------|
| Global Guard | `require_auth` (core/auth.py) | No | JWT claims `dict` | All protected routes |
| Per-Route | `get_current_user` (dependencies.py) | Yes | `User` ORM model | Routes needing full user |
| Admin | `get_current_active_admin` | Yes | `User` (role=admin) | Admin-only routes |
| Operator | `get_current_operator_or_admin` | Yes | `User` (role in admin, operator) | Operational routes |

**Public endpoints**: Only `/auth/*` and system health (`/`, `/health`, `/ready`).

---

## System Endpoints

> 3 endpoints — No authentication required. Mounted directly on `main.py`, NOT under `/api/v1`.

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/` | `root` | None | API information and version |
| 2 | GET | `/health` | `health_check` | None | Health check (DB + Redis status) |
| 3 | GET | `/ready` | `readiness_check` | None | K8s / Azure readiness probe |

---

## Domain A: Core Entity Management

> 588 endpoints across 9 modules — CRUD for primary platform resources.

### A1. Agents (`/agents`) — 6 endpoints

**Module**: `api/v1/agents/routes.py` | **Tags**: `Agents`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/agents/` | `create_agent` | JWT | Create new agent definition |
| 2 | GET | `/agents/` | `list_agents` | JWT | List agents (paginated) |
| 3 | GET | `/agents/{agent_id}` | `get_agent` | JWT | Get agent by ID |
| 4 | PUT | `/agents/{agent_id}` | `update_agent` | JWT | Update agent configuration |
| 5 | DELETE | `/agents/{agent_id}` | `delete_agent` | JWT | Delete agent |
| 6 | POST | `/agents/{agent_id}/run` | `run_agent` | JWT | Run agent with a message |

### A2. Workflows (`/workflows`) — 588 endpoints

**Module**: `api/v1/workflows/routes.py`, `graph_routes.py` | **Tags**: `Workflows`, `Workflow Graph`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/workflows/` | `create_workflow` | JWT | Create workflow |
| 2 | GET | `/workflows/` | `list_workflows` | JWT | List workflows (paginated) |
| 3 | GET | `/workflows/{workflow_id}` | `get_workflow` | JWT | Get workflow by ID |
| 4 | PUT | `/workflows/{workflow_id}` | `update_workflow` | JWT | Update workflow |
| 5 | DELETE | `/workflows/{workflow_id}` | `delete_workflow` | JWT | Delete workflow |
| 6 | POST | `/workflows/{workflow_id}/execute` | `execute_workflow` | JWT | Execute workflow |
| 7 | POST | `/workflows/{workflow_id}/validate` | `validate_workflow` | JWT | Validate workflow definition |
| 8 | POST | `/workflows/{workflow_id}/activate` | `activate_workflow` | JWT | Activate workflow |
| 9 | POST | `/workflows/{workflow_id}/deactivate` | `deactivate_workflow` | JWT | Deactivate workflow |
| 10 | GET | `/workflows/{workflow_id}/graph` | `get_workflow_graph` | JWT | Get workflow graph (React Flow) |
| 11 | PUT | `/workflows/{workflow_id}/graph` | `update_workflow_graph` | JWT | Update workflow graph |
| 12 | POST | `/workflows/{workflow_id}/graph/layout` | `auto_layout_graph` | JWT | Auto-layout graph |

### A3. Executions (`/executions`) — 588 endpoints

**Module**: `api/v1/executions/routes.py` | **Tags**: `Executions`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/executions/` | `list_executions` | JWT | List executions (paginated, filtered) |
| 2 | POST | `/executions/` | `create_execution` | JWT | Create execution |
| 3 | GET | `/executions/{execution_id}` | `get_execution` | JWT | Get execution detail |
| 4 | POST | `/executions/{execution_id}/cancel` | `cancel_execution` | JWT | Cancel running execution |
| 5 | GET | `/executions/{execution_id}/transitions` | `get_transitions` | JWT | Get valid state transitions |
| 6 | GET | `/executions/status/running` | `list_running` | JWT | List currently running executions |
| 7 | GET | `/executions/status/recent` | `list_recent` | JWT | List recent executions |
| 8 | GET | `/executions/workflows/{workflow_id}/stats` | `get_workflow_stats` | JWT | Workflow execution statistics |
| 9 | POST | `/executions/{execution_id}/resume` | `resume_execution` | JWT | Resume paused execution |
| 10 | GET | `/executions/{execution_id}/resume-status` | `get_resume_status` | JWT | Get resume status |
| 11 | POST | `/executions/{execution_id}/shutdown` | `shutdown_execution` | JWT | Graceful shutdown |

### A4. Checkpoints (`/checkpoints`) — 10 endpoints

**Module**: `api/v1/checkpoints/routes.py` | **Tags**: `Checkpoints`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/checkpoints/pending` | `list_pending` | JWT | List pending checkpoints |
| 2 | GET | `/checkpoints/{checkpoint_id}` | `get_checkpoint` | JWT | Get checkpoint detail |
| 3 | POST | `/checkpoints/{checkpoint_id}/approve` | `approve_checkpoint` | JWT | Approve checkpoint |
| 4 | POST | `/checkpoints/{checkpoint_id}/reject` | `reject_checkpoint` | JWT | Reject checkpoint |
| 5 | GET | `/checkpoints/execution/{execution_id}` | `list_by_execution` | JWT | List checkpoints by execution |
| 6 | GET | `/checkpoints/stats` | `get_stats` | JWT | Checkpoint statistics |
| 7 | POST | `/checkpoints/` | `create_checkpoint` | JWT | Create checkpoint |
| 8 | POST | `/checkpoints/expire` | `expire_checkpoints` | JWT | Expire old checkpoints |
| 9 | GET | `/checkpoints/approval/pending` | `list_pending_approvals` | JWT | List pending approvals |
| 10 | POST | `/checkpoints/approval/{executor_name}/respond` | `respond_to_approval` | JWT | Respond to approval request |

### A5. Templates (`/templates`) — 588 endpoints

**Module**: `api/v1/templates/routes.py` | **Tags**: `templates`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/templates/health` | `health_check` | JWT | Health check |
| 2 | GET | `/templates/statistics/summary` | `get_statistics` | JWT | Statistics summary |
| 3 | GET | `/templates/categories/list` | `list_categories` | JWT | List categories |
| 4 | GET | `/templates/popular/list` | `get_popular_templates` | JWT | Popular templates |
| 5 | GET | `/templates/top-rated/list` | `get_top_rated_templates` | JWT | Top rated templates |
| 6 | POST | `/templates/search` | `search_templates` | JWT | Search templates |
| 7 | GET | `/templates/` | `list_templates` | JWT | List all templates (paginated) |
| 8 | GET | `/templates/similar/{template_id}` | `get_similar_templates` | JWT | Find similar templates |
| 9 | GET | `/templates/{template_id}` | `get_template` | JWT | Get template detail |
| 10 | POST | `/templates/{template_id}/instantiate` | `instantiate_template` | JWT | Instantiate template |
| 11 | POST | `/templates/{template_id}/rate` | `rate_template` | JWT | Rate template |

### A6. Triggers (`/triggers`) — 8 endpoints

**Module**: `api/v1/triggers/routes.py` | **Tags**: `Triggers`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/triggers/webhook/{workflow_id}` | `trigger_webhook` | JWT | Trigger webhook for workflow |
| 2 | GET | `/triggers/webhooks` | `list_webhooks` | JWT | List all webhooks |
| 3 | POST | `/triggers/webhooks` | `create_webhook` | JWT | Create webhook trigger |
| 4 | GET | `/triggers/webhooks/{workflow_id}` | `get_webhook` | JWT | Get webhook by workflow |
| 5 | PUT | `/triggers/webhooks/{workflow_id}` | `update_webhook` | JWT | Update webhook |
| 6 | DELETE | `/triggers/webhooks/{workflow_id}` | `delete_webhook` | JWT | Delete webhook |
| 7 | POST | `/triggers/webhooks/test-signature` | `test_signature` | JWT | Test webhook signature |
| 8 | GET | `/triggers/health` | `health_check` | JWT | Health check |

### A7. Connectors (`/connectors`) — 9 endpoints

**Module**: `api/v1/connectors/routes.py` | **Tags**: `Connectors`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/connectors/` | `list_connectors` | JWT | List all connectors |
| 2 | GET | `/connectors/types` | `list_types` | JWT | List connector types |
| 3 | GET | `/connectors/health` | `health_check` | JWT | Connectors health check |
| 4 | GET | `/connectors/{name}` | `get_connector` | JWT | Get connector by name |
| 5 | GET | `/connectors/{name}/status` | `get_status` | JWT | Get connector status |
| 6 | GET | `/connectors/{name}/health` | `get_health` | JWT | Individual connector health |
| 7 | POST | `/connectors/{name}/execute` | `execute_connector` | JWT | Execute connector action |
| 8 | POST | `/connectors/{name}/connect` | `connect_connector` | JWT | Connect to external system |
| 9 | POST | `/connectors/{name}/disconnect` | `disconnect_connector` | JWT | Disconnect connector |

### A8. Tasks (`/tasks`) — 9 endpoints

**Module**: `api/v1/tasks/routes.py` | **Tags**: `tasks`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/tasks/` | `create_task` | JWT | Create task |
| 2 | GET | `/tasks/` | `list_tasks` | JWT | List tasks (filtered) |
| 3 | GET | `/tasks/{task_id}` | `get_task` | JWT | Get task detail |
| 4 | PUT | `/tasks/{task_id}` | `update_task` | JWT | Update task |
| 5 | DELETE | `/tasks/{task_id}` | `delete_task` | JWT | Delete task |
| 6 | POST | `/tasks/{task_id}/start` | `start_task` | JWT | Start task execution |
| 7 | POST | `/tasks/{task_id}/complete` | `complete_task` | JWT | Mark task complete |
| 8 | POST | `/tasks/{task_id}/fail` | `fail_task` | JWT | Mark task failed |
| 9 | POST | `/tasks/{task_id}/progress` | `update_progress` | JWT | Update task progress |

### A9. Routing (`/routing`) — 588 endpoints

**Module**: `api/v1/routing/routes.py` | **Tags**: `routing`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/routing/route` | `route_to_scenario` | JWT | Route request to scenario |
| 2 | POST | `/routing/relations` | `create_relation` | JWT | Create execution relation |
| 3 | GET | `/routing/executions/{execution_id}/relations` | `get_execution_relations` | JWT | Get execution relations |
| 4 | GET | `/routing/executions/{execution_id}/chain` | `get_execution_chain` | JWT | Get execution chain |
| 5 | GET | `/routing/relations/{relation_id}` | `get_relation` | JWT | Get relation detail |
| 6 | DELETE | `/routing/relations/{relation_id}` | `delete_relation` | JWT | Delete relation |
| 7 | GET | `/routing/scenarios` | `list_scenarios` | JWT | List routing scenarios |
| 8 | GET | `/routing/scenarios/{scenario_name}` | `get_scenario_config` | JWT | Get scenario config |
| 9 | PUT | `/routing/scenarios/{scenario_name}` | `configure_scenario` | JWT | Configure scenario |
| 10 | POST | `/routing/scenarios/{scenario_name}/workflow` | `set_default_workflow` | JWT | Set default workflow |
| 11 | GET | `/routing/relation-types` | `list_relation_types` | JWT | List relation types |
| 12 | GET | `/routing/statistics` | `get_statistics` | JWT | Routing statistics |
| 13 | DELETE | `/routing/relations` | `clear_all_relations` | JWT | Clear all relations |
| 14 | GET | `/routing/health` | `health_check` | JWT | Health check |

---

## Domain B: AI Agent Operations

> 588 endpoints across 17 route files — Claude SDK, hybrid operations, planning, groupchat, handoff, concurrent, and nested workflows.

### B1. Claude SDK Core (`/claude-sdk`) — 6 endpoints

**Module**: `api/v1/claude_sdk/routes.py` | **Tags**: `Claude SDK`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/claude-sdk/query` | `execute_query` | JWT | Execute Claude SDK query |
| 2 | POST | `/claude-sdk/sessions` | `create_session` | JWT | Create SDK session |
| 3 | POST | `/claude-sdk/sessions/{session_id}/query` | `session_query` | JWT | Query within session |
| 4 | DELETE | `/claude-sdk/sessions/{session_id}` | `close_session` | JWT | Close session |
| 5 | GET | `/claude-sdk/sessions/{session_id}/history` | `get_session_history` | JWT | Get session history |
| 6 | GET | `/claude-sdk/health` | `health_check` | JWT | SDK health check |

### B2. Claude SDK Autonomous (`/claude-sdk/autonomous`) — 7 endpoints

**Module**: `api/v1/claude_sdk/autonomous_routes.py` | **Tags**: `Claude SDK Autonomous`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/claude-sdk/autonomous/plan` | `generate_plan` | JWT | Generate autonomous plan |
| 2 | GET | `/claude-sdk/autonomous/{plan_id}` | `get_plan` | JWT | Get plan detail |
| 3 | POST | `/claude-sdk/autonomous/{plan_id}/execute` | `execute_plan` | JWT | Execute plan |
| 4 | DELETE | `/claude-sdk/autonomous/{plan_id}` | `delete_plan` | JWT | Delete plan |
| 5 | GET | `/claude-sdk/autonomous/` | `list_plans` | JWT | List all plans |
| 6 | POST | `/claude-sdk/autonomous/estimate` | `estimate_resources` | JWT | Estimate resource usage |
| 7 | POST | `/claude-sdk/autonomous/{plan_id}/verify` | `verify_plan` | JWT | Verify plan feasibility |

### B3. Claude SDK Hooks (`/claude-sdk/hooks`) — 6 endpoints

**Module**: `api/v1/claude_sdk/hooks_routes.py` | **Tags**: `Claude SDK Hooks`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/claude-sdk/hooks` | `list_hooks` | JWT | List registered hooks |
| 2 | GET | `/claude-sdk/hooks/{hook_id}` | `get_hook` | JWT | Get hook detail |
| 3 | POST | `/claude-sdk/hooks/register` | `register_hook` | JWT | Register new hook |
| 4 | DELETE | `/claude-sdk/hooks/{hook_id}` | `remove_hook` | JWT | Remove hook |
| 5 | PUT | `/claude-sdk/hooks/{hook_id}/enable` | `enable_hook` | JWT | Enable hook |
| 6 | PUT | `/claude-sdk/hooks/{hook_id}/disable` | `disable_hook` | JWT | Disable hook |

### B4. Claude SDK Hybrid (`/claude-sdk/hybrid`) — 5 endpoints

**Module**: `api/v1/claude_sdk/hybrid_routes.py` | **Tags**: `Claude SDK Hybrid`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/claude-sdk/hybrid/execute` | `execute_hybrid_task` | JWT | Execute hybrid MAF+SDK task |
| 2 | POST | `/claude-sdk/hybrid/analyze` | `analyze_task` | JWT | Analyze task for routing |
| 3 | GET | `/claude-sdk/hybrid/metrics` | `get_metrics` | JWT | Get hybrid metrics |
| 4 | POST | `/claude-sdk/hybrid/context/sync` | `sync_context` | JWT | Sync context between engines |
| 5 | GET | `/claude-sdk/hybrid/capabilities` | `list_capabilities` | JWT | List hybrid capabilities |

### B5. Claude SDK Intent (`/claude-sdk/intent`) — 6 endpoints

**Module**: `api/v1/claude_sdk/intent_routes.py` | **Tags**: `Intent Router`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/claude-sdk/intent/classify` | `classify_intent` | JWT | Classify user intent |
| 2 | POST | `/claude-sdk/intent/analyze-complexity` | `analyze_complexity` | JWT | Analyze task complexity |
| 3 | POST | `/claude-sdk/intent/detect-multi-agent` | `detect_multi_agent` | JWT | Detect multi-agent need |
| 4 | GET | `/claude-sdk/intent/classifiers` | `list_classifiers` | JWT | List available classifiers |
| 5 | GET | `/claude-sdk/intent/stats` | `get_stats` | JWT | Intent classification stats |
| 6 | PUT | `/claude-sdk/intent/config` | `update_config` | JWT | Update intent config |

### B6. Claude SDK MCP (`/claude-sdk/mcp`) — 6 endpoints

**Module**: `api/v1/claude_sdk/mcp_routes.py` | **Tags**: `Claude SDK MCP`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/claude-sdk/mcp/servers` | `list_mcp_servers` | JWT | List MCP servers |
| 2 | POST | `/claude-sdk/mcp/servers/connect` | `connect_mcp_server` | JWT | Connect to MCP server |
| 3 | POST | `/claude-sdk/mcp/servers/{server_id}/disconnect` | `disconnect_mcp_server` | JWT | Disconnect MCP server |
| 4 | GET | `/claude-sdk/mcp/servers/{server_id}/health` | `check_mcp_server_health` | JWT | Check server health |
| 5 | GET | `/claude-sdk/mcp/tools` | `list_mcp_tools` | JWT | List MCP tools |
| 6 | POST | `/claude-sdk/mcp/tools/execute` | `execute_mcp_tool` | JWT | Execute MCP tool |

### B7. Claude SDK Tools (`/claude-sdk/tools`) — 4 endpoints

**Module**: `api/v1/claude_sdk/tools_routes.py` | **Tags**: `Claude SDK Tools`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/claude-sdk/tools` | `list_tools` | JWT | List available tools |
| 2 | GET | `/claude-sdk/tools/{name}` | `get_tool` | JWT | Get tool by name |
| 3 | POST | `/claude-sdk/tools/execute` | `execute_tool_endpoint` | JWT | Execute tool |
| 4 | POST | `/claude-sdk/tools/validate` | `validate_tool_parameters` | JWT | Validate tool parameters |

### B8. Hybrid MAF+SDK Context (`/hybrid/context`) — 5 endpoints

**Module**: `api/v1/hybrid/context_routes.py` | **Tags**: `Hybrid Context`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/hybrid/context` | `list_contexts` | JWT | List all contexts |
| 2 | GET | `/hybrid/context/{session_id}` | `get_context` | JWT | Get session context |
| 3 | GET | `/hybrid/context/{session_id}/status` | `get_context_status` | JWT | Get context sync status |
| 4 | POST | `/hybrid/context/sync` | `sync_context` | JWT | Sync context between engines |
| 5 | POST | `/hybrid/context/merge` | `merge_contexts` | JWT | Merge multiple contexts |

### B9. Hybrid MAF+SDK Core (`/hybrid`) — 4 endpoints

**Module**: `api/v1/hybrid/core_routes.py` | **Tags**: `Hybrid`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/hybrid/analyze` | `analyze_task` | JWT | Analyze task for hybrid routing |
| 2 | POST | `/hybrid/execute` | `execute_hybrid` | JWT | Execute hybrid operation |
| 3 | GET | `/hybrid/metrics` | `get_metrics` | JWT | Get hybrid engine metrics |
| 4 | GET | `/hybrid/status` | `get_status` | JWT | Get hybrid system status |

### B10. Hybrid MAF+SDK Risk (`/hybrid/risk`) — 7 endpoints

**Module**: `api/v1/hybrid/risk_routes.py` | **Tags**: `Hybrid Risk`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/hybrid/risk/assess` | `assess_risk` | JWT | Assess operation risk |
| 2 | POST | `/hybrid/risk/assess-batch` | `assess_batch` | JWT | Batch risk assessment |
| 3 | GET | `/hybrid/risk/session/{session_id}` | `get_session_risk` | JWT | Get session risk history |
| 4 | GET | `/hybrid/risk/metrics` | `get_metrics` | JWT | Get risk metrics |
| 5 | DELETE | `/hybrid/risk/session/{session_id}/history` | `clear_history` | JWT | Clear risk history |
| 6 | POST | `/hybrid/risk/metrics/reset` | `reset_metrics` | JWT | Reset risk metrics |
| 7 | GET | `/hybrid/risk/config` | `get_config` | JWT | Get risk configuration |

### B11. Hybrid MAF+SDK Switch (`/hybrid/switch`) — 7 endpoints

**Module**: `api/v1/hybrid/switch_routes.py` | **Tags**: `Hybrid Switch`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/hybrid/switch` | `switch_mode` | JWT | Switch execution engine mode |
| 2 | GET | `/hybrid/switch/status/{session_id}` | `get_switch_status` | JWT | Get switch status |
| 3 | POST | `/hybrid/switch/rollback` | `rollback_switch` | JWT | Rollback mode switch |
| 4 | GET | `/hybrid/switch/history/{session_id}` | `get_switch_history` | JWT | Get switch history |
| 5 | GET | `/hybrid/switch/checkpoints/{session_id}` | `get_checkpoints` | JWT | Get switch checkpoints |
| 6 | DELETE | `/hybrid/switch/checkpoints/{session_id}/{checkpoint_id}` | `delete_checkpoint` | JWT | Delete checkpoint |
| 7 | DELETE | `/hybrid/switch/history/{session_id}` | `clear_history` | JWT | Clear switch history |

### B12. Planning (`/planning`) — 588 endpoints

**Module**: `api/v1/planning/routes.py` | **Tags**: `Planning`

#### B12a. Task Decomposition & Plans

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/planning/decompose` | `decompose_task` | JWT | Decompose task into subtasks |
| 2 | POST | `/planning/decompose/{task_id}/refine` | `refine_decomposition` | JWT | Refine decomposition |
| 3 | POST | `/planning/plans` | `create_plan` | JWT | Create execution plan |
| 4 | GET | `/planning/plans/{plan_id}` | `get_plan` | JWT | Get plan detail |
| 5 | GET | `/planning/plans/{plan_id}/status` | `get_plan_execution_status` | JWT | Get plan execution status |
| 6 | POST | `/planning/plans/{plan_id}/approve` | `approve_plan` | JWT | Approve plan |
| 7 | POST | `/planning/plans/{plan_id}/execute` | `execute_plan` | JWT | Execute plan |
| 8 | POST | `/planning/plans/{plan_id}/pause` | `pause_plan` | JWT | Pause plan execution |
| 9 | POST | `/planning/plans/{plan_id}/adjustments/approve` | `approve_adjustment` | JWT | Approve plan adjustment |
| 10 | GET | `/planning/plans` | `list_plans` | JWT | List all plans |
| 11 | DELETE | `/planning/plans/{plan_id}` | `delete_plan` | JWT | Delete plan |

#### B12b. Decisions

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 12 | POST | `/planning/decisions` | `make_decision` | JWT | Create decision |
| 13 | GET | `/planning/decisions/{decision_id}/explain` | `explain_decision` | JWT | Explain decision rationale |
| 14 | POST | `/planning/decisions/{decision_id}/approve` | `approve_decision` | JWT | Approve decision |
| 15 | POST | `/planning/decisions/{decision_id}/reject` | `reject_decision` | JWT | Reject decision |
| 16 | GET | `/planning/decisions` | `list_decisions` | JWT | List decisions |
| 17 | GET | `/planning/decisions/rules` | `list_decision_rules` | JWT | List decision rules |

#### B12c. Trial Execution

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 18 | POST | `/planning/trial` | `execute_with_trial` | JWT | Execute with trial mode |
| 19 | GET | `/planning/trial/insights` | `get_learning_insights` | JWT | Get trial insights |
| 20 | GET | `/planning/trial/recommendations` | `get_recommendations` | JWT | Get recommendations |
| 21 | GET | `/planning/trial/statistics` | `get_trial_statistics` | JWT | Trial statistics |
| 22 | GET | `/planning/trial/history` | `get_trial_history` | JWT | Trial history |
| 23 | DELETE | `/planning/trial/history` | `clear_trial_history` | JWT | Clear trial history |

#### B12d. Magentic Adapter

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 24 | POST | `/planning/magentic/adapter` | `create_magentic_adapter` | JWT | Create Magentic adapter |
| 25 | GET | `/planning/magentic/adapter/{adapter_id}` | `get_magentic_adapter_state` | JWT | Get adapter state |
| 26 | DELETE | `/planning/magentic/adapter/{adapter_id}` | `delete_magentic_adapter` | JWT | Delete adapter |
| 27 | POST | `/planning/magentic/adapter/{adapter_id}/run` | `run_magentic_workflow` | JWT | Run Magentic workflow |
| 28 | POST | `/planning/magentic/adapter/{adapter_id}/intervention` | `respond_to_intervention` | JWT | Respond to intervention |
| 29 | GET | `/planning/magentic/adapters` | `list_magentic_adapters` | JWT | List all Magentic adapters |
| 30 | GET | `/planning/magentic/adapter/{adapter_id}/ledger` | `get_magentic_ledger` | JWT | Get orchestration ledger |
| 31 | POST | `/planning/magentic/adapter/{adapter_id}/reset` | `reset_magentic_adapter` | JWT | Reset adapter state |

#### B12e. Planning Adapter

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 32 | POST | `/planning/adapter/planning` | `create_planning_adapter` | JWT | Create planning adapter |
| 33 | GET | `/planning/adapter/planning/{adapter_id}` | `get_planning_adapter` | JWT | Get planning adapter |
| 34 | POST | `/planning/adapter/planning/{adapter_id}/run` | `run_planning_adapter` | JWT | Run planning adapter |
| 35 | DELETE | `/planning/adapter/planning/{adapter_id}` | `delete_planning_adapter` | JWT | Delete planning adapter |
| 36 | GET | `/planning/adapter/planning` | `list_planning_adapters` | JWT | List planning adapters |

#### B12f. Multi-Turn Adapter

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 37 | POST | `/planning/adapter/multiturn` | `create_multiturn_adapter` | JWT | Create multi-turn session |
| 38 | GET | `/planning/adapter/multiturn/{session_id}` | `get_multiturn_adapter` | JWT | Get session detail |
| 39 | POST | `/planning/adapter/multiturn/{session_id}/turn` | `add_multiturn_turn` | JWT | Submit turn |
| 40 | GET | `/planning/adapter/multiturn/{session_id}/history` | `get_multiturn_history` | JWT | Get turn history |
| 41 | POST | `/planning/adapter/multiturn/{session_id}/checkpoint` | `save_multiturn_checkpoint` | JWT | Save checkpoint |
| 42 | POST | `/planning/adapter/multiturn/{session_id}/restore` | `restore_multiturn_checkpoint` | JWT | Restore checkpoint |
| 43 | POST | `/planning/adapter/multiturn/{session_id}/complete` | `complete_multiturn_session` | JWT | Complete session |
| 44 | DELETE | `/planning/adapter/multiturn/{session_id}` | `delete_multiturn_adapter` | JWT | Delete session |
| 45 | GET | `/planning/adapter/multiturn` | `list_multiturn_adapters` | JWT | List sessions |

#### B12g. Health

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 46 | GET | `/planning/health` | `health_check` | JWT | Planning health check |

### B13. GroupChat (`/groupchat`) — 588 endpoints

**Module**: `api/v1/groupchat/routes.py` | **Tags**: `GroupChat`

#### B13a. Group Management

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/groupchat/` | `create_group_chat` | JWT | Create group chat |
| 2 | GET | `/groupchat/` | `list_group_chats` | JWT | List group chats |
| 3 | GET | `/groupchat/{group_id}` | `get_group_chat` | JWT | Get group chat |
| 4 | PATCH | `/groupchat/{group_id}/config` | `update_group_config` | JWT | Update group config |
| 5 | POST | `/groupchat/{group_id}/agents/{agent_id}` | `add_agent_to_group` | JWT | Add agent to group |
| 6 | DELETE | `/groupchat/{group_id}/agents/{agent_id}` | `remove_agent_from_group` | JWT | Remove agent from group |
| 7 | POST | `/groupchat/{group_id}/start` | `start_conversation` | JWT | Start conversation |
| 8 | POST | `/groupchat/{group_id}/message` | `send_message` | JWT | Send message |
| 9 | GET | `/groupchat/{group_id}/messages` | `get_messages` | JWT | Get messages |
| 10 | GET | `/groupchat/{group_id}/transcript` | `get_transcript` | JWT | Get full transcript |
| 11 | GET | `/groupchat/{group_id}/summary` | `get_summary` | JWT | Get conversation summary |
| 12 | POST | `/groupchat/{group_id}/terminate` | `terminate_group_chat` | JWT | Terminate conversation |
| 13 | DELETE | `/groupchat/{group_id}` | `delete_group_chat` | JWT | Delete group chat |
| 14 | WS | `/groupchat/{group_id}/ws` | `websocket_endpoint` | — | Real-time WebSocket |

#### B13b. Sessions

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 15 | POST | `/groupchat/sessions/` | `create_session` | JWT | Create session |
| 16 | GET | `/groupchat/sessions/` | `list_sessions` | JWT | List sessions |
| 17 | GET | `/groupchat/sessions/{session_id}` | `get_session` | JWT | Get session |
| 18 | POST | `/groupchat/sessions/{session_id}/turns` | `execute_turn` | JWT | Execute turn |
| 19 | GET | `/groupchat/sessions/{session_id}/history` | `get_session_history` | JWT | Session history |
| 20 | PATCH | `/groupchat/sessions/{session_id}/context` | `update_session_context` | JWT | Update context |
| 21 | POST | `/groupchat/sessions/{session_id}/close` | `close_session` | JWT | Close session |
| 22 | DELETE | `/groupchat/sessions/{session_id}` | `delete_session` | JWT | Delete session |

#### B13c. Voting

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 23 | POST | `/groupchat/voting/` | `create_voting_session` | JWT | Create voting session |
| 24 | GET | `/groupchat/voting/` | `list_voting_sessions` | JWT | List voting sessions |
| 25 | GET | `/groupchat/voting/{session_id}` | `get_voting_session` | JWT | Get voting session |
| 26 | POST | `/groupchat/voting/{session_id}/vote` | `cast_vote` | JWT | Cast vote |
| 27 | PATCH | `/groupchat/voting/{session_id}/vote/{voter_id}` | `change_vote` | JWT | Change vote |
| 28 | DELETE | `/groupchat/voting/{session_id}/vote/{voter_id}` | `withdraw_vote` | JWT | Withdraw vote |
| 29 | GET | `/groupchat/voting/{session_id}/votes` | `get_votes` | JWT | List votes |
| 30 | POST | `/groupchat/voting/{session_id}/calculate` | `calculate_voting_result` | JWT | Calculate result |
| 31 | GET | `/groupchat/voting/{session_id}/statistics` | `get_voting_statistics` | JWT | Voting statistics |
| 32 | POST | `/groupchat/voting/{session_id}/close` | `close_voting_session` | JWT | Close voting |
| 33 | POST | `/groupchat/voting/{session_id}/cancel` | `cancel_voting_session` | JWT | Cancel voting |
| 34 | DELETE | `/groupchat/voting/{session_id}` | `delete_voting_session` | JWT | Delete voting |

#### B13d. Adapter (MAF GroupChat)

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 35 | POST | `/groupchat/adapter/` | `create_groupchat_adapter` | JWT | Create adapter |
| 36 | GET | `/groupchat/adapter/` | `list_groupchat_adapters` | JWT | List adapters |
| 37 | GET | `/groupchat/adapter/{adapter_id}` | `get_groupchat_adapter` | JWT | Get adapter |
| 38 | POST | `/groupchat/adapter/{adapter_id}/run` | `run_groupchat_adapter` | JWT | Run adapter |
| 39 | POST | `/groupchat/adapter/{adapter_id}/participants` | `add_adapter_participant` | JWT | Add participant |
| 40 | DELETE | `/groupchat/adapter/{adapter_id}/participants/{name}` | `remove_adapter_participant` | JWT | Remove participant |
| 41 | DELETE | `/groupchat/adapter/{adapter_id}` | `delete_groupchat_adapter` | JWT | Delete adapter |

#### B13e. Orchestrator

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 42 | POST | `/groupchat/orchestrator/select` | `orchestrator_select_speaker` | JWT | Manager speaker selection |

### B14. Handoff (`/handoff`) — 588 endpoints

**Module**: `api/v1/handoff/routes.py` | **Tags**: `Handoff`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/handoff/trigger` | `trigger_handoff` | JWT | Trigger agent handoff |
| 2 | GET | `/handoff/{handoff_id}/status` | `get_handoff_status` | JWT | Get handoff status |
| 3 | POST | `/handoff/{handoff_id}/cancel` | `cancel_handoff` | JWT | Cancel handoff |
| 4 | GET | `/handoff/history` | `get_handoff_history` | JWT | Get handoff history |
| 5 | POST | `/handoff/capability/match` | `match_capability` | JWT | Match agent capability |
| 6 | GET | `/handoff/agents/{agent_id}/capabilities` | `get_capabilities` | JWT | Get agent capabilities |
| 7 | POST | `/handoff/agents/{agent_id}/capabilities` | `register_capabilities` | JWT | Register capabilities |
| 8 | DELETE | `/handoff/agents/{agent_id}/capabilities/{capability_name}` | `remove_capability` | JWT | Remove capability |
| 9 | GET | `/handoff/hitl/sessions` | `list_hitl_sessions` | JWT | List HITL sessions |
| 10 | GET | `/handoff/hitl/sessions/{session_id}` | `get_hitl_session` | JWT | Get HITL session |
| 11 | GET | `/handoff/hitl/pending` | `list_pending_hitl` | JWT | List pending HITL requests |
| 12 | POST | `/handoff/hitl/submit` | `submit_hitl_response` | JWT | Submit HITL response |
| 13 | POST | `/handoff/hitl/sessions/{session_id}/cancel` | `cancel_hitl_session` | JWT | Cancel HITL session |
| 14 | POST | `/handoff/hitl/sessions/{session_id}/escalate` | `escalate_hitl_session` | JWT | Escalate HITL session |

### B15. Concurrent (`/concurrent`) — 588 endpoints (13 REST + 2 WS)

**Module**: `api/v1/concurrent/routes.py`, `websocket.py` | **Tags**: `concurrent`, `concurrent-websocket`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/concurrent/execute` | `execute_concurrent` | JWT | Execute concurrent (fork-join) |
| 2 | GET | `/concurrent/{execution_id}/status` | `get_execution_status` | JWT | Get execution status |
| 3 | GET | `/concurrent/{execution_id}/branches` | `get_branches` | JWT | List branches |
| 4 | GET | `/concurrent/{execution_id}/branches/{branch_id}` | `get_branch` | JWT | Get branch detail |
| 5 | POST | `/concurrent/{execution_id}/cancel` | `cancel_execution` | JWT | Cancel execution |
| 6 | POST | `/concurrent/{execution_id}/branches/{branch_id}/cancel` | `cancel_branch` | JWT | Cancel specific branch |
| 7 | GET | `/concurrent/stats` | `get_stats` | JWT | Concurrent statistics |
| 8 | GET | `/concurrent/health` | `health_check` | JWT | Health check |
| 9 | POST | `/concurrent/v2/execute` | `execute_v2` | JWT | V2 concurrent execute |
| 10 | GET | `/concurrent/v2/{execution_id}` | `get_v2_execution` | JWT | V2 execution detail |
| 11 | GET | `/concurrent/v2/stats` | `get_v2_stats` | JWT | V2 statistics |
| 12 | GET | `/concurrent/v2/health` | `health_v2` | JWT | V2 health check |
| 13 | GET | `/concurrent/v2/executions` | `list_v2_executions` | JWT | V2 list executions |
| 14 | WS | `/concurrent/ws/{execution_id}` | `websocket_execution` | — | Execution WebSocket |
| 15 | WS | `/concurrent/ws` | `websocket_global` | — | Global WebSocket |

### B16. Nested (`/nested`) — 588 endpoints

**Module**: `api/v1/nested/routes.py` | **Tags**: `Nested`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/nested/configs` | `create_config` | JWT | Create nested workflow config |
| 2 | GET | `/nested/configs` | `list_configs` | JWT | List configs |
| 3 | GET | `/nested/configs/{config_id}` | `get_config` | JWT | Get config detail |
| 4 | DELETE | `/nested/configs/{config_id}` | `delete_config` | JWT | Delete config |
| 5 | POST | `/nested/sub-workflows/execute` | `execute_sub_workflow` | JWT | Execute sub-workflow |
| 6 | POST | `/nested/sub-workflows/batch` | `batch_execute` | JWT | Batch execute sub-workflows |
| 7 | GET | `/nested/sub-workflows/{execution_id}/status` | `get_sub_workflow_status` | JWT | Get sub-workflow status |
| 8 | POST | `/nested/sub-workflows/{execution_id}/cancel` | `cancel_sub_workflow` | JWT | Cancel sub-workflow |
| 9 | POST | `/nested/recursive/execute` | `execute_recursive` | JWT | Execute recursive workflow |
| 10 | GET | `/nested/recursive/{execution_id}/status` | `get_recursive_status` | JWT | Get recursive status |
| 11 | POST | `/nested/compositions` | `create_composition` | JWT | Create workflow composition |
| 12 | POST | `/nested/compositions/execute` | `execute_composition` | JWT | Execute composition |
| 13 | POST | `/nested/context/propagate` | `propagate_context` | JWT | Propagate context |
| 14 | GET | `/nested/context/flow/{workflow_id}` | `get_context_flow` | JWT | Get context flow |
| 15 | GET | `/nested/context/tracker/stats` | `get_tracker_stats` | JWT | Context tracker stats |
| 16 | GET | `/nested/stats` | `get_stats` | JWT | Nested statistics |

---

## Domain C: Real-Time & Collaboration

> 588 endpoints across 8 route files — Sessions, chat, AG-UI streaming, and swarm visualization.

### C1. Sessions (`/sessions`) — 588 endpoints

**Module**: `api/v1/sessions/routes.py` | **Tags**: `sessions`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/sessions` | `create_session` | JWT | Create session |
| 2 | GET | `/sessions` | `list_sessions` | JWT | List sessions (paginated) |
| 3 | GET | `/sessions/{session_id}` | `get_session` | JWT | Get session detail |
| 4 | PATCH | `/sessions/{session_id}` | `update_session` | JWT | Update session |
| 5 | DELETE | `/sessions/{session_id}` | `delete_session` | JWT | Delete session |
| 6 | POST | `/sessions/{session_id}/activate` | `activate_session` | JWT | Activate session |
| 7 | POST | `/sessions/{session_id}/suspend` | `suspend_session` | JWT | Suspend session |
| 8 | POST | `/sessions/{session_id}/resume` | `resume_session` | JWT | Resume session |
| 9 | GET | `/sessions/{session_id}/messages` | `list_messages` | JWT | List session messages |
| 10 | POST | `/sessions/{session_id}/messages` | `add_message` | JWT | Add message |
| 11 | POST | `/sessions/{session_id}/attachments` | `add_attachment` | JWT | Add attachment |
| 12 | GET | `/sessions/{session_id}/attachments/{attachment_id}` | `get_attachment` | JWT | Get attachment |
| 13 | GET | `/sessions/{session_id}/tool-calls` | `list_tool_calls` | JWT | List tool calls |
| 14 | POST | `/sessions/{session_id}/tool-calls/{tool_call_id}` | `respond_to_tool_call` | JWT | Respond to tool call |

### C2. Sessions Chat (`/sessions/*/chat`) — 6 endpoints

**Module**: `api/v1/sessions/chat.py` | **Tags**: `sessions-chat`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/sessions/{session_id}/chat` | `chat_message` | JWT | Send chat message (sync) |
| 2 | POST | `/sessions/{session_id}/chat/stream` | `chat_stream` | JWT | Send chat message (SSE stream) |
| 3 | GET | `/sessions/{session_id}/approvals` | `list_approvals` | JWT | List pending approvals |
| 4 | POST | `/sessions/{session_id}/approvals/{approval_id}` | `respond_to_approval` | JWT | Respond to approval |
| 5 | DELETE | `/sessions/{session_id}/approvals` | `clear_approvals` | JWT | Clear all approvals |
| 6 | GET | `/sessions/{session_id}/chat/status` | `get_chat_status` | JWT | Get chat status |

### C3. Sessions WebSocket — 3 endpoints

**Module**: `api/v1/sessions/websocket.py` | **Tags**: `sessions-websocket`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | WS | `/sessions/{session_id}/ws` | `websocket_endpoint` | — | Real-time session WebSocket |
| 2 | GET | `/sessions/{session_id}/ws/status` | `get_websocket_status` | JWT | WebSocket connection status |
| 3 | POST | `/sessions/{session_id}/ws/broadcast` | `broadcast_to_session` | JWT | Broadcast to session |

### C4. Session Resume (`/sessions`) — 2 endpoints

**Module**: `api/v1/orchestrator/session_routes.py` | **Tags**: `sessions-resume`

> Registered BEFORE sessions_router to prevent `/{session_id}` wildcard capture.

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/sessions/recoverable` | `list_recoverable_sessions` | JWT | List recoverable sessions |
| 2 | POST | `/sessions/{session_id}/resume` | `resume_session` | JWT | Resume recoverable session |

### C5. Chat History (`/chat-history`) — 3 endpoints

**Module**: `api/v1/chat_history/routes.py` | **Tags**: `Chat History`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/chat-history/sync` | `sync_chat_history` | JWT | Sync chat history to DB |
| 2 | GET | `/chat-history/{session_id}` | `get_chat_history` | JWT | Get chat history |
| 3 | DELETE | `/chat-history/{session_id}` | `delete_chat_history` | JWT | Delete chat history |

### C6. AG-UI Protocol (`/ag-ui`) — 588 endpoints

**Module**: `api/v1/ag_ui/routes.py`, `upload.py` | **Tags**: `ag-ui`, `File Upload`

#### C6a. Core AG-UI

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/ag-ui/health` | `health_check` | JWT | AG-UI health check |
| 2 | GET | `/ag-ui/status` | `get_status` | JWT | AG-UI system status |
| 3 | POST | `/ag-ui/reset` | `reset` | JWT | Reset AG-UI state |
| 4 | POST | `/ag-ui` | `run_agent` | JWT | Run agent (SSE stream) |
| 5 | POST | `/ag-ui/sync` | `run_agent_sync` | JWT | Run agent (sync response) |

#### C6b. Thread Management

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 6 | GET | `/ag-ui/threads/{thread_id}/history` | `get_thread_history` | JWT | Thread message history |
| 7 | GET | `/ag-ui/threads` | `list_threads` | JWT | List threads |
| 8 | GET | `/ag-ui/threads/{thread_id}/state` | `get_thread_state` | JWT | Get shared state |
| 9 | PATCH | `/ag-ui/threads/{thread_id}/state` | `update_thread_state` | JWT | Update shared state |
| 10 | DELETE | `/ag-ui/threads/{thread_id}/state` | `delete_thread_state` | JWT | Delete shared state |

#### C6c. HITL Approvals

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 11 | GET | `/ag-ui/approvals/pending` | `list_pending_approvals` | JWT | List pending approvals |
| 12 | GET | `/ag-ui/approvals/stats` | `get_approval_stats` | JWT | Approval statistics |
| 13 | GET | `/ag-ui/approvals/{approval_id}` | `get_approval` | JWT | Get approval detail |
| 14 | POST | `/ag-ui/approvals/{approval_id}/approve` | `approve` | JWT | Approve request |
| 15 | POST | `/ag-ui/approvals/{approval_id}/reject` | `reject` | JWT | Reject request |
| 16 | POST | `/ag-ui/approvals/{approval_id}/cancel` | `cancel` | JWT | Cancel request |

#### C6d. Test Endpoints

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 17 | POST | `/ag-ui/test/progress` | `test_progress` | JWT | Test progress streaming |
| 18 | POST | `/ag-ui/test/mode-switch` | `test_mode_switch` | JWT | Test mode switching |
| 19 | POST | `/ag-ui/test/ui-component` | `test_ui_component` | JWT | Test UI component |
| 20 | POST | `/ag-ui/test/ui-component/stream` | `test_ui_component_stream` | JWT | Test UI component (SSE) |
| 21 | POST | `/ag-ui/test/hitl` | `test_hitl` | JWT | Test HITL flow |
| 22 | POST | `/ag-ui/test/hitl/stream` | `test_hitl_stream` | JWT | Test HITL flow (SSE) |
| 23 | POST | `/ag-ui/test/workflow-progress` | `test_workflow_progress` | JWT | Test workflow progress |
| 24 | POST | `/ag-ui/test/workflow-progress/stream` | `test_workflow_progress_stream` | JWT | Test workflow progress (SSE) |
| 25 | POST | `/ag-ui/test/prediction` | `test_prediction` | JWT | Test prediction |
| 26 | POST | `/ag-ui/test/prediction/stream` | `test_prediction_stream` | JWT | Test prediction (SSE) |

#### C6e. File Upload

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 27 | POST | `/ag-ui/upload` | `upload_file` | JWT | Upload file |
| 28 | GET | `/ag-ui/upload/list` | `list_uploads` | JWT | List uploaded files |
| 29 | DELETE | `/ag-ui/upload/{filename}` | `delete_upload` | JWT | Delete uploaded file |
| 30 | GET | `/ag-ui/upload/storage` | `get_storage_usage` | JWT | Get storage usage |

### C7. Swarm (`/swarm`) — 8 endpoints

**Module**: `api/v1/swarm/routes.py`, `demo.py` | **Tags**: `Swarm`, `Swarm Demo`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/swarm/{swarm_id}` | `get_swarm` | JWT | Get swarm status |
| 2 | GET | `/swarm/{swarm_id}/workers` | `list_workers` | JWT | List swarm workers |
| 3 | GET | `/swarm/{swarm_id}/workers/{worker_id}` | `get_worker` | JWT | Get worker detail |
| 4 | POST | `/swarm/demo/start` | `start_demo` | JWT | Start demo swarm |
| 5 | GET | `/swarm/demo/status/{swarm_id}` | `get_demo_status` | JWT | Get demo status |
| 6 | POST | `/swarm/demo/stop/{swarm_id}` | `stop_demo` | JWT | Stop demo swarm |
| 7 | GET | `/swarm/demo/scenarios` | `list_scenarios` | JWT | List demo scenarios |
| 8 | GET | `/swarm/demo/events/{swarm_id}` | `stream_events` | JWT | SSE event stream |

---

## Domain D: Orchestration & Routing

> 588 endpoints across 10 route files — Three-tier intent routing, orchestrator chat pipeline, and n8n integration.

### D1. Orchestration Policies (`/orchestration`) — 7 endpoints

**Module**: `api/v1/orchestration/routes.py` | **Tags**: `Orchestration`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/orchestration/policies` | `list_policies` | JWT | List orchestration policies |
| 2 | GET | `/orchestration/policies/{intent_category}` | `get_policy` | JWT | Get policies by category |
| 3 | POST | `/orchestration/policies/mode/{mode}` | `set_mode` | JWT | Set policy mode |
| 4 | POST | `/orchestration/risk/assess` | `assess_risk` | JWT | Risk assessment |
| 5 | GET | `/orchestration/metrics` | `get_metrics` | JWT | Get orchestration metrics |
| 6 | POST | `/orchestration/metrics/reset` | `reset_metrics` | JWT | Reset metrics |
| 7 | GET | `/orchestration/health` | `health_check` | JWT | Health check |

### D2. Orchestration Intent (`/orchestration/intent`) — 4 endpoints

**Module**: `api/v1/orchestration/intent_routes.py` | **Tags**: `Intent Classification`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/orchestration/intent/classify` | `classify_intent` | JWT | Classify user intent |
| 2 | POST | `/orchestration/intent/test` | `test_classification` | JWT | Test classification |
| 3 | POST | `/orchestration/intent/classify/batch` | `batch_classify` | JWT | Batch classify intents |
| 4 | POST | `/orchestration/intent/quick` | `quick_classify` | JWT | Quick classify |

### D3. Orchestration Dialog (`/orchestration/dialog`) — 4 endpoints

**Module**: `api/v1/orchestration/dialog_routes.py` | **Tags**: `Guided Dialog`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/orchestration/dialog/start` | `start_dialog` | JWT | Start guided dialog |
| 2 | POST | `/orchestration/dialog/{dialog_id}/respond` | `respond_to_dialog` | JWT | Respond to dialog |
| 3 | GET | `/orchestration/dialog/{dialog_id}/status` | `get_dialog_status` | JWT | Get dialog status |
| 4 | DELETE | `/orchestration/dialog/{dialog_id}` | `delete_dialog` | JWT | Delete dialog |

### D4. Orchestration Approvals (`/orchestration/approvals`) — 4 endpoints

**Module**: `api/v1/orchestration/approval_routes.py` | **Tags**: `HITL Approvals`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/orchestration/approvals` | `list_approvals` | JWT | List approvals |
| 2 | GET | `/orchestration/approvals/{approval_id}` | `get_approval` | JWT | Get approval detail |
| 3 | POST | `/orchestration/approvals/{approval_id}/decision` | `submit_decision` | JWT | Submit decision |
| 4 | POST | `/orchestration/approvals/{approval_id}/callback` | `approval_callback` | JWT | Approval callback |

### D5. Orchestration Webhooks (`/orchestration/webhooks`) — 3 endpoints

**Module**: `api/v1/orchestration/webhook_routes.py` | **Tags**: `orchestration-webhooks`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/orchestration/webhooks/servicenow` | `servicenow_webhook` | JWT | ServiceNow webhook |
| 2 | GET | `/orchestration/webhooks/servicenow/health` | `servicenow_health` | JWT | ServiceNow health |
| 3 | POST | `/orchestration/webhooks/servicenow/incident` | `servicenow_incident` | JWT | ServiceNow incident webhook |

### D6. Orchestration Route Management (`/orchestration/routes`) — 7 endpoints

**Module**: `api/v1/orchestration/route_management.py` | **Tags**: `orchestration-routes`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/orchestration/routes` | `create_route` | JWT | Create route configuration |
| 2 | GET | `/orchestration/routes` | `list_routes` | JWT | List routes |
| 3 | GET | `/orchestration/routes/{route_name}` | `get_route` | JWT | Get route by name |
| 4 | PUT | `/orchestration/routes/{route_name}` | `update_route` | JWT | Update route |
| 5 | DELETE | `/orchestration/routes/{route_name}` | `delete_route` | JWT | Delete route |
| 6 | POST | `/orchestration/routes/sync` | `sync_routes` | JWT | Sync route configurations |
| 7 | POST | `/orchestration/routes/search` | `search_routes` | JWT | Search routes |

### D7. Orchestrator Chat Pipeline (`/orchestrator`) — 6 endpoints

**Module**: `api/v1/orchestrator/routes.py` | **Tags**: `orchestrator`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/orchestrator/validate` | `orchestrator_validate` | JWT | Validate pipeline config |
| 2 | GET | `/orchestrator/health` | `orchestrator_health` | JWT | Pipeline health check |
| 3 | GET | `/orchestrator/test-intent` | `test_intent` | JWT | Test intent classification |
| 4 | POST | `/orchestrator/approval/{approval_id}` | `orchestrator_approval` | JWT | Submit approval decision |
| 5 | POST | `/orchestrator/chat/stream` | `orchestrator_chat_stream` | JWT | Chat with SSE stream |
| 6 | POST | `/orchestrator/chat` | `orchestrator_chat` | JWT | Chat sync response |

### D8. Cross-Scenario Routing (`/routing`) — 588 endpoints

> See [A9. Routing](#a9-routing-routing--14-endpoints) above.

### D9. n8n Integration (`/n8n`) — 7 endpoints

**Module**: `api/v1/n8n/routes.py` | **Tags**: `n8n Integration`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/n8n/webhook` | `receive_webhook` | JWT | Receive n8n webhook |
| 2 | POST | `/n8n/webhook/{workflow_id}` | `receive_workflow_webhook` | JWT | Receive workflow-specific webhook |
| 3 | GET | `/n8n/status` | `get_status` | JWT | n8n integration status |
| 4 | GET | `/n8n/config` | `get_config` | JWT | Get n8n config |
| 5 | PUT | `/n8n/config` | `update_config` | JWT | Update n8n config |
| 6 | POST | `/n8n/callback` | `receive_callback` | JWT | Receive orchestration callback |
| 7 | GET | `/n8n/callback/{orchestration_id}` | `get_callback_status` | JWT | Get callback status |

---

## Domain E: Monitoring & Observability

> 588 endpoints across 8 modules — Audit, performance, patrol, correlation, root cause, devtools, notifications, and dashboard.

### E1. Audit (`/audit`) — 8 endpoints

**Module**: `api/v1/audit/routes.py` | **Tags**: `Audit`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/audit/logs` | `list_audit_logs` | JWT | List audit logs (filtered) |
| 2 | GET | `/audit/logs/{entry_id}` | `get_audit_entry` | JWT | Get audit entry |
| 3 | GET | `/audit/executions/{execution_id}/trail` | `get_execution_trail` | JWT | Get execution audit trail |
| 4 | GET | `/audit/statistics` | `get_statistics` | JWT | Audit statistics |
| 5 | GET | `/audit/export` | `export_audit` | JWT | Export audit data |
| 6 | GET | `/audit/actions` | `list_actions` | JWT | List audit action types |
| 7 | GET | `/audit/resources` | `list_resources` | JWT | List audited resources |
| 8 | GET | `/audit/health` | `health_check` | JWT | Audit health check |

### E2. Decision Audit (`/audit/decisions`) — 7 endpoints

**Module**: `api/v1/audit/decision_routes.py` | **Tags**: `Decision Audit`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/audit/decisions` | `list_decisions` | JWT | List decision records |
| 2 | GET | `/audit/decisions/{decision_id}` | `get_decision` | JWT | Get decision detail |
| 3 | GET | `/audit/decisions/{decision_id}/report` | `get_report` | JWT | Get decision report |
| 4 | POST | `/audit/decisions/{decision_id}/feedback` | `submit_feedback` | JWT | Submit decision feedback |
| 5 | GET | `/audit/decisions/statistics` | `get_statistics` | JWT | Decision statistics |
| 6 | GET | `/audit/decisions/summary` | `get_summary` | JWT | Decision summary |
| 7 | GET | `/audit/decisions/health` | `health_check` | JWT | Decision audit health |

### E3. Performance (`/performance`) — 588 endpoints

**Module**: `api/v1/performance/routes.py` | **Tags**: `Performance`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/performance/metrics` | `get_performance_metrics` | JWT | Get performance metrics |
| 2 | POST | `/performance/profile/start` | `start_profiling_session` | JWT | Start profiling session |
| 3 | POST | `/performance/profile/stop` | `stop_profiling_session` | JWT | Stop profiling session |
| 4 | POST | `/performance/profile/metric` | `record_metric` | JWT | Record custom metric |
| 5 | GET | `/performance/profile/sessions` | `list_profiling_sessions` | JWT | List profiling sessions |
| 6 | GET | `/performance/profile/summary/{session_id}` | `get_session_summary` | JWT | Get session summary |
| 7 | POST | `/performance/optimize` | `run_optimization` | JWT | Run performance optimization |
| 8 | GET | `/performance/collector/summary` | `get_collector_summary` | JWT | Collector summary |
| 9 | GET | `/performance/collector/alerts` | `get_alerts` | JWT | Get performance alerts |
| 10 | POST | `/performance/collector/threshold` | `set_threshold` | JWT | Set alert threshold |
| 11 | GET | `/performance/health` | `performance_health` | JWT | Health check |

### E4. Patrol (`/patrol`) — 9 endpoints

**Module**: `api/v1/patrol/routes.py` | **Tags**: `patrol`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/patrol/trigger` | `trigger_patrol` | JWT | Trigger patrol check |
| 2 | GET | `/patrol/reports` | `get_patrol_reports` | JWT | List patrol reports |
| 3 | GET | `/patrol/reports/{report_id}` | `get_patrol_report` | JWT | Get specific report |
| 4 | GET | `/patrol/schedule` | `get_patrol_schedules` | JWT | List patrol schedules |
| 5 | POST | `/patrol/schedule` | `create_patrol_schedule` | JWT | Create patrol schedule |
| 6 | PUT | `/patrol/schedule/{patrol_id}` | `update_patrol_schedule` | JWT | Update schedule |
| 7 | DELETE | `/patrol/schedule/{patrol_id}` | `delete_patrol_schedule` | JWT | Delete schedule |
| 8 | GET | `/patrol/checks` | `list_check_types` | JWT | List check types |
| 9 | GET | `/patrol/checks/{check_type}` | `execute_check` | JWT | Execute specific check |

### E5. Correlation (`/correlation`) — 7 endpoints

**Module**: `api/v1/correlation/routes.py` | **Tags**: `correlation`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/correlation/analyze` | `analyze_correlation` | JWT | Analyze event correlations |
| 2 | GET | `/correlation/{event_id}` | `get_event_correlations` | JWT | Get event correlations |
| 3 | POST | `/correlation/rootcause/analyze` | `analyze_root_cause` | JWT | Root cause analysis |
| 4 | GET | `/correlation/rootcause/{analysis_id}` | `get_root_cause_analysis` | JWT | Get analysis result |
| 5 | GET | `/correlation/graph/{event_id}/mermaid` | `get_correlation_graph_mermaid` | JWT | Mermaid graph format |
| 6 | GET | `/correlation/graph/{event_id}/json` | `get_correlation_graph_json` | JWT | JSON graph format |
| 7 | GET | `/correlation/graph/{event_id}/dot` | `get_correlation_graph_dot` | JWT | DOT graph format |

### E6. Root Cause Analysis (`/rootcause`) — 4 endpoints

**Module**: `api/v1/rootcause/routes.py` | **Tags**: `Root Cause Analysis`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/rootcause/analyze` | `analyze_root_cause` | JWT | Analyze root cause |
| 2 | GET | `/rootcause/{analysis_id}/hypotheses` | `get_hypotheses` | JWT | Get hypotheses |
| 3 | GET | `/rootcause/{analysis_id}/recommendations` | `get_recommendations` | JWT | Get recommendations |
| 4 | POST | `/rootcause/similar` | `find_similar_patterns` | JWT | Find similar patterns |

### E7. DevTools (`/devtools`) — 588 endpoints

**Module**: `api/v1/devtools/routes.py` | **Tags**: `devtools`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/devtools/health` | `health_check` | JWT | Health check |
| 2 | GET | `/devtools/traces` | `list_traces` | JWT | List traces |
| 3 | POST | `/devtools/traces` | `start_trace` | JWT | Start new trace |
| 4 | GET | `/devtools/traces/{execution_id}` | `get_trace` | JWT | Get trace detail |
| 5 | POST | `/devtools/traces/{execution_id}/end` | `end_trace` | JWT | End trace |
| 6 | DELETE | `/devtools/traces/{execution_id}` | `delete_trace` | JWT | Delete trace |
| 7 | POST | `/devtools/traces/{execution_id}/events` | `add_event` | JWT | Add trace event |
| 8 | GET | `/devtools/traces/{execution_id}/events` | `get_events` | JWT | List trace events |
| 9 | POST | `/devtools/traces/{execution_id}/spans` | `start_span` | JWT | Create span |
| 10 | POST | `/devtools/spans/{span_id}/end` | `end_span` | JWT | End span |
| 11 | GET | `/devtools/traces/{execution_id}/timeline` | `get_timeline` | JWT | Get timeline |
| 12 | GET | `/devtools/traces/{execution_id}/statistics` | `get_statistics` | JWT | Trace statistics |

### E8. Notifications (`/notifications`) — 588 endpoints

**Module**: `api/v1/notifications/routes.py` | **Tags**: `notifications`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/notifications/approval` | `send_approval_notification` | JWT | Send approval notification |
| 2 | POST | `/notifications/completion` | `send_completion_notification` | JWT | Send completion notification |
| 3 | POST | `/notifications/error` | `send_error_alert` | JWT | Send error alert |
| 4 | POST | `/notifications/custom` | `send_custom_notification` | JWT | Send custom notification |
| 5 | GET | `/notifications/history` | `get_notification_history` | JWT | Get notification history |
| 6 | GET | `/notifications/statistics` | `get_notification_statistics` | JWT | Notification statistics |
| 7 | DELETE | `/notifications/history` | `clear_notification_history` | JWT | Clear notification history |
| 8 | GET | `/notifications/config` | `get_configuration` | JWT | Get config |
| 9 | PUT | `/notifications/config` | `update_configuration` | JWT | Update config |
| 10 | GET | `/notifications/types` | `list_notification_types` | JWT | List notification types |
| 11 | GET | `/notifications/health` | `health_check` | JWT | Health check |

### E9. Dashboard (`/dashboard`) — 2 endpoints

**Module**: `api/v1/dashboard/routes.py` | **Tags**: `Dashboard`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/dashboard/stats` | `get_dashboard_stats` | JWT | Dashboard statistics |
| 2 | GET | `/dashboard/executions/chart` | `get_execution_chart_data` | JWT | Execution chart data |

---

## Domain F: Platform Infrastructure

> 588 endpoints across 16 modules — Auth, files, memory, sandbox, cache, knowledge, versioning, prompts, learning, code interpreter, MCP, A2A, and autonomous.

### F1. Authentication (`/auth`) — 5 endpoints

**Module**: `api/v1/auth/routes.py`, `migration.py` | **Tags**: `Authentication`

> **Public router** — No JWT required.

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/auth/register` | `register` | Public | Register new user |
| 2 | POST | `/auth/login` | `login` | Public | Login (returns JWT) |
| 3 | POST | `/auth/refresh` | `refresh_token` | Public | Refresh JWT token |
| 4 | GET | `/auth/me` | `get_current_user` | Public | Get current user info |
| 5 | POST | `/auth/migrate-guest` | `migrate_guest` | Public | Migrate guest account data |

### F2. Files (`/files`) — 6 endpoints

**Module**: `api/v1/files/routes.py` | **Tags**: `Files`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/files/upload` | `upload_file` | JWT | Upload file |
| 2 | GET | `/files/` | `list_files` | JWT | List files |
| 3 | GET | `/files/{file_id}` | `get_file` | JWT | Get file metadata |
| 4 | GET | `/files/{file_id}/content` | `get_file_content` | JWT | Get file content |
| 5 | GET | `/files/{file_id}/download` | `download_file` | JWT | Download file |
| 6 | DELETE | `/files/{file_id}` | `delete_file` | JWT | Delete file |

### F3. Memory (`/memory`) — 7 endpoints

**Module**: `api/v1/memory/routes.py` | **Tags**: `Memory`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/memory/add` | `add_memory` | JWT | Add memory entry |
| 2 | POST | `/memory/search` | `search_memory` | JWT | Search memories |
| 3 | GET | `/memory/user/{user_id}` | `get_user_memories` | JWT | Get user memories |
| 4 | DELETE | `/memory/{memory_id}` | `delete_memory` | JWT | Delete memory |
| 5 | POST | `/memory/promote` | `promote_memory` | JWT | Promote to long-term memory |
| 6 | POST | `/memory/context` | `get_context_memories` | JWT | Get context-relevant memories |
| 7 | GET | `/memory/health` | `health_check` | JWT | Memory health check |

### F4. Sandbox (`/sandbox`) — 6 endpoints

**Module**: `api/v1/sandbox/routes.py` | **Tags**: `sandbox`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/sandbox/pool/status` | `get_pool_status` | JWT | Get sandbox pool status |
| 2 | POST | `/sandbox/pool/cleanup` | `cleanup_pool` | JWT | Cleanup sandbox pool |
| 3 | POST | `/sandbox` | `create_sandbox` | JWT | Create new sandbox |
| 4 | GET | `/sandbox/{sandbox_id}` | `get_sandbox` | JWT | Get sandbox detail |
| 5 | DELETE | `/sandbox/{sandbox_id}` | `delete_sandbox` | JWT | Delete sandbox |
| 6 | POST | `/sandbox/{sandbox_id}/ipc` | `send_ipc_message` | JWT | Send IPC message |

### F5. Cache (`/cache`) — 9 endpoints

**Module**: `api/v1/cache/routes.py` | **Tags**: `Cache`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/cache/stats` | `get_cache_stats` | JWT | Get cache statistics |
| 2 | GET | `/cache/config` | `get_cache_config` | JWT | Get cache configuration |
| 3 | POST | `/cache/enable` | `enable_cache` | JWT | Enable cache |
| 4 | POST | `/cache/disable` | `disable_cache` | JWT | Disable cache |
| 5 | POST | `/cache/get` | `get_cache_entry` | JWT | Get cache entry by key |
| 6 | POST | `/cache/set` | `set_cache_entry` | JWT | Set cache entry |
| 7 | POST | `/cache/clear` | `clear_cache` | JWT | Clear all cache |
| 8 | POST | `/cache/warm` | `warm_cache` | JWT | Warm up cache |
| 9 | POST | `/cache/reset-stats` | `reset_stats` | JWT | Reset cache statistics |

### F6. Knowledge (`/knowledge`) — 7 endpoints

**Module**: `api/v1/knowledge/routes.py` | **Tags**: `knowledge`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/knowledge/ingest` | `ingest_text` | JWT | Ingest document text |
| 2 | POST | `/knowledge/search` | `search_knowledge` | JWT | Semantic search |
| 3 | GET | `/knowledge/collections` | `get_collection_info` | JWT | Get collection info |
| 4 | DELETE | `/knowledge/collections` | `delete_collection` | JWT | Delete collection |
| 5 | GET | `/knowledge/skills` | `list_skills` | JWT | List Semantic Kernel skills |
| 6 | GET | `/knowledge/skills/{skill_id}` | `get_skill` | JWT | Get skill detail |
| 7 | GET | `/knowledge/skills/search/query` | `search_skills` | JWT | Search skills |

### F7. Versioning (`/versions`) — 588 endpoints

**Module**: `api/v1/versioning/routes.py` | **Tags**: `versioning`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/versions/health` | `health_check` | JWT | Health check |
| 2 | GET | `/versions/statistics` | `get_statistics` | JWT | Version statistics |
| 3 | POST | `/versions/compare` | `compare_versions` | JWT | Compare two versions |
| 4 | POST | `/versions/` | `create_version` | JWT | Create version |
| 5 | GET | `/versions/` | `list_all_versions` | JWT | List all versions |
| 6 | GET | `/versions/{version_id}` | `get_version` | JWT | Get version detail |
| 7 | DELETE | `/versions/{version_id}` | `delete_version` | JWT | Delete version |
| 8 | POST | `/versions/{version_id}/publish` | `publish_version` | JWT | Publish version |
| 9 | POST | `/versions/{version_id}/deprecate` | `deprecate_version` | JWT | Deprecate version |
| 10 | POST | `/versions/{version_id}/archive` | `archive_version` | JWT | Archive version |
| 11 | GET | `/versions/templates/{template_id}/versions` | `list_template_versions` | JWT | List template versions |
| 12 | GET | `/versions/templates/{template_id}/latest` | `get_latest_version` | JWT | Get latest version |
| 13 | POST | `/versions/templates/{template_id}/rollback` | `rollback_version` | JWT | Rollback to previous |
| 14 | GET | `/versions/templates/{template_id}/statistics` | `get_template_statistics` | JWT | Template version stats |

### F8. Prompts (`/prompts`) — 588 endpoints

**Module**: `api/v1/prompts/routes.py` | **Tags**: `Prompts`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/prompts/templates` | `list_templates` | JWT | List prompt templates |
| 2 | GET | `/prompts/templates/{template_id}` | `get_template` | JWT | Get template |
| 3 | POST | `/prompts/templates` | `create_template` | JWT | Create template |
| 4 | PUT | `/prompts/templates/{template_id}` | `update_template` | JWT | Update template |
| 5 | DELETE | `/prompts/templates/{template_id}` | `delete_template` | JWT | Delete template |
| 6 | POST | `/prompts/templates/{template_id}/render` | `render_template` | JWT | Render template |
| 7 | POST | `/prompts/templates/validate` | `validate_template` | JWT | Validate template |
| 8 | GET | `/prompts/categories` | `list_categories` | JWT | List categories |
| 9 | GET | `/prompts/search` | `search_prompts` | JWT | Search prompts |
| 10 | POST | `/prompts/reload` | `reload_prompts` | JWT | Reload prompt store |
| 11 | GET | `/prompts/health` | `health_check` | JWT | Health check |

### F9. Learning (`/learning`) — 588 endpoints

**Module**: `api/v1/learning/routes.py` | **Tags**: `learning`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/learning/health` | `health_check` | JWT | Health check |
| 2 | GET | `/learning/statistics` | `get_statistics` | JWT | Learning statistics |
| 3 | POST | `/learning/corrections` | `record_correction` | JWT | Record correction case |
| 4 | GET | `/learning/cases` | `list_cases` | JWT | List learning cases |
| 5 | GET | `/learning/cases/{case_id}` | `get_case` | JWT | Get case detail |
| 6 | DELETE | `/learning/cases/{case_id}` | `delete_case` | JWT | Delete case |
| 7 | POST | `/learning/cases/{case_id}/approve` | `approve_case` | JWT | Approve case |
| 8 | POST | `/learning/cases/{case_id}/reject` | `reject_case` | JWT | Reject case |
| 9 | POST | `/learning/cases/bulk-approve` | `bulk_approve_cases` | JWT | Bulk approve cases |
| 10 | POST | `/learning/similar` | `find_similar_cases` | JWT | Find similar cases |
| 11 | POST | `/learning/prompt` | `build_few_shot_prompt` | JWT | Build few-shot prompt |
| 12 | POST | `/learning/cases/{case_id}/effectiveness` | `record_effectiveness` | JWT | Record effectiveness |
| 13 | GET | `/learning/scenarios/{scenario_name}/statistics` | `get_scenario_statistics` | JWT | Scenario statistics |

### F10. Code Interpreter (`/code-interpreter`) — 588 endpoints

**Module**: `api/v1/code_interpreter/routes.py`, `visualization.py` | **Tags**: `Code Interpreter`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/code-interpreter/health` | `health_check` | JWT | Health check |
| 2 | POST | `/code-interpreter/execute` | `execute_code` | JWT | Execute code |
| 3 | POST | `/code-interpreter/analyze` | `analyze_code` | JWT | Analyze code |
| 4 | POST | `/code-interpreter/sessions` | `create_session` | JWT | Create interpreter session |
| 5 | DELETE | `/code-interpreter/sessions/{session_id}` | `delete_session` | JWT | Delete session |
| 6 | GET | `/code-interpreter/sessions/{session_id}` | `get_session` | JWT | Get session detail |
| 7 | POST | `/code-interpreter/files/upload` | `upload_file` | JWT | Upload file to session |
| 8 | GET | `/code-interpreter/files` | `list_files` | JWT | List session files |
| 9 | GET | `/code-interpreter/files/{file_id}` | `get_file` | JWT | Get file detail |
| 10 | DELETE | `/code-interpreter/files/{file_id}` | `delete_file` | JWT | Delete file |
| 11 | GET | `/code-interpreter/sandbox/containers/{container_id}/files/{file_id}` | `get_container_file` | JWT | Get container file |
| 12 | GET | `/code-interpreter/visualizations/types` | `list_visualization_types` | JWT | List visualization types |
| 13 | GET | `/code-interpreter/visualizations/{file_id}` | `get_visualization` | JWT | Get visualization |
| 14 | POST | `/code-interpreter/visualizations/generate` | `generate_visualization` | JWT | Generate visualization |

### F11. MCP (`/mcp`) — 588 endpoints

**Module**: `api/v1/mcp/routes.py` | **Tags**: `MCP`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | GET | `/mcp/servers` | `list_servers` | JWT | List MCP servers |
| 2 | POST | `/mcp/servers` | `register_server` | JWT | Register MCP server |
| 3 | GET | `/mcp/servers/{server_name}` | `get_server` | JWT | Get server detail |
| 4 | DELETE | `/mcp/servers/{server_name}` | `remove_server` | JWT | Remove server |
| 5 | POST | `/mcp/servers/{server_name}/connect` | `connect_server` | JWT | Connect to server |
| 6 | POST | `/mcp/servers/{server_name}/disconnect` | `disconnect_server` | JWT | Disconnect server |
| 7 | GET | `/mcp/servers/{server_name}/tools` | `list_server_tools` | JWT | List server tools |
| 8 | GET | `/mcp/tools` | `list_all_tools` | JWT | List all tools |
| 9 | POST | `/mcp/tools/execute` | `execute_tool` | JWT | Execute tool |
| 10 | GET | `/mcp/status` | `get_status` | JWT | MCP system status |
| 11 | GET | `/mcp/audit` | `get_audit_log` | JWT | MCP audit log |
| 12 | POST | `/mcp/connect-all` | `connect_all` | JWT | Connect all servers |
| 13 | POST | `/mcp/disconnect-all` | `disconnect_all` | JWT | Disconnect all servers |

### F12. A2A Protocol (`/a2a`) — 588 endpoints

**Module**: `api/v1/a2a/routes.py` | **Tags**: `A2A Communication`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/a2a/message` | `send_message` | JWT | Send A2A message |
| 2 | GET | `/a2a/message/{message_id}` | `get_message_status` | JWT | Get message status |
| 3 | GET | `/a2a/messages/pending` | `get_pending_messages` | JWT | Get pending messages |
| 4 | GET | `/a2a/conversation/{correlation_id}` | `get_conversation` | JWT | Get conversation thread |
| 5 | POST | `/a2a/agents/register` | `register_agent` | JWT | Register A2A agent |
| 6 | DELETE | `/a2a/agents/{agent_id}` | `unregister_agent` | JWT | Unregister agent |
| 7 | GET | `/a2a/agents` | `list_agents` | JWT | List registered agents |
| 8 | GET | `/a2a/agents/{agent_id}` | `get_agent` | JWT | Get agent detail |
| 9 | POST | `/a2a/agents/discover` | `discover_agents` | JWT | Discover agents by capability |
| 10 | GET | `/a2a/agents/{agent_id}/capabilities` | `get_agent_capabilities` | JWT | Get agent capabilities |
| 11 | POST | `/a2a/agents/{agent_id}/heartbeat` | `agent_heartbeat` | JWT | Agent heartbeat |
| 12 | PUT | `/a2a/agents/{agent_id}/status` | `update_agent_status` | JWT | Update agent status |
| 13 | GET | `/a2a/statistics` | `get_statistics` | JWT | A2A statistics |
| 14 | POST | `/a2a/maintenance/cleanup` | `run_cleanup` | JWT | Run maintenance cleanup |

### F13. Autonomous Planning (`/claude/autonomous`) — 4 endpoints

**Module**: `api/v1/autonomous/routes.py` | **Tags**: `Autonomous Planning`

| # | Method | Path | Handler | Auth | Description |
|---|--------|------|---------|------|-------------|
| 1 | POST | `/claude/autonomous/plan` | `create_plan` | JWT | Create autonomous plan |
| 2 | GET | `/claude/autonomous/history` | `get_task_history` | JWT | Get task history |
| 3 | GET | `/claude/autonomous/{task_id}` | `get_task_status` | JWT | Get task status |
| 4 | POST | `/claude/autonomous/{task_id}/cancel` | `cancel_task` | JWT | Cancel task |

---

## Authentication

### JWT Token Flow

```
1. POST /api/v1/auth/register   → Create account
2. POST /api/v1/auth/login      → Get {access_token, refresh_token}
3. Use Authorization: Bearer <access_token> for all /api/v1/* protected routes
4. POST /api/v1/auth/refresh    → Refresh expired token
```

### Header Format

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## Common Patterns

### Pagination

Standard query-parameter pagination on list endpoints:

```
GET /api/v1/agents/?page=1&page_size=20
```

Response:
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

### SSE Streaming

Endpoints returning `text/event-stream` (Server-Sent Events):

| Endpoint | Purpose |
|----------|---------|
| `POST /ag-ui` | AG-UI agent run (SSE) |
| `POST /ag-ui/test/*/stream` | AG-UI test streams |
| `POST /orchestrator/chat/stream` | Orchestrator chat stream |
| `POST /sessions/{id}/chat/stream` | Session chat stream |
| `GET /swarm/demo/events/{id}` | Swarm event stream |

### WebSocket Endpoints

| Endpoint | Purpose |
|----------|---------|
| `WS /sessions/{session_id}/ws` | Real-time session communication |
| `WS /concurrent/ws/{execution_id}` | Concurrent execution updates |
| `WS /concurrent/ws` | Global concurrent events |
| `WS /groupchat/{group_id}/ws` | GroupChat real-time |

---

## Error Codes

| Status Code | Meaning | Common Causes |
|-------------|---------|---------------|
| 200 | OK | Successful GET/PUT/PATCH |
| 201 | Created | Successful POST (resource created) |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Validation error, invalid state transition |
| 401 | Unauthorized | Missing/invalid/expired JWT |
| 403 | Forbidden | Insufficient role permissions |
| 404 | Not Found | Resource does not exist |
| 409 | Conflict | Duplicate name/key, concurrent modification |
| 422 | Unprocessable Entity | Pydantic validation failure |
| 500 | Internal Server Error | Unhandled exception |

---

## Endpoint Count Summary

| Domain | Category | Endpoints |
|--------|----------|-----------|
| System | Health/Ready | 3 |
| **A** | Core Entity Management | 80 |
| **B** | AI Agent Operations | 148 |
| **C** | Real-Time & Collaboration | 56 |
| **D** | Orchestration & Routing | 52 |
| **E** | Monitoring & Observability | 80 |
| **F** | Platform Infrastructure | 147 |
| | **Total** | **566** |

> Note: Some endpoints appear in multiple domain categories for cross-reference convenience (e.g., Routing appears in both A and D). The unique count across all route files is **563 REST + 3 WebSocket = 566**.

---

## Route File Index

Quick reference mapping modules to source files.

| Module | Route File(s) | Endpoints |
|--------|---------------|-----------|
| agents | `routes.py` | 6 |
| workflows | `routes.py`, `graph_routes.py` | 12 |
| executions | `routes.py` | 11 |
| checkpoints | `routes.py` | 10 |
| templates | `routes.py` | 11 |
| triggers | `routes.py` | 8 |
| connectors | `routes.py` | 9 |
| routing | `routes.py` | 14 |
| notifications | `routes.py` | 11 |
| audit | `routes.py`, `decision_routes.py` | 15 |
| cache | `routes.py` | 9 |
| prompts | `routes.py` | 11 |
| learning | `routes.py` | 13 |
| devtools | `routes.py` | 12 |
| dashboard | `routes.py` | 2 |
| versioning | `routes.py` | 14 |
| performance | `routes.py` | 11 |
| concurrent | `routes.py`, `websocket.py` | 15 |
| handoff | `routes.py` | 14 |
| groupchat | `routes.py` | 42 |
| planning | `routes.py` | 46 |
| nested | `routes.py` | 16 |
| code_interpreter | `routes.py`, `visualization.py` | 14 |
| mcp | `routes.py` | 13 |
| sessions | `routes.py`, `chat.py`, `websocket.py` | 23 |
| claude_sdk | `routes.py`, `autonomous_routes.py`, `hooks_routes.py`, `hybrid_routes.py`, `intent_routes.py`, `mcp_routes.py`, `tools_routes.py` | 40 |
| hybrid | `context_routes.py`, `core_routes.py`, `risk_routes.py`, `switch_routes.py` | 23 |
| ag_ui | `routes.py`, `upload.py` | 33 |
| auth | `routes.py`, `migration.py` | 5 |
| files | `routes.py` | 6 |
| memory | `routes.py` | 7 |
| sandbox | `routes.py` | 6 |
| autonomous | `routes.py` | 4 |
| a2a | `routes.py` | 14 |
| patrol | `routes.py` | 9 |
| correlation | `routes.py` | 7 |
| rootcause | `routes.py` | 4 |
| orchestration | `routes.py`, `intent_routes.py`, `dialog_routes.py`, `approval_routes.py`, `webhook_routes.py`, `route_management.py` | 29 |
| swarm | `routes.py`, `demo.py` | 8 |
| n8n | `routes.py` | 7 |
| orchestrator | `routes.py`, `session_routes.py` | 8 |
| chat_history | `routes.py` | 3 |
| tasks | `routes.py` | 9 |
| knowledge | `routes.py` | 7 |

---

*Document generated from V9 codebase analysis of 48 route modules (64 `.py` route files) under `backend/src/api/v1/`.*
