# pages/governance

HITL approvals + audit trail UI — `/governance` route.

**Implementation Phase**: 53.3 (engine UI), 53.4 (Teams notification)
**Backend pair**: `backend/src/api/v1/governance/`

## Phase 53.3-53.4 deliverables

- Pending approvals list (per tenant + reviewer scope)
- Approval decision modal (APPROVED / REJECTED / ESCALATED + reason)
- Audit trail viewer for any session
- Teams notification on new approval (via webhook)
