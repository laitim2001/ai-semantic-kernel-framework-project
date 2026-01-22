# 🆕 情況7: 新開發環境設置 - 完整環境初始化指引

> **使用時機**: 新開發者加入團隊、重新安裝開發環境、資料庫重建
> **目標**: 從零開始完整設置 IPA Platform 開發環境
> **前置條件**: 已安裝 Python 3.13、Docker Desktop、Node.js 18+

---

## 📋 Prompt 模板 (給開發人員)

```markdown
請幫我設置 IPA Platform 的新開發環境。

執行步驟:
1. 檢查系統環境 (Python、Docker、Node.js)
2. 安裝 Python 依賴
3. 初始化資料庫和執行遷移
4. 安裝前端依賴
5. 啟動並驗證所有服務

如有任何問題，請提供詳細的排錯方案。
```

---

## 🤖 AI 助手執行步驟

### Step 1: 環境檢查清單

```bash
# Python 版本檢查 (需要 3.13)
py -0p
# 預期: 應該看到 Python 3.13 可用

# Docker Desktop 狀態
docker --version
docker ps

# Node.js 版本 (需要 18+)
node --version
npm --version
```

### Step 2: 克隆倉庫和環境設定

```bash
# 克隆倉庫 (如尚未克隆)
git clone https://github.com/your-org/ai-semantic-kernel-framework-project.git
cd ai-semantic-kernel-framework-project

# 複製環境變數範例檔
cp .env.example .env
```

### Step 3: Python 依賴安裝

```bash
cd backend

# 安裝依賴 (確保使用 Python 3.13)
py -3.13 -m pip install -r requirements.txt

# 驗證關鍵依賴版本
py -3.13 -c "import bcrypt; print(f'bcrypt: {bcrypt.__version__}')"
py -3.13 -c "import passlib; print(f'passlib: {passlib.__version__}')"
```

### Step 4: 資料庫初始化與遷移

```bash
# 啟動 Docker 服務 (PostgreSQL, Redis, RabbitMQ)
cd ..
python scripts/dev.py start docker

# 等待服務健康檢查通過 (約 10 秒)
docker-compose ps

# 執行資料庫遷移
cd backend
py -3.13 -m alembic upgrade head
```

### Step 5: 前端依賴安裝

```bash
cd ../frontend
npm install
```

### Step 6: 服務啟動驗證

```bash
cd ..
python scripts/dev.py start

# 驗證所有服務
python scripts/dev.py status
```

### Step 7: 環境驗證腳本

```bash
# 運行完整環境驗證
py -3.13 backend/scripts/verify_env.py
```

---

## ⚠️ 常見問題排解

### 問題 1: bcrypt/passlib 版本不兼容

**症狀**:
- `AttributeError: module 'bcrypt' has no attribute '__about__'`
- 認證 API 返回 500 錯誤

**根因**: bcrypt 5.x 與 passlib 1.7.4 不兼容

**診斷**:
```bash
py -3.13 -c "import bcrypt; print(bcrypt.__version__)"
# 如果顯示 5.x，需要降級
```

**解決方案**:
```bash
py -3.13 -m pip uninstall bcrypt -y
py -3.13 -m pip install "bcrypt>=4.0.0,<5.0.0"
```

**預防**: `requirements.txt` 已鎖定版本範圍 `bcrypt>=4.0.0,<5.0.0`

---

### 問題 2: 資料庫欄位與 ORM 模型不匹配

**症狀**:
- `UndefinedColumnError: column users.hashed_password does not exist`
- 資料庫實際欄位名為 `password_hash`

**診斷**:
```bash
py -3.13 -c "
from sqlalchemy import create_engine, inspect
import os
from dotenv import load_dotenv
load_dotenv()
db_url = os.getenv('DATABASE_URL', 'postgresql://ipa_user:ipa_password@localhost:5432/ipa_platform')
engine = create_engine(db_url)
inspector = inspect(engine)
print('Users columns:', [c['name'] for c in inspector.get_columns('users')])
"
```

**解決方案 A**: 執行 Alembic 遷移 (推薦)
```bash
cd backend && py -3.13 -m alembic upgrade head
```

**解決方案 B**: 手動 SQL 修復
```sql
-- 連接到資料庫後執行
ALTER TABLE users RENAME COLUMN password_hash TO hashed_password;
ALTER TABLE users RENAME COLUMN name TO full_name;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP WITH TIME ZONE;
```

---

### 問題 3: sessions 表不存在

**症狀**:
- `UndefinedTableError: relation "sessions" does not exist`
- User relationships 載入時報錯

**根因**: 新表未創建，Alembic 遷移可能有依賴問題

**診斷**:
```bash
py -3.13 -c "
from sqlalchemy import create_engine, inspect
import os
from dotenv import load_dotenv
load_dotenv()
db_url = os.getenv('DATABASE_URL', 'postgresql://ipa_user:ipa_password@localhost:5432/ipa_platform')
engine = create_engine(db_url)
inspector = inspect(engine)
print('Tables:', inspector.get_table_names())
"
```

**解決方案 A**: 執行 Alembic 遷移
```bash
cd backend && py -3.13 -m alembic upgrade head
```

**解決方案 B**: 手動創建表
```sql
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
```

---

### 問題 4: User relationships 載入錯誤

**症狀**:
- `MissingGreenlet: greenlet_spawn has not been called`
- 相關表不存在時觸發

**根因**: SQLAlchemy `lazy="selectin"` 自動加載不存在的表

**臨時解決方案** (修改 ORM 模型):
```python
# 在 backend/src/infrastructure/database/models/user.py
# 將 lazy="selectin" 改為 lazy="noload"

sessions = relationship(
    "Session",
    back_populates="user",
    lazy="noload"  # 臨時禁用自動加載
)
```

**正式解決方案**: 確保所有相關表都已創建
```bash
py -3.13 -m alembic upgrade head
```

---

### 問題 5: Alembic 遷移失敗

**症狀**:
- `alembic upgrade head` 報錯
- 遷移版本衝突

**診斷**:
```bash
# 查看當前遷移狀態
cd backend && py -3.13 -m alembic current

# 查看遷移歷史
py -3.13 -m alembic history
```

**解決方案 A**: 標記已應用的遷移 (如果資料庫已手動修改)
```bash
py -3.13 -m alembic stamp head
```

**解決方案 B**: 降級後重新升級
```bash
py -3.13 -m alembic downgrade base
py -3.13 -m alembic upgrade head
```

**⚠️ 警告**: 方案 B 會刪除所有資料，僅適用於開發環境

---

### 問題 6: 環境變數未設定

**症狀**:
- `KeyError: 'DATABASE_URL'`
- 連接外部服務失敗

**診斷**:
```bash
py -3.13 -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('DATABASE_URL:', os.getenv('DATABASE_URL', 'NOT SET'))
print('AZURE_OPENAI_ENDPOINT:', os.getenv('AZURE_OPENAI_ENDPOINT', 'NOT SET'))
"
```

**解決方案**:
```bash
# 確保 .env 檔案存在且內容正確
cp .env.example .env

# 編輯 .env 設定必要值
# DATABASE_URL=postgresql://ipa_user:ipa_password@localhost:5432/ipa_platform
# AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com/
# AZURE_OPENAI_API_KEY=xxx
```

---

## 🔧 環境驗證腳本

### 使用方式

```bash
py -3.13 backend/scripts/verify_env.py
```

### 預期輸出 (全部通過)

```
============================================================
IPA Platform 環境驗證
============================================================

[Python 環境]
✓ Python 版本: 3.13.x
✓ bcrypt 版本: 4.x.x (兼容)
✓ passlib 版本: 1.7.x
✓ agent_framework 已安裝

[資料庫]
✓ 連接成功: PostgreSQL
✓ users 表結構正確
✓ sessions 表存在

[環境變數]
✓ DATABASE_URL 已設定
✓ AZURE_OPENAI_ENDPOINT 已設定

============================================================
驗證結果: 全部通過 ✓
============================================================
```

### 錯誤輸出示例

```
[Python 環境]
✗ bcrypt 版本: 5.0.0 (不兼容 passlib)
  → 修復: py -3.13 -m pip install "bcrypt>=4.0.0,<5.0.0"

[資料庫]
✗ users 表缺少欄位: hashed_password
  → 修復: 執行 alembic upgrade head 或參考手動 SQL

============================================================
驗證結果: 2 個問題需要修復
============================================================
```

---

## 📊 完整設置流程圖

```
┌─────────────────────────────────────────────────────────────┐
│                  新開發環境設置流程                           │
└─────────────────────────────────────────────────────────────┘

  1. 系統環境檢查
     ┌──────────┐   ┌──────────┐   ┌──────────┐
     │ Python   │   │  Docker  │   │  Node.js │
     │  3.13    │   │ Desktop  │   │   18+    │
     └────┬─────┘   └────┬─────┘   └────┬─────┘
          │              │              │
          └──────────────┼──────────────┘
                         │
                         ▼
  2. 倉庫設置
     ┌─────────────────────────────────────────┐
     │  git clone + cp .env.example .env       │
     └─────────────────┬───────────────────────┘
                       │
                       ▼
  3. 依賴安裝 (並行)
     ┌──────────────────┐   ┌──────────────────┐
     │ Backend (Python) │   │ Frontend (Node)  │
     │ pip install -r   │   │   npm install    │
     └────────┬─────────┘   └────────┬─────────┘
              │                      │
              └──────────┬───────────┘
                         │
                         ▼
  4. 基礎設施啟動
     ┌─────────────────────────────────────────┐
     │        Docker Services                  │
     │  PostgreSQL + Redis + RabbitMQ          │
     └─────────────────┬───────────────────────┘
                       │
                       ▼
  5. 資料庫遷移
     ┌─────────────────────────────────────────┐
     │        alembic upgrade head             │
     └─────────────────┬───────────────────────┘
                       │
                       ▼
  6. 環境驗證
     ┌─────────────────────────────────────────┐
     │     verify_env.py (自動檢測問題)          │
     └─────────────────┬───────────────────────┘
                       │
                       ▼
  7. 服務啟動
     ┌─────────────────────────────────────────┐
     │     python scripts/dev.py start         │
     └─────────────────────────────────────────┘
```

---

## ✅ 驗收標準

新環境設置成功後，確認：

1. **環境驗證腳本通過**
   ```bash
   py -3.13 backend/scripts/verify_env.py
   # 應顯示 "全部通過"
   ```

2. **所有服務運行中**
   ```bash
   python scripts/dev.py status
   # 所有服務顯示綠色
   ```

3. **API 可訪問**
   ```bash
   curl http://localhost:8000/health
   # 返回 200 OK
   ```

4. **認證功能正常**
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email": "test@example.com", "password": "testpass123", "full_name": "Test User"}'
   # 應返回用戶資料，不是 500 錯誤
   ```

---

## 🔗 相關文檔

### 日常開發
- [情況6: 服務啟動](./SITUATION-6-SERVICE-STARTUP.md) - 每日服務啟動
- [情況1: 專案入門](./SITUATION-1-PROJECT-ONBOARDING.md) - 了解專案結構

### 技術文檔
- [CLAUDE.md](../../../CLAUDE.md) - 專案總覽
- [Backend Rules](../../../.claude/rules/backend-python.md) - Python 開發規範

---

## 📝 2026-01-16 事件回顧 (供參考)

此文檔基於以下實際問題創建：

| 問題 | 根因 | 解決方案 |
|------|------|----------|
| bcrypt 5.x 與 passlib 不兼容 | requirements.txt 只有下限約束 | 鎖定 `bcrypt>=4.0.0,<5.0.0` |
| `users.hashed_password` 欄位不存在 | 資料庫欄位名為 `password_hash`，遷移未執行 | SQL 重命名欄位 |
| `sessions` 表不存在 | 新表未創建 | 手動創建表 |
| User relationships 載入錯誤 | `lazy="selectin"` 自動加載不存在的表 | 暫改為 `lazy="noload"` |

---

**維護者**: AI 助手 + 開發團隊
**最後更新**: 2026-01-16
**版本**: 1.0
