# Category 8 — Error Handling

**ABCs**: `ErrorPolicy`, `CircuitBreaker`, `ErrorTerminator` (in `_abc.py`)
**Spec**: `01-eleven-categories-spec.md` §範疇 8
**Implementation Phase**: 53.2
**V1 Alignment**: 20% → V2 target 75%+

## 4-class error taxonomy

| Class            | Action |
|------------------|--------|
| TRANSIENT        | Retry with backoff |
| LLM_RECOVERABLE  | Feed error back to LLM, let it adapt prompt |
| HITL_RECOVERABLE | Pause loop; wait for human decision (via §HITL) |
| FATAL            | Terminate via ErrorTerminator |

## Boundary with Category 9

Per 17.md §6: **Tripwire** is owned by Cat 9 (Guardrails). Cat 8 uses
**ErrorTerminator** for budget/circuit-driven termination. Different
naming prevents confusion.

## Sprint roadmap

| Sprint | Adds |
|--------|------|
| 49.1   | ABC stub (this) |
| 53.2   | 4-class classifier + retry strategies + circuit breaker + terminator |
