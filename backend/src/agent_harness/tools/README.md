# Category 2 — Tool Layer

**ABCs**: `ToolRegistry`, `ToolExecutor` (in `_abc.py`)
**Spec**: `01-eleven-categories-spec.md` §範疇 2
**17.md ABCs**: §2.1
**Implementation Phase**: 51.1
**V1 Alignment**: 32% → V2 target 75%+

## Responsibility

- Define + register `ToolSpec` (LLM-neutral tool definitions)
- Execute tool calls in a sandbox respecting `ConcurrencyPolicy` + `ToolAnnotations`
- Owns **built-in** tools (`web_search`, `python_sandbox`, etc.)
- Cross-category tools (`memory_*`, `task_spawn`, `handoff`, `request_approval`, `verify`)
  are **owned by their category** per 17.md §3.1 and registered here via helpers.

## Critical rules

- **No business-domain tools** here. Patrol / correlation / rootcause /
  audit / incident tools live in `business_domain/<domain>/tools.py` per
  `08b-business-tools-spec.md`.
- **No HITL logic in tools** — call `HITLManager.request_approval()` directly.

## Sprint roadmap

| Sprint | Adds |
|--------|------|
| 49.1   | ABC stub (this) |
| 51.1   | Built-in tools + sandbox executor + concurrency planner |
| 51.2+  | Cross-category register_*() helpers wired |
