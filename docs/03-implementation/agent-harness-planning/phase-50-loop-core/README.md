# Phase 50 — Loop Core

**Phase 進度**：Sprint 50.1 待 user approve（plan + checklist 已就緒）
**啟動日期**：2026-04-29（接 Phase 49 closeout）
**完成日期**：—
**狀態**：🔵 Sprint 50.1 PLANNED — 等用戶 approve 開始 Day 1 code

---

## Phase 50 目標

> **最重要的 Phase**（per `06-phase-roadmap.md` §Phase 50）。
> 實作真正的 TAO loop，跑通最簡單的 agent 對話。
> 完成後範疇 1 達 Level 3、範疇 6 達 Level 4。

詳細路線圖見 [`../06-phase-roadmap.md` §Phase 50](../06-phase-roadmap.md#phase-50-loop-core2-sprint)。

---

## Sprint 進度總覽

| Sprint | 狀態 | 主題 | 預估 | Branch |
|--------|------|------|------|--------|
| **50.1** | 🔵 PLANNED | 範疇 1 (Orchestrator Loop) + 範疇 6 (Output Parser) 核心 | 1 週（~28 SP） | `feature/phase-50-sprint-1-loop-core`（待建立） |
| **50.2** | ⏳ FUTURE | API + Frontend 對接（rolling — 50.1 closeout 後寫 plan） | 1 週 | — |

---

## Sprint 文件導航

```
phase-50-loop-core/
├── README.md                          ← (this file) Phase 50 入口
├── sprint-50-1-plan.md                🔵 待 user approve
├── sprint-50-1-checklist.md           🔵 待 user approve
├── sprint-50-2-plan.md                ⏳ 50.1 完成後寫（rolling planning）
└── sprint-50-2-checklist.md           ⏳ 50.1 完成後寫
```

執行紀錄（待建）：
```
docs/03-implementation/agent-harness-execution/phase-50/
└── sprint-50-1/{progress,retrospective}.md（待建）
```

---

## Phase 50 預期交付（從 06-phase-roadmap.md 抄錄；正式驗收以 sprint plan 為準）

### Sprint 50.1 預期交付

- `agent_harness/orchestrator_loop/loop.py` — `AgentLoop` 主類（while True + stop_reason 退出）
- `agent_harness/orchestrator_loop/events.py` — Loop events 完整流（補 49.1 _contracts/events.py 缺口）
- `agent_harness/orchestrator_loop/termination.py` — 4 類終止條件（max_turns / token_budget / tripwire / error）
- `agent_harness/output_parser/parser.py` — Native tool_calls 解析
- `agent_harness/output_parser/classifier.py` — Output 分類（TOOL_USE / FINAL / HANDOFF）
- 簡單 in-memory tool（`echo_tool` for testing）
- 第一個端到端測試：「用戶問 X → loop 跑 → 回答 X」

### Sprint 50.1 結構驗收（per 01-eleven-categories-spec.md §範疇 1）

- ✅ Loop 真正使用 `while` 結構（非 `for` 固定迴數）
- ✅ `StopReason` enum 驅動退出（中性化）
- ✅ Tool 結果以 `user message` 形式回注 messages
- ✅ Anti-Pattern 1（Pipeline 偽裝 Loop）零違反

### Sprint 50.2 預期（先列；正式 plan 50.1 closeout 後寫）

- API endpoint `POST /api/v1/chat/`（SSE）
- Frontend `pages/chat-v2/` 基本介面
- 整合 `runtime/workers/agent_loop_worker.py`（49.4 已建 stub）
- 第一個演示：「問 echo X，回答 X」

---

## Phase 50.1 Prerequisites（從 49.4 closeout 確認 unblocked）

- ✅ `ChatClient` ABC + `MockChatClient`（49.4 Day 1 + 41 contract tests）
- ✅ `_contracts/{chat,state,events,tools,...}` 完整（49.1 Day 4）
- ✅ `orchestrator_loop/_abc.py` stub（49.1）
- ✅ `output_parser/_abc.py` stub（49.1）
- ✅ `NoOpTracer` + 7 metrics 註冊（49.4 Day 3）
- ✅ `AgentLoopWorker.handler` signature（49.4 Day 2）
- ✅ pytest infra 完整（49.4 closeout 143 PASS）

---

## 下一步

1. 用戶 review `sprint-50-1-plan.md` + `sprint-50-1-checklist.md`
2. 用戶 approve → AI 助手建 feature branch 開始 Day 1 code
3. Day 1-5 嚴格按 V2 workflow（plan → checklist [ ] → code → checklist [x] → daily progress.md）
4. 50.1 closeout 才寫 sprint-50-2 plan（rolling planning 紀律）

---

**Last Updated**：2026-04-29 (Sprint 50.1 planning kickoff — Phase 49 ✅ DONE, Phase 50 starting)
**Maintainer**：用戶 + AI 助手共同維護
