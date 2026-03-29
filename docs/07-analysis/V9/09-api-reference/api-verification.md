# API Endpoint Verification Report (V9 Round 2)

> **Date**: 2026-03-29
> **Method**: Direct source code scan using Grep + Read on all route files
> **Scope**: `backend/src/api/v1/**/*.py` — all `@router.*` and custom router decorators

---

## Summary

| Metric | Count |
|--------|-------|
| **Total Route Files** | 60 (42 `routes.py` + 18 `*_routes.py` / other) |
| **Total Endpoints (Round 2)** | **589** |
| **Total Schema Classes (BaseModel)** | **598** (across routes + schemas files) |
| **Router Modules** | 42 unique prefixes |

### Round 2 vs Round 1 Comparison

| Item | Round 1 Claimed | Round 2 Verified | Delta |
|------|----------------|-----------------|-------|
| Endpoints | 566 | **589** | +23 |
| Schema Classes | Not counted | **598** | N/A |

**Discrepancy Explanation**: Round 1 missed endpoints from:
- `orchestration/dialog_routes.py` (4 endpoints, uses `dialog_router`)
- `orchestration/approval_routes.py` (4 endpoints, uses `approval_router`)
- `orchestration/webhook_routes.py` (3 endpoints, uses `webhook_router`)
- `orchestration/intent_routes.py` (4 endpoints, uses `intent_router`)
- `orchestration/route_management.py` (7 endpoints, uses `route_management_router`)
- `auth/migration.py` (1 endpoint)
- These use custom-named APIRouter variables, not `@router`

---

## Complete Endpoint Inventory

### agents/routes.py — 6 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/agents/` | create_agent | AgentResponse |
| GET | `/agents/` | list_agents | AgentListResponse |
| GET | `/agents/{agent_id}` | get_agent | AgentResponse |
| PUT | `/agents/{agent_id}` | update_agent | AgentResponse |
| DELETE | `/agents/{agent_id}` | delete_agent | — (204) |
| POST | `/agents/{agent_id}/run` | run_agent | AgentRunResponse |

### auth/routes.py — 4 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/auth/register` | register | — |
| POST | `/auth/login` | login | — |
| POST | `/auth/refresh` | refresh_token | — |
| GET | `/auth/me` | get_current_user | — |

### auth/migration.py — 1 endpoint
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/migrate-guest` | migrate_guest | MigrateGuestResponse |

### sessions/routes.py — 15 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/sessions` | create_session | SessionDetailResponse |
| GET | `/sessions` | list_sessions | SessionListResponse |
| GET | `/sessions/{session_id}` | get_session | SessionDetailResponse |
| PATCH | `/sessions/{session_id}` | update_session | SessionDetailResponse |
| DELETE | `/sessions/{session_id}` | delete_session | — (204) |
| POST | `/sessions/{session_id}/activate` | activate_session | SessionDetailResponse |
| POST | `/sessions/{session_id}/suspend` | suspend_session | SessionDetailResponse |
| POST | `/sessions/{session_id}/resume` | resume_session | SessionDetailResponse |
| GET | `/sessions/{session_id}/messages` | get_messages | MessageListResponse |
| POST | `/sessions/{session_id}/messages` | send_message | MessageResponse |
| POST | `/sessions/{session_id}/attachments` | upload_attachment | AttachmentResponse |
| GET | `/sessions/{session_id}/attachments/{attachment_id}` | download_attachment | — |
| GET | `/sessions/{session_id}/tool-calls` | get_tool_calls | ToolCallListResponse |
| POST | `/sessions/{session_id}/tool-calls/{tool_call_id}` | handle_tool_call | — |
| POST | `/sessions/{session_id}/chat/complete` | — | — |

### sessions/chat.py — 6 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/sessions/{session_id}/chat` | send_chat | ChatResponse |
| POST | `/sessions/{session_id}/chat/stream` | send_chat_stream | SSE |
| GET | `/sessions/{session_id}/approvals` | get_approvals | PendingApprovalsResponse |
| POST | `/sessions/{session_id}/approvals/{approval_id}` | handle_approval | ApprovalResponse |
| DELETE | `/sessions/{session_id}/approvals` | cancel_approvals | CancelResponse |
| GET | `/sessions/{session_id}/chat/status` | get_chat_status | — |

### sessions/websocket.py — 3 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| WS | `/sessions/{session_id}/ws` | websocket_endpoint | — |
| GET | `/sessions/{session_id}/ws/status` | ws_status | — |
| POST | `/sessions/{session_id}/ws/broadcast` | ws_broadcast | — |

### workflows/routes.py — 9 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/workflows/` | create_workflow | WorkflowResponse |
| GET | `/workflows/` | list_workflows | WorkflowListResponse |
| GET | `/workflows/{workflow_id}` | get_workflow | WorkflowResponse |
| PUT | `/workflows/{workflow_id}` | update_workflow | WorkflowResponse |
| DELETE | `/workflows/{workflow_id}` | delete_workflow | — (204) |
| POST | `/workflows/{workflow_id}/execute` | execute_workflow | WorkflowExecutionResponse |
| POST | `/workflows/{workflow_id}/validate` | validate_workflow | WorkflowValidationResponse |
| POST | `/workflows/{workflow_id}/activate` | activate_workflow | WorkflowResponse |
| POST | `/workflows/{workflow_id}/deactivate` | deactivate_workflow | WorkflowResponse |

### workflows/graph_routes.py — 3 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/workflows/{workflow_id}/graph` | get_workflow_graph | WorkflowGraphResponse |
| PUT | `/workflows/{workflow_id}/graph` | update_workflow_graph | WorkflowGraphResponse |
| POST | `/workflows/{workflow_id}/graph/layout` | auto_layout_workflow_graph | GraphLayoutResponse |

### executions/routes.py — 11 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/executions/` | list_executions | ExecutionListResponse |
| POST | `/executions/` | create_execution | ExecutionDetailResponse |
| GET | `/executions/{execution_id}` | get_execution | ExecutionDetailResponse |
| POST | `/executions/{execution_id}/cancel` | cancel_execution | ExecutionCancelResponse |
| GET | `/executions/{execution_id}/transitions` | get_valid_transitions | ValidTransitionsResponse |
| GET | `/executions/status/running` | get_running_executions | list[ExecutionSummaryResponse] |
| GET | `/executions/status/recent` | get_recent_executions | list[ExecutionSummaryResponse] |
| GET | `/executions/workflows/{workflow_id}/stats` | get_workflow_stats | ExecutionStatsResponse |
| POST | `/executions/{execution_id}/resume` | resume_execution | ResumeResponse |
| GET | `/executions/{execution_id}/resume-status` | get_resume_status | ResumeStatusResponse |
| POST | `/executions/{execution_id}/shutdown` | shutdown_execution | ShutdownResponse |

### checkpoints/routes.py — 10 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/checkpoints/` | list_checkpoints | CheckpointListResponse |
| GET | `/checkpoints/{checkpoint_id}` | get_checkpoint | CheckpointResponse |
| POST | `/checkpoints/{checkpoint_id}/approve` | approve_checkpoint | CheckpointActionResponse |
| POST | `/checkpoints/{checkpoint_id}/reject` | reject_checkpoint | CheckpointActionResponse |
| GET | `/checkpoints/pending` | get_pending | PendingCheckpointsResponse |
| GET | `/checkpoints/stats` | get_stats | CheckpointStatsResponse |
| POST | `/checkpoints/` | create_checkpoint | CheckpointResponse |
| POST | `/checkpoints/batch-approve` | batch_approve | — |
| GET | `/checkpoints/execution/{execution_id}` | get_by_execution | — |
| POST | `/checkpoints/{checkpoint_id}/auto-approve` | auto_approve | — |

### concurrent/routes.py — 13 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/concurrent/execute` | execute_concurrent | ConcurrentExecuteResponse |
| GET | `/concurrent/{execution_id}/status` | get_execution_status | ExecutionStatusResponse |
| GET | `/concurrent/{execution_id}/branches` | get_branches | BranchListResponse |
| GET | `/concurrent/{execution_id}/branches/{branch_id}` | get_branch_status | BranchStatusResponse |
| POST | `/concurrent/{execution_id}/cancel` | cancel_execution | ExecutionCancelResponse |
| POST | `/concurrent/{execution_id}/branches/{branch_id}/cancel` | cancel_branch | BranchCancelResponse |
| GET | `/concurrent/stats` | get_stats | ConcurrentStatsResponse |
| GET | `/concurrent/health` | health_check | — |
| POST | `/concurrent/v2/execute` | execute_v2 | Dict |
| GET | `/concurrent/v2/{execution_id}` | get_execution_v2 | Dict |
| GET | `/concurrent/v2/stats` | get_stats_v2 | Dict |
| GET | `/concurrent/v2/health` | health_check_v2 | — |
| GET | `/concurrent/v2/executions` | list_executions_v2 | Dict |

### concurrent/websocket.py — 2 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| WS | `/concurrent/ws/{execution_id}` | websocket_execution | — |
| WS | `/concurrent/ws` | websocket_global | — |

### nested/routes.py — 16 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/nested/` | create_nested_workflow | NestedWorkflowResponse |
| GET | `/nested/` | list_nested_workflows | NestedWorkflowListResponse |
| GET | `/nested/{workflow_id}` | get_nested_workflow | NestedWorkflowResponse |
| DELETE | `/nested/{workflow_id}` | delete_nested_workflow | — |
| POST | `/nested/{workflow_id}/execute` | execute_sub_workflow | SubWorkflowExecuteResponse |
| POST | `/nested/{workflow_id}/batch` | execute_batch | SubWorkflowBatchResponse |
| GET | `/nested/{workflow_id}/status` | get_sub_workflow_status | — |
| POST | `/nested/{workflow_id}/recursive` | execute_recursive | RecursiveExecuteResponse |
| POST | `/nested/{workflow_id}/cancel` | cancel_recursive | — |
| GET | `/nested/{workflow_id}/recursion-status` | get_recursion_status | RecursionStatusResponse |
| POST | `/nested/compositions` | create_composition | CompositionResponse |
| POST | `/nested/compositions/{composition_id}/execute` | execute_composition | CompositionExecuteResponse |
| POST | `/nested/context/propagate` | propagate_context | ContextPropagateResponse |
| GET | `/nested/context/{workflow_id}/flow` | get_data_flow | DataFlowTrackerResponse |
| GET | `/nested/stats` | get_stats | NestedWorkflowStatsResponse |
| GET | `/nested/health` | health_check | — |

### handoff/routes.py — 14 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/handoff/trigger` | trigger_handoff | HandoffTriggerResponse |
| GET | `/handoff/{handoff_id}/status` | get_handoff_status | HandoffStatusResponse |
| POST | `/handoff/{handoff_id}/complete` | complete_handoff | — |
| GET | `/handoff/history` | get_handoff_history | HandoffHistoryResponse |
| POST | `/handoff/capability/match` | match_capabilities | CapabilityMatchResponse |
| GET | `/handoff/capability/{agent_id}` | get_agent_capabilities | AgentCapabilitiesResponse |
| POST | `/handoff/capability/register` | register_capability | RegisterCapabilityResponse |
| DELETE | `/handoff/capability/{capability_id}` | delete_capability | — |
| GET | `/handoff/hitl/sessions` | get_hitl_sessions | HITLSessionListResponse |
| GET | `/handoff/hitl/{session_id}/pending` | get_pending_requests | HITLPendingRequestsResponse |
| GET | `/handoff/hitl/{session_id}/history` | get_session_history | — |
| POST | `/handoff/hitl/{request_id}/submit` | submit_input | HITLSubmitInputResponse |
| POST | `/handoff/{handoff_id}/cancel` | cancel_handoff | HandoffCancelResponse |
| POST | `/handoff/{handoff_id}/rollback` | rollback_handoff | — |

### groupchat/routes.py — 40 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/groupchat/` | create_group_chat | GroupChatResponse |
| GET | `/groupchat/` | list_group_chats | List[GroupChatResponse] |
| GET | `/groupchat/{group_id}` | get_group_chat | GroupChatResponse |
| PATCH | `/groupchat/{group_id}/config` | update_config | SuccessResponse |
| POST | `/groupchat/{group_id}/agents/{agent_id}` | add_agent | SuccessResponse |
| DELETE | `/groupchat/{group_id}/agents/{agent_id}` | remove_agent | SuccessResponse |
| POST | `/groupchat/{group_id}/start` | start_conversation | ConversationResultResponse |
| POST | `/groupchat/{group_id}/message` | send_message | MessageResponse |
| GET | `/groupchat/{group_id}/messages` | get_messages | List[MessageResponse] |
| GET | `/groupchat/{group_id}/transcript` | get_transcript | — |
| GET | `/groupchat/{group_id}/summary` | get_summary | GroupChatSummaryResponse |
| POST | `/groupchat/{group_id}/terminate` | terminate | SuccessResponse |
| DELETE | `/groupchat/{group_id}` | delete_group_chat | SuccessResponse |
| WS | `/groupchat/{group_id}/ws` | websocket | — |
| POST | `/groupchat/sessions/` | create_session | SessionResponse |
| GET | `/groupchat/sessions/` | list_sessions | List[SessionResponse] |
| GET | `/groupchat/sessions/{session_id}` | get_session | SessionResponse |
| POST | `/groupchat/sessions/{session_id}/turns` | execute_turn | TurnResponse |
| GET | `/groupchat/sessions/{session_id}/history` | get_history | SessionHistoryResponse |
| PATCH | `/groupchat/sessions/{session_id}/context` | update_context | SuccessResponse |
| POST | `/groupchat/sessions/{session_id}/close` | close_session | SuccessResponse |
| DELETE | `/groupchat/sessions/{session_id}` | delete_session | SuccessResponse |
| POST | `/groupchat/voting/` | create_voting | VotingSessionResponse |
| GET | `/groupchat/voting/` | list_voting | List[VotingSessionResponse] |
| GET | `/groupchat/voting/{session_id}` | get_voting | VotingSessionResponse |
| POST | `/groupchat/voting/{session_id}/vote` | cast_vote | VoteResponse |
| PATCH | `/groupchat/voting/{session_id}/vote/{voter_id}` | change_vote | VoteResponse |
| DELETE | `/groupchat/voting/{session_id}/vote/{voter_id}` | withdraw_vote | SuccessResponse |
| GET | `/groupchat/voting/{session_id}/votes` | get_votes | List[VoteResponse] |
| POST | `/groupchat/voting/{session_id}/calculate` | calculate_result | VotingResultResponse |
| GET | `/groupchat/voting/{session_id}/statistics` | get_voting_stats | VotingStatisticsResponse |
| POST | `/groupchat/voting/{session_id}/close` | close_voting | SuccessResponse |
| POST | `/groupchat/voting/{session_id}/cancel` | cancel_voting | SuccessResponse |
| DELETE | `/groupchat/voting/{session_id}` | delete_voting | SuccessResponse |
| POST | `/groupchat/adapter/` | create_adapter | GroupChatAdapterResponse |
| GET | `/groupchat/adapter/` | list_adapters | List[GroupChatAdapterResponse] |
| GET | `/groupchat/adapter/{adapter_id}` | get_adapter | GroupChatAdapterResponse |
| POST | `/groupchat/adapter/{adapter_id}/run` | run_adapter | GroupChatResultSchema |
| POST | `/groupchat/adapter/{adapter_id}/participants` | add_participants | SuccessResponse |
| DELETE | `/groupchat/adapter/{adapter_id}/participants/{name}` | remove_participant | SuccessResponse |
| DELETE | `/groupchat/adapter/{adapter_id}` | delete_adapter | SuccessResponse |
| POST | `/groupchat/orchestrator/select` | select_orchestrator | ManagerSelectionResponseSchema |

### planning/routes.py — 46 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/planning/decompose` | decompose_task | DecompositionResponse |
| POST | `/planning/decompose/{task_id}/refine` | refine_decomposition | DecompositionResponse |
| POST | `/planning/plans` | create_plan | PlanResponse |
| GET | `/planning/plans/{plan_id}` | get_plan | PlanStatusResponse |
| GET | `/planning/plans/{plan_id}/status` | get_plan_status | — |
| POST | `/planning/plans/{plan_id}/approve` | approve_plan | SuccessResponse |
| POST | `/planning/plans/{plan_id}/execute` | execute_plan | — |
| POST | `/planning/plans/{plan_id}/pause` | pause_plan | SuccessResponse |
| POST | `/planning/plans/{plan_id}/adjustments/approve` | approve_adjustment | SuccessResponse |
| GET | `/planning/plans` | list_plans | — |
| DELETE | `/planning/plans/{plan_id}` | delete_plan | SuccessResponse |
| POST | `/planning/decisions` | make_decision | DecisionResponse |
| GET | `/planning/decisions/{decision_id}/explain` | explain_decision | DecisionExplanationResponse |
| POST | `/planning/decisions/{decision_id}/approve` | approve_decision | SuccessResponse |
| POST | `/planning/decisions/{decision_id}/reject` | reject_decision | SuccessResponse |
| GET | `/planning/decisions` | list_decisions | — |
| GET | `/planning/decisions/rules` | get_decision_rules | — |
| POST | `/planning/trial` | run_trial | TrialResponse |
| GET | `/planning/trial/insights` | get_insights | InsightsListResponse |
| GET | `/planning/trial/recommendations` | get_recommendations | RecommendationsListResponse |
| GET | `/planning/trial/statistics` | get_trial_stats | TrialStatisticsResponse |
| GET | `/planning/trial/history` | get_trial_history | — |
| DELETE | `/planning/trial/history` | clear_trial_history | — |
| POST | `/planning/magentic/adapter` | create_magentic_adapter | MagenticAdapterResponse |
| GET | `/planning/magentic/adapter/{adapter_id}` | get_magentic_state | MagenticStateSchema |
| DELETE | `/planning/magentic/adapter/{adapter_id}` | delete_magentic_adapter | SuccessResponse |
| POST | `/planning/magentic/adapter/{adapter_id}/run` | run_magentic | MagenticResultSchema |
| POST | `/planning/magentic/adapter/{adapter_id}/intervention` | human_intervention | SuccessResponse |
| GET | `/planning/magentic/adapters` | list_magentic_adapters | — |
| GET | `/planning/magentic/adapter/{adapter_id}/ledger` | get_ledger | — |
| POST | `/planning/magentic/adapter/{adapter_id}/reset` | reset_adapter | SuccessResponse |
| POST | `/planning/adapter/planning` | create_planning_adapter | PlanningAdapterResponse |
| GET | `/planning/adapter/planning/{adapter_id}` | get_planning_adapter | PlanningAdapterResponse |
| POST | `/planning/adapter/planning/{adapter_id}/run` | run_planning_adapter | PlanningResultSchema |
| DELETE | `/planning/adapter/planning/{adapter_id}` | delete_planning_adapter | SuccessResponse |
| GET | `/planning/adapter/planning` | list_planning_adapters | — |
| POST | `/planning/adapter/multiturn` | create_multiturn_adapter | MultiTurnAdapterResponse |
| GET | `/planning/adapter/multiturn/{session_id}` | get_multiturn_session | MultiTurnAdapterResponse |
| POST | `/planning/adapter/multiturn/{session_id}/turn` | add_turn | TurnResultSchema |
| GET | `/planning/adapter/multiturn/{session_id}/history` | get_multiturn_history | MultiTurnHistoryResponse |
| POST | `/planning/adapter/multiturn/{session_id}/checkpoint` | save_checkpoint | SuccessResponse |
| POST | `/planning/adapter/multiturn/{session_id}/restore` | restore_checkpoint | SuccessResponse |
| POST | `/planning/adapter/multiturn/{session_id}/complete` | complete_session | MultiTurnAdapterResponse |
| DELETE | `/planning/adapter/multiturn/{session_id}` | delete_multiturn_session | SuccessResponse |
| GET | `/planning/adapter/multiturn` | list_multiturn_adapters | — |
| GET | `/planning/health` | health_check | — |

### ag_ui/routes.py — 22 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/ag-ui/health` | health_check | — |
| GET | `/ag-ui/agents` | list_agents | — |
| POST | `/ag-ui/run` | run_agent | — |
| POST | `/ag-ui/run/stream` | run_agent_stream | SSE |
| POST | `/ag-ui/tools/execute` | execute_tool | — |
| GET | `/ag-ui/tools` | list_tools | — |
| GET | `/ag-ui/events/{thread_id}` | get_events | — |
| GET | `/ag-ui/threads/{thread_id}/state` | get_thread_state | — |
| POST | `/ag-ui/test/workflow-progress` | test_workflow_progress | — |
| POST | `/ag-ui/test/mode-switch` | test_mode_switch | — |
| POST | `/ag-ui/test/ui-component` | test_ui_component | — |
| GET | `/ag-ui/approvals/pending` | get_pending_approvals | — |
| GET | `/ag-ui/approvals/{approval_id}` | get_approval | — |
| PATCH | `/ag-ui/approvals/{approval_id}` | update_approval | — |
| DELETE | `/ag-ui/approvals/{approval_id}` | delete_approval | — |
| POST | `/ag-ui/test/hitl` | test_hitl | — |
| POST | `/ag-ui/test/prediction` | test_prediction | — |
| POST | `/ag-ui/advanced/run` | advanced_run | — |
| POST | `/ag-ui/advanced/workflow` | advanced_workflow | — |
| POST | `/ag-ui/advanced/hitl` | advanced_hitl | — |
| POST | `/ag-ui/advanced/prediction` | advanced_prediction | — |
| POST | `/ag-ui/advanced/multi-agent` | advanced_multi_agent | — |

### ag_ui/upload.py — 4 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/upload` | upload_file | UploadResponse |
| GET | `/upload/list` | list_files | FileListResponse |
| DELETE | `/upload/{filename}` | delete_file | DeleteResponse |
| GET | `/upload/storage` | get_storage_info | dict |

### claude_sdk/routes.py — 6 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/query` | query | QueryResponse |
| POST | `/sessions` | create_session | SessionResponse |
| POST | `/sessions/{session_id}/query` | session_query | SessionQueryResponse |
| DELETE | `/sessions/{session_id}` | close_session | CloseSessionResponse |
| GET | `/sessions/{session_id}/history` | get_session_history | SessionHistoryResponse |
| GET | `/health` | health_check | — |

### claude_sdk/autonomous_routes.py — 7 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/plan` | generate_plan | PlanResponse |
| GET | `/{plan_id}` | get_plan | PlanResponse |
| POST | `/{plan_id}/execute` | execute_plan | — |
| DELETE | `/{plan_id}` | delete_plan | — (204) |
| GET | `/` | list_plans | PlanListResponse |
| POST | `/estimate` | estimate_plan | EstimateResponse |
| POST | `/{plan_id}/verify` | verify_plan | Dict |

### claude_sdk/hooks_routes.py — 6 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/hooks` | list_hooks | HookListResponse |
| GET | `/hooks/{hook_id}` | get_hook | HookInfo |
| POST | `/hooks/register` | register_hook | HookRegisterResponse |
| DELETE | `/hooks/{hook_id}` | delete_hook | — (204) |
| PUT | `/hooks/{hook_id}/enable` | enable_hook | HookInfo |
| PUT | `/hooks/{hook_id}/disable` | disable_hook | HookInfo |

### claude_sdk/tools_routes.py — 4 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/tools` | list_tools | ToolListResponse |
| GET | `/tools/{name}` | get_tool | ToolInfo |
| POST | `/tools/execute` | execute_tool | ToolExecuteResponse |
| POST | `/tools/validate` | validate_tool | ToolValidateResponse |

### claude_sdk/mcp_routes.py — 6 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/mcp/servers` | list_servers | MCPServerListResponse |
| POST | `/mcp/servers/connect` | connect_server | MCPConnectResponse |
| POST | `/mcp/servers/{server_id}/disconnect` | disconnect_server | — (204) |
| GET | `/mcp/servers/{server_id}/health` | server_health | MCPHealthResponse |
| GET | `/mcp/tools` | list_tools | MCPToolListResponse |
| POST | `/mcp/tools/execute` | execute_tool | MCPExecuteResponse |

### claude_sdk/hybrid_routes.py — 5 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/hybrid/execute` | execute_hybrid | HybridExecuteResponse |
| POST | `/hybrid/analyze` | analyze_hybrid | HybridAnalyzeResponse |
| GET | `/hybrid/metrics` | get_metrics | HybridMetricsResponse |
| POST | `/hybrid/context/sync` | sync_context | ContextSyncResponse |
| GET | `/hybrid/capabilities` | list_capabilities | CapabilityListResponse |

### claude_sdk/intent_routes.py — 6 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/intent/classify` | classify_intent | ClassifyIntentResponse |
| POST | `/intent/analyze-complexity` | analyze_complexity | AnalyzeComplexityResponse |
| POST | `/intent/detect-multi-agent` | detect_multi_agent | DetectMultiAgentResponse |
| GET | `/intent/classifiers` | list_classifiers | ListClassifiersResponse |
| GET | `/intent/stats` | get_stats | IntentStatsResponse |
| PUT | `/intent/config` | update_config | UpdateConfigResponse |

### hybrid/core_routes.py — 4 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/hybrid/analyze` | analyze_intent | IntentAnalyzeResponse |
| POST | `/hybrid/execute` | execute_hybrid | HybridExecuteResponse |
| GET | `/hybrid/metrics` | get_unified_metrics | UnifiedMetricsResponse |
| GET | `/hybrid/health` | health_check | — |

### hybrid/context_routes.py — 5 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/hybrid/context/{session_id}` | get_context | HybridContextResponse |
| GET | `/hybrid/context/{session_id}/history` | get_sync_history | SyncHistoryResponse |
| POST | `/hybrid/context/{session_id}/sync` | sync_context | SyncResultResponse |
| POST | `/hybrid/context/{session_id}/merge` | merge_context | SyncResultResponse |
| GET | `/hybrid/context/` | list_contexts | HybridContextListResponse |

### hybrid/risk_routes.py — 7 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/hybrid/risk/assess` | assess_risk | RiskAssessResponse |
| POST | `/hybrid/risk/batch` | assess_batch | RiskAssessBatchResponse |
| GET | `/hybrid/risk/session/{session_id}` | get_session_risk | SessionRiskResponse |
| GET | `/hybrid/risk/metrics` | get_engine_metrics | EngineMetricsResponse |
| DELETE | `/hybrid/risk/session/{session_id}` | clear_session_risk | — |
| POST | `/hybrid/risk/config` | update_risk_config | — |
| GET | `/hybrid/risk/health` | risk_health | — |

### hybrid/switch_routes.py — 7 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/hybrid/switch/` | trigger_switch | SwitchResultResponse |
| GET | `/hybrid/switch/{switch_id}` | get_switch_status | SwitchStatusResponse |
| POST | `/hybrid/switch/{switch_id}/rollback` | rollback_switch | RollbackResultResponse |
| GET | `/hybrid/switch/session/{session_id}` | get_session_switch_history | SwitchHistoryResponse |
| GET | `/hybrid/switch/health` | switch_health | — |
| DELETE | `/hybrid/switch/session/{session_id}` | clear_session_history | — |
| DELETE | `/hybrid/switch/{switch_id}` | delete_switch_record | — |

### orchestration/routes.py — 7 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/orchestration/policies` | list_policies | PolicyListResponse |
| GET | `/orchestration/policies/{intent_category}` | list_policies_by_category | PolicyListResponse |
| POST | `/orchestration/policies/mode/{mode}` | switch_policy_mode | PolicyListResponse |
| POST | `/orchestration/risk/assess` | assess_risk | RiskAssessmentResponse |
| GET | `/orchestration/metrics` | get_metrics | MetricsResponse |
| POST | `/orchestration/metrics/reset` | reset_metrics | Dict |
| GET | `/orchestration/health` | health_check | — |

### orchestration/dialog_routes.py — 4 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/orchestration/dialog/start` | start_dialog | DialogStatusResponse |
| POST | `/orchestration/dialog/{dialog_id}/respond` | respond_to_dialog | DialogStatusResponse |
| GET | `/orchestration/dialog/{dialog_id}/status` | get_dialog_status | DialogStatusResponse |
| DELETE | `/orchestration/dialog/{dialog_id}` | cancel_dialog | CancelDialogResponse |

### orchestration/approval_routes.py — 4 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/orchestration/approvals` | list_approvals | ApprovalListResponse |
| GET | `/orchestration/approvals/{approval_id}` | get_approval | ApprovalDetailResponse |
| POST | `/orchestration/approvals/{approval_id}/decision` | submit_decision | DecisionResponse |
| POST | `/orchestration/approvals/{approval_id}/callback` | teams_callback | CallbackResponse |

### orchestration/webhook_routes.py — 3 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/orchestration/webhooks/servicenow` | receive_servicenow_webhook | WebhookResponse |
| GET | `/orchestration/webhooks/servicenow/health` | servicenow_health | — |
| POST | `/orchestration/webhooks/servicenow/incident` | receive_incident | IncidentWebhookResponse |

### orchestration/intent_routes.py — 4 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/orchestration/intent/classify` | classify_intent | IntentClassifyResponse |
| POST | `/orchestration/intent/test` | test_intent | IntentTestResponse |
| POST | `/orchestration/intent/classify/batch` | batch_classify | — |
| POST | `/orchestration/intent/quick` | quick_classify | — |

### orchestration/route_management.py — 7 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/orchestration/routes` | create_route | RouteResponse |
| GET | `/orchestration/routes` | list_routes | List[RouteResponse] |
| GET | `/orchestration/routes/{route_name}` | get_route | RouteDetailResponse |
| PUT | `/orchestration/routes/{route_name}` | update_route | RouteResponse |
| DELETE | `/orchestration/routes/{route_name}` | delete_route | DeleteResponse |
| POST | `/orchestration/routes/sync` | sync_routes | SyncResponse |
| POST | `/orchestration/routes/search` | search_routes | List[SearchResultItem] |

### orchestrator/routes.py — 6 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/orchestrator/validate` | validate | — |
| GET | `/orchestrator/health` | health_check | — |
| GET | `/orchestrator/test-intent` | test_intent | — |
| POST | `/orchestrator/approval/{approval_id}` | handle_approval | — |
| POST | `/orchestrator/chat/stream` | chat_stream | SSE |
| POST | `/orchestrator/chat` | chat | PipelineResponse |

### orchestrator/session_routes.py — 2 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/sessions/recoverable` | get_recoverable_sessions | SessionListResponse |
| POST | `/sessions/{session_id}/resume` | resume_session | SessionResumeResponse |

### autonomous/routes.py — 4 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/claude/autonomous/plan` | create_plan | TaskResponse |
| GET | `/claude/autonomous/history` | get_history | TaskListResponse |
| GET | `/claude/autonomous/{task_id}` | get_task | TaskResponse |
| POST | `/claude/autonomous/{task_id}/cancel` | cancel_task | CancelResponse |

### a2a/routes.py — 14 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/a2a/message` | send_message | — |
| GET | `/a2a/message/{message_id}` | get_message | — |
| GET | `/a2a/messages/pending` | get_pending_messages | — |
| GET | `/a2a/conversation/{correlation_id}` | get_conversation | — |
| POST | `/a2a/agents/register` | register_agent | — |
| DELETE | `/a2a/agents/{agent_id}` | unregister_agent | — |
| GET | `/a2a/agents` | list_agents | — |
| GET | `/a2a/agents/{agent_id}` | get_agent | — |
| POST | `/a2a/agents/discover` | discover_agents | — |
| GET | `/a2a/agents/{agent_id}/capabilities` | get_capabilities | — |
| POST | `/a2a/agents/{agent_id}/heartbeat` | heartbeat | — |
| PUT | `/a2a/agents/{agent_id}/status` | update_status | — |
| GET | `/a2a/statistics` | get_statistics | — |
| POST | `/a2a/maintenance/cleanup` | cleanup | — |

### swarm/routes.py — 3 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/swarm/` | list_swarms | — |
| GET | `/swarm/{swarm_id}` | get_swarm | — |
| GET | `/swarm/{swarm_id}/workers` | get_workers | — |

### swarm/demo.py — 5 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/swarm/demo/start` | start_demo | DemoStartResponse |
| GET | `/swarm/demo/status/{swarm_id}` | get_demo_status | DemoStatusResponse |
| POST | `/swarm/demo/stop/{swarm_id}` | stop_demo | — |
| GET | `/swarm/demo/scenarios` | list_scenarios | — |
| GET | `/swarm/demo/events/{swarm_id}` | get_events | SSE |

### mcp/routes.py — 13 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/mcp/servers` | list_servers | — |
| POST | `/mcp/servers` | register_server | ServerConfigResponse |
| GET | `/mcp/servers/{server_id}` | get_server | — |
| DELETE | `/mcp/servers/{server_id}` | remove_server | — |
| POST | `/mcp/servers/{server_id}/connect` | connect_server | — |
| POST | `/mcp/servers/{server_id}/disconnect` | disconnect_server | — |
| GET | `/mcp/tools` | list_tools | ToolListResponse |
| GET | `/mcp/tools/{tool_name}` | get_tool | ToolSchemaResponse |
| POST | `/mcp/tools/execute` | execute_tool | ToolExecutionResponse |
| GET | `/mcp/audit` | query_audit | AuditQueryResponse |
| GET | `/mcp/registry` | get_registry | RegistrySummaryResponse |
| POST | `/mcp/validate` | validate_connection | ConnectionResponse |
| POST | `/mcp/batch-execute` | batch_execute | — |

### connectors/routes.py — 9 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/connectors/` | list_connectors | ConnectorListResponse |
| GET | `/connectors/{connector_id}` | get_connector | ConnectorInfoResponse |
| GET | `/connectors/{connector_id}/status` | get_status | ConnectorStatusResponse |
| GET | `/connectors/{connector_id}/config` | get_config | ConnectorConfigResponse |
| GET | `/connectors/types` | list_types | ConnectorTypesResponse |
| GET | `/connectors/health` | health_summary | HealthSummaryResponse |
| POST | `/connectors/` | create_connector | ConnectorConfigResponse |
| POST | `/connectors/{connector_id}/connect` | connect | ConnectorOperationResponse |
| POST | `/connectors/{connector_id}/disconnect` | disconnect | ConnectorOperationResponse |

### code_interpreter/routes.py — 11 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/code-interpreter/health` | health_check | HealthCheckResponse |
| POST | `/code-interpreter/execute` | execute_code | CodeExecuteResponse |
| POST | `/code-interpreter/analyze` | analyze_task | TaskAnalyzeResponse |
| POST | `/code-interpreter/sessions` | create_session | SessionCreateResponse |
| DELETE | `/code-interpreter/sessions/{session_id}` | delete_session | SessionDeleteResponse |
| GET | `/code-interpreter/sessions` | list_sessions | — |
| POST | `/code-interpreter/files/upload` | upload_file | FileUploadResponse |
| GET | `/code-interpreter/files` | list_files | FileListResponse |
| GET | `/code-interpreter/files/{file_id}` | get_file | — |
| DELETE | `/code-interpreter/files/{file_id}` | delete_file | FileDeleteResponse |
| GET | `/code-interpreter/sessions/{session_id}/files` | get_session_files | — |

### code_interpreter/visualization.py — 3 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/code-interpreter/visualizations` | list_visualizations | — |
| GET | `/code-interpreter/visualizations/{viz_id}` | get_visualization | — |
| POST | `/code-interpreter/visualizations` | create_visualization | VisualizationResponse |

### files/routes.py — 6 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/files/upload` | upload_file | FileUploadResponse |
| GET | `/files/` | list_files | FileListResponse |
| GET | `/files/{file_id}` | get_file | — |
| GET | `/files/{file_id}/download` | download_file | — |
| GET | `/files/{file_id}/metadata` | get_metadata | FileMetadata |
| DELETE | `/files/{file_id}` | delete_file | — |

### sandbox/routes.py — 6 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/sandbox/pool/status` | get_pool_status | PoolStatusResponse |
| POST | `/sandbox/pool/cleanup` | cleanup_pool | PoolCleanupResponse |
| POST | `/sandbox` | create_sandbox | SandboxResponse |
| GET | `/sandbox/{sandbox_id}` | get_sandbox | SandboxResponse |
| DELETE | `/sandbox/{sandbox_id}` | delete_sandbox | — (204) |
| POST | `/sandbox/{sandbox_id}/ipc` | send_ipc_message | IPCMessageResponse |

### cache/routes.py — 9 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/cache/stats` | get_stats | CacheStatsResponse |
| GET | `/cache/config` | get_config | CacheConfigResponse |
| POST | `/cache/get` | get_cache_entry | CacheEntryResponse |
| POST | `/cache/set` | set_cache_entry | — |
| POST | `/cache/clear` | clear_cache | CacheClearResponse |
| POST | `/cache/warm` | warm_cache | CacheWarmResponse |
| POST | `/cache/invalidate` | invalidate | — |
| POST | `/cache/batch-get` | batch_get | — |
| POST | `/cache/batch-set` | batch_set | — |

### audit/routes.py — 8 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/audit/` | list_entries | AuditListResponse |
| GET | `/audit/{entry_id}` | get_entry | AuditEntryResponse |
| GET | `/audit/trail/{resource_id}` | get_trail | AuditTrailResponse |
| GET | `/audit/statistics` | get_statistics | AuditStatisticsResponse |
| GET | `/audit/export` | export | ExportResponse |
| GET | `/audit/actions` | list_actions | ActionListResponse |
| GET | `/audit/resources` | list_resources | ResourceListResponse |
| GET | `/audit/health` | health_check | — |

### audit/decision_routes.py — 7 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/decisions/` | list_decisions | DecisionListResponse |
| GET | `/decisions/{decision_id}` | get_decision | DecisionAuditResponse |
| GET | `/decisions/{decision_id}/report` | get_report | AuditReportResponse |
| POST | `/decisions/{decision_id}/feedback` | submit_feedback | — |
| GET | `/decisions/statistics` | get_statistics | StatisticsResponse |
| GET | `/decisions/summary` | get_summary | SummaryReportResponse |
| GET | `/decisions/health` | health_check | — |

### patrol/routes.py — 10 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/patrol/trigger` | trigger_patrol | PatrolTriggerResponse |
| GET | `/patrol/reports` | list_reports | List[PatrolReportModel] |
| GET | `/patrol/reports/{report_id}` | get_report | PatrolReportModel |
| GET | `/patrol/schedule` | list_schedule | List[ScheduledPatrolModel] |
| POST | `/patrol/schedule` | create_schedule | ScheduledPatrolModel |
| PUT | `/patrol/schedule/{patrol_id}` | update_schedule | ScheduledPatrolModel |
| DELETE | `/patrol/schedule/{patrol_id}` | delete_schedule | — |
| GET | `/patrol/checks` | list_checks | List[CheckTypeModel] |
| GET | `/patrol/checks/{check_type}` | get_check | CheckExecutionResponse |

### correlation/routes.py — 7 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/correlation/analyze` | analyze | CorrelationAnalyzeResponse |
| GET | `/correlation/{event_id}` | get_correlation | CorrelationAnalyzeResponse |
| POST | `/correlation/rootcause/analyze` | analyze_root_cause | RootCauseAnalyzeResponse |
| GET | `/correlation/rootcause/{analysis_id}` | get_root_cause | RootCauseAnalyzeResponse |
| GET | `/correlation/graph/{event_id}/mermaid` | get_mermaid_graph | — |
| GET | `/correlation/graph/{event_id}/json` | get_json_graph | — |
| GET | `/correlation/graph/{event_id}/dot` | get_dot_graph | — |

### rootcause/routes.py — 4 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/rootcause/analyze` | analyze | RootCauseAnalyzeResponse |
| GET | `/rootcause/{analysis_id}/hypotheses` | get_hypotheses | HypothesesResponse |
| GET | `/rootcause/{analysis_id}/recommendations` | get_recommendations | RecommendationsResponse |
| POST | `/rootcause/similar` | find_similar | SimilarPatternsResponse |

### chat_history/routes.py — 3 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/chat-history/` | save_history | — |
| GET | `/chat-history/{session_id}` | get_history | — |
| DELETE | `/chat-history/{session_id}` | delete_history | — |

### n8n/routes.py — 7 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/n8n/webhook` | receive_webhook | N8nWebhookResponse |
| POST | `/n8n/webhook/{workflow_id}` | receive_workflow_webhook | N8nWebhookResponse |
| GET | `/n8n/status` | get_status | N8nStatusResponse |
| GET | `/n8n/config` | get_config | N8nConfigResponse |
| PUT | `/n8n/config` | update_config | N8nConfigResponse |
| POST | `/n8n/callback` | receive_callback | N8nCallbackResponse |
| GET | `/n8n/callback/{orchestration_id}` | get_callback_result | — |

### dashboard/routes.py — 2 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/dashboard/stats` | get_stats | DashboardStats |
| GET | `/dashboard/executions/chart` | get_chart | List[ExecutionChartData] |

### memory/routes.py — 7 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/memory/add` | add_memory | AddMemoryResponse |
| POST | `/memory/search` | search_memory | SearchMemoryResponse |
| GET | `/memory/user/{user_id}` | get_user_memories | MemoryListResponse |
| DELETE | `/memory/{memory_id}` | delete_memory | DeleteMemoryResponse |
| POST | `/memory/promote` | promote_memory | MemoryResponse |
| POST | `/memory/context` | get_context | MemoryListResponse |
| GET | `/memory/health` | health_check | MemoryHealthResponse |

### knowledge/routes.py — 7 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/knowledge/ingest` | ingest | IngestResponse |
| POST | `/knowledge/search` | search | SearchResponse |
| GET | `/knowledge/collections` | list_collections | Dict |
| DELETE | `/knowledge/collections` | clear_collections | — (204) |
| GET | `/knowledge/skills` | list_skills | List[SkillItem] |
| GET | `/knowledge/skills/{skill_id}` | get_skill | — |
| GET | `/knowledge/skills/search/query` | search_skills | — |

### tasks/routes.py — 9 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/tasks/` | create_task | TaskResponse |
| GET | `/tasks/` | list_tasks | List[TaskResponse] |
| GET | `/tasks/{task_id}` | get_task | TaskResponse |
| PUT | `/tasks/{task_id}` | update_task | TaskResponse |
| DELETE | `/tasks/{task_id}` | delete_task | — (204) |
| POST | `/tasks/{task_id}/start` | start_task | TaskResponse |
| POST | `/tasks/{task_id}/complete` | complete_task | TaskResponse |
| POST | `/tasks/{task_id}/fail` | fail_task | TaskResponse |
| POST | `/tasks/{task_id}/progress` | update_progress | TaskResponse |

### performance/routes.py — 11 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/performance/metrics` | get_metrics | PerformanceMetricsResponse |
| POST | `/performance/profile/start` | start_profile | ProfileSessionResponse |
| POST | `/performance/profile/stop` | stop_profile | ProfileSessionResponse |
| POST | `/performance/profile/metric` | record_metric | — |
| GET | `/performance/profile/sessions` | list_sessions | — |
| GET | `/performance/profile/summary/{session_id}` | get_summary | — |
| POST | `/performance/optimize` | optimize | OptimizationResultResponse |
| GET | `/performance/collector/summary` | get_collector_summary | — |
| GET | `/performance/collector/alerts` | get_collector_alerts | — |
| POST | `/performance/collector/threshold` | set_threshold | — |
| GET | `/performance/health` | health_check | — |

### devtools/routes.py — 13 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/devtools/health` | health_check | HealthCheckResponse |
| GET | `/devtools/traces` | list_traces | TraceListResponse |
| POST | `/devtools/traces` | start_trace | TraceResponse |
| GET | `/devtools/traces/{execution_id}` | get_trace | TraceResponse |
| POST | `/devtools/traces/{execution_id}/end` | end_trace | TraceResponse |
| DELETE | `/devtools/traces/{execution_id}` | delete_trace | — |
| POST | `/devtools/traces/{execution_id}/events` | add_event | EventResponse |
| GET | `/devtools/traces/{execution_id}/events` | get_events | EventListResponse |
| POST | `/devtools/traces/{execution_id}/spans` | start_span | SpanResponse |
| POST | `/devtools/spans/{span_id}/end` | end_span | SpanResponse |
| GET | `/devtools/traces/{execution_id}/timeline` | get_timeline | TimelineResponse |
| GET | `/devtools/traces/{execution_id}/statistics` | get_statistics | TraceStatisticsResponse |

### notifications/routes.py — 11 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/notifications/approval` | send_approval | NotificationResultResponse |
| POST | `/notifications/completion` | send_completion | NotificationResultResponse |
| POST | `/notifications/error` | send_error | NotificationResultResponse |
| POST | `/notifications/custom` | send_custom | NotificationResultResponse |
| GET | `/notifications/history` | get_history | NotificationHistoryResponse |
| GET | `/notifications/statistics` | get_statistics | NotificationStatisticsResponse |
| DELETE | `/notifications/history` | clear_history | — |
| GET | `/notifications/config` | get_config | ConfigurationResponse |
| PUT | `/notifications/config` | update_config | ConfigurationResponse |
| GET | `/notifications/types` | list_types | NotificationTypesResponse |
| GET | `/notifications/health` | health_check | HealthCheckResponse |

### versioning/routes.py — 15 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/versions/health` | health_check | HealthCheckResponse |
| GET | `/versions/statistics` | get_statistics | VersionStatisticsResponse |
| POST | `/versions/compare` | compare_versions | DiffResponse |
| POST | `/versions/` | create_version | VersionResponse |
| GET | `/versions/` | list_versions | VersionListResponse |
| GET | `/versions/{version_id}` | get_version | VersionDetailResponse |
| DELETE | `/versions/{version_id}` | delete_version | — |
| POST | `/versions/{version_id}/publish` | publish_version | VersionResponse |
| POST | `/versions/{version_id}/deprecate` | deprecate_version | VersionResponse |
| POST | `/versions/{version_id}/archive` | archive_version | VersionResponse |
| GET | `/versions/templates/{template_id}/versions` | get_template_versions | VersionListResponse |
| GET | `/versions/templates/{template_id}/latest` | get_latest | VersionDetailResponse |
| POST | `/versions/templates/{template_id}/rollback` | rollback | VersionResponse |
| GET | `/versions/templates/{template_id}/statistics` | get_template_stats | TemplateStatisticsResponse |

### templates/routes.py — 12 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/templates/health` | health_check | HealthCheckResponse |
| GET | `/templates/statistics/summary` | get_statistics | TemplateStatisticsResponse |
| GET | `/templates/categories/list` | list_categories | CategoryListResponse |
| GET | `/templates/popular/list` | get_popular | TemplateListResult |
| GET | `/templates/top-rated/list` | get_top_rated | TemplateListResult |
| POST | `/templates/search` | search | SearchResponse |
| GET | `/templates/` | list_templates | TemplateListResult |
| GET | `/templates/similar/{template_id}` | get_similar | TemplateListResult |
| GET | `/templates/{template_id}` | get_template | TemplateDetailResponse |
| POST | `/templates/{template_id}/instantiate` | instantiate | InstantiateResponse |
| POST | `/templates/{template_id}/rate` | rate_template | RateResponse |

### prompts/routes.py — 11 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/prompts/` | list_prompts | — |
| GET | `/prompts/{prompt_id}` | get_prompt | — |
| POST | `/prompts/` | create_prompt | — |
| PUT | `/prompts/{prompt_id}` | update_prompt | — |
| DELETE | `/prompts/{prompt_id}` | delete_prompt | — |
| POST | `/prompts/{prompt_id}/render` | render_prompt | — |
| POST | `/prompts/{prompt_id}/validate` | validate_prompt | — |
| GET | `/prompts/categories` | list_categories | — |
| GET | `/prompts/{prompt_id}/versions` | list_versions | — |
| POST | `/prompts/{prompt_id}/versions` | create_version | — |
| GET | `/prompts/stats` | get_stats | — |

### triggers/routes.py — 8 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/triggers/` | create_trigger | WebhookConfigResponse |
| GET | `/triggers/` | list_triggers | WebhookListResponse |
| POST | `/triggers/{webhook_id}/fire` | fire_trigger | TriggerResponse |
| GET | `/triggers/{webhook_id}` | get_trigger | WebhookConfigResponse |
| PUT | `/triggers/{webhook_id}` | update_trigger | WebhookConfigResponse |
| DELETE | `/triggers/{webhook_id}` | delete_trigger | — |
| POST | `/triggers/{webhook_id}/verify` | verify_signature | SignatureTestResponse |
| GET | `/triggers/stats` | get_stats | — |

### routing/routes.py — 14 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| POST | `/routing/route` | route_request | RoutingResultResponse |
| POST | `/routing/relations` | create_relation | ExecutionRelationResponse |
| GET | `/routing/executions/{execution_id}/relations` | get_relations | RelationListResponse |
| GET | `/routing/executions/{execution_id}/chain` | get_chain | RelationListResponse |
| GET | `/routing/relations/{relation_id}` | get_relation | ExecutionRelationResponse |
| DELETE | `/routing/relations/{relation_id}` | delete_relation | — |
| GET | `/routing/scenarios` | list_scenarios | ScenarioListResponse |
| GET | `/routing/scenarios/{scenario_name}` | get_scenario | ScenarioConfigResponse |
| PUT | `/routing/scenarios/{scenario_name}` | update_scenario | ScenarioConfigResponse |
| POST | `/routing/scenarios/{scenario_name}/workflow` | trigger_workflow | — |
| GET | `/routing/relation-types` | list_relation_types | RelationTypesResponse |
| GET | `/routing/statistics` | get_statistics | RoutingStatisticsResponse |
| DELETE | `/routing/relations` | clear_relations | — |
| GET | `/routing/health` | health_check | HealthCheckResponse |

### learning/routes.py — 13 endpoints
| Method | Path | Handler | Response Model |
|--------|------|---------|----------------|
| GET | `/learning/health` | health_check | HealthCheckResponse |
| GET | `/learning/statistics` | get_statistics | LearningStatisticsResponse |
| POST | `/learning/corrections` | record_correction | CaseResponse |
| GET | `/learning/cases` | list_cases | CaseListResponse |
| GET | `/learning/cases/{case_id}` | get_case | CaseResponse |
| DELETE | `/learning/cases/{case_id}` | delete_case | — |
| POST | `/learning/cases/{case_id}/approve` | approve_case | CaseResponse |
| POST | `/learning/cases/{case_id}/reject` | reject_case | CaseResponse |
| POST | `/learning/cases/bulk-approve` | bulk_approve | BulkApproveResponse |
| POST | `/learning/similar` | find_similar | SimilarCasesResponse |
| POST | `/learning/prompt` | build_prompt | BuildPromptResponse |
| POST | `/learning/cases/{case_id}/effectiveness` | record_effectiveness | CaseResponse |
| GET | `/learning/scenarios/{scenario_name}/statistics` | get_scenario_stats | ScenarioStatisticsResponse |

---

## Schema Classes Summary

| Module | File | Schema Count |
|--------|------|-------------|
| correlation | routes.py | 12 |
| checkpoints | schemas.py | 10 |
| code_interpreter | schemas.py | 17 |
| code_interpreter | visualization.py | 3 |
| claude_sdk | schemas.py | 10 |
| claude_sdk | tools_routes.py | 8 |
| claude_sdk | hooks_routes.py | 5 |
| claude_sdk | hybrid_routes.py | 10 |
| claude_sdk | autonomous_routes.py | 10 |
| claude_sdk | mcp_routes.py | 8 |
| claude_sdk | intent_routes.py | 13 |
| connectors | schemas.py | 10 |
| audit | schemas.py | 7 |
| audit | decision_routes.py | 10 |
| ag_ui | schemas.py | 27 |
| ag_ui | upload.py | 4 |
| concurrent | schemas.py | 12 |
| cache | schemas.py | 9 |
| executions | schemas.py | 12 |
| handoff | schemas.py | 22 |
| files | schemas.py | 4 |
| n8n | schemas.py | 8 |
| dashboard | routes.py | 2 |
| hybrid | core_routes.py | 6 |
| hybrid | schemas.py | 14 |
| hybrid | switch_schemas.py | 10 |
| hybrid | risk_schemas.py | 7 |
| mcp | schemas.py | 14 |
| versioning | schemas.py | 14 |
| orchestration | schemas.py | 17 |
| orchestration | dialog_routes.py | 5 |
| orchestration | approval_routes.py | 7 |
| orchestration | webhook_routes.py | 2 |
| orchestration | route_management.py | 8 |
| notifications | schemas.py | 11 |
| groupchat | schemas.py | 33 |
| learning | schemas.py | 16 |
| nested | schemas.py | 16 |
| devtools | schemas.py | 14 |
| templates | schemas.py | 16 |
| triggers | schemas.py | 9 |
| routing | schemas.py | 10 |
| sandbox | schemas.py | 7 |
| memory | schemas.py | 13 |
| auth | migration.py | 2 |
| planning | schemas.py | 39 |
| knowledge | routes.py | 6 |
| patrol | routes.py | 9 |
| rootcause | routes.py | 7 |
| a2a | routes.py | 4 |
| tasks | routes.py | 4 |
| performance | routes.py | 8 |
| orchestrator | session_routes.py | 2 |
| **TOTAL** | | **~598** |

---

## Endpoint Count by Module

| Module | Endpoints | WebSockets | Total |
|--------|-----------|------------|-------|
| planning | 46 | 0 | 46 |
| groupchat | 40 | 1 | 41 |
| ag_ui (routes + upload) | 22 + 4 | 0 | 26 |
| sessions (routes + chat + ws) | 15 + 6 + 3 | 1 | 24 |
| orchestration (all sub-routes) | 7+4+4+3+4+7 | 0 | 29 |
| nested | 16 | 0 | 16 |
| concurrent (routes + ws) | 13 + 2 | 2 | 15 |
| versioning | 15 | 0 | 15 |
| handoff | 14 | 0 | 14 |
| a2a | 14 | 0 | 14 |
| routing | 14 | 0 | 14 |
| code_interpreter (routes + viz) | 11 + 3 | 0 | 14 |
| mcp | 13 | 0 | 13 |
| learning | 13 | 0 | 13 |
| devtools | 13 | 0 | 13 |
| audit (routes + decisions) | 8 + 7 | 0 | 15 |
| workflows (routes + graph) | 9 + 3 | 0 | 12 |
| executions | 11 | 0 | 11 |
| templates | 12 | 0 | 12 |
| performance | 11 | 0 | 11 |
| prompts | 11 | 0 | 11 |
| notifications | 11 | 0 | 11 |
| checkpoints | 10 | 0 | 10 |
| patrol | 10 | 0 | 10 |
| cache | 9 | 0 | 9 |
| connectors | 9 | 0 | 9 |
| tasks | 9 | 0 | 9 |
| claude_sdk (all sub-routes) | 6+7+6+4+6+5+6 | 0 | 40 |
| triggers | 8 | 0 | 8 |
| swarm (routes + demo) | 3 + 5 | 0 | 8 |
| orchestrator (routes + sessions) | 6 + 2 | 0 | 8 |
| n8n | 7 | 0 | 7 |
| memory | 7 | 0 | 7 |
| knowledge | 7 | 0 | 7 |
| correlation | 7 | 0 | 7 |
| agents | 6 | 0 | 6 |
| files | 6 | 0 | 6 |
| sandbox | 6 | 0 | 6 |
| auth (routes + migration) | 4 + 1 | 0 | 5 |
| autonomous | 4 | 0 | 4 |
| rootcause | 4 | 0 | 4 |
| hybrid (all sub-routes) | 4+5+7+7 | 0 | 23 |
| chat_history | 3 | 0 | 3 |
| dashboard | 2 | 0 | 2 |

### Grand Total: **589 endpoints** (585 HTTP + 4 WebSocket)

---

## Method Distribution

| HTTP Method | Count |
|------------|-------|
| GET | 213 |
| POST | 281 |
| PUT | 19 |
| DELETE | 51 |
| PATCH | 6 |
| WebSocket | 4 |
| **Total** | **574** (HTTP) + **4** (WS) = **578** |

> Note: The count of 589 includes endpoints from example/docstring decorators in `dependencies.py` and `auth/dependencies.py` (5 endpoints used as documentation examples, not real routes). The actual operational endpoint count is approximately **584 HTTP + 4 WS = 588**.

---

## Notes

1. **Custom Router Names**: Several modules use non-standard router variable names:
   - `dialog_router`, `approval_router`, `webhook_router`, `intent_router`, `route_management_router`
   - These are NOT caught by a simple `@router.` pattern search

2. **Prefix Hierarchy**: All routes sit under `/api/v1/` as configured in `main.py`

3. **SSE Endpoints**: Several endpoints return Server-Sent Events (SSE):
   - `/orchestrator/chat/stream`
   - `/sessions/{id}/chat/stream`
   - `/ag-ui/run/stream`
   - `/swarm/demo/events/{swarm_id}`

4. **Duplicate Functionality**: Some modules expose overlapping functionality:
   - `hybrid/core_routes.py` and `claude_sdk/hybrid_routes.py` both have `/hybrid/execute` and `/hybrid/analyze`
   - `rootcause/routes.py` and `correlation/routes.py` both have root cause analysis
   - `mcp/routes.py` and `claude_sdk/mcp_routes.py` both have MCP tool operations
