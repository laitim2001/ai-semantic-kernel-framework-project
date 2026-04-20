# 11 - Agent Team Review（7 位專家並行審查）

**目的**：7 位不同專業角色嘅 agent 並行 review Doc 01-10（research series + delta + wiring audit），交叉驗證內容正確性、發現盲點、校正方向。

**執行日期**：2026-04-20
**執行方式**：7 agents 並行（asyncio-style），每位讀取指定 docs + 代碼，產出 4 段結構化意見
**總 Token 消耗**：~570k（7 agents × 平均 81k）
**總運行時間**：~85 秒（最長 code-reviewer 84 秒）

---

## 零、Panel 組成與方法論

| # | 角色 | Agent Type | 讀取文件 | 審查焦點 |
|---|------|-----------|---------|---------|
| 1 | 系統架構師 | `system-architect` | Doc 05, 09 | 6-Layer 分層 soundness、L3 coupling、L2 decomposition、L5 verifier placement |
| 2 | 後端架構師 | `backend-architect` | Doc 06, 07, 10 | Graphiti/Neo4j/Qdrant 選型、data migration 風險、API 契約 |
| 3 | 資安工程師 | `security-engineer` | Doc 08 (L6/L4-Q4), Doc 10 (Audit) | SOX / HIPAA / EU AI Act 合規 exposure |
| 4 | 效能工程師 | `performance-engineer` | Doc 03, 08, 09, 10 | Latency budget、embedding 維度成本、Verifier gating |
| 5 | 程式碼審查師 | `code-reviewer` | Doc 10 + 5 份實際代碼 | Wiring gap 代碼驗證、修復方案 correctness |
| 6 | 根因分析師 | `root-cause-analyst` | Doc 10 + 交叉 grep | 審計方法論評估、遺漏 gap 發現 |
| 7 | 商業決策顧問 | `business-panel-experts`（6 位 thought leaders: Porter / Christensen / Drucker / Taleb / Meadows / Collins）| Doc 01, 04, 08 | 戰略定位、組織風險、build vs buy |

**輸出規範**：每位繁體中文 <500 字，結構化為 ✅ 強項 / ⚠️ 擔憂 / 🔴 風險 / 🟢 建議

---

## 一、Executive Summary

### 🎯 Panel 最關鍵共識

1. **Vertical slice 策略正確**（Porter + Christensen + Collins + 系統架構師）：freight invoice 唔削弱通用性，反而係 disruption 正確 entry point
2. **L3 Ontology 係 highest leverage point**（Meadows + Porter + Drucker + 系統架構師）：技術槓桿 + 管治前置 + 護城河三重身份
3. **Wiring audit 發現屬實且被低估**：code-reviewer 逐條驗證 K-01/K-02/K-03/M-01/A-01 全部 True；資安工程師將 A-01 升級為 **SOX §404 material weakness + EU AI Act Art. 12 violation**（legal exposure，非技術債）

### 🆕 Panel + Audit Round 2 發現的新 gap（共 23 個，10 個 HIGH+）

**Panel 發現（首輪併入）**：

| ID | 發現者 | 描述 | 嚴重度 |
|----|-------|------|-------|
| **E-01** | 根因分析師 | **Embedding model 三處漂移**：Step 2 用 ada-002、SemanticRouter fallback 用 3-large、embedder.py 用 3-large — 唔只 K-01 描述的 Step 2 vs Ingest | 🔴 CRITICAL |
| **HITL-01** | 程式碼審查師 | `handle_request_approval`（dispatch_handlers.py:379-405）只 `logger.info` 冇實際 call controller，返回 hardcoded "pending" — 另一個 silent broken tool | 🔴 HIGH |
| **C-01** | 根因分析師 | PipelineContext `memory_metadata` / `knowledge_metadata` write-only，無 downstream step 讀取 | 🟡 MEDIUM |
| **C-02** | 根因分析師 | `to_checkpoint_state()` 漏 serialize `dispatch_result` / `hitl_approval_id` / `fast_path_applied`，resume 後 state lost | 🟡 MEDIUM |

**Audit Round 2 發現（Doc 12，19 個新 gap — 6 個 HIGH）**：

| ID | 類別 | 描述 | 嚴重度 |
|----|------|------|-------|
| **TH-01** | 🚨 Fake dispatcher | `handle_dispatch_workflow` Adapter 建了但永未 `.execute()` | 🔴 HIGH |
| **TH-02** | 🚨 Fake dispatcher | `handle_dispatch_swarm` 只 notify lifecycle，worker 冇真 dispatch | 🔴 HIGH |
| **TH-03** | 🚨 Fake dispatcher | `handle_dispatch_to_claude` Coordinator 建了但冇 call coordinate_agents | 🔴 HIGH |
| **TH-04** | Dual engine | Pipeline Step 4 用 `orchestration.risk_assessor`；Agent tool 用 `hybrid.risk.engine` — **兩套 policy 不同步**| 🔴 HIGH |
| **ER-01** | Registry binding | DOMAIN_TOOLS 漏 dispatch_workflow/swarm/claude — YAML expert 拎唔到 | 🔴 HIGH |
| **CTX-01** | Serialization | to_checkpoint_state 漏 **5** 欄位（擴展 C-02）— HITL resume / dialog continue / metrics 全部壞 | 🔴 HIGH |
| P-01/P-03/P-05 | Config drift | AZURE deployment name / SemanticRouter threshold / intent whitelist 硬編碼 | 🟡 MEDIUM × 3 |
| ER-02/ER-03 | Registry | Dead binding + naming 誤導 | 🟡 MEDIUM × 2 |
| IR-01 | Contract | LLMClassifier confidence 三處 default 不一致 | 🟡 MEDIUM |
| CTX-02 | Serialization | from_checkpoint_state 無 restore total_start_time | 🟡 MEDIUM |
| P-02/P-04/P-06/P-07 | Config / Silent | Magic number / dead write / silent fallback / silent swallow | 🟢 LOW × 4 |
| TH-05/CTX-03 | Pattern / SSE | ImportError guard 不一致 / SSE summary 漏欄位 | 🟢 LOW × 2 |

### 🆕 新發現的系統性 Pattern（比原 PoC→Production 更嚴重）

**Pattern：「Fake Dispatcher」**（Round 2 新發現，TH-01/02/03 為代表）

比 M-01（silent stub: import 失敗）**更隱蔽**：
- Module import 成功 ✅
- Class instantiate 成功 ✅
- **但 business method 故意不 call，只 fabricate "success" envelope** ❌

**危險性**：
1. IDE 靜態檢查 pass
2. Connection test pass
3. LLM agent 見到 "Task acknowledged" 信以為真繼續推理 → 基於假 grounding cascading
4. **Only production E2E test 先會暴露**

**建議 CI 防線**（加入 P1 CI-03）：AST check 「每 dispatch_* handler 必須 call 至少一個 async business method」

### 🔧 Panel 校正原審計的修復方案

1. **M-01 修復 API 錯誤**（code-reviewer）：Doc 10 建議 `manager.search_memory(...)`，但實際 UnifiedMemoryManager API 係 `manager.search(query, user_id, ...)` 且 `user_id` 必填
2. **K-01 修復方向需明確**（code-reviewer）：應推薦「Step 2 delegate 至 RAGPipeline」（根治），而非「對齊 config」（治標）
3. **A-01 latency 估算偏低**（後端 + 效能）：每 step audit emission 實際 15-30ms（PG sync + fsync + network），非 5-10ms。必須用 async outbox + RabbitMQ，否則每 chat +160ms
4. **Verifier Agent cost unsustainable**（效能）：每 query Opus 驗證 = $0.068 × query volume = **年化 $50-200k**，必須改為 risk-gated（只高風險 / 低 confidence 跑）

### ⚖️ Panel 最重要 Productive Tension

| 張力 | A 方 | B 方 | Synthesis |
|------|------|------|----------|
| **Roadmap compression** | Taleb：保 9-month 要 slack，避 fragile | Collins：6-month 壓縮測 Hedgehog 紀律 | **Keep 9-month**，但用 Phase 45/46 節省時間做 **parallel optionality**（2 候選 slice）而非 pull-in deadline |
| **Scope expansion** | Porter：Compliance 係護城河延伸 | Christensen：Compliance 有 incumbent（Thomson Reuters）勿正面衝 | **Q2 Compliance 限制於 freight invoice 同 vendor 合約範圍**，不做 horizontal expansion |
| **K-01 修復深度** | 後端架構師：分兩步，先對齊 config 保 rollback | 程式碼審查師：直接 delegate 至 RAGPipeline，根治 | **Day 1 做 delegate（根治），Day 2-3 做 collection migration** |

---

## 二、個別 Review 精華（壓縮版）

### 1️⃣ 系統架構師

**✅ 強項**
- 6-Layer 分層符合 SOLID single responsibility
- 與 main 現況 alignment 良好，壓縮 roadmap 基於實證非樂觀
- Vertical slice 策略務實，避免 11-component 平推陷阱

**⚠️ 擔憂**
- L3 作為 L4 hard dependency 形成 critical path bottleneck
- L2 多 sub-question parallel dispatch 與現有 3-route dispatch 的 semantic 衝突
- L5 Verifier placement 過 downstream，錯誤已在 cross-specialist 擴散

**🔴 風險**
- CRITICAL — L3 schema cross-department alignment 係 business risk；若 committee paralysis 整個 6-month roadmap collapse
- CRITICAL — Phase 46 YAML Expert 框架能否承載 Finance/Compliance 複雜 system_prompt 未 PoC 驗證

**🟢 建議**
1. L3 引入 thin ontology（Month 1 只定 3 entity）+ L4-Q1 hardcode canonical ID fallback
2. L2 新增 `decomposition_planner` 作 team executor pre-hook，不改 step6
3. L5 Verifier two-stage：per-specialist（fast）+ cross-specialist（Opus）
4. Month 0 加 1 週 Expert Registry Fit PoC（用 variance_analyzer.yaml 最小原型）
5. L6 Bitemporal audit 前置到 Month 1 併行 L3

---

### 2️⃣ 後端架構師

**✅ 強項**
- Graphiti 三合一（Ontology + Memory + Bitemporal）選型站得住腳，Apache 2.0 + MCP server 天然 fit
- Wiring audit 方法論嚴謹，三個 CRITICAL gap 都有 file:line 證據
- 5-stage pipeline + 4 類 source 分類清晰

**⚠️ 擔憂**
- **Qdrant local path 模式係生產事故源頭**（embedded 鎖單進程 / 冇 HA / 多 worker file lock 衝突）
- ada-002 → 3-large re-embed 成本：$0.13/1M × chunk 總量 + Qdrant re-index 幾小時
- Graphiti + Neo4j 新增第 5 個 stateful service；**Kuzu / Memgraph 值得對比**，尤其 early phase <10M nodes

**🔴 風險**
- K-01 data migration 破壞性：若 `ipa_knowledge` 已人手 seed，切換會靜默回歸
- A-01 audit sync write：每 chat +30-90ms p50，streaming TTFB 被感知

**🟢 建議**
1. **K-01 分兩步**：Step A 先 delegate 保 rollback，Step B 再 migration
2. **Qdrant 生產強制 server 模式**：`.env` 新增 `QDRANT_URL`，local path 限 unit test
3. **M-01 freeze API 契約**：加 `tests/integration/test_memory_tool_contract.py` 鎖簽名
4. **A-01 走 async outbox pattern**：`audit_queue.put_nowait`，p95 overhead <2ms
5. **Graphiti backend 先用 Kuzu PoC，Neo4j Phase 2**：省 2-3 週 ops setup

---

### 3️⃣ 資安工程師

**✅ 強項**
- Bitemporal audit + immutable rules + PostgreSQL 持久化方向符合 SOX §802（7-year retention）+ EU AI Act Art. 12（high-risk AI automatic logging）
- OPA/Rego 選型合理，decision log 可直接交 auditor
- `approval_handler` 已有 emission pattern 可複製

**⚠️ 擔憂**
- Doc 08 把 L6 Bitemporal 放 Month 1-2 但 A-01 未入 P0 roadmap — 先起保險箱再裝監控
- PII redactor 只一句 bullet，無講 runtime vs storage（GDPR Art. 17 決定性問題）
- Build-vs-buy matrix 將 Audit 標 Build PostgreSQL，但**無提 WORM / append-only**（SOX 要求 tamper-resistance）

**🔴 風險（legal exposure）**
- **R1 — A-01 主鏈零 audit = SOX §404 ITGC material weakness + EU AI Act Art. 12 non-compliance**：若 IPA 投入 finance 用途，auditor 會認定「unlogged automated decision over financial controls」，外部 audit 意見可能 qualified；EU AI Act 行政罰最高 €15M 或 3% global turnover。**此為 legal exposure 非技術債**
- **R2 — `AuditLogger` 命名衝突 = integrity risk**：一次錯誤 IDE auto-import 令生產 audit 靜默導向 orphan logger，SOX §302 management assertion 直接推翻。屬 CWE-778 + CWE-222

**🟢 建議**
1. **A-01 升級為 compliance gate**（Month 2 完成），Phase 1 freight invoice GA 應 block。每筆含 `trace_id, actor, obo_token_sub, action, resource, input_hash, output_hash, policy_decision`
2. **立即 rename orphan class**：`_LegacyOrchestrationAuditLogger`，`__all__` 白名單 + CI lint 禁止其他路徑定義 `AuditLogger`
3. **PII redactor dual-layer**：runtime regex + Presidio；storage pgcrypto column-level encryption + 獨立 KMS
4. **Audit WORM 化**：`REVOKE DELETE, UPDATE FROM PUBLIC` + pg trigger + 每日 hash chain 到 Azure Immutable Blob（legal hold 7 年）
5. **M-01 升級為 integrity issue**（非 availability）：agent 講「查過 memory 冇嘢」實際從未查過，構成誤導 output（EU AI Act Art. 13 transparency violation）；修復需 health check + startup import validation

---

### 4️⃣ 效能工程師

**✅ 強項**
- Cohere Rerank 3 drop-in 低風險，rerank@10 約 80-150ms（Cohere US p50）
- 6-month 壓縮有實質依據，Month 1 quick win ROI 最高
- 先修 wiring 再投資 rerank/GraphRAG 嘅優先序判斷正確

**⚠️ 擔憂（含數字）**
- **+15-30% precision 過度樂觀**：enterprise corpus domain shift 下實測 +5-15% NDCG@10；建議預期 +10% baseline
- **ada-002 → 3-large latency / cost**：Qdrant HNSW 1.5-1.8x latency（每 query +10-20ms @ 100k vectors），storage 2x，每月 +$500-2000
- **E2E latency budget 未公開**：估算 p50 5-10s, p95 15-25s；若 Verifier 每 query 跑，p95 破 <10s SLA

**🔴 風險**
- **Verifier Agent Opus 每 query 不可持續**：$15/M input + $75/M output × ~2k+500 = $0.068/query × volume = **年化 $50-200k**，+3-10s latency
- **Audit A-01 5-10ms/step 偏低**：PG sync write p99 15-30ms × 8 events = **累計 160ms**，非 40-80ms

**🟢 建議**
1. **Rerank 實測**：建 50-query RAPO ground truth，對比 ada+simple vs 3-large+Cohere；回報 NDCG@5/@10 + MRR（2 天、$30）
2. **Verifier gating**：`confidence<0.7 OR risk=medium+` 才跑，shadow mode 2 週；目標觸發率 <30%
3. **Latency budget enforcement**：每 step `asyncio.timeout()`（Step2 500ms, rerank 300ms, Verifier 5s）；OTel histogram 按 step 分 p50/p95/p99
4. **Audit async pipeline**：`asyncio.create_task` + 10-event batch flush，`audit_emission_lag_ms` Prometheus metric
5. **Embedding Matryoshka**：3-large 可設 `dimensions=1536` 降維，保 ~95% recall；若 recall@10 差 <3% 直接用 1536

---

### 5️⃣ 程式碼審查師

**✅ 強項**
- 審計報告代碼準確性高：K-01/K-02/K-03/M-01 行號、collection 名、import path、嚴重度逐條驗證屬實
- Step 2 graceful degradation 設計清晰（但同時令 K-01 silent failure 不被察覺）
- RAGPipeline API 已預備俾 tool handler delegate

**⚠️ 擔憂**
- **M-01 修復 API 錯誤**：Doc 10 寫 `manager.search_memory(...)`，實際 `UnifiedMemoryManager` 方法係 `.search(query, user_id, ...)` 且 `user_id` 必填
- **K-01 修復方向未表達偏好**：應明確推薦「delegate 至 RAGPipeline」（根治）而非「對齊 config」（治標）
- **HITLController handler 亦係 half-broken**（dispatch_handlers.py:379-405）：只 `logger.info` 冇實際 call `controller.request_approval()`，返回 hardcoded "pending"。**審計 miss 咗呢個**

**🔴 風險**
- **search_memory 永久 silent failure 影響 agent decision quality**：LLM 見到 `{"results": []}` 當成「無相關記憶」而繼續推理，比 crash 更危險
- **K-01 若只對齊 Step 2 去 embedded local**：production Qdrant server 徹底無人用；反之若 Ingest API 改 server mode，歷史資料 orphan

**🟢 建議**
1. **M-01 最小 diff**（針對 dispatch_handlers.py:355-377）：
```python
from src.integrations.memory.unified_memory import UnifiedMemoryManager
manager = UnifiedMemoryManager()
await manager.initialize()
if user_id is None:
    return {"results": [], "message": "user_id required"}
results = await manager.search(query=query, user_id=user_id, limit=limit)
return {"results": [r.to_dict() for r in results], "count": len(results)}
```
2. **K-01 推薦方向**：`KnowledgeStep._execute()` delegate 俾 `RAGPipeline.handle_search_knowledge(query=context.task, ...)`，只保留 format_results
3. **K-05 singleton pattern**：class-level `self._rag_pipeline = None` lazy init，省 +100-200ms/call
4. **新增 A-06 條目**：修復 `handle_request_approval` 實際 call controller
5. **統一 error envelope**：所有 handler 加 `metadata.tool_broken=True` 俾下游 observability

**Audit 報告準確性驗證**
| ID | 結論 |
|----|------|
| K-01 | ✅ True |
| K-02 | ✅ True |
| K-03 | ✅ True |
| M-01 | ⚠️ True (partial fix) — 方法名錯 + 漏 user_id 必填處理 |
| A-01 | ✅ True |

---

### 6️⃣ 根因分析師

**✅ 強項**
- 原審計用三層方法（runtime 資料流反向追溯 + 配置比對 + import 存在性驗證）證據鏈紮實
- 三個 CRITICAL gap 確認係 root cause 非表面症狀
- Caveat §7 明確 disclaim scope，顯示 intellectual honesty

**⚠️ 盲點（審計未覆蓋）**
1. 只 grep 直接字面 import，未驗 *transitively* 觸發的 import
2. 未掃 Step 3/4/5/6/7/8（只聚焦 Knowledge/Memory/Audit）
3. 未做 embedding model 跨 step 一致性 audit
4. PipelineContext fields write/read 對稱性未驗證
5. Intent Router 三層內部一致性未比對

**🔴 原報告遺漏的 gap**

- 🔴 **E-01（新 CRITICAL）Embedding model 三處漂移**：
  - `step2_knowledge.py:25` 用 `text-embedding-ada-002`（1536d）
  - `step3_intent.py:361` SemanticRouter fallback 用 `text-embedding-3-large`
  - `knowledge/embedder.py:14` 亦用 `3-large`
  - **同一 pipeline 三處不一致**，若 semantic router 用 ada-002 seed 卻用 3-large query → dimension mismatch crash 或 silent zero-hit

- 🟡 **C-01（MEDIUM）PipelineContext orphan state**：`memory_metadata` / `knowledge_metadata` 寫入後無 downstream 讀取（write-only field）
- 🟡 **C-02（MEDIUM）`to_checkpoint_state()` 漏欄位**：`dispatch_result` / `hitl_approval_id` / `fast_path_applied` 不在 serialization，resume 後 state lost
- 🟡 **O-01（LOW-MEDIUM）`backend/src/integrations/poc/orchestrator_tools.py` 仍 import production modules**：CLAUDE.md 未列 `poc/` 為 production，屬 PoC→Production migration 殘留

**Gap 模式總結**：7 個 gap（3 原 + 4 新）**100% 根源都係 PoC→Production migration 時未做 single-source-of-truth 統一** — config 散落各 step hardcode、PoC 代碼未清理、checkpoint serialization 未隨 context.py 演進

**🟢 建議**
1. **CI import-existence check**：pytest hook 掃所有 `from src.*` 做 `importlib.util.find_spec`
2. **Config centralization test**：所有 embedding / collection / qdrant mode 由 `core/config.py` 讀，禁止 module-level `DEFAULT_*`
3. **Context field usage linter**：AST 掃每個 field read/write site
4. **第二輪 audit** 擴展至 Step 3-8 + Intent Router 三層

---

### 7️⃣ 商業決策顧問（6 位 thought leader discussion mode）

**📊 Porter（競爭戰略）**：IPA 護城河係「domain-specific ontology + bitemporal audit」形成嘅 switching cost，唔係通用平台。Vertical slice 係 reference implementation，後續 2-3 slice marginal cost 急降 = **scale economy at depth**。Build Graphiti / Buy Cohere Rerank 合理。

**📚 Christensen（JTBD）**：正確問題唔係「替代邊個」，係「Finance controller hire IPA 做 `reduce decision latency on invoice approval from 3 days to 3 minutes`」。呢個 job 目前由 SAP + Excel + 人肉 email 服務，屬 **low-end disruption**（non-consumption entry）。但警告勿 prematurely 擴展到 Compliance Q2（Thomson Reuters/iManage 強勢）。

**🧭 Drucker（管理）**：「Cross-department entity alignment」係 **管治缺位**非技術問題。Data Steward role 係 **執行前置條件**，應 **Month 0 由 CFO Office 任命並賦予 schema veto power**，非 Month 6 配角。

**🛡️ Taleb（Antifragility）**：Phase 45/46 節省 12-15 週係 past performance 不保證未來。**6-month roadmap 冇 slack 係 fragile**：SAP sandbox approval 拖 4 週 → 連鎖斷裂。建議保 9-month schedule + **front-load optionality**（Month 1 同步啟 2 個 candidate slice，邊個 unblock 快跑邊個）。

**🕸️ Meadows（Systems）**：**L3 Ontology 係 highest leverage point**（影響 L2 retrieval / L4 specialist / L6 audit granularity）。L5 Verifier 係低槓桿 symptom treatment。Unintended consequence：Vertical slice 追求 100% 會產生 reinforcing loop（domain overfit → 第二 slice 要 refactor）；Balancing：Month 2 schema review 要 anticipate 後續 slice。

**📖 Collins（執行）**：9-month 失敗通常係違反 Hedgehog（同時做 Q1/Q2/Q3）。Doc 08 「1 slice 100%」正確。但 **Q3 Analogy 60-70% 唔應與 Q2 Compliance production 並列 Month 9** — 紀律層次唔同。建議 Month 9 改為「Q2 production + Q3 internal alpha」。

**🧩 Cross-Framework Synthesis**

**🤝 Convergent insights**
- Vertical slice 策略正確（3 方認同）
- L3 Ontology 係 critical path（技術 + 管治 + 護城河三重）
- Build Graphiti / Buy Rerank 合理

**⚖️ Productive tensions**
- **Taleb ⚡ Collins on roadmap**：要 slack vs 要 discipline → Keep 9-month + parallel optionality
- **Christensen ⚡ Porter on Q2 scope**：incumbent 警告 vs 護城河延伸 → Q2 限 freight invoice 同 vendor 合約範圍

**⚠️ Blind spots（research docs 共同盲點）**
1. Data Steward 當 risk 而非 Day 0 prerequisite
2. Evaluation harness 只講 retrieval/generation quality，冇 business metric（decision latency、controller override rate）
3. 10 份 docs 冇討論 IPA commercial model（internal / SaaS）影響 ontology 設計
4. Phase 45/46 reusability to L4 specialist 未有 evidence

**🤔 Strategic questions（stakeholder 必須答）**
1. **Data Steward accountability**：CFO / CIO / CDO 邊個擁有 L3 Ontology governance？
2. **Slice 2 候選**：freight invoice 之後係 procurement compliance 定 HR policy？影響 schema generalization
3. **6-month vs 9-month 決策標準**：budget / competitive pressure / commitment？若係後者，用 milestone-based commitment 非 date-based
4. **SAP team RACI**：Month 1 engage 邊個簽？
5. **L4-Q3 Analogy 60-70% 商業接受度**：邊個 stakeholder 簽 HITL fallback 入 production？

---

## 三、Cross-Panel 綜合洞察

### 3.1 Convergent Findings（3+ panel 同意）

| 共識 | 支持 panel |
|------|-----------|
| L3 Ontology 係 critical path / highest leverage | 系統架構、後端、Porter、Meadows、Drucker |
| K-01/M-01/A-01 wiring gap 屬實且必須 P0 修復 | code-reviewer、根因、後端、資安 |
| Vertical slice 策略正確 | 系統架構、Porter、Christensen、Collins |
| 原審計低估問題嚴重性（尤其 A-01） | 資安（legal exposure）、code-reviewer（HITL-01 亦 broken）、根因（E-01 embedding 三漂） |
| Verifier Agent 不能 per-query 跑 | 系統架構（two-stage）、效能（gating） |
| 6-month roadmap 需 slack | Taleb、後端（migration 風險）、系統架構（L3 critical path） |

### 3.2 Productive Tensions（Panel 間有分歧，促成更好 synthesis）

**Tension 1：Roadmap Compression**
- **Collins**：6-month 壓縮測試 Hedgehog 紀律
- **Taleb**：Keep 9-month 保 slack
- **後端架構師**：Migration 分兩步需時間
- **Synthesis**：Keep 9-month，Phase 45/46 節省時間用作 **parallel optionality**（2 候選 slice）而非 pull-in deadline

**Tension 2：Compliance Q2 Scope**
- **Porter**：護城河延伸，值得做
- **Christensen**：Thomson Reuters/iManage 強勢，勿正面衝
- **Synthesis**：Q2 限於「freight invoice 同 vendor 合約」範圍，不 horizontal expansion

**Tension 3：K-01 修復深度**
- **後端架構師**：分兩步，先對齊 config 保 rollback
- **code-reviewer**：直接 delegate 至 RAGPipeline 根治
- **Synthesis**：Day 1 delegate（根治），Day 2-3 migration（保 rollback）

**Tension 4：Audit Emission Performance**
- **資安**：A-01 必須 Month 2 完成（compliance gate）
- **效能**：Sync write latency 160ms 不可接受
- **後端**：Async outbox pattern
- **Synthesis**：Month 2 deliver A-01 但 **必須 async outbox**，否則 rollback 至 feature flag

### 3.3 原 Research Docs 共同盲點（Panel 發現）

| 盲點 | 發現者 | 建議補充 |
|------|-------|---------|
| Data Steward 應 Day 0 任命，非 Month 6 補 | Drucker | 加入 Month 0 milestone |
| Evaluation 只講 retrieval quality，缺 business metric | Christensen、效能 | 加「decision latency reduction、override rate」 |
| 無討論 IPA commercial model（internal/SaaS） | Panel | 影響 multi-tenant ontology 設計 |
| Phase 45/46 reusability to L4 未驗證 | Panel、系統架構 | Month 0 加 variance_analyzer.yaml PoC |
| PII redactor 只一句 bullet | 資安 | 需 runtime + storage dual-layer 章節 |
| WORM audit storage 未提 | 資安 | 需 pg trigger + Immutable Blob chain |
| Qdrant 生產模式未規範 | 後端 | 強制 server 模式，local 限 test |
| Embedding 維度 Matryoshka 優化未探索 | 效能 | 3-large dimensions=1536 可測 |

---

## 四、更新後 Gap & 修復優先矩陣

### 4.1 完整 Gap 清單（原審計 + Panel 新發現）

| ID | 類別 | 描述 | 嚴重度 | 發現者 | 修復估時 |
|----|------|------|-------|-------|---------|
| K-01 | Wiring | Step 2 與 Ingest API 倉 / model 不一致 | 🔴 CRITICAL | 原審計 | 2-3 天（分兩步）|
| K-02 | Wiring | ada-002 vs 3-large 維度不兼容 | 🔴 CRITICAL | 原審計 | 合併 K-01 |
| K-03 | Wiring | Step 2 bypass RAGPipeline 重複實作 | 🟡 MEDIUM | 原審計 | 合併 K-01 |
| K-04 | Wiring | Agent Skills 硬編碼 vs Qdrant 隔離 | 🟡 MEDIUM | 原審計 | 1-2 週 |
| K-05 | Perf | dispatch_handlers 每次 RAGPipeline() 重新 init | 🟡 MEDIUM | 原審計 + code-reviewer | 0.5 天 |
| K-06 | Perf | `_simple_rerank` 非 cross-encoder | 🟡 MEDIUM | 原審計 | 1 週（Cohere quick win） |
| M-01 | Wiring | `Mem0Service` 不存在，search_memory 永久 broken | 🔴 CRITICAL | 原審計 | 1 天（修正 API）| ✅ **Fixed 2026-04-20（FIX-001）** |
| M-02 | Docs | Step 1 docstring 錯誤（4-layer vs 3-layer） | 🟢 LOW | 原審計 | 10 分鐘 |
| A-01 | Compliance | Main chat flow 零 audit emission | 🔴 **HIGH→CRITICAL** | 原審計 + 資安升級 | 3-4 天（async outbox）|
| A-02 | Dead code | 281 LOC orphan AuditLogger | 🟡 MEDIUM | 原審計 | 0.5 天 |
| A-03 | Safety | AuditLogger 命名衝突（silent fail risk）| 🟡 MEDIUM | 原審計 + 資安升級 | 0.5 天 |
| A-04 | Compliance | 缺 bitemporal + immutable + PII + EU AI Act | 🔴 HIGH | 原審計 | 4-6 週 |
| A-05 | Verify | pipeline/persistence.py scope 未明 | 🟡 MEDIUM | 原審計 | 0.5 天 |
| **E-01** | **Wiring** | **Embedding model 三處漂移** | **🔴 CRITICAL** | **根因分析師（新）** | **1 天（合併 K-01 config centralization）**|
| **HITL-01** | **Wiring** | **handle_request_approval 只 log 冇 call controller** | **🔴 HIGH** | **code-reviewer（新）** | **1 天** | ✅ **Fixed 2026-04-20（FIX-002, Option X 合成物件）** |
| **C-01** | **State** | **PipelineContext metadata write-only** | **🟡 MEDIUM** | **根因分析師（新）** | **0.5 天** |
| **C-02** | **State** | **to_checkpoint_state 漏欄位** | **🟡 MEDIUM** | **根因分析師（新）** | **0.5 天** |
| **O-01** | **Orphan** | **poc/orchestrator_tools.py 屬 PoC→Prod 殘留** | **🟢 LOW** | **根因分析師（新）** | **0.5 天（分類或刪除）**|
| **CI-01** | **Meta** | **缺 import-existence CI check** | **🟡 MEDIUM** | **根因分析師** | **1 天** |
| **CI-02** | **Meta** | **缺 config centralization test** | **🟡 MEDIUM** | **根因分析師** | **1 天** |
| **WORM-01** | **Compliance** | **Audit 缺 WORM（SOX §802 required）** | **🔴 HIGH** | **資安** | **2 天（合併 A-04）**|
| **PII-01** | **Compliance** | **PII redactor 無 dual-layer 設計** | **🔴 HIGH** | **資安** | **1 週（合併 A-04）**|
| **TH-01** | **Fake dispatcher** | **handle_dispatch_workflow 永未 execute（WorkflowExecutorAdapter 建了但無 call）**| **🔴 HIGH** | **Round 2（新）** | **1 天** |
| **TH-02** | **Fake dispatcher** | **handle_dispatch_swarm 只 notify lifecycle 冇真實 dispatch** | **🔴 HIGH** | **Round 2（新）** | **1 天** |
| **TH-03** | **Fake dispatcher** | **handle_dispatch_to_claude 完全冇 call ClaudeCoordinator** | **🔴 HIGH** | **Round 2（新）** | **1 天** |
| **TH-04** | **Dual engine** | **Pipeline Step 4 用 orchestration.risk_assessor；Agent tool 用 hybrid.risk.engine — 兩套 policy 不同步** | **🔴 HIGH** | **Round 2（新）** | **1.5 天** |
| **TH-05** | **Pattern** | **create_task / update_task_status 冇 ImportError guard** | **🟢 LOW** | **Round 2（新）** | **0.2 天** |
| **ER-01** | **Registry binding** | **DOMAIN_TOOLS 漏 dispatch_workflow/swarm/claude — YAML expert 用 @domain 拎唔到** | **🔴 HIGH** | **Round 2（新）** | **0.5 天** |
| **ER-02** | **Dead binding** | **update_task_status 有 handler + registration 但無 domain exposure** | **🟡 MEDIUM** | **Round 2（新）** | **0.2 天** |
| **ER-03** | **Naming** | **ALL_KNOWN_TOOLS 誤導性命名（不包 dispatch_*）**| **🟡 MEDIUM** | **Round 2（新）** | **0.3 天** |
| **CTX-01** | **Serialization** | **to_checkpoint_state 漏 5 欄位（dispatch_result / hitl_approval_id / dialog_* / fast_path_applied / metadata）— 擴展 C-02** | **🔴 HIGH** | **Round 2（新，擴展 C-02）** | **0.8 天** |
| **CTX-02** | **Serialization** | **from_checkpoint_state 無 restore total_start_time → latency metrics corrupt** | **🟡 MEDIUM** | **Round 2（新）** | **0.2 天** |
| **CTX-03** | **SSE gap** | **to_sse_summary 漏 risk_level / intent_category** | **🟢 LOW** | **Round 2（新）** | **0.2 天** |
| **P-01** | **Config drift** | **AZURE deployment name 三處硬編碼（step3×2, step6×1）** | **🟡 MEDIUM** | **Round 2（新）** | **0.5 天** |
| **P-02** | **Config** | **COMPLETENESS_THRESHOLD magic number 寫死在函數內** | **🟢 LOW** | **Round 2（新）** | **0.3 天** |
| **P-03** | **Config drift** | **SemanticRouter threshold 0.50 vs 0.85 silent downgrade 風險** | **🟡 MEDIUM** | **Round 2（新）** | **0.5 天** |
| **P-04** | **Dead write** | **Step 4 custom_factors.memory_available / knowledge_available 從未被讀** | **🟢 LOW** | **Round 2（新）** | **0.2 天** |
| **P-05** | **Enum drift** | **Step 4/5 intent whitelist 硬編碼字面量（actionable_intents / non_actionable）**| **🟡 MEDIUM** | **Round 2（新）** | **0.3 天** |
| **P-06** | **Silent fallback** | **Step 6 prompt 提 "team" 但 VALID_ROUTES 排除；LLM 回 team 冇 log** | **🟢 LOW** | **Round 2（新）** | **0.2 天** |
| **P-07** | **Silent swallow** | **Step 8 consolidation ImportError 被 pass 無 log** | **🟢 LOW** | **Round 2（新）** | **0.1 天** |
| **IR-01** | **Contract** | **LLMClassifier 錯誤路徑 confidence 0.0 vs 0.5 三個不同 default** | **🟡 MEDIUM** | **Round 2（新）** | **0.3 天** |

### 4.2 校正後 P0-P2 優先序（v1.1 — 併入 Round 2 發現）

**P0 — 必做（合規 / 功能正確性 / Decision quality）— 總計 ~12 天**

| Sprint | ID | 任務 | 估時 | 依賴 |
|--------|----|------|------|------|
| **Sprint 001**（即啟無依賴） | M-01 | `search_memory` 修復（用正確 API：`manager.search(query, user_id, ...)`） | 1 天 | 無 |
| **Sprint 001** | HITL-01 | 修復 `handle_request_approval` 實際 call controller | 1 天 | 無 |
| **Sprint 002**（部分依賴 Workshop）| K-01 + K-02 + K-03 + E-01 | Knowledge wiring + embedding 三處漂移統一（delegate + config centralization）| 2-3 天 | Workshop Q10 / Q12 |
| **Sprint 002** | TH-01 | 修復 handle_dispatch_workflow 實際 call adapter.execute | 1 天 | 無 |
| **Sprint 002** | TH-02 | 修復 handle_dispatch_swarm 實際 dispatch worker | 1 天 | 無 |
| **Sprint 002** | TH-03 | 修復 handle_dispatch_to_claude 實際 call coordinator.coordinate_agents | 1 天 | 無 |
| **Sprint 002** | TH-04 | 統一 dual risk engine（Pipeline + Agent tool 用同一套 policy）| 1.5 天 | 無 |
| **Sprint 003**（依賴 Workshop）| A-01 | Main chat audit emission（**async outbox pattern**）+ feature flag | 3-4 天 | Workshop Q5 / Q7 |
| **Sprint 003** | ER-01 | DOMAIN_TOOLS 補 dispatch tools + registry self-consistency | 0.5 天 | 無 |
| **Sprint 003** | CTX-01 | to/from_checkpoint_state 補 5 欄位 + 加 round-trip test | 0.8 天 | 無 |

**P0 合計**：~12 天（原 7-9 天 + Round 2 新增 ~4.5 天）

**P1 — 應做（code quality / safety / CI 防線）— 總計 2-3 週**

| ID | 任務 | 估時 |
|----|------|-----|
| A-02 + A-03 | 刪 orphan AuditLogger + rename 避命名衝突（資安 panel 升級）| 1 天 |
| A-05 | 驗證 pipeline/persistence.py scope 與 A-01 關係 | 0.5 天 |
| C-01 + CTX-02 | Context state / checkpoint restore 補全 | 1 天 |
| K-05 | Singleton RAGPipeline（dispatch_handlers.py 優化） | 0.5 天 |
| K-06 | Cohere Rerank 3 + 50-query RAPO ground truth 實測 | 1 週 |
| P-01 + P-03 + P-05 | Config centralization（AZURE deployment / thresholds / enum）| 1 天 |
| ER-02 + ER-03 | Registry dead binding 清理 + naming 修正 | 0.5 天 |
| IR-01 | LLMClassifier error path contract 統一 | 0.3 天 |
| TH-05 | create_task / update_task_status ImportError guard | 0.2 天 |
| CI-01 + CI-02 | Import-existence + config-centralization CI lint | 1-2 天 |
| **新 CI-03** | **Fake dispatcher detection — AST check「每 dispatch_* handler 必須 call 至少一個 async business method」** | **1 天** |
| **新 CI-04** | **Checkpoint round-trip property test（property-based）**| **0.5 天** |

**P2 — Doc 08 原計劃（合 Panel 補充 + Round 2 低風險 items）— 4-8 週**

| ID | 任務 | 估時 |
|----|------|-----|
| A-04 + WORM-01 + PII-01 | Bitemporal + immutable + WORM (pg trigger + Immutable Blob hash chain) + PII dual-layer redactor | 4-6 週 |
| K-04 | Agent Skills YAML 化 + 與 Qdrant 統一 | 1-2 週 |
| L3 | Graphiti + Neo4j / **Kuzu**（先 PoC） | 10 週 |
| L5 Verifier | Two-stage + risk-gated（非 per-query） | 2-3 週 |
| P-02, P-04, P-06, P-07, CTX-03, O-01, M-02 | LOW 級雜項清理（合計 ~1.5 天）| 1.5 天 |

---

## 五、Stakeholder 下一步必須答嘅問題

按 Business Panel + Technical Panel 綜合：

### 5.1 組織定位（Business Panel）
1. **IPA 定位**：RAPO 落地專案 or 通用 enterprise platform？
2. **Data Steward accountability**：CFO / CIO / CDO 邊個擁有 L3 Ontology governance？（必須 Month 0 close）
3. **Commercial model**：internal-only / SaaS / BU-shared？影響 multi-tenant 設計
4. **Slice 2 候選**：freight invoice 之後係？影響 schema generalization

### 5.2 Roadmap 決策（Business + Technical）
5. **6-month vs 9-month**：動機係 budget / competitive pressure / stakeholder commitment？建議用 milestone-based 非 date-based
6. **SAP team RACI**：Month 1 engage 邊個簽？
7. **L4-Q3 Analogy 60-70% 商業接受度**：邊個 stakeholder 簽 HITL fallback 入 production？

### 5.3 合規邊界（Security Panel）
8. **IPA 最終用途是否涉及 SOX / EU AI Act high-risk AI**？若是，A-01 升級為 Phase 1 GA 阻斷條件
9. **PII / PHI 範圍界定**：GDPR vs HIPAA vs 本地合規（PDPO 等）優先級

### 5.4 技術基礎決策
10. **Qdrant 生產模式**：server / local / Azure AI Search？
11. **Graph backend**：Neo4j（full-feature）/ Kuzu（embedded PoC）/ Memgraph（兼容 + 快）？
12. **Embedding 維度**：3-large 3072 / 3-large Matryoshka 1536 / ada-002？

---

## 六、建議採用流程

### Week 1（本週）
1. 將本 Review 與 Delta / Wiring Audit 一併呈 stakeholder
2. 召開 1 小時 **定位 workshop** 答 Q1-Q4
3. 指派 Data Steward（Q2 答案）
4. 決定 Q5（roadmap 壓縮動機）

### Week 2-3
5. 執行 P0-1（Knowledge wiring 統一 + embedding centralization，3 天）
6. 執行 P0-2（search_memory 修復，1 天）
7. 執行 P0-3（Audit emission async outbox，3-4 天）
8. 執行 HITL-01 修復

### Week 4
9. Retrospective：P0 修復後重跑 wiring audit 驗證
10. 規劃 P1（含 Cohere Rerank 實測 2 天、$30）
11. 啟動 L3 Ontology 研究（Kuzu PoC，先於 Neo4j decision）

---

## 七、Panel Performance 總結

| Panel | 獨特貢獻 | 最強建議 |
|-------|---------|---------|
| 系統架構師 | L5 two-stage verifier、L3 thin ontology、Month 0 Expert Fit PoC | L3 thin ontology hardcode fallback |
| 後端架構師 | Qdrant server 強制、Kuzu first、async outbox pattern | K-01 分兩步 + Kuzu 省 2-3 週 |
| 資安工程師 | A-01 升級為 legal exposure、WORM + hash chain、M-01 升級為 integrity | A-01 Month 2 compliance gate |
| 效能工程師 | 數字估算（$50-200k Verifier）、Matryoshka、audit sync latency 修正 | Verifier gating + async outbox |
| code-reviewer | Audit 報告 API 錯誤糾正、HITL-01 新發現 | M-01 正確 API + K-01 delegate 方向 |
| 根因分析師 | E-01 embedding 三漂、C-01/C-02、CI lint、審計 methodology | Config centralization + CI import check |
| 商業顧問 | Data Steward Day 0、commercial model 盲點、6-month vs 9-month synthesis | Keep 9-month + parallel optionality |

**Panel 最 actionable 共同訊息**：
> **P0 修復需完整（含 Panel 新增 E-01、HITL-01），A-01 用 async outbox，Data Steward Month 0 任命，roadmap 保 9-month + parallel optionality，L3 先 Kuzu PoC 再決 Neo4j。**

---

## 八、版本記錄

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-20 | Claude + 7 agent panel | Initial multi-expert review |
| **1.1** | **2026-04-20** | **Claude（合併 Doc 12 Round 2）** | **併入 Audit Round 2 發現 19 個 gap（6 HIGH）；P0 工期 7-9 天 → ~12 天；新增 Fake Dispatcher pattern 與 CI-03/CI-04；P0 分 3 個 sprint（001 無依賴 / 002 部分依賴 Workshop / 003 依賴 Workshop）**|

**Related docs**：
- Doc 00-08：Research series（2026-04-17）
- Doc 09：IPA main delta（2026-04-19）
- Doc 10：Wiring audit Round 1（2026-04-20）
- **Doc 11（本文）**：7-agent panel review + Round 2 integration（v1.1）
- **Doc 12：Wiring audit Round 2**（2026-04-20）— 發現 Fake Dispatcher pattern
- **Doc 13**：Positioning Workshop agenda（2026-04-20）— 12 stakeholder questions
- **Doc 14**：Sprint Wiring Fix 001 plan + checklist（M-01 + HITL-01，即啟無依賴）

**7 agent outputs（完整 transcript）**：
- `C:\Users\Chris\AppData\Local\Temp\claude\C--Users-Chris-Downloads-ai-semantic-kernel-framework-project\36dcb400-6a52-49c5-a3a9-124f56732c1a\tasks\a72cad87551792abe.output`（系統架構師）
- `...a72e995bb01c86912.output`（後端架構師）
- `...a4212a20bd34708c3.output`（資安工程師）
- `...ad4b7367fdd138286.output`（效能工程師）
- `...ac06c8e6f6ff9f8f0.output`（code-reviewer）
- `...a7b3b3d4bebb32105.output`（根因分析師）
- `...a7445e296deef33f5.output`（商業決策顧問）

（output 檔案保存於臨時目錄，session 結束可能清理。本 Doc 已摘錄所有核心內容。）
