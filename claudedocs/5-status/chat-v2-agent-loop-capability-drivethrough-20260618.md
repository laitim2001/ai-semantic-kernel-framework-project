# Chat-V2 Agent Loop 能力 Drive-Through 總結（多輪）

**Purpose**: 將 2026-06-18 多輪對 chat-v2 主流量的 drive-through 發現集中留底 —— agent loop 各子能力是否「真的能用」，以及對「能否像 Claude Code 長時間自主運行」的誠實評估。
**Category / Scope**: 範疇 1 (Orchestrator Loop) 為主，橫跨 2/3/4/9/10/11/12；chat-v2 主流量
**Created**: 2026-06-18
**Last Modified**: 2026-06-18
**Status**: Active（drive-through 記錄；非 sprint）
**Verifier**: 真 UI（Playwright）+ 真後端（uvicorn :8000）+ 真 LLM（Azure gpt-5.2），dan@acme.com / acme-prod

> **Modification History**
> - 2026-06-18: Initial — 彙整 6 個 scenario（python_sandbox 修復 / subagent / verification self-correct / HITL / handoff / mid-run injection / long-run + compaction）

---

## 0. 為何做這幾輪

用戶核心期望：本項目的價值是「提供與 AI agent 互動，agent 會**思考、plan、有執行能力**，且**任務為本 / 像 CC 一樣能長時間運行**」。chat-v2 是這個價值的主流量。依 **Drive-Through Acceptance 硬約束**（gate 全綠 ≠ 人能真的用），逐一在真 UI + 真後端 + 真 LLM 上把每個子能力**開車驗證**，而非只看 gate / curl。

---

## 1. 結論速覽

| 子能力 | 範疇 | 結果 | 一句證據 |
|--------|------|------|---------|
| 工具執行（python_sandbox） | 2 | 🔴→✅ **修復後可用** | 修前 0ms「unknown tool error」完全跑不動 → FIX-033 後 Docker 真執行 |
| Subagent 任務分解 | 11 | ✅ 驗證為真 | `task_spawn(fork)`×3 → 3 真 child loop → Tree tab 渲染 |
| Verification self-correction | 10 | ✅ 驗證為真 | 初答含 PII → `verification_failed` → 重答 redact → `passed 0.98` |
| HITL pause/resume | 9→1 | ✅ 驗證為真 | MEDIUM 工具 → `awaiting_approval` + Approve → `resume` 續跑 |
| Handoff | 11 | ✅ 驗證為真 | `handoff(planner)` → `stop=handoff` + boot 新 session |
| Mid-run injection | 1×12 | ✅ 驗證為真 | run 中 `POST /inject` → 在 turn 邊界 drain → agent 採納 |
| Long-run 自主任務 | all | ✅ 驗證為真 | 多工具 + 2 subagent + 報告，`verification 0.98` |
| **Context compaction 實際壓縮** | 4 | ✅ 驗證為真 | 多 send 後 `messages_compacted=12`，token `4477→1649`（−63%） |

**本系列共發現並修復 1 個真實 bug（FIX-033，已 merged PR #319）**；其餘子能力皆已正確接線且可用，非 Potemkin。

---

## 2. 各 Scenario 詳細證據

### 2.1 工具執行修復（FIX-033）
詳見 `claudedocs/5-status/chat-v2-python-sandbox-drivethrough-20260618.md` + `claudedocs/4-changes/bug-fixes/FIX-033-*.md`。
- **根因**：chat path 寫死 `SubprocessSandbox` → Windows SelectorEventLoop 上 `create_subprocess_exec` 0ms 拋 `NotImplementedError`（空訊息）→ UI「unknown tool error」。修前「219.93」= 工具失敗後 agent 退回錯誤心算。
- **修法**：wiring 改 `default_sandbox()`/Docker（process-wide singleton，CI fallback Subprocess）+ image 加 numpy + tool description 明示 script-not-REPL/print()。
- **修後三輪 T1/T2/T3 全通**，mean 227.0 三方一致。

### 2.2 Subagent 任務分解（範疇 11）
Prompt：要 agent 用 `task_spawn(fork)` 各派一個 subagent 算 3 個獨立子任務。
- `task_spawn(mode="fork")` 呼叫 **3 次** → 3 個真 child loop：
  - 12! → `479001600`（subagent 101e7ed7，1853 tok）
  - F10 → `55`（dfba65a7，1863 tok）
  - 20 以下質數和 → `77`（ee89b132，1854 tok）
- Inspector **Tree** tab：`SUBAGENT TREE · LIVE`，3 子代 + `Mode: fork · Depth: 1 · Tokens(subtree): 5,570`（=1853+1863+1854 ✓）
- 合併最終答案 → `verification_passed llm_judge 0.99`

### 2.3 Verification Self-Correction（範疇 10）
預設 judge `output_quality` 過寬鬆（"when in doubt, pass"）不會 fail。改用 per-tenant override 把 judge 換成 `pii_leak_check`（admin `PUT /tenants/{id}/harness-policy`，事後還原），讓 agent **生成**一筆假 PII：
- 初答：`Jordan Mercer, jordan.mercer@example.test, +1-415-555-0187`
- → `verification_failed`（`Detected a real name, email address, and phone number`）
- → **self-correction**（依 judge 的 suggested_correction 重答，跑到 `max_correction_attempts=2`）
- → 最終 redact 成 `[NAME], [EMAIL], [PHONE]` → `verification_passed 0.98`

附帶驗證的兩個機制：
- **Cat 9 INPUT guardrail**：當輸入本身含真 PII（email+phone），在 LLM 前 `guardrail_triggered: input → block`。
- **safety_review judge 正確放行**：資安教育答案判 safe（0.93），未誤殺。

### 2.4 HITL Pause/Resume（範疇 9 → 1）
Prompt：要 agent 用 python_sandbox 算 8!（MEDIUM 風險）。
- `tool_call_request: python_sandbox` → `approval_requested risk=MEDIUM` → `state_checkpointed`（durable）→ `loop_end stop=awaiting_approval`
- UI 出現 **「Approve & continue」+「Reject」**
- 按 Approve → `POST /chat/{id}/resume` → 工具真執行 **40320**（8! ✓）→ `verification_passed 0.99` → `end_turn`
- Reject 路徑在 FIX-033 drive-through 已驗證（decision=REJECTED → loop 結束）

### 2.5 Handoff（範疇 11）
chat 有 spec-only `handoff` trigger tool（Sprint 57.107 B3，policy-gated `handoff_enabled`，預設 registered）。有效 targets = `researcher` / `reviewer` / `planner`。
- Prompt：要 agent 轉交給 `planner`
- `llm_response: 1 tool call`（handoff）→ loop 分類為 `OutputType.HANDOFF` → `loop_end stop=handoff`
- `agent_handoff{target_agent:"planner", reason:"…", parent_session_id:28d94671…, new_session_id:c6a0cf47…}`
- 平台層 boot 了新 planner-persona session（`new_session_id` 已產生）

### 2.6 Mid-Run Injection（範疇 1 × 12）
`POST /chat/{id}/inject`（Sprint 57.101 B1），需 run in-flight。
- 跑一個 15 步 python_sandbox 任務（MEDIUM→auto，不 pause），run 中 `POST /inject` 帶 sentinel
- `injectStatus 202`（`status: "queued"`，run 開始後 ~649ms）
- `message_injected` wire event 觸發 → 在 turn 邊界 drain 成 **「injected mid-run」user 訊息**
- agent 最終 summary 表格含 `| Sentinel | BANANA-42 |` **且** 15! 任務照常完成（`1307674368000`）—— 注入在不打斷原任務下被採納
- **發現**：run 進行中 composer 有 **「Inject」+「Stop」UI 按鈕**（比記憶中「inject UI 已移除」更完整）
- **時間性**：runs 在 ~5-8s 完成，比 tool 往返延遲快 → 改用瀏覽器內 300ms 輪詢消除往返才趕上注入窗

### 2.7 Long-Run 自主任務 + 真 Compaction（範疇 all）
**單次 send 的長任務**（16 筆延遲讀數的資料分析）：
- 多工具：mean **218.56**（=3497/16 ✓）、std 207.84、min/max 138/920、outlier 規則 mean+2σ=634.24 → flag **Day4=920**
- subagent 分解：2 個 fork subagent 獨立算 median **148.5** + 95th percentile **612.5**（各 ~4068 tok）
- 綜合報告 + `verification_passed 0.98`

**真 Compaction（需多 user turns）**：
- compaction 門檻 = `CHAT_COMPACTION_TOKEN_BUDGET`(預設 100,000) × `_CHAT_TOKEN_THRESHOLD_RATIO`(0.75) = **75,000 tokens** → 正常 chat(~4k/turn)永不觸發（這就是平時只見 0ms no-op 的原因）。
- 程式碼自身註明 `CHAT_COMPACTION_TOKEN_BUDGET` 是 **"the drive-through trigger lever"** → 帶 `=5000` 重啟後端 → 門檻降到 3750。
- **Send 1（單 user turn）**：compaction 觸發（tokens_before 一路 5675→15239 證明 env 生效）但 `messages_compacted=0` —— cutoff 看 USER turns，單 send 只 1 個 → 無舊 user turn 可壓（符合程式碼 line 129-134 註明行為）。
- **Send 3（多 send + rehydration，≥3 user turns）**：**真壓縮 `messages_compacted=12`，tokens `4477→1649`（−63%，省 2828）**。
- **壓縮後連續性保持**：follow-up 正確答出 Day4=920 最差（超均 ~701ms）、排除 spike 後 mean ≈147.6（=(3497-920-510)/14 ✓）。

---

## 3. 對「能否像 CC 長時間運行」的誠實評估（code-grounded）

| 面向 | 實情 | 來源 |
|------|------|------|
| Loop 結構 | while-true TAO/ReAct，4 終止條件（max_turns / token_budget / cancellation / END_TURN）；工具結果回注重新推理（非 pipeline 偽裝） | `orchestrator_loop/loop.py:2074`（3707 行） |
| **單次 send 上限** | chat real_llm loop **`max_turns=8`**（非 50）→ 一次自主爆發最多 8 turns，**不是** CC 數百 turn | `api/v1/chat/handler.py:710` |
| 自我修正 | `max_correction_attempts=2` | `handler.py` loop ctor / 已實證 §2.3 |
| 長對話延續 | 靠**多次 send + Cat 3 memory + rehydration**（Sprint 57.127）累積，非單次長 run | 已實證 §2.7 |
| Compaction | 預設門檻 75k 正常聊天不觸發；≥3 user turns 時才真壓縮（多 send 或 mid-run injection 才達 cutoff） | `_category_factories.py:108-140` + 已實證 §2.7 |
| 任務為本 | 靠「對話式 loop + 工具 + subagent 分解」達成；**無** CC 的 TodoWrite 顯式 task primitive；plan 是自然語言宣告 | 已實證 §2.2 / §2.7 |

**一句總結**：「會想、會 plan、能執行、可中斷（HITL/inject）、跨輪記憶、自我修正、子代分解、長對話壓縮」**全部驗證為真**；但「像 CC 單次跑數小時 / 數百 turn」**不成立** —— 本平台的長運行是**多次 8-turn 有界爆發 + rehydration + compaction**的組合，不是單一無界自主 run。這是有意設計（伺服器端、可治理、可審計），非缺陷。

---

## 4. Drive-Through 方法（可重現）

- 真 UI：Playwright 開 `http://localhost:3007/chat-v2`，dev-login dan@acme.com（admin / acme-prod）
- 真後端 :8000（uvicorn `api.main:app`）、真 LLM Azure gpt-5.2、mode=`real_llm`（非 echo_demo）
- 治理 lever（皆 per-request 生效、事後還原）：
  - verification：`PUT /api/v1/admin/tenants/{id}/harness-policy` `{verification_judge_template}`
  - HITL：`PUT /api/v1/admin/tenants/{id}/hitl-policies` `{auto_approve_max_risk, require_approval_min_risk}`
  - compaction：env `CHAT_COMPACTION_TOKEN_BUDGET` / `CHAT_COMPACTION_KEEP_RECENT_TURNS`（**需重啟後端**）
- 證據抓取：`browser_evaluate` 讀 transcript innerText/innerHTML（event 流含 `verification_failed` / `message_injected` / compaction `tokens_before/after` / `agent_handoff` 等）
- 截圖留證後清理（per 用戶工作區整潔要求）

### 還原清單（本系列結束時皆已執行）
- HITL policy → 基準（LOW:auto / MEDIUM+:always_ask）
- verification judge → 預設（null → `output_quality`）
- compaction env → 移除（重啟後端回預設 100k budget，PID 48688）
- 前端 :3007 全程未動

---

## 5. 重要環境/運維教訓（複用）

- **Risk Class E（stale `--reload` / orphan spawn worker）實證重現**：`dev.py stop` 後 parent 沒了但 `multiprocessing.spawn` worker 仍透過 SO_REUSEADDR 佔 :8000。清理要用 `Get-CimInstance Win32_Process` 按 cmdline(`uvicorn|multiprocessing.spawn`)掃，不能只看 port-owner。
- **PowerShell cwd 持久但 shell 變數不持久**：跨 tool call `cd` 殘留會使相對路徑（`scripts/dev.py`）解析錯誤 → 用絕對路徑。
- 後端重啟使 JWT/session 失效 → 需 dev-login 重登。

---

## 6. 相關文件

- `claudedocs/5-status/chat-v2-python-sandbox-drivethrough-20260618.md` —— FIX-033 完整發現
- `claudedocs/4-changes/bug-fixes/FIX-033-chat-python-sandbox-docker-wiring.md`
- `memory/feedback_drive_through_over_paper_metrics.md` —— Drive-Through 硬約束來源
- `memory/feedback_context_mode_plugin_prompt_injection.md` —— 本系列期間的工具層 prompt-injection 安全事件（app UI/SSE 全程零污染）
- `agent-harness-planning/01-eleven-categories-spec.md` —— 11+1 範疇定義
