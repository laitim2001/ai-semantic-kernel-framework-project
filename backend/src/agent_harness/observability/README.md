# Category 12 — Observability (cross-cutting)

**ABC**: `Tracer` (in `_abc.py`)
**Spec**: `01-eleven-categories-spec.md` §範疇 12
**ABC Implementation Phase**: 49.4 (when OTel + Jaeger wire up)
**V1 Alignment**: 0% → V2 target 75%+

## Cross-cutting

Every other category's ABC accepts `trace_context: TraceContext` —
this is mandatory, not optional. Tracer.start_span() is called at
each ABC entry. Per 17.md §7.2: this is THE rule, not repeated in
each category spec.

## ABC owner here, impl elsewhere

This directory only owns the **ABC**. The actual implementation
(OTel SDK + Jaeger exporter + Prometheus exporter + log correlation)
lives in `backend/src/platform/observability/`. Per architecture-design
5-layer split: `agent_harness/` defines contracts, `platform/`
implements platform-wide infrastructure.

## 5 must-instrument points

Per `observability-instrumentation.md` (.claude/rules/):

1. Loop turn open/close (Cat 1)
2. Tool execution open/close (Cat 2)
3. LLM call open/close (Adapters layer)
4. Verification pass/fail (Cat 10)
5. State checkpoint write/read (Cat 7)

## Sprint roadmap

| Sprint | Adds |
|--------|------|
| 49.1   | ABC stub (this) |
| 49.4   | OTel + Jaeger + Prometheus integration in `platform/observability/` |
| 50.1+  | Each category's implementation calls Tracer at the 5 points above |
