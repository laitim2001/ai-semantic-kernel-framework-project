# 01 - 基礎概念篇：Agent Memory vs RAG vs GraphRAG

**核心目的**：釐清三個經常被混淆嘅技術嘅真實能力邊界

---

## 一、三個技術嘅關係圖

```
┌──────────────────────────────────────────────────────────────────┐
│  Naive RAG / Hybrid RAG                                          │
│  「俾我相關 chunks，我用 LLM 生成答案」                              │
└──────────────────────────────────────────────────────────────────┘
                           ↓ 加入 LLM 自主決策
┌──────────────────────────────────────────────────────────────────┐
│  Agentic RAG                                                     │
│  「LLM 自己決定 retrieve 乜嘢、retrieve 幾多次、用咩 source」         │
└──────────────────────────────────────────────────────────────────┘

         ↑ 並列關係，唔係延伸 ↑

┌──────────────────────────────────────────────────────────────────┐
│  Knowledge Graph                                                 │
│  「結構化儲存 entities + relationships」（純儲存層）                 │
└──────────────────────────────────────────────────────────────────┘
                           ↓ 用 KG 做 retrieval
┌──────────────────────────────────────────────────────────────────┐
│  GraphRAG                                                        │
│  「用 KG 結構嚟 retrieve content（取代或補充 vector similarity）」   │
└──────────────────────────────────────────────────────────────────┘

         ↑ 正交關係，可以組合 ↑

┌──────────────────────────────────────────────────────────────────┐
│  Agent Memory                                                    │
│  「Agent 跨 session 嘅記憶能力」（OS-like memory management）      │
└──────────────────────────────────────────────────────────────────┘
```

**關鍵釐清**：
- Agentic RAG 同 GraphRAG **唔係替代關係，係正交**
- 一個系統可以同時係 「Agentic + Vector」、「Agentic + Graph」、「非 Agentic + Graph」
- KG 本身唔係 retrieval 方法，佢係 storage paradigm；GraphRAG 先係 retrieval method
- Agent Memory 係另一個維度，處理 agent state / user context 跨 session 嘅 persistence

---

## 二、每個技術嘅真實能力

### A. Naive RAG / Hybrid RAG

**實際做緊咩**：

```
User query → Embedding → Vector DB top-K 搜尋 → 
Concatenate chunks → LLM 生成答案
```

Hybrid 通常加入：
- BM25 keyword search
- Cross-encoder reranker（Cohere Rerank、BGE-reranker）
- Metadata filtering

**能做到**：
- ✅ 「呢份 50 頁文件講過 X 嗎？」
- ✅ 「我哋 leave policy 寫嘅 maternity leave 幾耐？」
- ✅ Single-document fact lookup
- ✅ Definition queries
- ✅ FAQ-style Q&A

**做唔到**：
- ❌ Multi-hop reasoning（「搵一個曾 review X policy 而家喺 Y team 嘅人」）
- ❌ Aggregation（「過去 6 個月 RICOH invoice 平均係幾多」）
- ❌ Temporal reasoning（「2024 Q1 我哋 policy 係點」）
- ❌ Cross-document comparison
- ❌ Causal reasoning
- ❌ 跨 silo 推理（document + structured data）

---

### B. Agentic RAG

**實際做緊咩**：

```
User query → Agent (LLM) decides:
   "我需要 retrieve 咩？"
   "從邊個 source？"
   "呢次結果夠唔夠？要唔要再 retrieve？"
→ Tool call (retrieve / compute / external API)
→ Loop until satisfied
→ 生成答案
```

**核心 difference**：retrieval 變咗 agent decision，唔係 fixed pipeline step

**比 naive RAG 多嘅能力**：
- ✅ Multi-step retrieval（先搵 X，根據結果搵 Y）
- ✅ Source routing
- ✅ Self-correction
- ✅ Hybrid tool use（retrieve + compute + external API）
- ✅ Query reformulation

**仍然嘅限制**：
- ❌ **依然受 retrieval source 嘅本質限制** — Agentic 唔等於 retrieval 質素變好，而係 strategy 變靈活
- ❌ 多倍 latency 同 cost
- ❌ Agent decision 自己會出錯
- ❌ 處理唔到結構化 aggregation

---

### C. Knowledge Graph（純 KG，作為 storage）

**實際做緊咩**：

```
(Tom: Employee) --[REPORTS_TO]--> (Sarah: Manager)
(Tom: Employee) --[APPROVED]--> (Invoice: INV-001)
(Invoice: INV-001) --[ISSUED_BY]--> (RICOH: Vendor)
(RICOH: Vendor) --[HAS_CONTRACT]--> (C2024-117: Contract)
```

**KG 本身能力**（冇 LLM 參與）：
- ✅ 精確 multi-hop traversal
- ✅ 結構化 query（Cypher / SPARQL）
- ✅ Relationship reasoning
- ✅ 數據一致性（schema enforcement）

**限制**：
- ❌ 唔識處理 unstructured text 內容
- ❌ 建構成本高（schema + ingestion + entity resolution）
- ❌ 自然語言 query 需要轉 Cypher
- ❌ 唔識 semantic similarity

---

### D. GraphRAG

**實際做緊咩**：用 KG 結構做 retrieval，有多個 variant：

- **Microsoft GraphRAG**：Documents → LLM 抽 entities → KG → communities → query 時 traverse
- **HippoRAG**：Documents → KG → query 時用 Personalized PageRank
- **LightRAG**：Documents → KG（entity + keywords）→ dual-level retrieval

**比純 vector RAG 多嘅能力**：
- ✅ Multi-hop reasoning（graph traversal）
- ✅ Theme-level / global questions
- ✅ Cross-document entity reasoning
- ✅ Better citation + explainability

**限制**：
- ❌ Build cost 極高（LLM extraction per document）
- ❌ Update cost 高
- ❌ 冇預先定義 entity / relationship type 嘅話，extraction quality 差
- ❌ Entity ambiguity 問題
- ❌ 處理唔到 structured operational data

---

### E. Agent Memory（作為第三個維度）

**實際做緊咩**：跨 session / conversation 持久儲存 agent 嘅 state 同 user context

**分類**（Atkinson-Shiffrin + Tulving 認知模型衍生）：
- **Core Memory**：always in-context（persona + user profile）
- **Episodic**：時間戳事件、對話片段
- **Semantic**：抽象 fact、概念
- **Procedural**：成功 workflow、skill
- **Resource**：外部文件、artifacts
- **Working**：當前 task scratchpad

**代表系統**：
- MemGPT / Letta：LLM-as-OS，tiered memory
- Mem0：bolt-on memory layer
- MIRIX：6-component multi-agent memory
- Zep / Graphiti：bitemporal knowledge graph
- A-MEM：Zettelkasten-style agentic memory

---

## 三、能力對比矩陣

```
能力維度                          | Vector | Hybrid | Agentic | Pure KG | GraphRAG | Agent
                                 |  RAG   |  RAG   |   RAG   |        |          | Memory
─────────────────────────────────┼────────┼────────┼─────────┼────────┼──────────┼────────
Single-fact lookup               |   ✅    |   ✅✅   |   ✅     |   ⚠️    |   ✅      |   ❌
Multi-document synthesis         |   ⚠️    |   ⚠️    |   ✅     |   ❌    |   ✅✅    |   ❌
Multi-hop reasoning              |   ❌    |   ❌    |   ⚠️    |   ✅✅   |   ✅✅    |   ❌
Aggregation queries              |   ❌    |   ❌    |   ❌     |   ✅✅   |   ⚠️     |   ❌
Temporal reasoning               |   ❌    |   ❌    |   ❌     |   ⚠️    |   ⚠️     |   ✅✅
Causal reasoning                 |   ❌    |   ❌    |   ⚠️    |   ❌    |   ⚠️     |   ⚠️
Theme / global understanding     |   ❌    |   ❌    |   ⚠️    |   ❌    |   ✅✅    |   ❌
Cross-source synthesis           |   ❌    |   ❌    |   ✅     |   ⚠️    |   ⚠️     |   ⚠️
Structured operational data      |   ❌    |   ❌    |   ⚠️*   |   ✅✅   |   ❌     |   ❌
Self-correction                  |   ❌    |   ❌    |   ✅     |   ❌    |   ❌     |   ❌
Cross-session personalization    |   ❌    |   ❌    |   ⚠️    |   ❌    |   ❌     |   ✅✅
Citation / provenance            |   ✅    |   ✅    |   ✅     |   ✅✅   |   ✅✅    |   ⚠️
Build cost                       |   $    |   $$    |   $$     |   $$$$  |   $$$$   |   $$$
Query cost                       |   $    |   $     |   $$     |   $     |   $$     |   $$
Update cost                      |   $    |   $     |   $$     |   $$$   |   $$$    |   $$
Latency                          |   Low  |   Low   |   High   |   Low   |   Med    |   Low
```

(* Agentic RAG + structured tools 可以間接處理，但唔係 native)

---

## 四、常見誤解

### 誤解 1：「GraphRAG 係 RAG 嘅升級版」
**真相**：GraphRAG 係 RAG 嘅 variant，適用場景唔同。GraphRAG 對 single-fact lookup 冇優勢，甚至更慢更貴。

### 誤解 2：「Agentic RAG 比 Hybrid RAG 好」
**真相**：Agentic 係 「決策靈活性」嘅升級，唔係 「retrieval quality」嘅升級。Simple query 用 Agentic 係 over-engineering。

### 誤解 3：「有咗 KG 就唔需要 RAG」
**真相**：KG 負責 structured relationships，RAG 負責 unstructured content。兩個 storage paradigm 服務唔同 query type，通常需要共存。

### 誤解 4：「Agent Memory 等於 RAG」
**真相**：Memory 跨 session persist user context，RAG 係 query-time retrieve knowledge。一個係 stateful，一個係 stateless。

### 誤解 5：「LLM context window 夠大就唔需要 RAG / Memory」
**真相**：Context rot 真實存在 —「needle in a haystack」style benchmark 證實 context 越長 recall 越差。Memory + RAG 係 signal-to-noise 嘅管理工具。

---

## 五、判斷用邊個技術嘅 5 條問題

| 問題 | 答 Yes 偏向 | 答 No 偏向 |
|------|-----------|-----------|
| 答案可以喺 1-2 份文件揾到？ | Hybrid RAG | GraphRAG |
| 需要追蹤「fact 喺幾時為真」？ | GraphRAG (bitemporal) | Hybrid RAG |
| 需要 reason 跨多個 entity 嘅 relationship？ | GraphRAG | Hybrid RAG |
| Failure cost 高（regulatory / safety / financial）？ | GraphRAG | Hybrid RAG |
| Single query 需要 combine 5+ source？ | GraphRAG + Agentic | Hybrid RAG |
| 跨 session 要記得用戶偏好？ | Agent Memory | 唔需要 |
| Query 本質係 computation / aggregation？ | Text-to-SQL | RAG 都唔合適 |

**3+ Yes** 在 GraphRAG 相關 → 認真考慮 GraphRAG 投資
**2 Yes** → Hybrid RAG + selective GraphRAG component
**0-1 Yes** → Hybrid RAG 已經夠

---

## 六、行業 consensus（2026 年）

基於過去 18 個月 industry 動態：

1. **「RAG is dead」嘅說法唔準確**，但 RAG 唔再係主角
2. **Hybrid approach 成為 enterprise default**：Agents orchestrate retrieval；RAG 提供 grounding
3. **Knowledge Runtime paradigm 取代 Retrieval Pipeline**：Palantir / Microsoft / Glean 都收斂到呢個方向
4. **Ontology 由 nice-to-have 變 mandatory**：Microsoft Fabric IQ Ontology 嘅推出係最大 signal
5. **Bitemporal KG 成為 compliance scene 嘅 de facto standard**

---

## 下一步

- 想深入每個技術 → 睇 Doc 02（Memory）同 Doc 03（RAG / GraphRAG）
- 想睇真實 use case → 睇 Doc 04
- 想睇架構設計 → 睇 Doc 05

---

*整理自 2026-04 系列討論*
