# 14 - Sprint Wiring Fix 001 — Execution Checklist

**配對文件**：`14-sprint-wiring-fix-001-plan.md`
**Sprint Goal**：修復 M-01 (search_memory) + HITL-01 (request_approval) 兩個 silent broken tool
**預計時長**：1-2 工作天

---

## Phase 1：前置調查（<2 小時）

### 1.1 代碼準備
- [ ] 從 main 開新 branch：`git checkout -b fix/wiring-m01-hitl01`
- [ ] 驗證 main 係 latest：`git pull origin main`
- [ ] 確認 worktree 無 uncommitted changes

### 1.2 代碼讀取（修復前必做）
- [ ] 讀 `backend/src/integrations/memory/unified_memory.py` 完整
  - [ ] 確認 `MemorySearchResult` dataclass 欄位與 `.to_dict()` 方法
  - [ ] 確認 `search()` 三層結果 merge 邏輯
  - [ ] 驗證 `initialize()` 是否 idempotent（singleton 安全）
- [ ] 讀 `backend/src/integrations/orchestration/hitl/controller.py` 完整
  - [ ] 確認 `HITLController.__init__` 簽名（是否需 `checkpoint_storage` DI）
  - [ ] 確認 `request_approval()` 存在、簽名、返回類型
  - [ ] 確認 Teams notification trigger 邏輯
- [ ] 讀 `backend/src/integrations/hybrid/orchestrator/dispatch_handlers.py` 完整
  - [ ] 確認 `DispatchHandlers.__init__` 現有 state（singleton pattern 在哪加）
  - [ ] 確認其他 handler 是否有類似 broken stub

### 1.3 測試基礎
- [ ] 驗證 local 環境 Qdrant + mem0 + PostgreSQL 都在運行
- [ ] 執行現有 dispatch_handlers tests：`pytest backend/tests/unit/test_dispatch_handlers.py -v`
- [ ] 確認 baseline pass

---

## Phase 2：M-01 修復（0.5-1 天）

### 2.1 DispatchHandlers class 改動
- [ ] 在 `DispatchHandlers.__init__` 加 `self._memory_manager: Optional[UnifiedMemoryManager] = None`
- [ ] 新增 `async def _get_memory_manager(self)` lazy singleton method
- [ ] 確認類型 annotation 正確（import `UnifiedMemoryManager` 於 TYPE_CHECKING）

### 2.2 handle_search_memory 重寫
- [ ] 移除 `from src.integrations.memory.mem0_service import Mem0Service` line
- [ ] 加 `if user_id is None:` early return with clear error
- [ ] Call `self._get_memory_manager()` 取得 singleton
- [ ] Call `manager.search(query=query, user_id=user_id, limit=limit)`
- [ ] Serialize `List[MemorySearchResult]` → list of dicts（用 `.to_dict()` 或 `dataclasses.asdict()`）
- [ ] 返回 envelope 加 `tool_broken`, `layers_searched` 欄位

### 2.3 M-01 Unit Tests（`backend/tests/unit/test_dispatch_handlers.py`）
- [ ] Test: `handle_search_memory(user_id=None)` 返回 `error: "user_id required"`
- [ ] Test: `handle_search_memory` 傳 valid args，mock UnifiedMemoryManager，驗證 call args
- [ ] Test: Singleton 驗證 — 兩次 call 應用同一 manager instance
- [ ] Test: UnifiedMemoryManager.search raise Exception → 返回 `tool_broken: True`

### 2.4 M-01 Integration Test（新檔 `backend/tests/integration/test_dispatch_handlers_memory.py`）
- [ ] Setup: 透過 `/api/v1/memory/` POST 寫入 3 條 test memory（user_id=test_user_001）
- [ ] Call `DispatchHandlers().handle_search_memory(query="...", user_id="test_user_001", limit=5)`
- [ ] Assert `count > 0` 且 `results[0]` 含 predictable content
- [ ] Assert `layers_searched` 包含 "working" 或 "session" 或 "long_term"
- [ ] Cleanup: 刪除 test memory

### 2.5 M-01 手動驗證
- [ ] 啟動 backend dev server
- [ ] Frontend 用 subagent/team mode 發問（包含 memory-dependent query）
- [ ] 觀察 backend log：應看到 `UnifiedMemoryManager.search` call 非 "Memory service not available"
- [ ] `grep -r "from src.integrations.memory.mem0_service" backend/` → 0 hits ✅

---

## Phase 3：HITL-01 修復（0.5 天）

### 3.1 DispatchHandlers 擴展
- [ ] 在 `DispatchHandlers.__init__` 加 `self._hitl_controller: Optional[HITLController] = None`
- [ ] 確認 HITLController 是否需 `checkpoint_storage` 依賴注入；若是，從 DispatchHandlers 層接入

### 3.2 handle_request_approval 重寫
- [ ] 移除 "# In full integration, would call controller.request_approval()" TODO comment
- [ ] 實際 call `self._hitl_controller.request_approval(...)`
- [ ] 確保 approval record 實際寫入 PostgreSQL
- [ ] 確保 Teams notification trigger（若 env 已設）
- [ ] 返回真實 `approval_id` 非 `uuid.uuid4()` 空殼

### 3.3 HITL-01 Unit Tests
- [ ] Test: mock HITLController.request_approval，驗證 call args
- [ ] Test: ImportError case 返回 `tool_broken: True`
- [ ] Test: request_approval raise Exception → error envelope

### 3.4 HITL-01 Integration Test（新檔 `backend/tests/integration/test_dispatch_handlers_approval.py`）
- [ ] Call `handle_request_approval(title="Test", description="...", risk_level="high", user_id="test_user")`
- [ ] Assert `approval_id` non-null 且格式符合 HITLController 規範
- [ ] Query `/api/v1/orchestration/approvals/{approval_id}` 驗證 record 存在
- [ ] （Optional）驗證 Teams notification API 被 call（mock）

### 3.5 HITL-01 手動驗證
- [ ] 透過 team mode 觸發 high-risk operation（或直接 call tool API）
- [ ] 驗證 approval record 出現喺 `/api/v1/orchestration/approvals/` list
- [ ] 在 frontend HITL UI 可見此 approval，可操作 approve/reject
- [ ] `grep "In full integration, would call" backend/` → 0 hits ✅

---

## Phase 4：Code Quality Gates（<1 小時）

- [ ] `cd backend && black .` — 無 change
- [ ] `cd backend && isort .` — 無 change
- [ ] `cd backend && flake8 .` — 無 error
- [ ] `cd backend && mypy src/integrations/hybrid/orchestrator/dispatch_handlers.py` — 無 error
- [ ] `cd backend && pytest tests/unit/test_dispatch_handlers.py -v` — 全 pass
- [ ] `cd backend && pytest tests/integration/test_dispatch_handlers_*.py -v` — 全 pass
- [ ] Coverage report：dispatch_handlers.py 整體 coverage ≥ 85%

---

## Phase 5：文件與記錄（<1 小時）

### 5.1 Bug Fix 記錄
- [ ] 建 `claudedocs/4-changes/bug-fixes/FIX-001-search-memory-broken-import.md`
  - 內容：problem / root cause / fix / verification
- [ ] 建 `claudedocs/4-changes/bug-fixes/FIX-002-request-approval-stub-implementation.md`
  - 同上格式

### 5.2 Doc 更新
- [ ] 更新 `docs/09-git-worktree-working-folder/knowledge-base-enterprise/10-wiring-audit.md`：
  - M-01 標記為 ✅ Fixed（version 1.1）
  - HITL-01 加入 gap 清單並標記 ✅ Fixed
  - 修正 M-01 建議代碼（`search_memory` → `search`）
- [ ] 更新 `docs/09-git-worktree-working-folder/knowledge-base-enterprise/11-agent-team-review.md`：
  - 修復矩陣中 M-01 / HITL-01 標 ✅

### 5.3 進度 log
- [ ] 建 `claudedocs/3-progress/daily/2026-04-XX-sprint-wiring-fix-001-progress.md`
  - 記錄實際 start/end time
  - 遇到嘅 blocker
  - 學到嘅 insight

---

## Phase 6：Git Commit & PR（<0.5 小時）

### 6.1 Commit 準備
- [ ] `git status` 確認改動範圍符合 Plan 嘅 File Change List
- [ ] `git diff --staged` review 確認無誤
- [ ] 驗證無 secret / 無 binary / 無建構 artifact

### 6.2 Commits（建議分 2 個 commit，對應 2 個 fix）
- [ ] Commit 1：`fix(hybrid): replace broken Mem0Service import with UnifiedMemoryManager (FIX-001)`
  - Body 描述 M-01 問題與修復
- [ ] Commit 2：`fix(hybrid): implement request_approval tool to actually call HITLController (FIX-002)`
  - Body 描述 HITL-01 問題與修復

### 6.3 PR（若用 GitHub flow）
- [ ] `git push -u origin fix/wiring-m01-hitl01`
- [ ] `gh pr create --title "fix(wiring): M-01 + HITL-01 — silent broken tool fixes"`
  - Body 包含：
    - Problem description（link Doc 10, 11）
    - Fix summary
    - Test plan（link integration tests）
    - Verification checklist（本文件關鍵條目）
- [ ] 等 CI 通過
- [ ] Request review

### 6.4 Merge
- [ ] 合併入 main
- [ ] 刪除 feature branch
- [ ] 確認 production deploy pipeline（若有）觸發

---

## Phase 7：Retrospective（30 分鐘）

Sprint 結束後填：

- [ ] **實際時長** vs 預估 1-2 天：___________
- [ ] **實際 story points delivered**：___________
- [ ] **Blockers 遇到**：___________
- [ ] **Plan 需要調整嘅地方**：___________
- [ ] **Sprint workflow（plan→checklist→code→progress）是否順暢**：___________
- [ ] **CLAUDE.md 有冇需要新增 rules**（例如 dispatch handler 開發紀律）：___________

---

## Phase 8：後續 sprint 啟動

- [ ] 若 Workshop 已完成：即啟 `Sprint Wiring Fix 002`（K-01 + E-01，依 Workshop Q10 / Q12 答案）
- [ ] 若 Workshop 未完成：提醒 stakeholder close Q5 / Q7 / Q10 / Q12 以啟 A-01 + K-01 sprint
- [ ] 寫 `15-sprint-wiring-fix-002-plan.md` 草稿（待 Workshop 答案填入）

---

## 進度追蹤

| Phase | 狀態 | 開始 | 完成 |
|-------|------|------|------|
| 1 前置調查 | ⏳ | | |
| 2 M-01 修復 | ⏳ | | |
| 3 HITL-01 修復 | ⏳ | | |
| 4 Code Quality | ⏳ | | |
| 5 文件記錄 | ⏳ | | |
| 6 Git Commit | ⏳ | | |
| 7 Retrospective | ⏳ | | |
| 8 下個 sprint | ⏳ | | |

**圖例**：⏳ Pending / 🔄 In Progress / ✅ Done / ⚠️ Blocked

---

**版本**

| Version | Date | Author |
|---------|------|--------|
| 1.0 | 2026-04-20 | Claude + Chris |

**配對 Plan**：`14-sprint-wiring-fix-001-plan.md`
