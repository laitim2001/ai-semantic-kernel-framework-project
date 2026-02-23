# IPA Platform 統一改善方案建議書

> **文件類型**: 跨領域專家匯總分析 — 決策文件
> **日期**: 2026-02-21
> **基於**: 6 位領域專家的獨立深度分析報告
> **專家團隊**: Security Architect / Enterprise Architect / SRE-DevOps / Business Analyst / Code Quality Lead / Integration Architect
> **匯總者**: Team Lead (Claude Opus 4.6)

---

## 一、執行摘要

### 1.1 核心共識（6/6 專家一致同意）

1. **安全是第一優先** — 7% Auth 覆蓋率 + 無 Rate Limiting + JWT 硬編碼 + MCP 無認證暴露，構成了不可接受的安全風險。所有專家一致認為必須在任何展示或試用之前完成安全加固。

2. **平台是「未完成」而非「品質差」** — 架構設計卓越（9/10），但工程實現嚴重不足。Code Quality Lead 精確指出：323 空函數中真正需填充的約 180 個，其餘是合理的 ABC/Protocol 定義。SQALE 評級 D，技術債 158.8 人天。

3. **先修路、再展示、漸進落地** — Business Analyst 的核心策略獲得所有專家認可。Phase A（安全基礎，2-3 週）是一切的前提。

### 1.2 最重要的 3 個發現

| # | 發現 | 發現者 | 影響 |
|---|------|--------|------|
| 1 | **Sessions 偽認證** — `get_current_user_id()` 返回硬編碼 UUID，所有用戶共享同一身份 | Security Architect | CRITICAL — 完全無多租戶隔離 |
| 2 | **MCP 28 Permission Patterns 完全未啟用** — 經代碼驗證，MCP servers 中 0 處調用 `check_permission` | Security Architect + Integration Architect | CRITICAL — 安全設計存在但形同虛設 |
| 3 | **HybridOrchestratorV2 是 God Object** — 1,254 LOC、知曉所有 Phase 28 組件、11 個依賴 | Enterprise Architect | HIGH — 架構演化的最大瓶頸 |

### 1.3 建議的第一步行動

**本週（Week 0）立即執行**：
1. 修復 CORS origin（3000→3005）+ Vite proxy（8010→8000）— **30 分鐘**
2. JWT Secret 移至環境變量 + 添加不安全值驗證器 — **2 小時**
3. 清理 authStore 的 5 個 console.log（PII 洩漏）— **30 分鐘**

---

## 二、跨專家共識分析

### 2.1 全票通過（6/6 共識）

| # | 問題 | 各專家角度 |
|---|------|-----------|
| 1 | **Auth 7% 覆蓋率必須立即修復** | Security: CRITICAL 漏洞 / Enterprise: 架構完整性 / SRE: 生產就緒 / BA: IT 審查攔截 / CQ: 品質基線 / Integration: MCP 安全鏈斷裂 |
| 2 | **InMemory 存儲必須替換** | Security: 審計合規 / Enterprise: 狀態一致性 / SRE: 生產穩定 / BA: 業務可靠性 / CQ: 代碼品質 / Integration: 整合鏈路 |
| 3 | **CORS/Vite 端口修復是零成本速效** | 所有專家確認 30 分鐘可修復，是端到端流程的第一個阻塞點 |
| 4 | **Mock 與生產代碼必須分離** | Security: 運行時確定性 / Enterprise: 架構清晰度 / CQ: Factory Pattern / Integration: 邊界明確 |
| 5 | **Phase A 安全加固是一切前提** | 所有專家的路線圖都以安全加固為起點 |

### 2.2 高度共識（5/6 或 4/6）

| # | 問題 | 共識度 | 差異點 |
|---|------|--------|--------|
| 6 | Swarm 應整合到主流程 | 5/6 | BA 認為可延後到 Phase C-D（不是第一落地場景的需求） |
| 7 | ContextSynchronizer 需加鎖 | 5/6 | SRE 和 Security 認為 P0，Enterprise 和 CQ 認為 Phase B |
| 8 | 4 Checkpoint 系統需統一 | 5/6 | Enterprise: CRITICAL / SRE: HIGH / 其他: 可分階段進行 |
| 9 | AD 帳號管理為第一落地場景 | 4/6 | BA 和 Integration 強烈推薦 / Security 需確認 LDAP 安全 / SRE 無異議 |
| 10 | RabbitMQ 短期可移除 | 4/6 | SRE 推薦短期移除 + 中期 Redis Streams / Enterprise 建議保留但延後實現 |

---

## 三、專家意見衝突分析

### 3.1 衝突 #1：ContextSynchronizer 修復優先級

| 專家 | 優先級 | 理由 |
|------|--------|------|
| **Security Architect** | P0 | 競爭條件可導致跨用戶數據洩漏 |
| **SRE/DevOps** | Phase A | 單 Worker 下風險較低，Multi-Worker 前必須修復 |
| **Enterprise Architect** | Phase B | 架構重構時一併處理更合理 |

**仲裁結論**：Phase A 添加 `asyncio.Lock` 作為最小修復（0.5 天），Phase C 升級為 Redis Distributed Lock。Security 的安全顧慮合理，但 SRE 指出單 Worker 下並發風險確實較低。

### 3.2 衝突 #2：RabbitMQ 去留

| 專家 | 建議 | 理由 |
|------|------|------|
| **SRE/DevOps** | 短期移除，中期 Redis Streams | 0% 使用率、佔 200MB RAM、RAPO 規模不需要 |
| **Enterprise Architect** | 保留但延後實現 | 長期事件驅動架構需要消息隊列 |
| **Integration Architect** | 保留 Docker 容器，短期用 FastAPI Background Tasks | 避免未來重新引入的成本 |

**仲裁結論**：保留 Docker 容器但不啟動（節省 RAM），短期用 FastAPI Background Tasks + Redis Streams。中期根據實際負載決定是否啟用 RabbitMQ。

### 3.3 衝突 #3：技術債償還策略

| 專家 | 策略 | 理由 |
|------|------|------|
| **Code Quality Lead** | 14 週 Burndown（158.8 人天） | 系統性消除，追求 80% 測試覆蓋 |
| **Business Analyst** | 場景驅動的漸進改善 | 只修復阻塞第一場景落地的問題 |
| **Enterprise Architect** | 架構優先的重構 | 先修正結構問題，再填充功能 |

**仲裁結論**：採用 **BA 的「場景驅動」為主、CQ 的「系統性 Burndown」為輔** 的混合策略。Phase A-B 聚焦第一場景需要的改善，Phase C-D 執行系統性品質提升。

---

## 四、報告遺漏問題匯總

6 位專家共發現 V2 原報告遺漏的 **39 個問題**（去重後 28 個），按嚴重程度分類：

### CRITICAL（5 項）

| # | 問題 | 發現者 |
|---|------|--------|
| 1 | Sessions 偽認證 — 硬編碼 UUID | Security |
| 2 | MCP Permission Patterns 完全未在運行時檢查 | Security + Integration |
| 3 | HybridOrchestratorV2 God Object | Enterprise |
| 4 | 雙套審批系統未協調（Claude SDK ApprovalHook vs Phase 28 HITLController） | Integration |
| 5 | LLMServiceFactory 預設靜默 fallback 到 Mock | Integration |

### HIGH（9 項）

| # | 問題 | 發現者 |
|---|------|--------|
| 6 | SSE 端點無認證 — 可觀察 Agent 執行 | Security |
| 7 | reload=True + Shell MCP = 代碼注入向量 | Security |
| 8 | Domain Layer 是最大「黑箱」（47K LOC 未詳細審查） | Enterprise |
| 9 | Session 存儲在 dict — 潛在記憶體洩漏 | Enterprise |
| 10 | 異常處理「吞異常」模式 | Enterprise |
| 11 | 無 Dockerfile（應用本身） | SRE |
| 12 | 無結構化日誌 | SRE |
| 13 | 無 Request ID 追蹤 | SRE |
| 14 | Embedding 提供商碎片化（3 處不同配置） | Integration |

### MEDIUM（8 項）

| # | 問題 | 發現者 |
|---|------|--------|
| 15 | 全局異常處理器洩漏 error_type | Security |
| 16 | Zustand localStorage 存儲 JWT Token | Security |
| 17 | Docker 預設憑證 admin/admin123 (n8n + Grafana) | Security |
| 18 | DB Schema Gap（Alembic 混亂） | SRE |
| 19 | 無 Graceful Shutdown | SRE |
| 20 | Barrel export 過深（57 個符號） | Code Quality |
| 21 | 重複的 ContextSynchronizer（2 份實現） | Code Quality |
| 22 | MCP Server 進程管理缺失 | Integration |

### LOW/INFO（6 項）

| # | 問題 | 發現者 |
|---|------|--------|
| 23 | Domain DEPRECATED 模組未清理 | Code Quality |
| 24 | Migration 檔案佔 ~4,700 LOC 可歸檔 | Code Quality |
| 25 | 跨時區運維挑戰 | Business Analyst |
| 26 | 多語言輸入支持不足 | Business Analyst |
| 27 | Prompt Drift 長期風險 | Business Analyst |
| 28 | 無 API 版本策略 | Code Quality |

---

## 五、統一優先級矩陣 — Top 20 改善項目

綜合安全、架構、基礎設施、業務、品質、整合六個維度排序：

| 排序 | 問題 | 影響維度 | 方案概要 | 工作量 | 階段 |
|------|------|---------|---------|--------|------|
| **1** | CORS/Vite 端口不匹配 | 全部 6 維度 | 修改 config.py + vite.config.ts | 0.5h | Week 0 |
| **2** | JWT Secret 硬編碼 (3 處) | 安全/合規 | 環境變量 + 驗證器 | 2h | Week 0 |
| **3** | authStore console.log PII 洩漏 | 安全 | 刪除 5 個 console.log | 0.5h | Week 0 |
| **4** | 全局 Auth Middleware | 安全/合規/業務 | FastAPI Depends + JWT 注入 | 3-5 天 | Phase A |
| **5** | Sessions 偽認證修復 | 安全 | 移除硬編碼 UUID，接入真實 Auth | 1 天 | Phase A |
| **6** | Rate Limiting | 安全 | slowapi middleware | 0.5 天 | Phase A |
| **7** | InMemoryApprovalStorage → Redis | 安全/業務/SRE | Redis 持久化實現 | 2 天 | Phase A |
| **8** | Mock 代碼分離 (18 Mock) | 品質/安全/架構 | Factory Pattern + tests/mocks/ | 3.5 天 | Phase A |
| **9** | MCP Permission 運行時啟用 | 安全/整合 | 在 MCP servers 中插入 check_permission | 2-3 天 | Phase A |
| **10** | Shell/SSH MCP 命令白名單 | 安全 | 白名單機制 + HITL 審批 | 2 天 | Phase A |
| **11** | ContextSynchronizer asyncio.Lock | 安全/架構 | 添加 asyncio.Lock 最小修復 | 0.5 天 | Phase A |
| **12** | Swarm 整合到主流程 | 架構/整合/業務 | execute_with_routing() 新增 SWARM_MODE | 2-3 天 | Phase B |
| **13** | SemanticRouter Mock→Real | 整合/業務 | Azure OpenAI embeddings + 路由數據 | 1.5 週 | Phase B |
| **14** | ServiceNow MCP Server | 整合/業務 | 6 tools, Table API + Attachment | 2 週 | Phase B |
| **15** | Multi-Worker Uvicorn | SRE | Gunicorn + env-aware config | 1-2 天 | Phase B |
| **16** | InMemory 存儲全部替換 (剩餘 8 個) | SRE/安全 | Redis/PostgreSQL schema | 7.5 天 | Phase B-C |
| **17** | Layer 4 拆分 (Input + Decision) | 架構 | 目錄重組 + 契約分離 | 5-7 天 | Phase B |
| **18** | L5-L6 循環依賴修復 | 架構 | ToolCallbackProtocol 共享介面 | 1-2 天 | Phase B |
| **19** | 測試覆蓋 33%→60% | 品質 | Orchestration + Auth + MCP 優先 | 4 週 | Phase B-C |
| **20** | 4 Checkpoint 系統統一 | 架構/SRE | UnifiedCheckpointRegistry | 3-5 天 | Phase C |

---

## 六、交叉影響分析

### 6.1 高價值「一箭多雕」改善項目

| 改善項目 | 正面影響範圍 | 效益說明 |
|----------|-------------|---------|
| **全局 Auth Middleware (#4)** | 安全 + 合規 + 業務 + MCP 安全鏈 | 修復後 MCP Permission 才有意義、IT 審查才能通過、多租戶才成立 |
| **Mock 代碼分離 (#8)** | 品質 + 安全 + 架構 + 測試 | 消除運行時不確定性、測試更可靠、架構邊界清晰 |
| **CORS/Vite 修復 (#1)** | 全部 6 維度 | 前端→後端→Agent→MCP 端到端流程的第一個卡點 |
| **SemanticRouter 啟用 (#13)** | 整合 + 業務 + 架構 | 三層路由從「60% 可用」提升到「95% 可用」|

### 6.2 改善項目依賴關係

```
#1 CORS/Vite 修復
 └→ 解鎖: 前端功能測試、E2E 測試、展示

#4 全局 Auth ──→ #5 Sessions 偽認證修復
                 ├→ #9 MCP Permission 啟用
                 └→ #10 Shell/SSH 白名單

#8 Mock 分離 ──→ #13 SemanticRouter 啟用（清理後才能確定用真實版）
              └→ #19 測試覆蓋提升（Mock 分離後測試才可靠）

#7 ApprovalStorage Redis ──→ #16 剩餘 InMemory 替換
                           └→ #15 Multi-Worker（需先解決 InMemory）

#15 Multi-Worker ──→ #11 ContextSynchronizer Lock（並發安全前提）
```

### 6.3 潛在衝突

| 改善 A | 改善 B | 衝突點 | 解決方案 |
|--------|--------|--------|---------|
| #17 Layer 4 拆分 | #8 Mock 分離 | 同時改 orchestration/ 目錄結構 | 先 Mock 分離（Phase A），再 Layer 拆分（Phase B） |
| #12 Swarm 整合 | #20 Checkpoint 統一 | Swarm 需要 Checkpoint 支持 | Swarm 先用現有 Checkpoint，統一在 Phase C |
| #15 Multi-Worker | #16 InMemory 替換 | Multi-Worker 前必須解決 InMemory | InMemory 替換在前，Multi-Worker 在後 |

---

## 七、統一路線圖

### Phase A：安全基礎 + 速效修復（Week 1-3）

**目標**：達到「可以安全地內部展示」的狀態

| Week | 任務 | 工作量 | 交付物 |
|------|------|--------|--------|
| **W0** | CORS/Vite 修復 + JWT 環境變量化 + console.log 清理 | 3h | 端到端通訊恢復 |
| **W1** | 全局 Auth Middleware + Sessions 偽認證修復 | 4 天 | 所有端點有認證 |
| **W1** | Rate Limiting (slowapi) | 0.5 天 | API 防濫用 |
| **W2** | Mock 代碼分離（Factory Pattern） | 3.5 天 | 運行時確定性 |
| **W2** | InMemoryApprovalStorage → Redis | 2 天 | 審批可靠性 |
| **W3** | MCP Permission 運行時啟用 + Shell/SSH 白名單 | 4 天 | MCP 安全閉環 |
| **W3** | ContextSynchronizer asyncio.Lock | 0.5 天 | 並發安全最小修復 |

**Phase A 交付物**：
- ✅ 前後端能通訊（CORS/Vite 修復）
- ✅ 所有 API 端點有認證（100% Auth）
- ✅ Mock 與生產代碼分離
- ✅ 審批使用 Redis 存儲
- ✅ MCP 工具調用有安全檢查
- ✅ **可以安全地向管理層展示**

**資源需求**：~15-17 天工作量，1 位全棧開發者 3 週

---

### Phase B：核心場景 + 架構加固（Week 4-8）

**目標**：第一個端到端業務場景完整可用

| Week | 任務 | 工作量 | 交付物 |
|------|------|--------|--------|
| **W4** | PatternMatcher AD 規則庫 + LDAP MCP 配置 | 2 天 | AD 場景基礎 |
| **W4-5** | ServiceNow Webhook 真實版 + RITM 映射 | 3 天 | 入口完整 |
| **W5-6** | SemanticRouter Mock→Real 遷移 | 1.5 週 | 路由覆蓋 95% |
| **W6** | Swarm 整合到 execute_with_routing() | 3 天 | 三框架完整 |
| **W6-7** | Layer 4 拆分 + L5-L6 循環依賴修復 | 1 週 | 架構加固 |
| **W7** | Multi-Worker Uvicorn | 2 天 | 並發能力提升 |
| **W7-8** | E2E 測試（AD 場景全流程） | 3 天 | 品質保證 |
| **W8** | ServiceNow MCP Server（基礎版） | 1 週 | RITM 回寫能力 |

**Phase B 交付物**：
- ✅ AD 帳號管理場景端到端可用
- ✅ ServiceNow MCP 基礎版
- ✅ 三層路由 95% 覆蓋率
- ✅ Swarm 在主流程中
- ✅ **可以展示真實業務價值**

**業務價值**（Business Analyst 估算）：
- 月節省 137.5 小時（~$5,740/月）
- ROI +112%（第一年）
- 投資平衡點：月 4

---

### Phase C：生產化 + 品質提升（Week 9-14）

**目標**：團隊內部可以開始使用

| 任務 | 工作量 | 交付物 |
|------|--------|--------|
| InMemory 存儲全部替換 | 7.5 天 | 重啟不丟失狀態 |
| 4 Checkpoint 系統統一 | 5 天 | 狀態一致性 |
| ContextSynchronizer Redis Lock | 2 天 | 分佈式並發安全 |
| Dockerfile + CI/CD Pipeline | 3 天 | 自動化部署 |
| Azure App Service 部署 | 3 天 | 雲端運行 |
| OTel + Azure Monitor | 3 天 | 可觀測性 |
| 測試覆蓋 → 60% | 4 週 | 品質基線 |
| 結構化日誌 + Request ID | 2 天 | 問題追蹤能力 |

**Phase C 交付物**：
- ✅ Docker 部署到 Azure
- ✅ Multi-Worker + Redis 存儲
- ✅ 測試覆蓋 60%+
- ✅ **團隊內部開始使用**

---

### Phase D：功能擴展 + 長期演化（Week 15+）

| 任務 | 優先級 | 業務價值 |
|------|--------|---------|
| n8n 整合（3 種協作模式） | P1 | IPA + n8n 互補 |
| Azure Data Factory MCP | P1 | ETL 場景 |
| IT 事件處理場景 | P1 | $4,000/月 |
| LLMClassifier Mock→Real | P2 | 路由最後 10% |
| D365 MCP | P2 | 業務系統整合 |
| Correlation/RootCause 連接真實數據 | P2 | 事件關聯分析 |
| Anti-Corruption Layer (MAF) | P2 | MAF 風險隔離 |
| 測試覆蓋 → 80% | P2 | 品質目標 |
| HybridOrchestratorV2 重構 (Mediator) | P3 | God Object 消除 |
| ReactFlow 工作流視覺化 | P3 | 前端完整度 |

---

## 八、資源需求總估算

### 8.1 按階段匯總

| 階段 | 工作量 | 日曆時間 | 成本（開發） | 成本（基礎設施） |
|------|--------|---------|-------------|----------------|
| Phase A | ~17 天 | 3 週 | - | $0（本地開發） |
| Phase B | ~30 天 | 5 週 | - | ~$120-1,200/月 LLM API |
| Phase C | ~35 天 | 6 週 | - | ~$107/月 Azure App Service |
| Phase D | 持續 | 持續 | - | 隨功能遞增 |
| **Total (A-C)** | **~82 天** | **~14 週** | - | **~$230-1,310/月** |

### 8.2 按技能分類

| 技能需求 | Phase A | Phase B | Phase C | Phase D |
|----------|---------|---------|---------|---------|
| Python Backend | 15 天 | 20 天 | 25 天 | 持續 |
| Frontend React/TS | 1 天 | 3 天 | 2 天 | 持續 |
| DevOps/Infra | 1 天 | 2 天 | 8 天 | 持續 |
| Security | 5 天 | 2 天 | 1 天 | 持續 |
| Testing | 2 天 | 5 天 | 15 天 | 持續 |

### 8.3 月度運營成本估算（Phase C 後）

| 項目 | 月成本 | 來源 |
|------|--------|------|
| Azure App Service B2 | ~$107 | SRE 估算 |
| Azure Database for PostgreSQL | ~$50-100 | 基礎 tier |
| Azure Cache for Redis | ~$20-50 | 基礎 tier |
| LLM API（Claude + Azure OpenAI） | ~$120-1,200 | Integration Architect 估算 |
| **合計** | **~$300-1,460/月** | |

**對比業務價值**：$5,740/月（僅 AD 場景）→ **ROI 明確正向**

---

## 九、快速致勝清單（Quick Wins）

### 1 天內可完成（0 成本）

| # | 任務 | 時間 | 效果 |
|---|------|------|------|
| 1 | CORS origin 3000→3005 | 5 min | 前端 API 通訊恢復 |
| 2 | Vite proxy 8010→8000 | 5 min | 開發環境 proxy 正常 |
| 3 | JWT Secret 環境變量化 | 2h | 消除最嚴重的硬編碼漏洞 |
| 4 | authStore 5 個 console.log 刪除 | 30 min | PII 洩漏修復 |
| 5 | Docker 憑證 admin/admin123 更改 | 15 min | 預設憑證風險消除 |
| 6 | reload=True 改為環境感知 | 30 min | 生產環境安全 |

### 1 週內可完成（Phase A 前半段）

| # | 任務 | 時間 | 效果 |
|---|------|------|------|
| 7 | 全局 Auth Middleware 注入 | 3-5 天 | 7%→100% Auth 覆蓋 |
| 8 | Sessions 偽認證修復 | 1 天 | 多租戶基礎 |
| 9 | slowapi Rate Limiting | 0.5 天 | API 防濫用 |
| 10 | ContextSynchronizer asyncio.Lock | 0.5 天 | 並發安全最小修復 |

**1 週成果**：安全評分從 1/10 → 6/10，可安全進行內部展示前的準備工作。

---

## 十、長期策略建議

### 10.1 技術選型建議

| 領域 | 建議 | 理由 |
|------|------|------|
| **認證** | Azure AD（RAPO 已有）+ JWT | 企業 SSO、與現有基礎設施一致 |
| **消息隊列** | Redis Streams（短中期）→ RabbitMQ（長期） | 漸進式，避免過早引入複雜度 |
| **部署** | Azure App Service（初期）→ AKS（規模化後） | 成本低、運維簡單、與 RAPO Azure 環境一致 |
| **LLM Gateway** | 統一入口管理 Claude + Azure OpenAI | 計費追蹤、限流、監控、降級的統一管理 |
| **MCP 擴展** | ServiceNow → n8n → ADF → D365 → SAP | 按業務價值遞減排序 |
| **MAF 風險** | Anti-Corruption Layer (ACL) | 隔離 MAF preview API 變更的影響 |

### 10.2 架構演化方向（Enterprise Architect）

```
現狀 (11 層):
  L1-L2-L3-L4-L5-L6-L7-L8-L9-L10-L11

目標 (9+2 架構):
  L1 Frontend
  L2 API
  L3 AG-UI Protocol
  L4a Input Processing (原 L4 拆分)
  L4b Decision Engine (原 L4 拆分)
  L5 Hybrid Orchestration
  L6 Execution Engines (MAF + Claude + Swarm 平級)
  L7 Tool Layer (MCP)
  L8 Domain
  L9 Infrastructure
  + CC1: Checkpoint (Cross-Cutting)
  + CC2: Observability (patrol/correlation/audit/rootcause)
```

### 10.3 組織建議（Business Analyst）

1. **IT 安全審查策略**：Phase A 完成後再向 IT 安全團隊展示，避免「不安全」的第一印象
2. **用戶教育**：準備 30 分鐘展示腳本，以 AD 帳號管理場景為核心展示
3. **變革管理**：漸進式推廣，先在小團隊內試用，收集回饋後再擴大
4. **n8n 協作**：IPA 做推理，n8n 做編排，互補而非替代

---

## 十一、結論與行動呼籲

### 11.1 關鍵決策點

| # | 決策 | 建議 | 影響 |
|---|------|------|------|
| 1 | 是否立即啟動 Phase A？ | **是** — Week 0 的 3 小時修復可以今天開始 | 延遲 = 安全風險持續存在 |
| 2 | 第一落地場景選擇？ | **AD 帳號管理** — LDAP MCP 已有、風險可控、業務價值最高 | 影響 Phase B 的工作方向 |
| 3 | RabbitMQ 去留？ | **保留容器不啟動** — 短期用 Redis Streams | 影響 Docker 資源和架構演化 |
| 4 | 測試覆蓋目標？ | **Phase B 結束 60%、Phase D 目標 80%** | 影響開發速度和品質平衡 |
| 5 | Azure 部署時機？ | **Phase C (Week 9-14)** | 團隊內部使用的前提 |

### 11.2 成功標準

| 階段 | 成功標準 | 測量方式 |
|------|---------|---------|
| Phase A | Auth 100%、安全評分 ≥6/10、可安全展示 | Security 覆蓋率掃描 |
| Phase B | AD 場景 E2E 通過、RITM 處理時間 <5min | 計時對比、E2E 測試 |
| Phase C | Azure 部署成功、20+ 並發用戶、測試 60%+ | 壓力測試、Coverage.py |
| Phase D | 3+ 業務場景可用、月節省 >$10,000 | 業務指標追蹤 |

### 11.3 最終建議

> **IPA Platform 的架構設計是這個項目最大的資產**。6 位專家一致認可其 11 層分離、混合編排、三層路由、MCP 統一工具層的設計理念。問題不在設計，而在實現的完成度和安全性。
>
> 用 3 週完成 Phase A 安全加固，用 5 週完成 Phase B 第一場景落地，IPA Platform 就能從「PoC」轉變為「可用的內部工具」。以 AD 帳號管理場景每月 $5,740 的業務價值計算，14 週的投入（~82 人天）在 4 個月內即可收回。
>
> **建議的第一步**：今天就修復 CORS/Vite 端口（30 分鐘）和 JWT Secret（2 小時），讓端到端流程先跑起來。

---

## 附錄 A：專家報告索引

| 專家 | 報告位置 | 頁數 | 核心指標 |
|------|---------|------|---------|
| Security Architect | `Expert-Analysis-Security-Architect.md` | ~500 行 | 6 個新發現、Top 10 修復、合規矩陣 |
| Enterprise Architect | `Expert-Analysis-Enterprise-Architect.md` | ~550 行 | 3 結構問題、2 隱性風險、9+2 架構建議 |
| SRE/DevOps | `Expert-Analysis-SRE-DevOps.md` | ~600 行 | 10 維度成熟度、33 天路線圖、配置範例 |
| Business Analyst | `Expert-Analysis-Business-Analyst.md` | ~650 行 | 4 場景量化、ROI +112%、展示策略 |
| Code Quality Lead | `Expert-Analysis-Code-Quality.md` | ~450 行 | SQALE D 級、158.8 人天、Burndown 計劃 |
| Integration Architect | `Expert-Analysis-Integration-Architect.md` | ~1100 行 | 5 結構問題、MCP 設計、遷移路徑 |

---

*本建議書基於 6 位獨立領域專家的深度分析，每位專家都進行了代碼級驗證。所有建議均可追溯到具體的源碼位置和專家論據。建議書的最終目的是為 RAPO Data & AI Team Manager 提供可直接執行的行動計劃。*
