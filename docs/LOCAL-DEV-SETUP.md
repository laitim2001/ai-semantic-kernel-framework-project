# IPA Platform - 本地開發環境部署指南

本文件提供完整的本地開發環境設置步驟，適用於 Windows 開發環境。

---

## 目錄

1. [系統需求](#系統需求)
2. [快速啟動](#快速啟動)
3. [詳細設置步驟](#詳細設置步驟)
4. [服務說明](#服務說明)
5. [常用命令](#常用命令)
6. [故障排除](#故障排除)

---

## 系統需求

### 必要軟體

| 軟體 | 版本要求 | 用途 |
|------|----------|------|
| Docker Desktop | 最新版 | 容器化基礎設施服務 |
| Python | 3.11+ | 後端 FastAPI 服務 |
| Node.js | 18+ | 前端 React 開發 |
| Git | 最新版 | 版本控制 |

### 可選軟體

| 軟體 | 用途 |
|------|------|
| VS Code | 推薦的 IDE |
| DBeaver | 資料庫管理工具 |
| Redis Insight | Redis 視覺化工具 |

---

## 快速啟動

如果你已經完成過初始設置，使用以下命令快速啟動：

```powershell
# 1. 進入專案目錄
cd C:\Users\rci.ChrisLai\Documents\GitHub\ai-semantic-kernel-framework-project

# 2. 確保 .env 檔案存在於專案根目錄和 backend/ 目錄
# (首次設置請參考詳細設置步驟)

# 3. 啟動基礎設施服務 (PostgreSQL, Redis, RabbitMQ)
# 注意: 使用 -f 指定只啟動核心服務，避免載入 override 檔案
docker-compose -f docker-compose.yml up -d

# 4. 等待服務就緒 (約 30 秒)
docker-compose ps

# 5. 啟動後端 (新開一個終端)
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 6. 啟動前端 (新開一個終端)
cd frontend
npm run dev
```

### 服務訪問網址

| 服務 | 網址 | 說明 |
|------|------|------|
| 前端 | http://localhost:3000 | React 開發伺服器 (Vite) |
| 後端 API | http://localhost:8000 | FastAPI 服務 |
| API 文檔 | http://localhost:8000/docs | Swagger UI |
| RabbitMQ UI | http://localhost:15672 | 帳號: guest / guest |

---

## 詳細設置步驟

### 步驟 1: 環境變數設置

```powershell
# 複製環境變數範本
cd C:\Users\rci.ChrisLai\Documents\GitHub\ai-semantic-kernel-framework-project
Copy-Item .env.example .env

# 重要：同時複製到 backend 目錄 (後端從 backend/ 目錄讀取 .env)
Copy-Item .env backend/.env

# 編輯 .env 檔案，填入必要的設定值
# 重點設定項目：
# - AZURE_OPENAI_ENDPOINT
# - AZURE_OPENAI_API_KEY
# - AZURE_OPENAI_DEPLOYMENT_NAME
```

> ⚠️ **重要**: 後端服務從 `backend/` 目錄運行，需要在該目錄也有一份 `.env` 檔案。

**環境變數說明：**

```ini
# 資料庫 (使用預設值即可)
DB_NAME=ipa_platform
DB_USER=ipa_user
DB_PASSWORD=ipa_password
DB_HOST=localhost
DB_PORT=5432

# Redis (使用預設值即可)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redis_password

# RabbitMQ (使用預設值即可)
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

# Azure OpenAI (必須填入實際值)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
```

### 步驟 2: 啟動 Docker 服務

```powershell
# 確保 Docker Desktop 已啟動

# 啟動核心服務 (使用 -f 避免載入 override 檔案)
docker-compose -f docker-compose.yml up -d

# 查看服務狀態
docker-compose ps

# 預期輸出：
# NAME            STATUS       PORTS
# ipa-postgres    running      0.0.0.0:5432->5432/tcp
# ipa-redis       running      0.0.0.0:6379->6379/tcp
# ipa-rabbitmq    running      0.0.0.0:5672->5672/tcp, 0.0.0.0:15672->15672/tcp
```

**等待服務健康檢查通過：**

```powershell
# 檢查服務健康狀態
docker-compose ps

# 所有服務應顯示 "healthy" 或 "running"
```

### 步驟 3: 設置 Python 後端

```powershell
# 進入後端目錄
cd backend

# 建立虛擬環境 (首次設置)
python -m venv venv

# 啟動虛擬環境
.\venv\Scripts\Activate

# 安裝依賴
pip install -r requirements.txt

# 執行資料庫遷移 (如有需要)
# alembic upgrade head

# 啟動後端服務 (二選一)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# 或者使用 python module 方式 (推薦，避免 PATH 問題)
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**驗證後端服務：**

```powershell
# 健康檢查
curl http://localhost:8000/health

# 預期回應：
# {"status":"healthy","version":"0.2.0"}
# 注意: 如果資料庫連接尚未設置，可能顯示 "degraded"

# 或使用瀏覽器訪問 API 文檔
# http://localhost:8000/docs
```

### 步驟 4: 設置 React 前端

```powershell
# 開啟新的終端視窗

# 進入前端目錄
cd C:\Users\rci.ChrisLai\Documents\GitHub\ai-semantic-kernel-framework-project\frontend

# 安裝依賴 (首次設置)
npm install

# 啟動開發伺服器
npm run dev
```

**驗證前端服務：**

瀏覽器訪問 http://localhost:3000

---

## 服務說明

### 核心基礎設施

| 服務 | 容器名稱 | 連接埠 | 用途 |
|------|----------|--------|------|
| PostgreSQL 16 | ipa-postgres | 5432 | 主資料庫 |
| Redis 7 | ipa-redis | 6379 | 快取與會話 |
| RabbitMQ | ipa-rabbitmq | 5672, 15672 | 訊息佇列 |

### 可選服務 (開發擴展)

使用 override 檔案啟動額外服務：

```powershell
# 啟動包含 n8n 的擴展服務
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d
```

| 服務 | 連接埠 | 用途 |
|------|--------|------|
| n8n | 5678 | 工作流程自動化 (帳號: admin / admin123) |
| Prometheus | 9090 | 指標收集 |
| Grafana | 3001 | 儀表板視覺化 (帳號: admin / admin123) |

### 監控堆疊 (可選)

```powershell
# 啟動包含完整監控的服務
docker-compose --profile monitoring up -d
```

| 服務 | 連接埠 | 用途 |
|------|--------|------|
| Jaeger | 16686 | 分散式追蹤 |
| Prometheus | 9090 | 指標收集 |
| Grafana | 3001 | 儀表板視覺化 |

---

## 常用命令

### Docker 操作

```powershell
# 啟動所有服務
docker-compose up -d

# 停止所有服務
docker-compose down

# 停止並刪除資料 (重置)
docker-compose down -v

# 查看日誌
docker-compose logs -f              # 所有服務
docker-compose logs -f postgres     # 特定服務

# 重啟特定服務
docker-compose restart postgres

# 進入容器
docker exec -it ipa-postgres psql -U ipa_user -d ipa_platform
docker exec -it ipa-redis redis-cli -a redis_password
```

### 後端操作

```powershell
cd backend

# 啟動服務
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 程式碼品質
black .                    # 格式化
isort .                    # 排序 imports
flake8 .                   # Lint 檢查
mypy .                     # 類型檢查

# 測試
pytest                     # 執行所有測試
pytest tests/unit/         # 單元測試
pytest -v --cov=src        # 含覆蓋率
```

### 前端操作

```powershell
cd frontend

# 啟動開發伺服器
npm run dev

# 建置
npm run build

# 測試
npm test
npm run test:coverage

# 類型檢查
npm run typecheck
```

### 資料庫操作

```powershell
# 連線到 PostgreSQL
docker exec -it ipa-postgres psql -U ipa_user -d ipa_platform

# 常用 SQL
\dt                        # 列出所有表
\d table_name              # 表結構
SELECT * FROM agents;      # 查詢資料

# Alembic 遷移
cd backend
alembic upgrade head                          # 執行遷移
alembic revision --autogenerate -m "描述"     # 產生遷移
alembic downgrade -1                          # 回滾一步
```

---

## 故障排除

### Docker 服務無法啟動

```powershell
# 1. 確認 Docker Desktop 已啟動
# 2. 檢查連接埠是否被佔用
netstat -ano | findstr :5432
netstat -ano | findstr :6379
netstat -ano | findstr :5672

# 3. 清理並重新啟動
docker-compose down -v
docker-compose up -d
```

### 後端無法連接資料庫

```powershell
# 1. 確認 PostgreSQL 容器運行中
docker-compose ps

# 2. 檢查健康狀態
docker inspect ipa-postgres | findstr "Health"

# 3. 測試連線
docker exec -it ipa-postgres pg_isready -U ipa_user -d ipa_platform
```

### 前端無法連接後端 API

```powershell
# 1. 確認後端服務運行中
curl http://localhost:8000/health

# 2. 檢查 CORS 設定
# 確認 .env 中的 CORS_ORIGINS 包含前端網址

# 3. 確認 API 路徑正確
# 前端預設連接 http://localhost:8000/api/v1/
```

### Python 套件安裝失敗

```powershell
# 1. 確認使用正確的 Python 版本
python --version  # 應為 3.11+

# 2. 更新 pip
python -m pip install --upgrade pip

# 3. 清理快取重新安裝
pip cache purge
pip install -r requirements.txt
```

### Node.js 套件安裝失敗

```powershell
# 1. 確認 Node.js 版本
node --version  # 應為 18+

# 2. 清理並重新安裝
cd frontend
Remove-Item -Recurse -Force node_modules
Remove-Item package-lock.json
npm install
```

---

## 開發提示

### 推薦的開發流程

1. **每次開發前**：同步最新程式碼 `git pull origin main`
2. **啟動順序**：Docker 服務 → 後端 → 前端
3. **開發時**：後端和前端都使用 hot-reload 模式
4. **提交前**：執行 lint 和測試

### VS Code 推薦擴充

- Python
- Pylance
- ESLint
- Prettier
- Docker
- GitLens
- REST Client

### 終端配置建議

使用 Windows Terminal 開啟多個分頁：
- Tab 1: Docker 日誌 (`docker-compose logs -f`)
- Tab 2: 後端服務 (`uvicorn main:app --reload`)
- Tab 3: 前端服務 (`npm run dev`)
- Tab 4: Git 操作和一般命令

---

## 相關文件

| 文件 | 說明 |
|------|------|
| `CLAUDE.md` | AI 助手使用指南 |
| `docs/02-architecture/technical-architecture.md` | 系統架構 |
| `claudedocs/AI-ASSISTANT-INSTRUCTIONS.md` | AI 工作流程說明 |

---

**最後更新**: 2025-12-02
