# 🧪 情況5: 測試執行 - 運行和編寫測試

> **使用時機**: 需要運行測試或編寫新測試時
> **目標**: 確保代碼品質和功能正確性
> **適用場景**: 功能驗證、回歸測試、TDD 開發

---

## 📋 Prompt 模板 (給開發人員)

```markdown
你好！我需要運行/編寫測試。

**測試類型**: [單元測試 / 整合測試 / E2E 測試]

**測試目標**:
- [要測試的模組/功能]
- [測試的重點]

請幫我：

1. 運行現有測試
   - 運行相關模組的測試
   - 分析測試結果

2. 編寫新測試 (如需要)
   - 識別缺少的測試案例
   - 編寫新的測試

3. 修復失敗的測試 (如有)
   - 分析失敗原因
   - 修復測試或代碼

4. 測試覆蓋報告
   - 檢查測試覆蓋率
   - 識別需要增加覆蓋的區域

請用中文回答。
```

---

## 🤖 AI 助手執行步驟

### Step 1: 運行測試 (2 分鐘)

```bash
# 1. 運行特定模組測試
Bash: cd backend && pytest tests/unit/domain/{module}/ -v

# 2. 運行 API 測試
Bash: cd backend && pytest tests/unit/api/v1/{module}/ -v

# 3. 運行所有單元測試
Bash: cd backend && pytest tests/unit/ -v --tb=short

# 4. 帶覆蓋率運行
Bash: cd backend && pytest tests/unit/ -v --cov=src --cov-report=term-missing
```

### Step 2: 分析測試結果 (1 分鐘)

```markdown
# 📊 測試結果分析

## 執行摘要
- **總測試數**: X
- **通過**: X ✅
- **失敗**: X ❌
- **跳過**: X ⏭️
- **覆蓋率**: X%

## 失敗測試分析 (如有)
| 測試 | 錯誤類型 | 原因分析 |
|------|----------|----------|
| test_xxx | AssertionError | [分析] |

## 建議行動
1. [建議 1]
2. [建議 2]
```

### Step 3: 編寫測試 (如需要)

```python
# 標準測試模板
# backend/tests/unit/domain/test_{module}_service.py

import pytest
from unittest.mock import MagicMock, patch

from src.domain.{module}.service import {Module}Service


class Test{Module}Service:
    """Test suite for {Module}Service."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create service instance with mocked dependencies."""
        return {Module}Service(mock_db)

    def test_get_all_returns_list(self, service):
        """Test get_all returns a list of items."""
        # Arrange
        expected = [...]

        # Act
        result = service.get_all()

        # Assert
        assert isinstance(result, list)

    def test_get_by_id_returns_item(self, service):
        """Test get_by_id returns correct item."""
        # Arrange
        item_id = "test-id"

        # Act
        result = service.get_by_id(item_id)

        # Assert
        assert result is not None

    def test_create_with_valid_data(self, service):
        """Test create with valid data succeeds."""
        # Arrange
        data = {"name": "test"}

        # Act
        result = service.create(data)

        # Assert
        assert result.name == "test"

    def test_create_with_invalid_data_raises(self, service):
        """Test create with invalid data raises error."""
        # Arrange
        data = {}  # Missing required fields

        # Act & Assert
        with pytest.raises(ValueError):
            service.create(data)
```

### Step 4: 覆蓋率分析 (1 分鐘)

```bash
# 1. 生成詳細覆蓋率報告
Bash: cd backend && pytest tests/unit/ --cov=src --cov-report=html

# 2. 檢查特定模組覆蓋率
Bash: cd backend && pytest tests/unit/ --cov=src/domain/{module} --cov-report=term-missing

# 3. 查看未覆蓋的行
# 輸出會顯示 "Missing" 列，指出未測試的行號
```

---

## 📝 測試類型參考

### 單元測試 (Unit Tests)
- **位置**: `tests/unit/`
- **範圍**: 單一函數或類
- **特點**: 快速、隔離、使用 Mock

### 整合測試 (Integration Tests)
- **位置**: `tests/integration/`
- **範圍**: 多個組件交互
- **特點**: 使用真實依賴、測試 API

### E2E 測試 (End-to-End Tests)
- **位置**: `tests/e2e/`
- **範圍**: 完整用戶流程
- **特點**: 模擬真實使用場景

---

## ✅ 驗收標準

AI 助手應該完成：

1. **測試執行**
   - 成功運行所有相關測試
   - 提供清晰的測試結果摘要

2. **結果分析**
   - 識別失敗測試的原因
   - 提供修復建議

3. **測試編寫** (如需要)
   - 測試案例覆蓋主要場景
   - 遵循項目測試模式

4. **覆蓋率**
   - 達到 80% 以上覆蓋率
   - 識別需要增加覆蓋的區域

---

## 🔗 相關文檔

### 開發流程指引
- [情況3: Bug 修復](./SITUATION-3-BUG-FIX.md)
- [情況4: 功能開發](./SITUATION-4-FEATURE-DEVELOPMENT.md)
- [情況6: 保存進度](./SITUATION-6-SAVE-PROGRESS.md)

### 測試資源
- `backend/tests/conftest.py` - 共用 Fixtures
- `.claude/rules/testing.md` - 測試規則

---

**維護者**: AI 助手 + 開發團隊
**最後更新**: 2025-12-24
**版本**: 2.0
