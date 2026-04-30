# Sprint 51.1 — 範疇 2 工具層（Level 3）

**Phase**: 51（Tools + Memory）
**Sprint 順序**：2 / 3（Phase 51 第 2 個 sprint）
**啟動日期**：2026-04-30（接 Sprint 51.0 closeout + main merge `8cd47ca`）
**預期完成**：2026-05-06（1 週 / 5 工作日）
**範疇歸屬**：範疇 2（Tool Layer）— 主要範疇；touches 範疇 12 (Observability) + §HITL（中央化）
**狀態**：🟡 PLANNING — 待用戶 approve

---

## Sprint Goal

> **一句話**：把 50.1 InMemoryToolRegistry / InMemoryToolExecutor stub 升級為 production-grade 範疇 2 工具層（ProductionToolRegistry / ToolExecutor / Sandbox / Permissions），加 ToolSpec first-class fields（hitl_policy / risk_level），交付 4 內建通用工具（search/exec/hitl/memory placeholder），讓範疇 2 達 Level 3。

**為什麼此 sprint 必要**（per `06-phase-roadmap.md` §Sprint 51.1）：
- 50.1 用 InMemoryToolRegistry 當 stub（DEPRECATED-IN: 51.1）— 沒 permission check、無 sandbox 隔離、執行純 sequential
- 50.1 / 51.0 既存 19 tool（echo + 18 business）需 graceful migration 到 production registry
- 51.0 retro 標記 CARRY-021：ToolSpec 缺 first-class hitl_policy + risk_level field（51.0 暫編到 tags）
- 範疇 2 達 Level 3 後，51.2 範疇 3 (Memory) 可直接接 production registry，52+ context/prompt sprint 可信賴 sandbox + permission

---

## User Stories

### US-1：作為主流量驅動者
**我希望** chat handler 預設 19 工具仍可呼叫，但執行時走 production registry（含 permission + sandbox）
**以便** Phase 53.x guardrails / Phase 54 verification 接入時有真實隔離保障

**驗收**：283 PASS baseline 完整保留；e2e mock_patrol 透過 production registry 跑通

### US-2：作為範疇 2 spec 維護者
**我希望** ToolSpec 加 first-class `hitl_policy: HITLPolicy` + `risk_level: Literal["low","medium","high"]` field（CARRY-021）
**以便** 51.0 業務 stub 18 個從 tags-encoded 升級為 typed fields，type safety 不再依賴字串 parse

**驗收**：18 業務 stub `tags=("hitl_policy:always_ask",...)` 改為 `hitl_policy=HITLPolicy.ALWAYS_ASK + risk_level="high"`；mypy strict pass；17.md §1.1 + §3.1 同步更新

### US-3：作為 Phase 53.3 guardrails 設計者
**我希望** 工具執行前自動檢查 permission（tenant_id / RBAC role / hitl_policy / risk_level）
**以便** HITL ALWAYS_ASK / ASK_ONCE 觸發 ApprovalRequest 由 production executor 統一處理（非每個 caller 自實作）

**驗收**：`PermissionChecker.allow(call, context) -> Allow|RequireApproval|Deny` ABC 在位；executor 集成 check；test case 覆蓋 3 種結果

### US-4：作為 Cat 2 Sandbox 強制執行者
**我希望** `python_sandbox` 工具在隔離環境執行（subprocess + 資源限制 + 無檔案寫入）
**以便** AI agent 跑 LLM 生成的 python code 時不會污染主機 file system / network / process tree

**驗收**：`SandboxBackend` ABC + `SubprocessSandbox` impl；test 嘗試 write `/tmp/escape.txt` 被擋；CPU/wall time limit 5s enforced

### US-5：作為 V2 紀律守護者
**我希望** Sprint 51.1 closeout 時 InMemoryToolRegistry / InMemoryToolExecutor 完全移除（CARRY-017）
**以便** stub layer 不被新代碼意外引用；51.x 後續 sprint 無 ambiguity

**驗收**：`grep -r "InMemoryToolRegistry\|InMemoryToolExecutor\|make_echo_executor" backend/src/` = 0 hits；`agent_harness/tools/_inmemory.py` 整檔刪除

---

## Technical Specifications

### 架構決策

#### 決策 1：ToolSpec 加 first-class hitl_policy + risk_level（CARRY-021）

**選擇**：擴 `_contracts/tools.py:ToolSpec` 加兩個 typed field，default 值保 backward-compat
**Alternative considered**：
- ❌ 維持 tags-encoded — 字串 parse 易出錯，無 type safety
- ❌ 拆 ToolSpecExtended subclass — 增加 dataclass 繼承複雜度
- ✅ 直接加 field，default = `HITLPolicy.AUTO` + `risk_level="low"`

```python
@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    annotations: ToolAnnotations = field(default_factory=ToolAnnotations)
    concurrency_policy: ConcurrencyPolicy = ConcurrencyPolicy.SEQUENTIAL
    hitl_policy: HITLPolicy = HITLPolicy.AUTO          # ← 新增
    risk_level: Literal["low", "medium", "high"] = "low"  # ← 新增
    version: str = "1.0"
    tags: tuple[str, ...] = ()
```

**Migration**：18 業務 stub 移除 tags 中的 `hitl_policy:*` / `risk:*`，改用 first-class field。
**17.md sync**：§1.1 ToolSpec dataclass 表 + §3.1 工具註冊表 同 commit 更新。

#### 決策 2：ProductionToolRegistry vs InMemoryToolRegistry（CARRY-017）

**選擇**：新增 `agent_harness/tools/registry.py:ToolRegistry`（concrete impl，非 ABC）
**Alternative considered**：
- ❌ 改 InMemoryToolRegistry 為 production — 違反 DEPRECATED-IN: 51.1 紀律（leading underscore filename 表 deprecation marker）
- ❌ 命名 `ProductionToolRegistry`（distinguishes from old）— 不必要冗詞
- ✅ 直接命名 `ToolRegistry`（concrete class），_inmemory.py 整檔刪除

**ABC 與 concrete**：
- `agent_harness/tools/_abc.py` 已有 `ToolRegistry` ABC（49.1）
- 51.1 加 `agent_harness/tools/registry.py:ToolRegistryImpl(ToolRegistry)` concrete
- export `ToolRegistry`（ABC）+ `ToolRegistryImpl`（impl）via `tools/__init__.py`

#### 決策 3：Sandbox subprocess vs Docker

**選擇**：51.1 採 subprocess + resource limits（quick start）；Docker container backend 留 51.x 後續或 Phase 53.x（Sandbox enforcement）
**Alternative considered**：
- ❌ Docker first — 增加 dev dependency，CI 配置複雜
- ✅ subprocess + `resource.setrlimit` (Linux/macOS) / Job Object (Windows) — 獨立，CI-friendly

```python
class SandboxBackend(ABC):
    @abstractmethod
    async def execute(
        self,
        code: str,
        *,
        timeout_seconds: float,
        memory_mb: int,
        network_blocked: bool = True,
    ) -> SandboxResult: ...

class SubprocessSandbox(SandboxBackend): ...  # 51.1
class DockerSandbox(SandboxBackend): ...       # 51.x or Phase 53.x
```

#### 決策 4：Permission check 範圍

**選擇**：51.1 permission check 涵蓋 3 維度：
1. **HITL policy**：`hitl_policy=ALWAYS_ASK / ASK_ONCE` 觸發 ApprovalRequest
2. **Risk level**：`risk_level="high"` 額外要求 approval（regardless of hitl_policy）
3. **Tool annotations**：`destructive=True` + 無 explicit approval → block

Tenant-aware permission（multi-tenant role check）留 51.x 或 Phase 53.x（governance sprint）。

```python
class PermissionDecision(Enum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"

class PermissionChecker:
    def check(
        self,
        spec: ToolSpec,
        call: ToolCall,
        context: ExecutionContext,
    ) -> PermissionDecision: ...
```

#### 決策 5：JSONSchema validation 位置

**選擇**：在 `ToolExecutor.execute()` 內 pre-execution validate；fail 時回傳 `ToolResult(success=False, error="schema mismatch: ...")`
**Alternative considered**：
- ❌ 在 ToolRegistry.register() 時 validate — 太早，ToolCall arguments 還沒到
- ✅ 在 execute() 進入點 validate — 統一錯誤處理路徑

使用 `jsonschema` library（已在 backend deps；49.1 baseline）。

#### 決策 6：4 內建工具完成度

**選擇**：51.1 交付 3 個 functional 內建工具 + 1 個 placeholder：
- ✅ `search_tools.web_search` — Azure Bing Search API（fallback：Google CSE 或 DuckDuckGo）
- ✅ `exec_tools.python_sandbox` — SubprocessSandbox 執行
- ✅ `hitl_tools.request_approval` — 觸發 PermissionDecision.REQUIRE_APPROVAL
- ⏸ `memory_tools.memory_search/memory_write` — placeholder spec only（51.2 接 Cat 3 真實實作）

### Single-source 同步

| 項目 | 位置 | Owner |
|-----|------|-------|
| ToolSpec 加 hitl_policy / risk_level | `_contracts/tools.py` + 17.md §1.1 | 範疇 2 |
| HITLPolicy enum | `_contracts/hitl.py:80`（已存在）| §HITL central |
| ToolRegistryImpl | `agent_harness/tools/registry.py`（新）| 範疇 2 |
| ToolExecutorImpl | `agent_harness/tools/executor.py`（新）| 範疇 2 |
| PermissionChecker | `agent_harness/tools/permissions.py`（新）| 範疇 2 |
| SandboxBackend ABC + Subprocess impl | `agent_harness/tools/sandbox.py`（新）| 範疇 2 |
| 4 內建工具 | `agent_harness/tools/{search,exec,hitl,memory}_tools.py`（新）| 範疇 2 |
| 17.md §3.1 工具註冊表 | 加 4 內建工具 entries（refining 51.0 entries） | Contract owner |

### 範疇歸屬規則

```
agent_harness/tools/
├── __init__.py                ← public exports
├── _abc.py                    ← ABC (49.1，不動)
├── _inmemory.py               ← DELETE（51.1 CARRY-017 deprecation）
├── registry.py                ← 新 ToolRegistryImpl (51.1)
├── executor.py                ← 新 ToolExecutorImpl (51.1)
├── permissions.py             ← 新 PermissionChecker (51.1)
├── sandbox.py                 ← 新 SandboxBackend ABC + SubprocessSandbox (51.1)
├── search_tools.py            ← 新 web_search (51.1)
├── exec_tools.py              ← 新 python_sandbox (51.1)
├── hitl_tools.py              ← 新 request_approval (51.1)
└── memory_tools.py            ← 新 placeholder (51.1; 51.2 fill)
```

**禁止**：
- ❌ business_domain 直接 import openai / anthropic（持續 51.0 規則）
- ❌ Sandbox impl 在 agent_harness 之外（必須在範疇 2）
- ❌ Permission check 在 chat handler / API layer（必須在 executor 內統一）

---

## File Change List（共 ~25 檔）

### 新建（13 檔）

#### 範疇 2 production stack（5 檔）
- `agent_harness/tools/registry.py` — ToolRegistryImpl（concrete）
- `agent_harness/tools/executor.py` — ToolExecutorImpl（concurrency policy + permission + JSONSchema）
- `agent_harness/tools/permissions.py` — PermissionChecker + PermissionDecision enum
- `agent_harness/tools/sandbox.py` — SandboxBackend ABC + SubprocessSandbox impl
- `agent_harness/tools/_factory.py` — `make_default_executor()` 移到此（替代 _register_all 內舊 factory）

#### 4 內建工具（4 檔）
- `agent_harness/tools/search_tools.py` — web_search ToolSpec + handler（Bing API）
- `agent_harness/tools/exec_tools.py` — python_sandbox ToolSpec + handler
- `agent_harness/tools/hitl_tools.py` — request_approval ToolSpec + handler
- `agent_harness/tools/memory_tools.py` — placeholder ToolSpec for memory_search / memory_write

#### Tests（4 檔）
- `tests/unit/tools/test_registry.py` — ToolRegistryImpl CRUD + duplicate detection
- `tests/unit/tools/test_executor.py` — JSONSchema validate / concurrency / permission gate
- `tests/unit/tools/test_sandbox.py` — Subprocess sandbox isolation + resource limits
- `tests/integration/tools/test_builtin_tools.py` — 4 built-in tools execute via registry

### 修改（10 檔）

- `agent_harness/_contracts/tools.py` — ToolSpec 加 hitl_policy + risk_level field
- `agent_harness/tools/__init__.py` — export ToolRegistryImpl / ToolExecutorImpl / PermissionChecker / SandboxBackend / SubprocessSandbox / 4 built-in tools
- `business_domain/{patrol,correlation,rootcause,audit_domain,incident}/tools.py` — 5 file 從 tags-encoded 改 first-class field（hitl_policy + risk_level）
- `business_domain/_register_all.py` — `make_default_executor()` 用新 ToolRegistryImpl + ToolExecutorImpl
- `api/v1/chat/handler.py` — 不動（透過 make_default_executor 自動切換）
- `docs/03-implementation/agent-harness-planning/17-cross-category-interfaces.md` — §1.1 ToolSpec dataclass 加 2 field；§3.1 4 built-in tools entries

### 刪除（1 檔）

- `agent_harness/tools/_inmemory.py` — 整檔刪除（CARRY-017 deprecation）
- 同時刪除：`from agent_harness.tools._inmemory import ...` 的所有 import 站點

---

## Acceptance Criteria

### 必過（DoD）

1. ✅ ToolSpec 加 hitl_policy + risk_level field；mypy strict pass
2. ✅ 18 業務 stub + echo_tool + 4 內建工具 = 23 ToolSpec 全用 first-class field（無 tags-encoded hitl_policy / risk）
3. ✅ ToolRegistryImpl + ToolExecutorImpl + PermissionChecker + SandboxBackend 全 implement 並 export
4. ✅ JSONSchema validation：bad input → ToolResult.success=False + error message（test 覆蓋）
5. ✅ Permission check 3 維度：HITL policy / risk level / annotations.destructive；3 種 Decision 各 ≥ 1 test
6. ✅ Sandbox：python_sandbox try `open("/tmp/escape.txt", "w")` → ProcessLookupError or PermissionError；CPU/wall 5s timeout 觸發
7. ✅ `grep -r "InMemoryToolRegistry\|InMemoryToolExecutor\|make_echo_executor" backend/src/` = 0 hits
8. ✅ `_inmemory.py` 整檔已刪
9. ✅ 既存 283 PASS baseline 完整保留 + 51.1 新增 ~25 tests = ~308 PASS / 0 SKIPPED
10. ✅ mypy strict / black / 5 V2 lints / LLM SDK leak 全 OK
11. ✅ 17.md §1.1 + §3.1 同步更新（同 commit）

### 建議過（不阻擋）

12. 🟡 Docker sandbox backend（留 51.x 或 Phase 53.x）
13. 🟡 Tenant-aware permission check（留 Phase 53.3 governance sprint）
14. 🟡 web_search 真實 API key 整合 demo（CARRY 用戶手動）

---

## Dependencies & Risks

### 依賴

- ✅ 50.1 ToolSpec / ToolAnnotations / ConcurrencyPolicy（在 `_contracts/tools.py`）
- ✅ 49.1 ToolRegistry / ToolExecutor ABC（在 `_abc.py`）
- ✅ 50.2 LoopEvent integration（ToolCallExecuted / ToolCallFailed）
- ✅ 51.0 18 業務 ToolSpec stubs + register_all_business_tools
- ⏸ Cat 3 Memory（51.2）— 51.1 memory_tools 只 placeholder
- ⏸ HITL real ApprovalManager（Phase 53.3）— 51.1 PermissionChecker 回 RequireApproval enum，不 invoke ApprovalManager

### 風險

| ID | 風險 | 機率 | 影響 | 緩解 |
|----|-----|-----|-----|------|
| R-1 | ToolSpec 加 field 破 50.x / 51.0 既有測試 | 中 | 高 | default 值（AUTO + low）保 backward-compat；Day 1 跑全 test 確認無 regression |
| R-2 | SubprocessSandbox 跨平台行為差（Linux setrlimit vs Windows Job Object）| 中 | 中 | Day 3 拆 Linux/macOS path（POSIX）+ Windows path；CI matrix Linux only（Windows mark `xfail` or skip） |
| R-3 | InMemoryToolRegistry 移除遺漏 import 站點 | 低 | 高 | Day 5 用 grep + AST scan 確認；backstop test：`test_no_legacy_imports` |
| R-4 | web_search 需真實 Bing/Google API key — CI 不能跑 | 高 | 低 | 51.1 web_search test 用 mock httpx response；real key smoke 留 user CARRY |
| R-5 | 18 業務 stub migration 順序 — 改 tools.py 後 register_all 短暫破 | 中 | 中 | Day 5 先改 ToolSpec contract + default 後保 51.0 tag-encoded path；逐 domain migrate test 後再清 tags |
| R-6 | JSONSchema lib `jsonschema` 慢（heavy） | 低 | 低 | 用 `jsonschema.Draft202012Validator` cached per spec；不 per-call 建 |

---

## Deliverables（Sprint Goal Mapping）

- [ ] **D-1**: ToolSpec 擴 hitl_policy + risk_level（CARRY-021）+ 17.md sync（US-2）
- [ ] **D-2**: ToolRegistryImpl + ToolExecutorImpl（concurrency policy enforcement）（US-1, US-3）
- [ ] **D-3**: PermissionChecker + PermissionDecision enum + executor 集成（US-3）
- [ ] **D-4**: SandboxBackend ABC + SubprocessSandbox（US-4）
- [ ] **D-5**: 4 內建工具（search/exec/hitl + memory placeholder）（US-1）
- [ ] **D-6**: 18 業務 stub migration（tags → first-class field）（US-2）
- [ ] **D-7**: `_inmemory.py` 整檔刪除（CARRY-017）（US-5）
- [ ] **D-8**: ~25 new tests（unit + integration）/ 累計 ~308 PASS（US-1）
- [ ] **D-9**: progress.md / retrospective.md / Phase 51 README 更新 / sprint-51-1-checklist 全 [x]（V2 紀律）

---

## 估時

| Day | 主題 | 預估 | 累計 |
|-----|------|-----|-----|
| 0 | Plan + Checklist + branch + Phase README sync | 4h | 4h |
| 1 | ToolSpec extension（CARRY-021）+ ToolRegistryImpl + 17.md sync | 5h | 9h |
| 2 | ToolExecutorImpl（concurrency + JSONSchema）+ PermissionChecker | 6h | 15h |
| 3 | SandboxBackend + SubprocessSandbox + exec_tools | 5h | 20h |
| 4 | search_tools + hitl_tools + memory_tools placeholder + 4 built-in tests | 6h | 26h |
| 5 | 18 業務 stub migration + _inmemory.py 整檔刪 + retro + closeout | 5h | 31h |

**Plan total**：~31h
**Actual estimate**（per V2 7-sprint 平均 20% 估時準度）：~6-8h（sandbox 跨平台 + 18 stub migration 較複雜，預期略高於 51.0 23%）

---

## V2 紀律對照（9 項）

| # | 紀律 | 對應檢查 |
|---|------|---------|
| 1 | Server-Side First | sandbox 在 backend；executor / permission 全 server-side |
| 2 | LLM Provider Neutrality | search_tools 透過 ChatClient (or HTTPx) 不 import OpenAI SDK |
| 3 | CC Reference 不照搬 | 51.1 自設計 PermissionChecker / SandboxBackend |
| 4 | 17.md Single-source | §1.1 ToolSpec field 加 / §3.1 4 built-in tools entries 同 commit |
| 5 | 11+1 範疇歸屬 | sandbox.py / permissions.py 全在 `agent_harness/tools/`（範疇 2）|
| 6 | 04 Anti-patterns | AP-3 安全（4 內建工具獨立檔）/ AP-4 Sandbox 真實隔離（非 stub）/ AP-9 permission 無 verification skip |
| 7 | Sprint workflow | Day 0 plan/checklist；Day 1-5 嚴格 plan→checklist→code→update→commit |
| 8 | File header convention | 13 新檔每檔有 V2 file header |
| 9 | Multi-tenant rule | 51.1 permission check 不 tenant-aware（簡化）；Phase 53.3 加 tenant_id check |

---

## Out of Scope（明確不做）

- ❌ Docker sandbox backend（51.x 或 Phase 53.x）
- ❌ Tenant-aware permission RBAC（Phase 53.3）
- ❌ 真實 ApprovalManager 整合（Phase 53.3）— 51.1 只回 PermissionDecision enum
- ❌ Memory tools 真實實作（51.2）— 51.1 placeholder ToolSpec only
- ❌ Streaming partial-token（CARRY-015，52.1）
- ❌ Real Azure Bing API smoke（用戶手動 CARRY）
- ❌ Tool result image / file attachment 處理（Phase 53.x）
- ❌ Tenant 限制 chat handler default tools（per request 過濾）— Phase 53.3
- ❌ Container resource quota（CPU pinning / network namespaces）— Phase 53.x

---

## Carry-forward 候選（從 50.2 + 51.0）

51.1 接收：
- **CARRY-017** InMemoryToolRegistry deprecation — **本 sprint 處理**
- **CARRY-021** ToolSpec first-class hitl_policy + risk_level — **本 sprint 處理**

51.1 暫不接：
- CARRY-019 frontend chat-v2 ToolCallCard manual smoke — 用戶 trigger
- CARRY-020 roadmap 24 vs spec 18（51.0 採 18 簡潔，無變動）
- CARRY-010 vitest install — 51.x Day 0 接
- CARRY-011 Tailwind retrofit — 53.4
- CARRY-012 dev e2e manual smoke — 用戶 trigger
- CARRY-013 npm audit — 51.x
- CARRY-014 DB-backed sessions — 51.x
- CARRY-015 streaming — 52.1
- CARRY-016 Real Azure run — 用戶
- CARRY-018 AST AP-1 lint — 51.x backlog

51.1 新增 CARRY 候選：
- **CARRY-022**：Docker sandbox backend（Phase 53.x）
- **CARRY-023**：Tenant-aware permission RBAC（Phase 53.3）
- **CARRY-024**：web_search 真實 API key 整合 manual smoke（用戶 trigger）

---

## Approval

- [ ] User review plan
- [ ] User review checklist
- [ ] User approve → AI 助手執行 Day 0（建 branch + commit plan/checklist）

---

**File**: `docs/03-implementation/agent-harness-planning/phase-51-tools-memory/sprint-51-1-plan.md`
**Created**: 2026-04-30
**Maintainer**：用戶 + AI 助手
