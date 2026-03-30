# IPA Platform Security Architecture — V9 Deep Analysis

> **Scope**: 6-Layer Defense-in-Depth security model across the entire IPA Platform
> **Date**: 2026-03-30
> **Method**: Source code reading + V9 layer report synthesis + cross-cutting analysis
> **Companion**: `cross-cutting-analysis.md` Section 1 (summary); this document provides full depth

---

## Table of Contents

1. [Defense-in-Depth Overview](#1-defense-in-depth-overview)
2. [Layer 1: JWT Authentication](#2-layer-1-jwt-authentication)
3. [Layer 2: RBAC Authorization](#3-layer-2-rbac-authorization)
4. [Layer 3: PromptGuard](#4-layer-3-promptguard)
5. [Layer 4: ToolGateway](#5-layer-4-toolgateway)
6. [Layer 5: Sandbox](#6-layer-5-sandbox)
7. [Layer 6: Audit Trail](#7-layer-6-audit-trail)
8. [Risk Assessment Model](#8-risk-assessment-model)
9. [Known Security Issues & Risk Registry](#9-known-security-issues--risk-registry)
10. [Recommendations](#10-recommendations)

---

## 1. Defense-in-Depth Overview

IPA Platform employs a 6-layer Defense-in-Depth architecture. Each layer addresses a distinct security concern. Requests entering from external sources must pass through each layer before reaching core business logic and infrastructure.

```
+---------------------------------------------------------------------------------+
|                  IPA Platform 六層縱深防禦架構                                    |
+---------------------------------------------------------------------------------+
|                                                                                 |
|  外部請求 (瀏覽器 / API Client / Webhook)                                      |
|     |                                                                           |
|     v                                                                           |
|  +----------------------------------------------------------------------+      |
|  |  第一層: JWT 身份驗證 (Authentication)                                 |      |
|  |  +---------------------------------------------------------------+   |      |
|  |  |  core/security/jwt.py                                          |   |      |
|  |  |  演算法: HS256 | 密鑰: pydantic Settings                       |   |      |
|  |  |  Access Token TTL: 可設定 | Refresh Token TTL: 7 天             |   |      |
|  |  |  1 public router + 46 protected routers                        |   |      |
|  |  +---------------------------------------------------------------+   |      |
|  +--------------------------------------+-------------------------------+      |
|                                         | [ok] 身份已驗證                       |
|                                         v                                       |
|  +----------------------------------------------------------------------+      |
|  |  第二層: RBAC 權限控制 (Authorization)                                 |      |
|  |  +---------------------------------------------------------------+   |      |
|  |  |  core/security/rbac.py + tool_gateway.py + mcp/permissions.py  |   |      |
|  |  |  3 角色: admin / operator / viewer                             |   |      |
|  |  |  3 個獨立 RBAC 系統 (Platform / ToolGateway / MCP)             |   |      |
|  |  |  WARNING: 三系統未整合，各自維護 in-memory 角色映射             |   |      |
|  |  +---------------------------------------------------------------+   |      |
|  +--------------------------------------+-------------------------------+      |
|                                         | [ok] 權限已確認                       |
|                                         v                                       |
|  +----------------------------------------------------------------------+      |
|  |  第三層: PromptGuard 提示注入防護                                      |      |
|  |  +---------------------------------------------------------------+   |      |
|  |  |  core/security/prompt_guard.py (Phase 36)                      |   |      |
|  |  |  L1: 17 regex 輸入過濾 + 2 XSS 逃逸偵測                       |   |      |
|  |  |  L2: <user_message> 標籤隔離系統提示                           |   |      |
|  |  |  L3: 工具呼叫白名單 + 參數注入掃描                             |   |      |
|  |  |  + ToolSecurityGateway: 17 額外注入模式 (SQL/Code/Prompt)      |   |      |
|  |  +---------------------------------------------------------------+   |      |
|  +--------------------------------------+-------------------------------+      |
|                                         | [ok] 輸入已淨化                       |
|                                         v                                       |
|  +----------------------------------------------------------------------+      |
|  |  第四層: ToolGateway 工具存取閘門                                      |      |
|  |  +---------------------------------------------------------------+   |      |
|  |  |  core/security/tool_gateway.py + mcp/security/*                |   |      |
|  |  |  MCP PermissionChecker: 4 級 RBAC (NONE/READ/EXECUTE/ADMIN)   |   |      |
|  |  |  CommandWhitelist: 79 白名單 + 24 黑名單 regex                 |   |      |
|  |  |  Glob-pattern 匹配 + 優先級策略評估 + Deny-list 優先           |   |      |
|  |  |  WARNING: 目前預設 mode=log (僅記錄不阻擋)                     |   |      |
|  |  +---------------------------------------------------------------+   |      |
|  +--------------------------------------+-------------------------------+      |
|                                         | [ok] 工具已授權                       |
|                                         v                                       |
|  +----------------------------------------------------------------------+      |
|  |  第五層: Sandbox 沙箱隔離                                              |      |
|  |  +---------------------------------------------------------------+   |      |
|  |  |  core/sandbox/ + mcp/servers/filesystem/sandbox.py             |   |      |
|  |  |  程式碼執行隔離 + 資源限制 + 超時控制                           |   |      |
|  |  |  Filesystem: 路徑驗證 + 敏感檔案封鎖 + 大小限制 (10MB)        |   |      |
|  |  |  Shell: 平台感知 (PowerShell/Bash/CMD) + 1MB 輸出限制          |   |      |
|  |  +---------------------------------------------------------------+   |      |
|  +--------------------------------------+-------------------------------+      |
|                                         | [ok] 執行已隔離                       |
|                                         v                                       |
|  +----------------------------------------------------------------------+      |
|  |  第六層: Audit Trail 稽核軌跡                                          |      |
|  |  +---------------------------------------------------------------+   |      |
|  |  |  mcp/security/audit.py + redis_audit.py                        |   |      |
|  |  |  AuditLogger: 12 事件類型 (5 類別)                             |   |      |
|  |  |  3 儲存後端: InMemory (dev) / File (簡易) / Redis (生產)       |   |      |
|  |  |  敏感欄位自動遮蔽 (password, secret, token, api_key 等)        |   |      |
|  |  |  + orchestration/audit/logger.py -- 路由決策稽核               |   |      |
|  |  |  + integrations/audit/ -- DecisionTracker 決策追蹤             |   |      |
|  |  +---------------------------------------------------------------+   |      |
|  +----------------------------------------------------------------------+      |
|                                                                                 |
|  全程操作記錄 <--- 每一層的操作結果都會被記錄到稽核軌跡                         |
|                                                                                 |
+---------------------------------------------------------------------------------+
```

### Layer Coverage Matrix

| 安全層 | 架構層 L01-L11 覆蓋 | 主要檔案位置 |
|--------|---------------------|-------------|
| L1 JWT Auth | L02 (API Gateway) | `core/security/jwt.py`, `api/v1/dependencies.py` |
| L2 RBAC | L02, L05, L08 | `core/security/rbac.py`, `core/security/tool_gateway.py`, `mcp/security/permissions.py` |
| L3 PromptGuard | L02, L04, L05 | `core/security/prompt_guard.py`, `core/security/tool_gateway.py` |
| L4 ToolGateway | L05, L08 | `mcp/security/permission_checker.py`, `mcp/security/command_whitelist.py` |
| L5 Sandbox | L08 | `core/sandbox/`, `mcp/servers/filesystem/sandbox.py`, `mcp/servers/shell/executor.py` |
| L6 Audit | L02, L04, L05, L08 | `mcp/security/audit.py`, `mcp/security/redis_audit.py`, `orchestration/audit/logger.py` |

---

## 2. Layer 1: JWT Authentication

### Architecture

```
+------------------------------------------------------------------------+
|  JWT 身份驗證流程                                                       |
+------------------------------------------------------------------------+
|                                                                         |
|  Client Request                                                         |
|     |  Authorization: Bearer <access_token>                             |
|     v                                                                   |
|  +----------------------------------------------+                      |
|  |  api/v1/dependencies.py                       |                      |
|  |  get_current_user()                           |                      |
|  |     +-- jwt.decode(token, SECRET, HS256)      |                      |
|  |     +-- 驗證 exp (expiration)                 |                      |
|  |     +-- 提取 sub (user_id)                    |                      |
|  |     +-- 返回 TokenPayload                     |                      |
|  +----------------+-----------------------------+                      |
|                   |                                                     |
|     +-------------+-------------------------------+                    |
|     v             v                               v                    |
|  public_router   protected_router              admin_router            |
|  (1 router)      (46 routers)                  get_current_active_     |
|  無需 JWT        需要 valid JWT                admin()                 |
|                                                需要 admin 角色         |
|                                                                         |
+------------------------------------------------------------------------+
```

### Configuration

| Attribute | Value | Source | Assessment |
|-----------|-------|--------|------------|
| Algorithm | HS256 (symmetric) | `core/security/jwt.py` | **MEDIUM risk** -- RS256 (asymmetric) preferred for production |
| Secret source | `settings.jwt_secret_key` | pydantic Settings (from `.env`) | OK -- not hardcoded |
| Access token TTL | `jwt_access_token_expire_minutes` | Configurable via env | OK |
| Refresh token TTL | 7 days | Hardcoded | **LOW risk** -- should be configurable |
| Token `type` claim | Only on refresh tokens (`"type": "refresh"`) | jwt.py | **MEDIUM risk** -- access tokens lack `type` claim |
| `aud`/`iss` claims | Not present | jwt.py | **MEDIUM risk** -- no audience/issuer validation |
| Datetime API | `datetime.utcnow()` | jwt.py | **LOW** -- deprecated in Python 3.12+, migrate to `datetime.now(UTC)` |

### FastAPI Dependency Chain

```python
# api/v1/dependencies.py -- 4 authentication dependencies
get_current_user              # JWT extraction + decode -> TokenPayload
get_current_user_optional     # Allows unauthenticated access (returns None)
get_current_active_admin      # get_current_user + admin role check
get_current_operator_or_admin # get_current_user + operator/admin role check
```

### Router Registration (`api/v1/__init__.py`)

- **1 public router**: Bypasses authentication entirely
- **46 protected routers**: Require valid JWT via `get_current_user` dependency
- **Gap**: No CORS origin whitelist found in security scan. CORS configuration likely in `main.py` but not validated per-environment

---

## 3. Layer 2: RBAC Authorization

### Three Parallel RBAC Systems

The platform maintains **3 independent RBAC implementations** that are NOT integrated:

```
+------------------------------------------------------------------------+
|  三個平行 RBAC 系統                                                     |
+------------------------------------------------------------------------+
|                                                                         |
|  +----------------------+  +----------------------+  +-----------------+|
|  |  Platform RBAC        |  |  Tool Gateway RBAC    |  | MCP Permissions ||
|  |  core/security/       |  |  core/security/       |  | mcp/security/   ||
|  |  rbac.py              |  |  tool_gateway.py      |  | permissions.py  ||
|  +----------------------+  +----------------------+  +-----------------+|
|  |  Role(str, Enum):     |  |  UserRole(str, Enum): |  | PermissionLevel ||
|  |  admin / operator /   |  |  admin / operator /   |  | (IntEnum):      ||
|  |  viewer               |  |  viewer               |  | NONE=0/READ=1/  ||
|  |                       |  |                       |  | EXECUTE=2/      ||
|  |                       |  |                       |  | ADMIN=3         ||
|  +----------------------+  +----------------------+  +-----------------+|
|  |  Scope: API 端點存取  |  |  Scope: 工具呼叫權限  |  | Scope: MCP 工具 ||
|  |  Storage: in-memory   |  |  Storage: in-memory   |  | Storage: memory ||
|  |  dict                 |  |  frozenset()          |  | glob patterns   ||
|  |  Wildcard: "tool:*"   |  |  Wildcard: frozenset()|  | Wildcard: fnmatch|
|  |  Default: VIEWER      |  |  Rate limit: 30/min   |  | Deny-list first ||
|  +----------------------+  +----------------------+  +-----------------+|
|                                                                         |
|  WARNING: 三系統的角色不互通                                            |
|  WARNING: 三系統都使用 in-memory 儲存 -- 重啟後狀態全部遺失             |
|  WARNING: 萬用字元語義不同: "tool:*" vs frozenset() vs fnmatch("*")    |
|                                                                         |
+------------------------------------------------------------------------+
```

### Role Capabilities

| Role | Platform RBAC | Tool Gateway | MCP Permissions |
|------|---------------|-------------|-----------------|
| **admin** | All API endpoints + user management | All tools (frozenset = all) + rate: 30/min | ADMIN (level 3) -- full control |
| **operator** | CRUD operations + execution | Execution tools + rate: 30/min | EXECUTE (level 2) -- run + read |
| **viewer** | Read-only endpoints | Read-only tools + rate: 30/min | READ (level 1) -- query only |
| **(unknown)** | Default to VIEWER | Default deny (empty permission set) | Default deny (NONE, level 0) |

### Critical Gaps

1. **Three separate permission stores**: `RBACManager._user_roles`, `ToolSecurityGateway._permissions`, `PermissionManager._policies` -- independent in-memory dicts, not synced
2. **In-memory only**: All three lose state on backend restart. `RBACManager` defaults unknown users to `Role.VIEWER` (safe but not persistent)
3. **Action parameter ignored**: `RBACManager.check_permission()` accepts `action` but documentation states it is "currently accepted but not enforced beyond presence in the permission set"
4. **Role enum duplication**: `Role(str, Enum)` in `rbac.py` and `UserRole(str, Enum)` in `tool_gateway.py` have identical values but are different Python types

---

## 4. Layer 3: PromptGuard

### Three-Layer Prompt Injection Defense

```
+------------------------------------------------------------------------+
|  PromptGuard 三層防護 (Phase 36)                                        |
+------------------------------------------------------------------------+
|                                                                         |
|  用戶輸入文字                                                           |
|     |                                                                   |
|     v                                                                   |
|  +-- L1: Input Filtering ------------------------------------------+   |
|  |  sanitize_input()                                                |   |
|  |  17 regex patterns:                                              |   |
|  |    +-- 角色混淆 (7 patterns):                                    |   |
|  |    |    "ignore previous instructions"                           |   |
|  |    |    "you are now [role]"                                     |   |
|  |    |    "pretend to be"                                          |   |
|  |    |    "act as if you are"                                      |   |
|  |    |    "your new role is"                                       |   |
|  |    |    "forget your instructions"                               |   |
|  |    |    "override your system prompt"                            |   |
|  |    +-- 邊界逃逸 (7 patterns):                                    |   |
|  |    |    "</system>", "```system", "[SYSTEM]"                     |   |
|  |    |    "BEGIN SYSTEM PROMPT"                                    |   |
|  |    |    multi-line boundary markers                              |   |
|  |    +-- 資料外洩 (3 patterns):                                    |   |
|  |    |    "repeat the system prompt"                               |   |
|  |    |    "show me your instructions"                              |   |
|  |    |    "what are your rules"                                    |   |
|  |    +-- XSS 逃逸 (2 patterns):                                    |   |
|  |         HTML entity encoding, unicode escapes                    |   |
|  +--------------------------------------+---------------------------+   |
|                                         v                               |
|  +-- L2: System Prompt Isolation -----------------------------------+   |
|  |  wrap_user_input()                                               |   |
|  |  將用戶文字包裹在 <user_message>...</user_message> 標籤中        |   |
|  |  確保 LLM 區分系統指令與用戶輸入                                 |   |
|  +--------------------------------------+---------------------------+   |
|                                         v                               |
|  +-- L3: Tool Call Validation --------------------------------------+   |
|  |  validate_tool_call()                                            |   |
|  |    +-- 工具名稱白名單檢查                                        |   |
|  |    +-- 參數 key 安全性驗證                                        |   |
|  |    +-- 參數 value 注入掃描                                        |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  +-- Additional: ToolSecurityGateway (tool_gateway.py) -------------+   |
|  |  第二道獨立注入掃描 (17 additional patterns):                    |   |
|  |    +-- SQL injection: "; DROP TABLE", "UNION SELECT", "OR 1=1"   |   |
|  |    +-- Code injection: "exec(", "eval(", "__import__("           |   |
|  |    +-- Prompt injection: "IGNORE PREVIOUS", "SYSTEM OVERRIDE"    |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  WARNING: PromptGuard is per-use instantiation, not middleware           |
|  WARNING: No Content Security Policy (CSP) headers found                |
|                                                                         |
+------------------------------------------------------------------------+
```

### Key Classes

| Class | File | LOC | Responsibility |
|-------|------|-----|----------------|
| `PromptGuard` | `core/security/prompt_guard.py` | ~300 | 3-layer input defense (sanitize, wrap, validate tool calls) |
| `ToolSecurityGateway` | `core/security/tool_gateway.py` | ~500 | Second injection scan (17 SQL/code/prompt patterns) + rate limiting |

### Assessment

- **Strength**: Defense-in-depth with two independent scanning layers (PromptGuard + ToolSecurityGateway)
- **Gap**: PromptGuard is instantiated per-use, not enforced as FastAPI middleware. No evidence it is automatically called in the chat pipeline -- calling code must explicitly invoke it
- **Gap**: No Content Security Policy (CSP) headers detected in the codebase

---

## 5. Layer 4: ToolGateway

### MCP Permission System (4-Level RBAC)

```
+------------------------------------------------------------------------+
|  MCP 4 級 RBAC 權限金字塔                                               |
+------------------------------------------------------------------------+
|                                                                         |
|                      +---------+                                        |
|                      |  ADMIN  |  Level 3                               |
|                      |   (3)   |  完全控制: 配置/管理/執行/讀取         |
|                    +-+---------+-+                                       |
|                    |   EXECUTE   |  Level 2                             |
|                    |    (2)      |  執行工具 + 讀取資源                 |
|                  +-+-------------+-+                                     |
|                  |      READ       |  Level 1                           |
|                  |      (1)        |  僅讀取資源/列表                   |
|                +-+-----------------+-+                                   |
|                |        NONE         |  Level 0                         |
|                |        (0)          |  完全禁止                        |
|                +---------------------+                                  |
|                                                                         |
|  Tool Permission Distribution (69 tools across 9 servers):              |
|                                                                         |
|  +----------+------+---------+-------+-------+                         |
|  | Server   | READ | EXECUTE | ADMIN | Total |                         |
|  +----------+------+---------+-------+-------+                         |
|  | Azure    |  18  |    1    |   4   |  23   |                         |
|  | Filesys. |   4  |    1    |   1   |   6   |                         |
|  | Shell    |   0  |    0    |   2   |   2   |                         |
|  | LDAP     |   5  |    1    |   0   |   6   |                         |
|  | SSH      |   1  |    2    |   3   |   6   |                         |
|  | ServiceN.|   2  |    4    |   0   |   6   |                         |
|  | n8n      |   4  |    1    |   1   |   6   |                         |
|  | ADF      |   6  |    1    |   1   |   8   |                         |
|  | D365     |   4  |    2    |   0   |   6   |                         |
|  +----------+------+---------+-------+-------+                         |
|  | Total    |  44  |   13    |  12   |  69   |                         |
|  +----------+------+---------+-------+-------+                         |
|                                                                         |
+------------------------------------------------------------------------+
```

### MCPPermissionChecker -- Two-Phase Rollout

| Phase | Mode | Env Var | Behavior |
|-------|------|---------|----------|
| **Phase 1** (current default) | `log` | `MCP_PERMISSION_MODE=log` | Violations logged as WARNING, tool invocation **continues** |
| **Phase 2** (production target) | `enforce` | `MCP_PERMISSION_MODE=enforce` | Raises `PermissionError`, blocks unauthorized calls |

**Default policies by environment**:

| Environment | Default Policy | Risk |
|-------------|---------------|------|
| `development` / `testing` (or unset) | `dev_default`: ADMIN to all servers/tools (priority 0) | **MEDIUM** -- overly permissive |
| `production` | No default policy; explicit configuration required | Safe -- deny by default |

**Policy Evaluation Algorithm**:
1. Collect applicable policies (user-specific + role-based)
2. Sort by priority (descending -- higher priority first)
3. For each policy: evaluate conditions -> check deny_list -> match server+tool globs -> compare `policy.level >= required`
4. First definitive result wins (deny_list always takes precedence)
5. Default: **deny** (when `_default_level < required`)

**Dynamic Conditions**: `time_range` (HH:MM start/end), `ip_whitelist` (IP list), custom evaluators via `register_condition_evaluator(name, func)`

### CommandWhitelist -- Three-Tier Command Security

```
+------------------------------------------------------------------------+
|  CommandWhitelist 三層指令安全決策                                       |
+------------------------------------------------------------------------+
|                                                                         |
|  輸入指令 (e.g., "sudo rm -rf /tmp/test")                              |
|     |                                                                   |
|     v  指令前綴剝離: sudo, nohup, env, time                            |
|     |  路徑剝離: /usr/bin/ls -> ls                                      |
|     v                                                                   |
|  +-- Tier 1: BLOCKED_PATTERNS (24 compiled regex) -----------------+   |
|  |  破壞性檔案操作: rm -rf /, rm -rf *, del /s, format C:, mkfs   |   |
|  |  權限提升: chmod 777 /, chown .* /$                              |   |
|  |  遠端程式碼管道: curl...|sh, wget...|sh                          |   |
|  |  Fork bomb: :(){ :|:& }                                         |   |
|  |  系統控制: shutdown, reboot, halt, poweroff, init 0/6           |   |
|  |  Windows 破壞: Remove-Item -Recurse -Force, Stop-Computer       |   |
|  |                                                                   |   |
|  |  --> Match = "blocked" = 立即拒絕 + WARNING log                  |   |
|  +-------------------------------+----------------------------------+   |
|                                  | No match                             |
|                                  v                                      |
|  +-- Tier 2: DEFAULT_WHITELIST (79 command names) -----------------+   |
|  |  系統資訊: whoami, hostname, date, uptime, uname                 |   |
|  |  檔案檢視: ls, dir, cat, head, tail, wc, find, grep, stat       |   |
|  |  網路診斷: ping, nslookup, dig, traceroute, curl, wget          |   |
|  |  系統狀態: ps, top, htop, df, du, free, vmstat, iostat, lsof    |   |
|  |  AD 唯讀: dsquery, dsget, Get-ADUser, Get-ADGroup               |   |
|  |  套件資訊: dpkg, rpm, pip, npm, which, where                    |   |
|  |  文字處理: awk, sed, sort, uniq, cut, tr, tee                   |   |
|  |  壓縮檢視: tar, zip, unzip, gzip                                |   |
|  |  環境變數: env, printenv, echo, printf                           |   |
|  |  PowerShell 唯讀: Get-Process, Get-Service, Get-EventLog, etc.  |   |
|  |                                                                   |   |
|  |  --> Match = "allowed" = 立即放行 + DEBUG log                    |   |
|  +-------------------------------+----------------------------------+   |
|                                  | No match                             |
|                                  v                                      |
|  +-- Tier 3: 其他所有指令 -------------------------------------+       |
|  |  --> "requires_approval" = INFO log                          |       |
|  |  WARNING: HITL 審批流程尚未實作 (Issue 08-07)                |       |
|  |     目前僅記錄，實際仍會執行                                 |       |
|  +--------------------------------------------------------------+       |
|                                                                         |
+------------------------------------------------------------------------+
```

### Key Classes

| Class | File | LOC | Purpose |
|-------|------|-----|---------|
| `PermissionLevel` | `mcp/security/permissions.py` | 458 | IntEnum: NONE(0), READ(1), EXECUTE(2), ADMIN(3) |
| `PermissionPolicy` | `mcp/security/permissions.py` | -- | Glob-based policy with servers, tools, level, deny_list, conditions, priority |
| `PermissionManager` | `mcp/security/permissions.py` | -- | Policy evaluation engine with deny-list precedence |
| `MCPPermissionChecker` | `mcp/security/permission_checker.py` | 183 | Runtime facade: log/enforce modes, dev default policy, statistics |
| `CommandWhitelist` | `mcp/security/command_whitelist.py` | 225 | 3-tier command decision: blocked(24) / allowed(79) / requires_approval |

### Whitelist Security Concerns

| Whitelisted Command | Risk | Concern |
|--------------------|------|---------|
| `curl`, `wget` | MEDIUM | Can exfiltrate data to external URLs |
| `env`, `printenv` | MEDIUM | Expose environment variables (may contain secrets) |
| `sed`, `awk` | LOW | Can modify files (not just read) |
| `tar`, `gzip` | LOW | Can overwrite files if used with extract/create flags |

**Recommendation**: Move `curl`, `wget`, `env`, `printenv` to `requires_approval` tier.

---

## 6. Layer 5: Sandbox

### Execution Isolation

| Component | File | Isolation Mechanism |
|-----------|------|-------------------|
| **Core Sandbox** | `core/sandbox/` | Code execution isolation with resource limits and timeout |
| **Filesystem Sandbox** | `mcp/servers/filesystem/sandbox.py` | Path validation, blocked patterns, size limits |
| **Shell Executor** | `mcp/servers/shell/executor.py` | Platform-aware shell, timeout, output limits |

### Filesystem Sandbox (`FilesystemSandbox`)

| Config | Default | Description |
|--------|---------|-------------|
| `allowed_paths` | Configurable list | Only paths within these directories are accessible |
| `blocked_patterns` | secrets, credentials, `.env`, `id_rsa`, etc. | Sensitive file patterns blocked from read/write |
| `max_file_size` | 10 MB | Maximum file size for read/write operations |
| `max_list_depth` | 10 levels | Maximum directory listing recursion depth |
| `allow_write` | Configurable | Write permission toggle |
| `allow_delete` | Configurable | Delete permission toggle |

### Shell Executor (`ShellExecutor`)

| Config | Default | Description |
|--------|---------|-------------|
| Shell detection | `ShellType` enum: PowerShell / Bash / CMD | Platform-aware (Windows/Linux) |
| Timeout | 60 seconds | Maximum command execution time |
| Max output | 1 MB | Truncates output beyond this limit |
| Working directory | Configurable | Isolated working directory |
| Command validation | Via `CommandWhitelist` | Blocked/allowed/requires_approval |

---

## 7. Layer 6: Audit Trail

### MCP AuditLogger -- 13 Event Types

```
+------------------------------------------------------------------------+
|  稽核事件分類 (4 Categories, 13 Event Types)                            |
+------------------------------------------------------------------------+
|                                                                         |
|  +-- Connection (連線) -----------------------------------------+      |
|  |  SERVER_CONNECT     -- MCP 伺服器連線建立                     |      |
|  |  SERVER_DISCONNECT  -- MCP 伺服器連線斷開                     |      |
|  |  SERVER_ERROR       -- MCP 伺服器連線錯誤                     |      |
|  +---------------------------------------------------------------+      |
|                                                                         |
|  +-- Tool (工具操作) -------------------------------------------+      |
|  |  TOOL_LIST          -- 查詢可用工具清單                       |      |
|  |  TOOL_EXECUTION     -- 工具執行 (含參數、結果、耗時)          |      |
|  |  TOOL_ERROR         -- 工具執行失敗                           |      |
|  +---------------------------------------------------------------+      |
|                                                                         |
|  +-- Access (存取控制) -----------------------------------------+      |
|  |  ACCESS_GRANTED     -- 權限檢查通過                           |      |
|  |  ACCESS_DENIED      -- 權限檢查拒絕                           |      |
|  +---------------------------------------------------------------+      |
|                                                                         |
|  +-- Admin/System (管理/系統) -----------------------------------+      |
|  |  CONFIG_CHANGE      -- 配置變更                               |      |
|  |  POLICY_CHANGE      -- 權限策略變更                           |      |
|  |  SYSTEM_START       -- 系統啟動                               |      |
|  |  SYSTEM_SHUTDOWN    -- 系統關閉                               |      |
|  +---------------------------------------------------------------+      |
|                                                                         |
+------------------------------------------------------------------------+
```

### AuditEvent Data Structure

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | UUID4 | Unique event identifier |
| `event_type` | AuditEventType | One of 12 event types |
| `timestamp` | datetime (UTC) | Event time |
| `user_id` | str | Acting user |
| `server` | str | MCP server name |
| `tool` | str | Tool name |
| `arguments` | dict (sanitized) | Tool arguments with sensitive fields redacted |
| `result` | str | Execution result summary |
| `status` | str | success / failure / error |
| `duration_ms` | float | Execution duration in milliseconds |
| `ip_address` | str | Client IP address |
| `session_id` | str | Session identifier |
| `metadata` | dict | Additional context |

### Sensitive Field Redaction

AuditLogger automatically and recursively redacts values for the following key patterns:

| Keyword Pattern | Redacted To |
|----------------|-------------|
| `password` | `"[REDACTED]"` |
| `secret` | `"[REDACTED]"` |
| `token` | `"[REDACTED]"` |
| `api_key` | `"[REDACTED]"` |
| `credential` | `"[REDACTED]"` |
| `auth` | `"[REDACTED]"` |
| `private_key` | `"[REDACTED]"` |

### Storage Backends

| Backend | Class | Storage | Capacity | Use Case |
|---------|-------|---------|----------|----------|
| **InMemory** | `InMemoryAuditStorage` | `deque(maxlen=10000)` | 10,000 events | Development/testing |
| **File** | `FileAuditStorage` | JSON Lines file | Unlimited (disk) | Simple production |
| **Redis** | `RedisAuditStorage` (Sprint 120) | Redis Sorted Set (`mcp:audit:events`) | Auto-trim to `max_size` | Production |

**Redis backend details**:
- Score = timestamp (for efficient time-range queries)
- Auto-trimming to `max_size` on each write
- Key: `mcp:audit:events`

### Multi-Layer Audit Integration

| Audit System | File | Scope | Storage |
|-------------|------|-------|---------|
| **MCP AuditLogger** | `mcp/security/audit.py` | MCP tool executions, access control | InMemory / File / Redis |
| **Orchestration AuditLogger** | `orchestration/audit/logger.py` | Routing decisions, risk assessments | Structured JSON logging |
| **DecisionTracker** | `integrations/audit/` | Cross-module decision tracking | In-memory |

**AuditLogger convenience methods**:
- `log_tool_execution()` -- Record tool invocation with full context
- `log_access()` -- Record access granted/denied
- `log_server_event()` -- Record connection lifecycle events
- `get_user_activity(hours=24)` -- Query recent user actions
- `get_server_activity(hours=24)` -- Query recent server events
- `cleanup(days=30)` -- Purge old events

---

## 8. Risk Assessment Model

### 7-Dimension Risk Scoring (RiskAssessor)

```
+------------------------------------------------------------------------+
|  RiskAssessor 七維度風險評估模型                                         |
+------------------------------------------------------------------------+
|                                                                         |
|  路由結果 (RoutingDecision)                                             |
|     |                                                                   |
|     v                                                                   |
|  +-- 7 Risk Dimensions ----------------------------------------+       |
|  |                                                              |       |
|  |  D1: 意圖類別 (Intent Category)      權重: 0.2 - 0.8       |       |
|  |      INCIDENT=0.8  CHANGE=0.6  UNKNOWN=0.5                  |       |
|  |      REQUEST=0.4  QUERY=0.2                                 |       |
|  |                                                              |       |
|  |  D2: 子意圖嚴重度 (Sub-Intent)        權重: 0.1 - 0.5       |       |
|  |      system_down=0.5  etl_failure=0.4  access_request=0.3   |       |
|  |                                                              |       |
|  |  D3: 生產環境 (Production)            固定: +0.3             |       |
|  |      context.is_production == True                           |       |
|  |                                                              |       |
|  |  D4: 週末執行 (Weekend)               固定: +0.2             |       |
|  |      context.is_weekend == True                              |       |
|  |                                                              |       |
|  |  D5: 緊急標記 (Urgency)               固定: +0.15            |       |
|  |      context.is_urgent == True                               |       |
|  |                                                              |       |
|  |  D6: 受影響系統數 (Affected Systems)  0.1 * count (cap 0.3) |       |
|  |      len(systems) > 0                                        |       |
|  |                                                              |       |
|  |  D7: 低路由信心度 (Low Confidence)    0.2 * (1-confidence)   |       |
|  |      confidence < 0.8 才觸發                                 |       |
|  |                                                              |       |
|  +-------------------------------+------------------------------+       |
|                                  v                                      |
|  +-- Score Calculation -----------------------------------------+       |
|  |                                                              |       |
|  |  base_score = RISK_LEVEL_SCORES[final_level]                 |       |
|  |    LOW=0.25 | MEDIUM=0.50 | HIGH=0.75 | CRITICAL=1.0        |       |
|  |                                                              |       |
|  |  factor_adj = SUM(increase_factors * 0.1)                    |       |
|  |             - SUM(decrease_factors * 0.1)                    |       |
|  |                                                              |       |
|  |  final_score = clamp(base_score + factor_adj, 0.0, 1.0)     |       |
|  |                                                              |       |
|  +-------------------------------+------------------------------+       |
|                                  v                                      |
|  +-- Approval Decision -----------------------------------------+       |
|  |                                                              |       |
|  |  CRITICAL (score >= 0.7) --> 多人審批 (multi-approver)       |       |
|  |  HIGH     (score >= 0.5) --> 單人審批 (single approver)      |       |
|  |  MEDIUM   (score >= 0.3) --> 自動放行 (auto-approved)        |       |
|  |  LOW      (score <  0.3) --> 自動放行 (auto-approved)        |       |
|  |                                                              |       |
|  +--------------------------------------------------------------+       |
|                                                                         |
+------------------------------------------------------------------------+
```

### 26 ITIL-Aligned Risk Policies

| Category | Policy Count | Risk Range | Approval Range |
|----------|-------------|------------|----------------|
| **INCIDENT** | 10 | CRITICAL - MEDIUM | multi / single / none |
| **REQUEST** | 5 | HIGH - LOW | single / none |
| **CHANGE** | 7 | CRITICAL - MEDIUM | multi / single / none |
| **QUERY** | 3 | LOW | none |
| **UNKNOWN** | 1 | MEDIUM | none |

**Policy Factory Functions**:
- `create_default_policies()` -- Standard 26-policy set (production baseline)
- `create_strict_policies()` -- All incidents and changes require approval
- `create_relaxed_policies()` -- Changes auto-approved in dev environment

### HITL Approval Flow

| Component | File | Purpose |
|-----------|------|---------|
| `HITLController` (Sprint 97) | `orchestration/hitl/controller.py` | Original orchestration-scoped approval lifecycle |
| `ApprovalHandler` | `orchestration/hitl/approval_handler.py` | Redis-backed approval storage (TTL: 30min pending, 7d completed) |
| `UnifiedApprovalManager` (Sprint 111) | `orchestration/hitl/unified_manager.py` | Cross-cutting approval for 5 sources |
| `TeamsNotificationService` | `orchestration/hitl/notification.py` | Microsoft Teams Actionable Message cards |

**Approval Status Lifecycle**:
```
PENDING --> APPROVED    (審批通過)
        +-> REJECTED    (審批拒絕)
        +-> EXPIRED     (逾時自動過期, 30 分鐘)
        +-> CANCELLED   (用戶主動取消)
```

**Dual Approval System Note**: Both `HITLController` (Redis-backed, Sprint 97) and `UnifiedApprovalManager` (PostgreSQL-backed, Sprint 111) coexist. The original is used for Phase 28 orchestration workflows; the unified manager serves as the cross-cutting consolidation layer for 5 approval sources: `ORCHESTRATION`, `AG_UI`, `CLAUDE_SDK`, `MAF_HANDOFF`, `ORCHESTRATOR_AGENT`.

---

## 9. Known Security Issues & Risk Registry

### Critical & High Issues

| # | Issue | Severity | Location | Description |
|---|-------|----------|----------|-------------|
| S-01 | HS256 symmetric JWT | **MEDIUM** | `core/security/jwt.py` | Uses shared secret (HS256); RS256 asymmetric signing preferred for production (prevents secret leakage from enabling token forgery) |
| S-02 | Three unintegrated RBAC systems | **HIGH** | `rbac.py`, `tool_gateway.py`, `mcp/permissions.py` | Platform, ToolGateway, and MCP maintain independent in-memory permission stores; role changes not propagated across systems |
| S-03 | All RBAC state in-memory | **CRITICAL** | All 3 RBAC modules | Backend restart resets all permissions, rate limits, and user-role mappings. 6/10 state categories are volatile |
| S-04 | MCP permission mode=log | **MEDIUM** | `mcp/security/permission_checker.py:52` | Default `MCP_PERMISSION_MODE=log` only warns on violations; unauthorized tool calls succeed in production |
| S-05 | Dev default grants ADMIN | **MEDIUM** | `mcp/security/permission_checker.py:72-78` | When `APP_ENV` is development/testing/unset, blanket ADMIN policy grants full access to all MCP tools |
| S-06 | PromptGuard not middleware | **MEDIUM** | `core/security/prompt_guard.py` | Not enforced as FastAPI middleware; must be explicitly invoked by calling code in chat pipeline |
| S-07 | Whitelist includes exfil commands | **LOW** | `mcp/security/command_whitelist.py` | `curl`, `wget` (data exfiltration), `env`, `printenv` (secret exposure) are whitelisted |
| S-08 | HITL for requires_approval not implemented | **MEDIUM** | `command_whitelist.py:183`, Shell/SSH tools | Commands returning `"requires_approval"` only log; no actual approval flow blocks execution |
| S-09 | Missing JWT claims | **MEDIUM** | `core/security/jwt.py` | Access tokens lack `type`, `aud`, `iss` claims; cannot validate token purpose or intended audience |
| S-10 | Dual approval systems coexist | **LOW** | `hitl/controller.py`, `hitl/unified_manager.py` | HITLController (Redis) and UnifiedApprovalManager (PostgreSQL) operate independently; architectural tension |

### SQL Injection Scan Results

| File | Pattern | Risk | Assessment |
|------|---------|------|------------|
| `hybrid/checkpoint/backends/postgres.py:233` | `f"DELETE FROM {self._table_name} WHERE id = :id"` | MEDIUM | Table name from constructor config, not user input. Parameters use `:id` binding (safe) |
| `hybrid/checkpoint/backends/postgres.py:479` | `f"DROP TABLE IF EXISTS {self._table_name} CASCADE"` | HIGH | DDL with f-string. Safe if config is trusted, but tainted config enables schema destruction |

**Overall**: No raw SQL with user-supplied values found. Main database layer uses SQLAlchemy ORM throughout.

### Hardcoded Secrets Scan

| Finding | Location | Risk |
|---------|----------|------|
| `rabbitmq_password: str = "guest"` | `core/config.py` | Safe -- default env fallback only |
| `password="redis_password"` | `api/v1/cache/routes.py:74` | Low -- appears to be demo/example value |
| All other credentials | Via `os.environ.get()` or pydantic `Settings` | OK -- properly externalized |

---

## 10. Recommendations

### Priority 1: Critical (Immediate Action)

| # | Action | Current State | Target State |
|---|--------|---------------|-------------|
| R-01 | Migrate RBAC state to Redis/PostgreSQL | In-memory dicts (lost on restart) | Persistent storage with TTL |
| R-02 | Unify 3 RBAC systems into single PermissionManager | 3 independent stores | Single source of truth with Redis backing |
| R-03 | Set `MCP_PERMISSION_MODE=enforce` in production | `log` (violations not blocked) | `enforce` (unauthorized calls blocked) |

### Priority 2: High (Next Sprint)

| # | Action | Current State | Target State |
|---|--------|---------------|-------------|
| R-04 | Migrate JWT to RS256 | HS256 (symmetric shared secret) | RS256 (asymmetric key pair) |
| R-05 | Add `type`, `aud`, `iss` claims to JWT | Missing claims | Full JWT validation per RFC 7519 |
| R-06 | Enforce PromptGuard as FastAPI middleware | Per-use instantiation | Auto-applied middleware for all chat endpoints |
| R-07 | Implement HITL approval for `requires_approval` commands | Log-only, execution continues | Integrated with HITLController/UnifiedApprovalManager |

### Priority 3: Medium (Planned Improvement)

| # | Action | Current State | Target State |
|---|--------|---------------|-------------|
| R-08 | Move `curl`/`wget`/`env`/`printenv` from whitelist to requires_approval | Allowed (data exfil risk) | Requires human approval |
| R-09 | Add CORS origin whitelist validation | Configuration not per-environment | Strict origin whitelist per deployment |
| R-10 | Add Content Security Policy headers | Not present | CSP headers on all responses |
| R-11 | Migrate `datetime.utcnow()` to `datetime.now(UTC)` | Deprecated API | Python 3.12+ compliant |
| R-12 | Make refresh token TTL configurable | Hardcoded 7 days | Environment-configurable |

---

*Analysis based on V9 architecture layer reports (L04, L08) and cross-cutting analysis. All file paths, class names, and configuration values verified against source code of 939+ backend files.*
