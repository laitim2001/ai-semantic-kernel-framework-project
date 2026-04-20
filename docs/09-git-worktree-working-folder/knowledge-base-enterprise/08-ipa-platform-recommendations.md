# 08 - 對 IPA Platform 嘅建議總結

**範圍**：Gap analysis、9-month roadmap、critical success factors、build vs buy decisions

---

## 一、Executive Summary

IPA Platform 嘅 memory 同 knowledge subsystem 需要由「零散 feature」演化成「integrated knowledge runtime」。基於前面 7 份 doc 嘅分析，**core recommendation**：

1. **唔需要 Day 1 build full stack** — 80% query 用 Hybrid RAG + Agentic RAG 已夠
2. **最 critical 投資係 Ontology layer (L3)** — Graphiti 路線 10 週 deliver
3. **Vertical slice approach** — 揀 freight invoice variance 做 Phase 1 end-to-end
4. **Cross-department alignment 係真正風險** — 技術路徑清晰

---

## 二、對照 V8 現狀嘅 Gap Analysis

### 已有 Building Blocks ✅

- Azure SSO + JWT（L0 大部分完成）
- OBO PoC 進行中（L0 finish）
- InputGateway（L1 完成）
- HybridOrchestratorV2（L2 基礎，但需 migrate 去 ClaudeAgent）
- 8 MCP Servers（reusable pattern）
- AIDE document processing
- Azure AI Search（hybrid search 基礎）
- mem0 三層記憶（V8 現狀，需升級）
- ADF MCP / n8n workflow（ingestion orchestration 基礎）
- PostgreSQL infrastructure（audit log 基礎）

### 部分有但需升級 ⚠️

| Component | V8 現狀 | 目標狀態 | Gap |
|-----------|---------|----------|-----|
| Orchestrator | Python control flow (HybridOrchestratorV2) | ClaudeAgent + Active Retrieval | V8.1 計劃中 |
| Memory | mem0 3 層 | 6-component + Active Retrieval | 需 schema 擴充 |
| RAG | Azure AI Search hybrid | + Reranker (Cohere/BGE) | Quick win |
| Audit | In-memory FIFO (issue C-01) | PostgreSQL bitemporal | 需 migration |
| Entity Resolution | Ad-hoc | Graphiti-managed | 需 new layer |

### 完全冇 ❌

| Component | Rationale |
|-----------|-----------|
| Ontology Layer (L3) | **最大 missing piece** |
| Bitemporal Knowledge Graph | Audit + temporal reasoning 需要 |
| Analogy / Causal Reasoning (L4-Q3) | Frontier capability |
| Policy Engine (OPA) for L4-Q4 | RBAC 不夠，需 ABAC |
| Verifier Agent (L5) | Quality gate 缺失 |
| Compliance Specialist (L4-Q2) | Contract reasoning 缺失 |
| Variance Specialist (L4-Q1) | SAP integration 缺失 |

---

## 三、推薦路線：9-Month Roadmap

### Quarter 1 (Month 1-3): Foundation

**Theme**：基建 + Ontology + 第一個 vertical slice 開始

```
Month 1:
├── [L0] OBO production hardening
├── [L3] Graphiti setup + Neo4j deployment
├── [L3] LLM-assisted schema discovery (Week 1-2)
├── [L3] Pydantic entity/edge definitions (5-10 entity)
├── [L6] Bitemporal audit PostgreSQL schema
└── [Ingestion] Source inventory spreadsheet

Month 2:
├── [L3] Vendor master + contract ingestion
├── [L3] Entity resolution review workflow
├── [L6] Audit logger production
├── [L2] Orchestrator migration 開始 (ClaudeAgent)
└── [Quick Win] Cohere Rerank 3 integration to AI Search

Month 3:
├── [L3] Graphiti MCP server (expose search/resolve/ingest)
├── [L2] Orchestrator completion (Active Retrieval)
├── [L3] Integration test: Orchestrator → Graphiti MCP
└── [Monitoring] Data steward UI MVP
```

**Deliverable**：
- ✅ Ontology + Memory + Bitemporal 三層 live
- ✅ Orchestrator 可 query Graphiti
- ✅ Audit trail 完整
- ✅ Vendor master + contracts 已 ingest

### Quarter 2 (Month 4-6): Specialist Agents Wave 1

**Theme**：第一批 specialist agent + Authorization

```
Month 4:
├── [L4-Q1] SAP MCP server
├── [L4-Q1] ERP/Budget MCP server
├── [L4-Q1] Variance Analyzer prompt + structured output
└── [L5] Verifier Agent (Claude Opus)

Month 5:
├── [L4-Q1] End-to-end integration
├── [L5] Synthesizer Agent
├── [L4-Q4] Start OPA integration
└── [Testing] Freight invoice variance use case E2E

Month 6:
├── [L4-Q4] Authorization Agent complete
├── [L4-Q4] Policy authoring workflow
├── [Production] Freight invoice variance GA
└── [Learning] Retrospective + plan Q3
```

**Deliverable**：
- ✅ 第一個 **end-to-end vertical slice production-ready**：「我可唔可以 approve 呢張 invoice？」
- ✅ Authorization policy 框架

### Quarter 3 (Month 7-9): Compliance + Analogy

**Theme**：Compliance specialist + 開始 tackle Analogy（最難）

```
Month 7:
├── [L4-Q2] Contract ingestion scale-up
├── [L4-Q2] Compliance Checker Agent
├── [L4-Q2] External data MCP (fuel index etc.)
└── [L4-Q3] Start: structured case schema design

Month 8:
├── [L4-Q2] Conditional rule reasoning
├── [L4-Q2] Citation accuracy evaluation
├── [L4-Q3] Case extraction pipeline
└── [L4-Q3] Multi-strategy retrieval (vector + structured + graph)

Month 9:
├── [L4-Q2] Production GA
├── [L4-Q3] LLM-as-Judge causal similarity
├── [L4-Q3] Evaluation harness
└── [Production] 2-3 additional vertical slices live
```

**Deliverable**：
- ✅ Compliance checking production
- ⚠️ Analogy Finder 60-70% quality（HITL fallback）

---

## 四、Critical Success Factors

### Technical

1. **Graphiti 路線決定 early**
   - 好處：三層（Ontology + Memory + Bitemporal）一次過
   - 風險：Neo4j ops learning curve，需要 1 個 senior engineer 專注

2. **Vertical slice discipline**
   - 唔好追求 11 個 component 個個 80%
   - 追求 1 個 vertical slice 100% production
   - 後續 slice marginal cost 急降

3. **Schema design 花夠時間**
   - Week 1-2 唔好趕
   - LLM-assisted discovery + engineer review + stakeholder validation
   - 一旦 schema 錯，後期修補極辛苦

4. **Reranker 係 free lunch**
   - Cohere Rerank 3 加入 AI Search 零架構改動
   - +15-30% precision，Month 1 可 deliver

### Organizational

5. **Cross-department entity alignment**
   - 「Vendor」喺 Finance / Procurement / Legal 定義唔同
   - 解法：由 1 department 開始，其他做 extension
   - 定期 cross-functional meeting

6. **SAP team early engagement**
   - Technical 上 doable，organizational approval cycle 長
   - Month 1 就 engage，sandbox PoC
   - 唔係 Month 4 先搵 SAP team

7. **Policy authoring stakeholder buy-in**
   - OPA 技術 1-2 週上手
   - 但「邊條 rule 應該點寫」需要 Finance / Legal / Compliance 三方 align
   - Governance process 要 early establish

8. **Data Steward role 要建立**
   - Entity resolution review
   - Schema evolution proposals
   - 6 個月後 graph quality 取決於呢個 role

### Evaluation

9. **Evaluation harness 要 Day 1 有**
   - 冇 metric 唔知好唔好
   - 每個 specialist agent 都要有 ground truth set
   - Retrieval precision + generation quality + end-to-end correctness 三個維度

10. **Failure mode 分類**
   - Retrieval miss？Write path 漏？Compression loss？Reasoning error？
   - 每類需要唔同 mitigation

---

## 五、Build vs Buy Decision Matrix

| Component | Build | Buy | Recommendation |
|-----------|-------|-----|----------------|
| L0 SSO | ✅ (Azure SSO) | — | ✅ Build (已有) |
| L1 Gateway | ✅ | — | ✅ Build (已完成) |
| L2 Orchestrator | ✅ (ClaudeAgent) | ❌ | ✅ Build (V8.1 計劃) |
| L3 Ontology | ✅ (Graphiti) | ⚠️ (Fabric IQ preview) | ✅ **Build with Graphiti** |
| L4-Q1 Variance | ✅ | ❌ | ✅ Build |
| L4-Q2 Compliance | ✅ | ⚠️ (Workiva) | ✅ Build (更 flexible) |
| L4-Q3 Analogy | ✅ Hybrid | ❌ | ⚠️ Build + HITL fallback |
| L4-Q4 Authorization | ✅ (OPA) | ❌ | ✅ Build |
| L5 Verifier | ✅ | — | ✅ Build |
| L5 Synthesizer | ✅ | — | ✅ Build |
| L6 Audit | ✅ (PostgreSQL) | ⚠️ (Datadog) | ✅ Build |
| Reranker | ⚠️ | ✅ Cohere Rerank 3 | ✅ **Buy Cohere** |
| Embedding | ⚠️ | ✅ Azure OpenAI | ✅ Buy |
| Vector DB | ⚠️ | ✅ Azure AI Search | ✅ Buy (已有) |
| Graph DB | ✅ (Neo4j self-host) | ⚠️ (Neo4j Aura) | ⚠️ Depends on ops capacity |
| Document Parser | ✅ (Docling) | ⚠️ (Unstructured.io) | ✅ **Build with Docling** |

---

## 六、Phase 1 Vertical Slice 建議

### 推薦：Freight Invoice Variance Analysis

**為咩呢個 slice**：
1. **Business value high**：每條 invoice 幾千到幾十萬 USD，錯誤 cost 高
2. **Scope 適中**：clear 嘅 query pattern，可以 end-to-end 做完
3. **Cover 5/6 layer**：涉及 L0 / L3 / L4-Q1 / L5 / L6
4. **Data 相對可得**：SAP + contract repo + budget data
5. **Stakeholder 明確**：Finance team 係 primary user

### Scope Definition

**In scope**:
- Vendor master ingestion（由 SAP）
- Contract repository ingestion（freight contracts only）
- Invoice variance calculation
- Contract clause compliance check（針對 surcharge / rate increase clauses）
- Historical similar invoice lookup（vector + graph hybrid）
- Audit trail

**Out of scope**（Phase 2）:
- Full analogy finder（causal similarity）
- Authorization engine（用 simple RBAC 先）
- 所有 non-freight invoice type

### Success Criteria

1. End-to-end latency < 30s for typical query
2. Citation accuracy > 95%（LLM-as-judge）
3. Audit trail 完整 + immutable
4. Finance team 接受度：> 70% query 答案 useful
5. False positive rate（錯誤 flag 合規 invoice）< 5%

---

## 七、Team Upskill Needs

### 必要 skills

| Skill | 學習時間 | 重要性 |
|-------|---------|--------|
| Pydantic + Python type | 1 週 | Critical（你 team 已有）|
| Neo4j + Cypher | 2-3 週 | High（1 個 engineer 專攻）|
| Graphiti API | 1 週 | High |
| Claude Agent SDK | 1 週（已熟）| Critical |
| MCP protocol | 1 週（已熟）| Critical |
| OPA / Rego | 1-2 週 | Medium |
| Bitemporal SQL pattern | 1 週 | Medium |
| Docling + VLM | 1 週 | Medium |

### Nice to have

| Skill | 學習時間 | 場景 |
|-------|---------|------|
| SAP BAPI / RFC | 2-4 週 | 如 team 無 SAP 經驗 |
| Cohere API | 1 天 | Reranker integration |
| Celery / n8n advanced | 1 週 | Ingestion orchestration |

### Hiring / External

建議 consider：
- **1 個 Data Steward**（part-time 開始）— Entity review、schema governance
- **1 個 ML Engineer**（for L4-Q3 evaluation harness）— 如果團隊冇 ML eval 經驗

---

## 八、Budget Considerations

### Infrastructure Cost（estimated monthly）

| Component | Cost Range (USD/month) | Notes |
|-----------|-----------------------|-------|
| Neo4j (self-hosted on Azure) | $500-2,000 | Depends on scale |
| Azure OpenAI (embedding + LLM) | $2,000-10,000 | 視 query volume |
| Claude API (Opus + Sonnet) | $3,000-15,000 | Orchestrator + Verifier |
| Azure AI Search | $500-2,000 | Hybrid search |
| Cohere Rerank 3 | $200-1,000 | Per 1M tokens |
| PostgreSQL (audit) | $200-500 | Growth driven |
| Monitoring (Datadog/etc) | $500-2,000 | |
| **Total** | **$7K-33K/month** | Scale dependent |

### Development Cost（9 months）

- 2-3 senior engineer × 9 months
- 1 data steward × 6 months part-time
- 1 ML engineer × 3 months (L4-Q3)
- External consulting（Graphiti/Neo4j expertise）：optional

### Cost Optimization

- Structured data 用 JSON episode type（extraction 效率最高）
- 細 chunk 用細 model（Haiku / gpt-4o-mini）
- 大 context 用 prompt caching
- Community rebuild 唔好 too frequent

---

## 九、Organizational Risks

### 真正 derail project 嘅風險

1. **Cross-department entity definition 僵持**
   - Mitigation：由 1 department start，明確定義「呢個 version 嘅 ontology」
   - Escalation path：RAPO leadership sponsor

2. **SAP team 唔 cooperate**
   - Mitigation：early stakeholder engagement（Month 1 start）
   - Alternative：先用 DW data，稍後再 direct integration

3. **L4-Q3 quality 唔達 stakeholder expectation**
   - Mitigation：early establish「Phase 1 60-70% quality + HITL」嘅 expectation
   - 唔好 over-promise

4. **Policy authoring 冇 ownership**
   - Mitigation：Governance committee early establish
   - 明確 accountability：Finance / Legal / Compliance representative

5. **Data Steward role 冇人做**
   - Mitigation：explicitly hire / assign
   - 唔可以當 engineer 兼職

### 技術風險（relatively manageable）

- Graphiti 0.x API evolution
- Neo4j performance tuning
- LLM cost spike
- Webhook reliability

---

## 十、Top 10 Immediate Actions

呢 10 個 action 可以 Week 1 開始：

1. ✅ **Sketch RAPO top 10 entities** + relationships on whiteboard
2. ✅ **Use case discovery workshop** — 收集 20-30 個 real query
3. ✅ **Source inventory spreadsheet** start filling
4. ✅ **Neo4j 部署**（Docker 開始，再 migrate 去 managed）
5. ✅ **Graphiti hello world**（ingest 10 個 sample episodes）
6. ✅ **Cohere Rerank 3 integration PoC**（1 week quick win）
7. ✅ **OBO production hardening** finish
8. ✅ **Bitemporal audit table** schema design
9. ✅ **SAP team intro meeting**（early engagement）
10. ✅ **ClaudeAgent migration plan** for orchestrator

---

## 十一、長期願景（Year 2-3）

### Year 2: Scale + Sophistication

- 5-8 vertical slices in production
- 擴展 ontology to cover HR、Asset management
- Advanced analogy reasoning（更近 causal similarity）
- Cross-tenant federation（如果 RAPO serve 多 BU）
- Proactive alerting（唔止 reactive Q&A）

### Year 3: Intelligence + Autonomy

- Agent autonomous execution for low-risk decisions
- Self-improving knowledge graph（schema evolution learning）
- Multi-modal fully（voice、image、video）
- Integration with Microsoft Fabric IQ（如當時 mature）
- Platform-level knowledge runtime

---

## 十二、Final Bottom Line

### 3 個唔可以漏嘅 Message

1. **Ontology 係真正 missing piece**
   - Day 1 start，Graphiti 路線 10 週 deliver
   - 呢個係所有其他 layer 嘅 dependency

2. **Vertical slice 勝過 horizontal completion**
   - 1 個 use case end-to-end 100% 好過 11 個 layer 個個 80%
   - Freight invoice variance 係理想 first slice

3. **Business alignment 比技術更難**
   - Cross-department entity definition
   - SAP approval cycle
   - Policy authoring stakeholder buy-in
   - 預計 30% effort 喺 organizational，唔係 technical

### 成功嘅 IPA Platform 會係點樣

12 個月後：
- 80% RAPO daily query 用 Hybrid RAG + Agentic RAG 快速回答
- 20% 高價值 query 通過 full stack 提供 verified + audited 答案
- Knowledge graph 有 100k+ entities，持續 update
- Finance manager 信任 IPA 嘅 approval recommendation
- 其他 RAPO department 排隊要 onboard

### 失敗嘅常見樣子

- 大量 feature 但冇 coherent user experience
- Knowledge graph 腐爛（冇 data steward）
- Specialist agent quality 唔穩定
- Stakeholder 唔信任 LLM 答案
- Audit trail 有 gap，compliance 擔心

**避免呢啲嘅關鍵**：呢份 roadmap 嘅執行 discipline + organizational commitment

---

*整理自 2026-04 系列討論*
*Final document in the series*
