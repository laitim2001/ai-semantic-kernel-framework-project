# 03 - RAG / GraphRAG 深入研究

**範圍**：RAG 演進階梯、GraphRAG 家族、Reasoning RAG、Multimodal RAG、Benchmark

---

## 一、RAG 演進階梯

```
Naive RAG (一 shot retrieve → generate)
   ↓
Advanced RAG (query rewrite、re-rank、chunk optimization)
   ↓
Modular RAG (pipeline orchestration、HyDE、Self-RAG)
   ↓
Agentic RAG (agent loop，reflection + planning + tool use)
   ↓
Reasoning RAG (System 2，iterative search-reason interleaving)
```

### 必讀 Survey

1. **arXiv:2501.09136** — *Agentic RAG: A Survey on Agentic RAG* (Singh et al., v4 updated 2026/04)
2. **arXiv:2507.09477** — *Towards Agentic RAG with Deep Reasoning*
3. **AACL 2025 Findings** — *Reasoning RAG via System 1 or System 2*
4. **arXiv:2501.00309** — *Retrieval-Augmented Generation with Graphs (GraphRAG Survey)*

---

## 二、GraphRAG 家族詳細對比

| 系統 | 索引方式 | 檢索策略 | Token cost | 優勢 | 劣勢 |
|------|---------|---------|-----------|------|------|
| **MS GraphRAG** | LLM 抽 entity + Leiden community，pregenerate community summaries | Global: community summary map-reduce；Local: entity traversal | 極高（610k+ tokens per run）| Global sensemaking 最強 | 成本高、update 慢 |
| **LightRAG** (EMNLP 2025) | Entity + relation 抽取，dual-level keywords | Dual-level（low-level entity + high-level theme）| <100 tokens/query | 極快，incremental update 好 | Community-level sensemaking 較弱 |
| **HippoRAG / HippoRAG 2** | Schemaless KG + Personalized PageRank | PPR-based single-step multi-hop | 低 | Multi-hop QA +20%，10-30x cheaper than IRCoT | 需 good NER；scale issue |
| **PathRAG** | 識別 key relation paths | Path-based retrieval | 中 | 減少 redundancy | 複雜 path queries |
| **GeAR** | Graph expansion over BM25 base | Agent-driven graph expansion | 中高 | Multi-hop 強 | Agent overhead |
| **Practical GraphRAG** (arXiv:2507.03226) | Dependency parsing（非 LLM）構 KG | Hybrid vector + graph via RRF | 極低 | 94% of LLM-based performance at fraction of cost | Parser 依賴語言 |

### 實戰建議

- **SCM document、vendor relationships、org chart** → LightRAG (dual-level keyword indexing + incremental update)
- **Multi-hop reasoning（complex policy query）** → HippoRAG 2 + PPR
- **Theme-level global sensemaking** → MS GraphRAG（如果 budget 允許）
- **Audit / compliance 重** → Graphiti + bitemporal

References:
- arXiv:2404.16130 (MS GraphRAG)
- arXiv:2410.05779 (LightRAG, EMNLP 2025)
- arXiv:2405.14831 (HippoRAG), arXiv:2502.14802 (HippoRAG 2 / ICML 2025)
- https://github.com/DEEP-PolyU/Awesome-GraphRAG

---

## 三、Reasoning RAG — 2025 最大突破方向

### 3.1 System 1 vs System 2 Paradigm

**Predefined reasoning（System 1）**：固定 pipeline、heuristic-based，快但缺適應性
**Agentic reasoning（System 2）**：LLM 主動 planning、evaluating、adapting，慢但靈活

Production 通常 mix — 簡單 query 直接 System 1，complex 觸發 System 2

Reference: Liang et al., *Reasoning RAG via System 1 or System 2*, AACL 2025 Findings

### 3.2 RL for Retrieval — 2025 下半年突破

呢個方向唔係 prompt engineering 層面，而係 fine-tune 層：

- **Search-R1**：end-to-end RL 訓練 LLM interleave search + reasoning，用 PPO/GRPO + retrieved token masking
- **R1-Searcher**：two-stage outcome-based RL
- **ReZero (Retry-Zero)**：incentivize persistence，模型識得「retry with different query」
- **ReasonRAG**：process-supervised RL with RAG-ProGuide dataset

**對 enterprise 實戰**：最現實係 borrow reasoning pattern 入 agent prompt + tool design，唔係自己 RL 訓練

### 3.3 Multi-Agent Decentralized / Centralized

- **Decentralized**：M-RAG、MDocAgent、Agentic Reasoning — 每個 agent 獨立 retrieval + reasoning，最後合併
- **Centralized**：HM-RAG、SurgRAW、Chain of Agents — 一個 coordinator 分派
- **Hierarchical**：Manager-Worker-Specialist

---

## 四、Multimodal RAG — ColPali / ColQwen

### 4.1 演進

**ColBERT → ColPali → ColQwen**：
- **ColBERT**：text-only late interaction，token-wise embedding
- **ColPali**（ICLR 2025, arXiv:2407.01449）：PaliGemma-3B + ColBERT-style late interaction，直接 embed document page image，跳過 OCR + layout detection + chunking
- **ColQwen / ColQwen2**：基於 Qwen2-VL，多語言、更好 resolution

### 4.2 核心優勢 vs 傳統 pipeline

1. 直接處理 visually-rich PDF（tables、charts、equations、multi-column）
2. Offline indexing 極快（no OCR）
3. Query 時 token-level late interaction，比 single-vector 保留更多 fine-grained signal

### 4.3 劣勢

1. Multi-vector storage 需要多幾倍空間
2. vLLM 等 serving 需要 custom modification
3. 資源密集，inference 需要 A100 or 相當

### 4.4 Document Parsing Stack（2026）

```
┌─── Layer 1: Structured Document Parser ──────────────────────┐
│   Docling / Granite-Docling / OpenDataLoader / Unstructured  │
│   → 抽取 text + tables + figures + reading order             │
└───────────────────────────────────────────────────────────────┘
                           ↓
┌─── Layer 2: Element-Specific Handlers ───────────────────────┐
│   Text chunks     → 直接入 RAG                                │
│   Tables          → Markdown / JSON                          │
│   Simple figures  → VLM caption                              │
│   Complex figures → VLM structured description               │
│   Abstract diagrams → hybrid approach                        │
└───────────────────────────────────────────────────────────────┘
                           ↓
┌─── Layer 3: Enriched Chunks ─────────────────────────────────┐
│   每個 chunk 都有 metadata header + VLM description          │
└───────────────────────────────────────────────────────────────┘
```

### Format 支援

| Format | Tool | Tables | Figures | Charts | Reading Order |
|--------|------|--------|---------|--------|---------------|
| PDF | Docling / Granite-Docling | ✅ 優 | ✅ 優 | ⚠️ Good | ✅ 優 |
| DOCX | Docling | ✅ 原生 | ✅ 原生 | ✅ 原生 | ✅ 原生 |
| PPTX | Docling | ✅ | ✅ | ⚠️ Mixed | ✅ |
| XLSX | Docling / pandas | ✅ 原生 | — | ⚠️ Limited | N/A |
| Scanned PDF | Docling + OCR | ⚠️ OK | ⚠️ OK | ❌ Weak | ⚠️ OK |
| HTML | Docling | ✅ | ✅ | ⚠️ | ✅ |

**推薦 stack**：Docling（IBM, Linux Foundation, MIT license）+ Granite-Docling VLM for 複雜視覺內容

References:
- arXiv:2407.01449 (ColPali)
- https://hf.co/vidore
- https://www.docling.ai/

---

## 五、Benchmark 方法學

### 5.1 標準 Benchmark

| Benchmark | 測試乜嘢 | 規模 |
|-----------|---------|------|
| **MuSiQue** | Multi-hop QA | 2–4 hop questions |
| **2WikiMultiHopQA** | Multi-hop over Wikipedia | 2-hop |
| **HotpotQA** | Multi-hop with supporting facts | — |
| **ViDoRe** | Visual document retrieval | Multi-domain, multi-language |
| **M-LongDoc** | Multimodal super-long document | 851 samples |

### 5.2 評估維度

1. **Retrieval accuracy**：precision@K、recall@K、MRR
2. **End-to-end correctness**：LLM-as-judge
3. **Token consumption**：per-query cost
4. **Latency**：p50 / p95
5. **Storage cost**：index size
6. **Update cost**：incremental ingestion time

---

## 六、Enterprise RAG Architecture Evolution（2026）

### 6.1 由 Pipeline 去 Runtime 嘅範式轉移

NStarX 報告指出嘅 2026-2030 趨勢：

> 「Successful enterprise deployments will treat RAG as a knowledge runtime: an orchestration layer that manages retrieval, verification, reasoning, access control, and audit trails as integrated operations.」

類比 Kubernetes：唔係單純 run container，而係管理 workload 嘅 health check、resource limits、security policies 整體 runtime。

### 6.2 四個成熟度階段

1. **Naive RAG**（2023）：retrieve → generate
2. **Hybrid RAG**（2024）：vector + BM25 + rerank
3. **Agentic RAG**（2025）：agent-controlled retrieval
4. **Knowledge Runtime**（2026）：governance + verification + audit baked in

### 6.3 Enterprise RAG 成熟度評估

報告顯示：
- 70% 嘅 RAG 系統仲缺 systematic evaluation framework
- production deployment 報告 25-40% irrelevant retrieval reduction
- 但新 failure modes 出現：retrieval loops、over-retrieval、confidence calibration 壞

---

## 七、Copyright 重要 disclaimer

**呢份文件嘅所有 paper reference 都係通過 arXiv ID 同 DOI 引用**。搜尋結果嘅內容經過 paraphrase 同 synthesis，唔係 verbatim 引用。使用者閱讀原 paper 獲得完整技術細節。

---

## 八、必讀 Paper 清單

### 核心 Survey
1. arXiv:2501.09136 — Agentic RAG Survey
2. arXiv:2507.09477 — Agentic RAG with Deep Reasoning
3. arXiv:2501.00309 — GraphRAG Survey
4. arXiv:2506.10408 — Reasoning RAG System 1/2

### GraphRAG 家族
5. arXiv:2404.16130 — MS GraphRAG
6. arXiv:2410.05779 — LightRAG
7. arXiv:2405.14831 — HippoRAG
8. arXiv:2502.14802 — HippoRAG 2 / From RAG to Memory
9. arXiv:2507.03226 — Practical GraphRAG

### Multimodal
10. arXiv:2407.01449 — ColPali
11. M-LongDoc (OpenReview 5zjsZiYEnr)

### Reasoning RAG / RL
12. Search-R1
13. R1-Searcher
14. ReasonRAG

---

## 九、GitHub Repos 清單

| Repo | 內容 |
|------|------|
| https://github.com/microsoft/graphrag | MS GraphRAG |
| https://github.com/HKUDS/LightRAG | LightRAG |
| https://github.com/OSU-NLP-Group/HippoRAG | HippoRAG / HippoRAG 2 |
| https://github.com/illuin-tech/colpali | ColPali 官方 |
| https://github.com/getzep/graphiti | Graphiti |
| https://github.com/DEEP-PolyU/Awesome-GraphRAG | Awesome GraphRAG curation |
| https://github.com/asinghcsu/AgenticRAG-Survey | Agentic RAG survey companion |
| https://github.com/HKUDS/RAG-Anything | Multimodal RAG |

---

## 十、Bottom Line

RAG / GraphRAG 選型關鍵：

1. **先問 use case**：single-fact lookup 用 Hybrid RAG；multi-hop / theme 用 GraphRAG
2. **唔好 over-engineer**：MS GraphRAG 嘅 token cost 通常勸退 production
3. **LightRAG 係 sweet spot**：性價比最高嘅 GraphRAG variant
4. **Reranker 係必須**：Cohere Rerank 3、BGE-reranker-v2-m3，零架構風險 +15-30% precision
5. **Multimodal 選 Docling**：MIT license，Linux Foundation 維護，production-ready

---

*整理自 2026-04 系列討論*
