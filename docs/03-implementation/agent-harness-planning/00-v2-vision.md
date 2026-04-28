# V2 願景文件

**建立日期**：2026-04-23
**版本**：V2.1（2026-04-28：加 V2 ≠ SaaS-ready 聲明）

---

## 一句話願景

> **建立業界第一個「企業級治理 + CC 級閉環」的混合 agent 平台 — 既有 Claude Code 等級的 agent 智能閉環，又有企業級多租戶、HITL、合規、審計能力**。

---

## ⚠️ 重要範圍聲明（2026-04-28 新增）

> **V2 完成（Phase 55）≠ SaaS-ready**

V2（Phase 49-55，22 sprint，約 5.5 個月）達成的是：
- ✅ **核心能力**：11 範疇 + 範疇 12（Observability）全部達 Level 4+（75%+ 對齊度）
- ✅ **業務領域**：5 個 IPA 業務 domain（patrol / correlation / rootcause / audit / incident）
- ✅ **Multi-tenant 能力**：RLS + 雙軸 memory + tenant-aware tracing
- ✅ **Canary 試用**：內部 1-2 用戶
- ✅ **完整 governance**：HITL + audit + 3 層 guardrails

**V2 *不*達成**（推遲到 Phase 56-58）：
- ❌ **SaaS Stage 1**（多租戶內部 SaaS / billing / SLA / DR）— 詳見 [`15-saas-readiness.md`](./15-saas-readiness.md)
- ❌ **第 13 範疇 Cost Tracking 完整實作**（Phase 56+）
- ❌ **多 provider 並行 routing 生產化**（Phase 57+）
- ❌ **公網開放 / 公開 self-service signup**

此聲明避免 stakeholder 期望錯位。如需 SaaS-ready 路線圖，見 V3 規劃（V2 完成後啟動）。

---

## 為什麼需要 V2

### V1 的 4 個結構性問題

#### 1. 「以 MAF 為基礎」的起點誤判
- MAF 真實只佔 5% 代碼
- MAF 不是企業 agent 平台框架，是 LLM provider + workflow 整合工具
- V1 起步時 MAF 還是 Preview，不夠成熟
- 結果：項目實質上不是 MAF 項目，但目錄組織仍延續 MAF 思維

#### 2. 「Pipeline ≠ Agent Loop」的根本誤解
- V1 主流量是 8-step **線性 Pipeline**
- agent harness 業界標準是 **TAO / ReAct loop**
- 兩者本質不同：Pipeline 一次性執行，Loop 多輪迭代
- 結果：範疇 1（Orchestrator）真實對齊度只 18%

#### 3. 「Phase 增量演進」累積散落
- 44 個 Phase 中沒有按 11 範疇組織代碼
- Guardrails 散在 6 處、Orchestrator 散在 5 處
- 每個範疇平均散落 4 個目錄
- 結果：跨範疇協作困難，整體對齊度只 27%

#### 4. 「結構槽位但無內容」(Potemkin Features)
- Memory：Step 1 跑了但沒實際讀 mem0
- Verification：postprocess 名稱誤導，實為 finalize
- Context Mgmt：完全沒有 context rot 防禦
- 結果：許多功能「看似有但無效」

---

## V2 的 5 個核心理念

### 理念 1：**11 範疇驅動，不是 Phase 驅動**

V1 是「Phase 1 → Phase 2 → ... → Phase 48」線性增量。
V2 是「11 範疇平行覆蓋，每個範疇獨立成熟」。

| 維度 | V1 | V2 |
|------|----|----|
| 組織方式 | 按 Phase | 按 11 範疇 |
| 進度衡量 | Sprint 完成數 | 11 範疇成熟度 |
| 代碼歸屬 | 散落 | 單一範疇目錄 |
| 驗證方式 | 端到端測試 | 範疇獨立測試 + 整合測試 |

### 理念 2：**閉環為先（Loop-First）**

V1 是 Pipeline 思維 — 進入 → 處理 → 退出。
V2 是 Loop 思維 — TAO 迴圈直到完成。

```
V1 主流量：
  Input → Step1 → Step2 → ... → Step8 → Output
  （線性 8 步）

V2 主流量：
  Input → [Loop: assemble → infer → parse → tool_exec → result_inject] → Output
  （直到 stop_reason=end_turn 或達上限）
```

### 理念 3：**「企業治理 + Agent 智能」雙軌平衡**

V1 強在治理（HITL / Risk），弱在智能（Loop / Memory / Verification）。
V2 兩者並重：

```
V2 架構雙軌：
  ┌─────────────────────────────────────┐
  │ Agent Harness（11 範疇）             │ ← agent 智能
  │  Loop / Tools / Memory / Context...  │
  └──────────────┬──────────────────────┘
                 ↕ 緊密耦合
  ┌──────────────┴──────────────────────┐
  │ Platform Governance Layer            │ ← 企業治理
  │  Multi-tenant / RBAC / HITL / Audit  │
  └─────────────────────────────────────┘
```

### 理念 4：**LLM Provider Neutrality（LLM 供應商完全中性）** ⭐⭐⭐

> **這是 V2 的最高原則之一。詳見 `10-server-side-philosophy.md`**

V1 主流量綁 Azure OpenAI + 部分 Anthropic SDK。
V2 透過 Adapter 層**完全解耦** agent_harness 與任何 LLM 供應商：

```
        ┌──────────────────────────────────┐
        │   Agent Harness（11 範疇）        │
        │   只依賴 ChatClient ABC          │
        │   ⛔ 禁止 import 任何 LLM SDK    │
        └──────────────┬───────────────────┘
                       ↓
        ┌──────────────────────────────────┐
        │   adapters/_base/                 │
        │   ChatClient ABC（中性介面）      │
        └──────────────┬───────────────────┘
                       ↓
        ┌──────────────────────────────────┐
        │   adapters/                       │
        ├──────────────────────────────────┤
        │   azure_openai/  ← 主（公司現況） │
        │   anthropic/     ← 備（公司開放後）│
        │   openai/        ← 備援           │
        │   foundry/       ← Azure Foundry  │
        └──────────────────────────────────┘
```

**強制規則**：
- ❌ `agent_harness/**` 任何檔案禁止 `import openai` / `import anthropic`
- ❌ 工具定義禁止用 OpenAI / Anthropic 原生 schema
- ❌ Message 格式禁止用任一供應商原生格式
- ✅ 全透過 `ChatClient` ABC + 中性 `ToolSpec` + 中性 `Message`
- ✅ CI 強制 lint 檢查

**驗收標準**：「30 分鐘換 provider」測試 — 主流量從 Azure OpenAI 切到 Anthropic 只改 config 不改代碼。

### 理念 5：**Server-Side Native + CC 架構參考但轉化** ⭐⭐⭐

> **詳見 `10-server-side-philosophy.md`**

V2 是**部署在企業伺服器的後端服務**（不是本地工具），同時**架構模式參考 Claude Code**（業界最完整 agent harness 實作）。

**參考 + 轉化原則**：
- ✅ **參考 CC**：架構模式、流程順序、解決問題思路
- ❌ **不照搬 CC**：具體 API、本地檔案假設、單用戶模型
- ⭐ **轉化為 server-side**：所有「本地」概念改為「server-side + multi-tenant」

從 Day 1 為**企業 server side** 設計：

| 維度 | CC（本地）| V2（企業 server）|
|------|----------|----------------|
| 用戶 | 終端使用者 | 遠端瀏覽器 |
| 工具 | Bash/Read/Write | 企業 API（D365/SAP/ServiceNow）|
| 記憶 | 本地檔案 | 多租戶 DB + Vector |
| HITL | 偶爾 | **密集**（幾乎每寫操作） |
| 隔離 | 無 | tenant × role × policy |

---

## V2 的 6 個非目標（What V2 is NOT）

明確 V2 不追求的：

1. ❌ **不追求 100% CC 對齊** — CC 是本地工具，V2 是企業平台。對齊到 75% 已是業界第一
2. ❌ **不追求 MAF 完整性** — MAF 只在需要 Multi-agent Builder 時保留
3. ❌ **不追求商業 SaaS 規模** — 先做企業內部部署成熟版本
4. ❌ **不追求 K8s 生產就緒**（Phase 49-55）— 容器化即可，K8s 是後續
5. ❌ **不追求支援所有 LLM** — 主推 Azure OpenAI，Adapter 層留接口
6. ❌ **不追求遷移 V1 數據** — 項目從未上線，無歷史包袱

---

## V2 的 5 個成功標準

Phase 55 完成時應達到：

### 標準 1：**11 範疇真實對齊度 ≥ 75%**
每個範疇單獨測試 + 整合測試 + 主流量驗證。

### 標準 2：**端到端閉環測試通過**
測試案例：「APAC Q2 銷售下降 15% 分析報告」
- agent 自主多輪呼叫工具（salesforce / erp / mem0 / bi）
- 中間有 thinking blocks
- 觸發 HITL（生成報告前）
- LLM-as-judge 驗證輸出
- 完整 audit trail

### 標準 3：**性能指標達標**
- 簡單問題：1-2 turn / < 5 秒
- 中等任務：5-10 turn / < 30 秒
- 複雜任務：20-50 turn / < 5 分鐘
- Context window 利用率 < 80%（autoCompact 運作）

### 標準 4：**安全合規通過**
- Input guardrail（PII / jailbreak）
- Output guardrail（毒性 / 敏感資訊）
- Tool permission matrix（role × tool × tenant）
- Tripwire 自動中斷
- Audit log 不可篡改

### 標準 5：**業務領域功能完整接入**
- patrol / correlation / rootcause / audit / incident 全部對接新 agent harness
- 業務功能可用率 ≥ 95%

---

## V2 vs V1 對比

| 維度 | V1 | V2 |
|------|----|----|
| 起點哲學 | MAF + 增量演進 | 11 範疇 + 閉環優先 |
| 主流量架構 | 8-step Pipeline | TAO / ReAct loop |
| 對齊度 | 27% | 75%+ |
| 代碼分佈 | 跨 4-6 目錄散落 | 11 範疇單一歸屬 |
| Provider | Azure 為主 | Adapter 層多供應商 |
| 記憶 | preload 一次 | 工具化（agent 可隨時 query） |
| Context Mgmt | 0%（無防禦） | compaction + masking + JIT |
| Verification | 0%（無迴圈） | rules + LLM-judge + visual |
| 開發週期 | 5+ 個月 / Phase | 約 1 個月 / Phase |

---

## V2 的核心約束

開發過程中必須遵守：

### 約束 1：**單一範疇歸屬原則**
任何代碼必須明確歸屬於 11 範疇之一（或 platform / business_domain / infrastructure / adapters）。
**禁止跨範疇雜湊**。

### 約束 2：**主流量驗證原則**
任何功能必須能在 UnifiedChat-V2 → API → Agent Loop 主流量中驗證。
**禁止「代碼存在但不在主流量」的 Potemkin Feature**。

### 約束 3：**Adapter 層隔離原則**
Agent Harness 代碼**禁止直接 import** `azure-ai`、`anthropic`、`openai` 等供應商 SDK。
必須透過 `adapters/_base/` 的 ABC。

### 約束 4：**Anti-Pattern 檢查原則**
每個 PR 必須通過 `04-anti-patterns.md` 檢查清單。

### 約束 5：**測試優先原則**
- 範疇單元測試 ≥ 80%
- 範疇整合測試 ≥ 60%
- 端到端閉環測試 ≥ 1 個關鍵案例

---

## V2 的 4 個技術賭注

V2 押注以下方向（如果押錯需重新評估）：

### 賭注 1：**TAO Loop 是正確架構**
- 業界主流（CC / OpenAI Codex / LangGraph / Anthropic SDK）都採用
- 概率：95%

### 賭注 2：**11 範疇分類能涵蓋所有需求**
- 來自業界研究的歸納
- 概率：85%（可能需新增第 12 範疇如「Cost Control」）

### 賭注 3：**Azure OpenAI 能勝任 agent loop**
- GPT-5.4 已支援 native function calling + parallel tool calls
- 概率：90%（mini 版可能不夠，要求用 5.4 而非 mini）

### 賭注 4：**Worker Queue 路線正確**
- Agent loop 是長時操作，必須 worker 化
- 候選：Celery / RQ / Temporal
- 概率：95%（具體選型再議）

---

## 心態與工作方式

### 對 AI 助手（Claude）的期待
- 主動指出 V1 的問題重現風險
- 嚴格按 11 範疇歸類新代碼
- 主流量驗證 + 範疇成熟度標籤
- 避免「為了好看給高分」

### 對開發者的期待
- 接受「重新出發」需要約 4 個月
- 接受 V2 不會 100% 對齊 CC（75% 已是業界第一）
- 接受不能跨範疇雜湊代碼

---

## 下一步

確認本願景文件後，依序檢視：
1. `01-eleven-categories-spec.md` — 11 範疇完整規格
2. `02-architecture-design.md` — 架構設計
3. `03-rebirth-strategy.md` — 重生策略
4. `04-anti-patterns.md` — V1 反模式
5. `05-reference-strategy.md` — 參考策略
6. `06-phase-roadmap.md` — Phase 路線圖
7. `07-tech-stack-decisions.md` — 技術選型
