# Phase 52 — Context + Prompt

**Phase 進度**：Sprint 52.1 ✅ DONE / Sprint 52.2 🟡 PLANNING — **1 / 2 sprint complete（50%）**
**啟動日期**：2026-04-30（接 Phase 51 closeout）
**狀態**：🟡 **Sprint 52.2 PLANNING 中** — Cat 5 PromptBuilder 將達 Level 4，6 大支柱（DefaultPromptBuilder + 3 PositionStrategy + Memory 5×3 真注入 + CacheBreakpoint 接通 + Loop integration + AP-8 lint rule）；Phase 52 收尾，V2 半程里程碑 11/22 = 50%

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
| **52.2** | 🟡 PLANNING | 範疇 5 PromptBuilder（Level 4）— DefaultPromptBuilder + 3 PositionStrategy + Memory 5×3 真注入 + CacheBreakpoint 接通 LLM call + Loop integration + AP-8 lint rule（CARRY-031/032 解除）| TBD | `feature/phase-52-sprint-2-cat5-prompt-builder`（待開）|

> **Rolling 紀律**：52.2 plan + checklist 已 Day 0 起草（2026-05-01，52.1 closeout merged 後才開始）；待用戶 approve 才啟動 Day 1 code。53.x plan/checklist **嚴禁預寫**，必須等 52.2 closeout（含 retrospective）才開始起草。違反 rolling = 重蹈 Phase 35-38 跳過 plan 覆轍。

---

## Sprint 文件導航

```
phase-52-context-prompt/
├── README.md                          ← (this file) Phase 52 入口
├── sprint-52-1-plan.md                ✅ DONE（2026-05-01 closeout merged）
├── sprint-52-1-checklist.md           ✅ DONE
├── sprint-52-2-plan.md                🟡 PLANNING（待用戶 approve；2026-05-01 Day 0 起草）
└── sprint-52-2-checklist.md           🟡 PLANNING
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

## Sprint 52.1 已交付（✅ Done 2026-05-01）

詳見 [`sprint-52-1-plan.md`](./sprint-52-1-plan.md) + [`../../agent-harness-execution/phase-52/sprint-52-1/retrospective.md`](../../agent-harness-execution/phase-52/sprint-52-1/retrospective.md)。

**核心交付（5 大支柱齊出，Cat 4 Level 0 → Level 3）**：

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

> **52.1 已記錄延後項**（已轉至 52.2 / Phase 50+ / 53.x / infra waiting）：
> - ✅ Anthropic `cache_control` 接通 → **52.2 處理**（CARRY-031）
> - ✅ OpenAI `prompt_cache_key` 接通 → **52.2 處理**（CARRY-032）
> - ⏸ Sub-agent delegation prompt hint → Phase 54.2（Cat 11 own）
> - ⏸ Qdrant semantic compaction → CARRY-026 同 51.2 延後
> - ⏸ Redis-backed cache_manager → 待 infrastructure/cache ship（同 CARRY-029）

---

## Sprint 52.2 範圍預覽

**核心交付（per [`sprint-52-2-plan.md`](./sprint-52-2-plan.md)，2026-05-01 Day 0 起草）**：

### A. DefaultPromptBuilder（Cat 5 主入口）
- 6 層階層組裝：system → tools → memory_layers → conversation → user_message + cache_breakpoints
- Constructor DI 6 項：`memory_retrieval` / `cache_manager` / `token_counter` / `default_strategy` / `default_cache_policy` / `templates`
- 升級 49.1 PromptBuilder ABC 簽名（+`cache_policy` +`position_strategy` default=None）

### B. PositionStrategy ABC + 3 concrete（Cat 5 Lost-in-middle）
- `NaiveStrategy`：`[system, tools, memory, conversation, user]`
- `LostInMiddleStrategy`（**default**）：`[system, user_echo, tools, memory_summary, ...mid..., recent_assistant, user_actual]`
- `ToolsAtEndStrategy`：`[system, memory, conversation, user, tools]`
- 業界共識：重要內容置首尾（user message 同時在首段 echo + 末段 actual）

### C. Memory 5 layer × 3 time scale 真注入（Cat 5 ↔ Cat 3 整合）
- 走 51.2 `MemoryRetrieval.retrieve()` ABC（不直接讀 store；single-source 維持）
- 5 layer：system / tenant / role / user / session
- 3 time scale：permanent（優先）/ quarterly / daily（過期 filter）
- 🛡️ **4 紅隊 tenant 隔離測試**：cross-tenant / cross-user / cross-session / expired-time-scale 0 leak

### D. CacheBreakpoint 接通 LLM call（CARRY-031 + CARRY-032 解除）
- DefaultPromptBuilder 呼叫 52.1 `PromptCacheManager.get_cache_breakpoints()` → 寫入 `PromptArtifact.cache_breakpoints`
- **Azure OpenAI adapter**：`prompt_cache_key = sha256(":".join([bp.section_id]))` 注入 request
- **Mock Anthropic adapter**（test-only；不 import anthropic SDK）：在 `messages[bp.position]` 注入 `cache_control: {"type": "ephemeral"}` marker
- Real Anthropic adapter 留 Phase 50+ Provider 擴充

### E. Loop 整合（Cat 1 ↔ Cat 5 接通）
- `AgentLoop.run()` 每 turn 呼叫 `prompt_builder.build()` → ChatClient.chat(messages=artifact.messages, cache_breakpoints=artifact.cache_breakpoints)
- emit `PromptBuilt` event（payload：messages_count / estimated_input_tokens / cache_breakpoints_count / memory_layers_used / position_strategy_used / duration_ms）
- 50.x backward-compat：`prompt_builder=None` default → fallback 50.x ad-hoc 邏輯

### F. AP-8 Lint Rule（CI 強制）
- `scripts/check_promptbuilder_usage.py` AST-based lint
- Allowlist：`tests/**` / `**/_testing/**` / `**/contract_test_*.py`
- 違規時：PR fail；強制 `agent_harness/**` 主流量 0 ad-hoc messages 組裝

### G. Tests
- Unit：3 strategies + builder basic / memory injection（+4 red-team）/ cache integration / position / token estimation / templates / lint rule / mock anthropic adapter（~50 tests）
- Integration：Loop + PromptBuilder e2e / 5×3 矩陣 / cache hit steady state / SLO latency
- E2E：100% 主流量透過 PromptBuilder 驗證

**範疇歸屬**：
- 全部代碼在 `agent_harness/prompt_builder/` — 範疇 5（per `01-eleven-categories-spec.md` §範疇 5）
- Mock anthropic adapter 在 `adapters/_mock/`（test-only；不 import anthropic SDK）
- contracts 擴充 `agent_harness/_contracts/`（PromptSections / PositionStrategy 加入 §1.1）

> **Rolling 紀律提醒**：以下不在 52.2 scope，列入 CARRY-033+：
> - Real Anthropic adapter cache_control → Phase 50+ Provider 擴充
> - Cat 12 Tracer span for PromptBuilt → Phase 53.x（per 52.1 AI-10）
> - PromptAudit 政策（合規 vs 隱私）→ Phase 53.4 Governance Frontend
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

1. **52.2 plan + checklist Day 0 起草完成**（2026-05-01）— 待用戶 approve
2. 等用戶 approve → 啟動 Day 1（Branch + ABC 升級 + 3 PositionStrategy + DefaultPromptBuilder 雛形）
3. **53.x plan 嚴禁預寫** — 待 52.2 closeout（含 retrospective）才開始 rolling
4. Phase 52 收尾後：Phase 53（State + Error + Guardrails）4 sprint 起手；V2 cumulative 11/22 = 50%（半程里程碑）

---

**Last Updated**：2026-05-01 (Sprint 52.2 🟡 PLANNING — Day 0 plan + checklist + README rolling switch；Phase 52 1/2 = 50%；V2 cumulative **10/22 = 45%**；待 52.2 closeout 達 11/22 = 50%)
**Maintainer**：用戶 + AI 助手共同維護
