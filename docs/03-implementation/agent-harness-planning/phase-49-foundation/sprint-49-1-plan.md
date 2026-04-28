# Sprint 49.1 — V1 封存 + V2 目錄骨架 + CI Pipeline

**建立日期**：2026-04-28
**修訂**：2026-04-28（review 整合：補 CI / 範疇 12 / _contracts / hitl 中央化）
**所屬 Phase**：Phase 49 — Foundation（4 sprint，**原 3 sprint 修訂**）
**版本**：V2.1
**Sprint 編號**：49.1（Phase 49 第 1 個 Sprint，**全 22 sprint 第 1 個**）
**工作量**：1 週（5 工作天）
**Story Points**：26 點（**原 21；補 CI + 範疇 12 + 中央化目錄 +5 點**）
**狀態**：📋 計劃中

---

## Sprint Goal

> **將 V1 完整封存為不可變基線、建立 V2「11 範疇 + 範疇 12 + 跨範疇 single-source」的後端與前端目錄骨架、上線 CI pipeline，讓後續 21 個 Sprint 都能在乾淨且結構正確、CI 自動把關的工作區上動工。**

本 Sprint **不寫任何業務邏輯、不寫任何 LLM 呼叫**，只交付「結構」+「可啟動」+「CI 上線」三個東西。

**整合修訂（2026-04-28）**：
1. 加入第 12 範疇 Observability ABC 空殼
2. 加入 `agent_harness/_contracts/` 跨範疇 single-source 型別包
3. 加入 `agent_harness/hitl/` HITL 中央化 ABC
4. 加入 CI pipeline（GitHub Actions backend-ci + frontend-ci）
5. 加入 V2 ≠ SaaS-ready 聲明（00-v2-vision.md 已更新）

---

## 前置條件

| 條件 | 狀態 |
|------|------|
| V2 規劃文件 17 份完成 | ✅ 已完成（README + 00-16） |
| 3 大最高指導原則確認 | ✅ 已完成（10-server-side-philosophy.md） |
| 11 範疇規格 + 對齊度基線 | ✅ 已完成（01-eleven-categories-spec.md） |
| Phase 路線圖確認 | ✅ 已完成（06-phase-roadmap.md） |
| 用戶選擇執行策略（A/B/C） | ✅ 用戶選擇執行 Prompt D1 |
| Phase 48 全部 PR 收尾 | ⚠️ 待確認（v1-final-phase48 tag 前必須） |

---

## User Stories

### Story 49.1-1：保留 V1 為唯讀考古資料

**作為** 平台 maintainer
**我希望** V1 完整搬到 `archived/v1-phase1-48/` 並打 git tag
**以便** 任何人都能回到 V1 對照、學教訓，但不會誤改 V1

### Story 49.1-2：建立可信的 V2 後端目錄

**作為** V2 開發者
**我希望** backend 目錄按「5 層 + 11 範疇」嚴格組織（agent_harness / platform / adapters / api / business_domain / infrastructure / core / middleware）
**以便** 後續 15 個 Sprint 不會再出現 V1「Guardrails 散在 6 處、Orchestrator 散在 5 處」的散落問題

### Story 49.1-3：建立可信的 V2 前端目錄

**作為** 前端開發者
**我希望** frontend 目錄按「11 範疇 features + chat-v2 主流量」組織
**以便** 範疇 features（如 governance、verification）有清楚的前端歸屬

### Story 49.1-4：每個範疇有「契約 + 空殼」可被 import

**作為** Phase 50+ 開發者
**我希望** 每個範疇目錄都有 `README.md` + ABC interface 空殼（不實作）
**以便** 我可以開始為範疇寫 type hints / 測試 stub，而不會撞到 ImportError

### Story 49.1-5：基礎開發環境一鍵啟動

**作為** 新加入的開發者
**我希望** `pip install -e .` + `npm install` + `docker compose up` 三條指令就能起所有依賴
**以便** Sprint 49.2 能立刻進入 DB schema 開發，不被環境問題卡住

---

## 技術設計

### 1. V1 封存策略

```bash
# Step 1: 確認 Phase 48 收尾
git checkout main
git pull
git status   # 必須 clean

# Step 2: 打不可變 tag
git tag -a v1-final-phase48 -m "V1 final state — Phase 1-48 (27% alignment baseline)"
git push origin v1-final-phase48

# Step 3: 移動到 archived/
git mv backend archived/v1-phase1-48/backend
git mv frontend archived/v1-phase1-48/frontend
git mv infrastructure archived/v1-phase1-48/infrastructure
# docs / claudedocs / reference 保持原位（V2 仍要用）

# Step 4: 在 archived/v1-phase1-48/README.md 標明
#   "READ-ONLY. V1 baseline frozen on 2026-04-XX. Phase 1-48. Do not modify."
```

**關鍵決策**：
- ✅ `docs/` 完整保留 — V2 仍寫在 `docs/03-implementation/agent-harness-planning/`
- ✅ `claudedocs/` 完整保留 — V2 持續使用
- ✅ `reference/` 完整保留 — V2 仍會看 MAF / Claude SDK 內部
- ❌ `backend/` / `frontend/` / `infrastructure/` 整個移到 archived/

### 2. V2 後端目錄樹

```
backend/                                 ← 全新（V1 已移走）
├── pyproject.toml                       ← V2 主配置
├── requirements.txt                     ← V2 鎖定版本
├── README.md                            ← V2 後端入口說明
├── alembic.ini                          ← Sprint 49.2 用，本 Sprint 留空
├── src/
│   ├── __init__.py
│   ├── main.py                          ← FastAPI app 啟動（最小骨架）
│   │
│   ├── agent_harness/                   ← 11 範疇 + 範疇 12 + 中央化（本 Sprint 只建空殼）
│   │   ├── __init__.py
│   │   ├── _contracts/                  ⭐ 跨範疇 single-source 型別（17.md §1.1）
│   │   │   ├── __init__.py              （統一 re-export）
│   │   │   ├── chat.py                  ← ChatRequest/Response/Message/StopReason
│   │   │   ├── tools.py                 ← ToolSpec/ToolCall/ToolResult/Annotations
│   │   │   ├── state.py                 ← LoopState/Transient/Durable/StateVersion
│   │   │   ├── events.py                ← LoopEvent + 子類
│   │   │   ├── memory.py                ← MemoryHint
│   │   │   ├── prompt.py                ← PromptArtifact/CacheBreakpoint
│   │   │   ├── verification.py          ← VerificationResult
│   │   │   ├── subagent.py              ← SubagentBudget/Result
│   │   │   ├── observability.py         ← TraceContext/MetricEvent
│   │   │   └── hitl.py                  ← ApprovalRequest/Decision/HITLPolicy
│   │   ├── orchestrator_loop/           ← 範疇 1
│   │   │   ├── __init__.py
│   │   │   ├── README.md
│   │   │   └── _abc.py                  ← AgentLoop ABC（async iterator）
│   │   ├── tools/                       ← 範疇 2
│   │   │   ├── __init__.py
│   │   │   ├── README.md
│   │   │   └── _abc.py                  ← ToolRegistry / ToolExecutor ABC
│   │   ├── memory/                      ← 範疇 3
│   │   │   ├── __init__.py
│   │   │   ├── README.md
│   │   │   └── _abc.py                  ← MemoryLayer ABC（雙軸）
│   │   ├── context_mgmt/                ← 範疇 4
│   │   │   ├── __init__.py
│   │   │   ├── README.md
│   │   │   └── _abc.py                  ← Compactor / TokenCounter / PromptCacheManager ABC
│   │   ├── prompt_builder/              ← 範疇 5
│   │   │   ├── __init__.py
│   │   │   ├── README.md
│   │   │   └── _abc.py                  ← PromptBuilder ABC
│   │   ├── output_parser/               ← 範疇 6
│   │   │   ├── __init__.py
│   │   │   ├── README.md
│   │   │   └── _abc.py                  ← OutputParser ABC
│   │   ├── state_mgmt/                  ← 範疇 7
│   │   │   ├── __init__.py
│   │   │   ├── README.md
│   │   │   └── _abc.py                  ← Checkpointer + Reducer ABC
│   │   ├── error_handling/              ← 範疇 8
│   │   │   ├── __init__.py
│   │   │   ├── README.md
│   │   │   └── _abc.py                  ← ErrorPolicy / CircuitBreaker / ErrorTerminator ABC
│   │   ├── guardrails/                  ← 範疇 9
│   │   │   ├── __init__.py
│   │   │   ├── README.md
│   │   │   └── _abc.py                  ← Guardrail / Tripwire ABC
│   │   ├── verification/                ← 範疇 10
│   │   │   ├── __init__.py
│   │   │   ├── README.md
│   │   │   └── _abc.py                  ← Verifier ABC
│   │   ├── subagent/                    ← 範疇 11
│   │   │   ├── __init__.py
│   │   │   ├── README.md
│   │   │   └── _abc.py                  ← SubagentDispatcher ABC
│   │   ├── observability/               ⭐ 範疇 12（cross-cutting）
│   │   │   ├── __init__.py
│   │   │   ├── README.md
│   │   │   └── _abc.py                  ← Tracer ABC
│   │   └── hitl/                        ⭐ §HITL 中央化
│   │       ├── __init__.py
│   │       ├── README.md
│   │       └── _abc.py                  ← HITLManager ABC
│   │
│   ├── platform/                        ← 治理 + Workers + 觀測（拆分上帝層）
│   │   ├── __init__.py
│   │   ├── governance/
│   │   │   ├── risk/                    ← V1 風險邏輯遷移用
│   │   │   ├── hitl/                    ← V1 HITL 邏輯遷移用
│   │   │   └── audit/                   ← Append-only audit
│   │   ├── identity/                    ← 多租戶 / 認證 / 角色
│   │   ├── observability/               ← OTel / metrics / logging
│   │   └── workers/                     ← Celery / Temporal worker
│   │
│   ├── adapters/                        ← 外部整合（LLM / MAF / Tools）
│   │   ├── __init__.py
│   │   ├── _base/
│   │   │   ├── __init__.py
│   │   │   ├── README.md
│   │   │   └── chat_client.py           ← ChatClient ABC（範疇中性）
│   │   ├── azure_openai/                ← Sprint 49.3 實作
│   │   │   └── README.md
│   │   ├── anthropic/                   ← 預留位（不實作）
│   │   │   └── README.md
│   │   └── maf/                         ← Sprint 54.2 實作（不在主流量）
│   │       └── README.md
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── chat/                    ← Phase 50.2 主流量
│   │       │   └── README.md
│   │       ├── governance/              ← Phase 53.3 HITL endpoint
│   │       │   └── README.md
│   │       └── health.py                ← /health endpoint（本 Sprint 實作）
│   │
│   ├── business_domain/                 ← 業務領域（Phase 55 接回）
│   │   ├── __init__.py
│   │   ├── README.md                    ← 標明「Phase 55 才動工」
│   │   ├── patrol/
│   │   ├── correlation/
│   │   ├── rootcause/
│   │   ├── audit_domain/
│   │   └── incident/
│   │
│   ├── infrastructure/                  ← DB / Redis / Storage / MQ
│   │   ├── __init__.py
│   │   ├── db/                          ← Sprint 49.2 實作
│   │   ├── cache/
│   │   ├── messaging/
│   │   └── storage/
│   │
│   ├── core/                            ← 全局工具（無業務邏輯）
│   │   ├── __init__.py
│   │   ├── config/                      ← pydantic Settings
│   │   ├── exceptions/
│   │   └── logging/
│   │
│   └── middleware/                      ← FastAPI 中介層
│       ├── __init__.py
│       ├── tenant.py                    ← Tenant context（Sprint 49.2 強化）
│       └── auth.py                      ← Auth context（Sprint 49.3 強化）
│
└── tests/
    ├── unit/
    └── integration/
```

**為什麼去掉 `0X_` 數字前綴**：
- Python import 慣例不允許 `from 01_orchestrator_loop import ...`
- 順序由 README + 文件管理，目錄名稱保持可 import

### 3. V2 前端目錄樹

```
frontend/                                ← 全新（V1 已移走）
├── package.json                         ← V2 主配置
├── tsconfig.json
├── vite.config.ts
├── README.md
├── index.html
├── public/
└── src/
    ├── main.tsx                         ← Entry
    ├── App.tsx                          ← Router root
    │
    ├── pages/
    │   ├── chat-v2/                     ← Phase 50.2 主流量
    │   │   └── README.md
    │   ├── governance/                  ← Phase 53.3 HITL UI
    │   │   └── README.md
    │   ├── verification/                ← Phase 54.1 verification panel
    │   │   └── README.md
    │   └── (business pages — Phase 55)
    │
    ├── components/
    │   ├── ui/                          ← Shadcn UI 基礎元件
    │   ├── layout/
    │   └── shared/
    │
    ├── features/                        ← 11 範疇 features 目錄（本 Sprint 只建空殼）
    │   ├── orchestrator-loop/           ← 範疇 1 events 顯示
    │   ├── tools/                       ← 範疇 2 tool call viewer
    │   ├── memory/                      ← 範疇 3 memory inspector
    │   ├── state-mgmt/                  ← 範疇 7 state timeline
    │   ├── guardrails/                  ← 範疇 9 governance UI
    │   ├── verification/                ← 範疇 10 verification panel
    │   └── subagent/                    ← 範疇 11 swarm visualizer
    │
    ├── hooks/
    ├── api/                             ← Fetch API 客戶端
    ├── stores/                          ← Zustand
    ├── types/
    └── utils/
```

### 4. 配置檔案最小骨架

#### `backend/pyproject.toml`（V2）

```toml
[project]
name = "ipa-platform-v2"
version = "2.0.0-alpha"
description = "IPA Platform V2 — 11-category agent harness"
requires-python = ">=3.11"

[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio", "black", "isort", "flake8", "mypy"]

[tool.black]
line-length = 100

[tool.isort]
profile = "black"

[tool.mypy]
strict = true
```

#### `backend/requirements.txt`（V2 最小）

```
fastapi>=0.115
uvicorn[standard]>=0.32
pydantic>=2.9
pydantic-settings>=2.5
sqlalchemy[asyncio]>=2.0
asyncpg>=0.30
alembic>=1.13
redis>=5.0
celery>=5.4
opentelemetry-api>=1.27
opentelemetry-sdk>=1.27
```

> **注意**：本 Sprint **不裝** `agent-framework` / `anthropic` / `openai` — 那是 Sprint 49.3 adapters 才需要。

#### `frontend/package.json`（V2 最小）

```json
{
  "name": "ipa-platform-v2-frontend",
  "version": "2.0.0-alpha",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "lint": "eslint src --ext ts,tsx"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.27.0",
    "zustand": "^5.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.6.0",
    "vite": "^5.4.0"
  }
}
```

#### `docker-compose.dev.yml`（最小依賴服務）

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ipa_v2
      POSTGRES_USER: ipa_v2
      POSTGRES_PASSWORD: ipa_v2_dev
    ports: ["5432:5432"]
    volumes: [pg_data_v2:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  rabbitmq:
    image: rabbitmq:3.13-management
    ports: ["5672:5672", "15672:15672"]

  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
    volumes: [qdrant_data_v2:/qdrant/storage]

volumes:
  pg_data_v2:
  qdrant_data_v2:
```

### 5. ABC 空殼範例（11 個範疇都比照辦理）

每個範疇目錄的 `_abc.py` 在本 Sprint 只放「契約輪廓」：

```python
# backend/src/agent_harness/orchestrator_loop/_abc.py
"""
範疇 1：Orchestrator Loop（TAO/ReAct）

本檔在 Sprint 49.1 只定義 ABC 輪廓。
實作在 Phase 50.1。
"""
from abc import ABC, abstractmethod
from typing import AsyncIterator, Any


class AgentLoop(ABC):
    """The TAO loop: think → act → observe，by while True until stop_reason."""

    @abstractmethod
    async def run(self, *, session_id: str, user_input: str) -> AsyncIterator[Any]:
        """執行 loop，yield events。實作在 Phase 50.1。"""
        ...
```

**驗收方式**：`pip install -e .` 後，`from agent_harness.orchestrator_loop import AgentLoop` 必須能 import 成功（NotImplementedError 可接受）。

---

## 待建立的目錄與檔案完整清單

### V1 封存（1 個動作）

- [ ] `git tag v1-final-phase48`
- [ ] `archived/v1-phase1-48/backend/`（從 V1 移過來）
- [ ] `archived/v1-phase1-48/frontend/`（從 V1 移過來）
- [ ] `archived/v1-phase1-48/infrastructure/`（從 V1 移過來）
- [ ] `archived/v1-phase1-48/README.md`（READ-ONLY 警告）

### V2 後端骨架（41 個目錄 + ~30 個檔案）

**根層**：
- [ ] `backend/pyproject.toml`
- [ ] `backend/requirements.txt`
- [ ] `backend/README.md`
- [ ] `backend/alembic.ini`（空殼，Sprint 49.2 填）
- [ ] `backend/src/main.py`（最小 FastAPI app）
- [ ] `backend/tests/unit/.gitkeep`
- [ ] `backend/tests/integration/.gitkeep`

**agent_harness/**（11 範疇 × 3 檔 = 33 檔）：
- [ ] 每個範疇目錄：`__init__.py` + `README.md` + `_abc.py`

**platform/**：
- [ ] `governance/{risk,hitl,audit}/__init__.py`
- [ ] `identity/__init__.py`
- [ ] `observability/__init__.py`
- [ ] `workers/__init__.py`

**adapters/**：
- [ ] `_base/chat_client.py`（ABC）
- [ ] `_base/README.md`
- [ ] `azure_openai/README.md`（標明 Sprint 49.3）
- [ ] `anthropic/README.md`（預留）
- [ ] `maf/README.md`（標明 Sprint 54.2）

**api/v1/**：
- [ ] `chat/README.md`
- [ ] `governance/README.md`
- [ ] `health.py`（本 Sprint 實作 `/health`）

**business_domain/**：
- [ ] `README.md`（標明「Phase 55 才動工」）
- [ ] 5 個業務子目錄 `__init__.py`

**infrastructure/**：
- [ ] `db/__init__.py`
- [ ] `cache/__init__.py`
- [ ] `messaging/__init__.py`
- [ ] `storage/__init__.py`

**core/**：
- [ ] `config/__init__.py`（pydantic Settings 骨架）
- [ ] `exceptions/__init__.py`
- [ ] `logging/__init__.py`

**middleware/**：
- [ ] `tenant.py`（空殼）
- [ ] `auth.py`（空殼）

### V2 前端骨架（~15 個目錄 + ~10 個檔案）

- [ ] `frontend/package.json`
- [ ] `frontend/tsconfig.json`
- [ ] `frontend/vite.config.ts`
- [ ] `frontend/index.html`
- [ ] `frontend/README.md`
- [ ] `frontend/src/main.tsx`
- [ ] `frontend/src/App.tsx`（最小 Router）
- [ ] `frontend/src/pages/chat-v2/README.md`
- [ ] `frontend/src/pages/governance/README.md`
- [ ] `frontend/src/pages/verification/README.md`
- [ ] `frontend/src/features/{orchestrator-loop,tools,memory,state-mgmt,guardrails,verification,subagent}/README.md`

### 根層配置

- [ ] `docker-compose.dev.yml`
- [ ] `.env.example`（V2 版）
- [ ] 根 `README.md` 加 V2 區段（不刪 V1 內容，加「V2 從這裡開始」標題）

---

## 與 11 範疇的關係

| 範疇 | 本 Sprint 產出 | 後續 Sprint 接手 |
|------|-------------|---------------|
| 1. Orchestrator Loop | 目錄 + ABC | Phase 50.1 實作 |
| 2. Tools | 目錄 + ABC | Phase 51.1 實作 |
| 3. Memory | 目錄 + ABC | Phase 51.2 實作 |
| 4. Context Mgmt | 目錄 + ABC | Phase 52.1 實作 |
| 5. Prompt Builder | 目錄 + ABC | Phase 52.2 實作 |
| 6. Output Parser | 目錄 + ABC | Phase 50.1 實作 |
| 7. State Mgmt | 目錄 + ABC | Phase 53.1 實作 |
| 8. Error Handling | 目錄 + ABC | Phase 53.2 實作 |
| 9. Guardrails | 目錄 + ABC | Phase 53.3 實作 |
| 10. Verification | 目錄 + ABC | Phase 54.1 實作 |
| 11. Subagent | 目錄 + ABC | Phase 54.2 實作 |

**本 Sprint 不影響成熟度**：11 範疇全部維持 Level 0（合理 — 還沒實作）。

---

## 依賴與風險

### 依賴

| 依賴 | 說明 | 阻塞點 |
|------|------|--------|
| Phase 48 收尾 | 必須所有 PR merged + main clean | 影響 `git tag v1-final-phase48` |
| Python 3.11+ | pyproject.toml 指定 | 開發者必須升級 |
| Node 20+ | Vite 5 需要 | 開發者必須升級 |
| Docker Desktop | docker-compose 用 | 開發者本機必須有 |

### 風險

| 風險 | 機率 | 影響 | 緩解 |
|------|-----|------|------|
| V1 移動破壞 git history | 低 | 高 | 用 `git mv` 而非 `mv`，保留 history |
| ABC 設計不夠成熟 | 中 | 中 | 標明「契約可在 Phase 50+ 修訂」，不視為固化合約 |
| 開發者誤改 archived/v1 | 中 | 中 | README 警告 + 後續 Sprint 加 pre-commit hook |
| `pip install -e .` fail | 低 | 高 | 本 Sprint 必驗收，不通過不收尾 |
| Docker compose 服務啟動慢 | 低 | 低 | 本 Sprint 不要求性能，能起即可 |

---

## Acceptance Criteria

### 結構驗收

- [ ] `git tag --list | grep v1-final-phase48` 找得到 tag
- [ ] `ls archived/v1-phase1-48/` 包含 backend / frontend / infrastructure
- [ ] `tree backend/src -L 3` 顯示完整 5 層架構
- [ ] `tree frontend/src -L 3` 顯示完整目錄
- [ ] 11 個範疇目錄都有 `README.md` + `_abc.py` + `__init__.py`

### 可啟動驗收

- [ ] `cd backend && pip install -e ".[dev]"` 通過（無錯誤）
- [ ] `cd frontend && npm install` 通過（無錯誤）
- [ ] `docker compose -f docker-compose.dev.yml up -d` 起 4 個服務（postgres / redis / rabbitmq / qdrant）
- [ ] `docker compose ps` 4 個服務都是 healthy / running
- [ ] `cd backend && python -m uvicorn src.main:app --port 8001` 啟動
- [ ] `curl http://localhost:8001/health` 回 `{"status": "ok", "version": "2.0.0-alpha"}`
- [ ] `cd frontend && npm run dev` 啟動 + 瀏覽器看到空白頁

### Import 驗收

- [ ] `python -c "from agent_harness.orchestrator_loop import AgentLoop"` 通過
- [ ] `python -c "from agent_harness.tools import ToolRegistry"` 通過
- [ ] **11 範疇 + 範疇 12（observability）+ §HITL（hitl）ABC 全部可 import**
- [ ] **跨範疇 contracts 全部可 import**：`from agent_harness._contracts import ChatRequest, ToolSpec, LoopState, MemoryHint, TraceContext, ApprovalRequest`

### CI Pipeline 驗收（**新增**）

- [ ] `.github/workflows/backend-ci.yml` 上線：black / isort / flake8 / mypy / pytest 全部執行
- [ ] `.github/workflows/frontend-ci.yml` 上線：lint / build / test 全部執行
- [ ] PR 觸發時 CI 自動執行
- [ ] CI 失敗時 PR 不可 merge（branch protection rule）
- [ ] PR 模板包含「3 大原則 check + 17.md 介面表 check」

### 程式碼品質驗收

- [ ] `cd backend && black --check .` 通過
- [ ] `cd backend && isort --check .` 通過
- [ ] `cd backend && mypy src/` 通過（strict mode）
- [ ] `cd frontend && npm run lint` 通過

### 文件驗收

- [ ] `archived/v1-phase1-48/README.md` 有 READ-ONLY 警告
- [ ] 根 `README.md` 有「V2 從這裡開始」區段
- [ ] 11 個範疇 README 簡述「範疇職責 + 預計實作 Sprint」

### 規範驗收

- [ ] 沒有任何業務邏輯（grep 業務關鍵字應為空）
- [ ] 沒有 LLM 呼叫（grep `openai|anthropic|agent_framework` import 應為空）
- [ ] 11 範疇 ABC 沒有具體實作（只有 `@abstractmethod` + `...`）

### Sprint 結束驗收

- [ ] `sprint-49-1-checklist.md` 100% 勾選
- [ ] `agent-harness-execution/phase-49/sprint-49-1/progress.md` 建立
- [ ] `agent-harness-execution/phase-49/sprint-49-1/retrospective.md` 建立
- [ ] V2 骨架 PR merge 到 main

---

## 不在本 Sprint 範圍

明確排除（避免 scope creep，對齊 22 sprint 路線圖）：

- ❌ DB schema / Alembic（→ Sprint 49.2）
- ❌ ORM models（→ Sprint 49.2）
- ❌ RLS policies + Audit append-only + Qdrant 隔離（→ Sprint 49.3）
- ❌ Adapter 真實作（→ Sprint 49.4）
- ❌ Worker queue 選型 PoC（→ Sprint 49.4）
- ❌ OTel 真實整合 + Jaeger（→ Sprint 49.4）
- ❌ 專案級 lint rules（duplicate-dataclass-check / cross-category-import-check / sync-callback-check）真實作（→ Sprint 49.4）
- ❌ 業務領域代碼（→ Phase 55.1）
- ❌ 任何範疇實作（→ Phase 50+）

> **注意**：本 sprint **必交**基礎 CI pipeline（GitHub Actions backend-ci + frontend-ci），跑 black/isort/flake8/mypy/pytest/eslint/build；專案級 lint rules 推遲到 49.4。

---

## 參考資料

| 文件 | 用途 |
|------|------|
| [02-architecture-design.md](../02-architecture-design.md) | V2 5 層架構設計 |
| [03-rebirth-strategy.md](../03-rebirth-strategy.md) | V1 封存策略 |
| [04-anti-patterns.md](../04-anti-patterns.md) | V1 教訓（避免重蹈） |
| [06-phase-roadmap.md](../06-phase-roadmap.md) | Phase 49-55 路線圖 |
| [07-tech-stack-decisions.md](../07-tech-stack-decisions.md) | 技術選型 |
| [10-server-side-philosophy.md](../10-server-side-philosophy.md) | 3 大最高指導原則 |
| [12-category-contracts.md](../12-category-contracts.md) | 範疇間契約（影響 ABC 設計） |

---

## Sprint 結束後產出

Sprint 結束時，以下兩個目錄完整存在：

```
docs/03-implementation/agent-harness-planning/phase-49-foundation/
├── sprint-49-1-plan.md           ← 本文件
└── sprint-49-1-checklist.md      ← 任務清單

docs/03-implementation/agent-harness-execution/phase-49/sprint-49-1/
├── progress.md                   ← 每日進度（Sprint 期間填寫）
├── retrospective.md              ← Sprint 回顧
└── artifacts/                    ← 產出證據（截圖 / log）
    ├── tree-output.txt           ← `tree backend/src` / `tree frontend/src`
    ├── pip-install-log.txt
    ├── npm-install-log.txt
    ├── docker-compose-ps.txt
    └── health-endpoint-curl.txt
```

---

**Sprint 狀態**：📋 計劃中
**Story Points**：21
**預計開始**：用戶批准後立即（建議週一）
**預計結束**：開始日 + 5 工作天
