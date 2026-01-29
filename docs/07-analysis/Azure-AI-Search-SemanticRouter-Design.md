# Azure AI Search 整合 SemanticRouter 設計文件

> **文件版本**: 1.0
> **建立日期**: 2026-01-29
> **狀態**: 設計階段
> **相關**: Phase 28 三層路由系統

---

## 1. 背景與動機

### 1.1 當前實現的限制

目前 IPA Platform 的 SemanticRouter 使用 `semantic-router` 庫（Aurelio），存在以下限制：

| 限制 | 說明 | 影響 |
|------|------|------|
| **內存存儲** | 路由向量存儲在內存中 | 服務重啟需重新編碼 |
| **靜態路由** | 路由在代碼中預定義 | 無法動態新增/修改 |
| **無持久化** | 沒有外部存儲 | 學習的新意圖無法保存 |
| **擴展性差** | 單一服務處理所有向量計算 | 高併發時效能瓶頸 |

### 1.2 整合 Azure AI Search 的優勢

| 優勢 | 說明 |
|------|------|
| **持久化存儲** | 路由向量存儲在 Azure 雲端，不受服務重啟影響 |
| **動態路由管理** | 可以通過 API 動態新增、修改、刪除路由 |
| **企業級 SLA** | 99.9% 可用性保證 |
| **混合搜索** | 支持向量搜索 + 關鍵字搜索 + 過濾器 |
| **語義排名** | 內建 Semantic Ranker 提高搜索品質 |
| **安全合規** | Azure AD 整合、RBAC、加密存儲 |
| **與 Azure OpenAI 整合** | 原生支持 Azure OpenAI Embedding |

---

## 2. 架構設計

### 2.1 整體架構圖

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        IPA Platform - SemanticRouter with Azure AI Search            │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────┐                      ┌─────────────────────────────────────┐   │
│  │   Frontend      │                      │         Azure Cloud                  │   │
│  │   /chat         │                      │                                      │   │
│  └────────┬────────┘                      │  ┌─────────────────────────────────┐ │   │
│           │                               │  │      Azure AI Search             │ │   │
│           ↓                               │  │      (Semantic Routes Index)     │ │   │
│  ┌─────────────────┐                      │  │                                  │ │   │
│  │   API Layer     │                      │  │  ┌──────────────────────────┐   │ │   │
│  │   /orchestration│                      │  │  │  semantic-routes        │   │ │   │
│  └────────┬────────┘                      │  │  │  ────────────────────    │   │ │   │
│           │                               │  │  │  • id                    │   │ │   │
│           ↓                               │  │  │  • route_name            │   │ │   │
│  ┌─────────────────────────────────────┐  │  │  │  • category              │   │ │   │
│  │        BusinessIntentRouter          │  │  │  │  • utterance            │   │ │   │
│  │  ┌───────────────────────────────┐  │  │  │  │  • utterance_vector     │   │ │   │
│  │  │ Layer 1: PatternMatcher       │  │  │  │  │  • workflow_type        │   │ │   │
│  │  │ (rules.yaml - 34 rules)       │  │  │  │  │  • risk_level           │   │ │   │
│  │  └───────────────────────────────┘  │  │  │  │  • enabled              │   │ │   │
│  │               ↓ (if no match)       │  │  │  └──────────────────────────┘   │ │   │
│  │  ┌───────────────────────────────┐  │  │  └─────────────────────────────────┘ │   │
│  │  │ Layer 2: AzureSemanticRouter  │←─┼──┼──────────── Vector Search ──────────│   │
│  │  │ (Azure AI Search)             │  │  │                                      │   │
│  │  └───────────────────────────────┘  │  │  ┌─────────────────────────────────┐ │   │
│  │               ↓ (if no match)       │  │  │      Azure OpenAI                │ │   │
│  │  ┌───────────────────────────────┐  │  │  │      (Embeddings)                │ │   │
│  │  │ Layer 3: LLMClassifier        │←─┼──┼──┤                                  │ │   │
│  │  │ (Claude Haiku)                │  │  │  │  text-embedding-ada-002         │ │   │
│  │  └───────────────────────────────┘  │  │  └─────────────────────────────────┘ │   │
│  └─────────────────────────────────────┘  │                                      │   │
│                                           └──────────────────────────────────────┘   │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                          Route Management API                                │    │
│  │                                                                              │    │
│  │  POST   /orchestration/routes          # 新增路由                           │    │
│  │  GET    /orchestration/routes          # 列出所有路由                        │    │
│  │  GET    /orchestration/routes/{id}     # 獲取單一路由                        │    │
│  │  PUT    /orchestration/routes/{id}     # 更新路由                           │    │
│  │  DELETE /orchestration/routes/{id}     # 刪除路由                           │    │
│  │  POST   /orchestration/routes/sync     # 從 YAML 同步到 Azure               │    │
│  │  POST   /orchestration/routes/search   # 測試語義搜索                       │    │
│  │                                                                              │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 數據流程

```
用戶輸入: "ETL Pipeline 今天跑失敗了"
                │
                ↓
┌───────────────────────────────────────────────────────────────────────────────────┐
│ Step 1: PatternMatcher (< 10ms)                                                    │
│ ─────────────────────────────────                                                  │
│ • 檢查是否匹配 rules.yaml 中的 34 條規則                                          │
│ • 使用預編譯正則表達式                                                            │
│ • 如果匹配且 confidence >= 0.90 → 返回結果                                        │
│ • 否則 → 繼續到 Layer 2                                                           │
└───────────────────────────────────────────────────────────────────────────────────┘
                │ (no match or confidence < 0.90)
                ↓
┌───────────────────────────────────────────────────────────────────────────────────┐
│ Step 2: AzureSemanticRouter (< 100ms)                                              │
│ ─────────────────────────────────────                                              │
│ a. 調用 Azure OpenAI Embedding API                                                 │
│    POST /openai/deployments/text-embedding-ada-002/embeddings                      │
│    Input: "ETL Pipeline 今天跑失敗了"                                              │
│    Output: [0.0234, -0.0123, ...] (1536 dimensions)                               │
│                                                                                    │
│ b. 調用 Azure AI Search Vector Search                                              │
│    POST /indexes/semantic-routes/docs/search                                       │
│    {                                                                               │
│      "vectorQueries": [{                                                           │
│        "vector": [0.0234, -0.0123, ...],                                          │
│        "k": 3,                                                                     │
│        "fields": "utterance_vector"                                               │
│      }],                                                                           │
│      "filter": "enabled eq true"                                                   │
│    }                                                                               │
│                                                                                    │
│ c. 返回最佳匹配（如果 similarity >= 0.85）                                        │
│    {                                                                               │
│      "route_name": "incident_etl",                                                │
│      "category": "incident",                                                       │
│      "sub_intent": "etl_failure",                                                 │
│      "similarity": 0.92                                                           │
│    }                                                                               │
│                                                                                    │
│ • 如果 similarity >= 0.85 → 返回結果                                              │
│ • 否則 → 繼續到 Layer 3                                                           │
└───────────────────────────────────────────────────────────────────────────────────┘
                │ (similarity < 0.85)
                ↓
┌───────────────────────────────────────────────────────────────────────────────────┐
│ Step 3: LLMClassifier (< 2000ms)                                                   │
│ ──────────────────────────────────                                                 │
│ • 調用 Claude Haiku 進行 LLM 分類                                                 │
│ • 返回分類結果和完整性評估                                                        │
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Azure AI Search 索引設計

### 3.1 索引結構

```json
{
  "name": "semantic-routes",
  "fields": [
    {
      "name": "id",
      "type": "Edm.String",
      "key": true,
      "searchable": false,
      "filterable": false
    },
    {
      "name": "route_name",
      "type": "Edm.String",
      "searchable": true,
      "filterable": true,
      "sortable": true
    },
    {
      "name": "category",
      "type": "Edm.String",
      "searchable": false,
      "filterable": true,
      "facetable": true
    },
    {
      "name": "sub_intent",
      "type": "Edm.String",
      "searchable": true,
      "filterable": true
    },
    {
      "name": "utterance",
      "type": "Edm.String",
      "searchable": true,
      "analyzer": "zh-Hans.microsoft"
    },
    {
      "name": "utterance_vector",
      "type": "Collection(Edm.Single)",
      "dimensions": 1536,
      "vectorSearchProfile": "vector-profile"
    },
    {
      "name": "workflow_type",
      "type": "Edm.String",
      "searchable": false,
      "filterable": true
    },
    {
      "name": "risk_level",
      "type": "Edm.String",
      "searchable": false,
      "filterable": true
    },
    {
      "name": "description",
      "type": "Edm.String",
      "searchable": true
    },
    {
      "name": "enabled",
      "type": "Edm.Boolean",
      "filterable": true
    },
    {
      "name": "created_at",
      "type": "Edm.DateTimeOffset",
      "filterable": true,
      "sortable": true
    },
    {
      "name": "updated_at",
      "type": "Edm.DateTimeOffset",
      "filterable": true,
      "sortable": true
    }
  ],
  "vectorSearch": {
    "algorithms": [
      {
        "name": "hnsw-algorithm",
        "kind": "hnsw",
        "hnswParameters": {
          "m": 4,
          "efConstruction": 400,
          "efSearch": 500,
          "metric": "cosine"
        }
      }
    ],
    "profiles": [
      {
        "name": "vector-profile",
        "algorithm": "hnsw-algorithm"
      }
    ]
  }
}
```

### 3.2 範例文檔

```json
{
  "id": "incident_etl_001",
  "route_name": "incident_etl",
  "category": "incident",
  "sub_intent": "etl_failure",
  "utterance": "ETL Pipeline 今天跑失敗了",
  "utterance_vector": [0.0234, -0.0123, ...],
  "workflow_type": "magentic",
  "risk_level": "high",
  "description": "ETL pipeline failure incidents",
  "enabled": true,
  "created_at": "2026-01-29T00:00:00Z",
  "updated_at": "2026-01-29T00:00:00Z"
}
```

---

## 4. AzureSemanticRouter 類設計

### 4.1 類結構

```python
# backend/src/integrations/orchestration/intent_router/semantic_router/azure_router.py

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import os

from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

from ..models import (
    ITIntentCategory,
    SemanticRoute,
    SemanticRouteResult,
    WorkflowType,
    RiskLevel,
)


@dataclass
class AzureSemanticRouterConfig:
    """Configuration for Azure Semantic Router."""

    # Azure AI Search
    search_endpoint: str
    search_api_key: str
    index_name: str = "semantic-routes"

    # Azure OpenAI (for embeddings)
    openai_endpoint: str
    openai_api_key: str
    embedding_deployment: str = "text-embedding-ada-002"

    # Search parameters
    similarity_threshold: float = 0.85
    top_k: int = 3

    @classmethod
    def from_env(cls) -> "AzureSemanticRouterConfig":
        """Create configuration from environment variables."""
        return cls(
            search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT", ""),
            search_api_key=os.getenv("AZURE_SEARCH_API_KEY", ""),
            index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "semantic-routes"),
            openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
            embedding_deployment=os.getenv(
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
                "text-embedding-ada-002"
            ),
            similarity_threshold=float(
                os.getenv("SEMANTIC_SIMILARITY_THRESHOLD", "0.85")
            ),
            top_k=int(os.getenv("SEMANTIC_TOP_K", "3")),
        )


class AzureSemanticRouter:
    """
    Semantic Router using Azure AI Search for vector storage and search.

    Features:
    - Persistent vector storage in Azure cloud
    - Dynamic route management (CRUD)
    - Hybrid search (vector + keyword + filters)
    - Enterprise-grade SLA and security
    """

    def __init__(self, config: Optional[AzureSemanticRouterConfig] = None):
        """Initialize the Azure Semantic Router."""
        self.config = config or AzureSemanticRouterConfig.from_env()

        # Initialize Azure AI Search client
        self._search_client = SearchClient(
            endpoint=self.config.search_endpoint,
            index_name=self.config.index_name,
            credential=AzureKeyCredential(self.config.search_api_key),
        )

        # Initialize Azure OpenAI client for embeddings
        self._openai_client = AzureOpenAI(
            azure_endpoint=self.config.openai_endpoint,
            api_key=self.config.openai_api_key,
            api_version="2024-02-15-preview",
        )

        self._initialized = True

    @property
    def is_available(self) -> bool:
        """Check if Azure services are configured."""
        return bool(
            self.config.search_endpoint
            and self.config.search_api_key
            and self.config.openai_endpoint
            and self.config.openai_api_key
        )

    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for text using Azure OpenAI."""
        response = self._openai_client.embeddings.create(
            model=self.config.embedding_deployment,
            input=text,
        )
        return response.data[0].embedding

    async def route(self, user_input: str) -> SemanticRouteResult:
        """
        Route user input using Azure AI Search vector search.

        Args:
            user_input: The user's input text

        Returns:
            SemanticRouteResult with match information
        """
        if not self.is_available:
            return SemanticRouteResult.no_match()

        try:
            # 1. Get embedding for user input
            query_vector = self._get_embedding(user_input)

            # 2. Perform vector search
            vector_query = VectorizedQuery(
                vector=query_vector,
                k_nearest_neighbors=self.config.top_k,
                fields="utterance_vector",
            )

            results = self._search_client.search(
                search_text=None,
                vector_queries=[vector_query],
                filter="enabled eq true",
                select=["route_name", "category", "sub_intent",
                        "workflow_type", "risk_level", "description"],
            )

            # 3. Process results
            for result in results:
                similarity = result["@search.score"]

                if similarity >= self.config.similarity_threshold:
                    return SemanticRouteResult(
                        matched=True,
                        intent_category=ITIntentCategory(result["category"]),
                        sub_intent=result["sub_intent"],
                        similarity=similarity,
                        route_name=result["route_name"],
                        metadata={
                            "workflow_type": result["workflow_type"],
                            "risk_level": result["risk_level"],
                            "description": result.get("description"),
                            "source": "azure_ai_search",
                        },
                    )

            return SemanticRouteResult.no_match()

        except Exception as e:
            logger.error(f"Azure Semantic Router error: {e}")
            return SemanticRouteResult.no_match()

    # =========================================================================
    # Route Management Methods
    # =========================================================================

    async def add_route(self, route: SemanticRoute) -> bool:
        """Add a new route to the index."""
        documents = []

        for i, utterance in enumerate(route.utterances):
            doc = {
                "id": f"{route.name}_{i:03d}",
                "route_name": route.name,
                "category": route.category.value,
                "sub_intent": route.sub_intent,
                "utterance": utterance,
                "utterance_vector": self._get_embedding(utterance),
                "workflow_type": route.workflow_type.value,
                "risk_level": route.risk_level.value,
                "description": route.description,
                "enabled": route.enabled,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            documents.append(doc)

        result = self._search_client.upload_documents(documents)
        return all(r.succeeded for r in result)

    async def remove_route(self, route_name: str) -> bool:
        """Remove all utterances for a route."""
        # Search for all documents with this route_name
        results = self._search_client.search(
            search_text="*",
            filter=f"route_name eq '{route_name}'",
            select=["id"],
        )

        doc_ids = [{"id": r["id"]} for r in results]

        if doc_ids:
            result = self._search_client.delete_documents(doc_ids)
            return all(r.succeeded for r in result)

        return True

    async def list_routes(self) -> List[Dict[str, Any]]:
        """List all unique routes in the index."""
        results = self._search_client.search(
            search_text="*",
            facets=["route_name"],
            top=0,
        )

        routes = []
        for facet in results.get_facets()["route_name"]:
            routes.append({
                "route_name": facet["value"],
                "count": facet["count"],
            })

        return routes

    async def sync_from_yaml(self, yaml_routes: List[SemanticRoute]) -> Dict[str, int]:
        """
        Sync routes from YAML definition to Azure AI Search.

        Returns:
            Statistics of sync operation
        """
        stats = {"added": 0, "updated": 0, "errors": 0}

        for route in yaml_routes:
            try:
                # Remove existing route first
                await self.remove_route(route.name)

                # Add route with all utterances
                success = await self.add_route(route)

                if success:
                    stats["added"] += 1
                else:
                    stats["errors"] += 1

            except Exception as e:
                logger.error(f"Failed to sync route {route.name}: {e}")
                stats["errors"] += 1

        return stats
```

### 4.2 整合到 BusinessIntentRouter

```python
# 修改 router.py 的 create_router 函數

def create_router(
    pattern_rules_path: Optional[str] = None,
    pattern_rules_dict: Optional[Dict[str, Any]] = None,
    semantic_routes: Optional[List[SemanticRoute]] = None,
    llm_api_key: Optional[str] = None,
    config: Optional[RouterConfig] = None,
    use_azure_search: bool = True,  # 新增參數
) -> BusinessIntentRouter:
    """
    Factory function to create a BusinessIntentRouter.

    Args:
        ...
        use_azure_search: If True, use AzureSemanticRouter instead of in-memory router
    """
    # Create pattern matcher
    if pattern_rules_path:
        pattern_matcher = PatternMatcher(rules_path=pattern_rules_path)
    elif pattern_rules_dict:
        pattern_matcher = PatternMatcher(rules_dict=pattern_rules_dict)
    else:
        pattern_matcher = PatternMatcher(rules_dict={"rules": []})

    # Create semantic router
    if use_azure_search:
        azure_config = AzureSemanticRouterConfig.from_env()
        if azure_config.search_endpoint and azure_config.search_api_key:
            semantic_router = AzureSemanticRouter(config=azure_config)
            logger.info("Using Azure AI Search for semantic routing")
        else:
            logger.warning("Azure AI Search not configured, using in-memory router")
            semantic_router = SemanticRouter(routes=semantic_routes or [])
    else:
        semantic_router = SemanticRouter(routes=semantic_routes or [])

    # Create LLM classifier
    llm_classifier = LLMClassifier(api_key=llm_api_key)

    # Create completeness checker
    completeness_checker = CompletenessChecker()

    return BusinessIntentRouter(
        pattern_matcher=pattern_matcher,
        semantic_router=semantic_router,
        llm_classifier=llm_classifier,
        completeness_checker=completeness_checker,
        config=config or RouterConfig.from_env(),
    )
```

---

## 5. 環境配置

### 5.1 新增環境變量

```bash
# backend/.env

# ===========================================
# Azure AI Search Configuration
# ===========================================
AZURE_SEARCH_ENDPOINT=https://<search-service-name>.search.windows.net
AZURE_SEARCH_API_KEY=<your-search-api-key>
AZURE_SEARCH_INDEX_NAME=semantic-routes

# ===========================================
# Semantic Router Configuration
# ===========================================
USE_AZURE_SEARCH=true
SEMANTIC_SIMILARITY_THRESHOLD=0.85
SEMANTIC_TOP_K=3
```

### 5.2 Azure 資源需求

| 資源 | SKU 建議 | 估計成本 (USD/月) |
|------|----------|------------------|
| Azure AI Search | Basic (15 GB, 3 replicas) | ~$75 |
| Azure OpenAI (Embeddings) | 按使用量計費 | ~$5-20 |

---

## 6. API 設計

### 6.1 路由管理 API

```yaml
# Route Management API Endpoints

POST /api/v1/orchestration/routes:
  summary: Add a new semantic route
  request_body:
    route_name: string
    category: incident|request|change|query
    sub_intent: string
    utterances: string[]
    workflow_type: string
    risk_level: string
    description: string
    enabled: boolean
  response:
    success: boolean
    route_id: string

GET /api/v1/orchestration/routes:
  summary: List all semantic routes
  response:
    routes:
      - route_name: string
        category: string
        utterance_count: int
        enabled: boolean

GET /api/v1/orchestration/routes/{route_name}:
  summary: Get route details
  response:
    route_name: string
    category: string
    sub_intent: string
    utterances: string[]
    workflow_type: string
    risk_level: string
    enabled: boolean

PUT /api/v1/orchestration/routes/{route_name}:
  summary: Update a route
  request_body:
    utterances: string[]  # 可以添加新的 utterances
    enabled: boolean
  response:
    success: boolean

DELETE /api/v1/orchestration/routes/{route_name}:
  summary: Delete a route
  response:
    success: boolean

POST /api/v1/orchestration/routes/sync:
  summary: Sync routes from YAML to Azure AI Search
  response:
    added: int
    updated: int
    errors: int

POST /api/v1/orchestration/routes/search:
  summary: Test semantic search
  request_body:
    query: string
    top_k: int
  response:
    results:
      - route_name: string
        similarity: float
        category: string
```

---

## 7. 遷移計劃

### 7.1 遷移步驟

```
Phase 1: 準備 (Day 1)
──────────────────────
□ 1. 建立 Azure AI Search 資源
□ 2. 建立索引 (semantic-routes)
□ 3. 配置環境變量
□ 4. 驗證 Azure 連接

Phase 2: 開發 (Day 2-3)
──────────────────────
□ 5. 實現 AzureSemanticRouter 類
□ 6. 實現路由管理 API
□ 7. 修改 BusinessIntentRouter 整合

Phase 3: 資料遷移 (Day 3)
──────────────────────
□ 8. 將 routes.py 中的 15 條路由遷移到 Azure
□ 9. 驗證遷移結果

Phase 4: 測試 (Day 4)
──────────────────────
□ 10. 單元測試
□ 11. 整合測試
□ 12. 效能測試

Phase 5: 上線 (Day 5)
──────────────────────
□ 13. 文檔更新
□ 14. 部署到測試環境
□ 15. 監控和優化
```

### 7.2 回滾計劃

```python
# 環境變量控制回滾
USE_AZURE_SEARCH=false  # 切換回內存路由器

# 代碼自動回滾邏輯
if not azure_router.is_available:
    logger.warning("Azure AI Search unavailable, falling back to in-memory router")
    semantic_router = SemanticRouter(routes=semantic_routes)
```

---

## 8. 監控和維護

### 8.1 監控指標

| 指標 | 說明 | 告警閾值 |
|------|------|----------|
| Search Latency | 搜索響應時間 | > 100ms |
| Document Count | 索引文檔數 | < 預期數量 |
| Query Success Rate | 搜索成功率 | < 99% |
| Embedding API Latency | Embedding 響應時間 | > 500ms |

### 8.2 維護任務

| 任務 | 頻率 | 說明 |
|------|------|------|
| 索引優化 | 每週 | 重建索引以優化性能 |
| 路由審查 | 每月 | 審查低使用率路由 |
| 成本監控 | 每月 | 檢查 Azure 資源使用量 |

---

## 9. 附錄

### 9.1 現有 15 條語義路由清單

| # | Route Name | Category | Sub Intent | Utterances |
|---|------------|----------|------------|------------|
| 1 | incident_etl | incident | etl_failure | 5 |
| 2 | incident_network | incident | network_issue | 4 |
| 3 | incident_performance | incident | performance_degradation | 4 |
| 4 | incident_system_down | incident | system_down | 3 |
| 5 | request_account | request | account_creation | 4 |
| 6 | request_access | request | access_request | 4 |
| 7 | request_software | request | software_installation | 3 |
| 8 | request_password | request | password_reset | 3 |
| 9 | change_deployment | change | release_deployment | 4 |
| 10 | change_config | change | configuration_update | 3 |
| 11 | change_database | change | database_change | 3 |
| 12 | query_status | query | status_inquiry | 4 |
| 13 | query_report | query | report_request | 3 |
| 14 | query_ticket | query | ticket_status | 4 |
| 15 | query_documentation | query | documentation_request | 3 |

**總計**: 15 routes, 56 utterances

### 9.2 參考資源

- [Azure AI Search 文檔](https://learn.microsoft.com/en-us/azure/search/)
- [Azure AI Search Vector Search](https://learn.microsoft.com/en-us/azure/search/vector-search-overview)
- [Azure OpenAI Embeddings](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/embeddings)

---

**文件結束**
