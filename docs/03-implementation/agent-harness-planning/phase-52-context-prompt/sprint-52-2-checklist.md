# Sprint 52.2 — Checklist：範疇 5 PromptBuilder

**Sprint**：52.2 — Cat 5 Prompt Construction
**Plan**：[`sprint-52-2-plan.md`](./sprint-52-2-plan.md)
**Branch**：`feature/phase-52-sprint-2-cat5-prompt-builder`（Day 1 開）
**Status**：🟡 PLANNING — 待用戶 approve

> **規矩重申**：每項 `[ ]` → `[x]` 一律由 AI 助手在 commit 時即時更新；**未勾選項禁止刪除**（per `feedback_never_delete_unchecked_items` + Phase 42 Sprint 147 教訓）。延後項標 `🚧` + 理由。

---

## Day 0 — Plan + Checklist + Phase 52 README sync（估 2h）

### 0.1 Plan / Checklist 起草
- [x] **建 `phase-52-context-prompt/sprint-52-2-plan.md`**（10 sections §0-9，對齊 52.1 格式）
  - 章節：0 目標 / 1 User Stories / 2 技術設計 / 3 File Change List / 4 DoD / 5 CARRY / 6 Day 估時 / 7 Sprint 結構決策 / 8 風險 / 9 啟動條件
  - DoD：與 52.1 plan 章節結構同（10 sections）
- [x] **建 `phase-52-context-prompt/sprint-52-2-checklist.md`**（本檔）
  - 5-day 結構（Day 0-4）；每 day 子任務含 DoD + Verify command
  - DoD：與 52.1 checklist 細節水平同（每 task 3-6 sub-bullets）

### 0.2 Phase 52 README sync
- [x] **修改 `phase-52-context-prompt/README.md`**（2026-05-01 完成）
  - 52.2 從 `⏸ ROLLING` → `🟡 PLANNING`（待用戶 approve）✅
  - sprint 進度表加 52.2 plan / checklist 連結 ✅
  - Phase 進度：1/2 → 預計 2/2 = 100%（待 closeout）✅
  - 範疇成熟度演進表加 Post-52.2 預計欄位（Cat 5 Level 0 → Level 4）✅
  - 52.1 範圍預覽改為「Sprint 52.1 已交付」（歷史保留）+ 加 §"Sprint 52.2 範圍預覽"（A-G 6 大支柱）✅
  - DoD：mirror `phase-51-tools-memory/README.md` + 52.1 結構 ✅

### 0.3 啟動前環境確認
- [x] **確認 main HEAD `a45fd2f2`（52.1 merge）pushed origin** ✅
  - Cmd：`git log -1 --oneline main` → `a45fd2f2 merge: Sprint 52.1` ✅
  - DoD：local HEAD = remote HEAD ✅
- [x] **確認 49.1 PromptBuilder ABC stub + PromptArtifact 既有 contract** ✅
  - Files：`agent_harness/prompt_builder/_abc.py:31-44`（PromptBuilder.build 簽名 — `state / tenant_id / user_id / trace_context` 4 參數）✅
  - Files：`_contracts/prompt.py:38-45`（PromptArtifact 4 欄位 — `messages / cache_breakpoints / estimated_input_tokens / layer_metadata`）✅
  - Action：Day 1.2 將 ABC 簽名升級（+cache_policy +position_strategy default=None）；保持向後兼容
  - DoD：plan §3 File Change List 已標 _abc.py 為「升級簽名」+ builder.py / strategies/ 為新建 ✅
- [x] **確認 51.2 MemoryRetrieval + 52.1 PromptCacheManager + 52.1 TokenCounter 全 ready** ✅
  - Files：`memory/retrieval.py`（51.2 ship）/ `context_mgmt/cache_manager.py`（52.1 ship）/ `context_mgmt/token_counter/*`（52.1 ship 3 impl）✅
  - DoD：3 依賴全 ship + ABC 穩定；52.2 PromptBuilder 注入無風險 ✅
- [x] **確認 52.1 retrospective Action Items 不阻 52.2 啟動** ✅
  - Read `docs/03-implementation/agent-harness-execution/phase-52/sprint-52-1/retrospective.md`
  - Status：
    - AI-6（grep `_contracts/prompt.py` + Cat 5 既有）→ ✅ Day 0 已完成 — 49.1 stub + PromptArtifact 簽名確認無衝突
    - AI-7（PromptBuilder inject TokenCounter）→ 本 sprint Day 1.6 處理
    - AI-9（ClaudeTokenCounter real anthropic tokenizer）→ Phase 50+；不阻 52.2
    - AI-10（Cat 12 Tracer span for ContextCompacted）→ Phase 53.x；不阻 52.2
    - AI-8（CARRY-035 test_builtin_tools 2 failures）→ Sprint 53.x
  - DoD：5 Action Items 全標 owner + sprint；無一是 52.2 hard blocker ✅

### 0.4 Day 0 commit
- [x] **commit Day 0 docs**
  - Files：3（`sprint-52-2-plan.md` + `sprint-52-2-checklist.md` + `phase-52-context-prompt/README.md` 修改）
  - Msg：`docs(phase-52, sprint-52-2): Day 0 plan + checklist + Phase 52 README rolling switch`
  - Co-author per V2 git-workflow.md
  - DoD：commit message scope = `phase-52, sprint-52-2`；working tree clean（除 pre-existing untracked V2-AUDIT 檔案）
  - Verify：`git log -1 --oneline` 顯示 Day 0 commit

---

## Day 1 — DefaultPromptBuilder + 3 PositionStrategy + templates + ABC 升級 + 17.md §1.1/§2.1 sync（估 6h）

### 1.1 開新 feature branch
- [x] **`git checkout -b feature/phase-52-sprint-2-cat5-prompt-builder`** from main HEAD `a45fd2f2`
  - DoD：`git branch --show-current` = `feature/phase-52-sprint-2-cat5-prompt-builder`
  - Verify：`git log -1 --oneline` 顯示 52.1 merge commit

### 1.2 升級 49.1 PromptBuilder ABC 簽名（30 min）
- [x] **修改 `agent_harness/prompt_builder/_abc.py`**
  - 加 `cache_policy: CachePolicy | None = None` 參數（None → builder 用 default policy）
  - 加 `position_strategy: PositionStrategy | None = None` 參數（None → builder 用 default strategy）
  - keep 既有 `state / tenant_id / user_id / trace_context` 簽名 + 順序
  - import：`from agent_harness._contracts import CachePolicy`（52.1 ship）+ `from agent_harness.prompt_builder.strategies import PositionStrategy`（1.3 後）
  - DoD：mypy --strict pass；既有 49.1 stub 49.1 callers（無）不破壞
  - Verify：`python -m mypy backend/src/agent_harness/prompt_builder --strict` → Success

### 1.3 建 `prompt_builder/strategies/` 目錄 + ABC（30 min）
- [x] **建 `prompt_builder/strategies/__init__.py`**（package marker，re-export PositionStrategy + 3 concrete + PromptSections）
- [x] **建 `prompt_builder/strategies/_abc.py`**
  - `PromptSections` dataclass（frozen=True）：`system: Message / tools: list[ToolSpec] / memory_layers: dict[MemoryLayer, list[MemoryHint]] / conversation: list[Message] / user_message: Message`
  - `PositionStrategy` ABC：`def arrange(self, sections: PromptSections) -> list[Message]`（純 stateless 重排函式，不做 IO）
  - DoD：file header 完整；mypy strict pass

### 1.4 建 3 PositionStrategy concrete impl（90 min）
- [x] **建 `prompt_builder/strategies/naive.py`**
  - `NaiveStrategy.arrange()`：order = `[system, tools, memory(flatten), conversation, user]`
- [x] **建 `prompt_builder/strategies/lost_in_middle.py`**
  - `LostInMiddleStrategy.arrange()`：order = `[system, user_echo, tools, memory_summary, ...mid_history..., recent_assistant, user_actual]`
  - `user_echo`：在首段以 `role="system"` 短摘要形式 echo（避免重複真 user message）
  - 中段保留：所有 user/assistant turn except 最後 `recent_assistant_count: int = 3` 個
- [x] **建 `prompt_builder/strategies/tools_at_end.py`**
  - `ToolsAtEndStrategy.arrange()`：order = `[system, memory(flatten), conversation, user, tools]`
  - tools 在 `messages` 末尾以特殊 `role="system"` content 形式攜帶（adapter 層處理 detach）
  - DoD：3 strategies 全 implements PositionStrategy ABC；mypy strict pass

### 1.5 建 `prompt_builder/templates.py`（30 min）
- [x] **建 `templates.py`**
  - `SYSTEM_ROLE_TEMPLATE`：常數模板（agent role + capabilities + safety guidelines）
  - `MEMORY_SECTION_HEADER`：`"=== {layer} Memory ({time_scale}) ==="` 格式
  - `MEMORY_HINT_FORMAT`：`"- [{score:.2f}] {content}"`
  - `format_memory_section(layer, time_scale, hints) -> str` helper
  - DoD：純 stateless function；無 IO；mypy strict pass

### 1.6 建 `prompt_builder/builder.py` DefaultPromptBuilder（雛形 + 範疇 12 埋點；90 min）
- [x] **建 `builder.py`**
  - `class DefaultPromptBuilder(PromptBuilder)`：constructor 接受 7 個 DI（`memory_retrieval` / `cache_manager` / `token_counter` / **`tracer: Tracer`** / `default_strategy: PositionStrategy = LostInMiddleStrategy()` / `default_cache_policy: CachePolicy = CachePolicy()` / `templates: dict | None = None`）
  - `async def build(state, tenant_id, ..., trace_context=None)` 雛形（Day 1 不接 memory / cache，只跑 system + tools + conversation + user 4 層組裝 + PositionStrategy 重排 + token estimation）
  - **🔴 W3-2 carryover**：build() 入口 `tracer.start_span("prompt_builder.build", parent_span_id=..., attributes={"tenant_id": ...})` + 結束時 `record_metric("prompt_builder_build_duration_seconds")`
  - **🔴 W3-2 carryover**：build() 內部建 child `TraceContext`（trace_id 沿用 / span_id 新建 / parent_span_id 接上層 / tenant_id+user_id propagate）
  - `_build_system_section(state, tenant_id) -> Message`：用 `SYSTEM_ROLE_TEMPLATE`
  - `_build_tools_section(tools) -> list[ToolSpec]`：直接 passthrough
  - **暫 stub**：`_inject_memory_layers(..., trace_context=child_ctx)` 回 empty dict（Day 2 接通）
  - **暫 stub**：`_build_cache_breakpoints(..., trace_context=child_ctx)` 回 empty list（Day 2 接通）
  - `PromptArtifact.layer_metadata["trace_id"] = child_ctx.trace_id` 寫入（前端 SSE 串連用）
  - DoD：DefaultPromptBuilder 可 build 出 PromptArtifact；mypy strict pass；file header 含 AP-8 + W3-2 carryover 引用

### 1.7 17.md §1.1 + §2.1 sync（45 min）
- [x] **更新 `17-cross-category-interfaces.md` §1.1**
  - 加 row：`PromptSections` — Cat 5，DefaultPromptBuilder 內部 dataclass（5 欄位）
  - 加 row：`PositionStrategy` — Cat 5，ABC for prompt section 重排
  - 改 row：`PromptArtifact`（既有 L57）— 加 `layer_metadata` keys 註明：`memory_layers_used / position_strategy / cache_sections`
  - 同步 §1.3 file layout：加 `strategies/_abc.py` + `strategies/{naive,lost_in_middle,tools_at_end}.py` + `builder.py` + `templates.py`
  - DoD：grep 確認 4 type 列入；single-source 規則維持
- [x] **更新 `17-cross-category-interfaces.md` §2.1**
  - 改 row：`PromptBuilder`（既有 L129）— 簽名升級 `build(state, tenant_id, user_id, cache_policy, position_strategy, trace_context) -> PromptArtifact`
  - 加 row：`PositionStrategy` — Cat 5，方法 `arrange(sections) -> list[Message]`
  - DoD：grep 確認 PromptBuilder + PositionStrategy 列入

### 1.8 18 unit tests（Day 1 部分填寫；75 min）
- [x] **建 `tests/unit/agent_harness/prompt_builder/test_strategies_naive.py`** — 3 tests
  - `test_order_system_first` / `test_tools_after_system` / `test_user_at_end`
- [x] **建 `test_strategies_lost_in_middle.py`** — 5 tests
  - `test_system_at_idx_0` / `test_user_echo_at_idx_1` / `test_user_actual_at_last` / `test_tools_after_user_echo` / `test_recent_assistant_count_3`
- [x] **建 `test_strategies_tools_at_end.py`** — 3 tests
  - `test_system_first` / `test_tools_at_last` / `test_user_before_tools`
- [x] **建 `test_builder_basic.py`** — 4 tests
  - `test_build_returns_prompt_artifact` / `test_default_strategy_lost_in_middle` / `test_default_cache_policy` / `test_layer_metadata_keys`
- [x] **建 `test_templates.py`** — 3 tests
  - `test_system_role_template_format` / `test_memory_section_header` / `test_format_memory_section`
- [x] 其他 6 test files 建占位（@pytest.mark.skip）：`test_builder_memory_injection.py` / `test_builder_cache_integration.py` / `test_builder_position_strategy.py` / `test_builder_token_estimation.py` / `test_lint_rule.py` / `test_anthropic_mock_adapter.py`
  - DoD：18 tests collect succeed；Day 1 fill 18（3+5+3+4+3）；6 placeholder skipped
  - Verify：`python -m pytest backend/tests/unit/agent_harness/prompt_builder/ -v` → 18 PASS + ~30 skipped

### 1.9 Day 1 commit
- [x] **commit Day 1**
  - Msg：`feat(prompt-builder, sprint-52-2): Day 1 — DefaultPromptBuilder + 3 strategies + templates + ABC upgrade + 18 tests`
  - Files：6 new src（builder + 3 strategies + strategies/_abc + templates）+ 1 edit（_abc.py upgrade）+ 11 test files（5 filled / 6 placeholder）+ 17.md §1.1/§2.1 sync + plan + checklist
  - DoD：mypy --strict pass；pytest 18 PASS（new）+ 434 PASS（baseline 維持）；51.1 adapter 41/41；50.x loop 10/10；LLM SDK leak 0
  - Verify：`grep -r "import openai\|import anthropic" backend/src/agent_harness/prompt_builder/` = 0

---

## Day 2 — Memory 5×3 真注入 + CacheBreakpoint 整合 + 紅隊測試（估 8h）

### 2.1 `_inject_memory_layers` impl + trace propagation（60 min）
- [x] **修改 `prompt_builder/builder.py`**
  - 實作 `async def _inject_memory_layers(tenant_id, user_id, query, *, trace_context: TraceContext | None = None) -> dict[MemoryLayer, list[MemoryHint]]`
  - 邏輯：call `await self._memory_retrieval.retrieve(tenant_id=tenant_id, user_id=user_id, query=query, top_k=10, trace_context=trace_context)` → 拿 `MemoryHint` list → 按 layer + time_scale 排序
  - **🔴 W3-2 carryover**：`trace_context` 沿鏈傳給 `memory_retrieval.retrieve()`（不可斷裂）
  - **🔴 W1-2 + W3-2 carryover**：`tenant_id` 強制必傳；**禁止** 在 PromptBuilder 內加任何 process-wide / class-level / module-level mutable cache 跨 tenant
  - 排序 key：`TIME_SCALE_PRIORITY = {permanent: 0, quarterly: 1, daily: 2}`（permanent 在前）
  - 失敗處理：`MemoryRetrievalError` → log warning + return empty dict（降級為 system + tools + conversation only）
  - DoD：implements 完整 logic；file header 含 AP-7 / Tenant 隔離 / W3-2 trace propagation 說明

### 2.2 `test_builder_memory_injection.py` — 8 tests（含 4 紅隊；75 min）
- [x] `test_5_layers_all_injected`（mock retrieval 回 5 layer hints → all 出現在 artifact）
- [x] `test_3_time_scales_ordered_permanent_first`（permanent / quarterly / daily 依序）
- [x] `test_memory_retrieval_failure_degrades_gracefully`（mock 拋 MemoryRetrievalError → artifact 仍可 build；layer_metadata["memory_layers_used"] = []）
- [x] `test_layer_metadata_records_used_layers`（layer_metadata["memory_layers_used"] 含 list of layer names）
- [x] **🛡️ red-team 1**：`test_cross_tenant_no_leak`（tenant_a memory 寫入 InMemoryStore；tenant_b PromptBuilder.build → grep tenant_a content in artifact = 0）
- [x] **🛡️ red-team 2**：`test_cross_user_no_leak`（user_a tenant_a memory 寫入；user_b tenant_a build → user-scoped memory 不含）
- [x] **🛡️ red-team 3**：`test_cross_session_no_leak`（session_a memory；session_b build → session-scoped memory 不含）
- [x] **🛡️ red-team 4**：`test_expired_time_scale_filtered`（daily memory 過期；build → 不再注入）
  - DoD：8 tests pass；4 red-team 全綠；no real DB；用 51.2 InMemoryStore + 預灌 fixture
  - Verify：`python -m pytest test_builder_memory_injection.py -v` → 8/8 PASS

### 2.3 `_build_cache_breakpoints` impl + trace propagation（60 min）
- [x] **修改 `prompt_builder/builder.py`**
  - 實作 `async def _build_cache_breakpoints(tenant_id, policy, sections, *, trace_context: TraceContext | None = None) -> list[CacheBreakpoint]`
  - 邏輯：call `await self._cache_manager.get_cache_breakpoints(tenant_id=tenant_id, policy=policy, trace_context=trace_context)` → 拿 breakpoint hints → 對每個 hint 補 logical metadata（content_hash via sha256）
  - **🔴 W3-2 carryover**：`trace_context` 沿鏈傳給 `cache_manager.get_cache_breakpoints()`（不可斷裂）
  - 對應：`section_id="system"` → hash sections.system.content；`section_id="tools"` → hash json.dumps(sections.tools)；`section_id="memory_*"` → hash 對應 layer hints
  - DoD：implements 完整 logic；layer_metadata["cache_sections"] 記錄 section_id list；trace propagation 落地

### 2.4 `test_builder_cache_integration.py` — 5 tests（45 min）
- [x] `test_default_policy_3_breakpoints`（system + tools + memory → 3 breakpoints）
- [x] `test_cache_recent_turns_disabled_default`（default policy 不含 recent turns breakpoint）
- [x] `test_content_hash_deterministic`（同 sections build 兩次 → 同 content_hash）
- [x] `test_layer_metadata_cache_sections`（layer_metadata["cache_sections"] = ["system", "tools", "memory"]）
- [x] `test_cache_manager_failure_degrades`（mock cache_manager 拋例外 → cache_breakpoints=[] + artifact 仍 build）
  - DoD：5 tests pass

### 2.5 `test_builder_position_strategy.py` + `test_builder_token_estimation.py` — 6 tests（45 min）
- [x] **`test_builder_position_strategy.py`** — 3 tests
  - `test_default_lost_in_middle` / `test_override_to_naive` / `test_override_to_tools_at_end`
- [x] **`test_builder_token_estimation.py`** — 3 tests
  - `test_token_count_called` / `test_estimated_tokens_in_artifact` / `test_token_counter_failure_zero`

### 2.6 5×3 矩陣 integration test — **real PostgreSQL via docker**（90 min；W3-2 carryover）
- [x] **建 `tests/integration/agent_harness/prompt_builder/test_memory_5x3_matrix.py`**
  - **🔴 W3-2 + testing.md carryover**：用 **real PostgreSQL via docker fixture**（asyncpg + docker postgres，per `.claude/rules/testing.md` + `multi-tenant-data.md`）— **不用 SQLite，不用 InMemoryStore**
  - 預灌 13 cell fixture（system 永久 / tenant 永久+季 / role 永久+季 / user 永久+季+天 / session 天 + 額外組合）via real PG insert with tenant_id NOT NULL + RLS active
  - 用 51.2 PostgresMemoryStore + 52.1 InMemoryCacheManager（cache 可 in-memory，因 51.2 cache infra 未 ship）+ 52.1 TiktokenCounter
  - **🛡️ 紅隊驗證**：跑紅隊 case（tenant_a row 寫入 PG → tenant_b PromptBuilder.build via 同一 PG connection → 0 leak via RLS）
  - assert：13 cell 全 covered；layer_metadata["memory_layers_used"] 含全 5 layer；trace_id 正確 propagate
  - DoD：integration 走 real PG ABCs；conftest fixture 用 docker-compose 起 postgres 並 teardown；mock LLM 不需要（build 是 deterministic）
  - Verify：`pytest tests/integration/agent_harness/prompt_builder/test_memory_5x3_matrix.py -v` → 1 PASS + RLS isolation 驗證

### 2.7 17.md sync 補強（15 min）
- [x] **更新 `17-cross-category-interfaces.md` §1.1 PromptArtifact row**
  - layer_metadata keys 註明完整：`memory_layers_used / position_strategy / cache_sections`
  - DoD：grep 確認 3 keys 列入

### 2.8 Day 2 commit
- [x] **commit Day 2**
  - Msg：`feat(prompt-builder, sprint-52-2): Day 2 — Memory 5×3 + CacheBreakpoint integration + 22 tests (4 red-team)`
  - Files：builder.py edit（_inject + _build_cache_breakpoints）+ 4 test files filled + 1 integration + 17.md sync
  - DoD：mypy strict pass；pytest 22 new + 18 Day 1 + 434 baseline = 474 PASS；4 red-team 全綠；LLM SDK leak 0
  - Verify：`grep -r "import openai\|import anthropic" backend/src/agent_harness/prompt_builder/` = 0

---

## Day 3 — Loop integration + Anthropic mock adapter + Azure OpenAI cache_key + adapter edits（估 7h）

### 3.1 Loop integration — `agent_harness/orchestrator_loop/loop.py`（90 min）
- [x] **修改 loop 接受 `prompt_builder: PromptBuilder | None = None` 注入**（None 則 fallback 50.x 邏輯，backward-compat）
- [x] **每 turn 開頭（compactor 之後）build artifact**：
  - `if self._prompt_builder is not None: artifact = await self._prompt_builder.build(state=state, tenant_id=..., user_id=..., trace_context=ctx)`
  - `messages = artifact.messages`；`cache_breakpoints = artifact.cache_breakpoints`
- [x] **替換既有 ad-hoc `messages = state.transient.messages.copy()` 組裝**為 artifact-based
- [x] **call ChatClient 時傳 cache_breakpoints**：`chat(messages=artifact.messages, tools=tools, cache_breakpoints=artifact.cache_breakpoints, ...)`
- [x] **emit `PromptBuilt` event**（payload 完整：messages_count / estimated_input_tokens / cache_breakpoints_count / memory_layers_used / position_strategy_used / duration_ms）
- [x] **既有 50.x loop tests 不被破壞**（prompt_builder=None default）
  - DoD：mypy strict pass；50.x loop tests 10/10 PASS（backward-compat）
  - Verify：`python -m pytest tests/unit/agent_harness/orchestrator_loop/test_loop.py -v` → 10/10 PASS

### 3.2 50.x backward-compat 驗證（15 min）
- [x] **跑 50.x loop tests + 52.1 30-turn integration**
  - `python -m pytest tests/unit/agent_harness/orchestrator_loop/ tests/integration/agent_harness/context_mgmt/test_loop_compaction_30turn.py -v`
  - DoD：100% pass（10 + 1 = 11 tests）；30-turn baseline 不退化

### 3.3 events.py PromptBuilt event 完整 payload（15 min）
- [x] **修改 `agent_harness/_contracts/events.py`**
  - PromptBuilt event payload schema：`messages_count: int / estimated_input_tokens: int / cache_breakpoints_count: int / memory_layers_used: list[str] / position_strategy_used: str / duration_ms: float`
  - DoD：mypy strict pass；既有 PromptBuilt event(stub) 不破壞

### 3.4 建 Anthropic mock adapter（60 min）
- [x] **建 `adapters/_mock/anthropic_adapter.py`**
  - `class MockAnthropicAdapter(ChatClient)`：test-only mock；**不 import anthropic SDK**（純 stub 用於 contract test）
  - `chat(messages, tools, cache_breakpoints=None, ...)` → 在對應 `messages[bp.position]` 注入 `cache_control: {"type": "ephemeral"}` 欄位（dict mutation in copy）
  - 回 `ChatResponse`（mock content="OK"）
  - DoD：implements ChatClient ABC；file header 標 test-only + 不 import anthropic
  - Verify：`grep "import anthropic" backend/src/adapters/_mock/anthropic_adapter.py` = 0

### 3.5 Azure OpenAI adapter cache_key 注入（45 min）
- [x] **修改 `adapters/azure_openai/adapter.py`**
  - `chat(...)` 簽名加 `cache_breakpoints: list[CacheBreakpoint] | None = None`
  - 邏輯：`if cache_breakpoints: prompt_cache_key = sha256(":".join([bp.section_id for bp in cache_breakpoints if bp.section_id])).hexdigest()`
  - 傳給 `client.chat.completions.create(..., extra_body={"prompt_cache_key": prompt_cache_key})`
  - 51.1 baseline 維持（adapter contract 41/41）
  - DoD：mypy strict pass；51.1 adapter 41/41 PASS

### 3.6 mock_clients.py 接收 cache_breakpoints（15 min）
- [x] **修改 `adapters/_testing/mock_clients.py`**
  - `MockChatClient.chat()` 簽名加 `cache_breakpoints: list[CacheBreakpoint] | None = None`
  - 記錄到 `self.last_call_cache_breakpoints`（test 用 assertion）
  - DoD：既有 mock 用法不破壞

### 3.7 `test_anthropic_mock_adapter.py` — 4 tests（30 min）
- [x] `test_chat_returns_response`（基本 contract）
- [x] `test_cache_control_marker_injected`（cache_breakpoints=[bp1] → messages[bp1.position] 含 cache_control）
- [x] `test_no_breakpoints_no_marker`（cache_breakpoints=None → messages 無 cache_control）
- [x] `test_does_not_import_anthropic_sdk`（grep file content = 0 anthropic imports）
  - DoD：4 tests pass

### 3.8 `test_loop_with_prompt_builder.py` integration（60 min）
- [x] **建 `tests/integration/agent_harness/prompt_builder/test_loop_with_prompt_builder.py`**
  - 用 MockChatClient + DefaultPromptBuilder（注入 InMemoryStore + InMemoryCacheManager + TiktokenCounter）
  - 跑 5 turn 對話；assert：
    - 每 turn 都有 PromptBuilt event emit
    - `MockChatClient.last_call_cache_breakpoints` 非空（至少 3 breakpoints）
    - layer_metadata["memory_layers_used"] 隨 turn 增加（session memory accumulate）
  - DoD：1 integration test pass

### 3.9 Day 3 commit
- [x] **commit Day 3**
  - Msg：`feat(prompt-builder, sprint-52-2): Day 3 — Loop integration + Anthropic mock + Azure cache_key + 5 tests`
  - Files：loop.py edit + events.py edit + _mock/anthropic_adapter.py + adapters/azure_openai/adapter.py edit + mock_clients.py edit + 1 unit test file（4 tests）+ 1 integration
  - DoD：mypy strict pass；pytest 5 new + 22 Day 2 + 18 Day 1 + 434 baseline = 479 PASS；50.x loop 10/10；51.1 adapter 41/41；LLM SDK leak 0
  - Verify：`grep -r "import openai\|import anthropic" backend/src/agent_harness/prompt_builder/ backend/src/adapters/_mock/` = 0

---

## Day 4 — AP-8 lint rule + 100% 主流量 e2e + SLO 量測 + retro + closeout（估 8h）

### 4.1 AP-8 lint rule 寫 `scripts/check_promptbuilder_usage.py`（90 min）
- [x] **建 `scripts/check_promptbuilder_usage.py`**
  - AST-based lint：iterate `agent_harness/**/*.py`；對每個 `chat_client.chat(...)` / `chat_client.stream(...)` call 檢查同 function scope 是否有 prior `prompt_builder.build(...)` call
  - allowlist：`tests/**` / `**/_testing/**` / `**/contract_test_*.py` / `scripts/check_promptbuilder_usage.py`（self-exempt）
  - 違規時：print 違規 file:line + raise SystemExit(1)
  - 提供 `--dry-run` flag（warning only，不 fail）
  - DoD：script executable；help message 完整
  - Verify：`python scripts/check_promptbuilder_usage.py --dry-run` → 列出違規（預期 0 violations after Day 3 Loop integration）

### 4.2 `test_lint_rule.py` — 5 tests（45 min）
- [x] `test_detects_chat_without_build`（fixture file 含 chat() 但無 build() → SystemExit(1)）
- [x] `test_allows_chat_with_prior_build`（fixture file 含 build() → chat() → exit 0）
- [x] `test_allowlist_tests_directory`（test_*.py 內 chat() 無 build() → exit 0）
- [x] `test_allowlist_mock_clients`（_testing/mock_clients.py → exit 0）
- [x] `test_dry_run_no_exit`（--dry-run + violation → 不 SystemExit）
  - DoD：5 tests pass

### 4.3 100% 主流量 e2e（45 min）
- [x] **建 `tests/e2e/test_main_flow_via_prompt_builder.py`**
  - 全鏈路：API request → AgentLoop（with PromptBuilder）→ MockChatClient → output parser → response
  - assert：
    - 每個 LLM call 之前 PromptBuilt event 都 emit
    - `MockChatClient.last_call_messages` 與 PromptArtifact.messages 一致
    - cache_breakpoints 從 builder 傳到 adapter
  - DoD：1 e2e pass；驗證 100% 主流量透過 PromptBuilder

### 4.4 SLO 量測 + tracer span 驗證（60 min；W3-2 carryover）
- [x] **建 `tests/integration/agent_harness/prompt_builder/test_slo_latency.py`**
  - 量 PromptBuilder.build() p50 / p95 / p99（100 次跑；含 memory injection + cache breakpoint generation）
  - assert：p95 < 50ms（mock memory_retrieval / cache_manager / token_counter）
  - 量 LostInMiddleStrategy 位置精準度（50 個 mock prompt → assert system idx==0 + user 在 last + first echo present）
  - assert：精準度 100%（50/50）
  - **🔴 W3-2 carryover**：用 `capture_spans()` context manager 收 100 次 build() 的 tracer spans；assert：
    - 100 個 `prompt_builder.build` span emit
    - 每個 span 有 child spans（memory_retrieval / cache_manager 至少各 1）
    - trace_id 沿鏈一致（root→child 同 trace_id）
    - `prompt_builder_build_duration_seconds` metric emit count = 100
  - DoD：3 SLO assertions + 4 tracer assertions all pass；log p50/p95/p99 / 精準度 / span count 數值

### 4.5 Cache hit steady state integration（30 min）
- [x] **建 `tests/integration/agent_harness/prompt_builder/test_cache_hit_steady_state.py`**
  - 5 turn 同 tenant + user 對話；用 InMemoryCacheManager
  - 每 turn 量 cache hit ratio（從 cache_manager.cache_size / total accesses）
  - assert：穩態 hit > 50%（turn 3-5 平均）
  - DoD：1 integration pass

### 4.6 17.md §4.1 PromptBuilt event sync（15 min）
- [x] **更新 `17-cross-category-interfaces.md` §4.1 LoopEvent 表**
  - PromptBuilt row：移除「待 Phase 52.2」備註；payload schema 完整：`messages_count / estimated_input_tokens / cache_breakpoints_count / memory_layers_used / position_strategy_used / duration_ms`
  - DoD：grep 確認 PromptBuilt row 含完整 payload 文字

### 4.7 LLM 中性 + 5 V2 lints 驗證（15 min）
- [x] **`grep -r "import openai\|import anthropic" backend/src/agent_harness/prompt_builder/` → 0 actual imports**
- [x] **`grep -r "import openai\|import anthropic" backend/src/adapters/_mock/` → 0**（mock anthropic adapter 不能 import 真 SDK）
- [x] **5 V2 lints 全 pass**：
  - `mypy --strict src/agent_harness src/adapters` → all clean
  - `flake8 src/agent_harness/prompt_builder src/adapters/_mock --max-line-length=120` → 0 violations
  - LLM neutrality（手動 grep）→ 0 leak
  - 51.1 adapter contract baseline → 41/41 PASS
  - 50.x loop baseline → 10/10 PASS
  - **AP-8 lint rule**：`python scripts/check_promptbuilder_usage.py` → 0 violations
  - DoD：所有 lint 0 violation；結果記入 retrospective.md

### 4.8 Phase 52 README cumulative table 更新（15 min）
- [x] **更新 `phase-52-context-prompt/README.md`**
  - 範疇成熟度表：Cat 5 Level 0 → **Level 4** ✅（達成）
  - sprint 進度表：52.2 PLANNING → ✅ DONE（commits 預期 5-6 + 完成日期 2026-05-XX）
  - Phase 52 進度：1/2 → **2/2 = 100%** ✅
  - V2 cumulative：10/22 → **11/22 = 50%** ✅
  - 加 5 條 Cat 5 Level 4 核心驗收結果 bullet
  - DoD：README 三處表格同步 + Last Updated bumped

### 4.9 retrospective.md + Audit Debt 必填段落（60 min；W3 process 修補）
- [x] **建 `docs/03-implementation/agent-harness-execution/phase-52/sprint-52-2/retrospective.md`**
  - **9 sections**（含 W3 carryover 強制段）：Outcome / 估時準度 / Went Well 5 / Surprises 5 / Action Items 5 / CARRY 確認 / 驗收檢查 / 紀律自檢 / **🔴 NEW Audit Debt（W3 process 修補）**
  - **Audit Debt 段必答**（per plan §10.3）：
    1. 是否守住 §10.2 跨切面紀律？任何砍 scope 透明列出
    2. §10.1 4 P0 cleanup sprint 進度（GitHub issue / sprint plan 連結）
    3. 本 sprint 過程發現新 audit findings？
    4. Process 修補進度（template 改 / GitHub issue / monthly review）
  - 規矩：禁止寫具體 53.1 day-level task — Action Items 全標 owner + sprint
  - DoD：9 sections 齊；Action Items ≤ 5 條；Audit Debt 段 4 問全答；無預寫未來 sprint task

### 4.10 progress.md 建（15 min）
- [x] **建 `docs/03-implementation/agent-harness-execution/phase-52/sprint-52-2/progress.md`**
  - Day 0-4 daily entry：5 day；每天時間 / 完成項 / Verification / Blockers / Lessons
  - Day 4 entry 標 Closeout
  - DoD：5 day entry 全寫；Day 4 標 closeout

### 4.11 Sprint closeout commits（30 min）
- [x] **commit Day 4 closeout impl**
  - Msg：`feat(prompt-builder, sprint-52-2): Day 4 closeout — AP-8 lint + e2e + SLO + Cat 5 Level 4`
  - Files：scripts/check_promptbuilder_usage.py + test_lint_rule.py + e2e + SLO integration + cache hit integration
- [x] **更新 `sprint-52-2-checklist.md` 全勾**（除 4.12 🚧）
- [x] **commit closeout docs**
  - Msg：`docs(phase-52, sprint-52-2): closeout — checklist 全勾 + retrospective + 17.md §4.1 sync + Phase 52 收尾`
  - Files：checklist + retrospective.md + progress.md + Phase 52 README + 17.md §4.1
  - DoD：working tree clean；branch ready for merge
  - Verify：`git log --oneline | head -10` 應顯示 6 commits on branch（Day 0 + Day 1-3 + Day 4 closeout impl + Day 4 closeout docs）

### 4.12 等用戶 review + merge（🚧 等用戶決策）
- [ ] 🚧 **等用戶選 A merge / B 留 branch / C 進 53.1 plan**
  - 理由：merge 是用戶 own 決策；rolling 紀律不預先 merge

---

## Sprint 完成判斷

**全勾條件**（除 4.12 🚧）：
- Day 0 全 4 group / 7 sub-task
- Day 1 全 9 group（含 18 tests）
- Day 2 全 8 group（含 22 tests + 4 red-team）
- Day 3 全 9 group（含 5 tests + Loop integration）
- Day 4 全 12 group（含 lint rule + e2e + SLO + retro + closeout）

**測試 baseline 預期**：
- Pre-52.2：434 PASS / 1 skipped / 2 pre-existing failures (CARRY-035)
- Post-52.2：~480 PASS（+45 unit + +3 integration + +1 e2e + +1 SLO）

**LLM 中性 baseline**：
- `agent_harness/prompt_builder/**` grep `import openai|import anthropic` = **0**
- `adapters/_mock/anthropic_adapter.py` grep `import anthropic` = **0**

**範疇成熟度躍遷**：
- Cat 5：Level 0 → **Level 4** ✅
- Cat 1：Level 3（unchanged，加 Loop PromptBuilder integration）
- Cat 12：Level 2（unchanged，加 PromptBuilt event payload；Tracer span 留 Phase 53.x per 52.1 AI-10）

**Phase 52 收尾**：
- Phase 52 進度：1/2 → **2/2 = 100%** ✅
- V2 cumulative：10/22 → **11/22 = 50%** ✅（半程里程碑）

---

**Last Updated**：2026-05-01（Sprint 52.2 ⭕ PLANNING — Day 0 plan + checklist 起草中；待用戶 approve 後啟動 Day 1）
