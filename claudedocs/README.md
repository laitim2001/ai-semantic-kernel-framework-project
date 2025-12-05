# Claude 輔助文檔索引 (Claude Docs) - V2.0

> **目的**: AI 助手生成的分析、規劃和實施文檔，用於輔助 IPA Platform 開發過程
> **特性**: 流程導向、時間序列化、階段性文檔
> **與 docs/ 的區別**: docs/ 是正式團隊文檔，claudedocs/ 是 AI 生成的工作文檔
> **最後更新**: 2025-12-05
> **新架構**: 數字編號體現開發流程自然順序 (規劃→執行→追蹤→變更→總結→輔助→歸檔)

---

## 專案狀態概覽

| 階段 | Sprint | 點數 | 狀態 |
|------|--------|------|------|
| **Phase 1 (MVP)** | Sprint 0-6 | 285 | ✅ 已完成 |
| **Phase 2 (進階功能)** | Sprint 7-12 | 222 | ⏳ 待開發 |
| **總計** | 12 Sprints | 507 | 進行中 |

---

## V2.0 文檔結構 (流程導向)

```
claudedocs/
├── 1-planning/          # 總體規劃 (開始階段)
│   ├── roadmap/         # 路線圖和時間線
│   ├── epics/           # Phase 詳細規劃
│   │   ├── phase-1/     # Phase 1 MVP 規劃
│   │   └── phase-2/     # Phase 2 進階功能規劃
│   ├── features/        # 功能規劃 (FEAT-XXX-name/)
│   └── architecture/    # 架構設計決策
│
├── 2-sprints/           # Sprint 執行文檔 (執行階段)
│   ├── phase-1/         # Phase 1 Sprint 文檔 (S0-S6)
│   ├── phase-2/         # Phase 2 Sprint 文檔 (S7-S12)
│   └── templates/       # Sprint 模板
│
├── 3-progress/          # 進度追蹤 (持續監控)
│   ├── weekly/          # 每週進度記錄
│   ├── daily/           # 每日開發日誌
│   ├── milestones/      # 里程碑達成記錄
│   └── templates/       # 進度追蹤模板
│
├── 4-changes/           # 變更記錄 (應對變化)
│   ├── bug-fixes/       # Bug 修復記錄 (FIX-XXX.md)
│   ├── feature-changes/ # 功能變更記錄 (CHANGE-XXX.md)
│   ├── refactoring/     # 重構記錄 (REFACTOR-XXX.md)
│   └── templates/       # 變更記錄模板
│
├── 5-status/            # 狀態報告 (階段總結)
│   ├── phase-reports/   # 階段/Sprint 完成報告
│   ├── testing/         # 測試報告
│   └── quality/         # 品質報告、Code Review
│
├── 6-ai-assistant/      # AI 助手指引 (輔助工具)
│   ├── prompts/         # Prompt 模板 (PROMPT-01 ~ PROMPT-09)
│   ├── session-guides/  # 會話指引
│   ├── analysis/        # AI 分析報告
│   └── handoff/         # 階段交接文檔
│
└── 7-archive/           # 歷史歸檔 (完成後)
    ├── phase-1-mvp/     # Phase 1 MVP 已完成文檔
    └── session-logs/    # 歷史會話記錄
```

---

## 開發情況快速導航

根據你當前的開發情況，選擇對應的 Prompt：

| 情況 | 描述 | Prompt |
|------|------|--------|
| **專案入門** | 首次接觸或長時間未參與 | [PROMPT-01](./6-ai-assistant/prompts/PROMPT-01-PROJECT-ONBOARDING.md) |
| **新任務準備** | 準備開發新功能 | [PROMPT-02](./6-ai-assistant/prompts/PROMPT-02-NEW-SPRINT-PREP.md) |
| **Bug 修復準備** | 準備修復 Bug | [PROMPT-03](./6-ai-assistant/prompts/PROMPT-03-BUG-FIX-PREP.md) |
| **開發執行** | 執行開發任務 | [PROMPT-04](./6-ai-assistant/prompts/PROMPT-04-SPRINT-DEVELOPMENT.md) |
| **測試階段** | 執行測試驗證 | [PROMPT-05](./6-ai-assistant/prompts/PROMPT-05-TESTING-PHASE.md) |
| **保存進度** | 保存工作進度 | [PROMPT-06](./6-ai-assistant/prompts/PROMPT-06-PROGRESS-SAVE.md) |
| **架構審查** | 審查架構設計 | [PROMPT-07](./6-ai-assistant/prompts/PROMPT-07-ARCHITECTURE-REVIEW.md) |
| **代碼審查** | 審查代碼品質 | [PROMPT-08](./6-ai-assistant/prompts/PROMPT-08-CODE-REVIEW.md) |
| **會話結束** | 結束開發會話 | [PROMPT-09](./6-ai-assistant/prompts/PROMPT-09-SESSION-END.md) |

### 開發流程概覽

```
專案入門 (PROMPT-01)
    │
    ▼
準備階段 (PROMPT-02/03) ──────────────┐
    │                                 │
    ▼                                 ▼
開發執行 (PROMPT-04)           Bug 修復 (PROMPT-03→04)
    │                                 │
    ▼                                 │
測試階段 (PROMPT-05)                  │
    │                                 │
    └──────────────┬──────────────────┘
                   │
                   ▼
           保存進度 (PROMPT-06)
                   │
                   ▼
           會話結束 (PROMPT-09)
```

---

## 各目錄詳細說明

### 1-planning/ (總體規劃)

**用途**: 存放**高層次規劃文檔**，為開發提供方向和藍圖

**子目錄**:
- `roadmap/` - MASTER-ROADMAP.md, MILESTONE-TIMELINE.md
- `epics/phase-1/` - Phase 1 MVP 概覽、需求
- `epics/phase-2/` - Phase 2 進階功能概覽、需求
- `features/` - 功能規劃目錄 (FEAT-XXX-name/)
- `architecture/` - 技術決策記錄 (ADR)、API 設計原則

**功能規劃結構**:
```
1-planning/features/
├── FEAT-001-concurrent-executor/
│   ├── 01-requirements.md
│   ├── 02-technical-design.md
│   ├── 03-implementation-plan.md
│   └── 04-progress.md
└── FEAT-002-handoff-controller/
    └── ...
```

**當前文件**:
- `epics/phase-2/PHASE-2-OVERVIEW.md` - Phase 2 進階功能概覽

---

### 2-sprints/ (Sprint 執行文檔)

**用途**: 存放**Sprint 執行期間的詳細任務和計劃**

**子目錄**:
- `phase-1/sprint-X/` - Sprint 計劃、任務、回顧、checklist
- `phase-2/sprint-X/` - (同上)
- `templates/` - Sprint 計劃、任務、回顧模板

**Phase 1 Sprints** (✅ 已完成):
| Sprint | 主題 | 點數 |
|--------|------|------|
| S0 | 專案初始化 | 21 |
| S1 | Agent Core | 55 |
| S2 | Workflow Engine | 55 |
| S3 | Human-in-the-loop | 42 |
| S4 | 連接器與路由 | 50 |
| S5 | 知識與學習 | 34 |
| S6 | 系統整合 | 28 |

**Phase 2 Sprints** (⏳ 待開發):
| Sprint | 主題 | 點數 |
|--------|------|------|
| S7 | 並行執行引擎 | 34 |
| S8 | 智能交接機制 | 31 |
| S9 | 群組協作模式 | 42 |
| S10 | 動態規劃引擎 | 42 |
| S11 | 嵌套工作流 | 39 |
| S12 | 整合與優化 | 34 |

---

### 3-progress/ (進度追蹤)

**用途**: 持續記錄**開發進度和狀態**

**子目錄**:
- `weekly/` - 每週進度摘要 (2025-WXX.md)
- `daily/` - 每日開發日誌 (2025-MM-DD.md)
- `milestones/` - 里程碑達成記錄

**使用指引**:
- 每週五更新 `weekly/2025-WXX.md`
- 每日更新 `daily/2025-MM-DD.md` (可選)
- 達成里程碑時創建 `milestones/MX-xxx-complete.md`

---

### 4-changes/ (變更記錄)

**用途**: 記錄**所有變更、修正和重構**

**子目錄**:
- `bug-fixes/` - Bug 修復文件 (FIX-XXX.md)
- `feature-changes/` - 功能變更記錄
- `refactoring/` - 重構記錄

---

### 5-status/ (狀態報告)

**用途**: 階段性的**狀態總結和品質報告**

**子目錄**:
- `phase-reports/` - Sprint/Phase 完成報告
- `testing/` - 測試報告 (e2e, unit, integration)
- `quality/` - 品質報告、Code Review

**當前文件**:
- `phase-reports/sprint-0-completion-report.md`
- `phase-reports/sprint-3-completion-report.md`
- `quality/code-review/sprint-0-architecture-review.md`

---

### 6-ai-assistant/ (AI 助手指引)

**用途**: 幫助 AI 助手**快速理解專案狀態和繼續工作**

**子目錄**:
- `prompts/` - Prompt 模板 (PROMPT-01 ~ PROMPT-09)
- `prompts/Example/` - 參考範例 (開發情況指引)
- `session-guides/` - 會話指引
- `analysis/` - AI 分析報告
- `handoff/` - 階段交接文檔

**Prompt 模板**:
| 編號 | 名稱 | 用途 |
|------|------|------|
| PROMPT-01 | PROJECT-ONBOARDING | 專案入門 |
| PROMPT-02 | NEW-SPRINT-PREP | 新任務準備 |
| PROMPT-03 | BUG-FIX-PREP | Bug 修復準備 |
| PROMPT-04 | SPRINT-DEVELOPMENT | 開發執行 |
| PROMPT-05 | TESTING-PHASE | 測試階段 |
| PROMPT-06 | PROGRESS-SAVE | 進度保存 |
| PROMPT-07 | ARCHITECTURE-REVIEW | 架構審查 |
| PROMPT-08 | CODE-REVIEW | 代碼審查 |
| PROMPT-09 | SESSION-END | 會話結束 |

**參考範例 (Example/)**:
- `SITUATION-2-FEATURE-DEV-PREP.md` - 功能開發前準備指引
- `SITUATION-3-FEATURE-ENHANCEMENT.md` - 功能增強/修復指引
- `SITUATION-4-NEW-FEATURE-DEV.md` - 新功能開發指引

---

### 7-archive/ (歷史歸檔)

**用途**: 存放**已完成階段的文檔**，保持活躍目錄的整潔

**子目錄**:
- `phase-1-mvp/` - Phase 1 MVP 已完成文檔
- `session-logs/` - 歷史會話記錄

---

## 文檔生命週期

```
1. 創建階段:
   規劃文檔: 1-planning/
   Sprint 文檔: 2-sprints/

2. 活躍維護:
   進度追蹤: 3-progress/ (每日/每週更新)
   變更記錄: 4-changes/ (持續新增)

3. 階段總結:
   狀態報告: 5-status/ (Sprint/Phase 結束時)

4. 歸檔:
   已完成文檔: 7-archive/ (Phase 完成後)
```

---

## 快速導航指南

### 我想了解...

| 需求 | 查看目錄 |
|------|---------|
| **專案總體規劃** | `1-planning/roadmap/` |
| **Phase 2 詳細規劃** | `1-planning/epics/phase-2/` |
| **當前 Sprint 任務** | `2-sprints/phase-X/sprint-X/` |
| **本週開發進度** | `3-progress/weekly/` |
| **最近的 Bug 修復** | `4-changes/bug-fixes/` |
| **Sprint 完成報告** | `5-status/phase-reports/` |
| **如何開始新 Sprint** | `6-ai-assistant/prompts/PROMPT-02` |
| **已完成的 Phase 1** | `7-archive/phase-1-mvp/` |

---

## 文檔命名規範

### 通用規則
- **UPPERCASE**: 重要的總覽文檔 (MASTER-ROADMAP.md)
- **kebab-case**: 詳細文檔 (sprint-7-plan.md)
- **有意義的前綴**: FIX-XXX, CHANGE-XXX, REFACTOR-XXX
- **日期格式**: ISO 格式 (2025-12-05.md, 2025-W49.md)

### 各類文檔命名範例
```bash
# 規劃文檔
1-planning/roadmap/MASTER-ROADMAP.md
1-planning/epics/phase-2/phase-2-overview.md

# Sprint 文檔
2-sprints/phase-2/sprint-7/SPRINT-7-PLAN.md
2-sprints/phase-2/sprint-7/checklist.md

# 進度追蹤
3-progress/weekly/2025-W49.md
3-progress/daily/2025-12-05.md

# 變更記錄
4-changes/bug-fixes/FIX-001-api-response.md

# 狀態報告
5-status/phase-reports/PHASE-1-COMPLETE.md
5-status/testing/e2e-test-report.md
```

---

## 與 docs/ 的區別

| 特性 | claudedocs/ | docs/ |
|------|-------------|-------|
| **性質** | AI 生成的工作文檔 | 正式團隊文檔 |
| **目的** | 輔助開發過程、分析問題、規劃任務 | 長期保存、團隊協作、正式文檔 |
| **生命週期** | 臨時性、階段性 | 永久性、持續維護 |
| **受眾** | AI 助手、開發者（短期參考） | 全體團隊、新成員、外部協作者 |
| **維護頻率** | 任務完成後可歸檔 | 持續更新 |
| **架構** | 流程導向（1-7 數字編號） | 內容導向（prd, stories, architecture） |

---

## V2.0 架構優勢

### 1. 流程清晰
- 數字編號體現開發流程: 規劃 → 執行 → 追蹤 → 變更 → 總結 → 輔助 → 歸檔
- 新開發者和 AI 助手可以快速理解當前階段

### 2. 易於維護
- 每個階段的文檔職責明確
- 歸檔策略清晰，避免文檔膨脹

### 3. AI 友善
- `6-ai-assistant/` 集中了所有 AI 輔助文檔
- Prompts 模板提高一致性
- Session guides 幫助 AI 快速上手

### 4. 擴展性強
- 新增階段可以插入數字編號
- 子目錄結構靈活可調整

### 5. 時間序列化
- `3-progress/` 按時間組織，便於追蹤歷史
- 里程碑記錄清晰標記重要節點

---

## 維護計劃

### 每日維護
- 更新 `3-progress/daily/2025-MM-DD.md` (開發日誌)
- 更新 `2-sprints/phase-X/sprint-X/checklist.md` (完成的任務打勾)

### 每週維護
- 更新 `3-progress/weekly/2025-WXX.md` (每週進度摘要)
- 檢查 `4-changes/` (記錄修正和變更)

### Sprint 結束維護
- 完成 `2-sprints/phase-X/sprint-X/SPRINT-X-RETRO.md` (Sprint 回顧)
- 更新 `3-progress/milestones/` (里程碑記錄)

### Phase 結束維護
- 生成 `5-status/phase-reports/PHASE-X-COMPLETE.md` (階段報告)
- 歸檔已完成文檔到 `7-archive/`

---

## 統計數據

**V2.0 更新統計** (2025-12-05):
- **總文件數**: ~30 個
- **1-planning/**: 1 個 (Phase 2 Overview)
- **2-sprints/**: 1 個模板
- **3-progress/**: 1 個模板
- **4-changes/**: 1 個模板
- **5-status/**: 3 個文件 (2 phase-reports + 1 code-review)
- **6-ai-assistant/**: 14 個文件 (10 prompts + 3 examples + 1 instructions)
- **7-archive/**: 4 個文件 (3 session-logs + 1 Phase 1 summary)

---

## 相關文檔

### 核心文檔
- [AI-ASSISTANT-INSTRUCTIONS.md](./6-ai-assistant/AI-ASSISTANT-INSTRUCTIONS.md) - AI 助手使用指南
- [CLAUDE.md](../CLAUDE.md) - 專案主要指引文件
- [docs/](../docs/) - 正式團隊文檔

### Prompt 模板
- [Prompts README](./6-ai-assistant/prompts/README.md) - Prompt 總覽
- [PROMPT-01: 專案入門](./6-ai-assistant/prompts/PROMPT-01-PROJECT-ONBOARDING.md)
- [PROMPT-02: 新任務準備](./6-ai-assistant/prompts/PROMPT-02-NEW-SPRINT-PREP.md)
- [PROMPT-04: 開發執行](./6-ai-assistant/prompts/PROMPT-04-SPRINT-DEVELOPMENT.md)
- [PROMPT-06: 進度保存](./6-ai-assistant/prompts/PROMPT-06-PROGRESS-SAVE.md)

### Phase 規劃
- [Phase 2 概覽](./1-planning/epics/phase-2/PHASE-2-OVERVIEW.md)
- [Phase 1 總結](./7-archive/phase-1-mvp/PHASE-1-SUMMARY.md)

---

**維護者**: AI 助手 + 開發團隊
**版本**: V2.0 (流程導向)
**創建日期**: 2025-12-05
**最後更新**: 2025-12-05
