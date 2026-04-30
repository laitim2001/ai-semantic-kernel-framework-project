# api/v1/governance — HITL + governance endpoints

**Implementation Phase**: 53.3 (HITL approval), 53.4 (Teams notification)

## Endpoints (planned)

- `GET /api/v1/governance/approvals/pending` — list pending approvals (per tenant + reviewer scope)
- `POST /api/v1/governance/approvals/{id}/decide` — submit decision (APPROVED / REJECTED / ESCALATED)
- `GET /api/v1/governance/audit/{session_id}` — audit trail

All endpoints require multi-tenant context (`current_tenant`) per
`.claude/rules/multi-tenant-data.md`.
