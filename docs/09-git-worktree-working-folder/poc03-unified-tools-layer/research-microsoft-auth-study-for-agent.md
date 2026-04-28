# IPA 統一工具層：用戶授權同意機制研究報告

> **文件版本**: v1.0  
> **日期**: 2026-04-11  
> **用途**: 作為 `poc/unified-tools` 分支中 ConsentManager 設計與實作的參考依據  
> **下一步**: 在 Claude Code 中評估技術細節並規劃實作方案

---

## 1. 研究背景與目標

### 1.1 問題陳述

IPA 平台的 agent 需要在企業環境中安全地訪問用戶的 Microsoft 365 資源（Outlook、SharePoint、Teams、OneDrive 等）以及 Azure 資源。核心需求是：

- 用戶透過 Azure SSO 登入 IPA 後，agent 能**代表用戶**訪問其 M365 資源
- 訪問前必須經過**用戶明確授權同意**（類似 Copilot Studio 彈出授權卡片的體驗）
- 授權模式需支持：**一次性授權**、**持久化授權**（記住不再詢問）、**有時限性授權**
- 整個流程必須安全、受控、可稽核

### 1.2 核心問題

> 當用戶要求 agent 查詢其 Outlook 郵件記錄或到 SharePoint 找資料時，agent 是否有技術手段在取得用戶授權後安全地執行？這在現實中是否可行？

**結論：完全可行。** Microsoft 已為此場景建立了完整的基礎設施——Entra Agent ID + OAuth 2.0 On-Behalf-Of (OBO) 流程。

---

## 2. Microsoft 授權體系架構

### 2.1 三層產品架構

Microsoft 的企業 Agent 工具生態由三個獨立但互補的產品組成：

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: Microsoft Agent Framework (MAF)                       │
│  ──────────────────────────────────────                         │
│  角色：Agent 建構層                                              │
│  提供：MCP Client + Middleware Pipeline + Memory                │
│  不提供：具體的 M365 工具（如讀郵件、查 SharePoint）            │
│  類比：「水管和接頭」，不是「水」                                │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: Microsoft Agent 365 + Work IQ MCP Servers             │
│  ──────────────────────────────────────────────                  │
│  角色：M365 工具層                                               │
│  提供：9 個預認證 M365 MCP Server（Mail, Calendar, Teams,       │
│        SharePoint, OneDrive, Word 等）                          │
│  授權：需要 Agent 365 企業授權（IT Admin 在 M365 Admin Center    │
│        管控）                                                    │
│  類比：「預製的水龍頭」                                          │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3: Agent Governance Toolkit (2026-04-02 開源)             │
│  ──────────────────────────────────────────────                  │
│  角色：治理層                                                    │
│  提供：Runtime policy enforcement, zero-trust identity,         │
│        執行沙箱, 稽核日誌, 合規映射 (GDPR, SOC2)               │
│  來源：https://github.com/microsoft/agent-governance-toolkit    │
│  類比：「閥門和水表」                                            │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 MAF 實際提供 vs 需另購/自建

| MAF 提供的 | 需要另購或自建的 |
|:-----------|:---------------|
| MCP Client（可連接任意 MCP Server） | 具體的 M365 工具（由 Work IQ MCP / Agent 365 提供） |
| Middleware pipeline（攔截/過濾） | 進階 policy engine（Agent Governance Toolkit） |
| Agent as MCP Server（暴露自身能力） | 自訂 MCP Server 實作 |
| M365 橋接模組（integrations/m365） | Work IQ 授權才能真正存取 M365 |
| Memory/Context providers | 企業記憶體基礎設施（Qdrant, Pinecone 等） |

### 2.3 對 IPA 的啟示

- MAF 給的是「接水管的工具」，不是「水」
- Work IQ MCP 是企業付費產品
- **IPA 不依賴 Work IQ MCP**——IPA 可以直接透過 Microsoft Graph API + OBO flow 自建 M365 工具，這是完全合法且受支持的做法
- Agent Governance Toolkit 剛開源，其設計模式值得參考

---

## 3. OAuth 2.0 On-Behalf-Of (OBO) 流程詳解

### 3.1 什麼是 OBO

OBO 是 OAuth 2.0 的一個標準擴展，專門解決「中間層服務代表用戶訪問下游服務」的場景。在 IPA 的語境中：

- **用戶**（Resource Owner）→ 登入 IPA 的企業員工
- **IPA 前端**（Client）→ 用戶互動介面
- **IPA 後端**（Middle-tier API / Agent 服務）→ 收到用戶 token，需要代表用戶訪問 Graph API
- **Microsoft Graph**（Downstream API）→ 提供 M365 資源訪問

### 3.2 端到端流程

```
┌──────────┐     ┌──────────┐     ┌──────────────┐     ┌─────────────────┐
│  用戶     │     │ IPA 前端  │     │ IPA 後端      │     │ Microsoft Graph │
│ (瀏覽器)  │     │ (React)  │     │ (Python/FastAPI)│   │ (M365 資源)     │
└────┬─────┘     └────┬─────┘     └──────┬───────┘     └────────┬────────┘
     │                │                   │                      │
     │ 1. Azure SSO   │                   │                      │
     │ ──────────────>│                   │                      │
     │                │                   │                      │
     │ 2. MSAL.js 取得│                   │                      │
     │    access token│(Tc, aud=IPA API)  │                      │
     │ <──────────────│                   │                      │
     │                │                   │                      │
     │ 3. 「幫我查上週 Outlook 郵件」      │                      │
     │ ──────────────>│                   │                      │
     │                │ 4. Bearer Tc      │                      │
     │                │ ─────────────────>│                      │
     │                │                   │                      │
     │                │                   │ 5. OBO Token Exchange │
     │                │                   │    POST /oauth2/v2.0/token
     │                │                   │    grant_type=jwt-bearer
     │                │                   │    assertion=Tc
     │                │                   │    scope=Mail.Read
     │                │                   │ ─────────────────────>│
     │                │                   │                      │
     │                │                   │    情況 A: 已有 consent
     │                │                   │ <─── Graph token ────│
     │                │                   │                      │
     │                │                   │    情況 B: 未 consent  │
     │                │                   │ <─── interaction_required
     │                │                   │                      │
     │                │ 6. (情況 B)        │                      │
     │ <── 推送授權卡片 ──│                │                      │
     │                │                   │                      │
     │ 7. 用戶點擊授權 │                   │                      │
     │ ──> Entra 登入頁 ──> consent ──────>│                      │
     │                │                   │                      │
     │                │                   │ 8. 重新 OBO Exchange  │
     │                │                   │ ─────────────────────>│
     │                │                   │ <─── Graph token ────│
     │                │                   │                      │
     │                │                   │ 9. GET /me/messages   │
     │                │                   │ ─────────────────────>│
     │                │                   │ <─── 郵件資料 ───────│
     │                │                   │                      │
     │ <───── Agent 回覆郵件摘要 ─────────│                      │
     │                │                   │                      │
```

### 3.3 OBO Token Exchange 的具體 HTTP 請求

```http
POST https://login.microsoftonline.com/{tenant-id}/oauth2/v2.0/token
Content-Type: application/x-www-form-urlencoded

client_id={IPA-app-client-id}
&client_secret={IPA-app-secret}
&grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer
&assertion={用戶的 access token (Tc)}
&scope=https://graph.microsoft.com/Mail.Read
&requested_token_use=on_behalf_of
```

**成功回應**會返回：
- `access_token`：可用於呼叫 Graph API 的 token
- `refresh_token`：可用於在 token 過期後取得新 token（不需要用戶再次互動）
- `expires_in`：通常 3600 秒（1 小時）

### 3.4 安全保障機制

OBO 流程有一個極其重要的安全特性：

> **OBO 只使用 delegated scopes，不使用 application roles。角色始終附在用戶（principal）身上，永遠不會附在代理操作的應用上。這防止了用戶獲得他們不該有的資源訪問權。**

這意味著：
- Agent 拿到的 token 只能訪問**該用戶自己有權限的資源**
- 用戶在 SharePoint 上沒有權限的文件，agent 同樣看不到
- 安全邊界由 **Entra 平台層面強制執行**，不是靠 IPA 自己實現
- 所有操作都可追溯到具體用戶（audit trail）

---

## 4. 可訪問的 M365 與 Azure 資源

### 4.1 Microsoft Graph API Scope 映射

所有 M365 資源都透過 Microsoft Graph API 訪問，差別只在 scope（權限範圍）不同：

| 資源類型 | Delegated Scope (讀取) | Delegated Scope (寫入) | Graph API Endpoint |
|:---------|:----------------------|:----------------------|:-------------------|
| **Outlook 郵件** | `Mail.Read` | `Mail.Send`, `Mail.ReadWrite` | `/me/messages` |
| **Outlook 日曆** | `Calendars.Read` | `Calendars.ReadWrite` | `/me/events` |
| **Outlook 聯絡人** | `Contacts.Read` | `Contacts.ReadWrite` | `/me/contacts` |
| **SharePoint 文件** | `Files.Read`, `Sites.Read.All` | `Files.ReadWrite` | `/me/drive/items`, `/sites/{id}` |
| **OneDrive** | `Files.Read` | `Files.ReadWrite` | `/me/drive` |
| **Teams 頻道訊息** | `ChannelMessage.Read.All` | `ChannelMessage.Send` | `/teams/{id}/channels/{id}/messages` |
| **Teams 聊天** | `Chat.Read` | `Chat.ReadWrite` | `/me/chats` |
| **Teams 會議** | `OnlineMeetings.Read` | `OnlineMeetings.ReadWrite` | `/me/onlineMeetings` |
| **用戶資料** | `User.Read` | `User.ReadWrite` | `/me` |
| **群組/團隊** | `Group.Read.All` | `Group.ReadWrite.All` | `/groups` |
| **Planner 任務** | `Tasks.Read` | `Tasks.ReadWrite` | `/me/planner/tasks` |
| **To Do** | `Tasks.Read` | `Tasks.ReadWrite` | `/me/todo/lists` |

### 4.2 Azure Resource Manager (ARM)

Azure 資源不走 Graph API，而是走 Azure Resource Manager API。OBO 機制完全一樣，只是 scope 不同：

| 資源類型 | Scope | ARM Endpoint |
|:---------|:------|:-------------|
| **VM 管理** | `https://management.azure.com/user_impersonation` | `/subscriptions/{sub}/providers/Microsoft.Compute/virtualMachines` |
| **Storage** | `https://management.azure.com/user_impersonation` | `/subscriptions/{sub}/providers/Microsoft.Storage/storageAccounts` |
| **SQL Database** | `https://management.azure.com/user_impersonation` | `/subscriptions/{sub}/providers/Microsoft.Sql/servers` |
| **Key Vault** | `https://vault.azure.net/user_impersonation` | `https://{vault-name}.vault.azure.net/` |
| **Monitor/Log Analytics** | `https://management.azure.com/user_impersonation` | `/subscriptions/{sub}/providers/Microsoft.OperationalInsights` |

> **注意**：Azure RBAC 與 M365 權限是獨立的體系。用戶在 Azure 上的 RBAC 角色（Reader、Contributor 等）決定了 agent 代表該用戶能做什麼。OBO token 會自動繼承用戶的 Azure RBAC 權限。

### 4.3 Entra Agent ID 的安全護欄

Microsoft 在 Entra Agent ID 中內建了安全限制：

**被封鎖的高權限 Scope**（Agent 無法獲得）：
- `RoleManagement.ReadWrite.Directory`（目錄角色管理）
- `Application.ReadWrite.All`（應用註冊全控）
- `AppRoleAssignment.ReadWrite.All`（角色指派全控）
- 其他 tenant-wide 的高危寫入權限

**允許的低/中權限 Scope**（Agent 可以獲得）：
- `Mail.Read` / `Mail.Send`（用戶郵箱）
- `Files.Read` / `Files.ReadWrite`（用戶文件）
- `Calendars.ReadWrite`（用戶日曆）
- `User.Read`（用戶資料）
- `Chat.Read`（用戶聊天）

這表示即使 IPA 的 Entra 應用請求了不當的高權限，Entra 平台本身也會拒絕。

---

## 5. 三種授權模式的實現方案

### 5.1 授權模式概覽

| 模式 | 用戶體驗 | 技術實現 | 適用場景 |
|:-----|:---------|:---------|:---------|
| **一次性授權** | 每次操作都需要確認 | 不緩存 refresh token，token 過期後需重新 consent | 高風險操作（如發送郵件、刪除文件） |
| **持久化授權** | 首次授權後不再詢問 | 緩存 refresh token，自動刷新 access token | 低風險讀取操作（如查看郵件、讀取文件） |
| **有時限性授權** | 授權在設定期限後失效 | IPA 應用層控制 refresh token 保留期限，到期後丟棄 | 中風險操作或臨時專案場景 |

### 5.2 Entra 原生行為 vs IPA 應用層控制

```
┌─────────────────────────────────────────────────────────────────┐
│                     Entra 平台層面                               │
│  ─────────────────────────────────────                          │
│  • OAuth2PermissionGrant 對象：記錄用戶對哪些 scope 的 consent   │
│  • 一旦 consent 被記錄，後續 OBO exchange 自動成功（不再提示）    │
│  • consent 本身沒有 expiry 欄位（除非 admin 主動撤銷）           │
│  • consent 頁面是 Microsoft 標準 UI，IPA 無法自訂              │
├─────────────────────────────────────────────────────────────────┤
│                     IPA 應用層面                                │
│  ─────────────────────────────────────                          │
│  • Token 緩存管理：決定是否保留 refresh token                    │
│  • 時限控制：記錄授權時間 + 到期後丟棄 refresh token             │
│  • 授權卡片 UI：在 agent 需要新 scope 時推送到前端              │
│  • Scope 分級策略：根據風險等級決定授權模式                     │
│  • 稽核記錄：記錄每次授權和工具調用                              │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 一次性授權的實現

```python
# 概念示意（非完整代碼）
async def execute_tool_one_time(user_id: str, scope: str, tool_call):
    """
    一次性授權：取得 token 後立即執行，不儲存 refresh token。
    下次調用同一 scope 時，如果 access token 已過期，需要重新觸發 consent。
    """
    # 嘗試 OBO exchange（不帶 refresh token）
    result = await msal_app.acquire_token_on_behalf_of(
        user_assertion=user_access_token,
        scopes=[f"https://graph.microsoft.com/{scope}"]
    )
    
    if "error" in result and result["error"] == "interaction_required":
        # 推送授權卡片到前端
        await push_consent_card(user_id, scope, mode="one_time")
        return ConsentRequired(scope=scope)
    
    # 執行工具調用
    response = await call_graph_api(result["access_token"], tool_call)
    
    # 不儲存 refresh token — 這是「一次性」的關鍵
    # access token 通常 1 小時過期後，需要重新授權
    
    return response
```

### 5.4 持久化授權的實現

```python
async def execute_tool_persistent(user_id: str, scope: str, tool_call):
    """
    持久化授權：首次 consent 後儲存 refresh token，後續自動刷新。
    用戶只需授權一次，之後 agent 可以持續代表用戶操作。
    """
    # 先檢查是否有緩存的 token
    cached = await token_cache.get(user_id, scope)
    
    if cached and not cached.is_expired:
        return await call_graph_api(cached.access_token, tool_call)
    
    if cached and cached.refresh_token:
        # 用 refresh token 靜默刷新（用戶無感）
        result = await msal_app.acquire_token_by_refresh_token(
            cached.refresh_token,
            scopes=[f"https://graph.microsoft.com/{scope}"]
        )
        if "access_token" in result:
            await token_cache.save(user_id, scope, result)
            return await call_graph_api(result["access_token"], tool_call)
    
    # 無緩存，需要 OBO exchange
    result = await msal_app.acquire_token_on_behalf_of(
        user_assertion=user_access_token,
        scopes=[f"https://graph.microsoft.com/{scope}"]
    )
    
    if "error" in result:
        await push_consent_card(user_id, scope, mode="persistent")
        return ConsentRequired(scope=scope)
    
    # 儲存 refresh token — 這是「持久化」的關鍵
    await token_cache.save(user_id, scope, result, ttl=None)
    
    return await call_graph_api(result["access_token"], tool_call)
```

### 5.5 有時限性授權的實現

```python
async def execute_tool_time_limited(user_id: str, scope: str, tool_call, ttl_hours: int = 720):
    """
    有時限性授權：與持久化類似，但 refresh token 有 TTL。
    到期後 IPA 主動丟棄 refresh token，下次需要重新授權。
    TTL 預設 720 小時（30 天），可由用戶或管理員配置。
    """
    cached = await token_cache.get(user_id, scope)
    
    if cached and cached.grant_expired:
        # IPA 層面的授權已過期，主動丟棄
        await token_cache.delete(user_id, scope)
        # 可選：透過 Graph API 撤銷 Entra 層面的 consent
        # await revoke_consent_via_graph(user_id, scope)
        cached = None
    
    if cached and not cached.is_expired:
        return await call_graph_api(cached.access_token, tool_call)
    
    if cached and cached.refresh_token:
        result = await msal_app.acquire_token_by_refresh_token(
            cached.refresh_token,
            scopes=[f"https://graph.microsoft.com/{scope}"]
        )
        if "access_token" in result:
            await token_cache.save(user_id, scope, result, ttl=ttl_hours)
            return await call_graph_api(result["access_token"], tool_call)
    
    result = await msal_app.acquire_token_on_behalf_of(
        user_assertion=user_access_token,
        scopes=[f"https://graph.microsoft.com/{scope}"]
    )
    
    if "error" in result:
        await push_consent_card(user_id, scope, mode="time_limited", ttl=ttl_hours)
        return ConsentRequired(scope=scope)
    
    # 儲存 refresh token，帶 TTL
    await token_cache.save(user_id, scope, result, ttl=ttl_hours)
    
    return await call_graph_api(result["access_token"], tool_call)
```

---

## 6. 企業環境中的授權策略

### 6.1 Admin Consent vs User Consent

在企業環境中，IT Admin 可以預先為整個 tenant 授權特定 scope，這樣用戶就不需要逐個同意：

```
Admin Consent（IT Admin 預授權）：
  → 在 Entra Admin Center 為 IPA 應用授予 Mail.Read, Calendars.Read 等
  → 用戶登入 IPA 後，agent 直接可以讀郵件/日曆，完全無感
  → 適用於：所有用戶都需要的基本功能

User Consent（用戶自行授權）：
  → IPA 在需要時觸發 consent 流程，用戶在 Microsoft 登入頁面同意
  → 適用於：進階功能或高風險操作
  → 可由 Entra 的 consent policy 控制哪些 scope 允許用戶自行 consent
```

### 6.2 建議的 Scope 分級策略

| 風險等級 | 授權方式 | 授權模式 | 範例 Scope |
|:---------|:---------|:---------|:-----------|
| **低風險** | Admin Pre-Consent | 持久化（自動） | `User.Read`, `Mail.Read`, `Calendars.Read`, `Files.Read` |
| **中風險** | User Consent | 有時限性（30 天） | `Mail.Send`, `Files.ReadWrite`, `Chat.ReadWrite` |
| **高風險** | User Consent + HITL | 一次性 | `Mail.ReadWrite`（刪除郵件）, `Sites.Manage.All` |
| **封鎖** | 不允許 | N/A | `Directory.ReadWrite.All`, `RoleManagement.ReadWrite.Directory` |

### 6.3 與 Entra Consent Policy 的整合

Microsoft Entra 從 2025 年 7 月起預設啟用 managed consent policy，預設阻止用戶對第三方應用授予文件和網站訪問權限。IPA 作為企業內部應用，需要：

1. 在 Entra Admin Center 將 IPA 註冊為 **Enterprise Application**
2. 由 IT Admin 進行 **Admin Consent** 預授權基本 scope
3. 配置 **Consent Policy** 允許用戶自行 consent 中風險 scope
4. 確保 IPA 應用的 **Publisher Domain** 已驗證（影響 consent 提示的信任級別）

---

## 7. IPA 現有架構的整合點

### 7.1 現有資產復用

| 現有資產 | 位置 | 如何復用 |
|:---------|:-----|:---------|
| **AG-UI APPROVAL_REQUEST 事件** | AG-UI SSE bridge | 新增 `CONSENT_REQUEST` 事件類型，推送授權卡片到前端 |
| **ApprovalMessageCard 組件** | unified-chat 組件 | 擴展為 `ConsentCard`，顯示所需權限、用途說明、授權時限選項 |
| **RiskAssessmentEngine** | orchestration/hitl/ | 擴展風險維度，將 M365 scope 納入風險評估 |
| **MCP Permission System** | mcp/security/ | 將 Graph API scope 映射到 MCP permission level |
| **ToolCallHandler** | domain/sessions/tool_handler.py | 在執行管線中加入 consent 檢查步驟 |
| **JWT 認證** | core/auth.py | SSO token 作為 OBO exchange 的 assertion 來源 |

### 7.2 需要新增的組件

```
┌──────────────────────────────────────────────────────────┐
│                    ConsentManager                         │
│  ──────────────────────────────────                       │
│                                                           │
│  ┌─────────────────┐  ┌──────────────────┐               │
│  │  ScopeMapper     │  │  ConsentStore    │               │
│  │                  │  │                  │               │
│  │  MCP Tool ID     │  │  user_id         │               │
│  │    → Graph Scope │  │  scope           │               │
│  │    → Risk Level  │  │  grant_type      │               │
│  │    → Auth Mode   │  │  granted_at      │               │
│  │                  │  │  expires_at      │               │
│  └─────────────────┘  │  refresh_token   │               │
│                        │  (encrypted)     │               │
│  ┌─────────────────┐  └──────────────────┘               │
│  │  TokenManager    │                                     │
│  │                  │  ┌──────────────────┐               │
│  │  OBO Exchange    │  │  ConsentUI       │               │
│  │  Token Cache     │  │                  │               │
│  │  Auto Refresh    │  │  AG-UI Event     │               │
│  │  Revocation      │  │  Consent Card    │               │
│  │                  │  │  Status Tracking │               │
│  └─────────────────┘  └──────────────────┘               │
│                                                           │
│  Backend: PostgreSQL (consent grants) + Redis (token cache)│
└──────────────────────────────────────────────────────────┘
```

### 7.3 統一工具執行管線（含 Consent）

```
用戶請求
  │
  ▼
[UnifiedToolCatalog] 工具發現
  │
  ▼
[ScopeMapper] 該工具需要哪些 Graph/ARM scope?
  │
  ├── 不需要外部資源 scope → 跳過 consent
  │
  ▼
[ConsentManager] 檢查授權狀態
  │
  ├── 有效 token 存在 → 直接執行
  │
  ├── Refresh token 存在且未過期 → 靜默刷新 → 執行
  │
  ├── 無授權 / 已過期 →
  │     │
  │     ▼
  │   [RiskAssessor] 評估風險等級
  │     │
  │     ▼
  │   [ConsentUI] 推送授權卡片到前端
  │     │  - 顯示所需權限清單
  │     │  - 顯示用途說明
  │     │  - 提供授權時限選項（如適用）
  │     │
  │     ▼
  │   用戶點擊 → Entra consent 頁面 → 回調
  │     │
  │     ▼
  │   [TokenManager] OBO Exchange → 儲存 token
  │
  ▼
[Permission Check] MCP RBAC 權限檢查（enforce 模式）
  │
  ▼
[Tool Execution] 執行工具（帶 Graph/ARM access token）
  │
  ▼
[Audit Logger] 記錄：誰、什麼時候、用了什麼 scope、做了什麼操作
```

---

## 8. 技術實作考量

### 8.1 MSAL for Python

IPA 後端使用 Python/FastAPI，應使用 `msal` Python 套件：

```bash
pip install msal
```

關鍵 API：
- `ConfidentialClientApplication.acquire_token_on_behalf_of()` — OBO exchange
- `ConfidentialClientApplication.acquire_token_by_refresh_token()` — 靜默刷新
- 內建 token cache（可擴展為 Redis/PostgreSQL backend）

### 8.2 Entra 應用註冊要求

IPA 需要在 Entra ID 中註冊為一個應用，配置：

| 配置項 | 值 | 說明 |
|:-------|:---|:-----|
| **Application type** | Web API | IPA 後端 |
| **Redirect URI** | `https://ipa.company.com/auth/callback` | Consent 回調 |
| **Client credentials** | Certificate 或 Managed Identity（推薦） | OBO exchange 需要 |
| **API Permissions** | Mail.Read, Files.Read, etc. (Delegated) | 所需的 Graph scope |
| **Expose an API** | `api://{client-id}/access_as_user` | 前端取得的 token audience |
| **Known client applications** | IPA 前端 app ID | 合併 consent 提示 |

### 8.3 Token 安全儲存

Refresh token 是高敏感度資料，必須加密儲存：

| 儲存層 | 用途 | 加密 | 建議 |
|:-------|:-----|:-----|:-----|
| **Redis** | Access token 緩存（短期） | 可選 | 設定 TTL = token 有效期 |
| **PostgreSQL** | Refresh token + consent 記錄（長期） | AES-256 加密 | 欄位級加密，key 由 Key Vault 管理 |
| **Key Vault** | 加密金鑰 + client credentials | N/A | 使用 Managed Identity 存取 |

### 8.4 前端授權卡片 UI

擴展現有的 `ApprovalMessageCard` 組件：

```typescript
// 概念示意
interface ConsentCardProps {
  requestId: string;
  agentName: string;
  toolName: string;
  requiredScopes: Array<{
    scope: string;
    description: string;      // e.g. "讀取您的 Outlook 郵件"
    riskLevel: 'low' | 'medium' | 'high';
  }>;
  authModeOptions?: Array<{
    mode: 'one_time' | 'persistent' | 'time_limited';
    label: string;            // e.g. "僅此一次" / "記住授權" / "授權 30 天"
    ttlHours?: number;
  }>;
  onAuthorize: (mode: string, ttlHours?: number) => void;
  onDeny: () => void;
}
```

### 8.5 Entra Agent ID vs 傳統 App Registration

Microsoft 於 2025 年底推出了 Entra Agent ID，這是專門為 AI agent 設計的身份框架。IPA 有兩種選擇：

| 方案 | 優點 | 缺點 | 建議 |
|:-----|:-----|:-----|:-----|
| **傳統 App Registration** | 成熟穩定，文件完善，MSAL 完全支持 | 不是 agent 專用，缺少 agent 專屬護欄 | 短期 PoC 使用 |
| **Entra Agent ID** | Agent 專屬安全護欄，高權限自動封鎖，Microsoft 推薦 | 較新（preview 階段），SDK 支援可能不完整 | 中長期遷移目標 |

**建議**：PoC 階段使用傳統 App Registration（成熟可靠），架構設計時預留遷移到 Agent ID 的空間。

---

## 9. 與 IPA 現有工具系統的問題對照

### 9.1 解決的現有問題

| # | 現有問題 | 嚴重度 | Consent 機制如何解決 |
|:--|:---------|:-------|:-------------------|
| 5 | 權限預設 "log" 非 "enforce" | HIGH | ConsentManager 在 enforce 模式下運作，無 token 無法執行 |
| 6 | MCP Audit 未接線 | HIGH | 每次 consent grant/revoke 和工具調用都寫入 audit log |
| 1 | 三套不相容的 Base Class | CRITICAL | ConsentManager 作為統一工具層的一部分，不依賴特定 registry |
| 2 | 沒有統一工具目錄 | CRITICAL | ScopeMapper 為統一目錄中的每個工具標註所需 scope |

### 9.2 新引入的設計挑戰

| 挑戰 | 說明 | 建議方案 |
|:------|:-----|:---------|
| **Token 安全儲存** | Refresh token 洩漏等同帳戶洩漏 | AES-256 加密 + Key Vault 金鑰管理 |
| **多 scope 合併** | 一次操作可能需要多個 scope | MSAL 支援多 scope 同時請求 |
| **Consent 彈窗體驗** | Entra consent 頁面會離開 IPA UI | 使用 popup 窗口而非全頁導航 |
| **Offline access** | Agent 需要在用戶不在線時執行嗎？ | 如果需要，使用 `offline_access` scope + refresh token |
| **Multi-tenant** | IPA 是否服務多個 Entra tenant？ | 應用註冊為 multi-tenant，consent 流程不變 |

---

## 10. PoC 實作建議優先級

### Phase 1：基礎 OBO Flow（建議先做）

- [ ] Entra 應用註冊 + 基本 scope 配置
- [ ] MSAL Python 整合到 FastAPI 後端
- [ ] 基本 OBO token exchange（Mail.Read 作為 PoC scope）
- [ ] 簡單的 token cache（Redis）
- [ ] 驗證：agent 能讀取登入用戶的 Outlook 郵件

### Phase 2：授權卡片 UI

- [ ] AG-UI `CONSENT_REQUEST` 事件類型
- [ ] `ConsentCard` 前端組件
- [ ] Consent callback 處理
- [ ] 三種授權模式的 UI 選項

### Phase 3：ConsentManager 完整實現

- [ ] ScopeMapper（工具 → scope 映射）
- [ ] ConsentStore（PostgreSQL + 加密）
- [ ] TokenManager（自動刷新 + 時限管理）
- [ ] 與統一工具執行管線整合

### Phase 4：企業治理

- [ ] Admin Consent 預授權流程
- [ ] Consent 審計日誌
- [ ] Scope 分級策略配置
- [ ] Consent 撤銷管理界面

---

## 11. 官方參考資料

### Microsoft Entra Agent ID（Agent 專用身份框架）

| 文件 | URL |
|:-----|:----|
| Agent ID 授權概覽 | https://learn.microsoft.com/en-us/entra/agent-id/authorization-agent-id |
| Agent OBO Flow | https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/agent-on-behalf-of-oauth-flow |
| 互動式 Agent 認證流程 | https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/interactive-agent-authentication-authorization-flow |
| Agent Token 獲取 | https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/interactive-agent-request-user-tokens |
| 授予 Agent M365 資源訪問權 | https://learn.microsoft.com/en-us/entra/agent-id/grant-agent-access-microsoft-365 |

### OAuth 2.0 OBO Flow（通用）

| 文件 | URL |
|:-----|:----|
| OBO Flow 協議詳解 | https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-on-behalf-of-flow |
| Delegated Access 概覽 | https://learn.microsoft.com/en-us/graph/auth-v2-user |
| 程式化授予/撤銷 API 權限 | https://learn.microsoft.com/en-us/graph/permissions-grant-via-msgraph |
| 審查/撤銷應用權限 | https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/manage-application-permissions |

### Agent Governance

| 文件 | URL |
|:-----|:----|
| Agent Governance Toolkit (GitHub) | https://github.com/microsoft/agent-governance-toolkit |
| Azure Logic Apps OBO 設定 | https://learn.microsoft.com/en-us/azure/logic-apps/set-up-on-behalf-of-user-flow |

### MSAL SDK

| SDK | URL |
|:----|:----|
| MSAL Python | https://github.com/AzureAD/microsoft-authentication-library-for-python |
| MSAL.js（前端） | https://github.com/AzureAD/microsoft-authentication-library-for-js |
| Microsoft.Identity.Web（.NET 參考） | https://github.com/AzureAD/microsoft-identity-web |

---

## 12. 總結

| 問題 | 答案 |
|:-----|:-----|
| IPA agent 能否代表用戶訪問 Outlook？ | ✅ 可以，透過 OBO flow + Mail.Read delegated scope |
| SharePoint / OneDrive 也可以？ | ✅ 可以，Files.Read / Sites.Read.All |
| Teams 也可以？ | ✅ 可以，Chat.Read / ChannelMessage.Read.All |
| Azure 資源也可以？ | ✅ 可以，ARM scope + 用戶的 Azure RBAC |
| 需要用戶授權同意嗎？ | ✅ 是，delegated permission 需要用戶或 admin consent |
| 可以做一次性授權？ | ✅ 可以，不緩存 refresh token |
| 可以記住授權？ | ✅ 可以，緩存 refresh token + 自動刷新 |
| 可以有時限性授權？ | ✅ 可以，IPA 應用層控制 refresh token TTL |
| 安全性有保障嗎？ | ✅ agent 只能訪問該用戶自己有權限的資源，由 Entra 平台強制 |
| 跟 Copilot Studio 做的是同一件事嗎？ | ✅ 本質上是，都是 OBO flow + consent |
| MAF 原生支持這些嗎？ | ⚠️ MAF 提供 MCP Client，但不直接提供 M365 工具和 consent 管理 |
| IPA 需要自建嗎？ | ✅ 需要自建 ConsentManager，但底層用的是 Microsoft 標準協議 |