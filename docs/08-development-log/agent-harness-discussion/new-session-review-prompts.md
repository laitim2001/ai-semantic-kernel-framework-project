# 新 Session Review Prompts（V2 版，2026-04-23 更新）

**用途**：在新 Claude Code session 中獨立 review V2 規劃文件
**使用方式**：複製對應 Prompt 到新 session 直接貼上

---

## 更新說明（2026-04-23）

### 已完成（不需再 review）
以下 3 份文件已經 codebase-researcher 子代理 review + P0 全部修訂：
- ✅ `02-architecture-design.md`（5 層架構 + 拆 platform + 去 0X 前綴）
- ✅ `04-anti-patterns.md`（強化 AP-3 lint + 新增 AP-11）
- ✅ `09-db-schema-design.md`（5 P0：trigger / tenant_id / RLS / 5 表 / partition）

### 待 review（建議重點）
以下文件值得獨立 session review：
- 🔴 `01-eleven-categories-spec.md` — **最關鍵**（11 範疇權威定義）
- 🔴 `10-server-side-philosophy.md` — **最關鍵**（3 大最高原則）
- 🟡 `12-category-contracts.md` — Phase 49.3 必用（範疇間契約）
- 🟡 `06-phase-roadmap.md` — 時程合理性
- 🟢 `11-test-strategy.md` — 測試策略
- 🟢 `14-security-deep-dive.md` — 安全合規
- 🟢 其他可選

---

## Prompt 1：Review `01-eleven-categories-spec.md` + `10-server-side-philosophy.md`（最重要）

**目標**：以業界專家視角獨立檢查 11 範疇規格 + 3 大最高原則

**建議用 max effort**

```
你是 AI Agent Architecture 的業界專家，熟悉以下框架：
- Anthropic Claude Code 與 Claude Agent SDK
- OpenAI Agents SDK 與 Codex
- LangGraph
- Microsoft Agent Framework (MAF)
- CrewAI
- LangChain Deep Agents

我需要你獨立 review 兩份核心 V2 規劃文件：

## 業界 11 範疇定義（這是業界研究的權威定義，請以此為基準）

[此處貼入用戶提供的 11 範疇原始定義 — 從
 docs/08-development-log/agent-harness-discussion/discussion-log-20260426.md 第 67-150 行]

---

## 待 review 文件（請完整閱讀兩份）

文件 1：
`C:\Users\Chris\Downloads\ai-semantic-kernel-framework-project\docs\03-implementation\agent-harness-planning\01-eleven-categories-spec.md`

文件 2（**權威最高原則**）：
`C:\Users\Chris\Downloads\ai-semantic-kernel-framework-project\docs\03-implementation\agent-harness-planning\10-server-side-philosophy.md`

---

## 重要項目背景

- **項目**：IPA Platform V2（重生計畫）
- **V1 對齊度**：27%（已被審計確認）
- **V2 目標**：75%+ 對齊度
- **公司限制**：只能用 Azure OpenAI（無 Claude API）
- **架構**：企業 server-side multi-tenant（不是本地工具）
- **MAF 在 V2**：只佔 5%，主架構是自建 + Adapter pattern

---

## 3 大最高原則（10-server-side-philosophy.md 中定義）

V2 必須遵守：
1. **Server-Side First** — 不是本地 CC，是企業 server
2. **LLM Provider Neutrality** — 不綁 Claude SDK，透過 ChatClient ABC
3. **CC 架構參考但 server-side 轉化** — 參考不照搬

---

## Review 任務

對兩份文件進行**嚴格獨立 review**：

### A. 範疇規格準確性（針對文件 1）
每個範疇的「業界原文」是否精準對應上述業界定義？

### B. 範疇規格完整性（針對文件 1）
每個範疇的「V2 規格」是否涵蓋業界該範疇的所有核心機制？

### C. 範疇可實作性（針對文件 1）
每個範疇的 API / 介面定義是否清晰可實作？

### D. 範疇間一致性（針對文件 1）
範疇之間引用是否一致？

### E. 驗收標準（針對文件 1）
每個範疇的「驗收標準」是否：
- 可量化？
- 可驗證？
- 與業界期待對齊？

### F. 企業 Server-Side 適配（針對兩份文件）
請檢查：
- 是否正確處理 multi-tenant
- 是否處理企業工具（D365 / SAP / ServiceNow）
- HITL 是否密集（企業特性）
- 記憶是否分層（5 層 vs CC 3 層）

### G. LLM Provider 中性性（針對文件 2）
- ChatClient ABC 設計是否真的能隔離供應商？
- ToolSpec 中性格式是否會限制功能？
- 「30 分鐘換 provider」驗收是否實際可行？

### H. CC → V2 轉化映射（針對文件 2）
- 轉化映射表是否完整？
- 有沒有漏掉的 CC 重要機制？
- 有沒有不該轉化的（直接照搬就好）？

### I. 衝突或矛盾
兩份文件之間是否有衝突？
範疇 spec 是否違反 3 大原則？

---

## 期望輸出格式

```
# 11 範疇規格 + Server-Side 哲學 Review 報告

## 整體評分：X/10

## 文件 1：01-eleven-categories-spec.md

### 範疇 1：Orchestrator Loop
- 準確性：✅/⚠️/❌
- 完整性：✅/⚠️/❌
- 可實作性：✅/⚠️/❌
- 驗收標準：✅/⚠️/❌
- 企業適配：✅/⚠️/❌
- 對齊 3 大原則：✅/⚠️/❌
- **發現的問題**：
- **建議修改**：

### 範疇 2: ... (同上格式，覆蓋全 11 範疇)

## 文件 2：10-server-side-philosophy.md

### 原則 1：Server-Side First
- 定義清晰度：...
- 落地可行性：...
- 缺漏：...

### 原則 2：LLM Provider Neutrality
- 同上

### 原則 3：CC 架構參考但轉化
- 轉化映射表完整度：...

## 跨文件問題
- 衝突或矛盾：...
- 範疇是否違反原則：...

## 缺漏的範疇 / 原則
（如果你認為應該有第 12 範疇 / 第 4 原則）

## 總體建議
- 優先修改：...
- 次要修改：...
```

請用繁體中文回應，**寧可嚴格不要寬鬆**。
```

---

## Prompt 2：Review `06-phase-roadmap.md`（時程合理性）

**目標**：以項目管理視角評估 Phase 49-55 路線圖

**建議用 high effort**

```
你是有 10+ 年經驗的軟體項目經理，熟悉 agile / scrum 與 AI 項目管理。

我需要你獨立 review V2 Phase 路線圖。

## 項目背景

- **項目**：IPA Platform（企業級 AI Agent 平台）V2 重生
- **V1 現狀**：跑了 5 年，48 phase，但真實對齊度只 27%
- **決策**：完全重新出發（V2）
- **團隊規模**：1 個資深開發者 + AI 助手協作
- **技術棧**：FastAPI + React 18 + PostgreSQL + Redis + Azure OpenAI GPT-5.4
- **約束**：公司只能用 Azure OpenAI

## V2 規劃完整度

V2 已有 17 份規劃文件覆蓋：
- 戰略（00 vision）
- 範疇規格（01）
- 架構（02）
- 重生策略（03）
- 反模式（04）
- 參考策略（05）
- 路線圖（06，**待你 review**）
- 技術選型（07）
- 術語表（08）
- DB schema（09）
- 3 大最高原則（10）
- 測試策略（11）
- 範疇契約（12）
- 部署 DevOps（13）
- 安全合規（14）
- SaaS readiness（15）
- Frontend 設計（16）

---

## 待 review 文件

主文件：
`C:\Users\Chris\Downloads\ai-semantic-kernel-framework-project\docs\03-implementation\agent-harness-planning\06-phase-roadmap.md`

可參考的依賴文件：
- `00-v2-vision.md`（成功標準）
- `01-eleven-categories-spec.md`（11 範疇）
- `02-architecture-design.md`（5 層架構）
- `09-db-schema-design.md`（Phase 49.2 DB 工作量）
- `11-test-strategy.md`（每範疇 DoD）
- `13-deployment-and-devops.md`（DevOps 工作量）
- `16-frontend-design.md`（前端工作量）

---

## Review 任務

請對 Phase 路線圖進行**嚴格獨立 review**：

### A. 時程合理性
- 每個 Sprint 1 週是否合理？
- Phase 49（3 sprint）是否能做完所有基礎建設（V1 封存 + V2 骨架 + DB schema 14 個 migration + Adapter + Worker queue + OTel）？
- Phase 50（2 sprint）範疇 1 + 6 是否能在 2 週做出真 ReAct loop？
- Phase 53（3 sprint，State + Error + Guardrails）的工作量分配？

### B. 依賴順序
- Phase 49 → 50 → 51 ... 順序是否正確？
- 範疇間依賴是否被正確排序？
- 哪些 Phase 應該並行？

### C. Scope 合理性
- 每個 Sprint 的 deliverables 是否過多 / 過少？
- 哪些 Sprint 風險最高（容易超期）？
- 哪些 deliverables 可以砍 scope？

### D. 與其他規劃文件一致性
- 范疇契約（12）說 Phase 49.3 必須完成所有 ABC，路線圖是否反映？
- 測試策略（11）說 Phase 50 起 CI 強制，路線圖是否反映？
- DevOps（13）說 Phase 49.1 起 docker-compose，路線圖是否反映？
- 安全（14）說 Phase 53 重點實作，路線圖是否反映？
- SaaS（15）說 Phase 56+ 才完整，但路線圖只到 Phase 55？

### E. 風險評估
- 16 sprint 達 75% 對齊度是否實際可行？
- 1 個資深開發者 + AI 是否足夠？
- 哪些技術假設最可能崩盤？

### F. 驗收里程碑
- 每個 Phase 結束的驗收條件是否合理？
- 是否有客觀標準？

### G. 建議調整
基於以上分析，給出：
- 應加長 / 縮短的 Sprint
- 應提前 / 延後的範疇
- 應砍掉 / 增加的 deliverables

---

## 期望輸出格式

```
# Phase 路線圖 Review 報告

## 整體可行性評估：X/10

## 各 Phase 評估

### Phase 49: Foundation（3 sprint）
- 時程合理性：合理 / 過短 / 過長 + 理由
- 與 09 / 11 / 13 文件一致性：
- 主要風險：
- 建議調整：

### Phase 50-55: ... (同上)

## 整體風險清單（按嚴重度）
1. ...

## 與其他文件的衝突
- ...

## 建議的修訂版路線圖
（如果你認為原路線圖有問題，給出修訂版）

## 信心評分
- 16 sprint 達 75% 對齊度的機率：__%
- 4 個月達成的機率：__%
```

請用繁體中文回應，給出**保守誠實**的評估。
```

---

## Prompt 3：Review `12-category-contracts.md`（Phase 49.3 必用）

**目標**：驗證範疇間契約完整性

**建議用 high effort 或子代理**

```
你是有 15+ 年經驗的軟體架構師，熟悉 ABC pattern、Hexagonal Architecture、API design。

我需要你獨立 review V2 範疇間整合契約文件。

## 項目背景
- IPA Platform V2，11 範疇 agent harness 架構
- 此文件定義 11 範疇間的 ABC + 資料流
- Phase 49.3 必須完成所有 ABC 簽名

## 待 review 文件
`C:\Users\Chris\Downloads\ai-semantic-kernel-framework-project\docs\03-implementation\agent-harness-planning\12-category-contracts.md`

可參考：
- `01-eleven-categories-spec.md`（範疇規格）
- `02-architecture-design.md`（架構）

## Review 任務

### A. 契約完整性
- 11 個 Contract 是否涵蓋所有重要互動？
- 有沒有漏掉的範疇間呼叫？

### B. ABC 設計品質
- ABC 簽名是否清晰？
- 參數型別是否合理？
- 返回值是否包含足夠資訊？
- 錯誤處理是否明確？

### C. 範疇呼叫順序圖
- 順序圖是否正確反映實際 loop 流程？
- 有沒有遺漏的步驟？
- 順序是否最優？

### D. LoopState 中央資料結構
- 欄位是否完整？
- 有沒有欄位過多 / 過少？
- 是否真的能跨範疇傳遞？

### E. 失敗模式
- 每個 Contract 的失敗模式是否完整？
- 錯誤傳播路徑是否清晰？

### F. 與業界對比
- 對比 LangGraph 的 state 設計
- 對比 OpenAI Agents Runner
- 對比 Anthropic Claude Agent SDK 的 query() pattern

## 期望輸出
- 整體評分：X/10
- 11 個 Contract 各評估
- 缺漏的契約
- ABC 設計改進建議
- 1500 字內
- 繁體中文
```

---

## Prompt 4：Review `11-test-strategy.md`（測試策略）

**建議子代理或 high effort**

```
你是有 10+ 年經驗的測試架構師，熟悉測試金字塔、TDD、AI 系統測試。

請 review：
`C:\Users\Chris\Downloads\ai-semantic-kernel-framework-project\docs\03-implementation\agent-harness-planning\11-test-strategy.md`

評估：
1. 測試金字塔比例是否合理（70/25/5）
2. 11 範疇測試矩陣是否完整
3. 性能基準目標是否合理
4. CI 雙環境策略可行性
5. OWASP LLM Top 10 涵蓋度
6. E2E 案例設計
7. DoD（Definition of Done）強度
8. Mock vs Real 雙跑機制

給出 1000 字內 review，繁體中文。
```

---

## Prompt 5：Review `14-security-deep-dive.md`（安全合規）

**建議 high effort**

```
你是有 10+ 年經驗的企業資安專家，熟悉 STRIDE / OWASP / SOC 2 / GDPR / ISO 27001。

請 review：
`C:\Users\Chris\Downloads\ai-semantic-kernel-framework-project\docs\03-implementation\agent-harness-planning\14-security-deep-dive.md`

評估：
1. STRIDE 威脅模型完整度
2. OWASP LLM Top 10 防禦
3. 加密策略（at rest / in transit / column-level）
4. RBAC + Multi-tenant 隔離強度
5. Sandbox 多層設計
6. Audit + Hash chain 安全性
7. GDPR 合規能力
8. Incident response runbook
9. 對比業界 SaaS 標準（如 Stripe / Datadog）

給出 1000 字內 review，繁體中文。
```

---

## Prompt 6：Review `15-saas-readiness.md`（SaaS 能力）

**建議 high effort**

```
你是有 8+ 年 SaaS 平台經驗的 product engineer。

請 review：
`C:\Users\Chris\Downloads\ai-semantic-kernel-framework-project\docs\03-implementation\agent-harness-planning\15-saas-readiness.md`

評估：
1. Tenant lifecycle 完整度
2. SLA 設計合理性
3. Billing 整合預留
4. DR 策略（RPO / RTO）
5. Tenant onboarding 自動化
6. Feature flags 設計
7. Multi-tenancy scaling 路線
8. Stage 1 / 2 / 3 / 4 演進是否合理

給出 1000 字內 review，繁體中文。
```

---

## Prompt 7：Review `16-frontend-design.md`（前端設計）

**建議 high effort**

```
你是有 8+ 年經驗的資深前端架構師，熟悉 React 18 / TypeScript / 設計系統 / a11y。

請 review：
`C:\Users\Chris\Downloads\ai-semantic-kernel-framework-project\docs\03-implementation\agent-harness-planning\16-frontend-design.md`

評估：
1. Chat 頁面 layout 是否合理
2. 11 範疇 features 組織是否清晰
3. State management 策略（Zustand + TanStack Query）
4. SSE stream 處理機制
5. TypeScript codegen 流程
6. 性能預算合理性
7. A11y / i18n 規劃
8. DevUI 設計是否實用

給出 800 字內 review，繁體中文。
```

---

## Prompt 8：Review `13-deployment-and-devops.md`（部署 DevOps）

**建議 high effort**

```
你是有 10+ 年經驗的 DevOps / SRE 專家，熟悉 Docker / K8s / CI/CD / Azure。

請 review：
`C:\Users\Chris\Downloads\ai-semantic-kernel-framework-project\docs\03-implementation\agent-harness-planning\13-deployment-and-devops.md`

評估：
1. 4 環境分層合理性
2. 8 階段 CI/CD pipeline
3. Docker 配置（多階段建構 / health check）
4. Secret 管理三層
5. Migration / Rollback 策略
6. Observability stack 完整度
7. K8s 預備設計（HPA / probe）
8. DR / Backup 策略

給出 1000 字內 review，繁體中文。
```

---

## 執行策略推薦

### 第 1 優先（強烈建議）
- **Prompt 1**：01 + 10（範疇規格 + 3 大原則）— 用 max effort 跑

### 第 2 優先（建議）
- **Prompt 2**：06（路線圖）— 用 high effort 跑
- **Prompt 3**：12（範疇契約）— Phase 49.3 必用，要早 review

### 第 3 優先（可選）
- Prompt 4 / 5 / 6 / 7 / 8（11 / 14 / 15 / 16 / 13）

---

## 整合 Review 用的 Prompt

```
（review 都完成後在主 session 貼入此 prompt 整合）

以下是 V2 規劃文件的獨立 review reports：

## Report 1（Prompt 1）：01-eleven-categories-spec.md + 10-server-side-philosophy.md
[貼入回應]

## Report 2（Prompt 2）：06-phase-roadmap.md
[貼入回應]

## Report 3（Prompt 3）：12-category-contracts.md
[貼入回應]

## Report 4-8（Prompt 4-8）：（如有）
[貼入回應]

---

## 整合任務

請進行：

### 1. 共通問題識別
列出**多份 report 都提到的問題**（信號最強）

### 2. 獨有問題評估
列出單份 report 獨有的問題

### 3. 衝突意見
列出 reports 間有衝突的部分

### 4. 修訂優先級
- P0（必修）
- P1（應修）
- P2（可修）

### 5. 執行修改
按 P0 → P1 順序，**直接修改對應規劃文件**並回報。

完成後總結修改範圍。
```

---

## 不需 review 的文件

以下文件**不需獨立 review**（戰略性質、工具性質、或已 review）：

- ❌ `README.md` — 索引
- ❌ `00-v2-vision.md` — 戰略，由你直接 review
- ❌ `03-rebirth-strategy.md` — 主 session context 充足
- ❌ `04-anti-patterns.md` — ✅ 已執行 + 修訂
- ❌ `02-architecture-design.md` — ✅ 已執行 + 修訂
- ❌ `09-db-schema-design.md` — ✅ 已執行 + 修訂
- ❌ `05-reference-strategy.md` — 工具性質
- ❌ `07-tech-stack-decisions.md` — 需配合公司現實，由你判斷
- ❌ `08-glossary.md` — 工具性質

---

## 工作流建議

```
今天（主 session）：
  ✅ 已完成 — 17 份規劃文件 + P0 修訂

下個工作日（用戶切換 session）：
  ☐ 開新 session A → 貼 Prompt 1（max effort）
  ☐ 開新 session B → 貼 Prompt 2（high effort）
  
  可選：
  ☐ 開新 session C → 貼 Prompt 3
  ☐ 主 session 開子代理 → 貼 Prompt 4-8

Review 完成後：
  ☐ 回主 session 貼整合 prompt
  ☐ 整合修改規劃文件

整合完成後：
  ☐ 啟動 Phase 49 Sprint 49.1
```
