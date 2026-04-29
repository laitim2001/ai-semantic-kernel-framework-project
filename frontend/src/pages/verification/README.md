# pages/verification

Verifier panel — `/verification` route.

**Implementation Phase**: 54.1
**Backend pair**: `backend/src/agent_harness/verification/`

## Phase 54.1 deliverables

- Verifier results timeline (passed / failed / correction attempts)
- Self-correction trace (suggested_correction → re-LLM-call → re-verify)
- Verifier type breakdown (rules_based / llm_judge / external)
