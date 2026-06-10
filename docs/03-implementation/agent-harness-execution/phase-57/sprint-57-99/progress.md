# Sprint 57.99 Progress — Verification-ESCALATE human-in-the-loop (A2)

**Plan**: [`sprint-57-99-plan.md`](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-99-plan.md) · **Checklist**: [`sprint-57-99-checklist.md`](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-99-checklist.md)
**Branch**: `feature/sprint-57-99-verification-escalate` (from `main` `be89d3ec` = A1 merged)
**Locked decisions** (AskUserQuestion 2026-06-10): APPROVE = **deliver the held failed answer (human overrides the judge)**; REJECT-with-note = **one human-coached turn, then terminal**; gating = **global settings toggle `chat_verification_escalate_on_max`, default OFF = A1 preserved**.

---

## Day 0 — Plan-vs-Repo Verify (2026-06-10)

An Explore "A2 verification-ESCALATE surface" recon ran first (mapped the 8-item surface + the realistic shape); a focused Day-0 grep then confirmed the load-bearing anchors on the A1-merged code. All anchors confirmed; all findings **reduce or confirm** scope (no expansion). **go/no-go = GO.**

### Prong 1 (path) + Prong 2 (content) — anchors confirmed (post-A1-merge)
- **The swap point** — `loop.py`: `if verdict.outcome == "failed_max":` `:2344` → `LoopCompleted(stop_reason=VERIFICATION_FAILED_STOP_REASON)` `:2346` (`VERIFICATION_FAILED_STOP_REASON = "verification_failed"` `:220`; the `_VerifyVerdict` failed_max return `:1688`). → A2 wraps `:2344-2346` in `if self._verification_escalate_on_max and not verification_escalated: → escalate; else → the A1 terminal`. **Confirmed exact.**
- **resume() kind dispatch is an `if/elif` chain** — `if kind == "input":` `:2856` / `elif kind == "between_turns":` `:2884` / `elif kind == "output":` `:2915` (→ `_replay_approved_output` `:2950`). → `elif kind == "verification":` is purely additive (D1 confirmed — no exhaustiveness consumer). **Confirmed.**
- **`_replay_approved_output`** `:3078` — the APPROVE path reuses this shape. **Confirmed.**
- **config** — `core/config/__init__.py`: `class Settings(BaseSettings)` `:28`; `chat_verification_mode: Literal["disabled","enabled"] = "enabled"` `:115`; `chat_verification_judge_template: str = "output_quality"` `:123`. → the new `chat_verification_escalate_on_max: bool = False` goes in the same Settings class near `:115-123` (the `chat_verification_*` cluster). **Confirmed.**
- The Explore recon's other anchors (carried into the plan §0, to re-confirm exactly at Day-1 as they are touched): `_emit_deferred_pause :1114-1165` (kinds tool/input/between_turns/output; output `response_snapshot`) · `_cat9_output_hitl_pause :1484-1604` (the A2 template) · `_replay_approved_output` snapshot fields `:3099-3105` · durable counter write `:3185-3186` + resume read (`metadata["verification_attempts"]`) · `ApprovalDecision.reason hitl.py:77` + `DecisionRequestBody.reason governance/router.py:106` · events `ApprovalRequested/Received events.py:400-408` · handler verification-mode threading `:265-270` + 3 builders.

### Prong 2.5 (drift) — confirmations
- **D1** — `resume()` kind dispatch is `if/elif` (`:2856`/`:2884`/`:2915`) → `elif kind == "verification":` additive, no enum/exhaustiveness break. *Confirmed.*
- **D2** — (Day-1) the held-answer snapshot field set (`_replay_approved_output :3099-3105`) must be in scope at the terminal `:2344`; if not, capture earlier in the turn. *To confirm Day-1.*
- **D3** — the REJECT bound: drive `_run_turns` with `verification_attempts=max` + `verification_escalated=True` so a 2nd fail → `failed_max` + already-escalated → terminal (not a 2nd escalate). The FAIL==max branch must read `verification_escalated`. *Design confirmed; wire Day-1.*
- **D4** — no new event (reuse `ApprovalRequested(HIGH)`/`ApprovalReceived`/`GuardrailTriggered`/`VerificationFailed` — the 57.93 precedent). *Confirmed.*

### Prong 3 (schema) — N/A
No DB/migration/ORM change (the durable `verification_escalated` bool rides the existing `state_snapshots` JSONB checkpoint metadata, the 57.98 precedent); no new event type (`check_event_schema_sync` unaffected); no new DTO (the reviewer note rides `ApprovalDecision.reason`). Confirmed no new table/column/event/DTO.

### Design-note decision
A2 = **feature-continuation** (the 4th pause leg — input/between-turns/output/verification — built from the same 57.91-93 primitive + the A1 gate) → **NO new design note** (`sprint-workflow.md §Step 5.5`, the 57.91-93/95/96 precedent). Record = CHANGE-066 + **update `25-verification-in-loop-design.md` §4** (A2 Open Invariant → SHIPPED) + 17.md (new resume kind).

### Strict-judge drive-through setup
Forcing a real verification fail for the Day-3 drive-through needs a strict judge template / a deliberately-hard prompt (the 57.98 carryover `strict-judge drive-through template`; a real gpt-5.2 answer passes the default `output_quality` judge first try). Day-3 approach: set a strict judge template (or a prompt the judge will reject) + `CHAT_VERIFICATION_ESCALATE_ON_MAX=true` on the drive-through backend; the cheap deployment (57.97) is set. If a real fail can't be forced cleanly, the escalate/approve/reject MECHANISM is unit-proven + the drive-through drives the toggle + the pause UI with a clearly-labelled forced-fail fixture.

### Drift findings (Day 0)
- **D-DAY0-1** — the swap point `:2344-2346` + the resume `if/elif` chain `:2856/2884/2915` are exactly as the plan assumed → A2 is a clean conditional-insert + additive `elif` (NO loop restructure). *Scope confirmed minimal.*
- **D-DAY0-2** — the config cluster `chat_verification_*` lives at `core/config/__init__.py:115-123` → the new toggle is a 1-line addition in the existing Settings class. *Confirmed straightforward.*
- (Day-1 will confirm D2 — the snapshot field set at the terminal — as `_cat10_verification_escalate_pause` is written.)

### Go/No-Go
**GO.** The recon + Day-0 grep confirm A2 is: a config toggle (1 line) + a new `_cat10_verification_escalate_pause` (mirror `_cat9_output_hitl_pause`) + a conditional at the FAIL==max terminal (`:2344`) + an additive `resume()` `elif kind == "verification":` + a durable `verification_escalated` bool (metadata, the 57.98 precedent). No new event/DB/DTO/migration/frontend. Scope shift vs plan ≈ 0%.

### Baseline (at branch creation)
- Branch `feature/sprint-57-99-verification-escalate` from `main` `be89d3ec` (A1 merged via PR #272)
- pytest collected = **2298** (`-m "not real_llm"`); `mypy src` = **0/353**; run_all 10/10 (to re-confirm at Day-0 commit)

---
