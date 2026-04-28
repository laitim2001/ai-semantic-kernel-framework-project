# PoC5 — Orchestrator Chat 三項改善（Worktree 1 整合、測試、合併）

**日期**: 2026-04-19
**Session 類型**: Worktree 1 (execution-log) 測試修復 + Merge 回 main
**相關 Branch**: `feature/orchestration-execution-log-persistence`
**最終 Merge Commit**: `69b5fa2`
**Push 目標**: `github.com/laitim2001/ai-semantic-kernel-framework-project.git`

---

## 目錄

1. [Session 起點與目標](#session-起點與目標)
2. [問題 1：切換 session 右側面板未重置](#問題-1切換-session-右側面板未重置)
3. [問題 2：歷史記錄的記憶/知識步驟顯示為空](#問題-2歷史記錄的記憶知識步驟顯示為空)
4. [問題 3：記憶系統為何一直是空的（機制討論）](#問題-3記憶系統為何一直是空的機制討論)
5. [問題 4：Subagent 模式顯示 9 個 agents（實際 5 個）— Phantom Agents Bug](#問題-4subagent-模式顯示-9-個-agents實際-5-個--phantom-agents-bug)
6. [SSE 串流不即時修復（Cherry-pick from main）](#sse-串流不即時修復cherry-pick-from-main)
7. [記憶/知識步驟顯示 full text 內容](#記憶知識步驟顯示-full-text-內容)
8. [Merge 流程完整執行](#merge-流程完整執行)
9. [發現的 Pre-existing Bug：Alembic 007 revision 錯誤](#發現的-pre-existing-bugalembic-007-revision-錯誤)
10. [Push 到 Github](#push-到-github)
11. [關鍵設計決策總結](#關鍵設計決策總結)
12. [後續 TODO](#後續-todo)

---

## Session 起點與目標

### 初始狀態
- Worktree 1 (`feature/orchestration-execution-log-persistence`) 已有 3 個 commits：
  - `1320023` feat(orchestrator): pipeline execution log persistence
  - `db01254` fix(orchestration): persistence import + migration
  - `c6fe8bf` feat(orchestration): integrate historical pipeline display
- 上一 session 已完成後端持久化 + 歷史面板 UI 整合，但 UI 有多個 bug 待修
- 另有 main 上的 `a1de257` SSE streaming fix 尚未 cherry-pick 到 worktree 1

### Session 目標
1. 啟動 worktree 1 所有服務進行 E2E 測試
2. 修復所有發現的 bugs
3. 完整 merge worktree 1 回 main
4. Push 到 github

---

## 問題 1：切換 session 右側面板未重置

### 現象
用戶開新對話或切換到已有 session 時，右側 orchestration panel 沒有清空——仍顯示上一個 session 的 pipeline 狀態或歷史記錄。

### 根因分析
- `handleSelectThread` (OrchestratorChat.tsx:662-689) 只清了 `selectedMessageId` 和 `selectedHistorySessionId`，**沒有 reset live pipeline state**
- `handleNewThread` (OrchestratorChat.tsx:642-657) 完全沒有 panel 相關清空邏輯
- `useOrchestratorPipeline` hook 沒有對外暴露的 `reset()` 函數

### 修復方案

**修改 1：`frontend/src/hooks/useOrchestratorPipeline.ts`**
新增 `reset()` 函數並 export：
```ts
const reset = useCallback(() => {
  abortRef.current?.abort();
  setState({ ...INITIAL_STATE, steps: INITIAL_STEPS.map(s => ({ ...s })) });
  useAgentTeamStore.getState().reset();
}, []);
```

**修改 2：`frontend/src/pages/OrchestratorChat.tsx`**
- `handleNewThread`：新增 `pipeline.reset()` + `setSelectedMessageId(null)` + `setSelectedHistorySessionId(null)`
- `handleSelectThread`：新增 `pipeline.reset()`（其他兩個 setter 原本已有）

### 驗證
- 開新對話 → 8 步驟回 pending、無 route、無 agents ✅
- 切換 thread → 歷史和 live 都清空 ✅

---

## 問題 2：歷史記錄的記憶/知識步驟顯示為空

### 現象
點 📊 Pipeline 按鈕載入歷史記錄後，「記憶讀取」和「知識搜索」兩個 step 有 latency（4.8s / 1.7s）但內容完全空白。

### 根因
- Backend `persistence._build_pipeline_steps` 只存 `status` + `latency_ms`，完全沒存各 step 的 metadata
- Frontend `transformExecutionLogToPanel` 只為 `intent_analysis`/`risk_assessment`/`hitl_gate`/`llm_route_decision`/`dispatch`/`post_process` 建構 metadata，漏了 `memory_read` 和 `knowledge_search`

### 修復方案

**修改 1：`backend/src/integrations/orchestration/pipeline/persistence.py`**
`_build_pipeline_steps` 為 `memory_read` / `knowledge_search` 附加 `context.memory_metadata` / `context.knowledge_metadata`

**修改 2：`frontend/src/hooks/useOrchestratorHistory.ts`**
`transformExecutionLogToPanel` 新的 step metadata 預設從 `record.metadata` fallback 提取

### 驗證
- 歷史面板「記憶讀取」顯示：Pinned、Budget、Status ✅
- 歷史面板「知識搜索」顯示：Results、Scores、Status ✅
- （後續發現 text body 仍缺，見問題 7）

---

## 問題 3：記憶系統為何一直是空的（機制討論）

### 現象
每次對話記憶步驟都顯示 `Pinned: 0, Budget: 0%, Status: ok`，內容 `No memory context available.`

### Backend log 關鍵訊息
```
Extraction skipped (trivial) for session f5812350-fd0...
```

### 機制釐清

**寫入流程（自動 + LLM 篩選）**：
1. Pipeline Step 8 `post_process` 觸發 `MemoryExtractionService.extract_and_store()`（`asyncio.create_task` fire-and-forget）
2. Extraction LLM 判斷對話是否 **trivial**：打招呼、簡單狀態查詢 → `skip: true` → 不寫入
3. 非 trivial 時提取 4 類：FACTS / PREFERENCES / DECISIONS / PATTERNS

**為什麼空**：
- 測試訊息都被 LLM 判為 trivial → skipped
- 需發送有實質資訊的訊息（例如「我負責 APAC ETL Pipeline」、「偏好中文回答」）

**讀取流程**：
- 5 個 sections：pinned_knowledge / recent_context / relevant_memories / user_preferences / history_summary
- 全部空時顯示 "No memory context available."
- Pinned 層是使用者手動控制（類似 CC 的 CLAUDE.md），不會自動提取

### 結論
非 bug，是設計行為。**不需改程式碼**。

---

## 問題 4：Subagent 模式顯示 9 個 agents（實際 5 個）— Phantom Agents Bug

### 現象
- Backend log 確認 `SubagentExecutor: Decomposed into 5 sub-tasks`
- 但右側面板「AGENT TEAM」顯示 **9 Agents**
- 前 5 個有 task title（正確）
- 後 4 個只有 role name（Database/Application/Cloud/Network Expert），0% progress
- 少 security_expert（可能當下還沒 start）

### 三路深入 explore 分析

**事件流追蹤**：
1. `subagent.py:76-95` emit **AGENT_TEAM_CREATED**（5 agents，`agent_id=w-<uuid>`、`agent_name=task.title`）→ frontend store 塞入 5 個正確 agents ✅
2. 每個 worker start，`worker_executor.py:87-97` emit **SWARM_WORKER_START**（包含 `worker_id`、`agent_name=role_def["name"]="database_expert"`、`display_name`、`role`）
3. `event_adapter.py:50-72` 把 SWARM_WORKER_START 轉成兩個事件：
   - `AGENT_MEMBER_STARTED`（`agent_id=worker_id` = `w-<uuid>`，dedup 命中 ✅）
   - **legacy AGENT_THINKING**（line 65-72，只有 `agent_name=role_def["name"]`，**無 agent_id**）← **BUG 源頭**
4. `useOrchestratorPipeline.ts:217-230` 的 AGENT_THINKING handler 用 `agentName` 當 `agentId`：
   ```ts
   addAgent({ agentId: agentName, agentName, ... })
   ```
   → `agentId="database_expert"` 與原 `w-<uuid>` 不同 → **dedup 失效 → 新增 phantom agent**

Team mode 有相同 bug：`pipeline_emitter_bridge.py:77-82`

### Explore Agent 驗證
- Backend 其他 AGENT_THINKING 來源（`agent_team_poc.py`、`agent_work_loop.py`、`mediator.py`）是 PoC 獨立進度訊號，不造成 phantom
- 無 unit/integration test 依賴 AGENT_THINKING
- `pipeline.agents` 只被 `OrchestratorChat.tsx:1172` 消費（StepDetailPanel agents prop）
- `AgentProgress` minimum: agentName + status

### 修復方案（A + B + C）

**Phase A（backend）**：移除 2 處 backward-compat AGENT_THINKING emit
- `backend/src/integrations/orchestration/dispatch/executors/event_adapter.py` line 65-72
- `backend/src/integrations/orchestration/dispatch/executors/pipeline_emitter_bridge.py` line 77-82

**Phase B（frontend）**：`useOrchestratorPipeline.ts` AGENT_THINKING handler（line 191-230）移除 line 217-230 的 `addAgent` 區段（保留 line 192-201 的 pipeline.agents 更新供 PoC 路徑用）

**Phase C（frontend）**：在 AGENT_MEMBER_STARTED handler（line 369-410）新增 `pipeline.agents` 更新，取代原本靠 AGENT_THINKING populate 的機制

### 驗證
- AGENT TEAM 顯示正確數字（5）✅
- 上方 Agents block 顯示 role-name + Thinking/Completed 狀態 ✅
- 無 phantom agents ✅

### Commit 產出
`23da222` fix(orchestration): right-panel UX fixes + step metadata + phantom agent cleanup
涵蓋問題 1、2、4 三項修復。

---

## SSE 串流不即時修復（Cherry-pick from main）

### 現象
右側 panel 的步驟訊息不會即時顯示，而是等所有步驟完成後一次性顯示。

### 根因
Pre-existing bug from Sprint 153-154。Main 已有修復 `a1de257`，但 worktree 1 尚未 cherry-pick。

### 修復
Cherry-pick commit `a1de257` → worktree 1 `3c54a96`

**修改**: `backend/src/integrations/orchestration/pipeline/service.py`
`_emit()` 的 `queue.put()` 後加 `await asyncio.sleep(0)` 強制 event loop yield

### 驗證
- Socket test 顯示 events 從 [31.21s] 全部到達 → [5s, 22s, 25s, 34s] 分散到達 ✅

---

## 記憶/知識步驟顯示 full text 內容

### 現象
修復問題 2 後，歷史面板只顯示 metadata 摘要（Pinned、Budget、Results、Scores），但 live 模式實際顯示完整的 `memory_text` 和 `knowledge_text` body。

### 根因
- Live 模式 `service.py:511-518` 的 `_build_step_summary` 將 `memory_text` / `knowledge_text` full text 塞入 STEP_COMPLETED SSE 事件
- `StepDetailPanel.tsx:135/151` 會從 `meta.memory_text` / `meta.knowledge_text` 渲染
- Persistence 只存 metadata 沒存 text body → 歷史模式缺完整內容

### 修復
`backend/src/integrations/orchestration/pipeline/persistence.py`:
- `memory_read`：同時儲存 `memory_metadata` + `memory_text` + `memory_chars`
- `knowledge_search`：同時儲存 `knowledge_metadata` + `knowledge_text` + `knowledge_chars`
- 用同一個 `meta` dict 合併，避免互相覆蓋

### 驗證
發新訊息後點 📊 → 歷史面板的記憶讀取和知識搜索顯示完整 text body（與 live 模式一致）✅

### Commit 產出
`9c3df99` fix(orchestration): persist full memory/knowledge text in execution log

---

## Merge 流程完整執行

### 合入的 6 個 Commits

| SHA | 標題 |
|-----|------|
| `1320023` | feat(orchestrator): pipeline execution log persistence to PostgreSQL |
| `db01254` | fix(orchestration): fix persistence service import + add DB migration |
| `c6fe8bf` | feat(orchestration): integrate historical pipeline display in right panel |
| `23da222` | fix(orchestration): right-panel UX fixes + step metadata + phantom agent cleanup |
| `3c54a96` | fix(pipeline): force event loop yield after SSE emit (cherry-pick from main) |
| `9c3df99` | fix(orchestration): persist full memory/knowledge text in execution log |

### 風險點評估

| 風險 | 等級 | 實際結果 |
|------|------|----------|
| SSE fix 重複（main `a1de257` vs worktree `3c54a96`） | 🟡 中 | Git 3-way merge 自動解析為「兩邊加相同 2 行 → 不衝突」✅ |
| Migration 008 編號衝突 | 🟢 低 | 無衝突 ✅ |
| `vite.config.ts` 未 commit 的 testing port | 🟢 低 | merge 前 `git checkout` 還原 ✅ |
| Phantom agent 修復衝突 | 🟢 低 | 無衝突 ✅ |

### 執行步驟

**階段 1：Pre-merge 準備**
1. worktree 1: `git checkout frontend/vite.config.ts` 還原（port 4120/8660 → 4070/8600）
2. 停止 worktree 1 服務（backend 8660、frontend 4120）
3. Main repo: `git status` 確認 clean

**階段 2：Merge 執行**
```bash
git merge --no-ff feature/orchestration-execution-log-persistence \
  -m "merge: Phase 47 worktree 1..."
```
結果：**21 檔案變更，1,238+/-42 行，無衝突** → Merge commit `69b5fa2`

**階段 3：驗證**
- `grep -c "await asyncio.sleep(0)" service.py` = 1 ✅（SSE fix 無重複）
- Backend 啟動在新 port 8700 ✅
- Frontend 啟動在新 port 4200 ✅
- 用戶 E2E 測試通過

---

## 發現的 Pre-existing Bug：Alembic 007 revision 錯誤

### 情境
Merge 後嘗試 `alembic upgrade head` 想套用 migration 008，結果：
```
KeyError: '006_sync_execution_model'
```

### 根因
`backend/alembic/versions/20260414_1000_007_create_agent_experts_table.py` 第 19 行：
```python
down_revision: Union[str, None] = "006_sync_execution_model"
```

但 `20260116_1705_006_sync_execution_model.py` 第 21 行實際 revision ID：
```python
revision: str = '006_sync_executions'
```

**Revision 鏈斷裂**：007 指向不存在的 revision → 所有 alembic 指令（upgrade / downgrade / heads）失敗

### 影響
- Main 從某個 Phase 開始就無法用 alembic（不知多久）
- DB 沒有 `alembic_version` table（schema 透過 SQLAlchemy `create_all` 或手動建立）

### 本次處理
- **不修**（不屬於 worktree 1 scope）
- Migration 008 實際不需跑：`orchestration_execution_logs` table 已存在於共用 DB（worktree 1 測試時建立）

### 建議後續修復
1. 修 007 的 `down_revision` 從 `"006_sync_execution_model"` 改為 `"006_sync_executions"`
2. `alembic stamp head` 標記 DB 為最新（因 tables 已存在）
3. 未來 migration 就能正常運作

---

## Push 到 Github

### 推送前狀態
- Local main ahead of origin/main by **94 commits**（含本次 merge + 過去未 push 累積）

### 執行
```bash
git push origin main
# Result: 63ae7ff..69b5fa2  main -> main ✅
```

### 結果
- Main 完整同步到 github ✅
- Feature branch `feature/orchestration-execution-log-persistence` **本地保留**，未 push 到 remote

---

## 關鍵設計決策總結

### 決策 1：Per-message history navigation（非 auto-load）
每個 assistant 訊息旁加 📊 按鈕，用戶點擊才載入該 session 的歷史。避免自動載入造成的困惑。

### 決策 2：Phase A+B+C 完整修復而非只 A+B
只做 A+B 會導致上方小「Agents」block 變空（因 pipeline.agents 沒 populate）。加 C 在 AGENT_MEMBER_STARTED 補上 populate，確保視覺一致。

### 決策 3：Worktree 不移除
Branch、commits、實體目錄全部保留作為 reference。Git worktree tracking 已移除但可用 `git worktree add --force` 重建。

### 決策 4：Alembic bug 不在本 merge scope 修
Pre-existing bug 屬於 main 自身問題，不屬於 worktree 1 的變更範圍。獨立修復以保持 merge scope 純淨。

### 決策 5：每次重啟換新 port
遵循 feedback memory：Windows socket leak 風險，--reload 不可靠。每次重啟 backend/frontend 換新 port。

### 決策 6：Agents block 顯示粒度（未實作，待用戶決策）
- 上方 block 按 role dedup（2 個）vs 下方按 task id（3 個）
- 選項 A：維持（role 概觀 + task 細節互補）
- 選項 B：改上方用 task title dedup
- 選項 C：移除上方小 block

---

## 檔案變更總覽

### Backend（11 個檔案）
| 檔案 | 改動 |
|------|------|
| `backend/alembic/versions/20260416_1400_008_create_orchestration_execution_logs.py` | 新增（DB migration，未實際執行） |
| `backend/src/api/v1/orchestration/execution_log_routes.py` | 新增 |
| `backend/src/api/v1/orchestration/execution_log_schemas.py` | 新增 |
| `backend/src/api/v1/orchestration/chat_routes.py` | 加 `_persist_execution` fire-and-forget |
| `backend/src/api/v1/__init__.py` | 註冊 router |
| `backend/src/infrastructure/database/models/orchestration_execution_log.py` | 新增（ORM） |
| `backend/src/infrastructure/database/models/__init__.py` | 匯出新模型 |
| `backend/src/infrastructure/database/repositories/orchestration_execution_log.py` | 新增（Repository） |
| `backend/src/integrations/orchestration/pipeline/persistence.py` | 新增 + 2 次修復（memory/knowledge metadata + text body） |
| `backend/src/integrations/orchestration/pipeline/service.py` | SSE yield fix（cherry-pick） |
| `backend/src/integrations/orchestration/dispatch/executors/event_adapter.py` | 移除 backward-compat AGENT_THINKING |
| `backend/src/integrations/orchestration/dispatch/executors/pipeline_emitter_bridge.py` | 同上 for team mode |

### Frontend（8 個檔案）
| 檔案 | 改動 |
|------|------|
| `frontend/src/hooks/useOrchestratorHistory.ts` | 新增 hook + `transformExecutionLogToPanel` + record.metadata fallback |
| `frontend/src/api/endpoints/orchestration.ts` | 新增 API 函數 |
| `frontend/src/pages/OrchestratorChat.tsx` | effectivePanelData、per-message click、panel reset、historical 整合 |
| `frontend/src/hooks/useOrchestratorPipeline.ts` | `reset()` 函數 + AGENT_THINKING handler 簡化 + AGENT_MEMBER_STARTED 同步 pipeline.agents |
| `frontend/src/components/unified-chat/MessageList.tsx` | 📊 Pipeline 按鈕 |
| `frontend/src/components/unified-chat/ChatArea.tsx` | `onMessageClick` prop |
| `frontend/src/types/unified-chat.ts` | ChatAreaProps 擴充 |
| `frontend/vite.config.ts` | 僅測試用 port 切換（已還原） |

### Docs（2 個檔案）
- `docs/03-implementation/sprint-planning/phase-47/sprint-169-plan.md`
- `docs/03-implementation/sprint-planning/phase-47/sprint-169-checklist.md`

---

## 服務 Port 歷史（本 session 使用記錄）

| 階段 | Backend | Frontend | 備註 |
|------|---------|----------|------|
| 起始測試 | 8620 | 4090 | 初次 worktree 1 啟動 |
| SSE fix 後 | 8630 | 4090 | Backend 換 port 使改動生效 |
| Phantom fix 後 | 8640 | 4100 | 兩者都換 |
| SSE cherry-pick 後 | 8650 | 4110 | 兩者都換 |
| Memory text fix 後 | 8660 | 4120 | 兩者都換（最後 worktree 測試 port） |
| Merge 後 main | 8700 | 4200 | Main E2E 驗證 |
| 最終 | -（停止） | -（停止） | Cleanup 後停服務 |

---

## 後續 TODO

### Phase 47 剩餘
1. **Worktree 2 (intent-classifier-improvements)** 合併到 main — commit `89e9037`
2. **Worktree 3 (subagent-count-control)** 合併到 main — commit `01d9913`

### Pre-existing Bug
3. **Alembic 007 down_revision 修復**：將 `"006_sync_execution_model"` 改為 `"006_sync_executions"` + `alembic stamp head`

### Code 改善候選（本 session 討論但未實作）
4. **Agents block 顯示粒度**：上方 block 目前按 role dedup（顯示 2），下方按 task id（顯示 3）

### 工作區清理
5. 主 repo untracked 測試 artifacts（PNGs / MDs / log 檔）可考慮清理
6. 可選：刪除實體目錄 `ai-semantic-kernel-execution-log`（Windows file handle 可能需重啟釋放）
7. 可選：`git push origin feature/orchestration-execution-log-persistence` 做 remote 備份

---

## Memory 更新

本 session 更新的 auto-memory 檔案：
- `project_git_worktrees.md`：Worktree 1 標記 Merged + 保留 reference
- `project_phase47_orchestrator_improvements.md`：Worktree 1 完整紀錄（含後續 UI fixes + SSE cherry-pick + 發現的 Alembic 007 bug）

---

## Session 總結

### 本 session 新增 commits
- **3 個 commits on worktree 1**：
  - `23da222` — UX fixes + metadata + phantom agents
  - `3c54a96` — SSE yield fix（cherry-pick）
  - `9c3df99` — full memory/knowledge text persist
- **1 個 merge commit on main**：`69b5fa2`
- **Push**：94 commits → `origin/main`

### 本 session Phase 47 進度
- ✅ Worktree 1 (execution-log) → merged & pushed
- 🔄 Worktree 2 (intent-classifier) → pending merge
- 🔄 Worktree 3 (subagent-count-control) → pending merge

### 核心成就
Worktree 1 完整 merged，涵蓋後端持久化、歷史面板整合、per-message history navigation、panel reset、記憶/知識完整內容、SSE 即時串流、phantom agent 消除。所有 E2E 功能驗證通過。
