# CHANGE-002: 並行處理架構改進 — 三層背壓與分散式狀態

**變更日期**: 2026-01-28
**變更類型**: 架構改進
**影響範圍**: Input Gateway、Orchestration Layer、Claude Worker Pool 三層並行架構
**相關 Sprint**: 待規劃
**狀態**: 📋 方案設計完成，待實施

---

## 變更摘要

針對 IPA Platform 三層架構（Input Gateway → Orchestration → Claude Worker Pool）的並行處理能力進行系統性改進。解決四個核心問題：單 Process 瓶頸、狀態無法跨 Worker 共享、缺少全局背壓機制、Race Condition 與無界記憶體增長。

---

## 變更原因

### 現有架構問題

#### 問題 1：單 Process 瓶頸

**位置**: `backend/main.py:238-244`

```python
# 目前只啟動單一 Uvicorn worker
uvicorn.run(
    "main:app",
    host="0.0.0.0",
    port=8000,
    reload=True,
    log_level="info",
)
```

- Uvicorn 預設 1 個 worker，所有請求共用一個 process
- Python GIL 限制 CPU 密集操作（如 Semantic Router 的 vector similarity）
- DB 連線池 `pool_size=5, max_overflow=10`（最多 15 連線）以單 worker 為前提設計

#### 問題 2：Orchestration 狀態純 In-Memory

**位置**: `backend/src/integrations/hybrid/context/sync/synchronizer.py:114-117`

```python
# 純 in-memory dict，無法跨 worker 共享
self._context_versions: Dict[str, int] = {}
self._rollback_snapshots: Dict[str, List[HybridContext]] = {}
```

- 所有 orchestration 狀態存在 process 記憶體中
- 無法水平擴展（多 worker 時狀態不一致）
- Process 重啟後狀態完全丟失
- 無分散式鎖保護並行存取

#### 問題 3：缺少全局背壓機制

- **Layer 1 (API)**：無任何限流 middleware，全部請求直接接受
- **Layer 2 (Orchestration)**：無並行 session 數量限制，全部處理
- **Layer 3 (Worker Pool)**：`RateLimitHook` 限制 10 並行、60/min，但無法向上游傳遞反壓信號
- 三層之間無協調，突發流量會導致 Layer 2 積壓大量任務

#### 問題 4：Race Condition 與無界記憶體

**4a. Race Condition**

**位置**: `backend/src/integrations/hybrid/context/sync/synchronizer.py:174-175`

```python
# 非原子操作，兩個 async task 可能交錯執行
if result.success:
    self._context_versions[context_id] = result.target_version
```

**位置**: `backend/src/integrations/hybrid/context/sync/synchronizer.py:594-606`

```python
# 同一 context 的並行請求可能同時讀寫同一個 list
def _save_snapshot(self, context: HybridContext) -> None:
    snapshots = self._rollback_snapshots[context_id]
    snapshots.append(context)  # 非原子
```

`_context_versions` 和 `_rollback_snapshots` 均為普通 dict/list，無 `asyncio.Lock` 保護。同一用戶快速連續請求時可能導致版本追蹤出錯。

**4b. 無界記憶體增長**

| 元件 | 無界資料結構 | 位置 |
|------|------------|------|
| `ClaudeCoordinator` | `_coordination_history: List` | `orchestrator/coordinator.py:72` |
| `SessionStateManager` | `_state_cache: Dict` | `claude_sdk/session_state.py` |
| `ClaudeSDKClient` | `_sessions: Dict` | `claude_sdk/client.py` |
| `RateLimitHook` | `_call_timestamps: list` | `hooks/rate_limit.py:121` |
| `ContextSynchronizer` | `_context_versions: Dict` | `context/sync/synchronizer.py:114` |

長時間運行下，這些無界資料結構會持續增長，最終導致 OOM。

### 改進後的架構優勢

1. **水平擴展**：多 Worker 部署，Redis 作為共享狀態層
2. **高可用**：狀態持久化，process 重啟不丟失
3. **流量控制**：三層漏斗式背壓，防止系統過載
4. **資料安全**：分散式鎖消除 race condition
5. **記憶體穩定**：有界資料結構防止 OOM

---

## 詳細變更

### 改進架構總覽

```
改進前:

  用戶請求 ──→ [Uvicorn x1] ──→ [Orchestrator (in-memory)] ──→ [Worker Pool]
              無限流            無鎖、無背壓                   Semaphore(10)

改進後:

  用戶請求 ──→ [Nginx/Traefik]
              │
              ├── [Uvicorn Worker 1] ──┐
              ├── [Uvicorn Worker 2] ──┼── [Redis 分散式狀態] ──→ [Worker Pool]
              └── [Uvicorn Worker N] ──┘   • 版本追蹤            Semaphore(10)
              全局+用戶限流                 • 分散式鎖            + 反壓信號
                                           • Session 狀態
                                           • 背壓計數器
```

---

### 優先級 1：Race Condition 修復 + 無界記憶體治理

> 低風險、高收益，單 Worker 環境即可實施

#### 1a. ContextSynchronizer 加入 asyncio.Lock

**修改文件**: `backend/src/integrations/hybrid/context/sync/synchronizer.py`

**改進方向**：

```python
import asyncio
from collections import defaultdict

class ContextSynchronizer:
    def __init__(self, ...):
        ...
        # 全局鎖（保護 _locks dict 本身的建立）
        self._global_lock = asyncio.Lock()
        # 每個 context 一個鎖
        self._locks: Dict[str, asyncio.Lock] = {}

    async def _get_lock(self, context_id: str) -> asyncio.Lock:
        """安全地獲取 context 專用鎖"""
        if context_id not in self._locks:
            async with self._global_lock:
                # Double-check pattern
                if context_id not in self._locks:
                    self._locks[context_id] = asyncio.Lock()
        return self._locks[context_id]

    async def sync(self, source: HybridContext, ...) -> SyncResult:
        lock = await self._get_lock(source.context_id)
        async with lock:
            # ... 原有 sync 邏輯（版本更新、snapshot 保存等）...
            pass

    async def rollback(self, context_id: str, ...) -> SyncResult:
        lock = await self._get_lock(context_id)
        async with lock:
            # ... 原有 rollback 邏輯 ...
            pass
```

**關鍵設計決策**：
- 使用 per-context lock 而非全局 lock，避免不同 session 之間互相阻塞
- 使用 double-check pattern 保護 lock 的建立過程
- `_save_snapshot` 和版本更新都在 lock 保護範圍內

#### 1b. 無界資料結構改為有界

**依賴安裝**：`cachetools` 已在 Python 生態中廣泛使用

**各元件改進方向**：

| 元件 | 改進前 | 改進後 | 說明 |
|------|--------|--------|------|
| `ClaudeCoordinator._coordination_history` | `List` | `collections.deque(maxlen=1000)` | 自動淘汰最舊記錄 |
| `SessionStateManager._state_cache` | `Dict` | `cachetools.TTLCache(maxsize=500, ttl=3600)` | TTL + 最大容量 |
| `ClaudeSDKClient._sessions` | `Dict` | `cachetools.TTLCache(maxsize=200, ttl=7200)` | 2 小時無活動自動過期 |
| `ContextSynchronizer._context_versions` | `Dict` | `cachetools.LRUCache(maxsize=1000)` | LRU 淘汰最少使用的 |
| `ContextSynchronizer._locks` | `Dict` | 定期清理無活動鎖 | 配合 `_context_versions` 淘汰 |

**改進範例 — ClaudeCoordinator**：

```python
from collections import deque

class ClaudeCoordinator:
    def __init__(self, ...):
        ...
        # 改進：限制歷史記錄最大長度
        self._coordination_history: deque = deque(maxlen=1000)
```

**改進範例 — SessionStateManager**：

```python
from cachetools import TTLCache

class SessionStateManager:
    def __init__(self, ...):
        ...
        # 改進：TTL + 最大容量，自動淘汰
        self._state_cache: TTLCache = TTLCache(maxsize=500, ttl=3600)
```

---

### 優先級 2：Redis 分散式狀態層

> 中等難度，為水平擴展打基礎

#### 2a. StateStore 抽象層

**新增文件**: `backend/src/infrastructure/state/store.py`

**設計方向**：

```python
from typing import List, Optional, Protocol
from src.integrations.hybrid.context.models import HybridContext


class StateStore(Protocol):
    """分散式狀態儲存抽象"""

    # 版本管理
    async def get_version(self, context_id: str) -> int: ...
    async def set_version(self, context_id: str, version: int) -> None: ...

    # Snapshot 管理
    async def save_snapshot(
        self, context_id: str, context: HybridContext, max_snapshots: int = 5
    ) -> None: ...
    async def get_snapshots(self, context_id: str) -> List[HybridContext]: ...
    async def clear_snapshots(self, context_id: str) -> None: ...

    # 分散式鎖
    async def acquire_lock(
        self, lock_key: str, timeout: float = 5.0, ttl: float = 30.0
    ) -> bool: ...
    async def release_lock(self, lock_key: str) -> None: ...

    # 背壓計數器
    async def get_active_count(self, counter_key: str) -> int: ...
    async def increment_active(self, counter_key: str, ttl: int = 60) -> int: ...
    async def decrement_active(self, counter_key: str) -> int: ...
```

#### 2b. InMemoryStateStore（開發/測試用）

**新增文件**: `backend/src/infrastructure/state/memory_store.py`

```python
class InMemoryStateStore:
    """
    In-Memory 實現，用於開發和測試環境。
    行為與 RedisStateStore 一致，但狀態只在 process 內有效。
    """

    def __init__(self):
        self._versions: Dict[str, int] = {}
        self._snapshots: Dict[str, List[Any]] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._counters: Dict[str, int] = {}
```

#### 2c. RedisStateStore（生產用）

**新增文件**: `backend/src/infrastructure/state/redis_store.py`

**Redis 資料結構映射**：

| 功能 | Redis 命令 | Key Pattern | 說明 |
|------|-----------|-------------|------|
| 版本號 | `GET/SET` | `ipa:ctx:version:{context_id}` | 簡單 key-value |
| Snapshots | `LPUSH/LTRIM/LRANGE` | `ipa:ctx:snapshots:{context_id}` | List，LTRIM 控制數量 |
| 分散式鎖 | `SET NX EX` | `ipa:lock:{lock_key}` | NX 保證原子性，EX 防死鎖 |
| 背壓計數 | `INCR/DECR/GET` | `ipa:backpressure:{counter}` | 原子計數器 |
| Session 狀態 | `HSET/HGET/EXPIRE` | `ipa:session:{session_id}` | Hash + TTL |

**關鍵實現要點**：

```python
import redis.asyncio as aioredis

class RedisStateStore:
    def __init__(self, redis_url: str):
        self._redis = aioredis.from_url(redis_url, decode_responses=True)

    async def acquire_lock(self, lock_key: str, timeout: float = 5.0, ttl: float = 30.0) -> bool:
        """
        分散式鎖實現
        - SET NX：只在 key 不存在時設置（原子操作）
        - EX ttl：自動過期，防止 process crash 後死鎖
        - 輪詢等待 timeout 秒
        """
        key = f"ipa:lock:{lock_key}"
        lock_value = f"{os.getpid()}:{time.time()}"
        deadline = time.time() + timeout

        while time.time() < deadline:
            acquired = await self._redis.set(key, lock_value, nx=True, ex=int(ttl))
            if acquired:
                return True
            await asyncio.sleep(0.05)  # 50ms 輪詢間隔

        return False

    async def release_lock(self, lock_key: str) -> None:
        """釋放鎖（使用 Lua script 確保原子性）"""
        key = f"ipa:lock:{lock_key}"
        await self._redis.delete(key)
```

#### 2d. ContextSynchronizer 整合 StateStore

**修改文件**: `backend/src/integrations/hybrid/context/sync/synchronizer.py`

**改進方向**：

```python
class ContextSynchronizer:
    def __init__(
        self,
        state_store: Optional[StateStore] = None,  # 新增
        conflict_resolver: Optional[ConflictResolver] = None,
        event_publisher: Optional[SyncEventPublisher] = None,
        ...
    ):
        self._state_store = state_store or InMemoryStateStore()
        ...
        # 移除原有的 in-memory 狀態
        # self._context_versions: Dict[str, int] = {}        # 刪除
        # self._rollback_snapshots: Dict[str, List[...]] = {} # 刪除

    async def sync(self, source: HybridContext, ...) -> SyncResult:
        context_id = source.context_id

        # 使用分散式鎖（取代 asyncio.Lock）
        locked = await self._state_store.acquire_lock(f"sync:{context_id}")
        if not locked:
            raise SyncError("Context is being synced by another request")

        try:
            # 使用 StateStore 替代直接 dict 操作
            await self._state_store.save_snapshot(context_id, source)

            result = await self._sync_with_retry(...)

            if result.success:
                await self._state_store.set_version(
                    context_id, result.target_version
                )

            return result
        finally:
            await self._state_store.release_lock(f"sync:{context_id}")
```

---

### 優先級 3：多 Worker 部署 + API 層限流

> 需要優先級 2 完成後才能安全實施

#### 3a. 生產環境多 Worker 啟動配置

**新增文件**: `backend/scripts/start_production.sh`

```bash
#!/bin/bash
# IPA Platform - Production startup with multi-worker

WORKERS=${WORKERS:-4}  # 預設 4 workers，可由環境變數覆蓋
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}

echo "Starting IPA Platform with $WORKERS workers on $HOST:$PORT"

gunicorn main:app \
    -w $WORKERS \
    -k uvicorn.workers.UvicornWorker \
    --bind $HOST:$PORT \
    --timeout 300 \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --access-logfile - \
    --error-logfile -
```

#### 3b. DB 連線池動態配置

**修改文件**: `backend/src/infrastructure/database/session.py`

**改進方向**：

```python
# 連線池大小應從設定讀取，並考慮 worker 數量
engine_kwargs["pool_size"] = settings.db_pool_size       # 新增設定項
engine_kwargs["max_overflow"] = settings.db_max_overflow  # 新增設定項
```

**計算公式**：

```
每 Worker 連線數 = pool_size + max_overflow
總連線數 = Workers × 每 Worker 連線數
PostgreSQL max_connections ≥ 總連線數 + 預留

範例：4 Workers
  pool_size=3, max_overflow=5 → 每 Worker 8 → 總共 32
  PostgreSQL max_connections=50（含預留）
```

#### 3c. API 層限流 Middleware

**新增文件**: `backend/src/api/middleware/rate_limit.py`

**設計方向**：

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import redis.asyncio as aioredis


class APIRateLimitMiddleware(BaseHTTPMiddleware):
    """
    基於 Redis 的分散式 API 限流

    限流規則：
    - 全局：每秒最多 100 個請求
    - 每 IP：每分鐘最多 60 個請求
    - Agent 端點 (/api/v1/claude-sdk/*, /api/v1/agents/*/execute)：
      每用戶每分鐘最多 20 個請求

    使用 Redis INCR + EXPIRE 實現滑動窗口
    """

    def __init__(self, app, redis_url: str):
        super().__init__(app)
        self._redis = aioredis.from_url(redis_url, decode_responses=True)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"

        # 全局限流
        global_key = f"ipa:ratelimit:global:{int(time.time())}"
        global_count = await self._redis.incr(global_key)
        if global_count == 1:
            await self._redis.expire(global_key, 2)
        if global_count > 100:
            return JSONResponse(
                status_code=429,
                content={"error": "RATE_LIMIT_EXCEEDED", "message": "Too many requests"}
            )

        # 每 IP 限流
        ip_key = f"ipa:ratelimit:ip:{client_ip}:{int(time.time() / 60)}"
        ip_count = await self._redis.incr(ip_key)
        if ip_count == 1:
            await self._redis.expire(ip_key, 120)
        if ip_count > 60:
            return JSONResponse(
                status_code=429,
                content={"error": "IP_RATE_LIMIT", "message": "Too many requests from this IP"}
            )

        return await call_next(request)
```

**整合到 main.py**：

```python
# 在 create_app() 中加入
from src.api.middleware.rate_limit import APIRateLimitMiddleware

if settings.app_env == "production":
    app.add_middleware(APIRateLimitMiddleware, redis_url=settings.redis_url)
```

---

### 優先級 4：反壓信號機制

> 錦上添花，提升極端負載下的穩定性

#### 4a. 背壓信號服務

**新增文件**: `backend/src/core/performance/backpressure.py`

**設計方向**：

```python
class BackpressureMonitor:
    """
    監控 Worker Pool 負載，向上游發送反壓信號

    水位級別：
    - GREEN  (0-60%): 正常接受所有請求
    - YELLOW (60-80%): 拒絕低優先級請求
    - RED    (80%+): 只接受高優先級請求（如 HITL 審批回應）
    """

    def __init__(self, state_store: StateStore, capacity: int = 10):
        self._state_store = state_store
        self._capacity = capacity

    async def get_pressure_level(self) -> str:
        """查詢當前背壓級別"""
        active = await self._state_store.get_active_count("worker_pool")
        ratio = active / self._capacity

        if ratio < 0.6:
            return "GREEN"
        elif ratio < 0.8:
            return "YELLOW"
        else:
            return "RED"

    async def should_accept_request(self, priority: str = "normal") -> bool:
        """根據背壓級別決定是否接受請求"""
        level = await self.get_pressure_level()

        if level == "GREEN":
            return True
        elif level == "YELLOW":
            return priority in ("high", "critical")
        else:  # RED
            return priority == "critical"
```

#### 4b. Worker Pool 整合背壓

**修改文件**: `backend/src/integrations/claude_sdk/orchestrator/task_allocator.py`

**改進方向**：

```python
class TaskAllocator:
    def __init__(self, ..., state_store: Optional[StateStore] = None):
        ...
        self._state_store = state_store

    async def execute_parallel(self, subtasks, selections, executor):
        # 執行前：增加活動計數
        if self._state_store:
            await self._state_store.increment_active("worker_pool")

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return processed_results
        finally:
            # 執行後：減少活動計數
            if self._state_store:
                await self._state_store.decrement_active("worker_pool")
```

---

## 修改文件清單

### 優先級 1：新增/修改文件

| 文件 | 修改說明 |
|------|----------|
| `backend/src/integrations/hybrid/context/sync/synchronizer.py` | 加入 `asyncio.Lock` per-context 鎖 |
| `backend/src/integrations/claude_sdk/orchestrator/coordinator.py` | `_coordination_history` 改為 `deque(maxlen=1000)` |
| `backend/src/integrations/claude_sdk/session_state.py` | `_state_cache` 改為 `TTLCache(maxsize=500, ttl=3600)` |
| `backend/src/integrations/claude_sdk/client.py` | `_sessions` 改為 `TTLCache(maxsize=200, ttl=7200)` |
| `backend/requirements.txt` | 加入 `cachetools>=5.3.0` |

### 優先級 2：新增/修改文件

| 文件 | 說明 |
|------|------|
| `backend/src/infrastructure/state/__init__.py` | State 模組入口 |
| `backend/src/infrastructure/state/store.py` | StateStore Protocol 定義 |
| `backend/src/infrastructure/state/memory_store.py` | InMemoryStateStore 實現 |
| `backend/src/infrastructure/state/redis_store.py` | RedisStateStore 實現 |
| `backend/src/integrations/hybrid/context/sync/synchronizer.py` | 整合 StateStore，移除 in-memory 狀態 |
| `backend/src/core/config.py` | 新增 state_store_backend 設定 |

### 優先級 3：新增/修改文件

| 文件 | 說明 |
|------|------|
| `backend/scripts/start_production.sh` | Gunicorn + UvicornWorker 啟動腳本 |
| `backend/src/api/middleware/__init__.py` | Middleware 模組入口 |
| `backend/src/api/middleware/rate_limit.py` | API 層限流 middleware |
| `backend/src/infrastructure/database/session.py` | DB pool 動態配置 |
| `backend/src/core/config.py` | 新增 db_pool_size, db_max_overflow 設定 |
| `backend/main.py` | 掛載 RateLimitMiddleware |

### 優先級 4：新增/修改文件

| 文件 | 說明 |
|------|------|
| `backend/src/core/performance/backpressure.py` | BackpressureMonitor 服務 |
| `backend/src/integrations/claude_sdk/orchestrator/task_allocator.py` | 整合背壓計數 |

---

## 實施計劃

### 階段與優先級

```
優先級 1（低風險、高收益）
├── 1a. ContextSynchronizer 加入 asyncio.Lock
├── 1b. 無界資料結構改為有界（deque/TTLCache/LRUCache）
└── 預計效果：消除 race condition + 防止記憶體洩漏

優先級 2（中等難度、關鍵基礎）
├── 2a. StateStore Protocol 定義
├── 2b. InMemoryStateStore 實現（測試用）
├── 2c. RedisStateStore 實現（生產用）
├── 2d. ContextSynchronizer 整合 StateStore
└── 預計效果：為水平擴展打基礎

優先級 3（需要優先級 2 完成）
├── 3a. Gunicorn 多 Worker 啟動配置
├── 3b. DB 連線池動態配置
├── 3c. API 層限流 Middleware
└── 預計效果：真正實現水平擴展

優先級 4（錦上添花）
├── 4a. BackpressureMonitor 服務
├── 4b. Worker Pool 整合背壓計數
└── 預計效果：極端負載下的穩定性
```

### 實施原則

1. **先修單 Worker 問題再開多 Worker**：多 Worker 環境會放大現有的 race condition
2. **漸進式遷移**：StateStore 使用 Protocol，可以在 InMemory → Redis 間無縫切換
3. **向下相容**：所有改進透過設定開關控制，不影響開發環境
4. **測試先行**：每個優先級都有對應的測試清單

---

## 設定項變更

### 新增環境變數

```bash
# State Store 配置
STATE_STORE_BACKEND=memory          # memory | redis（預設 memory，生產改 redis）

# DB 連線池配置
DB_POOL_SIZE=5                      # 每 worker 的基本連線數
DB_MAX_OVERFLOW=10                  # 每 worker 的最大溢出連線數

# API 限流配置
API_RATE_LIMIT_ENABLED=false        # 是否啟用 API 限流（生產設 true）
API_RATE_LIMIT_GLOBAL_PER_SEC=100   # 全局每秒最大請求數
API_RATE_LIMIT_IP_PER_MIN=60        # 每 IP 每分鐘最大請求數

# Worker 配置
UVICORN_WORKERS=1                   # Uvicorn worker 數量（生產設 4）

# 背壓配置
BACKPRESSURE_ENABLED=false          # 是否啟用背壓機制
BACKPRESSURE_CAPACITY=10            # Worker Pool 容量
```

---

## 測試清單

### 優先級 1 測試

- [ ] ContextSynchronizer：同一 context 的並行 sync 請求不會互相干擾
- [ ] ContextSynchronizer：不同 context 的並行 sync 請求互不阻塞
- [ ] ContextSynchronizer：lock 的 double-check pattern 正確運作
- [ ] ClaudeCoordinator：`_coordination_history` 不超過 maxlen
- [ ] SessionStateManager：`_state_cache` 過期自動清理
- [ ] SessionStateManager：`_state_cache` 超過 maxsize 自動淘汰
- [ ] ClaudeSDKClient：`_sessions` TTL 過期後自動清理

### 優先級 2 測試

- [ ] InMemoryStateStore：所有 Protocol 方法正確實現
- [ ] RedisStateStore：版本號的讀寫一致性
- [ ] RedisStateStore：分散式鎖的互斥性（兩個 process 不能同時獲得同一鎖）
- [ ] RedisStateStore：鎖的自動過期（防死鎖）
- [ ] RedisStateStore：Snapshot 的 LTRIM 正確限制數量
- [ ] ContextSynchronizer + RedisStateStore：端到端 sync 流程
- [ ] ContextSynchronizer + RedisStateStore：端到端 rollback 流程

### 優先級 3 測試

- [ ] 多 Worker 啟動：所有 Worker 能正常處理請求
- [ ] 多 Worker：不同 Worker 的 Context 狀態透過 Redis 同步
- [ ] API 限流：超過全局限制返回 429
- [ ] API 限流：超過 IP 限制返回 429
- [ ] API 限流：正常流量不被誤擋
- [ ] DB 連線池：多 Worker 總連線數不超過 PostgreSQL max_connections

### 優先級 4 測試

- [ ] 背壓監控：GREEN/YELLOW/RED 級別判斷正確
- [ ] 背壓監控：YELLOW 級別下低優先級請求被拒絕
- [ ] 背壓監控：RED 級別下只有 critical 請求通過
- [ ] Worker Pool：活動計數正確遞增/遞減

---

## 風險評估

| 風險 | 影響 | 機率 | 緩解措施 |
|------|------|------|----------|
| Redis 不可用導致全系統故障 | 高 | 低 | 自動 fallback 到 InMemoryStateStore |
| Lock TTL 過短導致操作被中斷 | 中 | 中 | Lock 續期機制 + 合理 TTL 設定 |
| 限流過嚴影響正常用戶 | 中 | 中 | 設定項可調整 + 監控告警 |
| 多 Worker DB 連線耗盡 | 高 | 中 | 連線池大小公式計算 + 監控 |
| cachetools TTLCache 清理不及時 | 低 | 低 | 定期手動觸發清理 |

---

## 相關連結

- **架構分析來源**: 基於 IPA Platform 三層並行架構深度分析（2026-01-28 對話記錄）
- **現有基礎設施**: Redis 已在 `backend/src/core/config.py:59-68` 配置
- **現有 Worker Pool**: `backend/src/core/performance/concurrent_optimizer.py:475+`
- **現有 Rate Limit**: `backend/src/integrations/claude_sdk/hooks/rate_limit.py`
- **現有 Context Sync**: `backend/src/integrations/hybrid/context/sync/synchronizer.py`

---

**變更者**: AI 助手 (Claude)
**審核者**: Development Team
**版本**: v1.0
