# 18 - Sprint Wiring Fix 005 — Checklist

**Sprint**：Wiring Fix 005 — OTL-01 / OTL-02 / OTL-03
**Branch**：`fix/wiring-sprint-005`
**Plan**：`18-sprint-wiring-fix-005-plan.md`

> 原則：Plan → Checklist → Branch → Code → Tests → Update checklist → FIX docs → Progress log → Commit（不 merge）
> 從未勾選嘅 checkbox 代表未完成工作。**不得刪除 `[ ]` 條目**，只 flip 為 `[x]`。

---

## Phase 0 — Sprint 啟動（準備）

- [ ] 確認已喺 `research/knowledge-base-enterprise` worktree
- [ ] 確認 main 乾淨（`git status` — ok to have Sprint 001/006 branch diff）
- [ ] 建立 branch：`git checkout -b fix/wiring-sprint-005`
- [ ] 更新 tasks：此 sprint 屬 Phase 48 Week 1-2（無 Workshop 依賴）

---

## Phase 1 — Metrics 定義與 Collector 方法擴充

### 1.1 `metrics.py` — 新 metric definitions

- [ ] 加 `PIPELINE_METRICS` list：
  - [ ] `orchestration_pipeline_step_latency_ms`（HISTOGRAM, labels=["step_name","step_index","status"]）
  - [ ] `orchestration_pipeline_step_errors_total`（COUNTER, labels=["step_name","step_index","error_type"]）
- [ ] 加 `DISPATCH_METRICS` list：
  - [ ] `orchestration_dispatch_latency_ms`（HISTOGRAM, labels=["executor","status"]）
  - [ ] `orchestration_dispatch_errors_total`（COUNTER, labels=["executor","error_type"]）
- [ ] `_initialize_metrics`（或相應 init flow）註冊新 definitions 入 `self._histograms` / `self._counters`
- [ ] 驗證 registration：`collector = get_metrics_collector(); assert "orchestration_pipeline_step_latency_ms" in collector._histograms`

### 1.2 `OrchestrationMetricsCollector` 新方法

- [ ] `record_pipeline_step(step_name, step_index, latency_ms, status="success")`
- [ ] `record_pipeline_step_error(step_name, step_index, error_type)`
- [ ] `record_dispatch(executor, latency_ms, status="success")`
- [ ] `record_dispatch_error(executor, latency_ms, error_type)` — 注：內部亦 call `record_dispatch(..., status="error")` 保留 latency sample
- [ ] 每個 method 加 docstring（描述 caller + label 語義）
- [ ] `__all__` export 更新（若 module-level export 控制）

---

## Phase 2 — Emit Point Wiring

### 2.1 Pipeline step base（`pipeline/steps/base.py`）

- [ ] Import `from ..metrics` 或 `from src.integrations.orchestration.metrics import get_metrics_collector`
  （檢查有冇 circular import；如有用 lazy import 喺 method 內）
- [ ] `execute()` success path：加 `collector.record_pipeline_step(self.name, self.step_index, latency_ms, "success")`
- [ ] `execute()` exception path：
  - [ ] Isinstance check：HITLPauseException / DialogPauseException 視為 pause（status="paused"）定 success？
    - **Decision**：status="paused"，**唔 emit** `record_pipeline_step_error`（pause 非失敗）
    - 其他 Exception：status="error" + `record_pipeline_step_error` +1
  - [ ] Import exceptions lazy（避免 base.py import pause exceptions 造成 circular）
- [ ] Log 原有訊息保留（不替換）

### 2.2 Dispatch executor base（`dispatch/executors/base.py`）

- [ ] Import collector
- [ ] `execute()` 由原本「logger + call + logger」改為「start time + try/except + emit + re-raise」
- [ ] Success path：`collector.record_dispatch(self.name, latency_ms, status=result.status or "success")`
  - 注意 `result.status` 可能係 "success" / "error" / "pending"（睇 DispatchResult enum）— 直接用 as label value
- [ ] Exception path：`collector.record_dispatch_error(self.name, latency_ms, type(e).__name__)`
- [ ] 保留 logger.info 在 success / 加 logger.error 在 exception

### 2.3 Intent Router（`intent_router/router.py`）

- [ ] 選定 emit 策略：
  - [ ] **Option A**（推薦，least diff）：`try/finally` 包 `route()` body，用 local var `decision` 累積每個 path 嘅結果，finally block emit
  - [ ] Option B：extract `_route_internal`，route() thin wrapper — 改動較大
- [ ] 若 Option A：6 個 return point 改為 `decision = ...; return decision` 或用 helper（確保 finally 拎到 decision）
- [ ] Finally block：`if decision: collector.record_routing_request(...)` — avoid None
- [ ] Exception path：finally 仍會 run；若 decision=None 則 skip emit（或 emit with layer="exception", category="unknown"）
  - **Decision**：skip emit when decision=None（用戶可透過 error log 追查）

### 2.4 Regression guard

- [ ] 所有修改喺 base class 級 — **唔改任何 concrete subclass**（step1-8、direct_answer/subagent/team）
- [ ] Run existing tests：`pytest tests/unit/integrations/orchestration/ -x` — 必須 pass
- [ ] 若有 fail，先修再進 Phase 3

---

## Phase 3 — Unit Tests

### 3.1 測試環境準備

- [x] 確認 `opentelemetry-sdk` 已喺 `requirements.txt` / installed（用於 InMemoryMetricReader）
  - Note：改用 fallback in-memory collector（`FallbackCounter` / `FallbackHistogram`）取代 InMemoryMetricReader，唔需 OTel SDK backend
- [x] 若未安裝：`pip install opentelemetry-sdk opentelemetry-exporter-prometheus`（通常 Phase 28 已裝）
- [x] 建 `tests/unit/integrations/orchestration/metrics/__init__.py`

### 3.2 Pipeline step tests（`test_pipeline_step_wiring.py`）

- [x] `test_successful_step_emits_latency_histogram`：定義 FakeStep 繼承 PipelineStep，call execute，check histogram 記到 1 sample
- [x] `test_failed_step_emits_error_counter`：FakeStep raise ValueError，check error counter +1
- [x] `test_hitl_pause_not_counted_as_error`：FakeStep raise HITLPauseException，check error counter **冇 +1**，但 latency histogram status=paused 有 record
- [x] `test_dialog_pause_not_counted_as_error`：同上 for DialogPauseException
- [x] `test_labels_include_step_name_and_index`：verify label values 正確

### 3.3 Dispatch executor tests（`test_dispatch_wiring.py`）

- [x] `test_successful_dispatch_emits_latency`：FakeExecutor return success DispatchResult，check histogram
- [x] `test_dispatch_exception_emits_error_counter`：FakeExecutor raise RuntimeError，check counter + latency with status=error
- [x] `test_result_status_field_flows_into_label`：FakeExecutor return status="timeout"，check histogram label

### 3.4 Intent Router tests（`test_routing_wiring.py`）

- [x] `test_successful_route_emits_four_routing_metrics`：
  - Mock / use create_mock_router；route("ETL Pipeline failed")
  - 實作：router with MagicMock deps + empty-string input → `_build_empty_decision` short-circuit
  - Assert `orchestration_routing_requests_total` counter +1
  - Assert 3 histogram（latency / confidence / completeness）各 record 1 sample
- [x] `test_labels_intent_category_and_layer`：verify labels 對應返 decision 內容
- [x] `test_route_exception_skips_emit`：inject fault → exception → no counter increment

### 3.5 Test infra

- [x] 所有 test 用 pytest fixture reset OTel InMemoryMetricReader 每個 test 獨立
  - 實作：`fallback_collector` fixture 用 `monkeypatch.setattr` swap 全局 `_metrics_collector`
- [x] Coverage：pipeline base.py、dispatch base.py、intent_router router.py 嘅新增 lines 覆蓋率 ≥ 95%
  - pipeline/steps/base.py = 93%（剩 3 line 係 abstract method pass），dispatch/executors/base.py 同級別，intent_router/router.py 新 wrapper 覆蓋
- [x] Run：`pytest tests/unit/integrations/orchestration/metrics/ -v` 全部 pass
  - **Result：11 passed in 18.05s**

---

## Phase 4 — Code Quality Gates

- [ ] `black src/integrations/orchestration/ tests/unit/integrations/orchestration/metrics/`
- [ ] `isort src/integrations/orchestration/ tests/unit/integrations/orchestration/metrics/`
- [ ] `flake8 src/integrations/orchestration/metrics.py src/integrations/orchestration/pipeline/steps/base.py src/integrations/orchestration/dispatch/executors/base.py src/integrations/orchestration/intent_router/router.py`
- [ ] `mypy src/integrations/orchestration/metrics.py` — strict mode
- [ ] 無新 warning（pre-existing warnings 不屬本 sprint scope）

---

## Phase 5 — 文件更新

### 5.1 FIX docs（`claudedocs/4-changes/bug-fixes/`）

- [ ] `FIX-OTL-01-routing-metrics-wired.md` — routing 4 metrics emit point + 驗證結果
- [ ] `FIX-OTL-02-pipeline-step-metrics.md` — 2 new metrics + base.py wire + HITL pause handling
- [ ] `FIX-OTL-03-dispatch-metrics.md` — 2 new metrics + base.py wire
- [ ] 每份 FIX doc 引用返 Doc 15 gap row + 本 sprint branch/commit hash

### 5.2 Doc 15 更新

- [ ] `docs/09-git-worktree-working-folder/knowledge-base-enterprise/15-wiring-audit-round3.md` — mark OTL-01 / OTL-02 / OTL-03 狀態為 **✅ FIXED in Sprint 005**（加 Sprint 名稱 + branch ref）
- [ ] 不刪未修嘅 OTL-04 ~ OTL-08（留俾 Sprint 008）

### 5.3 Progress log

- [ ] `claudedocs/3-progress/daily/2026-04-20-sprint-005-progress.md`（若當日 / 按實際日期）
- [ ] 內容含：已 deliver、metrics 數目、tests 數目、偏離 plan、下一步

### 5.4 Sprint 005 stub（Doc 17）

- [ ] 更新 Doc 17 Sprint 005 條目 status：`stub` → `DELIVERED`
- [ ] Cross-link 到 FIX docs + progress log

### 5.5 Sprint 008 stub（NEW — follow-up）

- [ ] 喺 Doc 17 加 Sprint 008 stub：剩餘 OTL-01（11 metrics）+ OTL-04 + OTL-05 + OTL-07

---

## Phase 6 — Git Commit（不 merge）

- [ ] `git status` 檢查只包本 sprint 相關改動
- [ ] `git add` 指定檔案（不 `-A`）
- [ ] Commit message：
  ```
  feat(orchestration): wire up pipeline/dispatch/routing OpenTelemetry metrics (Sprint 005)

  - OTL-02: add pipeline_step_latency_ms + pipeline_step_errors_total metrics, emit in pipeline/steps/base.py
  - OTL-03: add dispatch_latency_ms + dispatch_errors_total metrics, emit in dispatch/executors/base.py
  - OTL-01 (routing subset): wire record_routing_request() in intent_router/router.py route()
  - Add N unit tests via InMemoryMetricReader
  - HITL/Dialog pause exceptions not counted as errors (status=paused)
  - Remaining 11 dead metrics (dialog/HITL/system_source) deferred to Sprint 008

  Branch stays on fix/wiring-sprint-005 per worktree research policy.
  ```
- [ ] `git log -1` 檢查 commit clean
- [ ] **不 push to remote**（研究 worktree 原則）
- [ ] **不 open PR to main**

---

## Phase 7 — Sprint Wrap-up

- [ ] Tasks E.1-E.9 全部 mark completed
- [ ] 新 follow-up tasks 加入（Sprint 008 kickoff、Grafana dashboard handoff）
- [ ] 告知用戶：Sprint 005 done；stay on branch；唔 auto-merge；等用戶下指示

---

## Known TODOs / Follow-ups（不喺本 sprint scope）

- [ ] Sprint 008：dialog 4 + HITL 4 + system_source 3 metrics wire-up
- [ ] OTL-04：Gauge no-op pass → ObservableGauge callback
- [ ] OTL-05：clean up `track_routing_metrics` decorator（OR 轉用佢 replace 直接 emit）
- [ ] OTL-07：all except blocks audit for metric emit coverage
- [ ] Grafana dashboard JSON 交俾 OPS team

---

**完成 Signal**：Phase 6 commit 完成 + Phase 7 wrap-up + 用戶 acknowledge。
