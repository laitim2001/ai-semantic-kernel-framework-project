# Category 10 — Verification Loops

**ABC**: `Verifier` (in `_abc.py`)
**Spec**: `01-eleven-categories-spec.md` §範疇 10
**Implementation Phase**: 54.1
**V1 Alignment**: 15% → V2 target 70%+

## Verifier types

- **RulesBasedVerifier**: regex / schema / format check (fast, cheap)
- **LLMJudgeVerifier**: spawn subagent to judge (expensive, accurate)
- **ExternalVerifier**: call out to compliance/audit API

## Self-correction

On `VerificationResult(passed=False, suggested_correction=...)`, loop
appends correction message and re-asks LLM. Max 2 attempts per spec.

## Anti-pattern AP-9

V1 had no verification loop — agent output passed directly to user.
V2 mandates `Verifier.verify()` before main agent loop terminates.

## Cross-category tools owned

Per 17.md §3.1 — `verify` tool is owned by Category 10 and registered
into Cat 2 Registry, allowing LLM to self-trigger verification.

## Sprint roadmap

| Sprint | Adds |
|--------|------|
| 49.1   | ABC stub (this) |
| 54.1   | RulesBasedVerifier + LLMJudgeVerifier + self-correction loop |
