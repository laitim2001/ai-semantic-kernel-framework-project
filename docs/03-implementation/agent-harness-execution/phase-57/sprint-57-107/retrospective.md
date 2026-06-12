# Sprint 57.107 Retrospective — B3 HANDOFF finish

**Closed**: 2026-06-12 · Branch `feature/sprint-57-107-handoff-finish` (base `main` `b6b2c392`)
**Commits**: `126fbf9d` Day0 · `7b4e657f` Day1 · `c28732e1` Day2 · `f2ad65c9` Day3-FE · `801a9165` Day3-DT/docs · (closeout)

## Q1 — What shipped vs planned

ALL 5 user stories shipped, 0 scope cuts. US-1 stub trio retired + spec-only `handoff` tool (the chat 主流量's FIRST LLM-drivable handoff); US-2 `HarnessPolicy` 9→11 + boot allowlist double-gate + admin/FE; US-3 `GET /sessions` + SessionList real-data + ↳ 鏈 badge (closes `AD-ChatV2-SessionList-Backend`); US-4 migration 0028 + sidechain transcript observer (`message_events` first writer; closes `AD-Subagent-Transcript-Isolation`); US-5 drive-through ALL 4 legs PASS. Bonus: D4 partition time-bomb defused (both tables un-writable from 2026-07-01 — pre-existing dated production failure caught by Prong 3).

## Q2 — Calibration

Plan §7: bottom-up ~18.5 hr → class-calibrated commit ~12 hr (`mixed-multidomain-bundle` 0.65). Actual ≈ 9.5-11 hr-equivalent (Day 0 recon+plan ~1.5 · Day 1 ~2 · Day 2 ~2.5 · Day 3 parent ~2.5 incl. drive-through · Day 4 ~1). **Ratio ≈ 0.8-0.9 IN band** — the class's first IN-band point after the 0.42 confound era (resolved at the agent_factor sub-class layer). **Agent-delegated: partial** (FE track delegated-then-parent-re-verified; backend parent-direct — 57.104/57.106 blended precedent, no single agent_factor; 3-segment form held).

## Q3 — What went well

- **Day-0 three-prong paid for the sprint**: D4 (partition time-bomb — a dated production failure invisible to all suites) + the head-start recon's "no handoff ToolSpec on 主流量" finding reshaped US-1 from hygiene into the slice's biggest payoff (LLM-drivable handoff).
- **Pattern reuse compounding**: C3's policy machinery absorbed US-2 in ~1 hr (field lists drive from_dict/to_dict/is_empty automatically); the sessions-observer SAVEPOINT pattern absorbed US-4's observer; `_HandoffLoop`/`_SpawningLoop` test scaffolds mirror cleanly.
- **Drive-through over-delivered**: B1 produced an UNPLANNED observation — the allowlist's spec-description layer alone steered the live LLM to the only legal target (defense layer 1 works on real model behavior, not just at boot).
- 7 integration tests passed first-run; full suite +21 with 0 deletions.

## Q4 — What to improve / lessons

- **L1 (process)**: the founder drive-through password wasn't recoverable post-compaction (correctly absent from docs) — the 57.105 D11 out-of-band `set_password` re-set pattern recovered in ~5 min; acceptable, no AD (secrets stay out of docs; the reset primitive IS the recovery path).
- **L2 (tooling)**: `run_all.py` from `backend/` CWD reports 9/10 false-FAIL (CWD-sensitive `--root` defaults) — run from repo root; recurred once before (Day-1 note); if it bites a 3rd time → propose a CWD guard in the wrapper (AD candidate logged below).
- **L3 (drive-through design)**: a forced off-list handoff attempt is hard to elicit live — the spec description steers the LLM too well; boot-layer negatives belong to integration tests (documented as an Open Invariant in note 29, honest split).

## Q5 — Anti-pattern audit

AP-1..11: 0 violations. AP-2/AP-11 NET-NEGATIVE (the stub trio removed). AP-4 guarded twice (defensive-raise handler + negative tests). Drive-through item 8: PASS with 4 screenshots + observed-vs-intended table.

## Q6 — Carryover (→ next-phase-candidates)

- **`AD-Sidechain-Transcript-Read-API`** (NEW): sidechain rows + message_events are write-only today — a READ API + Inspector replay UI is the natural consumer slice.
- **`AD-RunAll-CWD-Guard`** (NEW, 🟢 process): run_all.py false-FAILs from non-root CWD; add a repo-root guard if it recurs.
- Deferred unchanged: detached teammate (§2.5, unlocks inject UI) · depth>1 · multi-hop lineage tree walk · parent `messages` writes · C2 / B4 / A3.

## Q7 — Next slice

Per the interleave decision (RBAC → C3 → **B3 ✅** → UX → C2 → B4): next = **1 UX slice** (candidates: `AD-ChatV2-HITL-Card-Tool-Name` + `AD-ChatV2-Inspector-Turn-Metadata-Wire` bundle, or `AD-FE-Tenant-Display-Fixture-Phase58`), then C2 compaction cheap tier. Rolling: no plan pre-written.

## Design Note Extract（spike sprint）

**File**: `docs/03-implementation/agent-harness-planning/29-handoff-completion-sidechain-transcript-design.md`
**Verified ratio (estimated)**: ~96%
**8-Point Quality Gate**: [x] 1 section↔US · [x] 2 file:line · [x] 3 decision matrix · [x] 4 verification commands · [x] 5 test fixtures · [x] 6 open-invariant 分界 · [x] 7 rollback · [x] 8 17.md cross-ref
**Reviewer pass**: self-review
