# Sprint 50.2 Progress

**Branch**: `feature/phase-50-sprint-2-api-frontend`
**Plan**: [`../../../agent-harness-planning/phase-50-loop-core/sprint-50-2-plan.md`](../../../agent-harness-planning/phase-50-loop-core/sprint-50-2-plan.md)
**Checklist**: [`../../../agent-harness-planning/phase-50-loop-core/sprint-50-2-checklist.md`](../../../agent-harness-planning/phase-50-loop-core/sprint-50-2-checklist.md)
**Started**: 2026-04-30

---

## Day 0 — 2026-04-30

### 預計 vs 實際

| Step | Plan | Actual | Notes |
|------|------|--------|-------|
| 0.1 確認 50.1 closeout 狀態 | 5 min | ~3 min | Branch `feature/phase-50-sprint-1-loop-core` HEAD = `92c8fd4`，working tree clean except user IDE 編輯的 V2-AUDIT-* / discussion-log（unrelated） |
| 0.2 拉新 sprint branch | 5 min | ~1 min | `git checkout -b feature/phase-50-sprint-2-api-frontend` 一次成功；graphify post-checkout hook 觸發但非阻斷 |
| 0.3 commit plan + checklist | 5 min | ~3 min | commit `6de7aed` — 754 insertions（plan ~360 / checklist ~280） |
| 0.4 Phase 50 README 標 in-progress | 5 min | ~3 min | commit `80c9295` — 4 處編輯（header / 進度表 / 結構表 / Last Updated） |
| 0.5 CARRY-001 testing.md rule | 5 min | ~2 min | 加 §Critical block + 改 commands `pytest` → `python -m pytest`，引用 50.1 retro 出處 |
| 0.6 CARRY-002 events.py fix | 5 min | ~3 min | `from datetime import UTC, datetime` + `default_factory=lambda: datetime.now(UTC)` + Modification History entry |
| 0.7 commit CARRY trivia | 5 min | ~2 min | commit `80338f0` — 2 檔（testing.md / events.py） |
| **Day 0 總計** | **30 min** | **~17 min（57%）** | 比 plan 快，符合 Phase 50 整體 19% pattern |

### Verification

- ✅ pytest `tests/unit/agent_harness/orchestrator_loop/` **17 PASS / 0 warnings**（事前 28+ DeprecationWarning 全消）
- ✅ events.py mypy strict 仍通過（純 default_factory 替換，型別無變）
- ✅ Branch state：3 commits ahead of 50.1 HEAD = 13 commits ahead of `feature/phase-50-sprint-1-loop-core`

### Surprises / Decisions

1. **Working tree dirty** at branch cut — 用戶 IDE 編輯的 `V2-AUDIT-*.md`（8 檔）+ `discussion-log-20260429.md` + `agent-harness-checking-log-20260429.md` 都是用戶平行工作，不屬於 50.2 sprint 範圍。`git checkout -b` 自動 carry over（untracked / modified 都不會丟）。**決策**：50.2 commits 只 stage 50.2 相關檔案（明確 path），不用 `git add -A`，符合 git-workflow.md。
2. **graphify post-checkout / post-commit hook 噪音**：每次 commit 都 trigger 一次 3890 file AST extraction，生成 ~75K node graph 但因 size 太大 viz fail。**非阻斷**，commit 還是成功。觀察記在這裡，不在 50.2 處理（屬 graphify scope）。
3. **commit 結構與 plan 微調**：plan 寫 5 commits，actual 3 commits（plan/checklist 1 + README 1 + CARRY-001+002 合併 1）— CARRY-001（rule doc）+ CARRY-002（code fix）放同一 commit 合理因為都是 50.1 retro carry-forward，scope mixed 但 "trivia" 標籤清楚。如果後續發現需要拆，rebase fixup 即可。

### Next Day (Day 1)

- 主題：API 層（`api/v1/chat/{router,sse,schemas,handler,session_registry}.py`）+ ~15 unit tests
- Plan 6h；預估 actual ~70-80 min（per 19% 比率）
- Pre-work：Day 0 已驗 Day 1 的 dependencies（Cat 1 / 6 / 49.4 全 ready，handler factory 設計已在 plan §4.3）

---

## Day 1 — 2026-04-30

### 預計 vs 實際

| Step | Plan | Actual | Notes |
|------|------|--------|-------|
| 1.1 schemas.py + 7 tests | 30 min | ~5 min | ChatRequest（mode literal / message length 限制）+ ChatSessionResponse |
| 1.2 session_registry.py + 7 tests | 45 min | ~8 min | asyncio.Lock 守 dict / cancel_event 為 asyncio.Event / module-level singleton + factory for tests |
| 1.3 sse.py + 10 tests | 90 min | ~12 min | 4 50.1-emit events + ToolCallExecuted forward-compat for Day 2；其餘 18 events raise NotImplementedError 帶 sprint pointer；UUID + datetime 由 _jsonable() 轉 str |
| 1.4 handler.py + 5 tests | 60 min | ~8 min | echo_demo 用 MockChatClient scripted（2 responses pop）；real_llm 用 AzureOpenAIAdapter(AzureOpenAIConfig())（envalidation + late import）|
| 1.5 router.py + 10 tests + main.py 接 | 120 min | ~18 min | StreamingResponse + 自動 mark_completed + cancel/get_session 端點；handler 失敗 503；422 由 Pydantic 自動發 |
| 1.6 progress + commit | 15 min | ~10 min | 含 quality gate 全跑 + cross-cat lint regression fix |
| **Day 1 總計** | **~6h（360 min）** | **~61 min（17%）** | 與 50.1 Day 2 (19%) 對齊 |

### Verification (final)

- ✅ `python -m pytest tests/` **239 PASS / 0 SKIPPED / 4.15s**（50.1 baseline 210 + 29 Day 1 新增）
- ✅ `python -m mypy src --strict` 136 files OK
- ✅ 5/5 V2 lints PASS
- ✅ LLM SDK leak grep = 0
- ✅ `tests/unit/api/v1/chat/` 39 tests PASS（5 files × ~8 tests 平均）

### Surprises / Decisions

1. **`tests/unit/api/v1/__init__.py` 衝突 src/api 包名** — 建 `tests/unit/api/v1/__init__.py` + `tests/unit/api/v1/chat/__init__.py` 後，`from api.v1.chat import router` 在 pytest 全 collection 時 resolve 到 tests dir 而不是 src dir。**根本原因**：50.1 既有 `tests/unit/agent_harness/` 完全沒有 `__init__.py`（namespace package mode）。**解法**：刪除我新增的 v1/ + v1/chat/ 兩個 init 檔，改成 namespace package（與 50.1 對齐）。tests/unit/api/__init__.py 也一併刪（之前 49.4 留下的，現在改全 namespace）。**教訓**：CARRY-001 後第二個 pytest 路徑 quirk — 可能值得 50.2 retro 加一條 carry forward。
2. **`AzureOpenAIAdapter` ctor sig 跟 plan 預期不同** — plan §4.1 寫 `AzureOpenAIAdapter(endpoint=..., api_key=..., deployment_name=..., api_version=...)`；actual 是 `AzureOpenAIAdapter(config: AzureOpenAIConfig | None = None)`，AzureOpenAIConfig 是 BaseSettings auto-load AZURE_OPENAI_* env。**修正**：handler.py `build_real_llm_handler()` 改為 `AzureOpenAIAdapter(AzureOpenAIConfig())`，外層仍維持 env vars existence 自檢（避免讓 config 內部 lazy fail 拖到 Loop run time）。
3. **50.1 latent cross-cat lint failure** — `loop.py:94` 走 `agent_harness.tools._abc` 私有路徑，雖然 `tools/__init__.py` 已 re-export `ToolExecutor` / `ToolRegistry`。50.1 retro 寫「5 V2 lints all OK」可能是 lint 沒在 CI 或當時跑法不同。**修正**：改 public path + Modification History entry。Day 1 1.5 順手修，不另開 sprint。
4. **router.py user_input bug 早期被抓** — 一開始我寫 `user_input=""`（誤以為 echo_demo 不需要 message at run time）。**根本原因**：MockChatClient 確實 ignore，但 real_llm 必須走 user_input。**修正**：router 把 req.message 傳到 _stream_loop_events，handler.py 不變（echo_demo 在 build time 已 bake message 到 scripted response，duplicate 但無害）。
5. **handler.py `_chat_client` private attr** — test_handler.py `test_build_echo_demo_scripts_message_into_tool_call` peek MockChatClient 的 `_responses` 內部驗 scripted 對齊 user message。**權衡**：peek 私有屬性不理想，但比建 wrapper public method 更簡單，且 50.x 還沒固化 MockChatClient 公開 inspector API。51.x 若 MockChatClient 增 `peek_scripted_responses()` 此 test 順便 refactor。

### Next Day (Day 2)

- 主題：4 個新 LoopEvent（TurnStarted / LLMRequested / LLMResponded / ToolCallCompleted）+ Worker handler factory + Loop yield 修改
- Plan 6h；預估 actual ~70-90 min（Day 1 比率 17%；Day 2 涉及 _contracts/events.py + Loop body 修改 + tests，scope 略大）
- Pre-work：Day 1 已驗 SSE serializer 對 Day 2 的 4 個新 event types 已 reserve NotImplementedError stub — Day 2 只需把 raise 改成具體 mapping

---

## Day 2 — pending

…（待寫）

---

## Day 2 — pending

…

---

## Day 3 — pending

…

---

## Day 4 — pending

…

---

## Day 5 — pending

…
