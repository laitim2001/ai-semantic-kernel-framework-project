# Sprint 52.1 — Checklist：範疇 4 Context Mgmt

**Sprint**：52.1 — Cat 4 Context Management
**Plan**：[`sprint-52-1-plan.md`](./sprint-52-1-plan.md)
**Branch**：`feature/phase-52-sprint-1-cat4-context-mgmt`（Day 1 開）
**Status**：🟡 PLANNING — 待用戶 approve

> **規矩重申**：每項 `[ ]` → `[x]` 一律由 AI 助手在 commit 時即時更新；**未勾選項禁止刪除**（per `feedback_never_delete_unchecked_items` + Phase 42 Sprint 147 教訓）。延後項標 `🚧` + 理由。

---

## Day 0 — Plan + Checklist + Phase 52 README sync（估 2h）

### 0.1 Plan / Checklist 起草（已完成）
- [x] **建 `phase-52-context-prompt/sprint-52-1-plan.md`**（10 sections §0-9，對齊 51.2 格式）
  - 章節：0 目標 / 1 User Stories / 2 技術設計 / 3 File Change List / 4 DoD / 5 CARRY / 6 Day 估時 / 7 Sprint 結構決策 / 8 風險 / 9 啟動條件
  - DoD：與 51.2 plan 章節結構同（10 sections）
- [x] **建 `phase-52-context-prompt/sprint-52-1-checklist.md`**（本檔）
  - 5-day 結構（Day 0-4）；每 day 子任務含 DoD + Verify command
  - DoD：與 51.2 checklist 細節水平同

### 0.2 Phase 52 README sync
- [x] **建 `phase-52-context-prompt/README.md`**
  - phase 進度 / sprint 總覽（52.1 PLANNING / 52.2 ⏸ ROLLING）/ 範疇成熟度演進 / 52.1 範圍預覽
  - 寫入 rolling 紀律提醒（52.2 不預寫）
  - DoD：mirror `phase-51-tools-memory/README.md` 結構

### 0.3 啟動前環境確認
- [x] **確認 main HEAD `a541d97`（51.2 merge）pushed origin**
  - Cmd：`git log -1 --oneline main`；`git ls-remote origin main`
  - Result：local HEAD `a541d97` ✅；remote `a541d979...4f8a4ef`（同 commit）✅
- [x] **確認 `agent_harness/context_mgmt/` 為 49.1 stub（不是 greenfield）**
  - Actual：目錄存在；含 `__init__.py` + `_abc.py`（49.1 Sprint 起的 stub，3 ABC：TokenCounter / Compactor / PromptCacheManager — 簽名與 52.1 spec 不同）
  - Action：Day 1 將 stub 重組為 5 ABC + 子目錄結構（`compactor/_abc.py` / `token_counter/_abc.py` / 新 `_abc.py` 含 ObservationMasker / JITRetrieval / `cache_manager.py` 含 PromptCacheManager）
  - DoD：plan §3 File Change List 已標 _abc.py / __init__.py 為「重組現有 49.1 stub」
- [x] **確認 51.2 retrospective Action Items 不阻 52.1 啟動**
  - Read `docs/03-implementation/agent-harness-execution/phase-51/sprint-51-2/retrospective.md`
  - Status：
    - AI-3（pytest `__init__.py` convention / `--import-mode=importlib`）→ owner AI / sprint 52.x — 可在 52.1 期間順手；不阻啟動
    - AI-4（security hook trigger pattern 研究）→ owner AI / sprint 52.x — 研究性質；不阻啟動
    - AI-5（Cat 12 observability span for MemoryRetrieval）→ owner AI / sprint 53.x — 不阻 52.1
  - DoD：3 Action Items 全標 owner + sprint；無一是 52.1 hard blocker ✅

### 0.4 Day 0 commit
- [x] **commit Day 0 docs**
  - Files：3 new（`phase-52-context-prompt/README.md` + `sprint-52-1-plan.md` + `sprint-52-1-checklist.md`）
  - Msg：`docs(phase-52, sprint-52-1): Day 0 plan + checklist + Phase 52 README rolling start`
  - Co-author per V2 git-workflow.md
  - DoD：commit message scope = `phase-52, sprint-52-1`；working tree 留有其他 pre-existing 修改（V2-AUDIT W1/W2 + sprint-workflow.md / CLAUDE.md / situation prompt）— 留待後續單獨 commit
  - Verify：`git log -1 --oneline` 顯示 Day 0 commit ✅

---

## Day 1 — 5 ABC + 4 contracts + 17.md sync（估 6h）

### 1.1 開新 feature branch
- [x] **`git checkout -b feature/phase-52-sprint-1-cat4-context-mgmt`** from main HEAD `a541d97`
  - DoD：`git branch --show-current` = `feature/phase-52-sprint-1-cat4-context-mgmt` ✅
  - Verify：`git log -1 --oneline` 顯示 51.2 merge commit ✅（branch 早於 Day 1 已存在；feature HEAD = `e5bbc995` Day 0 commit）

### 1.2 重組 49.1 stub 為 5 ABC + 子目錄結構（30 min）

> **Day 1 執行 note (2026-05-01)**：1.2 + 1.5 合併執行（同一輪重組 + ABC 簽名一氣呵成），因依賴順序為 1.3+1.4 contracts → 1.2+1.5 ABCs → 1.6+1.7 17.md → 1.8 tests。__init__.py 在 1.2 同時更新 re-export（不延後到 Day 4）以維持 test_imports baseline 不破。

- [x] **更新 `agent_harness/context_mgmt/__init__.py`**：re-export 5 ABC（Compactor / ObservationMasker / JITRetrieval / TokenCounter / PromptCacheManager）從新位置
- [x] **重寫 `agent_harness/context_mgmt/_abc.py`**：移除 49.1 三 ABC（TokenCounter/Compactor/PromptCacheManager），改為 ObservationMasker + JITRetrieval ABC（其餘 3 ABC 移至子目錄）
- [x] **建 `agent_harness/context_mgmt/compactor/__init__.py`**（package marker，re-export Compactor）
- [x] **建 `agent_harness/context_mgmt/compactor/_abc.py`**（Compactor ABC + 預設 should_compact 邏輯；簽名升級至 `compact_if_needed → CompactionResult`）
- [x] **建 `agent_harness/context_mgmt/token_counter/__init__.py`**（package marker，re-export TokenCounter）
- [x] **建 `agent_harness/context_mgmt/token_counter/_abc.py`**（TokenCounter ABC + accuracy() Literal["exact","approximate"]）
- [x] **建 `agent_harness/context_mgmt/cache_manager.py`**（PromptCacheManager ABC + tenant-scoped get_cache_breakpoints / invalidate）
  - DoD：7 file 全有 file header（per `file-header-convention.md`）；mypy --strict pass ✅
  - Verify：`python -m mypy backend/src/agent_harness/context_mgmt --strict` → Success: no issues found in 7 source files

### 1.3 建 `_contracts/compaction.py`（30 min）
- [x] **`_contracts/compaction.py`**：`CompactionStrategy` enum（STRUCTURAL / SEMANTIC / HYBRID）✅
- [x] **`_contracts/compaction.py`**：`CompactionResult` dataclass（frozen=True）
  - 欄位：`triggered: bool` / `strategy_used: CompactionStrategy | None` / `tokens_before: int` / `tokens_after: int` / `messages_compacted: int` / `duration_ms: float` / `compacted_state: LoopState | None` ✅
- [x] **更新 `_contracts/__init__.py` re-export**
  - DoD：`from agent_harness._contracts import CompactionStrategy, CompactionResult` 成功 ✅
  - Verify：`python -m mypy backend/src/agent_harness/_contracts --strict` → Success ✅

### 1.4 擴充 chat.py CacheBreakpoint + 建 `_contracts/cache.py`（30 min）

> **設計校正（2026-05-01）**：原 plan §1.4 寫「建 `cache.py` 含 CacheBreakpoint」，但 51.1 已在 `_contracts/chat.py:122` 定義 CacheBreakpoint 物理 marker 並由 5 處 callers（`adapters/_base/chat_client.py` / `azure_openai/adapter.py` / `_testing/mock_clients.py` / `_contracts/prompt.py` / `context_mgmt/_abc.py`）使用。為維持 single-source rule + 兼容 51.1，採方案 A：**擴充既有 chat.py CacheBreakpoint**（加 logical metadata 欄位 default=None），新建 cache.py 只放 CachePolicy。

- [x] **擴充 `_contracts/chat.py` CacheBreakpoint**（保留既有 `position` / `ttl_seconds` / `breakpoint_type` 物理欄位）
  - 加：`section_id: str | None = None`（logical 區塊識別，52.2 PromptBuilder 接通）✅
  - 加：`content_hash: str | None = None`（內容 hash，cache invalidation 用）✅
  - 加：`cache_control: dict[str, object] | None = None`（Anthropic-style raw control，52.2 接通）✅
  - 全 default=None → 51.1 既有 5 處 callers 不破壞 ✅（adapter test 41/41 PASS）
- [x] **建 `_contracts/cache.py`**：`CachePolicy` dataclass（frozen=True）
  - 欄位：`enabled: bool = True` / `cache_system_prompt: bool = True` / `cache_tool_definitions: bool = True` / `cache_memory_layers: bool = True` / `cache_recent_turns: bool = False` / `ttl_seconds: int = 300` / `invalidate_on: list[str] = []` ✅
- [x] **更新 `_contracts/__init__.py` re-export**：加 CachePolicy + CompactionStrategy + CompactionResult（CacheBreakpoint 已 export，欄位擴充無需動 __init__ 但仍從 chat 重新 import）✅
  - DoD：CachePolicy 可 import；mypy strict clean；51.1 5 處 callers 不破壞 ✅
  - Verify：`from agent_harness._contracts import CachePolicy, CacheBreakpoint, CompactionStrategy, CompactionResult` 成功 ✅ + 51.1 adapter tests 41/41 PASS ✅

### 1.5 完成 5 ABC（90 min）

> **Day 1 執行 note (2026-05-01)**：與 1.2 合併執行。所有 ABC 簽名一次到位，避免 placeholder→fill 兩輪改寫。

- [x] **`compactor/_abc.py` 寫 `Compactor` ABC** ✅
  - `should_compact(state) -> bool`（concrete default：`token_used > window * 0.75 OR turn_count > 30`；concrete impls 可 override）✅
  - `compact_if_needed(state) -> CompactionResult`（async abstract，trace_context 可選）✅
  - DoD：mypy strict pass；ABC method docstring 完整 ✅
- [x] **`_abc.py` 寫 `ObservationMasker` ABC** ✅
  - `mask_old_results(messages, *, keep_recent: int = 5) -> list[Message]` (abstract) ✅
- [x] **`_abc.py` 寫 `JITRetrieval` ABC** ✅
  - `resolve(pointer: str, *, tenant_id: UUID) -> str` (async abstract) ✅
- [x] **`token_counter/_abc.py` 寫 `TokenCounter` ABC** ✅
  - `count(*, messages, tools=None) -> int` (abstract) ✅
  - `accuracy() -> Literal["exact", "approximate"]` (abstract) ✅
- [x] **`cache_manager.py` 寫 `PromptCacheManager` ABC** ✅
  - `get_cache_breakpoints(*, tenant_id, policy) -> list[CacheBreakpoint]` (async abstract) ✅
  - `invalidate(*, tenant_id, reason) -> None` (async abstract) ✅
  - DoD：5 ABC 簽名齊；每個 ABC 有 module docstring（含 owner / 跨範疇互動說明）✅
  - Verify：`python -m mypy backend/src/agent_harness/context_mgmt --strict` → Success: no issues found in 7 source files ✅

### 1.6 17.md §1.1 同步（45 min）
- [x] **更新 `17-cross-category-interfaces.md` §1.1** ✅
  - 加 row：`CompactionStrategy` — Owner `01-eleven-categories-spec.md` §範疇 4，描述 enum 3 值 ✅
  - 加 row：`CompactionResult` — Owner Cat 4，描述 7 欄位 ✅
  - 加 row：`CachePolicy` — Owner Cat 4，描述 5 cache_* boolean ✅
  - 改 row：`CacheBreakpoint` — Owner 改為「範疇 5（物理）+ 範疇 4（logical metadata）」標明 52.1 擴充欄位 ✅
  - 同步 §1.3 file layout：加 `compaction.py` + `cache.py` ✅
  - DoD：grep 確認 4 type 列入；single-source 規則維持 ✅
  - Verify：`grep -n "CompactionStrategy\|CompactionResult\|CachePolicy\|CacheBreakpoint" docs/03-implementation/agent-harness-planning/17-cross-category-interfaces.md` → 4 type 全列入 ✅

### 1.7 17.md §2.1 同步（45 min）
- [x] **更新 `17-cross-category-interfaces.md` §2.1** ✅
  - 改 row：`Compactor` — Cat 4，簽名升級 `should_compact() / compact_if_needed() -> CompactionResult`（49.1 stub `compact() -> LoopState` 已淘汰）✅
  - 加 row：`ObservationMasker` — Cat 4，方法 `mask_old_results()` ✅
  - 加 row：`JITRetrieval` — Cat 4，方法 `resolve(pointer)`（multi-tenant safety: tenant_id 強制）✅
  - 改 row：`TokenCounter` — Cat 4，加 `accuracy()` Literal["exact","approximate"] ✅
  - 加 row：`PromptCacheManager` — Cat 4，方法 `get_cache_breakpoints()` / `invalidate()`（multi-tenant safety: tenant_id 強制隔離）✅
  - DoD：5 ABC 列入；grep 確認 ✅
  - Verify：`grep -n "ObservationMasker\|JITRetrieval\|PromptCacheManager" 17.md` → 全列入 ✅

### 1.8 9 個 unit test 占位（30 min）
- [x] **建 `tests/unit/agent_harness/context_mgmt/` 9 個 test 檔**（per plan §3 file 清單）✅
  - `test_compactor_structural.py` / `test_compactor_semantic.py` / `test_compactor_hybrid.py` ✅
  - `test_observation_masker.py` / `test_jit_retrieval.py` ✅
  - `test_token_counter_tiktoken.py` / `test_token_counter_claude.py` / `test_token_counter_generic.py` ✅
  - `test_cache_manager.py` ✅
  - 各檔內含 `pytest.mark.skip(reason="Day 2-4 implements")` placeholder + module docstring（每檔列 Day X.Y 對應的 test 名單）✅
  - DoD：pytest collect succeeds；no test runs（all skipped）✅
  - Verify：`python -m pytest backend/tests/unit/agent_harness/context_mgmt/ --collect-only -q` → 9 tests collected; `pytest -v` → 9 skipped ✅

### 1.9 Day 1 commit
- [x] **commit Day 1** ✅
  - Msg：`feat(context-mgmt, sprint-52-1): Day 1 — 5 ABC + 4 contracts + 17.md §1.1/§2.1 sync` ✅
  - Files：7 src（6 new + 1 rewrite）+ 3 contracts edits（chat extension + 2 new）+ 9 test placeholder + 17.md + plan + checklist
  - DoD：mypy --strict pass（20 files clean）；pytest collect 0 fail（9 tests collected/skipped）；51.1 baseline 維持（adapter 41/41 PASS）；test_imports 4/4 PASS；LLM SDK leak 0 ✅
  - 已知 carry：`test_builtin_tools.py::test_memory_search_placeholder_raises` + `test_memory_write_placeholder_raises` 2 個 PRE-EXISTING failure（非 Day 1 引入；Cat 2/3 placeholder 行為 vs test 期望分歧；Sprint 51.2 retroactive 應已捕捉但未修；CARRY-035 留 retro Day 4）
  - Verify：`git log -1 --stat` ✅

---

## Day 2 — Compactor 3 策略 + Loop integration（估 8h）

### 2.1 `StructuralCompactor` impl（90 min）

> **Day 2 執行 note (2026-05-01)**：完成；採方案 A 預先擴充 `Message.metadata: dict` 欄位以支援 `hitl=True` / `compacted_summary=True` 標記（17.md §1.1 Message row 已 sync）。

- [x] **建 `compactor/structural.py`** ✅
  - 邏輯：保留 system message + 最近 `keep_recent_turns` turn + HITL decisions（標 `metadata["hitl"]=True`）；丟重複 tool retry（detect by tool_name + sha256(args)） ✅
  - 配置：`keep_recent_turns: int = 5` / `preserve_hitl: bool = True` / `token_budget: int = 100_000` / `token_threshold_ratio: float = 0.75` / `turn_threshold: int = 30` ✅
  - Day 2 暫用 inline mask 邏輯（`_redact_old_tool_results` helper；Day 3.3 接通 ObservationMasker） ✅
  - override `should_compact()` 用 state.transient.token_usage_so_far / current_turn ✅
  - DoD：implements Compactor ABC 全方法；file header 含 `Why:` 說明（V1 教訓 AP-7） ✅

### 2.2 `test_compactor_structural.py` — 6 tests（45 min）
- [x] `test_not_triggered_below_threshold`（token < 75% AND turn < 30）✅
- [x] `test_triggered_by_token_threshold`（token > 75%）✅
- [x] `test_triggered_by_turn_count`（turn > 30 但 token 低）✅
- [x] `test_preserves_system_message`（system message always 在 result.compacted_state）✅
- [x] `test_preserves_hitl_decisions`（metadata["hitl"]=True 不被丟）✅
- [x] `test_drops_redundant_tool_retry`（同 tool_name + sha256(args) 出現 2+ 次只留最新）✅
  - DoD：6 tests pass；mock LoopState；no real LLM call ✅
  - Verify：`python -m pytest backend/tests/unit/agent_harness/context_mgmt/test_compactor_structural.py -v` → 6/6 PASS ✅

### 2.3 `SemanticCompactor` impl（120 min）
- [x] **建 `compactor/semantic.py`** ✅
  - 邏輯：取超過 `keep_recent_turns` 的 user→assistant turn（以 user message 為錨點）→ 透過注入 ChatClient.chat() 摘要 → 替換為 single assistant message（標 `metadata["compacted_summary"]=True`） ✅
  - 注入：`chat_client: ChatClient` / `summary_max_tokens: int = 2000` / `summary_system_prompt: str = SUMMARY_PROMPT` 常數 / `retry_count: int = 1` ✅
  - Failure handling：retry 1 次；仍失敗則 raise `SemanticCompactionFailedError`（HybridCompactor 接住降級）✅
  - **LLM 中性**：`grep "import openai\|import anthropic" compactor/semantic.py` = 0（docstring 警語不算實際 import）✅
  - DoD：implements Compactor ABC；file header 含 LLM 中性說明 ✅

### 2.4 `test_compactor_semantic.py` — 4 tests（45 min）
- [x] `test_summarize_old_turns_via_mock_client`（MockChatClient 回固定摘要 → 替換成功）✅
- [x] `test_preserves_recent_n_turns`（keep_recent_turns 以 user 為錨；最近 N 個 user→assistant turn 完整保留）✅
- [x] `test_handles_llm_failure_raises`（_FailingChatClient 拋例外 → retry 後 SemanticCompactionFailedError）✅
- [x] `test_summary_metadata_marker`（metadata["compacted_summary"]=True 標記寫入）✅
  - DoD：用 MockChatClient 注入；real LLM 不在 unit ✅
  - Verify：`grep "import openai\|import anthropic"` → 0 行 ✅

### 2.5 `HybridCompactor` impl（60 min）
- [x] **建 `compactor/hybrid.py`** ✅
  - 邏輯：先 StructuralCompactor 跑；若 `tokens_after > token_budget * token_threshold_ratio` 仍存在 → 接 SemanticCompactor；若 SemanticCompactor raise SemanticCompactionFailedError → log warning，回 Structural result（標 strategy=HYBRID）✅
  - 注入：`structural: StructuralCompactor` / `semantic: SemanticCompactor` / `token_budget` / `token_threshold_ratio` ✅
  - DoD：implements Compactor ABC；file header 含 fallback 邏輯說明 ✅

### 2.6 `test_compactor_hybrid.py` — 5 tests（30 min）
- [x] `test_structural_sufficient`（structural 後 tokens < threshold → 不跑 semantic；call_count semantic=0）✅
- [x] `test_structural_insufficient_runs_semantic`（structural 不夠 → 接 semantic；total messages_compacted = sum）✅
- [x] `test_semantic_failure_fallback_structural`（_StubSemantic raise SemanticCompactionFailedError → 回 structural result，strategy=HYBRID）✅
- [x] `test_both_fail_emit_warning`（structural triggered=False + semantic raise → caplog.WARNING + triggered=False）✅
- [x] `test_preserves_message_order`（compacted_state messages 順序維持）✅
  - DoD：5 tests pass；`_StubCompactor` + `_StubSemantic` 模擬 structural / semantic 行為 ✅

### 2.7 Loop integration — `agent_harness/orchestrator_loop/loop.py`（90 min）
- [x] **修改 loop 接受 `compactor: Compactor | None = None` 注入**（None 則無 compaction，50.x backward-compat）✅
  - 預設：None（caller 顯式注入 HybridCompactor；DI 容器 Phase 53.x 接通）✅
- [x] **每 turn 開頭（pre-LLM termination 後）build LoopState placeholder + call `await self._compactor.compact_if_needed(state, trace_context=ctx)`** ✅
- [x] **若 result.triggered：messages = result.compacted_state.transient.messages；tokens_used = result.tokens_after** ✅
- [x] **emit `ContextCompacted` event** ✅
  - payload：`tokens_before` / `tokens_after` / `compaction_strategy` / **`messages_compacted` / `duration_ms`**（events.py 同 commit 擴充 2 欄位）✅
- [x] **既有 50.x loop tests 不被破壞** ✅
  - DoD：mypy strict pass（75 source files clean）；50.x loop tests 10/10 PASS ✅
  - Verify：`python -m pytest tests/unit/agent_harness/orchestrator_loop/test_loop.py tests/unit/runtime/workers/test_agent_loop_handler.py -v` → 10/10 PASS ✅

### 2.8 Day 2 commit
- [x] **commit Day 2** ✅
  - Msg：`feat(context-mgmt, sprint-52-1): Day 2 — 3 Compactor strategies + Loop integration + 15 tests`
  - Files：3 compactor impl（structural / semantic / hybrid）+ loop.py edit + 3 test files filled (15 tests) + Message metadata 擴充 (chat.py) + ContextCompacted event +2 fields (events.py) + 17.md Message row sync + checklist updates
  - DoD：mypy strict pass（75 src files clean）；pytest baseline 397 PASS（+15 from Day 1 final 382）；7 skipped（剩餘 Day 3-4 placeholders）；ChatClient 注入無 SDK leak ✅
  - 已知 carry：CARRY-035（test_builtin_tools 2 個 pre-existing failure）仍未處理，Day 4 retro 統一處理 ✅
  - Verify：`grep -r "import openai\|import anthropic" backend/src/agent_harness/context_mgmt/` = 0 ✅

---

## Day 3 — ObservationMasker + JITRetrieval + 3 TokenCounter（估 7h）

### 3.1 `DefaultObservationMasker` impl（45 min）
- [x] **建 `observation_masker.py`** ✅
  - 邏輯：iterate messages；保留所有 `role="assistant"` 的 `tool_calls` 字段；遮蔽超過 `keep_recent` user→assistant turn 的 `role="tool"` 訊息為 `[REDACTED: tool {name} result; bytes={n}]` ✅（cutoff anchor on user message index）
  - 配置：`keep_recent: int = 5`（簽名 method-level，per ABC contract）✅
  - 不影響 `role="user"` / `role="system"` / `role="assistant"`（content 保留）✅
  - DoD：implements ObservationMasker ABC；file header 含 V1 教訓引用（AP-7）✅

### 3.2 `test_observation_masker.py` — 6 tests（30 min）
- [x] `test_12turn_keep_recent_5_redacts_old_intact_recent`（核心 case：12 turn / keep_recent=5 → 0-6 redact / 7-11 intact）✅
- [x] `test_preserves_tool_calls_field`（assistant tool_calls 不動，10 個 assistant 全 verified）✅
- [x] `test_handles_empty_messages`（input [] → output []）✅
- [x] `test_handles_single_turn`（< keep_recent 全保留）✅
- [x] `test_honors_keep_recent_override`（keep_recent=3 行為）✅
- [x] `test_skips_non_tool_messages`（user / system / assistant content 不動）✅
  - DoD：6 tests pass ✅
  - Verify：6/6 PASS ✅

### 3.3 接通 StructuralCompactor → ObservationMasker（30 min）
- [x] **修改 `compactor/structural.py` 注入 `masker: ObservationMasker | None = None`**（default = `DefaultObservationMasker()`）✅
- [x] **替換 inline `_redact_old_tool_results` 邏輯為 `self.masker.mask_old_results()` call**（移除 helper function）✅
- [x] **測試**：6 個 structural tests 仍全 pass ✅
  - DoD：依賴注入 pattern；StructuralCompactor 不再含 inline mask 邏輯 ✅
  - Verify：`python -m pytest test_compactor_structural.py test_observation_masker.py` → 12 pass ✅

### 3.4 `PointerResolver` JITRetrieval impl（45 min）
- [x] **建 `jit_retrieval.py`** ✅
  - 邏輯：parse pointer prefix（`db://` / `memory://` / `tool://` / `kb://`）；52.1 提供 `db://` resolver；其他 raise `JITRetrievalNotSupportedError` ✅
  - `db://` 範例：`db://memory_user/{uuid}?tenant_id={tid}` → mock `db_session.fetch_content(table, row_id, tenant_id)` ✅
  - 注入：`db_session: Any | None = None`（缺則 `db://` 拋 `JITRetrievalConfigError`）✅
  - 多層 tenant 防衛：(a) pointer query 須含 tenant_id，(b) 與 runtime tenant_id 必匹配，(c) 不匹配 raise `PointerTenantMismatchError`，(d) DB 層 fetch 帶 tenant_id filter ✅
  - 額外：`_ALLOWED_DB_TABLES` whitelist 限定 5 個 memory_* tables ✅
  - DoD：implements JITRetrieval ABC；tenant_id filter 強制（multi-tenant safety）✅

### 3.5 `test_jit_retrieval.py` — 4 tests（20 min）
- [x] `test_db_pointer_resolves_with_tenant_filter`（mock _MockDBSession 接收 table/row_id/tenant_id）✅
- [x] `test_unknown_prefix_raises_not_supported`（memory:// / tool:// / kb:// / weird:// 4 cases）✅
- [x] `test_missing_db_session_raises_config_error` ✅
- [x] `test_tenant_id_required_filter_enforced`（red-team 3 cases：missing query / cross-tenant / malformed UUID）✅
  - DoD：4 tests pass；tenant 隔離測試含 ✅
  - Verify：4/4 PASS ✅

### 3.6 `TiktokenCounter` impl（45 min）
- [x] **建 `token_counter/tiktoken_counter.py`** ✅
  - 用 `tiktoken` lib（dep 已在；驗 0.12.0 ready）；自動選 encoding：`gpt-4o* / gpt-5* / o1 / o3 / o4` → `o200k_base`；其他 → `cl100k_base` ✅
  - implements `count(messages, tools)`：iterate messages → count content tokens + role tokens + tool_calls / tool_call_id + tools schema tokens（JSON serialize） ✅
  - implements `accuracy() -> "exact"` ✅
  - **可配置 overhead**（52.1 Day 3.10 修正）：`per_message_overhead` / `per_request_overhead` / `per_tool_overhead` 全可注入；empty input 短路返回 0（adapter 兼容）✅
  - DoD：implements TokenCounter ABC；handle missing tiktoken lib（raise ImportError 帶提示）✅

### 3.7 `test_token_counter_tiktoken.py` — 5 tests（30 min）
- [x] `test_count_plain_text`（empty messages → 0；adapter contract aligned）✅
- [x] `test_count_messages_with_role_overhead`（單訊息 >= 8；2 倍 message → 至少加 4 token）✅
- [x] `test_count_with_tools_schema`（tools serialize 後 +>= 10 tokens）✅
- [x] `test_handles_model_variants`（gpt-4o → o200k_base / gpt-3.5-turbo → cl100k_base）✅
- [x] `test_accuracy_returns_exact`（accuracy() == "exact"）✅
  - DoD：5 tests pass ✅

### 3.8 `ClaudeTokenCounter` impl + 3 tests（45 min）
- [x] **建 `token_counter/claude_counter.py`** ✅
  - 嘗試 import `anthropic.tokenizer.count_tokens`；若失敗 `_ANTHROPIC_COUNTER = None` → fallback 到 4 chars/token approx + tools 30% buffer + accuracy="approximate" ✅
  - 加 `force_approximate=True` constructor flag for tests forcing fallback path ✅
  - DoD：handle import error gracefully ✅
- [x] **`test_token_counter_claude.py` 3 tests** ✅
  - `test_count_via_anthropic_lib_or_fallback`（counter 返回 positive estimate regardless of path） ✅
  - `test_fallback_to_approx_when_lib_missing`（force_approximate=True 路徑 → expected 8 tokens for 16-char content） ✅
  - `test_accuracy_returns_appropriate_value`（monkeypatch _ANTHROPIC_COUNTER 模擬 lib present / missing）✅

### 3.9 `GenericApproxCounter` impl + 3 tests（30 min）
- [x] **建 `token_counter/generic_approx.py`** ✅
  - 邏輯：`ceil(len(text) / 4)` per content；tools schema serialize → `ceil(* 1.3)` buffer ✅
  - implements `accuracy() -> "approximate"` ✅
- [x] **`test_token_counter_generic.py` 3 tests** ✅
  - `test_plain_text_4chars_per_token`（16 char user msg → 8 tokens 精準）✅
  - `test_tools_buffer_adds_30_percent`（schema 序列化後 ceil(× 1.3)）✅
  - `test_accuracy_returns_approximate` ✅

### 3.10 ChatClient adapter `count_tokens()` 路由（30 min）
- [x] **修改 `adapters/azure_openai/adapter.py`** ✅
  - `count_tokens(messages, tools)` → 內部 lazy build `TiktokenCounter(model=..., per_message_overhead=4, per_request_overhead=0)` 並 call `count()` ✅
  - constructor 加 `_token_counter` field（lazy init via `_get_token_counter()`） ✅
  - TYPE_CHECKING import for forward-ref（避免循環 import）✅
  - 不影響 51.1 預留簽名 contract test ✅
  - DoD：existing adapter contract test 仍 pass ✅
  - Verify：`python -m pytest tests/unit/adapters/ -q` → 41/41 PASS ✅

### 3.11 Day 3 commit
- [x] **commit Day 3** ✅
  - Msg：`feat(context-mgmt, sprint-52-1): Day 3 — ObservationMasker + JITRetrieval + 3 TokenCounter + 21 tests`
  - Files：5 src（masker / jit / 3 counter）+ 5 test files filled + adapter.py edit + structural.py edit (3.3) + checklist updates
  - DoD：mypy --strict pass（93 src files clean）；pytest baseline 397 → **418 PASS** (+21 from Day 2)；2 skipped (Day 4 cache_manager)；51.1 adapter 41/41 維持；CARRY-035 仍延後 ✅
  - Verify：`python -m pytest tests/unit/agent_harness/context_mgmt/ -v` → 36 PASS（含 6 structural + 4 semantic + 5 hybrid + 6 masker + 4 jit + 5 tiktoken + 3 claude + 3 generic）✅

---

## Day 4 — PromptCacheManager + 30+ turn e2e + retro + closeout（估 8h）

### 4.1 `InMemoryCacheManager` impl（90 min）
- [ ] **建 `cache_manager.py`**（含 PromptCacheManager ABC + InMemoryCacheManager 同檔）
  - dict-backed key store + per-key expiry timestamp（lazy TTL check on access）
  - key 公式：`hashlib.sha256(f"{tenant_id}:{section_id}:{content_hash}:{provider_signature}".encode()).hexdigest()`
  - methods：
    - `get_cache_breakpoints(tenant_id, policy)` — 根據 policy 5 個 boolean 回對應 CacheBreakpoint list
    - `invalidate(tenant_id, reason)` — 刪所有 keys with prefix `{tenant_id}:`
    - `_check_ttl(key)` — internal lazy expiry
    - `_compute_cache_key(tenant_id, section_id, content_hash, provider)` — hash 公式
  - DoD：implements PromptCacheManager ABC；file header 含 cache key 設計說明 + tenant 隔離保證

### 4.2 `test_cache_manager.py` — 8 tests（含 4 紅隊，60 min）
- [ ] `test_set_and_get_breakpoints`（基本流程）
- [ ] `test_ttl_expiry`（fast-forward time，過期不回傳）
- [ ] `test_invalidate_by_tenant`（invalidate(tenant_a) → tenant_a 全 miss，tenant_b 不影響）
- [ ] **🛡️ red-team 1**：`test_cross_tenant_same_content_no_leak` — tenant_a 寫 + tenant_b 用 same content_hash 查 → cache miss（key 第一段不同）
- [ ] **🛡️ red-team 2**：`test_invalidate_isolation` — invalidate(tenant_a) 不影響 tenant_b 既有 keys
- [ ] **🛡️ red-team 3**：`test_cache_key_includes_tenant_id_first` — assert hash key 算法第一參數必為 tenant_id（lint-style assertion）
- [ ] **🛡️ red-team 4**：`test_provider_signature_isolation` — same tenant 但 provider 不同 → different keys
- [ ] `test_default_cache_policy_5_booleans`（驗證 policy default 值）
  - DoD：8 tests 全 pass；4 紅隊任一 fail = sprint blocker
  - Verify：`python -m pytest backend/tests/unit/agent_harness/context_mgmt/test_cache_manager.py -v`

### 4.3 Cache hit ratio 整合測試（30 min）
- [ ] **建 `tests/integration/agent_harness/context_mgmt/test_cache_hit_ratio_steady_state.py`**
  - 場景：5 turn 同 tenant + user 對話；mock LLM 觸發 cache_breakpoints；穩態量測 cache hit / total request 比率
  - assert：`hit_ratio > 0.5`（穩態 multi-turn）
  - DoD：integration test 走 InMemoryCacheManager + mock LLM
  - Verify：assert log 寫入 hit_ratio 數值

### 4.4 ObservationMasker keep_recent 整合測試（30 min）
- [ ] **建 `tests/integration/agent_harness/context_mgmt/test_observation_masker_keep_recent.py`**
  - 場景：12 turn 通過 Loop + StructuralCompactor → assert tool results redaction 行為（與 unit test 不同：走完整 Loop integration path）
  - DoD：integration 結果與 unit 一致；Loop event 序列含 ContextCompacted

### 4.5 30+ turn no-OOM integration test（45 min）
- [ ] **建 `tests/integration/agent_harness/context_mgmt/test_loop_compaction_30turn.py`**
  - 場景：35 turn 對話；mock LLM 每 turn 回 ~1KB 內容
  - asserts：
    - `token_used` 在 75% 以下 ≥ 95% turns
    - ContextCompacted event 觸發 ≥ 1 次
    - 無 OOM exception
    - turn 35 後 state 仍可序列化（State Mgmt 友好）
  - DoD：deterministic mock；turn-count cap 60 + token-budget cap 100K（hard fail-stop）
  - Verify：log 顯示 compaction trigger 次數 + tokens_before/after

### 4.6 50-turn e2e + verifier 對照（45 min）
- [ ] **建 `tests/e2e/test_long_conversation_50turn.py`**
  - 場景：跑 50 turn with HybridCompactor；對比基準（無 compaction，前 25 turn）的 verifier pass rate
  - 用 MockVerifier（rules-based）+ mock ChatClient
  - assert：compaction 後 verifier pass rate ±5% 對比基準
  - DoD：兩組 run（with/without compaction）；統計差距 < 5%
  - Verify：assert log 顯示 baseline_pass_rate / compacted_pass_rate / delta

### 4.7 SLO 量測補測（30 min）
- [ ] **建 `tests/integration/agent_harness/context_mgmt/test_compaction_latency_slo.py`**
  - 跑 100 次 compaction（不同 strategy）；量 p95 latency
  - asserts：`Structural p95 < 100ms` / `Semantic p95 < 2000ms` / `Hybrid p95 < 2500ms`
  - DoD：3 SLO 全 pass；若 fail 觸發 review + 調策略參數
  - Verify：log 顯示 p50/p95/p99 數值

### 4.8 17.md §4.1 sync（15 min）
- [ ] **更新 `17-cross-category-interfaces.md` §4.1 LoopEvent 表**
  - 找 `ContextCompacted` row → 移除「待 Phase 52.1」備註
  - 標 payload：`tokens_before` / `tokens_after` / `strategy_used` / `duration_ms`
  - DoD：grep 確認備註已移除
  - Verify：`grep -A1 "ContextCompacted" docs/03-implementation/agent-harness-planning/17-cross-category-interfaces.md`

### 4.9 LLM 中性 + 5 V2 lints 驗證（15 min）
- [ ] **`grep -r "import openai\|import anthropic" backend/src/agent_harness/context_mgmt/` → expect 0**
- [ ] **5 V2 lint 全 pass**：
  - `scripts/check_llm_neutrality.py`
  - `scripts/check_cross_category_imports.py`
  - `scripts/check_tenant_isolation.sh`
  - mypy strict
  - flake8
  - DoD：所有 lint 0 violation；結果記入 retrospective.md
  - Verify：`bash scripts/run_all_lints.sh 2>&1 | tee /tmp/52-1-lints.log`

### 4.10 Phase 52 README cumulative table 更新（15 min）
- [ ] **更新 `phase-52-context-prompt/README.md`**
  - 範疇成熟度表：Cat 4 Level 0 → **Level 3** ✅
  - sprint 進度表：52.1 PLANNING → ✅ DONE（含 commits 數 + 完成日期）
  - 範疇成熟度演進表更新（Pre-52.1 → Post-52.1 預計 → 實際）
  - DoD：README 三處表格同步

### 4.11 retrospective.md（45 min）
- [ ] **建 `docs/03-implementation/agent-harness-execution/phase-52/sprint-52-1/retrospective.md`**
  - sections：
    - **Sprint Outcome**（功能交付 + 範疇成熟度躍遷）
    - **估時準度**（plan 31h vs actual Xh = X%；對比 V2 cumulative pattern）
    - **Went Well**（5 條）
    - **Surprises / Improve**（5 條）
    - **Action Items**（每項 owner + due sprint）
    - **CARRY-031..034 確認**
  - 規矩：**禁止寫具體 52.2 day-level task**（rolling 紀律）
  - DoD：5 sections 齊；Action Items 不超 5 條；無預寫未來 sprint task
  - Verify：grep `Day 1\|Day 2` retrospective.md → 應只在 Day 標記實際完成情況，不指未來 sprint

### 4.12 progress.md 更新（15 min）
- [ ] **建 `docs/03-implementation/agent-harness-execution/phase-52/sprint-52-1/progress.md`**
  - Day 1-4 daily entry：時間 / 完成項 / 阻塞 / 教訓
  - DoD：4 day entry 全寫；Day 4 entry 標 closeout
  - Verify：grep `Day [1-4]` progress.md → 4 sections

### 4.13 Sprint closeout commits（30 min）
- [ ] **commit Day 4 closeout impl**
  - Msg：`feat(context-mgmt, sprint-52-1): Day 4 closeout — cache + 30+ turn e2e + retro + Cat 4 Level 3`
  - Files：cache_manager.py + 5 test files（unit + integration + e2e + SLO）+ adapter contract test 確認
- [ ] **更新 `sprint-52-1-checklist.md` 全勾**（除 4.14 🚧）
- [ ] **commit closeout docs**
  - Msg：`docs(phase-52, sprint-52-1): closeout — checklist 全勾 + retrospective 完成 + 17.md §4.1 sync`
  - Files：checklist + retrospective.md + progress.md + Phase 52 README + 17.md
  - DoD：working tree clean；branch ready for merge
  - Verify：`git log --oneline | head -10` 應顯示 7 個 commit（Day 0 + Day 1-4 + 2 closeout）

### 4.14 等用戶 review + merge（🚧 等用戶決策）
- [ ] 🚧 **等用戶選 A merge / B 留 branch / C 進 52.2 plan**
  - 理由：merge 是用戶 own 決策；rolling 紀律不預先 merge

---

## Sprint 完成判斷

**全勾條件**（除 4.14 🚧）：
- Day 0 全 4 group / 7 sub-task ✅
- Day 1 全 9 group ✅
- Day 2 全 8 group（含 15 tests）✅
- Day 3 全 11 group（含 21 tests）✅
- Day 4 全 13 group（含 14 tests + retro + closeout）✅

**測試 baseline 預期**：
- Pre-52.1：142 PASS + 1 platform-skip
- Post-52.1：~205 PASS（+44 unit + +5 integration + +1 e2e + +1 SLO + Loop integration baseline 維持）

**LLM 中性 baseline**：`agent_harness/context_mgmt/**` grep `import openai|import anthropic` = **0**

**範疇成熟度躍遷**：
- Cat 4：Level 0 → **Level 3** ✅
- Cat 1：Level 3（unchanged，加 Loop compactor 整合）
- Cat 12：Level 2（unchanged，加 ContextCompacted span / token_count metric）

---

**Last Updated**：2026-05-01（Day 3 ✅ 11 group 完成 — DefaultObservationMasker + PointerResolver (JIT) + 3 TokenCounter (Tiktoken/Claude/Generic) + StructuralCompactor → ObservationMasker DI + adapter count_tokens() route。mypy strict 93 source files clean / pytest 418 PASS / 0 LLM SDK leak / 51.1 adapter 41/41 維持。CARRY-035 仍延後 Day 4 retro。）
