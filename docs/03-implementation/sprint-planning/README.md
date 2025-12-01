# IPA Platform - Sprint Planning Overview

**版本**: 2.0 (Based on Microsoft Agent Framework)
**創建日期**: 2025-11-29
**總開發週期**: 12-14 週 (6 個 Sprint)

---

## 快速導航

| Sprint | 名稱 | 週數 | 主要交付物 | 文件 |
|--------|------|------|-----------|------|
| Sprint 0 | 基礎設施 | Week 1-2 | 開發環境 + CI/CD | [Plan](./sprint-0-plan.md) / [Checklist](./sprint-0-checklist.md) |
| Sprint 1 | 核心引擎 | Week 3-4 | Agent Framework 集成 | [Plan](./sprint-1-plan.md) / [Checklist](./sprint-1-checklist.md) |
| Sprint 2 | 工作流 & 檢查點 | Week 5-6 | Workflow + Checkpoint | [Plan](./sprint-2-plan.md) / [Checklist](./sprint-2-checklist.md) |
| Sprint 3 | 集成 & 可靠性 | Week 7-8 | n8n + Teams + 審計 | [Plan](./sprint-3-plan.md) / [Checklist](./sprint-3-checklist.md) |
| Sprint 4 | 開發者體驗 | Week 9-10 | Marketplace + DevUI | [Plan](./sprint-4-plan.md) / [Checklist](./sprint-4-checklist.md) |
| Sprint 5 | 前端 UI | Week 11-12 | React UI + Dashboard | [Plan](./sprint-5-plan.md) / [Checklist](./sprint-5-checklist.md) |
| Sprint 6 | 打磨 & 發布 | Week 13-14 | 測試 + 部署 | [Plan](./sprint-6-plan.md) / [Checklist](./sprint-6-checklist.md) |

---

## 產品概述

### 產品定位
**IPA Platform** (Intelligent Process Automation) - 企業級 AI Agent 編排管理平台

### 核心差異化
| 傳統 RPA | IPA Platform |
|---------|--------------|
| 規則基礎，固定流程 | **LLM 智能決策**，自適應場景 |
| 被動執行，問題發生後處理 | **主動巡檢預防**，從救火到預防 |
| 單系統操作，信息孤島 | **跨系統關聯分析**，統一視圖 |
| 無學習能力，準確率固定 | **人機協作學習**，越用越智能 |

### 目標用戶
1. **IT 運維團隊** (主要) - 500-2000 人企業，50-500 人 IT 部門
2. **客戶服務團隊** (次要) - 100-1000 人 CS 部門

### 商業價值
- IT 處理時間：6 小時/天 → 1 小時/天 (節省 40%+)
- CS 處理時間：30-80 分鐘/工單 → 縮短 50%+
- 12 個月 ROI > 200%

---

## 技術架構摘要

### 核心技術棧

| 層級 | 技術 | 版本 | 說明 |
|------|------|------|------|
| **Agent 框架** | Microsoft Agent Framework | Preview | 核心編排引擎 |
| **後端** | Python FastAPI | 0.100+ | REST API 服務 |
| **前端** | React + TypeScript | 18+ | 現代化 UI |
| **數據庫** | PostgreSQL | 16+ | 主數據存儲 |
| **緩存** | Redis | 7+ | LLM 響應緩存 |
| **消息隊列** | Azure Service Bus / RabbitMQ | - | 異步任務處理 |
| **LLM** | Azure OpenAI | GPT-4o | 企業級推理 |

### Agent Framework 核心 API

```python
# 安裝
pip install agent-framework --pre

# 基本 Agent 創建
from agent_framework.azure import AzureOpenAIChatClient

agent = AzureOpenAIChatClient().create_agent(
    name="MyAgent",
    instructions="You are a helpful assistant.",
    tools=[my_tool]
)
result = await agent.run("Execute task")

# Workflow 構建
from agent_framework import WorkflowBuilder, Executor

workflow = (
    WorkflowBuilder(max_iterations=10)
    .set_start_executor(prepare)
    .add_edge(prepare, agent_executor)
    .add_edge(agent_executor, review_gateway)
    .with_checkpointing(checkpoint_storage)
    .build()
)

# Human-in-the-loop
await ctx.request_info(
    request_data=ApprovalRequest(prompt="Review needed"),
    response_type=str
)
```

### 系統架構圖

```
┌─────────────────────────────────────────────────┐
│         React 18 前端 (Shadcn UI)               │
│  Dashboard | Workflows | Agents | Monitor       │
└─────────────────────┬───────────────────────────┘
                      │ HTTPS
┌─────────────────────┴───────────────────────────┐
│  Azure App Service (Python FastAPI)             │
│  ├─ Workflow Service (CRUD, 驗證)              │
│  ├─ Execution Service (調度, 狀態管理)         │
│  └─ Agent Service (Agent Framework 運行時)     │
└─────────────────────┬───────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
   ┌────▼───┐   ┌────▼────┐   ┌───▼────────┐
   │Service │   │Redis    │   │PostgreSQL  │
   │Bus     │   │Cache    │   │Database    │
   └────────┘   └─────────┘   └────────────┘
```

---

## 14 個 MVP 功能

### 核心引擎層 (P0)
| ID | 功能 | 開發時間 | Sprint |
|----|------|---------|--------|
| F1 | 順序式 Agent 編排 | 2 週 | Sprint 1 |
| F2 | 人機協作檢查點 (Human-in-the-loop) | 2 週 | Sprint 2 |
| F3 | 跨系統關聯 (ServiceNow/Dynamics/SharePoint) | 2 週 | Sprint 2 |

### 創新功能層 (P1)
| ID | 功能 | 開發時間 | Sprint |
|----|------|---------|--------|
| F4 | 跨場景協作 (CS↔IT) | 2 週 | Sprint 3 |
| F5 | 學習型協作 (Few-shot Learning) | 1 週 | Sprint 4 |

### 開發者體驗層 (P0)
| ID | 功能 | 開發時間 | Sprint |
|----|------|---------|--------|
| F6 | Agent 模板市場 (6-8 模板) | 3 週 | Sprint 4 |
| F7 | DevUI 整合 (可視化調試) | 2 週 | Sprint 4 |

### 可靠性層 (P0)
| ID | 功能 | 開發時間 | Sprint |
|----|------|---------|--------|
| F8 | n8n 觸發 + 錯誤處理 | 2 週 | Sprint 3 |
| F9 | Prompt 管理 (YAML 模板) | 1 週 | Sprint 3 |

### 可觀測性層 (P0)
| ID | 功能 | 開發時間 | Sprint |
|----|------|---------|--------|
| F10 | 審計追蹤 (Append-only) | 1 週 | Sprint 3 |
| F11 | Teams 通知 (Adaptive Card) | 1 週 | Sprint 3 |
| F12 | 監控儀表板 | 2 週 | Sprint 5 |

### UI/UX 層 (P0)
| ID | 功能 | 開發時間 | Sprint |
|----|------|---------|--------|
| F13 | 現代 Web UI | 4 週 | Sprint 5 |

### 性能優化層 (P0)
| ID | 功能 | 開發時間 | Sprint |
|----|------|---------|--------|
| F14 | Redis 緩存 | 1 週 | Sprint 2 |

---

## 數據模型概覽

### 核心表結構

```sql
-- 用戶表
users (id, email, name, role, password_hash, created_at)

-- Agent 表
agents (id, name, description, category, code, config, status, created_by)

-- 工作流表
workflows (id, agent_id, name, trigger_type, trigger_config, created_at)

-- 執行記錄表
executions (id, workflow_id, status, started_at, completed_at, result, error,
            llm_calls, llm_tokens, llm_cost)

-- 檢查點表
checkpoints (id, execution_id, step, state, status, approved_by, feedback)

-- 審計日誌表 (Append-only)
audit_logs (id, execution_id, action, actor, details, timestamp)

-- 學習案例表
learning_cases (id, execution_id, scenario, original_action,
                human_modified_action, feedback)

-- Agent 模板表
agent_templates (id, name, category, description, code_template,
                 config_schema, usage_count)
```

---

## 非功能性需求 (NFR)

### 性能要求
| 指標 | 目標值 |
|------|--------|
| Agent 執行延遲 (P95) | < 5 秒 |
| LLM 調用延遲 (P95) | < 3 秒 |
| API 響應時間 (P95) | < 500ms |
| Dashboard 加載時間 | < 2 秒 |
| 併發執行數 | 50+ 同時 |
| Redis 緩存命中率 | ≥ 60% |

### 可用性要求
| 指標 | MVP 目標 | Phase 2 目標 |
|------|----------|-------------|
| 系統正常運行 | 99.0% | 99.5% |
| 數據持久性 | 99.99% | 99.99% |
| 檢查點恢復 | 100% | 100% |

### 安全要求
| 要求 | 實現方式 |
|------|---------|
| 認證 | JWT + 24h 會話 |
| 授權 | 角色基礎 (admin/user/viewer) |
| 傳輸加密 | TLS 1.3 |
| 存儲加密 | AES-256 |
| 機密管理 | Azure Key Vault |

---

## 成功指標 (KPI)

### 技術 KPI
| 指標 | 1 月 | 3 月 | 6 月 |
|------|------|------|------|
| Agent 執行成功率 | ≥85% | ≥90% | ≥95% |
| 平均執行時間 | <60s | <45s | <30s |
| LLM 成本/執行 | <$0.10 | <$0.08 | <$0.05 |
| 緩存命中率 | ≥50% | ≥60% | ≥70% |

### 業務 KPI
| 指標 | 基線 (人工) | 1 月目標 | 3 月目標 |
|------|------------|----------|----------|
| 工單解決時間 | 4-6 小時 | 2-3 小時 | 1-2 小時 |
| 人工工作減少 | 0% | 30% | 40-50% |
| 人工干預率 | 100% | <40% | <30% |

---

## 開發環境設置

### 前置要求
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Azure CLI (已登入)
- Git

### 快速開始

```bash
# 1. Clone 專案
git clone https://github.com/your-org/ipa-platform.git
cd ipa-platform

# 2. 啟動開發環境
docker-compose up -d

# 3. 安裝 Python 依賴
cd backend
pip install -r requirements.txt
pip install agent-framework --pre

# 4. 啟動後端
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 5. 安裝前端依賴 (另一終端)
cd frontend
npm install
npm run dev
```

### 環境變量

```bash
# .env
DATABASE_URL=postgresql://user:pass@localhost:5432/ipa_platform
REDIS_URL=redis://localhost:6379
AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com/
AZURE_OPENAI_API_KEY=xxx
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
```

---

## 風險與緩解

| 風險 | 等級 | 緩解措施 |
|------|------|---------|
| Agent Framework API 變更 | 中 | 鎖定版本，監控 Release Notes |
| LLM Token 成本超預算 | 中 | 成本監控 + 閾值告警 + 緩存 |
| 第三方 API 不穩定 | 中 | 超時控制 + 降級策略 + 重試 |
| UI 開發延遲 | 低 | 使用 Shadcn UI 組件庫 |

---

## 參考文檔

| 類別 | 文檔位置 |
|------|---------|
| 產品探索 | `docs/00-discovery/` |
| 產品規劃 | `docs/01-planning/prd/` |
| UI/UX 設計 | `docs/01-planning/ui-ux/` |
| 技術架構 | `docs/02-architecture/` |
| Agent Framework | `reference/agent-framework/` |
| Agent Framework 官方文檔 | https://learn.microsoft.com/en-us/agent-framework/ |

---

**下一步**: 查看 [Sprint 0 Plan](./sprint-0-plan.md) 開始開發
