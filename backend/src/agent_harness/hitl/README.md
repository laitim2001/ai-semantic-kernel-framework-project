# §HITL — Human-in-the-Loop Centralization

**ABC**: `HITLManager` (in `_abc.py`)
**Spec**: `01-eleven-categories-spec.md` §HITL 中央化
**Implementation Phase**: 53.3 (engine), 53.4 (Teams notification)

## Why centralized

V1 had HITL logic scattered:
- Category 2 (tools/request_approval)
- Category 7 (state/pending_approvals)
- Category 8 (errors/HITL recoverable)
- Category 9 (guardrails/HITL escalate)

→ Modifying one place left others stale. V2 centralizes via `HITLManager`.

## Cross-category interaction (per 17.md §5.3)

- **Cat 2 / Cat 9** are CALLERS — invoke `request_approval()`
- **Cat 7** is STORAGE — `pending_approval_ids` in DurableState
- **Cat 8** is NOT owner — treats HITL as resumable wait
- **Reducer** (Cat 7) merges `ApprovalDecision` back into LoopState

## Cross-category tools owned

Per 17.md §3.1 — `request_approval` tool is owned here and registered
into Cat 2 Registry.

## Sprint roadmap

| Sprint | Adds |
|--------|------|
| 49.1   | ABC stub (this) |
| 53.3   | HITLManager + DB queue + cross-session resume |
| 53.4   | Teams notification + reviewer UI integration |
