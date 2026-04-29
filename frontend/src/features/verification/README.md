# features/verification

UI components for **Category 10 (Verification)** — verifier panel.

**Backend pair**: `backend/src/agent_harness/verification/`
**Used by**: pages/verification
**First impl**: Phase 54.1

## Components (planned)

- `<VerificationResultCard>` — per-result viewer (verifier_type / passed / score / reason / suggested_correction)
- `<SelfCorrectionTrace>` — show iteration N / max_attempts (typically max=2)
- `<VerifierTypeBadge>` — rules_based / llm_judge / external visual
