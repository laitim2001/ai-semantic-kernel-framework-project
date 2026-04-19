# Delta: Phase 45-47 Changes

> **Baseline**: V9 at commit `50ec420` (2026-03-31, Phase 44 complete, Sprint 152)
> **Target**: commit `69b5fa2` (2026-04-19, Phase 47 worktree 1 merged)
> **Scope**: 162 commits, 194 source files changed (+28,944 / -3,033 LOC)
> **Phases covered**: Phase 45 (Orchestration Core), Phase 46 (Agent Expert Registry), Phase 47 worktree 1 (Execution Log Persistence) + PoC Agent Team V4 merge
> **Method**: git log 50ec420..HEAD on main branch; parallel source-code evidence collection

---

## 1. Phase Summary

| Phase | Sprints | Merge Commit | Main Topic |
|-------|---------|--------------|------------|
| **PoC V3/V4 merge** | — | `c20c72d` | PoC Agent Team merge — Orchestrator + Subagent + Agent Team (pre-Phase 45) |
| **Phase 42 deep integration merge** | — | `63ae7ff` | V9 analysis + Claude Code source study + merge docs |
| **Phase 45** | 153-158 | `2a12d0b` | Orchestration Core — unified 8-step pipeline, dispatch layer, LLM route decision, OrchestratorChat |
| **Phase 46** | 159-166 | `80678dd` | Agent Expert Registry — YAML + DB-backed expert CRUD, domain-specific tool schemas, dynamic agent count |
| **Phase 47 W1** | — | `69b5fa2` | Orchestration Execution Log Persistence |

---

## 2. New Backend Directories

### 2.1 `backend/src/integrations/orchestration/pipeline/` (NEW, Phase 45)

**Purpose**: Unified 8-step orchestration pipeline (Sprint 153-156, `6e7bf1d..f946489`)

| File | Key Classes | Evidence |
|------|-------------|----------|
| `service.py` | `OrchestrationPipelineService`, `PipelineEvent`, `PipelineEventType` (27 values) | 569 LOC, `pipeline/service.py:92,132` |
| `context.py` | `PipelineContext` dataclass | `pipeline/context.py` |
| `exceptions.py` | `DialogPauseException`, `HITLPauseException`, `PipelineError` | `pipeline/exceptions.py` |
| `persistence.py` | `PipelineExecutionPersistenceService` | `pipeline/persistence.py` (Phase 47) |
| `steps/base.py` | `PipelineStep` ABC | `pipeline/steps/base.py:23` |
| `steps/step1_memory.py` | `MemoryStep(PipelineStep)` — name="memory_read" | index=0 |
| `steps/step2_knowledge.py` | `KnowledgeStep` — name="knowledge_search" | index=1 |
| `steps/step3_intent.py` | `IntentStep` — name="intent_analysis" (3-tier cascade) | index=2 |
| `steps/step4_risk.py` | `RiskStep` — name="risk_assessment" | index=3 |
| `steps/step5_hitl.py` | `HITLGateStep` — name="hitl_gate" | index=4 |
| `steps/step6_llm_route.py` | `LLMRouteStep` — name="llm_route_decision" (function calling) | index=5 |
| `steps/step8_postprocess.py` | `PostProcessStep` — name="postprocess" (checkpoint + memory) | index=7 |

> Step 7 = dispatch execution (handled by `DispatchService`, not a pipeline step).

**`PipelineEventType` enum values** (27 SSE events, `pipeline/service.py:27-61`):
`PIPELINE_START`, `STEP_START`, `STEP_COMPLETE`, `STEP_ERROR`, `DIALOG_REQUIRED`, `HITL_REQUIRED`,
`LLM_ROUTE_DECISION`, `ROUTING_COMPLETE`, `DISPATCH_START`, `AGENT_THINKING`, `AGENT_TOOL_CALL`,
`AGENT_COMPLETE`, `AGENT_TEAM_CREATED`, `AGENT_MEMBER_STARTED`, `AGENT_MEMBER_THINKING`,
`AGENT_MEMBER_TOOL_CALL`, `AGENT_MEMBER_COMPLETED`, `AGENT_TEAM_COMPLETED`, `AGENT_TEAM_MESSAGE`,
`AGENT_INBOX_RECEIVED`, `AGENT_TASK_CLAIMED`, `AGENT_TASK_REASSIGNED`, `AGENT_APPROVAL_REQUIRED`,
`EXPERT_ROSTER_PREVIEW`, `TEXT_DELTA`, `PIPELINE_COMPLETE`, `PIPELINE_ERROR`.

### 2.2 `backend/src/integrations/orchestration/dispatch/` (NEW, Phase 45)

**Purpose**: Route dispatch layer — 3 executors for direct_answer / subagent / team

| File | Key Classes |
|------|-------------|
| `models.py` | `ExecutionRoute` enum (`DIRECT_ANSWER`, `SUBAGENT`, `TEAM`), `DispatchRequest`, `DispatchResult`, `AgentResult` |
| `service.py` | `DispatchService` with `dispatch()`, `register_executor()` |
| `executors/base.py` | `BaseExecutor(ABC)` — template with timing/logging |
| `executors/direct_answer.py` | `DirectAnswerExecutor` |
| `executors/subagent.py` | `SubagentExecutor` — includes `_infer_complexity()` (Sprint 166) |
| `executors/team.py` | `TeamExecutor` — delegates to PoC `run_parallel_team()` |
| `executors/event_adapter.py` | `EventQueueAdapter` |
| `executors/pipeline_emitter_bridge.py` | `PipelineEmitterBridge` (maps PoC SWARM_* → pipeline SSE) |
| `executors/team_agent_adapter.py` | `TeamAgentAdapter` |
| `executors/team_tool_registry.py` | Team tool registry for per-agent tools |

> `ExecutionRoute.from_string()` defaults to `TEAM` on unknown input (`dispatch/models.py:13`).

### 2.3 `backend/src/integrations/orchestration/experts/` (NEW, Phase 46 Sprint 158-163)

**Purpose**: Agent Expert Registry — YAML + DB-backed expert definitions

| File | Key Classes / Content |
|------|----------------------|
| `registry.py` | `AgentExpertRegistry`, `AgentExpertDefinition`, `get_registry()` singleton, `reset_registry()` |
| `bridge.py` | `get_expert_role()`, `get_expert_role_names()`, `get_expert_descriptions()` (adapter for `worker_roles`) |
| `domain_tools.py` | `TEAM_TOOLS` (6 tools), `DOMAIN_TOOLS` dict (7 domains), `resolve_tools()` for `*`/`@domain` tokens |
| `tool_validator.py` | Tool schema validation |
| `seeder.py` | YAML → DB seeder |
| `exceptions.py` | `ExpertDefinitionError`, `ExpertNotFoundError`, `ExpertSchemaValidationError` |

**VALID_DOMAINS** (`registry.py:27`): `{network, database, application, security, cloud, general, custom}`

**YAML expert definitions** (`experts/definitions/`):
- `network_expert.yaml`, `database_expert.yaml`, `cloud_expert.yaml`, `application_expert.yaml`, `security_expert.yaml`, `general.yaml`

**YAML schema** (version 1.0):
```yaml
version: "1.0"
name: <slug>
display_name: "English"
display_name_zh: "中文"
description: ...
domain: <one of VALID_DOMAINS>
capabilities: [list of strings]
model: null | "claude-sonnet-4-6" | ...
max_iterations: 5        # range 1-20
system_prompt: |
  <multi-line>
tools: [explicit names] | ["*"] | ["@domain"]
enabled: true
metadata: { icon, color, priority }
```

### 2.4 `backend/src/integrations/orchestration/approval/`, `transcript/`, `resume/` (NEW, Phase 45)

| Directory | Purpose |
|-----------|---------|
| `approval/service.py` | `ApprovalService` — HITL approval service used by Step 5 |
| `transcript/service.py` | `TranscriptService` + `TranscriptEntry` — records step entries to Redis Streams |
| `resume/service.py` | `ResumeService` — checkpoint-based resume from paused step |

### 2.5 `backend/src/integrations/poc/` (NEW, 10 files, PoC V4 merge)

**Purpose**: CC-inspired persistent agent loop, SharedTaskList, HITL gate, tools

| File | LOC | Purpose |
|------|-----|---------|
| `agent_work_loop.py` | 1002 | `_agent_work_loop()` (3-phase A/B/C persistent loop), `run_parallel_team()` orchestrator |
| `shared_task_list.py` | 370 | `SharedTaskList` (in-memory), `SharedTaskListProtocol`, `TaskItem`, `TaskStatus`, `TeamMessage`, `create_shared_task_list()` factory |
| `redis_task_list.py` | 442 | `RedisSharedTaskList` (Redis Streams + Hash, 1h TTL) |
| `approval_gate.py` | ~150 | `TeamApprovalManager` (event-driven), `ToolRiskLevel`, `requires_approval()`, `PendingApproval` |
| `agent_work_loop` phases | — | A=active, B=idle, C=500ms mailbox poll; never exits unless shutdown/10-turn safety |
| `claude_sdk_tools.py` | — | Claude SDK tool simulations |
| `memory_integration.py` | — | Pre/post-execution memory retrieval + storage |
| `orchestrator_tools.py` | — | TeamLead decomposition tools |
| `real_tools.py` | — | Real diagnostic tools (subprocess) |
| `team_tools.py` | — | Inter-agent comm tools (`send_team_message`, `check_my_inbox`, etc.) |

**HIGH_RISK_TOOLS** (`approval_gate.py:~48`): `"run_diagnostic_command"`, `"query_database"`
**MEDIUM_RISK_TOOLS**: `"search_knowledge_base"`

### 2.6 `backend/src/integrations/agent_framework/clients/` (NEW, PoC V4)

| File | LOC | Purpose |
|------|-----|---------|
| `anthropic_chat_client.py` | 393 | `AnthropicChatClient(FunctionInvocationLayer, BaseChatClient)` — Claude API wrapper for MAF, supports extended thinking, non-streaming tool calls |
| `__init__.py` | — | Re-exports |

**Plus**: `backend/src/integrations/agent_framework/ipa_checkpoint_storage.py` (NEW) — IPA-specific checkpoint storage.

### 2.7 `backend/src/integrations/memory/` (3 new modules, Phase 45-46)

| File | Purpose |
|------|---------|
| `consolidation.py` | Memory consolidation logic (episodic → semantic) |
| `context_budget.py` | Token budget allocation for memory retrieval |
| `extraction.py` | Memory extraction from transcripts |

Plus **modified**: `mem0_client.py`, `types.py`, `unified_memory.py`.

---

## 3. New API Endpoints

### 3.1 `backend/src/api/v1/orchestration/chat_routes.py` (Phase 45 Sprint 156)

**Prefix**: `/orchestration/chat` | **Tags**: `"Orchestration Chat (Phase 45)"`

| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | `/orchestration/chat` | `ChatRequest` | SSE stream of `PipelineEventType` events |
| POST | `/orchestration/chat/resume` | `ResumeRequest` | SSE stream |
| POST | `/orchestration/chat/dialog-respond` | `DialogRespondRequest` | SSE stream |
| POST | `/orchestration/chat/team/approval` | `TeamApprovalDecisionRequest` | approval confirmation |
| GET | `/orchestration/chat/session/{session_id}` | — | `SessionStatusResponse` |

**Schemas** (`chat_schemas.py`): `ChatRequest`, `ResumeRequest`, `DialogRespondRequest`, `TeamApprovalDecisionRequest`, `PipelineStepStatus`, `SessionStatusResponse`.

### 3.2 `backend/src/api/v1/orchestration/execution_log_routes.py` (Phase 47 W1)

**Purpose**: Persistent orchestration execution log retrieval
**Schemas**: `execution_log_schemas.py`

### 3.3 `backend/src/api/v1/experts/` (Phase 46 Sprint 162-163)

**Prefix**: `/experts`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/experts/` | List experts (filters: `domain`, `enabled`) |
| GET | `/experts/{name}` | Get expert detail |
| POST | `/experts/` | Create new expert |
| PUT | `/experts/{name}` | Update expert (auto-bumps `version`) |
| DELETE | `/experts/{name}` | Delete (403 if `is_builtin=True`) |
| POST | `/experts/reload` | Re-seed YAML + reload in-memory registry |

**Schemas** (`schemas.py`): `ExpertResponse`, `ExpertDetailResponse`, `ExpertListResponse`, `ExpertCreateRequest`, `ExpertUpdateRequest`, `ReloadResponse`.

### 3.4 `backend/src/api/v1/poc/agent_team_poc.py` (PoC V4)

**Prefix**: `/poc/agent-team`

| Path | Purpose |
|------|---------|
| `test_team` | Team mode (GroupChat + SharedTaskList) |
| `test_team_stream` | Team mode with SSE streaming |
| `test_subagent` | Subagent mode (ConcurrentBuilder) |
| `test_hybrid` | Orchestrator decides mode |

---

## 4. New Database Tables / ORM Models

### 4.1 `agent_expert` (Phase 46 Sprint 163)

**File**: `backend/src/infrastructure/database/models/agent_expert.py` (168 LOC)
**Repository**: `backend/src/infrastructure/database/repositories/agent_expert.py` (109 LOC)

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK, default=uuid4 |
| `name` | String(255) | UNIQUE, INDEXED |
| `display_name` | String(255) | — |
| `display_name_zh` | String(255) | — |
| `description` | Text | nullable |
| `domain` | String(100) | INDEXED, CHECK (one of 7 domains) |
| `capabilities` | JSONB | default=[] |
| `model` | String(255) | nullable |
| `max_iterations` | Integer | default=5, range 1-20 |
| `system_prompt` | Text | — |
| `tools` | JSONB | default=[] |
| `enabled` | Boolean | INDEXED, default=True |
| `is_builtin` | Boolean | default=False (blocks deletion) |
| `metadata_` | JSONB | default={} |
| `version` | Integer | default=1 (auto-bump on update) |
| `created_at`, `updated_at` | timestamps | from `TimestampMixin` |

**Repository methods** (async, AsyncSession): `create`, `get_by_id`, `get_by_name`, `list_all(domain, enabled)`, `update(bumps version)`, `delete`, `upsert_from_yaml`, `count`.

### 4.2 `orchestration_execution_log` (Phase 47 W1)

**File**: `backend/src/infrastructure/database/models/orchestration_execution_log.py`
**Repository**: `backend/src/infrastructure/database/repositories/orchestration_execution_log.py`

**Purpose**: Persist full pipeline execution log (memory/knowledge text, step metadata, route decisions) for later retrieval and display.

---

## 5. New Frontend

### 5.1 New pages

| Page | Route | File |
|------|-------|------|
| **OrchestratorChat** | `/orchestrator-chat` | `frontend/src/pages/OrchestratorChat.tsx` (Phase 45 Sprint 157) |
| **AgentTeamTestPage** | `/agent-team-test` | `frontend/src/pages/AgentTeamTestPage.tsx` (PoC V4) |
| **Agent Experts pages** | `/agent-experts/*` | `frontend/src/pages/agent-experts/` — `AgentExpertsPage.tsx`, `AgentExpertDetailPage.tsx`, `CreateAgentExpertPage.tsx`, `EditAgentExpertPage.tsx` (Phase 46 Sprint 164) |

### 5.2 New hooks

| Hook | File |
|------|------|
| `useOrchestratorPipeline` | `frontend/src/hooks/useOrchestratorPipeline.ts` |
| `useOrchestratorSSE` | `frontend/src/hooks/useOrchestratorSSE.ts` |
| `useOrchestratorHistory` | `frontend/src/hooks/useOrchestratorHistory.ts` |
| `useExperts` | `frontend/src/hooks/useExperts.ts` — React Query: `useExpertsList`, `useExpertDetail`, `useCreateExpert`, `useUpdateExpert`, `useDeleteExpert`, `useReloadExperts` |

### 5.3 New Zustand stores

| Store | File | Replaces |
|-------|------|----------|
| `agentTeamStore` | `frontend/src/stores/agentTeamStore.ts` | **replaces** `swarmStore.ts` (deleted) |
| `expertSelectionStore` | `frontend/src/stores/expertSelectionStore.ts` | — |

### 5.4 Frontend directory rename: `agent-swarm/` → `agent-team/`

**Mass rename** at `frontend/src/components/unified-chat/`:
- 15 files renamed (rename similarity 51-100%)
- **New components** (not in agent-swarm): `AgentCardList.tsx`, `ExpertBadges.tsx`, `ConversationLog.tsx`, `AgentRosterPanel.tsx`
- **Deleted**: `WorkerCardList.tsx` (refactored into `AgentCardList`), all agent-swarm test files (replaced)
- **New hooks** in `agent-team/hooks/`: `useAgentTeamEventHandler.ts`, `useAgentTeamEvents.ts`, `useAgentTeamStatus.ts`, `useAgentDetail.ts`
- **New types**: `agent-team/types/events.ts` (wire-format snake_case payloads), `agent-team/types/index.ts` (UI camelCase types)

### 5.5 New unified-chat components (Phase 45)

| Component | File | Purpose |
|-----------|------|---------|
| `GuidedDialogPanel` | `frontend/src/components/unified-chat/GuidedDialogPanel.tsx` | Missing-field question form when pipeline pauses at Step 3 (intent) |
| `PipelineProgressPanel` | `frontend/src/components/unified-chat/PipelineProgressPanel.tsx` | 8-step visual progress tracker |
| `StepDetailPanel` | `frontend/src/components/unified-chat/StepDetailPanel.tsx` | Step-specific result display |

### 5.6 Types expansion — `frontend/src/types/unified-chat.ts`

New types: `ExecutionMode`, `ModeSource`, `WorkflowStepStatus`, `WorkflowStep`, `WorkflowState`, `TrackedToolCall`, `Checkpoint`, `TokenUsage`, `ExecutionTime`.

---

## 6. New Backend Tests

**Directory** `backend/tests/unit/orchestration/pipeline/` (NEW, Phase 45 Sprint 158):
- `test_context.py`, `test_pipeline_e2e.py`, `test_service.py`, `test_step6_dispatch.py`, `test_step8_api.py`, `test_steps.py`, `test_steps_3_5.py`

**Directory** `backend/tests/unit/api/v1/experts/` (Phase 46):
- `test_routes.py`, `test_crud_routes.py`

**Directory** `backend/tests/unit/integrations/orchestration/experts/` (Phase 46):
- `test_bridge.py`, `test_domain_tools.py`, `test_registry.py`

**Single file** `backend/tests/unit/test_sprint166_dynamic_agents.py` (Sprint 166):
- Tests `SubagentExecutor._infer_complexity()` — pipeline rules + task text overrides + `MAX_SUBTASKS=10` cap.

**Test count**: backend tests went from 386 → ~460 (~+74 files).

---

## 7. Dynamic Agent Count (Sprint 166)

**File**: `backend/src/integrations/orchestration/dispatch/executors/subagent.py`
**Function**: `SubagentExecutor._infer_complexity()`

**Complexity values**: `"simple"`, `"moderate"`, `"complex"`, `"auto"`

**Pipeline rules** (from `risk_level` + `intent_summary`):
- `CRITICAL`/`HIGH` risk → `"complex"`
- `INCIDENT` in intent_summary → `"complex"`
- `MEDIUM` risk → `"moderate"`
- `CHANGE` intent → `"moderate"`
- `QUERY` + `LOW` → `"simple"`
- Empty fields → `"auto"`

**Task text overrides**:
- `"multiple services down"` → `"complex"` (even if LOW/QUERY)
- 2+ domains mentioned → `"moderate"`
- `"investigate"` keyword → `"moderate"`
- 3+ domains → `"complex"`

**Subtask cap**: `MAX_SUBTASKS = 10`.

---

## 8. Orchestration Pipeline Flow (E2E)

**Entry**: `POST /orchestration/chat` with `ChatRequest`

```
1. Step1Memory (memory_read)         → ctx.memory_text
2. Step2Knowledge (knowledge_search) → ctx.knowledge_text
3. Step3Intent (intent_analysis)     → ctx.routing_decision + completeness check
                                       → [DialogPauseException if incomplete]
4. Step4Risk (risk_assessment)       → ctx.risk_assessment
5. Step5HITL (hitl_gate)             → [HITLPauseException if HIGH/CRITICAL]
6. Step6LLMRoute (llm_route_decision) → ctx.selected_route
                                       → (fast-path for QUERY/REQUEST confidence ≥ 0.92)
7. (Dispatch) DispatchService.dispatch(ExecutionRoute)
                                       → BaseExecutor.execute()
                                       → direct_answer | subagent | team (PoC run_parallel_team)
8. Step8PostProcess (postprocess)    → checkpoint save + memory extraction → ctx.checkpoint_id
```

**Pause/resume**: `DialogPauseException` and `HITLPauseException` save checkpoint; `ResumeService` re-enters pipeline at `start_from_step`.

---

## 9. File Inventory Changes

| Area | V9 Baseline (2026-03-31) | Post-Phase 47 (2026-04-19) | Delta |
|------|-------------------------|----------------------------|-------|
| Backend `.py` (src) | 792 | 862 | +70 |
| Frontend `.ts/.tsx` (src) | 236 | 254 | +18 |
| Backend tests `.py` | 386 | 460 | +74 |
| **Total source files** | **1028** | **1116** | **+88** |

Change breakdown across 194 changed files:
- Added: 123 files
- Deleted: 10 files
- Modified: 52 files
- Renamed: 27 files (mostly `agent-swarm/*` → `agent-team/*`)

---

## 10. Evidence Notes / Caveats

- **Unmerged branches NOT included** in this delta:
  - `feature/intent-classifier-improvements` (ahead=1)
  - `feature/subagent-count-control` (ahead=2)
  - `poc/anthropic-chatclient` (ahead=4)
  - `poc/unified-tools` (ahead=1)
  - These are in separate worktrees but not in main.
- **Verification method**: parallel evidence collection via 4 Explore agents reading actual source files.
- **Flagged for manual review**: Step 7 of pipeline is NOT a pipeline step but is the dispatch execution phase handled by `DispatchService`. Confirm if this is intentional naming.
- **LOC totals**: not yet re-computed; V9 baseline was 327,582 LOC. Estimated +28,944 insertions suggest post-change total is in ~350K range but exact count requires full scan.

---

*End of delta-phase-45-47.md*
