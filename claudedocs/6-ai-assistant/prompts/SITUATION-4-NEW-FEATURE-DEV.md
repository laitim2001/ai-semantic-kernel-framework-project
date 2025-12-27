# 🚀 情況4: 新功能開發

> **使用時機**: 開始實際編寫新功能/模組代碼時
> **目標**: 按照計劃高效地完成功能開發
> **適用場景**: Sprint 開發、新功能實作、新模組開發、API 開發

---

## 📋 Prompt 模板 (給開發人員)

```markdown
你好！我要開始開發一個功能。

**功能名稱**: [功能名稱]
**功能描述**: [詳細描述功能需求]

**技術要求**:
- [技術要求 1]
- [技術要求 2]

**相關文件** (如有):
- [相關設計文檔]
- [相關 API 規格]

請幫我：

1. 確認開發計劃
   - 回顧之前的任務準備 (如有)
   - 確認實作步驟

2. 實作功能
   - 按照 IPA Platform 的架構模式開發
   - 遵循現有的代碼風格

3. 編寫測試
   - 為新功能添加單元測試
   - 確保測試覆蓋主要場景

4. 代碼品質檢查
   - 運行 linting
   - 檢查類型

請用中文回答，開始開發。
```

---

## 🤖 AI 助手執行步驟

### Step 1: 確認開發計劃 (1 分鐘)

```bash
# 1. 確認當前分支
Bash: git status
Bash: git branch

# 2. 回顧相關架構
Read: backend/src/api/CLAUDE.md (如開發 API)
Read: backend/src/domain/CLAUDE.md (如開發業務邏輯)
```

### Step 2: 實作功能 (主要時間)

```bash
# IPA Platform 標準開發流程

# 1. Domain Layer (業務邏輯)
# 位置: backend/src/domain/{module}/

Write/Edit: backend/src/domain/{module}/models.py   # Domain 模型
Write/Edit: backend/src/domain/{module}/service.py  # 業務邏輯

# 2. API Layer (HTTP 路由)
# 位置: backend/src/api/v1/{module}/

Write/Edit: backend/src/api/v1/{module}/schemas.py  # Pydantic 模型
Write/Edit: backend/src/api/v1/{module}/routes.py   # FastAPI 路由

# 3. Infrastructure Layer (如需要)
# 位置: backend/src/infrastructure/

Write/Edit: backend/src/infrastructure/database/models/{module}.py
Write/Edit: backend/src/infrastructure/database/repositories/{module}_repository.py
```

### Step 3: 編寫測試 (重要!)

```bash
# 1. 單元測試
# 位置: backend/tests/unit/

Write: backend/tests/unit/domain/test_{module}_service.py
Write: backend/tests/unit/api/v1/test_{module}_routes.py

# 2. 運行測試
Bash: cd backend && pytest tests/unit/domain/test_{module}_service.py -v
Bash: cd backend && pytest tests/unit/api/v1/test_{module}_routes.py -v

# 3. 運行相關模組所有測試
Bash: cd backend && pytest tests/unit/ -k "{module}" -v
```

### Step 4: 代碼品質檢查 (2 分鐘)

```bash
# 1. 格式化
Bash: cd backend && black src/domain/{module}/ src/api/v1/{module}/

# 2. Import 排序
Bash: cd backend && isort src/domain/{module}/ src/api/v1/{module}/

# 3. Linting
Bash: cd backend && flake8 src/domain/{module}/ src/api/v1/{module}/

# 4. 類型檢查 (可選)
Bash: cd backend && mypy src/domain/{module}/ src/api/v1/{module}/
```

---

## 📦 IPA Platform 代碼模板

### Domain Service 模板

```python
# backend/src/domain/{module}/service.py
from typing import List, Optional
from sqlalchemy.orm import Session

from src.infrastructure.database.repositories.{module}_repository import {Module}Repository
from src.core.logging import get_logger

logger = get_logger(__name__)


class {Module}Service:
    """
    {Module} 業務邏輯服務。

    遵循 IPA Platform 標準 Service 模式。
    """

    def __init__(self, db: Session):
        self.db = db
        self.repository = {Module}Repository(db)

    def get_all(self, skip: int = 0, limit: int = 100) -> List[...]:
        """取得所有項目。"""
        return self.repository.get_all(skip=skip, limit=limit)

    def get_by_id(self, id: str) -> Optional[...]:
        """根據 ID 取得單一項目。"""
        return self.repository.get_by_id(id)

    def create(self, data: dict) -> ...:
        """創建新項目。"""
        self._validate_create(data)
        item = self.repository.create(data)
        logger.info(f"Created {module}: {item.id}")
        return item
```

### API Route 模板

```python
# backend/src/api/v1/{module}/routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.domain.{module}.service import {Module}Service
from . import schemas

router = APIRouter(prefix="/{module}", tags=["{Module}"])


@router.get("/", response_model=list[schemas.{Module}Response])
async def list_{module}s(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """列出所有 {module}。"""
    service = {Module}Service(db)
    return service.get_all(skip=skip, limit=limit)


@router.post("/", response_model=schemas.{Module}Response, status_code=status.HTTP_201_CREATED)
async def create_{module}(
    data: schemas.{Module}Create,
    db: Session = Depends(get_db)
):
    """創建新 {module}。"""
    service = {Module}Service(db)
    return service.create(data.dict())
```

---

## ✅ 驗收標準

AI 助手完成開發後應確認：

1. **功能完整**
   - 所有需求都已實現
   - 代碼符合 IPA Platform 架構模式

2. **測試通過**
   - 單元測試全部通過
   - 測試覆蓋主要場景

3. **代碼品質**
   - Black 格式化通過
   - Flake8 無錯誤
   - 無明顯的安全問題

4. **文檔更新** (如需要)
   - API 文檔更新
   - CLAUDE.md 更新

---

## 🔗 相關文檔

### 開發流程指引
- [情況2: 開發前準備](./SITUATION-2-FEATURE-DEV-PREP.md)
- [情況3: 功能增強/修正](./SITUATION-3-FEATURE-ENHANCEMENT.md)
- [情況5: 保存進度](./SITUATION-5-SAVE-PROGRESS.md)

### 架構參考
- `backend/src/api/CLAUDE.md` - API 層設計規範
- `backend/src/domain/CLAUDE.md` - Domain 層設計規範
- `backend/CLAUDE.md` - 後端總體指南

---

**維護者**: AI 助手 + 開發團隊
**最後更新**: 2025-12-27
**版本**: 3.0
