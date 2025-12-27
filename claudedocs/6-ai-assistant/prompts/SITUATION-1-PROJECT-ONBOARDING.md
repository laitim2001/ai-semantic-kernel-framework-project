# 🚀 情況1: 專案入門 - 開發人員重新開始開發活動

> **使用時機**: 新對話開始前，開發人員需要快速了解專案
> **目標**: 讓 AI 助手在 5 分鐘內理解專案全貌
> **適用場景**: 新開發者、長時間未接觸專案、會話重啟

---

## 📋 Prompt 模板 (給開發人員)

```markdown
你好！我需要你幫我快速了解這個專案。

這是 IPA Platform (Intelligent Process Automation)，一個企業級 AI Agent 編排管理平台，我需要你:

1. 閱讀專案概覽
   - 請先閱讀 `CLAUDE.md` 了解專案基本資訊和開發指南
   - 閱讀 `docs/bmm-workflow-status.yaml` 了解當前開發階段

2. 理解專案結構
   - 查看 `backend/src/api/v1/` 了解 API 結構
   - 查看 `backend/src/domain/` 了解業務邏輯層
   - 查看 `backend/src/integrations/agent_framework/` 了解 Agent Framework 整合

3. 確認當前狀態
   - 檢查 Git 狀態: `git status` 和 `git log --oneline -10`
   - 閱讀 `claudedocs/3-progress/weekly/` 最新的每週進度 (如有)

4. 總結並回答
   - 這個專案是做什麼的？
   - 當前開發到哪個階段？
   - 最近完成了什麼功能？
   - 有沒有進行中的任務？
   - 技術棧是什麼？

請用中文回答，並保持簡潔。
```

---

## 🤖 AI 助手執行步驟

### Step 1: 快速理解專案 (2 分鐘)

```bash
# 1. 讀取核心文檔
Read: CLAUDE.md (專案總覽和開發指南)
Read: docs/bmm-workflow-status.yaml (工作流程狀態)

# 2. 檢查 Git 狀態
Bash: git status
Bash: git log --oneline -10
Bash: git branch

# 3. 讀取最新進度 (如有)
Read: claudedocs/3-progress/weekly/[最新週報].md
```

### Step 2: 理解項目結構 (2 分鐘)

```bash
# 1. 掃描後端結構
Bash: ls backend/src/api/v1/
Bash: ls backend/src/domain/
Bash: ls backend/src/integrations/agent_framework/
Bash: ls backend/src/integrations/claude_sdk/ (Phase 12)

# 2. 檢查配置文件
Read: backend/requirements.txt (了解依賴)
Read: docker-compose.yml (了解服務架構)
```

### Step 3: 生成總結報告 (1 分鐘)

```markdown
# 📊 專案入門總結

## 專案概覽
- **名稱**: IPA Platform (Intelligent Process Automation)
- **定位**: 企業級 AI Agent 編排管理平台
- **核心框架**: Microsoft Agent Framework (Preview)
- **目標用戶**: 中型企業 IT 運維團隊 (500-2000 人)

## 技術架構
- **後端**: Python FastAPI + Pydantic
- **前端**: React 18 + TypeScript + Tailwind CSS
- **數據庫**: PostgreSQL 16 + Redis 7
- **消息隊列**: RabbitMQ
- **LLM**: Azure OpenAI GPT-4o

## 當前狀態
- **階段**: [從 bmm-workflow-status.yaml 讀取]
- **完成度**: [Sprint 數量和 Story Points]
- **最新分支**: main
- **最後提交**: [commit message]

## 已完成的主要 Phases
| Phase | 名稱 | 重點功能 |
|-------|------|----------|
| 1-3 | Core MVP | 基礎設施、核心引擎、工作流 |
| 4-6 | Agent Framework | 官方 API 整合、Adapters |
| 7-8 | Orchestration | 並發執行、Agent Handoff |
| 9-10 | MCP & Sessions | MCP 架構、Session Mode |
| 11 | Integration | Agent-Session 整合 |
| 12 | Claude Agent SDK | SDK 整合、Tools、Hooks、MCP、Hybrid 架構 |

## 進行中任務
- ⏳ [檢查 Git 狀態或 bmm-workflow-status.yaml]
- ⏳ [如果沒有，回答: 無進行中任務]

## 快速導航
- **後端 API**: backend/src/api/v1/
- **業務邏輯**: backend/src/domain/
- **Agent Framework**: backend/src/integrations/agent_framework/
- **Claude SDK**: backend/src/integrations/claude_sdk/ (Phase 12)
- **前端頁面**: frontend/src/pages/
- **文檔**: docs/
- **AI 助手**: claudedocs/6-ai-assistant/prompts/

## 下一步建議
1. 運行 `docker-compose up -d` 啟動服務
2. 運行 `cd backend && uvicorn main:app --reload`
3. 檢查 `curl http://localhost:8000/health`
4. 閱讀相關 SITUATION 指引開始工作
```

---

## ✅ 驗收標準

AI 助手應該能回答以下問題:

1. **專案是什麼？**
   - IPA Platform，企業級 AI Agent 編排管理平台

2. **當前階段？**
   - 從 bmm-workflow-status.yaml 讀取當前 Phase 和 Sprint

3. **最近完成？**
   - 從 Git log 或狀態文件讀取

4. **進行中任務？**
   - 檢查 Git 狀態或 bmm-workflow-status.yaml

5. **技術棧？**
   - Python FastAPI + React + PostgreSQL + Redis + Azure OpenAI

6. **如何啟動？**
   - `docker-compose up -d` → `uvicorn main:app --reload`

---

## 📚 推薦閱讀順序 (深入了解)

### 新開發者 (Day 1)
1. CLAUDE.md - 專案總覽
2. docs/bmm-workflow-status.yaml - 當前狀態
3. docker-compose.yml - 環境設置

### 新開發者 (Day 2-3)
1. docs/02-architecture/ - 技術架構
2. docs/01-planning/prd/ - 產品需求
3. backend/src/api/v1/ - API 結構

### 新開發者 (Week 2)
1. backend/src/domain/ - 業務邏輯
2. backend/src/integrations/agent_framework/ - Agent Framework
3. backend/src/integrations/claude_sdk/ - Claude Agent SDK (Phase 12)
4. docs/03-implementation/sprint-planning/phase-12/ - Phase 12 規劃
5. claudedocs/4-changes/ - 變更歷史

---

## 🔗 相關文檔

### 開發流程指引
- [情況2: 開發前準備](./SITUATION-2-FEATURE-DEV-PREP.md)
- [情況3: 功能增強/修正](./SITUATION-3-FEATURE-ENHANCEMENT.md)
- [情況4: 新功能開發](./SITUATION-4-NEW-FEATURE-DEV.md)
- [情況5: 保存進度](./SITUATION-5-SAVE-PROGRESS.md)

---

**維護者**: AI 助手 + 開發團隊
**最後更新**: 2025-12-27
**版本**: 2.1
