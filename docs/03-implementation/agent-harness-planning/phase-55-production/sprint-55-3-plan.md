# Sprint 55.3 — Plan: Audit Cycle Mini-Sprint #1 (Groups A + G)

**Phase**: 55 (Production / V2 Closure Audit Cycles)
**Sprint Type**: Audit Cycle Mini-Sprint #1 (post-V2 22/22 closure)
**Branch**: `feature/sprint-55-3-audit-cycle-A-G`
**Estimated Duration**: 5 days (Day 0-4)
**Status**: Day 0 — Plan / Checklist drafting
**Author**: AI Assistant (laitim2001 ack)
**Created**: 2026-05-04

> **Modification History**
> - 2026-05-04: Initial draft (Sprint 55.3 Day 0)

---

## Sprint Goal

Close 6 carryover Audit Debt items (Groups A + G per scope ack) through a focused, low-risk mini-sprint:

- **Group A** (process / template, ~1.5 hr bottom-up):
  - **AD-Plan-1** — extend `sprint-workflow.md` §Step 3 with mandatory Day-0 plan-vs-repo grep verify
  - **AD-Lint-2** — drop per-day calibrated targets; keep only sprint-aggregate
  - **AD-Lint-3** — Modification History format → 1-line `YYYY-MM-DD: scope (Sprint XX.Y)`
- **Group G** (散件 backend, ~8.5-11 hr bottom-up):
  - **AD-Cat7-1** — Sole-mutator grep-zero refactor + CI lint enforcement
  - **AD-Hitl-7** — Per-tenant `HITLPolicy` DB persistence (new table + Alembic + RLS + DBHITLPolicyStore + DefaultHITLManager wiring)
  - **AD-Cat12-Helpers-1** — Extract `verification_span` to `agent_harness/observability/helpers.py` (cross-Cat reuse pattern)

**Outcome**: 6 ADs closed; calibration multiplier 0.40 (2nd application after 55.2 = 1.10 first-hit-in-band); V2 22/22 unchanged (audit cycle, not main progress).

---

## Background

### V2 Closure Status (post-Sprint 55.2)

V2 重構達成 **22/22 (100%)** 於 2026-05-04(Sprint 55.2 PR #85 merged `9a8296ae`)。 11+1 範疇全 Level 4(Cat 9 L5);5 business domains production-capable;LLM Provider Neutral CI-enforced;Multi-tenant 3 鐵律。

V2 closure ≠ open items closed。Per `SITUATION-V2-SESSION-START.md` §第八部分,主要 carryover 包括 Cat 8/9/10/11 backend backlog、Cat 7 audit、§HITL DB persistence、Cat 12 helpers、process/template updates、Cat 10 frontend panel、infra (Dockerfile / paths-filter)。

### 處理框架(用戶 approved 2026-05-04)

**方案 1 多 mini-sprint** (vs 單一大 bundle):
- 53.7 audit bundle (9 AD) 是 close + lint fix 為主(範圍小);本輪 AD 多含 production wiring(中-大範圍)
- Calibration 在 0.40 起點,需逐 sprint 驗證 ratio 是否回到 [0.85, 1.20] 帶
- 每 sprint retrospective 可讓設計向 review 階段更平滑

**Audit cycle 路線**:
```
55.3 (audit cycle 1) — Groups A + G        (process + 散件 backend)  ← THIS SPRINT
55.4 (audit cycle 2) — Groups B + C        (Cat 8 + Cat 9 backend)
55.5 (audit cycle 3) — Groups D + E        (Cat 10 + Cat 11 backend)
55.6 (audit cycle 4) — Group F             (Cat 10 frontend)
Group H (#31 / AD-CI-5 / AD-CI-6)          → infra track, no sprint binding
```

55.3 起步刻意輕量(process + 散件)以驗證 0.40 ratio 是否在 band,確認後再進入 55.4 較大 backend scope。

### Day-0 Pre-flight Findings (AD-Plan-1 newly-applied)

Per AD-Plan-1 mandatory Day-0 探勘 grep(這是該 AD 第一次自我應用):

| Finding | Source | Implication |
|---------|--------|-------------|
| `state.messages.append \| state.scratchpad \| state.tool_calls` 三 pattern grep-zero in `backend/src/agent_harness/` | 5-call grep | **D1 — AD-Cat7-1 scope smaller**;sole-mutator 大部分已達成;scope 收斂為 enforcement test + grep CI lint + 殘餘違規 audit log |
| `verification/_obs.py` already exists with `verification_span` async ctx mgr; `business_domain/_obs.py` 同 pattern | Read tool | **D2 — AD-Cat12-Helpers-1 是 extract**(non-create);可泛化為 `category_span(name, category)` 並 refactor 兩處呼叫 |
| `DefaultHITLManager.__init__` 接受 `default_policy: HITLPolicy \| None` in-memory fallback;no DB persistence | Read tool | **D3 — AD-Hitl-7 baseline**;設計 = `hitl_policies` table + `DBHITLPolicyStore` + `get_policy(tenant_id)` from DB,fallback to `default_policy` |

→ Drift findings catalog 起步 D1-D3;Day 1+ 預期再加入。

---

## Audit Debt Items

### AD-Plan-1 — Day-0 Plan-vs-Repo Grep Verify (Process)

**Source**: 53.7 retrospective Q4 (5 drift findings D4-D12 cost ~1 hr re-work)

**Why**: Plans drafted from session memory + retro context drift from real repo. Day-0 探勘 must grep each plan §Technical Spec assertion (file paths / class names / table names / fixture paths) against actual repo state before code starts.

**Spec**:
- Extend `.claude/rules/sprint-workflow.md` §Step 3 "Implement Code" 章節前,加 §Step 2.5 "Day-0 Plan-vs-Repo Verify" — 強制要求:
  - Grep 每個 plan §Technical Spec 提及的檔案路徑 / class 名 / table 名 / fixture path
  - Catalog drift findings 在 progress.md Day 0 entry
  - 必要時 update plan §Risks(不修改 §Spec — preserves audit trail)
- 加 catalog 範例(來自 53.7 D4-D12 + 55.3 D1-D3)
- Cross-link 到 `anti-patterns-checklist.md` AP-2 (no orphan code)

**File**: `.claude/rules/sprint-workflow.md` (edit)

**Estimated**: 0.5 hr

---

### AD-Lint-2 — Drop Per-Day Calibrated Targets (Template)

**Source**: 53.7 retrospective Q4 + Sprint 53.7 Day 2/3 over-runs offset by Day 1 / Day 4 banking

**Why**: Day-level estimates have higher variance than sprint-level (53.7 banking offset Day 2/3 over-runs against budget). Per-day calibrated targets create false precision and trigger anxiety mid-sprint when Day N slips.

**Spec**:
- `.claude/rules/sprint-workflow.md` checklist template section: drop "Estimated X hours" header from each Day section
- Keep sprint-aggregate "Workload" estimate in plan §Workload only
- 加 doc note: per-day estimates 可放 progress.md Day entry(個人記錄),但 not in checklist(template noise)

**File**: `.claude/rules/sprint-workflow.md` (edit; same file as AD-Plan-1)

**Estimated**: 0.5 hr (combined edit pass with AD-Plan-1)

---

### AD-Lint-3 — Modification History 1-Line Format (Template)

**Source**: 54.2 retrospective Q4 (4× flake8 E501 hits in Day 4 from MHist accumulation)

**Why**: Multi-line MHist entries accumulate in mature files (50+ lines header eventually);each new entry 跨 100 字符限制,反覆 hit flake8 E501。Verbose MHist 重複 commit message + git blame 已紀錄。

**Spec**:
- `.claude/rules/file-header-convention.md` §Modification History 詳細規範:
  - 將「格式」段(L188-195)改為 1-line max:`YYYY-MM-DD: scope (Sprint XX.Y) — <≤60 char one-line reason>`
  - 範例段更新所有 file (Python / TypeScript / Markdown) 改為 1-line entries
  - 加禁止項:多段 reason / 換行 / quote markers
- Optional: extend `flake8` to enforce E501 fail-fast(現已 fail-fast since 49.2)— 確認無需 config change

**File**: `.claude/rules/file-header-convention.md` (edit)

**Estimated**: 0.5 hr

---

### AD-Cat7-1 — Sole-Mutator Grep-Zero + CI Lint (Cat 7)

**Source**: 53.1 retrospective Q5 (full sole-mutator pattern was deferred due to time)

**Why**: V2 LoopState 應只透過 `DefaultReducer.apply(state, event)` 變更(範疇 7 single-mutator pattern);ad-hoc `state.messages.append(...)` / `state.scratchpad[...] = ...` / `state.tool_calls.append(...)` 違反 reducer 唯一入口契約。

**D1 (Day-0 探勘)**: 三 pattern 全 grep-zero in `backend/src/agent_harness/` → sole-mutator 大部分已達成 → scope 收斂。

**Spec**:
1. **Verify grep-zero** in production code (Day 1):
   - `backend/src/agent_harness/**/*.py`(excluding `state_mgmt/reducer.py` which IS the sole mutator)
   - `backend/src/api/**/*.py`
   - `backend/src/business_domain/**/*.py`
   - `backend/src/platform_layer/**/*.py`
2. **Add CI lint script** `backend/scripts/lint/check_sole_mutator.py`:
   - Disallowed patterns: `state\.messages\.append`, `state\.scratchpad\[`, `state\.tool_calls\.append`, `state\.user_input\s*=`(direct user_input rebind 也只允許 reducer)
   - Whitelist: `agent_harness/state_mgmt/reducer.py`, `tests/**`
   - Exit 1 on any match in production code
3. **Add unit test** `backend/tests/unit/state_mgmt/test_sole_mutator_lint.py`:
   - Subprocess invokes `check_sole_mutator.py`;assert exit 0
   - Inject violation into temp file;assert exit 1
4. **Wire into 6 V2 lints**:
   - Update `backend/scripts/lint/run_all.py` to invoke `check_sole_mutator.py`(7th lint;rename comment "6 V2 lints" → "7 V2 lints")
5. **Audit log** 殘餘違規(if any found in Step 1):
   - Catalog in progress.md Day 1 entry
   - 修補 to use `reducer.apply(...)` pattern

**Estimated**: 3-4 hr (~3.5 hr;range reflects whether residual violations exist in agent_harness/api/business_domain/platform_layer)

**Files**:
- `backend/scripts/lint/check_sole_mutator.py` — new
- `backend/scripts/lint/run_all.py` — edit (add 7th lint)
- `backend/tests/unit/state_mgmt/test_sole_mutator_lint.py` — new

---

### AD-Hitl-7 — Per-Tenant HITLPolicy DB Persistence (§HITL)

**Source**: 53.4 retrospective Q5 (per-tenant HITLPolicy was deferred to enable 53.5 frontend focus)

**Why**: `DefaultHITLManager.__init__` 只接受 `default_policy: HITLPolicy | None`(in-memory fallback);無法 per-tenant 設定不同 risk thresholds / approver_roles / sla_seconds。生產環境多租戶必須 per-tenant override。

**D3 (Day-0 探勘)**: HITLPolicy 已存在於 3 處(`_contracts/hitl.py` spec / `manager.py` impl / `_contracts/tools.py` reference);DB persistence 是新增層,**不變更** spec / ABC。

**Spec**:
1. **DB Schema** — new table `hitl_policies`:
   - Columns: `id UUID PK`, `tenant_id UUID NOT NULL`(FK tenants), `risk_thresholds JSONB`, `approver_roles JSONB`, `sla_seconds INT`, `escalation_chain JSONB`, `created_at`, `updated_at`
   - Constraint: `UNIQUE (tenant_id)`(per-tenant 單一 row;若需多 policy variant by category 需 future scope)
   - RLS policy: tenant-isolation per `multi-tenant-data.md` §Rule 1
   - Alembic migration: `0013_hitl_policies.py`(reuse 0012 RLS policy pattern)
2. **ORM Model** — `infrastructure/db/models/governance.py`:
   - `class HitlPolicyRow(Base)` mapping to `hitl_policies` table
3. **DBHITLPolicyStore ABC + Default Impl**:
   - ABC: `agent_harness/hitl/_abc.py` — add `class HITLPolicyStore` ABC with `async def get(tenant_id) -> HITLPolicy | None`
   - Default: `platform_layer/governance/hitl/policy_store.py` — `DBHITLPolicyStore` reading from `hitl_policies` table
4. **Wire into DefaultHITLManager**:
   - `__init__` 接受 `policy_store: HITLPolicyStore | None = None`
   - `get_policy(tenant_id)` 改為:if `policy_store` 提供 → query DB by tenant_id;若 None or no row → fallback to `default_policy`
5. **ServiceFactory wiring**:
   - `platform_layer/governance/service_factory.py` — when constructing `DefaultHITLManager`, also instantiate `DBHITLPolicyStore` if not test
6. **Tests**:
   - Unit: `test_db_hitl_policy_store.py` — fakedb 連線, get/get_missing/get_with_rls; insert sample policy → retrieve match
   - Integration: `test_hitl_manager_per_tenant_policy.py` — 2 tenants 各 insert 不同 policy;verify `get_policy(tenant_a) ≠ get_policy(tenant_b)`;tenant_c (no row) → returns default_policy
   - Reset singleton: per-suite autouse fixture(per `testing.md` §Module-level Singleton Reset Pattern)

**Estimated**: 4-5 hr (~4.5 hr;DB schema + Alembic + RLS + ABC + Default + tests)

**Files**:
- `backend/alembic/versions/0013_hitl_policies.py` — new
- `backend/src/infrastructure/db/models/governance.py` — edit (add `HitlPolicyRow`)
- `backend/src/agent_harness/hitl/_abc.py` — edit (add `HITLPolicyStore` ABC)
- `backend/src/platform_layer/governance/hitl/policy_store.py` — new (DBHITLPolicyStore)
- `backend/src/platform_layer/governance/hitl/manager.py` — edit (`__init__` + `get_policy`)
- `backend/src/platform_layer/governance/service_factory.py` — edit
- `backend/tests/unit/governance/hitl/test_db_hitl_policy_store.py` — new
- `backend/tests/integration/governance/test_hitl_manager_per_tenant_policy.py` — new

---

### AD-Cat12-Helpers-1 — Extract verification_span (Cat 12)

**Source**: 54.2 retrospective Q5 + Day-0 D2 finding

**Why**: `verification/_obs.py:verification_span` 是 async ctx mgr emitting `verifier.{name}` span under `SpanCategory.VERIFICATION`;`business_domain/_obs.py` 同 pattern 但 different category。Cat 11 dispatch / mailbox / handoff observability 將需要相同模式 → DRY violation 累積。

**D2 (Day-0 探勘)**: `verification_span` + `business_domain` _obs span 共用 single helper 即可;Cat 8 retry / Cat 11 subagent 將受惠於 same helper。

**Spec**:
1. **Create** `backend/src/agent_harness/observability/helpers.py`:
   - `category_span(tracer, name, category) -> AsyncIterator[None]` — generic async ctx mgr
   - Cleaner signature: `tracer: Tracer | None`, `name: str`, `category: SpanCategory`
   - No-op when tracer is None (preserves 54.2 D8 wrapper pattern)
2. **Refactor** `agent_harness/verification/_obs.py`:
   - Keep `verification_span` thin wrapper: `lambda tracer, n: category_span(tracer, f"verifier.{n}", SpanCategory.VERIFICATION)`
   - **OR** delete `_obs.py` 完全 + 直接呼叫 `category_span(tracer, f"verifier.{name}", SpanCategory.VERIFICATION)` from rules_based.py + llm_judge.py(more direct;preserves 17.md single-source pattern)
   - **Decision in Day 1**: Choose Option A (thin wrapper) or B (direct call) based on usage count
3. **Refactor** `business_domain/_obs.py`:
   - Same pattern as verification/_obs.py decision
4. **Refactor 4 verifier classes**:
   - `verification/rules_based.py` — `async with verification_span(...)` → 不變 OR `async with category_span(...)`
   - `verification/llm_judge.py` — same
   - Cat 9 wrappers (`guardrails/llm_judge_fallback.py` / `guardrails/llm_verify_mutate.py`):per 54.2 D19, reuse inner judge tracer — **不動** unless Cat 9 wrappers also extract
5. **Tests**:
   - Unit: `backend/tests/unit/observability/test_category_span.py` — tracer=None no-op + tracer mock 驗 span emit
   - Regression: existing 2 verifier tests pass post-refactor

**Estimated**: 1.5-2 hr (~1.75 hr;extract + refactor + tests)

**Files**:
- `backend/src/agent_harness/observability/helpers.py` — new
- `backend/src/agent_harness/verification/_obs.py` — edit OR delete
- `backend/src/agent_harness/verification/rules_based.py` — edit (import path)
- `backend/src/agent_harness/verification/llm_judge.py` — edit (import path)
- `backend/src/business_domain/_obs.py` — edit OR delete
- `backend/src/business_domain/_base.py` — edit (import path)
- `backend/tests/unit/observability/test_category_span.py` — new

---

## Technical Specifications

### Calibration Multiplier Strategy

| Sprint | Mult | Bottom-up | Committed | Actual | Ratio |
|--------|------|-----------|-----------|--------|-------|
| 53.7 | 0.55 | 13.5 hr | 7.4 hr | 7.5 hr | 1.01 ✅ in band |
| 54.1 | 0.55 | 18.5 hr | 10.2 hr | 7 hr | 0.69 below |
| 54.2 | 0.55 | 22.5 hr | 12.4 hr | 8 hr | 0.65 below |
| 55.1 | 0.50 | 22 hr | 11 hr | 7.5 hr | 0.68 below |
| 55.2 | 0.40 | 17.5 hr | 7 hr | 7.7 hr | 1.10 ✅ in band |
| **55.3** | **0.40** | **~10-12.5 hr** | **~4-5 hr** | TBD | 2nd application of 0.40 |

**Strategy**: 0.40 carry-over from 55.2(first hit in band)。If 55.3 ratio ∈ [0.85, 1.20] → confirm 0.40 stable for Phase 56+。 If outside band → AD-Phase56-Calibration triggers re-baseline。

### Group A Edit Strategy

3 ADs(AD-Plan-1 / AD-Lint-2 / AD-Lint-3)合併為 Day 1 早段single-pass edit:
- 兩個 ADs 共改 `sprint-workflow.md`(combine commit)
- AD-Lint-3 改 `file-header-convention.md`(separate commit)
- 共 2 commits in Day 1 morning

### Group G Sequential Strategy

3 ADs 各自獨立 commit + test pass:
- Day 1 afternoon: AD-Cat12-Helpers-1(unblocks future Cat 11 obs)
- Day 2: AD-Cat7-1(grep + lint script + test)
- Day 3: AD-Hitl-7(DB schema + ABC + impl + tests + integration)

### LLM Provider Neutrality / Single-source

- AD-Cat12-Helpers-1 不引入 LLM SDK;observability 層中性
- AD-Hitl-7 不變更 `_contracts/hitl.py` HITLPolicy spec;只新增 storage layer
- AD-Cat7-1 lint script 不 import LLM SDK
- 17.md updates(if any)— 預期無;AD-Hitl-7 加 `HITLPolicyStore` ABC 在 `agent_harness/hitl/_abc.py` 屬於範疇內,不需 17.md update

---

## Acceptance Criteria

| Criterion | Target | Verify |
|-----------|--------|--------|
| AD-Plan-1 closed | `sprint-workflow.md` §Step 2.5 added with mandatory grep verify + drift catalog example | grep `## Step 2.5` returns 1 |
| AD-Lint-2 closed | Per-day "Estimated X hours" headers removed from checklist template; sprint-aggregate kept in plan | grep `Estimated.*hours` in checklist template returns 0 |
| AD-Lint-3 closed | `file-header-convention.md` §Modification History 1-line format; all 3 examples (Python/TS/MD) updated | grep `Modification History (newest-first):` shows 1-line entries only |
| AD-Cat7-1 closed | grep-zero in production code + `check_sole_mutator.py` runs in `run_all.py` + unit test passes | `python scripts/lint/check_sole_mutator.py` exit 0 + `pytest test_sole_mutator_lint.py` |
| AD-Hitl-7 closed | `hitl_policies` table + `DBHITLPolicyStore` + DefaultHITLManager wiring + 2-tenant integration test green | `pytest test_db_hitl_policy_store.py test_hitl_manager_per_tenant_policy.py` |
| AD-Cat12-Helpers-1 closed | `category_span` extracted; 2 verifier classes use new helper; existing tests pass; new helper unit test passes | `pytest test_category_span.py` + Cat 10 verifier tests |
| Tests added | ≥+12(AD-Cat7-1: 2-3, AD-Hitl-7: 5-7, AD-Cat12-Helpers-1: 3-4) | pytest count: 1416 → ≥1428 |
| 6 V2 lints (now 7) | All green in run_all.py | `python scripts/lint/run_all.py` exit 0 |
| LLM SDK leak | 0 in agent_harness/ + infrastructure/ | grep check (CI enforced) |
| mypy --strict | 0 errors | `mypy backend/src --strict` |
| Calibration ratio | ∈ [0.85, 1.20] | Day 4 retro Q2 |

---

## Day-by-Day Plan

### Day 0 — Plan / Checklist + Day-0 探勘 (½ day)

- Verify working tree clean on main `596405b3`
- Branch `feature/sprint-55-3-audit-cycle-A-G` created (✓ done)
- Day-0 探勘 grep(AD-Plan-1 newly self-applied)— 5 grep + 2 file reads (✓ done; D1-D3 catalogued)
- Read most-recent completed sprint plan(55.2)as template (✓ done; 13 sections confirmed)
- Write `sprint-55-3-plan.md`(this file)+ `sprint-55-3-checklist.md`
- Write Day 0 `progress.md`
- Commit Day 0(plan + checklist + progress)

### Day 1 — Group A + AD-Cat12-Helpers-1 (~1.75-2.5 hr)

- **Morning** (~1 hr):
  - AD-Plan-1 + AD-Lint-2: edit `.claude/rules/sprint-workflow.md`(combined commit)
  - AD-Lint-3: edit `.claude/rules/file-header-convention.md`(separate commit)
- **Afternoon** (~1.5 hr):
  - AD-Cat12-Helpers-1: create `observability/helpers.py` + decide Option A/B + refactor + tests
- Update progress.md Day 1 entry

### Day 2 — AD-Cat7-1 (~3-4 hr)

- Verify grep-zero in 4 production paths (agent_harness / api / business_domain / platform_layer)
- Catalog any residual violations(audit log)
- Write `check_sole_mutator.py` lint script
- Wire into `run_all.py`(7th lint)
- Write `test_sole_mutator_lint.py` unit test
- Run all tests + 6+1 V2 lints green
- Update progress.md Day 2 entry + commit

### Day 3 — AD-Hitl-7 (~4-5 hr)

- DB schema design + Alembic 0013_hitl_policies + RLS policy
- ORM model `HitlPolicyRow`
- ABC `HITLPolicyStore`
- Default impl `DBHITLPolicyStore`
- DefaultHITLManager `__init__` + `get_policy` wiring
- ServiceFactory wiring
- Unit + integration tests (2 tenants)
- Run alembic upgrade + downgrade verification
- Update progress.md Day 3 entry + commit

### Day 4 — Retrospective + Closeout (~1 hr)

- Write `retrospective.md`(6 必答 Q1-Q6)
- Verify all 6 ADs closed (acceptance criteria checklist)
- Run pytest + mypy + 7 V2 lints + LLM SDK leak check
- Calibration ratio compute(actual / committed)
- Drift findings final catalog(D1 + new from Day 1-3)
- Update SITUATION-V2-SESSION-START.md §8 (close 6 AD;add new AD if any)
- Push branch
- Open PR with 6 AD closure summary
- Watch CI green
- Merge after CI green

---

## File Change List

### New Files (5)
- `backend/scripts/lint/check_sole_mutator.py`
- `backend/src/agent_harness/observability/helpers.py`
- `backend/src/platform_layer/governance/hitl/policy_store.py`
- `backend/alembic/versions/0013_hitl_policies.py`
- 7 test files(see per-AD spec)

### Edit Files (10)
- `.claude/rules/sprint-workflow.md`(AD-Plan-1 + AD-Lint-2)
- `.claude/rules/file-header-convention.md`(AD-Lint-3)
- `backend/scripts/lint/run_all.py`(7th lint wiring)
- `backend/src/agent_harness/verification/_obs.py`(refactor;Option A/B Day 1)
- `backend/src/agent_harness/verification/rules_based.py`(import path)
- `backend/src/agent_harness/verification/llm_judge.py`(import path)
- `backend/src/business_domain/_obs.py`(refactor;Option A/B Day 1)
- `backend/src/business_domain/_base.py`(import path)
- `backend/src/agent_harness/hitl/_abc.py`(add HITLPolicyStore ABC)
- `backend/src/infrastructure/db/models/governance.py`(add HitlPolicyRow)
- `backend/src/platform_layer/governance/hitl/manager.py`(__init__ + get_policy)
- `backend/src/platform_layer/governance/service_factory.py`(DBHITLPolicyStore wiring)
- `claudedocs/6-ai-assistant/prompts/SITUATION-V2-SESSION-START.md`(Day 4 close 6 AD)

---

## Dependencies & Risks

### Dependencies

- **Internal**:
  - AD-Cat12-Helpers-1 should land before any future Cat 11 obs (55.5);no current dep
  - AD-Hitl-7 needs Alembic CLI + asyncpg working(verified working 0012 via 55.1)
  - AD-Cat7-1 lint depends on `run_all.py` infrastructure(53.7)
- **External**:None

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **R1**(AD-Cat7-1 殘餘違規)| Low | Low | Day 2 verify grep-zero;若有違規則 catalog + 修補(可能增加 ~30 min)|
| **R2**(AD-Hitl-7 Alembic conflict)| Low | Med | reuse 0012 RLS pattern;Day 3 上午先 dry-run upgrade head + downgrade base |
| **R3**(AD-Cat12-Helpers-1 refactor breaks Cat 9 wrappers)| Low | Low | per 54.2 D19,Cat 9 wrappers reuse inner judge tracer 不動;refactor 範圍限於 verification + business_domain |
| **R4**(Calibration ratio outside band 2nd time)| Med | Low | scope 已輕量設計;若 ratio < 0.85,55.4 plan multiplier 0.35;若 ratio > 1.20 → 探討 AD scope underestimation |
| **R5**(Group A edit conflicts in concurrent rule files)| Low | Low | sequential commits in Day 1 morning;no parallel writes |

### Drift Findings (Day-0 探勘 — AD-Plan-1 first self-application)

- **D1** AD-Cat7-1 scope smaller than originally specified(grep-zero 大部分達成;scope 收斂為 enforcement + lint)
- **D2** AD-Cat12-Helpers-1 是 extract(non-create);`business_domain/_obs.py` 同 pattern → 可一併 refactor
- **D3** AD-Hitl-7 baseline confirmed `default_policy` in-memory only;DB persistence 是新增層

→ Day 1+ 預期再加 D4-Dn drift findings(catalog in progress.md;non-disruptive — preserves audit trail per AD-Plan-1)

---

## Workload

```
Bottom-up est:    ~10-12.5 hr
                  = AD-Plan-1 0.5 + AD-Lint-2 0.5 + AD-Lint-3 0.5
                  + AD-Cat7-1 3-4 + AD-Hitl-7 4-5 + AD-Cat12-Helpers-1 1.5-2

Calibrated commit: ~10 × 0.40 = ~4 hr
Multiplier: 0.40 (2nd application; 55.2 1st = 1.10 in band)
```

**Day 4 retrospective Q2 must verify**:
- Compute `actual_total_hr / committed_total_hr` ratio
- If ∈ [0.85, 1.20] → 0.40 confirmed stable for Phase 56+ baseline
- If outside band → AD-Phase56-Calibration triggers re-baseline (55.4 plan multiplier adjust)

---

## Out of Scope

| Item | Why Out | Where |
|------|---------|-------|
| Group B (Cat 8: AD-Cat8-1/2/3) | bottom-up ~5-7 hr;separate calibration cycle | → Sprint 55.4 |
| Group C (Cat 9: AD-Cat9-5/6) | 1 hr each;couple with Cat 8 batch | → Sprint 55.4 |
| AD-Cat9-1-WireDetectors | operator-driven non-sprint | → ops runbook |
| Group D (Cat 10: AD-Cat10-Wire-1, Obs-Cat9Wrappers) | depends on chat router obs strategy | → Sprint 55.5 |
| Group E (Cat 11: AD-Cat11-Multiturn/SSEEvents/ParentCtx) | bottom-up ~6-8 hr large;needs dedicated sprint | → Sprint 55.5 |
| Group F (Cat 10 Frontend: VisualVerifier, Frontend-Panel) | frontend-only;separate calibration | → Sprint 55.6 |
| Group H (#31, AD-CI-5, AD-CI-6) | infra track, no sprint binding | → infra track |
| Phase 56+ scope (SaaS Stage 1) | needs user approval first | → Phase 56+ |

---

## AD Carryover Sub-Scope

If 55.3 hits time-box pressure,**rolling carryover** priority order(largest to smallest):

1. AD-Hitl-7 Day 3 → 55.4 (most isolatable;DB schema + tests)
2. AD-Cat7-1 Day 2 → 55.4 (lint script;non-blocking for Cat 8/9)
3. AD-Cat12-Helpers-1 → 55.5 (cross-Cat helper;non-blocking)
4. Group A doc updates → 55.4 next morning(low overhead)

> **Note**: Carryover should be exception, not rule. 55.3 calibration validation depends on closing all 6 ADs.

---

## Definition of Done

- ☐ All 6 ADs closed per acceptance criteria
- ☐ Tests added ≥+12 (cumulative 1416 → ≥1428)
- ☐ 7 V2 lints green (6 existing + new check_sole_mutator)
- ☐ pytest unit + integration green
- ☐ mypy --strict 0 errors
- ☐ LLM SDK leak 0 (CI enforced)
- ☐ black + isort + flake8 green
- ☐ Alembic upgrade head + downgrade base verified (0013)
- ☐ Calibration ratio computed in retro Q2
- ☐ Drift findings catalogued (D1-Dn)
- ☐ retrospective.md with 6 必答 Q1-Q6
- ☐ SITUATION-V2-SESSION-START.md §8 updated (close 6 AD; add new AD if any)
- ☐ PR opened + CI green + merged to main

---

## References

- **`SITUATION-V2-SESSION-START.md`** §8 Open Items(source of 6 ADs)
- **`.claude/rules/sprint-workflow.md`**(target of AD-Plan-1 + AD-Lint-2 edits)
- **`.claude/rules/file-header-convention.md`**(target of AD-Lint-3 edit)
- **`docs/03-implementation/agent-harness-planning/01-eleven-categories-spec.md`** §範疇 7 / §範疇 12 / §HITL Centralization
- **`docs/03-implementation/agent-harness-planning/17-cross-category-interfaces.md`** §5 HITLManager / §Contract 12 Tracer
- **`docs/03-implementation/agent-harness-planning/09-db-schema-design.md`** §approvals(reuse pattern for hitl_policies)
- **`.claude/rules/multi-tenant-data.md`** §Rule 1 (RLS for hitl_policies)
- **`.claude/rules/testing.md`** §Module-level Singleton Reset Pattern(autouse fixture for HITLManager test)
- **Sprint 53.4 plan + retrospective** — origin of AD-Hitl-7
- **Sprint 53.1 retrospective** — origin of AD-Cat7-1
- **Sprint 53.7 retrospective** — origin of AD-Plan-1 / AD-Lint-2
- **Sprint 54.2 retrospective** — origin of AD-Lint-3 / AD-Cat12-Helpers-1
- **Sprint 55.2 plan + checklist** — format template (13 sections / Day 0-4)

---

**Status**: Day 0 — pending user approval before Day 1 code starts.
