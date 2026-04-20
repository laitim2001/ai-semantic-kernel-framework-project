# 10 - IPA Platform Wiring Audit（Knowledge / Memory / Audit）

**目的**：對 IPA Platform main 分支（commit `69b5fa2` + Phase 47 W1 forward sync `179d7f8`）的**三個知識 / 記憶 / 合規相關 subsystem** 執行 wiring 完整性審計，辨識「代碼存在但未正確串接」的 dead paths 與靜默失敗點。

**方法論**：以「**實際 runtime 資料流**」為單位，不看「代碼是否存在」，而看「呼叫者 → 被呼叫者 → 結果 consumer」是否 end-to-end 連通且配置一致。

**基準**：
- 分支：`research/knowledge-base-enterprise`
- 基底 main commit：`69b5fa2`（Phase 45 + 46 合併後）
- 最新 main commit：`179d7f8`（V9 forward sync to Phase 47 W1）
- 審計日期：2026-04-20
- 審計員：Claude + Chris

---

## 零、Executive Summary

### 核心結論

**主要使用者路徑（chat 聊天主鏈）存在 3 個嚴重 wiring 斷裂，使 IPA 的 knowledge grounding / memory recall / audit trail 三大核心能力處於「存在但無效」狀態**。

| 斷裂 | 嚴重度 | 使用者感知 | 實際情況 |
|------|-------|----------|---------|
| Knowledge Step 2 與 Ingest API 寫去不同倉 | 🔴 CRITICAL | 「我 ingest 的文件應該會被 RAG 搜到」 | Step 2 永遠搜空；只有 agent tool call 路徑找得到 |
| `search_memory` tool import 不存在的 `Mem0Service` | 🔴 CRITICAL | 「agent 會查我的 memory」 | tool 永久返回 empty |
| Main chat flow 零 audit emission | 🔴 HIGH | 「所有操作都有 audit trail」 | 主鏈無 audit；只有 HITL / MCP 有 |

### 修復規模

- **P0（必做）總成本**：4-6 人日
- **ROI**：最高 — 修好前，任何 reranker / GraphRAG / Graphiti 升級都係徒勞
- **風險**：低 — 均係 wiring 改動，不涉及 schema migration 或新 module

### 為何這份文件重要

Doc 01-08 研究系列聚焦「缺什麼」（Ontology、Bitemporal 等）。
Doc 09 delta 報告聚焦「已有什麼」。
**Doc 10（本文）聚焦「已有的東西是否 work」— 答案係部分不 work**。

---

## 一、範圍與方法

### 審計範圍

| Subsystem | 關注代碼 | 執行路徑 |
|-----------|---------|---------|
| Knowledge | `integrations/knowledge/` + `orchestration/pipeline/steps/step2_knowledge.py` + `api/v1/knowledge/` + `hybrid/orchestrator/dispatch_handlers.py` | Pipeline 被動、Agent 主動 tool、HTTP API |
| Memory | `integrations/memory/` + `orchestration/pipeline/steps/step1_memory.py` + `api/v1/memory/` + `hybrid/orchestrator/dispatch_handlers.py` | 同上三路 |
| Audit | `domain/audit/` + `integrations/audit/` + `integrations/orchestration/audit/` + `api/v1/audit/` + 所有 orchestration pipeline 步驟 | Pipeline emit、API query |

### 審計方法

1. **資料流反向追溯**：從使用者可見 entry（chat API、ingest API、search tool）追溯至最終儲存
2. **配置比對**：embedding model、collection、client mode、class name 逐項 diff
3. **Import 驗證**：確認 import 的 module/class 實際存在
4. **Dead code detection**：反向 grep 所有 import，找無人使用的模組

### 不在本次審計範圍

- HITL wiring（approval_handler 有 audit 係 one positive，主鏈無才係 negative，本次聚焦 negative）
- Intent classifier / LLMRoute 一致性（下一份 audit 處理）
- 前端 SSE event 對應（AG-UI wiring 另議）

---

## 二、Knowledge 層 Wiring Audit

### 2.1 三條並存路徑概覽

```
┌─── 路徑 ① Pipeline Step 2（被動，每 chat query 自動跑）──────────────┐
│  chat_routes → create_default_pipeline → MemoryStep → KnowledgeStep │
│  ├── embedding: text-embedding-ada-002 (1536 dim)                  │
│  ├── Qdrant mode: server (localhost:6333)                          │
│  ├── collection: "ipa_knowledge"                                   │
│  └── retrieval: 純 vector, top_k=3                                  │
│  → 結果：填入 context.knowledge_text，注入 Orchestrator system prompt │
└────────────────────────────────────────────────────────────────────┘

┌─── 路徑 ② Agent Tool（主動，subagent/team 模式下 agent 自行呼叫）──────┐
│  subagent/team → tool_call(search_knowledge) →                     │
│  hybrid/orchestrator/dispatch_handlers.handle_search_knowledge →   │
│  knowledge/rag_pipeline.RAGPipeline.handle_search_knowledge →      │
│  knowledge/retriever.KnowledgeRetriever.retrieve                   │
│  ├── embedding: text-embedding-3-large (3072 dim)                  │
│  ├── Qdrant mode: embedded local ("./qdrant_data")                 │
│  ├── collection: "knowledge_base"                                  │
│  └── retrieval: vector + BM25-like + RRF + simple rerank            │
│  → 結果：返回 results dict 俾 agent 用                               │
└────────────────────────────────────────────────────────────────────┘

┌─── 路徑 ③ Agent Skills（靜態預設知識，與 RAG 無關）────────────────────┐
│  knowledge/agent_skills.py AgentSkillsProvider                     │
│  ├── 3 份硬編碼 ITIL SOP（Incident / Change / EA Reference）         │
│  └── 搜索：純 keyword overlap                                        │
│  → 結果：get_skill_context() 返回 text 俾 prompt 注入                │
└────────────────────────────────────────────────────────────────────┘
```

### 2.2 代碼證據

#### 證據 2.2.1 — 路徑 ① 配置

```python
# backend/src/integrations/orchestration/pipeline/steps/step2_knowledge.py
# Lines 24-26
DEFAULT_COLLECTION = "ipa_knowledge"
DEFAULT_EMBEDDING_MODEL = "text-embedding-ada-002"
DEFAULT_TOP_K = 3

# Lines 60-61
self._qdrant_host = qdrant_host or os.getenv("QDRANT_HOST", "localhost")
self._qdrant_port = qdrant_port or int(os.getenv("QDRANT_PORT", "6333"))

# Lines 146-149
client = QdrantClient(
    host=self._qdrant_host,  # ← SERVER 模式
    port=self._qdrant_port,
)
```

#### 證據 2.2.2 — 路徑 ② 配置

```python
# backend/src/integrations/knowledge/vector_store.py
# Line 16
DEFAULT_COLLECTION = "knowledge_base"

# Lines 43-47
def __init__(
    self,
    collection_name: str = DEFAULT_COLLECTION,
    qdrant_path: str = "./qdrant_data",  # ← LOCAL 檔案
) -> None:

# Line 53-60
async def initialize(self, dimension: int = 3072) -> None:  # ← 3072 dim
    ...
    self._client = QdrantClient(path=self._qdrant_path)  # ← EMBEDDED 模式

# backend/src/integrations/knowledge/embedder.py
# Line 14
DEFAULT_MODEL = "text-embedding-3-large"  # ← 3072 dim

# backend/src/integrations/hybrid/orchestrator/dispatch_handlers.py
# Lines 411-426
async def handle_search_knowledge(self, query, collection=None, limit=5, **kwargs):
    try:
        from src.integrations.knowledge.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline()  # ← 每次 call 都 new instance
        return await pipeline.handle_search_knowledge(...)
```

#### 證據 2.2.3 — 路徑 ① 被實際 wire 入生產 chat flow

```python
# backend/src/api/v1/orchestration/chat_routes.py
# Lines 199-208
pipeline = create_default_pipeline()  # Memory + Knowledge (Steps 1-2)
pipeline.configure_steps([
    *pipeline._steps,  # Steps 1-2 from factory
    IntentStep(),       # Step 3
    RiskStep(),         # Step 4
    HITLGateStep(...),  # Step 5
    LLMRouteStep(),     # Step 6
])
```

→ 即每個 chat 訊息都會執行 KnowledgeStep

#### 證據 2.2.4 — 零 ingestion 寫入 `ipa_knowledge`

```bash
# Grep pattern: ipa_knowledge
# Matches:
step2_knowledge.py:24        DEFAULT_COLLECTION = "ipa_knowledge"  # 讀取
poc/agent_team_poc.py:927    qd.query_points("ipa_knowledge", ...) # 讀取（PoC）
poc/agent_team_poc.py:2166   qd.query_points("ipa_knowledge", ...) # 讀取（PoC）

# Grep pattern: upsert.*ipa_knowledge | create_collection.*ipa_knowledge | ingest.*ipa_knowledge
# Matches: 0 hits
```

→ **沒有任何代碼寫入 `ipa_knowledge` collection**

#### 證據 2.2.5 — Ingestion API 寫去哪

```python
# backend/src/api/v1/knowledge/routes.py
# Lines 31-33
if _rag_pipeline is None:
    from src.integrations.knowledge.rag_pipeline import RAGPipeline
    _rag_pipeline = RAGPipeline()  # ← 預設 collection="knowledge_base"

# Lines 96-100
@router.post("/ingest", ...)
async def ingest_text(body: IngestTextRequest) -> IngestResponse:
    pipeline = await get_rag_pipeline()
    result = await pipeline.ingest_text(...)  # → knowledge_base 倉

# backend/src/integrations/knowledge/rag_pipeline.py
# Lines 35-52
def __init__(
    self,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    collection: str = "knowledge_base",  # ← 預設倉
):
    ...
    self._vector_store = VectorStoreManager(collection_name=collection)
    #   ↑ 實例化為 local mode "./qdrant_data"
```

→ **Ingest API 寫入 `./qdrant_data/knowledge_base`**；**Step 2 讀取 `localhost:6333/ipa_knowledge`** — 兩個獨立儲存

### 2.3 Gap 矩陣

| 不一致點 | 路徑 ①（Step 2） | 路徑 ②（Tool / Ingest API） | 結果 |
|---------|-----------------|---------------------------|------|
| Embedding 模型 | `ada-002`（1536 dim）| `3-large`（3072 dim）| 維度不相容；**結構上無法共用同一 collection** |
| Qdrant 連線模式 | server（host:port）| embedded local（path）| 儲存位置完全獨立 |
| Collection 名稱 | `ipa_knowledge` | `knowledge_base` | 同一 query 命中完全不同資料 |
| 檢索邏輯 | 純 vector top_k=3 | vector + BM25 + RRF + simple rerank | 結果分布差異大 |
| 使用頻率 | 每個 chat query | 僅 subagent/team mode agent 主動 call | — |

### 2.4 實際使用者體驗

```
使用者行為                          Pipeline 反應                    結果
─────────────────────────────────────────────────────────────────────
① 使用者 POST /api/v1/knowledge    ✅ 寫入 ./qdrant_data/            OK
  /ingest 文件                      knowledge_base（3072d）
─────────────────────────────────────────────────────────────────────
② 使用者在 chat 問問題              ✅ Step 2 連 localhost:6333       knowledge_text = ""
                                    搜 ipa_knowledge（1536d）         （因為那裡沒資料）
                                    → query_points 返回 []             → Orchestrator
                                                                       system prompt
                                                                       無企業知識 context
─────────────────────────────────────────────────────────────────────
③ LLMRouteStep 決定 direct_answer  ✅ LLM 用通用知識回答              使用者收到答案，
                                    ❌ 無 ingested 知識 grounding      但其實 miss 咗
                                                                       自己 ingest 嘅嘢
─────────────────────────────────────────────────────────────────────
④ LLMRouteStep 決定 subagent/team  ✅ agent 可 call search_knowledge  tool 搜 local
                                    → 走 RAGPipeline                   knowledge_base（3072d）
                                    → 找到 ingested 資料               → agent 拿到知識
```

**結論**：
- 走 **direct_answer（PoC 測量佔 80% query）** 的使用者，知識層完全失效
- 走 **subagent/team** 的使用者，知識層部分生效（要 agent 主動 call）

### 2.5 Gap 清單

| ID | 描述 | 嚴重度 | 修復估時 |
|----|------|-------|---------|
| K-01 | Step 2 與 Ingest API 寫去不同 Qdrant 倉 | 🔴 CRITICAL | 0.5-1 天 |
| K-02 | Step 2 用 ada-002（舊，1536d），其他路徑用 3-large（3072d） | 🔴 CRITICAL | 0.5 天（配合 K-01）|
| K-03 | Step 2 bypass `RAGPipeline`，重複實作 search 邏輯 | 🟡 MEDIUM | 合併入 K-01 修復 |
| K-04 | Agent Skills（硬編碼 3 份 ITIL SOP）與 Qdrant 知識完全隔離 | 🟡 MEDIUM | 1-2 天（YAML 化）|
| K-05 | `dispatch_handlers` 每次 call 都 `RAGPipeline()` 重新實例化（無 cache）| 🟢 LOW | 0.5 天 |
| K-06 | `_simple_rerank` 只係字詞 overlap，非 cross-encoder | 🟡 MEDIUM | 1 週（Cohere Rerank 3 quick win）|

---

## 三、Memory 層 Wiring Audit

### 3.1 三條並存路徑概覽

```
┌─── 路徑 ① Pipeline Step 1（被動，每 chat query 自動跑）──────────────┐
│  MemoryStep → UnifiedMemoryManager + ContextBudgetManager           │
│  → context.memory_text 注入 Orchestrator system prompt              │
│  狀態：✅ 正常                                                        │
└────────────────────────────────────────────────────────────────────┘

┌─── 路徑 ② Agent Tool（主動，subagent/team 模式下 agent 自行呼叫）──────┐
│  subagent/team → tool_call(search_memory) →                         │
│  hybrid/orchestrator/dispatch_handlers.handle_search_memory →       │
│  from src.integrations.memory.mem0_service import Mem0Service       │
│  ❌ mem0_service 模組不存在！❌ Mem0Service class 亦不存在！           │
│  → ImportError → 捕獲 → 返回 {"results": [], "message": "not avail"} │
│  狀態：🚨 永久 broken                                                 │
└────────────────────────────────────────────────────────────────────┘

┌─── 路徑 ③ HTTP API（外部調用）─────────────────────────────────────┐
│  /api/v1/memory/* → UnifiedMemoryManager                            │
│  狀態：✅ 正常                                                        │
└────────────────────────────────────────────────────────────────────┘
```

### 3.2 代碼證據

#### 證據 3.2.1 — `search_memory` tool 實作

```python
# backend/src/integrations/hybrid/orchestrator/dispatch_handlers.py
# Lines 355-377
async def handle_search_memory(
    self,
    query: str,
    user_id: Optional[str] = None,
    limit: int = 5,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Search user memory via mem0."""
    try:
        from src.integrations.memory.mem0_service import Mem0Service  # ← 不存在的模組
        service = Mem0Service()
        results = await service.search(
            query=query,
            user_id=user_id,
            limit=limit,
        )
        return {"results": results, "count": len(results)}
    except ImportError:
        logger.warning("Mem0Service not available")
        return {"results": [], "count": 0, "message": "Memory service not available"}
```

#### 證據 3.2.2 — `Mem0Service` 不存在

```bash
# Glob pattern: backend/**/mem0_service*
# Matches: 0 hits

# Glob pattern: backend/**/mem0*.py
# Matches:
backend/src/integrations/memory/mem0_client.py  # 只得呢個

# Grep pattern: class Mem0Service | Mem0Service\s*=
# Matches: 0 hits
```

→ **`Mem0Service` class 完全不存在**；實際存在的是 `Mem0Client`（位於 `mem0_client.py`），API 名稱也不同（`search_memory()` vs `search()`）

#### 證據 3.2.3 — 正確路徑（Step 1 + API）用 UnifiedMemoryManager

```python
# backend/src/integrations/orchestration/pipeline/steps/step1_memory.py
# Lines 106-113
async def _get_memory_manager(self) -> object:
    if self._memory_manager is None:
        from src.integrations.memory.unified_memory import UnifiedMemoryManager
        self._memory_manager = UnifiedMemoryManager()
        await self._memory_manager.initialize()
    return self._memory_manager

# backend/src/api/v1/memory/routes.py  —— Grep confirmed UnifiedMemoryManager usage
# 13+ references
```

### 3.3 Gap 清單

| ID | 描述 | 嚴重度 | 修復估時 | 狀態 |
|----|------|-------|---------|------|
| M-01 | `search_memory` tool import 不存在的 `Mem0Service`，永久 silent failure | 🔴 CRITICAL | 1 天 | ✅ **Fixed 2026-04-20（FIX-001, Sprint Wiring Fix 001）**|
| M-02 | Step 1 docstring 稱「4-layer: pinned, working, session, long-term」但 UnifiedMemoryManager 實際 3 層 | 🟢 LOW（文件不符，不影響 runtime） | 10 分鐘 | pending |

### 3.4 修復方案（M-01）— ✅ DELIVERED

**實際修復**（見 `FIX-001-search-memory-broken-import.md`）：

```python
# 正確 API：UnifiedMemoryManager.search() — 非 .search_memory()
# user_id 係必填（無 Optional default）
# 返回 List[MemorySearchResult]，每個有 .to_dict()

async def _get_memory_manager(self):
    """Lazy singleton — avoid per-call re-initialise."""
    if self._memory_manager is None:
        from src.integrations.memory.unified_memory import UnifiedMemoryManager
        self._memory_manager = UnifiedMemoryManager()
        await self._memory_manager.initialize()
    return self._memory_manager

async def handle_search_memory(self, query, user_id=None, limit=5, **kwargs):
    if user_id is None:
        return {"results": [], "count": 0, "error": "user_id required", "tool_broken": False}
    try:
        manager = await self._get_memory_manager()
        results = await manager.search(query=query, user_id=user_id, limit=limit)
        return {
            "results": [r.to_dict() for r in results],
            "count": len(results),
            "layers_searched": ["working", "session", "long_term"],
            "tool_broken": False,
        }
    except Exception as e:
        logger.error("Memory search failed: %s", e, exc_info=True)
        return {"results": [], "count": 0, "error": str(e)[:200], "tool_broken": True}
```

**糾正原建議錯誤**：Doc 10 v1.0 寫 `manager.search_memory()` — **錯誤**。實際 API 係 `manager.search(query, user_id, ...)`，由 code-reviewer panel 於 Doc 11 發現。

**Test coverage**：`tests/unit/integrations/hybrid/orchestrator/test_dispatch_handlers.py` 新增 5 個 unit test 覆蓋 user_id 缺失、singleton 行為、exception handling、regression guard。

---

## 四、Audit 層 Wiring Audit

### 4.1 三個並存的 Audit 模組

| 位置 | LOC | 核心 class | 實際使用者 | 狀態 |
|------|-----|-----------|-----------|------|
| `domain/audit/logger.py` | ~250 | `AuditLogger` + `AuditAction` + `AuditResource` + `AuditSeverity` enums | `api/v1/audit/routes.py`、`api/v1/mcp/routes.py`、`hitl/approval_handler.py` | ✅ 生產使用 |
| `integrations/audit/` | 4 files | `DecisionTracker`、`ReportGenerator` | `api/v1/audit/decision_routes.py` | ✅ 生產使用（局部）|
| `integrations/orchestration/audit/logger.py` | 281 | 另一個 `AuditLogger` + `AuditEntry` | **🚨 零外部 import** | 🔴 dead code |

### 4.2 代碼證據

#### 證據 4.2.1 — Orchestration AuditLogger orphan 驗證

```bash
# Grep pattern: from src.integrations.orchestration.audit | orchestration\.audit
# Matches:
integrations/orchestration/audit/logger.py:82
    logger_name: str = "orchestration.audit",  # ← 只得 self-reference

# 其他任何檔案 import 此 module 的 matches: 0 hits
```

→ `integrations/orchestration/audit/logger.py`（281 LOC）完全無人 import

#### 證據 4.2.2 — Main Chat Flow 零 audit emission

```bash
# 對以下目錄 Grep audit_logger | AuditLogger | log_audit | audit_event | \.audit\(
integrations/orchestration/pipeline/           → 0 hits
integrations/orchestration/dispatch/           → 0 hits
api/v1/orchestration/ (chat_routes 所在)       → 0 hits
```

→ Phase 28/45/46/47 建立的主 chat 鏈完全無 audit emission

#### 證據 4.2.3 — 局部有 audit 的地方

```bash
# AuditLogger 實際呼叫者
api/v1/audit/routes.py:60   get_audit_logger()        # audit API 本身（self-consuming）
api/v1/audit/routes.py:65   AuditLogger()
api/v1/mcp/routes.py:83     get_audit_logger()        # MCP tool call ✅
api/v1/mcp/routes.py:87     AuditLogger()
hitl/approval_handler.py:340 self.audit_logger = ...  # HITL 批准 ✅
```

### 4.3 Audit 替代機制（已有但不等同 audit）

| 機制 | 目的 | 是否符合 audit 要求 |
|------|------|------------------|
| `TranscriptService`（`pipeline/service.py:496 append()`） | 對話歷史 for UI replay | ❌ 可變；無 immutability；無 bitemporal；無 actor / resource / severity 分級 |
| `checkpoint_storage`（`step3/5/8 .save(checkpoint)`） | HITL / post-process state 持久化 | ❌ 目的是恢復執行；非合規追溯 |
| `integrations/orchestration/pipeline/persistence.py`（Phase 47 Sprint 169）| Execution log persistence | ⚪ **待進一步驗證** — 名稱似 audit 但實際 scope 未明 |

### 4.4 與研究 Doc 05 / 08 期望的對照

| Doc 05 L6 要求 | 現況 | Gap |
|---------------|------|-----|
| Bitemporal（event_time + ingestion_time）| 基礎 logger 僅 event_time | 🔴 缺 |
| PostgreSQL 持久化 + immutable rules | 在 JSON log 層面 | 🔴 缺（與 `AUDIT_NO_DELETE` rule 等）|
| Audit chain（parent_event_id）| 未實作 | 🔴 缺 |
| PII redactor | 未實作 | 🔴 缺 |
| EU AI Act 分級 | 未實作 | 🔴 缺 |
| **All step audit-traceable** | **Main chat 主鏈零 audit** | 🚨 **本次審計最嚴重發現** |

### 4.5 Gap 清單

| ID | 描述 | 嚴重度 | 修復估時 |
|----|------|-------|---------|
| A-01 | Main chat flow（Pipeline 8 steps + Dispatch）零 audit emission | 🔴 HIGH | 2-3 天（加 audit emit hook） |
| A-02 | `integrations/orchestration/audit/logger.py` 281 LOC 完全 orphan | 🟡 MEDIUM | 0.5 天（刪除或合併）|
| A-03 | 2 個 `AuditLogger` 同名 class 在不同 module，易 import 錯 | 🟡 MEDIUM | 0.5 天（rename 其一）|
| A-04 | `domain/audit/logger.py` 無 bitemporal / immutable / PII redactor | 🔴 HIGH | 4-6 週（Doc 08 原計劃）|
| A-05 | `pipeline/persistence.py` scope 未明，與 audit 關係需釐清 | 🟡 MEDIUM | 0.5 天（讀代碼確認）|

---

## 五、三層綜合對照

### 5.1 路徑 × 層 對照矩陣

| 層 | Passive Pipeline 路徑 | Agent Tool 路徑 | HTTP API 路徑 |
|----|---------------------|----------------|--------------|
| **Knowledge** | Step 2 → Qdrant server / ada-002 / `ipa_knowledge`<br>🔴 **永遠搜空** | Tool → RAGPipeline → local / 3-large / `knowledge_base`<br>✅ 正常 | `/api/v1/knowledge/*` → RAGPipeline<br>✅ 正常 |
| **Memory** | Step 1 → UnifiedMemoryManager<br>✅ 正常 | Tool → `Mem0Service`（不存在）<br>🔴 **永遠 broken** | `/api/v1/memory/*` → UnifiedMemoryManager<br>✅ 正常 |
| **Audit** | （無）<br>🔴 **無 emission** | （無）<br>🔴 **無 emission** | `/api/v1/audit/*` → domain AuditLogger<br>✅ 正常（但資料源只有 HITL、MCP）|

### 5.2 使用者實際能得到什麼（以目前 wiring）

```
使用者走 direct_answer 路徑（80% query）:
├─ knowledge grounding    ❌ 無（Step 2 空）
├─ memory grounding       ✅ 有（Step 1 ok）
└─ audit trail            ❌ 無（主鏈零 emission）

使用者走 subagent/team 路徑（20% query）:
├─ knowledge grounding    ⚠️ 弱 Agentic（要 agent 主動 call search_knowledge）
├─ memory grounding       ⚠️ 弱 Agentic（但 search_memory tool broken，只剩 Step 1 被動 inject）
└─ audit trail            ❌ 無（主鏈零 emission；agent tool call 亦無 audit）
```

---

## 六、修復計劃

### 6.1 P0（CRITICAL，總計 4-6 天）

| ID | 任務 | 估時 | 依賴 |
|----|------|-----|------|
| K-01+02+03 | Knowledge wiring 統一：Step 2 改用 RAGPipeline 或對齊 config（model、collection、client mode）| 1 天 | — |
| M-01 | `search_memory` tool 改用 `UnifiedMemoryManager.search_memory()`；驗證 API 兼容 | 1 天 | — |
| A-01 | Main chat flow 加 audit emission：Pipeline base step + Dispatch hook → domain `AuditLogger` | 2-3 天 | — |

### 6.2 P1（HIGH，總計 2-4 天）

| ID | 任務 | 估時 |
|----|------|-----|
| A-02 | 刪除或合併 `integrations/orchestration/audit/logger.py` dead code | 0.5 天 |
| A-03 | Rename orphan `AuditLogger` class 避免混淆 | 0.5 天 |
| A-05 | 讀 `pipeline/persistence.py`（Phase 47 Sprint 169）確認與 audit 關係 | 0.5 天 |
| K-06 | Cohere Rerank 3 替換 `_simple_rerank` | 1 週（quick win，非 critical path） |
| M-02 | Step 1 docstring 修正（4-layer → 3-layer） | 10 分鐘 |

### 6.3 P2（Doc 08 原計劃，基於 P0 修好後）

| ID | 任務 | 估時 |
|----|------|-----|
| A-04 | Bitemporal audit + PostgreSQL + immutable rules + PII redactor + EU AI Act 分級 | 4-6 週 |
| K-04 | Agent Skills YAML 化 + 與 Qdrant 知識統一 | 1-2 週 |
| K-05 | `dispatch_handlers` RAGPipeline instance cache | 0.5 天 |

### 6.4 修復順序建議

```
Week 1:
  Day 1-2: K-01+02+03 (Knowledge wiring 統一)
  Day 3:   M-01 (search_memory tool 修復)
  Day 4-5: A-01 (Main chat audit emission)

Week 2:
  Day 1:   A-02 + A-03 (Audit dead code + rename)
  Day 2-5: K-06 (Cohere Rerank quick win)

Week 3+:
  A-04 (Bitemporal) 與 L3 Ontology 並行規劃
  K-04 (Agent Skills YAML) 併入 Agent Expert Registry 擴展
```

### 6.5 驗收標準

**K-01+02+03 修復完成驗收**
- [ ] `step2_knowledge.py` 與 `vector_store.py` 用同一 embedding model（名稱 + 維度）
- [ ] 透過 `/api/v1/knowledge/ingest` 上傳文件後，在 chat 問相關問題，Step 2 能返回命中結果（`context.knowledge_text` 非空）
- [ ] Integration test：ingest → chat → 驗證 knowledge_text 有內容
- [ ] 兩個路徑使用同一 `QdrantClient` 連線模式（path 或 host/port 統一）

**M-01 修復完成驗收**
- [ ] `from src.integrations.memory.mem0_service import Mem0Service` 從代碼 remove
- [ ] 在 team mode 下，agent call `search_memory` tool 能返回實際 memory（非「not available」）
- [ ] Integration test：寫入 memory → agent call search_memory → 驗證有結果

**A-01 修復完成驗收**
- [ ] 每次 chat 訊息完成後，`/api/v1/audit/events` 能查到對應 audit entries（至少 intent / risk / route / dispatch 結果各一筆）
- [ ] Audit entries 包含 actor（user_id）、action、resource、trace_id
- [ ] Integration test：chat → query audit API → 驗證有 entries

---

## 七、風險與不確定性

### 本份審計本身的 caveats

1. **`pipeline/persistence.py` 未深讀**（Phase 47 Sprint 169 新增）— 可能已是 A-01 的部分實作，需確認後調整估時
2. **`UnifiedMemoryManager.search_memory()` 方法簽名未驗證** — M-01 修復前需快速讀 API
3. **本次未涵蓋 frontend SSE event wiring** — chat 前端是否即使 Step 2 搜空仍顯示「已搜索知識庫」誤導，未驗證
4. **未涵蓋 PoC `agent_team_poc.py`** — 該檔案的路徑可能與本次描述的 production 路徑不同，但 PoC 不影響生產
5. **未涵蓋 ADF / n8n / 外部 ingestion pipeline** — 若有外部 script 寫入 Qdrant server `ipa_knowledge`，Step 2 可能有資料（但本 repo 沒找到此類 script）

### 風險

- **K-01 修復風險**：如生產環境實際有 Qdrant server 被手動 seed 過 `ipa_knowledge`，統一 config 後現有資料會失聯。**建議修復前先 snapshot server state**
- **A-01 修復風險**：每 step 加 audit emission 會增加 latency（每 chat +5-10 ms）。需 benchmark 驗證在可接受範圍

---

## 八、參考代碼位置索引

### Knowledge

- `backend/src/integrations/orchestration/pipeline/steps/step2_knowledge.py` — 路徑 ① 主體
- `backend/src/integrations/knowledge/rag_pipeline.py` — 路徑 ② 主體
- `backend/src/integrations/knowledge/retriever.py` — Hybrid 邏輯
- `backend/src/integrations/knowledge/vector_store.py` — VectorStoreManager（local mode）
- `backend/src/integrations/knowledge/embedder.py` — EmbeddingManager
- `backend/src/integrations/knowledge/agent_skills.py` — 路徑 ③ 主體
- `backend/src/api/v1/knowledge/routes.py` — HTTP API
- `backend/src/api/v1/orchestration/chat_routes.py` — Pipeline 組裝

### Memory

- `backend/src/integrations/orchestration/pipeline/steps/step1_memory.py` — 路徑 ① 主體
- `backend/src/integrations/memory/unified_memory.py` — UnifiedMemoryManager
- `backend/src/integrations/memory/mem0_client.py` — Mem0Client（正確類名）
- `backend/src/integrations/hybrid/orchestrator/dispatch_handlers.py:355-377` — search_memory tool（BROKEN）
- `backend/src/api/v1/memory/routes.py` — HTTP API

### Audit

- `backend/src/domain/audit/logger.py` — 生產 AuditLogger
- `backend/src/integrations/audit/` — DecisionTracker
- `backend/src/integrations/orchestration/audit/logger.py` — **ORPHAN**
- `backend/src/api/v1/audit/routes.py` — HTTP API
- `backend/src/integrations/orchestration/hitl/approval_handler.py:340` — HITL audit hook（唯一生產 emission 之一）
- `backend/src/integrations/orchestration/pipeline/service.py:496` — TranscriptService.append（非 audit）
- `backend/src/integrations/orchestration/pipeline/persistence.py` — Phase 47 execution persistence（待驗證）

### Orchestration Core（對照）

- `backend/src/integrations/orchestration/pipeline/service.py` — Pipeline runner
- `backend/src/integrations/orchestration/pipeline/__init__.py` — 文檔 + 初始化
- `backend/src/integrations/orchestration/dispatch/executors/` — Direct / Subagent / Team executors
- `backend/src/integrations/hybrid/orchestrator/dispatch_handlers.py` — Tool handler registry

---

## 九、版本記錄

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-20 | Claude + Chris | Initial wiring audit based on main commit `179d7f8` (Phase 47 W1) |

**Related docs**：
- `docs/09-git-worktree-working-folder/knowledge-base-enterprise/09-ipa-main-delta.md` — 6-layer gap analysis
- `docs/09-git-worktree-working-folder/knowledge-base-enterprise/01-foundation-concepts.md` — RAG / Memory / GraphRAG 概念
- `docs/09-git-worktree-working-folder/knowledge-base-enterprise/05-end-to-end-architecture.md` — 6-layer 架構設計
- `docs/09-git-worktree-working-folder/knowledge-base-enterprise/08-ipa-platform-recommendations.md` — 9-month roadmap 建議
