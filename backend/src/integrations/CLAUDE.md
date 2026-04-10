# Integrations Layer

> 16 integration modules, ~315 Python files — External framework adapters and protocol implementations

---

## Module Index

| Module | Files | LOC | Phase | Purpose |
|--------|-------|-----|-------|---------|
| **[agent_framework/](agent_framework/CLAUDE.md)** | 53 | ~15K | 1-4 | MAF Adapters (builders, memory, multiturn, tools) |
| **[claude_sdk/](claude_sdk/CLAUDE.md)** | 47 | ~15K | 12 | Claude Agent SDK (autonomous, hooks, hybrid, mcp, tools) |
| **[hybrid/](hybrid/CLAUDE.md)** | 60 | ~21K | 13-14 | Hybrid MAF+Claude SDK bridge |
| **[orchestration/](orchestration/CLAUDE.md)** | 39 | ~16K | 28 | Three-tier Intent Routing system |
| **[ag_ui/](ag_ui/)** | 18 | — | 15 | AG-UI Protocol (SSE events, features, threads) |
| **[mcp/](mcp/CLAUDE.md)** | 43 | ~4K | 9-10 | MCP servers (Azure, Filesystem, LDAP, Shell, SSH) |
| **[patrol/](patrol/)** | 10 | — | 23 | Continuous monitoring checks |
| **[swarm/](swarm/CLAUDE.md)** | 7 | ~1K | 29 | Agent Swarm state tracking + SSE events |
| **[llm/](llm/)** | 6 | — | 1 | LLM client integration (Azure OpenAI) |
| **[memory/](memory/)** | 5 | — | 22 | mem0 memory system |
| **[learning/](learning/)** | 5 | — | 4 | Few-shot learning mechanism |
| **[audit/](audit/)** | 4 | — | 23 | Audit integration |
| **[correlation/](correlation/)** | 4 | — | 23 | Multi-agent event correlation |
| **[a2a/](a2a/)** | 3 | — | 23 | Agent-to-Agent protocol |
| **[rootcause/](rootcause/)** | 3 | — | 23 | Root cause analysis |

---

## Architecture

```
                    ┌─────────────────────┐
                    │   API Layer (v1/)    │
                    └─────────┬───────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
   ┌──────────▼──────┐ ┌─────▼─────┐ ┌───────▼──────┐
   │ agent_framework/ │ │ claude_sdk │ │ orchestration│
   │ (MAF Adapters)   │ │ (Claude)  │ │ (Intent Rtr) │
   └────────┬─────────┘ └─────┬─────┘ └──────┬───────┘
            │                 │               │
            └────────┬────────┘               │
                     │                        │
              ┌──────▼──────┐          ┌──────▼──────┐
              │   hybrid/   │          │    hitl/     │
              │ (Bridge)    │          │  (Approval)  │
              └──────┬──────┘          └─────────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
    ┌────▼───┐ ┌─────▼────┐ ┌───▼────┐
    │  mcp/  │ │  swarm/  │ │ ag_ui/ │
    │(Tools) │ │(Workers) │ │ (SSE)  │
    └────────┘ └──────────┘ └────────┘
```

## Key Patterns

### Adapter Pattern (agent_framework/)
All MAF builders wrapped as IPA adapters: `self._builder = OfficialBuilder()`

### Hook Chain (claude_sdk/)
Tool calls intercepted by hooks: Approval → Audit → RateLimit → Sandbox

### Three-tier Routing (orchestration/)
Pattern Matcher (<10ms) → Semantic Router (<100ms) → LLM Classifier (<2s)

### Event Streaming (ag_ui/, swarm/)
AG-UI Protocol SSE events for real-time frontend updates

---

## Cross-Module Dependencies

```
agent_framework  ← hybrid (MAF execution)
claude_sdk       ← hybrid (Claude execution)
hybrid           ← orchestration (framework selection)
ag_ui            ← swarm (SSE event streaming)
orchestration    ← api/v1/orchestration (HTTP endpoints)
mcp              ← claude_sdk/mcp (tool discovery)
```

---

## Critical Rules

1. **agent_framework/**: MUST import from `agent_framework` package, use Adapter pattern
2. **claude_sdk/**: Uses `anthropic.AsyncAnthropic` client
3. **hybrid/**: ContextSynchronizer has known thread-safety issue (in-memory dict, no locks)
4. **orchestration/**: Three-tier router requires all layers for full coverage
5. **mcp/**: Azure server requires Azure SDK credentials

See individual module CLAUDE.md files for detailed documentation.

---

## V9 Deep Dive

> V9 covers each integration module in dedicated layer files:
> - `docs/07-analysis/V9/01-architecture/layer-05-orchestration.md` — Hybrid orchestration
> - `docs/07-analysis/V9/01-architecture/layer-06-maf-builders.md` — MAF builders (23 builders)
> - `docs/07-analysis/V9/01-architecture/layer-07-claude-sdk.md` — Claude SDK integration
> - `docs/07-analysis/V9/01-architecture/layer-08-mcp-tools.md` — MCP tool servers
> - `docs/07-analysis/V9/01-architecture/layer-09-integrations.md` — A2A, memory, patrol, correlation, etc.
> - `docs/07-analysis/V9/02-modules/` — Module-level cross-cutting analysis

---

**Last Updated**: 2026-03-31
