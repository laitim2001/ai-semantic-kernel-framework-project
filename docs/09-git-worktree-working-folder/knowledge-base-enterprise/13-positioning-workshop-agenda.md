# 13 - 定位 Workshop 議程

**目的**：在啟動 P0 wiring 修復 + 規劃 6-9 month roadmap 前，釐清 12 個影響後續所有技術與商業決策嘅 stakeholder questions。

**建議時長**：60-90 分鐘
**建議出席**：Product Owner / Tech Lead / Security Officer（或 Compliance 代表）/ Data Steward 候選人 / Finance Stakeholder（若涉 RAPO 落地）
**輸出**：本議程空格填滿 + 指派 action owners + 定下 milestone date

**背景文件**：
- Doc 08（IPA Platform Recommendations）— 9-month roadmap 原案
- Doc 09（IPA Main Delta）— Phase 45/46/47 校正後 6-month 版本
- Doc 10（Wiring Audit）— 3 個 CRITICAL wiring gap
- Doc 11（Agent Team Review）— 7 專家交叉審查 + 新發現 E-01 / HITL-01 / C-01 / C-02

---

## 議程規則

- 每題 **5-7 分鐘**討論 + 1 分鐘決策
- 若某題無法 close，**指派 owner + due date**，不拖延整體 workshop
- 決策記錄要 **explicit**（非「之後再諗」）
- Workshop 結束時整理 action items list

---

## Part A：組織定位（20 分鐘）

### Q1 — IPA 最終定位

**問題**：IPA 係 **(A) RAPO 深度落地專案** 還是 **(B) 通用 enterprise AI agent platform**？

**為何重要**：
- (A) → 6-Layer 架構應 RAPO-first、ontology schema 可 domain-specific、freight invoice vertical slice 直接當 Phase 1
- (B) → 架構應 domain-agnostic、vertical slice 應選 generic use case（例如「企業文件 Q&A + citation + audit trail」）先驗架構再 specialize

**背景 data**：
- Doc 05/08 深度綁定 RAPO（SAP、freight invoice、vendor master）
- CLAUDE.md Core Vision 講「enterprise AI agent teams」（通用）
- 兩者衝突未解決

**決策空間**：
- [ ] (A) RAPO 落地優先，後續延伸其他部門
- [ ] (B) 通用平台優先，RAPO 係 first customer
- [ ] (C) 雙軌：RAPO 作為 reference implementation，平台能力 extract 為 reusable SDK

**決策**：___________
**Owner**：___________
**Rationale**：___________

---

### Q2 — Data Steward 任命

**問題**：**Month 0** 由邊個擁有 L3 Ontology governance（schema veto power）？

**為何重要**（Drucker panel insight）：Cross-department entity alignment（Vendor / Contract 定義）係 **管治缺位**非技術問題。6-month roadmap 冇 steward，graph quality 會劣化。

**候選 owner**：
- [ ] CFO Office（若 (A) RAPO/finance-first）
- [ ] CIO Office
- [ ] Chief Data Officer / Data Governance team
- [ ] CTO / Tech Lead（不建議，工程師兼任會 bottleneck）
- [ ] Part-time external hire

**承諾規模**：___________（FTE 或 %time）
**決策**：___________
**Due date for appointment**：___________

---

### Q3 — Commercial Model

**問題**：IPA 最終係 **(A) internal-only** / **(B) SaaS** / **(C) multi-BU shared service**？

**為何重要**（Business Panel blind spot #3）：
- (A) → single-tenant schema，可 hardcode org-specific，audit 滿足 internal ITGC 即可
- (B) → multi-tenant isolation 係架構一級決策（row-level security / per-tenant vector / ...）
- (C) → 中間態，需 BU-level federation

**決策空間**：___________
**Owner**：___________

---

### Q4 — Slice 2 候選

**問題**：Freight invoice variance 之後，第二個 vertical slice 候選係？

**為何重要**（Meadows panel insight）：Month 2 schema review 必須 anticipate 後續 slice，否則 domain overfit → 第二 slice 要 refactor。

**候選**：
- [ ] Procurement contract compliance（延伸 freight 合約域）
- [ ] HR policy reasoning / onboarding
- [ ] IT Change Management（走 ITIL 深度）
- [ ] Expense approval / T&E audit
- [ ] 其他：___________

**決策**：___________（可留 Month 2 再決，但 Month 2 前必須 close）

---

## Part B：Compliance 範圍（15 分鐘）

### Q5 — SOX / EU AI Act / HIPAA / GDPR 適用性

**問題**：IPA 最終用途涉及以下邊幾個 regulatory regime？

- [ ] SOX（finance / 財務控制）— 影響 A-01 audit 為 compliance gate
- [ ] EU AI Act（high-risk AI / automatic decision over natural persons）— 影響 A-04 bitemporal + Art. 12 logging
- [ ] HIPAA（healthcare / PHI）— 影響 PII redactor dual-layer
- [ ] GDPR / PDPO（EU / HK 個資）— 影響 right to erasure + storage encryption
- [ ] 僅 internal ITGC（無外部 regulator）

**為何重要**（Security Panel insight）：決定 A-01 升級為 **compliance gate / legal exposure** vs 僅 **observability best practice**，影響 P0 投資深度 3-5 倍。

**決策**：___________
**Owner**：___________（建議 Security Officer / Legal）

---

### Q6 — PII 範圍定義

**問題**：IPA 會處理 / 記錄邊啲 PII？

- [ ] 員工 ID / email（低敏感）
- [ ] 供應商聯絡人（低敏感）
- [ ] 財務數字（商業機密）
- [ ] 個人健康資訊（PHI, HIPAA）
- [ ] 客戶個資（GDPR/PDPO）

**redactor 策略**：
- [ ] Runtime only（regex + Presidio 在 log entry 前）
- [ ] Storage only（pgcrypto column-level encryption）
- [ ] Dual-layer（runtime + storage，security panel 建議）

**決策**：___________

---

### Q7 — Audit Retention 要求

**問題**：Audit trail 需要保留幾耐？需要 WORM 嗎？

- [ ] 90 天（一般 operational）
- [ ] 1 年（internal compliance）
- [ ] 7 年 + WORM（SOX §802 / EU AI Act 要求）
- [ ] 永久 immutable（法律保全）

**決策**：___________

---

## Part C：Roadmap 與資源（20 分鐘）

### Q8 — Roadmap Compression 動機

**問題**：Delta 報告提出 6-month 壓縮版（vs 原 9-month），動機係？

- [ ] Budget constraint（deadline-driven）
- [ ] Competitive pressure（market window）
- [ ] Stakeholder commitment（已承諾 date）
- [ ] 純工程評估（Phase 45/46 確實節省 12-15 週）

**Taleb 警告**：若係 budget / commitment，6-month 冇 slack → fragile；建議保 9-month + parallel optionality（Phase 45/46 節省時間用作 2 候選 slice）。

**決策**：___________
- [ ] 採 9-month schedule（穩健）
- [ ] 採 6-month（快，但需接受 fragility）
- [ ] 採 milestone-based 而非 date-based（Collins + Taleb synthesis）

---

### Q9 — SAP Team RACI

**問題**：Month 1 engage SAP team 係 best-effort 還是 formal commitment？

**為何重要**：Doc 08 列為 organizational killer #2。SAP approval cycle 長，Month 1 engage 若只係「打招呼」，Month 4 L4-Q1 Variance 會卡。

**決策**：
- Accountable（一人簽名）：___________
- Responsible（實際做）：___________
- Consulted：___________
- Informed：___________

---

## Part D：技術基礎決策（15 分鐘）

### Q10 — Qdrant 生產模式

**問題**：生產 Qdrant 採邊個模式？

- [ ] Embedded local（`./qdrant_data`，現 RAGPipeline default）— 單進程 / 冇 HA / 多 worker file lock 衝突（後端 panel 警告）
- [ ] Server（`host:port`，現 Step 2 default）— docker-compose 已有
- [ ] Azure AI Search（Doc 08 baseline）— managed，但要 migrate
- [ ] Hybrid（test embedded / prod server）

**決策**：___________（直接影響 K-01 修復方向）

---

### Q11 — Graph Backend 選擇

**問題**：L3 Ontology 用邊個 graph backend？

- [ ] Neo4j（full-feature，Doc 06/08 推薦，但第 5 個 stateful service）
- [ ] Kuzu（embedded，無新 service，後端 panel 建議先 PoC，省 2-3 週 ops）
- [ ] Memgraph（Cypher 兼容 + 更快，early phase <10M nodes 適用）
- [ ] Azure Cosmos DB Gremlin（managed）

**決策**：
- [ ] 直接決定：___________
- [ ] Month 1 先做 Kuzu PoC，Month 2 基於 PoC result 決定是否升 Neo4j

---

### Q12 — Embedding 維度策略

**問題**：目前有 ada-002 (1536d) + 3-large (3072d) 三處漂移（原 K-02 + 新 E-01）。統一為？

- [ ] 全部切 3-large 3072d（全面升級，best recall，2x storage/latency）
- [ ] 全部切 3-large 1536d（Matryoshka 截斷，~95% recall，省一半 storage；效能 panel 建議）
- [ ] 全部切 ada-002 1536d（穩定，但舊 model）
- [ ] 其他：___________

**前置工作**：需做 1-2 天 recall@10 benchmark（50-query ground truth）才能決定。

**決策**：___________
**Benchmark owner**：___________

---

## Part E：Action Items 總結（10 分鐘）

填滿以下表格並指派：

| # | Question | 決策 | Owner | Due Date | Status |
|---|----------|------|-------|---------|--------|
| 1 | IPA 定位（A/B/C） | | | | |
| 2 | Data Steward | | | | |
| 3 | Commercial Model | | | | |
| 4 | Slice 2 候選 | | | | |
| 5 | Compliance 適用性 | | | | |
| 6 | PII 範圍 + redactor | | | | |
| 7 | Audit Retention | | | | |
| 8 | Roadmap 壓縮動機 | | | | |
| 9 | SAP Team RACI | | | | |
| 10 | Qdrant 模式 | | | | |
| 11 | Graph Backend | | | | |
| 12 | Embedding 維度 | | | | |

---

## Part F：P0 sprint 啟動前提

Workshop 必須 close 以下最少問題才啟動 P0 修復：

| P0 Task | 必答 Questions |
|---------|---------------|
| M-01 search_memory 修復 | 無（技術上獨立） |
| HITL-01 request_approval 修復 | 無（技術上獨立） |
| K-01 Knowledge wiring 統一 | Q10（Qdrant 模式）、Q12（embedding 策略） |
| A-01 Main chat audit emission | Q5（compliance 適用性）、Q7（retention） |

**建議**：M-01 + HITL-01 可 **即日啟動**，不需等 workshop（Doc 14 Sprint Plan 已就緒）。K-01 / A-01 等 workshop Q5/Q7/Q10/Q12 close。

---

## 附錄 — 相關文件快速 link

- Doc 08 — 9-month roadmap + Build vs Buy matrix
- Doc 09 — 6-month 壓縮版 Delta
- Doc 10 — Wiring Audit（K-01/M-01/A-01）
- Doc 11 — 7-Agent Panel Review（含 E-01/HITL-01/C-01/C-02 新發現）
- Doc 14 — M-01 + HITL-01 Sprint Plan（即啟 ready）

---

**版本**

| Version | Date | Author |
|---------|------|--------|
| 1.0 | 2026-04-20 | Claude + Chris（待 workshop 執行後填答案）|
