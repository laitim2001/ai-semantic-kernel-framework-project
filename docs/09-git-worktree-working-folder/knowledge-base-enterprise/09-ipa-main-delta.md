# 09 - IPA Platform Main 現況 Delta 分析

**目的**：對照 Doc 01-08 研究架構與 IPA Platform main 分支（Phase 44 完成、Phase 45/46/47 W1 已合併）的實際代碼現況，產出三色表（可 reuse / 需擴展 / 需新建），作為後續 roadmap 決策的定錨。

**基準日期**：2026-04-19
**基準 main commit**：`69b5fa2`（後有 `179d7f8` V9 forward sync 到 Phase 47 W1）
**對照文件**：`docs/09-git-worktree-working-folder/knowledge-base-enterprise/` Doc 01-08

---

## 零、Executive Summary

### 關鍵發現

1. **L2 Orchestrator 大幅領先研究文件假設**
   - 研究文件假設「V8.1 計劃 migrate 去 ClaudeAgent」(Doc 08)
   - 實際 main 已有 **Phase 28 三層意圖路由**（pattern < 10ms / semantic < 100ms / LLM < 2s）
   - 實際 main 已有 **Phase 45 3-route dispatch**（direct_answer / subagent / team）
   - 實際 main 已有 **8-step pipeline**（memory → knowledge → intent → risk → hitl → llm_route → postprocess）
   - **架構節省 ≥ 8 週**

2. **L4 Specialist 框架已有，但 expert 定位不同**
   - Phase 46 Agent Expert Registry 已 deliver（YAML-based, 6 IT expert: network / database / application / security / cloud / general）
   - 研究文件設想的 Finance / Compliance / Analogy / Authorization 4 specialist 可**直接註冊為新 YAML expert**，不需重新設計 agent 框架
   - **架構節省 3-4 週**

3. **L3 Ontology 仍是最大缺口**（確認研究判斷）
   - Zero Graphiti / Neo4j / entity resolution / ontology
   - `correlation/graph.py` 是事件關聯，非 KG
   - 仍需 10 週投資

4. **L6 Audit 基礎 ✅，Bitemporal ❌**
   - `orchestration/audit/logger.py`（281 LOC）只係 structured JSON logging
   - 無 PostgreSQL bitemporal schema、無 immutable rules、無 PII redaction
   - 仍需 4-6 週

5. **Knowledge subsystem 超出研究文件假設**
   - Doc 08 描述 V8 只有「Azure AI Search hybrid」
   - 實際 `integrations/knowledge/` 已有完整 RAG pipeline（parser + chunker + embedder + vector_store + retriever）+ 本地 hybrid（vector + BM25-like + RRF + simple rerank）
   - 缺 Cohere Rerank 3 升級、缺 GraphRAG、缺合約 / multi-modal 特化

6. **Memory 完全符合研究假設**
   - mem0 三層（core / working / long-term via mem0 + Qdrant）
   - UnifiedMemoryManager 已 integrate

### 9-month Roadmap 可壓縮至 ~6 個月

原 Doc 08 roadmap：Q1 基建 + Q2 Specialist Wave 1 + Q3 Compliance + Analogy = 9 月
校正後：L2 / L4 框架 / Knowledge baseline 已就緒，省 12-15 週
**新預估：~6 個月可達 Doc 08 的 9-month deliverables**

---

## 一、六層架構 Delta 矩陣

### 色碼定義

| 色碼 | 意義 |
|------|------|
| 🟢 **REUSE** | main 已有，可直接使用，無需修改 |
| 🟡 **EXTEND** | main 已有基礎，需擴展 / 升級 |
| 🔴 **NEW** | main 完全缺失，需從零新建 |
| ⚪ **VALIDATE** | main 有但需驗證 production-readiness |

---

### L0 - Identity & Session Layer

| Sub-component | 狀態 | main 現況 | Gap |
|---------------|------|----------|-----|
| Azure SSO | 🟢 REUSE | `core/security/jwt.py`, `domain/auth/service.py`, `api/v1/auth/routes.py` | — |
| JWT 核心 | 🟢 REUSE | JWT utilities 齊備 | — |
| Auth migration | 🟢 REUSE | `api/v1/auth/migration.py` | — |
| OBO Token Flow | ⚪ VALIDATE | 未見明確 OBO module；需確認 PoC 狀態 | 可能仍需 3-4 週 hardening |
| Token refresh / vault | 🔴 NEW | 未見 | 1-2 週 |

**整體**：🟡 EXTEND — 基礎穩固，OBO 仍需完成

**研究文件 vs main**：Doc 08 「OBO PoC 進行中」— 目前 main 內未見明確 OBO 代碼，建議先盤點 OBO PoC 落在哪個 worktree

---

### L1 - Input Gateway

| Sub-component | 狀態 | main 現況 | Gap |
|---------------|------|----------|-----|
| InputGateway 核心 | 🟢 REUSE | `integrations/orchestration/input_gateway/gateway.py` | — |
| Schema validation | 🟢 REUSE | `schema_validator.py` | — |
| UserInput handler | 🟢 REUSE | `source_handlers/user_input_handler.py` | — |
| ServiceNow handler | 🟢 REUSE | `source_handlers/servicenow_handler.py` | — |
| Prometheus handler | 🟢 REUSE | `source_handlers/prometheus_handler.py` | — |
| Finance / Contract / Email 等 handler | 🔴 NEW | 未見 | 每個 handler 1-2 週 |
| Base handler 擴展 | 🟢 REUSE | `base_handler.py` 抽象已有 | 新 handler 可直接繼承 |

**整體**：🟢 REUSE（核心）+ 🔴 NEW（企業特定 handler）

**研究文件 vs main**：Doc 05「已完成」— 完全正確。只需為 enterprise use case 新增 source handler

---

### L2 - Orchestrator / Query Decomposition

| Sub-component | 狀態 | main 現況 | Gap |
|---------------|------|----------|-----|
| 3-tier Intent Router | 🟢 REUSE | Phase 28 complete: pattern (<10ms) + semantic (<100ms) + LLM classifier (<2s) | — |
| Completeness checker | 🟢 REUSE | `intent_router/completeness/checker.py` | — |
| Guided dialog (multi-turn) | 🟢 REUSE | `guided_dialog/engine.py` + context_manager + generator | — |
| Risk assessor | 🟢 REUSE | `risk_assessor/assessor.py` + policies | — |
| **3-route dispatch**（PoC 驗證，Phase 45） | 🟢 REUSE | `dispatch/executors/`：direct_answer / subagent / team | — |
| **8-step pipeline** | 🟢 REUSE | step1_memory → step2_knowledge → step3_intent → step4_risk → step5_hitl → step6_llm_route → step8_postprocess | — |
| HITL controller | 🟢 REUSE | `hitl/controller.py` + approval_handler + Teams notification | — |
| Active Retrieval（Doc 02 提及） | 🔴 NEW | 現 Orchestrator 未 implement active retrieval 決策模式 | 需評估是否合併入 step6_llm_route |
| Query 分解 → 4 Q pattern（Doc 05） | 🟡 EXTEND | 目前 dispatch 係 1-to-1（單 intent）；Doc 05 設想多 sub-question parallel dispatch | 需新增 decomposition step 或擴展 team executor |
| OpenTelemetry metrics | 🟢 REUSE | `orchestration/metrics.py`（893 LOC） | — |

**整體**：🟢 REUSE（核心 90%）+ 🟡 EXTEND（Query decomposition 多 sub-question 模式）

**研究文件 vs main**：**Doc 08「V8.1 計劃轉 ClaudeAgent」嚴重低估 main 現況**。Phase 28 + 45 + 46 合起來已遠超 Doc 08 所述 V8 baseline。**原計劃 6-8 週「L2 Orchestrator migration」可完全省略**

---

### L3 - Ontology / Entity Resolution Layer ⭐

| Sub-component | 狀態 | main 現況 | Gap |
|---------------|------|----------|-----|
| Graphiti / Neo4j | 🔴 NEW | Zero | 10 週 |
| Entity 解析（canonical ID） | 🔴 NEW | Zero | — |
| Bitemporal KG | 🔴 NEW | Zero | — |
| Pydantic entity/edge schema | 🔴 NEW | Zero | 1-2 週 |
| LLM-assisted schema discovery | 🔴 NEW | Zero | 1 週 |
| Entity resolution review workflow | 🔴 NEW | Zero | 2 週 |
| Graphiti MCP server | 🔴 NEW | Zero | 1 週 |
| `correlation/graph.py` | ❌ 不相關 | 多 agent 事件關聯，非 KG | 不可 reuse |

**整體**：🔴 NEW — **完全從零建構**（確認 Doc 06 判斷）

**研究文件 vs main**：Doc 06 / 08 判斷正確。**10 週投資不變**。這是整個 roadmap 的 critical path

---

### L4 - Specialist Agent Layer

| Sub-component | 狀態 | main 現況 | Gap |
|---------------|------|----------|-----|
| **Agent Expert Registry 框架**（Phase 46） | 🟢 REUSE | `orchestration/experts/registry.py`、YAML definitions 目錄 | — |
| Expert YAML schema | 🟢 REUSE | name / display_name / domain / capabilities / model / system_prompt / tools / enabled / metadata | — |
| Domain tools 解析 | 🟢 REUSE | `experts/domain_tools.py` | — |
| Tool validator | 🟢 REUSE | `experts/tool_validator.py` | — |
| Expert bridge / seeder | 🟢 REUSE | `experts/bridge.py`, `experts/seeder.py` | — |
| **現有 6 expert** | 🟢 REUSE | network / database / application / security / cloud / general | — |
| **Q1 Variance Analyzer**（Finance） | 🔴 NEW | 未註冊 | 4-6 週（含 SAP MCP + budget MCP） |
| **Q2 Compliance Checker** | 🔴 NEW | 未註冊 | 6-8 週（含 contract ingestion + reranker 升級） |
| **Q3 Analogy Finder** | 🔴 NEW | 未註冊 | 12-16 週（最難，依賴 L3 Ontology） |
| **Q4 Authorization Agent** | 🔴 NEW | 未註冊 | 4-6 週（含 OPA） |
| SAP / ERP / Budget / External-data MCP | 🔴 NEW | 未見 | 每個 1-2 週 |
| Verifier Agent（L5） | 🔴 NEW | 未見 | 2-3 週 |
| Synthesizer Agent（L5） | 🟡 EXTEND | team mode executor 有基礎 synthesis | 1-2 週 formalize |

**整體**：🟢 REUSE（框架 100%）+ 🔴 NEW（企業 specialist 全缺）

**研究文件 vs main**：**Doc 08 把 4 specialist 視為從零設計**，但 main 已有 YAML registry 框架。**新增 specialist 只係寫 YAML + 實作 tool MCP，架構層省 3-4 週**

**關鍵架構判斷**：Doc 08 的 4 specialist 應重新定位為「新 YAML expert 定義」，而非「全新 agent 框架」

---

### L5 - Verification & Synthesis

| Sub-component | 狀態 | main 現況 | Gap |
|---------------|------|----------|-----|
| Verifier Agent (Claude Opus) | 🔴 NEW | 未見 | 2-3 週 |
| Synthesizer | 🟡 EXTEND | `dispatch/executors/team.py` 有 team 模式 multi-agent synthesis | 1-2 週 formalize 為獨立 agent |
| Citation 機制 | 🟡 EXTEND | RAG retriever 返回 `RetrievalResult` 含 source 欄位；但全鏈 citation trace 未系統化 | 1-2 週 |
| Claim-level 驗證 prompt | 🔴 NEW | 未見 | 1 週 |
| Verifier token cost 控制 | 🔴 NEW | 未見 | 納入 context_budget 考量 |

**整體**：🟡 EXTEND / 🔴 NEW

**研究文件 vs main**：Doc 05 L5 Verifier 估 2-3 週、Synthesizer 1-2 週 — 基本準確，但 team executor 已有部分 synthesis 邏輯可 leverage

---

### L6 - Governance & Audit

| Sub-component | 狀態 | main 現況 | Gap |
|---------------|------|----------|-----|
| 基礎 audit logger | 🟢 REUSE | `orchestration/audit/logger.py`（281 LOC, structured JSON） | — |
| `integrations/audit/` 模組 | 🟢 REUSE | 4 files | — |
| **Bitemporal schema**（event_time + ingestion_time） | 🔴 NEW | 無 | 2-3 週 |
| PostgreSQL 持久化 + immutable rules | 🔴 NEW | 無（目前只 JSON log） | 2-3 週 |
| Audit chain（parent_event_id） | 🔴 NEW | 無 | 1 週 |
| PII redactor | 🔴 NEW | 無 | 1-2 週 |
| EU AI Act 分級 | 🔴 NEW | 無 | 1 週 |
| OPA policy engine | 🔴 NEW | 無 | 2-3 週（屬 L4-Q4） |

**整體**：🟡 EXTEND — 基礎 logger ✅，企業合規升級 ❌

**研究文件 vs main**：Doc 05 / 08 估 4-6 週基本準確。可 leverage 現有 logger 作 base，加 bitemporal persistence + immutable rules

---

## 二、Knowledge Subsystem 詳細 Delta

Doc 08 的 Knowledge 部分分散，以下是深度對照：

### `backend/src/integrations/knowledge/` 現況

| 模組 | 功能 | 實作程度 | Doc 03/07 提及升級 |
|------|------|---------|-------------------|
| `document_parser.py` | 文件解析 | ✅ 基礎 | Docling / VLM 升級（Doc 07）|
| `chunker.py` | RECURSIVE 分塊 | ✅ 基礎 | Semantic / Hierarchical / Layout-aware 策略（Doc 07）|
| `embedder.py` | EmbeddingManager | ✅ | — |
| `vector_store.py` | VectorStoreManager | ✅ | — |
| `retriever.py` | **Hybrid retrieve**（vector + BM25-like + RRF + simple rerank） | ✅ | **Cohere Rerank 3 升級（Doc 08 quick win）** |
| `rag_pipeline.py` | 端到端 pipeline | ✅ Sprint 118 Phase 38 | — |
| `agent_skills.py` | Agent knowledge tool | ✅ | Knowledge-as-Tool 模式（與 Claude SDK 整合）|

### Delta 表

| 研究文件要求 | main 現況 | 狀態 | 工作量 |
|------------|----------|------|--------|
| Hybrid RAG（vector + BM25 + rerank） | ✅ 有（simple rerank） | 🟡 EXTEND | Cohere Rerank 3 替換 = 1 週 quick win |
| Reciprocal Rank Fusion | ✅ 已 implement | 🟢 REUSE | — |
| 多格式 parser（PDF / Word / PPT / Excel） | ⚪ VALIDATE（parser 存在但深度未驗） | 可能需 Docling 升級 | 1-2 週 |
| Layout-aware chunking | 🔴 NEW | 未見 | 2 週 |
| Multimodal（表格 / 圖表 / OCR） | 🔴 NEW | 未見 | 3-4 週 |
| GraphRAG（Microsoft / HippoRAG / LightRAG） | 🔴 NEW | 未見 | 依賴 L3，12-16 週 |
| Query rewriting / HyDE | 🔴 NEW | 未見 | 1-2 週 |
| 5-stage ingestion pipeline（Doc 07） | 🟡 EXTEND | `rag_pipeline.py` 已有 ingestion/retrieval 兩路，但未達 Doc 07 完整 5-stage | 3-4 週 |
| CDC / real-time update | 🔴 NEW | 未見 | 2-3 週 |
| Contract-specific handling（clause version chain） | 🔴 NEW | 未見 | 3-4 週 |

**結論**：Knowledge subsystem 比研究文件假設成熟。**Cohere Rerank 3 係真正 1 週 quick win，建議 Week 1 executed**

---

## 三、Memory Subsystem Delta

### `backend/src/integrations/memory/` 現況

| 模組 | 功能 | 對應 Doc 02 概念 |
|------|------|----------------|
| `unified_memory.py` | UnifiedMemoryManager（三層協調） | Memory orchestrator |
| `mem0_client.py` | Mem0Client（長期記憶）| Semantic memory layer |
| `types.py` | Memory type enum | Memory taxonomy |
| `embeddings.py` | 向量化 | — |
| `consolidation.py` | 記憶整合 | Sleep/consolidation pattern (Doc 02) |
| `context_budget.py` | Context 預算管理 | Context rot 對策（Doc 02）|
| `extraction.py` | 記憶抽取 | Memory extraction（Doc 02）|

### Delta 表

| Doc 02 要求 | main 現況 | 狀態 |
|------------|----------|------|
| Core Memory（always in-context） | ✅ UnifiedMemoryManager 三層 | 🟢 REUSE |
| Working Memory | ✅ 三層之一 | 🟢 REUSE |
| Long-term Memory (mem0 + Qdrant) | ✅ 已整合 | 🟢 REUSE |
| Context budget 管理 | ✅ `context_budget.py` | 🟢 REUSE |
| Memory consolidation | ✅ `consolidation.py` | 🟢 REUSE |
| Episodic memory（event-based） | ⚪ VALIDATE | 待深查 mem0 config |
| Procedural memory（成功 workflow） | ⚪ VALIDATE | 需確認 |
| Resource memory（外部文件）| ⚪ VALIDATE | 與 Knowledge subsystem 交界 |
| Bitemporal memory（Graphiti 風格） | 🔴 NEW | 依賴 L3 |
| MIRIX-style 6-component | 🔴 NEW | 目前 3 層 |

**與 `research/memory-system-enterprise` worktree 的 interlock**：兩個 research 方向應 joint，Memory Doc 02 與 Knowledge Doc 03 同為 L3 Ontology 的 downstream consumer

---

## 四、MCP / Tools Delta

### 現有 MCP Servers（`integrations/mcp/`）
- Azure、Filesystem、LDAP、Shell、SSH（43 files）

### Doc 08 要求的 MCP Servers
| MCP Server | 用途 | 狀態 | 工作量 |
|-----------|------|------|--------|
| Graphiti MCP | Ontology search/resolve/ingest | 🔴 NEW | 1 週（L3 配套）|
| SAP MCP | ERP invoice / vendor query | 🔴 NEW | 2-3 週 |
| Budget MCP | ERP budget | 🔴 NEW | 1-2 週 |
| Contract repo MCP | 合約檢索 | 🔴 NEW | 1-2 週 |
| External data MCP（燃油指數等）| 外部 reference data | 🔴 NEW | 1 週 |
| Email MCP（MS Graph）| 郵件 / Teams 溝通 | 🔴 NEW | 1 週 |
| OPA MCP | Policy 決策 | 🔴 NEW | 1 週（L4-Q4 配套）|

**結論**：現有 MCP 框架 ✅（已證明可擴展），企業特定 MCP 全新建

---

## 五、Gap Analysis 總表

### 🟢 可直接 Reuse（總計節省 12-15 週工作）

1. L0 Azure SSO + JWT + auth routes
2. L1 InputGateway 核心 + 3 個 source handler
3. L2 三層 intent routing（Phase 28）
4. L2 guided dialog / risk assessor / HITL（Phase 28）
5. L2 3-route dispatch（Phase 45）
6. L2 8-step pipeline
7. L2 metrics（OpenTelemetry）
8. L4 Agent Expert Registry 框架（Phase 46）
9. L4 6 個現有 IT expert YAML
10. L6 基礎 audit logger
11. Knowledge hybrid retriever + RRF
12. Memory 三層 mem0 + UnifiedMemoryManager
13. MCP 框架 + 5 個現有 server

### 🟡 需 Extend（不大工作量）

1. L0 OBO token flow（確認現況後 hardening）
2. L2 Query decomposition → 多 sub-question parallel dispatch
3. L5 Synthesizer formalize（team executor 已有基礎）
4. L5 Citation trace 全鏈系統化
5. L6 Audit 升級到 bitemporal + PostgreSQL immutable
6. Knowledge 升 Cohere Rerank 3（1 週 quick win）
7. Knowledge 多格式 parser 驗證 / Docling 升級

### 🔴 需完全 New（最大投資）

1. **L3 Ontology 整層**（Graphiti + Neo4j + entity resolution + schema discovery + review workflow + MCP 配套）= **10 週 critical path**
2. **L4 企業 specialist**（Variance + Compliance + Analogy + Authorization）+ 配套 MCP = **26-36 週（可大幅 parallel）**
3. **L5 Verifier Agent**
4. **L6 Bitemporal + PII redactor + EU AI Act 分級**
5. **Knowledge 進階**：GraphRAG（依賴 L3）、Multimodal、Layout-aware、Query rewriting、CDC
6. **Contract-specific**（clause version chain）
7. **企業 MCP 群**（SAP / Budget / Contract / External / Email / OPA）

---

## 六、校正後 Roadmap 建議（6 個月版）

### Month 1：Quick Wins + Foundation

- **Week 1**: Cohere Rerank 3 替換 `_simple_rerank`（知識 quick win）
- **Week 1**: OBO 現況盤點（哪個 worktree）
- **Week 2-3**: Graphiti + Neo4j docker 部署；Pydantic entity schema（5-10 entity）
- **Week 3-4**: LLM-assisted schema discovery PoC
- **併行**: Bitemporal audit PostgreSQL schema 設計

### Month 2：Ontology + Audit

- L3 Graphiti PoC：vendor master + contract ingestion（100 episode）
- L3 Entity resolution review workflow
- L6 Bitemporal audit 上線
- Graphiti MCP server

### Month 3：第一批 Specialist YAML

- L4-Q1 Variance：新增 `variance_analyzer.yaml` + SAP MCP + Budget MCP
- L4-Q4 Authorization：新增 `authorization_agent.yaml` + OPA MCP
- L5 Verifier Agent 實作（利用 team executor 基礎）

### Month 4：第二批 + E2E Slice

- L4-Q2 Compliance：`compliance_checker.yaml` + contract ingestion 完整 pipeline
- **Freight Invoice Variance 端到端 E2E**（L0 + L3 + L4-Q1 + L4-Q4 + L5 + L6）
- Citation trace 系統化

### Month 5：Production Hardening

- Freight Invoice Variance Production GA
- Evaluation harness（每個 specialist ground truth）
- OPA policy authoring workflow

### Month 6：Q3 Analogy Start + 擴展

- L4-Q3 Analogy Finder：structured case schema + multi-strategy retrieval
- GraphRAG 探索（Microsoft GraphRAG PoC）
- 第二個 vertical slice kickoff（視 Month 5 retrospective）

**Deliverable**：6 個月達 Doc 08 原 9 個月 Q1 + Q2 + 部分 Q3 範圍；L4-Q3 Analogy 留給 Month 7-9 成熟

---

## 七、下一步建議（Week 1 可做）

### 立即執行（本週內）

1. **本 Delta 報告與 Core Team / Stakeholder 對齊**，校正 roadmap
2. **定位 workshop**：IPA 是 (A) RAPO 落地專案 or (B) 通用平台？決定 vertical slice 選擇
3. **OBO worktree 盤點**：確認 L0 剩餘 gap 實際大小
4. **Cohere Rerank 3 spike**（1-2 天評估成本 / 延遲 / precision 改善）

### Week 2-3

5. **Graphiti hello world**：docker + 10 entity + 100 episode ingestion
6. **Delta 報告維護**：每個 worktree merge 後更新三色表
7. **與 `research/memory-system-enterprise` worktree joint architecture 討論**

### Week 4

8. **決定 first vertical slice 目標**：Freight Invoice Variance（若 (A)）or 通用「文件 Q&A + citation + audit trail」（若 (B)）
9. **Sprint plan 撰寫**：按 CLAUDE.md Sprint Execution Workflow（plan + checklist + code + progress）

---

## 八、風險提醒

### 本 Delta 報告本身的風險

1. **OBO 狀態未驗證**：報告假設「可能在某 worktree」，需實地確認
2. **Memory episodic / procedural 狀態 VALIDATE 中**：未深讀 mem0 config
3. **Expert Registry 與 4 Q specialist 的 fit**：YAML schema 是否足以承載 finance/compliance 複雜 system_prompt，需 PoC 驗證一個 expert 才能確認
4. **Team executor synthesis 深度未驗**：需讀代碼確認是否可 leverage 為 Synthesizer Agent

### 研究文件（Doc 01-08）本身的風險

1. **V8 baseline 敘述陳舊**：Doc 08 多處引用「V8 現狀」，與 main 實際差距大（Phase 44+）
2. **RAPO-specific 假設**：Doc 05 案例 query、Doc 08 vertical slice 均綁定 RAPO freight；若 IPA 為通用平台需重新設計
3. **9-month roadmap 假設 ClaudeAgent migration 是大工程**：實際 main 已遠超此基線

---

## 九、結論

**核心訊息**：

1. **IPA main 比研究文件假設成熟 2-3 個 phase**。L2 Orchestrator + L4 Expert Registry 框架 + Knowledge hybrid 都已 deliver，**省下 12-15 週工作**
2. **真正投資仍集中在 L3 Ontology + L4 企業 specialist + L6 Bitemporal + GraphRAG**
3. **原 9-month roadmap 可壓縮到 ~6 個月**達同等 deliverable，Month 1 即可有 Cohere Rerank quick win
4. **下一步關鍵決策不是技術，是定位**：(A) RAPO 落地 or (B) 通用平台，兩者 vertical slice 取捨不同

**建議 next step**：先跑**定位 workshop**（1 小時）確認 (A) vs (B)，再基於本 Delta 設計 Phase 48 或 Research 2.0 roadmap

---

**版本記錄**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-19 | Claude + Chris | Initial delta analysis based on main commit `69b5fa2` + `179d7f8` (V9 forward sync to Phase 47 W1) |

**Related docs**：
- Research series: Doc 00-08（`docs/09-git-worktree-working-folder/knowledge-base-enterprise/`）
- V9 analysis: `docs/07-analysis/V9/00-index.md`
- Worktree: `research/knowledge-base-enterprise` at commit `69b5fa2`
