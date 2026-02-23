# IPA Platform — SRE/DevOps 基礎設施與可擴展性深度分析報告

> **分析日期**: 2026-02-21
> **分析者**: SRE/DevOps Engineer (Claude Opus 4.6)
> **分析對象**: IPA Platform 全面深度分析報告 V2 + 代碼實地驗證
> **分析方法**: 基於分析報告識別問題 → 代碼實地驗證 → 修復方案設計 → 配置範例

---

## 目錄

1. [基礎設施總體評估](#一基礎設施總體評估)
2. [單 Worker + reload=True 修復方案](#二單-worker--reloadtrue-修復方案)
3. [9 個 InMemory 存儲替換策略](#三9-個-inmemory-存儲替換策略)
4. [RabbitMQ 評估 — 保留 vs 移除](#四rabbitmq-評估--保留-vs-移除)
5. [4 Checkpoint 系統統一方案](#五4-checkpoint-系統統一方案)
6. [ContextSynchronizer 並發修復](#六contextsynchronizer-並發修復)
7. [Docker Compose 衝突修復](#七docker-compose-衝突修復)
8. [CORS / Vite 端口不匹配修復](#八cors--vite-端口不匹配修復)
9. [CI/CD Pipeline 建議](#九cicd-pipeline-建議)
10. [Azure 部署架構設計](#十azure-部署架構設計)
11. [監控方案 — OTel + Azure Monitor](#十一監控方案--otel--azure-monitor)
12. [容量規劃和水平擴展策略](#十二容量規劃和水平擴展策略)
13. [報告可能遺漏的基礎設施問題](#十三報告可能遺漏的基礎設施問題)
14. [綜合優先級路線圖](#十四綜合優先級路線圖)

---

## 一、基礎設施總體評估

### 1.1 基礎設施成熟度矩陣

| 維度 | 評分 | 現狀摘要 |
|------|------|----------|
| **運行配置** | 1/10 | 單 Worker + reload=True 硬編碼，不具備生產部署條件 |
| **數據持久化** | 2/10 | 9 個 InMemory 存儲，重啟即丟失運行狀態 |
| **消息隊列** | 0/10 | RabbitMQ Docker 容器運行但零行 Python 代碼使用 |
| **狀態一致性** | 2/10 | 4 個 Checkpoint 系統未協調，ContextSynchronizer 無鎖 |
| **可觀測性** | 4/10 | OTel 依賴已安裝、Prometheus/Grafana 有配置但端點未完全整合 |
| **容器化** | 5/10 | Docker Compose 存在但有 override 衝突、無 Dockerfile 用於應用本身 |
| **CI/CD** | 0/10 | 無 GitHub Actions / Azure DevOps Pipeline 配置 |
| **部署策略** | 0/10 | 無任何 Azure App Service / AKS 配置 |
| **連線池** | 6/10 | PostgreSQL pool_size=5, max_overflow=10 已配置 |
| **健康檢查** | 7/10 | /health 和 /ready 端點存在且檢查 DB 連線 |

### 1.2 基礎設施層比例失衡

代碼驗證確認了報告中指出的比例失衡：

```
backend/src/infrastructure/ — 僅 4 個子目錄:
├── database/    ✅ 18 files — PostgreSQL ORM + Repository
├── cache/       ⚠️ 2 files  — 僅 LLM 快取
├── messaging/   ❌ 1 file   — 空 __init__.py（31 bytes）
└── storage/     ❌ 0 files  — 完全空目錄

→ 3,401 LOC 支撐 228,700 LOC 的上層 = 基礎設施僅佔 1.5%
→ 典型企業平台基礎設施應佔 10-15%
```

### 1.3 代碼驗證結果摘要

| 問題 | 報告描述 | 代碼驗證 | 嚴重程度 |
|------|---------|---------|---------|
| 單 Worker | `uvicorn.run(..., reload=True)` | **確認**: `main.py:238-244` | CRITICAL |
| CORS 不匹配 | 白名單 3000, 前端 3005 | **確認**: `config.py:138` 預設 3000+8000 | HIGH |
| Vite proxy | 指向 8010 | **確認**: `vite.config.ts:30` target 8010 | HIGH |
| RabbitMQ 空殼 | 有 Docker 無代碼 | **確認**: `messaging/__init__.py` 僅 31 bytes | MEDIUM |
| InMemory ×9 | 分布在多個模組 | **確認**: 9 個 class 分布 8 個檔案 | CRITICAL |
| Checkpoint ×4 | 未協調 | **確認**: 4 套獨立系統 | HIGH |
| ContextSync 無鎖 | 2 個實現都無 Lock | **確認**: 兩處均使用 Dict，無 asyncio.Lock | CRITICAL |
| JWT Secret 硬編碼 | `"change-this-to..."` | **確認**: `config.py:29,131` 兩處 | CRITICAL |
| DB Pool 配置 | 未提及具體值 | pool_size=5, max_overflow=10 | 適中 |
| 健康檢查 | 未詳細分析 | `/health` 和 `/ready` 均存在 | 良好 |

---

## 二、單 Worker + reload=True 修復方案

### 2.1 現狀

**位置**: `backend/main.py:235-244`

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,        # ← 生產禁止: 檔案變更自動重載
        log_level="info",
    )
```

### 2.2 風險分析

| 風險 | 影響 | 嚴重度 |
|------|------|--------|
| **reload=True** | 生產環境中任何檔案變更觸發服務重啟；攻擊者若能上傳檔案即可造成 DoS | CRITICAL |
| **單 Worker** | 所有 HTTP 請求在同一 Python 進程內 asyncio 事件迴圈處理；任何 CPU 密集操作（如 LLM 回應解析、風險評估計算）阻塞所有請求 | CRITICAL |
| **無 Gunicorn** | 無法利用多核 CPU，無 worker 崩潰自動重啟，無優雅關機 | HIGH |
| **硬編碼 port** | 部署時需覆蓋 main.py 而非環境變數 | LOW |

### 2.3 修復方案

#### Phase 1: 環境感知啟動（0.5 天）

修改 `backend/main.py`:

```python
if __name__ == "__main__":
    import uvicorn
    from src.core.config import get_settings

    settings = get_settings()
    is_dev = settings.app_env == "development"

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=is_dev,              # 僅開發環境啟用
        workers=1 if is_dev else int(os.environ.get("WEB_CONCURRENCY", 4)),
        log_level=settings.log_level.lower(),
        access_log=is_dev,
        timeout_keep_alive=30,
    )
```

#### Phase 2: Gunicorn 生產部署（1 天）

新增 `backend/gunicorn.conf.py`:

```python
"""Gunicorn configuration for production deployment."""
import multiprocessing
import os

# Server Socket
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
backlog = 2048

# Worker Processes
# 推薦公式: (2 × CPU cores) + 1
# Azure App Service B2: 2 cores → 5 workers
# Azure App Service P1v3: 2 cores → 5 workers
workers = int(os.environ.get("WEB_CONCURRENCY", (2 * multiprocessing.cpu_count()) + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 120                # LLM 調用可能需要較長時間
graceful_timeout = 30
keepalive = 5

# Worker Lifecycle
max_requests = 1000          # 每個 worker 處理 1000 請求後重啟（防止記憶體洩漏）
max_requests_jitter = 50     # 隨機偏移避免所有 worker 同時重啟
preload_app = True           # 預載入應用，共享記憶體中的模組

# Logging
accesslog = "-"              # stdout
errorlog = "-"               # stderr
loglevel = os.environ.get("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process Naming
proc_name = "ipa-platform"

# Server Mechanics
daemon = False
tmp_upload_dir = None

# Hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("IPA Platform starting with Gunicorn")

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def worker_exit(server, worker):
    """Called when a worker process exits."""
    server.log.info(f"Worker exited (pid: {worker.pid})")
```

**啟動命令** (取代 `uvicorn main:app`):

```bash
# 生產環境
gunicorn main:app -c gunicorn.conf.py

# Docker 容器
CMD ["gunicorn", "main:app", "-c", "gunicorn.conf.py"]
```

#### Phase 3: 新增 Gunicorn 依賴

在 `backend/requirements.txt` 新增:

```
gunicorn>=21.2.0             # Production WSGI/ASGI server
```

### 2.4 Multi-Worker 注意事項

切換到多 Worker 後，以下元件**必須**先修復：

| 元件 | 問題 | 原因 |
|------|------|------|
| **9 個 InMemory 存儲** | Worker 間無法共享記憶體 | 每個 Worker 有獨立的 dict |
| **ContextSynchronizer** | 跨 Worker 狀態不一致 | 各 Worker 各自維護 _contexts dict |
| **SSE 連線** | 用戶可能被路由到不同 Worker | SSE 長連線需 sticky session |

**依賴順序**: InMemory 替換 → ContextSync 修復 → Multi-Worker 啟用

### 2.5 工作量估算

| 項目 | 工作量 | 前置條件 |
|------|--------|---------|
| Phase 1: 環境感知啟動 | 0.5 天 | 無 |
| Phase 2: Gunicorn 配置 | 1 天 | 無 |
| Phase 3: Multi-Worker 啟用 | 需等 InMemory 替換完成 | Section 三 |

---

## 三、9 個 InMemory 存儲替換策略

### 3.1 完整清單與代碼位置

| # | Class | 檔案位置 | 風險 | 目標後端 |
|---|-------|---------|------|---------|
| 1 | `InMemoryApprovalStorage` | `orchestration/hitl/controller.py:647` | **CRITICAL** | Redis → PostgreSQL |
| 2 | `InMemoryConversationMemory` | `domain/orchestration/memory/in_memory.py:29` | HIGH | PostgreSQL |
| 3 | `InMemoryCheckpointStorage` | `agent_framework/checkpoint.py:653` | HIGH | Redis（已有 CachedCheckpointStorage） |
| 4 | `InMemoryCheckpointStorage` | `hybrid/switching/switcher.py:183` | HIGH | 統一到 Hybrid Checkpoint |
| 5 | `InMemoryThreadRepository` | `ag_ui/thread/storage.py:276` | HIGH | PostgreSQL |
| 6 | `InMemoryDialogSessionStorage` | `orchestration/guided_dialog/context_manager.py:752` | MEDIUM | Redis |
| 7 | `InMemoryAuditStorage` | `mcp/security/audit.py:265` | MEDIUM | PostgreSQL（合規需求） |
| 8 | `InMemoryCache` | `ag_ui/thread/storage.py:341` | LOW | Redis |
| 9 | `InMemoryTransport` | `mcp/core/transport.py:321` | LOW | 保留（MCP 內部通訊） |

### 3.2 P0: InMemoryApprovalStorage → Redis

**業務影響**: 服務重啟後所有 PENDING 審批消失 — 高風險操作（Shell/SSH 命令執行）可能永遠不被處理

**現狀代碼** (`orchestration/hitl/controller.py:647-683`):

```python
class InMemoryApprovalStorage:
    def __init__(self) -> None:
        self._requests: Dict[str, ApprovalRequest] = {}

    async def save(self, request: ApprovalRequest) -> None:
        self._requests[request.request_id] = request

    async def get(self, request_id: str) -> Optional[ApprovalRequest]:
        return self._requests.get(request_id)
```

**替換方案 — Redis + PostgreSQL 雙寫**:

```python
"""Redis-backed Approval Storage with PostgreSQL audit trail."""
import json
from datetime import timedelta
from typing import Dict, List, Optional

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings


class RedisApprovalStorage:
    """
    Production approval storage using Redis for active requests
    and PostgreSQL for permanent audit trail.

    Redis keys:
        approval:{request_id} — JSON serialized ApprovalRequest (TTL: 24h)
        approval:pending — Set of pending request IDs
        approval:session:{session_id} — Set of request IDs per session

    PostgreSQL table: approval_requests (immutable audit log)
    """

    REDIS_PREFIX = "approval"
    DEFAULT_TTL = timedelta(hours=24)

    def __init__(
        self,
        redis_client: aioredis.Redis,
        db_session_factory=None,
    ):
        self._redis = redis_client
        self._db_factory = db_session_factory

    async def save(self, request: ApprovalRequest) -> None:
        """Save request to Redis + PostgreSQL."""
        key = f"{self.REDIS_PREFIX}:{request.request_id}"
        data = request.to_dict()  # 假設 ApprovalRequest 有 to_dict()

        pipe = self._redis.pipeline()
        pipe.setex(key, self.DEFAULT_TTL, json.dumps(data))
        pipe.sadd(f"{self.REDIS_PREFIX}:pending", request.request_id)
        if request.session_id:
            pipe.sadd(
                f"{self.REDIS_PREFIX}:session:{request.session_id}",
                request.request_id,
            )
        await pipe.execute()

        # PostgreSQL audit trail (async, non-blocking)
        if self._db_factory:
            try:
                async with self._db_factory() as session:
                    await self._persist_to_db(session, request)
            except Exception as e:
                # Log but don't fail — Redis is the source of truth for active state
                logger.error(f"Failed to persist approval to DB: {e}")

    async def get(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get request from Redis."""
        key = f"{self.REDIS_PREFIX}:{request_id}"
        data = await self._redis.get(key)
        if data is None:
            return None
        return ApprovalRequest.from_dict(json.loads(data))

    async def update(self, request: ApprovalRequest) -> None:
        """Update request status."""
        key = f"{self.REDIS_PREFIX}:{request.request_id}"
        data = request.to_dict()
        await self._redis.setex(key, self.DEFAULT_TTL, json.dumps(data))

        # Remove from pending if resolved
        if request.status != ApprovalStatus.PENDING:
            await self._redis.srem(
                f"{self.REDIS_PREFIX}:pending", request.request_id
            )

        # Update PostgreSQL
        if self._db_factory:
            try:
                async with self._db_factory() as session:
                    await self._update_db(session, request)
            except Exception as e:
                logger.error(f"Failed to update approval in DB: {e}")

    async def list_pending(self) -> List[ApprovalRequest]:
        """List all pending requests."""
        pending_ids = await self._redis.smembers(f"{self.REDIS_PREFIX}:pending")
        if not pending_ids:
            return []

        pipe = self._redis.pipeline()
        for rid in pending_ids:
            pipe.get(f"{self.REDIS_PREFIX}:{rid.decode() if isinstance(rid, bytes) else rid}")
        results = await pipe.execute()

        requests = []
        for data in results:
            if data:
                req = ApprovalRequest.from_dict(json.loads(data))
                if req.status == ApprovalStatus.PENDING:
                    requests.append(req)
        return requests

    async def delete(self, request_id: str) -> None:
        """Delete request from Redis (soft delete in PostgreSQL)."""
        pipe = self._redis.pipeline()
        pipe.delete(f"{self.REDIS_PREFIX}:{request_id}")
        pipe.srem(f"{self.REDIS_PREFIX}:pending", request_id)
        await pipe.execute()
```

**PostgreSQL Schema**:

```sql
-- Alembic migration: approval_requests
CREATE TABLE approval_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(100) UNIQUE NOT NULL,
    session_id VARCHAR(100),
    risk_level VARCHAR(20) NOT NULL,
    description TEXT,
    requester VARCHAR(100),
    approver VARCHAR(100),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    timeout_minutes INTEGER DEFAULT 30,
    metadata JSONB DEFAULT '{}',

    -- Indexes
    CONSTRAINT chk_status CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'EXPIRED', 'CANCELLED'))
);

CREATE INDEX idx_approval_status ON approval_requests(status);
CREATE INDEX idx_approval_session ON approval_requests(session_id);
CREATE INDEX idx_approval_created ON approval_requests(created_at);
```

**工作量**: 2 天

### 3.3 P1: 其他 HIGH 優先級替換

#### InMemoryThreadRepository → PostgreSQL

**檔案**: `ag_ui/thread/storage.py:276`

需新增 PostgreSQL 表:

```sql
CREATE TABLE chat_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id VARCHAR(100) UNIQUE NOT NULL,
    session_id VARCHAR(100) NOT NULL,
    title VARCHAR(500),
    messages JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_archived BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_thread_session ON chat_threads(session_id);
CREATE INDEX idx_thread_updated ON chat_threads(updated_at DESC);
```

**工作量**: 1.5 天

#### InMemoryConversationMemory → PostgreSQL

**檔案**: `domain/orchestration/memory/in_memory.py:29`

使用與 chat_threads 相似的 schema，但存儲結構化對話記錄。

**工作量**: 1 天

#### InMemoryAuditStorage → PostgreSQL

**檔案**: `mcp/security/audit.py:265`

```sql
CREATE TABLE mcp_audit_logs (
    id BIGSERIAL PRIMARY KEY,
    event_id VARCHAR(100) UNIQUE NOT NULL,
    server_name VARCHAR(50) NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    user_id VARCHAR(100),
    action VARCHAR(50) NOT NULL,
    parameters JSONB,
    result VARCHAR(20),  -- 'success', 'denied', 'error'
    risk_level VARCHAR(20),
    duration_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Partition by month for performance
    CONSTRAINT chk_result CHECK (result IN ('success', 'denied', 'error'))
);

CREATE INDEX idx_audit_server ON mcp_audit_logs(server_name, created_at);
CREATE INDEX idx_audit_user ON mcp_audit_logs(user_id, created_at);
CREATE INDEX idx_audit_tool ON mcp_audit_logs(tool_name);
```

**合規要求**: 審計日誌必須不可篡改、保留至少 1 年。建議使用 PostgreSQL Table Partitioning 按月分區。

**工作量**: 1.5 天

### 3.4 P2: MEDIUM / LOW 替換

| Class | 替換方案 | 工作量 |
|-------|---------|--------|
| `InMemoryDialogSessionStorage` | Redis（帶 TTL，對話完成後過期） | 1 天 |
| `InMemoryCache` (ag_ui) | 直接使用已有的 Redis 客戶端 | 0.5 天 |
| `InMemoryTransport` (MCP) | **保留** — MCP stdio 內部通訊用途，不影響持久化 | 0 |
| `InMemoryCheckpointStorage` (×2) | 見 Section 五 統一方案 | 包含在 Checkpoint 統一工作中 |

### 3.5 總工作量

| 優先級 | 項目數 | 工作量 |
|--------|--------|--------|
| P0 | 1 (ApprovalStorage) | 2 天 |
| P1 | 3 (Thread, Conversation, Audit) | 4 天 |
| P2 | 2 (Dialog, Cache) | 1.5 天 |
| 保留 | 1 (Transport) | 0 |
| Checkpoint 統一 | 2 | 見 Section 五 |
| **合計** | **9** | **~7.5 天 + Checkpoint** |

---

## 四、RabbitMQ 評估 — 保留 vs 移除

### 4.1 現狀

**Docker Compose**: `docker-compose.yml:69-87` — RabbitMQ 3.12 容器正常運行

**Python 依賴**: `requirements.txt:34` — `aio-pika>=9.3.0` 已安裝

**實際使用**: **零行 Python 代碼使用 RabbitMQ**
- `messaging/__init__.py` 僅含 `# Messaging infrastructure`（31 bytes）
- `config.py:71-84` 有連線配置但無人調用
- 搜索 `rabbitmq|pika|aio_pika|amqp` 在 `backend/src/` 中僅有配置引用和字串匹配

### 4.2 方案比較

#### 方案 A: 保留並實現 RabbitMQ（推薦用於中期）

**適用場景**:
- 長時間運行的 Agent 任務（>30s）需要異步處理
- 多 Worker 間的任務分派
- 事件驅動的審計日誌寫入
- Swarm 多 Agent 協調的消息傳遞

**需要實現的 Queue**:

```
Exchange: ipa.direct (direct exchange)
├── Queue: agent.execution    — Agent 執行任務
├── Queue: audit.log          — 異步審計寫入
├── Queue: notification.send  — Teams/Email 通知
├── Queue: checkpoint.save    — Checkpoint 持久化
└── Queue: swarm.coordination — Swarm Worker 協調

Exchange: ipa.topic (topic exchange)
├── Queue: events.#           — 所有事件（監控用）
├── Queue: events.security.*  — 安全事件
└── Queue: events.hitl.*      — HITL 相關事件
```

**工作量**: 5-8 天（含 Publisher、Consumer、Worker Pool）

#### 方案 B: 移除 RabbitMQ，使用 Redis Pub/Sub + Redis Queue

**優點**:
- 減少一個基礎設施依賴
- Redis 已經在使用中
- 對於 RAPO 規模（20-50 並發用戶）足夠

**缺點**:
- Redis Pub/Sub 不保證消息傳遞（fire-and-forget）
- 無內建的死信隊列（DLQ）
- 無消息確認機制（ack）
- 不適合需要可靠傳遞的場景（如審計日誌）

**替代選擇**: 使用 Redis Streams（Redis 5.0+）作為輕量級消息隊列:

```python
# Redis Streams 提供:
# - 消費者群組（Consumer Group）
# - 消息確認（ACK）
# - 消息持久化
# - 回溯讀取

# 範例：發布 Agent 執行任務
await redis.xadd("agent:execution", {"task_id": task_id, "payload": json.dumps(data)})

# 範例：消費者群組消費
await redis.xreadgroup("worker-group", "worker-1", {"agent:execution": ">"}, count=1)
```

#### 方案 C: 目前完全移除（推薦用於短期）

**理由**:
- 當前 0% 使用率，但佔用 Docker 資源（RAM ~200MB）
- RAPO 初期（<20 用戶）不需要消息隊列
- FastAPI Background Tasks 足以處理短期異步需求

**短期替代**:

```python
from fastapi import BackgroundTasks

@router.post("/agents/{agent_id}/execute")
async def execute_agent(
    agent_id: str,
    background_tasks: BackgroundTasks,
):
    # 同步驗證和風險評估
    risk = await risk_assessor.assess(request)

    if risk.level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        # HITL 審批（同步等待）
        approval = await hitl_controller.request_approval(request)
        if not approval.approved:
            return {"status": "rejected"}

    # 異步執行 Agent 任務
    background_tasks.add_task(execute_agent_task, agent_id, request)
    return {"status": "accepted", "task_id": task_id}
```

### 4.3 建議

```
短期 (Phase A-B): 方案 C — 移除 RabbitMQ Docker 容器，用 BackgroundTasks
中期 (Phase C):   方案 B — 引入 Redis Streams 替代簡單隊列場景
長期 (Phase D+):  方案 A — 如需跨服務通訊或複雜路由，引入 RabbitMQ/Azure Service Bus
```

---

## 五、4 Checkpoint 系統統一方案

### 5.1 4 套系統驗證

代碼驗證確認 4 套獨立的 Checkpoint 系統：

| # | 系統 | 位置 | 後端選項 | 現狀 |
|---|------|------|---------|------|
| 1 | **MAF Checkpoint** | `agent_framework/checkpoint.py` | InMemory, Postgres, Cached | `InMemoryCheckpointStorage` 為預設 |
| 2 | **Hybrid Checkpoint** | `hybrid/checkpoint/` | Memory, Redis, Postgres, Filesystem | 4 後端完整實現（品質最高） |
| 3 | **Multiturn Checkpoint** | `agent_framework/multiturn/checkpoint_storage.py` | Redis, Postgres, File | 無 InMemory 但獨立於 #1 |
| 4 | **Switching Checkpoint** | `hybrid/switching/switcher.py:183` | InMemory only | 最簡陋，僅 Dict |

### 5.2 系統間差異分析

```
MAF Checkpoint:
├── 基類: CheckpointStorageAdapter (ABC)
├── 方法: save, load, delete, list_checkpoints
├── 特點: CachedCheckpointStorage 包裝 Redis + Postgres
└── 問題: 預設使用 InMemoryCheckpointStorage

Hybrid Checkpoint:
├── 基類: UnifiedCheckpointStorage (ABC)
├── 方法: save, load, delete, exists, query, get_stats, cleanup_expired, restore
├── 特點: 4 後端 + 版本遷移 + 壓縮序列化 + TTL 過期
├── MemoryCheckpointStorage 使用 threading.Lock ← 有鎖（唯一有的）
└── 品質最高，應作為統一基礎

Multiturn Checkpoint:
├── 基類: BaseCheckpointStorage → CheckpointStorage
├── 方法: save, load, delete, list_all, list_by_thread
├── 特點: 按 thread_id 索引，適合多輪對話
└── 與 MAF Checkpoint 接口不同

Switching Checkpoint:
├── 基類: CheckpointStorageProtocol (Protocol)
├── 方法: save_state, load_state, delete_state
├── 特點: 僅用於模式切換時的狀態快照
└── 僅有 InMemory 實現
```

### 5.3 統一方案

**策略**: 以 Hybrid Checkpoint 為基礎，建立統一接口，其他 3 套系統透過 Adapter 接入。

```python
"""Unified Checkpoint Registry — 統一 4 套系統的 Checkpoint 管理。"""
from enum import Enum
from typing import Dict, Optional

class CheckpointDomain(Enum):
    """Checkpoint 所屬領域。"""
    MAF = "maf"                # Agent Framework 執行
    HYBRID = "hybrid"          # 混合編排
    MULTITURN = "multiturn"    # 多輪對話
    SWITCHING = "switching"    # 模式切換

class UnifiedCheckpointRegistry:
    """
    統一 Checkpoint 註冊表。

    所有 4 套 Checkpoint 系統共享同一個存儲後端（Redis 或 PostgreSQL），
    通過 domain prefix 區分。
    """

    def __init__(self, storage_backend):
        """
        Args:
            storage_backend: UnifiedCheckpointStorage 的實現
                            (RedisCheckpointStorage 或 PostgresCheckpointStorage)
        """
        self._backend = storage_backend
        self._domain_adapters: Dict[CheckpointDomain, "DomainAdapter"] = {}

    def get_storage(self, domain: CheckpointDomain):
        """獲取特定領域的 Checkpoint 存儲。"""
        if domain not in self._domain_adapters:
            self._domain_adapters[domain] = DomainAdapter(
                backend=self._backend,
                domain=domain,
            )
        return self._domain_adapters[domain]

    async def get_unified_stats(self) -> dict:
        """獲取所有領域的統合統計。"""
        stats = {}
        for domain in CheckpointDomain:
            adapter = self.get_storage(domain)
            stats[domain.value] = await adapter.get_stats()
        return stats

    async def cleanup_all(self) -> int:
        """清理所有領域的過期 Checkpoint。"""
        total = 0
        for domain in CheckpointDomain:
            adapter = self.get_storage(domain)
            total += await adapter.cleanup_expired()
        return total
```

**Redis Key Schema**:

```
checkpoint:maf:{session_id}:{checkpoint_id}
checkpoint:hybrid:{session_id}:{checkpoint_id}
checkpoint:multiturn:{thread_id}:{checkpoint_id}
checkpoint:switching:{session_id}:{checkpoint_id}
```

### 5.4 遷移步驟

1. **建立 UnifiedCheckpointRegistry** — 新增檔案
2. **MAF Checkpoint Adapter** — 包裝 Hybrid 後端到 MAF 接口
3. **Multiturn Adapter** — 包裝 Hybrid 後端到 Multiturn 接口
4. **Switching Adapter** — 包裝 Hybrid 後端到 Switching 接口
5. **修改各模組** — 注入 Registry 而非直接使用 InMemory
6. **配置切換** — 環境變數控制後端選擇

### 5.5 工作量

| 項目 | 工作量 |
|------|--------|
| UnifiedCheckpointRegistry | 1 天 |
| 3 個 Domain Adapter | 2 天 |
| 各模組注入修改 | 1.5 天 |
| 測試 | 1.5 天 |
| **合計** | **6 天** |

---

## 六、ContextSynchronizer 並發修復

### 6.1 現狀驗證

**存在 2 個獨立的 ContextSynchronizer**:

| 實現 | 位置 | LOC | 問題 |
|------|------|-----|------|
| #1 `hybrid/context/sync/synchronizer.py:63` | Hybrid 層 | 629 | `_context_versions: Dict` 無鎖 |
| #2 `claude_sdk/hybrid/synchronizer.py:278` | Claude SDK 層 | 892 | `_contexts: Dict` + `_snapshots: Dict` 無鎖 |

**#1 (Hybrid) 代碼確認**:

```python
class ContextSynchronizer:
    def __init__(self, ...):
        # Version tracking per context — 無 Lock 保護
        self._context_versions: Dict[str, int] = {}
        # Rollback snapshots — 無 Lock 保護
        self._rollback_snapshots: Dict[str, List[HybridContext]] = {}
```

**#2 (Claude SDK) 代碼確認**:

```python
class ContextSynchronizer:
    def __init__(self, ...):
        self._contexts: Dict[str, ContextState] = {}        # 無 Lock
        self._snapshots: Dict[str, List[ContextSnapshot]] = {}  # 無 Lock
        self._sync_listeners: List[Callable[...]] = []       # 無 Lock
```

### 6.2 風險場景

```
Worker A (ConcurrentBuilder)          Worker B (ConcurrentBuilder)
    │                                       │
    ├─ read context["state"] → "v1"         │
    │                                       ├─ read context["state"] → "v1"
    ├─ compute new_state                    │
    │                                       ├─ compute different_state
    ├─ write context["state"] = "v2"        │
    │                                       ├─ write context["state"] = "v3"
    │                                       │
    └─ 結果: "v2" 被 "v3" 覆蓋，Worker A 的狀態丟失
```

### 6.3 修復方案 — asyncio.Lock

**方案選擇**:

| 方案 | 適用場景 | 複雜度 |
|------|---------|--------|
| `asyncio.Lock` | 單進程 (單 Worker) | 低 |
| Redis Distributed Lock (`redlock`) | 多進程 (多 Worker) | 中 |
| PostgreSQL Advisory Lock | 需要持久化保證 | 高 |

**建議**: 分兩階段
- **Phase A (單 Worker)**: asyncio.Lock — 立即修復
- **Phase C (多 Worker)**: Redis Distributed Lock — 配合 Gunicorn 多 Worker

#### Phase A: asyncio.Lock 修復

**#1 Hybrid ContextSynchronizer**:

```python
class ContextSynchronizer:
    def __init__(self, ...):
        self._conflict_resolver = conflict_resolver or ConflictResolver()
        self._event_publisher = event_publisher or SyncEventPublisher()
        self._max_retries = max_retries
        self._timeout_ms = timeout_ms
        self._auto_resolve_conflicts = auto_resolve_conflicts

        # Version tracking per context
        self._context_versions: Dict[str, int] = {}
        # Rollback snapshots
        self._rollback_snapshots: Dict[str, List[HybridContext]] = {}
        self._max_snapshots = 5

        # 新增: 並發控制
        self._lock = asyncio.Lock()
        self._context_locks: Dict[str, asyncio.Lock] = {}

    def _get_context_lock(self, context_id: str) -> asyncio.Lock:
        """獲取特定 context 的細粒度鎖。"""
        if context_id not in self._context_locks:
            self._context_locks[context_id] = asyncio.Lock()
        return self._context_locks[context_id]

    async def sync(self, source, target_type, strategy=...):
        context_id = source.context_id
        lock = self._get_context_lock(context_id)

        async with lock:  # ← 加鎖
            # ... 原有邏輯不變 ...
            pass
```

**#2 Claude SDK ContextSynchronizer**:

```python
class ContextSynchronizer:
    def __init__(self, ...):
        self._config = config or HybridSessionConfig()
        self._conflict_resolution = conflict_resolution
        self._contexts: Dict[str, ContextState] = {}
        self._snapshots: Dict[str, List[ContextSnapshot]] = {}
        self._sync_listeners: List[Callable[...]] = []
        self._sync_count = 0
        self._last_sync_time: Optional[float] = None

        # 新增: 並發控制
        self._lock = asyncio.Lock()

    def create_context(self, ...):
        # 這是同步方法，改為 async 或使用 threading.Lock
        # 由於 FastAPI 是 async，建議改為 async
        pass

    async def create_context(self, ...):
        async with self._lock:
            context = ContextState(...)
            self._contexts[context.context_id] = context
            self._snapshots[context.context_id] = []
            return context
```

#### Phase C: Redis Distributed Lock

```python
import redis.asyncio as aioredis

class DistributedContextLock:
    """Redis-based distributed lock for multi-worker environments."""

    def __init__(self, redis_client: aioredis.Redis, prefix: str = "ctx_lock"):
        self._redis = redis_client
        self._prefix = prefix

    async def acquire(self, context_id: str, timeout: int = 30) -> bool:
        """嘗試獲取分佈式鎖。"""
        key = f"{self._prefix}:{context_id}"
        lock_id = str(uuid.uuid4())
        acquired = await self._redis.set(
            key, lock_id, nx=True, ex=timeout
        )
        if acquired:
            return lock_id
        return None

    async def release(self, context_id: str, lock_id: str) -> bool:
        """釋放分佈式鎖（僅持有者可釋放）。"""
        key = f"{self._prefix}:{context_id}"
        # Lua script 保證原子性
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        result = await self._redis.eval(script, 1, key, lock_id)
        return bool(result)
```

### 6.4 工作量

| 項目 | 工作量 |
|------|--------|
| Phase A: asyncio.Lock 兩處修復 | 1 天 |
| Phase C: Redis Distributed Lock | 2 天 |
| 測試（並發場景模擬） | 1 天 |
| **合計** | **4 天** |

---

## 七、Docker Compose 衝突修復

### 7.1 現狀

**衝突**: `docker-compose.yml` 和 `docker-compose.override.yml` 中 Prometheus 和 Grafana 定義衝突。

| 項目 | docker-compose.yml | docker-compose.override.yml |
|------|-------------------|---------------------------|
| **Prometheus 版本** | `prom/prometheus:v2.48.0` | `prom/prometheus:v2.45.0` |
| **Prometheus 配置路徑** | `./monitoring/prometheus/prometheus.yml` | `./monitoring/prometheus.yml` |
| **Grafana 版本** | `grafana/grafana:10.2.2` | `grafana/grafana:10.0.0` |
| **Grafana 密碼** | `admin` (env var) | `admin123` (硬編碼) |
| **Prometheus profile** | `monitoring` (需顯式啟用) | 無 profile (預設啟用) |
| **container_name** | `ipa-prometheus` | `ipa-prometheus` (重複) |
| **Compose version** | 無 (v2+) | `version: '3.8'` (已廢棄) |

### 7.2 額外發現: n8n 硬編碼憑證

`docker-compose.override.yml:17-18`:
```yaml
- N8N_BASIC_AUTH_USER=admin
- N8N_BASIC_AUTH_PASSWORD=admin123
```

### 7.3 修復方案

#### 方案 A: 統一到 docker-compose.yml（推薦）

刪除 `docker-compose.override.yml`，將 n8n 整合為 optional profile:

```yaml
# docker-compose.yml — 新增 n8n 為 tools profile
  n8n:
    image: n8nio/n8n:1.73  # 鎖定版本
    container_name: ipa-n8n
    profiles: ["tools"]
    ports:
      - "5678:5678"
    environment:
      N8N_BASIC_AUTH_ACTIVE: "true"
      N8N_BASIC_AUTH_USER: ${N8N_USER:-admin}
      N8N_BASIC_AUTH_PASSWORD: ${N8N_PASSWORD:-}  # 必須從 .env 提供
      N8N_HOST: localhost
      N8N_PORT: 5678
      N8N_PROTOCOL: http
      N8N_SECURE_COOKIE: "false"
      WEBHOOK_URL: http://host.docker.internal:8000
      GENERIC_TIMEZONE: Asia/Taipei
      TZ: Asia/Taipei
    volumes:
      - n8n_data:/home/node/.n8n
    networks:
      - ipa-network
    restart: unless-stopped
```

#### 方案 B: 修復 override 使其不衝突

如果需要保留 override（用於開發者個別覆蓋），則:
1. 移除 override 中的 prometheus/grafana 定義
2. 修正 `version` key（移除，使用 v2+ 格式）
3. 將 n8n 保留在 override 中

### 7.4 統一版本建議

```yaml
# 鎖定版本避免意外升級
postgres: postgres:16-alpine
redis: redis:7-alpine
rabbitmq: rabbitmq:3.12-management-alpine  # 或移除（見 Section 四）
jaeger: jaegertracing/all-in-one:1.53
prometheus: prom/prometheus:v2.48.0
grafana: grafana/grafana:10.2.2
n8n: n8nio/n8n:1.73
```

### 7.5 工作量

| 項目 | 工作量 |
|------|--------|
| 統一 docker-compose.yml | 0.5 天 |
| 移除/清理 override | 0.5 天 |
| 驗證所有服務啟動正常 | 0.5 天 |
| **合計** | **1.5 天** |

---

## 八、CORS / Vite 端口不匹配修復

### 8.1 現狀

```
問題 #1: CORS Origin 不匹配
──────────────────────────
backend/src/core/config.py:138
  cors_origins: str = "http://localhost:3000,http://localhost:8000"
                                        ^^^^
frontend 在 port 3005 → 瀏覽器 CORS 策略攔截

問題 #2: Vite Proxy 不匹配
──────────────────────────
frontend/vite.config.ts:29-33
  proxy: {
    '/api': {
      target: 'http://localhost:8010',  ← 8010
                                ^^^^
backend 在 port 8000 → 開發環境 API 請求打不通
```

### 8.2 修復方案（30 分鐘）

**`backend/src/core/config.py:138`**:

```python
# Before
cors_origins: str = "http://localhost:3000,http://localhost:8000"

# After
cors_origins: str = "http://localhost:3005,http://localhost:8000"
```

**`frontend/vite.config.ts:30`**:

```typescript
// Before
target: 'http://localhost:8010',

// After
target: 'http://localhost:8000',
```

### 8.3 生產配置建議

CORS 應從環境變數讀取:

```python
# config.py — 已有此機制，只需修改預設值
cors_origins: str = Field(
    default="http://localhost:3005",
    description="Comma-separated CORS origins"
)

# .env.production
CORS_ORIGINS=https://ipa.rapo.ricoh.com
```

CORS Middleware 加固:

```python
# main.py — 限制方法和標頭
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Guest-Id", "X-Request-Id"],
    max_age=3600,  # 預檢請求快取 1 小時
)
```

### 8.4 工作量

| 項目 | 工作量 |
|------|--------|
| CORS origin 修復 | 10 分鐘 |
| Vite proxy 修復 | 10 分鐘 |
| CORS 方法/標頭加固 | 30 分鐘 |
| **合計** | **~1 小時** |

---

## 九、CI/CD Pipeline 建議

### 9.1 現狀

代碼倉庫中**無任何 CI/CD 配置**:
- 無 `.github/workflows/`
- 無 `azure-pipelines.yml`
- 無 `Dockerfile`（用於應用容器化）

### 9.2 GitHub Actions 配置

#### `.github/workflows/ci.yml`

```yaml
name: IPA Platform CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: '3.11'
  NODE_VERSION: '20'

jobs:
  # ──────────────────────────────────────────
  # Backend CI
  # ──────────────────────────────────────────
  backend-lint:
    name: Backend Lint & Type Check
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
      - run: pip install -r requirements.txt
      - run: black --check .
      - run: isort --check-only .
      - run: flake8 .
      - run: mypy src/ --ignore-missing-imports

  backend-test:
    name: Backend Tests
    runs-on: ubuntu-latest
    needs: backend-lint
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: ipa_test
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_password
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    defaults:
      run:
        working-directory: backend
    env:
      DB_HOST: localhost
      DB_PORT: 5432
      DB_NAME: ipa_test
      DB_USER: test_user
      DB_PASSWORD: test_password
      REDIS_HOST: localhost
      REDIS_PORT: 6379
      APP_ENV: testing
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
      - run: pip install -r requirements.txt
      - run: pytest tests/unit/ -v --cov=src --cov-report=xml
      - run: pytest tests/integration/ -v --timeout=60
      - uses: codecov/codecov-action@v4
        with:
          file: backend/coverage.xml
          flags: backend

  backend-security:
    name: Backend Security Scan
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      - run: pip install pip-audit bandit
      - run: pip-audit -r requirements.txt
      - run: bandit -r src/ -ll

  # ──────────────────────────────────────────
  # Frontend CI
  # ──────────────────────────────────────────
  frontend-lint:
    name: Frontend Lint & Type Check
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run lint
      - run: npx tsc --noEmit

  frontend-test:
    name: Frontend Tests
    runs-on: ubuntu-latest
    needs: frontend-lint
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run test -- --coverage
      - uses: codecov/codecov-action@v4
        with:
          flags: frontend

  frontend-build:
    name: Frontend Build
    runs-on: ubuntu-latest
    needs: frontend-lint
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: frontend-dist
          path: frontend/dist/
```

#### `.github/workflows/cd.yml`（Azure 部署）

```yaml
name: IPA Platform CD

on:
  push:
    branches: [main]
    paths-ignore:
      - 'docs/**'
      - '*.md'

env:
  AZURE_WEBAPP_NAME: ipa-platform-backend
  AZURE_SWA_NAME: ipa-platform-frontend

jobs:
  deploy-backend:
    name: Deploy Backend
    runs-on: ubuntu-latest
    needs: [backend-test]  # 引用 CI workflow 的 job
    environment: production
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      - uses: azure/webapps-deploy@v3
        with:
          app-name: ${{ env.AZURE_WEBAPP_NAME }}
          package: backend/

  deploy-frontend:
    name: Deploy Frontend
    runs-on: ubuntu-latest
    needs: [frontend-build]
    environment: production
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: frontend-dist
          path: frontend/dist/
      - uses: Azure/static-web-apps-deploy@v1
        with:
          azure_static_web_apps_api_token: ${{ secrets.AZURE_SWA_TOKEN }}
          action: upload
          app_location: frontend/dist
```

### 9.3 Dockerfile

#### `backend/Dockerfile`

```dockerfile
# ============================================
# IPA Platform Backend — Multi-stage Build
# ============================================

# Stage 1: Dependencies
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim AS runtime
WORKDIR /app

# Security: non-root user
RUN groupadd -r ipa && useradd -r -g ipa -d /app -s /bin/false ipa

# Copy dependencies
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Ownership
RUN chown -R ipa:ipa /app

USER ipa

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8000/health'); assert r.status_code == 200"

# Runtime
EXPOSE 8000
CMD ["gunicorn", "main:app", "-c", "gunicorn.conf.py"]
```

#### `frontend/Dockerfile`

```dockerfile
# ============================================
# IPA Platform Frontend — Multi-stage Build
# ============================================

# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Serve
FROM nginx:1.25-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 9.4 工作量

| 項目 | 工作量 |
|------|--------|
| CI Pipeline (GitHub Actions) | 1 天 |
| CD Pipeline | 1 天 |
| Dockerfile (backend + frontend) | 1 天 |
| 測試 Pipeline 運作 | 0.5 天 |
| **合計** | **3.5 天** |

---

## 十、Azure 部署架構設計

### 10.1 方案比較

| 項目 | Azure App Service | Azure Kubernetes Service (AKS) |
|------|------------------|-------------------------------|
| **複雜度** | 低 | 高 |
| **學習曲線** | 低（PaaS） | 高（需 K8s 知識） |
| **適合規模** | <100 並發 | >100 並發 |
| **自動擴展** | 內建 | 需配置 HPA |
| **成本（估算）** | ~$150-300/月 | ~$300-600/月 |
| **運維負擔** | 低 | 中-高 |
| **RAPO 適用性** | **推薦** | 過度設計 |

### 10.2 推薦: Azure App Service 架構

```
                    ┌─────────────────────────┐
                    │   Azure Front Door /    │
                    │   Application Gateway   │
                    └───────────┬─────────────┘
                                │
                    ┌───────────┴─────────────┐
                    │                         │
         ┌──────────▼──────┐      ┌──────────▼──────────┐
         │ Azure Static    │      │ Azure App Service    │
         │ Web Apps        │      │ (Linux, Python 3.11) │
         │ (Frontend)      │      │ Gunicorn + Uvicorn   │
         │ $0 (Free tier)  │      │ B2: $55/月           │
         └─────────────────┘      └──────────┬───────────┘
                                              │
                    ┌──────────┬──────────────┬┘
                    │          │              │
         ┌──────────▼───┐ ┌───▼────────┐ ┌───▼────────────┐
         │ Azure DB for │ │ Azure Cache│ │ Azure Key Vault│
         │ PostgreSQL   │ │ for Redis  │ │ (Secrets)      │
         │ Flex B1ms    │ │ Basic C0   │ │ $0.03/10K ops  │
         │ $25/月       │ │ $16/月     │ │                │
         └──────────────┘ └────────────┘ └────────────────┘
```

### 10.3 成本估算

| 服務 | SKU | 月成本 (USD) |
|------|-----|-------------|
| App Service (Backend) | B2 (2 cores, 3.5GB) | ~$55 |
| Static Web Apps (Frontend) | Free | $0 |
| Azure DB for PostgreSQL | Flexible B1ms | ~$25 |
| Azure Cache for Redis | Basic C0 (250MB) | ~$16 |
| Azure Key Vault | Standard | ~$1 |
| Azure Monitor | 基本 | ~$10 |
| **合計** | | **~$107/月** |

**進階需求加價**:

| 需求 | SKU 升級 | 加價 |
|------|---------|------|
| 更多並發 | App Service P1v3 | +$85 (~$140) |
| 更多 DB 空間 | PostgreSQL B2ms | +$25 (~$50) |
| Redis Pub/Sub | Standard C1 | +$84 (~$100) |
| Front Door CDN | Standard | +$35 |

### 10.4 App Service 配置

**Application Settings**:

```bash
# Azure Portal > App Service > Configuration > Application Settings
APP_ENV=production
PORT=8000
WEB_CONCURRENCY=4
LOG_LEVEL=WARNING

# Database (from Key Vault Reference)
DB_HOST=@Microsoft.KeyVault(SecretUri=https://ipa-kv.vault.azure.net/secrets/db-host)
DB_PORT=5432
DB_NAME=ipa_platform
DB_USER=@Microsoft.KeyVault(SecretUri=https://ipa-kv.vault.azure.net/secrets/db-user)
DB_PASSWORD=@Microsoft.KeyVault(SecretUri=https://ipa-kv.vault.azure.net/secrets/db-password)

# Redis
REDIS_HOST=ipa-redis.redis.cache.windows.net
REDIS_PORT=6380
REDIS_PASSWORD=@Microsoft.KeyVault(SecretUri=https://ipa-kv.vault.azure.net/secrets/redis-key)

# CORS
CORS_ORIGINS=https://ipa.rapo.ricoh.com

# JWT
JWT_SECRET_KEY=@Microsoft.KeyVault(SecretUri=https://ipa-kv.vault.azure.net/secrets/jwt-secret)

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=@Microsoft.KeyVault(SecretUri=https://ipa-kv.vault.azure.net/secrets/aoai-endpoint)
AZURE_OPENAI_API_KEY=@Microsoft.KeyVault(SecretUri=https://ipa-kv.vault.azure.net/secrets/aoai-key)

# OTel
OTEL_ENABLED=true
OTEL_SERVICE_NAME=ipa-platform-prod
```

**Startup Command**:

```bash
gunicorn main:app -c gunicorn.conf.py
```

### 10.5 工作量

| 項目 | 工作量 |
|------|--------|
| Azure 資源建立 (IaC or Portal) | 2 天 |
| Key Vault 設定 | 0.5 天 |
| App Service 配置 | 1 天 |
| Static Web Apps 配置 | 0.5 天 |
| 端到端部署驗證 | 1 天 |
| **合計** | **5 天** |

---

## 十一、監控方案 — OTel + Azure Monitor

### 11.1 現狀

**已有**:
- `requirements.txt`: OpenTelemetry API/SDK/FastAPI instrumentation/OTLP exporter 全部已安裝
- `config.py:160-163`: OTel 配置項已定義（預設關閉）
- `orchestration/metrics.py`: 893 LOC 的 OrchestrationMetricsCollector（使用 OTel）
- `monitoring/prometheus/prometheus.yml`: Prometheus scrape 配置
- `monitoring/grafana/`: 2 個 Dashboard（performance + security-audit）
- Docker Compose: Jaeger + Prometheus + Grafana 在 monitoring profile 中

**缺失**:
- OTel 未在 main.py 中初始化
- 無 Azure Monitor / Application Insights 整合
- 無結構化日誌（structlog 已安裝但未全面使用）
- 無 SLI/SLO 定義

### 11.2 OTel 初始化方案

新增 `backend/src/core/observability.py`:

```python
"""OpenTelemetry initialization for IPA Platform."""
import logging
from src.core.config import get_settings

logger = logging.getLogger(__name__)


def init_telemetry(app):
    """Initialize OpenTelemetry instrumentation."""
    settings = get_settings()

    if not settings.otel_enabled:
        logger.info("OpenTelemetry disabled")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        # Resource attributes
        resource = Resource.create({
            "service.name": settings.otel_service_name,
            "service.version": "0.2.0",
            "deployment.environment": settings.app_env,
        })

        # Tracer provider
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(
            OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
        )
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        # FastAPI instrumentation
        FastAPIInstrumentor.instrument_app(app)

        logger.info(
            f"OpenTelemetry initialized: {settings.otel_service_name} "
            f"→ {settings.otel_exporter_otlp_endpoint}"
        )

    except ImportError as e:
        logger.warning(f"OpenTelemetry dependencies not available: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry: {e}")
```

在 `main.py` 的 `create_app()` 中添加:

```python
def create_app() -> FastAPI:
    app = FastAPI(...)

    # ... CORS middleware ...

    # Initialize observability
    from src.core.observability import init_telemetry
    init_telemetry(app)

    # ... routes ...
    return app
```

### 11.3 Azure Monitor 整合

Azure App Service 可直接使用 Azure Monitor Application Insights:

```bash
# requirements.txt 新增
azure-monitor-opentelemetry-exporter>=1.0.0b15
```

```python
# observability.py — Azure Monitor exporter
if settings.app_env == "production":
    from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
    azure_exporter = AzureMonitorTraceExporter(
        connection_string=settings.azure_monitor_connection_string
    )
    provider.add_span_processor(BatchSpanProcessor(azure_exporter))
```

### 11.4 SLI/SLO 建議

| SLI | 目標 SLO | 測量方式 |
|-----|---------|---------|
| API 可用性 | 99.5% | `/health` endpoint 回應成功率 |
| API 延遲 (p99) | < 5s | OTel histograms |
| Agent 執行成功率 | > 95% | OrchestrationMetrics |
| HITL 審批回應時間 | < 30min | ApprovalStorage timestamp diff |
| SSE 連線穩定性 | > 99% | 斷線重連計數 |

### 11.5 工作量

| 項目 | 工作量 |
|------|--------|
| OTel 初始化 + FastAPI instrumentation | 1 天 |
| Azure Monitor exporter | 0.5 天 |
| 結構化日誌整合 | 1 天 |
| Grafana Dashboard 更新 | 1 天 |
| SLI/SLO alerting rules | 0.5 天 |
| **合計** | **4 天** |

---

## 十二、容量規劃和水平擴展策略

### 12.1 當前容量評估

```
單 Worker + asyncio 並發模型:

理論最大並發請求數:
├── asyncio 事件迴圈: ~1000 個協程（I/O 密集）
├── DB 連線池: pool_size=5 + max_overflow=10 = 15 連線
├── LLM API 調用: 單次 2-30 秒（阻塞事件迴圈的風險）
└── SSE 長連線: 每個用戶 1 條

實際瓶頸:
├── LLM API 延遲 (2-30s) → 單一 API 調用期間其他請求等待
├── DB 連線 (15) → 超過 15 個並發 DB 查詢即阻塞
├── 記憶體: InMemory 存儲隨用戶增長而膨脹
└── SSE: 每個連線佔用一個 HTTP 連線

估計可支撐: ~5-10 並發用戶
```

### 12.2 RAPO 需求分析

```
RAPO Data & AI Team:
├── 直接用戶: ~10-20 人
├── 間接觸發 (ServiceNow webhook): ~10-30 /小時
├── 峰值並發: ~10-15 同時
└── 目標: 20-50 並發用戶

→ 當前架構 (5-10) 不足
→ Multi-Worker (4x, 20-40) 基本滿足
→ 長期需考慮水平擴展 (100+)
```

### 12.3 垂直擴展路線

| 階段 | 配置 | 預估並發 | 所需修復 |
|------|------|---------|---------|
| **現狀** | 1 Worker, InMemory | ~5-10 | - |
| **Phase A** | 4 Workers, Gunicorn | ~20-40 | InMemory → Redis/PG |
| **Phase B** | 8 Workers, P1v3 | ~40-80 | ContextSync 分佈式鎖 |
| **Phase C** | App Service Scale-out | ~80-200 | SSE sticky sessions |

### 12.4 水平擴展策略

如需超過 200 並發（超出 RAPO 近期需求）:

```
                    ┌─────────────────────┐
                    │   Azure Front Door  │
                    │   (Load Balancing)  │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼──────┐ ┌──────▼────────┐ ┌─────▼─────────┐
    │ App Service #1 │ │ App Service #2│ │ App Service #3│
    │ 4 Workers      │ │ 4 Workers     │ │ 4 Workers     │
    └────────┬───────┘ └───────┬───────┘ └───────┬───────┘
             │                 │                 │
             └─────────┬───────┘                 │
                       │                         │
              ┌────────▼──────────┐    ┌─────────▼────────┐
              │ Azure Redis       │    │ Azure PostgreSQL  │
              │ (Shared State)    │    │ (Shared DB)       │
              │ Standard C1       │    │ GP D2s_v3         │
              └───────────────────┘    └──────────────────┘
```

**SSE Sticky Session 配置**:

```
Azure Front Door:
  Session Affinity: Enabled
  Affinity Type: Cookie-based
  → 確保 SSE 長連線始終路由到同一個後端實例
```

**Redis 作為共享狀態**:

```python
# 所有 InMemory 替換為 Redis 後，
# 多個 App Service 實例共享同一個 Redis:
# - Approval requests
# - Dialog sessions
# - Context versions
# - Checkpoint metadata
```

### 12.5 DB 連線池調整

多 Worker / 多實例場景下需調整 PostgreSQL 連線池:

```python
# 單實例 4 Workers:
# 每 Worker pool_size=5 → 4 × 5 = 20 連線 (+ overflow)
# PostgreSQL max_connections 預設 100 → 足夠

# 3 實例 × 4 Workers:
# 3 × 4 × 5 = 60 連線 (+ overflow 可達 120)
# 需提升 PostgreSQL max_connections 或使用 PgBouncer

# Azure DB for PostgreSQL Flex B1ms:
# max_connections = 50 → 不足
# 建議: 升級到 GP D2s_v3 (max_connections = 859)
# 或加上 PgBouncer (connection pooler)
```

---

## 十三、報告可能遺漏的基礎設施問題

以下是深度分析報告 V2 中未充分涵蓋的基礎設施問題，經代碼驗證發現：

### 13.1 缺少 Dockerfile（CRITICAL for 部署）

**現狀**: 整個專案沒有任何 Dockerfile

**影響**: 無法容器化部署到 Azure App Service (Container) 或 AKS

**修復**: 見 Section 九 的 Dockerfile 範例

### 13.2 無結構化日誌

**現狀**: `requirements.txt` 安裝了 `structlog>=24.1.0`，但 `main.py:27-30` 使用基本 `logging.basicConfig()`

**影響**:
- 生產環境無法有效搜索和分析日誌
- 無法關聯請求 ID 跨多個服務
- Azure Monitor 日誌查詢效率低

**修復**:

```python
# backend/src/core/logging.py
import structlog

def configure_logging(app_env: str):
    """Configure structured logging."""
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if app_env == "production":
        # JSON format for Azure Monitor
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Pretty format for development
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
```

### 13.3 無 Request ID 追蹤

**現狀**: 無 middleware 生成和傳播 request ID

**影響**: 無法在日誌中追蹤單一請求的完整生命週期

**修復**:

```python
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response
```

### 13.4 數據庫模型與 InMemory 存儲的 Schema Gap

**現狀**:
- 數據庫模型: 8 個（agent, audit, base, checkpoint, execution, session, user, workflow）
- InMemory 存儲: 9 個
- **Gap**: 大部分 InMemory 存儲沒有對應的 DB model

需新增的 DB model/table:

| 需新增 | 對應 InMemory | 優先級 |
|--------|-------------|--------|
| `approval_requests` | InMemoryApprovalStorage | P0 |
| `chat_threads` | InMemoryThreadRepository | P1 |
| `conversation_memory` | InMemoryConversationMemory | P1 |
| `mcp_audit_logs` | InMemoryAuditStorage | P1 |
| `dialog_sessions` | InMemoryDialogSessionStorage | P2 |

### 13.5 無 Graceful Shutdown 處理

**現狀**: `main.py` lifespan 有基本的 shutdown 處理（關閉 DB 連線和 Agent Service），但:
- 未等待進行中的 SSE 連線優雅結束
- 未等待進行中的 Agent 執行完成
- 未保存 InMemory 狀態到持久化存儲

**影響**: 部署更新時可能中斷用戶操作、丟失審批請求

**建議**: 在 lifespan shutdown 中添加:

```python
# Shutdown
logger.info("IPA Platform shutting down...")

# 1. 停止接受新請求 (Gunicorn 處理)
# 2. 等待進行中的 Agent 執行完成 (max 30s)
# 3. 關閉 SSE 連線
# 4. 將 InMemory 狀態 flush 到 Redis/PG
# 5. 關閉 DB 連線
```

### 13.6 Alembic 遷移管理

**現狀**: 6 個遷移檔案，全部集中在 2026-01 月，且命名順序混亂（003, 004 的時間戳早於 001, 002）

**建議**:
- 建立遷移命名規範: `{YYYYMMDD}_{HHMM}_{sequential_id}_{description}.py`
- 新增遷移前先跑 `alembic check` 確認一致性
- CI/CD 中自動執行 `alembic upgrade head`

### 13.7 無 Backup / Restore 策略

**現狀**: 無任何數據庫備份配置

**建議**: Azure DB for PostgreSQL Flex 內建備份功能:
- 自動備份: 保留 7-35 天
- 時間點還原 (PITR)
- 異地備份 (Geo-redundant)

---

## 十四、綜合優先級路線圖

### 14.1 修復優先級矩陣

```
影響 ↑
  │
  │  ┌────────────────────────────┬──────────────────────────────┐
  │  │ CORS/Vite 修復 (1h)       │ ContextSync 加鎖 (1d)       │
高│  │ reload=True 修復 (0.5d)    │ Checkpoint 統一 (6d)        │
  │  │ InMemory Approval (2d)    │ Gunicorn 配置 (1d)          │
  │  │ Docker Compose 衝突 (1.5d)│ 其他 InMemory 替換 (5.5d)   │
  │  │                           │                              │
  │  │    ← Week 1-2 →          │     ← Week 3-5 →            │
  │  ├────────────────────────────┼──────────────────────────────┤
  │  │                            │                              │
中│  │ CI/CD Pipeline (3.5d)      │ Azure 部署 (5d)             │
  │  │ Dockerfile 建立 (1d)       │ 監控整合 (4d)               │
  │  │ 結構化日誌 (1d)            │ DB 模型補齊 (3d)            │
  │  │                            │                              │
  │  │    ← Week 5-7 →           │     ← Week 7-10 →           │
  │  └────────────────────────────┴──────────────────────────────┘
  └──────────────────────────────────────────────────→ 工作量
```

### 14.2 Phase 分期

#### Phase A: 緊急修復（Week 1-2, ~7 天）

| # | 項目 | 工作量 | 依賴 |
|---|------|--------|------|
| A1 | CORS origin 修復 (3000→3005) | 10min | 無 |
| A2 | Vite proxy 修復 (8010→8000) | 10min | 無 |
| A3 | CORS 方法/標頭加固 | 30min | 無 |
| A4 | reload=True → 環境感知 | 0.5天 | 無 |
| A5 | Docker Compose 衝突修復 | 1.5天 | 無 |
| A6 | InMemoryApprovalStorage → Redis | 2天 | 無 |
| A7 | ContextSynchronizer asyncio.Lock | 1天 | 無 |
| A8 | RabbitMQ 容器暫時移除 | 0.5天 | A5 |

**Phase A 交付**: 前後端能通訊、審批不丟失、並發安全

#### Phase B: 持久化加固（Week 3-5, ~12 天）

| # | 項目 | 工作量 | 依賴 |
|---|------|--------|------|
| B1 | Gunicorn 配置 | 1天 | A4, A6, A7 |
| B2 | InMemory Thread/Conversation/Audit → PG | 4天 | 無 |
| B3 | InMemory DialogSession/Cache → Redis | 1.5天 | 無 |
| B4 | Checkpoint 系統統一 | 6天 | B2 |

**Phase B 交付**: 所有狀態持久化、Multi-Worker 可啟用

#### Phase C: 生產化（Week 5-10, ~14 天）

| # | 項目 | 工作量 | 依賴 |
|---|------|--------|------|
| C1 | CI/CD Pipeline | 3.5天 | 無 |
| C2 | Dockerfile (backend + frontend) | 1天 | 無 |
| C3 | 結構化日誌 + Request ID | 1.5天 | 無 |
| C4 | Azure 部署架構 | 5天 | C1, C2 |
| C5 | OTel + Azure Monitor | 4天 | C4 |

**Phase C 交付**: Azure 部署完成、可觀測性到位、CI/CD 自動化

### 14.3 總工作量

| Phase | 工作量 | 時間跨度 |
|-------|--------|---------|
| Phase A (緊急) | ~7 天 | Week 1-2 |
| Phase B (加固) | ~12 天 | Week 3-5 |
| Phase C (生產化) | ~14 天 | Week 5-10 |
| **合計** | **~33 天 (≈7 週)** | **10 週（含緩衝）** |

---

## 附錄：驗證的檔案清單

以下是本報告代碼驗證所讀取的核心檔案：

| 檔案 | 驗證項目 |
|------|---------|
| `backend/main.py` | Uvicorn 配置、Lifespan、路由註冊 |
| `backend/src/core/config.py` | JWT Secret、CORS、RabbitMQ、OTel 配置 |
| `frontend/vite.config.ts` | Proxy target、Port 配置 |
| `docker-compose.yml` | 服務定義、版本、Healthcheck |
| `docker-compose.override.yml` | 衝突定義、n8n 憑證 |
| `backend/src/infrastructure/` | 目錄結構、messaging 空殼、storage 空目錄 |
| `backend/src/infrastructure/database/session.py` | 連線池配置 |
| `backend/src/integrations/hybrid/context/sync/synchronizer.py` | ContextSync #1 無鎖 |
| `backend/src/integrations/claude_sdk/hybrid/synchronizer.py` | ContextSync #2 無鎖 |
| `backend/src/integrations/orchestration/hitl/controller.py` | InMemoryApprovalStorage |
| `backend/src/integrations/hybrid/checkpoint/backends/memory.py` | Hybrid Checkpoint (有 Lock) |
| `backend/requirements.txt` | 依賴清單 |
| `monitoring/prometheus/prometheus.yml` | Prometheus scrape 配置 |

---

*本報告基於 IPA Platform 全面深度分析報告 V2 的基礎設施發現，結合代碼實地驗證撰寫。所有配置範例均針對 RAPO Data & AI Team 的實際需求（20-50 並發用戶、Azure 部署環境）設計。*
