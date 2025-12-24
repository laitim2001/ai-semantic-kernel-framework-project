# 🤖 AI 助手 Prompt 庫

> **版本**: v3.1.0
> **專案**: IPA Platform (Intelligent Process Automation)
> **更新日期**: 2025-12-24
> **狀態**: Phase 11 完成 - Agent-Session Integration

---

## 📚 情況指引清單

### 開發準備

| 情況 | 文件 | 用途 |
|------|------|------|
| 🚀 **情況1** | [專案入門](./SITUATION-1-PROJECT-ONBOARDING.md) | 新開發者或新會話開始時，快速了解專案 |
| 🎯 **情況2** | [開發任務準備](./SITUATION-2-FEATURE-DEV-PREP.md) | 開始新開發任務前的準備工作 |

### 開發實施

| 情況 | 文件 | 用途 |
|------|------|------|
| 🐛 **情況3** | [Bug 修復](./SITUATION-3-BUG-FIX.md) | 處理 Bug 和錯誤修復 |
| 🚀 **情況4** | [功能開發](./SITUATION-4-FEATURE-DEVELOPMENT.md) | 實作新功能的標準流程 |
| 🧪 **情況5** | [測試執行](./SITUATION-5-TESTING.md) | 運行和編寫測試 |
| 🔄 **情況11** | [功能修改/更新](./SITUATION-11-FEATURE-UPDATE.md) | 修改、更新或重構現有功能 |

### 進度管理

| 情況 | 文件 | 用途 |
|------|------|------|
| 💾 **情況6** | [保存進度](./SITUATION-6-SAVE-PROGRESS.md) | 提交和保存開發成果 |
| 🔚 **情況9** | [Session 結束](./SITUATION-9-SESSION-END.md) | 結束開發會話 |

### 審查與驗證

| 情況 | 文件 | 用途 |
|------|------|------|
| 🏗️ **情況7** | [架構審查](./SITUATION-7-ARCHITECTURE-REVIEW.md) | 評估和改進系統架構 |
| 👀 **情況8** | [代碼審查](./SITUATION-8-CODE-REVIEW.md) | 審查代碼變更和 PR |
| 🎯 **情況10** | [UAT 測試](./SITUATION-10-UAT-SESSION.md) | 用戶驗收測試會話 |

---

## 🎯 設計理念 (v3.0.0)

### 核心原則

1. **情境導向**
   - 根據開發者的實際工作情境設計
   - 使用「情況」命名，更貼近使用場景
   - 每個情況都有明確的使用時機

2. **Prompt 模板區塊**
   - 每個文件都有明確的「📋 Prompt 模板」區塊
   - 開發者可以直接複製使用
   - 模板設計簡潔實用

3. **AI 執行步驟**
   - 清晰的步驟順序
   - 每個步驟有預估時間
   - 包含具體的命令和操作

4. **驗收標準**
   - 每個情況都有「✅ 驗收標準」
   - 明確列出完成條件
   - 便於驗證 AI 助手的輸出

5. **相關文檔連結**
   - 每個文件都連結到相關情況
   - 形成完整的工作流程
   - 便於流程間切換

---

## 📖 使用指南

### 基本使用方式

```markdown
# 方式 1: 閱讀情況文件
用戶: "請閱讀 SITUATION-1-PROJECT-ONBOARDING.md 並執行"
AI: 讀取文件並按照步驟執行

# 方式 2: 複製 Prompt 模板
用戶: [複製文件中的 Prompt 模板區塊]
AI: 根據模板提供的上下文執行

# 方式 3: 直接描述情境
用戶: "我剛開始這個專案，需要快速上手"
AI: 參考 SITUATION-1 的流程執行
```

### 常用工作流程

```yaml
# 每日開發流程
開始工作:
  - SITUATION-1: 專案入門 (如果是新會話)
  - SITUATION-2: 開發任務準備

開發中:
  - SITUATION-4: 功能開發 (新功能)
  - SITUATION-11: 功能修改/更新 (現有功能)
  - SITUATION-3: Bug 修復 (如遇到問題)
  - SITUATION-5: 測試執行

結束工作:
  - SITUATION-6: 保存進度
  - SITUATION-9: Session 結束

# 審查流程
  - SITUATION-8: 代碼審查
  - SITUATION-7: 架構審查 (大型變更)

# Phase 驗收
  - SITUATION-10: UAT 測試
```

---

## 📊 專案狀態概覽

### IPA Platform 當前狀態

| 項目 | 狀態 |
|------|------|
| **Phase** | Phase 11 完成 - Agent-Session Integration |
| **Sprint** | 47 Sprints 完成 |
| **Story Points** | ~1490 Points |
| **測試覆蓋** | 3500+ tests |
| **核心框架** | Microsoft Agent Framework (Preview) |

### 技術棧

```
後端: Python FastAPI + Pydantic
前端: React 18 + TypeScript + Tailwind CSS
數據庫: PostgreSQL 16 + Redis 7
消息隊列: RabbitMQ
LLM: Azure OpenAI GPT-4o
```

---

## 🔗 相關文檔

### 專案文檔
- `CLAUDE.md` - 專案總覽和開發指南
- `docs/bmm-workflow-status.yaml` - 工作流程狀態

### 架構文檔
- `backend/CLAUDE.md` - 後端架構指南
- `backend/src/api/CLAUDE.md` - API 層設計規範
- `backend/src/domain/CLAUDE.md` - Domain 層設計規範

### 規則文檔
- `.claude/rules/code-quality.md` - 代碼品質規則
- `.claude/rules/git-workflow.md` - Git 工作流程規則
- `.claude/rules/testing.md` - 測試規則

---

## 🔄 版本歷史

### v3.1.0 (2025-12-24)
- ✅ 新增 SITUATION-11: 功能修改/更新
- ✅ 覆蓋現有功能修改、重構、API 更新場景

### v3.0.0 (2025-12-24)
- 🔄 完全重寫 Prompt 系統
- ✅ 採用「情況」(SITUATION) 命名
- ✅ 添加 Prompt 模板區塊
- ✅ 添加驗收標準
- ✅ 更新至 Phase 11 狀態
- ✅ 10 個標準情況文件

### v2.0.0 (2025-11-20)
- 初始版本發布
- 12 個 PROMPT 文件
- 整合 AI-ASSISTANT-INSTRUCTIONS.md

---

**維護者**: AI 助手 + 開發團隊
**最後更新**: 2025-12-24
**反饋**: GitHub Issues
