# V1 Archive — Phase 1-48 (READ-ONLY)

> ⛔ **READ-ONLY. DO NOT MODIFY.** This is the frozen V1 baseline.
>
> **Frozen on**: 2026-04-29 (start of V2 Phase 49 launch)
> **Git tag**: `v1-final-phase48`
> **Final commit at freeze**: `1d9b05f` (chore(gitignore): exclude entire graphify-out/ directory)

---

## What is in this directory

V1 of the IPA Platform — Phase 1 through Phase 48 (Sprint 1-180), as of
2026-04-29. The contents below represent ~5 months of accumulated work:

| Subdirectory | What it was | Notes |
|--------------|-------------|-------|
| `backend/` | FastAPI backend (Python) | Includes `integrations/agent_framework/` (Microsoft Agent Framework) and `integrations/claude_sdk/` (Claude Agent SDK) — both core to V1 architecture, **not used by V2** |
| `frontend/` | React 18 + Vite frontend | Includes `pages/chat/`, `pages/agent-swarm/`, and shared components — V2 will rebuild as `chat-v2/` etc. |
| `infrastructure/` | Docker, K8s, deployment configs | V2 will re-evaluate each component; do not assume V2 inherits any of this |

---

## V1 alignment baseline (Why V2 exists)

V1 was audited (2026-04 V9 analysis) and rated as having only **~27% real
alignment** with the agent-harness 11-category specification. Eight of
the 11 categories scored Level 0–2 (unusable / half-baked):

| Category | V1 alignment |
|----------|--------------|
| 1. Orchestrator Loop | 18% |
| 2. Tool Layer | 32% |
| 3. Memory | 15% |
| 4. Context Mgmt | 5% |
| 5. Prompt Construction | 20% |
| 6. Output Parsing | 75% |
| 7. State Mgmt | 30% |
| 8. Error Handling | 20% |
| 9. Guardrails | 30% |
| 10. Verification Loops | 15% |
| 11. Subagent Orchestration | 35% |

→ V2 (Phase 49+) is a **rebirth**, not a patch. See
`docs/03-implementation/agent-harness-planning/00-v2-vision.md`.

---

## Phase 48 final state — Sprint 181 DEFERRED

V1's last active phase was Phase 48 (LLM-native orchestrator). Status at
freeze:

- ✅ **Sprint 179 + 180**: completed. Legacy code removal of -7,430 lines
  (3.7× the planned target). LLM-native orchestrator + 7 YAML configs
  landed in V1.
- ❌ **Sprint 181**: **DEFERRED, not executed**. Planned scope was:
  - completeness folder migration
  - guided_dialog migration

  These will **not** be completed in V1. V2 (Phase 49+) does not reuse
  the V1 orchestrator architecture (TAO/ReAct loop replaces hybrid
  orchestrator + intent classifier), so finishing Sprint 181 was judged
  low-ROI (its output would be archived immediately).

  If you need to understand where Sprint 181 left off, see:
  - `docs/03-implementation/sprint-planning/` (frozen V1 sprint plans)
  - Last Phase 48 progress logs in `claudedocs/3-progress/`

---

## V2 has replaced V1

| Concern | V1 (this archive) | V2 (`backend/`, `frontend/` after Sprint 49.1) |
|---------|-------------------|------------------------------------------------|
| Architecture | Hybrid orchestrator + intent classifier + MAF / Claude SDK | TAO/ReAct agent harness, 11+1 categories, LLM-provider-neutral |
| LLM coupling | Direct `import openai` / `import anthropic` allowed | Strict ChatClient ABC; SDK imports forbidden in `agent_harness/` |
| Multi-tenant | Partial (per-table tenant_id, no RLS) | Strict (RLS + tenant_id rule, GDPR-aware) |
| Observability | Ad-hoc logging | Cross-cutting Category 12 (OTel + TraceContext) |

V2 authoritative docs: `docs/03-implementation/agent-harness-planning/`
(19 docs).

---

## What is preserved at repo root (NOT in this archive)

These directories remain at the repo root because V2 continues to use
them:

- `docs/` — All V1 design docs are reference material for V2
- `claudedocs/` — AI assistant collaboration logs continue across V1/V2
- `reference/` — V1 reference snapshots (MAF / Claude SDK source) — V2
  may still consult these as inspiration (per
  `agent-harness-planning/05-reference-strategy.md`)

---

## What you can / cannot do here

### ✅ Allowed (read-only inspection)

- Inspect V1 source code for design lessons or historical context
- Reference specific V1 files in V2 design discussions
- Use this archive to validate "did V1 ever do X?" questions

### ⛔ Forbidden

- **Do not modify any file in this directory.** If a fix is needed, fix
  it in V2 instead — V2 supersedes V1 entirely.
- **Do not extend V1.** The Microsoft Agent Framework integration
  (`backend/src/integrations/agent_framework/`) and Claude SDK
  integration (`backend/src/integrations/claude_sdk/`) are frozen.
- **Do not run V1 services in production.** V2 will replace V1 once
  Phase 55 completes (~5.5 months from 2026-04-29).

---

## How to inspect V1 at the freeze point

```bash
# Check out V1 final state (read-only):
git checkout v1-final-phase48

# Or browse this archive directly (also read-only by convention):
ls archived/v1-phase1-48/
```

---

## V2 launch reference

| Item | Reference |
|------|-----------|
| V2 vision | `docs/03-implementation/agent-harness-planning/00-v2-vision.md` |
| 11+1 categories | `docs/03-implementation/agent-harness-planning/01-eleven-categories-spec.md` |
| 22-sprint roadmap | `docs/03-implementation/agent-harness-planning/06-phase-roadmap.md` |
| Sprint 49.1 plan | `docs/03-implementation/agent-harness-planning/phase-49-foundation/sprint-49-1-plan.md` |
| Anti-patterns to avoid (lessons from V1) | `docs/03-implementation/agent-harness-planning/04-anti-patterns.md` |

---

**Frozen by**: Sprint 49.1 Day 1 (2026-04-29) — see commit message of the
archive operation for exact author / co-author attribution.
