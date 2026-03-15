# Architecture Review Board -- 架構診斷共識報告

**Date**: 2026-03-15
**Version**: 1.0
**Status**: FINAL CONSENSUS
**Evaluation Context**: 企業客戶 POC → 生產部署過渡階段

---

## Executive Summary

IPA Platform 經歷 29 個 Phase、133 個 Sprint、~2,379 Story Points 的開發投入，在功能豐富度上表現出色（84.3% 功能完成率、308K+ LOC、10K+ 測試案例）。然而，Architecture Review Board 經過 6 份專家報告的交叉分析、Devil's Advocate 壓力測試、以及業務影響評估後，一致認定：

**平台有「做什麼」的能力，但缺少「可靠地做」的基礎設施。**

核心診斷：**原型品質代碼未升級為生產品質代碼**。系統的 CRUD 核心（agents, workflows, executions, sessions, users）已具備生產級品質（PostgreSQL-backed, 正確的 Repository Pattern），但圍繞核心的 20+ 輔助模組仍停留在開發階段的 InMemory 存儲、4 個 API 模組返回硬編碼假數據、安全機制定義但未啟用、且架構分層在快速迭代中逐漸退化。

**關鍵結論**：投入 4-6 週的生產化加固 Sprint，專注於持久化、安全、API 接線三個方向，即可將平台從「功能展示品」升級為「可部署產品」。這個投資相對於已完成的 133 個 Sprint 來說微不足道（<5%），但對商業可行性至關重要。

---

## 圓桌討論參與者

### 6 位領域分析專家（報告提供者）

| 專家 | 領域 | 報告文件 | 關鍵發現數 |
|------|------|---------|-----------|
| **Dr. Security** | 安全架構 | `Security-Architecture-Deep-Analysis.md` | 27 issues (6C/8H/8M/5L) |
| **Dr. API Design** | API 架構與整合 | `Dr-API-Design-Analysis-V8.md` | 19 recommendations (4C/5H/6M/4L) |
| **Dr. Software Architecture** | 軟體架構與分層 | `Dr-Software-Architecture-Analysis-V8.md` | 架構健康度 52/100 |
| **Dr. Distributed** | 分散式系統 | `Dr-Distributed-Architecture-Analysis-V1.md` | 25+ InMemory 模組, NOT PROD-READY |
| **Dr. Frontend** | 前端架構 | `Frontend-Architecture-Analysis-V8.md` | 22 issues (3C/6H/8M/5L) |
| **Dr. Data** | 資料架構 | `DrData-Data-Architecture-Analysis-V8.md` | 資料持久化覆蓋率 ~30% |

### 3 位 Review Board 成員（圓桌討論者）

| 角色 | 職責 | 核心貢獻 |
|------|------|---------|
| **Chief Architect** (主持人) | 跨領域整合與共識建立 | 6 共識/3 爭議/5 盲點/3 連鎖分析 |
| **Devil's Advocate** | 挑戰結論與壓力測試 | 6 大挑戰 + 2 額外質疑, 修正 3 處過度結論 |
| **Business Impact Analyst** | 業務影響評估與 ROI 分析 | 8C + 16H 業務影響量化, 財務損失估算 |

---

## 1. 共識問題清單（按嚴重度 x 業務影響排序）

### 1.1 CRITICAL -- 上線阻斷器（Must Fix Before Customer Contact）

> 以下問題獲得 Review Board 全票通過為「上線阻斷器」。

#### CR-01: InMemory 存儲 -- 核心用戶資料重啟遺失

| 屬性 | 值 |
|------|-----|
| **V8 Issue** | C-01 (部分) |
| **專家共識** | 6/6 專家一致指出 |
| **嚴重度** | CRITICAL (Tier 1 子集), HIGH (Tier 2), MEDIUM (Tier 3) |
| **業務影響** | 部署阻斷器。伺服器重啟 = 所有進行中對話、審批、執行狀態歸零 |
| **財務風險** | NT$500 萬-2,000 萬/年（資料遺失造成的客戶事件處理中斷） |

**Board 決議**：原 C-01 「25+ 模組 InMemory」經 Devil's Advocate 挑戰後，拆分為 4 個 Tier 獨立評估：

| Tier | 嚴重度 | 模組 | 業務影響 | 修復優先 |
|------|--------|------|---------|---------|
| **Tier 1** | CRITICAL | AG-UI ApprovalStorage, Chat Session, Decision Tracker, Swarm Tracker, A2A Router, MCP Audit (~6-8 模組) | 用戶可見資料丟失、合規缺口、安全審計空白 | Sprint N+1~N+2 |
| **Tier 2** | HIGH | ContextBridge, Rate Limiter, Dialog Context, Orchestration Metrics (~5-7 模組) | 服務降級、DDoS 防護缺口、上下文混亂 | Sprint N+3~N+5 |
| **Tier 3** | MEDIUM | 有 StorageFactory 備選或可自動恢復的模組 (~5-7 模組) | 功能降級但可恢復 | Sprint N+6+ |
| **Tier 4** | N/A | Mock 模組的 InMemory (4 模組) | 丟失的是假數據，無實際影響 | 不適用（隨 Mock 接線解決） |

**Devil's Advocate 關鍵修正**：「25+ 模組全部 CRITICAL」被修正為「6-8 模組 CRITICAL + 分層處理」。Mock 模組的 InMemory 丟失無實際意義（「丟失的是假數據」）。

---

#### CR-02: 4 個 API 模組返回硬編碼假數據

| 屬性 | 值 |
|------|-----|
| **V8 Issue** | C-02, C-03, C-04, C-05 |
| **專家共識** | Dr. API + Dr. Data 一致確認；真實 Integration 層實作已存在 |
| **嚴重度** | CRITICAL |
| **業務影響** | 產品功能聲稱存在但實際不工作 = 「展示與交付不一致」 |
| **財務風險** | NT$200 萬-1,000 萬（每個失敗 POC 的合約機會損失） |

| Mock 模組 | 假數據表現 | 真實實作位置 | 接線工作量 |
|-----------|-----------|-------------|-----------|
| `correlation/routes.py` | 硬編碼 correlation scores (0.8, 0.7) | `integrations/correlation/` (Sprint 130) | ~1 天 |
| `rootcause/routes.py` | 固定 "Database connection pool exhaustion" | `integrations/rootcause/` (Sprint 130) | ~1 天 |
| `patrol/routes.py` | "All systems operating normally" + `time.sleep()` | `integrations/patrol/` | ~1 天 |
| `autonomous/routes.py` | 固定 7 步驟模板 | `integrations/claude_sdk/autonomous/` | ~1-2 天 |

**Board 決議**：這是**投資回報率最高的修復**。代碼已存在，只需接線，3-5 天即可從「假數據」變「真分析」。

---

#### CR-03: SQL Injection 風險

| 屬性 | 值 |
|------|-----|
| **V8 Issue** | C-07 |
| **專家共識** | 4/6 專家交叉確認 (Security, API, Software Arch, Data) |
| **嚴重度** | CRITICAL |
| **業務影響** | 資料洩露可觸發個資法罰款 NT$200 萬-2,000 萬 |
| **修復成本** | < 2 小時（改用參數化查詢） |

**Devil's Advocate 註記**：目前攻擊面可能接近零（因為 InMemory 是預設，postgres_store 可能未被使用）。但隨著 InMemory → PostgreSQL 遷移推進，此漏洞將從理論風險變為真實攻擊面。修復成本極低，無理由延遲。

---

#### CR-04: MCP 安全模型 -- 權限未啟用 + 審計未連接

| 屬性 | 值 |
|------|-----|
| **V8 Issue** | H-07 (權限 log 模式), H-06 (AuditLogger 未連接) |
| **專家共識** | Dr. Security 深度分析 + Dr. API 交叉確認 |
| **嚴重度** | CRITICAL（Board 從 HIGH 升級） |
| **業務影響** | MCP 工具可執行未授權操作且無審計紀錄 = 安全事件後無法追溯 |

**Board 升級理由**：H-07 和 H-06 獨立看是 HIGH，但組合後構成完整的安全缺口鏈：
```
未授權操作 (H-07: log-only) → 操作執行成功 → 無審計紀錄 (H-06: AuditLogger 未接線)
= 安全事件發生時完全無法追溯
```

修復：
- H-07: 將 `MCP_PERMISSION_MODE` 預設從 `log` 改為 `enforce`（1 行配置）
- H-06: 在 8 個 MCP Server 的 `__init__` 中連接 AuditLogger（每檔 ~3 行，共 8 檔案）

---

#### CR-05: Shell/SSH/Azure 命令執行無有效控制

| 屬性 | 值 |
|------|-----|
| **V8 Issue** | H-12, H-13 |
| **專家共識** | Dr. Security 深度分析 |
| **嚴重度** | CRITICAL（Board 從 HIGH 升級） |
| **業務影響** | Agent 可在生產伺服器/Azure VM 上執行任意破壞性命令 |
| **財務風險** | 單次事件可達 NT$1,000 萬+（生產環境破壞 + 復原成本） |

**Board 升級理由**：在企業 AI Agent 平台中，命令執行是最高風險操作。HITL 審批機制僅記錄不阻擋（H-12）+ Azure run_command 無內容驗證（H-13）= Agent 在客戶基礎設施上執行 `rm -rf /` 的路徑完全暢通。

---

#### CR-06: RabbitMQ 訊息佇列 100% 空殼

| 屬性 | 值 |
|------|-----|
| **V8 Issue** | C-06 |
| **專家共識** | Dr. Distributed + Dr. Data 一致確認 |
| **嚴重度** | CRITICAL (架構層面), 但 **非上線阻斷器** |
| **業務影響** | 無異步處理能力，高併發場景下系統不穩定 |

**Board 決議**：RabbitMQ 是規模化阻斷器（>10 併發用戶時），但不是上線阻斷器。初期可用 Redis Pub/Sub 作為輕量替代，當用戶量增長時再實作完整 RabbitMQ。

---

### 1.2 HIGH -- 下一輪 Sprint 修復

| ID | 問題 | 專家來源 | 業務影響 | 修復 Sprint |
|----|------|---------|---------|------------|
| **HI-01** | RBAC 定義但未應用於任何端點 | Security + API | 任何登入用戶可執行管理員操作 | N+1 |
| **HI-02** | ContextBridge 無 asyncio.Lock | Distributed + Security | 併發時用戶上下文混亂（隱私洩漏） | N+1 |
| **HI-03** | JWT 無 Token 撤銷機制 | Security | 被盜 token 60 分鐘內無法阻止 | N+2 |
| **HI-04** | require_auth 不查 is_active | Security | 停用帳戶在 token 過期前仍可存取 | N+2 |
| **HI-05** | 前端 10+ 頁面靜默 Mock 降級 | Frontend + API | 用戶無法區分真實/假數據 | N+2 |
| **HI-06** | Rate Limiter InMemory | Security + Distributed | 多 Worker 時 DDoS 防護失效 | N+2 |
| **HI-07** | Chat 歷史僅 localStorage | Frontend + Data | 清除瀏覽器 = 所有歷史消失 | N+2 |
| **HI-08** | 測試端點未依環境門控 | Security + API | 生產環境暴露測試功能 | N+1 (簡單 fix) |
| **HI-09** | HS256 對稱演算法 | Security | 密鑰洩漏 = 認證體系崩潰 | N+3 |
| **HI-10** | 前端零 Code Splitting | Frontend | 首次載入下載全部 JS (~250KB+ 浪費) | N+2 |

---

### 1.3 MEDIUM -- 計劃性修復

| ID | 問題 | 專家來源 | 修復 Sprint |
|----|------|---------|------------|
| **ME-01** | API Key 前綴暴露 (原 C-08, Board 降級) | Security + API | N+1 |
| **ME-02** | API 錯誤回應格式不一致 (3 種 shape) | API | N+3~N+5 |
| **ME-03** | Create/Edit 頁面 80% 程式碼重複 | Frontend | N+3~N+5 |
| **ME-04** | os.environ 171 處直接調用 | Software Arch | N+3~N+8 |
| **ME-05** | Domain→API 反向依賴 (files/service.py) | Software Arch | N+1 (4h fix) |
| **ME-06** | 49 個 console.log 留在生產代碼 | Frontend | N+2 |
| **ME-07** | Alembic migration 停滯 (Sprint 72 後無新 migration) | Data | N+2 |
| **ME-08** | N+1 查詢風險 (Workflow.executions selectin) | Data | N+3 |
| **ME-09** | JSONB 過度使用 (19 欄位) | Data | N+6+ |
| **ME-10** | datetime.utcnow() deprecated | Security + Data + API | N+3 |

---

### 1.4 LOW -- 持續改進

| ID | 問題 | 專家來源 |
|----|------|---------|
| **LO-01** | store/ vs stores/ 雙目錄 | Frontend |
| **LO-02** | dialog.tsx 小寫命名 | Frontend |
| **LO-03** | UI barrel export 不完整 (3/18) | Frontend |
| **LO-04** | OpenAPI tag 命名不一致 | API |
| **LO-05** | 2 個 "Coming Soon" 佔位頁面 | Frontend |
| **LO-06** | deprecated domain/orchestration/ 未清理 | Software Arch |

---

## 2. 專家間的分歧與決議

### DISPUTE-1: 修復路徑 -- 先安全還是先持久化？

| 專家 | 立場 |
|------|------|
| Dr. Security | 安全優先：JWT 撤銷、MCP 權限 |
| Dr. Distributed | 持久化優先：存儲 survive restart |
| Dr. Data | 兩者並行 |
| Business Impact | 零成本安全修復先行，然後核心持久化 |

**Board 決議**：採用 Business Impact 的建議 -- 三階段串行：
1. **Day 1-3**：零成本安全修復（C-07 SQL injection、H-07 MCP enforce、H-13 Azure 驗證、H-08 test gate）
2. **Sprint N+1~N+2**：核心 InMemory Tier 1 持久化（審批、對話、審計）
3. **Sprint N+1~N+2 並行**：Mock API 接線（ROI 最高）

**理由**：安全 1-line fixes 的修復成本接近零但消除法律風險；持久化和接線可以並行進行。

---

### DISPUTE-2: 架構重構範圍

| 專家 | 建議 |
|------|------|
| Dr. Software Architecture | 17-25 Sprint 完整分層重構 |
| Dr. API Design | 聚焦 4 mock 模組 (2-3 sprints) |
| Dr. Distributed | 3-5 sprints 關鍵路徑 |

**Board 決議**（經 Devil's Advocate 挑戰）：**17-25 Sprint 全停重構不現實，也不會被 stakeholder 批准。** 採用漸進策略：
- 每 Sprint 分配 **30% 容量**給技術債償還
- 按 ROI 排序，優先修復對業務影響最大的項目
- 預估 8-10 個 Sprint 完成核心修復（非完整重構）

---

### DISPUTE-3: Singleton 問題嚴重度

| 專家 | 立場 |
|------|------|
| Dr. Distributed | BLOCKING（阻止水平擴展） |
| Dr. Software Architecture | HIGH（損害可測試性） |
| Dr. API Design | HIGH but not CRITICAL |

**Board 決議**：**HIGH，非 BLOCKING**。理由：
- 核心 CRUD 路徑（PostgreSQL-backed）已支持 multi-worker
- Singleton 影響的主要是輔助功能模組
- 10,271 個測試的存在表明大部分功能仍可測試（通過 monkeypatch）
- 但 Singleton 確實阻礙了**生產級多租戶**和**並發安全**
- 應在 Phase B/C 漸進重構，非立即阻斷

---

### DISPUTE-4: Dr. Security 報告中的錯誤

**Devil's Advocate 發現**：SEC-AUTH-03 聲稱「`validate_security_settings()` 未在啟動時調用」，但 Devil's Advocate 驗證 `backend/main.py:65` **已經調用**了此函數。

**Board 決議**：SEC-AUTH-03 的部分結論標記為 **DISPUTED -- 需再次驗證**。此發現證明圓桌討論的價值：單一專家報告可能包含事實錯誤，交叉驗證是必要的。

---

### DISPUTE-5: C-08 嚴重度

**Devil's Advocate 挑戰**：API key prefix 洩漏不構成 CRITICAL。

**Board 決議**：**C-08 從 CRITICAL 降為 MEDIUM (ME-01)**。API key 前綴（非完整 key）的實際攻擊價值有限。仍需修復（1 行代碼），但不是上線阻斷器。

---

## 3. 交叉影響分析

### CHAIN-1: InMemory 連鎖效應（修正版）

```
InMemory Storage (Tier 1 子集, 6-8 模組)
  |
  +-> 安全: 審計紀錄重啟遺失 -> 合規性障礙
  +-> 安全: MCP AuditLogger 未連接 -> 零操作追蹤
  +-> 擴展: 核心功能可 multi-worker，但輔助功能行為未定義
  |         (修正: 非「結構性不可能」，而是「部分降級」)
  +-> API: Rate limiter per-worker -> DDoS 防護缺口
  +-> 前端: 靜默降級為 mock -> 用戶信任風險
```

**Devil's Advocate 修正**：「水平擴展結構性不可能」修正為「核心 CRUD 功能支持水平擴展，20+ 輔助功能在 multi-worker 下行為未定義」。

---

### CHAIN-2: 假數據連鎖（新增）

```
後端 4 個 Mock API (C-02~C-05)
  |
  +-> 前端 10+ 頁面靜默降級 (H-08)
  |     (注意: 這是獨立設計缺陷, 非同一根因)
  +-> POC Demo 展示假數據 -> 客戶發現 -> 信任崩潰
  +-> 安全審計報告也是硬編碼假數據 (SEC-DATA-01) -> 合規詐欺風險
  +-> Mock 測試驗證假行為 -> 測試套件可信度存疑
```

**Devil's Advocate 修正**：前端 `try/catch + generateMock*()` 是**獨立的設計缺陷**。修復後端 mock API 不會自動修復前端的靜默降級。兩者需要獨立修復。

---

### CHAIN-3: 安全缺口鏈

```
MCP Permission log-only (H-07)
  +-> 未授權操作可執行
  +-> AuditLogger 未連接 (H-06) -> 無審計紀錄
  +-> Shell/SSH HITL 僅 log (H-12) -> 高風險命令通行
  +-> Azure run_command 無驗證 (H-13) -> VM 任意命令
  = 從「未授權操作」到「客戶基礎設施破壞」的完整攻擊路徑
```

---

### CHAIN-4: 分層退化連鎖

```
API→Integration 104 次直接依賴
  +-> API→Infrastructure 32 次直接依賴
  +-> Domain→API 1 次反向依賴 (致命循環)
  = Integration 層任何變更波及 40+ API 檔案
    (Devil's Advocate 修正: 核心路徑約 40-50 次, 非全部 104 次)
```

---

## 4. 修復路線圖

### Phase A: 止血（Sprint N ~ N+2, 約 2 Sprints）

> **目標**：消除上線阻斷器，達到「可安全 Demo」狀態

**Week 1: 零成本安全修復（Day 1-3）**

| 優先級 | 問題 | 修復動作 | 工時 |
|--------|------|---------|------|
| P0 | CR-03 SQL Injection | `postgres_store.py` 改用參數化查詢 | 2h |
| P0 | CR-04 MCP 權限 | `MCP_PERMISSION_MODE` 改為 `enforce` | 1 行 |
| P0 | CR-04 MCP 審計 | 8 個 MCP Server 連接 AuditLogger | 8 檔, 每檔 3 行 |
| P0 | CR-05 Azure 驗證 | Azure `run_command` 加入 CommandWhitelist | 半天 |
| P0 | HI-08 Test 端點 | 加 `if settings.app_env != "production"` gate | 5 行 |
| P1 | ME-01 API Key | 從 ag-ui reset 回應移除 key prefix | 1 行 |
| P1 | ME-05 反向依賴 | 遷移 FileCategory 等型別到 Domain 層 | 4h |

**Week 2-4: 核心持久化 + Mock 接線（並行執行）**

| 優先級 | 問題 | 修復動作 | 工時 |
|--------|------|---------|------|
| P0 | CR-01 Tier 1 | ApprovalStorage, Chat Session, MCP Audit → Redis/PostgreSQL | 2 sprints |
| P0 | CR-02 Mock 接線 | 4 個 mock API → 真實 Integration 層 | 3-5 天 |
| P1 | HI-01 RBAC | 為破壞性端點添加角色檢查 dependency | 4h |
| P1 | HI-02 Lock | ContextBridge 加 asyncio.Lock | 5 行 |
| P1 | HI-08 Test Gate | AG-UI test 端點環境門控 | 2h |

**Phase A 預期成果**：
- 安全漏洞（SQL injection, MCP 權限, Azure 命令）已修復
- 核心用戶資料（審批, 對話, 審計）survive restart
- 4 個 AIOps 功能從假數據變真分析
- 可安全進行客戶 Demo

---

### Phase B: 基礎加固（Sprint N+3 ~ N+5, 約 3 Sprints）

> **目標**：達到「可 POC 部署」狀態，每 Sprint 30% 容量用於技術債

| 優先級 | 問題 | 修復動作 | 工時 |
|--------|------|---------|------|
| P1 | CR-01 Tier 2 | ContextBridge, Rate Limiter, Dialog Context → Redis | 2-3 sprints |
| P1 | HI-03 | JWT Token 撤銷機制（Redis blacklist） | 1 sprint |
| P1 | HI-04 | require_auth 加入 Redis-cached is_active 檢查 | 3 天 |
| P1 | HI-05 | 前端 MockDataBanner 元件 + 移除靜默降級 | 1 sprint |
| P1 | HI-06 | Rate Limiter 遷移到 Redis storage | 2-3h (配置改) |
| P1 | HI-10 | React.lazy Code Splitting | 3 天 |
| P2 | ME-02 | 統一 API 錯誤回應格式 | 1 sprint |
| P2 | ME-07 | Alembic baseline migration | 2 天 |

**Phase B 預期成果**：
- 輔助功能也具備持久化
- 安全認證體系完整（token 撤銷 + is_active 檢查）
- 前端首次載入效能改善 ~40%
- 可進入客戶 POC 階段

---

### Phase C: 架構重構（Sprint N+6 ~ N+10+, 持續進行）

> **目標**：漸進式架構改善，每 Sprint 30% 容量

| 優先級 | 問題 | 修復動作 |
|--------|------|---------|
| P2 | HI-09 | JWT 從 HS256 遷移到 RS256 |
| P2 | CR-01 Tier 3 | 剩餘 InMemory 模組遷移 |
| P2 | CHAIN-4 | 漸進消除 API→Integration 直接依賴（按模組） |
| P2 | ME-04 | os.environ → get_settings() 統一 (171 處) |
| P2 | Singleton | 核心路徑 Singleton → FastAPI Depends 遷移 |
| P2 | CR-06 | Redis Pub/Sub 替代或 RabbitMQ 實作 |
| P3 | ME-09 | 部分 JSONB 正規化 |
| P3 | 前端 | useUnifiedChat 拆分, Create/Edit 元件合併 |

**Phase C 不設固定終點**，作為持續改進流程融入日常開發。

---

### Phase D: 品質提升（持續）

| 領域 | 動作 |
|------|------|
| 測試 | 驗證 10K+ 測試套件的實際覆蓋率和通過率 |
| 可訪問性 | WCAG 2.1 AA 合規（aria-live, 鍵盤導航） |
| 效能 | 負載測試基線建立 |
| CI/CD | 建立自動化品質門檻 |
| 架構守衛 | ArchUnit/import-linter 防止分層退化 |

---

## 5. 風險評估

### 不修復的後果

| 風險場景 | 概率 | 後果 | 年化預期損失 |
|---------|------|------|------------|
| 客戶 POC 期間伺服器重啟，所有資料丟失 | 極高 (>90%) | POC 失敗, 客戶流失 | NT$500 萬-2,000 萬 |
| 客戶發現分析結果為固定假數據 | 極高 (>90%) | 信任崩潰, 合約取消 | NT$200 萬-1,000 萬 |
| SQL injection 被利用 | 中 (10-30%) | 資料洩露, 法律訴訟, 罰款 | NT$200 萬-2,000 萬 |
| MCP 工具執行未授權操作 | 中 (10-30%) | 客戶基礎設施破壞 | NT$500 萬-5,000 萬 |
| 安全審計報告被發現為假數據 | 低-中 (5-15%) | 合規詐欺指控 | NT$100 萬-500 萬 |
| **合計年化風險** | | | **NT$1,500 萬-10,500 萬** |

### 修復的投資回報

| 修復階段 | 投資（人天） | 消除風險 | ROI |
|---------|------------|---------|-----|
| Phase A 止血 | ~20-30 天 | CR-01~CR-05, 安全底線 | **極高** |
| Phase B 基礎加固 | ~40-60 天 | 認證完整性, 前端品質 | **高** |
| Phase C 架構重構 | ~80-120 天 (漸進) | 長期維護性, 擴展性 | **中** |

---

## 6. 已識別的盲點（需後續驗證）

| ID | 盲點 | 來源 | 影響 | 建議 |
|----|------|------|------|------|
| **BS-01** | StorageFactory 7 個 factory 的實際採用率未驗證 | Devil's Advocate | 若 factory 未被使用，「遷移到 factory」的路線前提不成立 | Sprint N 驗證 |
| **BS-02** | 10,271 個測試的通過率和覆蓋率未知 | Devil's Advocate | 測試可能在驗證 mock 假行為，套件可信度存疑 | Sprint N 執行 coverage report |
| **BS-03** | CI/CD pipeline 完全未分析 | Chief Architect | Docker Compose 有空殼配置，可能有更多未實作基礎設施 | 後續專項分析 |
| **BS-04** | 無負載測試數據 | Chief Architect | 所有效能結論為推斷非實測 | 建立負載測試基線 |
| **BS-05** | JSONB 查詢效能未分析 | Chief Architect | 19 個 JSONB 欄位可能含效能瓶頸 | 後續 DBA 分析 |
| **BS-06** | 前端安全未深入（localStorage token, CSP） | Chief Architect | 前端 token 存儲可能有安全風險 | Security Phase B 涵蓋 |
| **BS-07** | SEC-AUTH-03 結論需再次驗證 | Devil's Advocate | Dr. Security 聲稱函數未被調用，但初步驗證已被調用 | Sprint N 確認 |

---

## 附錄 A: 6 份專家報告索引

| # | 報告 | 專家 | 行數 | 核心指標 |
|---|------|------|------|---------|
| 1 | `Security-Architecture-Deep-Analysis.md` | Dr. Security | ~495 | 27 issues, 5 attack surfaces |
| 2 | `Dr-API-Design-Analysis-V8.md` | Dr. API Design | ~586 | 540 endpoints, 4 mock modules, health 62/100 |
| 3 | `Dr-Software-Architecture-Analysis-V8.md` | Dr. Software Arch | ~439 | Health 52/100, 672-992h tech debt |
| 4 | `Dr-Distributed-Architecture-Analysis-V1.md` | Dr. Distributed | ~514 | 25+ InMemory, 90+ singletons |
| 5 | `Frontend-Architecture-Analysis-V8.md` | Dr. Frontend | ~552 | 22 issues, TS quality 9.5/10, perf 5/10 |
| 6 | `DrData-Data-Architecture-Analysis-V8.md` | Dr. Data | ~489 | 9 tables, 19 JSONB, 30% persistence coverage |

## 附錄 B: V8 Issue Registry 交叉對照

| Board Issue | V8 Issue(s) | 嚴重度變更 | 備註 |
|-------------|-------------|-----------|------|
| CR-01 | C-01 | 保持 CRITICAL (拆分 Tier) | Devil's Advocate 修正: 拆為 4 Tier |
| CR-02 | C-02, C-03, C-04, C-05 | 保持 CRITICAL | 最高 ROI 修復 |
| CR-03 | C-07 | 保持 CRITICAL | 目前攻擊面可能為零，但修復成本極低 |
| CR-04 | H-06 + H-07 | **HIGH → CRITICAL** | Board 升級: 組合構成完整安全缺口 |
| CR-05 | H-12 + H-13 | **HIGH → CRITICAL** | Board 升級: 客戶基礎設施破壞風險 |
| CR-06 | C-06 | CRITICAL (規模化) | 非上線阻斷器，但規模化阻斷器 |
| ME-01 | C-08 | **CRITICAL → MEDIUM** | Devil's Advocate 降級: prefix 非完整 key |
| -- | SEC-AUTH-03 (部分) | **DISPUTED** | Devil's Advocate: validate 已被調用 |

## 附錄 C: 財務影響量化（Business Impact Analyst）

| 風險類別 | 年化預期損失 (NTD) | 修復成本 (人天) | ROI 等級 |
|---------|-------------------|----------------|---------|
| 資料遺失 (CR-01) | 500 萬-2,000 萬 | 15-25 天 | 極高 |
| Mock 暴露 (CR-02) | 200 萬-1,000 萬 | 3-5 天 | **極高 (最佳 ROI)** |
| 安全事件 (CR-03~05) | 200 萬-5,000 萬 (條件性) | 3-5 天 | 極高 |
| 合規缺失 (CR-04 審計) | 100 萬-500 萬 | 5-8 天 | 高 |
| 客戶體驗 (HI-05/07/10) | 50 萬-200 萬 | 8-12 天 | 中-高 |

---

*Architecture Review Board Consensus Report v1.0*
*Generated: 2026-03-15*
*Participants: Chief Architect (Chair), Devil's Advocate, Business Impact Analyst*
*Based on: 6 expert analysis reports + cross-domain roundtable discussion*
