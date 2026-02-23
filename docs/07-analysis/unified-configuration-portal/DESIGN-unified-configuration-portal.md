# IPA Platform 統一配置管理系統 (Unified Configuration Portal)

> **文件版本**: 1.0
> **創建日期**: 2026-01-25
> **狀態**: 設計階段

## 概述

設計並實現一個統一的配置管理系統，讓用戶可以通過 Portal 介面管理 IPA Platform 所有組件的配置。

## 需求來源

基於 MAF-Claude-Hybrid-Architecture-V2 架構圖，用戶需要管理：
- Input Gateway 配置（來源啟用/停用、webhook、schema）
- 觸發器配置（Event Trigger、User Trigger）
- Coordinator Agent 配置（意圖分類閾值、風險參數、HITL 超時）
- Claude Worker Pool 配置（Worker 數量、類型、timeout）
- MCP 工具層配置（MCP Server 啟用/停用、連接參數）
- 可觀測性配置（日誌級別、Metrics、Audit 保留期）

---

## 現有配置狀態分析

| 配置類別 | 當前方式 | 持久化 | 動態更新 |
|---------|---------|--------|---------|
| 應用級 | `.env` + Pydantic Settings | 文件 | ❌ 重啟 |
| Gateway | 環境變數 + dataclass | 文件 | ❌ 重啟 |
| Intent Router | 環境變數 + API | 記憶體 | ✅ 部分 |
| Risk Policies | 硬編碼 + 規則文件 | 代碼/文件 | ⚠️ 規則可配 |
| HITL | 構造函數參數 | 記憶體 | ❌ 初始化時 |
| MCP | YAML + 環境變數 | 文件 | ⚠️ 程式化 |
| 前端 Settings | 佔位符 | - | - |

**關鍵缺口**：
- 無統一配置資料庫模型
- 無前端配置管理介面
- 無熱更新機制

---

## 設計方案

### 系統架構圖

```
┌─────────────────────────────────────────────────────────────────┐
│                Frontend Configuration Portal                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────────┐│
│  │ Gateway  │ │ Router   │ │ Risk     │ │ Observability        ││
│  │ Config   │ │ Config   │ │ Config   │ │ Config               ││
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Configuration REST API                        │
│  /api/v1/config/{category}/{key}                                │
│  GET, PUT, PATCH, DELETE + /versions + /audit                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  ConfigurationService (Domain)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Validation   │  │ Versioning   │  │ Hot Reload Publisher │  │
│  │ Engine       │  │ Manager      │  │ (Redis PubSub)       │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ ConfigRepository │ │ Redis Cache      │ │ Component        │
│ (PostgreSQL)     │ │ (Hot Config)     │ │ Subscribers      │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

---

## 一、資料庫模型設計

### 1.1 Configuration 主表

```python
# backend/src/infrastructure/database/models/configuration.py

class Configuration(Base, TimestampMixin):
    """動態配置存儲模型"""

    __tablename__ = "configurations"

    # 主鍵
    id: Mapped[uuid4] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # 配置識別
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # 配置值
    value: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    value_type: Mapped[str] = mapped_column(String(50), nullable=False, default="string")
    # value_type: 'string', 'number', 'boolean', 'object', 'array'

    # 文檔
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_value: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # 安全
    is_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # 狀態
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # 版本控制
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # 驗證 Schema
    schema_def: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # 關聯
    versions = relationship("ConfigurationVersion", back_populates="configuration")
    audit_logs = relationship("ConfigurationAudit", back_populates="configuration")

    __table_args__ = (
        UniqueConstraint("category", "key", name="uq_config_category_key"),
    )
```

### 1.2 ConfigurationVersion 版本表

```python
class ConfigurationVersion(Base, TimestampMixin):
    """配置版本歷史"""

    __tablename__ = "configuration_versions"

    id: Mapped[uuid4] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    configuration_id: Mapped[uuid4] = mapped_column(UUID(as_uuid=True), ForeignKey("configurations.id"))
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    changed_by: Mapped[str] = mapped_column(String(255), nullable=False)
    change_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    change_type: Mapped[str] = mapped_column(String(50), nullable=False, default="update")
    # change_type: 'create', 'update', 'rollback', 'delete'

    configuration = relationship("Configuration", back_populates="versions")
```

### 1.3 ConfigurationAudit 審計表

```python
class ConfigurationAudit(Base):
    """配置變更審計日誌"""

    __tablename__ = "configuration_audits"

    id: Mapped[uuid4] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    configuration_id: Mapped[Optional[uuid4]] = mapped_column(UUID(as_uuid=True), ForeignKey("configurations.id"))
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    # action: 'read', 'create', 'update', 'delete', 'rollback'
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_ip: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    old_value: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    configuration = relationship("Configuration", back_populates="audit_logs")
```

---

## 二、配置分類體系

### 2.1 配置分類枚舉

```python
# backend/src/domain/configuration/categories.py

class ConfigCategory(str, Enum):
    """配置分類"""

    # Phase 28 Orchestration
    GATEWAY = "gateway"           # Input Gateway 配置
    ROUTER = "router"             # Intent Router 配置
    RISK = "risk"                 # Risk Assessor 配置
    HITL = "hitl"                 # HITL Controller 配置
    DIALOG = "dialog"             # Guided Dialog 配置

    # Hybrid Orchestration
    ORCHESTRATOR = "orchestrator" # Hybrid Orchestrator 配置
    FRAMEWORK = "framework"       # Framework 選擇配置

    # MCP Tools
    MCP = "mcp"                   # MCP Server 配置

    # Claude SDK
    CLAUDE_SDK = "claude_sdk"     # Claude SDK 配置

    # Observability
    OBSERVABILITY = "observability"  # 日誌、Metrics、Tracing

    # System
    SYSTEM = "system"             # 系統級配置
```

### 2.2 各分類配置項目

#### Gateway 配置
| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enable_schema_validation` | boolean | true | 啟用 JSON schema 驗證 |
| `enable_metrics` | boolean | true | 啟用 Gateway metrics |
| `default_source_type` | string | "user" | 預設來源類型 |
| `max_content_length` | number | 0 | 最大內容長度 (0=無限) |
| `source_headers` | object | {...} | 來源識別 headers |

#### Router 配置
| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `pattern_threshold` | number | 0.90 | Pattern 匹配閾值 |
| `semantic_threshold` | number | 0.85 | Semantic 相似度閾值 |
| `enable_llm_fallback` | boolean | true | 啟用 LLM fallback |
| `enable_completeness` | boolean | true | 啟用完整度檢查 |

#### Risk 配置
| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `thresholds` | object | {...} | 風險等級閾值 |
| `factor_weights` | object | {...} | 風險因素權重 |
| `auto_approve_settings` | object | {...} | 自動審批設定 |
| `enable_pattern_detection` | boolean | true | 啟用行為模式檢測 |

#### HITL 配置
| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `default_timeout_minutes` | number | 30 | 預設審批超時 |
| `notification_channels` | object | {...} | 通知渠道配置 |
| `escalation_rules` | array | [...] | 升級規則 |

#### MCP 配置
| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `servers` | array | [...] | MCP server 列表 |
| `default_timeout` | number | 30 | 預設超時 (秒) |

#### Claude SDK 配置
| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `model` | string | "claude-sonnet-4-..." | 預設模型 |
| `max_tokens` | number | 4096 | 最大 tokens |
| `timeout` | number | 300 | 請求超時 (秒) |
| `tools_enabled` | array | [...] | 啟用的工具列表 |
| `denied_commands` | array | [...] | 禁止的 bash 命令 |

#### Observability 配置
| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `log_level` | string | "INFO" | 日誌級別 |
| `otel_enabled` | boolean | false | 啟用 OpenTelemetry |
| `metrics_enabled` | boolean | true | 啟用 Prometheus metrics |
| `audit_retention_days` | number | 90 | 審計日誌保留天數 |

---

## 三、API 設計

### 3.1 REST API Endpoints

| Method | Endpoint | 功能 |
|--------|----------|------|
| GET | `/api/v1/config/` | 列出所有配置 |
| GET | `/api/v1/config/categories` | 列出所有分類 |
| GET | `/api/v1/config/{category}` | 獲取分類下所有配置 |
| GET | `/api/v1/config/{category}/{key}` | 獲取單個配置 |
| POST | `/api/v1/config/{category}/{key}` | 創建配置 |
| PUT | `/api/v1/config/{category}/{key}` | 更新配置 |
| DELETE | `/api/v1/config/{category}/{key}` | 停用配置 (軟刪除) |
| GET | `/api/v1/config/{category}/{key}/versions` | 獲取版本歷史 |
| POST | `/api/v1/config/{category}/{key}/rollback/{version}` | 回滾到指定版本 |
| POST | `/api/v1/config/{category}/{key}/validate` | 驗證配置值 |
| GET | `/api/v1/config/{category}/{key}/audit` | 獲取審計日誌 |
| GET | `/api/v1/config/audit` | 獲取全局審計日誌 |
| POST | `/api/v1/config/bulk/import` | 批量導入 |
| GET | `/api/v1/config/bulk/export` | 批量導出 |

### 3.2 Request/Response Schemas

```python
# 創建配置
class ConfigurationCreate(BaseModel):
    value: Any
    value_type: str = "string"
    description: Optional[str] = None
    default_value: Optional[Any] = None
    schema_def: Optional[Dict[str, Any]] = None
    is_sensitive: bool = False
    change_reason: Optional[str] = None

# 更新配置
class ConfigurationUpdate(BaseModel):
    value: Any
    change_reason: Optional[str] = None

# 配置響應
class ConfigurationResponse(BaseModel):
    id: UUID
    category: str
    key: str
    value: Any  # 敏感值會被 mask
    value_type: str
    description: Optional[str]
    is_sensitive: bool
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime
```

---

## 四、熱更新機制

### 4.1 Redis PubSub 發布訂閱

```python
# backend/src/domain/configuration/hot_reload.py

class ConfigurationPublisher:
    """配置變更發布者"""

    CHANNEL_PREFIX = "config:changes:"

    async def publish_change(self, event: ConfigChangeEvent) -> int:
        """
        發布配置變更事件到多個 channel:
        - config:changes:{category}
        - config:changes:{category}:{key}
        - config:changes:*
        """
        ...


class ConfigurationSubscriber:
    """配置變更訂閱者"""

    def subscribe(self, category: str, key: str = None, callback: Callable = None):
        """訂閱特定配置的變更"""
        ...

    def subscribe_all(self, callback: Callable):
        """訂閱所有配置變更"""
        ...

    async def start(self):
        """開始監聽"""
        ...

    async def stop(self):
        """停止監聽"""
        ...
```

### 4.2 動態配置加載器

```python
# backend/src/domain/configuration/loader.py

class DynamicConfigLoader(Generic[T]):
    """
    泛型動態配置加載器

    提供類型安全的配置訪問，支持熱更新

    Example:
        loader = DynamicConfigLoader[RouterConfig](
            service=config_service,
            subscriber=subscriber,
            category="router",
            config_class=RouterConfig,
        )
        await loader.start()
        config = loader.get_config()
    """

    async def start(self) -> None:
        """加載初始配置，訂閱變更"""
        ...

    def get_config(self) -> T:
        """獲取當前配置"""
        ...

    def get_value(self, key: str, default: Any = None) -> Any:
        """獲取單個配置值"""
        ...
```

---

## 五、組件整合方式

### 5.1 RouterConfig 整合示例

```python
# backend/src/integrations/orchestration/intent_router/router.py

@dataclass
class RouterConfig:
    pattern_threshold: float = 0.90
    semantic_threshold: float = 0.85
    enable_llm_fallback: bool = True
    enable_completeness: bool = True
    track_latency: bool = True

    @classmethod
    def from_env(cls) -> "RouterConfig":
        """從環境變數創建 (備用方式)"""
        ...

    @classmethod
    async def from_dynamic_config(cls, config_service) -> "RouterConfig":
        """從動態配置服務創建"""
        configs, _ = await config_service.list_configurations(
            category="router",
            active_only=True,
        )
        config_dict = {c.key: c.value.get("value", c.value) for c in configs}
        return cls(**config_dict)


class BusinessIntentRouter:
    def __init__(
        self,
        ...,
        config: Optional[RouterConfig] = None,
        config_loader: Optional[DynamicConfigLoader] = None,  # 新增
    ):
        self._static_config = config or RouterConfig.from_env()
        self._config_loader = config_loader

    @property
    def config(self) -> RouterConfig:
        """獲取當前配置 (支持熱更新)"""
        if self._config_loader:
            return self._config_loader.get_config()
        return self._static_config
```

### 5.2 應用啟動整合

```python
# backend/src/main.py

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化配置服務
    config_service = ConfigurationService(db_session_factory, redis_client)
    config_subscriber = ConfigurationSubscriber(redis_client)

    # 註冊組件配置加載器
    router_loader = DynamicConfigLoader[RouterConfig](
        service=config_service,
        subscriber=config_subscriber,
        category="router",
        config_class=RouterConfig,
    )
    await router_loader.start()

    # 存儲到 app.state
    app.state.config_service = config_service
    app.state.router_config_loader = router_loader

    await config_subscriber.start()

    yield

    await config_subscriber.stop()
```

---

## 六、前端頁面設計

### 6.1 頁面結構

```
frontend/src/pages/configuration/
├── ConfigurationPage.tsx           # 主頁面
├── components/
│   ├── CategoryNav.tsx             # 分類導航
│   ├── ConfigTable.tsx             # 配置列表
│   ├── ConfigForm.tsx              # 配置表單
│   ├── ConfigVersionHistory.tsx    # 版本歷史
│   └── ConfigAuditLog.tsx          # 審計日誌
```

### 6.2 頁面佈局

```
┌──────────────────────────────────────────────────────────────────┐
│ Configuration Portal                                              │
├─────────────┬────────────────────────────────────────────────────┤
│             │                                                     │
│  Categories │  [Settings] [Version History] [Audit Log]          │
│  ─────────  │  ─────────────────────────────────────────────────  │
│  □ Gateway  │  ┌─────────────────────┐ ┌─────────────────────┐   │
│  ■ Router   │  │ Configuration Items │ │ Edit Configuration  │   │
│  □ Risk     │  │ ──────────────────  │ │ ──────────────────  │   │
│  □ HITL     │  │ pattern_threshold   │ │ Key: pattern_thres..│   │
│  □ MCP      │  │ semantic_threshold  │ │ Type: number        │   │
│  □ Claude   │  │ enable_llm_fallback │ │ Version: v3         │   │
│  □ Observ.. │  │                     │ │                     │   │
│             │  │                     │ │ Value: [0.90    ]   │   │
│             │  │                     │ │                     │   │
│             │  │                     │ │ Reason: [........]  │   │
│             │  │                     │ │                     │   │
│             │  │                     │ │ [Cancel] [Save]     │   │
│             │  └─────────────────────┘ └─────────────────────┘   │
└─────────────┴────────────────────────────────────────────────────┘
```

---

## 七、實施計劃

### 7.1 實施階段

| 階段 | 內容 | 預估時間 |
|------|------|----------|
| Phase 1 | 資料庫模型和遷移 | 1-2 天 |
| Phase 2 | ConfigurationService 核心服務 | 2-3 天 |
| Phase 3 | REST API 實現 | 2 天 |
| Phase 4 | 熱更新機制 (Redis PubSub) | 1-2 天 |
| Phase 5 | 現有組件整合 | 2-3 天 |
| Phase 6 | 前端 Portal 開發 | 3-4 天 |
| Phase 7 | 測試和文檔 | 2 天 |
| **總計** | | **13-18 天** |

### 7.2 優先級

- **P0 必要**：資料庫模型、核心 API、基本前端
- **P1 重要**：熱更新、版本控制、審計日誌
- **P2 增強**：批量導入導出、進階驗證、前端美化

---

## 八、關鍵文件清單

### 8.1 新建文件（後端）

| 文件路徑 | 用途 |
|---------|------|
| `backend/src/infrastructure/database/models/configuration.py` | 資料庫模型 |
| `backend/src/domain/configuration/__init__.py` | 模組初始化 |
| `backend/src/domain/configuration/service.py` | 核心服務 |
| `backend/src/domain/configuration/repository.py` | 資料存取 |
| `backend/src/domain/configuration/categories.py` | 配置分類定義 |
| `backend/src/domain/configuration/hot_reload.py` | 熱更新機制 |
| `backend/src/domain/configuration/loader.py` | 動態加載器 |
| `backend/src/api/v1/configuration/__init__.py` | API 模組 |
| `backend/src/api/v1/configuration/routes.py` | API 路由 |
| `backend/src/api/v1/configuration/schemas.py` | API Schema |

### 8.2 新建文件（前端）

| 文件路徑 | 用途 |
|---------|------|
| `frontend/src/pages/configuration/ConfigurationPage.tsx` | 主頁面 |
| `frontend/src/pages/configuration/components/CategoryNav.tsx` | 分類導航 |
| `frontend/src/pages/configuration/components/ConfigTable.tsx` | 配置列表 |
| `frontend/src/pages/configuration/components/ConfigForm.tsx` | 配置表單 |
| `frontend/src/pages/configuration/components/ConfigVersionHistory.tsx` | 版本歷史 |
| `frontend/src/pages/configuration/components/ConfigAuditLog.tsx` | 審計日誌 |
| `frontend/src/api/endpoints/configuration.ts` | API 客戶端 |
| `frontend/src/types/configuration.ts` | TypeScript 類型 |

### 8.3 修改文件

| 文件路徑 | 修改內容 |
|---------|---------|
| `backend/src/main.py` | 初始化配置服務和訂閱者 |
| `backend/src/api/v1/__init__.py` | 註冊配置路由 |
| `backend/src/integrations/orchestration/intent_router/router.py` | 支持動態配置 |
| `frontend/src/App.tsx` | 添加配置頁面路由 |

---

## 九、驗證計劃

### 9.1 後端測試

```bash
# 單元測試
cd backend
pytest tests/unit/domain/configuration/ -v

# API 測試
pytest tests/unit/api/configuration/ -v

# 整合測試 - 熱更新
pytest tests/integration/configuration/ -v
```

### 9.2 手動驗證

1. **配置 CRUD**：通過 API 創建、讀取、更新、刪除配置
2. **熱更新**：修改配置後，驗證組件是否收到更新
3. **版本回滾**：測試配置回滾功能
4. **前端 Portal**：測試所有 UI 操作

---

## 附錄：與架構圖的對應關係

| 架構圖組件 | 配置分類 | 主要配置項 |
|-----------|---------|-----------|
| Input Gateway | `gateway` | 來源識別、schema 驗證 |
| Event Trigger / User Trigger | `gateway` | 觸發器設定 |
| Coordinator Agent | `orchestrator`, `router`, `risk`, `hitl` | 閾值、策略、超時 |
| Coordinator Tools | `orchestrator` | 可用工具列表 |
| Task Dispatch | `orchestrator` | 分派策略 |
| Claude Worker Pool | `claude_sdk` | Worker 配置 |
| Unified MCP Tool Layer | `mcp` | MCP Server 列表 |
| Observability & Governance | `observability` | 日誌、Metrics、審計 |
