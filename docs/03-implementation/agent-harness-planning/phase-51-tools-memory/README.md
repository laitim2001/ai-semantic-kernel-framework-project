# Phase 51 — Tools + Memory

**Phase 進度**：Sprint 51.0 🟡 PLANNING（plan + checklist 待用戶 approve）/ Sprint 51.1 ⏸ 未啟動 / Sprint 51.2 ⏸ 未啟動 — **0 / 3 sprint complete（0%）**
**啟動日期**：2026-04-30（接 Phase 50 closeout）
**狀態**：🟡 Phase 51 啟動中 — Sprint 51.0 plan/checklist 已就緒，等用戶 approve 才 code

---

## Phase 51 目標

> **Phase 51 是 demo 基礎設施 + 範疇 2/3 核心**（per `06-phase-roadmap.md` §Phase 51）。
> 本 phase 完成後：
> - 範疇 2（Tools）達 Level 3（51.1）
> - 範疇 3（Memory）達 Level 3（51.2）
> - 5 業務 domain 有 mock backend，52-54 demo 不再用 echo_tool（51.0）

詳細路線圖見 [`../06-phase-roadmap.md` §Phase 51](../06-phase-roadmap.md#phase-51-tools--memory3-sprint-原-2)。

---

## Sprint 進度總覽

| Sprint | 狀態 | 主題 | 完成日期 | Branch / Commits |
|--------|------|------|---------|------------------|
| **51.0** | 🟡 PLANNING | Mock 企業工具 + 業務工具骨架（**新增 sprint**） | TBD | TBD |
| **51.1** | ⏸ 待啟動 | 範疇 2 工具層（Level 3） | TBD | TBD |
| **51.2** | ⏸ 待啟動 | 範疇 3 記憶層（Level 3） | TBD | TBD |

---

## Sprint 文件導航

```
phase-51-tools-memory/
├── README.md                          ← (this file) Phase 51 入口
├── sprint-51-0-plan.md                🟡 PLANNING（待用戶 approve）
├── sprint-51-0-checklist.md           🟡 PLANNING
├── sprint-51-1-plan.md                ⏸ 51.0 closeout 後 rolling 寫
├── sprint-51-1-checklist.md           ⏸ 同上
├── sprint-51-2-plan.md                ⏸ 51.1 closeout 後 rolling 寫
└── sprint-51-2-checklist.md           ⏸ 同上
```

執行紀錄（51.0 啟動後建立）：
```
docs/03-implementation/agent-harness-execution/phase-51/
└── sprint-51-0/{progress,retrospective}.md
```

---

## 範疇成熟度演進（規劃）

| 範疇 | Pre-51.0 | Post-51.0 | Post-51.1 | Post-51.2 |
|------|---------|----------|----------|-----------|
| 1. Orchestrator Loop | Level 3 | Level 3 | Level 3 | Level 3 |
| 2. Tool Layer | Level 1 | Level 1+ | **Level 3** | Level 3 |
| 3. Memory | Level 0 | Level 0 | Level 0 | **Level 3** |
| 6. Output Parser | Level 4 | Level 4 | Level 4 | Level 4 |
| 12. Observability | Level 2 | Level 2 | Level 2 | Level 2 |

> Sprint 51.0 不直接提升範疇 2/3 等級，但**解鎖 51.1+ 的 demo 場景**：移除 echo_tool 依賴，讓 52-54 sprint 有真實業務工具可呼叫。

---

## Sprint 51.0 範圍預覽

**核心交付（per Sprint 51.0 plan）**：
- 5 業務 domain 各 1 個 `tools.py`（含 `register_<domain>_tools(registry)` 入口）
- 18 個業務 ToolSpec stub（指向 mock backend HTTP endpoint）
- Mock backend FastAPI 子服務（CRM / KB / 5 domain 的 mock 資料路由）
- Mock data seed（10 customer / 50 order / 20 alert / 5 incident）
- e2e demo：agent loop 呼叫 `mock_patrol_check_servers` 拿到 mock 結果

**範疇歸屬**：
- 18 ToolSpec 在 `business_domain/` — 業務領域層（per `08b-business-tools-spec.md`）
- Mock backend 在 `mock_services/` — 平台輔助層（測試與 demo 用，**非 production**）
- ToolRegistry 持續用 50.1 `InMemoryToolRegistry`（51.1 升級為 Level 3）

> **與 spec 差異**：roadmap 寫「24 個工具」，08b spec 列 **18 個**（4+3+3+3+5）。51.0 採 spec 為準，差異記入 retrospective.md。

---

## Phase 51 結束驗收（per 51.0 + 51.1 + 51.2）

- ✅ Tool layer 三大能力齊備：registry / spec / executor / sandbox / permissions（51.1）
- ✅ 5 層記憶獨立可測 + tenant 隔離（51.2）
- ✅ Agent 可主動呼叫 memory_search + 業務工具混合運作（51.2）
- ✅ 「線索→驗證」工作流範例（51.2）
- ✅ 第二個 demo 案例「memory_search 找過去資料 + 用工具驗證」可跑（51.2）
- ✅ 不再有 echo_tool dependency（51.0 起）

---

## 下一步

1. **用戶 review**：sprint-51-0-plan.md + sprint-51-0-checklist.md
2. **approve 後**：AI 助手執行 Sprint 51.0 Day 0（建 branch + commit plan/checklist）
3. **51.0 closeout 後**：再 rolling 建 sprint-51-1-plan.md + checklist（**禁止預寫**）

---

**Last Updated**：2026-04-30 (Sprint 51.0 planning 啟動)
**Maintainer**：用戶 + AI 助手共同維護
