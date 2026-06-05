# Sprint 57.83 Retrospective — B-8 leg-2: general judge + real-LLM e2e + flip default

**Sprint**: 57.83
**Closed**: 2026-06-05
**Branch**: `feature/sprint-57-83-verification-enable`
**Closes**: B-8 (blocker B + C + flip) / `AD-Cat10-Wire-1-Production` — **B-8 fully closed**

---

## Q1. Goal achieved?

✅ Yes — B-8 fully closed. Shipped a general final-output quality judge (blocker B), measured it against real Azure (blocker C), and flipped `chat_verification_mode` default to `enabled` on the data:
- NEW `output_quality.txt` (re-tuned to a lightweight "clearly-failed-only" judge) + default judge template swap.
- Real-Azure measurement: pass 1 (fail-on-any) FP ~75% → DO-NOT-FLIP; re-tuned in-sprint → pass 2 (lightweight) FP 0% → FLIP.
- Default `chat_verification_mode` `disabled` → `enabled`. Gates: mypy src/ 0 (332) / pytest 2150 / run_all 10/10.

## Q2. Estimate accuracy

- Plan: bottom-up ~5.5 hr → class-calibrated commit ~4.4 hr (`medium-backend` 0.80, `agent_factor` 1.0 parent-direct).
- Actual: ~5 hr. Day-0 + blocker B (template + default + tests) ~1.5 hr; Docker/backend spin-up + 2 measurement passes + re-tune ~2 hr; flip + grep + full test ~0.5 hr; closeout ~1 hr.
- Ratio actual/committed ~1.14 — band upper edge. **Caveat (noted in plan §7)**: the real-LLM measurement is research-shaped (Docker setup + 2 passes + an unplanned re-tune cycle); wall-clock is noisier than a pure-code sprint. `medium-backend` 0.80 roughly held. Clean human-cadence data point (NOT agent-delegated).

## Q3. What went well

- **The data-driven gate did exactly its job**: pass 1 measured the user-selected fail-on-any judge at ~75% FP on real Azure — it would have shipped a false-positive storm (normal answers failed + 3× correction re-runs + `stop_reason=verification_failed` shown to users). The gate caught it before the flip.
- **In-sprint re-tune closed the loop**: rather than deferring, the lightweight "clearly-failed-only" judge was re-tuned + re-measured (FP 0%) in the same sprint, so B-8 fully closed. The leg-1 AskUserQuestion had flagged this exact lighter judge as the low-FP option — the data vindicated it.
- **load_template reads per-call → no restart needed** for the re-tune: editing `output_quality.txt` took effect on the running backend's next chat, so re-measure was immediate.
- **Flip was provably safe**: a Prong-2 grep before the flip showed only ONE test (`test_default_is_disabled`) depended on the default; everything else sets mode explicitly. Full pytest 2150 confirmed the flip broke nothing.
- **Cost measurement was free**: leg-1's judge→ledger wiring meant the `_verification` cost entries were already there to read.

## Q4. Lessons

- **A strict "fail on any dimension" judge is the wrong default for general traffic** — real LLMs give terse-but-correct answers that a 4-dimension judge rejects. The right bar for a low-FP gate is "flag only clear failures (refusal/incoherent/empty/off-topic), default to pass." Confirmed empirically (75% → 0% FP) by swapping only the template phrasing.
- **A subjective judge's FP rate cannot be reasoned about — it must be measured.** The same judge that "sounds reasonable" in a prompt produced 75% FP. The data-driven gate (Q2 choice) was the right call over flipping on a mock-only basis.
- **Small-sample caveat**: 8 normal prompts is enough to reject a 75%-FP judge but not to certify a production FP rate precisely. The flip ships on a 0%-of-8 signal — monitor real-traffic verification_failed rate post-flip (Q6 carryover).

## Q5. Improvements next sprint

- When a sprint includes a real-LLM measurement, budget explicitly for a re-tune cycle (the first template rarely lands). The 2-pass + re-tune shape here was ~half the wall-clock — worth planning for, not treating as overrun.

## Q6. Carryover

- **Monitor production verification_failed rate post-flip** — the 0% FP is from 8 prompts; watch real-traffic FP + correction-rate to confirm the lightweight judge holds (the leg-1 `_verification` ledger + verification_log give the data). If real FP creeps up, re-tune.
- **Per-verifier cost attribution** (leg-1 carryover) — still one `_verification` sub_type.
- **Multi-judge registry** (safety + quality) — shipped one general quality judge; layering safety/PII on the main path is a separate decision.
- **C-15 DevOps/data-platform billing** — the billing-bundle's remaining leg (cost_ledger 雙扣 risk).

## Q7. Risks

- **Medium** (this flips a production default). Mitigations: the lightweight judge measured 0% FP + caught genuine garbage; fail-closed semantics unchanged; correction capped at 2; the flip is env-overridable (`CHAT_VERIFICATION_MODE=disabled`) for instant rollback; full pytest 2150 green. Residual: small measurement sample (8 prompts) — Q6 monitoring carryover. judge adds ~1 LLM call + ~5s tail per chat (within the §範疇10 < 5s SLO) + judge cost (~$0.0047/chat, now correctly billed via leg-1).

---

## Design Note Extract

NO — new prompt template + config-default change + a measurement artifact; no new contract / no new domain spike. (The measurement protocol + data live in `claudedocs/5-status/cat10-verification-real-llm-measurement-20260605.md`.)
