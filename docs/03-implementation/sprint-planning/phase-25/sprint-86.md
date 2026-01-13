# Sprint 86: mem0 整合完善

> **Sprint**: 86
> **Story Points**: 13 pts
> **目標**: 完善 mem0 整合的依賴、配置和測試

---

## User Stories

### S86-1: 添加 mem0 依賴 (1 pt)

**描述**: 將 mem0 SDK 添加到項目依賴

**驗收標準**:
- [ ] 添加 `mem0ai>=0.0.1` 到 `requirements.txt`
- [ ] `pip install -r requirements.txt` 成功
- [ ] `python -c "import mem0"` 無錯誤
- [ ] 現有測試仍然通過

**交付物**:
- 更新 `backend/requirements.txt`

---

### S86-2: 環境變數配置 (2 pts)

**描述**: 完善 mem0 相關的環境變數配置

**驗收標準**:
- [ ] 更新 `.env.example` 包含所有 mem0 配置
- [ ] 更新 `types.py` 支持環境變數讀取
- [ ] 配置項包含：
  - `MEM0_ENABLED`
  - `QDRANT_PATH`
  - `QDRANT_COLLECTION`
  - `EMBEDDING_MODEL`
  - `MEMORY_LLM_PROVIDER`
  - `MEMORY_LLM_MODEL`
  - `WORKING_MEMORY_TTL`
  - `SESSION_MEMORY_TTL`
- [ ] 默認值合理

**交付物**:
- 更新 `backend/.env.example`
- 更新 `backend/src/integrations/memory/types.py`

---

### S86-3: mem0_client.py 單元測試 (5 pts)

**描述**: 為 Mem0Client 類添加完整的單元測試

**驗收標準**:
- [ ] 測試 `initialize()` 成功場景
- [ ] 測試 `initialize()` 失敗場景
- [ ] 測試 `add_memory()` 功能
- [ ] 測試 `search_memory()` 功能
- [ ] 測試 `get_all()` 功能
- [ ] 測試 `get_memory()` 功能
- [ ] 測試 `update_memory()` 功能
- [ ] 測試 `delete_memory()` 功能
- [ ] 測試 `delete_all()` 功能
- [ ] 測試 `get_history()` 功能
- [ ] Mock 外部 API 調用
- [ ] 測試覆蓋率 > 85%

**交付物**:
- 新增 `backend/tests/unit/test_mem0_client.py`

**測試結構**:
```python
import pytest
from unittest.mock import Mock, patch, AsyncMock

from src.integrations.memory.mem0_client import Mem0Client
from src.integrations.memory.types import MemoryConfig


class TestMem0ClientInitialization:
    """初始化測試"""
    
    @patch('src.integrations.memory.mem0_client.Memory')
    async def test_initialize_success(self, mock_memory):
        """測試成功初始化"""
        client = Mem0Client()
        await client.initialize()
        assert client.is_initialized
        
    @patch('src.integrations.memory.mem0_client.Memory')
    async def test_initialize_with_custom_config(self, mock_memory):
        """測試自定義配置初始化"""
        config = MemoryConfig(qdrant_path="/custom/path")
        client = Mem0Client(config)
        await client.initialize()
        # 驗證配置被正確使用


class TestMem0ClientOperations:
    """記憶操作測試"""
    
    @pytest.fixture
    def initialized_client(self):
        """已初始化的客戶端 fixture"""
        client = Mem0Client()
        client._memory = Mock()
        client._initialized = True
        return client
    
    async def test_add_memory(self, initialized_client):
        """測試添加記憶"""
        initialized_client._memory.add = Mock(
            return_value={"id": "mem-123"}
        )
        result = await initialized_client.add_memory(
            content="Test memory",
            user_id="user-1"
        )
        assert result["id"] == "mem-123"
        
    async def test_search_memory(self, initialized_client):
        """測試搜索記憶"""
        initialized_client._memory.search = Mock(
            return_value=[{"id": "mem-1", "score": 0.95}]
        )
        results = await initialized_client.search_memory(
            query="test query",
            user_id="user-1"
        )
        assert len(results) == 1
```

---

### S86-4: Memory API 集成測試 (3 pts)

**描述**: 為 Memory API 端點添加集成測試

**驗收標準**:
- [ ] 測試 `POST /memory/add` 端點
- [ ] 測試 `POST /memory/search` 端點
- [ ] 測試 `GET /memory/user/{user_id}` 端點
- [ ] 測試 `GET /memory/{memory_id}` 端點
- [ ] 測試 `DELETE /memory/{memory_id}` 端點
- [ ] 測試 `POST /memory/promote` 端點
- [ ] 測試 `POST /memory/context` 端點
- [ ] 測試 `GET /memory/health` 端點
- [ ] 測試錯誤處理和驗證

**交付物**:
- 新增 `backend/tests/integration/test_memory_api.py`

**測試結構**:
```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from main import app


class TestMemoryAPI:
    """Memory API 集成測試"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @patch('src.integrations.memory.unified_memory.UnifiedMemoryManager')
    def test_add_memory_success(self, mock_manager, client):
        """測試成功添加記憶"""
        mock_manager.return_value.add = AsyncMock(
            return_value={"id": "mem-123", "layer": "long_term"}
        )
        
        response = client.post("/api/v1/memory/add", json={
            "content": "User prefers dark mode",
            "user_id": "user-1",
            "memory_type": "user_preference"
        })
        
        assert response.status_code == 200
        assert response.json()["id"] == "mem-123"
        
    def test_add_memory_validation_error(self, client):
        """測試添加記憶的驗證錯誤"""
        response = client.post("/api/v1/memory/add", json={
            # 缺少必要字段
        })
        assert response.status_code == 422
```

---

### S86-5: 文檔更新 (2 pts)

**描述**: 更新 mem0 相關的技術文檔

**驗收標準**:
- [ ] 創建 `docs/04-usage/memory-configuration.md`
- [ ] 更新 `docs/02-architecture/technical-architecture.md`
- [ ] 包含配置說明
- [ ] 包含 API 使用示例
- [ ] 包含故障排除章節

**交付物**:
- 新增 `docs/04-usage/memory-configuration.md`
- 更新架構文檔

**文檔結構**:
```markdown
# Memory System Configuration

## Overview
- Three-layer architecture explanation
- mem0 integration details

## Configuration
- Environment variables
- Default values
- Production recommendations

## Usage Examples
- Adding memories
- Searching memories
- Memory promotion

## API Reference
- Endpoint documentation
- Request/Response examples

## Troubleshooting
- Common issues
- Debugging tips
```

---

## 技術實現

### 環境變數讀取

```python
# backend/src/integrations/memory/types.py

import os
from dataclasses import dataclass, field

@dataclass
class MemoryConfig:
    """Memory system configuration."""
    
    # Qdrant settings
    qdrant_path: str = field(
        default_factory=lambda: os.getenv("QDRANT_PATH", "/data/mem0/qdrant")
    )
    qdrant_collection: str = field(
        default_factory=lambda: os.getenv("QDRANT_COLLECTION", "ipa_memories")
    )
    
    # Embedding settings
    embedding_model: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    )
    
    # LLM settings for memory extraction
    llm_provider: str = field(
        default_factory=lambda: os.getenv("MEMORY_LLM_PROVIDER", "anthropic")
    )
    llm_model: str = field(
        default_factory=lambda: os.getenv("MEMORY_LLM_MODEL", "claude-sonnet-4-20250514")
    )
    
    # TTL settings (seconds)
    working_memory_ttl: int = field(
        default_factory=lambda: int(os.getenv("WORKING_MEMORY_TTL", "1800"))
    )
    session_memory_ttl: int = field(
        default_factory=lambda: int(os.getenv("SESSION_MEMORY_TTL", "604800"))
    )
    
    # Feature flag
    enabled: bool = field(
        default_factory=lambda: os.getenv("MEM0_ENABLED", "true").lower() == "true"
    )
```

---

## 測試計劃

### 單元測試
- [ ] Mem0Client 初始化
- [ ] 記憶 CRUD 操作
- [ ] 搜索功能
- [ ] 錯誤處理

### 集成測試
- [ ] API 端點功能
- [ ] 層級選擇邏輯
- [ ] 健康檢查

### 端到端測試
- [ ] 完整記憶流程
- [ ] 多層記憶互動

---

## 更新歷史

| 日期 | 說明 |
|------|------|
| 2026-01-13 | 初始規劃 |
