# Phase 25: mem0 整合完善

> **Phase**: 25
> **Sprint**: S86
> **Story Points**: 13 pts (預估)
> **狀態**: 📋 規劃中

---

## 概述

### 目標

完善 mem0 長期記憶系統的整合，添加依賴項、環境變數配置、測試覆蓋和文檔更新。

### 背景

mem0 整合的核心代碼已在 Phase 22 實現，包含：
- `Mem0Client` - mem0 SDK 包裝器
- `UnifiedMemoryManager` - 三層記憶統一管理
- `EmbeddingService` - 向量生成服務
- Memory API 路由 (8 個端點)

但存在以下待完成項目：
- `mem0ai` 未添加到 `requirements.txt`
- 環境變數配置不完整
- 缺少單元測試和集成測試

---

## Sprint 規劃

### Sprint 86: mem0 整合完善 (13 pts)

| Story | 內容 | Points |
|-------|------|--------|
| S86-1 | 添加 mem0 依賴 | 1 |
| S86-2 | 環境變數配置 | 2 |
| S86-3 | mem0_client.py 單元測試 | 5 |
| S86-4 | Memory API 集成測試 | 3 |
| S86-5 | 文檔更新 | 2 |

---

## 技術需求

### 外部服務依賴

| 服務 | 用途 | 環境變數 | 必要性 |
|------|------|---------|--------|
| **OpenAI API** | 向量生成 (Embeddings) | `OPENAI_API_KEY` | 必須 |
| **Anthropic API** | 記憶提取 (Claude) | `ANTHROPIC_API_KEY` | 必須 |
| **Qdrant** | 向量存儲 | 本地檔案系統 | 已內建 |

### 本地開發模式

mem0 支持完全本地開發：
- Qdrant 使用本地檔案系統存儲
- 無需外部 Qdrant 服務
- 但仍需要 OpenAI 和 Anthropic API keys

### 預估費用

| 服務 | 定價模式 | 預估費用 (開發) |
|------|---------|----------------|
| OpenAI Embeddings | $0.0001/1K tokens | ~$1-5/月 |
| Anthropic Claude | $3/$15 per 1M tokens | ~$5-20/月 |
| Qdrant | 本地免費 | $0 |

---

## 實現詳情

### S86-1: 添加 mem0 依賴

**修改文件**: `backend/requirements.txt`

```txt
# Memory (mem0)
mem0ai>=0.0.1
```

**驗收標準**:
- [ ] 添加 mem0ai 到 requirements.txt
- [ ] pip install 成功
- [ ] import mem0 無錯誤

---

### S86-2: 環境變數配置

**修改文件**: `backend/.env.example`

```bash
# ===========================
# Memory Configuration (mem0)
# ===========================
MEM0_ENABLED=true
QDRANT_PATH=/data/mem0/qdrant
QDRANT_COLLECTION=ipa_memories
EMBEDDING_MODEL=text-embedding-3-small
MEMORY_LLM_PROVIDER=anthropic
MEMORY_LLM_MODEL=claude-sonnet-4-20250514

# Working Memory TTL (seconds)
WORKING_MEMORY_TTL=1800

# Session Memory TTL (seconds)
SESSION_MEMORY_TTL=604800
```

**驗收標準**:
- [ ] .env.example 包含所有 mem0 配置
- [ ] 配置說明註釋完整
- [ ] 默認值合理

---

### S86-3: mem0_client.py 單元測試

**新增文件**: `backend/tests/unit/test_mem0_client.py`

**測試範圍**:
```python
class TestMem0Client:
    def test_initialize_success(self):
        """測試成功初始化"""
        
    def test_initialize_with_invalid_config(self):
        """測試無效配置時的錯誤處理"""
        
    def test_add_memory(self):
        """測試添加記憶"""
        
    def test_search_memory(self):
        """測試語義搜索"""
        
    def test_search_memory_with_filters(self):
        """測試帶過濾條件的搜索"""
        
    def test_get_all_memories(self):
        """測試獲取用戶所有記憶"""
        
    def test_get_memory_by_id(self):
        """測試按 ID 獲取記憶"""
        
    def test_update_memory(self):
        """測試更新記憶"""
        
    def test_delete_memory(self):
        """測試刪除記憶"""
        
    def test_delete_all_memories(self):
        """測試刪除用戶所有記憶"""
        
    def test_get_memory_history(self):
        """測試獲取記憶歷史版本"""
```

**驗收標準**:
- [ ] 所有測試通過
- [ ] 覆蓋主要功能
- [ ] Mock 外部 API 調用

---

### S86-4: Memory API 集成測試

**新增文件**: `backend/tests/integration/test_memory_api.py`

**測試範圍**:
```python
class TestMemoryAPI:
    def test_add_memory_endpoint(self):
        """POST /memory/add"""
        
    def test_search_memory_endpoint(self):
        """POST /memory/search"""
        
    def test_get_user_memories_endpoint(self):
        """GET /memory/user/{user_id}"""
        
    def test_get_memory_endpoint(self):
        """GET /memory/{memory_id}"""
        
    def test_delete_memory_endpoint(self):
        """DELETE /memory/{memory_id}"""
        
    def test_promote_memory_endpoint(self):
        """POST /memory/promote"""
        
    def test_get_context_endpoint(self):
        """POST /memory/context"""
        
    def test_memory_layer_selection(self):
        """測試記憶層自動選擇邏輯"""
        
    def test_health_endpoint(self):
        """GET /memory/health"""
```

**驗收標準**:
- [ ] 所有端點測試通過
- [ ] 層級選擇邏輯正確
- [ ] 錯誤處理測試

---

### S86-5: 文檔更新

**修改文件**: 
- `docs/04-usage/memory-configuration.md` (新增)
- `docs/02-architecture/technical-architecture.md` (更新)

**文檔內容**:
1. mem0 配置說明
2. 三層記憶系統架構說明
3. API 使用示例
4. 開發環境設置指南
5. 故障排除

**驗收標準**:
- [ ] 配置說明完整
- [ ] 包含示例代碼
- [ ] 包含故障排除章節

---

## 三層記憶架構

```
┌─────────────────────────────────────────────────────────┐
│             Working Memory (Layer 1)                     │
│  Redis | TTL: 30 min | 容量: 有限 | 速度: 最快          │
│  用途: 當前對話上下文、即時狀態                          │
└────────────────┬────────────────────────────────────────┘
                 │
┌─────────────────▼────────────────────────────────────────┐
│            Session Memory (Layer 2)                       │
│ PostgreSQL | TTL: 7 天 | 容量: 中等 | 速度: 中等         │
│ 用途: 會話範圍內的記憶、反饋、學習                       │
└────────────────┬────────────────────────────────────────┘
                 │
┌─────────────────▼────────────────────────────────────────┐
│           Long-term Memory (Layer 3)                      │
│ mem0 + Qdrant | TTL: 永久 | 容量: 無限 | 速度: 慢        │
│ 用途: 用戶偏好、最佳實踐、系統知識、事件解決方案         │
└───────────────────────────────────────────────────────────┘
```

---

## 驗收標準

### 功能驗收
- [ ] mem0 正確安裝和初始化
- [ ] 記憶添加和搜索功能正常
- [ ] 三層記憶自動選擇正確
- [ ] API 端點正常工作

### 技術驗收
- [ ] requirements.txt 更新
- [ ] .env.example 完整
- [ ] 測試覆蓋 > 80%
- [ ] 文檔完整

---

## 相關代碼

| 文件 | 說明 |
|------|------|
| `backend/src/integrations/memory/mem0_client.py` | mem0 客戶端 |
| `backend/src/integrations/memory/unified_memory.py` | 統一記憶管理器 |
| `backend/src/integrations/memory/embeddings.py` | 向量服務 |
| `backend/src/api/v1/memory/routes.py` | API 路由 |

---

## 更新歷史

| 日期 | 版本 | 說明 |
|------|------|------|
| 2026-01-13 | 1.0 | 初始規劃 |
