# Delta Report: Phase 43-44 (True Swarm + Magentic Orchestrator)

> V8 -> V9 Changes | Sprints 148-152 | ~52 Story Points
> Status: Phase 43 partially implemented (Sprint 148); Phase 44 in planning
> Period: Planned for post-Phase 42 completion

---

### Swarm 執行引擎架構 (Phase 43 目標)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              Phase 43 Swarm Engine — Mock → Real 架構轉換                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  用戶複雜任務 (e.g. "診斷伺服器故障")                                      │
│       │                                                                     │
│       ↓                                                                     │
│  ┌──────────────────────────────────────────┐                               │
│  │  TaskDecomposer (LLM 分析)              │                               │
│  │  複雜任務 → 子任務分解 → Worker 分配     │                               │
│  └─────────────────┬────────────────────────┘                               │
│                    │                                                         │
│       ┌────────────┼────────────┐                                           │
│       ↓            ↓            ↓                                           │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐     asyncio.gather()                 │
│  │Worker A │ │Worker B │ │Worker C │     (真正並行, 非 for 迴圈)           │
│  │Network  │ │Database │ │App      │                                        │
│  │Expert   │ │Expert   │ │Expert   │                                        │
│  │         │ │         │ │         │                                        │
│  │┌───────┐│ │┌───────┐│ │┌───────┐│                                       │
│  ││ Tool  ││ ││ Tool  ││ ││ Tool  ││  每個 Worker 獨立工具註冊表            │
│  ││Registry││ ││Registry││ ││Registry││                                      │
│  │└───────┘│ │└───────┘│ │└───────┘│                                       │
│  └────┬────┘ └────┬────┘ └────┬────┘                                       │
│       │           │           │                                             │
│       └─────┬─────┴─────┬─────┘                                             │
│             │           │                                                    │
│             ↓           ↓                                                    │
│  ┌──────────────┐  ┌──────────────────────┐                                 │
│  │SwarmEvent    │  │ SwarmTracker          │                                 │
│  │Emitter       │  │ (thread-safe state)   │                                 │
│  │→ SSE 即時串流│  │ 進度追蹤 + 結果聚合  │                                 │
│  └──────────────┘  └──────────────────────┘                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6 個缺口封閉路線圖

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              Phase 43 缺口封閉計劃                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Gap   Current State              Target State              Priority        │
│  ───   ─────────────              ────────────              ────────        │
│                                                                             │
│  #1    for loop (sequential)  →   asyncio.gather()          🔴 CRITICAL    │
│        Workers 逐一執行           真正並行執行                              │
│                                                                             │
│  #2    tools=None             →   Per-worker ToolRegistry   🔴 CRITICAL    │
│        Worker 無工具存取          獨立工具 + function call                  │
│                                                                             │
│  #3    SwarmEventEmitter      →   Connected to SSE          🟡 HIGH        │
│        已建但未接線               PipelineEventEmitter                      │
│                                                                             │
│  #4    只有最終結果            →   即時 think/tool events    🟡 HIGH        │
│        無中間過程事件             每步驟串流到前端                          │
│                                                                             │
│  #5    demo.py polling        →   AG-UI CustomEvent format  🟢 MEDIUM      │
│        格式不相容                 統一 SSE 格式                             │
│                                                                             │
│  #6    swarmStore unused      →   Single source of truth    🟢 MEDIUM      │
│        多 hooks 各管各的          Zustand 統一管理                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 43: Agent Swarm Complete Implementation — True Multi-Agent Parallel Collaboration
- **Sprints**: 148-150
- **Story Points**: ~36
- **Status**: Partially Implemented (Sprint 148 completed via commit `a0438f1`; Sprints 149-150 planned)

### Core Problem (6 Key Gaps)
Phase 42 connected Swarm UI framework (AgentSwarmPanel in Chat, SSE event definitions, swarmStore), but the **core execution engine** remains stub/mock:

| # | Gap | Current State | Target |
|---|-----|--------------|--------|
| 1 | Workers always sequential | `_execute_all_workers()` uses `for` loop even when mode=parallel | `asyncio.gather()` true parallel |
| 2 | Workers have no tool access | `_execute_worker_task()` passes `tools=None` | Each Worker gets independent tool registry + function calling |
| 3 | SwarmEventEmitter disconnected | Built but not connected to SSE endpoint or execution path | Workers emit real-time events to frontend |
| 4 | No thinking/tool_call events | Workers return only final results, no process events | Every think/tool-call/progress step streams in real-time |
| 5 | Demo SSE format incompatible | demo.py uses polling+snapshot, not AG-UI CustomEvent format | Unified AG-UI or Pipeline SSE format |
| 6 | swarmStore not integrated | Various hooks manage own state; swarmStore unused | Chat Swarm managed by single swarmStore |

### Existing Infrastructure (Reusable)
- SwarmTracker — thread-safe swarm/worker state tracking
- SwarmEventEmitter — event emitter with throttle and batch
- SwarmModeHandler — framework exists (analyze_for_swarm, execute)
- Frontend 15 components — AgentSwarmPanel, WorkerCard, WorkerDetailDrawer, ExtendedThinkingPanel, ToolCallsPanel, etc.
- swarmStore (Zustand) — store with complete actions
- AG-UI Swarm event type definitions (events.ts: 9 event types)

### New Files (Sprint 148)

**Backend — Swarm Engine**
| File | Purpose |
|------|---------|
| `backend/src/integrations/swarm/worker_executor.py` | SwarmWorkerExecutor: independent executor per worker with LLM `chat_with_tools()` + tool registry + event emitter |
| `backend/src/integrations/swarm/task_decomposer.py` | TaskDecomposer: LLM analyzes complex tasks and breaks into subtasks for worker distribution |
| `backend/src/integrations/swarm/worker_roles.py` | Worker role definitions (NetworkExpert, DatabaseExpert, ApplicationExpert, etc.) |

> **Note**: These files were first created in Phase 43 Sprint 148 (commit `a0438f1`). They did NOT exist before Phase 43 — `git diff --diff-filter=A` confirms first addition in Sprint 148.

### Planned Modifications
| File | Change |
|------|--------|
| `backend/src/integrations/swarm/swarm_integration.py` | `_execute_all_workers()` rewritten: `for` loop -> `asyncio.gather()` for true parallel execution |
| `backend/src/integrations/swarm/swarm_integration.py` | `_execute_worker_task()` receives tool registry + function calling capability |
| `backend/src/integrations/swarm/events/emitter.py` | Connected to PipelineEventEmitter bridge for SSE delivery |
| `backend/src/integrations/hybrid/orchestrator/handlers/execution.py` | ExecutionHandler -> SwarmModeHandler complete wiring |
| `frontend/src/stores/swarmStore.ts` | Populated by SSE events from pipeline (not mock data) |
| Frontend WorkerDetailDrawer | Integrated into Chat (currently only in SwarmTestPage) |

### Planned Architecture Changes

**Worker Execution Architecture**:
```
SwarmWorkerExecutor per worker:
  1. Receives: worker_id, role, subtask, llm_service, tool_registry, event_emitter
  2. Executes: LLM chat_with_tools() in function calling loop
  3. Emits: WORKER_THINKING -> WORKER_TOOL_CALL -> WORKER_PROGRESS -> WORKER_COMPLETED
  4. Returns: WorkerResult(content, worker_id)
```

**Complete SSE Event Set (11 events)**:
| Event | Trigger |
|-------|---------|
| SWARM_STARTED | Swarm session created |
| SWARM_WORKER_START | Worker begins execution |
| SWARM_WORKER_THINKING | Worker LLM reasoning |
| SWARM_WORKER_TOOL_CALL | Worker invokes tool |
| SWARM_WORKER_PROGRESS | Worker progress update (0-100) |
| SWARM_WORKER_MESSAGE | Worker intermediate message |
| SWARM_WORKER_COMPLETED | Worker finished |
| SWARM_WORKER_FAILED | Worker error |
| SWARM_PROGRESS | Overall progress |
| SWARM_AGGREGATING | Result aggregation started |
| SWARM_COMPLETED | Entire swarm finished |

**Result Aggregation**: LLM-based aggregator synthesizes all worker results into unified response, streamed via TEXT_DELTA events.

### Planned Features
- True parallel worker execution via `asyncio.gather()`
- Each worker has independent tool registry + function calling
- Real-time per-worker SSE events (thinking, tool calls, progress)
- TaskDecomposer: LLM breaks complex tasks into subtasks
- WorkerDetailDrawer in Chat showing thinking + tool calls + messages
- swarmStore populated by real SSE events
- Result aggregation with LLM synthesis
- Worker timeout (60s default) with graceful fallback
- Rate limiter for parallel LLM calls

### Sprint Breakdown

**Sprint 148 (~14 SP)**: Swarm Core Engine
- Task decomposition with LLM
- Worker parallel execution via asyncio.gather()
- Worker tool access (chat_with_tools + tool registry)
- Per-worker SSE event emission

**Sprint 149 (~12 SP)**: Worker Detail Visualization
- WorkerDetailDrawer integrated in Chat
- Extended Thinking panel for worker reasoning
- Tool Calls panel for worker tool invocations
- swarmStore unified state management

**Sprint 150 (~10 SP)**: Result Aggregation + Robustness + E2E
- LLM-based result aggregation
- Error handling (worker failure, timeout, partial results)
- Complete E2E verification

---

## Phase 44: Magentic Orchestrator Agent — Multi-Model Dynamic Selection + Manager Upgrade
- **Sprints**: 151-152
- **Story Points**: ~16
- **Status**: In Planning

### Core Problem (4 Key Gaps)
| # | Gap | Current State | Target |
|---|-----|--------------|--------|
| 1 | Manager model not configurable | `StandardMagenticManager()` with no parameters | YAML config + auto-select Opus/Sonnet/Haiku/GPT by risk |
| 2 | Only Azure OpenAI | `LLMServiceFactory` supports only azure/mock | Add Anthropic provider (AnthropicChatClient) |
| 3 | build() doesn't pass manager | `MagenticBuilder(participants=...).build()` skips manager config | Pass `manager_agent=` at construction (PoC verified) |
| 4 | Risk level not forwarded | FrameworkSelector's routing_decision not passed to MagenticBuilderAdapter | risk_level drives ManagerModelSelector |

### Existing Infrastructure (Reusable)
- `anthropic>=0.84.0` installed; `claude_sdk/client.py` has AsyncAnthropic experience
- `BaseChatClient` — MAF core abstract base class, designed for extension
- `MagenticBuilderAdapter` — has `with_manager()`, `with_plan_review()` methods
- `MagenticBuilder` constructor accepts `manager_agent=` parameter (PoC verified)
- `RiskLevel` enum: CRITICAL/HIGH/MEDIUM/LOW
- `FrameworkSelector.select_framework()` accepts `routing_decision` with risk_level
- `LLMServiceProtocol` — generate + generate_structured + chat_with_tools
- `StandardMagenticManager` — MAF official Manager accepting `agent_executor` etc.

### Planned New Files
| Planned File | Purpose | Est. LOC |
|-------------|---------|----------|
| `backend/config/manager_models.yaml` | YAML configuration: model definitions + selection strategy per risk level | ~80 |
| `backend/src/integrations/agent_framework/clients/anthropic_chat_client.py` | AnthropicChatClient(BaseChatClient): wraps AsyncAnthropic as MAF ChatClient | ~150 |
| `backend/src/integrations/hybrid/orchestrator/manager_model_registry.py` | ManagerModelRegistry: loads YAML config, manages multiple provider/model entries | ~120 |
| `backend/src/integrations/hybrid/orchestrator/manager_model_selector.py` | ManagerModelSelector: auto-selects model based on risk_level + complexity | ~60 |
| `backend/src/api/v1/orchestration/manager_model_routes.py` | API endpoints: list models, test connection, auto-select | ~50 |

### Planned Modifications
| File | Change | Est. LOC |
|------|--------|----------|
| `backend/src/integrations/agent_framework/builders/magentic.py` | Fix `build()` to pass `manager_agent=` to MagenticBuilder constructor | ~30 lines |
| `backend/src/integrations/hybrid/intent/router.py` | Forward risk_level through FrameworkSelector to Builder | ~15 lines |

**Total**: 5 new files (~460 LOC) + 2 modified files (~45 lines)

### Planned Architecture Changes

**Data Flow**:
```
User Input + Mode Selection
  -> [L4] BusinessIntentRouter.route() -> RoutingDecision
  -> [L4] RiskAssessor.assess() -> RiskLevel
  -> [L4] HITLController.check() -> Approved
  -> [L5] FrameworkSelector.select_framework(routing_decision=) -> ExecutionMode
  -> [L5->L6] ManagerModelSelector.select_model(risk_level, complexity)  [NEW]
  -> [L6] MagenticBuilderAdapter.build_with_model_selection()  [NEW]
       -> AnthropicChatClient / AzureOpenAI client  [NEW]
       -> Agent(client, name="Manager", instructions="...")
       -> MagenticBuilder(participants=..., manager_agent=manager)
       -> builder.build()
  -> [L6] workflow.run(task)
```

**Model Selection Strategy**:
| Risk Level | Manager Model | Scenario |
|-----------|---------------|----------|
| CRITICAL | claude-opus-4-6 + Extended Thinking 10K | Full system outage, ERP migration |
| HIGH | claude-sonnet-4-6 + Extended Thinking 5K | Security incident, deployment failure |
| MEDIUM | gpt-4o | Routine change management, service request |
| LOW | claude-haiku-4-5 | Information query, status check |
| USER_OVERRIDE | Any registered model | Dev/test, manual selection |

**Key Design Principles**:
1. Minimal change scope — only L5 (FrameworkSelector forwarding) and L6 (Builder integration) modified; L1-L4 and L7-L11 untouched
2. YAML zero-code config — ops team edits `config/manager_models.yaml` to switch models
3. Auto fallback — Claude API unavailable triggers automatic downgrade to Azure OpenAI
4. Adapter pattern — AnthropicChatClient implements MAF `BaseChatClient`, not a hack
5. Fix before build — Step 0 fixes `build()` forwarding, ensures foundation correct before adding features

### Planned Features
- Multi-model support: Anthropic (Opus/Sonnet/Haiku) + Azure OpenAI (GPT-4o)
- Risk-based automatic model selection (CRITICAL->Opus, HIGH->Sonnet, MEDIUM->GPT-4o, LOW->Haiku)
- YAML-based model configuration (zero code changes for model switching)
- AnthropicChatClient implementing MAF BaseChatClient interface
- API endpoints for model listing, connection testing, auto-selection
- Automatic fallback when primary provider unavailable
- Extended Thinking support configurable per risk level
- MagenticBuilder correctly receives manager_agent parameter (PoC verified)

### Sprint Breakdown

**Sprint 151 (~9 SP)**: Foundation
- AnthropicChatClient(BaseChatClient) implementation
- ManagerModelRegistry with YAML config loading
- ManagerModelSelector with risk-based selection
- Fix MagenticBuilderAdapter.build() to pass manager_agent=

**Sprint 152 (~7 SP)**: Integration + E2E
- MagenticBuilderAdapter integration with ManagerModelSelector
- FrameworkSelector forwards risk_level to Builder
- API endpoints for model management
- E2E verification: different risk levels -> different models

---

## Summary: Phase 43-44 Delta

### Aggregate Metrics
| Metric | Value |
|--------|-------|
| Total Sprints | 5 (148-152) |
| Total Story Points | ~52 |
| New Backend Files (Planned) | ~8 (3 swarm + 5 magentic) |
| Modified Files (Planned) | ~8 |
| Status | Phase 43: Partially implemented (Sprint 148 done) / Phase 44: In Planning |

### Key Transformation (Planned)
**Before (Post Phase 42)**: Swarm UI connected but engine is stub/mock; Workers execute sequentially with no tools; MagenticBuilder uses default StandardMagenticManager with fixed model.

**After (Post Phase 44)**: True multi-agent parallel execution with per-worker tool access and real-time SSE events; MagenticBuilder dynamically selects optimal LLM model (Opus/Sonnet/GPT-4o/Haiku) based on task risk level via YAML configuration.

### Dependencies
- Phase 43 depends on Phase 42 completion (SSE streaming, Mode Selector, HITL)
- Phase 44 depends on Phase 42-43 (E2E Pipeline + Swarm Core Engine)
- Phase 44 also depends on REFACTOR-001 (LLMServiceProtocol.chat_with_tools)
- `anthropic>=0.84.0` already installed
- `agent-framework>=1.0.0rc4` already installed

### Risk Summary
| Risk | Phases | Mitigation |
|------|--------|-----------|
| Parallel LLM calls hit API rate limits | 43 | Rate limiter + configurable max parallelism |
| Task decomposition inaccuracy | 43 | Structured LLM prompt rules + user manual adjustment |
| Large SSE event volume causes frontend lag | 43 | SwarmEventEmitter throttle (100ms) + React.memo |
| build() fix may break existing flows | 44 | E2E test verification before and after fix |
| AnthropicChatClient format conversion issues | 44 | Start with simple prompts, incrementally add complexity |
| Cost control (Opus expensive) | 44 | max_cost_per_task limit + auto-downgrade strategy |

### PoC Validation (Phase 44)
All 5 PoC steps passed for Magentic Orchestrator upgrade:
- `BaseChatClient` extension confirmed
- `MagenticBuilder(manager_agent=)` parameter injection confirmed
- Anthropic API integration pattern validated
- Risk-based model selection logic verified
- YAML configuration loading tested

See: `docs/07-analysis/claude-agent-study/poc-findings.md`
