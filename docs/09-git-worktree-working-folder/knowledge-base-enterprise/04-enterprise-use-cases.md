# 04 - 企業場景分析：25 個真實 Use Case

**範圍**：enterprise 真實 use case 分類、決策框架、典型 distribution

---

## 一、決策框架

問自己呢 7 條問題：

| 問題 | 答 Yes 偏向 | 答 No 偏向 |
|------|-----------|-----------|
| 答案可以喺 1-2 份文件揾到？ | Hybrid RAG | GraphRAG |
| 需要追蹤「fact 喺幾時為真」？ | GraphRAG (bitemporal) | Hybrid RAG |
| 需要 reason 跨多個 entity 嘅 relationship？ | GraphRAG | Hybrid RAG |
| Failure cost 高（regulatory / safety / financial）？ | GraphRAG | Hybrid RAG |
| Single query 需要 combine 5+ source？ | GraphRAG + Agentic | Hybrid RAG |
| 跨 session 要記得用戶偏好？ | Agent Memory | 唔需要 |
| Query 本質係 computation / aggregation？ | Text-to-SQL | RAG 都唔合適 |

**判斷方法**：
- 3+ Yes 在 GraphRAG 相關 → 認真考慮 GraphRAG 投資
- 2 Yes → Hybrid RAG + selective GraphRAG component
- 0-1 Yes → Hybrid RAG 已經夠

---

## 二、Hybrid RAG + Agentic RAG 足夠嘅 Use Case（佔 ~80%）

呢類嘅共通特徵：
- 答案主要喺 unstructured documents
- 唔需要 cross-entity multi-hop reasoning
- 唔需要 temporal precision
- Single query 涉及 1-3 個 source
- Failure cost 低

### UC1 - HR Policy Query Bot

**真實 query**：
- 「我懷孕咗，maternity leave 點計？」
- 「Hybrid work policy 點？每週幾日 WFH？」
- 「Probation period 內離職嘅 notice？」

**Source**：HR policy PDFs、employee handbook、benefits doc
**為咩 Hybrid RAG 足夠**：答案直接喺 policy doc，冇 multi-hop
**Production 例子**：Glean、Microsoft Copilot、Notion AI

---

### UC2 - IT Support Knowledge Base / Self-Service

**真實 query**：
- 「VPN connect 唔到 office network」
- 「點 reset AD password」
- 「Teams 入會議冇 audio」

**Source**：IT runbooks、known issues DB、past tickets
**升級成 Agentic**：當需要 take action（password reset）
**Production 例子**：ServiceNow Now Assist、Atlassian Rovo

---

### UC3 - Sales Battlecard / Competitive Intelligence

**真實 query**：
- 「同 Salesforce 比有咩優勢？」
- 「Competitor X 嘅 pricing comparison sheet 喺邊？」
- 「Objection handling 對 'too expensive' 點答？」

**Source**：Sales playbook、battlecards、case studies
**升級成 Agentic**：cross-reference customer history + battlecards
**Production 例子**：Gong、Highspot、Seismic

---

### UC4 - Customer Support Tier-1（Product Issues）

**真實 query**：
- 「點 export dashboard 做 PDF？」
- 「Subscription renewal 點 cancel？」
- 「Error code E-401 係咩意思？」

**Source**：Product documentation、user guides、release notes
**升級成 Agentic**：查 user account status + 提供解答
**Production 例子**：Intercom Fin、Zendesk AI、Decagon

---

### UC5 - Internal Engineering Documentation Search

**真實 query**：
- 「我哋 microservice authentication flow 點 work？」
- 「Database migration SOP 喺邊？」
- 「呢個 internal API spec 係點？」

**Source**：Confluence、internal wikis、READMEs、ADRs
**升級成 Agentic**：debug 場景 retrieve docs + read code + run test
**Production 例子**：Cursor、Claude Code 嘅部分功能

---

### UC6 - Legal Document / Contract Lookup（reference，非 reasoning）

**真實 query**：
- 「同 Vendor X 嘅 NDA 喺邊？」
- 「Standard MSA template 最新 version？」
- 「Termination clause 嘅 standard wording？」

**Source**：Contract repository、template library
**升級場景**：「對比 contract A 同 B 嘅 termination clause」→ Agentic 或 GraphRAG
**Production 例子**：Ironclad、LinkSquares

---

### UC7 - Financial Reporting Q&A（搵 report 入面內容）

**真實 query**：
- 「上 quarter EBITDA 點解低過預期？」
- 「Asia Pacific 嘅 revenue 係幾多？」
- 「Annual report 提到嘅 strategic priorities？」

**Source**：10-K、10-Q、earnings reports
**唔屬於呢類**：「Q3 sales 跌咗點解」需要 aggregation → Text-to-SQL
**Production 例子**：Bloomberg、AlphaSense、Hebbia

---

### UC8 - Onboarding / Training Content Discovery

**真實 query**：
- 「新入職第一週要做乜？」
- 「Compliance training 點 enrol？」
- 「AWS training material 喺邊？」

**Source**：LMS content、onboarding wikis、training materials
**Production 例子**：Workday、Cornerstone 嘅 AI search

---

### UC9 - Marketing Asset / Brand Guideline

**真實 query**：
- 「Brand color hex code？」
- 「Approved logo file 喺邊？」
- 「Tone of voice guideline？」

**Source**：Brand portal、DAM、style guide
**Production 例子**：Frontify、Bynder 嘅 AI search

---

### UC10 - Vendor / Procurement Knowledge Lookup

**真實 query**：
- 「呢個 software 我哋有冇 enterprise license？」
- 「Vendor onboarding SOP？」
- 「>$10K purchase approval 流程？」

**Source**：Procurement policy、approved vendor list、SOPs
**升級場景**：「我可唔可以 approve 呢張 PO」需要 user role + amount + vendor status → Agentic + 結構化
**Production 例子**：Coupa、SAP Ariba 嘅 AI assist

---

### UC11 - Product Documentation for Customers（External）

**真實 query**：
- 「點 integrate 你哋 product 同 Slack？」
- 「API rate limit 係幾多？」
- 「Free tier vs Pro tier feature 差別？」

**Source**：Public documentation、API docs、tutorials
**Production 例子**：Algolia DocSearch、Mintlify、Kapa.ai

---

### UC12 - Internal Process / SOP Lookup（非 IT）

**真實 query**：
- 「Travel reimbursement claim 點交？」
- 「Client entertainment expense limit？」
- 「員工離職 offboarding checklist？」

**Source**：Company SOPs、process documentation
**Production 例子**：Microsoft Copilot for Business、Glean

---

## 三、需要 GraphRAG / KG 嘅 Use Case（佔 ~20%）

呢類嘅共通特徵：
- Multi-hop entity reasoning
- Cross-source / cross-silo synthesis
- Temporal precision
- Relationship > Content matter
- Failure cost 高
- Single query 可能涉及 100+ entities

### UC13 - AML / Anti-Money Laundering Investigation

**真實 query**：
- 「Account A 過去 6 個月 funds 流去邊？」
- 「Customer 同 sanctions list 有冇 indirect relationship？」
- 「呢類可疑 pattern 喺其他 customer 有冇出現？」

**為咩需要 GraphRAG**：pure entity-relationship，multi-hop traversal，multi-source synthesis
**Production 例子**：Quantexa、ComplyAdvantage、Palantir Foundry（金融）

---

### UC14 - Pharmaceutical Drug-Drug Interaction

**真實 query**：
- 「Drug X 同 Drug Y 一齊有冇 contraindication？」
- 「Compound A 有冇 mechanism 類似已知 toxic drug？」

**為咩需要 KG**：Drug → Target → Pathway → Side Effect 嘅 multi-hop；已有成熟 ontology (DrugBank, ChEMBL)
**Production 例子**：BenevolentAI、Recursion、藥廠內部；Stardog 主 customer

---

### UC15 - Customer 360 / Account Intelligence（B2B Sales）

**真實 query**：
- 「Customer X 嘅 stakeholder map 同 influence 點？」
- 「過去 24 個月 touch points 有邊啲？」
- 「Tom 5 年前喺 Company A 用過我哋產品，而家轉 Company B 做 CTO」

**為咩需要 KG**：highly entity-centric，relationship 隨時間變化（bitemporal），multi-hop reasoning
**Production 例子**：Zep 主 use case、Outreach、Gong、6sense

---

### UC16 - Supply Chain Risk Analysis

**真實 query**：
- 「Tier-2/3 supplier 有冇 exposure 到 Country X sanctions？」
- 「Supplier A 出事，alternative supplier + lead time？」
- 「過去 3 年 supply disruption pattern？」

**為咩需要 GraphRAG**：multi-tier supplier relationship，Component→Part→Supplier→Country traversal
**Production 例子**：Resilinc、Interos、Palantir Foundry

---

### UC17 - Cybersecurity Threat Investigation

**真實 query**：
- 「呢個 IP 過去 30 日 access 邊啲 resources？同邊啲 IP communication？」
- 「呢個 alert 同上週 incident 有冇關聯？」
- 「呢個 account 嘅 access pattern 對比 peer group？」

**為咩需要 KG**：pure entity relationship，multi-hop attack chain，temporal correlation
**Production 例子**：Splunk Enterprise Security、CrowdStrike、Microsoft Sentinel

---

### UC18 - Clinical Decision Support（醫療）

**真實 query**：
- 「Patient 嘅 differential diagnosis？」
- 「Treatment guideline + contraindication 對 patient condition？」
- 「Similar cases 嘅 treatment outcome？」

**為咩需要 KG**：醫學本體 (SNOMED CT, ICD-11) 已係 ontology；Symptom→Disease→Treatment inference chains
**Production 例子**：Epic Cosmos、Glass Health、Hippocratic AI

---

### UC19 - Regulatory Compliance Mapping

**真實 query**：
- 「FDA 21 CFR Part 11 requirement 同我哋 SOP mapping？」
- 「New regulation 對我哋邊啲 internal controls 有 impact？」
- 「Compliance evidence traceability？」

**為咩需要 KG**：Regulation→Requirement→Control→Evidence→SOP 嘅 traceability graph；bidirectional links
**Production 例子**：Workiva、AuditBoard、製藥 GxP compliance

---

### UC20 - Research Knowledge Discovery / Literature Review

**真實 query**：
- 「過去 5 年 X 領域 research themes 演進？」
- 「呢個 hypothesis 同 literature 嘅 contradicting evidence？」
- 「Research group A 同 B 嘅 indirect collaboration？」

**為咩需要 GraphRAG**：MS GraphRAG 嘅 sweet spot（global sensemaking）；Author-Paper-Citation 天然 graph
**Production 例子**：藥廠 R&D、學術 institutions、Elicit、Consensus AI

---

### UC21 - Insurance Claims / Fraud Detection

**真實 query**：
- 「Claim 嘅 claimant-provider-witness 有冇異常 relationship？」
- 「呢類 injury claim fraud pattern 有邊啲，呢宗 match 嗎？」
- 「Provider A billing pattern 對比 peers 有冇 outlier？」

**為咩需要 KG**：entity network analysis（collusion detection），pattern matching
**Production 例子**：Shift Technology、FRISS、carriers 內部

---

### UC22 - Operational Decision Support（IPA Platform 核心）

**真實 query**（前文 RICOH freight invoice 例子）：
- 「呢張 invoice 點解超預算？同 contract align 嗎？類似 past dispute 嗎？可以 approve 嗎？」
- 「Incident root cause 同過去類似 incident 嘅 resolution 點？」

**為咩需要 GraphRAG + KG**：cross-silo entity reasoning，temporal precision，analogical retrieval，action authorization
**Production 例子**：Palantir AIP 最接近；Microsoft Fabric IQ + Copilot Studio 緊跟；多數 custom build

---

### UC23 - Insider Threat / HR Risk Analysis

**真實 query**：
- 「High-risk employee 嘅 data access + email + travel pattern 有冇異常？」
- 「Mass resignation cluster — 邊個 team / manager anomaly？」
- 「Harassment investigation — 涉事人 reporting line + collaboration history？」

**為咩需要 KG**：People-People-Event-Asset multi-modal graph，cross-source synthesis
**Production 例子**：Microsoft Insider Risk Management、Code42、Cyberhaven

---

### UC24 - M&A Due Diligence

**真實 query**：
- 「Target customer concentration 同 acquirer customer 重疊？」
- 「Management team 之前 involve 過 dispute / litigation？」
- 「Target IP portfolio vs existing patents 嘅 overlap？」

**為咩需要 KG**：跨 company entity disambiguation，multi-source synthesis，relationship discovery
**Production 例子**：Diligent、AlphaSense Enterprise Intelligence、PitchBook

---

### UC25 - Engineering Asset / Equipment Knowledge

**真實 query**（manufacturing / utilities）：
- 「呢台 turbine maintenance history、failure pattern、same model fleet systemic issue？」
- 「Sensor reading anomaly 之前喺其他 asset 出現過？root cause？」
- 「Critical part supply chain dependency map？」

**為咩需要 KG**：Asset-Component-Sensor-Event-Maintenance network，cross-asset pattern matching
**Production 例子**：Siemens MindSphere、GE Predix、SparkCognition、AspenTech

---

## 四、典型 Enterprise Distribution

基於 industry benchmark 嘅 user query distribution：

```
~40% 場景 1 類（internal knowledge search）     → Hybrid RAG
~25% 場景 2-7 類（chatbot / support / search）  → Agentic RAG
~15% 場景 8 類（analytics / aggregation）      → Text-to-SQL
~10% 場景 3/6 類（compliance / decision）       → Full stack
~10% 其他
```

**Implications**：
- 80% use case 用 Hybrid RAG + Agentic RAG 就解決
- GraphRAG / KG 主要 serve 10-15% 高價值 use case
- 唔需要 Day 1 就 build full stack
- 但需要 architecture 預留 extension point

---

## 五、能力對比 Quick Reference

```
你嘅問題                              | 主要技術選擇
────────────────────────────────────┼────────────────────────────────────
搵單一文件入面嘅 fact                  | Hybrid RAG
跨文件 synthesis                      | Agentic RAG
Multi-hop entity reasoning            | GraphRAG
Theme-level / global sensemaking      | GraphRAG (MS-style)
Cross-source orchestration            | Agentic RAG
Temporal precision required           | Bitemporal KG (Zep/Graphiti)
Customer 360 / relationship reasoning | KG + GraphRAG
Compliance / audit                    | Agentic + GraphRAG + Bitemporal
Personal conversational memory        | Agent Memory (MIRIX/Letta)
Aggregation / numerical computation   | Text-to-SQL (NOT RAG)
Action / decision support             | Agentic + 全部 + Policy Engine
Document generation                   | Hybrid RAG + templates
```

---

## 六、對 IPA Platform 嘅具體 distribution（推測）

Based on 對 RAPO use case 嘅理解：

**屬於 Hybrid RAG + Agentic RAG（~60-70% daily query volume）**：
- HR policy queries
- IT support knowledge
- Internal SOP lookup
- Vendor / procurement reference
- Engineering documentation
- Onboarding content

**屬於 GraphRAG + KG（~15-20% daily query volume，但 business value 佔 60-70%）**：
- Operational decision support（freight invoice 場景）
- Incident root cause analysis
- Cross-functional approval workflow
- Supply chain risk
- Vendor relationship analysis

**屬於 Text-to-SQL / 其他（~15%）**：
- Financial analytics
- KPI trending
- Aggregation queries

---

## 七、建議下一步 - Use Case Discovery

唔好再 design 架構前，建議先做：

1. 同 RAPO stakeholder 收集 20-30 條真實 user query
2. 逐條 classify 屬邊個 UC
3. 算 distribution
4. 根據 distribution 揀技術組合

**Timeline**：1-2 週可以做完 use case discovery，但會徹底改變 architecture 決策

---

*整理自 2026-04 系列討論*
