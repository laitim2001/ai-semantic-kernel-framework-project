# Sprint 57.2 — Phase 57+ Audit Cycle Lvl 2: Carryover ADs Closure + 11+1 範疇 Alignment Final Check

> **Sprint Type**: Audit Cycle Mini-Sprint **Lvl 2** — 集中處理 5 條 high-ROI Phase 53-56 carryover ADs + 1 light-touch 11+1 範疇 vs 規劃文件 alignment audit；**NOT main progress**；V2 22/22 + Phase 56-58 SaaS Stage 1 3/3 + Phase 57+ Frontend 1/N **unchanged** (carryover bundle pattern per 53.2.5 / 53.7 / 55.3-55.6 precedent)
> **Owner Categories**: Cross-cutting (範疇 8 retry / 9 detectors / 10 verification / 11 subagent / 12 obs metrics + Cat 8b business cost ledger + CI infra + 11+1 範疇 alignment)
> **Phase**: 57 (Audit Cycle bundle, between Sprint 57.1 main progress and Phase 57+ next main-progress sprint TBD)
> **Workload**: 5 days (Day 0-4); bottom-up est ~25-30 hr → calibrated commit **~14-17 hr** (multiplier **0.55** per AD-Sprint-Plan-4 `large multi-domain` 3rd application — 56.1=1.00 + 56.3=1.04 in band, 2-data-point mean 1.02 → KEEP 0.55；若此 sprint ratio ∈ [0.85, 1.20] band → 3-data-point window opens 視為 stable)
> **Branch**: `feature/sprint-57-2-audit-cycle-carryover`
> **Plan Authority**: This document (per CLAUDE.md §Sprint Execution Workflow)
> **Roadmap Source**: 56.3 retrospective Q5 carryover ADs (3 條: AD-Cost-Ledger-Token-Split + AD-Cost-Ledger-Provider-Attribution + AD-Cat10-Cat11-LoopMetricsAccumulator) + 54.1 deferred AD (AD-Cat9-1-WireDetectors) + 55.6 deferred AD (AD-CI-6 deploy-production re-enable) + Sprint 57.1 retrospective Q5 candidate + user approval 2026-05-06 session
> **AD logging (sub-scope)**: 5 candidate ADs to close + 1 process AD candidate (若 11+1 alignment audit detect drift > 3 條 → log AD-Cat-Alignment-Drift-1) + AD-Sprint-Plan-4 `large multi-domain` 3rd application calibration verify

---

## Sprint Goal

集中處理 5 條 high-ROI carryover ADs（估 12-15 hr bottom-up）+ 1 light-touch 11+1 範疇 alignment audit（估 3-5 hr bottom-up）= bundle 14-17 hr commit。**Audit-cycle scope** — V2 22/22 + Phase 56-58 + Phase 57+ 1/N 主進度數字不變。

- **US-1**: Cost Ledger 精度提升 — close **AD-Cost-Ledger-Token-Split** + **AD-Cost-Ledger-Provider-Attribution**（56.3 carryover bundle 同 code path）；input/output token 分開記錄（取代 56.3 D2 single-entry combined）+ 真實讀取 ChatResponse provider/model attribute 取代 default `azure_openai/gpt-5.4` 估算
- **US-2**: Cat 10 + Cat 11 LoopMetrics 精度 — close **AD-Cat10-Cat11-LoopMetricsAccumulator**（56.3 carryover）；取代 SLAMetricRecorder last-event proxy（56.3 用 LoopCompleted.total_turns / total_tokens last-event 估算）為 proper accumulator pattern（Cat 10 verification iterations + Cat 11 subagent dispatched count）
- **US-3**: Cat 9 detector wiring Stage 1 — close **AD-Cat9-1-WireDetectors**（54.1 deferred）；4 detectors（PIIDetector / JailbreakDetector / SecretsLeakDetector / RoleConfusionDetector）從 Stage 0 advisory（audit log only）→ Stage 1 active gate（Loop pre-tool boundary block）
- **US-4**: CI deploy production 啟用 — close **AD-CI-6**（55.6）；deploy-production.yml 從 `workflow_dispatch only` → 5-point criteria 達成 push-to-main trigger 啟用（5 active CI checks 全 stable / staging-smoke pass / branch protection enforce_admins=true / production runner 配置 / rollback playbook）
- **US-5**: 11+1 範疇 alignment audit + closeout — light-touch grep across `backend/src/agent_harness/<範疇>/` vs 對應 V2 規劃文件 `01-eleven-categories-spec.md` 章節；catalogue drift（spec claims X but code does Y）為 D-findings；若 drift > 3 條 → log AD-Cat-Alignment-Drift-1 process AD；retrospective + `large multi-domain` 0.55 3rd app calibration verify + cumulative cross-class window stats + Phase 57+ next-sprint candidates Q5（不寫 plan task detail 紀律）

Sprint 結束後：
- (a) **Cost Ledger 精度** 滿足 GDPR / billing 級別 — input/output token 各別欄位 + provider 真實值非 default
- (b) **SLA reports** 不再被 last-event proxy 估算誤差影響 — 真實 turn / token cumulative across loop
- (c) **Cat 9 主流量保護** 從 advisory（Stage 0 audit log）→ active pre-tool gate（Stage 1 block）
- (d) **deploy-production.yml 啟用** — push-to-main automated production deployment 上線（5-point criteria 已 Phase 56.x + 57.1 累積達成）
- (e) **11+1 範疇 vs 規劃文件 alignment** 已 audit；若有 drift catalogued for 後續 audit cycle 處理（不在此 sprint 修）
- (f) **`large multi-domain` 0.55 multiplier 3-data-point window opens**（56.1=1.00 + 56.3=1.04 + 57.2=TBD）若 in band → 視為 stable, KEEP；若 outside → AD-Sprint-Plan-N+1 logged

**主流量驗收標準**：
- Cost Ledger entries 顯示 `input_tokens` / `output_tokens` 各別欄位 + `provider` 真實值（非 default `azure_openai`）
- SLA report `total_turns` / `total_tokens` 為 sum-across-loop accumulated（用 LoopMetricsAccumulator）非 last-event proxy
- Loop pre-tool boundary 觸發 Cat 9 detectors；若 PII / jailbreak detected → tool call 被擋 + GuardrailTriggered SSE event + audit log entry
- Push to main → `deploy-production.yml` 自動觸發（staging → smoke test → production）
- 11+1 範疇 alignment audit 結果 catalogued in retrospective Q3；drift list 提供
- pytest baseline 1557 → **≥ 1567**（+10 minimum）
- 8 V2 lints 8/8 green
- mypy --strict 0 errors / 293+ source files
- LLM SDK leak 0

---

## Background

### V2 進度

- **22/22 sprints (100%) main progress completed** + **Phase 56-58 SaaS Stage 1 3/3 ✅ CLOSED** + **Phase 57+ Frontend SaaS 1/N opened**（Sprint 57.1 v2 ✅ 2026-05-06）
- **Audit-cycle CLAUDE.md V1/MAF cleanup** ✅ 完成（PR #105 merged `96716a1a` 2026-05-06）— V1/MAF 過時敘述清零；V2 docs 數量 17/19 → 21；rule table refresh
- main HEAD: `96716a1a` — Day 0 verified
- pytest baseline 1557 / mypy --strict 0/293 source files / 8 V2 lints 8/8 green
- 12-sprint window 8/12 (67%) sustained ≥ 60% threshold for 3rd consecutive sprint（53.7=1.01 / 55.2=1.10 / 55.5=1.14 / 55.6=0.92 / 56.1=1.00 / 56.2=1.17 / 56.3=1.04 / 57.1=0.85）
- **本 sprint = Phase 57+ Audit Cycle Lvl 2**（user-approved 2026-05-06 session — 集中處理 5 條 carryover ADs + 11+1 alignment audit；不算入主 progress）

### 為什麼 audit cycle 而非繼續 Phase 57+ frontend / backend main progress

User approved 2026-05-06 session（取代繼續 Tenant Settings / Admin console / Onboarding 重設計）：

1. **5 條 high-ROI ADs 累積已成 cluster** — 56.3 retrospective 留 3 條（Token-Split / Provider-Attribution / LoopMetricsAccumulator）+ 54.1 留 1（Cat9-WireDetectors）+ 55.6 留 1（CI-6 deploy）；繼續累積會讓 future sprint plan 受牽引（每個 frontend sprint 都要先處理 backend cost ledger 精度問題）
2. **`large multi-domain` 0.55 multiplier 需 3rd data point** 確認 stable — 56.1 + 56.3 都 in band；3rd 確認後可信度大幅提升；audit cycle scope 落該 class 區間
3. **11+1 範疇 alignment final check 應在 V2 22/22 closure 後做一次** — 確認 spec vs code 無 silent drift；過去每 sprint 內 retrospective check own 範疇，但 cross-範疇 systemic check 從未做過
4. **Cat 9 detector Stage 1 wiring 是阻塞性** — Phase 57+ frontend 沒有 backend Cat 9 active gate 保護;若未來有外部 user 流入,advisory mode 不夠
5. **Cost Ledger 精度是 billing critical** — 即將進入 SaaS Stage 2 Stripe 整合,token-split + provider attribution 是 billing accurate 的前提
6. **deploy-production.yml 啟用是 production gate** — 5 個 5-point criteria 已 56.4-57.1 期間累積達成,僅缺 sprint 來執行最後 wiring

### 既有結構（Day 0 探勘 三-prong grep 將驗證以下假設）

⚠️ **以下 assumptions 是 plan-time 推斷**；Day 0 grep（per sprint-workflow.md §Step 2.5 Prong 1 Path Verify + Prong 2 Content Verify + Prong 3 Schema Verify）將 confirm 或 catalogue 為 D-finding：

```
backend/src/
├── agent_harness/
│   ├── orchestrator_loop/loop.py          # 主 loop;LoopCompleted event emit point — US-2 改 last-event → accumulator
│   ├── guardrails/                        # Cat 9 detectors;Stage 0 advisory only — US-3 改 Stage 1 active gate
│   │   ├── _abc.py                        # Detector ABC
│   │   ├── pii_detector.py                # ✅ existing
│   │   ├── jailbreak_detector.py          # ✅ existing
│   │   ├── secrets_leak_detector.py       # ✅ existing
│   │   └── role_confusion_detector.py     # ✅ existing
│   └── verification / subagent /          # ✅ existing — US-2 LoopMetricsAccumulator scope
├── business_domain/
│   └── cost_ledger/                       # 56.3 introduced — US-1 改 input/output split + provider truthful
│       ├── service.py                     # CostLedgerService.record_llm_call() — D2 single-entry simplification
│       └── pricing_loader.py              # ✅ existing
├── platform_layer/
│   └── observability/
│       └── sla_metric_recorder.py         # 56.3 — last-event proxy classify_loop_complexity()
└── api/v1/chat/
    └── router.py                          # LoopCompleted observer wires — US-1 + US-2 改 hook source

.github/workflows/
└── deploy-production.yml                  # 55.6 introduced workflow_dispatch only — US-4 改 push-to-main trigger
```

---

## User Stories

### US-1：Cost Ledger 精度提升（AD-Cost-Ledger-Token-Split + AD-Cost-Ledger-Provider-Attribution）

**As a** SaaS billing operator
**I want** cost ledger entries 顯示 input/output token 分開 + 真實 provider/model attribution
**So that** 即將推進 Stripe 整合時 billing 數字 production-grade（不是 default azure_openai/gpt-5.4 估算）

**Acceptance**:
- `cost_ledger` table 新增 `input_tokens` / `output_tokens` 兩欄（取代或補入 `total_tokens`）
- `CostLedgerService.record_llm_call()` 從 ChatResponse 讀取 `usage.prompt_tokens` / `usage.completion_tokens` 各別記錄
- `provider` / `model` 從 ChatResponse 真實 attribute 讀取（非 default constant）
- Alembic migration 0017（add columns + backfill default 0 / azure_openai）
- 5 unit tests（split accuracy / provider truthful / backwards-compat fallback）
- 1 integration test（chat router → LoopCompleted → CostLedger 真實值）

### US-2：Cat 10 + Cat 11 LoopMetrics 精度（AD-Cat10-Cat11-LoopMetricsAccumulator）

**As a** SLA monitor
**I want** total_turns / total_tokens 是 sum-across-loop accumulated 非 last-event proxy
**So that** SLA report 不被 last-event drop 場景失真（例如 verification correction 多次 turn 但 last event 只 reflect 最後一次）

**Acceptance**:
- 新增 `LoopMetricsAccumulator` class（sum across LoopEvent stream）
- AgentLoop 內注入 accumulator;每個 LLM call / verification / subagent dispatch 累加
- LoopCompleted event payload 改用 accumulator 結果（取代 last-event proxy）
- `classify_loop_complexity()` 仍適用（依 accumulated 值分類）
- 5 unit tests（accumulator correctness / verification correction case / subagent dispatch count）
- 1 integration test（multi-turn loop with verification → SLA report 反映真實 cumulative）

### US-3：Cat 9 detector Stage 1 wiring（AD-Cat9-1-WireDetectors）

**As a** security operator
**I want** 4 detectors（PII / Jailbreak / SecretsLeak / RoleConfusion）在 Loop pre-tool boundary actively block
**So that** 主流量真正受保護（不只 audit log advisory）

**Acceptance**:
- AgentLoop pre-tool 階段 invoke detector chain
- Detected → tool call 被擋 + GuardrailTriggered SSE event 發送 + audit log entry
- Detector severity threshold（per detector configurable;default HIGH 才 block）
- 4 unit tests per detector（Stage 1 block path）+ 4 integration tests（chat router pre-tool block scenario）
- 既有 Stage 0 advisory tests 保持 pass（backwards-compat）

### US-4：CI deploy-production.yml 啟用（AD-CI-6）

**As a** DevOps operator
**I want** push-to-main → 自動 staging → smoke test → production deployment
**So that** Phase 57+ frontend changes 不再依賴 manual workflow_dispatch

**Acceptance**:
- 5-point criteria verify Day 1（5 active CI checks 全 stable / staging-smoke pass historical 30 days / enforce_admins=true confirmed / production runner 配置 / rollback playbook 文件 ≥ 1 page）
- `deploy-production.yml` trigger 改 `on: push: branches: [main]` + `workflow_dispatch:` 雙啟用
- Staging smoke test job 新增（pre-production gate）
- Branch protection 補入 `deploy-production / staging-smoke` 為 required check
- 1 dry-run（push to test branch with deploy override）+ 1 production push verify

### US-5：11+1 範疇 alignment audit + closeout

**As a** V2 architecture custodian
**I want** light-touch grep across agent_harness/<範疇>/ vs 01-eleven-categories-spec.md §category 章節
**So that** spec vs code drift catalogued before Phase 57+ continues（防止 silent drift 累積）

**Acceptance**:
- 12 範疇逐一 grep（主要 ABC class / public API / event names / type definitions）vs spec 章節描述
- D-findings catalogued in retrospective Q3（spec claims X but code does Y）
- 若 drift > 3 條 → log AD-Cat-Alignment-Drift-1 process AD（後續 audit cycle 處理）
- Retrospective Q1-Q5（含 medium-frontend 1st app calibration verify cumulative）
- Phase 57+ next-sprint candidates Q5（不寫 plan task detail；rolling planning 紀律）

---

## Technical Specifications

### US-1 設計重點

```python
# Migration 0017 (input/output token split)
class CostLedger(Base):
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    # total_tokens column 保留（backwards-compat;= input + output）

# Service signature change
async def record_llm_call(
    self,
    *,
    tenant_id: UUID,
    input_tokens: int,           # was: tokens (combined)
    output_tokens: int,          # NEW
    cached_tokens: int = 0,
    provider: str,               # NEW — 真實 ChatResponse.provider (was default "azure_openai")
    model: str,                  # NEW — 真實 ChatResponse.model (was default "gpt-5.4")
    ...
) -> None: ...

# Chat router observer (LoopCompleted)
await cost_ledger.record_llm_call(
    tenant_id=...,
    input_tokens=event.usage.prompt_tokens,        # was: total combined
    output_tokens=event.usage.completion_tokens,
    provider=event.provider,                         # was: hardcoded
    model=event.model,                               # was: hardcoded
)
```

### US-2 設計重點

```python
# New accumulator
@dataclass
class LoopMetricsAccumulator:
    total_turns: int = 0
    total_tokens: int = 0
    verification_iterations: int = 0
    subagent_dispatched: int = 0
    cumulative_input_tokens: int = 0
    cumulative_output_tokens: int = 0

    def on_event(self, event: LoopEvent) -> None:
        # Accumulate based on event type
        ...

# AgentLoop
class AgentLoop:
    def __init__(self, ...):
        self._metrics = LoopMetricsAccumulator()

    async def run(self, ...):
        async for event in ...:
            self._metrics.on_event(event)
            yield event
        # Final emission uses accumulated, not last-event:
        yield LoopCompleted(
            total_turns=self._metrics.total_turns,
            total_tokens=self._metrics.total_tokens,
            ...
        )
```

### US-3 設計重點

```python
# In AgentLoop.run() before tool execution
for tool_call in response.tool_calls:
    # Stage 1 active gate (was: Stage 0 audit log only)
    detector_results = await self.guardrail_engine.check_pre_tool(
        tool_call=tool_call,
        state=state,
    )
    if any(r.severity == Severity.HIGH and r.blocked for r in detector_results):
        # Block + SSE event + audit log
        yield GuardrailTriggered(detector_name=..., severity=...)
        await audit_log.append(...)
        continue  # skip this tool_call
    # else: execute as before
    result = await self.tool_executor.execute(tool_call)
```

### US-4 設計重點

```yaml
# .github/workflows/deploy-production.yml
on:
  push:
    branches: [main]              # NEW
  workflow_dispatch:              # KEEP for manual override

jobs:
  staging-smoke:                  # NEW pre-production gate
    runs-on: production-runner
    steps:
      - run: ./scripts/deploy-staging.sh
      - run: ./scripts/smoke-test.sh
  deploy:
    needs: staging-smoke
    runs-on: production-runner
    steps:
      - run: ./scripts/deploy-production.sh
```

### US-5 設計重點

```bash
# Light-touch grep audit (Day 4)
for cat in 1 2 3 4 5 6 7 8 9 10 11 12; do
    spec_file="docs/.../01-eleven-categories-spec.md"
    code_dir="backend/src/agent_harness/<cat-dir>/"
    # 1. Extract spec claims (公開 ABC / event names / type names)
    # 2. Grep code dir for actual definitions
    # 3. Diff and catalogue mismatches
done
```

---

## Acceptance Criteria

### 量化目標

- pytest 1557 → **≥ 1567**（+10 minimum；US-1 +6 / US-2 +6 / US-3 +8 / US-4 +2 / US-5 +0 = ~22 expected, conservative target +10）
- Cost Ledger entries（after US-1）:`input_tokens` 非 0 AND `output_tokens` 非 0 AND `provider` 與 ChatResponse 一致
- SLA report（after US-2）:`total_turns` / `total_tokens` ≥ last-event proxy（accumulator 應 ≥ proxy）
- Cat 9 pre-tool gate（after US-3）:GuardrailTriggered SSE event 出現於 PII / jailbreak test fixtures
- deploy-production.yml（after US-4）:test branch dry-run pass + 1 production push verify
- 11+1 alignment audit（after US-5）:12 範疇 grep 完成 + D-findings catalogued
- 8 V2 lints 8/8 green
- mypy --strict 0 errors
- LLM SDK leak 0

### 質化目標

- 每個 US 對應 acceptance 全 verifiable command
- D-findings catalogued in progress.md Day 0（per AD-Plan-1）+ retrospective Q3
- Calibration ratio computed Day 4（actual sum vs committed 14-17 hr）

---

## Day-by-Day Plan

### Day 0：探勘 + 三-prong plan-vs-repo verify（~3 hr）

- 三-prong grep（Path Verify + Content Verify + Schema Verify）against plan §既有結構 + §Technical Specifications
- D1-Dn catalogue in progress.md Day 0
- AD-Plan-4-Schema-Grep prong 3 確認 cost_ledger schema 與 plan 假設一致（input_tokens / output_tokens 欄位是否已存在？）
- Branch create `feature/sprint-57-2-audit-cycle-carryover`
- Decide go/no-go（若 drift > 50% scope shift → abort + redraft）

### Day 1：US-1 Cost Ledger 精度（~3.5 hr）

- Alembic 0017 migration（input/output token columns + RLS unchanged）
- CostLedgerService.record_llm_call signature + impl
- Chat router observer 改 ChatResponse 真實 attribute
- 5 unit + 1 integration test
- mypy / lint / pytest checkpoint

### Day 2：US-2 LoopMetricsAccumulator（~3.5 hr）

- LoopMetricsAccumulator class 新增
- AgentLoop inject + on_event hook 邏輯
- LoopCompleted event payload 改用 accumulator
- 5 unit + 1 integration test
- mypy / lint / pytest checkpoint

### Day 3：US-3 Cat 9 Stage 1 wiring（~3.5 hr）

- AgentLoop pre-tool detector chain invoke
- GuardrailTriggered SSE event emission
- 4 detector Stage 1 unit tests + 4 integration tests
- Backwards-compat（Stage 0 advisory tests 仍 pass）
- mypy / lint / pytest checkpoint

### Day 4：US-4 + US-5 + closeout（~3 hr）

- US-4：deploy-production.yml trigger 改 + staging-smoke job + branch protection update（~1 hr）
- US-5：12 範疇 alignment grep + D-findings catalogue（~1.5 hr）
- Retrospective Q1-Q5 + calibration verify + Phase 57+ next-sprint candidates Q5（~30 min）
- Closeout：merge + closeout PR + memory snapshot

---

## File Change List

| File | Action | Lines |
|------|--------|-------|
| `backend/src/infrastructure/db/migrations/versions/0017_cost_ledger_token_split.py` | NEW | ~80 |
| `backend/src/business_domain/cost_ledger/service.py` | MODIFY | ~30 |
| `backend/src/api/v1/chat/router.py` | MODIFY | ~15 |
| `backend/src/agent_harness/orchestrator_loop/_metrics.py` | NEW | ~80 |
| `backend/src/agent_harness/orchestrator_loop/loop.py` | MODIFY | ~25 |
| `backend/src/agent_harness/_contracts/events.py` | MODIFY (LoopCompleted payload) | ~10 |
| `backend/src/agent_harness/orchestrator_loop/loop.py` (US-3) | MODIFY (pre-tool gate) | ~30 |
| `backend/src/agent_harness/guardrails/engine.py` | MODIFY (Stage 1 method) | ~20 |
| `.github/workflows/deploy-production.yml` | MODIFY | ~30 |
| `tests/unit/business_domain/cost_ledger/test_token_split.py` | NEW | ~120 |
| `tests/integration/api/test_cost_ledger_provider_truthful.py` | NEW | ~50 |
| `tests/unit/agent_harness/orchestrator_loop/test_metrics_accumulator.py` | NEW | ~120 |
| `tests/integration/agent_harness/test_loop_metrics_e2e.py` | NEW | ~60 |
| `tests/unit/agent_harness/guardrails/test_stage1_block.py` | NEW | ~150 |
| `tests/integration/api/test_chat_pre_tool_block.py` | NEW | ~80 |
| `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-2/progress.md` | NEW | ~150 |
| `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-2/retrospective.md` | NEW | ~100 |

**Total**: ~1170 lines new / ~130 lines modified

---

## Dependencies & Risks

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Day 0 grep 揭露 cost_ledger schema 與 plan 假設不符 | Medium | Medium | AD-Plan-4-Schema-Grep Prong 3 catch；scope re-shape per drift |
| US-2 accumulator 影響 既有 LoopCompleted consumer | Low | High | backwards-compat（payload 補入 accumulator 結果但保留 last-event 欄位）+ regression tests |
| US-3 Stage 1 active gate 引入 false positive 阻擋合法 tool calls | Medium | High | severity threshold conservative（HIGH only block）+ 既有 200-case PII fixture verify |
| US-4 production deployment 觸發 unexpected outage | Medium | Critical | 5-point criteria 嚴格 verify Day 1 + dry-run on test branch first + rollback playbook ready |
| 11+1 alignment audit 揭露大量 drift > 3 條 | Low | Low | log AD-Cat-Alignment-Drift-1 + 後續 audit cycle 處理（不在此 sprint 修） |
| Calibration ratio outside band | Medium | Low | AD-Sprint-Plan-N+1 logged + multiplier 調整 |

### Common Risk Classes（per sprint-workflow.md §Common Risk Classes）

- **Risk Class A (Paths-filter vs required_status_checks)**: 不適用（55.6 已 close 此 class via Option Z）
- **Risk Class B (Cross-platform mypy unused-ignore)**: 適用於 US-1 / US-2 新檔；採 `# type: ignore[X, unused-ignore]` 雙 ignore code pattern
- **Risk Class C (Module-level Singleton)**: 不適用（此 sprint 不引入新 singleton）

---

## Workload

**Bottom-up est ~25-30 hr → calibrated commit ~14-17 hr (multiplier 0.55 `large multi-domain`)**

| Day | Task | Bottom-up | Calibrated |
|-----|------|-----------|------------|
| 0 | 探勘 + 三-prong verify + branch create | ~3 hr | ~1.7 hr |
| 1 | US-1 Cost Ledger 精度 | ~6 hr | ~3.3 hr |
| 2 | US-2 LoopMetricsAccumulator | ~6 hr | ~3.3 hr |
| 3 | US-3 Cat 9 Stage 1 | ~6 hr | ~3.3 hr |
| 4 | US-4 + US-5 + closeout | ~5 hr | ~2.7 hr |
| **Total** | | **~26 hr** | **~14.3 hr** |

---

## Out of Scope

- ❌ AD-Cat10-VisualVerifier（55.5 deferred）— too large for audit cycle；defer to Phase 57+ Group F dedicated sprint
- ❌ AD-Cat10-Frontend-Panel（55.5 deferred）— same reason
- ❌ AD-Cat11-Multiturn / SSEEvents / ParentCtx（54.2 deferred bundle）— ~15-20 hr 太大；defer to dedicated Cat 11 enhancement sprint
- ❌ Onboarding self-serve wizard（57.1 v1 abort 主因）— needs backend self-serve API design first；SaaS Stage 2 scope
- ❌ Tenant Settings / Admin tenant console — Phase 57+ frontend rolling main progress；user 待 decide
- ❌ DR + WAL streaming — Phase 57+ infrastructure；large multi-domain dedicated sprint
- ❌ 修復 11+1 alignment drift（若 audit 揭露）— catalogue only；後續 audit cycle 處理

---

## AD Carryover Sub-Scope

### 5 ADs to close（main goal）

1. **AD-Cost-Ledger-Token-Split**（56.3 carryover）— US-1
2. **AD-Cost-Ledger-Provider-Attribution**（56.3 carryover）— US-1
3. **AD-Cat10-Cat11-LoopMetricsAccumulator**（56.3 carryover）— US-2
4. **AD-Cat9-1-WireDetectors**（54.1 deferred）— US-3
5. **AD-CI-6**（55.6 deferred）— US-4

### 1 process AD candidate

- **AD-Cat-Alignment-Drift-1**（log only if 11+1 audit detect drift > 3 條）— US-5

### Calibration verify

- **AD-Sprint-Plan-4 `large multi-domain` 0.55 3rd application**（56.1=1.00 + 56.3=1.04 → 57.2=TBD）
- 3-data-point window opens（in-band → KEEP；outside → AD-Sprint-Plan-N+1）

---

## Definition of Done

- [ ] 5 carryover ADs all closed（US-1 to US-4 = 5 ADs）
- [ ] US-5 11+1 alignment audit 完成 + D-findings catalogued
- [ ] pytest 1557 → ≥ 1567
- [ ] mypy --strict 0 errors
- [ ] 8 V2 lints 8/8 green
- [ ] LLM SDK leak 0
- [ ] Day 0 三-prong verify D-findings catalogued in progress.md
- [ ] Retrospective Q1-Q5 written
- [ ] Calibration ratio computed + 13-sprint window stats updated
- [ ] PR open + CI green + squash merge to main
- [ ] Closeout PR（CLAUDE.md / SITUATION-V2 sync）+ memory snapshot
- [ ] Phase 57+ next-sprint candidates Q5 列出（不寫 plan task detail）

---

## References

- **CLAUDE.md** §Sprint Execution Workflow / §Phase Roadmap（Phase 56-58 SaaS Stage 1 closure 後 Audit Cycle Lvl 2）
- **sprint-workflow.md** §Step 2.5（三-prong verify 含 Schema Verify Prong 3）/ §Workload Calibration / §Common Risk Classes
- **anti-patterns-checklist.md** AP-3（cross-directory scattering — US-2 accumulator 集中於 orchestrator_loop/）/ AP-9（verification — US-2 之精度提升）
- **17-cross-category-interfaces.md** §Cat 8 retry / §Cat 9 detector chain / §Cat 10 verification / §Cat 11 subagent / §Cat 12 metrics
- **01-eleven-categories-spec.md** §Cat 1-12（US-5 alignment audit baseline）
- **15-saas-readiness.md** §Cost ledger / §SLA monitoring / §billing accuracy
- **Sprint 56.3 retrospective Q5** — 3 條 carryover ADs origin
- **Sprint 54.1 retrospective** — AD-Cat9-1-WireDetectors origin
- **Sprint 55.6 retrospective** — AD-CI-6 origin
- **Sprint 57.1 retrospective Q5** — Phase 57+ candidate scope
- **PR #105**（CLAUDE.md V1/MAF cleanup）— main HEAD baseline `96716a1a`

---

**Plan Status**: DRAFT — pending user final approval before Day 0 execution
**Next Step**: 起草 sprint-57-2-checklist.md（mirror plan structure；5 days × per-task DoD + Verify command）
**Approval Trail**: User approved 2026-05-06 session（Lvl 2 audit cycle 12-18 hr commit `large multi-domain` 0.55）
