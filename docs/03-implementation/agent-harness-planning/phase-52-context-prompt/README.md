# Phase 52 — Context + Prompt

**Phase 進度**：Sprint 52.1 ✅ DONE / Sprint 52.2 ⏸ ROLLING — **1 / 2 sprint complete（50%）**
**啟動日期**：2026-04-30（接 Phase 51 closeout）
**狀態**：🟢 **Sprint 52.1 closeout 中** — Cat 4 達 Level 3，5 大支柱齊出，30+ turn no-OOM 驗證；Sprint 52.2 嚴守 rolling 紀律（待 52.1 merge 才寫）

---

## Phase 52 目標

> **Phase 52 是「對話可持久 + Prompt 集中化」**（per `06-phase-roadmap.md` §Phase 52）。
> 本 phase 完成後：
> - 範疇 4（Context Mgmt）達 Level 3（52.1）— 30+ turn 對話不劣化
> - 範疇 5（PromptBuilder）達 Level 4（52.2）— 100% 主流量透過 PromptBuilder 注入

詳細路線圖見 [`../06-phase-roadmap.md` §Phase 52](../06-phase-roadmap.md#phase-52-context--prompt2-sprint).

---

## Sprint 進度總覽

| Sprint | 狀態 | 主題 | 完成日期 | Branch / Commits |
|--------|------|------|---------|------------------|
| **52.1** | ✅ DONE | 範疇 4 Context Mgmt（Level 3）— 5 ABC + 3 Compactor 策略 + ObservationMasker + JITRetrieval (db://) + 3 TokenCounter + InMemoryCacheManager + Loop integration + 30+ turn no-OOM ⭐ + 50-turn e2e + SLO latency | **2026-05-01** | `feature/phase-52-sprint-1-cat4-context-mgmt`（5 commits：Day 0 / Day 1 / Day 2 / Day 3 / Day 4 + closeout）|
| **52.2** | ⏸ ROLLING | 範疇 5 PromptBuilder（Level 4）— 統一入口 + Lost-in-middle 策略 + CacheBreakpoint 接通 + memory layer 真注入 lint rule | TBD | TBD（52.1 merge 後 rolling 寫）|

> **Rolling 紀律**：52.2 plan/checklist **未寫**，必須等 52.1 closeout（含 retrospective）才開始起草。違反 rolling = 重蹈 Phase 35-38 跳過 plan 覆轍。

---

## Sprint 文件導航

```
phase-52-context-prompt/
├── README.md                          ← (this file) Phase 52 入口
├── sprint-52-1-plan.md                🟡 PLANNING（待用戶 approve）
├── sprint-52-1-checklist.md           🟡 PLANNING
├── sprint-52-2-plan.md                ⏸ ROLLING（52.1 closeout 後寫）
└── sprint-52-2-checklist.md           ⏸ ROLLING
```

執行紀錄（52.1 啟動後建立）：
```
docs/03-implementation/agent-harness-execution/phase-52/
└── sprint-52-1/{progress,retrospective}.md
```

---

## 範疇成熟度演進（規劃）

| 範疇 | Pre-Phase-52 | Post-52.1 實際 ✅ | Post-52.2 預計 |
|------|-------------|------------------|---------------|
| 1. Orchestrator Loop | Level 3 | **Level 3**（unchanged；Loop 加 compactor 注入 + ContextCompacted event；50.x baseline 10/10 維持）| **Level 3**（PromptBuilder 整合進 Loop 入口）|
| 2. Tool Layer | Level 3 | **Level 3**（unchanged）| **Level 3**（unchanged）|
| 3. Memory | Level 3 | **Level 3**（unchanged；Cat 4 透過 prompt hint 與 Cat 11 互動，不直接呼叫 Cat 3）| **Level 3**（PromptBuilder 從 Cat 3 抽 memory hints 注入 prompt）|
| **4. Context Mgmt** | Level 0 | **Level 3** ✅ **（達成）** | **Level 3**（unchanged；52.2 加 CacheBreakpoint 實際接通 LLM call）|
| **5. Prompt Builder** | Level 0 | Level 0 | **Level 4** ✅ |
| 6. Output Parser | Level 4 | Level 4 | Level 4 |
| 12. Observability | Level 2 | **Level 2**（52.1 ContextCompacted event 已 emit，Tracer span 留 Phase 53.x）| **Level 2**（52.2 加 PromptBuilt span）|

> **Cat 4 Level 3 的核心驗收（52.1 達成）**：
> - 30+ turn (35-turn integration test) → 0 over-budget turns + ≥1 compaction event ✅
> - Compaction latency p95：Structural 0.03ms / Semantic 0.02ms / Hybrid 0.05ms（mock LLM）— 全遠低於 SLO ✅
> - TokenCounter 3 implementations: TiktokenCounter (exact) / ClaudeTokenCounter (DI-friendly approx) / GenericApproxCounter ✅
> - Tenant cache 隔離 4 red-team tests + JIT tenant filter 3 red-team cases，0 leak ✅
> - 50-turn verifier pass-rate Δ < 5%（baseline 100% / compacted 100% → Δ=0）✅

---

## Sprint 52.1 範圍預覽

**核心交付（per Sprint 52.1 plan rolling 起草）**：

### A. Compaction 引擎（Cat 4 第 1 機制）
- `Compactor` ABC + `CompactionStrategy` enum（structural / semantic / hybrid）
- 3 個 concrete impl：
  - `StructuralCompactor` — 保留 system + 最近 N turn + HITL decisions；丟棄冗餘 tool results
  - `SemanticCompactor` — LLM judge 摘要早期 turn（透過 ChatClient ABC，符合中性原則）
  - `HybridCompactor` — structural 先跑 + 視 token 餘量 trigger semantic
- `should_compact()` 條件：`tokens > window * 0.75` 或 `turn_count > 30`

### B. Observation Masking（Cat 4 第 2 機制）
- `ObservationMasker` — 保留 tool_call requests，遮蔽超過 `keep_recent` 輪的 tool_results 為 `[REDACTED: tool X result]`
- 配置：`keep_recent: int = 5` 預設

### C. JIT Retrieval（Cat 4 第 3 機制）
- `JITRetrieval` — 「輕量 pointer + lazy resolve」pattern；避免把整個檔案 / 列表塞 context
- 51.2 `MemoryHint.full_content_pointer` 已是此 pattern 應用；52.1 提供 generic helper 給 Cat 2 工具用

### D. TokenCounter ABC（per-provider 實作）
- `TokenCounter` ABC：`count(messages, tools) -> int`
- 3 個 concrete impl：
  - `TiktokenCounter` — Azure OpenAI / OpenAI（cl100k_base / o200k_base）
  - `ClaudeTokenCounter` — Anthropic claude-tokenizer
  - `GenericApproxCounter` — fallback（4 chars ≈ 1 token；標記 `accuracy: approximate`）
- 由 `ChatClient.count_tokens()` 呼叫（已在 51.x adapter 簽名預留）

### E. PromptCacheManager ABC（caching infra）
- `PromptCacheManager` ABC：`get_cache_breakpoints()` + `invalidate(tenant_id, reason)`
- `CachePolicy` dataclass + `CacheBreakpoint` 標記
- `InMemoryCacheManager` impl（穩態 key-based dedup；TTL 300s 預設）
- **52.1 範圍**：ABC + impl + tenant key 隔離設計；**不接通**到實際 Anthropic `cache_control` 標記（52.2 PromptBuilder 在 build() 時注入）

### F. Loop 整合（Cat 1 連接點）
- `AgentLoop.run()` 每輪開頭呼叫 `compactor.compact_if_needed(state)`
- emit `ContextCompacted` event（已在 17.md §4.1 登記）
- token_used / window_size 寫入 `LoopState.transient.token_budget`

### G. Tests
- Unit：5 ABC + 3 compactor strategy + observation_masker + jit_retrieval + 3 token_counter + cache_manager（~30 tests）
- Integration：Loop + Compactor 30+ turn 不 OOM；Loop + ObservationMasker keep_recent 行為；Cache hit ratio 穩態量測
- E2E：50 turn 對話品質（Compaction 前後 verifier pass rate ±5%）+ tenant cache isolation red-team

**範疇歸屬**：
- 全部代碼在 `agent_harness/context_mgmt/` — 範疇 4（per `01-eleven-categories-spec.md` §範疇 4）
- contracts 在 `agent_harness/_contracts/` — 跨範疇 single-source（17.md §1.1）

> **Rolling 紀律提醒**：以下不在 52.1 scope，列入 CARRY-031+：
> - Anthropic `cache_control` 實際接通 → 52.2 PromptBuilder
> - Sub-agent delegation prompt hint → Phase 54.2 (Cat 11 own)
> - Qdrant semantic compaction → CARRY-026 同 51.2 延後
> - Redis-backed cache_manager → 待 infrastructure/cache ship（同 CARRY-029）

---

## Phase 52 結束驗收（per 52.1 + 52.2）

- ✅ 30+ turn 對話 token usage 在 75% 以下（95% session）（52.1）
- ✅ Compaction p95 latency < 2s（52.1）
- ✅ TokenCounter 誤差 < 2%（與 provider billing 比對；52.1）
- ✅ Tenant cache 隔離 red-team 0 leak（52.1）
- ✅ 100% 主流量 LLM 呼叫透過 PromptBuilder（52.2 lint rule）
- ✅ 5 layer × 3 time scale memory 真注入有測試（52.2）
- ✅ Anthropic `cache_control` / OpenAI `prompt_cache_key` 實際接通（52.2）

---

## 下一步

1. **52.1 plan + checklist 起草中**（rolling 進入 Day 0）
2. 等用戶 approve plan → 啟動 Day 1（Branch + ABC + contracts）
3. **52.2 plan 嚴禁預寫** — 待 52.1 closeout（含 retrospective）才開始 rolling

---

**Last Updated**：2026-05-01 (Sprint 52.1 ✅ DONE Day 4 closeout；Phase 52 1/2 = 50%；V2 cumulative **10/22 = 45%**)
**Maintainer**：用戶 + AI 助手共同維護
