# Sprint 50.2 — Checklist

**Plan**: [`sprint-50-2-plan.md`](./sprint-50-2-plan.md)
**Branch**: `feature/phase-50-sprint-2-api-frontend`
**Sacred rule**：只能 `[ ]` → `[x]`，禁止刪除未勾選項；必要時改成 `🚧 阻塞: <reason>`。
**Estimate**：28 SP / ~28h plan，per 49.x + 50.1 19% 比率預估 actual ~5-6h

---

## Day 0 — Branch + 微清理（≤30 min）

### 0.1 確認 50.1 closeout 狀態（5 min）
- [x] `git status` clean（除 user IDE 編輯 + V2-AUDIT-* 平行文件）
- [x] `git log --oneline -5` 顯示 50.1 closeout commit `92c8fd4`
- [x] `git branch --show-current` = `feature/phase-50-sprint-1-loop-core`

### 0.2 拉新 sprint branch（5 min）
- [x] `git checkout -b feature/phase-50-sprint-2-api-frontend`
- [x] DoD：`git branch --show-current` = `feature/phase-50-sprint-2-api-frontend`

### 0.3 提交 plan + checklist（5 min）
- [x] `git add docs/03-implementation/agent-harness-planning/phase-50-loop-core/sprint-50-2-{plan,checklist}.md`
- [x] commit msg：`docs(sprint-50-2): plan + checklist (Day 0)` per git-workflow.md → commit `6de7aed`
- [x] DoD：`git log --oneline -1` 顯示新 commit

### 0.4 更新 Phase 50 README 標 50.2 in-progress（5 min）
- [x] Edit `phase-50-loop-core/README.md` Sprint 進度表 50.2 改 ⏳ → 🟡 IN PROGRESS
- [x] Last Updated 改 2026-04-30
- [x] commit：`docs(sprint-50-2): Phase 50 README 50.2 in-progress (Day 0)` → commit `80c9295`

### 0.5 CARRY-001：testing.md 加 `python -m pytest` rule（5 min）
- [x] Edit `.claude/rules/testing.md` 在 §Test Commands 段加 `### Critical` block + 改 commands 範例為 `python -m pytest`
- [x] DoD：grep `python -m pytest` 在 testing.md 出現 ≥ 1 次（actual: 4 次）

### 0.6 CARRY-002：fix datetime.utcnow() in events.py（5 min）
- [x] Edit `backend/src/agent_harness/_contracts/events.py` 把 `datetime.utcnow()` 改 `datetime.now(UTC)`
- [x] 同檔頂端 `from datetime import UTC, datetime` 加 UTC
- [x] 跑 `python -m pytest backend/tests/unit/agent_harness/orchestrator_loop/` 驗證 DeprecationWarning 消失
- [x] DoD：pytest 17 PASS / 0 warnings（事前 28+ warnings）

### 0.7 commit Day 0 trivia（5 min）
- [x] `git add backend/src/agent_harness/_contracts/events.py .claude/rules/testing.md`
- [x] commit：`fix(events,docs, sprint-50-2): CARRY-001 + CARRY-002 trivia (Day 0)` → commit `80338f0`

**Day 0 Total Plan**: ≤30 min / 5 commits → **Actual: ~17 min（57%）/ 3 commits**（CARRY-001+002 合併因 scope 對等：trivia carry-forward）

---

## Day 1 — API 層（6h plan）

### 1.1 schemas.py — Pydantic models（30 min）
- [ ] 建 `backend/src/api/v1/chat/schemas.py`
- [ ] `ChatRequest` { message: str, session_id: UUID | None, mode: Literal["echo_demo", "real_llm"] = "echo_demo" }
- [ ] `ChatSessionResponse` { session_id: UUID, status: Literal["running", "completed", "cancelled"], started_at: datetime }
- [ ] `ToolCallSummary` / `MessageSummary`（for SSE event payload）
- [ ] DoD：mypy --strict 通過 + 1 unit test 驗 validation

### 1.2 session_registry.py — in-memory session map（45 min）
- [ ] 建 `backend/src/api/v1/chat/session_registry.py`
- [ ] `SessionRegistry` class：register / get / cancel / cleanup
- [ ] thread-safe（asyncio.Lock）+ session_id → asyncio.Event (cancel signal) + status enum
- [ ] DoD：3 unit test PASS（register / cancel / cleanup race）

### 1.3 sse.py — LoopEvent → SSE serializer（90 min）
- [ ] 建 `backend/src/api/v1/chat/sse.py`
- [ ] `serialize_loop_event(event: LoopEvent) -> dict` 對應 02.md §SSE 13 types
  - 50.2 必實作 7：loop_start / turn_start / llm_request / llm_response / tool_call_request / tool_call_result / loop_end
  - 其餘 6 type 留 stub（raise NotImplementedError）+ 註明 sprint owner
- [ ] `format_sse_message(event_type, data) -> bytes`（`event: ...\ndata: ...\n\n`）
- [ ] DoD：4 unit test 對 4 種 LoopEvent class 各驗一次 serialize

### 1.4 handler.py — agent loop handler factory（60 min）
- [ ] 建 `backend/src/api/v1/chat/handler.py`
- [ ] `build_echo_demo_handler() -> tuple[AgentLoopImpl, ToolRegistry, ToolExecutor]`：用 50.1 `make_echo_executor()` + `MockChatClient` scripted response
- [ ] `build_real_llm_handler() -> tuple[...]`：用 49.4 `AzureOpenAIAdapter` + `make_echo_executor()`
- [ ] DoD：3 unit test PASS（echo_demo build / real_llm build skipped if no AZURE key / wrong mode raises）

### 1.5 router.py — POST /chat + GET /sessions/{id}（120 min）
- [ ] 建 `backend/src/api/v1/chat/router.py`
- [ ] `POST /api/v1/chat/` 用 `EventSourceResponse`（sse-starlette）or 純 `StreamingResponse(media_type="text/event-stream")`
- [ ] flow：parse ChatRequest → build handler by mode → register session → wrap loop.run() generator → 每 LoopEvent → format_sse → yield bytes
- [ ] `GET /api/v1/chat/sessions/{id}` → SessionRegistry.get → return ChatSessionResponse
- [ ] include in `api/v1/chat/__init__.py`
- [ ] include in `api/main.py` `app.include_router(chat_router, prefix="/api/v1/chat")`
- [ ] DoD：5 unit test PASS（happy path / invalid mode / missing message / session 404 / cancel signal received）+ FastAPI test client integration smoke

### 1.6 Day 1 progress + commit（15 min）
- [ ] checklist 1.1-1.5 全 [x]
- [ ] 寫 `docs/03-implementation/agent-harness-execution/phase-50/sprint-50-2/progress.md` Day 1 段（estimate vs actual / surprises）
- [ ] commit：`feat(api, sprint-50-2): chat router + SSE serializer + session registry (Day 1)`
- [ ] commit checklist update：`docs(sprint-50-2): Day 1 progress + checklist [x] update`

**Day 1 Total Plan**: ~6h / ~15 unit tests / 2 commits

---

## Day 2 — Worker 整合 + 4 新 LoopEvent（6h plan）

### 2.1 17.md owner check — 4 個新 LoopEvent（15 min）
- [ ] Read `17-cross-category-interfaces.md` §4.1 Event ownership table
- [ ] 確認 `TurnStarted` / `LLMRequested` / `LLMResponded` / `ToolCallCompleted` 4 個 owner = Cat 1
- [ ] 若 17.md 沒明列，則寫提案 PR comment 同步表更新（Day 2 commit 同次提）
- [ ] DoD：4 個新 event 在 17.md 表中有條目（或 commit 訊息 explicitly extends 17.md）

### 2.2 _contracts/events.py 加 4 新 event class（45 min）
- [ ] Edit `backend/src/agent_harness/_contracts/events.py`
- [ ] 加 `TurnStarted(LoopEvent)` { turn_num: int }
- [ ] 加 `LLMRequested(LoopEvent)` { model: str, tokens_in: int }
- [ ] 加 `LLMResponded(LoopEvent)` { content: str, tool_calls: list, thinking: str | None = None }
- [ ] 加 `ToolCallCompleted(LoopEvent)` { tool_name: str, result: object, is_error: bool }
- [ ] 全用 50.1 已 fix 的 `datetime.now(UTC)` default_factory
- [ ] Modification History 加 entry
- [ ] DoD：mypy strict 通過 + 4 dataclass test PASS

### 2.3 events.py shim 加 re-export（10 min）
- [ ] Edit `backend/src/agent_harness/orchestrator_loop/events.py` 加 4 個新 re-export
- [ ] 更新 Modification History
- [ ] DoD：`from agent_harness.orchestrator_loop.events import TurnStarted` 通過

### 2.4 loop.py yield 4 新 event 在正確時機（90 min）
- [ ] Edit `backend/src/agent_harness/orchestrator_loop/loop.py`
- [ ] turn loop start → yield `TurnStarted(turn_num=N)`
- [ ] llm call 前 → yield `LLMRequested(model=..., tokens_in=...)`
- [ ] llm call 後 + parse 後 → yield `LLMResponded(content=..., tool_calls=[...], thinking=...)`
- [ ] tool execute 後 → yield `ToolCallCompleted(tool_name=..., result=..., is_error=...)`
- [ ] 確保 yield 順序與 02.md §SSE 期待一致（loop_start → turn_start → llm_request → llm_response → tool_call_request → tool_call_result → tool_call_completed → ... → loop_end）
- [ ] DoD：50.1 既有 7 個 loop unit test 仍 PASS（4 新 event 不破既有）+ 4 新 unit test 驗 emit 時機

### 2.5 agent_loop_worker.py — build_agent_loop_handler 工廠（90 min）
- [ ] Edit `backend/src/runtime/workers/agent_loop_worker.py`
- [ ] 加 `build_agent_loop_handler(*, chat_client, tool_registry, tool_executor, output_parser, system_prompt, sse_emit) -> TaskHandler`
- [ ] handler 內部：建 AgentLoopImpl → loop.run() 收 LoopEvent → 每個 event 呼叫 sse_emit callback
- [ ] 保留 `_default_handler` stub（DEPRECATED-IN: 53.1 + Modification History 紀錄）
- [ ] DoD：3 unit test PASS（factory 建 handler / sse_emit called per event / handler error 不洩漏 task）

### 2.6 router.py 接入 worker handler（60 min）
- [ ] Edit `backend/src/api/v1/chat/router.py` 用 `build_agent_loop_handler` 替換之前直接 loop.run()
- [ ] sse_emit callback 寫進 SSE response stream
- [ ] DoD：integration smoke 仍 PASS（router 用 handler factory 跑 echo demo）

### 2.7 Day 2 progress + commit（15 min）
- [ ] checklist 2.1-2.6 全 [x]
- [ ] progress.md Day 2 段
- [ ] commit：`feat(orchestrator-loop, sprint-50-2): 4 new LoopEvents + worker handler factory (Day 2)`
- [ ] commit checklist update

**Day 2 Total Plan**: ~6h / ~10 unit tests / 2 commits

---

## Day 3 — Frontend Skeleton（6h plan）

### 3.1 SSE backend → curl 驗證（15 min）
- [ ] 跑 backend：`cmd /c "cd /d <project>\backend && python -m uvicorn api.main:app --reload --port 8000"`
- [ ] curl test：`curl -N -X POST http://localhost:8000/api/v1/chat/ -H "Content-Type: application/json" -H "X-Tenant-Id: test" -d '{"message":"echo hello","mode":"echo_demo"}'`
- [ ] DoD：terminal 看到 7 個 SSE event 順序 + final `loop_end` event

### 3.2 frontend types.ts — LoopEvent 1:1 對應 02.md（45 min）
- [ ] 建 `frontend/src/features/chat_v2/types.ts`
- [ ] discriminated union 13 個 event types（per 02.md §SSE）
- [ ] additional UI types：`Message` / `ToolCallEntry` / `ChatSession` / `ChatMode`
- [ ] DoD：tsc --noEmit 通過

### 3.3 chatStore.ts — Zustand store（60 min）
- [ ] 建 `frontend/src/features/chat_v2/store/chatStore.ts`
- [ ] state: { sessionId, messages[], events[], status, error }
- [ ] actions: addMessage / mergeEvent / reset / setStatus
- [ ] mergeEvent 解構 LoopEvent 加入 messages（user / assistant / tool_call_card）
- [ ] DoD：3 vitest unit test PASS

### 3.4 chatService.ts — fetch + SSE consumer（60 min）
- [ ] 建 `frontend/src/features/chat_v2/services/chatService.ts`
- [ ] `streamChat(req: ChatRequest, onEvent: (ev) => void, signal: AbortSignal): Promise<void>` — 用 `fetch(...)` + `response.body.getReader()` + 解析 `event:` / `data:` lines
- [ ] DoD：mock fetch + assert onEvent called per event chunk

### 3.5 useLoopEventStream.ts — React hook（45 min）
- [ ] 建 `frontend/src/features/chat_v2/hooks/useLoopEventStream.ts`
- [ ] `useLoopEventStream(): { send: (msg) => void, status, error }`
- [ ] Wrap chatService.streamChat → 自動呼叫 chatStore.mergeEvent
- [ ] AbortController for cancellation
- [ ] DoD：4 vitest test（connect / receive / disconnect / error）

### 3.6 ChatLayout.tsx — 3-column placeholder（45 min）
- [ ] 建 `frontend/src/features/chat_v2/components/ChatLayout.tsx`
- [ ] 用 Tailwind grid 3 column：sidebar (placeholder) / main / inspector (placeholder)
- [ ] minimal — sidebar / inspector 內容只放「Coming in Phase 51+」
- [ ] DoD：頁面 render 不崩 + lint pass

### 3.7 pages/chat-v2/index.tsx 取代 placeholder（15 min）
- [ ] Edit `frontend/src/pages/chat-v2/index.tsx` import + render `<ChatLayout>`
- [ ] DoD：dev server 訪問 /chat-v2 看到 3-column layout

### 3.8 Day 3 progress + commit（15 min）
- [ ] checklist 3.1-3.7 全 [x]
- [ ] progress.md Day 3 段
- [ ] commit：`feat(frontend-page-chat-v2, sprint-50-2): types + store + service + hook + layout (Day 3)`
- [ ] commit checklist update

**Day 3 Total Plan**: ~6h / ~7 vitest tests / 2 commits

---

## Day 4 — Frontend Wiring + e2e（6h plan）

### 4.1 MessageList.tsx — 渲染 messages + thinking（90 min）
- [ ] 建 `frontend/src/features/chat_v2/components/MessageList.tsx`
- [ ] 從 chatStore.messages render：user / assistant text / thinking block (collapsed by default) / tool_call_card
- [ ] 自動 scroll-to-bottom on new message
- [ ] DoD：dev render 顯示 user msg + assistant + tool_call entry

### 4.2 ToolCallCard.tsx — 折疊 request/result 對（60 min）
- [ ] 建 `frontend/src/features/chat_v2/components/ToolCallCard.tsx`
- [ ] 顯示 tool_name / args (JSON pretty) / result (JSON pretty) / status badge (running / done / error)
- [ ] click to expand/collapse
- [ ] DoD：vitest test 驗 expand/collapse + error state render

### 4.3 InputBar.tsx — text + Send + mode toggle（45 min）
- [ ] 建 `frontend/src/features/chat_v2/components/InputBar.tsx`
- [ ] textarea + Send button + mode toggle (echo_demo / real_llm)
- [ ] disable send while loop running；Stop button when running 觸發 abort
- [ ] DoD：keyboard Enter / shift+Enter 行為正確

### 4.4 整合到 ChatLayout（15 min）
- [ ] Edit `ChatLayout.tsx` main column 加 `<MessageList /><InputBar />`
- [ ] DoD：頁面長相 OK + lint pass

### 4.5 e2e demo 手動測試（30 min）
- [ ] start backend + frontend dev servers
- [ ] 訪問 http://localhost:3005/chat-v2
- [ ] 輸入 "echo hello world"
- [ ] DoD：看到 user msg → thinking → tool_call_card (echo_tool / args / result) → assistant final answer "hello world"

### 4.6 integration test — backend e2e（60 min）
- [ ] 建 `backend/tests/integration/api/test_chat_e2e.py`
- [ ] FastAPI test client：POST /chat with echo_demo → assert SSE 7 events 順序 + final content
- [ ] cancellation test：mid-flight abort → session_registry 清理
- [ ] DoD：2 integration test PASS

### 4.7 frontend integration test — useLoopEventStream + chatStore（30 min）
- [ ] vitest：mock fetch streaming → useLoopEventStream → chatStore.messages 變化
- [ ] DoD：1 vitest integration PASS

### 4.8 Day 4 progress + commit（30 min）
- [ ] checklist 4.1-4.7 全 [x]
- [ ] progress.md Day 4 段
- [ ] commit：`feat(frontend-page-chat-v2, sprint-50-2): MessageList + ToolCallCard + InputBar + e2e (Day 4)`
- [ ] commit checklist update

**Day 4 Total Plan**: ~6h / ~3 integration tests + ~5 vitest / 2 commits

---

## Day 5 — Real LLM + Closeout（4h plan）

### 5.1 Real Azure OpenAI demo（用戶 trigger，AI 助手 wiring）（45 min）
- [ ] 確認 `.env` 含 `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_API_KEY` / `AZURE_OPENAI_DEPLOYMENT_NAME` / `AZURE_OPENAI_API_VERSION`
- [ ] 啟動 backend + frontend
- [ ] /chat-v2 切 mode = real_llm，輸入「請呼叫 echo 工具，內容是 hello GPT」
- [ ] DoD：看到 LLM 真實 thinking + 真實 tool_call → echo result → final answer

### 5.2 quality gates final check（30 min）
- [ ] backend: `python -m pytest backend/tests` PASS
- [ ] backend: `python -m mypy backend/src --strict`
- [ ] backend: 5 V2 lints OK
- [ ] backend: LLM SDK leak grep = 0（agent_harness + business_domain）
- [ ] backend: alembic from-zero cycle ✅（無新 migration 預期）
- [ ] frontend: `npm run lint` + `npm run build` + `npm run test`
- [ ] DoD：截圖貼進 retrospective.md

### 5.3 retrospective.md（45 min）
- [ ] 建 `docs/03-implementation/agent-harness-execution/phase-50/sprint-50-2/retrospective.md`
- [ ] sections：Outcome / Estimate accuracy / Quality gates / Did well ≥3 / Improve next sprint ≥3 / Action items table / Lessons learned 3 / 50.1 retro carry-over status / 50.2 carry-forward / Cumulative branch state
- [ ] DoD：211+ 行 / 結構對齊 50.1 retrospective.md

### 5.4 Phase 50 README 收尾（30 min）
- [ ] Edit `phase-50-loop-core/README.md`
- [ ] Sprint 50.2 標 ✅ DONE 2026-05-XX
- [ ] Phase 進度 1/2 → 2/2 = 100%
- [ ] 範疇成熟度更新：Cat 1 Level 2 → 3，Cat 6 Level 3 → 4
- [ ] Last Updated 改 2026-05-XX
- [ ] DoD：file render OK / 無 broken link

### 5.5 MEMORY.md + project_phase50_loop_core.md 同步（15 min）
- [ ] Edit `memory/project_phase50_loop_core.md` 加 50.2 outputs section
- [ ] Edit `MEMORY.md` index entry 50 改 description
- [ ] DoD：grep 50.2 OK

### 5.6 final closeout commit（15 min）
- [ ] commit：`docs(sprint-50-2, phase-50): closeout — Sprint 50.2 ✅ DONE / Phase 50 2/2 = 100% (Day 5)`
- [ ] DoD：working tree clean except user IDE / V2-AUDIT-* 平行文件

**Day 5 Total Plan**: ~4h / 1 commit

---

## Cumulative branch state target at closeout

```
feature/phase-50-sprint-2-api-frontend (10 commits)
├── (Day 0) docs(sprint-50-2): plan + checklist
├── (Day 0) docs(sprint-50-2): Phase 50 README in-progress
├── (Day 0) fix(events, sprint-50-2): CARRY-001 + CARRY-002
├── (Day 1) feat(api, sprint-50-2): chat router + SSE + session_registry
├── (Day 1) docs(sprint-50-2): Day 1 progress + checklist [x]
├── (Day 2) feat(orchestrator-loop, sprint-50-2): 4 new LoopEvents + worker handler
├── (Day 2) docs(sprint-50-2): Day 2 progress + checklist [x]
├── (Day 3) feat(frontend-page-chat-v2, sprint-50-2): types + store + service + hook + layout
├── (Day 3) docs(sprint-50-2): Day 3 progress + checklist [x]
├── (Day 4) feat(frontend-page-chat-v2, sprint-50-2): MessageList + ToolCallCard + InputBar + e2e
├── (Day 4) docs(sprint-50-2): Day 4 progress + checklist [x]
└── (Day 5) docs(sprint-50-2, phase-50): closeout — Sprint 50.2 ✅ DONE
```

Branch ~56 commits ahead of main（46 from 50.1 + 10 from 50.2）。

---

## Sacred Rule 自檢

- ☐ 沒預寫多個未來 sprint plan（51.x plan + checklist 都未寫，符合 rolling planning）
- ☐ 沒跳過 plan/checklist 直接 code（plan + checklist Day 0 之前完成）
- ☐ 沒刪除未勾選的 [ ] 項目（所有變動只能 [ ]→[x] 或 🚧+reason）
- ☐ retrospective.md 不寫 51.x 具體 task（只列 50.2 carry-forward）

---

**Checklist version**：1.0（2026-04-30）
**Reference**：[`sprint-50-1-checklist.md`](./sprint-50-1-checklist.md) 結構對齊
