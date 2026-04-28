# 技術選型決策

**建立日期**：2026-04-23
**版本**：V2.0

---

## 已確定選型

### LLM 供應商
- **主**：Azure OpenAI GPT-5.4（公司限制）
- **輔**：GPT-5.4-mini（subagent / classifier 用）
- **備援**：Anthropic Claude（公司開放後可切換）
- **架構**：透過 `adapters/_base/chat_client.py` ABC 解耦

### Backend 框架
- **FastAPI**：保留（V1 已用，成熟）
- **Python 3.11+**：使用最新穩定版
- **async/await**：全 async 設計（V1 同步混用要修正）

### Frontend 框架
- **React 18 + TypeScript**：保留
- **Vite**：保留（dev server）
- **shadcn/ui**：保留（V1 抽取）
- **Zustand**：保留（合併 V1 store + stores）
- **Fetch API**：保留（不換 Axios）

### 資料庫
- **PostgreSQL 16**：保留
- **SQLAlchemy 2.x async**：升級至全 async
- **Alembic**：從零 migration

### 快取
- **Redis 7**：保留

### Vector DB
- **Qdrant**：保留（已整合過）
- 設計：tenant-aware namespace

### 開發環境
- **Docker Compose**：強化（解決死 port 問題）
- **WSL2 推薦**（Windows 用戶）

---

## 待決策選型

### 1. Worker Queue（Phase 49.3 PoC 後決定）

| 選項 | 優點 | 缺點 | 評分 |
|------|-----|-----|------|
| **Celery** | 成熟、Python 標準、生態大 | 概念較重、配置複雜 | ⭐⭐⭐ |
| **RQ** | 簡單、輕量 | 功能受限、不夠彈性 | ⭐⭐ |
| **Temporal** | Durable workflow、與 agent loop 天然契合 | 學習曲線、需額外服務 | ⭐⭐⭐⭐ |
| **Kafka + 自建** | 最強彈性 | 過度複雜 | ⭐ |

**初步傾向**：**Temporal**（durable workflow 概念與 agent loop 一拍即合）

**備選**：Celery（如果 Temporal 學習曲線太陡）

**決策時機**：Phase 49.3 早期 PoC 後

### 2. Audit Append-Only Store

| 選項 | 優點 | 缺點 |
|------|-----|-----|
| **PostgreSQL + 觸發器禁止 update/delete** | 簡單、現有 DB 可用 | 不是真正不可篡改 |
| **AWS QLDB** | 真正 immutable | 綁定 AWS |
| **Azure Immutable Storage** | Microsoft 生態 | 較少 Python 支援 |
| **Event Sourcing 模式** | 設計上 append-only | 工程量大 |

**初步傾向**：**PostgreSQL + 觸發器**（Phase 49 簡單版，Phase 56+ 升級）

### 3. Sandbox 實作

| 選項 | 優點 | 缺點 |
|------|-----|-----|
| **Docker container（每個 tool 一個）** | 隔離強 | 啟動慢、資源耗 |
| **Subprocess + seccomp** | 輕量 | Linux only、安全弱 |
| **Firecracker microVM** | 隔離 + 輕量 | 複雜度高 |
| **WebAssembly (WASM)** | 安全、快 | Python sandbox 支援有限 |

**初步傾向**：**Docker container**（成熟、跨平台）

### 4. Observability Stack

| 元件 | 選型 |
|------|-----|
| Tracing | **OpenTelemetry + Jaeger / Tempo** |
| Metrics | **OpenTelemetry + Prometheus** |
| Logs | **結構化 JSON logs + Loki** 或 **ELK** |
| Dashboard | **Grafana** |

### 5. Frontend State 管理升級

| 選項 | 評估 |
|------|-----|
| **Zustand**（保留） | 簡單、V1 已用 |
| **Jotai** | 原子化，更現代 |
| **TanStack Query**（補充） | 用於 API 狀態 |

**建議**：**Zustand 保留 + TanStack Query 補充**（API state 與 client state 分離）

---

## 關鍵設計決策

### Decision 1：Loop 在 Worker 還是 API？

**問題**：Agent loop 是長時操作，放哪？

**選項**：
- A. API process 內跑（FastAPI background task）
- B. 獨立 worker process（Celery / Temporal）

**決策**：**B（worker process）**

**理由**：
- Agent loop 可能跑數分鐘
- API process 需要快速回應
- Worker 可橫向擴展
- 失敗隔離

**實作**：Phase 49.3 + Phase 50.2

### Decision 2：SSE 還是 WebSocket？

**問題**：Loop events 推送機制？

**選項**：
- A. SSE（Server-Sent Events）
- B. WebSocket

**決策**：**A（SSE）**

**理由**：
- Loop 是單向推送（server → client）
- SSE 更簡單（HTTP/1.1 友善）
- V1 已有 SSE 經驗
- 自動重連

### Decision 3：Tool Schema 格式

**問題**：用 OpenAI 還是 Anthropic 格式為主？

**選項**：
- A. OpenAI function calling 格式為主，adapter 轉 Anthropic
- B. 自定義中性格式，adapter 轉雙邊

**決策**：**B（自定義中性格式）**

**理由**：
- ToolSpec 是 V2 自有規格
- Adapter 層負責格式轉換
- 未來新供應商加入無痛

**實作**：Phase 51.1 ToolSpec 設計

### Decision 4：Memory 儲存策略

**問題**：5 層 memory 各用什麼儲存？

| 層 | 儲存 | 理由 |
|---|------|-----|
| Layer 1 System | YAML 檔案 + Redis cache | 變動少、全局共享 |
| Layer 2 Tenant | DB + Vector DB | 結構化 + 語義搜索 |
| Layer 3 Role | DB | 角色規則結構化 |
| Layer 4 User | DB + Vector DB | 個人化記憶 |
| Layer 5 Session | Redis | 短期、TTL 24h |

### Decision 5：Verification 強度

**問題**：每次 loop 都跑 verification 嗎？

**決策**：**主流量強制，但**：
- 簡單查詢（直接回答）：跳過 verification
- 工具呼叫產生內容：跑 RulesBasedVerifier
- 重要產出（報告 / 決策）：跑 LLMJudgeVerifier
- 失敗 self-correction max 2 次

### Decision 6：HITL 觸發策略

**問題**：哪些動作需 HITL？

**決策**：政策化（YAML config）：
```yaml
hitl_policies:
  - tool_pattern: "*_create"  # 所有創建類工具
    risk_level: medium
    policy: ask_once
  
  - tool_pattern: "send_email"
    risk_level: high
    policy: always_ask
  
  - tool_pattern: "delete_*"
    risk_level: critical
    policy: always_ask + multi_approver
```

---

## 環境配置

### 開發環境（Phase 49 起）
```yaml
# docker-compose.dev.yml
services:
  backend-api:
    image: ipa-backend:dev
    ports: ["8000:8000"]
  
  agent-worker:
    image: ipa-backend:dev
    command: ["python", "-m", "platform.workers.runner"]
  
  postgres:
    image: postgres:16
    ports: ["5432:5432"]
  
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
  
  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
  
  rabbitmq:
    image: rabbitmq:3-management
    ports: ["5672:5672", "15672:15672"]
  
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports: ["16686:16686"]
  
  frontend:
    image: ipa-frontend:dev
    ports: ["3000:3000"]
```

### 測試環境
- 同 dev 但用 `docker-compose.test.yml`
- Mock 外部服務（Azure OpenAI 用 vcrpy 錄制）

### 預備環境（Phase 56+）
- K8s deployment（暫不規劃細節）

---

## 套件版本選擇

### Backend Python 套件

| 套件 | 版本 | 用途 |
|------|-----|------|
| fastapi | 最新穩定 | API |
| pydantic | 2.x | 類型 |
| sqlalchemy | 2.x | ORM async |
| asyncpg | 最新 | Postgres async driver |
| alembic | 最新 | Migration |
| redis | 5.x | Redis async client |
| qdrant-client | 最新 | Vector DB |
| openai | 最新 | Azure OpenAI |
| anthropic | 最新 | （備援） |
| opentelemetry-api | 最新 | OTel |
| opentelemetry-sdk | 最新 | OTel |
| pytest | 最新 | 測試 |
| pytest-asyncio | 最新 | Async 測試 |

### Frontend npm 套件

| 套件 | 版本 |
|------|-----|
| react | 18.x |
| typescript | 5.x |
| vite | 最新 |
| zustand | 最新 |
| @tanstack/react-query | 最新 |
| @radix-ui/react-* | shadcn 依賴 |
| tailwindcss | 最新 |

---

## 不選的技術 + 理由

| 不選 | 理由 |
|------|-----|
| LangChain | 過重、抽象層次與本項目不符 |
| LangGraph | 我們是 loop-based，不是 graph-based |
| CrewAI | 過於 role-based，不適合企業治理 |
| Semantic Kernel | 與 MAF 同源，已透過 MAF 整合 |
| Haystack | RAG 框架，本項目自建 |
| Pinecone | 已選 Qdrant |
| MongoDB | 已選 Postgres，不用混 |

---

## 下一步

確認技術選型後：
- `08-glossary.md`：術語表
- 啟動 Phase 49 Sprint 49.1
