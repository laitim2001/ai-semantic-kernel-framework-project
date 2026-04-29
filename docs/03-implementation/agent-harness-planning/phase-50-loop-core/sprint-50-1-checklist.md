# Sprint 50.1 Checklist — Loop Core

**Sprint**：50.1
**Plan**：[sprint-50-1-plan.md](./sprint-50-1-plan.md)
**Branch**：`feature/phase-50-sprint-1-loop-core` (created 2026-04-29)
**預估**：5 days / ~28 SP / ~28h
**Status**：🟢 IN_PROGRESS — Day 0-2 ✅ DONE; Day 3 next

> **使用方式**：每完成一項，將 `[ ]` 改為 `[x]`。**禁止刪除未勾選項**（per CLAUDE.md sacred rule）。如項目被取消，標 🚧 + 寫理由保留。

---

## Day 0（用戶 approve 後執行）— Branch + 環境準備（30 min）

- [x] **0.1 建 feature branch**
  - DoD：`git status` 顯示 on `feature/phase-50-sprint-1-loop-core`，from main HEAD（or last 49.4 closeout commit）
  - Command：`git checkout -b feature/phase-50-sprint-1-loop-core`

- [x] **0.2 確認 prerequisites 全綠**
  - DoD：pytest 143 PASS（49.4 closeout baseline）；mypy strict 0；4 lints OK
  - Command：`cd backend && pytest -q && mypy src --strict`

- [x] **0.3 commit plan + checklist + Phase 50 README**
  - DoD：3 docs commit 到 feature branch first commit
  - Command：`git add docs/03-implementation/agent-harness-planning/phase-50-loop-core/ && git commit -m "docs(sprint-50-1, sprint-50-1): plan + checklist + Phase 50 README"`

---

## Day 1（2026-04-30，估 6h）— Output Parser + StopReason 完整化

### 1.1 OutputParser 具體實作（90 min）

- [x] **建 `agent_harness/output_parser/types.py`**
  - 內容：`ParsedOutput` dataclass（tool_calls / final_text / handoff_request / metadata）
  - DoD：mypy strict pass；可 import
  - Command：`python -c "from agent_harness.output_parser.types import ParsedOutput; print(ParsedOutput.__dataclass_fields__.keys())"`

- [x] **建 `agent_harness/output_parser/parser.py`**
  - 內容：`OutputParser` 具體實作（從 49.1 _abc.py 衍生 `OutputParserImpl`）
  - 方法：`parse(response: ChatResponse) -> ParsedOutput`
  - 邏輯：從 ChatResponse.tool_calls / content / 自定欄位 萃取
  - **禁止** regex 文本解析（lint check）
  - DoD：5 unit tests PASS（pos: tool_calls / final_text / handoff / 空 / 混合）

- [x] **建 `agent_harness/output_parser/__init__.py` 補完 export**
  - DoD：`from agent_harness.output_parser import OutputParser, ParsedOutput, classify_output, OutputType` 全可用

### 1.2 classifier.py（60 min）

- [x] **建 `agent_harness/output_parser/classifier.py`**
  - 內容：`OutputType{TOOL_USE, FINAL, HANDOFF}` enum + `classify_output(response: ChatResponse) -> OutputType`
  - 邏輯：tool_calls 非空 → TOOL_USE；handoff_request 非空 → HANDOFF；否則 → FINAL
  - DoD：3 unit tests PASS（每個 case 1 個）+ docstring 標 owner=範疇 6

### 1.3 StopReason 4 種 mapping + MockChatClient enhancement（90 min）

- [x] **確認 `_contracts/chat.py` StopReason enum 完整**
  - 應有 5 enum：END_TURN / TOOL_USE / MAX_TOKENS / SAFETY_REFUSAL / PROVIDER_ERROR
  - DoD：49.4 已建；50.1 不新增；確認 import OK

- [x] 🚧 **更新 `adapters/_testing/mock_clients.py`** — SKIPPED: 49.4 MockChatClient `responses: list[ChatResponse]` + `pop(0)` already implements sequence behavior; no enhancement needed
  - 加 `MockChatClient.with_response_sequence(responses: list[ChatResponse])`
  - 依 turn_count（call count）取 index；超出時 raise StopIteration
  - DoD：6 unit tests（1 turn / 2 turn / 3 turn / 0 / overrun / reset）

- [x] **建 `tests/unit/output_parser/test_stop_reason_mapping.py`**
  - 4 stop_reason × 3 場景 = 12 unit tests
  - 場景：純 stop_reason / 含 tool_calls / 含 content
  - DoD：12 PASS

### 1.4 Parser + Classifier 單元測試（60 min）

- [x] **建 `tests/unit/output_parser/test_parser.py`**
  - 5 tests: 純 final_text / 純 tool_calls / 純 handoff / 空 / 混合（tool_calls + content）
  - 1 perf test：1k 次 parse < 5s（p95 < 5ms / call）
  - DoD：6 PASS

- [x] **建 `tests/unit/output_parser/test_classifier.py`**
  - 3 tests: TOOL_USE / FINAL / HANDOFF（per 1 ChatResponse fixture）
  - DoD：3 PASS

### Day 1 Wrap-up

- [x] **跑全套 pytest + mypy + lints 確認 0 regression**
  - Command：`cd backend && pytest -q && mypy src --strict && python scripts/lint/check_*.py src/`
  - DoD：143（49.4 carry）+ ~25 new = ~168 PASS / 0 SKIPPED

- [x] **Day 1 progress.md 寫入**
  - 路徑：`docs/03-implementation/agent-harness-execution/phase-50/sprint-50-1/progress.md`
  - 內容：Day 1 estimate vs actual / 完成項 / surprises

- [x] **Day 1 commit**
  - Message：`feat(output-parser, sprint-50-1): OutputParser + classifier + StopReason mapping (Day 1)`
  - DoD：commit hash 記入 progress.md

---

## Day 2（2026-05-01，估 6h）— AgentLoop while-true + termination

### 2.1 termination.py 4 類終止（120 min）

- [x] **建 `agent_harness/orchestrator_loop/termination.py`**
  - 4 個 terminator function：
    - `should_terminate_by_stop_reason(response: ChatResponse) -> bool`
    - `should_terminate_by_turns(turn_count: int, max_turns: int) -> bool`
    - `should_terminate_by_tokens(tokens_used: int, token_budget: int) -> bool`
    - `should_terminate_by_cancellation() -> bool`（檢查 asyncio current task cancellation）
  - `TerminationReason` enum：END_TURN / MAX_TURNS / TOKEN_BUDGET / CANCELLED / TRIPWIRE / ERROR
  - `TripwireTerminator` ABC stub（範疇 9 在 53.3 接入）
  - DoD：mypy strict pass；ABC stub 含 docstring 標 「Sprint 53.3 implements」

- [x] **建 `tests/unit/orchestrator_loop/test_termination.py`**
  - 8 unit tests：4 terminator × 2 scenarios（trigger / not trigger）
  - DoD：8 PASS

### 2.2 AgentLoopImpl 主迴圈（180 min）

- [x] **建 `agent_harness/orchestrator_loop/loop.py`**
  - `class AgentLoopImpl(AgentLoop)`：
    - `__init__(chat_client, output_parser, tool_registry, tracer, ...)`
    - `async def run(messages, tools, system_prompt, max_turns=50, token_budget=100_000, ...)` async generator
  - 主迴圈邏輯：
    ```python
    turn_count = 0
    yield LoopStarted(...)
    while True:
        if should_terminate_by_turns(turn_count, max_turns) or ...:
            yield LoopCompleted(reason=...)
            break
        try:
            response = await self.chat_client.chat(messages, tools, ...)
            yield Thinking(text=response.content_text)
            parsed = self.output_parser.parse(response)
            output_type = classify_output(response)
            if output_type == OutputType.FINAL:
                yield LoopCompleted(reason=END_TURN)
                break
            elif output_type == OutputType.TOOL_USE:
                for tc in parsed.tool_calls:
                    yield ToolCallRequested(tool_call=tc)
                    result = await self.tool_registry.execute(tc)
                    messages.append(Message(role="tool", tool_call_id=tc.id, content=result))
                    # ToolCallExecuted yielded by tool_registry impl in Day 3
                turn_count += 1
                continue
            elif output_type == OutputType.HANDOFF:
                yield LoopCompleted(reason=HANDOFF_NOT_IMPLEMENTED)  # 50.1 留 enum，54.2 接
                break
        except asyncio.CancelledError:
            # in-flight cleanup
            yield LoopCompleted(reason=CANCELLED)
            raise
    ```
  - DoD：mypy strict pass；可 import；無業務邏輯錯誤

- [x] **建 `tests/unit/orchestrator_loop/test_loop.py`**
  - 6 unit tests：
    1. 單 turn 結束（FINAL stop_reason）
    2. 多 turn（2-turn tool_use → end_turn）
    3. max_turns 觸發（max_turns=2 + LLM 一直 tool_use）
    4. token_budget 觸發
    5. cancellation（asyncio.wait_for timeout）
    6. HANDOFF 路徑（50.1 留 LoopCompleted reason=HANDOFF_NOT_IMPLEMENTED）
  - DoD：6 PASS

### 2.3 MockChatClient sequence enhancement test（60 min）

- [x] **加 `MockChatClient` cancellation 行為測試**
  - 測試：tool execute 中 cancel → MockChatClient 不應發新 chat call
  - DoD：2 unit tests PASS

### Day 2 Wrap-up

- [x] **跑全套 pytest + mypy + lints**
  - DoD：~168（Day 1 累積）+ ~16 new = ~184 PASS

- [x] **Day 2 progress.md 寫入**

- [x] **Day 2 commit**
  - Message：`feat(orchestrator-loop, sprint-50-1): AgentLoop while-true main loop + 4 terminators (Day 2)`

---

## Day 3（2026-05-02，估 6h）— Events + tool 結果回注 + AP-1 lint

### 3.1 events.py 範疇 1 own 事件（90 min）

- [ ] **建 `agent_harness/orchestrator_loop/events.py`**
  - 從 `_contracts/events.py` re-export `LoopEvent` base + 9 子類
  - 在 orchestrator_loop/ 內 own 5 個必須事件（per 17.md §4.1）：
    - `LoopStarted` / `Thinking` / `LoopCompleted`（owner: 範疇 1）
    - `ToolCallRequested`（owner: 範疇 6 — output_parser 解析後 emit）
    - `ContextCompacted` stub（owner: 範疇 4 在 52.1）
  - 每個 event 含 `trace_context: TraceContext`（NoOpTracer fallback）
  - DoD：所有 event 可 instantiate + json-serialize（用於後續 SSE）

- [ ] **建 `tests/unit/orchestrator_loop/test_events.py`**
  - 5 tests：每個 event class 1 個 instantiate + serialize
  - 1 test：sequence 順序（LoopStarted → ... → LoopCompleted）
  - DoD：6 PASS

### 3.2 Tool 結果回注驗證（60 min）

- [ ] **整合測試 `tests/integration/orchestrator_loop/test_tool_feedback.py`**
  - MockChatClient sequence：
    - Turn 1：tool_calls=[ToolCall(name="echo", arguments={"text":"hi"})]
    - Turn 2：FINAL「The echo returned: hi」
  - 跑 `async for event in loop.run(...)` 收集 events + final messages
  - 斷言：`messages[-1].role == "tool"` 且 `tool_call_id` 對應
  - 斷言：第 2 turn ChatClient 收到包含 tool message 的 messages
  - DoD：1 test PASS（核心 e2e tool feedback case）

### 3.3 InMemoryToolRegistry + echo_tool（90 min）

- [ ] **建 `agent_harness/tools/_inmemory_registry.py`**
  - `class InMemoryToolRegistry(ToolRegistry)`（對齐 49.1 _abc.py）
  - 方法：register / get / list / execute
  - **檔名前綴 `_` + docstring 標：「DEPRECATED-IN: Sprint 51.1（範疇 2 完整實作 supersedes）」**
  - `echo_tool` 函式 + `ECHO_TOOL_SPEC: ToolSpec`（read_only / read_only_parallel）
  - 整合 49.4 NoOpTracer（emit `tool_execution_duration_seconds` metric）
  - DoD：mypy strict pass；可 import + execute

- [ ] **建 `tests/unit/tools/test_inmemory_registry.py`**
  - 5 tests：register / get / list / execute echo / unknown tool error
  - 1 test：metric emit 驗證（用 in-memory metric reader）
  - DoD：6 PASS

### 3.4 AP-1 lint rule（60 min）

- [ ] **建 `scripts/lint/check_ap1_pipeline_disguise.py`**
  - 檢查 `agent_harness/orchestrator_loop/loop.py` 結構：
    - 必須含 `while True:` 或 `while not …:`（AST 檢測）
    - 不能用 `for step in steps:` 模式
  - 檢查 tool 結果回注：
    - grep `messages.append(Message(role=` 或同等模式
    - 缺失 → fail with hint「AP-1: Tool results must be fed back as messages」
  - **stdlib only**（per 49.4 lint scripts 慣例）
  - DoD：mypy strict pass

- [ ] **加入 `.pre-commit-config.yaml`**
  - 同 49.4 4 個 lint hooks 結構
  - DoD：`pre-commit run check-ap1 --all-files` 對 50.1 codebase 0 違反

- [ ] **加入 `.github/workflows/lint.yml`**
  - 加一個 step `Check AP-1 pipeline disguise`
  - DoD：CI workflow YAML 合法（GH Actions parser 通過）

- [ ] **建 `tests/unit/lint/test_ap1_pipeline_disguise.py`**
  - 4 tests：
    - pos：AgentLoopImpl with while-True → pass
    - neg：fake module with `for step in steps:` → fail
    - variant：`while turn_count < max_turns:` → pass（while-conditional 也算）
    - missing tool feedback → fail
  - DoD：4 PASS

### Day 3 Wrap-up

- [ ] **跑全套 pytest + mypy + 5 lints（49.4 4 + AP-1 1）**
  - DoD：~184 + ~21 new = ~205 PASS

- [ ] **Day 3 progress.md 寫入**

- [ ] **Day 3 commit**
  - Message：`feat(orchestrator-loop, sprint-50-1): events + tool result feed-back + AP-1 lint (Day 3)`

---

## Day 4（2026-05-03，估 6h）— E2E + Tracer 埋點 + Cancellation

### 4.1 端到端 e2e test（150 min）

- [ ] **建 `tests/integration/orchestrator_loop/test_e2e_echo.py`**
  - Setup fixtures：
    - MockChatClient with 2-turn pre-programmed response sequence
    - InMemoryToolRegistry + register echo_tool
    - OutputParserImpl
    - NoOpTracer
    - AgentLoopImpl
  - Run：
    ```python
    events = []
    async for event in loop.run(
        messages=[Message(role="user", content="please echo hello")],
        tools=[ECHO_TOOL_SPEC],
        system_prompt="You are an echo assistant.",
        max_turns=5,
        token_budget=10_000,
    ):
        events.append(event)
    ```
  - 斷言 event 序列（順序 + types）：
    - `LoopStarted` × 1
    - `Thinking` × 2
    - `ToolCallRequested` × 1
    - `LoopCompleted` × 1（reason=END_TURN）
  - 斷言 messages 最終狀態：
    - 含 `Message(role="tool", tool_call_id=...)`
    - 最後一個 assistant turn content 含「hello」
  - 斷言 turn_count == 2
  - DoD：1 test PASS in < 1s

- [ ] **驗證 e2e test 在 cancellation 邊界正確**
  - `asyncio.wait_for(loop.run(...), timeout=...)` 觸發 cancel mid-turn
  - 斷言：events 含 LoopCompleted with reason=CANCELLED
  - 斷言：raises asyncio.CancelledError
  - DoD：1 test PASS

### 4.2 Tracer / Metrics 埋點驗證（90 min）

- [ ] **建 `tests/integration/orchestrator_loop/test_observability_coverage.py`**
  - 用 OTelTracer + in-memory exporter（49.4 SDK 已有）
  - 跑 e2e echo flow
  - 斷言：每個 turn 有對應 span
  - 斷言：`agent_loop_duration_seconds` metric emit
  - 斷言：`loop_turn_duration_seconds` metric emit per turn
  - 斷言：`tool_execution_duration_seconds` metric emit per tool call
  - DoD：4 assertions PASS

- [ ] **驗證 `observability-instrumentation.md` 5 處埋點覆蓋**
  - 1. Loop turn 開頭 + 結尾 ✓
  - 2. Tool 執行前後 ✓
  - 3. LLM 呼叫前後（adapter 已埋）✓
  - 4. Output parser parse 前後（50.1 補）✓
  - 5. State checkpoint（50.1 N/A — 53.1 接入）✓ skip with stub
  - DoD：5 處全綠（4 + 1 skip）

### 4.3 Cancellation 完整測試（60 min）

- [ ] **建 `tests/unit/orchestrator_loop/test_cancellation.py`**
  - 3 scenarios：
    1. Slow tool execute → cancel mid-tool → 工具被 cancel + Loop yield CANCELLED
    2. Cancel before first turn → LoopStarted yield 但立即 LoopCompleted CANCELLED
    3. Cancel between turns → 不發新 chat call
  - 斷言：messages 不會被 partial state 污染（最後 message 完整 / 整體 consistent）
  - DoD：3 PASS

### 4.4 全套驗證（60 min）

- [ ] **mypy --strict 對 50.1 全 source 跑一次**
  - DoD：0 issues

- [ ] **pytest 全套**
  - DoD：~205 + ~10 new = ~215 PASS / 0 SKIPPED / < 5s

- [ ] **5 lints + LLM SDK leak grep**
  - Command：
    ```
    python scripts/lint/check_duplicate_dataclass.py src/
    python scripts/lint/check_cross_category_import.py src/agent_harness/
    python scripts/lint/check_sync_callback.py src/agent_harness/
    python scripts/lint/check_llm_sdk_leak.py src/agent_harness/ src/business_domain/ src/platform_layer/ src/runtime/ src/api/
    python scripts/lint/check_ap1_pipeline_disguise.py src/agent_harness/orchestrator_loop/
    ```
  - DoD：5 lints 全 PASS / LLM SDK leak = 0

- [ ] **alembic from-zero cycle（49.4 baseline 確認）**
  - Command：`cd backend && alembic downgrade base && alembic upgrade head`
  - DoD：head=`0010_pg_partman` / 0 error

### Day 4 Wrap-up

- [ ] **Day 4 progress.md 寫入**

- [ ] **Day 4 commit**
  - Message：`test(orchestrator-loop, sprint-50-1): e2e + tracer coverage + cancellation (Day 4)`

---

## Day 5（2026-05-04，估 4h）— Polish + Retrospective + 50.2 stub

### 5.1 File header convention 全檔通檢（60 min）

- [ ] **對 50.1 新建 ~12 檔逐一補完 file header**
  - 需含：File / Purpose / Category / Scope / Description / Key Components / Created / Last Modified / Modification History (newest-first) / Related
  - 範疇對齐：1（loop / events / termination）/ 6（parser / classifier / types）/ 2（_inmemory_registry）
  - DoD：每檔 grep `Modification History` 找到；newest-first

- [ ] **更新檔的 Modification History 補一筆**
  - `MockChatClient`（49.4 → 50.1 加 sequence）
  - `_contracts/events.py`（如有 minor 補欄位）
  - DoD：Modification History newest-first 含 50.1 entry

### 5.2 progress.md 最終彙整（60 min）

- [ ] **`docs/03-implementation/agent-harness-execution/phase-50/sprint-50-1/progress.md` 最終版**
  - Day-by-Day estimate vs actual table（5 day）
  - Daily highlights（Day 1-5 重點）
  - Surprises / fixes recorded（**rule**：≥ 2 條真實踩坑）
  - Cumulative branch state（commits list + lines added/removed）
  - Quality gates summary（pytest / mypy / lints / LLM SDK leak / multi-tenant rule check）
  - DoD：~150-200 行彙整文件

### 5.3 retrospective.md（60 min）

- [ ] **`docs/03-implementation/agent-harness-execution/phase-50/sprint-50-1/retrospective.md`**
  - **Did well**（≥ 3 條）
  - **Improve next sprint**（≥ 3 條）
  - **Action items for Sprint 50.2+**（每項標 owner + deadline）
  - **Estimate accuracy %**（plan 28h / actual ?h ratio）
  - **3 lessons learned**（含「為何 V2 plan 仍保守」自省）
  - **49.4 retro 5 Action items 中 Sprint 50.1 carry-over 處理狀態**
  - DoD：~100-150 行 retrospective

### 5.4 Phase 50 README 更新（30 min）

- [ ] **更新 `phase-50-loop-core/README.md`**
  - Sprint 50.1 ✅ DONE 標記
  - 完成日期 / branch / commits 列表
  - Sprint 50.2 仍 ⏳ FUTURE（**不寫 50.2 plan**；rolling）
  - 「Phase 50.2 prerequisites」段：列 50.1 unblocked 的能力
  - DoD：標題 / 表格 / 日期更新一致

### 5.5 MEMORY.md 更新（30 min）

- [ ] **建 `memory/project_phase50_loop_core.md`**
  - Phase 50.1 落地關鍵事實
  - 對 50.2 prerequisites（AsyncIterator yield 可被 SSE consume / runtime/workers handler 可呼叫）
  - DoD：內容 ≤ 30 行

- [ ] **更新 `memory/MEMORY.md` index**
  - 加一行：`- [project_phase50_loop_core.md](project_phase50_loop_core.md) — Phase 50.1 ✅ ...`
  - DoD：MEMORY.md index < 200 行

### Day 5 Closeout

- [ ] **Day 5 closeout commit**
  - Message：`docs(sprint-50-1): closeout — Phase 50 Sprint 1/2 ✅ DONE`
  - 含：file header polish + progress.md final + retrospective.md + Phase 50 README update + MEMORY.md update
  - DoD：commit 後 working tree clean（除 user IDE 編輯）

- [ ] **Phase 50 progress 確認**
  - 50.1 ✅ DONE / 50.2 ⏳ PLANNED
  - DoD：README 顯示 1/2 = 50%

---

## Sprint 50.1 整體 Acceptance Sanity Check（Day 5 結束最終驗）

- [ ] AP-1 lint 對整個 agent_harness/orchestrator_loop/ 跑一次：0 違反
- [ ] AsyncIterator real（grep `AgentLoop.run` 無 sync callback signature）
- [ ] StopReason 4 enum 中性化（per_provider mapping unit tests 12 PASS）
- [ ] Tool message role 為 "tool"（grep `Message(role="tool"` 出現在 tests + loop.py）
- [ ] e2e test 真實跑通：「用戶問 echo hello → 答 hello」（test_e2e_echo PASS）
- [ ] 範疇 12 埋點驗證 4/5 處（state checkpoint 留 53.1 stub）
- [ ] pytest ~215 PASS / 0 SKIPPED / < 5s
- [ ] mypy --strict 0 issues
- [ ] 5 V2 lints + LLM SDK leak = 0 違反
- [ ] LoopState（TransientState only）跨 turn 正確維護（messages / turn_count / tokens_used）

---

## 用戶手動處理項（從 49.x 累積 + 50.1 新增）

> **per CLAUDE.md sacred rule：留 [ ] 不刪；標 ⏸ + 理由保留**

- [ ] ⏸ **GitHub branch protection rule**（49.1 carry）— admin UI
- [ ] ⏸ **49.1+49.2+49.3+49.4 merge to main 決策**（用戶決策）
- [ ] ⏸ **npm audit 2 moderate vulnerabilities**（49.1 carry；frontend sprint）
- [ ] 🚧 **Production app role 在 staging 環境配置**（49.4 → Phase 53.1+）
- [ ] 🚧 **CI deploy gate 引入規範 E 警報**（Phase 55 production cutover）
- [ ] 🚧 **TemporalQueueBackend 真實實作**（Phase 53.1 HITL signals 真實需要時）
- [ ] 🚧 **pg_partman create_parent for messages/message_events**（生產 deploy ops runbook）
- [ ] 🚧 **tool_calls.message_id FK**（PG 18 LTS / Phase 56+）
- [ ] 🚧 **Frontend Vite 啟動整合**（49.4 推遲；用戶 owns）
- [ ] 🚧 **InMemoryToolRegistry deprecate**（51.1 範疇 2 完整實作 supersedes）

---

**Status**：🔵 PLANNED — 等用戶 approve 才執行 Day 0
