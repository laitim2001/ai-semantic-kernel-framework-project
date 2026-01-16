# IPA Platform 三層路由架構重構規劃

> **版本**: 1.0 | **日期**: 2026-01-15 | **狀態**: 規劃中

---

## 一、執行摘要

### 1.1 專案目標

將 IPA Platform 的編排層重構為業界最佳實踐的**三層路由架構**，實現：

| 指標 | 當前估計 | 目標 | 
|------|---------|------|
| 意圖識別準確率 | ~70% | >95% |
| P50 路由延遲 | 未知 | <100ms |
| P95 路由延遲 | 未知 | <500ms |
| 自動處理率 | 未知 | >80% |

### 1.2 三層架構概覽

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        三層路由架構                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   Layer 1: Pattern Matcher (模式匹配)                                   │
│   ════════════════════════════════════                                  │
│   • 方法: 正則表達式 + 關鍵字匹配                                       │
│   • 覆蓋: 70-80% 流量                                                   │
│   • 延遲: ~1ms                                                          │
│   • 成本: $0                                                            │
│                                                                          │
│   Layer 2: Semantic Router (語義路由)                                   │
│   ════════════════════════════════════                                  │
│   • 方法: 向量嵌入相似度匹配                                            │
│   • 覆蓋: 15-25% 流量                                                   │
│   • 延遲: 10-100ms                                                      │
│   • 成本: 嵌入 API 費用                                                 │
│                                                                          │
│   Layer 3: LLM Classifier (LLM 分類)                                    │
│   ════════════════════════════════════                                  │
│   • 方法: Claude Haiku 結構化分類                                       │
│   • 覆蓋: 5-10% 流量                                                    │
│   • 延遲: 500-2000ms                                                    │
│   • 成本: LLM API 費用                                                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 二、整體架構設計

### 2.1 系統架構圖

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           IPA Platform 編排層架構                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   入口                                                                       │
│   ════                                                                       │
│   REST API ──┐                                                              │
│   Webhook ───┼──▶ Request Normalizer ──▶ Intent Router                     │
│   Slack ─────┤                              │                               │
│   Teams ─────┘                              │                               │
│                                             ▼                               │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                      Intent Router (三層路由)                        │  │
│   │                                                                      │  │
│   │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │  │
│   │  │ Pattern Matcher  │─▶│ Semantic Router  │─▶│  LLM Classifier  │  │  │
│   │  │    (Layer 1)     │  │    (Layer 2)     │  │    (Layer 3)     │  │  │
│   │  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  │  │
│   │           │ 匹配                │ 匹配                │ 分類       │  │
│   │           └─────────────────────┴─────────────────────┘            │  │
│   │                                 │                                   │  │
│   └─────────────────────────────────┼───────────────────────────────────┘  │
│                                     ▼                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                       Risk Assessor (風險評估)                       │  │
│   │  • 操作類型 • 影響範圍 • 可逆性 • 合規檢查                          │  │
│   └─────────────────────────────────┬───────────────────────────────────┘  │
│                                     │                                       │
│                    ┌────────────────┴────────────────┐                     │
│                    │                                 │                     │
│                    ▼                                 ▼                     │
│   ┌──────────────────────────┐    ┌──────────────────────────────────┐    │
│   │ 自動處理 (Low Risk)      │    │ HITL Controller (Medium+ Risk)   │    │
│   │                          │    │ • 創建審批請求                    │    │
│   │                          │    │ • 發送通知 (Teams/Slack)         │    │
│   │                          │    │ • 等待決策                        │    │
│   └────────────┬─────────────┘    └────────────────┬─────────────────┘    │
│                │                                    │ (審批後)             │
│                └────────────────────┬───────────────┘                     │
│                                     ▼                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                    Workflow Selector (工作流選擇)                    │  │
│   │  Sequential │ Magentic │ GroupChat │ Handoff                        │  │
│   └─────────────────────────────────┬───────────────────────────────────┘  │
│                                     ▼                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                     Task Dispatcher (任務分發)                       │  │
│   │                                                                      │  │
│   │   ┌─────────────┐   ┌──────────────┐   ┌─────────────┐              │  │
│   │   │ MAF Workers │   │Claude Workers│   │ N8N Workers │              │  │
│   │   └─────────────┘   └──────────────┘   └─────────────┘              │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 技術選型

| 組件 | 選型 | 理由 |
|------|------|------|
| **Pattern Matcher** | Python `re` + 自定義規則引擎 | 輕量、可控、易維護 |
| **Semantic Router** | Aurelio Semantic Router | 專為此場景設計、比 LLM 快 50x |
| **Embedding** | Azure OpenAI text-embedding-3-small | 已有訂閱、成本效益 |
| **LLM Classifier** | Claude Haiku | 性價比高、結構化輸出穩定 |
| **State Store** | Redis | 低延遲、已有基礎設施 |
| **Audit Store** | PostgreSQL | 事務支持、持久化 |
| **Tracing** | OpenTelemetry + Jaeger | 開源、標準化 |

---

## 三、核心組件設計

### 3.1 Layer 1: Pattern Matcher

#### 規則結構

```python
@dataclass
class PatternRule:
    id: str                    # 規則 ID，如 "INC-001"
    name: str                  # 規則名稱
    pattern: str               # 正則表達式
    intent: str                # 意圖類別: incident|request|change|problem|query
    sub_intent: str            # 子意圖
    workflow: str              # 推薦工作流: sequential|magentic|group_chat|handoff
    priority: int              # 優先級 (1-100)
    confidence: float          # 信心度 (0.0-1.0)
    tags: List[str]            # 標籤
    enabled: bool = True       # 是否啟用
```

#### 預定義規則範例

| ID | 名稱 | Pattern | 意圖 | 子意圖 | 工作流 | 優先級 |
|-----|------|---------|------|--------|--------|--------|
| INC-001 | ETL Failure | `(?i)(etl\|pipeline).*?(fail\|error\|down)` | incident | etl_failure | magentic | 90 |
| INC-002 | Server Down | `(?i)(server\|service).*?(down\|unavailable)` | incident | service_outage | magentic | 95 |
| REQ-001 | Password Reset | `(?i)(password\|pwd).*?(reset\|forgot)` | request | password_reset | sequential | 80 |
| CHG-001 | Deployment | `(?i)(deploy\|release).*?(new\|update)` | change | deployment | magentic | 85 |
| QRY-001 | Status Query | `(?i)(status\|state).*?(check\|what)` | query | status_check | sequential | 70 |

#### 接口設計

```python
class PatternMatcher:
    def __init__(self, rules: List[PatternRule]): ...
    
    def match(self, text: str) -> MatchResult:
        """嘗試匹配，返回最高優先級的匹配結果"""
        
    def add_rule(self, rule: PatternRule) -> bool:
        """動態添加規則"""
        
    def get_stats(self) -> dict:
        """獲取匹配統計"""
```

### 3.2 Layer 2: Semantic Router

#### 路由定義

```python
@dataclass
class SemanticRoute:
    name: str                  # 路由名稱
    description: str           # 描述
    utterances: List[str]      # 示例話語 (用於生成嵌入)
    intent_category: str       # 意圖類別
    sub_intent: str            # 子意圖
    workflow_type: str         # 工作流類型
```

#### 預定義路由範例

```python
SEMANTIC_ROUTES = [
    SemanticRoute(
        name="incident_handler",
        description="處理 IT 事件和故障",
        utterances=[
            "系統出問題了", "服務無法使用", "出現錯誤訊息",
            "Something is broken", "Service is down"
        ],
        intent_category="incident",
        sub_intent="general_incident",
        workflow_type="magentic"
    ),
    SemanticRoute(
        name="request_handler",
        description="處理 IT 服務請求",
        utterances=[
            "我需要申請帳號", "可以幫我安裝軟體嗎", "申請 VPN 存取",
            "I need a new account", "Please install software"
        ],
        intent_category="request",
        sub_intent="service_request",
        workflow_type="sequential"
    ),
    # ... 更多路由
]
```

#### 接口設計

```python
class SemanticRouter:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        routes: List[SemanticRoute],
        similarity_threshold: float = 0.85
    ): ...
    
    async def initialize(self) -> None:
        """初始化路由嵌入索引"""
        
    async def route(self, text: str) -> SemanticMatchResult:
        """嘗試語義路由"""
```

### 3.3 Layer 3: LLM Classifier

#### 系統提示詞

```
你是 Ricoh APAC IT 服務的意圖分類專家。分析用戶請求並提供結構化分類。

## 意圖類別
1. incident - IT 事件和故障
2. request - IT 服務請求
3. change - 變更請求
4. problem - 問題調查
5. query - 查詢請求

## 輸出格式 (JSON)
{
    "intent_category": "string",
    "sub_intent": "string",
    "workflow_type": "string",
    "confidence": 0.0-1.0,
    "risk_level": "low|medium|high|critical",
    "requires_approval": true/false,
    "reasoning": "簡短說明"
}
```

#### 接口設計

```python
class LLMClassifier:
    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-haiku-20241022"
    ): ...
    
    async def classify(
        self, 
        text: str, 
        context: Dict = None
    ) -> LLMClassificationResult:
        """使用 LLM 進行意圖分類"""
```

### 3.4 Intent Router (三層協調器)

```python
class IntentRouter:
    """
    三層意圖路由器 - 協調三個層級實現高效且準確的意圖識別
    
    路由策略：
    1. 優先使用 Pattern Matcher（快速路徑）
    2. 無匹配時使用 Semantic Router（語義匹配）
    3. 低信心度時使用 LLM Classifier（精確分類）
    """
    
    def __init__(
        self,
        pattern_matcher: PatternMatcher,
        semantic_router: SemanticRouter,
        llm_classifier: LLMClassifier,
        semantic_confidence_threshold: float = 0.85
    ): ...
    
    async def route(self, text: str, context: Dict = None) -> RoutingDecision:
        # Layer 1: Pattern Matcher
        pattern_result = self.pattern_matcher.match(text)
        if pattern_result.matched:
            return self._create_decision(pattern_result, layer="pattern_matcher")
        
        # Layer 2: Semantic Router
        semantic_result = await self.semantic_router.route(text)
        if semantic_result.matched and semantic_result.confidence >= threshold:
            return self._create_decision(semantic_result, layer="semantic_router")
        
        # Layer 3: LLM Classifier
        llm_result = await self.llm_classifier.classify(text, context)
        if llm_result.success:
            return self._create_decision(llm_result, layer="llm_classifier")
        
        # Fallback: 人工處理
        return self._create_fallback_decision()
```

---

## 四、風險評估與 HITL

### 4.1 風險分類框架

| 風險等級 | 分數範圍 | 操作類型 | 審批要求 |
|----------|----------|----------|----------|
| **Low** | 0.0-0.3 | 唯讀、查詢 | 無需審批 |
| **Medium** | 0.3-0.6 | 創建、標準修改 | 自我確認 |
| **High** | 0.6-0.8 | 生產配置、部署 | 經理審批 |
| **Critical** | 0.8-1.0 | 刪除、安全相關 | 高管審批 |

### 4.2 風險評估因素

```python
class RiskAssessor:
    def assess(self, intent: str, sub_intent: str, context: Dict) -> RiskAssessment:
        # 風險因素權重
        weights = {
            "action_type": 0.25,      # 讀/寫/刪/執行
            "impact_scope": 0.25,     # 單用戶/單系統/多系統/全域
            "reversibility": 0.15,    # 可逆/不可逆
            "production": 0.15,       # 是否影響生產
            "pii": 0.10,              # 是否涉及 PII
            "financial": 0.10         # 是否涉及財務
        }
        
        risk_score = self._calculate_score(...)
        return RiskAssessment(
            risk_level=self._score_to_level(risk_score),
            requires_approval=risk_score > 0.3,
            approval_level=self._determine_approval_level(risk_score)
        )
```

### 4.3 HITL 審批流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        HITL 審批流程                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   1. 創建審批請求                                                       │
│      ┌─────────────────────────────────────────────────────────┐        │
│      │ ApprovalRequest                                         │        │
│      │ • request_id                                            │        │
│      │ • original_request                                      │        │
│      │ • risk_assessment                                       │        │
│      │ • approval_level: self | manager | security | executive │        │
│      │ • expires_at: 24小時後                                  │        │
│      └─────────────────────────────────────────────────────────┘        │
│                            │                                             │
│   2. 發送通知              ▼                                             │
│      ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│      │    Teams     │  │    Slack     │  │    Email     │               │
│      │ Adaptive Card│  │  Block Kit   │  │              │               │
│      └──────┬───────┘  └──────┬───────┘  └──────┬───────┘               │
│             └─────────────────┴─────────────────┘                        │
│                            │                                             │
│   3. 審批者決策            ▼                                             │
│      ┌─────────────────────────────────────────────────────────┐        │
│      │ ApprovalAction                                          │        │
│      │ • APPROVE - 批准執行                                    │        │
│      │ • REJECT  - 拒絕執行                                    │        │
│      │ • EDIT    - 修改後執行                                  │        │
│      │ • ESCALATE - 升級到更高級別                             │        │
│      └─────────────────────────────────────────────────────────┘        │
│                            │                                             │
│   4. 執行或終止            ▼                                             │
│      ┌────────────┐    ┌────────────┐                                   │
│      │  繼續執行  │    │  終止流程  │                                   │
│      │  Workflow  │    │  通知用戶  │                                   │
│      └────────────┘    └────────────┘                                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 五、數據模型

### 5.1 核心數據結構

```python
@dataclass
class RoutingDecision:
    """最終路由決策"""
    request_id: str
    original_text: str
    timestamp: str
    
    # 分類結果
    intent_category: str       # incident|request|change|problem|query
    sub_intent: str
    workflow_type: str         # sequential|magentic|group_chat|handoff
    confidence: float
    
    # 風險評估
    risk_level: str            # low|medium|high|critical
    requires_approval: bool
    
    # 路由信息
    routed_to: str             # Agent 或 Workflow 名稱
    layer_used: str            # pattern_matcher|semantic_router|llm_classifier
    
    # 處理追蹤
    total_processing_time_ms: float
    metadata: Dict[str, Any]


@dataclass
class RequestContext:
    """請求完整上下文 (狀態管理)"""
    request_id: str
    state: str                 # received|routing|risk_assessing|awaiting_approval|...
    
    # 請求內容
    original_text: str
    source_channel: str        # api|webhook|slack|teams
    user_id: str
    
    # 路由結果
    intent_category: str
    sub_intent: str
    workflow_type: str
    
    # 風險評估
    risk_level: str
    requires_approval: bool
    
    # 審批信息
    approval_id: Optional[str]
    approval_status: str
    
    # 執行信息
    assigned_worker: str
    workflow_instance_id: str
    
    # 結果
    result: Optional[Dict]
    error: Optional[str]
```

---

## 六、API 設計

### 6.1 核心端點

| 方法 | 路徑 | 描述 |
|------|------|------|
| POST | `/api/v1/requests` | 提交新請求 |
| GET | `/api/v1/requests/{id}` | 獲取請求狀態 |
| POST | `/api/v1/requests/{id}/cancel` | 取消請求 |
| GET | `/api/v1/approvals` | 獲取待審批列表 |
| POST | `/api/v1/approvals/{id}/decision` | 提交審批決策 |
| POST | `/api/v1/routing/test` | 測試路由 (不執行) |
| GET | `/api/v1/stats` | 獲取統計信息 |

### 6.2 請求/響應範例

**提交請求**
```http
POST /api/v1/requests
Content-Type: application/json

{
    "text": "ETL Pipeline 失敗了，日報表無法生成",
    "context": {
        "source": "servicenow",
        "incident_id": "INC0012345"
    },
    "priority": "high"
}
```

**響應**
```json
{
    "requestId": "req_20260115123456",
    "status": "accepted",
    "message": "Request accepted for processing",
    "estimatedProcessingTime": "< 5 seconds"
}
```

---

## 七、實施計劃

### 7.1 階段概覽

```
Phase 0: 準備 (1週)      ──▶ 環境設置、依賴安裝
Phase 1: 核心路由 (2週)  ──▶ Pattern Matcher + Semantic Router + LLM Classifier
Phase 2: 風險與審批 (2週) ──▶ Risk Assessor + HITL Controller
Phase 3: 工作流整合 (2週) ──▶ MAF/Claude/N8N Workers 整合
Phase 4: API (1週)       ──▶ REST API + Webhook
Phase 5: 測試優化 (2週)   ──▶ 測試 + 規則調優
Phase 6: 上線 (1週)      ──▶ 文檔 + 培訓 + 灰度發布

總計: 約 11 週
```

### 7.2 Phase 1 詳細任務

| 週次 | 任務 | 產出 | 完成標準 |
|------|------|------|----------|
| W1 | 數據模型定義 | `models.py` | 所有 dataclass 完成 |
| W1 | Pattern Matcher | `pattern_matcher/` | 30+ 規則，測試通過 |
| W2 | Embedding 接口 | `embedding.py` | Azure OpenAI 連接 |
| W2 | Semantic Router | `semantic_router/` | 10+ 路由，測試通過 |
| W2 | LLM Classifier | `llm_classifier/` | Claude 整合完成 |
| W2 | Intent Router | `intent_router.py` | 三層路由整合 |

### 7.3 關鍵里程碑

| 里程碑 | 目標日期 | 驗收標準 |
|--------|----------|----------|
| M1: 三層路由可運行 | Phase 1 結束 | 測試用例通過率 >90% |
| M2: HITL 流程完整 | Phase 2 結束 | 可在 Teams 審批 |
| M3: 工作流整合完成 | Phase 3 結束 | E2E 流程驗證通過 |
| M4: API 上線 | Phase 4 結束 | Swagger 文檔可訪問 |
| M5: 準確率達標 | Phase 5 結束 | 意圖識別 >95% |
| M6: 正式上線 | Phase 6 結束 | 灰度發布完成 |

---

## 八、代碼結構

```
ipa-platform/
├── src/
│   ├── api/                          # API 層
│   │   ├── routes/                   # 路由定義
│   │   ├── middleware/               # 中間件
│   │   └── webhooks/                 # Webhook 處理
│   │
│   ├── orchestration/                # 編排層核心 ⭐
│   │   ├── pattern_matcher/          # Layer 1
│   │   │   ├── matcher.py
│   │   │   └── rules.py
│   │   ├── semantic_router/          # Layer 2
│   │   │   ├── router.py
│   │   │   └── routes.py
│   │   ├── llm_classifier/           # Layer 3
│   │   │   ├── classifier.py
│   │   │   └── prompts.py
│   │   ├── intent_router.py          # 三層協調器
│   │   ├── risk_assessor.py          # 風險評估
│   │   ├── hitl_controller.py        # HITL 控制
│   │   ├── workflow_selector.py      # 工作流選擇
│   │   └── state_manager.py          # 狀態管理
│   │
│   ├── workers/                      # 工作者層
│   │   ├── maf/                      # MAF 工作者
│   │   ├── claude/                   # Claude 工作者
│   │   └── n8n/                      # N8N 工作者
│   │
│   ├── notifiers/                    # 通知器
│   │   ├── teams.py
│   │   └── slack.py
│   │
│   └── utils/                        # 工具
│       ├── config.py
│       ├── logging.py
│       └── tracing.py
│
├── tests/
│   ├── unit/                         # 單元測試
│   ├── integration/                  # 整合測試
│   └── performance/                  # 性能測試
│
├── config/                           # 配置文件
│   ├── rules/                        # 規則配置
│   └── routes/                       # 路由配置
│
└── docs/                             # 文檔
    ├── architecture/
    └── api/
```

---

## 九、監控指標

### 9.1 關鍵指標

| 指標 | 類型 | 告警閾值 |
|------|------|----------|
| `ipa_routing_latency_p95` | Histogram | > 500ms |
| `ipa_layer_hit_rate` | Gauge | Layer 3 > 20% |
| `ipa_approval_pending` | Gauge | > 50 |
| `ipa_error_rate` | Counter | > 5% |

### 9.2 Dashboard 視圖

- **Request Rate** - 按意圖類別分組
- **Routing Latency** - P50/P95/P99
- **Layer Distribution** - 三層命中比例
- **Approval Queue** - 待審批數量
- **Error Rate** - 錯誤率趨勢

---

## 十、風險與緩解

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| LLM API 延遲 | 用戶體驗 | 超時 + 緩存 + fallback |
| 規則覆蓋不足 | 準確率 | 監控 fallback 率 + 持續更新 |
| 審批瓶頸 | 請求積壓 | SLA + 自動升級 |
| 語義漂移 | 準確率下降 | 定期重訓練 + A/B 測試 |

---

## 十一、下一步行動

1. **立即** - 確認技術選型和環境準備
2. **本週** - 建立開發環境和 CI/CD
3. **下週** - 開始 Phase 1: Pattern Matcher 開發
4. **持續** - 收集真實 IT 事件樣本用於規則設計

---

**文檔版本**: 1.0  
**最後更新**: 2026-01-15  
**作者**: Chris Lai / Ricoh APAC Data & AI Team