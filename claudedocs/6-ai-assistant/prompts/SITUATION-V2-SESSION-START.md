# SITUATION V2 — Session Start Prompt（V2 重構期間每個新 session 必用）

> **用法**：在每個新 session 開始時，整份 copy 到對話框，**更新最後一節「今天的任務」一行即可**。其他段落是給 AI 助手的常駐脈絡，不必每次改。
>
> **適用範圍**：Phase 49+（V2 重構期間，預計 22 sprint / 5.5 個月）。完成 V2 後（Phase 56+）再決定是否退役此 prompt。

---

## 第一部分：你正在加入什麼專案

你好。本專案是 **IPA Platform V2**（Intelligent Process Automation Platform），目前正處於 **V2 重構期間**（Phase 49+，2026-04 啟動）。

### V2 為何存在（Why this rebirth）

V1（Phase 1-48）2025-11 至 2026-04 累積了 5 個月的開發，但 2026-04 V9 audit 發現：
- 真實對齊度只有 **27%**（11 範疇中 8 個 Level 0-2 — 不可用 / 半成品）
- Guardrails 散在 6 處、Orchestrator 散在 5 處（cross-directory scattering）
- Pipeline 偽裝成 Loop / 無 PromptBuilder / 無 Verification / Context Rot 完全忽略
- Hybrid 橋接層債務 + Potemkin Features（結構在但無內容）

→ 決策**重新出發**（不修補、不全砍）：保留 V9 分析 / CC 30-wave 研究 / V1 教訓作設計知識，從 Day 1 按 **agent harness 11+1 範疇**重新組織代碼。

### V2 不是什麼（避免常見誤解）

- ❌ **不是「Claude SDK 應用」** — V2 是 LLM Provider 中性的企業 agent 平台
- ❌ **不是「CC 移植」** — 參考 CC 架構但完全 server-side 重新設計
- ❌ **不是「本地工具升級版」** — V2 是企業 server-side，工具是企業 API/服務
- ❌ **不是「修補 V1」** — V1 已封存到 `archived/v1-phase1-48/`（READ-ONLY），不擴充
- ❌ **不是 SaaS-ready**（Phase 55 完成 ≠ SaaS-ready；SaaS Stage 1 在 Phase 56-58）

---

## 第二部分：3 大最高指導原則（不可違反）

詳見 `docs/03-implementation/agent-harness-planning/10-server-side-philosophy.md`。

### 原則 1：Server-Side First
- 部署在企業伺服器；用戶在遠端 browser；多租戶 + zero-trust
- 工具是**企業 API**（D365 / SAP / KB / SharePoint）— 不是本地檔案 read/write
- HITL 是核心，不是邊角

### 原則 2：LLM Provider Neutrality ⭐⭐⭐
- ❌ `agent_harness/**` 任何檔案禁止 `import openai` / `import anthropic` / `import agent_framework`
- ✅ 全走 `adapters/_base/ChatClient` ABC + 中性 ToolSpec / Message / StopReason
- CI 強制 lint 檢查；違反 = PR 直接 revert

### 原則 3：CC 參考但 Server-Side 轉化
- 概念複製、實作重寫
- CC `Bash tool` → 沙盒化 enterprise 命令；CC `Read/Write user files` → 企業 API；CC git checkpoint → DB state_snapshots
- 不照搬 CC 本地實作（multi-tenant 場景會出安全 / 性能問題）

---

## 第三部分：V2 11+1 範疇（架構骨架）

V2 嚴格按以下範疇組織代碼，**禁止跨範疇雜湊**：

| # | 範疇 | Phase 實作 |
|---|------|----------|
| 1 | Orchestrator Loop（TAO/ReAct）| 50.1 |
| 2 | Tool Layer | 51.1 |
| 3 | Memory（5 scope × 3 time scale）| 51.2 |
| 4 | Context Mgmt（Compaction + Prompt Caching）| 52.1 |
| 5 | Prompt Construction | 52.2 |
| 6 | Output Parsing | 50.1 |
| 7 | State Mgmt（Reducer + transient/durable）| 53.1 |
| 8 | Error Handling | 53.2 |
| 9 | Guardrails & Safety（含 Tripwire）| 53.3 + 53.4 |
| 10 | Verification Loops | 54.1 |
| 11 | Subagent Orchestration（4 模式，**無 worktree**）| 54.2 |
| **12** | **Observability / Tracing**（cross-cutting）| 49.4 起滲透所有 |

外加 `§HITL Centralization`（`agent_harness/hitl/`）— 跨範疇 2/7/8/9 的 HITL 統一管理。

完整 spec：`agent-harness-planning/01-eleven-categories-spec.md`。

---

## 第四部分：權威排序（衝突時上位者勝）

```
docs/03-implementation/agent-harness-planning/ (19 份 V2 規劃) > 根目錄 CLAUDE.md > .claude/rules/ > V1 文件
```

**任何衝突以上位者為準**。例如：V2 規劃說 `platform_layer/`，過期 V1 文件說 `platform/` → 用 V2 規劃。

---

## 第五部分：必讀文件（每次新 session 至少讀這 5 份）

依序讀完才能對齊上下文：

1. **本 prompt**（你正在讀）— 高層 onboarding
2. **`CLAUDE.md`**（專案根目錄，2026-04-28 V2 重寫版）— 高層導航 + V2 11+1 範疇 + 5 大核心約束 + Sprint Workflow
3. **`docs/03-implementation/agent-harness-planning/README.md`** — V2 規劃 19 份文件導覽
4. **`docs/03-implementation/agent-harness-planning/10-server-side-philosophy.md`** — 3 大最高指導原則完整論述
5. **`docs/03-implementation/agent-harness-planning/17-cross-category-interfaces.md`** — Single-source 介面權威表（24 dataclass + 19 ABC + 22 LoopEvent + 9 跨範疇工具）

按需要再讀：
- `04-anti-patterns.md`（V1 教訓 11 條反模式 — PR 必通檢查清單）
- `06-phase-roadmap.md`（22 sprint 路線圖）
- `.claude/rules/README.md`（13 份 V2 開發規則索引）

---

## 第六部分：Rolling Sprint Planning 規則（V2 紀律核心）⭐

> **這是 V2 最重要的工作節奏紀律，每次 session 都要記住**

V2 採用「**滾動式 sprint 規劃**」（per `.claude/rules/sprint-workflow.md`）：

### ✅ 正確做法

- **執行當前 sprint 期間（或結束時）**才寫**下一個** sprint 的 plan + checklist
- 每個 sprint 結束 retrospective 後，根據實作學習**微調**下一 sprint 設計
- Phase README + 06-phase-roadmap.md 提供高層綱要，**不是**完整 plan
- 完成 sprint plan + checklist 才開始 code（**禁止跳步**：Phase README → Plan → Checklist → Code → Update → Progress doc → Retrospective）

### ❌ 禁止做法

- **不**預寫全 22 個 sprint plan + checklist（過早決定 = 將來必返工）
- **不**「為了完整」而把 49.2 / 49.3 / 49.4 plan 一次寫齊（違反 rolling）
- **不**跳過 plan 直接 code（Phase 35-38 + 42 違規前車之鑑）
- **不**刪除未勾選的 checklist 項（只能 `[ ]→[x]`，延後項加 🚧 + reason）

### 為什麼是 rolling，不是預寫

1. 實作 sprint N 會學到東西，會影響 sprint N+1 的設計
2. 一次預寫 5 個 sprint plan，第 1 個跑完通常要改後 4 個
3. ROI 偏低 + 維護成本高
4. 標準業界做法

→ **每個新 session 開始時，AI 助手必須先確認 rolling planning 紀律仍在執行，沒有突然出現 5 個未來 sprint plan 文件。**

---

## 第七部分：當前進度（AI 自查，不需用戶手動更新）

新 session 開始時，AI 助手請用以下指令自查當前進度：

```bash
# 1. 看現在在哪個 branch
git branch --show-current

# 2. 看 main 最近的 commits（過去 sprint 痕跡）
git log main --oneline -20

# 3. 看當前 branch 的 commits（如果在 feature branch）
git log $(git branch --show-current) --oneline --not main

# 4. 看 working tree 是否乾淨
git status --short

# 5. 看 V2 sprint 規劃文件覆蓋（已寫了哪些 sprint）
ls docs/03-implementation/agent-harness-planning/phase-*

# 6. 看執行紀錄（已執行 / 收尾的 sprint）
ls docs/03-implementation/agent-harness-execution/

# 7. 讀最近收尾的 sprint retrospective（學該 sprint 的 open items + lessons）
# 路徑類似 docs/03-implementation/agent-harness-execution/phase-XX/sprint-XX-Y/retrospective.md
```

**讀完上述後**，AI 助手應該能回答：
- 目前在哪個 sprint？哪一天？
- 上一個收尾的 sprint 是哪個？有什麼 open items？
- 累計完成多少 sprint？離 Phase 55（V2 完成）還有多遠？

---

## 第八部分：常駐 Open Items / Follow-ups（每個 sprint 結束時更新）

> **這段需要每個 sprint 結束時用戶或 AI 添加。** 收尾時，把 retrospective.md 的「待改進」「Action items」精煉成下方一句話列表。

### 已知未解（at session start time）

- ⏸ **`platform/` rename 同步**：Sprint 49.1 Day 5 將 `backend/src/platform/` rename 為 `platform_layer/`（避免 stdlib shadow）。但 V2 規劃文件 `02-architecture-design.md` + `06-phase-roadmap.md` 仍寫 `platform/`，需在 Sprint 49.2+ 同步更新
- ⏸ **branch protection rule**：用戶尚未在 GitHub UI 設定 main 分支必須 CI green 才可 merge
- ⏸ **CI lint** 防 `platform` package 重新引入：未實作；建議 Sprint 49.4 lint rules 一併補
- ⏸ **agent-harness-planning/README.md「Sprint 49.2 已啟動」更新**：等 49.2 plan 寫了再改
- ⏸ **真實 dev server 手動驗證**：用戶尚未親跑 `uvicorn` + `npm run dev` 確認瀏覽器端可看 placeholder pages
- ⏸ **npm audit 2 moderate vulnerabilities**：transitive deps，後續 sprint 處理
- ⏸ **Sprint 181 deferred**（V1 work）：`completeness folder` + `guided_dialog migration` 在 V1 archive 內未完成 — 已記錄於 `archived/v1-phase1-48/README.md`，V2 不會繼承（不需處理）

> **AI 助手任務**：每個新 sprint 開始時，先看本 prompt 此節 + 上 sprint 的 retrospective.md 「Action items」，向用戶確認哪些 follow-up 要在這個 sprint 處理，哪些繼續延後。

---

## 第九部分：常駐 milestones（V2 累計完成）

> **每個 sprint 結束更新一行**

| Sprint | 完成日期 | Branch / Commits | 主要成果 |
|--------|---------|----------------|---------|
| **49.1** | 2026-04-29 | `feature/phase-49-sprint-1-v2-foundation`（13 commits, pushed）| V1 archive + V2 5-layer skeleton + 11+1 ABC stubs + _contracts + ChatClient ABC + frontend skeleton + Docker + CI + ESLint + test_imports |
| 49.2 | _pending_ | _pending_ | DB Schema + Async ORM |
| 49.3 | _pending_ | _pending_ | RLS + Audit + Adapter (Azure OpenAI) |
| 49.4 | _pending_ | _pending_ | Worker queue PoC + OTel + Lint rules |
| Phase 50-55 | _pending_ | _pending_ | 18 sprints across 6 phases |

**累計**：1 / 22 sprint 完成（Phase 49 1/4，Phase 50-55 全 0）

---

## 第十部分：行為規範（給 AI 助手）

每次回應前，AI 助手請確保：

### 必做

- [ ] 對齐 3 大最高指導原則（server-side / LLM neutrality / CC reference）
- [ ] 不引入新 LLM SDK 直接 import 進 `agent_harness/**`
- [ ] 不刪除未勾選的 checklist 項（只能 `[ ]→[x]` 或加 🚧）
- [ ] 跨範疇型別從 `agent_harness._contracts/` import（不重複定義）
- [ ] 開始 code 前確認該 sprint 已有 plan + checklist
- [ ] 寫 commit message 用 Conventional Commits 格式（per `.claude/rules/git-workflow.md`）+ co-author
- [ ] 每個 commit 對應一個 checklist 項目
- [ ] 維持每天 progress.md 紀錄（estimates vs actual）
- [ ] sprint 結束寫 retrospective.md（5 必述：outcome / estimates / went-well / surprises / Action items）

### 不做

- [ ] 不預寫多個未來 sprint plan（rolling planning！）
- [ ] 不刪除 V1 archive 內任何檔案（archived/v1-phase1-48/ 是 read-only baseline）
- [ ] 不讓 AI 助手單方面決定不可逆操作（git tag push / git mv 大量檔案）— 必須先報告
- [ ] 不執行 `--no-verify` / `--force` git 命令（除非用戶明確授權）
- [ ] 不啟動長期運行 server process（CLAUDE.md 規範：節點 process 與 claude code 衝突）

---

## 第十一部分：今天的任務（**唯一需要用戶填寫的部分**）

> 在每個新 session 開始時，把整份 prompt copy 後，只改下方這一節即可。

```
今天的任務：__________________

例：
- 「啟動 Sprint 49.2 — DB Schema + Async ORM」
  → AI 將先寫 `phase-49-foundation/sprint-49-2-plan.md` + `sprint-49-2-checklist.md`，等用戶 approve 才開始 code
- 「繼續 Sprint 49.2 Day 3」
  → AI 接續執行 Day 3 任務（先讀 progress.md 確認 Day 1-2 完成情況）
- 「修復 Sprint 49.1 follow-up：rename platform/ in V2 規劃文件」
  → AI 處理 Open Items 中的 `platform/` rename 同步
- 「Review Sprint 49.1 retrospective + 規劃 Sprint 49.2 plan」
  → AI 讀 retrospective.md 後與用戶討論 49.2 範圍 + 寫 plan
- 「建立第 8 個 SITUATION prompt」
  → AI 按用戶需求建立 / 修改 prompt 模板
```

---

## 附錄：本 prompt 自身的維護

### 何時更新

| 觸發 | 更新位置 |
|------|---------|
| Sprint 結束 | 第八部分 Open Items（合併 retrospective Action items）+ 第九部分 milestones（加一行）|
| 發現 V2 規劃修訂（17.md / 02 / 04 / 10 等）| 第三部分（11+1 範疇）+ 第四部分（權威排序）+ 第五部分（必讀清單）|
| Phase 切換（如 Phase 49 → 50）| 第七部分（自查指令）+ 第九部分（milestones）|

### 何時退役

V2 完成（Phase 55 後）→ 此 prompt 變歷史紀念物，改用 V3 / SaaS Stage 1 對應 prompt（如有）。

---

**Last Updated**: 2026-04-29（Sprint 49.1 完成後初版）
**Maintainer**: 用戶 + AI 助手共同維護
**File location**: `claudedocs/6-ai-assistant/prompts/SITUATION-V2-SESSION-START.md`
