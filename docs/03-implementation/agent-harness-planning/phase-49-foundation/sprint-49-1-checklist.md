# Sprint 49.1 — V1 封存 + V2 目錄骨架 + CI Pipeline（Checklist）

**對應 Plan**：[sprint-49-1-plan.md](./sprint-49-1-plan.md)
**Sprint 編號**：49.1
**工作量**：5 工作天
**Story Points**：26 點（**修訂後 +5 點**）
**狀態**：📋 計劃中

## 2026-04-28 整合修訂摘要

本 checklist 已對齊 review 整合，新增任務：
- ✅ 範疇 12 (Observability) ABC 空殼（Day 2）
- ✅ `agent_harness/_contracts/` 跨範疇型別包 10 個檔案（Day 2）
- ✅ `agent_harness/hitl/` HITL 中央化 ABC（Day 2）
- ✅ CI Pipeline GitHub Actions 上線（Day 5）
- ✅ PR 模板（含 3 大原則 + 17.md 介面表 check）（Day 5）

---

## 使用說明

- 每完成一個任務，將 `[ ]` 改為 `[x]`
- ⚠️ **絕對不要刪除未完成項目**（違反 CLAUDE.md「Never Delete Checklist Items」）
- 每天結束在 `agent-harness-execution/phase-49/sprint-49-1/progress.md` 記錄
- **遇到阻塞**：在該任務後加註 `🚧 阻塞：<原因>`，不要跳過

---

## Day 1 — V1 封存 + 根層配置（4 小時）

### 1.1 Phase 48 收尾確認（30 min）

- [ ] **檢查 main branch 狀態**
  - 預估：10 min
  - DoD：`git status` 顯示 clean，`git log main..origin/main` 為空
  - 指令：`git checkout main && git pull && git status`

- [ ] **確認所有 Phase 48 PR 已 merged**
  - 預估：10 min
  - DoD：`gh pr list --state open --label phase-48` 為空

- [ ] **建立工作 branch**
  - 預估：10 min
  - DoD：`git branch --show-current` 顯示 `feature/phase-49-sprint-1-v2-foundation`
  - 指令：`git checkout -b feature/phase-49-sprint-1-v2-foundation`

### 1.2 V1 不可變 tag（15 min）

- [ ] **打 V1 final tag**
  - 預估：10 min
  - DoD：`git tag --list | grep v1-final-phase48` 找得到
  - 指令：`git tag -a v1-final-phase48 -m "V1 final state — Phase 1-48 (27% alignment baseline)"`

- [ ] **推送 tag 到 remote**
  - 預估：5 min
  - DoD：`git ls-remote --tags origin | grep v1-final-phase48` 找得到
  - 指令：`git push origin v1-final-phase48`

### 1.3 V1 移到 archived/（90 min）

- [ ] **建立 archived 目錄**
  - 預估：5 min
  - DoD：`ls archived/` 顯示 `v1-phase1-48/`
  - 指令：`mkdir -p archived/v1-phase1-48`

- [ ] **`git mv backend → archived/v1-phase1-48/backend`**
  - 預估：20 min（檔案多）
  - DoD：`ls backend` 失敗，`ls archived/v1-phase1-48/backend` 成功

- [ ] **`git mv frontend → archived/v1-phase1-48/frontend`**
  - 預估：20 min
  - DoD：同上

- [ ] **`git mv infrastructure → archived/v1-phase1-48/infrastructure`**
  - 預估：15 min
  - DoD：同上

- [ ] **建立 archived/v1-phase1-48/README.md（READ-ONLY 警告）**
  - 預估：10 min
  - DoD：檔案內容包含「READ-ONLY」、「Frozen on 2026-04-XX」、「Phase 1-48」、「Do not modify」

- [ ] **驗證：`docs/`、`claudedocs/`、`reference/` 仍在原位**
  - 預估：5 min
  - DoD：3 個目錄都存在於 repo 根

- [ ] **commit V1 封存**
  - 預估：5 min
  - DoD：`git log --oneline -1` 顯示 `chore(v2): archive V1 to archived/v1-phase1-48/`

### 1.4 根層配置（45 min）

- [ ] **建立 `docker-compose.dev.yml`**
  - 預估：20 min
  - DoD：包含 postgres / redis / rabbitmq / qdrant 4 個服務，volume 命名加 `_v2` 後綴

- [ ] **建立 `.env.example`（V2 版）**
  - 預估：15 min
  - DoD：包含 DB / Redis / RabbitMQ / Qdrant 連線字串，標明「V2」

- [ ] **更新根 `README.md` 加 V2 區段**
  - 預估：10 min
  - DoD：頂部加「V2 從 backend/ + frontend/ 開始；V1 已封存到 archived/」

### 1.5 Day 1 收尾（10 min）

- [ ] **更新 progress.md**
- [ ] **commit Day 1 work**
  - DoD：`git log --oneline | head -5` 顯示當日 2-3 個 commit

---

## Day 2 — V2 後端骨架 Part 1（agent_harness + adapters，6 小時）

### 2.1 backend 根層（45 min）

- [ ] **建立 `backend/` 目錄樹基礎**
  - 預估：5 min
  - DoD：`mkdir -p backend/src backend/tests/{unit,integration}`

- [ ] **建立 `backend/pyproject.toml`**
  - 預估：15 min
  - DoD：依 plan 規格，含 `[project]` + `[project.optional-dependencies]` + `[tool.black/isort/mypy]`

- [ ] **建立 `backend/requirements.txt`**
  - 預估：15 min
  - DoD：依 plan 列表，鎖定主要版本

- [ ] **建立 `backend/README.md`**
  - 預估：10 min
  - DoD：說明 V2 後端入口 + 5 層架構導覽

### 2.2 agent_harness/ 11 範疇空殼（3.5 hours）

> 每個範疇 20 min × 11 = 3 小時 40 分鐘

- [ ] **範疇 1：orchestrator_loop**
  - 預估：20 min
  - DoD：`__init__.py` + `README.md`（職責 + Phase 50.1 接手）+ `_abc.py`（`AgentLoop` ABC）
  - 驗證：`python -c "from agent_harness.orchestrator_loop import AgentLoop"`

- [ ] **範疇 2：tools**
  - 預估：20 min
  - DoD：含 `ToolRegistry` + `ToolSpec` ABC

- [ ] **範疇 3：memory**
  - 預估：20 min
  - DoD：含 `MemoryLayer` ABC（標明 5 層）

- [ ] **範疇 4：context_mgmt**
  - 預估：20 min
  - DoD：含 `Compactor` + `TokenCounter` ABC

- [ ] **範疇 5：prompt_builder**
  - 預估：20 min
  - DoD：含 `PromptBuilder` ABC

- [ ] **範疇 6：output_parser**
  - 預估：20 min
  - DoD：含 `OutputParser` ABC（強調 native tool_calls）

- [ ] **範疇 7：state_mgmt**
  - 預估：20 min
  - DoD：含 `Checkpointer` ABC

- [ ] **範疇 8：error_handling**
  - 預估：20 min
  - DoD：含 `ErrorPolicy` ABC（4 類錯誤）

- [ ] **範疇 9：guardrails**
  - 預估：20 min
  - DoD：含 `Guardrail` ABC（input / output / tool 三種）

- [ ] **範疇 10：verification**
  - 預估：20 min
  - DoD：含 `Verifier` ABC

- [ ] **範疇 11：subagent**
  - 預估：20 min
  - DoD：含 `SubagentDispatcher` ABC（4 種模式，**不含 worktree**）+ `SubagentBudget`

- [ ] **範疇 12：observability（cross-cutting）**
  - 預估：25 min
  - DoD：`observability/_abc.py` 含 `Tracer` ABC（`start_span` async context manager + `record_metric` + `get_current_context`）；README 標明「實作在 backend/src/observability/，本目錄只 own ABC」

- [ ] **§HITL 中央化：hitl/**
  - 預估：20 min
  - DoD：`hitl/_abc.py` 含 `HITLManager` ABC（4 abstract methods：request_approval / wait_for_decision / get_pending / decide）；README 引用 17.md §5

### 2.2.5 跨範疇 single-source 型別包：_contracts/（**新增**，60 min）

- [ ] **建立 `_contracts/__init__.py`**（統一 re-export）
  - 預估：10 min
  - DoD：from `_contracts` import 可拿到所有 dataclass / enum

- [ ] **建立 10 個 contract 檔案**（每個 5 min × 10 = 50 min）
  - [ ] `_contracts/chat.py`（ChatRequest/Response/Message/StopReason/ContentBlock）
  - [ ] `_contracts/tools.py`（ToolSpec/ToolCall/ToolResult/ToolAnnotations/ConcurrencyPolicy）
  - [ ] `_contracts/state.py`（LoopState/TransientState/DurableState/StateVersion）
  - [ ] `_contracts/events.py`（LoopEvent + 22 個子類 stub）
  - [ ] `_contracts/memory.py`（MemoryHint）
  - [ ] `_contracts/prompt.py`（PromptArtifact/CacheBreakpoint）
  - [ ] `_contracts/verification.py`（VerificationResult）
  - [ ] `_contracts/subagent.py`（SubagentBudget/SubagentResult/SubagentMode）
  - [ ] `_contracts/observability.py`（TraceContext/MetricEvent/SpanCategory）
  - [ ] `_contracts/hitl.py`（ApprovalRequest/Decision/HITLPolicy）
  - DoD：每個 dataclass 完整型別 hint；mypy strict 通過

### 2.3 adapters/ 骨架（45 min）

- [ ] **建立 `adapters/_base/chat_client.py`（ChatClient ABC）**
  - 預估：20 min
  - DoD：定義 `chat()` / `stream()` 兩個 abstract method

- [ ] **建立 `adapters/{azure_openai,anthropic,maf}/README.md`**
  - 預估：15 min
  - DoD：3 份 README 標明 Sprint 49.3 / 預留 / Sprint 54.2

- [ ] **建立 `adapters/__init__.py` + `adapters/_base/__init__.py`**
  - 預估：10 min

### 2.4 Day 2 收尾（30 min）

- [ ] **驗證 11 範疇全部可 import**
  - 預估：15 min
  - DoD：跑 `python -c "from agent_harness.{範疇} import {ABC}"` 11 次全部通過

- [ ] **commit Day 2 work**
  - 預估：15 min
  - DoD：`git diff --stat HEAD~1` 顯示 11 範疇 + adapters 檔案

---

## Day 3 — V2 後端骨架 Part 2（platform + api + infra + core，5 小時）

### 3.1 platform/ 骨架（80 min）

- [ ] **建立 `platform/governance/{risk,hitl,audit}/__init__.py` + README**
  - 預估：30 min
  - DoD：3 個子目錄，每個含 README 標明「Phase 53.3 接手」

- [ ] **建立 `platform/identity/__init__.py` + README**
  - 預估：15 min
  - DoD：README 標明多租戶 / 認證 / 角色職責

- [ ] **建立 `platform/observability/__init__.py` + README**
  - 預估：15 min
  - DoD：README 標明 OTel 接入點（Sprint 49.3）

- [ ] **建立 `platform/workers/__init__.py` + README**
  - 預估：20 min
  - DoD：README 標明 Celery vs Temporal 待選（Sprint 49.3 PoC）

### 3.2 api/v1/ 骨架（60 min）

- [ ] **建立 `api/v1/chat/__init__.py` + README**
  - 預估：15 min
  - DoD：README 標明 Phase 50.2 接手

- [ ] **建立 `api/v1/governance/__init__.py` + README**
  - 預估：15 min
  - DoD：README 標明 Phase 53.3 接手

- [ ] **建立 `api/v1/health.py`（最小 endpoint 實作）**
  - 預估：30 min
  - DoD：FastAPI router 有 `GET /health` 回 `{"status": "ok", "version": "2.0.0-alpha"}`

### 3.3 business_domain/ 骨架（30 min）

- [ ] **建立 5 個業務子目錄 `__init__.py`**
  - 預估：15 min
  - DoD：patrol / correlation / rootcause / audit_domain / incident

- [ ] **建立 `business_domain/README.md`（標明 Phase 55）**
  - 預估：15 min
  - DoD：明確標「Phase 55 才動工，本目錄目前為空殼」

### 3.4 infrastructure/ 骨架（30 min）

- [ ] **建立 4 個子目錄 `__init__.py` + README**
  - 預估：30 min
  - DoD：db / cache / messaging / storage 各一個 README

### 3.5 core/ + middleware/ 骨架（45 min）

- [ ] **建立 `core/config/__init__.py`（pydantic Settings 骨架）**
  - 預估：20 min
  - DoD：`Settings(BaseSettings)` 含基本欄位（DB_URL / REDIS_URL）

- [ ] **建立 `core/exceptions/__init__.py`**
  - 預估：10 min
  - DoD：定義 `IPABaseException`

- [ ] **建立 `core/logging/__init__.py`**
  - 預估：5 min
  - DoD：空殼，標明 Sprint 49.3 接 OTel

- [ ] **建立 `middleware/{tenant,auth}.py`（空殼）**
  - 預估：10 min
  - DoD：空 placeholder，標明後續 Sprint 強化

### 3.6 main.py（FastAPI app）（30 min）

- [ ] **建立 `backend/src/main.py`**
  - 預估：30 min
  - DoD：最小 FastAPI app，include `health.py` router，可啟動

### 3.7 Day 3 收尾（30 min）

- [ ] **驗證 `pip install -e ".[dev]"`**
  - 預估：15 min
  - DoD：成功安裝，無錯誤

- [ ] **驗證 FastAPI 啟動**
  - 預估：10 min
  - DoD：`uvicorn src.main:app --port 8001` 啟動 + `curl localhost:8001/health` 回 ok

- [ ] **commit Day 3 work**

---

## Day 4 — V2 前端骨架（5 小時）

### 4.1 frontend 根層（60 min）

- [ ] **建立 `frontend/` 目錄樹基礎**
  - 預估：5 min
  - DoD：`mkdir -p frontend/src/{pages,components,features,hooks,api,stores,types,utils} frontend/public`

- [ ] **建立 `frontend/package.json`**
  - 預估：15 min
  - DoD：依 plan 規格，React 18 + Vite 5 + Zustand + React Router

- [ ] **建立 `frontend/tsconfig.json`**
  - 預估：10 min
  - DoD：strict mode + ES2022

- [ ] **建立 `frontend/vite.config.ts`**
  - 預估：10 min
  - DoD：含 React plugin + 預設 port 3007（避開 V1 的 3005）

- [ ] **建立 `frontend/index.html`**
  - 預估：5 min
  - DoD：基本 HTML + `<div id="root">`

- [ ] **建立 `frontend/README.md`**
  - 預估：15 min
  - DoD：說明 V2 前端入口 + 範疇 features 結構

### 4.2 frontend/src 主檔（60 min）

- [ ] **建立 `src/main.tsx`**
  - 預估：15 min
  - DoD：React.StrictMode + BrowserRouter + App

- [ ] **建立 `src/App.tsx`（最小 Router）**
  - 預估：30 min
  - DoD：路由含 `/chat-v2` + `/governance` + `/verification` 占位頁

- [ ] **建立 `src/components/{ui,layout,shared}/.gitkeep`**
  - 預估：5 min

- [ ] **建立 `src/{hooks,api,stores,types,utils}/.gitkeep`**
  - 預估：10 min

### 4.3 pages/ 占位（45 min）

- [ ] **建立 `pages/chat-v2/README.md` + `index.tsx`（空白頁）**
  - 預估：15 min
  - DoD：README 標明 Phase 50.2 接手；index.tsx 顯示「Chat V2 — coming Phase 50」

- [ ] **建立 `pages/governance/README.md` + `index.tsx`**
  - 預估：15 min
  - DoD：標明 Phase 53.3

- [ ] **建立 `pages/verification/README.md` + `index.tsx`**
  - 預估：15 min
  - DoD：標明 Phase 54.1

### 4.4 features/ 11 範疇 features 占位（55 min）

> 7 個前端有意義的範疇 × 8 min ≈ 1 小時

- [ ] **`features/orchestrator-loop/README.md`**
- [ ] **`features/tools/README.md`**
- [ ] **`features/memory/README.md`**
- [ ] **`features/state-mgmt/README.md`**
- [ ] **`features/guardrails/README.md`**
- [ ] **`features/verification/README.md`**
- [ ] **`features/subagent/README.md`**
  - 共預估：55 min
  - DoD：每個 README 標明對應後端範疇 + 接手 Sprint

### 4.5 Day 4 收尾（60 min）

- [ ] **驗證 `npm install`**
  - 預估：20 min
  - DoD：成功，`node_modules/` 建立

- [ ] **驗證 `npm run dev`**
  - 預估：15 min
  - DoD：Vite 啟動，瀏覽器看到「Chat V2 — coming Phase 50」

- [ ] **驗證 `npm run lint`**
  - 預估：10 min
  - DoD：通過

- [ ] **驗證 `npm run build`**
  - 預估：10 min
  - DoD：通過，`dist/` 產生

- [ ] **commit Day 4 work**
  - 預估：5 min

---

## Day 5 — Docker + 整合驗收 + Sprint 收尾（4 小時）

### 5.0 CI Pipeline 上線（**新增**，60 min）

- [ ] **建立 `.github/workflows/backend-ci.yml`**
  - 預估：20 min
  - DoD：on PR + push to main；steps: setup-python → install deps → black --check → isort --check → flake8 → mypy → pytest（即使 0 test 也要綠）

- [ ] **建立 `.github/workflows/frontend-ci.yml`**
  - 預估：15 min
  - DoD：on PR + push to main；steps: setup-node → npm ci → lint → build → test

- [ ] **建立 `.github/PULL_REQUEST_TEMPLATE.md`**
  - 預估：15 min
  - DoD：含 checklist：3 大原則 / 17.md 介面表 / 範疇歸屬 / 測試 / 文件更新

- [ ] **設定 branch protection rule**（GitHub UI 或 admin）
  - 預估：10 min
  - DoD：main 分支必須 CI green 才可 merge；至少 1 reviewer approve

### 5.1 Docker compose 驗證（45 min）

- [ ] **`docker compose -f docker-compose.dev.yml up -d`**
  - 預估：15 min
  - DoD：4 個服務 status running

- [ ] **驗證每個服務可連線**
  - 預估：30 min
  - DoD：
    - PostgreSQL：`psql -h localhost -U ipa_v2 -d ipa_v2 -c "SELECT 1"` 通過
    - Redis：`redis-cli ping` 回 PONG
    - RabbitMQ：`curl http://localhost:15672/api/overview -u guest:guest` 回 200
    - Qdrant：`curl http://localhost:6333/healthz` 回 ok

### 5.2 端到端啟動驗收（30 min）

- [ ] **後端啟動**
  - 預估：10 min
  - DoD：`uvicorn src.main:app --port 8001` 啟動

- [ ] **前端啟動**
  - 預估：10 min
  - DoD：`npm run dev` 啟動

- [ ] **`/health` endpoint**
  - 預估：10 min
  - DoD：`curl http://localhost:8001/health` 回 `{"status": "ok", "version": "2.0.0-alpha"}`

### 5.3 程式碼品質驗收（45 min）

- [ ] **後端 black**
  - 預估：10 min
  - DoD：`black --check backend/` 通過

- [ ] **後端 isort**
  - 預估：5 min
  - DoD：`isort --check backend/` 通過

- [ ] **後端 mypy**
  - 預估：15 min
  - DoD：`mypy backend/src/` 通過（strict）

- [ ] **後端 flake8**
  - 預估：5 min
  - DoD：`flake8 backend/` 通過

- [ ] **前端 lint**
  - 預估：5 min
  - DoD：`npm run lint` 通過

- [ ] **前端 build**
  - 預估：5 min
  - DoD：`npm run build` 通過

### 5.4 Import 全面驗收（45 min）

- [ ] **跑 11 + 1 範疇 + HITL ABC import 測試**
  - 預估：20 min
  - DoD：寫 `tests/unit/test_imports.py`，13 個 import（11 範疇 + observability + hitl）全部通過

- [ ] **跑 _contracts 統一 import 測試**
  - 預估：10 min
  - DoD：`from agent_harness._contracts import ChatRequest, ToolSpec, LoopState, MemoryHint, PromptArtifact, VerificationResult, SubagentBudget, TraceContext, MetricEvent, ApprovalRequest, ApprovalDecision, HITLPolicy, LoopEvent` 一次 import 全通過

- [ ] **驗證沒有任何業務 / LLM 殘留**
  - 預估：15 min
  - DoD：
    - `grep -r "openai\|anthropic\|agent_framework" backend/src/agent_harness/` 為空
    - `grep -r "patrol\|correlation\|rootcause" backend/src/agent_harness/` 為空

### 5.5 文件補完（45 min）

- [ ] **更新 `agent-harness-planning/README.md`**
  - 預估：10 min
  - DoD：「下一步」改為「Sprint 49.2 已啟動」

- [ ] **建立 `agent-harness-execution/phase-49/sprint-49-1/progress.md`**
  - 預估：15 min
  - DoD：5 天進度記錄完整

- [ ] **建立 `agent-harness-execution/phase-49/sprint-49-1/retrospective.md`**
  - 預估：15 min
  - DoD：含 「做得好 / 待改進 / 下個 Sprint 動作」3 個區塊

- [ ] **產出 artifacts/**
  - 預估：5 min
  - DoD：tree output、pip log、npm log、docker ps、curl health 5 個證據檔

### 5.6 PR + 收尾（45 min）

- [ ] **本 checklist 100% 勾選**
  - 預估：10 min
  - DoD：所有 `[ ]` 變成 `[x]`，無未完成項

- [ ] **建立 PR**
  - 預估：20 min
  - DoD：PR title `Phase 49 Sprint 1: V1 archive + V2 foundation skeleton`，body 連結 plan + checklist

- [ ] **PR self-review**
  - 預估：15 min
  - DoD：自己看 diff 一遍，確認沒有業務邏輯混入

---

## Sprint 結束驗收 Checklist

完成所有上述任務後，最終驗收：

### 結構完整性

- [ ] V1 完全在 `archived/v1-phase1-48/`
- [ ] `git tag --list | grep v1-final-phase48` 找得到
- [ ] `tree backend/src -L 3` 顯示完整 5 層架構（agent_harness / platform / adapters / api / business_domain / infrastructure / core / middleware）
- [ ] `tree frontend/src -L 3` 顯示完整目錄
- [ ] 11 個範疇目錄都有 `README.md` + `_abc.py` + `__init__.py`

### 可啟動性

- [ ] `pip install -e ".[dev]"` 通過
- [ ] `npm install` 通過
- [ ] `docker compose up -d` 4 個服務 healthy
- [ ] FastAPI 啟動 + `/health` 回 ok
- [ ] Vite 啟動 + 瀏覽器看到首頁

### 程式碼品質

- [ ] 後端 black / isort / mypy / flake8 全通過
- [ ] 前端 lint / build 通過

### 範疇 import

- [ ] 11 範疇 ABC 全部可 import

### 規範

- [ ] 沒有業務邏輯
- [ ] 沒有 LLM 直接 import
- [ ] 11 個範疇 ABC 沒有具體實作

### 文件

- [ ] `archived/v1-phase1-48/README.md` 有 READ-ONLY 警告
- [ ] 11 個範疇 README 簡述職責 + 接手 Sprint
- [ ] `progress.md` + `retrospective.md` 完整

### Sprint 治理

- [ ] PR 已建立
- [ ] PR description 連結 plan + checklist
- [ ] 11 範疇成熟度仍為 Level 0（無 regression / 無假升級）

---

## 阻塞處理

如遇阻塞，記錄格式：

```markdown
- [ ] 任務 X
  🚧 **阻塞**：<原因>
  - 發現時間：YYYY-MM-DD HH:MM
  - 嘗試方案 1：失敗，因為 ...
  - 嘗試方案 2：成功，採用
  - 解除時間：YYYY-MM-DD HH:MM
```

---

## 進度統計

| 階段 | 任務數 | 預估時間 |
|------|-------|---------|
| Day 1：V1 封存 + 根層 | 13 | 4h |
| Day 2：agent_harness + adapters（**+範疇 12 + _contracts + hitl 共 +12 任務**）| 30 | 7.5h |
| Day 3：platform + api + infra + core | 16 | 5h |
| Day 4：前端骨架 | 17 | 5h |
| Day 5：CI Pipeline + 整合驗收 + 收尾（**+CI 4 任務**）| 27 | 5h |
| Sprint 結束驗收 | 18 | — |
| **合計** | **121** | **26.5h（5 工作天，部分 buffer 給 Day 2）** |

---

**Sprint 狀態追蹤**：
- [ ] Sprint 啟動（用戶批准 + branch 建立）
- [ ] Day 1 完成
- [ ] Day 2 完成
- [ ] Day 3 完成
- [ ] Day 4 完成
- [ ] Day 5 完成
- [ ] Sprint 結束驗收通過
- [ ] PR merged 到 main
- [ ] Sprint 49.1 ✅ DONE

**下一個 Sprint**：[sprint-49-2-plan.md](./sprint-49-2-plan.md)（DB Schema + Async ORM）— 規劃中
