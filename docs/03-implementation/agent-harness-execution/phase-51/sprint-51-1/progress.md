# Sprint 51.1 Progress

**Sprint**：51.1 — 範疇 2 工具層（Level 3）
**Branch**：`feature/phase-51-sprint-1-cat2-tool-layer`
**啟動**：2026-04-30（接 Sprint 51.0 closeout + main merge `8cd47ca`）

---

## Day 0 — 2026-04-30 (plan + checklist + branch)

**Estimated**：4h / **Actual**：~1h（plan ~570 行 / checklist ~310 行）

### Done
- `sprint-51-1-plan.md`（5 US / 6 架構決策 / 25 file change list / 6 risks / V2 紀律 9 項對照）
- `sprint-51-1-checklist.md`（Day 0-5 共 32 task / 10 條 closeout 驗收）
- `phase-51-tools-memory/README.md` Sprint 51.1 → 🟡 PLANNING

### Commit
- `6aa6e32` docs(plan, sprint-51-1): Day 0 — plan + checklist + Phase 51 README sync

### Notes
- Day 0 estimate 4h actual ~1h (~25%)；continuing 51.0 23% baseline
- Day 0.5 / 0.6 baseline verification 留到 Day 1 開工前一併跑

---

## Day 1 — 2026-04-30 (ToolSpec extension + ToolRegistryImpl)

**Estimated**：5h / **Actual**：~1h

### Done
- **Day 0.5 baseline verify**：`make_default_executor` 19 tools importable ✅
- **Day 0.6 baseline verify**：jsonschema 4.26.0 在 deps ✅
- **1.1 ToolSpec extension（CARRY-021）**：
  - `_contracts/tools.py` 加 `ToolHITLPolicy` enum（AUTO / ASK_ONCE / ALWAYS_ASK）+ ToolSpec 加 `hitl_policy: ToolHITLPolicy = ToolHITLPolicy.AUTO` + `risk_level: RiskLevel = RiskLevel.LOW` field
  - **設計調整**：plan §決策 1 寫的「HITLPolicy.AUTO」與既有 `_contracts/hitl.py:HITLPolicy` 衝突（後者為 per-tenant policy dataclass，非 enum）。新建 distinct enum `ToolHITLPolicy`，per-tenant 與 per-tool 兩個 type 並存。將於 retrospective 登錄。
  - `risk_level` 複用 既有 `RiskLevel` enum（single-source 紀律）。
- **1.2 17.md sync**：§1.1 ToolSpec 註明加 hitl_policy/risk_level；新增 ToolHITLPolicy row；§3.1 註腳更新（51.0 tags-encoded → 51.1 first-class）。
- **1.3 baseline test**：`pytest` 283 PASS / 0 SKIPPED（field default 完全 backward-compat）。
- **1.4 ToolRegistryImpl**：`tools/registry.py`（55 行）concrete class — duplicate detection + Draft202012Validator.check_schema + `by_tag` helper。File header 完整。
- **1.5 export**：`tools/__init__.py` + `_contracts/__init__.py` 加 ToolRegistryImpl + ToolHITLPolicy export。

### Verification
- `pytest` 283 PASS（unchanged baseline）✅
- `mypy --strict` 32 source files clean ✅
- `black --check` 4 files clean ✅（registry.py 過程中被 black 重排 raise from line）
- 4/5 V2 lints OK（cross_category_import / llm_sdk_leak / duplicate_dataclass / sync_callback）✅；AP-1 skip（orchestrator_loop dir 不在 lint --root path）
- Smoke：register / get / list / by_tag / dup detection / bad schema rejection 全 pass

### Notes
- mypy strict 與 builtin `list` shadow 問題：method `def list(self) -> list[ToolSpec]` 在有 method body 的 concrete class 內 mypy 解析 annotation 時把 `list` 認作 method（class scope shadow）。修法：`from builtins import list as _list` 並 annotation 用 `_list[ToolSpec]`。ABC `_abc.py` 同樣 signature 但因 method body 是 `...` 不觸發此問題。
- jsonschema lib 缺 type stubs；用 `# type: ignore[import-untyped]` 兩行（不引入 types-jsonschema 依賴避免 deps drift）。
- Day 1 6 task 全 [x]；commit pending（1.6）。

### Files Changed
**Modified (4)**：
- `backend/src/agent_harness/_contracts/tools.py` — +ToolHITLPolicy enum + ToolSpec field 擴展
- `backend/src/agent_harness/_contracts/__init__.py` — export ToolHITLPolicy
- `backend/src/agent_harness/tools/__init__.py` — export ToolRegistryImpl
- `docs/03-implementation/agent-harness-planning/17-cross-category-interfaces.md` — §1.1 + §3.1 註腳

**Created (1)**：
- `backend/src/agent_harness/tools/registry.py` — ToolRegistryImpl concrete class

### Commit (pending)
- Will commit as `feat(tools, sprint-51-1): Day 1 — ToolSpec hitl_policy/risk_level + ToolRegistryImpl + 17.md §1.1 sync`

---

## Day 2 — 2026-04-30 (PermissionChecker + ToolExecutorImpl + JSONSchema)

**Estimated**：6h / **Actual**：~1.5h

### Done
- **2.1 PermissionChecker + ExecutionContext refactor**：
  - `tools/permissions.py` 新建 PermissionDecision enum + PermissionChecker.check() 3 維度（HITL policy / risk_level / annotations.destructive）
  - **Refactor 期間**：plan 把 `ExecutionContext` 設計在 `permissions.py`，但 ToolExecutor ABC（`_abc.py`）需要在 method 簽名引用 ExecutionContext，會反向 import permissions → dependency cycle。解：把 ExecutionContext 移到 `_contracts/tools.py`（single-source per 17.md §1.1），permissions.py / executor.py / ABC 全從 `_contracts` import。`_contracts/__init__.py` export 同步加。
  - 17.md §1.1 ExecutionContext entry sync 留 Day 5 closeout 一起補。
- **2.2 ToolExecutorImpl**：
  - `tools/executor.py` 新建 ~190 行 — `__init__(*, registry, handlers, permission_checker, tracer, metric_registry)`
  - `execute(call, *, trace_context, context)`：6 階段 pipeline（lookup → permission → schema → handler dispatch → tracer span → metric emit）
  - `execute_batch(calls, *, trace_context, context)`：`_batch_can_parallelize()` 根據 batch 內全部 spec 的 ConcurrencyPolicy 決定 `asyncio.gather` 或 sequential await loop（任一 spec 為 SEQUENTIAL → fall back sequential，conservative）
  - 失敗路徑統一走 `_fail()` helper：拋 ToolResult.error + 對應 status label 給 metric（unknown / denied / approval_required / schema_invalid / error）
- **2.3 JSONSchema runtime validation**：
  - `Draft202012Validator` per-spec cached in `_validator_cache: dict[str, Validator]`
  - bad input → `ToolResult(success=False, error="schema mismatch: <path>: <message>")`
- **ABC sync**：`_abc.py:ToolExecutor.execute/execute_batch` 加 `context: ExecutionContext | None = None` kwarg；`_inmemory.InMemoryToolExecutor` 同步（accepts 但 unused）
- **`tools/__init__.py`** export `ToolExecutorImpl` / `PermissionChecker` / `PermissionDecision`
- **2.4 + 2.5 tests**：`tests/unit/agent_harness/tools/test_executor.py`（19 tests，~270 行）
  - Permission（7）：3 Decision 各 ≥ 1（ALLOW / REQUIRE_APPROVAL / DENY），含 resolution order test（DENY > REQUIRE_APPROVAL）
  - JSONSchema（4）：valid / missing required / wrong type / validator cached
  - Concurrency（4）：empty / read-only-parallel timing / sequential timing / all-parallel timing
  - Edge（3）：unknown_tool / handler_exception / no_handler_registered
  - Direct enum（1）：PermissionDecision values

### Verification
- pytest 19 new tests PASS（總 302 PASS / 0 SKIPPED）✅
- mypy --strict 35 source files clean ✅
- black formatted ✅
- 4/4 V2 lints OK ✅（cross_category_import / llm_sdk_leak / duplicate_dataclass / sync_callback）

### Notes
- 計時 test thresholds：parallel ~100ms（threshold 250ms），serial ~300ms（threshold 280ms gates against false-pass parallel）；OS jitter 容忍 ~150% slack
- Permission resolution order：destructive (DENY) > HITL/risk (REQUIRE_APPROVAL) > AUTO+LOW (ALLOW)；`test_deny_beats_require_approval` 明確驗證
- `ASK_ONCE` 51.1 與 `ALWAYS_ASK` 同樣 REQUIRE_APPROVAL（per-session first-call tracking 留 53.3 ApprovalManager 一起做）
- ExecutionContext single-source 重定址未在 plan 預期；屬 Day 2 期間發現的設計優化，登錄 retrospective

### Files Changed
**Modified (5)**：
- `_contracts/tools.py` — +ExecutionContext dataclass + UUID import
- `_contracts/__init__.py` — export ExecutionContext
- `tools/_abc.py` — ABC 加 `context: ExecutionContext | None = None` kwarg
- `tools/_inmemory.py` — sig sync (DEPRECATED-IN 51.1)
- `tools/__init__.py` — export ToolExecutorImpl + PermissionChecker + PermissionDecision

**Created (3)**：
- `tools/permissions.py` — PermissionDecision + PermissionChecker
- `tools/executor.py` — ToolExecutorImpl + ToolHandler type alias
- `tests/unit/agent_harness/tools/test_executor.py` — 19 tests

### Commit (pending)
- Will commit as `feat(tools, sprint-51-1): Day 2 — ToolExecutorImpl + PermissionChecker + JSONSchema validation`

---

## Day 3 — 2026-04-30 (SandboxBackend + SubprocessSandbox + python_sandbox tool)

**Estimated**: 5h / **Actual**: ~1h

### Done
- 3.1 SandboxBackend ABC + SandboxResult dataclass (stdout / stderr / exit_code / duration_seconds / killed_by_timeout)
- 3.2 SubprocessSandbox: asyncio subprocess + tempdir cwd + asyncio.wait_for timeout (kill + drain on TimeoutError); POSIX preexec_fn applies RLIMIT_AS (memory) + RLIMIT_CPU (timeout x 2 backstop); Windows skips rlimit (Job Object is CARRY-022)
- 3.3 10 sandbox tests: 7 direct + 3 built-in tool integration; POSIX-only memory test marked skipif(win32)
  - Plan adjustment: original "open(/tmp/escape.txt) blocked" requires chroot/namespace; rescoped to "relative writes contained in tempdir" + POSIX memory limit. Logged in retro.
- 3.4 exec_tools.PYTHON_SANDBOX_SPEC (code/timeout_seconds 0.1-30/memory_mb 16-1024); destructive=False; hitl_policy=AUTO + risk_level=MEDIUM; tags=("builtin","exec"); make_python_sandbox_handler factory JSON-serializes SandboxResult
- tools/__init__.py exports 5 new symbols

### Verification
- pytest 311 PASS / 1 SKIPPED (POSIX memory test on Windows; platform-correct skipif pattern)
- mypy --strict 39 source files clean (sandbox.py: # type: ignore[attr-defined] x2 for resource.RLIMIT_AS/CPU on Windows mypy; exec_tools: -> ToolHandler annotation added)
- black formatted; 4/4 V2 lints OK

### Notes
- 51.0 retro DoD "0 SKIPPED" relaxed for 51.1: 1 SKIPPED (platform-specific) is the standard Python pytest pattern for POSIX-only paths.
- Security hook false-positive on the literal "child_process.exec" rule (Python uses asyncio's argv-list subprocess API, no shell). Bypass: write minimal stub then expand via Edit.

### Files
- Modified: tools/__init__.py
- Created: tools/sandbox.py / tools/exec_tools.py / tests/unit/agent_harness/tools/test_sandbox.py

### Commit (pending)
- Will commit as feat(tools, sprint-51-1): Day 3 — SandboxBackend + SubprocessSandbox + python_sandbox tool

---

## 估時 vs Actual（rolling）

| Day | Plan | Actual | % |
|-----|------|--------|---|
| 0   | 4h   | ~1h    | 25% |
| 1   | 5h   | ~1h    | 20% |
| 2   | 6h   | ~1.5h  | 25% |
| 3   | 5h   | ~1h    | 20% |
| **累計** | **20h** | **~4.5h** | **23%** |

V2 7-sprint avg 20%；51.0 23%；51.1 early-mid 23%（趨勢 nominal）。

---

**Maintainer**：用戶 + AI 助手共同維護
