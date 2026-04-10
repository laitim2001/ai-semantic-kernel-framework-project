# R4 Semantic Analysis: backend/src/api/v1/

> V9 Codebase Analysis Round 4 — Per-file semantic summaries
> Generated: 2026-03-29 | Total: 107 non-init files, 46,341 LOC, 594 endpoints, 634 Pydantic schemas

---

## Module Index

| Module | Files | LOC | Endpoints | Phase |
|--------|-------|-----|-----------|-------|
| `__init__.py` + `dependencies.py` | 2 | 432 | 0 | Core |
| `a2a/` | 1 | 240 | 14 | 23 |
| `ag_ui/` | 4 | 3,624 | 30 | 15 |
| `agents/` | 1 | 394 | 6 | 1 |
| `audit/` | 3 | 987 | 15 | 1, 22 |
| `auth/` | 3 | 537 | 5+1migr | 18 |
| `autonomous/` | 1 | 372 | 4 | 22 |
| `cache/` | 2 | 460 | 9 | 1 |
| `chat_history/` | 1 | 169 | 3 | 35 |
| `checkpoints/` | 2 | 863 | 10 | 1, 5 |
| `claude_sdk/` | 8 | 3,204 | 40 | 12 |
| `code_interpreter/` | 3 | 1,537 | 14 | 8 |
| `concurrent/` | 4 | 2,397 | 15 | 2 |
| `connectors/` | 2 | 738 | 9 | 1 |
| `correlation/` | 1 | 591 | 7 | 23 |
| `dashboard/` | 1 | 192 | 2 | 1 |
| `devtools/` | 2 | 602 | 12 | 1 |
| `executions/` | 2 | 1,030 | 11 | 1 |
| `files/` | 2 | 419 | 6 | 20 |
| `groupchat/` | 3 | 2,774 | 42 | 2 |
| `handoff/` | 2 | 1,769 | 14 | 2 |
| `hybrid/` | 7 | 3,142 | 23 | 13-14 |
| `knowledge/` | 1 | 211 | 7 | 38 |
| `learning/` | 2 | 571 | 13 | 1 |
| `mcp/` | 2 | 832 | 13 | 9 |
| `memory/` | 2 | 668 | 7 | 22 |
| `n8n/` | 2 | 803 | 7 | 34 |
| `nested/` | 2 | 1,695 | 16 | 2 |
| `notifications/` | 2 | 536 | 11 | 1 |
| `orchestration/` | 6 | 2,664 | 29 | 28 |
| `orchestrator/` | 2 | 654 | 8 | 35 |
| `patrol/` | 1 | 558 | 9 | 23 |
| `performance/` | 1 | 431 | 11 | 1 |
| `planning/` | 2 | 2,078 | 46 | 2 |
| `prompts/` | 2 | 654 | 11 | 1 |
| `rootcause/` | 1 | 442 | 4 | 23 |
| `routing/` | 2 | 574 | 14 | 1 |
| `sandbox/` | 2 | 205 | 6 | 21 |
| `sessions/` | 4 | 2,234 | 23 | 10 |
| `swarm/` | 4 | 1,063 | 8 | 29 |
| `tasks/` | 1 | 260 | 9 | 37 |
| `templates/` | 2 | 652 | 11 | 1 |
| `triggers/` | 2 | 537 | 8 | 1 |
| `versioning/` | 2 | 610 | 14 | 1 |
| `workflows/` | 2 | 940 | 12 | 1, 34 |

---

## Per-File Semantic Summaries

### backend/src/api/v1/__init__.py (252 lines)
Router aggregation module. Assembles 47 registered routers into `api_router` with `/api/v1` prefix. Separates public routes (auth only) from protected routes (all others require JWT via `require_auth`). Imports span Phase 1 through Phase 38. Route ordering matters for `session_resume_router` which must precede `sessions_router` to avoid `/{session_id}` path collision.

### backend/src/api/v1/dependencies.py (180 lines)
Shared authentication dependency injection providers. Defines `OAuth2PasswordBearer` schemes (required + optional), plus 4 dependency functions: `get_current_user` (JWT decode + DB lookup), `get_current_user_optional` (silent fail), `get_current_active_admin` (role=admin check), `get_current_operator_or_admin` (role in admin/operator). All use async pattern with `AsyncSession`.

---

### a2a/ (Agent-to-Agent Communication)

### backend/src/api/v1/a2a/routes.py (240 lines)
A2A Communication Protocol API (Sprint 81). 14 endpoints under `/a2a` tag. Provides inter-agent messaging (`POST /message`, `GET /message/{id}`, `GET /messages/pending`, `GET /conversation/{id}`), agent registry (`POST /agents/register`, `DELETE /agents/{id}`, `GET /agents`, `GET /agents/{id}`, `POST /agents/discover`, `GET /agents/{id}/capabilities`, `POST /agents/{id}/heartbeat`, `PUT /agents/{id}/status`), plus statistics and maintenance cleanup. Uses global singleton `AgentDiscoveryService` and `MessageRouter` from `src.integrations.a2a`. 4 inline Pydantic schemas: `SendMessageRequest`, `RegisterAgentRequest`, `DiscoverAgentsRequest`, `UpdateStatusRequest`.

---

### ag_ui/ (AG-UI Protocol)

### backend/src/api/v1/ag_ui/__init__.py (23 lines)
Module init. Imports `router` from `routes.py` and `upload_router` from `upload.py`, includes upload_router under main router. Exports both.

### backend/src/api/v1/ag_ui/dependencies.py (714 lines)
Complex dependency injection for AG-UI SSE streaming. Creates `HybridEventBridge` with optional `HybridOrchestratorV2` and `ClaudeSDKClient`. Key functions: `get_hybrid_bridge` (creates bridge with orchestrator), `_create_approval_callback` (HITL approval flow for Write/Edit/Bash tools), `_try_create_claude_client` (creates ClaudeSDKClient with ApprovalHook), `_create_claude_executor` (wraps Claude API calls with multimodal support, S75-5), `get_redis_client`, `reset_hybrid_bridge`, `get_bridge_status`. Also provides user identification dependencies: `get_user_id_or_guest`, `get_user_id`, `get_user_id_optional`, `get_user_and_guest_id`. Supports simulation mode via `AG_UI_SIMULATION_MODE` env var.

### backend/src/api/v1/ag_ui/routes.py (1,889 lines)
Main AG-UI SSE streaming routes. 26 endpoints under `/ag-ui` tag. Core SSE endpoint `POST /ag-ui/` streams events via `HybridEventBridge`. Includes HITL approval endpoints (`GET /approvals/pending`, `POST /approvals/{id}/approve`, `POST /approvals/{id}/reject`, `GET /approvals/stats`), shared state management (`GET /state/{thread_id}`, `PUT /state/{thread_id}`, `GET /state/{thread_id}/conflicts`), test feature endpoints for workflow progress, mode switch, UI component, HITL, and prediction events, plus health/diagnostics/reset endpoints. Largest route file in the project.

### backend/src/api/v1/ag_ui/schemas.py (727 lines)
Comprehensive AG-UI Pydantic schemas. 30+ schema classes covering: execution modes (`AGUIExecutionMode`), tool definitions (`AGUIToolDefinition`), messages (`AGUIMessage`), attachments (`AGUIAttachment`), run agent request/response (`RunAgentRequest`, `RunAgentResponse`), health/error responses, HITL approval schemas (`ApprovalStatusEnum`, `RiskLevelEnum`, `ApprovalActionRequest`, `ApprovalResponse`, `ApprovalActionResponse`, `PendingApprovalsResponse`, `ApprovalStorageStats`), shared state schemas (`DiffOperationEnum`, `ConflictResolutionStrategyEnum`, `StateDiffSchema`, `ThreadStateResponse`, `ThreadStateUpdateRequest`, `StateUpdateResponse`, `StateConflictResponse`), and test schemas for workflow progress, mode switch, UI component, HITL, and prediction events.

### backend/src/api/v1/ag_ui/upload.py (294 lines)
File upload API for AG-UI (Sprint 68). 4 endpoints under `/ag-ui/upload` tag: `POST /` (upload file), `GET /list` (list uploads), `DELETE /{filename}` (delete file), `GET /storage` (storage usage). Uses `SandboxConfig` for per-user directory isolation, validates file extensions and size limits. 4 inline schemas: `UploadResponse`, `FileInfo`, `FileListResponse`, `DeleteResponse`.

---

### agents/ (Agent Management)

### backend/src/api/v1/agents/routes.py (394 lines)
Agent CRUD and execution API (Sprint 1). 6 endpoints under `/agents` tag: `POST /` (create), `GET /` (list with pagination/search), `GET /{id}` (get), `PUT /{id}` (update), `DELETE /{id}` (delete), `POST /{id}/run` (execute agent). Uses `AgentRepository` for DB operations and `AgentService` for execution. Schemas imported from `src.domain.agents.schemas`. Includes name uniqueness checks, version incrementing on update, and active status validation before run.

---

### audit/ (Audit Logging)

### backend/src/api/v1/audit/routes.py (408 lines)
Audit log query API (Sprint 3). 8 endpoints under `/audit` tag: `GET /logs` (filtered list), `GET /logs/{id}` (single entry), `GET /executions/{id}/trail` (execution audit trail), `GET /statistics` (aggregated stats), `GET /export` (CSV/JSON export), `GET /actions` (action type list), `GET /resources` (resource type list), `GET /health`. Uses `AuditLogger` from domain layer with global singleton pattern.

### backend/src/api/v1/audit/schemas.py (91 lines)
Audit API Pydantic schemas. 7 response classes: `AuditEntryResponse`, `AuditListResponse`, `AuditTrailResponse`, `AuditStatisticsResponse`, `ExportResponse`, `ActionListResponse`, `ResourceListResponse`. Chinese descriptions throughout.

### backend/src/api/v1/audit/decision_routes.py (488 lines)
Decision audit tracking API (Sprint 80). 7 endpoints under `/decisions` tag: `GET /` (query decisions), `GET /{id}` (decision detail), `GET /{id}/report` (explainability report), `POST /{id}/feedback` (add feedback), `GET /statistics` (decision stats), `GET /summary` (summary report), `GET /health`. Uses `DecisionTracker` and `AuditReportGenerator` from integrations. 12 inline schemas including `DecisionAuditResponse`, `ThinkingProcessResponse`, `AlternativeResponse`, `FeedbackRequest`, `StatisticsResponse`.

---

### auth/ (Authentication)

### backend/src/api/v1/auth/routes.py (217 lines)
Authentication API (Sprint 70). 4 endpoints under `/auth` tag: `POST /register` (create account, rate-limited 10/min), `POST /login` (OAuth2 password flow, rate-limited 10/min), `POST /refresh` (token refresh), `GET /me` (current user). Uses `AuthService` from domain layer. Integrates with `limiter` middleware for rate limiting.

### backend/src/api/v1/auth/dependencies.py (64 lines)
Convenience auth dependencies. Re-exports `get_current_user`, `get_current_user_optional`, `get_current_active_admin`, `get_current_operator_or_admin` from `api/v1/dependencies.py`. Adds `get_current_user_id` and `get_current_user_id_optional` helpers that return string IDs.

### backend/src/api/v1/auth/migration.py (256 lines)
Guest data migration API (Sprint 72). 1 endpoint: `POST /migrate-guest`. Migrates guest user sessions (DB update) and sandbox directories (file move) to authenticated user. Handles file name conflicts and empty directory cleanup. Uses `MigrateGuestRequest`/`MigrateGuestResponse` inline schemas.

---

### autonomous/ (Autonomous Planning - Phase 22 Testing)

### backend/src/api/v1/autonomous/routes.py (372 lines)
Autonomous task planning endpoints for UAT testing. 4 endpoints under `/claude/autonomous` tag: `POST /plan` (create plan), `GET /history` (task history), `GET /{task_id}` (task status with simulated progress), `POST /{task_id}/cancel` (cancel task). Uses in-memory `AutonomousTaskStore` with mock step generation and progress simulation. 6 inline schemas including `TaskStep`, `CreatePlanRequest`, `TaskResponse`.

---

### cache/ (LLM Response Caching)

### backend/src/api/v1/cache/routes.py (370 lines)
LLM cache management API (Sprint 2). 9 endpoints under `/cache` tag: `GET /stats`, `GET /config`, `POST /enable`, `POST /disable`, `POST /get`, `POST /set`, `POST /clear` (requires confirmation), `POST /warm`, `POST /reset-stats`. Uses `LLMCacheService` with Redis backend, falls back to mock service if Redis unavailable.

### backend/src/api/v1/cache/schemas.py (90 lines)
Cache API Pydantic schemas. 9 classes: `CacheStatsResponse`, `CacheEntryResponse`, `CacheSetRequest`, `CacheGetRequest`, `CacheClearRequest`, `CacheClearResponse`, `CacheWarmRequest`, `CacheWarmResponse`, `CacheConfigResponse`.

---

### chat_history/ (Chat History Sync)

### backend/src/api/v1/chat_history/routes.py (169 lines)
Chat history sync API (Sprint 111). 3 endpoints under `/chat-history` tag: `POST /sync` (bulk sync messages from frontend localStorage), `GET /{session_id}` (retrieve stored history), `DELETE /{session_id}` (delete history). Uses `SessionStore` with auto backend detection and 7-day TTL. Models imported from `src.domain.chat_history.models`.

---

### checkpoints/ (HITL Checkpoint Management)

### backend/src/api/v1/checkpoints/routes.py (694 lines)
Checkpoint approval workflow API (Sprint 29 migration). 10 endpoints under `/checkpoints` tag: `GET /pending` (pending list), `GET /{id}` (details), `POST /{id}/approve`, `POST /{id}/reject`, `GET /stats` (statistics), `GET /execution/{id}` (by execution), `POST /` (create), `POST /{id}/escalate`, `GET /expired` (expired list), `POST /cleanup` (purge expired). Hybrid approach: combines `CheckpointService` (DB storage) with `ApprovalWorkflowManager` (adapter layer). Status mapping between checkpoint and adapter approval statuses.

### backend/src/api/v1/checkpoints/schemas.py (169 lines)
Checkpoint Pydantic schemas. 9 classes: `CheckpointResponse`, `CheckpointSummaryResponse`, `CheckpointListResponse`, `PendingCheckpointsResponse`, `ApprovalRequest`, `RejectionRequest`, `CheckpointCreateRequest`, `CheckpointActionResponse`, `CheckpointStatsResponse`.

---

### claude_sdk/ (Claude Agent SDK)

### backend/src/api/v1/claude_sdk/schemas.py (106 lines)
Claude SDK core Pydantic schemas. 10 classes covering query (`QueryRequest`, `QueryResponse`, `ToolCallSchema`) and session (`CreateSessionRequest`, `SessionResponse`, `SessionQueryRequest`, `SessionQueryResponse`, `SessionHistoryMessageSchema`, `SessionHistoryResponse`, `CloseSessionResponse`).

### backend/src/api/v1/claude_sdk/routes.py (224 lines)
Claude SDK core API. 6 endpoints: `POST /query` (one-shot autonomous), `POST /sessions` (create), `POST /sessions/{id}/query` (session query), `DELETE /sessions/{id}` (close), `GET /sessions/{id}/history` (history), `GET /health` (status check). Uses global `ClaudeSDKClient` singleton.

### backend/src/api/v1/claude_sdk/autonomous_routes.py (435 lines)
Autonomous planning engine API (Sprint 79). 7 endpoints: `POST /plan` (generate plan with Extended Thinking), `GET /{plan_id}`, `POST /{plan_id}/execute` (SSE streaming execution), `DELETE /{plan_id}`, `GET /` (list plans), `POST /estimate` (resource estimation), `POST /{plan_id}/verify` (result verification). Uses `AutonomousPlanner`, `PlanExecutor`, `ResultVerifier` from integrations. 10 inline schemas.

### backend/src/api/v1/claude_sdk/hooks_routes.py (403 lines)
Hook lifecycle management API (Sprint 51). 6 endpoints for managing Claude SDK hooks (pre/post processing, approval hooks). Provides hook registration, listing, removal, and execution testing.

### backend/src/api/v1/claude_sdk/hybrid_routes.py (433 lines)
Hybrid context integration API (Sprint 54). 5 endpoints bridging Claude SDK with MAF context, including context sync, status, and mode negotiation.

### backend/src/api/v1/claude_sdk/intent_routes.py (569 lines)
Intent classification API (Sprint 50). 6 endpoints for classifying user intents using Claude SDK, including batch classification, confidence thresholds, and category management.

### backend/src/api/v1/claude_sdk/mcp_routes.py (474 lines)
MCP integration routes (Sprint 51). 6 endpoints for managing MCP server connections through Claude SDK, including server discovery, tool listing, and execution proxying.

### backend/src/api/v1/claude_sdk/tools_routes.py (364 lines)
Tool management API (Sprint 49). 4 endpoints for managing tools available to Claude SDK agents, including registration, listing, and capability queries.

---

### code_interpreter/ (Code Execution)

### backend/src/api/v1/code_interpreter/routes.py (779 lines)
Code interpreter API (Sprint 37). 11 endpoints for code execution via OpenAI Responses API: execute code, get execution status, list executions, cancel, get output, upload file, list files, delete file, get supported languages, health check, and batch execute. Uses sandbox isolation.

### backend/src/api/v1/code_interpreter/schemas.py (317 lines)
Code interpreter Pydantic schemas. Covers execution requests/responses, file operations, language support, and batch execution.

### backend/src/api/v1/code_interpreter/visualization.py (441 lines)
Visualization generation endpoints. 3 endpoints for creating charts and plots from code execution results. Supports multiple visualization types.

---

### concurrent/ (Fork-Join Execution)

### backend/src/api/v1/concurrent/routes.py (1,094 lines)
Concurrent execution API (Sprint 7). 13 endpoints for fork-join pattern execution: create concurrent task, get task status, list tasks, cancel, get results, create fork, join results, get execution graph, retry failed, batch create, get metrics, health check, and cleanup. Uses `ConcurrentBuilderAdapter`.

### backend/src/api/v1/concurrent/schemas.py (285 lines)
Concurrent execution Pydantic schemas covering task definition, fork-join configuration, execution results, and metrics.

### backend/src/api/v1/concurrent/adapter_service.py (518 lines)
Service layer bridging concurrent routes to `ConcurrentBuilderAdapter`. Manages task lifecycle and orchestrates fork-join execution patterns.

### backend/src/api/v1/concurrent/websocket.py (500 lines)
WebSocket endpoint for real-time concurrent execution monitoring. 2 WebSocket endpoints for streaming task progress and execution graph updates.

---

### connectors/ (Cross-System Connectors)

### backend/src/api/v1/connectors/routes.py (591 lines)
Connector management API (Sprint 1). 9 endpoints: CRUD for connectors, test connection, sync, list types, get connector status, health check. Manages cross-system integrations.

### backend/src/api/v1/connectors/schemas.py (147 lines)
Connector Pydantic schemas for connector configuration, status, and test results.

---

### correlation/ (Event Correlation)

### backend/src/api/v1/correlation/routes.py (591 lines)
Multi-agent event correlation API (Sprint 82). 7 endpoints: correlate events, get correlation results, list correlations, get timeline, get pattern analysis, health check, cleanup. Uses `CorrelationEngine` from integrations.

---

### dashboard/ (Analytics Dashboard)

### backend/src/api/v1/dashboard/routes.py (192 lines)
Dashboard analytics API. 2 endpoints: `GET /dashboard/summary` (aggregated system metrics), `GET /dashboard/health` (service health overview). Provides high-level system status.

---

### devtools/ (Developer Tools)

### backend/src/api/v1/devtools/routes.py (412 lines)
Developer debugging tools API (Sprint 4). 12 endpoints: execution trace, step details, replay execution, compare executions, get logs, performance metrics, request inspection, debug session management, config viewer, health check, clear traces, export traces. All use in-memory stores.

### backend/src/api/v1/devtools/schemas.py (190 lines)
DevTools Pydantic schemas for execution traces, step details, performance metrics, and debug sessions.

---

### executions/ (Execution Tracking)

### backend/src/api/v1/executions/routes.py (825 lines)
Execution lifecycle management API (Sprint 1-2). 11 endpoints: create execution, get status, list executions, cancel, get results, get timeline, retry, batch status, get metrics, pause/resume, health check. Uses `ExecutionService` from domain layer with `ExecutionRepository`.

### backend/src/api/v1/executions/schemas.py (205 lines)
Execution Pydantic schemas covering execution state, results, timeline events, and metrics.

---

### files/ (File Management)

### backend/src/api/v1/files/routes.py (249 lines)
File attachment management API (Sprint 75). 6 endpoints: upload file, list files, get file metadata, download file, delete file, get storage quota. Uses `SandboxConfig` for per-user isolation.

### backend/src/api/v1/files/schemas.py (170 lines)
File management Pydantic schemas for upload, metadata, quota, and download responses.

---

### groupchat/ (Multi-Agent GroupChat)

### backend/src/api/v1/groupchat/routes.py (1,770 lines)
GroupChat multi-turn conversation API (Sprint 9). 42 endpoints -- the second largest route file. Covers: group creation/management, participant management, message sending/listing, turn management, moderator controls, voting, topic management, history export, analytics, health check. Uses `GroupChatBuilderAdapter`.

### backend/src/api/v1/groupchat/schemas.py (403 lines)
GroupChat Pydantic schemas for groups, participants, messages, turns, votes, topics, and analytics.

### backend/src/api/v1/groupchat/multiturn_service.py (601 lines)
Service layer for multi-turn GroupChat conversations. Manages conversation state, turn rotation, and message routing between multiple agents.

---

### handoff/ (Agent Handoff)

### backend/src/api/v1/handoff/routes.py (1,006 lines)
Agent handoff and collaboration API (Sprint 8). 14 endpoints: create handoff, get status, list handoffs, accept/reject, complete, cancel, get history, get metrics, retry, batch create, get recommendations, health check, cleanup. Uses `HandoffBuilderAdapter`.

### backend/src/api/v1/handoff/schemas.py (763 lines)
Handoff Pydantic schemas covering handoff requests, agent matching, status transitions, and collaboration metrics.

---

### hybrid/ (Hybrid MAF+Claude SDK)

### backend/src/api/v1/hybrid/dependencies.py (146 lines)
Hybrid module dependency injection. Provides `HybridOrchestratorV2`, `HybridContextSync`, and `HybridSwitchManager` instances.

### backend/src/api/v1/hybrid/schemas.py (247 lines)
Core hybrid Pydantic schemas for orchestrator configuration, mode selection, and bridge status.

### backend/src/api/v1/hybrid/context_routes.py (503 lines)
Context synchronization API (Sprint 53). 5 endpoints: sync context, get context status, reset context, get context diff, health check. Synchronizes state between MAF and Claude SDK.

### backend/src/api/v1/hybrid/core_routes.py (580 lines)
Core hybrid operations API (Sprint 52-54). 4 endpoints: execute hybrid query, get orchestrator status, configure mode, health check.

### backend/src/api/v1/hybrid/risk_routes.py (425 lines)
Risk assessment API (Sprint 55). 7 endpoints: assess risk, get risk history, get risk config, update thresholds, get risk statistics, batch assess, health check.

### backend/src/api/v1/hybrid/risk_schemas.py (371 lines)
Risk assessment Pydantic schemas for risk levels, factors, thresholds, and assessment results.

### backend/src/api/v1/hybrid/switch_routes.py (741 lines)
Mode switching API (Sprint 56). 7 endpoints: switch mode, get switch status, get switch history, configure auto-switch, get recommendations, rollback switch, health check.

### backend/src/api/v1/hybrid/switch_schemas.py (264 lines)
Mode switch Pydantic schemas for switch requests, status, history, and recommendations.

---

### knowledge/ (Knowledge Management)

### backend/src/api/v1/knowledge/routes.py (211 lines)
Knowledge base management API (Sprint 119). 7 endpoints: ingest document, query knowledge, list documents, get document, delete document, get statistics, health check.

---

### learning/ (Few-Shot Learning)

### backend/src/api/v1/learning/routes.py (374 lines)
Few-shot learning API (Sprint 3). 13 endpoints: add example, get examples, search examples, delete example, get categories, get statistics, batch add, export, import, clear category, validate example, optimize, health check.

### backend/src/api/v1/learning/schemas.py (197 lines)
Learning Pydantic schemas for examples, categories, search results, and optimization metrics.

---

### mcp/ (MCP Server Management)

### backend/src/api/v1/mcp/routes.py (645 lines)
MCP server management API (Sprint 39-41). 13 endpoints: list servers, get server info, start/stop server, get tools, execute tool, get server logs, register server, unregister, health check, batch execute, get capabilities, server statistics.

### backend/src/api/v1/mcp/schemas.py (187 lines)
MCP Pydantic schemas for server configuration, tool definitions, execution results, and server status.

---

### memory/ (Memory System)

### backend/src/api/v1/memory/routes.py (476 lines)
Memory system API (Sprint 79). 7 endpoints: store memory, search memories, get memory by ID, delete memory, list memories, get memory statistics, health check. Uses mem0 integration for semantic/episodic/procedural memory.

### backend/src/api/v1/memory/schemas.py (192 lines)
Memory Pydantic schemas for memory entries, search queries, and statistics.

---

### n8n/ (n8n Integration)

### backend/src/api/v1/n8n/routes.py (522 lines)
n8n workflow integration API (Sprint 124). 7 endpoints: trigger workflow, get execution status, list workflows, get workflow details, import workflow, export workflow, health check.

### backend/src/api/v1/n8n/schemas.py (281 lines)
n8n Pydantic schemas for workflow definitions, triggers, execution status, and import/export formats.

---

### nested/ (Nested Workflows)

### backend/src/api/v1/nested/routes.py (1,146 lines)
Nested workflow orchestration API (Sprint 11). 16 endpoints: create nested workflow, get status, list workflows, execute, cancel, get results, get execution graph, add sub-workflow, remove sub-workflow, reorder, validate, clone, get metrics, batch execute, health check, cleanup. Uses `NestedWorkflowAdapter`.

### backend/src/api/v1/nested/schemas.py (549 lines)
Nested workflow Pydantic schemas for workflow trees, sub-workflow configuration, execution graphs, and validation results.

---

### notifications/ (Notification System)

### backend/src/api/v1/notifications/routes.py (397 lines)
Notification management API (Sprint 3). 11 endpoints: send notification, list notifications, get notification, mark read, mark all read, delete, get channels, configure channel, get notification stats, batch send, health check. Supports Teams integration.

### backend/src/api/v1/notifications/schemas.py (139 lines)
Notification Pydantic schemas for notification messages, channels, and delivery status.

---

### orchestration/ (Three-Tier Intent Routing)

### backend/src/api/v1/orchestration/routes.py (336 lines)
Policy management API (Sprint 96). 7 endpoints: get routing policies, create policy, update policy, delete policy, get policy stats, test policy, health check.

### backend/src/api/v1/orchestration/schemas.py (339 lines)
Orchestration Pydantic schemas for routing policies, intent categories, and routing decisions.

### backend/src/api/v1/orchestration/intent_routes.py (488 lines)
Intent classification API (Sprint 96). 4 endpoints: classify intent (three-tier routing), batch classify, get classification history, get routing metrics. Uses `BusinessIntentRouter` with PatternMatcher -> SemanticRouter -> LLMClassifier pipeline.

### backend/src/api/v1/orchestration/dialog_routes.py (504 lines)
Guided dialog API (Sprint 98). 4 endpoints: start dialog session, advance dialog step, get dialog state, abandon dialog. Uses `GuidedDialogEngine`.

### backend/src/api/v1/orchestration/approval_routes.py (513 lines)
HITL approval flow API (Sprint 98). 4 endpoints: get pending approvals, approve, reject, get approval history. Integrates with `HITLController`.

### backend/src/api/v1/orchestration/webhook_routes.py (354 lines)
Webhook management API (Sprint 114). 3 endpoints: register webhook, list webhooks, delete webhook. Enables external system callbacks.

### backend/src/api/v1/orchestration/route_management.py (439 lines)
Route management API (Sprint 115). 7 endpoints: create route, list routes, update route, delete route, test route, get route stats, health check. Manages custom routing rules.

---

### orchestrator/ (Orchestrator Chat Pipeline)

### backend/src/api/v1/orchestrator/routes.py (509 lines)
Orchestrator chat E2E pipeline API (Sprint 108). 6 endpoints: `POST /chat` (main chat endpoint with full pipeline), `POST /chat/stream` (SSE streaming), `GET /chat/models` (available models), `GET /chat/status` (pipeline status), `POST /chat/reset` (reset state), `GET /health`. Central chat pipeline orchestrating intent routing, model selection, and response generation.

### backend/src/api/v1/orchestrator/session_routes.py (145 lines)
Session resume API (Sprint 115). 2 endpoints: `POST /sessions/{id}/resume` (resume interrupted session), `GET /sessions/{id}/state` (get session state for resumption). Must be registered before sessions_router to avoid path collision.

---

### patrol/ (Continuous Monitoring)

### backend/src/api/v1/patrol/routes.py (558 lines)
Patrol mode monitoring API (Sprint 82). 9 endpoints: start patrol, stop patrol, get patrol status, get findings, acknowledge finding, get patrol history, configure patrol, get patrol metrics, health check. Uses `PatrolService` from integrations.

---

### performance/ (Performance Monitoring)

### backend/src/api/v1/performance/routes.py (431 lines)
Performance monitoring API (Sprint 12). 11 endpoints: get current metrics, get historical metrics, get benchmarks, run benchmark, get optimization suggestions, apply optimization, get profiling data, start profiling, stop profiling, get cache performance, health check.

---

### planning/ (Dynamic Planning)

### backend/src/api/v1/planning/routes.py (1,488 lines)
Dynamic planning and autonomous decisions API (Sprint 10). 46 endpoints -- the largest endpoint count per file. Covers: plan CRUD, step management, execution, validation, optimization, template management, plan comparison, dependency analysis, resource estimation, batch operations, versioning, export/import, health check. Uses `MagenticBuilder` adapter pattern.

### backend/src/api/v1/planning/schemas.py (590 lines)
Planning Pydantic schemas for plans, steps, dependencies, resources, templates, and optimization metrics.

---

### prompts/ (Prompt Template Management)

### backend/src/api/v1/prompts/routes.py (520 lines)
Prompt template management API (Sprint 3). 11 endpoints: CRUD for prompts, render prompt with variables, list categories, search prompts, duplicate, get statistics, validate, batch render, health check.

### backend/src/api/v1/prompts/schemas.py (134 lines)
Prompt Pydantic schemas for template definitions, render requests, and validation results.

---

### rootcause/ (Root Cause Analysis)

### backend/src/api/v1/rootcause/routes.py (442 lines)
Root cause analysis API (Sprint 82). 4 endpoints: analyze root cause, get analysis results, list analyses, health check. Uses `RootCauseAnalyzer` from integrations for incident investigation.

---

### routing/ (Cross-Scenario Routing)

### backend/src/api/v1/routing/routes.py (443 lines)
Cross-scenario routing and decision logic API (Sprint 1). 14 endpoints: create route, get route, list routes, update route, delete route, test route, evaluate conditions, get route metrics, clone route, batch create, get decision tree, validate route, export routes, health check.

### backend/src/api/v1/routing/schemas.py (131 lines)
Routing Pydantic schemas for route definitions, conditions, and decision trees.

---

### sandbox/ (Sandbox Security)

### backend/src/api/v1/sandbox/routes.py (136 lines)
Sandbox execution API (Sprint 77-78). 6 endpoints: execute in sandbox, get execution result, list sandbox sessions, get sandbox config, cleanup sandbox, health check. Provides isolated code execution environment.

### backend/src/api/v1/sandbox/schemas.py (69 lines)
Sandbox Pydantic schemas for execution requests, results, and configuration.

---

### sessions/ (Session Management)

### backend/src/api/v1/sessions/routes.py (678 lines)
Session management API (Sprint 42-44). 14 endpoints: create session, get session, list sessions, update session, delete session, get session messages, add message, clear messages, get session metadata, set metadata, fork session, merge sessions, get session stats, health check. Uses `SessionService` from domain layer.

### backend/src/api/v1/sessions/schemas.py (320 lines)
Session Pydantic schemas for session configuration, messages, metadata, and fork/merge operations.

### backend/src/api/v1/sessions/chat.py (570 lines)
Chat endpoint within session context. 6 endpoints for sending messages within sessions, including streaming responses and tool-augmented chat.

### backend/src/api/v1/sessions/websocket.py (666 lines)
WebSocket endpoints for real-time session communication. 3 WebSocket endpoints for bidirectional messaging, typing indicators, and session state synchronization.

---

### swarm/ (Agent Swarm)

### backend/src/api/v1/swarm/routes.py (208 lines)
Agent swarm status API (Sprint 100). 3 endpoints: `GET /swarm/status` (swarm status), `GET /swarm/workers` (worker list), `GET /swarm/health` (health check). Uses `SwarmManager` from integrations.

### backend/src/api/v1/swarm/schemas.py (143 lines)
Swarm Pydantic schemas for swarm status, worker state, and task assignment.

### backend/src/api/v1/swarm/demo.py (690 lines)
Swarm demo/test API with SSE (Sprint 107). 5 endpoints: `POST /swarm/demo/start` (start demo swarm), `GET /swarm/demo/stream` (SSE event stream), `GET /swarm/demo/status` (demo status), `POST /swarm/demo/stop` (stop demo), `POST /swarm/demo/reset` (reset demo). Provides comprehensive swarm demonstration with real-time visualization via SSE.

### backend/src/api/v1/swarm/dependencies.py (22 lines)
Swarm dependency injection. Provides `SwarmManager` instance.

---

### tasks/ (Task Management)

### backend/src/api/v1/tasks/routes.py (260 lines)
Task management API (Sprint 113). 9 endpoints: create task, get task, list tasks, update task, delete task, assign task, complete task, get task history, health check.

---

### templates/ (Workflow Templates)

### backend/src/api/v1/templates/routes.py (436 lines)
Workflow template marketplace API (Sprint 1). 11 endpoints: CRUD for templates, publish/unpublish, clone template, list categories, search, get popular templates, validate template, health check.

### backend/src/api/v1/templates/schemas.py (216 lines)
Template Pydantic schemas for template definitions, categories, and marketplace listings.

---

### triggers/ (Webhook Triggers)

### backend/src/api/v1/triggers/routes.py (424 lines)
Webhook trigger management API (Sprint 1). 8 endpoints: CRUD for triggers, enable/disable, test trigger, get trigger logs, health check. Manages workflow execution triggers.

### backend/src/api/v1/triggers/schemas.py (113 lines)
Trigger Pydantic schemas for trigger configuration, webhook payloads, and trigger logs.

---

### versioning/ (Template Versioning)

### backend/src/api/v1/versioning/routes.py (429 lines)
Template version management API (Sprint 1). 14 endpoints: create version, get version, list versions, compare versions, rollback, get diff, set active version, get version history, tag version, list tags, delete version, get version metrics, promote version, health check.

### backend/src/api/v1/versioning/schemas.py (181 lines)
Versioning Pydantic schemas for version metadata, diffs, tags, and comparison results.

---

### workflows/ (Workflow Management)

### backend/src/api/v1/workflows/routes.py (577 lines)
Workflow CRUD and validation API (Sprint 1). 9 endpoints: create workflow, get workflow, list workflows, update workflow, delete workflow, validate workflow, execute workflow, clone workflow, health check. Uses `WorkflowService` from domain layer.

### backend/src/api/v1/workflows/graph_routes.py (363 lines)
Workflow graph visualization API (Sprint 133). 3 endpoints: `GET /workflows/{id}/graph` (get visual graph data), `POST /workflows/{id}/graph/layout` (compute layout), `GET /workflows/{id}/graph/export` (export graph as image/SVG). Provides React Flow compatible graph data.

---

## Cross-Cutting Patterns

### Authentication
- Public routes: only `auth/routes.py` (login, register, refresh)
- All other routes protected by `require_auth` JWT dependency at the `protected_router` level
- Per-route user access via `get_current_user` or `get_current_user_optional`

### Dependency Injection
- Global singleton pattern used extensively (e.g., `_cache_service`, `_audit_logger`, `_planner`)
- FastAPI `Depends()` for request-scoped dependencies (DB sessions, services)
- Module-level `dependencies.py` files in: root, ag_ui, auth, hybrid, swarm

### Error Handling
- Consistent use of `HTTPException` with appropriate status codes
- `try/except` blocks with logging in all endpoint handlers
- 404 for not found, 400 for validation, 500 for internal errors

### In-Memory Storage
- Several modules use in-memory stores for development/testing: autonomous, devtools, patrol, planning, groupchat
- Pattern: global `Optional` variable + `get_or_create` factory function

### SSE Streaming
- Used in: ag_ui (main chat), claude_sdk/autonomous (plan execution), swarm/demo (visualization), concurrent/websocket, sessions/websocket

### Total Verified Counts
- **107 non-init Python files**
- **594 endpoint decorators** (confirmed by R3 verification)
- **634 Pydantic schema classes** (BaseModel subclasses)
- **46,341 total lines of code**
- **70 files containing endpoints**
- **43 modules** (directories)
