# 13a - Positioning Workshop Stakeholder Pre-Read Handout

**分發對象**：Workshop 出席者（Product Owner / Tech Lead / Security Officer / Data Steward 候選 / Finance Stakeholder）
**閱讀時間**：15-20 分鐘
**Workshop 議程**：見 Doc 13

---

## 一、我們在哪裡（2 分鐘）

**IPA Platform**（Intelligent Process Automation）係企業級 AI agent orchestration 平台，Phase 44 完成（152+ sprints），已 deliver：
- 3-tier intent routing（pattern / semantic / LLM）
- 3-route dispatch（direct_answer / subagent / team）
- Agent Expert Registry（YAML-based，6 IT experts）
- 完整 HITL workflow + Teams notification
- mem0 三層記憶系統
- 基礎 hybrid RAG（vector + BM25 + rerank）

---

## 二、研究背景（3 分鐘）

過去 2 週內部 research team 產出 10+ 份文件（Doc 01-12），聚焦「**企業 knowledge base / memory / audit system**」升級，發現：

### ✅ 好消息

- Phase 45/46 已合併 → 比研究文件預期省 **12-15 週**
- 大部分架構決策方向正確（Graphiti + Cohere Rerank + vertical slice）

### ⚠️ 不好的消息 — 發現 ~36 個 wiring gap

| 嚴重度 | 數量 | 代表問題 |
|-------|------|---------|
| 🔴 CRITICAL / HIGH | **15** | Knowledge RAG **80% 使用者 query 搜空**；Memory tool 永久 broken；Main chat **零 audit**；3 個 dispatch tool 假裝工作 |
| 🟡 MEDIUM / 🟢 LOW | ~21 | Config drift、命名衝突、state serialization 缺失 |

---

## 三、為何需要 Workshop（2 分鐘）

**Tech team 搵到問題，但修復方案有 12 個 strategic questions 需 stakeholder 答**：
- 有些影響 scope（例如 IPA 係 RAPO 落地定通用平台？）
- 有些影響合規 gate（SOX？EU AI Act 適用？）
- 有些影響架構（Graphiti 用 Neo4j 定 Kuzu？Qdrant server 定 local？）

**若不開 Workshop 就啟動 P0 修復**：可能 Week 2 返工，延誤 2-4 週

---

## 四、你需要準備嘅背景（10 分鐘）

### 4.1 必讀（~5 分鐘）

- **Doc 11 Executive Summary 第 0.1 節「Panel 最關鍵共識」**
- **Doc 11 第 4.2 節 P0 優先序**（知道技術團隊建議做咩）
- **Doc 13 12 個 questions**（本議程）

### 4.2 選讀（depending on role，~5 分鐘）

| 角色 | 建議讀 |
|------|-------|
| Product Owner | Doc 08 Executive Summary + Slice 1 建議 |
| Tech Lead | Doc 10 + Doc 12 前兩章（Knowledge / Memory wiring audit）|
| Security Officer | Doc 11 第 2.3 節「資安工程師 review」 — 含 SOX §404 / EU AI Act 分析 |
| Data Steward 候選 | Doc 06 Ontology 前三章 + Doc 08 第 七章「組織風險」|
| Finance Stakeholder | Doc 08 第 六章「Phase 1 Vertical Slice 建議」— Freight Invoice Variance |

---

## 五、Workshop 嘅 12 個 Questions 預覽（2 分鐘）

### Part A — 組織定位
1. **IPA 定位**：RAPO 深度落地 / 通用 enterprise platform / 雙軌？
2. **Data Steward**：Month 0 由邊個任命？
3. **Commercial Model**：internal-only / SaaS / BU-shared？
4. **Slice 2 候選**：freight invoice 之後係邊個？

### Part B — Compliance 範圍
5. **SOX / EU AI Act / HIPAA / GDPR 適用性**
6. **PII 範圍** + redactor 策略
7. **Audit retention**（SOX §802 7-year + WORM？）

### Part C — Roadmap 與資源
8. **6-month vs 9-month**：動機？
9. **SAP team RACI**

### Part D — 技術基礎
10. **Qdrant 生產模式**：server / local / Azure AI Search
11. **Graph Backend**：Neo4j / Kuzu / Memgraph
12. **Embedding 維度**：3-large 3072 / Matryoshka 1536 / ada-002

---

## 六、你會被期待做嘅事情（2 分鐘）

在 Workshop 中：

✅ **做**：
- 基於你嘅 domain expertise 提供決策
- 若未能立即決策，指派 owner + due date
- Push back 技術團隊建議（若 business 角度不同）

❌ **不做**：
- 唔好答「之後再諗」（會延誤 2-4 週）
- 唔好迴避 Q5（合規適用性）— 無論答案係咩都要 close
- 唔好指派「整個團隊討論」作為 owner（要 single accountable）

---

## 七、Workshop 之後

我們會：
1. 填滿 Doc 13 Part E action items 表
2. **Sprint Wiring Fix 001**（M-01 + HITL-01）即啟動（唔等 Workshop，無依賴）
3. **Sprint Wiring Fix 002**（基於 Q10/Q12）啟動
4. **Sprint Wiring Fix 003**（基於 Q5/Q7）啟動
5. 2-3 週內 IPA 從「wiring 斷裂」狀態恢復

---

## 八、常見問題

**Q**：為何要花時間開 workshop？直接修代碼不行？
**A**：技術層面可修，但如果 IPA 最終係 SOX-regulated finance 用途，修復方案要強度 5 倍（bitemporal + WORM + PII dual-layer）。不 align 就做錯方向。

**Q**：Workshop 要準備咩材料？
**A**：本 handout 已足夠。深度讀 Doc 11 executive summary + Doc 13 questions 可，<30 分鐘總時間。

**Q**：我唔係技術人，可以跳過 Part D（技術基礎）嗎？
**A**：可以，但建議 Tech Lead 在場時聽——技術決策有 cost/compliance implication，非純技術。

**Q**：Q5（compliance 適用性）我唔確定點答，點算？
**A**：Workshop 中指派 Security Officer / Legal 為 owner，給 1 週 deadline 返答案；**唔好拖**，因為此 question 決定 A-01 Sprint 003 能否啟動。

---

## 九、Pre-Workshop Feedback

若你閱讀本 handout 後有問題或希望加 agenda item，請在 workshop 前 24 小時 feedback：
- Owner：___________
- Channel：___________

---

**文件位置**：`docs/09-git-worktree-working-folder/knowledge-base-enterprise/13a-workshop-stakeholder-handout.md`
**配對議程**：Doc 13
**版本**：1.0 / 2026-04-20
