# LLM 服務模組

> 統一的 LLM (Large Language Model) 服務抽象層，支援 AI 自主決策能力

**版本**: 1.0.0
**日期**: 2025-12-21
**狀態**: Phase 7 完成

---

## 目錄

- [概覽](#概覽)
- [快速開始](#快速開始)
- [架構設計](#架構設計)
- [服務實現](#服務實現)
- [使用指南](#使用指南)
- [配置說明](#配置說明)
- [測試指南](#測試指南)
- [效能優化](#效能優化)
- [故障排除](#故障排除)

---

## 概覽

LLM 服務模組為 IPA Platform 提供統一的 AI 能力接口，主要特性：

- **統一接口**: `LLMServiceProtocol` 定義標準 API
- **多提供者支援**: Azure OpenAI、Mock 測試服務
- **效能優化**: Redis 緩存、連接池
- **降級策略**: LLM 不可用時自動回退到規則式處理
- **可測試性**: Mock 服務支援完整單元測試

---

## 快速開始

### 基本用法

```python
from src.integrations.llm import LLMServiceFactory

# 創建 LLM 服務實例
llm_service = LLMServiceFactory.create()

# 生成文本回應
response = await llm_service.generate("請分析這個任務的複雜度")
print(response)

# 生成結構化回應
schema = {
    "type": "object",
    "properties": {
        "subtasks": {"type": "array"},
        "confidence": {"type": "number"}
    }
}
result = await llm_service.generate_structured(
    prompt="分解這個任務: 實現用戶認證系統",
    output_schema=schema
)
print(result)  # {"subtasks": [...], "confidence": 0.85}
```

### 與 PlanningAdapter 整合

```python
from src.integrations.llm import LLMServiceFactory
from src.integrations.agent_framework.builders.planning import PlanningAdapter

# 創建 LLM 服務
llm_service = LLMServiceFactory.create()

# 創建規劃適配器並注入 LLM
adapter = (
    PlanningAdapter(id="planner", llm_service=llm_service)
    .with_task_decomposition()
    .with_decision_engine()
    .with_trial_error()
)

# 使用 AI 能力分解任務
plan = await adapter.plan(goal="實現完整的認證系統")
```

---

## 架構設計

### 模組結構

```
src/integrations/llm/
├── __init__.py           # 模組入口，導出公開 API
├── protocol.py           # LLMServiceProtocol 定義
├── factory.py            # LLMServiceFactory 工廠類
├── azure_openai.py       # Azure OpenAI 實現
├── mock.py               # Mock 測試服務
├── cached.py             # Redis 緩存包裝器
├── exceptions.py         # LLM 相關異常
└── README.md             # 本文檔
```

### 類別關係

```
┌─────────────────────────────────────────────────────┐
│              LLMServiceProtocol                      │
│  (Protocol - 接口定義)                               │
│  + generate(prompt) → str                           │
│  + generate_structured(prompt, schema) → Dict       │
│  + is_available() → bool                            │
└───────────────────┬─────────────────────────────────┘
                    │ implements
        ┌───────────┼───────────────┐
        ▼           ▼               ▼
┌───────────────┐ ┌────────────┐ ┌──────────────────┐
│ AzureOpenAI-  │ │ MockLLM-   │ │ CachedLLM-       │
│ LLMService    │ │ Service    │ │ Service          │
│               │ │            │ │ (Decorator)      │
│ - 生產環境    │ │ - 測試用   │ │ - 包裝任意服務   │
└───────────────┘ └────────────┘ └──────────────────┘
                                          │
                                          ▼
                             ┌──────────────────────┐
                             │  Inner LLMService    │
                             │  (被包裝的服務)       │
                             └──────────────────────┘
```

---

## 服務實現

### AzureOpenAILLMService

生產環境使用的 Azure OpenAI 服務：

```python
from src.integrations.llm.azure_openai import AzureOpenAILLMService

service = AzureOpenAILLMService(
    endpoint="https://your-resource.openai.azure.com/",
    api_key="your-api-key",
    deployment_name="gpt-5.2",
    timeout=30
)

# 檢查服務可用性
if service.is_available():
    response = await service.generate("Hello, world!")
```

**特性**:
- GPT-4o / GPT-4 Turbo 支援
- 自動重試 (可配置)
- 超時控制
- 詳細錯誤處理

### MockLLMService

測試用的模擬服務：

```python
from src.integrations.llm.mock import MockLLMService

# 基本 Mock
mock_service = MockLLMService(
    responses={"default": "這是測試回應"},
    latency=0.1  # 模擬 100ms 延遲
)

# 結構化回應 Mock
mock_service = MockLLMService(
    structured_responses={
        "default": {"subtasks": [], "confidence": 0.9}
    }
)

# 錯誤模擬
mock_service = MockLLMService(
    error_on_call=3,  # 第 3 次調用拋出錯誤
    error_type="timeout"  # 超時錯誤
)
```

**特性**:
- 可配置回應內容
- 延遲模擬
- 錯誤注入
- 調用計數追蹤

### CachedLLMService

Redis 緩存包裝器：

```python
from src.integrations.llm.cached import CachedLLMService

# 包裝現有服務
cached_service = CachedLLMService(
    inner_service=azure_service,
    redis_client=redis_client,
    ttl=3600,  # 緩存 1 小時
    enabled=True
)

# 獲取緩存統計
stats = cached_service.get_stats()
print(f"命中率: {stats['hit_rate']:.2%}")
```

**特性**:
- 透明緩存層
- 可禁用/啟用
- 命中率統計
- TTL 配置

---

## 使用指南

### 工廠模式

推薦使用 `LLMServiceFactory` 創建服務：

```python
from src.integrations.llm import LLMServiceFactory

# 自動選擇提供者 (根據環境配置)
service = LLMServiceFactory.create()

# 指定提供者
service = LLMServiceFactory.create(provider="azure_openai")
service = LLMServiceFactory.create(provider="mock")

# 單例模式 (共享實例)
service1 = LLMServiceFactory.create(singleton=True)
service2 = LLMServiceFactory.create(singleton=True)
assert service1 is service2  # 同一實例

# 測試用快捷方法
mock_service = LLMServiceFactory.create_for_testing()
```

### 與組件整合

#### TaskDecomposer

```python
from src.integrations.agent_framework.builders.planning import (
    PlanningAdapter,
    DecompositionStrategy
)

adapter = PlanningAdapter(id="test", llm_service=llm_service)
adapter.with_task_decomposition(strategy=DecompositionStrategy.HYBRID)

# TaskDecomposer 自動使用 LLM 進行任務分解
```

#### DecisionEngine

```python
adapter = PlanningAdapter(id="test", llm_service=llm_service)
adapter.with_decision_engine()

# DecisionEngine 自動使用 LLM 進行決策
```

#### TrialAndErrorEngine

```python
adapter = PlanningAdapter(id="test", llm_service=llm_service)
adapter.with_trial_error(max_retries=3)

# TrialAndErrorEngine 自動使用 LLM 學習錯誤
```

---

## 配置說明

### 環境變數

```bash
# Azure OpenAI 必要配置
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5.2

# LLM 服務可選配置
LLM_PROVIDER=azure_openai    # azure_openai | mock
LLM_TIMEOUT=30               # 請求超時 (秒)
LLM_MAX_RETRIES=3            # 最大重試次數

# 緩存配置
LLM_CACHE_ENABLED=true       # 啟用緩存
LLM_CACHE_TTL=3600           # 緩存 TTL (秒)

# 降級配置
LLM_FALLBACK_ENABLED=true    # 啟用降級
```

### 配置優先級

1. 環境變數
2. `src/core/config.py` 默認值
3. 程式碼硬編碼默認值

---

## 測試指南

### 單元測試

```python
import pytest
from src.integrations.llm import LLMServiceFactory

@pytest.fixture
def mock_llm():
    return LLMServiceFactory.create_for_testing()

@pytest.mark.asyncio
async def test_generate(mock_llm):
    response = await mock_llm.generate("test prompt")
    assert response is not None

@pytest.mark.asyncio
async def test_generate_structured(mock_llm):
    result = await mock_llm.generate_structured(
        prompt="test",
        output_schema={"type": "object"}
    )
    assert isinstance(result, dict)
```

### 效能測試

```bash
# 執行 LLM 效能測試
cd backend
pytest tests/performance/test_llm_performance.py -v -m performance
```

### E2E 測試

```bash
# 執行端到端 LLM 整合測試
cd backend
pytest tests/e2e/test_llm_integration.py -v -m e2e
```

---

## 效能優化

### 緩存策略

1. **相同提示緩存**: 相同輸入產生相同輸出時使用緩存
2. **TTL 配置**: 根據資料時效性調整 TTL
3. **緩存預熱**: 啟動時預載入常用查詢

### 並發控制

```python
# 並發請求限制
import asyncio

semaphore = asyncio.Semaphore(10)  # 最多 10 並發

async def limited_generate(prompt):
    async with semaphore:
        return await llm_service.generate(prompt)
```

### 效能指標

| 指標 | 目標值 | 監控方式 |
|------|--------|----------|
| P95 延遲 | < 5s | Prometheus |
| 並發成功率 | > 80% | Application Insights |
| 緩存命中率 | > 60% | Redis 統計 |
| 錯誤率 | < 5% | 日誌監控 |

---

## 故障排除

### 常見問題

#### 1. Azure OpenAI 連接失敗

```
Error: LLMServiceError: Failed to connect to Azure OpenAI
```

**解決方案**:
- 檢查 `AZURE_OPENAI_ENDPOINT` 格式
- 驗證 `AZURE_OPENAI_API_KEY` 有效性
- 確認 deployment name 正確

#### 2. 超時錯誤

```
Error: LLMTimeoutError: Request timed out after 30s
```

**解決方案**:
- 增加 `LLM_TIMEOUT` 值
- 檢查網路連接
- 使用更簡短的 prompt

#### 3. 降級到規則式

```
Warning: LLM service unavailable, using rule-based fallback
```

**說明**:
- 這是正常的降級行為
- LLM 功能暫時不可用
- 系統仍能正常運作

### 日誌查看

```python
from src.core.logging import get_logger

logger = get_logger("llm")
logger.setLevel("DEBUG")  # 啟用詳細日誌
```

---

## 相關文檔

- [技術架構文檔](../../../../docs/02-architecture/technical-architecture.md)
- [Phase 7 總結報告](../../../../docs/03-implementation/sprint-execution/phase-7-summary.md)
- [UAT 驗證計畫](../../../../claudedocs/uat/UAT-SCENARIO-VALIDATION-PLAN.md)

---

**最後更新**: 2025-12-21
