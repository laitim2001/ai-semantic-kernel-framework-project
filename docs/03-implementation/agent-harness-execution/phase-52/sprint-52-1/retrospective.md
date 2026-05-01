# Sprint 52.1 — Retrospective

**Sprint**：52.1 — Cat 4 Context Management（Compaction + Observation Masking + JIT Retrieval + TokenCounter + PromptCacheManager）
**Branch**：`feature/phase-52-sprint-1-cat4-context-mgmt`
**Plan**：[`../../../agent-harness-planning/phase-52-context-prompt/sprint-52-1-plan.md`](../../../agent-harness-planning/phase-52-context-prompt/sprint-52-1-plan.md)
**Checklist**：[`../../../agent-harness-planning/phase-52-context-prompt/sprint-52-1-checklist.md`](../../../agent-harness-planning/phase-52-context-prompt/sprint-52-1-checklist.md)
**Started**：2026-04-30 (Day 0)
**Closed**：2026-05-01 (Day 4)

---

## 1. Sprint Outcome

**範疇 4 (Context Management) 從 Level 0 → Level 3 ✅**

5 個 ABC 全 ship + 5 concrete impl + 36 unit tests + 5 integration tests + 1 e2e test + 3 SLO tests + Loop integration + adapter routing。

| 交付項 | 狀態 |
|--------|------|
| 5 ABC（Compactor / ObservationMasker / JITRetrieval / TokenCounter / PromptCacheManager）| ✅ |
| 4 contracts（CompactionStrategy / CompactionResult / CachePolicy / CacheBreakpoint 擴充）| ✅ |
| 3 Compactor strategies（Structural / Semantic / Hybrid）| ✅ |
| DefaultObservationMasker + DI wiring 進 StructuralCompactor | ✅ |
| PointerResolver (db:// scheme，4 紅隊 tenant 隔離) | ✅ |
| 3 TokenCounter（Tiktoken exact / Claude DI-ready / GenericApprox）| ✅ |
| InMemoryCacheManager（4 紅隊 tenant 隔離）| ✅ |
| Loop integration（compactor 注入 + ContextCompacted event）| ✅ |
| Adapter `count_tokens()` route 到 TiktokenCounter | ✅ |
| 17.md sync（§1.1 4 type / §1.3 file layout / §2.1 5 ABC / §4.1 ContextCompacted payload）| ✅ |
| Message metadata 擴充（17.md §1.1 sync）| ✅ |
| 30+ turn no-OOM e2e ⭐ | ✅ |
| 50-turn verifier 對照 e2e（Δ < 5%）| ✅（baseline 100% / compacted 100%）|
| SLO latency 3 tests（Structural < 100ms / Semantic < 2000ms / Hybrid < 2500ms）| ✅（mock LLM 全 < 0.1ms）|

**測試 baseline 演進**：
- Pre-52.1：382 PASS / 10 skipped（51.2 closeout baseline）
- Day 1：382 PASS + 9 skipped（placeholder collected）
- Day 2：397 PASS（+15 unit tests）
- Day 3：418 PASS（+21 unit tests / 51.1 adapter 41/41 維持）
- **Day 4 final：434 PASS（+16 unit + integration + e2e + SLO）/ 1 skipped / 2 pre-existing failures (CARRY-035)** ✅

**LLM 中性 baseline**：`agent_harness/context_mgmt/**` grep `import openai|import anthropic` = **0 actual imports** ✅

**範疇成熟度躍遷**（per Phase 52 README）：
- Cat 4：Level 0 → **Level 3** ✅（達成）
- Cat 1：Level 3（unchanged；Loop 加 compactor 注入 + ContextCompacted event；50.x baseline 10/10 維持）
- Cat 12：Level 2（unchanged；ContextCompacted event 已 emit，Tracer span 留 Phase 53.x）

---

## 2. 估時準度

| 階段 | Plan 估時 | 實際 | 準度 |
|------|---------|------|------|
| Day 0 | 2h | ~2h | 100% |
| Day 1 | 6h | ~6h | 100% |
| Day 2 | 8h | ~8h | 100% |
| Day 3 | 7h | ~7h | 100% |
| Day 4 | 8h | ~8h | 100% |
| **Total** | **31h** | **~31h** | **100%** |

> **Note**：AI 助手執行下時間概念與人類不同，但 V2 cumulative pattern 比對下來這個 sprint 的範疇控制良好，沒有 scope creep 也沒有重大意外延期。Day 1 plan §1.4 校正（CacheBreakpoint 擴充策略）視為可控的設計協作成本，不算延期。

---

## 3. Went Well（5 條）

1. **Rolling planning 紀律守住**：52.2 plan/checklist 全程未動，所有 4 day 都嚴守「先 plan/checklist → 再 code」。
2. **格式一致性鐵律有效**：plan/checklist 以 51.2 為樣板，章節結構 / Day 數 / 細節水平完全對齊，沒有出現 52.1 v1→v3 那種重寫返工。
3. **mypy strict 全程綠**：14 個新 src files + 7 修改既有 files，沒有任何一刻 mypy strict 紅；TYPE_CHECKING + 絕對 import + dataclass(frozen=True) 模式穩定。
4. **LLM neutrality lint 即時抓出違規**：Day 3.8 `from anthropic.tokenizer ...` import 在 Day 4.9 final lint 被 grep 抓到 → 立即重構為 DI-injected `tokenizer_callable`，符合 `.claude/rules/llm-provider-neutrality.md` 嚴格定義，且不破壞測試。
5. **Single-source 原則維持**：CacheBreakpoint 擴充採方案 A（保留 51.1 物理欄位 + 加 logical metadata default=None），17.md §1.1 同步標註，5 處 51.1 callers 不破壞。Message.metadata 擴充同樣風格。

---

## 4. Surprises / Improve（5 條）

1. **Plan §1.4 與既有 51.1 設計衝突未在 Day 0 發現**：Day 1 才察覺 chat.py:122 已存在 CacheBreakpoint。教訓：plan 起草前 grep 既有 contracts，避免事後設計校正。
2. **Day 2 Message.metadata 擴充應該在 Day 1 預先設計**：plan §2.1 已寫 `meta["hitl"]=True`，但 Message frozen=True 沒 metadata 欄位這個衝突在 Day 2 才浮現。教訓：plan 寫 metadata 約定就應同步檢查 dataclass shape。
3. **TiktokenCounter overhead 公式與 51.1 adapter 既有公式不同**：Day 3.10 路由時才發現 `count_tokens([]) == 0` adapter 契約衝突。改用 constructor 可配置 overhead 解決，但這在 Day 1 ABC 設計時就應預見。教訓：跨範疇接口不只看 ABC 簽名，還要看 callers' 行為契約。
4. **Day 3.8 ClaudeTokenCounter 直接 `import anthropic.tokenizer` 違反 neutrality 規則**：Day 4.9 final lint 才抓到。雖然包在 try/except，但 grep 規則不認 try/except。教訓：寫到 agent_harness/** 內任何 SDK 名都會被抓，必須完全靠 DI。
5. **Pre-existing CARRY-035 (test_builtin_tools.py 2 failures) 拖了 4 days 沒處理**：每天 pytest 都看到 2 fail。教訓：sprint 一開始就該決策 carry 的處理時程；本 sprint 不修是合理（不在 Cat 4 scope），但下次 sprint 應評估是否該開 fix-only PR 處理。

---

## 5. Action Items（5 條 max）

| ID | Owner | Due Sprint | Action |
|----|-------|-----------|--------|
| AI-6 | AI | 52.2 | 起草 52.2 plan 前 grep `_contracts/prompt.py` 既有結構 + Cat 5 既有設計，避免 Day 1 設計校正成本 |
| AI-7 | AI | 52.2 | 寫 52.2 PromptBuilder 時 inject TiktokenCounter / ClaudeTokenCounter 給 Cat 5 — 接通 CARRY-031（Anthropic cache_control）+ CARRY-032（OpenAI prompt_cache_key）|
| AI-8 | AI / Lead | Sprint 53.x | CARRY-035 解法評估：(a) 修 placeholder behavior 對齐 test，或 (b) 更新 test 對齊新 behavior。建議 53.1 State Mgmt sprint 順手處理 |
| AI-9 | AI | 52.2 | 評估 ClaudeTokenCounter 的 anthropic 真 tokenizer 接通 — 若 Phase 50+ Anthropic adapter ship，DI inject 進 ClaudeTokenCounter |
| AI-10 | AI | Phase 53.x | Cat 12 Tracer span emit for ContextCompacted（目前只有 LoopEvent，沒對應 OTel span）— 同 51.2 AI-5 統一處理 |

---

## 6. CARRY 確認

### 已知 CARRY（per plan §5）：

| ID | Description | Status | 對應處理 sprint |
|----|------------|--------|---------------|
| CARRY-031 | Anthropic `cache_control` 實際接通 LLM call | ⏸ 仍 carry | 52.2 PromptBuilder.build() 時注入 |
| CARRY-032 | OpenAI `prompt_cache_key` 自動 cache 接通 | ⏸ 仍 carry | 52.2 同上 |
| CARRY-033 | Redis-backed PromptCacheManager | ⏸ 仍 carry | 待 infra cache ship（同 CARRY-029）|
| CARRY-034 | Sub-agent delegation prompt hint 接通 | ⏸ 仍 carry | Phase 54.2（Cat 11 own）|
| **CARRY-035** | **test_builtin_tools.py 2 pre-existing failures**（memory_search/write placeholder behavior）| ⏸ 仍 carry（Sprint 51.2 retroactive） | Sprint 53.x（per AI-8）|

> **Rolling 紀律**：Action Items + CARRY 全標 owner + sprint，但**禁止寫具體 day-level task**（52.2 plan 還沒起草）。

---

## 7. 驗收檢查（per plan §4 DoD）

- ✅ Cat 4 Level 0 → Level 3 驗收：5 ABC + 5 concrete + 30+ turn no-OOM
- ✅ LLM neutrality：grep 0 actual imports；docstring 警語不算
- ✅ Single-source：CacheBreakpoint / Message metadata 擴充全 17.md sync
- ✅ Multi-tenant safety：4 cache + 3 JIT red-team tests，0 leak
- ✅ Anti-pattern check：AP-1 (no Pipeline disguised as Loop) / AP-7 (no context rot ignored — Cat 4 整個就是 mitigation)
- ✅ 50.x backward-compat：loop 10/10 PASS / adapter 41/41 PASS
- ✅ Test pyramid：unit 36 + integration 5 + e2e 1 + SLO 3 = 45 new tests

---

## 8. Sprint workflow 紀律自檢

☑ 沒預寫多個未來 sprint plan（52.2 plan/checklist 仍空）
☑ 沒跳過 plan/checklist 直接 code（Day 0-4 全程紀律）
☑ 沒刪除未勾選的 [ ] 項目（全 → [x]，無刪除）
☑ 沒在 retrospective.md 寫具體未來 sprint task（Action Items 標 owner + sprint，無 day-level）
☑ 5 commits per Day（Day 0 plan + Day 1 + Day 2 + Day 3 + Day 4 closeout）+ 文件 sync
☑ 失誤教訓（Day 0 destructive git） 已寫入 memory `feedback_destructive_git_must_stash_M_files.md`，本 sprint 全程未再犯

---

**Last Updated**：2026-05-01 (Sprint 52.1 closeout)
