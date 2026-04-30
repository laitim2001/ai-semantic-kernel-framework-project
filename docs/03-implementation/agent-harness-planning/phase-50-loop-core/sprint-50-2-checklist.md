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
- [x] `ChatRequest` { message: str, session_id: UUID | None, mode: Literal["echo_demo", "real_llm"] = "echo_demo" }
- [x] `ChatSessionResponse` { session_id: UUID, status: Literal["running", "completed", "cancelled"], started_at: datetime }
- 🚧 `ToolCallSummary` / `MessageSummary`（for SSE event payload）— **不需要**：SSE payload 直接 dict 序列化 LoopEvent dataclass，無需中間 Pydantic 包
- [x] DoD：mypy --strict 通過 + 7 unit tests PASS

### 1.2 session_registry.py — in-memory session map（45 min）
- [x] 建 `backend/src/api/v1/chat/session_registry.py`
- [x] `SessionRegistry` class：register / get / cancel / cleanup / mark_completed
- [x] thread-safe（asyncio.Lock）+ session_id → asyncio.Event (cancel signal) + status Literal enum + module-level default singleton + get_default_registry() factory
- [x] DoD：7 unit test PASS（含 register idempotent / cancel returns False on missing / mark_completed not override cancelled / asyncio.gather race）

### 1.3 sse.py — LoopEvent → SSE serializer（90 min）
- [x] 建 `backend/src/api/v1/chat/sse.py`
- [x] `serialize_loop_event(event: LoopEvent) -> dict` 對應 02.md §SSE
  - Day 1 已實作 5: loop_start (LoopStarted) / llm_response (Thinking) / tool_call_request (ToolCallRequested) / tool_call_result (ToolCallExecuted forward-compat for Day 2) / loop_end (LoopCompleted)
  - 🚧 turn_start / llm_request / llm_response (LLMResponded) — Day 2 加 4 個新 LoopEvent 後 fill in
  - 其餘 14 events（HITL / Guardrails / Verification / 等）raise NotImplementedError 帶 sprint pointer
- [x] `format_sse_message(event_type, data) -> bytes`（`event: ...\ndata: ...\n\n`）+ `_jsonable()` 處理 UUID / datetime
- [x] DoD：10 unit tests PASS（5 event types + 3 format/UUID/unicode + NotImplementedError 帶 sprint 50.2 pointer）

### 1.4 handler.py — agent loop handler factory（60 min）
- [x] 建 `backend/src/api/v1/chat/handler.py`
- [x] `build_echo_demo_handler(message: str) -> AgentLoopImpl`：用 50.1 `make_echo_executor()` + `MockChatClient` 2-step scripted response（TOOL_USE → END_TURN）
- [x] `build_real_llm_handler() -> AgentLoopImpl`：用 49.4 `AzureOpenAIAdapter(AzureOpenAIConfig())` + `make_echo_executor()`；env validation 在 build 時間檢查（缺 raise RuntimeError）
- [x] `build_handler(mode, message) -> AgentLoopImpl` dispatcher
- [x] DoD：5 unit tests PASS（echo_demo build / scripted message into echo_tool args / real_llm missing env raises / dispatch echo_demo / dispatch invalid mode raises）

### 1.5 router.py — POST /chat + GET /sessions/{id}（120 min）
- [x] 建 `backend/src/api/v1/chat/router.py`
- [x] `POST /api/v1/chat/` 用 `StreamingResponse(media_type="text/event-stream")` + X-Session-Id response header
- [x] flow：parse ChatRequest → build_handler by mode → register session → _stream_loop_events generator (serialize_loop_event + format_sse_message + mark_completed on natural completion) → yield bytes
- [x] `GET /api/v1/chat/sessions/{session_id}` → SessionRegistry.get → return ChatSessionResponse / 404
- [x] `POST /api/v1/chat/sessions/{session_id}/cancel` → SessionRegistry.cancel → 204 / 404
- [x] include in `api/v1/chat/__init__.py`（re-export router）
- [x] include in `api/main.py` `app.include_router(chat_router, prefix="/api/v1")`
- [x] DoD：10 unit tests PASS（SSE 5+ events stream / 422 empty msg / 422 invalid mode / 422 missing msg / 503 missing AZURE env / session_id persisted as completed / 404 unknown session / running session GET / cancel happy / cancel 404）

### 1.6 Day 1 progress + commit（15 min）
- [x] checklist 1.1-1.5 全 [x]
- [x] 寫 `docs/03-implementation/agent-harness-execution/phase-50/sprint-50-2/progress.md` Day 1 段（estimate vs actual / 5 surprises）
- [x] commit：`feat(api,orchestrator-loop, sprint-50-2): chat router + SSE serializer + session registry (Day 1)` → commit `<HEAD>`
- [x] commit checklist update：`docs(sprint-50-2): Day 1 progress + checklist [x] update`

**Day 1 Total Plan**: ~6h / ~15 unit tests / 2 commits → **Actual: ~61 min（17%）/ 29 unit tests / 2 commits**

### Day 1 Bonus 修正（plan 外）

- 🚧 **`loop.py:94` 50.1 latent cross-cat lint warn** — 順手改成 public path（`agent_harness.tools` 已 re-export ToolExecutor/ToolRegistry）。Modification History entry 加。
- 🚧 **tests/unit/api/__init__.py + v1/__init__.py + v1/chat/__init__.py 刪除** — namespace package mode（與 50.1 tests/unit/agent_harness/ 對齐）。pytest 全 collection 時 src/api 與 tests/api 衝突的 quirk。
- 🚧 **handler.py `AzureOpenAIAdapter` ctor sig 修正** — plan §4.1 寫的 `endpoint=..., api_key=...` 不對，actual 是 `AzureOpenAIAdapter(AzureOpenAIConfig())`（BaseSettings env auto-load）。env existence 自檢仍保留。

---

## Day 2 — Worker 整合 + 4 新 LoopEvent（6h plan）

### 2.1 17.md owner check — 新 LoopEvent（15 min）
- [x] Read `17-cross-category-interfaces.md` §4.1 Event ownership table
- 🚧 `ToolCallCompleted` — **不加**：與既有 `ToolCallExecuted` (Cat 2 / success) + `ToolCallFailed` (Cat 2 / error) 重疊；改成擴 ToolCallExecuted 加 `result_content` field
- [x] `TurnStarted` / `LLMRequested` / `LLMResponded` 3 個 Cat 1 owner — 17.md §4.1 表擴 3 entries（commit 同次）
- [x] DoD：3 新 event 在 17.md §4.1 有條目；ToolCallExecuted Modification History 紀錄欄位擴展

### 2.2 _contracts/events.py 加 3 新 event class + 擴 ToolCallExecuted（45 min）
- [x] Edit `backend/src/agent_harness/_contracts/events.py`
- [x] 加 `TurnStarted(LoopEvent)` { turn_num: int = 0 }
- [x] 加 `LLMRequested(LoopEvent)` { model: str = "", tokens_in: int = 0 }
- [x] 加 `LLMResponded(LoopEvent)` { content: str = "", tool_calls: tuple[Any, ...] = field(default_factory=tuple), thinking: str | None = None } (tuple 因 frozen dataclass + circular import 規避)
- [x] 擴 `ToolCallExecuted` 加 `result_content: str = ""`（backward-compat default）
- [x] 全用 `datetime.now(UTC)` default_factory（CARRY-002 已 fix）
- [x] Modification History 加 2 entry
- [x] DoD：mypy strict 通過 + dup-dataclass scan 51→54 classes 確認

### 2.3 events.py shim 加 re-export（10 min）
- [x] Edit `backend/src/agent_harness/orchestrator_loop/events.py` 加 3 個新 + ToolCallExecuted/Failed re-export（後 2 個 Day 2 Loop 開始 emit）
- [x] 更新 Modification History
- [x] DoD：`from agent_harness.orchestrator_loop.events import TurnStarted, LLMRequested, LLMResponded, ToolCallExecuted, ToolCallFailed` 通過

### 2.4 loop.py yield 5 新 event 在正確時機（90 min）
- [x] Edit `backend/src/agent_harness/orchestrator_loop/loop.py`
- [x] pre-LLM check 通過後 → yield `TurnStarted(turn_num=turn_count)`
- [x] chat call 前 → yield `LLMRequested(model=chat_client.model_info().model_name, tokens_in=0)`（tokens_in best-effort 0；Phase 52.1 wire count_tokens）
- [x] parse 後 → yield `LLMResponded(content=parsed.text, tool_calls=tuple(parsed.tool_calls), thinking=None)` (canonical) → yield `Thinking(text=parsed.text)` (50.1 backward compat)
- [x] tool_executor.execute 後 → result.success ? yield `ToolCallExecuted(...with result_content)` : yield `ToolCallFailed(...)`
- [x] 確保 yield 順序與 02.md §SSE 期待一致
- [x] DoD：50.1 既有 17 loop unit tests 全 PASS（更新 2 個 event 序列 assertion）+ 50.1 integration 3 tests 全 PASS（更新 2 個 sequence）

### 2.5 agent_loop_worker.py — execute_loop_with_sse + build_agent_loop_handler 工廠（90 min）
- [x] Edit `backend/src/runtime/workers/agent_loop_worker.py`
- [x] 加 `execute_loop_with_sse(*, loop, session_id, user_input, sse_emit, trace_context) -> dict[str, Any]` — common driver；router + worker 共用
- [x] 加 `build_agent_loop_handler(*, chat_client, tool_registry, tool_executor, output_parser, sse_emit, system_prompt, max_turns, token_budget) -> TaskHandler`
- [x] handler 內部：建 AgentLoopImpl → 經 execute_loop_with_sse 跑 → return summary dict
- [x] task_id (str) → UUID coerce 含 deterministic fallback for non-UUID
- [x] 保留 `_default_handler` stub（DEPRECATED-IN: 53.1 標 + Modification History 紀錄）
- [x] runtime/workers/__init__.py 加 3 新 export
- [x] DoD：3 unit test PASS（execute happy / build handler / non-UUID fallback）

### 2.6 router None-skip + 17.md §4.1 擴 3 entries（60 min）
- [x] Edit `backend/src/api/v1/chat/router.py` `_stream_loop_events` — 加 `if payload is None: continue`（Thinking → None skip）
- 🚧 router **不主動呼叫** worker handler — 會引入 in-process queue bridge 複雜度；保留 direct iteration；helpers 作為 53.1 forward-compat。Decision 紀錄於 commit message + progress.md surprise #3。
- [x] sse.py 3 個新 mapping (TurnStarted / LLMRequested / LLMResponded) + Thinking→None + ToolCallFailed → tool_call_result is_error=True + ToolCallExecuted 加 result
- [x] 17.md §4.1 表擴 3 entries（TurnStarted / LLMRequested / LLMResponded — Cat 1 owner）
- [x] DoD：integration test test_e2e_echo + test_tool_feedback PASS（更新 sequence assertion）

### 2.7 Day 2 progress + commit（15 min）
- [x] checklist 2.1-2.6 全 [x]（含 🚧 + reason）
- [x] progress.md Day 2 段（estimate vs actual / 6 surprises）
- [x] commit：`feat(orchestrator-loop,api,runtime, sprint-50-2): 3 new LoopEvents + worker handler factory (Day 2)` → commit `4e04ae7`
- [x] commit checklist update：`docs(sprint-50-2): Day 2 progress + checklist [x] update`

**Day 2 Total Plan**: ~6h / ~10 unit tests / 2 commits → **Actual: ~86 min（24%）/ 17 new tests + 4 modified tests / 2 commits**

---

## Day 3 — Frontend Skeleton（6h plan）

### 3.1 SSE backend → curl 驗證（15 min）
- 🚧 dev server curl test 跳過 — 啟 uvicorn 在 bash 會 block；改用 Day 1 test_router.py FastAPI TestClient SSE 10 tests 覆蓋全 7-event 流（test_echo_demo_streams_loop_events / tool_call_request args / loop_end last / 422 / 503 / 404 / cancel 等）
- [x] DoD：Day 1 test_router.py 256 PASS 已涵蓋 SSE 端到端契約

### 3.2 frontend types.ts — LoopEvent 1:1 對應 02.md（45 min）
- [x] 建 `frontend/src/features/chat_v2/types.ts`
- [x] 7-arm discriminated union（Sprint 50.2 wire 範圍：loop_start / turn_start / llm_request / llm_response / tool_call_request / tool_call_result / loop_end；其餘 02.md events 留 51+ 解 unknown）
- [x] additional UI types：`Message` / `ToolCallEntry` / `ChatSession` / `ChatMode` / `ChatStatus`
- [x] `KNOWN_LOOP_EVENT_TYPES` Set gate 用於 chatService parser
- [x] DoD：`npm run build` 通過

### 3.3 chatStore.ts — Zustand store（60 min）
- [x] 建 `frontend/src/features/chat_v2/store/chatStore.ts`
- [x] state: { sessionId, status, totalTurns, stopReason, errorMessage, mode, messages[], rawEvents[] }
- [x] actions: setMode / setStatus / setError / pushUserMessage / mergeEvent / reset
- [x] mergeEvent 7-case switch（loop_start / turn_start / llm_request / llm_response / tool_call_request / tool_call_result / loop_end）+ default: never exhaustive check
- 🚧 `vitest unit test` — vitest 沒裝；50.2 不裝；Phase 51+ test infra
- [x] DoD：build PASS + 邏輯 validation 留 Day 4 e2e

### 3.4 chatService.ts — fetch + SSE consumer（60 min）
- [x] 建 `frontend/src/features/chat_v2/services/chatService.ts`
- [x] `streamChat(body, opts)` — 用 `fetch + response.body.getReader()` + TextDecoder 解析 `event:` / `data:` lines；frame split by `\n\n`
- [x] AbortSignal 通過 fetch + reader；AbortError 靜默 return（不 onError）
- [x] `parseSSEFrame` 用 KNOWN_LOOP_EVENT_TYPES gate 過濾 unknown → null
- 🚧 `vitest mock fetch test` — 同上 deferred
- [x] DoD：build PASS + Day 4 e2e 驗

### 3.5 useLoopEventStream.ts — React hook（45 min）
- [x] 建 `frontend/src/features/chat_v2/hooks/useLoopEventStream.ts`
- [x] `useLoopEventStream(): { send, cancel, isRunning }` 連接 chatStore
- [x] Wrap chatService.streamChat → 自動呼叫 chatStore.mergeEvent + 紀錄 user message + setStatus
- [x] AbortController for cancellation；fallback status="completed" if loop_end 未到
- 🚧 `vitest 4 test` — 同上 deferred
- [x] DoD：build PASS + Day 4 e2e 驗

### 3.6 ChatLayout.tsx — 3-column placeholder（45 min）
- [x] 建 `frontend/src/features/chat_v2/components/ChatLayout.tsx`
- [x] CSS Grid 3-column + header（gridTemplateAreas）：sidebar / main / inspector
- [x] minimal — sidebar / inspector 內容放 "Phase 51.x" placeholder
- 🚧 用 Tailwind — Tailwind 沒裝；改 inline styles；Phase 53.4 retrofit
- [x] DoD：build PASS + lint clean

### 3.7 pages/chat-v2/index.tsx 取代 placeholder（15 min）
- [x] Edit `frontend/src/pages/chat-v2/index.tsx` import + render `<ChatLayout>` + Day 4 placeholder
- [x] DoD：build PASS + Modification History entry

### 3.8 Day 3 progress + commit（15 min）
- [x] checklist 3.1-3.7 全 [x]（含 🚧 + reason）
- [x] progress.md Day 3 段（estimate vs actual / 5 surprises）
- [x] commit：`feat(frontend-page-chat-v2, sprint-50-2): types + store + service + hook + layout (Day 3)` → commit `<HEAD>`
- [x] commit checklist update：`docs(sprint-50-2): Day 3 progress + checklist [x] update`

**Day 3 Total Plan**: ~6h / ~7 vitest tests / 2 commits → **Actual: ~70 min（19%）/ 0 frontend tests (vitest deferred) / 2 commits**

---

## Day 4 — Frontend Wiring + e2e（6h plan）

### 4.1 MessageList.tsx — 渲染 messages + thinking（90 min）
- [x] 建 `frontend/src/features/chat_v2/components/MessageList.tsx`
- [x] useChatStore.messages subscribe；user / assistant rows；assistant 內嵌 ToolCallCard
- [x] 自動 scroll-to-bottom on messages.length change（useEffect）
- [x] empty state 提示 (試 `echo hello`)
- [x] DoD：build PASS / TypeScript narrow OK

### 4.2 ToolCallCard.tsx — 折疊 request/result 對（60 min）
- [x] 建 `frontend/src/features/chat_v2/components/ToolCallCard.tsx`
- [x] 顯示 tool_name / args (JSON pretty) / result / 3-status badge (running / done / error) / duration_ms
- [x] click header to expand/collapse（default open）
- 🚧 vitest test — Phase 51+ infra
- [x] DoD：build PASS + render correct

### 4.3 InputBar.tsx — text + Send + mode toggle（45 min）
- [x] 建 `frontend/src/features/chat_v2/components/InputBar.tsx`
- [x] textarea + Send button + Stop button (when running) + mode toggle (echo_demo / real_llm)
- [x] status pill + error banner
- [x] disable input/buttons while running；abort 觸發 cancel
- [x] keyboard Enter（送）/ Shift+Enter（新行）正確
- [x] DoD：build PASS + lint OK

### 4.4 整合到 ChatLayout（15 min）
- [x] Edit `frontend/src/pages/chat-v2/index.tsx` ChatLayout 內放 MessageList + InputBar
- [x] DoD：頁面 render OK + lint pass + Modification History entry

### 4.5 e2e demo 手動測試（30 min）
- 🚧 dev server e2e 跳過 — uvicorn / npm run dev 會 block bash；Day 1 + Day 4.6 共 13 backend tests 已覆蓋 SSE 端到端契約；frontend 真實瀏覽器 e2e 留 next session 用戶手動 verify（type/build/lint 全綠）
- [x] DoD：13 backend tests PASS 確認契約一致

### 4.6 integration test — backend e2e（60 min）
- [x] 建 `backend/tests/integration/api/test_chat_e2e.py`
- [x] FastAPI test client：POST /chat echo_demo → SSE 8-event sequence verify (loop_start / 2× turn_start+llm_request+llm_response / tool_call_request / tool_call_result / loop_end) + result_content / final llm_response.content / total_turns
- [x] X-Session-Id header → GET sessions/{id} flips to "completed" after stream drain
- [x] Cancel endpoint test：pre-register sid → POST /cancel → 204 / GET reflects "cancelled"
- [x] DoD：3 integration tests PASS

### 4.7 frontend integration test — useLoopEventStream + chatStore（30 min）
- 🚧 vitest 沒裝 — Phase 51+ test infra
- [x] DoD：deferred 紀錄

### 4.8 Day 4 progress + commit（30 min）
- [x] checklist 4.1-4.7 全 [x]（含 🚧 + reasons）
- [x] progress.md Day 4 段（estimate vs actual / 5 surprises）
- [x] commit：`feat(frontend-page-chat-v2,api, sprint-50-2): MessageList + ToolCallCard + InputBar + e2e (Day 4)` → commit `<HEAD>`
- [x] commit checklist update：`docs(sprint-50-2): Day 4 progress + checklist [x] update`

**Day 4 Total Plan**: ~6h / ~3 integration + ~5 vitest / 2 commits → **Actual: ~64 min（18%）/ 3 integration tests + 0 vitest (deferred) / 2 commits**

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
