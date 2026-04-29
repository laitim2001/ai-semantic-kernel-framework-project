# Phase 50 — Loop Core

**Phase 進度**：Sprint 50.1 ✅ DONE / Sprint 50.2 🟡 IN PROGRESS — **1 / 2 sprint complete（50%）**
**啟動日期**：2026-04-29（接 Phase 49 closeout）
**完成日期**：—（Phase 50 still in progress; 50.2 Day 0 started 2026-04-30）
**狀態**：🟡 Sprint 50.2 Day 0 — plan + checklist approved; branch `feature/phase-50-sprint-2-api-frontend` 已開

---

## Phase 50 目標

> **最重要的 Phase**（per `06-phase-roadmap.md` §Phase 50）。
> 實作真正的 TAO loop，跑通最簡單的 agent 對話。
> 完成後範疇 1 達 Level 3、範疇 6 達 Level 4。

詳細路線圖見 [`../06-phase-roadmap.md` §Phase 50](../06-phase-roadmap.md#phase-50-loop-core2-sprint)。

---

## Sprint 進度總覽

| Sprint | 狀態 | 主題 | 完成日期 | Branch / Commits |
|--------|------|------|---------|------------------|
| **50.1** | ✅ DONE | 範疇 1 (Orchestrator Loop) + 範疇 6 (Output Parser) 核心 | 2026-04-30 | `feature/phase-50-sprint-1-loop-core`（10 commits incl. closeout）|
| **50.2** | 🟡 IN PROGRESS | API + Frontend 對接 | — | `feature/phase-50-sprint-2-api-frontend`（Day 0 + plan/checklist 已 commit）|

---

## Sprint 文件導航

```
phase-50-loop-core/
├── README.md                          ← (this file) Phase 50 入口
├── sprint-50-1-plan.md                ✅ DONE
├── sprint-50-1-checklist.md           ✅ DONE
├── sprint-50-2-plan.md                🟡 Day 0 (committed 2026-04-30)
└── sprint-50-2-checklist.md           🟡 Day 0 (committed 2026-04-30)
```

執行紀錄：
```
docs/03-implementation/agent-harness-execution/phase-50/
└── sprint-50-1/{progress,retrospective}.md ✅
```

---

## Sprint 50.1 累計交付

### 主要 source（7 檔）

- `agent_harness/orchestrator_loop/loop.py` — `AgentLoopImpl` while-true 主迴圈（AP-1 cure）
- `agent_harness/orchestrator_loop/termination.py` — 4 純 terminator + `TerminationReason` enum + `TripwireTerminator` ABC stub
- `agent_harness/orchestrator_loop/events.py` — Cat 1 owner-attribution shim（re-export from `_contracts.events`）
- `agent_harness/output_parser/parser.py` — `OutputParserImpl` (Tracer + native tool_calls only)
- `agent_harness/output_parser/classifier.py` — `classify_output()` 3-way + `HANDOFF_TOOL_NAME`
- `agent_harness/output_parser/types.py` — `ParsedOutput` (refactored from 49.1 _abc) + `OutputType` enum
- `agent_harness/tools/_inmemory.py` — `InMemoryToolRegistry` + `InMemoryToolExecutor` + `echo_tool` + `make_echo_executor()` factory (DEPRECATED-IN: 51.1)

### Refactored / Updated（4 檔）

- `agent_harness/output_parser/_abc.py` — refactor 把 `ParsedOutput` 移到 `.types`
- `agent_harness/output_parser/__init__.py` — full export
- `agent_harness/orchestrator_loop/__init__.py` — full export
- `agent_harness/tools/__init__.py` — full export incl. `_inmemory` symbols

### Lint 強化（1 條新 V2 lint）

- `scripts/lint/check_ap1_pipeline_disguise.py` — V2 Lint #5（AP-1 detection）
- `.pre-commit-config.yaml` + `.github/workflows/lint.yml` — hook + CI step

### Tests（60 new tests）

- Unit: parser × 5 / classifier × 3 / stop_reason × 13 / termination × 10 / loop × 7 / tools (_inmemory) × 8 / ap1-lint × 4
- Integration: tool feedback × 2 / e2e echo × 2 / observability coverage × 3 / cancellation safety × 3
- Total: **210 PASS / 0 SKIPPED / 4.25s**

### 文件

- `sprint-50-1-plan.md` (474 行)
- `sprint-50-1-checklist.md` (469 行；Day 0-5 全 [x]，1 項 🚧 with reason)
- `progress.md` (Day-by-day estimates / 12 surprises / branch state / quality gates)
- `retrospective.md` (3 lessons / 9 carry items / 49.4 retro carry-over status)

---

## Sprint 50.1 結構驗收（per 01-eleven-categories-spec.md §範疇 1 + §範疇 6）

- ✅ Loop 真正使用 `while` 結構（非 `for` 固定迴數）— AP-1 lint 強制驗證
- ✅ `StopReason` enum 中性化驅動退出（4 種 reason × 3 場景測試 12 PASS）
- ✅ Tool 結果以 `Message(role="tool", tool_call_id=...)` 回注 messages
- ✅ `AsyncIterator[LoopEvent]` real（無 sync callback）
- ✅ 4 類終止條件（max_turns / token_budget / cancellation / stop_reason）+ TripwireTerminator ABC stub
- ✅ Native tool_calling parse（禁 regex；AP-9 cure 驗證）
- ✅ Anti-Pattern 1（Pipeline 偽裝 Loop）零違反 — lint clean
- ✅ Sprint 50.1 e2e acceptance：用戶問 echo X → loop 跑 → 答 X — `test_e2e_echo_acceptance` PASS

---

## Phase 50.2 Prerequisites — UNBLOCKED

從 50.1 closeout 確認，下列能力已 ready 給 50.2 任務：

- ✅ `AgentLoopImpl.run()` 是真實 `AsyncIterator[LoopEvent]`，可直接 feed 進 SSE handler
- ✅ `make_echo_executor()` factory + `ECHO_TOOL_SPEC`：50.2 demo「問 echo X 答 X」立即可用
- ✅ Cat 12 Tracer / Metrics 埋點完整：50.2 frontend 可顯示 LoopEvent 流
- ✅ `runtime/workers/agent_loop_worker.py` (49.4) `TaskHandler` sig 跟 `AgentLoopImpl.run()` 兼容 — 接入 mechanical
- ✅ `MockChatClient.responses` sequence (49.4)：50.2 frontend smoke test 可預編腳本，real LLM 留 closeout 階段
- ✅ AP-1 lint pre-commit + CI：50.2 frontend / API 加 Loop 變體時自動驗 TAO 紀律

---

## Sprint 50.1 範疇成熟度提升

| 範疇 | Pre-50.1 | Post-50.1 | 備註 |
|------|---------|----------|------|
| 1. Orchestrator Loop | Level 0 | **Level 2** | 核心 loop 跑通；Level 3 需 50.2 接 API 主流量 |
| 6. Output Parser | Level 0 | **Level 3** | 完整 native tool_calling parse + 3-way classifier |
| 2. Tool Layer | Level 0 | **Level 1** | InMemoryToolRegistry stub；51.1 進 Level 3+ |
| 12. Observability | Level 1 | **Level 2** | 範疇 1 / 6 / 2 真實埋點 + Cat 12 coverage test |

---

## 下一步（Next session）

1. 用戶開新 session 時，**第一件事**：用 `claudedocs/6-ai-assistant/prompts/SITUATION-V2-SESSION-START.md` onboarding（注意：第八+九部分 Open Items / milestones table 需要 50.1 完成後同步更新）
2. 指示「啟動 Sprint 50.2 — API + Frontend 對接」
3. AI 助手依 rolling planning 建 `sprint-50-2-plan.md` + `sprint-50-2-checklist.md` 等用戶 approve 才 code

**用戶手動處理項**（從 49.x + 50.1 累積）：
- ⏸ GitHub branch protection rule（49.1 carry）— admin UI
- ⏸ 49.1+49.2+49.3+49.4+50.1 merge to main 決策（用戶決策）
- ⏸ npm audit 2 moderate vulnerabilities（49.1 carry）— 留待 frontend sprint
- ⏸ Production app role 在 staging 環境配置（per Day 5.2 guide）— Phase 53.1+
- ⏸ CI deploy gate 引入規範 E 警報（Production cutover Phase 55）
- ⏸ SITUATION-V2-SESSION-START.md 第八+九部分過期（49.2/49.3/49.4/50.1 milestones）— 待用戶或 AI 助手同步

---

**Last Updated**：2026-04-30 (Sprint 50.2 Day 0 started — plan + checklist committed)
**Maintainer**：用戶 + AI 助手共同維護
