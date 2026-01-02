# IPA Platform - Sprint Planning Overview

**版本**: 4.0 (Phase 14: Hybrid MAF + Claude SDK Architecture)
**創建日期**: 2025-11-29
**最後更新**: 2026-01-02
**總開發週期**: 57 Sprints (14 Phases)

---

## 快速導航 - Phase 總覽

| Phase | 名稱 | Sprints | Story Points | 狀態 | 文件 |
|-------|------|---------|--------------|------|------|
| Phase 1 | 基礎建設 | 1-6 | ~90 pts | ✅ 完成 | [README](./phase-1/README.md) |
| Phase 2 | 並行執行引擎 | 7-12 | ~90 pts | ✅ 完成 | [README](./phase-2/README.md) |
| Phase 3 | Official API Migration | 13-18 | ~105 pts | ✅ 完成 | [README](./phase-3/README.md) |
| Phase 4 | Advanced Adapters | 19-24 | ~105 pts | ✅ 完成 | [README](./phase-4/README.md) |
| Phase 5 | Connector Ecosystem | 25-27 | ~75 pts | ✅ 完成 | [README](./phase-5/README.md) |
| Phase 6 | Enterprise Integration | 28-30 | ~75 pts | ✅ 完成 | [README](./phase-6/README.md) |
| Phase 7 | Multi-turn & Memory | 31-33 | ~90 pts | ✅ 完成 | [README](./phase-7/README.md) |
| Phase 8 | Code Interpreter | 34-36 | ~90 pts | ✅ 完成 | [README](./phase-8/README.md) |
| Phase 9 | MCP Integration | 37-39 | ~90 pts | ✅ 完成 | [README](./phase-9/README.md) |
| Phase 10 | MCP Expansion | 40-44 | ~105 pts | ✅ 完成 | [README](./phase-10/README.md) |
| Phase 11 | Agent-Session Integration | 45-47 | ~90 pts | ✅ 完成 | [README](./phase-11/README.md) |
| Phase 12 | Claude Agent SDK | 48-51 | ~105 pts | 🔄 進行中 | [README](./phase-12/README.md) |
| **Phase 13** | **Hybrid Core Architecture** | 52-54 | 105 pts | 📋 待開始 | [README](./phase-13/README.md) |
| **Phase 14** | **Advanced Hybrid Features** | 55-57 | 95 pts | 📋 待開始 | [README](./phase-14/README.md) |

**總計**: ~1310 Story Points across 57 Sprints

---

## Phase 13-14: Hybrid Architecture (NEW)

### 背景

Phase 12 完成 Claude Agent SDK 整合後，需要進一步整合 **Microsoft Agent Framework (MAF)** 和 **Claude Agent SDK** 兩個框架，實現真正的混合編排架構。

### Phase 13: Hybrid Core Architecture (105 pts)

**目標**: 建立 MAF + Claude SDK 的核心整合架構

| Sprint | 名稱 | Points | 主要交付物 |
|--------|------|--------|-----------|
| Sprint 52 | Intent Router & Mode Detection | 35 pts | 智能意圖路由、模式檢測 |
| Sprint 53 | Context Bridge & Sync | 35 pts | 跨框架上下文同步 |
| Sprint 54 | HybridOrchestrator Refactor | 35 pts | 統一 Tool 執行、V2 編排器 |

**核心組件**:
- **Intent Router**: 判斷 Workflow Mode vs Chat Mode
- **Context Bridge**: MAF ↔ Claude 狀態同步
- **Unified Tool Executor**: 所有 Tool 通過 Claude 執行

### Phase 14: Advanced Hybrid Features (95 pts)

**目標**: 實現進階混合功能和優化

| Sprint | 名稱 | Points | 主要交付物 |
|--------|------|--------|-----------|
| Sprint 55 | Risk Assessment Engine | 30 pts | 風險評估驅動的審批決策 |
| Sprint 56 | Mode Switcher & HITL | 35 pts | 動態模式切換、增強 HITL |
| Sprint 57 | Unified Checkpoint & Polish | 30 pts | 統一 Checkpoint、整合測試 |

**核心組件**:
- **Risk Assessment Engine**: 基於風險等級的 HITL
- **Mode Switcher**: Workflow ↔ Chat 動態切換
- **Unified Checkpoint**: 跨框架狀態保存與恢復

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
| **Claude SDK** | Claude Agent SDK | Latest | 智能對話能力 |
| **後端** | Python FastAPI | 0.100+ | REST API 服務 |
| **前端** | React + TypeScript | 18+ | 現代化 UI |
| **數據庫** | PostgreSQL | 16+ | 主數據存儲 |
| **緩存** | Redis | 7+ | LLM 響應緩存 |
| **消息隊列** | Azure Service Bus / RabbitMQ | - | 異步任務處理 |
| **LLM** | Azure OpenAI + Claude | GPT-4o / Claude 3.5 | 企業級推理 |

### 系統架構圖 (Phase 14)

```
┌─────────────────────────────────────────────────────────────┐
│              React 18 前端 (Shadcn UI)                       │
│   Dashboard | Workflows | Agents | Sessions | Monitor        │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTPS
┌─────────────────────────┴───────────────────────────────────┐
│                   FastAPI Backend                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐   │
│  │Intent Router│───→│HybridOrchest.│───→│ Risk Assessor │   │
│  └─────────────┘    └──────────────┘    └───────────────┘   │
│         │                  │                    │            │
│         ▼                  ▼                    ▼            │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐   │
│  │Mode Switcher│    │Context Bridge│    │Unified Chkpt  │   │
│  └─────────────┘    └──────────────┘    └───────────────┘   │
│         │                  │                                 │
│         ▼                  ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Unified Tool Executor                       │ │
│  └─────────────────────────────────────────────────────────┘ │
│         │                                │                   │
│         ▼                                ▼                   │
│  ┌─────────────────┐            ┌───────────────────┐       │
│  │MAF Adapters     │            │Claude SDK         │       │
│  │ - GroupChat     │            │ - ClaudeSDKClient │       │
│  │ - Handoff       │            │ - ToolRegistry    │       │
│  │ - Concurrent    │            │ - HookManager     │       │
│  │ - Nested        │            │ - MCP Integration │       │
│  └─────────────────┘            └───────────────────┘       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
   ┌────▼────┐      ┌────▼────┐      ┌─────▼─────┐
   │Service  │      │Redis    │      │PostgreSQL │
   │Bus      │      │Cache    │      │Database   │
   └─────────┘      └─────────┘      └───────────┘
```

---

## 開發狀態總覽

### 已完成 Phase (1-11)

| Phase | 主要成就 |
|-------|---------|
| Phase 1-2 | 基礎架構、並行執行引擎 |
| Phase 3-4 | Official API Migration、Advanced Adapters |
| Phase 5-6 | Connector Ecosystem、Enterprise Integration |
| Phase 7-8 | Multi-turn & Memory、Code Interpreter |
| Phase 9-10 | MCP Core、MCP Expansion (22 servers) |
| Phase 11 | Agent-Session Integration (90 pts) |

### 進行中 Phase (12)

| Sprint | 狀態 | Points |
|--------|------|--------|
| Sprint 48 | ✅ 完成 | 35 pts |
| Sprint 49 | ✅ 完成 | 35 pts |
| Sprint 50 | ✅ 完成 | 30 pts |
| Sprint 51 | 🔄 進行中 | 35 pts |

**Phase 12 進度**: 130/165 pts (79%)

### 待開始 Phase (13-14)

Phase 13-14 為 **Hybrid MAF + Claude SDK** 整合架構，計劃在 Phase 12 完成後開始。

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
| Checkpoint 恢復成功率 | > 99.9% |
| 模式切換成功率 | > 99% |

### 可用性要求
| 指標 | MVP 目標 | Phase 14 目標 |
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
| 風險評估 | Risk Assessment Engine (Phase 14) |

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
ANTHROPIC_API_KEY=xxx
```

---

## 風險與緩解

| 風險 | 等級 | 緩解措施 |
|------|------|---------|
| Agent Framework API 變更 | 中 | 鎖定版本，監控 Release Notes |
| Claude SDK API 變更 | 中 | 版本鎖定，抽象層隔離 |
| LLM Token 成本超預算 | 中 | 成本監控 + 閾值告警 + 緩存 |
| 框架整合複雜度 | 高 | Context Bridge + Unified Checkpoint |
| 模式切換狀態丟失 | 中 | Checkpoint 機制 + 回滾支持 |

---

## 參考文檔

| 類別 | 文檔位置 |
|------|---------|
| 產品探索 | `docs/00-discovery/` |
| 產品規劃 | `docs/01-planning/prd/` |
| UI/UX 設計 | `docs/01-planning/ui-ux/` |
| 技術架構 | `docs/02-architecture/` |
| Agent Framework | `reference/agent-framework/` |
| Claude Agent SDK | `backend/src/integrations/claude_sdk/` |
| Phase 13 文檔 | `docs/03-implementation/sprint-planning/phase-13/` |
| Phase 14 文檔 | `docs/03-implementation/sprint-planning/phase-14/` |

---

**下一步**:
- 完成 Phase 12 Sprint 51
- 開始 Phase 13 Sprint 52 - Intent Router & Mode Detection
