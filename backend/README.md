# IPA Platform V2 — Backend

Server-side, LLM-provider-neutral agent harness. Built around **11 + 1
categories** of agent harness concerns (per
`docs/03-implementation/agent-harness-planning/01-eleven-categories-spec.md`).

> **Status**: Phase 49 Foundation, Sprint 49.1 (skeleton only — no business
> logic, no LLM calls). Each subsequent Phase fills in one or more
> categories. See `06-phase-roadmap.md` for the 22-sprint plan.

## Architecture (5 layers)

```
backend/src/
├── agent_harness/          ← The 11+1 categories of agent harness
│   ├── _contracts/         ← Cross-category single-source types (per 17.md)
│   ├── orchestrator_loop/  ← Cat 1: TAO/ReAct loop
│   ├── tools/              ← Cat 2: Tool registry + executor
│   ├── memory/             ← Cat 3: 5-layer memory
│   ├── context_mgmt/       ← Cat 4: Compaction + caching
│   ├── prompt_builder/     ← Cat 5: Layered prompt assembly
│   ├── output_parser/      ← Cat 6: Parse LLM responses + tool calls
│   ├── state_mgmt/         ← Cat 7: Checkpoint + reducer
│   ├── error_handling/     ← Cat 8: 4-class error policy
│   ├── guardrails/         ← Cat 9: Input/output/tool + tripwire
│   ├── verification/       ← Cat 10: Verifier + self-correction
│   ├── subagent/           ← Cat 11: 4-mode dispatch (no worktree)
│   ├── observability/      ← Cat 12: Cross-cutting tracing (ABC owner)
│   └── hitl/               ← HITL centralization (per §HITL)
├── platform_layer/         ← Governance, identity, observability impl, workers
│                              (named `platform_layer` not `platform` to avoid
│                               shadowing Python stdlib `platform` module)
├── adapters/               ← Outbound integrations
│   ├── _base/              ← ChatClient ABC (LLM-provider-neutral)
│   ├── azure_openai/       ← V2 primary provider (Sprint 49.3)
│   ├── anthropic/          ← Optional adapter (Phase 50+)
│   └── maf/                ← Microsoft Agent Framework (Sprint 54.2 if needed)
├── api/v1/                 ← FastAPI endpoints
├── business_domain/        ← Patrol / correlation / rootcause / etc. (Phase 55)
├── infrastructure/         ← DB / cache / messaging / storage clients
├── core/                   ← Config, exceptions, logging
└── middleware/             ← Tenant context, auth context
```

## Critical rules

- **LLM-provider-neutrality**: `agent_harness/**` must NEVER import openai
  / anthropic SDKs. Use `adapters/_base/chat_client.py` (`ChatClient` ABC).
  CI lint enforces this in Sprint 49.4.
- **Single-source types**: All cross-category dataclasses / ABCs / events
  live in `agent_harness/_contracts/`. Never duplicate.
- **Multi-tenant**: All business tables include `tenant_id`; all queries
  filter by it. RLS policies added in Sprint 49.3.

## Quickstart

```bash
# Install (Phase 49 dev mode)
pip install -e ".[dev]"

# Run linters (CI gates added in Sprint 49.1 Day 5)
black --check . && isort --check . && flake8 . && mypy src/

# Run tests
pytest

# Start FastAPI dev server (skeleton only at Sprint 49.1)
uvicorn src.main:app --reload --port 8001

# Health check
curl http://localhost:8001/health
```

## References

- V2 plan root: `docs/03-implementation/agent-harness-planning/`
- Server-side / LLM-neutral / CC reference: `10-server-side-philosophy.md`
- 11+1 categories: `01-eleven-categories-spec.md`
- Cross-category interface registry: `17-cross-category-interfaces.md`
- Anti-patterns checklist: `04-anti-patterns.md`
- Sprint 49.1 plan: `phase-49-foundation/sprint-49-1-plan.md`
