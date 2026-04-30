# Sprint 50.1 Plan — Loop Core（範疇 1 + 範疇 6）

**Sprint**：50.1
**Phase**：50（Loop Core，**最重要的 Phase**）
**主題**：Orchestrator Loop（範疇 1）+ Output Parser（範疇 6）核心實作
**預估**：1 週 / 5 day / **28 SP**
**Branch**（待建立）：`feature/phase-50-sprint-1-loop-core`
**Status**：🔵 PLANNED — 等用戶 approve 開始 Day 1
**Owner**：AI 助手 + 用戶
**Plan Created**：2026-04-29

---

## Sprint Goal

> **跑通第一個真正的 TAO loop**：實作範疇 1 `AgentLoop.run() -> AsyncIterator[LoopEvent]` 的 while-true 主迴圈、由中性化 `StopReason` enum 驅動退出、tool 結果以 user message 回注；範疇 6 `OutputParser.parse(response) -> ParsedOutput` 完整 native tool_calls 解析 + classifier。**端到端**：傳一個訊息給 `AgentLoop.run()` → 用 `MockChatClient` + `echo_tool` → AsyncIterator yield 完整事件流 → 收到答案。**不接 API**（API 整合是 50.2 工作；50.1 純 backend agent_harness/ 內單元 + 整合 test）。

---

## 前置條件（49.4 closeout 已確認 unblocked）

- ✅ `_contracts/chat.py`（Message / ChatResponse / StopReason / ToolCall）— 49.1 Day 4
- ✅ `_contracts/events.py`（LoopEvent base + 9 子類 stub）— 49.1 Day 4
- ✅ `_contracts/state.py`（LoopState / TransientState / DurableState）— 49.1 Day 4
- ✅ `_contracts/tools.py`（ToolSpec / ToolCall / ToolResult / ConcurrencyPolicy）— 49.1 Day 4
- ✅ `agent_harness/orchestrator_loop/_abc.py`（AgentLoop ABC stub）— 49.1
- ✅ `agent_harness/output_parser/_abc.py`（OutputParser ABC stub）— 49.1
- ✅ `adapters/_base/chat_client.py` + `MockChatClient`（49.4 Day 1，41 contract tests）
- ✅ `agent_harness/observability/{tracer,metrics}.py`（49.4 Day 3）
- ✅ pytest infra + black/isort/mypy/flake8 + 4 V2 lint rules（49.4 Day 4）
- ✅ `runtime/workers/agent_loop_worker.py` stub + `TaskHandler` signature（49.4 Day 2）

---

## User Stories

### Story 50.1-1：範疇 6 OutputParser 完整實作

**作為** Agent harness 主迴圈
**我希望** 有一個能從中性 `ChatResponse` 判斷接下來要做什麼（執行工具 / 結束 / 切換 agent）的 parser
**以便** 我能根據 LLM 輸出做正確分支，不需要每個 caller 重複寫分類邏輯

**驗收**：
- `OutputParser.parse(response) -> ParsedOutput` 可從 `ChatResponse` 萃取 `tool_calls` / `final_text` / `handoff_request`
- `classify_output(response) -> OutputType{TOOL_USE, FINAL, HANDOFF}` 三向分類
- `StopReason` enum 中性化 mapping 100% 精確（per-provider unit test：MockChatClient 模擬 4 種 stop_reason）
- 禁止任何 regex 文本解析作為主路徑（lint scan + AP-1 check）
- p95 < 5ms（不含 streaming 等待）

### Story 50.1-2：範疇 1 AgentLoop 主迴圈

**作為** AI agent 平台核心
**我希望** 有一個 `AgentLoop` 真正的 TAO 迴圈：assemble prompt → call LLM → parse output → execute tools → feed results back → repeat
**以便** 平台具備真正的 autonomous reasoning，不再是 V1 的「Pipeline 偽裝 Loop」（AP-1）

**驗收**：
- `AgentLoop.run(messages, tools, system_prompt, max_turns, token_budget, ...) -> AsyncIterator[LoopEvent]`
- 真正使用 `while True` 結構（非 `for step in steps:`）
- 由 `StopReason.END_TURN` 退出（中性化 enum）
- Tool 結果以 `Message(role="tool", tool_call_id=..., content=...)` 形式回注 messages
- 支援 `asyncio.CancelledError`，in-flight tool calls 正確釋放
- AP-1 lint rule 零違反

### Story 50.1-3：Termination 4 類終止條件

**作為** AgentLoop 安全保護
**我希望** Loop 能在 4 種情況下安全退出（不只是 stop_reason）
**以便** 即使 LLM 不收斂，平台也能在合理 budget 內結束

**驗收**：
- `termination.py` 提供 4 個 terminator function：
  1. `should_terminate_by_stop_reason(response) -> bool`
  2. `should_terminate_by_turns(turn_count, max_turns) -> bool`
  3. `should_terminate_by_tokens(tokens_used, token_budget) -> bool`
  4. `should_terminate_by_cancellation(state) -> bool`（檢查 asyncio.CancelledError sentinel）
- 每個 terminator 有獨立 unit test
- `TripwireTerminator` / `ErrorTerminator` 介面預留（範疇 9 / 8 在 53.x 接入）

### Story 50.1-4：Loop Events 完整事件流

**作為** Loop 觀察者（範疇 12 / SSE handler / 測試）
**我希望** Loop 每個關鍵節點 yield 對應 LoopEvent 子類
**以便** 我能即時觀察 agent 推理過程（Phase 50.2 接 SSE）

**驗收**：
- `events.py` 從 `_contracts/events.py` re-export base + 在 orchestrator_loop/ 內 own 5 個必須事件：
  - `LoopStarted`（loop 開始）
  - `Thinking`（含 partial token emit；50.1 用 finalized text，streaming token 留 50.2）
  - `ToolCallRequested`（output parser 解析出 tool_calls 後）
  - `LoopCompleted`（loop 終止）
- `ToolCallExecuted` / `ToolCallFailed` 由範疇 2 owner emit（50.1 by in-memory ToolRegistry stub）
- 每個 event 含 `trace_context`（範疇 12 自動注入；NoOpTracer fallback）
- `AsyncIterator[LoopEvent]` 真實 yield（非 sync callback；AP-1 變體 lint check）

### Story 50.1-5：In-Memory ToolRegistry + echo_tool（測試專用）

**作為** 50.1 端到端測試
**我希望** 有最簡 ToolRegistry + 一個 echo_tool 能跑通 TAO loop
**以便** 證明 Loop 能正確收 tool_calls → execute → 回注 → 繼續推理

**驗收**：
- `agent_harness/tools/_inmemory_registry.py`（**只供 50.1 / 50.2 使用**；51.1 真正範疇 2 上線後 deprecate）
- `echo_tool(text: str) -> str`（直接 return text；ToolSpec 完整定義）
- 1 個 read_only_parallel ConcurrencyPolicy
- ToolRegistry 對齐範疇 2 ABC 簽名（`register()` / `get()` / `list()`）但 in-memory backend
- 整合 49.4 NoOpTracer 埋點（`tool_execution_duration_seconds` metric emit）

### Story 50.1-6：第一個端到端整合測試

**作為** Sprint 50.1 驗收
**我希望** 一個 e2e 測試：用戶 message → AgentLoop.run() → MockChatClient yield tool_call → echo_tool execute → MockChatClient yield END_TURN → 收到答案
**以便** 證明 Phase 50 Sprint 50.1 真實落地，不是 Potemkin Feature（AP-4）

**驗收**：
- `tests/integration/orchestrator_loop/test_e2e_echo.py`
  - 注入 MockChatClient（pre-programmed 2-turn response：1st turn tool_use echo, 2nd turn end_turn with text）
  - 注入 InMemoryToolRegistry + echo_tool
  - `async for event in loop.run(...)` 收集 events
  - 斷言：events 序列含 `LoopStarted` → `Thinking` → `ToolCallRequested` → `ToolCallExecuted`（by registry stub）→ `Thinking` → `LoopCompleted`
  - 斷言：最終 message 含 echo 結果
  - 斷言：turn_count == 2，stop_reason == END_TURN
- mypy strict 0 issues
- 4 V2 lint 全 pass（特別 AP-1 / sync-callback / cross-category-import）

---

## 範疇歸屬（11+1）

| 範疇 | Sprint 50.1 工作量 |
|------|--------------------|
| **1. Orchestrator Loop** | 主要：loop.py / events.py / termination.py 核心實作 |
| **6. Output Parser** | 主要：parser.py / classifier.py 核心實作 |
| 2. Tool Layer | 部分：in-memory registry + echo_tool（**stub**，51.1 完整實作會 supersede） |
| 12. Observability | 滲透：所有 5 處埋點（loop turn / tool exec / output parse / event emit / cancellation） |
| 7. State Mgmt | 部分：用 49.1 _contracts/state.py 的 TransientState 即可（**完整 Checkpointer** 在 53.1） |

> **不在範圍**：範疇 3 / 4 / 5 / 8 / 9 / 10 / 11（後續 phase 51-54）。50.1 純粹 Loop + Parser 跑通骨架。

---

## Day-by-Day 計劃

### Day 1（2026-04-30，估 6h）— Output Parser 核心 + StopReason 完善

**任務 1.1（90 min）**：`output_parser/parser.py`
- `OutputParser` 具體實作（從 49.1 _abc.py 衍生）
- `parse(response: ChatResponse) -> ParsedOutput`：萃取 `tool_calls` + `final_text` + `handoff_request`
- `ParsedOutput` dataclass 定義（在 output_parser/types.py）

**任務 1.2（60 min）**：`output_parser/classifier.py`
- `classify_output(response) -> OutputType{TOOL_USE, FINAL, HANDOFF}`
- 邏輯：tool_calls 非空 → TOOL_USE；handoff_request 非空 → HANDOFF；否則 → FINAL
- 與 parser 解耦（caller 可獨立呼叫）

**任務 1.3（90 min）**：StopReason mapping 完整 + tests
- `_contracts/chat.py` 確認 StopReason enum 完整（END_TURN / TOOL_USE / MAX_TOKENS / SAFETY_REFUSAL / PROVIDER_ERROR）
- Adapters/_base 已有；Mock 補：MockChatClient 支援 inject 4 種 stop_reason 模擬
- 12 個 unit tests（4 stop_reason × 3 場景）

**任務 1.4（60 min）**：parser + classifier 單元測試（~12 tests）
- 5 case：tool_calls / final_text / handoff / 空 / 混合
- 1 perf test：p95 < 5ms 1k 次 parse

**Day 1 commit**：`feat(output-parser, sprint-50-1): OutputParser + classifier + StopReason mapping (Day 1)`

---

### Day 2（2026-05-01，估 6h）— AgentLoop 主迴圈 while-true + termination

**任務 2.1（120 min）**：`orchestrator_loop/termination.py`
- 4 個 terminator function（stop_reason / turns / tokens / cancellation）
- `TerminationReason` enum（記錄哪個 terminator 觸發；feed into LoopCompleted event）
- `TripwireTerminator` ABC stub（範疇 9 在 53.3 接入）
- 8 unit tests（4 terminator × 2 scenarios）

**任務 2.2（180 min）**：`orchestrator_loop/loop.py`
- `AgentLoopImpl(AgentLoop)` 具體實作
- `run()` async generator：
  ```python
  while True:
      check terminators (max_turns / tokens)
      yield LoopStarted (only first iteration)
      response = await chat_client.chat(messages, tools, ...)
      yield Thinking(response.content)
      parsed = output_parser.parse(response)
      output_type = classify_output(response)
      if output_type == FINAL:
          yield LoopCompleted(reason=END_TURN)
          break
      elif output_type == TOOL_USE:
          for tc in parsed.tool_calls:
              yield ToolCallRequested(tc)
              result = await tool_registry.execute(tc)
              messages.append(Message(role="tool", tool_call_id=tc.id, content=result))
          turn_count += 1
          continue
  ```
- Cancellation 處理（try/except `asyncio.CancelledError` → 釋放 in-flight + raise）
- Tracer span / metrics 埋點（49.4 NoOpTracer fallback）

**任務 2.3（60 min）**：MockChatClient 增強（49.4 已建）
- 增加 `injectable_responses_sequence`：依 turn_count 返回不同 response
- 4 unit tests（單 turn / 多 turn / cancellation / max_turns 觸發）

**Day 2 commit**：`feat(orchestrator-loop, sprint-50-1): AgentLoop while-true main loop + 4 terminators (Day 2)`

---

### Day 3（2026-05-02，估 6h）— Loop Events + tool 結果回注 + AP-1 / sync-callback lint

**任務 3.1（90 min）**：`orchestrator_loop/events.py`
- 從 `_contracts/events.py` re-export base + 5 必須事件
- 在 orchestrator_loop/ 範疇 own 的事件補完欄位（per 17.md §4.1 表格）
- `LoopStarted` / `Thinking` / `LoopCompleted` 是範疇 1 owner
- `ToolCallRequested` 由 output_parser 解析後 emit（owner 範疇 6）— 確認 owner 標註

**任務 3.2（60 min）**：tool 結果回注驗證
- 整合測試：呼叫 echo_tool → 結果以 `Message(role="tool")` append → 下個 turn LLM 看到此 message
- 驗證 `messages[-1].role == "tool"` 且 `tool_call_id` 對應

**任務 3.3（90 min）**：`agent_harness/tools/_inmemory_registry.py` + `echo_tool`
- `InMemoryToolRegistry`（對齐範疇 2 ABC 但簡化 backend）
- `echo_tool(text: str) -> str`：直接 return
- ToolSpec：name="echo_tool" / description / input_schema / annotations(read_only=True) / concurrency_policy=READ_ONLY_PARALLEL
- 4 unit tests（register / get / execute / unknown tool error）

**任務 3.4（60 min）**：AP-1 lint rule + sync-callback lint 驗證
- `scripts/lint/check_ap1_pipeline_disguise.py`（**新建**；現有 4 lints 是 AP-2/3/6/11，AP-1 缺）
  - 檢查 `agent_harness/orchestrator_loop/loop.py`：必含 `while` 結構（不是純 `for step in`）
  - 工具結果必須以 user/tool message 回注（grep `messages.append(Message(role="tool"`）
- 加入 `.pre-commit-config.yaml` + `.github/workflows/lint.yml`
- 4 unit tests（pos / neg / variant patterns）

**Day 3 commit**：`feat(orchestrator-loop, sprint-50-1): events + tool result feed-back + AP-1 lint (Day 3)`

---

### Day 4（2026-05-03，估 6h）— 端到端整合測試 + Tracer 埋點 + cancellation

**任務 4.1（150 min）**：`tests/integration/orchestrator_loop/test_e2e_echo.py`
- 注入 MockChatClient（pre-programmed 2-turn）
- 注入 InMemoryToolRegistry + echo_tool
- 注入 NoOpTracer（49.4 default）
- 收 `async for event in loop.run(...)` events list
- 斷言完整 event sequence + final message content + turn_count + stop_reason

**任務 4.2（90 min）**：Tracer / Metrics 埋點驗證
- 啟用 OTelTracer（in-memory exporter）作為對比測試
- 斷言每個 turn 有 span + 7 metrics 中 `agent_loop_duration_seconds` / `loop_turn_duration_seconds` 被 emit
- 1 個 observability coverage test：所有 LoopEvent emit 對應 span

**任務 4.3（60 min）**：Cancellation 完整測試
- `asyncio.wait_for(loop.run(...), timeout=0.001)` → `TimeoutError`
- 驗證 in-flight tool 被取消（用 sleep 模擬慢工具）
- 驗證 messages 不會被 partial state 污染

**任務 4.4（60 min）**：mypy --strict + 全套 pytest 跑一次
- mypy 0 issues
- pytest（49.3 73 + 49.4 70 + 50.1 ~50 = ~193）全 PASS / 0 SKIPPED

**Day 4 commit**：`test(orchestrator-loop, sprint-50-1): e2e + tracer coverage + cancellation (Day 4)`

---

### Day 5（2026-05-04，估 4h）— Polish + Retrospective + 50.2 plan stub

**任務 5.1（60 min）**：File header convention 全檔通檢
- 對 50.1 新建 ~10 檔案 補完 header（per `file-header-convention.md`）
- Modification History newest-first
- Related 引用 17.md / 01.md / 04.md

**任務 5.2（60 min）**：`progress.md`（每日累積已寫；做最終彙整）
- Day-by-day estimate vs actual ratio table
- Surprises / fixes recorded
- Cumulative branch state
- Quality gates summary

**任務 5.3（60 min）**：`retrospective.md`
- Did well / Improve / Action items for Sprint 50.2+
- Estimate accuracy %
- 3 lessons learned

**任務 5.4（30 min）**：Phase 50 README 更新
- Sprint 50.1 ✅ DONE 標記 + commits 列表
- Sprint 50.2 仍 ⏳ FUTURE（rolling — 不預寫 50.2 plan）

**任務 5.5（30 min）**：MEMORY.md 更新
- 補 `project_phase50_loop_core.md`（Phase 50.1 落地關鍵事實 + 對 50.2 prerequisites）

**Day 5 closeout commit**：`docs(sprint-50-1): closeout — Phase 50 Sprint 1/2 ✅ DONE`

---

## Acceptance Criteria（Sprint 級）

### 結構驗收（binary）

- [ ] **AP-1 零違反**：`AgentLoop.run()` 真 while-true，由 StopReason 退出（非 for-step）
- [ ] Tool 結果以 `Message(role="tool", tool_call_id=...)` 回注 messages
- [ ] `AsyncIterator[LoopEvent]` real yield（非 sync callback；違反 lint 檢出）
- [ ] 4 類終止條件全實作（stop_reason / max_turns / token_budget / cancellation）
- [ ] `OutputParser.parse(response) -> ParsedOutput` 完整 native tool_calls 解析（**禁止** regex 文本解析）
- [ ] `classify_output(response) -> OutputType` 三向分類（TOOL_USE / FINAL / HANDOFF）
- [ ] StopReason enum 中性化（4 種 stop_reason × MockChatClient 4 場景測試）
- [ ] In-memory ToolRegistry + echo_tool 可註冊 / 執行
- [ ] 端到端 e2e test：用戶 message → AgentLoop → echo → 答案 ✅
- [ ] 範疇 12 埋點：每個 turn 1 span + `agent_loop_duration_seconds` metric emit

### Quality Gates

- [ ] pytest：~50 new + 49.4 carry forward = ~193 PASS / 0 SKIPPED
- [ ] mypy --strict：0 issues across 50.1 source files
- [ ] black + isort + flake8：clean
- [ ] 4 V2 lint rules（49.4 已建）+ 1 新增 AP-1 lint = 5 lint rules：all OK
- [ ] LLM SDK leak grep（agent_harness/ + business_domain/ + platform_layer/ + runtime/ + api/）= 0
- [ ] Cross-category import lint：0 違反
- [ ] Sync-callback lint：0 違反（`AsyncIterator` real）

### 範疇成熟度

- 範疇 1（Orchestrator Loop）：Level 0 → **Level 2**（核心 loop 跑通；Level 3 需 50.2 接 API 主流量）
- 範疇 6（Output Parser）：Level 0 → **Level 3**（完整 native tool_calling parse + classifier）
- 範疇 2（Tool Layer）：Level 0 → **Level 1**（in-memory stub；51.1 進 Level 3+）
- 範疇 12（Observability）：Level 1（49.4）→ **Level 2**（範疇 1 / 6 真實埋點）

---

## File Change List（預估）

### 新建（~12 檔）

```
agent_harness/orchestrator_loop/
├── loop.py                              ← AgentLoopImpl 主類
├── events.py                            ← re-export + 範疇 1 own events
└── termination.py                       ← 4 terminators + TerminationReason

agent_harness/output_parser/
├── parser.py                            ← OutputParser 具體實作
├── classifier.py                        ← classify_output / OutputType
└── types.py                             ← ParsedOutput dataclass

agent_harness/tools/
└── _inmemory_registry.py                ← InMemoryToolRegistry + echo_tool（50.x 限定）

scripts/lint/
└── check_ap1_pipeline_disguise.py       ← 新增第 5 條 V2 lint rule

tests/unit/orchestrator_loop/
├── test_loop.py                         ← AgentLoop while-true / cancellation
├── test_termination.py                  ← 4 terminators
└── test_events.py                       ← LoopEvent emit sequence

tests/unit/output_parser/
├── test_parser.py
├── test_classifier.py
└── test_stop_reason_mapping.py

tests/integration/orchestrator_loop/
└── test_e2e_echo.py                     ← Sprint 50.1 acceptance e2e

tests/unit/tools/
└── test_inmemory_registry.py
```

### 更新（~6 檔）

```
agent_harness/orchestrator_loop/__init__.py     ← export AgentLoopImpl
agent_harness/output_parser/__init__.py         ← export OutputParser / classify_output
agent_harness/tools/__init__.py                 ← export InMemoryToolRegistry / echo_tool
adapters/_testing/mock_clients.py               ← MockChatClient 支援 sequence + 4 stop_reason
.pre-commit-config.yaml                         ← 加 AP-1 lint hook
.github/workflows/lint.yml                      ← 加 AP-1 lint job
```

### 文件（4 檔）

```
phase-50-loop-core/
├── README.md                             ← 已建立
├── sprint-50-1-plan.md                   ← (this file)
└── sprint-50-1-checklist.md              ← 與 plan 同步建立

agent-harness-execution/phase-50/sprint-50-1/
├── progress.md                           ← Day 1-5 累積
└── retrospective.md                      ← Day 5
```

---

## Dependencies & Risks

### Dependencies（已 unblocked）

| Dep | 狀態 | Sprint |
|-----|------|--------|
| `_contracts/{chat,events,state,tools}.py` | ✅ | 49.1 |
| `orchestrator_loop/_abc.py` + `output_parser/_abc.py` | ✅ | 49.1 |
| `MockChatClient` + ChatClient ABC | ✅ | 49.4 D1 |
| NoOpTracer + 7 metrics | ✅ | 49.4 D3 |
| pytest infra + lint | ✅ | 49.4 D4 |

### Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| **AP-1 lint 不夠精準（false positive 或 negative）** | M | M | Day 3 task 3.4：4 unit tests（pos/neg/variant）+ 對 49.4 lint scripts 抄結構 |
| **MockChatClient sequence injection 設計過複雜** | L | M | 簡化：`responses: list[ChatResponse]` 依 turn_count 取 index；不做 condition matching |
| **InMemoryToolRegistry 違反範疇邊界（51.1 真正範疇 2 上線後不 deprecate）** | M | L | 檔名前綴 `_`、docstring 標 `# DEPRECATED-IN: 51.1`、加 lint warning（不過 fail）|
| **Loop streaming token emit 在 50.1 偷做** | L | M | Plan 明確：50.1 只 finalized text；streaming token 留 50.2 |
| **Loop run() generator cancellation 邊界 case 漏** | M | M | Day 4 task 4.3：3 cancel scenarios（slow tool / mid-turn / before first turn）|
| **Tool 結果回注的 Message role 不對（user vs tool）** | M | H | 跟 17.md §4 確認 tool message role；MockChatClient response 容忍兩者；Day 3 task 3.2 e2e 驗 |
| **NoOpTracer 在 cancellation 漏 span end** | L | L | Day 4 task 4.2 OTelTracer in-memory exporter 對比驗證 |

---

## Out of Scope（明確不做，留待後續 sprint）

- ❌ FastAPI `POST /api/v1/chat/` endpoint（→ 50.2）
- ❌ Frontend `pages/chat-v2/`（→ 50.2）
- ❌ Streaming partial token emit（→ 50.2）
- ❌ 範疇 2 完整 ToolRegistry / Sandbox / 內建工具（web_search / python_sandbox）（→ 51.1）
- ❌ 範疇 3 Memory（5 層）（→ 51.2）
- ❌ 範疇 4 Compaction（→ 52.1）
- ❌ 範疇 5 PromptBuilder（→ 52.2）
- ❌ 範疇 7 Checkpointer 完整（→ 53.1；50.1 用 in-memory TransientState 即可）
- ❌ 範疇 8 ErrorPolicy / Retry / CircuitBreaker（→ 53.2）
- ❌ 範疇 9 Guardrails / Tripwire（→ 53.3；50.1 留 ABC stub）
- ❌ 範疇 10 Verifier（→ 54.1）
- ❌ 範疇 11 Subagent / handoff（→ 54.2；classify_output `HANDOFF` 留 enum，不實作 dispatch）
- ❌ 真實 LLM provider 整合測試（用 MockChatClient；real LLM 留 50.2 demo）
- ❌ Worker queue（Celery/Temporal）整合（→ 53.1；50.1 不經 worker，直接 in-process）

---

## 驗收與 Definition of Done

### Sprint Done

- ✅ 11 個 acceptance criteria 全部 binary check 通過
- ✅ 5 個 quality gates 全部綠燈
- ✅ 範疇 1 / 6 / 2 / 12 成熟度提升符合預期
- ✅ ~12 個新建檔案 + ~6 個更新檔案 全部 file header convention 對齐
- ✅ Sprint 50.1 retrospective.md 完成
- ✅ Phase 50 README 更新（50.1 ✅ DONE）
- ✅ MEMORY.md 更新

### Done = Ready for Sprint 50.2

- AgentLoop.run() 可被 `runtime/workers/agent_loop_worker.py`（49.4 stub）的 handler 直接呼叫
- LoopEvent AsyncIterator 可被 SSE handler `async for` consume（50.2 任務）
- e2e test 為 50.2 demo 案例「問 echo X，回答 X」奠定基礎

---

## 引用權威文件

- `06-phase-roadmap.md` §Phase 50 — Sprint 50.1 範圍源頭
- `01-eleven-categories-spec.md` §範疇 1 / §範疇 6 — ABC + 結構驗收 + SLO
- `17-cross-category-interfaces.md` §1.1 / §2.1 / §4.1 / §4.2 — single-source 型別 + ABC + LoopEvent 表 + 事件序列
- `04-anti-patterns.md` §AP-1 Pipeline 偽裝 Loop — Day 3 lint rule 依據
- `10-server-side-philosophy.md` §原則 1 / §原則 2 — Server-Side First + LLM Provider Neutrality
- `02-architecture-design.md` §約束 2 — 範疇間依賴
- `.claude/rules/sprint-workflow.md` — 5-step execution 紀律
- `.claude/rules/anti-patterns-checklist.md` — 11 點 PR 自檢
- `.claude/rules/observability-instrumentation.md` — 範疇 12 埋點規範
- `.claude/rules/llm-provider-neutrality.md` — agent_harness/ 禁 LLM SDK import
- 49.4 sprint-49-4-plan.md — 結構範本

---

**Plan Status**：🔵 PLANNED — 等用戶 approve 才開始 Day 1 code
**Next Step**：用戶 review → approve → AI 助手建 feature branch `feature/phase-50-sprint-1-loop-core`
