# V2 規劃文件 P0 修訂報告

**修訂日期**：2026-04-23
**修訂者**：本主 session
**範圍**：3 大原則補強 + 9 個 P0 修訂

---

## 修訂背景

V2 規劃文件原 10 份完成後，經以下檢查發現需修訂：

1. **3 子代理平行 review**（02 / 04 / 09）— 發現 9 個 P0 問題
2. **用戶提醒**：規劃需強化 3 大原則
   - Server-side 架構（不是本地 CC）
   - LLM Provider 中性（不綁 Claude SDK）
   - CC 架構參考但 server-side 轉化（不照搬）

---

## 第一批修訂：3 大原則補強

### 新建文件

#### `10-server-side-philosophy.md` ⭐⭐⭐
- **權威定義**3 大最高指導原則
- 詳細 CC → V2 server-side 轉化映射表
- 違反原則的後果說明
- 應用矩陣（11 範疇 × 3 原則 check）

### 修訂文件

#### `00-v2-vision.md`
- 強化「理念 4 LLM Provider Neutrality」 — 加入完整 ChatClient ABC 圖示 + 強制規則
- 強化「理念 5 Server-Side Native + CC 參考但轉化」 — 明確「參考 + 轉化原則」

#### `01-eleven-categories-spec.md`（範疇 2）
- 加入「⚠️ 關鍵理解：CC 工具與 V2 工具完全不同」對比表
- CC 6 大類降為「僅作架構參考，非實作模板」
- V2 規格擴充為**企業 server-side 8 大類**：
  1. 企業資料查詢 / 2. 企業資料變更 / 3. 沙盒執行 / 4. 網絡（治理代理）
  5. 記憶 / 6. 子代理 / 7. 業務領域 / 8. HITL / Governance
- 強調**禁止使用 OpenAI/Anthropic 原生 schema**，必須用中性 ToolSpec

#### `02-architecture-design.md`（約束 3）
- 「Adapter 層強制」改為「LLM Provider 中性」標題
- 加入禁止 import 清單（`openai` / `anthropic`）
- 加入「30 分鐘換 provider」驗收標準

#### `05-reference-strategy.md`
- 加入「⚠️ 關鍵注意事項」明確「不要照搬」清單
- 簡要 CC→V2 轉化映射（連回 10-server-side-philosophy.md 為權威）

---

## 第二批修訂：9 個 P0 問題

### 文件 02 架構設計（4 個 P0）

#### P0-1：重畫 5 層分層圖納入 business_domain
**修改**：原 4 層改為 5 層 + 跨切面
- Layer 1: API
- Layer 2: **Business Domain**（新明確歸屬）
- Layer 3: Agent Harness
- Layer 4a: Adapters（主鏈）
- Layer 4b: Runtime（反向依賴例外）
- Layer 5: Infrastructure
- Cross-cutting: governance / identity / observability

#### P0-2：拆解 platform/ 為獨立目錄
**修改**：原 `platform/` 改為 4 個獨立目錄
- `governance/` — HITL / Risk / Audit / Compliance
- `identity/` — Auth / RBAC / Multi-tenancy
- `observability/` — Tracing / Metrics / Logging / Cost
- `runtime/` — Workers / Task Queue / Scheduler

#### P0-3：約束 1 與分層圖一致化
**修改**：明示 workers 反向依賴例外
- `runtime/workers/` 是「反向依賴例外」
- 在分層圖中明確標註

#### P0-4：去除 0X 數字前綴
**修改**：所有範疇目錄從 `01_xxx` / `02_xxx` 等改為純名稱
- `01_orchestrator_loop` → `orchestrator_loop`
- `02_tools` → `tools`
- ...（共 11 個範疇全部更新）
- **理由**：違反 Python import 慣例（`from agent_harness.01_xxx` 不合法）

### 文件 04 反模式（2 個 P0）

#### P0-5：強化 AP-3 散落為 lint rule
**修改**：原版「PR 模板自檢」不夠強制，加入 4 個 CI lint rules：
- Lint 3.1：範疇代碼歸屬檢查
- Lint 3.2：禁止散落關鍵字（approval / risk / audit / permission 不可跨目錄）
- Lint 3.3：禁止 LLM SDK 直接 import
- Lint 3.4：禁止裸組 messages list
- Phase 49.3 建立 lint scripts，Phase 50 開始 CI 強制執行

#### P0-6：新增 AP-11 命名版本後綴遺留
**修改**：新增反模式 11
- 證據：V1 的 `orchestrator_v2.py` / `step8_postprocess.py`（名為 verifier 實為 finalize）
- Rule 11.1：禁止版本後綴
- Rule 11.2：命名行為驗證
- Rule 11.3：Refactor 完整性

### 文件 09 DB Schema（5 個 P0）

#### P0-7：修正 audit_log trigger 語法
**修改**：原 `BEFORE UPDATE OR DELETE OR TRUNCATE FOR EACH ROW` 不合法
- 拆為 ROW-level（UPDATE/DELETE）+ STATEMENT-level（TRUNCATE）
- 加入 DBA 部署檢查清單（撤銷 TRUNCATE 權限、role 分離）

#### P0-8：所有 session-scoped 表加 tenant_id
**修改**：原版只主業務表有 tenant_id
- 所有 session-scoped 表加 `tenant_id UUID NOT NULL`：
  - sessions, messages, tool_calls, tool_results, state_snapshots, etc.

#### P0-9：啟用 PostgreSQL Row-Level Security (RLS)
**修改**：新增 RLS policies
- 所有帶 tenant_id 的表 `ENABLE ROW LEVEL SECURITY`
- 統一 policy：`tenant_id = current_setting('app.tenant_id')::uuid`
- Connection 層注入 tenant context
- 禁止繞過 RLS 機制

#### P0-10：補 5 個 production-critical 表
**修改**：新增 Group 12「Production-Critical」
- `api_keys` — Tenant API 金鑰（bcrypt hash）
- `rate_limits` — Per-tenant 配額追蹤
- `cost_ledger` — 細粒度成本紀錄
- `llm_invocations` — 每次 LLM call 紀錄（含 prompt cache tokens）
- `outbox` — 事務性訊息發送（Teams 通知用）

#### P0-11：messages / audit_log / message_events Day 1 partition
**修改**：3 高量表改為月度 partition
- `messages` 月度 partition + 自動建立未來分區
- `audit_log` 月度 partition + 90 天冷儲分層
- `message_events` 月度 partition + 30 天保留

### Bonus 修訂

#### Cost 精度提升
- 所有 `cost_usd` 從 `DECIMAL(10, 4)` 改為 `DECIMAL(14, 6)`
- **理由**：GPT-5.4-nano 等便宜模型已超出 4 位精度

#### Migration 順序重整
- 原 10 個 migration 改為 14 個
- audit_log 提前到 0002（其他表 insert 都要 audit）
- api_keys / rate_limits 提前（API 開始就需要）
- RLS policies 最後一個 migration（讓所有表建好後套用）

---

## 修訂後文件清單

```
docs/03-implementation/agent-harness-planning/
├── README.md                                  ← 已更新索引
├── 00-v2-vision.md                            ← 強化理念 4+5
├── 01-eleven-categories-spec.md               ← 範疇 2 重寫
├── 02-architecture-design.md                  ← 4 層 → 5 層 + 拆 platform
├── 03-rebirth-strategy.md                     ← 未動
├── 04-anti-patterns.md                        ← 強化 AP-3 + 新增 AP-11
├── 05-reference-strategy.md                   ← 加 CC→V2 轉化說明
├── 06-phase-roadmap.md                        ← 未動（待 user review 後動）
├── 07-tech-stack-decisions.md                 ← 未動
├── 08-glossary.md                             ← 未動
├── 09-db-schema-design.md                     ← 5 個 P0 + Bonus 修訂
└── 10-server-side-philosophy.md               ⭐ 新增（最高原則）
```

---

## 預期影響

### V2 規劃完整度
- **修訂前**：80%（缺 09 / 缺 3 大原則明示）
- **修訂後**：**95%**（10 份核心文件 + 1 份哲學文件）

### V2 起點對齊度
- V1：27%
- V2 目標：75%+
- **修訂後路線更穩**：3 大原則明確 + lint 強制 + RLS 落實

### Phase 49 Sprint 49.2 影響
- DB schema migration 從 10 個增為 14 個
- 加入 5 個 production-critical 表
- Sprint 49.2 工作量增加約 30%（**仍可在 1 sprint 內完成，因為從零建立比改 V1 schema 容易**）

---

## 待後續處理

### 仍待 P1/P2 修訂（非緊急）
- 0X 前綴檔案 / class 命名（同步全項目其他文件）
- ENUM lookup table 化
- UUID v4 → v7
- compacted_from_ids 改關聯表
- ToolSpec 中性格式詳細規格

### 仍待新 session review 的文件
- `01-eleven-categories-spec.md` — 完整 11 範疇規格（已修範疇 2，但其他範疇仍待 review）
- `06-phase-roadmap.md` — Phase 路線圖時程合理性

### 仍待補的規劃文件
- `11-test-strategy.md` — 測試策略（Phase 50+ 邊做邊建）
- `12-category-contracts.md` — 範疇間整合契約（Phase 49.3 建立）

---

## 結語

P0 全部修訂完成。**V2 規劃方向**已根據 3 大原則 + review 意見強化。

下一步建議：
1. 用戶審視本修訂報告
2. 決定是否啟動新 session review 01 + 06（用戶提供的 prompt 已準備）
3. 或直接進入 Phase 49 Sprint 49.1 規劃（V1 封存 + V2 骨架建立）
