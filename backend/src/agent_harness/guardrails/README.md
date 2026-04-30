# Category 9 — Guardrails & Safety

**ABCs**: `Guardrail`, `Tripwire` (in `_abc.py`)
**Spec**: `01-eleven-categories-spec.md` §範疇 9
**Implementation Phase**: 53.3 (engine) + 53.4 (Tripwire patterns)
**V1 Alignment**: 30% → V2 target 85%+

## 3 guardrail types

| Type   | Position | Examples |
|--------|----------|----------|
| INPUT  | before LLM | PII detect, jailbreak detect, prompt injection |
| OUTPUT | after LLM  | toxicity, factuality, leak detect, format check |
| TOOL   | before tool exec | RBAC, parameter sanity, scope check |

## Tripwire vs ErrorTerminator (per 17.md §6)

- **Tripwire (Cat 9)**: severe policy violation (PII leak, jailbreak, data exfil) → terminate
- **ErrorTerminator (Cat 8)**: budget exhausted / circuit open / fatal exception → terminate

Different categories own different terminators. Don't conflate.

## Anti-pattern AP-3

V1 had Guardrails scattered in 6 places (security / hitl / risk_assessor /
audit / hooks / acl). V2 owns them ALL here in `guardrails/`. No
scattering allowed.

## Sprint roadmap

| Sprint | Adds |
|--------|------|
| 49.1   | ABC stub (this) |
| 53.3   | Guardrail engine + 3-type chain + result composition |
| 53.4   | Tripwire patterns (PII / jailbreak / data exfil detectors) |
