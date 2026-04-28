# Category 3 — Memory (5-layer × 3-time-scale)

**ABC**: `MemoryLayer` (in `_abc.py`)
**Spec**: `01-eleven-categories-spec.md` §範疇 3
**Implementation Phase**: 51.2
**V1 Alignment**: 15% → V2 target 70%+

## 5 layers × 3 time scales

| Scope     | Permanent | Quarterly | Daily |
|-----------|-----------|-----------|-------|
| system    | global rules | trends | flags |
| tenant    | policies | KPIs | events |
| role      | role manual | role context | role state |
| user      | preferences | recent topics | session refs |
| session   | (n/a) | summary | turn buffer |

## Lead-then-verify pattern

`read()` returns `MemoryHint` (token-cheap). The loop verifies relevance
before calling `resolve()` to fetch full content. Prevents context bloat.

## Cross-category tools owned

Per 17.md §3.1 — these are **owned by Memory** and registered into Cat 2 Registry:
- `memory_search` (read across layers)
- `memory_write` (write to specified layer)
- `memory_extract` (background worker job)

## Sprint roadmap

| Sprint | Adds |
|--------|------|
| 49.1   | ABC stub (this) |
| 51.2   | 5 layer implementations + DB tables + Vector DB |
