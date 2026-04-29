# Sprint 50.2 — API + Frontend 對接

**Sprint**: 50.2
**Phase**: 50 (Loop Core) — 第 2 個（最後一個）sprint
**Start Date**: 2026-04-30
**Target End Date**: 2026-05-06（1 週）
**Branch**: `feature/phase-50-sprint-2-api-frontend`（從 `feature/phase-50-sprint-1-loop-core` HEAD 拉）
**Story Points**: 28 SP（plan，actual 預估 ~5-6h per 49.x / 50.1 ~19% 比率）
**Authority**: [`06-phase-roadmap.md` §Sprint 50.2](../06-phase-roadmap.md#sprint-502-api--frontend-對接) / [`02-architecture-design.md` §SSE 事件規範](../02-architecture-design.md#sse-事件規範frontend--backend) / [`16-frontend-design.md` §Chat 頁面設計](../16-frontend-design.md#chat-頁面設計最重要)

---

## 0. Context — 50.1 已收尾、50.2 準備就緒

**Sprint 50.1 ✅ DONE 2026-04-30**（10 commits）:
- `agent_harness/orchestrator_loop/{loop,termination,events}.py` — `AgentLoopImpl` while-true TAO loop + 4 terminator
- `agent_harness/output_parser/{parser,classifier,types}.py` — `OutputParserImpl` + `classify_output` 3-way
- `agent_harness/tools/_inmemory.py` — `InMemoryToolRegistry` + `make_echo_executor()` factory（DEPRECATED-IN: 51.1）
- `scripts/lint/check_ap1_pipeline_disguise.py` — V2 Lint #5（AP-1）
- 60 new tests / 210 PASS / mypy 131 / 5 V2 lints OK

**Sprint 50.1 retrospective.md CARRY-001..009** 中本 sprint 接 5 項：
- **CARRY-001** Day 0：`python -m pytest` rule 加進 `testing.md` + pre-commit hook line（trivial）
- **CARRY-002** Day 0：fix `datetime.utcnow()` → `datetime.now(UTC)` in `_contracts/events.py`（trivial / 28+ DeprecationWarning 消音）
- **CARRY-003** Day 3-4：Frontend `pages/chat-v2/` skeleton + SSE 消費
- **CARRY-004** Day 1-2：API endpoint `POST /api/v1/chat/` + SSE 序列化
- **CARRY-005** Day 2-3：`runtime/workers/agent_loop_worker.py` 49.4 stub 接 `AgentLoopImpl.run()` 真實 handler
- **CARRY-006** Day 4：streaming partial-token emit — **🚧 延後 Phase 51.2 / 52.1**（依 ChatClient.stream() 完整實作；50.2 只 emit native LoopEvent）
- **CARRY-007** Day 5：real Azure OpenAI demo（用戶手動 trigger，AI 助手提供 wiring）
- **CARRY-008/009** 51.x backlog（不在 50.2）

---

## 1. Sprint Goal（一句話）

把 50.1 完成的 `AgentLoopImpl` + InMemoryToolRegistry + echo executor，**經由 `POST /api/v1/chat/` SSE endpoint 暴露給 frontend `pages/chat-v2/`**，達成「用戶在 V2 chat-v2 介面輸入 → 即時看到 LoopEvent 流（thinking / tool_call / tool_result / final）→ 拿到 echo 回答」的端到端閉環。

> **驗收原則**：範疇 1 從 Level 2 → **Level 3**（接入主流量），範疇 6 → **Level 4**（完全 native + frontend 顯示）。

---

## 2. User Stories（5 個）

### US-1：API 端點 ✅ Cat 1 / Adapters 主流量入口
**作為** V2 backend 開發者
**我希望** `POST /api/v1/chat/` 接收 user message → 啟動 `AgentLoopImpl.run()` → 透過 SSE 即時 push `LoopEvent` 給 client
**以便** 前端可一邊看 loop 進行一邊收事件，不用 polling

### US-2：Worker 整合 ✅ 49.4 stub → 真實 handler
**作為** runtime 設計者
**我希望** 49.4 `agent_loop_worker.py` 的 `_default_handler` 被替換為**呼叫 `AgentLoopImpl.run()` 並把 LoopEvent 寫進 SSE channel** 的真實 handler
**以便** Phase 53.1 接 Temporal / SQS 等真實 broker 時，handler 邏輯已經 ready，只換 backend

### US-3：Frontend 主介面 ✅ Cat 範疇 1 / 6 主流量驗證
**作為** 終端用戶
**我希望** 在 `/chat-v2` 頁面輸入 echo X，即時看到：
1. `loop_start` → 顯示 session_id
2. `turn_start` → 顯示 turn 編號
3. `llm_response` → 顯示 thinking + tool_calls
4. `tool_call_request` → 顯示 echo_tool args = X
5. `tool_call_result` → 顯示 echo result = X
6. `loop_end` → 顯示 X 答覆 + total_turns + total_tokens
**以便** 我看到完整的 TAO loop 過程，不只是最終答覆

### US-4：Demo 案例可重現
**作為** 用戶 / reviewer
**我希望** 有一個固定 e2e 演示腳本「問 echo X → 答 X」可在 dev 環境一鍵跑通
**以便** Phase 50 closeout 時可示範範疇 1 / 6 主流量達 Level 3+ / Level 4

### US-5：Carry-forward 收乾淨
**作為** sprint workflow maintainer
**我希望** 50.1 retrospective CARRY-001 + CARRY-002 trivial 項在 50.2 Day 0 順手清掉
**以便** 50.2 day-1+ 工作不被 deprecation warning / pytest 路徑 confusion 干擾

---

## 3. Scope

### 3.1 In-Scope（本 sprint 必交）

| 範疇 | 項目 | 對應 user story |
|------|------|--------------|
| api | `POST /api/v1/chat/` (SSE) + `GET /api/v1/chat/sessions/{id}` | US-1 |
| api | `LoopEvent` → SSE message serializer（13 event types per 02.md §SSE，本 sprint 實作 7 個 echo demo 必須）| US-1 |
| runtime | `agent_loop_worker.py` 真實 handler factory（不刪 stub）| US-2 |
| runtime | session 註冊 + cancel hook（簡化版，full HITL Phase 53.1）| US-2 |
| frontend | `pages/chat-v2/index.tsx` 取代 placeholder | US-3 |
| frontend | `features/chat_v2/{components,hooks,services,store,types}/` 全新模組 | US-3 |
| frontend | `useLoopEventStream` hook（SSE consumer）+ `chatStore` (Zustand) | US-3 |
| frontend | `MessageList` + `ToolCallCard` + `InputBar` + `ChatLayout` minimal subset | US-3 |
| 測試 | unit: API router / SSE serializer / Frontend components | US-1, US-3 |
| 測試 | integration: e2e echo demo（pytest + Playwright minimal）| US-4 |
| 文件 | progress.md / retrospective.md / Phase 50 README 收尾 | US-4 |
| trivia | CARRY-001 testing.md `python -m pytest` rule | US-5 |
| trivia | CARRY-002 datetime.utcnow() fix | US-5 |
| closeout | Real Azure OpenAI demo wiring（用戶 trigger）| US-4 |

### 3.2 Deferred / Out-of-Scope（明確標出留哪 sprint）

| 項目 | 為何延後 | Sprint 接手 |
|------|---------|----------|
| HITL approval / reject UI | 範疇 9 + §HITL 中央化 | **53.4** |
| Verification badge UI | 範疇 10 ABC | **54.1** |
| Memory Layers Inspector panel | 範疇 3 5 層 | **51.2** |
| Cost / Token tracker | 範疇 4 token budget UI | **52.1+** |
| Sessions sidebar persist（pagination / search）| 需要 sessions table query API | 51.x |
| Streaming partial-token emit (CARRY-006) | 需 ChatClient.stream() 完整實作 | **51.2 / 52.1** |
| Tripwire fired event UI | 範疇 9 | **53.3** |
| Compaction triggered event UI | 範疇 4 | **52.1** |
| Real LLM 完整測試 | 跑 real Azure OpenAI 容易消預算；50.2 只跑 1 demo confirmation | 53+（CI matrix）|
| AST-based AP-1 lint refinement (CARRY-009) | 50.1 substring-based 已 acceptable | 51.x backlog |

---

## 4. Technical Specifications

### 4.1 API 層（`api/v1/chat/`）

```
backend/src/api/v1/chat/
├── __init__.py        — re-export router
├── router.py          — POST /chat (SSE) + GET /chat/sessions/{id}
├── sse.py             — LoopEvent → SSE event_dict serializer
├── schemas.py         — Pydantic ChatRequest / ChatSessionResponse
├── handler.py         — build_echo_demo_handler() / build_real_llm_handler()
└── session_registry.py — in-memory session_id → asyncio.CancelEvent map
```

**`POST /api/v1/chat/` 行為**：
1. 接 `ChatRequest{ message: str, session_id: UUID | None, mode: "echo_demo" | "real_llm" }`
2. 若無 session_id 則新建 UUID + 註冊到 session_registry
3. Build `AgentLoopImpl`（依 mode）
4. Wrap `loop.run()` 的 `AsyncIterator[LoopEvent]` → `event_stream` SSE
5. Return `EventSourceResponse`（用 `sse-starlette`）

**`GET /api/v1/chat/sessions/{id}`**：return `{ session_id, status: "running"|"completed"|"cancelled", started_at }`（in-memory；Phase 53.1 + DB persist）

**Tracer / Tenant**：經 `TenantContextMiddleware`（49.3 已配）+ `setup_opentelemetry`（49.4 已配）；endpoint 創建 `TraceContext.create_root()` 傳入 `AgentLoopImpl.run()`。

### 4.2 SSE Serialization（`sse.py`）

依 `02-architecture-design.md` §SSE 事件規範 13 types。50.2 僅實作 echo demo 必須的 7 個（其餘留 sprint 接手）：

```python
# event types (50.2 subset)
"loop_start"          # data: {request_id, session_id}
"turn_start"          # data: {turn_num}
"llm_request"         # data: {model, tokens_in}        # 從 ChatRequest.usage
"llm_response"        # data: {content, tool_calls?}    # 從 LLMResponse / ParsedOutput
"tool_call_request"   # data: {tool_name, args}
"tool_call_result"    # data: {tool_name, result, is_error}
"loop_end"            # data: {result, total_turns, total_tokens}
```

**LoopEvent → SSE 對應**：50.1 `_contracts/events.py` 已有 `LoopStarted` / `Thinking` / `ToolCallRequested` / `LoopCompleted` 4 個。50.2 加映 `TurnStarted` / `LLMRequested` / `LLMResponded` / `ToolCallCompleted` 4 個（per 17.md §4.1 owner table，Cat 1 own）。

> **17.md owner check**：✅ 4 個新事件全部歸 Cat 1（Loop 主流量），與 17.md §4.1 表一致；不違反 single-source。

### 4.3 Worker Handler（`agent_loop_worker.py` 修改）

```python
# 新加：build_real_handler 工廠（不刪 _default_handler stub）
def build_agent_loop_handler(
    *,
    chat_client: ChatClient,
    tool_registry: ToolRegistry,
    tool_executor: ToolExecutor,
    output_parser: OutputParser,
    system_prompt: str,
    sse_emit: Callable[[LoopEvent], Awaitable[None]],
) -> TaskHandler:
    async def handler(envelope: TaskEnvelope) -> dict[str, object]:
        loop = AgentLoopImpl(
            chat_client=chat_client,
            output_parser=output_parser,
            tool_executor=tool_executor,
            tool_registry=tool_registry,
            system_prompt=system_prompt,
        )
        async for event in loop.run(
            session_id=UUID(envelope.task_id),
            user_input=envelope.payload["message"],
            trace_context=TraceContext(...),
        ):
            await sse_emit(event)
        return {"status": "completed"}
    return handler
```

> handler 不直接寫 SSE → 透過 `sse_emit` callback 解耦；由 `api/v1/chat/router.py` 注入。

### 4.4 Frontend（`features/chat_v2/`）

```
frontend/src/
├── pages/chat-v2/
│   └── index.tsx             — top-level route，裝 ChatLayout
└── features/chat_v2/
    ├── components/
    │   ├── ChatLayout.tsx    — 3-column placeholder（sidebar 簡化版 / conversation / inspector minimal）
    │   ├── MessageList.tsx   — render message + thinking + tool_call
    │   ├── ToolCallCard.tsx  — 折疊 tool_call_request + tool_call_result 對
    │   └── InputBar.tsx      — text input + Send button + mode toggle (echo_demo | real_llm)
    ├── hooks/
    │   └── useLoopEventStream.ts  — SSE consumer（fetch + EventSource polyfill）
    ├── services/
    │   └── chatService.ts    — fetch wrapper（POST /api/v1/chat with SSE）
    ├── store/
    │   └── chatStore.ts      — Zustand: messages[] / sessionId / status / events[]
    └── types.ts              — LoopEvent type 1:1 對應 02.md §SSE
```

**SSE consumer 策略**（per V2 frontend 哲學「real-time streaming」）：
- 用 `fetch()` + `ReadableStream` reader 解析 `text/event-stream`（不用瀏覽器原生 `EventSource` 因為它不支援 POST body）
- 收到 event → push 進 Zustand store → React re-render
- 連線中斷自動 reconnect 不在本 sprint（Phase 51+）

### 4.5 LLM-Provider Neutrality 自查

✅ 全 `agent_harness/**` 不 import LLM SDK（已 50.1 強制）
✅ `api/v1/chat/handler.py` 用 `MockChatClient`（49.4）做 echo_demo mode
✅ `real_llm` mode 用 `AzureOpenAIAdapter`（49.4 已實作）— 經 ChatClient ABC，不直接 import openai
✅ Lint #1 (LLM SDK leak grep) 仍 0

---

## 5. File Change List

### 5.1 新建（11 backend + 9 frontend = 20 檔）

#### Backend

| 路徑 | 行數估 | Category |
|------|------|---------|
| `backend/src/api/v1/chat/router.py` | ~150 | api |
| `backend/src/api/v1/chat/sse.py` | ~120 | api |
| `backend/src/api/v1/chat/schemas.py` | ~40 | api |
| `backend/src/api/v1/chat/handler.py` | ~100 | api |
| `backend/src/api/v1/chat/session_registry.py` | ~60 | api |
| `backend/tests/unit/api/v1/chat/__init__.py` | 1 | tests |
| `backend/tests/unit/api/v1/chat/test_router.py` | ~150 | tests |
| `backend/tests/unit/api/v1/chat/test_sse.py` | ~100 | tests |
| `backend/tests/unit/api/v1/chat/test_handler.py` | ~80 | tests |
| `backend/tests/unit/api/v1/chat/test_session_registry.py` | ~60 | tests |
| `backend/tests/integration/api/test_chat_e2e.py` | ~120 | tests |

#### Frontend

| 路徑 | 行數估 |
|------|------|
| `frontend/src/features/chat_v2/components/ChatLayout.tsx` | ~80 |
| `frontend/src/features/chat_v2/components/MessageList.tsx` | ~120 |
| `frontend/src/features/chat_v2/components/ToolCallCard.tsx` | ~80 |
| `frontend/src/features/chat_v2/components/InputBar.tsx` | ~60 |
| `frontend/src/features/chat_v2/hooks/useLoopEventStream.ts` | ~120 |
| `frontend/src/features/chat_v2/services/chatService.ts` | ~80 |
| `frontend/src/features/chat_v2/store/chatStore.ts` | ~80 |
| `frontend/src/features/chat_v2/types.ts` | ~80 |
| `frontend/__tests__/features/chat_v2/useLoopEventStream.test.ts` | ~100 |

### 5.2 修改（8 檔）

| 路徑 | 改動 |
|------|------|
| `backend/src/api/main.py` | include `chat.router` |
| `backend/src/api/v1/chat/__init__.py` | re-export `router` |
| `backend/src/runtime/workers/agent_loop_worker.py` | 加 `build_agent_loop_handler` factory（保留 stub）|
| `backend/src/agent_harness/_contracts/events.py` | CARRY-002 datetime.utcnow → now(UTC) + 加 4 events（TurnStarted / LLMRequested / LLMResponded / ToolCallCompleted） |
| `backend/src/agent_harness/orchestrator_loop/loop.py` | yield 4 個新 events |
| `backend/src/agent_harness/orchestrator_loop/events.py` | re-export 4 個新 event |
| `frontend/src/pages/chat-v2/index.tsx` | 取代 placeholder |
| `.claude/rules/testing.md` | CARRY-001 加 `python -m pytest` rule |

### 5.3 文件

| 路徑 | 改動 |
|------|------|
| `docs/03-implementation/agent-harness-execution/phase-50/sprint-50-2/progress.md` | 每 day 寫 |
| `docs/03-implementation/agent-harness-execution/phase-50/sprint-50-2/retrospective.md` | Day 5 寫 |
| `docs/03-implementation/agent-harness-planning/phase-50-loop-core/README.md` | 50.2 標 ✅ DONE / Phase 50 progress 2/2 |
| `MEMORY.md` + `memory/project_phase50_loop_core.md` | sprint closeout 更新 |

---

## 6. Acceptance Criteria

### 6.1 結構驗收（per 06-roadmap §Sprint 50.2 驗收）

- [ ] 用戶在前端 chat-v2 輸入訊息 → 看到完整 loop 過程 → 拿到答案
- [ ] 範疇 1 達 Level 3（接入主流量 — 從 API 入點 → AgentLoopImpl → frontend 完整鏈路）
- [ ] 範疇 6 達 Level 4（完全 native — frontend 真的 render parse 後的 tool_calls + thinking）

### 6.2 質量門檻

- [ ] pytest backend 全 PASS（210 + ~30 new = ~240 PASS）
- [ ] frontend `npm run test` PASS
- [ ] backend mypy --strict 通過所有新檔
- [ ] frontend `npm run lint` + `npm run build` 通過
- [ ] 5 V2 lints 全 OK（含 50.1 新增 AP-1）
- [ ] LLM SDK leak grep（agent_harness + business_domain）= 0
- [ ] alembic from-zero cycle 通過（無新 migration 預期）
- [ ] CARRY-001（testing.md 加 rule）+ CARRY-002（datetime.utcnow fix）已 close

### 6.3 端到端

- [ ] echo_demo 模式在 dev 環境跑通（用戶手動驗）
- [ ] real_llm 模式至少 1 個 demo 跑通 with Azure OpenAI（Day 5 closeout）
- [ ] 前端 SSE 連線中斷時優雅顯示 error toast（不 hang）
- [ ] cancellation：用戶按「Stop」按鈕能中斷正在跑的 loop（per 49.4 + 50.1 cancellation safety pattern）

### 6.4 文件 / 紀律

- [ ] checklist 90+ items 全 [x]（除非有明確 🚧 + reason）
- [ ] progress.md Day 0-5 每天有紀錄
- [ ] retrospective.md 含 estimate accuracy / 3 lessons / 50.2 carry-forward
- [ ] Phase 50 README 標 ✅ DONE 2/2 = 100%
- [ ] memory/project_phase50_loop_core.md 同步

---

## 7. Day-by-Day Breakdown

| Day | 主題 | 預估 |
|-----|------|------|
| **Day 0** | Branch + plan/checklist commit + CARRY-001 + CARRY-002 + Phase 50 README 標 in-progress | ≤30 min |
| **Day 1** | API 層：router + sse + schemas + handler + session_registry + 5 unit tests | 6h |
| **Day 2** | Worker handler integration + 4 個新 LoopEvent + Loop yield 修改 + 8 unit tests | 6h |
| **Day 3** | Frontend skeleton：ChatLayout + types + chatStore + chatService + useLoopEventStream + 1 unit test | 6h |
| **Day 4** | Frontend wiring：MessageList + ToolCallCard + InputBar + e2e demo + integration test | 6h |
| **Day 5** | Real Azure OpenAI demo + retrospective + Phase 50 README 收尾 + MEMORY 同步 | 4h |
| **Total** | | ~28h plan / actual TBD（預估 ~5-6h per 50.1 19% 比率）|

---

## 8. Dependencies & Risks

### 8.1 Dependencies

- ✅ 50.1 `AgentLoopImpl` real `AsyncIterator[LoopEvent]`（unblocked）
- ✅ 49.4 `MockChatClient` + `AzureOpenAIAdapter`（unblocked）
- ✅ 49.4 `agent_loop_worker.py` `TaskHandler` sig（unblocked）
- ✅ 49.4 OTel SDK + JSON logger + TenantContextMiddleware（unblocked）
- ⏸ Frontend SSE consumer fetch streaming：需驗證 Vite dev server proxy + browser fetch streaming compatibility（Day 3 risk）

### 8.2 Risks

| Risk | 影響 | Mitigation |
|------|------|---------|
| **Vite SSE proxy 配置 quirk** | 50.2 frontend 跑不起來 | Day 3 先寫 raw `curl http://localhost:8000/api/v1/chat` 確認 SSE 從 backend 出來；frontend 部分用 `fetch + ReadableStream`（不是 `EventSource`）規避 POST 限制 |
| **`sse-starlette` 版本相容性** | API 啟動失敗 | 用 49.4 已驗證的 starlette / fastapi 版本；rollback to manual `StreamingResponse` 若有問題 |
| **Real Azure OpenAI demo 預算超支** | Day 5 卡住 | 限 1 個 demo 5 turn 內結束；用 echo_demo 為主驗收，real_llm 為 spot check |
| **新 4 個 LoopEvent 與 17.md owner 表不一致** | violation 17.md §1 single-source | Day 2 Step 1：先驗 17.md §4.1 表，把 owner 標清楚；不確定就先不加，用 LoopStarted+Thinking+ToolCallRequested+LoopCompleted 4 個就夠 echo demo |
| **Frontend Zustand state shape 與 SSE event 不對齊** | UI 渲染崩潰 | Day 3 先定 types.ts（1:1 對應 02.md §SSE）→ 再寫 store；schema-first |
| **cancellation 在 frontend 中斷 fetch 時 backend 沒清理** | leak | Day 4 加 integration test：abort fetch 後 verify backend 清理 session_registry |

---

## 9. Test Strategy

### 9.1 Unit tests（~30 new）

- API router (5)：endpoint 接受合法 / 拒絕 invalid / SSE response shape
- SSE serializer (4)：每個 LoopEvent type 對應正確 SSE event_dict
- Handler factory (3)：build echo handler / build real handler / handler error path
- Session registry (3)：register / cancel / cleanup
- Loop new events (4)：4 個新 LoopEvent emit 在正確時機
- Frontend useLoopEventStream (4)：connect / receive / disconnect / error
- Frontend chatStore (3)：addMessage / mergeEvent / reset

### 9.2 Integration tests（~3）

- e2e echo demo：spawn FastAPI test client → POST /api/v1/chat with echo X → assert SSE 收到 7 events 順序 + final text = X
- cancellation safety：mid-flight abort → backend session_registry 清理
- real_llm spot check（marked `slow` + skip-if-no-AZURE_KEY）：1 turn smoke test

### 9.3 Frontend e2e（minimal — Phase 53.4 才有 Playwright full suite）

50.2 不導入 Playwright；frontend e2e 留 manual smoke + Phase 53.4 接 Playwright。

### 9.4 Anti-pattern check

- AP-1（Pipeline disguise Loop）：lint clean ✅（50.1 已 enforce，不會 regress）
- AP-2（Side-track）：API endpoint 必須從 `api/main.py include_router` 進入主流量
- AP-3（Cross-directory scattering）：`features/chat_v2/` 自洽，不散落到 components root

---

## 10. Definition of Done (DoD)

Sprint 50.2 視為 ✅ DONE 當且僅當：

1. ✅ `POST /api/v1/chat/` SSE endpoint 在 dev 環境跑通 echo demo
2. ✅ Frontend `/chat-v2` 顯示完整 7-event 流程
3. ✅ pytest 全 PASS / mypy strict / 5 V2 lints / LLM SDK grep = 0
4. ✅ frontend lint + build 通過
5. ✅ checklist 全 [x]（或 🚧 + reason）
6. ✅ retrospective.md / Phase 50 README / MEMORY.md 同步
7. ✅ CARRY-001 + CARRY-002 closed
8. ✅ Phase 50 progress = 2/2 = 100%
9. ✅ 範疇成熟度更新：Cat 1 → Level 3，Cat 6 → Level 4
10. ✅ V2 累計：6/22 sprint complete（49.1, 49.2, 49.3, 49.4, 50.1, 50.2）

---

## 11. Out-of-band 用戶手動處理項

從 50.1 closeout 累積 + 50.2 新增：

- ⏸ **GitHub branch protection rule**（49.1 carry）— admin UI
- ⏸ **49.1+49.2+49.3+49.4+50.1+50.2 merge to main 決策**（用戶決策；50.2 closeout 後可一次合併）
- ⏸ **npm audit 2 moderate vulnerabilities**（49.1 carry）— 50.2 frontend sprint 有機會處理
- ⏸ **Production app role 在 staging 環境配置**（per Day 5.2 guide）— Phase 53.1+
- ⏸ **CI deploy gate 引入規範 E 警報**（Production cutover Phase 55）
- ⏸ **SITUATION-V2-SESSION-START.md 第八+九部分過期**（49.2/49.3/49.4/50.1/50.2 milestones）— 待用戶或 AI 助手同步
- ⏸ **Real Azure OpenAI key 配置 + 預算**（Day 5 closeout 用戶 trigger）

---

**Plan version**：1.0（2026-04-30）
**Approved by**：⏳ 待用戶 approve 才開始 code（Day 1）
**Reference plans**：[`sprint-49-1-plan.md`](../phase-49-foundation/sprint-49-1-plan.md) / [`sprint-50-1-plan.md`](./sprint-50-1-plan.md)
