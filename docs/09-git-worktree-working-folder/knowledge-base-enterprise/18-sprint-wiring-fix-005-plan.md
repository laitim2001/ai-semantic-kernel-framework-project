# 18 - Sprint Wiring Fix 005 — Plan

**Sprint Name**：Wiring Fix Sprint 005 — OTL-01 / OTL-02 / OTL-03（OpenTelemetry metrics wire-up）
**Sprint Type**：Dead Infrastructure Wire-up Sprint
**預計 Story Points**：5 pts（OTL-02: 2 + OTL-03: 1 + OTL-01: 2，含測試）
**預計時長**：3 天（壓縮版 1-1.5 天可執行）
**分支建議**：`fix/wiring-sprint-005`（從 main 開新 branch）
**依賴**：無（無 Workshop 決策相依）
**前置文件**：Doc 15（Wiring Audit Round 3，§2 OTL-01/02/03/08）、Doc 16（Phase 48 Master Plan）、Doc 17 Sprint 005 stub

---

## 一、Sprint Goal

將**三層 orchestration 執行路徑**（Pipeline Steps / Dispatch Executors / Intent Router）嘅 OpenTelemetry metrics 真正 wire 起，令 live chat request 能 emit latency + error metrics，為後續 Grafana dashboard / SLO 監控打基礎。

**Why this sprint**：
- Doc 15 Round 3 §2 揭發 **15 個 orchestration metrics 全部 dead**（定義齊但零 caller），屬典型 "Dead Infrastructure" 反模式。
- Pipeline + Dispatch 兩層 **連 metric 定義都冇**（OTL-08），等於 observability 真空。
- 本 Sprint 修復後，**任何一條 chat request 都會 emit metrics**，令後續 oncall/debugging 有 data 可查。
- **無 Workshop 依賴**，純 backend，風險低。

---

## 二、User Stories

### Story 1：Pipeline Step 觀測（OTL-02）

**作為** SRE / oncall
**我希望** 每次 pipeline 執行 step1-8 時，每步都 emit `step_latency_ms` 與 `step_error_total` metric
**以便** 我可以喺 Grafana 見到「step3 intent_analysis p95 latency 800ms，step5 HITL 有 3% error rate」，快速定位 bottleneck

**目前行為**（`pipeline/steps/base.py:64-112` `execute()`）：
```python
async def execute(self, context):
    start = time.time()
    try:
        context = await self._execute(context)
        latency_ms = (time.time() - start) * 1000
        context.mark_step_complete(self.name, latency_ms)
        logger.info("completed in %.1fms", latency_ms)
        return context
    except Exception:
        latency_ms = (time.time() - start) * 1000
        logger.error("failed after %.1fms", latency_ms)
        raise
```
**無 metric emit**。Latency 只記落 log 同 context，監控系統睇唔到。

**修復後行為**：
```python
# Success path
collector.record_pipeline_step(step_name, step_index, latency_ms, status="success")

# Failure path (before raise)
collector.record_pipeline_step(step_name, step_index, latency_ms, status="error")
collector.record_pipeline_step_error(step_name, step_index, error_type=type(e).__name__)
```

### Story 2：Dispatch Executor 觀測（OTL-03）

**作為** oncall
**我希望** 每次 dispatch 去 direct_answer / subagent / team executor 時 emit `dispatch_latency_ms` 與 `dispatch_errors_total`
**以便** 我可以比較三條 dispatch route 嘅 performance + 失敗率

**目前行為**（`dispatch/executors/base.py:48-70` `execute()`）：
```python
async def execute(self, request, event_queue=None):
    logger.info("starting ...")
    result = await self._execute(request, event_queue)  # NO TRY/EXCEPT
    logger.info("completed — status=%s, duration=%.1fms", result.status, result.duration_ms)
    return result
```
無 metric emit，亦無 try/except 保護（exception 會 bubble 但唔記 metric）。

**修復後行為**：
```python
start = time.time()
try:
    result = await self._execute(request, event_queue)
    latency_ms = (time.time() - start) * 1000
    collector.record_dispatch(self.name, latency_ms, status=result.status or "success")
    return result
except Exception as e:
    latency_ms = (time.time() - start) * 1000
    collector.record_dispatch_error(self.name, latency_ms, error_type=type(e).__name__)
    raise
```

### Story 3：Intent Router Layer 觀測（OTL-01 routing subset）

**作為** product analyst
**我希望** 每次 `BusinessIntentRouter.route()` 完成時 emit 4 個 routing metrics（requests_total, latency, confidence, completeness_score）
**以便** 我可以追蹤 pattern vs semantic vs LLM 三層 trigger rate + confidence 分佈，評估 router 健康度

**目前行為**（`intent_router/router.py:182` `route()`）：
- 6 個 return point（pattern / semantic / llm / safe_default / none × 2）
- `record_routing_request()` 已定義但零 caller

**修復後行為**：
- 統一喺 route() 出口 emit 一次 `record_routing_request(intent_category, layer_used, latency, confidence, completeness)`
- 用 try/finally 保證成功 + exception path 都有 emit

---

## 三、Scope 明確

### In Scope
- OTL-02：NEW 2 個 pipeline step metrics definitions + `pipeline/steps/base.py` emit（1 處修改 auto-wire 7 個 steps）
- OTL-03：NEW 2 個 dispatch metrics definitions + `dispatch/executors/base.py` emit（1 處修改 auto-wire 3 個 executors）
- OTL-01（routing subset）：Wire 4 個現有 routing metrics（`record_routing_request`）喺 `intent_router/router.py`
- Unit tests via `opentelemetry.sdk.metrics.export.InMemoryMetricReader`

### Out of Scope（延後）
- **OTL-01 剩餘 11 metrics**（dialog 4 + HITL 4 + system_source 3）：留俾 **Sprint 008 / OTL-06**。Dialog metrics 要修 guided_dialog/engine.py、HITL 要修 hitl/controller.py、system_source 要修 input_gateway — 三個不同模組，scope 太闊。
- **OTL-04**（Gauge no-op pass）：🟡 MED，留 Sprint 008
- **OTL-05**（track_routing_metrics decorator 改用）：本 sprint 用直接 emit 路線，decorator 遲啲再清
- **OTL-07**（except block 全部 metric emit）：本 sprint 只做 base class 層 error emit，逐個 except block 檢查延後
- **Grafana dashboard JSON**：本 sprint 只保證 metrics flow，dashboard 由 OPS team 做

---

## 四、Technical Specifications

### 4.1 新 metric definitions（加入 `metrics.py`）

```python
# Pipeline Metrics Definitions（NEW — 補 OTL-08 缺失）
PIPELINE_METRICS = [
    MetricDefinition(
        name="orchestration_pipeline_step_latency_ms",
        description="Pipeline step latency in milliseconds",
        unit="ms",
        metric_type=MetricType.HISTOGRAM,
        labels=["step_name", "step_index", "status"],  # status: success|error
    ),
    MetricDefinition(
        name="orchestration_pipeline_step_errors_total",
        description="Total pipeline step errors",
        unit="errors",
        metric_type=MetricType.COUNTER,
        labels=["step_name", "step_index", "error_type"],
    ),
]

# Dispatch Metrics Definitions（NEW）
DISPATCH_METRICS = [
    MetricDefinition(
        name="orchestration_dispatch_latency_ms",
        description="Dispatch executor latency in milliseconds",
        unit="ms",
        metric_type=MetricType.HISTOGRAM,
        labels=["executor", "status"],
    ),
    MetricDefinition(
        name="orchestration_dispatch_errors_total",
        description="Total dispatch executor errors",
        unit="errors",
        metric_type=MetricType.COUNTER,
        labels=["executor", "error_type"],
    ),
]
```

### 4.2 新 collector methods（加入 `OrchestrationMetricsCollector`）

```python
def record_pipeline_step(
    self,
    step_name: str,
    step_index: int,
    latency_ms: float,
    status: str = "success",
) -> None:
    """Record pipeline step latency. Called by pipeline/steps/base.py execute()."""
    histogram = self._histograms.get("orchestration_pipeline_step_latency_ms")
    if histogram:
        histogram.record(latency_ms, {
            "step_name": step_name,
            "step_index": str(step_index),
            "status": status,
        })

def record_pipeline_step_error(
    self,
    step_name: str,
    step_index: int,
    error_type: str,
) -> None:
    """Record pipeline step error. Called by base.execute() on exception."""
    counter = self._counters.get("orchestration_pipeline_step_errors_total")
    if counter:
        counter.add(1, {
            "step_name": step_name,
            "step_index": str(step_index),
            "error_type": error_type,
        })

def record_dispatch(
    self,
    executor: str,
    latency_ms: float,
    status: str = "success",
) -> None:
    """Record dispatch executor latency."""
    histogram = self._histograms.get("orchestration_dispatch_latency_ms")
    if histogram:
        histogram.record(latency_ms, {"executor": executor, "status": status})

def record_dispatch_error(
    self,
    executor: str,
    latency_ms: float,
    error_type: str,
) -> None:
    """Record dispatch executor error. Also records latency with status=error."""
    counter = self._counters.get("orchestration_dispatch_errors_total")
    if counter:
        counter.add(1, {"executor": executor, "error_type": error_type})
    # 亦記 error path 嘅 latency（了解 error 發生前 spent 幾耐）
    self.record_dispatch(executor, latency_ms, status="error")
```

### 4.3 Pipeline step base.py emit point

```python
# pipeline/steps/base.py
async def execute(self, context):
    collector = get_metrics_collector()
    start = time.time()
    try:
        context = await self._execute(context)
        latency_ms = (time.time() - start) * 1000
        context.mark_step_complete(self.name, latency_ms)
        collector.record_pipeline_step(self.name, self.step_index, latency_ms, "success")
        return context
    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        collector.record_pipeline_step(self.name, self.step_index, latency_ms, "error")
        collector.record_pipeline_step_error(self.name, self.step_index, type(e).__name__)
        raise
```

**Note**：HITLPauseException / DialogPauseException 算作「error」status 嗎？**否**，佢哋係控制流，非失敗。用 separate isinstance check 分離（design decision — see checklist TODO）。

### 4.4 Dispatch executor base.py emit point

```python
# dispatch/executors/base.py
async def execute(self, request, event_queue=None):
    collector = get_metrics_collector()
    start = time.time()
    try:
        result = await self._execute(request, event_queue)
        latency_ms = (time.time() - start) * 1000
        collector.record_dispatch(self.name, latency_ms, status=result.status or "success")
        return result
    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        collector.record_dispatch_error(self.name, latency_ms, type(e).__name__)
        raise
```

### 4.5 Intent Router emit point

```python
# intent_router/router.py route()
async def route(self, user_input, skip_llm=False):
    collector = get_metrics_collector()
    start = time.perf_counter()
    decision = None
    try:
        # ... existing logic, decision assigned at each return path ...
        decision = await self._route_internal(user_input, skip_llm)
        return decision
    finally:
        if decision:
            latency_s = time.perf_counter() - start
            collector.record_routing_request(
                intent_category=decision.intent_category.value if decision.intent_category else "unknown",
                layer_used=decision.routing_layer,
                latency_seconds=latency_s,
                confidence=decision.confidence_score,
                completeness_score=getattr(decision, "completeness_score", 1.0),
            )
```

**Design choice**：採 **refactor 路線**（extract `_route_internal`）或 **post-return emit**？Checklist 會列 tradeoff，最少 diff 路線優先：用 try/finally + 把 `return` 改 `decision =` pattern。

---

## 五、File Changes

| File | Type | Change |
|------|------|--------|
| `src/integrations/orchestration/metrics.py` | Modified | +2 metric definition lists、+4 collector methods、register 新 definitions 喺 `_initialize_metrics` |
| `src/integrations/orchestration/pipeline/steps/base.py` | Modified | execute() 加 collector emit（success + error path）|
| `src/integrations/orchestration/dispatch/executors/base.py` | Modified | execute() 加 try/except + collector emit |
| `src/integrations/orchestration/intent_router/router.py` | Modified | route() 包 try/finally + `record_routing_request()` |
| `tests/unit/integrations/orchestration/metrics/test_pipeline_step_wiring.py` | New | 驗證 emit via InMemoryMetricReader |
| `tests/unit/integrations/orchestration/metrics/test_dispatch_wiring.py` | New | 驗證 executor emit |
| `tests/unit/integrations/orchestration/metrics/test_routing_wiring.py` | New | 驗證 router emit |
| `tests/unit/integrations/orchestration/metrics/__init__.py` | New | package marker |

---

## 六、Acceptance Criteria

1. ✅ 新加 4 個 metric definitions 可由 `get_metrics_collector()._histograms` / `._counters` 查到
2. ✅ Pipeline step 執行一次 → `orchestration_pipeline_step_latency_ms` histogram 記到 1 次 sample
3. ✅ Pipeline step raise → error counter +1 + latency histogram with status=error +1
4. ✅ Dispatch executor 同上 2 cases
5. ✅ BusinessIntentRouter.route() 正常返回 → `orchestration_routing_requests_total` counter +1 + 3 histogram records
6. ✅ 所有新 tests 過（InMemoryMetricReader 驗證）
7. ✅ Black / isort / flake8 pass；mypy strict pass
8. ✅ 無 production error — 執行 `pytest tests/unit/integrations/orchestration/` 現有 tests 依然 pass（regression guard）

---

## 七、Known Limitations（Carry-over）

- **Dialog 4 + HITL 4 + System Source 3 metrics 仍 dead**：延後 Sprint 008
- **Gauge no-op**（OTL-04）：延後
- **Decorator refactor**（OTL-05）：延後
- **All except block metric emit**（OTL-07）：本 sprint 只 cover base class，全面 audit 延後

---

## 八、Rollback Plan

若 metric emit 引入 production issue（極不可能 — fire-and-forget）：
- Revert `pipeline/steps/base.py` + `dispatch/executors/base.py` + `intent_router/router.py` 嘅 try/finally wrapper
- `metrics.py` 新 definitions / methods 保留（dormant，冇 caller 就冇 side effect）

---

## 九、Follow-up

- **Sprint 008 stub（新）**：OTL-01 剩 11 metrics wire-up + OTL-04/05/07
- **OPS handoff**：提供 4 個新 metric name 俾 OPS team 加 Grafana dashboard
- **FIX docs**：分 3 個（FIX-OTL-01 / FIX-OTL-02 / FIX-OTL-03），reference Doc 15 對應 gap row

---

**維持 worktree 研究原則**：本 sprint 交付物停喺 `fix/wiring-sprint-005` branch，**唔 auto-merge main**。待用戶手動 manual-verify 再決定。
