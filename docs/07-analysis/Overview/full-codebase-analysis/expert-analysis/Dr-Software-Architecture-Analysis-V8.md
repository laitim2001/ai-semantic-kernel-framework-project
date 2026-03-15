# Dr. Software Architecture -- IPA Platform 軟體架構分析

> **分析版本**: V8 (基於 2026-03-15 AST 掃描 + 深度代碼審查)
> **分析範圍**: Backend 725 files / 258,904 LOC | Frontend 214 files / 49,357 LOC
> **分析方法**: 靜態 import 依賴追蹤、跨層違規搜索、設計模式識別、SOLID 原則驗證

---

## Executive Summary

IPA Platform 採用四層架構 (API -> Domain -> Integration -> Infrastructure)，經歷 34 個 Phase、133 個 Sprint 的快速迭代後，架構呈現出**局部優秀、全局退化**的典型特徵。

**正面發現**:
- Domain 層已引入 Protocol/ABC 抽象（約 30 處），展示 DIP 意識
- Integration 層內部模組化清晰（16 個獨立子模組）
- Sprint 132 成功將 HybridOrchestratorV2 從 God Object 重構為 Mediator Pattern
- 三層路由架構 (Pattern -> Semantic -> LLM) 展示良好的 Strategy Pattern 應用
- Infrastructure 層的 StorageFactory 提供環境感知的後端切換

**核心問題**:
- API 層嚴重違反分層原則：直接引用 Infrastructure 32 次、Integration 104 次，繞過 Domain
- 全域 Singleton 反模式擴散至 20+ 模組，喪失可測試性
- Domain 層存在反向依賴 API 層的致命違規（`domain/files/service.py` import `api/v1/files/schemas`）
- InMemory 存儲作為生產預設，影響 20+ 模組
- `os.environ`/`os.getenv` 在 Integration 層有 171 處直接調用，繞過 Settings

**架構健康度評分**: **52/100**

| 維度 | 評分 | 說明 |
|------|------|------|
| 分層嚴謹性 | 35/100 | 大量跨層直接調用，層邊界名存實亡 |
| SOLID 遵守度 | 55/100 | DIP 有意識但未貫徹，SRP 有多處違反 |
| 耦合控制 | 45/100 | API-Integration 緊耦合，Singleton 擴散 |
| 內聚品質 | 65/100 | 模組內職責較清晰，但有 deprecated 死代碼 |
| 可測試性 | 50/100 | Singleton + 具體依賴使 mock 困難 |
| 技術債 | 40/100 | 快速迭代累積大量架構債務 |

---

## 1. 分層架構分析

### 1.1 四層架構遵守度

**設計意圖的架構**:
```
API Layer (api/v1/) ──→ Domain Layer (domain/) ──→ Infrastructure (infrastructure/)
                                                          ↑
                     Integration Layer (integrations/) ────┘
```

**實際依賴方向** (基於 import 統計):

| 來源層 | 目標層 | import 次數 | 違規性質 |
|--------|--------|-------------|----------|
| API -> Domain | 49 次 (24 files) | 合法 (正常調用) |
| API -> Integration | **104 次 (40 files)** | **嚴重違規**: API 應透過 Domain 間接使用 Integration |
| API -> Infrastructure | **32 次 (15 files)** | **嚴重違規**: API 直接操作 DB session/repository/model |
| Domain -> Infrastructure | 9 次 (少量) | 可接受 (Repository 注入) |
| Domain -> API | **1 次 (1 file)** | **致命違規**: 反向依賴，破壞分層根基 |
| Integration -> Domain | 15 次 | 可接受 (使用 Domain Models) |
| Integration -> Infrastructure | 3 次 | 可接受 (少量直接 infra 調用) |
| Integration -> API | 0 次 | 良好 (無反向依賴) |

**分層嚴謹性評分: 35/100**

### 1.2 跨層違規清單

#### CRITICAL -- Domain 反向依賴 API

```
檔案: backend/src/domain/files/service.py (Line 17)
違規: from src.api.v1.files.schemas import (
        EXTENSION_TO_MIME, FileCategory, FileMetadata, FileStatus,
        FileUploadResponse, get_file_category, get_max_size_for_mime, is_allowed_mime_type)
```

這是最嚴重的架構違規。Domain 層是核心業務邏輯，絕不應依賴 API 層的 schemas。這些型別定義（FileCategory, FileMetadata 等）應位於 Domain 層，由 API 層的 schemas 引用，而非反過來。

#### HIGH -- API 直接操作 Infrastructure

以下 API 路由直接 import Database session、Repository、Model，完全繞過 Domain Service 層：

| API 路由檔案 | Infrastructure 依賴 | 影響 |
|-------------|---------------------|------|
| `api/v1/agents/routes.py` | `get_session`, `AgentRepository` | Agent CRUD 繞過 Service |
| `api/v1/workflows/routes.py` | `get_session`, `WorkflowRepository` | Workflow CRUD 繞過 Service |
| `api/v1/executions/routes.py` | `ExecutionRepository`, `get_session`, `CheckpointRepository` | Execution 繞過 Service |
| `api/v1/dashboard/routes.py` | 5 個 Model 直接 import | Dashboard 直接查 DB Model |
| `api/v1/auth/routes.py` | `get_session`, `User`, `UserRepository` | Auth 繞過 Service |
| `api/v1/sessions/chat.py` | `get_session` | Chat 直接操作 DB |
| `api/v1/sessions/websocket.py` | `get_session` (6 次 domain import) | WebSocket 混合依賴 |
| `api/v1/cache/routes.py` | `LLMCacheService` | Cache 直接引用 Infra |
| `api/v1/ag_ui/dependencies.py` | `User` model | AG-UI 直接用 DB model |
| `api/v1/checkpoints/routes.py` | `CheckpointRepository` | Checkpoint 繞過 Service |

#### HIGH -- API 直接耦合 Integration（104 次）

API 層有 40 個檔案直接 import Integration 層的具體實現類。最嚴重的幾個：

| API 檔案 | Integration 直接依賴數 | 性質 |
|---------|----------------------|------|
| `api/v1/ag_ui/routes.py` | 6 處 | 直接引用 bridge, events, features |
| `api/v1/ag_ui/dependencies.py` | 7 處 | 直接引用 integrations 類 |
| `api/v1/hybrid/core_routes.py` | 6 處 | 直接實例化 Integration 類 |
| `api/v1/planning/routes.py` | 6 處 | 直接引用 builder, multiturn |
| `api/v1/orchestration/intent_routes.py` | 5 處 | 直接引用 router, dialog |
| `api/v1/orchestration/routes.py` | 5 處 | 直接引用 orchestration 類 |
| `api/v1/claude_sdk/mcp_routes.py` | 5 處 | 直接引用 MCP 類 |

### 1.3 分層改進建議

**P0 -- 修復反向依賴**:
- 將 `api/v1/files/schemas.py` 中的 domain 型別 (FileCategory, FileMetadata, FileStatus) 遷移至 `domain/files/models.py`
- API schemas 引用 Domain models，而非相反

**P1 -- 引入 Application Service 層**:
```
API ──→ Application Service ──→ Domain Service ──→ Repository
                │
                └──→ Integration (Adapters)
```
在 API 和 Domain/Integration 之間引入 Application Service，負責組合 Domain 和 Integration 的操作。API 只調用 Application Service。

**P2 -- 消除 API -> Infrastructure 直接依賴**:
- 所有 `get_session` 調用應透過 Dependency Injection 包裝
- Repository 實例由 Service 層管理，不應在 Route 中直接實例化

---

## 2. SOLID 原則評估

### 2.1 SRP 違反 (Single Responsibility Principle)

#### God Class 清單

| 類別 | 檔案 | LOC | 職責數 | 問題 |
|------|------|-----|--------|------|
| `HybridOrchestratorV2` | `hybrid/orchestrator_v2.py` | 1,254 | 6+ | 雖已 Sprint 132 重構為 Mediator，仍承擔框架選擇、上下文同步、工具執行、風險評估、HITL、檢查點 |
| `ConversationContextManager` | `guided_dialog/context_manager.py` | 1,163 | 4+ | 對話狀態追蹤、歷史管理、上下文壓縮、記憶體管理 |
| `QuestionGenerator` | `guided_dialog/generator.py` | 1,151 | 3+ | 問題生成、模板管理、回應格式化 |
| `ContextBridge` | `hybrid/context/bridge.py` | 932 | 4+ | 雙向同步、衝突解決、快取管理、事件發布 |
| `OrchestrationMetricsCollector` | `orchestration/metrics.py` | 893 | 3+ | 指標收集、匯出、OpenTelemetry 整合 |
| `ClaudeMAFFusion` | `hybrid/claude_maf_fusion.py` | 892 | 4+ | Claude-MAF 融合、決策路由、上下文翻譯、錯誤處理 |
| `ModeSwitcher` | `hybrid/switching/switcher.py` | 829 | 3+ | 模式偵測、狀態遷移、觸發器管理 |
| `HITLController` | `orchestration/hitl/controller.py` | 788 | 4+ | 審批流程、Redis 操作、通知、狀態管理 |
| `UnifiedToolExecutor` | `hybrid/execution/unified_executor.py` | 797 | 3+ | 工具路由、執行、結果處理 |

**評估**: 多數核心類超過 800 LOC，承擔 3-6 項職責，違反 SRP。Sprint 132 的 Mediator 重構方向正確，但 Mediator 本身仍需進一步拆分。

### 2.2 OCP 評估 (Open/Closed Principle)

**良好實踐**:
- `orchestration/input_gateway/source_handlers/base_handler.py` -- BaseSourceHandler 抽象基類，新來源只需擴展
- `domain/connectors/base.py` -- BaseConnector ABC，支持擴展新連接器
- `domain/checkpoints/storage.py` -- CheckpointStorage ABC，4 種後端實現
- 三層路由器 -- PatternMatcher / SemanticRouter / LLMClassifier 可獨立擴展

**違反案例**:
- `api/v1/__init__.py` 需要手動修改以註冊每個新路由（47 個 import + include_router）
- `main.py` 的 `register_routes()` 是一個巨大的修改入口
- 新 MCP Server 需修改多處配置（非插件式）

### 2.3 LSP 評估 (Liskov Substitution Principle)

**基本遵守**: ABC/Protocol 的實現類大致遵守契約。

**潛在風險**:
- `MemoryCheckpointStorage` 作為 `CheckpointStorage` 的實現，數據重啟即遺失，行為語義與持久化抽象不一致
- `InMemoryConversationMemoryStore` 同理，語義上不滿足持久化契約

### 2.4 ISP 評估 (Interface Segregation Principle)

**良好實踐**:
- Domain 層使用 `Protocol` 定義細粒度介面（約 15+ Protocol 定義）：
  - `SessionServiceProtocol`, `AgentRepositoryProtocol`, `MCPClientProtocol`
  - `LLMServiceProtocol`, `WorkflowServiceProtocol`, `CacheProtocol`
  - `ToolRegistryProtocol`, `DatabaseSessionProtocol`, `RedisClientProtocol`

**違反案例**:
- `HybridOrchestratorV2` 對外暴露的介面過於龐大，調用方必須了解全部 6 個子系統
- 部分 Service 類沒有介面定義，直接作為具體類被依賴

### 2.5 DIP 評估 (Dependency Inversion Principle)

**依賴抽象 vs 具體的比率**:

| 層級 | ABC/Protocol 數量 | 具體類直接依賴 | DIP 遵守率 |
|------|-------------------|---------------|-----------|
| Domain | ~15 Protocol + 4 ABC | 9 次直接 import Infrastructure | ~60% |
| API | 0 (無抽象依賴) | 104 次直接 import Integration + 32 次 Infrastructure | ~5% |
| Integration | 少量內部抽象 | 3 次直接 import Infrastructure + 171 次 os.environ | ~40% |

**核心問題**: API 層完全不依賴抽象，直接耦合具體實現類。這是系統最大的 DIP 違規。

**`os.environ` / `os.getenv` 濫用**:
- Integration 層: 171 次直接調用 (44 個檔案)
- 應統一透過 `src.core.config.get_settings()` (Pydantic Settings) 存取
- 散落的 `os.getenv` 使環境配置無法集中管理、無法型別校驗

---

## 3. 耦合與內聚分析

### 3.1 模組耦合矩陣

```
            API   Domain  Integr.  Infra   Core
API          -     49      104      32      ~10
Domain       1*     -       0       9       ~5
Integration  0     15       -       3       ~20
Infra        0      0       0       -       ~3
Core         0      0       0       0        -

* = 致命反向依賴
```

**最高耦合模組對**:
1. `api/v1/` <-> `integrations/` : 104 次 (應為 0)
2. `api/v1/` <-> `infrastructure/` : 32 次 (應為 0，透過 DI 注入)
3. `api/v1/` <-> `domain/` : 49 次 (合法但應透過 Application Service)

### 3.2 循環依賴

**已確認的循環依賴**:

1. **Domain <-> API 循環** (CRITICAL):
   ```
   domain/files/service.py ──import──→ api/v1/files/schemas.py
   api/v1/files/routes.py  ──import──→ domain/files/service.py
   ```

2. **Integration <-> Infrastructure 潛在循環**:
   ```
   integrations/orchestration/hitl/controller.py ──import──→ infrastructure/redis_client.py
   infrastructure/storage/storage_factories.py   ──import──→ integrations/ag_ui/thread/storage.py
   infrastructure/storage/storage_factories.py   ──import──→ integrations/hybrid/switching/switcher.py
   ```
   Infrastructure 的 StorageFactory 反向引用 Integration 層的具體實現類，形成架構反模式。

### 3.3 God Module / God Class

#### God Module

| 模組 | 檔案數 | LOC | 問題 |
|------|--------|-----|------|
| `integrations/hybrid/` | 60 | ~21,000 | 承擔過多職責：intent, context, execution, checkpoint, switching, risk, hooks |
| `integrations/orchestration/` | 39 | ~16,000 | 涵蓋路由、對話、閘道、HITL、風險、審計、指標 |
| `integrations/agent_framework/` | 53 | ~15,000 | 9+ builder adapters + memory + multiturn + tools |
| `domain/sessions/` | 33 | 最大 domain 模組 | models, service, events, executor, streaming, tools, errors, recovery, metrics |

#### Singleton 擴散 (God Instance 反模式)

已識別 20+ 處 Module-level Singleton：

| 位置 | Singleton 類型 | 影響 |
|------|---------------|------|
| `api/v1/hybrid/core_routes.py` | Module-level instances | 無法 mock 測試 |
| `api/v1/hybrid/context_routes.py` | Module-level instances | 全域狀態 |
| `api/v1/hybrid/switch_routes.py` | Module-level instances | 全域狀態 |
| `api/v1/hybrid/risk_routes.py` | Module-level instances | 全域狀態 |
| `api/v1/hybrid/dependencies.py` | Module-level instances | 全域狀態 |
| `api/v1/orchestration/intent_routes.py` | Singleton Router Instance | 無法替換 |
| `api/v1/orchestration/routes.py` | Module-level instances | 全域狀態 |
| `api/v1/orchestration/webhook_routes.py` | Service Singleton | 全域狀態 |
| `api/v1/checkpoints/routes.py` | ApprovalWorkflowManager Singleton | 全域狀態 |
| `api/v1/planning/routes.py` | PlanningAdapter Singleton | 全域狀態 |
| `api/v1/handoff/routes.py` | Service Singleton | 全域狀態 |
| `api/v1/concurrent/adapter_service.py` | _service_instance = None | 手動 Singleton |
| `domain/agents/tools/registry.py` | _registry_instance = None | 手動 Singleton |
| `integrations/agent_framework/acl/adapter.py` | Module-level Singleton | 全域狀態 |
| `integrations/swarm/tracker.py` | Singleton instance | 全域狀態 |
| `integrations/llm/factory.py` | Singleton pattern | 全域狀態 |
| `core/observability/metrics.py` | Singleton metrics | 全域狀態 |
| `integrations/claude_sdk/tools/registry.py` | Singleton instances | 全域狀態 |

**影響**: Module-level Singleton 使得：
1. 單元測試無法獨立 mock（需要 monkey-patching）
2. 並發場景下存在競爭條件（如 `ContextBridge._context_cache` 無鎖）
3. 服務生命週期無法被容器管理
4. 無法實現優雅的多租戶隔離

---

## 4. 技術債評估

### 4.1 架構債務

| 債務項 | 嚴重度 | 影響範圍 | 預估修復工時 |
|--------|--------|----------|------------|
| API 層繞過 Domain 直接調用 Integration/Infrastructure | CRITICAL | 40+ 檔案, 136 次違規 | 80-120h |
| Domain -> API 反向依賴 | CRITICAL | 1 檔案但破壞架構根基 | 4h |
| Infrastructure StorageFactory 反向引用 Integration | HIGH | 6 個 factory 函數 | 16h |
| 缺少 Application Service 層 | HIGH | 全系統 | 120-160h |
| 47 個路由手動註冊（OCP 違規） | MEDIUM | main.py + __init__.py | 24h |

### 4.2 設計債務

| 債務項 | 嚴重度 | 影響範圍 | 預估修復工時 |
|--------|--------|----------|------------|
| 20+ Module-level Singleton | HIGH | 20+ 模組 | 60-80h |
| InMemory 作為生產預設 | CRITICAL | 20+ 模組 (C-01) | 40-60h |
| `os.environ` 散落使用 | HIGH | 171 次 (44 files) | 32-48h |
| God Classes (800+ LOC) | MEDIUM | 9 個核心類 | 60-80h |
| deprecated domain/orchestration/ 未清理 | LOW | 4 個子模組 | 8-16h |

### 4.3 代碼債務

| 債務項 | 嚴重度 | 數量 | 預估修復工時 |
|--------|--------|------|------------|
| 空函數 / Stub | HIGH | 285 個 (3.7%) | 100-200h |
| Mock/硬編碼回應 API | CRITICAL | 234 處 (119 backend + 115 frontend) | 80-120h |
| SQL Injection (f-string) | CRITICAL | 1 處 (postgres_store.py) | 2h |
| API Key 暴露 | CRITICAL | 1 處 (ag_ui response) | 2h |
| datetime.utcnow() deprecated | LOW | 6+ 處 | 4h |
| 無 Auth 端點 | HIGH | 529/560 (94.5%) | 40-60h |

### 4.4 債務量化估算

| 類別 | 預估總工時 | 相當於 Sprint 數 |
|------|-----------|----------------|
| 架構債務 | 244-320h | 6-8 sprints |
| 設計債務 | 200-284h | 5-7 sprints |
| 代碼債務 | 228-388h | 6-10 sprints |
| **總計** | **672-992h** | **17-25 sprints** |

以目前團隊速率（~2500 SP / 133 sprints = ~19 SP/sprint），技術債修復約需 **17-25 個 Sprint**，佔已投入工作量的 13-19%。這個比例在快速迭代項目中屬於中高水平，但仍在可管理範圍內。

---

## 5. 設計模式分析

### 5.1 使用的模式及合理性

| 模式 | 使用位置 | 合理性 | 評分 |
|------|---------|--------|------|
| **Adapter** | `integrations/agent_framework/builders/` (9 adapters) | 優秀 -- 隔離外部 MAF API 變更 | 9/10 |
| **Strategy** | Three-tier routing (Pattern/Semantic/LLM) | 優秀 -- 可獨立替換路由策略 | 9/10 |
| **Mediator** | `HybridOrchestratorV2` (Sprint 132 重構) | 良好 -- 解耦了 6 個 Handler，但 Mediator 本身仍偏大 | 7/10 |
| **Factory** | `infrastructure/storage/storage_factories.py` | 良好 -- 環境感知後端切換 | 7/10 |
| **Observer/Event** | `domain/sessions/events.py` (15 event types) | 良好 -- 解耦事件發布/訂閱 | 7/10 |
| **State Machine** | `domain/executions/state_machine.py` | 優秀 -- 清晰的狀態轉換定義 | 8/10 |
| **Repository** | `infrastructure/database/repositories/` | 良好 -- 但被 API 層繞過 | 6/10 |
| **Chain of Responsibility** | Hook Chain (Approval -> Audit -> RateLimit -> Sandbox) | 良好 -- Claude SDK hook 設計 | 7/10 |
| **Template Method** | `BaseSourceHandler` (InputGateway) | 良好 -- 統一來源處理流程 | 7/10 |
| **Singleton** | 20+ 處 Module-level | **差** -- 濫用，損害可測試性 | 2/10 |

### 5.2 缺失的模式（應用但未用）

| 建議模式 | 適用場景 | 預期收益 |
|---------|---------|---------|
| **Dependency Injection Container** | 替代所有 Module-level Singleton | 可測試性、生命週期管理、多租戶 |
| **CQRS (Command Query Separation)** | API 層的讀/寫分離 | 560 端點的性能優化、讀模型簡化 |
| **Unit of Work** | 跨 Repository 的交易管理 | 資料一致性保證 |
| **Anti-Corruption Layer (ACL)** | API -> Integration 邊界 | 隔離外部框架變更對內部的影響 |
| **Domain Events (Pub/Sub)** | 跨模組通訊 | 解耦模組間直接依賴 |
| **Plugin Architecture** | Router 註冊、MCP Server 註冊 | 自動發現、OCP 遵守 |
| **Specification Pattern** | 複雜查詢/過濾邏輯 | 業務規則可組合、可測試 |

---

## 6. 架構改進路線圖

### Phase A: 止血 (Sprint N+1 ~ N+3, 約 3 Sprints)

**目標**: 修復致命違規，阻止架構進一步退化

| 優先級 | 任務 | 工時 | 影響 |
|--------|------|------|------|
| P0 | 修復 `domain/files/service.py` -> `api/v1/files/schemas` 反向依賴 | 4h | 消除循環依賴 |
| P0 | 修復 SQL Injection (`postgres_store.py` f-string) | 2h | 安全修復 |
| P0 | 修復 API Key 暴露 (ag_ui response) | 2h | 安全修復 |
| P1 | 統一 `os.environ` -> `get_settings()` (44 files) | 32h | 配置集中管理 |
| P1 | 修復 `infrastructure/storage_factories.py` 反向引用 Integration | 16h | 消除架構循環 |

### Phase B: 基礎設施 (Sprint N+4 ~ N+8, 約 5 Sprints)

**目標**: 建立正確的依賴管理基礎

| 優先級 | 任務 | 工時 | 影響 |
|--------|------|------|------|
| P1 | 引入 DI Container (如 `dependency-injector` 或 FastAPI 原生 Depends 重構) | 40h | 替代 20+ Singleton |
| P1 | InMemory -> Redis/PostgreSQL 預設切換 (20+ 模組) | 40h | 生產就緒 |
| P1 | 建立 Application Service 層 (先處理 agents, workflows, executions) | 48h | 分層基礎 |
| P2 | API 路由自動發現機制 (Plugin Pattern) | 24h | OCP 遵守 |

### Phase C: 分層重構 (Sprint N+9 ~ N+16, 約 8 Sprints)

**目標**: 逐步消除跨層直接依賴

| 優先級 | 任務 | 工時 | 影響 |
|--------|------|------|------|
| P1 | API -> Infrastructure 32 次直接依賴遷移至 Service/DI | 60h | 分層合規 |
| P1 | API -> Integration 104 次依賴遷移至 Application Service | 80h | 分層合規 |
| P2 | God Class 拆分 (9 個 800+ LOC 類) | 60h | SRP 遵守 |
| P2 | deprecated `domain/orchestration/` 清理 | 16h | 減少死代碼 |

### Phase D: 品質提升 (Sprint N+17 ~ N+25, 約 9 Sprints)

**目標**: 架構品質達到企業級標準

| 優先級 | 任務 | 工時 | 影響 |
|--------|------|------|------|
| P2 | 引入 Domain Events 解耦跨模組通訊 | 40h | 模組獨立性 |
| P2 | CQRS 讀寫分離 (高流量端點) | 60h | 性能優化 |
| P3 | ArchUnit/import-linter 自動化架構規則檢查 | 16h | 持續合規 |
| P3 | 空函數/Stub 清理 (285 個) | 100h | 代碼品質 |

### 成功指標

| 指標 | 當前值 | Phase B 目標 | Phase D 目標 |
|------|--------|-------------|-------------|
| API -> Infrastructure 直接依賴 | 32 次 | 16 次 | 0 次 |
| API -> Integration 直接依賴 | 104 次 | 52 次 | 0 次 |
| Domain -> API 反向依賴 | 1 次 | 0 次 | 0 次 |
| Module-level Singleton | 20+ 處 | 5 處 | 0 處 |
| os.environ 直接調用 | 171 次 | 30 次 | 0 次 |
| InMemory 生產預設 | 20+ 模組 | 5 模組 | 0 模組 |
| 架構健康度評分 | 52/100 | 70/100 | 85/100 |

---

## 附錄 A: 分析方法論

本分析使用以下方法：

1. **Import 依賴追蹤**: 使用 `grep` 搜索 `from src.{layer}` 模式，統計跨層依賴次數和檔案數
2. **Singleton 識別**: 搜索 `_instance = None`, `Singleton`, module-level instance 模式
3. **抽象介面統計**: 搜索 `ABC`, `Protocol`, `Interface`, `abstractmethod` 使用
4. **InMemory 模式識別**: 搜索 `InMemory`, `in_memory`, `_store = {}`, `_cache = {}` 模式
5. **環境配置違規**: 搜索 `os.environ`, `os.getenv` 在非 core/config 位置的使用
6. **V8 AST 分析報告**: 交叉驗證 62 項已知問題

## 附錄 B: 參考文件

- `MAF-Claude-Hybrid-Architecture-V8.md` -- 11 層架構深度分析
- `MAF-Features-Architecture-Mapping-V8.md` -- 70+ 功能驗證
- `phase4-validation-issue-registry.md` -- 62 項去重問題清單
- `phase4-validation-e2e-flows.md` -- 5 條端到端流程驗證
