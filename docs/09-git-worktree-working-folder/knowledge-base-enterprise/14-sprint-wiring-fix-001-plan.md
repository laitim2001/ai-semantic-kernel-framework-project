# 14 - Sprint Wiring Fix 001 — Plan

**Sprint Name**：Wiring Fix Sprint 001 — M-01 + HITL-01 修復
**Sprint Type**：Bug Fix Sprint（bundle of 2 CRITICAL + HIGH gap）
**預計 Story Points**：3 pts（M-01: 2 pts + HITL-01: 1 pt，含測試）
**預計時長**：1-2 工作天
**分支建議**：`fix/wiring-m01-hitl01`（從 main 開新 branch）
**依賴**：無（獨立於 Workshop 決策）
**前置文件**：Doc 10（Wiring Audit）、Doc 11（Agent Panel Review code-reviewer 驗證）

---

## 一、Sprint Goal

修復兩個 dispatch_handlers 中嘅 silent broken tool，令 agent 主動調用 `search_memory` 與 `request_approval` 能真正 execute 而非返回假 response。

**Why this sprint first**：
- Panel 一致認為係 **風險最低、ROI 最高**嘅 P0
- **無依賴** Workshop 決策
- **驗證** sprint workflow（plan → checklist → branch → code → progress → commit）
- M-01 + HITL-01 同模式（handler 內 import/call 問題），可 bundle
- Agent 使用 search_memory / request_approval 會影響 80% subagent/team mode query 嘅 decision quality

---

## 二、User Stories

### Story 1：search_memory tool 修復（M-01）

**作為** subagent/team mode 嘅 expert agent
**我希望** 當我 call `search_memory` tool 時能真正查詢 user memory 並收到結果
**以便** 我基於過往對話 / 偏好做更準確嘅決策

**目前行為**：
```
agent → tool_call(search_memory) 
  → dispatch_handlers.py:364 from src.integrations.memory.mem0_service import Mem0Service
  → ModuleNotFoundError（mem0_service 不存在）
  → except ImportError 靜默返回 {"results": [], "message": "Memory service not available"}
  → agent LLM 見到空 results 當成「用戶無相關 memory」繼續推理
```

**修復後行為**：
```
agent → tool_call(search_memory, query=..., user_id=...)
  → dispatch_handlers → UnifiedMemoryManager.search(query, user_id, limit=5)
  → 返回 WORKING + SESSION + LONG_TERM 三層搜索結果，sorted by relevance
  → agent 收到實際 memory，可 ground decision
```

### Story 2：request_approval tool 修復（HITL-01）

**作為** subagent/team mode 嘅 expert agent
**我希望** 當我 call `request_approval` tool 時能真正觸發 HITL workflow
**以便** 高風險操作確實被 human reviewer 審批

**目前行為**（`dispatch_handlers.py:379-405`）：
```python
async def handle_request_approval(...):
    approval_id = str(uuid.uuid4())
    try:
        from src.integrations.orchestration.hitl.controller import HITLController
        controller = HITLController()
        logger.info("Requesting approval: %s (risk=%s)", title, risk_level)
        # In full integration, would call controller.request_approval()  ← 永遠 TODO
    except ImportError:
        ...
    return {
        "approval_id": approval_id,
        "status": "pending",  # hardcoded，無實際 HITL workflow
        ...
    }
```

**修復後行為**：
- 實際 call `controller.request_approval(...)` 觸發 Teams 通知 + checkpoint persist
- 返回真實 approval workflow ID（非 uuid.uuid4() 空殼）
- Approval record 寫入 PostgreSQL 可後續追溯

---

## 三、Technical Specification

### 3.1 M-01 修復

**檔案**：`backend/src/integrations/hybrid/orchestrator/dispatch_handlers.py`
**行數**：355-377

**關鍵 API 事實**（已驗證於 `unified_memory.py:304-358`）：
```python
class UnifiedMemoryManager:
    async def search(
        self,
        query: str,
        user_id: str,                      # REQUIRED, no default
        memory_types: Optional[List[MemoryType]] = None,
        layers: Optional[List[MemoryLayer]] = None,
        min_importance: float = 0.0,
        limit: int = 10,
    ) -> List[MemorySearchResult]:
```

**修復代碼**（替換 lines 355-377）：

```python
# Class-level singleton for RAGPipeline-style lazy init
# Add to __init__ of DispatchHandlers:
#     self._memory_manager: Optional[UnifiedMemoryManager] = None

async def _get_memory_manager(self):
    """Lazy singleton initializer for UnifiedMemoryManager."""
    if self._memory_manager is None:
        from src.integrations.memory.unified_memory import UnifiedMemoryManager
        self._memory_manager = UnifiedMemoryManager()
        await self._memory_manager.initialize()
    return self._memory_manager

async def handle_search_memory(
    self,
    query: str,
    user_id: Optional[str] = None,
    limit: int = 5,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Search user memory via UnifiedMemoryManager (3-layer)."""
    if user_id is None:
        logger.warning("search_memory called without user_id")
        return {
            "results": [],
            "count": 0,
            "error": "user_id required",
            "tool_broken": False,
        }
    try:
        manager = await self._get_memory_manager()
        results = await manager.search(
            query=query,
            user_id=user_id,
            limit=limit,
        )
        # MemorySearchResult is a dataclass — use dataclasses.asdict or .to_dict()
        return {
            "results": [r.to_dict() if hasattr(r, "to_dict") else dataclasses.asdict(r) for r in results],
            "count": len(results),
            "layers_searched": ["working", "session", "long_term"],
        }
    except Exception as e:
        logger.error("Memory search failed: %s", e, exc_info=True)
        return {
            "results": [],
            "count": 0,
            "error": str(e)[:200],
            "tool_broken": True,
        }
```

**關鍵差異 vs 原 Doc 10 建議**：
- ✅ 用 `.search()`（正確方法名），**非** `.search_memory()`
- ✅ `user_id` 必填處理（`None` → early return with error，非 crash）
- ✅ Singleton pattern（非每次 new instance）
- ✅ 統一 error envelope 加 `tool_broken` flag（下游 observability）

### 3.2 HITL-01 修復

**檔案**：`backend/src/integrations/hybrid/orchestrator/dispatch_handlers.py`
**行數**：379-405

**修復代碼**：

```python
async def handle_request_approval(
    self,
    title: str,
    description: str,
    risk_level: str = "medium",
    user_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Request human-in-the-loop approval via HITLController."""
    try:
        from src.integrations.orchestration.hitl.controller import HITLController
        if self._hitl_controller is None:
            self._hitl_controller = HITLController()
            # Note: HITLController may need dependency injection (checkpoint_storage)
            # — verify exact constructor before finalizing
        
        # ACTUAL call (not just logger.info)
        approval_request = await self._hitl_controller.request_approval(
            title=title,
            description=description,
            risk_level=risk_level,
            user_id=user_id,
            trace_id=trace_id,
        )
        
        return {
            "approval_id": approval_request.approval_id,
            "status": approval_request.status,  # Actual status from controller
            "title": title,
            "risk_level": risk_level,
            "teams_notification_sent": approval_request.notified,
            "tool_broken": False,
        }
    except ImportError:
        logger.error("HITLController not available")
        return {
            "approval_id": None,
            "status": "error",
            "error": "HITL system not available",
            "tool_broken": True,
        }
    except Exception as e:
        logger.error("Approval request failed: %s", e, exc_info=True)
        return {
            "approval_id": None,
            "status": "error",
            "error": str(e)[:200],
            "tool_broken": True,
        }
```

**前置工作**（需先讀代碼確認）：
- [ ] `HITLController.__init__` 簽名（是否需 `checkpoint_storage` 依賴注入？）
- [ ] `HITLController.request_approval()` 方法是否存在、返回類型
- [ ] Approval record 序列化欄位

---

## 四、File Change List

| File | Change Type | 描述 |
|------|------------|------|
| `backend/src/integrations/hybrid/orchestrator/dispatch_handlers.py` | Modify | 修改 `handle_search_memory`（M-01）+ `handle_request_approval`（HITL-01）+ 加 singleton helpers |
| `backend/tests/integration/test_dispatch_handlers_memory.py` | Create | Integration test: search_memory end-to-end |
| `backend/tests/integration/test_dispatch_handlers_approval.py` | Create | Integration test: request_approval end-to-end |
| `backend/tests/unit/test_dispatch_handlers.py` | Modify | Unit test coverage for error cases（user_id missing / import fail）|
| `docs/09-git-worktree-working-folder/knowledge-base-enterprise/10-wiring-audit.md` | Update | 修正 M-01 修復建議（API 名）、標記 HITL-01 為已修復 |
| `claudedocs/4-changes/bug-fixes/FIX-001-search-memory-broken-import.md` | Create | Bug fix 記錄 |
| `claudedocs/4-changes/bug-fixes/FIX-002-request-approval-stub-implementation.md` | Create | Bug fix 記錄 |

---

## 五、Acceptance Criteria

### M-01
- [ ] `grep "from src.integrations.memory.mem0_service" backend/` 返回 0 hits
- [ ] `UnifiedMemoryManager` import 成功，`.search(query, user_id, limit)` 可正常 call
- [ ] Integration test：寫入 memory via `/api/v1/memory/`，然後 subagent call `search_memory` 能返回寫入記錄
- [ ] `user_id=None` case 返回清晰 error（非靜默）
- [ ] 連續 100 次 call 不產生多個 UnifiedMemoryManager instance（驗證 singleton）

### HITL-01
- [ ] `grep "# In full integration, would call" backend/` 返回 0 hits（移除 TODO）
- [ ] 實際 call `controller.request_approval()`
- [ ] Approval record 寫入 PostgreSQL（可透過 `/api/v1/orchestration/approvals/{id}` 查到）
- [ ] Teams notification 可送出（若 env var 已設）
- [ ] Integration test：subagent call request_approval → 產生實際 approval workflow → approver action → resume

### 通用
- [ ] 所有 dispatch_handler 返回 envelope 含 `tool_broken: bool` flag
- [ ] `pytest backend/tests/integration/test_dispatch_handlers_*.py` 全部 pass
- [ ] Black / isort / flake8 / mypy clean

---

## 六、Out of Scope（留給後續 sprint）

- K-01 Knowledge wiring 統一 → **Sprint Wiring Fix 002**（依賴 Workshop Q10/Q12）
- E-01 embedding model 三處漂移 → **合併入 K-01 sprint**
- A-01 main chat audit emission → **Sprint Wiring Fix 003**（依賴 Workshop Q5/Q7）
- A-02/A-03 orphan AuditLogger 處理 → **併入 A-01 sprint**
- C-01/C-02 Context state 補全 → **Sprint State Integrity 001**
- K-06 Cohere Rerank 3 替換 → **Perf Sprint 001**（1 週獨立 quick win）

---

## 七、Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `HITLController.request_approval()` API 與預期不同 | Medium | Medium | Day 1 先讀 controller.py 代碼，若 API 差異大提早 flag |
| `MemorySearchResult.to_dict()` 不存在 | Low | Low | fallback to `dataclasses.asdict()` |
| UnifiedMemoryManager singleton 在多個 request 共享導致 race | Low | Medium | Integration test 含 concurrent call；必要時加 asyncio.Lock |
| mem0 backend 未運行（Qdrant / Ollama local）| Medium | Low | Graceful degradation 返回 `tool_broken: True` |
| Approval record schema migration | Low | High | 確認 PostgreSQL schema 已就緒 before coding |

---

## 八、Execution Checklist（對應 CLAUDE.md Sprint Workflow）

詳見 `14-sprint-wiring-fix-001-checklist.md`（同時交付）。

---

## 九、Sprint Metrics

**Pre-Sprint**（baseline）：
- search_memory tool 成功率：**~0%**（永久 import fail）
- request_approval tool 實效：**~0%**（無實際 controller call）

**Post-Sprint Target**：
- search_memory tool 成功率：**>95%**（5% 容忍 user_id 缺失 / backend 不可用）
- request_approval tool 實效：**>98%**（approval record 真實寫入 PG）
- Integration test coverage：新增 2 檔，>80% 覆蓋 happy path + 3 error cases

---

## 十、Post-Sprint Follow-up

Sprint 完成後：
1. 更新 `10-wiring-audit.md` 將 M-01 / HITL-01 標記為 ✅ Fixed
2. 更新 `11-agent-team-review.md` 修復矩陣
3. 寫 `claudedocs/3-progress/daily/` 進度 log
4. Retrospective：sprint workflow 是否順暢？有冇 CLAUDE.md 需更新嘅 rules？
5. 啟動 Workshop（若尚未召開）+ Sprint Wiring Fix 002 plan（K-01 + E-01）

---

## 十一、版本記錄

| Version | Date | Author |
|---------|------|--------|
| 1.0 | 2026-04-20 | Claude + Chris |

**Related docs**：
- Doc 10 — Wiring Audit（M-01 / HITL-01 原始描述）
- Doc 11 — Agent Team Review（code-reviewer API 糾正）
- Doc 13 — Workshop Agenda
- Doc 14-checklist — Execution checklist
