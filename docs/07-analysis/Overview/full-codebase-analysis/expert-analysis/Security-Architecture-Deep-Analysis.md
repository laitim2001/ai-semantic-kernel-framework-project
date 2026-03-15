# Dr. Security -- IPA Platform 安全架構深度分析

**Generated**: 2026-03-15
**Analyst**: Dr. Security (Security Architecture Specialist)
**Scope**: Full backend security architecture review based on source code reading
**Source Files Read**: 18 source files + V8 issue registry (62 issues)

---

## Executive Summary

IPA Platform 的安全架構處於 **Phase 31 Security Hardening 後的半成品狀態**。Sprint 111 引入了全域 JWT 保護 (`protected_router`)，使路由覆蓋率從 7% 躍升至接近 100%，這是顯著的改善。然而，系統性的架構安全問題依然嚴重：**JWT 使用 HS256 對稱演算法且缺乏 Token 撤銷機制**；**MCP 權限模型預設為 `log` 模式（記錄但不阻擋）**；**所有 MCP 伺服器的 AuditLogger 從未被連接**；**沙箱隔離僅為進程級別，缺乏容器/cgroup 強制隔離**；**Rate Limiter 使用 in-memory 儲存，多 worker 部署下各自獨立**。最嚴重的是，20+ 模組的 in-memory 狀態存儲意味著安全審計紀錄、權限決策、HITL 審批紀錄在重啟後全部遺失，構成合規性的根本性障礙。

---

## 1. 認證與授權架構分析

### 1.1 現狀評估

**JWT 實作** (`backend/src/core/security/jwt.py`):
- 使用 `python-jose[cryptography]` 套件，HS256 對稱演算法
- Access Token 預設 60 分鐘過期 (`config.py:133`)
- Refresh Token 固定 7 天過期 (`jwt.py:148`)
- Token Payload 包含 `sub`(user_id)、`role`、`exp`、`iat`

**全域認證中間件** (`backend/src/core/auth.py`):
- Sprint 111 引入 `require_auth` -- 輕量級 JWT 驗證（不查資料庫）
- `protected_router` 透過 `dependencies=[Depends(require_auth)]` 保護所有非公開路由 (`api/v1/__init__.py:126`)
- 公開路由僅 auth 端點（login, register, refresh）

**RBAC 實作** (`backend/src/api/v1/dependencies.py`):
- 四個角色等級：admin, operator, approver, viewer
- `get_current_active_admin` -- 要求 admin 角色 (line 135-156)
- `get_current_operator_or_admin` -- 要求 operator 或 admin (line 159-180)
- `get_current_user` -- 完整 DB 查詢驗證 (line 57-104)

**密碼安全** (`backend/src/core/security/password.py`):
- 使用 `passlib[bcrypt]`，業界標準
- 自動升級舊雜湊 (`deprecated="auto"`)

### 1.2 架構缺陷

**SEC-AUTH-01 [CRITICAL]: JWT 缺乏 Token 撤銷/黑名單機制**
- 證據：搜尋整個 `backend/src` 目錄，找不到 `token_blacklist`、`revoke`、`logout` 相關的 token 撤銷實作
- `jwt.py` 中的 `decode_token()` 僅驗證簽名和過期時間，無撤銷檢查
- 影響：被盜用的 token 在 60 分鐘內持續有效，無法強制登出；Refresh Token 被盜用後 7 天內持續有效
- 攻擊向量：Token 外洩後無法即時撤銷，即使發現帳號被入侵也無法阻止

**SEC-AUTH-02 [HIGH]: HS256 對稱演算法 -- 單一共享密鑰**
- 證據：`config.py:132` -- `jwt_algorithm: str = "HS256"`
- `jwt.py:77-81` -- 編碼和解碼使用同一個 `settings.jwt_secret_key`
- 影響：所有服務共享同一個密鑰，任何能存取密鑰的服務都能偽造 token。在微服務架構中，應使用 RS256/ES256 非對稱演算法
- 風險：密鑰洩漏 = 完整認證體系崩潰

**SEC-AUTH-03 [HIGH]: JWT Secret 預設為空字串**
- 證據：`config.py:131` -- `jwt_secret_key: str = ""`
- `config.py:185-212` 中的 `validate_security_settings()` 會在 production 環境 raise ValueError，但此函數必須被顯式調用
- 搜尋 `main.py` 未發現啟動時自動調用 `validate_security_settings()`
- 影響：開發環境中使用空字串作為 JWT 密鑰，任何人都能偽造 token

**SEC-AUTH-04 [HIGH]: require_auth 不查資料庫 -- 已停用帳戶可能繼續存取**
- 證據：`auth.py:46-97` -- `require_auth` 僅驗證 JWT 簽名，不查詢使用者是否仍然 active
- `dependencies.py:96` -- `get_current_user` 有 `is_active` 檢查，但 `require_auth` 沒有
- `api/v1/__init__.py:126` -- `protected_router` 使用的是 `require_auth`（無 DB 查詢版本）
- 影響：停用帳戶的使用者在 token 過期前仍可存取所有 protected 路由

**SEC-AUTH-05 [MEDIUM]: Refresh Token 與 Access Token 使用相同密鑰和幾乎相同結構**
- 證據：`jwt.py:150-156` -- Refresh token 僅多一個 `"type": "refresh"` 欄位
- `jwt.py:106-118` -- `decode_token()` 不驗證 token type
- 影響：Access Token 的解碼函數可以接受 Refresh Token，反之亦然，可能導致 token 混淆攻擊

**SEC-AUTH-06 [MEDIUM]: RBAC 未應用於破壞性操作**
- 證據：V8 issue H-01 -- cache clear、connector execute、agent unregister 端點未檢查角色
- `protected_router` 僅驗證 "已認證"，不驗證 "有權限"
- 影響：任何 viewer 角色的使用者都能執行管理員級別的破壞性操作

### 1.3 風險等級: **CRITICAL**

### 1.4 建議架構改進

1. **Token 撤銷機制**：實作 Redis-based token blacklist，在 `require_auth` 中檢查
2. **遷移至 RS256**：使用非對稱金鑰對，公鑰驗證，私鑰簽發
3. **啟動時強制安全驗證**：在 `main.py` 的 `create_app()` 中調用 `settings.validate_security_settings()`
4. **require_auth 加入 is_active 快取檢查**：使用 Redis 快取停用帳戶清單
5. **Token type 欄位強制驗證**：`decode_token()` 應區分 access/refresh token
6. **全面 RBAC enforcement**：為每個破壞性端點添加角色檢查 dependency

---

## 2. API 安全架構分析

### 2.1 現狀評估

**Rate Limiting** (`backend/src/middleware/rate_limit.py`):
- 使用 `slowapi`，以 IP 為 key
- 開發環境：1000/minute；生產環境：100/minute
- Login/Register 端點有專門的 10/minute 限制 (`auth/routes.py:69,114`)

**CORS 配置** (`backend/main.py:180-186`):
- `allow_origins` 從 `settings.cors_origins_list` 讀取
- `allow_credentials=True`
- `allow_methods=["*"]`，`allow_headers=["*"]`

**輸入驗證**：
- 使用 Pydantic BaseModel 進行 request body 驗證
- OAuth2PasswordRequestForm 用於 login

**異常處理** (`backend/main.py:189-212`):
- 全域 exception handler
- 開發環境回傳完整錯誤訊息 `str(exc)`
- 生產環境僅回傳 "Internal server error"

### 2.2 架構缺陷

**SEC-API-01 [HIGH]: Rate Limiter 使用 in-memory 儲存**
- 證據：`rate_limit.py:57` -- `storage_uri=None` 註解明確寫道 "Uses in-memory storage; upgrade to Redis in Sprint 119"
- 影響：多 worker 部署（`uvicorn --workers N`）時，每個 worker 有獨立的計數器，實際限制 = N * 配置限制
- 攻擊向量：暴力破解攻擊可在 4 worker 部署中達到 400 req/min 而非預期的 100 req/min

**SEC-API-02 [HIGH]: CORS 過度寬鬆**
- 證據：`main.py:184-185` -- `allow_methods=["*"]`，`allow_headers=["*"]`
- `config.py:138` -- 預設 origins 為 `"http://localhost:3005,http://localhost:8000"`
- 配合 `allow_credentials=True`，如果 origins 被誤設為 `"*"`，將完全暴露認證 cookie
- 影響：攻擊者可利用寬鬆的 CORS 策略進行跨站攻擊

**SEC-API-03 [HIGH]: 開發環境異常洩漏完整堆疊追蹤**
- 證據：`main.py:199-204` -- `"detail": str(exc)` 在 development 模式
- `config.py:27` -- `app_env` 預設為 `"development"`
- 影響：如果生產環境忘記設定 `APP_ENV=production`，所有內部錯誤（包括 SQL 查詢、檔案路徑）將洩漏給攻擊者

**SEC-API-04 [HIGH]: API Key 前綴洩漏**
- 證據：V8 issue C-08 -- AG-UI `/ag-ui/reset` 端點在回應 payload 中包含 Anthropic API key 前綴
- 影響：洩漏部分 API key 資訊，可用於社會工程攻擊或縮小暴力破解範圍

**SEC-API-05 [MEDIUM]: Test 端點未依環境門控**
- 證據：V8 issue H-02 -- AG-UI `/test/*` 路由不受 APP_ENV 環境變數控制
- 影響：生產環境中暴露測試端點，可能被用於繞過正常流程

**SEC-API-06 [MEDIUM]: 缺乏 CSRF 保護**
- 證據：搜尋整個後端代碼庫，未發現 CSRF token 生成或驗證邏輯
- 前端使用 Bearer token 而非 cookie，部分降低風險
- 但 `allow_credentials=True` 的 CORS 配置暗示可能使用 cookie-based 認證場景

### 2.3 風險等級: **HIGH**

### 2.4 建議架構改進

1. **Rate Limiter 遷移到 Redis**：將 `storage_uri` 設為 `settings.redis_url`
2. **CORS 收緊**：明確列出允許的 HTTP methods，移除 `allow_headers=["*"]`
3. **強制 APP_ENV 在生產環境**：啟動時檢查，缺少時拒絕啟動
4. **移除 API key 洩漏**：從所有回應中清除任何 credential 前綴
5. **環境門控 test 端點**：使用 `if settings.app_env != "production"` 條件

---

## 3. 沙箱與隔離架構分析

### 3.1 現狀評估

**沙箱架構** (`backend/src/core/sandbox/`):
- `ProcessSandboxConfig` -- 定義進程隔離配置 (`config.py`)
- `SandboxOrchestrator` -- Worker 進程池管理 (`orchestrator.py`)
- `SandboxWorker` -- 個別 subprocess 管理，JSON-RPC over stdin/stdout (`worker.py`)

**環境隔離措施** (`config.py:73-138`):
- 明確的環境變數白名單（允許 ANTHROPIC_API_KEY、PATH 等）
- 阻擋前綴清單（DB_、REDIS_、AWS_、AZURE_、SECRET_、JWT_ 等）
- User ID 清理防止路徑遍歷 (`config.py:221-244`)

**資源限制** (`config.py:56-70`):
- Worker timeout: 300 秒
- Max workers: 10
- Max requests per worker: 100（超過後回收）
- Idle timeout: 300 秒

### 3.2 架構缺陷

**SEC-SANDBOX-01 [CRITICAL]: 沙箱為模擬實作 -- 無真正的進程隔離**
- 證據：V8 issue H-09 -- "Sandbox is simulated -- no real process isolation, container usage, or enforcement"
- `worker.py:147-156` -- 使用 `subprocess.Popen()`，無 cgroup、namespace、seccomp 限制
- 沙箱進程與主進程在同一個 OS 使用者下運行
- 影響：惡意代碼可存取主機檔案系統、網路、其他進程

**SEC-SANDBOX-02 [HIGH]: ANTHROPIC_API_KEY 傳入沙箱環境**
- 證據：`config.py:76` -- `"ANTHROPIC_API_KEY"` 在 `allowed_env_vars` 清單中
- `config.py:269` -- 驗證函數甚至要求此變數必須存在
- 影響：沙箱進程可直接存取 Anthropic API key，若沙箱被逃逸，API key 即被竊取
- 設計矛盾：環境變數過濾的目的是限制敏感資訊，但主要的 API 密鑰卻被允許通過

**SEC-SANDBOX-03 [HIGH]: 無檔案系統限制強制執行**
- 證據：`worker.py:147-156` -- subprocess 的 `cwd` 設為沙箱目錄，但無 chroot 或 mount namespace
- 進程可透過 `../` 或絕對路徑存取任何檔案
- `config.py:204-206` 中的 user_id sanitization 僅防止沙箱目錄本身的路徑遍歷

**SEC-SANDBOX-04 [MEDIUM]: 無記憶體/CPU 資源限制**
- 證據：`subprocess.Popen()` 呼叫中無 `ulimit`、`cgroup`、或 `resource` 模組設定
- 影響：惡意沙箱進程可消耗無限記憶體/CPU，導致 DoS

### 3.3 風險等級: **CRITICAL**

### 3.4 建議架構改進

1. **容器化沙箱**：使用 Docker/Podman 或 gVisor 提供真正的隔離
2. **API Key 代理模式**：沙箱進程不直接持有 API key，而是透過代理服務轉發 API 呼叫
3. **seccomp + cgroup**：即使不使用容器，也應設定系統呼叫過濾和資源限制
4. **chroot 或 mount namespace**：限制檔案系統存取範圍

---

## 4. MCP 安全模型分析

### 4.1 現狀評估

**權限管理** (`backend/src/integrations/mcp/security/permissions.py`):
- `PermissionManager` -- RBAC 風格，支援 glob 模式匹配
- 四級權限：NONE(0) < READ(1) < EXECUTE(2) < ADMIN(3)
- 支援 deny list、priority-based 策略評估、動態條件

**權限檢查器** (`backend/src/integrations/mcp/security/permission_checker.py`):
- `MCPPermissionChecker` -- 集中式權限檢查
- 兩種模式：`log`（僅記錄，不阻擋）和 `enforce`（阻擋未授權操作）
- 預設模式由 `MCP_PERMISSION_MODE` 環境變數控制，**預設為 `log`**

**Command Whitelist** (`backend/src/integrations/mcp/security/command_whitelist.py`):
- 三層命令安全：allowed（白名單立即執行）、blocked（危險命令拒絕）、requires_approval（需 HITL 審批）
- 相當完善的阻擋模式清單（27 個 regex 模式）

**Audit Logger** (`backend/src/integrations/mcp/security/audit.py`):
- 完整的審計事件模型和儲存抽象
- InMemoryAuditStorage（開發用）和 RedisAuditStorage（生產用）
- 敏感資料清理功能 (`_sanitize_arguments`)

### 4.2 架構缺陷

**SEC-MCP-01 [CRITICAL]: 權限預設為 `log` 模式 -- 未授權操作可繼續執行**
- 證據：`permission_checker.py:52` -- `self._mode = os.environ.get("MCP_PERMISSION_MODE", "log")`
- `permission_checker.py:153-158` -- log 模式下 `check_tool_permission` 回傳 `allowed` (False)，但呼叫端不一定檢查回傳值
- 影響：即使權限檢查回傳 denied，操作仍會繼續執行，僅留下一條 WARNING 日誌

**SEC-MCP-02 [CRITICAL]: AuditLogger 從未被連接到任何 MCP 伺服器**
- 證據：搜尋整個 `backend/src/integrations/mcp/servers` 目錄，`set_audit_logger` 無任何匹配結果
- 8 個 MCP 伺服器都設定了 `MCPPermissionChecker`，但無一設定 AuditLogger
- `AuditLogger` 類別完整實作但從未被實例化和使用
- 影響：所有 MCP 工具執行（包括 Shell 命令、VM 操作、檔案存取）完全無審計紀錄

**SEC-MCP-03 [HIGH]: 開發環境預設全域 ADMIN 權限**
- 證據：`permission_checker.py:70-78` -- 當 `APP_ENV` 為 development 或 testing 時，自動添加 `PermissionLevel.ADMIN` 的全域策略
- 影響：開發環境中任何使用者可執行任何 MCP 工具（包括 `run_command`），無任何限制

**SEC-MCP-04 [HIGH]: Azure `run_command` 工具無命令內容驗證**
- 證據：V8 issue H-13 -- 即使在 Level 3 (ADMIN) 下，Azure VM 的 `run_command` 工具不驗證命令內容
- `CommandWhitelist` 存在於 Shell/SSH 伺服器，但 Azure VM `run_command` 未使用
- 影響：可在 Azure VM 上執行任意破壞性命令

**SEC-MCP-05 [HIGH]: 無使用者匹配策略時回退為檢查所有策略**
- 證據：`permissions.py:317-319` -- `if not applicable_policies: applicable_policies = list(self._policies.values())`
- 影響：當使用者/角色未明確分配策略時，系統會評估所有已定義的策略，可能意外授予權限

**SEC-MCP-06 [MEDIUM]: 時間範圍條件解析失敗時預設允許**
- 證據：`permissions.py:401-402` -- `except Exception: return True`
- 影響：畸形的時間條件配置將導致條件被跳過（視為通過）

### 4.3 風險等級: **CRITICAL**

### 4.4 建議架構改進

1. **立即將 MCP_PERMISSION_MODE 預設改為 `enforce`**（至少在 production 環境）
2. **連接 AuditLogger**：在每個 MCP server 的 `__init__` 中設定 audit logger
3. **Azure run_command 加入 CommandWhitelist**
4. **無策略匹配時預設 DENY**：移除回退到所有策略的邏輯
5. **條件評估失敗應預設拒絕**，而非預設允許

---

## 5. 資料保護與加密分析

### 5.1 現狀評估

**密碼雜湊**：bcrypt via passlib -- 業界標準，無問題
**JWT 簽發**：HS256 -- 見第 1 節分析
**敏感設定**：Pydantic Settings 從 `.env` 載入，`lru_cache` 確保單例

**Security Audit Report** (`backend/src/core/security/audit_report.py`):
- 靜態/硬編碼的合規報告，非實際掃描結果
- OWASP 合規檢查全部回傳硬編碼的 `PASS` 或 `PARTIAL`（`audit_report.py:163-264`）
- 聲稱 "Role-based access control implemented with JWT validation"、"AES-256 encryption"、"TLS 1.3" 等，但為硬編碼字串，非實際驗證

### 5.2 架構缺陷

**SEC-DATA-01 [CRITICAL]: 安全審計報告為硬編碼假資料**
- 證據：`audit_report.py:163-264` -- 所有 10 個 OWASP 合規檢查結果為硬編碼值
- `_review_authentication()` (line 267-291) -- 回傳硬編碼的 `"rate_limiting": True, "max_attempts": 5`，但實際系統不一定有這些實作
- 影響：產生虛假的合規感。如果此報告被用於審計目的，將構成合規性詐欺

**SEC-DATA-02 [CRITICAL]: 20+ 模組的安全相關資料使用 in-memory 儲存**
- 證據：V8 issue C-01 -- ApprovalStorage、AuditDecisionRecords、ChatSession 等全部使用 in-memory dict
- MCP AuditLogger 預設使用 `InMemoryAuditStorage`（`audit.py:455`）
- 影響：伺服器重啟後，所有審批紀錄、審計日誌、安全事件完全遺失。違反大多數合規框架的資料保留要求

**SEC-DATA-03 [HIGH]: SQL Injection 風險 -- f-string 表名插值**
- 證據：V8 issue C-07 -- `integrations/agent_framework/` 中的 PostgreSQL memory store 和 checkpoint store 使用 f-string 插入表名
- 影響：如果表名受使用者輸入影響，可注入任意 SQL

**SEC-DATA-04 [MEDIUM]: 日誌中洩漏使用者郵件地址**
- 證據：`auth/routes.py:92` -- `logger.info(f"User registered: {user.email}")`
- `auth/routes.py:136` -- `logger.info(f"User logged in: {user.email}")`
- `auth/routes.py:146` -- `logger.warning(f"Login failed for: {form_data.username}")`
- 影響：PII 寫入日誌，在集中日誌系統中可能被未授權人員查看

**SEC-DATA-05 [MEDIUM]: `datetime.utcnow()` deprecated 使用**
- 證據：`jwt.py:64,66,74,148,154` -- 多處使用 `datetime.utcnow()`
- Python 3.12+ 已棄用此方法，未來版本可能移除
- 影響：token 時間戳精確性和相容性風險

### 5.3 風險等級: **CRITICAL**

### 5.4 建議架構改進

1. **重寫 Security Audit Report**：改為實際掃描而非硬編碼值
2. **系統性持久化遷移**：優先遷移 approval、audit、MCP audit 到 PostgreSQL/Redis
3. **修復 SQL Injection**：使用參數化查詢或 SQLAlchemy ORM
4. **日誌 PII 清理**：實作日誌過濾器，清除或遮蔽敏感資訊
5. **遷移到 `datetime.now(timezone.utc)`**

---

## 6. 系統性安全架構問題

### 6.1 安全債務地圖

```
[CRITICAL 安全債務]
├── JWT 無撤銷機制 .................. SEC-AUTH-01
├── MCP 權限 log-only 模式 ......... SEC-MCP-01
├── MCP AuditLogger 未連接 ......... SEC-MCP-02
├── 沙箱無真正隔離 .................. SEC-SANDBOX-01
├── 安全審計報告為假資料 ............ SEC-DATA-01
├── 20+ 模組安全資料 in-memory ..... SEC-DATA-02
│
[HIGH 安全債務]
├── HS256 對稱演算法 ................ SEC-AUTH-02
├── JWT Secret 預設空字串 ........... SEC-AUTH-03
├── require_auth 不查 is_active ..... SEC-AUTH-04
├── Rate Limiter in-memory .......... SEC-API-01
├── CORS 過度寬鬆 .................. SEC-API-02
├── 異常訊息洩漏 .................... SEC-API-03
├── API Key 前綴洩漏 ................ SEC-API-04
├── ANTHROPIC_API_KEY 傳入沙箱 ..... SEC-SANDBOX-02
├── 沙箱無檔案系統限制 .............. SEC-SANDBOX-03
├── MCP 開發環境全域 ADMIN .......... SEC-MCP-03
├── Azure run_command 無驗證 ........ SEC-MCP-04
├── MCP 無策略回退為全部評估 ....... SEC-MCP-05
├── SQL Injection 風險 .............. SEC-DATA-03
│
[MEDIUM 安全債務]
├── Token type 不區分 ............... SEC-AUTH-05
├── RBAC 未覆蓋破壞性操作 .......... SEC-AUTH-06
├── Test 端點未門控 ................. SEC-API-05
├── 無 CSRF 保護 ................... SEC-API-06
├── 沙箱無資源限制 .................. SEC-SANDBOX-04
├── MCP 時間條件失敗預設允許 ........ SEC-MCP-06
├── 日誌 PII 洩漏 .................. SEC-DATA-04
└── datetime.utcnow deprecated ...... SEC-DATA-05
```

### 6.2 攻擊面分析

**攻擊面 1: Token 竊取 + 持久化存取**
```
攻擊路徑: XSS/MITM → 竊取 JWT → 60分鐘無限制存取
防禦缺口: 無 Token 撤銷、無 IP 綁定、require_auth 不查 DB
嚴重度: CRITICAL
```

**攻擊面 2: MCP 工具執行鏈**
```
攻擊路徑: 認證後 → 呼叫 MCP Shell/SSH 工具 → 權限僅 log 不阻擋 → 執行任意命令 → 無審計紀錄
防禦缺口: log-only 模式 + AuditLogger 未連接 + 開發環境 ADMIN 權限
嚴重度: CRITICAL
```

**攻擊面 3: 沙箱逃逸**
```
攻擊路徑: 提交惡意代碼 → 沙箱執行 → 無容器隔離 → 存取主機 → 讀取 ANTHROPIC_API_KEY 和其他環境變數
防禦缺口: subprocess 無隔離 + API Key 在沙箱環境中
嚴重度: CRITICAL
```

**攻擊面 4: Rate Limit 繞過 + 暴力破解**
```
攻擊路徑: 多 worker 部署 → 每個 worker 獨立計數 → 有效 rate limit = N * 配置值
防禦缺口: in-memory rate limiter
嚴重度: HIGH
```

**攻擊面 5: 合規性風險**
```
攻擊路徑: 安全審計 → 提交硬編碼的"PASS"報告 → 真實漏洞未被發現
防禦缺口: 假合規報告 + in-memory 審計紀錄（重啟遺失）
嚴重度: CRITICAL (合規層面)
```

### 6.3 零信任差距

| 零信任原則 | 現狀 | 差距 |
|-----------|------|------|
| **永不信任，總是驗證** | `require_auth` 不查 DB，信任 token 中的 role claim | 停用帳戶仍可存取 |
| **最小權限** | MCP 開發環境預設 ADMIN；破壞性操作無 RBAC | 過度授權 |
| **假設被入侵** | 無 token 撤銷；審計紀錄 in-memory | 入侵後無法回應 |
| **明確驗證每個請求** | 全域 JWT 驗證已實作（Sprint 111） | 已改善但仍需 DB 驗證 |
| **限制爆炸半徑** | 沙箱無真正隔離；共享 HS256 密鑰 | 單點突破 = 全面失陷 |
| **自動化安全回應** | 無自動化安全事件回應機制 | 完全手動 |

---

## 7. 優先修復路線圖

### Phase A: 緊急修復 (1-2 Sprints) -- 阻擋主動攻擊向量

| 優先級 | Issue | 修復行動 | 複雜度 |
|--------|-------|---------|--------|
| P0 | SEC-MCP-01 | 將 `MCP_PERMISSION_MODE` 預設改為 `enforce` (production) | 1 行 |
| P0 | SEC-API-04 / C-08 | 從 AG-UI reset 回應移除 API key 前綴 | 1 行 |
| P0 | SEC-DATA-03 / C-07 | 修復 f-string SQL injection -- 改用參數化查詢 | 2 檔案 |
| P0 | SEC-AUTH-03 | 在 `main.py create_app()` 中調用 `validate_security_settings()` | 1 行 |
| P1 | SEC-MCP-02 | 連接 AuditLogger 到所有 8 個 MCP 伺服器 | 8 檔案，每檔 ~3 行 |
| P1 | SEC-API-05 / H-02 | Gate test 端點: `if settings.app_env != "production"` | ~5 行 |
| P1 | SEC-AUTH-04 | 在 `require_auth` 中加入 Redis-cached is_active 檢查 | ~20 行 |

### Phase B: 架構強化 (3-5 Sprints) -- 修復系統性弱點

| 優先級 | Issue | 修復行動 | 複雜度 |
|--------|-------|---------|--------|
| P1 | SEC-AUTH-01 | 實作 Redis-based token blacklist + /logout 端點 | 中 |
| P1 | SEC-API-01 / H-14 | Rate Limiter 遷移到 Redis storage | 低（改配置） |
| P1 | SEC-AUTH-06 / H-01 | 為所有破壞性端點添加 RBAC dependency | 中 |
| P2 | SEC-AUTH-02 | JWT 從 HS256 遷移到 RS256 | 中高 |
| P2 | SEC-AUTH-05 | Token type 欄位強制驗證（access vs refresh） | 低 |
| P2 | SEC-MCP-05 | 無策略匹配時預設 DENY，移除 fallback 邏輯 | 低 |
| P2 | SEC-MCP-06 | 條件評估失敗改為預設拒絕 | 1 行 |
| P2 | SEC-DATA-01 | 重寫 Security Audit Report 為實際掃描 | 高 |

### Phase C: 深度防禦 (5-10 Sprints) -- 零信任目標

| 優先級 | Issue | 修復行動 | 複雜度 |
|--------|-------|---------|--------|
| P2 | SEC-SANDBOX-01 | 容器化沙箱（Docker/gVisor） | 高 |
| P2 | SEC-SANDBOX-02 | API Key 代理模式 | 中 |
| P2 | SEC-DATA-02 / C-01 | 系統性 in-memory → persistent 遷移 | 非常高 |
| P3 | SEC-API-02 | CORS 策略收緊 | 低 |
| P3 | SEC-API-06 | CSRF 保護（如需 cookie-based 場景） | 中 |
| P3 | SEC-SANDBOX-03/04 | seccomp + cgroup 資源限制 | 中 |
| P3 | SEC-DATA-04 | 日誌 PII 過濾器 | 低 |
| P3 | SEC-MCP-03 | 開發環境也應使用受限策略（非 ADMIN） | 低 |

---

## Appendix: Issue Cross-Reference

| 本報告 Issue | V8 Issue Registry | 狀態 |
|-------------|-------------------|------|
| SEC-AUTH-01 | (新發現) | 未修復 |
| SEC-AUTH-02 | (新發現) | 未修復 |
| SEC-AUTH-03 | (新發現) | 未修復 |
| SEC-AUTH-04 | (新發現) | 未修復 |
| SEC-AUTH-05 | (新發現) | 未修復 |
| SEC-AUTH-06 | H-01 | 未修復 |
| SEC-API-01 | H-14 | 未修復 |
| SEC-API-02 | (新發現) | 未修復 |
| SEC-API-03 | (新發現) | 未修復 |
| SEC-API-04 | C-08 | 未修復 |
| SEC-API-05 | H-02 | 未修復 |
| SEC-API-06 | (新發現) | 未修復 |
| SEC-SANDBOX-01 | H-09 | 未修復 |
| SEC-SANDBOX-02 | (新發現) | 未修復 |
| SEC-SANDBOX-03 | (新發現) | 未修復 |
| SEC-SANDBOX-04 | (新發現) | 未修復 |
| SEC-MCP-01 | H-07 | 未修復 |
| SEC-MCP-02 | H-06 | 未修復 |
| SEC-MCP-03 | (新發現) | 未修復 |
| SEC-MCP-04 | H-13 | 未修復 |
| SEC-MCP-05 | M-19 | 未修復 |
| SEC-MCP-06 | (新發現) | 未修復 |
| SEC-DATA-01 | (新發現) | 未修復 |
| SEC-DATA-02 | C-01 | 未修復 |
| SEC-DATA-03 | C-07 | 未修復 |
| SEC-DATA-04 | (新發現) | 未修復 |
| SEC-DATA-05 | M-01 | 未修復 |

**統計**: 27 個安全問題，其中 **14 個為本次新發現**（V8 issue registry 未收錄），13 個與 V8 已知問題交叉驗證。

---

*Report generated by Dr. Security -- Security Architecture Deep Analysis*
*Based on direct source code reading of 18 files + V8 Issue Registry cross-reference*
