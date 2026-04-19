# Testing Landscape Analysis

> V9 Analysis Report | Date: 2026-03-29 | Scope: Full test infrastructure inventory + coverage gap analysis

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Test Inventory](#2-test-inventory)
3. [Coverage Gap Analysis](#3-coverage-gap-analysis)
4. [Test Infrastructure](#4-test-infrastructure)
5. [Test Configuration](#5-test-configuration)
6. [Critical Gaps](#6-critical-gaps)
7. [Recommendations](#7-recommendations)

---

## 1. Executive Summary

| Metric | Count |
|--------|-------|
| **Total Backend Test Files** | 361 (excluding `__init__.py`) |
| **Backend Unit Tests** | 289 files |
| **Backend Integration Tests** | 28 files |
| **Backend E2E Tests** | 23 files |
| **Backend Performance Tests** | 10 files |
| **Backend Security Tests** | 3 files |
| **Backend Load Tests** | 1 file |
| **Backend Mocks** | 3 files |
| **Backend conftest.py** | 4 files |
| **Frontend Unit Tests** | 13 files |
| **Frontend E2E Tests** | 12 files (Playwright) |
| **Source Modules (backend)** | 20 integration + 21 domain + 7 infrastructure + 5 core |
| **Modules with ZERO Unit Tests** | 6 critical modules identified (memory, knowledge, learning, patrol, audit, a2a) |

**Overall Assessment**: Backend has extensive test coverage for integration-layer modules (agent_framework, claude_sdk, hybrid, ag_ui, orchestration, mcp), with additional top-level test directories for auth (5), orchestration (16), swarm (5), and mcp (2). Critical gaps remain in memory/, knowledge/, learning/, a2a/, patrol/, and audit/ integration modules. Frontend testing is narrowly focused on swarm components only -- all other UI areas lack unit tests. Domain layer testing is concentrated in sessions/ with 19 of 24 domain modules untested.

---

### 測試覆蓋金字塔

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    IPA Platform 測試金字塔                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                        ╱╲                                                   │
│                       ╱  ╲     Load Tests (1 file)                         │
│                      ╱ 🔥 ╲    locustfile.py                              │
│                     ╱──────╲                                                │
│                    ╱        ╲   Security Tests (3 files)                   │
│                   ╱   🛡️    ╲                                              │
│                  ╱────────────╲                                             │
│                 ╱              ╲  E2E Tests (23 backend + 12 frontend)     │
│                ╱    🌐 E2E     ╲  Playwright browser automation            │
│               ╱────────────────╲                                           │
│              ╱                  ╲  Performance Tests (10 files)            │
│             ╱    ⚡ Perf         ╲                                          │
│            ╱──────────────────────╲                                        │
│           ╱                        ╲  Integration Tests (28 files)         │
│          ╱    🔗 Integration        ╲  API endpoint testing               │
│         ╱────────────────────────────╲                                     │
│        ╱                              ╲  Unit Tests (289 + 13 files)      │
│       ╱        🧪 Unit Tests          ╲  Backend: 289 files               │
│      ╱          (最大覆蓋面積)          ╲  Frontend: 13 files             │
│     ╱────────────────────────────────────╲                                 │
│                                                                             │
│  Total: 361 backend + 25 frontend = 386 test files                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 測試缺口熱力圖

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    模組測試覆蓋熱力圖                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Integration Modules          Coverage    Status                            │
│  ──────────────────          ────────    ──────                            │
│  agent_framework/        ████████████  ✅ GOOD  (~30+ test files)          │
│  claude_sdk/             ███████████   ✅ GOOD  (~25+ test files)          │
│  hybrid/                 ██████████    ✅ GOOD  (~20+ test files)          │
│  ag_ui/                  █████████     ✅ GOOD  (~15+ test files)          │
│  orchestration/          ████████      ✅ GOOD  (~12+ test files)          │
│  mcp/                    ███████       ✅ FAIR  (~10+ test files)          │
│  llm/                    ████          ⚠️ LOW   (~4 test files)            │
│  swarm/                  ████          ⚠️ PARTIAL (5 top-level unit tests) │
│  memory/                 ░░░░░░░░░░░░  🔴 ZERO  (0 test files)            │
│  knowledge/              ░░░░░░░░░░░░  🔴 ZERO  (0 test files)            │
│  learning/               ░░░░░░░░░░░░  🔴 ZERO  (0 test files)            │
│  a2a/                    ░░░░░░░░░░░░  🔴 ZERO  (0 test files)            │
│  patrol/                 ░░░░░░░░░░░░  🔴 ZERO  (0 test files)            │
│  audit/                  ░░░░░░░░░░░░  🔴 ZERO  (0 test files)            │
│                                                                             │
│  Domain Modules                                                             │
│  ──────────────                                                            │
│  sessions/               ████████████  ✅ GOOD  (19/24 domain tests)       │
│  workflows/              ████           ⚠️ SOME                             │
│  agents/                 ████           ⚠️ SOME                             │
│  其他 18 domain modules  ░░░░░░░░░░░░  🔴 ZERO                             │
│                                                                             │
│  Frontend                                                                   │
│  ────────                                                                  │
│  agent-swarm/ components ████████      ✅ GOOD  (13 unit tests)            │
│  其他所有 UI              ░░░░░░░░░░░░  🔴 ZERO  (0 unit tests)            │
│                                                                             │
│  █ = covered   ░ = NO coverage   🔴 = 6 critical modules with ZERO tests  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Test Inventory

### 2.1 Backend Tests

#### `backend/tests/unit/` -- Root Level (84 test files)

| File | Covers |
|------|--------|
| `test_agent_api.py` | Agent API routes |
| `test_agent_service.py` | Agent domain service |
| `test_approval_gateway.py` | Approval gateway |
| `test_audit.py` | Audit functionality |
| `test_checkpoint_service.py` | Checkpoint service |
| `test_config.py` | Configuration |
| `test_connectors.py` | Connectors |
| `test_devtools.py` | DevTools |
| `test_execution_state_machine.py` | Execution state machine |
| `test_health.py` | Health endpoint |
| `test_learning.py` | Learning module |
| `test_llm_cache.py` | LLM cache |
| `test_notifications.py` | Notifications |
| `test_prompts.py` | Prompt management |
| `test_routing.py` | Routing logic |
| `test_templates.py` | Templates |
| `test_tools.py` | Tool system |
| `test_triggers.py` | Triggers |
| `test_versioning.py` | Versioning |
| `test_workflow_models.py` | Workflow models |
| `test_workflow_resume_service.py` | Workflow resume |
| `test_concurrent_executor.py` | Concurrent execution |
| `test_concurrent_state.py` | Concurrent state |
| `test_parallel_gateway.py` | Parallel gateway |
| `test_deadlock_detector.py` | Deadlock detection |
| `test_concurrent_api.py` | Concurrent API |
| `test_handoff_api.py` | Handoff API |
| `test_multiturn_session.py` | Multi-turn sessions |
| `test_conversation_memory.py` | Conversation memory |
| `test_groupchat_api.py` | GroupChat API |
| `test_task_decomposer.py` | Task decomposition |
| `test_dynamic_planner.py` | Dynamic planner |
| `test_planning_api.py` | Planning API |
| `test_decision_engine.py` | Decision engine |
| `test_trial_error.py` | Trial-error logic |
| `test_sub_executor.py` | Sub-executor |
| `test_recursive_handler.py` | Recursive handler |
| `test_composition_builder.py` | Composition builder |
| `test_context_propagation.py` | Context propagation |
| `test_nested_api.py` | Nested API |
| `test_agent_framework_base.py` | MAF base adapter |
| `test_agent_framework_workflow.py` | MAF workflow adapter |
| `test_agent_framework_mocks.py` | MAF mock system |
| `test_concurrent_builder_adapter.py` | Concurrent builder |
| `test_concurrent_migration.py` | Concurrent migration |
| `test_edge_routing.py` | Edge routing |
| `test_concurrent_adapter_service.py` | Concurrent adapter service |
| `test_handoff_builder_adapter.py` | Handoff builder |
| `test_handoff_migration.py` | Handoff migration |
| `test_handoff_hitl.py` | Handoff HITL |
| `test_groupchat_builder_adapter.py` | GroupChat builder |
| `test_groupchat_migration.py` | GroupChat migration |
| `test_groupchat_orchestrator.py` | GroupChat orchestrator |
| `test_magentic_migration.py` | Magentic migration |
| `test_workflow_executor_adapter.py` | Workflow executor adapter |
| `test_workflow_executor_migration.py` | Workflow executor migration |
| `test_groupchat_adapter.py` | GroupChat adapter |
| `test_groupchat_voting_adapter.py` | GroupChat voting adapter |
| `test_handoff_policy_adapter.py` | Handoff policy adapter |
| `test_handoff_capability_adapter.py` | Handoff capability adapter |
| `test_handoff_context_adapter.py` | Handoff context adapter |
| `test_handoff_service_adapter.py` | Handoff service adapter |
| `test_concurrent_adapter.py` | Concurrent adapter |
| `test_memory_storage.py` | Memory storage |
| `test_nested_workflow_adapter.py` | Nested workflow adapter |
| `test_sprint24_adapters.py` | Sprint 24 adapters |
| `test_nested_workflow_manager.py` | Nested workflow manager |
| `test_workflow_node_executor.py` | Workflow node executor |
| `test_workflow_edge_adapter.py` | Workflow edge adapter |
| `test_workflow_definition_adapter.py` | Workflow definition adapter |
| `test_workflow_context_adapter.py` | Workflow context adapter |
| `test_sequential_orchestration_adapter.py` | Sequential orchestration adapter |
| `test_workflow_status_event_adapter.py` | Workflow status event adapter |
| `test_enhanced_state_machine.py` | Enhanced state machine |
| `test_human_approval_executor.py` | Human approval executor |
| `test_approval_workflow.py` | Approval workflow |
| `test_llm_fallback.py` | LLM fallback |
| `test_execution_events.py` | Execution events |
| `test_agent_executor.py` | Agent executor |
| `test_streaming.py` | Streaming |
| `test_tool_handler.py` | Tool handler |
| `test_sandbox_security.py` | Sandbox security |
| `test_magentic_builder_adapter.py` | Magentic builder adapter |
| `test_mem0_client.py` | mem0 client |

#### `backend/tests/unit/performance/` (5 test files)

| File | Covers |
|------|--------|
| `test_performance_profiler.py` | Performance profiler |
| `test_optimizer.py` | Optimizer |
| `test_concurrent_optimizer.py` | Concurrent optimizer |
| `test_metric_collector.py` | Metric collector |
| `test_benchmark.py` | Benchmark system |

#### `backend/tests/unit/integrations/llm/` (5 test files)

| File | Covers |
|------|--------|
| `test_protocol.py` | LLM protocol abstraction |
| `test_cached.py` | LLM caching layer |
| `test_mock.py` | LLM mock client |
| `test_factory.py` | LLM factory |
| `test_azure_openai.py` | Azure OpenAI client |

#### `backend/tests/unit/integrations/agent_framework/` (10 test files)

| Subdirectory | File | Covers |
|-------------|------|--------|
| `builders/` | `test_planning_llm_injection.py` | Planning LLM injection |
| `assistant/` | `test_models.py` | Assistant models |
| `assistant/` | `test_exceptions.py` | Assistant exceptions |
| `assistant/` | `test_api_routes.py` | Assistant API routes |
| `assistant/` | `test_files.py` | Assistant files |
| `assistant/` | `test_code_interpreter.py` | Code interpreter |
| `tools/` | `test_base.py` | Tool base |
| `tools/` | `test_code_interpreter_tool.py` | Code interpreter tool |
| (root) | `test_acl_interfaces.py` | ACL interfaces |
| (root) | `test_acl_adapter.py` | ACL adapter |

#### `backend/tests/unit/integrations/claude_sdk/` (18 test files)

| Subdirectory | File | Covers |
|-------------|------|--------|
| (root) | `test_config.py` | SDK config |
| (root) | `test_session.py` | SDK session |
| (root) | `test_client.py` | SDK client |
| (root) | `test_query.py` | SDK query |
| (root) | `test_exceptions.py` | SDK exceptions |
| (root) | `test_file_tools.py` | File tools |
| (root) | `test_command_tools.py` | Command tools |
| (root) | `test_hooks.py` | Hooks |
| (root) | `test_web_tools.py` | Web tools |
| `mcp/` | `test_types.py` | MCP types |
| `mcp/` | `test_exceptions.py` | MCP exceptions |
| `mcp/` | `test_servers.py` | MCP servers |
| `mcp/` | `test_manager.py` | MCP manager |
| `mcp/` | `test_discovery.py` | MCP discovery |
| `hybrid/` | `test_capability.py` | Hybrid capability |
| `hybrid/` | `test_selector.py` | Hybrid selector |
| `hybrid/` | `test_orchestrator.py` | Hybrid orchestrator |
| `hybrid/` | `test_synchronizer.py` | Hybrid synchronizer |

#### `backend/tests/unit/integrations/hybrid/` (38 test files)

| Subdirectory | Files | Covers |
|-------------|-------|--------|
| `intent/` | `test_models.py`, `test_router.py` | Intent models, router |
| `intent/analyzers/` | `test_multi_agent.py`, `test_complexity.py` | Multi-agent analyzer, complexity analyzer |
| `intent/classifiers/` | `test_rule_based.py` | Rule-based classifier |
| `context/` | `test_models.py`, `test_bridge.py` | Context models, bridge |
| `context/mappers/` | `test_claude_mapper.py`, `test_maf_mapper.py` | Context mappers |
| `context/sync/` | `test_conflict.py`, `test_events.py`, `test_synchronizer.py` | Conflict resolution, events, sync |
| `execution/` | `test_tool_callback.py`, `test_unified_executor.py` | Tool callback, unified executor |
| `risk/` | `test_models.py`, `test_engine.py`, `test_scorer.py`, `test_operation_analyzer.py`, `test_context_evaluator.py`, `test_pattern_detector.py` | Full risk subsystem |
| `hooks/` | `test_approval_hook.py` | Approval hook |
| `switching/` | `test_models.py`, `test_switcher.py` | Switching models, switcher |
| `switching/triggers/` | `test_complexity.py`, `test_failure.py` | Switching triggers |
| `switching/migration/` | `test_state_migrator.py` | State migrator |
| `checkpoint/` | `test_models.py`, `test_version.py`, `test_serialization.py`, `test_storage.py`, `test_memory_storage.py` | Full checkpoint subsystem |
| (root) | `test_orchestrator_v2.py`, `test_swarm_mode.py`, `test_mediator.py`, `test_routing_handler.py`, `test_execution_handler.py`, `test_backward_compat.py`, `test_redis_checkpoint.py` (in switching/) | V2 orchestrator, swarm mode, mediator, handlers |

#### `backend/tests/unit/integrations/ag_ui/` (17 test files)

| Subdirectory | Files | Covers |
|-------------|-------|--------|
| `events/` | `test_base.py`, `test_lifecycle.py`, `test_message.py`, `test_tool.py`, `test_state.py` | All AG-UI event types |
| `thread/` | `test_models.py`, `test_storage.py`, `test_manager.py` | Thread management |
| (root) | `test_converters.py`, `test_bridge.py` | Converters, bridge |
| `features/` | `test_tool_rendering.py`, `test_human_in_loop.py`, `test_generative_ui.py`, `test_agentic_chat.py` | All AG-UI features |
| `features/advanced/` | `test_predictive.py`, `test_tool_ui.py`, `test_shared_state.py` | Advanced features |

#### `backend/tests/unit/integrations/orchestration/` (16 test files)

| Subdirectory | Files | Covers |
|-------------|-------|--------|
| `input_gateway/` | `test_models.py`, `test_schema_validator.py`, `test_source_handlers.py`, `test_gateway.py` | Input gateway subsystem |
| `intent_router/` | `test_ad_pattern_rules.py`, `test_llm_classifier_real.py`, `test_classification_prompt.py`, `test_llm_cache.py`, `test_llm_fallback.py` | Intent router subsystem |
| (root) | `test_servicenow_webhook.py`, `test_ritm_intent_mapper.py`, `test_azure_semantic_router.py`, `test_embedding_service.py`, `test_route_manager.py`, `test_route_api.py`, `test_incident_handler.py` | Core orchestration components |

#### `backend/tests/unit/integrations/mcp/` (19 test files)

| Subdirectory | Files | Covers |
|-------------|-------|--------|
| `servers/azure/` | `test_client.py`, `test_vm_tools.py`, `test_server.py` | Azure MCP server |
| `servers/n8n/` | `test_n8n_client.py`, `test_n8n_server.py` | n8n MCP server |
| `servers/adf/` | `test_adf_client.py`, `test_adf_server.py` | ADF MCP server |
| `servers/d365/` | `test_d365_auth.py`, `test_d365_server.py`, `test_odata_builder.py`, `test_d365_client.py` | D365 MCP server |
| `security/` | `test_redis_audit.py`, `test_permissions.py`, `test_permission_checker.py`, `test_command_whitelist.py` | MCP security |
| `core/` | `test_mcp_protocol.py`, `test_mcp_client.py`, `test_mcp_transport.py` | MCP core protocol |
| (root) | `test_server_registry.py` | Server registry |

#### `backend/tests/unit/integrations/` -- Other Modules

| Module | Files | Covers |
|--------|-------|--------|
| `correlation/` | `test_correlation_data_source.py`, `test_event_collector.py` | Correlation data source, event collector |
| `rootcause/` | `test_case_repository.py`, `test_case_matcher.py` | Case repository, case matcher |
| `n8n/` | `test_n8n_orchestrator.py`, `test_n8n_monitor.py` | n8n orchestrator, monitor |
| `incident/` | `test_types.py`, `test_recommender.py`, `test_executor.py`, `test_analyzer.py` | Full incident subsystem |
| `shared/` | `test_protocols.py` | Shared protocols |

#### `backend/tests/unit/auth/` (5 test files)

| File | Covers |
|------|--------|
| `test_auth_service.py` | Auth service |
| `test_jwt.py` | JWT token handling |
| `test_password.py` | Password hashing |
| `test_rate_limit.py` | Rate limiting |
| `test_require_auth.py` | Auth requirement decorator |

#### `backend/tests/unit/orchestration/` (16 test files)

> **Note**: These are top-level orchestration tests, separate from `integrations/orchestration/` tests.

| File | Covers |
|------|--------|
| `test_approval_handler.py` | Approval handler |
| `test_business_intent_router.py` | Business intent router |
| `test_dialog_context_manager.py` | Dialog context manager |
| `test_dialog_engine_deep.py` | Dialog engine deep tests |
| `test_guided_dialog.py` | Guided dialog |
| `test_hitl.py` | HITL core |
| `test_hitl_controller_deep.py` | HITL controller deep tests |
| `test_hitl_notification.py` | HITL notification |
| `test_input_gateway.py` | Input gateway |
| `test_layer_contracts.py` | Layer contracts |
| `test_llm_classifier.py` | LLM classifier |
| `test_orchestration_metrics.py` | Orchestration metrics |
| `test_pattern_matcher.py` | Pattern matcher |
| `test_risk_assessor.py` | Risk assessor |
| `test_schema_validator.py` | Schema validator |
| `test_semantic_router.py` | Semantic router |

#### `backend/tests/unit/swarm/` (5 test files)

| File | Covers |
|------|--------|
| `test_emitter.py` | Event emitter |
| `test_event_types.py` | Event type definitions |
| `test_models.py` | Swarm data models |
| `test_thinking_events.py` | Thinking events |
| `test_tracker.py` | Swarm progress tracker |

#### `backend/tests/unit/mcp/` (2 test files)

> **Note**: These are top-level MCP tests, separate from `integrations/mcp/` tests.

| File | Covers |
|------|--------|
| `test_servicenow_client.py` | ServiceNow client |
| `test_servicenow_server.py` | ServiceNow server |

#### `backend/tests/unit/api/` (15 test files)

| Subdirectory | Files | Covers |
|-------------|-------|--------|
| `v1/code_interpreter/` | `test_visualization.py` | Code interpreter visualization |
| `v1/sessions/` | `test_chat.py` | Session chat API |
| `v1/claude_sdk/` | `test_routes.py`, `test_tools_routes.py`, `test_hooks_routes.py`, `test_mcp_routes.py`, `test_hybrid_routes.py`, `test_intent_routes.py` | Claude SDK API routes |
| `v1/hybrid/` | `test_context_routes.py`, `test_risk_routes.py`, `test_switch_routes.py` | Hybrid API routes |
| `v1/ag_ui/` | `test_routes.py`, `test_approval_routes.py` | AG-UI API routes |
| `n8n/` | `test_n8n_webhook.py` | n8n webhook API |
| `workflows/` | `test_graph_routes.py` | Workflow graph API |

#### `backend/tests/unit/domain/` (5 test files)

| Subdirectory | Files | Covers |
|-------------|-------|--------|
| `sessions/` | `test_approval.py`, `test_bridge.py`, `test_error_handler.py`, `test_recovery.py`, `test_metrics.py` | Session domain logic |

#### `backend/tests/unit/infrastructure/` (11 test files)

| Subdirectory | Files | Covers |
|-------------|-------|--------|
| (root) | `test_storage_backends.py`, `test_storage_factory.py`, `test_distributed_lock.py` | Storage, distributed lock |
| `storage/` | `test_storage_factories_sprint120.py` | Sprint 120 storage factories |
| `checkpoint/` | `test_protocol.py`, `test_unified_registry.py` | Checkpoint protocol, registry |
| `checkpoint/adapters/` | `test_hybrid_adapter.py`, `test_agent_framework_adapter.py`, `test_domain_adapter.py`, `test_session_recovery_adapter.py`, `test_multi_provider_integration.py` | Checkpoint adapters |

#### `backend/tests/unit/core/` (7 test files)

| File | Covers |
|------|--------|
| `test_server_config.py` | Server configuration |
| `test_observability_setup.py` | Observability setup |
| `test_spans.py` | Trace spans |
| `test_metrics.py` | Metrics system |
| `test_request_id_middleware.py` | Request ID middleware |
| `test_sensitive_filter.py` | Sensitive data filter |
| `test_structured_logging.py` | Structured logging |

#### `backend/tests/integration/` (28 test files)

| Subdirectory | Files | Covers |
|-------------|-------|--------|
| (root) | `test_execution_adapter_e2e.py` | Execution adapter |
| (root) | `test_sprint29_api_routes.py` | Sprint 29 routes |
| (root) | `test_phase3_integration.py` | Phase 3 integration |
| (root) | `test_execution_service_migration.py` | Execution service migration |
| (root) | `test_memory_api.py` | Memory API |
| (root) | `test_business_intent_router.py` | Business intent router |
| (root) | `test_e2e_smoke.py` | Smoke tests |
| `api/v1/sessions/` | `test_websocket.py` | WebSocket sessions |
| `hybrid/` | `test_intent_router_integration.py`, `test_orchestrator_v2_integration.py`, `test_context_bridge_integration.py`, `test_phase14_integration.py`, `test_swarm_routing.py` | Hybrid integration |
| `orchestration/` | `test_e2e_hitl.py`, `test_e2e_dialog.py`, `test_e2e_routing.py`, `test_three_layer_real.py` | Orchestration E2E |
| `swarm/` | `test_bridge_integration.py`, `test_api.py` | Swarm integration |
| `security/` | `test_phase31_integration.py` | Phase 31 security |
| `mcp/` | `test_ldap_ad_operations.py`, `test_servicenow_api.py` | MCP integrations |
| `n8n/` | `test_n8n_integration.py`, `test_n8n_mode3.py` | n8n integration |
| `adf/` | `test_adf_integration.py` | ADF integration |
| `d365/` | `test_d365_integration.py` | D365 integration |
| `correlation/` | `test_correlation_real.py` | Correlation integration |
| `rootcause/` | `test_rootcause_real.py` | Root cause integration |

#### `backend/tests/e2e/` (23 test files)

| Subdirectory | Files | Covers |
|-------------|-------|--------|
| (root) | `test_agent_execution.py`, `test_human_approval.py`, `test_n8n_integration.py`, `test_workflow_lifecycle.py` | Core workflows |
| (root) | `test_complete_workflow.py`, `test_approval_workflow.py`, `test_concurrent_workflow.py` | Complex workflows |
| (root) | `test_handoff_workflow.py`, `test_groupchat_workflow.py`, `test_error_recovery.py` | Handoff, groupchat, recovery |
| (root) | `test_llm_integration.py`, `test_ai_autonomous_decision.py`, `test_session_agent_integration.py` | LLM & AI E2E |
| (root) | `test_incident_pipeline.py`, `test_n8n_e2e_verification.py`, `test_incident_e2e_verification.py` | Incident pipeline |
| (root) | `test_cross_functional_integration.py`, `test_adf_e2e_verification.py` | Cross-functional |
| `ag_ui/` | `test_full_flow.py` | AG-UI full flow |
| `swarm/` | `test_swarm_execution.py` | Swarm execution |
| `orchestration/` | `test_ad_scenario_fixtures.py`, `test_ad_scenario_e2e.py`, `test_semantic_routing_e2e.py` | Orchestration scenarios |

#### `backend/tests/performance/` (10 test files)

| Subdirectory | Files | Covers |
|-------------|-------|--------|
| (root) | `test_workflow_executor_performance.py`, `test_api_performance.py`, `test_concurrent_performance.py` | Workflow, API, concurrency |
| (root) | `test_memory_usage.py`, `test_llm_performance.py`, `test_router_performance.py`, `test_routing_performance.py` | Memory, LLM, routing |
| (root) | `test_sprint127_benchmarks.py` | Sprint 127 benchmarks |
| `swarm/` | `test_swarm_performance.py` | Swarm performance |
| `orchestration/` | `test_routing_performance.py` | Orchestration routing |

#### `backend/tests/security/` (3 test files)

| File | Covers |
|------|--------|
| `test_authentication.py` | Authentication security |
| `test_authorization.py` | Authorization security |
| `test_input_validation.py` | Input validation security |

#### `backend/tests/load/` (1 test file)

| File | Covers |
|------|--------|
| `locustfile.py` | Load test scenarios |

### 2.2 Frontend Tests

#### `frontend/src/` -- Unit Tests (13 files, Vitest)

| File | Covers |
|------|--------|
| `components/unified-chat/agent-swarm/__tests__/SwarmHeader.test.tsx` | Swarm header component |
| `components/unified-chat/agent-swarm/__tests__/OverallProgress.test.tsx` | Overall progress display |
| `components/unified-chat/agent-swarm/__tests__/WorkerCard.test.tsx` | Worker card component |
| `components/unified-chat/agent-swarm/__tests__/WorkerCardList.test.tsx` | Worker card list |
| `components/unified-chat/agent-swarm/__tests__/SwarmStatusBadges.test.tsx` | Status badges |
| `components/unified-chat/agent-swarm/__tests__/AgentSwarmPanel.test.tsx` | Main swarm panel |
| `components/unified-chat/agent-swarm/__tests__/useWorkerDetail.test.ts` | Worker detail hook |
| `components/unified-chat/agent-swarm/__tests__/ToolCallItem.test.tsx` | Tool call item |
| `components/unified-chat/agent-swarm/__tests__/MessageHistory.test.tsx` | Message history |
| `components/unified-chat/agent-swarm/__tests__/WorkerDetailDrawer.test.tsx` | Worker detail drawer |
| `components/unified-chat/agent-swarm/__tests__/WorkerActionList.test.tsx` | Worker action list |
| `components/unified-chat/agent-swarm/__tests__/ExtendedThinkingPanel.test.tsx` | Extended thinking panel |
| `stores/__tests__/swarmStore.test.ts` | Swarm Zustand store |

#### `frontend/e2e/` + `frontend/tests/e2e/` -- E2E Tests (12 files, Playwright)

| File | Covers |
|------|--------|
| `e2e/approvals.spec.ts` | Approval workflows |
| `e2e/dashboard.spec.ts` | Dashboard page |
| `e2e/workflows.spec.ts` | Workflow management |
| `e2e/ag-ui/agentic-chat.spec.ts` | AG-UI agentic chat |
| `e2e/ag-ui/tool-rendering.spec.ts` | AG-UI tool rendering |
| `e2e/ag-ui/hitl.spec.ts` | AG-UI human-in-the-loop |
| `e2e/ag-ui/generative-ui.spec.ts` | AG-UI generative UI |
| `e2e/ag-ui/tool-ui.spec.ts` | AG-UI tool UI |
| `e2e/ag-ui/shared-state.spec.ts` | AG-UI shared state |
| `e2e/ag-ui/predictive-state.spec.ts` | AG-UI predictive state |
| `e2e/ag-ui/integration.spec.ts` | AG-UI integration |
| `tests/e2e/swarm.spec.ts` | Agent swarm E2E |

---

## 3. Coverage Gap Analysis

### 3.1 Integration Modules (`backend/src/integrations/`)

| Module | Source Files | Has Unit Tests | Test File Count | Coverage |
|--------|-------------|----------------|-----------------|----------|
| `agent_framework/` | ~53 | YES | 10 | PARTIAL -- builders/ lightly covered, memory/multiturn under-tested |
| `claude_sdk/` | ~47 | YES | 18 | GOOD -- config, session, client, tools, MCP, hybrid |
| `hybrid/` | ~60 | YES | 38 | GOOD -- intent, context, risk, switching, checkpoint all covered |
| `orchestration/` | ~39 | YES | 16 + 16 top-level | GOOD -- input_gateway + intent_router under integrations/; guided_dialog, hitl, risk_assessor covered in top-level `tests/unit/orchestration/` |
| `ag_ui/` | ~18 | YES | 17 | GOOD -- events, thread, features, advanced all covered |
| `mcp/` | ~43 | YES | 19 + 2 top-level | MODERATE -- Azure, n8n, ADF, D365, security, core, ServiceNow covered; Filesystem, LDAP, Shell, SSH missing |
| `llm/` | ~6 | YES | 5 | GOOD -- protocol, cached, mock, factory, azure_openai |
| `swarm/` | ~7 | YES (top-level) | 5 (in `tests/unit/swarm/`) | PARTIAL -- emitter, event_types, models, thinking_events, tracker covered; worker_executor.py, task_decomposer.py still untested |
| `memory/` | ~5 | NO | 0 | **ZERO** -- unified_memory.py, embeddings.py, types.py untested |
| `knowledge/` | ~8 | NO | 0 | **ZERO** -- rag_pipeline.py, vector_store.py, retriever.py, chunker.py all untested |
| `learning/` | ~5 | NO | 0 | **ZERO** -- despite `test_learning.py` in root unit/, no dedicated module tests |
| `patrol/` | ~10 | NO | 0 | **ZERO** -- continuous monitoring completely untested |
| `audit/` | ~4 | NO | 0 | **ZERO** -- despite `test_audit.py` in root unit/, no dedicated module tests |
| `a2a/` | ~3 | NO | 0 | **ZERO** -- Agent-to-Agent protocol untested |
| `correlation/` | ~4 | YES | 2 | PARTIAL -- data_source + event_collector |
| `rootcause/` | ~3 | YES | 2 | PARTIAL -- case_repository + case_matcher |
| `n8n/` | varies | YES | 2 | PARTIAL -- orchestrator + monitor |
| `incident/` | varies | YES | 4 | GOOD -- types, recommender, executor, analyzer |
| `shared/` | varies | YES | 1 | MINIMAL -- protocols only |
| `contracts/` | varies | NO | 0 | **ZERO** |

### 3.2 Domain Modules (`backend/src/domain/`)

| Module | Has Unit Tests | Test File Count | Notes |
|--------|----------------|-----------------|-------|
| `agents/` | NO (dedicated) | 0 | Covered partially by root `test_agent_service.py` |
| `audit/` | NO (dedicated) | 0 | Covered partially by root `test_audit.py` |
| `auth/` | YES (in `tests/unit/auth/`) | 5 | Covered by top-level auth tests (jwt, password, auth_service, rate_limit, require_auth) |
| `chat_history/` | NO | 0 | **GAP** |
| `checkpoints/` | NO (dedicated) | 0 | Covered by root `test_checkpoint_service.py` |
| `connectors/` | NO (dedicated) | 0 | Covered by root `test_connectors.py` |
| `devtools/` | NO (dedicated) | 0 | Covered by root `test_devtools.py` |
| `executions/` | NO (dedicated) | 0 | Covered by root `test_execution_state_machine.py` |
| `files/` | NO | 0 | **GAP** |
| `learning/` | NO (dedicated) | 0 | Covered by root `test_learning.py` |
| `notifications/` | NO (dedicated) | 0 | Covered by root `test_notifications.py` |
| `orchestration/` | NO | 0 | **GAP** |
| `prompts/` | NO (dedicated) | 0 | Covered by root `test_prompts.py` |
| `routing/` | NO (dedicated) | 0 | Covered by root `test_routing.py` |
| `sandbox/` | NO | 0 | **GAP** |
| `sessions/` | YES | 5 | approval, bridge, error_handler, recovery, metrics |
| `tasks/` | NO | 0 | **GAP** |
| `templates/` | NO (dedicated) | 0 | Covered by root `test_templates.py` |
| `triggers/` | NO (dedicated) | 0 | Covered by root `test_triggers.py` |
| `versioning/` | NO (dedicated) | 0 | Covered by root `test_versioning.py` |
| `workflows/` | NO (dedicated) | 0 | Covered by root `test_workflow_models.py` |

**Notes**: Many domain modules have "legacy" test files at `tests/unit/test_*.py` (root level) that were written early in the project. These provide some coverage but are not organized under `tests/unit/domain/`. Only `sessions/` has properly structured domain-level tests.

### 3.3 Infrastructure Modules (`backend/src/infrastructure/`)

| Module | Has Unit Tests | Test File Count | Notes |
|--------|----------------|-----------------|-------|
| `cache/` | NO | 0 | **GAP** -- no cache layer tests |
| `checkpoint/` | YES | 7 | GOOD -- protocol, registry, 5 adapters |
| `database/` | NO | 0 | **GAP** -- no database layer tests |
| `distributed_lock/` | YES | 1 | `test_distributed_lock.py` |
| `messaging/` | NO | 0 | **GAP** -- RabbitMQ layer untested |
| `storage/` | YES | 3 | `test_storage_backends.py`, `test_storage_factory.py` (root), `test_storage_factories_sprint120.py` (subdirectory) |
| `workers/` | NO | 0 | **GAP** |
| `redis_client.py` | NO | 0 | **GAP** |

### 3.4 Core Modules (`backend/src/core/`)

| Module | Has Unit Tests | Test File Count | Notes |
|--------|----------------|-----------------|-------|
| `config.py` | YES (root) | 1 | Root `test_config.py` |
| `server_config.py` | YES | 1 | `test_server_config.py` |
| `auth.py` | NO | 0 | **GAP** |
| `factories.py` | NO | 0 | **GAP** |
| `logging/` | YES | 2 | `test_sensitive_filter.py`, `test_structured_logging.py` |
| `observability/` | YES | 3 | `test_observability_setup.py`, `test_spans.py`, `test_metrics.py` |
| `performance/` | YES | 5 | Full coverage via `unit/performance/` |
| `sandbox/` | NO (dedicated) | 0 | Root `test_sandbox_security.py` only |
| `security/` | YES (in `tests/unit/auth/`) | 5 | jwt.py, password.py covered by `tests/unit/auth/test_jwt.py`, `test_password.py`; also test_auth_service, test_rate_limit, test_require_auth |
| `sandbox_config.py` | NO | 0 | **GAP** |

### 3.5 Frontend Coverage

| Area | Has Unit Tests | Has E2E Tests | Gap Level |
|------|---------------|---------------|-----------|
| Agent Swarm components | YES (12 files) | NO | LOW |
| Swarm store | YES (1 file) | NO | LOW |
| Unified Chat components (~27 files) | NO | NO | **CRITICAL** |
| AG-UI components | NO | YES (7 files) | MODERATE |
| DevUI components (~15 files) | NO | NO | **HIGH** |
| Layout components | NO | NO | **HIGH** |
| Auth components | NO | NO | **HIGH** |
| Pages (11 modules) | NO | PARTIAL (3 files) | **HIGH** |
| Hooks (17 hooks) | NO | NO | **CRITICAL** |
| Stores (unifiedChatStore, authStore) | NO | NO | **HIGH** |
| API client (client.ts, endpoints) | NO | NO | **CRITICAL** |

---

## 4. Test Infrastructure

### 4.1 Backend Fixtures (`backend/tests/conftest.py`)

**Root conftest.py provides**:

| Fixture | Type | Description |
|---------|------|-------------|
| `client` | Function | FastAPI `TestClient` from `main:app` (lazy import) |
| `api_prefix` | Function | Returns `/api/v1` string |

**Custom Markers**:

| Marker | Purpose |
|--------|---------|
| `@pytest.mark.e2e` | End-to-end tests requiring real API |
| `@pytest.mark.performance` | Performance benchmark tests |
| `@pytest.mark.slow` | Long-running tests |
| `@pytest.mark.integration` | Integration tests |

**Commented-out fixtures** (stubs for future implementation):
- `db_session` -- Database session fixture (async)
- `sample_user` -- Sample user data
- `mock_agent_executor` -- Agent executor mock
- `mock_workflow` -- Workflow mock
- `redis_client` -- Redis client fixture

**E2E conftest** (`backend/tests/e2e/conftest.py`), **orchestration conftest** (`backend/tests/e2e/orchestration/conftest.py`), and **security conftest** (`backend/tests/security/conftest.py`) exist but were not read for this analysis.

**Shared mocks** (`backend/tests/mocks/`):
- `agent_framework_mocks.py` -- Reusable MAF mock objects
- `llm.py` -- LLM mock client
- `orchestration.py` -- Orchestration mock objects

### 4.2 Frontend Playwright Fixtures (`frontend/e2e/ag-ui/fixtures.ts`)

**Page Object: `AGUITestPage`**

A comprehensive Page Object Model encapsulating AG-UI demo page interactions:

| Category | Locators |
|----------|----------|
| **Main Elements** | `pageContainer`, `tabNavigation`, `eventLogPanel` |
| **Tabs** (7) | `chatTab`, `toolTab`, `hitlTab`, `generativeTab`, `toolUITab`, `stateTab`, `predictiveTab` |
| **Chat** | `messageInput`, `sendButton`, `chatContainer` |
| **Approval** | `approvalDialog`, `approvalBanner` |

**Methods**:

| Method | Description |
|--------|-------------|
| `goto()` | Navigate to `/ag-ui-demo` and wait for container |
| `switchTab(tabId)` | Switch to feature tab by ID |
| `sendMessage(text)` | Fill input and click send |
| `waitForAssistantMessage()` | Wait for assistant response (10s timeout) |
| `getEventCount()` | Count event log entries |
| `approveToolCall(id)` | Click approve button for tool call |
| `rejectToolCall(id)` | Click reject button for tool call |
| `getRiskBadge(level)` | Get risk badge locator by level |
| `isStreaming()` | Check streaming indicator visibility |
| `waitForStreamingComplete()` | Wait for streaming to end (30s timeout) |
| `getMessages()` | Extract all visible message bubbles with role and content |
| `toggleTask(taskId)` | Toggle task checkbox in predictive demo |

**Test Extension**: Exports extended `test` fixture with pre-initialized `agUiPage` that auto-navigates to the demo page.

---

## 5. Test Configuration

### 5.1 Backend (pytest via `pyproject.toml`)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_functions = "test_*"
python_classes = "Test*"
asyncio_mode = "auto"
addopts = "-v --tb=short --cov=src --cov-report=term-missing --cov-report=xml"
```

| Setting | Value | Notes |
|---------|-------|-------|
| **Test discovery path** | `tests/` | All subdirectories scanned |
| **File pattern** | `test_*.py` | Standard Python convention |
| **Async mode** | `auto` | pytest-asyncio auto-mode -- async tests run without explicit marker |
| **Verbosity** | `-v` | Verbose output |
| **Traceback** | `--tb=short` | Short traceback format |
| **Coverage source** | `src/` | All backend source |
| **Coverage reports** | `term-missing` + `xml` | Terminal + XML (CI compatible) |
| **Deprecation warnings** | Ignored | Filtered out |

**Coverage Configuration**:

```toml
[tool.coverage.run]
source = ["src"]
omit = ["*/tests/*", "*/__pycache__/*", "*/migrations/*"]

[tool.coverage.report]
fail_under = 80
exclude_lines = ["pragma: no cover", "def __repr__", "raise NotImplementedError", "if TYPE_CHECKING:"]
```

| Setting | Value |
|---------|-------|
| **Minimum coverage** | 80% (enforced) |
| **Omitted paths** | tests, pycache, migrations |
| **Excluded patterns** | `pragma: no cover`, `__repr__`, `NotImplementedError`, `TYPE_CHECKING` |

### 5.2 Frontend (Vitest + Playwright via `package.json`)

**Test Scripts**:

| Script | Command | Description |
|--------|---------|-------------|
| `test` | `vitest` | Run unit tests in watch mode |
| `test:ui` | `vitest --ui` | Vitest browser UI |
| `test:coverage` | `vitest --coverage` | Coverage report (v8 provider) |
| `test:e2e` | `playwright test` | Playwright E2E tests |

**Testing Dependencies**:

| Package | Version | Purpose |
|---------|---------|---------|
| `vitest` | ^1.1.3 | Unit test runner |
| `@vitest/ui` | ^1.1.3 | Browser UI for tests |
| `@vitest/coverage-v8` | ^1.1.3 | V8 coverage provider |
| `@testing-library/react` | ^14.1.2 | React component testing |
| `@testing-library/jest-dom` | ^6.2.0 | DOM matchers |
| `@playwright/test` | ^1.40.1 | E2E browser testing |
| `jsdom` | ^23.2.0 | DOM simulation for unit tests |

---

## 6. Critical Gaps

### 6.1 CRITICAL -- Modules with ZERO Test Coverage

#### `integrations/swarm/` -- Agent Swarm System (Phase 29)

| Source File | Purpose | Risk | Test Status |
|-------------|---------|------|-------------|
| `worker_executor.py` | Worker agent execution logic | **HIGH** -- core execution path | **UNTESTED** |
| `tracker.py` | Swarm progress tracking | MEDIUM | Covered by `tests/unit/swarm/test_tracker.py` |
| `task_decomposer.py` | Task decomposition into subtasks | **HIGH** -- affects task distribution | **UNTESTED** |
| `worker_roles.py` | Worker role definitions | LOW | **UNTESTED** |
| `models.py` | Swarm data models | MEDIUM | Covered by `tests/unit/swarm/test_models.py` |
| `swarm_integration.py` | Swarm integration layer | **HIGH** -- bridges to rest of system | **UNTESTED** |

**Unit tests exist** in `tests/unit/swarm/` (5 files: emitter, event_types, models, thinking_events, tracker). **Integration tests exist** (`tests/integration/swarm/test_bridge_integration.py`, `test_api.py`) and **E2E tests exist** (`tests/e2e/swarm/test_swarm_execution.py`). Remaining gap: worker_executor, task_decomposer, swarm_integration.

#### `integrations/memory/` -- Memory System (mem0)

| Source File | Purpose | Risk |
|-------------|---------|------|
| `unified_memory.py` | Unified memory abstraction | **HIGH** -- data persistence |
| `embeddings.py` | Embedding generation | MEDIUM |
| `mem0_client.py` | mem0 client wrapper | MEDIUM (has root `test_mem0_client.py`) |
| `types.py` | Memory type definitions | LOW |

#### `integrations/knowledge/` -- Knowledge/RAG System

| Source File | Purpose | Risk |
|-------------|---------|------|
| `rag_pipeline.py` | RAG pipeline orchestration | **CRITICAL** -- core RAG flow |
| `vector_store.py` | Vector database operations | **HIGH** -- data retrieval |
| `retriever.py` | Document retrieval | **HIGH** -- search quality |
| `chunker.py` | Document chunking | MEDIUM |
| `document_parser.py` | Document parsing | MEDIUM |
| `embedder.py` | Embedding generation | MEDIUM |
| `agent_skills.py` | Agent skill definitions | LOW |

#### `integrations/patrol/` -- Continuous Monitoring (Phase 23)

10 source files with **zero test coverage** at any level (unit, integration, or E2E).

#### `integrations/a2a/` -- Agent-to-Agent Protocol

3 source files with **zero test coverage** at any level.

#### `integrations/audit/` -- Audit Integration

4 source files with no dedicated integration-level tests (only root `test_audit.py` exists for domain layer).

#### `integrations/contracts/` -- Integration Contracts

No test coverage.

### 6.2 HIGH -- Domain Layer Gaps

The following domain modules have **no dedicated test files** under `tests/unit/domain/`:

- `domain/auth/` -- Authentication logic
- `domain/chat_history/` -- Chat history management
- `domain/files/` -- File management
- `domain/orchestration/` -- Domain-level orchestration
- `domain/sandbox/` -- Sandbox management
- `domain/tasks/` -- Task management

**Note**: Some are partially covered by root-level `test_*.py` files, but those tests are not organized under `tests/unit/domain/` and may not test domain logic thoroughly.

### 6.3 HIGH -- Infrastructure Gaps

- `infrastructure/cache/` -- No cache tests
- `infrastructure/database/` -- No database layer tests
- `infrastructure/messaging/` -- No messaging (RabbitMQ) tests
- `infrastructure/workers/` -- No worker tests
- `infrastructure/redis_client.py` -- No Redis client tests

### 6.4 HIGH -- Frontend Gaps

- **0 unit tests** for 27+ unified-chat components (excluding swarm)
- **0 unit tests** for 17 custom hooks (`useAGUI`, `useApprovalFlow`, `useUnifiedChat`, etc.)
- **0 unit tests** for API client (`client.ts`, endpoints)
- **0 unit tests** for DevUI (15 components), auth components, layout components
- **0 unit tests** for non-swarm stores (`unifiedChatStore`, `authStore`)
- Only AG-UI area has meaningful E2E tests; other pages have minimal coverage

### 6.5 MEDIUM -- Sessions Streaming Gap

`domain/sessions/streaming.py` exists but has **no dedicated test**. The `tests/unit/test_streaming.py` in root may partially cover it, but given SSE streaming is a critical real-time feature, a dedicated test is needed.

---

## 7. Recommendations

### 7.1 Priority 1 -- Critical Module Unit Tests

| Module | Recommended Action | Estimated Tests |
|--------|-------------------|-----------------|
| `integrations/swarm/` | Add unit tests for worker_executor, task_decomposer, swarm_integration | 15-20 tests |
| `integrations/knowledge/` | Add unit tests for rag_pipeline, vector_store, retriever, chunker | 20-25 tests |
| `integrations/memory/` | Add unit tests for unified_memory, embeddings | 10-15 tests |
| `integrations/patrol/` | Add unit tests for all 10 files | 20-30 tests |
| `integrations/a2a/` | Add unit tests for A2A protocol | 8-12 tests |

### 7.2 Priority 2 -- Infrastructure Tests

| Module | Recommended Action |
|--------|-------------------|
| `infrastructure/cache/` | Test cache hit/miss, TTL, invalidation |
| `infrastructure/database/` | Test connection pool, transaction handling |
| `infrastructure/messaging/` | Test RabbitMQ publish/subscribe patterns |

### 7.3 Priority 3 -- Frontend Test Expansion

| Area | Recommended Action |
|------|-------------------|
| Hooks (17) | Unit tests for `useUnifiedChat`, `useAGUI`, `useApprovalFlow`, `useOrchestration` |
| API client | Test fetch wrapper, error handling, auth headers |
| Unified Chat | Component tests for ChatArea, ChatInput, MessageList, InlineApproval |
| Stores | Test `unifiedChatStore`, `authStore` state transitions |

### 7.4 Priority 4 -- Test Organization Improvement

- **Restructure root-level unit tests**: Move `tests/unit/test_*.py` into proper subdirectories matching source structure (`tests/unit/domain/`, `tests/unit/integrations/`, etc.)
- **Add conftest fixtures**: Implement the commented-out `db_session`, `redis_client`, `mock_agent_executor` fixtures
- **Frontend test structure**: Create `__tests__/` directories in each component folder, not just `agent-swarm/`

### 7.5 Test Count Summary

| Category | Current Files | Estimated Need | Gap |
|----------|--------------|----------------|-----|
| Backend Unit | ~289 | ~360 | ~71 files |
| Backend Integration | ~28 | ~35 | ~7 files |
| Backend E2E | ~23 | ~30 | ~7 files |
| Frontend Unit | 13 | ~60 | ~47 files |
| Frontend E2E | 12 | ~20 | ~8 files |
| **Total** | **~365** | **~505** | **~140 files** |

---

## Phase 45-47 Test Additions (2026-04-19 sync)

**Scope**: 162 commits, 194 source files changed since commit `50ec420`.
**Backend tests**: 386 → **460** (+74 files).

### New Backend Test Directories

| Directory | Files | Purpose |
|-----------|-------|---------|
| `backend/tests/unit/orchestration/pipeline/` | 7 files | Phase 45 Sprint 158 E2E pipeline tests (`f1923d3`) |
| `backend/tests/unit/api/v1/experts/` | 2 files (+ `__init__.py`) | Phase 46 Expert CRUD API tests |
| `backend/tests/unit/integrations/orchestration/experts/` | 3 files (+ `__init__.py`) | Phase 46 Expert registry/bridge/domain_tools tests |

### New Backend Test Files

| File | Coverage Target |
|------|----------------|
| `tests/unit/orchestration/pipeline/test_context.py` | `PipelineContext` dataclass lifecycle |
| `tests/unit/orchestration/pipeline/test_pipeline_e2e.py` | End-to-end pipeline execution |
| `tests/unit/orchestration/pipeline/test_service.py` | `OrchestrationPipelineService.run()` |
| `tests/unit/orchestration/pipeline/test_step6_dispatch.py` | Step 6 LLM route + dispatch integration |
| `tests/unit/orchestration/pipeline/test_step8_api.py` | Step 8 postprocess API integration |
| `tests/unit/orchestration/pipeline/test_steps.py` | Step base class contract |
| `tests/unit/orchestration/pipeline/test_steps_3_5.py` | Steps 3 (intent) and 5 (HITL gate) |
| `tests/unit/api/v1/experts/test_routes.py` | Expert GET/POST routes |
| `tests/unit/api/v1/experts/test_crud_routes.py` | Expert PUT/DELETE/reload |
| `tests/unit/integrations/orchestration/experts/test_bridge.py` | Legacy worker_roles fallback |
| `tests/unit/integrations/orchestration/experts/test_domain_tools.py` | TEAM_TOOLS, DOMAIN_TOOLS, resolve_tools() |
| `tests/unit/integrations/orchestration/experts/test_registry.py` | YAML loading + validation |
| `tests/unit/test_sprint166_dynamic_agents.py` | Sprint 166 `_infer_complexity()` rules + MAX_SUBTASKS cap |
| `tests/unit/orchestration/test_business_intent_router.py` | **Modified** — new completeness/routes YAML configs |

### Frontend Test Changes

- **Added**: `frontend/src/stores/__tests__/agentTeamStore.test.ts` (replaces `swarmStore.test.ts`)
- **Deleted**: `frontend/src/stores/__tests__/swarmStore.test.ts`
- **Renamed** (agent-swarm → agent-team, rename similarity 51-100%): 15+ test files including `AgentCard.test.tsx`, `AgentDetailDrawer.test.tsx`, `AgentTeamHeader.test.tsx`, `AgentTeamPanel.test.tsx`, `AgentActionList.test.tsx`, `ExtendedThinkingPanel.test.tsx`, `MessageHistory.test.tsx`, `OverallProgress.test.tsx`, `ToolCallItem.test.tsx`, `useAgentDetail.test.ts`
- **New**: `AgentCardList.test.tsx`, `AgentTeamStatusBadges.test.tsx`

### Updated Test Count Table

| Category | V9 Baseline | Phase 47 Actual | Delta |
|----------|-------------|-----------------|-------|
| Backend unit tests | 289 | **~363** | +74 |
| Backend integration | 28 | ~28 | — |
| Backend E2E | 23 | ~23 | — |
| Frontend unit/E2E | 25 | ~26 | +1 (net: agentTeamStore − swarmStore) |
| **Total** | **386** | **~460** | **+74** |

---

*Analysis generated: 2026-03-29 | Method: Full glob scan of test directories + source module cross-reference*
*Phase 45-47 test additions appended 2026-04-19 from `git diff 50ec420..HEAD -- backend/tests/`.*
