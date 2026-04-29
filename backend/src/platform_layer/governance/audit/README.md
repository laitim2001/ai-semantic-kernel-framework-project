# platform/governance/audit

Append-only audit log + Merkle hash chain (per 14-security-deep-dive.md).

**Implementation Phase**: 49.3 (append-only WORM table), 53.x (Merkle chain)
**Consumed by**: All categories (every state mutation + tool execution + HITL decision is auditable)
