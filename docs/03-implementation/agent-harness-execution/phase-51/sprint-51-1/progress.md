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

## 估時 vs Actual（rolling）

| Day | Plan | Actual | % |
|-----|------|--------|---|
| 0   | 4h   | ~1h    | 25% |
| 1   | 5h   | ~1h    | 20% |
| **累計** | **9h** | **~2h** | **22%** |

V2 7-sprint avg 20%；51.0 23%；51.1 早期 22%（趨勢 nominal）。

---

**Maintainer**：用戶 + AI 助手共同維護
