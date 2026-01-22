# ClaudeDocs - AI 助手文檔目錄

> **相關規則**: 請參閱 `.claude/rules/` 獲取文檔撰寫的完整規範

## 📋 目錄用途

此目錄是 AI 助手（Claude）與開發團隊協作產出的項目文檔中心，採用結構化的 7 層分類方式組織，涵蓋從規劃、開發到維運的完整生命週期文檔。這些文檔用於：

- **項目規劃**: Phase/Sprint 架構設計、功能規劃、路線圖
- **進度追蹤**: 每日/每週進度報告、Sprint 計劃
- **變更管理**: Bug 修復記錄、功能變更追蹤
- **AI 協作**: 情境提示詞、工作流程指南、分析報告
- **知識傳承**: 開發經驗、故障排查、部署指南

---

## 🎯 項目概覽 - IPA Platform

### 核心目標
- **平台定位**: 企業級 AI Agent 編排管理平台 (Intelligent Process Automation)
- **核心框架**: Microsoft Agent Framework + Claude Agent SDK + AG-UI Protocol
- **目標用戶**: IT 運維團隊、客戶服務團隊
- **商業價值**: IT 處理時間節省 40%+，12 個月 ROI > 200%

### 核心架構 - 三層意圖路由系統

```
┌─────────────────────────────────────────────────────────────────┐
│ TIER 1: Pattern Matcher（模式匹配）                              │
│ • 基於正則表達式快速匹配已知模式                                 │
├─────────────────────────────────────────────────────────────────┤
│ TIER 2: Semantic Router（語義路由）                              │
│ • 使用 Embedding 進行語義相似度匹配                              │
├─────────────────────────────────────────────────────────────────┤
│ TIER 3: LLM Classifier（智能分類）                               │
│ • 當以上都無法匹配時，使用 LLM 進行意圖分類                      │
└─────────────────────────────────────────────────────────────────┘
```

### 風險評估路由機制

| 風險等級 | 處理方式 | 說明 |
|----------|---------|------|
| LOW | AUTO_APPROVE | 自動通過，無需人工介入 |
| MEDIUM | QUICK_REVIEW | 快速人工確認 |
| HIGH | FULL_REVIEW | 完整人工審核 |
| CRITICAL | MANUAL_ONLY | 必須人工操作 |

---

## 🏗️ 目錄結構詳解

```
claudedocs/
├── 1-planning/                  # 規劃文檔
│   ├── architecture/            # 架構設計文檔
│   ├── epics/                   # Phase 規劃
│   │   ├── phase-1/             # Phase 1 基礎建設
│   │   ├── phase-2/             # Phase 2 並行執行引擎
│   │   └── ... (phase-3 ~ phase-28)
│   ├── features/                # Feature 規劃
│   └── roadmap/                 # 產品路線圖
│
├── 2-sprints/                   # Sprint 文檔
│   ├── phase-1/                 # Phase 1 Sprint 文檔
│   ├── phase-2/                 # Phase 2 Sprint 文檔
│   └── templates/               # Sprint 模板
│
├── 3-progress/                  # 進度追蹤
│   ├── daily/                   # 每日進度
│   ├── weekly/                  # 每週進度報告
│   ├── milestones/              # 里程碑記錄
│   └── templates/               # 進度追蹤模板
│
├── 4-changes/                   # 變更記錄
│   ├── bug-fixes/               # Bug 修復記錄 (FIX-*)
│   ├── feature-changes/         # 功能變更記錄 (CHANGE-*)
│   ├── refactoring/             # 重構記錄 (REFACTOR-*)
│   └── templates/               # 變更記錄模板
│
├── 5-status/                    # 狀態報告
│   ├── phase-reports/           # Phase 完成報告
│   ├── testing/                 # 測試文檔
│   └── quality/                 # 品質報告、Code Review
│
├── 6-ai-assistant/              # AI 助手相關
│   ├── analysis/                # 分析報告
│   ├── prompts/                 # 情境提示詞 (SITUATION-*)
│   │   ├── SITUATION-1-PROJECT-ONBOARDING.md   # 項目入門
│   │   ├── SITUATION-2-FEATURE-DEV-PREP.md     # 功能開發準備
│   │   ├── SITUATION-3-FEATURE-ENHANCEMENT.md  # 功能增強
│   │   ├── SITUATION-4-NEW-FEATURE-DEV.md      # 新功能開發
│   │   ├── SITUATION-5-SAVE-PROGRESS.md        # 保存進度
│   │   ├── SITUATION-6-SERVICE-STARTUP.md      # 服務啟動
│   │   └── SITUATION-7-NEW-ENV-SETUP.md        # 新環境設置
│   ├── session-guides/          # 會話指南
│   ├── changelogs/              # 變更日誌
│   └── handoff/                 # 階段交接文檔
│
├── 7-archive/                   # 歸檔文檔
│   ├── phase-1-mvp/             # Phase 1 已完成文檔
│   └── session-logs/            # 歷史會話記錄
│
├── CLAUDE.md                    # 本文件 - 目錄索引
└── README.md                    # 目錄說明
```

---

## 📊 項目進度追蹤

### Phase 完成狀態 (2026-01-22)

| Phase | 名稱 | Sprints | Story Points | 狀態 |
|-------|------|---------|--------------|------|
| Phase 1 | 基礎建設 | 1-6 | ~90 pts | ✅ 已完成 |
| Phase 2 | 並行執行引擎 | 7-12 | ~90 pts | ✅ 已完成 |
| Phase 3 | Official API Migration | 13-18 | ~105 pts | ✅ 已完成 |
| Phase 4 | Advanced Adapters | 19-24 | ~105 pts | ✅ 已完成 |
| Phase 5 | Connector Ecosystem | 25-27 | ~75 pts | ✅ 已完成 |
| Phase 6 | Enterprise Integration | 28-30 | ~75 pts | ✅ 已完成 |
| Phase 7 | Multi-turn & Memory | 31-33 | ~90 pts | ✅ 已完成 |
| Phase 8 | Code Interpreter | 34-36 | ~90 pts | ✅ 已完成 |
| Phase 9 | MCP Integration | 37-39 | ~90 pts | ✅ 已完成 |
| Phase 10 | MCP Expansion | 40-44 | ~105 pts | ✅ 已完成 |
| Phase 11 | Agent-Session Integration | 45-47 | ~90 pts | ✅ 已完成 |
| Phase 12 | Claude Agent SDK | 48-51 | 165 pts | ✅ 已完成 |
| Phase 13 | Hybrid Core Architecture | 52-54 | 105 pts | ✅ 已完成 |
| Phase 14 | Advanced Hybrid Features | 55-57 | 95 pts | ✅ 已完成 |
| Phase 15 | AG-UI Protocol Integration | 58-60 | 85 pts | ✅ 已完成 |
| Phase 16 | Unified Agentic Chat | 61-65 | 100 pts | ✅ 已完成 |
| Phase 17 | DevTools Backend API | 66-68 | 72 pts | ✅ 已完成 |
| Phase 18 | Session Management | 69-70 | 46 pts | ✅ 已完成 |
| Phase 19 | Autonomous Agent | 71-72 | 48 pts | ✅ 已完成 |
| Phase 20 | File Attachment Support | 73-76 | 60 pts | ✅ 已完成 |
| Phase 21 | Sandbox Security | 77-78 | 48 pts | ✅ 已完成 |
| Phase 22 | mem0 Core Implementation | 79-80 | 54 pts | ✅ 已完成 |
| Phase 23 | Performance Optimization | 81-82 | 48 pts | ✅ 已完成 |
| Phase 24 | Production Deployment | 83-84 | 48 pts | ✅ 已完成 |
| Phase 25 | Production Expansion | 85-86 | 45 pts | ✅ 已完成 |
| Phase 26 | DevUI Frontend | 87-89 | 42 pts | ✅ 已完成 |
| Phase 27 | mem0 整合完善 | 90 | 13 pts | ✅ 已完成 |
| Phase 28 | 三層意圖路由 | 91-99 | 235 pts | ✅ 已完成 |

**總計**: 2189 Story Points across 99 Sprints (28 Phases)

### 最新 Bug 修復 (Sprint 99)

| 編號 | 名稱 | 狀態 |
|------|------|------|
| FIX-001 | HITL 審批 API 使用錯誤的 ID 類型 | ✅ 已修復 |
| FIX-002 | 過期的審批請求阻擋新審批 | ✅ 已修復 |
| FIX-003 | 審批操作後卡片消失無歷史記錄 | ✅ 已修復 |
| FIX-004 | 審批請求出現時無自動滾動 | ✅ 已修復 |

### 最新功能變更 (Sprint 99)

| 編號 | 名稱 | 狀態 |
|------|------|------|
| CHANGE-001 | HITL 審批改為內嵌式訊息卡片 | ✅ 已完成 |

---

## 📝 文檔命名約定

### Phase/Sprint 規劃
```
claudedocs/1-planning/epics/
├── phase-{N}/
│   ├── README.md               # Phase 概述
│   ├── architecture.md         # 技術架構
│   └── stories.md              # User Stories 列表
```

### 功能變更 (CHANGE-*)
```
claudedocs/4-changes/feature-changes/
└── CHANGE-{NNN}-{description}.md
```

**標準 CHANGE 文檔結構**:
```markdown
# CHANGE-{NNN}: {Change Title}

**變更日期**: YYYY-MM-DD
**變更類型**: 功能改進 | 新功能 | 重構
**狀態**: ✅ 已完成 | 🚧 進行中

## 變更摘要
## 變更原因
## 詳細變更
## 修改文件清單
## 測試清單
```

### Bug 修復 (FIX-*)
```
claudedocs/4-changes/bug-fixes/
└── FIX-{NNN}-{description}.md
```

**標準 FIX 文檔結構**:
```markdown
# FIX-{NNN}: {Bug Description}

**修復日期**: YYYY-MM-DD
**嚴重程度**: 高 | 中 | 低
**狀態**: ✅ 已修復 | 🚧 進行中

## 問題描述
## 根本原因分析
## 修復方案
## 測試驗證
```

### 進度報告
```
claudedocs/3-progress/
├── daily/{YYYY}-{MM}/{YYYY}-{MM}-{DD}.md       # 日報
└── weekly/{YYYY}-W{WW}.md                       # 週報
```

### 情境提示詞 (SITUATION-*)
```
claudedocs/6-ai-assistant/prompts/
└── SITUATION-{N}-{DESCRIPTION}.md
```

**SITUATION 文檔結構**:
```markdown
# 🚀 情況{N}: {Title}

> **使用時機**: {觸發條件}
> **目標**: {期望達成}
> **適用場景**: {適用情境}

## 📋 Prompt 模板
## 🤖 AI 助手執行步驟
## ✅ 驗收標準
## 🔗 相關文檔
```

---

## 🛠️ 技術棧

### 核心框架
- **Agent 框架**: Microsoft Agent Framework (Preview)
- **AI SDK**: Claude Agent SDK
- **後端**: Python FastAPI 0.100+
- **前端**: React 18 + TypeScript
- **資料庫**: PostgreSQL 16+ + Prisma ORM
- **狀態管理**: Zustand (UI) + React Query (Server State)
- **緩存**: Redis 7+

### 外部服務
- **LLM**: Azure OpenAI GPT-4o + Claude 3.5
- **認證**: JWT Token
- **消息隊列**: RabbitMQ / Azure Service Bus

### 協議與標準
- **AG-UI Protocol**: Agent-User Interface Protocol (SSE based)
- **MCP**: Model Context Protocol (22 servers integrated)

---

## 🔍 重要文檔索引

### AI 助手工作流程

| 文檔路徑 | 用途 |
|----------|------|
| `6-ai-assistant/prompts/SITUATION-1-PROJECT-ONBOARDING.md` | 項目入門、新會話啟動 |
| `6-ai-assistant/prompts/SITUATION-2-FEATURE-DEV-PREP.md` | 功能開發準備、任務分析 |
| `6-ai-assistant/prompts/SITUATION-3-FEATURE-ENHANCEMENT.md` | 功能增強、代碼優化 |
| `6-ai-assistant/prompts/SITUATION-4-NEW-FEATURE-DEV.md` | 新功能開發、實作執行 |
| `6-ai-assistant/prompts/SITUATION-5-SAVE-PROGRESS.md` | 保存進度、會話結束 |
| `6-ai-assistant/prompts/SITUATION-6-SERVICE-STARTUP.md` | 服務啟動、環境檢查 |
| `6-ai-assistant/prompts/SITUATION-7-NEW-ENV-SETUP.md` | 新開發環境設置 |

### 核心文檔

| 文檔路徑 | 用途 |
|----------|------|
| `CLAUDE.md` (根目錄) | 專案總指南 |
| `docs/01-planning/prd/` | 產品需求文檔 |
| `docs/02-architecture/` | 系統架構設計 |
| `docs/03-implementation/sprint-planning/` | Sprint 計劃追蹤 |
| `docs/api/ag-ui-api-reference.md` | AG-UI API 參考 |

---

## 🛠️ 使用指南

### 查找文檔

| 需求 | 路徑 |
|------|------|
| Phase 規劃 | `1-planning/epics/phase-{N}/` |
| 功能變更 | `4-changes/feature-changes/CHANGE-{NNN}-*` |
| Bug 修復 | `4-changes/bug-fixes/FIX-{NNN}-*` |
| 測試報告 | `5-status/testing/` |
| 週報 | `3-progress/weekly/` |
| AI 工作流程 | `6-ai-assistant/prompts/` |

### 創建新文檔

1. **確定文檔類型和目錄**
   - 新 Phase → `1-planning/epics/phase-{N}/`
   - 功能變更 → `4-changes/feature-changes/`
   - Bug 修復 → `4-changes/bug-fixes/`
   - 進度報告 → `3-progress/`

2. **使用正確的命名約定**
   - Phase: `phase-{N}` (1-28+)
   - CHANGE: `CHANGE-{NNN}-{description}.md`
   - FIX: `FIX-{NNN}-{description}.md`

3. **遵循格式範本**
   - 參考 `4-changes/templates/` 下的範本
   - 包含必要的 frontmatter
   - 使用一致的章節標題

---

## ⚠️ 重要約定

1. **命名一致性**
   - 使用 UPPERCASE-WITH-DASHES 格式
   - 編號使用三位數 (001, 002, ...)
   - 描述使用簡短英文 kebab-case

2. **語言規範**
   - 文檔內容: 繁體中文為主
   - 代碼片段: 英文
   - 日期格式: YYYY-MM-DD

3. **狀態標記**
   - ✅ 已完成
   - 🚧 進行中
   - ⏸️ 暫停/待開發
   - ❌ 已取消
   - ⚠️ 有風險/需注意

4. **禁止事項**
   - ❌ 在錯誤目錄創建文檔
   - ❌ 使用不一致的命名格式
   - ❌ 遺漏必要的 frontmatter
   - ❌ 留下未更新的過時內容

---

## 📚 相關文件

### 項目級文檔
- `CLAUDE.md` - 根目錄專案總指南
- `docs/03-implementation/sprint-planning/README.md` - Sprint 狀態追蹤

### 規則文件
- `.claude/rules/backend-python.md` - Python 後端規範
- `.claude/rules/frontend-react.md` - React 前端規範
- `.claude/rules/agent-framework.md` - Agent Framework 規範
- `.claude/rules/git-workflow.md` - Git 工作流程
- `.claude/rules/code-quality.md` - 代碼品質規範
- `.claude/rules/testing.md` - 測試規範

---

**維護者**: AI 助手 + 開發團隊
**最後更新**: 2026-01-22
**文檔版本**: 3.0.0
