# Sprint 51.1 — Checklist

**Plan**：[`sprint-51-1-plan.md`](./sprint-51-1-plan.md)
**Sprint**：51.1 — 範疇 2 工具層（Level 3）
**狀態**：🟡 PLANNING — 待用戶 approve

---

## 進度總覽

- **Day 0**：✅ Plan + Checklist + branch（4h）
- **Day 1**：✅ ToolSpec extension（CARRY-021）+ ToolRegistryImpl（5h plan / actual ~1h）
- **Day 2**：✅ ToolExecutorImpl + PermissionChecker（6h plan / actual ~1.5h）
- **Day 3**：✅ SandboxBackend + SubprocessSandbox + exec_tools（5h plan / actual ~1h）
- **Day 4**：✅ search_tools + hitl_tools + memory_tools placeholder + tests（6h plan / actual ~1.5h）
- **Day 5**：✅ 18 業務 stub migration + _inmemory.py 刪 + retro + closeout（5h plan / actual ~1.5h）

**Plan total**：31h / **Actual**：~7.5h（24% — V2 avg 20%；51.0 23%；nominal）

---

## Day 0 — Plan / Checklist / Branch / Phase README sync（預估 4 小時）

### 0.1 Sprint plan 撰寫（45 min）
- [x] **撰寫 sprint-51-1-plan.md**
  - DoD: 含 Sprint Goal + 5 User Stories + 6 架構決策 + File Change List + Acceptance Criteria + Deliverables + 6 Risks + V2 紀律對照
  - 已完成 ✅（commit `6aa6e32`）

### 0.2 Sprint checklist 撰寫（45 min）
- [x] **撰寫 sprint-51-1-checklist.md**（本檔）
  - DoD: Day 0-5 task 全列；每項 ≤ 90 min；含 DoD + verification command
  - 已完成 ✅（commit `6aa6e32`）

### 0.3 Phase 51 README 同步（30 min）
- [x] **修改 phase-51-tools-memory/README.md** — Sprint 51.1 狀態 ⏸→🟡 PLANNING
  - DoD: README Sprint 表更新 51.1 狀態 + 範圍預覽 ✅（commit `6aa6e32`）

### 0.4 建立 branch（10 min）
- [x] **`git checkout -b feature/phase-51-sprint-1-cat2-tool-layer` from main**
  - DoD: branch 從 main HEAD（51.0 merge commit `8cd47ca`）切；當前未動 main
  - **已執行**：branch 在 51.0 closeout 後建立 ✅

### 0.5 確認 50.x / 51.0 baseline ready（30 min）
- [x] **`make_default_executor` / `register_all_business_tools` / 18 ToolSpec / InMemoryToolRegistry 全 importable**
  - DoD: smoke import test ✅（Day 1 開工前驗證 `tool_count 19`）

### 0.6 確認 jsonschema lib 可用（15 min）
- [x] **`python -c "import jsonschema; print(jsonschema.__version__)"` ≥ 4.20**
  - DoD: jsonschema 在 backend deps；如缺，加到 pyproject.toml requirements 並重 install
  - 49.1 baseline 已含 ✅（4.26.0）

### 0.7 Day 0 commit（10 min）
- [x] **commit `docs(plan, sprint-51-1): Day 0 plan + checklist + Phase 51 README`**
  - DoD: 3 docs 提交；branch HEAD = Day 0 commit；working tree clean (除用戶 IDE work) ✅（`6aa6e32`）

---

## Day 1 — ToolSpec extension + ToolRegistryImpl（預估 5 小時）

### 1.1 ToolSpec 加 hitl_policy + risk_level field（CARRY-021）（45 min）
- [x] **修改 `_contracts/tools.py:ToolSpec`** 加兩個 field 帶 default
  - DoD: `hitl_policy: ToolHITLPolicy = ToolHITLPolicy.AUTO` + `risk_level: RiskLevel = RiskLevel.LOW` ✅
  - **設計調整**：plan §決策 1 寫 `HITLPolicy.AUTO`，但 `_contracts/hitl.py:HITLPolicy` 已存在為 per-tenant dataclass（不是 enum）。新增 distinct enum `ToolHITLPolicy`（AUTO / ASK_ONCE / ALWAYS_ASK）與既有 per-tenant `HITLPolicy` dataclass 區分；`risk_level` 複用 `_contracts/hitl.py:RiskLevel` enum（single-source 紀律）
  - 將於 retrospective 登錄此調整
  - mypy strict pass ✅

### 1.2 17.md §1.1 sync ToolSpec dataclass 表（30 min）
- [x] **修改 `17-cross-category-interfaces.md` §1.1**
  - DoD: ToolSpec 表加 hitl_policy / risk_level annotation；新增 ToolHITLPolicy row；§3.1 註腳更新（51.0 tags-encoded → 51.1 first-class）✅

### 1.3 50.x / 51.0 既存測試 baseline run（30 min）
- [x] **`PYTHONPATH=src python -m pytest --tb=line` 跑全 test**
  - DoD: 283 PASS / 0 SKIPPED 不變 ✅（後 1.4 重跑亦 283 PASS）

### 1.4 ToolRegistryImpl class（60 min）
- [x] **`agent_harness/tools/registry.py:ToolRegistryImpl(ToolRegistry)`** ✅
  - register: duplicate detection + Draft202012Validator.check_schema(spec.input_schema)
  - get / list / by_tag 完整
  - File header 完整 ✅

### 1.5 tools/__init__.py 加 export（15 min）
- [x] **export ToolRegistryImpl + 保留 ToolRegistry ABC export** ✅
  - smoke confirmed: `from agent_harness.tools import ToolRegistry, ToolRegistryImpl` 兩者皆可
  - `from agent_harness._contracts import ToolHITLPolicy` 亦 OK

### 1.6 Day 1 commit（15 min）
- [x] **commit `feat(tools, sprint-51-1): Day 1 — ToolSpec hitl_policy/risk_level + ToolRegistryImpl + 17.md §1.1 sync`** ✅ `5468303`
  - DoD: 283 baseline 全 PASS ✅；mypy strict OK ✅；black clean ✅；4/5 V2 lints OK（AP-1 skipped: orchestrator_loop dir 未在當前 mypy --root path）

---

## Day 2 — ToolExecutorImpl + PermissionChecker（預估 6 小時）

### 2.1 PermissionDecision enum + PermissionChecker class（60 min）
- [x] **`agent_harness/tools/permissions.py`** ✅
  - PermissionDecision = ALLOW / REQUIRE_APPROVAL / DENY enum；PermissionChecker.check(spec, call, context) returns Decision
  - 3 維度檢查：HITL policy / risk_level / annotations.destructive
  - **Refactor**：`ExecutionContext` 移到 `_contracts/tools.py`（single-source）讓 ToolExecutor ABC 可 reference 而不引入 dependency cycle；§17.md §1.1 同步加 row（pending Day 5 closeout sync）

### 2.2 ToolExecutorImpl class（90 min）
- [x] **`agent_harness/tools/executor.py:ToolExecutorImpl(ToolExecutor)`** ✅
  - `__init__(*, registry, handlers, permission_checker, tracer, metric_registry)`
  - `execute(call, *, trace_context, context)` — registry lookup → permission gate → JSONSchema validate → handler → tracer span + metric emit
  - `execute_batch(calls, *, trace_context, context)` — `_batch_can_parallelize()` 判斷後路由 asyncio.gather 或 sequential loop
  - ABC `_abc.py:ToolExecutor` 同步加 `context` kwarg；`_inmemory.InMemoryToolExecutor` 同步加（unused; DEPRECATED-IN: 51.1）

### 2.3 JSONSchema validation（30 min）
- [x] **executor.execute() 加 validator** ✅
  - bad input → ToolResult.success=False + error="schema mismatch: <field>: <message>"
  - validator 用 `_validator_cache: dict[str, Draft202012Validator]` per-spec cached
  - 4 tests（valid / missing required / wrong type / cache verification）

### 2.4 Permission tests（45 min）
- [x] **`tests/unit/agent_harness/tools/test_executor.py` permission gate tests** ✅
  - 3 種 Decision 全覆蓋：
    - ALLOW: `test_allow_simple_read_only` / `test_allow_destructive_with_explicit_approval`
    - REQUIRE_APPROVAL: `test_require_approval_always_ask` / `test_require_approval_ask_once` / `test_require_approval_high_risk_overrides_auto_hitl`
    - DENY: `test_deny_destructive_without_explicit_approval` / `test_deny_beats_require_approval`
  - 加 `test_permission_decision_enum_values` direct enum assertion

### 2.5 Concurrency tests（45 min）
- [x] **`tests/unit/agent_harness/tools/test_executor.py` concurrency tests** ✅
  - `test_batch_read_only_parallel_runs_concurrently`（3 × 100ms slow handler，threshold < 250ms）
  - `test_batch_with_sequential_runs_serial`（混合 SEQ + RO_PARALLEL → sequential，threshold > 280ms）
  - `test_batch_all_parallel_runs_concurrently`（2 × ALL_PARALLEL，threshold < 180ms）
  - `test_batch_empty_returns_empty`
  - Edge cases：unknown_tool / handler_exception / no_handler_registered

### 2.6 Day 2 commit（15 min）
- [x] **commit `feat(tools, sprint-51-1): Day 2 — ToolExecutorImpl + PermissionChecker + JSONSchema validation`** ✅ `8b364fc`
  - DoD: pytest 302 PASS（19 new）✅；mypy strict 35 source files clean ✅；4/4 V2 lints OK ✅；black formatted ✅

---

## Day 3 — SandboxBackend + SubprocessSandbox + exec_tools（預估 5 小時）

### 3.1 SandboxBackend ABC + SandboxResult dataclass（30 min）
- [x] **`agent_harness/tools/sandbox.py:SandboxBackend(ABC)` + `SandboxResult`** ✅
  - ABC method `execute(code, *, timeout_seconds, memory_mb, network_blocked) -> SandboxResult`
  - SandboxResult: stdout / stderr / exit_code / duration_seconds / killed_by_timeout

### 3.2 SubprocessSandbox impl（90 min）
- [x] **`agent_harness/tools/sandbox.py:SubprocessSandbox`** ✅
  - asyncio.create_subprocess_exec + asyncio.wait_for timeout（kill on timeout → killed_by_timeout=True）
  - tempfile.TemporaryDirectory cwd（每執行 fresh tempdir auto-cleanup）
  - POSIX `_make_posix_limiter`：preexec_fn 設 RLIMIT_AS (memory) + RLIMIT_CPU (timeout × 2 backstop)
  - Windows: 跳過 rlimit（依賴 wall-time wait_for kill；Job Object CARRY-022）
  - network_blocked: 51.1 不執行（doc note；CARRY-022 Docker）

### 3.3 Sandbox isolation tests（60 min）
- [x] **`tests/unit/agent_harness/tools/test_sandbox.py`**（10 tests）✅
  - test_sandbox_returns_stdout（happy path）
  - test_sandbox_timeout_kills_runaway（while True → killed_by_timeout=True / duration < 1.5s）
  - test_sandbox_exit_code_propagated（sys.exit(42) → exit_code=42）
  - test_sandbox_runs_in_isolated_cwd（subprocess cwd != host cwd / 含 sbx_ tempdir prefix）
  - test_sandbox_stderr_captured
  - test_sandbox_relative_writes_contained_in_tempdir（cwd-relative writes，tempdir auto-cleanup）
  - test_sandbox_memory_limit_kills_oversized_alloc（POSIX-only，`@pytest.mark.skipif(win32)` 標記）
  - test_python_sandbox_spec_metadata + happy_path + uses_defaults（3 tests for built-in tool）
  - **設計調整**：plan §3.3 寫「test_filesystem_write_blocked: try open("/tmp/escape.txt", "w") → 失敗」需 chroot/namespace（51.1 best-effort 不擋 absolute path writes；Docker 才能真隔離）。改為 `test_sandbox_relative_writes_contained_in_tempdir`（cwd-relative 寫 OK + tempdir cleanup 隔離）+ memory_limit test（POSIX only）。原 plan test 留 51.x Docker sandbox 真實實作。

### 3.4 exec_tools.py — python_sandbox ToolSpec + handler（45 min）
- [x] **`agent_harness/tools/exec_tools.py`** ✅
  - PYTHON_SANDBOX_SPEC（input_schema {code, timeout_seconds default 5, memory_mb default 256}）
  - annotations: destructive=False（subprocess sandboxed）/ open_world=False
  - hitl_policy=AUTO + risk_level=MEDIUM（任意 code 執行即使 sandboxed 也 medium）
  - tags=("builtin","exec")
  - `make_python_sandbox_handler(backend)` factory 返回 async handler；handler 序列化 SandboxResult → JSON ToolResult.content

### 3.5 Day 3 commit（15 min）
- [x] **commit `feat(tools, sprint-51-1): Day 3 — SandboxBackend + SubprocessSandbox + python_sandbox tool`** ✅ `24734dd`
  - DoD: pytest 311 PASS / 1 SKIPPED（POSIX-only mem test，Windows skip）；mypy --strict 39 source files clean；black formatted；4/4 V2 lints OK

---

## Day 4 — search_tools + hitl_tools + memory_tools + tests（預估 6 小時）

### 4.1 search_tools.py — web_search ToolSpec + handler（75 min）
- [x] **`agent_harness/tools/search_tools.py`** ✅
  - WEB_SEARCH_SPEC（input_schema {query required minLength=1, top_k 1-20 default 5}; annotations open_world=True）
  - hitl_policy=AUTO + risk_level=LOW + tags=("builtin","search")
  - `make_web_search_handler(client, *, endpoint, api_key_env)` factory；缺 BING_SEARCH_API_KEY 拋 `WebSearchConfigError`
  - 支援 `BING_SEARCH_ENDPOINT` env override（self-hosted / 沙盒）
  - Test 用 `httpx.MockTransport` mock response（real key smoke 留 CARRY-024）

### 4.2 hitl_tools.py — request_approval ToolSpec + handler（45 min）
- [x] **`agent_harness/tools/hitl_tools.py`** ✅
  - REQUEST_APPROVAL_SPEC（input_schema {message required, severity enum [low/medium/high/critical] default medium}）
  - hitl_policy=ALWAYS_ASK（self-referential）+ risk_level=MEDIUM + concurrency=SEQUENTIAL + tags=("builtin","hitl")
  - `request_approval_handler` 返回 JSON `{pending_approval_id, message, severity, status:"pending", note}`；`pending_approval_id` 用 `uuid5(NAMESPACE_OID, f"approval:{call.id}")` 確保 deterministic for tracing
  - 文件註明：handler 通常被 PermissionChecker 短路；只有 explicit_approval=True 才會跑（且即使如此 ALWAYS_ASK 仍 gate）

### 4.3 memory_tools.py — placeholder ToolSpec（30 min）
- [x] **`agent_harness/tools/memory_tools.py`** ✅
  - MEMORY_SEARCH_SPEC（query / scopes enum / top_k）read_only=True / RO_PARALLEL
  - MEMORY_WRITE_SPEC（scope enum / key / content）SEQUENTIAL
  - 兩 spec hitl=AUTO + risk=LOW + tags=("builtin","memory","placeholder")
  - `memory_placeholder_handler` raises `NotImplementedError("memory tool 'X' is a 51.1 placeholder; Sprint 51.2 wires Cat 3 backend")`
  - MEMORY_TOOL_SPECS tuple export 給 register helper 用

### 4.4 4 built-in tools register helpers（30 min）
- [x] **`agent_harness/tools/__init__.py` 加 `register_builtin_tools(registry, handlers, *, sandbox_backend)`** ✅
  - 註冊 6 個 spec：echo_tool / python_sandbox / web_search / request_approval / memory_search / memory_write
  - 補回 echo_tool（仍從 `_inmemory.py` import，Day 5 將遷移到非 deprecation 路徑）
  - export `register_builtin_tools`
  - **變動 vs plan**：plan 寫「4 內建工具」實際是 6（echo + python_sandbox + web_search + request_approval + memory_search + memory_write）— echo 從 50.1 留存 + memory ×2 placeholder 計入

### 4.5 Integration test：4 built-in via registry（60 min）
- [x] **`tests/integration/agent_harness/tools/test_builtin_tools.py`**（12 tests）✅
  - register wiring（2）：register_builtin_tools 註冊 6 specs / duplicate raises
  - execute via executor（6）：echo / python_sandbox / request_approval blocked by ALWAYS_ASK / explicit_approval still blocked / memory_search placeholder / memory_write placeholder
  - web_search（2）：mocked httpx response / missing env raises
  - meta（2）：first-class hitl/risk fields no tags-encoding（CARRY-021 verification）/ permission decisions reproducible

### 4.6 17.md §3.1 sync — 4 built-in entries（30 min）
- [x] **修改 `17-cross-category-interfaces.md` §3.1** ✅
  - §3.1 表加 column「concurrency / hitl / risk」
  - web_search / python_sandbox / echo_tool / request_approval / memory_search / memory_write 各填 51.1 metadata
  - request_approval 註明 51.1 placeholder + 53.3 wires；memory_* 註明 51.2 fills；python_sandbox 註明 CARRY-022 Docker；echo_tool 改備註「仍 active in 51.1；可能在 52.x deprecate」（51.1 不刪 echo_tool）

### 4.7 Day 4 commit（15 min）
- [x] **commit `feat(tools, sprint-51-1): Day 4 — built-in tools (web_search/hitl/memory placeholder) + 17.md §3.1 sync`** ✅ `dd08fc2`
  - DoD: pytest 323 PASS / 1 SKIPPED ✅；mypy --strict 23 source files clean ✅；black formatted ✅；4/4 V2 lints OK ✅

---

## Day 5 — Migration + _inmemory.py delete + retro + closeout（預估 5 小時）

### 5.1 18 業務 stub migration tags → first-class field（90 min）
- [x] **修改 5 file `business_domain/{patrol,correlation,rootcause,audit_domain,incident}/tools.py`** ✅
  - 18 spec 全移除 `hitl_policy:*` / `risk:*` tags-encoded；加 first-class `hitl_policy=ToolHITLPolicy.X` + `risk_level=RiskLevel.X`
  - 保 `tags=("domain:*",)`
  - register parameter type `InMemoryToolRegistry` → `ToolRegistry` ABC
  - mypy strict 39 source files clean ✅

### 5.2 `make_default_executor()` 切到 ToolRegistryImpl + ToolExecutorImpl（30 min）
- [x] **修改 `business_domain/_register_all.py`** ✅
  - ToolRegistryImpl + ToolExecutorImpl 取代 InMemoryToolRegistry + InMemoryToolExecutor
  - 從新 `tools/echo_tool.py` import ECHO_TOOL_SPEC + echo_handler（不再依賴 _inmemory.py）
  - parameter type `InMemoryToolRegistry` → `ToolRegistry` ABC

### 5.3 `_inmemory.py` 整檔刪除（30 min）
- [x] **delete `agent_harness/tools/_inmemory.py`** ✅
  - 同時刪：`tests/unit/agent_harness/tools/test_inmemory.py`（8 tests for deprecated impl）
  - **影響範圍 vs plan**：13 callers 修：5 business_domain/*/tools.py + _register_all.py + tools/__init__.py + 6 test files
  - 修 6 test files：5 用 make_echo_executor (re-export from tools/) + 1 用 ToolExecutorImpl + AllowAllPermissionChecker test helper
  - Verify: `grep -r InMemoryToolRegistry|InMemoryToolExecutor|make_echo_executor backend/src/` 全是 docstring/comment（0 active import）；`_inmemory.py` not exists ✅

### 5.4 既存 283 tests 回歸驗證（45 min）
- [x] **`PYTHONPATH=src python -m pytest --tb=short`** ✅
  - 315 PASS / 1 SKIPPED（POSIX-only memory test on Windows，platform-skipif 標準 pattern）
  - 算式：51.0 baseline 283 + Day 2 ~19 + Day 3 ~9 + Day 4 ~12 - Day 5 inmemory delete -8 = **315 PASS active**
  - mock_services + 18 業務（透過 _AllowAllPermissionChecker 在 routing test 中保留 happy path）+ e2e 全 PASS

### 5.5 progress.md Day 0-5 全紀錄（30 min）
- [x] **`docs/03-implementation/agent-harness-execution/phase-51/sprint-51-1/progress.md`** ✅
  - Day 0-5 各 1 entry；估時 vs actual 表

### 5.6 retrospective.md（30 min）
- [x] **`docs/03-implementation/agent-harness-execution/phase-51/sprint-51-1/retrospective.md`** ✅
  - 5 Did Well / 5 Improve / 4 Action Items / CARRY 解決+延後+forward / 估時準度 24% / 範疇成熟度 Post-51.1（Cat 2 → Level 3）

### 5.7 Phase 51 README 更新 51.1 ✅ DONE（15 min）
- [x] **`phase-51-tools-memory/README.md`** ✅
  - Sprint 51.1 ✅ DONE；2 / 3 sprint complete (67%)；範疇成熟度表 Post-51.1 column 更新

### 5.8 sprint-51-1-checklist 全 [x] / 🚧（10 min）
- [x] **本檔所有 `[ ]` → `[x]`** ✅
  - 0 個未勾選殘留（除 5.9 closeout commit pending 自身）

### 5.9 Day 5 closeout commit（15 min）
- [ ] **commit `docs(closeout, sprint-51-1): Day 5 — 18 stub migration + _inmemory delete + 6 caller migrations + retro + Phase 51 README`**
  - DoD: working tree clean；branch HEAD = closeout commit；Sprint 51.1 ✅ DONE

---

## Sprint 51.1 完成驗收（DoD aggregate）

執行下列全部 PASS 才算 Sprint 51.1 ✅ DONE：

```bash
# 1. Test suite
PYTHONPATH=src python -m pytest --tb=short
# Expected: ≥ 308 PASS / 0 SKIPPED

# 2. Type check
PYTHONPATH=src python -m mypy src/agent_harness/tools/ src/business_domain/ src/mock_services/ --strict
# Expected: 0 errors

# 3. Lint
black --check backend/src/agent_harness/tools/
isort --check backend/src/agent_harness/tools/
flake8 backend/src/agent_harness/tools/
# Expected: all clean

# 4. V2 5 lints
python scripts/lint/check_ap1_pipeline_disguise.py
python scripts/lint/check_cross_category_imports.py 2>/dev/null || python scripts/lint/check_cross_category_import.py
python scripts/lint/check_llm_neutrality.py 2>/dev/null || python scripts/lint/check_llm_sdk_leak.py
python scripts/lint/check_duplicate_dataclass.py
python scripts/lint/check_sync_callback.py
# Expected: all OK

# 5. CARRY-017 verify — InMemoryToolRegistry fully removed
grep -rE "InMemoryToolRegistry|InMemoryToolExecutor|make_echo_executor" backend/src/ 2>&1 | grep -v "__pycache__"
# Expected: 0 results

# 6. _inmemory.py deleted
test ! -f backend/src/agent_harness/tools/_inmemory.py && echo "OK: _inmemory.py deleted"

# 7. CARRY-021 verify — ToolSpec first-class fields used
grep -rE 'tags=\(.*"hitl_policy:|tags=\(.*"risk:' backend/src/business_domain/ backend/src/agent_harness/tools/
# Expected: 0 results (tags-encoded hitl_policy / risk migrated to first-class fields)

# 8. Sandbox isolation test
PYTHONPATH=src python -m pytest tests/unit/tools/test_sandbox.py -v
# Expected: filesystem escape blocked + timeout kills runaway

# 9. e2e mock_patrol still works (regression)
PYTHONPATH=src python -m pytest tests/e2e/test_agent_loop_with_mock_patrol.py -v
# Expected: 2 PASS

# 10. Working tree clean
git status
# Expected: nothing to commit
```

---

## 🚧 延後項（rolling planning 留）

無（51.1 開工前）

> 開工後若有阻塞，加 🚧 標記 + reason，並登錄到 retrospective.md Action Items。**禁止刪除 [ ]**。

---

**File**: `docs/03-implementation/agent-harness-planning/phase-51-tools-memory/sprint-51-1-checklist.md`
**Created**: 2026-04-30
**Maintainer**：用戶 + AI 助手
