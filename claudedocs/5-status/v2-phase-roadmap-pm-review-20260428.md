# V2 Phase 路線圖 — 項目管理視角 Review 報告

**Reviewer**：項目管理獨立 review（10+ 年 agile / AI 項目經驗視角）
**日期**：2026-04-28
**Scope**：`docs/03-implementation/agent-harness-planning/06-phase-roadmap.md`
**參考依賴文件**：00, 01, 02, 09, 11, 13, 14, 15, 16

---

## 整體可行性評估：**5.5 / 10**

**核心判斷**：路線圖戰略方向正確，但 16 sprint 達 75% 對齊度的 deliverables-to-time 比例**普遍超載 1.5-2.5 倍**。Phase 49 與 Phase 55 是兩大重災區。1 個資深開發者 + AI 助手在 4 個月內達成路線圖宣稱範圍的機率偏低。

---

## 各 Phase 評估

### Phase 49: Foundation（3 sprint）— **過短，建議 +1 sprint**

| 項目 | 評估 |
|------|------|
| 時程合理性 | **過短**。3 sprint 包山包海。 |
| 主要風險 | Sprint 49.2 一週要 ship 14+ ORM models + Alembic + RLS policies + Qdrant tenant namespace + audit append-only triggers — 對照 09 文件，RLS 涵蓋 14+ 張表並要求 `SET LOCAL app.tenant_id` per-request。RLS 設計+測試本身就是 3-5 天工作。<br/>Sprint 49.3 把 Worker queue **選型決策** + PoC + OTel + 全 FastAPI + Frontend 骨架塞一週。Celery vs Temporal 是架構級決定（影響後續所有 long-running operation），業界通常 2-3 週評估。 |
| 與其他文件一致性 | 09 RLS 工作量未在路線圖反映；13 dev 環境 docker-compose 已涵蓋；11 CI gate 從 Phase 50 起 — 但路線圖未明示 CI pipeline 何時建立（理應 49.3 即建）。 |
| 建議調整 | **拆為 4 sprint**：49.1 V1 封存+骨架；49.2 DB schema + Alembic（不含 RLS 細節）；49.3 RLS + Qdrant + Audit；49.4 Adapters + Worker queue 選型 + OTel + CI pipeline。 |

### Phase 50: Loop Core（2 sprint）— **基本合理**

- 範疇 1 + 6 已是 V2 最小核心，2 sprint 可達成。
- **風險**：「Anti-Pattern 1 零違反」需 lint rule 配合，但工具未在 49 完成 → 應前置到 49.3（CI 建立時一併）。
- **與測試文件一致性**：11 文件要求 CI 強制從 Phase 50 起 — 路線圖未明確規定 50.1 必須 PR 觸發 CI 全套。

### Phase 51: Tools + Memory（2 sprint）— **scope 不一致**

- 01 範疇 2 規格列 **8 大類工具**（企業查詢 / 變更 / 沙盒 / 網絡 / 記憶 / 子代理 / 業務 / HITL）。Sprint 51.1 只交 4 類（memory 占位、search、exec、hitl），**企業 D365/SAP/Salesforce 工具被推遲到 55.1**，這意味 51-54 之間 agent 沒有真實業務工具可呼叫，端到端閉環缺乏材料。
- **建議**：51.1 增加 1-2 個簡化版企業工具（mock backend 即可），讓 52-54 demo 案例有真材料。
- 範疇 3 記憶層 1 sprint 做 5 層 + 提取 worker + Qdrant 整合 — **過於緊湊**。

### Phase 52: Context + Prompt（2 sprint）— **合理**

- Compaction + observation masking + JIT retrieval + token counter 1 sprint 可行（核心邏輯不複雜）。
- 30+ turn 對話測試案例需要前置真實 fixture — 依賴 51 的工具就緒。

### Phase 53: State + Error + Guardrails（3 sprint）— **53.3 嚴重超載**

| Sprint | 評估 |
|--------|------|
| 53.1 State | 合理，1 sprint 可達 |
| 53.2 Error | 合理 |
| **53.3 Guardrails** | **約 2 週工作量**。3 層 guardrails + tripwire + V1 Risk 邏輯遷移 + V1 HITL 邏輯遷移 + audit append-only 驗證 + frontend governance 頁。**14 文件**安全合規重點實作就在此 sprint，量級顯著高於其他單一 sprint。 |

**建議**：53 拆為 4 sprint（State / Error / Guardrails 核心 / Governance 整合 + Frontend），或將 frontend governance 頁推遲到 55。

### Phase 54: Verification + Subagent（2 sprint）— **基本合理**

- Subagent 4 模式（Fork/Teammate/Handoff/AsTool）+ MAF Builders 整合 1 sprint 偏緊但可達。
- LLM-judge 用獨立 subagent 需與 54.2 反覆迭代，54.1 後段預留時間。

### Phase 55: Production（2 sprint）— **嚴重不足，至少 4 sprint**

- 55.1 試圖在 **1 週**重新設計 5 個業務領域（patrol/correlation/rootcause/audit/incident）+ 業務工具註冊 + 業務 API + Frontend agents/workflows 頁面。**結構性不可能**。光是 frontend agents+workflows 頁面（依 16 文件 React Flow + 自訂 node）就是 1-2 sprint。
- 55.2 完整端到端 + canary + 性能調優 + 全文件化 + DevUI 11 範疇 dashboard — 1 sprint 不可能。

**建議**：55 拆為 **4 sprint**（業務領域 backend / 業務領域 frontend / 端到端 + 性能 / Canary + 文件化 + retro），或砍部分業務領域到 Phase 56。

---

## 整體風險清單（依嚴重度）

1. **🔴 CRITICAL — Sprint scope 普遍超載 1.5-2.5 倍**：每個 sprint 1 週的單位時間，但 deliverables 對應 1.5-2.5 週實際工作量。1 senior + AI 約等於 1.3-1.5 工作 FTE，無法吸收。
2. **🔴 CRITICAL — Phase 55 結構性不可能**：5 個業務領域 + 完整 frontend + canary + 文件，2 sprint 完成是空話。
3. **🟡 HIGH — Worker queue 選型在 49.3 是賭注**：Celery vs Temporal 決定影響全部 long-running 設計。一旦 PoC 後悔重選將拖延 2-3 sprint。
4. **🟡 HIGH — Frontend 工作量低估**：16 文件 9 個頁面 + 5 個 DevUI 組件，路線圖只排到 chat（50.2）+ governance（53.3）+ agents/workflows（55.1）。Memory / audit / tools / admin / dashboard / DevUI 5 個頁面**未排程**。
5. **🟡 HIGH — CI pipeline 建立時間未指定**：11 文件要求 Phase 50 起 CI 強制，但路線圖沒指明 49.3 建 CI；若 50.1 才補 CI，會與功能開發混亂。
6. **🟢 MEDIUM — RLS 工作量隱藏**：09 文件強調所有 session-scoped 表 RLS + per-request `SET LOCAL`，這是 3-5 天獨立工作，路線圖只一行帶過。
7. **🟢 MEDIUM — SaaS Readiness 未涵蓋**：15 文件 Stage 1 多租戶內部 SaaS 在 56-58；路線圖到 55 為止只達 Stage 0（1-3 tenant 手動）。對齊但需明示「V2 完成 ≠ SaaS-ready」。

---

## 與其他文件的衝突

| 衝突 | 詳情 |
|------|------|
| **09 vs 06** | RLS 工作量、Qdrant tenant namespace 在 06 一行帶過，09 是 multi-tenant 強制重點 |
| **11 vs 06** | CI 從 Phase 50 強制 — 06 未指定 CI 建立 sprint |
| **13 vs 06** | 13 列 Dev/Integration/Staging/Prod 4 環境 + 5 階段 pipeline，06 只談 Dev docker-compose |
| **14 vs 06** | 14 安全合規重點放 53，但 53.3 已超載 |
| **15 vs 06** | 15 Stage 1 SaaS 需 Phase 56-58 — 06 路線圖到 55，**對齊但需文件明示 V2 ≠ SaaS-ready** |
| **16 vs 06** | 9 個前端頁面 + DevUI 5 組件，06 只排 3 個 |
| **01 vs 06** | 01 範疇 2 列 8 大類工具，06 Phase 51 只交 4 類，企業工具延到 55 |

---

## 建議的修訂版路線圖

維持 7 Phase 結構，但 **16 sprint 擴為 22 sprint**（約 5.5 個月）：

| Phase | 原 sprint | 修訂 sprint | 主要調整 |
|-------|----------|-------------|---------|
| 49 Foundation | 3 | **4** | 拆 RLS / Worker queue 選型 / CI 建立 |
| 50 Loop Core | 2 | 2 | 不變 |
| 51 Tools + Memory | 2 | **3** | 51.0 增加最小可用企業工具（mock backend） |
| 52 Context + Prompt | 2 | 2 | 不變 |
| 53 State + Error + Guardrails | 3 | **4** | 53.3 拆 Guardrails 核心 + Governance/Frontend |
| 54 Verification + Subagent | 2 | 2 | 不變 |
| 55 Production | 2 | **5** | 業務 backend / 業務 frontend / 缺漏前端頁 / 端到端+性能 / Canary+retro |
| **合計** | 16 | **22** | +6 sprint，約 +6 週 |

或維持 16 sprint 不變，但**砍 scope**：

- 業務領域只交 2 個（patrol + audit），其餘推 Phase 56
- Frontend 只交 chat / governance / agents 3 頁
- Verification 只交 rules-based + LLM-judge，砍 visual
- Subagent 砍 Teammate（複雜度最高）

---

## 信心評分

| 指標 | 機率 |
|------|------|
| 16 sprint 達 75% 對齊度 | **30-35%** |
| 4 個月達成原訂 scope | **20-25%** |
| 22 sprint 達 75% 對齊度（修訂版） | **65-70%** |
| 16 sprint 達 60% 對齊度（砍 scope 版） | **70-75%** |
| 1 senior + AI 配置足夠 | **40-50%**（建議至少 1.5 FTE 或加 1 個 full-stack 開發者） |

---

## 最終建議

1. **採用修訂版 22 sprint** 或 **明確砍 scope 版**，二選一，不要硬撐 16 sprint 完整 scope。
2. **49.1 立即補建 CI pipeline**（與骨架同步），不要拖到 50。
3. **51.0 補一個簡化企業工具**（哪怕 mock），讓 52-54 demo 有真材料。
4. **53 拆 4 sprint**，避免 53.3 黑洞。
5. **55 至少 4 sprint** 或砍業務領域數量。
6. **每 Phase 結束強制 retro + scope 重評**，不達 Definition of Done 不進下一 Phase。
7. **明文說明 V2 完成 ≠ SaaS-ready**，避免 stakeholder 誤解。

---

**核心結論**：路線圖**戰略對、節奏錯**。願景與架構文件（00-05, 10）品質高，但時程估算偏向 best-case，缺乏 1 senior + AI 真實 throughput 校準。建議與開發者重新跑一次「vertical slice」估算（拿 49.2 的 14 表 RLS 為例做 1 週試做），用實測 throughput 校正後續 sprint。
