# Sprint 51.1 — Checklist

**Plan**：[`sprint-51-1-plan.md`](./sprint-51-1-plan.md)
**Sprint**：51.1 — 範疇 2 工具層（Level 3）
**狀態**：🟡 PLANNING — 待用戶 approve

---

## 進度總覽

- **Day 0**：⏸ Plan + Checklist + branch（4h）
- **Day 1**：⏸ ToolSpec extension（CARRY-021）+ ToolRegistryImpl（5h）
- **Day 2**：⏸ ToolExecutorImpl + PermissionChecker（6h）
- **Day 3**：⏸ SandboxBackend + SubprocessSandbox + exec_tools（5h）
- **Day 4**：⏸ search_tools + hitl_tools + memory_tools placeholder + tests（6h）
- **Day 5**：⏸ 18 業務 stub migration + _inmemory.py 刪 + retro + closeout（5h）

**Plan total**：31h / **Actual estimate**：6-8h

---

## Day 0 — Plan / Checklist / Branch / Phase README sync（預估 4 小時）

### 0.1 Sprint plan 撰寫（45 min）
- [ ] **撰寫 sprint-51-1-plan.md**
  - DoD: 含 Sprint Goal + 5 User Stories + 6 架構決策 + File Change List + Acceptance Criteria + Deliverables + 6 Risks + V2 紀律對照
  - 已完成 ✅（本 commit 提交）

### 0.2 Sprint checklist 撰寫（45 min）
- [ ] **撰寫 sprint-51-1-checklist.md**（本檔）
  - DoD: Day 0-5 task 全列；每項 ≤ 90 min；含 DoD + verification command
  - 已完成 ✅（本 commit 提交）

### 0.3 Phase 51 README 同步（30 min）
- [ ] **修改 phase-51-tools-memory/README.md** — Sprint 51.1 狀態 ⏸→🟡 PLANNING
  - DoD: README Sprint 表更新 51.1 狀態 + 範圍預覽

### 0.4 建立 branch（10 min）
- [ ] **`git checkout -b feature/phase-51-sprint-1-cat2-tool-layer` from main**
  - DoD: branch 從 main HEAD（51.0 merge commit `8cd47ca`）切；當前未動 main
  - **已執行**：branch 在 51.0 closeout 後建立

### 0.5 確認 50.x / 51.0 baseline ready（30 min）
- [ ] **`make_default_executor` / `register_all_business_tools` / 18 ToolSpec / InMemoryToolRegistry 全 importable**
  - DoD: smoke import test
  - Command: `python -c "from business_domain._register_all import make_default_executor; from agent_harness.tools._inmemory import InMemoryToolRegistry; reg, exe = make_default_executor(); print(len(reg.list()))"` ≥ 19

### 0.6 確認 jsonschema lib 可用（15 min）
- [ ] **`python -c "import jsonschema; print(jsonschema.__version__)"` ≥ 4.20**
  - DoD: jsonschema 在 backend deps；如缺，加到 pyproject.toml requirements 並重 install
  - 49.1 baseline 應已含

### 0.7 Day 0 commit（10 min）
- [ ] **commit `docs(plan, sprint-51-1): Day 0 plan + checklist + Phase 51 README`**
  - DoD: 3 docs 提交；branch HEAD = Day 0 commit；working tree clean (除用戶 IDE work)

---

## Day 1 — ToolSpec extension + ToolRegistryImpl（預估 5 小時）

### 1.1 ToolSpec 加 hitl_policy + risk_level field（CARRY-021）（45 min）
- [ ] **修改 `_contracts/tools.py:ToolSpec`** 加兩個 field 帶 default
  - DoD: `hitl_policy: HITLPolicy = HITLPolicy.AUTO` + `risk_level: Literal["low","medium","high"] = "low"`
  - import HITLPolicy from `_contracts.hitl`（forward-ref 或直接 import）
  - mypy strict pass

### 1.2 17.md §1.1 sync ToolSpec dataclass 表（30 min）
- [ ] **修改 `17-cross-category-interfaces.md` §1.1**
  - DoD: ToolSpec 表加 hitl_policy + risk_level row；註明 51.1 加入 + 替代 51.0 tags-encoded

### 1.3 50.x / 51.0 既存測試 baseline run（30 min）
- [ ] **`PYTHONPATH=src python -m pytest --tb=line` 跑全 test**
  - DoD: 283 PASS / 0 SKIPPED 不變（ToolSpec 加 default field 應 backward-compat）
  - 若 fail：修 ToolSpec field default 或 dataclass(frozen=True) 互動

### 1.4 ToolRegistryImpl class（60 min）
- [ ] **`agent_harness/tools/registry.py:ToolRegistryImpl(ToolRegistry)`**
  - DoD:
    - `register(spec) -> None` 含 duplicate detection + JSONSchema validate spec.input_schema
    - `get(name) -> ToolSpec | None`
    - `list() -> list[ToolSpec]`
    - `by_tag(tag) -> list[ToolSpec]` helper
  - File header 完整

### 1.5 tools/__init__.py 加 export（15 min）
- [ ] **export ToolRegistryImpl + 保留 ToolRegistry ABC export**
  - DoD: `from agent_harness.tools import ToolRegistry, ToolRegistryImpl` 兩者都可

### 1.6 Day 1 commit（15 min）
- [ ] **commit `feat(tools, sprint-51-1): Day 1 — ToolSpec hitl_policy/risk_level + ToolRegistryImpl + 17.md §1.1 sync`**
  - DoD: 283 baseline 全 PASS；mypy strict OK

---

## Day 2 — ToolExecutorImpl + PermissionChecker（預估 6 小時）

### 2.1 PermissionDecision enum + PermissionChecker class（60 min）
- [ ] **`agent_harness/tools/permissions.py`**
  - DoD: PermissionDecision = ALLOW / REQUIRE_APPROVAL / DENY enum；PermissionChecker.check(spec, call, context) returns Decision
  - 3 維度檢查：HITL policy / risk_level / annotations.destructive

### 2.2 ToolExecutorImpl class（90 min）
- [ ] **`agent_harness/tools/executor.py:ToolExecutorImpl(ToolExecutor)`**
  - DoD:
    - `__init__` 接 handlers dict + permission_checker + tracer
    - `execute(call, *, trace_context=None)` — pre-check permission → JSONSchema validate → run handler → emit metric
    - `execute_batch(calls)` — 依 ConcurrencyPolicy 路由 read-parallel via asyncio.gather / write-sequential

### 2.3 JSONSchema validation（30 min）
- [ ] **executor.execute() 加 validator**
  - DoD: bad input → ToolResult.success=False + error="schema mismatch: <field>: <reason>"；validator cached per spec
  - test 覆蓋

### 2.4 Permission tests（45 min）
- [ ] **`tests/unit/tools/test_executor.py` permission gate tests**
  - DoD: 3 種 Decision 各 ≥ 1 test（ALLOW / REQUIRE_APPROVAL / DENY）
  - test 用 spec.hitl_policy / spec.risk_level 不同組合

### 2.5 Concurrency tests（45 min）
- [ ] **`tests/unit/tools/test_executor.py` concurrency tests**
  - DoD: read-only → asyncio.gather；write → sequential；ALL_PARALLEL → gather；mock handlers 計時驗證

### 2.6 Day 2 commit（15 min）
- [ ] **commit `feat(tools, sprint-51-1): Day 2 — ToolExecutorImpl + PermissionChecker + JSONSchema validation`**
  - DoD: pytest 全 PASS；mypy strict OK

---

## Day 3 — SandboxBackend + SubprocessSandbox + exec_tools（預估 5 小時）

### 3.1 SandboxBackend ABC + SandboxResult dataclass（30 min）
- [ ] **`agent_harness/tools/sandbox.py:SandboxBackend(ABC)` + `SandboxResult`**
  - DoD: ABC method `execute(code, *, timeout_seconds, memory_mb, network_blocked) -> SandboxResult`
  - SandboxResult: stdout, stderr, exit_code, duration_seconds, killed_by_timeout

### 3.2 SubprocessSandbox impl（90 min）
- [ ] **`agent_harness/tools/sandbox.py:SubprocessSandbox`**
  - DoD: subprocess.Popen + asyncio wait + resource.setrlimit (POSIX) / Job Object (Windows)
  - timeout 觸發 kill；memory limit (POSIX) `RLIMIT_AS`
  - network_blocked: skip 51.1（CARRY 為 51.x；用 doc 註明）

### 3.3 Sandbox isolation tests（60 min）
- [ ] **`tests/unit/tools/test_sandbox.py`**
  - DoD:
    - test_subprocess_returns_stdout（happy path）
    - test_timeout_kills_runaway（while True loop → killed_by_timeout=True）
    - test_filesystem_write_blocked（嘗試 `open("/tmp/escape.txt", "w")` → 失敗）— platform-specific
    - test_exit_code_propagated（sys.exit(42) → exit_code=42）

### 3.4 exec_tools.py — python_sandbox ToolSpec + handler（45 min）
- [ ] **`agent_harness/tools/exec_tools.py`**
  - DoD: ToolSpec(name="python_sandbox", input_schema={code: str}, annotations destructive=False, idempotent=False, sandbox-required tag)
  - handler 用 SubprocessSandbox.execute(call.arguments["code"])
  - hitl_policy=HITLPolicy.AUTO + risk_level="medium"（執行任意 code 即使 sandboxed 也 medium risk）

### 3.5 Day 3 commit（15 min）
- [ ] **commit `feat(tools, sprint-51-1): Day 3 — SandboxBackend + SubprocessSandbox + python_sandbox tool`**
  - DoD: pytest 全 PASS；sandbox isolation tests pass on Linux/macOS（Windows xfail OK）

---

## Day 4 — search_tools + hitl_tools + memory_tools + tests（預估 6 小時）

### 4.1 search_tools.py — web_search ToolSpec + handler（75 min）
- [ ] **`agent_harness/tools/search_tools.py`**
  - DoD: ToolSpec web_search input_schema {query, top_k}
  - handler 用 httpx async 打 Bing Search API（env BING_SEARCH_API_KEY；缺時 raise ConfigError）
  - hitl_policy=HITLPolicy.AUTO + risk_level="low"
  - Test 用 mock httpx response（real key smoke 留 CARRY-024）

### 4.2 hitl_tools.py — request_approval ToolSpec + handler（45 min）
- [ ] **`agent_harness/tools/hitl_tools.py`**
  - DoD: ToolSpec request_approval input_schema {message, severity}
  - handler return PermissionDecision.REQUIRE_APPROVAL serialized as ToolResult content（含 approval_request_id placeholder）
  - hitl_policy=HITLPolicy.ALWAYS_ASK（self-referential：tool 本身 always_ask）+ risk_level="medium"

### 4.3 memory_tools.py — placeholder ToolSpec（30 min）
- [ ] **`agent_harness/tools/memory_tools.py`**
  - DoD: 2 placeholder ToolSpec（memory_search / memory_write）handler 回 `NotImplementedError("memory_tools placeholder; Sprint 51.2 wires Cat 3")`
  - 文件註明 51.2 接 Cat 3 真實實作

### 4.4 4 built-in tools register helpers（30 min）
- [ ] **`agent_harness/tools/__init__.py` 加 `register_builtin_tools(registry, handlers)`**
  - DoD: 一次註冊 4 內建工具 + 補回 echo_tool（從原 _inmemory.py 改地）
  - export `register_builtin_tools`

### 4.5 Integration test：4 built-in via registry（60 min）
- [ ] **`tests/integration/tools/test_builtin_tools.py`**
  - DoD: register_builtin_tools → 4 + echo = 5 specs；execute happy path 各 1 case

### 4.6 17.md §3.1 sync — 4 built-in entries（30 min）
- [ ] **修改 `17-cross-category-interfaces.md` §3.1**
  - DoD: web_search / python_sandbox / request_approval / memory_search / memory_write entries 加（refining 51.0 entries with new fields）

### 4.7 Day 4 commit（15 min）
- [ ] **commit `feat(tools, sprint-51-1): Day 4 — 4 built-in tools (search/exec/hitl + memory placeholder) + 17.md §3.1 sync`**
  - DoD: pytest 全 PASS

---

## Day 5 — Migration + _inmemory.py delete + retro + closeout（預估 5 小時）

### 5.1 18 業務 stub migration tags → first-class field（90 min）
- [ ] **修改 5 file `business_domain/{patrol,correlation,rootcause,audit_domain,incident}/tools.py`**
  - DoD: 每個 ToolSpec 移除 `tags=("hitl_policy:*", "risk:*", ...)` 中的 hitl_policy / risk 編碼，加 first-class `hitl_policy=...` + `risk_level=...`
  - 保 `tags=("domain:*",)`（domain tag 持續用作分類）
  - 18 spec 全 mypy strict pass

### 5.2 `make_default_executor()` 切到 ToolRegistryImpl + ToolExecutorImpl（30 min）
- [ ] **修改 `business_domain/_register_all.py`**
  - DoD: 用 ToolRegistryImpl + ToolExecutorImpl 取代 InMemoryToolRegistry + InMemoryToolExecutor
  - executor 注入 PermissionChecker + tracer

### 5.3 `_inmemory.py` 整檔刪除（30 min）
- [ ] **delete `agent_harness/tools/_inmemory.py`**
  - DoD: file 不存在；同時刪所有 `from agent_harness.tools._inmemory import` 站點
  - Verify: `grep -r "InMemoryToolRegistry\|InMemoryToolExecutor\|make_echo_executor" backend/src/` = 0 hits

### 5.4 既存 283 tests 回歸驗證（45 min）
- [ ] **`PYTHONPATH=src python -m pytest --tb=short`**
  - DoD: 283 baseline + ~25 new = ~308 PASS / 0 SKIPPED；mock_services + 18 業務 + e2e 全 PASS
  - 若 fail：診斷 migration 影響並修

### 5.5 progress.md Day 0-5 全紀錄（30 min）
- [ ] **`docs/03-implementation/agent-harness-execution/phase-51/sprint-51-1/progress.md`**
  - DoD: Day 0-5 各 1 entry；估時 vs actual 表

### 5.6 retrospective.md（30 min）
- [ ] **`docs/03-implementation/agent-harness-execution/phase-51/sprint-51-1/retrospective.md`**
  - DoD: 含 Did Well / Improve / Action Items / 估時準度 / 範疇成熟度 Post-51.1（Cat 2 → Level 3）

### 5.7 Phase 51 README 更新 51.1 ✅ DONE（15 min）
- [ ] **`phase-51-tools-memory/README.md`**
  - DoD: Sprint 51.1 ✅ DONE 標記；Cat 2 Level 1+ → Level 3；Sprint 進度 2/3 = 67%

### 5.8 sprint-51-1-checklist 全 [x] / 🚧（10 min）
- [ ] **本檔所有 `[ ]` → `[x]` 或標 🚧 + reason**
  - DoD: 0 個未勾選殘留

### 5.9 Day 5 closeout commit（15 min）
- [ ] **commit `docs(closeout, sprint-51-1): Day 5 — migration + _inmemory delete + progress + retro + Phase 51 README`**
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
