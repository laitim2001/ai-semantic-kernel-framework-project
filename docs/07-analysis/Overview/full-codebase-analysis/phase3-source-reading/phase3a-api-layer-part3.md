# Phase 3A: API Layer Analysis - Part 3

> **Agent**: A3
> **Scope**: `backend/src/api/v1/` — orchestration, patrol, performance, planning, prompts, rootcause, routing, sandbox, sessions, swarm, templates, triggers, versioning, workflows
> **Date**: 2026-03-15
> **Total Files Read**: 48 Python files
> **Total LOC**: ~8,900 lines (estimated across all files)

---

## Module-by-Module Analysis

---

### orchestration/

**Files**: 8 files, ~2,350 LOC
**Endpoints**: 28 endpoints (across 6 routers)

| Endpoint | Method | Path | Business Logic | Data Source | Problems |
|----------|--------|------|----------------|-------------|----------|
| list_policies | GET | /orchestration/policies | List all risk policies from RiskPolicies singleton | In-memory RiskPolicies | None |
| list_policies_by_category | GET | /orchestration/policies/{category} | Filter policies by intent category | In-memory RiskPolicies | None |
| switch_policy_mode | POST | /orchestration/policies/mode/{mode} | Switch between default/strict/relaxed policy sets | In-memory singleton swap | Global mutable state |
| assess_risk | POST | /orchestration/risk/assess | Standalone risk assessment for an intent | RiskAssessor + AssessmentContext | None |
| get_metrics | GET | /orchestration/metrics | Return routing metrics | **HARDCODED zeros** | **STUB**: Returns all-zero placeholder metrics |
| reset_metrics | POST | /orchestration/metrics/reset | Reset routing metrics | None | **STUB**: No actual reset logic |
| health_check | GET | /orchestration/health | Module health status | In-memory singletons | None |
| classify_intent | POST | /orchestration/intent/classify | Three-tier intent classification (Pattern->Semantic->LLM) + risk assessment | Real BusinessIntentRouter or mock fallback | Falls back to mock router if real router init fails |
| test_intent | POST | /orchestration/intent/test | Debug: layer-by-layer classification results | Real/mock router | Test endpoint runs classification twice (layer tests + full route) |
| batch_classify | POST | /orchestration/intent/classify/batch | Sequential batch classification | Calls classify_intent in loop | Not parallelized - sequential processing |
| quick_classify | POST | /orchestration/intent/quick | Simplified classification with minimal response | Router + Assessor | None |
| start_dialog | POST | /orchestration/dialog/start | Start guided dialog session for information gathering | GuidedDialogEngine (real or mock) | In-memory session storage (`_dialog_sessions` dict) |
| respond_to_dialog | POST | /orchestration/dialog/{id}/respond | Submit user responses to dialog questions | GuidedDialogEngine | Concatenates field responses into single string |
| get_dialog_status | GET | /orchestration/dialog/{id}/status | Get current dialog session status | In-memory + engine state | Swallows engine errors, returns basic info |
| cancel_dialog | DELETE | /orchestration/dialog/{id} | Cancel/close dialog session | In-memory session | None |
| list_approvals | GET | /orchestration/approvals | List pending HITL approval requests | HITLController (Redis/InMemory) | Pagination is in-memory (loads all then slices) |
| get_approval | GET | /orchestration/approvals/{id} | Get detailed approval request info | HITLController | Heavy use of hasattr() for duck-typing |
| submit_decision | POST | /orchestration/approvals/{id}/decision | Submit approve/reject decision | HITLController | None |
| teams_callback | POST | /orchestration/approvals/{id}/callback | Teams Adaptive Card action callback | HITLController | Returns 200 with success=false on errors instead of HTTP error codes |
| create_route | POST | /orchestration/routes | Create semantic route in Azure AI Search | RouteManager (Azure Search + Embeddings) | Requires USE_AZURE_SEARCH=true, uses os.getenv for config |
| list_routes | GET | /orchestration/routes | List all semantic routes | RouteManager | None |
| get_route | GET | /orchestration/routes/{name} | Get single route detail | RouteManager | None |
| update_route | PUT | /orchestration/routes/{name} | Update route metadata/utterances | RouteManager | None |
| delete_route | DELETE | /orchestration/routes/{name} | Delete route and utterance documents | RouteManager | None |
| sync_routes | POST | /orchestration/routes/sync | Sync predefined routes to Azure AI Search | RouteManager | None |
| search_test | POST | /orchestration/routes/search | Test vector search query | RouteManager | None |
| receive_servicenow_webhook | POST | /orchestration/webhooks/servicenow | Receive ServiceNow RITM webhook events | WebhookReceiver + RITMIntentMapper | Uses os.environ for config (should use Settings) |
| webhook_health | GET | /orchestration/webhooks/servicenow/health | Webhook receiver health check | WebhookReceiver | Accesses private attributes |
| receive_servicenow_incident | POST | /orchestration/webhooks/servicenow/incident | Receive ServiceNow INC incident webhook | WebhookReceiver + IncidentHandler | None |

**Sprint Reference**: Phase 28, Sprints 96-98 (core); Sprint 114-115 (webhooks/routes); Sprint 126 (incidents); Sprint 128 (LLM factory)
**Assessment**: **MOSTLY COMPLETE** — Core three-tier routing is fully implemented with real LLM integration. Metrics endpoints are stubs. Dialog uses in-memory storage.

**Issues Found**:
1. **STUB**: `get_metrics()` returns hardcoded zeros — no actual metrics collection
2. **STUB**: `reset_metrics()` does nothing
3. **In-memory storage**: Dialog sessions use `_dialog_sessions` dict — data lost on restart
4. **Mock fallback**: Intent router falls back to mock if real router initialization fails (acceptable for dev, problematic for prod)
5. **Global mutable state**: Policy mode switching uses module-level globals
6. **os.environ usage**: `webhook_routes.py` uses `os.environ.get()` for ServiceNow config instead of pydantic Settings (violates project convention per `feedback_env_vars_vs_settings.md`)
7. **route_management.py**: Uses `os.getenv()` for Azure Search config instead of Settings
8. **Teams callback**: Returns 200 with `success=false` instead of proper HTTP error codes

---

### patrol/

**Files**: 2 files, ~559 LOC
**Endpoints**: 9 endpoints

| Endpoint | Method | Path | Business Logic | Data Source | Problems |
|----------|--------|------|----------------|-------------|----------|
| trigger_patrol | POST | /patrol/trigger | Trigger manual patrol execution | **In-memory dict** | **MOCK**: Creates simulated report, no real execution |
| get_patrol_reports | GET | /patrol/reports | List patrol reports with pagination | **Hardcoded sample data** | **MOCK**: Returns hardcoded sample report |
| get_patrol_report | GET | /patrol/reports/{id} | Get specific patrol report | In-memory dict | **MOCK**: Auto-completes "running" reports on fetch |
| get_patrol_schedules | GET | /patrol/schedule | List patrol schedules | **Hardcoded + in-memory** | **MOCK**: Returns hardcoded default schedules |
| create_patrol_schedule | POST | /patrol/schedule | Create patrol schedule | In-memory dict | **MOCK**: No actual cron scheduling |
| update_patrol_schedule | PUT | /patrol/schedule/{id} | Update patrol schedule | In-memory dict | Creates copy for built-in schedules on update |
| delete_patrol_schedule | DELETE | /patrol/schedule/{id} | Delete patrol schedule | In-memory dict | None |
| list_check_types | GET | /patrol/checks | List available check types | **Hardcoded dict** | Static check type definitions |
| execute_check | GET | /patrol/checks/{type} | Execute a specific check | **MOCK execution** | **BLOCKING**: Uses `time.sleep(0.1)` in async handler |

**Sprint Reference**: Phase 23, Sprint 82
**Assessment**: **STUB** — Entirely mock/simulated. No real patrol execution, no real scheduling, no real check execution.

**Issues Found**:
1. **All mock data**: Every endpoint returns simulated/hardcoded data
2. **Blocking sleep**: `execute_check` uses synchronous `time.sleep(0.1)` in async handler — blocks event loop
3. **No persistence**: In-memory dicts lose all data on restart
4. **No real scheduling**: Schedule CRUD exists but no scheduler integration
5. **Auto-completing reports**: `get_patrol_report` silently changes report status from "running" to "healthy" on fetch

---

### performance/

**Files**: 2 files, ~432 LOC
**Endpoints**: 11 endpoints

| Endpoint | Method | Path | Business Logic | Data Source | Problems |
|----------|--------|------|----------------|-------------|----------|
| get_performance_metrics | GET | /performance/metrics | Comprehensive performance metrics | MetricCollector + mock Phase2 stats | **PARTIAL**: Phase2 stats are hardcoded mock values |
| start_profiling_session | POST | /performance/profile/start | Start profiling session | PerformanceProfiler | None |
| stop_profiling_session | POST | /performance/profile/stop | Stop active profiling session | PerformanceProfiler | None |
| record_metric | POST | /performance/profile/metric | Record a performance metric | PerformanceProfiler | None |
| list_profiling_sessions | GET | /performance/profile/sessions | List all profiling sessions | PerformanceProfiler | None |
| get_session_summary | GET | /performance/profile/summary/{id} | Get profiling session summary | PerformanceProfiler | None |
| run_optimization | POST | /performance/optimize | Run optimization analysis | PerformanceOptimizer | None |
| get_collector_summary | GET | /performance/collector/summary | Get metric collector summary | MetricCollector | None |
| get_alerts | GET | /performance/collector/alerts | Get performance alerts | MetricCollector | None |
| set_threshold | POST | /performance/collector/threshold | Set metric threshold | MetricCollector | None |
| performance_health | GET | /performance/health | Module health check | MetricCollector | Swallows errors, returns "unhealthy" status |

**Sprint Reference**: Phase 2, Sprint 12
**Assessment**: **MOSTLY COMPLETE** — Real system metrics collection works. Phase 2 stats (concurrent_executions, handoff_success_rate, etc.) are hardcoded mock values. Profiler and optimizer use real core modules.

**Issues Found**:
1. **Mock Phase2 stats**: `Phase2StatsResponse` contains hardcoded values (e.g., `concurrent_executions=12`, `handoff_success_rate=97.5`)
2. **Generated history**: Historical metrics are synthetically generated from current values, not real historical data
3. **Default recommendations**: Falls back to hardcoded recommendations when profiler returns none
4. **Error swallowing**: `get_performance_metrics` returns hardcoded fallback data on any exception instead of raising

---

### planning/

**Files**: 3 files, ~1,180 LOC
**Endpoints**: ~46 endpoints (estimated from file structure)

| Endpoint | Method | Path | Business Logic | Data Source | Problems |
|----------|--------|------|----------------|-------------|----------|
| decompose_task | POST | /planning/decompose | Decompose task into subtasks | PlanningAdapter | None |
| get_decomposition | GET | /planning/decompose/{id} | Get decomposition result | In-memory store | None |
| refine_decomposition | POST | /planning/decompose/{id}/refine | Refine decomposition with feedback | PlanningAdapter | None |
| create_plan | POST | /planning/plans | Create execution plan | PlanningAdapter | None |
| get_plan | GET | /planning/plans/{id} | Get plan details | In-memory | None |
| get_plan_status | GET | /planning/plans/{id}/status | Get plan execution status | In-memory | None |
| start_plan | POST | /planning/plans/{id}/start | Start plan execution | PlanningAdapter | None |
| approve_plan | POST | /planning/plans/{id}/approve | Approve plan for execution | PlanningAdapter | None |
| make_decision | POST | /planning/decisions | Make autonomous decision | PlanningAdapter | None |
| execute_trial | POST | /planning/trial | Execute with trial-and-error | PlanningAdapter | None |
| (Magentic endpoints) | Various | /planning/magentic/* | Magentic One workflow operations | MagenticBuilder | ~15 endpoints |
| (PlanningAdapter endpoints) | Various | /planning/adapter/* | PlanningAdapter CRUD | PlanningAdapter | ~10 endpoints |
| (MultiTurn endpoints) | Various | /planning/multiturn/* | MultiTurn session management | MultiTurnAdapter | ~8 endpoints |

**Sprint Reference**: Phase 2, Sprint 10 (core); Sprint 17 (Magentic); Sprint 24 (PlanningAdapter + MultiTurn); Sprint 31 (adapter migration)
**Assessment**: **COMPLETE** — Comprehensive planning module with task decomposition, autonomous decisions, trial-and-error learning, Magentic One workflows, and multi-turn sessions. Uses PlanningAdapter from Agent Framework.

**Issues Found**:
1. **Large file**: `routes.py` is ~1,000+ lines — could benefit from splitting into sub-routers
2. **In-memory stores**: Plans, decisions, and trials stored in module-level dicts
3. **Complex schemas**: `schemas.py` is ~590 lines with many model classes across multiple feature areas

---

### prompts/

**Files**: 3 files, ~656 LOC
**Endpoints**: 11 endpoints

| Endpoint | Method | Path | Business Logic | Data Source | Problems |
|----------|--------|------|----------------|-------------|----------|
| list_templates | GET | /prompts/templates | List prompt templates with filtering | PromptTemplateManager | None |
| get_template | GET | /prompts/templates/{id} | Get specific template | PromptTemplateManager | None |
| create_template | POST | /prompts/templates | Create new prompt template | PromptTemplateManager | None |
| update_template | PUT | /prompts/templates/{id} | Update existing template | PromptTemplateManager | Direct mutation of domain object |
| delete_template | DELETE | /prompts/templates/{id} | Delete template | PromptTemplateManager | None |
| render_template | POST | /prompts/templates/{id}/render | Render template with variables | PromptTemplateManager | None |
| validate_template | POST | /prompts/templates/validate | Validate template syntax | PromptTemplateManager | None |
| list_categories | GET | /prompts/categories | List template categories | PromptTemplateManager | None |
| search_templates | GET | /prompts/search | Search templates by keyword | PromptTemplateManager | None |
| reload_templates | POST | /prompts/reload | Reload templates from filesystem | PromptTemplateManager | None |
| health_check | GET | /prompts/health | Service health check | PromptTemplateManager | None |

**Sprint Reference**: Phase 1, Sprint 3
**Assessment**: **COMPLETE** — Full CRUD + render + validate + search for prompt templates. Uses domain layer properly.

**Issues Found**:
1. **Direct mutation**: `update_template` mutates the domain object directly (`template.name = request.name`) instead of going through a service method
2. **Global singleton**: Uses module-level `_prompt_manager` global

---

### rootcause/

**Files**: 2 files, ~443 LOC
**Endpoints**: 4 endpoints

| Endpoint | Method | Path | Business Logic | Data Source | Problems |
|----------|--------|------|----------------|-------------|----------|
| analyze_root_cause | POST | /rootcause/analyze | Start root cause analysis | **RootCauseStore (all mock)** | **STUB**: Returns hardcoded analysis results |
| get_hypotheses | GET | /rootcause/{id}/hypotheses | Get analysis hypotheses | **Mock store** | **STUB**: Hardcoded hypothesis templates |
| get_recommendations | GET | /rootcause/{id}/recommendations | Get recommendations | **Mock store** | **STUB**: Hardcoded recommendations |
| find_similar_patterns | POST | /rootcause/similar | Find similar historical patterns | **Mock store** | **STUB**: Hardcoded patterns |

**Sprint Reference**: Phase 23 (Testing)
**Assessment**: **STUB** — Entirely mock implementation. All data is hardcoded templates generated at request time. No real AI analysis, no real historical pattern matching.

**Issues Found**:
1. **100% mock**: Every response is generated from hardcoded templates
2. **No AI integration**: Despite being "root cause analysis", no LLM or ML is used
3. **Fake confidence scores**: Hardcoded confidence values (0.87, 0.65, 0.55, etc.)
4. **In-memory only**: `RootCauseStore` uses dict, data lost on restart

---

### routing/

**Files**: 3 files, ~576 LOC
**Endpoints**: 14 endpoints

| Endpoint | Method | Path | Business Logic | Data Source | Problems |
|----------|--------|------|----------------|-------------|----------|
| route_to_scenario | POST | /routing/route | Route execution between scenarios | ScenarioRouter (domain) | None |
| create_relation | POST | /routing/relations | Create execution relationship | ScenarioRouter | None |
| get_execution_relations | GET | /routing/executions/{id}/relations | Get related executions | ScenarioRouter | None |
| get_execution_chain | GET | /routing/executions/{id}/chain | Get full relation chain | ScenarioRouter | None |
| get_relation | GET | /routing/relations/{id} | Get specific relation | ScenarioRouter | None |
| delete_relation | DELETE | /routing/relations/{id} | Delete relation | ScenarioRouter | None |
| list_scenarios | GET | /routing/scenarios | List configured scenarios | ScenarioRouter | None |
| get_scenario_config | GET | /routing/scenarios/{name} | Get scenario configuration | ScenarioRouter | None |
| configure_scenario | PUT | /routing/scenarios/{name} | Update scenario config | ScenarioRouter | None |
| set_default_workflow | POST | /routing/scenarios/{name}/workflow | Set default workflow | ScenarioRouter | None |
| list_relation_types | GET | /routing/relation-types | List available relation types | Enum values | None |
| get_statistics | GET | /routing/statistics | Get routing statistics | ScenarioRouter | None |
| clear_all_relations | DELETE | /routing/relations | Clear all relations (admin) | ScenarioRouter | No auth protection on destructive operation |
| health_check | GET | /routing/health | Health check | ScenarioRouter | None |

**Sprint Reference**: Phase 1, Sprint 3
**Assessment**: **COMPLETE** — Full cross-scenario routing with relationship management. Uses domain layer properly.

**Issues Found**:
1. **No auth on destructive ops**: `clear_all_relations` has no authentication/authorization check
2. **In-memory ScenarioRouter**: All relations stored in memory (domain layer limitation)
3. **Global singleton**: Module-level `_routing_service`

---

### sandbox/

**Files**: 3 files, ~207 LOC
**Endpoints**: 6 endpoints

| Endpoint | Method | Path | Business Logic | Data Source | Problems |
|----------|--------|------|----------------|-------------|----------|
| get_pool_status | GET | /sandbox/pool/status | Get process pool status | SandboxService (domain) | None |
| cleanup_pool | POST | /sandbox/pool/cleanup | Cleanup idle processes | SandboxService | None |
| create_sandbox | POST | /sandbox | Create new sandbox process | SandboxService | None |
| get_sandbox | GET | /sandbox/{id} | Get sandbox status | SandboxService | None |
| delete_sandbox | DELETE | /sandbox/{id} | Terminate and delete sandbox | SandboxService | None |
| send_ipc_message | POST | /sandbox/{id}/ipc | Send IPC message to sandbox | SandboxService | None |

**Sprint Reference**: Phase 21
**Assessment**: **COMPLETE** — Clean implementation using domain service. Well-structured with proper error handling.

**Issues Found**:
1. **Global singleton**: Module-level `_sandbox_service`
2. **No authentication**: No auth checks on sandbox operations

---

### sessions/

**Files**: 5 files, ~1,988 LOC
**Endpoints**: ~20 endpoints (REST + WebSocket + Chat)

| Endpoint | Method | Path | Business Logic | Data Source | Problems |
|----------|--------|------|----------------|-------------|----------|
| create_session | POST | /sessions | Create interactive session | SessionService (DB + Redis) | None |
| list_sessions | GET | /sessions | List user sessions | SessionService | None |
| get_session | GET | /sessions/{id} | Get session details | SessionService | None |
| update_session | PATCH | /sessions/{id} | Update session title/metadata | SessionService | None |
| end_session | DELETE | /sessions/{id} | End session | SessionService | None |
| activate_session | POST | /sessions/{id}/activate | Activate session | SessionService | None |
| suspend_session | POST | /sessions/{id}/suspend | Suspend active session | SessionService | None |
| resume_session | POST | /sessions/{id}/resume | Resume suspended session | SessionService | None |
| get_messages | GET | /sessions/{id}/messages | Get message history | SessionService | None |
| send_message | POST | /sessions/{id}/messages | Send user message | SessionService | None |
| upload_attachment | POST | /sessions/{id}/attachments | Upload attachment | **NOT IMPLEMENTED** | **TODO**: Returns 501 |
| download_attachment | GET | /sessions/{id}/attachments/{aid} | Download attachment | **NOT IMPLEMENTED** | **TODO**: Returns 501 |
| list_tool_calls | GET | /sessions/{id}/tool-calls | List tool calls | SessionService | None |
| handle_tool_call | POST | /sessions/{id}/tool-calls/{tcid} | Approve/reject tool call | SessionService | None |
| chat | POST | /sessions/{id}/chat | Send chat message (sync) | SessionAgentBridge | None |
| chat_stream | POST | /sessions/{id}/chat/stream | Chat with SSE streaming | SessionAgentBridge | None |
| get_pending_approvals | GET | /sessions/{id}/approvals | Get pending approvals | SessionAgentBridge | None |
| handle_approval | POST | /sessions/{id}/approvals/{aid} | Process approval request | SessionAgentBridge | None |
| cancel_approvals | DELETE | /sessions/{id}/approvals | Cancel all pending approvals | SessionAgentBridge | None |
| get_chat_status | GET | /sessions/{id}/chat/status | Get chat processing status | SessionAgentBridge | **TODO**: `is_processing` hardcoded to False |
| websocket_endpoint | WS | /sessions/{id}/ws | Real-time WebSocket chat | SessionAgentBridge | None |
| get_websocket_status | GET | /sessions/{id}/ws/status | WebSocket connection status | WebSocketManager | None |
| broadcast_to_session | POST | /sessions/{id}/ws/broadcast | Broadcast to session connections | WebSocketManager | None |

**Sprint Reference**: Phase 8-10 (core); Sprint 46 (WebSocket + Chat); Sprint 111 (JWT auth)
**Assessment**: **MOSTLY COMPLETE** — Best-implemented module in this batch. Uses proper DI with database + Redis. JWT authentication integrated. WebSocket with heartbeat support.

**Issues Found**:
1. **NOT IMPLEMENTED**: Attachment upload/download returns 501 with TODO comment
2. **TODO**: `get_chat_status` has `is_processing: False` hardcoded
3. **SimpleAgentRepository**: `chat.py` uses a stub agent repository that always returns None
4. **Duplicate Redis clients**: Three separate `_redis_client` singletons across routes.py, websocket.py, and chat.py

---

### swarm/

**Files**: 5 files, ~835 LOC
**Endpoints**: 8 endpoints

| Endpoint | Method | Path | Business Logic | Data Source | Problems |
|----------|--------|------|----------------|-------------|----------|
| get_swarm_status | GET | /swarm/{id} | Get swarm execution status | SwarmTracker | None |
| list_swarm_workers | GET | /swarm/{id}/workers | List all workers in swarm | SwarmTracker | None |
| get_worker_details | GET | /swarm/{id}/workers/{wid} | Get detailed worker info | SwarmTracker | None |
| start_demo | POST | /swarm/demo/start | Start demo swarm execution | SwarmIntegration (background task) | Demo/simulation only |
| get_demo_status | GET | /swarm/demo/status/{id} | Get demo execution status | SwarmTracker + _active_demos | None |
| stop_demo | POST | /swarm/demo/stop/{id} | Stop demo execution | _active_demos dict | Only marks as cancelled, doesn't actually stop tasks |
| list_scenarios | GET | /swarm/demo/scenarios | List available demo scenarios | Hardcoded list | None |
| subscribe_swarm_events | GET | /swarm/demo/events/{id} | SSE event stream for swarm progress | SwarmTracker polling | None |

**Sprint Reference**: Phase 29
**Assessment**: **COMPLETE** — Status API uses real SwarmTracker. Demo endpoints provide simulated execution with real SSE streaming. Clean architecture with proper dependency injection.

**Issues Found**:
1. **Stop doesn't cancel**: `stop_demo` only sets status in dict but doesn't cancel the asyncio background task
2. **Polling SSE**: Event generator polls SwarmTracker at 200ms intervals rather than using push-based events
3. **In-memory demos**: `_active_demos` dict loses state on restart

---

### templates/

**Files**: 3 files, ~654 LOC
**Endpoints**: 11 endpoints

| Endpoint | Method | Path | Business Logic | Data Source | Problems |
|----------|--------|------|----------------|-------------|----------|
| health_check | GET | /templates/health | Service health check | TemplateService | None |
| get_statistics | GET | /templates/statistics/summary | Template statistics | TemplateService | None |
| list_categories | GET | /templates/categories/list | List template categories | TemplateService | None |
| get_popular_templates | GET | /templates/popular/list | Popular templates by usage | TemplateService | None |
| get_top_rated_templates | GET | /templates/top-rated/list | Top rated templates | TemplateService | None |
| search_templates | POST | /templates/search | Search with relevance scoring | TemplateService | None |
| list_templates | GET | /templates/ | List with filtering and pagination | TemplateService | In-memory pagination |
| get_similar_templates | GET | /templates/similar/{id} | Find similar templates | TemplateService | None |
| get_template | GET | /templates/{id} | Get template details | TemplateService | None |
| instantiate_template | POST | /templates/{id}/instantiate | Create agent from template | TemplateService | None |
| rate_template | POST | /templates/{id}/rate | Rate template (1-5) | TemplateService | None |

**Sprint Reference**: Phase 1, Sprint 4
**Assessment**: **COMPLETE** — Full template marketplace with search, rating, instantiation. Static routes correctly ordered before dynamic routes.

**Issues Found**:
1. **In-memory pagination**: `list_templates` loads all templates then slices in memory
2. **Global singleton**: Module-level `_template_service`
3. **File-based templates**: Loads from filesystem directory

---

### triggers/

**Files**: 3 files, ~538 LOC
**Endpoints**: 9 endpoints (including health)

| Endpoint | Method | Path | Business Logic | Data Source | Problems |
|----------|--------|------|----------------|-------------|----------|
| trigger_workflow | POST | /triggers/webhook/{wf_id} | Trigger workflow via webhook with signature verification | WebhookTriggerService (domain) | None |
| list_webhook_configs | GET | /triggers/webhooks | List all webhook configurations | WebhookTriggerService | None |
| create_webhook_config | POST | /triggers/webhooks | Create webhook configuration | WebhookTriggerService | None |
| get_webhook_config | GET | /triggers/webhooks/{wf_id} | Get webhook config by workflow ID | WebhookTriggerService | None |
| update_webhook_config | PUT | /triggers/webhooks/{wf_id} | Update webhook configuration | WebhookTriggerService | Direct object mutation |
| delete_webhook_config | DELETE | /triggers/webhooks/{wf_id} | Delete webhook configuration | WebhookTriggerService | None |
| test_signature | POST | /triggers/webhooks/test-signature | Test HMAC signature verification | WebhookTriggerService | None |
| health_check | GET | /triggers/health | Service health check | WebhookTriggerService | None |

**Sprint Reference**: Phase 1, Sprint 3
**Assessment**: **COMPLETE** — Full webhook trigger management with HMAC signature verification and retry support. Uses domain layer properly.

**Issues Found**:
1. **Direct object mutation**: `update_webhook_config` mutates domain config object directly
2. **Global singleton**: Module-level `_trigger_service`

---

### versioning/

**Files**: 3 files, ~612 LOC
**Endpoints**: 14 endpoints

| Endpoint | Method | Path | Business Logic | Data Source | Problems |
|----------|--------|------|----------------|-------------|----------|
| health_check | GET | /versions/health | Service health check | VersioningService | None |
| get_statistics | GET | /versions/statistics | Versioning statistics | VersioningService | None |
| compare_versions | POST | /versions/compare | Compare two versions with diff | VersioningService | None |
| create_version | POST | /versions/ | Create new version (major/minor/patch) | VersioningService | None |
| list_all_versions | GET | /versions/ | List all versions with filtering | VersioningService | Accesses private `_template_versions` |
| get_version | GET | /versions/{id} | Get version details with content | VersioningService | None |
| delete_version | DELETE | /versions/{id} | Delete a version | VersioningService | None |
| publish_version | POST | /versions/{id}/publish | Publish version | VersioningService | None |
| deprecate_version | POST | /versions/{id}/deprecate | Deprecate version | VersioningService | None |
| archive_version | POST | /versions/{id}/archive | Archive version | VersioningService | None |
| list_template_versions | GET | /versions/templates/{tid}/versions | List template's versions | VersioningService | None |
| get_latest_version | GET | /versions/templates/{tid}/latest | Get latest version | VersioningService | None |
| rollback_version | POST | /versions/templates/{tid}/rollback | Rollback to previous version | VersioningService | None |
| get_template_statistics | GET | /versions/templates/{tid}/statistics | Template version statistics | VersioningService | None |

**Sprint Reference**: Phase 1, Sprint 4
**Assessment**: **COMPLETE** — Comprehensive version management with semantic versioning, diff comparison, rollback, and lifecycle management.

**Issues Found**:
1. **Private attribute access**: `list_all_versions` accesses `service._template_versions` directly
2. **In-memory**: VersioningService stores all versions in memory
3. **Global singleton**: Module-level `_versioning_service`

---

### workflows/

**Files**: 3 files, ~942 LOC
**Endpoints**: 12 endpoints

| Endpoint | Method | Path | Business Logic | Data Source | Problems |
|----------|--------|------|----------------|-------------|----------|
| create_workflow | POST | /workflows/ | Create workflow with graph definition | WorkflowRepository (DB) + WorkflowDefinitionAdapter | None |
| list_workflows | GET | /workflows/ | List workflows with pagination | WorkflowRepository (DB) | None |
| get_workflow | GET | /workflows/{id} | Get workflow by ID | WorkflowRepository (DB) | None |
| update_workflow | PUT | /workflows/{id} | Update workflow | WorkflowRepository (DB) + Adapter validation | None |
| delete_workflow | DELETE | /workflows/{id} | Delete workflow | WorkflowRepository (DB) | None |
| execute_workflow | POST | /workflows/{id}/execute | Execute workflow | WorkflowDefinitionAdapter.run() | None |
| validate_workflow | POST | /workflows/{id}/validate | Validate workflow definition | WorkflowDefinitionAdapter | None |
| activate_workflow | POST | /workflows/{id}/activate | Set workflow to active | WorkflowRepository (DB) | None |
| deactivate_workflow | POST | /workflows/{id}/deactivate | Set workflow to inactive | WorkflowRepository (DB) | None |
| get_workflow_graph | GET | /workflows/{id}/graph | Get DAG visualization data | WorkflowRepository (DB) | None |
| update_workflow_graph | PUT | /workflows/{id}/graph | Save DAG layout with positions | WorkflowRepository (DB) | None |
| auto_layout_workflow_graph | POST | /workflows/{id}/graph/layout | Auto-layout DAG (server-side fallback) | WorkflowRepository (DB) + topological sort | None |

**Sprint Reference**: Phase 1, Sprint 1 (core); Sprint 29 (adapter migration); Sprint 133 (graph visualization)
**Assessment**: **COMPLETE** — Best-architected module. Uses real database via SQLAlchemy async. Proper adapter pattern with Agent Framework. Graph visualization with server-side topological sort layout.

**Issues Found**:
1. **No authentication**: No auth middleware on any endpoint
2. **Duplicate dependency**: `get_workflow_repository` defined in both `routes.py` and `graph_routes.py`

---

## Cross-Module Summary

### Endpoint Count by Module

| Module | Endpoints | Assessment | Sprint/Phase |
|--------|-----------|------------|-------------|
| orchestration/ | 28 | MOSTLY COMPLETE | Phase 28 (S96-98, S114-115, S126, S128) |
| patrol/ | 9 | STUB | Phase 23 (S82) |
| performance/ | 11 | MOSTLY COMPLETE | Phase 2 (S12) |
| planning/ | ~46 | COMPLETE | Phase 2 (S10, S17, S24, S31) |
| prompts/ | 11 | COMPLETE | Phase 1 (S3) |
| rootcause/ | 4 | STUB | Phase 23 |
| routing/ | 14 | COMPLETE | Phase 1 (S3) |
| sandbox/ | 6 | COMPLETE | Phase 21 |
| sessions/ | ~20 | MOSTLY COMPLETE | Phase 8-10 (S46, S111) |
| swarm/ | 8 | COMPLETE | Phase 29 |
| templates/ | 11 | COMPLETE | Phase 1 (S4) |
| triggers/ | 9 | COMPLETE | Phase 1 (S3) |
| versioning/ | 14 | COMPLETE | Phase 1 (S4) |
| workflows/ | 12 | COMPLETE | Phase 1 (S1), Phase 5 (S29), Phase 34 (S133) |

**Total**: ~203 endpoints across 48 files (~8,900 LOC)

### Data Source Distribution

| Data Source | Modules |
|-------------|---------|
| **Real Database (PostgreSQL)** | workflows, sessions |
| **Real Redis Cache** | sessions |
| **Real Domain Services** | routing, templates, triggers, versioning, prompts, sandbox |
| **Real Integration Layer** | orchestration (intent routing), swarm (tracker), planning (adapters) |
| **In-Memory Only** | patrol, rootcause, performance (partial) |
| **Hardcoded/Mock** | patrol, rootcause, performance (Phase2 stats), orchestration (metrics) |

### Top Issues Across All Modules

1. **STUB modules**: patrol/ and rootcause/ are entirely mock/hardcoded — no real business logic
2. **In-memory state**: 10 of 14 modules use module-level singleton dicts that lose data on restart
3. **Global mutable state**: Every module uses `_service: Optional[X] = None` pattern
4. **Missing authentication**: Most modules lack auth (exceptions: sessions uses JWT)
5. **os.getenv usage**: orchestration/webhook_routes.py and route_management.py use os.getenv/os.environ instead of pydantic Settings
6. **Direct domain mutation**: prompts/ and triggers/ mutate domain objects directly in update endpoints
7. **NOT IMPLEMENTED**: sessions/attachments returns 501
8. **Blocking code in async**: patrol/execute_check uses `time.sleep()` in async handler
9. **Duplicate code**: Redis client singletons duplicated across sessions/ sub-modules; workflow repo dependency duplicated

### Feature Mapping

| Feature ID | Module(s) | Status |
|-----------|-----------|--------|
| F3 (Intent Routing) | orchestration/ | COMPLETE (real three-tier routing) |
| F4 (Risk Assessment) | orchestration/ | COMPLETE |
| F5 (Guided Dialog) | orchestration/ | COMPLETE (in-memory sessions) |
| F6 (HITL Approval) | orchestration/ | COMPLETE |
| G1 (Patrol Monitoring) | patrol/ | STUB |
| G2 (Root Cause Analysis) | rootcause/ | STUB |
| G3 (Performance Monitoring) | performance/ | PARTIAL |
| H1 (Workflow Management) | workflows/ | COMPLETE (DB-backed) |
| H2 (Template Marketplace) | templates/ | COMPLETE |
| H3 (Version Control) | versioning/ | COMPLETE |
| H4 (Webhook Triggers) | triggers/ | COMPLETE |
| B6 (Session Management) | sessions/ | MOSTLY COMPLETE |
| B7 (Agent Swarm) | swarm/ | COMPLETE |
