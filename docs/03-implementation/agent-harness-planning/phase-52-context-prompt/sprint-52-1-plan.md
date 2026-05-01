# Sprint 52.1 — Plan：範疇 4 Context Mgmt（Level 0 → Level 3）

**Sprint**：52.1 — Cat 4 Context Management（Compaction + Observation Masking + JIT Retrieval + TokenCounter + PromptCacheManager）
**Phase**：52（Context + Prompt）/ 第 1 / 共 2 sprint
**Cumulative**：10/22 V2 sprints（Phase 52 進度 0/2 → 預計 1/2 = 50%）
**Branch**：`feature/phase-52-sprint-1-cat4-context-mgmt`（待開）
**Plan 起草**：2026-04-30
**Status**：🟡 PLANNING — 待用戶 approve 後啟動 Day 1

---

## 0. Sprint 目標（一句話）

把 **51.x 累積的長對話 token 風險**（30+ turn 必劣化、無 compaction、無 token 預算追蹤）解決，交付 **Cat 4 5 大支柱**：3 種 Compactor 策略 + ObservationMasker + JITRetrieval helper + 3 種 TokenCounter + PromptCacheManager ABC + InMemoryCacheManager impl，並把 Compactor 接進 Cat 1 AgentLoop 每輪開頭，使範疇 4 從 **Level 0 進到 Level 3**。

---

## 1. User Stories

### Story 1：Loop 每輪自動偵測 token 用量並 compact

> **作為** agent harness 主流量呼叫者
> **我希望** AgentLoop 每輪開頭自動 check token usage，超過 75% window 或 turn > 30 時自動 compact
> **以便** 30+ turn 對話不會 OOM、不會「lost in middle」、不會劣化決策品質

**驗收**：
- `AgentLoop.run()` 每 turn 開頭呼叫 `compactor.compact_if_needed(state)`
- 觸發條件：`state.token_used > window * 0.75` **OR** `state.turn_count > 30`
- 觸發時 emit `ContextCompacted` event（含 before / after token count）
- 30+ turn 整合測試：token usage 在 75% 以下 ≥ 95% turns
- 不觸發時 zero-cost（< 1ms overhead per turn）

### Story 2：3 種 Compaction 策略可切換 + Observation Masking 保留 tool_call 但遮蔽舊 results

> **作為** Phase 52+ 開發者
> **我希望** Compactor 可選擇 `structural`（規則式快）/ `semantic`（LLM judge 摘要準）/ `hybrid`（先 structural 不夠再 semantic），且舊 tool results 自動被遮蔽但保留 tool_call
> **以便** 不同場景能調策略，第 10 turn 仍看到「呼叫過 X 工具」但不需 5KB 舊 JSON

**驗收**：
- `CompactionStrategy` enum：`STRUCTURAL` / `SEMANTIC` / `HYBRID`；3 個 concrete impl 都通過 `Compactor` ABC contract test
- StructuralCompactor：保留 system + 最近 N turn + HITL decisions；< 100ms p95
- SemanticCompactor：LLM judge 摘要早期 turn（透過 ChatClient ABC，**0 LLM SDK leak**）；< 2s p95
- HybridCompactor：先 structural；若仍 > 75% 才 semantic；總 latency p95 < 2.5s
- `ObservationMasker.mask_old_results(messages, keep_recent=5)` 保留 `tool_calls` 字段，遮蔽 `role="tool"` 訊息為 `[REDACTED: tool {name} result; ts={ts}; bytes={n}]`

### Story 3：TokenCounter ABC 三 provider 精確計算

> **作為** Cat 4 Compactor / Cat 5 PromptBuilder
> **我希望** 我能呼叫 `token_counter.count(messages, tools)` 拿到誤差 < 2% 的 token 估算
> **以便** 75% threshold 觸發 compaction 不被誤估害到（過早 compact 浪費 / 過晚 compact OOM）

**驗收**：
- `TokenCounter` ABC + 3 concrete：`TiktokenCounter` / `ClaudeTokenCounter` / `GenericApproxCounter`
- TiktokenCounter 用官方 `tiktoken` lib（`cl100k_base` / `o200k_base` 視 model）
- ClaudeTokenCounter 用 anthropic 官方 tokenizer（lib 或 fallback approx）
- GenericApproxCounter：4 chars per token + tools schema +30% buffer（標記 `accuracy="approximate"`）
- 與 provider billing 對比測試：誤差 < 2%（real LLM 整合測試 = 50-message 對照）
- ChatClient adapter（azure_openai）`count_tokens()` 路由到 `TiktokenCounter`

### Story 4：PromptCacheManager ABC + Tenant 隔離

> **作為** 平台
> **我希望** 同一 tenant 的 system prompt + tool definitions + tenant memory 能 cache（穩態 hit > 50%），但 tenant A 的 cache 絕對不會被 tenant B hit
> **以便** 多租戶場景成本下降 30-90% + 合規不出包

**驗收**：
- `PromptCacheManager` ABC：`get_cache_breakpoints(tenant_id, policy)` + `invalidate(tenant_id, reason)`
- `CachePolicy` dataclass：5 個 cache_* boolean + `ttl_seconds: int = 300` + `invalidate_on: list[str]`
- `CacheBreakpoint` **擴充既有 `_contracts/chat.py:122`**（51.1 已有物理 marker：`position`/`ttl_seconds`/`breakpoint_type`）；52.1 加 logical metadata：`section_id: str | None` / `content_hash: str | None` / `cache_control: dict | None`，全 default=None 維持 51.1 callers 兼容（5 處 unchanged）
- `InMemoryCacheManager` impl：dict-backed key store + TTL；key = `sha256(tenant_id || section_id || content_hash || provider)`
- Tenant 隔離 red-team test：tenant_a 寫入 + tenant_b 用 same content 查 → cache miss（key 不同）
- 穩態 cache hit 率 > 50% 整合測試（5 turn 同 tenant + user 對話）
- **52.1 範圍**：ABC + InMemoryCacheManager + tenant key 隔離；**不接通 LLM call** → 留 52.2 PromptBuilder（CARRY-031）

### Story 5：範疇 4 達 Level 3 + Phase 52.2 整合就緒

> **作為** Phase 52.2 開發者
> **我希望** 範疇 4 的 ABC + 5 大組件穩定可用，並有 17.md §1.1 / §2.1 / §4.1 完整登記
> **以便** Sprint 52.2 PromptBuilder 可直接 inject memory hints + cache breakpoints + 透過 token_counter 守 budget

**驗收**：
- mypy --strict 全 src（baseline 65 → 目標 ~80 files）clean
- pytest 全綠（baseline 142 → 目標 ~205 PASS）
- 17.md §1.1 / §2.1 / §4.1 同步（5 ABC + 4 dataclass + 1 event 登記）
- Phase 52 README cumulative table 標 Cat 4 Level 0 → **Level 3**
- 30+ turn e2e + verifier pass rate 不劣化（±5%）

---

## 2. 技術設計

### 2.1 Cat 4 5 大支柱概覽

| 支柱 | ABC | 主要 Impl | 用途 | 觸發者 |
|------|-----|----------|------|--------|
| 1. Compaction | `Compactor` | StructuralCompactor / SemanticCompactor / HybridCompactor | 摘要 / 丟棄舊 turn | Cat 1 Loop（每 turn 開頭）|
| 2. Observation Masking | `ObservationMasker` | DefaultObservationMasker | 遮蔽舊 tool results 但保留 tool_calls | Compactor 內部 helper |
| 3. JIT Retrieval | `JITRetrieval` | PointerResolver helper | 輕量 pointer + lazy resolve | Cat 2 工具呼叫者（optional） |
| 4. Token Counting | `TokenCounter` | TiktokenCounter / ClaudeTokenCounter / GenericApproxCounter | 精確 token 估算 | ChatClient adapter + Compactor |
| 5. Prompt Caching | `PromptCacheManager` | InMemoryCacheManager | tenant-scoped breakpoint dedup | Cat 5 PromptBuilder（52.2）|

### 2.2 ABC 接口設計（draft，Day 1 final）

ABC 簽名概念（type hints 在 Day 1 落地）：

- `Compactor.compact_if_needed(state) -> CompactionResult`（async）
- `Compactor.should_compact(state) -> bool`（預設：token_used > window * 0.75 OR turn_count > 30）
- `ObservationMasker.mask_old_results(messages, keep_recent=5) -> list[Message]`
- `JITRetrieval.resolve(pointer, tenant_id) -> str`（async）
- `TokenCounter.count(messages, tools) -> int` + `accuracy() -> Literal["exact", "approximate"]`
- `PromptCacheManager.get_cache_breakpoints(tenant_id, policy) -> list[CacheBreakpoint]`（async）
- `PromptCacheManager.invalidate(tenant_id, reason) -> None`（async）

`CompactionResult` dataclass：triggered / strategy_used / tokens_before / tokens_after / messages_compacted / duration_ms / compacted_state（不觸發為 None）。

### 2.3 Compaction 3 策略

| 策略 | 邏輯 | 預期 latency p95 | 用途 |
|------|------|----------------|------|
| **Structural** | 保留 system + 最近 N turn + HITL decisions；丟棄重複 tool retry；call ObservationMasker 遮舊 tool results | < 100ms | 成本敏感 / 快速 turn |
| **Semantic** | 取超過 keep_recent 的 turn → 餵 ChatClient.chat() → 拿 ≤ 2000 token 摘要替代 | < 2s | 品質敏感 / token 緊張 |
| **Hybrid** | 先 Structural；若 token > 75% threshold 仍存在 → 接 Semantic | < 2.5s | 預設策略（balanced） |

**LLM 中性原則**：SemanticCompactor 注入 ChatClient ABC，禁止直接 import openai/anthropic（lint 強制）。

### 2.4 目錄結構

```
agent_harness/context_mgmt/
├── __init__.py                     # public re-exports
├── _abc.py                         # 5 ABC（ObservationMasker / JITRetrieval / 其他放對應子模組）
├── compactor/
│   ├── __init__.py
│   ├── _abc.py                     # Compactor ABC + CompactionStrategy enum
│   ├── structural.py               # StructuralCompactor
│   ├── semantic.py                 # SemanticCompactor (ChatClient injection)
│   └── hybrid.py                   # HybridCompactor (composes both)
├── observation_masker.py           # DefaultObservationMasker
├── jit_retrieval.py                # PointerResolver helper
├── token_counter/
│   ├── __init__.py
│   ├── _abc.py                     # TokenCounter ABC
│   ├── tiktoken_counter.py
│   ├── claude_counter.py
│   └── generic_approx.py
└── cache_manager.py                # PromptCacheManager ABC + InMemoryCacheManager
```

### 2.5 Loop 整合點（Cat 1 ↔ Cat 4 contract）

`AgentLoop.run()` 每 turn 開頭：

1. `result = await self.compactor.compact_if_needed(state)`
2. 若 `result.triggered` 為 True：state = result.compacted_state；emit `LoopEvent(type="ContextCompacted", payload={...})`
3. 繼續既有 reasoning / tool exec / verification 流程

**契約**：Compactor 不直接 mutate state（回傳 new state）→ Cat 7 State Mgmt 友好；Loop 不知道 strategy（依賴 Compactor ABC）→ Open/Closed 原則。

### 2.6 PromptCacheManager Cache Key 設計 + 與 Cat 11 非直接關係

**Cache key 公式**：
```
cache_key = sha256(tenant_id || section_id || content_hash || provider_signature)
```

- **Tenant 隔離**：tenant_id 第一段 → 不同 tenant same content 永遠不同 key
- **Provider 中性**：provider_signature 區分 azure_openai vs anthropic 的 cache

**Cat 4 ↔ Cat 11**（per 17.md §7.1）：**沒有直接 ABC 呼叫**，僅透過 prompt hint + LLM 決策聯繫。
- 52.1 scope：Compactor 在 token > 90% 且 task 可拆分時 emit hint `"consider task_spawn delegation"`（純 prompt 注入）
- 實際 `task_spawn` tool 在 Phase 54.2（Cat 11 own，CARRY-034）

### 2.7 17.md 同步點

**§1.1（dataclass / contract 表）— 新增 4 row**：
- `CompactionStrategy` — Cat 4，enum：STRUCTURAL / SEMANTIC / HYBRID
- `CompactionResult` — Cat 4，Compactor.compact_if_needed 回傳
- `CachePolicy` — Cat 4，per-tenant + per-loop caching 政策
- `CacheBreakpoint` — **擴充**既有 chat.py:122（Cat 5 own 物理 marker；Cat 4 加 logical metadata 欄位 — section_id/content_hash/cache_control，全 default=None）

**§2.1（ABC 表）— 新增 5 row**：
- `Compactor` / `ObservationMasker` / `JITRetrieval` / `TokenCounter` / `PromptCacheManager` 全 owner = `01-eleven-categories-spec.md` §範疇 4

**§4.1（LoopEvent 表）— 標記 ContextCompacted 為實作完成**：
- 移除「待 Phase 52.1」備註；payload：tokens_before / tokens_after / strategy_used / duration_ms

**§3.1（工具表）— 無變化**（Cat 4 不註冊 tool）。

---

## 3. File Change List

### 新建 / 重組（~14 file；含 49.1 stub 重寫 2 file）

```
agent_harness/context_mgmt/                              # 49.1 stub 已存（__init__.py + _abc.py）；52.1 重組 + 擴展
├── __init__.py                          # 49.1 stub；52.1 Day 4 補 public re-exports
├── _abc.py                              # 🔧 重寫：49.1 三 ABC 移至子目錄；改放 ObservationMasker / JITRetrieval ABC
├── compactor/{__init__,_abc,structural,semantic,hybrid}.py   # 5 file
├── observation_masker.py
├── jit_retrieval.py
├── token_counter/{__init__,_abc,tiktoken_counter,claude_counter,generic_approx}.py  # 5 file
└── cache_manager.py

agent_harness/_contracts/
├── compaction.py                        # CompactionStrategy + CompactionResult (NEW)
├── cache.py                             # CachePolicy (NEW)
└── chat.py                              # CacheBreakpoint extended with section_id / content_hash / cache_control (default=None)

tests/unit/agent_harness/context_mgmt/   # 9 test files / ~44 tests
├── test_compactor_structural.py        (6)
├── test_compactor_semantic.py          (4)
├── test_compactor_hybrid.py            (5)
├── test_observation_masker.py          (6)
├── test_jit_retrieval.py               (4)
├── test_token_counter_tiktoken.py      (5)
├── test_token_counter_claude.py        (3)
├── test_token_counter_generic.py       (3)
└── test_cache_manager.py               (8)

tests/integration/agent_harness/context_mgmt/
├── test_loop_compaction_30turn.py
├── test_observation_masker_keep_recent.py
└── test_cache_hit_ratio_steady_state.py

tests/e2e/
└── test_long_conversation_50turn.py
```

### 修改（~5 file）

- `agent_harness/orchestrator_loop/loop.py` — +compactor injection + per-turn compact check + ContextCompacted event
- `agent_harness/_contracts/__init__.py` — +CompactionStrategy/CompactionResult/CachePolicy exports（CacheBreakpoint 已 export，欄位擴充無需改 __init__）
- `adapters/azure_openai/adapter.py` — `ChatClient.count_tokens()` 路由到 TiktokenCounter
- `docs/03-implementation/agent-harness-planning/17-cross-category-interfaces.md` — §1.1 + §2.1 + §4.1 sync
- `docs/03-implementation/agent-harness-planning/phase-52-context-prompt/README.md` — 52.1 ✅ DONE marker（closeout）

### 刪除

無（52.1 純加新範疇 + 整合）。

---

## 4. Acceptance Criteria（DoD）

### 結構驗收
- [ ] 5 ABC（Compactor / ObservationMasker / JITRetrieval / TokenCounter / PromptCacheManager）齊備
- [ ] 3 Compactor 策略 concrete impl 都通過 Compactor ABC contract test
- [ ] 3 TokenCounter concrete impl 都通過 TokenCounter ABC contract test
- [ ] InMemoryCacheManager 實作 PromptCacheManager
- [ ] Loop 整合：每 turn 開頭呼叫 `compact_if_needed`；觸發時 emit `ContextCompacted` event
- [ ] CompactionResult dataclass 完整（triggered / strategy_used / tokens_before/after / duration_ms / compacted_state）

### SLO 量化驗收
- [ ] `context_used / window <= 75%` 在 95% session turn 中保持（30+ turn 測試）
- [ ] StructuralCompactor p95 < 100ms
- [ ] SemanticCompactor p95 < 2s
- [ ] HybridCompactor p95 < 2.5s
- [ ] TokenCounter 誤差 < 2%（與 Azure OpenAI billing 對比 ≥ 50 message 對照）
- [ ] Cache hit 率 > 50%（5 turn 同 tenant + user 穩態量測）
- [ ] Compaction 觸發後 verifier pass rate ±5%（無品質劣化）

### 多租戶 / 安全驗收
- [ ] tenant_a 寫入 cache + tenant_b 用 same content key 查 → miss（key 第一段不同）
- [ ] tenant_a 的 SemanticCompactor 摘要不會 leak tenant_b 內容
- [ ] PromptCacheManager.invalidate(tenant_a) 不影響 tenant_b 的 cache
- [ ] Red-team query × 5 全 0 leak
- [ ] `agent_harness/context_mgmt/**/*.py` grep `import openai|import anthropic` = **0**

### 測試 / Quality 驗收
- [ ] mypy --strict pass
- [ ] pytest baseline 142 → 目標 ~205 PASS（44 unit + 3 integration + 1 e2e + ~15 covered by integration）
- [ ] 所有新檔有 file header（per `file-header-convention.md`）
- [ ] AP-7 Context Rot Ignored 反模式 — 解決 ✅（本 sprint 主旨）
- [ ] 5 V2 lints 全 pass
- [ ] 17.md §1.1 + §2.1 + §4.1 同步（4 dataclass + 5 ABC + 1 event）

### 整合 / Demo 驗收
- [ ] 30+ turn e2e 測試（35 turn no-OOM + ContextCompacted ≥ 1 次）
- [ ] 50-turn verifier 對照（compaction 後 pass rate ±5%）
- [ ] Compaction p95 SLO 量測 3 strategy 全 pass
- [ ] Phase 52 README cumulative table 標 Cat 4 Level 0 → Level 3

---

## 5. CARRY Items 處理計畫

### 處理（51.x → 52.1 涵蓋）

無 — 52.1 不直接處理 51.x CARRY；CARRY-026/027/029/030 與 Cat 4 不衝突。

### 與 51.x CARRY 互動（不衝突）

| 51.x CARRY | 52.1 處理 |
|-----------|----------|
| CARRY-026（Qdrant semantic）| 不互動；SemanticCompactor 用 LLM 摘要 ≠ Qdrant 向量檢索 |
| CARRY-027（MemoryExtractor Celery）| 不互動 |
| CARRY-029（SessionLayer Redis）| 同 infra waiting；52.1 PromptCacheManager 同樣 in-memory 起步 |
| CARRY-030（ExecutionContext threading）| 52.1 暫透過 ToolCall.arguments / kwargs 傳 tenant_id；ExecutionContext 接通待 53.3 |

### 延後（記入 52.1 retrospective）

| ID | 項目 | 延後到 | 理由 |
|----|------|--------|------|
| CARRY-031 | Anthropic `cache_control` 實際接通 LLM call | 52.2 | 由 Cat 5 PromptBuilder 在 build() 時注入 |
| CARRY-032 | OpenAI `prompt_cache_key` 自動 cache 接通 | 52.2 | 同上 |
| CARRY-033 | Redis-backed PromptCacheManager | 待 infra cache ship | 同 CARRY-029 |
| CARRY-034 | Sub-agent delegation prompt hint 接通 | Phase 54.2 | Cat 11 own；52.1 只在 Compactor 留 stub hint |

---

## 6. Day 估時 + Theme（rolling 5-day）

| Day | 主題 | 估時 | 主要交付 |
|-----|------|------|---------|
| **Day 0** | Plan + Checklist + README sync | 2h | 本 plan / checklist / Phase 52 README |
| **Day 1** | 5 ABC + 4 contracts + 17.md §1.1/§2.1 sync + Branch | 6h | `_abc.py` + `_contracts/compaction.py` + `_contracts/cache.py` + 9 空 test 占位 |
| **Day 2** | Compactor 3 策略 concrete impl + Loop integration + ContextCompacted event | 8h | structural/semantic/hybrid + loop.py edit + 15 tests |
| **Day 3** | ObservationMasker + JITRetrieval + 3 TokenCounter + adapter route | 7h | 3 components + 21 tests |
| **Day 4** | PromptCacheManager + 30+ turn e2e + retro + closeout + 17.md §4.1 + README sync | 8h | cache_manager.py + 14 tests + retrospective.md + closeout |

**總估時**：~31h；預期 actual 8-10h（V2 cumulative pattern 24-28%）

> **Day 0 起跑前確認項**：
> - 用戶 approve plan（本檔）
> - 用戶 approve checklist
> - 用戶確認可開 branch `feature/phase-52-sprint-1-cat4-context-mgmt`

---

## 7. Sprint 結構決策（rolling）

### 決策 1：5 大支柱齊出，不分批

**選擇**：Compactor + ObservationMasker + JITRetrieval + TokenCounter + PromptCacheManager 一併進 52.1。

**理由**：5 者高度耦合 — Compactor 依賴 TokenCounter 量、依賴 ObservationMasker 遮蔽、SemanticCompactor 注入 ChatClient + 透過 PromptCacheManager 標 cache。分批會反覆改 Loop integration。

### 決策 2：PromptCacheManager 不接通 LLM call（留 52.2）

**選擇**：52.1 只 own ABC + InMemoryCacheManager + tenant key 隔離。實際 `cache_control` 注入 LLM call 留 52.2 PromptBuilder。

**理由**：cache 接通必須在 PromptBuilder.build() 時插 breakpoint marker；52.1 寫 PromptBuilder 違反 rolling（那是 52.2 範圍）。52.1 提供 ABC 給 52.2 用即可。

### 決策 3：JITRetrieval 提供 generic helper，但實際 wider use case 留後續

**選擇**：52.1 提供 `PointerResolver` 處理 `db://` / `memory://` 兩個 prefix；其他（`tool://` / `kb://`）stub + raise NotImplementedError。

**理由**：51.2 `MemoryHint.full_content_pointer` 已是此 pattern 應用；52.1 無新業務需求 trigger 完整 prefix tree。YAGNI。

### 決策 4：30+ turn e2e 用 mock LLM，不用 real provider

**選擇**：deterministic mock ChatClient（每 turn 回 ~1KB 內容）；real LLM 整合測試在 Sprint 56+ canary 處理。

**理由**：real LLM cost 高 + 不穩定（rate limit / 流量）；用 mock 能精確測 compaction 觸發、token 計算、tenant 隔離。

---

## 8. 風險與緩解

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|----------|
| TokenCounter 誤差 > 2%（real provider billing 對不上） | Medium | High（觸發 compaction 點偏移）| Day 4 加 50-message 對照測試；fallback 用 +20% safety buffer |
| SemanticCompactor LLM call 失敗 → state 丟失 | Low | High | HybridCompactor 設計時 Structural 先跑保底；Semantic 失敗 retry 1 次後降級為 Structural |
| Cache key 設計疏漏導致 tenant leak | Low | Critical | Day 4 強制 4 紅隊測試；Cache key 第一段必為 tenant_id |
| Compaction 後對話品質劣化 > 5% | Medium | High | Day 4 加 50-turn verifier 對照；劣化 > 5% 觸發 review + 調策略參數 |
| 30+ turn e2e 觸發 OOM（即使 compact）| Low | High | 加 turn-count cap 60 + token-budget cap 100K（hard fail-stop） |
| Day 4 過載（cache + e2e + retro 一併做） | Medium | Medium | 容許滑到 Day 5（rolling 紀律允許）；retro 必跑 |

---

## 9. 啟動條件

- [x] Phase 51 closeout 完成（51.0 + 51.1 + 51.2 全 ✅；main HEAD `a541d97` pushed）
- [x] V2 規劃文件 17.md 第 §1.1 / §2.1 / §4.1 確認可加新 row（無已存在衝突）
- [x] `agent_harness/context_mgmt/` 為 49.1 stub（`__init__.py` + `_abc.py` 含 3 舊 ABC）— 52.1 Day 1 將重組（`_abc.py` 改為 ObservationMasker/JITRetrieval；TokenCounter/Compactor/PromptCacheManager 移至子目錄；簽名升級）
- [ ] 用戶 approve plan（本檔）+ checklist
- [ ] 用戶確認可開 branch `feature/phase-52-sprint-1-cat4-context-mgmt`
- [ ] Sprint 51.2 Day 5 retrospective Action Items 處理狀態確認（AI-3 testing.md / AI-4 hook 調查 — 不阻 52.1 啟動）

---

**Last Updated**：2026-04-30（Day 0 起草完成，已對齊 51.2 plan 9 章節格式；待用戶 approve）
**Maintainer**：用戶 + AI 助手共同維護
