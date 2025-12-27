# 🚀 情況1: 專案入門 - 開發人員重新開始開發活動

> **使用時機**: 新對話開始前，開發人員需要快速了解專案
> **目標**: 讓 AI 助手在 5 分鐘內理解專案全貌
> **適用場景**: 新開發者、長時間未接觸專案、會話重啟

---

## 📋 Prompt 模板 (給開發人員)

```markdown
你好！我需要你幫我快速了解這個專案。

這是 IPA Platform (Intelligent Process Automation)，一個企業級 AI Agent 編排管理平台。

請幫我：

1. 閱讀專案概覽
   - 請先閱讀 `CLAUDE.md` 了解專案基本資訊和開發指南
   - 閱讀 `docs/bmm-workflow-status.yaml` 了解當前階段和歷史

2. 理解專案結構
   - 查看 `backend/src/api/v1/` 了解 API 結構
   - 查看 `backend/src/domain/` 了解業務邏輯層
   - 查看 `backend/src/integrations/agent_framework/` 了解 Agent Framework 整合

3. 確認當前狀態
   - 檢查 Git 狀態: `git status` 和 `git log --oneline -10`
   - 了解最近完成的 Phase 和 Sprint

4. 總結並回答
   - 這個專案是做什麼的？
   - 當前開發到哪個階段？
   - 最近完成了什麼功能？
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
```

### Step 2: 理解項目結構 (2 分鐘)

```bash
# 1. 掃描後端結構
Bash: ls backend/src/api/v1/
Bash: ls backend/src/domain/
Bash: ls backend/src/integrations/agent_framework/

# 2. 掃描前端結構
Bash: ls frontend/src/pages/
Bash: ls frontend/src/components/
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
- **階段**: Phase 11 完成 - Agent-Session Integration
- **完成度**: 47 Sprints, ~1490 Story Points
- **UAT**: 4/4 場景通過
- **最新分支**: main

## 已完成的主要 Phases
| Phase | 名稱 | 重點功能 |
|-------|------|----------|
| 1-3 | Core MVP | 基礎設施、核心引擎、工作流 |
| 4-6 | Agent Framework | 官方 API 整合、Adapters |
| 7-8 | Orchestration | 並發執行、Agent Handoff |
| 9-10 | MCP & Sessions | MCP 架構、Session Mode |
| 11 | Integration | Agent-Session 整合 |

## 快速導航
- **後端 API**: backend/src/api/v1/
- **業務邏輯**: backend/src/domain/
- **Agent Framework**: backend/src/integrations/agent_framework/
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

AI 助手應該能回答以下問題：

1. **專案是什麼？**
   - IPA Platform，企業級 AI Agent 編排管理平台

2. **當前階段？**
   - Phase 11 完成，Agent-Session Integration

3. **技術棧？**
   - FastAPI + React + PostgreSQL + Redis + Azure OpenAI

4. **核心框架？**
   - Microsoft Agent Framework (Preview)

5. **如何啟動？**
   - `docker-compose up -d` → `uvicorn main:app --reload`

6. **專案規模？**
   - 47 Sprints, ~1490 Story Points, 3500+ tests

---

## 🔗 相關文檔

### 核心開發流程
- [情況2: 開發前準備](./SITUATION-2-FEATURE-DEV-PREP.md)
- [情況3: 功能增強/修正](./SITUATION-3-FEATURE-ENHANCEMENT.md)
- [情況4: 新功能開發](./SITUATION-4-NEW-FEATURE-DEV.md)
- [情況5: 保存進度](./SITUATION-5-SAVE-PROGRESS.md)

---

**維護者**: AI 助手 + 開發團隊
**最後更新**: 2025-12-27
**版本**: 3.0
