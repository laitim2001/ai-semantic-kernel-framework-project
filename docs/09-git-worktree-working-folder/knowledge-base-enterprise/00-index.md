# AI 記憶與知識庫研究文件集 — 總覽

**作者**：Chris Lai（RAPO / IPA Platform Architect）
**整理自**：2026-04 系列深度討論
**目的**：為 IPA Platform 嘅記憶同知識系統設計提供完整參考

---

## 文件結構

```
00 - Index（本文件）

01 - 基礎概念篇
      三大技術嘅邊界：Agent Memory / RAG / GraphRAG 分別係乜，唔應該混為一談

02 - Agent Memory 深入研究
      最新 paper、系統對比（MemGPT/Letta、Mem0、MIRIX、Zep、A-MEM、HippoRAG）
      Anthropic Context Engineering 工程實踐

03 - RAG / GraphRAG 深入研究
      RAG 演進階梯、GraphRAG 家族對比、Reasoning RAG、Multimodal RAG
      Benchmark 同評估方法學

04 - 企業場景分析
      能力對比矩陣
      25 個真實 enterprise use case，分類屬 Hybrid RAG 或需要 GraphRAG
      決策框架：點判斷你嘅 query 屬邊類

05 - 端到端架構設計
      Cross-department query 嘅 6-layer 架構
      逐 layer 嘅 Build 難度分析
      真實 complexity assessment

06 - Ontology 專題
      Build vs Buy 完整分析
      4 條自建路線對比
      Graphiti-First 推薦路線深入

07 - Ingestion 工程手冊
      由 raw data 去 queryable KG 嘅 5-stage pipeline
      多格式 document 處理（PDF / Word / PPT / Excel / 圖表）
      持續更新機制（real-time / batch / CDC）

08 - 對 IPA Platform 嘅建議總結
      Gap analysis 對照 V8 現狀
      階段性 roadmap
      Critical success factors
```

---

## 閱讀順序建議

### 如果你係技術決策者：
→ 01 → 04 → 08（快速掌握邊界、場景、建議）

### 如果你係架構師：
→ 01 → 02 → 03 → 04 → 05（理論 + 系統 + 場景 + 架構）

### 如果你準備實作：
→ 05 → 06 → 07（架構 + ontology + ingestion）

### 如果你要同 stakeholder 溝通：
→ 01 → 04 → 08（概念清晰、場景具體、建議 actionable）

---

## 關鍵 insight 速覽

以下係整個研究最重要嘅幾個洞察：

1. **三個技術唔係替代關係**
   - Agent Memory、RAG、GraphRAG 解決唔同問題
   - Agentic RAG vs GraphRAG 係正交（orthogonal）關係，可以組合

2. **「Retrieval Pipeline」→「Knowledge Runtime」範式轉移**
   - 2026 年 enterprise SOTA 唔係更勁嘅 RAG
   - 而係將 retrieval 降格成 multi-capability orchestration 嘅其中一層

3. **最大 missing piece 係 Ontology，唔係 retrieval 算法**
   - Cross-silo entity resolution 冇得 skip
   - Graphiti 一個 framework 可以同時搞掂 ontology + memory + bitemporal

4. **80/20 分佈**
   - 80% enterprise query 用 Hybrid RAG + Agentic RAG 已夠
   - 20% 高價值 query 需要 GraphRAG + KG + Bitemporal

5. **真正風險唔係技術，係 organizational alignment**
   - Cross-department entity definition alignment
   - SAP / ERP integration approval cycle
   - Policy authoring stakeholder buy-in

---

## 文件版本

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-04-17 | Initial compilation from discussion series |

---

**相關 reference**：
- 所有引用 paper 同系統喺 Doc 02 / Doc 03 嘅 reference list
- 所有 code sample 喺 Doc 07
- 所有 architecture diagram 描述喺 Doc 05
