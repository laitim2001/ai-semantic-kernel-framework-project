# 02 - Agent Memory 深入研究

**範圍**：LLM agent memory 嘅理論基礎、最新 paper、主流系統對比、工程實踐

---

## 一、理論框架

### 1.1 POMDP-style Write-Manage-Read Loop

2026 年出現嘅重要 survey《Memory for Autonomous LLM Agents: Mechanisms》（arXiv:2603.07670）提出統一 formalism：

**將 agent memory 形式化為 write–manage–read loop，嵌入 POMDP 式 agent cycle**

Debug 三問：當 agent 答錯，係:
- Retrieval 錯（wrong records surfaced）？
- Write path 漏（relevant info never stored）？
- Compression 丟失（detail lost during summarization）？
- 定係 Reasoning over correct records 出問題？

### 1.2 認知科學啟發嘅記憶分類

主流系統（尤其 MIRIX）採用嘅分類方案源自 Atkinson-Shiffrin 人類記憶模型同 Tulving episodic/semantic 區分：

| 記憶類型 | 用途 | 典型實作 |
|---------|------|---------|
| **Core Memory** | 高優先、always in-context（persona + human profile）| MemGPT/Letta core blocks |
| **Episodic Memory** | 時間戳事件、對話片段 | Zep episode subgraph、MIRIX episodic |
| **Semantic Memory** | 事實、概念、實體關係 | Zep semantic subgraph、Mem0 graph memory |
| **Procedural Memory** | 技能、workflow、操作步驟 | MIRIX procedural、A-MEM notes |
| **Working / Short-term** | 當前 task scratchpad | HiAgent hierarchical working memory |
| **Resource Memory** | 外部檔案、大型 artifacts | MIRIX resource vault、Claude Code /memories |
| **Knowledge Vault** | 結構化長期知識、多模態資料 | MIRIX Knowledge Vault |

**6-component model（MIRIX 提出）係目前 SOTA，建議 borrow 做 memory schema 基礎**

### 1.3 記憶演化三階段模型

2026 年《From Storage to Experience》survey 提出：

- **Storage 階段**（trajectory preservation）：原始 append-only log
- **Reflection 階段**（trajectory refinement）：periodic summarization、self-critique
- **Experience 階段**（trajectory abstraction）：skill compilation、lesson extraction

真正 long-horizon agent 嘅突破口喺 Experience 階段（對應 MemRL、MemEvolve 等方向）。

---

## 二、主流系統對比

| 系統 | Paradigm | 儲存層 | 檢索策略 | LongMemEval 成績 | 適用場景 |
|------|---------|-------|---------|-----------------|---------|
| **MemGPT / Letta** | LLM-as-OS，3-tier（core / recall / archival）| PostgreSQL + pgvector | Agent self-editing via tool calls | 未公布 | Full agent runtime |
| **Mem0** | Memory-as-layer，passive extraction | Vector (+ optional Kuzu/Neo4j graph) | Hybrid vector + graph | Mem0 49.0%／Mem0g 68.4% | Bolt-on personalization |
| **Zep (Graphiti)** | Bitemporal knowledge graph | Neo4j | Hybrid cosine + BM25 + BFS + reranker | +18.5%, −90% latency | Enterprise temporal reasoning |
| **A-MEM** | Zettelkasten agentic memory | Vector + LLM-generated links | Embedding + LLM link generation + evolution | Strong on multi-hop | 研究 / 自主 agent |
| **MIRIX** | Multi-agent + 6 memory types | Hybrid per type | Active Retrieval（topic-first）| 85.38%（SOTA）| Multimodal + personal assistant |
| **HippoRAG 2** | Neurobiological（hippocampal indexing）| LLM-constructed KG | Personalized PageRank | +7% associative memory | Continual learning |
| **MemOS** | OS-level memory abstraction | Multi-tier | OS-style paging | — | Long-horizon agent |
| **OMEGA** | MCP-based persistent memory | File + embeddings | Multi-strategy | **95.4%（#1）**| Coding agents |

---

### 2.1 Letta (MemGPT) — 最值得借鑒嘅 paradigm

**核心 metaphor**：LLM 當 operating system，用 virtual memory

- **Core Memory**（RAM）：agent 直接讀寫嘅 context-resident blocks
- **Recall Memory**（disk cache）：搜尋歷史對話
- **Archival Memory**（cold storage）：long-term tool-callable storage

**自編輯機制**：agent 自己決定乜嘢值得記，通過 tool call 寫入 memory

**Trade-off**：
- Predictability 較低（model 判斷有誤就記唔到）
- 但靈活性遠勝 passive extraction

Reference: arXiv:2310.08560 (MemGPT), https://github.com/letta-ai/letta

---

### 2.2 A-MEM — NeurIPS 2025 新銳

**創新點**：Memory Evolution

新 memory 加入時，唔止建新 node，仲會 **retroactively 更新舊 notes 嘅 contextual description、keywords、tags**。對應人類 associative memory 嘅 refinement behavior。

**Zettelkasten 式 LLM-generated links** 係 game-changer — 由 embedding similarity + LLM reasoning 共同決定邊兩個 memory unit 應該 connect，遠勝純 cosine similarity。

Reference: arXiv:2502.12110

---

### 2.3 MIRIX — 目前最完整 multi-agent memory

**兩個關鍵設計**：

1. **Active Retrieval**
   - Agent 喺 input 時先 generate current topic（類似 HyDE query expansion）
   - 用呢個 topic 做 retrieval key
   - 解決「user 問『Twitter CEO 係邊個』時 agent 唔會諗起之前 save 過嘅 memory」嘅經典問題

2. **六種 memory 各自獨立 store + coordinator agent**
   - 寫入時 router 分派去對應 store
   - Retrieval 時 coordinator orchestrate 跨 memory 類型嘅檢索

**Benchmark**：LOCOMO 85.38% accuracy、較 best baseline +8%、storage 較 long-context baseline 少 93.3%

Reference: arXiv:2507.07957

---

### 2.4 Zep / Graphiti — Bitemporal 係 enterprise 殺手鐧

解決兩個 time dimension：
- **Event time (T)**：fact 喺現實世界幾時為真
- **Ingestion time (T')**：agent 幾時學到呢個 fact

**對 enterprise 場景嘅價值**：
- 內部 policy 版本控制
- Audit / compliance requirement
- 「我 2026-01-05 嗰陣知道嘅 policy vs 今日 policy」

**Graphiti 實作**：
- Episode subgraph（非失真原始數據）
- Semantic entity subgraph（抽取 entity + relation）
- Community subgraph（類似 GraphRAG Leiden community）
- 三層 hybrid search：cosine + BM25 + BFS + cross-encoder rerank

Reference: arXiv:2501.13956, https://github.com/getzep/graphiti

---

## 三、Anthropic Context Engineering — 工程實踐

Anthropic 2025-09 發布嘅《Effective context engineering for AI agents》同 Claude Code memory system 值得直接 align。

**核心原則**：

1. **Context rot 係真實現象**：token 越多，recall 越差
2. **Just-in-time retrieval**：維持 lightweight identifiers，agent runtime 先 load
3. **Compaction**：近 context limit 時 LLM 自己 summarize 歷史
4. **Tool result clearing**：最低成本 compaction — 清走舊 tool call 嘅 raw result
5. **CLAUDE.md 分層**（Enterprise / Project / User / Session）

**Benchmark 數字**：100-turn web search，context editing 令 agent 完成原本會 exhaust 嘅 workflow，token 減 84%

References：
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool

---

## 四、新興研究方向（2025 Q4 – 2026 Q1）

| 論文 | 關鍵 idea |
|------|----------|
| **Memory as Action** (arXiv 2025/11) | 將 context curation 當 RL action |
| **MemSearcher** (arXiv 2025/11) | End-to-end RL 訓練 agent reason/search/manage memory |
| **Agentic Context Engineering** (arXiv 2025/11) | Evolving contexts for self-improving LLMs |
| **MAGMA** (arXiv 2026/01) | Multi-graph agentic memory |
| **EverMemOS** (arXiv 2026/01) | Self-organizing memory OS |
| **Memoria** (arXiv 2025/12) | Scalable agentic memory for personalized chatbots |
| **MemRL** (arXiv 2026/01) | Self-evolving agents via runtime RL on episodic memory |
| **Hindsight is 20/20** (arXiv 2025/12) | Dynamic procedural memory |

Repo tracking:
- https://github.com/Shichun-Liu/Agent-Memory-Paper-List
- https://github.com/TeleAI-UAGI/Awesome-Agent-Memory

---

## 五、Memory 選型決策樹

```
你需要 memory 做咩？

├── 跨 session 記得 user preference（personalization）
│   └── Mem0 或 Letta core memory block
│
├── 長 horizon agent task 嘅 state persistence
│   └── Letta archival memory 或 Claude Agent SDK memory tool
│
├── Multi-session conversation 裏面嘅 fact evolution
│   └── Zep / Graphiti（bitemporal 天然支援）
│
├── Enterprise compliance / audit trail
│   └── Zep / Graphiti（bitemporal + immutable audit）
│
├── 個人 assistant with 多模態 input
│   └── MIRIX（6-component schema）
│
├── Research / experimental agentic behavior
│   └── A-MEM（Zettelkasten + evolution）
│
└── Coding agent memory across sessions
    └── OMEGA 或 Claude Agent SDK memory tool + file-based
```

---

## 六、必讀 Paper 清單

### 開山之作
1. **arXiv:2310.08560** — MemGPT：LLM-as-OS paradigm
2. **arXiv:2404.13501** — 首個 Agent Memory Survey (ACM TOIS)

### 2025 核心
3. **arXiv:2502.12110** — A-MEM（NeurIPS 2025）
4. **arXiv:2501.13956** — Zep / Graphiti
5. **arXiv:2504.19413** — Mem0（ECAI 2025）
6. **arXiv:2507.07957** — MIRIX
7. **arXiv:2507.05257** — Incremental Multi-Turn Memory Evaluation

### 2026 最新
8. **arXiv:2603.07670** — Memory for Autonomous LLM Agents（綜合 survey）
9. **arXiv:2601.01885** — Memory in the Age of AI Agents
10. **Preprints 202601.0618** — From Storage to Experience（演化論）

---

## 七、實作 benchmark

必須 benchmark 自己 memory system 嘅方法：

| Benchmark | 測試乜嘢 | 規模 |
|-----------|---------|------|
| **LongMemEval** | 長期對話 memory，6 種 question types | ~115K tokens/conversation, 500 pairs |
| **LoCoMo** | Long conversational memory | 10 long conversations |
| **MemBench** (arXiv:2506.21605) | 綜合 memory evaluation | 多維度 |
| **MemoryArena** (He et al., 2026) | Agentic benchmark coupling memory + action | 2026 新 |

**評估維度**（Mem0 benchmark 框架）：
1. **LLM Score**：binary correctness via LLM judge
2. **Token Consumption**：total tokens to final answer
3. **Latency**：wall-clock p50/p95
4. **Storage cost**：memory footprint

三個軸必須一齊睇 — 高 accuracy 但每 query 26K tokens 唔係 production-viable。

---

## 八、對 IPA Platform 嘅直接 implication

你目前 V8 有 mem0 三層記憶（C 類 maturity L3）。升級方向：

**短期（1-2 月）**：
- Active Retrieval pattern（MIRIX-style topic-first）
- 加 org_scope / tenant dimension

**中期（3-6 月）**：
- 升級成 6-component schema
- 考慮 Graphiti 整合（同時解決 bitemporal + KG + memory 三個問題）

**長期（6-12 月）**：
- Memory evolution + reflection loop（A-MEM pattern）
- Procedural memory / skill compilation

---

## Bottom Line

Memory 係 agent 嘅 「跨時空 continuity」。選型關鍵：

1. **唔好 over-engineer**：個人 chatbot 用 Mem0；coding agent 用 Claude memory tool
2. **Enterprise 場景 Zep/Graphiti 最 production-ready**：bitemporal 天然 fit audit requirement
3. **研究前沿關注 A-MEM / MemRL**：但 production 投資要謹慎
4. **Anthropic 嘅 context engineering 原則對所有 agent 都啱**：compaction + tool clearing + just-in-time retrieval

---

*整理自 2026-04 系列討論*
