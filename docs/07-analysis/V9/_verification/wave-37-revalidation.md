# Wave 37: Re-validation of Wave 36R Corrections (Layer 10 + Layer 11)

> Verifier: Claude Opus 4.6 (1M context)
> Date: 2026-03-31
> Scope: 50-point verification of Wave 36R corrections

---

## Layer 10: Domain Layer (25 pts)

### P1-P5: Session activate() 狀態轉換修正

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| P1 | `activate()` accepts CREATED or SUSPENDED | ✅ | `models.py:475`: `if self.status not in [SessionStatus.CREATED, SessionStatus.SUSPENDED]` |
| P2 | `activate()` checks not expired | ✅ | `models.py:477-478`: `if self.is_expired(): raise ValueError` |
| P3 | `activate()` extends expiry | ✅ | `models.py:481`: `self._extend_expiry()` |
| P4 | `resume()` only accepts SUSPENDED | ✅ | `models.py:500`: `if self.status != SessionStatus.SUSPENDED` |
| P5 | Doc correctly describes both transitions | ✅ | Doc L292-293 matches: `CREATED -> ACTIVE` via activate, `SUSPENDED -> ACTIVE` via activate OR resume |

### P6-P8: ExecutionEventType 10 個成員

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| P6 | Enum has exactly 10 members | ✅ | `events.py:41-56`: CONTENT, CONTENT_DELTA, TOOL_CALL, TOOL_RESULT, APPROVAL_REQUIRED, APPROVAL_RESPONSE, STARTED, DONE, ERROR, HEARTBEAT |
| P7 | 4 categories correctly documented | ✅ | Doc L317-332: Content(2), Tool(4), Status(3), System(1) = 10 |
| P8 | Event type names match source | ✅ | All 10 names in doc table match enum values exactly |

### P9-P12: CheckpointService 方法

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| P9 | Doc lists 11 methods | ✅ | Doc L606-618 lists: create_checkpoint, get_checkpoint, get_pending_approvals, get_checkpoints_by_execution, approve_checkpoint (DEP), reject_checkpoint (DEP), expire_old_checkpoints, get_stats, delete_checkpoint, create_checkpoint_with_approval, handle_approval_response |
| P10 | Source has same 11 methods | ✅ | `service.py` grep confirms all 11 async methods at lines 223, 273, 289, 311, 333, 397, 461, 475, 490, 530, 607 |
| P11 | Deprecation status correct | ✅ | approve_checkpoint and reject_checkpoint marked DEPRECATED in both doc and source |
| P12 | Bridge methods documented | ✅ | create_checkpoint_with_approval and handle_approval_response correctly described as bridge pattern |

### P13-P15: 狀態機 6 states

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| P13 | ExecutionStatus has 6 states | ✅ | `state_machine.py:47-52`: PENDING, RUNNING, PAUSED, COMPLETED, FAILED, CANCELLED |
| P14 | Terminal states correct | ✅ | Source L44: "Terminal States: COMPLETED, FAILED, CANCELLED (no transitions out)" |
| P15 | Doc L644 matches source | ✅ | Doc: "6-state execution lifecycle (PENDING→RUNNING→PAUSED→COMPLETED/FAILED/CANCELLED)" |

### P16-P20: 修正周邊內容是否仍正確

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| P16 | ToolCall 6 states correct | ✅ | Doc L306-311: PENDING→APPROVED→RUNNING→COMPLETED, PENDING→REJECTED, RUNNING→FAILED |
| P17 | Dual event system description | ✅ | System 1: ExecutionEventFactory 10 types, System 2: SessionEventPublisher 17 types — both verified |
| P18 | AgentExecutor streaming simulation | ✅ | Doc L376-388 accurately describes simulated streaming with chunk_size=20 and asyncio.sleep(0.01) |
| P19 | ToolCallHandler permission system | ✅ | Doc L427: 4 levels AUTO/NOTIFY/APPROVAL_REQUIRED/DENIED |
| P20 | orchestration/ 22 files DEPRECATED | ✅ | Doc L499 correctly shows 22 files, ~11,465 LOC |

### P21-P25: 抽查 5 個 domain model 屬性

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| P21 | Agent.tools: JSONB, NOT NULL, default=list | ✅ | `agent.py:81-85`: `Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=list)` — Doc L306 correctly notes type annotation mismatch |
| P22 | User.role: VARCHAR(50), default="viewer" | ✅ | `user.py:73`: matches doc L289 |
| P23 | Execution.llm_cost: NUMERIC(10,6) | ✅ | `execution.py:115`: matches doc L347 |
| P24 | SessionModel.session_metadata: JSONB | ✅ | `session.py:100`: matches doc L391 "Avoids SA reserved word" |
| P25 | Checkpoint.node_id: VARCHAR(255), nullable | ✅ | `checkpoint.py:68-71`: `Mapped[str] = mapped_column(String(255), nullable=True)` — Doc L362 correct |

**Layer 10 Subtotal: 25/25 ✅**

---

## Layer 11: Infrastructure + Core (25 pts)

### P26-P28: infra 文件數 54

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| P26 | infrastructure/ has 54 .py files | ✅ | `find ... -name "*.py" | wc -l` = 54 |
| P27 | Doc L13 says 54 files | ✅ | Matches exactly |
| P28 | File tree inventory complete | ✅ | All subdirectories (database/18, storage/18, checkpoint/8, cache/2, messaging/1, distributed_lock/2, workers/3, root 2) = 54 |

### P29-P31: core 文件數 39

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| P29 | core/ has 39 .py files | ✅ | `find ... -name "*.py" | wc -l` = 39 |
| P30 | Doc L14 says 39 files | ✅ | Matches exactly |
| P31 | File tree inventory complete | ✅ | security/7, performance/11, sandbox/7, observability/4, logging/4, root 6 = 39 |

### P32-P34: security 7, performance 11

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| P32 | core/security/ has 7 .py files | ✅ | `find ... -name "*.py" | wc -l` = 7 |
| P33 | core/performance/ has 11 .py files | ✅ | `find ... -name "*.py" | wc -l` = 11 |
| P34 | Doc file tree matches | ✅ | Doc L216-235 lists all files correctly |

### P35-P37: storage_factories.py 函數數量

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| P35 | Source has 8 async factory functions | ✅ | Lines 70, 103, 141, 166, 196, 226, 258, 291 |
| P36 | Doc L556 says "8 factory functions" | ✅ | Matches source |
| P37 | Factory table lists all 8 | ⚠️ | Doc L558-567 table lists all 8 correctly, BUT file tree comment at L168 says "7 domain-specific factories" — minor inconsistency in the file tree annotation vs the detailed section |

### P38-P40: Agent tools column type 描述

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| P38 | Agent.tools JSONB type | ✅ | Source: `mapped_column(JSONB, nullable=False, default=list)` |
| P39 | Doc notes Mapped type mismatch | ✅ | Doc L306: "Mapped type annotation is `Dict[str, Any]` despite `default=list`" — accurate observation |
| P40 | Column constraints correct | ✅ | NOT NULL, default=list — matches doc |

### P41-P45: 修正周邊內容

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| P41 | Dual storage protocol issue | ✅ | Doc L493-509 accurately describes Sprint 110 ABC vs Sprint 119 Protocol incompatibility |
| P42 | BaseRepository methods | ✅ | Doc L458-465: create, get, get_by, list, update, delete, exists, count — standard CRUD |
| P43 | Redis cache layering (L1/L2/L3) | ✅ | Doc L101-117 correctly describes 3-tier cache: Working Memory 30min, Session Cache 7d, Persistent PG |
| P44 | Checkpoint unification 4 systems | ✅ | Doc L590-595 lists all 4 independent systems with correct origins |
| P45 | middleware/ 2 files, 107 LOC | ✅ | Doc L69-71 matches actual structure |

### P46-P50: ORM Column 抽樣再驗（5 models）

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| P46 | User.email: VARCHAR(255), UNIQUE, NOT NULL, INDEX | ✅ | `user.py:55` mapped_column confirmed; Doc L286 matches |
| P47 | Execution.workflow_id: UUID, FK, NOT NULL, INDEX | ✅ | `execution.py:65` mapped_column confirmed; Doc L339 matches |
| P48 | SessionModel.status: VARCHAR(20), NOT NULL, default="created", INDEX | ✅ | `session.py:68` mapped_column confirmed; Doc L386 matches |
| P49 | MessageModel.content: TEXT, NOT NULL, default="" | ✅ | `session.py:159` mapped_column confirmed; Doc L405 matches |
| P50 | Checkpoint.status: VARCHAR(50), nullable, default="pending", INDEX | ✅ | `checkpoint.py:95` mapped_column confirmed; Doc L366 matches |

**Layer 11 Subtotal: 24/25 ✅ + 1 ⚠️**

---

## Summary

| Category | Pass | Warn | Fail | Total |
|----------|------|------|------|-------|
| Layer 10 (P1-P25) | 25 | 0 | 0 | 25 |
| Layer 11 (P26-P50) | 24 | 1 | 0 | 25 |
| **Total** | **49** | **1** | **0** | **50** |

### Issues Found

| ID | Severity | Location | Description |
|----|----------|----------|-------------|
| W37-1 | ⚠️ LOW | layer-11 L168 | File tree comment says "7 domain-specific factories" but detailed section (L556) and source code both show **8** factory functions. The file tree annotation should be corrected to "8". |

### Conclusion

Wave 36R 的 10 處修正全部驗證通過。兩份文件（layer-10-domain.md 和 layer-11-infrastructure.md）與源碼高度一致。唯一發現的問題是 Layer 11 文件樹註解中的 factory 數量（7 vs 8）存在微小不一致，但詳細描述章節的數字是正確的。

**驗證結果：49 ✅ / 1 ⚠️ / 0 ❌ — PASS**
