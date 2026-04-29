# features/guardrails

UI components for **Category 9 (Guardrails)** — governance UI.

**Backend pair**: `backend/src/agent_harness/guardrails/`
**Used by**: pages/governance
**First impl**: Phase 53.3

## Components (planned)

- `<GuardrailViolationCard>` — per-violation viewer (type + action + reason + risk_level)
- `<TripwireBanner>` — severe violation alert (loop terminated)
- `<ApprovalDecisionModal>` — used by governance page
- `<RiskLevelBadge>` — visual LOW / MEDIUM / HIGH / CRITICAL
