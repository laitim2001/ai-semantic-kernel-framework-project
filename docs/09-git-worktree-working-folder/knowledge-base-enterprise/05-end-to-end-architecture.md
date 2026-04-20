# 05 - 端到端架構設計

**範圍**：Cross-department query 嘅 6-layer 架構、每層複雜度分析、真實 build 難度

---

## 一、Case Study：單一 Query，Full Stack 需求

用一個真實會喺 IPA Platform 出現嘅問題做例子：

> **「上個月 RICOH HK 嘅 freight invoice 點解超預算 12%？同我哋上次 contract renewal 嘅承諾係咪 align？另外，個 issue 同上年同期我哋同 Yamato 嗰單 dispute 有冇類似 root cause？而家我可以 approve 個 invoice 嗎？」**

### 拆解：包含嘅 Cognitive Operations

呢條 query 包含 **4 個 sub-question，9 個 cognitive operation**：

| # | 操作 | 涉及 |
|---|------|------|
| 1. Resolve「RICOH HK」係邊個 entity | Vendor master data（Finance） |
| 2. 搵「上個月」嘅 freight invoice | SCM invoice system + AIDE |
| 3. 計算「超預算 12%」 | Budget data（Finance）+ 數學運算 |
| 4. 搵 contract renewal「承諾」 | Contract repository（Legal）+ semantic understanding |
| 5. 對比 invoice vs contract terms | Cross-domain reasoning |
| 6. 搵「上年同期 Yamato dispute」 | Incident history（Operations）+ temporal reasoning |
| 7. 識別「類似 root cause」 | Causal analogy across cases |
| 8. 判斷「我可以 approve 嗎」 | RBAC + approval policy |
| 9. 所有 step audit-traceable | Governance |

### 純 Agentic RAG + GraphRAG 做到邊幾步？

- **Step 1**：部分。Graph 可以 link aliases，但前提係 graph 已包含 Finance vendor master
- **Step 2, 3**：失敗。呢啲係 structured operational data，RAG native 唔 handle
- **Step 4, 5**：部分。GraphRAG 可 retrieve clauses，但**唔識 reason** 「12% vs ±10% acceptable」係否 violation
- **Step 6**：勉強。Bitemporal KG 做得好
- **Step 7**：失敗。「類似 root cause」要 causal model，唔係 similarity model
- **Step 8**：完全唔關 RAG 事
- **Step 9**：RAG 自己冇 audit

**結論**：9 個 operation，agentic RAG + GraphRAG 勉強處理 2-3 個，其餘 6-7 個唔係佢負責

---

## 二、完整 6-Layer 架構

```
┌──────────────────────────────────────────────────────────────────┐
│  L0  IDENTITY & SESSION                                          │
│  Azure SSO → JWT → OBO token for downstream                     │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  L1  INPUT GATEWAY                                               │
│  Normalize input → UnifiedRequestEnvelope                        │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  L2  QUERY DECOMPOSITION (Orchestrator Agent)                    │
│  ClaudeAgent + Active Retrieval                                  │
│  - Generate intent topics                                        │
│  - Decompose into Q1/Q2/Q3/Q4 with dependencies                 │
│  - Dispatch to specialists                                       │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  L3  ENTITY RESOLUTION / ONTOLOGY LAYER ⭐                       │
│  Resolve named entities to canonical IDs                         │
│  - "RICOH HK" → Vendor.V0023                                     │
│  - "上個月" → TimeRange[2026-03-01, 2026-03-31]                 │
│  - "I" (Tom) → Employee.U1042                                    │
│  Backend: Microsoft Fabric IQ / Graphiti / Neo4j                │
└──────────────────────────────────────────────────────────────────┘
                              ↓ (Shared Knowledge Context broadcasts)
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  L4  SPECIALIST AGENT LAYER (parallel)                           │
│                                                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌────────────┐ ┌─────────────┐│
│  │ Variance    │ │ Compliance  │ │ Analogy    │ │ Authorization││
│  │ Analyzer    │ │ Checker     │ │ Finder     │ │ Agent        ││
│  │ (Q1)        │ │ (Q2)        │ │ (Q3)       │ │ (Q4)         ││
│  └─────────────┘ └─────────────┘ └────────────┘ └─────────────┘│
│                                                                  │
│  Shared data sources: SAP/ERP, Contract Repo, Agentic Memory,  │
│                       External APIs, Email/Slack                │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  L5  VERIFICATION & SYNTHESIS                                    │
│  - Verifier Agent (Claude Opus): cross-check claims vs sources  │
│  - Synthesizer Agent: combine into coherent narrative           │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  L6  GOVERNANCE & AUDIT                                          │
│  - Bitemporal audit logger                                       │
│  - PII redactor                                                  │
│  - EU AI Act classification                                      │
└──────────────────────────────────────────────────────────────────┘
                              ↓
                    FINAL ANSWER + CITATIONS
```

---

## 三、逐 Layer Build 難度分析

評分標準：
- **可實現性**：✅ Production-ready / ⚠️ Workable but tricky / ❌ Frontier research
- **複雜度**：🟢 Easy / 🟡 Medium / 🔴 Hard / 🔥 Very Hard

### L0 - Identity & Session Layer (Azure SSO + OBO)

| 評估 | 結果 |
|------|------|
| 可實現性 | ✅ Production-ready |
| 複雜度 | 🟢 Easy（你已 95% 完成）|
| 估時 | 3-4 週 |
| 現狀 | 已有 Azure SSO + JWT，OBO PoC 進行中 |

**剩餘工作**：Token vault、token refresh middleware、cross-org OBO flow
**風險點**：token caching strategy、refresh token rotation

---

### L1 - Input Gateway

| 評估 | 結果 |
|------|------|
| 可實現性 | ✅ Done |
| 複雜度 | 🟢 Done |
| 現狀 | 已完成（Phase 28 InputGateway）|

**無需更動**

---

### L2 - Orchestrator Agent (ClaudeAgent + Active Retrieval)

| 評估 | 結果 |
|------|------|
| 可實現性 | ✅ Production-ready |
| 複雜度 | 🟡 Medium |
| 估時 | 6-8 週 |
| 現狀 | V8.1 計劃轉 ClaudeAgent |

**核心 challenge 唔係技術，係 prompt engineering**

```python
ORCHESTRATOR_SYSTEM_PROMPT = """
For every user request:

1. INTENT DECOMPOSITION
   - Cognitive type (Diagnostic / Compliance / Analogical / Authorization)
   - Required entities (call entity_resolve)
   - Dependencies

2. ENTITY RESOLUTION (always first)
   All specialists must reference resolved canonical IDs.

3. SPECIALIST DISPATCH
   Parallel when independent; sequential when dependencies exist.

4. SYNTHESIS COORDINATION
   Dispatch to synthesizer + verifier.
"""
```

**風險點**：decomposition 出錯 → cascading failure；token consumption 高；latency

---

### L3 - Ontology / Entity Resolution Layer ⭐

| 評估 | 結果 |
|------|------|
| 可實現性 | ✅ Production-ready（Graphiti 路線）/ ⚠️ Tricky（Fabric IQ preview） |
| 複雜度 | 🟡 Medium |
| 估時 | 10 週 |
| 詳細見 | Doc 06 |

---

### L4-Q1 - Variance Analyzer Agent

| 評估 | 結果 |
|------|------|
| 可實現性 | ✅ Production-ready |
| 複雜度 | 🟡 Medium |
| 估時 | 4-6 週 |

**核心 components**：
1. SAP MCP server（新建，~2 週）
2. ERP/Budget MCP server（同上）
3. AIDE invoice OCR（已有）
4. Variance attribution prompt（1 週 iterate）
5. Historical RAG over past invoices（1-2 週）

**風險點**：
- SAP integration 永遠係 enterprise project 最 painful（ABAP、ALE、BAPI、license）
- Numeric precision（financial 必須 deterministic Python，唔用 LLM 計）
- Currency conversion / exchange rate

---

### L4-Q2 - Compliance Checker Agent

| 評估 | 結果 |
|------|------|
| 可實現性 | ✅ Production-ready |
| 複雜度 | 🟡 Medium |
| 估時 | 6-8 週 |

**核心 components**：
1. Contract ingestion（PDF parsing、chunking）
2. Hybrid RAG over contracts（vector + BM25 + reranker）
3. Cohere Rerank 3 或 BGE-reranker-v2（1 週）
4. External data MCP（fuel index 等）
5. Email MCP（MS Graph API）
6. Rule-application prompt + structured output

**風險點**：
- Contract clause conditional reasoning（「unless... exceeds...」LLM 容易錯）
- Citation accuracy 必須準確
- Multi-version contract handling（renewal、amendment chain）

---

### L4-Q3 - Analogy Finder Agent 🔴 最難

| 評估 | 結果 |
|------|------|
| 可實現性 | ⚠️ Workable but tricky |
| 複雜度 | 🔴 Hard |
| 估時 | 12-16 週（80% production quality）|

**核心 challenge**：

「Causal similarity」≠「Embedding similarity」

Yamato 2025 同 RICOH 2026 喺 vector space 可能唔似（唔同 vendor、金額、時間），但 causal structure 高度類似。

**現實 Hybrid Pragmatic Approach**：

```
Step 1: Structured case extraction
  每個 incident case 抽取 structured schema:
  - root_cause_category
  - involved_parties
  - trigger_event_type
  - resolution_pattern

Step 2: Multi-strategy retrieval
  a. Vector search over case description (broad recall)
  b. Structured filter on root_cause_category (precision)
  c. Graph traversal (related vendors, similar contract types)

Step 3: LLM-as-Judge causal similarity
  每個 candidate case，用 Claude Opus 比較 causal structure

Step 4: Top-K return with explanation
```

**風險點**：
- Quality 唔保證 — analogy 質素極依賴 case 標註質量
- Cold start problem — 冇歷史 case 就 work 唔到
- LLM-as-judge 一致性問題
- Evaluation 困難 — 「呢兩個 case 算唔算 analogous」有主觀性

**Honest expectation**：Phase 1 60-70% quality，Phase 2 80%。100% 唔現實。

**降級方案**：low-confidence 時標記「請 reviewer 確認」，final judgment 留俾 human

---

### L4-Q4 - Authorization Agent

| 評估 | 結果 |
|------|------|
| 可實現性 | ✅ Production-ready |
| 複雜度 | 🟡 Medium |
| 估時 | 4-6 週 |

**核心 components**：
1. Identity service（已有 JWT + RBAC）
2. Policy engine — **Open Policy Agent (OPA)** 係 industry standard
3. Risk aggregator（從 Q1/Q2/Q3 收集 risk signals）
4. Approval chain lookup

**OPA 範例**：
```rego
package ipa.invoice_approval

default allow = false

allow {
    input.user.role == "Finance_Manager"
    input.invoice.amount_usd <= input.user.approval_limit
    not high_risk_signal
}

high_risk_signal {
    input.signals.compliance_violation == true
}

require_escalation {
    high_risk_signal
    not input.user.role == "Senior_Manager"
}
```

**風險點**：policy authoring 需 cross-functional alignment（Finance、Legal、Compliance）

---

### L5 - Verifier Agent

| 評估 | 結果 |
|------|------|
| 可實現性 | ✅ Production-ready |
| 複雜度 | 🟢 Easy |
| 估時 | 2-3 週 |

**Pattern**：另一個 ClaudeAgent instance（建議 Opus），對每個 specialist output 逐 claim 驗證

**Prompt**：
```
For each claim:
1. Identify supporting citation
2. Re-fetch source data
3. Verify claim is grounded
4. Output: {claim, citation, verified, confidence, issue}
```

**風險點**：token cost 增加、latency 增加、verifier 自己會錯

---

### L5 - Synthesizer Agent

| 評估 | 結果 |
|------|------|
| 可實現性 | ✅ Production-ready |
| 複雜度 | 🟢 Easy |
| 估時 | 1-2 週 |

純 prompt engineering，將 4 個 sub-answer 組合 + citations

---

### L6 - Bitemporal Audit Logger

| 評估 | 結果 |
|------|------|
| 可實現性 | ✅ Production-ready |
| 複雜度 | 🟡 Medium |
| 估時 | 4-6 週 |

**Schema**：
```sql
CREATE TABLE audit_events (
    event_id UUID PRIMARY KEY,
    trace_id VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    ingestion_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    agent_id VARCHAR NOT NULL,
    action VARCHAR NOT NULL,
    inputs JSONB,
    outputs JSONB,
    citations JSONB,
    parent_event_id UUID REFERENCES audit_events(event_id),
    pii_redacted BOOLEAN DEFAULT FALSE,
    risk_class VARCHAR,
    INDEX idx_trace (trace_id),
    INDEX idx_user_time (user_id, event_time DESC),
    INDEX idx_chain (parent_event_id)
);

CREATE RULE audit_immutable AS ON UPDATE TO audit_events DO INSTEAD NOTHING;
CREATE RULE audit_no_delete AS ON DELETE TO audit_events DO INSTEAD NOTHING;
```

**風險點**：storage growth、query performance、compliance scope 需 legal team

---

## 四、整體 Build vs Adopt 矩陣

| Layer | 自建可行 | 推薦路線 | 估時 | 主要風險 |
|-------|---------|---------|------|---------|
| L0 Identity + OBO | ✅ | 自建（已 PoC）| 3-4 週 | Token caching |
| L1 Input Gateway | ✅ | 已完成 | — | — |
| L2 Orchestrator | ✅ | 自建（V8.1）| 6-8 週 | Prompt quality |
| L3 Ontology | ✅ | **Graphiti + LLM-assisted** | 10 週 | Schema alignment |
| L4-Q1 Variance | ✅ | 自建（多 SAP MCP）| 4-6 週 | SAP integration |
| L4-Q2 Compliance | ✅ | 自建（加 reranker）| 6-8 週 | Conditional rules |
| L4-Q3 Analogy | ⚠️ | 自建（hybrid pragmatic）| 12-16 週 | Causal quality |
| L4-Q4 Authorization | ✅ | 自建 + OPA | 4-6 週 | Policy authoring |
| L5 Verifier | ✅ | 自建 | 2-3 週 | Verifier errors |
| L5 Synthesizer | ✅ | 自建 | 1-2 週 | 細節 |
| L6 Bitemporal Audit | ✅ | 自建 PostgreSQL | 4-6 週 | Storage growth |

**Total（sequential）**：~70 週 = 16 個月
**現實（parallel + leverage）**：~9 個月

---

## 五、Realistic 9-month Timeline

```
Quarter 1 (Month 1-3):
├── L0 OBO production
├── L3 Ontology (Graphiti) ⭐
├── L6 Bitemporal Audit
└── L2 Orchestrator migration 開始

Quarter 2 (Month 4-6):
├── L2 Orchestrator 完成
├── L4-Q1 Variance Analyzer
├── L5 Verifier + Synthesizer
└── L4-Q4 Authorization (start)

Quarter 3 (Month 7-9):
├── L4-Q2 Compliance Checker
├── L4-Q4 完成
└── L4-Q3 Analogy Finder (start)

Quarter 4 (Month 10-12):
└── L4-Q3 Analogy refinement
```

**9 個月 deliver Q1+Q2+Q4 完整 production，Q3 達 80% quality**

---

## 六、Risk Summary

### 高風險 component（潛在 derail project）

1. **L4-Q3 Analogy Finder（causal reasoning）**
   - 唔係 build 唔到，係 quality 標準難定義
   - Mitigation：early evaluation harness + HITL fallback

2. **L3 Ontology schema 跨部門 alignment**
   - 純技術冇難度，**business alignment 係 killer**
   - 例：「Vendor」喺 Finance vs Procurement 定義唔同
   - Mitigation：由 1 個 department、1 個 use case 開始

3. **SAP / ERP integration（L4-Q1）**
   - 技術 doable，organizational friction 高
   - SAP team protective，approval cycle 長
   - Mitigation：early engagement，先 PoC sandbox

### 中風險 component

4. **L2 Orchestrator decomposition quality** — prompt engineering 問題，可控
5. **L4-Q2 Conditional rule reasoning** — 需 structured rule extraction + Python execution

### 低風險 component

6. L0、L1、L5、L6 — engineering 問題，路徑清晰

---

## 七、最 Critical 嘅 Decision

**揀 1 個 narrow 嘅 RAPO use case 做 Phase 1 vertical slice**，全 stack（L0-L6）端到端做完。

**比一次過 build 11 個 component 但個個都係 80% 完成穩陣得多**。

推薦：**Freight invoice variance analysis** 做第一個 vertical slice。涵蓋：
- L0 identity
- L3 ontology（基本 entity：Vendor、Invoice、Budget）
- L4-Q1 specialist
- L5 verification
- L6 audit

呢個 slice 完成後，加第二個 use case 嘅 marginal cost 大幅下降（L0/L1/L3/L5/L6 reusable）。

---

*整理自 2026-04 系列討論*
