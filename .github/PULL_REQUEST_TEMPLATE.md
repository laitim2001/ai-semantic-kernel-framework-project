# Pull Request

## Summary

<!-- 1-3 sentences. What changed and why? -->

## Sprint linkage

- Sprint plan: `docs/03-implementation/agent-harness-planning/phase-XX-name/sprint-XX-Y-plan.md`
- Sprint checklist: `docs/03-implementation/agent-harness-planning/phase-XX-name/sprint-XX-Y-checklist.md`
- Progress doc: `docs/03-implementation/agent-harness-execution/phase-XX/sprint-XX-Y/progress.md`

## V2 Three Highest Principles (10-server-side-philosophy.md)

- [ ] **Server-Side First**: No host-fs access; tools call enterprise APIs only
- [ ] **LLM Provider Neutrality**: `agent_harness/**` does not `import openai` / `import anthropic`; `ChatClient` ABC used
- [ ] **CC Reference, Not Copy**: V2-specific server-side adaptation, not local-agent ports

## Cross-Category Interface Check (17-cross-category-interfaces.md)

- [ ] All cross-category dataclasses / ABCs / events come from `agent_harness._contracts/` — none re-defined elsewhere
- [ ] If new cross-category type added: 17.md owner table also updated
- [ ] No cross-category direct private imports (only public ABCs / contracts)

## Anti-Patterns Checklist (04-anti-patterns.md, 11 points)

- [ ] AP-1: No Pipeline-disguised-as-Loop (if has LLM calls)
- [ ] AP-2: No side-track / orphan code (traceable from `api/`)
- [ ] AP-3: No cross-directory scattering (each function lives in its category)
- [ ] AP-4: No Potemkin features (functionality + tests, not just structure)
- [ ] AP-5: No undocumented PoC (deadline + decision exit if PoC)
- [ ] AP-6: No "future-proof" abstraction without real use case
- [ ] AP-7: Context rot mitigated (if long conversation involved)
- [ ] AP-8: All LLM calls go through `PromptBuilder` (not ad-hoc messages = [...])
- [ ] AP-9: Has verification (if output generation)
- [ ] AP-10: Mock and real adapters share same ABC
- [ ] AP-11: No version suffixes (`_v1`, `_v2`, `_old`); naming consistent

## Multi-tenant + Security

- [ ] All new business tables include `tenant_id`
- [ ] All new endpoints inject `current_tenant` dependency
- [ ] All queries filter by tenant_id
- [ ] No PII / secrets committed; .env not staged

## Test plan

<!-- Bulleted list of how the changes were verified. -->

- [ ]
- [ ]
- [ ]

## CI Gates

- [ ] `cd backend && black --check . && isort --check . && mypy src/ --strict && pytest`
- [ ] `cd frontend && npm run lint && npm run build`

🤖 Per `.claude/rules/git-workflow.md` Pre-commit checklist
