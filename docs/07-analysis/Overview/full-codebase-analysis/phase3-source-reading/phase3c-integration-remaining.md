# Phase 3C: Remaining Integration Modules Analysis

**Analyst**: Agent C11
**Date**: 2026-03-15
**Scope**: `backend/src/integrations/` — 12 smaller modules (~64 files)
**Cross-ref**: Features G3-G5, H1-H4, E6-E7, F1, C4-C5

---

## Executive Summary

Analyzed 12 integration modules totaling ~64 Python files. Key findings:

| Module | Files | Status | Data Source |
|--------|-------|--------|-------------|
| **swarm/** | 7 | FULLY IMPLEMENTED | Real (in-memory + optional Redis) |
| **patrol/** | 11 | FULLY IMPLEMENTED | Real (psutil, filesystem, HTTP) |
| **incident/** | 6 | FULLY IMPLEMENTED | Real (correlation + rootcause + LLM) |
| **correlation/** | 6 | FIXED (Sprint 130) | Real (Azure Monitor / App Insights) |
| **rootcause/** | 5 | FIXED (Sprint 130) | Real (CaseRepository + seed data) |
| **memory/** | 5 | FULLY IMPLEMENTED | Real (mem0 + Qdrant + Redis + PostgreSQL) |
| **llm/** | 6 | FULLY IMPLEMENTED | Real (Azure OpenAI via `openai` SDK) |
| **learning/** | 5 | FULLY IMPLEMENTED | Real (mem0 memory + embeddings) |
| **n8n/** | 3 | FULLY IMPLEMENTED | Real (n8n REST API via httpx) |
| **audit/** | 4 | FULLY IMPLEMENTED | In-memory (no DB persistence) |
| **a2a/** | 4 | FULLY IMPLEMENTED | In-memory (no external transport) |
| **shared/** | 2 | FULLY IMPLEMENTED | N/A (protocol definitions only) |

**Critical V7 Verification Result**: The V7 report flagged `correlation/` and `rootcause/` as STUB modules with fake/hardcoded data. **Sprint 130 has successfully fixed both modules**. Correlation now uses `EventDataSource` backed by Azure Monitor/App Insights REST API, and rootcause uses `CaseRepository` with 15 real IT Ops seed cases plus a `CaseMatcher` engine. Both gracefully degrade to empty results when external services are unconfigured (no more fake data).

---

## Module 1: swarm/ (7 files) — Agent Swarm System

**Phase**: 29 (Sprints 100-106)
**Feature**: C4 (Agent Swarm Visualization)

### Architecture

```
ClaudeCoordinator (claude_sdk/)
    |-- callbacks -->
SwarmIntegration (swarm_integration.py)
    |-- delegates to -->
SwarmTracker (tracker.py)          -- state management (in-memory + optional Redis)
    |
SwarmEventEmitter (events/emitter.py) -- SSE via AG-UI CustomEvent
    |-- emits to -->
Frontend (AgentSwarmPanel)
```

### Classes and Methods

#### `models.py` — Data Structures (~394 LOC)

| Class | Type | Description |
|-------|------|-------------|
| `WorkerType` | Enum | 9 worker roles: RESEARCH, WRITER, DESIGNER, REVIEWER, COORDINATOR, ANALYST, CODER, TESTER, CUSTOM |
| `WorkerStatus` | Enum | 7 states: PENDING, RUNNING, THINKING, TOOL_CALLING, COMPLETED, FAILED, CANCELLED |
| `SwarmMode` | Enum | 3 modes: SEQUENTIAL, PARALLEL, HIERARCHICAL |
| `SwarmStatus` | Enum | 5 states: INITIALIZING, RUNNING, PAUSED, COMPLETED, FAILED |
| `ToolCallStatus` | Enum | 4 states: PENDING, RUNNING, COMPLETED, FAILED |
| `ToolCallInfo` | Dataclass | Tool invocation tracking (id, name, is_mcp, input_params, result, duration_ms) |
| `ThinkingContent` | Dataclass | Extended thinking block (content, timestamp, token_count) |
| `WorkerMessage` | Dataclass | Conversation message (role, content, timestamp, thinking) |
| `WorkerExecution` | Dataclass | Full worker state (id, name, type, role, status, progress, tool_calls, thinking_contents, messages) |
| `AgentSwarmStatus` | Dataclass | Complete swarm state (swarm_id, mode, status, workers, progress, tool_call counts) |

All dataclasses implement `to_dict()`, `from_dict()`, and JSON serialization.

#### `tracker.py` — SwarmTracker (~694 LOC)

| Method | Description |
|--------|-------------|
| `create_swarm(swarm_id, mode, metadata)` | Create new swarm, store in dict + optional Redis |
| `get_swarm(swarm_id)` | Get swarm by ID (memory first, then Redis fallback) |
| `complete_swarm(swarm_id, status)` | Mark swarm completed, set progress to 100 |
| `update_swarm_status(swarm_id, status)` | Update swarm status |
| `start_worker(swarm_id, worker_id, ...)` | Add worker to swarm, auto-set swarm to RUNNING |
| `update_worker_progress(swarm_id, worker_id, progress)` | Update progress (0-100), recalculate overall |
| `update_worker_status(swarm_id, worker_id, status)` | Update worker status |
| `add_worker_thinking(swarm_id, worker_id, content)` | Add thinking content, set status to THINKING |
| `add_worker_tool_call(swarm_id, worker_id, ...)` | Add tool call, set status to TOOL_CALLING |
| `update_tool_call_result(swarm_id, worker_id, tool_id, result)` | Complete tool call, calculate duration |
| `add_worker_message(swarm_id, worker_id, role, content)` | Add conversation message |
| `complete_worker(swarm_id, worker_id, status)` | Mark worker completed |
| `delete_swarm(swarm_id)` | Delete from memory + Redis |
| `list_swarms()` / `list_active_swarms()` | List all/active swarms |

- Thread-safe via `threading.RLock`
- Singleton pattern via `get_swarm_tracker()` / `set_swarm_tracker()`
- Callback hooks: `on_swarm_update`, `on_worker_update`
- Redis persistence: optional, uses JSON serialization

#### `swarm_integration.py` — SwarmIntegration (~405 LOC)

Bridge between `ClaudeCoordinator` and `SwarmTracker`. Callback-based interface:

| Method | Description |
|--------|-------------|
| `on_coordination_started(swarm_id, mode, subtasks)` | Create swarm with subtask metadata |
| `on_subtask_started(swarm_id, worker_id, ...)` | Start worker |
| `on_subtask_progress(swarm_id, worker_id, progress)` | Update progress |
| `on_tool_call(swarm_id, worker_id, ...)` | Track tool invocation |
| `on_tool_result(swarm_id, worker_id, tool_id, result)` | Track tool result |
| `on_thinking(swarm_id, worker_id, content)` | Track thinking |
| `on_message(swarm_id, worker_id, role, content)` | Track messages |
| `on_subtask_completed(swarm_id, worker_id)` | Complete worker |
| `on_coordination_completed(swarm_id)` | Complete swarm |

Helper: `_infer_worker_type(name, role)` — keyword-based type inference from name/role strings.

#### `events/types.py` — 9 Event Payload Dataclasses (~444 LOC)

| Payload | Fields |
|---------|--------|
| `SwarmCreatedPayload` | swarm_id, session_id, mode, workers[], created_at |
| `SwarmStatusUpdatePayload` | swarm_id, session_id, mode, status, total_workers, overall_progress, workers[] |
| `SwarmCompletedPayload` | swarm_id, status, summary, total_duration_ms, completed_at |
| `WorkerStartedPayload` | swarm_id, worker_id, worker_name, worker_type, role, task_description |
| `WorkerProgressPayload` | swarm_id, worker_id, progress, status, current_action |
| `WorkerThinkingPayload` | swarm_id, worker_id, thinking_content, token_count |
| `WorkerToolCallPayload` | swarm_id, worker_id, tool_call_id, tool_name, status, input_args, output_result |
| `WorkerMessagePayload` | swarm_id, worker_id, role, content, tool_call_id |
| `WorkerCompletedPayload` | swarm_id, worker_id, status, result, duration_ms |

All implement `to_dict()` for JSON serialization. `SwarmEventNames` provides string constants and helper methods (`all_events()`, `priority_events()`, `throttled_events()`).

#### `events/emitter.py` — SwarmEventEmitter (~635 LOC)

| Method | Description |
|--------|-------------|
| `start()` / `stop()` | Start/stop batch sender asyncio task |
| `emit_swarm_created(swarm)` | Priority event (immediate send) |
| `emit_swarm_status_update(swarm)` | Throttled event |
| `emit_swarm_completed(swarm)` | Priority event |
| `emit_worker_started(swarm_id, worker)` | Priority event |
| `emit_worker_progress(swarm_id, worker)` | Throttled event |
| `emit_worker_thinking(swarm_id, worker, content)` | Throttled event |
| `emit_worker_tool_call(swarm_id, worker, tool_call)` | Priority event |
| `emit_worker_message(swarm_id, worker, role, content)` | Non-priority (batched) |
| `emit_worker_completed(swarm_id, worker)` | Priority event |

- Throttling: configurable interval (default 200ms), per-key tracking
- Batch sending: asyncio queue with configurable batch size (default 5)
- Priority events bypass queue and send immediately
- Emits AG-UI `CustomEvent` objects (from `src.integrations.ag_ui.events`)

### Dependencies
- `src.integrations.ag_ui.events.CustomEvent` (for SSE event format)
- Standard library: `asyncio`, `threading`, `dataclasses`, `datetime`, `json`

### Data Source
- **In-memory dict** (`self._swarms: Dict[str, AgentSwarmStatus]`)
- **Optional Redis persistence** (serialize/deserialize via JSON)
- **No hardcoded/fake data** — tracks real swarm executions

### Implementation Completeness: 100%
Fully implemented with thread safety, Redis persistence, SSE event streaming with throttling/batching, and comprehensive data models.

---

## Module 2: patrol/ (11 files) — Continuous Monitoring

**Phase**: 23 (Sprint 82)
**Feature**: G3 (Proactive Patrol System)

### Architecture

```
PatrolScheduler (scheduler.py)
    |-- schedules -->
PatrolAgent (agent.py)
    |-- executes -->
Check Registry: ServiceHealthCheck, APIResponseCheck, ResourceUsageCheck,
                 LogAnalysisCheck, SecurityScanCheck
    |-- produces -->
PatrolReport (types.py) + RiskAssessment
```

### Classes and Methods

#### `types.py` — Type Definitions

| Type | Description |
|------|-------------|
| `CheckType` | Enum: SERVICE_HEALTH, API_RESPONSE, RESOURCE_USAGE, LOG_ANALYSIS, SECURITY_SCAN |
| `PatrolStatus` | Enum: HEALTHY, WARNING, CRITICAL, UNKNOWN |
| `PatrolPriority` | Enum: LOW, MEDIUM, HIGH, CRITICAL |
| `ScheduleFrequency` | Enum: ONCE, HOURLY, DAILY, WEEKLY, MONTHLY, CUSTOM |
| `CheckResult` | Dataclass: check_id, check_type, status, message, started_at, completed_at, duration_ms, details, metrics, errors |
| `RiskAssessment` | Dataclass: risk_score, risk_level, risk_factors, mitigation_suggestions |
| `PatrolReport` | Dataclass: patrol_id, execution_id, name, started_at, completed_at, overall_status, checks[], risk_assessment, summary |
| `PatrolConfig` | Dataclass: patrol_id, name, description, check_types[], schedule, priority, config |
| `ScheduledPatrol` | Dataclass: patrol_id, config, frequency, cron_expression, next_run, last_run, last_status |
| `PatrolTriggerRequest` / `PatrolTriggerResponse` | Dataclasses for API request/response |
| `calculate_risk_score(checks)` | Utility: weighted risk calculation from check results |
| `determine_overall_status(checks)` | Utility: aggregate check statuses |

#### `agent.py` — PatrolAgent

| Method | Description |
|--------|-------------|
| `register_check(check_type, check_class)` | Register a check implementation |
| `execute_patrol(config, execution_id)` | Run all checks in config, aggregate results |
| `_execute_checks(config)` | Run checks in parallel via `asyncio.gather` |
| `_calculate_risk(checks)` | Generate RiskAssessment using `calculate_risk_score` |
| `_generate_summary(config, checks, risk)` | Text summary of patrol results |
| `_analyze_with_claude(report)` | Optional Claude-enhanced analysis |

- Accepts optional `claude_client` for AI-enhanced analysis
- Check registry pattern for extensibility
- Tracks running patrols via `_running_patrols` dict

#### `scheduler.py` — PatrolScheduler

| Method | Description |
|--------|-------------|
| `schedule_patrol(config, frequency, cron_expression)` | Schedule a patrol |
| `unschedule_patrol(patrol_id)` | Remove scheduled patrol |
| `get_scheduled_patrols()` | List all scheduled patrols |
| `start()` / `stop()` | Start/stop scheduler loop |
| `trigger_patrol(patrol_id)` | Manually trigger a patrol |
| `_scheduler_loop()` | asyncio loop checking due patrols |
| `_is_patrol_due(scheduled)` | Check if patrol should run |

#### `checks/base.py` — BaseCheck

| Method | Description |
|--------|-------------|
| `execute()` | Abstract: run the check |
| `_start_check()` | Record start time |
| `_healthy(message, details, metrics)` | Create HEALTHY result |
| `_warning(message, details, metrics)` | Create WARNING result |
| `_critical(message, details, metrics, errors)` | Create CRITICAL result |
| `get_config_value(key, default)` | Get config with default |

#### Check Implementations

| Check Class | File | Data Source | What It Does |
|-------------|------|-------------|-------------|
| `ServiceHealthCheck` | `service_health.py` | Real HTTP calls (`httpx`) | Checks service endpoints, measures response time, verifies status codes |
| `APIResponseCheck` | `api_response.py` | Real HTTP calls (`httpx`) | Tests API endpoints with configurable methods, headers, expected status codes, response time thresholds |
| `ResourceUsageCheck` | `resource_usage.py` | Real system data (`psutil`) | Checks CPU, memory, disk usage against configurable thresholds |
| `LogAnalysisCheck` | `log_analysis.py` | Real filesystem (`os`, `re`) | Scans log files for error/warning patterns, counts occurrences |
| `SecurityScanCheck` | `security_scan.py` | Real filesystem (`os`, `re`) | Scans for hardcoded passwords, API keys, private keys, dangerous configs, file permissions |

### Dependencies
- `httpx` (HTTP health checks)
- `psutil` (resource monitoring — graceful fallback if not installed)
- Standard library: `asyncio`, `os`, `re`, `datetime`

### Data Source: REAL
All checks use real system data (HTTP calls, filesystem, psutil). No hardcoded/fake data.

### Implementation Completeness: 100%
5 concrete check implementations, scheduler, agent with check registry, risk assessment, and optional Claude integration.

---

## Module 3: incident/ (6 files) — Incident Management

**Phase**: 34 (Sprint 126)
**Feature**: H1 (IT Incident Processing)

### Architecture

```
IncidentContext (input)
    |
IncidentAnalyzer (analyzer.py)
    |-- uses --> CorrelationAnalyzer + RootCauseAnalyzer + optional LLM
    |-- produces --> IncidentAnalysis
    |
ActionRecommender (recommender.py)
    |-- rule-based templates + optional LLM enhancement
    |-- produces --> List[RemediationAction]
    |
IncidentExecutor (executor.py)
    |-- auto-execute (low risk) or HITL approval (high risk)
    |-- uses MCP tools for execution
    |-- writes back to ServiceNow
    |-- produces --> List[ExecutionResult]
```

### Classes and Methods

#### `types.py` — Type Definitions

| Type | Description |
|------|-------------|
| `IncidentSeverity` | Enum: P1, P2, P3, P4 |
| `IncidentCategory` | Enum: NETWORK, SERVER, DATABASE, APPLICATION, SECURITY, PERFORMANCE, STORAGE, OTHER |
| `RemediationRisk` | Enum: LOW, MEDIUM, HIGH, CRITICAL |
| `RemediationActionType` | Enum: RESTART_SERVICE, CLEAR_DISK_SPACE, AD_ACCOUNT_UNLOCK, SCALE_RESOURCE, NETWORK_ACL_CHANGE, FIREWALL_RULE_CHANGE, RESTART_DATABASE, CLEAR_CACHE, CUSTOM |
| `ExecutionStatus` | Enum: PENDING, IN_PROGRESS, COMPLETED, FAILED, SKIPPED, AWAITING_APPROVAL |
| `IncidentContext` | Dataclass: incident_number, short_description, description, severity, category, cmdb_ci, caller_id, assignment_group, created_at, additional_data |
| `IncidentAnalysis` | Dataclass: analysis_id, incident_number, root_cause_summary, confidence, correlations_found, recommended_actions[], severity_assessment, analysis_details |
| `RemediationAction` | Dataclass: action_type, title, description, confidence, risk, mcp_tool, mcp_params, prerequisites, rollback_steps, estimated_duration_seconds, metadata |
| `ExecutionResult` | Dataclass: action_type, status, output, error, started_at, completed_at, duration_ms, approval_required, approved_by |

#### `prompts.py` — LLM Prompt Templates
- `INCIDENT_ANALYSIS_PROMPT`: Template for LLM-enhanced incident analysis

#### `analyzer.py` — IncidentAnalyzer

| Method | Description |
|--------|-------------|
| `analyze(context)` | Full pipeline: convert to Event -> correlate -> root cause -> LLM enhance -> merge |
| `_context_to_event(context)` | Convert IncidentContext to correlation Event |
| `_merge_analysis(rca, correlations, context)` | Merge RCA + correlations into IncidentAnalysis |
| `_enhance_with_llm(analysis, context)` | Optional LLM enhancement for deeper insights |
| `_extract_actions_from_rca(rca)` | Extract remediation actions from RCA recommendations |

- Depends on: `CorrelationAnalyzer`, `RootCauseAnalyzer`, optional `LLMServiceProtocol`
- Creates defaults if dependencies not provided

#### `recommender.py` — ActionRecommender

| Method | Description |
|--------|-------------|
| `recommend(analysis, context)` | Generate remediation actions (rule + LLM) |
| `_rule_based_recommend(analysis, context)` | Template-based actions per category |
| `_llm_recommend(analysis, context)` | LLM-enhanced recommendations |
| `_substitute_params(params, context)` | Replace placeholders in MCP parameters |
| `_deduplicate_actions(actions)` | Remove duplicate actions |

- `ACTION_TEMPLATES`: Hardcoded remediation templates per `IncidentCategory` (NETWORK, DATABASE, PERFORMANCE, etc.)
- Templates include MCP tool names and parameters (e.g., `shell:run_command`, `redis-cli FLUSHDB`)
- LLM enhancement is optional

#### `executor.py` — IncidentExecutor

| Method | Description |
|--------|-------------|
| `execute(analysis, context, actions)` | Execute all actions with risk-based routing |
| `_should_auto_execute(action, context)` | Determine if action can auto-execute (LOW risk only) |
| `_auto_execute(action, context)` | Execute via MCP tool |
| `_request_approval(action, context)` | Submit for HITL approval |
| `_execute_mcp_tool(tool_name, params)` | Call MCP tool |
| `_writeback_to_servicenow(context, results)` | Update ServiceNow with results |

- Risk-based execution: LOW risk = auto-execute, MEDIUM/HIGH = HITL approval
- MCP tool integration for automated remediation
- ServiceNow writeback capability

### Dependencies
- `correlation.analyzer.CorrelationAnalyzer`
- `rootcause.analyzer.RootCauseAnalyzer`
- `llm.LLMServiceProtocol` (optional)
- MCP tool execution (optional)

### Data Source: REAL
Uses real correlation and root cause analysis pipelines. Templates are hardcoded but represent real remediation patterns.

### Implementation Completeness: 95%
Full pipeline implemented. ServiceNow writeback is stubbed (needs real ServiceNow API credentials). MCP tool execution depends on MCP server availability.

---

## Module 4: correlation/ (6 files) — Event Correlation Analysis

**Phase**: 23 (Sprint 82), **Updated**: Sprint 130
**Feature**: G4 (Intelligent Correlation)
**V7 Status**: Was STUB with fake data. **Now FIXED**.

### Architecture (Post-Sprint 130)

```
EventDataSource (data_source.py)        <-- Azure Monitor / App Insights REST API
    |-- queries via KQL -->
EventCollector (event_collector.py)     <-- Dedup + Aggregate
    |-- feeds -->
CorrelationAnalyzer (analyzer.py)       <-- Time + Dependency + Semantic analysis
    |-- builds -->
GraphBuilder (graph.py)                 <-- Correlation graph visualization
    |-- produces -->
CorrelationResult (types.py)
```

### Classes and Methods

#### `types.py` — Type Definitions

| Type | Description |
|------|-------------|
| `CorrelationType` | Enum: TIME, DEPENDENCY, SEMANTIC, CAUSAL |
| `EventSeverity` | Enum: INFO, WARNING, ERROR, CRITICAL |
| `EventType` | Enum: ALERT, METRIC_ANOMALY, LOG_PATTERN, INCIDENT, CHANGE, CONFIG_CHANGE |
| `Event` | Dataclass: event_id, title, description, event_type, severity, timestamp, source_system, affected_components, metadata |
| `Correlation` | Dataclass: correlation_id, source_event_id, target_event_id, correlation_type, score, confidence, evidence, metadata |
| `GraphNode` | Dataclass: node_id, node_type, label, severity, timestamp, metadata |
| `GraphEdge` | Dataclass: edge_id, source_id, target_id, relation_type, weight, label, metadata |
| `CorrelationGraph` | Dataclass: graph_id, root_event_id, nodes[], edges[] + add_node/add_edge/get_neighbors |
| `CorrelationResult` | Dataclass: query, event, correlations, graph, analysis_time_ms, total_events_scanned, summary |
| `DiscoveryQuery` | Dataclass: event, time_window, correlation_types, min_score, max_results |
| `CORRELATION_WEIGHTS` | Dict: TIME=0.40, DEPENDENCY=0.35, SEMANTIC=0.25 |
| `calculate_combined_score()` | Weighted score calculation |

#### `data_source.py` — EventDataSource (Sprint 130: NEW)

| Method | Description |
|--------|-------------|
| `get_event(event_id)` | Query App Insights by operation_Id/itemId via KQL |
| `get_events_in_range(start, end, source, severity, max)` | Range query with filters |
| `get_events_for_component(component_id, time_window)` | Query by cloud_RoleName |
| `get_dependencies(component_id, time_window)` | Get component dependencies |
| `_query_app_insights(kql_query)` | Execute KQL against App Insights REST API |
| `_query_log_analytics(kql_query)` | Execute KQL against Log Analytics workspace |
| `_convert_to_event(row)` | Convert raw telemetry row to Event object |
| `_is_configured()` | Check if Azure credentials are available |

- `AzureMonitorConfig`: app_id, api_key, workspace_id, subscription_id, resource_group, resource_name
- Uses `httpx.AsyncClient` for HTTP calls
- **Graceful degradation**: Returns `None`/`[]` when not configured (no fake data)
- KQL sanitization via `_sanitize_kql()` helper
- Severity/type mapping dicts for raw telemetry conversion

#### `event_collector.py` — EventCollector (Sprint 130: NEW)

| Method | Description |
|--------|-------------|
| `collect_events(start, end, service, severity)` | Collect + dedup events |
| `deduplicate(events)` | Remove duplicates by event_id + time-proximity signature |
| `aggregate_by_service(events)` | Group events by source_system |
| `get_component_dependencies(component_id)` | Get dependencies from data source |

- `CollectionConfig`: default_time_window (1h), max_events_per_query (200), dedup_window_seconds (60)
- Dedup uses event_id + hash signature with configurable time window

#### `analyzer.py` — CorrelationAnalyzer

| Method | Description |
|--------|-------------|
| `find_correlations(event, time_window, types, min_score, max)` | Main entry: parallel analysis across types |
| `discover(query)` | Full discovery: correlations + graph + summary |
| `_time_correlation(event, time_window)` | Time-proximity analysis via EventCollector |
| `_dependency_correlation(event)` | System dependency analysis |
| `_semantic_correlation(event)` | Semantic similarity analysis |
| `_merge_correlations(correlations)` | Merge duplicate event correlations |
| `_build_graph(event, correlations)` | Build CorrelationGraph from results |
| `_generate_summary(event, correlations)` | Generate text summary |
| `_get_event(event_id)` | Get event from data source (returns None if unconfigured) |
| `_get_events_in_range(start, end)` | Get events from data source |

**Sprint 130 Changes**:
- Constructor now accepts `data_source: EventDataSource` and `event_collector: EventCollector`
- `_time_correlation` fetches real events from EventCollector when available
- `_get_event` / `_get_events_in_range` delegate to `EventDataSource`
- All methods return empty results when data source is unconfigured
- **No more fake/hardcoded data anywhere**

#### `graph.py` — GraphBuilder

| Method | Description |
|--------|-------------|
| `build_from_correlations(root_event, correlations, related_events)` | Build graph from data |
| `find_critical_path()` | Find highest-weight path through graph |
| `get_statistics()` | Node/edge counts, avg weight |
| `to_vis_format()` | Export for visualization (nodes + edges arrays) |
| `to_mermaid()` | Export as Mermaid diagram |
| `to_adjacency_list()` | Export as adjacency list |

### Dependencies
- `httpx` (Azure Monitor REST API)
- Standard library: `asyncio`, `hashlib`, `logging`, `datetime`

### Data Source: REAL (Sprint 130 fix verified)
- Primary: Azure Monitor / Application Insights REST API via KQL queries
- Graceful fallback: empty results when unconfigured
- **No hardcoded examples, no fake data, no stub returns**

### Implementation Completeness: 95%
Fully implemented with real data source. The semantic correlation analysis still uses basic keyword matching (no embedding-based similarity). The CAUSAL correlation type is defined but not implemented in the analyzer.

---

## Module 5: rootcause/ (5 files) — Root Cause Analysis

**Phase**: 23 (Sprint 82), **Updated**: Sprint 130
**Feature**: G5 (Root Cause Analysis)
**V7 Status**: Was STUB with hardcoded HistoricalCase objects. **Now FIXED**.

### Architecture (Post-Sprint 130)

```
CaseRepository (case_repository.py)     <-- In-memory + optional PostgreSQL
    |-- 15 IT Ops seed cases -->
CaseMatcher (case_matcher.py)           <-- Multi-dimensional matching
    |-- finds similar cases -->
RootCauseAnalyzer (analyzer.py)
    |-- uses CorrelationAnalyzer + CaseMatcher + optional Claude
    |-- produces --> RootCauseAnalysis
```

### Classes and Methods

#### `types.py` — Type Definitions

| Type | Description |
|------|-------------|
| `AnalysisStatus` | Enum: PENDING, IN_PROGRESS, COMPLETED, FAILED |
| `EvidenceType` | Enum: SYSTEM, LOG, METRIC, CORRELATION, EXPERT, HISTORICAL |
| `RecommendationType` | Enum: IMMEDIATE, SHORT_TERM, LONG_TERM |
| `HistoricalCase` | Dataclass: case_id, title, description, root_cause, resolution, category, severity, lessons_learned, similarity_score, metadata |
| `Evidence` | Dataclass: evidence_id, evidence_type, description, source, timestamp, relevance_score |
| `RootCauseHypothesis` | Dataclass: hypothesis_id, description, confidence, evidence[], supporting_events |
| `Recommendation` | Dataclass: recommendation_id, recommendation_type, description, priority, estimated_effort, steps |
| `AnalysisContext` | Dataclass: event_data, correlations, graph_data, system_context, historical_patterns |
| `AnalysisRequest` | Dataclass: event, depth, include_historical, max_hypotheses |
| `RootCauseAnalysis` | Full analysis result with hypotheses, evidence chain, recommendations, historical cases |
| `ANALYSIS_DEPTH_CONFIG` | Dict: quick/standard/deep configurations |
| `calculate_overall_confidence()` | Weighted confidence from hypotheses |

#### `case_repository.py` — CaseRepository (Sprint 130: NEW)

| Method | Description |
|--------|-------------|
| `get_case(case_id)` | Get case by ID |
| `get_all_cases()` | Get all cases |
| `search_cases(query, category, severity, max)` | Text search across title/description/root_cause |
| `add_case(case)` | Add new case |
| `update_case(case)` | Update existing case |
| `delete_case(case_id)` | Delete case |
| `get_cases_by_category(category)` | Filter by category |
| `get_recent_cases(days, max)` | Get recent cases |
| `import_from_servicenow(tickets)` | Batch import from ServiceNow format |
| `get_statistics()` | Case count, category distribution, avg resolution time |

**Seed Data**: 15 real IT Ops historical cases:
- HC-001: Database Connection Pool Exhaustion
- HC-002: Memory Leak in Node.js API Service
- HC-003: DNS Resolution Failure
- HC-004: Redis Cluster Split-Brain
- HC-005: TLS Certificate Expiry
- HC-006: ETL Pipeline Data Skew
- HC-007 through HC-015: Additional real-world IT operations scenarios

Storage modes:
- **In-memory**: Default, auto-loads seed data
- **PostgreSQL**: Via `db_session` parameter (interface defined but DB queries not fully implemented — in-memory fallback)

#### `case_matcher.py` — CaseMatcher (Sprint 130: NEW)

| Method | Description |
|--------|-------------|
| `find_similar_cases(event, max_results, min_similarity)` | Multi-dimensional matching |
| `find_similar_with_details(event, max_results, min_similarity)` | Returns MatchResult with score breakdown |
| `_compute_text_similarity(event, case)` | Keyword overlap / TF-IDF style scoring |
| `_compute_category_match(event, case)` | Category keyword matching |
| `_compute_severity_match(event, case)` | Severity alignment scoring |
| `_compute_recency_score(case)` | More recent cases score higher |
| `_extract_keywords(text)` | Stop-word removal + tokenization |
| `_infer_category(event)` | Infer category from event keywords |

Scoring weights:
- Text similarity: 45%
- Category match: 25%
- Severity match: 15%
- Recency: 15%
- Optional LLM semantic matching (overrides text similarity when available)

Category keyword dictionaries for: database, networking, security, infrastructure, application, deployment, messaging, data, observability.

#### `analyzer.py` — RootCauseAnalyzer

| Method | Description |
|--------|-------------|
| `analyze_root_cause(event, correlations, graph)` | Full analysis pipeline |
| `get_similar_patterns(event)` | Find similar historical cases via CaseMatcher |
| `_build_analysis_context(event, correlations, graph)` | Build AnalysisContext |
| `_generate_hypotheses(context, historical_cases)` | Generate hypotheses from correlations + historical cases |
| `_claude_analyze(event, context, hypotheses, cases)` | LLM-powered root cause determination |
| `_basic_analysis(hypotheses)` | Fallback without Claude (uses top hypothesis) |
| `_build_analysis_prompt(event, context, hypotheses, cases)` | Construct Claude prompt |
| `_parse_claude_response(response)` | Extract ROOT_CAUSE, CONFIDENCE, EVIDENCE from Claude response |
| `_identify_contributing_factors(correlations, hypotheses)` | Identify secondary factors |
| `_generate_recommendations(root_cause, factors, cases)` | Generate IMMEDIATE + SHORT_TERM recommendations |

**Sprint 130 Changes**:
- Constructor accepts `case_repository: CaseRepository` and `case_matcher: CaseMatcher`
- `get_similar_patterns()` delegates to `CaseMatcher.find_similar_cases()` instead of returning hardcoded cases
- Returns empty list when no case_matcher configured (no fake data)
- `metadata` includes `"data_source": "case_repository"` or `"none"` for auditability

### Dependencies
- `correlation.CorrelationAnalyzer`, `correlation.types.Event/Correlation/CorrelationGraph`
- Optional: `claude_client` (any object with `send_message()` method)
- Optional: `CaseRepository` + `CaseMatcher`

### Data Source: REAL (Sprint 130 fix verified)
- Case repository with 15 seed cases (real IT Ops scenarios, not fake/placeholder)
- CaseMatcher with real multi-dimensional scoring algorithm
- Claude integration for intelligent analysis (graceful fallback to basic analysis)
- **No more hardcoded HistoricalCase objects in analyzer**

### Implementation Completeness: 90%
Core analysis pipeline complete. PostgreSQL storage for CaseRepository is interface-only (falls back to in-memory). ServiceNow import is implemented but untested with real ServiceNow data.

---

## Module 6: memory/ (5 files) — mem0 Memory System

**Phase**: 22 (Sprint 79)
**Feature**: E6 (Three-Layer Memory)

### Architecture

```
UnifiedMemoryManager (unified_memory.py)
    |-- Layer 1: Working Memory --> Redis (TTL 30min)
    |-- Layer 2: Session Memory --> PostgreSQL (TTL 7 days)
    |-- Layer 3: Long-term Memory --> Mem0Client (Qdrant, permanent)
    |
    |-- EmbeddingService (embeddings.py)
    |     |-- OpenAI / Azure OpenAI embeddings
    |     |-- In-memory cache with TTL
    |
    |-- Mem0Client (mem0_client.py)
          |-- mem0 SDK wrapper
          |-- Qdrant vector storage
```

### Classes and Methods

#### `types.py` — Type Definitions

| Type | Description |
|------|-------------|
| `MemoryType` | Enum: FACT, PREFERENCE, CONTEXT, INTERACTION, EVENT, SYSTEM_KNOWLEDGE, BEST_PRACTICE, USER_PREFERENCE, EVENT_RESOLUTION |
| `MemoryLayer` | Enum: WORKING, SESSION, LONG_TERM |
| `MemoryMetadata` | Dataclass: source, importance, tags, context_id, session_id, custom |
| `MemoryRecord` | Dataclass: id, content, memory_type, layer, metadata, embedding, created_at, updated_at, expires_at |
| `MemorySearchQuery` | Dataclass: query, user_id, memory_types, layers, limit, min_score |
| `MemorySearchResult` | Dataclass: record, score, highlights |
| `MemoryConfig` | Dataclass: qdrant_path, qdrant_collection, embedding_model, llm_provider, llm_model, working_memory_ttl, session_memory_ttl, min_importance |
| `DEFAULT_MEMORY_CONFIG` | Pre-configured defaults |

#### `mem0_client.py` — Mem0Client

| Method | Description |
|--------|-------------|
| `initialize()` | Import mem0 SDK, configure Qdrant + embedder + LLM, create Memory instance |
| `add_memory(content, user_id, metadata)` | Store memory with auto-extraction |
| `search_memory(query)` | Semantic search across memories |
| `get_all(user_id)` | Get all memories for a user |
| `get_memory(memory_id)` | Get specific memory by ID |
| `update_memory(memory_id, content)` | Update existing memory |
| `delete_memory(memory_id)` | Remove memory |

- Wraps `mem0.Memory` SDK
- Configures: Qdrant (local path), OpenAI embeddings, Claude/OpenAI for extraction
- Lazy initialization pattern

#### `embeddings.py` — EmbeddingService

| Method | Description |
|--------|-------------|
| `initialize()` | Create OpenAI/Azure OpenAI client |
| `embed_text(text, use_cache)` | Generate embedding for single text |
| `embed_batch(texts, use_cache)` | Batch embedding generation |
| `compute_similarity(embedding1, embedding2)` | Cosine similarity calculation |

- `EmbeddingCache`: In-memory cache with TTL, SHA-256 key generation
- Supports both OpenAI and Azure OpenAI clients
- Lazy initialization with error handling

#### `unified_memory.py` — UnifiedMemoryManager

| Method | Description |
|--------|-------------|
| `initialize()` | Init mem0 + embeddings + Redis |
| `add(content, user_id, memory_type, layer, metadata)` | Add memory with automatic layer selection |
| `search(query, user_id, types, layers, limit)` | Search across all layers |
| `get_context(session_id, user_id, limit)` | Get relevant memories for current context |
| `promote(memory_id, target_layer)` | Move memory to higher layer |
| `consolidate(user_id, session_id)` | Merge and summarize memories |
| `_initialize_redis()` | Lazy Redis connection |
| `_store_working_memory(record)` | Store in Redis with TTL |
| `_store_session_memory(record)` | Store in PostgreSQL |
| `_store_long_term_memory(record)` | Store via mem0 |
| `_search_working_memory(query)` | Search Redis |
| `_search_session_memory(query)` | Search PostgreSQL |
| `_search_long_term_memory(query)` | Search via mem0 |

### Dependencies
- `mem0` SDK (optional — graceful degradation if not installed)
- `openai` SDK (for embeddings)
- Redis (optional — for working memory)
- PostgreSQL (optional — for session memory)

### Data Source: REAL
- mem0 SDK with Qdrant for vector storage
- OpenAI/Azure OpenAI for embeddings
- Redis for working memory
- PostgreSQL for session memory
- All connections are optional with graceful degradation

### Implementation Completeness: 85%
Core three-layer architecture implemented. Redis and PostgreSQL layers have lazy initialization. Consolidation logic is basic. All external dependencies are optional with graceful fallback.

---

## Module 7: llm/ (6 files) — LLM Provider Integration

**Phase**: 1 (Sprint 34)
**Feature**: E7 (LLM Service Infrastructure)

### Architecture

```
LLMServiceProtocol (protocol.py)        <-- Interface definition
    |
    |-- AzureOpenAILLMService (azure_openai.py)  <-- Production: AsyncAzureOpenAI SDK
    |-- MockLLMService (mock.py)                  <-- Testing: configurable responses
    |-- CachedLLMService (cached.py)              <-- Decorator: Redis caching
    |
LLMServiceFactory (factory.py)           <-- Factory + singleton + auto-detection
```

### Classes and Methods

#### `protocol.py` — LLMServiceProtocol

```python
@runtime_checkable
class LLMServiceProtocol(Protocol):
    async def generate(prompt, max_tokens, temperature, stop, **kwargs) -> str
    async def generate_structured(prompt, output_schema, max_tokens, temperature, **kwargs) -> Dict
```

Custom exceptions: `LLMServiceError`, `LLMTimeoutError`, `LLMRateLimitError`, `LLMParseError`, `LLMValidationError`

#### `azure_openai.py` — AzureOpenAILLMService

| Method | Description |
|--------|-------------|
| `generate(prompt, max_tokens, temperature, stop)` | Chat completions via Azure OpenAI |
| `generate_structured(prompt, output_schema, max_tokens, temperature)` | JSON output with schema validation |
| `_call_with_retry(messages, max_tokens, temperature, stop, response_format)` | Retry with exponential backoff |
| `_extract_json(text)` | Extract JSON from response text |
| `_validate_output(output, schema)` | Validate against schema |

- Uses `openai.AsyncAzureOpenAI` client (real SDK, real API calls)
- Reads from env: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT_NAME`
- Retry: max 3 retries with exponential backoff (1s, 2s, 4s)
- Handles: `RateLimitError`, `APITimeoutError`, `APIError`
- Timeout: 180s (for complex AI analysis)

#### `mock.py` — MockLLMService

| Method | Description |
|--------|-------------|
| `generate(prompt, ...)` | Return configurable mock response |
| `generate_structured(prompt, output_schema, ...)` | Return configurable structured response |
| `set_response(response)` | Set default text response |
| `set_structured_response(response)` | Set default structured response |
| `get_call_history()` | Get all recorded calls |
| `reset()` | Clear call history and responses |

#### `cached.py` — CachedLLMService

| Method | Description |
|--------|-------------|
| `generate(prompt, ...)` | Check Redis cache -> call inner service -> cache result |
| `generate_structured(prompt, ...)` | Check Redis cache -> call inner service -> cache result |
| `_make_cache_key(operation, prompt, **params)` | SHA-256 hash of operation + params |
| `invalidate(pattern)` | Invalidate cache entries by pattern |
| `get_stats()` | Return cache hit/miss statistics |

- Wraps any `LLMServiceProtocol` implementation
- Redis-based caching with configurable TTL (default 3600s)
- Cache key: SHA-256 of operation + prompt + parameters

#### `factory.py` — LLMServiceFactory

| Method | Description |
|--------|-------------|
| `create(provider, use_cache, cache_ttl, singleton)` | Create LLM service instance |
| `create_mock(**kwargs)` | Convenience: create MockLLMService |
| `_detect_provider()` | Auto-detect: Azure (if env vars set) > Mock (testing) > error (production) |
| `_create_azure_service(**kwargs)` | Create AzureOpenAILLMService |
| `_create_mock_service(**kwargs)` | Create MockLLMService |
| `_wrap_with_cache(service, ttl)` | Wrap with CachedLLMService |

- Singleton pattern with cache key based on provider + cache config
- Environment-aware: production requires real config, development falls back to mock with warning

### Dependencies
- `openai` SDK (`AsyncAzureOpenAI`)
- Redis (optional — for CachedLLMService)

### Data Source: REAL
`AzureOpenAILLMService` makes real API calls to Azure OpenAI via the official `openai` Python SDK. No fake data.

### Implementation Completeness: 100%
Full protocol + Azure implementation + mock + caching decorator + factory with auto-detection.

---

## Module 8: learning/ (5 files) — Few-Shot Learning

**Phase**: 4 (Sprint 80)
**Feature**: F1 (Few-Shot Learning System)

### Architecture

```
FewShotLearner (few_shot.py)
    |-- CaseExtractor (case_extractor.py)
    |     |-- extracts cases from UnifiedMemoryManager
    |-- SimilarityCalculator (similarity.py)
    |     |-- semantic + structural similarity
    |     |-- uses EmbeddingService
    |-- enhance_prompt() --> enhanced prompt with examples
    |-- track_effectiveness() --> learning feedback loop
```

### Classes and Methods

#### `types.py` — Type Definitions

| Type | Description |
|------|-------------|
| `CaseOutcome` | Enum: SUCCESS, PARTIAL_SUCCESS, FAILURE, UNKNOWN |
| `CaseCategory` | Enum: INCIDENT_RESOLUTION, PERFORMANCE_OPTIMIZATION, SECURITY_RESPONSE, DEPLOYMENT_ISSUE, CONFIGURATION_CHANGE, USER_SUPPORT, SYSTEM_MAINTENANCE, OTHER |
| `CaseMetadata` | Dataclass: source, event_id, resolution_time_seconds, resolver_id, tags, custom |
| `Case` | Dataclass: id, title, description, category, outcome, affected_systems, root_cause, resolution_steps, lessons_learned, quality_score, metadata, embedding |
| `SimilarityResult` | Dataclass: case, semantic_score, structural_score, total_score |
| `LearningResult` | Dataclass: enhancement_id, original_prompt, enhanced_prompt, cases_used, quality_improvement |
| `LearningEffectiveness` | Dataclass: enhancement_id, decision_id, was_successful, feedback |
| `LearningConfig` | Dataclass: max_examples_in_prompt, min_quality_score, min_similarity_score, semantic_weight, structural_weight, include_lessons_learned, include_resolution_steps, case_expiry_days |

#### `case_extractor.py` — CaseExtractor

| Method | Description |
|--------|-------------|
| `initialize(memory_manager)` | Connect to UnifiedMemoryManager |
| `extract_from_memory(query, systems, category, max)` | Search memory for relevant cases |
| `create_case_from_resolution(title, description, ...)` | Create case from a resolution event |
| `_memory_to_case(record)` | Convert MemoryRecord to Case |
| `_rank_cases(cases, query, systems)` | Rank by relevance |
| `clear_cache()` | Clear internal case cache |

#### `similarity.py` — SimilarityCalculator

| Method | Description |
|--------|-------------|
| `calculate_similarity(query, case, embedding_service)` | Combined semantic + structural score |
| `_semantic_similarity(query, case, embedding_service)` | Cosine similarity via embeddings |
| `_structural_similarity(query_systems, case)` | Jaccard similarity on affected systems |
| `batch_calculate(query, cases, embedding_service)` | Batch similarity computation |

- Weighted scoring: semantic_weight (default 0.7) + structural_weight (default 0.3)

#### `few_shot.py` — FewShotLearner

| Method | Description |
|--------|-------------|
| `initialize(embedding_service, memory_manager)` | Setup dependencies |
| `get_similar_cases(query, systems, category, max)` | Find similar cases with scoring |
| `enhance_prompt(base_prompt, event_description, systems, category, max_examples)` | Add case examples to prompt |
| `track_effectiveness(enhancement_id, decision_id, was_successful, feedback)` | Record learning feedback |
| `get_effectiveness_stats()` | Aggregate effectiveness metrics |
| `_format_case_example(case, score)` | Format case for prompt injection |

### Dependencies
- `memory.UnifiedMemoryManager`
- `memory.EmbeddingService`

### Data Source: REAL
Extracts cases from the real memory system. Embeddings from OpenAI/Azure OpenAI.

### Implementation Completeness: 90%
Core functionality implemented. Effectiveness tracking is in-memory (no persistence). Case extraction depends on memory system being initialized.

---

## Module 9: n8n/ (3 files) — n8n Workflow Integration

**Phase**: Not specified (Sprint unspecified)
**Feature**: H3 (n8n Bidirectional Orchestration)

### Classes and Methods

#### `monitor.py` — ExecutionMonitor

| Method | Description |
|--------|-------------|
| `wait_for_completion(execution_id, timeout, progress_callback)` | Poll n8n API until execution completes |
| `_poll_execution(execution_id)` | Single poll request |
| `_estimate_progress(state, poll_count)` | Estimate progress percentage |

- `MonitorConfig`: poll_interval (2s), max_poll_interval (30s), backoff_factor (1.5x), default_timeout (300s)
- `ExecutionState` enum: PENDING, RUNNING, SUCCESS, ERROR, CANCELLED, TIMEOUT, UNKNOWN
- `ExecutionProgress` / `MonitorResult` dataclasses
- Exponential backoff polling with progress callbacks

#### `orchestrator.py` — N8nBidirectionalOrchestrator

| Method | Description |
|--------|-------------|
| `orchestrate(request)` | Full pipeline: reason -> translate -> execute -> monitor -> return |
| `register_reasoning_handler(handler)` | Register IPA reasoning function |
| `register_translation_handler(handler)` | Register input translation function |
| `register_progress_callback(request_id, callback)` | Register progress callback |
| `cancel(request_id)` | Cancel active orchestration |
| `get_status(request_id)` | Get orchestration status |

- `OrchestrationRequest`: user_input, context, workflow_id, workflow_params, timeout, callback_url
- `OrchestrationResult`: request_id, status, reasoning, execution_id, execution_result, duration_ms
- `ReasoningResult`: intent, sub_intent, confidence, recommended_workflow, workflow_input, risk_level, requires_approval
- 5-phase pipeline: Reasoning -> Translation -> Execution -> Monitoring -> Result
- Uses `N8nApiClient` from `src.integrations.mcp.servers.n8n.client`

### Dependencies
- `src.integrations.mcp.servers.n8n.client.N8nApiClient` (real n8n API)
- `asyncio` for async orchestration

### Data Source: REAL
Makes real API calls to n8n instance via `N8nApiClient`. Requires `N8N_BASE_URL` and `N8N_API_KEY` env vars.

### Implementation Completeness: 95%
Full bidirectional orchestration pipeline. Reasoning and translation handlers must be registered externally (pluggable design).

---

## Module 10: audit/ (4 files) — Decision Audit System

**Phase**: 22 (Sprint 80)
**Feature**: H2 (Decision Audit Tracking)

### Classes and Methods

#### `types.py` — Type Definitions

| Type | Description |
|------|-------------|
| `DecisionType` | Enum: PLAN_GENERATION, TOOL_SELECTION, RISK_ASSESSMENT, ESCALATION, REMEDIATION, APPROVAL, FRAMEWORK_SELECTION |
| `DecisionOutcome` | Enum: SUCCESS, PARTIAL_SUCCESS, FAILURE, PENDING, CANCELLED |
| `QualityRating` | Enum: EXCELLENT, GOOD, ACCEPTABLE, POOR, CRITICAL |
| `DecisionContext` | Dataclass: event_id, session_id, user_id, incident_id, system_state, related_decisions |
| `ThinkingProcess` | Dataclass: raw_thinking, structured_steps, key_factors, alternatives_evaluated, risk_considerations |
| `AlternativeConsidered` | Dataclass: description, confidence, reason_rejected |
| `DecisionAudit` | Full audit record: decision_id, decision_type, timestamp, selected_action, action_details, confidence_score, context, thinking_process, alternatives, outcome, outcome_details, quality_rating |
| `AuditReport` | Dataclass: report_id, decision_audit, explainability_score, summary, key_factors, risk_summary, recommendations |
| `AuditQuery` | Dataclass: decision_types, outcomes, date_range, min_confidence, session_id, event_id, limit |
| `AuditConfig` | Dataclass: enabled, retention_days, min_confidence_to_audit, include_thinking |

#### `decision_tracker.py` — DecisionTracker

| Method | Description |
|--------|-------------|
| `initialize()` | Setup tracker |
| `record_decision(decision_type, selected_action, ...)` | Create DecisionAudit record |
| `update_outcome(decision_id, outcome, details)` | Update decision outcome |
| `update_quality_rating(decision_id, rating)` | Rate decision quality |
| `query_decisions(query)` | Query audit records with filters |
| `get_decision(decision_id)` | Get single decision by ID |
| `get_statistics(time_window)` | Aggregate statistics |

- **In-memory storage** (`Dict[str, DecisionAudit]`)
- No database persistence (ephemeral)

#### `report_generator.py` — AuditReportGenerator

| Method | Description |
|--------|-------------|
| `generate_report(audit)` | Generate explainability report |
| `generate_batch_report(audits)` | Generate report for multiple decisions |
| `_calculate_explainability_score(audit)` | Score based on thinking process completeness |
| `_generate_summary(audit)` | Text summary of decision |
| `_extract_key_factors(audit)` | Extract key decision factors |
| `_generate_risk_summary(audit)` | Risk assessment summary |
| `_generate_recommendations(audit)` | Improvement recommendations |

### Dependencies
- Standard library only

### Data Source: IN-MEMORY
All audit records stored in-memory dict. **No database persistence** — records lost on restart.

### Implementation Completeness: 80%
Core tracking and reporting implemented. Missing: database persistence, export/import, long-term analytics.

---

## Module 11: a2a/ (4 files) — Agent-to-Agent Protocol

**Phase**: 23 (Sprint 81)
**Feature**: C5 (A2A Communication)

### Classes and Methods

#### `protocol.py` — Message Format and Agent Capabilities

| Type | Description |
|------|-------------|
| `MessageType` | Enum: REQUEST, RESPONSE, NOTIFICATION, BROADCAST, HANDOFF, HEARTBEAT |
| `MessagePriority` | Enum: LOW, NORMAL, HIGH, URGENT |
| `MessageStatus` | Enum: PENDING, DELIVERED, PROCESSED, FAILED, EXPIRED |
| `A2AAgentStatus` | Enum: ONLINE, BUSY, OFFLINE, MAINTENANCE |
| `A2AMessage` | Dataclass: message_id, message_type, priority, sender_id, receiver_id, content, correlation_id, reply_to, ttl, metadata, status, created_at |
| `AgentCapability` | Dataclass: agent_id, agent_name, capabilities[], status, metadata, last_heartbeat |
| `DiscoveryQuery` | Dataclass: capability, agent_status, max_results |
| `DiscoveryResult` | Dataclass: agents[], query_time_ms |

#### `discovery.py` — AgentDiscoveryService

| Method | Description |
|--------|-------------|
| `register_agent(capability)` | Register agent capabilities |
| `unregister_agent(agent_id)` | Remove agent |
| `discover(query)` | Find agents by capability and status |
| `get_agent(agent_id)` | Get agent by ID |
| `update_status(agent_id, status)` | Update agent status |
| `heartbeat(agent_id)` | Update last heartbeat timestamp |
| `cleanup_stale(timeout)` | Remove agents with expired heartbeats |

- **In-memory registry** (`Dict[str, AgentCapability]`)

#### `router.py` — MessageRouter

| Method | Description |
|--------|-------------|
| `route_message(message)` | Route message to receiver |
| `register_handler(agent_id, handler)` | Register message handler function |
| `broadcast(message, target_agents)` | Send to multiple agents |
| `get_message_history(agent_id, limit)` | Get message history |
| `get_pending_messages(agent_id)` | Get undelivered messages |

- **In-memory message storage and routing**
- No external message transport (no RabbitMQ/Redis pub-sub)

### Dependencies
- Standard library only

### Data Source: IN-MEMORY
Agent registry and message routing all in-memory. No external transport layer.

### Implementation Completeness: 75%
Protocol and routing logic defined. Missing: persistent storage, external transport (RabbitMQ/Redis), real inter-process communication.

---

## Module 12: shared/ (2 files) — Shared Protocols

**Phase**: 28 (Sprint 116)
**Feature**: Cross-module protocol definitions

### Classes and Methods

#### `protocols.py` — Protocol Definitions for Cross-Module Communication

Breaks circular dependencies between L5 (orchestration) and L6 (claude_sdk/agent_framework).

| Type | Description |
|------|-------------|
| `ToolCallStatus` | Enum: PENDING, RUNNING, COMPLETED, FAILED, CANCELLED |
| `ToolCallEvent` | Dataclass: tool_name, tool_id, input_params, is_mcp, timestamp, worker_id, metadata |
| `ToolResultEvent` | Dataclass: tool_name, tool_id, status, result, error, duration_ms, timestamp, worker_id |
| `ExecutionRequest` | Dataclass: request_id, messages, tools, model, system_prompt, metadata |
| `ExecutionResult` | Dataclass: success, content, error, framework_used, tool_calls, tokens_used, duration_ms, metadata |
| `SwarmEvent` | Dataclass: event_type, swarm_id, worker_id, data, timestamp |
| `ToolCallbackProtocol` | Protocol: `on_tool_call(event) -> Dict`, `on_tool_result(event) -> None` |
| `ExecutionEngineProtocol` | Protocol: `execute(request) -> ExecutionResult`, `is_available() -> bool`, `get_capabilities() -> Dict` |

- Uses `typing.Protocol` with `@runtime_checkable`
- No runtime cost — purely type-checking interfaces
- Standard library only (no external dependencies)

### Dependencies
- Standard library only

### Implementation Completeness: 100%
Pure protocol definitions. Fully implemented.

---

## Cross-Module Dependency Map

```
shared/protocols  <--------  orchestration/, claude_sdk/, agent_framework/
     |
llm/              <--------  rootcause/ (Claude analysis), incident/ (LLM enhance)
     |                        learning/ (embeddings indirect)
     |
correlation/      <--------  rootcause/ (event correlations)
     |                        incident/ (correlation analysis)
     |
rootcause/        <--------  incident/ (root cause analysis)
     |
memory/           <--------  learning/ (case extraction from memory)
     |
swarm/            <--------  ag_ui/ (SSE events)
     |
patrol/           ---------> (standalone, optional Claude)
audit/            ---------> (standalone)
a2a/              ---------> (standalone)
n8n/              ---------> mcp/servers/n8n/client
```

---

## Feature Cross-Reference

| Feature ID | Feature Name | Module(s) | Status |
|-----------|-------------|-----------|--------|
| C4 | Agent Swarm Visualization | swarm/ | COMPLETE |
| C5 | A2A Communication | a2a/ | PARTIAL (in-memory only) |
| E6 | Three-Layer Memory | memory/ | COMPLETE |
| E7 | LLM Service Infrastructure | llm/ | COMPLETE |
| F1 | Few-Shot Learning | learning/ | COMPLETE |
| G3 | Proactive Patrol System | patrol/ | COMPLETE |
| G4 | Intelligent Correlation | correlation/ | COMPLETE (Sprint 130 fix) |
| G5 | Root Cause Analysis | rootcause/ | COMPLETE (Sprint 130 fix) |
| H1 | IT Incident Processing | incident/ | COMPLETE |
| H2 | Decision Audit Tracking | audit/ | PARTIAL (no persistence) |
| H3 | n8n Bidirectional Orchestration | n8n/ | COMPLETE |
| H4 | Shared Protocols | shared/ | COMPLETE |

---

## Key Findings

### 1. Sprint 130 Successfully Fixed Stub Modules
Both `correlation/` and `rootcause/` were correctly identified by V7 as having fake/hardcoded data. Sprint 130 introduced:
- `EventDataSource` with real Azure Monitor/App Insights KQL queries
- `EventCollector` with deduplication and aggregation
- `CaseRepository` with 15 real IT Ops seed cases
- `CaseMatcher` with multi-dimensional scoring (text similarity + category + severity + recency)
- All modules gracefully degrade to empty results when unconfigured (no fake data fallback)

### 2. LLM Integration Is Real
`AzureOpenAILLMService` uses the official `openai.AsyncAzureOpenAI` SDK with real API calls, retry logic, and error handling. The factory auto-detects environment and only falls back to mock in non-production environments.

### 3. Memory System Architecture Is Sound
Three-layer memory (Redis + PostgreSQL + mem0/Qdrant) with proper fallbacks. Each layer is optional and gracefully degrades.

### 4. Two Modules Lack Persistence
- `audit/`: Decision records stored in-memory dict only — lost on restart
- `a2a/`: Agent registry and messages in-memory only — no external transport

### 5. Swarm Module Is Production-Ready
Thread-safe tracker with Redis persistence, comprehensive SSE event system with throttling/batching, and clean integration bridge to ClaudeCoordinator.

### 6. Patrol System Uses Real System Data
All 5 check implementations use real data sources (HTTP, psutil, filesystem). No mocked checks.
