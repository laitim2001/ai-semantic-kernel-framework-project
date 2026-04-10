# CC vs IPA Agent Team 完整功能對比報告

> 基於 CC 源碼分析（30 waves, 75 files）+ IPA V4 最新測試結果（2026-04-09）
> 測試環境：Backend 8043 (single worker + reload), Frontend 4070

---

## 13 維度完整對比

### 1. Agent 建立與配置

| 功能 | CC | IPA V4 | 狀態 |
|------|-----|--------|------|
| Agent 定義 | `.claude/agents/` markdown + YAML frontmatter | `_build_team_agents_config()` Python dict 角色庫 | ✅ 對等（形式不同） |
| 角色數量 | 無限自定義 | 8 個預定義角色（V4 擴展） | ✅ PoC 足夠 |
| 動態 agent 數 | Lead 決定需要幾個 | TeamLead Phase 0 動態分解 2-8 | ✅ 對等 |
| Agent routing | 6-way 決策樹（teammate/fork/remote/async/sync） | 單一路徑：asyncio.create_task | ⚠️ IPA 較簡單 |
| Model 選擇 | Per-agent model (sonnet/opus/haiku) | 統一 model（所有 agent 共用） | ❌ IPA 缺失 |
| MCP 過濾 | `filterAgentsByMcpRequirements()` | 無 | ❌ 不適用（server-side 無 MCP） |

**測試驗證**：✅ 5 agents 動態建立（LogExpert/DBExpert/AppExpert/SecurityExpert/CloudExpert），4 tasks 動態分解

---

### 2. 並行執行模型

| 功能 | CC | IPA V4 | 狀態 |
|------|-----|--------|------|
| 執行模型 | Pane-based (tmux/iTerm2) + In-process (AsyncLocalStorage) | asyncio.gather + ThreadPoolExecutor | ✅ 對等效果 |
| 隔離機制 | AsyncLocalStorage per agent | Per-agent coroutine in asyncio.gather | ✅ 對等 |
| 真正並行 | 多進程（pane）或同進程（async） | asyncio.to_thread + 獨立 event loop per agent | ✅ 對等 |
| Backend 多型 | 3 backends (Tmux/iTerm2/InProcess) | 單一 in-process（server-side 不需要終端） | ✅ 適合 server-side |
| 獨立 client | 每個 agent 獨立 API client | 每個 agent 獨立 `client_factory()` | ✅ 對等 |

**測試驗證**：✅ 5 agents 同時啟動（時間戳差 <0.1s），並行工作

---

### 3. Agent 生命週期

| 功能 | CC | IPA V4 | 狀態 |
|------|-----|--------|------|
| Spawn | `spawnTeammate()` + AbortController | `asyncio.create_task()` | ✅ 對等 |
| Active 階段 | `runAgent()` 執行 LLM + tools | Phase A: claim task → LLM call → report | ✅ 對等 |
| Idle 階段 | `isIdle` flag + `pendingUserMessages[]` | Phase B: emit agent_idle + Phase C: poll 500ms | ✅ 對等 |
| Graceful shutdown | `shutdown_request` message → agent 確認退出 | `SHUTDOWN_REQUEST` via inbox → `SHUTDOWN_ACK` 回覆 | ✅ 對等 |
| Hard kill | `AbortController.abort()` + state cleanup | `shutdown_event.set()` + `task.cancel()` | ✅ 對等 |
| 10-step cleanup | MCP/hooks/tracking/fileState/perfetto/todos/shell | 簡化版：emit SWARM_WORKER_END | ⚠️ IPA 較簡單 |
| Max turns safety | 無明確限制 | `max_llm_turns=10` 安全帽 | ✅ IPA 有安全措施 |

**測試驗證**：✅ 3 agents 回覆 SHUTDOWN_ACK（CloudExpert 105.4s, SecurityExpert 105.5s, DBExpert 105.6s），2 agents 被 force-kill（在 LLM call/approval 等待中）

---

### 4. Agent 間通訊

| 功能 | CC | IPA V4 | 狀態 |
|------|-----|--------|------|
| 通訊機制 | File-based mailbox (append-only JSONL) | Redis Stream per-agent inbox | ✅ IPA 更優（Redis 比 file 更適合 server-side） |
| 定向訊息 | `SendMessageTool(to: "agent-name")` | `send_team_message(to_agent="DBExpert")` | ✅ 對等 |
| 廣播訊息 | 寫入所有 mailbox | `to_agent=None` → 全域 message stream | ✅ 對等 |
| Polling 頻率 | File polling（無明確間隔） | 500ms polling in Phase C | ✅ 對等 |
| 訊息持久化 | File-based（crash-safe） | Redis Stream（crash-safe） | ✅ 對等 |
| Unread tracking | 基於 file offset | 基於 Redis Stream cursor + `read_by` set | ✅ 對等 |
| 結構化訊息 | `shutdown_request`, `shutdown_response`, `plan_approval_response` | `SHUTDOWN_REQUEST`, `SHUTDOWN_ACK`（V4） | ✅ 對等 |
| 權限請求路由 | Teammate → leader via mailbox | N/A（server-side 用 API endpoint） | ✅ 架構適應 |

**測試驗證**：✅ 5 條定向訊息（DBExpert→LogExpert, SecurityExpert→LogExpert/DBExpert/AppExpert, DBExpert→SecurityExpert），Redis Stream 持久化

---

### 5. 任務管理

| 功能 | CC | IPA V4 | 狀態 |
|------|-----|--------|------|
| 任務分解 | Lead agent 手動分派 | TeamLead Phase 0 LLM 動態分解 | ✅ IPA 更優（自動化） |
| 任務狀態機 | `pending → running → {completed, failed, killed}` | `PENDING → IN_PROGRESS → {COMPLETED, FAILED}` | ✅ 對等 |
| 任務認領 | Lead 指派 | `claim_task()` work-stealing（agent 自助認領） | ✅ IPA 更優 |
| 進度追蹤 | Token count + message count | Task progress（completed/in_progress/pending） | ✅ 對等 |
| 任務重分配 | 無明確機制 | V4: `reassign_task()` + retry_count（失敗後重分配） | ✅ IPA 更優 |
| 優先級 | 無 | Priority 1-5（高優先先被 claim） | ✅ IPA 更優 |
| Expertise matching | 無 | `required_expertise` field（task-agent 匹配提示） | ✅ IPA 更優 |

**測試驗證**：✅ TeamLead 建立 4 tasks，5 agents 各自 claim，2/4 completed，進度條顯示

---

### 6. 工具執行與權限

| 功能 | CC | IPA V4 | 狀態 |
|------|-----|--------|------|
| 權限模式 | 7 種（default/acceptEdits/plan/bypass/dontAsk/auto/bubble） | 2 種（approve/skip） | ⚠️ IPA 較簡單 |
| 權限決策 | 9-step cascade + 5-way concurrent resolver | Tool name whitelist + event-driven approval | ⚠️ IPA 較簡單（PoC 足夠） |
| Event-driven 等待 | `Promise` + `await` + `claim()` guard | `asyncio.Event` + `await event.wait()` + `is_set()` guard | ✅ 對等架構 |
| 不阻塞其他 agents | `AsyncLocalStorage` 隔離 | Per-coroutine in `asyncio.gather` | ✅ 對等 |
| 單 worker 可用 | 是（Node.js event loop） | 是（asyncio event loop） | ✅ 對等（V4 修正後） |
| Bash 安全檢查 | 23 個 security check IDs | 命令白名單 + FORBIDDEN_PATTERNS | ✅ 對等（形式不同） |
| 工具安全 | Bash sanitization + prefix matching | `ALLOWED_COMMANDS` whitelist + subprocess sandbox | ✅ 對等 |
| Real tools | Bash/Read/Write/Grep/Glob | run_diagnostic_command/query_database/read_log_file/search_knowledge_base | ✅ 對等 |

**測試驗證**：✅ 3 個 agents 同時觸發 approval（LogExpert/AppExpert/SecurityExpert），SecurityExpert 被 Approve → 立即恢復，**單 worker 運作**

---

### 7. 錯誤處理與恢復

| 功能 | CC | IPA V4 | 狀態 |
|------|-----|--------|------|
| Graceful shutdown | `shutdown_request` + agent 確認 | `SHUTDOWN_REQUEST` + `SHUTDOWN_ACK` | ✅ 對等 |
| Hard kill | `AbortController.abort()` | `shutdown_event.set()` + `task.cancel()` | ✅ 對等 |
| 權限拒絕追蹤 | `maxConsecutive=3`, `maxTotal=20` | 無（PoC 未實作） | ⚠️ IPA 缺失 |
| Retry 機制 | 無明確 retry | V4: classify_error + exponential backoff（2 retries） | ✅ IPA 更優 |
| Task 重分配 | 無 | V4: `reassign_task()` 失敗後返回 PENDING | ✅ IPA 更優 |
| Error 分類 | 無 | TRANSIENT/FATAL/UNKNOWN 三級分類 | ✅ IPA 更優 |
| Dead session recovery | iTerm2 dead session pruning | N/A（server-side 無 session） | ✅ 架構適應 |

**測試驗證**：⚠️ 本次測試 LLM 未出錯，retry 機制未觸發（代碼就緒）

---

### 8. Shutdown 與清理

| 功能 | CC | IPA V4 | 狀態 |
|------|-----|--------|------|
| Shutdown 協議 | `shutdown_request` → agent 確認 → cleanup | `SHUTDOWN_REQUEST` → `SHUTDOWN_ACK` → `shutdown_event` | ✅ 對等 |
| 10-step cleanup | MCP/hooks/tracking/fileState/perfetto/todos/shell/初始訊息/transcript/lock | emit SWARM_WORKER_END + clear shared state | ⚠️ IPA 較簡單（server-side 需清理較少資源） |
| Timeout fallback | 無明確 timeout | 10s ACK timeout → force-kill | ✅ IPA 有安全措施 |
| 孤兒進程防護 | `registerCleanupHandler()` SIGHUP | `asyncio.wait(timeout=5)` + `task.cancel()` | ✅ 對等 |
| Team 刪除 | `TeamDeleteTool` kill all + clean mailbox + remove team file | `approval_manager.clear()` + Redis TTL 自動清理 | ✅ 對等 |

**測試驗證**：✅ 3 agents ACK，2 agents force-killed，`team_complete` 事件觸發

---

### 9. 即時可視化

| 功能 | CC | IPA V4 | 狀態 |
|------|-----|--------|------|
| 事件串流 | Terminal polling + React hooks | SSE event-driven real-time streaming | ✅ IPA 更優 |
| Agent 狀態卡片 | Terminal pane（text-based） | React UI 卡片（Running/Idle/Completed/Shutdown） | ✅ IPA 更優 |
| 定向通訊顯示 | Terminal text | `→` 箭頭 + agent 名稱 + 訊息內容 | ✅ IPA 更優 |
| 任務進度條 | 無 | Tasks: X/Y completed 進度條 | ✅ IPA 更優 |
| Activity Log | 無集中 log | 時間戳 + 事件類型 + agent 名稱 | ✅ IPA 更優 |
| Synthesis 面板 | Terminal 文字輸出 | Markdown 渲染的統一分析報告 | ✅ IPA 更優 |
| HITL 審批 UI | Permission dialog（terminal） | Approve/Reject 按鈕 + loading 狀態 | ✅ IPA 更優（web UI） |
| 色彩區分 | `assignTeammateColor()` palette | Agent 卡片顏色 | ✅ 對等 |

**測試驗證**：✅ 完整 SSE 串流、5 agent 卡片、5 條通訊訊息、Activity Log 時間戳、Synthesis 報告

---

### 10. Memory 與 Context

| 功能 | CC | IPA V4 | 狀態 |
|------|-----|--------|------|
| Agent 隔離 context | `AsyncLocalStorage` + `TeammateContext` | Per-coroutine context in asyncio.gather | ✅ 對等 |
| 跨 session 記憶 | Sidechain transcript（per-agent disk 記錄） | V4: mem0/Qdrant 長期記憶 + transcript storage | ✅ IPA 更優（向量搜索） |
| Pre-execution retrieval | 無 | V4: `retrieve_for_goal()` 注入 past findings | ✅ IPA 更優 |
| Post-execution storage | Sidechain transcript append | V4: `store_synthesis()` + `store_transcript()` | ✅ 對等 |
| Context window 管理 | Auto-compaction in `inProcessRunner.ts` | 無（依賴 MAF Agent 內建） | ⚠️ IPA 缺失 |
| Cache sharing | Fork cache sharing via `CacheSafeParams` | 無 | ❌ 不適用（server-side LLM 無 prompt cache） |

**測試驗證**：✅ `Memory: retrieved 1 relevant memories (229 chars)` + `Memory: stored synthesis` + `Retrieved 25 memories for user`

---

### 11. 可擴展性

| 功能 | CC | IPA V4 | 狀態 |
|------|-----|--------|------|
| Max agents | 10+ in-process, 50+ pane | 2-8（TEAM_MAX_AGENTS 環境變數） | ⚠️ IPA 較低（PoC 限制） |
| 併發控制 | Pane creation mutex | `Semaphore(3)` LLM 併發 + ThreadPoolExecutor | ✅ 對等 |
| 資源清理 | Eviction grace period + periodic GC | Redis TTL 3600s 自動清理 | ✅ 對等 |
| Context overflow | Auto-compaction | 無 | ⚠️ IPA 缺失 |
| MCP per agent | 獨立 MCP initialization | N/A（server-side） | ✅ 架構適應 |

**測試驗證**：✅ 5 agents 成功並行，`TEAM_MAX_AGENTS` 控制數量

---

### 12. 結果彙整

| 功能 | CC | IPA V4 | 狀態 |
|------|-----|--------|------|
| 結果提取 | `extractPartialResult()` from incomplete agents | 直接從 agent coroutine 收集 | ✅ 對等 |
| Lead Synthesis | 手動 polling + 合併 | Phase 2 自動 LLM Synthesis（獨立 LLM call） | ✅ IPA 更優 |
| 報告格式 | Plain text | Markdown 結構化報告（Executive Summary + Findings + Next Steps） | ✅ IPA 更優 |
| 進度追蹤 | Token/message count | SSE task_completed + team_complete 事件 | ✅ 對等 |
| 跨 agent 關聯 | 無 | Synthesis 自動關聯多 agent 發現 | ✅ IPA 更優 |

**測試驗證**：✅ TeamLead Synthesis 產出完整報告（Executive Summary、5 sections、Prioritized Root Cause、Next Steps）

---

### 13. 安全與沙箱

| 功能 | CC | IPA V4 | 狀態 |
|------|-----|--------|------|
| 保護路徑 | `.git/`, `.claude/`, `.vscode/`（bypass-immune） | N/A（server-side 無本地文件系統） | ✅ 架構適應 |
| 命令安全 | 23 bash security checks | ALLOWED_COMMANDS whitelist + FORBIDDEN_PATTERNS | ✅ 對等（形式不同） |
| SQL 安全 | 無（用戶自己控制） | SELECT-only validation + statement_timeout | ✅ IPA 更優 |
| 路徑白名單 | 無 | `_validate_log_path()` — `/var/log/*`, `/app/logs/*` only | ✅ IPA 更優 |
| Agent 權限過濾 | `filterDeniedAgents()` | 無（所有 agent 共用相同 tools） | ⚠️ IPA 缺失 |
| Worktree 隔離 | `isolation: 'worktree'` git worktree | 無 | ❌ 不適用（server-side） |

**測試驗證**：✅ HITL approval 觸發 query_database（HIGH risk tool），user approve 後才執行

---

## 總結統計

| 類別 | 總功能數 | ✅ 對等或更優 | ⚠️ IPA 較簡單 | ❌ 缺失/不適用 |
|------|---------|-------------|--------------|--------------|
| 1. Agent 建立 | 6 | 3 | 1 | 2 |
| 2. 並行執行 | 5 | 5 | 0 | 0 |
| 3. 生命週期 | 7 | 6 | 1 | 0 |
| 4. 通訊 | 8 | 8 | 0 | 0 |
| 5. 任務管理 | 7 | 7 | 0 | 0 |
| 6. 工具權限 | 8 | 6 | 2 | 0 |
| 7. 錯誤處理 | 7 | 5 | 1 | 0 |* |
| 8. Shutdown | 5 | 4 | 1 | 0 |
| 9. 可視化 | 8 | 8 | 0 | 0 |
| 10. Memory | 6 | 4 | 1 | 1 |
| 11. 可擴展性 | 5 | 3 | 2 | 0 |
| 12. 結果彙整 | 5 | 5 | 0 | 0 |
| 13. 安全沙箱 | 6 | 4 | 1 | 1 |
| **合計** | **83** | **68 (82%)** | **10 (12%)** | **4 (5%)** |

### IPA 優於 CC 的維度（12 項）

1. **Redis Stream 通訊**（比 file mailbox 更適合 server-side）
2. **TeamLead 自動任務分解**（CC 需手動分派）
3. **Work-stealing 任務認領**（agent 自助認領 vs lead 指派）
4. **Task 重分配**（失敗後自動返回 PENDING）
5. **Priority + expertise matching**（任務優先級和專長匹配）
6. **Retry + error classification**（三級錯誤分類 + exponential backoff）
7. **SSE event-driven streaming**（比 terminal polling 更即時）
8. **Web UI 可視化**（卡片/進度條/Activity Log/Synthesis 面板）
9. **HITL 審批 Web UI**（比 terminal dialog 更友好）
10. **Pre-execution memory retrieval**（向量搜索過去經驗）
11. **Phase 2 自動 Synthesis**（LLM 自動彙整 vs 手動合併）
12. **SQL/Path 安全白名單**（server-side 特有安全措施）

### IPA 較弱或缺失的維度（14 項）

| 功能 | 原因 | 是否需要修復 |
|------|------|-------------|
| Agent routing 6-way | Server-side 不需要 fork/remote/pane | 不需要 |
| Per-agent model 選擇 | 可實作但 PoC 未做 | 後續可加 |
| MCP 過濾 | Server-side 無 MCP | 不需要 |
| 10-step cleanup | Server-side 需清理的資源較少 | 低優先 |
| 7 種權限模式 | PoC 用 2 種足夠 | 後續可擴展 |
| 9-step 權限 cascade | PoC 用 whitelist 足夠 | 後續可擴展 |
| 權限拒絕追蹤 | 可實作 | 後續可加 |
| Context window 管理 | 依賴 MAF Agent 內建 | 中優先 |
| Cache sharing | Server-side LLM 無 prompt cache | 不需要 |
| Max agents 50+ | PoC 8 個足夠 | 後續可擴展 |
| Context overflow protection | 可實作 | 中優先 |
| Per-agent 權限過濾 | 可實作 | 後續可加 |
| Worktree 隔離 | Server-side 不需要 | 不需要 |
| Fork 遞歸防護 | Server-side 不需要 | 不需要 |

---

*報告生成時間: 2026-04-09 19:45 UTC+8*
*基於 CC 源碼分析 30 waves + IPA V4 測試 commit 60ef956*
